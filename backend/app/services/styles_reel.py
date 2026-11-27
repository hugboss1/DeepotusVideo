# -*- coding: utf-8 -*-
"""t503 (lot G13, 26/11/2026) — la BIBLIOTHÈQUE DE STYLES DE REEL NOMMÉS.

Un style est une RECETTE au-dessus de briques qui existent déjà dans l'application, rien de plus :
  - un gabarit INTÉGRÉ de Templates (`backend/app/templates/tpl_*.json`), dont chaque emplacement dit d'où vient son
    contenu : une page motion code (`motion`), l'avatar (`avatar`), un texte (`texte`) ou un plan fourni (`fournir`) ;
  - une ou plusieurs pages motion code, chacune = une fiche de style MAISON de la bibliothèque motion (t233,
    `style-<thème>`) avec ses champs de liste ou de nombre fixés (les champs texte restent à l'utilisateur) et ses
    curseurs (`motion_choregraphe.CURSEURS`) — exactement la `direction` que prend `POST /api/motion/code/ecrire` ;
  - une voix : synthèse (`elevenlabs_service.ELEVEN_MODELS`, balises Eleven v3 de `voice_direction`) ou celle de
    l'avatar ;
  - une humeur de musique (`music_service.MOOD_BY_ID`) et un modèle du catalogue (`music_service.MUSIC_MODELS`) ;
  - un préréglage de sous-titres (`subtitle_service.STYLES`), calé localement sur le texte connu ;
  - un rythme (durée d'un plan, durées min / type / max, bornées par le motion code).

Les styles sont des DONNÉES versionnées : `backend/app/styles_reel/<id>.json`, FR et EN. `verifier()` relit chaque
référence dans le code (un gabarit, un style motion, une humeur, un préréglage qui n'existe pas = un écart signalé).
Familles GÉNÉRIQUES (présentateur, motion sans visage, données, classement…) : aucun nom, texte ni visuel repris d'un
produit tiers.

Lecture seule et devis GRATUIT : `devis_style` chiffre la production avec les prix existants (`pricing.estimate` :
voix, avatar, musique, moteur de texte du motion code) sans rien lancer ni appeler aucun moteur. Les rendus (gabarit
ffmpeg, page motion code dans le bac à sable, calage des sous-titres) sont locaux : 0 $, et dits."""
from __future__ import annotations

import json
import re
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent.parent / "styles_reel"
LANGUES = ("fr", "en")
ASPECT = "9:16"

FAMILLES: dict[str, dict] = {
    "presentateur": {"fr": "Présentateur", "en": "Presenter"},
    "motion": {"fr": "Motion sans visage", "en": "Faceless motion"},
    "donnees": {"fr": "Données", "en": "Data"},
    "classement": {"fr": "Classement", "en": "Ranking"},
    "explication": {"fr": "Explication", "en": "Explainer"},
    "comparaison": {"fr": "Comparaison", "en": "Comparison"},
    "demo": {"fr": "Démonstration", "en": "Demo"},
    "actualite": {"fr": "Actualité", "en": "News"},
}
SOURCES = ("motion", "avatar", "texte", "fournir")
VOIX_MOTEURS = ("tts", "avatar", "aucune")
STABILITES = (0.0, 0.5, 1.0)
VOLUME_DB = (-40.0, 0.0)
PLAN_S_MAX = 10.0

_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,40}$")
_MAX_TITRE = 80
_MAX_RESUME = 280

_LIBELLES = {
    "rendu_motion": {"fr": "Rendu motion code « {page} » (bac à sable local)",
                     "en": "Motion code render “{page}” (local sandbox)"},
    "repli_motion": {"fr": "Page motion code « {page} » : repli déterministe (sans moteur de texte)",
                     "en": "Motion code page “{page}”: deterministic fallback (no text engine)"},
    "gabarit": {"fr": "Gabarit {id} (ffmpeg local)", "en": "Template {id} (local ffmpeg)"},
    "sous_titres": {"fr": "Sous-titres « {id} » calés sur le texte (local)",
                    "en": "Captions “{id}” aligned to the text (local)"},
}


