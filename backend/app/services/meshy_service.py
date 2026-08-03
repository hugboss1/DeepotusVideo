"""3D Studio Meshy — proxy sécurisé, tarification, persistance, rapatriement.

Spec : INTEGRATION-MESHY.md + frontend/meshy/meshy.client.js (projet Claude
Design « DeepOtus Studio », écran 3D Studio). Trois règles produit :

1. La clé MESHY_API_KEY ne quitte JAMAIS le serveur. Le navigateur parle au
   proxy /api/meshy/* qui recopie la requête vers https://api.meshy.ai en
   injectant le Bearer — chemins strictement allowlistés (surface documentée
   docs.meshy.ai, rien d'autre ne passe).
2. Le coût est visible AVANT chaque action (estimate_pipeline) ; après coup,
   `consumed_credits` de la réponse Meshy est la seule vérité comptable
   (une tâche FAILED rembourse → 0).
3. Les URLs Meshy expirent (`expires_at`) : chaque tâche SUCCEEDED est
   enregistrée en base (meshy_tasks) et ses binaires sont rapatriés dans
   outputs/meshy3d/<task_id>/ — sans quoi la bibliothèque se vide seule.

Mode mock (MESHY_MOCK=1 dans le .env) : simulateur en mémoire fidèle aux
réponses Meshy (PENDING→IN_PROGRESS→SUCCEEDED, progress, consumed_credits
selon la grille tarifaire) — le front réel roule dessus sans crédits.
Ce flux n'a aucun lien avec Game Assets 3D (fal) : asset3d_service reste
intact, les moteurs fal continuent de passer par /api/assets/3d.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import struct
import time
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx

from app.config import settings, SSL_VERIFY

logger = logging.getLogger(__name__)

MESHY_API = "https://api.meshy.ai"

# ── surface d'API autorisée (docs.meshy.ai) ─────────────────────────────────
# base → POST (création) + GET (liste) ; base/{id} → GET ; base/{id}/stream
# → GET (SSE) ; base/{id} → DELETE. Tout le reste est refusé (403).
ALLOWED_BASES = {
    "openapi/v2/text-to-3d",
    "openapi/v1/image-to-3d",
    "openapi/v1/multi-image-to-3d",
    "openapi/v1/remesh",
    "openapi/v1/convert",
    "openapi/v1/resize",
    "openapi/v1/uv-unwrap",
    "openapi/v1/retexture",
    "openapi/v1/rigging",
    "openapi/v1/animations",
    "openapi/v1/text-to-image",
    "openapi/v1/image-to-image",
}
BALANCE_PATH = "openapi/v1/balance"
TERMINAL = ("SUCCEEDED", "FAILED", "CANCELED")

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")


def parse_proxy_path(method: str, path: str) -> Optional[dict]:
    """Valide un chemin proxifié. Retourne {base, task_id, stream} ou None.
    `path` arrive sans slash de tête (FastAPI {path:path})."""
    p = path.strip("/")
    m = method.upper()
    if p == BALANCE_PATH:
        return {"base": p, "task_id": None, "stream": False} if m == "GET" else None
    for base in ALLOWED_BASES:
        if p == base:
            # POST = création de tâche ; GET = liste paginée
            return {"base": base, "task_id": None, "stream": False} if m in ("GET", "POST") else None
        if not p.startswith(base + "/"):
            continue
        rest = p[len(base) + 1:]
        if rest.endswith("/stream"):
            tid = rest[: -len("/stream")]
            if m == "GET" and _TASK_ID_RE.match(tid):
                return {"base": base, "task_id": tid, "stream": True}
            return None
        if _TASK_ID_RE.match(rest) and m in ("GET", "DELETE"):
            return {"base": base, "task_id": rest, "stream": False}
        return None
    return None


# ── grille tarifaire (docs.meshy.ai/en/api/pricing) ─────────────────────────
# Port exact de frontend/meshy/meshy.client.js → CREDITS. Toute divergence
# entre les deux est un bug : test_meshy_service les confronte.

def _is_hd_model(ai_model: str, model_type: str) -> bool:
    return ai_model in ("meshy-6", "latest") or model_type == "lowpoly"


def credits_text_to_3d_preview(ai_model: str = "meshy-6",
                               model_type: str = "standard") -> int:
    return 20 if _is_hd_model(ai_model, model_type) else 5


def credits_text_to_3d_refine(texture_resolution: str = "2k") -> int:
    return 15 if texture_resolution == "8k" else 10


def credits_image_to_3d(ai_model: str = "meshy-6", model_type: str = "standard",
                        should_texture: bool = True,
                        texture_resolution: str = "2k") -> int:
    smart = model_type == "smart-topology"
    if not should_texture:
        return 5 if smart else (20 if _is_hd_model(ai_model, model_type) else 5)
    if texture_resolution == "8k":
        return 20 if smart else 35
    return 15 if smart else (30 if _is_hd_model(ai_model, model_type) else 15)


def credits_retexture(texture_resolution: str = "2k") -> int:
    return 15 if texture_resolution == "8k" else 10


CREDITS_FLAT = {"remesh": 5, "convert": 1, "resize": 1, "uv-unwrap": 1,
                "rigging": 5, "animations": 3}

# formats émis sans surcoût par les tâches ; seule la conversion 3MF facture.
NATIVE_FORMATS = {"glb", "fbx", "obj", "usdz", "stl"}


def _cfg(cfg: dict, camel: str, snake: str, default):
    """Le front (meshy.client.js) parle camelCase, les tests backend snake."""
    v = cfg.get(camel)
    if v is None:
        v = cfg.get(snake)
    return default if v is None else v


def estimate_pipeline(cfg: dict) -> dict:
    """Coût total AVANT lancement — exigence produit : jamais après coup.
    Même logique que estimatePipeline() du client de référence."""
    source = _cfg(cfg, "source", "source", "text")
    ai_model = _cfg(cfg, "aiModel", "ai_model", "meshy-6")
    model_type = _cfg(cfg, "modelType", "model_type", "standard")
    res = _cfg(cfg, "textureResolution", "texture_resolution", "2k")
    with_texture = bool(_cfg(cfg, "withTexture", "with_texture", True))
    with_remesh = bool(_cfg(cfg, "withRemesh", "with_remesh", True))
    with_rig = bool(_cfg(cfg, "withRig", "with_rig", True))
    actions = _cfg(cfg, "animationActions", "animation_actions", []) or []
    formats = _cfg(cfg, "exportFormats", "export_formats", ["glb", "fbx"]) or []

    lines: list[dict] = []
    if source == "text":
        lines.append({"id": "preview", "label": "Maillage · text-to-3d preview",
                      "credits": credits_text_to_3d_preview(ai_model, model_type)})
        if with_texture:
            lines.append({"id": "texture", "label": f"Texture PBR {res} · refine",
                          "credits": credits_text_to_3d_refine(res)})
    else:
        lines.append({"id": "preview", "label": "Maillage + texture · image-to-3d",
                      "credits": credits_image_to_3d(ai_model, model_type,
                                                     with_texture, res)})
    if with_remesh:
        lines.append({"id": "remesh", "label": "Remesh · topologie",
                      "credits": CREDITS_FLAT["remesh"]})
    if with_rig:
        lines.append({"id": "rig", "label": "Auto-rig humanoïde",
                      "credits": CREDITS_FLAT["rigging"]})
    for a in actions:
        name = a.get("name") if isinstance(a, dict) else None
        aid = a.get("actionId") or a.get("action_id") if isinstance(a, dict) else a
        lines.append({"id": "animate", "label": f"Animation · {name or aid}",
                      "credits": CREDITS_FLAT["animations"]})
    extra = [f for f in formats if str(f).lower() not in NATIVE_FORMATS]
    if extra:
        lines.append({"id": "export", "label": "Conversion " + ", ".join(extra),
                      "credits": len(extra) * CREDITS_FLAT["convert"]})
    return {"total": sum(x["credits"] for x in lines), "lines": lines}


# ── binaires minuscules pour le mode mock ────────────────────────────────────

def tiny_glb() -> bytes:
    """GLB 2.0 valide minimal (un triangle) — assez pour <model-viewer>."""
    positions = struct.pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.5, 1.0, 0.0)
    gltf = {
        "asset": {"version": "2.0", "generator": "deepotus-meshy-mock"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3,
                       "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0,
                         "byteLength": len(positions)}],
        "buffers": [{"byteLength": len(positions)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binc = positions + b"\x00" * (-len(positions) % 4)
    total = 12 + 8 + len(js) + 8 + len(binc)
    return (struct.pack("<III", 0x46546C67, 2, total)
            + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binc), 0x004E4942) + binc)


def tiny_png() -> bytes:
    """PNG 1×1 gris valide (aperçu mock)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x55")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


