# -*- coding: utf-8 -*-
"""Tâche #81 (03/10/2026, plan-library T9-T10) — la CORBEILLE de la Bibliothèque.

Décisions de l'utilisateur (03/10) : jeter une IMAGE, un SON ou un RENDU l'envoie dans `assets/_corbeille` au lieu de
l'effacer ; on le RESTAURE depuis l'onglet Corbeille ; « Vider » est MANUEL (dialogue maison à l'écran) ; au-delà de
30 jours un élément est PROPOSÉ à la purge, jamais purgé seul ; la corbeille ne part pas au transfert (lot « rebuts »).

Une entrée = un dossier `_corbeille/<id>/` : `journal.json` (écrit EN PREMIER, .part puis replace) et `f/` (les
fichiers déplacés). Le journal garde ce que la suppression perdait et que le plan oubliait : la ligne d'index ENTIÈRE
(tags, favori, note, licence, lignée, recette…), les PROJETS, les fichiers compagnons (recette d'une image fixe de
gabarit, recette d'un dépôt du téléphone), l'entrée du sidecar des sons ; pour un rendu, la ligne du job et son dossier
de sortie. Un nom déjà repris au moment de restaurer : l'élément revient sous un nom voisin, et on le DIT.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings

JOURS = 30


def dossier() -> Path:
    return settings.images_path.parent / "_corbeille"


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _audio_dir() -> Path:
    return settings.images_path.parent / "audio"


def _ecrire_journal(d: Path, j: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "journal.json.part"
    tmp.write_text(json.dumps(j, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, d / "journal.json")


def _lire_journal(d: Path) -> dict | None:
    try:
        j = json.loads((d / "journal.json").read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _taille(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return 0


def _deplacer(fichiers: list[tuple[Path, str]], d: Path) -> list[dict]:
    """Déplace (orig, nom stocké) dans d/f ; en cas d'échec, remet ce qui est déjà parti et relève."""
    f = d / "f"
    f.mkdir(parents=True, exist_ok=True)
    faits: list[dict] = []
    try:
        for orig, nom in fichiers:
            shutil.move(str(orig), str(f / nom))
            faits.append({"orig": str(orig), "stocke": nom, "dossier": (f / nom).is_dir()})
    except Exception:
        for e in reversed(faits):
            try:
                shutil.move(str(f / e["stocke"]), e["orig"])
            except Exception as e2:  # noqa: BLE001
                logger.warning(f"corbeille : retour impossible de {e['orig']} ({e2})")
        raise
    return faits


def _colonnes(row) -> dict:
    out = {}
    for c in row.__table__.columns:
        v = getattr(row, c.key)
        out[c.key] = v.isoformat() if isinstance(v, datetime) else v
    return out


def _depuis_colonnes(modele, cols: dict):
    vals = {}
    for c in modele.__table__.columns:
        if c.key not in cols:
            continue
        v = cols[c.key]
        if v is not None and str(c.type).upper().startswith("DATETIME") and isinstance(v, str):
            try:
                v = datetime.fromisoformat(v)
            except ValueError:
                v = None
        vals[c.key] = v
    return modele(**vals)


def _nouvel_id() -> str:
    return _maintenant().strftime("%Y%m%d%H%M%S") + "_" + uuid4().hex[:6]


async def jeter_fichier(nom: str, kind: str) -> dict | None:
    """Une IMAGE ou un SON de la Bibliothèque à la corbeille. None si le fichier n'existe pas."""
    from sqlalchemy import select
    from app.services import library_index as LI
    from app.services.storage import LibraryAsset, LibraryProjectItem, async_session_factory
    nom = Path(str(nom or "")).name
    src = (_audio_dir() if kind == "audio" else settings.images_path) / nom
    if not nom or not src.is_file():
        return None
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, nom)
        index = _colonnes(row) if row is not None else None
        res = await s.execute(select(LibraryProjectItem).where(LibraryProjectItem.ref == nom))
        projets = [{"project_id": p.project_id, "kind": p.kind} for p in res.scalars().all()]
    fichiers = [(src, nom)]
    compagnons = []
    for c in (settings.images_path / f"{nom}.recette.json", settings.outputs_path / "_sync" / "recettes" / f"{nom}.json"):
        if c.is_file():
            stocke = f"compagnon_{len(fichiers)}_{c.name}"
            fichiers.append((c, stocke))
            compagnons.append(stocke)
    sfx = None
    if kind == "audio":
        from app.services import sfx_service as SFX
        sfx = SFX.load_meta().get(nom)
    eid = _nouvel_id()
    d = dossier() / eid
    j = {"id": eid, "type": "son" if kind == "audio" else "image", "nom": nom, "kind": kind,
         "jete_le": _maintenant().isoformat(timespec="seconds"), "octets": sum(_taille(p) for p, _ in fichiers),
         "index": index, "projets": projets, "compagnons": compagnons, "sfx_meta": sfx, "fichiers": []}
    _ecrire_journal(d, j)
    try:
        j["fichiers"] = _deplacer(fichiers, d)
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise
    from app.services import library_commentaires as LCM   # tâche #82 : les commentaires partent avec l'asset
    j["commentaires"] = await LCM.emporter(nom)
    _ecrire_journal(d, j)
    await LI.retirer(nom)
    if sfx is not None:
        _sfx_oublier(nom)
    return j


