# -*- coding: utf-8 -*-
"""Card Forge — P3 « Typographie ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/type`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P3. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). Ce dont il a besoin vient de
`cards/contract.py` (géométrie, `deck_dir`) — jamais d'un voisin.

Le module s'appelle `type`, comme la fonction native : `cards/__init__.py`
l'importe sous alias pour ne pas la masquer. Ici on n'écrit JAMAIS `type(x)`.

CE QUE CE FICHIER FAIT — et surtout ce qu'il ne fait PAS :

  * il NE DESSINE RIEN. Le texte est rendu par le navigateur, au painter z=60,
    sur la toile de `geom.canvas_px` : un seul moteur (risque 2 de la spec).
    Un deuxième moteur ici ferait diverger l'écran et le fichier livré.
  * il sert le CATALOGUE DES POLICES réellement présentes sur le disque
    (`frontend/dist/fonts`, servi en `/fonts/`) — 23 familles, 22 `.ttf` plus
    `PolandKaito.otf`. L'extension est LUE, jamais devinée.
  * il sert les GABARITS de slots. Un gabarit est exprimé en fractions de la
    ZONE SÛRE, pas de la rogne : converti pour un format donné, il tombe donc
    dans la zone sûre des douze formats par construction — y compris `micro`
    (31,75 mm de large pour 3,175 mm de zone sûre, soit 10 % de marge de
    chaque côté, là où `jumbo` n'en demande que 3,6 %). Un gabarit en
    fractions de la ROGNE sortait de la zone sûre sur les petits formats.
  * il JUGE une mise en page : boîtes en pixels de toile, et confinement dans
    la zone sûre. La mesure des glyphes reste au navigateur (lui seul a les
    polices chargées et le même moteur de texte que le fichier livré) ; il
    renvoie ses encombrements mesurés (`ink`) et le backend dit oui ou non
    avec la même règle de géométrie que l'imprimeur. C'est le contrôle que P7
    reprendra avant vol.

Le contrat sortant de la pièce est `doc.type.slots[]` (spec §2.3) :
`{id, label, box:[x, y, w, h] en mm depuis le coin ROGNE, ...}` — lu par P4
(menu de mappage) et par P7 (contrôle avant vol).
"""
from __future__ import annotations

import asyncio
import copy
import io
import math
import pathlib
import re
import struct

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from .contract import (
    DEFAULT_DPI,
    DEFAULT_FMT,
    FORMATS,
    MM_PER_INCH,
    deck_dir,
    geom as geom_of,
    is_valid_did,
    rnd,
)

router = APIRouter()

# ════════════════════════════════════════════════════════════════════════════
# 1. LES POLICES — celles qui sont VRAIMENT sur le disque
# ════════════════════════════════════════════════════════════════════════════
# 23 fichiers servis sur `/fonts/` par le montage racine de la SPA : 22 `.ttf`
# et UN `.otf` (PolandKaito). Le piège documenté par la spec est de deviner
# l'extension ; ici on lit le dossier, et la table ci-dessous ne porte que ce
# qui ne se lit pas dans un nom de fichier : le libellé et la famille d'usage.

FONT_KINDS: dict[str, str] = {
    "titre": "Titres",
    "fantasy": "Fantasy",
    "texte": "Texte courant",
    "mono": "Chasse fixe",
    "manuscrit": "Manuscrites",
    "retro": "Rétro / jeu",
    "autre": "Autres",
}

# stem du fichier -> (libellé lisible, famille d'usage)
FONT_META: dict[str, tuple[str, str]] = {
    "AbrilFatface": ("Abril Fatface", "titre"),
    "Anton": ("Anton", "titre"),
    "ArchivoBlack": ("Archivo Black", "titre"),
    "BebasNeue": ("Bebas Neue", "titre"),
    "Bungee": ("Bungee", "titre"),
    "Righteous": ("Righteous", "titre"),
    "Staatliches": ("Staatliches", "titre"),
    "Cinzel": ("Cinzel", "fantasy"),
    "DistantGalaxy": ("Distant Galaxy", "fantasy"),
    "PolandKaito": ("Poland Kaito", "fantasy"),
    "IBMPlexSans": ("IBM Plex Sans", "texte"),
    "Inter": ("Inter", "texte"),
    "SpaceGrotesk": ("Space Grotesk", "texte"),
    "JetBrainsMono": ("JetBrains Mono", "mono"),
    "DrippingMarker": ("Dripping Marker", "manuscrit"),
    "GraffitiBrush": ("Graffiti Brush", "manuscrit"),
    "Pacifico": ("Pacifico", "manuscrit"),
    "PermanentMarker": ("Permanent Marker", "manuscrit"),
    "SuperFeel": ("Super Feel", "manuscrit"),
    "SuperPencil": ("Super Pencil", "manuscrit"),
    "Hacked": ("Hacked", "retro"),
    "Monoton": ("Monoton", "retro"),
    "PressStart2P": ("Press Start 2P", "retro"),
}

FONT_EXTS = (".ttf", ".otf", ".woff2", ".woff")
FONT_FAMILY_PREFIX = "CFT "     # le nom sous lequel le navigateur les charge
FONT_FALLBACK = "Inter"

# ────────────────────────────────────────────────────────────────────────────
# CE QU'UNE POLICE SAIT ÉCRIRE — LU DANS LE FICHIER, PAS SUPPOSÉ
#
# « 23 polices » était un compte de FICHIERS. Qu'un de ces fichiers sache
# écrire « Créature » en est une AUTRE affirmation, et personne ne la
# vérifiait. Le navigateur, lui, ne prévient pas : un glyphe absent est
# remplacé en silence par celui d'une autre police (repli par caractère), et
# le mot part chez l'imprimeur avec un é d'une fonte étrangère. C'est
# exactement la faute que cette pièce refuse ailleurs — perdre du texte sans
# le dire — sauf qu'elle se joue ici sur UN caractère.
#
# On lit donc la table `cmap` de chaque fichier, sur ses octets, et on publie
# les caractères du répertoire français qui n'y sont PAS. Mesure, pas promesse.
# Résultat sur le catalogue servi (compté, pas estimé — `test_cards_type.py`
# le rejoue sur les fichiers réels) : 18 familles sur 23 portent les 41
# caractères ci-dessous ; 5 ne les portent pas, dont trois qui n'ont presque
# aucun accent (Poland Kaito 37 manquants, Graffiti Brush 38, Dripping Marker
# 41 sur 41). Distant Galaxy en manque 5 et Hacked 4.
# ────────────────────────────────────────────────────────────────────────────
# Le répertoire minimal d'un jeu de cartes en français : accents, ligatures,
# guillemets, points de suspension, tiret cadratin, apostrophe typographique.
FR_PROBE = "ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒàâäçéèêëîïôöùûüÿæœ«»…—’"

_SFNT_TAGS = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1")


def _sfnt_tables(b: bytes) -> dict[bytes, tuple[int, int]]:
    """Le répertoire de tables d'un fichier sfnt (`.ttf`, `.otf`, `.ttc`)."""
    if len(b) < 12:
        return {}
    off = 0
    tag = b[:4]
    if tag == b"ttcf":                      # collection : on prend la 1re fonte
        if len(b) < 16:
            return {}
        (n,) = struct.unpack_from(">I", b, 8)
        if n < 1:
            return {}
        (off,) = struct.unpack_from(">I", b, 12)
        tag = b[off:off + 4]
    if tag not in _SFNT_TAGS or off + 12 > len(b):
        return {}
    (num,) = struct.unpack_from(">H", b, off + 4)
    out: dict[bytes, tuple[int, int]] = {}
    p = off + 12
    for _ in range(min(num, 512)):
        if p + 16 > len(b):
            break
        out[b[p:p + 4]] = struct.unpack_from(">II", b, p + 8)
        p += 16
    return out


def _cmap_subtable(b: bytes, off: int) -> set[int]:
    """Les points de code d'UNE sous-table cmap (formats 0, 4, 6, 12)."""
    cps: set[int] = set()
    if off + 4 > len(b):
        return cps
    (fmt,) = struct.unpack_from(">H", b, off)
    if fmt == 0:
        if off + 262 > len(b):
            return cps
        for c in range(256):
            if b[off + 6 + c]:
                cps.add(c)
    elif fmt == 4:
        (segx2,) = struct.unpack_from(">H", b, off + 6)
        seg = segx2 // 2
        end, start = off + 14, off + 14 + segx2 + 2
        delta, rng = start + segx2, start + 2 * segx2
        if rng + segx2 > len(b):
            return cps
        for i in range(seg):
            (e,) = struct.unpack_from(">H", b, end + i * 2)
            (s,) = struct.unpack_from(">H", b, start + i * 2)
            (d,) = struct.unpack_from(">h", b, delta + i * 2)
            (r,) = struct.unpack_from(">H", b, rng + i * 2)
            if s > e:
                continue
            for c in range(s, min(e, 0xFFFE) + 1):
                if r == 0:
                    g = (c + d) & 0xFFFF
                else:
                    gi = rng + i * 2 + r + (c - s) * 2
                    if gi + 2 > len(b):
                        continue
                    (g,) = struct.unpack_from(">H", b, gi)
                    if g:
                        g = (g + d) & 0xFFFF
                if g:
                    cps.add(c)
    elif fmt == 6:
        if off + 10 > len(b):
            return cps
        first, cnt = struct.unpack_from(">HH", b, off + 6)
        for i in range(cnt):
            if off + 10 + i * 2 + 2 > len(b):
                break
            (g,) = struct.unpack_from(">H", b, off + 10 + i * 2)
            if g:
                cps.add(first + i)
    elif fmt == 12:
        if off + 16 > len(b):
            return cps
        (n,) = struct.unpack_from(">I", b, off + 12)
        for i in range(min(n, 100000)):
            if off + 16 + i * 12 + 12 > len(b):
                break
            s, e, _g = struct.unpack_from(">III", b, off + 16 + i * 12)
            if e < s or e - s > 0x10FFFF:
                continue
            cps.update(range(s, min(e, 0x10FFFF) + 1))
    return cps


