"""Fonctions de texte pures (aucune dépendance réseau), testables isolément."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from urllib.parse import urlparse

STOPWORDS = set("""
a à au aux avec ce ces cet cette dans de des du elle elles en et eux il ils je la le les leur leurs lui
ma mais me même mes moi mon ne nos notre nous on ou où par pas pour qu que qui sa se ses son sur ta te
tes toi ton tu un une vos votre vous c d j l m n s t y ete etre avoir fait est sont etait ont plus moins
tres tout tous toute toutes selon depuis entre sans sous vers chez ainsi alors donc car comme si cela ceci
aussi encore deja apres avant lors dont sera seront peut peuvent doit doivent quand
the of and to in is are was were be been for on with that this it as by at from or an has have had not
but which their its will would can could about into than then there these those they them his her
""".split())


def normalize(text: str | None) -> str:
    return unicodedata.normalize("NFKC", text or "").strip()


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", strip_accents((text or "").lower()))


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if (len(t) > 2 or t.isdigit()) and t not in STOPWORDS]


def keywords(text: str, max_words: int = 8) -> list[str]:
    """Mots-clés par fréquence puis ordre d'apparition ; les nombres et noms propres sont favorisés."""
    words = re.findall(r"[\wÀ-ÿ’'-]+", text or "")
    proper = {strip_accents(w.lower()) for w in words[1:] if w[:1].isupper()}
    toks = content_tokens(text)
    counts = Counter(toks)
    first = {}
    for i, t in enumerate(toks):
        first.setdefault(t, i)
    ranked = sorted(counts, key=lambda t: (-(counts[t] + (1.5 if t in proper or t.isdigit() else 0)), first[t]))
    return ranked[:max_words]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?…])\s+(?=[A-ZÀ-Ý0-9«\"“])", text)
    return [p.strip() for p in parts if len(p.strip()) > 1]


def overlap(reference: str, candidate: str) -> float:
    """Part des mots porteurs de sens de `reference` présents dans `candidate` (0 à 1)."""
    ref = set(content_tokens(reference))
    if not ref:
        return 0.0
    cand = set(content_tokens(candidate))
    return len(ref & cand) / len(ref)


def truncate(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def best_excerpt(paragraphs: list[str], claim: str, max_chars: int = 420) -> tuple[str, float]:
    """Retourne le paragraphe (ou la fenêtre de phrases) le plus proche de l'affirmation."""
    best, best_score = "", 0.0
    for para in paragraphs:
        para = para.strip()
        if len(para) < 40:
            continue
        sentences = split_sentences(para) or [para]
        # Fenêtres de 1 à 3 phrases pour garder un extrait court et ciblé.
        for size in (1, 2, 3):
            for i in range(0, max(1, len(sentences) - size + 1)):
                window = " ".join(sentences[i:i + size])
                score = overlap(claim, window) - (0.02 * (size - 1))
                if score > best_score:
                    best, best_score = window, score
    return truncate(best, max_chars), round(max(best_score, 0.0), 3)


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def numbers_in(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,\u202f\u00a0 ]\d+)*", text or "")
