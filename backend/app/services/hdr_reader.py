# -*- coding: utf-8 -*-
"""Lire un .hdr (Radiance RGBE) en stdlib pur, et en faire une ambiance LDR.

POURQUOI. `<model-viewer>` a besoin d'une image d'environnement, sinon un
matériau métallique s'affiche NOIR (c'est déjà écrit dans `env_service`). Les
sept ambiances du dépôt sont générées en PIL ; R10c P2 demande en plus les
HDRI de l'utilisateur — et les HDRI du monde réel sont des `.hdr`.

LE FORMAT, ET POURQUOI IL EST LISIBLE SANS DÉPENDANCE. Un fichier Radiance est
un en-tête TEXTE, une ligne vide, une ligne de résolution, puis des scanlines
de quadruplets RGBE : trois octets de mantisse et UN exposant partagé, quatre
octets par pixel, `canal = M x 2^(E-128)`. Aucune compression d'entropie,
aucun flottant à décoder : du découpage d'octets suffit.

    #?RADIANCE
    FORMAT=32-bit_rle_rgbe
    EXPOSURE=1.0            (facultatif, multiplicatif, répétable)
                            <- ligne vide : fin de l'en-tête
    -Y 512 +X 1024          <- résolution ET orientation

Deux codages de scanline :
  * PLAT — `w` quadruplets entrelacés, dans l'ordre des pixels ;
  * RLE ADAPTATIF (« new-style ») — la scanline commence par `02 02 hi lo`
    avec `(hi << 8) | lo == w` et `8 <= w <= 32767` ; suivent QUATRE plans
    (R, G, B, E), chacun codé ainsi : un octet `c > 128` annonce `c - 128`
    copies de l'octet suivant, un octet `c <= 128` annonce `c` octets
    littéraux.
  * L'ANCIEN RLE (un pixel `255 255 255 n` qui répète le précédent) est
    REFUSÉ EN LE DISANT plutôt que deviné. Plus aucun outil ne l'écrit depuis
    vingt ans, et un décodeur silencieusement faux est pire qu'un refus : la
    matière sortirait éclairée de travers, sans que rien ne grince.

`.exr` EST HORS PÉRIMÈTRE, ET C'EST DIT ICI. OpenEXR admet au moins dix
schémas de compression (NONE, RLE, ZIPS, ZIP, PIZ, PXR24, B44, B44A, DWAA,
DWAB) ; seuls NONE et ZIP/ZIPS retomberaient sur `zlib`, et rien ne garantit
qu'un fichier donné soit de ceux-là. Un décodeur partiel qui refuse un fichier
sur deux APRÈS le téléchargement serait une promesse fausse : la route refuse
donc `.exr` par son extension, avec la phrase qui dit quoi faire.

Références relues le 03/09/2026 : `graphics.cornell.edu/~bjw/rgbe.html`
(implémentation de référence de Bruce Walter ; le `.c` lui-même répond
HTTP 300 à la lecture automatique), `floyd.lbl.gov/radiance/refer/filefmts.pdf`
(148,6 Ko, HTTP 200, illisible par l'outil de ce poste),
`en.wikipedia.org/wiki/RGBE_image_format` (magic `23 3f 52 41 44 49 41 4e 43
45 0a`, `fR = R x 2^(E-128)`).
"""
from __future__ import annotations

import math

from PIL import Image

__all__ = ["MAGIC", "HDR_MAX_PIXELS", "SORTIE", "lire_entete", "decoder",
           "equirect_ldr"]

MAGIC = b"#?"
SORTIE = (1024, 512)          # même taille que les sept ambiances du dépôt

# GARDE DE TAILLE, ET ELLE EST CHIFFRÉE. Le décodage garde 4 octets par pixel
# en mémoire (les quatre plans) : un 4096x2048 coûte 33 Mo, un 8192x4096 en
# coûterait 134, et un 16k 537. Comme la sortie fait de toute façon 1024x512,
# refuser au-delà de 12 Mpx ne coûte rien à personne et évite de manger la
# mémoire d'une machine qui rend une vidéo à côté.
HDR_MAX_PIXELS = 12_000_000


