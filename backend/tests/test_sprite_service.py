"""Recette chantier 9a — sprite_service (Game Assets 2D, Sprite Lab).

Lancé avec le python embarqué de l'app installée, ffmpeg du bin de l'app sur
le PATH, et DEEPOTUS_DATA_DIR isolé :

  set DEEPOTUS_DATA_DIR=<tmp>
  set PATH=C:\\Users\\olivi\\AppData\\Local\\DeepotusVideoGen\\bin;%PATH%
  runtime\\python\\python.exe -m pytest backend/tests/test_sprite_service.py -v

Couvre : grille/manifest cohérents sur une vidéo synthétique (vrai ffmpeg),
rejet path-traversal, survie à l'échec d'une frame remove-bg, tight vs
animation, pack Unity présent dans le zip, pricing sprite2d.
"""
import asyncio
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.config import settings
from app.services import sprite_service as S


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(payload, job_id, steps=None):
    async def on_step(label, pct):
        if steps is not None:
            steps.append((label, pct))
    return asyncio.run(S.generate_sprites(payload, job_id, on_step=on_step))


def _payload(**over):
    p = {"source": {"kind": "video", "path": "videos/synth.mp4"},
         "fps_sample": 6, "max_frames": 8, "remove_bg": "none",
         "trim": "animation", "cell": {"size": 128, "align": "center"},
         "columns": "auto"}
    p.update(over)
    return p


def _patch_chroma_rembg(monkeypatch, fail_marker=None):
    """Patch the fal seams with a deterministic local chroma-key: green pixels
    become transparent. Exercises the real per-frame plumbing without any
    network call. `fail_marker`: substring of the frame path that must FAIL."""
    from PIL import ImageChops

    async def up(path):
        return f"mem://{path}"

    async def rem(url):
        if fail_marker and fail_marker in url:
            raise RuntimeError("fal.ai: 429 rate limited (simulated)")
        return url

    def dl(url, dest, timeout=120):
        src = Path(url[len("mem://"):])
        img = Image.open(src).convert("RGBA")
        r, g, b, a = img.split()
        gm = g.point(lambda v: 255 if v > 120 else 0)
        rm = r.point(lambda v: 255 if v < 100 else 0)
        bm = b.point(lambda v: 255 if v < 100 else 0)
        key = ImageChops.multiply(ImageChops.multiply(gm, rm), bm)
        img.putalpha(ImageChops.subtract(a, key))
        img.save(dest, format="PNG")
        return True

    monkeypatch.setattr(S, "_upload", up)
    monkeypatch.setattr(S, "_rembg_api", rem)
    monkeypatch.setattr(S, "_download", dl)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def synth_video(tmp_path_factory):
    """12 frames 320x240 @6fps : fond vert uni, carré rouge qui traverse en
    bas de l'image (2 s). Assemblée avec le vrai ffmpeg — la recette exige une
    extraction réelle, pas un mock."""
    assert shutil.which("ffmpeg"), \
        "ffmpeg introuvable sur le PATH — préfixer avec le bin de l'app installée"
    base = tmp_path_factory.mktemp("synth")
    fdir = base / "f"
    fdir.mkdir()
    for i in range(12):
        img = Image.new("RGB", (320, 240), (0, 200, 30))
        d = ImageDraw.Draw(img)
        x = 20 + i * 12
        d.rectangle([x, 160, x + 40, 200], fill=(220, 40, 40))
        img.save(fdir / f"{i:03d}.png")
    out = base / "synth.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", "6", "-i", str(fdir / "%03d.png"),
         "-pix_fmt", "yuv420p", str(out)],
        check=True, capture_output=True, timeout=120)
    return out


@pytest.fixture
def outputs(tmp_path, monkeypatch, synth_video):
    """outputs_path -> tmp, avec la vidéo synthétique déposée en
    videos/synth.mp4 (même layout que les renders réels)."""
    monkeypatch.setattr(type(settings), "outputs_path",
                        property(lambda self: tmp_path))
    (tmp_path / "videos").mkdir()
    shutil.copy2(synth_video, tmp_path / "videos" / "synth.mp4")
    return tmp_path


# ── normalisation des options ────────────────────────────────────────────────

def test_normalize_defaults():
    o = S.normalize_opts({})
    assert o == {"fps": 8, "max_frames": 16, "remove_bg": "none",
                 "trim": "animation", "cell_size": 256, "align": "center",
                 "columns": "auto", "pixel": None}


def test_normalize_rejects_out_of_range():
    for bad in ({"fps_sample": 0}, {"fps_sample": 25}, {"fps_sample": "x"},
                {"max_frames": 3}, {"max_frames": 65},
                {"remove_bg": "chroma"}, {"trim": "loose"},
                {"cell": {"size": 300}}, {"cell": {"align": "top"}},
                {"cell": "big"}, {"columns": 0}, {"columns": "three"}):
        with pytest.raises(ValueError):
            S.normalize_opts(bad)


