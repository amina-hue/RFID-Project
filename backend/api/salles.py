"""Gestion des salles (table SQLite salles).

Le nom d'une salle doit être identique à celui utilisé dans MQTT (salle1, salle2...).
"""
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.sqlite_db import get_connection

router = APIRouter(prefix="/salles", tags=["Salles"])


class SalleIn(BaseModel):
    nom: str
    localisation: str | None = None


@router.get("")
def lister():
    """Liste de toutes les salles."""
    con = get_connection()
    try:
        lignes = con.execute("SELECT * FROM salles ORDER BY nom").fetchall()
        return [dict(ligne) for ligne in lignes]
    finally:
        con.close()


@router.get("/{salle_id}")
def lire(salle_id: int):
    """Une salle par son id."""
    con = get_connection()
    try:
        ligne = con.execute(
            "SELECT * FROM salles WHERE id = ?", (salle_id,)
        ).fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail="Salle introuvable")
        return dict(ligne)
    finally:
        con.close()


@router.post("", status_code=201)
def creer(s: SalleIn):
    """Crée une salle."""
    con = get_connection()
    try:
        cur = con.execute(
            "INSERT INTO salles (nom, localisation) VALUES (?, ?)",
            (s.nom, s.localisation),
        )
        con.commit()
        return {"id": cur.lastrowid, **s.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ce nom de salle existe déjà")
    finally:
        con.close()


@router.put("/{salle_id}")
def modifier(salle_id: int, s: SalleIn):
    """Modifie une salle."""
    con = get_connection()
    try:
        cur = con.execute(
            "UPDATE salles SET nom = ?, localisation = ? WHERE id = ?",
            (s.nom, s.localisation, salle_id),
        )
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Salle introuvable")
        return {"id": salle_id, **s.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ce nom de salle existe déjà")
    finally:
        con.close()


@router.delete("/{salle_id}")
def supprimer(salle_id: int):
    """Supprime une salle (ses autorisations aussi)."""
    con = get_connection()
    try:
        cur = con.execute("DELETE FROM salles WHERE id = ?", (salle_id,))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Salle introuvable")
        return {"message": "Salle supprimée"}
    finally:
        con.close()