def _ligne(data: bytes, i: int) -> tuple[str, int]:
    j = data.find(b"\n", i)
    if j < 0:
        raise ValueError("HDR : en-tête tronqué (aucune fin de ligne)")
    return data[i:j].decode("latin-1"), j + 1


def lire_entete(data: bytes) -> tuple[dict, int]:
    """L'en-tête, la résolution, et l'offset du PREMIER octet de pixel."""
    if not data.startswith(MAGIC):
        raise ValueError("HDR : ce fichier ne commence pas par « #? » — ce "
                         "n'est pas un Radiance (.hdr)")
    entete: dict = {}
    signature, i = _ligne(data, 0)
    entete["signature"] = signature.strip()
    while True:
        ligne, i = _ligne(data, i)
        s = ligne.strip()
        if not s:
            break
        if s.startswith("#"):
            continue
        if "=" in s:
            cle, _, val = s.partition("=")
            entete[cle.strip().upper()] = val.strip()
    fmt = entete.get("FORMAT", "32-bit_rle_rgbe")
    if "rgbe" not in fmt.lower():
        raise ValueError(
            f"HDR : FORMAT={fmt} — seul 32-bit_rle_rgbe est lu. Le XYZE "
            "demanderait une conversion colorimétrique que rien ici ne sait "
            "faire ; réexportez en RGBE.")
    res, i = _ligne(data, i)
    p = res.split()
    if len(p) != 4 or p[0] != "-Y" or p[2] != "+X":
        raise ValueError(
            f"HDR : ligne de résolution « {res.strip()} » — seule "
            "l'orientation standard « -Y h +X w » est lue (les sept autres "
            "orientations du format sont légales mais introuvables en "
            "pratique, et les deviner serait une image retournée sans un mot)")
    h, w = int(p[1]), int(p[3])
    if w <= 0 or h <= 0:
        raise ValueError(f"HDR : résolution {w}x{h} invalide")
    if w * h > HDR_MAX_PIXELS:
        raise ValueError(
            f"HDR : {w}x{h}, soit {w * h / 1e6:.0f} Mpx — au-delà de la garde "
            f"de {HDR_MAX_PIXELS // 10 ** 6} Mpx. L'ambiance ne fait de toute "
            f"façon que {SORTIE[0]}x{SORTIE[1]} : réexportez en 4k.")
    entete["width"], entete["height"] = w, h
    return entete, i


def _scanline(data: bytes, i: int, w: int, sortie: bytearray) -> int:
    """Décode UNE scanline en 4·w octets planaires (R…, G…, B…, E…)."""
    if i + 4 > len(data):
        raise ValueError("HDR : fichier tronqué (scanline manquante)")
    if data[i] == 255 and data[i + 1] == 255 and data[i + 2] == 255:
        raise ValueError(
            "HDR : ancien codage RLE (255 255 255 n) — plus aucun outil ne "
            "l'écrit depuis vingt ans. Réexportez depuis un logiciel récent.")
    if not (8 <= w <= 32767 and data[i] == 2 and data[i + 1] == 2
            and (data[i + 2] << 8 | data[i + 3]) == w):
        fin = i + 4 * w
        bloc = data[i:fin]
        if len(bloc) < 4 * w:
            raise ValueError("HDR : fichier tronqué (scanline plate)")
        for c in range(4):
            sortie[c * w:(c + 1) * w] = bloc[c::4]
        return fin
    i += 4
    for c in range(4):
        x, base = 0, c * w
        while x < w:
            if i >= len(data):
                raise ValueError("HDR : fichier tronqué (plan RLE)")
            n = data[i]
            i += 1
            if n > 128:
                n -= 128
                if x + n > w:
                    raise ValueError("HDR : répétition RLE hors scanline")
                sortie[base + x:base + x + n] = bytes([data[i]]) * n
                i += 1
            else:
                if n == 0 or x + n > w or i + n > len(data):
                    raise ValueError("HDR : bloc littéral RLE invalide")
                sortie[base + x:base + x + n] = data[i:i + n]
                i += n
            x += n
    return i


