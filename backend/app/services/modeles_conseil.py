# -*- coding: utf-8 -*-
"""t492 (lot F5 « Fiches modèle », 10/11/2026) — conseiller un modèle et relire un prompt, SANS LLM et sans réseau.

Deux fonctions pures, servies aux agents par la boîte « modeles » (outils `recommander_modele`, `verifier_prompt`) :

- `recommander(nature, consigne, contraintes)` : classe les membres d'une nature d'appel. D'abord les FILTRES durs lus au
  catalogue (durée, format, image de fin, références, fond transparent, retouche, paroles, texte vers 3D, pose de rig,
  format d'export, clé posée, budget) ; puis la PERTINENCE (mots de la consigne trouvés dans la description de la fiche
  de la famille et dans ses puces [CHOIX]) ; puis le COÛT estimé. Rend un premier choix, une ALTERNATIVE chez un autre
  fournisseur (une famille de fiche différente : une même famille partage son filtre de modération) et un conseil de
  BROUILLON (palier bas, résolution basse, membre moins cher de la même famille, brouillon sans texture).
- `verifier_prompt(id, prompt)` : relecture par motifs — format écrit en prose, « no music », négatifs en clair,
  prix ou mention légale, balises de voix, paramètres d'un autre outil (« --ar »), liste de mots-clés, longueur au-delà
  du plafond du membre, fond transparent demandé à un modèle qui ne le rend pas.

Le texte des fiches est une DONNÉE : on n'en tire que des mots et des puces citées, jamais une consigne.
"""
from __future__ import annotations

import math
import re
import unicodedata

from app.services import catalogue_ia as C, modeles_fiches as MF

# Plafonds de prompt connus hors registre, datés. Les autres viennent des registres (musique, effets, voix).
# h3-max : 2000 caractères (schéma fal relu le 09/11/2026, relevé de la conception §3).
PROMPT_MAX_VIDEO = {"h3-max": 2000}

_NATURES_VIDEO = ("video_i2v", "video_fl")
_UNITAIRES = {"image", "gen", "piste", "son", "video", "requete", "effet", "mp"}
_VIDES = {"avec", "pour", "dans", "plus", "sans", "une", "des", "les", "que", "qui", "the", "and", "with", "for",
          "from", "this", "that", "pas", "est", "sur", "par", "veux", "faire", "faut", "image", "video", "modele", "model"}


def _plat(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _mots(s: str) -> set[str]:
    """Les mots porteurs, RACINES (6 premières lettres) : « typographie » et « typographique », « poses » et « pose »
    se rejoignent. Les ids et numéros (« 16:9 », « v3 ») restent entiers."""
    out = set()
    for m in re.findall(r"[a-z0-9][a-z0-9.\-]+", _plat(s)):
        m = m.rstrip(".-")
        # deux lettres : seulement une version (« v3 », « 4k ») ; sinon trois au moins
        if m in _VIDES or len(m) < 2 or (len(m) < 3 and not re.search(r"\d", m)):
            continue
        if m.isalpha() and len(m) > 4 and m[-1] in "sx":     # pluriel : « poses », « travaux »
            m = m[:-1]
        out.add(m[:6] if m.isalpha() else m)
    return out


# ---- contraintes -----------------------------------------------------------------------------------------------------
_NOMBRES = {"duree": float, "refs": int, "vues": int, "budget_usd": float, "caracteres": int, "n": int}
_BOOLEENS = ("image_fin", "seed", "negatif", "retouche", "transparent", "vecteur", "paroles", "garder_voix",
             "depuis_texte", "pose_rig", "balises", "cles_posees")
_TEXTES = ("ratio", "format_export", "qualite")
CONTRAINTES = tuple(_NOMBRES) + _BOOLEENS + _TEXTES
_BAS_PRIX = re.compile(r"\b(?:brouillons?|drafts?|pas chers?|peu chers?|cheap(?:er)?|essais?|maquettes?)\b", re.I)


def normaliser(contraintes: dict | None) -> tuple[dict, list[str]]:
    """Les contraintes connues, typées ; les clés inconnues sont rendues à part (`ignorees`). ValueError nommée sur
    un nombre illisible ou négatif."""
    c, ignorees = {}, []
    for k, v in (contraintes or {}).items():
        if v in (None, ""):
            continue
        if k in _NOMBRES:
            try:
                x = _NOMBRES[k](float(v)) if _NOMBRES[k] is int else float(v)
            except (TypeError, ValueError):
                raise ValueError(f"contrainte « {k} » : un nombre est attendu, pas « {v} »")
            if x < 0 or (k in ("n", "duree", "caracteres", "vues") and x == 0):
                raise ValueError(f"contrainte « {k} » : valeur positive attendue")
            c[k] = x
        elif k in _BOOLEENS:
            c[k] = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "oui", "yes")
        elif k in _TEXTES:
            c[k] = str(v)[:20].lower() if k != "ratio" else str(v)[:10]
        else:
            ignorees.append(str(k)[:40])
    return c, ignorees


