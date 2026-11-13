"""Crée la base SQLite des badges et y met quelques badges de test."""
import sqlite3

con = sqlite3.connect("badges.db")
con.executescript("""
CREATE TABLE IF NOT EXISTS badges (
    uid   TEXT PRIMARY KEY,          -- numéro du badge, ex: A1B2C3D4
    nom   TEXT NOT NULL,
    role  TEXT NOT NULL,             -- etudiant, enseignant, technicien, admin
    actif INTEGER NOT NULL DEFAULT 1 -- 1 = actif, 0 = révoqué
);
CREATE TABLE IF NOT EXISTS droits (
    uid   TEXT NOT NULL,
    salle TEXT NOT NULL,             -- ex: salle1
    PRIMARY KEY (uid, salle)
);
""")

# Badges de test : remplacez les UID par ceux de VOS vrais badges
badges = [
    ("A1B2C3D4", "Sara Benali",   "etudiant",   1),
    ("11223344", "Prof. Amrani",  "enseignant", 1),
    ("DEADBEEF", "Ancien badge",  "etudiant",   0),   # révoqué
]
droits = [
    ("A1B2C3D4", "salle1"),
    ("11223344", "salle1"),
    ("11223344", "salle2"),
    ("DEADBEEF", "salle1"),
]
con.executemany("INSERT OR IGNORE INTO badges VALUES (?,?,?,?)", badges)
con.executemany("INSERT OR IGNORE INTO droits VALUES (?,?)", droits)
con.commit()
con.close()
print("Base badges.db prête.")