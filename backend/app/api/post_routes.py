"""Post-traitement de Son & VFX — routes de la pile (t276, 22/10/2026), montées sous /api/post.

  GET    /catalogue        les 15 presets (effects_engine.POST_PILE), bornes traduites, LUT .cube disponibles
  GET    /sources          {rendus, vfx, particules} : rendus vidéo finis, résultats VFX IA, particules (webm alpha)
  POST   /apercu           body {source: job_id, pile, t?, largeur?} → image/png de la pile à l'instant t
  POST   /rendre           body {source, pile, titre?} → {job_id, usd: 0} ; le job rend en ffmpeg local, gratuit, vers
                           outputs/final, et range la vidéo dans la Bibliothèque (relation « post », mère = la source)
  POST   /lut              multipart `fichier` (.cube, 20 Mo au plus, LUT_3D_SIZE présent) → {nom, luts} : la LUT
                           rejoint le dossier des LUT (settings.luts_path), le seul que le moteur lit
  GET    /presets          les piles enregistrées
  POST   /presets          body {nom, pile} → la pile enregistrée
  DELETE /presets/{id}     supprime une pile enregistrée (404 si absente)
t277 (22/10/2026) — générateurs IA selon les clés (services/post_ia.py) :
  GET    /generateurs      {generateurs, moteurs_texte} : les générateurs vidéo → vidéo du catalogue_ia par fournisseur
                           (fal, decart, elevenlabs), listés SANS clé aussi (dispo False, clé nommée), et les moteurs de
                           texte de « Décrire le look »
  POST   /devis            body {source, pile} → {usd, lignes, cles, ia} : le devis des maillons IA actifs (gratuit)
  POST   /decrire          body {phrase, moteur?, modele?} → {propose: true, moteur, pile} : une pile de presets LOCAUX
                           PROPOSÉE par le moteur de texte (tirer_garde, catégorie « son ») ; rien n'est appliqué
  /rendre accepte des maillons IA {ia, prompt, options, masque} : PAYANT. Ordre des refus : pile 400 → clé absente 503
  (avant toute garde) → consigne / options 400 → source refusée par un générateur 400 → `confirme_cout` absent 409 (avec
  le devis) → garde des plafonds 402 → job (provider « post »). /apercu ignore les maillons IA (rendu seulement).
Refus : id de source hostile 400, job inconnu 404, job pas fini 409, job sans vidéo (planche sprite) 404, pile refusée
400. Une pile de presets locaux est gratuite : aucun plafond. Les écritures hors de la boucle locale sont refusées par la garde de main.py.
"""
import asyncio
import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings
from app.services import effects_engine as FX
from app.services import library_index as LI
from app.services import plafonds as _PLAF
from app.services import post_ia as PI
from app.services import post_pile as PP

router = APIRouter()


def _require_local_depense(request: Request) -> None:
    """t277 : la garde des routes qui dépensent (celle de routes.py), posée sur /rendre."""
    from app.api.routes import _require_local_depense as _rl
    _rl(request)

#: Extensions d'une vidéo de rendu acceptée comme source.
_VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".mkv", ".webm")
#: Sources listées par famille, les plus récentes d'abord.
_SOURCES_MAX = 60
#: Les rendus en cours (référence gardée : une tâche asyncio sans référence peut être ramassée).
_TACHES: set = set()


async def _corps(request: Request) -> dict:
    try:
        d = await request.json()
    except Exception:
        d = None
    return d if isinstance(d, dict) else {}


@router.get("/catalogue")
async def catalogue(request: Request = None):
    from app.i18n import langue_requete
    from app.i18n.catalogues import _t, _lang, slug
    lang = _lang(langue_requete(request))
    pres = FX.post_catalogue()
    for p in pres:
        for b in p["bounds"].values():
            if isinstance(b.get("label"), str):
                b["label"] = _t("effets.param." + slug(b["label"]), b["label"], lang)
    luts = sorted(f.name for f in settings.luts_path.glob("*.cube") if f.is_file())
    return {"presets": pres, "luts": luts, "pile_max": PP.PILE_MAX}


def _particules_webm(jr) -> Path | None:
    """Le webm alpha d'un job de particules (provider sprite2d, cost_meta.kind « particles »), ou None."""
    try:
        meta = json.loads(jr.cost_meta or "{}")
    except (TypeError, ValueError):
        meta = {}
    if jr.provider != "sprite2d" or meta.get("kind") != "particles" or not jr.final_video_path:
        return None
    w = Path(jr.final_video_path).parent / "alpha.webm"
    return w if w.is_file() else None


