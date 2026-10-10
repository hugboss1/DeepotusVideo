# -*- coding: utf-8 -*-
"""Le score de pertinence News (plan 2026-09-03, lot 1, tache 4 ; tache #33 du suivi).

Deuxieme etage, apres le filtre gratuit : ce qui a survecu recoit un score 0-100 — « ce sujet merite-t-il le reel
du jour ».

Ecart date (30/09/2026, decision de l'utilisateur) : le score est DETERMINISTE par defaut. Le LLM — payant — ne sert
que sur demande explicite (`llm=True`), et la route qui le demande passe d'abord par la garde des plafonds. Le plan
prevoyait « LLM quand il y a une cle » : ouvrir l'ecran News aurait depense sans le dire.

Garanties :
  1. sans `llm=True`, aucun fournisseur n'est appele ;
  2. avec `llm=True` : UN SEUL appel pour tout le lot ; s'il rend None, leve, ou rend un JSON illisible, le score
     deterministe prend la main — l'ecran reste trie ;
  3. un score est toujours dans [0, 100] et porte son origine et son motif ;
  4. `classer` ne leve jamais.
"""
import json
import unicodedata

from loguru import logger

from app.services.news_filter import jetons

EN_TETE_MAX = 5          # « les 3 a 5 meilleurs du jour en tete » (R8 P1)
LOT_MAX = 40             # articles envoyes au LLM en un appel
TITRE_MAX = 140

_SYSTEME = (
    "You score news headlines for a deep-sea themed crypto brand called "
    "deepotus, which publishes one short vertical video per day. Reply with "
    "JSON ONLY: a list of {\"id\": str, \"score\": int 0-100, \"pourquoi\": "
    "str}, one entry per headline given, no preamble, no code fence."
)


def jetons_llm(n: int) -> tuple[int, int]:
    """(entree, sortie) estimes pour un appel sur `n` articles — ce que la route chiffre AVANT de depenser."""
    n = max(0, min(int(n), LOT_MAX))
    return 250 + 45 * n, 200 + 40 * n


