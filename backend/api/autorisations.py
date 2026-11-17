"""Gestion des autorisations : qui a le droit d'entrer dans quelle salle, et quand."""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.sqlite_db import get_connection

router = APIRouter(prefix="/autorisations", tags=["Autorisations"])

STATUTS = {"active", "suspendue"}
FORMAT_DATE = "%Y-%m-%d %H:%M:%S"

SELECT_AUTORISATION = """
SELECT a.id, a.utilisateur_id, u.prenom || ' ' || u.nom AS utilisateur,
       a.salle_id, s.nom AS salle, a.date_debut, a.date_fin, a.statut
FROM autorisations a
JOIN utilisateurs u ON u.id = a.utilisateur_id
JOIN salles s ON s.id = a.salle_id
"""


class AutorisationIn(BaseModel):
    utilisateur_id: int
    salle_id: int
    date_debut: datetime
    date_fin: datetime
    statut: str = "active"


def verifier(con, a: AutorisationIn):
    if a.statut not in STATUTS:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs possibles : {sorted(STATUTS)}",
        )
    if a.date_fin <= a.date_debut:
        raise HTTPException(
            status_code=422, detail="date_fin doit être après date_debut"
        )
    if con.execute(
        "SELECT 1 FROM utilisateurs WHERE id = ?", (a.utilisateur_id,)
    ).fetchone() is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if con.execute(
        "SELECT 1 FROM salles WHERE id = ?", (a.salle_id,)
    ).fetchone() is None:
        raise HTTPException(status_code=404, detail="Salle introuvable")


def lire_autorisation(con, auto_id: int) -> dict:
    ligne = con.execute(
        SELECT_AUTORISATION + " WHERE a.id = ?", (auto_id,)
    ).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Autorisation introuvable")
    return dict(ligne)


@router.get("")
def lister(utilisateur_id: int | None = None, salle_id: int | None = None):
    """Liste des autorisations (filtres possibles : utilisateur_id, salle_id)."""
    conditions, parametres = [], []
    if utilisateur_id is not None:
        conditions.append("a.utilisateur_id = ?")
        parametres.append(utilisateur_id)
    if salle_id is not None:
        conditions.append("a.salle_id = ?")
        parametres.append(salle_id)
    requete = SELECT_AUTORISATION
    if conditions:
        requete += " WHERE " + " AND ".join(conditions)
    requete += " ORDER BY a.id"
    con = get_connection()
    try:
        return [dict(ligne) for ligne in con.execute(requete, parametres).fetchall()]
    finally:
        con.close()


@router.get("/{auto_id}")
def lire(auto_id: int):
    """Une autorisation par son id."""
    con = get_connection()
    try:
        return lire_autorisation(con, auto_id)
    finally:
        con.close()


@router.post("", status_code=201)
def creer(a: AutorisationIn):
    """Donne à un utilisateur l'accès à une salle pour une période."""
    con = get_connection()
    try:
        verifier(con, a)
        cur = con.execute(
            "INSERT INTO autorisations "
            "(utilisateur_id, salle_id, date_debut, date_fin, statut) "
            "VALUES (?,?,?,?,?)",
            (
                a.utilisateur_id,
                a.salle_id,
                a.date_debut.strftime(FORMAT_DATE),
                a.date_fin.strftime(FORMAT_DATE),
                a.statut,
            ),
        )
        con.commit()
        return lire_autorisation(con, cur.lastrowid)
    finally:
        con.close()


@router.put("/{auto_id}")
def modifier(auto_id: int, a: AutorisationIn):
    """Modifie une autorisation."""
    con = get_connection()
    try:
        lire_autorisation(con, auto_id)
        verifier(con, a)
        con.execute(
            "UPDATE autorisations SET utilisateur_id = ?, salle_id = ?, "
            "date_debut = ?, date_fin = ?, statut = ? WHERE id = ?",
            (
                a.utilisateur_id,
                a.salle_id,
                a.date_debut.strftime(FORMAT_DATE),
                a.date_fin.strftime(FORMAT_DATE),
                a.statut,
                auto_id,
            ),
        )
        con.commit()
        return lire_autorisation(con, auto_id)
    finally:
        con.close()


def changer_statut(auto_id: int, statut: str) -> dict:
    con = get_connection()
    try:
        lire_autorisation(con, auto_id)
        con.execute(
            "UPDATE autorisations SET statut = ? WHERE id = ?", (statut, auto_id)
        )
        con.commit()
        return lire_autorisation(con, auto_id)
    finally:
        con.close()


@router.patch("/{auto_id}/suspendre")
def suspendre(auto_id: int):
    """Suspend une autorisation sans la supprimer."""
    return changer_statut(auto_id, "suspendue")


@router.patch("/{auto_id}/activer")
def activer(auto_id: int):
    """Réactive une autorisation suspendue."""
    return changer_statut(auto_id, "active")


@router.delete("/{auto_id}")
def supprimer(auto_id: int):
    """Supprime une autorisation."""
    con = get_connection()
    try:
        cur = con.execute("DELETE FROM autorisations WHERE id = ?", (auto_id,))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Autorisation introuvable")
        return {"message": "Autorisation supprimée"}
    finally:
        con.close()