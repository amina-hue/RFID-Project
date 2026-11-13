"""Faux badge : simule l'ESP32. Usage : python faux_badge.py A1B2C3D4 salle1"""
import json
import sys

import paho.mqtt.client as mqtt

uid = sys.argv[1] if len(sys.argv) > 1 else "A1B2C3D4"
salle = sys.argv[2] if len(sys.argv) > 2 else "salle1"


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(f"access/{salle}/response")
    client.publish(f"access/{salle}/request", json.dumps({"uid": uid}))
    print(f"Badge {uid} présenté à {salle}...")


def on_message(client, userdata, msg):
    rep = json.loads(msg.payload)
    print("OUVERT" if rep["granted"] else "REFUSÉ", "-", rep["reason"])
    client.disconnect()


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_forever()