# ---- coût ------------------------------------------------------------------------------------------------------------
def cout(m: dict, c: dict) -> float | None:
    """Le coût estimé d'UN tir de `m` sous les contraintes `c` (duree s, caracteres, n). None = prix à mesurer."""
    usd = float(m.get("usd") or 0.0)
    q = m.get("qualites")
    if c.get("qualite") and isinstance(q, dict):
        bas = c["qualite"] == "bas"
        cle = min(q, key=lambda k: float(q[k] or 0)) if bas else c["qualite"]
        if q.get(cle):
            usd = float(q[cle])
    if not usd:
        return 0.0 if m.get("voie") == "local" else None
    n = max(1, int(c.get("n") or 1))
    u = m.get("unite") or ""
    d = c.get("duree")
    if u == "s":
        if d is None:
            ds = m.get("durations") or (m.get("duree") or [None])
            d = min(ds) if ds and ds[0] is not None else 1
        return round(usd * float(d) * n, 4)
    if u == "min":
        return round(usd * max(1, math.ceil(float(d or 60) / 60.0)) * n, 4)
    if u == "1k_car":
        return round(usd * max(1, int(c.get("caracteres") or 1000)) / 1000.0, 4)
    return round(usd * n, 4)


# ---- filtres durs ----------------------------------------------------------------------------------------------------
def ecart(m: dict, c: dict) -> str | None:
    """La raison pour laquelle `m` ne tient PAS les contraintes, ou None."""
    nat = set(m.get("natures") or [m.get("nature")])
    if c.get("cles_posees") and not m.get("dispo"):
        return f"clé {m.get('cle')} absente"
    d = c.get("duree")
    if d is not None:
        if nat & set(_NATURES_VIDEO) and m.get("durations") and int(round(float(d))) not in m["durations"]:
            ds = m["durations"]
            suite = ds == list(range(ds[0], ds[-1] + 1))
            return f"durée {d:g} s non permise ({f'{ds[0]}–{ds[-1]} s' if suite else ', '.join(map(str, ds)) + ' s'})"
        if "musique" in nat and not m.get("duree"):
            return "durée choisie par le modèle (non réglable)"
        plage = m.get("video_s") or m.get("duree")
        if not nat & set(_NATURES_VIDEO) and plage and not (float(plage[0]) <= float(d) <= float(plage[-1])):
            return f"durée {d:g} s hors de {plage[0]:g}–{plage[-1]:g} s"
    if c.get("ratio") and m.get("ratios") and c["ratio"] not in m["ratios"]:
        return f"format {c['ratio']} absent ({', '.join(m['ratios'])})"
    if c.get("image_fin") and nat & set(_NATURES_VIDEO) and not m.get("end_image"):
        return "pas d'image de fin"
    if c.get("seed") and nat & set(_NATURES_VIDEO) and not m.get("seed"):
        return "pas de seed"
    if c.get("negatif") and nat & set(_NATURES_VIDEO) and not m.get("negatif"):
        return "pas de champ négatif"
    refs = int(c.get("refs") or 0)
    if refs and "image" in nat:
        if not m.get("edit"):
            return "ne retouche pas (aucune image d'entrée)"
        if m.get("refs_max") is not None and refs > int(m["refs_max"]):
            return f"{refs} références > {m['refs_max']}"
    if c.get("retouche") and "image" in nat and not m.get("edit"):
        return "ne retouche pas"
    if c.get("transparent") and "image" in nat and not m.get("transparent"):
        return "pas de vrai fond transparent (détourer ensuite)"
    if "image" in nat and bool(c.get("vecteur")) != (m.get("sortie") == "svg"):
        return "sortie SVG" if m.get("sortie") == "svg" else "sortie raster, pas SVG"
    if c.get("paroles") and "musique" in nat and not m.get("paroles"):
        return "pas de paroles"
    if c.get("garder_voix") and "sfx_video" in nat and not m.get("voix"):
        return "ne garde pas la voix du clip"
    if "modele3d" in nat:
        if c.get("depuis_texte") and not m.get("texte"):
            return "ne part pas d'un texte"
        if c.get("pose_rig") and not m.get("tpose"):
            return "ne demande pas de pose de rig"
        if c.get("format_export") and c["format_export"] not in (m.get("formats") or []):
            return f"pas d'export {c['format_export']}"
        if c.get("vues") and int(c["vues"]) > int(m.get("vues") or 1):
            return f"{c['vues']} vues > {m.get('vues') or 1}"
    if c.get("balises") and "voix" in nat and not m.get("balises"):
        return "ne lit pas les balises d'émotion"
    if c.get("budget_usd") is not None:
        k = cout(m, c)
        if k is not None and k > float(c["budget_usd"]):
            return f"coût estimé {k:g} $ > budget {float(c['budget_usd']):g} $"
    return None


