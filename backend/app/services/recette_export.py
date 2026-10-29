# -*- coding: utf-8 -*-
"""t346 (29/10/2026, D2 du lot Scenario) — EXPORTER la recette d'un rendu, d'un plan ou d'un asset de la Bibliothèque
en « skill » : un ZIP qui contient `SKILL.md` (au format des skills Claude : frontmatter name/description, étapes
reproductibles, prompts EXACTS, modèles et endpoints, paramètres, graine, coûts réels contre estimés, ratés et essais
rejetés quand on les connaît, provenance des entrées), `fabrication.pdf` (vignettes, chronologie, coûts), `recette.json`
(le dossier lisible par une machine) et les images d'entrée et de sortie RÉDUITES.

Chez Scenario, chaque exploration publie son skill ZIP et son making-of PDF ; ici, tout est local et GRATUIT : on relit
ce que l'application a déjà gardé, sans rien appeler ni rien payer.
  - un RENDU (job) : `recette_rendu.recette` (recette Quick, colonnes du job, recette d'import), la recette de la
    Bibliothèque rangée avec sa vidéo (previs : endpoint, arguments, tâche, résolution, conform, recalage), `cost_meta`,
    et les essais du même lot (`batch_id`) ;
  - un PLAN : croquis (graine), image de production (prompt), bornes du Plateau, puis ses jobs : la vidéo du plan
    (`shot.video`), les previs rangées dans la Bibliothèque pour ce plan (`recette.plan`) et les previs ratées
    (`cost_meta.plan`, posé depuis t346) ; les lignes de dépense du plan (`ref` = l'id du plan) ;
  - un ASSET : sa lignée remontée jusqu'à la racine (`parent_filename`), racine d'abord ; chaque maillon porte sa
    recette de la Bibliothèque et, s'il vient d'un job, l'étape de ce job.
Les coûts viennent du registre des plafonds (`depenses` : estimé AVANT le tir, réel quand le fournisseur le dit) ; le
devis gardé dans `cost_meta.usd` sert quand aucune ligne n'est rattachée.

AUCUN secret ne sort (banc test_recette_export [D]) : `nettoyer` retire tout champ nommé comme une clé (api_key, token,
secret, authorization…), remplace toute valeur de clé RÉELLEMENT posée dans les réglages, les formes connues (Bearer,
sk-…, clé fal), coupe la requête des URL (jetons signés) et réduit un chemin local à son nom de fichier.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

TYPES = ("job", "plan", "asset")
LIGNEE_PAS = 12                  # maillons remontés au plus (un cycle est coupé)
MAX_IMAGES = 24                  # images mises dans l'archive
COTE_IMAGE = 1024                # côté maximal d'une image réduite
MAX_PROMPT_PDF = 14              # lignes de prompt imprimées par étape dans le PDF (le SKILL.md le garde en entier)
MASQUE = "[secret masqué]"


class RecetteIntrouvable(LookupError):
    """Le job, le plan ou l'asset demandé n'existe pas (404)."""


class RecetteRefusee(ValueError):
    """Une demande mal formée : type inconnu, nom d'asset avec un dossier (400)."""


# ── Nettoyage : aucun secret, aucun chemin local ───────────────────────────────────────────────────────────────────

_CLE_SECRETE = re.compile(r"^(.*[_-])?(api[_-]?key|apikey|key|token|access[_-]?token|refresh[_-]?token|secret|password|"
                          r"passwd|authorization|auth|cookie|credentials?|signature|sig|bearer)$", re.I)
_FORMES = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=\-]{8,}", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{16,}\b", re.I),   # clé fal
    re.compile(r"\b(api[_-]?key|token|secret|password)\s*[=:]\s*\S{6,}", re.I),
]
_URL_REQUETE = re.compile(r"(https?://[^\s?#\"'<>]+)\?[^\s\"'<>]*")
_CHEMIN_WIN = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?:[^\s\"'<>|*?]+[\\/])*([^\s\"'<>|*?\\/]+)")
_CHEMIN_UNIX = re.compile(r"(?<![\w.])/(?:home|Users|tmp|var|mnt)/(?:[^\s\"'<>/]+/)*([^\s\"'<>/]+)")


def _valeurs_secretes() -> list[str]:
    """Les valeurs de clé RÉELLEMENT posées (réglages chargés depuis le coffre ou le .env), les plus longues d'abord."""
    vals = set()
    for nom in dir(settings):
        if nom.startswith("_") or not re.search(r"(KEY|TOKEN|SECRET|PASSWORD)", nom):
            continue
        try:
            v = getattr(settings, nom)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(v, str) and len(v.strip()) >= 6:
            vals.add(v.strip())
    return sorted(vals, key=len, reverse=True)


class _Nettoyeur:
    def __init__(self):
        self.secrets = _valeurs_secretes()
        self.masques = 0
        self.racines = [str(p) for p in {settings.images_path, settings.outputs_path, Path(settings.outputs_path).parent}
                        if p]

    def texte(self, s: str) -> str:
        avant = s
        for v in self.secrets:
            if v in s:
                s = s.replace(v, MASQUE)
        for f in _FORMES:
            s = f.sub(MASQUE, s)
        s = _URL_REQUETE.sub(r"\1", s)
        s = _CHEMIN_WIN.sub(r"\1", s)
        s = _CHEMIN_UNIX.sub(r"\1", s)
        if s != avant and MASQUE in s and MASQUE not in avant:
            self.masques += 1
        return s

    def __call__(self, v):
        if isinstance(v, dict):
            out = {}
            for k, x in v.items():
                if isinstance(k, str) and _CLE_SECRETE.match(k.strip()):
                    self.masques += 1
                    continue
                out[k] = self(x)
            return out
        if isinstance(v, (list, tuple)):
            return [self(x) for x in v]
        if isinstance(v, str):
            return self.texte(v)
        return v


def nettoyer(v):
    """Le même objet sans secret ni chemin local (voir l'en-tête)."""
    return _Nettoyeur()(v)


# ── Lectures ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _json(brut) -> dict:
    if isinstance(brut, dict):
        return brut
    try:
        v = json.loads(brut or "{}")
    except (TypeError, ValueError):
        return {}
    return v if isinstance(v, dict) else {}


def _iso(d) -> str | None:
    return d.isoformat(timespec="seconds") if isinstance(d, datetime) else None