MOCK_FILE_PREFIX = "/api/meshy3d/mockfile/"


def mock_file_bytes(fname: str) -> tuple[bytes, str]:
    """Contenu servi par /api/meshy3d/mockfile/<task>/<fname>."""
    ext = fname.rsplit(".", 1)[-1].lower()
    if ext == "glb":
        return tiny_glb(), "model/gltf-binary"
    if ext == "png":
        return tiny_png(), "image/png"
    return (f"deepotus meshy mock · {fname}\n".encode(),
            "application/octet-stream")


# ── simulateur Meshy (MESHY_MOCK=1) ──────────────────────────────────────────

class MeshyMock:
    """Réponses au format Meshy, horloge monotone, ids déterministes.
    `speed` < 1 accélère (tests) ; MESHY_MOCK_SPEED dans le .env."""

    # durées simulées (s) — proportions calquées sur les durées observées
    # en prod notées dans la maquette (118 s preview, 96 s refine, …).
    DURATIONS = {
        "text-to-3d:preview": 8.0, "text-to-3d:refine": 6.5,
        "image-to-3d": 9.0, "multi-image-to-3d": 9.0,
        "remesh": 2.0, "rigging": 3.0, "animations": 2.2, "convert": 1.2,
        "retexture": 6.0, "resize": 1.0, "uv-unwrap": 1.0,
        "text-to-image": 2.0, "image-to-image": 2.0,
    }

    def __init__(self, speed: float = 1.0):
        self.speed = max(float(speed), 0.001)
        self.tasks: dict[str, dict] = {}
        self.counter = 0

    def _kind(self, base: str, payload: dict) -> str:
        k = base.rsplit("/", 1)[-1]
        if k == "text-to-3d":
            return f"text-to-3d:{payload.get('mode') or 'preview'}"
        return k

    def _credits(self, kind: str, payload: dict) -> int:
        if kind == "text-to-3d:preview":
            return credits_text_to_3d_preview(payload.get("ai_model", "meshy-6"),
                                              payload.get("model_type", "standard"))
        if kind == "text-to-3d:refine":
            return credits_text_to_3d_refine(payload.get("texture_resolution", "2k"))
        if kind in ("image-to-3d", "multi-image-to-3d"):
            return credits_image_to_3d(payload.get("ai_model", "meshy-6"),
                                       payload.get("model_type", "standard"),
                                       payload.get("should_texture", True),
                                       payload.get("texture_resolution", "2k"))
        if kind == "retexture":
            return credits_retexture(payload.get("texture_resolution", "2k"))
        if kind == "convert":
            return len(payload.get("target_formats") or ["glb"]) * CREDITS_FLAT["convert"]
        return CREDITS_FLAT.get(kind.split(":")[0], 0)

    def create(self, base: str, payload: dict) -> tuple[int, dict]:
        kind = self._kind(base, payload or {})
        payload = payload or {}
        # refine exige un preview SUCCEEDED — même contrat que l'API réelle.
        if kind == "text-to-3d:refine":
            prev = self.tasks.get(str(payload.get("preview_task_id") or ""))
            if not prev or self._status(prev)[0] != "SUCCEEDED":
                return 400, {"message": "preview_task_id must reference a SUCCEEDED preview task"}
        if kind == "animations" and not payload.get("rig_task_id"):
            return 400, {"message": "rig_task_id is required"}
        self.counter += 1
        tid = f"mock-{self.counter:04d}"
        self.tasks[tid] = {
            "id": tid, "base": base, "kind": kind, "payload": payload,
            "t0": time.monotonic(),
            "duration": self.DURATIONS.get(kind, 3.0) * self.speed,
            "credits": self._credits(kind, payload),
        }
        return 202, {"result": tid}

    def _status(self, t: dict) -> tuple[str, int]:
        el = time.monotonic() - t["t0"]
        if el >= t["duration"]:
            return "SUCCEEDED", 100
        if el < min(0.15 * t["duration"], 0.6 * self.speed):
            return "PENDING", 0
        return "IN_PROGRESS", min(99, int(el / t["duration"] * 100))

    def _formats(self, t: dict) -> list[str]:
        fmts = [str(f).lower() for f in (t["payload"].get("target_formats") or [])]
        fmts = [f for f in fmts if f in NATIVE_FORMATS or f == "3mf"]
        return fmts or ["glb", "fbx"]

    def get(self, task_id: str) -> tuple[int, dict]:
        t = self.tasks.get(task_id)
        if not t:
            return 404, {"message": f"Task {task_id} not found"}
        status, progress = self._status(t)
        now_ms = int(time.time() * 1000)
        out = {
            "id": t["id"], "status": status, "progress": progress,
            "created_at": now_ms, "preceding_tasks": 0, "task_error": None,
            "art_style": t["payload"].get("art_style"),
            "prompt": t["payload"].get("prompt"),
        }
        if status == "SUCCEEDED":
            pre = f"{MOCK_FILE_PREFIX}{t['id']}/"
            out["model_urls"] = {f: f"{pre}model.{f}" for f in self._formats(t)}
            out["thumbnail_url"] = f"{pre}preview.png"
            out["texture_urls"] = [{"base_color": f"{pre}texture_0.png"}]
            out["consumed_credits"] = t["credits"]
            out["expires_at"] = now_ms + 3 * 24 * 3600 * 1000
            if t["kind"] == "rigging":
                out["result"] = {"rigged_model_url": f"{pre}model.glb"}
            if t["kind"] == "animations":
                out["result"] = {"animation_glb_url": f"{pre}model.glb",
                                 "animation_fbx_url": f"{pre}model.fbx"}
        else:
            out["consumed_credits"] = 0
        return 200, out

    def delete(self, task_id: str) -> tuple[int, dict]:
        if self.tasks.pop(task_id, None) is None:
            return 404, {"message": f"Task {task_id} not found"}
        return 200, {"result": task_id}

    def balance(self) -> tuple[int, dict]:
        used = sum(t["credits"] for t in self.tasks.values()
                   if self._status(t)[0] == "SUCCEEDED")
        return 200, {"balance": 8240 - used}

    async def stream(self, task_id: str) -> AsyncIterator[str]:
        """Flux SSE mock : un événement ~toutes les 300 ms jusqu'au terminal."""
        while True:
            code, task = self.get(task_id)
            if code != 200:
                yield f"event: error\ndata: {json.dumps(task)}\n\n"
                return
            yield f"data: {json.dumps(task)}\n\n"
            if task["status"] in TERMINAL:
                return
            await asyncio.sleep(min(0.3, max(0.02, 0.3 * self.speed)))