def _sans_accents(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def score_deterministe(item: dict, mots_du_brief: list[str]) -> tuple[int, str]:
    """Score sans fournisseur. Volontairement simple et STABLE : deux passages sur le meme flux rendent le meme
    nombre.

    Bareme, somme bornee a 100 :
      +18 par mot du brief present dans le titre ou le resume (plafond 54) ;
      +12 par media distinct ayant couvert le meme sujet — les `doublons` du dedoublonnage (plafond 24) : un sujet
          repris est un sujet qui compte ;
      +12 si l'article a un corps exploitable (au moins 40 jetons distincts) ;
      +10 de socle, pour qu'un article hors brief ne soit pas a zero.
    Brief d'abord (decision de l'utilisateur, 30/09/2026) : quand un brief est donne et que l'article n'en porte aucun
    mot, reprises et corps comptent pour MOITIE — mesure sur 8799 : deux reprises (+24) et un corps (+12) mettaient un
    article hors brief devant un article du brief (+18). A egalite, `classer` fait passer l'article du brief devant.
    """
    corpus = _sans_accents(f"{item.get('title', '')} {item.get('summary', '')} {item.get('essence', '')}")
    touches = [m for m in mots_du_brief if m and m in corpus]
    pts_mots = min(54, 18 * len(touches))
    reprises = len(item.get("doublons") or [])
    pts_reprises = min(24, 12 * reprises)
    corps = len(set(jetons(item.get("essence") or item.get("summary") or "")))
    pts_corps = 12 if corps >= 40 else 0
    hors_brief = bool(mots_du_brief) and not touches
    signaux = (pts_reprises + pts_corps) // 2 if hors_brief else pts_reprises + pts_corps
    total = min(100, 10 + pts_mots + signaux)
    bouts = []
    if touches:
        bouts.append("brief : " + ", ".join(touches[:3]))
    if reprises:
        bouts.append(f"{reprises} média(s) sur le même sujet")
    if pts_corps:
        bouts.append("article lisible")
    if hors_brief and signaux:
        bouts.append("hors brief : moitié des points")
    return total, " ; ".join(bouts) or "aucun signal, socle seulement"


def _mots_du_brief(brief: str) -> list[str]:
    vus, out = set(), []
    for m in jetons(brief or ""):          # jetons() rend deja sans accents et en minuscules
        if m and m not in vus:
            vus.add(m)
            out.append(m)
    return out


def _extraire_json(texte: str):
    """Le premier tableau JSON du texte, ou None. Un LLM qui entoure sa reponse d'explications ou d'une cloture en
    triples accents graves reste lisible."""
    if not texte:
        return None
    depart = texte.find("[")
    fin = texte.rfind("]")
    if depart < 0 or fin <= depart:
        return None
    try:
        d = json.loads(texte[depart:fin + 1])
    except json.JSONDecodeError:
        return None
    return d if isinstance(d, list) else None


def _scores_llm(items: list[dict], brief: str) -> tuple[dict, str]:
    """Rend ({id: (score, pourquoi)}, fournisseur) — ({}, "") si indisponible."""
    from app.services import summarizer
    lot = items[:LOT_MAX]
    lignes = "\n".join(f'- id={it.get("id")} | {str(it.get("title") or "")[:TITRE_MAX]}' for it in lot)
    prompt = (f"Brand brief: {brief or 'deep-sea crypto brand, community of traders'}"
              f"\n\nHeadlines:\n{lignes}\n\n"
              "Score each headline 0-100 for how much it deserves today's video.")
    try:
        brut, fournisseur = summarizer._chat_dispatch(prompt, _SYSTEME, jetons_llm(len(lot))[1])
    except Exception as e:  # noqa: BLE001 - un fournisseur ne casse pas l'ecran
        logger.warning(f"news_rank: dispatch en echec ({e}) - deterministe")
        return {}, ""
    if not brut:
        return {}, ""
    lu = _extraire_json(brut)
    if not lu:
        logger.warning("news_rank: reponse LLM illisible - deterministe")
        return {}, ""
    connus = {str(it.get("id")) for it in lot}
    out: dict = {}
    for ligne in lu:
        if not isinstance(ligne, dict):
            continue
        ident = str(ligne.get("id") or "")
        if ident not in connus:
            continue
        try:
            score = int(round(float(ligne.get("score"))))
        except (TypeError, ValueError, OverflowError):
            continue
        out[ident] = (max(0, min(100, score)), str(ligne.get("pourquoi") or "")[:200])
    return out, (fournisseur if out else "")


def classer(items: list[dict], *, brief: str = "", penalites: dict | None = None,
            llm: bool = False) -> list[dict]:
    """Rend une COPIE des articles, du meilleur au pire, chacun portant `score`, `score_origine`, `score_pourquoi`
    et `en_tete`. `llm=True` seulement quand l'utilisateur l'a demande ET que la garde des plafonds est passee.

    `penalites` : {source_id: points a retrancher} — rempli par la tache 8 (equilibre des sources)."""
    if not items:
        return []
    mots = _mots_du_brief(brief)
    llm_scores, fournisseur = _scores_llm(items, brief) if llm else ({}, "")
    penalites = penalites or {}
    sortie: list[dict] = []
    for it in items:
        copie = dict(it)
        ident = str(it.get("id"))
        if ident in llm_scores:
            score, pourquoi = llm_scores[ident]
            origine = fournisseur
        else:
            score, pourquoi = score_deterministe(it, mots)
            origine = "deterministe"
        try:
            malus = int(penalites.get(it.get("source_id"), 0))
        except (TypeError, ValueError):
            malus = 0
        if malus:
            pourquoi = f"{pourquoi} ; -{malus} source sur-représentée"
        copie["score"] = max(0, min(100, score - malus))
        copie["score_origine"] = origine
        copie["score_pourquoi"] = pourquoi
        copie["en_tete"] = False
        sortie.append(copie)
    # tri stable : score decroissant, puis le plus recent d'abord
    sortie.sort(key=lambda x: str(x.get("published") or ""), reverse=True)
    sortie.sort(key=lambda x: str(x.get("score_pourquoi") or "").startswith("brief :"), reverse=True)   # brief d'abord a egalite
    sortie.sort(key=lambda x: x["score"], reverse=True)
    for c in sortie[:EN_TETE_MAX]:
        c["en_tete"] = True
    return sortie
