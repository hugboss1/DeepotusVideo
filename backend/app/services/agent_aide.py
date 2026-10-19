# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md, 19/10/2026).

La connaissance vit dans docs/agent/ (AGENT.md écrit à la main, ancres.json) et docs/guide/src/ (chapitres.json,
jeveux.json). Ce module l'assemble en message système, appelle UN moteur de texte sous le plafond « aide », puis
transforme les balises de la réponse en actions pour l'écran. Il n'exécute RIEN de payant pour l'utilisateur.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

from loguru import logger

RACINE = Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "docs" / "agent"
GUIDE = RACINE / "docs" / "guide" / "src"
# les vues du rail de la SPA, dans l'ordre du rail
VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings")
# les sections des Réglages que l'écran sait ouvrir (`dzReglagesEcoute` du bundle ; settings_routes._RUBRIQUES en a une
# de plus, « transfert », que l'écran n'ouvre pas par section)
SECTIONS_REGLAGES = ("diag", "coffre", "appareils", "keys", "accounts", "personas", "branding", "pack", "defaults",
                     "paths", "news", "appearance", "pricing", "espaces")

MAX_QUESTION = 2000
MAX_HISTORIQUE = 10
MAX_TOUR = 1000
MAX_TOKENS = 2000   # les moteurs qui raisonnent comptent la réflexion dans la sortie
REPONSE_VIDE = {"fr": "Voici où regarder :", "en": "Here is where to look:"}
SANS_REPONSE = {"fr": "Je n'ai pas de réponse utile ; le guide peut aider.",
                "en": "I have no useful answer; the guide can help."}
PREFERENCE = ("anthropic", "openai", "gemini")
SANS_CLE = {
    "fr": "Aucun moteur de texte n'est branché : l'assistant a besoin d'une clé (Anthropic, OpenAI, Gemini) ou d'un "
          "serveur local. Ouvre les Réglages › Clés d'API, colle ta clé, puis repose ta question.",
    "en": "No text engine is connected: the assistant needs an API key (Anthropic, OpenAI, Gemini) or a local "
          "server. Open Settings › API keys, paste your key, then ask again.",
}

# A5 : la vision en secours. La consigne voyage dans la QUESTION (le système reste identique d'un appel à l'autre).
COTE_MAX = 1280                 # l'écran réduit la capture à 1 280 px au plus sur son grand côté
VUE_NOMINALE = (1280, 800)      # le devis se calcule sur cette taille : même texte au devis et à l'envoi
MAX_IMAGE_B64 = 6_000_000
EPS_USD = 0.0001                # une unité d'arrondi du devis (4 décimales)
CONSIGNE_VUE = {
    "fr": "Une capture de l'écran visible est jointe ({l}×{h} px). Trouve l'élément qui répond à la question et "
          "termine par [POINT:x,y:libellé] : x et y en pixels DE LA CAPTURE, au centre de l'élément ; libellé = son "
          "nom en 3 mots au plus. Si l'élément n'est pas sur la capture, dis-le, sans balise POINT.",
    "en": "A capture of the visible screen is attached ({l}×{h} px). Find the element that answers the question and "
          "end with [POINT:x,y:label]: x and y in pixels OF THE CAPTURE, at the centre of the element; label = its "
          "name in 3 words at most. If the element is not on the capture, say so, with no POINT tag.",
}


class CoutChange(Exception):
    """Le coût recalculé dépasse le montant accepté par l'utilisateur : rien n'est envoyé (409 sur la route)."""


@lru_cache(maxsize=1)
def connaissance() -> dict:
    """Lue une fois par processus (les fichiers suivent l'installation, jamais l'utilisateur)."""
    ancres = json.loads((DOSSIER / "ancres.json").read_text(encoding="utf-8"))["ancres"]
    chap = json.loads((GUIDE / "chapitres.json").read_text(encoding="utf-8"))["chapitres"]
    jv = json.loads((GUIDE / "jeveux.json").read_text(encoding="utf-8"))["entrees"]
    return {"agent": (DOSSIER / "AGENT.md").read_text(encoding="utf-8"),
            "ancres": {a["id"]: a for a in ancres},
            "chapitres": {c["id"]: c for c in chap},
            "jeveux": jv}


