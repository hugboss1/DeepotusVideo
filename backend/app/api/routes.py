"""FastAPI route definitions — v1.3 (batch multi-seeds)."""
import asyncio
import json
import random
import re
from pathlib import Path
from uuid import uuid4

import httpx

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.responses import FileResponse
from PIL import Image as PILImage
from loguru import logger

from app.config import settings, APP_VERSION, SSL_VERIFY
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateBatchRequest,
    GenerateBatchResponse,
    GenerateHeyGenRequest,
    CompositionRequest,
    CompositionResponse,
    JobStatus,
    ImageItem,
    BuildPromptRequest,
    BuildPromptResponse,
    HeyGenAvatar,
    HeyGenVoice,
    PhotoAvatarCreateResponse,
    BuildScriptRequest,
    BuildScriptResponse,
    BuildCompositionRequest,
    BuildCompositionResponse,
    TemplateSaveRequest,
    TemplateSaveResponse,
    TemplateRenderRequest,
    TemplateRenderResponse,
    JobRenameRequest,
    AddNewsSourceRequest,
    NewsSourceToggleRequest,
    NewsScriptRequest,
    NewsScriptResponse,
    NewsEssence,
    NewsIllustrationRequest,
    NewsIllustrationResponse,
)
from app.services.pipeline import Pipeline
from app.services.heygen_service import HeyGenClient, HeyGenError, invalidate_list_cache
from app.services.template_service import TemplateEngine
from app.services.news_service import news_service


router = APIRouter()
pipeline = Pipeline(persona_id="deepotus")
template_engine = TemplateEngine()


# ---- Templates ----

@router.get("/templates")
async def list_templates():
    return {
        "persona": pipeline.engine.persona["display_name"],
        "templates": [t.model_dump() for t in pipeline.engine.list_templates()],
    }


@router.get("/persona")
async def get_persona():
    return pipeline.engine.persona


# ---- v1.6: Layout Templates (node system) ----
# NOTE: namespaced under /layout-templates to avoid colliding with the
# existing /templates endpoint (Seedance prompt templates).

@router.get("/layout-templates")
async def list_layout_templates():
    """List all layout templates (built-in + user-created)."""
    return {"templates": template_engine.list_templates()}


@router.get("/layout-templates/{template_id}")
async def get_layout_template(template_id: str):
    try:
        return template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")


@router.get("/layout-templates/{template_id}/slots")
async def list_layout_template_slots(template_id: str):
    try:
        return {"slots": template_engine.list_slots(template_id)}
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")


@router.post("/layout-templates", response_model=TemplateSaveResponse)
async def save_layout_template(request: TemplateSaveRequest):
    try:
        tid = template_engine.save_template(request.template)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return TemplateSaveResponse(template_id=tid, message="Saved")


@router.delete("/layout-templates/{template_id}")
async def delete_layout_template(template_id: str):
    result = template_engine.delete_template(template_id)
    if result == "builtin":
        raise HTTPException(400, "Built-in templates cannot be deleted")
    if result == "missing":
        raise HTTPException(404, f"Template not found: {template_id}")
    return {"deleted": template_id}

@router.post("/layout-templates/{template_id}/render",
             response_model=TemplateRenderResponse)
async def render_layout_template(
    template_id: str,
    request: TemplateRenderRequest,
    background_tasks: BackgroundTasks,
):
    """Render a layout template with filled slots.

    Seedance/HeyGen slots are generated in parallel via the existing pipeline,
    upload/file slots used as-is, text slots drawn directly. All slots resolve,
    then ffmpeg composites them. Poll GET /api/jobs/{job_id} for progress.
    """
    # Inline template (unsaved editor edits) renders as-is; otherwise the
    # saved template must exist.
    if request.template is None:
        try:
            template_engine.get_template(template_id)
        except FileNotFoundError:
            raise HTTPException(404, f"Template not found: {template_id}")
    else:
        try:
            template_engine._validate(request.template)
        except ValueError as e:
            raise HTTPException(400, f"Invalid template: {e}")

    kinds = {sv.source_kind for sv in request.slot_values.values()}
    if "seedance" in kinds and not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it to backend/.env")
    if "heygen" in kinds and not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured. Add it to backend/.env")

    job_id = str(uuid4())

    if request.source_graph:
        try:
            import json as _json
            gdir = settings.outputs_path / "_graphs"
            gdir.mkdir(parents=True, exist_ok=True)
            (gdir / f"{job_id}.json").write_text(
                _json.dumps(request.source_graph, ensure_ascii=False),
                encoding="utf-8")
        except Exception as e:
            logger.warning(f"source_graph save failed for {job_id}: {e}")

    async def _run():
        try:
            await pipeline.render_template(
                template_id=template_id,
                slot_values=request.slot_values,
                voice_mode=request.voice_mode,
                job_id=job_id,
                template=request.template,
                title=request.title,
            )
        except Exception as e:
            logger.exception(f"Template render {job_id} failed: {e}")

    background_tasks.add_task(_run)
    return TemplateRenderResponse(
        template_id=template_id,
        job_id=job_id,
        message=f"Template render queued. Poll GET /api/jobs/{job_id}.",
    )


@router.get("/jobs/{job_id}/graph")
async def get_job_graph(job_id: str):
    """The Studio node graph that produced this render (saved at render time),
    for "Reopen in Studio". 404 if the render had no stored graph (older
    renders, or non-Studio producers)."""
    import json as _json
    safe = Path(job_id).name
    p = settings.outputs_path / "_graphs" / f"{safe}.json"
    if not p.is_file():
        raise HTTPException(404, "No source graph for this render")
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "Graph unreadable")


# ── Studio named-graph store (v1.15.6): save / reload node graphs by name,
# separate from the render-time source_graph dump. Lives in the data dir
# (DATA_ROOT/assets/studio_graphs) so it survives updates/reinstalls.
def _studio_graphs_dir():
    d = settings.outputs_path.parent / "studio_graphs"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.get("/studio-graphs")
async def list_studio_graphs():
    """Saved Studio graphs (metadata only, newest first)."""
    import json as _json
    out = []
    for f in _studio_graphs_dir().glob("*.json"):
        try:
            d = _json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": d.get("id", f.stem),
                        "name": d.get("name", f.stem),
                        "updated_at": d.get("updated_at")})
        except Exception:
            continue
    out.sort(key=lambda g: g.get("updated_at") or "", reverse=True)
    return {"graphs": out}


@router.get("/studio-graphs/{graph_id}")
async def get_studio_graph(graph_id: str):
    import json as _json
    p = _studio_graphs_dir() / f"{Path(graph_id).name}.json"
    if not p.is_file():
        raise HTTPException(404, "Graph not found")
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "Graph unreadable")


@router.post("/studio-graphs")
async def save_studio_graph(body: dict, request: Request):
    """Save or overwrite a named Studio graph. Body: {id?, name, graph}."""
    _require_localhost(request)
    import json as _json
    from datetime import datetime as _dtnow
    graph = body.get("graph")
    if not isinstance(graph, dict) or not graph.get("nodes"):
        raise HTTPException(400, "graph (with nodes) is required")
    gid = (str(body.get("id") or "").strip()) or f"g_{uuid4().hex[:8]}"
    gid = Path(gid).name
    name = (str(body.get("name") or graph.get("name") or "Untitled graph").strip())[:120]
    rec = {"id": gid, "name": name, "graph": graph,
           "updated_at": _dtnow.utcnow().isoformat()}
    (_studio_graphs_dir() / f"{gid}.json").write_text(
        _json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return {"id": gid, "name": name}


@router.delete("/studio-graphs/{graph_id}")
async def delete_studio_graph(graph_id: str):
    p = _studio_graphs_dir() / f"{Path(graph_id).name}.json"
    if not p.is_file():
        raise HTTPException(404, "Graph not found")
    p.unlink()
    return {"deleted": graph_id}


@router.get("/emojis")
async def list_emojis():
    """Curated native emoji set (categories -> [{e: char, f: png basename}])
    for the Studio emoji picker. PNGs are served at /emoji/<f>.png and used by
    the renderer (Twemoji overlay) so picker and video match."""
    import json
    from pathlib import Path as _P
    p = _P(__file__).resolve().parent.parent / "assets" / "emoji" / "manifest.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _emoji_custom_dir() -> Path:
    from app.config import DATA_ROOT
    p = DATA_ROOT / "assets" / "emoji_custom"
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.get("/emojis/custom")
async def list_custom_emojis():
    """User-imported custom emojis (stored in the data dir). Each entry ->
    {name, file, url, code}. The picker inserts `code` (:name:) into ticker /
    text-overlay text; the renderer resolves it to the PNG so video matches."""
    d = _emoji_custom_dir()
    out = [{"name": f.stem, "file": f.name,
            "url": f"/emoji-custom/{f.name}", "code": f":{f.stem}:"}
           for f in sorted(d.glob("*.png"))]
    return {"emojis": out}


@router.post("/emojis/custom")
async def upload_custom_emoji(request: Request,
                             file: UploadFile = File(...),
                             name: str = Form("")):
    """Import a custom emoji image -> RGBA PNG (<=160px) in the data dir under a
    :shortcode: from `name` (or the filename). Survives app reinstall."""
    _require_localhost(request)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        raise HTTPException(400, "Emoji must be .png, .jpg, .webp or .gif")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 5 MB)")
    base = _slug(name or Path(file.filename or "emoji").stem) or "emoji"
    d = _emoji_custom_dir()
    nm, i = base, 2
    while (d / (nm + ".png")).exists():
        nm = f"{base}-{i}"
        i += 1
    try:
        import io
        from PIL import Image as PILImg
        img = PILImg.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail((160, 160), PILImg.LANCZOS)
        img.save(d / (nm + ".png"), format="PNG")
    except Exception as e:
        raise HTTPException(400, f"Not a valid image: {e}")
    logger.info(f"custom emoji imported: {nm}")
    return {"name": nm, "file": nm + ".png",
            "url": f"/emoji-custom/{nm}.png", "code": f":{nm}:"}


@router.delete("/emojis/custom/{name}")
async def delete_custom_emoji(name: str, request: Request):
    _require_localhost(request)
    p = _emoji_custom_dir() / (_slug(name) + ".png")
    if p.exists():
        try:
            p.unlink()
        except Exception as e:
            raise HTTPException(500, f"Could not delete: {e}")
    return {"ok": True, "name": _slug(name)}