_mock: Optional[MeshyMock] = None


def mock_enabled() -> bool:
    return bool(getattr(settings, "MESHY_MOCK", False))


def get_mock() -> MeshyMock:
    global _mock
    if _mock is None:
        _mock = MeshyMock(speed=float(getattr(settings, "MESHY_MOCK_SPEED", 1.0)))
    return _mock


# ── persistance (spec §6) : journal + bibliothèque qui survit aux URLs ───────

PHASE_OF_KIND = {
    "text-to-3d:preview": "preview", "text-to-3d:refine": "texture",
    "image-to-3d": "preview", "multi-image-to-3d": "preview",
    "remesh": "remesh", "rigging": "rig", "animations": "animate",
    "convert": "export", "retexture": "texture",
    "resize": "export", "uv-unwrap": "export",
    "text-to-image": "source", "image-to-image": "source",
}


def kind_of(base: str, payload: dict | None) -> str:
    k = base.rsplit("/", 1)[-1]
    if k == "text-to-3d":
        return f"text-to-3d:{(payload or {}).get('mode') or 'preview'}"
    return k


def meshy3d_dir() -> Path:
    p = settings.outputs_path / "meshy3d"
    p.mkdir(parents=True, exist_ok=True)
    return p


async def record_created(task_id: str, base: str, payload: dict | None) -> None:
    from app.services.storage import MeshyTaskRecord, async_session_factory
    kind = kind_of(base, payload)
    async with async_session_factory() as s:
        row = await s.get(MeshyTaskRecord, task_id)
        if row is None:
            row = MeshyTaskRecord(id=task_id)
            s.add(row)
        row.kind = kind
        row.phase = PHASE_OF_KIND.get(kind, "export")
        row.status = "PENDING"
        row.progress = 0
        row.payload = json.dumps(payload or {}, ensure_ascii=False)
        row.created_at = datetime.utcnow()
        await s.commit()


