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
de production), le SERVICE des fichiers qu'elle range, et l'ANALYSE LOCALE —
bordure, zones occupées, fond, palette, et la confiance CHIFFRÉE de chacune
(spec §7.1.2). Ce qui n'y est pas encore : le détourage IA opt-in (T3), les
adoptions chez les pièces voisines (T3/T4), le manifeste de couches (T5).

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

Routes (toutes relatives à /api/cards/{did}/capture) :

    POST /card?side=recto|verso   corps BRUT : la carte à importer
    GET  /file/{nom}              un fichier du dossier, par liste blanche
    POST /analyse                 mesure le recto STOCKÉ, rend le relevé
"""
from __future__ import annotations

import asyncio
import io
import math
import re
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from .contract import deck_dir, is_valid_did, rnd

# Règle 8 : signature imposée, chemins RELATIFS.
router = APIRouter()

__all__ = ["router", "SIDES", "SRC_MAX_BYTES", "IMG_MAX_PIXELS",
           "MAX_IMPORT_PX", "FILE_RE", "cap_dir", "source_name",
           "analyse_recto", "BORD_FRONT_MIN", "BORD_MIN_BORDS",
           "ZONE_BLOC_MM", "ZONE_SOUS", "ZONE_SPAN_MIN", "FOND_SEUIL_UNI",
           "PALETTE_N", "OPTION_IA"]

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
FILE_RE = re.compile(r"source_(?:recto|verso)\.png\Z")


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


def _name_or_404(nom: str) -> str:
    """Liste blanche. Voir `FILE_RE` : ni traversée, ni fichier temporaire."""
    n = str(nom or "")
    if not FILE_RE.fullmatch(n):
        raise HTTPException(
            404, "Fichier inconnu dans le dossier de capture : ce dossier ne "
                 "sert que " + " et ".join(source_name(s) for s in SIDES) + ".")
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
# AUCUN CHIFFRE DE CETTE SECTION N'EST DEVINÉ. Chacun porte la mesure qui l'a
# fixé, prise sur les cartes de synthèse du test (630 x 880 px pour un poker
# 63 x 88 mm, bordure de 26 px, trois cartouches à fort contraste).

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
# ... et le front doit DOMINER le reste du profil : un fondu régulier peut
# cumuler 40 de dénivelé sans qu'aucune marche ne se distingue.
# CE QU'IL PEUT ET NE PEUT PAS, MESURÉ : sur un profil qui plonge sur le quart
# du petit côté d'une carte, la marche MÉDIANE ne peut pas dépasser ~5 en L1
# (255 x 3 niveaux répartis sur ~157 rangées), donc le plancher absolu ci-dessus
# décide TOUJOURS avant ce rapport. Il ne mord que sur un profil COURT — une
# image minuscule, ou une carte sondée sur quelques rangées. Il reste parce que
# ce cas-là existe, et il est avoué non gardé dans l'en-tête du test.
BORD_FRONT_RATIO = 4.0
# UN SEUL BORD N'EST PAS UNE BANDE. Un liseré trouvé en haut et nulle part
# ailleurs est un élément de mise en page, pas une bordure de carte.
BORD_MIN_BORDS = 2
# La distance L1 sous laquelle deux couleurs se valent, pour le suivi de coin.
BORD_COIN_PROCHE = 60
# La fenêtre de recherche d'un rayon de coin : 15 % du petit côté (~9 mm sur
# 63) — largement au-delà de tout rayon de carte réel.
BORD_COIN_FENETRE = 0.15

# LA GRILLE DES ZONES, EN MILLIMÈTRES ET NON EN PIXELS. Le plan disait
# « ~32 px » ; mesuré, un bloc en pixels rend l'analyse DÉPENDANTE de la
# résolution du scan — la même carte à 1060 px et au plafond d'import
# n'aurait pas les mêmes boîtes. Un bloc de 1,5 mm vaut 25 px sur le scan
# (1060 px pour 63 mm) — les « ~32 px » du plan, à la résolution qu'il avait en
# tête — et il donne TOUJOURS une grille de ~42 colonnes, quelle que soit
# l'image. C'est aussi la hauteur d'une ligne de texte de carte : une zone plus
# fine qu'un bloc n'est pas une zone, c'est un trait.
ZONE_BLOC_MM = 1.5
# Les pixels de TRAVAIL par bloc. L'image est ramenée à `cols * ZONE_SOUS` de
# large avant la carte d'énergie : le coût devient constant (8 ms mesurés au
# lieu de ~1 s sur une image au plafond d'import) et le résultat cesse de
# dépendre de la finesse du scan. Huit pixels par bloc suffisent à voir une
# arête de lettre.
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

PALETTE_N = 6                      # « ~6 teintes dominantes » (plan D4)
PALETTE_TRAVAIL_PX = 256           # côté long du sous-échantillon de comptage


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


def _front(profil) -> dict | None:
    """La PREMIÈRE marche du profil : sa position (= l'épaisseur en px), sa
    hauteur, et le BRUIT du profil entier. Sans ce dernier, un fondu régulier
    finirait par cumuler assez de dénivelé pour se faire passer pour une
    bordure.

    LA PREMIÈRE, ET PAS LA PLUS HAUTE — la première écriture prenait le
    maximum, et une carte de synthèse à trois cartouches l'a démentie en une
    passe : un bandeau clair posé sur toute la largeur à 60 px du haut donne
    une marche de 540 quand la bordure n'en donne que 455, et l'analyse
    annonçait une bordure de 6 mm là où le test en avait posé 2,6. Une bordure
    est ce qui BORDE : le premier front en venant du bord, par définition."""
    if len(profil) < 3:
        return None
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
        return {"k": i + 1, "pic": v, "bruit": bruit, "largeur": large,
                "nettete": net}
    return None


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
    `40 - sqrt(40² - 27²)`. Le rayon ne se lit qu'au bord."""
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
    return float(vues[len(vues) // 2])


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
    vus = {nom: f for nom, f in fronts.items() if f}
    if len(vus) < BORD_MIN_BORDS:
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
    out = {"mm": rnd(ep_px * mm_par_px, 3),
           "color": _hexa(_couleur_bande(im, ep_px)),
           "confidence": rnd(conf, 3),
           "bords": sorted(vus),
           "regularite": rnd(regularite, 3),
           "nettete": rnd(nettete, 3),
           "epaisseurs_mm": [rnd(e * mm_par_px, 3) for e in sorted(eps)]}
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


def _analyse_zones(im, mm_par_px: float, bord_px: float, notes: list) -> list:
    from app.services.pbr_service import stats
    g, cols, rows, bloc_px = _grille(im, mm_par_px)
    s = stats(g)
    if s["span"] < ZONE_SPAN_MIN:
        notes.append(
            f"Zones : contraste local trop faible pour découper quoi que ce "
            f"soit (étendue {s['span']} sur 255, plancher {ZONE_SPAN_MIN}). "
            f"Aucune boîte n'est publiée — un seuil relatif sur une image "
            f"plate ne découpe que du bruit.")
        return []
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
        })
    return out


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
    motif = ("pourtour non uni" if uni < FOND_SEUIL_UNI
             else "couverture hors bornes")
    if uni < FOND_SEUIL_UNI:
        notes.append(f"Fond : pourtour uni à {_fr(uni, 3)} pour un plancher de "
                     f"{_fr(FOND_SEUIL_UNI)} — le détourage local refuse.")
    else:
        notes.append(f"Fond : le pourtour est uni ({_fr(uni, 3)}) mais la "
                     f"couleur retirée couvrirait {_fr(couv * 100, 1)} % de "
                     f"l'image, hors des bornes "
                     f"[{FOND_COUV_MIN:.0%}, {FOND_COUV_MAX:.0%}] — un "
                     f"détourage qui garde tout, ou rien, n'est pas un "
                     f"détourage.")
    return {"bg_failed": True,
            "motif": motif,
            "uniformite": rnd(uni, 3),
            "seuil": FOND_SEUIL_UNI,
            "couverture": rnd(couv, 3),
            "couverture_bornes": [FOND_COUV_MIN, FOND_COUV_MAX],
            "color": _hexa(m["cle"]),
            "option_ia": OPTION_IA}


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
    if abs(ecart) > 0.005:
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
        "border": None, "boxes": [], "bg": None, "palette": [],
        "notes": notes,
    }
    bord_px = 0.0
    try:
        out["border"], bord_px = _analyse_bordure(im, mm_par_px, notes)
    except Exception as e:                                  # noqa: BLE001
        notes.append(f"Bordure : mesure impossible sur cette image ({e}).")
    try:
        out["boxes"] = _analyse_zones(im, mm_par_px, bord_px, notes)
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
        # §8 : dépendance absente -> 503 avec l'erreur LITTÉRALE.
        raise HTTPException(503, f"L'analyse a besoin de la bibliothèque "
                                 f"d'images, absente ici : {e}")
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

    `to_thread` : la mesure prend de 40 à 200 ms de CPU selon la trame, et la
    boucle d'événements sert d'autres requêtes pendant ce temps."""
    return await asyncio.to_thread(_analyse_du_disque, did)


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
        cote = n[len("source_"):-len(".png")]
        raise HTTPException(404, f"Aucune capture {cote} sur ce jeu : déposez "
                                 f"une image dans la pièce Import.")
    return _png(await asyncio.to_thread(p.read_bytes))
