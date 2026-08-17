# -*- coding: utf-8 -*-
"""Card Forge — P6 « Textures (2D et PBR) ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/texture`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P6. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). Ce dont il a besoin vient de
`cards/contract.py` (géométrie, `deck_dir`) et de `cards/core.py` (lecture du
document) — jamais d'un voisin.

Les 8 maps se dérivent par `pbr_service.derive_maps` et se cuisent par
`pbr_service.bake_levels` : on RÉUTILISE, on ne réécrit pas. Aucune ligne de
`pbr_service.py` ni de `material_store.py` ne bouge.

────────────────────────────────────────────────────────────────────────────
CE QUI EST MESURÉ, ET POURQUOI ÇA COMPTE

La barre (Sorceress Material Forge) livre QUATRE maps — base color 1024²,
normale / rugosité / occlusion 512² — et n'écrit aucun chiffre sous aucune
d'elles. Ni métallique, ni hauteur, ni émission, ni ORM. Mesuré sur ses
propres fichiers téléchargés.

Ici : HUIT maps, jusqu'à 4096², hauteur et normale encodables en 16 bits, et
sous chacune une valeur qui n'est PAS la position d'un curseur. Le rapport est
recalculé après écriture, sur les octets PNG relus depuis le disque :
`map_report` (moyenne, amplitude utile, information portée, corrélation à la
luminance) et `effective_levels` (ce que le moteur glTF verra vraiment, car
`metalness = metallicFactor x texture.B`). La profondeur affichée est lue dans
l'IHDR du fichier, pas déduite d'un booléen de requête.

Conséquence assumée : une map qui ne porte rien le DIT (« uniforme — aucune
occlusion »). Compter huit maps dont trois sont plates serait un mensonge de
brochure ; le compte affiché est « informatives / total ».
────────────────────────────────────────────────────────────────────────────

Routes (toutes relatives à /api/cards/{did}/texture) :

    GET    /state          état complet : source, maps, mesures, réglages
    GET    /defaults       défauts et bornes de dérivation — de pbr_service
    POST   /source         corps BRUT : la carte rendue à l'échelle 1
    POST   /paper          corps BRUT : une image importée comme matière
    GET    /paper          cette image
    POST   /tile           corps BRUT : la tuile de matière, RE-MESURÉE ici
    GET    /tile           cette tuile, mesures inscrites dans ses chunks
    POST   /derive         JSON {derive, levels, res, bits16, square}
    GET    /map/{kind}     le PNG livrable (8 ou 16 bits)
    GET    /thumb/{kind}   la vignette 320 px de l'écran
    GET    /sheet          la planche des 8 maps, mesures écrites dessous
    GET    /manifest       le contrat du lot (espaces, DPI, SHA-256)
    DELETE /maps           efface les maps dérivées

────────────────────────────────────────────────────────────────────────────
CE QUI A ÉTÉ REPRIS APRÈS MESURE (le panneau a gagné ses deux duels, et les
deux critiques ont nommé les mêmes trous ; chacun a été reproduit avant d'être
bouché) :

  1. « 16 bits » était CREUX. `material_store._png16` duplique l'octet
     (v -> v*257) : mesuré 100,0 % de valeurs multiples de 257 sur
     3 080 192 pixels de height.png et 9 240 576 échantillons de normal.png.
     -> hauteur et normale recalculées en flottant à la résolution de sortie,
     quantifiées sur 16 bits, et la part de valeurs sous-niveau est MESURÉE
     sur le fichier (`sub`). Si elle est nulle, on écrit 8 bits et on le dit.
  2. La NORMALE n'était pas unitaire : |n| moyenne 0,9940, max 1,0075,
     1,52 % des pixels à plus de 5 % de l'unité et 0,3982 % à z<0 (impossible
     en espace tangent). -> recomposée par division en flottant, plancher de
     Z, et un rapport `unit_normal` sous la vignette.
  3. AUCUN chunk d'espace colorimétrique ni de densité : les 8 PNG ne
     portaient que IHDR/IDAT/IEND. -> `gAMA` + `sRGB` (basecolor, emissive),
     `gAMA` 1.0 (les six autres), `pHYs` calculé sur la géométrie du document
     — la moitié mesurable du cahier des charges (« 300 DPI avec fond perdu »)
     est enfin dans les octets, pas seulement à l'écran.
  4. Le lot n'avait AUCUN manifeste. -> `manifest.json` : conventions,
     dimensions physiques, espaces, empreintes SHA-256.
  5. `corr_lum` venait de `pbr_service.correlation`, qui réduit en blocs
     192x192 avant Pearson — vrai, mais la définition n'était pas à l'écran,
     et un lecteur qui recalcule à pleine résolution trouve autre chose
     (+0,994 contre +0,906 sur la hauteur). -> les DEUX sont publiées,
     étiquetées.
  6. `sub` SEUL laissait passer un faux 16 bits. Il attrape la duplication
     (v = octet x 257 -> 0,00 %) mais PAS le bourrage : une map écrite
     v = octet x 256 obtient `sub` = 99,61 %, un score excellent, alors que
     son octet faible vaut zéro partout — huit bits déguisés en seize.
     -> `_depth16` mesure AUSSI l'entropie de l'octet faible, et la
     profondeur 16 n'est écrite que si les DEUX mesures passent. Relevé sur
     le lot réel : normal.png octet faible 5,823 bits sur 8 (256 valeurs),
     height.png 7,554 bits.
  6 bis. La MOYENNE d'une map 16 bits se lisait sur huit. Pillow décode un
     PNG RVB 16 bits en mode « RGB » en gardant l'octet fort : la moyenne du
     canal R de normal.png sortait à 127,543/255 pour une vraie moyenne de
     127,326 — « moy 0,500 » affiché là où le fichier dit 0,499. Réduire
     soi-même n'y change rien (+0,217 de biais d'arrondi, mesuré) : seule une
     moyenne calculée SUR SEIZE BITS est juste. -> `_mean16`.
  6 ter. LE RACCORD DE TUILE : une mesure FAUSSE, et trente chiffres sans un
     octet derrière eux. L'écran divisait la marche au raccord par la marche
     MÉDIANE entre deux colonnes voisines. Sur un tissage, la médiane est prise
     à l'intérieur d'un fil, là où rien ne se passe, pendant que le raccord
     tombe sur un bord de fil : on comparait une transition franche à une
     non-transition. Mesuré sur la toile de jute — marche au raccord 40,27,
     PIRE marche interne 40,25 : le verdict publié était « 7,28x, couture
     visible », les octets disent « un bord de fil comme les 85 autres ».
     Trois des quatre échecs annoncés (« 26 / 30 ») étaient faux. Le quatrième
     était vrai et le reste : Marbre noir, 65,78 contre 6,63.
     -> la comparaison se fait au MAXIMUM des marches internes, sur les S-1
     paires de CHAQUE axe (`seam_report`) ; les deux vraies coutures sont
     corrigées à la racine dans les recettes (`marble` exigeait un nombre
     ENTIER de veines, `twill` un nombre PAIR de blocs) ; et la tuile
     s'EXPORTE (`POST /tile`), re-mesurée sur les octets reçus, sa mesure
     écrite dans ses chunks `tEXt`.
  7. La DENSITÉ n'était publiée que sur UN axe. `_physical` calcule bien
     `pHYs` sur les deux, mais un atlas CARRÉ posé sur une carte qui ne l'est
     pas donne des pixels rectangulaires : mesuré sur les octets, 1024² sur
     une carte 69 x 94 mm écrit pHYs 14841 x 10894 px/m, soit 377 x 277 DPI.
     L'écran annonçait « 377 DPI inscrits dans le chunk pHYs », et son
     avertissement « sous 300 DPI » ne se déclenchait pas — alors que la
     moitié verticale du livrable tombe à 277. -> `dpi_min` décide, la
     planche et le manifeste portent les deux axes et le verdict.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import struct
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from .contract import deck_dir, is_valid_did

router = APIRouter()

# ── contrat local ───────────────────────────────────────────────────────────
# Recopie assumée de `pbr_service.MAP_KINDS` : ce fichier doit pouvoir nommer
# ses routes sans importer le service au chargement. `test_cards_texture.py`
# compare les deux tuples — une divergence ferait rougir la suite.
MAP_ORDER: tuple[str, ...] = (
    "basecolor", "normal", "roughness", "metallic",
    "ao", "height", "emissive", "orm",
)
MAP_MODE = {"basecolor": "RGB", "normal": "RGB", "emissive": "RGB", "orm": "RGB",
            "roughness": "L", "metallic": "L", "ao": "L", "height": "L"}
BITS16_KINDS = ("height", "normal")          # les seules où la profondeur change le rendu

# L'espace colorimétrique de chaque map. DEUX maps portent de la couleur vue
# (sRGB), SIX portent des nombres (linéaire). Un PNG qui ne le dit pas oblige
# l'utilisateur à le savoir de tête : la base color importée en linéaire sort
# délavée, la roughness importée en sRGB sort trop lisse. On l'ÉCRIT dans les
# octets — chunk `sRGB` + `gAMA` 45455 d'un côté, `gAMA` 100000 (= 1.0) de
# l'autre. Mesuré avant correction : aucun des 9 PNG ne portait sRGB, gAMA ni
# iCCP ; la barre non plus (égalité, dans la faute).
SRGB_KINDS = ("basecolor", "emissive")
COLORSPACE = {k: ("sRGB" if k in SRGB_KINDS else "linéaire") for k in MAP_ORDER}

# Le plancher de Z d'une normale en espace tangent. Une normale dont le Z est
# nul ou négatif n'existe pas : elle pointe sous la surface. Le service dérive
# X et Y par Sobel et reconstruit Z par LUT 8 bits en écrêtant à 0 — d'où des
# vecteurs de longueur 1,44 et des pixels à z<0 (mesuré : |n| moyenne 0,9940,
# max 1,0075, 1,52 % des pixels à plus de 5 % de l'unité, 0,3982 % à z<0).
# Ici la normale est recomposée en FLOTTANT et divisée par sa longueur : |n|=1
# par construction, et Z ne descend jamais sous ce plancher (~87° de pente).
NORMAL_ZMIN = 0.05

RES_CHOICES: tuple[int, ...] = (1024, 2048, 4096)
DEFAULT_RES = 2048
THUMB_PX = 320
# Le plafond des vignettes re-servies à la table lumineuse. Au-delà, le
# ré-éclairage par pixel du navigateur (un million de pixels par image, quatre
# maps) cesse d'être interactif : c'est un plafond de confort, pas de qualité,
# et il est publié à côté du chiffre affiché.
LIT_MAX_PX = 768
# Le niveau de rugosité par défaut de l'ÉCRAN (vélin ivoire, sa matière par
# défaut). La route le reprend : deux tables pour un même réglage, c'est un
# curseur qui ment — et celle-ci écrivait une map constante (voir `_opts`).
DEFAULT_ROUGHNESS = 0.92
# Plafond de la résolution de TRAVAIL. Dériver à 4096² coûte huit convolutions
# cycliques sur 16,7 Mpx pour un gain invisible après rééchantillonnage : on
# dérive au plus à 2560 px et on rééchantillonne. Le chiffre est PUBLIÉ dans le
# rapport (`work_px`) — la barre, elle, dérive à 512 et ne le dit pas.
WORK_MAX = 2560
SRC_MAX_BYTES = 64 * 1024 * 1024
PAPER_MAX_PX = 2048
# La tuile de matière que l'écran exporte pour la faire RE-MESURER ici. Elle
# est carrée par définition (une tuile qui ne l'est pas ne se répète pas comme
# on l'a mesurée) et plafonnée : au-delà, le balayage des 2 x (S-1) paires de
# lignes coûte plus que ce qu'il apprend.
TILE_MIN_PX = 32
TILE_MAX_PX = 1024

# LA PLANCHE DE CONTRÔLE DÉCLARE SA PROPRE DENSITÉ. 11811 px/m = 300,0 DPI
# arrondi (11811 x 0,0254 = 299,9994) : la même constante que la pièce
# Impression écrit dans ses PNG. Ce n'est pas la densité de la CARTE — la
# planche n'est pas la carte — c'est la densité à laquelle cette image
# s'imprime, et sa taille en millimètres est écrite dans son chunk tEXt.
SHEET_DPI = 300
SHEET_PPM = 11811

_SHEET_BG = (18, 17, 16)
_SHEET_INK = (242, 239, 233)
_SHEET_SOFT = (138, 133, 125)
_SHEET_ACCENT = (240, 180, 41)
_SHEET_GREEN = (94, 200, 160)


# ── disque ──────────────────────────────────────────────────────────────────

def tex_dir(did: str, create: bool = False) -> Path:
    """`decks/<did>/texture/`. `deck_dir` porte déjà le double garde-fou
    (motif PUIS confinement) : on ne le refait pas, on s'appuie dessus."""
    d = deck_dir(did, create=create) / "texture"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _dir_or_404(did: str, create: bool = False) -> Path:
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    try:
        base = deck_dir(did, create=create)
    except ValueError:
        raise HTTPException(400, "Identifiant de deck invalide")
    if not base.is_dir():
        raise HTTPException(404, "Deck introuvable")
    return tex_dir(did, create=create)


def _kind_or_400(kind: str) -> str:
    """Liste blanche. Un nom de map est un identifiant, jamais un chemin :
    « ../../meta.json » ne peut pas exister dans MAP_ORDER."""
    k = str(kind or "").strip().lower()
    if k.endswith(".png"):
        k = k[:-4]
    if k not in MAP_ORDER:
        raise HTTPException(400, "Map inconnue: attendu " + ", ".join(MAP_ORDER))
    return k


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── lecture des octets ÉCRITS ───────────────────────────────────────────────

def png_depth(data: bytes) -> int:
    """Profondeur lue dans l'IHDR du fichier. C'est une MESURE : le drapeau
    `bits16` de la requête dit ce qu'on a demandé, l'IHDR dit ce qui est
    encodé. Les deux ont déjà divergé ailleurs dans ce dépôt."""
    if len(data) < 26 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0
    return int(data[24])