# on préfère la sous-table la plus large : Unicode complet (3/10, 0/4) avant le
# plan de base (3/1, 0/3), et le symbole ou le legacy Mac en dernier recours.
_CMAP_RANK = {(3, 10): 5, (0, 4): 5, (0, 6): 5, (3, 1): 4, (0, 3): 4,
              (0, 0): 3, (0, 1): 3, (0, 2): 3, (3, 0): 2, (1, 0): 1}


def font_codepoints(path: pathlib.Path) -> set[int] | None:
    """Les points de code que ce FICHIER porte réellement.

    `None` quand la table est illisible (fichier compressé `.woff2`, sfnt
    tronqué) : dans ce cas l'écran doit dire « inconnu », jamais « couvert »."""
    try:
        b = path.read_bytes()
    except OSError:
        return None
    tables = _sfnt_tables(b)
    if b"cmap" not in tables:
        return None
    off = tables[b"cmap"][0]
    if off + 4 > len(b):
        return None
    (n,) = struct.unpack_from(">H", b, off + 2)
    best: tuple[int, int] | None = None
    for i in range(min(n, 64)):
        if off + 4 + i * 8 + 8 > len(b):
            break
        pid, eid, sub = struct.unpack_from(">HHI", b, off + 4 + i * 8)
        rank = _CMAP_RANK.get((pid, eid), 0)
        if best is None or rank > best[0]:
            best = (rank, off + sub)
    if best is None:
        return None
    try:
        cps = _cmap_subtable(b, best[1])
    except (struct.error, IndexError, MemoryError, ValueError):
        return None
    return cps or None


def missing_chars(text: str, missing: set[str]) -> list[str]:
    """Les caractères DISTINCTS de `text` absents de la police, dans l'ordre où
    ils apparaissent. Les blancs ne comptent pas : ils ne se voient pas."""
    seen: list[str] = []
    for ch in str(text):
        if ch in missing and ch not in seen and not ch.isspace():
            seen.append(ch)
    return seen


# le scan lit 23 fichiers (3,9 Mo) : on garde le résultat tant que ni la taille
# ni la date de modification n'ont bougé. Le catalogue reste donc juste si un
# fichier est remplacé, sans relire 3,9 Mo à chaque ouverture du panneau.
_FONT_CACHE: dict[tuple, list[dict]] = {}


def fonts_dir() -> pathlib.Path:
    """Le dossier réellement servi en `/fonts/` : `frontend/dist/fonts`.

    Même dérivation que `app/main.py` pour le montage de la SPA — quatre
    parents au-dessus de `cards/type.py`, donc la racine du dépôt (ou de
    l'application installée, qui a la même forme)."""
    return pathlib.Path(__file__).resolve().parents[4] / "frontend" / "dist" / "fonts"


def _pretty(stem: str) -> str:
    """Libellé de repli pour une police non répertoriée : « PressStart2P »
    devient « Press Start 2P ». Une police posée dans le dossier après coup
    apparaît donc dans le menu au lieu d'être ignorée."""
    out = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
    out = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", out)
    return out.strip() or stem


def scan_fonts(directory: pathlib.Path | None = None) -> list[dict]:
    """Les polices présentes, triées par famille d'usage puis par libellé.

    Chaque entrée porte ce que le FICHIER sait écrire : `cmap_pts` (nombre de
    points de code lus dans sa table cmap) et `fr_missing` (les caractères du
    répertoire français qui n'y sont pas). Les deux sortent des octets."""
    d = directory or fonts_dir()
    out: list[dict] = []
    if not d.is_dir():
        return out
    files = [p for p in sorted(d.iterdir())
             if p.is_file() and p.suffix.lower() in FONT_EXTS]
    stamp = []
    for p in files:
        try:
            st = p.stat()
            stamp.append((p.name, st.st_size, int(st.st_mtime_ns)))
        except OSError:
            stamp.append((p.name, 0, 0))
    key = (str(d), tuple(stamp))
    hit = _FONT_CACHE.get(key)
    if hit is not None:
        return copy.deepcopy(hit)
    for p in files:
        label, kind = FONT_META.get(p.stem, (_pretty(p.stem), "autre"))
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        cps = font_codepoints(p)
        out.append({
            "id": p.stem,
            "label": label,
            "kind": kind,
            "kind_label": FONT_KINDS.get(kind, FONT_KINDS["autre"]),
            "family": FONT_FAMILY_PREFIX + p.stem,
            "file": p.name,
            "ext": p.suffix.lower().lstrip("."),
            "url": "/fonts/" + p.name,
            "bytes": size,
            # None = table illisible. L'écran doit alors dire « inconnu » :
            # une liste vide voudrait dire « tout est là », ce qui serait une
            # affirmation gratuite — exactement ce qu'on refuse ici.
            "cmap_pts": (len(cps) if cps else None),
            "fr_missing": (None if cps is None
                           else [c for c in FR_PROBE if ord(c) not in cps]),
        })
    # COMBIEN DE FICHIERS PORTENT CETTE FAMILLE — compté, pas supposé. Le
    # catalogue sert 23 fichiers pour 23 familles : UNE graisse et UN style par
    # famille. Le bouton G de l'écran ne peut donc pas charger un vrai gras, il
    # ne peut que faire épaissir le trait par le navigateur ; l'écran le dit
    # au lieu de laisser croire à une graisse dessinée. Si un jour une famille
    # reçoit un second fichier, ce compteur passe à 2 tout seul.
    per_family: dict[str, int] = {}
    for f in out:
        per_family[f["family"]] = per_family.get(f["family"], 0) + 1
    for f in out:
        f["faces"] = per_family[f["family"]]
        f["synthetic_bold"] = per_family[f["family"]] < 2
        f["fr_ok"] = (None if f["fr_missing"] is None else not f["fr_missing"])
    order = list(FONT_KINDS)
    out.sort(key=lambda f: (order.index(f["kind"]) if f["kind"] in order else 99,
                            f["label"].lower()))
    _FONT_CACHE.clear()
    _FONT_CACHE[key] = copy.deepcopy(out)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 2. LES GABARITS — en fractions de la ZONE SÛRE
# ════════════════════════════════════════════════════════════════════════════
# `rel` = [x, y, w, h] dans le repère de la zone sûre (0..1). La conversion en
# millimètres depuis le coin ROGNE se fait avec la zone sûre du format demandé
# — c'est ce qui rend un gabarit valable sur les douze formats sans le
# redessiner, `micro` compris.
#
# CE BLOC EST MIROIR de `frontend/cardforge/js/mod-type.js`, entre les
# marqueurs CF-TYPE-PRESETS. `test_cards_type.py` extrait le bloc JS et le
# compare à ce dictionnaire, clé par clé : une divergence fait rougir la
# suite. (Le lab doit servir les mêmes gabarits hors ligne que le backend en
# ligne ; deux tables recopiées à la main auraient dérivé au premier ajout.)

