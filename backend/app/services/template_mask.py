# -*- coding: utf-8 -*-
"""Plan-templates T3 (tache #74 du suivi, PR A, 03/10/2026) — MASQUES de region pour les cases video et image.

`mask` sur une region video_slot / image_slot :
    {"shape": "rounded" | "ellipse" | "polygon",
     "radius": px (coins, rounded),            "points": [[fx, fy], ...] (polygon, 3 a 64 points, FRACTIONS 0..1),
     "holes": [{"shape": "rect" | "ellipse", "x", "y", "width", "height" (FRACTIONS 0..1), "radius": px}, ...]  (16 max),
     "feather_px": px (bord adouci, 0 = net),  "border_px": px, "border_color": "#RRGGBB" (liseré qui suit la forme)}
Decisions de l'utilisateur (03/10) : arrondi, ellipse, fenetres ajourees ET polygone ; video et image seulement ;
adoucissement reglable + liseré colore. Les fenetres et les points sont des FRACTIONS de la region : le reagencement
(#73) etire une case axe par axe, des pixels deriveraient ; les epaisseurs (rayon, adoucissement, liseré) sont en px et
suivent l'echelle du reagencement.
Le masque est une image fixe (Pillow, dessinee a 4x puis reduite : bords lisses) fusionnee par `alphamerge` — le
Montage notait (montage_service, D-19) que `geq` coute ~x29 et que le masque statique etait la voie a prendre.
Sans `mask`, le graphe ffmpeg ne change pas d'un octet.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

FORMES = ("rounded", "ellipse", "polygon")
FORMES_TROU = ("rect", "ellipse")
TYPES = ("video_slot", "image_slot")
MAX_TROUS, MAX_POINTS = 16, 64
SUR = 4                                    # sur-echantillonnage du dessin (anticrenelage)
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_NOM = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _nombre(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _frac(v) -> bool:
    return _nombre(v) and 0 <= v <= 1


def verifier_masques(regions) -> None:
    """ValueError qui nomme la region et le champ fautifs (appele par TemplateEngine._validate)."""
    for r in regions or []:
        m = r.get("mask")
        if m is None:
            continue
        rid = r.get("id")
        if r.get("type") not in TYPES:
            raise ValueError(f"Region {rid} : un masque ne s'applique qu'aux cases vidéo et image (pas {r.get('type')}).")
        if not isinstance(m, dict):
            raise ValueError(f"Region {rid} : « mask » doit être un objet.")
        forme = m.get("shape", "rounded")
        if forme not in FORMES:
            raise ValueError(f"Region {rid} : forme de masque {forme!r} inconnue — {', '.join(FORMES)}.")
        for ch, hi in (("radius", 5000), ("feather_px", 200), ("border_px", 200)):
            if ch in m and not (_nombre(m[ch]) and 0 <= m[ch] <= hi):
                raise ValueError(f"Region {rid} : mask.{ch} doit être un nombre entre 0 et {hi}.")
        if "border_color" in m and not (isinstance(m["border_color"], str) and _COULEUR.match(m["border_color"])):
            raise ValueError(f"Region {rid} : mask.border_color doit être #RRGGBB.")
        if forme == "polygon":
            pts = m.get("points")
            if not isinstance(pts, list) or not 3 <= len(pts) <= MAX_POINTS or not all(
                    isinstance(p, (list, tuple)) and len(p) == 2 and _frac(p[0]) and _frac(p[1]) for p in pts):
                raise ValueError(f"Region {rid} : un polygone demande 3 à {MAX_POINTS} points [x, y] en fractions 0..1.")
        trous = m.get("holes", [])
        if not isinstance(trous, list) or len(trous) > MAX_TROUS:
            raise ValueError(f"Region {rid} : mask.holes doit être une liste de {MAX_TROUS} fenêtres au plus.")
        for i, t in enumerate(trous):
            if not isinstance(t, dict) or t.get("shape", "rect") not in FORMES_TROU or not all(
                    _frac(t.get(k)) for k in ("x", "y", "width", "height")) or (t.get("width") or 0) <= 0 or (t.get("height") or 0) <= 0:
                raise ValueError(f"Region {rid} : fenêtre {i + 1} invalide — shape rect|ellipse, x, y, width, height en fractions 0..1.")
            if "radius" in t and not (_nombre(t["radius"]) and t["radius"] >= 0):
                raise ValueError(f"Region {rid} : fenêtre {i + 1}, radius doit être un nombre positif.")


def _boite(t, w, h):
    return (t["x"] * w, t["y"] * h, (t["x"] + t["width"]) * w, (t["y"] + t["height"]) * h)


def _dessiner_forme(d, m, w, h, k, **style):
    """La forme du masque sur un dessin a l'echelle k (anticrenelage) ; `style` = fill / outline+width."""
    forme = m.get("shape", "rounded")
    if forme == "ellipse":
        d.ellipse((0, 0, w * k - 1, h * k - 1), **style)
    elif forme == "polygon":
        d.polygon([(fx * (w * k - 1), fy * (h * k - 1)) for fx, fy in m["points"]], **style)
    else:
        rad = max(0, min(float(m.get("radius", 0)), min(w, h) / 2)) * k
        d.rounded_rectangle((0, 0, w * k - 1, h * k - 1), radius=rad, **style)


