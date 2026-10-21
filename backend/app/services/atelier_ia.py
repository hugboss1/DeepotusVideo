"""Atelier sonore — nœuds IA posés sur une plage (t272, 21/10/2026, plan 2026-10-21-optimisation-menus-son-vfx.md).

Le registre des modèles qu'un nœud IA de l'Atelier peut tirer, relevé sur le catalogue fal en direct le 21/10/2026
(schéma openapi « queue » de chaque endpoint, prix affiché sur la page du modèle). Seuls les gestes qu'un modèle
accepte VRAIMENT (un audio d'entrée, une plage, une continuation) sont livrés :
  prolonger  continuation au bout de la piste    Stable Audio 3 Medium (audio-outpainting), ACE-Step (audio-outpaint)
  regenerer  inpainting d'une plage               Stable Audio 3 Medium (audio-inpainting), Stable Audio 2.5 (inpaint),
                                                  ACE-Step (audio-inpaint)
  variation  audio → audio, force réglable        Stable Audio 3 Medium (init_noise_level), Stable Audio 2.5 (strength)
  sfx        bruitage décrit, posé sur la plage   les modèles TEXTE du registre des bruitages passant par fal
                                                  (sfx_service.SFX_MODELS ; ElevenLabs direct n'est pas une requête fal)
ÉCARTÉS : « ajouter une couche instrumentale » (aucun modèle du catalogue ne rend une piste SEULE accordée à un audio
d'entrée : audio-to-audio rend le mélange, text-to-audio ignore le tempo et la tonalité de la piste) ; ACE-Step
audio-to-audio (exige les balises et la graine d'ORIGINE du morceau, inconnues pour un fichier importé).
Les modèles de MUSIC_MODELS sont tous texte → musique : aucun n'accepte un audio d'entrée.

Prix : « gen » = par génération (la page fal dit « per audio ») ; « s » = par seconde d'audio GÉNÉRÉ (ACE-Step,
0,0002 $), chiffré sur une borne prudente (fenêtre envoyée la plus longue possible). Un id inconnu ne se chiffre pas.
Les appels au fournisseur passent par trois coutures (`_envoyer`, `_appeler`, `_telecharger`) que les bancs
remplacent ; les refus sont des ValueError au message français (traduits à la sortie par i18n_l10_erreurs).
"""
from __future__ import annotations

import math

from app.config import settings
from app.services import sfx_service as SX

OPS = ("prolonger", "regenerer", "variation", "sfx")
CONTEXTE_S = 15.0          # secondes de piste envoyées autour d'une plage (régénérer) ou avant la fin (prolonger)
PLAGE_MIN_S = 1.0
PROMPT_MAX = 450


def _f(op, label, endpoint, usd, unite, max_s, champs, fixe=None, ext_max=None, entier=False):
    return {"op": op, "label": label, "endpoint": endpoint, "usd": usd, "unite": unite, "max_s": max_s,
            "ext_max": ext_max, "champs": champs, "fixe": dict(fixe or {}), "entier": entier}