# ---- pertinence ------------------------------------------------------------------------------------------------------
def _choix(corps: str) -> list[str]:
    out, cur = [], None
    for l in corps.splitlines():
        if l.startswith("- ["):
            cur = l[2:] if re.match(r"- \[(CHOIX|CHOICE)\]", l) else None
            if cur is not None:
                out.append(cur)
        elif cur is not None and l.startswith("  "):
            out[-1] += " " + l.strip()
        else:
            cur = None
    return out


_PAS_ENCORE = re.compile(r"Pas encore dans l'app|Not in the app yet", re.I)


def _fiches(langue: str) -> dict:
    fr, en = MF.charger("fr"), MF.charger("en")
    out = {}
    for fam, v in fr.items():
        if fam == MF.COMMUN:
            continue
        txt = v["meta"].get("description", "") + " " + (en.get(fam, {}).get("meta", {}).get("description", ""))
        corps = (en if langue == "en" and fam in en else fr)[fam]["corps"]
        ch = _choix(corps)
        mc = set()
        for x in _choix(fr[fam]["corps"]) + (_choix(en[fam]["corps"]) if fam in en else []):
            mc |= _mots(x)
        out[fam] = {"mots": _mots(txt), "mots_choix": mc - _mots(txt), "choix": ch, "ids": v["meta"].get("ids") or []}
    return out