def _ligne(v, n: int = 60) -> str:
    """Une valeur libre (nom d'espace, écran) réduite à UNE ligne bornée avant d'entrer dans le message système."""
    return " ".join(str(v or "").split())[:n]


NON_REDIGE = {"fr": "— pas encore rédigé : décris seulement ce qui est visible",
              "en": "— not written yet: describe only what is visible"}
NON_DOCUMENTE = {"fr": "non documenté", "en": "not documented"}


def _fiche_ligne(x: dict, cle: str, avec_role: bool = True) -> str:
    lib = ((x.get("libelle") or {}).get(cle) or (x.get("infobulle") or {}).get(cle) or x["id"])
    pt = " [pointable]" if x.get("localisateur") else ""
    ou = x.get("ecran") or "partout"
    if not avec_role:
        return f"- {x['id']} « {lib} »{pt}"
    role = (x.get("role") or {}).get(cle) or ""
    return f"- {x['id']} ({ou}) « {lib} »{pt} : {role or NON_REDIGE[cle]}"


def systeme(ecran: str, lang: str, espace: str = "", pertinents=(), visibles=None) -> str:
    """AGENT.md + chapitres + « Je veux… » + ancres + vues, puis « ## Contexte » ; les sections qui changent à chaque
    question (éléments pertinents, écran relevé) viennent APRÈS, pour garder le préfixe identique (cache)."""
    ecran, espace = _ligne(ecran, 30), _ligne(espace)
    k = connaissance()
    en = lang == "en"
    cle = "en" if en else "fr"
    chap = "\n".join(f"- {c['id']} : {c[cle]}" for c in k["chapitres"].values())
    jv = "\n".join(f"- {e[cle]} → {e['cible']}" for e in k["jeveux"])
    anc = "\n".join(f"- {a['id']} ({'partout' if a.get('partout') or not a.get('ecran') else a['ecran']}) : {a[cle]}" for a in k["ancres"].values())
    s = (f"{k['agent']}\n\n## Chapitres (id : titre)\n{chap}\n\n## Je veux…\n{jv}\n\n"
         f"## Ancres (id (écran) : libellé)\n{anc}\n\n## Vues\n{', '.join(VUES)}\n\n"
         f"## Contexte\n- écran ouvert : {ecran or 'inconnu'}\n- espace de marque actif : {espace or 'inconnu'}\n"
         f"- langue : {'English' if en else 'français'}\n")
    if pertinents:
        s += "\n## Éléments pertinents (id (écran) « libellé » : rôle)\n" + "\n".join(
            _fiche_ligne(x, cle) for x in pertinents) + "\n"
    if visibles and (visibles.get("reconnus") or visibles.get("inconnus")):
        lignes = [_fiche_ligne(x, cle, avec_role=False) for x in visibles.get("reconnus", [])]
        lignes += [f"- « {v['t'] or v['i']} »" + (f" ({v['i']})" if v["t"] and v["i"] else "")
                   + f" — {NON_DOCUMENTE[cle]}" for v in visibles.get("inconnus", [])]
        s += "\n## À l'écran maintenant\n" + "\n".join(lignes) + "\n"
    return s


CATALOGUE = DOSSIER / "catalogue"
MAX_PERTINENTS = 15
# bonus mesurés le 19/10 sur le catalogue non rédigé ; à revoir après C2
BONUS_ECRAN = 2.0       # multiplicateur pour l'écran ouvert
BONUS_VISIBLE = 6.0     # ajout pour un élément visible maintenant
POIDS = (("libelle", 3.0), ("synonymes", 3.0), ("infobulle", 2.0), ("role", 1.0))
MOTS_VIDES = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "en", "au", "aux", "je", "tu", "il",
              "ce", "ca", "est", "pour", "par", "sur", "dans", "avec", "comment", "quoi", "que", "qui", "mon",
              "ma", "mes", "the", "an", "of", "to", "in", "on", "is", "how", "do", "i", "my", "what", "where"}


@lru_cache(maxsize=1)
def catalogue() -> dict:
    """Les fiches non retirées de docs/agent/catalogue/*.json (lues une fois par processus)."""
    fiches = {}
    if CATALOGUE.is_dir():
        for f in sorted(CATALOGUE.glob("*.json")):
            if f.name.startswith("_"):
                continue
            for x in json.loads(f.read_text(encoding="utf-8"))["fiches"]:
                if x.get("etat") != "retire":
                    fiches[x["id"]] = x
    return fiches