def _endpoint(modele: str | None) -> str | None:
    """L'endpoint fal d'un modèle vidéo connu (registre des références, puis registre vidéo)."""
    if not modele:
        return None
    try:
        from app.services import video_refs
        m = video_refs.REGISTRE_REFS.get(modele)
        if m and m.get("endpoint"):
            return m["endpoint"]
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services import fal_service
        m = fal_service.VIDEO_MODELS.get(modele)
        if isinstance(m, dict) and m.get("endpoint"):
            return str(m["endpoint"])
    except Exception:  # noqa: BLE001
        pass
    return None


async def _lignes_couts(refs: list[str]) -> list:
    """Les lignes du registre des dépenses rattachées à ces références (l'id même, ou « préfixe:id »)."""
    from sqlalchemy import or_, select
    from app.services.storage import Depense, async_session_factory
    refs = [r for r in dict.fromkeys(refs) if r]
    if not refs:
        return []
    conds = [Depense.ref == r for r in refs] + [Depense.ref.like(f"%:{r}") for r in refs]
    async with async_session_factory() as s:
        return (await s.execute(select(Depense).where(or_(*conds)).order_by(Depense.quand, Depense.id))).scalars().all()


def _couts(lignes, devis: float | None = None) -> dict:
    """Estimé, réel, effectif (réel là où il existe, estimé ailleurs) et l'état, comme Réglages › Dépenses."""
    est = round(sum(float(l.estime_usd or 0) for l in lignes), 6)
    reelles = [l for l in lignes if l.reel_usd is not None]
    reel = round(sum(float(l.reel_usd) for l in reelles), 6)
    eff = round(sum(float(l.reel_usd) if l.reel_usd is not None else float(l.estime_usd or 0) for l in lignes), 6)
    if lignes:
        etat = "reel" if len(reelles) == len(lignes) else ("reel-partiel" if reelles else "estime")
    elif devis:
        etat, est, eff = "devis", round(float(devis), 6), round(float(devis), 6)
    else:
        etat = "inconnu"
    return {"estime_usd": est, "reel_usd": reel if reelles else None, "effectif_usd": eff, "etat": etat,
            "lignes": len(lignes), "lignes_reelles": len(reelles),
            "moteurs": sorted({str(l.moteur) for l in lignes})}


async def _assets(**filtre) -> list:
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    q = select(LibraryAsset)
    for k, v in filtre.items():
        q = q.where(getattr(LibraryAsset, k) == v)
    async with async_session_factory() as s:
        return (await s.execute(q)).scalars().all()


async def _provenance(nom: str | None) -> dict | None:
    """Ce que la Bibliothèque sait d'un fichier d'entrée : source, relation, mère."""
    if not nom:
        return None
    from app.services.storage import LibraryAsset, async_session_factory
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, Path(str(nom)).name)
    if row is None:
        return {"nom": Path(str(nom)).name}
    return {"nom": row.filename, "source": row.source, "relation": row.relation, "mere": row.parent_filename,
            "job_id": row.job_id}


async def _entree(nom, role: str) -> dict | None:
    if not nom:
        return None
    p = await _provenance(nom)
    return {"nom": Path(str(nom)).name, "role": role, "provenance": p}


def _chemin_video(job) -> Path | None:
    for v in (getattr(job, "final_video_path", None), getattr(job, "video_path", None)):
        if v and Path(str(v)).is_file():
            return Path(str(v))
    return None


async def _etape_job(job, genre: str | None = None, ordre: int = 0) -> dict:
    """Une étape reproductible depuis un JobRecord (ce qu'on sait, rien d'inventé)."""
    import asyncio
    from app.services import recette_rendu
    rc = await asyncio.to_thread(recette_rendu.recette, job)
    meta = _json(job.cost_meta)
    lib = {}
    sortie = None
    for row in await _assets(job_id=job.id):
        r = _json(row.recette)
        if r and not lib:
            lib = r
        sortie = sortie or row.filename
    fv = getattr(job, "final_video_path", None) or getattr(job, "video_path", None)
    if fv and not sortie:
        sortie = Path(str(fv)).name
    modele = rc.get("model") or lib.get("modele") or lib.get("model") or meta.get("modele")
    params = {k: v for k, v in {
        "duree_s": rc.get("duration_s"), "format": rc.get("aspect_ratio"), "style": rc.get("style"),
        "gabarit": rc.get("template_id"), "tache": lib.get("tache"), "resolution": lib.get("resolution"),
        "conform": lib.get("conform") or meta.get("conform"),
    }.items() if v not in (None, "", [], {})}
    entrees = []
    for nom, role in ((rc.get("image"), "image de départ"), (rc.get("image_end"), "image de fin"),
                      (lib.get("clip"), "clip de previs (@Video1)")):
        e = await _entree(nom, role)
        if e:
            entrees.append(e)
    for i, f in enumerate(lib.get("style_frames") or []):
        e = await _entree(f, f"style frame (@Image{i + 1})")
        if e:
            entrees.append(e)
    entrees = list({(e["nom"], e["role"]): e for e in entrees}.values())
    statut = {"done": "ok", "failed": "rate"}.get(str(job.status), str(job.status))
    prompt = rc.get("prompt_envoye") or rc.get("prompt") or lib.get("prompt")
    saisi = rc.get("prompt") if rc.get("prompt") and rc.get("prompt") != prompt else None
    lignes = await _lignes_couts([job.id])
    etape = {
        "genre": genre or (job.provider or "rendu"), "ordre": ordre, "titre": job.title or job.id,
        "job_id": job.id, "fichier": sortie, "statut": statut, "erreur": (job.error or None) if statut != "ok" else None,
        "quand": _iso(job.created_at), "modele": modele, "endpoint": lib.get("endpoint") or _endpoint(modele),
        "fournisseur": job.provider, "prompt": prompt, "prompt_saisi": saisi, "negatif": rc.get("negative"),
        "parametres": params, "graine": rc.get("seed") if rc.get("seed") is not None else lib.get("seed"),
        "entrees": entrees, "sorties": [sortie] if sortie else [],
        "arguments": lib.get("arguments") or None, "notes": [str(n) for n in (lib.get("notes") or [])],
        "recalage": lib.get("recalage") or meta.get("recalage"), "source_recette": rc.get("source"),
        "import": rc.get("import"), "cout": _couts(lignes, meta.get("usd")), "_lignes": [l.id for l in lignes],
        "_devis": meta.get("usd"), "_video": str(_chemin_video(job) or "") or None,
    }
    return etape