# ORDRE = ordre du sélecteur ; le premier modèle d'une opération est son défaut.
MODELES: dict[str, dict] = {
    "sa3-prolonger": _f("prolonger", "Stable Audio 3 Medium", "fal-ai/stable-audio-3/medium/audio-outpainting",
                        0.0446, "gen", 380.0, {"prompt": "prompt", "seed": "seed", "apres": "extend_seconds_after"},
                        ext_max=120.0),
    "ace-prolonger": _f("prolonger", "ACE-Step", "fal-ai/ace-step/audio-outpaint", 0.0002, "s", 240.0,
                        {"prompt": "tags", "seed": "seed", "apres": "extend_after_duration"},
                        {"extend_before_duration": 0}, ext_max=107.0),
    "sa3-regenerer": _f("regenerer", "Stable Audio 3 Medium", "fal-ai/stable-audio-3/medium/audio-inpainting",
                        0.0442, "gen", 380.0, {"prompt": "prompt", "seed": "seed", "debut": "mask_start_seconds",
                                               "fin": "mask_end_seconds"}),
    "sa25-regenerer": _f("regenerer", "Stable Audio 2.5", "fal-ai/stable-audio-25/inpaint", 0.20, "gen", 190.0,
                         {"prompt": "prompt", "seed": "seed", "debut": "mask_start", "fin": "mask_end",
                          "total": "seconds_total"}, entier=True),
    "ace-regenerer": _f("regenerer", "ACE-Step", "fal-ai/ace-step/audio-inpaint", 0.0002, "s", 240.0,
                        {"prompt": "tags", "seed": "seed", "debut": "start_time", "fin": "end_time"}),
    "sa3-variation": _f("variation", "Stable Audio 3 Medium", "fal-ai/stable-audio-3/medium/audio-to-audio",
                        0.0417, "gen", 380.0, {"prompt": "prompt", "seed": "seed", "force": "init_noise_level",
                                               "total": "duration"}),
    "sa25-variation": _f("variation", "Stable Audio 2.5", "fal-ai/stable-audio-25/audio-to-audio", 0.20, "gen", 190.0,
                         {"prompt": "prompt", "seed": "seed", "force": "strength", "total": "total_seconds"},
                         entier=True),
}
DEFAUT_SFX = "sonilo-1.1"      # prix connu (0,0018 $/s) ; les autres bruitages fal sont « à mesurer »


def ids_sfx() -> list[str]:
    return [k for k, e in SX.SFX_MODELS.items() if e["nature"] == SX.SFX_TEXTE and e["voie"] == "fal"]


def ids(op: str) -> list[str]:
    return ids_sfx() if op == "sfx" else [k for k, e in MODELES.items() if e["op"] == op]


def defaut(op: str) -> str:
    return DEFAUT_SFX if op == "sfx" else ids(op)[0]


def label(op: str, mid: str) -> str:
    return SX.SFX_MODELS[mid]["label"] if op == "sfx" else MODELES[mid]["label"]


def plage_max(op: str, mid: str) -> float:
    """La plus longue plage (ou prolongation) qu'un modèle accepte."""
    if op == "sfx":
        b = SX.SFX_MODELS[mid].get("bornes")
        return float(b[1]) if b else 22.0
    e = MODELES[mid]
    return float(e["ext_max"] if op == "prolonger" else e["max_s"])


def verifier_modele(op: str, mid) -> str:
    """L'id retenu (vide = le défaut de l'opération) ; ValueError s'il n'appartient pas à cette opération."""
    m = str(mid or "").strip() or defaut(op)
    if m not in ids(op):
        raise ValueError(f"modèle inconnu pour « {op} » : {m} (connus : {', '.join(ids(op))})")
    return m


def catalogue() -> dict:
    """Pour l'inspecteur : par opération, le défaut et les modèles (prix, unité, clé, disponibilité). Un modèle sans
    clé reste listé et choisissable (décision du 11/10/2026) : le tir est refusé en 503 au lancement."""
    from app.services import pricing
    dispo = bool(str(settings.FAL_KEY or "").strip())
    out = {}
    for op in OPS:
        mods = []
        for mid in ids(op):
            if op == "sfx":
                e = SX.SFX_MODELS[mid]
                usd, unite = pricing.taux_sfx(mid), e["unite"]
            else:
                e = MODELES[mid]
                usd, unite = e["usd"], e["unite"]
            mods.append({"id": mid, "label": label(op, mid), "usd": usd, "unite": unite,
                         "max_s": plage_max(op, mid), "note": "" if usd else "a_mesurer", "cle": "FAL_KEY",
                         "dispo": dispo})
        out[op] = {"defaut": defaut(op), "modeles": mods}
    return out


