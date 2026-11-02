"""Détection locale de contenus générés par IA.

Deux familles d'indices :
- signatures explicites, quasi certaines : métadonnées C2PA / IPTC « trainedAlgorithmicMedia »,
  paramètres de génération Stable Diffusion / ComfyUI, logiciel générateur dans l'EXIF ou les
  propriétés PDF/DOCX, formules d'assistant conversationnel ;
- indices statistiques (stylométrie), plafonnés car peu fiables seuls.

Les probabilités sont combinées par « OU bruité » : p = 1 - Π(1 - p_i).
"""
from __future__ import annotations

import io
import re
import statistics
from dataclasses import dataclass, field

from .textutils import split_sentences, tokens

STRONG_TEXT_PHRASES = [
    "en tant qu'ia", "en tant qu’ia", "en tant que modèle de langage", "en tant qu'intelligence artificielle",
    "en tant qu’intelligence artificielle", "je suis une intelligence artificielle", "je suis un modèle de langage",
    "as an ai language model", "as an ai model", "i am an ai language model", "as of my last knowledge update",
    "as of my last update", "my knowledge cutoff", "ma date limite de connaissances", "regenerate response",
    "je n'ai pas accès à internet en temps réel", "i don't have real-time access",
]

STYLE_MARKERS = [
    "il est important de noter", "il convient de noter", "dans un monde en constante évolution",
    "en conclusion,", "en résumé,", "en somme,", "plongeons", "n'hésitez pas à", "joue un rôle crucial",
    "jouent un rôle crucial", "un rôle essentiel", "une véritable mine", "tapisserie", "explorons ensemble",
    "dans le paysage", "it is important to note", "in today's fast-paced world", "delve into", "tapestry",
    "in conclusion,", "furthermore,", "moreover,", "plays a crucial role", "a testament to", "seamlessly",
    "navigate the complexities", "embark on", "unlock the potential", "ever-evolving",
]

ZERO_WIDTH = "\u200b\u200c\u200d\u2060\u2062\u2063\ufeff"

GENERATOR_NAMES = [
    "dall-e", "dall·e", "midjourney", "stable diffusion", "stablediffusion", "comfyui", "automatic1111",
    "novelai", "adobe firefly", "leonardo.ai", "ideogram", "openai", "chatgpt", "gpt-4", "gpt-5", "gemini",
    "google ai", "imagen", "claude", "copilot", "jasper", "bing image creator", "runway", "sora",
]

BYTE_SIGNATURES: list[tuple[bytes, float, str]] = [
    (b"trainedAlgorithmicMedia", 0.97, "Métadonnée IPTC « trainedAlgorithmicMedia » : image déclarée générée par IA"),
    (b"compositeWithTrainedAlgorithmicMedia", 0.85, "Métadonnée IPTC : image composite incluant de l'IA"),
    (b"c2pa.ai_generative_training", 0.6, "Assertion C2PA liée à l'IA générative"),
    (b"Midjourney", 0.9, "Signature Midjourney dans les métadonnées"),
    (b"DALL-E", 0.9, "Signature DALL·E dans les métadonnées"),
    (b"DALL\xc2\xb7E", 0.9, "Signature DALL·E dans les métadonnées"),
    (b"Stable Diffusion", 0.9, "Signature Stable Diffusion dans les métadonnées"),
    (b"ComfyUI", 0.9, "Signature ComfyUI dans les métadonnées"),
    (b"NovelAI", 0.9, "Signature NovelAI dans les métadonnées"),
    (b"Adobe Firefly", 0.85, "Signature Adobe Firefly dans les métadonnées"),
    (b"Made with Google AI", 0.9, "Mention « Made with Google AI » dans les métadonnées"),
    (b"Leonardo.Ai", 0.85, "Signature Leonardo.Ai dans les métadonnées"),
]


@dataclass
class AIResult:
    probability: float
    signals: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"probability": self.probability, "signals": self.signals}


def noisy_or(probabilities: list[float]) -> float:
    remaining = 1.0
    for p in probabilities:
        remaining *= 1.0 - max(0.0, min(1.0, p))
    return round(min(0.99, 1.0 - remaining), 2)


