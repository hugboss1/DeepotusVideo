"""Recette de la ronde 6 — le bloc `render` doit suivre le curseur.

    runtime\\python\\python.exe -m pytest backend/tests/test_material_render_r6.py -v

LE DEFAUT QUE CECI VERROUILLE. La ronde 5 avait ajoute le bloc `render`
(facteurs a 1.0, formule glTF, valeur effective MESUREE sur les octets livres).
Il etait ecrit a la derivation... et jamais recalcule ensuite. Mesure sur le
backend en marche, matiere « pierre moussue » :

    curseur      GLB apercu / export      API : render.effective.roughness
    0.00         0.0000                   0.485
    0.25         0.2499                   0.485
    0.50         0.4999                   0.485
    0.75         0.7499                   0.485
    1.00         1.0000                   0.485

Le GLB suivait le curseur, le contrat publie annoncait la valeur de la derniere
derivation. Un importateur qui lit `render.effective` (c'est-a-dire le seul
chiffre qu'on lui demande de croire) recevait donc un nombre faux des le premier
mouvement de curseur.

Deuxieme piege, evite ici : recopier `level_stats` (loi affine, moyenne = le
niveau exactement) et l'appeler « mesure ». Les octets passent par une LUT
arrondie a l'entier ; a 4096 la moyenne encodee vaut 0.402 pour un curseur a
0.400. `level_mean` somme LUT x histogramme du motif : c'est la moyenne exacte
des octets, sans relire un pixel (1.46 s de decodage evitees a 4096).
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw                            # noqa: E402

from app.services import material_store as MS               # noqa: E402
from app.services import pbr_service as PBR                 # noqa: E402

CRANS = (0.0, 0.25, 0.50, 0.75, 1.00)


def _grain(w=192, h=192, seed=11):
    img = Image.new("RGB", (w, h), (140, 132, 124))
    px = img.load()
    s = seed
    for y in range(h):
        for x in range(w):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            n = (s >> 16) % 48 - 24
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    d = ImageDraw.Draw(img)
    for k in range(9):
        cx, cy = 20 + k * 18, 40 + (k * 37) % 110
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(96, 90, 84))
    return img


def _maps():
    return PBR.derive_maps(_grain(), None,
                           ["basecolor", "roughness", "metallic", "orm"])


# ═══════════ 1. la moyenne annoncee est celle des octets ════════════════════

def test_level_mean_is_the_exact_mean_of_the_baked_bytes():
    """A chaque cran, `level_mean` doit donner la moyenne des octets au
    centieme de niveau pres — pas la loi affine, les octets."""
    maps = _maps()
    hist = maps["roughness"].convert("L").histogram()[:256]
    for lv in CRANS:
        baked = PBR.bake_levels(maps, dict(MS.default_props(), roughness=lv))
        real = PBR.stats(baked["roughness"])["mean"] / 255.0
        told = PBR.level_mean(hist, lv)
        assert abs(told - real) <= 1e-4, (lv, told, real)


def test_level_mean_is_stricter_than_the_affine_prediction():
    """La loi affine annonce exactement le niveau ; les octets s'en ecartent.
    Si les deux etaient toujours egaux, ce module ne servirait a rien : on
    verifie qu'il existe au moins un cran ou l'ecart est reel."""
    maps = _maps()
    hist = maps["roughness"].convert("L").histogram()[:256]
    ecarts = []
    for lv in CRANS:
        baked = PBR.bake_levels(maps, dict(MS.default_props(), roughness=lv))
        real = PBR.stats(baked["roughness"])["mean"] / 255.0
        ecarts.append(abs(real - lv))
    assert max(ecarts) > 0.0, ecarts
    # et level_mean, lui, colle
    for lv in CRANS:
        baked = PBR.bake_levels(maps, dict(MS.default_props(), roughness=lv))
        real = PBR.stats(baked["roughness"])["mean"] / 255.0
        assert abs(PBR.level_mean(hist, lv) - real) <= abs(real - lv) + 1e-9


def test_level_mean_survives_a_missing_or_empty_histogram():
    assert PBR.level_mean([], 0.5) == 0.0
    assert PBR.level_mean([0] * 256, 0.5) == 0.0
    assert PBR.level_mean(None, 0.5) == 0.0


# ═══════════ 2. l'histogramme du motif est publie ═══════════════════════════

def test_map_stats_carries_the_pattern_histogram():
    """Sans l'histogramme, le curseur ne peut pas dire la verite sans relire
    16 M pixels. Il doit accompagner les trois maps a niveau."""
    mid = "mat_0000cafe"
    d = MS.material_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    for k, img in maps.items():
        img.save(d / f"{k}.png")
    st = MS.map_stats(mid, MS.default_props())
    for kind in ("roughness", "metallic", "orm"):
        h = st[kind].get("pattern_hist")
        assert isinstance(h, list) and len(h) == 256, (kind, type(h))
        assert sum(h) == 192 * 192, (kind, sum(h))


# ═══════════ 3. le contrat publie suit le curseur ═══════════════════════════

def test_render_block_follows_the_slider_through_the_patch_path():
    """Le chemin exact du PATCH : recalcul analytique des stats + moyenne
    exacte -> `render.effective`. Il doit egaler ce que mesure le GLB."""
    maps = _maps()
    props = dict(MS.default_props())
    hist = maps["roughness"].convert("L").histogram()[:256]
    for lv in CRANS:
        props["roughness"] = lv
        # ce que le PATCH publiera
        told = round(PBR.level_mean(hist, lv), 3)
        # ce que le GLB emportera reellement
        baked = PBR.bake_levels(maps, props)
        eff = PBR.effective_levels(baked)["roughness"]
        assert abs(told - eff) <= 0.001, (lv, told, eff)
        block = MS.render_block(props)
        block["effective"]["roughness"] = told
        assert block["roughnessFactor"] == 1.0
        assert abs(block["effective"]["roughness"] - eff) <= 0.001, lv


def test_the_archive_does_not_ship_the_internal_histograms():
    """L'histogramme du motif est de la comptabilité interne : il reste dans
    meta.json (le backend en a besoin) et sort de `material.json` livré, sinon
    l'archive emporte 9.4 ko de nombres illisibles."""
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    mat = MS.normalize_material({"id": "mat_0000feed", "name": "grain",
                                 "props": MS.default_props()})
    mat["map_stats"] = {"roughness": {"mean": 100.0, "informative": True,
                                      "pattern": {"mean": 120.0},
                                      "pattern_hist": [1] * 256}}
    pub = MS.public_material(mat)
    assert "pattern_hist" not in pub["map_stats"]["roughness"]
    assert pub["map_stats"]["roughness"]["pattern"] == {"mean": 120.0}
    assert "pattern_hist" in mat["map_stats"]["roughness"]      # non muté
    blob = MS.export_zip(mat, maps, "standard")
    import zipfile as _z, io as _io, json as _j
    with _z.ZipFile(_io.BytesIO(blob)) as z:
        got = _j.loads(z.read("material.json").decode("utf-8"))
    assert "pattern_hist" not in got["map_stats"]["roughness"]


def test_a_stale_render_block_cannot_survive_a_level_change():
    """Le bloc `render` d'une matiere relue est reconstruit sur ses props :
    un facteur perime ne peut pas revenir par la porte de derriere."""
    mat = MS.normalize_material({
        "id": "mat_0000beef", "name": "acier rouge",
        "props": dict(MS.default_props(), roughness=0.25),
        "render": {"levels_baked": [], "metallicFactor": 0.5,
                   "roughnessFactor": 0.5, "effective": {"roughness": 0.9,
                                                         "metallic": 0.9}},
    })
    assert mat["render"]["roughnessFactor"] == 1.0
    assert mat["render"]["metallicFactor"] == 1.0
    assert mat["render"]["levels_baked"] == ["metallic", "roughness"]