def _mots(t) -> list:
    t = re.sub(r"\{[^{}]*\}", " ", str(t or ""))                 # les gabarits {k}, {piste}… ne sont pas des mots
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return [m for m in re.findall(r"[a-z0-9]+", t) if len(m) >= 2 and m not in MOTS_VIDES]


def _racine(m: str) -> str:
    return m[:5] if len(m) > 5 else m           # « coupe », « couper », « coupez » se rejoignent


@lru_cache(maxsize=1)
def _index() -> tuple:
    docs, df = {}, Counter()
    for i, x in catalogue().items():
        poids = {}
        for champ, w in POIDS:
            v = x.get(champ) or {}
            for lang in ("fr", "en"):
                t = v.get(lang) if isinstance(v, dict) else None
                t = " ".join(t) if isinstance(t, list) else (t or "")
                for m in _mots(t):
                    r = _racine(m)
                    poids[r] = max(poids.get(r, 0.0), w)
        docs[i] = poids
        df.update(poids.keys())
    n = max(1, len(docs))
    return docs, {r: math.log(1 + n / c) for r, c in df.items()}


def chercher(question, ecran: str = "", visibles=(), n: int = MAX_PERTINENTS) -> list:
    """Les fiches les plus proches de la question : mots communs pondérés par champ et par rareté, ×BONUS_ECRAN
    sur l'écran ouvert, +BONUS_VISIBLE pour un élément visible maintenant. [] si la question n'a aucun mot utile."""
    q = {_racine(m) for m in _mots(question)}
    if not q:
        return []
    docs, idf = _index()
    fiches, vis, res = catalogue(), set(visibles or ()), []
    for i, poids in docs.items():
        s = sum(poids[r] * idf.get(r, 0.0) for r in q if r in poids)
        if not s:
            continue
        if ecran and fiches[i].get("ecran") == ecran:
            s *= BONUS_ECRAN
        if i in vis:
            s += BONUS_VISIBLE
        res.append((-s, i))
    return [fiches[i] for _, i in sorted(res)[:n]]


@lru_cache(maxsize=1)
def _par_texte() -> dict:
    """Provisoire : rempli à la tâche 9."""
    return {}


# toute balise MAJUSCULE entre crochets, avec ou sans cible : les connues deviennent des actions, les autres sont
# retirées (comptées) — l'écran ne voit jamais une balise
BALISE = re.compile(r"\[([A-Z]{2,8})(?::([^\[\]\n]{1,80}))?\]")
MAX_ACTIONS = 6
# A5 : coordonnées rendues par un moteur qui a VU une capture (pixels de la capture), libellé facultatif
XY = re.compile(r"^(\d{1,5})\s*,\s*(\d{1,5})\s*(?::(.*))?$")


def _sans_controle(t: str) -> str:
    """Sans caractères de contrôle ni de format Unicode (catégories C* : U+202E, zéro-largeur…) : le libellé s'affiche."""
    return "".join(" " if c.isspace() else c for c in t if c.isspace() or not unicodedata.category(c).startswith("C"))


def _action(typ: str, cible: str, image: dict | None = None) -> dict | None:
    """image : {largeur, hauteur} de la capture jointe à l'appel (A5) — seule une réponse à une capture peut rendre des
    coordonnées, et jamais une nouvelle demande de capture."""
    k = connaissance()
    if typ == "POINT" and cible in k["ancres"]:
        a = k["ancres"][cible]
        return {"type": "point", "cible": cible, "ecran": a.get("ecran"), "selecteur": a.get("selecteur"),
                "texte": a.get("texte"), "cadre": a.get("cadre"), "reglages": a.get("reglages"),
                "partout": bool(a.get("partout")), "libelle": a.get("libelle"),
                "fr": a["fr"], "en": a["en"]}
    if typ == "POINT" and cible in catalogue() and catalogue()[cible].get("localisateur"):
        x = catalogue()[cible]
        loc = x["localisateur"]
        lib = x.get("libelle") or {}
        tip = x.get("infobulle") or {}
        return {"type": "point", "cible": cible, "ecran": None if x.get("ecran") == "commun" else x.get("ecran"),
                "selecteur": loc.get("selecteur"), "texte": loc.get("texte"), "cadre": x.get("cadre") or loc.get("cadre"),
                "reglages": loc.get("reglages"), "partout": bool(loc.get("partout") or x.get("ecran") == "commun"),
                "libelle": loc.get("libelle"), "fr": lib.get("fr") or tip.get("fr") or cible,
                "en": lib.get("en") or tip.get("en") or cible}
    if typ == "POINT" and image:
        m = XY.match(cible)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            if x < image["largeur"] and y < image["hauteur"]:
                return {"type": "point_xy", "cible": f"{x},{y}", "x": x, "y": y, "largeur": image["largeur"],
                        "hauteur": image["hauteur"], "libelle": _ligne(_sans_controle(m.group(3) or ""), 60)}
        return None
    if typ == "VOIR" and not cible and not image:
        return {"type": "voir", "cible": "ecran"}
    if typ == "ALLER" and cible in VUES:
        return {"type": "aller", "cible": cible}
    if typ == "GUIDE" and cible in k["chapitres"]:
        c = k["chapitres"][cible]
        return {"type": "guide", "cible": cible, "fr": c["fr"], "en": c["en"]}
    return None