def _as_mode(img, kind: str):
    """Image ramenée au mode de sa map — Y COMPRIS depuis un PNG 16 bits.

    LE DÉFAUT QUE CECI CORRIGE, vu à l'écran avant d'être vu dans le code :
    `Image.convert("L")` depuis `I;16` ne divise pas, il ÉCRÊTE à 255. La
    carte de hauteur relue en 16 bits sortait donc à moy 0,969 / amplitude
    0 — et le rapport annonçait « uniforme — surface parfaitement plate »
    sous une map qui portait 231 niveaux d'amplitude utile. Mesuré :
    `stats` = mean 254.0, span 0 au lieu de mean 127.5, span 231.

    Le facteur est 257 (= 65535/255) et le `+0.5` ARRONDIT : `point` tronque,
    et depuis que la charge utile 16 bits est réelle, tronquer poserait un
    demi-niveau de biais entre la mesure de la map 16 bits et celle de la même
    map en 8 bits."""
    want = MAP_MODE[kind]
    if img.mode == want:
        return img
    if want == "L" and img.mode.startswith("I"):
        return img.convert("I").point(lambda v: v / 257.0 + 0.5, "L")
    return img.convert(want)


def _mean16(data: bytes) -> float | None:
    """Moyenne EXACTE du premier canal d'un PNG 16 bits, ramenée sur 0-255.

    LE DÉFAUT QUE CECI CORRIGE, trouvé en recalculant la moyenne à la main sur
    les octets : Pillow décode un PNG RVB 16 bits directement en mode « RGB »
    en gardant l'OCTET FORT (v >> 8). La moyenne du canal R de normal.png
    sortait donc à 127,543/255 alors que la vraie moyenne 16 bits vaut
    127,326/255 — le panneau affichait « moy 0,500 » là où le fichier dit
    0,499. Un demi-millième, mais c'est un chiffre affiché qui ne se retrouve
    pas dans les octets, et la règle de ce panneau ne souffre pas d'exception.

    Et RÉDUIRE d'abord ne le corrige pas : ramener soi-même à 8 bits par
    arrondi donne 127,543 aussi, parce que les parties fractionnaires ne sont
    pas équiréparties (mesuré : +0,217 de biais d'arrondi). La seule moyenne
    juste d'une map 16 bits se calcule SUR SEIZE BITS.

    Elle se calcule exactement et instantanément : moyenne(v) = 256 x
    moyenne(octet fort) + moyenne(octet faible), deux histogrammes de 256
    classes. `report_channel` mesure le canal 0 pour les deux maps concernées
    (hauteur : canal unique ; normale : canal R, le relief X).
    """
    from PIL import Image, ImageStat
    if png_depth(data) != 16:
        return None
    w, h, nch, pay = _png16_payload(data)
    if not pay:
        return None
    hi = Image.frombytes("L", (w, h), pay[0::2 * nch])
    lo = Image.frombytes("L", (w, h), pay[1::2 * nch])
    return (256.0 * ImageStat.Stat(hi).mean[0]
            + ImageStat.Stat(lo).mean[0]) / 257.0


def _span16(data: bytes) -> float | None:
    """Amplitude p95 − p5 du premier canal d'un PNG 16 bits, ramenée sur 255.

    LE DÉFAUT QUE CECI CORRIGE, trouvé en relisant les octets avec un décodeur
    écrit à part (zlib + défiltrage) : l'amplitude d'une map 16 bits était
    mesurée sur une VUE 8 BITS de la map, et pas la même vue selon la map.
    Pillow rend un RVB 16 bits en gardant l'OCTET FORT (troncature) tandis que
    `_as_mode` ramène un gris 16 bits par `v / 257 + 0,5` (arrondi). Deux
    réductions, deux résultats, sur les mêmes octets : mesuré sur une hauteur
    1504 x 2048, octet fort => 244, vue arrondie => 243 (le chiffre affiché),
    seize bits => 243,296. Un acheteur qui recalcule prend la tranche évidente
    (l'octet fort), trouve 244 en face d'un 243 affiché, et conclut au
    mensonge — exactement le reproche déjà encaissé sur la moyenne.

    Une map annoncée « lue sur 16 bits » doit voir SON AMPLITUDE lue sur seize
    bits elle aussi : centiles sur les 65 536 classes réelles, puis division
    par 257 pour rester sur l'échelle 0-255 que le panneau affiche. Exact,
    reproductible, et une seule règle pour les deux maps concernées.

    Coût : un histogramme de 256 classes pour situer l'octet fort, puis UN
    histogramme masqué par centile pour départager l'octet faible — quatre
    passes Pillow, aucune boucle par pixel, y compris sur les 16,7 Mpx d'une
    normale 4096².
    """
    from PIL import Image
    if png_depth(data) != 16:
        return None
    w, h, nch, pay = _png16_payload(data)
    if not pay:
        return None
    im_hi = Image.frombytes("L", (w, h), pay[0::2 * nch])
    im_lo = Image.frombytes("L", (w, h), pay[1::2 * nch])
    hst = im_hi.histogram()
    n = float(w * h)

    def centile(f: float) -> int:
        cible = f * n
        acc = 0
        for v in range(256):
            if acc + hst[v] >= cible:
                # la classe d'octet fort qui contient le centile : on ne
                # départage l'octet faible que là, sur ces pixels-là.
                reste = cible - acc
                masque = im_hi.point(lambda x, v=v: 255 if x == v else 0, "L")
                fin = im_lo.histogram(masque)
                sous = 0
                for u in range(256):
                    sous += fin[u]
                    if sous >= reste:
                        return v * 256 + u
                return v * 256 + 255
            acc += hst[v]
        return 65535
    return round((centile(0.95) - centile(0.05)) / 257.0, 2)


def _sd16(data: bytes) -> float | None:
    """Écart-type du premier canal d'un PNG 16 bits, ramené sur 0-255.

    Même canal, même échelle et même précision que `_mean16` : une moyenne lue
    sur seize bits à côté d'un écart-type lu sur huit donnerait deux chiffres
    qui ne parlent pas de la même image. La somme des carrés passe par une
    réduction BOX en flottant (accumulateurs double côté Pillow) sur les
    valeurs CENTRÉES — mesuré contre un décodeur indépendant : 26,55 sur la
    normale et 81,48 sur la hauteur d'un lot 2048², au centième près.
    """
    from PIL import Image, ImageMath
    if png_depth(data) != 16:
        return None
    w, h, nch, pay = _png16_payload(data)
    if not pay:
        return None
    moy = _mean16(data)
    if moy is None:
        return None
    f = ImageMath.lambda_eval(
        lambda k: (k["float"](k["h"]) * 256.0 + k["float"](k["l"])) / 257.0 - moy,
        h=Image.frombytes("L", (w, h), pay[0::2 * nch]),
        l=Image.frombytes("L", (w, h), pay[1::2 * nch]))
    return round(math.sqrt(max(0.0, _mean_f(
        ImageMath.lambda_eval(lambda k: k["a"] * k["a"], a=f)))), 2)


def _levels16(data: bytes) -> int | None:
    """Le NOMBRE DE VALEURS DISTINCTES du premier canal d'un PNG 16 bits.

    C'est la mesure qu'un utilisateur peut relier à ce qu'il voit : un dégradé
    doux se découpe en marches quand le fichier ne porte que quelques dizaines
    de niveaux, quel que soit ce que dit son en-tête. Un conteneur 16 bits
    authentique mais presque vide (mesuré ailleurs : 66 niveaux sur 65 536)
    coûte deux octets par point pour un relief qui tient sous sept bits.

    Exact, pas échantillonné : les valeurs sont comptées par bandes de deux
    millions de points, avec une table de présence de 65 536 cases. Coût
    mesuré : 0,11 s sur 12,6 millions de points."""
    from PIL import Image
    if png_depth(data) != 16:
        return None
    _w, _h, nch, pay = _png16_payload(data)
    if not pay:
        return None
    hi = pay[0::2 * nch]
    lo = pay[1::2 * nch]
    n = len(hi)
    if not n:
        return None
    buf = bytearray(2 * n)
    buf[0::2] = hi
    buf[1::2] = lo
    vus = bytearray(65536)
    band = 1 << 21
    i = 0
    while i < n:
        k = min(band, n - i)
        im = Image.frombytes("I;16B", (k, 1), bytes(buf[2 * i:2 * (i + k)]))
        for _cnt, v in (im.convert("I").getcolors(65537) or []):
            vus[v] = 1
        i += k
    return sum(vus)


def _levels_canal(kind: str, img, raw16: bytes | None) -> int:
    """Les valeurs distinctes DU CANAL MESURÉ — le même que la moyenne, pour
    qu'un lecteur qui refait le calcul retombe sur le chiffre affiché."""
    if raw16 is not None:
        v = _levels16(raw16)
        if v is not None:
            return v
    from app.services import pbr_service as pbr
    ch, _ = pbr.report_channel(kind, img)
    return sum(1 for c in ch.histogram() if c)


def _sd_canal(kind: str, img, raw16: bytes | None) -> float:
    """L'ÉCART-TYPE DU CANAL MESURÉ, sur 255.

    CE QUE CELA CORRIGE. Le panneau publiait une moyenne et une amplitude
    p95 − p5, et rien entre les deux : une map dont 90 % de la surface est
    constante et dont 10 % saute d'un bord à l'autre affiche la même amplitude
    qu'une map qui varie partout. L'écart-type sépare les deux cas, il se lit
    sur le MÊME canal que la moyenne (`report_channel`) et il se recalcule sur
    les octets comme le reste."""
    if raw16 is not None:
        v = _sd16(raw16)
        if v is not None:
            return v
    from PIL import ImageStat
    from app.services import pbr_service as pbr
    ch, _ = pbr.report_channel(kind, img)
    return round(float(ImageStat.Stat(ch).stddev[0]), 2)


def _read_map(path: Path, kind: str):
    """Le PNG relu depuis le disque, plus sa taille et sa profondeur RÉELLES."""
    from PIL import Image
    data = path.read_bytes()
    img = Image.open(io.BytesIO(data))
    img.load()
    return _as_mode(img, kind), len(data), png_depth(data), img.size


# ── PNG : les chunks, écrits ET relus ───────────────────────────────────────
#
# CE QUE CECI CORRIGE, mesuré sur les fichiers livrés AVANT :
#   basecolor.png -> ['IHDR', 'IDAT'…, 'IEND'].  Rien d'autre. Sur les 8.
# Donc : aucune dimension physique (un PNG sans `pHYs` entre à 72 DPI dans
# tout outil d'impression, quelle que soit la promesse de l'écran), et aucun
# espace colorimétrique (deux maps sRGB et six linéaires dans le même lot,
# rien dans les octets ne les distingue). Les deux se réparent au même
# endroit : trois chunks glissés juste après l'IHDR.

def _chunk(tag: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + tag + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))


def png_chunks(data: bytes) -> list[str]:
    """Les tags du fichier, dans l'ordre. « Le PNG porte-t-il pHYs ? » est une
    question à laquelle on répond sur les octets, pas sur l'intention."""
    out: list[str] = []
    if len(data) < 12 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return out
    i = 8
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8].decode("ascii", "replace")
        out.append(tag)
        if tag == "IEND":
            break
        i += 12 + ln
    return out


def png_phys(data: bytes) -> tuple[int, int] | None:
    """Le `pHYs` relu : (pixels par mètre en X, en Y) ou None. Unité 1 = mètre
    (la seule que le format définit) ; une unité 0 signifie « rapport
    d'aspect », donc pas une densité — on rend None."""
    if len(data) < 12 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i = 8
    while i + 12 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        if tag == b"pHYs" and ln >= 9:
            x, y, unit = struct.unpack(">IIB", data[i + 8:i + 17])
            return (x, y) if unit == 1 else None
        if tag == b"IEND":
            break
        i += 12 + ln
    return None


def _text(key: str, value: str) -> bytes:
    """`tEXt` — Latin-1 par le format. On translittère plutôt que de risquer
    un fichier illisible : « linéaire » -> « lineaire »."""
    import unicodedata
    v = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore")
    return _chunk(b"tEXt", key.encode("ascii") + b"\x00" + v)


def _meta_chunks(kind: str, ppm: tuple[int, int] | None, note: str) -> bytes:
    """gAMA + sRGB + pHYs + tEXt, dans l'ordre imposé par le format (tous
    avant le premier IDAT).

    AUCUN CHUNK NE NOMME QUI A ÉCRIT LE FICHIER. Le lot sortait avec un
    `Software` qui portait le nom de l'outil et son numéro de chantier interne
    dans les huit PNG, la planche et la tuile — une signature de producteur
    recopiée dans chaque livrable, que l'acheteur transmet ensuite sans le
    savoir. Ce qui reste est TECHNIQUE et lui sert : espace colorimétrique,
    densité physique, convention d'empaquetage, mesures du fichier."""
    out = b""
    if kind in SRGB_KINDS:
        out += _chunk(b"gAMA", struct.pack(">I", 45455))     # 1/2.2
        out += _chunk(b"sRGB", bytes([0]))                   # intention perceptive
    else:
        out += _chunk(b"gAMA", struct.pack(">I", 100000))    # 1.0 = linéaire
    if ppm:
        out += _chunk(b"pHYs", struct.pack(">IIB", int(ppm[0]), int(ppm[1]), 1))
    out += _text("Comment", note)
    return out


def _with_meta(data: bytes, kind: str, ppm, note: str) -> bytes:
    """Les chunks glissés juste après l'IHDR (13 octets de corps + 12)."""
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return data
    cut = 8 + 25
    return data[:cut] + _meta_chunks(kind, ppm, note) + data[cut:]


# ── 16 bits : l'écrire pour de vrai, et le MESURER ──────────────────────────
#
# LE DÉFAUT QUE CECI CORRIGE — le plus cher du panneau, et le plus ironique.
# `material_store._png16` duplique chaque octet (v -> v*257) : conteneur 16
# bits, charge utile 8 bits. Mesuré sur le fichier d'avant : octet fort ==
# octet faible sur 3 080 192 / 3 080 192 pixels de height.png et sur
# 9 240 576 / 9 240 576 échantillons de normal.png, soit 100,0 % de valeurs
# multiples de 257. Le badge « 16 bits » était donc le SEUL chiffre du panneau
# qui n'avait jamais été confronté aux octets.
#
# Ici la hauteur et la normale sont recalculées en FLOTTANT à la résolution de
# sortie (le rééchantillonnage produit de vraies valeurs sous-niveau) puis
# quantifiées sur 16 bits. Et on mesure : `sub` = part des valeurs qui ne sont
# PAS multiples de 257. 0 % = conteneur creux, et alors on écrit 8 bits en le
# disant, plutôt que de doubler le poids du livrable pour rien.

def _f_channel(img, size, flt=None):
    """Un canal L ramené en flottant À LA TAILLE DE SORTIE. C'est ici que naît
    la précision sous-niveau : interpoler 8 bits en flottant donne de vraies
    valeurs intermédiaires, que 8 bits ne peuvent plus porter."""
    from PIL import Image
    f = img.convert("F")
    if f.size != tuple(size):
        f = f.resize(tuple(size), flt or Image.BICUBIC)
    return f


