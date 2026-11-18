"""Écriture et lecture des événements d'accès dans InfluxDB."""
import hashlib
import os

from influxdb_client import Point

from database.influx_db import INFLUX_BUCKET, query_api, write_api

SEL = os.getenv("UID_SEL", "change-moi")   # sert à hacher les UID (RGPD)


def hacher(uid: str) -> str:
    """Empreinte de l'UID : on ne stocke jamais l'UID brut dans InfluxDB."""
    return hashlib.sha256((SEL + uid).encode()).hexdigest()[:16]


def enregistrer(salle, uid, autorise, raison, nom, role, latence_ms):
    """Écrit un événement d'accès."""
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


# ---------- Lecture (utilisée par l'API plus tard) ----------
# Le tag "result" est renommé "resultat" à la lecture : InfluxDB a déjà
# une colonne "result" dans sa réponse, ce qui créait un conflit.

def derniers_acces(limite: int = 20, jours: int = 7):
    """Les derniers accès, un par ligne."""
    requete = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{jours}d)
  |> filter(fn: (r) => r._measurement == "access_events")
  |> rename(columns: {{result: "resultat"}})
  |> pivot(rowKey: ["_time", "room", "role", "resultat"], columnKey: ["_field"], valueColumn: "_value")
  |> group()
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limite})
'''
    lignes = []
    for table in query_api.query(requete):
        for r in table.records:
            lignes.append({
                "heure": r.get_time().isoformat(),
                "salle": r.values.get("room"),
                "role": r.values.get("role"),
                "resultat": r.values.get("resultat"),
                "raison": r.values.get("reason"),
                "nom": r.values.get("nom"),
                "latence_ms": r.values.get("latency_ms"),
                "uid_hash": r.values.get("uid_hash"),
            })
    return lignes


def acces_par_heure(jours: int = 7):
    """Nombre d'accès par heure et par salle."""
    requete = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{jours}d)
  |> filter(fn: (r) => r._measurement == "access_events" and r._field == "latency_ms")
  |> group(columns: ["room"])
  |> aggregateWindow(every: 1h, fn: count, createEmpty: false)
'''
    lignes = []
    for table in query_api.query(requete):
        for r in table.records:
            lignes.append({
                "heure": r.get_time().isoformat(),
                "salle": r.values.get("room"),
                "acces": r.get_value(),
            })
    return lignes


def resume(jours: int = 7):
    """Nombre d'accès autorisés et refusés."""
    requete = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{jours}d)
  |> filter(fn: (r) => r._measurement == "access_events" and r._field == "latency_ms")
  |> rename(columns: {{result: "resultat"}})
  |> group(columns: ["resultat"])
  |> count()
'''
    total = {"granted": 0, "denied": 0}
    for table in query_api.query(requete):
        for r in table.records:
            total[r.values.get("resultat")] = r.get_value()
    return total