def analyser(texte, image: dict | None = None) -> tuple[str, list, int]:
    """(texte sans balises ni indentation, actions dédoublonnées ≤ MAX_ACTIONS, nombre de balises rejetées).
    image : {largeur, hauteur} quand la réponse vient d'un appel avec capture (A5)."""
    actions, vus, rejets = [], set(), 0

    def remplacer(m):
        nonlocal rejets
        a = _action(m.group(1), (m.group(2) or "").strip(), image)
        if a is None:
            rejets += 1
        elif (a["type"], a["cible"]) not in vus and len(actions) < MAX_ACTIONS:
            vus.add((a["type"], a["cible"]))
            actions.append(a)
        return ""

    propre = BALISE.sub(remplacer, str(texte or ""))
    # linéaire (« [ \t]+\n » en re.sub est quadratique) ; retire aussi l'indentation qu'un modèle recopie, et les \r
    propre = "\n".join(l.strip() for l in propre.split("\n"))
    propre = re.sub(r"\n{3,}", "\n\n", propre).strip()
    return propre, actions, rejets


def choisir_moteur(demande: str = "") -> str:
    """Le moteur demandé s'il est connu ET configuré ; sans demande, le premier configuré dans PREFERENCE, puis le
    premier configuré tout court ; "" si aucun. Jamais de repli d'un moteur demandé vers un autre."""
    from app.services import moteurs_texte as MT
    if demande:
        return demande if MT.connu(demande) and MT.configure(demande) and not MT.modele_fautif(demande) else ""
    lignes = [l["moteur"] for l in MT.etat() if l["configure"] and not l.get("fautif")]
    for p in PREFERENCE:
        if p in lignes:
            return p
    return lignes[0] if lignes else ""


def _espace() -> str:
    try:
        from app.services import espaces as ES
        return str(ES.actif().get("nom") or "")
    except Exception:  # noqa: BLE001 — l'espace n'est qu'un contexte : son absence ne bloque pas l'aide
        return ""


def _historique(h) -> str:
    if not isinstance(h, list):
        return ""
    lignes = []
    for t in h[-MAX_HISTORIQUE:]:
        if isinstance(t, dict) and t.get("role") in ("user", "assistant") and isinstance(t.get("texte"), str):
            qui = "Utilisateur" if t["role"] == "user" else "Assistant"
            lignes.append(f"{qui} : {t['texte'].strip()[:MAX_TOUR]}")
    return ("Échange précédent :\n" + "\n".join(lignes) + "\n\nNouvelle question : ") if lignes \
        else "Nouvelle question : "


def _image(im) -> tuple[dict, list]:
    """({largeur, hauteur}, [{mime, b64}]) d'une capture jointe ; ValueError si elle est illisible."""
    from app.services import moteurs_texte as MT
    if not isinstance(im, dict):
        raise ValueError("Image jointe illisible.")
    l, h, b64 = im.get("largeur"), im.get("hauteur"), im.get("b64")
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 < v <= COTE_MAX for v in (l, h)) \
            or not isinstance(b64, str) or len(b64) > MAX_IMAGE_B64:
        raise ValueError("Image jointe illisible.")
    try:
        images = MT.images_valides([{"mime": im.get("mime"), "b64": b64}])
    except RuntimeError as e:
        raise ValueError(str(e)) from None
    return {"largeur": l, "hauteur": h}, images


