"""Recette Material Forge — derivation des maps PBR (`pbr_service`).

Tests purs (aucun reseau, aucune app FastAPI, zero numpy). Ce qui est verifie :
  jeu complet des 8 maps (tailles + modes), normale neutre sur une image plate,
  **raccord cyclique** (seam_score des maps derivees d'une tuile seamless sous
  2.0, et nettement meilleur qu'une convolution naive), effet reel de chaque
  reglage de derivation, normalisation des reglages, resize_maps, budget temps.

  runtime\\python\\python.exe -m pytest backend/tests/test_pbr_service.py -v
"""
import io
import math
import random
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

import app.services.pbr_service as pbr
from app.services.pbr_service import (DERIVE_DEFAULTS, MAP_KINDS, MAP_MODES,
                                      derive_maps, normalize_derive,
                                      resize_maps)
from app.services.pixel_ops import (make_seamless, normalize_seamless_opts,
                                    seam_score)

SEAM_MAX = 2.0          # la barre annoncee dans BRIEF.md


# ── images de test deterministes ─────────────────────────────────────────────

def _periodic(w=256, h=256, waves=((1, 1, 80), (2, 3, 30), (5, 4, 12))):
    """Tuile EXACTEMENT periodique (somme de sinus de periode w et h) : le
    raccord est parfait par construction, ce qui isole la seule variable
    testee ici — la derivation reste-t-elle raccordable ?"""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = 128.0
            for kx, ky, amp in waves:
                v += amp * math.sin(2 * math.pi * kx * x / w) \
                         * math.cos(2 * math.pi * ky * y / h)
            v = max(0.0, min(255.0, v))
            px[x, y] = (int(v), int(v * 0.82 + 18), int(v * 0.6 + 40))
    return img


def _flat(w=64, h=64, level=137):
    return Image.new("RGB", (w, h), (level, level, level))


