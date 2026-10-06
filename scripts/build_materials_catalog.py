# -*- coding: utf-8 -*-
# scripts/build_materials_catalog.py
"""Fabrique le catalogue de démarrage des MATIÈRES depuis Poly Haven (CC0).

POURQUOI AU BUILD ET PAS À L'EXÉCUTION. L'application est un studio LOCAL : un
écran de matières qui exige le réseau pour montrer quoi que ce soit trahit sa
promesse, et une API tierce qui bouge casserait l'écran d'un utilisateur qui
n'a rien demandé. Les assets sont CC0 — donc redistribuables sans condition —
et l'API autorise depuis le 18/07/2026 l'usage commercial (ToS relues le
03/09/2026). Rien n'oblige donc à appeler quoi que ce soit depuis le produit :
on télécharge une fois, ici, et l'application n'a plus jamais besoin du
réseau. Même doctrine que `build_starter_catalog.py` pour les sons Kenney.

TROIS CARTES EMBARQUÉES, CINQ DÉRIVÉES, et c'est un choix mesuré. Poly Haven
publie jusqu'à onze cartes par matière ; trois seulement portent une
information qu'une dérivation ne peut pas inventer — la couleur, la normale
MESURÉE (un relief photogrammétré, pas une estimation depuis l'albédo) et la
rugosité. L'occlusion, la hauteur, le métal, l'émissif et l'ORM se dérivent
localement, gratuitement et hors ligne par `pbr_service` : les embarquer
doublerait le poids de l'installeur pour zéro information. La fiche de chaque
matière importée le DIT.

Sortie : backend/app/assets/materials/ (dans le paquet Python, donc embarquée
par l'installeur qui recopie {#AppRoot}\\* — rien à ajouter au .iss) :

    catalog.json          index unique lu par starter_materials.py
    NOTICE.txt            sources, auteurs et licence (remerciement, pas
                          obligation : la CC0 n'exige aucune attribution)
    <slug>/basecolor.jpg  1024x1024, JPEG q82
    <slug>/normal.jpg     idem — carte MESURÉE, convention OpenGL (nor_gl)
    <slug>/roughness.jpg  idem

Usage :
  python scripts/build_materials_catalog.py --fetch    # télécharge puis build
  python scripts/build_materials_catalog.py --check    # vérifie la sortie
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "backend" / "app" / "assets" / "materials"
CACHE_DEFAULT = REPO / ".cache" / "materials-polyhaven"

API = "https://api.polyhaven.com"
LICENCE_URL = "https://polyhaven.com/license"
# Les ToS (relues le 03/09/2026) exigent « a unique Referer header or
# user-agent that matches your software name ». Le voici.
UA = "DeepotusVideoGen/2.1 (+materials starter catalog build script)"

RES = "1k"                 # la résolution du catalogue embarqué
COTE = 1024                # les cartes sont ré-encodées à ce côté
QUALITE = 82               # JPEG : au-dessus, le poids double pour rien
# Les trois cartes de Poly Haven que l'on embarque, et leur nom chez nous.
CARTES = (("Diffuse", "basecolor"), ("nor_gl", "normal"), ("Rough", "roughness"))

FAMILLES = [
    {"id": "sols", "name": "Sols"},
    {"id": "murs", "name": "Murs & briques"},
    {"id": "metaux", "name": "Métaux"},
    {"id": "bois", "name": "Bois"},
    {"id": "tissus", "name": "Tissus & cuirs"},
    {"id": "beton_terrain", "name": "Béton & terrains"},
]

# LES TRENTE, PAR IDENTIFIANT EXPLICITE. Chacun a été vérifié présent dans
# `api.polyhaven.com/assets?t=textures` le 03/09/2026. Une liste explicite et
# pas un filtre par catégorie : un filtre rendrait un catalogue différent à
# chaque build, donc un installeur non reproductible et des captures d'écran
# qui mentent.
ASSETS = [
    {"slug": "brick_floor_003", "name": "Sol de briques", "family": "sols"},
    {"slug": "brown_floor_tiles", "name": "Carrelage brun", "family": "sols"},
    {"slug": "anti_skid_tiles", "name": "Dalles antidérapantes", "family": "sols"},
    {"slug": "asphalt_04", "name": "Asphalte", "family": "sols"},
    {"slug": "bicolour_gravel", "name": "Gravier bicolore", "family": "sols"},

    {"slug": "brick_wall_001", "name": "Mur de briques rouges", "family": "murs"},
    {"slug": "brick_wall_003", "name": "Mur de briques clair", "family": "murs"},
    {"slug": "castle_brick_02_red", "name": "Brique de château, rouge", "family": "murs"},
    {"slug": "beige_wall_001", "name": "Enduit beige", "family": "murs"},
    {"slug": "blue_plaster_wall", "name": "Enduit bleu", "family": "murs"},

    {"slug": "metal_plate", "name": "Tôle striée", "family": "metaux"},
    {"slug": "corrugated_iron_02", "name": "Tôle ondulée", "family": "metaux"},
    {"slug": "rusty_metal_02", "name": "Métal rouillé", "family": "metaux"},
    {"slug": "green_metal_rust", "name": "Métal peint rouillé", "family": "metaux"},
    {"slug": "blue_metal_plate", "name": "Plaque de métal bleue", "family": "metaux"},

    {"slug": "brown_planks_03", "name": "Planches brunes", "family": "bois"},
    {"slug": "black_walnut_veneer_01", "name": "Placage de noyer", "family": "bois"},
    {"slug": "bamboo_wall", "name": "Bambou", "family": "bois"},
    {"slug": "black_painted_planks", "name": "Planches peintes en noir", "family": "bois"},
    {"slug": "ash_veneer", "name": "Placage de frêne", "family": "bois"},

    {"slug": "denim_fabric", "name": "Denim", "family": "tissus"},
    {"slug": "rough_linen", "name": "Lin brut", "family": "tissus"},
    {"slug": "brown_leather", "name": "Cuir brun", "family": "tissus"},
    {"slug": "ribbed_corduroy", "name": "Velours côtelé", "family": "tissus"},
    {"slug": "wool_boucle", "name": "Laine bouclée", "family": "tissus"},

    {"slug": "brushed_concrete", "name": "Béton brossé", "family": "beton_terrain"},
    {"slug": "anti_slip_concrete", "name": "Béton antidérapant", "family": "beton_terrain"},
    {"slug": "aerial_rocks_02", "name": "Rochers", "family": "beton_terrain"},
    {"slug": "brown_mud_dry", "name": "Terre sèche", "family": "beton_terrain"},
    {"slug": "aerial_sand", "name": "Sable", "family": "beton_terrain"},
]


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "DeepotusVideoGen"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _json(url: str) -> dict:
    return json.loads(_get(url).decode("utf-8"))


def assert_cc0() -> str:
    """Abandonne si la page de licence ne dit plus CC0.

    Même garde que `_assert_cc0` du catalogue de sons : la licence se VÉRIFIE
    au build. Poly Haven n'expose pas de champ `license` par asset (mesuré le
    03/09/2026 sur /info/brick_wall_001) — c'est donc la page du site qui fait
    foi, et un changement en amont fait échouer le build au lieu de
    contaminer silencieusement l'installeur."""
    txt = _get(LICENCE_URL).decode("utf-8", "replace")
    if "CC0" not in txt.upper():
        raise SystemExit(
            "[licence] polyhaven.com/license ne mentionne plus CC0 — build "
            "abandonné. Relire la page avant de redistribuer quoi que ce soit.")
    return LICENCE_URL


