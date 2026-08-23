# -*- coding: utf-8 -*-
"""Card Forge — P10 « Import » (id de module `capture`). Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/capture`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

L'id est `capture` et non `import` : `import.py` serait INIMPORTABLE (mot
réservé Python), et la règle 1 du lint exige qu'une pièce porte son id sur ses
quatre fichiers. Le libellé à l'écran, lui, reste « Import ».

CE FICHIER APPARTIENT À P10. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). Ce dont il a besoin vient de
`cards/contract.py` — jamais d'un voisin.

────────────────────────────────────────────────────────────────────────────
CE QUE CETTE PIÈCE TIENT AUJOURD'HUI, ET CE QU'ELLE NE TIENT PAS ENCORE

Aujourd'hui : l'ADMISSION d'une carte existante (une photo, un scan, un PNG
de production) et le SERVICE des fichiers qu'elle range. L'ANALYSE — bordure,
zones occupées, fond, palette, et la confiance CHIFFRÉE de chacune — arrive
juste après (spec §7.1.2) et s'écrira ici, sous ces routes-là.

Ce qui est déjà tranché, et qui ne bougera pas :

  1. L'ADMISSION EST CELLE DE `texture.py:post_paper`, à la lettre — corps
     BRUT, poids pesé sur le fil, dimensions lues dans l'EN-TÊTE avant tout
     décodage, `load()` gardé, RGB, réduction LANCZOS, écriture atomique.
     Ce n'est pas le quintette de la galerie 3b (numérotation O_EXCL) : une
     capture n'est pas une pile ouverte, c'est UN fichier par côté.
  2. RÉ-IMPORT = REMPLACEMENT, sans historique. Une capture est un point de
     départ ; ce qu'on en tire (l'illustration adoptée par P1, la bordure
     mesurée pour P2, les zones pour P3) vit chez les pièces qui l'adoptent.
  3. LE DOCUMENT EST PUBLIÉ PAR L'ÉCRAN, PAS PAR LA ROUTE. Cette route range
     des PNG et REND ses mesures ; c'est `mod-capture.js` qui écrit
     `doc.capture` par la voie d'autosave unique. Une seule main sur le
     document — c'est la règle 12, et elle vaut aussi pour le backend.
  4. TOUT REFUS EST FRANÇAIS ET NOMMÉ (spec §8) : jamais de 500 sur un corps,
     jamais un 422 anglais de validation automatique sur un `?side` mal tapé.

Routes (toutes relatives à /api/cards/{did}/capture) :

    POST /card?side=recto|verso   corps BRUT : la carte à importer
    GET  /{nom}                   un fichier du dossier, par liste blanche
"""
from __future__ import annotations

import asyncio
import io
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from .contract import deck_dir, is_valid_did

# Règle 8 : signature imposée, chemins RELATIFS.
router = APIRouter()

__all__ = ["router", "SIDES", "SRC_MAX_BYTES", "IMG_MAX_PIXELS",
           "MAX_IMPORT_PX", "FILE_RE", "cap_dir", "source_name"]

# ── seuils ──────────────────────────────────────────────────────────────────
# Les deux côtés d'une carte, et il n'y en a pas de troisième. La liste est le
# refus : un `Literal[…]` de FastAPI rendrait un 422 ANGLAIS de validation
# automatique (« value is not a valid enumeration member ») à qui tape
# « front » — pour un utilisateur francophone, une panne sans message.
SIDES = ("recto", "verso")

# Le plafond de POIDS du corps, pesé sur le fil AVANT tout décodage. Même
# chiffre que P6 (`texture.py:SRC_MAX_BYTES`) et P3 (`type.py:IMG_MAX_BYTES`).
SRC_MAX_BYTES = 64 * 1024 * 1024
# Le plafond de TRAME, et ce n'est PAS le même garde-fou. Le poids du corps ne
# dit rien du coût du décodage : un PNG de zéros de quelques centaines de
# kilo-octets déclare 12000 x 12000 sans effort, et ces 144 millions de pixels
# demandent un demi-gigaoctet de tampon — par requête, pendant que la
# bibliothèque se contente d'AVERTIR jusqu'à 179 Mpx avant de décoder quand
# même. Les dimensions se lisent dans l'EN-TÊTE : c'est le seul endroit où ce
# refus coûte zéro.
IMG_MAX_PIXELS = 32 * 1024 * 1024
# Le côté long au-delà duquel une image importée est ré-échelonnée. MÊME
# CHIFFRE que l'illustration de P1 (`cards/face.py:MAX_IMPORT_PX`), RECOPIÉ et
# non importé : la règle 8 interdit à une pièce d'importer le module d'une
# voisine (doctrine `type.py:552`). C'est la SEPTIÈME copie — les six autres
# sont face.py, frame.py, type.py, mod-face.js, mod-frame.js, mod-type.js — et
# le test de la pièce les confronte plutôt que de faire confiance à ce
# commentaire.
MAX_IMPORT_PX = 4096

# LA LISTE BLANCHE DU SERVICE. Un nom de fichier est un IDENTIFIANT, jamais un
# chemin : « ../meta.json » ne peut pas satisfaire ce motif. Il ne décrit QUE
# des noms FINAUX — et c'est le second point, moins évident : `_store_image`
# écrit `source_recto.png.tmp` puis le remplace, et pendant cette fenêtre le
# `.tmp` est une image TRONQUÉE. Un motif qui tolérerait un suffixe la
# servirait comme si c'était la capture.
FILE_RE = re.compile(r"^source_(?:recto|verso)\.png$")


