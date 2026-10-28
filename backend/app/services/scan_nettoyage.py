"""t312 (28/10/2026) (C1 Scan, tâche 2) — nettoyage du texte lu par l'OCR (module PUR : ni fichier, ni réseau).

Entrée : les sorties de `scan_ocr.lire_page` ({langue, angle, lignes:[{texte, mots:[{texte,x,y,l,h}]}], largeur,
hauteur}, boîtes dans le repère de l'image d'origine). Sortie : {texte, incertains:[{debut,fin}], stats, langue}.

Décision 4 du plan, avec les précisions retenues ici :
- Lignes : les mots d'une ligne séparés par un grand blanc (> 2,5 × leur hauteur et > 3 % de la largeur) forment
  deux lignes (l'OCR fusionne parfois deux colonnes).
- Folios : ligne extrême (la plus haute dans les 20 % du haut, la plus basse dans les 20 % du bas) faite d'un nombre,
  d'un nombre romain ou de « — 12 — ». Titres courants : même ligne de tête (casse, chiffres, folio et ponctuation
  ignorés) sur ≥ 2 pages.
- Colonnes : histogramme horizontal de couverture des lignes (200 cases) ; une gouttière est une bande vide (au plus
  une ligne sur dix la traverse : un titre) d'au moins 1,5 % de la largeur, avec ≥ 2 lignes de chaque côté dont des
  lignes CÔTE À CÔTE (chevauchement vertical) — c'est ce qui distingue une vraie colonne d'un retrait de première ligne
  ou d'une réplique courte ; chaque colonne garde ≥ 8 % de la largeur. Les lignes qui traversent la gouttière sont
  « pleine largeur » (titres) : elles coupent la page en blocs, chaque bloc est lu colonne par colonne, gauche à droite.
- Paragraphes : interligne > 1,5 × l'interligne de référence (médian, plafonné à 1,5 × la hauteur médiane de ligne),
  ou ligne précédente nettement plus courte finie par .!?:»…”", ou première ligne en retrait après une phrase finie ;
  une ligne pleine largeur est toujours un paragraphe à part ; d'une colonne ou d'une page à l'autre, le texte continue
  sauf ligne courte finie ou retrait.
- Césures : mot fini par un tiret en fin de ligne, suivi d'une minuscule -> recollé sans tiret ; suivi d'une majuscule
  ou d'un chiffre (Jean-/Pierre, 1914-/1918) -> recollé en gardant le tiret ; en français, les composés connus
  (peut-être, a-t-il, celui-ci, c'est-à-dire…) gardent leur tiret. L'anglais recolle toujours les minuscules.
- Mots incertains : Décision 3 (`incertain`) + jeton d'un seul signe isolé au milieu d'une ligne + (mode auto) mot lu
  autrement par l'autre passe (boîte alignée par recouvrement, IoU ≥ 0,5 ; un recouvrement plus faible = découpage
  différent = incertain ; aucun recouvrement = pas d'avis). Positions sur le CŒUR du mot (ponctuation collée exclue).
- Mode auto (Décision 2) : la passe au moins de mots incertains est gardée, égalité -> fr.
"""
from __future__ import annotations

import math
import re
import unicodedata

PONCT = frozenset(".,;:!?…'’‘‚\"“”„«»‹›()[]-‐‑–—/&%*§°+=@#€$£¥‰×²³¹½¼¾©®™·¬­  ")
SEUL_PERMIS = frozenset("—–-‐«»:;!?&%/…§+=×#*$€£")      # signes qui vivent seuls au milieu d'une ligne
FIN_PHRASE = tuple(".!?:»…”\"")
TIRETS = "-‐­¬"
_UNITES = (r"kg|g|mg|µg|t|km|m|cm|mm|µm|nm|m²|m³|km²|cm²|l|L|cl|cL|ml|mL|dl|h|min|mn|s|ms|ha|°C|°F|°|%|€|\$|£|"
           r"px|pt|ko|Ko|Mo|Go|To|KB|MB|GB|TB|kB|Hz|kHz|MHz|GHz|W|kW|V|A|mph|ft|in|lb|lbs|oz|am|pm|k|M|x|j|an|ans|"
           r"bis|ter")
