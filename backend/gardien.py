"""
Le « gardien » : reçoit l'UID par MQTT, décide, répond, enregistre dans InfluxDB.

Sujets MQTT :
  demande : access/<salle>/request   {"uid": "A1B2C3D4"}
  réponse : access/<salle>/response  {"granted": true, "reason": "ok", "nom": "..."}
"""
import hashlib
import json
import os
import sqlite3
import time

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------- Réglages (modifiables par variables d'environnement) ----------
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "token-de-dev-123")
INFLUX_ORG = os.getenv("INFLUX_ORG", "projet")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acces")
SEL = os.getenv("UID_SEL", "change-moi")   # sert à hacher les UID (RGPD)
DB_FILE = "badges.db"

# ---------- Connexions ----------
influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api(write_options=SYNCHRONOUS)


def hacher(uid: str) -> str:
    """Empreinte de l'UID : on ne stocke jamais l'UID brut dans InfluxDB."""
    return hashlib.sha256((SEL + uid).encode()).hexdigest()[:16]


def decider(uid: str, salle: str):
    """Retourne (autorise, raison, nom, role) en consultant SQLite."""
    con = sqlite3.connect(DB_FILE)
    try:
        ligne = con.execute(
            "SELECT nom, role, actif FROM badges WHERE uid = ?", (uid,)
        ).fetchone()
        if ligne is None:
            return False, "badge_inconnu", None, "inconnu"
        nom, role, actif = ligne
        if not actif:
            return False, "badge_revoque", nom, role
        droit = con.execute(
            "SELECT 1 FROM droits WHERE uid = ? AND salle = ?", (uid, salle)
        ).fetchone()
        if droit is None:
            return False, "salle_non_autorisee", nom, role
        return True, "ok", nom, role
    finally:
        con.close()


def enregistrer(salle, uid, autorise, raison, nom, role, latence_ms):
    """Écrit un événement dans InfluxDB."""
    point = (
        Point("access_events")
        .tag("room", salle)
        .tag("role", role)
        .tag("result", "granted" if autorise else "denied")
        .field("uid_hash", hacher(uid))
        .field("nom", nom or "")
        .field("reason", raison)
        .field("latency_ms", float(latence_ms))
    )
    write_api.write(bucket=INFLUX_BUCKET, record=point)


# ---------- MQTT ----------
def on_connect(client, userdata, flags, reason_code, properties):
    print("Connecté à MQTT (code :", reason_code, ")")
    client.subscribe("access/+/request")


def on_message(client, userdata, msg):
    debut = time.time()
    try:
        salle = msg.topic.split("/")[1]
        uid = json.loads(msg.payload)["uid"].strip().upper()
    except Exception as e:
        print("Message illisible :", msg.payload, e)
        return

    autorise, raison, nom, role = decider(uid, salle)

    # 1) On répond d'abord (la porte ne doit pas attendre InfluxDB)
    reponse = {"granted": autorise, "reason": raison, "nom": nom}
    client.publish(f"access/{salle}/response", json.dumps(reponse))
    print(f"[{salle}] {uid} -> {'OUVERT' if autorise else 'REFUSÉ'} ({raison})")

    # 2) Puis on enregistre. Si InfluxDB est en panne, le gardien continue.
    latence_ms = (time.time() - debut) * 1000
    try:
        enregistrer(salle, uid, autorise, raison, nom, role, latence_ms)
    except Exception as e:
        print("Écriture InfluxDB impossible :", e)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT)
print("Gardien en attente de badges... (Ctrl+C pour arrêter)")
client.loop_forever()