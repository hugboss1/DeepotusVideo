# -*- coding: utf-8 -*-
"""t207 (Espaces de marque E7, 13/10/2026) — les CONTENUS DE DÉPART d'un espace (`contenus.json`, spec D5).

Ce que Quick lit pour l'espace actif : les modèles de prompt (id, cat, title, emoji, short, body — la forme de
PROMPT_TEMPLATES), les catégories, les ingrédients du générateur (ING), les vibes, et les hashtags. Deepotus garde sa
graine (la liste de prompts.jsx, extraite à l'octet par t200) ; un espace neuf part VIDE, puis :
  - à la validation de l'onboarding, une proposition SANS IA tirée du persona (et de son identité t206) est écrite si
    l'espace n'a encore aucun modèle ;
  - « Modèles de l'espace » (Quick) propose d'autres modèles — sans IA (gratuit) ou par LLM (sur demande, devisé, sous
    plafond) — pour tout l'espace ou UNE catégorie ; l'utilisateur coche, puis ajoute ou remplace. Rien n'est écrit
    sans ce geste.
Doctrine : jamais de nom d'artiste dans un modèle (identite.nom_d_artiste), jamais un sujet ou un mot interdit du
persona ; un modèle fautif est écarté, pas réécrit.
"""
from __future__ import annotations

import json
import re

from loguru import logger

from app.services import espaces

PRESETS = ("cinematic", "ugc_raw", "hybrid")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
MAX_CATS, MAX_TPL, MAX_ING, MAX_ING_VAL, MAX_VIBES, MAX_TAGS = 12, 80, 10, 20, 16, 30
CLES = ("version", "prompt_templates", "prompt_cats", "ingredients", "vibes", "hashtags")


def slug(t: str, defaut: str = "x") -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40]
    return s or defaut


# ---- validation ------------------------------------------------------------------------------------------------------

def _txt(v, champ, mini, maxi):
    if not isinstance(v, str):
        raise ValueError(f"{champ} doit être un texte")
    v = v.strip()
    if len(v) < mini or len(v) > maxi:
        raise ValueError(f"{champ} : de {mini} à {maxi} caractères")
    return v


def _id(v, champ):
    if not isinstance(v, str) or not _SLUG.match(v):
        raise ValueError(f"{champ} : identifiant en minuscules, chiffres, tiret ou souligné (40 au plus)")
    return v