_MOTIFS = tuple(re.compile(p) for p in (
    r"^\d+(e|er|ère|re|ème|eme|es|ers|ères|res|èmes|emes|nd|nde|nds|ndes|d|de|ds|des|st|rd|th)$",
    r"^[nN]°\d+$",
    rf"^\d+([.,]\d+)?({_UNITES})$",
    r"^\d{1,2}h\d{2}$",
    r"^[A-Z]{1,5}\d{1,4}$",
    r"^\d+[DK]$",
    r"^\d+(s|’s|'s)$",
))
_ROMAIN = r"(?=[MDCLXVI])M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"
_BORD = r"[\s\-‐–—.·•]*"
_FOLIO = re.compile(rf"^{_BORD}(?:\d{{1,4}}|{_ROMAIN}){_BORD}$", re.I)
_MARQUE = re.compile(r"\[\[\?(.*?)\]\]", re.S)

# composés français dont la seconde partie garde le tiret en fin de ligne
_FR_LIBRES = frozenset({"être", "il", "ils", "elle", "elles", "on", "je", "nous", "vous", "moi", "toi", "même", "mêmes"})
_FR_PAIRES = {
    "ci": {"celui", "celle", "ceux", "celles", "ce", "là", "par", "ici", "jusque"},
    "là": {"celui", "celle", "ceux", "celles", "ce", "par", "jusque", "ici", "de", "au"},
    "ce": {"est", "qu'est", "qu’est", "sont", "était", "fut", "serait", "sera"},
    "dire": {"à"},
    "bas": {"là", "ici", "en", "là"},
    "delà": {"au", "par", "là"}, "dessus": {"au", "là", "ci", "par", "en"}, "dessous": {"au", "là", "ci", "par", "en"},
    "dedans": {"au", "là", "en"}, "dehors": {"au", "là", "en"}, "devant": {"au", "là", "par"},
}
_FR_INVERSION = frozenset({"il", "ils", "elle", "elles", "on"})

BANDE_BORD = 0.20          # part de la hauteur où chercher folios et titres courants
NB_CASES = 200             # histogramme horizontal des colonnes
GOUTTIERE_MIN = 3          # cases (1,5 % de la largeur)
COLONNE_MIN = 0.08         # part de la largeur
SEUIL_COURTE = 0.15        # « nettement plus courte » : finit avant 85 % de la colonne


# ------------------------------------------------------------------------------------------------- mots incertains
def _coeur(t: str) -> tuple[int, int]:
    """Bornes du mot sans la ponctuation collée au début et à la fin."""
    d, f = 0, len(t)
    while d < f and t[d] in PONCT:
        d += 1
    while f > d and t[f - 1] in PONCT:
        f -= 1
    return d, f


def incertain(mot: str) -> bool:
    """Décision 3 (hors contexte) : lettres et chiffres mêlés hors motifs connus, caractère inhabituel, caractère
    (non chiffre) répété plus de 3 fois."""
    if not isinstance(mot, str):
        return False
    t = mot.strip()
    if not t:
        return False
    for ch in t:
        if not (ch.isalpha() or ch.isdigit() or ch in PONCT):
            return True
    if re.search(r"(\D)\1{3,}", t.casefold()):
        return True
    d, f = _coeur(t)
    for piece in re.split(r"[-‐‑–—/'’]", t[d:f]):
        if any(c.isalpha() for c in piece) and any(c.isdecimal() for c in piece):
            if not any(m.match(piece) for m in _MOTIFS):
                return True
    return False


def depuis_marques(texte: str) -> tuple[str, list]:
    """« le [[?chat]] dort » -> (« le chat dort », [{debut: 3, fin: 7}]) ; une marque vide est retirée."""
    sortie, positions, pos, n = [], [], 0, 0
    for m in _MARQUE.finditer(texte or ""):
        avant = texte[pos:m.start()]
        sortie.append(avant); n += len(avant)
        mot = m.group(1)
        if mot:
            positions.append({"debut": n, "fin": n + len(mot)})
            sortie.append(mot); n += len(mot)
        pos = m.end()
    sortie.append((texte or "")[pos:])
    return "".join(sortie), positions