def _etape_fichier(row, genre: str, ordre: int = 0) -> dict:
    """Une étape depuis une ligne de la Bibliothèque (image du générateur, retouche…), sans job."""
    from app.services import library_fiche
    r = library_fiche._recette(row.filename, row.recette) or {}
    modele = r.get("model") or r.get("modele")
    params = {k: r[k] for k in ("size", "style", "background", "dur", "kind") if r.get(k) not in (None, "")}
    return {"genre": genre, "ordre": ordre, "titre": row.filename, "job_id": row.job_id, "fichier": row.filename,
            "statut": "ok", "erreur": None, "quand": _iso(getattr(row, "created", None)), "modele": modele,
            "endpoint": r.get("endpoint") or _endpoint(modele), "fournisseur": row.source,
            "prompt": r.get("prompt_envoye") or r.get("prompt"),
            "prompt_saisi": r.get("prompt") if r.get("prompt_envoye") else None, "negatif": r.get("negative"),
            "parametres": params, "graine": r.get("seed"), "relation": row.relation,
            "entrees": [], "sorties": [row.filename], "arguments": None, "notes": [], "recalage": None,
            "source_recette": r.get("origine"), "cout": _couts([]), "_lignes": [], "_devis": None, "_video": None}


async def _finir(dossier: dict, lignes_plus: list = ()) -> dict:
    """Coûts agrégés, ratés, entrées et sorties du dossier ; retire les champs internes."""
    from sqlalchemy import select
    from app.services.storage import Depense, async_session_factory
    ids = set()
    for e in dossier["etapes"]:
        ids.update(e.get("_lignes") or [])
    ids.update(l.id for l in lignes_plus)
    lignes = []
    if ids:
        async with async_session_factory() as s:
            lignes = (await s.execute(select(Depense).where(Depense.id.in_(sorted(ids))))).scalars().all()
    devis_sans_ligne = sum(float(e["_devis"] or 0) for e in dossier["etapes"] if e.get("_devis") and not e.get("_lignes"))
    c = _couts(lignes)
    if devis_sans_ligne:
        c["devis_sans_ligne_usd"] = round(devis_sans_ligne, 6)
        c["effectif_usd"] = round(c["effectif_usd"] + devis_sans_ligne, 6)
        if c["etat"] == "inconnu":
            c["etat"], c["estime_usd"] = "devis", round(devis_sans_ligne, 6)
    dossier["couts"] = c
    dossier["rates"] = [{"job_id": e.get("job_id"), "titre": e.get("titre"), "statut": e["statut"],
                         "erreur": e.get("erreur"), "quand": e.get("quand"), "modele": e.get("modele"),
                         "prompt": e.get("prompt")}
                        for e in dossier["etapes"] if e["statut"] not in ("ok",)] + dossier.pop("_essais", [])
    dossier["etapes"] = [e for e in dossier["etapes"] if e["statut"] == "ok"] or dossier["etapes"]
    for i, e in enumerate(dossier["etapes"], 1):
        e["ordre"] = i
    vus, entrees, sorties = set(), [], []
    for e in dossier["etapes"]:
        for x in e.get("entrees") or []:
            if x["nom"] not in vus:
                vus.add(x["nom"])
                entrees.append(x)
        sorties += [s for s in e.get("sorties") or [] if s not in sorties]
    dossier["entrees"], dossier["sorties"] = entrees, sorties
    dossier["videos"] = {Path(e["_video"]).name: e["_video"] for e in dossier["etapes"] if e.get("_video")}
    for e in dossier["etapes"]:
        for k in ("_lignes", "_devis", "_video"):
            e.pop(k, None)
    return dossier