def valider(doc) -> dict:
    """Le contenus.json propre, ou ValueError (dit le champ fautif)."""
    if not isinstance(doc, dict):
        raise ValueError("les contenus s'écrivent en objet JSON")
    inconnus = set(doc) - set(CLES)
    if inconnus:
        raise ValueError(f"champ inconnu : {', '.join(sorted(inconnus))}")
    cats = doc.get("prompt_cats", [])
    if not isinstance(cats, list) or len(cats) > MAX_CATS:
        raise ValueError(f"prompt_cats : une liste de {MAX_CATS} catégories au plus")
    out_c, vus = [], set()
    for i, c in enumerate(cats):
        if not isinstance(c, dict):
            raise ValueError(f"catégorie n°{i + 1} invalide")
        cid = _id(c.get("id"), f"catégorie n°{i + 1}")
        if cid in vus:
            raise ValueError(f"catégorie en double : {cid}")
        vus.add(cid)
        out_c.append({"id": cid, "label": _txt(c.get("label"), f"catégorie {cid}.label", 1, 40)})
    tpls = doc.get("prompt_templates", [])
    if not isinstance(tpls, list) or len(tpls) > MAX_TPL:
        raise ValueError(f"prompt_templates : une liste de {MAX_TPL} modèles au plus")
    out_t, ids = [], set()
    for i, t in enumerate(tpls):
        if not isinstance(t, dict):
            raise ValueError(f"modèle n°{i + 1} invalide")
        tid = _id(t.get("id"), f"modèle n°{i + 1}")
        if tid in ids:
            raise ValueError(f"modèle en double : {tid}")
        ids.add(tid)
        if t.get("cat") not in vus:
            raise ValueError(f"modèle {tid} : catégorie inconnue ({t.get('cat')})")
        out_t.append({"id": tid, "cat": t["cat"], "title": _txt(t.get("title"), f"modèle {tid}.title", 1, 80),
                      "emoji": _txt(t.get("emoji", ""), f"modèle {tid}.emoji", 0, 8),
                      "short": _txt(t.get("short", ""), f"modèle {tid}.short", 0, 140),
                      "body": _txt(t.get("body"), f"modèle {tid}.body", 1, 1500)})
    ing = doc.get("ingredients", {})
    if not isinstance(ing, dict) or len(ing) > MAX_ING:
        raise ValueError(f"ingredients : un objet de {MAX_ING} familles au plus")
    out_i = {}
    for k, v in ing.items():
        _id(k, f"ingrédient {k}")
        if not isinstance(v, list) or len(v) > MAX_ING_VAL or not all(isinstance(x, str) for x in v):
            raise ValueError(f"ingredients.{k} : une liste de {MAX_ING_VAL} textes au plus")
        out_i[k] = [_txt(x, f"ingredients.{k}", 1, 80) for x in v]
    vib = doc.get("vibes", [])
    if not isinstance(vib, list) or len(vib) > MAX_VIBES:
        raise ValueError(f"vibes : une liste de {MAX_VIBES} au plus")
    out_v, vids = [], set()
    for i, v in enumerate(vib):
        if not isinstance(v, dict):
            raise ValueError(f"vibe n°{i + 1} invalide")
        vid = _id(v.get("id"), f"vibe n°{i + 1}")
        if vid in vids:
            raise ValueError(f"vibe en double : {vid}")
        vids.add(vid)
        if v.get("preset") not in PRESETS:
            raise ValueError(f"vibe {vid} : preset parmi {', '.join(PRESETS)}")
        out_v.append({"id": vid, "preset": v["preset"], "tags": _txt(v.get("tags", ""), f"vibe {vid}.tags", 0, 300)})
    out = {"version": 1, "prompt_templates": out_t, "prompt_cats": out_c, "ingredients": out_i, "vibes": out_v}
    if "hashtags" in doc:
        h = doc["hashtags"]
        if not isinstance(h, list) or len(h) > MAX_TAGS or not all(isinstance(x, str) for x in h):
            raise ValueError(f"hashtags : une liste de {MAX_TAGS} textes au plus")
        out["hashtags"] = [_txt(x, "hashtags", 1, 40) for x in h]
    return out


def ecrire(eid: str, doc) -> dict:
    """Remplace contenus.json après validation (rien d'écrit sur un refus). KeyError = espace inconnu."""
    if not espaces.id_valide(eid) or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    propre = valider(doc)
    espaces._ecrire_json(espaces.chemin(eid, "contenus.json"), propre)
    return espaces.contenus(eid)


# ---- la proposition sans IA ------------------------------------------------------------------------------------------

_DIRECTIONS = {"cinema": ("Cinéma", "🎬", "cinematic, low-key lighting, deep shadows, anamorphic lens, film grain"),
               "lumineux": ("Lumineux", "☀", "bright clean studio light, soft shadows, minimal set, crisp product focus"),
               "graphique": ("Graphique", "🟥", "bold flat colors, graphic shapes, high contrast, poster-like composition"),
               "organique": ("Organique", "🌿", "natural textures, warm diffuse light, shallow depth of field, calm mood")}
_CATS_DEFAUT = [("produit", "Produit", "✨", "clean hero shot, slow push-in, soft key light, crisp details"),
                ("personnage", "Personnage", "🎭", "character close-up, expressive pose, shallow depth of field"),
                ("ambiance", "Ambiance", "🌫", "atmospheric wide shot, slow drift, layered depth, gentle haze"),
                ("social", "Social", "📱", "vertical 9:16, punchy opening frame, handheld energy, bold framing")]
_MOTION = ["slow push-in", "orbit", "handheld drift", "static locked-off", "tracking shot", "crane descending",
           "whip pan"]
_LENS = ["35mm", "50mm", "85mm portrait", "anamorphic", "macro", "wide 24mm"]


def _sujets(eid: str) -> list:
    p = espaces.persona(eid)
    vis, idt = p.get("visuel") or {}, p.get("identite") or {}
    pers = vis.get("personnage") or {}
    out = []
    if pers.get("type") in ("mascotte", "humain", "abstrait") and (pers.get("description") or "").strip():
        out.append(pers["description"].strip()[:80])
    out += [x.strip()[:80] for x in (idt.get("produits") or []) if isinstance(x, str) and x.strip()]
    out.append((p.get("display_name") or eid).strip()[:80])
    return list(dict.fromkeys(out))