# ------------------------------------------------------------------------------------------------- outils
def _num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def _mediane(vals, defaut: float = 0.0) -> float:
    v = sorted(vals)
    if not v:
        return defaut
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def _quantile(vals, q: float) -> float:
    v = sorted(vals)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0


def _texte(li: dict) -> str:
    return " ".join(m["t"] for m in li["mots"])


def _hauteur(li: dict) -> float:
    return li["y1"] - li["y0"]


# ------------------------------------------------------------------------------------------------- lecture des pages
def _jetons(page: dict) -> list[list[dict]]:
    """Lignes brutes de l'OCR -> listes de jetons {t, x0, y0, x1, y1, ctx}."""
    lignes, dernier = [], 0.0
    for li in page.get("lignes") or []:
        if not isinstance(li, dict):
            continue
        mots = []
        for m in li.get("mots") or []:
            if not isinstance(m, dict):
                continue
            x, y = _num(m.get("x")), _num(m.get("y"))
            l, h = max(_num(m.get("l")), 0.0), max(_num(m.get("h")), 0.0)
            for t in str(m.get("texte") or "").split():
                mots.append({"t": t, "x0": x, "y0": y, "x1": x + l, "y1": y + h, "ctx": False})
        if not mots:   # ligne sans boîtes : gardée dans l'ordre, juste sous la précédente
            mots = [{"t": t, "x0": 0.0, "y0": dernier + 1, "x1": 0.0, "y1": dernier + 1, "ctx": False}
                    for t in str(li.get("texte") or "").split()]
        if mots:
            dernier = max(dernier, max(m["y1"] for m in mots))
            lignes.append(mots)
    return lignes


def _ligne(mots: list[dict]) -> dict:
    return {"mots": mots, "x0": min(m["x0"] for m in mots), "y0": min(m["y0"] for m in mots),
            "x1": max(m["x1"] for m in mots), "y1": max(m["y1"] for m in mots)}


def _couper(mots: list[dict], W: float) -> list[dict]:
    """Recoupe une ligne au grand blanc (deux colonnes fusionnées par l'OCR) ; marque les signes isolés."""
    mots = sorted(mots, key=lambda m: m["x0"])
    for j, m in enumerate(mots):
        t = m["t"]
        if 0 < j < len(mots) - 1 and len(t) == 1 and not t.isalnum() and t not in SEUL_PERMIS:
            m["ctx"] = True
    h = _mediane([m["y1"] - m["y0"] for m in mots if m["y1"] > m["y0"]])
    seuil = max(2.5 * h, 0.03 * W) if h > 0 else math.inf
    groupes, cur = [], [mots[0]]
    for a, b in zip(mots, mots[1:]):
        if b["x0"] - a["x1"] > seuil:
            groupes.append(cur); cur = []
        cur.append(b)
    groupes.append(cur)
    return [_ligne(g) for g in groupes]


def _discorde(m: dict, autres: list[dict]) -> bool:
    a = (m["x1"] - m["x0"]) * (m["y1"] - m["y0"])
    if a <= 0:
        return False
    meilleur, texte, touche = 0.0, None, False
    for o in autres:
        iw = min(m["x1"], o["x1"]) - max(m["x0"], o["x0"])
        ih = min(m["y1"], o["y1"]) - max(m["y0"], o["y0"])
        if iw <= 0 or ih <= 0:
            continue
        touche = True
        inter = iw * ih
        iou = inter / (a + (o["x1"] - o["x0"]) * (o["y1"] - o["y0"]) - inter)
        if iou > meilleur:
            meilleur, texte = iou, o["t"]
    if not touche:
        return False
    if meilleur < 0.5:
        return True
    d1, f1 = _coeur(m["t"]); d2, f2 = _coeur(texte)
    return m["t"][d1:f1] != texte[d2:f2]


# ------------------------------------------------------------------------------------------------- folios, titres
def _cle_titre(txt: str) -> str:
    toks = unicodedata.normalize("NFC", txt).casefold().split()
    while toks and _FOLIO.match(toks[0]):
        toks.pop(0)
    while toks and _FOLIO.match(toks[-1]):
        toks.pop()
    t = re.sub(r"\d+", " ", " ".join(toks))
    t = re.sub(r"[^\w\s]|_", " ", t)
    return " ".join(t.split())