# ---- v1.7: News / RSS pipeline ----

@router.get("/news/sources")
async def list_news_sources():
    return {"sources": news_service.list_sources()}


@router.post("/news/sources")
async def add_news_source(request: AddNewsSourceRequest):
    try:
        src = news_service.add_source(
            request.url, request.name, request.type)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"source": src}


@router.delete("/news/sources/{source_id}")
async def delete_news_source(source_id: str):
    if not news_service.remove_source(source_id):
        raise HTTPException(404, f"Source not found: {source_id}")
    return {"deleted": source_id}


@router.post("/news/sources/{source_id}/toggle")
async def toggle_news_source(source_id: str, request: NewsSourceToggleRequest):
    if not news_service.set_enabled(source_id, request.enabled):
        raise HTTPException(404, f"Source not found: {source_id}")
    return {"source_id": source_id, "enabled": request.enabled}


@router.post("/news/sources/defaults")
async def seed_default_news_sources():
    """Add the curated default feed pack (crypto / geopolitics / economy /
    politics EU·China·USA). Idempotent — skips sources already present."""
    return news_service.seed_defaults()


@router.post("/news/refresh")
async def refresh_news():
    try:
        return await news_service.refresh()
    except Exception as e:
        logger.exception("news refresh failed")
        raise HTTPException(500, f"Refresh failed: {e}")


@router.get("/news/items")
async def list_news_items():
    return news_service.get_items()


@router.post("/news/script", response_model=NewsScriptResponse)
async def generate_news_script_route(request: NewsScriptRequest):
    """Read the selected articles (when read_articles), extract the essence
    + lead images (saved to assets/images for Seedance), then render a
    deepotus 'prophet' (cynical/humorous) script + caption."""
    try:
        items = [i.model_dump() for i in request.items]
        essences: list[NewsEssence] = []
        images: list[str] = []
        if request.read_articles:
            items = await news_service.enrich_items(
                items, summary_words=request.summary_words)
            for it in items:
                if it.get("image"):
                    images.append(it["image"])
                essences.append(NewsEssence(
                    title=it.get("title", ""),
                    essence=it.get("essence", ""),
                    image=it.get("image"),
                    link=it.get("link", ""),
                    status=it.get("scrape_status", ""),
                ))
        base = await asyncio.to_thread(
            pipeline.engine.generate_news_script,
            items,
            voice_mode=request.voice_mode,
            language=request.language,
            max_words=request.max_words,
            angle=request.angle,
        )
        return NewsScriptResponse(
            **base.model_dump(),
            sources_read=len(essences),
            images=images,
            essences=essences,
        )
    except Exception as e:
        logger.exception("news script generation failed")
        raise HTTPException(500, f"Script generation failed: {e}")


@router.post("/news/illustration", response_model=NewsIllustrationResponse)
async def generate_news_illustration_route(
    request: NewsIllustrationRequest,
    background_tasks: BackgroundTasks,
):
    """Render a branded 1080x1920 news-illustration reel from selected items.
    Silent (the avatar carries audio when composed). Poll GET /api/jobs."""
    job_id = str(uuid4())

    async def _run():
        try:
            await pipeline.run_news_illustration(
                [i.model_dump() for i in request.items],
                per_card_s=request.per_card_s,
                engine=request.engine,
                job_id=job_id,
            )
        except Exception as e:
            logger.exception(f"news illustration {job_id} failed: {e}")

    background_tasks.add_task(_run)
    return NewsIllustrationResponse(
        job_id=job_id,
        message=f"News illustration queued. Poll GET /api/jobs/{job_id}.",
    )


# ---- Images ----

@router.get("/images")
async def list_images():
    folder = settings.images_path
    if not folder.exists():
        return {"folder": str(folder), "images": [], "warning": "Folder does not exist"}

    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    items: list[ImageItem] = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in extensions:
            try:
                with PILImage.open(p) as img:
                    width, height = img.size
            except Exception:
                width = height = None
            items.append(ImageItem(
                filename=p.name,
                path=str(p),
                size_kb=p.stat().st_size // 1024,
                width=width,
                height=height,
            ))
    return {"folder": str(folder), "images": [i.model_dump() for i in items]}


@router.post("/images/upload")
async def upload_image(file: UploadFile = File(...)):
    folder = settings.images_path
    folder.mkdir(parents=True, exist_ok=True)
    safe = Path(file.filename or "image.png").name
    if not safe or safe in (".", "..") or "/" in safe or "\\" in safe:
        raise HTTPException(400, "Invalid filename")
    dest = folder / safe
    contents = await file.read()
    dest.write_bytes(contents)
    return {"saved": str(dest), "filename": safe, "size_kb": len(contents) // 1024}


@router.get("/images/{filename}")
async def get_image_file(filename: str):
    safe = Path(filename).name
    p = settings.images_path / safe
    try:
        if not str(p.resolve()).startswith(str(settings.images_path.resolve())) \
                or not p.is_file():
            raise HTTPException(404, f"Image not found: {filename}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Image not found: {filename}")
    return FileResponse(p)


@router.delete("/images/{filename}")
async def delete_image_file(filename: str):
    """Delete a generated/uploaded image from the images folder."""
    safe = Path(filename).name
    p = settings.images_path / safe
    try:
        if not str(p.resolve()).startswith(str(settings.images_path.resolve())) \
                or not p.is_file():
            raise HTTPException(404, f"Image not found: {filename}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Image not found: {filename}")
    p.unlink()
    return {"deleted": safe}


_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}