def _descripteurs(eid: str) -> list:
    from app.services import identite
    a = identite.adn(eid)
    return list(dict.fromkeys([x for x in a["touches_sujet"] + a["touches_decor"] if x]))


def proposition_manuelle(eid: str, categorie: str | None = None) -> dict:
    """Tirée du persona et de son identité, SANS IA (toujours possible, gratuite). `categorie` : seulement ses modèles."""
    from app.services import identite
    p = espaces.persona(eid)
    vis, ec = p.get("visuel") or {}, p.get("ecran") or {}
    choisies = [d for d in (vis.get("directions_choisies") or []) if d in _DIRECTIONS]
    cats = [(d, *_DIRECTIONS[d]) for d in choisies] + [c for c in _CATS_DEFAUT if c[0] not in choisies]
    cats = cats[:6]
    actuels = {c["id"]: c for c in espaces.contenus(eid).get("prompt_cats", [])}
    if categorie:
        cats = [c for c in cats if c[0] == categorie] or ([(categorie, actuels[categorie]["label"], "✨",
                                                             "signature shot, considered framing, brand mood")]
                                                           if categorie in actuels else [])
        if not cats:
            raise ValueError(f"catégorie inconnue : {categorie}")
    sujets, desc = _sujets(eid), _descripteurs(eid)
    pal = [c["hex"] for c in identite.lire(eid)["palette"]][:3]
    couleurs = f"brand colors {' and '.join(pal)}" if pal else ""
    tpls = []
    for cid, label, emoji, style in cats:
        for k, sujet in enumerate(sujets[:3]):
            bouts = [sujet, style] + desc[k:k + 2] + ([couleurs] if couleurs else [])
            body = ", ".join(b for b in bouts if b) + "."
            tid, n = f"{cid}-{slug(sujet)}"[:40], 2
            while any(t["id"] == tid for t in tpls):
                tid, n = f"{cid}-{slug(sujet)}"[:36] + f"-{n}", n + 1
            tpls.append({"id": tid, "cat": cid, "title": f"{sujet[:40]} · {label}"[:80],
                         "emoji": emoji, "short": style.split(",")[0][:140], "body": body[:1500]})
    vibes = [{"id": "cinematic", "preset": "cinematic", "tags": ", ".join(desc[:3])},
             {"id": "ugc_raw", "preset": "ugc_raw", "tags": "shot on phone, handheld, available light, slight motion blur"},
             {"id": "hybrid", "preset": "hybrid", "tags": ""}]
    vibes += [{"id": d, "preset": "cinematic", "tags": _DIRECTIONS[d][2]} for d in choisies]
    tons = [x for x in (ec.get("tone") or []) if isinstance(x, str)] + list((p.get("audience") or {}).get("aime") or [])
    ingredients = {"subject": sujets[:9], "mood": (tons or ["calm", "confident", "playful", "tense"])[:8],
                   "light": identite.adn(eid)["eclairages"][:7], "motion": _MOTION,
                   "palette": pal + ["warm neutrals", "high contrast", "muted pastels"][:max(0, 6 - len(pal))],
                   "lens": _LENS, "fx": desc[:8] or ["film grain", "soft haze"]}
    ingredients = {k: [x[:80] for x in v if x] for k, v in ingredients.items() if v}
    return _filtrer(eid, {"version": 1, "prompt_cats": [{"id": c[0], "label": c[1]} for c in cats],
                          "prompt_templates": tpls, "ingredients": ingredients, "vibes": vibes,
                          "hashtags": list(p.get("default_hashtags_pool") or [])[:MAX_TAGS]})


def _interdits(eid: str) -> list:
    p = espaces.persona(eid)
    vis, ec = p.get("visuel") or {}, p.get("ecran") or {}
    inter = vis.get("interdits") or {}
    mots = list(inter.get("sujets") or []) + list(ec.get("banned") or []) + list(inter.get("concurrents") or [])
    return [m.strip().lower() for m in mots if isinstance(m, str) and len(m.strip()) > 1]


