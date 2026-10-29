# -*- coding: utf-8 -*-
"""t343 (29/10/2026, lot Scenario B8) — VIDÉO → MOUVEMENT par Uthana (voie PAYANTE).

Relevé du 29/10/2026 (sans dépense, pages publiques) :
  - fal n'a PAS de modèle « vidéo → mouvement » fiable : fal-ai/dwpose/video rend des poses 2D dessinées,
    fal-ai/muse-pose est retiré, fal-ai/sam-3/3d-body lit UNE IMAGE (paramètres MHR, pas un clip d'os) ;
  - Uthana (uthana.com/docs/api/capabilities/video-to-motion) : POST https://uthana.com/graphql en Basic (la clé en
    nom d'utilisateur, mot de passe vide), mutation multipart `create_video_to_motion(file, motion_name)` →
    `job { id status }` ; suivi `job(job_id) { id status result }` jusqu'à FINISHED / FAILED ; l'id du mouvement est
    `result.result.id` ; le clip SANS maillage se télécharge en GLB à
    https://uthana.com/motion/animation/motion_viewer/{personnage}/{mouvement}/glb/motion.glb?fps=30
    (personnage par défaut cXi2eAP19XwQ) ; vidéo .mp4/.mov/.avi, 2 à 60 s, 24 à 120 i/s, 300 à 4096 px, une
    personne entière, plan fixe ; modèle par défaut video-to-motion-2.0 ;
  - prix (uthana.com/pricing) : 0,05 $ par seconde de vidéo envoyée, crédits prépayés, API comprise.
Une estimation de pose 2D LOCALE n'est pas possible sans paquet (mediapipe, torch : absents du python embarqué).
Les appels réseau passent par trois COUTURES (`_poster`, `_requete`, `_telecharger`) que les bancs remplacent.
"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
from pathlib import Path

from app.config import settings

URL_GRAPHQL = "https://uthana.com/graphql"
URL_CLIP = "https://uthana.com/motion/animation/motion_viewer/{perso}/{mvt}/glb/motion.glb?fps=30"
PERSONNAGE = "cXi2eAP19XwQ"
MODELE = "video-to-motion-2.0"
PRIX_SECONDE = 0.05
DUREE_MIN, DUREE_MAX = 2.0, 60.0
FPS_MIN, FPS_MAX = 24.0, 120.0
COTE_MIN, COTE_MAX = 300, 4096
EXT_ACCEPTEES = (".mp4", ".mov", ".avi")
ATTENTE_MAX_S = 15 * 60
PAS_S = 5.0
MUTATION = ("mutation ($file: Upload!, $motion_name: String!) { create_video_to_motion(file: $file, "
            "motion_name: $motion_name) { job { id status } } }")
REQUETE_JOB = "query ($job_id: String!) { job(job_id: $job_id) { id status result } }"


def cle() -> str:
    return str(getattr(settings, "UTHANA_API_KEY", "") or "").strip()


def devis(secondes: float | None) -> dict:
    """Le prix AVANT : 0,05 $ par seconde envoyée (arrondie à la seconde supérieure)."""
    from app.services import pricing
    s = int(math.ceil(float(secondes or 0)))
    est = pricing.estimate({"kind": "video_mouvement", "secondes": s})
    return {"fournisseur": "uthana", "modele": MODELE, "secondes": s,
            "usd_seconde": round(est["total_usd"] / s, 4) if s else PRIX_SECONDE, "usd": round(est["total_usd"], 2)}


def verifier(infos: dict, debut: float = 0.0, fin: float | None = None) -> dict:
    """Les bornes d'Uthana, jugées sur la vidéo ROGNÉE, avant toute dépense. Rend {debut, fin, secondes}."""
    total = infos.get("secondes")
    if not total:
        raise ValueError("vidéo illisible : durée inconnue (ffprobe)")
    fin = float(total) if fin is None else float(fin)
    debut = float(debut or 0.0)
    if not 0 <= debut < fin <= float(total) + 0.05:
        raise ValueError(f"rognage hors de la vidéo (0 à {total} s, début avant la fin)")
    s = round(fin - debut, 3)
    if not DUREE_MIN <= s <= DUREE_MAX:
        raise ValueError(f"Uthana lit de {int(DUREE_MIN)} à {int(DUREE_MAX)} s de vidéo : rogne la vidéo "
                         f"({s} s retenues)")
    fps = infos.get("fps")
    if fps and not FPS_MIN - 0.5 <= float(fps) <= FPS_MAX:
        raise ValueError(f"cadence de {fps} i/s : Uthana attend 24 à 120 i/s")
    for cote in (infos.get("largeur"), infos.get("hauteur")):
        if cote and not COTE_MIN <= int(cote) <= COTE_MAX:
            raise ValueError(f"résolution hors bornes : {COTE_MIN} à {COTE_MAX} px par côté")
    return {"debut": debut, "fin": fin, "secondes": s}