def _langue(langue) -> str:
    return langue if langue in LANGUES else "fr"


def _loc(v, langue: str) -> str:
    if isinstance(v, dict):
        return str(v.get(langue) or v.get("fr") or "")
    return str(v or "")


def _bilingue(v, maxi: int) -> bool:
    return isinstance(v, dict) and all(isinstance(v.get(lg), str) and 0 < len(v[lg].strip()) <= maxi
                                       for lg in LANGUES)


def _nombre(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ── chargement ────────────────────────────────────────────────────────────────────────────────────────────────────
def _fichiers(dossier=None) -> list:
    d = Path(dossier) if dossier else DOSSIER
    return sorted(d.glob("*.json")) if d.is_dir() else []


def _lire_tous(dossier=None) -> tuple:
    """([(chemin, style)], [écarts de lecture])."""
    out, ecarts = [], []
    for p in _fichiers(dossier):
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            ecarts.append(f"{p.name} : illisible ({e.__class__.__name__})")
            continue
        if not isinstance(b, dict):
            ecarts.append(f"{p.name} : un objet JSON est attendu")
            continue
        out.append((p, b))
    return out, ecarts


def _valides(dossier=None) -> dict:
    """{id: style} des styles SANS écart (un style fautif n'est jamais servi)."""
    styles, _ = _lire_tous(dossier)
    return {b["id"]: b for p, b in styles if not _ecarts_style(p, b)}


# ── vérification ──────────────────────────────────────────────────────────────────────────────────────────────────
def _gabarits():
    from app.services.template_service import TemplateEngine
    return TemplateEngine()


def _fiche_motion(sid: str):
    from app.services import motion_biblio as MB
    if not isinstance(sid, str) or not sid.startswith("style-"):
        return None
    try:
        f = MB.lire(sid)
    except (LookupError, ValueError, OSError):
        return None
    return f if f.get("nature") == "style" else None


def _ecarts_motion(nom: str, pg, duree: dict) -> list:
    from app.services import motion_choregraphe as CH, motion_code as MC
    e = []
    if not isinstance(pg, dict):
        return [f"page motion « {nom} » : un objet est attendu"]
    f = _fiche_motion(pg.get("style"))
    if f is None:
        e.append(f"page motion « {nom} » : style motion inconnu {pg.get('style')!r}")
    else:
        champs = {c["id"]: c for c in f.get("champs") or [] if isinstance(c, dict) and c.get("id")}
        valeurs = pg.get("champs") or {}
        if not isinstance(valeurs, dict):
            e.append(f"page motion « {nom} » : champs illisibles")
            valeurs = {}
        for cid, v in valeurs.items():
            c = champs.get(cid)
            if c is None:
                e.append(f"page motion « {nom} » : champ inconnu {cid!r} pour {pg['style']}")
            elif c.get("type") == "texte":
                e.append(f"page motion « {nom} » : le champ texte {cid!r} revient à l'utilisateur, pas au style")
            elif c.get("type") == "liste" and v not in [o.get("valeur") for o in c.get("options") or []]:
                e.append(f"page motion « {nom} » : valeur {v!r} hors de la liste de {cid!r}")
            elif c.get("type") == "nombre" and not (_nombre(v) and c.get("min", v) <= v <= c.get("max", v)):
                e.append(f"page motion « {nom} » : nombre {v!r} hors des bornes de {cid!r}")
    cur = pg.get("curseurs") or {}
    if not isinstance(cur, dict):
        e.append(f"page motion « {nom} » : curseurs illisibles")
        cur = {}
    for k, v in cur.items():
        if k not in CH.CURSEURS:
            e.append(f"page motion « {nom} » : curseur inconnu {k!r}")
        elif not (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 4):
            e.append(f"page motion « {nom} » : curseur {k!r} hors de 0-4")
    part = pg.get("part", 1.0)
    if not (_nombre(part) and 0 < part <= 1):
        e.append(f"page motion « {nom} » : part hors de ]0, 1]")
    elif all(_nombre(duree.get(k)) for k in ("min", "max")):
        lo, hi = MC.DUREE
        if not (lo <= duree["min"] * part and duree["max"] * part <= hi):
            e.append(f"page motion « {nom} » : sa durée sort des bornes du motion code ({lo}-{hi} s)")
    return e


def _ecarts_style(p: Path, b: dict) -> list:
    from app.services import elevenlabs_service as EL, music_service as MU, subtitle_service as ST
    from app.services import voice_direction as VD
    sid = b.get("id")
    e = []
    if not isinstance(sid, str) or not _ID.match(sid):
        e.append(f"id illisible {sid!r}")
    elif sid != p.stem:
        e.append(f"id {sid!r} ≠ nom du fichier {p.stem!r}")
    if not (isinstance(b.get("version"), int) and not isinstance(b.get("version"), bool) and b["version"] >= 1):
        e.append("version : un entier ≥ 1 est attendu")
    if b.get("famille") not in FAMILLES:
        e.append(f"famille inconnue {b.get('famille')!r}")
    if not _bilingue(b.get("titre"), _MAX_TITRE):
        e.append("titre : FR et EN attendus")
    if not _bilingue(b.get("resume"), _MAX_RESUME):
        e.append("résumé : FR et EN attendus")
    af = b.get("a_fournir")
    if not (isinstance(af, list) and af and all(_bilingue(x, _MAX_RESUME) for x in af)):
        e.append("à fournir : une liste non vide, FR et EN")

    # rythme
    ry = b.get("rythme") if isinstance(b.get("rythme"), dict) else {}
    duree = ry.get("duree_s") if isinstance(ry.get("duree_s"), dict) else {}
    if not (all(_nombre(duree.get(k)) for k in ("min", "type", "max"))
            and 0 < duree["min"] <= duree["type"] <= duree["max"]):
        e.append("rythme.duree_s : min ≤ type ≤ max attendus")
        duree = {}
    ps = ry.get("plan_s")
    if not (isinstance(ps, list) and len(ps) == 2 and all(_nombre(x) for x in ps) and 0 < ps[0] <= ps[1] <= PLAN_S_MAX):
        e.append(f"rythme.plan_s : [a, b] avec 0 < a ≤ b ≤ {PLAN_S_MAX:g}")

    # motion
    motion = b.get("motion") if b.get("motion") is not None else {}
    if not isinstance(motion, dict):
        e.append("motion : un objet {page: direction} est attendu")
        motion = {}
    for nom, pg in motion.items():
        e += _ecarts_motion(nom, pg, duree)

    # voix
    voix = b.get("voix") if isinstance(b.get("voix"), dict) else {}
    vm = voix.get("moteur")
    if vm not in VOIX_MOTEURS:
        e.append(f"voix : moteur inconnu {vm!r}")
    if vm == "tts":
        if voix.get("modele") not in EL.ELEVEN_MODELS:
            e.append(f"voix : modèle inconnu {voix.get('modele')!r}")
        bal = voix.get("balises") or []
        if not (isinstance(bal, list) and len(bal) <= VD.MAX_TAGS and all(isinstance(t, str) and VD.is_known(t)
                                                                           for t in bal)):
            e.append(f"voix : balises inconnues ou trop nombreuses {bal!r}")
        if voix.get("stabilite", 0.5) not in STABILITES:
            e.append(f"voix : stabilité hors de {STABILITES}")

    # gabarit
    g = b.get("gabarit")
    avatars = 0
    pages_utilisees = set()
    if g is not None:
        tp = _gabarits()
        if not isinstance(g, dict) or not isinstance(g.get("id"), str) or not tp.is_builtin(g["id"]):
            e.append(f"gabarit inconnu {(g or {}).get('id') if isinstance(g, dict) else g!r}")
        else:
            slots = {s["slot_name"]: s for s in tp.list_slots(g["id"])}
            emp = g.get("emplacements") if isinstance(g.get("emplacements"), dict) else {}
            for nom in emp:
                if nom not in slots:
                    e.append(f"gabarit {g['id']} : emplacement inconnu {nom!r}")
            for nom, s in slots.items():
                if s.get("type") != "audio_slot" and nom not in emp:
                    e.append(f"gabarit {g['id']} : emplacement oublié {nom!r}")
            for nom, x in emp.items():
                x = x if isinstance(x, dict) else {}
                src = x.get("source")
                if src not in SOURCES:
                    e.append(f"emplacement {nom!r} : source inconnue {src!r}")
                elif src == "motion":
                    if x.get("page") not in motion:
                        e.append(f"emplacement {nom!r} : page motion absente {x.get('page')!r}")
                    pages_utilisees.add(x.get("page"))
                elif src == "avatar":
                    avatars += 1
                    part = x.get("part", 1.0)
                    if not (_nombre(part) and 0 < part <= 1):
                        e.append(f"emplacement {nom!r} : part hors de ]0, 1]")
                elif src == "texte" and not _bilingue(x.get("libelle"), _MAX_TITRE):
                    e.append(f"emplacement {nom!r} : libellé FR et EN attendu")
                if nom in slots and src in ("motion", "avatar", "fournir") and slots[nom].get("type") != "video_slot":
                    e.append(f"emplacement {nom!r} : une vidéo ne va pas dans un emplacement {slots[nom].get('type')}")
                if nom in slots and src == "texte" and slots[nom].get("type") != "text_slot":
                    e.append(f"emplacement {nom!r} : un texte ne va que dans un emplacement texte")
            for nom in motion:
                if nom not in pages_utilisees:
                    e.append(f"page motion « {nom} » : aucun emplacement ne l'utilise")
    elif len(motion) != 1:
        e.append("sans gabarit : exactement une page motion est attendue")
    if (avatars > 0) != (vm == "avatar"):
        e.append("voix : la voix d'avatar va avec au moins un emplacement avatar, et réciproquement")

    # musique, sous-titres
    mu = b.get("musique")
    if mu is not None:
        if not isinstance(mu, dict) or mu.get("humeur") not in MU.MOOD_BY_ID:
            e.append(f"musique : humeur inconnue {(mu or {}).get('humeur') if isinstance(mu, dict) else mu!r}")
        elif mu.get("modele") not in MU.MUSIC_MODELS:
            e.append(f"musique : modèle inconnu {mu.get('modele')!r}")
        elif not (_nombre(mu.get("volume_db", -18)) and VOLUME_DB[0] <= mu.get("volume_db", -18) <= VOLUME_DB[1]):
            e.append(f"musique : volume hors de {VOLUME_DB}")
    stt = b.get("sous_titres")
    if stt is not None and (not isinstance(stt, dict) or stt.get("prereglage") not in ST.STYLES):
        e.append(f"sous-titres : préréglage inconnu {(stt or {}).get('prereglage') if isinstance(stt, dict) else stt!r}")
    return [f"{p.name} : {x}" for x in e]


def verifier(dossier=None) -> list:
    """Les écarts du registre (liste vide = sain) : lecture, schéma, FR/EN, et CHAQUE référence relue dans le code."""
    styles, ecarts = _lire_tous(dossier)
    vus: dict = {}
    for p, b in styles:
        ecarts += _ecarts_style(p, b)
        sid = b.get("id")
        if isinstance(sid, str):
            if sid in vus:
                ecarts.append(f"{p.name} : id {sid!r} en double (déjà dans {vus[sid]})")
            vus.setdefault(sid, p.name)
    return ecarts


# ── lecture ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _briques(b: dict) -> dict:
    g = b.get("gabarit") or {}
    return {"gabarit": g.get("id"), "motion": sorted({pg["style"] for pg in (b.get("motion") or {}).values()}),
            "voix": (b.get("voix") or {}).get("moteur"), "musique": (b.get("musique") or {}).get("humeur"),
            "sous_titres": (b.get("sous_titres") or {}).get("prereglage")}


def lister_styles(langue: str = "fr", dossier=None) -> list:
    """Les styles sains, triés par id : {id, famille, famille_libelle, titre, resume, duree_s, gabarit, motion, voix,
    musique, sous_titres}. Gratuit, aucune écriture."""
    lg = _langue(langue)
    out = []
    for sid, b in sorted(_valides(dossier).items()):
        out.append({"id": sid, "famille": b["famille"], "famille_libelle": FAMILLES[b["famille"]][lg],
                    "titre": _loc(b["titre"], lg), "resume": _loc(b["resume"], lg),
                    "duree_s": dict(b["rythme"]["duree_s"])} | _briques(b))
    return out


def familles(langue: str = "fr") -> list:
    lg = _langue(langue)
    return [{"id": k, "libelle": v[lg]} for k, v in FAMILLES.items()]


def style(sid, langue: str = "fr", dossier=None) -> dict | None:
    """Le style complet dans `langue` (repli FR) : parties, emplacements nommés du gabarit, champs motion à remplir,
    ce qu'il faut fournir. None pour un id inconnu, illisible ou fautif."""
    if not isinstance(sid, str) or not _ID.match(sid):
        return None
    b = _valides(dossier).get(sid)
    if b is None:
        return None
    lg = _langue(langue)
    out = {"id": sid, "version": b["version"], "famille": b["famille"], "famille_libelle": FAMILLES[b["famille"]][lg],
           "titre": _loc(b["titre"], lg), "resume": _loc(b["resume"], lg),
           "a_fournir": [_loc(x, lg) for x in b["a_fournir"]], "rythme": json.loads(json.dumps(b["rythme"])),
           "voix": dict(b["voix"]), "musique": dict(b["musique"]) if b.get("musique") else None,
           "sous_titres": dict(b["sous_titres"]) if b.get("sous_titres") else None, "motion": {}, "gabarit": None}
    for nom, pg in (b.get("motion") or {}).items():
        f = _fiche_motion(pg["style"])
        fixes = pg.get("champs") or {}
        a_remplir = [{"id": c["id"], "type": c["type"], "libelle": _loc(c.get("libelle"), lg),
                      "aide": _loc(c.get("aide"), lg)}
                     for c in f.get("champs") or [] if c.get("id") not in fixes]
        out["motion"][nom] = {"style": pg["style"], "titre_style": _loc(f.get("titre"), lg),
                              "direction": {"style": pg["style"], "champs": dict(fixes),
                                            "curseurs": dict(pg.get("curseurs") or {})},
                              "part": pg.get("part", 1.0), "a_remplir": a_remplir}
    g = b.get("gabarit")
    if g:
        slots = {s["slot_name"]: s for s in _gabarits().list_slots(g["id"])}
        emps = []
        for nom, x in g["emplacements"].items():
            e = {"emplacement": nom, "type": slots[nom].get("type"), "libelle_gabarit": slots[nom].get("slot_label"),
                 "source": x["source"]}
            if x["source"] == "motion":
                e["page"] = x["page"]
            elif x["source"] == "avatar":
                e["part"] = x.get("part", 1.0)
            elif x["source"] == "texte":
                e["libelle"] = _loc(x.get("libelle"), lg)
            emps.append(e)
        out["gabarit"] = {"id": g["id"], "emplacements": emps}
    return out


# ── devis ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _ligne_locale(cle: str, lg: str, **v) -> dict:
    return {"provider": "local", "label": _LIBELLES[cle][lg].format(**v), "units": 1, "unit": "job", "usd": 0.0}


def _txt(lignes: list, lg: str) -> list:
    from app import i18n
    return [dict(l, label=i18n.texte(l["label"], lg)) if isinstance(l.get("label"), str) else l for l in lignes]


def devis_style(sid, duree_s=None, langue: str = "fr", moteur: str = "anthropic", dossier=None) -> dict:
    """Le devis GRATUIT d'un reel dans ce style, sans rien lancer ni appeler aucun moteur.

    Durée : celle demandée, bornée aux durées du style (absente -> la durée type). Texte parlé : durée × débit de
    parole de la grille (`heygen_chars_per_min`). Lignes : une par page motion code (le moteur de texte `moteur`, au
    prompt système et au script de cette durée, `MAX_TOKENS` en sortie ; local = 0 ; vide = le repli déterministe),
    la voix de synthèse ou un avatar par emplacement (le texte partagé selon `part`), la musique (modèle du style, à la
    durée), puis les rendus locaux (0 $). Une 2e tentative du motion code, possible après une page refusée, n'est pas
    comptée : la garde des plafonds la chiffre à son tour. LookupError pour un style inconnu."""
    from app.services import motion_choregraphe as CH, motion_code as MC, moteurs_texte as MT, pricing
    b = _valides(dossier).get(sid) if isinstance(sid, str) and _ID.match(sid) else None
    if b is None:
        raise LookupError("Style de reel inconnu.")
    lg = _langue(langue)
    p = pricing.load()
    bornes = b["rythme"]["duree_s"]
    try:
        demande = float(duree_s) if duree_s is not None and str(duree_s).strip() != "" else None
    except (TypeError, ValueError):
        demande = None
    if demande is not None and demande != demande:                   # NaN
        demande = None
    duree = bornes["type"] if demande is None else min(bornes["max"], max(bornes["min"], demande))
    duree = int(duree) if float(duree).is_integer() else round(duree, 2)
    try:
        debit = float(p.get("heygen_chars_per_min") or pricing.DEFAULTS["heygen_chars_per_min"]) / 60.0
    except (TypeError, ValueError):
        debit = pricing.DEFAULTS["heygen_chars_per_min"] / 60.0
    chars = round(duree * debit)
    moteur = (moteur or "").strip() if isinstance(moteur, str) else ""

    ops, locales = [], []
    W, H = MC.taille(ASPECT)
    for nom, pg in (b.get("motion") or {}).items():
        part = float(pg.get("part", 1.0))
        d_page = max(MC.DUREE[0], min(MC.DUREE[1], round(duree * part, 2)))
        if moteur and MT.connu(moteur):
            d = CH.direction({"style": pg["style"], "champs": pg.get("champs") or {},
                              "curseurs": pg.get("curseurs") or {}}, lg)
            sy = MC.systeme(d, W, H, d_page, MC.FPS_DEFAUT, CH.marque(None))
            pr = MC.prompt("x" * max(1, round(chars * part)), ASPECT, W, H, d_page, MC.FPS_DEFAUT)
            ops.append(MT.estimer(moteur, pr, sy, MC.MAX_TOKENS))
        else:
            locales.append(_ligne_locale("repli_motion", lg, page=nom))
        locales.append(_ligne_locale("rendu_motion", lg, page=nom))
    voix = b["voix"]
    if voix["moteur"] == "tts":
        ops.append({"kind": "elevenlabs", "chars": chars, "model": voix["modele"]})
    elif voix["moteur"] == "avatar":
        for x in (b.get("gabarit") or {}).get("emplacements", {}).values():
            if x["source"] == "avatar":
                ops.append({"kind": "heygen", "chars": max(1, round(chars * float(x.get("part", 1.0))))})
    if b.get("musique"):
        ops.append({"kind": "music", "model": b["musique"]["modele"], "duration_s": duree})
    if b.get("gabarit"):
        locales.append(_ligne_locale("gabarit", lg, id=b["gabarit"]["id"]))
    if b.get("sous_titres"):
        locales.append(_ligne_locale("sous_titres", lg, id=b["sous_titres"]["prereglage"]))

    est = pricing.estimate({"kind": "composition", "parts": ops}, p)
    lignes = _txt(est["breakdown"], lg) + locales
    return {"style": sid, "duree_s": duree, "duree_bornee": demande is not None and demande != duree,
            "caracteres": chars, "moteur": moteur, "breakdown": lignes,
            "total_usd": round(sum(l["usd"] for l in lignes), 4), "credits": est.get("credits") or {},
            "lance": False, "gratuit": True}