def recommander(nature: str, consigne: str = "", contraintes: dict | None = None, langue: str = "fr") -> dict:
    """Classe les membres de `nature` ; KeyError si la nature est inconnue."""
    c, ignorees = normaliser(contraintes)                       # ValueError -> refus nommé
    entrees = C.lister(nature)                                   # KeyError -> refus de l'outil
    hypotheses = {}
    if not c.get("qualite") and _BAS_PRIX.search(consigne or ""):
        c["qualite"] = "bas"                                      # « brouillon », « pas cher » : devis au palier bas
        hypotheses["qualite"] = "palier le plus bas (consigne : brouillon / pas cher)"
    fiches = _fiches(langue)
    fam_de = {i: f for f, v in fiches.items() for i in v["ids"]}
    ids = [e["id"] for e in entrees]
    enrichis = {m["id"]: m for m in MF.membres({"natures": [nature], "ids": ids})}
    # les mots de prix (« brouillon », « pas cher ») règlent le PALIER du devis, pas la pertinence d'une famille
    mots = _mots(consigne) - _mots(" ".join(x.group(0) for x in _BAS_PRIX.finditer(consigne or "")))
    # un mot présent dans la description de PRESQUE toutes les familles de la nature ne départage rien : poids 1/df
    fams_nat = {fam_de[i] for i in ids if i in fam_de}
    df = {w: max(1, sum(1 for fa in fams_nat if w in fiches[fa]["mots"] | fiches[fa]["mots_choix"])) for w in mots}
    gardes, ecartes = [], []
    nat_video = nature in _NATURES_VIDEO
    for e in entrees:
        m = enrichis.get(e["id"], dict(e, natures=[nature]))
        r = ecart(m, c)
        if r:
            ecartes.append({"id": m["id"], "raison": r})
            continue
        fam = fam_de.get(m["id"])
        f = fiches.get(fam) or {"mots": set(), "mots_choix": set(), "choix": []}
        lab = _mots(m.get("label", "") + " " + m["id"])
        trouves = sorted(mots & f["mots"])
        # les puces [CHOIX] et le nom du membre comptent pour moitié
        dans_choix = sorted((mots & (f["mots_choix"] | lab)) - set(trouves))
        raisons = [ch for ch in f["choix"] if mots & _mots(ch) and not _PAS_ENCORE.search(ch)]
        # une puce [CHOIX] qui répond à la consigne ET nomme ce membre (« Cheveux, fourrure : BiRefNet v2 ») le
        # départage de ses frères de famille
        nom = _mots(re.split(r"[·(—–,]", m.get("label") or "")[0]) - _mots(fam or "")
        nomme = [ch for ch in raisons if nom and any(mots & _mots(p) and nom <= _mots(p)
                                                     for p in re.split(r"(?<=[.;])\s+", ch))]
        raisons = (nomme + [ch for ch in raisons if ch not in nomme])[:3]
        k = cout(m, c)
        # ADÉQUATION : une contrainte tenue par un CHAMP du membre (format listé, image de fin, seed, négatif) vaut
        # plus qu'un mot de la consigne ; un format demandé à un membre sans champ format suit l'image de départ
        adequation = sum(0.75 for ok in (
            c.get("ratio") and m.get("ratios") and c["ratio"] in m["ratios"],
            c.get("image_fin") and m.get("end_image"), c.get("seed") and m.get("seed"),
            c.get("negatif") and m.get("negatif")) if ok)
        avert = []
        if c.get("ratio") and nat_video and not m.get("ratios"):
            avert.append("pas de champ format : le cadre suit l'image de départ (la préparer au format voulu)")
        if k is None:
            avert.append("prix à mesurer : chiffré à zéro au devis, le plafond ne le freine pas ; essayer une fois")
        gardes.append({"id": m["id"], "label": m.get("label"), "famille": fam, "voie": m.get("voie"),
                       "dispo": bool(m.get("dispo")), "cle": m.get("cle"), "cout_estime": k,
                       "prix_a_mesurer": k is None, "unite": m.get("unite"), "usd": m.get("usd"),
                       "score": round(sum(1.0 / df.get(w, 1) for w in trouves) + sum(0.5 / df.get(w, 1) for w in dans_choix)
                                      + (0.25 if m.get("defaut") else 0) + (1.0 if nomme else 0) + adequation, 3),
                       "adequation": adequation, "avertissements": avert,
                       "mots": trouves + dans_choix,
                       "raisons": raisons, "_m": m})
    # pertinence d'abord, puis disponibilité, puis prix connu croissant ; un prix à mesurer est rangé APRÈS les
    # prix connus à score égal (on ne recommande pas d'emblée un tir non chiffré : l'avertissement le dit)
    gardes.sort(key=lambda g: (-g["score"], not g["dispo"], g["cout_estime"] is None,
                               g["cout_estime"] if g["cout_estime"] is not None else 0.0))
    premier = gardes[0] if gardes else None
    alternative = next((g for g in gardes[1:] if premier and g["famille"] != premier["famille"]), None)
    brouillon = _brouillon(premier, gardes, c) if premier else None
    pub = lambda g: None if g is None else {k: v for k, v in g.items() if k != "_m"}   # noqa: E731
    if alternative is not None:
        alternative = dict(alternative, role="repli chez un autre fournisseur (modération, panne) : même prompt "
                                             "adapté à sa fiche")
    if c.get("duree") is None and nature in _NATURES_VIDEO + ("sfx_texte", "sfx_video", "musique"):
        hypotheses["duree"] = "la plus courte du membre (aucune durée donnée)"
    if nature == "voix" and not c.get("caracteres"):
        hypotheses["caracteres"] = 1000
    return {"nature": nature, "contraintes": c, "ignorees": ignorees, "hypotheses": hypotheses,
            "premier": pub(premier), "alternative": pub(alternative), "brouillon": brouillon,
            "classement": [pub(g) for g in gardes], "ecartes": ecartes, "total": len(entrees)}