# ── disque ──────────────────────────────────────────────────────────────────

def cap_dir(did: str, create: bool = False) -> Path:
    """`decks/<did>/capture/`. `deck_dir` porte déjà le double garde-fou
    (motif PUIS confinement) : on ne le refait pas, on s'appuie dessus."""
    d = deck_dir(did, create=create) / "capture"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def source_name(side: str) -> str:
    """Le nom du fichier d'un côté. UN SEUL endroit le fabrique, et la liste
    blanche du service décrit exactement ce qu'il produit."""
    return f"source_{side}.png"


def _dir_or_404(did: str, create: bool = False) -> Path:
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    try:
        base = deck_dir(did, create=create)
    except ValueError:
        raise HTTPException(400, "Identifiant de deck invalide")
    if not base.is_dir():
        raise HTTPException(404, "Deck introuvable")
    return cap_dir(did, create=create)


def _side_or_400(side: str | None) -> str:
    """Le côté, validé À LA MAIN. `side` est pris en `str | None` et non en
    `Literal` EXPRÈS : le refus doit être le nôtre, en français, et nommer les
    deux valeurs possibles. `None` (paramètre ABSENT) vaut recto ; `?side=`
    (présent et vide) est une faute, pas un défaut."""
    if side is None:
        return SIDES[0]
    if side not in SIDES:
        vu = side if len(side) <= 40 else side[:40] + "…"
        raise HTTPException(
            400, f"Côté inconnu : « {vu} ». Une carte a deux côtés, et le "
                 f"paramètre ?side ne connaît que ceux-là : "
                 f"{' ou '.join(SIDES)} (par défaut : {SIDES[0]}).")
    return side


def _name_or_404(nom: str) -> str:
    """Liste blanche. Voir `FILE_RE` : ni traversée, ni fichier temporaire."""
    n = str(nom or "")
    if not FILE_RE.match(n):
        raise HTTPException(
            404, "Fichier inconnu dans le dossier de capture : ce dossier ne "
                 "sert que " + " et ".join(source_name(s) for s in SIDES) + ".")
    return n


def _store_image(did: str, name: str, raw: bytes, cap: int | None = None) -> dict:
    """Le patron d'admission de `texture.py:_store_image`, recopié et non
    partagé (règle 8). L'ORDRE des cinq gardes EST la protection : peser,
    lire l'en-tête, refuser, PUIS décoder."""
    from PIL import Image
    d = _dir_or_404(did, create=True)
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    # LE POIDS DU CORPS NE DIT RIEN DU COÛT DU DÉCODAGE — les dimensions se
    # lisent dans l'en-tête, avant qu'une seule ligne soit décodée.
    if w * h > IMG_MAX_PIXELS:
        raise HTTPException(
            413, f"Image trop grande : {w} x {h} pixels, soit "
                 f"{w * h // 1048576} millions de pixels pour un maximum de "
                 f"{IMG_MAX_PIXELS // 1048576}. Réduisez-la avant de l'importer.")
    try:
        img.load()
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    try:
        img = img.convert("RGB")
    except Exception:
        raise HTTPException(400, "Image au mode de couleur inattendu : elle "
                                 "n'a pas pu être ramenée en RVB")
    if cap and max(img.size) > cap:
        k = cap / float(max(img.size))
        img = img.resize((max(1, round(img.size[0] * k)),
                          max(1, round(img.size[1] * k))), Image.LANCZOS)
    # ÉCRITURE ATOMIQUE. Un `save()` sur le nom final laisse une image
    # TRONQUÉE lisible par le GET si l'écriture s'interrompt — et une capture
    # tronquée serait analysée comme si elle était entière.
    tmp = d / (name + ".tmp")
    img.save(tmp, format="PNG", optimize=False)
    tmp.replace(d / name)
    return {"w": img.size[0], "h": img.size[1],
            "bytes": (d / name).stat().st_size, "stamp": int(time.time())}


def _png(data: bytes) -> Response:
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ── routes ──────────────────────────────────────────────────────────────────

@router.post("/card")
async def post_card(did: str, request: Request, side: str | None = None):
    """La carte à reprendre — corps BRUT, un fichier par côté.

    Le côté est validé AVANT que le corps soit lu : refuser une faute de
    frappe après avoir avalé soixante mégaoctets serait une politesse chère.
    """
    s = _side_or_400(side)
    _dir_or_404(did)
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer l'image de la carte à "
                                 "importer")
    if len(raw) > SRC_MAX_BYTES:
        raise HTTPException(400, "Image trop lourde (max 64 Mo)")
    info = await asyncio.to_thread(_store_image, did, source_name(s), raw,
                                   MAX_IMPORT_PX)
    return {"side": s, **info}


@router.get("/{nom}")
async def get_file(did: str, nom: str):
    """Un fichier du dossier de capture, par liste blanche de noms FINAUX."""
    n = _name_or_404(nom)
    d = _dir_or_404(did)
    p = d / n
    if not p.is_file():
        cote = n[len("source_"):-len(".png")]
        raise HTTPException(404, f"Aucune capture {cote} sur ce jeu : déposez "
                                 f"une image dans la pièce Import.")
    return _png(await asyncio.to_thread(p.read_bytes))
