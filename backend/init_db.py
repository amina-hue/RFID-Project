"""Crée la base SQLite (rfid.db) et y met des données de test."""
from database.sqlite_db import get_connection, init_schema

DEBUT = "2026-01-01 00:00:00"
FIN = "2027-12-31 23:59:59"

utilisateurs = [
    # (nom, prenom, matricule, role)
    ("Albane", "Amina", "ADM001", "admin"),
    ("Belarbi", "Tinhinane", "ETU001", "etudiant"),
    ("Benazzouz", "Sonia", "ETU002", "etudiant"),
    ("Melissa", "Azil", "ETU003", "etudiant"),
    ("Periode", "Test", "ETU004", "etudiant"),
]
badges = [
    # (uid, matricule, statut)
    ("A1B2C3D4", "ADM001", "actif"),
    ("11223344", "ETU001", "actif"),
    ("55667788", "ETU002", "actif"),
    ("DEADBEEF", "ETU003", "revoque"),   # pour tester badge_revoque
    ("CAFE0001", "ETU004", "actif"),     # autorisation expirée : hors_periode
]
salles = [
    ("salle1", "Salle TP 1"),
    ("salle2", "Salle TP 2"),
]
autorisations = [
    # (matricule, salle, date_debut, date_fin)
    ("ADM001", "salle1", DEBUT, FIN),
    ("ADM001", "salle2", DEBUT, FIN),
    ("ETU001", "salle1", DEBUT, FIN),
    ("ETU002", "salle1", DEBUT, FIN),
    ("ETU002", "salle2", DEBUT, FIN),
    ("ETU003", "salle1", DEBUT, FIN),
    ("ETU004", "salle1", "2025-01-01 00:00:00", "2025-12-31 23:59:59"),
]

init_schema()
con = get_connection()
try:
    deja = con.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    if deja:
        print("La base contient déjà des données : rien à ajouter.")
    else:
        con.executemany(
            "INSERT INTO utilisateurs (nom, prenom, matricule, role) VALUES (?,?,?,?)",
            utilisateurs,
        )
        con.executemany("INSERT INTO salles (nom, localisation) VALUES (?,?)", salles)
        for uid, matricule, statut in badges:
            con.execute(
                "INSERT INTO badges (uid, utilisateur_id, statut) "
                "VALUES (?, (SELECT id FROM utilisateurs WHERE matricule = ?), ?)",
                (uid, matricule, statut),
            )
        for matricule, salle, debut, fin in autorisations:
            con.execute(
                "INSERT INTO autorisations (utilisateur_id, salle_id, date_debut, date_fin) "
                "VALUES ((SELECT id FROM utilisateurs WHERE matricule = ?), "
                "(SELECT id FROM salles WHERE nom = ?), ?, ?)",
                (matricule, salle, debut, fin),
            )
        con.commit()
        print("Base rfid.db prête.")
finally:
    con.close()