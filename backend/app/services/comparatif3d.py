# -*- coding: utf-8 -*-
"""Banc comparatif des moteurs image → 3D — t344 (lot Scenario B9, 29/10/2026).

Une image, N moteurs, et un TABLEAU MESURÉ : triangles, arêtes ouvertes et non-manifold, taille, temps, coût estimé et
réel. Deux façons de remplir un comparatif :
- « tir » : la même image part chez N moteurs en UN clic (devis total affiché avant, `confirme_cout`, plafonds — la
  route `/api/comparatif3d` le garde) ; chaque moteur est un job Game Assets 3D ordinaire (dossier, manifeste, fiche
  de maillage), rangé dans le comparatif ;
- « existants » : des GLB DÉJÀ générés (jobs assets3d, imports) rejoués côte à côte — gratuit, c'est aussi la preuve
  sans dépense.

Les mesures viennent toutes de la fiche de maillage (`mesh_report`) — jamais saisies, jamais recopiées d'une fiche
produit. Le temps est celui du job (début → fin du tir, à défaut création → fin du JobRecord). Le coût « réel » est
celui du registre des dépenses quand le fournisseur l'a donné (`reel_usd` sur la référence `asset3d:<job>`) ; un
moteur local est gratuit et le dit ; sinon `None`, et l'écran écrit « non rapproché ».

« Garder celui-ci » range le gagnant dans la Bibliothèque : une vue capturée du canevas (PNG écrit ICI, en Python),
indexée source « assets3d », mère = l'image source, relation « comparatif », recette = le tableau.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

MIN_MOTEURS = 2
ID_RE = re.compile(r"^c3d_[0-9a-f]{10}$")
JOB_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
POSTER_MAX = 2 * 1024 * 1024
TRIS = ("moteur", "tris", "aretes_bord", "aretes_non_manifold", "octets", "duree_s", "usd_estime", "usd_reel")
_VERROU = threading.Lock()


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dossier() -> Path:
    d = settings.outputs_path / "assets3d" / "_comparatifs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def id_valide(cid) -> bool:
    return isinstance(cid, str) and bool(ID_RE.match(cid))


def job_valide(job) -> bool:
    return isinstance(job, str) and bool(JOB_RE.match(job)) and job not in (".", "..") and not job.startswith("_")


# ── moteurs, clés et devis ─────────────────────────────────────────────────

def cle_de(moteur: str) -> str:
    """La clé (ou le service) dont un moteur a besoin : « fal » ou « local »."""
    from app.services.asset3d_service import ENGINES
    return "local" if ENGINES[moteur].get("local") else "fal"


def valider_moteurs(moteurs) -> list[str]:
    """Liste dédoublonnée dans l'ordre donné, ids connus, au moins deux : un comparatif d'un seul moteur n'en est pas un."""
    from app.services.asset3d_service import ENGINES
    if not isinstance(moteurs, list):
        raise ValueError("moteurs : une liste d'identifiants de moteurs 3D est attendue")
    vus: list[str] = []
    for m in moteurs:
        m = str(m or "").strip().lower()
        if m not in ENGINES:
            raise ValueError(f"Moteur 3D inconnu : {m!r}")
        if m not in vus:
            vus.append(m)
    if len(vus) < MIN_MOTEURS:
        raise ValueError("Choisis au moins deux moteurs à comparer")
    return vus


def op(moteur: str, textures: bool) -> dict:
    """L'op de devis d'UN tir — la même que POST /api/assets/3d (image unique, pas de vues complémentaires)."""
    return {"kind": "asset3d", "engine": moteur, "textures": bool(textures), "multiview": False}