SLOT_DEFAULTS: dict = {
    "id": "slot",
    "label": "Texte",
    "box": [0.0, 0.0, 10.0, 5.0],
    "font": FONT_FALLBACK,
    "size_pt": 10.0,
    "min_pt": 5.0,
    # PLANCHER DE LISIBILITÉ, en points, PAR NATURE DE BLOC. `min_pt` est un
    # plancher d'ENCOMBREMENT : il dit jusqu'où l'ajustement automatique a le
    # droit de descendre pour faire tenir le texte. Il ne dit RIEN de la
    # lisibilité une fois la carte imprimée — un titre ramené de 14 à 9 pt
    # « tient » et ne se lit plus. `read_pt` est l'autre plancher : celui du
    # métier. Il n'empêche RIEN (couper serait pire que rétrécir) ; il fait
    # dire au relevé « ce bloc est en dessous », ce que le badge « ajusté »
    # taisait. 0 = pas de plancher déclaré.
    "read_pt": 0.0,
    "color": "#f2efe9",
    "align": "left",       # left | center | right | justify
    "valign": "top",
    "track": 0.0,          # interlettrage, en % du cadratin
    "leading": 1.18,       # interligne, multiple du corps
    # Élasticité maximale d'un blanc justifié, en % de l'espace naturel de la
    # fonte. Au-delà, l'écran fait passer le supplément dans l'interlettrage de
    # la ligne : c'est le seul défaut que produit une justification, et le
    # plafond du métier est 133 %. 100 = aucun étirement.
    "just_max": 133.0,
    # Longueur minimale de la dernière ligne d'un paragraphe, en % de la
    # justification (règle classique : au moins un quart). En dessous, l'écran
    # descend le dernier mot de la ligne précédente. 0 = contrôle désactivé.
    "last_pct": 25.0,
    "hyphen": False,       # cesure automatique (l'ecran coupe, pas le backend)
    "caps": "none",        # none | upper | lower | title
    "bold": False,
    "italic": False,
    "outline": 0.0,        # contour, en pt
    "outline_color": "#0a0a0c",
    "shadow": 0.0,         # flou de l'ombre portée, en pt
    "shadow_color": "#000000",
    "shadow_dx": 0.0,
    "shadow_dy": 0.0,
    # ── LA PLAQUE DE FOND DU SLOT (spec §6.1) ──────────────────────────────
    # Un rectangle (éventuellement arrondi) peint SOUS le texte du slot, dans
    # la même passe et dans la MÊME boîte : c'est le cartouche derrière un
    # encadré de règles, la pastille derrière un coût, la barre derrière un
    # nom. Elle appartient à P3 et pas à P2 parce qu'elle suit le slot quand
    # on le déplace — un ornement de cadre, lui, ne bouge pas.
    #
    # `None` = PAS DE PLAQUE, et c'est le défaut. C'est ce qui rend les quatre
    # gabarits livrés byte-identiques après l'ajout : aucun ne nomme la
    # plaque, tous héritent du défaut, et le défaut ne peint rien. L'alpha
    # vaut 1 pour que poser une couleur suffise à voir quelque chose ; il ne
    # sert à rien tant que `plate_color` est nul.
    "plate_color": None,   # hex (#rgb, #rrggbb, #rrggbbaa) ou None
    "plate_alpha": 1.0,    # 0..1, multiplié par l'opacité du slot
    "plate_radius": 0.0,   # rayon des coins, en mm
    "rotate": 0.0,         # degrés
    "arc": 0.0,            # -100..100, texte sur arc
    "autofit": True,       # rétrécir-pour-tenir
    "wrap": True,          # retour à la ligne
    "opacity": 100.0,
    "side": "front",       # front | back | both
    "on": True,
    # ── LE VERROU (spec §6.1, « liste de calques ordonnée … verrouillage ») ──
    # Un bloc verrouillé refuse les GESTES DE SCÈNE de l'écran d'édition —
    # glisser, poignées, flèches, Suppr au clavier — et rien d'autre : il reste
    # sélectionnable (c'est par là qu'on le déverrouille) et le panneau
    # continue de le régler. Le verrou protège de la main qui dérape, pas de
    # l'intention.
    #
    # Le backend ne l'INTERPRÈTE pas : il le transporte. Aucun painter ne le
    # lit, aucun calcul de mise en page ne le regarde — c'est exactement ce qui
    # rend les quatre gabarits livrés byte-identiques après son arrivée. Il est
    # ici, et non dans un état d'écran, parce qu'il doit voyager avec le deck :
    # un bloc protégé qui redevient libre à la réouverture ne protège rien.
    "lock": False,
    # ── LE CALQUE D'IMAGE (spec §6.1, « calque d'image/motif ») ─────────────
    # La spec veut que les éléments ajoutables soient « instanciés comme des
    # objets Cardforge ORDINAIRES ». Un calque d'image est donc un slot P3
    # d'une autre NATURE, pas un objet neuf : il hérite ainsi, gratuitement, de
    # l'ordre de peinture dans la bande z=60, de l'œil, du verrou, du calque
    # d'édition (glisser, poignées, flèches), de l'annulation et de la
    # fluidité. La pile de calques d'un éditeur d'images, pour le prix d'une
    # clé.
    #
    # `kind: "text"` PAR DÉFAUT — c'est ce qui rend les quatre gabarits livrés
    # byte-identiques après l'ajout, et ce qui fait qu'un document écrit avant
    # la 3b reste exactement ce qu'il était.
    #
    # Un calque d'image IGNORE les clés typographiques ; elles ne sont pas
    # retirées de l'objet (la parité stricte des deux tables prime, et un slot
    # partiel obligerait chaque lecteur à connaître les défauts). Elles sont
    # INERTES : le painter ne les lit pas sur cette branche, et le panneau ne
    # les montre pas.
    "kind": "text",        # text | image
    # `""` ou `img:{fichier}` — un NOM, jamais un chemin. Le fichier est écrit
    # par `POST /image` dans le dossier du deck, et son nom est fabriqué par le
    # serveur (`img_{n}.png`) : le motif ci-dessous est donc EXACT, pas
    # permissif. Le stockage est côté serveur et non dans le navigateur parce
    # qu'un calque de deck doit VOYAGER avec le deck (export, duplication).
    "src": "",
    "fit": "contain",      # contain (entre entière) | cover (remplit, découpé)
    "text": "",
}

ALIGNS = ("left", "center", "right", "justify")
VALIGNS = ("top", "middle", "bottom")
CASES = ("none", "upper", "lower", "title")
SIDES = ("front", "back", "both")
KINDS = ("text", "image")
FITS = ("contain", "cover")

SIZE_PT_MIN, SIZE_PT_MAX = 2.0, 400.0
READ_PT_MIN, READ_PT_MAX = 0.0, 400.0

# LES FOURCHETTES DU MÉTIER, telles que la spec les fixe pour une carte tenue
# en main : un titre se compose de 12 à 20 pt, un encadré de règles de 6 à 9,
# un crédit de 4 à 5. Ce sont les BAS de ces fourchettes qui servent de
# plancher de lisibilité aux gabarits ; un chiffre de statistique n'a pas de
# fourchette écrite, mais sous 8 pt il ne se lit plus à bout de bras, et c'est
# dit ici plutôt que supposé ailleurs.
READ_FLOOR_PT: dict[str, float] = {
    "title": 12.0, "name": 12.0,
    "typeline": 6.0, "rules": 6.0, "flavor": 6.0, "arcnum": 6.0,
    "cost": 8.0, "atk": 8.0, "def": 8.0,
    "num": 4.0, "artist": 4.0,
}
TRACK_MIN, TRACK_MAX = -30.0, 100.0
LEADING_MIN, LEADING_MAX = 0.6, 3.0
# Le plancher de `just_max` est 100 % : un blanc RÉTRÉCI collerait les mots
# entre eux, et aucun plafond ne doit pouvoir le demander.
JUST_MAX_MIN, JUST_MAX_MAX = 100.0, 400.0
LAST_PCT_MIN, LAST_PCT_MAX = 0.0, 80.0
ARC_MIN, ARC_MAX = -100.0, 100.0
# LA PLAQUE DE FOND. Le rayon est en millimètres et son plafond est celui du
# métier : au-delà de 30 mm, sur une carte de 63 x 88, un « coin arrondi » est
# un disque — la boîte du slot borne de toute façon le rayon à la moitié de son
# petit côté, AU DESSIN (le painter reçoit les slots du document tels quels).
PLATE_ALPHA_MIN, PLATE_ALPHA_MAX = 0.0, 1.0
PLATE_RADIUS_MIN, PLATE_RADIUS_MAX = 0.0, 30.0
SLOT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
SLOTS_MAX = 40

# ── LES IMAGES DE CALQUE ────────────────────────────────────────────────────
# `SLOT_SRC_RE` est le motif du VOCABULAIRE (ce qu'un document a le droit de
# nommer) ; `IMG_NAME_RE` celui de la ROUTE (ce qu'un GET a le droit de
# demander). Les deux sont exacts, et pour la même raison : ces noms ne
# viennent pas de l'utilisateur, ils sont FABRIQUÉS ICI par un compteur. Un
# motif permissif aurait ouvert le dossier du deck (`job.json`, `paper.png`,
# tout ce qu'une autre pièce y écrira demain) à la première lettre près.
SLOT_SRC_RE = re.compile(r"^(|img:img_\d+\.png)$")
IMG_NAME_RE = re.compile(r"^img_\d+\.png$")
# Le plafond de NOMBRE. Il compte ce qui EXISTE sur le disque, pas ce qui a été
# importé dans la session : un deck dupliqué arrive avec ses images.
SLOT_IMAGES_MAX = 12
# Le plafond de POIDS du corps, celui de la matière de P6 (64 Mo) — pesé AVANT
# tout décodage, seul ordre qui protège la mémoire.
IMG_MAX_BYTES = 64 * 1024 * 1024
# Le côté long au-delà duquel une image importée est ré-échelonnée. MÊME
# CHIFFRE que l'illustration de P1 (`cards/face.py:MAX_IMPORT_PX`), RECOPIÉ et
# non importé : la règle 8 interdit à une pièce d'importer le module d'une
# voisine. Le test de parité épingle les quatre endroits qui le portent (les
# deux backends et les deux écrans).
MAX_IMPORT_PX = 4096

# L'encadré de règles de démonstration fait plus de 400 caractères : c'est le
# seuil chiffré de la pièce (« l'encadré accepte >= 400 caractères et reste
# dans la zone sûre »). Il est ici, dans le gabarit, pour que l'écran arrive
# déjà chargé du cas difficile au lieu d'attendre qu'on le tape.
_RULES_TEXT = (
    "Vol, célérité. À l'entrée en jeu, révélez les trois cartes du dessus de "
    "votre pioche : gardez-en une en main, renvoyez les autres au fond du "
    "paquet. Tant que cette créature est en jeu, vos sorts d'eau coûtent 1 de "
    "moins et vos créatures marines gagnent +0/+1. Sacrifice : défaussez une "
    "carte pour donner +2/+0 à une créature alliée jusqu'à la fin du tour. À "
    "sa mort, chaque adversaire défausse une carte au hasard et vous piochez."
)

