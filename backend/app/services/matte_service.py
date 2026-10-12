# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T9, D2a) — le matte vidéo : BiRefNet v2 (fal) détoure le
sujet d'un rendu et le rend en ProRes 4444 (avec alpha), rangé sous
outputs/mattes/ ; le Montage compose ensuite les effets ENTRE le fond et lui.

Schéma relu le 06/10/2026 sur l'openapi « queue » de fal
(`fal-ai/birefnet/v2/video`) : `video_url` seul requis ; `video_output_type`
∈ {X264 (.mp4), VP9 (.webm), PRORES4444 (.mov), GIF (.gif)} ; `model` ∈ six
libellés ; `operating_resolution` ∈ {1024x1024, 2048x2048, 2304x2304} ;
`refine_foreground` (défaut vrai) ; sortie `video` (+ `mask_video`).

LE PRIX N'EST PAS CONNU, ET ON LE DIT. La page du modèle n'affiche que
« $0 per compute second » (relu le 06/10, comme le 03/09) — un chiffre qui ne
peut pas être vrai. Le devis vaut donc 0 $ AVEC une ligne qui le nomme « à
mesurer », la note suit le travail jusqu'à l'écran, et le vrai montant se lit
sur le tableau de bord fal après le premier tir (à écrire alors dans
pricing.DEFAULTS["birefnet_video_usd_per_s"], daté).

Travaux suivis EN MÉMOIRE (un détourage dure de quelques secondes à quelques
dizaines ; le panneau interroge aussitôt) : un redémarrage les oublie, les
fichiers restent. Les appels réseau passent par trois seams de module
(`_upload`, `_fal_subscribe`, `_download`) que les bancs remplacent.

