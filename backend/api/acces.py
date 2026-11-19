"""Autorisation manuelle d'un accès refusé, depuis le tableau de bord.

Un refus reste dans l'historique tel quel. L'autorisation manuelle ajoute un
nouvel événement « autorisé » (raison : autorisation_manuelle) qui garde la
trace de qui a validé, quand, et pourquoi. Elle n'ouvre aucune porte : elle
sert à corriger la présence dans le journal.
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.sqlite_db import get_connection
from services import influx_service

router = APIRouter(prefix="/acces", tags=["Accès"])

ROLES_VALIDEURS = {"enseignant", "admin"}
FORMAT_DATE = "%Y-%m-%d %H:%M:%S"


class AutorisationManuelleIn(BaseModel):
    utilisateur_id: int            # l'étudiant à autoriser
    salle: str                     # nom de la salle (identique à MQTT : salle1...)
    valide_par: int                # l'enseignant ou l'admin qui valide
    motif: str | None = None       # ex : « badge oublié »
    refus_heure: datetime | None = None   # heure du refus d'origine (évite un doublon)


def lire_utilisateur(con, user_id: int, libelle: str):
    ligne = con.execute(
        "SELECT id, nom, prenom, role FROM utilisateurs WHERE id = ?", (user_id,)
    ).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail=f"{libelle} introuvable")
    return ligne


def verifier_valideur(con, valideur, salle_id: int):
    """Un admin peut toujours valider. Un enseignant doit avoir le droit d'entrer
    dans cette salle en ce moment (sinon il pourrait valider dans n'importe quelle salle)."""
    if valideur["role"] not in ROLES_VALIDEURS:
        raise HTTPException(
            status_code=403,
            detail=f"Seuls les rôles {sorted(ROLES_VALIDEURS)} peuvent autoriser un accès",
        )
    if valideur["role"] == "admin":
        return
    maintenant = datetime.now().strftime(FORMAT_DATE)
    ok = con.execute(
        """SELECT 1 FROM autorisations
           WHERE utilisateur_id = ? AND salle_id = ? AND statut = 'active'
             AND date_debut <= ? AND date_fin >= ? LIMIT 1""",
        (valideur["id"], salle_id, maintenant, maintenant),
    ).fetchone()
    if ok is None:
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas d'autorisation active pour cette salle en ce moment",
        )


@router.post("/manuel", status_code=201)
def autoriser_manuellement(a: AutorisationManuelleIn):
    """Enregistre une entrée autorisée à la main pour un étudiant."""
    con = get_connection()
    try:
        salle = con.execute(
            "SELECT id FROM salles WHERE nom = ?", (a.salle,)
        ).fetchone()
        if salle is None:
            raise HTTPException(status_code=404, detail="Salle introuvable")

        etudiant = lire_utilisateur(con, a.utilisateur_id, "Utilisateur")
        valideur = lire_utilisateur(con, a.valide_par, "Validateur")
        verifier_valideur(con, valideur, salle["id"])

        # Le hachage du badge de l'étudiant relie cette entrée à ses autres passages
        badge = con.execute(
            "SELECT uid FROM badges WHERE utilisateur_id = ? ORDER BY id LIMIT 1",
            (etudiant["id"],),
        ).fetchone()
        uid = badge["uid"] if badge else f"MATRICULE-{etudiant['id']}"
    finally:
        con.close()

    nom = f"{etudiant['prenom']} {etudiant['nom']}"
    valide_par = f"{valideur['prenom']} {valideur['nom']}"
    refus_heure = a.refus_heure.isoformat() if a.refus_heure else None

    try:
        if refus_heure and influx_service.deja_autorise(a.salle, refus_heure):
            raise HTTPException(
                status_code=409, detail="Ce refus a déjà été autorisé manuellement"
            )
        heure = influx_service.enregistrer_manuel(
            a.salle, uid, nom, etudiant["role"], valide_par, a.motif, refus_heure
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {e}")

    return {
        "heure": heure,
        "salle": a.salle,
        "nom": nom,
        "resultat": "granted",
        "raison": "autorisation_manuelle",
        "valide_par": valide_par,
        "motif": a.motif,
    }