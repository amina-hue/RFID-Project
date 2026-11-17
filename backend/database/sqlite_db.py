"""Connexion à SQLite et création des tables."""
import os
import sqlite3

# Fichier rfid.db dans le dossier backend (quel que soit le dossier de lancement)
DB_FILE = os.getenv(
    "SQLITE_FILE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rfid.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT NOT NULL,
    prenom    TEXT NOT NULL,
    matricule TEXT NOT NULL UNIQUE,
    role      TEXT NOT NULL            -- etudiant, enseignant, technicien, admin
);

CREATE TABLE IF NOT EXISTS badges (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    uid            TEXT NOT NULL UNIQUE,   -- numéro du badge, ex: A1B2C3D4
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    statut         TEXT NOT NULL DEFAULT 'actif'   -- actif, revoque
);

CREATE TABLE IF NOT EXISTS salles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nom          TEXT NOT NULL UNIQUE,   -- identique au nom MQTT : salle1, salle2...
    localisation TEXT
);

CREATE TABLE IF NOT EXISTS autorisations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    salle_id       INTEGER NOT NULL REFERENCES salles(id) ON DELETE CASCADE,
    date_debut     TEXT NOT NULL,          -- 'AAAA-MM-JJ HH:MM:SS'
    date_fin       TEXT NOT NULL,
    statut         TEXT NOT NULL DEFAULT 'active'  -- active, suspendue
);
"""


def get_connection():
    """Ouvre une connexion SQLite (les lignes se lisent comme des dictionnaires)."""
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_schema():
    """Crée les tables si elles n'existent pas."""
    con = get_connection()
    try:
        con.executescript(SCHEMA)
        con.commit()
    finally:
        con.close()