def devis(moteurs: list[str], textures: bool = True, cle_fal: bool | None = None,
          local_ok: bool | None = None) -> dict:
    """Le devis ligne par ligne et le total — GRATUIT, rien n'est écrit. `cle_fal` / `local_ok` disent si la clé ou le
    service manque (le moteur reste choisissable : le refus n'arrive qu'au lancement)."""
    from app.services import pricing
    from app.services.asset3d_service import ENGINES
    if cle_fal is None:
        cle_fal = bool((settings.FAL_KEY or "").strip())
    lignes = []
    for m in moteurs:
        e = pricing.estimate(op(m, textures))
        cle = cle_de(m)
        lignes.append({"moteur": m, "label": ENGINES[m]["label"], "usd": round(float(e["total_usd"]), 4),
                       "cle": cle, "cle_ok": bool(cle_fal) if cle == "fal" else local_ok,
                       "note": ENGINES[m].get("note") or ""})
    return {"lignes": lignes, "total_usd": round(sum(l["usd"] for l in lignes), 4), "textures": bool(textures),
            "n": len(lignes)}


# ── le fichier d'un comparatif ─────────────────────────────────────────────

def _chemin(cid: str) -> Path:
    if not id_valide(cid):
        raise ValueError(f"Identifiant de comparatif invalide : {str(cid)[:40]!r}")
    return dossier() / f"{cid}.json"


def _ecrire(c: dict) -> None:
    p = _chemin(c["id"])
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(c, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def creer(mode: str, lignes: list[dict], *, image_filename: str | None = None, textures: bool = True,
          titre: str = "") -> dict:
    if mode not in ("tir", "existants"):
        raise ValueError(f"mode inconnu : {mode!r}")
    c = {"id": "c3d_" + uuid.uuid4().hex[:10], "mode": mode, "image_filename": image_filename,
         "textures": bool(textures), "titre": str(titre or "")[:120], "created_at": _maintenant(),
         "lignes": [dict(l) for l in lignes], "gagnant": None}
    with _VERROU:
        _ecrire(c)
    return c


def lire(cid: str) -> dict:
    p = _chemin(cid)
    if not p.is_file():
        raise FileNotFoundError(f"Comparatif introuvable : {cid}")
    return json.loads(p.read_text(encoding="utf-8"))


def noter(cid: str, job: str, **champs) -> dict:
    """Met à jour la ligne du job (début, fin, erreur). Sous verrou : les N tirs finissent en même temps."""
    with _VERROU:
        c = lire(cid)
        for l in c["lignes"]:
            if l.get("job") == job:
                l.update(champs)
        _ecrire(c)
    return c


def lister() -> list[dict]:
    out = []
    for p in sorted(dossier().glob("c3d_*.json")):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"id": c["id"], "mode": c.get("mode"), "titre": c.get("titre") or "",
                    "image_filename": c.get("image_filename"), "created_at": c.get("created_at"),
                    "moteurs": [l.get("moteur") for l in c.get("lignes") or []],
                    "gagnant": (c.get("gagnant") or {}).get("moteur")})
    out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return out


# ── les modèles existants (mode gratuit) ───────────────────────────────────

def _glb(job: str, version: int) -> Path:
    from app.services import mesh_report
    return mesh_report.job_dir(job) / ("model.glb" if int(version) == 1 else f"model.v{int(version)}.glb")


def _manifeste(job: str) -> dict:
    from app.services import asset3d_service
    try:
        return asset3d_service.read_manifest(job)
    except (FileNotFoundError, ValueError):
        return {}


def _registre(job: str) -> dict | None:
    from app.services import mesh_report
    try:
        return mesh_report.read_registry(job)
    except (FileNotFoundError, ValueError):
        return None


