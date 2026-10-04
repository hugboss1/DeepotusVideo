# -*- coding: utf-8 -*-
"""Projets de la Bibliothèque — tâche #78 (plan-library T3, 03/10/2026).

Un projet contient des assets de TOUTES les catégories ; la catégorie redevient
un filtre à l'intérieur. Un asset appartient à N projets. `ref` est le filename
pour un fichier, le job_id pour un rendu / 3D / sprite ; `kind` reprend le
vocabulaire de l'écran.

Décisions de l'utilisateur (03/10) :
- UN seul projet. Celui de la Bibliothèque porte `epingle` (« épinglé sur le
  téléphone ») : le manifeste mobile le lit ici, et les épingles de
  `outputs/_sync/projets.json` (tâche #58, qui se disait pense-bête de CE
  chantier) sont reprises une fois — le fichier est gardé.
- Le PROJET ACTIF range TOUT : les fichiers (le seul site `library_index.noter`,
  par où passent tous les producteurs) ET les jobs terminés (rendus, 3D,
  sprites) — un écouteur SQLAlchemy sur `jobs.status`, parce que l'état « done »
  est posé depuis plus de vingt sites. Ranger est OPTIONNEL et silencieux :
  comme l'index de provenance, ce hook ne fait jamais échouer la route (ni la
  génération payée) qui l'appelle.

Le projet actif est une ligne d'`atelier_settings` (clé `library_projet_actif`),
le patron de `global_style`.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from uuid import uuid4

from loguru import logger
from sqlalchemy import delete, event, func, inspect as sa_inspect, select
from sqlalchemy.orm import Session

CLE_ACTIF = "library_projet_actif"
CLE_JSON_REPRIS = "library_projets_json_repris"
KINDS = ("image", "audio", "render", "asset3d", "sprite2d")
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _t():
    from app.services.storage import (AtelierSetting, LibraryProject,
                                      LibraryProjectItem, async_session_factory)
    return AtelierSetting, LibraryProject, LibraryProjectItem, async_session_factory


def nom_propre(nom) -> str:
    return " ".join(str(nom or "").split()).strip()[:120]


def couleur_valide(c) -> bool:
    return c in (None, "") or bool(_COULEUR.match(str(c)))


def _vue(p, n: int | None = None) -> dict:
    d = {"id": p.id, "nom": p.nom, "couleur": p.couleur, "epingle": bool(p.epingle)}
    if n is not None:
        d["n"] = n
    return d


async def creer(nom: str, couleur: str | None = None, epingle: bool = False) -> dict:
    _A, P, _I, S = _t()
    nom = nom_propre(nom)
    if not nom:
        raise ValueError("Le nom du projet est vide.")
    if not couleur_valide(couleur):
        raise ValueError("couleur attendue au format #rrggbb")
    pid = "proj_" + uuid4().hex[:8]
    async with S() as s:
        p = P(id=pid, nom=nom, couleur=couleur or None, epingle=1 if epingle else 0)
        s.add(p)
        await s.commit()
        return _vue(p)


async def lister(ref: str | None = None) -> list[dict]:
    """Tous les projets, ou seulement ceux qui contiennent `ref` — la question
    « où sert cet asset ? ». Chacun porte son nombre d'items."""
    _A, P, I, S = _t()
    async with S() as s:
        q = select(P)
        if ref:
            q = q.join(I, I.project_id == P.id).where(I.ref == str(ref))
        projets = list((await s.execute(q.order_by(P.created_at.desc()))).scalars())
        cnt = dict((await s.execute(select(I.project_id, func.count()).group_by(I.project_id))).fetchall())
    return [_vue(p, cnt.get(p.id, 0)) for p in projets]


async def contenu(pid: str) -> dict:
    _A, P, I, S = _t()
    async with S() as s:
        p = await s.get(P, pid)
        if p is None:
            raise KeyError(pid)
        res = await s.execute(select(I.ref, I.kind).where(I.project_id == pid).order_by(I.added_at.desc()))
        d = _vue(p)
        d["items"] = [{"ref": r, "kind": k} for r, k in res.fetchall()]
        return d


