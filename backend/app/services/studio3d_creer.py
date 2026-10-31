# -*- coding: utf-8 -*-
"""t389 (31/10/2026) — l'onglet 3D de Game Assets devient « Créer » : il ne fait plus que GÉNÉRER le modèle de base
(D1) ; tout le reste se fait dans le 3D Studio.

Relevé de Sorceress (Create) : plusieurs modèles cochés = un job par modèle ; modes Image, Texte et Multi-images
(« Drop multiple images to batch-generate a separate 3D model for each one ») ; quantité 1 à 4 ; réglages par
modèle ; total estimé avant de générer. Ce module est PUR : il valide une demande et en compose les tirs et le devis.
La route (studio3d_routes) garde l'ordre des refus de toute dépense : 400 → 503 clé → 409 `confirme_cout` → plafond
sur le TOTAL → une garde par tir.
"""
from __future__ import annotations

from pathlib import Path

MODES = ("image", "texte", "multi")
QUANTITE_MAX = 4
TIRS_MAX = 24            # garde-fou : 6 moteurs × 4 images, au-delà c'est une erreur de saisie, pas une demande


def valider(body: dict, images_dir: Path) -> dict:
    """La demande normalisée, ou ValueError (→ 400) avec un message lisible."""
    from app.services import moteurs3d_neufs as M
    from app.services.asset3d_service import ENGINES
    b = body or {}
    mode = str(b.get("mode") or "image").lower()
    if mode not in MODES:
        raise ValueError(f"mode inconnu : {mode!r}")
    moteurs = []
    for m in b.get("moteurs") or []:
        m = str(m or "").strip().lower()
        if m not in ENGINES:
            raise ValueError(f"moteur 3D inconnu : {m!r}")
        if m not in moteurs:
            moteurs.append(m)
    if not moteurs:
        raise ValueError("coche au moins un modèle")
    try:
        quantite = int(b.get("quantite") or 1)
    except (TypeError, ValueError):
        raise ValueError("quantité : un entier de 1 à 4")
    if not 1 <= quantite <= QUANTITE_MAX:
        raise ValueError("quantité : de 1 à 4")
    prompt = str(b.get("prompt") or "").strip()
    images: list[str] = []
    if mode == "texte":
        if not prompt:
            raise ValueError("le mode texte demande une description")
        sans = [ENGINES[m]["label"] for m in moteurs if not ENGINES[m].get("texte")]
        if sans:
            raise ValueError("ces modèles ne génèrent pas depuis un texte : " + ", ".join(sans))
        images = [""]
    else:
        brut = b.get("images") or ([b.get("image_filename")] if b.get("image_filename") else [])
        for fn in brut:
            n = Path(str(fn or "")).name
            if not n or not (images_dir / n).is_file():
                raise ValueError(f"image introuvable dans la Bibliothèque : {fn!r}")
            if n not in images:
                images.append(n)
        if not images:
            raise ValueError("choisis une image source")
        if mode == "image" and len(images) > 1:
            raise ValueError("le mode image prend une seule image ; le mode multi-images en prend plusieurs")
    reglages = {}
    for m, r in (b.get("reglages") or {}).items():
        if m in moteurs and m in M.MOTEURS:
            reglages[m] = M.valider(m, r)
    pose = str(b.get("pose") or "")
    if pose not in ("", "t-pose", "a-pose"):
        raise ValueError(f"pose inconnue : {pose!r}")
    n = len(moteurs) * len(images) * quantite
    if n > TIRS_MAX:
        raise ValueError(f"{n} générations demandées : {TIRS_MAX} au plus en un clic")
    return {"mode": mode, "moteurs": moteurs, "images": images, "prompt": prompt[:1000], "quantite": quantite,
            "reglages": reglages, "pose": pose, "textures": bool(b.get("textures", True)),
            "titre": str(b.get("titre") or "")[:120]}


def tirs(d: dict) -> list[dict]:
    """Un tir par (image, moteur, exemplaire), dans cet ordre : la galerie se remplit image par image."""
    out = []
    for img in d["images"]:
        for m in d["moteurs"]:
            for k in range(d["quantite"]):
                p = {"engine": m, "textures": d["textures"], "formats": ["glb"], "multiview": False,
                     "pose": d["pose"], "reglages": d["reglages"].get(m) or {}}
                if img:
                    p["image_filename"] = img
                else:
                    p["prompt"] = d["prompt"]
                if d["prompt"] and img:
                    p["subject"] = d["prompt"]
                p["exemplaire"] = k + 1
                out.append(p)
    return out


def op(tir: dict) -> dict:
    """L'op de devis d'un tir (même forme que POST /api/assets/3d, réglages des moteurs neufs compris)."""
    return {"kind": "asset3d", "engine": tir["engine"], "textures": tir["textures"], "multiview": False,
            "reglages": tir.get("reglages") or {}}


def devis(d: dict) -> dict:
    """Le devis : une ligne par moteur (prix unitaire × nombre de tirs) et le total. Gratuit, rien n'est écrit."""
    from app.services import pricing
    from app.services.asset3d_service import ENGINES
    lignes, total = [], 0.0
    par_image = len(d["images"]) * d["quantite"]
    for m in d["moteurs"]:
        e = pricing.estimate(op({"engine": m, "textures": d["textures"], "reglages": d["reglages"].get(m)}))
        u = round(float(e["total_usd"]), 4)
        lignes.append({"moteur": m, "label": ENGINES[m]["label"], "unitaire_usd": u, "tirs": par_image,
                       "usd": round(u * par_image, 4)})
        total += u * par_image
    return {"lignes": lignes, "tirs": par_image * len(d["moteurs"]), "total_usd": round(total, 4)}