PRESETS: dict = {
    "champion": {
        "label": "Champion",
        "hint": "Titre long, coût, statistiques, encadré de règles, ambiance, crédits.",
        "slots": [
            {"id": "cost", "label": "Coût", "rel": [0.0, 0.0, 0.17, 0.115],
             "font": "Anton", "size_pt": 22.0, "min_pt": 9.0, "read_pt": 8.0, "color": "#f6e7c2",
             "align": "center", "valign": "middle", "outline": 1.4,
             "outline_color": "#1b1206", "wrap": False,
             "text": "5"},
            {"id": "title", "label": "Titre", "rel": [0.19, 0.0, 0.81, 0.115],
             "font": "Cinzel", "size_pt": 14.0, "min_pt": 6.5, "read_pt": 12.0, "color": "#f6e7c2",
             "align": "center", "valign": "middle", "track": 2.0, "leading": 1.02,
             "caps": "upper", "bold": True, "outline": 0.8,
             "outline_color": "#1b1206", "shadow": 1.2, "shadow_dy": 0.6,
             "text": "Veilleur, Grand Oracle des Marches Profondes"},
            {"id": "typeline", "label": "Ligne de type", "rel": [0.0, 0.552, 1.0, 0.05],
             "font": "Staatliches", "size_pt": 8.5, "min_pt": 5.0, "read_pt": 6.0, "color": "#e8d8b6",
             "align": "center", "valign": "middle", "track": 6.0, "caps": "upper",
             "wrap": False, "text": "Créature légendaire — Sentinelle"},
            {"id": "rules", "label": "Encadré de règles", "rel": [0.02, 0.615, 0.96, 0.2],
             "font": "IBMPlexSans", "size_pt": 8.0, "min_pt": 4.5, "read_pt": 6.0, "color": "#efe7d6",
             "align": "justify", "valign": "top", "leading": 1.22, "hyphen": True,
             "text": _RULES_TEXT},
            {"id": "flavor", "label": "Texte d'ambiance", "rel": [0.04, 0.826, 0.92, 0.055],
             "font": "IBMPlexSans", "size_pt": 7.0, "min_pt": 4.5, "read_pt": 6.0, "color": "#c9bda6",
             "align": "center", "valign": "middle", "italic": True,
             "text": "« Ce qui monte finit toujours par redescendre, dit-on ici. »"},
            {"id": "atk", "label": "Attaque", "rel": [0.0, 0.885, 0.17, 0.09],
             "font": "Anton", "size_pt": 19.0, "min_pt": 8.0, "read_pt": 8.0, "color": "#f6e7c2",
             "align": "center", "valign": "middle", "outline": 1.4,
             "outline_color": "#1b1206", "wrap": False, "text": "4"},
            {"id": "def", "label": "Vie", "rel": [0.83, 0.885, 0.17, 0.09],
             "font": "Anton", "size_pt": 19.0, "min_pt": 8.0, "read_pt": 8.0, "color": "#f6e7c2",
             "align": "center", "valign": "middle", "outline": 1.4,
             "outline_color": "#1b1206", "wrap": False, "text": "5"},
            # Les crédits vont TOUT EN BAS de la zone sûre : c'est la
            # convention du métier, et cela laisse la bande centrale aux
            # ornements que P2 pose en dessous du texte. Les deux boîtes sont
            # le MIROIR l'une de l'autre autour de l'axe de la zone sûre
            # (0,20-0,45 et 0,55-0,80) : le numéro fer à gauche et le crédit
            # fer à droite se tournent alors le dos vers l'extérieur, ce qui
            # est la disposition du métier — et l'asymétrie apparente des deux
            # alignements devient une symétrie mesurable.
            {"id": "num", "label": "Numéro", "rel": [0.2, 0.952, 0.25, 0.045],
             "font": "JetBrainsMono", "size_pt": 5.0, "min_pt": 3.5, "read_pt": 4.0, "color": "#c5bba4",
             "align": "left", "valign": "middle", "wrap": False, "text": "017 / 060"},
            {"id": "artist", "label": "Artiste", "rel": [0.55, 0.952, 0.25, 0.045],
             "font": "IBMPlexSans", "size_pt": 5.0, "min_pt": 3.5, "read_pt": 4.0, "color": "#c5bba4",
             "align": "right", "valign": "middle", "wrap": False,
             "text": "ill. A. Nonyme"},
        ],
    },
    "sort": {
        "label": "Sort",
        "hint": "Sans statistiques : titre, coût, grand encadré de règles, ambiance.",
        "slots": [
            {"id": "cost", "label": "Coût", "rel": [0.0, 0.0, 0.16, 0.11],
             "font": "Anton", "size_pt": 21.0, "min_pt": 9.0, "read_pt": 8.0, "color": "#dce9f6",
             "align": "center", "valign": "middle", "outline": 1.4,
             "outline_color": "#08131f", "wrap": False, "text": "3"},
            # « Marée d'encre » sur PolandKaito.otf : ce fichier n'a pas de
            # « é » (114 points de code, lus dans sa cmap). Le navigateur
            # l'empruntait à une autre police, en silence — le gabarit livré
            # démontrait la faute que ce module dénonce. Cinzel porte les 41
            # signes du répertoire français ; PolandKaito reste au menu, où
            # elle est désormais marquée pour ce qu'elle est.
            {"id": "title", "label": "Titre", "rel": [0.18, 0.0, 0.82, 0.11],
             "font": "Cinzel", "size_pt": 15.0, "min_pt": 6.5, "read_pt": 12.0, "color": "#dce9f6",
             "align": "center", "valign": "middle", "track": 1.0,
             "outline": 0.8, "outline_color": "#08131f",
             "text": "Marée d'encre"},
            {"id": "typeline", "label": "Ligne de type", "rel": [0.0, 0.55, 1.0, 0.05],
             "font": "Staatliches", "size_pt": 8.5, "min_pt": 5.0, "read_pt": 6.0, "color": "#c7d9ea",
             "align": "center", "valign": "middle", "track": 6.0, "caps": "upper",
             "wrap": False, "text": "Sort instantané"},
            {"id": "rules", "label": "Encadré de règles", "rel": [0.02, 0.615, 0.96, 0.24],
             "font": "IBMPlexSans", "size_pt": 8.5, "min_pt": 4.5, "read_pt": 6.0, "color": "#e6eef7",
             "align": "justify", "valign": "top", "leading": 1.24, "hyphen": True,
             "text": _RULES_TEXT},
            {"id": "flavor", "label": "Texte d'ambiance", "rel": [0.04, 0.87, 0.92, 0.06],
             "font": "IBMPlexSans", "size_pt": 7.0, "min_pt": 4.5, "read_pt": 6.0, "color": "#9fb3c6",
             "align": "center", "valign": "middle", "italic": True,
             "text": "« L'encre monte, la mémoire descend. »"},
            {"id": "artist", "label": "Artiste", "rel": [0.35, 0.945, 0.65, 0.045],
             "font": "IBMPlexSans", "size_pt": 5.0, "min_pt": 3.5, "read_pt": 4.0, "color": "#8496a8",
             "align": "right", "valign": "middle", "wrap": False,
             "text": "ill. A. Nonyme"},
        ],
    },
    "arcane": {
        "label": "Arcane (texte sur arc)",
        "hint": "Titre courbé en haut, chiffre romain, cartouche de nom en bas.",
        "slots": [
            {"id": "arcnum", "label": "Numéro d'arcane", "rel": [0.3, 0.0, 0.4, 0.07],
             "font": "Cinzel", "size_pt": 11.0, "min_pt": 6.0, "read_pt": 6.0, "color": "#e9d7a8",
             "align": "center", "valign": "middle", "track": 12.0, "caps": "upper",
             "wrap": False, "text": "XVII"},
            {"id": "title", "label": "Titre sur arc", "rel": [0.05, 0.075, 0.9, 0.12],
             "font": "Cinzel", "size_pt": 13.0, "min_pt": 6.0, "read_pt": 12.0, "color": "#e9d7a8",
             "align": "center", "valign": "middle", "track": 4.0, "caps": "upper",
             "arc": 38.0, "bold": True, "wrap": False,
             "text": "La Roue des Marées"},
            {"id": "name", "label": "Cartouche", "rel": [0.05, 0.86, 0.9, 0.075],
             "font": "Cinzel", "size_pt": 12.0, "min_pt": 6.0, "read_pt": 12.0, "color": "#e9d7a8",
             "align": "center", "valign": "middle", "track": 8.0, "caps": "upper",
             "arc": -22.0, "wrap": False, "text": "La Gardienne"},
            {"id": "artist", "label": "Artiste", "rel": [0.2, 0.95, 0.6, 0.04],
             "font": "IBMPlexSans", "size_pt": 5.0, "min_pt": 3.5, "read_pt": 4.0, "color": "#d3c39c",
             "align": "center", "valign": "middle", "wrap": False,
             "text": "ill. A. Nonyme"},
        ],
    },
    "minimal": {
        "label": "Minimal",
        "hint": "Deux slots : un titre, un encadré. Le point de départ le plus sobre.",
        "slots": [
            {"id": "title", "label": "Titre", "rel": [0.0, 0.0, 1.0, 0.1],
             "font": "SpaceGrotesk", "size_pt": 14.0, "min_pt": 7.0, "read_pt": 12.0,
             "color": "#f2efe9", "align": "left", "valign": "top", "bold": True,
             "text": "Veilleur, Grand Oracle des Marches Profondes"},
            {"id": "rules", "label": "Encadré de règles", "rel": [0.0, 0.62, 1.0, 0.24],
             "font": "IBMPlexSans", "size_pt": 8.5, "min_pt": 4.5, "read_pt": 6.0, "color": "#d8d2c8",
             "align": "justify", "valign": "top", "leading": 1.25, "hyphen": True,
             "text": _RULES_TEXT},
        ],
    },
}

