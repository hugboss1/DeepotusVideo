"""Traduction L3 (t143) : le PÉRIMÈTRE du lot et le contrôle « plus de texte en dur ».

Le lot couvre la couche frontend/patches/montage.js (window.DzTracks : pistes, barre d'outils flottante, projets,
tiroirs Médias et Texte, étalonnage, scopes, voix off, menus, raccourcis, livraison…) — TOUT ce qui y reste en dur
après L1 (Bibliothèque, Réglages) et L2 (Studio, Templates), dont quelques aides de leurs composants que leurs
relevés avaient laissées (dzSendStudioRendu, dzMasqueSvg, dzAnimStyle…). Les couches sfxstudio, vfxrack et
son-vfx-montage (DzMontage) sont à L4.

C'est une SOURCE lisible : un groupe de saisie est une plage de lignes de la couche telle qu'elle était à la BASE du
lot (main be7f9e9f, L1 et L2 posées). `restes(base, courant, gardes, groupes)` rend, dans la couche COURANTE, les
littéraux qui ressemblent encore à du texte d'interface : ni argument d'un dzT(…), ni littéral GARDÉ (saisie X de L3,
ou gardes « couche » de L1/L2), ni bruit technique. Chaque reste est rangé dans son groupe par son numéro de ligne :
une substitution ne doit donc jamais changer le nombre de lignes (un S sur plusieurs lignes garde ses retours).
"""
import re

from i18n_l1_perimetre import TECHNIQUES as TECHNIQUES_L1, litteraux, texte_visible

# cible -> fichier de la couche
CIBLES = {"montage": "frontend/patches/montage.js"}

# groupe -> (cible, première ligne, dernière ligne) — lignes 1-indexées de la couche de BASE (be7f9e9f), bornes
# incluses ; un groupe à la dernière ligne None va jusqu'au bout du fichier
GROUPES = {
    "montage_a": ("montage", 1, 1035),
    "montage_b": ("montage", 1036, 1946),
    "montage_c": ("montage", 1947, 2724),
    "montage_d": ("montage", 2725, 3529),
    "montage_e": ("montage", 3530, 6345),
    "montage_f": ("montage", 6346, 7067),
    "montage_g": ("montage", 7068, 7799),
    "montage_h": ("montage", 7800, 8925),
    "montage_i": ("montage", 8926, None),
}

TECHNIQUES = set(TECHNIQUES_L1)
# listes de classes CSS des trois couches (« svm-secbtn svm-kbio », « vfx-btn vfx-add ») : des jetons en minuscules
# dont l'un au moins porte un tiret
_CSS = re.compile(r"\s*[a-z0-9_\-]+(?:\s+[a-z0-9_\-]+)*\s*")


def _gardes_l1_l2():
    """Les littéraux de la couche montage.js que L1 et L2 ont GARDÉS (motivés dans leur saisie)."""
    import json
    import pathlib
    racine = pathlib.Path(__file__).resolve().parent
    out = set()
    for t in ("i18n_l1_paires.json", "i18n_l2_paires.json"):
        p = racine / t
        if p.is_file():
            out |= {g["texte"][1:-1] for g in json.loads(p.read_bytes().decode("utf-8"))["gardes"] if g.get("cible") == "couche"}
    return out


GARDES_L1_L2 = _gardes_l1_l2()


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
        g_txt = {g["texte"][1:-1] for g in gardes if g["cible"] == cible} | GARDES_L1_L2
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