def _sfx_oublier(nom: str) -> None:
    from app.services import sfx_service as SFX
    meta = SFX.load_meta()
    if nom in meta:
        meta.pop(nom)
        p = SFX._meta_path()
        tmp = p.with_name(p.name + ".part")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)


async def jeter_job(job_id: str) -> dict | None:
    """Un RENDU à la corbeille : ses fichiers, son dossier de sortie (sprites / 3D), la ligne du job, ses projets."""
    from sqlalchemy import delete, select
    from app.services import library_projects as LP
    from app.services.storage import JobRecord, LibraryProjectItem, async_session_factory
    async with async_session_factory() as s:
        job = await s.get(JobRecord, str(job_id))
        if job is None:
            return None
        cols = _colonnes(job)
        res = await s.execute(select(LibraryProjectItem).where(LibraryProjectItem.ref == job.id))
        projets = [{"project_id": p.project_id, "kind": p.kind} for p in res.scalars().all()]
        chemins = []
        for c in (job.video_path, job.audio_path, job.final_video_path, job.caption_path):
            if c and Path(c).exists() and Path(c) not in chemins:
                chemins.append(Path(c))
        sub = {"sprite2d": "sprites", "asset3d": "assets3d", "card3d": "assets3d"}.get(job.provider or "")
        if sub and (settings.outputs_path / sub / job.id[:8]).is_dir():
            chemins.append(settings.outputs_path / sub / job.id[:8])
    fichiers = [(p, f"{i}_{p.name}") for i, p in enumerate(chemins)]
    eid = _nouvel_id()
    d = dossier() / eid
    j = {"id": eid, "type": "rendu", "nom": cols.get("title") or job_id, "job_id": job_id,
         "jete_le": _maintenant().isoformat(timespec="seconds"), "octets": sum(_taille(p) for p, _ in fichiers),
         "job": cols, "projets": projets, "fichiers": []}
    _ecrire_journal(d, j)
    try:
        j["fichiers"] = _deplacer(fichiers, d)
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise
    _ecrire_journal(d, j)
    async with async_session_factory() as s:
        await s.execute(delete(JobRecord).where(JobRecord.id == job_id))
        await s.commit()
    await LP.oublier_ref(job_id)
    return j


def lister() -> dict:
    """Le contenu de la corbeille, le plus récent d'abord ; `ancien` = jeté il y a plus de 30 jours (PROPOSÉ à la
    purge). Un dossier sans journal lisible est montré comme tel (on ne le cache pas, on ne le restaure pas)."""
    out, octets, anciens = [], 0, 0
    lim = _maintenant() - timedelta(days=JOURS)
    if dossier().is_dir():
        for d in sorted(dossier().iterdir(), reverse=True):
            if not d.is_dir():
                continue
            j = _lire_journal(d)
            if j is None:
                out.append({"id": d.name, "type": "illisible", "nom": d.name, "jete_le": None, "octets": _taille(d),
                            "ancien": False, "restaurable": False})
                continue
            try:
                quand = datetime.fromisoformat(j.get("jete_le") or "")
            except ValueError:
                quand = None
            vieux = bool(quand and quand < lim)
            anciens += vieux
            octets += int(j.get("octets") or 0)
            out.append({"id": j["id"], "type": j.get("type"), "nom": j.get("nom"), "job_id": j.get("job_id"),
                        "jete_le": j.get("jete_le"), "octets": j.get("octets"), "ancien": vieux, "restaurable": True,
                        "jours": (_maintenant() - quand).days if quand else None})
    return {"elements": out, "octets": octets, "anciens": anciens, "jours": JOURS}


