# -*- coding: utf-8 -*-
"""Plan mobile T3 (tache #56 du suivi, 01/10/2026) — QR minimal stdlib, VERSION 4, correction L, mode octet.
Banc-miroir par DECODAGE : il ne relit pas l'encodeur, il decode la MATRICE avec une seconde implementation
(demasquage, zigzag, mode, longueur, octets). Ecarts au plan, qui ne verifiait ni la correction d'erreur ni le format
— or c'est ce qu'un telephone verifie :
  - les 20 SYNDROMES de Reed-Solomon du mot lu sont nuls (calcul independant sur GF(256)) ;
  - les 15 bits de format, lus aux DEUX emplacements, sont la chaine de la norme pour (L, masque) — table thonky.com
    relevee le 01/10/2026 ;
  - le PNG est rouvert par Pillow (taille, deux couleurs, et les modules relus a l'echelle).
Les nombres 4-L (80 donnees, 20 correction, 1 bloc, 78 octets) ont ete releves le 01/10/2026 sur thonky.com.
Temoin positif : la base (eef08cd7) n'a pas qrcode_min.
Run (depuis backend/) : & $PY tests/test_qrcode_min.py"""
import io, os, pathlib, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "cat-file", "-e", "eef08cd7:backend/app/services/qrcode_min.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas qrcode_min", r0.returncode != 0)

TAILLE = 33
MASQUES = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]
#: la norme, niveau L, masques 0..7 (thonky.com/qr-code-tutorial/format-version-tables, 01/10/2026)
FORMAT_L = ["111011111000100", "111001011110011", "111110110101010", "111100010011101",
            "110011000101111", "110001100011000", "110110001000001", "110100101110110"]


def _reserve():
    res = [[False] * TAILLE for _ in range(TAILLE)]
    for (r0_, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0_ + dr, c0 + dc
                if 0 <= r < TAILLE and 0 <= c < TAILLE:
                    res[r][c] = True
    for i in range(TAILLE):
        res[6][i] = res[i][6] = True
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            res[26 + dr][26 + dc] = True
    for i in range(9):
        res[8][i] = res[i][8] = True
    for i in range(8):
        res[8][TAILLE - 1 - i] = res[TAILLE - 1 - i][8] = True
    return res


def _format_haut(m):
    pos = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + [(5 - i, 8) for i in range(6)]
    return "".join("1" if m[r][c] else "0" for r, c in pos)


def _format_bas(m):
    pos = [(TAILLE - 1 - i, 8) for i in range(7)] + [(8, TAILLE - 8 + i) for i in range(8)]
    return "".join("1" if m[r][c] else "0" for r, c in pos)


def _decoder(m):
    fmt = _format_haut(m)
    masque = FORMAT_L.index(fmt) if fmt in FORMAT_L else -1
    assert masque >= 0, f"format illisible {fmt}"
    f = MASQUES[masque]
    res = _reserve()
    bits = []
    col, haut = TAILLE - 1, True
    while col > 0:
        if col == 6:
            col -= 1
        for r in (range(TAILLE - 1, -1, -1) if haut else range(TAILLE)):
            for c in (col, col - 1):
                if not res[r][c]:
                    bits.append(int(bool(m[r][c]) != f(r, c)))
        haut = not haut
        col -= 2
    mots = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, 800, 8)]
    flux = "".join(map(str, bits))
    assert flux[:4] == "0100", f"mode {flux[:4]}"
    n = int(flux[4:12], 2)
    charge = bytes(int(flux[12 + 8 * i:20 + 8 * i], 2) for i in range(n))
    return charge, mots, masque, len(bits)


# GF(256) ecrit autrement : multiplication « paysanne » (sans tables), polynome 0x11D
def _gmul(a, b):
    p = 0
    while b:
        if b & 1:
            p ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11D
        b >>= 1
    return p


def _syndromes(mots):
    out, alpha = [], 1
    for _ in range(20):
        s = 0
        for c in mots:                      # Horner : c(alpha^j)
            s = _gmul(s, alpha) ^ c
        out.append(s)
        alpha = _gmul(alpha, 2)
    return out


from app.services import qrcode_min as Q                            # noqa: E402

print("\n[N] les nombres de la norme")
check("N1 4-L : 33 modules, 80 donnees, 20 correction, 78 octets (releve thonky 01/10/2026)",
      (Q.TAILLE, Q.MOTS_DONNEES, Q.MOTS_CORRECTION, Q.CAPACITE_OCTETS) == (33, 80, 20, 78))