def _audio_dir() -> Path:
    """User audio assets (music / SFX / voice), in the stable data dir."""
    p = settings.images_path.parent / "audio"
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.get("/audio")
async def list_audio():
    """List uploaded audio assets for the Library + Studio audio nodes."""
    d = _audio_dir()
    out = []
    for p in sorted(d.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True):
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTS:
            out.append({"name": p.name, "url": f"/api/audio/{p.name}",
                        "size_kb": p.stat().st_size // 1024})
    return {"audio": out}


@router.post("/audio/upload")
async def upload_audio(file: UploadFile = File(...)):
    folder = _audio_dir()
    safe = Path(file.filename or "audio.mp3").name
    if not safe or safe in (".", "..") or "/" in safe or "\\" in safe:
        raise HTTPException(400, "Invalid filename")
    if Path(safe).suffix.lower() not in _AUDIO_EXTS:
        raise HTTPException(400, "Unsupported audio format")
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(400, "Audio too large (max 50 MB)")
    dest = folder / safe
    dest.write_bytes(contents)
    return {"saved": str(dest), "filename": safe, "size_kb": len(contents) // 1024}


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    safe = Path(filename).name
    p = _audio_dir() / safe
    try:
        if not str(p.resolve()).startswith(str(_audio_dir().resolve())) \
                or not p.is_file():
            raise HTTPException(404, f"Audio not found: {filename}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404, f"Audio not found: {filename}")
    return FileResponse(p)


@router.delete("/audio/{filename}")
async def delete_audio_file(filename: str):
    safe = Path(filename).name
    p = _audio_dir() / safe
    if not p.is_file():
        raise HTTPException(404, f"Audio not found: {filename}")
    p.unlink()
    return {"deleted": safe}


@router.post("/audio/voiceover")
async def create_voiceover(request: Request):
    """Synthesize a voiceover (ElevenLabs) and save it as a reusable audio asset.

    Used by Quick's "voix off seule" mode: the script is spoken by the app voice
    engine and the .mp3 lands in the Library audio dir, selectable in audio nodes.
    Body: {script, language?: "en"|"fr", name?}.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    script = (payload.get("script") or "").strip()
    if not script:
        raise HTTPException(400, "Empty script")
    from app.services.elevenlabs_service import VoiceoverService
    voice = VoiceoverService()
    if not voice.is_enabled():
        raise HTTPException(400, "ElevenLabs voice not configured — add the API key in Settings.")
    voice_id = (payload.get("voice_id") or "").strip() or None
    lang = str(payload.get("language") or "en").lower()
    if lang not in ("en", "fr"):
        lang = "en"
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", str(payload.get("name") or "narration")).strip("_")[:40]
    fn = f"{base or 'narration'}-{random.randint(100000, 999999)}.mp3"
    dest = _audio_dir() / fn
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: voice.generate_long(text=script, output_path=dest,
                                              language=lang, voice_id=voice_id))
    except Exception as e:
        raise HTTPException(502, f"Voiceover failed: {e}")
    if not dest.is_file():
        raise HTTPException(502, "Voiceover produced no file")
    return {"ok": True, "filename": fn, "url": f"/api/audio/{fn}",
            "size_kb": dest.stat().st_size // 1024}


@router.get("/voices")
async def list_voices():
    """List ElevenLabs voices for the Episodes / voiceover voice picker."""
    if not settings.has_voiceover:
        return {"voices": [], "enabled": False}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://api.elevenlabs.io/v1/voices",
                            headers={"xi-api-key": settings.ELEVENLABS_API_KEY})
            r.raise_for_status()
            data = r.json()
        out = []
        for v in (data.get("voices") or []):
            lbl = v.get("labels") or {}
            out.append({
                "voice_id": v.get("voice_id"),
                "name": v.get("name"),
                "category": v.get("category"),
                "language": lbl.get("language") or lbl.get("accent"),
                "labels": lbl,
                "preview_url": v.get("preview_url"),
            })
        return {"voices": out, "enabled": True}
    except Exception as e:
        logger.warning(f"ElevenLabs voices fetch failed: {e}")
        return {"voices": [], "enabled": True, "error": str(e)}


@router.post("/episodes/extract-text")
async def extract_chapter_text(file: UploadFile = File(...)):
    """Extract plain text from an uploaded chapter file (.txt / .docx / .pdf)
    for the Episodes narration. Returns {text, words, chars}."""
    import io as _io
    name = (file.filename or "").lower()
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 25 MB)")
    text = ""
    try:
        if name.endswith(".docx"):
            import docx
            doc = docx.Document(_io.BytesIO(data))
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(_io.BytesIO(data))
            parts = []
            for pg in reader.pages:
                t = (pg.extract_text() or "").strip()
                if t:
                    parts.append(t)
            text = "\n\n".join(parts)
        else:  # .txt or unknown → decode as plain text
            for enc in ("utf-8", "utf-8-sig", "latin-1"):
                try:
                    text = data.decode(enc)
                    break
                except Exception:
                    continue
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f"Could not read this file: {e}")
    text = (text or "").strip()
    if not text:
        raise HTTPException(
            422, "No selectable text found (a scanned PDF is an image — export a text PDF).")
    return {"text": text, "words": len(text.split()), "chars": len(text)}


def _scene_prompt_from(text: str, limit: int = 160) -> str:
    """Rough illustration prompt for paragraph mode: the first sentence."""
    m = re.split(r"(?<=[.!?…])\s", text.strip(), maxsplit=1)
    s = (m[0] if m else text).strip()
    return (s[:limit].rstrip() + "…") if len(s) > limit else s


def _paragraph_scenes(script: str) -> list[dict]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", script) if p.strip()]
    if len(paras) <= 1:  # no blank-line paragraphs → fall back to single lines
        paras = [p.strip() for p in script.splitlines() if p.strip()]
    return [{"text": p, "illustration_prompt": _scene_prompt_from(p)}
            for p in paras[:60]]


def _ai_scenes(script: str, lang: str) -> list[dict]:
    from app.services.summarizer import _chat_dispatch
    langname = "French" if lang.startswith("fr") else "English"
    n = max(3, min(12, len(script.split()) // 80 + 1))
    system = ("You are a storyboard director for DEEPOTUS, a deep-sea / abyssal "
              "themed brand. You split a narrated novel chapter into visual scenes "
              "and write a vivid image prompt for each. Return ONLY valid JSON.")
    prompt = (
        f"Split this chapter into about {n} sequential scenes for a narrated video. "
        f"For each scene return: \"text\" = the chapter text for that scene, COPIED "
        f"VERBATIM and in order so concatenating all texts reproduces the chapter; "
        f"and \"illustration_prompt\" = a vivid cinematic image prompt in {langname} "
        f"(deep-sea, bioluminescent, atmospheric). Return ONLY a JSON array "
        f"[{{\"text\":\"...\",\"illustration_prompt\":\"...\"}}].\n\nChapter:\n{script[:12000]}")
    out, _prov = _chat_dispatch(prompt, system, 4000)
    if not out:
        return []
    txt = out.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```$", "", txt).strip()
    i, j = txt.find("["), txt.rfind("]")
    if i >= 0 and j > i:
        txt = txt[i:j + 1]
    try:
        data = json.loads(txt)
    except Exception:
        return []
    scenes = []
    for it in (data if isinstance(data, list) else []):
        if isinstance(it, dict) and str(it.get("text") or "").strip():
            scenes.append({"text": str(it["text"]).strip(),
                           "illustration_prompt": str(it.get("illustration_prompt") or "").strip()})
    return scenes


@router.post("/episodes/scenes")
async def episode_scenes(request: Request):
    """Split a chapter into scenes for the storyboard.
    Body: {script, language?, method:"paragraph"|"ai"}.
    Returns {scenes:[{text, illustration_prompt}], method, count}."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    script = (payload.get("script") or "").strip()
    if not script:
        raise HTTPException(400, "Empty script")
    method = (payload.get("method") or "paragraph").lower()
    lang = str(payload.get("language") or "en").lower()
    if method == "ai":
        from app.services.summarizer import available
        if not available():
            return {"scenes": [], "method": "ai",
                    "error": "Aucun LLM configuré (Réglages → clés API). Utilise le découpage par paragraphe."}
        loop = asyncio.get_running_loop()
        scenes = await loop.run_in_executor(None, lambda: _ai_scenes(script, lang))
        if not scenes:
            return {"scenes": [], "method": "ai",
                    "error": "Le découpage IA a échoué — réessaie, ou utilise les paragraphes."}
        return {"scenes": scenes, "method": "ai", "count": len(scenes)}
    scenes = _paragraph_scenes(script)
    return {"scenes": scenes, "method": "paragraph", "count": len(scenes)}


@router.post("/episodes/render")
async def render_episode(request: Request, background_tasks: BackgroundTasks):
    """Assemble a narrated illustrated episode (per-scene TTS narration + Ken
    Burns / still over each scene's image, concatenated into one 9:16 video).
    Returns a job_id; poll GET /api/jobs/{job_id}.
    Body: {title, voice_id, language, scenes:[{text, image_filename, motion}]}."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    scenes = payload.get("scenes") or []
    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(400, "No scenes to render")
    if not any((s.get("text") or "").strip() for s in scenes if isinstance(s, dict)):
        raise HTTPException(400, "Scenes have no narration text")
    if not settings.has_voiceover:
        raise HTTPException(400, "ElevenLabs voice not configured — add the API key in Settings.")
    job_id = str(uuid4())

    async def _run():
        try:
            await pipeline.run_episode(
                job_id=job_id, title=payload.get("title"),
                voice_id=(payload.get("voice_id") or "").strip() or None,
                language=str(payload.get("language") or "en"),
                scenes=scenes)
        except Exception as e:
            logger.exception(f"Episode render {job_id} failed: {e}")

    background_tasks.add_task(_run)
    return {"ok": True, "job_id": job_id,
            "message": f"Episode render queued. Poll GET /api/jobs/{job_id}."}


@router.post("/videos/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a user-shot video (UGC — e.g. a phone selfie clip).

    Stored under outputs/uploads and registered as a FINISHED job, so it:
      - shows up immediately in the Library (Renders tab),
      - can be attached to a scheduled post,
      - can be dropped into the Studio as a source clip,
      - and — crucially — its real (ffprobe) duration can drive the MASTER
        duration of a composition: a layout whose audio.master_track points at
        the UGC slot renders to the UGC length, so generated animations
        (Seedance) are calibrated around the real human clip.
    """
    from datetime import datetime as _dtu
    from app.services.storage import JobRecord, async_session_factory

    base = file.filename or "ugc.mp4"
    safe = "".join(c for c in base if c.isalnum() or c in "._- ").strip() or "ugc.mp4"
    if not safe.lower().endswith((".mp4", ".mov", ".webm", ".m4v", ".avi")):
        safe += ".mp4"
    folder = settings.outputs_path / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / safe
    stem, ext = dest.stem, dest.suffix
    n = 1
    while dest.exists():
        dest = folder / f"{stem}_{n}{ext}"
        n += 1
    contents = await file.read()
    dest.write_bytes(contents)

    dur = _probe_seconds(str(dest)) or 0.0
    job_id = str(uuid4())
    async with async_session_factory() as session:
        session.add(JobRecord(
            id=job_id,
            status=JobStatus.DONE.value,
            progress=100,
            title=dest.stem,
            image_filename=dest.name,        # column is non-null; use the file name
            final_video_path=str(dest),
            video_path=str(dest),
            duration_s=int(round(dur)) if dur else None,
            aspect_ratio="9:16",
            provider="ugc",
            current_step="Uploaded",
            completed_at=_dtu.utcnow(),
        ))
        await session.commit()
    return {
        "ok": True, "job_id": job_id, "filename": dest.name,
        "duration_s": round(dur, 2), "final_video_path": str(dest),
    }


# ---- Prompt preview & builder ----

@router.post("/prompt/preview")
async def preview_prompt(request: GenerateRequest):
    try:
        prompt, negative = pipeline.engine.build_prompt(request)
        caption = pipeline.engine.build_caption(request)
        vo = pipeline.engine.build_voiceover_script(request)
        return {
            "prompt": prompt,
            "negative_prompt": negative,
            "caption": caption,
            "voiceover_script": vo,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/prompt/build", response_model=BuildPromptResponse)
async def build_prompt_from_intent(request: BuildPromptRequest):
    """Generate a Seedance prompt from free-text keywords/intent.
    Injects deepotus DNA and structures the output for Seedance 2.0.
    """
    try:
        return pipeline.engine.generate_from_intent(request)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Prompt builder failed")
        raise HTTPException(500, f"Builder error: {e}")


# ---- Generate ----

@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it to backend/.env")

    image_path = settings.images_path / request.image_filename
    if not image_path.exists():
        raise HTTPException(404, f"Start image not found: {request.image_filename}")

    if request.image_filename_end:
        end_path = settings.images_path / request.image_filename_end
        if not end_path.exists():
            raise HTTPException(404, f"End image not found: {request.image_filename_end}")

    if not request.template_id and not request.custom_prompt:
        raise HTTPException(400, "Must provide either template_id or custom_prompt")

    async def _run():
        try:
            await pipeline.run(request)
        except Exception as e:
            logger.error(f"Background pipeline error: {e}")

    background_tasks.add_task(_run)

    return GenerateResponse(
        job_id="pending",
        status=JobStatus.QUEUED,
        message="Job queued. Poll GET /jobs to see latest status.",
    )


# v1.3: Batch generate — N variations with offset seeds
@router.post("/generate/batch", response_model=GenerateBatchResponse)
async def generate_batch(request: GenerateBatchRequest, background_tasks: BackgroundTasks):
    """Queue N jobs sharing the same config but with offset seeds.

    Behavior:
    - If request.seed is provided, seeds = [seed, seed+1, ..., seed+N-1].
    - If request.seed is None, a random base seed is generated and used.
    - All N jobs share a batch_id (returned) so the UI can group them.
    """
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it to backend/.env")

    image_path = settings.images_path / request.image_filename
    if not image_path.exists():
        raise HTTPException(404, f"Start image not found: {request.image_filename}")

    if request.image_filename_end:
        end_path = settings.images_path / request.image_filename_end
        if not end_path.exists():
            raise HTTPException(404, f"End image not found: {request.image_filename_end}")

    if not request.template_id and not request.custom_prompt:
        raise HTTPException(400, "Must provide either template_id or custom_prompt")

    if request.variations_count < 1 or request.variations_count > 8:
        raise HTTPException(400, "variations_count must be between 1 and 8")

    # Determine base seed
    base_seed = request.seed if request.seed is not None else random.randint(1, 2_000_000_000)
    seeds = [base_seed + i for i in range(request.variations_count)]
    batch_id = str(uuid4())

    # Build per-variation requests
    base_dict = request.model_dump(exclude={"variations_count", "seed"})

    async def _run_one(variation_seed: int, idx: int):
        try:
            sub_req = GenerateRequest(**base_dict, seed=variation_seed)
            await pipeline.run(
                sub_req,
                batch_id=batch_id,
                batch_index=idx,
                batch_size=request.variations_count,
            )
        except Exception as e:
            logger.error(f"Batch {batch_id} variation {idx} failed: {e}")

    for idx, s in enumerate(seeds):
        background_tasks.add_task(_run_one, s, idx)

    return GenerateBatchResponse(
        batch_id=batch_id,
        job_count=request.variations_count,
        base_seed=base_seed,
        seeds=seeds,
        message=f"Queued {request.variations_count} variations with seeds {seeds[0]}-{seeds[-1]}.",
    )


# ============ HEYGEN ENDPOINTS (v1.4) ============

@router.get("/heygen/health")
async def heygen_health():
    """Check whether HeyGen is configured and reachable.

    Uses the lightweight /v2/user/remaining_quota probe (sub-second) rather
    than listing avatars (/v2/avatars can take 60s+), so the status badge
    stays responsive and a slow avatar catalogue never makes HeyGen look
    'unreachable'.
    """
    if not settings.has_heygen:
        return {"configured": False, "reachable": False,
                "message": "HEYGEN_API_KEY not set in backend/.env"}
    try:
        client = HeyGenClient()
        quota = await client.remaining_quota()
        rem = quota.get("remaining_quota") if isinstance(quota, dict) else None
        msg = "OK -- key valid"
        if rem is not None:
            msg += f", {rem} credits remaining"
        return {"configured": True, "reachable": True,
                "remaining_quota": rem, "message": msg}
    except HeyGenError as e:
        return {"configured": True, "reachable": False, "message": str(e)}
    except Exception as e:
        return {"configured": True, "reachable": False, "message": f"Network error: {e}"}


@router.get("/heygen/avatars")
async def list_heygen_avatars():
    """List avatars available on your HeyGen account.

    First load can take up to ~2 min (HeyGen's /v2/avatars is slow for large
    catalogues); the result is cached so later loads are instant.
    """
    if not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured")
    try:
        client = HeyGenClient()
        avatars = await client.list_avatars()
        return {"count": len(avatars), "avatars": avatars}
    except HeyGenError as e:
        raise HTTPException(502, f"HeyGen error: {e}")
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        raise HTTPException(504, f"HeyGen timed out listing avatars: {e}")


@router.get("/heygen/voices")
async def list_heygen_voices():
    """List voices available on your HeyGen account."""
    if not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured")
    try:
        client = HeyGenClient()
        voices = await client.list_voices()
        return {"count": len(voices), "voices": voices}
    except HeyGenError as e:
        raise HTTPException(502, f"HeyGen error: {e}")
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        raise HTTPException(504, f"HeyGen timed out listing voices: {e}")


@router.post("/generate/heygen")
async def generate_heygen(request: GenerateHeyGenRequest, background_tasks: BackgroundTasks):
    """Queue a HeyGen avatar video generation."""
    if not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured. Add it to backend/.env")
    if not request.script.strip():
        raise HTTPException(400, "Script must not be empty")

    async def _run():
        try:
            await pipeline.run_heygen(request)
        except Exception as e:
            logger.error(f"Background HeyGen pipeline error: {e}")

    background_tasks.add_task(_run)
    return GenerateResponse(
        job_id="pending",
        status=JobStatus.QUEUED,
        message="HeyGen job queued. Poll GET /jobs to see status.",
    )


@router.post("/generate/composition", response_model=CompositionResponse)
async def generate_composition(request: CompositionRequest, background_tasks: BackgroundTasks):
    """Queue a composition job: Seedance clip + HeyGen clip combined.

    Layout: sequential, split_vstack, or split_hstack.
    Both clips are generated in parallel, then composed via ffmpeg.
    """
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured")
    if not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured")

    # Validate Seedance side
    img_path = settings.images_path / request.seedance.image_filename
    if not img_path.exists():
        raise HTTPException(404, f"Seedance start image not found: {request.seedance.image_filename}")
    if not request.seedance.template_id and not request.seedance.custom_prompt:
        raise HTTPException(400, "Seedance side needs template_id or custom_prompt")

    # Validate HeyGen side
    if not request.heygen.script.strip():
        raise HTTPException(400, "HeyGen script must not be empty")
    if not request.heygen.avatar_id or not request.heygen.voice_id:
        raise HTTPException(400, "HeyGen avatar_id and voice_id are required")

    async def _run():
        try:
            await pipeline.run_composition(request)
        except Exception as e:
            logger.error(f"Background composition pipeline error: {e}")

    background_tasks.add_task(_run)
    return CompositionResponse(
        composition_id="pending",
        job_id="pending",
        message=f"Composition queued ({request.layout.value}). Poll GET /jobs.",
    )


# ============ v1.5: PHOTO AVATAR UPLOAD ============

@router.post("/heygen/photo-avatar/create", response_model=PhotoAvatarCreateResponse)
async def create_photo_avatar_endpoint(
    file: UploadFile = File(...),
    avatar_name: str = "Custom deepotus avatar",
    group_name: str = "",
    do_train: bool = True,
):
    """Upload an image and create a HeyGen photo avatar from it.

    Flow:
      1. Save uploaded file to a temp location
      2. Call HeyGenClient.create_photo_avatar() which:
         - uploads image to HeyGen storage
         - creates an avatar group
         - adds the photo as a look
         - polls until ready (5-30s typical)
         - optionally triggers training (do_train=True)
      3. Returns the photo_avatar_id usable as a talking_photo in video generation.
    """
    if not settings.has_heygen:
        raise HTTPException(400, "HEYGEN_API_KEY not configured")

    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    suffix = Path(file.filename).suffix.lower() if file.filename else ".png"
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type. Use one of: {', '.join(allowed)}")

    # Save to a temp file in images_path/_avatar_uploads (auto-created)
    tmp_dir = settings.images_path / "_avatar_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in (file.filename or "avatar.png") if c.isalnum() or c in "._-") or "avatar.png"
    tmp_path = tmp_dir / f"{uuid4().hex[:8]}_{safe_name}"
    data = await file.read()
    tmp_path.write_bytes(data)
    logger.info(f"Photo avatar upload received: {tmp_path} ({len(data)} bytes)")

    try:
        client = HeyGenClient()
        result = await client.create_photo_avatar(
            file_path=tmp_path,
            avatar_name=avatar_name or "Custom deepotus avatar",
            group_name=group_name or None,
            do_train=do_train,
        )
        # Drop the cached avatar list so the new talking photo shows up on the
        # next /heygen/avatars call instead of waiting for the TTL to expire.
        invalidate_list_cache()
        return PhotoAvatarCreateResponse(
            photo_avatar_id=result["photo_avatar_id"],
            group_id=result["group_id"],
            status=result["status"],
            avatar_name=result["avatar_name"],
            asset_url=result.get("asset_url"),
            message=(
                f"Avatar '{result['avatar_name']}' created and ready. "
                f"Use it in HeyGen mode with avatar_type='talking_photo'."
            ),
        )
    except HeyGenError as e:
        raise HTTPException(502, f"HeyGen error: {e}")
    except Exception as e:
        logger.exception("Photo avatar create failed")
        raise HTTPException(500, f"Photo avatar creation failed: {e}")
    finally:
        # Cleanup the temp file
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            logger.warning(f"Could not clean up temp avatar file: {e}")


# ============ v1.5: UNIVERSAL BUILDER ============

@router.post("/prompt/build-script", response_model=BuildScriptResponse)
async def build_script_endpoint(request: BuildScriptRequest):
    """Generate a HeyGen avatar SCRIPT from a free-text intent.

    Returns: spoken script + suggested caption.
    Different from /prompt/build (which generates VISUAL prompts for Seedance).
    """
    if not request.intent.strip():
        raise HTTPException(400, "Intent must not be empty")
    try:
        return await asyncio.to_thread(
            pipeline.engine.generate_script_from_intent,
            intent=request.intent,
            voice_mode=request.voice_mode,
            language=request.voiceover_language,
            max_words=request.max_words,
            inject_persona=request.inject_persona,
        )
    except Exception as e:
        logger.exception("build_script failed")
        raise HTTPException(500, f"Builder error: {e}")


@router.post("/prompt/refine")
async def refine_text(body: dict):
    """AI-refine a Text node's copy for natural spoken (avatar) delivery.

    Controls: tone, humor, avoid[]. Fail-safe — returns the original text
    with ai=false when no LLM key is configured, so the UI never breaks and
    the user spends nothing.
    """
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    tone = str(body.get("tone") or "").strip()
    humor = str(body.get("humor") or "").strip()
    avoid = body.get("avoid") or []
    mode = str(body.get("mode") or "spoken").strip().lower()
    language = str(body.get("language") or "").strip()
    from app.services import summarizer
    _LMAP = {"FR": "French", "EN": "English", "ES": "Spanish", "DE": "German",
             "IT": "Italian", "PT": "Portuguese", "NL": "Dutch", "JA": "Japanese",
             "KO": "Korean", "ZH": "Chinese", "AR": "Arabic", "HI": "Hindi"}
    if not language:
        lang = "English"
    elif len(language) <= 3:
        lang = _LMAP.get(language.upper(), "English")
    else:
        lang = language  # already a full name from the voice (e.g. "French")
    if mode == "visual":
        # Prompt node: expand an idea into a vivid image/video generation prompt.
        system = (
            "You write prompts for an AI image/video generator (Seedance). "
            "Turn the idea into ONE vivid, concrete visual prompt: subject, "
            "setting, action, camera angle/movement, lighting, color, and art "
            "style. Use comma-separated descriptors, not narration. No "
            "markdown, no preamble, no quotation marks. Return ONLY the prompt."
        )
        parts = ["Expand this into a single cinematic image/video generation prompt."]
        if tone:
            parts.append(f"Visual style: {tone}.")
        if humor and humor.lower() != "none":
            parts.append(f"Mood: {humor}.")
        if isinstance(avoid, list) and avoid:
            parts.append("Do NOT include: " + "; ".join(str(a) for a in avoid) + ".")
        parts.append("Keep it under 60 words.")
        prompt = " ".join(parts) + "\n\nIdea:\n" + text[:2000]
    else:
        system = (
            "You rewrite short scripts that an AI avatar will SPEAK ALOUD. "
            "Optimize for natural, human spoken delivery and clean diction: "
            "short sentences, easy-to-pronounce words, no tongue-twisters, no "
            "markdown, no emojis, no stage directions, no quotation marks, no "
            "preamble. Return ONLY the rewritten script."
        )
        parts = [f"Rewrite this script in {lang} for an avatar to read aloud."]
        if tone:
            parts.append(f"Tone: {tone}.")
        if humor and humor.lower() != "none":
            parts.append(f"Humor: {humor}.")
        if isinstance(avoid, list) and avoid:
            parts.append("Avoid: " + "; ".join(str(a) for a in avoid) + ".")
        parts.append("Keep roughly the same length.")
        prompt = " ".join(parts) + "\n\nScript:\n" + text[:4000]
    try:
        out, prov = await asyncio.to_thread(
            summarizer._chat_dispatch, prompt, system, 800)
    except Exception as e:
        logger.warning(f"refine error: {e}")
        out, prov = None, ""
    if out:
        return {"text": out, "provider": prov, "ai": True}
    return {"text": text, "provider": "", "ai": False}


@router.post("/prompt/build-composition", response_model=BuildCompositionResponse)
async def build_composition_endpoint(request: BuildCompositionRequest):
    """Generate BOTH a Seedance prompt AND a HeyGen script from one intent.

    The two outputs are coherent per the layout:
      - Sequential: avatar SETS UP, Seedance PAYS OFF
      - Split: avatar NARRATES, Seedance SHOWS in parallel
    """
    if not request.intent.strip():
        raise HTTPException(400, "Intent must not be empty")
    try:
        return pipeline.engine.generate_composition_from_intent(
            intent=request.intent,
            layout=request.layout,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            duration_s=request.duration_s,
            voice_mode=request.voice_mode,
            language=request.voiceover_language,
            max_script_words=request.max_script_words,
            inject_persona=request.inject_persona,
        )
    except Exception as e:
        logger.exception("build_composition failed")
        raise HTTPException(500, f"Builder error: {e}")


# ---- Jobs ----

def _job_to_dict(j) -> dict:
    return {
        "job_id": j.id,
        "status": j.status,
        "progress": j.progress,
        "title": getattr(j, "title", None),
        "current_step": j.current_step,
        "image_filename": j.image_filename,
        "image_filename_end": j.image_filename_end,
        "final_prompt": j.final_prompt,
        "negative_prompt": j.negative_prompt,
        "video_path": j.video_path,
        "audio_path": j.audio_path,
        "final_video_path": j.final_video_path,
        "caption_text": j.caption_text,
        "caption_path": j.caption_path,
        "seed": j.seed,
        "duration_s": j.duration_s,
        "aspect_ratio": j.aspect_ratio,
        "style": j.style,
        "template_id": j.template_id,
        "voiceover_language": j.voiceover_language,
        "voice_mode": j.voice_mode,
        "provider": j.provider,
        "composition_id": j.composition_id,
        "composition_layout": j.composition_layout,
        "layer_index": j.layer_index,
        "error": j.error,
        "batch_id": j.batch_id,
        "batch_index": j.batch_index,
        "batch_size": j.batch_size,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
    }


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    jobs = await Pipeline.list_jobs(limit=limit)
    return [_job_to_dict(j) for j in jobs]


def _probe_seconds(path: str | None) -> float | None:
    """Real media duration of a finished render (ffprobe). Used by the
    timeline 'Fit to avatar' so animation clips can be calibrated to the
    avatar's exact length instead of a guessed target."""
    if not path:
        return None
    import subprocess
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True).stdout.strip()
        return round(float(out), 3)
    except (ValueError, FileNotFoundError, OSError):
        return None


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    j = await Pipeline.get_job(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    d = _job_to_dict(j)
    d["duration_real_s"] = _probe_seconds(j.final_video_path)
    return d


@router.patch("/jobs/{job_id}")
async def rename_job(job_id: str, request: JobRenameRequest):
    """Rename a render so it's identifiable in the queue and the
    'existing' clip / audio pickers."""
    j = await Pipeline.rename_job(job_id, request.title)
    if not j:
        raise HTTPException(404, "Job not found")
    return _job_to_dict(j)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job DB record + all files (video, audio, caption)."""
    success = await Pipeline.delete_job(job_id)
    if not success:
        raise HTTPException(404, "Job not found")
    return {"deleted": True, "job_id": job_id}


# v1.3: Bulk delete entire batch
@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str):
    """Delete all jobs in a batch and their files."""
    count = await Pipeline.delete_batch(batch_id)
    if count == 0:
        raise HTTPException(404, "Batch not found or empty")
    return {"deleted": True, "batch_id": batch_id, "jobs_deleted": count}


@router.get("/jobs/{job_id}/video")
async def download_job_video(job_id: str):
    j = await Pipeline.get_job(job_id)
    if not j or not j.final_video_path:
        raise HTTPException(404, "Final video not available")
    p = Path(j.final_video_path)
    if not p.exists():
        raise HTTPException(404, "Video file missing on disk")
    return FileResponse(p, media_type="video/mp4", filename=p.name)


# ---- Health ----

@router.get("/health")
async def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "telegram_enabled": settings.has_telegram,
        "x_enabled": settings.has_x,
        "ollama_enabled": settings.has_ollama,
        "fal_configured": bool(settings.FAL_KEY),
        "voiceover_enabled": settings.has_voiceover,
        "heygen_enabled": settings.has_heygen,
        "summarizer_enabled": settings.has_summarizer,
        "has_summarizer": settings.has_summarizer,
        "openai_enabled": settings.has_openai,
        "gemini_enabled": settings.has_gemini,
        "any_llm": settings.has_any_llm,
        "images_folder": str(settings.images_path),
        "outputs_folder": str(settings.outputs_path),
    }


# ============ v1.8: settings / .env editor ============
# LOCAL SINGLE-USER ONLY. The backend already binds 127.0.0.1:8765 and the
# user explicitly approved this surface. Hardening in depth:
#   - strict allowlist of writable keys (no arbitrary env vars)
#   - masked previews on read (raw values never leave the server)
#   - structured upsert (preserves comments, .env layout)
#   - explicit "restart required" signal (pydantic-settings doesn't reload)

_ALLOWED_ENV_KEYS = {
    "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID_EN", "ELEVENLABS_VOICE_ID_FR",
    "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
    "OPENAI_API_KEY", "OPENAI_MODEL",
    "GEMINI_API_KEY", "GEMINI_MODEL",
    "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
    "OLLAMA_URL", "OLLAMA_MODEL",
    "ARTICLE_READER_FALLBACK",
    # Connected accounts (Scheduler — UI-only for now, but the keys live here)
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CHANNEL_ID",
    "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
}


def _env_path() -> Path:
    """The per-user .env in the stable data dir (survives reinstalls)."""
    from app.config import ENV_FILE
    return ENV_FILE


def _read_env_file() -> dict[str, str]:
    p = _env_path()
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _mask(v: str | None) -> str:
    if not v:
        return ""
    if len(v) <= 8:
        return "•" * len(v)
    return v[:4] + "•" * max(len(v) - 8, 4) + v[-4:]


def _require_localhost(request: Request) -> None:
    """The settings surface reads/writes API keys — refuse any client that
    isn't loopback, even if HOST was misconfigured to 0.0.0.0."""
    host = (request.client.host if request.client else "") or ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(403, "Settings are only accessible from localhost")


@router.get("/settings/keys")
async def list_keys(request: Request):
    """Every allowed key with `set` (bool) + masked `preview`. Raw values
    are never returned."""
    _require_localhost(request)
    env = _read_env_file()
    out = []
    for k in sorted(_ALLOWED_ENV_KEYS):
        v = env.get(k, "")
        out.append({"key": k, "set": bool(v), "preview": _mask(v)})
    return {"keys": out, "env_path": str(_env_path())}


@router.post("/settings/keys")
async def set_key(body: dict, request: Request):
    """Upsert one or more keys into backend/.env.
    Accepts { name, value } or { entries: [{name, value}, …] }.
    Empty value clears the key. The backend must be restarted for
    changes to take effect (pydantic-settings doesn't hot-reload .env).
    """
    _require_localhost(request)
    entries = body.get("entries") if isinstance(body, dict) else None
    if entries is None:
        name = (body or {}).get("name")
        value = (body or {}).get("value", "")
        entries = [{"name": name, "value": value}] if name else []
    if not entries:
        raise HTTPException(400, "No entries to write")
    for e in entries:
        n = (e.get("name") or "").strip()
        if n not in _ALLOWED_ENV_KEYS:
            raise HTTPException(400, f"Key not allowed: {n}")

    p = _env_path()
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    changes = {(e.get("name") or "").strip(): (e.get("value") or "").strip()
               for e in entries}
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if (not s) or s.startswith("#") or "=" not in s:
            new_lines.append(line)
            continue
        k, _, _v = line.partition("=")
        k = k.strip()
        if k in changes:
            new_lines.append(f"{k}={changes[k]}")
            seen.add(k)
        else:
            new_lines.append(line)
    for k, v in changes.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"Wrote {len(changes)} key(s) to {p}")
    return {
        "ok": True,
        "written": list(changes.keys()),
        "restart_required": True,
        "message": "Saved. Restart the backend for changes to apply.",
    }


# ============ v1.15: provider defaults ============

@router.get("/settings/provider-defaults")
async def get_provider_defaults(request: Request):
    _require_localhost(request)
    from app.services.summarizer import active_provider as sum_active, _available_providers as sum_avail
    from app.services.marketing import _plan_available, _PLAN_PRIORITY
    plan_avail = [p for p in _PLAN_PRIORITY if _plan_available(p)]
    pref_plan = settings.PLANNER_PROVIDER.strip().lower()
    active_plan = pref_plan if (pref_plan and pref_plan in plan_avail) else (plan_avail[0] if plan_avail else "")
    return {
        "roles": {
            "summarizer": {
                "available": sum_avail(),
                "active": sum_active(),
                "preference": settings.SUMMARIZER_PROVIDER,
            },
            "planner": {
                "available": plan_avail,
                "active": active_plan,
                "preference": settings.PLANNER_PROVIDER,
            },
        },
    }


@router.post("/settings/provider-defaults")
async def set_provider_defaults(body: dict, request: Request):
    _require_localhost(request)
    allowed_roles = {"summarizer": "SUMMARIZER_PROVIDER", "planner": "PLANNER_PROVIDER"}
    changes: dict[str, str] = {}
    for role, value in (body or {}).items():
        env_key = allowed_roles.get(role)
        if not env_key:
            continue
        changes[env_key] = str(value or "").strip().lower()
    if not changes:
        raise HTTPException(400, "No valid role/provider pairs")
    p = _env_path()
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if (not s) or s.startswith("#") or "=" not in s:
            new_lines.append(line)
            continue
        k, _, _v = line.partition("=")
        k = k.strip()
        if k in changes:
            new_lines.append(f"{k}={changes[k]}")
            seen.add(k)
        else:
            new_lines.append(line)
    for k, v in changes.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "written": changes,
        "restart_required": True,
        "message": "Saved. Restart the backend for changes to apply.",
    }


# ============ v1.11: WHITE-LABEL BRANDING ============
# The shipped product boots as "deepotus"; everything user-facing is
# rebrandable. Config lives in assets/branding/branding.json + logo.png —
# under assets/, so upgrades never touch it.

BRAND_DEFAULTS = {
    "app_name": "DEEPOTUS",
    "app_sub": "VIDEO",
    "tagline_1": "From the deep,",
    "tagline_2": "for the deep.",
    "brand_color": "#ef4444",
    "accent_color": "#00e5ff",
}
_BRAND_COLOR_RE = r"^#[0-9a-fA-F]{6}$"


def _branding_dir() -> Path:
    from app.config import DATA_ROOT
    p = DATA_ROOT / "assets" / "branding"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read_branding() -> dict:
    f = _branding_dir() / "branding.json"
    data = dict(BRAND_DEFAULTS)
    if f.is_file():
        try:
            user = json.loads(f.read_text(encoding="utf-8"))
            for k in BRAND_DEFAULTS:
                if isinstance(user.get(k), str) and user[k].strip():
                    data[k] = user[k].strip()
        except (ValueError, OSError) as e:
            logger.warning(f"branding.json unreadable, using defaults: {e}")
    data["has_custom_logo"] = (_branding_dir() / "logo.png").is_file()
    data["is_default"] = not (_branding_dir() / "branding.json").is_file() \
        and not data["has_custom_logo"]
    return data


@router.get("/branding")
async def get_branding():
    return _read_branding()


@router.post("/branding")
async def set_branding(body: dict, request: Request):
    """Update brand fields (allowlisted, colors validated). Empty body or
    {"reset": true} restores deepotus defaults (and removes the custom logo)."""
    _require_localhost(request)
    bdir = _branding_dir()
    if not body or body.get("reset"):
        (bdir / "branding.json").unlink(missing_ok=True)
        (bdir / "logo.png").unlink(missing_ok=True)
        logger.info("branding reset to deepotus defaults")
        return _read_branding()
    clean = {}
    for k in BRAND_DEFAULTS:
        v = body.get(k)
        if not isinstance(v, str) or not v.strip():
            continue
        v = v.strip()
        if k.endswith("_color") and not re.match(_BRAND_COLOR_RE, v):
            raise HTTPException(400, f"{k} must be #RRGGBB (got: {v})")
        clean[k] = v[:60]
    existing = {}
    f = bdir / "branding.json"
    if f.is_file():
        try:
            existing = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            existing = {}
    existing.update(clean)
    f.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    logger.info(f"branding updated: {list(clean.keys())}")
    return _read_branding()


@router.get("/branding/logo")
async def get_branding_logo():
    """The brand logo: custom upload if present, else the bundled deepotus
    mark. Cache disabled so a rebrand shows immediately."""
    custom = _branding_dir() / "logo.png"
    if custom.is_file():
        return FileResponse(str(custom), media_type="image/png",
                            headers={"Cache-Control": "no-cache"})
    bundled = (Path(__file__).resolve().parents[2].parent
               / "frontend" / "public" / "deepotus-logo.png")
    if bundled.is_file():
        return FileResponse(str(bundled), media_type="image/png",
                            headers={"Cache-Control": "no-cache"})
    raise HTTPException(404, "No logo available")


@router.post("/branding/logo")
async def upload_branding_logo(request: Request, file: UploadFile = File(...)):
    _require_localhost(request)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPException(400, "Logo must be .png, .jpg or .webp")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Logo too large (max 5 MB)")
    # Normalize to PNG via Pillow (also validates it's a real image).
    try:
        import io
        from PIL import Image as PILImg
        img = PILImg.open(io.BytesIO(data)).convert("RGBA")
        img.save(_branding_dir() / "logo.png", format="PNG")
    except Exception as e:
        raise HTTPException(400, f"Not a valid image: {e}")
    logger.info("custom brand logo uploaded")
    return _read_branding()


# ============ v1.14: editable caption pack (Telegram Premium tags) ============
# The Scheduler caption editor offers one-tap branded tags. The default set is
# deepotus-flavoured; this endpoint lets the user (or a white-label reseller)
# edit the entries and upload a custom icon per entry. Stored next to branding.

_DEFAULT_CAPTION_PACK = [
    {"id": "deepotus-protocol", "emoji": "\U0001F419", "label": "Deepotus Protocol", "icon": "/pack/deepotus-protocol.png"},
    {"id": "rippled-signal",    "emoji": "\U0001F30A", "label": "Rippled Signal",    "icon": "/pack/rippled-signal.png"},
    {"id": "prophet",           "emoji": "\U0001F441", "label": "Prophet",           "icon": ""},
    {"id": "chapter-drop",      "emoji": "\U0001F4D6", "label": "Chapter Drop",      "icon": ""},
    {"id": "board-game",        "emoji": "\U0001F3B4", "label": "Board Game",        "icon": ""},
    {"id": "dnd",               "emoji": "\U0001F3B2", "label": "D&D",               "icon": ""},
    {"id": "mobile-devlog",     "emoji": "\U0001F4F1", "label": "Mobile Devlog",     "icon": ""},
    {"id": "deep",              "emoji": "\U0001FA99", "label": "$DEEP",             "icon": ""},
    {"id": "gencoin",           "emoji": "\U0001F9EC", "label": "Gencoin",           "icon": ""},
    {"id": "video-engine",      "emoji": "\U0001F3AC", "label": "Video Engine",      "icon": ""},
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40] or "tag"


def _caption_pack_file() -> Path:
    return _branding_dir() / "caption-pack.json"


def _pack_icons_dir() -> Path:
    p = _branding_dir() / "pack-icons"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clean_pack_entry(e: dict) -> dict | None:
    if not isinstance(e, dict):
        return None
    label = str(e.get("label") or "").strip()
    if not label:
        return None
    return {
        "id": (str(e.get("id") or "").strip() or _slug(label))[:40],
        "emoji": str(e.get("emoji") or "").strip()[:8],
        "label": label[:40],
        "icon": str(e.get("icon") or "").strip()[:300],
    }


def _read_caption_pack() -> list:
    f = _caption_pack_file()
    if f.is_file():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                out = [c for c in (_clean_pack_entry(e) for e in data) if c]
                if out:
                    return out
        except (ValueError, OSError) as ex:
            logger.warning(f"caption-pack.json unreadable: {ex}")
    return [dict(e) for e in _DEFAULT_CAPTION_PACK]


@router.get("/caption-pack")
async def get_caption_pack():
    return {"pack": _read_caption_pack(), "is_default": not _caption_pack_file().is_file()}


@router.post("/caption-pack")
async def set_caption_pack(body: dict, request: Request):
    """Save the caption pack. {"reset": true} restores deepotus defaults and
    clears uploaded icons."""
    _require_localhost(request)
    if not body or body.get("reset"):
        _caption_pack_file().unlink(missing_ok=True)
        import shutil
        shutil.rmtree(_pack_icons_dir(), ignore_errors=True)
        logger.info("caption pack reset to defaults")
        return {"pack": _read_caption_pack(), "is_default": True}
    items = body.get("pack")
    if not isinstance(items, list):
        raise HTTPException(400, "pack must be a list")
    clean = [c for c in (_clean_pack_entry(e) for e in items[:40]) if c]
    _caption_pack_file().write_text(
        json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"caption pack saved: {len(clean)} entries")
    return {"pack": clean, "is_default": False}


@router.get("/caption-pack/icon/{slot}")
async def get_pack_icon(slot: str):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", slot)[:40]
    p = _pack_icons_dir() / f"{safe}.png"
    if not p.is_file():
        raise HTTPException(404, "icon not found")
    return FileResponse(str(p), media_type="image/png", headers={"Cache-Control": "no-cache"})


@router.post("/caption-pack/icon/{slot}")
async def upload_pack_icon(slot: str, request: Request, file: UploadFile = File(...)):
    _require_localhost(request)
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", slot)[:40] or "tag"
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Icon too large (max 5 MB)")
    try:
        import io
        from PIL import Image as PILImg
        img = PILImg.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail((128, 128), PILImg.LANCZOS)
        img.save(_pack_icons_dir() / f"{safe}.png", format="PNG")
    except Exception as e:
        raise HTTPException(400, f"Not a valid image: {e}")
    logger.info(f"caption pack icon uploaded: {safe}")
    return {"ok": True, "icon": f"/api/caption-pack/icon/{safe}"}


# ============ v1.9: MARKETING PLAN + SCHEDULER + IMAGE GEN ============

from datetime import datetime as _dt, timedelta as _td
from sqlalchemy import select as _select, delete as _delete
from app.services.storage import ScheduledPost, JobRecord, async_session_factory
from app.services import marketing


def _post_to_dict(p: ScheduledPost) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "caption": p.caption,
        "channels": [c for c in (p.channels or "").split(",") if c],
        "run_at": (p.run_at.isoformat() + "Z") if p.run_at else None,
        "status": p.status,
        "mode": p.mode,
        "job_id": p.job_id,
        "format": p.format,
        "hook": p.hook,
        "script_idea": p.script_idea,
        "image_idea": p.image_idea,
        "plan_id": p.plan_id,
        "error": p.error,
        "created_at": (p.created_at.isoformat() + "Z") if p.created_at else None,
        "posted_at": (p.posted_at.isoformat() + "Z") if p.posted_at else None,
        "x_post_id": p.x_post_id,
        "metrics": p.metrics,
        "source_image": p.source_image,
    }


@router.get("/schedule")
async def list_schedule(days_back: int = 30, days_forward: int = 90):
    """All scheduled posts in a window around now (UTC)."""
    lo = _dt.utcnow() - _td(days=days_back)
    hi = _dt.utcnow() + _td(days=days_forward)
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost)
            .where(ScheduledPost.run_at >= lo)
            .where(ScheduledPost.run_at <= hi)
            .order_by(ScheduledPost.run_at.asc()))
        return [_post_to_dict(p) for p in res.scalars().all()]