def _video(jr) -> Path | None:
    if jr.provider == "sprite2d":
        return _particules_webm(jr)
    fp = jr.final_video_path or jr.video_path
    p = Path(fp) if fp else None
    return p if p is not None and p.suffix.lower() in _VIDEO_EXTS and p.is_file() else None


def _fiche(jr, p: Path) -> dict | None:
    try:
        i = PP.infos(p)
    except Exception:  # noqa: BLE001 — une source illisible n'est pas listée
        return None
    return {"job_id": jr.id, "titre": jr.title or p.stem, "provider": jr.provider, "dur": round(i["dur"], 2),
            "w": i["w"], "h": i["h"], "alpha": p.suffix.lower() == ".webm",
            "date": jr.completed_at.isoformat() if jr.completed_at else None}


@router.get("/sources")
async def sources():
    from sqlalchemy import select
    from app.services.storage import JobRecord, async_session_factory
    async with async_session_factory() as s:
        rows = (await s.execute(select(JobRecord).where(JobRecord.status == "done")
                                .order_by(JobRecord.completed_at.desc(), JobRecord.created_at.desc())
                                .limit(400))).scalars().all()
    out = {"rendus": [], "vfx": [], "particules": []}
    for jr in rows:
        p = _video(jr)
        if p is None:
            continue
        fam = ["particules"] if jr.provider == "sprite2d" else (["rendus", "vfx"] if jr.provider == "vfx_ia" else ["rendus"])
        if all(len(out[f]) >= _SOURCES_MAX for f in fam):
            continue
        fiche = await asyncio.to_thread(_fiche, jr, p)
        if fiche is None:
            continue
        for f in fam:
            if len(out[f]) < _SOURCES_MAX:
                out[f].append(fiche)
    return out


async def _source(job_id):
    """(vidéo, job) de la source demandée, ou HTTPException."""
    from app.services.storage import JobRecord, async_session_factory
    jid = str(job_id or "").strip()
    if not jid or len(jid) > 64 or not re.fullmatch(r"[A-Za-z0-9_-]+", jid):
        raise HTTPException(400, "source refusée : donnez le job_id d'un rendu")
    async with async_session_factory() as s:
        jr = await s.get(JobRecord, jid)
    if jr is None:
        raise HTTPException(404, "rendu introuvable")
    if jr.status != "done":
        raise HTTPException(409, "ce rendu n'est pas terminé")
    p = _video(jr)
    if p is None:
        raise HTTPException(404, "ce rendu n'a pas de vidéo à post-traiter")
    return p, jr