def _retirer_folios(lignes: list[dict], Hp: float, haut: bool, bas: bool) -> int:
    n = 0
    for cote_haut in (True, False):
        if (cote_haut and not haut) or (not cote_haut and not bas):
            continue
        for _ in range(2):
            if not lignes:
                return n
            li = min(lignes, key=lambda x: x["y0"]) if cote_haut else max(lignes, key=lambda x: x["y1"])
            if not _FOLIO.match(_texte(li)):
                break
            if (cote_haut and li["y0"] > BANDE_BORD * Hp) or (not cote_haut and li["y1"] < (1 - BANDE_BORD) * Hp):
                break
            lignes.remove(li); n += 1
    return n


def _tete(lignes: list[dict], Hp: float):
    if not lignes:
        return None
    li = min(lignes, key=lambda x: x["y0"])
    return li if li["y0"] <= BANDE_BORD * Hp else None


# ------------------------------------------------------------------------------------------------- colonnes
def _chevauche(a: dict, b: dict) -> bool:
    ov = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
    return ov > 0 and ov >= 0.5 * min(_hauteur(a), _hauteur(b))


def _coupe_valide(lignes: list[dict], s: float) -> bool:
    g = [li for li in lignes if li["x1"] <= s]
    d = [li for li in lignes if li["x0"] >= s]
    if len(g) < 2 or len(d) < 2:
        return False
    cote = sum(1 for a in g if any(_chevauche(a, b) for b in d))
    return cote >= max(2, math.ceil(0.3 * min(len(g), len(d))))


def _plein(li: dict, coupes: list[float]) -> bool:
    return any(li["x0"] < s < li["x1"] for s in coupes)


def _col(li: dict, coupes: list[float]) -> int:
    return sum(1 for s in coupes if li["x0"] >= s)


