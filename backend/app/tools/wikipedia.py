"""Wikipedia : contexte encyclopédique, résumé et image de l'article (sans clé)."""
from __future__ import annotations

import asyncio
from urllib.parse import quote

from .http import client, error_payload


async def _summary(http, lang: str, title: str) -> dict | None:
    resp = await http.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}")
    if resp.status_code != 200:
        return None
    d = resp.json()
    if d.get("type") == "disambiguation":
        return None
    return {
        "title": d.get("title", title),
        "url": (d.get("content_urls") or {}).get("desktop", {}).get("page")
               or f"https://{lang}.wikipedia.org/wiki/{quote(title)}",
        "extract": d.get("extract", ""),
        "image_url": (d.get("thumbnail") or {}).get("source"),
        "last_modified": d.get("timestamp"),
        "language": lang,
    }


async def search(query: str, language: str = "fr", limit: int = 3) -> dict:
    """Cherche les articles Wikipedia les plus pertinents et renvoie leur résumé."""
    lang = language if language in {"fr", "en", "mg", "es", "de", "pt", "it"} else "fr"
    try:
        async with client() as http:
            resp = await http.get(f"https://{lang}.wikipedia.org/w/api.php", params={
                "action": "query", "list": "search", "srsearch": query[:300],
                "srlimit": limit, "format": "json", "utf8": 1,
            })
            resp.raise_for_status()
            titles = [r["title"] for r in resp.json().get("query", {}).get("search", [])]
            summaries = await asyncio.gather(*(_summary(http, lang, t) for t in titles))
        return {"ok": True, "items": [s for s in summaries if s]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Wikipedia")
