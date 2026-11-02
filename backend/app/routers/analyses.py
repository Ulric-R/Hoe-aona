"""Routes des analyses : création (multipart), suivi, historique, article."""
from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from ..config import get_settings
from ..db import get_db
from ..schemas import AnalysisOut, AnalysisPage, AnalysisResult, Article
from ..services import article as article_service
from ..services.llm import LLMClient
from ..services.pipeline import load_preferences, run_analysis
from ..services.textutils import truncate

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

KINDS = {
    "image": {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic"},
    "document": {"application/pdf", "text/plain", "text/markdown", "text/html",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "audio": {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg",
              "audio/mp4", "audio/x-m4a", "audio/m4a", "video/webm"},
}
EXTENSIONS = {
    "image": (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"),
    "document": (".pdf", ".txt", ".md", ".html", ".htm", ".docx"),
    "audio": (".mp3", ".wav", ".webm", ".ogg", ".m4a", ".mp4"),
}


def _kind_of(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    ctype = (upload.content_type or "").split(";")[0]
    for kind in ("image", "document", "audio"):
        if ctype in KINDS[kind] or name.endswith(EXTENSIONS[kind]):
            return kind
    raise HTTPException(415, f"Type de fichier non pris en charge : {upload.filename} ({ctype or 'inconnu'})")


def _parse_urls(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    try:
        values = json.loads(raw)
        values = values if isinstance(values, list) else [values]
    except ValueError:
        values = re.split(r"[\s,]+", raw)
    urls = [str(v).strip() for v in values if str(v).strip()]
    bad = [u for u in urls if not re.match(r"^https?://", u)]
    if bad:
        raise HTTPException(422, f"Lien invalide (http ou https attendu) : {bad[0]}")
    return urls[:10]


def _to_out(record: dict) -> AnalysisOut:
    return AnalysisOut(**{k: record.get(k) for k in AnalysisOut.model_fields if k != "result"},
                       result=AnalysisResult(**record["result"]) if record.get("result") else None)


@router.post("", response_model=AnalysisOut, status_code=202)
async def create_analysis(
    background: BackgroundTasks,
    text: str = Form(""),
    urls: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    settings = get_settings()
    url_list = _parse_urls(urls)
    if not text.strip() and not files and not url_list:
        raise HTTPException(422, "Ajoutez au moins un texte, un fichier ou un lien à analyser")
    if len(text) > 50_000:
        raise HTTPException(413, "Texte trop long (50 000 caractères maximum)")
    if len(files) > 6:
        raise HTTPException(413, "6 fichiers maximum par analyse")

    analysis_id = uuid.uuid4().hex[:16]
    folder = settings.data_dir / "uploads" / analysis_id
    inputs: list[dict] = []
    if text.strip():
        inputs.append({"kind": "text", "text": text.strip()})
    for url in url_list:
        inputs.append({"kind": "url", "url": url})

    max_bytes = settings.max_upload_mb * 1024 * 1024
    for upload in files:
        kind = _kind_of(upload)
        folder.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.\-]", "_", Path(upload.filename or "fichier").name)[:80]
        dest = folder / f"{len(inputs)}_{safe}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        if dest.stat().st_size > max_bytes:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(413, f"{upload.filename} dépasse {settings.max_upload_mb} Mo")
        inputs.append({"kind": kind, "path": str(dest), "name": upload.filename or safe,
                       "mime": upload.content_type or "application/octet-stream"})

    first = inputs[0]
    title = truncate(first.get("text") or first.get("name") or first.get("url") or "Analyse", 80)
    kinds = {i["kind"] for i in inputs}
    input_kind = kinds.pop() if len(kinds) == 1 else "mixte"
    get_db().create_analysis(title, input_kind, inputs, analysis_id)
    background.add_task(run_analysis, analysis_id)
    return _to_out(get_db().get_analysis(analysis_id))


@router.get("", response_model=AnalysisPage)
async def list_analyses(q: str = "", verdict: str | None = None,
                        limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    items, total = get_db().list_analyses(q.strip(), verdict, limit, offset)
    return {"items": items, "total": total}


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(analysis_id: str):
    record = get_db().get_analysis(analysis_id)
    if not record:
        raise HTTPException(404, "Analyse introuvable")
    return _to_out(record)


@router.delete("/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str):
    if not get_db().delete_analysis(analysis_id):
        raise HTTPException(404, "Analyse introuvable")
    shutil.rmtree(get_settings().data_dir / "uploads" / analysis_id, ignore_errors=True)


def _result(analysis_id: str) -> AnalysisResult:
    record = get_db().get_analysis(analysis_id)
    if not record or not record.get("result"):
        raise HTTPException(404, "Résultat indisponible")
    return AnalysisResult(**record["result"])


@router.post("/{analysis_id}/article", response_model=Article)
async def regenerate_article(analysis_id: str):
    result = _result(analysis_id)
    warnings: list[str] = []
    result.article = await article_service.generate(result, LLMClient(), load_preferences().report_language, warnings)
    get_db().update_analysis(analysis_id, result=result.model_dump(mode="json"))
    return result.article


@router.get("/{analysis_id}/article.md", response_class=PlainTextResponse)
async def article_markdown(analysis_id: str):
    result = _result(analysis_id)
    if not result.article:
        raise HTTPException(404, "Article non généré")
    return PlainTextResponse(article_service.to_markdown(result.article), media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="verification-{analysis_id}.md"'})


@router.get("/{analysis_id}/article.html", response_class=HTMLResponse)
async def article_html(analysis_id: str):
    result = _result(analysis_id)
    if not result.article:
        raise HTTPException(404, "Article non généré")
    return HTMLResponse(article_service.to_html(result.article),
                        headers={"Content-Disposition": f'attachment; filename="verification-{analysis_id}.html"'})
