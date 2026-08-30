# -*- coding: utf-8 -*-
"""La vie d'un modèle, en une seule liste.

Trois registres racontent aujourd'hui la même histoire sans se parler : les
tâches Meshy (`MeshyTaskRecord`, binaires rapatriés), les versions d'un job
`assets3d` (`report.json`), et la version décimée (`model.opt.glb`). Ce module
les fond — il LIT ce qui existe, sans table ni migration.
"""
from __future__ import annotations

import json

from loguru import logger

from app.config import settings


def _jobs_dir():
    return settings.outputs_path / "assets3d"


def _numero_de_version(nom: str) -> int | None:
    """Le numéro d'une version, ou `None` si le nom ne suit pas la convention.

    L'explorateur Windows produit spontanément `model.v2 (1).glb` sur une
    copie à la main. Mesuré : sans cette garde, `int()` lève et TOUTE la
    chronologie tombe — y compris les jobs sains d'à côté. La bibliothèque 3D
    entière disparaîtrait de l'écran à cause d'un fichier copié.

    L'`isascii()` n'est pas décoratif : `'²'.isdigit()` vaut `True` alors
    qu'`int('²')` lève. Mesuré : 128 caractères sont dans ce cas — exposants,
    indices, chiffres cerclés, éthiopiens, brahmi — et tous sont non-ASCII.
    """
    if nom == "model.glb":
        return 1
    if not (nom.startswith("model.v") and nom.endswith(".glb")):
        return None
    reste = nom[len("model.v"):-len(".glb")]
    return int(reste) if reste.isascii() and reste.isdigit() else None


def _versions_du_job(job: str) -> list[dict]:
    """Les versions d'un job, enrichies par sa fiche quand elle existe."""
    from app.services import mesh_report

    d = _jobs_dir() / job
    fiches: dict[str, dict] = {}
    try:
        registre = mesh_report.read_registry(job)
        if isinstance(registre, dict):
            for e in registre.get("entries") or []:
                if isinstance(e, dict):
                    fiches[str(e.get("file"))] = e
    except (FileNotFoundError, ValueError):
        pass                      # un job sans registre reste listable

    etapes: list[dict] = []
    for glb in sorted(d.glob("model*.glb")):
        if glb.name == "model.opt.glb":
            continue
        v = _numero_de_version(glb.name)
        if v is None:
            continue              # nom hors convention : ignoré, jamais fatal
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
        # Si cette tâche a déjà été adoptée, on le DIT plutôt que de laisser
        # l'interface afficher deux fois le même maillage sans lien entre eux.
        # (`adopter_meshy` nomme le job `meshy_<id>`.)
        adopte = f"meshy_{t['id']}"
        out.append({
            "source": "meshy", "id": t["id"], "nom": t["id"][:12],
            "phase": t.get("phase"), "kind": t.get("kind"),
            "moteur": "meshy",           # même forme que les lignes assets3d
            "adopte_de": None,
            "adopte_en": adopte if (_jobs_dir() / adopte).is_dir() else None,
            "created_at": t.get("created_at"),
            "etapes": [{
                "version": None, "file": cle, "libelle": cle,
                "url": url, "bytes": None, "sha256": None,
                "triangles": None, "created_at": t.get("created_at"),
            } for cle, url in sorted(glbs.items())],
        })
    return out


def _ligne_de_job(d) -> dict | None:
    """La ligne d'un job, ou `None` s'il ne porte aucune version."""
    etapes = _versions_du_job(d.name)
    if not etapes:
        return None
    manifeste = {}
    p = d / "asset.json"
    if p.is_file():
        try:
            manifeste = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            manifeste = {}
    if not isinstance(manifeste, dict):
        # un `asset.json` valide mais qui n'est pas un objet (une liste, par
        # exemple) traverserait le `except ValueError` ci-dessus
        manifeste = {}
    return {
        "source": "assets3d", "id": d.name,
        "nom": manifeste.get("name") or d.name,
        "moteur": manifeste.get("engine"),
        "phase": manifeste.get("stage"),
        "kind": None,                   # même forme que les lignes meshy
        "adopte_de": manifeste.get("adopte_de"),
        "adopte_en": None,
        "created_at": manifeste.get("created_at"),
        "etapes": etapes,
    }


def lister() -> list[dict]:
    """Les jobs `assets3d` et leurs versions. Synchrone : lecture de disque.

    ORDRE : les jobs sortent triés par NOM de dossier, qui est un préfixe
    d'UUID — donc sans rapport avec le temps. `created_at` est là pour que
    l'appelant retrie ; l'interface ne doit pas faire confiance à cet ordre.
    Seules les `etapes` d'un job sont, elles, réellement chronologiques.

    APPELANT ASYNCHRONE : c'est de l'E/S disque synchrone. Une route
    `async def` doit l'envelopper dans `asyncio.to_thread(...)`, sinon elle
    gèle la boucle d'événements — donc TOUTES les requêtes du serveur, pas
    seulement la sienne.
    """
    racine = _jobs_dir()
    if not racine.is_dir():
        return []
    out: list[dict] = []
    for d in sorted(racine.iterdir()):
        if not d.is_dir():
            continue
        try:
            ligne = _ligne_de_job(d)
        except Exception as e:      # noqa: BLE001 — un job abîmé n'en éteint pas 300
            # « il LIT ce qui existe » a une conséquence : ce dossier est
            # ouvert aux mains de l'utilisateur. Un voisin abîmé ne doit pas
            # faire disparaître toute la bibliothèque de l'écran.
            logger.warning(f"mesh_sources: job {d.name} illisible ({e}) — ignoré")
            continue
        if ligne:
            out.append(ligne)
    return out
