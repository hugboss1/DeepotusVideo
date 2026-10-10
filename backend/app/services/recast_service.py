# -*- coding: utf-8 -*-
"""Avatar live G1 (t162, 10/10/2026) — le Recast différé, l'équivalent du Genjutsu de Higgsfield : une vidéo de 3 à 30 s
et un Personnage (G0) donnent une vidéo où le personnage, le décor ou un élément a changé, le jeu d'acteur restant.
Spec : docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md (§5, §9).

Modèles et prix RELEVÉS le 10/10/2026 (openapi de queue fal, 200 pour chaque id ; llms.txt pour les prix) :
  remplacer      fal-ai/wan/v2.2-14b/animate/replace   video_url + image_url ; 480p/580p/720p = 0,04/0,06/0,08 $/s
  animer         fal-ai/wan/v2.2-14b/animate/move      mêmes entrées ; prix non affiché à part -> celui de replace (dit)
  mouvement      fal-ai/kling-video/v3/standard/motion-control   image_url + video_url + character_orientation ;
                 keep_original_sound (vrai) ; elements = visage frontal + 1-3 vues -> le Personnage ; 0,126 $/s
  mouvement_pro  fal-ai/kling-video/v3/pro/motion-control        idem ; 0,168 $/s
  objet          decart/lucy-edit/pro                  prompt + video_url ; 720p 0,15 $/s, 480p 0,10 $/s (sans Personnage)

t168c (10/10/2026) — brouillon puis rendu final : Wan (replace, move) et Lucy prennent `seed` (openapi relevé le
10/10) ; Kling motion control n'en a pas. Ces modèles reçoivent TOUJOURS une graine (tirée si absente), gardée avec
le job dans sa RECETTE (outputs/recast/recettes/<job>.json) ; « Brouillon » tire en 480p, « Finaliser » relance la
même recette (source, Personnage, consigne, voix, graine) à la résolution finale. fal ne promet pas l'identité du
rendu à graine égale (la résolution change le bruit initial) : l'écran le dit, sans le cacher.

Le rendu est un JOB (JobRecord, provider « recast ») : il paraît dans les rendus, le Montage le lit par job_id, le
téléphone le tire par /sync/media/{job_id}. Les appels réseau passent par trois seams (`_upload`, `_fal_subscribe`,
`_download`) que les bancs remplacent. PAYANT : la route passe la garde des plafonds AVANT `lancer_recast`."""
from __future__ import annotations

import asyncio
import json
import random
import re
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

DUREE_MIN_S = 3.0
DUREE_MAX_S = 30.0

MODELES: dict[str, dict] = {
    "remplacer": {"fal": "fal-ai/wan/v2.2-14b/animate/replace", "famille": "wan",
                  "label": "Remplacer le personnage (garde le décor et le jeu)",
                  "prix": {"480p": 0.04, "580p": 0.06, "720p": 0.08}, "defaut": "720p", "personnage": True,
                  "consigne": False, "graine": True},
    "animer": {"fal": "fal-ai/wan/v2.2-14b/animate/move", "famille": "wan",
               "label": "Animer le personnage dans SON décor (mouvement de la vidéo)",
               "prix": {"480p": 0.04, "580p": 0.06, "720p": 0.08}, "defaut": "720p", "personnage": True,
               "consigne": False, "graine": True,
               "note_prix": "prix de « remplacer » : fal n'affiche pas celui-ci à part (10/10)"},
    "mouvement": {"fal": "fal-ai/kling-video/v3/standard/motion-control", "famille": "kling",
                  "label": "Transfert de mouvement (personnage et décor de l'image, son d'origine gardé)",
                  "prix": {"source": 0.126}, "defaut": "source", "personnage": True, "consigne": True},
    "mouvement_pro": {"fal": "fal-ai/kling-video/v3/pro/motion-control", "famille": "kling",
                      "label": "Transfert de mouvement, qualité pro",
                      "prix": {"source": 0.168}, "defaut": "source", "personnage": True, "consigne": True},
    "objet": {"fal": "decart/lucy-edit/pro", "famille": "lucy",
              "label": "Remplacer un élément par une consigne (tenue, objet, décor)",
              "prix": {"480p": 0.10, "720p": 0.15}, "defaut": "720p", "personnage": False, "consigne": True,
              "graine": True},
}