def _dessiner_trou(d, t, w, h, k, **style):
    x0, y0, x1, y1 = (v * k for v in _boite(t, w, h))
    if t.get("shape", "rect") == "ellipse":
        d.ellipse((x0, y0, x1 - 1, y1 - 1), **style)
    else:
        rad = max(0, min(float(t.get("radius", 0)), (x1 - x0) / k / 2, (y1 - y0) / k / 2)) * k
        d.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=rad, **style)


def dessiner_masque(m: dict, w: int, h: int):
    """Image L (w x h) : 255 dans la forme, 0 dehors et dans les fenetres ; bord adouci de feather_px."""
    from PIL import Image, ImageDraw, ImageFilter
    k = SUR
    im = Image.new("L", (w * k, h * k), 0)
    d = ImageDraw.Draw(im)
    _dessiner_forme(d, m, w, h, k, fill=255)
    for t in m.get("holes") or []:
        _dessiner_trou(d, t, w, h, k, fill=0)
    im = im.resize((w, h), Image.LANCZOS)
    f = float(m.get("feather_px", 0) or 0)
    if f > 0:
        # Le flou part d'une MARGE VIDE autour de la forme : flouter l'image seule ne change rien sur une forme qui
        # touche les bords (le filtre prolonge le bord) — trouve par le banc-miroir.
        p = int(f) + 2
        pad = Image.new("L", (w + 2 * p, h + 2 * p), 0)
        pad.paste(im, (p, p))
        im = pad.filter(ImageFilter.GaussianBlur(f / 2)).crop((p, p, p + w, p + h))
    return im


def dessiner_cadre(m: dict, w: int, h: int):
    """Image RGBA (w x h) du liseré qui suit la forme ET les fenetres ; None sans liseré."""
    bp = float(m.get("border_px", 0) or 0)
    if bp <= 0:
        return None
    from PIL import Image, ImageDraw, ImageColor
    k = SUR
    coul = ImageColor.getrgb(m.get("border_color") or "#ffffff") + (255,)
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ep = max(1, round(bp * k))
    _dessiner_forme(d, m, w, h, k, outline=coul, width=ep)
    for t in m.get("holes") or []:
        _dessiner_trou(d, t, w, h, k, outline=coul, width=ep)
    return im.resize((w, h), Image.LANCZOS)


def ecrire(r: dict, w: int, h: int, work: Path) -> tuple:
    """(chemin du masque, chemin du liseré ou None) dans le dossier de travail du rendu. Le nom de fichier ne reprend
    l'id de region que s'il est sur ; sinon une empreinte (un id de region n'est pas filtre par la validation)."""
    rid = str(r.get("id") or "")
    nom = rid if _NOM.match(rid) else "r" + hashlib.sha1(rid.encode("utf-8")).hexdigest()[:10]
    work.mkdir(parents=True, exist_ok=True)
    m = r["mask"]
    mp = work / f"mask_{nom}.png"
    dessiner_masque(m, w, h).save(mp)
    cadre = dessiner_cadre(m, w, h)
    fp = None
    if cadre is not None:
        fp = work / f"frame_{nom}.png"
        cadre.save(fp)
    return mp, fp