@router.post("/schedule")
async def create_scheduled_post(body: dict):
    """Create one post. Body: {title, caption, channels[], run_at (UTC ISO),
    status?, mode?, job_id?, format?}."""
    run_at_raw = (body.get("run_at") or "").replace("Z", "")
    try:
        run_at = _dt.fromisoformat(run_at_raw)
    except ValueError:
        raise HTTPException(400, f"Invalid run_at: {body.get('run_at')}")
    p = ScheduledPost(
        id=str(uuid4()),
        title=(body.get("title") or "Untitled post")[:200],
        caption=body.get("caption") or "",
        channels=",".join(body.get("channels") or ["x"]),
        run_at=run_at,
        status=body.get("status") if body.get("status") in
               ("draft", "scheduled", "ready") else "draft",
        mode=body.get("mode") if body.get("mode") in
             ("auto", "assisted") else "assisted",
        job_id=body.get("job_id"),
        format=body.get("format"),
        hook=body.get("hook"),
        script_idea=body.get("script_idea"),
        image_idea=body.get("image_idea"),
        source_image=body.get("source_image") or None,
    )
    async with async_session_factory() as session:
        session.add(p)
        await session.commit()
    return _post_to_dict(p)


@router.patch("/schedule/{post_id}")
async def update_scheduled_post(post_id: str, body: dict):
    """Patch any editable field of a post."""
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == post_id))
        p = res.scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Post not found")
        if "title" in body:
            p.title = (body["title"] or "")[:200]
        if "caption" in body:
            p.caption = body["caption"] or ""
        if "channels" in body:
            p.channels = ",".join(body["channels"] or [])
        if "run_at" in body and body["run_at"]:
            try:
                p.run_at = _dt.fromisoformat(
                    str(body["run_at"]).replace("Z", ""))
            except ValueError:
                raise HTTPException(400, f"Invalid run_at: {body['run_at']}")
        if "status" in body and body["status"] in (
                "draft", "scheduled", "ready", "posted", "failed"):
            p.status = body["status"]
        if "mode" in body and body["mode"] in ("auto", "assisted"):
            p.mode = body["mode"]
        if "job_id" in body:
            p.job_id = body["job_id"] or None
        if "format" in body:
            p.format = body["format"] or None
        if "source_image" in body:
            p.source_image = body["source_image"] or None
        await session.commit()
        await session.refresh(p)
        return _post_to_dict(p)


