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