async def etat(pid: str) -> dict:
    """Tâche #82 (04/10/2026, plan-library T15) — ce qui, DANS un projet, est monté, publié, imprimé ou inutilisé.
    Aucune donnée neuve, aucune écriture : trois jointures et un complément.
      * monté   : un job TERMINÉ l'a pour image de départ ou de fin — ou c'est lui-même un rendu terminé du projet ;
      * publié  : un post PUBLIÉ (« posted ») l'a pour image source ou pour rendu ;
      * imprimé : il a nourri une production de l'Établi (image source du job 3D, ou le job lui-même) ;
      * inutilisé : le COMPLÉMENT exact (un asset peut être dans plusieurs des trois premiers).
    KeyError si le projet n'existe pas."""
    from app.services.storage import JobRecord, ScheduledPost
    d = await contenu(pid)
    refs = {i["ref"]: i["kind"] for i in d["items"]}
    _A, P, I, S = _t()
    async with S() as s:
        jobs = (await s.execute(select(JobRecord.id, JobRecord.image_filename, JobRecord.image_filename_end)
                                .where(JobRecord.status == "done"))).fetchall()
        posts = (await s.execute(select(ScheduledPost.source_image, ScheduledPost.job_id)
                                 .where(ScheduledPost.status == "posted"))).fetchall()
    monte_noms = {x for j in jobs for x in (j[1], j[2]) if x} | {j[0] for j in jobs}
    publie_noms = {x for p in posts for x in p if x}
    imprime_noms: set = set()
    try:
        from app.api import routes as _R
        from app.services import asset3d_service as _A3
        prods = await asyncio.to_thread(_R._etabli_productions)
        for dossier in {e.get("job") for e in prods if e.get("job")}:
            imprime_noms.add(dossier)
            try:
                src = (_A3.read_manifest(dossier) or {}).get("image_filename")
                if src:
                    imprime_noms.add(Path(str(src)).name)
            except Exception:  # noqa: BLE001 — un job sans manifeste n'a pas de source connue
                pass
    except Exception:  # noqa: BLE001 — l'Établi illisible ne vide pas l'état
        pass

    def _imprime(ref: str) -> bool:
        return ref in imprime_noms or ref[:8] in imprime_noms   # un job 3D a pour dossier les 8 premiers caractères

    def _l(f):
        return [{"ref": r, "kind": k} for r, k in refs.items() if f(r)]
    monte, publie, imprime = _l(lambda r: r in monte_noms), _l(lambda r: r in publie_noms), _l(_imprime)
    vus = {x["ref"] for x in monte + publie + imprime}
    return {"id": pid, "nom": d.get("nom"), "n": len(refs), "monte": monte, "publie": publie, "imprime": imprime,
            "inutilise": [{"ref": r, "kind": k} for r, k in refs.items() if r not in vus]}


async def modifier(pid: str, champs: dict) -> dict:
    """Champs déjà validés par la route : nom, couleur, epingle. État RELU."""
    _A, P, _I, S = _t()
    async with S() as s:
        p = await s.get(P, pid)
        if p is None:
            raise KeyError(pid)
        if "nom" in champs:
            p.nom = nom_propre(champs["nom"])
        if "couleur" in champs:
            p.couleur = champs["couleur"] or None
        if "epingle" in champs:
            p.epingle = 1 if champs["epingle"] else 0
        await s.commit()
        await s.refresh(p)
        return _vue(p)


async def supprimer(pid: str) -> None:
    """Le projet et ses appartenances — JAMAIS les fichiers. S'il était actif,
    plus aucun projet ne l'est."""
    A, P, I, S = _t()
    async with S() as s:
        p = await s.get(P, pid)
        if p is None:
            raise KeyError(pid)
        await s.execute(delete(I).where(I.project_id == pid))
        await s.delete(p)
        row = await s.get(A, CLE_ACTIF)
        if row is not None and row.value == pid:
            row.value = ""
        await s.commit()


async def ajouter(pid: str, items: list[dict]) -> int:
    """Rend le nombre RÉELLEMENT ajouté : re-poser un item existant vaut 0.
    `kind` est validé par l'appelant (route) ; un kind hors KINDS devient image."""
    _A, P, I, S = _t()
    n = 0
    async with S() as s:
        if await s.get(P, pid) is None:
            raise KeyError(pid)
        vus = set()
        for it in items or []:
            ref = str((it or {}).get("ref") or "").strip()[:255]
            if not ref or ref in vus or await s.get(I, (pid, ref)) is not None:
                continue
            vus.add(ref)
            kind = str((it or {}).get("kind") or "image")
            s.add(I(project_id=pid, ref=ref, kind=kind if kind in KINDS else "image"))
            n += 1
        await s.commit()
    return n