@router.delete("/schedule/{post_id}")
async def delete_scheduled_post(post_id: str):
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == post_id))
        if not res.scalar_one_or_none():
            raise HTTPException(404, "Post not found")
        await session.execute(
            _delete(ScheduledPost).where(ScheduledPost.id == post_id))
        await session.commit()
    return {"deleted": post_id}


@router.post("/schedule/{post_id}/fire")
async def fire_scheduled_post(post_id: str):
    """Publish NOW on auto-capable channels (Telegram). Channels without an
    auto adapter stay listed in `pending` — the post flips to `ready` so the
    user can publish manually with the caption + downloaded render."""
    result = await marketing.fire_post(post_id)
    if not result.get("ok") and result.get("error") == "post not found":
        raise HTTPException(404, "Post not found")
    return result


def _render_poster_frame(jobrec) -> str | None:
    """Cached poster frame (~1s in) extracted from a render's video, used as the
    post-preview hero when the render has no still image (e.g. HeyGen avatars).
    Returns the PNG path or None."""
    import subprocess
    vp = getattr(jobrec, "final_video_path", None)
    if not vp:
        return None
    src = Path(vp)
    if not src.is_file():
        return None
    cache = settings.outputs_path / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f"poster_{jobrec.id}.png"
    if out.is_file() and out.stat().st_mtime >= src.stat().st_mtime:
        return str(out)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1", "-i", str(src),
             "-frames:v", "1", "-q:v", "3", str(out)],
            check=True, capture_output=True, timeout=30)
        return str(out) if out.is_file() else None
    except Exception as e:
        logger.warning(f"poster extraction failed for {getattr(jobrec,'id','?')}: {e}")
        return None