# Préréglages de décor/élément (consigne envoyée en anglais, libellé en français) — partagés avec G3 et G4.
PREREGLAGES: list[dict] = [
    {"id": "studio_neon", "label": "Studio néon", "consigne": "in a dark studio lit by pink and cyan neon tubes"},
    {"id": "plateau_tv", "label": "Plateau télé", "consigne": "on a bright modern TV news set with screens behind"},
    {"id": "bureau", "label": "Bureau moderne", "consigne": "in a modern glass office with soft daylight"},
    {"id": "tokyo_nuit", "label": "Rue de Tokyo la nuit", "consigne": "on a rainy Tokyo street at night with neon signs"},
    {"id": "plage", "label": "Plage au coucher du soleil", "consigne": "on a beach at golden-hour sunset"},
    {"id": "foret", "label": "Forêt brumeuse", "consigne": "in a misty pine forest at dawn"},
    {"id": "station", "label": "Station orbitale", "consigne": "inside a space station with Earth visible through the window"},
    {"id": "bibliotheque", "label": "Bibliothèque ancienne", "consigne": "in an old wooden library full of books"},
    {"id": "desert", "label": "Désert", "consigne": "in a vast sand desert under a clear sky"},
    {"id": "salle_classe", "label": "Salle de classe", "consigne": "in a sunny classroom with a chalkboard"},
    {"id": "fond_vert", "label": "Fond vert uni", "consigne": "in front of a flat uniform chroma-key green background"},
    {"id": "cave_crypto", "label": "Antre crypto", "consigne": "in a dim crypto trading den full of glowing charts"},
]
_PRE = {p["id"]: p for p in PREREGLAGES}
_SAFE_DEPOT = re.compile(r"^[a-f0-9]{24}\.(mp4|mov|webm)$")
_SAFE_JOB = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
BROUILLON_RES = "480p"
GRAINE_MAX = 2 ** 31 - 1
_TACHES: set = set()


def sources_dir() -> Path:
    p = Path(settings.outputs_path) / "recast" / "sources"
    p.mkdir(parents=True, exist_ok=True)
    return p


def chemin_depot(nom: str) -> Path | None:
    n = str(nom or "")
    if not _SAFE_DEPOT.match(n):
        return None
    p = sources_dir() / n
    return p if p.is_file() else None


def lire_graine(v) -> int | None:
    """Une graine fal valide (entier 0..2^31-1), sinon None ; un booléen n'en est pas une."""
    if isinstance(v, bool):
        return None
    try:
        g = int(v)
    except (TypeError, ValueError):
        return None
    return g if 0 <= g <= GRAINE_MAX else None