@router.post("/apercu")
async def apercu(request: Request):
    d = await _corps(request)
    p, _ = await _source(d.get("source"))
    try:
        loc = PI.locaux(d.get("pile") or [])   # t277 : les maillons IA ne s'appliquent qu'au rendu
        img = await asyncio.to_thread(PP.apercu, p, loc, d.get("t", 0), d.get("largeur") or None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return FileResponse(img, media_type="image/png", headers={"Cache-Control": "no-store"})


async def _rendre_job(job_id: str, src: Path, pile: list, dest: Path, source_id: str, usd: float = 0.0):
    from app.services.storage import JobRecord, async_session_factory
    loop = asyncio.get_running_loop()
    etat = {"pct": 5}
    etps = PI.etapes(pile)
    travail = settings.outputs_path / "post_tmp" / job_id

    async def _suivre():
        while True:
            await asyncio.sleep(0.5)
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None and jr.status != "done":
                    jr.progress = etat["pct"]
                    await s.commit()

    suivi = asyncio.create_task(_suivre())
    try:
        if len(etps) == 1 and etps[0][0] == "local":
            await loop.run_in_executor(None, lambda: PP.rendre(src, etps[0][1], dest,
                                                               lambda f: etat.update(pct=5 + int(90 * f))))
        else:
            # t277 : la pile mixte, étape par étape — presets locaux par ffmpeg, maillons IA par leur fournisseur
            travail.mkdir(parents=True, exist_ok=True)
            cur = src
            for k, (genre, x) in enumerate(etps):
                base = 5 + int(90 * k / len(etps))
                if genre == "local":
                    nxt = travail / f"etape{k}.mp4"
                    await loop.run_in_executor(None, lambda c=cur, g=x, n=nxt, b=base: PP.rendre(
                        c, g, n, lambda f: etat.update(pct=b + int(90 * f / len(etps)))))
                else:
                    etat["pct"] = base
                    secs = (await asyncio.to_thread(PP.infos, cur))["dur"]
                    nxt = await PI.appliquer_maillon(x, cur, secs, travail)
                cur = nxt
            await asyncio.to_thread(PI.finaliser, cur, dest)
        dur = (await asyncio.to_thread(PP.infos, dest))["dur"]
        suivi.cancel()
        async with async_session_factory() as s:
            jr = await s.get(JobRecord, job_id)
            jr.status, jr.progress, jr.current_step = "done", 100, "Complete"
            jr.final_video_path = jr.video_path = str(dest)
            jr.image_filename = dest.name
            jr.duration_s = int(round(dur)) if dur else None
            jr.completed_at = datetime.utcnow()
            jr.cost_meta = json.dumps({"usd": usd, "kind": "post", "source": source_id,
                                       "ia": [m["ia"] for m in PI.actifs_ia(pile)]})
            await s.commit()
        await LI.noter([dest.name], "sonvfx", kind="video", job_id=job_id, parent=src.name, relation="post",
                       recette={"pile": pile, "source": source_id, "usd": usd})
    except Exception as e:  # noqa: BLE001 — l'échec reste lisible dans le job
        suivi.cancel()
        logger.warning(f"post {job_id} : {e}")
        async with async_session_factory() as s:
            jr = await s.get(JobRecord, job_id)
            if jr is not None:
                jr.status, jr.error, jr.current_step = "failed", str(e)[:500], "Failed"
                await s.commit()
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def _refus_cle(cle: str, nom: str, request: Request) -> HTTPException:
    from app.api.routes import _refus_cle as _rc
    return _rc(cle, nom, request)


def _txt(x, request: Request) -> str:
    from app.api.routes import _txt_g
    return _txt_g(x, request)


async def _devis(pile: list, src: Path, request: Request) -> dict:
    """Le devis des maillons IA actifs (même op pour /devis et la garde de /rendre) et les infos de la source."""
    from app.services import pricing as _pricing
    i = await asyncio.to_thread(PP.infos, src)
    op = PI.op_devis(pile, i["dur"], i["w"], i["h"])
    est = _pricing.estimate(op)
    return {"op": op, "usd": round(est["total_usd"], 6), "infos": i,
            "lignes": [{"label": _txt(ln["label"], request), "usd": ln["usd"], "provider": ln["provider"]}
                       for ln in est["breakdown"]]}


@router.get("/generateurs")
async def generateurs():
    from app.services import catalogue_ia as CI
    return {"generateurs": PI.generateurs(),
            "moteurs_texte": [{"id": m["id"], "label": m["label"], "dispo": m["dispo"], "cle": m["cle"],
                               "voie": m["voie"]} for m in CI.lister("texte")]}


@router.post("/devis")
async def devis(request: Request):
    d = await _corps(request)
    src, _ = await _source(d.get("source"))
    try:
        pile = PI.valider(d.get("pile") or [])
    except ValueError as e:
        raise HTTPException(400, _txt(e, request))
    dv = await _devis(pile, src, request)
    return {"usd": dv["usd"], "lignes": dv["lignes"], "cles": PI.cles_manquantes(pile), "ia": len(PI.actifs_ia(pile))}


@router.post("/rendre", dependencies=[Depends(_require_local_depense)])
async def rendre(request: Request):
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    d = await _corps(request)
    src, jr0 = await _source(d.get("source"))
    try:
        pile = PI.normaliser(d.get("pile") or [])
        ia = PI.actifs_ia(pile)
        if not ia and not PP.effets(PI.locaux(pile)):
            raise ValueError("la pile ne rend rien : chaque maillon est masqué ou à 0 %")
    except ValueError as e:
        raise HTTPException(400, str(e))
    usd = 0.0
    if ia:
        # t277 : maillons PAYANTS — la clé (503, avant toute garde), la validation, le devis confirmé, la garde
        manque = PI.sans_cle(pile)
        if manque:
            raise _refus_cle(manque[0], manque[1], request)
        try:
            pile = PI.valider(pile)
        except ValueError as e:
            raise HTTPException(400, _txt(e, request))
        dv = await _devis(pile, src, request)
        i = dv["infos"]
        refus = PI.refus_source(pile, src, i["dur"], (i["w"], i["h"]), src.stat().st_size)
        if refus:
            raise HTTPException(400, _txt(refus, request))
        if d.get("confirme_cout") is not True:
            raise HTTPException(409, {"message": "la pile contient des maillons payants : confirmez le devis",
                                      "usd": dv["usd"], "lignes": dv["lignes"]})
        await _PLAF.verifier(dv["op"], "son", src.name)
        usd = dv["usd"]
    job_id = str(uuid.uuid4())
    final = settings.outputs_path / "final"
    final.mkdir(parents=True, exist_ok=True)
    stem = "".join(c for c in src.stem if c.isalnum() or c in "-_")[:40] or "rendu"
    dest = final / f"post_{stem}_{job_id[:8]}.mp4"
    titre = " ".join(str(d.get("titre") or "").split())[:120] or f"{(jr0.title or src.stem)[:100]} · post"
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=5, title=titre,
                        image_filename=dest.name, provider="post", current_step="Post-traitement"))
        await s.commit()
    t = asyncio.create_task(_rendre_job(job_id, src, pile, dest, jr0.id, usd))
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return {"job_id": job_id, "status": "queued", "usd": usd}


