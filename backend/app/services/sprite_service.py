"""Game Assets 2D — Sprite Lab: video render -> frames -> sprite sheet.

See docs/superpowers/specs/2026-07-19-game-assets-2d-sprites-design.md (9a).
Mirrors asset3d_service.py: the orchestrator is pure logic; everything that
leaves the process (ffmpeg/ffprobe subprocesses, fal upload/rembg, downloads)
goes through module-level seams so tests can patch them.

Outputs land in outputs/sprites/{job}/ :
  sheet.png, frames/000.png…, preview.gif, manifest.json,
  sheet.unity.json + SpriteSheetImporter.cs (pack Unity).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".gif"}
_CELL_SIZES = (128, 256, 512)


# ── request normalization (shared by the route's fail-fast and the job) ──────
def normalize_opts(body: dict) -> dict:
    """Validate/normalize the sprite request knobs. Raises ValueError with a
    user-readable message on anything out of range (the route maps it to 400)."""
    body = body or {}

    def _int(name, default, lo, hi):
        raw = body.get(name)
        if raw is None or raw == "":
            return default
        try:
            v = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer ({lo}-{hi})")
        if not lo <= v <= hi:
            raise ValueError(f"{name} must be between {lo} and {hi}")
        return v

    fps = _int("fps_sample", 8, 1, 24)
    max_frames = _int("max_frames", 16, 4, 64)

    method = str(body.get("remove_bg") or "none").lower()
    if method not in ("none", "api", "local"):
        raise ValueError("remove_bg must be one of: none, api, local")

    trim = str(body.get("trim") or "animation").lower()
    if trim not in ("animation", "tight"):
        raise ValueError("trim must be 'animation' or 'tight'")

    cell = body.get("cell") or {}
    if not isinstance(cell, dict):
        raise ValueError("cell must be an object {size, align}")
    try:
        size = int(cell.get("size") or 256)
    except (TypeError, ValueError):
        raise ValueError(f"cell.size must be one of {_CELL_SIZES}")
    if size not in _CELL_SIZES:
        raise ValueError(f"cell.size must be one of {_CELL_SIZES}")
    align = str(cell.get("align") or "center").lower()
    if align not in ("feet", "center"):
        raise ValueError("cell.align must be 'feet' or 'center'")

    columns = body.get("columns", "auto")
    if columns != "auto":
        try:
            columns = int(columns)
        except (TypeError, ValueError):
            raise ValueError("columns must be 'auto' or an integer (1-32)")
        if not 1 <= columns <= 32:
            raise ValueError("columns must be 'auto' or an integer (1-32)")

    # pixel-art per-frame op (chantier 9b): normalized by pixel_ops, applied
    # per frame in generate_sprites (direct import, no HTTP). scale is forced
    # to 1 — cell fitting handles the size (NEAREST keeps the pixels crisp).
    pixel = body.get("pixel") or None
    if pixel is not None:
        from app.services.pixel_ops import normalize_pixel_opts
        pixel = dict(normalize_pixel_opts(pixel), scale=1)

    return {"fps": fps, "max_frames": max_frames, "remove_bg": method,
            "trim": trim, "cell_size": size, "align": align,
            "columns": columns, "pixel": pixel}


# ── source resolution (job render / user upload / on-disk video) ─────────────
def _inside(p: Path, root: Path) -> bool:
    rp, rr = str(p.resolve()), str(root.resolve())
    return rp == rr or rp.startswith(rr + os.sep)


async def resolve_source(source: dict) -> Path:
    """Resolve {kind: job|upload|video, ...} to an existing video file.
    Raises ValueError on anything missing or escaping the outputs folder
    (path-traversal guard: user-supplied paths must never leave outputs)."""
    from app.config import settings

    source = source or {}
    kind = str(source.get("kind") or "").lower()
    outputs = settings.outputs_path

    if kind == "job":
        job_id = str(source.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("source.job_id is required for kind 'job'")
        from app.services.storage import JobRecord, async_session_factory
        async with async_session_factory() as s:
            jr = await s.get(JobRecord, job_id)
        if jr is None:
            raise ValueError(f"Job not found: {job_id}")
        for cand in (jr.final_video_path, jr.video_path):
            if cand and Path(cand).is_file() \
                    and Path(cand).suffix.lower() in _VIDEO_EXTS:
                return Path(cand)
        raise ValueError(f"Job {job_id} has no video file on disk")

    if kind == "upload":
        fn = Path(str(source.get("filename") or "")).name  # basename only
        p = outputs / "uploads" / fn
        if not fn or not p.is_file() or not _inside(p, outputs):
            raise ValueError(f"Upload not found: {source.get('filename')!r}")
        return p

    if kind == "video":
        raw = str(source.get("path") or source.get("file") or "").strip()
        if not raw:
            raise ValueError("source.path is required for kind 'video'")
        p = Path(raw)
        if not p.is_absolute():
            p = outputs / raw
        if not _inside(p, outputs):
            raise ValueError("source.path must stay inside the outputs folder")
        p = p.resolve()
        if not p.is_file() or p.suffix.lower() not in _VIDEO_EXTS:
            raise ValueError(f"Video not found in outputs: {raw!r}")
        return p

    raise ValueError(f"Unknown source kind: {kind!r} (expected job|upload|video)")


# ── seams (patched in tests; real impls shell out / call fal) ────────────────
def _ffprobe_duration(path: Path) -> float:
    from app.services.ffmpeg_service import FFmpegMerger
    try:
        return float(FFmpegMerger.probe_dur(Path(path)) or 0.0)
    except Exception:
        return 0.0


def _extract_frames(src: Path, fps: int, out_dir: Path) -> list[Path]:
    """ffmpeg frame extraction at fps_sample. Returns the sorted PNG paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", f"fps={fps}",
           str(out_dir / "raw_%04d.png")]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True,
                       timeout=600)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg frame extraction failed: {(e.stderr or '')[-300:]}") from e
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found on PATH")
    return sorted(out_dir.glob("raw_*.png"))


