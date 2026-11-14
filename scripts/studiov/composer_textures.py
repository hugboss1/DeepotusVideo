# -*- coding: utf-8 -*-
"""SVH (14/11/2026) — fabrique le PACK DE MATIÈRES D'INTÉRIEUR du studio virtuel depuis Poly Haven (CC0) :
backend/app/studiov/textures/ (catalog.json, NOTICE.txt, <slug>/{basecolor,normal,roughness,vignette}.jpg).

Même doctrine que scripts/build_materials_catalog.py (catalogue de la Forge) : on télécharge UNE fois, au build ;
l'application n'a jamais besoin du réseau. Ce pack COMPLÈTE les trente matières de la Forge (sols, murs, métaux, bois,
tissus, béton) par ce qu'il faut à un intérieur de studio : parquets, enduits clairs, marbre, moquette, cuirs, velours,
placages. Les deux catalogues sont servis ensemble au décorateur (services/studiov_habillage.py).

Poids : la couleur en 1024 px (elle se voit), la normale et la rugosité en 512 px (elles se devinent) ; une vignette de
96 px pour la grille du décorateur. Liste EXPLICITE d'identifiants : un filtre par catégorie rendrait un pack différent
à chaque build.

  python scripts/studiov/composer_textures.py --fetch    télécharge (cache .cache/studiov-polyhaven) puis fabrique
  python scripts/studiov/composer_textures.py            fabrique depuis le cache
  python scripts/studiov/composer_textures.py --check    vérifie que catalog.json et les fichiers concordent
  python scripts/studiov/composer_textures.py --planche f.jpg   une planche-contact des couleurs (contrôle visuel)"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import shutil
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SORTIE = REPO / "backend" / "app" / "studiov" / "textures"
CACHE = REPO / ".cache" / "studiov-polyhaven"
API = "https://api.polyhaven.com"
LICENCE_URL = "https://polyhaven.com/license"
UA = "DeepotusVideoGen/2.8 (+virtual studio materials build script)"
CARTES = (("Diffuse", "basecolor", 1024, 80), ("nor_gl", "normal", 512, 86), ("Rough", "roughness", 512, 80))

FAMILLES = [
    {"id": "sols", "nom": "Sols", "nom_en": "Floors"},
    {"id": "murs", "nom": "Murs", "nom_en": "Walls"},
    {"id": "bois", "nom": "Bois et placages", "nom_en": "Wood and veneers"},
    {"id": "tissus", "nom": "Tissus et cuirs", "nom_en": "Fabrics and leathers"},
    {"id": "metaux", "nom": "Métaux", "nom_en": "Metals"},
]

# usages : où la matière se propose d'abord dans le décorateur (sol, mur, plafond, bois, tissu, cuir, metal, pierre)
A = lambda slug, nom, nom_en, famille, *usages: {"slug": slug, "nom": nom, "nom_en": nom_en, "famille": famille,  # noqa: E731
                                                "usages": list(usages)}
ASSETS = [
    A("laminate_floor_02", "Stratifié chêne", "Oak laminate", "sols", "sol", "bois"),
    A("herringbone_parquet", "Parquet à chevrons", "Herringbone parquet", "sols", "sol"),
    A("diagonal_parquet", "Parquet en diagonale", "Diagonal parquet", "sols", "sol"),
    A("wood_floor", "Plancher sombre", "Dark plank floor", "sols", "sol", "bois"),
    A("plank_flooring_02", "Plancher de pin", "Pine plank floor", "sols", "sol", "bois"),
    A("concrete_floor_worn_001", "Béton ciré", "Polished concrete", "sols", "sol", "mur"),
    A("painted_concrete", "Béton peint vert, usé", "Worn green painted concrete", "sols", "sol"),
    A("interior_tiles", "Carrelage d'intérieur", "Interior tiles", "sols", "sol"),
    A("terrazzo_tiles", "Terrazzo brun", "Brown terrazzo", "sols", "sol", "pierre"),
    A("marble_01", "Dalles de pierre beige", "Beige stone slabs", "sols", "sol", "mur", "pierre"),
    A("checkered_pavement_tiles", "Dallage en damier", "Checkered tiles", "sols", "sol"),
    A("rubber_tiles", "Dalles de caoutchouc noir", "Black rubber tiles", "sols", "sol"),
    A("rubberized_track", "Piste de sport", "Running track", "sols", "sol"),
    A("dirty_carpet", "Moquette sombre", "Dark carpet", "sols", "sol", "tissu"),
    A("leafy_grass", "Pelouse", "Grass", "sols", "sol"),

    A("white_plaster_02", "Enduit gris nuagé", "Cloudy grey plaster", "murs", "mur", "plafond"),
    A("plastered_wall", "Plâtre lissé", "Smooth plaster", "murs", "mur", "plafond"),
    A("white_rough_plaster", "Peinture écaillée", "Peeling paint", "murs", "mur", "plafond"),
    A("grey_plaster", "Enduit patiné", "Weathered plaster", "murs", "mur"),
    A("plaster_grey_04", "Plâtre gris clair", "Light grey plaster", "murs", "mur", "plafond"),
    A("concrete_wall_008", "Béton lisse", "Smooth concrete", "murs", "mur"),
    A("patterned_concrete_wall", "Béton à motifs", "Patterned concrete", "murs", "mur"),
    A("painted_brick", "Brique peinte en bleu", "Blue painted brick", "murs", "mur"),
    A("factory_brick", "Brique d'usine", "Factory brick", "murs", "mur"),

    A("oak_veneer_01", "Placage de chêne", "Oak veneer", "bois", "bois", "mur"),
    A("rosewood_veneer1", "Placage de palissandre", "Rosewood veneer", "bois", "bois"),
    A("dark_wood", "Bois exotique veiné", "Veined exotic wood", "bois", "bois", "sol"),
    A("plywood", "Contreplaqué", "Plywood", "bois", "bois", "mur"),
    A("wood_table_001", "Bois foncé verni", "Dark varnished wood", "bois", "bois"),
    A("wood_cabinet_worn_long", "Bois patiné", "Worn wood", "bois", "bois"),

    A("leather_white", "Cuir clair", "Light leather", "tissus", "cuir"),
    A("leather_red_02", "Cuir brun foncé", "Dark brown leather", "tissus", "cuir"),
    A("fabric_leather_02", "Cuir cognac", "Cognac leather", "tissus", "cuir"),
    A("velour_velvet", "Velours framboise", "Raspberry velvet", "tissus", "tissu"),
    A("poly_wool_herringbone", "Laine grise à chevrons", "Grey herringbone wool", "tissus", "tissu"),
    A("fabric_pattern_07", "Vichy vert", "Green gingham", "tissus", "tissu"),
    A("cotton_jersey", "Jersey rosé", "Blush jersey", "tissus", "tissu"),
    A("quatrefoil_jacquard_fabric", "Jacquard rouge", "Red jacquard", "tissus", "tissu"),
    A("curly_teddy_natural", "Bouclette crème", "Cream teddy fleece", "tissus", "tissu"),
    A("book_pattern", "Toile olive", "Olive bookcloth", "tissus", "tissu"),

    A("metal_plate_02", "Tôle sombre", "Dark sheet metal", "metaux", "metal"),
    A("painted_metal_shutter", "Rideau métallique", "Metal shutter", "metaux", "metal", "mur"),
]


def _get(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "DeepotusVideoGen"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def assert_cc0() -> None:
    """La licence se VÉRIFIE au build : si la page de Poly Haven ne dit plus CC0, on ne redistribue rien."""
    if "CC0" not in _get(LICENCE_URL).decode("utf-8", "replace").upper():
        raise SystemExit("[licence] polyhaven.com/license ne mentionne plus CC0 : build abandonné.")


def fetch() -> None:
    assert_cc0()
    CACHE.mkdir(parents=True, exist_ok=True)
    for a in ASSETS:
        slug = a["slug"]
        fichiers = json.loads(_get(f"{API}/files/{slug}"))
        (CACHE / f"{slug}.info.json").write_bytes(_get(f"{API}/info/{slug}"))
        for cle, notre, _cote, _q in CARTES:
            # certaines matières n'ont pas de « Diffuse » mais des variantes de couleur (coll1, coll2…) : la première
            noms = [cle] + ([k for k in sorted(fichiers) if k.lower().startswith("col")] if cle == "Diffuse" else [])
            bloc = next((x for x in (((fichiers.get(n) or {}).get("1k") or {}).get("jpg") for n in noms) if x), None)
            if not bloc:
                raise SystemExit(f"[{slug}] carte « {cle} » absente en 1k/jpg : {sorted(fichiers)}")
            dest = CACHE / f"{slug}.{notre}.jpg"
            if dest.is_file() and hashlib.md5(dest.read_bytes()).hexdigest() == bloc.get("md5"):
                continue
            data = _get(bloc["url"], timeout=300)
            if bloc.get("md5") and hashlib.md5(data).hexdigest() != bloc["md5"]:
                raise SystemExit(f"[{slug}/{cle}] empreinte différente de celle de l'API : abandon")
            dest.write_bytes(data)
            print(f"[fetch] {slug}/{notre} {len(data) // 1024} Ko")


def _jpeg(im, cote: int, qualite: int) -> bytes:
    from PIL import Image
    im = im.convert("RGB")
    if im.size != (cote, cote):
        im = im.resize((cote, cote), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=qualite, optimize=True, subsampling=1)
    return buf.getvalue()


def build() -> dict:
    from PIL import Image
    if SORTIE.exists():
        shutil.rmtree(SORTIE)
    SORTIE.mkdir(parents=True)
    textures, notices = [], []
    for a in ASSETS:
        slug = a["slug"]
        info_f = CACHE / f"{slug}.info.json"
        if not info_f.is_file():
            raise SystemExit(f"[{slug}] absente du cache : lancez avec --fetch")
        info = json.loads(info_f.read_text("utf-8"))
        (SORTIE / slug).mkdir()
        poids = 0
        for _cle, notre, cote, q in CARTES:
            with Image.open(CACHE / f"{slug}.{notre}.jpg") as im:
                data = _jpeg(im, cote, q)
            (SORTIE / slug / f"{notre}.jpg").write_bytes(data)
            poids += len(data)
        with Image.open(CACHE / f"{slug}.basecolor.jpg") as im:
            rvb = im.convert("RGB")
            v = _jpeg(rvb, 96, 78)
            r, g, b = rvb.resize((1, 1), Image.BOX).getpixel((0, 0))
        (SORTIE / slug / "vignette.jpg").write_bytes(v)
        poids += len(v)
        dims = info.get("dimensions") or [1000, 1000]
        auteurs = info.get("authors") or {}
        textures.append({"id": slug, "nom": a["nom"], "nom_en": a["nom_en"], "famille": a["famille"],
                         "usages": a["usages"], "taille_m": round(max(0.05, float(dims[0]) / 1000.0), 3),
                         "moyenne": f"#{r:02x}{g:02x}{b:02x}", "auteurs": sorted(auteurs),
                         "url": f"https://polyhaven.com/a/{slug}", "octets": poids})
        notices.append(f"{a['nom']} ({slug}) — Poly Haven — CC0 1.0\n  https://polyhaven.com/a/{slug}\n"
                       f"  {', '.join(f'{k} ({w})' for k, w in auteurs.items())}")
        print(f"[build] {slug} {poids // 1024} Ko")
    cat = {"version": 1, "source": {"nom": "Poly Haven", "url": "https://polyhaven.com", "licence": "CC0-1.0",
                                    "licence_url": LICENCE_URL},
           "familles": FAMILLES, "textures": textures}
    (SORTIE / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
    (SORTIE / "NOTICE.txt").write_text(
        "Matières d'intérieur du studio virtuel — DeepotusVideoGen\n"
        "=========================================================\n\n"
        "Toutes les matières ci-dessous viennent de Poly Haven et sont publiées sous Creative Commons Zero\n"
        "(CC0 1.0) : usage commercial libre, aucune attribution exigée. Cette notice est un remerciement.\n\n"
        + "\n\n".join(notices) + "\n", "utf-8", newline="\n")
    return cat


def check() -> int:
    f = SORTIE / "catalog.json"
    if not f.is_file():
        print(f"[check] catalog.json absent : {f}")
        return 1
    cat = json.loads(f.read_text("utf-8"))
    attendus = {"catalog.json", "NOTICE.txt"}
    total = 0
    for t in cat["textures"]:
        for carte in ("basecolor", "normal", "roughness", "vignette"):
            attendus.add(f"{t['id']}/{carte}.jpg")
    presents = {p.relative_to(SORTIE).as_posix() for p in SORTIE.rglob("*") if p.is_file()}
    total = sum(p.stat().st_size for p in SORTIE.rglob("*") if p.is_file())
    ids = [t["id"] for t in cat["textures"]]
    print(f"[check] {len(ids)} matières, {total / 1048576:.1f} Mo")
    if attendus != presents or ids != [a["slug"] for a in ASSETS]:
        print(f"[check] ÉCART : manquants {sorted(attendus - presents)[:8]} ; en trop {sorted(presents - attendus)[:8]}")
        return 1
    return 0


def planche(dest: str) -> None:
    from PIL import Image, ImageDraw
    n, cote, col = len(ASSETS), 150, 7
    im = Image.new("RGB", (col * cote, ((n + col - 1) // col) * (cote + 14)), "#202020")
    d = ImageDraw.Draw(im)
    for i, a in enumerate(ASSETS):
        with Image.open(SORTIE / a["slug"] / "basecolor.jpg") as t:
            im.paste(t.resize((cote, cote)), ((i % col) * cote, (i // col) * (cote + 14)))
        d.text(((i % col) * cote + 2, (i // col) * (cote + 14) + cote + 1), a["slug"][:24], fill="#ffffff")
    im.save(dest, quality=85)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--planche")
    args = ap.parse_args()
    if args.check:
        sys.exit(check())
    if args.planche:
        planche(args.planche)
        sys.exit(0)
    if args.fetch:
        fetch()
    build()
    sys.exit(check())
