"""Recette chantier 9e — op "seamless" + chroma_key (pixel_ops).

Tests golden purs (aucun réseau, aucune app FastAPI) :
  normalisation (défauts, bornes, erreurs), offset (taille conservée,
  déterminisme byte-identique, raccord fortement réduit), mirror (raccord
  exactement nul), recadrage carré + target_px, seam_score cohérent avec
  tile_preview, chroma_key (fond uni transparent, sujet sombre conservé,
  garde-fou couverture).

  runtime\\python\\python.exe -m pytest backend/tests/test_pixel_seamless.py -v
"""
import io
import random

import pytest
from PIL import Image, ImageDraw

from app.services.pixel_ops import (chroma_key, make_seamless,
                                    normalize_seamless_opts, seam_score,
                                    tile_preview)


# ── images de test déterministes ─────────────────────────────────────────────

def _gradient(w=256, h=256):
    """Rampe horizontale : bords gauche/droite opposés -> raccord mauvais."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (int(255 * x / (w - 1)), 96, 160)
    return img


def _busy_photo(w=256, h=256):
    """Pseudo-photo seedée (même recette que la recette 9b)."""
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


def _green_scene(w=200, h=200, bg=(96, 220, 96)):
    """Sujet sombre (manteau #202020) sur fond uni vert — le cas Olivier."""
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([70, 40, 130, 180], fill=(32, 32, 32))
    d.ellipse([80, 15, 120, 55], fill=(180, 140, 110))
    return img


def _png_bytes(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


# ── normalisation ────────────────────────────────────────────────────────────

def test_normalize_seamless_defaults():
    assert normalize_seamless_opts({}) == {
        "method": "offset", "blend": 20, "target_px": 0, "square": True}
    o = normalize_seamless_opts({"method": "mirror", "blend": 35,
                                 "target_px": 128, "square": False})
    assert o == {"method": "mirror", "blend": 35, "target_px": 128,
                 "square": False}


def test_normalize_seamless_rejects():
    for bad in ({"method": "wang"}, {"blend": 4}, {"blend": 46},
                {"blend": "x"}, {"target_px": 63}, {"target_px": 1025},
                {"target_px": "x"}):
        with pytest.raises(ValueError):
            normalize_seamless_opts(bad)


# ── méthode offset ───────────────────────────────────────────────────────────

def test_offset_reduces_seam_and_is_deterministic():
    img = _busy_photo()
    before = seam_score(img)
    opts = normalize_seamless_opts({})
    out1 = make_seamless(img, opts)
    out2 = make_seamless(img, opts)
    assert out1.size == img.size
    after = seam_score(out1)
    assert after < before, (after, before)
    assert after <= 10.0, after
    assert _png_bytes(out1) == _png_bytes(out2)


def test_offset_keeps_non_square_when_asked():
    img = _busy_photo(300, 200)
    out = make_seamless(img, normalize_seamless_opts({"square": False}))
    assert out.size == (300, 200)
    assert seam_score(out) <= 10.0


# ── méthode mirror ───────────────────────────────────────────────────────────

def test_mirror_seam_is_zero():
    img = _busy_photo()
    out = make_seamless(img, normalize_seamless_opts({"method": "mirror"}))
    assert out.size == img.size
    assert seam_score(out) == 0.0


# ── carré + target_px ────────────────────────────────────────────────────────

def test_square_crop_and_target():
    img = _busy_photo(300, 200)
    out = make_seamless(img, normalize_seamless_opts({}))
    assert out.size == (200, 200)                     # carré centré par défaut
    out2 = make_seamless(img, normalize_seamless_opts({"target_px": 128}))
    assert out2.size == (128, 128)


# ── seam_score cohérent avec tile_preview ────────────────────────────────────

def test_seam_score_matches_tile_preview():
    img = _busy_photo()
    _, score = tile_preview(img, 2)
    assert seam_score(img) == score
    assert seam_score(Image.new("RGB", (64, 64), (10, 200, 30))) == 0.0


# ── chroma_key ───────────────────────────────────────────────────────────────

def test_chroma_key_green_bg_dark_subject():
    out, ok = chroma_key(_green_scene())
    assert ok is True
    a = out.getchannel("A").load()
    assert a[4, 4] == 0                # coin = fond -> transparent
    assert a[195, 4] == 0
    assert a[100, 110] == 255          # manteau sombre conservé
    assert a[100, 30] == 255           # tête conservée


def test_chroma_key_grey_bg():
    out, ok = chroma_key(_green_scene(bg=(216, 216, 213)))
    assert ok is True
    assert out.getchannel("A").load()[4, 4] == 0
    assert out.getchannel("A").load()[100, 110] == 255


def test_chroma_key_guard_rails():
    uni = Image.new("RGB", (64, 64), (96, 220, 96))
    _, ok = chroma_key(uni)                       # tout serait mangé
    assert ok is False
    _, ok2 = chroma_key(_gradient())              # pas de fond uni fiable
    assert ok2 is False


def test_chroma_key_deterministic():
    img = _green_scene()
    assert _png_bytes(chroma_key(img)[0]) == _png_bytes(chroma_key(img)[0])