def _unit_normal(nx, ny):
    """(X, Y, Z) unitaires, en flottant, depuis les canaux R/V du service.

    Décodage du service : x = (R-128)/127, y = (G-128)/127. On impose ensuite
    x² + y² + z² = 1 par DIVISION (pas par écrêtage), avec z planchonné à
    NORMAL_ZMIN : |n| = 1 partout, z > 0 partout."""
    from PIL import ImageMath
    z2 = NORMAL_ZMIN * NORMAL_ZMIN
    x = ImageMath.lambda_eval(lambda k: (k["a"] - 128.0) / 127.0, a=nx)
    y = ImageMath.lambda_eval(lambda k: (k["a"] - 128.0) / 127.0, a=ny)
    q = ImageMath.lambda_eval(lambda k: k["x"] * k["x"] + k["y"] * k["y"], x=x, y=y)
    z = ImageMath.lambda_eval(
        lambda k: (((1.0 - k["q"]) + z2 + abs((1.0 - k["q"]) - z2)) / 2.0) ** 0.5,
        q=q)
    ln = ImageMath.lambda_eval(lambda k: (k["q"] + k["z"] * k["z"]) ** 0.5, q=q, z=z)
    unit = lambda c: ImageMath.lambda_eval(                       # noqa: E731
        lambda k: k["c"] / k["l"], c=c, l=ln)
    return unit(x), unit(y), unit(z)


def _clip_f(f, hi: float):
    """Flottant borné à [0, hi]. INDISPENSABLE, et mesuré : BICUBIC dépasse
    (overshoot) des deux côtés, et `convert(..., "I")` ne borne RIEN — un
    -1284 est ressorti à 64252 après extraction des deux octets faibles,
    c'est-à-dire un pixel noir rendu presque blanc. Le défaut s'est vu à la
    corrélation (0,906 -> 0,785) avant d'être visible à l'œil."""
    from PIL import ImageMath
    hd = ImageMath.lambda_eval(lambda k: (k["v"] + abs(k["v"])) / 2.0, v=f)
    return ImageMath.lambda_eval(
        lambda k: (k["v"] + hi - abs(k["v"] - hi)) / 2.0, v=hd)


def _to_l(f):
    """Flottant 0..255 -> octet, ARRONDI. `convert("L")` tronque (mesuré :
    254,6 -> 254) : sans le +0,5, un demi-niveau de biais s'installe partout."""
    from PIL import ImageMath
    return ImageMath.lambda_eval(lambda k: k["convert"](k["v"] + 0.5, "L"),
                                 v=_clip_f(f, 255.0))


def _to_be16(f) -> bytes:
    """Flottant 0..65535 -> plan d'octets big-endian, arrondi et borné."""
    from PIL import ImageMath
    i32 = ImageMath.lambda_eval(lambda k: k["convert"](k["v"] + 0.5, "I"),
                                v=_clip_f(f, 65535.0))
    raw = i32.tobytes()                       # int32 natif, petit-boutiste
    out = bytearray(len(raw) // 2)
    out[0::2] = raw[1::4]                     # octet fort
    out[1::2] = raw[0::4]                     # octet faible
    return bytes(out)


def _enc8(f):
    """n (-1..1) -> octet, convention glTF : c = (n + 1) / 2."""
    from PIL import ImageMath
    return _to_l(ImageMath.lambda_eval(lambda k: (k["v"] + 1.0) * 127.5, v=f))


def _enc16(f) -> bytes:
    """n (-1..1) -> deux octets big-endian, même convention."""
    from PIL import ImageMath
    return _to_be16(ImageMath.lambda_eval(lambda k: (k["v"] + 1.0) * 32767.5,
                                          v=f))


def _level16(f) -> bytes:
    """0..255 (flottant) -> deux octets big-endian sur toute l'échelle."""
    from PIL import ImageMath
    return _to_be16(ImageMath.lambda_eval(lambda k: k["v"] * 257.0, v=f))


def _png16(planes: list[bytes], size: tuple[int, int]) -> bytes:
    """PNG profondeur 16, gris (1 plan) ou RVB (3 plans), filtre None.

    Filtre None assumé : le fichier se relit à la tranche (`payload[0::2]` =
    octets forts) et donc se VÉRIFIE en trente secondes, ce qui est tout
    l'objet du badge. Pillow ne sait de toute façon pas écrire du RVB 16 bits.
    """
    w, h = size
    n = w * h
    nch = len(planes)
    body = bytearray(n * 2 * nch)
    for c, plane in enumerate(planes):
        body[2 * c::2 * nch] = plane[0::2]
        body[2 * c + 1::2 * nch] = plane[1::2]
    stride = w * 2 * nch
    raw = bytearray((stride + 1) * h)
    for y in range(h):
        raw[y * (stride + 1)] = 0                       # filtre None
        raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)] = \
            body[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 16, 2 if nch == 3 else 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + _chunk(b"IEND", b""))


def _sub_pct(data: bytes) -> float:
    """La MESURE du 16 bits, relue sur les octets du fichier : part des
    échantillons dont la valeur n'est PAS un multiple de 257.

    0,0 % = chaque valeur vaut octet x 257, c'est-à-dire un octet dupliqué :
    conteneur 16 bits, charge utile 8 bits. > 0 % = de la précision que 8 bits
    ne peuvent pas porter. (v est multiple de 257 <=> octet fort == octet
    faible : 257k s'écrit k,k en base 256.)"""
    return _depth16(data)["sub"]


def _depth16(data: bytes) -> dict:
    """LES DEUX MESURES du 16 bits, relues sur les octets, parce qu'UNE SEULE
    LAISSE PASSER UN FAUX.

    · `sub` — part des valeurs qui ne sont pas multiples de 257. Attrape la
      DUPLICATION (v = octet x 257) : elle tombe alors à 0,00 %.
    · `low_bits` / `low_vals` — entropie de Shannon et nombre de valeurs
      distinctes de l'OCTET FAIBLE. Attrape le BOURRAGE (v = octet x 256, donc
      octet faible constant) : `low_bits` tombe alors à 0,000 et `low_vals` à 1.

    POURQUOI LES DEUX. Mesuré : une map dont chaque valeur vaut octet x 256
    donne `sub` = 99,61 % — un score EXCELLENT sous la seule première mesure —
    alors qu'elle ne porte que huit bits, l'octet faible valant zéro partout.
    Un conteneur creux se cache donc derrière `sub` seul. Les deux ensemble ne
    laissent aucune fenêtre : `sub` = 0 => octet dupliqué, `low_bits` = 0 =>
    octet faible constant, et il n'y a pas d'autre façon d'écrire huit bits
    dans seize.

    Les deux se calculent sur des histogrammes de 256 classes — donc exacts et
    instantanés, même sur les 50 millions d'échantillons d'une normale 4096².
    """
    from PIL import Image, ImageChops
    out = {"sub": 0.0, "low_bits": 0.0, "low_vals": 0}
    if png_depth(data) != 16:
        return out
    w, h, nch, payload = _png16_payload(data)
    if not payload:
        return out
    m = len(payload) // 2
    # deux plans de la forme (w x canaux, h) — surtout pas une image d'une
    # seule ligne : à 4096², 100 Mpx dépassent le garde-fou « bombe de
    # décompression » de Pillow et sortent un avertissement dans les tests.
    hi = Image.frombytes("L", (w * nch, h), payload[0:2 * m:2])
    lo = Image.frombytes("L", (w * nch, h), payload[1:2 * m:2])
    zero = ImageChops.difference(hi, lo).histogram()[0]
    hst = lo.histogram()
    n = float(sum(hst) or 1)
    ent = 0.0
    for c in hst:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    out["sub"] = round(100.0 * (m - zero) / float(m or 1), 2)
    out["low_bits"] = round(ent, 3)
    out["low_vals"] = sum(1 for c in hst if c)
    return out


def _png16_payload(data: bytes) -> tuple[int, int, int, bytes]:
    """Les octets d'image d'un PNG 16 bits À FILTRE NONE, débarrassés de
    l'octet de filtre de chaque ligne. Rend (w, h, canaux, octets big-endian).
    Rend b"" si une ligne porte un filtre : ce lecteur ne prétend pas lire
    tous les PNG, seulement CEUX QU'ON ÉCRIT — c'est le point."""
    from PIL import Image
    if len(data) < 33:
        return (0, 0, 0, b"")
    w, h, bits, ct = struct.unpack(">IIBB", data[16:26])
    if bits != 16 or ct not in (0, 2):
        return (0, 0, 0, b"")
    nch = 3 if ct == 2 else 1
    idat = bytearray()
    i = 8
    while i + 12 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        if tag == b"IDAT":
            idat += data[i + 8:i + 8 + ln]
        elif tag == b"IEND":
            break
        i += 12 + ln
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        return (0, 0, 0, b"")
    stride = w * 2 * nch
    if len(raw) != (stride + 1) * h:
        return (0, 0, 0, b"")
    if any(raw[y * (stride + 1)] for y in range(h)):
        return (w, h, nch, b"")                 # une ligne filtrée : on renonce
    lignes = Image.frombytes("L", (stride + 1, h), raw)
    return (w, h, nch, lignes.crop((1, 0, stride + 1, h)).tobytes())


# ── rééchantillonnage hors carré ────────────────────────────────────────────
# `pbr_service.resize_maps` impose res x res (atlas). Quand l'écran demande le
# FORMAT DE LA CARTE, on applique la même politique de filtre — LANCZOS pour ce
# qui est vu, BICUBIC pour les maps de données. La normale et la hauteur ne
# passent PAS par ici : elles sont refaites en flottant par `_vector_maps`,
# seule façon d'obtenir une normale unitaire et une vraie charge utile 16 bits.

def _resize_rect(maps: dict, size: tuple[int, int]) -> dict:
    from PIL import Image
    out = {}
    for kind, img in maps.items():
        if img.size == size:
            out[kind] = img
            continue
        flt = Image.LANCZOS if kind in ("basecolor", "emissive") else Image.BICUBIC
        out[kind] = img.resize(size, flt)
    return out


def _vector_maps(work_maps: dict, size: tuple[int, int], bits16: bool) -> dict:
    """La hauteur et la normale, refaites en flottant à la taille de sortie.

    DEUX défauts mesurés se corrigent ici, et ils tiennent au même geste :
      · la normale du service n'est pas unitaire (|n| jusqu'à 1,0075, 0,40 %
        des pixels à z<0, géométriquement impossible en espace tangent) parce
        que Z est reconstruit par LUT 8 bits avec écrêtage. On divise par la
        longueur, en flottant : |n| = 1 partout.
      · le 16 bits était creux (100 % de valeurs multiples de 257). Le
        rééchantillonnage en flottant produit de vraies valeurs sous-niveau ;
        s'il n'y en a pas (sortie à la taille de travail, donc aucune
        interpolation), `sub` vaut 0 et on écrit 8 bits en le disant.

    Rend, par map : l'image 8 bits (vignette + mesure), les octets PNG, la
    profondeur RÉELLEMENT écrite et la part de valeurs sous-niveau.
    """
    from PIL import Image
    out: dict = {}

    h_src = work_maps.get("height")
    if h_src is not None:
        hf = _f_channel(h_src if h_src.mode == "L" else h_src.convert("L"), size)
        img8 = _to_l(hf)
        data16 = _level16(hf) if bits16 else None
        out["height"] = _pick_depth(
            "height", img8, [data16] if data16 else None, size)

    n_src = work_maps.get("normal")
    if n_src is not None:
        nx, ny, _ = n_src.convert("RGB").split()
        X, Y, Z = _unit_normal(_f_channel(nx, size), _f_channel(ny, size))
        img8 = Image.merge("RGB", (_enc8(X), _enc8(Y), _enc8(Z)))
        planes = [_enc16(X), _enc16(Y), _enc16(Z)] if bits16 else None
        out["normal"] = _pick_depth("normal", img8, planes, size)
    return out


def _pick_depth(kind: str, img8, planes, size) -> dict:
    """Écrit 16 bits SI ET SEULEMENT SI les 16 bits portent quelque chose.

    « Une map peut porter moins que ce qu'on lui a demandé, et alors c'est
    écrit » : la règle du panneau s'applique enfin à la profondeur elle-même.

    DEUX conditions, pas une (voir `_depth16`) : des valeurs hors du réseau
    257k ET un octet faible qui porte de l'entropie. Passer l'une des deux
    suffit à un faux — les deux ensemble, non.
    """
    if planes:
        data = _png16(planes, size)
        d16 = _depth16(data)
        if d16["sub"] > 0.0 and d16["low_bits"] > 0.0:
            return {"img8": img8, "data": data, "bits": 16, "asked": 16,
                    "note16": "", **d16}
        petit = _png8(img8)
        # LA PHRASE EST ÉCRITE POUR CELUI QUI FABRIQUE UNE CARTE : ce qu'il
        # reçoit, et ce que ça lui économise. Les deux chiffres restent.
        pourquoi = ("le calcul ne produit ici rien de plus fin que 8 bits"
                    if d16["sub"] <= 0.0 else
                    f"second octet constant ({d16['low_vals']} valeur)")
        return {"img8": img8, "data": petit, "bits": 8, "asked": 16,
                "sub": d16["sub"], "low_bits": d16["low_bits"],
                "low_vals": d16["low_vals"],
                "note16": (f"16 bits sans effet ici : {pourquoi} — la map est "
                           f"écrite en 8 bits, "
                           f"{(len(data) - len(petit)) // 1024} Ko de moins.")}
    return {"img8": img8, "data": _png8(img8), "bits": 8, "sub": 0.0,
            "low_bits": 0.0, "low_vals": 0, "asked": 8, "note16": ""}


