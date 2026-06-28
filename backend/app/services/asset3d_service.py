"""Game Assets 3D: image -> (optional multi-view) -> 3D engine -> mesh + shots.

See docs/superpowers/specs/2026-06-28-game-assets-3d-design.md. Per-engine
argument/result shapes are verified against live fal calls (route smoke); the
adapters below isolate those quirks so the orchestrator stays engine-agnostic.
"""
from __future__ import annotations

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
        a = {"image_url": primary, "texture": bool(opts.get("textures", True)),
             "output_format": fmt, "pbr": True}
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
    for key in ("model_mesh", "mesh", "model", "glb", "model_glb", "output"):
        if key in res and _url(res[key]):
            mesh = _url(res[key])
            break
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


def _download(url, dest):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        dest.write_bytes(r.read())
    return True


async def generate_asset3d(payload: dict, job_id: str):
    """Upload image -> optional multi-view -> 3D engine -> download mesh formats,
    shots and poster under outputs/assets3d/{job_id}/. Returns a summary dict."""
    import shutil
    from app.config import settings

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    formats = [f.lower() for f in (payload.get("formats") or ["glb"])]
    if "glb" not in formats:
        formats = ["glb"] + formats  # GLB always (preview + interchange)

    out_dir = settings.outputs_path / "assets3d" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    src = settings.images_path / payload.get("image_filename", "")
    src_url = await _upload(src)

    # shots: shot_0 = source, shot_1..N = multi-view boost
    shutil.copy2(src, out_dir / "shot_0.png")
    shots = ["shot_0.png"]
    image_urls = [src_url]
    if payload.get("multiview"):
        for i, pr in enumerate(view_prompts(int(payload.get("views", 3)), payload.get("subject", "")), 1):
            u = await _seedream_edit(src_url, pr)
            if u:
                _download(u, out_dir / f"shot_{i}.png")
                shots.append(f"shot_{i}.png")
                image_urls.append(u)

    base_opts = {"format": "glb", "textures": payload.get("textures", True),
                 "quality": payload.get("quality", "medium"), "tpose": payload.get("tpose")}
    result = await _run_engine(engine, build_engine_args(engine, image_urls, base_opts))

    files = {}
    if result.get("mesh_url"):
        _download(result["mesh_url"], out_dir / "model.glb")
        files["glb"] = str(out_dir / "model.glb")
    for ext, url in (result.get("format_urls") or {}).items():
        if ext in formats:
            _download(url, out_dir / f"model.{ext}")
            files[ext] = str(out_dir / f"model.{ext}")
    # extra formats not returned by the first call -> targeted re-export
    for f in formats:
        if f != "glb" and f not in files and f in ENGINES[engine]["formats"]:
            r2 = await _run_engine(engine, build_engine_args(engine, image_urls,
                {"format": f, "textures": payload.get("textures", True)}))
            if r2.get("mesh_url"):
                _download(r2["mesh_url"], out_dir / f"model.{f}")
                files[f] = str(out_dir / f"model.{f}")
    if result.get("preview_url"):
        _download(result["preview_url"], out_dir / "preview.png")

    return {"glb": files.get("glb"), "files": files, "shots": shots,
            "preview": str(out_dir / "preview.png"), "engine": engine}