DEFAULT_PRESET = "champion"


# ════════════════════════════════════════════════════════════════════════════
# 3. NORMALISATION — un corps mal formé ne fait JAMAIS 500 (spec §2.5)
# ════════════════════════════════════════════════════════════════════════════

def _num(value, default: float, lo: float, hi: float) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(f):
        return float(default)
    return min(hi, max(lo, f))


def _choice(value, allowed: tuple[str, ...], default: str) -> str:
    s = str(value).strip().lower() if value is not None else ""
    return s if s in allowed else default


def _color(value, default: str | None) -> str | None:
    """Une couleur hexadécimale, ou le défaut. Le défaut peut être `None` :
    « pas de couleur » est un état légitime pour une plaque de fond, alors
    qu'il ne l'est pas pour l'encre d'un texte."""
    s = str(value).strip() if value is not None else ""
    if re.fullmatch(r"#[0-9a-fA-F]{3}", s) or re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s.lower()
    if re.fullmatch(r"#[0-9a-fA-F]{8}", s):
        return s.lower()
    return default


def norm_slot(raw, index: int = 0) -> dict:
    """Un slot venant du client, ramené dans ses bornes. Jamais d'exception."""
    r = raw if isinstance(raw, dict) else {}
    out = copy.deepcopy(SLOT_DEFAULTS)
    sid = str(r.get("id") or "").strip().lower()
    out["id"] = sid if SLOT_ID_RE.match(sid) else f"slot{index + 1}"
    out["label"] = (str(r.get("label") or out["id"]).strip() or out["id"])[:40]
    box = r.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4:
        out["box"] = [_num(box[0], 0.0, -500.0, 500.0),
                      _num(box[1], 0.0, -500.0, 500.0),
                      _num(box[2], 10.0, 0.0, 500.0),
                      _num(box[3], 5.0, 0.0, 500.0)]
    out["font"] = (str(r.get("font") or FONT_FALLBACK).strip() or FONT_FALLBACK)[:64]
    out["size_pt"] = _num(r.get("size_pt"), SLOT_DEFAULTS["size_pt"], SIZE_PT_MIN, SIZE_PT_MAX)
    out["min_pt"] = _num(r.get("min_pt"), SLOT_DEFAULTS["min_pt"], SIZE_PT_MIN, SIZE_PT_MAX)
    out["min_pt"] = min(out["min_pt"], out["size_pt"])
    # `read_pt` n'est PAS ramené sous `size_pt` : un plancher de lisibilité
    # au-dessus du corps demandé est une information juste (« ce bloc est déjà
    # trop petit »), pas une erreur de saisie à corriger en silence.
    out["read_pt"] = _num(r.get("read_pt"), 0.0, READ_PT_MIN, READ_PT_MAX)
    out["color"] = _color(r.get("color"), SLOT_DEFAULTS["color"])
    out["align"] = _choice(r.get("align"), ALIGNS, SLOT_DEFAULTS["align"])
    out["valign"] = _choice(r.get("valign"), VALIGNS, SLOT_DEFAULTS["valign"])
    out["track"] = _num(r.get("track"), 0.0, TRACK_MIN, TRACK_MAX)
    out["leading"] = _num(r.get("leading"), SLOT_DEFAULTS["leading"], LEADING_MIN, LEADING_MAX)
    out["just_max"] = _num(r.get("just_max"), SLOT_DEFAULTS["just_max"],
                           JUST_MAX_MIN, JUST_MAX_MAX)
    out["last_pct"] = _num(r.get("last_pct"), SLOT_DEFAULTS["last_pct"],
                           LAST_PCT_MIN, LAST_PCT_MAX)
    out["hyphen"] = bool(r.get("hyphen", False))
    out["caps"] = _choice(r.get("caps"), CASES, SLOT_DEFAULTS["caps"])
    out["bold"] = bool(r.get("bold", False))
    out["italic"] = bool(r.get("italic", False))
    out["outline"] = _num(r.get("outline"), 0.0, 0.0, 20.0)
    out["outline_color"] = _color(r.get("outline_color"), SLOT_DEFAULTS["outline_color"])
    out["shadow"] = _num(r.get("shadow"), 0.0, 0.0, 40.0)
    out["shadow_color"] = _color(r.get("shadow_color"), SLOT_DEFAULTS["shadow_color"])
    out["shadow_dx"] = _num(r.get("shadow_dx"), 0.0, -40.0, 40.0)
    out["shadow_dy"] = _num(r.get("shadow_dy"), 0.0, -40.0, 40.0)
    # LA PLAQUE. Une couleur illisible ne vaut pas « noir » ici : elle vaut
    # PAS DE PLAQUE. Peindre du noir sur un cartouche parce qu'un import a
    # écrit « bleu » aurait été un défaut visible et muet.
    out["plate_color"] = _color(r.get("plate_color"), None)
    out["plate_alpha"] = _num(r.get("plate_alpha"), SLOT_DEFAULTS["plate_alpha"],
                              PLATE_ALPHA_MIN, PLATE_ALPHA_MAX)
    out["plate_radius"] = _num(r.get("plate_radius"), 0.0,
                               PLATE_RADIUS_MIN, PLATE_RADIUS_MAX)
    out["rotate"] = _num(r.get("rotate"), 0.0, -180.0, 180.0)
    out["arc"] = _num(r.get("arc"), 0.0, ARC_MIN, ARC_MAX)
    out["autofit"] = bool(r.get("autofit", True))
    out["wrap"] = bool(r.get("wrap", True))
    out["opacity"] = _num(r.get("opacity"), 100.0, 0.0, 100.0)
    out["side"] = _choice(r.get("side"), SIDES, SLOT_DEFAULTS["side"])
    out["on"] = bool(r.get("on", True))
    # Faux par défaut, donc faux pour tout document écrit avant la 3b : un bloc
    # ne devient protégé que si quelqu'un l'a demandé.
    out["lock"] = bool(r.get("lock", False))
    # LA NATURE DU BLOC. Une valeur inconnue retombe sur « text » : un `kind`
    # inventé enverrait le painter dans une branche qui n'existe pas, et un
    # bloc de texte inerte est une dégradation lisible, pas une panne.
    out["kind"] = _choice(r.get("kind"), KINDS, SLOT_DEFAULTS["kind"])
    # LA SOURCE. Le motif est exact (voir SLOT_SRC_RE) et appliqué SANS
    # rognage : ce nom n'est jamais tapé par un humain, il est fabriqué par la
    # route d'import. « img:img_1.png » suivi d'une espace n'est donc pas une
    # faute de frappe à réparer, c'est une chaîne qui ne vient pas de nous.
    # `fullmatch` et non `match` : `$` accepte un saut de ligne final, et un
    # nom de fichier n'a pas de saut de ligne.
    src = r.get("src") if isinstance(r.get("src"), str) else ""
    out["src"] = src if SLOT_SRC_RE.fullmatch(src) else ""
    out["fit"] = _choice(r.get("fit"), FITS, SLOT_DEFAULTS["fit"])
    out["text"] = str(r.get("text") or "")[:4000]
    return out


def norm_slots(raw) -> list[dict]:
    rows = raw if isinstance(raw, list) else []
    out, seen = [], set()
    for i, r in enumerate(rows[:SLOTS_MAX]):
        s = norm_slot(r, i)
        sid, n = s["id"], 2
        while sid in seen:                     # deux slots de même id : P4 ne
            sid = f"{s['id']}{n}"              # saurait plus lequel remplir
            n += 1
        s["id"] = sid
        seen.add(sid)
        out.append(s)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 4. GABARIT -> MILLIMÈTRES, puis MILLIMÈTRES -> PIXELS DE TOILE
# ════════════════════════════════════════════════════════════════════════════

def safe_rect_mm(g) -> tuple[float, float, float, float]:
    """La zone sûre en mm depuis le coin ROGNE, TELLE QU'ELLE EXISTE EN PIXELS.

    Ce n'est pas `(safe_mm, trim_mm - 2*safe_mm)` : la zone sûre du fichier
    livré est `safe_px` (une longueur arrondie une seule fois) CENTRÉE dans la
    rogne, et elle ne retombe pas exactement sur les millimètres demandés —
    sur `poker_eu`, 3 mm de consigne donnent 3,0056 mm en largeur et 2,9633 mm
    en hauteur. Les pixels font le fichier ; les millimètres n'en sont que la
    lecture. Un gabarit calé sur les millimètres tombait à 0,07 px HORS de la
    zone sûre en pixels et le contrôle avant vol de P7 l'aurait signalé."""
    k = MM_PER_INCH / g.dpi
    return ((g.safe_off_px[0] - g.bleed_off_px[0]) * k,
            (g.safe_off_px[1] - g.bleed_off_px[1]) * k,
            g.safe_px[0] * k, g.safe_px[1] * k)


