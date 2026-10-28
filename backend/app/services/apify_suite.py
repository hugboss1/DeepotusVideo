# -*- coding: utf-8 -*-
"""t365-t368 (28/10/2026) — ce que devient une collecte Apify acceptée, selon le BUT de sa carte (plan
docs/superpowers/plans/2026-10-28-veille-apify-t365-t369.md, décision 1). Le dépôt JSON brut du socle t364 reste ; ce
module en tire ce que l'agent et les écrans utilisent :
  leads   (t365) : des CIBLES {nom, site, note, categorie, ville} — ni téléphone ni avis — et le site PUBLIC de chaque
                   cible déposé comme URL, lisible ensuite par `prospects_chercher(source="entreprise")` (lecteur t354) ;
  veille  (t366) : des LIGNES DE VEILLE (auteur haché, jamais en clair) ajoutées au brut de la dernière veille, puis
                   reconsolidées par la grille ;
  signaux (t367) : des SIGNAUX DE BESOIN Reddit (posts « alternative à », « combien coûte »…) gardés 30 jours par
                   espace, rendus par `prospects_chercher(source="veille")` ; jamais une fiche, jamais un DM ;
Rien ici n'écrit de fiche ni n'envoie quoi que ce soit.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

BUTS = ("leads", "veille", "signaux")

# t366 : le champ d'entrée de chaque source de veille, et la nature de ses valeurs (requete : des mots, repris des
# requêtes du concurrent par défaut ; url : collée par l'utilisateur ; url_objet : {"url": …} ; id : identifiant)
ENTREES_VEILLE = {
    "reddit": ("searches", "requete"), "x": ("searchTerms", "requete"), "tiktok": ("searchQueries", "requete"),
    "instagram": ("directUrls", "url"), "instagram_posts": ("directUrls", "url"), "tiktok_commentaires": ("postURLs", "url"),
    "avis_google_maps": ("startUrls", "url_objet"), "google_play": ("appIds", "id"), "trustpilot": ("companyUrls", "url"),
    "g2": ("productUrls", "url"),
}
# Champs candidats par source (premier non vide) — portés du skill veille-concurrents (apify_vers_brut.py, 28/10/2026)
CHAMPS = {
    "reddit": {"texte": ["body", "text", "title"], "titre": ["title"], "url": ["url", "link"],
               "date": ["createdAt", "created_at"], "auteur": ["username", "author"], "score": ["upVotes", "score"]},
    "x": {"texte": ["text", "fullText", "full_text"], "url": ["url", "twitterUrl"], "date": ["createdAt", "created_at"],
          "auteur": ["author.userName", "author.username", "user.screen_name"], "score": ["likeCount", "favorite_count"]},
    "instagram": {"texte": ["text", "comment"], "url": ["postUrl", "url", "inputUrl"], "date": ["timestamp", "createdAt"],
                  "auteur": ["ownerUsername", "username", "owner.username"], "score": ["likesCount", "likes"]},
    "avis_google_maps": {"texte": ["text", "textTranslated", "reviewText"], "url": ["reviewUrl", "url"],
                         "date": ["publishedAtDate", "publishAt", "date"], "auteur": ["name", "reviewerName", "reviewerId"],
                         "score": ["stars", "rating"]},
    "google_play": {"texte": ["text", "content", "review", "reviewText"], "url": ["url", "reviewUrl", "appUrl"],
                    "date": ["date", "at", "updated", "publishedAt"], "auteur": ["userName", "user", "author"],
                    "score": ["score", "rating", "stars"]},
    "trustpilot": {"texte": ["text", "reviewText", "body", "content"], "titre": ["title", "reviewTitle"],
                   "url": ["url", "reviewUrl", "link"], "date": ["date", "publishedAt", "datePublished", "createdAt"],
                   "auteur": ["author", "consumerName", "userName", "name"], "score": ["rating", "stars", "score"]},
    "g2": {"texte": ["text", "reviewText", "review", "body", "likes"], "titre": ["title", "reviewTitle"],
           "url": ["url", "reviewUrl", "productUrl"], "date": ["date", "publishedAt", "submittedAt", "createdAt"],
           "auteur": ["author", "reviewerName", "userName", "name"], "score": ["rating", "stars", "score"]},
    "tiktok": {"texte": ["text", "desc"], "url": ["webVideoUrl", "url"], "date": ["createTimeISO", "createTime"],
               "auteur": ["authorMeta.name", "authorMeta.id", "author"], "score": ["diggCount", "playCount"]},
    "tiktok_commentaires": {"texte": ["text", "comment"], "url": ["videoWebUrl", "url"], "date": ["createTimeISO", "createTime"],
                            "auteur": ["uniqueId", "user.uniqueId", "uid"], "score": ["diggCount", "likes"]},
    "instagram_posts": {"texte": ["caption", "text"], "url": ["url", "inputUrl"], "date": ["timestamp", "createdAt"],
                        "auteur": ["ownerUsername", "owner.username"], "score": ["likesCount", "likes"]},
}
MAX_TEXTE_VEILLE = 4000


def _champ(item: dict, chemins: list):
    for chemin in chemins:
        v = item
        for k in chemin.split("."):
            v = v.get(k) if isinstance(v, dict) else None
        if v not in (None, "", [], {}):
            return v
    return None


def _date(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = v / 1000 if v > 1e12 else v
        try:
            return datetime.fromtimestamp(v, timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    s = str(v or "")
    return s[:10] if len(s) >= 10 and s[4] == "-" else s[:40]


def lignes_veille(source: str, concurrent: str, items: list, requete: str = "") -> list[dict]:
    """Les éléments d'un dataset en lignes de veille (format de veille_collecte) ; un élément sans texte est écarté."""
    from app.services import veille_collecte as VC
    c = CHAMPS[source]
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        texte, titre = _champ(it, c["texte"]), _champ(it, c.get("titre", []))
        if not isinstance(texte, str) or not texte.strip():
            continue
        if isinstance(titre, str) and titre.strip() and titre.strip() not in texte:
            texte = titre.strip() + " — " + texte
        score = _champ(it, c["score"])
        auteur = _champ(it, c["auteur"])
        out.append(VC._ligne(concurrent, source, str(_champ(it, c["url"]) or "")[:500], _date(_champ(it, c["date"])),
                             str(auteur) if auteur else None, texte.strip()[:MAX_TEXTE_VEILLE],
                             score if isinstance(score, (int, float)) and not isinstance(score, bool) else None, requete))
    return out


