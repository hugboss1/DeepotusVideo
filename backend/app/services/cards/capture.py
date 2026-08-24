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
de production), le SERVICE des fichiers qu'elle range, l'ANALYSE LOCALE —
bordure, zones occupées, fond, palette, et la confiance CHIFFRÉE de chacune
(spec §7.1.2) — et le DÉTOURAGE IA OPT-IN qui produit la couche « sujet »
(spec §7.1.3) et, depuis T5, la PUBLICATION DES COUCHES IMPORTÉES au format
de manifeste de P9 (spec §7.1.6, plan D7) — une carte importée peut partir
en 3D sans être reconstruite. Les ADOPTIONS, elles, ne seront jamais ici :
elles vivent chez la pièce qui adopte (plan D6), et cette pièce-ci ne touche
jamais l'état d'une voisine — elle publie, on vient se servir.

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
  5. L'ANALYSE EST GRATUITE, LOCALE, ET REJOUABLE. Elle court sur le recto
     STOCKÉ (pas sur un corps de requête) : « Analyser » est un geste à part,
     l'admission ne calcule rien. Aucun appel réseau, aucun fournisseur, PIL
     pur — c'est ce qui permet de la relancer sans y penser.
  6. CHAQUE DÉTECTION PUBLIE SA CONFIANCE MESURÉE, et une détection qui n'a
     rien trouvé est ABSENTE du résultat au lieu de rendre un zéro rassurant.
     Un chiffre de confiance qui ne peut pas être bas est un chiffre qui ment
     (leçon de clôture T1) : chaque confiance de ce fichier a un cas connu où
     elle s'effondre, et le test de la pièce le joue.

  7. LE PAYANT EST OPT-IN, ET SON PRIX VIENT DE LA TABLE. Rien ici n'appelle
     un fournisseur sans qu'on l'ait demandé ; `GET /ai-options` dit AVANT le
     clic ce qui est disponible et ce que ça coûte, en lisant
     `pricing.py` — jamais une copie (§8 :583). Une voie absente n'est pas
     une erreur : la réponse le DIT et l'écran ne propose rien.

Routes (toutes relatives à /api/cards/{did}/capture) :

    POST /card?side=recto|verso   corps BRUT : la carte à importer
    GET  /file/{nom}              un fichier du dossier, par liste blanche
    POST /analyse                 mesure le recto STOCKÉ, rend le relevé
    GET  /ai-options              les voies de détourage, et leur prix
    POST /rembg                   détoure le recto -> la couche « sujet »
    POST /manifeste?card=N        publie les couches importées pour P9
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import re
import struct
import sys
import time
import uuid
import zlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from .contract import deck_dir, is_valid_did, rnd

# Règle 8 : signature imposée, chemins RELATIFS.
router = APIRouter()

__all__ = ["router", "SIDES", "SRC_MAX_BYTES", "IMG_MAX_PIXELS",
           "MAX_IMPORT_PX", "FILE_RE", "cap_dir", "source_name",
           "analyse_recto", "BORD_FRONT_MIN", "BORD_MIN_BORDS",
           "ZONE_BLOC_MM", "ZONE_SOUS", "ZONE_SPAN_MIN", "FOND_SEUIL_UNI",
           "PALETTE_N", "OPTION_IA", "SUJET_NAME", "PRIX_CLE",
           "REMBG_FAL_MODELE", "PREFIXE_FAL", "PREFIXE_LOCAL", "ai_options",
           "COUCHE_COUV_MAX", "FAL_TIMEOUT_S",
           "P9_DIR", "CAPTURE_SIDE", "ROLE_RECTO", "ROLE_SUJET",
           "MANIFEST_SCHEMA", "_ppm", "_card_label"]

# ── seuils ──────────────────────────────────────────────────────────────────
# Les deux côtés d'une carte, et il n'y en a pas de troisième. La liste est le
# refus : un `Literal[…]` de FastAPI rendrait un 422 ANGLAIS de validation
# automatique (« value is not a valid enumeration member ») à qui tape
# « front » — pour un utilisateur francophone, une panne sans message.
SIDES = ("recto", "verso")

# Le plafond de POIDS du corps. Même chiffre que P6
# (`texture.py:SRC_MAX_BYTES`) et P3 (`type.py:IMG_MAX_BYTES`).
# CE QU'IL PROTÈGE, ET CE QU'IL NE PROTÈGE PAS — il est pesé avant tout
# DÉCODAGE, jamais avant la RÉCEPTION : `await request.body()` a déjà tout
# ramassé en mémoire quand on le lit. Un corps de 300 Mo est donc bien refusé,
# mais après avoir été bufferisé. Le vrai garde-fou de réception est en amont
# (le serveur), pas ici ; l'écrire autrement demanderait de consommer le flux
# par morceaux — un chantier de pièce, pas de coquille. Dit plutôt que corrigé.
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
# voisine (doctrine `type.py:552`). C'est la SEPTIÈME copie côté Python et la
# HUITIÈME du lab — les sept autres sont face.py, frame.py, type.py,
# mod-face.js, mod-frame.js, mod-type.js et mod-capture.js — et le test de la
# pièce les confronte TOUTES LES HUIT, lues sur les fichiers, plutôt que de
# faire confiance à ce commentaire (il a déjà menti d'un cran : la ronde a
# trouvé le plafond écrit EN TOUTES LETTRES dans deux phrases d'écran de
# mod-capture.js, donc une copie que rien ne confrontait). Le même test
# refuse désormais tout nombre nu : ici, le chiffre ne s'écrit qu'une fois.
MAX_IMPORT_PX = 4096

# LA LISTE BLANCHE DU SERVICE. Un nom de fichier est un IDENTIFIANT, jamais un
# chemin : « ../meta.json » ne peut pas satisfaire ce motif. Il ne décrit QUE
# des noms FINAUX — et c'est le second point, moins évident : `_store_image`
# écrit un `.tmp` puis le remplace, et pendant cette fenêtre le `.tmp` est une
# image TRONQUÉE. Un motif qui tolérerait un suffixe la servirait comme si
# c'était la capture.
#
# `\Z` ET `fullmatch`, PAS `$` ET `match` — et c'est la QUATRIÈME fois que ce
# chantier paie cette leçon : en Python `$` apparie AUSSI juste avant un saut
# de ligne final, si bien que « source_recto.png\n » (un nom qui arrive tel
# quel d'une URL percent-encodée `%0A`) passait la liste blanche. `\Z` ne
# connaît que la fin de la chaîne ; `fullmatch` refuse en plus tout reste à
# droite. Les deux ensemble : la ceinture et les bretelles d'un contrôle qui
# décide d'un accès au disque.
#
# T3 L'ÉTEND D'UN NOM, PAS D'UN MOTIF. `sujet_recto.png` est la couche
# produite par le détourage IA — un troisième nom FINI, écrit en toutes
# lettres. Un motif du genre `(?:source|sujet)_\w+\.png` aurait ouvert la
# porte à `sujet_verso.png` et à tout ce que T5 rangera là : une liste
# blanche qui devine n'est plus une liste blanche.
SUJET_NAME = "sujet_recto.png"
FILE_RE = re.compile(r"(?:source_(?:recto|verso)|sujet_recto)\.png\Z")


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


def _mpx(n: int) -> str:
    """Des millions de pixels DÉCIMAUX (10^6), écrits à la française.

    `n // 1048576` annonçait « 137 millions » pour 144 000 000 pixels : un
    mébipixel affiché sous le nom d'un million. Le chiffre ne se retrouvait
    nulle part — pas même dans le commentaire de `IMG_MAX_PIXELS`, vingt
    lignes plus haut, qui dit 144. C'est la leçon Mo/Mio de P8, au même
    endroit du même piège (CEI 80000-13)."""
    v = n / 1_000_000
    s = f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"
    return s.replace(".", ",")


def _servis() -> tuple:
    """Les noms que le dossier sert, dans l'ordre où on les explique. Une
    seule source pour le message de refus ET pour le libellé d'un fichier
    absent : deux listes finissent par diverger."""
    return tuple(source_name(s) for s in SIDES) + (SUJET_NAME,)


def _quoi(nom: str) -> str:
    """Ce qu'un nom de la liste blanche DÉSIGNE, en français.

    Le calcul d'avant était `n[len("source_"):-len(".png")]` — une découpe
    par longueur, juste pour les deux noms qu'elle connaissait et fausse dès
    le troisième : « sujet_recto.png » y rendait « cto ». Une table dit ce
    qu'elle sait et ne calcule rien."""
    if nom == SUJET_NAME:
        return "couche « sujet » du recto"
    for s in SIDES:
        if nom == source_name(s):
            return f"capture {s}"
    return "fichier"                       # inatteignable : la liste blanche


def _name_or_404(nom: str) -> str:
    """Liste blanche. Voir `FILE_RE` : ni traversée, ni fichier temporaire."""
    n = str(nom or "")
    if not FILE_RE.fullmatch(n):
        raise HTTPException(
            404, "Fichier inconnu dans le dossier de capture : ce dossier ne "
                 "sert que " + ", ".join(_servis()) + ".")
    return n


# Le remplacement final, et sa patience. Mesuré sur 40 envois simultanés du
# même côté : le brouillon unique supprime la collision d'ÉCRITURE, mais deux
# `replace` visant la MÊME destination se refusent encore l'un l'autre sur
# Windows (MoveFileEx, partage) — 7 refus sur 40. Une seconde tentative après
# un souffle suffit à les absorber : le conflit dure le temps d'un appel
# système, pas d'une requête. Le plafond est court EXPRÈS (5 x 20 ms = 100 ms
# au pire) : au-delà, ce n'est plus une course, c'est un vrai problème de
# disque, et il doit se dire au lieu de s'attendre.
REPLACE_ESSAIS = 5
REPLACE_PAUSE_S = 0.02


def _replace_avec_patience(tmp: Path, final: Path) -> None:
    for reste in range(REPLACE_ESSAIS - 1, -1, -1):
        try:
            tmp.replace(final)
            return
        except OSError:
            if not reste:
                raise
            time.sleep(REPLACE_PAUSE_S)


def _store_image(did: str, name: str, raw: bytes, cap: int | None = None) -> dict:
    """Le patron d'admission de `texture.py:_store_image`, recopié et non
    partagé (règle 8). L'ORDRE des cinq gardes EST la protection : peser,
    lire l'en-tête, refuser, PUIS décoder."""
    from PIL import Image
    d = _dir_or_404(did, create=True)
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
    except Image.DecompressionBombError as e:
        # AU-DELÀ DE 2 x `MAX_IMAGE_PIXELS` (soit ~179 Mpx), la bibliothèque
        # refuse D'OUVRIR — elle lève avant même de rendre la taille. Attrapé
        # par le `except Exception` d'à côté, ce refus-là ressortait en
        # « Corps illisible » : mesuré sur 20000² et 60000², un 400 « ce n'est
        # pas une image » pour une image parfaitement valide et simplement
        # énorme. Le motif du refus doit être le VRAI motif — 413, trop
        # grande — sinon l'utilisateur cherche un fichier corrompu qui n'existe
        # pas. Le compte de pixels se relit dans le message de la bibliothèque.
        vu = re.search(r"(\d+)", str(e))
        combien = (f"{_mpx(int(vu.group(1)))} millions de pixels"
                   if vu else "une trame démesurée")
        raise HTTPException(
            413, f"Image trop grande : {combien}, pour un maximum de "
                 f"{_mpx(IMG_MAX_PIXELS)} millions. La bibliothèque a refusé "
                 f"de l'ouvrir. Réduisez-la avant de l'importer.")
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    # LE POIDS DU CORPS NE DIT RIEN DU COÛT DU DÉCODAGE — les dimensions se
    # lisent dans l'en-tête, avant qu'une seule ligne soit décodée.
    if w * h > IMG_MAX_PIXELS:
        raise HTTPException(
            413, f"Image trop grande : {w} x {h} pixels, soit "
                 f"{_mpx(w * h)} millions de pixels pour un maximum de "
                 f"{_mpx(IMG_MAX_PIXELS)} millions. Réduisez-la avant de "
                 f"l'importer.")
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
    # ÉCRITURE ATOMIQUE, ET LE TEMPORAIRE EST NOMINATIF. Un `save()` sur le
    # nom final laisse une image TRONQUÉE lisible par le GET si l'écriture
    # s'interrompt. Mais un tmp CONSTANT (`source_recto.png.tmp`) rejouait le
    # même défaut d'un cran plus loin : deux envois simultanés sur le même
    # côté écrivaient dans LE MÊME fichier et se disputaient le `replace`.
    # Mesuré en concurrence réelle, 40 requêtes : 4 réponses 500 (WinError 32,
    # « le processus ne peut pas accéder au fichier »), soit 10 %. Deux
    # onglets, ou un double-clic, suffisaient. Le suffixe unique donne à
    # chaque requête SON brouillon ; le `replace` reste atomique, et le
    # dernier arrivé gagne proprement.
    tmp = d / f"{name}.{uuid.uuid4().hex}.tmp"
    try:
        img.save(tmp, format="PNG", optimize=False)
        _replace_avec_patience(tmp, d / name)
    except OSError as e:
        try:
            tmp.unlink()
        except OSError:
            pass                       # le brouillon n'a peut-être jamais existé
        # L'ERREUR LITTÉRALE, MAIS PAS LE CHEMIN. `str(e)` porte le chemin
        # ABSOLU du fichier — donc le nom de compte de l'utilisateur, dans une
        # réponse HTTP (l'incident de fuite du gauntlet, à ne pas rejouer).
        # `strerror` dit ce que l'OS a refusé, et rien d'autre.
        motif = getattr(e, "strerror", None) or e.__class__.__name__
        raise HTTPException(
            409, f"Le fichier de capture n'a pas pu être remplacé : {motif}. "
                 f"Un autre envoi l'écrivait au même instant, ou le disque a "
                 f"refusé. Renvoyez l'image.")
    # L'HORODATAGE EST EN MILLISECONDES. En secondes, deux imports de la même
    # seconde rendaient le MÊME `stamp`, donc la même URL d'aperçu
    # (`…?t=stamp`), donc l'ancienne image resservie par le cache du
    # navigateur : le remplacement se voyait dans le fichier et pas à l'écran.
    return {"w": img.size[0], "h": img.size[1],
            "bytes": (d / name).stat().st_size,
            "stamp": int(time.time() * 1000)}