def _base(type_: str, ident: str, titre: str) -> dict:
    return {"type": type_, "id": ident, "titre": titre, "exporte_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "application": "DeepotusVideo", "tache": "t346", "etapes": [], "_essais": []}


async def dossier_job(job_id: str) -> dict:
    from sqlalchemy import select
    from app.services.storage import JobRecord, async_session_factory
    async with async_session_factory() as s:
        job = await s.get(JobRecord, str(job_id or ""))
        if job is None:
            raise RecetteIntrouvable(f"rendu inconnu : {job_id}")
        freres = []
        if job.batch_id:
            freres = (await s.execute(select(JobRecord).where(JobRecord.batch_id == job.batch_id)
                                      .where(JobRecord.id != job.id).order_by(JobRecord.batch_index))).scalars().all()
    d = _base("job", job.id, job.title or job.id)
    d["etapes"].append(await _etape_job(job))
    for f in freres:   # les essais du même lot : rejetés (ratés) ou simplement non retenus
        d["_essais"].append({"job_id": f.id, "titre": f.title or f.id, "statut": "rate" if f.status == "failed" else "essai",
                             "erreur": f.error or None, "quand": _iso(f.created_at), "modele": f.video_model,
                             "prompt": f.final_prompt, "graine": f.seed, "note": f.rating})
    return await _finir(d)


async def dossier_plan(shot_id: str) -> dict:
    from sqlalchemy import select
    from app.services.storage import Chapter, JobRecord, LibraryAsset, Shot, async_session_factory
    async with async_session_factory() as s:
        sh = await s.get(Shot, str(shot_id or ""))
        if sh is None:
            raise RecetteIntrouvable(f"plan inconnu : {shot_id}")
        ch = await s.get(Chapter, sh.chapter_id) if sh.chapter_id else None
        ids = []
        rows = (await s.execute(select(LibraryAsset).where(LibraryAsset.job_id.is_not(None))
                                .where(LibraryAsset.recette.like(f'%{sh.id}%')))).scalars().all()
        ids += [r.job_id for r in rows if _json(r.recette).get("plan") == sh.id]
        cands = (await s.execute(select(JobRecord).where(JobRecord.cost_meta.like(f'%{sh.id}%')))).scalars().all()
        ids += [j.id for j in cands if _json(j.cost_meta).get("plan") == sh.id]
        if sh.video:
            ids.append(sh.video)
        jobs = [j for j in [await s.get(JobRecord, i) for i in dict.fromkeys(ids)] if j is not None]
        img_row = await s.get(LibraryAsset, sh.image) if sh.image else None
    action = (sh.action or "").strip()
    titre = " · ".join(x for x in ((ch.title if ch else ""), f"plan {sh.idx + 1 if sh.idx is not None else ''}".strip(),
                                    action[:80]) if x)
    d = _base("plan", sh.id, titre or sh.id)
    d["plan"] = {"chapitre": ch.title if ch else None, "rang": sh.idx, "action": action or None,
                 "cadrage": sh.shot_type, "camera": sh.camera_move, "duree_s": sh.duration_s,
                 "prompt_mouvement": sh.motion_prompt or None, "video": sh.video}
    if sh.sketch_image:
        d["etapes"].append({"genre": "croquis", "titre": "Croquis (FLUX, style storyboard)", "job_id": None,
                            "fichier": sh.sketch_image, "statut": "ok", "erreur": None, "quand": None, "modele": "flux",
                            "endpoint": None, "fournisseur": "fal", "prompt": None, "prompt_saisi": None,
                            "negatif": None, "parametres": {"cadrage": sh.shot_type, "camera": sh.camera_move},
                            "graine": sh.sketch_seed, "entrees": [], "sorties": [sh.sketch_image], "arguments": None,
                            "notes": ["prompt recomposé à chaque tir depuis le plan (cadrage, caméra, entités) : "
                                      "non gardé ; la graine l'est"], "recalage": None, "source_recette": "plan",
                            "cout": _couts([]), "_lignes": [], "_devis": None, "_video": None})
    if sh.image:
        e = _etape_fichier(img_row, "image") if img_row is not None and _json(img_row.recette) else {
            "genre": "image", "titre": "Image de production", "job_id": None, "fichier": sh.image, "statut": "ok",
            "erreur": None, "quand": None, "modele": None, "endpoint": None, "fournisseur": None,
            "prompt": None, "prompt_saisi": None, "negatif": None, "parametres": {}, "graine": None,
            "entrees": [], "sorties": [sh.image], "arguments": None, "notes": [], "recalage": None,
            "source_recette": "plan", "cout": _couts([]), "_lignes": [], "_devis": None, "_video": None}
        e["titre"] = "Image de production (vues des entités en référence)"
        e["prompt"] = e.get("prompt") or sh.prompt or None
        if sh.sketch_image:
            e["entrees"] = [await _entree(sh.sketch_image, "croquis")]
        d["etapes"].append(e)
    bornes = [x for x in [await _entree(sh.keyframe_image, "borne de début (Plateau 3D)"),
                          await _entree(sh.keyframe_end, "borne de fin (Plateau 3D)")] if x]
    for j in sorted(jobs, key=lambda j: j.created_at or datetime.min):
        e = await _etape_job(j, "previs" if j.provider == "previs" else "video")
        if j.provider != "previs":
            e["entrees"] = bornes + e["entrees"]
        if e["statut"] == "ok" and j.id != sh.video:
            e["statut"] = "essai"
            e["erreur"] = "remplacé par la vidéo actuelle du plan"
        d["etapes"].append(e)
    if bornes and not any(x["nom"] == bornes[0]["nom"] for e in d["etapes"] for x in e.get("entrees") or []):
        if d["etapes"]:
            d["etapes"][-1]["entrees"] = bornes + (d["etapes"][-1].get("entrees") or [])
    lignes_plan = await _lignes_couts([sh.id])
    return await _finir(d, lignes_plan)


def _nom_sur(nom: str) -> str:
    n = Path(str(nom or "")).name
    if not n or n != str(nom or "") or n in (".", "..") or any(c in str(nom) for c in "/\\:"):
        raise RecetteRefusee("nom d'asset refusé : un nom de fichier de la Bibliothèque, sans dossier")
    return n


async def dossier_asset(filename: str) -> dict:
    from sqlalchemy import or_, select
    from app.services import library_index
    from app.services.storage import JobRecord, LibraryAsset, async_session_factory
    nom = _nom_sur(filename)
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, nom)
        if row is None and library_index.du_magasin(nom) is None:
            raise RecetteIntrouvable(f"asset inconnu : {nom}")
        chaine, vus, cour = [], set(), nom
        for _ in range(LIGNEE_PAS):
            if cour in vus:
                break
            vus.add(cour)
            r = await s.get(LibraryAsset, cour)
            job = None
            if r is not None and r.job_id:
                job = await s.get(JobRecord, r.job_id)
            elif r is None:   # une mère hors de l'index : la vidéo d'un rendu
                jr = (await s.execute(select(JobRecord).where(or_(JobRecord.final_video_path.like(f"%{cour}"),
                                                                   JobRecord.video_path.like(f"%{cour}"))))).scalars().all()
                job = next((j for j in jr if cour in (Path(str(j.final_video_path or "")).name,
                                                       Path(str(j.video_path or "")).name)), None)
            chaine.append((cour, r, job))
            mere = r.parent_filename if r is not None else None
            if not mere:
                break
            cour = mere
    titre = nom
    d = _base("asset", nom, titre)
    for cour, r, job in reversed(chaine):          # racine d'abord
        if job is not None:
            e = await _etape_job(job)
            e["fichier"] = cour
            if r is not None:
                e["relation"] = r.relation
        elif r is not None:
            e = _etape_fichier(r, r.relation or r.source or "fichier")
        else:
            e = {"genre": "fichier", "titre": cour, "job_id": None, "fichier": cour, "statut": "ok", "erreur": None,
                 "quand": None, "modele": None, "endpoint": None, "fournisseur": None, "prompt": None,
                 "prompt_saisi": None, "negatif": None, "parametres": {}, "graine": None, "entrees": [],
                 "sorties": [cour], "arguments": None, "notes": ["fichier sans recette connue (import, antérieur)"],
                 "recalage": None, "source_recette": None, "cout": _couts([]), "_lignes": [], "_devis": None,
                 "_video": None}
        if r is not None and r.parent_filename:
            m = await _entree(r.parent_filename, f"mère ({r.relation or 'dérivé'})")
            if m and all(x["nom"] != m["nom"] for x in e["entrees"]):
                e["entrees"] = [m] + e["entrees"]
        d["etapes"].append(e)
    return await _finir(d)