def _brouillon(p: dict, gardes: list[dict], c: dict) -> dict | None:
    m = p["_m"]
    q = m.get("qualites")
    if isinstance(q, dict) and len(q) > 1:
        bas = min(q, key=lambda k: float(q[k] or 0))
        if float(q[bas] or 0) < float(q.get(m.get("qualite_defaut") or "high", max(q.values())) or 0):
            return {"id": p["id"], "reglage": {"qualite": bas}, "usd_unite": q[bas],
                    "conseil": f"brouillon au palier « {bas} », puis le final au palier voulu (même prompt : sans "
                               f"seed, c'est un nouveau tirage)"}
    r = m.get("resolutions")
    if isinstance(r, dict) and len(r) > 1:
        bas = min(r, key=lambda k: float(r[k] or 0))
        return {"id": p["id"], "reglage": {"resolution": bas}, "usd_unite": r[bas],
                "conseil": f"brouillon en {bas}, final à la résolution voulue"}
    if m.get("brouillon"):
        return {"id": p["id"], "reglage": {"texture": False},
                "conseil": "brouillon sans texture pour juger la forme, puis le tir texturé"}
    moins = [g for g in gardes if g["famille"] == p["famille"] and g["id"] != p["id"] and g["cout_estime"] is not None
             and p["cout_estime"] is not None and g["cout_estime"] < p["cout_estime"]]
    if moins:
        g = min(moins, key=lambda g: g["cout_estime"])
        return {"id": g["id"], "reglage": {}, "cout_estime": g["cout_estime"],
                "conseil": f"brouillon sur {g['label']} (même famille, moins cher), à la durée et au format finaux ; "
                           f"le final sur {p['label']}"}
    return None


# ---- relecture d'un prompt -------------------------------------------------------------------------------------------
_RX_FORMAT = re.compile(r"\b(?:\d{1,2}\s?[:/x]\s?\d{1,2}\b(?!\s?(?:am|pm|h))|aspect ratio|widescreen|(?:format|cadre)\s+"
                        r"(?:vertical|horizontal|portrait|paysage|carre|carré)|vertical (?:video|format)|"
                        r"portrait orientation|landscape orientation|square (?:format|frame|aspect))", re.I)
_RX_SANS_SON = re.compile(r"\b(?:no|without)\s+(?:music|sound|audio|sfx|soundtrack)\b|\bsans\s+(?:musique|son)\b", re.I)
_RX_NEGATIF = re.compile(r"\b(?:no|without|avoid|don't|do not|never)\s+[a-z][\w-]*|\b(?:sans|pas de|aucun|aucune)\s+\w+",
                         re.I)