def preset_slots(preset_id: str, g) -> list[dict]:
    """Les slots d'un gabarit, convertis en mm pour CE format.

    `rel` est en fractions de la zone sûre : le résultat est dans la zone sûre
    des douze formats par construction, sans table par format."""
    p = PRESETS.get(preset_id)
    if p is None:
        raise HTTPException(400, "Gabarit inconnu : " + ", ".join(sorted(PRESETS)))
    sx, sy, sw, sh = safe_rect_mm(g)
    out = []
    for spec in p["slots"]:
        s = copy.deepcopy(SLOT_DEFAULTS)
        for k, v in spec.items():
            if k == "rel":
                continue
            s[k] = copy.deepcopy(v)
        rx, ry, rw, rh = spec["rel"]
        # 6 décimales : 1e-6 mm vaut 1,2e-5 px à 300 DPI. L'aller-retour
        # px -> mm -> px est donc exact à un cent-millième de pixel près, ce
        # que `_outside` absorbe explicitement (EPS_PX).
        s["box"] = [rnd(sx + rx * sw, 6), rnd(sy + ry * sh, 6),
                    rnd(rw * sw, 6), rnd(rh * sh, 6)]
        out.append(norm_slot(s))
    return out


def mm2px(v: float, dpi: int) -> float:
    """Millimètres -> pixels de toile, EXACT (non arrondi) : une boîte de
    texte tombe volontiers sur un demi-pixel, comme le trait de coupe."""
    return v / MM_PER_INCH * dpi


def pt2px(pt: float, dpi: int) -> float:
    """Points typographiques -> pixels. 1 pt = 1/72 in, par définition."""
    return pt / 72.0 * dpi


def box_px(box, g) -> list[float]:
    """Boîte en mm depuis le coin ROGNE -> pixels depuis le coin de TOILE."""
    return [
        g.bleed_off_px[0] + mm2px(box[0], g.dpi),
        g.bleed_off_px[1] + mm2px(box[1], g.dpi),
        mm2px(box[2], g.dpi),
        mm2px(box[3], g.dpi),
    ]


# Seuil de bruit du confinement : un dix-millième de pixel. Ce n'est PAS une
# marge de tolérance — un vrai débordement se compte en dixièmes de pixel au
# minimum. C'est le résidu de l'aller-retour millimètres <-> pixels : le
# document stocke des millimètres (c'est l'unité du métier et celle du
# contrat `doc.type.slots`), la toile compte des pixels, et 1e-6 mm de
# quantification vaut 1,2e-5 px. Sans ce seuil, une boîte calée EXACTEMENT
# sur le bord de la zone sûre serait signalée « hors zone » une fois sur deux
# selon le sens de l'arrondi.
EPS_PX = 1e-4


def _outside(rect, safe) -> dict:
    """De combien `rect` sort de `safe`, côté par côté, en pixels."""
    def d(v):
        return rnd(v, 4) if v > EPS_PX else 0.0
    return {
        "left": d(safe[0] - rect[0]),
        "top": d(safe[1] - rect[1]),
        "right": d((rect[0] + rect[2]) - (safe[0] + safe[2])),
        "bottom": d((rect[1] + rect[3]) - (safe[1] + safe[3])),
    }


def font_missing_map() -> dict[str, set[str] | None]:
    """id de police -> caractères français absents du fichier (`None` = table
    illisible). Sert au recomptage hors écran des glyphes manquants."""
    out: dict[str, set[str] | None] = {}
    for f in scan_fonts():
        miss = f.get("fr_missing")
        out[f["id"]] = None if miss is None else set(miss)
    return out


def apply_case(text: str, caps: str) -> str:
    """La casse, appliquée comme le fait l'écran — ACCENTS COMPRIS.

    `"Créature".upper()` rend `"CRÉATURE"` en Python comme en JavaScript : la
    mise en capitales ne mange pas l'accent. Le concurrent, lui, capitalise
    dans la donnée et sort `CREATURE`. La fonction est ici pour que ce soit
    une ligne de test et non une conviction.

    L'APOSTROPHE N'OUVRE PAS UN MOT. `"marée d'encre"` en capitales initiales
    sortait `"Marée D'Encre"` : l'apostrophe était traitée comme une espace,
    donc `encre` passait pour un mot neuf. C'est faux dans toutes les langues
    qui élident (`d'`, `l'`, `qu'`), et c'était imprimé sur la carte. Elle
    reste donc DANS le mot ; les vraies coupures sont les blancs, les
    guillemets droits et les parenthèses."""
    if caps == "upper":
        return str(text).upper()
    if caps == "lower":
        return str(text).lower()
    if caps == "title":
        return re.sub(r"[^\s\"(\[]+",
                      lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(),
                      str(text))
    return str(text)


def layout(g, slots: list[dict], inks: dict | None = None,
           posed: dict | None = None, texts: dict | None = None) -> dict:
    """Le jugement : boîtes en pixels de toile et confinement dans la zone
    sûre. `inks[slot_id] = [x, y, w, h]` = l'encombrement RÉELLEMENT MESURÉ du
    texte par le navigateur (en pixels de toile) — c'est lui qui décide, pas
    la boîte : un texte qui déborde de sa boîte sort de la zone sûre même si
    la boîte, elle, y était.

    `posed[slot_id]` = le corps RÉELLEMENT COMPOSÉ, en points, après
    l'ajustement automatique. Lui non plus ne se devine pas ici : c'est le
    navigateur qui a les polices et qui a rétréci. Le backend s'en sert pour
    appliquer LA MÊME règle que l'écran au plancher de lisibilité `read_pt` —
    deux verdicts sur la même grandeur, et un écart entre eux serait un bug
    visible plutôt qu'un silence."""
    safe = [g.safe_off_px[0], g.safe_off_px[1], float(g.safe_px[0]), float(g.safe_px[1])]
    trim = [g.bleed_off_px[0], g.bleed_off_px[1], float(g.trim_px[0]), float(g.trim_px[1])]
    inks = inks if isinstance(inks, dict) else {}
    posed = posed if isinstance(posed, dict) else {}
    texts = texts if isinstance(texts, dict) else {}
    # le catalogue n'est lu que si on nous donne des textes à vérifier.
    fmiss = font_missing_map() if texts else {}
    rows, out_ids, under_ids, tofu_ids = [], [], [], []
    for s in slots:
        r = box_px(s["box"], g)
        o = _outside(r, safe)
        inside = not any(o.values())
        # ── UN CALQUE D'IMAGE N'EST PAS JUGÉ COMME UN TEXTE ─────────────────
        # Il n'a pas de glyphe : pas de corps composé, pas de plancher de
        # lisibilité, pas de signe hors police. Les colonnes typographiques
        # valent donc `None` — et non 0, qui se lirait comme une MESURE et
        # aurait rempli le relevé de « blocs trop petits » imaginaires.
        #
        # CE QUI RESTE JUGÉ : la géométrie. Une image qui sort du cadre de
        # composition est un défaut de fabrication exactement comme des glyphes
        # qui en sortent — la coupe emporte ses pixels de la même façon. C'est
        # la LISIBILITÉ qui est sans objet ici, pas le confinement.
        img = s["kind"] == "image"
        row = {
            "id": s["id"],
            "label": s["label"],
            "on": s["on"],
            "side": s["side"],
            "kind": s["kind"],
            "src": s["src"],
            "fit": s["fit"],
            "box_mm": [rnd(v, 3) for v in s["box"]],
            "box_px": [rnd(v, 2) for v in r],
            "size_px": None if img else rnd(pt2px(s["size_pt"], g.dpi), 2),
            "min_px": None if img else rnd(pt2px(s["min_pt"], g.dpi), 2),
            "read_pt": None if img else rnd(s["read_pt"], 2),
            "read_px": None if img else rnd(pt2px(s["read_pt"], g.dpi), 2),
            "posed_pt": None,
            "under_read": None,
            "inside_safe": inside,
            "out_px": o,
            "ink_px": None,
            "ink_inside_safe": None,
            "ink_out_px": None,
            # LES CARACTÈRES QUE CETTE POLICE NE SAIT PAS ÉCRIRE, recomptés
            # ici : le navigateur les remplace en silence par ceux d'une autre
            # fonte, et le mot part quand même à l'impression.
            "missing_glyphs": None,
        }
        if texts and not img:
            miss = fmiss.get(s["font"])
            raw = texts.get(s["id"])
            if raw is None:
                raw = s.get("text", "")
            if miss:
                row["missing_glyphs"] = missing_chars(apply_case(raw, s["caps"]), miss)
                if s["on"] and row["missing_glyphs"]:
                    tofu_ids.append(s["id"])
            elif miss is not None:
                row["missing_glyphs"] = []
        ink = inks.get(s["id"])
        if isinstance(ink, (list, tuple)) and len(ink) == 4:
            try:
                rect = [float(v) for v in ink]
            except (TypeError, ValueError):
                rect = None
            if rect is not None and all(math.isfinite(v) for v in rect):
                io = _outside(rect, safe)
                row["ink_px"] = [rnd(v, 2) for v in rect]
                row["ink_out_px"] = io
                row["ink_inside_safe"] = not any(io.values())
        p = None if img else posed.get(s["id"])
        try:
            pf = float(p)
        except (TypeError, ValueError):
            pf = None
        if pf is not None and math.isfinite(pf) and pf > 0:
            row["posed_pt"] = rnd(pf, 2)
            # LA MÊME COMPARAISON QUE L'ÉCRAN, au dixième de point — celui qui
            # est affiché. Le corps composé sort d'une recherche dichotomique :
            # elle s'arrête à 11,99 pt quand on visait 12, et un plancher jugé
            # au centième faisait écrire « 12 < 12 pt » au badge. Un centième
            # de point n'est pas un défaut de lisibilité ; un badge qui se
            # contredit lui-même en est un. `floor(x*10 + 0.5)` et non `round`
            # : la fonction native de Python arrondit à l'entier PAIR, celle de
            # JavaScript arrondit vers le haut — deux verdicts qui divergent
            # une fois sur vingt sur un demi-dixième.
            row["under_read"] = bool(
                s["read_pt"] > 0
                and math.floor(pf * 10 + 0.5) < math.floor(s["read_pt"] * 10 + 0.5))
            if s["on"] and row["under_read"]:
                under_ids.append(s["id"])
        bad = (row["ink_inside_safe"] is False) or \
              (row["ink_inside_safe"] is None and not inside)
        if s["on"] and bad:
            out_ids.append(s["id"])
        rows.append(row)
    return {
        "geom": g.to_dict(),
        "canvas_px": list(g.canvas_px),
        "trim_rect_px": [rnd(v, 2) for v in trim],
        "safe_rect_px": [rnd(v, 2) for v in safe],
        "safe_rect_mm": [rnd(v, 3) for v in safe_rect_mm(g)],
        "slots": rows,
        "summary": {
            "n": len(rows),
            "visible": sum(1 for s in slots if s["on"]),
            "outside_safe": out_ids,
            # SÉPARÉ de `ok` À DESSEIN. Sortir de la zone sûre est un défaut de
            # fabrication : la coupe emporte l'encre. Composer sous le plancher
            # de lisibilité est un défaut de LECTURE : le fichier est correct,
            # la carte ne se lira pas. Les mélanger dans un seul voyant aurait
            # rendu l'un des deux invisible.
            "under_read": under_ids,
            # TROISIÈME défaut, séparé lui aussi : le fichier est juste, le
            # bloc est lisible, et un caractère n'est pas de la bonne police.
            "missing_glyphs": tofu_ids,
            "ok": not out_ids,
        },
    }