async def dossier(type_: str, ident: str) -> dict:
    """Le dossier NETTOYÉ (aucun secret) d'un rendu, d'un plan ou d'un asset."""
    if type_ not in TYPES:
        raise RecetteRefusee(f"type inconnu : {type_} (job, plan ou asset)")
    if not str(ident or "").strip() or len(str(ident)) > 255:
        raise RecetteRefusee("identifiant manquant")
    fn = {"job": dossier_job, "plan": dossier_plan, "asset": dossier_asset}[type_]
    d = await fn(str(ident).strip())
    videos = d.pop("videos", {})
    n = _Nettoyeur()
    propre = n(d)
    propre["securite"] = {"secrets_masques": n.masques,
                          "regle": "aucune clé, aucun jeton, aucun chemin local (t346)"}
    propre["_videos"] = videos            # chemins locaux : pour les vignettes seulement, jamais écrits
    return propre


# ── SKILL.md ──────────────────────────────────────────────────────────────────────────────────────────────────────

L = {
    "fr": {"recette": "Recette", "exporte": "Exportée le {d} depuis DeepotusVideo (t346), gratuitement et en local.",
           "type": {"job": "rendu", "plan": "plan", "asset": "asset de la Bibliothèque"},
           "quand": "Utiliser pour refaire ou décliner « {t} » ({n} étape(s) : {m}) avec les prompts, modèles et graines exacts.",
           "resume": "Résumé", "etapes": "Étapes", "prompt": "Prompt exact envoyé", "saisi": "Prompt saisi",
           "negatif": "Négatif", "modele": "Modèle", "endpoint": "Endpoint", "graine": "Graine", "params": "Paramètres",
           "entrees": "Entrées", "sorties": "Sortie", "cout": "Coût", "statut": "Statut", "erreur": "Erreur",
           "rates": "Ratés et essais rejetés", "aucun_rate": "Aucun raté connu.", "couts": "Coûts",
           "provenance": "Provenance des entrées", "refaire": "Refaire dans DeepotusVideo", "fichiers": "Fichiers",
           "estime": "estimé", "reel": "réel", "effectif": "effectif", "etat": "état", "lignes": "lignes du registre",
           "inconnu": "inconnu", "non_garde": "non gardée", "recalage": "Recalage", "notes": "Notes",
           "arguments": "Arguments envoyés", "relation": "Relation", "quand_tir": "Tiré le", "job": "Job",
           "plan_info": "Plan", "devis": "devis", "etats": {"reel": "réel", "reel-partiel": "réel partiel",
                                                           "estime": "estimé", "devis": "devis", "inconnu": "inconnu"},
           "graine_note": "même modèle + même graine + même prompt = le même tirage chez la plupart des modèles",
           "pdf": "making-of illustré (vignettes, chronologie, coûts)", "json": "le dossier lisible par une machine",
           "images": "images d'entrée et de sortie réduites",
           "refaire_job": "Bibliothèque › fiche du rendu › « Recette » : Quick ou Studio (le coût est réestimé au tarif du jour).",
           "refaire_plan": "Chapitres › le plan › « Previs → plan » (devis gratuit, puis confirmation du coût).",
           "refaire_asset": "Bibliothèque › fiche de l'asset › « Rejouer » quand la recette vient du générateur.",
           "provenance_de": "source {s}", "mere": "mère {m}", "etapes_n": "{n} étape(s)", "rates_n": "{n} raté(s) ou essai(s)",
           "securite": "Secrets masqués à l'export : {n}."},
    "en": {"recette": "Recipe", "exporte": "Exported on {d} from DeepotusVideo (t346), free and local.",
           "type": {"job": "render", "plan": "shot", "asset": "Library asset"},
           "quand": "Use to remake or vary \"{t}\" ({n} step(s): {m}) with the exact prompts, models and seeds.",
           "resume": "Summary", "etapes": "Steps", "prompt": "Exact prompt sent", "saisi": "Prompt as typed",
           "negatif": "Negative", "modele": "Model", "endpoint": "Endpoint", "graine": "Seed", "params": "Parameters",
           "entrees": "Inputs", "sorties": "Output", "cout": "Cost", "statut": "Status", "erreur": "Error",
           "rates": "Failures and rejected tries", "aucun_rate": "No known failure.", "couts": "Costs",
           "provenance": "Input provenance", "refaire": "Remake in DeepotusVideo", "fichiers": "Files",
           "estime": "estimated", "reel": "actual", "effectif": "effective", "etat": "state", "lignes": "ledger lines",
           "inconnu": "unknown", "non_garde": "not kept", "recalage": "Realignment", "notes": "Notes",
           "arguments": "Arguments sent", "relation": "Relation", "quand_tir": "Run on", "job": "Job",
           "plan_info": "Shot", "devis": "quote", "etats": {"reel": "actual", "reel-partiel": "partly actual",
                                                           "estime": "estimated", "devis": "quote", "inconnu": "unknown"},
           "graine_note": "same model + same seed + same prompt = the same draw on most models",
           "pdf": "illustrated making-of (thumbnails, timeline, costs)", "json": "the machine-readable record",
           "images": "downsized input and output images",
           "refaire_job": "Library › render card › \"Recipe\": Quick or Studio (the cost is re-estimated at today's price).",
           "refaire_plan": "Chapters › the shot › \"Previs → shot\" (free quote, then cost confirmation).",
           "refaire_asset": "Library › asset card › \"Replay\" when the recipe comes from the generator.",
           "provenance_de": "source {s}", "mere": "parent {m}", "etapes_n": "{n} step(s)", "rates_n": "{n} failure(s) or try(ies)",
           "securite": "Secrets masked on export: {n}."},
}


def _lang(lang) -> str:
    return "en" if str(lang or "").lower().startswith("en") else "fr"


def _usd(v) -> str:
    return "—" if v is None else f"{float(v):.2f} $" if float(v) >= 0.1 or float(v) == 0 else f"{float(v):.4f} $"


def slug(texte: str, ident: str = "") -> str:
    """Le `name` du skill : minuscules, chiffres et tirets, 64 caractères au plus."""
    texte = re.sub(r"\.(png|jpe?g|webp|gif|mp4|webm|mov|wav|mp3|flac|ogg)$", "", str(texte or ""), flags=re.I)
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    suf = re.sub(r"[^a-z0-9]+", "", str(ident or "").lower())[:8]
    if suf and suf in t.replace("-", ""):      # un asset : son nom EST déjà le titre
        suf = ""
    base = "recette-" + (t[:40].strip("-") or "deepotus")
    nom = f"{base}-{suf}" if suf else base
    return re.sub(r"-+", "-", nom)[:64].strip("-")