async def record_state(task: dict, base: str | None = None) -> None:
    """Upsert l'état renvoyé par Meshy (GET ou événement SSE). À l'arrivée en
    SUCCEEDED, déclenche le rapatriement des binaires en tâche de fond."""
    from app.services.storage import MeshyTaskRecord, async_session_factory
    tid = str(task.get("id") or "")
    if not tid:
        return
    schedule_fetch = False
    async with async_session_factory() as s:
        row = await s.get(MeshyTaskRecord, tid)
        if row is None:
            row = MeshyTaskRecord(id=tid, created_at=datetime.utcnow())
            if base:
                row.kind = kind_of(base, None)
                row.phase = PHASE_OF_KIND.get(row.kind, "export")
            s.add(row)
        row.status = str(task.get("status") or row.status or "PENDING")
        row.progress = int(task.get("progress") or 0)
        if task.get("consumed_credits") is not None:
            row.consumed_credits = int(task["consumed_credits"])
        if task.get("model_urls"):
            row.model_urls = json.dumps(task["model_urls"])
        if task.get("thumbnail_url"):
            row.thumbnail_url = str(task["thumbnail_url"])
        if task.get("expires_at"):
            try:
                row.expires_at = datetime.utcfromtimestamp(
                    int(task["expires_at"]) / 1000)
            except (TypeError, ValueError, OSError):
                pass
        if row.status == "SUCCEEDED" and not row.local_dir:
            schedule_fetch = True
        await s.commit()
    if schedule_fetch:
        # rapatriement AVANT expires_at — spec §6 ; en tâche de fond pour ne
        # pas retarder la réponse proxifiée.
        asyncio.create_task(_safe_repatriate(tid))


