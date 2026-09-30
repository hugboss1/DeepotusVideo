# -*- coding: utf-8 -*-
"""Les tendances locales, et le signal X borne (plan 2026-09-03 T14, tache #35 du suivi, 30/09/2026).

La tendance de base ne coute rien : un sujet cite par au moins SOURCES_MIN medias DISTINCTS le MEME JOUR est chaud.
Ecart date (mesure, 30/09) : le rafraichissement FOND deja les reprises (`news_filter.dedoublonner`) — le cache porte un
article par sujet et ses `doublons`. Les medias d'un article sont donc sa source PLUS ses doublons ; les articles non
fondus restent regroupes par `titres_presque_identiques` (la meme fonction, pas une copie de ses seuils).

Google Trends est ECARTEE (API en alpha sur candidature). Le signal X ne part que sur demande (decision de
l'utilisateur, 30/09) : trois appels par jour au plus, jamais sans cle X, et chaque post LU est compte dans le quota
mensuel `x_lecture` (100/mois au palier gratuit — mesure : une recherche rend 10 posts au minimum, donc un appel peut
couter 10 lectures). Le budget du jour est tenu sur le disque : un redemarrage n'offre pas un second quota.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services import quota
from app.services.news_filter import titres_presque_identiques

SOURCES_MIN = 3            # medias distincts pour qu'un sujet soit « tendance »
APPELS_PAR_JOUR = 3        # appels X par jour au plus
POSTS_PAR_APPEL = 10       # max_results minimal de search_recent_tweets : un appel peut lire 10 posts
MOTIF_JOUR = "limite du jour atteinte : 3 lectures du signal X par jour"
MOTIF_CLE = "aucune cle X configuree (Reglages -> Connected accounts)"


def chemin_budget() -> Path:
    d = settings.outputs_path.parent / "news"
    d.mkdir(parents=True, exist_ok=True)
    return d / "budget_x.json"


def _jour(quand: str | None) -> str:
    if quand:
        try:
            return datetime.fromisoformat(str(quand)).date().isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).date().isoformat()


def _medias(item: dict) -> set:
    """Les medias d'un article : sa source et celles de ses doublons fondus (par nom, en minuscules)."""
    out = set()
    for nom in [item.get("source_name") or item.get("source_id")] + [
            d.get("source_name") for d in (item.get("doublons") or []) if isinstance(d, dict)]:
        nom = " ".join(str(nom or "").split()).lower()
        if nom:
            out.add(nom)
    return out


def marquer_tendances(items: list[dict]) -> list[dict]:
    """Rend une COPIE des articles portant `tendance` (bool) et `tendance_sources` (medias distincts du groupe).
    Le regroupement est par jour de publication : trois medias sur trois jours, c'est un feuilleton."""
    groupes: list[dict] = []
    for k, it in enumerate(items):
        titre = str(it.get("title") or "")
        jour = str(it.get("published") or "")[:10]
        for g in groupes:
            if g["jour"] == jour and titres_presque_identiques(titre, g["titre"]):
                g["membres"].append(k)
                g["medias"] |= _medias(it)
                break
        else:
            groupes.append({"titre": titre, "jour": jour, "membres": [k], "medias": _medias(it)})
    n_de: dict = {}
    for g in groupes:
        n = len(g["medias"])
        for k in g["membres"]:
            n_de[k] = n if n >= SOURCES_MIN else 0
    sortie = []
    for k, it in enumerate(items):
        copie = dict(it)
        copie["tendance"] = bool(n_de.get(k))
        copie["tendance_sources"] = n_de.get(k, 0)
        sortie.append(copie)
    return sortie


def _lire_budget() -> dict:
    p = chemin_budget()
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    return d if isinstance(d, dict) else {}


def _ecrire_budget(d: dict) -> None:
    p = chemin_budget()
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _lire_x(requete: str) -> dict:
    """UNE recherche X (posts des 7 derniers jours). Remplacee par le banc ; en production, le client tweepy de la
    publication."""
    from app.services.marketing import _x_client
    r = _x_client().search_recent_tweets(query=requete, max_results=POSTS_PAR_APPEL)
    return {"posts": len(getattr(r, "data", None) or [])}


def signal_x(requete: str, *, quand: str | None = None) -> dict:
    """Rend {posts, restant_jour, quota, motif}. `posts` vaut None quand rien n'a ete lu. Ordre : cle, quota
    mensuel (il faut POSTS_PAR_APPEL lectures devant soi), limite du jour ; l'appel du jour est decompte AVANT
    (un echec qui se repete ne vide pas le jour en silence), les posts lus APRES dans `x_lecture`."""
    jour = _jour(quand)
    now = datetime.fromisoformat(f"{jour}T12:00:00")
    budget = _lire_budget()
    utilise = int(budget.get(jour, 0) or 0)
    base = {"posts": None, "restant_jour": max(0, APPELS_PAR_JOUR - utilise)}
    if not settings.has_x:
        return dict(base, quota=quota.check("x_lecture", now)[1], motif=MOTIF_CLE)
    lim = quota.LIMITS["x_lecture"][1]
    deja = quota.used("x_lecture", now)
    if deja + POSTS_PAR_APPEL > lim:
        return dict(base, quota=f"{deja}/{lim}",
                    motif=f"quota x_lecture : {deja}/{lim} ce mois, un appel peut lire {POSTS_PAR_APPEL} posts "
                          f"({quota.LIMITS['x_lecture'][2]})")
    if utilise >= APPELS_PAR_JOUR:
        return dict(base, quota=f"{deja}/{lim}", motif=MOTIF_JOUR)
    _ecrire_budget({jour: utilise + 1})          # une seule journee gardee
    restant = APPELS_PAR_JOUR - (utilise + 1)
    try:
        lu = _lire_x(requete)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"news_trends: lecture X en echec ({e})")
        return {"posts": None, "restant_jour": restant, "quota": f"{deja}/{lim}", "motif": str(e)[:200]}
    posts = max(0, int(lu.get("posts") or 0))
    if posts:
        quota.count("x_lecture", now, n=posts)
    return {"posts": posts, "restant_jour": restant, "quota": f"{deja + posts}/{lim}", "motif": ""}
