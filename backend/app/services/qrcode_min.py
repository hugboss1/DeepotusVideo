# -*- coding: utf-8 -*-
"""Plan mobile T3 (tâche #56, 01/10/2026) — QR code minimal, stdlib pur — VERSION 4, correction L, mode octet.

POURQUOI si peu : le paquet `qrcode` est absent de requirements.txt et le
runtime livré est stdlib + Pillow (mesuré 03/09). Le QR d'appairage porte
au plus « dz1://pair?h=<ip>&p=<port>&s=<32 hex> », soit ~50 octets.

POURQUOI la version 4 et la correction L : c'est la plus petite version
dont la capacité (78 octets en mode octet) couvre l'URL, et 4-L n'a QU'UN
SEUL bloc de correction — l'entrelacement des blocs, la partie la plus
délicate de la norme, disparaît entièrement.

Nombres de la version 4-L (à vérifier avant de les changer) :
  33 x 33 modules, 100 mots de code, 20 de correction, 80 de données,
  un unique motif d'alignement en (26, 26), pas d'information de version
  (elle n'existe qu'à partir de la version 7).
"""
import struct
import zlib

VERSION = 4
TAILLE = 4 * VERSION + 17          # 33
MOTS_DONNEES = 80
MOTS_CORRECTION = 20
CAPACITE_OCTETS = 78               # 80 mots - 4 bits de mode - 8 de longueur
ALIGNEMENT = (26, 26)

_MASQUES = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]

# ── GF(256), polynôme 0x11D, la table de la norme ────────────────────────────
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _generateur(n: int) -> list[int]:
    g = [1]
    for i in range(n):
        g2 = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            g2[j] ^= c
            g2[j + 1] ^= _mul(c, _EXP[i])
        g = g2
    return g


def _correction(donnees: bytes, n: int) -> list[int]:
    g = _generateur(n)
    reste = list(donnees) + [0] * n
    for i in range(len(donnees)):
        tete = reste[i]
        if tete:
            for j, c in enumerate(g):
                reste[i + j] ^= _mul(c, tete)
    return reste[len(donnees):]


def _bits(charge: bytes) -> list[int]:
    """Mode octet (0100), longueur sur 8 bits (versions 1 à 9), données,
    terminateur, remplissage par 0xEC / 0x11."""
    b: list[int] = [0, 1, 0, 0]
    for i in range(7, -1, -1):
        b.append((len(charge) >> i) & 1)
    for o in charge:
        for i in range(7, -1, -1):
            b.append((o >> i) & 1)
    b += [0] * min(4, MOTS_DONNEES * 8 - len(b))
    while len(b) % 8:
        b.append(0)
    remplissage = (0xEC, 0x11)
    k = 0
    while len(b) < MOTS_DONNEES * 8:
        for i in range(7, -1, -1):
            b.append((remplissage[k % 2] >> i) & 1)
        k += 1
    return b


