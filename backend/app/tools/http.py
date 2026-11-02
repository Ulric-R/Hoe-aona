"""Client HTTP partagé par les outils, avec garde-fou contre les requêtes vers le réseau interne."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from ..config import get_settings


class UnsafeURL(ValueError):
    pass


def client(timeout: float | None = None) -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(
        timeout=timeout or s.http_timeout,
        follow_redirects=True,
        headers={"User-Agent": s.user_agent, "Accept-Language": "fr,en;q=0.8"},
    )


async def assert_public_url(url: str) -> None:
    """Refuse les schémas autres que http(s) et les hôtes qui résolvent vers une IP privée."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURL("Seules les adresses http(s) publiques sont acceptées")
    host = parsed.hostname
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURL(f"Nom de domaine introuvable : {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeURL("Adresse interne refusée")


def error_payload(exc: Exception, source: str) -> dict:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        hint = {401: "clé refusée", 403: "accès refusé", 429: "quota gratuit atteint"}.get(code, "erreur du service")
        return {"ok": False, "error": f"{source} : {hint} (HTTP {code})", "items": []}
    if isinstance(exc, httpx.TimeoutException):
        return {"ok": False, "error": f"{source} : délai dépassé", "items": []}
    return {"ok": False, "error": f"{source} : {type(exc).__name__}: {exc}"[:300], "items": []}


def skipped(source: str, reason: str) -> dict:
    return {"ok": False, "skipped": True, "error": f"{source} : {reason}", "items": []}