def _filtrer(eid: str, prop: dict) -> dict:
    """Écarte un modèle qui nomme un artiste ou un interdit du persona ; la proposition reste valide (ou ValueError)."""
    from app.services import identite
    interdits = _interdits(eid)
    ecartes = []
    garde = []
    for t in prop.get("prompt_templates", []):
        texte = f"{t.get('title', '')} {t.get('short', '')} {t.get('body', '')}"
        fautif = identite.nom_d_artiste(texte) or next((m for m in interdits if m in texte.lower()), None)
        (ecartes if fautif else garde).append(t if not fautif else f"{t.get('id')} ({fautif})")
    prop = dict(prop, prompt_templates=garde)
    out = valider(prop)
    if ecartes:
        out["_ecartes"] = ecartes
    return out


# ---- la proposition par LLM ------------------------------------------------------------------------------------------

SYSTEME_LLM = ("You write starter content for a short-video brand app. Reply with JSON ONLY: "
               '{"prompt_cats": [{"id": slug, "label": str}] (4-6), "prompt_templates": [{"id": slug, "cat": cat id, '
               '"title": str, "emoji": one emoji, "short": str (<= 60 chars), "body": str (one video prompt, 25-60 words: '
               'subject, action, camera, light, palette, texture)}] (2-3 per category), "ingredients": {"subject": [...], '
               '"mood": [...], "light": [...], "motion": [...], "palette": [...], "lens": [...], "fx": [...]} (6-9 short '
               'items each), "vibes": [{"id": slug, "preset": "cinematic"|"ugc_raw"|"hybrid", "tags": str}] (4-8), '
               '"hashtags": [6-12]}. Describe visual style with descriptors only, NEVER an artist, studio or franchise '
               "name. Respect every forbidden topic, word and legal constraint of the persona.")


def jetons_llm() -> tuple:
    return 2500, 3000


def _persona_pour_llm(eid: str, categorie: str | None) -> str:
    from app.services import identite
    p = espaces.persona(eid)
    resume = {k: p.get(k) for k in ("display_name", "vibe_keywords", "identite", "audience", "ton", "visuel",
                                    "default_hashtags_pool")}
    resume["ecran"] = {k: (p.get("ecran") or {}).get(k) for k in ("role", "tone", "catchphrase", "banned", "languages")}
    idv = identite.lire(eid)
    resume["identite_visuelle"] = {"palette": idv["palette"], "style_ecrit": idv["style_ecrit"]}
    txt = "Persona (JSON):\n" + json.dumps(resume, ensure_ascii=False)[:6000]
    if categorie:
        cat = next((c for c in espaces.contenus(eid).get("prompt_cats", []) if c["id"] == categorie), None)
        txt += (f"\nOnly regenerate the category {json.dumps(cat or {'id': categorie}, ensure_ascii=False)}: "
                "return that single category and 3-5 templates in it.")
    return txt


def _json_objet(txt: str):
    from app.services.onboarding_persona import _json_objet as j
    return j(txt)


def proposition_llm(eid: str, categorie: str | None = None, dispatch=None) -> dict:
    """La proposition par LLM ; chaque partie illisible ou invalide garde la proposition SANS IA (note dite)."""
    base = proposition_manuelle(eid, categorie)
    if dispatch is None:
        from app.services import summarizer
        dispatch = summarizer._chat_dispatch
    try:
        brut, fournisseur = dispatch(_persona_pour_llm(eid, categorie), SYSTEME_LLM, jetons_llm()[1])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"contenus llm : {e}")
        brut, fournisseur = None, ""
    j = _json_objet(brut or "")
    if not j:
        return base | {"note": "le LLM n'a rien rendu de lisible : proposition sans IA"}
    out = dict(base)
    notes = []
    for k in ("prompt_cats", "vibes", "hashtags", "ingredients"):
        if k in j:
            try:
                out[k] = valider({k: j[k]})[k]          # chaque partie validée SEULE (les modèles viennent après)
            except ValueError as e:
                notes.append(f"{k} : {e}")
    if categorie:
        out["prompt_cats"] = [c for c in out["prompt_cats"] if c["id"] == categorie] or base["prompt_cats"]
    cats = {c["id"] for c in out["prompt_cats"]}
    tpls, vus = [], set()
    for t in j.get("prompt_templates") or []:
        if not isinstance(t, dict):
            continue
        t = dict(t, id=slug(t.get("id") or t.get("title") or "modele"), cat=categorie or t.get("cat"))
        if t["cat"] not in cats or t["id"] in vus:
            continue
        try:
            tpls.append(valider({"prompt_cats": out["prompt_cats"], "prompt_templates": [t]})["prompt_templates"][0])
            vus.add(t["id"])
        except ValueError as e:
            notes.append(str(e))
    if tpls:
        out["prompt_templates"] = tpls
    else:
        notes.append("aucun modèle lisible : modèles sans IA gardés")
        out["prompt_templates"] = [t for t in base["prompt_templates"] if t["cat"] in cats]
    out = _filtrer(eid, {k: v for k, v in out.items() if k in CLES})
    out["source"] = f"llm:{fournisseur}" if fournisseur else "llm"
    if notes:
        out["note"] = "; ".join(notes)[:600]
    return out


