# -*- coding: utf-8 -*-
"""Card Forge — P7, sidecar « gabarits » (tâche #83, plan-cartes T2, 04/10/2026) :
le PAQUET qu'on envoie à l'imprimeur.

SIDECAR, pas une pièce : aucun `router` ici (règle 8 — la route vit dans
print.py, qui seul déclare `router = APIRouter()` pour le sous-préfixe
/api/cards/{did}/print). Ce fichier ne fait que des octets.

MPC et The Game Crafter apparient recto et verso PAR LE NOM DE FICHIER. Le nom
est donc un livrable, pas un détail : numéro zéro-comblé sur la largeur du deck,
côté en DERNIER segment, un seul séparateur.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
import zipfile

from .contract import CardGeom, printer_profile

__all__ = ["pack_name", "deck_slug", "build_pack", "SIDE_WORDS"]

SIDE_WORDS = {"front": "recto", "back": "verso"}

# Un nom de fichier qui survit à Windows, à un ZIP et à un portail web : ASCII,
# tiret comme unique séparateur, jamais deux de suite.
_SLUG_BAD = re.compile(r"[^A-Za-z0-9]+")


def deck_slug(name: str) -> str:
    """Le nom du jeu, réduit à ce qu'un portail accepte. Jamais vide."""
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    s = _SLUG_BAD.sub("-", s).strip("-").lower()
    return s[:48].strip("-") or "jeu"


def pack_name(profile: str, slug: str, i: int, side: str, n: int, ext: str) -> str:
    """`<profil>/<jeu>_<NN>_<recto|verso>.<ext>`.

    LE ZÉRO-COMBLEMENT SUIT LA TAILLE DU DECK, pas un 2 en dur : un jeu de 120
    cartes trié par nom mettrait « 100 » avant « 2 » et l'imprimeur imprimerait
    la mauvaise carte. Largeur minimale 2, pour que 9 cartes donnent 01..09.
    """
    largeur = max(2, len(str(max(1, int(n)))))
    mot = SIDE_WORDS.get(side, side)
    return "%s/%s_%0*d_%s.%s" % (profile, slug, largeur, i + 1, mot, ext)


def build_pack(profile: str, slug: str, g: CardGeom,
               faces: dict[str, dict[int, bytes]], ext: str) -> bytes:
    """Le ZIP. `faces` = {"front": {i: octets}, "back": {i: octets}} — les
    octets sont DÉJÀ encodés par `print.encode_image` : ce fichier ne réencode
    rien, il nomme, condense et archive.

    Le manifeste dit ce que le paquet CONTIENT (toile, fond perdu, condensat
    par fichier), pas ce qu'on a demandé : c'est lui qu'on relit au banc.
    """
    pr = printer_profile(profile)
    n = max([len(v) for v in faces.values()] + [1])
    entrees, index = [], []
    for side in ("front", "back"):
        for i in sorted(faces.get(side) or {}):
            data = faces[side][i]
            nom = pack_name(profile, slug, i, side, n, ext)
            entrees.append((nom, data))
            index.append({
                "nom": nom.split("/", 1)[1], "carte": i + 1,
                "side": SIDE_WORDS[side], "octets": len(data),
                "px": list(g.canvas_px),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
    manifeste = {
        "profil": profile, "label": pr["label"], "url": pr["url"],
        "livraison": pr["delivery"], "note": pr["note"], "verifie": pr["verifie"],
        "jeu": slug, "fmt": g.fmt, "dpi": g.dpi,
        "canvas_px": list(g.canvas_px), "trim_px": list(g.trim_px),
        "bleed_off_px": list(g.bleed_off_px),
        "safe_px": list(g.safe_px), "safe_off_px": list(g.safe_off_px),
        "bleed_mm": g.bleed_mm, "safe_mm": g.safe_mm,
        "cartes": n, "fichiers": index,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # Le manifeste EN PREMIER : un humain qui ouvre l'archive le voit.
        z.writestr(f"{profile}/manifeste.json", json.dumps(manifeste, ensure_ascii=False, indent=1))
        for nom, data in entrees:
            # STORED : un PNG est déjà compressé, le redéflater coûte du temps et ne gagne rien.
            z.writestr(zipfile.ZipInfo(nom, date_time=(2026, 1, 1, 0, 0, 0)), data,
                       compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()