def _decoupes(lignes: list[dict], W: float) -> list[float]:
    n = len(lignes)
    if n < 4 or W <= 0:
        return []
    pas = W / NB_CASES
    cov = [0] * NB_CASES
    for li in lignes:
        b0 = max(0, min(NB_CASES - 1, int(li["x0"] / pas)))
        b1 = max(b0, min(NB_CASES - 1, int(math.ceil(li["x1"] / pas)) - 1))
        for b in range(b0, b1 + 1):
            cov[b] += 1
    tol = max(1, n // 10)
    bg = int(min(li["x0"] for li in lignes) / pas) + 1
    bd = min(NB_CASES - 1, int(math.ceil(max(li["x1"] for li in lignes) / pas)) - 2)
    coupes, i = [], bg
    while i <= bd:
        if cov[i] > tol:
            i += 1; continue
        j = i
        while j + 1 <= bd and cov[j + 1] <= tol:
            j += 1
        bas = min(cov[i:j + 1])                 # dans la bande, la plus longue suite au plus bas
        meilleur, k = None, i
        while k <= j:
            if cov[k] != bas:
                k += 1; continue
            m = k
            while m + 1 <= j and cov[m + 1] == bas:
                m += 1
            if meilleur is None or m - k > meilleur[1] - meilleur[0]:
                meilleur = (k, m)
            k = m + 1
        if meilleur[1] - meilleur[0] + 1 >= GOUTTIERE_MIN:
            s = (meilleur[0] + meilleur[1] + 1) / 2 * pas
            if _coupe_valide(lignes, s):
                coupes.append(s)
        i = j + 1
    while coupes:
        cols = [[] for _ in range(len(coupes) + 1)]
        for li in lignes:
            if not _plein(li, coupes):
                cols[_col(li, coupes)].append(li)
        mauvaise = next((k for k, c in enumerate(cols)
                         if not c or max(x["x1"] for x in c) - min(x["x0"] for x in c) < COLONNE_MIN * W), None)
        if mauvaise is None:
            break
        coupes.pop(min(mauvaise, len(coupes) - 1))
    return coupes


def _ordre(lignes: list[dict], coupes: list[float], ip: int) -> list[tuple[dict, tuple]]:
    """Ordre de lecture : blocs séparés par les lignes pleine largeur, colonnes de gauche à droite, haut en bas."""
    srt = sorted(lignes, key=lambda li: (li["y0"], li["x0"]))
    if not coupes:
        return [(li, (ip, 0, 0)) for li in srt]
    sorties, bloc, ib, dans_plein = [], [], 0, False

    def vider():
        nonlocal ib
        for c in range(len(coupes) + 1):
            for li in sorted((x for x in bloc if _col(x, coupes) == c), key=lambda x: (x["y0"], x["x0"])):
                sorties.append((li, (ip, ib, c)))
        bloc.clear(); ib += 1

    for li in srt:
        if _plein(li, coupes):
            if bloc:
                vider()
            sorties.append((li, (ip, ib, -1))); dans_plein = True
        else:
            if dans_plein:
                ib += 1; dans_plein = False
            bloc.append(li)
    if bloc:
        vider()
    return sorties


# ------------------------------------------------------------------------------------------------- césures
def _garde_tiret(base: str, suite: str, langue: str) -> bool:
    if langue != "fr":
        return False
    d, f = _coeur(suite)
    s = suite[d:f].casefold()
    s = re.split(r"[-‐]", s)[0]
    dernier = re.split(r"[-‐]", base.casefold())[-1]
    if s in _FR_LIBRES:
        return True
    if dernier == "t" and s in _FR_INVERSION:
        return True
    return dernier in _FR_PAIRES.get(s, ())


def _coller(p: str, s: str, langue: str):
    """Recollage d'une césure : texte recollé, ou None si la fin de ligne n'est pas une césure."""
    if len(p) < 2 or p[-1] not in TIRETS or not p[-2].isalnum() or not s or not s[0].isalnum():
        return None
    base = p[:-1]
    if p[-1] in "­¬":
        return base + s
    if p[-2].isalpha() and s[0].islower() and not _garde_tiret(base, s, langue):
        return base + s
    return base + "-" + s


# ------------------------------------------------------------------------------------------------- nettoyage
def _langue(pages: list[dict], langue: str) -> str:
    for p in pages:
        if p.get("langue") in ("fr", "en"):
            return p["langue"]
    return langue if langue in ("fr", "en") else "fr"


def _nettoyer(pages: list[dict], langue: str, autre: list[dict] | None) -> dict:
    stats = {"pages": len(pages), "lignes": 0, "mots": 0, "incertains": 0, "colonnes": 0,
             "folios_retires": 0, "titres_retires": 0, "cesures": 0}
    lg = _langue(pages, langue)
    par_page = []
    for ip, page in enumerate(pages):
        brutes = _jetons(page)
        if autre is not None and ip < len(autre) and isinstance(autre[ip], dict):
            autres = [m for li in _jetons(autre[ip]) for m in li]
            for li in brutes:
                for m in li:
                    if _discorde(m, autres):
                        m["ctx"] = True
        W = _num(page.get("largeur")) or max((m["x1"] for li in brutes for m in li), default=0.0)
        Hp = _num(page.get("hauteur")) or max((m["y1"] for li in brutes for m in li), default=0.0)
        lignes = [x for li in brutes for x in _couper(li, W)]
        stats["folios_retires"] += _retirer_folios(lignes, Hp, True, True)
        par_page.append({"lignes": lignes, "W": W, "H": Hp})

    # titres courants : même ligne de tête sur au moins deux pages
    vues: dict[str, set] = {}
    for ip, pp in enumerate(par_page):
        t = _tete(pp["lignes"], pp["H"])
        k = _cle_titre(_texte(t)) if t else ""
        pp["cle"] = k
        if len(k) >= 3:
            vues.setdefault(k, set()).add(ip)
    for pp in par_page:
        if len(vues.get(pp["cle"], ())) >= 2:
            pp["lignes"].remove(_tete(pp["lignes"], pp["H"]))
            stats["titres_retires"] += 1
            stats["folios_retires"] += _retirer_folios(pp["lignes"], pp["H"], True, False)

    # ordre de lecture et repères de mise en page
    flux = []
    for ip, pp in enumerate(par_page):
        lignes, W = pp["lignes"], pp["W"]
        if not lignes:
            continue
        coupes = _decoupes(lignes, W)
        stats["colonnes"] = max(stats["colonnes"], len(coupes) + 1)
        ordre = _ordre(lignes, coupes, ip)
        hm = _mediane([_hauteur(li) for li in lignes if _hauteur(li) > 0])
        pas = [b["y0"] - a["y0"] for (a, ka), (b, kb) in zip(ordre, ordre[1:]) if ka == kb and b["y0"] > a["y0"]]
        pas_med = _mediane(pas)
        ref = min(pas_med, 1.5 * hm) if (pas and hm > 0) else (pas_med or 1.2 * hm)
        seuil = 1.5 * ref if ref > 0 else math.inf
        retrait = max(0.8 * hm, 0.02 * W)
        par_cle: dict[tuple, list] = {}
        for li, k in ordre:
            par_cle.setdefault(k, []).append(li)
        bords = {k: (_quantile([x["x0"] for x in ls], 0.25), _quantile([x["x1"] for x in ls], 0.75))
                 for k, ls in par_cle.items()}
        for li, k in ordre:
            flux.append({"li": li, "cle": k, "seuil": seuil, "retrait": retrait,
                         "gauche": bords[k][0], "droite": bords[k][1]})
    stats["lignes"] = len(flux)

    def fin_phrase(e):
        return e["li"]["mots"][-1]["t"].endswith(FIN_PHRASE)

    def courte(e):
        w = e["droite"] - e["gauche"]
        return w > 0 and e["li"]["x1"] < e["droite"] - SEUIL_COURTE * w

    def rupture(a, b) -> bool:
        if a["cle"] == b["cle"]:
            if b["li"]["y0"] - a["li"]["y0"] > a["seuil"]:
                return True
        elif a["cle"][2] == -1 or b["cle"][2] == -1:
            return True
        if fin_phrase(a) and (courte(a) or b["li"]["x0"] - b["gauche"] > b["retrait"]):
            return True
        return False

    paragraphes, cur, prec = [], None, None
    for e in flux:
        mots = [dict(m) for m in e["li"]["mots"]]
        if cur is None:
            cur = mots
        elif rupture(prec, e):
            paragraphes.append(cur); cur = mots
        else:
            colle = _coller(cur[-1]["t"], mots[0]["t"], lg)
            if colle is not None:
                cur[-1] = {"t": colle, "ctx": cur[-1]["ctx"] or mots[0]["ctx"]}
                cur.extend(mots[1:])
                stats["cesures"] += 1
            else:
                cur.extend(mots)
        prec = e
    if cur:
        paragraphes.append(cur)

    morceaux, incertains, n = [], [], 0
    for i, para in enumerate(paragraphes):
        if i:
            morceaux.append("\n\n"); n += 2
        for j, m in enumerate(para):
            if j:
                morceaux.append(" "); n += 1
            t = m["t"]
            if m["ctx"] or incertain(t):
                d, f = _coeur(t)
                if d >= f:
                    d, f = 0, len(t)
                incertains.append({"debut": n + d, "fin": n + f})
            morceaux.append(t); n += len(t)
            stats["mots"] += 1
    stats["incertains"] = len(incertains)
    return {"texte": "".join(morceaux), "incertains": incertains, "stats": stats, "langue": lg}


def nettoyer(pages: list[dict], *, langue: str = "fr", autre: list[dict] | None = None) -> dict:
    """Pages lues -> {texte, incertains, stats, langue}. `autre` = la passe de l'autre langue (mode auto) : la passe
    au moins de mots incertains est gardée (égalité -> fr), et les mots que les deux passes lisent autrement sont
    marqués incertains."""
    pages = [p if isinstance(p, dict) else {} for p in (pages or [])]
    if not autre:
        return _nettoyer(pages, langue, None)
    autre = [p if isinstance(p, dict) else {} for p in autre]
    a, b = _nettoyer(pages, langue, None), _nettoyer(autre, langue, None)
    na, nb = a["stats"]["incertains"], b["stats"]["incertains"]
    if nb < na or (nb == na and b["langue"] == "fr" and a["langue"] != "fr"):
        pages, autre = autre, pages
    return _nettoyer(pages, langue, autre)
