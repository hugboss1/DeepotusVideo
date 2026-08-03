"""Recette chantier 9b — pixel_ops (op "pixel" + op "tile-preview").

Tests golden purs (aucun réseau, aucune app FastAPI) :
  nombre de couleurs exact <= preset, dimensions attendues, déterminisme
  byte-identique, dithers none/ordered/floyd, alpha binaire, métrique
  tile-preview basse sur une tuile unie et haute sur une image chargée.

  runtime\\python\\python.exe -m pytest backend/tests/test_pixel_ops.py -v
"""
import random

import pytest
from PIL import Image, ImageDraw

from app.services.pixel_ops import (PALETTES, normalize_pixel_opts, pixelate,
                                    tile_preview)


# ── images de test déterministes ─────────────────────────────────────────────

def _gradient(w=400, h=300):
    """Dégradé horizontal + vertical : des milliers de couleurs distinctes."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (int(255 * x / (w - 1)), int(255 * y / (h - 1)), 128)
    return img


def _busy_photo(w=256, h=256):
    """Pseudo-photo seedée : rampe gauche->droite + formes bruitées.
    Bords opposés très différents -> raccord de tuile mauvais."""
    img = _gradient(w, h)
    d = ImageDraw.Draw(img)
    rng = random.Random(42)
    for _ in range(80):
        x, y = rng.randrange(w), rng.randrange(h)
        r = rng.randrange(4, 24)
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(rng.randrange(256), rng.randrange(256),
                        rng.randrange(256)))
    return img


def _soft_alpha_sprite(w=200, h=200):
    """Disque rouge sur fond transparent avec bord d'alpha adouci."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([30, 30, w - 30, h - 30], fill=(220, 40, 40, 255))
    return img.resize((w // 2, h // 2), Image.LANCZOS)  # bords semi-transparents


def _opaque_colors(img):
    """Couleurs RGB distinctes des pixels opaques d'une image RGBA."""
    img = img.convert("RGBA")
    return {(r, g, b) for r, g, b, a in img.getdata() if a >= 128}


# ── normalisation des options ────────────────────────────────────────────────

def test_normalize_defaults():
    assert normalize_pixel_opts({}) == {
        "target_px": 64, "colors": 16, "palette": None,
        "dither": "none", "scale": 1}
    # preset -> colors implicite par la palette
    o = normalize_pixel_opts({"palette": "pico8", "dither": "floyd",
                              "scale": 4, "target_px": 32})
    assert o == {"target_px": 32, "colors": None, "palette": "pico8",
                 "dither": "floyd", "scale": 4}


def test_normalize_rejects_out_of_range():
    for bad in ({"target_px": 7}, {"target_px": 513}, {"target_px": "x"},
                {"colors": 1}, {"colors": 257},
                {"palette": "vga"}, {"dither": "bayer"},
                {"scale": 0}, {"scale": 17},
                {"colors": 8, "palette": "pico8"}):   # exclusifs
        with pytest.raises(ValueError):
            normalize_pixel_opts(bad)


def test_palettes_presets():
    assert set(PALETTES) == {"pico8", "gameboy", "nes", "sweetie16", "onebit"}
    assert len(PALETTES["pico8"]) == 16
    assert len(PALETTES["gameboy"]) == 4
    assert len(PALETTES["sweetie16"]) == 16
    assert len(PALETTES["onebit"]) == 2
    assert 50 <= len(PALETTES["nes"]) <= 64
    for pal in PALETTES.values():   # uniques, triplets RGB valides
        assert len(set(pal)) == len(pal)
        assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in pal)


# ── dimensions ───────────────────────────────────────────────────────────────

def test_grid_dimensions_long_side():
    img = _gradient(400, 300)
    out = pixelate(img, normalize_pixel_opts({"target_px": 64}))
    assert out.size == (64, 48)                      # côté long = target_px
    out = pixelate(img.rotate(90, expand=True),
                   normalize_pixel_opts({"target_px": 64}))
    assert out.size == (48, 64)
    out = pixelate(img, normalize_pixel_opts({"target_px": 64, "scale": 4}))
    assert out.size == (256, 192)                    # upscale NEAREST x4
    assert out.mode == "RGBA"


def test_scale_is_nearest_blocky():
    """x4 : chaque bloc 4x4 du résultat est uni (aucun lissage)."""
    out = pixelate(_gradient(), normalize_pixel_opts(
        {"target_px": 16, "colors": 8, "scale": 4}))
    px = out.load()
    for by in range(0, out.height, 4):
        for bx in range(0, out.width, 4):
            block = {px[bx + i, by + j] for i in range(4) for j in range(4)}
            assert len(block) == 1


# ── couleurs ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dither", ["none", "ordered", "floyd"])
def test_adaptive_color_count(dither):
    out = pixelate(_gradient(), normalize_pixel_opts(
        {"target_px": 64, "colors": 8, "dither": dither}))
    n = len(_opaque_colors(out))
    assert 2 <= n <= 8, f"{dither}: {n} couleurs"


@pytest.mark.parametrize("name", sorted(PALETTES))
def test_palette_subset(name):
    out = pixelate(_gradient(), normalize_pixel_opts(
        {"target_px": 64, "palette": name, "dither": "ordered"}))
    got = _opaque_colors(out)
    assert got <= set(PALETTES[name]), \
        f"{name}: couleurs hors palette {sorted(got - set(PALETTES[name]))[:4]}"
    assert len(got) >= 2


def test_onebit_is_two_colors_max():
    out = pixelate(_gradient(), normalize_pixel_opts(
        {"target_px": 48, "palette": "onebit", "dither": "floyd"}))
    assert _opaque_colors(out) <= {(0, 0, 0), (255, 255, 255)}


# ── déterminisme & dithers ───────────────────────────────────────────────────

@pytest.mark.parametrize("spec", [
    {"target_px": 64, "colors": 8},
    {"target_px": 64, "colors": 8, "dither": "floyd"},
    {"target_px": 64, "palette": "pico8", "dither": "ordered"},
    {"target_px": 32, "palette": "onebit", "dither": "ordered", "scale": 2},
])
def test_determinism(spec):
    a = pixelate(_gradient(), normalize_pixel_opts(spec))
    b = pixelate(_gradient(), normalize_pixel_opts(spec))
    assert a.size == b.size and a.tobytes() == b.tobytes()


def test_ordered_dither_actually_dithers():
    """Sur un dégradé, ordered != none (le motif Bayer doit agir)."""
    base = {"target_px": 64, "palette": "gameboy"}
    none_ = pixelate(_gradient(), normalize_pixel_opts(base))
    ordered = pixelate(_gradient(),
                       normalize_pixel_opts({**base, "dither": "ordered"}))
    assert none_.tobytes() != ordered.tobytes()


# ── alpha ────────────────────────────────────────────────────────────────────

def test_alpha_is_binary():
    out = pixelate(_soft_alpha_sprite(), normalize_pixel_opts(
        {"target_px": 32, "palette": "pico8"}))
    alphas = {a for _, _, _, a in out.getdata()}
    assert alphas <= {0, 255} and alphas == {0, 255}


# ── tile-preview ─────────────────────────────────────────────────────────────

def test_tile_preview_uniform_low():
    comp, score = tile_preview(Image.new("RGB", (256, 256), (90, 120, 60)), 2)
    assert comp.size == (512, 512)
    assert score < 2, score


def test_tile_preview_busy_high():
    comp, score = tile_preview(_busy_photo(), 2)
    assert score > 20, score


def test_tile_preview_grid3_and_cap():
    comp, _ = tile_preview(Image.new("RGB", (100, 80), (10, 10, 10)), 3)
    assert comp.size == (300, 240)
    # composite plafonné : tuile réduite à 512 max par côté
    comp, _ = tile_preview(Image.new("RGB", (2048, 1024), (10, 10, 10)), 2)
    assert max(comp.size) <= 1024


def test_tile_preview_deterministic():
    a = tile_preview(_busy_photo(), 2)
    b = tile_preview(_busy_photo(), 2)
    assert a[1] == b[1] and a[0].tobytes() == b[0].tobytes()
    assert 0 <= a[1] <= 100
