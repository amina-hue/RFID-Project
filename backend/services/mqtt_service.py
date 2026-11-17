"""Service MQTT : reçoit les demandes d'accès, décide, répond et enregistre."""
import json
import os
import time

import paho.mqtt.client as mqtt

from services.access_service import decider
from services.influx_service import enregistrer

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")            # à remplir quand Mosquitto aura un mot de passe
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connecté à MQTT (code :", reason_code, ")")
    client.subscribe("access/+/request")


def on_message(client, userdata, msg):
    debut = time.perf_counter()
    try:
        salle = msg.topic.split("/")[1]
        uid = json.loads(msg.payload)["uid"].strip().upper()
    except Exception as e:
        print("Message illisible :", msg.payload, e)
        return

    try:
        autorise, raison, nom, role = decider(uid, salle)
    except Exception as e:
        print("Erreur SQLite :", e)
        autorise, raison, nom, role = False, "erreur_interne", None, "inconnu"

    # 1) On répond d'abord (la porte ne doit pas attendre InfluxDB)
    reponse = {"granted": autorise, "reason": raison, "nom": nom}
    client.publish(f"access/{salle}/response", json.dumps(reponse))
    print(f"[{salle}] {uid} -> {'OUVERT' if autorise else 'REFUSÉ'} ({raison})")

    # 2) Puis on enregistre. Si InfluxDB est en panne, le service continue.
    latence_ms = (time.perf_counter() - debut) * 1000
    try:
        enregistrer(salle, uid, autorise, raison, nom, role, latence_ms)
    except Exception as e:
        print("Écriture InfluxDB impossible :", e)


def lancer(bloquant: bool = True):
    """Démarre l'écoute MQTT. bloquant=False : tourne en arrière-plan (pour l'API)."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    if bloquant:
        print("Gardien en attente de badges... (Ctrl+C pour arrêter)")
        client.loop_forever()
    else:
        client.loop_start()
    return client