@router.get("/schedule/{post_id}/preview.png")
async def scheduled_post_preview(post_id: str, channel: str = "x",
                                 caption: str | None = None,
                                 img: str | None = None,
                                 job: str | None = None):
    """Compose the final post (hero image + caption) as a platform-styled PNG
    so the user can visualize it before publishing. channel = x | telegram.

    Hero image resolves to the post's source_image, else the attached render's
    still (job.image_filename), else a placeholder. The caption is rendered in
    the platform's usage format (X: handle + 280-char card; Telegram: channel
    bubble with image-then-caption).

    Optional query overrides (caption, img, job) let the inspector preview
    live, still-unsaved edits without a DB round-trip."""
    from app.services import post_preview as _pp
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == post_id))
        p = res.scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Post not found")
        eff_src = img if img is not None else p.source_image
        eff_job = job if job is not None else p.job_id
        hero = None
        if eff_src:
            cand = settings.images_path / eff_src
            if cand.is_file():
                hero = str(cand)
        if not hero and eff_job:
            jr = await session.execute(
                _select(JobRecord).where(JobRecord.id == eff_job))
            jobrec = jr.scalar_one_or_none()
            if jobrec:
                if jobrec.image_filename:
                    cand = settings.images_path / jobrec.image_filename
                    if cand.is_file():
                        hero = str(cand)
                if not hero:
                    hero = _render_poster_frame(jobrec)
        caption = caption if caption is not None else (p.caption or p.title or "")
    brand = _read_branding()
    name = (brand.get("app_name") or "Deepotus").strip().title() or "Deepotus"
    handle = re.sub(r"[^a-z0-9_]", "", name.lower())[:15] or "deepotus"
    try:
        png = _pp.render_preview(channel=channel, caption=caption,
                                 hero_path=hero, display_name=name, handle=handle)
    except Exception as e:
        logger.exception("post preview render failed")
        raise HTTPException(500, f"Preview failed: {e}")
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ============ COST WIDGET (v1.15.1) ============

