"""Lance le moteur de décision MQTT seul (sans l'API)."""
import sys

from database.sqlite_db import init_schema
from services import mqtt_service

if __name__ == "__main__":
    init_schema()
    try:
        mqtt_service.lancer(bloquant=True)
    except OSError as e:
        print(f"Impossible de joindre Mosquitto ({e})")
        print("Vérifie que Docker tourne : docker compose up -d")
        sys.exit(1)