async def _veille(args: dict, items: list) -> dict:
    import asyncio
    from app.services import veille as V
    source, conc = args.get("acteur"), str(args.get("concurrent") or "")
    if source not in CHAMPS or not conc or not args.get("espace_id"):
        return {}
    ent = args.get("entree") or {}
    requete = " | ".join(str(x) for x in (ent.get(ENTREES_VEILLE[source][0]) or []) if isinstance(x, str))[:300]
    lignes = lignes_veille(source, conc, items, requete)
    r = await asyncio.to_thread(V.ajouter_brut, args["espace_id"], source, conc, lignes)
    return {"verbatims": r["ajoutes"], "consolide": r["consolide"]}


MAX_CIBLES = 100


def _texte(v, n: int = 200) -> str:
    return str(v or "").strip()[:n] if isinstance(v, (str, int, float)) else ""


async def _site_public(u) -> str:
    """L'URL normalisée si c'est un site public http(s), sinon "" (hôte local, javascript:, illisible)."""
    from app.services import agent_outils as AO
    n = AO._url_normale(str(u or ""))
    if not n:
        return ""
    try:
        AO._url_sure(n)
    except Exception:  # noqa: BLE001 — hôte local ou interdit
        return ""
    return n


async def _leads(cid: str, args: dict, items: list) -> dict:
    from app.services import agent_outils as AO
    ville = _texte((args.get("entree") or {}).get("locationQuery"), 120)
    cibles, deposes = [], set()
    for it in items[:MAX_CIBLES]:
        site = await _site_public(it.get("website"))
        note = it.get("totalScore")
        cibles.append({"nom": _texte(it.get("title")), "site": site,
                       "note": note if isinstance(note, (int, float)) and not isinstance(note, bool) else None,
                       "categorie": _texte(it.get("categoryName"), 120), "ville": _texte(it.get("city"), 120) or ville})
        if site and site not in deposes:
            deposes.add(site)
            await AO.enregistrer_depot(cid, "url", site)
    return {"cibles": cibles}


# ---- t367 : signaux de besoin Reddit --------------------------------------------------------------------------------
BESOIN_REDDIT = re.compile(r"alternativ|combien (co[uû]te|ça co[uû]te)|how much|looking for|je cherche|on cherche|"
                           r"recommend|recommand|conseill|which (tool|app|software)|quel (outil|logiciel)|cheaper|"
                           r"moins cher|switch(ing)? from|replace|remplacer", re.I)
JOURS_SIGNAUX = 30
MAX_SIGNAUX = 200
EXTRAIT = 300


def _fichier_signaux(eid: str):
    from app.config import DATA_ROOT
    return DATA_ROOT / "espaces" / eid / "signaux_reddit.json"


def signaux_reddit(eid: str) -> list:
    """Les signaux Reddit gardés de l'espace (30 jours), du plus récent au plus ancien ; [] si aucun ou illisible."""
    try:
        s = json.loads(_fichier_signaux(eid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    limite = (datetime.now(timezone.utc) - timedelta(days=JOURS_SIGNAUX)).isoformat()
    return [x for x in s if isinstance(x, dict) and str(x.get("collecte_le") or "") >= limite] if isinstance(s, list) else []


def _garder_signaux(eid: str, nouveaux: list) -> list:
    """Fusionne (doublon = même lien), garde 30 jours et 200 au plus ; rend les signaux réellement ajoutés."""
    gardes = signaux_reddit(eid)
    vus = {x.get("url") for x in gardes}
    ajoutes = [x for x in nouveaux if x.get("url") and x["url"] not in vus and not vus.add(x["url"])]
    tout = (ajoutes + gardes)[:MAX_SIGNAUX]
    f = _fichier_signaux(eid)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tout, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return ajoutes


async def _signaux(args: dict, items: list) -> dict:
    import asyncio
    eid = args.get("espace_id")
    if not eid:
        return {}
    requete = " | ".join(str(x) for x in ((args.get("entree") or {}).get("searches") or []) if isinstance(x, str))[:300]
    nouveaux = [l for l in lignes_veille("reddit", "", items, requete)
                if BESOIN_REDDIT.search(str(l.get("texte") or ""))]
    for l in nouveaux:
        l["texte"] = l["texte"][:EXTRAIT]
        l.pop("concurrent", None)
        l.pop("score", None)
    ajoutes = await asyncio.to_thread(_garder_signaux, eid, nouveaux)
    return {"signaux": len(ajoutes)}


async def traiter(but, cid: str, args: dict, items: list) -> dict:
    """Ce que le fait « terminee » de la carte porte en plus ; {} pour un but inconnu ou absent."""
    if but == "leads":
        return await _leads(cid, args, items)
    if but == "veille":
        return await _veille(args, items)
    if but == "signaux":
        return await _signaux(args, items)
    return {}
