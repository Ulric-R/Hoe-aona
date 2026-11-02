"""Lecture sécurisée d'une page web : texte, auteur, date, image, logiciel générateur."""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .http import UnsafeURL, assert_public_url, client, error_payload

MAX_BYTES = 3_000_000


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _json_ld(soup: BeautifulSoup) -> dict:
    found: dict = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        nodes = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("datePublished") and "published_at" not in found:
                found["published_at"] = node["datePublished"]
            author = node.get("author")
            if author and "author" not in found:
                if isinstance(author, list):
                    author = author[0] if author else None
                found["author"] = author.get("name") if isinstance(author, dict) else str(author)
            publisher = node.get("publisher")
            if isinstance(publisher, dict) and publisher.get("name") and "publisher" not in found:
                found["publisher"] = publisher["name"]
    return found


def parse_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    ld = _json_ld(soup)
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "iframe"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for p in root.find_all(["p", "li", "blockquote"])]
    paragraphs = [p for p in paragraphs if len(p) > 40][:120]
    time_tag = soup.find("time")
    return {
        "url": url,
        "title": (_meta(soup, "og:title") or (soup.title.string if soup.title else "") or "").strip(),
        "site_name": _meta(soup, "og:site_name") or ld.get("publisher"),
        "author": _meta(soup, "author", "article:author", "dc.creator") or ld.get("author"),
        "published_at": _meta(soup, "article:published_time", "datePublished", "date", "dc.date", "pubdate")
                        or ld.get("published_at")
                        or (time_tag.get("datetime") if time_tag and time_tag.get("datetime") else None),
        "image_url": _meta(soup, "og:image", "twitter:image"),
        "generator": _meta(soup, "generator"),
        "description": _meta(soup, "og:description", "description"),
        "paragraphs": paragraphs,
        "text": "\n".join(paragraphs)[:20000],
    }


async def fetch(url: str) -> dict:
    """Télécharge une page publique et en extrait le contenu éditorial et les métadonnées."""
    try:
        await assert_public_url(url)
        async with client() as http:
            async with http.stream("GET", url) as resp:
                resp.raise_for_status()
                await assert_public_url(str(resp.url))
                ctype = resp.headers.get("content-type", "")
                if "html" not in ctype and "text" not in ctype:
                    return {"ok": False, "error": f"Contenu non textuel ({ctype or 'inconnu'})", "items": []}
                chunks, size = [], 0
                async for chunk in resp.aiter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_BYTES:
                        break
                html = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
                final_url = str(resp.url)
        page = parse_html(html, final_url)
        return {"ok": True, "items": [page]}
    except UnsafeURL as exc:
        return {"ok": False, "error": str(exc), "items": []}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Lecture de page")