def test_normalize_pixel_9b():
    # accepté et normalisé via pixel_ops ; scale forcé à 1 côté sprite
    # (la mise à l'échelle est faite par la cellule, pas par l'op)
    o = S.normalize_opts({"pixel": {"target_px": 48, "palette": "gameboy",
                                    "scale": 8}})
    assert o["pixel"] == {"target_px": 48, "colors": None,
                          "palette": "gameboy", "dither": "none", "scale": 1}
    for bad in ({"pixel": {"target_px": 4}}, {"pixel": {"palette": "vga"}},
                {"pixel": {"colors": 8, "palette": "pico8"}},
                {"pixel": "yes"}):
        with pytest.raises(ValueError):
            S.normalize_opts(bad)


# ── résolution de source & path-traversal ────────────────────────────────────

def test_resolve_source_rejects_traversal(tmp_path, monkeypatch):
    out = tmp_path / "out"
    (out / "videos").mkdir(parents=True)
    (out / "uploads").mkdir()
    (tmp_path / "secret.env").write_text("FAL_KEY=leak")
    (out / "videos" / "ok.mp4").write_bytes(b"\x00\x00\x00 ftypisom")
    monkeypatch.setattr(type(settings), "outputs_path",
                        property(lambda self: out))

    def resolve(src):
        return asyncio.run(S.resolve_source(src))

    # légitime : chemin relatif sous outputs
    assert resolve({"kind": "video", "path": "videos/ok.mp4"}).name == "ok.mp4"
    # traversals / hors-outputs / manquants -> ValueError, jamais d'accès
    for bad in ({"kind": "video", "path": "..\\secret.env"},
                {"kind": "video", "path": "../secret.env"},
                {"kind": "video", "path": str(tmp_path / "secret.env")},
                {"kind": "video", "path": ""},
                {"kind": "video", "path": "videos/missing.mp4"},
                {"kind": "upload", "filename": "..\\..\\secret.env"},
                {"kind": "upload", "filename": "nope.mp4"},
                {"kind": "nope"}, {}):
        with pytest.raises(ValueError):
            resolve(bad)


# ── pipeline complet sur vidéo synthétique (vrai ffmpeg) ─────────────────────

def test_generate_grid_manifest_sheet_zip(outputs):
    steps = []
    r = _run(_payload(), "j-grid", steps)
    d = outputs / "sprites" / "j-grid"

    # fichiers de sortie (spec 9a)
    for name in ("sheet.png", "preview.gif", "manifest.json",
                 "sheet.unity.json", "SpriteSheetImporter.cs"):
        assert (d / name).is_file(), f"missing {name}"
    assert not (d / "_raw").exists()  # dossier de travail nettoyé

    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    # 12 frames extraites @6fps, max 8 -> sous-échantillonnage régulier
    assert m["source"]["sampled"] is True
    n = len(m["frames"])
    assert n == 8
    assert [f["file"] for f in m["frames"]] == \
        [f"frames/{i:03d}.png" for i in range(n)]
    assert all((d / f["file"]).is_file() for f in m["frames"])

    # grille ~carrée et rects dans les bornes du sheet
    g = m["grid"]
    assert (g["cols"], g["rows"]) == (3, 3) and g["cell_w"] == g["cell_h"] == 128
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (g["cols"] * 128, g["rows"] * 128)
        sheet_h = sh.height
    for f in m["frames"]:
        r_ = f["rect"]
        assert r_["w"] == r_["h"] == 128
        assert 0 <= r_["x"] <= sheet_h and 0 <= r_["y"] <= sheet_h
        assert f["offset"] == {"x": 0, "y": 0}          # trim=animation
        assert f["bg_removed"] is False                  # remove_bg=none
    assert m["fps"] == 6 and m["trim"] == "animation"

    # préviz animée : autant de frames que le sheet
    with Image.open(d / "preview.gif") as gif:
        assert getattr(gif, "n_frames", 1) == n

    # pack Unity : y inversé (origine bas-gauche), pivots, importer C#
    u = json.loads((d / "sheet.unity.json").read_text(encoding="utf-8"))
    assert u["pixelsPerUnit"] == 128 and len(u["frames"]) == n
    f0 = u["frames"][0]
    assert (f0["x"], f0["y"]) == (0, sheet_h - 128)      # top-left PIL -> Unity
    assert (f0["pivotX"], f0["pivotY"]) == (0.5, 0.5)    # align center
    cs = (d / "SpriteSheetImporter.cs").read_text(encoding="utf-8")
    assert "DeepotusSpriteSheetImporter" in cs
    assert "SpriteImportMode.Multiple" in cs

    # zip = sheet + frames + manifests + pack Unity
    names = set(zipfile.ZipFile(
        io.BytesIO(S.build_zip_bytes(d))).namelist())
    assert {"sheet.png", "preview.gif", "manifest.json", "sheet.unity.json",
            "SpriteSheetImporter.cs", "frames/000.png"} <= names

    # progression : croissante, se termine à Complete/100
    pcts = [p for _, p in steps]
    assert pcts == sorted(pcts) and steps[-1] == ("Complete", 100)

    # résumé du job (repris dans cost_meta par la route)
    assert r["frames"] == n and r["grid"] == g and r["bg_failed"] == []


