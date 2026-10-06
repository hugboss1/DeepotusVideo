# -*- coding: utf-8 -*-
"""Découpe en pièces, os, export Spine JSON — t111 (plan-sprites T12, CORRIGÉ le 06/10/2026).

PÉRIMÈTRE FIGÉ : un RIG — pièces, os, slots, skin — et PAS d'animation. Dériver des timelines depuis une feuille
d'images-clés n'est pas ce que demande le balayage (« découpe en pièces, os et export ») et donnerait un fichier qui a
l'air juste et bouge faux. Les tags de la feuille deviennent des animations NOMMÉES et VIDES : le fichier s'ouvre dans
Spine avec les bons noms.

FORMAT : Spine 3.8 JSON (`skeleton.spine = "3.8.99"`). `skins` est un TABLEAU de {name, attachments} — la carte de
cartes est la forme 3.7 (mesuré par le plan le 03/09).

CE QUE LE PLAN AVAIT FAUX (doc relue le 06/10/2026, esotericsoftware.com/spine-json-format) : les x, y, rotation d'un
os sont « relative to the parent », ceux d'une pièce « relative to the slot's bone ». Le plan écrivait chaque os en
coordonnées ABSOLUES de la case, et le décalage d'une pièce sans la rotation de son os : dès qu'un os a un parent
décalé ou tourné (le « cou » du plan, enfant du « torse »), l'os et sa pièce sortaient ailleurs. Ici la page envoie ce
qu'elle voit — positions et angles DANS LA CASE — et ce module compose : repère du parent inversé pour l'os, repère
de l'os inversé pour la pièce, pièce remise droite. Le banc relit le JSON et refait la cinématique directe.

LES DEUX REPÈRES, convertis UNE FOIS, à la porte (`_vers_spine`) : la page parle en pixels de case, origine en haut à
gauche, y vers le BAS ; Spine pose sa racine au coin BAS-GAUCHE et fait REMONTER y. Les angles sont visuels, sens
trigonométrique (90 = vers le haut), comme Spine — la conversion de y ne les retourne donc pas.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path

from PIL import Image

SPINE = "3.8.99"
_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
MAX_OS = 24
MAX_PIECES = 24


def _vers_spine(x: float, y_case: float, hauteur: int) -> tuple[float, float]:
    """Point de la case (y vers le bas) -> point de Spine (y vers le haut, racine au coin bas-gauche). LA conversion
    de repère, et il n'y en a qu'une dans ce module."""
    return x, hauteur - y_case


def _num(bloc: dict, cle: str, defaut, lo, hi, quoi: str) -> float:
    brut = bloc.get(cle, defaut)
    if isinstance(brut, bool):
        raise ValueError(f"{quoi} : {cle} doit être un nombre ({lo}..{hi})")
    try:
        v = float(brut)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} : {cle} doit être un nombre ({lo}..{hi})")
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"{quoi} : {cle}={brut!r} hors de {lo}..{hi}")
    return v


def normaliser(spec: dict, w: int, h: int) -> dict:
    """{bones, pieces} validés, en coordonnées de CASE. ValueError lisible sinon."""
    if not isinstance(spec, dict):
        raise ValueError("rig : un objet {bones, pieces} est attendu")
    os_bruts = spec.get("bones")
    if not isinstance(os_bruts, list) or not os_bruts:
        raise ValueError("rig : au moins un os (bones)")
    if len(os_bruts) > MAX_OS:
        raise ValueError(f"rig : {MAX_OS} os au plus")
    os_, vus = [], {"root"}
    for b in os_bruts:
        if not isinstance(b, dict):
            raise ValueError("rig : chaque os est un objet {name, x, y}")
        nom = str(b.get("name") or "")
        if not _NOM.match(nom):
            raise ValueError(f"os {nom!r} : 1 à 32 caractères, lettres, chiffres, _ ou -")
        if nom in vus:
            raise ValueError(f"os {nom!r} : nom en double (ou « root », réservé à la racine)")
        parent = str(b.get("parent") or "root")
        # LE PARENT PRÉCÈDE : c'est ce qui interdit les cycles sans parcours de graphe, et Spine lit les os dans
        # l'ordre (un parent avant ses enfants)
        if parent not in vus:
            raise ValueError(f"os {nom!r} : parent {parent!r} inconnu ou déclaré après lui")
        vus.add(nom)
        q = f"os {nom!r}"
        os_.append({"name": nom, "parent": parent, "x": _num(b, "x", 0, 0, w, q), "y": _num(b, "y", 0, 0, h, q),
                    "length": _num(b, "length", 0, 0, 4 * max(w, h), q),
                    "rotation": _num(b, "rotation", 0, -360, 360, q)})
    p_bruts = spec.get("pieces")
    if not isinstance(p_bruts, list) or not p_bruts:
        raise ValueError("rig : au moins une pièce (pieces)")
    if len(p_bruts) > MAX_PIECES:
        raise ValueError(f"rig : {MAX_PIECES} pièces au plus")
    pieces, vues = [], set()
    for p in p_bruts:
        if not isinstance(p, dict):
            raise ValueError("rig : chaque pièce est un objet {name, bone, x, y, w, h}")
        nom = str(p.get("name") or "")
        # le nom devient un NOM DE FICHIER (spine/images/<nom>.png) : la regexp n'admet ni / ni .
        if not _NOM.match(nom):
            raise ValueError(f"pièce {nom!r} : 1 à 32 caractères, lettres, chiffres, _ ou - (c'est un nom de fichier)")
        if nom in vues:
            raise ValueError(f"pièce {nom!r} : nom en double")
        vues.add(nom)
        os_nom = str(p.get("bone") or "")
        if os_nom not in vus or os_nom == "root":
            raise ValueError(f"pièce {nom!r} : os {os_nom!r} inconnu")
        q = f"pièce {nom!r}"
        x, y = int(_num(p, "x", 0, 0, w - 1, q)), int(_num(p, "y", 0, 0, h - 1, q))
        pw, ph = int(_num(p, "w", 0, 2, w, q)), int(_num(p, "h", 0, 2, h, q))
        if x + pw > w or y + ph > h:
            raise ValueError(f"pièce {nom!r} : la boîte {x},{y} {pw}×{ph} sort de la case ({w}×{h})")
        pieces.append({"name": nom, "bone": os_nom, "x": x, "y": y, "w": pw, "h": ph})
    return {"bones": os_, "pieces": pieces}


def _local(px, py, prot, x, y):
    """Le point monde (x, y) dans le repère d'un os monde (px, py, prot) : rotation inverse de la différence."""
    a = math.radians(prot)
    dx, dy = x - px, y - py
    return math.cos(a) * dx + math.sin(a) * dy, -math.sin(a) * dx + math.cos(a) * dy