# ────────────────────────────────────────────────────────────────────────────
# LA ZONE SÛRE DOIT SURVIVRE AU CHANGEMENT DE DÉFINITION
#
# L'écran prouve, sur les octets, qu'aucun bloc ne bouge entre 300 et 600 DPI.
# Il reste une question qu'il ne peut pas se poser tout seul, parce qu'elle
# porte sur la RÈGLE et non sur le tracé : la zone sûre elle-même est-elle la
# même longueur aux deux définitions ? Elle sort d'un arrondi au pixel
# (`safe_px = R(mm / 25,4 * dpi)`), donc rien ne le garantit — et si elle
# bougeait, un bloc jugé DEDANS à 300 DPI pourrait sortir à 600 sans que ni la
# boîte ni le texte n'aient changé. Ce serait le pire des verdicts : juste des
# deux côtés, et contradictoire.
#
# On mesure donc la dérive, format par format et définition par définition, au
# lieu de la supposer nulle. Le chiffre remonte dans la réponse de `/layout`,
# à côté du verdict de zone sûre qu'il qualifie.
# ────────────────────────────────────────────────────────────────────────────
DEFINITIONS: tuple[int, ...] = (150, 300, 600)


def definition_drift(fmt: str, bleed_mm: float, safe_mm: float,
                     dpis: tuple[int, ...] = DEFINITIONS) -> dict:
    """La zone sûre, en millimètres, à chaque définition — et l'écart maximal.

    Le résultat est une MESURE, pas une promesse : chaque ligne porte les
    pixels d'où elle sort, pour qu'on refasse la division à la main."""
    rows = []
    for d in dpis:
        g = geom_of(fmt, d, bleed_mm, safe_mm, 3.0)
        r = safe_rect_mm(g)
        rows.append({
            "dpi": d,
            "canvas_px": list(g.canvas_px),
            "safe_px": list(g.safe_px),
            "safe_off_px": [rnd(v, 2) for v in g.safe_off_px],
            "safe_rect_mm": [rnd(v, 4) for v in r],
        })
    drift = 0.0
    for k in range(4):
        vals = [row["safe_rect_mm"][k] for row in rows]
        drift = max(drift, max(vals) - min(vals))
    return {
        "fmt": fmt,
        "dpis": list(dpis),
        "rows": rows,
        # en millimètres, et aussi en pixels de la définition la PLUS GROSSIÈRE
        # — l'unité dans laquelle un arrondi au pixel se lit pour ce qu'il est.
        "drift_mm": rnd(drift, 4),
        "drift_px_min_dpi": rnd(drift / (MM_PER_INCH / min(dpis)), 3),
        "quantum_mm": rnd(MM_PER_INCH / min(dpis), 4),
    }


def _geom_from(body: dict):
    """La géométrie demandée par le client, avec les mêmes bornes que le
    CORE. Un format inconnu = 400 en énumérant la liste blanche."""
    fmt = str(body.get("fmt") or DEFAULT_FMT).strip().lower()
    if fmt not in FORMATS:
        raise HTTPException(400, "Format inconnu : " + ", ".join(sorted(FORMATS)))
    dpi = body.get("dpi", DEFAULT_DPI)
    try:
        dpi = int(float(dpi))
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, "Le DPI doit être un nombre")
    try:
        return geom_of(fmt, dpi, body.get("bleed_mm"), body.get("safe_mm"),
                       body.get("corner_mm", 3.0))
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


def _check_did(did: str) -> None:
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")


# ════════════════════════════════════════════════════════════════════════════
# 4bis. LES IMAGES DE CALQUE, SUR LE DISQUE DU DECK
# ════════════════════════════════════════════════════════════════════════════
# Patron `texture.py:post_paper` — le seul précédent du lab qui range un import
# d'utilisateur AVEC LE DECK plutôt que dans le navigateur. Les deux
# différences, et elles sont voulues :
#
#   · P6 garde UN fichier (`paper.png`) qu'il écrase à chaque import ; ici il y
#     en a jusqu'à douze, et un COMPTEUR leur donne des noms. Écraser aurait
#     changé l'image d'un calque en en important une autre.
#   · le compteur vaut MAX + 1, jamais « le premier trou libre ». Un slot
#     supprimé se rattrape par Ctrl+Z : son image doit rester joignable, et un
#     numéro recyclé aurait fait revenir le bloc annulé avec une AUTRE image.
#
# PAS DE ROUTE DE SUPPRESSION, et c'est la même raison : tant que l'annulation
# peut ramener le bloc, effacer ses octets serait une perte irréversible
# déclenchée par un geste réversible. Le ramassage des images qu'aucun slot ne
# nomme plus est un travail de la 3c (avec le reste du ménage de fin de phase).

def type_dir(did: str, create: bool = False) -> pathlib.Path:
    """`decks/<did>/type/`. `deck_dir` porte déjà le double garde-fou (motif
    PUIS confinement) : on ne le refait pas, on s'appuie dessus."""
    d = deck_dir(did, create=create) / "type"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _deck_or_404(did: str, create: bool = False) -> pathlib.Path:
    """Le dossier de la pièce, pour un deck QUI EXISTE DÉJÀ.

    L'existence est vérifiée SANS `create` — sinon le contrôle se répondrait à
    lui-même : `deck_dir(did, create=True)` fabrique le dossier, et le `is_dir`
    qui suit ne peut plus qu'être vrai. Un identifiant bien formé mais inconnu
    aurait alors fait naître un jeu vide à chaque import."""
    _check_did(did)
    try:
        base = deck_dir(did)
    except ValueError:
        raise HTTPException(400, "Identifiant de deck invalide")
    if not base.is_dir():
        raise HTTPException(404, "Deck introuvable")
    return type_dir(did, create=create)


def _next_img_index(d: pathlib.Path) -> tuple[int, int]:
    """(numéro libre, nombre d'images existantes). Le numéro est MAX + 1 : les
    trous laissés par une suppression manuelle ne sont pas repris."""
    hauts, n = 0, 0
    if d.is_dir():
        for p in d.iterdir():
            if IMG_NAME_RE.fullmatch(p.name) and p.is_file():
                n += 1
                hauts = max(hauts, int(p.name[4:-4]))
    return hauts + 1, n