def test_remove_bg_frame_failure_is_tolerated(outputs, monkeypatch):
    # 12 frames extraites, max 8 -> sous-échantillonnage garde raw_0001,
    # raw_0003, raw_0004, ... : la position 1 du pipeline est raw_0003.
    # Son remove-bg échoue -> frame conservée non détourée + flag manifest.
    _patch_chroma_rembg(monkeypatch, fail_marker="raw_0003")
    r = _run(_payload(remove_bg="api"), "j-fail")
    m = json.loads((outputs / "sprites" / "j-fail" / "manifest.json")
                   .read_text(encoding="utf-8"))
    flags = [f["bg_removed"] for f in m["frames"]]
    assert flags[1] is False and all(flags[:1] + flags[2:])
    assert r["bg_failed"] == [1]


def test_trim_tight_vs_animation(outputs, monkeypatch):
    _patch_chroma_rembg(monkeypatch)
    cell = {"size": 128, "align": "feet"}
    _run(_payload(remove_bg="api", trim="animation", cell=cell), "j-anim")
    _run(_payload(remove_bg="api", trim="tight", cell=cell), "j-tight")
    ma = json.loads((outputs / "sprites" / "j-anim" / "manifest.json")
                    .read_text(encoding="utf-8"))
    mt = json.loads((outputs / "sprites" / "j-tight" / "manifest.json")
                    .read_text(encoding="utf-8"))

    # animation : canvas complet préservé, offset nul ;
    # tight : recadré à la bbox union du contenu -> offset non nul
    assert ma["frames"][0]["offset"] == {"x": 0, "y": 0}
    ot = mt["frames"][0]["offset"]
    assert ot["x"] > 0 and ot["y"] > 0

    def alpha_stats(job):
        p = outputs / "sprites" / job / "frames" / "000.png"
        with Image.open(p) as im:
            a = im.convert("RGBA").getchannel("A")
            bbox = a.getbbox()
            opaque = sum(a.histogram()[129:])
        return bbox, opaque

    bb_a, op_a = alpha_stats("j-anim")
    bb_t, op_t = alpha_stats("j-tight")
    # le contenu remplit mieux la cellule en tight (carré plus grand)
    assert op_t > op_a > 0
    # ancre 'feet' : le bas du contenu touche le bas de la cellule
    assert bb_t[3] >= 126


def test_pixel_art_frames(outputs, monkeypatch):
    """pixel gameboy : chaque frame du sheet reste dans la palette (4 couleurs
    + transparent), alpha binaire — preuve que le fit cellule est en NEAREST
    (un LANCZOS mélangerait les couleurs hors palette)."""
    from app.services.pixel_ops import PALETTES
    _patch_chroma_rembg(monkeypatch)
    steps = []
    r = _run(_payload(remove_bg="api",
                      pixel={"target_px": 32, "palette": "gameboy"}),
             "j-pix", steps)
    d = outputs / "sprites" / "j-pix"

    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert m["pixel"]["target_px"] == 32
    assert m["pixel"]["palette"] == "gameboy"
    assert any(lbl.startswith("Pixel-art") for lbl, _ in steps)

    pal = set(PALETTES["gameboy"])
    for f in m["frames"][:3]:
        with Image.open(d / f["file"]) as im:
            im = im.convert("RGBA")
            assert im.size == (128, 128)
            data = list(im.getdata())
        opaque = {(px[0], px[1], px[2]) for px in data if px[3] >= 128}
        assert opaque and opaque <= pal, sorted(opaque - pal)[:4]
        assert {px[3] for px in data} <= {0, 255}
    assert r["frames"] == len(m["frames"])


# ── pricing ──────────────────────────────────────────────────────────────────

def test_pricing_sprite2d():
    from app.services.pricing import estimate, DEFAULTS
    r = estimate({"kind": "sprite2d", "frames": 16, "remove_bg": "api"})
    assert r["total_usd"] == round(16 * DEFAULTS["rembg_api_usd"], 4) > 0
    free = estimate({"kind": "sprite2d", "frames": 16, "remove_bg": "none"})
    assert free["total_usd"] == 0.0
    # le breakdown reste honnête : la partie locale apparaît à 0 $
    assert any(l["provider"] == "local" for l in free["breakdown"])