async def retirer(pid: str, refs: list[str]) -> int:
    _A, P, I, S = _t()
    async with S() as s:
        if await s.get(P, pid) is None:
            raise KeyError(pid)
        res = await s.execute(delete(I).where(I.project_id == pid, I.ref.in_([str(r) for r in (refs or [])])))
        await s.commit()
        return res.rowcount or 0


async def actif() -> dict:
    """{id, nom} du projet actif, ou {id: ""}. Un id dont le projet a disparu
    se lit vide (jamais un rangement dans le vide)."""
    A, P, _I, S = _t()
    async with S() as s:
        row = await s.get(A, CLE_ACTIF)
        pid = (row.value or "") if row is not None else ""
        p = await s.get(P, pid) if pid else None
        return {"id": p.id, "nom": p.nom} if p is not None else {"id": ""}


async def poser_actif(pid: str) -> dict:
    """Vide = aucun projet actif ; un id INCONNU lève KeyError (404)."""
    A, P, _I, S = _t()
    pid = str(pid or "")
    async with S() as s:
        if pid and await s.get(P, pid) is None:
            raise KeyError(pid)
        row = await s.get(A, CLE_ACTIF)
        if row is None:
            row = A(key=CLE_ACTIF)
            s.add(row)
        row.value = pid
        await s.commit()
    return await actif()


async def ranger_dans_actif(refs, kind: str = "image") -> int:
    """Hook des producteurs. Aucun projet actif = no-op. Toute panne est avalée."""
    try:
        pid = (await actif()).get("id")
        if not pid:
            return 0
        return await ajouter(pid, [{"ref": str(r), "kind": kind} for r in (refs or []) if str(r)])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_projects.ranger_dans_actif ignoré: {e}")
        return 0


async def renommer_ref(ancien: str, nouveau: str) -> None:
    """Le fichier renommé reste dans ses projets (appelé par library_index.renommer)."""
    if not ancien or not nouveau or ancien == nouveau:
        return
    try:
        _A, _P, I, S = _t()
        async with S() as s:
            rows = list((await s.execute(select(I).where(I.ref == ancien))).scalars())
            for r in rows:
                if await s.get(I, (r.project_id, nouveau)) is None:
                    s.add(I(project_id=r.project_id, ref=nouveau, kind=r.kind, added_at=r.added_at))
                await s.delete(r)
            await s.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_projects.renommer_ref ignoré: {e}")


async def oublier_ref(ref: str) -> None:
    """Le fichier ou le job supprimé quitte tous ses projets."""
    try:
        _A, _P, I, S = _t()
        async with S() as s:
            await s.execute(delete(I).where(I.ref == str(ref)))
            await s.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"library_projects.oublier_ref ignoré: {e}")


# ── le téléphone ──────────────────────────────────────────────────────────────────────────────────────────────────────

async def epingler_par_nom(nom: str, fichiers: list) -> dict:
    """Contrat de POST /api/sync/projet (tâche #58) gardé : {nom, fichiers} →
    {nom, fichiers}. Le projet de la Bibliothèque de ce NOM est créé s'il manque,
    épinglé, et reçoit les fichiers (AJOUT, jamais de retrait). Rend ses
    fichiers images, noms nus triés."""
    _A, P, I, S = _t()
    nom = nom_propre(nom)
    if not nom:
        raise ValueError("Nom de projet requis")
    async with S() as s:
        p = (await s.execute(select(P).where(P.nom == nom).order_by(P.created_at))).scalars().first()
        pid = p.id if p is not None else None
        if p is not None:
            p.epingle = 1
            await s.commit()
    if pid is None:
        pid = (await creer(nom, epingle=True))["id"]
    noms = [Path(str(f)).name for f in (fichiers or [])]
    await ajouter(pid, [{"ref": n, "kind": "image"} for n in noms if n])
    d = await contenu(pid)
    return {"nom": d["nom"], "fichiers": sorted(i["ref"] for i in d["items"] if i["kind"] == "image")}