def _png(data: bytes) -> Response:
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ── analyse locale : les seuils, et la mesure qui les pose ───────────────────
#
# CHAQUE CHIFFRE DE CETTE SECTION EST MESURÉ OU RAISONNÉ, ET CHACUN LE DIT.
# La première version de cette phrase annonçait « aucun chiffre n'est deviné »
# — c'était faux pour trois d'entre eux (la proximité de coin, le seuil de
# fusion, la taille du sous-échantillon de palette), qui sont des choix de bon
# sens qu'aucune mesure ne fixe. Une promesse trop large sur une page de
# constantes est pire qu'une constante nue : elle décourage de vérifier.
# Les mesures viennent des cartes de synthèse du test (630 x 880 px pour un
# poker 63 x 88 mm, bordure de 26 px, trois cartouches à fort contraste).

# LE BALAYAGE DE BORDURE. On sonde depuis chaque bord vers l'intérieur, sur le
# quart du petit côté : une bande de bordure de carte fait 2 à 5 mm sur 63,
# soit 3 à 8 % — un quart laisse de la marge à une carte au cadre large sans
# jamais aller chercher un front au milieu de l'illustration.
BORD_FENETRE = 0.25
# ... et on IGNORE le cinquième de chaque extrémité du bord. Les coins sont
# arrondis : sonder à travers eux mesurerait la courbe, pas la bande. Le rayon
# d'un coin de carte vaut ~3 mm sur 63 (5 %) ; 20 % est quatre fois la marge.
BORD_MARGE = 0.20
# LE FRONT MINIMAL, EN DISTANCE L1 SUR RVB (0-765). Mesuré : une bordure or
# franche sur intérieur sombre donne un pic de 455 ; un dégradé doux sans
# bordure donne 1. Deux ordres de grandeur séparent les deux cas, le seuil se
# pose au milieu du vide. C'est LUI qui rend la bordure ABSENTE plutôt que
# « 0 mm, confiance 1 » sur une carte pleine illustration.
BORD_FRONT_MIN = 40
# ... et le front doit DOMINER le reste du profil.
# CE QU'IL FAIT VRAIMENT, RE-MESURÉ — et l'aveu précédent avait tort DEUX
# FOIS. Il prétendait que ce rapport ne peut pas mordre sur une carte (parce
# qu'un fondu monotone ne cumule que ~5 de marche médiane) et qu'il ne mord
# que sur une image minuscule. Les deux sont faux, et c'est le PROFIL
# OSCILLANT qui le montre : sur des rayures de 2 px, la marche médiane vaut
# 455 et le plancher passe de 40 à 1824 — le rapport décide seul, et il
# refuse. Sur une image de 40 x 56, à l'inverse, la marche médiane vaut ZÉRO
# et le rapport ne joue aucun rôle. Ce qu'il attrape n'est donc pas un fondu :
# c'est une bordure à FILETS FINS ou un scan TRAMÉ, où aucun front ne domine
# la trame. Le refus doit alors nommer cette cause-là — voir `_front`, qui
# rend son diagnostic, et la note « profil texturé » de `_analyse_bordure`.
BORD_FRONT_RATIO = 4.0
# UN SEUL BORD N'EST PAS UNE BANDE. Un liseré trouvé en haut et nulle part
# ailleurs est un élément de mise en page, pas une bordure de carte.
BORD_MIN_BORDS = 2
# La distance L1 sous laquelle deux couleurs se valent, pour le suivi de coin.
# RAISONNÉ, PAS MESURÉ — et c'est dit : 60 sur 765, soit 20 niveaux par canal,
# le voisinage d'une couleur « la même à l'œil ». Il faut qu'il tolère un
# dégradé de bande et un anticrénelage sans confondre le dehors de la carte
# avec sa bordure. Aucun cas de synthèse ne le contraint aujourd'hui ; le jour
# où un coin réel le démentira, ce chiffre-là bougera avec sa mesure.
BORD_COIN_PROCHE = 60
# La fenêtre de recherche d'un rayon de coin : 15 % du petit côté (~9 mm sur
# 63) — largement au-delà de tout rayon de carte réel.
BORD_COIN_FENETRE = 0.15

# LA GRILLE DES ZONES, EN MILLIMÈTRES ET NON EN PIXELS. Le plan disait
# « ~32 px » ; mesuré, un bloc en pixels rend l'analyse DÉPENDANTE de la
# résolution du scan — la même carte à 1060 px et au plafond d'import
# n'aurait pas les mêmes boîtes. Un bloc de 1,5 mm vaut 25 px sur le scan
# (1060 px pour 63 mm) — les « ~32 px » du plan, à la résolution qu'il avait en
# tête — et il donne une grille de ~42 colonnes DÈS 168 px DE LARGE, quelle
# que soit la trame au-dessus. En dessous, le plancher de 4 px par bloc mord
# et la grille rétrécit (15 colonnes à 60 px, mesuré) : la phrase « toujours
# 42 colonnes » était fausse là où le bloc ne peut plus être un bloc. C'est
# aussi la hauteur d'une ligne de texte de carte : une zone plus fine qu'un
# bloc n'est pas une zone, c'est un trait.
ZONE_BLOC_MM = 1.5
# Les pixels de TRAVAIL par bloc. L'image est ramenée à `cols * ZONE_SOUS` de
# large avant la carte d'énergie. Le coût n'en devient pas CONSTANT — la
# première rédaction l'écrivait, et la mesure la dément : `_grille` prend
# 7,9 ms sur 630 x 880 et 35,9 ms au plafond d'import, parce que la RÉDUCTION
# qui mène au sous-échantillon lit, elle, toute la trame. Ce qui devient
# constant, c'est la carte d'énergie elle-même, et c'est la partie chère : le
# coût est AMORTI à partir de la grille. Huit pixels par bloc suffisent à voir
# une arête de lettre.
ZONE_SOUS = 8
# Le rayon du passe-haut, en pixels de TRAVAIL. `_micro_contrast` floue deux
# fois (r puis 2r) : sa portée totale vaut ~9r, soit ici 1,5 bloc — et c'est ce
# chiffre qui fixe le retrait ci-dessous. Mesuré à r = 8/3 : la portée de
# 3 blocs noyait les trois cartouches dans un seul composant qui faisait le
# tour de la carte.
ZONE_RAYON = ZONE_SOUS / 6.0
ZONE_PORTEE_BLOCS = 9.0 * ZONE_RAYON / ZONE_SOUS
# Le seuil, en part de l'étendue [p5, p95] des blocs. Mesuré sur la carte de
# synthèse : 0,25 à 0,50 rendent les mêmes trois boîtes, 0,35 est le milieu.
ZONE_FRAC = 0.35
# L'ÉTENDUE MINIMALE SOUS LAQUELLE ON NE CHERCHE RIEN. Un seuil relatif sur une
# image sans contraste local découpe du bruit en « zones ». Mesuré : 89 sur la
# carte de synthèse, 0 sur un aplat total. Le plancher se pose près de zéro.
ZONE_SPAN_MIN = 10
ZONE_MIN_BLOCS = 2                 # un bloc seul est un point, pas une boîte
ZONE_MAX_BOITES = 12               # un relevé se lit ; 400 boîtes ne se lisent pas
# Deux boîtes dont la plus petite est à moitié dans l'autre n'en font qu'une :
# les composants sont disjoints, mais leurs RECTANGLES peuvent s'emboîter.
# RAISONNÉ : « à moitié dedans » est la définition qu'on a choisie, et une
# demie est le seul point où la question n'a pas de réponse arbitraire.
ZONE_FUSION = 0.50

# LE FOND — les deux portes de `pixel_ops.chroma_key`, RECOPIÉES ici pour
# pouvoir PUBLIER la mesure qui refuse. Le verdict, lui, vient de `chroma_key`
# et de personne d'autre : ces constantes ne décident rien, elles nomment. Le
# test de la pièce confronte les deux (mesure d'ici, verdict de là-bas) sur un
# dégradé et sur un aplat — s'ils divergeaient, le refus mentirait sur sa cause.
FOND_TOLERANCE = 28
FOND_FEATHER = 1.6
FOND_SEUIL_UNI = 0.60
FOND_COUV_MIN = 0.05
FOND_COUV_MAX = 0.95
# La phrase de la spec §8 : « fond non uni à l'import -> refus mesuré du
# détourage local + PROPOSITION de l'option IA ». Le prix ne s'écrit pas ici :
# il vient de `pricing.py` par la route d'options (T3), jamais d'une copie.
OPTION_IA = ("Le détourage local s'arrête ici : ce fond n'est pas assez uni "
             "pour être retiré sans abîmer le sujet. Un détourage par IA sait "
             "isoler un fond comme celui-là — c'est une option payante, "
             "proposée à part avec son prix.")

# L'ÉCART DE RATIO SOUS LEQUEL ON SE TAIT. Il était nu dans le code, et un
# seuil nu est un seuil qu'on n'ose plus bouger. Sa raison : un poker_eu de
# 630 px de large vaut 880 px de haut ; 879 ou 881 — l'arrondi d'UN pixel —
# donnent déjà ±0,11 % d'écart. Une note à chaque analyse sur un demi-pour-cent
# serait du bruit qui apprendrait à ne plus lire les notes. Au-delà, l'écart
# est celui d'un vrai recadrage, et il se dit. Mesuré aux deux bords :
# +0,45 % se tait, +0,57 % parle.
ECART_RATIO_MUET = 0.005

PALETTE_N = 6                      # « ~6 teintes dominantes » (plan D4)
# Côté long du sous-échantillon de comptage. RAISONNÉ : compter des teintes
# DOMINANTES n'a pas besoin de la trame entière — 256 px de côté font encore
# 65 000 échantillons pour six couleurs, et la réduction coûte moins que la
# quantification qu'elle évite. Le chiffre n'est pas gardé par un test : le
# ramener à 24 px change les teintes mineures, ce que le contrôle de palette
# voit, mais rien n'épingle 256 en particulier.
PALETTE_TRAVAIL_PX = 256


