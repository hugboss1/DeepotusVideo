# -*- coding: utf-8 -*-
# scripts/build_starter_catalog.py
"""Fabrique le catalogue de démarrage « Son & VFX » depuis des packs CC0.

Pourquoi : un acheteur qui lance l'app pour la première fois n'a NI clé
ElevenLabs NI clé fal. Sans catalogue embarqué, les trois sous-catégories de
Son & VFX (SFX, VFX particules, Sprites) sont des écrans vides qui promettent
une facture. Ce script transforme des packs libres en un catalogue jouable
hors ligne, livré avec l'app.

Source unique : kenney.nl, licence Creative Commons Zero (CC0 1.0). La CC0 est
la SEULE licence acceptée ici — elle autorise la redistribution commerciale
sans attribution ni part virale. La vérification n'est pas décorative :
`_assert_cc0` lit le License.txt de CHAQUE archive et abandonne si la mention
CC0 n'y est pas. Un pack qui changerait de licence en amont fait échouer le
build au lieu de contaminer silencieusement l'installeur.

Sortie : backend/app/assets/starter/ (dans le paquet Python, donc embarqué par
l'installeur qui recopie {#AppRoot}\\* — rien à ajouter au .iss) :

    catalog.json          index unique lu par starter_catalog.py
    NOTICE.txt            attributions + licences (obligation morale, pas légale)
    particles/<id>.png    textures de particules 512² RGBA
    particles/thumb/*.png vignettes 128² pour la grille de l'UI
    anims/<seq>/NNN.png   séquences animées prêtes à assembler en sprite sheet
    anims/<seq>/thumb.png vignette de la séquence (frame la plus dense)
    sfx/<famille>/<id>.ogg bruitages classés par famille

Durées audio : lues directement dans l'en-tête Ogg (page finale + granule /
sample-rate). Pur Python — pas de ffprobe, pas 559 sous-processus au build,
et le runtime n'a plus rien à sonder puisque catalog.json porte les durées.

Idempotent et relançable : la sortie est reconstruite à l'identique à partir
des .zip. `--check` ne réécrit rien et ne fait que confronter catalog.json aux
fichiers réellement présents (garde de CI / de packaging).

Usage :
  python scripts/build_starter_catalog.py --fetch      # télécharge puis build
  python scripts/build_starter_catalog.py --zips <dir> # build depuis des .zip locaux
  python scripts/build_starter_catalog.py --check      # vérifie la sortie existante
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import shutil
import struct
import sys
import unicodedata
import urllib.request
import zipfile
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "backend" / "app" / "assets" / "starter"
ZIPS_DEFAULT = REPO / ".cache" / "starter-packs"

UA = "DeepotusVideoGen/2.1 (+starter-catalog build script)"


# ── packs sources ───────────────────────────────────────────────────────────
# `kind` pilote l'extraction ; `pick` filtre les membres de l'archive.
#   particles : PNG (Transparent) NON pivotés — les « Rotated » sont la même
#               texture pré-tournée, inutile puisque le générateur fait
#               tourner chaque particule lui-même.
#   anims     : séquences de frames (un dossier = une animation).
#   sfx       : tous les .ogg sauf les « Preview.ogg » (démos du pack, pas des
#               bruitages — les embarquer polluerait le catalogue).
PACKS = [
    {"slug": "particle-pack", "name": "Particle Pack", "kind": "particles",
     "pick": lambda n: n.startswith("PNG (Transparent)/")
     and "/Rotated/" not in n and n.lower().endswith(".png")},
    {"slug": "smoke-particles", "name": "Smoke Particles", "kind": "anims",
     "pick": lambda n: n.startswith("PNG/") and n.lower().endswith(".png")},
    {"slug": "impact-sounds", "name": "Impact Sounds", "kind": "sfx"},
    {"slug": "interface-sounds", "name": "Interface Sounds", "kind": "sfx"},
    {"slug": "ui-audio", "name": "UI Audio", "kind": "sfx"},
    {"slug": "digital-audio", "name": "Digital Audio", "kind": "sfx"},
    {"slug": "sci-fi-sounds", "name": "Sci-fi Sounds", "kind": "sfx"},
    {"slug": "rpg-audio", "name": "RPG Audio", "kind": "sfx"},
    {"slug": "music-jingles", "name": "Music Jingles", "kind": "sfx"},
    {"slug": "casino-audio", "name": "Casino Audio", "kind": "sfx"},
]

# ── familles SFX (l'ordre est celui du rail de l'écran Son & VFX) ───────────
# Chaque famille : libellé FR + règle d'appartenance. Une famille est un
# RANGEMENT, pas une source : « Impacts » agrège les impacts du pack Impact
# Sounds ET les explosions du pack Sci-fi, parce que c'est ce que l'utilisateur
# cherche. Le premier prédicat qui matche gagne (ordre significatif).
SFX_FAMILIES = [
    {"id": "impacts", "name": "Impacts & explosions",
     "desc": "Chocs, coups, verre, métal, bois, explosions",
     "match": lambda pack, stem: (
         stem.startswith("impact") or "explosion" in stem.lower())},
    {"id": "steps", "name": "Pas & matières",
     "desc": "Pas au sol, tissu, cuir, grincements, découpe",
     "match": lambda pack, stem: (
         stem.startswith("footstep") or stem.startswith("cloth")
         or stem in ("creak", "chop", "knifeSlice", "drawKnife",
                     "dropLeather", "handleSmallLeather", "beltHandle"))},
    {"id": "interface", "name": "Interface",
     "desc": "Clics, bascules, confirmations, erreurs, survols",
     "match": lambda pack, stem: pack in ("interface-sounds", "ui-audio")},
    {"id": "digital", "name": "Numérique & rétro",
     "desc": "Zaps, bips, power-up, tonalités arcade",
     "match": lambda pack, stem: pack == "digital-audio"},
    {"id": "scifi", "name": "Science-fiction",
     "desc": "Lasers, moteurs, champs de force, sas",
     "match": lambda pack, stem: pack == "sci-fi-sounds"},
    {"id": "objects", "name": "Objets & décor",
     "desc": "Portes, livres, pièces, serrures, ustensiles",
     "match": lambda pack, stem: pack == "rpg-audio"},
    {"id": "cards", "name": "Cartes & jetons",
     "desc": "Cartes battues, jetons, dés",
     "match": lambda pack, stem: pack == "casino-audio"},
    {"id": "jingles", "name": "Jingles",
     "desc": "Stingers courts — victoire, échec, transition",
     "match": lambda pack, stem: pack == "music-jingles"},
]

# Libellés FR des radicaux Kenney. Absent de la table -> le radical est
# simplement joli-formaté (camelCase -> mots). Traduire ce qui est CHERCHÉ,
# pas tout : « impactGlass_heavy » doit se trouver en tapant « verre ».
STEM_FR = {
    "impactBell_heavy": "Cloche, lourd", "impactGeneric_light": "Impact générique, léger",
    "impactGlass_heavy": "Verre, lourd", "impactGlass_light": "Verre, léger",
    "impactGlass_medium": "Verre, moyen", "impactMetal_heavy": "Métal, lourd",
    "impactMetal_light": "Métal, léger", "impactMetal_medium": "Métal, moyen",
    "impactMining": "Pioche", "impactPlank_medium": "Planche, moyen",
    "impactPlate_heavy": "Plaque, lourd", "impactPlate_light": "Plaque, léger",
    "impactPlate_medium": "Plaque, moyen", "impactPunch_heavy": "Coup de poing, lourd",
    "impactPunch_medium": "Coup de poing, moyen", "impactSoft_heavy": "Sourd, lourd",
    "impactSoft_medium": "Sourd, moyen", "impactTin_medium": "Tôle, moyen",
    "impactWood_heavy": "Bois, lourd", "impactWood_light": "Bois, léger",
    "impactWood_medium": "Bois, moyen", "impactMetal": "Impact métal",
    "footstep_carpet": "Pas sur tapis", "footstep_concrete": "Pas sur béton",
    "footstep_grass": "Pas sur herbe", "footstep_snow": "Pas dans la neige",
    "footstep_wood": "Pas sur bois", "footstep": "Pas",
    "explosionCrunch": "Explosion craquante",
    "lowFrequency_explosion": "Explosion basse fréquence",
    "back": "Retour", "bong": "Bong", "click": "Clic", "close": "Fermeture",
    "confirmation": "Confirmation", "drop": "Dépôt", "error": "Erreur",
    "glass": "Verre", "glitch": "Glitch", "maximize": "Agrandir",
    "minimize": "Réduire", "open": "Ouverture", "pluck": "Pincement",
    "question": "Question", "scratch": "Grattement", "scroll": "Défilement",
    "select": "Sélection", "switch": "Bascule", "tick": "Tic",
    "toggle": "Interrupteur", "mouseclick": "Clic souris",
    "mouserelease": "Relâchement souris", "rollover": "Survol",
    "highDown": "Aigu descendant", "highUp": "Aigu montant", "laser": "Laser",
    "lowDown": "Grave descendant", "lowRandom": "Grave aléatoire",
    "lowThreeTone": "Grave, trois tons", "pepSound": "Bip vif",
    "phaseJump": "Saut de phase", "phaserDown": "Phaser descendant",
    "phaserUp": "Phaser montant", "powerUp": "Power-up",
    "spaceTrash": "Parasite spatial", "threeTone": "Trois tons",
    "tone": "Tonalité", "twoTone": "Deux tons", "zap": "Zap",
    "zapThreeToneDown": "Zap trois tons, descendant",
    "zapThreeToneUp": "Zap trois tons, montant", "zapTwoTone": "Zap deux tons",
    "computerNoise": "Bruit d'ordinateur", "doorClose": "Porte qui se ferme",
    "doorOpen": "Porte qui s'ouvre", "engineCircular": "Moteur circulaire",
    "forceField": "Champ de force", "laserLarge": "Laser lourd",
    "laserRetro": "Laser rétro", "laserSmall": "Laser léger", "slime": "Slime",
    "spaceEngine": "Moteur spatial", "spaceEngineLarge": "Moteur spatial lourd",
    "spaceEngineLow": "Moteur spatial grave",
    "spaceEngineSmall": "Moteur spatial léger", "thrusterFire": "Propulseur",
    "beltHandle": "Ceinture", "bookClose": "Livre refermé",
    "bookFlip": "Page tournée", "bookOpen": "Livre ouvert",
    "bookPlace": "Livre posé", "chop": "Coup de hache", "cloth": "Tissu",
    "clothBelt": "Ceinture de tissu", "creak": "Grincement",
    "drawKnife": "Lame dégainée", "dropLeather": "Cuir lâché",
    "handleCoins": "Pièces manipulées",
    "handleSmallLeather": "Petite bourse", "knifeSlice": "Coup de lame",
    "metalClick": "Clic métallique", "metalLatch": "Loquet métallique",
    "metalPot": "Marmite",
    "card-fan-": "Cartes en éventail", "card-place-": "Carte posée",
    "card-shove-": "Cartes poussées", "card-shuffle": "Cartes battues",
    "card-slide-": "Carte glissée", "cards-pack-open-": "Paquet ouvert",
    "cards-pack-take-out-": "Carte sortie du paquet", "chip-lay-": "Jeton posé",
    "chips-collide-": "Jetons entrechoqués", "chips-handle-": "Jetons manipulés",
    "chips-stack-": "Pile de jetons", "dice-grab-": "Dés ramassés",
    "dice-shake-": "Dés secoués", "dice-throw-": "Dés lancés",
    "die-throw-": "Dé lancé",
    "jingles_HIT": "Jingle percussif", "jingles_NES": "Jingle 8-bit",
    "jingles_PIZZI": "Jingle pizzicato", "jingles_SAX": "Jingle saxophone",
    "jingles_STEEL": "Jingle steel drum",
}

# ── familles de particules (radical du nom de fichier Kenney) ───────────────
PARTICLE_FAMILIES = {
    "circle": ("Disques", "Disques doux — base de halo et de fumée"),
    "dirt": ("Poussière", "Éclats de terre et de gravats"),
    "fire": ("Feu", "Boules de feu pleines"),
    "flame": ("Flammes", "Langues de flamme étirées"),
    "flare": ("Halo", "Halo lenticulaire"),
    "light": ("Lumière", "Points lumineux et lueurs"),
    "magic": ("Magie", "Volutes et runes"),
    "muzzle": ("Départ de coup", "Éclairs de bouche"),
    "scorch": ("Brûlure", "Traces de suie"),
    "scratch": ("Griffure", "Rayures"),
    "slash": ("Entaille", "Coups de lame"),
    "smoke": ("Fumée", "Bouffées douces"),
    "spark": ("Étincelles", "Grains lumineux"),
    "star": ("Étoiles", "Étoiles et éclats"),
    "symbol": ("Symboles", "Glyphes"),
    "trace": ("Traînées", "Sillages et rubans"),
    "twirl": ("Spirales", "Tourbillons"),
    "window": ("Fenêtres", "Cadres et bordures"),
}

ANIM_FR = {
    "Black smoke": ("Fumée noire", "black-smoke"),
    "Explosion": ("Explosion", "explosion"),
    "Fart": ("Bouffée basse", "low-puff"),
    "Flash": ("Flash", "flash"),
    "White puff": ("Bouffée blanche", "white-puff"),
}


# ── utilitaires ─────────────────────────────────────────────────────────────
def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "x"


def _pretty(stem: str) -> str:
    """camelCase / snake_case -> mots lisibles (repli quand STEM_FR ne sait pas)."""
    s = re.sub(r"[_\-]+", " ", stem)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s).strip()
    return (s[:1].upper() + s[1:]) if s else stem


def _stem_of(name: str) -> str:
    """« impactGlass_heavy_003.ogg » -> « impactGlass_heavy »."""
    base = pathlib.Path(name).stem
    return re.sub(r"[_ ]?\d+$", "", base)


def ogg_duration(data: bytes) -> float:
    """Durée d'un Ogg Vorbis, en secondes, sans décodeur.

    Le sample-rate vit dans l'en-tête d'identification (\\x01vorbis) de la
    première page ; le nombre total d'échantillons est la granule position de
    la DERNIÈRE page. Retourne 0.0 si le fichier n'est pas exploitable — un
    catalogue avec une durée à 0 reste utilisable, un build qui explose non.
    """
    try:
        i = data.find(b"\x01vorbis")
        if i < 0:
            return 0.0
        rate = struct.unpack_from("<I", data, i + 12)[0]
        if not rate:
            return 0.0
        tail = data[-65536:]
        j = tail.rfind(b"OggS")
        if j < 0:
            return 0.0
        granule = struct.unpack_from("<q", tail, j + 6)[0]
        return round(max(0.0, granule / rate), 3)
    except (struct.error, IndexError, ZeroDivisionError):
        return 0.0


def _assert_cc0(zf: zipfile.ZipFile, slug: str) -> str:
    """Abandonne si l'archive ne porte pas une licence CC0. Retourne le texte."""
    names = [n for n in zf.namelist() if pathlib.Path(n).name.lower()
             in ("license.txt", "licence.txt")]
    if not names:
        raise SystemExit(f"[{slug}] aucun License.txt dans l'archive — build abandonné.")
    txt = zf.read(names[0]).decode("utf-8", "replace")
    if "cc0" not in txt.lower():
        raise SystemExit(
            f"[{slug}] la licence de l'archive n'est PAS CC0 :\n"
            f"{txt[:400]}\n"
            f"-> pack retiré de PACKS, ou redistribution impossible.")
    return txt


