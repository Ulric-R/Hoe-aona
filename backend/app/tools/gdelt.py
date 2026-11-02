"""GDELT DOC 2.0 : articles de presse mondiaux des trois derniers mois (sans clé).

Conditions d'utilisation : citer le GDELT Project (https://www.gdeltproject.org/).
"""
from __future__ import annotations

import re

from .http import client, error_payload

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
LANGS = {"fr": "french", "en": "english", "mg": "malagasy", "es": "spanish", "pt": "portuguese", "de": "german"}


def _clean_query(query: str) -> str:
    words = [w for w in re.findall(r"[\wÀ-ÿ]+", query) if len(w) > 2][:7]
    return " ".join(words)


async def search(query: str, language: str | None = None, timespan: str = "3months", max_records: int = 8) -> dict:
    """Recherche d'articles de presse récents correspondant aux mots-clés."""
    q = _clean_query(query)
    if not q:
        return {"ok": True, "items": []}
    if language in LANGS:
        q = f"{q} sourcelang:{LANGS[language]}"
    params = {"query": q, "mode": "ArtList", "format": "json", "maxrecords": max_records,
              "sort": "HybridRel", "timespan": timespan}
    try:
        async with client() as http:
            resp = await http.get(BASE, params=params)
            resp.raise_for_status()
            if "json" not in resp.headers.get("content-type", "") and not resp.text.lstrip().startswith("{"):
                return {"ok": False, "error": f"GDELT : {resp.text.strip()[:160]}", "items": []}
            data = resp.json() if resp.text.strip() else {}
        items = [{
            "url": a.get("url"),
            "title": a.get("title", ""),
            "domain": a.get("domain"),
            "seen_date": a.get("seendate"),
            "language": a.get("language"),
            "source_country": a.get("sourcecountry"),
            "image_url": a.get("socialimage") or None,
        } for a in data.get("articles", []) if a.get("url")]
        return {"ok": True, "items": items}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "GDELT")