def text_signals(text: str) -> AIResult:
    raw = text or ""
    low = raw.lower()
    probs: list[float] = []
    signals: list[str] = []

    hits = [p for p in STRONG_TEXT_PHRASES if p in low]
    if hits:
        probs.append(0.97)
        signals.append(f"Formule typique d'un assistant IA : « {hits[0]} »")

    zw = sum(raw.count(c) for c in ZERO_WIDTH) - (1 if raw.startswith("\ufeff") else 0)
    if zw >= 3:
        probs.append(0.6)
        signals.append(f"{zw} caractères invisibles (filigrane textuel possible)")

    words = tokens(raw)
    if len(raw) < 280 or len(words) < 50:
        signals.append("Texte trop court pour une analyse stylométrique fiable")
        probs.append(0.05)
        return AIResult(noisy_or(probs), signals)

    style = 0.0
    lengths = [len(s.split()) for s in split_sentences(raw) if s.split()]
    if len(lengths) >= 5:
        mean = statistics.mean(lengths)
        cv = statistics.pstdev(lengths) / mean if mean else 1.0
        if cv < 0.35:
            style += 0.25
            signals.append("Phrases de longueur très régulière (faible variabilité)")
        elif cv < 0.5:
            style += 0.1

    markers = [m for m in STYLE_MARKERS if m in low]
    if markers:
        style += min(0.35, 0.12 * len(markers))
        signals.append("Tournures fréquentes chez les modèles de langage : " + ", ".join(f"« {m} »" for m in markers[:3]))

    if re.search(r"^\s*#{1,3} |\*\*[^*]+\*\*", raw, flags=re.M):
        style += 0.1
        signals.append("Mise en forme Markdown typique d'une réponse de chatbot")

    probs.append(min(0.8, 0.08 + style))
    if not signals:
        signals.append("Aucune signature IA détectée dans le texte")
    return AIResult(noisy_or(probs), signals)


def metadata_signals(values: dict[str, str | None], context: str = "document") -> AIResult:
    """Propriétés de fichier (PDF Producer/Creator, auteur DOCX, EXIF Software...)."""
    probs, signals = [], []
    for key, value in values.items():
        if not value:
            continue
        low = str(value).lower()
        for name in GENERATOR_NAMES:
            if name in low:
                probs.append(0.85)
                signals.append(f"Propriété « {key} » du {context} mentionne {name} : {str(value)[:60]}")
                break
    return AIResult(noisy_or(probs) if probs else 0.0, signals)


def image_signatures(data: bytes) -> AIResult:
    probs: list[float] = []
    signals: list[str] = []

    for needle, prob, message in BYTE_SIGNATURES:
        if needle in data:
            probs.append(prob)
            signals.append(message)
    if b"c2pa" in data and not any("C2PA" in s or "IPTC" in s for s in signals):
        probs.append(0.3)
        signals.append("Manifeste C2PA présent (à inspecter : il peut aussi provenir d'un appareil ou d'un logiciel d'édition)")

    try:
        from PIL import Image  # import local : Pillow est optionnel pour les tests

        with Image.open(io.BytesIO(data)) as im:
            info = {str(k).lower(): v for k, v in (im.info or {}).items()}
            if "parameters" in info:
                probs.append(0.95)
                signals.append("Paramètres de génération Stable Diffusion intégrés au PNG")
            if "prompt" in info or "workflow" in info:
                probs.append(0.9)
                signals.append("Prompt ou workflow ComfyUI intégré au PNG")
            exif = im.getexif()
            software = str(exif.get(305, "") or info.get("software", ""))
            meta = metadata_signals({"Software": software, "ImageDescription": str(exif.get(270, "") or "")}, "fichier image")
            if meta.probability:
                probs.append(meta.probability)
                signals.extend(meta.signals)
            if exif.get(271) or exif.get(272):
                signals.append(f"Métadonnées d'appareil photo présentes ({exif.get(271, '')} {exif.get(272, '')})".strip())
            else:
                probs.append(0.08)
                signals.append("Aucune métadonnée d'appareil photo (fréquent aussi après partage sur les réseaux sociaux)")
    except Exception:
        signals.append("Métadonnées de l'image illisibles")

    if not probs:
        probs.append(0.05)
    return AIResult(noisy_or(probs), signals)


def combine(local: AIResult, remote_probability: float | None, remote_label: str = "Détecteur externe") -> AIResult:
    if remote_probability is None:
        return local
    signals = list(local.signals) + [f"{remote_label} : {round(remote_probability * 100)} % de probabilité IA"]
    return AIResult(noisy_or([local.probability, remote_probability]), signals)