def _ligne_cout(c: dict, T: dict) -> str:
    etat = T["etats"].get(c.get("etat"), c.get("etat"))
    if c.get("etat") in (None, "inconnu"):       # rien au registre ni devis : on ne l'écrit pas « 0 $ »
        return f"{T['inconnu']} (0 {T['lignes']})"
    parts = [f"{T['estime']} {_usd(c.get('estime_usd'))}"]
    if c.get("reel_usd") is not None:
        parts.append(f"{T['reel']} {_usd(c.get('reel_usd'))}")
    parts.append(f"{T['effectif']} {_usd(c.get('effectif_usd'))}")
    return " · ".join(parts) + f" ({etat}, {c.get('lignes', 0)} {T['lignes']})"


def _fmt_param(v) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k} = {x}" for k, x in v.items())
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def skill_md(d: dict, lang: str = "fr") -> str:
    T = L[_lang(lang)]
    nom = slug(d.get("titre") or d.get("id"), d.get("id"))
    modeles = sorted({e["modele"] for e in d["etapes"] if e.get("modele")})
    desc = T["quand"].format(t=str(d.get("titre") or d.get("id"))[:120], n=len(d["etapes"]),
                             m=", ".join(modeles) or T["inconnu"])
    c = d.get("couts") or {}
    desc += (f" {T['cout']} : {T['inconnu']}." if c.get("etat") in (None, "inconnu") else
             f" {T['cout']} : {_usd(c.get('effectif_usd'))} ({T['etats'].get(c.get('etat'), c.get('etat'))}).")
    desc = desc.replace("\n", " ")[:1024]
    o = ["---", f"name: {nom}", f"description: {desc}", "---", "",
         f"# {T['recette']} — {d.get('titre') or d.get('id')}", "",
         T["exporte"].format(d=d.get("exporte_le", "")[:10]) + f" {T['type'].get(d['type'], d['type'])} `{d['id']}`.", "",
         f"## {T['resume']}", "",
         f"- {T['etapes_n'].format(n=len(d['etapes']))} ; {T['rates_n'].format(n=len(d.get('rates') or []))}",
         f"- {T['couts']} : {_ligne_cout(c, T)}"]
    if d.get("plan"):
        p = d["plan"]
        o.append(f"- {T['plan_info']} : " + " · ".join(str(x) for x in (p.get("chapitre"), p.get("action"),
                                                                           p.get("cadrage"), p.get("camera"),
                                                                           f"{_fmt_param(p.get('duree_s'))} s")
                                                          if x not in (None, "", "None s")))
    o += ["", f"## {T['etapes']}", ""]
    for e in d["etapes"]:
        o.append(f"### {e['ordre']}. {e.get('titre') or e.get('genre')}" + (f" — {e['modele']}" if e.get("modele") else ""))
        o.append("")
        if e.get("modele"):
            o.append(f"- {T['modele']} : `{e['modele']}`" + (f" · {T['endpoint']} : `{e['endpoint']}`" if e.get("endpoint") else ""))
        if e.get("job_id"):
            o.append(f"- {T['job']} : `{e['job_id']}`" + (f" · {T['quand_tir']} {e['quand'][:16].replace('T', ' ')}" if e.get("quand") else ""))
        if e.get("relation"):
            o.append(f"- {T['relation']} : {e['relation']}")
        o.append(f"- {T['graine']} : " + (f"`{e['graine']}` ({T['graine_note']})" if e.get("graine") is not None else T["non_garde"]))
        if e.get("parametres"):
            o.append(f"- {T['params']} :")
            for k, v in e["parametres"].items():
                o.append(f"  - {k} : {_fmt_param(v)}{' s' if k == 'duree_s' else ''}")
        if e.get("entrees"):
            o.append(f"- {T['entrees']} : " + ", ".join(f"`{x['nom']}` ({x['role']})" for x in e["entrees"]))
        if e.get("sorties"):
            o.append(f"- {T['sorties']} : " + ", ".join(f"`{s}`" for s in e["sorties"]))
        o.append(f"- {T['cout']} : {_ligne_cout(e.get('cout') or {}, T)}")
        if e.get("recalage"):
            rc = e["recalage"]
            o.append(f"- {T['recalage']} : " + (rc.get("phrase") or "") +
                     (f" (dérive {rc.get('derive_images')} image(s), score {rc.get('score')})" if "derive_images" in rc else
                      f" ({rc.get('erreur')})" if rc.get("erreur") else ""))
        o.append("")
        if e.get("prompt"):
            o += [f"{T['prompt']} :", "", "```text", str(e["prompt"]), "```", ""]
        if e.get("prompt_saisi"):
            o += [f"{T['saisi']} :", "", "```text", str(e["prompt_saisi"]), "```", ""]
        if e.get("negatif"):
            o += [f"{T['negatif']} :", "", "```text", str(e["negatif"]), "```", ""]
        if e.get("arguments"):
            o += [f"{T['arguments']} :", "", "```json", json.dumps(e["arguments"], ensure_ascii=False, indent=1), "```", ""]
        if e.get("notes"):
            o += [f"{T['notes']} :", ""] + [f"- {n}" for n in e["notes"]] + [""]
    o += [f"## {T['rates']}", ""]
    if d.get("rates"):
        for x in d["rates"]:
            o.append(f"- `{x.get('job_id')}` — {x.get('titre')} · {T['statut']} : {x.get('statut')}"
                     + (f" · {T['modele']} : `{x['modele']}`" if x.get("modele") else "")
                     + (f" · {T['graine']} : {x['graine']}" if x.get("graine") is not None else "")
                     + (f" · {T['erreur']} : {x['erreur']}" if x.get("erreur") else ""))
    else:
        o.append(T["aucun_rate"])
    o += ["", f"## {T['couts']}", "", f"| | {T['estime']} | {T['reel']} | {T['effectif']} | {T['etat']} |",
          "|---|---|---|---|---|"]
    for e in d["etapes"]:
        ce = e.get("cout") or {}
        if ce.get("etat") in (None, "inconnu"):
            o.append(f"| {e['ordre']}. {e.get('genre')} | — | — | — | {T['etats']['inconnu']} |")
            continue
        o.append(f"| {e['ordre']}. {e.get('genre')} | {_usd(ce.get('estime_usd'))} | {_usd(ce.get('reel_usd'))} | "
                 f"{_usd(ce.get('effectif_usd'))} | {T['etats'].get(ce.get('etat'), ce.get('etat'))} |")
    o.append(f"| **Total** | {_usd(c.get('estime_usd'))} | {_usd(c.get('reel_usd'))} | {_usd(c.get('effectif_usd'))} | "
             f"{T['etats'].get(c.get('etat'), c.get('etat'))} |")
    o += ["", f"## {T['provenance']}", ""]
    for x in d.get("entrees") or []:
        p = x.get("provenance") or {}
        bits = [T["provenance_de"].format(s=p["source"])] if p.get("source") else []
        if p.get("relation"):
            bits.append(p["relation"])
        if p.get("mere"):
            bits.append(T["mere"].format(m=p["mere"]))
        o.append(f"- `{x['nom']}` — {x['role']}" + (f" ({', '.join(bits)})" if bits else ""))
    if not d.get("entrees"):
        o.append("—")
    o += ["", f"## {T['refaire']}", "", "- " + T["refaire_" + d["type"]], "",
          f"## {T['fichiers']}", "", f"- `fabrication.pdf` — {T['pdf']}", f"- `recette.json` — {T['json']}",
          f"- `images/` — {T['images']}", "", T["securite"].format(n=(d.get("securite") or {}).get("secrets_masques", 0)), ""]
    return "\n".join(o)