#: Ordre de préférence du moteur de « Décrire le look » quand l'écran n'en nomme aucun.
_MOTEURS_LOOK = ("openai", "gemini", "anthropic", "ollama")


@router.post("/decrire")
async def decrire(request: Request):
    from app.services import moteurs_texte as MT
    d = await _corps(request)
    phrase = " ".join(str(d.get("phrase") or "").split())
    if not phrase:
        raise HTTPException(400, "décrivez le look voulu en une phrase")
    if len(phrase) > PI.PHRASE_MAX:
        raise HTTPException(400, f"phrase trop longue : {len(phrase)} caractères (au plus {PI.PHRASE_MAX})")
    moteur = str(d.get("moteur") or "").strip()
    if moteur:
        if not MT.connu(moteur):
            raise HTTPException(400, f"moteur de texte inconnu : {moteur[:40]!r}")
        if not MT.configure(moteur):
            raise _refus_cle(MT.CLE_ACCES.get(moteur) or moteur, MT.nom(moteur), request)
    else:
        moteur = next((m for m in _MOTEURS_LOOK if MT.configure(m)), "")
        if not moteur:
            raise _refus_cle("OPENAI_API_KEY", MT.nom("openai"), request)
    try:
        texte = await MT.tirer_garde(moteur, str(d.get("modele") or ""), phrase, PI.systeme_decrire(), 1200, True,
                                     categorie="son")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — réseau, quota : lisible, rien n'est appliqué
        raise HTTPException(502, f"moteur de texte : {str(e)[:300]}")
    try:
        pile = PI.pile_proposee(texte)
    except ValueError as e:
        raise HTTPException(502, str(e))
    return {"propose": True, "moteur": moteur, "pile": pile}


#: Taille maximale d'une LUT importée.
_LUT_MAX = 20 * 1024 * 1024


@router.post("/lut")
async def lut_import(fichier: UploadFile = File(...)):
    nom = Path(str(fichier.filename or "")).name
    base = "".join(c for c in Path(nom).stem if c.isalnum() or c in "-_ ").strip().replace(" ", "_")[:60]
    if not base or not nom.lower().endswith(".cube"):
        raise HTTPException(400, "LUT refusée : un fichier .cube est attendu")
    data = await fichier.read(_LUT_MAX + 1)
    if len(data) > _LUT_MAX:
        raise HTTPException(400, "LUT refusée : 20 Mo au plus")
    try:
        texte = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise HTTPException(400, "LUT refusée : ce n'est pas un fichier texte .cube")
    if "LUT_3D_SIZE" not in texte:
        raise HTTPException(400, "LUT refusée : LUT_3D_SIZE absent (seules les LUT 3D sont lues)")
    dest = settings.luts_path / f"{base}.cube"
    await asyncio.to_thread(dest.write_bytes, data)
    luts = sorted(f.name for f in settings.luts_path.glob("*.cube") if f.is_file())
    return {"nom": dest.name, "luts": luts}


@router.get("/presets")
async def presets_liste():
    return {"presets": PP.presets()}


@router.post("/presets")
async def presets_ajout(request: Request):
    d = await _corps(request)
    try:
        return PP.enregistrer_preset(d.get("nom"), d.get("pile") or [])
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/presets/{pid}")
async def presets_suppr(pid: str):
    if not PP.supprimer_preset(pid):
        raise HTTPException(404, "preset de pile introuvable")
    return {"ok": True}
