"""Traduction L4 (t144) : le PÉRIMÈTRE du lot et le contrôle « plus de texte en dur ».

Le lot couvre TROIS couches entières (fiche t144 du suivi) : frontend/patches/sfxstudio.js (tiroir Sons, rack SFX,
vumètre), frontend/patches/vfxrack.js (rack VFX, Bézier, matte) et frontend/patches/son-vfx-montage.js (écran Son &
VFX DzSonVfx et ses helpers, et l'écran Montage DzMontage de la même couche). La couche frontend/patches/montage.js
(DzTracks…) et le patcher Montage restent à L3.

Ce sont des SOURCES lisibles (pas du minifié) : un groupe de saisie est une plage de lignes d'une couche, telle
qu'elle était à la BASE du lot (main ecf945e4). `restes(textes, gardes, groupes)` rend, dans la plage de chaque
groupe de la couche COURANTE (après saisie), les littéraux qui ressemblent encore à du texte d'interface : ni
argument d'un dzT(…), ni littéral GARDÉ (saisie X ou fragment de gabarit gardé), ni bruit technique.

Le découpage lexical (chaînes, morceaux de gabarits, regex et commentaires sautés) est celui de L1
(scripts/i18n_l1_perimetre.py).
"""
import re

from i18n_l1_perimetre import TECHNIQUES as TECHNIQUES_L1, litteraux, texte_visible

# cible -> fichier de la couche
CIBLES = {"sfxstudio": "frontend/patches/sfxstudio.js",
          "vfxrack": "frontend/patches/vfxrack.js",
          "sonvfx": "frontend/patches/son-vfx-montage.js"}

# groupe -> (cible, première ligne, dernière ligne) — lignes 1-indexées de la couche de BASE (ecf945e4), bornes
# incluses ; un groupe à la dernière ligne None va jusqu'au bout du fichier
GROUPES = {
    "sfx_a": ("sfxstudio", 1, 851),
    "sfx_b": ("sfxstudio", 852, None),
    "vfx": ("vfxrack", 1, None),
    "son_a": ("sonvfx", 1, 563),
    "son_b": ("sonvfx", 564, 1569),
    "montage_a": ("sonvfx", 1570, 4231),
    "montage_b": ("sonvfx", 4232, 5180),
    "montage_c": ("sonvfx", 5181, 5874),
    "montage_d": ("sonvfx", 5875, None),
}

TECHNIQUES = set(TECHNIQUES_L1)
# listes de classes CSS des trois couches (« svm-secbtn svm-kbio », « vfx-btn vfx-add ») : des jetons en minuscules
# dont l'un au moins porte un tiret
_CSS = re.compile(r"\s*[a-z0-9_\-]+(?:\s+[a-z0-9_\-]+)*\s*")


def technique(t):
    return t in TECHNIQUES or (_CSS.fullmatch(t) is not None and "-" in t)


def _offsets(s):
    """index de début de chaque ligne (1-indexé : off[1] = 0)."""
    off = [0, 0]
    k = s.find("\n")
    while k >= 0:
        off.append(k + 1)
        k = s.find("\n", k + 1)
    return off


def plage(s, groupe):
    """(début, fin) en caractères de la plage d'un groupe dans le texte de BASE `s`."""
    _, a, b = GROUPES[groupe]
    off = _offsets(s)
    d = off[a]
    f = len(s) if b is None or b + 1 >= len(off) else off[b + 1]
    return d, f


def groupe_de(s, cible, pos):
    for g, (c, _, _) in GROUPES.items():
        if c == cible:
            d, f = plage(s, g)
            if d <= pos < f:
                return g
    return None


def restes(base, courant, gardes, groupes=None):
    """base/courant = {cible: texte}. La plage d'un groupe est prise dans la BASE puis décalée dans le texte COURANT
    par les longueurs des lignes : on rescanne simplement la couche courante entière, et on attribue chaque littéral
    restant à son groupe par son numéro de ligne (les substitutions ne changent pas le nombre de lignes)."""
    out = []
    for cible, s in courant.items():
        g_txt = {g["texte"][1:-1] for g in gardes if g["cible"] == cible}
        off = _offsets(s)
        for d, e, t, q in litteraux(s, 0, len(s)):
            if s[max(0, d - 4):d] == "dzT(":
                continue
            if t in g_txt or technique(t) or not texte_visible(t):
                continue
            # ligne du littéral
            lo, hi = 1, len(off) - 1
            while lo < hi:
                m = (lo + hi + 1) // 2
                if off[m] <= d:
                    lo = m
                else:
                    hi = m - 1
            g = None
            for gg, (c, a, b) in GROUPES.items():
                if c == cible and a <= lo and (b is None or lo <= b):
                    g = gg
            if groupes is not None and g not in groupes:
                continue
            out.append(f"{g} {cible}:{lo} {t[:90]!r}")
    return out