_fetching: set[str] = set()


async def _safe_repatriate(task_id: str) -> None:
    # deux GET SUCCEEDED rapprochés (poll + SSE) ne doivent pas écrire le
    # même fichier en parallèle (PermissionError Windows)
    if task_id in _fetching:
        return
    _fetching.add(task_id)
    try:
        await repatriate(task_id)
    except Exception as e:  # noqa: BLE001 — le journal garde l'erreur, pas un crash
        logger.exception(f"meshy3d repatriate {task_id} failed: {e}")
    finally:
        _fetching.discard(task_id)


async def _fetch_url(url: str) -> bytes:
    """Bytes d'une URL Meshy — ou du générateur local en mode mock."""
    if url.startswith(MOCK_FILE_PREFIX):
        fname = url.rsplit("/", 1)[-1]
        return mock_file_bytes(fname)[0]
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=300.0,
                                 follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


def _safe_name(url: str, fallback: str) -> str:
    name = Path(url.split("?", 1)[0]).name or fallback
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or fallback


async def repatriate(task_id: str) -> dict:
    """Copie les binaires d'une tâche SUCCEEDED dans outputs/meshy3d/<id>/ et
    mémorise la carte {clé: fichier local}. Idempotent."""
    from app.services.storage import MeshyTaskRecord, async_session_factory
    async with async_session_factory() as s:
        row = await s.get(MeshyTaskRecord, task_id)
        if row is None:
            raise ValueError(f"meshy task {task_id} not recorded")
        urls: dict[str, str] = {}
        if row.model_urls:
            try:
                urls.update({k: v for k, v in json.loads(row.model_urls).items() if v})
            except (ValueError, AttributeError):
                pass
        if row.thumbnail_url:
            urls["thumbnail"] = row.thumbnail_url

    dest = meshy3d_dir() / re.sub(r"[^A-Za-z0-9._-]", "_", task_id)
    dest.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for key, url in urls.items():
        fname = _safe_name(url, f"{key}.bin")
        if key == "thumbnail" and "." not in fname:
            fname = "preview.png"
        target = dest / fname
        if not target.exists():
            data = await _fetch_url(url)
            target.write_bytes(data)
        files[key] = fname

    async with async_session_factory() as s:
        row = await s.get(MeshyTaskRecord, task_id)
        row.local_dir = dest.name
        row.local_files = json.dumps(files)
        await s.commit()
    logger.info(f"meshy3d: task {task_id} rapatriée ({len(files)} fichiers)")
    return {"task_id": task_id, "dir": str(dest), "files": files}