_NEGATIFS_PERMIS = re.compile(r"\bno (?:other|extra) (?:text|words)\b|\bno duplicate text\b|\bno letterboxing\b|"
                              r"\bno (?:lettering|text|words)\b", re.I)
_RX_PRIX = re.compile(r"[$€£]\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|\$|eur(?:os?)?\b|dollars?\b|usd\b)|[©®™]|\b(?:terms and conditions|"
                      r"conditions g[ée]n[ée]rales|mentions? l[ée]gales?|offre valable|valid until)|[-−]\s?\d{1,2}\s?%|\d{1,2}\s?%\s?off\b",
                      re.I)
_RX_CLI = re.compile(r"(?:^|\s)--(?:ar|v|q|s|style|stylize|seed|no|chaos|niji|weird|tile)\b", re.I)
_RX_CROCHET = re.compile(r"\[[^\[\]\n]{1,40}\]")


def _entree(mid: str) -> dict | None:
    for n in C.natures():
        for e in C.lister(n):
            if e["id"] == mid:
                return (MF.membres({"natures": [n], "ids": [mid]}) or [dict(e, natures=[n])])[0]
    return None


def _limite(m: dict) -> int | None:
    nat = set(m.get("natures") or [])
    if m["id"] in PROMPT_MAX_VIDEO:
        return PROMPT_MAX_VIDEO[m["id"]]
    if "voix" in nat:
        return m.get("car_max")
    if "musique" in nat:
        from app.services import music_service as MS
        e = MS.MUSIC_MODELS.get(m["id"]) or {}
        return int(e.get("prompt_max") or MS._MAX_PROMPT)
    if nat & {"sfx_texte", "sfx_video"}:
        from app.services import sfx_service as SX
        e = SX.SFX_MODELS.get(m["id"]) or {}
        return int(e["prompt_max"]) if e.get("prompt_max") else None
    return None


