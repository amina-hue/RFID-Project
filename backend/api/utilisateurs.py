"""Gestion des utilisateurs (table SQLite utilisateurs)."""
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.sqlite_db import get_connection

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])

ROLES = {"etudiant", "enseignant", "technicien", "admin"}


class UtilisateurIn(BaseModel):
    nom: str
    prenom: str
    matricule: str
    role: str


def verifier_role(role: str):
    if role not in ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Rôle invalide. Valeurs possibles : {sorted(ROLES)}",
        )


@router.get("")
def lister():
    """Liste de tous les utilisateurs."""
    con = get_connection()
    try:
        lignes = con.execute(
            "SELECT * FROM utilisateurs ORDER BY nom, prenom"
        ).fetchall()
        return [dict(ligne) for ligne in lignes]
    finally:
        con.close()


@router.get("/{user_id}")
def lire(user_id: int):
    """Un utilisateur par son id."""
    con = get_connection()
    try:
        ligne = con.execute(
            "SELECT * FROM utilisateurs WHERE id = ?", (user_id,)
        ).fetchone()
        if ligne is None:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return dict(ligne)
    finally:
        con.close()


@router.post("", status_code=201)
def creer(u: UtilisateurIn):
    """Crée un utilisateur."""
    verifier_role(u.role)
    con = get_connection()
    try:
        cur = con.execute(
            "INSERT INTO utilisateurs (nom, prenom, matricule, role) VALUES (?,?,?,?)",
            (u.nom, u.prenom, u.matricule, u.role),
        )
        con.commit()
        return {"id": cur.lastrowid, **u.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ce matricule existe déjà")
    finally:
        con.close()


@router.put("/{user_id}")
def modifier(user_id: int, u: UtilisateurIn):
    """Modifie un utilisateur."""
    verifier_role(u.role)
    con = get_connection()
    try:
        cur = con.execute(
            "UPDATE utilisateurs SET nom = ?, prenom = ?, matricule = ?, role = ? WHERE id = ?",
            (u.nom, u.prenom, u.matricule, u.role, user_id),
        )
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return {"id": user_id, **u.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ce matricule existe déjà")
    finally:
        con.close()


@router.delete("/{user_id}")
def supprimer(user_id: int):
    """Supprime un utilisateur (ses badges et autorisations aussi)."""
    con = get_connection()
    try:
        cur = con.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return {"message": "Utilisateur supprimé"}
    finally:
        con.close()