def fetch(cache: pathlib.Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for a in ASSETS:
        slug = a["slug"]
        fichiers = _json(f"{API}/files/{slug}")
        info = _json(f"{API}/info/{slug}")
        (cache / f"{slug}.info.json").write_text(
            json.dumps(info, ensure_ascii=False), encoding="utf-8")
        for cle, notre in CARTES:
            bloc = ((fichiers.get(cle) or {}).get(RES) or {}).get("jpg")
            if not bloc:
                raise SystemExit(
                    f"[{slug}] carte « {cle} » absente en {RES}/jpg — "
                    f"cartes publiées : {sorted(fichiers)}")
            dest = cache / f"{slug}.{notre}.jpg"
            if dest.is_file() and hashlib.md5(dest.read_bytes()).hexdigest() \
                    == bloc.get("md5"):
                continue
            data = _get(bloc["url"], timeout=300)
            got = hashlib.md5(data).hexdigest()
            if bloc.get("md5") and got != bloc["md5"]:
                raise SystemExit(f"[{slug}/{cle}] md5 {got} != {bloc['md5']} "
                                 "annoncé par l'API — téléchargement abandonné")
            dest.write_bytes(data)
            print(f"[fetch] {slug}/{notre}: {len(data) // 1024} Ko")


def build(cache: pathlib.Path, out: pathlib.Path) -> dict:
    from PIL import Image
    licence = assert_cc0()
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    materials, notices = [], []
    for a in ASSETS:
        slug = a["slug"]
        info_p = cache / f"{slug}.info.json"
        if not info_p.is_file():
            raise SystemExit(f"[{slug}] info absente : {info_p}\n"
                             "-> lancez avec --fetch.")
        info = json.loads(info_p.read_text(encoding="utf-8"))
        (out / slug).mkdir(parents=True, exist_ok=True)
        cartes, poids = {}, 0
        for _cle, notre in CARTES:
            src = cache / f"{slug}.{notre}.jpg"
            if not src.is_file():
                raise SystemExit(f"[{slug}] carte absente : {src}")
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.size != (COTE, COTE):
                    im = im.resize((COTE, COTE), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=QUALITE, optimize=True,
                        subsampling=1)
            (out / slug / f"{notre}.jpg").write_bytes(buf.getvalue())
            cartes[notre] = f"{slug}/{notre}.jpg"
            poids += len(buf.getvalue())
        auteurs = info.get("authors") or {}
        materials.append({
            "id": slug, "name": a["name"], "family": a["family"],
            "polyhaven_name": info.get("name") or slug,
            "tags": list(info.get("tags") or [])[:8],
            "authors": auteurs,
            # `scale` et `dimensions` sont RELEVÉS mais jamais interprétés :
            # E1 de R10c écarte la taille physique propagée aux moteurs.
            "scale": info.get("scale"), "dimensions": info.get("dimensions"),
            "url": f"https://polyhaven.com/a/{slug}",
            "maps": cartes, "bytes": poids})
        notices.append(f"{a['name']} ({slug}) — Poly Haven — CC0 1.0\n"
                       f"  https://polyhaven.com/a/{slug}\n"
                       f"  {', '.join(f'{k} ({v})' for k, v in auteurs.items())}")
        print(f"[build] {slug}: {poids // 1024} Ko")

    cat = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
                                .replace("+00:00", "Z"),
        "source": {"name": "Poly Haven", "url": "https://polyhaven.com",
                   "license": "CC0-1.0", "license_url": licence},
        "families": [{**f, "count": sum(1 for m in materials
                                        if m["family"] == f["id"])}
                     for f in FAMILLES],
        "materials": materials,
    }
    (out / "catalog.json").write_text(
        json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "NOTICE.txt").write_text(
        "Catalogue de matières DeepotusVideoGen\n"
        "======================================\n\n"
        "Toutes les matières ci-dessous viennent de Poly Haven et sont\n"
        "publiées sous Creative Commons Zero (CC0 1.0) : usage commercial\n"
        "libre, aucune attribution exigée. Cette notice est un remerciement.\n\n"
        "Trois cartes sont embarquées (couleur, normale mesurée, rugosité) ;\n"
        "les cinq autres sont dérivées localement par l'application.\n\n"
        + "\n\n".join(notices) + "\n", encoding="utf-8")
    return cat