async def epingles_pour_manifeste() -> list[dict]:
    """Les projets ÉPINGLÉS, triés par nom, avec leurs FICHIERS images seulement
    (un id de job ne se télécharge pas). Forme du manifeste de la tâche #58."""
    _A, P, I, S = _t()
    async with S() as s:
        ps = list((await s.execute(select(P).where(P.epingle == 1))).scalars())
        out = []
        for p in sorted(ps, key=lambda x: x.nom):
            res = await s.execute(select(I.ref).where(I.project_id == p.id, I.kind == "image"))
            out.append({"nom": p.nom, "fichiers": sorted(r for (r,) in res.fetchall()), "entier": True})
        return out


async def reprendre_epingles_json() -> int:
    """UNE fois : les épingles de outputs/_sync/projets.json deviennent des
    projets épinglés. Le fichier est GARDÉ (retour arrière). Rend le nombre de
    projets repris (0 au deuxième appel)."""
    A, _P, _I, S = _t()
    from app.config import settings
    async with S() as s:
        if await s.get(A, CLE_JSON_REPRIS) is not None:
            return 0
    f = settings.outputs_path / "_sync" / "projets.json"
    tout = {}
    if f.is_file():
        try:
            v = json.loads(f.read_text(encoding="utf-8"))
            tout = v if isinstance(v, dict) else {}
        except (ValueError, OSError):
            tout = {}
    n = 0
    for nom, fichiers in tout.items():
        if nom_propre(nom):
            await epingler_par_nom(nom, fichiers if isinstance(fichiers, list) else [])
            n += 1
    async with S() as s:
        s.add(A(key=CLE_JSON_REPRIS, value=str(n)))
        await s.commit()
    if n:
        logger.info(f"library_projects: {n} projet(s) épinglé(s) repris de projets.json")
    return n


# ── les jobs terminés (rendus, 3D, sprites) ──────────────────────────────────────────────────────────────────────────

def kind_de_job(provider: str | None) -> str:
    p = str(provider or "")
    if p in ("asset3d", "card3d"):
        return "asset3d"
    if p == "sprite2d":
        return "sprite2d"
    return "render"


_TACHES: set = set()


def _job_termine(_mapper, _connection, target) -> None:
    """after_insert / after_update de JobRecord : le statut DEVIENT « done »
    (un job créé terminé compte ; ré-écrire « done » ne compte pas). Noté dans
    la session, rangé après COMMIT seulement."""
    try:
        h = sa_inspect(target).attrs.status.history
        if "done" in (h.added or ()) and "done" not in (h.deleted or ()):
            sess = sa_inspect(target).session
            if sess is not None:
                sess.info.setdefault("dz_ranger_jobs", []).append((target.id, target.provider))
    except Exception:  # noqa: BLE001
        pass


async def _ranger_jobs(lst) -> None:
    from app.services.montage_service import _PROXY_PROVIDER, _STAB_PROVIDER
    for jid, prov in lst:
        if prov in (_PROXY_PROVIDER, _STAB_PROVIDER):
            continue  # les précalculs du Montage ne sont pas des productions
        await ranger_dans_actif([jid], kind_de_job(prov))


def _apres_commit(session) -> None:
    lst = session.info.pop("dz_ranger_jobs", None)
    if not lst:
        return
    try:
        t = asyncio.get_running_loop().create_task(_ranger_jobs(lst))
        _TACHES.add(t)
        t.add_done_callback(_TACHES.discard)
    except RuntimeError:
        pass  # session synchrone hors boucle : rien à ranger (jamais une erreur)


def _apres_rollback(session, _previous_transaction=None) -> None:
    session.info.pop("dz_ranger_jobs", None)


def installer() -> None:
    """Pose les écouteurs une seule fois (appelé par app.main à l'import)."""
    from app.services.storage import JobRecord
    if event.contains(JobRecord, "after_update", _job_termine):
        return
    event.listen(JobRecord, "after_insert", _job_termine)
    event.listen(JobRecord, "after_update", _job_termine)
    event.listen(Session, "after_commit", _apres_commit)
    event.listen(Session, "after_soft_rollback", _apres_rollback)