def decoder(data: bytes) -> tuple[int, int, bytearray]:
    """(largeur, hauteur, 4·w·h octets) — les plans R, G, B, E, RANGÉE PAR
    RANGÉE (pour la rangée y : R sur w octets, puis G, puis B, puis E).

    On rend des octets bruts et pas des flottants : 8 Mpx de triplets Python
    coûteraient 400 Mo et vingt secondes d'allocation, pour une image dont on
    ne gardera que 1024x512."""
    entete, i = lire_entete(data)
    w, h = entete["width"], entete["height"]
    plans = bytearray(4 * w * h)
    ligne = bytearray(4 * w)
    for y in range(h):
        i = _scanline(data, i, w, ligne)
        plans[y * 4 * w:(y + 1) * 4 * w] = ligne
    return w, h, plans


def _luts(plans: bytearray, w: int, h: int, gamma: float = 2.2) -> list:
    """256 LUT de 256 entrées : `_luts[E][M]` donne l'octet de sortie.

    L'EXPOSITION EST UNE MÉDIANE, PAS UN MAXIMUM, et c'est la seule décision
    de ce module. Un HDRI porte presque toujours un soleil des milliers de
    fois plus lumineux que le ciel : normaliser sur le maximum rendrait tout
    le reste noir, ce qui est exactement le contraire de ce qu'on veut d'une
    carte d'éclairage. La médiane de l'exposant partagé donne l'échelle de la
    SCÈNE. Courbe de Reinhard (`y = x / (1 + x)`) : elle ne sature jamais,
    donc le soleil reste un point clair au lieu d'une tache blanche à bord
    franc, ce qui compte pour un reflet.
    """
    hist = [0] * 256
    for y in range(h):
        base = y * 4 * w + 3 * w
        for e in plans[base:base + w]:
            hist[e] += 1
    n = sum(hist) or 1
    acc, med = 0, 128
    for e, c in enumerate(hist):
        acc += c
        if acc >= n * 0.5:
            med = e
            break
    if med == 0:                     # image entièrement noire
        med = 128
    # `s` ramène la luminance médiane à ~0,5 après Reinhard (x = 1)
    s = 2.0 ** (128 - med)
    inv = 1.0 / max(0.1, gamma)
    table = []
    for e in range(256):
        if e == 0:
            table.append(bytes(256))
            continue
        k = (2.0 ** (e - 128)) * s / 256.0
        table.append(bytes(
            min(255, int(round(255.0 * ((m + 0.5) * k / (1.0 + (m + 0.5) * k))
                               ** inv))) for m in range(256)))
    return table


def equirect_ldr(data: bytes, sortie: tuple = SORTIE) -> Image.Image:
    """Un `.hdr` -> l'équirectangulaire LDR RGB que le viewport sait lire.

    Échantillonnage au point à DEUX FOIS la taille de sortie, puis réduction
    en BOX : le premier reste une boucle Python (3 x 2,1 M consultations de
    LUT, mesuré sous 3 s), le second est en C et rend au moyennage ce que le
    point-à-point lui a pris. Un HDRI sert d'éclairage diffus : c'est
    l'intégrale qui compte, pas le pixel."""
    w, h, plans = decoder(data)
    ow, oh = int(sortie[0]), int(sortie[1])
    tw, th = ow * 2, oh * 2
    table = _luts(plans, w, h)
    brut = bytearray(3 * tw * th)
    for j in range(th):
        y = min(h - 1, j * h // th)
        base = y * 4 * w
        ligne_e = plans[base + 3 * w:base + 4 * w]
        for i in range(tw):
            x = min(w - 1, i * w // tw)
            t = table[ligne_e[x]]
            o = 3 * (j * tw + i)
            brut[o] = t[plans[base + x]]
            brut[o + 1] = t[plans[base + w + x]]
            brut[o + 2] = t[plans[base + 2 * w + x]]
    return Image.frombytes("RGB", (tw, th), bytes(brut)).resize(
        (ow, oh), Image.BOX)