def modeles() -> list[dict]:
    """Les jobs 3D qui ont un GLB, le plus récent d'abord, avec le moteur du manifeste et l'image source."""
    racine = settings.outputs_path / "assets3d"
    if not racine.is_dir():
        return []
    out = []
    for d in racine.iterdir():
        if not d.is_dir() or d.name.startswith("_") or not (d / "model.glb").is_file():
            continue
        man = _manifeste(d.name)
        reg = _registre(d.name) or {}
        v = int(reg.get("current_version") or 1)
        if not _glb(d.name, v).is_file():
            v = 1
        fiche = next((e for e in reg.get("entries") or [] if int(e.get("version") or 0) == v), None) or {}
        out.append({"job": d.name, "version": v, "moteur": str(man.get("engine") or "?"),
                    "image_filename": man.get("image_filename"),
                    "created_at": man.get("created_at") or datetime.fromtimestamp(
                        (d / "model.glb").stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                    "tris": int((fiche.get("geometry") or {}).get("tris") or 0) or None})
    out.sort(key=lambda m: str(m["created_at"]), reverse=True)
    return out


def preparer_existants(modeles_choisis) -> list[dict]:
    """[{job, version?}] ou [job] → lignes du comparatif. Calcule la fiche de maillage absente (local, gratuit)."""
    from app.services import mesh_report
    if not isinstance(modeles_choisis, list):
        raise ValueError("modeles : une liste de jobs 3D est attendue")
    lignes, vus = [], set()
    for m in modeles_choisis:
        job, version = (m.get("job"), m.get("version")) if isinstance(m, dict) else (m, None)
        job = str(job or "")
        if not job_valide(job):
            raise ValueError(f"Job 3D refusé : {job[:40]!r}")
        reg = _registre(job) or {}
        try:
            v = int(version or reg.get("current_version") or 1)
        except (TypeError, ValueError):
            raise ValueError("version : un entier à partir de 1") from None
        if v < 1 or not _glb(job, v).is_file():
            raise FileNotFoundError(f"Modèle introuvable : {job} v{v}")
        if (job, v) in vus:
            continue
        vus.add((job, v))
        if not any(int(e.get("version") or 0) == v for e in reg.get("entries") or []):
            mesh_report.write_report(job, _glb(job, v).name, version=v, avec_silhouettes=False)
        man = _manifeste(job)
        lignes.append({"moteur": str(man.get("engine") or "?"), "job": job, "version": v, "usd_estime": None})
    if len(lignes) < MIN_MOTEURS:
        raise ValueError("Choisis au moins deux modèles à comparer")
    return lignes


# ── le tableau mesuré ──────────────────────────────────────────────────────

def mesures(job: str, version: int) -> dict:
    """Ce que la fiche de maillage dit de cette version — tout `None` si la fiche manque (job en cours)."""
    reg = _registre(job) or {}
    fiche = next((e for e in reg.get("entries") or [] if int(e.get("version") or 0) == int(version)), None)
    if not fiche:
        return {"tris": None, "sommets": None, "aretes_bord": None, "aretes_non_manifold": None, "ferme": None,
                "bord_pct": None, "octets": None, "octets_textures": None, "materiaux": None}
    geo = fiche.get("geometry") or {}
    topo = geo.get("topologie") or {}
    calc = bool(topo.get("calcule"))
    return {"tris": geo.get("tris"), "sommets": geo.get("verts"),
            "aretes_bord": topo.get("aretes_de_bord") if calc else None,
            "aretes_non_manifold": topo.get("aretes_non_manifold") if calc else None,
            "ferme": topo.get("ferme") if calc else None, "bord_pct": topo.get("bord_pct") if calc else None,
            "octets": fiche.get("bytes"), "octets_textures": (fiche.get("gltf") or {}).get("texture_bytes"),
            "materiaux": geo.get("materials")}


def _usd_estime_manifeste(moteur: str, man: dict):
    from app.services import pricing
    from app.services.asset3d_service import ENGINES
    if moteur not in ENGINES:
        return None                           # un import n'a pas de devis
    tex = str(man.get("texture_mode") or "standard")
    return round(float(pricing.estimate({"kind": "asset3d", "engine": moteur, "textures": tex != "no",
                                         "multiview": bool(man.get("multiview")),
                                         "views": int(man.get("views") or 0)})["total_usd"]), 4)


def _secondes(a, b):
    try:
        da = a if isinstance(a, datetime) else datetime.fromisoformat(str(a))
        db = b if isinstance(b, datetime) else datetime.fromisoformat(str(b))
    except (TypeError, ValueError):
        return None
    if (da.tzinfo is None) != (db.tzinfo is None):
        da, db = da.replace(tzinfo=None), db.replace(tzinfo=None)
    return round(max(0.0, (db - da).total_seconds()), 1)


async def _jobs_et_depenses(jobs: list[str]) -> tuple[dict, dict]:
    """{short: JobRecord} et {short: [reel_usd…]} — lus en base, jamais une écriture."""
    from sqlalchemy import select
    from app.services import plafonds
    from app.services.storage import Depense, JobRecord, async_session_factory
    recs, reels = {}, {}
    if not jobs:
        return recs, reels
    async with async_session_factory() as s:
        for j in jobs:
            r = (await s.execute(select(JobRecord).where(JobRecord.provider == "asset3d",
                                                         JobRecord.id.like(f"{j[:8]}%"))
                 .order_by(JobRecord.created_at.desc()))).scalars().first()
            if r is not None and len(j) == 8:
                recs[j] = r
    async with plafonds._registre() as s:
        for j in jobs:
            ls = (await s.execute(select(Depense).where(Depense.ref == f"asset3d:{j}"))).scalars().all()
            reels[j] = [l.reel_usd for l in ls]
    return recs, reels


def _statut(rec, glb_ok: bool, mode: str) -> tuple[str, int, str | None, str | None]:
    if rec is None:
        return ("termine" if glb_ok else ("absent" if mode == "existants" else "en_cours")), (100 if glb_ok else 0), \
            None, None
    st = str(rec.status or "")
    if st == "done":
        return "termine", 100, rec.current_step, None
    if st == "failed":
        return "echec", int(rec.progress or 0), rec.current_step, rec.error
    return "en_cours", int(rec.progress or 0), rec.current_step, None


async def tableau(cid: str) -> dict:
    """Le comparatif et une ligne MESURÉE par moteur (statut, mesures de la fiche, temps, coûts)."""
    from app.services.asset3d_service import ENGINES
    c = lire(cid)
    jobs = [l["job"] for l in c["lignes"] if l.get("job")]
    recs, reels = await _jobs_et_depenses(jobs)
    out = []
    for l in c["lignes"]:
        job, v, m = l.get("job"), int(l.get("version") or 1), l.get("moteur") or "?"
        glb_ok = bool(job) and _glb(job, v).is_file()
        rec = recs.get(job)
        statut, prog, etape, err = _statut(rec, glb_ok, c.get("mode"))
        err = l.get("erreur") or err
        if l.get("erreur"):
            statut = "echec"
        duree = _secondes(l.get("debut"), l.get("fin")) if l.get("debut") and l.get("fin") else (
            _secondes(rec.created_at, rec.completed_at) if rec is not None and rec.completed_at else None)
        estime = l.get("usd_estime")
        if estime is None and job:
            estime = _usd_estime_manifeste(m, _manifeste(job))
        connus = [x for x in reels.get(job, []) if x is not None]
        if m in ENGINES and ENGINES[m].get("local"):
            reel = 0.0                          # local : gratuit, et c'est un réel
        elif connus:
            reel = round(sum(connus), 4)
        else:
            reel = None
        out.append({"moteur": m, "label": ENGINES[m]["label"] if m in ENGINES else m, "job": job, "version": v,
                    "statut": statut, "progression": prog, "etape": etape, "erreur": err,
                    **(mesures(job, v) if job else mesures("", 0)),
                    "duree_s": duree, "usd_estime": estime, "usd_reel": reel,
                    "glb": f"/api/assets/3d/{job}/version/{v}" if glb_ok else None,
                    "gagnant": bool(c.get("gagnant")) and c["gagnant"].get("job") == job})
    n_fin = sum(1 for x in out if x["statut"] in ("termine", "echec", "absent"))
    return {**{k: v for k, v in c.items() if k != "lignes"}, "lignes": out,
            "en_cours": n_fin < len(out),
            "total_estime_usd": round(sum(x["usd_estime"] or 0 for x in out), 4)}


def trier(lignes: list[dict], cle: str = "tris", desc: bool = False) -> list[dict]:
    """Tri stable ; une valeur inconnue (None) passe TOUJOURS en dernier, quel que soit le sens."""
    if cle not in TRIS:
        raise ValueError(f"tri inconnu : {cle!r} (attendu : {', '.join(TRIS)})")
    connus = [l for l in lignes if l.get(cle) is not None]
    inconnus = [l for l in lignes if l.get(cle) is None]
    return sorted(connus, key=lambda l: l[cle], reverse=desc) + inconnus


def resume(tab: dict, langue: str = "fr") -> str:
    """Une phrase par moteur, pour l'agent : triangles, ouvert ou étanche, temps, coût."""
    en = langue == "en"
    morceaux = []
    for l in tab["lignes"]:
        if l["statut"] != "termine":
            morceaux.append(f"{l['label']} : {l['statut']}")
            continue
        etanche = ("watertight" if en else "étanche") if l["ferme"] else (
            f"{l['aretes_bord']} open edges" if en else f"{l['aretes_bord']} arêtes ouvertes") \
            if l["aretes_bord"] is not None else "?"
        cout = "—" if l["usd_estime"] is None else f"{l['usd_estime']} $"
        morceaux.append(f"{l['label']} : {l['tris']} tris, {etanche}, {l['duree_s'] or '?'} s, {cout}")
    return " ; ".join(morceaux)


# ── « Garder celui-ci » ────────────────────────────────────────────────────

def lire_poster(valeur) -> bytes:
    """Un PNG en data URL (ou base64 nu) → octets ; borné, magic vérifié."""
    import base64
    if not isinstance(valeur, str) or not valeur:
        raise ValueError("poster : la vue capturée (PNG en data URL) est attendue")
    if valeur.startswith("data:"):
        valeur = valeur.split(",", 1)[-1]
    if len(valeur) > POSTER_MAX * 4 // 3 + 8:
        raise ValueError("poster trop lourd : 2 Mio au plus")
    try:
        brut = base64.b64decode(valeur, validate=True)
    except ValueError:
        raise ValueError("poster illisible : base64 attendu") from None
    if len(brut) > POSTER_MAX:
        raise ValueError("poster trop lourd : 2 Mio au plus")
    if not brut.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("poster refusé : une image PNG est attendue")
    return brut


async def garder(cid: str, job: str, poster: bytes) -> dict:
    """Le gagnant entre dans la Bibliothèque : sa vue capturée, indexée avec sa provenance, et le comparatif le retient."""
    from app.services import library_index as LI
    tab = await tableau(cid)
    ligne = next((l for l in tab["lignes"] if l.get("job") == job), None)
    if ligne is None:
        raise LookupError(f"{job} ne fait pas partie de ce comparatif")
    if ligne["statut"] != "termine":
        raise ValueError("Ce modèle n'est pas terminé : rien à garder")
    images = settings.images_path
    images.mkdir(parents=True, exist_ok=True)
    dest = images / f"shot_{job}_comparatif.png"
    n = 2
    while dest.exists():
        dest = images / f"shot_{job}_comparatif_{n}.png"
        n += 1
    dest.write_bytes(poster)
    vign = settings.outputs_path / "assets3d" / job / f"vignette_v{int(ligne['version'])}.png"
    if not vign.exists():
        vign.write_bytes(poster)              # la carte 3D de la Bibliothèque montre enfin le vrai rendu
    mere = Path(str(_manifeste(job).get("image_filename") or tab.get("image_filename") or "")).name or None
    cols = ("moteur", "tris", "aretes_bord", "aretes_non_manifold", "ferme", "octets", "duree_s", "usd_estime",
            "usd_reel")
    recette = {"outil": "comparatif3d", "comparatif": cid, "moteur": ligne["moteur"], "job": job,
               "version": ligne["version"], "mesures": {k: ligne.get(k) for k in cols},
               "rivaux": [{k: l.get(k) for k in cols} | {"job": l.get("job")}
                          for l in tab["lignes"] if l.get("job") != job]}
    await LI.noter([dest.name], "assets3d", job_id=job, parent=mere, relation="comparatif", recette=recette)
    gagnant = {"job": job, "moteur": ligne["moteur"], "filename": dest.name, "le": _maintenant()}
    with _VERROU:
        c = lire(cid)
        c["gagnant"] = gagnant
        _ecrire(c)
    return {"filename": dest.name, "gagnant": gagnant}