t186 (G4, 12/10/2026) — `detourer` accepte aussi tout id `detourage_video` du registre UNIQUE
(app.services.detourage.REGISTRE : Bria VRMBG 3.0, VEED rapide, Pixelcut vidéo, SAM 3.1 avec un sujet nommé,
BiRefNet v2 vidéo) ; les trois anciennes clés (general / matting / portrait) restent valides = BiRefNet v2 vidéo
avec le `model` correspondant, et « general » reste le défaut. Certaines sorties sont des .webm VP9 AVEC alpha :
`matte_path` accepte .mov et .webm (toujours confiné), et `decodeur_entree` impose le décodeur libvpx-vp9 à qui
lit un .webm (le décodeur vp9 natif de ffmpeg JETTE l'alpha). Les seams servent aussi le détourage d'image
(detourage.detourer_image) : un seul jeu de coutures pour tout le détourage."""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

ENDPOINT = "fal-ai/birefnet/v2/video"
MATTE_MODELS = {
    "general": {"label": "Général (léger)", "fal": "General Use (Light)"},
    "matting": {"label": "Matting — cheveux, transparences", "fal": "Matting"},
    "portrait": {"label": "Portrait", "fal": "Portrait"},
}
ARGS_FIXED = {"video_output_type": "PRORES4444 (.mov)", "refine_foreground": True,
              "operating_resolution": "1024x1024", "video_quality": "high"}
from app.i18n import Message, Nom   # noqa: E402  t192 : la note se dit dans la langue de la requête (routes du matte)
USD_NOTE = Message("matte.note_birefnet")   # « prix à mesurer : fal n'affiche que « $0 per compute second » … »
_JOBS: dict[str, dict] = {}
_JOBS_MAX = 40
_SAFE = re.compile(r"^[A-Za-z0-9_-]+\.(?:mov|webm)$")


def mattes_dir() -> Path:
    p = Path(settings.outputs_path) / "mattes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def decodeur_entree(path) -> list[str]:
    """Les options à poser AVANT `-i <matte>` : un .webm (VP9 + alpha, t186) se lit par libvpx-vp9 — le
    décodeur vp9 natif de ffmpeg ignore la couche alpha et rendrait un sujet sur fond noir. Rien pour un .mov
    (commande d'avant, octet pour octet)."""
    return ["-c:v", "libvpx-vp9"] if Path(str(path)).suffix.lower() == ".webm" else []


def media_type(name: str) -> str:
    """Le type servi par GET /matte/file/{name}."""
    return "video/webm" if str(name).lower().endswith(".webm") else "video/quicktime"


def matte_path(name: str) -> Path:
    """Le chemin d'un matte, CONFINÉ : un nom simple en .mov ou .webm, dans le dossier
    des mattes et nulle part ailleurs — ValueError sinon (les routes en font
    un 404, le Montage un « pas de matte »)."""
    n = str(name or "")
    if not _SAFE.match(n):
        raise ValueError(f"nom de matte refusé : {n[:40]!r}")
    p = (mattes_dir() / n).resolve()
    if p.parent != mattes_dir().resolve():
        raise ValueError("matte hors dossier")
    return p


async def _upload(path: Path) -> str:                               # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments,
                                            with_logs=False)


async def _download(url: str, dest: Path, max_octets: int | None = None) -> None:   # seam
    """Rapatrie `url` vers `dest` (via un .part, puis os.replace). t189 (relecture) : `max_octets` facultatif — le
    corps est alors lu en FLUX et le téléchargement s'arrête (RuntimeError nommée, .part effacé) dès qu'il dépasse
    la borne ; sans lui, le comportement d'avant, octet pour octet (les autres appelants ne le passent pas)."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=600) as c:
        if max_octets is None:
            r = await c.get(url)
            r.raise_for_status()
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(r.content)
            os.replace(tmp, dest)
            return
        tmp = dest.with_name(dest.name + ".part")
        try:
            async with c.stream("GET", url) as r:
                r.raise_for_status()
                n = 0
                with open(tmp, "wb") as f:
                    async for bloc in r.aiter_bytes():
                        n += len(bloc)
                        if n > int(max_octets):
                            raise RuntimeError(f"téléchargement refusé : plus de {int(max_octets) // (1024 * 1024)} Mo "
                                               f"({int(max_octets)} octets au plus)")
                        f.write(bloc)
            os.replace(tmp, dest)
        finally:
            tmp.unlink(missing_ok=True)


def status(mid: str) -> dict:
    return dict(_JOBS.get(str(mid)) or {"status": "unknown"})


def est_connu(model_key: str) -> bool:
    """Une ancienne clé (general / matting / portrait) ou un id `detourage_video` du registre."""
    from app.services import detourage as DT
    return model_key in MATTE_MODELS or model_key in DT.ids(DT.VIDEO)


def requete(model_key: str, url: str, sujet=None) -> tuple[str, dict]:
    """(endpoint, arguments) d'un détourage vidéo : les anciennes clés gardent EXACTEMENT les arguments
    d'avant (ARGS_FIXED + le `model` BiRefNet choisi) ; un id du registre passe par detourage.build_request."""
    if model_key in MATTE_MODELS:
        return ENDPOINT, dict(ARGS_FIXED, video_url=url, model=MATTE_MODELS[model_key]["fal"])
    from app.services import detourage as DT
    return DT.build_request(model_key, url, sujet)


def extension(model_key: str) -> str:
    """.mov pour BiRefNet et Bria v3 (ProRes avec alpha), .webm pour VEED, Pixelcut vidéo, SAM 3.1."""
    from app.services import detourage as DT
    return ".mov" if model_key in MATTE_MODELS else DT.REGISTRE[model_key]["ext"]


def op_devis(model_key: str, duree_s: float, fps: float | None = None) -> dict:
    """t186 (G4) — L'op de devis (pricing.estimate) d'un détourage VIDÉO, source unique de /matte et du décor Avatar :
    kind « matte » pour BiRefNet (anciennes clés et birefnet-v2-video — même tarif, la ligne que les bancs du matte
    figent), kind « detourage » (secondes, fps 30 par défaut) pour les autres modèles du registre. Le rack VFX en
    garde une copie JS (vfxMatteDevis, frontend/patches/vfxrack.js) qui renvoie ici."""
    if model_key in MATTE_MODELS or model_key == "birefnet-v2-video":
        return {"kind": "matte", "duration_s": float(duree_s)}
    from app.services import detourage as DT
    return DT.op_cout(model_key, secondes=float(duree_s), fps=fps)


def note_prix(model_key: str) -> str:
    """La note de prix qui suit le travail jusqu'à l'écran : celle de BiRefNet (prix à mesurer) pour les
    anciennes clés et birefnet-v2-video ; « prix à mesurer » nommé pour un autre modèle à 0 $ ; vide sinon."""
    from app.services import detourage as DT, pricing as P
    if model_key in MATTE_MODELS or model_key == "birefnet-v2-video":
        return USD_NOTE
    e = DT.REGISTRE.get(model_key) or {}
    taux = P.taux_detourage(model_key)
    return "" if taux else Message("matte.note_a_mesurer", modele=Nom(model_key, e.get('label', model_key)),
                                   champ=e.get("prix"))


async def _run(mid: str, src: Path, model_key: str, sujet: str | None = None) -> None:
    from app.services import detourage as DT
    j = _JOBS[mid]
    try:
        j.update(status="upload", pct=10)
        url = await _upload(src)
        j.update(status="fal", pct=30)
        endpoint, args = requete(model_key, url, sujet)
        res = await _fal_subscribe(endpoint, args)
        vurl = DT.url_video(res)
        if not vurl:
            keys = ", ".join(map(str, res or {})) if isinstance(res, dict) else type(res).__name__
            raise RuntimeError(f"fal.ai : aucune vidéo dans la réponse (clés : {keys})")
        j.update(status="download", pct=80)
        dest = mattes_dir() / f"{j['label']}_{mid[:8]}{extension(model_key)}"
        await _download(vurl, dest)
        j.update(status="done", pct=100, file=dest.name,
                 url=f"/api/matte/file/{dest.name}")
        logger.info(f"matte {mid} : {dest.name} ({dest.stat().st_size // 1024} Ko) — {j['usd_note'] or model_key}")
    except Exception as e:  # noqa: BLE001 — le travail échoue NOMMÉMENT, rien ne fuit
        logger.warning(f"matte {mid} en échec : {e}")
        j.update(status="failed", error=str(e)[:300])


def detourer(src: Path, model_key: str = "general", label: str = "clip", sujet: str | None = None) -> str:
    """Lance un détourage (tâche de fond sur la boucle COURANTE) et rend son
    id. ValueError nommée : clé absente, modèle inconnu, sujet manquant (SAM 3.1),
    source introuvable. `model_key` : ancienne clé ou id detourage_video du registre.
    PAYANT (fal) : la route passe la garde des plafonds AVANT d'appeler ceci."""
    from app.services import detourage as DT
    if not (settings.FAL_KEY or "").strip():
        raise ValueError("fal.ai : aucune clé configurée (Réglages → clés API).")
    if not est_connu(model_key):
        raise ValueError(f"modèle de détourage inconnu : {model_key!r} "
                         f"(connus : {', '.join(list(MATTE_MODELS) + DT.ids(DT.VIDEO))})")
    sujet = None if model_key in MATTE_MODELS else DT.sujet_de(model_key, sujet)
    if not Path(src).is_file():
        raise ValueError("source vidéo introuvable")
    while len(_JOBS) >= _JOBS_MAX:
        _JOBS.pop(next(iter(_JOBS)))
    mid = uuid4().hex
    _JOBS[mid] = {"status": "queued", "pct": 0, "file": None, "url": None,
                  "error": None, "model": model_key,
                  "label": re.sub(r"[^A-Za-z0-9_-]+", "_", str(label or ""))
                  .strip("_")[:24] or "clip",
                  "usd_note": note_prix(model_key)}
    asyncio.get_running_loop().create_task(_run(mid, Path(src), model_key, sujet))
    return mid
