"""Point d'entrée : lance l'API et le moteur de décision MQTT."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import acces, autorisations, badges, salles, statistiques, utilisateurs
from database.sqlite_db import init_schema
from services import mqtt_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    client = None
    try:
        client = mqtt_service.lancer(bloquant=False)
        print("Moteur de décision MQTT démarré")
    except OSError as e:
        print(f"MQTT indisponible ({e}) : l'API démarre quand même")
    yield
    if client:
        client.loop_stop()
        client.disconnect()


app = FastAPI(title="API RFID - contrôle d'accès", lifespan=lifespan)

# Autorise le tableau de bord (autre adresse/port) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(utilisateurs.router)
app.include_router(badges.router)
app.include_router(salles.router)
app.include_router(autorisations.router)
app.include_router(statistiques.router)
app.include_router(acces.router)


@app.get("/")
def racine():
    return {"message": "API RFID en ligne", "documentation": "/docs"}