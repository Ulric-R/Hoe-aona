"""Préférences de l'application (pondérations, seuils, pays, langue, rétention)."""
from fastapi import APIRouter

from ..db import get_db
from ..schemas import Preferences
from ..services.pipeline import load_preferences

router = APIRouter(prefix="/api/settings", tags=["paramètres"])


@router.get("", response_model=Preferences)
async def read_settings():
    return load_preferences()


@router.put("", response_model=Preferences)
async def update_settings(prefs: Preferences):
    get_db().save_preferences(prefs.model_dump())
    return prefs