@router.post("/cost/estimate")
async def cost_estimate(body: dict, request: Request):
    """Preview budget for a planned op (single edit / plan / campaign)."""
    _require_localhost(request)
    from app.services import pricing as _pricing
    return _pricing.estimate(body or {})


def _job_to_cost(job, p):
    from app.services import pricing as _pricing
    prov = (job.provider or "seedance").lower()
    dur = job.duration_s or 10
    if prov == "heygen":
        return _pricing.estimate({"kind": "heygen", "minutes": max(0.2, dur / 60.0)}, p)
    if prov == "episode":
        import json as _json
        try:
            meta = _json.loads(job.cost_meta or "{}")
        except Exception:
            meta = {}
        return _pricing.estimate({"kind": "episode",
                                  "images": int(meta.get("images", 1) or 1),
                                  "chars": float(meta.get("chars", 0) or 0)}, p)
    return _pricing.estimate({"kind": "campaign", "ops": [
        {"kind": "image"}, {"kind": "seedance", "duration_s": dur}]}, p)


@router.get("/cost/usage")
async def cost_usage():
    """Cumulative ESTIMATED spend, computed from finished job records."""
    from app.services import pricing as _pricing
    p = _pricing.load()
    per = {}
    total = 0.0
    async with async_session_factory() as session:
        res = await session.execute(
            _select(JobRecord).where(JobRecord.status == "done"))
        for job in res.scalars().all():
            e = _job_to_cost(job, p)
            total += e["total_usd"]
            for ln in e["breakdown"]:
                per[ln["provider"]] = round(per.get(ln["provider"], 0) + ln["usd"], 4)
    return {"total_usd": round(total, 2), "by_provider": per}


@router.get("/cost/balances")
async def cost_balances():
    """Live remaining balances where a provider exposes them (HeyGen credits,
    ElevenLabs characters); pay-as-you-go otherwise."""
    from app.services import pricing as _pricing
    p = _pricing.load()
    out = {}
    if settings.has_heygen:
        try:
            q = await HeyGenClient().remaining_quota()
            rem = q.get("remaining_quota") if isinstance(q, dict) else None
            out["heygen"] = {"available": True, "credits": rem,
                             "usd": round((rem or 0) * p["heygen_credit_usd"], 2)}
        except Exception:
            out["heygen"] = {"available": False}
    if settings.has_voiceover:
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=SSL_VERIFY) as c:
                r = await c.get("https://api.elevenlabs.io/v1/user/subscription",
                                headers={"xi-api-key": settings.ELEVENLABS_API_KEY})
                if r.status_code == 200:
                    d = r.json()
                    used = d.get("character_count")
                    lim = d.get("character_limit")
                    out["elevenlabs"] = {
                        "available": True, "used": used, "limit": lim,
                        "remaining": (lim - used) if (lim is not None and used is not None) else None}
                else:
                    out["elevenlabs"] = {"available": False}
        except Exception:
            out["elevenlabs"] = {"available": False}
    for prov, on in (("fal", bool(settings.FAL_KEY)),
                     ("anthropic", settings.has_summarizer),
                     ("openai", settings.has_openai),
                     ("gemini", settings.has_gemini)):
        if on:
            out[prov] = {"available": False, "mode": "pay-as-you-go"}
    return out


@router.get("/cost/pricing")
async def get_pricing():
    from app.services import pricing as _pricing
    return _pricing.load()


@router.post("/cost/pricing")
async def set_pricing(body: dict, request: Request):
    _require_localhost(request)
    from app.services import pricing as _pricing
    return _pricing.save(body or {})



@router.post("/marketing/plan")
async def marketing_plan(body: dict):
    """Prompt → structured posting plan.
    Body: {prompt, days=7, posts_per_day=1, channels=["x"], language="EN",
           persona?{name,tone,audience}, auto_materialize=false,
           start_date "YYYY-MM-DD", tz_offset_minutes (JS getTimezoneOffset),
           mode "auto"|"assisted"}.
    Uses Anthropic when ANTHROPIC_API_KEY is set; deterministic otherwise."""
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    days = max(1, min(31, int(body.get("days") or 7)))
    ppd = max(1, min(6, int(body.get("posts_per_day") or 1)))
    plan = await marketing.generate_plan(
        prompt,
        days=days,
        posts_per_day=ppd,
        channels=body.get("channels") or ["x"],
        language=body.get("language") or "EN",
        persona=body.get("persona"),
    )
    materialized: list[str] = []
    if body.get("auto_materialize"):
        start = body.get("start_date") or _dt.now().strftime("%Y-%m-%d")
        materialized = await marketing.materialize_plan(
            plan["posts"],
            start_date=start,
            tz_offset_minutes=int(body.get("tz_offset_minutes") or 0),
            mode=body.get("mode") or "assisted",
        )
    return {**plan, "materialized_ids": materialized}