# ---- appliquer une proposition ----------------------------------------------------------------------------------------

def appliquer(eid: str, prop, mode: str = "ajouter", categorie: str | None = None, ids=None,
              tout: bool = False) -> dict:
    """Écrit les modèles COCHÉS (`ids`, tous sinon) : « ajouter » les met à la suite (un id déjà pris reçoit un suffixe),
    « remplacer » retire d'abord ceux de `categorie` (de tout l'espace sans catégorie). `tout` reprend aussi les
    catégories, ingrédients, vibes et hashtags proposés. ValueError = rien d'écrit."""
    if mode not in ("ajouter", "remplacer"):
        raise ValueError("mode : ajouter ou remplacer")
    p = valider({k: v for k, v in (prop or {}).items() if k in CLES})
    actuel = espaces.contenus(eid)
    neuf = {k: json.loads(json.dumps(actuel.get(k, v))) for k, v in espaces.CONTENUS_VIDES.items()}
    if "hashtags" in actuel:
        neuf["hashtags"] = list(actuel["hashtags"])
    if tout:
        for k in ("ingredients", "vibes", "hashtags"):
            if k in p:
                neuf[k] = p[k]
    cats = {c["id"]: c for c in neuf["prompt_cats"]}
    for c in p["prompt_cats"]:
        if tout or c["id"] not in cats:
            cats[c["id"]] = c
    if tout:
        ordre = [c["id"] for c in p["prompt_cats"]] + [k for k in cats if k not in {c["id"] for c in p["prompt_cats"]}]
        neuf["prompt_cats"] = [cats[k] for k in ordre]
    else:
        neuf["prompt_cats"] = list(cats.values())
    choisis = [t for t in p["prompt_templates"] if ids is None or t["id"] in set(ids)]
    if mode == "remplacer":
        neuf["prompt_templates"] = [t for t in neuf["prompt_templates"] if categorie and t["cat"] != categorie]
    pris = {t["id"] for t in neuf["prompt_templates"]}
    for t in choisis:
        tid, n = t["id"], 2
        while tid in pris:
            tid, n = f"{t['id'][:36]}-{n}", n + 1
        pris.add(tid)
        neuf["prompt_templates"].append(dict(t, id=tid))
    utilisees = {t["cat"] for t in neuf["prompt_templates"]}
    if mode == "remplacer" and not categorie:   # tout remplacé : les catégories vides partent
        neuf["prompt_cats"] = [c for c in neuf["prompt_cats"] if c["id"] in utilisees]
    return ecrire(eid, neuf)


def semer_si_vide(eid: str) -> bool:
    """À la validation de l'onboarding : un espace SANS modèle reçoit la proposition sans IA. Jamais Deepotus, jamais
    un espace qui a déjà des modèles. Rend vrai si elle a été écrite."""
    try:
        if eid == "deepotus" or espaces.contenus(eid).get("prompt_templates"):
            return False
        ecrire(eid, {k: v for k, v in proposition_manuelle(eid).items() if k in CLES})
        return True
    except Exception as e:  # noqa: BLE001 — l'onboarding est validé ; les contenus se génèrent ensuite dans Quick
        logger.warning(f"contenus de départ de {eid} : {e}")
        return False