def _nom_libre(dossier_cible: Path, nom: str) -> str:
    if not (dossier_cible / nom).exists():
        return nom
    p = Path(nom)
    for i in range(1, 1000):
        cand = f"{p.stem}_restaure{'' if i == 1 else i}{p.suffix}"
        if not (dossier_cible / cand).exists():
            return cand
    raise RuntimeError(f"aucun nom libre pour {nom}")


async def restaurer(eid: str) -> dict:
    """Remet l'élément en place (fichiers, index, projets encore existants, compagnons, sidecar). ValueError si
    l'entrée n'existe pas ou n'est pas restaurable ; un rendu dont l'id a été repris est refusé (FileExistsError)."""
    from app.services.storage import JobRecord, LibraryAsset, async_session_factory
    eid = Path(str(eid or "")).name
    d = dossier() / eid
    j = _lire_journal(d) if eid and d.is_dir() else None
    if j is None:
        raise ValueError(f"Rien à restaurer : {eid}")
    f = d / "f"
    if j.get("type") == "rendu":
        async with async_session_factory() as s:
            if await s.get(JobRecord, j["job_id"]) is not None:
                raise FileExistsError(f"Un rendu porte déjà l'identifiant {j['job_id']}")
        for e in j.get("fichiers") or []:
            if Path(e["orig"]).exists():
                raise FileExistsError(f"Un fichier occupe déjà {e['orig']}")
        for e in j.get("fichiers") or []:
            Path(e["orig"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f / e["stocke"]), e["orig"])
        async with async_session_factory() as s:
            s.add(_depuis_colonnes(JobRecord, j["job"]))
            await s.commit()
        await _reposer_projets(j, j["job_id"])
        shutil.rmtree(d, ignore_errors=True)
        return {"restaure": j["job_id"], "type": "rendu", "renomme": False}
    kind = j.get("kind") or "image"
    cible = _audio_dir() if kind == "audio" else settings.images_path
    cible.mkdir(parents=True, exist_ok=True)
    nom = _nom_libre(cible, j["nom"])
    for e in j.get("fichiers") or []:
        if e["stocke"] == j["nom"]:
            shutil.move(str(f / e["stocke"]), str(cible / nom))
        else:   # un compagnon : il suit le NOM rendu
            orig = Path(e["orig"])
            dest = orig.with_name(orig.name.replace(j["nom"], nom, 1))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f / e["stocke"]), str(dest))
    if j.get("index"):
        cols = dict(j["index"]); cols["filename"] = nom
        async with async_session_factory() as s:
            if await s.get(LibraryAsset, nom) is None:
                s.add(_depuis_colonnes(LibraryAsset, cols))
                await s.commit()
    if j.get("sfx_meta") is not None:
        from app.services import sfx_service as SFX
        SFX.record_meta(nom, j["sfx_meta"])
    await _reposer_projets(j, nom)
    if j.get("commentaires"):   # tâche #82 : ils reviennent sous le nom RENDU
        from app.services import library_commentaires as LCM
        await LCM.rapporter(nom, j["commentaires"])
    shutil.rmtree(d, ignore_errors=True)
    return {"restaure": nom, "type": j.get("type"), "renomme": nom != j["nom"]}


async def _reposer_projets(j: dict, ref: str) -> None:
    from app.services.storage import LibraryProject, LibraryProjectItem, async_session_factory
    async with async_session_factory() as s:
        for p in j.get("projets") or []:
            if await s.get(LibraryProject, p["project_id"]) is None:
                continue        # le projet a été supprimé entre-temps
            if await s.get(LibraryProjectItem, (p["project_id"], ref)) is None:
                s.add(LibraryProjectItem(project_id=p["project_id"], ref=ref, kind=p.get("kind") or "image"))
        await s.commit()


def vider(ids: list[str] | None = None, tout: bool = False) -> dict:
    """Efface DÉFINITIVEMENT des entrées (celles nommées, ou toutes). Rend le nombre et les octets libérés."""
    n, octets = 0, 0
    if not dossier().is_dir():
        return {"vides": 0, "octets": 0}
    cibles = [d for d in dossier().iterdir() if d.is_dir()] if tout else \
        [dossier() / Path(str(i)).name for i in (ids or []) if str(i).strip()]
    for d in cibles:
        # DEUX gardes, chacune suffit (mutants équivalents documentés) : le nom seul (.name ci-dessus) et le parent
        if d.is_dir() and d.parent == dossier():
            octets += _taille(d)
            shutil.rmtree(d, ignore_errors=True)
            n += 1
    return {"vides": n, "octets": octets}
