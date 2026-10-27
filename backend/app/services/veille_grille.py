# -*- coding: utf-8 -*-
"""t352 (27/10/2026) — la grille de la veille (skill veille-concurrents, `references/grille.md`) appliquée SANS modèle,
et le rapport qu'on en tire (`references/rapport-modele.md`).

Le classement automatique est un lexique FR/EN : il ne dépense rien et se relit (le rapport le dit dans ses limites).
Une veille IMPORTÉE (classée à la main hors de l'app) garde son classement : `classer` ne reclasse pas une ligne qui a
déjà `theme` et `polarite`.

Règles du skill tenues ici : une tendance = au moins 3 auteurs distincts ; un angle de message seulement pour un thème
que l'app règle (`CHEZ_NOUS` statut « regle », écran à l'appui) ; une demande n'est jamais annoncée (« a_decider ») ;
citations courtes (une phrase, 200 caractères), sans auteur.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Iterable

THEMES = ("prix_credits", "qualite_sortie", "coherence", "controle", "vitesse_files", "censure_moderation",
          "droits_licence", "confidentialite_local", "flux_travail", "game_assets", "social_publication",
          "support_fiabilite", "apprentissage", "fournisseur_unique")
POLARITES = ("force", "faiblesse", "demande", "neutre")
MAX_CITATION = 200
MIN_AUTEURS = 3


def _rx(*mots: str) -> re.Pattern:
    return re.compile(r"(?<![\w])(?:" + "|".join(mots) + r")", re.I)


# Thème -> lexique (débuts de mots, FR et EN). Le thème retenu est celui qui a le plus de touches (égalité : l'ordre).
LEXIQUE: dict[str, re.Pattern] = {
    "prix_credits": _rx(r"credits?", r"crédits?", r"pric", r"prix", r"expensive", r"cher\b", r"chère", r"subscri",
                        r"abonnement", r"refund", r"rembours", r"billing", r"factur", r"charged", r"débité", r"paywall",
                        r"\$\d", r"\d+ ?€", r"cost", r"coût", r"money", r"argent", r"tokens?\b", r"plan\b"),
    "qualite_sortie": _rx(r"quality", r"qualité", r"artifact", r"artefact", r"blurr", r"flou", r"resolution",
                          r"résolution", r"hands?\b", r"mains?\b", r"distort", r"déform", r"output", r"rendu", r"médiocre",
                          r"looks? (fake|bad|weird)", r"realistic", r"réaliste", r"ugly", r"moche"),
    "coherence": _rx(r"consisten", r"inconsisten", r"cohéren", r"same character", r"même personnage",
                     r"changes between", r"change d'un", r"drift", r"identity", r"identité"),
    "controle": _rx(r"control", r"contrôl", r"camera", r"caméra", r"prompt adherence", r"edit only", r"inpaint",
                    r"keyframe", r"mise en scène", r"précis", r"precise"),
    "vitesse_files": _rx(r"queue", r"file d'attente", r"slow", r"lent", r"waiting", r"attente", r"rate limit",
                         r"takes forever", r"hours? to", r"heures? pour", r"outage", r"panne", r"down\b"),
    "censure_moderation": _rx(r"censor", r"censur", r"moderat", r"modérat", r"nsfw", r"filter", r"filtre",
                              r"refused", r"refus", r"flagged", r"policy violation", r"violates"),
    "droits_licence": _rx(r"copyright", r"droits? d'auteur", r"commercial use", r"usage commercial", r"licen",
                          r"ownership", r"propriété", r"training data", r"données d'entraînement"),
    "confidentialite_local": _rx(r"privacy", r"confidential", r"offline", r"hors ligne", r"\blocal", r"en local",
                                 r"cloud", r"my data", r"mes données", r"self.host"),
    "flux_travail": _rx(r"workflow", r"flux de travail", r"export", r"import", r"integrat", r"intégrat", r"premiere",
                        r"davinci", r"after effects", r"blender", r"plugin", r"collaborat", r"pipeline", r"timeline",
                        r"editing", r"montage"),
    # bornes de fin sur les mots courts : « rig » n'est pas « right », « unreal » n'est pas « unrealistic »
    "game_assets": _rx(r"sprite", r"tiles?\b", r"tileset", r"tuiles?\b", r"3d model", r"modèle 3d",
                       r"rig(?:s|ged|ging)?\b", r"unity\b", r"unreal(?: engine)?\b", r"godot\b", r"game assets?", r"assets? de jeu", r"texture", r"pixel art", r"gamedev"),
    "social_publication": _rx(r"tiktok", r"reels?\b", r"shorts\b", r"caption", r"sous-titre", r"subtitle",
                              r"schedul", r"planifi", r"post\b", r"publish", r"publier", r"clips?\b", r"viral"),
    "support_fiabilite": _rx(r"support", r"customer service", r"service client", r"crash", r"plant", r"bug",
                             r"broken", r"freez", r"stuck", r"bloqué", r"error", r"erreur", r"doesn'?t work",
                             r"not working", r"ne marche", r"fonctionne pas", r"banned", r"account", r"compte",
                             r"never (answer|respond|repl)", r"no response", r"aucune réponse", r"glitch", r"fail", r"échou",
                             r"won'?t (create|work|load|open|generate|export)", r"didn'?t work", r"never finish",
                             r"lag", r"network", r"réseau", r"loading", r"chargement", r"update", r"mise à jour"),
    "apprentissage": _rx(r"learning curve", r"courbe d'apprentissage", r"complicated", r"compliqué", r"confusing",
                         r"déroutant", r"hard to use", r"difficile", r"tutorial", r"tuto", r"documentation",
                         r"beginner", r"débutant", r"prise en main", r"intuitive", r"intuitif"),
    "fournisseur_unique": _rx(r"shut ?down", r"fermeture", r"discontinu", r"sunset", r"lock.?in", r"vendor",
                              r"only one model", r"un seul modèle", r"sora\b", r"dépendan"),
}

_DEMANDE = _rx(r"i wish", r"wish (they|it|you)", r"please add", r"would love", r"feature request", r"needs? (a|an|to add)",
               r"should add", r"add support", r"j'aimerais", r"il manque", r"ajoutez", r"ce serait bien",
               r"please (bring|make|let)")
_NEGATIF = _rx(r"expensive", r"pricey", r"overpriced", r"too much", r"waste", r"scam", r"refund", r"cancel",
               r"terrible", r"awful", r"\bbad\b", r"worst", r"broken", r"crash", r"bug", r"slow", r"never", r"useless",
               r"disappoint", r"frustrat", r"annoying", r"inconsisten", r"not consistent", r"changes between",
               r"burn", r"rip.?off", r"censor", r"blocked", r"doesn'?t work", r"not working", r"stuck", r"hate",
               r"horrible", r"garbage", r"trash", r"poor", r"lost", r"stole", r"no response", r"unusable",
               r"trop cher", r"cher\b", r"arnaque", r"rembours", r"\bnul", r"lent\b", r"plant", r"inutile", r"déçu",
               r"jamais", r"ne marche", r"fonctionne pas", r"bloqué", r"en fumée", r"résili", r"horrible", r"pire",
               r"volé", r"perdu", r"aucune réponse", r"fail", r"won'?t", r"didn'?t", r"sucks", r"lag",
               r"médiocre", r"greed", r"not free", r"can'?t", r"cannot", r"impossible", r"error", r"erreur",
               r"échou", r"pas gratuit", r"dommage", r"problème", r"problem", r"issue", r"ne peut", r"plus rien")
_POSITIF = _rx(r"love", r"amazing", r"great", r"awesome", r"\bbest", r"excellent", r"impressive", r"incredible",
               r"perfect", r"fantastic", r"beautiful", r"game.?changer", r"recommend", r"adore", r"génial", r"super\b",
               r"\btop\b", r"parfait", r"bluffant", r"magnifique", r"incroyable", r"bravo")
_COLERE = _rx(r"refund", r"scam", r"cancel", r"rip.?off", r"chargeback", r"fraud", r"stole", r"uninstall",
              r"rembours", r"arnaque", r"résili", r"désabonn", r"escroc", r"volé", r"désinstall")
_FORT = _rx(r"terrible", r"awful", r"worst", r"useless", r"waste", r"never", r"frustrat", r"hate", r"horrible",
            r"garbage", r"unusable", r"nul\b", r"inutile", r"déçu", r"pire", r"jamais", r"way too", r"beaucoup trop")

# Ce que DeepotusVideoGen oppose, thème par thème. « regle » seulement avec un écran à l'appui (grille.md).
CHEZ_NOUS: dict[str, dict] = {
    "prix_credits": {"statut": "regle",
                     "preuve": {"fr": "Réglages › Dépenses : coût affiché avant de cliquer, plafonds, vos clés au prix coûtant",
                                "en": "Settings › Spending: cost shown before you click, caps, your own keys at cost"},
                     "angle": {"fr": "Vous voyez le prix avant de cliquer, et vous fixez votre plafond.",
                               "en": "You see the price before you click, and you set your own cap."}},
    "qualite_sortie": {"statut": "inconnu", "preuve": None, "angle": None},
    "coherence": {"statut": "partiel",
                  "preuve": {"fr": "Espaces de marque : persona, produits et références réutilisés",
                             "en": "Brand spaces: persona, products and references reused"}, "angle": None},
    "controle": {"statut": "partiel",
                 "preuve": {"fr": "Studio et Montage : édition plan par plan", "en": "Studio and Editing: shot-by-shot editing"},
                 "angle": None},
    "vitesse_files": {"statut": "inconnu", "preuve": None, "angle": None},
    "censure_moderation": {"statut": "inconnu", "preuve": None, "angle": None},
    "droits_licence": {"statut": "inconnu", "preuve": None, "angle": None},
    "confidentialite_local": {"statut": "regle",
                              "preuve": {"fr": "Projets et Bibliothèque enregistrés sur votre PC",
                                         "en": "Projects and Library stored on your PC"},
                              "angle": {"fr": "Vos projets restent chez vous : rien n'est hébergé chez nous.",
                                        "en": "Your projects stay with you: nothing is hosted by us."}},
    "flux_travail": {"statut": "regle",
                     "preuve": {"fr": "Montage complet et « Envoyer vers » entre les labs",
                                "en": "Full Editing and “Send to” between labs"},
                     "angle": {"fr": "Du prompt au montage dans la même app, sans aller-retour entre outils.",
                               "en": "From prompt to final cut in one app, no back-and-forth between tools."}},
    "game_assets": {"statut": "regle",
                    "preuve": {"fr": "Spritelab, Tilelab, Établi 3D : exports Godot, Unity, Unreal, Blender",
                               "en": "Spritelab, Tilelab, 3D Workbench: Godot, Unity, Unreal, Blender exports"},
                    "angle": {"fr": "Sprites, tuiles et 3D prêts pour votre moteur de jeu.",
                              "en": "Sprites, tiles and 3D ready for your game engine."}},
    "social_publication": {"statut": "regle",
                           "preuve": {"fr": "Planificateur : calendrier, canaux, multi-comptes par espace",
                                      "en": "Scheduler: calendar, channels, multiple accounts per space"},
                           "angle": {"fr": "Créez, sous-titrez et planifiez vos posts au même endroit.",
                                     "en": "Create, caption and schedule your posts in one place."}},
    "support_fiabilite": {"statut": "inconnu", "preuve": None, "angle": None},
    "apprentissage": {"statut": "inconnu", "preuve": None, "angle": None},
    "fournisseur_unique": {"statut": "regle",
                           "preuve": {"fr": "Plusieurs fournisseurs au choix (fal, OpenAI, ElevenLabs…), modèle par tâche",
                                      "en": "Several providers to choose from (fal, OpenAI, ElevenLabs…), model per task"},
                           "angle": {"fr": "Si un modèle ferme, vous passez à un autre : l'app ne dépend d'aucun.",
                                     "en": "If a model shuts down, switch to another: the app depends on none."}},
}


def _note(l: dict) -> int | None:
    if str(l.get("source") or "").startswith("appstore") and isinstance(l.get("score"), (int, float)):
        return int(l["score"])
    return None


def classer(l: dict) -> dict:
    """La ligne plus `theme`, `polarite`, `intensite`, `chez_nous`, `classement` ; une ligne déjà classée est gardée."""
    out = dict(l)
    if out.get("theme") in THEMES and out.get("polarite") in POLARITES:
        out["intensite"] = out.get("intensite") if out.get("intensite") in (1, 2, 3) else 1
        out["chez_nous"] = out.get("chez_nous") or CHEZ_NOUS[out["theme"]]["statut"]
        out["classement"] = "importe"
        return out
    texte = str(out.get("texte") or "")
    touches = {t: len(rx.findall(texte)) for t, rx in LEXIQUE.items()}
    meilleur = max(touches.values()) if touches else 0
    theme = next((t for t in THEMES if touches[t] == meilleur), None) if meilleur else None
    neg, pos = len(_NEGATIF.findall(texte)), len(_POSITIF.findall(texte))
    note = _note(out)
    if theme is None:
        polarite = "neutre"
    elif _DEMANDE.search(texte):
        polarite = "demande"
    elif note is not None and note <= 2:
        polarite = "faiblesse"
    elif note is not None and note >= 4 and neg <= pos:
        polarite = "force"
    elif note == 3 and neg:
        polarite = "faiblesse"
    elif neg > pos:
        polarite = "faiblesse"
    elif pos > neg:
        polarite = "force"
    else:
        polarite = "neutre"
    if _COLERE.search(texte) and polarite == "faiblesse":
        intensite = 3
    elif polarite == "faiblesse" and (_FORT.search(texte) or neg >= 3 or note == 1):
        intensite = 2
    else:
        intensite = 1
    out.update(theme=theme, polarite=polarite, intensite=intensite,
               chez_nous=CHEZ_NOUS[theme]["statut"] if theme else "inconnu", classement="auto")
    return out


def _citation(l: dict) -> dict:
    t = re.sub(r"\s+", " ", str(l.get("texte") or "")).strip()
    phrase = re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0]
    if len(phrase) > MAX_CITATION:
        phrase = phrase[:MAX_CITATION - 1].rstrip() + "…"
    return {"texte": phrase, "url": l.get("url"), "date": str(l.get("date") or "")[:10], "source": l.get("source"),
            "concurrent": l.get("concurrent")}


def _auteur(l: dict) -> str:
    return l.get("auteur_hash") or f"url:{l.get('url')}"


def _meilleures(lignes: list[dict], n: int) -> list[dict]:
    tri = sorted(lignes, key=lambda l: (-(l.get("intensite") or 1), -(l.get("score") or 0) if isinstance(l.get("score"), (int, float)) else 0))
    vus, out = set(), []
    for l in tri:
        c = _citation(l)
        if c["texte"] and c["texte"] not in vus:
            vus.add(c["texte"])
            out.append(c)
        if len(out) >= n:
            break
    return out


def rapport(verbatims: Iterable[dict], meta: dict) -> dict:
    """Le rapport (schéma version 1) des verbatims déjà classés."""
    tous = list(verbatims)
    gardes = [l for l in tous if l.get("polarite") in ("force", "faiblesse", "demande") and l.get("theme") in THEMES]
    par_source = Counter(str(l.get("source") or "").split("-")[0] for l in gardes)
    par_concurrent = Counter(l.get("concurrent") for l in gardes)
    dates = sorted(str(l.get("date"))[:10] for l in gardes if l.get("date"))
    matrice: dict = defaultdict(lambda: defaultdict(lambda: {"f": 0, "F": 0, "_i": []}))
    for l in gardes:
        cel = matrice[l.get("concurrent")][l["theme"]]
        if l["polarite"] == "faiblesse":
            cel["f"] += 1
            cel["_i"].append(l.get("intensite") or 1)
        elif l["polarite"] == "force":
            cel["F"] += 1
    matrice_out = {c: {t: {"f": v["f"], "F": v["F"], "i": round(sum(v["_i"]) / len(v["_i"]), 1) if v["_i"] else 0}
                       for t, v in th.items()} for c, th in matrice.items()}

    def groupes(polarite: str) -> dict[str, list[dict]]:
        g: dict[str, list[dict]] = defaultdict(list)
        for l in gardes:
            if l["polarite"] == polarite:
                g[l["theme"]].append(l)
        return g

    douleurs = []
    for theme, ls in groupes("faiblesse").items():
        auteurs = len({_auteur(l) for l in ls})
        if auteurs < MIN_AUTEURS:
            continue
        cn = CHEZ_NOUS[theme]
        douleurs.append({"theme": theme, "n": len(ls), "n3": sum(1 for l in ls if l.get("intensite") == 3),
                         "auteurs": auteurs, "concurrents": [c for c, _ in Counter(l.get("concurrent") for l in ls).most_common()],
                         "citations": _meilleures(ls, 3), "chez_nous": cn["statut"], "preuve": cn["preuve"]})
    douleurs.sort(key=lambda d: (-d["n"], THEMES.index(d["theme"])))
    angles = [{"theme": d["theme"], "n": d["n"], "preuve": CHEZ_NOUS[d["theme"]]["preuve"],
               "angle": CHEZ_NOUS[d["theme"]]["angle"]} for d in douleurs if CHEZ_NOUS[d["theme"]]["statut"] == "regle"]
    forces = sorted(({"theme": t, "n": len(ls), "concurrents": [c for c, _ in Counter(l.get("concurrent") for l in ls).most_common(5)],
                      "citations": _meilleures(ls, 1)} for t, ls in groupes("force").items()),
                    key=lambda f: (-f["n"], THEMES.index(f["theme"])))[:8]
    demandes = sorted(({"theme": t, "n": len(ls), "auteurs": len({_auteur(l) for l in ls}), "citations": _meilleures(ls, 2),
                        "chez_nous": CHEZ_NOUS[t]["statut"], "statut": "a_decider"}
                       for t, ls in groupes("demande").items() if CHEZ_NOUS[t]["statut"] != "regle"),
                      key=lambda d: (-d["n"], THEMES.index(d["theme"])))
    importe = any(l.get("classement") == "importe" for l in gardes)
    auto = any(l.get("classement") != "importe" for l in gardes)
    limites = list(meta.get("limites") or [])
    if auto:
        limites.append("classement automatique par mots-clés : à relire avant de citer")
    if gardes and par_source.get("appstore", 0) > 0.6 * len(gardes):
        limites.append("corpus dominé par les avis App Store : plaintes de facturation mobile sur-représentées")
    if 0 < len(gardes) < 100:
        limites.append(f"volume faible ({len(gardes)} verbatims gardés)")
    return {"version": 1, "date": meta.get("date"), "espace_id": meta.get("espace_id"),
            "classement": "importe" if importe and not auto else "auto",
            "volumes": {"brut": meta.get("brut", len(tous)), "gardes": len(gardes), "par_source": dict(par_source),
                        "par_concurrent": dict(par_concurrent.most_common()),
                        "periode": [dates[0], dates[-1]] if dates else None},
            "matrice": matrice_out, "douleurs": douleurs[:10], "angles": angles, "forces": forces,
            "demandes": demandes, "limites": limites}
