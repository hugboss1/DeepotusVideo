"""Game Assets 3D: image -> (optional multi-view) -> 3D engine -> mesh + shots.

See docs/superpowers/specs/2026-06-28-game-assets-3d-design.md. Per-engine
argument/result shapes are verified against live fal calls (route smoke); the
adapters below isolate those quirks so the orchestrator stays engine-agnostic.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ANGLES = [
    "front view, full body, T-pose, plain neutral background",
    "back view, full body, plain neutral background",
    "left 3/4 side view, full body, plain neutral background",
    "right 3/4 side view, full body, plain neutral background",
]


def view_prompts(n: int, subject: str) -> list[str]:
    """N angle prompts (1..4) for the Seedream multi-view boost."""
    n = 1 if n < 1 else 4 if n > 4 else n
    subj = (subject or "the same character/object, consistent design").strip()
    return [f"{subj}, {a}" for a in _ANGLES[:n]]


# endpoint + the export formats the engine can emit natively.
ENGINES = {
    "tripo":   {"endpoint": "tripo3d/tripo/v2.5/image-to-3d", "formats": ["glb", "fbx", "obj", "stl", "usdz"]},
    "hunyuan": {"endpoint": "fal-ai/hunyuan3d/v2",            "formats": ["glb", "obj"]},
    "trellis": {"endpoint": "fal-ai/trellis",                "formats": ["glb"]},
    "rodin":   {"endpoint": "fal-ai/hyper3d/rodin",          "formats": ["glb", "fbx", "obj", "stl", "usdz"]},
    "triposr": {"endpoint": "fal-ai/triposr",                "formats": ["glb"]},
}


def build_engine_args(engine: str, image_urls: list[str], opts: dict) -> dict:
    """Map the common request to the chosen engine's fal arguments."""
    fmt = (opts.get("format") or "glb").lower()
    primary = image_urls[0] if image_urls else None
    if engine == "rodin":
        return {"input_image_urls": image_urls, "geometry_file_format": fmt,
                "material": "PBR", "quality_mesh_option": opts.get("quality", "medium"),
                "TAPose": bool(opts.get("tpose")), "use_original_alpha": True, "preview_render": True}
    if engine == "tripo":
        # Tripo's `texture` is a literal: 'no' | 'standard' | 'HD' (not a bool).
        if not opts.get("textures", True):
            tex = "no"
        elif str(opts.get("quality", "")).lower() in ("high", "hd"):
            tex = "HD"
        else:
            tex = "standard"
        a = {"image_url": primary, "texture": tex, "output_format": fmt, "pbr": True}
        if len(image_urls) > 1:
            a["multiview_images"] = image_urls
        return a
    if engine == "hunyuan":
        return {"input_image_url": primary, "textured_mesh": bool(opts.get("textures", True)),
                "output_format": fmt}
    # trellis / triposr / fallback
    return {"image_url": primary, "output_format": fmt}


def parse_engine_result(engine: str, res: dict) -> dict:
    """Pull mesh URL (+ any extra-format URLs) + texture URLs + a preview image
    out of whatever shape the engine returned. Tolerant of common fal fields."""
    def _url(v):
        if isinstance(v, dict):
            return v.get("url") or v.get("file_url")
        if isinstance(v, str):
            return v
        return None

    mesh = None
    # tripo v2.5 (pbr:true) livre le mesh texturé dans pbr_model — model_mesh
    # peut être null (constaté le 20/07/2026, schéma OpenAPI fal à l'appui)
    for key in ("model_mesh", "pbr_model", "base_model",
                "mesh", "model", "glb", "model_glb", "output"):
        if key in res and _url(res[key]):
            mesh = _url(res[key])
            break
    if mesh is None:
        from loguru import logger
        logger.warning(f"parse_engine_result[{engine}]: no mesh url in "
                       f"keys={sorted(res.keys())}")
    meshes = {}
    for m in (res.get("model_meshes") or []):
        u = _url(m)
        if u:
            ext = u.rsplit(".", 1)[-1].split("?")[0].lower()
            meshes[ext] = u
    textures = [t for t in (_url(x) for x in (res.get("textures") or [])) if t]
    preview = None
    for key in ("preview_render", "rendered_image", "preview", "thumbnail"):
        if key in res and _url(res[key]):
            preview = _url(res[key])
            break
    return {"mesh_url": mesh, "format_urls": meshes, "texture_urls": textures, "preview_url": preview}


# ── orchestration seams (patched in tests; real impls call fal/HTTP) ──────────
async def _upload(path):
    from app.services.fal_service import FalSeedanceClient
    return await FalSeedanceClient.upload_image(path)