def _angle(r: float) -> float:
    """Un angle ramené dans ]-180, 180]."""
    r = (r + 180.0) % 360.0 - 180.0
    return 180.0 if r == -180.0 else r


def squelette(rig: dict, w: int, h: int, tags: list, fps: float) -> dict:
    """Le skeleton.json (sans le hash). Os et pièces en repères LOCAUX, comme Spine les lit."""
    monde = {"root": (0.0, 0.0, 0.0)}                    # (x, y, rotation) monde de Spine
    os_json = [{"name": "root"}]
    for b in rig["bones"]:
        wx, wy = _vers_spine(b["x"], b["y"], h)
        px, py, pr = monde[b["parent"]]
        lx, ly = _local(px, py, pr, wx, wy)
        monde[b["name"]] = (wx, wy, b["rotation"])
        os_json.append({"name": b["name"], "parent": b["parent"], "x": round(lx, 3), "y": round(ly, 3),
                        "length": round(b["length"], 3), "rotation": round(_angle(b["rotation"] - pr), 3)})
    slots, attachements = [], {}
    for p in rig["pieces"]:
        cx, cy = _vers_spine(p["x"] + p["w"] / 2.0, p["y"] + p["h"] / 2.0, h)
        bx, by, br = monde[p["bone"]]
        lx, ly = _local(bx, by, br, cx, cy)
        slots.append({"name": p["name"], "bone": p["bone"], "attachment": p["name"]})
        # la pièce est DROITE dans la case : son angle local annule celui de son os
        attachements[p["name"]] = {p["name"]: {"x": round(lx, 3), "y": round(ly, 3), "rotation": round(_angle(-br), 3),
                                               "width": p["w"], "height": p["h"]}}
    return {
        "skeleton": {"spine": SPINE, "x": 0, "y": 0, "width": w, "height": h, "images": "./images/", "fps": fps},
        "bones": os_json,
        "slots": slots,
        "skins": [{"name": "default", "attachments": attachements}],       # TABLEAU : la forme 3.8
        "animations": {str(t["name"]): {} for t in (tags or []) if isinstance(t, dict) and t.get("name")},
    }


def ecrire(case: Path, spec: dict, dest: Path, tags: list, fps: float = 8.0) -> dict:
    """Valide le rig contre la case, puis écrit `dest/skeleton.json` et `dest/images/<pièce>.png` — dans un dossier
    NEUF (un rig précédent laisserait des pièces orphelines dans le ZIP). Rend le squelette."""
    with Image.open(case) as brut:
        im = brut.convert("RGBA")
    w, h = im.size
    rig = normaliser(spec, w, h)
    sq = squelette(rig, w, h, tags, fps)
    sq["skeleton"]["hash"] = hashlib.sha1(json.dumps(sq, sort_keys=True).encode("utf-8")).hexdigest()[:11]
    tmp = dest.parent / (dest.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "images").mkdir(parents=True)
    for p in rig["pieces"]:
        im.crop((p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"])).save(tmp / "images" / f"{p['name']}.png", "PNG")
    (tmp / "skeleton.json").write_text(json.dumps(sq, indent=2, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(dest, ignore_errors=True)
    tmp.replace(dest)
    return sq