def _zip_url(slug: str) -> str:
    url = f"https://kenney.nl/assets/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(
        r"https://kenney\.nl/media/pages/assets/" + re.escape(slug)
        + r"/[^\"']+?\.zip", html)
    if not m:
        raise SystemExit(f"[{slug}] lien .zip introuvable sur {url} "
                         f"— la page a changé de structure.")
    return m.group(0)


def fetch_zips(zips_dir: pathlib.Path) -> None:
    zips_dir.mkdir(parents=True, exist_ok=True)
    for pack in PACKS:
        slug = pack["slug"]
        dest = zips_dir / f"kenney_{slug}.zip"
        if dest.is_file():
            print(f"[fetch] {slug}: déjà là ({dest.stat().st_size // 1024} Ko)")
            continue
        url = _zip_url(slug)
        print(f"[fetch] {slug}: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.write_bytes(r.read())
        print(f"[fetch] {slug}: {dest.stat().st_size // 1024} Ko")


# ── extraction ──────────────────────────────────────────────────────────────
def _thumb(png_bytes: bytes, size: int) -> bytes:
    from PIL import Image
    with Image.open(io.BytesIO(png_bytes)) as im:
        im = im.convert("RGBA")
        im.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def _alpha_mass(png_bytes: bytes) -> int:
    """Somme du canal alpha — sert à choisir la frame la plus « pleine »
    d'une séquence comme vignette (une frame de début est souvent vide)."""
    from PIL import Image
    with Image.open(io.BytesIO(png_bytes)) as im:
        return sum(im.convert("RGBA").getchannel("A").histogram()[i] * i
                   for i in range(256))


def build(zips_dir: pathlib.Path, out: pathlib.Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    (out / "particles" / "thumb").mkdir(parents=True, exist_ok=True)
    (out / "anims").mkdir(parents=True, exist_ok=True)
    (out / "sfx").mkdir(parents=True, exist_ok=True)

    sources, particles, anims, sfx = [], [], [], []
    notices = []

    for pack in PACKS:
        slug, kind = pack["slug"], pack["kind"]
        zpath = zips_dir / f"kenney_{slug}.zip"
        if not zpath.is_file():
            raise SystemExit(f"[{slug}] archive absente : {zpath}\n"
                             f"-> lancez avec --fetch, ou passez --zips <dir>.")
        with zipfile.ZipFile(zpath) as zf:
            licence = _assert_cc0(zf, slug)
            sources.append({
                "id": f"kenney-{slug}", "name": pack["name"], "author": "Kenney",
                "url": f"https://kenney.nl/assets/{slug}",
                "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            })
            notices.append(f"{pack['name']} — Kenney (kenney.nl) — CC0 1.0\n"
                           f"  https://kenney.nl/assets/{slug}\n"
                           f"{licence.strip()[:600]}\n")

            members = [n for n in zf.namelist() if not n.endswith("/")]
            if kind == "particles":
                _do_particles(zf, members, pack, out, particles)
            elif kind == "anims":
                _do_anims(zf, members, pack, out, anims)
            else:
                _do_sfx(zf, members, pack, out, sfx)
        print(f"[build] {slug}: OK")

    catalog = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc)
                                .isoformat(timespec="seconds")
                                .replace("+00:00", "Z"),
        "sources": sources,
        "sfx_families": [{"id": f["id"], "name": f["name"], "desc": f["desc"],
                          "count": sum(1 for s in sfx if s["family"] == f["id"])}
                         for f in SFX_FAMILIES],
        "particle_families": _particle_family_index(particles),
        "particles": particles,
        "anims": anims,
        "sfx": sfx,
    }
    (out / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "NOTICE.txt").write_text(
        "Catalogue de démarrage DeepotusVideoGen\n"
        "=======================================\n\n"
        "Tous les éléments ci-dessous sont publiés sous Creative Commons Zero\n"
        "(CC0 1.0) : usage commercial libre, aucune attribution exigée.\n"
        "Cette notice est un remerciement, pas une obligation.\n\n"
        + "\n".join(notices), encoding="utf-8")
    return catalog


def _do_particles(zf, members, pack, out, acc):
    picked = sorted(n for n in members if pack["pick"](n))
    if not picked:
        raise SystemExit(f"[{pack['slug']}] aucune texture retenue "
                         f"— le filtre `pick` ne correspond plus à l'archive.")
    for name in picked:
        base = pathlib.Path(name).name
        pid = pathlib.Path(base).stem                       # ex. « fire_02 »
        fam = re.sub(r"_\d+$", "", pid)
        label, _desc = PARTICLE_FAMILIES.get(fam, (_pretty(fam), ""))
        data = zf.read(name)
        (out / "particles" / f"{pid}.png").write_bytes(data)
        (out / "particles" / "thumb" / f"{pid}.png").write_bytes(_thumb(data, 128))
        num = (re.search(r"_(\d+)$", pid) or [None, ""])[1]
        acc.append({
            "id": pid, "family": fam,
            "name": f"{label} {num}".strip(),
            "file": f"particles/{pid}.png",
            "thumb": f"particles/thumb/{pid}.png",
            "source": f"kenney-{pack['slug']}",
        })


def _do_anims(zf, members, pack, out, acc):
    groups: dict[str, list[str]] = {}
    for name in members:
        if not pack["pick"](name):
            continue
        parts = pathlib.PurePosixPath(name).parts
        if len(parts) < 3:      # PNG/<dossier>/<frame>.png attendu
            continue
        groups.setdefault(parts[1], []).append(name)
    if not groups:
        raise SystemExit(f"[{pack['slug']}] aucune séquence trouvée.")
    for folder, names in sorted(groups.items()):
        label, aid = ANIM_FR.get(folder, (_pretty(folder), _slugify(folder)))
        names.sort()
        adir = out / "anims" / aid
        adir.mkdir(parents=True, exist_ok=True)
        best, best_mass = None, -1
        for i, name in enumerate(names):
            data = zf.read(name)
            (adir / f"{i:03d}.png").write_bytes(data)
            mass = _alpha_mass(data)
            if mass > best_mass:
                best, best_mass = data, mass
        (adir / "thumb.png").write_bytes(_thumb(best, 128))
        acc.append({
            "id": aid, "name": label, "frames": len(names),
            "dir": f"anims/{aid}", "thumb": f"anims/{aid}/thumb.png",
            "source": f"kenney-{pack['slug']}",
        })


def _do_sfx(zf, members, pack, out, acc):
    slug = pack["slug"]
    picked = sorted(n for n in members if n.lower().endswith(".ogg")
                    and pathlib.Path(n).stem.lower() != "preview")
    if not picked:
        raise SystemExit(f"[{slug}] aucun .ogg retenu.")
    for name in picked:
        base = pathlib.Path(name).name
        stem = _stem_of(base)
        fam = next((f["id"] for f in SFX_FAMILIES if f["match"](slug, stem)), None)
        if fam is None:
            raise SystemExit(
                f"[{slug}] « {stem} » n'entre dans aucune famille SFX. "
                f"-> compléter SFX_FAMILIES plutôt que de laisser un son "
                f"invisible dans l'UI.")
        sid = f"{_slugify(slug)}__{pathlib.Path(base).stem}"
        data = zf.read(name)
        fdir = out / "sfx" / fam
        fdir.mkdir(parents=True, exist_ok=True)
        (fdir / f"{sid}.ogg").write_bytes(data)
        num = (re.search(r"[_ ](\d+)$", pathlib.Path(base).stem) or [None, ""])[1]
        label = STEM_FR.get(stem, _pretty(stem))
        acc.append({
            "id": sid, "family": fam,
            "name": f"{label} {num}".strip() if num else label,
            "stem": stem,
            "file": f"sfx/{fam}/{sid}.ogg",
            "dur": ogg_duration(data),
            "source": f"kenney-{slug}",
        })


def _particle_family_index(particles):
    seen, out = {}, []
    for p in particles:
        seen.setdefault(p["family"], []).append(p)
    for fam in sorted(seen, key=lambda f: list(PARTICLE_FAMILIES).index(f)
                      if f in PARTICLE_FAMILIES else 99):
        label, desc = PARTICLE_FAMILIES.get(fam, (_pretty(fam), ""))
        out.append({"id": fam, "name": label, "desc": desc,
                    "count": len(seen[fam]), "cover": seen[fam][0]["id"]})
    return out


# ── vérification ────────────────────────────────────────────────────────────
def check(out: pathlib.Path) -> int:
    cat_path = out / "catalog.json"
    if not cat_path.is_file():
        print(f"[check] catalog.json absent — {cat_path}")
        return 1
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    missing, extra = [], []
    declared = set()
    for item in cat["particles"] + cat["sfx"]:
        for key in ("file", "thumb"):
            rel = item.get(key)
            if not rel:
                continue
            declared.add(rel)
            if not (out / rel).is_file():
                missing.append(rel)
    for anim in cat["anims"]:
        adir = out / anim["dir"]
        declared.add(anim["thumb"])
        n = len(list(adir.glob("[0-9][0-9][0-9].png"))) if adir.is_dir() else 0
        for i in range(anim["frames"]):
            declared.add(f"{anim['dir']}/{i:03d}.png")
        if n != anim["frames"]:
            missing.append(f"{anim['dir']} ({n}/{anim['frames']} frames)")
    for p in out.rglob("*"):
        if p.is_file() and p.name not in ("catalog.json", "NOTICE.txt"):
            rel = p.relative_to(out).as_posix()
            if rel not in declared:
                extra.append(rel)
    total = len(cat["particles"]) + len(cat["sfx"]) + len(cat["anims"])
    print(f"[check] {total} entrées — {len(cat['particles'])} textures, "
          f"{len(cat['anims'])} animations, {len(cat['sfx'])} sons")
    if missing:
        print(f"[check] MANQUANT ({len(missing)}) : {missing[:10]}")
    if extra:
        print(f"[check] ORPHELIN ({len(extra)}) : {extra[:10]}")
    if missing or extra:
        return 1
    print("[check] catalogue et fichiers concordent.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", default=str(ZIPS_DEFAULT),
                    help="dossier des archives sources")
    ap.add_argument("--out", default=str(OUT_DEFAULT),
                    help="dossier de sortie du catalogue")
    ap.add_argument("--fetch", action="store_true",
                    help="télécharger les archives manquantes depuis kenney.nl")
    ap.add_argument("--check", action="store_true",
                    help="ne rien écrire, vérifier la sortie existante")
    args = ap.parse_args()
    out = pathlib.Path(args.out)

    if args.check:
        return check(out)

    zips = pathlib.Path(args.zips)
    if args.fetch:
        fetch_zips(zips)
    cat = build(zips, out)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"\n[build] {len(cat['particles'])} textures · "
          f"{len(cat['anims'])} animations · {len(cat['sfx'])} sons "
          f"-> {out} ({size / 1024 / 1024:.1f} Mo)")
    return check(out)


if __name__ == "__main__":
    sys.exit(main())
