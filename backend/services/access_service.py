"""Logique de décision : ce badge a-t-il le droit d'entrer dans cette salle ?"""
from datetime import datetime

from database.sqlite_db import get_connection


def decider(uid: str, salle: str):
    """Retourne (autorise, raison, nom_complet, role)."""
    con = get_connection()
    try:
        badge = con.execute(
            """SELECT b.statut, u.id AS user_id, u.nom, u.prenom, u.role
               FROM badges b JOIN utilisateurs u ON u.id = b.utilisateur_id
               WHERE b.uid = ?""",
            (uid,),
        ).fetchone()
        if badge is None:
            return False, "badge_inconnu", None, "inconnu"

        nom_complet = f"{badge['prenom']} {badge['nom']}"
        role = badge["role"]

        if badge["statut"] != "actif":
            return False, "badge_revoque", nom_complet, role

        ligne_salle = con.execute(
            "SELECT id FROM salles WHERE nom = ?", (salle,)
        ).fetchone()
        if ligne_salle is None:
            return False, "salle_inconnue", nom_complet, role

        maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        valide = con.execute(
            """SELECT 1 FROM autorisations
               WHERE utilisateur_id = ? AND salle_id = ? AND statut = 'active'
                 AND date_debut <= ? AND date_fin >= ? LIMIT 1""",
            (badge["user_id"], ligne_salle["id"], maintenant, maintenant),
        ).fetchone()
        if valide:
            return True, "ok", nom_complet, role

        # Refus : on précise si une autorisation existe mais hors période
        existe = con.execute(
            """SELECT 1 FROM autorisations
               WHERE utilisateur_id = ? AND salle_id = ? AND statut = 'active' LIMIT 1""",
            (badge["user_id"], ligne_salle["id"]),
        ).fetchone()
        raison = "hors_periode" if existe else "salle_non_autorisee"
        return False, raison, nom_complet, role
    finally:
        con.close()