print("\n[F] la forme")
URL = "dz1://pair?h=192.168.1.20&p=8765&s=" + "0f" * 16
m = Q.matrice(URL)
forme = len(m) == TAILLE and all(len(l) == TAILLE for l in m)
for (r0_, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
    forme = forme and m[r0_][c0] and m[r0_ + 6][c0 + 6] and not m[r0_ + 1][c0 + 1] and m[r0_ + 3][c0 + 3]
check("F1 33x33, trois reperes (coin noir, anneau blanc, coeur noir)", forme)
# preuve externe du 01/10 (jsQR, 0 QR lu sur 12) : la ligne de synchronisation du plan traversait les reperes. Chaque
# repere est donc compare EN ENTIER au motif de la norme, separateur blanc compris.
REPERE = ["1111111", "1000001", "1011101", "1011101", "1011101", "1000001", "1111111"]
abimes = []
for mk in [m] + [Q.matrice(URL, masque=k) for k in range(8)]:
    for (r0_, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        lu = ["".join("1" if mk[r0_ + dr][c0 + dc] else "0" for dc in range(7)) for dr in range(7)]
        sep = [mk[r][c] for r in range(r0_ - 1, r0_ + 8) for c in range(c0 - 1, c0 + 8)
               if 0 <= r < TAILLE and 0 <= c < TAILLE and not (r0_ <= r < r0_ + 7 and c0 <= c < c0 + 7)]
        if lu != REPERE or any(sep):
            abimes.append((r0_, c0, lu))
check("F4 les trois reperes sont EXACTEMENT ceux de la norme (7x7 + separateur blanc), pour les huit masques",
      not abimes, str(abimes[:1]))
check("F2 lignes de synchronisation alternees", all(m[6][i] == (i % 2 == 0) and m[i][6] == (i % 2 == 0) for i in range(8, TAILLE - 8)))
check("F3 motif d'alignement en (26, 26) et module noir permanent", m[26][26] and not m[25][26] and m[24][24] and m[TAILLE - 8][8])

print("\n[D] decodage independant")
charge, mots, masque, nbits = _decoder(m)
check("D1 l'URL d'appairage se relit a l'identique", charge.decode("ascii") == URL, repr(charge))
check("D2 807 modules de donnees lus (100 mots + 7 bits de reste, version 4)", nbits == 807, str(nbits))
check("D3 les 20 SYNDROMES de Reed-Solomon sont nuls (un telephone corrigera les erreurs)", _syndromes(mots) == [0] * 20,
      str(_syndromes(mots)[:5]))
check("D4 format : chaine de la norme pour (L, masque), IDENTIQUE aux deux emplacements",
      _format_haut(m) == FORMAT_L[masque] and _format_bas(m) == FORMAT_L[masque], f"{_format_haut(m)} {_format_bas(m)}")
mauvais = []
for n in (1, 2, 17, 45, 77, 78):
    t = "".join(chr(97 + (i % 26)) for i in range(n))
    mm = Q.matrice(t)
    ch, mo, _mq, _nb = _decoder(mm)
    if ch.decode("ascii") != t or _syndromes(mo) != [0] * 20:
        mauvais.append(n)
check("D5 charges de 1 a 78 octets : relues, syndromes nuls", not mauvais, str(mauvais))
masques_vus = {_decoder(Q.matrice("x" * n))[2] for n in range(1, 40, 3)}
check("D6 le masque est CHOISI (plusieurs masques servent selon la charge), et chacun se relit", len(masques_vus) >= 2, str(masques_vus))
try:
    Q.matrice("x" * 79); e = None
except ValueError as x:
    e = str(x)
check("D7 au-dela de 78 octets : refus qui le dit", e is not None and "78" in e, str(e))
faux = []
for k in range(8):                       # D4 ne voit que le masque CHOISI : un bit mal place peut y tomber juste
    mk = Q.matrice(URL, masque=k)
    chk, mok, mqk, _n = _decoder(mk)
    if not (mqk == k and chk.decode("ascii") == URL and _syndromes(mok) == [0] * 20
            and _format_haut(mk) == _format_bas(mk) == FORMAT_L[k] and mk[TAILLE - 8][8]):
        faux.append((k, _format_haut(mk), _format_bas(mk)))
check("D9 les HUIT masques forces : relus, syndromes nuls, format de la norme aux deux places, module noir intact",
      not faux, str(faux[:3]))
ch_u = _decoder(Q.matrice("dz1://é"))[0]
check("D8 UTF-8 : l'octet est porte tel quel", ch_u == "dz1://é".encode("utf-8"), repr(ch_u))

print("\n[P] le PNG")
from PIL import Image                                               # noqa: E402
png = Q.png("dz1://pair?h=10.0.0.5&p=8765&s=" + "1" * 32, module=8, marge=4)
im = Image.open(io.BytesIO(png))
cote = (TAILLE + 8) * 8
check("P1 taille demandee, deux couleurs seulement", im.size == (cote, cote) and set(im.convert("L").getdata()) == {0, 255}, str(im.size))
mp = Q.matrice("dz1://pair?h=10.0.0.5&p=8765&s=" + "1" * 32)
g = im.convert("L")
relue = all((g.getpixel(((c + 4) * 8 + 4, (r + 4) * 8 + 4)) == 0) == bool(mp[r][c]) for r in range(TAILLE) for c in range(TAILLE))
marge_blanche = all(g.getpixel((x, y)) == 255 for x in range(cote) for y in (0, 31, cote - 1))
check("P2 chaque module relu au centre de sa case, marge blanche (zone calme)", relue and marge_blanche)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
