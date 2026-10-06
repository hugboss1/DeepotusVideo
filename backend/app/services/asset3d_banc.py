# -*- coding: utf-8 -*-
"""Banc de référence par sujet type — T107 (plan-moteurs-3d T8, R10e D2).

Le registre des moteurs (`asset3d_service.ENGINES`) porte des drapeaux et des notes ; la matrice `BESOINS_3D`
recommande. Aucun des deux ne dit ce que CE moteur produit CHEZ NOUS : combien de triangles, quel poids, quelle
silhouette, pour combien. Ce module range ces chiffres — un par (sujet type, moteur) — et les rend à
`/assets3d/engines`, qui cesse alors de citer des fiches produit.

Il ne GÉNÈRE rien : générer coûte de l'argent, et l'argent se dépense sur un geste de l'utilisateur.
`scripts/banc_moteurs3d.py` imprime le plan de tir et son coût ; `mesurer()` range un job déjà produit. Tout ce qu'il
lit vient de la fiche de maillage (`report.json`) et du manifeste (`asset.json`) écrits par le flux normal — jamais
saisi. Le MOTEUR d'une mesure est celui du manifeste : une mesure rangée sous un autre nom fausserait la matrice.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

SUJETS = {
    "personnage": {"label": "Personnage", "besoin": "hero",
                   "prompt": "full body character, T-pose, stylized, plain flat neutral background, even diffuse "
                             "lighting, no cast shadow"},
    "objet": {"label": "Objet / accessoire", "besoin": "prop",
              "prompt": "a single hand prop object, centered, plain flat neutral background, even diffuse lighting, "
                        "no cast shadow"},
    "vehicule": {"label": "Véhicule", "besoin": "decor",
                 "prompt": "a small vehicle, three quarter view, centered, plain flat neutral background, even "
                           "diffuse lighting, no cast shadow"},
}


def sujets() -> list[dict]:
    return [{"id": k, **v} for k, v in SUJETS.items()]


def _dossier() -> Path:
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "_banc"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lire() -> dict:
    """Le banc ; un fichier absent ou illisible rend un banc VIDE — jamais une matrice qui tombe."""
    p = _dossier() / "banc.json"
    try:
        charge = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, ValueError):
        charge = None
    if not isinstance(charge, dict) or not isinstance(charge.get("lignes"), list):
        return {"lignes": [], "created_at": None}
    return charge


def mesurer(job, sujet: str, moteur: str | None = None, *, version: int | None = None) -> dict:
    """Range un job déjà produit comme point de référence. Le couple (sujet, moteur) est la CLÉ : remesurer remplace
    la ligne — sans cela, trois essais du même moteur pèseraient trois fois dans la médiane."""
    from app.services import asset3d_service, mesh_report, pricing
    sujet = str(sujet)
    if sujet not in SUJETS:
        raise ValueError(f"sujet type inconnu : {sujet!r} (attendu : {', '.join(SUJETS)})")
    nom = Path(str(job)).name
    reg = mesh_report.read_registry(nom)                    # FileNotFoundError « aucune fiche » si absente
    entrees = reg.get("entries") or []
    if not entrees:
        raise FileNotFoundError(f"la fiche de {nom} est vide : rien à mesurer")
    v = int(version) if version else int(reg.get("current_version") or entrees[-1].get("version") or 1)
    fiche = next((e for e in entrees if int(e.get("version") or 0) == v), entrees[-1])
    try:
        man = asset3d_service.read_manifest(nom)
    except (FileNotFoundError, ValueError):
        man = {}
    du_job = str(man.get("engine") or "").lower()
    moteur = str(moteur or du_job).lower()
    if not moteur:
        raise ValueError(f"le manifeste de {nom} ne dit pas quel moteur l'a produit : donne-le")
    if du_job and moteur != du_job:
        raise ValueError(f"{nom} a été produit par {du_job}, pas par {moteur} : une mesure rangée sous un autre "
                         "moteur fausserait la matrice")

    geo = fiche.get("geometry") or {}
    topo = geo.get("topologie") or {}
    sil = fiche.get("silhouettes") or {}
    tex = str(man.get("texture_mode") or "standard")
    devis = pricing.estimate({"kind": "asset3d", "engine": moteur, "textures": tex != "no",
                              "quality": "hd" if tex == "HD" else (man.get("quality") or ""),
                              "multiview": bool(man.get("multiview")), "views": int(man.get("views") or 0)})
    ligne = {
        "sujet": sujet, "moteur": moteur, "job": nom, "version": v,
        "tris": int(geo.get("tris") or 0), "verts": int(geo.get("verts") or 0),
        "materials": int(geo.get("materials") or 0),
        "bytes": int(fiche.get("bytes") or 0),
        "texture_bytes": int((fiche.get("gltf") or {}).get("texture_bytes") or 0),
        "sha256": fiche.get("sha256"),
        "ferme": topo.get("ferme"), "bord_pct": topo.get("bord_pct"),
        "couverture": {k: (sil.get(k) or {}).get("couverture") for k in ("face", "profil", "dessus")},
        "texture_mode": man.get("texture_mode"),
        "usd_estime": float(devis["total_usd"]),
        "mesure_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    banc = lire()
    banc["lignes"] = [l for l in banc["lignes"] if not (l.get("sujet") == sujet and l.get("moteur") == moteur)]
    banc["lignes"].append(ligne)
    banc["lignes"].sort(key=lambda l: (l.get("moteur") or "", l.get("sujet") or ""))
    banc["created_at"] = banc.get("created_at") or ligne["mesure_le"]
    banc["updated_at"] = ligne["mesure_le"]
    p = _dossier() / "banc.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(banc, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return ligne


def resume_par_moteur() -> dict:
    """{moteur: {sujets, tris_median, bytes_median, usd_median, ferme_sur, mesures, dernier}} — ce que la matrice
    besoin → moteur peut CITER. Un moteur jamais mesuré est absent : mieux vaut un trou visible qu'un chiffre inventé."""
    out: dict[str, dict] = {}
    par_moteur: dict[str, list] = {}
    for l in lire()["lignes"]:
        par_moteur.setdefault(l.get("moteur") or "?", []).append(l)
    for m, lignes in par_moteur.items():
        tris = [int(l.get("tris") or 0) for l in lignes if l.get("tris")]
        octs = [int(l.get("bytes") or 0) for l in lignes if l.get("bytes")]
        usd = [float(l.get("usd_estime") or 0) for l in lignes]
        out[m] = {
            "sujets": len({l.get("sujet") for l in lignes}),
            "tris_median": int(statistics.median(tris)) if tris else 0,
            "bytes_median": int(statistics.median(octs)) if octs else 0,
            "usd_median": round(statistics.median(usd), 4) if usd else 0.0,
            "ferme_sur": sum(1 for l in lignes if l.get("ferme")),
            "mesures": len(lignes),
            "dernier": max((l.get("mesure_le") or "") for l in lignes),
        }
    return out