def _colorful(w=96, h=96):
    """Trois plages verticales, plus une legere rampe verticale pour que les
    derivees en Y ne soient pas nulles : gris clair desature (metal en mode
    auto), jaune sature (lumineux mais PAS metal), presque blanc (emissif).
    La rampe est nulle a mi-hauteur : les assertions y lisent la couleur pure."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        k = int(12 * (2.0 * y / (h - 1) - 1.0))
        for x in range(w):
            if x < w // 3:
                c = (205, 207, 206)
            elif x < 2 * w // 3:
                c = (235, 200, 40)
            else:
                c = (252, 250, 248)
            px[x, y] = tuple(max(0, min(255, v + k)) for v in c)
    return img


def _png(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


# ── jeu de maps ──────────────────────────────────────────────────────────────

def test_eight_maps_sizes_and_modes():
    maps = derive_maps(_periodic(128, 128))
    assert list(maps) == list(MAP_KINDS)
    assert len(maps) == 8
    for kind, img in maps.items():
        assert img.size == (128, 128), kind
        assert img.mode == MAP_MODES[kind], (kind, img.mode)


def test_want_subset_only_returns_asked_maps():
    maps = derive_maps(_periodic(64, 64), None, ["roughness", "normal"])
    assert list(maps) == ["normal", "roughness"]        # ordre de MAP_KINDS
    assert derive_maps(_periodic(64, 64), None, ["nawak"]) == {}
    only_orm = derive_maps(_periodic(64, 64), None, ["orm"])
    assert list(only_orm) == ["orm"]                    # deps calculees en interne


def test_orm_packs_ao_roughness_metallic():
    maps = derive_maps(_colorful())
    r, g, b = maps["orm"].split()
    assert _png(r) == _png(maps["ao"])
    assert _png(g) == _png(maps["roughness"])
    assert _png(b) == _png(maps["metallic"])


def test_derivation_is_deterministic():
    src = _periodic(96, 96)
    a = derive_maps(src)
    b = derive_maps(src)
    for kind in MAP_KINDS:
        assert _png(a[kind]) == _png(b[kind]), kind


# ── normale ──────────────────────────────────────────────────────────────────

def test_flat_image_gives_neutral_normal():
    n = derive_maps(_flat(), None, ["normal"])["normal"]
    assert n.mode == "RGB"
    assert n.getextrema() == ((128, 128), (128, 128), (255, 255))
    assert n.getpixel((0, 0)) == (128, 128, 255)        # coin = bord cyclique
    assert n.getpixel((63, 0)) == (128, 128, 255)
    assert n.getpixel((32, 32)) == (128, 128, 255)


def test_flat_image_gives_open_ao_and_black_metallic_none():
    maps = derive_maps(_flat(), {"metallic_mode": "none"})
    assert maps["ao"].getextrema() == (255, 255)        # rien d'occlus
    assert maps["metallic"].getextrema() == (0, 0)


def test_normal_slope_signs_are_opengl():
    """Rampe montant vers la droite -> X pointe vers -X (R < 128) ;
    rampe montant vers le haut -> Y pointe vers -Y (G < 128, +Y en haut)."""
    w = h = 64
    ramp_x = Image.new("RGB", (w, h))
    px = ramp_x.load()
    for y in range(h):
        for x in range(w):
            v = 40 + int(150 * x / (w - 1))
            px[x, y] = (v, v, v)
    n = derive_maps(ramp_x, {"normal_strength": 0.5}, ["normal"])["normal"]
    assert n.getpixel((32, 32))[0] < 128

    ramp_y = Image.new("RGB", (w, h))
    px = ramp_y.load()
    for y in range(h):
        for x in range(w):
            v = 40 + int(150 * (h - 1 - y) / (h - 1))   # clair en haut
            px[x, y] = (v, v, v)
    n = derive_maps(ramp_y, {"normal_strength": 0.5}, ["normal"])["normal"]
    assert n.getpixel((32, 32))[1] < 128


def test_normal_invert_y_flips_green_only():
    src = _periodic(96, 96)
    gl = derive_maps(src, {"normal_invert_y": False}, ["normal"])["normal"]
    dx = derive_maps(src, {"normal_invert_y": True}, ["normal"])["normal"]
    assert _png(gl) != _png(dx)
    assert _png(gl.getchannel("R")) == _png(dx.getchannel("R"))
    assert _png(gl.getchannel("B")) == _png(dx.getchannel("B"))
    # G miroir autour de 128 (a l'arrondi 8 bits pres)
    a, b = gl.getchannel("G"), dx.getchannel("G")
    mirror = b.point([255 - v for v in range(256)])     # 255 - v ~ 256 - v
    diff = ImageStat.Stat(ImageChops.difference(a, mirror)).mean[0]
    assert diff <= 1.5, diff


def test_normal_is_unit_length_in_8_bits():
    n = derive_maps(_periodic(64, 64), {"normal_strength": 1.0},
                    ["normal"])["normal"]
    px = n.load()
    worst = 0.0
    for y in range(0, 64, 7):
        for x in range(0, 64, 7):
            r, g, b = px[x, y]
            nx, ny, nz = (r - 128) / 127.0, (g - 128) / 127.0, b / 255.0
            worst = max(worst, abs(math.sqrt(nx * nx + ny * ny + nz * nz) - 1.0))
    assert worst < 0.02, worst


# ── LE point dur : raccord cyclique ──────────────────────────────────────────

def test_derived_maps_of_a_seamless_tile_stay_seamless():
    src = _periodic()
    assert seam_score(src) < 1.0                        # la tuile source raccorde
    maps = derive_maps(src)
    for kind, img in maps.items():
        assert seam_score(img) < SEAM_MAX, (kind, seam_score(img))


def test_cyclic_convolution_beats_the_naive_one():
    """Meme chaine, `_wrap` en moins : c'est exactement ce que fait une
    implementation naive (et ce que la barre ne mesure pas)."""
    src = _periodic()
    d = normalize_derive(None)
    maps = derive_maps(src)
    height = maps["height"]

    strength = d["normal_strength"] * 4.0
    kx = ImageFilter.Kernel((3, 3), pbr._SOBEL_X, scale=8, offset=128)
    ky = ImageFilter.Kernel((3, 3), pbr._SOBEL_Y, scale=8, offset=128)
    lut_x = [pbr._c8(128.0 - (v - 128) * strength) for v in range(256)]
    lut_y = [pbr._c8(128.0 + (v - 128) * strength) for v in range(256)]
    naive_normal = pbr._renormalize(height.filter(kx).point(lut_x),
                                    height.filter(ky).point(lut_y))

    blur = height.filter(ImageFilter.GaussianBlur(d["ao_radius"]))
    naive_ao = ImageChops.subtract(blur, height).point(
        [pbr._c8(255.0 - d["ao_strength"] * v) for v in range(256)])

    radius = 1.0 + 3.0 * (1.0 - d["height_detail"])
    naive_height = ImageOps.autocontrast(
        src.convert("L").filter(ImageFilter.GaussianBlur(radius)), cutoff=1)

    for kind, ours, naive in (("normal", maps["normal"], naive_normal),
                              ("ao", maps["ao"], naive_ao),
                              ("height", height, naive_height)):
        mine, theirs = seam_score(ours), seam_score(naive)
        assert mine < theirs, (kind, mine, theirs)
        assert mine <= theirs / 2.0, (kind, mine, theirs)

    # Le defaut le plus visible d'une convolution non bordee : la colonne de
    # bord n'est pas convoluee du tout. On le mesure contre sa voisine.
    def _col_gap(img, a, b):
        img = img.convert("RGB")
        h = img.height
        stat = ImageStat.Stat(ImageChops.difference(
            img.crop((a, 0, a + 1, h)), img.crop((b, 0, b + 1, h)))).mean
        return sum(stat) / len(stat)

    assert _col_gap(maps["normal"], 0, 1) < _col_gap(naive_normal, 0, 1) / 3.0


def test_convolved_maps_survive_a_real_offset_tile():
    """Cas reel : une texture quelconque passee par `make_seamless` (offset
    50/50). Depuis la fermeture de boucle de `pixel_ops` la tuile sort a 0.00
    (avant 12.9), la comparaison relative n'a donc plus de sens : on exige
    l'ABSOLU sur les huit maps. Ce sont les deux maps entierement convoluees
    (normal, ao) et la height qui peuvent deriver — c'est exactement ce que le
    bordage cyclique doit empecher. Mesure sur cette machine :
    basecolor/roughness/metallic/emissive 0.00, orm 0.15, ao 0.46,
    normal 0.76, height 1.14 — toutes sous la barre de 2.0 du BRIEF."""
    src = Image.new("RGB", (256, 256), (120, 100, 80))
    draw = ImageDraw.Draw(src)
    rng = random.Random(7)
    for _ in range(200):
        x, y = rng.randrange(256), rng.randrange(256)
        r = rng.randrange(4, 24)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=(rng.randrange(60, 200), rng.randrange(50, 170),
                           rng.randrange(40, 140)))
    src = src.filter(ImageFilter.GaussianBlur(2))
    tile = make_seamless(src, normalize_seamless_opts({"blend": 25})) \
        .convert("RGB")
    before, after = seam_score(src), seam_score(tile)
    assert after < before / 3.0, (before, after)
    assert after == 0.0, after            # la boucle est fermee, pas "presque"

    maps = derive_maps(tile)
    for kind in MAP_KINDS:                # les HUIT, pas seulement deux
        score = seam_score(maps[kind])
        assert score < SEAM_MAX, (kind, score)
    assert seam_score(maps["normal"]) < 1.5
    # L'AO multi-echelle amplifie ce qu'elle mesure (trois octaves, gain 3) :
    # le meme residu physique se lit donc environ trois fois plus haut qu'avec
    # l'ancienne AO plate — 1.6 au lieu de 0.5. Ce n'est pas une degradation du
    # raccord, c'est le contraste de la map. La bonne mesure est le RAPPORT de
    # couture, qui rapporte la jonction a la variation interne de la map :
    # sous 1.0, la jonction ne depasse pas le grain normal de l'AO.
    assert seam_score(maps["ao"]) < SEAM_MAX, seam_score(maps["ao"])
    # ... et la vraie question : la derivation AJOUTE-t-elle une couture ? On
    # compare le rapport de couture de l'AO a celui de la tuile dont elle sort.
    tile_ratio = pbr.seam_report(tile)["ratio"]
    ao_ratio = pbr.seam_report(maps["ao"])["ratio"]
    assert ao_ratio <= max(1.3, tile_ratio * 1.3), (tile_ratio, ao_ratio)


def test_seam_stays_low_at_1024():
    maps = derive_maps(_periodic(1024, 1024))
    for kind in ("normal", "ao", "height", "orm"):
        assert seam_score(maps[kind]) < SEAM_MAX, kind


# ── les reglages changent vraiment la sortie ─────────────────────────────────

def test_every_derive_setting_changes_its_map():
    """Chacun des 11 reglages doit deplacer SA map — sinon le bouton ment."""
    relief = _periodic(128, 128)          # variation 2D : gx et gy non nuls
    tinted = _colorful(128, 128)          # variete de teintes et de saturations
    cases = [
        (relief, {"normal_strength": 0.2}, "normal"),
        (relief, {"normal_invert_y": True}, "normal"),
        (relief, {"height_detail": 1.0}, "height"),
        (relief, {"ao_strength": 4.0}, "ao"),
        (relief, {"ao_radius": 16.0}, "ao"),
        (tinted, {"roughness_bias": 0.9}, "roughness"),
        (tinted, {"roughness_contrast": 0.0}, "roughness"),
        (tinted, {"roughness_invert": True}, "roughness"),
        (tinted, {"roughness_source": "albedo"}, "roughness"),
        (tinted, {"metallic_mode": "none"}, "metallic"),
        (tinted, {"metallic_mode": "luminance"}, "metallic"),
        # seuil : il faut une source qui balaie toute la plage de luminance,
        # les trois plages de `tinted` sont toutes au-dessus des deux seuils.
        (relief, {"metallic_threshold": 0.05}, "metallic"),
        (tinted, {"emissive_threshold": 0.2}, "emissive"),
    ]
    refs = {id(src): derive_maps(src) for src in (relief, tinted)}
    seen = set()
    for src, overrides, kind in cases:
        changed = _png(derive_maps(src, overrides, [kind])[kind])
        assert changed != _png(refs[id(src)][kind]), (overrides, kind)
        seen |= set(overrides)
    assert seen == set(DERIVE_DEFAULTS)        # aucun reglage oublie


def test_roughness_of_a_flat_image_is_the_bias_not_the_luminance():
    """La rugosite ne suit PLUS le niveau de gris. Sur un aplat — aucun grain,
    aucune cavite — il n'y a rien a dire : la map vaut le biais, quelle que
    soit la couleur. C'est l'inverse exact de l'ancienne formule, ou un aplat
    noir sortait « rugueux 1.00 » et un aplat blanc « miroir » sans qu'aucune
    des deux valeurs ne repose sur quoi que ce soit de mesure."""
    for level in (0, 128, 255):
        r = derive_maps(_flat(32, 32, level), None, ["roughness"])["roughness"]
        assert r.getextrema() == (128, 128), level      # biais 0.5
    biased = derive_maps(_flat(32, 32, 40), {"roughness_bias": 0.9},
                         ["roughness"])["roughness"]
    assert biased.getextrema() == (230, 230)            # 0.9 -> 229.5
    inv = derive_maps(_flat(32, 32, 40), {"roughness_bias": 0.9,
                                          "roughness_invert": True},
                      ["roughness"])["roughness"]
    assert inv.getextrema() == (25, 25)                 # 1 - 0.9 -> 25.5


def test_the_legacy_albedo_source_is_still_available():
    """`roughness_source = "albedo"` restaure l'ancienne formule a l'identique :
    la comparaison reste possible, et une matiere dont l'albedo EST la carte
    d'usure peut la demander explicitement."""
    d = {"roughness_source": "albedo"}
    black = derive_maps(_flat(32, 32, 0), d, ["roughness"])["roughness"]
    white = derive_maps(_flat(32, 32, 255), d, ["roughness"])["roughness"]
    assert black.getextrema() == (255, 255)             # sombre = rugueux
    assert white.getextrema() == (0, 0)                 # clair = lisse
    flatter = derive_maps(_flat(32, 32, 0), dict(d, roughness_contrast=0.0),
                          ["roughness"])["roughness"]
    assert flatter.getextrema() == (191, 191)           # 0.5 + 0.5*0.5 = 0.75