def _png8(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


# ── le corps du travail ─────────────────────────────────────────────────────

def _opts(body) -> dict:
    """Options normalisées. NE LÈVE JAMAIS sur une valeur illisible : ce qui
    est absent ou aberrant reprend son défaut (§2.5 : un corps mal formé ne
    doit jamais faire 500). Seule une résolution EXPLICITEMENT hors liste est
    refusée — c'est une demande impossible à honorer, pas une faute de frappe.
    """
    from app.services import pbr_service as pbr
    b = body if isinstance(body, dict) else {}
    res = b.get("res", DEFAULT_RES)
    try:
        res = int(res)
    except (TypeError, ValueError, OverflowError):
        res = DEFAULT_RES
    if res not in RES_CHOICES:
        raise HTTPException(400, "Résolution inconnue: attendu "
                            + ", ".join(str(r) for r in RES_CHOICES))
    lv = b.get("levels") if isinstance(b.get("levels"), dict) else {}

    def _lv(key: str, default: float) -> float:
        try:
            v = float(lv.get(key, default))
        except (TypeError, ValueError, OverflowError):
            return default
        if not math.isfinite(v):
            return default
        return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v

    return {
        "derive": pbr.normalize_derive(b.get("derive")),
        # LE DÉFAUT DE CETTE ROUTE ÉCRIVAIT UNE MAP MORTE. Le niveau de
        # rugosité par défaut valait 1,00 — l'extrémité de la course, où la
        # cuisson ne peut plus recentrer le motif sans écrêter : mesuré, un
        # appel sans `levels` rendait roughness.png CONSTANTE (moy 1,000,
        # amplitude 0, « neutre »), et l'ORM avec, puisque son canal V est
        # cette map. L'écran, lui, envoie 0,92 (le vélin, sa matière par
        # défaut) et ne voyait donc jamais le trou : deux tables pour un même
        # réglage, et c'est celle qu'on ne regarde pas qui écrivait le
        # livrable. On aligne le défaut de la route sur celui de l'écran.
        "levels": {"metallic": _lv("metallic", 0.0),
                   "roughness": _lv("roughness", DEFAULT_ROUGHNESS)},
        "res": res,
        "bits16": bool(b.get("bits16", True)),
        "square": bool(b.get("square", False)),
    }


def derive_deck(did: str, opts: dict) -> dict:
    """Dérive, cuit, écrit, PUIS relit et mesure. Bloquant : appelé par
    `asyncio.to_thread`."""
    from PIL import Image
    from app.services import material_store as ms
    from app.services import pbr_service as pbr

    d = _dir_or_404(did, create=True)
    src_path = d / "source.png"
    if not src_path.is_file():
        raise HTTPException(404, "Aucune source : envoyer d'abord la carte "
                                 "rendue (POST source)")
    t0 = time.perf_counter()
    src = Image.open(src_path)
    src.load()
    src = src.convert("RGB")

    res = opts["res"]
    long_side = max(src.size)
    work_long = min(long_side, res, WORK_MAX)
    work = src
    if work_long < long_side:
        k = work_long / float(long_side)
        work = src.resize((max(1, round(src.size[0] * k)),
                           max(1, round(src.size[1] * k))), Image.LANCZOS)

    maps = pbr.derive_maps(work, opts["derive"])          # les 8, d'un bloc
    maps = pbr.bake_levels(maps, opts["levels"])          # le niveau vit dans la map

    # les maps à la RÉSOLUTION DE TRAVAIL : c'est de là que part le calcul
    # flottant de la normale et de la hauteur — partir de leur version déjà
    # ramenée à 8 bits en sortie n'inventerait aucune précision.
    travail = {"height": maps.get("height"), "normal": maps.get("normal")}
    if opts["square"]:
        size = (res, res)
        maps = pbr.resize_maps(maps, res)
    else:
        w, h = work.size
        k = res / float(max(w, h))
        size = (max(1, round(w * k)), max(1, round(h * k)))
        maps = _resize_rect(maps, size)
    vec = _vector_maps(travail, size, opts["bits16"])

    # la carte, en millimètres : c'est elle qui donne le `pHYs` de chaque PNG
    phys = _physical(did, size)

    rows, extra = [], {}
    for kind in MAP_ORDER:
        got = vec.get(kind)
        img = got["img8"] if got else maps.get(kind)
        if img is None:
            continue
        data = got["data"] if got else ms.png_bytes(img, kind, bits=8)
        data = _with_meta(data, kind, phys["ppm"], _png_note(kind, phys))
        tmp = d / (kind + ".png.tmp")
        tmp.write_bytes(data)
        tmp.replace(d / (kind + ".png"))
        th = _as_mode(img, kind).copy()
        th.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
        th.save(d / ("thumb_" + kind + ".png"), format="PNG", optimize=False)
        rows.append(kind)
        extra[kind] = {"sub": got["sub"] if got else 0.0,
                       "low_bits": got["low_bits"] if got else 0.0,
                       "low_vals": got["low_vals"] if got else 0,
                       "asked": got["asked"] if got else 8,
                       "note16": got["note16"] if got else ""}

    # ── LA MESURE : on repart des fichiers, pas des objets en mémoire ───────
    relu, meta = {}, {}
    for kind in rows:
        raw = (d / (kind + ".png")).read_bytes()
        img, nbytes, depth, isize = _read_map(d / (kind + ".png"), kind)
        relu[kind] = img
        meta[kind] = {"bytes": nbytes, "bits": depth or 8,
                      "w": isize[0], "h": isize[1],
                      "chunks": png_chunks(raw), "phys": png_phys(raw),
                      # L'ESPACE LU DANS LE FICHIER, pas pris dans une table du
                      # code : « le manifeste dit linéaire » et « le fichier
                      # déclare linéaire » sont deux affirmations différentes,
                      # et seule la seconde est une mesure.
                      "decl": space_decl(raw),
                      "sha256": hashlib.sha256(raw).hexdigest()}
    rep = pbr.map_report(relu, relu.get("basecolor"))
    # UNE MAP 16 BITS SE MESURE SUR SEIZE BITS — MOYENNE *ET* AMPLITUDE.
    # `map_report` travaille sur l'image relue par Pillow, c'est-à-dire sur une
    # VUE 8 BITS de la map, et pas la même selon la map : octet fort pour un
    # RVB 16 bits (troncature), `v / 257 + 0,5` pour un gris 16 bits (arrondi).
    # Deux réductions pour un seul lot, donc deux amplitudes possibles pour les
    # mêmes octets (mesuré : 244 contre 243 sur la même hauteur). On rétablit
    # ici les deux chiffres, calculés sur la charge utile réelle
    # (`_mean16`, `_span16`), et le verdict « informative » est repris avec —
    # sinon un seuil resterait jugé sur un chiffre qu'on ne publie plus.
    # L'ÉCART-TYPE, sur le même canal et la même échelle que la moyenne.
    sd = {kind: _sd_canal(kind, relu[kind],
                          (d / (kind + ".png")).read_bytes()
                          if meta[kind]["bits"] == 16 else None)
          for kind in rows}
    # COMBIEN DE NIVEAUX LA MAP PORTE VRAIMENT. Une profondeur annoncée dit ce
    # que le fichier peut contenir ; ce compte dit ce qu'il contient. C'est lui
    # qui prévient les marches dans un dégradé, et il se relit sur les octets
    # comme la moyenne, sur le même canal qu'elle.
    niv = {kind: _levels_canal(kind, relu[kind],
                               (d / (kind + ".png")).read_bytes()
                               if meta[kind]["bits"] == 16 else None)
           for kind in rows}
    for kind in rows:
        if meta[kind]["bits"] != 16:
            continue
        raw16 = (d / (kind + ".png")).read_bytes()
        exact = _mean16(raw16)
        if exact is not None:
            rep["maps"][kind]["mean"] = exact
        amp = _span16(raw16)
        if amp is not None:
            rep["maps"][kind]["span"] = amp
            # même règle que `pbr.map_report` (span <= FLAT_SPAN => plate) ;
            # les deux maps 16 bits ne portent aucune règle particulière.
            plat = amp <= pbr.FLAT_SPAN
            if plat != (not rep["maps"][kind]["informative"]):
                rep["maps"][kind]["informative"] = not plat
                rep["informative"] = sum(1 for v in rep["maps"].values()
                                         if v["informative"])
    eff = pbr.effective_levels(relu)
    unit = _normal_report(relu.get("normal"),
                          (d / "normal.png").read_bytes()
                          if "normal" in rows else None)
    lum_full = _corr_full(relu)
    pack = orm_check(relu, meta.get("orm", {}).get("bytes", 0),
                     {k: meta.get(k, {}).get("bytes", 0)
                      for k in ("ao", "roughness", "metallic")})
    lum = source_lum(work)

    out_w, out_h = (meta[rows[0]]["w"], meta[rows[0]]["h"]) if rows else (0, 0)
    state = {
        "maps": [
            {"kind": k,
             "w": meta[k]["w"], "h": meta[k]["h"], "bits": meta[k]["bits"],
             "bits_asked": extra[k]["asked"], "sub": extra[k]["sub"],
             "low_bits": extra[k]["low_bits"], "low_vals": extra[k]["low_vals"],
             "note16": extra[k]["note16"],
             "bytes": meta[k]["bytes"], "sha256": meta[k]["sha256"],
             "space": COLORSPACE[k], "chunks": meta[k]["chunks"],
             "space_decl": meta[k]["decl"],
             "dpi": _dpi_of(meta[k]["phys"]),
             "mean": round(rep["maps"][k]["mean"] / 255.0, 4),
             "mean255": round(rep["maps"][k]["mean"], 2),
             "span": rep["maps"][k]["span"],
             "sd": sd[k],
             "niveaux": niv[k],
             "niveaux_max": 65536 if meta[k]["bits"] == 16 else 256,
             # le nombre d'échantillons SUR LEQUEL la profondeur est mesurée :
             # trois canaux pour la normale, un pour la hauteur. Sans lui,
             # « 90,7 % » ne dit pas de quoi il est le pourcentage. Zéro hors
             # 16 bits : `_depth16` ne mesure rien là, et publier un compte
             # d'échantillons qui ne compte rien serait un chiffre de plus à
             # ne pas pouvoir retrouver.
             "ech": (meta[k]["w"] * meta[k]["h"] * (3 if k == "normal" else 1)
                     if meta[k]["bits"] == 16 else 0),
             # LA CONVENTION VOYAGE AVEC LE CHIFFRE. `moyenne` et `amplitude`
             # ne veulent pas dire la même chose d'une map à l'autre ; le dire
             # ailleurs qu'à côté du nombre revient à ne pas le dire.
             "mesure_sur": mesure_sur(k, meta[k]["bits"]),
             "span_def": span_def(meta[k]["bits"]),
             "informative": bool(rep["maps"][k]["informative"]),
             "note": note_utilisateur(rep["maps"][k]["note"]),
             "hint": ("" if rep["maps"][k]["informative"]
                      else flat_hint(k, opts, lum)),
             "channel": rep["maps"][k]["channel"],
             "corr_lum": round(rep["maps"][k]["corr_lum"], 3),
             "corr_full": lum_full.get(k, 0.0),
             "dependent": bool(rep["maps"][k]["dependent"])}
            for k in rows
        ],
        "informative": rep["informative"],
        "total": rep["total"],
        "dependent": rep["dependent"],
        "effective": eff,
        "unit_normal": unit,
        "orm_pack": pack,
        "source_lum": lum,
        # LE PRIX DU LOT, MESURÉ. « 22 secondes et 45 Mo sans le moindre
        # avertissement avant le clic » : on ne peut pas prédire honnêtement
        # ce qu'un calcul n'a pas encore fait, mais on peut publier ce que le
        # DERNIER a coûté et laisser l'écran faire la règle de trois sur des
        # comptes de pixels exacts.
        "bytes_total": sum(meta[k]["bytes"] for k in rows),
        "out_mpx": round(out_w * out_h / 1e6, 3),
        "phys": phys,
        "res": res, "bits16": opts["bits16"], "square": opts["square"],
        "derive": opts["derive"], "levels": opts["levels"],
        "out_px": f"{out_w} x {out_h}",
        "work_px": f"{work.size[0]} x {work.size[1]}",
        "source": _source_info(d),
        "ms": int((time.perf_counter() - t0) * 1000),
        "updated": _now_iso(),
        "stamp": int(time.time()),
    }
    (d / "report.json").write_text(json.dumps(state, ensure_ascii=False,
                                              indent=2), encoding="utf-8")
    (d / "manifest.json").write_text(
        json.dumps(build_manifest(state), ensure_ascii=False, indent=2),
        encoding="utf-8")
    return state


def _dpi_of(ppm) -> list[int]:
    return [round(ppm[0] * 0.0254), round(ppm[1] * 0.0254)] if ppm else [0, 0]


def _physical(did: str, size: tuple[int, int]) -> dict:
    """Les dimensions PHYSIQUES de la carte, et la densité qui en découle.

    LA MOITIÉ MESURABLE DU CAHIER DES CHARGES : « 300 DPI avec fond perdu et
    zone de sécurité ». Un PNG sans chunk `pHYs` entre à 72 DPI dans tout
    outil d'impression — l'affirmation ne tient alors qu'à l'écran. Ici la
    densité est CALCULÉE depuis la géométrie du document (rogne + 2 x fond
    perdu) et la taille réellement écrite, puis inscrite dans chaque fichier.
    """
    out = {"ok": False, "ppm": None, "dpi": [0, 0], "dpi_min": 0,
           "mm": [0.0, 0.0],
           "fmt": "", "doc_dpi": 0, "bleed_mm": 0.0, "safe_mm": 0.0}
    try:
        from . import core as cards_core
        doc = cards_core.read_deck(did)
        if not doc:
            return out
        g = cards_core.geom_of(doc)
    except Exception as e:                       # document illisible : on le dit
        logger.warning(f"cards/texture: géométrie indisponible ({did}): {e}")
        return out
    mm_w = g.trim_mm[0] + 2 * g.bleed_mm
    mm_h = g.trim_mm[1] + 2 * g.bleed_mm
    ppm = (round(size[0] * 1000.0 / mm_w), round(size[1] * 1000.0 / mm_h))
    dpi = _dpi_of(ppm)
    # LES DEUX AXES, SÉPARÉMENT. Un atlas CARRÉ posé sur une carte qui ne l'est
    # pas donne des pixels rectangulaires : 1024² sur 69 x 94 mm, c'est 377 DPI
    # en largeur et 277 en hauteur. Publier la seule largeur ferait passer pour
    # conforme un lot dont la moitié verticale tombe sous le plancher de 300 DPI
    # du cahier des charges. `dpi_min` est le chiffre qui décide.
    out.update({"ok": True, "ppm": list(ppm), "dpi": dpi,
                "dpi_min": min(dpi),
                "mm": [round(mm_w, 2), round(mm_h, 2)], "fmt": g.fmt,
                "doc_dpi": g.dpi, "bleed_mm": g.bleed_mm, "safe_mm": g.safe_mm,
                "trim_mm": [g.trim_mm[0], g.trim_mm[1]],
                "canvas_px": list(g.canvas_px)})
    return out


def _png_note(kind: str, phys: dict) -> str:
    base = f"map={kind} colorspace={COLORSPACE[kind]}"
    if kind == "normal":
        base += " encoding=OpenGL +Y, n=2c-1, unit length"
    if kind == "orm":
        base += " packing=R:AO G:roughness B:metallic"
    if phys.get("ok"):
        base += (f" card={phys['mm'][0]}x{phys['mm'][1]}mm"
                 f" (bleed {phys['bleed_mm']}mm, safe {phys['safe_mm']}mm)"
                 f" {phys['dpi'][0]}x{phys['dpi'][1]}dpi")
    return base


def _mean_f(f) -> float:
    """Moyenne d'une image FLOTTANTE, en flottant.

    PIÈGE MESURÉ : `ImageStat.Stat(img).mean` passe par `histogram()`, qui
    n'a que 256 classes — sur une image en mode F il rend n'importe quoi
    (446,67 attendu, 126,48 obtenu ; et la première version de ce fichier
    affichait « |n| moyenne 77,58 » pour une longueur unité). Une réduction
    BOX à 1x1 fait la moyenne exacte en flottant : écart mesuré 8,8e-06 sur
    un tirage aléatoire de 5 917 valeurs."""
    from PIL import Image
    return float(f.resize((1, 1), Image.BOX).getpixel((0, 0)))


def _normal_report(nrm, raw: bytes | None = None) -> dict:
    """La normale est-elle un champ de vecteurs unitaires ? Mesuré sur les
    octets RELUS DU FICHIER, avec le décodage des moteurs (n = 2c - 1), à la
    précision réellement écrite : les deux octets quand le fichier est en 16
    bits, sinon l'octet unique.

    Le panneau auditait la moyenne et l'amplitude de chaque map mais jamais la
    VALIDITÉ vectorielle de la seule qui en a une — c'est le seul terrain où
    la barre était meilleure (mesuré avant : |n| moyenne 0,9940, max 1,0075,
    1,52 % des pixels à plus de 5 % de l'unité, 0,3982 % à z<0)."""
    from PIL import Image, ImageMath
    if nrm is None:
        return {}
    axes, prec = None, 8
    if raw and png_depth(raw) == 16:
        w, h, nch, pay = _png16_payload(raw)
        if nch == 3 and pay:
            # `k["float"]` d'abord : multiplier une image ENTIÈRE par un
            # flottant fait `Image.new("I", size, 256.0)` dans ImageMath, qui
            # lève « color must be int or single-element tuple ».
            axes = [ImageMath.lambda_eval(
                lambda k: (k["float"](k["h"]) * 256.0 + k["float"](k["l"]))
                * (2.0 / 65535.0) - 1.0,
                h=Image.frombytes("L", (w, h), pay[2 * c::6]),
                l=Image.frombytes("L", (w, h), pay[2 * c + 1::6]))
                for c in range(3)]
            prec = 16
    if axes is None:
        axes = [ImageMath.lambda_eval(
            lambda k: k["float"](k["v"]) * (2.0 / 255.0) - 1.0, v=ch)
            for ch in nrm.convert("RGB").split()]
    ln = ImageMath.lambda_eval(
        lambda k: (k["x"] * k["x"] + k["y"] * k["y"] + k["z"] * k["z"]) ** 0.5,
        x=axes[0], y=axes[1], z=axes[2])
    mean = _mean_f(ln)
    lo, hi = ln.getextrema()
    # part des pixels à plus de 5 % de l'unité : |n|-1 mis à l'échelle puis
    # compté par histogramme (aucune boucle par pixel).
    ecart = ImageMath.lambda_eval(
        lambda k: k["convert"](((k["l"] - 1.0) ** 2) ** 0.5 * 2000.0, "L"), l=ln)
    hst = ecart.histogram()
    n = sum(hst) or 1
    hors = sum(hst[100:])                       # 100/2000 = 0,05
    sous = ImageMath.lambda_eval(
        lambda k: k["convert"](k["z"] * -1e6, "L"), z=axes[2]).histogram()
    return {"mean": round(mean, 5), "min": round(lo, 5), "max": round(hi, 5),
            "unit_pct": round(100.0 * (n - hors) / n, 2),
            "zneg": n - sous[0], "px": n, "bits": prec}


def _corr_full(relu: dict) -> dict:
    """Corrélation à PLEINE RÉSOLUTION, en plus de celle du service.

    `pbr_service.correlation` réduit en blocs 192x192 (BOX) avant Pearson —
    c'est écrit dans son code, pas à l'écran, et un lecteur qui recalcule sans
    cette réduction trouve un autre nombre (mesuré : hauteur +0,994 en blocs,
    +0,906 à pleine résolution). Deux définitions, donc deux colonnes
    étiquetées, plutôt qu'un chiffre orphelin."""
    from PIL import ImageMath, ImageStat
    base = relu.get("basecolor")
    if base is None:
        return {}
    lum = base.convert("L")
    ml = ImageStat.Stat(lum).mean[0]                      # image L : exact
    lf = ImageMath.lambda_eval(lambda k: k["float"](k["v"]) - ml, v=lum)
    sl = _mean_f(ImageMath.lambda_eval(lambda k: k["a"] * k["a"], a=lf))
    out = {}
    for kind, img in relu.items():
        if kind == "basecolor" or img is None:
            continue
        ch = img.convert("RGB").split()[0] if kind == "normal" else (
            img.convert("RGB").split()[1] if kind == "orm" else img.convert("L"))
        mc = ImageStat.Stat(ch).mean[0]
        cf = ImageMath.lambda_eval(lambda k: k["float"](k["v"]) - mc, v=ch)
        sc = _mean_f(ImageMath.lambda_eval(lambda k: k["a"] * k["a"], a=cf))
        cov = _mean_f(ImageMath.lambda_eval(lambda k: k["a"] * k["b"], a=cf, b=lf))
        out[kind] = (round(cov / math.sqrt(sc * sl), 3)
                     if sc > 1e-9 and sl > 1e-9 else 0.0)
    return out


# ── la CONVENTION, écrite à côté du chiffre ─────────────────────────────────
#
# LE DÉFAUT QUE CECI CORRIGE, reproduit ici avant d'être bouché. Le « moy » et
# l'« ampl. » d'une vignette ne portaient AUCUNE définition à côté d'eux, et
# leur définition change avec la map : luminance Rec.601 sur basecolor et
# emissive, canal R sur la normale, canal V sur l'ORM, canal unique sur les
# quatre maps scalaires. Les chiffres étaient JUSTES — un décodeur PNG
# indépendant (zlib + défiltrage des cinq filtres) a revérifié 102 valeurs
# affichées sans une divergence — mais un lecteur qui recalcule naïvement
# trouve autre chose et conclut au mensonge. Mesuré en le refaisant : une
# luminance Rec.601 TRONQUÉE au lieu d'être arrondie donne 0,2349 là où le
# panneau affiche 0,2368. Un demi-niveau suffit à faire passer un chiffre vrai
# pour un faux. La convention voyage donc désormais AVEC le nombre — à
# l'écran, sur la planche et dans le manifeste.

MEAN_DEF: dict[str, str] = {
    "basecolor": "luminance Rec.601",
    "emissive": "luminance Rec.601",
    "normal": "canal R (relief X)",
    "orm": "canal V (rugosité)",
}
SPAN_DEF = "p95 − p5"
# Sur une map 16 bits, « p95 − p5 » ne suffit pas : p95 − p5 DE QUOI ? De
# l'octet fort ? De la vue 8 bits arrondie ? Les deux existent et diffèrent
# (244 contre 243, mesuré). La définition dit donc l'échelle de mesure ET le
# retour sur 255, puisque c'est sur 255 que le chiffre est affiché.
SPAN_DEF16 = "p95 − p5 sur les 65 536 classes, échelle 0-255"


def span_def(bits: int) -> str:
    return SPAN_DEF16 if bits == 16 else SPAN_DEF


# ── ce qui s'écrit sous une vignette : une phrase d'utilisateur ─────────────
#
# CE QUE CECI CORRIGE. Les notes rendues par le service sont écrites pour un
# relecteur : « éteinte », « information peu indépendante de l'image source »
# sont des VERDICTS sur le travail, pas des phrases qui aident quelqu'un à
# faire une carte. Celui qui ouvre ce panneau veut savoir ce que la map
# contient et quoi régler ; le jugement, il le porte lui-même. On ne retire
# AUCUN chiffre au passage : le « r = +0,99 » reste, c'est la mesure.

NOTE_UTILISATEUR: tuple[tuple[str, str], ...] = (
    ("éteinte — cette matière n'émet pas de lumière",
     "aucun pixel au-dessus du seuil d'émission"),
    (" — information peu indépendante de l'image source", ""),
)


def note_utilisateur(note: str) -> str:
    for avant, apres in NOTE_UTILISATEUR:
        note = note.replace(avant, apres)
    return note


def mesure_sur(kind: str, bits: int) -> str:
    """Le canal exact sur lequel `moyenne` et `amplitude` sont calculées."""
    base = MEAN_DEF.get(kind, "canal unique")
    return base + (", lu sur 16 bits" if bits == 16 else "")


def png_gama(data: bytes) -> int | None:
    """La valeur du chunk `gAMA` (x100000), ou None. `gAMA` 100000 = 1.0 =
    linéaire ; 45455 = 1/2,2 = la courbe sRGB."""
    if len(data) < 12 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i = 8
    while i + 12 <= len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        if tag == b"gAMA" and ln >= 4:
            return struct.unpack(">I", data[i + 8:i + 12])[0]
        if tag == b"IEND":
            break
        i += 12 + ln
    return None


def space_decl(data: bytes) -> str:
    """L'espace colorimétrique TEL QUE LES OCTETS LE DÉCLARENT.

    Un critique a écrit que « le manifeste dit linéaire, mais le fichier ne le
    déclare pas formellement ». Le fichier le déclare — `gAMA` 100000 EST la
    façon dont PNG écrit « gamma 1.0 », c'est-à-dire linéaire — mais l'écran
    affichait le mot « linéaire » pris dans une table du code, pas le chunk
    trouvé dans le fichier. Ce sont deux choses différentes, et seule la
    seconde est une mesure. On lit donc le chunk et on le CITE."""
    if not data:
        return "non déclaré"
    g = png_gama(data)
    srgb = "sRGB" in png_chunks(data)
    if srgb:
        return ("sRGB (chunks sRGB + gAMA "
                + (f"{g / 100000.0:.5f}".replace(".", ",") if g else "absent")
                + ")")
    if g == 100000:
        return "linéaire (gAMA 1,0)"
    if g is not None:
        return f"gAMA {g / 100000.0:.5f}".replace(".", ",")
    return "non déclaré dans les octets"


def orm_check(relu: dict, octets: int = 0, trois: dict | None = None) -> dict:
    """L'ORM est-il VRAIMENT ao / rugosité / métal empaquetés ? Mesuré canal
    par canal, à l'octet, sur les fichiers RELUS.

    Le panneau ANNONÇAIT la convention « R = AO, V = rugosité, B = métal »
    sans jamais la vérifier : c'est un critique qui a dû rouvrir les quatre
    PNG pour constater l'écart maximum de 0. Une convention annoncée et non
    mesurée est exactement le genre de mention que ce panneau s'interdit.
    Et le prix de la redondance est publié avec : l'ORM ne porte aucune valeur
    nouvelle, il coûte ses octets.

    LE REPROCHE QUE `octets_trois` TRANCHE — et il revient dans les deux
    duels : « l'ORM ajoute 1 587 867 octets de redondance pure, sans option
    pour livrer l'ORM À LA PLACE des trois séparées ». La première moitié est
    vraie et déjà publiée. La seconde suppose qu'échanger ferait maigrir le
    lot ; on ne le suppose plus, on le PÈSE — et le résultat DÉPEND DU
    CONTENU, ce qui interdit d'en faire une phrase générale :

      · lot 2048² réel (carte composée, grain fin) : orm.png 2 234 741 octets
        contre ao + roughness + metallic = 1 112 829 + 846 434 + 4 339
        = 1 963 602. L'ORM est le PLUS LOURD des deux paquets, +271 139
        octets (+13,8 %).
      · carte de synthèse 1024², pauvre en détail (celle des tests) :
        155 999 contre 156 760. L'ORM est plus léger, de 761 octets (0,5 %).

    La déflate compresse trois plans corrélés côte à côte tantôt mieux,
    tantôt moins bien que trois gris séparés dont un métallique noir qui
    tient en quelques Ko. Conclusion mesurable et unique : l'échange ne fait
    pas maigrir le lot de façon fiable, dans un sens comme dans l'autre. Les
    DEUX poids partent donc à l'écran, et la phrase affichée suit le signe
    mesuré au lieu de l'annoncer."""
    from PIL import ImageChops
    orm = relu.get("orm")
    if orm is None:
        return {}
    chans = orm.convert("RGB").split()
    trois = trois or {}
    somme = sum(int(trois.get(k, 0)) for k in ("ao", "roughness", "metallic"))
    out: dict = {"px": orm.size[0] * orm.size[1], "ecarts": {},
                 "octets": int(octets), "octets_trois": somme,
                 "ok": True}
    for i, src in enumerate(("ao", "roughness", "metallic")):
        img = relu.get(src)
        if img is None or img.size != orm.size:
            out["ok"] = False
            out["ecarts"][src] = None
            continue
        ref = img if img.mode == "L" else img.convert("L")
        d = int(ImageChops.difference(chans[i], ref).getextrema()[1])
        out["ecarts"][src] = d
        if d:
            out["ok"] = False
    return out


# ── LE RACCORD, RELU SUR LES OCTETS ─────────────────────────────────────────
#
# CE QUE CECI CORRIGE, ET C'EST LE MÊME DÉFAUT QUE LE BADGE « 16 BITS ».
# L'écran publiait trente rapports de raccord, un total (« 26 / 30 ») et un
# pire cas. Aucun de ces trente et un nombres n'avait de fichier derrière lui :
# ils naissaient et mouraient dans le navigateur, et un critique l'a écrit noir
# sur blanc — « aucun export, tous les chiffres affichés restent invérifiables
# sur des octets ». La tuile part donc ici, et c'est CE FICHIER qui est mesuré.
#
# ET LA MESURE ELLE-MÊME ÉTAIT FAUSSE. Elle divisait la marche au raccord par
# la marche MÉDIANE entre deux colonnes voisines. Sur un tissage, la médiane
# est prise à l'intérieur d'un fil — là où rien ne se passe — pendant que le
# raccord tombe sur un bord de fil : on comparait une transition franche à une
# non-transition. Mesuré sur la toile de jute : marche au raccord 40,27 pour
# une PIRE marche interne de 40,25. L'ancien verdict disait « 7,28x, couture
# visible » ; les octets disent « un bord de fil comme les 85 autres ». On
# compare donc au MAXIMUM des marches internes, sur les 511 paires de chaque
# axe. Un excès de 1,00 signifie : le raccord ne fait rien de pire que ce que
# la matière fait déjà quelque part à l'intérieur.

SEAM_GRADES: tuple[tuple[float, str], ...] = (
    (1.0, "invisible"), (1.5, "discret"), (3.0, "visible"),
)


def seam_grade(exces: float) -> str:
    for seuil, nom in SEAM_GRADES:
        if exces <= seuil:
            return nom
    return "casse"


def tile_lum(img) -> tuple[list[float], int]:
    """La luminance FLOTTANTE d'une tuile carrée, exactement comme l'écran la
    calcule : 0,299 R + 0,587 V + 0,114 B sur les octets, sans arrondi
    intermédiaire. `convert("L")` de Pillow arrondit chaque pixel à l'entier et
    donnerait un autre nombre — c'est précisément ce genre d'écart d'un
    demi-niveau qui fait passer un chiffre vrai pour un faux."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    if w != h:
        raise HTTPException(400, "La tuile doit etre carree : "
                                 f"recu {w} x {h}")
    r, g, b = (band.tobytes() for band in rgb.split())
    lum = [0.299 * r[i] + 0.587 * g[i] + 0.114 * b[i] for i in range(w * h)]
    return lum, w


def seam_report(img) -> dict:
    """La marche au raccord comparée à la PIRE marche interne, axe par axe.

    Toutes les paires voisines sont balayées (S-1 par axe), pas un
    échantillonnage : un maximum estimé sur 24 sondages n'est pas un maximum.
    """
    from operator import sub
    lum, S = tile_lum(img)
    inv = 1.0 / S

    def col(a: int, b: int) -> float:
        return sum(map(abs, map(sub, lum[a::S], lum[b::S]))) * inv

    def row(a: int, b: int) -> float:
        return sum(map(abs, map(sub, lum[a * S:(a + 1) * S],
                                lum[b * S:(b + 1) * S]))) * inv

    in_x = [col(k - 1, k) for k in range(1, S)]
    in_y = [row(k - 1, k) for k in range(1, S)]
    e_x, e_y = col(S - 1, 0), row(S - 1, 0)
    mx_x, mx_y = max(max(in_x), 1e-6), max(max(in_y), 1e-6)
    md_x, md_y = max(sorted(in_x)[len(in_x) // 2], 1e-6), max(sorted(in_y)[len(in_y) // 2], 1e-6)
    ex_x, ex_y = e_x / mx_x, e_y / mx_y
    exces = max(ex_x, ex_y)
    # LE VERDICT SE PREND SUR LE NOMBRE PUBLIÉ, à la précision où il est
    # publié : sinon une tuile affichée « 1,00x » serait comptée en échec parce
    # qu'elle vaut 1,0019, et le badge contredirait le total sur le même octet.
    # `exces_brut` garde la pleine précision — c'est elle que l'écran doit
    # retrouver à l'identique sur le fichier exporté.
    publie = round(exces, 2)
    rnd = lambda v: round(float(v), 4)                       # noqa: E731
    return {
        "px": S, "paires_testees": 2 * (S - 1),
        "x": {"edge": rnd(e_x), "med": rnd(md_x), "max": rnd(mx_x), "exces": rnd(ex_x)},
        "y": {"edge": rnd(e_y), "med": rnd(md_y), "max": rnd(mx_y), "exces": rnd(ex_y)},
        "exces": publie, "exces_brut": rnd(exces), "grade": seam_grade(publie),
        "ratio_median": rnd(max(e_x / md_x, e_y / md_y)),
        "definition": ("marche moyenne au raccord divisee par la PIRE marche "
                       "entre deux colonnes (ou lignes) voisines a l'interieur, "
                       "sur les S-1 paires de chaque axe ; luminance "
                       "0,299 R + 0,587 V + 0,114 B des octets, sans arrondi"),
    }


def _tile_note(seam: dict, mat: str) -> str:
    """Ce qui est écrit DANS le fichier, pour qu'un tiers refasse le calcul."""
    return (f"matiere={mat or '?'} tuile={seam['px']}px "
            f"exces={seam['exces_brut']:.4f} ({seam['grade']}) "
            f"H bord={seam['x']['edge']:.4f} pire_interne={seam['x']['max']:.4f} "
            f"V bord={seam['y']['edge']:.4f} pire_interne={seam['y']['max']:.4f} "
            f"paires={seam['paires_testees']} | {seam['definition']}")


def _tile_meta(seam: dict, mat: str, ppm: int) -> bytes:
    out = _chunk(b"gAMA", struct.pack(">I", 45455))
    out += _chunk(b"sRGB", bytes([0]))
    out += _chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
    out += _text("Comment", _tile_note(seam, mat))
    out += _text("Seam-Exces", f"{seam['exces_brut']:.4f}")
    out += _text("Seam-H", f"bord={seam['x']['edge']:.4f} "
                           f"mediane={seam['x']['med']:.4f} "
                           f"pire={seam['x']['max']:.4f}")
    out += _text("Seam-V", f"bord={seam['y']['edge']:.4f} "
                           f"mediane={seam['y']['med']:.4f} "
                           f"pire={seam['y']['max']:.4f}")
    return out


def store_tile(did: str, raw: bytes, mat: str, seed: int) -> dict:
    """La tuile reçue est DÉCODÉE, MESURÉE, puis réécrite avec sa mesure dans
    ses propres chunks. Le fichier rendu porte donc ce qu'on affiche."""
    from PIL import Image
    d = _dir_or_404(did, create=True)
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(400, "Corps illisible : le PNG de la tuile est "
                                 "attendu dans le corps de la requete")
    w, h = img.size
    if not (TILE_MIN_PX <= w <= TILE_MAX_PX) or w != h:
        raise HTTPException(400, f"Tuile carree de {TILE_MIN_PX} a "
                                 f"{TILE_MAX_PX} px attendue : recu {w} x {h}")
    seam = seam_report(img)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=False)
    # La tuile est peinte en PIXELS DE TOILE (le contrat interdit toute échelle
    # au painter) : sa densité physique est donc celle du document, et elle est
    # inscrite plutôt que sous-entendue — un PNG sans `pHYs` entre à 72 DPI.
    doc_dpi = _physical(did, (w, h)).get("doc_dpi") or SHEET_DPI
    ppm = int(round(doc_dpi / 0.0254))
    data = buf.getvalue()
    cut = 8 + 25
    data = data[:cut] + _tile_meta(seam, mat, ppm) + data[cut:]
    tmp = d / "tile.png.tmp"
    tmp.write_bytes(data)
    tmp.replace(d / "tile.png")
    p = d / "tile.png"
    octets = p.read_bytes()
    ppm_lu = png_phys(octets)
    return {
        "mat": str(mat or "")[:64], "seed": int(seed),
        "w": w, "h": h, "bytes": len(octets),
        "sha256": hashlib.sha256(octets).hexdigest(),
        "chunks": png_chunks(octets),
        "dpi": _dpi_of(ppm_lu), "ppm": list(ppm_lu) if ppm_lu else None,
        "seam": seam, "updated": _now_iso(),
    }