def preparer(src: Path, dest: Path, debut: float, fin: float) -> Path:
    """Le passage envoyé : rogné, en MP4 H.264 sans son (ffmpeg, local, gratuit)."""
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{debut:.3f}", "-i", str(src), "-t", f"{fin - debut:.3f}",
                        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", str(dest)],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not dest.is_file():
        raise RuntimeError(f"ffmpeg n'a pas préparé la vidéo ({(r.stderr or '').strip()[:200]})")
    return dest


# ─────────── coutures réseau (remplacées au banc) ───────────

async def _poster(video: Path, nom: str) -> dict:                   # pragma: no cover — réseau
    import httpx
    ops = json.dumps({"query": MUTATION, "variables": {"file": None, "motion_name": nom}})
    async with httpx.AsyncClient(timeout=300) as c:
        with video.open("rb") as f:
            r = await c.post(URL_GRAPHQL, auth=(cle(), ""), data={"operations": ops, "map": '{"0": ["variables.file"]}'},
                             files={"0": (video.name, f, "video/mp4")})
    r.raise_for_status()
    return r.json()


async def _requete(job_id: str) -> dict:                            # pragma: no cover — réseau
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(URL_GRAPHQL, auth=(cle(), ""), json={"query": REQUETE_JOB, "variables": {"job_id": job_id}})
    r.raise_for_status()
    return r.json()


async def _telecharger(url: str) -> bytes:                          # pragma: no cover — réseau
    import httpx
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as c:
        r = await c.get(url, auth=(cle(), ""))
    r.raise_for_status()
    return r.content


def _erreurs(rep: dict) -> str | None:
    e = rep.get("errors") if isinstance(rep, dict) else None
    if e:
        return "; ".join(str((x or {}).get("message") or x)[:160] for x in e[:3])
    return None


async def video_vers_mouvement(video: Path, nom: str, on_etat=None, pas_s: float = PAS_S) -> dict:
    """LE PUITS : envoie le passage préparé, suit le travail, rapatrie le clip GLB. Rend {glb, job, mouvement}."""
    if not cle():
        raise PermissionError("clé Uthana absente")
    rep = await _poster(Path(video), nom)
    err = _erreurs(rep)
    if err:
        raise RuntimeError(f"Uthana a refusé la vidéo : {err}")
    job = (((rep.get("data") or {}).get("create_video_to_motion") or {}).get("job") or {})
    jid = job.get("id")
    if not jid:
        raise RuntimeError("Uthana n'a rendu aucun identifiant de travail")
    if on_etat:
        await on_etat({"etat": "envoye", "uthana_job": jid})
    attente = 0.0
    while True:
        r = await _requete(jid)
        err = _erreurs(r)
        if err:
            raise RuntimeError(f"suivi Uthana : {err}")
        j = (r.get("data") or {}).get("job") or {}
        st = str(j.get("status") or "").upper()
        if st == "FINISHED":
            res = j.get("result")
            if isinstance(res, str):
                try:
                    res = json.loads(res)
                except ValueError:
                    res = {}
            mvt = (((res or {}).get("result") or {}).get("id")) if isinstance(res, dict) else None
            if not mvt:
                raise RuntimeError("Uthana a fini sans identifiant de mouvement")
            glb = await _telecharger(URL_CLIP.format(perso=PERSONNAGE, mvt=mvt))
            if glb[:4] != b"glTF":
                raise RuntimeError("Uthana : le clip rapatrié n'est pas un GLB")
            return {"glb": glb, "job": jid, "mouvement": mvt}
        if st == "FAILED":
            raise RuntimeError("Uthana : le travail a échoué (une personne entière, plan fixe, fond simple)")
        if on_etat:
            await on_etat({"etat": "en_cours", "uthana_job": jid, "statut": st})
        if attente >= ATTENTE_MAX_S:
            raise TimeoutError("Uthana : pas de résultat après 15 minutes")
        await asyncio.sleep(pas_s)
        attente += pas_s or 1.0
