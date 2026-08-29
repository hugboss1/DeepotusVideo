# -*- coding: utf-8 -*-
"""La vie d'un modèle, en une seule liste.

Trois registres racontent aujourd'hui la même histoire sans se parler : les
tâches Meshy (`MeshyTaskRecord`, binaires rapatriés), les versions d'un job
`assets3d` (`report.json`), et la version décimée (`model.opt.glb`). Ce module
les fond — il LIT ce qui existe, sans table ni migration.
"""
from __future__ import annotations

import json

from app.config import settings


def _jobs_dir():
    return settings.outputs_path / "assets3d"


def _versions_du_job(job: str) -> list[dict]:
    """Les versions d'un job, enrichies par sa fiche quand elle existe."""
    from app.services import mesh_report

    d = _jobs_dir() / job
    fiches: dict[str, dict] = {}
    try:
        registre = mesh_report.read_registry(job)
        for e in registre.get("entries") or []:
            fiches[str(e.get("file"))] = e
    except (FileNotFoundError, ValueError):
        pass                      # un job sans registre reste listable

    etapes: list[dict] = []
    for glb in sorted(d.glob("model*.glb")):
        if glb.name == "model.opt.glb":
            continue
        v = 1 if glb.name == "model.glb" else int(
            glb.name.split(".v")[1].split(".")[0])
        f = fiches.get(glb.name) or {}
        geo = f.get("geometry") or {}
        etapes.append({
            "version": v,
            "file": glb.name,
            "libelle": "brouillon" if v == 1 else f"version {v}",
            "url": f"/api/assets/3d/{job}/version/{v}",
            "bytes": glb.stat().st_size,
            "sha256": f.get("sha256"),
            # ATTENTION : la fiche nomme ce compte `tris_lus`, pas `triangles`.
            # `mesh_sources` normalise le nom pour toute l'interface.
            "triangles": geo.get("tris_lus"),
            "created_at": f.get("created_at"),
        })
    etapes.sort(key=lambda e: e["version"])
    if (d / "model.opt.glb").is_file():
        etapes.append({
            "version": None, "file": "model.opt.glb", "libelle": "décimée",
            "url": f"/api/assets/3d/{job}/opt-glb",
            "bytes": (d / "model.opt.glb").stat().st_size,
            "sha256": None, "triangles": None, "created_at": None,
        })
    return etapes


async def lister_meshy(limit: int = 60) -> list[dict]:
    """Les tâches Meshy rapatriées, une ligne par tâche."""
    from app.services import meshy_service

    out: list[dict] = []
    for t in await meshy_service.list_tasks(limit=limit):
        glbs = {k: u for k, u in (t.get("local_files") or {}).items()
                if str(u).endswith(".glb")}
        if not glbs:
            continue
        out.append({
            "source": "meshy", "id": t["id"], "nom": t["id"][:12],
            "phase": t.get("phase"), "kind": t.get("kind"),
            "created_at": t.get("created_at"),
            "etapes": [{
                "version": None, "file": cle, "libelle": cle,
                "url": url, "bytes": None, "sha256": None,
                "triangles": None, "created_at": t.get("created_at"),
            } for cle, url in sorted(glbs.items())],
        })
    return out


def lister() -> list[dict]:
    """Les jobs `assets3d` et leurs versions. Synchrone : lecture de disque."""
    racine = _jobs_dir()
    if not racine.is_dir():
        return []
    out: list[dict] = []
    for d in sorted(racine.iterdir()):
        if not d.is_dir():
            continue
        etapes = _versions_du_job(d.name)
        if not etapes:
            continue
        manifeste = {}
        p = d / "asset.json"
        if p.is_file():
            try:
                manifeste = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                manifeste = {}
        out.append({
            "source": "assets3d", "id": d.name,
            "nom": manifeste.get("name") or d.name,
            "moteur": manifeste.get("engine"),
            "phase": manifeste.get("stage"),
            "created_at": manifeste.get("created_at"),
            "etapes": etapes,
        })
    return out