# ── Images réduites ───────────────────────────────────────────────────────────────────────────────────────────────

def _jpeg(src: Path | bytes) -> bytes | None:
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(src) if isinstance(src, bytes) else src)
        im.load()
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            fond = Image.new("RGB", im.size, (255, 255, 255))
            fond.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3])
            im = fond
        else:
            im = im.convert("RGB")
        im.thumbnail((COTE_IMAGE, COTE_IMAGE))
        b = io.BytesIO()
        im.save(b, "JPEG", quality=82, optimize=True)
        return b.getvalue()
    except Exception:  # noqa: BLE001 — une image illisible ne casse pas l'export
        return None


def _image_video(p: Path) -> bytes | None:
    """Une image de la vidéo (ffmpeg, s'il est là) ; None sinon."""
    try:
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "v.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", str(p), "-frames:v", "1", str(out)],
                           capture_output=True, timeout=60)
            return _jpeg(out.read_bytes()) if out.is_file() else None
    except (OSError, subprocess.SubprocessError):
        return None


def images(d: dict) -> dict[str, bytes]:
    """{nom.jpg: octets} des entrées et sorties connues, réduites (MAX_IMAGES au plus)."""
    out: dict[str, bytes] = {}
    videos = d.get("_videos") or {}
    for nom in [x["nom"] for x in d.get("entrees") or []] + list(d.get("sorties") or []):
        if len(out) >= MAX_IMAGES:
            break
        n = Path(str(nom)).name
        cle = Path(n).stem + ".jpg"
        if not n or cle in out:
            continue
        p = settings.images_path / n
        b = None
        if p.is_file():
            b = _jpeg(p)
        elif n in videos and Path(videos[n]).is_file():
            b = _image_video(Path(videos[n]))
        if b:
            out[cle] = b
    return out


# ── fabrication.pdf ───────────────────────────────────────────────────────────────────────────────────────────────

def _or(doc, x, y, l, h):
    """Un aplat or Deepotus (#f0b429), en opérateur PDF brut (pdf_compose ne remplit qu'en gris)."""
    doc._p["ops"].append(f"q 0.941 0.706 0.161 rg {x:.2f} {doc.h - y - h:.2f} {l:.2f} {h:.2f} re f Q".encode("ascii"))