def _hexa(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(v)))) for v in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _l1(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else float(v)


def _fr(v: float, n: int = 2) -> str:
    """Un nombre DANS UNE PHRASE FRANÇAISE. Les notes sont de la prose lue par
    l'utilisateur, pas du JSON : « uniformité 0.246 pour un plancher de 0.6 »
    au milieu de trois lignes à virgule décimale se voit tout de suite (mesuré
    à l'écran). Les CHAMPS, eux, restent des nombres — c'est l'écran qui les
    écrit, et lui aussi met la virgule."""
    return f"{float(v):.{n}f}".replace(".", ",")


def _signe(v: float, n: int) -> float:
    """Arrondi demi-haut SYMÉTRIQUE. `contract.rnd` est demi-haut vers le
    haut et le dit : « toutes les longueurs servies ici sont positives ».
    L'écart de ratio, lui, a un signe — une image plus haute que son format
    donne un écart négatif — et `floor(v*p + 0.5)` arrondirait -0,0025 en
    -0,002 d'un côté et 0,0025 en 0,003 de l'autre. Une mesure signée mérite
    un arrondi qui ne penche pas."""
    s = -1.0 if v < 0 else 1.0
    return s * rnd(abs(float(v)), n)


# ── 1. la bordure : un balayage de gradient depuis les quatre bords ──────────

def _profils(im) -> dict:
    """Pour chaque bord, la couleur MOYENNE de la bande à la profondeur k.

    En une seule opération C par bord : on recadre la tranche centrale du bord,
    puis `resize` en BOX vers une colonne (ou une ligne) d'un pixel — chaque
    pixel de sortie EST la moyenne de sa rangée. Mesuré à 1,5 ms sur
    630 x 880 et 4,4 ms sur 1060 x 1484 ; la boucle Python équivalente lisait
    un demi-million de pixels un par un."""
    from PIL import Image
    w, h = im.size
    maxk = max(2, int(min(w, h) * BORD_FENETRE))
    x0, x1 = int(w * BORD_MARGE), max(int(w * BORD_MARGE) + 1,
                                      int(w * (1.0 - BORD_MARGE)))
    y0, y1 = int(h * BORD_MARGE), max(int(h * BORD_MARGE) + 1,
                                      int(h * (1.0 - BORD_MARGE)))
    maxk = max(2, min(maxk, w, h))
    out = {}
    haut = im.crop((x0, 0, x1, maxk)).resize((1, maxk), Image.BOX)
    out["haut"] = [haut.getpixel((0, k)) for k in range(maxk)]
    bas = im.crop((x0, h - maxk, x1, h)).resize((1, maxk), Image.BOX)
    out["bas"] = [bas.getpixel((0, maxk - 1 - k)) for k in range(maxk)]
    gau = im.crop((0, y0, maxk, y1)).resize((maxk, 1), Image.BOX)
    out["gauche"] = [gau.getpixel((k, 0)) for k in range(maxk)]
    dro = im.crop((w - maxk, y0, w, y1)).resize((maxk, 1), Image.BOX)
    out["droite"] = [dro.getpixel((maxk - 1 - k, 0)) for k in range(maxk)]
    return out


def _front(profil) -> dict:
    """La PREMIÈRE marche du profil : sa position (= l'épaisseur en px), sa
    hauteur, et le BRUIT du profil entier. Sans ce dernier, un fondu régulier
    finirait par cumuler assez de dénivelé pour se faire passer pour une
    bordure.

    ELLE REND TOUJOURS UN DIAGNOSTIC, jamais `None` : `ok` dit s'il y a un
    front, et sinon `cause` dit POURQUOI il n'y en a pas — « plat » (rien ne
    dépasse le plancher absolu) ou « texture » (le plancher a été RELEVÉ par
    l'agitation du profil). Les deux refus ne se ressemblent pas du tout à
    l'écran, et celui qui les lit doit pouvoir les distinguer : un scan tramé
    n'appelle pas le même geste qu'une carte pleine illustration.

    LA PREMIÈRE, ET PAS LA PLUS HAUTE — la première écriture prenait le
    maximum, et une carte de synthèse à trois cartouches l'a démentie en une
    passe : un bandeau clair posé sur toute la largeur à 60 px du haut donne
    une marche de 540 quand la bordure n'en donne que 455, et l'analyse
    annonçait une bordure de 6 mm là où le test en avait posé 2,6. Une bordure
    est ce qui BORDE : le premier front en venant du bord, par définition."""
    if len(profil) < 3:
        return {"ok": False, "cause": "court", "bruit": 0,
                "plancher": float(BORD_FRONT_MIN), "pic": 0}
    d = [_l1(profil[k], profil[k - 1]) for k in range(1, len(profil))]
    trie = sorted(d)
    bruit = trie[len(trie) // 2]
    plancher = max(float(BORD_FRONT_MIN), BORD_FRONT_RATIO * (bruit + 1))
    for i, v in enumerate(d):
        if v < plancher:
            continue
        # LA NETTETÉ, EN DEUX FACTEURS QUI SAVENT TOMBER TOUS LES DEUX.
        #  · le fond de bruit : ce que le front doit à lui-même plutôt qu'à
        #    l'agitation du profil ;
        #  · la LARGEUR du front en profondeur — combien de rangées la
        #    transition met à s'accomplir. Une bordure imprimée bascule en une
        #    rangée ; la PHOTO d'une carte, floue ou compressée, met dix
        #    rangées, et c'est exactement la situation où la mesure de bordure
        #    mérite d'être crue à moitié. Sans ce second facteur la netteté ne
        #    tombait presque jamais : le profil est une MOYENNE sur 60 % du
        #    bord, et elle écrase le grain (mesuré : un bruit uniforme de
        #    ±28 par canal laisse la netteté à 0,993).
        large = 1
        seuil_flanc = 0.25 * v
        j = i - 1
        while j >= 0 and d[j] >= seuil_flanc:
            large += 1
            j -= 1
        j = i + 1
        while j < len(d) and d[j] >= seuil_flanc:
            large += 1
            j += 1
        net = (_clamp01(1.0 - bruit / float(v))
               * _clamp01(2.0 / (1.0 + large)))
        return {"ok": True, "k": i + 1, "pic": v, "bruit": bruit,
                "largeur": large, "nettete": net, "plancher": plancher}
    return {"ok": False,
            "cause": "texture" if plancher > BORD_FRONT_MIN else "plat",
            "bruit": bruit, "plancher": plancher, "pic": max(d)}


def _rayon_coin(im, profils: dict) -> float | None:
    """Le rayon de coin, estimé par la LONGUEUR DE CE QUI N'EST PAS LA CARTE.

    Sur un coin droit, le pixel du coin porte déjà la couleur de la bande. Si
    le coin est arrondi, les premiers pixels de la RANGÉE EXTÉRIEURE
    appartiennent à ce qu'il y a autour de la carte : on avance le long du
    bord jusqu'à retrouver la couleur de bande, et la distance parcourue est
    le rayon. Huit mesures (quatre coins, deux directions), médiane — un coin
    abîmé ou un logo posé dessus ne déplace pas la médiane de huit.

    LA RANGÉE EXTÉRIEURE, ET PAS LE MILIEU DE LA BANDE : une première version
    sondait à mi-bande, où la corde d'un cercle de rayon r ne mesure plus r.
    Mesuré : 10 px lus pour 40 px posés, à la profondeur 13 — soit exactement
    `40 - sqrt(40² - 27²)`. Le rayon ne se lit qu'au bord.

    ET LA COURSE LUE N'EST PAS LE RAYON : `_rayon_depuis_course` la corrige.
    C'est là que vit la seconde moitié de la mesure."""
    w, h = im.size
    maxr = max(2, int(min(w, h) * BORD_COIN_FENETRE))
    px = im.load()
    vues = []
    # (bord de référence, générateur de points le long de la rangée extérieure)
    axes = (
        ("haut", lambda i: (i, 0)), ("haut", lambda i: (w - 1 - i, 0)),
        ("bas", lambda i: (i, h - 1)), ("bas", lambda i: (w - 1 - i, h - 1)),
        ("gauche", lambda i: (0, i)), ("gauche", lambda i: (0, h - 1 - i)),
        ("droite", lambda i: (w - 1, i)), ("droite", lambda i: (w - 1, h - 1 - i)),
    )
    for nom, point in axes:
        ref = profils[nom][0]
        trouve = None
        for i in range(min(maxr, w, h)):
            x, y = point(i)
            if _l1(px[x, y], ref) <= BORD_COIN_PROCHE:
                trouve = i
                break
        if trouve is not None:
            vues.append(trouve)
    if len(vues) < 4:                       # moins de la moitié : on se tait
        return None
    vues.sort()
    return _rayon_depuis_course(float(vues[len(vues) // 2]))


def _rayon_depuis_course(course: float) -> float:
    """La course lue sur la rangée extérieure -> le RAYON.

    LES DEUX NE SONT PAS LE MÊME NOMBRE, et l'écart est calculable. La rangée
    extérieure a une HAUTEUR : son premier pixel plein n'est pas celui qui
    touche le disque, c'est celui dont le CENTRE y entre. Pour un arc de
    rayon r centré en (r, r), ce pixel est à `r - sqrt(r)` du coin, à un demi
    près. La course sous-estime donc le rayon de `sqrt(r)` — 3 px sur 10,
    9 px sur 90, soit 12 à 30 % : un biais qui grandit avec le rayon et qu'on
    ne peut pas laisser dans une tolérance.

    CE N'EST PAS UN ARTEFACT DU MONTAGE DE TEST. Le calcul ne parle que de la
    grille de pixels : tout arc rastérisé s'y plie, celui d'une carte scannée
    comme celui d'une bibliothèque de dessin. La correction appartient donc à
    la mesure, pas au test — et le test, lui, pose des rayons ronds et exige
    de les retrouver.

    L'inversion de `c = r - sqrt(r)` est `r = ((1 + sqrt(1 + 4c)) / 2)²`.
    Mesurée sur des rayons posés de 10, 20, 40, 60 et 90 px : elle rend 10,2 ;
    20,5 ; 40,3 ; 60,8 et 90,5 — sous 0,10 mm d'écart partout. Une course
    NULLE reste un rayon nul : un coin carré n'a pas de rayon caché."""
    if course <= 0.0:
        return 0.0
    return ((1.0 + math.sqrt(1.0 + 4.0 * course)) / 2.0) ** 2


def _couleur_bande(im, bord_px: int):
    """La couleur DOMINANTE des quatre bandes, pas leur moyenne. Une bordure à
    filets (or sur noir) a une moyenne qui n'existe nulle part sur la carte ;
    la quantification, elle, rend une couleur qu'on peut montrer."""
    from PIL import Image
    w, h = im.size
    e = max(1, min(int(bord_px), min(w, h) // 2))
    if w - 2 * e < 1 or h - 2 * e < 1:
        # La bande mangerait la carte : il n'y a plus de bande à isoler, on
        # rend la dominante de l'image entière plutôt que de recadrer du vide.
        return _dominantes(im, 4)[0][0]
    lg = w - 2 * e
    ht = h - 2 * e
    bande = Image.new("RGB", (max(lg, ht), 4 * e))
    bande.paste(im.crop((e, 0, w - e, e)).resize((max(lg, ht), e), Image.BOX),
                (0, 0))
    bande.paste(im.crop((e, h - e, w - e, h)).resize((max(lg, ht), e), Image.BOX),
                (0, e))
    bande.paste(im.crop((0, e, e, h - e)).transpose(Image.ROTATE_90)
                  .resize((max(lg, ht), e), Image.BOX), (0, 2 * e))
    bande.paste(im.crop((w - e, e, w, h - e)).transpose(Image.ROTATE_90)
                  .resize((max(lg, ht), e), Image.BOX), (0, 3 * e))
    return _dominantes(bande, 4)[0][0]


def _analyse_bordure(im, mm_par_px: float, notes: list):
    """(relevé de bordure ou None, épaisseur en PIXELS). Épaisseur (mm),
    couleur, rayon de coin, et la confiance MESURÉE.

    LES PIXELS SORTENT PAR LA PORTE DE SERVICE. Le relevé publié ne parle
    QU'EN MILLIMÈTRES (plan D3 : « une unité par frontière ») ; l'épaisseur en
    pixels est rendue à part parce que le chercheur de zones en a besoin pour
    son retrait, et lui vit de ce côté-ci de l'API.

    La confiance est le produit de trois parts qui savent toutes tomber :
    combien de bords ont vu un front (n/4), à quel point leurs épaisseurs
    concordent (la régularité), et la netteté du plus mou des quatre fronts.
    Chacune a son cas connu, et le test les joue : une bordure posée
    irrégulière effondre la deuxième (mesuré 0,167 pour des bandes de 1, 2,6,
    4 et 6 mm) ; un flou gaussien de 1 px effondre la troisième (mesuré
    1,0 -> 0,5 -> 0,167 à sigma 0, 1 et 3 px)."""
    profils = _profils(im)
    fronts = {nom: _front(p) for nom, p in profils.items()}
    vus = {nom: f for nom, f in fronts.items() if f["ok"]}
    if len(vus) < BORD_MIN_BORDS:
        # LE REFUS DOIT NOMMER SA VRAIE CAUSE. « Aucun front franc » couvrait
        # deux situations qui n'appellent pas le même geste : une carte pleine
        # illustration (rien ne dépasse le plancher) et un scan TRAMÉ ou une
        # bordure à filets fins (le plancher a été relevé par l'agitation du
        # profil, et aucune marche ne le dépasse plus). La seconde ressortait
        # sous la phrase de la première — un refus qui envoie chercher au
        # mauvais endroit.
        tex = [f for f in fronts.values()
               if not f["ok"] and f.get("cause") == "texture"]
        if tex:
            notes.append(
                f"Bordure : profil TEXTURÉ sur {len(tex)} des 4 bords — la "
                f"marche médiane y vaut {max(f['bruit'] for f in tex)}, ce qui "
                f"relève le plancher de détection de {BORD_FRONT_MIN} à "
                f"{int(max(f['plancher'] for f in tex))}, et aucune marche ne "
                f"le dépasse. Une bordure à filets fins, ou un scan tramé, "
                f"donne ce profil : il n'y a pas UNE bande à mesurer. Rien "
                f"n'est publié.")
        else:
            notes.append(
                f"Bordure : aucun front franc sur {4 - len(vus)} des 4 bords "
                f"(il en faut {BORD_MIN_BORDS}). La carte n'a pas de bande de "
                f"bordure mesurable, ou elle se confond avec l'illustration — "
                f"rien n'est publié plutôt qu'une épaisseur de zéro.")
        return None, 0.0
    eps = [f["k"] for f in vus.values()]
    ep_px = sorted(eps)[len(eps) // 2]
    regularite = _clamp01(1.0 - (max(eps) - min(eps)) / float(max(eps)))
    nettete = min(f["nettete"] for f in vus.values())
    conf = _clamp01(len(vus) / 4.0 * regularite * nettete)
    # LES ÉPAISSEURS SONT UN DICTIONNAIRE, ET C'EST UNE CORRECTION. Elles
    # sortaient en LISTE triée par valeur, à côté d'une liste de bords triée
    # par NOM : les apparier par indice — ce que tout lecteur fait — était
    # faux dès que l'ordre des mesures n'était pas l'ordre de l'alphabet.
    # Mesuré sur des bandes de 1,0 / 2,0 / 3,0 / 4,0 mm posées à gauche, en
    # haut, à droite et en bas : les quatre couples étaient faux. Un
    # dictionnaire ne peut pas se désapparier.
    epaisseurs = {nom: rnd(f["k"] * mm_par_px, 3) for nom, f in vus.items()}
    out = {"mm": rnd(ep_px * mm_par_px, 3),
           "color": _hexa(_couleur_bande(im, ep_px)),
           "confidence": rnd(conf, 3),
           "bords": sorted(epaisseurs),
           "regularite": rnd(regularite, 3),
           "nettete": rnd(nettete, 3),
           "epaisseurs_mm": epaisseurs}
    r = _rayon_coin(im, profils)
    out["radius_mm"] = rnd(r * mm_par_px, 3) if r is not None else None
    if r is None:
        notes.append("Bordure : le rayon de coin n'a pas pu être suivi sur au "
                     "moins quatre des huit mesures de coin — il est laissé "
                     "vide au lieu d'être inventé.")
    return out, float(ep_px)


# ── 2. les zones occupées : blocs, seuil, composants 4-voisins ───────────────

def _grille(im, mm_par_px: float):
    """La carte d'énergie, ramenée à une grille de blocs de `ZONE_BLOC_MM`.

    `_micro_contrast` vient de `pbr_service` : c'est la mesure « cette région
    accroche la lumière à l'échelle du grain », et un texte sur un aplat en
    est le cas d'école. Elle est PRIVÉE (préfixe `_`) chez sa pièce d'origine :
    le test de la pièce l'importe explicitement pour qu'un renommage là-bas
    fasse rougir ICI, au lieu de faire tomber la route en production."""
    from PIL import Image
    from app.services.pbr_service import _micro_contrast
    w, h = im.size
    bloc_px = max(4.0, ZONE_BLOC_MM / mm_par_px)
    cols = max(1, int(round(w / bloc_px)))
    rows = max(1, int(round(h / bloc_px)))
    trav = im.convert("L").resize((cols * ZONE_SOUS, rows * ZONE_SOUS),
                                  Image.BOX)
    energie = _micro_contrast(trav, ZONE_RAYON)
    return energie.resize((cols, rows), Image.BOX), cols, rows, bloc_px


def _composants(masque, cols: int, rows: int) -> list:
    """Composants connexes 4-voisins sur la grille grossière, en ITÉRATIF.

    Rien de tel n'existait dans le lab (vérifié : ni `pixel_ops` ni
    `pbr_service` n'ont de chercheur de boîtes) — c'est le seul morceau neuf
    de l'analyse. La pile explicite plutôt que la récursion : une grille de
    42 x 59 fait 2 478 cases, et une carte entièrement dense les enfilerait
    toutes dans la même chaîne d'appels."""
    vus = [[False] * cols for _ in range(rows)]
    out = []
    for y0 in range(rows):
        for x0 in range(cols):
            if not masque[y0][x0] or vus[y0][x0]:
                continue
            pile = [(x0, y0)]
            vus[y0][x0] = True
            cells = []
            while pile:
                cx, cy = pile.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < cols and 0 <= ny < rows
                            and masque[ny][nx] and not vus[ny][nx]):
                        vus[ny][nx] = True
                        pile.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append({"x0": min(xs), "y0": min(ys), "x1": max(xs) + 1,
                        "y1": max(ys) + 1, "n": len(cells)})
    return out


def _emboite(a: dict, b: dict) -> float:
    """Part de la PLUS PETITE des deux boîtes qui tombe dans l'autre. Le
    rapport de Jaccard dirait « distinctes » d'un cartouche entièrement posé
    sur un bandeau dix fois plus grand — ici c'est la même zone."""
    ix = max(0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    iy = max(0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    inter = ix * iy
    if not inter:
        return 0.0
    aa = (a["x1"] - a["x0"]) * (a["y1"] - a["y0"])
    bb = (b["x1"] - b["x0"]) * (b["y1"] - b["y0"])
    return inter / float(min(aa, bb) or 1)


def _fusionne(boites: list) -> list:
    """Fusion par recouvrement, jusqu'au point fixe : fusionner A et B peut
    créer un recouvrement avec C qu'aucune passe unique ne verrait."""
    bs = list(boites)
    encore = True
    while encore:
        encore = False
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                if _emboite(bs[i], bs[j]) >= ZONE_FUSION:
                    a, b = bs[i], bs[j]
                    bs[i] = {"x0": min(a["x0"], b["x0"]),
                             "y0": min(a["y0"], b["y0"]),
                             "x1": max(a["x1"], b["x1"]),
                             "y1": max(a["y1"], b["y1"]),
                             "n": a["n"] + b["n"]}
                    bs.pop(j)
                    encore = True
                    break
            if encore:
                break
    return bs


def _analyse_zones(im, mm_par_px: float, bord_px: float, notes: list):
    """(boîtes en mm, largeur EN MM de la bande exclue le long des bords)."""
    from app.services.pbr_service import stats
    g, cols, rows, bloc_px = _grille(im, mm_par_px)
    s = stats(g)
    if s["span"] < ZONE_SPAN_MIN:
        notes.append(
            f"Zones : contraste local trop faible pour découper quoi que ce "
            f"soit (étendue {s['span']} sur 255, plancher {ZONE_SPAN_MIN}). "
            f"Aucune boîte n'est publiée — un seuil relatif sur une image "
            f"plate ne découpe que du bruit.")
        return [], 0.0
    seuil = s["p5"] + ZONE_FRAC * (s["p95"] - s["p5"])
    # LE RETRAIT. La bande de bordure est le plus fort contraste de la carte :
    # sans retrait, son anneau relie toutes les zones en un seul composant qui
    # fait le tour de l'image (mesuré : une boîte de 570 x 825 px au lieu de
    # trois). On retire l'épaisseur de bande PLUS la portée du passe-haut, qui
    # étale le front vers l'intérieur.
    retrait = int(math.ceil(bord_px / bloc_px)
                  + math.ceil(ZONE_PORTEE_BLOCS))
    if 2 * retrait >= min(cols, rows):       # une carte plus petite que sa marge
        retrait = 0
    # ... ET IL FAUT LE DIRE. Ce retrait n'est pas gratuit : il BLANCHIT une
    # bande de plusieurs millimètres le long des quatre bords — 6,00 mm
    # mesurés pour une bordure de 2,6 mm — et un cartouche posé dedans
    # ressortait COUPÉ à la frontière du masque, avec une densité et une
    # netteté parfaitement saines. Rien, dans le relevé, ne distinguait la
    # coupe d'une mesure (mesuré : un cartouche de 30 x 9 mm collé au coin
    # rendait un recouvrement de 0,459 avec ce qui avait été posé, et `notes`
    # était vide). C'est le cas du bandeau de titre collé au cadre, et P3 fera
    # naître des slots de ces millimètres-là.
    #
    # CE QU'ON NE FAIT PAS, ET POURQUOI : on ne ré-étend PAS les boîtes vers
    # l'extérieur pour « récupérer » la coupe. Le retrait existe pour exclure
    # l'énergie de la bordure elle-même ; une ré-extension gober ait le cadre et
    # rendrait une boîte fausse au lieu d'une boîte courte. Entre une mesure
    # tronquée AVOUÉE et une mesure inventée, on garde la première — et
    # l'adoptant lit `tronquee`. La ré-extension mesurée reste une dette.
    bande_mm = rnd(retrait * bloc_px * mm_par_px, 2)
    if retrait:
        portee_mm = rnd(math.ceil(ZONE_PORTEE_BLOCS) * bloc_px * mm_par_px, 2)
        notes.append(
            f"Zones : une bande de {_fr(bande_mm)} mm le long des quatre bords "
            f"est exclue de la recherche — la bande de bordure "
            f"({_fr(rnd(bord_px * mm_par_px, 2))} mm) plus la portée du filtre "
            f"({_fr(portee_mm)} mm), sans quoi l'anneau du cadre relie toutes "
            f"les zones en une seule. Les boîtes qui la touchent portent "
            f"« tronquee » : de ce côté-là, leur bord est celui du masque et "
            f"non celui du dessin.")
    lire = g.load()
    masque = [[(lire[x, y] > seuil
                and retrait <= x < cols - retrait
                and retrait <= y < rows - retrait)
               for x in range(cols)] for y in range(rows)]
    trouves = [c for c in _composants(masque, cols, rows)
               if c["n"] >= ZONE_MIN_BLOCS]
    fus = _fusionne(trouves)
    fus.sort(key=lambda c: -((c["x1"] - c["x0"]) * (c["y1"] - c["y0"])))
    if len(fus) > ZONE_MAX_BOITES:
        notes.append(f"Zones : {len(fus)} boîtes candidates trouvées, les "
                     f"{ZONE_MAX_BOITES} plus grandes sont publiées.")
        fus = fus[:ZONE_MAX_BOITES]
    out = []
    for c in fus:
        bw = c["x1"] - c["x0"]
        bh = c["y1"] - c["y0"]
        somme = 0
        for y in range(c["y0"], c["y1"]):
            for x in range(c["x0"], c["x1"]):
                somme += lire[x, y]
        out.append({
            "x": rnd(c["x0"] * bloc_px * mm_par_px, 2),
            "y": rnd(c["y0"] * bloc_px * mm_par_px, 2),
            "w": rnd(bw * bloc_px * mm_par_px, 2),
            "h": rnd(bh * bloc_px * mm_par_px, 2),
            # DENSITÉ : la part du rectangle réellement au-dessus du seuil. Un
            # cartouche plein vaut 1, une diagonale de texte vaut 0,3 — c'est
            # ce qui distingue une boîte d'un fouillis qui a le même contour.
            "densite": rnd(c["n"] / float(bw * bh), 3),
            # NETTETÉ : l'énergie moyenne du rectangle, ramenée à [0,1]. Elle
            # dit combien la zone tranche, la densité dit si elle est pleine.
            "nettete": rnd(somme / float(bw * bh * 255), 3),
            # TRONQUÉE : un côté au moins bute sur la frontière du masque. Ce
            # que le drapeau affirme est exactement « DE CE CÔTÉ-LÀ, ON NE
            # VOIT PAS PLUS LOIN » — pas « cette boîte a certainement été
            # coupée ». Une zone qui commence pile au premier bloc autorisé
            # est indiscernable d'une zone coupée, et c'est justement pour ça
            # qu'on la marque : la mesure est un MINIMUM, pas une taille, et
            # celui qui l'adopte doit le savoir avant d'en faire un slot.
            "tronquee": bool(c["x0"] <= retrait or c["y0"] <= retrait
                             or c["x1"] >= cols - retrait
                             or c["y1"] >= rows - retrait),
        })
    return out, bande_mm


# ── 3. le fond : le verdict de `chroma_key`, et la mesure qui l'explique ─────

def _mesure_fond(im) -> dict:
    """Les DEUX portes de `chroma_key`, chiffrées — mêmes échantillons, même
    clé médiane, même tolérance. On ne décide rien ici : `chroma_key` reste le
    juge, ces nombres ne font que dire POURQUOI il a refusé."""
    from PIL import Image, ImageChops
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    pas = max(1, (w + h) // 128)
    ech = []
    for x in range(0, w, pas):
        ech.append(px[x, 0])
        ech.append(px[x, h - 1])
    for y in range(0, h, pas):
        ech.append(px[0, y])
        ech.append(px[w - 1, y])
    rs = sorted(s[0] for s in ech)
    gs = sorted(s[1] for s in ech)
    bs = sorted(s[2] for s in ech)
    cle = (rs[len(rs) // 2], gs[len(gs) // 2], bs[len(bs) // 2])
    proches = sum(1 for s in ech if _l1(s, cle) <= 3 * FOND_TOLERANCE)
    lo = int(FOND_TOLERANCE)
    hi = max(lo + 1, int(round(FOND_TOLERANCE * FOND_FEATHER)))
    diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), cle)) \
                     .convert("L")
    lut = [0 if v <= lo else 255 if v >= hi
           else int((v - lo) * 255 / (hi - lo)) for v in range(256)]
    hist = diff.point(lut).histogram()
    return {"cle": cle,
            "uniformite": proches / float(len(ech)),
            "couverture": sum(hist[128:]) / float(w * h)}


def _analyse_fond(im, notes: list) -> dict:
    from app.services.pixel_ops import chroma_key
    m = _mesure_fond(im)
    uni = m["uniformite"]
    couv = m["couverture"]
    _, ok = chroma_key(im, tolerance=FOND_TOLERANCE, feather=FOND_FEATHER)
    if ok:
        # LA CONFIANCE DU FOND EST SON UNIFORMITÉ MESURÉE, pas un « oui ». Elle
        # vaut 0,62 sur un pourtour bruité qui passe tout juste la porte.
        return {"color": _hexa(m["cle"]),
                "confidence": rnd(uni, 3),
                "uniformite": rnd(uni, 3),
                "couverture": rnd(couv, 3),
                "seuil": FOND_SEUIL_UNI}
    # RIEN À DÉTOURER N'EST PAS UN FOND DIFFICILE. Sous le plancher de
    # couverture, ce qui survivrait au détourage est vide : l'image est d'une
    # seule couleur, il n'y a pas de sujet. Proposer là une option PAYANTE,
    # c'est vendre un service sans objet — mesuré sur un aplat gris, la
    # couverture vaut 0,0 % et l'option était proposée quand même.
    rien = couv < FOND_COUV_MIN
    if uni < FOND_SEUIL_UNI:
        motif = "pourtour non uni"
        notes.append(f"Fond : pourtour uni à {_fr(uni, 3)} pour un plancher de "
                     f"{_fr(FOND_SEUIL_UNI)} — le détourage local refuse.")
    elif rien:
        motif = "rien à détourer"
        notes.append(f"Fond : la couleur du pourtour couvre toute l'image "
                     f"({_fr((1.0 - couv) * 100, 1)} %) — il ne resterait "
                     f"{_fr(couv * 100, 1)} % de sujet, sous le plancher de "
                     f"{FOND_COUV_MIN:.0%}. Il n'y a rien à détourer ici, ni "
                     f"localement ni autrement.")
    else:
        motif = "couverture hors bornes"
        notes.append(f"Fond : le pourtour est uni ({_fr(uni, 3)}) mais la "
                     f"couleur retirée laisserait {_fr(couv * 100, 1)} % de "
                     f"l'image, hors des bornes "
                     f"[{FOND_COUV_MIN:.0%}, {FOND_COUV_MAX:.0%}] — un "
                     f"détourage qui garde tout, ou rien, n'est pas un "
                     f"détourage.")
    out = {"bg_failed": True,
           "motif": motif,
           "uniformite": rnd(uni, 3),
           "seuil": FOND_SEUIL_UNI,
           "couverture": rnd(couv, 3),
           "couverture_bornes": [FOND_COUV_MIN, FOND_COUV_MAX],
           "color": _hexa(m["cle"])}
    if not rien:
        out["option_ia"] = OPTION_IA
    return out


# ── 4. la palette ───────────────────────────────────────────────────────────

def _dominantes(im, combien: int) -> list:
    """[(rgb, part), …] triés par part décroissante, par quantification
    adaptative MEDIANCUT — la même primitive PIL que `pixel_ops._quantize_rgb`,
    appelée directement : la fonction de là-bas est privée, et elle traîne un
    tramage qui INVENTE des couleurs intermédiaires. Pour compter des teintes,
    le tramage est exactement ce qu'il ne faut pas."""
    from PIL import Image
    n = max(1, min(256, int(combien)))
    p = im.convert("RGB").quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = p.getpalette() or []
    comptes = p.getcolors(65536) or []
    total = float(sum(c for c, _ in comptes) or 1)
    comptes.sort(key=lambda t: -t[0])
    out = []
    for compte, idx in comptes:
        base = idx * 3
        if base + 2 < len(pal):
            out.append(((pal[base], pal[base + 1], pal[base + 2]),
                        compte / total))
    return out or [((0, 0, 0), 1.0)]


def _analyse_palette(im) -> list:
    from PIL import Image
    w, h = im.size
    k = PALETTE_TRAVAIL_PX / float(max(w, h))
    petit = (im if k >= 1.0
             else im.resize((max(1, round(w * k)), max(1, round(h * k))),
                            Image.BOX))
    return [{"hex": _hexa(rgb), "part": rnd(part, 4)}
            for rgb, part in _dominantes(petit, PALETTE_N)]


# ── 5. le relevé complet ────────────────────────────────────────────────────

def analyse_recto(im, geo) -> dict:
    """Le relevé d'une image de recto, pour une géométrie de deck.

    PURE ET SANS DISQUE : c'est ce qui permet au test de lui donner des cartes
    de synthèse à vérité connue sans monter de route. Chaque détection est
    gardée séparément — une image pathologique dégrade le relevé et l'AVOUE
    dans `notes`, elle ne fait pas tomber la route (spec §8, jamais 500)."""
    w, h = im.size
    notes: list = []
    # L'ÉCHELLE EST CELLE DU FORMAT, PAR LA LARGEUR. Un seul facteur pour les
    # deux axes : si l'image n'a pas le ratio du format, la mesure verticale
    # serait fausse d'autant — alors on PUBLIE l'écart au lieu de le répartir
    # en silence sur les deux axes, où plus personne ne le retrouverait.
    mm_par_px = geo.trim_mm[0] / float(w)
    ratio_img = h / float(w)
    ratio_fmt = geo.trim_mm[1] / float(geo.trim_mm[0])
    ecart = ratio_img / ratio_fmt - 1.0
    if abs(ecart) > ECART_RATIO_MUET:
        notes.append(
            f"Échelle : l'image est {'plus haute' if ecart > 0 else 'plus large'} "
            f"que le format {geo.fmt} de {_fr(abs(ecart) * 100, 1)} % "
            f"(ratio {_fr(ratio_img, 4)} contre {_fr(ratio_fmt, 4)}). Les "
            f"millimètres sont calés sur la LARGEUR ; les mesures verticales "
            f"portent cet écart.")
    out = {
        "analyzed": int(time.time() * 1000),
        "echelle": {"mm_par_px": rnd(mm_par_px, 5),
                    "image_px": [w, h],
                    "carte_mm": [rnd(w * mm_par_px, 2), rnd(h * mm_par_px, 2)],
                    "fmt": geo.fmt,
                    "trim_mm": [geo.trim_mm[0], geo.trim_mm[1]],
                    "ratio_image": rnd(ratio_img, 4),
                    "ratio_format": rnd(ratio_fmt, 4)},
        "ecart_ratio": _signe(ecart, 4),
        "border": None, "boxes": [], "zones_bande_mm": None,
        "bg": None, "palette": [],
        "notes": notes,
    }
    bord_px = 0.0
    try:
        out["border"], bord_px = _analyse_bordure(im, mm_par_px, notes)
    except Exception as e:                                  # noqa: BLE001
        notes.append(f"Bordure : mesure impossible sur cette image ({e}).")
    try:
        out["boxes"], out["zones_bande_mm"] = _analyse_zones(
            im, mm_par_px, bord_px, notes)
    except Exception as e:                                  # noqa: BLE001
        notes.append(f"Zones : mesure impossible sur cette image ({e}).")
    try:
        out["bg"] = _analyse_fond(im, notes)
    except Exception as e:                                  # noqa: BLE001
        notes.append(f"Fond : mesure impossible sur cette image ({e}).")
    try:
        out["palette"] = _analyse_palette(im)
    except Exception as e:                                  # noqa: BLE001
        notes.append(f"Palette : mesure impossible sur cette image ({e}).")
    return out


def _analyse_du_disque(did: str) -> dict:
    """Ouvre le recto STOCKÉ et le mesure. Le geste « Analyser » est à part de
    l'admission (plan D3 précisé T2) : on relance une mesure sans redéposer."""
    d = _dir_or_404(did)
    p = d / source_name(SIDES[0])
    if not p.is_file():
        raise HTTPException(
            404, "Aucun recto à mesurer sur ce jeu : déposez d'abord l'image "
                 "de la carte à reprendre, l'analyse porte sur le recto.")
    try:
        from PIL import Image
    except Exception as e:                                  # noqa: BLE001
        # §8 : dépendance absente -> 503 avec l'erreur LITTÉRALE. UNE PRÉCISION
        # QUE LA PREMIÈRE RÉDACTION S'ÉPARGNAIT : PIL n'est PAS une dépendance
        # optionnelle de ce laboratoire — la moitié des pièces l'importent, et
        # sans elle il n'y a pas d'application. Ce garde-fou couvre une
        # INSTALLATION CASSÉE, pas une option absente ; la doctrine 503 de §8,
        # elle, vise les dépendances vraiment facultatives, et T3 en aura une
        # (rembg local). Il est écrit ici parce qu'un 500 sur une installation
        # abîmée n'apprend rien à personne — et le test de la pièce le JOUE, en
        # retirant la bibliothèque du chargeur le temps d'une requête.
        raise HTTPException(503, f"L'analyse a besoin de la bibliothèque "
                                 f"d'images (PIL), introuvable ici : {e}")
    try:
        with Image.open(p) as im:
            im.load()
            rgb = im.convert("RGB")
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            409, f"Le recto stocké ne se relit pas ({e.__class__.__name__}). "
                 f"Déposez à nouveau l'image de la carte.")
    from . import core as cards_core
    doc = cards_core.read_deck(did)
    if not doc:
        raise HTTPException(
            409, "Le document de ce jeu ne se lit plus : sans son format, un "
                 "millimètre ne veut rien dire. Rouvrez le jeu.")
    geo = cards_core.geom_of(doc)
    return analyse_recto(rgb, geo)


# ── 6. le détourage IA opt-in (spec §7.1.3, plan D5) ────────────────────────
#
# LE BASCULEMENT EST CELUI DU PIPELINE SPRITE, ET C'EST LA SPEC QUI LE DIT
# (:507 « même basculement que le pipeline sprite ») : voie LOCALE d'abord si
# `rembg` s'importe, voie fal ensuite si une clé est enregistrée, rien sinon.
# `sprite_service` porte les deux moitiés (`_rembg_api` :199-209 pour fal,
# `_rembg_local_bytes` :219-221 pour le local) et `routes.py` porte le patron
# de disponibilité, DEUX FOIS (:710-716 et :3837-3873). On ne l'importe pas —
# règle 8, une pièce n'importe pas le module d'une voisine — on le RECOPIE,
# et on l'avoue ici.
#
# UN ÉCART ASSUMÉ AVEC `routes.py` : là-bas, une dépendance absente rend 400.
# Chez `cards`, §8 :581 dit 503 avec l'erreur littérale, et §8 fait loi dans
# ce domaine. L'écart est écrit ici pour qu'il ne se lise pas comme un oubli.
#
# CE QUE `rembg` EST VRAIMENT SUR CE POSTE, mesuré le 24/08 : ABSENT — ni du
# python de développement, ni du runtime embarqué de l'application, ni de
# `requirements.txt`. La voie locale est donc, aujourd'hui, du code qui ne
# s'exécute jamais en production ; le test de la pièce la joue avec un faux
# module injecté dans `sys.modules`, faute de quoi la moitié du basculement
# serait écrite et jamais éprouvée. L'empaqueter dans l'installeur est une
# dette nommée (transmis de phase 3).

REMBG_FAL_MODELE = "fal-ai/imageutils/rembg"
# La CLÉ de tarif, pas le tarif. Le chiffre vit dans `pricing.DEFAULTS` et
# nulle part ailleurs (§8 :583, « jamais recopié ») : ce qui est écrit ici est
# le nom sous lequel on va le LIRE.
PRIX_CLE = "rembg_api_usd"
# Le préfixe de fournisseur des refus (§8 :584). Il n'est pas décoratif : il
# dit OÙ aller regarder son compte quand un appel échoue.
PREFIXE_FAL = "fal.ai rembg"
PREFIXE_LOCAL = "rembg (local)"
# Le temps qu'on laisse à la relève du résultat. Le fournisseur a déjà rendu
# une URL à ce stade : ce qui reste est un téléchargement de quelques centaines
# de kilo-octets. CHIFFRE DE CONFORT, ET AUCUN TEST NE LE GARDE : le mesurer
# demanderait de tenir une socket ouverte plus longtemps que le délai,
# c'est-à-dire un test qui dure ce qu'il mesure. Dit plutôt que gardé.
FAL_TIMEOUT_S = 120
# LE PLAFOND DE COUVERTURE — la seconde moitié de la doctrine.
# « Un détourage qui garde TOUT, ou rien, n'est pas un détourage » : la moitié
# « rien » (couche transparente) sautait aux yeux, la moitié « tout » est
# pourtant le mode d'échec ORDINAIRE de rembg — aucun sujet trouvé, l'image
# ressort quasi intacte, l'utilisateur a payé, et P1 adopte sa carte entière
# comme « sujet détouré ».
# MESURÉ sur une carte de 630 x 880 : rien retiré = 1,00000 ; un cadre d'UN
# pixel retiré = 0,99456 ; un sujet posé à 4 px du bord = 0,97833 ; un sujet
# ovale ordinaire = 0,52181. Le plancher se pose donc entre les deux
# premiers : en dessous, il reste au moins le liséré d'un pixel de vrai
# retrait ; au-dessus, rien n'a été retiré nulle part.
# CE QU'IL FAUT SAVOIR AVANT DE LE DÉPLACER : c'est une PART, donc il dépend
# de la résolution — sur une trame au plafond d'import, un cadre d'un pixel ne
# pèse plus que 0,0008. Le chiffre reste juste pour ce qu'il attrape (une
# image RENDUE INTACTE, qui vaut exactement 1) et il est dit ici pour qu'on ne
# le prenne pas pour une mesure de qualité de détourage.
COUCHE_COUV_MAX = 0.995


def _sans_chemin(e) -> str:
    """L'erreur LITTÉRALE d'un fournisseur, moins les chemins absolus.

    Ce n'est pas de la cosmétique. `FalSeedanceClient.upload_image` lève
    `FileNotFoundError(f"Image not found: {image_path}")` — un chemin ABSOLU,
    donc le nom de compte de l'utilisateur, dans une réponse HTTP. C'est
    exactement l'incident de fuite de nom du gauntlet, et la jurisprudence
    T1 (`_store_image`, qui ne rend que `strerror`) s'applique telle quelle.
    Ce qui reste après le nettoyage est ce qui APPREND quelque chose : le
    motif du refus, pas l'endroit où le fichier se trouvait."""
    s = str(e).strip() or e.__class__.__name__
    # d'abord les chemins AVEC extension : eux peuvent contenir des espaces
    # (« C:\\Users\\...\\Mes documents\\x.png »), et un motif sans espace
    # s'arrêterait au milieu en laissant le nom de compte derrière lui.
    s = re.sub(r"[A-Za-z]:[\\/][^\r\n]*?\.(?:png|jpe?g|webp|tmp)\b", "…", s,
               flags=re.I)
    s = re.sub(r"[A-Za-z]:[\\/][^\s\"'<>]*", "…", s)
    # LE CHEMIN UNC, et il en dit plus qu'un chemin local : `\\SRV-PAIE\part`
    # porte le nom d'une MACHINE de l'entreprise et celui d'un partage. C'est
    # la forme ordinaire d'un poste de bureau, et elle manquait.
    s = re.sub(r"\\\\[^\s\"'<>]+", "…", s)
    # ... et le raccourci `~/`, qui n'est un raccourci que jusqu'à ce qu'un
    # outil le développe : il désigne le dossier de compte.
    s = re.sub(r"~[\\/][^\s\"'<>]*", "…", s)
    s = re.sub(r"/(?:home|Users|mnt|var|tmp|opt)/[^\s\"'<>]*", "…", s)
    return s[:300]


def _rembg_local_dispo() -> tuple:
    """(disponible, motif de l'absence). L'ORDRE DES TROIS QUESTIONS EST LA
    MESURE :

      1. `sys.modules` — s'il est déjà chargé, la réponse est instantanée (et
         c'est aussi ce qui rend la voie locale JOUABLE par un test, qui n'a
         pas de moteur ONNX à installer pour prouver un basculement) ;
      2. `find_spec` — présent sur le disque ? C'est une question de
         CATALOGUE, elle ne charge rien. Sur ce poste elle rend `None`, et
         c'est là que s'arrête le coût de la question ;
      3. l'import réel, seulement si le catalogue dit oui. Un `rembg` présent
         mais cassé (onnxruntime absent, DLL manquante) doit se dire
         « présent et ne se charge pas », pas « installé ».

    POURQUOI PAS DE MÉMO : l'import réussi peuple `sys.modules`, donc le
    second appel repasse par la porte 1. Un mémo n'aurait rien gagné et
    aurait figé une réponse que l'utilisateur peut changer en installant le
    paquet sans redémarrer."""
    import importlib
    import importlib.util
    if "rembg" in sys.modules:
        return True, ""
    try:
        spec = importlib.util.find_spec("rembg")
    except Exception as e:                                  # noqa: BLE001
        return False, f"le module rembg ne se cherche pas ici ({e})"
    if spec is None:
        return False, ("rembg n'est pas installé dans ce runtime — la voie "
                       "gratuite demande « pip install rembg »")
    try:
        importlib.import_module("rembg")
    except Exception as e:                                  # noqa: BLE001
        return False, f"rembg est présent mais ne se charge pas : {e}"
    return True, ""


def _fal_dispo() -> tuple:
    """(disponible, motif de l'absence). Une CLÉ enregistrée, rien de plus :
    on ne va pas interroger le fournisseur pour savoir s'il répondrait — ce
    serait un appel pour préparer un appel."""
    try:
        from app.config import settings
    except Exception as e:                                  # noqa: BLE001
        return False, f"les réglages ne se lisent pas ici ({e})"
    if getattr(settings, "FAL_KEY", ""):
        return True, ""
    return False, ("aucune clé fal enregistrée (Réglages -> Clés d'API) — la "
                   "voie payante ne peut pas partir")


def _prix_rembg():
    """Le tarif unitaire, LU dans la table de l'application. `None` quand la
    table ne le porte pas : l'écran écrit alors « tarif non tabulé » plutôt
    qu'un montant de repli, qui serait le prix d'autre chose.

    `isinstance(True, int)` vaut vrai en Python — un booléen glissé dans la
    table sortirait ici en « 1,0 $ ». Il est exclu explicitement."""
    try:
        from app.services import pricing
        v = (pricing.load() or {}).get(PRIX_CLE)
    except Exception:                                       # noqa: BLE001
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def ai_options() -> dict:
    """Ce que ce poste sait faire, et ce que ça coûte — AVANT le clic.

    D5, mot pour mot : « option absente = pas proposée (aucune erreur) ». Une
    route d'options qui refuserait quand rien n'est disponible obligerait
    l'écran à traiter une absence de capacité comme une panne, et à afficher
    un message rouge pour dire « cette fonction n'existe pas ici »."""
    loc, loc_motif = _rembg_local_dispo()
    fal, fal_motif = _fal_dispo()
    prix = _prix_rembg()
    # SANS PRIX TABULÉ, LA VOIE PAYANTE N'EST PAS OFFERTE. §8 :583 dit « prix
    # AVANT, depuis pricing.py » : un bouton payant sans chiffre n'est pas un
    # libellé honnête, c'est un écart de spec. La clé RESTE annoncée présente
    # (`fal` vaut vrai) — ce qui manque n'est pas la clé, c'est le tarif, et
    # les deux se réparent à des endroits différents.
    if fal and prix is None:
        fal_motif = ("la clé est enregistrée, mais le tarif du détourage n'est "
                     "pas dans la table (Réglages -> Tarifs et budget) : le "
                     "prix se dit AVANT l'appel, donc la voie payante n'est "
                     "pas proposée")
    voie = "local" if loc else ("fal" if (fal and prix is not None) else None)
    motif = ""
    if voie is None:
        motif = (f"Le détourage par IA n'est disponible sur ce poste par "
                 f"aucune des deux voies. Voie gratuite : {loc_motif}. Voie "
                 f"payante : {fal_motif}.")
    return {
        "local": loc,
        "fal": fal,
        "voie": voie,
        "gratuit": voie == "local",
        "prix_usd": prix,
        "devise": "USD",
        "modele_fal": REMBG_FAL_MODELE,
        "tarif_source": "la table de tarifs de l'application (Réglages -> "
                        "Tarifs et budget, pricing.json) — le fournisseur "
                        "facture directement",
        "local_motif": loc_motif,
        "fal_motif": fal_motif,
        "motif": motif,
    }


def _rembg_local(raw: bytes) -> bytes:
    """La voie GRATUITE, patron `sprite_service._rembg_local_bytes` (:219).
    La disponibilité a déjà été tranchée par la route : ici on appelle."""
    from rembg import remove
    return remove(raw)


async def _fal_upload(chemin: Path) -> str:
    """L'image part chez le fournisseur. PREMIÈRE des trois primitives
    réseau, et c'est délibéré qu'elles soient trois FONCTIONS DE MODULE : le
    test pose son espion exactement ici — au point de CONSOMMATION — au lieu
    de doubler la logique de `_rembg_fal` dans un faux."""
    from app.services.fal_service import FalSeedanceClient
    return await FalSeedanceClient.upload_image(chemin)


async def _fal_rembg(url: str) -> str:
    """L'appel PAYANT. Le dépliage de la réponse est celui de
    `sprite_service._rembg_api` (:203-208), recopié : deux formes de retour
    circulent chez ce fournisseur (`image.url` et `images[].url`)."""
    import fal_client
    res = await fal_client.subscribe_async(
        REMBG_FAL_MODELE, arguments={"image_url": url})
    out = ((res or {}).get("image") or {}).get("url") or next(
        (im.get("url") for im in (res or {}).get("images", [])
         if isinstance(im, dict) and im.get("url")), None)
    if not out:
        raise RuntimeError("le fournisseur n'a rendu aucune image")
    return str(out)


def _fal_lire(url: str) -> bytes:
    """La lecture, BORNÉE. `read()` sans argument ramène tout ce que le
    fournisseur veut bien envoyer : le refus « image trop grande » d'à côté ne
    parlait que des PIXELS, et il arrivait APRÈS que tout soit en mémoire. On
    demande donc UN OCTET DE PLUS que le plafond — s'il arrive, c'est qu'il y
    en avait trop, et on n'a pas eu besoin de tout lire pour le savoir. Le
    plafond est celui de l'admission : ce qui entre par une route ou par
    l'autre pèse pareil."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=FAL_TIMEOUT_S) as r:
        data = r.read(SRC_MAX_BYTES + 1)
    if len(data) > SRC_MAX_BYTES:
        raise RuntimeError(
            f"réponse trop lourde : au-delà de {SRC_MAX_BYTES // 1048576} Mo "
            f"d'octets, la relève s'arrête")
    return data


def _destination_sure(url: str) -> str:
    """"" si la destination est acceptable, sinon la RAISON du refus.

    LE SCHÉMA NE SUFFIT PAS, ET LE DOCSTRING D'AVANT VALAIT CONTRE LUI-MÊME :
    il disait « une réponse de fournisseur n'a pas à pouvoir désigner un
    fichier de cette machine », puis laissait passer
    `http://127.0.0.1:8765/api/settings` — l'API locale de cette application,
    qui n'a AUCUNE authentification. Une réponse mal formée, ou hostile,
    désignait donc le backend de l'utilisateur.

    CE QU'ON NE FAIT PAS, ET POURQUOI : on ne RÉSOUT aucun nom. Une résolution
    DNS est un appel réseau — dans une fonction dont tout l'objet est de
    décider s'il faut faire un appel réseau, et dans un banc qui n'en fait
    aucun. Un nom public qui pointerait vers 127.0.0.1 passerait donc : c'est
    une limite connue, écrite ici, et non un oubli. Ce que ce garde-fou
    attrape est le cas réel — une IP littérale de la machine ou du réseau
    local dans une réponse de fournisseur."""
    import ipaddress
    from urllib.parse import urlsplit
    try:
        hote = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return "adresse illisible"
    if not hote:
        return "aucun hôte"
    if hote == "localhost" or hote.endswith(".localhost"):
        return "la machine locale (localhost)"
    try:
        ip = ipaddress.ip_address(hote)
    except ValueError:
        return ""                       # un NOM : voir le pavé ci-dessus
    # L'ORDRE DES QUATRE FAMILLES EST CELUI DE LEUR PRÉCISION, et il n'est pas
    # cosmétique : `ipaddress` range 127.0.0.0/8, ::1, 169.254/16 et 0.0.0.0/8
    # DANS les réseaux privés — poser `is_private` en premier ferait dire
    # « un réseau privé (127.0.0.1) » de la boucle locale, et le mot juste est
    # ce qui apprend à l'utilisateur où sa réponse voulait aller. Le refus est
    # le même dans les quatre cas ; le diagnostic, non.
    if ip.is_loopback:
        return f"la boucle locale ({ip})"
    if ip.is_link_local:
        return f"le lien-local ({ip})"
    if ip.is_unspecified or ip.is_multicast or ip.is_reserved:
        return f"une adresse réservée ({ip})"
    if ip.is_private:
        return f"un réseau privé ({ip})"
    return ""


async def _fal_download(url: str) -> bytes:
    """La relève du résultat. L'URL VIENT DU DEHORS : son schéma ET sa
    destination sont gardés (`urlopen` sait ouvrir `file://`, et le reste du
    raisonnement est dans `_destination_sure`)."""
    u = str(url or "")
    if not re.match(r"https?://", u, re.I):
        raise RuntimeError(f"adresse de résultat inattendue : {u[:80]}")
    mauvaise = _destination_sure(u)
    if mauvaise:
        raise RuntimeError(
            f"destination interdite pour un résultat de fournisseur : "
            f"{mauvaise}. Un détourage se relève sur le web, pas sur cette "
            f"machine ni sur le réseau local.")
    return await asyncio.to_thread(_fal_lire, u)


async def _rembg_fal(chemin: Path) -> bytes:
    """La voie PAYANTE, en trois temps qui se nomment séparément.

    §8 :584 — « échec fournisseur -> erreur littérale + préfixe fournisseur ».
    Le préfixe seul ne suffit pas : « fal.ai rembg : 404 » ne dit pas si
    l'envoi a échoué ou si c'est le résultat qui ne se relève pas, et ce ne
    sont pas les mêmes gestes. Chaque temps porte donc son nom."""
    try:
        entree = await _fal_upload(chemin)
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            502, f"{PREFIXE_FAL} (envoi de l'image) : {_sans_chemin(e)}")
    try:
        sortie = await _fal_rembg(entree)
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            502, f"{PREFIXE_FAL} a refusé le détourage : {_sans_chemin(e)}")
    try:
        return await _fal_download(sortie)
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            502, f"{PREFIXE_FAL} (relève du résultat) : {_sans_chemin(e)}")


def _store_layer(did: str, name: str, data: bytes, prefixe: str) -> dict:
    """Ranger une couche RGBA rendue par un fournisseur.

    CE N'EST PAS `_store_image`, et la différence tient en une lettre : là-bas
    on convertit en RGB — ce qui TUE l'alpha, c'est-à-dire tout l'objet d'un
    détourage. Ici on convertit en RGBA et on MESURE ce qui a survécu.

    L'écriture est celle de T1 (brouillon nominatif + `replace` patient) : deux
    détourages simultanés sur le même jeu ne se disputent pas le fichier, et
    le GET ne voit jamais un PNG à moitié écrit."""
    from PIL import Image
    d = _dir_or_404(did, create=True)
    try:
        img = Image.open(io.BytesIO(data))
        w, h = img.size
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            502, f"{prefixe} n'a pas rendu une image lisible "
                 f"({e.__class__.__name__}) : rien n'est rangé.")
    if w * h > IMG_MAX_PIXELS:
        raise HTTPException(
            502, f"{prefixe} a rendu une image de {_mpx(w * h)} millions de "
                 f"pixels, au-delà du plafond de {_mpx(IMG_MAX_PIXELS)} "
                 f"millions : rien n'est rangé.")
    try:
        img.load()
        img = img.convert("RGBA")
    except Exception as e:                                  # noqa: BLE001
        raise HTTPException(
            502, f"{prefixe} a rendu une image qui ne se décode pas "
                 f"({e.__class__.__name__}) : rien n'est rangé.")
    # LE SUJET HÉRITE DE LA RÉDUCTION D'ADMISSION. Le recto est ramené à
    # `MAX_IMPORT_PX` en entrant ; le sujet, lui, ressortait à la taille que
    # le fournisseur voulait bien rendre — mesuré : un scan de 6000 px de côté
    # donnait un recto au plafond et un sujet resté à 6000. Deux tailles pour
    # la même carte, et P1 adoptant la plus lourde des deux. La réduction est
    # AVANT la mesure de couverture : le chiffre publié doit décrire le
    # fichier rangé, pas celui qu'on a reçu.
    if max(img.size) > MAX_IMPORT_PX:
        k = MAX_IMPORT_PX / float(max(img.size))
        img = img.resize((max(1, round(img.size[0] * k)),
                          max(1, round(img.size[1] * k))), Image.LANCZOS)
        w, h = img.size
    # CE QUI A SURVÉCU AU DÉTOURAGE, EN CLAIR — ET LA DOCTRINE VAUT DE SES
    # DEUX MOITIÉS. Un détourage rend une couche ; une couche entièrement
    # transparente n'est pas une couche, et une couche qui garde TOUT non
    # plus. La seconde est même le mode d'échec ORDINAIRE de rembg (aucun
    # sujet trouvé -> l'image ressort intacte) : l'utilisateur a payé, et P1
    # adopterait sa carte entière comme « sujet détouré ». C'est la phrase du
    # refus local, mot pour mot : « un détourage qui garde tout, ou rien,
    # n'est pas un détourage ».
    couverture = sum(img.getchannel("A").histogram()[128:]) / float(w * h)
    if couverture <= 0.0:
        raise HTTPException(
            502, f"{prefixe} a rendu une couche ENTIÈREMENT transparente : il "
                 f"n'y a aucun sujet dedans. Rien n'est rangé — une couche "
                 f"vide adoptée comme illustration ferait une carte blanche.")
    if couverture >= COUCHE_COUV_MAX:
        raise HTTPException(
            502, f"{prefixe} a rendu une couche qui garde "
                 f"{_fr(couverture * 100, 1)} % de l'image, au-delà du "
                 f"plafond de {_fr(COUCHE_COUV_MAX * 100, 1)} % : rien n'a "
                 f"été retiré. C'est ce que rend un détourage qui n'a trouvé "
                 f"aucun sujet. Rien n'est rangé — la carte entière adoptée "
                 f"comme « sujet » serait la carte de départ.")
    tmp = d / f"{name}.{uuid.uuid4().hex}.tmp"
    try:
        img.save(tmp, format="PNG", optimize=False)
        _replace_avec_patience(tmp, d / name)
    except OSError as e:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise HTTPException(
            409, f"La couche détourée n'a pas pu être écrite : "
                 f"{getattr(e, 'strerror', None) or e.__class__.__name__}. "
                 f"Relancez le détourage.")
    return {"w": w, "h": h, "bytes": (d / name).stat().st_size,
            "stamp": int(time.time() * 1000),
            "couverture": rnd(couverture, 4)}


# ── DEUX CLICS NE PAIENT PAS DEUX FOIS ──────────────────────────────────────
#
# MESURÉ : douze POST simultanés sur le même jeu donnaient DOUZE invocations
# du fournisseur et onze résultats jetés — un double-clic, deux onglets, ou un
# client qui réessaie, et la facture est multipliée sans que rien ne le dise.
# Le verrou BUSY de l'écran ne protège qu'UN onglet ; le contrat de la route,
# lui, doit tenir tout seul.
#
# LA COALESCENCE EST PAR JEU : un appel en vol pour `did`, tous les demandeurs
# suivants attendent CELUI-LÀ et reçoivent le même relevé. Deux jeux
# différents ne s'attendent pas.
#
# POURQUOI IL N'Y A PAS DE VERROU : asyncio est à un seul fil d'exécution, et
# il n'y a AUCUN `await` entre la lecture du dictionnaire et son écriture —
# la séquence est donc atomique du point de vue de la boucle. Un `asyncio.Lock`
# ici n'ajouterait rien qu'un objet à créer et une occasion de se tromper.
#
# CE QUI N'EST PAS COALESCÉ, ET C'EST UN CHOIX : deux clics SÉPARÉS dans le
# temps. Un « Redétourer » est une demande explicite — mettre le résultat en
# cache empêcherait de relancer après un changement de recto et rendrait le
# bouton menteur. La coalescence protège de l'ACCIDENT, pas de l'intention.
_EN_VOL: dict = {}


async def _coalesce(did: str, faire):
    """(résultat, `True` si c'est CETTE requête qui a payé).

    `shield` n'est pas décoratif : sans lui, un client qui referme son onglet
    pendant l'attente annulerait la tâche partagée — donc l'appel PAYANT —
    et les onze autres repartiraient avec une annulation. Un appel lancé se
    termine et se range ; c'est déjà facturé."""
    tache = _EN_VOL.get(did)
    if tache is None or tache.done():
        tache = asyncio.ensure_future(faire())
        _EN_VOL[did] = tache
        mien = True
    else:
        mien = False
    try:
        return await asyncio.shield(tache), mien
    finally:
        if _EN_VOL.get(did) is tache and tache.done():
            _EN_VOL.pop(did, None)


def _oublie_sujet(did: str) -> None:
    """Le sujet détouré est une PROPRIÉTÉ DU RECTO : il meurt avec lui.

    `effacements("recto")` remet `layers` à vide côté écran, mais le PNG,
    lui, restait sur le disque — et `GET /file/sujet_recto.png` continuait de
    servir le sujet de la carte PRÉCÉDENTE. P1 l'aurait adopté sans que rien
    ne l'annonce : une illustration qui n'a aucun rapport avec la carte
    qu'on vient d'importer."""
    try:
        (cap_dir(did) / SUJET_NAME).unlink()
    except OSError:
        pass                                # il n'y en avait pas : très bien


# ── 7. LE MANIFESTE DES COUCHES IMPORTÉES (T5, plan D7 amendé) ─────────────
#
# CE QUE CE MANIFESTE EST, ET CE QU'IL N'EST PAS. P9 sait partir d'un
# manifeste de couches — celui que les PEINTRES écrivent après avoir prouvé
# leur empilement. Les couches importées ne passeraient jamais cette preuve :
# elles n'ont jamais été empilées, elles ont été photographiées. Leur
# manifeste est donc le LEUR (`layers_{carte}_capture.json`, `side` et
# `source` valant tous deux « capture »), au MÊME schéma, avec une preuve
# d'une autre nature : l'EMPREINTE de chaque fichier et la COUVERTURE mesurée
# du sujet (T3). C'est ce qui fait de « une carte importée peut partir en 3D
# sans être reconstruite » (spec §7.1.6) un fait vérifiable.
#
# IL NE LISTE QUE CE QUI EXISTE (amendement D7 du 24/08). Deux fichiers, pas
# quatre : le SUJET détouré s'il a été produit (rôle `illustration`) et la
# FACE ENTIÈRE importée (rôle `recto`). Aucune tâche n'a jamais découpé de
# bordure ni de fond isolés — nommer un `cadre` ou un `fond-matiere` que rien
# ne porte serait inventer un fichier.
#
# OÙ IL ÉCRIT, ET POURQUOI CE N'EST PAS UNE ENTORSE. Les fichiers partent dans
# `decks/{did}/forge3d/`, le dossier de P9 — parce que c'est LÀ que P9 lit ses
# manifestes et ses couches, à un chemin qu'elle construit elle-même. Écrire
# ailleurs obligerait la voisine à apprendre le dossier de celle-ci : le
# couplage serait le même, dans l'autre sens, et en double (le manifeste ici,
# les PNG là). La règle 8 interdit d'IMPORTER le module d'une voisine — pas de
# déposer un fichier au format public qu'elle publie. Rien de ce que les
# peintres ont écrit n'est touché : leurs noms portent `_front`/`_back`, ceux-
# ci portent `_capture`.
#
# LES OCTETS SONT RENDUS AU FORMAT DE LA CARTE, pas recopiés tels quels. Une
# couche de P9 est une TOILE : `canvas_px` de large, fond perdu compris, et
# c'est sur cette convention que reposent la fenêtre UV du quad, la boîte en
# millimètres et le recadrage à la coupe d'un relief. La face importée est
# posée dans le rectangle de COUPE de cette toile ; le fond perdu reste
# TRANSPARENT — une capture n'en a pas, et en inventer un serait peindre.
P9_DIR = "forge3d"
CAPTURE_SIDE = "capture"
# LES DEUX RÔLES, DANS L'ORDRE OÙ ILS S'EMPILERAIENT (le sujet par-dessus la
# face). Jumeaux de `forge3d.py:CAPTURE_ROLES` — la parité est testée.
ROLE_RECTO = "recto"
ROLE_SUJET = "illustration"
MANIFEST_SCHEMA = "card-3d/layers-manifest@1"


def _ppm(dpi: float) -> int:
    """DPI -> pixels par mètre, arrondi demi-haut. COPIE LOCALE de
    `forge3d.py:_dpi_to_ppm` (lui-même copie de `face.py:dpi_to_ppm`) — règle
    8, zéro import pièce->pièce, et la parité est testée contre P9. Le pHYs
    d'une couche importée doit porter la MÊME densité que celui d'une couche
    peinte du même jeu : c'est la même toile."""
    return int(math.floor(float(dpi) / 0.0254 + 0.5))


def _card_label(raw) -> str:
    """`c01`, `c02`… — l'étiquette de carte qui nomme les fichiers de P9.
    COPIE du patron de `forge3d.py:_card_idx` (règle 8, parité testée) : une
    entrée non numérique ou négative retombe sur la première carte, JAMAIS une
    exception (spec §8)."""
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        v = 0.0
    if not math.isfinite(v):
        v = 0.0
    n = int(v)
    return f"c{(n if n >= 0 else 0) + 1:02d}"


def _sur_la_toile(im, geo):
    """La face importée, POSÉE dans le rectangle de coupe d'une toile de jeu.

    L'image est ramenée à `trim_px` puis collée à l'offset de fond perdu. La
    mise à l'échelle est NON UNIFORME quand le scan n'a pas le ratio du format
    — et c'est le choix assumé : une carte importée EST la carte, la déformer
    de quelques pour cent la fait tenir dans son format, alors qu'un
    letterbox y ajouterait des bandes que personne n'a photographiées. L'écart
    est PUBLIÉ (`ecart_ratio`, mesuré par l'analyse), jamais absorbé en
    silence."""
    from PIL import Image
    cw, ch = geo.canvas_px
    tw, th = geo.trim_px
    ox, oy = int(round(geo.bleed_off_px[0])), int(round(geo.bleed_off_px[1]))
    toile = Image.new("RGBA", (int(cw), int(ch)), (0, 0, 0, 0))
    face = im.convert("RGBA").resize((max(1, int(tw)), max(1, int(th))),
                                     Image.LANCZOS)
    toile.paste(face, (ox, oy))
    return toile


def _png_de_toile(img, ppm: int) -> bytes:
    """Les octets PNG d'une couche importée, pHYs COMPRIS.

    LE CHUNK EST ÉCRIT À LA MAIN, et deux voies plus simples ont été essayées
    puis écartées, mesurées :
      · `PngInfo.add(b"pHYs", ...)` est SILENCIEUSEMENT IGNORÉ par la
        bibliothèque (vérifié sur les octets : aucun `pHYs` dans le fichier) —
        elle n'écrit avant l'IDAT qu'une liste fermée de chunks connus ;
      · le paramètre `dpi=`, lui, écrit bien le chunk, mais avec SA constante
        (39,3701 pouces par mètre tronqués) et non 1/0,0254. Les deux tombent
        d'accord sur les densités du lab, et rien ne garantit qu'elles le
        restent : la densité publiée dans le manifeste doit être `_ppm()` À
        L'ENTIER, celle-là même que P9 écrit pour une couche peinte du même
        jeu, sans quoi une même toile porterait deux densités.
    Le chunk se glisse juste après l'IHDR, dont la taille est FIXE (13 octets
    de données) — c'est le seul endroit valide au regard du format, et c'est
    aussi celui où P9 pose le sien."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    brut = buf.getvalue()
    corps = struct.pack(">IIB", int(ppm), int(ppm), 1)
    chunk = (struct.pack(">I", len(corps)) + b"pHYs" + corps
             + struct.pack(">I", zlib.crc32(b"pHYs" + corps) & 0xFFFFFFFF))
    coupe = 8 + 25                       # signature + chunk IHDR (13 + 12)
    return brut[:coupe] + chunk + brut[coupe:]


def _ligne_couche(role: str, fname: str, data: bytes, img, geo) -> dict:
    """UNE ligne du manifeste, au schéma de `post_layers` — mesurée sur les
    OCTETS ÉCRITS, jamais sur l'intention.

    `z` reste VIDE et `module` dit « capture », pour les deux rôles : la
    Z_TABLE du CORE est le rang d'un peintre dans un empilement, et rien n'a
    empilé ces couches-ci. Leur donner le z de la couche homonyme laisserait
    croire à une provenance qu'elles n'ont pas.

    `bbox_mm` suit la convention EXACTE de P9 : origine au coin de TOILE (fond
    perdu compris), y vers le bas — c'est ce repère-là que `_layer_box_mm`
    sait retourner vers celui de la coupe."""
    w, h = img.size
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    cover = (w * h - alpha.histogram()[0]) / float(w * h) * 100.0
    toile_mm = (geo.trim_mm[0] + 2.0 * geo.bleed_mm,
                geo.trim_mm[1] + 2.0 * geo.bleed_mm)
    bbox_mm = None if bbox is None else [
        rnd(bbox[0] * toile_mm[0] / w, 2), rnd(bbox[1] * toile_mm[1] / h, 2),
        rnd(bbox[2] * toile_mm[0] / w, 2), rnd(bbox[3] * toile_mm[1] / h, 2)]
    return {"role": role, "z": [], "module": "capture", "file": fname,
            "mode": "isolee",
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "bbox_px": list(bbox) if bbox else None, "bbox_mm": bbox_mm,
            "coverage_pct": rnd(cover, 2)}


def _ecrit_manifeste(did: str, card_raw) -> dict:
    """Publie les couches importées au format de P9. Tout le travail disque et
    PIL de la route — appelé en `to_thread`."""
    from PIL import Image
    d = _dir_or_404(did)
    recto = d / source_name(SIDES[0])
    if not recto.is_file():
        raise HTTPException(
            404, "Aucun recto importé sur ce jeu : déposez d'abord l'image de "
                 "la carte à reprendre — un manifeste sans face n'a rien à "
                 "décrire.")
    from . import core as cards_core
    doc = cards_core.read_deck(did)
    if not doc:
        raise HTTPException(
            409, "Le document de ce jeu ne se lit plus : sans son format, une "
                 "couche importée n'a ni taille ni millimètres. Rouvrez le "
                 "jeu.")
    geo = cards_core.geom_of(doc)
    label = _card_label(card_raw)
    ppm = _ppm(geo.dpi)
    out = deck_dir(did) / P9_DIR
    out.mkdir(parents=True, exist_ok=True)

    sources = [(ROLE_RECTO, recto)]
    sujet = d / SUJET_NAME
    if sujet.is_file():
        # L'ORDRE EST CELUI DE L'EMPILEMENT : la face d'abord, le sujet
        # au-dessus. Le manifeste ne rend pas de z (voir `_ligne_couche`),
        # mais l'ordre de la liste, lui, est lisible et il ne coûte rien
        # d'être juste.
        sources.append((ROLE_SUJET, sujet))

    lignes: list = []
    couv_sujet = None
    ratios: list = []
    for role, chemin in sources:
        try:
            with Image.open(chemin) as im:
                im.load()
                brut = im.convert("RGBA")
        except Exception as e:                              # noqa: BLE001
            raise HTTPException(
                409, f"La couche « {role} » ne se relit pas sur le disque "
                     f"({e.__class__.__name__}). Redéposez l'image de la "
                     f"carte, puis relancez la publication.")
        ratios.append((role, brut.size))
        toile = _sur_la_toile(brut, geo)
        fname = f"{role}_{label}_{CAPTURE_SIDE}.png"
        data = _png_de_toile(toile, ppm)
        tmp = out / f"{fname}.{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_bytes(data)
            _replace_avec_patience(tmp, out / fname)
        except OSError as e:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise HTTPException(
                409, f"La couche « {role} » n'a pas pu être écrite : "
                     f"{getattr(e, 'strerror', None) or e.__class__.__name__}. "
                     f"Relancez la publication.")
        ligne = _ligne_couche(role, fname, data, toile, geo)
        lignes.append(ligne)
        if role == ROLE_SUJET:
            couv_sujet = ligne["coverage_pct"]

    # L'ÉCART DE RATIO, MESURÉ SUR LA FACE ELLE-MÊME (le même calcul que
    # `analyse_recto`, sur la même image — pas une valeur relue d'un document
    # qui a pu changer de format depuis).
    src_px = dict(ratios)[ROLE_RECTO]
    ratio_img = src_px[1] / float(src_px[0])
    ratio_fmt = geo.trim_mm[1] / float(geo.trim_mm[0])
    ecart = ratio_img / ratio_fmt - 1.0
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "deck": {"id": did, "name": doc.get("name")},
        "card": {"index": int(label[1:]) - 1, "label": label},
        "side": CAPTURE_SIDE,
        "source": CAPTURE_SIDE,
        "format": geo.fmt,
        "canvas_px": [int(geo.canvas_px[0]), int(geo.canvas_px[1])],
        "canvas_mm": [rnd(geo.trim_mm[0] + 2.0 * geo.bleed_mm, 3),
                      rnd(geo.trim_mm[1] + 2.0 * geo.bleed_mm, 3)],
        "size_mm": [geo.trim_mm[0], geo.trim_mm[1]],
        "bleed_mm": geo.bleed_mm,
        "phys_ppm": ppm,
        "layers": lignes,
        # ── LA PREUVE, ET SA DETTE, ÉCRITES ENSEMBLE ────────────────────
        # Pas de `proof.client` / `proof.backend` : il n'y a pas eu
        # d'empilement à re-jouer. Ce qui en tient lieu est l'empreinte de
        # chaque ligne (P9 la RECALCULE avant de construire) et la couverture
        # mesurée du sujet. La recomposition fond+sujet attend un fond isolé,
        # qu'aucune tâche n'a produit : la dette est NOMMÉE, pas simulée.
        "proof": {"capture": {
            "note": "couches importees : aucune preuve d'empilement de "
                    "peintres (rien ne les a empilees). L'empreinte de "
                    "chaque fichier et la couverture mesuree du sujet en "
                    "tiennent lieu.",
            "couverture_sujet_pct": couv_sujet,
            "recomposition": None,
            "recomposition_why": (
                "aucune couche de fond isolee n'existe : la recomposition "
                "fond+sujet attend qu'une tache en produise une"),
            "source_px": [int(src_px[0]), int(src_px[1])],
            "ecart_ratio": rnd(ecart, 4),
        }},
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    nom_manifeste = f"layers_{label}_{CAPTURE_SIDE}.json"
    tmp = out / f"{nom_manifeste}.{uuid.uuid4().hex}.tmp"
    try:
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        _replace_avec_patience(tmp, out / nom_manifeste)
    except OSError as e:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise HTTPException(
            409, f"Le manifeste n'a pas pu être écrit : "
                 f"{getattr(e, 'strerror', None) or e.__class__.__name__}. "
                 f"Relancez la publication.")
    return {"manifeste": nom_manifeste, "layers": manifest}


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
    if s == SIDES[0]:
        await asyncio.to_thread(_oublie_sujet, did)
    return {"side": s, **info}


@router.post("/analyse")
async def post_analyse(did: str):
    """Le relevé du recto STOCKÉ — gratuit, local, PIL pur, rejouable.

    ELLE NE PUBLIE RIEN. La route RÉPOND le relevé ; c'est `mod-capture.js`
    qui écrit `doc.capture` par la voie d'autosave unique (règle 12, plan D3).
    Une seule main sur le document, et le geste reste annulable côté écran.

    AUCUN CORPS N'EST LU, et c'est délibéré : tout ce qui se règle se règle
    dans le document (le format donne l'échelle) ou dans les constantes
    mesurées de ce fichier. Un POST à paramètres serait une surface de plus à
    nettoyer pour zéro service rendu.

    `to_thread` : la mesure prend 35 ms de CPU sur un scan de 630 x 880 et
    1,1 s sur une trame carrée AU PLAFOND D'IMPORT (mesuré — la première
    rédaction annonçait « 40 à 200 ms », qui était le petit bout de
    l'intervalle pris pour l'intervalle). Une seconde de calcul dans la boucle
    bloquerait toutes les autres requêtes : c'est justement le chiffre du
    plafond qui rend ce `to_thread` obligatoire, pas facultatif."""
    return await asyncio.to_thread(_analyse_du_disque, did)


@router.get("/ai-options")
async def get_ai_options(did: str):
    """Les voies de détourage disponibles sur CE poste, et leur prix.

    SERVIE MÊME SI LE JEU N'EXISTE PLUS, et c'est le précédent
    `frame.py:ai_models` : « un menu qui s'éteint parce qu'un deck a été
    supprimé est pire qu'inutile ». La question posée ici — « cette machine
    sait-elle détourer, et à quel prix ? » — n'a pas de deck pour réponse.
    Un identifiant MAL FORMÉ reste refusé : c'est la garde du domaine, et
    elle ne dépend d'aucun dossier.

    `to_thread` : la troisième porte de `_rembg_local_dispo` IMPORTE
    réellement le module, et un import de rembg charge un moteur ONNX —
    plusieurs secondes la première fois. Dans la boucle, ce serait toutes les
    autres requêtes en attente. (Sur ce poste la question s'arrête à la
    deuxième porte, qui ne coûte rien ; le `to_thread` est là pour le poste
    où rembg EST installé.)"""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    return await asyncio.to_thread(ai_options)


@router.post("/rembg")
async def post_rembg(did: str):
    """Le détourage OPT-IN du recto -> la couche « sujet » (spec §7.1.3).

    ELLE NE PUBLIE RIEN, comme `/analyse` : la route range le PNG et REND ce
    qu'elle a fait ; c'est `mod-capture.js` qui écrit
    `doc.capture.layers.sujet` par la voie d'autosave unique (règle 12,
    plan D3). Une seule main sur le document.

    LE PRIX EST RENDU AVEC LE RÉSULTAT, et c'est le patron du décor IA de P2 :
    la dépense se dit APRÈS avec le MÊME tarif qu'avant le clic. Deux chiffres
    différents de part et d'autre d'un clic sont le meilleur moyen de perdre
    la confiance de celui qui paie."""
    d = _dir_or_404(did)
    recto = d / source_name(SIDES[0])
    if not recto.is_file():
        raise HTTPException(
            404, "Aucun recto à détourer sur ce jeu : déposez d'abord l'image "
                 "de la carte à reprendre — le sujet s'isole sur le recto.")
    o = await asyncio.to_thread(ai_options)
    voie = o["voie"]
    if voie is None:
        # §8 :581 — 503 avec l'erreur LITTÉRALE. `routes.py` répond 400 sur le
        # même cas (:710-720) ; chez `cards`, §8 fait loi, et l'écart est
        # écrit en tête de section pour ne pas se lire comme un oubli.
        raise HTTPException(
            503, f"{o['motif']} L'analyse locale, elle, reste gratuite et "
                 f"sans fournisseur.")
    async def _faire() -> dict:
        if voie == "local":
            raw = await asyncio.to_thread(recto.read_bytes)
            try:
                data = await asyncio.to_thread(_rembg_local, raw)
            except Exception as e:                          # noqa: BLE001
                raise HTTPException(
                    502, f"{PREFIXE_LOCAL} a refusé le détourage : "
                         f"{_sans_chemin(e)}")
            prefixe = PREFIXE_LOCAL
        else:
            data = await _rembg_fal(recto)
            prefixe = PREFIXE_FAL
        return await asyncio.to_thread(_store_layer, did, SUJET_NAME, data,
                                       prefixe)

    info, mien = await _coalesce(did, _faire)
    return {"layer": SUJET_NAME, "voie": voie, "gratuit": voie == "local",
            "prix_usd": (o["prix_usd"] if voie == "fal" else None),
            "devise": o["devise"],
            # `coalesce` dit à CETTE réponse si elle a payé ou si elle a été
            # servie du travail d'une autre. L'écran n'en fait rien pour
            # l'instant ; le contrat, lui, est mesurable — et c'est ce qui
            # empêche la coalescence de disparaître sans bruit.
            "coalesce": not mien,
            **info}


@router.post("/manifeste")
async def post_manifeste(did: str, card: str | None = None):
    """Publie les couches importées au format de manifeste de P9 (T5, D7).

    POURQUOI UNE ROUTE, ET PAS « AU FIL DE L'EAU » APRÈS L'ANALYSE OU LE
    DÉTOURAGE — trois raisons mesurées, pas une préférence :

      1. LE MANIFESTE DÉPEND DU FORMAT DU JEU, pas seulement des images. La
         toile, les millimètres, la densité physique et jusqu'au nom des
         fichiers (`c01`) viennent de la géométrie du document, qui peut
         changer APRÈS l'import. Un manifeste écrit en douce à l'analyse
         serait périmé au premier changement de format, sans que personne
         l'ait demandé ; un geste explicite se REJOUE — exactement l'argument
         qui a déjà séparé « Analyser » de l'admission (T2).
      2. ON NE CHARGE PAS LA ROUTE QUI PAIE. `/rembg` est le seul geste
         facturé de la pièce ; lui ajouter deux rendus de toile et deux
         écritures disque allongerait la fenêtre pendant laquelle un résultat
         DÉJÀ payé peut échouer à se ranger. Le travail gratuit ne se greffe
         pas sur le travail cher.
      3. ELLE ÉCRIT CHEZ LA VOISINE. Déposer dans `decks/{did}/forge3d/` est
         un acte qui se voit et se déclenche, pas un effet de bord de deux
         autres routes.

    Comme `/analyse` et `/rembg` : elle range des fichiers et REND ce qu'elle
    a fait — c'est l'écran qui publie le document (règle 12, plan D3).

    `to_thread` : deux rendus LANCZOS à la taille de toile (1050 x 1500 px sur
    un poker à 300 DPI) plus deux écritures PNG — le même ordre de grandeur
    que l'analyse au plafond, donc le même traitement."""
    return await asyncio.to_thread(_ecrit_manifeste, did, card)


@router.get("/file/{nom}")
async def get_file(did: str, nom: str):
    """Un fichier du dossier de capture, par liste blanche de noms FINAUX.

    SOUS `/file/`, ET PAS À LA RACINE DU PRÉFIXE. `GET /{nom}` avalait
    d'avance TOUTE route GET future de la pièce : Starlette apparie dans
    l'ordre, et `/ai-options` (T3), `/rembg`, `/analyse` seraient tombés dans
    ce joker — avec, pour tout diagnostic, « Fichier inconnu dans le dossier
    de capture ». Mesuré sur les trois. Le piège de classe meurt ici plutôt
    que d'être documenté trois tâches plus loin."""
    n = _name_or_404(nom)
    d = _dir_or_404(did)
    p = d / n
    if not p.is_file():
        suite = ("lancez le détourage IA depuis la pièce Import."
                 if n == SUJET_NAME
                 else "déposez une image dans la pièce Import.")
        raise HTTPException(404, f"Aucune {_quoi(n)} sur ce jeu : {suite}")
    return _png(await asyncio.to_thread(p.read_bytes))