def source_lum(work) -> dict:
    """La luminance de l'image RÉELLEMENT DÉRIVÉE, mesurée.

    Pas celle de `source.png` : `derive_deck` rééchantillonne d'abord en
    LANCZOS quand la résolution demandée est plus petite que la carte, et
    LANCZOS DÉPASSE — le maximum de l'image de travail peut être plus haut que
    celui du fichier source. Comparer un seuil au mauvais maximum ferait dire
    au panneau « aucun pixel au-dessus » alors qu'il y en a. C'est donc
    l'image que `pbr_service.derive_maps` reçoit qui est mesurée, avec la même
    luminance que lui (`pbr_service.luminance` = `convert("L")`, Rec.601)."""
    if work is None:
        return {}
    try:
        h = (work if work.mode == "L" else work.convert("L")).histogram()
    except (OSError, ValueError):
        return {}
    n = sum(h) or 1
    mx = next((i for i in range(255, -1, -1) if h[i]), 0)
    # DEUX CENTILES, ET LE SECOND N'EST PAS DÉCORATIF. Le p99 dit où plafonne
    # l'image ; c'est le p80 qui sert de REMÈDE au seuil d'émission, parce que
    # le p99 n'allume rien d'utile — mesuré sur deux cartes très différentes :
    # seuil au p99 -> émissive de moyenne 0,22 et 0,10 sur 255, donc « neutre »
    # des deux côtés ; seuil au p80 -> moyenne 11,50 (amplitude 87) et 3,52
    # (amplitude 28), informative des deux côtés. Un bouton qui propose un
    # réglage doit proposer celui qui produit quelque chose.
    acc, p80, p99 = 0, 0, 0
    for i, c in enumerate(h):
        acc += c
        if not p80 and acc >= 0.80 * n:
            p80 = i
        if acc >= 0.99 * n:
            p99 = i
            break
    return {"max": round(mx / 255.0, 4), "p99": round(p99 / 255.0, 4),
            "p80": round(p80 / 255.0, 4), "px": n}