@router.post("/marketing/plan/import")
async def import_marketing_plan(
    file: UploadFile = File(...),
    days: int = 30,
    channels: str = "x",
    language: str = "EN",
):
    """Upload an EXISTING strategy document (.md / .txt / .docx / .pdf) and
    transcribe it into posting-plan slices. Human-in-the-loop: returns the
    structured plan only — the UI previews it and the user materializes
    explicitly via POST /marketing/plan with the returned posts, or via the
    modal's Add-to-calendar which re-sends with auto_materialize."""
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 15 MB)")
    try:
        text = marketing.extract_document_text(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"document extraction failed: {e}")
        raise HTTPException(400, f"Could not read the document: {e}")
    try:
        plan = await marketing.plan_from_document(
            text,
            days=max(1, min(60, days)),
            channels=[c for c in channels.split(",") if c] or ["x"],
            language=language,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {**plan, "chars_read": len(text), "filename": file.filename}


@router.post("/marketing/plan/materialize")
async def materialize_plan_route(body: dict):
    """Materialize an already-generated/imported plan (the human-approved
    posts array) into scheduled_posts. Used by the import flow where the
    posts were reviewed in the preview before being committed."""
    posts = body.get("posts")
    if not isinstance(posts, list) or not posts:
        raise HTTPException(400, "posts array is required")
    start = body.get("start_date") or _dt.now().strftime("%Y-%m-%d")
    ids = await marketing.materialize_plan(
        posts,
        start_date=start,
        tz_offset_minutes=int(body.get("tz_offset_minutes") or 0),
        mode=body.get("mode") or "assisted",
    )
    return {"materialized_ids": ids}


@router.post("/channels/test")
async def test_channel(body: dict):
    """Send a test message on a channel to validate the keys. Telegram sends
    a text message; X posts a real (deletable) tweet only when confirm=true,
    otherwise it just validates credentials by fetching the authed user."""
    ch = (body or {}).get("channel")
    if ch == "telegram":
        if not settings.has_telegram:
            raise HTTPException(400, "Telegram keys not set")
        ok, detail = await marketing.publish_telegram(
            "Deepotus Video Gen — test message. The deep hears you. 🐙")
        return {"ok": ok, "detail": detail}
    if ch == "x":
        if not settings.has_x:
            raise HTTPException(400, "X keys not set")
        import asyncio as _aio
        def _verify():
            try:
                me = marketing._x_client().get_me()
                return True, f"authenticated as @{me.data.username}"
            except Exception as e:
                return False, str(e)
        ok, detail = await _aio.to_thread(_verify)
        return {"ok": ok, "detail": detail}
    raise HTTPException(400, f"No test available for channel: {ch}")


@router.post("/images/import-url")
async def import_image_url(body: dict):
    """Download a remote image (e.g. the picture attached to a news item)
    into the images folder so it can be used as a Seedance start frame or a
    post still. Returns {filename}. Used by the plan's Sources step."""
    url = (body or {}).get("url", "").strip()
    if not url or not url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "A valid image URL is required")
    import httpx as _httpx
    import ipaddress as _ipaddr
    _host = (_httpx.URL(url).host or "").lower()

    def _is_private(h: str) -> bool:
        if h in ("localhost", "") or h.endswith(".local"):
            return True
        try:
            ip = _ipaddr.ip_address(h)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            return False  # plain hostname; DNS-rebinding out of scope for a desktop tool
    if _is_private(_host):
        raise HTTPException(400, "Refusing to fetch a private/loopback address")
    try:
        async with _httpx.AsyncClient(verify=SSL_VERIFY, timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Mozilla/5.0"}) as r:
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if "image" not in ctype and not url.lower().split("?")[0].endswith(
                        (".png", ".jpg", ".jpeg", ".webp")):
                    raise HTTPException(400, f"URL is not an image ({ctype})")
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > 25 * 1024 * 1024:
                        raise HTTPException(400, "Image too large (max 25 MB)")
            import io
            from PIL import Image as _PILImage
            img = _PILImage.open(io.BytesIO(bytes(buf))).convert("RGB")
            fname = f"news_{uuid4().hex[:8]}.png"
            img.save(settings.images_path / fname, format="PNG")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"news image import failed: {e}")
        raise HTTPException(502, f"Could not import the image: {e}")
    logger.info(f"imported news image -> {fname}")
    return {"filename": fname}


@router.post("/images/generate")
async def generate_image(body: dict, background_tasks: BackgroundTasks):
    """Text-to-image via fal.ai FLUX (same FAL_KEY as Seedance). Saves the
    PNG(s) into the images folder so they're immediately usable as Seedance
    start frames. Body: {prompt, n=1, size="portrait_16_9"}. Synchronous —
    FLUX schnell returns in ~2-4s per image."""
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    n = max(1, min(4, int(body.get("n") or 1)))
    size = body.get("size") or "portrait_16_9"
    model = (body.get("model") or "").strip().lower()
    import httpx as _httpx

    # --- OpenAI gpt-image / dall-e path (per the selected model) -----------
    if model.startswith("gpt-image") or model.startswith("dall-e"):
        if not settings.OPENAI_API_KEY:
            raise HTTPException(400, "OPENAI_API_KEY not configured. Add it in Settings.")
        osize = ("1024x1536" if "portrait" in size
                 else "1536x1024" if "landscape" in size else "1024x1024")
        payload = {"model": model, "prompt": prompt, "n": n, "size": osize}
        try:
            async with _httpx.AsyncClient(verify=SSL_VERIFY, timeout=180.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json=payload)
        except Exception as e:
            logger.error(f"OpenAI image gen failed: {e}")
            raise HTTPException(502, f"OpenAI: image generation failed: {e}")
        if resp.status_code != 200:
            logger.error(f"OpenAI image HTTP {resp.status_code}: {resp.text[:300]}")
            raise HTTPException(502, f"OpenAI image error: {resp.text[:200]}")
        data = (resp.json() or {}).get("data", [])
        import base64 as _b64
        saved: list[str] = []
        for it in data:
            fname = f"gen_{uuid4().hex[:8]}.png"
            dest = settings.images_path / fname
            if it.get("b64_json"):
                dest.write_bytes(_b64.b64decode(it["b64_json"]))
                saved.append(fname)
            elif it.get("url"):
                async with _httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as c2:
                    rr = await c2.get(it["url"])
                    rr.raise_for_status()
                    dest.write_bytes(rr.content)
                saved.append(fname)
        if not saved:
            raise HTTPException(502, "OpenAI returned no images")
        logger.info(f"OpenAI {model}: saved {len(saved)} image(s): {saved}")
        return {"images": saved, "prompt": prompt, "model": model}

    # --- fal.ai FLUX path (default) ---------------------------------------
    if not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it in Settings.")
    if size not in ("square_hd", "square", "portrait_4_3", "portrait_16_9",
                    "landscape_4_3", "landscape_16_9"):
        size = "portrait_16_9"
    import fal_client
    try:
        result = await fal_client.subscribe_async(
            "fal-ai/flux/schnell",
            arguments={"prompt": prompt, "image_size": size,
                       "num_images": n, "enable_safety_checker": True},
        )
    except Exception as e:
        logger.error(f"FLUX generation failed: {e}")
        raise HTTPException(502, f"fal.ai: image generation failed: {e}")
    urls = [im.get("url") for im in (result or {}).get("images", [])
            if im.get("url")]
    if not urls:
        raise HTTPException(502, "FLUX returned no images")
    saved = []
    async with _httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as client:
        for u in urls:
            fname = f"gen_{uuid4().hex[:8]}.png"
            dest = settings.images_path / fname
            r = await client.get(u)
            r.raise_for_status()
            dest.write_bytes(r.content)
            saved.append(fname)
    logger.info(f"FLUX: saved {len(saved)} image(s): {saved}")
    return {"images": saved, "prompt": prompt, "model": "flux"}


@router.post("/images/fetch")
async def fetch_image(body: dict):
    """Download a remote image URL into the images folder so it's usable as a
    Studio slot (e.g. a news headline's own image). Body: {url}. -> {filename}."""
    import httpx as _httpx
    url = (body.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "A valid image URL is required")
    try:
        async with _httpx.AsyncClient(verify=SSL_VERIFY, timeout=30.0,
                                      follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
    except Exception as e:
        raise HTTPException(502, f"Image fetch failed: {e}")
    ct = (r.headers.get("content-type") or "").lower()
    low = url.lower().split("?")[0]
    if "image" not in ct and not low.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        raise HTTPException(415, "That URL is not an image")
    ext = ".jpg" if ("jpeg" in ct or "jpg" in ct or low.endswith((".jpg", ".jpeg"))) \
        else ".webp" if ("webp" in ct or low.endswith(".webp")) else ".png"
    fname = f"gen_{uuid4().hex[:8]}{ext}"
    (settings.images_path / fname).write_bytes(r.content)
    logger.info(f"Fetched image -> {fname} ({len(r.content) // 1024} KB)")
    return {"filename": fname}


@router.get("/image-models")
async def list_image_models():
    """Image-generation models available given the registered API keys. The
    Studio image picker uses this to show only usable models; the chosen id is
    sent back as `model` to POST /images/generate. Persisted client-side."""
    out = []
    if settings.FAL_KEY:
        out.append({"id": "flux", "label": "FLUX schnell",
                    "provider": "fal", "note": "fast, low cost"})
    if settings.OPENAI_API_KEY:
        out.append({"id": "gpt-image-2", "label": "GPT Image 2",
                    "provider": "openai", "note": "best quality"})
        out.append({"id": "gpt-image-1", "label": "GPT Image 1",
                    "provider": "openai", "note": "balanced"})
        out.append({"id": "gpt-image-1-mini", "label": "GPT Image 1 mini",
                    "provider": "openai", "note": "cheapest OpenAI"})
    return {"models": out, "default": ("flux" if settings.FAL_KEY
                                       else (out[0]["id"] if out else ""))}