async def _upload(path: Path) -> str:
    from app.services.fal_service import FalSeedanceClient
    return await FalSeedanceClient.upload_image(path)


async def _rembg_api(url: str) -> str:
    """fal rembg on an uploaded frame; returns the detoured image URL."""
    import fal_client
    res = await fal_client.subscribe_async(
        "fal-ai/imageutils/rembg", arguments={"image_url": url})
    out = ((res or {}).get("image") or {}).get("url") or \
        next((im.get("url") for im in (res or {}).get("images", [])
              if im.get("url")), None)
    if not out:
        raise RuntimeError("rembg returned no image")
    return out


def _download(url: str, dest: Path, timeout: int = 120):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:
        dest.write_bytes(r.read())
    return True


def _rembg_local_bytes(data: bytes) -> bytes:
    from rembg import remove as _remove  # availability checked by the route
    return _remove(data)


# ── frame helpers (pure PIL) ─────────────────────────────────────────────────
def _content_bbox(img):
    """Bounding box of the actual content: alpha-based when the frame has an
    alpha channel (post remove-bg), else PIL's non-black bbox (raw video)."""
    if "A" in img.getbands():
        return img.getchannel("A").getbbox()
    return img.getbbox()


def compute_grid(n: int, columns) -> tuple[int, int]:
    """(cols, rows) — 'auto' aims for a near-square sheet."""
    n = max(1, int(n))
    cols = math.ceil(math.sqrt(n)) if columns == "auto" \
        else max(1, min(int(columns), n))
    return cols, math.ceil(n / cols)


def _fit_into_cell(img, size: int, align: str, resample=None):
    """Scale (contain) into a size×size transparent cell. Horizontal center;
    vertical: 'feet' anchors the content bottom to the cell bottom, 'center'
    centers it. `resample`: NEAREST for pixel-art frames (LANCZOS would blend
    the palette away), LANCZOS otherwise."""
    from PIL import Image
    w, h = img.size
    if not w or not h:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scale = min(size / w, size / h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    if resample is None:          # NB: Image.NEAREST == 0, donc pas de `or`
        resample = Image.LANCZOS
    im2 = img.resize((nw, nh), resample)
    if im2.mode != "RGBA":
        im2 = im2.convert("RGBA")
    cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - nw) // 2
    y = (size - nh) if align == "feet" else (size - nh) // 2
    cell.paste(im2, (x, y), im2)
    return cell