def _reserve() -> list[list[bool]]:
    res = [[False] * TAILLE for _ in range(TAILLE)]
    for (r0, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < TAILLE and 0 <= c < TAILLE:
                    res[r][c] = True
    for i in range(TAILLE):
        res[6][i] = True
        res[i][6] = True
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            res[ALIGNEMENT[0] + dr][ALIGNEMENT[1] + dc] = True
    for i in range(9):
        res[8][i] = True
        res[i][8] = True
    for i in range(8):
        res[8][TAILLE - 1 - i] = True
        res[TAILLE - 1 - i][8] = True
    res[TAILLE - 8][8] = True
    return res


def _motifs(m: list[list[bool]]) -> None:
    for (r0, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        for dr in range(7):
            for dc in range(7):
                bord = dr in (0, 6) or dc in (0, 6)
                coeur = 2 <= dr <= 4 and 2 <= dc <= 4
                m[r0 + dr][c0 + dc] = bord or coeur
    # synchronisation ENTRE les repères seulement (écart au plan, qui traçait toute la ligne 6 et la colonne 6 et
    # ÉCRASAIT les trois repères : 0 QR lu sur 12 par jsQR, preuve externe du 01/10)
    for i in range(8, TAILLE - 8):
        m[6][i] = i % 2 == 0
        m[i][6] = i % 2 == 0
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            bord = abs(dr) == 2 or abs(dc) == 2
            m[ALIGNEMENT[0] + dr][ALIGNEMENT[1] + dc] = bord or (dr == dc == 0)
    m[TAILLE - 8][8] = True


def _format(m: list[list[bool]], masque: int) -> None:
    """15 bits : 2 de correction (L = 01), 3 de masque, 10 de BCH, XOR
    du masque de format de la norme."""
    val = (0b01 << 3) | masque
    reste = val << 10
    for i in range(4, -1, -1):
        if reste & (1 << (i + 10)):
            reste ^= 0b10100110111 << i
    bits15 = ((val << 10) | reste) ^ 0b101010000010010
    liste = [(bits15 >> (14 - i)) & 1 for i in range(15)]
    for i in range(6):
        m[8][i] = bool(liste[i])
    m[8][7] = bool(liste[6])
    m[8][8] = bool(liste[7])
    m[7][8] = bool(liste[8])
    for i in range(6):
        m[5 - i][8] = bool(liste[9 + i])
    # seconde copie (norme ; écart au plan, qui décalait d'un module et ÉCRASAIT le module noir (n-8, 8)) :
    # bits 0..6 en colonne 8, du bas vers le haut (lignes n-1 .. n-7), bits 7..14 en ligne 8 (colonnes n-8 .. n-1)
    for i in range(7):
        m[TAILLE - 1 - i][8] = bool(liste[i])
    for i in range(8):
        m[8][TAILLE - 8 + i] = bool(liste[7 + i])


def _penalite(m: list[list[bool]]) -> int:
    """Règle 1 seule (séries de 5+), suffisante pour choisir un masque
    honnête sur une charge de 50 octets — la norme en compte quatre."""
    p = 0
    for ligne in list(m) + [list(col) for col in zip(*m)]:
        n, prec = 1, ligne[0]
        for v in ligne[1:]:
            if v == prec:
                n += 1
            else:
                if n >= 5:
                    p += 3 + (n - 5)
                n, prec = 1, v
        if n >= 5:
            p += 3 + (n - 5)
    return p


def matrice(texte: str, masque: int | None = None) -> list[list[bool]]:
    """La matrice 33x33 de `texte` (ASCII/UTF-8), version 4, correction L. `masque` force un masque (0..7) ;
    sinon le moins pénalisé est choisi."""
    charge = texte.encode("utf-8")
    if len(charge) > CAPACITE_OCTETS:
        raise ValueError(
            f"{len(charge)} octets : une version 4-L en porte 78 au plus")
    bits = _bits(charge)
    donnees = bytes(
        int("".join(str(b) for b in bits[i:i + 8]), 2)
        for i in range(0, len(bits), 8))
    flux = list(donnees) + _correction(donnees, MOTS_CORRECTION)
    suite = [(o >> i) & 1 for o in flux for i in range(7, -1, -1)]

    res = _reserve()
    meilleure, meilleur_score = None, None
    for masque in (range(8) if masque is None else (masque,)):
        m = [[False] * TAILLE for _ in range(TAILLE)]
        _motifs(m)
        f = _MASQUES[masque]
        k = 0
        col, haut = TAILLE - 1, True
        while col > 0:
            if col == 6:
                col -= 1
            lignes = range(TAILLE - 1, -1, -1) if haut else range(TAILLE)
            for r in lignes:
                for c in (col, col - 1):
                    if res[r][c]:
                        continue
                    v = bool(suite[k]) if k < len(suite) else False
                    k += 1
                    m[r][c] = (not v) if f(r, c) else v
            haut = not haut
            col -= 2
        _format(m, masque)
        s = _penalite(m)
        if meilleur_score is None or s < meilleur_score:
            meilleure, meilleur_score = m, s
    return meilleure


def png(texte: str, module: int = 8, marge: int = 4, masque: int | None = None) -> bytes:
    """Le QR en PNG noir sur blanc, écrit sans Pillow (zlib suffit)."""
    m = matrice(texte, masque)
    cote = (TAILLE + 2 * marge) * module
    lignes = bytearray()
    for y in range(cote):
        lignes.append(0)                        # filtre None
        r = y // module - marge
        for x in range(cote):
            c = x // module - marge
            noir = (0 <= r < TAILLE and 0 <= c < TAILLE and m[r][c])
            lignes.append(0 if noir else 255)

    def bloc(tag: bytes, data: bytes) -> bytes:
        corps = tag + data
        return (struct.pack(">I", len(data)) + corps
                + struct.pack(">I", zlib.crc32(corps) & 0xFFFFFFFF))

    entete = struct.pack(">IIBBBBB", cote, cote, 8, 0, 0, 0, 0)  # gris 8 bits
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", entete)
            + bloc(b"IDAT", zlib.compress(bytes(lignes), 9))
            + bloc(b"IEND", b""))