async def list_tasks(limit: int = 60) -> list[dict]:
    from sqlalchemy import select
    from app.services.storage import MeshyTaskRecord, async_session_factory
    async with async_session_factory() as s:
        rows = (await s.execute(
            select(MeshyTaskRecord)
            .order_by(MeshyTaskRecord.created_at.desc()).limit(limit)
        )).scalars().all()
    out = []
    for r in rows:
        files = {}
        if r.local_dir and r.local_files:
            try:
                files = {k: f"/api/meshy3d/files/{r.local_dir}/{v}"
                         for k, v in json.loads(r.local_files).items()}
            except ValueError:
                files = {}
        out.append({
            "id": r.id, "kind": r.kind, "phase": r.phase,
            "status": r.status, "progress": r.progress,
            "consumed_credits": r.consumed_credits,
            "thumbnail_url": r.thumbnail_url,
            "expires_at": r.expires_at.isoformat() + "Z" if r.expires_at else None,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            "payload": json.loads(r.payload) if r.payload else {},
            "local_files": files,
        })
    return out


# ── proxy vers l'API réelle ──────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.MESHY_API_KEY}",
            "Content-Type": "application/json"}


async def proxy_request(method: str, path: str, body: bytes | None,
                        params: dict) -> tuple[int, bytes, str]:
    """Recopie la requête vers api.meshy.ai en injectant la clé (spec §1)."""
    url = f"{MESHY_API}/{path.strip('/')}"
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as c:
        r = await c.request(method, url, headers=_headers(),
                            content=body or None, params=params or None)
    return r.status_code, r.content, r.headers.get("content-type", "application/json")


async def proxy_stream(path: str) -> AsyncIterator[str]:
    """Relais SSE en streaming (spec §7 « reste à câbler ») : progression à la
    seconde sans polling. Chaque événement `data:` terminal est enregistré."""
    url = f"{MESHY_API}/{path.strip('/')}"
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=None) as c:
        async with c.stream("GET", url, headers={
                **_headers(), "Accept": "text/event-stream"}) as r:
            if r.status_code != 200:
                detail = (await r.aread()).decode("utf-8", "replace")[:400]
                yield f"event: error\ndata: {json.dumps({'status': r.status_code, 'detail': detail})}\n\n"
                return
            async for line in r.aiter_lines():
                if line.startswith("data:"):
                    try:
                        task = json.loads(line[5:].strip())
                        if task.get("status") in TERMINAL:
                            await record_state(task)
                    except (ValueError, KeyError):
                        pass
                yield line + "\n"


def expiring_soon(rows: list[dict], within_hours: int = 24) -> list[dict]:
    """Tâches SUCCEEDED non rapatriées dont l'URL expire bientôt (garde-fou)."""
    limit = datetime.utcnow() + timedelta(hours=within_hours)
    out = []
    for r in rows:
        if r["status"] != "SUCCEEDED" or r["local_files"]:
            continue
        exp = r.get("expires_at")
        if exp and datetime.fromisoformat(exp.rstrip("Z")) < limit:
            out.append(r)
    return out