async def _run_engine(engine, args):
    import fal_client
    ep = ENGINES[engine]["endpoint"]
    try:
        res = await fal_client.subscribe_async(ep, arguments=args, with_logs=False)
    except Exception as e:
        raise RuntimeError(f"fal.ai: {e}") from e
    return parse_engine_result(engine, res)


async def _seedream_edit(image_url, prompt):
    import fal_client
    res = await fal_client.subscribe_async(
        "fal-ai/bytedance/seedream/v4/edit",
        arguments={"image_urls": [image_url], "prompt": prompt, "num_images": 1})
    imgs = res.get("images") or []
    return imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else None


def _download(url, dest, timeout=120):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:
        dest.write_bytes(r.read())
    return True


async def generate_asset3d(payload: dict, job_id: str, on_step=None):
    """Upload image -> optional multi-view -> 3D engine -> download mesh formats,
    shots and poster under outputs/assets3d/{job_id}/. Returns a summary dict.
    `on_step(label, pct)` (optional async) is awaited at each phase for live UI."""
    import asyncio
    import shutil
    from pathlib import Path
    from app.config import settings

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    formats = [f.lower() for f in (payload.get("formats") or ["glb"])]
    if "glb" not in formats:
        formats = ["glb"] + formats  # GLB always (preview + interchange)

    out_dir = settings.outputs_path / "assets3d" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    await _step("Uploading", 10)
    # basename + containment check: the raw payload value must never escape the
    # Library folder (it gets uploaded to fal, so a traversal would exfiltrate it)
    fn = Path(str(payload.get("image_filename") or "")).name
    src = settings.images_path / fn
    if not fn or not src.is_file() \
            or not str(src.resolve()).startswith(str(settings.images_path.resolve())):
        raise ValueError(f"Image not found in Library: {payload.get('image_filename')!r}")
    src_url = await _upload(src)

    # shots: shot_0 = source, shot_1..N = multi-view boost
    shutil.copy2(src, out_dir / "shot_0.png")
    shots = ["shot_0.png"]
    image_urls = [src_url]
    if payload.get("multiview"):
        try:
            _nv = max(1, min(4, int(payload.get("views", 3))))
        except (TypeError, ValueError):
            _nv = 3
        for i, pr in enumerate(view_prompts(_nv, payload.get("subject", "")), 1):
            await _step(f"View {i}/{_nv}", 10 + int(40 * i / max(1, _nv)))
            try:
                u = await _seedream_edit(src_url, pr)
            except Exception as e:
                # the multi-view boost is best-effort: keep the views we already
                # have instead of failing the whole (already partly paid) job
                logger.warning(f"multi-view {i}/{_nv} failed (continuing): {e}")
                u = None
            if u:
                await asyncio.to_thread(_download, u, out_dir / f"shot_{i}.png")
                shots.append(f"shot_{i}.png")
                image_urls.append(u)

    await _step(f"Running {engine}", 60)
    base_opts = {"format": "glb", "textures": payload.get("textures", True),
                 "quality": payload.get("quality", "medium"), "tpose": payload.get("tpose")}
    result = await _run_engine(engine, build_engine_args(engine, image_urls, base_opts))

    files = {}
    if result.get("mesh_url"):
        await asyncio.to_thread(_download, result["mesh_url"], out_dir / "model.glb")
        files["glb"] = str(out_dir / "model.glb")
    else:
        # sans mesh principal le job n'a aucune valeur : échouer visiblement
        # plutôt que de terminer "done" avec un dossier sans model.glb
        # (cas e9e150d2 du 20/07/2026 — pbr_model non parsé)
        raise RuntimeError(
            f"{engine}: aucun mesh dans la réponse fal (shots conservés)")
    for ext, url in (result.get("format_urls") or {}).items():
        if ext in formats:
            await asyncio.to_thread(_download, url, out_dir / f"model.{ext}")
            files[ext] = str(out_dir / f"model.{ext}")
    # extra formats not returned by the first call -> targeted re-export
    for f in formats:
        if f != "glb" and f not in files and f in ENGINES[engine]["formats"]:
            r2 = await _run_engine(engine, build_engine_args(engine, image_urls,
                {"format": f, "textures": payload.get("textures", True)}))
            if r2.get("mesh_url"):
                await asyncio.to_thread(_download, r2["mesh_url"], out_dir / f"model.{f}")
                files[f] = str(out_dir / f"model.{f}")
    if result.get("preview_url"):
        await asyncio.to_thread(_download, result["preview_url"], out_dir / "preview.png")

    await _step("Complete", 100)
    preview_p = out_dir / "preview.png"
    return {"glb": files.get("glb"), "files": files, "shots": shots,
            "preview": str(preview_p) if preview_p.is_file() else None,
            "skipped_formats": [f for f in formats if f not in files],
            "engine": engine}