def check(out: pathlib.Path) -> int:
    p = out / "catalog.json"
    if not p.is_file():
        print(f"[check] catalog.json absent — {p}")
        return 1
    cat = json.loads(p.read_text(encoding="utf-8"))
    manquant, orphelin, declares = [], [], set()
    total = 0
    for m in cat["materials"]:
        for rel in m["maps"].values():
            declares.add(rel)
            f = out / rel
            if not f.is_file():
                manquant.append(rel)
            else:
                total += f.stat().st_size
    for f in out.rglob("*"):
        if f.is_file() and f.name not in ("catalog.json", "NOTICE.txt"):
            rel = f.relative_to(out).as_posix()
            if rel not in declares:
                orphelin.append(rel)
    print(f"[check] {len(cat['materials'])} matières, "
          f"{len(declares)} cartes, {total / 1024 / 1024:.1f} Mo")
    if manquant:
        print(f"[check] MANQUANT ({len(manquant)}) : {manquant[:10]}")
    if orphelin:
        print(f"[check] ORPHELIN ({len(orphelin)}) : {orphelin[:10]}")
    if manquant or orphelin:
        return 1
    print("[check] catalogue et fichiers concordent.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(CACHE_DEFAULT))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    if args.check:
        return check(out)
    cache = pathlib.Path(args.cache)
    if args.fetch:
        fetch(cache)
    build(cache, out)
    return check(out)


if __name__ == "__main__":
    sys.exit(main())