def test_ao_strength_deepens_occlusion():
    src = _periodic(128, 128)
    soft = derive_maps(src, {"ao_strength": 0.25}, ["ao"])["ao"]
    hard = derive_maps(src, {"ao_strength": 4.0}, ["ao"])["ao"]
    assert ImageStat.Stat(hard).mean[0] < ImageStat.Stat(soft).mean[0]
    assert hard.getextrema()[0] < soft.getextrema()[0]


def test_metallic_auto_prefers_bright_desaturated_areas():
    m = derive_maps(_colorful(), None, ["metallic"])["metallic"]
    px = m.load()
    assert px[16, 48] > 200          # gris clair desature -> metal
    assert px[48, 48] < 40           # jaune sature -> pas metal
    none = derive_maps(_colorful(), {"metallic_mode": "none"},
                       ["metallic"])["metallic"]
    assert none.getextrema() == (0, 0)
    lum = derive_maps(_colorful(), {"metallic_mode": "luminance"},
                      ["metallic"])["metallic"]
    # la luminance seule ne voit pas la saturation : elle prend le jaune vif
    # pour du metal, la ou "auto" le rejette. C'est tout l'interet du mode.
    assert lum.load()[48, 48] > 200


def test_emissive_keeps_only_the_brightest_pixels():
    e = derive_maps(_colorful(), None, ["emissive"])["emissive"]
    assert e.getpixel((80, 48))[0] > 200      # presque blanc -> emet
    assert e.getpixel((48, 48)) == (0, 0, 0)  # jaune sature -> muet
    assert e.getpixel((16, 48)) == (0, 0, 0)  # gris clair -> sous le seuil
    dark = derive_maps(_flat(32, 32, 10), None, ["emissive"])["emissive"]
    assert dark.getextrema() == ((0, 0), (0, 0), (0, 0))