def _store_slot_image(did: str, raw: bytes) -> dict:
    """Décode, borne, écrit — dans cet ordre, et jamais en place.

    Le décodage sert à DEUX choses : refuser ce qui n'est pas une image (un
    `.zip` renommé, un fichier tronqué), et ramener le côté long sous
    `MAX_IMPORT_PX`. L'écran réduit déjà avant d'envoyer ; on le refait ici
    parce qu'un client n'est pas une garantie."""
    from PIL import Image
    d = _deck_or_404(did, create=True)
    libre, n = _next_img_index(d)
    if n >= SLOT_IMAGES_MAX:
        raise HTTPException(
            409, f"Ce jeu porte déjà {SLOT_IMAGES_MAX} images de calque, "
                 f"le maximum. Supprimez-en une du dossier du jeu, ou "
                 f"réutilisez une image déjà importée sur un autre calque.")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(400, "Corps illisible : une image PNG/JPEG/WebP "
                                 "est attendue dans le corps de la requête")
    # RGBA gardé : un calque d'image se pose PAR-DESSUS les couches du bas
    # (papier, illustration, cadre de base), donc sa transparence porte —
    # contrairement à la matière de P6, qui est un fond.
    img = img.convert("RGBA")
    if max(img.size) > MAX_IMPORT_PX:
        k = MAX_IMPORT_PX / float(max(img.size))
        img = img.resize((max(1, round(img.size[0] * k)),
                          max(1, round(img.size[1] * k))), Image.LANCZOS)
    name = f"img_{libre}.png"
    tmp = d / (name + ".tmp")
    img.save(tmp, format="PNG", optimize=False)
    tmp.replace(d / name)
    return {"file": name, "src": "img:" + name, "px": [img.size[0], img.size[1]],
            "bytes": (d / name).stat().st_size, "n": n + 1,
            "max": SLOT_IMAGES_MAX}


def _read_slot_image(did: str, name: str) -> bytes | None:
    d = type_dir(did)
    p = d / name
    try:
        if not p.is_file():
            return None
        return p.read_bytes()
    except OSError:
        return None


# ════════════════════════════════════════════════════════════════════════════
# 5. ROUTES — relatives à /api/cards/{did}/type (règle 8)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/fonts")
async def get_fonts(did: str):
    """Le catalogue des polices RÉELLEMENT servies sur `/fonts/`.

    Lu sur le disque, jamais deviné : 23 familles, 22 `.ttf` et un `.otf`.
    L'écran s'en sert pour peupler son sélecteur — et pour charger chaque
    fichier par `FontFace`, sans CDN ni octet réseau."""
    _check_did(did)
    fonts = await asyncio.to_thread(scan_fonts)
    return {
        "fonts": fonts,
        "count": len(fonts),
        "ttf": sum(1 for f in fonts if f["ext"] == "ttf"),
        "otf": sum(1 for f in fonts if f["ext"] == "otf"),
        "kinds": [{"id": k, "label": v} for k, v in FONT_KINDS.items()],
        "family_prefix": FONT_FAMILY_PREFIX,
        "fallback": FONT_FALLBACK,
        # le nombre de familles qui ont VRAIMENT plus d'un fichier : tant qu'il
        # vaut 0, tout gras et tout italique de l'écran est synthétique, et
        # c'est ce compteur-là qui le dit, pas une promesse.
        "multi_face": sum(1 for f in fonts if f["faces"] > 1),
        # LU DANS LES FICHIERS : combien de familles savent écrire le français.
        # `fr_unknown` = tables cmap illisibles, comptées à part pour que
        # `fr_ok` reste un compte de faits et non un compte d'optimismes.
        "fr_probe": FR_PROBE,
        "fr_ok": sum(1 for f in fonts if f["fr_ok"] is True),
        "fr_partial": sum(1 for f in fonts if f["fr_ok"] is False),
        "fr_unknown": sum(1 for f in fonts if f["fr_ok"] is None),
        "dir": str(fonts_dir()),
    }


@router.get("/presets")
async def get_presets(did: str, fmt: str | None = None, dpi: str | None = None,
                      bleed_mm: str | None = None, safe_mm: str | None = None):
    """Les gabarits, DÉJÀ convertis en millimètres pour le format demandé.

    Un gabarit est écrit en fractions de la zone sûre : converti ici, il tient
    dans la zone sûre des douze formats sans une table par format."""
    _check_did(did)
    body = {"fmt": fmt or DEFAULT_FMT, "dpi": dpi or DEFAULT_DPI,
            "bleed_mm": bleed_mm, "safe_mm": safe_mm}
    g = _geom_from({k: v for k, v in body.items() if v is not None})
    out = []
    for pid, p in PRESETS.items():
        slots = preset_slots(pid, g)
        rep = layout(g, slots)
        out.append({
            "id": pid, "label": p["label"], "hint": p["hint"],
            "n": len(slots), "slots": slots,
            "ok": rep["summary"]["ok"],
            "outside_safe": rep["summary"]["outside_safe"],
        })
    return {"presets": out, "default": DEFAULT_PRESET,
            "geom": g.to_dict(), "safe_rect_mm": [rnd(v, 3) for v in safe_rect_mm(g)]}


@router.post("/layout")
async def post_layout(did: str, body: dict | None = None):
    """Le contrôle : les boîtes et les encombrements mesurés, jugés contre la
    zone sûre AVEC LA MÊME RÈGLE que l'imprimeur.

    Corps : `{fmt, dpi, bleed_mm, safe_mm, slots:[…], ink:{slot_id:[x,y,w,h]},
    posed:{slot_id: pt}}`. `ink` et `posed` viennent du navigateur : lui seul a
    les polices chargées et le moteur de texte qui produira le fichier livré.
    Le backend ne redessine rien — un deuxième moteur ferait diverger l'écran
    et le PDF (risque 2 de la spec)."""
    _check_did(did)
    b = body if isinstance(body, dict) else {}
    g = _geom_from(b)
    slots = norm_slots(b.get("slots"))
    if not slots:
        preset = str(b.get("preset") or DEFAULT_PRESET)
        slots = preset_slots(preset if preset in PRESETS else DEFAULT_PRESET, g)
    try:
        rep = layout(g, slots, b.get("ink"), b.get("posed"), b.get("texts"))
        # le verdict de zone sûre vaut ce que vaut la zone sûre : on livre à
        # côté de lui la mesure de sa stabilité entre définitions.
        rep["definition"] = definition_drift(g.fmt, g.bleed_mm, g.safe_mm)
        return rep
    except (TypeError, ValueError, KeyError) as e:
        logger.exception("cards/type: mise en page impossible")
        raise HTTPException(400, f"Mise en page impossible: {e}")


@router.post("/image")
async def post_slot_image(did: str, request: Request):
    """L'image d'un calque, importée par l'utilisateur — CORPS BRUT.

    Elle est rangée AVEC LE DECK (`decks/{did}/type/img_{n}.png`) et non dans
    le navigateur : un calque de deck doit voyager avec lui — export,
    duplication, sauvegarde. La duplication de la 3a copie déjà le dossier, si
    bien qu'un jeu dupliqué arrive avec ses images sans une ligne de plus.

    Le corps est PESÉ avant d'être décodé (seul ordre qui protège la mémoire),
    puis décodé — ce qui refuse du même geste ce qui n'est pas une image — puis
    ramené sous `MAX_IMPORT_PX` de côté."""
    raw = await request.body()
    if not raw:
        raise HTTPException(400, "Corps vide : envoyer une image")
    if len(raw) > IMG_MAX_BYTES:
        raise HTTPException(413, "Image trop lourde (max 64 Mo)")
    return await asyncio.to_thread(_store_slot_image, did, raw)


@router.get("/image/{name}")
async def get_slot_image(did: str, name: str):
    """L'image d'un calque, telle qu'elle a été rangée.

    LISTE BLANCHE D'ABORD, DISQUE ENSUITE — l'ordre est le fond de l'affaire
    (patron `forge3d.get_node_file`, 2c) : un motif appliqué APRÈS avoir composé
    un chemin a déjà laissé le chemin exister. Le dossier `decks/{did}/type/`
    n'a aujourd'hui que des `img_{n}.png`, mais rien ne garantit qu'il n'aura
    pas d'état interne demain, et cette route ne doit pas s'élargir avec lui.

    LES OCTETS SONT LUS ICI, jamais servis par `FileResponse` : celui-ci
    re-stat le fichier au moment de l'ENVOI, donc APRÈS le contrôle — une
    disparition entre les deux y lève RuntimeError, c'est-à-dire un 500 sur une
    pièce qui n'en fait jamais.

    LE CACHE EST PERMIS, et c'est une conséquence du compteur : `img_7.png` ne
    change jamais de contenu (un import écrit `img_8.png`), donc `no-store` ne
    protégerait de rien et coûterait un aller-retour à chaque frame de
    l'aperçu."""
    _check_did(did)
    # `fullmatch` et non `match` : `$` accepte un saut de ligne final, et le
    # nom vient d'une URL — c'est exactement le genre de caractère qu'on n'a
    # pas envie de voir arriver jusqu'à un chemin.
    if not IMG_NAME_RE.fullmatch(name or ""):
        raise HTTPException(
            400, f"Nom d'image invalide : {name!r} — les images de calque "
                 f"s'appellent « img_1.png », « img_2.png », etc.")
    data = await asyncio.to_thread(_read_slot_image, did, name)
    if data is None:
        raise HTTPException(404, f"Aucune image {name} dans ce jeu")
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})