def _gif_frame(rgba):
    """RGBA -> palettized GIF frame, palette index 255 = transparent."""
    from PIL import Image
    alpha = rgba.getchannel("A")
    p = rgba.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
    mask = alpha.point(lambda a: 255 if a <= 128 else 0)
    p.paste(255, mask)
    return p


# ── pack Unity ───────────────────────────────────────────────────────────────
# One-file Editor script (no fragile .meta generation): the user drops it in
# Assets/Editor/, puts sheet.png + sheet.unity.json under Assets/, selects the
# texture and runs the menu item — it applies Sprite Multiple slicing from the
# JSON. Flat JSON fields on purpose: Unity's JsonUtility can't read nested dicts.
UNITY_IMPORTER_CS = """\
// Généré par DeepotusVideoGen — Sprite Lab (chantier 9a).
// 1. Copiez ce fichier dans Assets/Editor/ de votre projet Unity.
// 2. Importez sheet.png ET sheet.unity.json côte à côte sous Assets/.
// 3. Sélectionnez la texture sheet.png, puis menu
//    Tools ▸ Deepotus ▸ Slice Selected Sprite Sheet.
// Le script lit le .unity.json voisin et découpe la texture en Sprites
// (mode Multiple, pivots par frame) — aucun .meta généré à la main.
using System.IO;
using UnityEditor;
using UnityEngine;

public static class DeepotusSpriteSheetImporter
{
    [System.Serializable] private class Frame
    { public string name; public float x, y, w, h, pivotX, pivotY; }

    [System.Serializable] private class Sheet
    { public string name; public int pixelsPerUnit; public Frame[] frames; }

    [MenuItem("Tools/Deepotus/Slice Selected Sprite Sheet")]
    public static void Slice()
    {
        var tex = Selection.activeObject as Texture2D;
        if (tex == null)
        {
            EditorUtility.DisplayDialog("Sprite Lab",
                "Sélectionnez d'abord la texture sheet.png dans le projet.", "OK");
            return;
        }
        string texPath = AssetDatabase.GetAssetPath(tex);
        string jsonPath = Path.Combine(
            Path.GetDirectoryName(texPath),
            Path.GetFileNameWithoutExtension(texPath) + ".unity.json");
        if (!File.Exists(jsonPath))
        {
            EditorUtility.DisplayDialog("Sprite Lab",
                "Fichier introuvable : " + jsonPath, "OK");
            return;
        }
        var sheet = JsonUtility.FromJson<Sheet>(File.ReadAllText(jsonPath));
        var importer = (TextureImporter)AssetImporter.GetAtPath(texPath);
        importer.textureType = TextureImporterType.Sprite;
        importer.spriteImportMode = SpriteImportMode.Multiple;
        importer.spritePixelsPerUnit = sheet.pixelsPerUnit;
        importer.filterMode = FilterMode.Point;
        importer.mipmapEnabled = false;
        var metas = new SpriteMetaData[sheet.frames.Length];
        for (int i = 0; i < sheet.frames.Length; i++)
        {
            var f = sheet.frames[i];
            metas[i] = new SpriteMetaData
            {
                name = f.name,
                rect = new Rect(f.x, f.y, f.w, f.h),
                alignment = (int)SpriteAlignment.Custom,
                pivot = new Vector2(f.pivotX, f.pivotY),
            };
        }
        importer.spritesheet = metas;
        EditorUtility.SetDirty(importer);
        importer.SaveAndReimport();
        Debug.Log("Sprite Lab : " + sheet.frames.Length +
                  " sprites découpés depuis " + texPath);
    }
}
"""


def build_unity_pack(manifest: dict, sheet_h: int, align: str) -> dict:
    """sheet.unity.json content. Unity rects are bottom-left origin (PIL is
    top-left) -> y is flipped here. Pivot: feet = bottom-center of the cell."""
    px, py = (0.5, 0.0) if align == "feet" else (0.5, 0.5)
    frames = []
    for f in manifest["frames"]:
        r = f["rect"]
        frames.append({"name": f"frame_{f['index']:03d}",
                       "x": r["x"], "y": sheet_h - (r["y"] + r["h"]),
                       "w": r["w"], "h": r["h"], "pivotX": px, "pivotY": py})
    return {"name": "sheet", "pixelsPerUnit": manifest["grid"]["cell_w"],
            "frames": frames}