def _preparer(corps, lang: str) -> dict:
    """La question validée, le moteur, et les prompts d'un appel : `prompt` (envoyé), `devis` (consigne de vue à la
    taille nominale : le texte que chiffrent le devis ET la vérification de `max_usd`)."""
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    q = corps.get("question")
    q = q.strip()[:MAX_QUESTION] if isinstance(q, str) else ""
    if not q:
        raise ValueError("La question est vide.")
    lang = "en" if (corps.get("lang") or lang) == "en" else "fr"
    ecran = corps.get("ecran") if corps.get("ecran") in VUES else ""
    demande = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    image, images = _image(corps["image"]) if corps.get("image") is not None else (None, None)
    base = _historique(corps.get("historique")) + q
    vue = "\n\n" + CONSIGNE_VUE[lang]
    return {"q": q, "lang": lang, "ecran": ecran, "moteur": choisir_moteur(demande), "image": image,
            "images": images,
            "prompt": base + (vue.format(l=image["largeur"], h=image["hauteur"]) if image else ""),
            "devis": base + vue.format(l=VUE_NOMINALE[0], h=VUE_NOMINALE[1])}


def _cout(p: dict, sys_txt: str) -> float:
    """Le coût estimé (USD, 4 décimales) d'un appel AVEC capture pour cette question."""
    from app.services import moteurs_texte as MT
    from app.services import pricing as PR
    op = MT.estimer(p["moteur"], p["devis"], sys_txt, MAX_TOKENS, "low", images=1)
    return round(float(PR.estimate(op).get("total_usd") or 0.0), 4)


def _systeme_question(p: dict) -> str:
    """Le message système d'une question : un seul point pour le devis et l'envoi, qui restent le même texte."""
    vis = rapprocher(p.get("visibles") or [], p["lang"]) if p.get("visibles") else None
    ids = [x["id"] for x in (vis or {}).get("reconnus", [])]
    return systeme(p["ecran"], p["lang"], _espace(), pertinents=chercher(p["q"], p["ecran"], ids), visibles=vis)


def estimer_vue(corps, lang: str = "fr") -> dict:
    """Le devis GRATUIT d'un appel avec capture : {moteur, nom, usd, cout, vision}. Aucune image n'est lue ici."""
    from app.services import moteurs_texte as MT
    if isinstance(corps, dict) and "image" in corps:
        corps = {k: v for k, v in corps.items() if k != "image"}
    p = _preparer(corps, lang)
    if not p["moteur"]:
        return {"moteur": "", "nom": "", "usd": 0.0, "cout": "", "vision": False}
    return {"moteur": p["moteur"], "nom": MT.nom(p["moteur"]), "cout": MT.nature_cout(p["moteur"]),
            "vision": MT.vision(p["moteur"]), "usd": _cout(p, _systeme_question(p))}


async def demander(corps, lang: str = "fr") -> dict:
    """{texte, actions, moteur, nom, rejets, sans_cle}. ValueError : corps, question ou capture invalides.
    CoutChange : le coût d'un appel avec capture dépasse `max_usd`. RuntimeError : le moteur a échoué.
    HTTPException 402 : plafond « aide » (remonte tel quel jusqu'au dialogue de l'écran)."""
    from app.services import moteurs_texte as MT
    p = _preparer(corps, lang)
    lang, moteur = p["lang"], p["moteur"]
    if not moteur:
        _, actions, _ = analyser("[POINT:reglages.cles] [GUIDE:cles]")
        return {"texte": SANS_CLE[lang], "actions": actions, "moteur": "", "nom": "", "rejets": 0, "sans_cle": True}
    sys_txt = _systeme_question(p)
    if p["images"]:
        if not await asyncio.to_thread(MT.vision, moteur):
            raise ValueError("Ce moteur ne lit pas les images : choisis-en un qui voit l'écran.")
        mx = corps.get("max_usd")
        if isinstance(mx, bool) or not isinstance(mx, (int, float)):
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.")
        try:
            mx = float(mx)              # un entier géant (10**400) lève OverflowError
        except (OverflowError, ValueError):
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.") from None
        if not math.isfinite(mx) or mx < 0:
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.")
        if await asyncio.to_thread(_cout, p, sys_txt) > mx + EPS_USD:      # peut interroger Ollama (synchrone)
            raise CoutChange()
    sortie = await MT.tirer_garde(moteur, "", p["prompt"], sys_txt, MAX_TOKENS, categorie="aide", effort="low",
                                  images=p["images"])
    texte, actions, rejets = analyser(sortie, p["image"])
    if not texte:
        if actions:
            texte = REPONSE_VIDE[lang]
        else:
            texte = SANS_REPONSE[lang]
            actions = analyser("[GUIDE:tour]")[1]
    if rejets:
        logger.info(f"agent_aide : {rejets} balise(s) inconnue(s) retirée(s) ({moteur})")
    return {"texte": texte, "actions": actions, "moteur": moteur, "nom": MT.nom(moteur), "rejets": rejets,
            "sans_cle": False}


