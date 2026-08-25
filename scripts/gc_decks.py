# -*- coding: utf-8 -*-
"""Le GC des jeux de banc (Cardforge, phase 6 T5) — il RANGE, il ne supprime
jamais.

Les rondes de preuve des phases 1-5 jouaient contre le backend DÉPLOYÉ :
chaque preuve posait son deck « Nouveau jeu » dans le magasin réel. Mesuré le
25/08 : 2 110 jeux de banc sur 2 206, 6,1 Go. Cet outil les déplace dans un
rebut daté `rebut_decks_<AAAA-MM-JJ>/` au patron du rebut de série — la
SUPPRESSION DÉFINITIVE appartient à l'utilisateur, pas à un script.

LA CEINTURE EST DOUBLE :
  1. le NOM, exactement « Nouveau jeu » (l'utilisateur nomme ce qu'il garde —
     les 96 jeux gardés de l'inventaire portent TOUS un nom) ; un méta
     illisible ou un dossier hors forme `deck_[0-9a-f]{8}` est GARDÉ ;
  2. ZÉRO référence externe : l'identifiant est cherché dans les octets de
     toute base `.db` et de tout `.json` du dossier de données, HORS le
     magasin de jeux lui-même et les rebuts précédents (un id cité par un
     graphe Studio, un post programmé ou un manifeste n'est pas un banc
     oublié — et un rebut d'hier ne vaccine pas le GC d'aujourd'hui).

Usage :
    python scripts/gc_decks.py                 # dry-run : le rapport, rien d'écrit
    python scripts/gc_decks.py --deplacer      # range les candidats au rebut daté
    python scripts/gc_decks.py --racine <dir>  # autre dossier de données
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path

DID_RE = re.compile(r"deck_[0-9a-f]{8}\Z")
ID_DANS_TEXTE = re.compile(r"deck_[0-9a-f]{8}")
NOM_DE_BANC = "Nouveau jeu"


def _racine_defaut() -> Path:
    env = os.environ.get("DEEPOTUS_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "DeepotusVideoGenData"
    return Path.home() / ".deepotus-video-gen"


def _references(racine: Path, decks: Path) -> dict:
    """{deck_id: fichier-qui-le-cite} pour tout id cité HORS du magasin de
    jeux et des rebuts. Une seule passe par blob : on relève les ids
    présents, pas l'inverse (2 110 recherches × N fichiers seraient le même
    travail en quadratique)."""
    refs: dict = {}
    for p in sorted(racine.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".json", ".db"):
            continue
        rel = p.relative_to(racine)
        if decks in p.parents:
            continue
        if any(part.startswith("rebut_") for part in rel.parts):
            continue
        try:
            texte = p.read_bytes().decode("utf-8", errors="replace")
        except OSError:                                   # pragma: no cover
            continue
        for m in ID_DANS_TEXTE.finditer(texte):
            refs.setdefault(m.group(0), str(rel))
    return refs


def gc(racine: Path, deplacer: bool = False, date: str | None = None) -> dict:
    """Le rapport — et, sur `deplacer=True` seulement, le rangement.

    Rend {total, candidats, deplaces, gardes:[{id, raison[, ou]}],
    octets_deplaces, rebut}. `date` ne sert qu'au NOM du rebut ; les tests la
    fixent pour rester rejouables."""
    racine = Path(racine)
    decks = racine / "assets" / "outputs" / "decks"
    date = date or time.strftime("%Y-%m-%d")
    rap = {"total": 0, "candidats": [], "deplaces": [], "gardes": [],
           "octets_deplaces": 0, "rebut": None}
    if not decks.is_dir():
        return rap
    refs = _references(racine, decks)
    for d in sorted(decks.iterdir()):
        if not d.is_dir():
            continue
        rap["total"] += 1
        if not DID_RE.fullmatch(d.name):
            rap["gardes"].append({"id": d.name, "raison": "hors_forme"})
            continue
        meta = d / "meta.json"
        try:
            nom = json.loads(meta.read_text(encoding="utf-8")).get("name")
        except (OSError, ValueError):
            rap["gardes"].append({"id": d.name, "raison": "meta_illisible"})
            continue
        if nom != NOM_DE_BANC:
            rap["gardes"].append({"id": d.name, "raison": "nomme"})
            continue
        if d.name in refs:
            rap["gardes"].append({"id": d.name, "raison": "reference",
                                  "ou": refs[d.name]})
            continue
        rap["candidats"].append(d.name)
    if not deplacer or not rap["candidats"]:
        return rap
    rebut = racine / ("rebut_decks_" + date)
    rebut.mkdir(parents=True, exist_ok=True)
    for did in rap["candidats"]:
        src = decks / did
        octets = sum(p.stat().st_size for p in src.rglob("*") if p.is_file())
        shutil.move(str(src), str(rebut / did))
        rap["deplaces"].append(did)
        rap["octets_deplaces"] += octets
    rap["rebut"] = str(rebut)
    n = len(rap["deplaces"])
    mo = rap["octets_deplaces"] / (1024 * 1024)
    (rebut / "_POURQUOI.txt").write_text(
        (f"Jeux de banc ranges par scripts/gc_decks.py le {date}.\n"
         f"{n} jeu{'x' if n > 1 else ''} nomme{'s' if n > 1 else ''} "
         f"exactement « {NOM_DE_BANC} », {mo:.1f} Mo, ZERO "
         f"reference externe (base .db et .json du dossier de donnees "
         f"balayes, magasin de jeux et rebuts exclus).\n"
         f"Rien n'a ete supprime : la suppression definitive appartient a "
         f"l'utilisateur.\n"),
        encoding="utf-8")
    return rap


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--racine", default=None,
                    help="dossier de donnees (defaut : celui de l'application)")
    ap.add_argument("--deplacer", action="store_true",
                    help="range les candidats au rebut date (sinon : dry-run)")
    a = ap.parse_args(argv)
    racine = Path(a.racine) if a.racine else _racine_defaut()
    rap = gc(racine, deplacer=a.deplacer)
    mode = "RANGEMENT" if a.deplacer else "DRY-RUN (rien d'ecrit)"
    print(f"gc_decks — {mode} — racine : {racine}")
    print(f"  jeux vus       : {rap['total']}")
    print(f"  candidats      : {len(rap['candidats'])}")
    raisons: dict = {}
    for g in rap["gardes"]:
        raisons[g["raison"]] = raisons.get(g["raison"], 0) + 1
    for r, n in sorted(raisons.items()):
        print(f"  gardes ({r}) : {n}")
    if a.deplacer:
        print(f"  ranges         : {len(rap['deplaces'])} "
              f"({rap['octets_deplaces'] / (1024 * 1024):.1f} Mo) "
              f"-> {rap['rebut']}")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