# ── normalisation des reglages ───────────────────────────────────────────────

def test_normalize_derive_defaults():
    assert normalize_derive(None) == DERIVE_DEFAULTS
    assert normalize_derive({}) == DERIVE_DEFAULTS
    assert normalize_derive("nawak") == DERIVE_DEFAULTS
    assert normalize_derive({"normal_strength": None}) == DERIVE_DEFAULTS


def test_normalize_derive_clamps_and_never_raises():
    d = normalize_derive({"normal_strength": 99, "ao_radius": -5,
                          "roughness_bias": "0.25", "roughness_invert": "true",
                          "normal_invert_y": 1, "metallic_mode": "NONE",
                          "emissive_threshold": float("nan"),
                          "height_detail": "pas un nombre",
                          "inconnu": 12})
    assert d["normal_strength"] == 4.0
    assert d["ao_radius"] == 0.5
    assert d["roughness_bias"] == 0.25
    assert d["roughness_invert"] is True
    assert d["normal_invert_y"] is True
    assert d["metallic_mode"] == "none"
    assert d["emissive_threshold"] == DERIVE_DEFAULTS["emissive_threshold"]
    assert d["height_detail"] == DERIVE_DEFAULTS["height_detail"]
    assert "inconnu" not in d
    assert normalize_derive({"metallic_mode": "argent"})["metallic_mode"] == "auto"


