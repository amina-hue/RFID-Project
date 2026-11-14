"""
Générateur de faux événements d'accès pour InfluxDB.

Écrit dans le bucket « acces » avec EXACTEMENT le même format que gardien.py :
  mesure : access_events
  tags   : room, role, result (granted / denied)
  champs : uid_hash, nom, reason, latency_ms

Exemples :
  python generateur.py                  # 30 derniers jours
  python generateur.py --jours 14       # 14 derniers jours
  python generateur.py --test-tache     # 30 événements dans la dernière heure
                                        # (pour tester la tâche de downsampling)

Attention : la rétention du bucket est de 90 jours, donc on ne génère jamais
d'événements plus vieux que 85 jours (sinon InfluxDB les supprime aussitôt).
"""
import argparse
import hashlib
import os
import random
from datetime import datetime, timedelta, timezone

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------- Réglages (les mêmes que gardien.py) ----------
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "token-de-dev-123")
INFLUX_ORG = os.getenv("INFLUX_ORG", "projet")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acces")
SEL = os.getenv("UID_SEL", "change-moi")

# ---------- Données fictives (à adapter si besoin) ----------
SALLES = ["salle1", "salle2", "salle3", "salle4"]
ROLES = ["etudiant", "enseignant", "admin"]
POIDS_ROLES = [80, 15, 5]          # 80 % étudiants, 15 % enseignants, 5 % admins
NB_UTILISATEURS = 40

# Poids par heure : plus c'est grand, plus il y a de passages (pics 8h et 13h)
POIDS_HEURES = {
    8: 6, 9: 8, 10: 7, 11: 5, 12: 3, 13: 7, 14: 8, 15: 6, 16: 4, 17: 2,
}
MAX_PAR_HEURE_ET_SALLE = 8          # passages max par heure et par salle (jour de semaine)
PROBA_REFUS = 0.12                  # environ 12 % de refus


def hacher(uid: str) -> str:
    """Même fonction que dans gardien.py : on ne stocke jamais l'UID brut."""
    return hashlib.sha256((SEL + uid).encode()).hexdigest()[:16]


def creer_utilisateurs():
    """Crée de faux utilisateurs : uid fictif, nom, rôle."""
    utilisateurs = []
    for i in range(NB_UTILISATEURS):
        uid = f"{random.getrandbits(32):08X}"
        role = random.choices(ROLES, weights=POIDS_ROLES)[0]
        utilisateurs.append({"uid": uid, "nom": f"Utilisateur{i + 1}", "role": role})
    return utilisateurs


def faire_point(ts, salle, utilisateurs):
    """Fabrique un événement (accepté ou refusé) à l'instant ts."""
    if random.random() < PROBA_REFUS:
        raison = random.choices(
            ["badge_inconnu", "salle_non_autorisee", "badge_revoque"],
            weights=[50, 35, 15],
        )[0]
        if raison == "badge_inconnu":
            uid = f"{random.getrandbits(32):08X}"
            nom, role = "", "inconnu"
        else:
            u = random.choice(utilisateurs)
            uid, nom, role = u["uid"], u["nom"], u["role"]
        return construire(ts, salle, uid, nom, role, False, raison)

    u = random.choice(utilisateurs)
    return construire(ts, salle, u["uid"], u["nom"], u["role"], True, "ok")


def construire(ts, salle, uid, nom, role, autorise, raison):
    latence = max(50.0, random.gauss(350, 120))
    return (
        Point("access_events")
        .tag("room", salle)
        .tag("role", role)
        .tag("result", "granted" if autorise else "denied")
        .field("uid_hash", hacher(uid))
        .field("nom", nom)
        .field("reason", raison)
        .field("latency_ms", float(latence))
        .time(ts)
    )


def generer_historique(jours, utilisateurs, maintenant):
    """Génère plusieurs jours d'événements, heure par heure, salle par salle."""
    points = []
    debut = (maintenant - timedelta(days=jours)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    jour = debut
    while jour < maintenant:
        # Vendredi (4) et samedi (5) : week-end en Algérie, très peu de passages
        facteur = 0.1 if jour.weekday() in (4, 5) else 1.0
        for heure, poids in POIDS_HEURES.items():
            for salle in SALLES:
                maxi = int(MAX_PAR_HEURE_ET_SALLE * poids / 8 * facteur)
                for _ in range(random.randint(0, max(maxi, 0))):
                    ts = jour.replace(hour=heure) + timedelta(
                        seconds=random.randint(0, 3599)
                    )
                    if ts < maintenant:     # jamais d'événement dans le futur
                        points.append(faire_point(ts, salle, utilisateurs))
        jour += timedelta(days=1)

    # Quelques rafales de refus (plus de 5 d'affilée) pour tester la détection d'anomalie
    for _ in range(max(1, jours // 7)):
        salle = random.choice(SALLES)
        ts0 = maintenant - timedelta(
            days=random.randint(1, jours), hours=random.randint(0, 8)
        )
        for k in range(random.randint(6, 9)):
            ts = ts0 + timedelta(seconds=10 * k)
            if ts < maintenant:
                points.append(
                    construire(
                        ts, salle, f"{random.getrandbits(32):08X}", "",
                        "inconnu", False, "badge_inconnu",
                    )
                )
    return points


def generer_derniere_heure(utilisateurs, maintenant, nombre=30):
    """Événements de la dernière heure, pour tester la tâche de downsampling."""
    return [
        faire_point(
            maintenant - timedelta(seconds=random.randint(1, 3000)),
            random.choice(SALLES),
            utilisateurs,
        )
        for _ in range(nombre)
    ]


def main():
    parser = argparse.ArgumentParser(description="Générateur de faux événements d'accès")
    parser.add_argument("--jours", type=int, default=30, help="nombre de jours à générer (max 85)")
    parser.add_argument("--test-tache", action="store_true",
                        help="génère 30 événements dans la dernière heure")
    parser.add_argument("--seed", type=int, default=None, help="graine aléatoire (résultats reproductibles)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
    jours = min(max(args.jours, 1), 85)

    maintenant = datetime.now(timezone.utc)
    utilisateurs = creer_utilisateurs()

    if args.test_tache:
        points = generer_derniere_heure(utilisateurs, maintenant)
    else:
        points = generer_historique(jours, utilisateurs, maintenant)

    print(f"{len(points)} événements à écrire dans « {INFLUX_BUCKET} »...")
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        for i in range(0, len(points), 5000):        # par paquets de 5000
            write_api.write(bucket=INFLUX_BUCKET, record=points[i:i + 5000])
            print(f"  {min(i + 5000, len(points))}/{len(points)}")
    print("Terminé.")


if __name__ == "__main__":
    main()