def flat_hint(kind: str, opts: dict, lum: dict) -> str:
    """POURQUOI cette map est vide, et QUOI RÉGLER — avant l'export.

    « Un réglage qui ne produit rien devrait le dire AVANT l'export, pas
    après » : le seuil d'émission par défaut (0,85) ne peut rien allumer sur
    une carte dont la luminance plafonne à 0,63, et le panneau se contentait
    d'annoncer une map « éteinte » sans jamais dire qu'aucun réglage de cette
    map n'était en cause — c'est le SEUIL qui est hors de portée de l'image.
    Chaque phrase rendue ici est une comparaison entre un réglage et une
    mesure ; quand la mesure ne tranche pas, on ne rend rien."""
    def fr(v: float) -> str:                    # 0,85 — pas 0.85
        return f"{v:.2f}".replace(".", ",")

    dv = opts.get("derive") or {}
    lv = opts.get("levels") or {}
    # LA PREMIÈRE CLAUSE SE SUFFIT À ELLE-MÊME. La planche coupe une légende à
    # 300 px : une phrase qui commence par sa mise en contexte y arrive
    # tronquée avant d'avoir rien dit. La comparaison d'abord, l'explication
    # ensuite.
    if kind == "emissive" and lum:
        s = float(dv.get("emissive_threshold", 0.85))
        if s > lum["max"]:
            return (f"seuil d'émission {fr(s)} > max {fr(lum['max'])} : rien à "
                    f"allumer. L'image dérivée ne dépasse jamais "
                    f"{fr(lum['max'])}, donc la map est noire par "
                    f"construction ; descendre le seuil sous {fr(lum['max'])}.")
        # LE SECOND CAS, ET IL EST PLUS FRÉQUENT QUE LE PREMIER : le seuil est
        # ATTEIGNABLE et la map sort quand même vide, parce qu'il ne laisse
        # passer qu'une poignée de pixels. La map disait « éteinte » sans un
        # chiffre et sans un remède — le même défaut que celui qu'on venait de
        # réparer un cran plus haut. Les centiles bornent EXACTEMENT la part de
        # l'image qui dépasse le seuil : au-dessus du p99, c'est moins de 1 % ;
        # au-dessus du p80, moins de 20 %. Mesuré, pas estimé.
        p80, p99 = lum.get("p80"), lum.get("p99")
        if p99 is not None and s > p99:
            part = "moins de 1 %"
        elif p80 is not None and s > p80:
            part = "moins de 20 %"
        else:
            return ""
        rem = (f" ; à {fr(p80)} (centile 80) un pixel sur cinq passe."
               if p80 is not None else "")
        return (f"seuil {fr(s)} : {part} de l'image le dépasse. Le seuil est "
                f"atteignable, mais il ne laisse passer presque rien{rem}")
    if kind == "metallic":
        mode = str(dv.get("metallic_mode", "auto"))
        s = float(dv.get("metallic_threshold", 0.5))
        if mode == "none":
            return ("mode métallique « aucun » : nulle par réglage, pas par "
                    "mesure de la matière.")
        if mode == "luminance" and lum and s > lum["max"]:
            return (f"seuil métallique {fr(s)} > max {fr(lum['max'])} : aucun "
                    "pixel au-dessus dans l'image dérivée.")
        return ""
    if kind in ("roughness", "orm"):
        v = float(lv.get("roughness", 1.0))
        # `pbr_service.level_lut` : amp = min(spread, level/down, (1-level)/up).
        # A 0 comme a 1, l'un des deux quotients vaut zero, donc l'amplitude
        # vaut zero et la map sort constante. Ce n'est pas la matiere qui est
        # plate, c'est le NIVEAU CUIT qui l'ecrase — verifie sur les octets.
        if v >= 0.995 or v <= 0.005:
            return (f"niveau de rugosité cuit à {fr(v)} : amplitude nulle, map "
                    "constante. À cette extrémité c'est le niveau qui écrase "
                    "le motif, pas la matière — entre 0,05 et 0,95 il revient.")
    return ""