def etat() -> dict:
    from app.services import moteurs_texte as MT
    k = connaissance()
    moteurs = [{"moteur": l["moteur"], "nom": l["nom"], "cout": MT.nature_cout(l["moteur"]),
                "vision": MT.vision(l["moteur"])}
               for l in MT.etat() if l["configure"] and not l.get("fautif")]
    return {"moteur": choisir_moteur(), "moteurs": moteurs, "ancres": len(k["ancres"]),
            "chapitres": len(k["chapitres"]), "voix": etat_voix()}


# ── A6 : la lecture à voix haute (voix des Réglages : Voicebox local gratuit, ElevenLabs payant) ──
MAX_LECTURE = 1500               # caractères lus au plus : une réponse de l'assistant tient en dessous
GARDER_LECTURES = 30             # MP3 gardés dans le cache (les plus récents)
NOMS_VOIX = {"elevenlabs": "ElevenLabs", "voicebox": "Voicebox"}


def texte_a_lire(t) -> str:
    """Le texte d'une réponse à lire : une chaîne, sans balise, espaces réduits, bornée."""
    if not isinstance(t, str):
        return ""
    return " ".join(BALISE.sub(" ", t).split())[:MAX_LECTURE]


def dossier_lectures() -> Path:
    """Le cache des lectures, À PART de la Bibliothèque (jamais listé comme un média de l'utilisateur)."""
    from app.config import settings
    d = settings.images_path.parent / "agent_lectures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def voix_lecture(fournisseur: str, lang: str) -> str:
    """La voix et le modèle réglés pour cette langue : changer de voix dans les Réglages ne relit pas l'ancien MP3."""
    from app.config import settings
    if fournisseur == "elevenlabs":
        v = getattr(settings, "ELEVENLABS_VOICE_ID_" + ("EN" if lang == "en" else "FR"), "")
        return f"{v}|{getattr(settings, 'ELEVENLABS_MODEL', '')}"
    return str(getattr(settings, "VOICEBOX_URL", "") or "")


def chemin_lecture(fournisseur: str, lang: str, texte: str, voix: str = "") -> Path:
    h = hashlib.sha1(f"{fournisseur}|{voix}|{lang}|{texte}".encode("utf-8")).hexdigest()[:20]
    return dossier_lectures() / f"{h}.mp3"


def op_lecture(fournisseur: str, texte: str) -> dict | None:
    """L'op de la garde des plafonds : ElevenLabs au caractère ; Voicebox (local) ne coûte rien -> None."""
    return {"kind": "elevenlabs", "chars": len(texte)} if fournisseur == "elevenlabs" else None


def elaguer_lectures(garder: int = GARDER_LECTURES) -> None:
    datees = []
    for p in dossier_lectures().glob("*.mp3"):          # les `.part` en cours d'écriture ne sont jamais comptés
        try:
            datees.append((p.stat().st_mtime, p))
        except OSError:
            continue                                     # disparu entre-temps (autre requête) : ignoré
    datees.sort(key=lambda x: x[0], reverse=True)
    for _, p in datees[garder:]:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


def etat_voix() -> dict:
    """{fournisseur, nom, cout} de la voix des Réglages ; fournisseur "" : aucune voix (le tiroir cache « Lire »)."""
    from app.services import voice_providers as VP
    p = VP.resolve_provider()
    return {"fournisseur": p, "nom": NOMS_VOIX.get(p, ""),
            "cout": "gratuit" if p == "voicebox" else ("payant" if p else "")}
