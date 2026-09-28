# -*- coding: utf-8 -*-
"""Scènes « Seedance (animated) » d'un épisode narré (P1 #6, lot A, 28/09/2026).

Jusqu'ici `run_episode` rendait toute scène en Ken Burns (« v1 fallback ») :
l'interface proposait Seedance, rien ne l'appelait. Ce module PLANIFIE les
clips à générer — pur, sans réseau — pour que la route (devis + garde de coût),
la pipeline (génération) et `cost_meta` (facturation) lisent la même chose.

Décisions de l'utilisateur (28/09) :
  - clip COURT : la plus petite durée native du modèle, après le plafond
    `video_max_gen_s` — puis BOUCLÉ à la durée de la narration (ffmpeg) ;
  - modèle et résolution PAR SCÈNE ; défaut = modèle global, PLUS BASSE
    résolution du modèle (une résolution inconnue du modèle retombe aussi sur
    la plus basse, jamais sur la plus chère) ;
  - un échec de génération replie la scène en Ken Burns (pipeline).
"""
from app.services import pricing as _pricing
from app.services.fal_service import resolve_video_model


def est_seedance(scene: dict) -> bool:
    """Scène animée par un modèle vidéo : motion seedance ET une illustration."""
    return (isinstance(scene, dict) and (scene.get("motion") or "") == "seedance"
            and bool(scene.get("image_filename")))


def resolution_de(model: dict, demandee: str | None) -> str | None:
    """La résolution demandée si le modèle l'a, sinon sa PLUS BASSE ; None
    quand l'endpoint n'a pas de paramètre de résolution."""
    res = model.get("resolutions")
    if not res:
        return None
    return demandee if demandee in res else res[0]


def plan_videos(scenes: list) -> list[dict]:
    """Un clip par scène Seedance illustrée, dans l'ordre des scènes.

    -> [{index, model, resolution, duration_s, prompt}] ; `duration_s` est la
    durée GÉNÉRÉE (facturée). Un modèle inconnu lève ValueError (la route en
    fait un 400 qui liste les modèles)."""
    out: list[dict] = []
    for i, sc in enumerate(scenes or []):
        if not est_seedance(sc):
            continue
        m = resolve_video_model((sc.get("video_model") or "").strip() or None)
        dur = _pricing.video_gen_seconds(m["id"], min(m["durations"]))
        prompt = ((sc.get("illustration_prompt") or "").strip()
                  or (sc.get("text") or "").strip())[:1500]
        out.append({"index": i, "model": m["id"],
                    "resolution": resolution_de(m, (sc.get("resolution") or "").strip() or None),
                    "duration_s": dur, "prompt": prompt})
    return out


def video_ops(plan: list[dict]) -> list[dict]:
    """Les ops `estimate` des clips planifiés (une par scène)."""
    return [{"kind": "seedance", "model": c["model"], "n": 1,
             "resolution": c["resolution"] or "1080p",
             "duration_s": c["duration_s"]} for c in plan]


def devis(scenes: list) -> dict:
    """{total_usd, scenes:[{scene (1-based), model, resolution, duration_s, usd}]}."""
    plan = plan_videos(scenes)
    lignes = []
    for c, op in zip(plan, video_ops(plan)):
        usd = _pricing.estimate(op)["total_usd"]
        lignes.append({"scene": c["index"] + 1, "model": c["model"],
                       "resolution": c["resolution"], "duration_s": c["duration_s"],
                       "usd": usd})
    return {"total_usd": round(sum(l["usd"] for l in lignes), 4), "scenes": lignes}
