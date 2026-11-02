"""Sightengine (modèle `genai`) : probabilité qu'une image soit générée par IA."""
from __future__ import annotations

import base64

from ..config import get_settings
from .http import client, error_payload, skipped

URL = "https://api.sightengine.com/1.0/check.json"


async def detect_ai_image(image_base64: str | None = None, image_url: str | None = None) -> dict:
    """Envoie une image (base64 ou URL publique) au détecteur d'images générées."""
    s = get_settings()
    if not (s.sightengine_api_user and s.sightengine_api_secret):
        return skipped("Sightengine", "identifiants SIGHTENGINE_API_USER / SECRET absents")
    data = {"models": "genai", "api_user": s.sightengine_api_user, "api_secret": s.sightengine_api_secret}
    try:
        async with client(timeout=40) as http:
            if image_base64:
                files = {"media": ("image", base64.b64decode(image_base64))}
                resp = await http.post(URL, data=data, files=files)
            elif image_url:
                resp = await http.post(URL, data={**data, "url": image_url})
            else:
                return {"ok": False, "error": "Aucune image fournie", "items": []}
            resp.raise_for_status()
            payload = resp.json()
        if payload.get("status") != "success":
            return {"ok": False, "error": f"Sightengine : {payload.get('error', {}).get('message', 'échec')}", "items": []}
        return {"ok": True, "items": [{"ai_generated": float(payload.get("type", {}).get("ai_generated", 0.0))}]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Sightengine")
