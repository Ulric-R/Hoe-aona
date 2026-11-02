"""Google Fact Check Tools API : vérifications déjà publiées par les fact-checkers (ClaimReview)."""
from __future__ import annotations

from ..config import get_settings
from .http import client, error_payload, skipped

BASE = "https://factchecktools.googleapis.com/v1alpha1"


def _items(claims: list[dict]) -> list[dict]:
    out = []
    for c in claims:
        for review in c.get("claimReview", []) or []:
            publisher = review.get("publisher") or {}
            out.append({
                "claim_text": c.get("text", ""),
                "claimant": c.get("claimant"),
                "claim_date": c.get("claimDate"),
                "url": review.get("url"),
                "title": review.get("title") or c.get("text", "")[:120],
                "publisher": publisher.get("name") or publisher.get("site") or "Fact-checker",
                "site": publisher.get("site"),
                "review_date": review.get("reviewDate"),
                "rating": review.get("textualRating"),
                "language": review.get("languageCode"),
            })
    return [i for i in out if i["url"]]


async def search(query: str, language: str = "fr", max_results: int = 6) -> dict:
    """Cherche des fact-checks publiés correspondant à une affirmation."""
    key = get_settings().google_factcheck_api_key
    if not key:
        return skipped("Google Fact Check", "clé GOOGLE_FACTCHECK_API_KEY absente")
    params = {"query": query[:500], "pageSize": max_results, "key": key}
    if language:
        params["languageCode"] = language
    try:
        async with client() as http:
            resp = await http.get(f"{BASE}/claims:search", params=params)
            resp.raise_for_status()
            items = _items(resp.json().get("claims", []))
            if not items and language:  # deuxième essai sans filtre de langue
                params.pop("languageCode")
                resp = await http.get(f"{BASE}/claims:search", params=params)
                resp.raise_for_status()
                items = _items(resp.json().get("claims", []))
        return {"ok": True, "items": items[:max_results]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Google Fact Check")


async def image_search(image_url: str, max_results: int = 6) -> dict:
    """Cherche des fact-checks portant sur une image publique (URL)."""
    key = get_settings().google_factcheck_api_key
    if not key:
        return skipped("Google Fact Check (image)", "clé GOOGLE_FACTCHECK_API_KEY absente")
    try:
        async with client() as http:
            resp = await http.get(f"{BASE}/claims:imageSearch",
                                  params={"imageUri": image_url, "pageSize": max_results, "key": key})
            resp.raise_for_status()
            data = resp.json()
        claims = [r.get("claim", r) for r in data.get("results", [])]
        return {"ok": True, "items": _items(claims)[:max_results]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Google Fact Check (image)")