def recettes_dir() -> Path:
    p = Path(settings.outputs_path) / "recast" / "recettes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ecrire_recette(job_id: str, recette: dict) -> None:
    (recettes_dir() / f"{job_id}.json").write_text(json.dumps(recette, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_recette(job_id: str) -> dict | None:
    j = str(job_id or "")
    if not _SAFE_JOB.match(j):
        return None
    p = recettes_dir() / f"{j}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, ValueError):
        return None


def brouillons() -> dict:
    """{job_id: recette} des brouillons dont la recette est lisible (pour proposer « Finaliser ») ; `finales` liste les
    versions finales déjà tirées de chacun (l'écran le dit : refinaliser se paie une seconde fois)."""
    toutes = {p.stem: lire_recette(p.stem) for p in sorted(recettes_dir().glob("*.json"))}
    out = {j: dict(r, finales=[]) for j, r in toutes.items() if r and r.get("brouillon")}
    for j, r in toutes.items():
        if r and r.get("brouillon_de") in out:
            out[r["brouillon_de"]]["finales"].append(j)
    return out


def resolution(modele: str, demandee) -> str:
    m = MODELES[modele]
    r = str(demandee or "").strip().lower()
    return r if r in m["prix"] else m["defaut"]


def prix_usd_s(modele: str, res: str) -> float:
    m = MODELES.get(modele)
    if m is None:
        return 0.0
    return float(m["prix"].get(res, m["prix"][m["defaut"]]))


def consigne_finale(modele: str, consigne, prereglage) -> str:
    c = str(consigne or "").strip()[:500]
    p = _PRE.get(str(prereglage or ""))
    if p and modele == "objet":
        c = (c + " " if c else "") + "Change the background: the scene now takes place " + p["consigne"] + "."
    elif p:
        c = (c + ", " if c else "") + "the character " + p["consigne"]
    return c.strip()


def preparer(corps: dict, src: Path, duree_s: float, personnage: dict | None) -> dict:
    """Tout ce qui ne coûte rien, contrôlé AVANT la garde : modèle, Personnage, consigne, durée. ValueError nommée."""
    modele = str(corps.get("modele") or "")
    if modele not in MODELES:
        raise ValueError(f"Modèle inconnu : {modele!r} (connus : {', '.join(MODELES)}).")
    if not (settings.FAL_KEY or "").strip():
        raise ValueError("fal.ai : aucune clé configurée (Réglages → clés API) — rien n'a été lancé.")
    m = MODELES[modele]
    if m["personnage"] and personnage is None:
        raise ValueError(f"« {m['label']} » demande un Personnage (images de référence avec consentement).")
    consigne = consigne_finale(modele, corps.get("consigne"), corps.get("prereglage"))
    if modele == "objet" and not consigne:
        raise ValueError("« Remplacer un élément » demande une consigne ou un préréglage (ce qui doit changer).")
    if not DUREE_MIN_S <= duree_s <= DUREE_MAX_S:
        raise ValueError(f"La vidéo source fait {duree_s:.1f} s : le Recast prend de {DUREE_MIN_S:.0f} à "
                         f"{DUREE_MAX_S:.0f} s (comme Genjutsu). Coupez-la au Montage.")
    brouillon = bool(corps.get("brouillon"))
    if brouillon and not m.get("graine"):
        raise ValueError(f"« {m['label']} » n'a pas de brouillon : fal ne prend pas de graine pour ce modèle, un "
                         "second tir ne repartirait pas du même rendu.")
    res = BROUILLON_RES if brouillon else resolution(modele, corps.get("resolution"))
    graine = None
    if m.get("graine"):
        graine = lire_graine(corps.get("graine"))
        if graine is None:
            graine = random.randint(1, GRAINE_MAX)
    orient = "image" if str(corps.get("orientation") or "") == "image" else "video"
    op = {"kind": "recast", "modele": modele, "seconds": float(duree_s), "resolution": res}
    voice_id = None
    if corps.get("voix"):
        # G2 (t163) : la voix du Personnage remplace celle de la prise, APRÈS fal (le devis porte les deux)
        from app.services import avatar_voix as _av
        voice_id = ((personnage or {}).get("voix") or {}).get("voice_id")
        if not voice_id:
            raise ValueError("« Avec la voix du Personnage » : ce Personnage n'a pas de voix (clonez-la d'abord).")
        if not _av.cle():
            raise ValueError("Clé ElevenLabs absente (Réglages → clés API) — rien n'a été lancé.")
        op = {"kind": "campaign", "ops": [op, {"kind": "voix_sts", "duration_s": float(duree_s)}]}
    return {"modele": modele, "resolution": res, "consigne": consigne, "orientation": orient,
            "duree_s": float(duree_s), "src": src, "personnage": personnage, "voice_id": voice_id, "op": op,
            "graine": graine, "brouillon": brouillon}


async def _upload(path: Path) -> str:                               # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments, with_logs=False)


async def _download(url: str, dest: Path) -> None:                  # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=900) as c:
        r = await c.get(url)
        r.raise_for_status()
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(r.content)
        tmp.replace(dest)


def a_du_son(path) -> bool:
    """Vrai si ffprobe trouve au moins une piste audio."""
    from app.services.fal_video_tools import _bin
    out = subprocess.run([_bin("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(path)], capture_output=True, timeout=60)
    return bool(out.stdout.strip())


def reposer_son(src: Path, dest: Path) -> bool:
    """Genjutsu garde l'audio et la synchro labiale de la source. Les modèles Wan et Lucy ne disent pas rendre de son
    (schémas de sortie du 10/10) : si la vidéo rendue n'en a pas et que la source en a, la piste de la source est
    recollée (vidéo copiée, -shortest : Wan normalise à 16 i/s et peut raccourcir d'une fraction de seconde).
    Local, gratuit. Rend vrai si la piste a été posée."""
    from app.services.fal_video_tools import _bin
    if a_du_son(dest) or not a_du_son(src):
        return False
    tmp = dest.with_name(dest.stem + ".son" + dest.suffix)
    r = subprocess.run([_bin("ffmpeg"), "-y", "-v", "error", "-i", str(dest), "-i", str(src), "-map", "0:v:0",
                        "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(tmp)],
                       capture_output=True, timeout=300)
    if r.returncode != 0 or not tmp.is_file():
        tmp.unlink(missing_ok=True)
        logger.warning(f"recast : son de la source non recollé ({r.stderr.decode('utf-8', 'replace')[-200:]})")
        return False
    tmp.replace(dest)
    return True


def arguments(prep: dict, video_url: str, images: list[str]) -> dict:
    """Le corps fal de chaque famille, d'après l'openapi relevé le 10/10."""
    m = MODELES[prep["modele"]]
    if m["famille"] == "wan":
        a = {"video_url": video_url, "image_url": images[0], "resolution": prep["resolution"],
             "video_quality": "high"}
        if prep.get("graine") is not None:
            a["seed"] = prep["graine"]
        return a
    if m["famille"] == "kling":
        a = {"video_url": video_url, "image_url": images[0], "character_orientation": prep["orientation"],
             "keep_original_sound": True}
        if prep["consigne"]:
            a["prompt"] = prep["consigne"]
        a["elements"] = [{"frontal_image_url": images[0], **({"reference_image_urls": images[1:4]} if len(images) > 1 else {})}]
        return a
    a = {"video_url": video_url, "prompt": prep["consigne"], "resolution": prep["resolution"]}
    if prep.get("graine") is not None:
        a["seed"] = prep["graine"]
    return a


async def _executer(job_id: str, prep: dict, lignes: list) -> None:
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    from app.services import plafonds as _plaf, avatar_live as AL
    from app.services.fal_service import FalSeedanceClient

    async def maj(**kw):
        async with async_session_factory() as s:
            j = await s.get(JobRecord, job_id)
            for k, v in kw.items():
                setattr(j, k, v)
            await s.commit()

    try:
        await _plaf.rattacher(lignes, f"recast:{job_id}")
        await maj(status=JobStatus.UPLOADING.value, current_step="Envoi de la vidéo et des références", progress=10)
        vurl = await _upload(prep["src"])
        images = []
        if prep["personnage"]:
            for n in range(min(4, int(prep["personnage"]["images"]))):
                p = AL.chemin_image(prep["personnage"]["id"], n)
                if p:
                    images.append(await _upload(Path(p)))
        m = MODELES[prep["modele"]]
        await maj(status=JobStatus.GENERATING_VIDEO.value, current_step=m["label"], progress=35)
        res = await _fal_subscribe(m["fal"], arguments(prep, vurl, images))
        url = FalSeedanceClient.extract_video_url(res)
        if not url:
            cles = ", ".join(map(str, res or {})) if isinstance(res, dict) else type(res).__name__
            raise RuntimeError(f"fal.ai : aucune vidéo dans la réponse (clés : {cles})")
        await maj(status=JobStatus.DOWNLOADING.value, current_step="Téléchargement", progress=85)
        dest = Path(settings.outputs_path) / "final" / f"{job_id}.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await _download(url, dest)
        if await asyncio.to_thread(reposer_son, Path(prep["src"]), dest):
            logger.info(f"recast {job_id} : son de la source recollé")
        if prep.get("voice_id"):
            from app.services import avatar_voix as _av
            await maj(status=JobStatus.GENERATING_VOICEOVER.value, current_step="Voix du Personnage", progress=92)
            tmpv = dest.with_name(dest.stem + ".voix.mp4")
            await _av.convertir_fichier(dest, prep["voice_id"], False, tmpv)
            tmpv.replace(dest)
        await maj(video_path=str(dest), final_video_path=str(dest), status=JobStatus.DONE.value,
                  current_step="Complete", progress=100, completed_at=datetime.utcnow())
        logger.info(f"recast {job_id} ({prep['modele']}) : {dest.name}")
    except Exception as e:  # noqa: BLE001 — le job échoue NOMMÉMENT
        logger.warning(f"recast {job_id} en échec : {e}")
        await maj(status=JobStatus.FAILED.value, current_step="Failed", error=str(e)[:500],
                  completed_at=datetime.utcnow())


async def lancer_recast(prep: dict, lignes: list, parent_job_id: str | None, recette: dict | None = None) -> str:
    """Crée le job et lance le rendu en tâche de fond ; rend l'id du job. PAYANT (fal) : la garde est passée.
    `recette` (t168c) : ce qu'il faut pour refaire ce rendu (source, Personnage, réglages, graine), gardé à côté."""
    from app.models.schemas import JobStatus, Provider
    from app.services.storage import JobRecord, async_session_factory
    from app.services import fal_video_tools as FV
    job_id = str(uuid4())
    try:
        info = await asyncio.to_thread(FV.probe, prep["src"])
    except Exception:  # noqa: BLE001
        info = {}
    titre = ("Recast (brouillon 480p) — " if prep.get("brouillon") else "Recast — ") + \
        (prep["personnage"]["nom"] if prep["personnage"] else MODELES[prep["modele"]]["label"])
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.QUEUED.value, image_filename="",
                        provider=Provider.RECAST.value, parent_job_id=parent_job_id, video_model=prep["modele"],
                        aspect_ratio=info.get("ratio"), duration_s=int(round(prep["duree_s"])),
                        final_prompt=prep["consigne"] or None, title=titre[:200], created_at=datetime.utcnow()))
        await s.commit()
    if recette is not None:
        ecrire_recette(job_id, dict(recette, modele=prep["modele"], resolution=prep["resolution"], graine=prep.get("graine"),
                                    brouillon=bool(prep.get("brouillon")), duree_s=prep["duree_s"]))
    t = asyncio.get_running_loop().create_task(_executer(job_id, prep, lignes))
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return job_id