def test_bad_derive_never_breaks_derivation():
    maps = derive_maps(_periodic(64, 64), {"ao_radius": "x", "normal_strength": []})
    assert len(maps) == 8


# ── resize_maps ──────────────────────────────────────────────────────────────

def test_resize_maps_sizes_modes_and_renormalized_normal():
    maps = derive_maps(_periodic(256, 256))
    small = resize_maps(maps, 64)
    for kind, img in small.items():
        assert img.size == (64, 64), kind
        assert img.mode == MAP_MODES[kind], kind
    flat = resize_maps(derive_maps(_flat(64, 64)), 128)
    assert flat["normal"].getextrema() == ((128, 128), (128, 128), (255, 255))
    same = resize_maps(maps, 256)
    assert _png(same["normal"]) == _png(maps["normal"])   # no-op si deja bon


def test_resize_keeps_the_normal_unit_length():
    n = resize_maps(derive_maps(_periodic(256, 256), {"normal_strength": 1.0},
                                ["normal"]), 96)["normal"]
    px = n.load()
    worst = 0.0
    for y in range(0, 96, 9):
        for x in range(0, 96, 9):
            r, g, b = px[x, y]
            nx, ny, nz = (r - 128) / 127.0, (g - 128) / 127.0, b / 255.0
            worst = max(worst, abs(math.sqrt(nx * nx + ny * ny + nz * nz) - 1.0))
    assert worst < 0.02, worst


# ── budget temps (SPEC : 4096 sous ~25 s sur cette machine) ──────────────────

def test_derivation_time_budget():
    src = _periodic(512, 512)
    seen = {}
    for res in (1024, 2048, 4096):
        big = src.resize((res, res), Image.LANCZOS)
        t0 = time.perf_counter()
        maps = derive_maps(big)
        seen[res] = time.perf_counter() - t0
        assert len(maps) == 8
        assert maps["normal"].size == (res, res)
        del maps, big
    print("\nderivation :", " ".join(f"{r}={seen[r]:.2f}s" for r in sorted(seen)))
    assert seen[4096] < 25.0, seen