def verifier_prompt(mid: str, prompt: str) -> dict:
    """Relit `prompt` pour le modèle `mid`. KeyError si l'id est inconnu."""
    m = _entree(str(mid or ""))
    if m is None:
        raise KeyError(mid)
    p = str(prompt or "")
    nat = set(m.get("natures") or [])
    visuel = bool(nat & {"image", "video_i2v", "video_fl"})
    sonore = bool(nat & {"video_i2v", "video_fl", "musique", "sfx_texte", "sfx_video"})
    out: list[dict] = []

    def dire(code, gravite, message, extrait=""):
        out.append({"code": code, "gravite": gravite, "message": message, "extrait": str(extrait)[:80]})

    if "voix" in nat:
        from app.services import voice_direction as VD
        tags = [x for x in VD.find_tags(p) if VD.is_known(x)]
        if tags and not m.get("balises"):
            dire("balises_retirees", "info", "ces balises seront RETIRÉES avant l'envoi (seul Eleven v3 les lit) ; "
                 "un crochet hors palette part tel quel et sera lu", ", ".join(tags))
        inconnues = VD.unknown_tags(p)
        if inconnues:
            dire("balise_hors_palette", "erreur", "crochet hors palette : il part tel quel et sera lu à voix haute",
                 ", ".join(inconnues))
        lue = re.search(r"\((?:[^()]{0,30}\b(?:say|says|speak|tone|voice|read|dire|dis|ton|voix|lire|lis)\b[^()]{0,30}|"
                        r"\s*(?:angry|angrily|sad|sadly|happy|happily|whisper\w*|excited|en col[eè]re|triste|joyeu\w*|"
                        r"chuchot\w*)\s*)\)", p, re.I)
        if lue:
            dire("consigne_lue", "avertissement", "une consigne de ton écrite dans le script est LUE : passer par une "
                 "balise (v3) ou les réglages", lue.group(0))
    else:
        f = _RX_FORMAT.search(p)
        if f and (visuel or "modele3d" in nat):
            sans_champ = bool(nat & set(_NATURES_VIDEO)) and not m.get("ratios")
            dire("format_en_prose", "avertissement", ("ce membre n'a pas de champ format : le cadre suit l'image de "
                 "départ, à préparer au format voulu ; écrit en prose, il ne fait rien de bon") if sans_champ else
                 ("le format se règle dans son champ, pas dans le texte : écrit en prose, il donne des bandes noires "
                  "ou un recadrage"), f.group(0))
        s = _RX_SANS_SON.search(p)
        if s and sonore:
            dire("sans_son_ecrit", "avertissement", "« no music » écrit fait souvent refuser la piste ou fait entendre "
                 "ce qu'il nomme : couper le son par l'interrupteur du membre, ou nommer les sons voulus", s.group(0))
        negs = [x.group(0) for x in _RX_NEGATIF.finditer(p)
                if not _NEGATIFS_PERMIS.match(p[x.start():]) and not _RX_SANS_SON.match(p[x.start():])]
        if negs and (visuel or sonore):
            ou = ("le membre a un champ négatif : y mettre ces mots" if m.get("negatif")
                  else "le membre n'a pas de champ négatif : formuler en positif (ce qu'on veut voir)")
            dire("negatif_en_clair", "info", "un mot écrit dessine ce qu'il nomme ; " + ou, ", ".join(negs[:4]))
        pr = _RX_PRIX.search(p)
        if pr and visuel:
            dire("prix_ou_mention", "erreur", "un prix, un numéro ou une mention légale généré peut sortir faux : "
                 "l'incruster ensuite (Templates, Montage, Card Forge)", pr.group(0))
        cli = _RX_CLI.search(p)
        if cli:
            dire("parametre_autre_outil", "avertissement", "paramètre d'un autre outil : il n'est pas lu comme réglage "
                 "et peut apparaître dans l'image ; utiliser les champs de l'app", cli.group(0).strip())
        cr = _RX_CROCHET.search(p)
        if cr and visuel:
            dire("crochets", "info", "un crochet n'est pas un champ à remplir : il est lu, voire dessiné", cr.group(0))
        segs = [s.strip() for s in re.split(r"[,;\n]", p) if s.strip()]
        if visuel and len(segs) >= 8 and sum(len(s.split()) <= 3 for s in segs) >= 0.7 * len(segs):
            dire("mots_cles", "avertissement", "liste de mots-clés : écrire des phrases (sujet, action, décor, "
                 "lumière, style)", ", ".join(segs[:5]))
        if "image" in nat:
            from app.services import image_providers as IP
            if IP.fond_transparent_demande(p) and not IP.accepte_transparent(m["id"]):
                dire("transparent_non_servi", "avertissement", "ce modèle ne rend pas de vrai fond transparent : "
                     "l'image sortira opaque ; demander un fond uni puis détourer, ou prendre un membre qui le rend")
    requis = bool(m.get("prompt")) if nat & {"detourage_image", "detourage_video", "sfx_texte", "sfx_video"} else False
    if requis and not p.strip():
        dire("description_requise", "erreur", "ce membre exige une description (sujet nommé, sons) : refusé avant "
             "toute dépense sans elle")
    if nat & {"detourage_image", "detourage_video"} and "prompt" in m and not m.get("prompt") and p.strip():
        dire("description_ignoree", "info", "ce membre ne prend aucune description : elle sera ignorée")
    lim = _limite(m)
    if lim and len(p) > lim:
        if "voix" in nat:
            dire("trop_long", "info", f"{len(p)} caractères > {lim} par requête : le texte sera découpé aux fins de "
                 f"phrase, puis recollé")
        else:
            dire("trop_long", "erreur", f"{len(p)} caractères > {lim} : le texte serait coupé ou refusé")
    fam = MF.famille_de(m["id"])
    return {"id": m["id"], "famille": fam, "natures": sorted(nat), "longueur": len(p), "limite": lim,
            "constats": out, "ok": not any(x["gravite"] == "erreur" for x in out)}