def secondes_facturees(op: str, mid: str, p: dict) -> float:
    """La borne prudente de l'audio GÉNÉRÉ (modèles à la seconde) : la fenêtre la plus longue que la génération
    enverra, plus la prolongation."""
    e = MODELES[mid]
    if op == "prolonger":
        return min(e["max_s"], CONTEXTE_S) + float(p["secondes"])
    long = float(p["fin"]) - float(p["debut"])
    if op == "regenerer":
        return min(e["max_s"], long + 2 * CONTEXTE_S)
    return long


def cout(op: str, mid: str, p: dict) -> dict:
    """L'op de devis d'un nœud : `atelier_ia` pour les modèles de ce registre, `sfx` pour un bruitage (même devis que
    la page SFX). Lu par /devis ET par la garde des plafonds : une seule source."""
    if op == "sfx":
        return {"kind": "sfx", "modele": mid, "duration_s": round(float(p["fin"]) - float(p["debut"]), 3)}
    return {"kind": "atelier_ia", "modele": mid, "secondes": round(secondes_facturees(op, mid, p), 3)}


def ligne(op_devis: dict) -> dict:
    """UNE ligne de pricing.estimate pour le kind « atelier_ia »."""
    from app.i18n import Message, Nom
    from app.services.pricing import _line
    mid = str(op_devis.get("modele") or "")
    e = MODELES.get(mid)
    if e is None:
        return _line("fal", f"Atelier IA : modèle inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    lib = Message("pricing.atelier_ia." + e["op"], modele=Nom(mid, e["label"]))
    if e["unite"] == "s":
        try:
            sec = max(0.0, float(op_devis.get("secondes") or 0))
        except (TypeError, ValueError):
            sec = 0.0
        return _line("fal", Message("pricing.ligne_sec", label=lib, sec=f"{sec:g}", n=1), sec, "s", sec * e["usd"])
    return _line("fal", lib, 1, "gen", float(e["usd"]))


def requete(op: str, mid: str, p: dict, fen: dict, url: str | None) -> tuple[str, dict]:
    """(endpoint, arguments) d'un nœud IA. `fen` décrit ce qui part : {long (s), debut, fin (relatifs à la fenêtre)}.
    Seuls les champs que le schéma du modèle nomme partent ; la graine = la prise (une autre prise, un autre tirage)."""
    if op == "sfx":
        return SX.build_request(mid, p["prompt"], round(float(p["fin"]) - float(p["debut"]), 3))
    e = MODELES[mid]
    ch = e["champs"]
    args = dict(e["fixe"])
    args["audio_url"] = url
    args[ch["prompt"]] = str(p["prompt"])[:PROMPT_MAX]
    args[ch["seed"]] = int(p["prise"])
    if op == "prolonger":
        args[ch["apres"]] = float(p["secondes"])
    elif op == "regenerer":
        a, b = fen["debut"], fen["fin"]
        if e["entier"]:
            args[ch["debut"]], args[ch["fin"]] = int(math.floor(a)), int(math.ceil(b))
        else:
            args[ch["debut"]], args[ch["fin"]] = round(a, 3), round(b, 3)
        if ch.get("total"):
            args[ch["total"]] = int(math.ceil(fen["long"] - 1e-6))
    else:
        args[ch["force"]] = round(float(p["force"]), 3)
        args[ch["total"]] = int(math.ceil(fen["long"] - 1e-6)) if e["entier"] else round(fen["long"], 3)
    return e["endpoint"], args


def url_audio(res) -> str:
    """L'URL du son rendu, quel que soit le nom du champ (`audio`, `audio_file`, `audio_url`…)."""
    from app.services import music_service as MU
    try:
        return MU._audio_url(res)
    except MU.MusicError as e:
        raise RuntimeError(str(e.message)) from e


async def _envoyer(chemin) -> str:                      # couture
    return await SX._upload(chemin)


async def _appeler(endpoint: str, args: dict) -> dict:   # couture
    return await SX._fal_subscribe(endpoint, args)


async def _telecharger(url: str, dest) -> None:          # couture
    await SX._download(url, dest)
