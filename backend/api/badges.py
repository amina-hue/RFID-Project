"""Gestion des badges (table SQLite badges)."""
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.sqlite_db import get_connection

router = APIRouter(prefix="/badges", tags=["Badges"])

STATUTS = {"actif", "revoque"}

SELECT_BADGE = """
SELECT b.id, b.uid, b.statut, b.utilisateur_id,
       u.prenom || ' ' || u.nom AS utilisateur, u.matricule
FROM badges b JOIN utilisateurs u ON u.id = b.utilisateur_id
"""


class BadgeIn(BaseModel):
    uid: str
    utilisateur_id: int
    statut: str = "actif"


def normaliser_uid(uid: str) -> str:
    """Le gardien met les UID en majuscules : on stocke donc en majuscules."""
    uid = uid.strip().upper()
    if not uid:
        raise HTTPException(status_code=422, detail="L'UID ne peut pas être vide")
    return uid


def verifier_statut(statut: str):
    if statut not in STATUTS:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs possibles : {sorted(STATUTS)}",
        )


def verifier_utilisateur(con, utilisateur_id: int):
    ligne = con.execute(
        "SELECT 1 FROM utilisateurs WHERE id = ?", (utilisateur_id,)
    ).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")


def lire_badge(con, badge_id: int) -> dict:
    ligne = con.execute(SELECT_BADGE + " WHERE b.id = ?", (badge_id,)).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Badge introuvable")
    return dict(ligne)


@router.get("")
def lister(utilisateur_id: int | None = None):
    """Liste des badges (filtre possible par utilisateur_id)."""
    con = get_connection()
    try:
        if utilisateur_id is None:
            lignes = con.execute(SELECT_BADGE + " ORDER BY b.id").fetchall()
        else:
            lignes = con.execute(
                SELECT_BADGE + " WHERE b.utilisateur_id = ? ORDER BY b.id",
                (utilisateur_id,),
            ).fetchall()
        return [dict(ligne) for ligne in lignes]
    finally:
        con.close()


@router.get("/{badge_id}")
def lire(badge_id: int):
    """Un badge par son id."""
    con = get_connection()
    try:
        return lire_badge(con, badge_id)
    finally:
        con.close()


@router.post("", status_code=201)
def creer(b: BadgeIn):
    """Associe un nouveau badge à un utilisateur."""
    uid = normaliser_uid(b.uid)
    verifier_statut(b.statut)
    con = get_connection()
    try:
        verifier_utilisateur(con, b.utilisateur_id)
        cur = con.execute(
            "INSERT INTO badges (uid, utilisateur_id, statut) VALUES (?,?,?)",
            (uid, b.utilisateur_id, b.statut),
        )
        con.commit()
        return lire_badge(con, cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Cet UID de badge existe déjà")
    finally:
        con.close()


@router.put("/{badge_id}")
def modifier(badge_id: int, b: BadgeIn):
    """Modifie un badge (UID, propriétaire, statut)."""
    uid = normaliser_uid(b.uid)
    verifier_statut(b.statut)
    con = get_connection()
    try:
        lire_badge(con, badge_id)
        verifier_utilisateur(con, b.utilisateur_id)
        con.execute(
            "UPDATE badges SET uid = ?, utilisateur_id = ?, statut = ? WHERE id = ?",
            (uid, b.utilisateur_id, b.statut, badge_id),
        )
        con.commit()
        return lire_badge(con, badge_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Cet UID de badge existe déjà")
    finally:
        con.close()


def changer_statut(badge_id: int, statut: str) -> dict:
    con = get_connection()
    try:
        lire_badge(con, badge_id)
        con.execute("UPDATE badges SET statut = ? WHERE id = ?", (statut, badge_id))
        con.commit()
        return lire_badge(con, badge_id)
    finally:
        con.close()


@router.patch("/{badge_id}/revoquer")
def revoquer(badge_id: int):
    """Révoque un badge (badge perdu ou volé) : il sera refusé partout."""
    return changer_statut(badge_id, "revoque")


@router.patch("/{badge_id}/activer")
def activer(badge_id: int):
    """Réactive un badge révoqué."""
    return changer_statut(badge_id, "actif")


@router.delete("/{badge_id}")
def supprimer(badge_id: int):
    """Supprime définitivement un badge."""
    con = get_connection()
    try:
        cur = con.execute("DELETE FROM badges WHERE id = ?", (badge_id,))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Badge introuvable")
        return {"message": "Badge supprimé"}
    finally:
        con.close()