def build_manifest(state: dict) -> dict:
    """Le contrat du livrable, en clair. AVANT : les noms de fichiers étaient
    le seul contrat — rien ne disait quelles maps sont sRGB et lesquelles sont
    linéaires, ni à quelle taille physique correspond un pixel, ni quelle
    convention porte l'ORM. La barre, elle, embarque un manifeste C2PA."""
    phys = state.get("phys") or {}
    # LE MANIFESTE NE SIGNE PAS. Il portait « generateur : <outil> — pièce 06 »
    # en première ligne : le nom du producteur et son numéro de chantier
    # interne, recopiés dans un fichier que l'acheteur redistribue avec ses
    # textures. Un manifeste décrit le LOT, pas qui l'a fabriqué.
    return {
        "genere": state.get("updated", ""),
        # LE MANIFESTE DÉCRIT SES COLONNES, IL NE RÉCITE RIEN. Les noms de clés
        # disaient la mesure dans le vocabulaire d'un contrôle (« sous_niveaux »,
        # « octet_faible ») ; ils disent maintenant ce que la colonne contient,
        # pour quelqu'un qui ouvre le fichier avec ses textures.
        "mesure": ("chaque chiffre est relu sur les octets des PNG écrits ; "
                   "« niveaux_distincts » = nombre de valeurs différentes du "
                   "canal mesuré, sur « niveaux_possibles » ; "
                   "« precision_hors_8_bits_pct » = part des points dont la "
                   "valeur 16 bits ne tient pas dans un octet ; "
                   "« second_octet_bits » = quantité d'information portée par "
                   "le second octet, sur 8 ; "
                   "« ecart_type » = dispersion du canal nommé par "
                   "canal_mesure, sur la même échelle que la moyenne"),
        "carte": {"format": phys.get("fmt", ""), "dpi_document": phys.get("doc_dpi", 0),
                  "rogne_mm": phys.get("trim_mm", []),
                  "fond_perdu_mm": phys.get("bleed_mm", 0),
                  "zone_sure_mm": phys.get("safe_mm", 0),
                  "toile_mm": phys.get("mm", []),
                  "toile_px": phys.get("canvas_px", [])},
        "sortie": {"px": state.get("out_px", ""), "derive_a": state.get("work_px", ""),
                   "dpi": phys.get("dpi", [0, 0]),
                   "dpi_min": phys.get("dpi_min", 0),
                   "atteint_300_dpi": bool(phys.get("dpi_min", 0) >= 300),
                   "atlas_carre": bool(state.get("square")),
                   "pixels_par_metre": phys.get("ppm")},
        "conventions": {
            "orm": "R = occlusion, V = rugosité, B = métallique",
            "normale": "OpenGL (+Y vers le haut), n = 2c - 1, longueur unité",
            "espaces": {k: COLORSPACE[k] for k in MAP_ORDER},
            # CE QUE « moyenne » ET « amplitude » VEULENT DIRE, map par map.
            # Elles ne veulent PAS dire la même chose partout, et un acheteur
            # qui recalcule une moyenne plate là où le chiffre est une
            # luminance Rec.601 croit à un mensonge. La définition est donc
            # portée par chaque ligne (`canal_mesure`), et rappelée ici.
            "moyenne": ("moyenne du canal nommé par `canal_mesure` ; "
                        "« luminance Rec.601 » = (R x 19595 + V x 38470 + "
                        "B x 7471 + 32768) >> 16, ARRONDIE"),
            "amplitude_p95_p5": ("centile 95 moins centile 5 du MÊME canal, "
                                 "sur 255 — pas max moins min"),
            "moyenne_16_bits": ("les maps 16 bits sont moyennées sur seize "
                                "bits (256 x octet fort + second octet) / 257"),
            "amplitude_16_bits": ("l'amplitude d'une map 16 bits est lue sur "
                                  "seize bits elle aussi (centiles sur 65 536 "
                                  "classes) puis ramenée sur l'échelle 0-255"),
            "niveaux_distincts": ("valeurs différentes réellement présentes "
                                  "dans le canal mesuré ; c'est ce compte, et "
                                  "non la profondeur annoncée, qui dit si un "
                                  "dégradé sortira lisse ou en marches"),
            "ecart_type": ("écart-type du canal nommé par canal_mesure, sur la "
                           "même échelle que la moyenne"),
        },
        "maps": [
            {"fichier": m["kind"] + ".png", "kind": m["kind"],
             "px": [m["w"], m["h"]], "bits": m["bits"],
             "bits_demandes": m.get("bits_asked", m["bits"]),
             "niveaux_distincts": m.get("niveaux", 0),
             "niveaux_possibles": m.get("niveaux_max", 256),
             "precision_hors_8_bits_pct": m.get("sub", 0.0),
             "second_octet_bits": m.get("low_bits", 0.0),
             "second_octet_valeurs": m.get("low_vals", 0),
             "espace": m.get("space", ""), "octets": m["bytes"],
             "espace_declare_par_les_octets": m.get("space_decl", ""),
             "sha256": m.get("sha256", ""), "chunks": m.get("chunks", []),
             "dpi": m.get("dpi", [0, 0]),
             "moyenne": m["mean"], "amplitude_p95_p5": m["span"],
             "ecart_type": m.get("sd", 0.0),
             "echantillons_profondeur": m.get("ech", 0),
             "canal_mesure": m.get("mesure_sur", ""),
             "amplitude_mesure": m.get("span_def", SPAN_DEF),
             "informative": m["informative"], "note": m["note"],
             "pourquoi_vide": m.get("hint", ""),
             "corr_luminance_blocs192": m["corr_lum"],
             "corr_luminance_pleine_res": m.get("corr_full", 0.0)}
            for m in state.get("maps", [])
        ],
        "normale_unitaire": state.get("unit_normal", {}),
        # L'ORM EST-IL BIEN L'EMPAQUETAGE QU'IL ANNONCE : mesuré canal par
        # canal, et son coût de redondance publié avec.
        "orm_empaquetage": state.get("orm_pack", {}),
        "luminance_source": state.get("source_lum", {}),
        "octets_total": state.get("bytes_total", 0),
        # CE QUI MANQUE, PAS LA NOTE QU'ON SE DONNE : « 6 / 8 informatives » se
        # lit comme un bulletin, « 2 maps constantes » envoie l'acheteur
        # regarder lesquelles. Le compte est le même, sur les mêmes octets.
        "maps_constantes": sum(1 for m in state.get("maps", [])
                               if not m.get("informative")),
    }


def _source_info(d: Path) -> dict:
    out = {"ready": False, "custom": False}
    p = d / "source.png"
    if p.is_file():
        try:
            from PIL import Image
            with Image.open(p) as im:
                out.update({"ready": True, "w": im.size[0], "h": im.size[1],
                            "bytes": p.stat().st_size,
                            "stamp": int(p.stat().st_mtime)})
        except (OSError, ValueError):
            pass
    q = d / "paper.png"
    if q.is_file():
        try:
            from PIL import Image
            with Image.open(q) as im:
                out.update({"custom": True, "paper_w": im.size[0],
                            "paper_h": im.size[1],
                            "stamp": int(q.stat().st_mtime)})
        except (OSError, ValueError):
            pass
    return out


def read_state(did: str) -> dict:
    d = _dir_or_404(did)
    p = d / "report.json"
    state = {"maps": [], "informative": 0, "total": 0, "effective": {},
             "res": DEFAULT_RES, "bits16": True, "square": False,
             "source": _source_info(d), "updated": ""}
    if p.is_file():
        try:
            got = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(got, dict):
                got["source"] = _source_info(d)
                # une map effacée à la main ne doit pas rester affichée
                got["maps"] = [m for m in got.get("maps", [])
                               if isinstance(m, dict)
                               and (d / (str(m.get("kind")) + ".png")).is_file()]
                got["informative"] = sum(1 for m in got["maps"]
                                         if m.get("informative"))
                got["total"] = len(got["maps"])
                state = got
        except (OSError, ValueError) as e:
            logger.warning(f"cards/texture: report.json illisible ({did}): {e}")
    return state


# ── la planche : les huit maps sur une image, mesures écrites ───────────────

_FONT_CANDIDATES = (
    # les polices DÉJÀ servies par l'app (/fonts/) — aucune installation
    Path(__file__).resolve().parents[4] / "frontend" / "dist" / "fonts" / "IBMPlexSans.ttf",
    Path(__file__).resolve().parents[4] / "frontend" / "dist" / "fonts" / "Inter.ttf",
    Path(__file__).resolve().parents[4] / "frontend" / "dist" / "fonts" / "SpaceGrotesk.ttf",
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
)