def fabrication_pdf(d: dict, imgs: dict[str, bytes], lang: str = "fr") -> bytes:
    from app.services import pdf_compose as PC
    T = L[_lang(lang)]
    doc = PC.Document(PC.A4)
    W, H, M = doc.l, doc.h, 42.0
    y = [M]

    def place(h):
        if y[0] + h > H - M:
            doc.nouvelle_page()
            _or(doc, 0, 0, W, 6)
            y[0] = M

    def para(t, police="H", taille=9.5, gris=None, interl=1.35, x=M, larg=None, max_lignes=None):
        larg = larg or (W - x - M)
        lignes = []
        for p in str(t).split("\n"):
            lignes += PC.couper(p, police, taille, larg)
        if max_lignes and len(lignes) > max_lignes:
            lignes = lignes[:max_lignes - 1] + [lignes[max_lignes - 1][:80] + " …"]
        for li in lignes:
            place(taille * interl)
            y[0] += taille * interl
            doc.texte(x, y[0], li, police, taille, gris)

    def image_tmp(nom, x, yy, l, h):
        b = imgs.get(Path(str(nom)).stem + ".jpg")
        if not b:
            return None
        return doc.image(io.BytesIO(b), x, yy, l, h, dpi=110)

    # page 1 : titre, résumé, sorties
    _or(doc, 0, 0, W, 6)
    y[0] = M + 14
    doc.texte(M, y[0], "DEEPOTUS · " + T["recette"].upper() + " · " + T["type"].get(d["type"], d["type"]).upper(), "HB", 9, 0.45)
    y[0] += 26
    para(str(d.get("titre") or d.get("id")), "HB", 20, None, 1.2)
    y[0] += 6
    para(T["exporte"].format(d=str(d.get("exporte_le", ""))[:10]), "H", 9, 0.45)
    c = d.get("couts") or {}
    y[0] += 10
    doc.trait(M, y[0], W - M, y[0], 0.6, 0.8)
    y[0] += 4
    para(f"{T['etapes_n'].format(n=len(d['etapes']))}  ·  {T['rates_n'].format(n=len(d.get('rates') or []))}", "HB", 11)
    para(f"{T['couts']} : {_ligne_cout(c, T)}", "H", 10)
    if d.get("plan") and d["plan"].get("action"):
        para(f"{T['plan_info']} : {d['plan']['action']}", "H", 10)
    sorties = [s for s in d.get("sorties") or [] if imgs.get(Path(str(s)).stem + ".jpg")][-3:]
    if sorties:
        y[0] += 14
        larg = (W - 2 * M - 12 * (len(sorties) - 1)) / len(sorties)
        hb = min(360.0, H - M - y[0] - 20)
        for i, s in enumerate(sorties):
            image_tmp(s, M + i * (larg + 12), y[0], larg, hb)
        y[0] += hb + 4
        for i, s in enumerate(sorties):
            doc.texte(M + i * (larg + 12), y[0] + 10, str(s)[:48], "H", 7.5, 0.45)

    # chronologie : une boîte par étape (vignettes à gauche, texte à droite)
    doc.nouvelle_page()
    _or(doc, 0, 0, W, 6)
    y[0] = M + 10
    para(T["etapes"], "HB", 15)
    y[0] += 6
    VL = 120.0
    for e in d["etapes"]:
        place(150)
        haut = y[0] + 6
        _or(doc, M, haut, 3, 14)
        doc.texte(M + 10, haut + 11, f"{e['ordre']}. {str(e.get('titre') or e.get('genre'))[:80]}", "HB", 11)
        y[0] = haut + 18
        vis = (e.get("sorties") or [])[:1] + [x["nom"] for x in (e.get("entrees") or [])][:2]
        yv = y[0] + 4
        for nomv in vis:
            if image_tmp(nomv, M, yv, VL, 80):
                yv += 86
        x_txt = M + VL + 14
        larg = W - x_txt - M
        lignes = []
        if e.get("modele"):
            lignes.append((f"{T['modele']} : {e['modele']}" + (f"  ·  {e['endpoint']}" if e.get("endpoint") else ""), "C", 8))
        if e.get("quand"):
            lignes.append((f"{T['quand_tir']} {e['quand'][:16].replace('T', ' ')}", "H", 8.5))
        lignes.append((f"{T['graine']} : {e['graine'] if e.get('graine') is not None else T['non_garde']}", "H", 8.5))
        for k, v in (e.get("parametres") or {}).items():
            lignes.append((f"{k} : {_fmt_param(v)}", "H", 8.5))
        if e.get("entrees"):
            lignes.append((f"{T['entrees']} : " + ", ".join(x["nom"] for x in e["entrees"]), "H", 8.5))
        lignes.append((f"{T['cout']} : {_ligne_cout(e.get('cout') or {}, T)}", "H", 8.5))
        if e.get("recalage") and e["recalage"].get("phrase"):
            lignes.append((f"{T['recalage']} : {e['recalage']['phrase']}", "H", 8.5))
        for t, pol, ta in lignes:
            para(t, pol, ta, None, 1.3, x_txt, larg)
        if e.get("prompt"):
            y[0] += 4
            para(T["prompt"], "HB", 8.5, 0.35, 1.3, x_txt, larg)
            para(str(e["prompt"]), "C", 7.8, None, 1.3, x_txt, larg, MAX_PROMPT_PDF)
        y[0] = max(y[0], yv) + 10
        doc.trait(M, y[0], W - M, y[0], 0.4, 0.85)

    # ratés et coûts
    doc.nouvelle_page()
    _or(doc, 0, 0, W, 6)
    y[0] = M + 10
    para(T["rates"], "HB", 15)
    y[0] += 4
    if d.get("rates"):
        for x in d["rates"]:
            para(f"{x.get('job_id')} — {x.get('titre')} · {x.get('statut')}" + (f" · {x['erreur']}" if x.get("erreur") else ""),
                 "H", 9)
    else:
        para(T["aucun_rate"], "H", 9, 0.45)
    y[0] += 16
    para(T["couts"], "HB", 15)
    y[0] += 8
    cols = [M, M + 220, M + 300, M + 380, M + 460]
    place(16)
    y[0] += 12
    for x, t in zip(cols, ["", T["estime"], T["reel"], T["effectif"], T["etat"]]):
        doc.texte(x, y[0], t, "HB", 9)
    for e in d["etapes"] + [{"ordre": "", "genre": "Total", "cout": c}]:
        ce = e.get("cout") or {}
        place(14)
        y[0] += 14
        doc.texte(cols[0], y[0], f"{e['ordre']}{'. ' if e['ordre'] != '' else ''}{e.get('genre')}"[:40],
                  "HB" if e["genre"] == "Total" else "H", 9)
        inc = ce.get("etat") in (None, "inconnu")
        for x, v in zip(cols[1:4], (ce.get("estime_usd"), ce.get("reel_usd"), ce.get("effectif_usd"))):
            doc.texte(x, y[0], "—" if inc else _usd(v), "H", 9)
        doc.texte(cols[4], y[0], str(T["etats"].get(ce.get("etat"), ce.get("etat") or "")), "H", 9)
    y[0] += 20
    para(T["securite"].format(n=(d.get("securite") or {}).get("secrets_masques", 0)), "H", 8, 0.45)
    return doc.octets(titre=f"{T['recette']} — {d.get('titre') or d.get('id')}")


# ── L'archive ─────────────────────────────────────────────────────────────────────────────────────────────────────

def archive(d: dict, lang: str = "fr") -> tuple[str, bytes]:
    """(nom du fichier .zip, octets) : <nom>/SKILL.md, fabrication.pdf, recette.json, images/*.jpg."""
    nom = slug(d.get("titre") or d.get("id"), d.get("id"))
    imgs = images(d)
    public = {k: v for k, v in d.items() if not k.startswith("_")}
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{nom}/SKILL.md", skill_md(public, lang))
        z.writestr(f"{nom}/fabrication.pdf", fabrication_pdf(public, imgs, lang))
        z.writestr(f"{nom}/recette.json", json.dumps(public, ensure_ascii=False, indent=1))
        for k, v in imgs.items():
            z.writestr(f"{nom}/images/{k}", v)
    return f"{nom}.zip", b.getvalue()


def apercu(d: dict, lang: str = "fr") -> dict:
    """Ce que l'écran et l'agent lisent : le dossier public + le texte du SKILL.md + le lien de l'export."""
    from urllib.parse import quote
    public = {k: v for k, v in d.items() if not k.startswith("_")}
    nom = slug(d.get("titre") or d.get("id"), d.get("id"))
    return public | {"nom": nom, "skill_md": skill_md(public, lang),
                     "export": f"/api/recettes/export?type={d['type']}&id={quote(str(d['id']))}&lang={_lang(lang)}"}
