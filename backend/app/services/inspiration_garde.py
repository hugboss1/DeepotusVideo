# -*- coding: utf-8 -*-
"""t313 (28/10/2026) (C3 Inspiration, tâche 1) — les GARDES ANTI-COPIE d'un contenu neuf tiré d'une inspiration.

Spec boîte à outils §7.4 point 5 (décision de l'utilisateur : refabriquer, jamais republier) :
- texte : un brouillon dont une suite de `SEUIL_SUITE` mots consécutifs (ou plus) reprend la capture est refusé ; la
  comparaison se fait sur des mots NORMALISÉS (casse, accents, ponctuation, apostrophes et retours à la ligne neutres),
  pour qu'un déguisement typographique ne passe pas. La spec dit « plus de 12 mots » ; la fiche du suivi dit « 12 mots
  consécutifs » : on lit le plus prudent, refus dès 12 (choix noté au registre du lot).
- proximité : la part (0-100) des trigrammes de mots du texte jugé qui figurent dans la capture ; affichée, jamais
  bloquante à elle seule ;
- image : l'image captée n'est jamais le visuel du post. `empreinte` = sha256 des octets + empreinte moyenne 8×8
  (« aHash ») ; `meme_image` reconnaît la même image recompressée ou redimensionnée (≤ `SEUIL_AHASH` bits d'écart).
Module PUR (Pillow pour les images) : aucun fichier, aucun réseau, aucun journal.
"""
from __future__ import annotations

import hashlib
import io
import re
import unicodedata

SEUIL_SUITE = 12
SEUIL_AHASH = 6
_INVISIBLES = "\u00ad\u180e\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff"
_MOT = re.compile(r"[^\W_]+(?:[" + _INVISIBLES + r"]+[^\W_]+)*", re.UNICODE)   # revue t313 : « mai\u00adson » = un mot
_RETIRER = {ord(c): None for c in _INVISIBLES}


def _norme(mot: str) -> str:
    t = unicodedata.normalize("NFKD", mot.translate(_RETIRER).casefold())
    return "".join(c for c in t if not unicodedata.combining(c))


def _jetons(texte) -> list[tuple[str, int, int]]:
    """[(mot normalisé, début, fin)] dans le texte d'origine."""
    return [(_norme(m.group(0)), m.start(), m.end()) for m in _MOT.finditer(str(texte or ""))]


def mots(texte) -> list[str]:
    """Les mots normalisés d'un texte (casse, accents et ponctuation retirés)."""
    return [j[0] for j in _jetons(texte)]


def plus_longue_suite(capte, texte) -> tuple[int, str]:
    """(n, extrait) : la plus longue suite de mots consécutifs du `texte` qui figure telle quelle dans `capte` ;
    `extrait` = ce passage tel qu'il est écrit dans le texte jugé (blancs réduits)."""
    a = mots(capte)
    b = _jetons(texte)
    if not a or not b:
        return 0, ""
    pos: dict[str, list[int]] = {}
    for j, w in enumerate(a):
        pos.setdefault(w, []).append(j)
    prec: dict[int, int] = {}
    meilleur, fin = 0, -1
    for i, (w, _d, _f) in enumerate(b):
        cour: dict[int, int] = {}
        for j in pos.get(w, ()):
            n = prec.get(j - 1, 0) + 1
            cour[j] = n
            if n > meilleur:
                meilleur, fin = n, i
        prec = cour
    if not meilleur:
        return 0, ""
    t = str(texte or "")
    extrait = t[b[fin - meilleur + 1][1]:b[fin][2]]
    return meilleur, " ".join(extrait.split())


def _ngrammes(liste: list[str], n: int) -> list[tuple]:
    return [tuple(liste[i:i + n]) for i in range(len(liste) - n + 1)]


def proximite(capte, texte) -> int:
    """La part (0-100) des trigrammes de mots du texte présents dans la capture (unigrammes sous trois mots)."""
    a, b = mots(capte), mots(texte)
    if not a or not b:
        return 0
    n = 3 if len(b) >= 3 and len(a) >= 3 else 1
    jb = _ngrammes(b, n)
    ja = set(_ngrammes(a, n))
    return round(100 * sum(1 for g in jb if g in ja) / len(jb)) if jb else 0


def juger(capte, texte) -> dict:
    """{suite, proximite, extrait, ok} ; ok = suite < SEUIL_SUITE."""
    n, extrait = plus_longue_suite(capte, texte)
    return {"suite": n, "proximite": proximite(capte, texte), "extrait": extrait[:300], "ok": n < SEUIL_SUITE}


def empreinte(octets: bytes) -> dict:
    """{sha256, ahash} d'une image ; ValueError si elle est illisible."""
    from PIL import Image, ImageOps
    o = bytes(octets or b"")
    try:
        with Image.open(io.BytesIO(o)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                fond = Image.new("RGB", im.size, (255, 255, 255))
                fond.paste(im, mask=im.getchannel("A"))
                im = fond
            g = im.convert("L").resize((8, 8), Image.BOX)
            px = list(g.getdata())
    except Exception:  # noqa: BLE001
        raise ValueError("Image illisible.") from None
    moy = sum(px) / len(px)
    bits = "".join("1" if p > moy else "0" for p in px)
    return {"sha256": hashlib.sha256(o).hexdigest(), "ahash": f"{int(bits, 2):016x}"}


def meme_image(a, b) -> bool:
    """Deux empreintes désignent-elles la même image (octets identiques, ou ≤ SEUIL_AHASH bits d'écart) ?"""
    a, b = a if isinstance(a, dict) else {}, b if isinstance(b, dict) else {}
    if a.get("sha256") and a.get("sha256") == b.get("sha256"):
        return True
    try:
        x, y = int(str(a.get("ahash")), 16), int(str(b.get("ahash")), 16)
    except (TypeError, ValueError):
        return False
    return bin(x ^ y).count("1") <= SEUIL_AHASH
