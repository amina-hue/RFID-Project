"""Statistiques d'accès pour le tableau de bord (lues dans InfluxDB)."""
from fastapi import APIRouter, HTTPException, Query

from services import influx_service

router = APIRouter(prefix="/statistiques", tags=["Statistiques"])


@router.get("/resume")
def resume(jours: int = Query(7, ge=1, le=365)):
    """Nombre d'accès autorisés (granted) et refusés (denied)."""
    try:
        return influx_service.resume(jours)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {e}")


@router.get("/par-heure")
def par_heure(jours: int = Query(7, ge=1, le=365)):
    """Nombre d'accès par heure et par salle."""
    try:
        return influx_service.acces_par_heure(jours)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {e}")


@router.get("/derniers-acces")
def derniers_acces(
    limite: int = Query(20, ge=1, le=500),
    jours: int = Query(7, ge=1, le=365),
):
    """Les derniers accès (journal en direct)."""
    try:
        return influx_service.derniers_acces(limite, jours)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {e}")