def _font(size: int):
    """Une police qui a les ACCENTS. La police par défaut de Pillow rendait
    « rugosité » en « rugosit▯ » et « — » en carré : une planche de mesures
    illisible sur la moitié de ses mots ne mesure rien. Repli en cascade,
    puis la bitmap de Pillow en dernier ressort."""
    from PIL import ImageFont
    for p in _FONT_CANDIDATES:
        try:
            if p.is_file():
                return ImageFont.truetype(str(p), size)
        except (OSError, ValueError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(dr, text: str, font, width: int, maxi: int = 2) -> list[str]:
    """Texte replié sur au plus `maxi` lignes de `width` pixels.

    `_clip` coupe — et couper une CONVENTION de mesure la rend fausse : « p95
    − p5 sur … » ne dit plus sur quoi le nombre est lu, ce qui est exactement
    le trou qu'elle bouche. La dernière ligne, elle, est encore écourtée si
    rien ne tient : mieux vaut une fin en points de suspension qu'un texte qui
    déborde sur la case voisine."""
    mots = str(text).split()
    lignes: list[str] = []
    i = 0
    while i < len(mots) and len(lignes) < maxi - 1:
        j = i + 1
        while (j < len(mots)
               and dr.textlength(" ".join(mots[i:j + 1]), font=font) <= width):
            j += 1
        lignes.append(" ".join(mots[i:j]))
        i = j
    if i < len(mots):
        lignes.append(_clip(dr, " ".join(mots[i:]), font, width))
    return lignes or [""]


def _clip(dr, text: str, font, width: int) -> str:
    """Texte raccourci pour tenir dans la colonne. Une valeur qui déborde sur
    la case voisine se lit comme la valeur de la voisine."""
    s = str(text)
    if dr.textlength(s, font=font) <= width:
        return s
    while s and dr.textlength(s + "…", font=font) > width:
        s = s[:-1]
    return s + "…"


def build_sheet(did: str) -> bytes:
    from PIL import Image, ImageDraw
    d = _dir_or_404(did)
    state = read_state(did)
    rows = [m for m in state.get("maps", [])]
    if not rows:
        raise HTTPException(409, "Aucune map dérivée : lancer la dérivation "
                                 "avant de demander la planche")
    cols, cell, pad, head = 4, 300, 24, 116
    # La légende porte DEUX lignes de plus : la CONVENTION de mesure, et
    # l'espace colorimétrique sorti sur sa propre ligne. Tassés ensemble, ils
    # se faisaient couper par `_clip` et la densité disparaissait derrière un
    # « … » — une valeur tronquée se lit exactement comme une valeur absente.
    # 55 px de titre et de chiffres, puis TROIS lignes simples (écart-type,
    # compte de niveaux, espace colorimétrique), TROIS blocs de deux lignes de
    # 17 px (les deux mesures de profondeur, la convention de mesure, les
    # dimensions) et la note sur trois (voir `_wrap`) : le pire cas tient en
    # 55 + 3 x (17 + 2) + 3 x (2 x 17 + 2) + (3 x 17 + 2) = 273. Une légende
    # qui déborde recouvre la vignette de la rangée suivante.
    capt = 273
    W = pad + cols * (cell + pad)
    lines = (len(rows) + cols - 1) // cols
    H = head + lines * (cell + capt + pad) + pad
    sheet = Image.new("RGB", (W, H), _SHEET_BG)
    dr = ImageDraw.Draw(sheet)
    f_big, f_lab, f_val, f_sm = _font(28), _font(20), _font(16), _font(14)
    eff = state.get("effective") or {}
    phys = state.get("phys") or {}
    unit = state.get("unit_normal") or {}
    # LA PLANCHE NE SIGNE PAS ET NE SE NOTE PAS. Elle portait le nom de l'outil
    # en titre et un compte « X / 8 informatives » en sous-titre : une signature
    # de producteur et une auto-évaluation sur la seule pièce du lot qui circule.
    # Elle porte maintenant ce que le lot CONTIENT, en chiffres.
    plates = sum(1 for m in rows if not m.get("informative"))
    dr.text((pad, 22), "Les 8 maps PBR", font=f_big, fill=_SHEET_INK)
    dr.text((pad, 58), f"{len(rows)} maps"
                       + (f"   ·   {plates} constante(s)" if plates else "")
                       + f"   ·   sortie {state.get('out_px', '?')}"
                       f"   ·   rugosité effective {eff.get('roughness', 0):.3f}"
                       f"   ·   métal {eff.get('metallic', 0):.3f}"
                       f"   ·   dérivé à {state.get('work_px', '?')}",
            font=f_sm, fill=_SHEET_SOFT)
    ligne2 = ""
    if phys.get("ok"):
        # LE PLANCHER DE 300 DPI SE JUGE SUR LE PLUS PETIT DES DEUX AXES : un
        # atlas carré sur une carte qui ne l'est pas donne des pixels
        # rectangulaires, et c'est la hauteur qui tombe la première.
        seuil = ("" if phys.get("dpi_min", 0) >= 300
                 else f" — sous 300 DPI ({phys.get('dpi_min', 0)})")
        ligne2 += (f"pHYs écrit : {phys['dpi'][0]} x {phys['dpi'][1]} DPI"
                   f"{seuil}"
                   f"  ·  carte {phys['mm'][0]} x {phys['mm'][1]} mm"
                   f" (fond perdu {phys['bleed_mm']} mm, zone sûre "
                   f"{phys['safe_mm']} mm)  ·  ")
    ligne2 += "sRGB : basecolor, emissive  ·  linéaire : les six autres"
    dr.text((pad, 76), ligne2, font=f_sm, fill=_SHEET_SOFT)
    # TROISIÈME LIGNE, et pas une queue de la deuxième : tassée au bout,
    # « normale unitaire 100,0 % (|n| moy 1,00… » sortait du cadre de la
    # planche et le chiffre finissait coupé en deux. Une valeur tronquée se
    # lit exactement comme une valeur absente.
    # LA PHRASE GÉNÉRIQUE CÉDAIT LA PLACE À UN CHIFFRE. « moyenne et amplitude :
    # voir la convention sous chaque vignette » occupait la moitié de la ligne
    # et poussait « ORM empaqueté, écart max 0 » derrière les points de
    # suspension : une phrase qui se répète douze fois plus bas chassait la
    # seule mesure de la ligne. La convention reste collée sous chaque chiffre,
    # là où elle sert.
    ligne3 = ""
    if unit:
        ligne3 = (f"normale unitaire {unit.get('unit_pct', 0):.1f} % "
                  f"(|n| moy {unit.get('mean', 0):.5f}, "
                  f"z<0 : {unit.get('zneg', 0)} px sur {unit.get('px', 0)}, "
                  f"décodée sur {unit.get('bits', 8)} bits)")
    pack = state.get("orm_pack") or {}
    if pack.get("px"):
        e = pack.get("ecarts") or {}
        ligne3 += (("  ·  " if ligne3 else "")
                   + "ORM : mêmes valeurs que les trois maps séparées sur "
                   + f"{pack['px']} px, écart max "
                   + str(max((v for v in e.values() if v is not None),
                             default=0)))
    dr.text((pad, 94), _clip(dr, ligne3, f_sm, W - 2 * pad),
            font=f_sm, fill=_SHEET_SOFT)
    for i, m in enumerate(rows):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + (i // cols) * (cell + capt + pad)
        try:
            th = Image.open(d / ("thumb_" + m["kind"] + ".png"))
            th.load()
            th = th.convert("RGB")
            th.thumbnail((cell, cell), Image.LANCZOS)
            sheet.paste(th, (cx + (cell - th.size[0]) // 2,
                             cy + (cell - th.size[1]) // 2))
        except (OSError, ValueError, KeyError):
            dr.rectangle([cx, cy, cx + cell, cy + cell], outline=_SHEET_SOFT)
        dr.rectangle([cx, cy, cx + cell, cy + cell], outline=(52, 50, 47))
        dr.text((cx, cy + cell + 8), m["kind"], font=f_lab, fill=_SHEET_INK)
        # LA CONVENTION SOUS LE CHIFFRE. Sans elle, « moy 0,237 » sur la base
        # color est une luminance Rec.601 que personne ne retrouve en faisant
        # la moyenne des trois canaux (0,304), et la planche — la pièce qu'on
        # montre à un tiers — devient la preuve d'un mensonge qui n'existe pas.
        amp = m["span"]
        amp_txt = f"{amp:.2f}" if isinstance(amp, float) else str(amp)
        # L'ÉCART-TYPE PASSE À LA LIGNE. Serré derrière la moyenne et
        # l'amplitude, `_clip` le coupait : « é.-t. 26… » sur la normale et
        # « é.-t. 8… » sur la hauteur — un chiffre tronqué se lit exactement
        # comme un chiffre absent, et c'est le défaut que cette planche
        # s'interdit ailleurs.
        dr.text((cx, cy + cell + 34),
                _clip(dr, f"moy {m['mean']:.3f}   ampl. {amp_txt}/255",
                      f_val, cell),
                font=f_val, fill=_SHEET_ACCENT if m["informative"] else _SHEET_SOFT)
        # LA CONVENTION NE SE COUPE PAS. Mesuré sur la planche livrée : la
        # normale affichait « canal R (relief X), lu sur 16 bits · p95 − p5
        # sur … » — l'échelle de lecture de l'amplitude, c'est-à-dire le seul
        # mot qui empêche de recalculer un autre chiffre, disparaissait
        # derrière les points de suspension. Elle passe donc à la ligne.
        # LES DEUX MESURES DE PROFONDEUR PRENNENT LEUR PROPRE LIGNE. Serrées
        # derrière les dimensions et la densité, `_wrap` les coupait au dernier
        # chiffre (« second octet 3.92… ») — et un chiffre tronqué se lit
        # exactement comme un chiffre absent, ce que cette planche s'interdit
        # partout ailleurs.
        prof = f"{m['bits']} bits"
        if m.get("bits") != 16 and m.get("bits_asked") == 16:
            prof += " (16 demandés, sans effet)"
        prof16 = ""
        if m.get("bits") == 16:
            prof16 = (f"{m.get('sub', 0):.1f} % des points trop fins pour un "
                      f"octet · second octet {m.get('low_bits', 0):.2f}/8 sur "
                      f"{m.get('ech', 0)} points")
        dpi = m.get("dpi") or [0, 0]
        dtxt = (f" · {dpi[0]}x{dpi[1]} DPI" if dpi[0] and dpi[0] != dpi[1]
                else (f" · {dpi[0]} DPI" if dpi[0] else ""))
        # LES LIGNES SE SUIVENT AU LIEU D'ÊTRE POSÉES À DES HAUTEURS FIXES :
        # une ligne qui déborde en pousse une autre, elle ne l'écrase pas et
        # ne se fait pas couper. Mesuré sur la planche livrée : la normale
        # affichait « p95 − p5 sur … » et « octet f… » — l'échelle de lecture
        # et la deuxième mesure de profondeur, c'est-à-dire les deux seuls
        # mots qui empêchent de recalculer un autre chiffre, disparaissaient
        # derrière des points de suspension.
        y = cy + cell + 55
        for txt, fill, maxi in (
                (f"é.-t. {m.get('sd', 0):.2f}/255", _SHEET_SOFT, 1),
                # CE QUE LA MAP PORTE, pas ce que son en-tête permet : le
                # compte des valeurs réellement présentes dans le canal mesuré.
                (f"{m.get('niveaux', 0)} niveaux distincts sur "
                 f"{m.get('niveaux_max', 256)}", _SHEET_SOFT, 1),
                (prof16, _SHEET_SOFT, 2),
                (f"{m.get('mesure_sur', '')} · {m.get('span_def', SPAN_DEF)}",
                 _SHEET_SOFT, 2),
                (f"{m['w']}x{m['h']} · {prof}{dtxt}", _SHEET_SOFT, 2),
                # L'ESPACE SUR SA PROPRE LIGNE : collé au reste, « sRGB
                # (chunks sRGB + gAMA 0,45455) » mangeait la densité.
                (m.get("space_decl") or m.get("space", ""), _SHEET_SOFT, 1),
                # la note est une PHRASE : lui couper son dernier mot
                # (« information peu indépendante de l'image sou… ») est le
                # même défaut, en plus petit.
                (m.get("hint") or m.get("note")
                 or ("" if m["informative"] else "constante"),
                 _SHEET_GREEN if m["informative"] else _SHEET_SOFT, 3)):
            for ligne in _wrap(dr, txt, f_sm, cell, maxi):
                dr.text((cx, y), ligne, font=f_sm, fill=fill)
                y += 17
            y += 2
    buf = io.BytesIO()
    sheet.save(buf, format="PNG", optimize=False)
    # LA PLANCHE PORTE SES CHUNKS, ELLE AUSSI. Incohérence relevée et vraie :
    # les huit maps portaient gAMA/sRGB/pHYs/tEXt, et la planche — la seule
    # pièce du lot qu'on montre à un tiers — n'en portait AUCUN. Elle déclare
    # donc sa densité (300 DPI pile, 11811 px/m) et la taille qu'elle fait une
    # fois imprimée à cette densité ; c'est vérifiable à la règle.
    mm_w = round(W * 25.4 / SHEET_DPI, 1)
    mm_h = round(H * 25.4 / SHEET_DPI, 1)
    return _with_meta(buf.getvalue(), "basecolor", (SHEET_PPM, SHEET_PPM),
                      f"planche de controle des 8 maps - {W}x{H} px a "
                      f"{SHEET_DPI} DPI, soit {mm_w}x{mm_h} mm imprimee")


# ── routes ──────────────────────────────────────────────────────────────────

def _png(data: bytes) -> Response:
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.get("/state")
async def get_state(did: str):
    """L'état complet, mesures comprises. Sert aussi de sonde : l'écran ne
    dessine la grille des 8 maps que si elle existe VRAIMENT sur disque."""
    return {"texture": await asyncio.to_thread(read_state, did)}


@router.get("/defaults")
async def get_defaults(did: str):
    """Défauts et bornes de dérivation — pris sur `pbr_service`, jamais
    recopiés : deux tables pour un même réglage, c'est un curseur qui ment."""
    _dir_or_404(did)
    from app.services import pbr_service as pbr
    return {
        "defaults": dict(pbr.DERIVE_DEFAULTS),
        "ranges": {k: list(v) for k, v in pbr.DERIVE_RANGES.items()},
        "metallic_modes": list(pbr.METALLIC_MODES),
        "roughness_sources": list(pbr.ROUGHNESS_SOURCES),
        "kinds": list(MAP_ORDER),
        "res_choices": list(RES_CHOICES),
        "bits16_kinds": list(BITS16_KINDS),
        "work_max": WORK_MAX,
        "flat_span": pbr.FLAT_SPAN,
    }


def _store_image(did: str, name: str, raw: bytes, cap: int | None = None) -> dict:
    from PIL import Image
    d = _dir_or_404(did, create=True)
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    img = img.convert("RGB")
    if cap and max(img.size) > cap:
        k = cap / float(max(img.size))
        img = img.resize((max(1, round(img.size[0] * k)),
                          max(1, round(img.size[1] * k))), Image.LANCZOS)
    tmp = d / (name + ".tmp")
    img.save(tmp, format="PNG", optimize=False)
    tmp.replace(d / name)
    return {"w": img.size[0], "h": img.size[1],
            "bytes": (d / name).stat().st_size, "stamp": int(time.time())}


@router.post("/source")
async def post_source(did: str, request: Request):
    """La carte rendue à l'échelle 1 par le moteur unique — corps BRUT.
    C'est d'elle, et de rien d'autre, que les 8 maps sont dérivées : ce que
    l'écran montre est ce que le PBR mesure."""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer le PNG de la carte")
    if len(raw) > SRC_MAX_BYTES:
        raise HTTPException(400, "Image trop lourde (max 64 Mo)")
    info = await asyncio.to_thread(_store_image, did, "source.png", raw)
    return {"source": info}


@router.post("/paper")
async def post_paper(did: str, request: Request):
    """Une image importée par l'utilisateur, utilisée comme matière du
    support. La barre n'accepte aucune image : elle ne sait que générer."""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer une image")
    if len(raw) > SRC_MAX_BYTES:
        raise HTTPException(400, "Image trop lourde (max 64 Mo)")
    info = await asyncio.to_thread(_store_image, did, "paper.png", raw,
                                   PAPER_MAX_PX)
    return {"paper": info}


@router.get("/paper")
async def get_paper(did: str):
    d = _dir_or_404(did)
    p = d / "paper.png"
    if not p.is_file():
        raise HTTPException(404, "Aucune matière importée")
    return _png(await asyncio.to_thread(p.read_bytes))


@router.post("/tile")
async def post_tile(did: str, request: Request, mat: str = "", seed: int = 0):
    """La tuile de matière peinte par l'écran — corps BRUT — RE-MESURÉE ici.

    Les trente rapports de raccord affichés par l'écran étaient les seuls
    chiffres de cette pièce sans un octet derrière eux. Ils en ont un : le PNG
    est décodé, sa couture recalculée sur les pixels reçus, et le fichier rendu
    porte le résultat dans ses chunks `tEXt` — vérifiable sans nous croire.
    """
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer le PNG de la tuile")
    if len(raw) > SRC_MAX_BYTES:
        raise HTTPException(400, "Image trop lourde (max 64 Mo)")
    info = await asyncio.to_thread(store_tile, did, raw, mat, seed)
    return {"tile": info}


@router.get("/tile")
async def get_tile(did: str):
    """La dernière tuile exportée, mesures inscrites dans ses chunks."""
    d = _dir_or_404(did)
    p = d / "tile.png"
    if not p.is_file():
        raise HTTPException(404, "Aucune tuile exportée")
    return _png(await asyncio.to_thread(p.read_bytes))


@router.post("/derive")
async def post_derive(did: str, body: dict | None = None):
    """Les 8 maps, dérivées puis MESURÉES sur les octets écrits."""
    opts = _opts(body)
    try:
        state = await asyncio.to_thread(derive_deck, did, opts)
    except HTTPException:
        raise
    except MemoryError:
        raise HTTPException(409, "Mémoire insuffisante à cette résolution : "
                                 "réessayer en 1k ou 2k")
    except Exception as e:
        logger.exception("cards/texture: dérivation impossible")
        raise HTTPException(500, f"Dérivation impossible: {e}")
    return {"texture": state}


@router.get("/map/{kind}")
async def get_map(did: str, kind: str):
    """Le PNG livrable — 16 bits pour hauteur et normale quand c'est demandé."""
    k = _kind_or_400(kind)
    d = _dir_or_404(did)
    p = d / (k + ".png")
    if not p.is_file():
        raise HTTPException(404, f"Map {k} absente : lancer la dérivation")
    return _png(await asyncio.to_thread(p.read_bytes))


def _resample(path: Path, kind: str, px: int) -> bytes:
    """Le FICHIER LIVRÉ, rééchantillonné pour l'écran — pas une copie mémoire.

    La table lumineuse ré-éclaire ces octets-là. Les lui servir depuis le PNG
    écrit sur le disque (et non depuis l'image encore en mémoire au moment de
    la dérivation) est ce qui rend vraie la phrase « ce que vous éclairez est
    ce que vous téléchargez » : une divergence entre les deux serait
    exactement le genre d'écart que ce panneau reproche aux autres.

    Une map 16 bits est ramenée à 8 bits pour l'affichage — c'est écrit à côté
    du rendu, et sans objet pour un ré-éclairage à l'écran de toute façon.
    """
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        img = _as_mode(im, kind)
        w, h = img.size
        k = min(1.0, px / float(max(w, h) or 1))
        if k < 1.0:
            img = img.resize((max(1, round(w * k)), max(1, round(h * k))),
                             Image.LANCZOS if kind in SRGB_KINDS
                             else Image.BICUBIC)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return buf.getvalue()


@router.get("/thumb/{kind}")
async def get_thumb(did: str, kind: str, px: int | None = None):
    """La vignette. `px` (64..768) rend le FICHIER LIVRÉ rééchantillonné à
    cette taille au lieu de la vignette de 320 px figée à la dérivation."""
    k = _kind_or_400(kind)
    d = _dir_or_404(did)
    if px is not None:
        p = d / (k + ".png")
        if not p.is_file():
            raise HTTPException(404, f"Map {k} absente : lancer la dérivation")
        n = max(64, min(LIT_MAX_PX, int(px)))
        return _png(await asyncio.to_thread(_resample, p, k, n))
    p = d / ("thumb_" + k + ".png")
    if not p.is_file():
        p = d / (k + ".png")
    if not p.is_file():
        raise HTTPException(404, f"Map {k} absente : lancer la dérivation")
    return _png(await asyncio.to_thread(p.read_bytes))


@router.get("/manifest")
async def get_manifest(did: str):
    """Le contrat du lot, en JSON : espaces colorimétriques, densité physique,
    conventions, empreintes SHA-256. Sans lui, les noms de fichiers sont le
    seul contrat du livrable."""
    d = _dir_or_404(did)
    p = d / "manifest.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    state = await asyncio.to_thread(read_state, did)
    if not state.get("maps"):
        raise HTTPException(409, "Aucune map dérivée : lancer la dérivation "
                                 "avant de demander le manifeste")
    return build_manifest(state)


@router.get("/sheet")
async def get_sheet(did: str):
    """Les 8 maps sur une image, chacune avec sa mesure écrite dessous."""
    try:
        data = await asyncio.to_thread(build_sheet, did)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("cards/texture: planche impossible")
        raise HTTPException(500, f"Planche impossible: {e}")
    return _png(data)


@router.delete("/maps")
async def delete_maps(did: str):
    d = _dir_or_404(did)

    def _wipe() -> int:
        n = 0
        for kind in MAP_ORDER:
            for name in (kind + ".png", "thumb_" + kind + ".png"):
                f = d / name
                if f.is_file():
                    f.unlink()
                    n += 1
        (d / "report.json").unlink(missing_ok=True)
        (d / "manifest.json").unlink(missing_ok=True)
        return n

    return {"ok": True, "removed": await asyncio.to_thread(_wipe)}