# ── zip export (sheet + frames + manifests + pack Unity) ─────────────────────
def build_zip_bytes(out_dir: Path) -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("sheet.png", "preview.gif", "manifest.json",
                     "sheet.unity.json", "SpriteSheetImporter.cs"):
            p = out_dir / name
            if p.is_file():
                z.write(p, name)
        fdir = out_dir / "frames"
        if fdir.is_dir():
            for f in sorted(fdir.glob("*.png")):
                z.write(f, f"frames/{f.name}")
    return buf.getvalue()


# ── sheet assembly (sync, runs in a worker thread) ───────────────────────────
def _assemble(frame_files: list[tuple[Path, bool]], opts: dict, out_dir: Path,
              source_info: dict) -> dict:
    """Trim/align/scale every frame into cells, build sheet.png + preview.gif
    + manifest.json + the Unity pack. Two passes over the files (bbox, then
    compose) so at most one full frame + the sheet live in memory."""
    from PIL import Image

    size, align, trim = opts["cell_size"], opts["align"], opts["trim"]
    resample = Image.NEAREST if opts.get("pixel") else Image.LANCZOS

    # pass 1 — union bbox of the content across frames (tight mode)
    union = None
    if trim == "tight":
        for path, _ in frame_files:
            with Image.open(path) as im:
                bb = _content_bbox(im)
            if bb:
                union = bb if union is None else (
                    min(union[0], bb[0]), min(union[1], bb[1]),
                    max(union[2], bb[2]), max(union[3], bb[3]))
    offset = (union[0], union[1]) if union else (0, 0)

    n = len(frame_files)
    cols, rows = compute_grid(n, opts["columns"])
    sheet = Image.new("RGBA", (cols * size, rows * size), (0, 0, 0, 0))
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # pass 2 — crop (tight) -> cell -> paste into the sheet + save the frame
    manifest_frames, gif_frames = [], []
    for i, (path, bg_removed) in enumerate(frame_files):
        with Image.open(path) as im:
            im = im.convert("RGBA")
            if union:
                im = im.crop(union)
            cell = _fit_into_cell(im, size, align, resample)
        fname = f"{i:03d}.png"
        cell.save(frames_dir / fname, format="PNG")
        x, y = (i % cols) * size, (i // cols) * size
        sheet.paste(cell, (x, y))
        gif_frames.append(_gif_frame(cell))
        manifest_frames.append({
            "index": i, "file": f"frames/{fname}",
            "rect": {"x": x, "y": y, "w": size, "h": size},
            "offset": {"x": offset[0], "y": offset[1]},
            "bg_removed": bool(bg_removed),
        })

    sheet.save(out_dir / "sheet.png", format="PNG")

    fps = opts["fps"]
    gif_frames[0].save(
        out_dir / "preview.gif", save_all=True, append_images=gif_frames[1:],
        duration=max(20, int(1000 / fps)), loop=0, disposal=2, transparency=255)

    manifest = {
        "version": 1,
        "source": source_info,
        "grid": {"cols": cols, "rows": rows, "cell_w": size, "cell_h": size},
        "frames": manifest_frames,
        "fps": fps,
        "trim": trim,
        "align": align,
        "pixel": opts.get("pixel"),
        "created_at": datetime.now(timezone.utc)
                              .isoformat(timespec="seconds")
                              .replace("+00:00", "Z"),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    unity = build_unity_pack(manifest, sheet.height, align)
    (out_dir / "sheet.unity.json").write_text(
        json.dumps(unity, indent=2), encoding="utf-8")
    (out_dir / "SpriteSheetImporter.cs").write_text(
        UNITY_IMPORTER_CS, encoding="utf-8")

    return {"sheet": str(out_dir / "sheet.png"),
            "preview": str(out_dir / "preview.gif"),
            "manifest": str(out_dir / "manifest.json"),
            "frames": n,
            "grid": manifest["grid"]}


# ── orchestrator ─────────────────────────────────────────────────────────────
async def generate_sprites(payload: dict, job_id: str, on_step=None) -> dict:
    """Video -> frames (ffmpeg) -> optional remove-bg -> trim/align -> sheet
    + preview + manifests under outputs/sprites/{job_id}/. Returns a summary.
    `on_step(label, pct)` (optional async) is awaited at each phase."""
    from app.config import settings

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    opts = normalize_opts(payload)
    out_dir = settings.outputs_path / "sprites" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw"

    await _step("Resolving source", 5)
    src = await resolve_source(payload.get("source") or {})
    duration = await asyncio.to_thread(_ffprobe_duration, src)

    await _step("Extracting frames", 15)
    raw = await asyncio.to_thread(_extract_frames, src, opts["fps"], raw_dir)
    if not raw:
        raise RuntimeError("ffmpeg extracted no frames from the source video")

    sampled = len(raw) > opts["max_frames"]
    if sampled:
        # even subsample across the whole clip (keeps the loop cycle intact)
        m = opts["max_frames"]
        idx = [round(i * (len(raw) - 1) / (m - 1)) for i in range(m)]
        raw = [raw[i] for i in dict.fromkeys(idx)]

    # remove-bg per frame (batch). One failed frame never kills the job: it is
    # kept un-detoured and flagged in the manifest (spec 9a).
    method = opts["remove_bg"]
    flags = [None] * len(raw)  # None = pending; bool = detoured ok / kept as-is
    if method == "api":
        sem = asyncio.Semaphore(3)
        done = 0

        async def _one(i, path):
            nonlocal done
            async with sem:
                try:
                    url = await _upload(path)
                    out_url = await _rembg_api(url)
                    dest = raw_dir / f"det_{i:04d}.png"
                    await asyncio.to_thread(_download, out_url, dest)
                    ok = True
                except Exception as e:
                    logger.warning(
                        f"sprite {job_id}: remove-bg frame {i} failed "
                        f"(kept as-is): {e}")
                    dest, ok = path, False
            done += 1
            await _step(f"Remove-BG {done}/{len(raw)}",
                        30 + int(30 * done / len(raw)))
            return i, dest, ok

        results = await asyncio.gather(*(_one(i, p) for i, p in enumerate(raw)))
        for i, dest, ok in results:
            raw[i], flags[i] = dest, ok
    elif method == "local":
        for i, path in enumerate(raw):
            try:
                data = await asyncio.to_thread(
                    _rembg_local_bytes, path.read_bytes())
                dest = raw_dir / f"det_{i:04d}.png"
                dest.write_bytes(data)
                raw[i], flags[i] = dest, True
            except Exception as e:
                logger.warning(f"sprite {job_id}: local remove-bg frame {i} "
                               f"failed (kept as-is): {e}")
                flags[i] = False
            await _step(f"Remove-BG {i + 1}/{len(raw)}",
                        30 + int(30 * (i + 1) / len(raw)))
    else:
        flags = [False] * len(raw)  # nothing detoured (and nothing failed)

    # pixel-art per frame (9b) — local PIL, after remove-bg so the quantizer
    # sees the final content, before trim/assembly which run on the result
    if opts["pixel"]:
        from PIL import Image
        from app.services.pixel_ops import pixelate

        def _pix_file(src_path: Path, dest: Path):
            with Image.open(src_path) as im:
                out = pixelate(im, opts["pixel"])
            out.save(dest, format="PNG")

        for i, path in enumerate(raw):
            dest = raw_dir / f"pix_{i:04d}.png"
            await asyncio.to_thread(_pix_file, path, dest)
            raw[i] = dest
            await _step(f"Pixel-art {i + 1}/{len(raw)}",
                        60 + int(10 * (i + 1) / len(raw)))

    await _step("Assembling sheet", 75)
    source_info = {"kind": str((payload.get("source") or {}).get("kind") or ""),
                   "file": src.name, "duration_s": round(duration, 2),
                   "fps_sample": opts["fps"], "sampled": sampled,
                   "remove_bg": method}
    frame_files = list(zip(raw, [bool(f) for f in flags]))
    summary = await asyncio.to_thread(
        _assemble, frame_files, opts, out_dir, source_info)

    await _step("Writing manifests", 90)
    shutil.rmtree(raw_dir, ignore_errors=True)

    await _step("Complete", 100)
    summary["bg_failed"] = [i for i, (_, ok) in enumerate(frame_files)
                            if method != "none" and not ok]
    summary["remove_bg"] = method
    summary["out_dir"] = str(out_dir)
    return summary
