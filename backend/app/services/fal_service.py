"""fal.ai client wrapper for Seedance 2.0 — v1.3.1+ patched.

PATCH (May 2026): handle non-ASCII filenames during upload.

Why: fal_client uses multipart HTTP form upload internally, which encodes the
filename in ASCII headers. Files like "accréditation.png", "café.jpg",
"été-2026.webp" etc. crash the upload with:
  'ascii' codec can't encode character '\\xe9' in position N

Fix: detect non-ASCII filename, copy to a temp file with an ASCII-safe name,
upload that, then clean up. The original file in assets/images is untouched.

New in v1.2:
- Smart routing: 1 image -> Pro single-image; 2 images -> Lite first-last-frame
- Returns seed used by the model (for reproducibility / regeneration)
"""
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
from pathlib import Path
from typing import Optional

import fal_client
import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY


if settings.FAL_KEY:
    os.environ["FAL_KEY"] = settings.FAL_KEY


# Endpoints
SEEDANCE_PRO_I2V = "fal-ai/bytedance/seedance/v1/pro/image-to-video"
SEEDANCE_LITE_I2V = "fal-ai/bytedance/seedance/v1/lite/image-to-video"


# ─── W-a (v1.19): multi-model video registry ─────────────────────────────
# Endpoint ids FROZEN 22/07/2026 against the live fal catalog and Google
# ListModels (plan docs/superpowers/plans/2026-07-22-modeles-generation-onthefly.md).
# "gemini-omni-flash-preview" was probed the same day and cannot generate
# video through generateContent ("This model only supports Interactions
# API") — the Google-native video path was then Veo 3.1 via
# predictLongRunning. t406 (01/11/2026) : Google a ARRÊTÉ les trois Veo 3.1
# preview le 22/10/2026 (doc vidéo ; 404 « no longer available » relevés le
# 01/11) ; la voie Google directe est désormais Gemini Omni Flash
# (`gemini-omni-1.1-flash`) par l'Interactions API (google_video.py).
# t406 — clés facultatives du retrait :
#   retire       date ISO de l'arrêt par le fournisseur : l'entrée reste
#                RÉSOLUBLE (anciennes recettes, graphes) mais sort des listes
#                (/video-models, catalogue) et tout tir est refusé (410) avant
#                la clé et la dépense — refus_retire()
#   remplacant   id du modèle proposé à la place dans le refus
#
# Caps come from each endpoint's OpenAPI schema (fal) / API probe (Google):
#   durations    native seconds the model accepts (longer targets are ffmpeg-
#                extended by the pipeline, same as before)
#   ratios       None = the endpoint has no aspect param (follows the image)
#   resolutions  None = no resolution param
#   end_image    first-last-frame support (guard raises a clean error) — the
#                ONLY fact read by accepte_fin(), the routes, the catalogue
#                and the pipeline
#   seed         seed param support (unsupported -> dropped with a note)
#   negatif      negative_prompt param support (absent = False ; unsupported
#                -> dropped with a note) — t184 : remplace la liste de familles
# t184 (G2) — clés facultatives :
#   image_arg     nom de l'image de départ (défaut "image_url" ; Kling v3 et
#                 Wan 3.0 : "start_image_url")
#   end_arg       nom de l'image de fin sur l'endpoint i2v (défaut "end_image_url")
#   endpoint_fl   endpoint SÉPARÉ quand une image de fin est donnée (Veo 3.1
#                 sur fal) — ROUTAGE seulement : end_image reste le fait
#   fl_args       noms (début, fin) sur endpoint_fl (défaut first/last_frame_url)
#   duree_suffixe présent = durée envoyée en CHAÎNE (« 8s » Veo, « 5 » Kling turbo)
#   res_alias     résolution de l'app -> résolution du fournisseur (H3 : 720p -> 768p)
#   resolution_maj résolution envoyée en MAJUSCULES (H3 : « 768P »)
#   extra_args    arguments fixes requis par le schéma (H3 : prompt_expansion_mode)
#   audio_param  name of the "generate audio" switch — always forced False:
#                the app's pipeline owns audio (VO node / ElevenLabs / BGM).
#                For most models pricing.py encodes the audio-off column;
#                Seedance 2.5 bills the same with or without audio (doc fal
#                lue le 26/09 : `generate_audio` sans effet sur le prix).
#                None on veo-google = audio is baked in (no switch, priced flat).
# usd_per_s is mirrored in pricing.py DEFAULTS["video_usd_per_s"] (user-editable).
# Défaut : Seedance 2.5 depuis le 27/09 (plan retours-ia, tâche 5). L'ancien
# défaut `seedance-v1-pro` reste au registre et choisissable ; les graphes et
# jobs déjà enregistrés gardent leur modèle.
DEFAULT_VIDEO_MODEL = "seedance-2.5"

VIDEO_MODELS: dict = {
    "seedance-v1-pro": {
        "label": "Seedance 1.0 Pro", "provider": "fal", "family": "seedance1",
        "endpoint": SEEDANCE_PRO_I2V,
        "durations": list(range(3, 11)), "ratios": ["9:16", "1:1", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": None,
    },
    "seedance-2": {
        "label": "Seedance 2.0", "provider": "fal", "family": "seedance2",
        "endpoint": "bytedance/seedance-2.0/image-to-video",
        "durations": list(range(4, 16)), "ratios": ["9:16", "1:1", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": False,
        "audio_param": "generate_audio",
    },
    "seedance-2-fast": {
        "label": "Seedance 2.0 Fast", "provider": "fal", "family": "seedance2",
        "endpoint": "bytedance/seedance-2.0/fast/image-to-video",
        "durations": list(range(4, 16)), "ratios": ["9:16", "1:1", "16:9"],
        "resolutions": ["720p"], "end_image": True, "seed": False,
        "audio_param": "generate_audio",
    },
    # Seedance 2.5 (Dreamina) — ajouté 28/08/2026, OpenAPI fal relu le jour
    # même : durées natives 4..30 s (enum "auto"|4-30 — l'app envoie l'entier),
    # aspect_ratio "auto" SEULEMENT (l'endpoint suit l'image -> ratios None,
    # aucun param envoyé), pas de seed d'entrée (présent en sortie seulement).
    # 1080p est accepté par l'endpoint mais fal ne publie que les $/s 480p et
    # 720p (facturation aux tokens, 0,0214 $/1k) : il reste HORS registre tant
    # que le chiffre n'est pas affiché — le clamp le dit dans les notes.
    "seedance-2.5": {
        "label": "Seedance 2.5", "provider": "fal", "family": "seedance25",
        "endpoint": "bytedance/seedance-2.5/image-to-video",
        "durations": list(range(4, 31)), "ratios": None,
        "resolutions": ["480p", "720p"], "end_image": True, "seed": False,
        "audio_param": "generate_audio",
    },
    "kling-v3-pro": {
        "label": "Kling v3 Pro", "provider": "fal", "family": "kling",
        "endpoint": "fal-ai/kling-video/v3/pro/image-to-video",
        "durations": list(range(3, 16)), "ratios": None,
        "resolutions": None, "end_image": True, "seed": False,
        "audio_param": "generate_audio", "image_arg": "start_image_url",
        "negatif": True,
    },
    "kling-v3-standard": {
        "label": "Kling v3 Standard", "provider": "fal", "family": "kling",
        "endpoint": "fal-ai/kling-video/v3/standard/image-to-video",
        "durations": list(range(3, 16)), "ratios": None,
        "resolutions": None, "end_image": True, "seed": False,
        "audio_param": "generate_audio", "image_arg": "start_image_url",
        "negatif": True,
    },
    "pixverse-v6": {
        "label": "PixVerse v6", "provider": "fal", "family": "pixverse",
        "endpoint": "fal-ai/pixverse/v6/image-to-video",
        "durations": [5, 8], "ratios": None,
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": True,
        "audio_param": "generate_audio_switch", "negatif": True,
    },
    # t184 (G2, plan « Génération IA enrichie », 11/10/2026) — schémas fal
    # relus le jour même (fal_schema.py + OpenAPI de la file). Veo 3.1 sur fal
    # accepte une image de FIN par un endpoint SÉPARÉ (`endpoint_fl`) qui
    # attend `first_frame_url` / `last_frame_url` (`fl_args`) au lieu de
    # `image_url` ; durées en chaînes « 4s|6s|8s » (`duree_suffixe`). Les
    # entrées Google natives (veo-3.1-*-google) restent : ce sont les JUMEAUX
    # de ces trois-là dans le catalogue (deux voies pour Veo).
    "veo-3.1-fast-fal": {
        "label": "Veo 3.1 Fast (fal)", "provider": "fal", "family": "veo_fal",
        "endpoint": "fal-ai/veo3.1/fast/image-to-video",
        "endpoint_fl": "fal-ai/veo3.1/fast/first-last-frame-to-video",
        "fl_args": ("first_frame_url", "last_frame_url"), "duree_suffixe": "s",
        "negatif": True,
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": "generate_audio",
    },
    "veo-3.1-fal": {
        "label": "Veo 3.1 (fal)", "provider": "fal", "family": "veo_fal",
        "endpoint": "fal-ai/veo3.1/image-to-video",
        "endpoint_fl": "fal-ai/veo3.1/first-last-frame-to-video",
        "fl_args": ("first_frame_url", "last_frame_url"), "duree_suffixe": "s",
        "negatif": True,
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": "generate_audio",
    },
    "veo-3.1-lite-fal": {
        "label": "Veo 3.1 Lite (fal)", "provider": "fal", "family": "veo_fal",
        "endpoint": "fal-ai/veo3.1/lite/image-to-video",
        "endpoint_fl": "fal-ai/veo3.1/lite/first-last-frame-to-video",
        "fl_args": ("first_frame_url", "last_frame_url"), "duree_suffixe": "s",
        "negatif": True,
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": "generate_audio",
    },
    # MiniMax H3 Max : `prompt_expansion_mode` REQUIS (disabled | balanced |
    # quality ; « balanced » = défaut du schéma, ~1 s) ; durée 0,92..15 s mais
    # facturée 5 s au minimum -> 5..15 ; résolutions en MAJUSCULES côté
    # endpoint (480P/768P/1080P) : le registre les garde en minuscules
    # (`resolution_maj`) et l'app qui demande 720p reçoit 768P (`res_alias`).
    # Pas de ratio (le cadre suit l'image), pas d'interrupteur audio.
    "h3-max": {
        "label": "MiniMax H3 Max", "provider": "fal", "family": "minimax",
        "endpoint": "minimax/h3-max/image-to-video",
        "durations": list(range(5, 16)), "ratios": None,
        "resolutions": ["480p", "768p", "1080p"], "res_alias": {"720p": "768p"},
        "resolution_maj": True, "end_image": True, "seed": True,
        "audio_param": None, "extra_args": {"prompt_expansion_mode": "balanced"},
    },
    # Wan 3.0 : image de départ `start_image_url` (requise), fin
    # `end_image_url`, durée entière 2..30 s, ratio « adaptive » par défaut
    # (suit l'image : rien n'est envoyé), interrupteur audio `audio`.
    "wan-3.0": {
        "label": "Wan 3.0", "provider": "fal", "family": "wan",
        "endpoint": "alibaba/wan-3.0/image-to-video", "image_arg": "start_image_url",
        "durations": list(range(2, 31)), "ratios": None,
        "resolutions": ["480p", "720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": "audio",
    },
    # Gemini Omni Flash v1.1 servi PAR FAL (voie fal ; jumeau de
    # gemini-omni-flash-google, t406) : durée entière 3..10 s, ni
    # seed ni interrupteur audio ; 360p et 4k existent mais restent hors
    # registre (720p/1080p seulement, comme les autres).
    "gemini-omni-flash": {
        "label": "Gemini Omni Flash (fal)", "provider": "fal", "family": "gemini_omni",
        "endpoint": "google/gemini-omni-flash/v1.1/image-to-video",
        "durations": list(range(3, 11)), "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": False,
        "audio_param": None,
    },
    # LTX 2.5 Fast : durées paires 6..20 s (enum), audio natif inclus au prix
    # (l'interrupteur est quand même coupé : le pipeline possède le son) ;
    # 1440p/2160p existent, hors registre.
    "ltx-2.5-fast": {
        "label": "LTX 2.5 Fast", "provider": "fal", "family": "ltx",
        "endpoint": "lightricks/ltx-2.5/image-to-video/fast",
        "durations": [6, 8, 10, 12, 14, 16, 18, 20], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": False,
        "audio_param": "generate_audio",
    },
    # Kling v3 Turbo Pro : `image_url` (PAS start_image_url comme Kling v3),
    # durée en CHAÎNE « 3 ».. « 15 » (`duree_suffixe` vide), ni image de fin,
    # ni ratio, ni résolution, ni négatif, ni seed, ni interrupteur audio.
    "kling-v3-turbo-pro": {
        "label": "Kling v3 Turbo Pro", "provider": "fal", "family": "kling",
        "endpoint": "fal-ai/kling-video/v3/turbo/pro/image-to-video",
        "image_arg": "image_url", "duree_suffixe": "",
        "durations": list(range(3, 16)), "ratios": None,
        "resolutions": None, "end_image": False, "seed": False,
        "audio_param": None,
    },
    # t407 (01/11/2026) — sortis sur fal le 16/10/2026, OpenAPI relue le jour
    # même. Kling 4.0 : `start_image_url` (requis) et `end_image_url` sur le
    # MÊME endpoint, durée ENTIÈRE 3..30 s, 720p/1080p (fal prend 1080p par
    # défaut : la résolution part toujours), ni ratio (suit l'image), ni seed,
    # ni négatif, ni interrupteur audio. `multi_prompt` et `middle_image_urls`
    # (plans multiples, images intermédiaires) restent hors registre.
    "kling-v4": {
        "label": "Kling 4.0", "provider": "fal", "family": "kling",
        "endpoint": "kling/v4/image-to-video", "image_arg": "start_image_url",
        "durations": list(range(3, 31)), "ratios": None,
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": False,
        "audio_param": None,
    },
    # FLUX 3 Max (Black Forest Labs) : `image_url` + `end_image_url` sur le
    # MÊME endpoint (le keyframes-to-video séparé reste hors registre), durée
    # entière 5..20 s, ratios 9:16/1:1/16:9 (auto, 21:9, 2:1, 4:3, 3:4 hors
    # registre), seed, `generate_audio` (vrai par défaut chez fal : coupé
    # comme partout), pas de négatif. `reasoning_level` laissé au défaut.
    "flux-3-max": {
        "label": "FLUX 3 Max", "provider": "fal", "family": "flux3",
        "endpoint": "blackforestlabs/flux-3-max/image-to-video",
        "durations": list(range(5, 21)), "ratios": ["9:16", "1:1", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": True,
        "audio_param": "generate_audio",
    },
    # t406 (01/11/2026) — Gemini Omni Flash 1.1 par la CLÉ GOOGLE (AI Studio,
    # Interactions API, google_video.py) : les crédits Google au lieu du solde
    # fal. Caps du jumeau fal (3..10 s, 9:16/16:9, début + fin) ; l'API a aussi
    # 360p et 4k (hors registre, comme le jumeau). Ni seed ni négatif.
    "gemini-omni-flash-google": {
        "label": "Gemini Omni Flash (Google)", "provider": "google", "family": "gemini_omni",
        "endpoint": "gemini-omni-1.1-flash",
        "durations": list(range(3, 11)), "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": True, "seed": False,
        "audio_param": None,
    },
    # Veo 3.1 preview par la clé Google : ARRÊTÉS par Google le 22/10/2026
    # (t406, voir l'en-tête) — résolubles, hors des listes, refusés au tir.
    "veo-3.1-google": {
        "label": "Veo 3.1 (Google)", "provider": "google", "family": "veo_google",
        "endpoint": "veo-3.1-generate-preview",
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": False,
        "audio_param": None, "retire": "2026-10-22", "remplacant": "gemini-omni-flash-google",
    },
    "veo-3.1-fast-google": {
        "label": "Veo 3.1 Fast (Google)", "provider": "google", "family": "veo_google",
        "endpoint": "veo-3.1-fast-generate-preview",
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": False,
        "audio_param": None, "retire": "2026-10-22", "remplacant": "gemini-omni-flash-google",
    },
    "veo-3.1-lite-google": {
        "label": "Veo 3.1 Lite (Google)", "provider": "google", "family": "veo_google",
        "endpoint": "veo-3.1-lite-generate-preview",
        "durations": [4, 6, 8], "ratios": ["9:16", "16:9"],
        "resolutions": ["720p", "1080p"], "end_image": False, "seed": False,
        "audio_param": None, "retire": "2026-10-22", "remplacant": "gemini-omni-flash-google",
    },
}


def est_retire(m: dict) -> bool:
    """t406 — le fournisseur a arrêté ce modèle (`retire`) : hors des listes,
    refusé au tir."""
    return bool((m or {}).get("retire"))


def refus_retire(m: dict, lang: "Optional[str]" = None) -> str:
    """t406 — le texte du refus d'un modèle retiré (messages.json :
    ia.video.retire), qui date l'arrêt et nomme le remplaçant."""
    from app import i18n as _i18n
    lang = lang or _i18n.langue_ui()
    iso = str(m.get("retire") or "")
    morceaux = iso.split("-")
    date = "/".join(reversed(morceaux)) if lang == "fr" and len(morceaux) == 3 else iso
    rempl = VIDEO_MODELS.get(m.get("remplacant") or "") or {}
    return _i18n.msg("ia.video.retire", lang, model=m.get("label", m.get("id", "?")), date=date,
                     remplacant=rempl.get("label", m.get("remplacant") or "?"))


def accepte_fin(m: dict) -> bool:
    """t184 (G2) — SOURCE UNIQUE : le modèle accepte une image de FIN
    (first-last-frame). Seul `end_image` le dit ; `endpoint_fl` ne fait que
    router (Veo 3.1 sur fal), il implique end_image (banc test_video_fl)."""
    return bool((m or {}).get("end_image"))


def refus_fin(label: str, lang: "Optional[str]" = None) -> str:
    """Le texte du refus « pas d'image de fin » (messages.json :
    ia.video.pas_de_fin), avec la liste des modèles qui en acceptent une."""
    from app import i18n as _i18n
    modeles = ", ".join(m["label"] for m in VIDEO_MODELS.values() if accepte_fin(m) and not est_retire(m))
    return _i18n.msg("ia.video.pas_de_fin", lang or _i18n.langue_ui(), model=label, modeles=modeles)


def resolve_video_model(model_id: "Optional[str]") -> dict:
    """Registry entry for `model_id` (default when falsy), with its id set.

    Unknown ids raise a clean ValueError listing the valid ones, so a job
    fails with an actionable `job.error` instead of a provider 404.
    """
    mid = (model_id or DEFAULT_VIDEO_MODEL).strip()
    m = VIDEO_MODELS.get(mid)
    if m is None:
        raise ValueError(
            f"Unknown video model '{mid}'. Available: "
            + ", ".join(sorted(VIDEO_MODELS)))
    return {**m, "id": mid}


def clamp_duration(model: dict, requested: int) -> int:
    """Nearest NATIVE duration >= requested (or the model max). The pipeline
    still ffmpeg-extends beyond the native max, exactly as before."""
    allowed = model["durations"]
    if requested in allowed:
        return requested
    bigger = [d for d in allowed if d > requested]
    return min(bigger) if bigger else max(allowed)


def generated_duration(model: dict, requested: int,
                       max_gen_s: "Optional[float]" = None) -> int:
    """Seconds actually GENERATED (and billed) for a `requested` clip length.

    Native clamp first (`clamp_duration`, min 3 s as before), then the cap
    `max_gen_s` (pricing.json `video_max_gen_s`, 10 s by default): above it,
    the largest native duration <= cap (or the model's minimum when none
    fits). The pipeline ffmpeg-extends the rest, exactly as before. A falsy
    cap keeps the previous behavior."""
    dur = clamp_duration(model, max(3, int(requested)))
    if max_gen_s:
        cap = int(max_gen_s)
        if dur > cap:
            under = [d for d in model["durations"] if d <= cap]
            dur = max(under) if under else min(model["durations"])
    return dur


def clamp_resolution(model: dict, requested: str) -> "Optional[str]":
    """Requested resolution if the model has it; else its best available.
    None when the endpoint has no resolution param."""
    res = model["resolutions"]
    if res is None:
        return None
    # t184 : une résolution voisine nommée autrement chez le fournisseur
    # (MiniMax H3 : 768p pour la 720p de l'app)
    requested = (model.get("res_alias") or {}).get(requested, requested)
    return requested if requested in res else res[-1]


def build_fal_args(
    model_id: str,
    *,
    image_url: str,
    prompt: str,
    negative_prompt: str = "",
    end_image_url: "Optional[str]" = None,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    resolution: str = "1080p",
    seed: "Optional[int]" = None,
) -> tuple:
    """Map the app's uniform request onto one fal endpoint's exact contract.

    Returns (endpoint, arguments, notes). Pure function — unit-tested against
    the frozen OpenAPI caps. Guards raise ValueError with a clean message.

    t184 (G2) : une image de fin bascule vers `endpoint_fl` quand le modèle
    en a un (Veo 3.1 sur fal : first_frame_url / last_frame_url, sans
    image_url) ; sinon elle part sur l'endpoint i2v sous `end_arg`. Un modèle
    qui n'accepte pas de fin (accepte_fin) lève ValueError (refus_fin).
    """
    m = resolve_video_model(model_id)
    if m["provider"] != "fal":
        raise ValueError(f"{m['label']} is not a fal model")
    notes: list = []

    if end_image_url and not accepte_fin(m):
        raise ValueError(refus_fin(m["label"]))

    dur = clamp_duration(m, duration)
    if dur != duration:
        notes.append(f"duration {duration}s->{dur}s")
    res = clamp_resolution(m, resolution)
    if res is not None and res != resolution:
        notes.append(f"resolution {resolution}->{res}")
    ratio_ok = m["ratios"] is not None and aspect_ratio in m["ratios"]
    if m["ratios"] is not None and not ratio_ok:
        notes.append(f"ratio {aspect_ratio} unsupported -> model default")

    family = m["family"]
    if family == "seedance1":
        # Legacy contract, byte-identical to the pre-W-a behavior: end frame
        # routes to the Lite endpoint (first-last), else Pro.
        endpoint = SEEDANCE_LITE_I2V if end_image_url else SEEDANCE_PRO_I2V
        args = {"image_url": image_url, "prompt": prompt, "duration": dur,
                "aspect_ratio": aspect_ratio, "resolution": res}
        if negative_prompt:
            args["negative_prompt"] = negative_prompt
        if seed is not None:
            args["seed"] = seed
        if end_image_url:
            args["end_image_url"] = end_image_url
        return endpoint, args, notes

    # t184 (G2) : image de fin -> endpoint first-last SÉPARÉ quand le modèle
    # en a un (Veo : first_frame_url / last_frame_url, sans image_url) ;
    # sinon l'endpoint i2v avec le nom d'argument du modèle (`image_arg`,
    # `end_arg` : Kling v3 et Wan 3.0 attendent start_image_url).
    if end_image_url and m.get("endpoint_fl"):
        endpoint = m["endpoint_fl"]
        k1, k2 = m.get("fl_args") or ("first_frame_url", "last_frame_url")
        args = {"prompt": prompt, k1: image_url, k2: end_image_url}
    else:
        endpoint = m["endpoint"]
        args = {"prompt": prompt, m.get("image_arg", "image_url"): image_url}
        if end_image_url:
            args[m.get("end_arg", "end_image_url")] = end_image_url
    # durée : Veo attend « 4s|6s|8s », Kling turbo « 5 » (chaîne nue),
    # les autres un entier
    if "duree_suffixe" in m:
        args["duration"] = f"{int(dur)}{m['duree_suffixe']}"
    else:
        args["duration"] = dur
    if ratio_ok:
        args["aspect_ratio"] = aspect_ratio
    if res is not None:
        args["resolution"] = res.upper() if m.get("resolution_maj") else res
    # negative_prompt : fait du registre (`negatif`), comme seed
    if negative_prompt:
        if m.get("negatif"):
            args["negative_prompt"] = negative_prompt
        else:
            notes.append("negative_prompt unsupported -> dropped")
    for k, v in (m.get("extra_args") or {}).items():
        args.setdefault(k, v)
    if seed is not None:
        if m["seed"]:
            args["seed"] = seed
        else:
            notes.append("seed unsupported -> dropped")
    if m["audio_param"]:
        # the pipeline owns audio (VO/BGM mix)
        args[m["audio_param"]] = False
    return endpoint, args, notes


def _ascii_safe_filename(filename: str) -> str:
    """Convert a filename to an ASCII-only safe equivalent.

    'accréditation.png' -> 'accreditation.png'
    'été 2026.jpg'      -> 'ete_2026.jpg'
    'café.png'          -> 'cafe.png'
    """
    # Normalize unicode (decompose accents into base+accent), then drop accents
    normalized = unicodedata.normalize("NFKD", filename)
    ascii_only = normalized.encode("ASCII", "ignore").decode("ASCII")
    # Replace any leftover non-safe chars with underscore
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", ascii_only)
    # Collapse double underscores
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "image.png"


def _filename_is_ascii_safe(name: str) -> bool:
    try:
        name.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


class FalSeedanceClient:
    @staticmethod
    async def upload_image(image_path: Path) -> str:
        """Upload to fal storage. Handles non-ASCII filenames transparently."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # If filename has non-ASCII chars, copy to a safe-named temp file first.
        # The original file in assets/images is never modified.
        cleanup_temp_path: Optional[Path] = None
        if _filename_is_ascii_safe(image_path.name):
            upload_path = image_path
        else:
            safe_name = _ascii_safe_filename(image_path.name)
            unique = uuid.uuid4().hex[:8]
            temp_dir = Path(tempfile.gettempdir())
            upload_path = temp_dir / f"deepotus_{unique}_{safe_name}"
            shutil.copy2(image_path, upload_path)
            cleanup_temp_path = upload_path
            logger.info(
                f"Filename has non-ASCII chars; renamed for upload: "
                f"'{image_path.name}' -> '{upload_path.name}'"
            )

        try:
            logger.info(f"Uploading image to fal storage: {upload_path.name}")
            url = await fal_client.upload_file_async(str(upload_path))
            logger.info(f"Image uploaded: {url}")
            return url
        finally:
            # Always clean up the temp file, even on failure
            if cleanup_temp_path is not None and cleanup_temp_path.exists():
                try:
                    cleanup_temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not clean up temp file {cleanup_temp_path}: {e}")

    @staticmethod
    async def _soumettre(endpoint: str, arguments: dict):
        """Submit to the fal queue ONCE — the application never replays.

        Mesuré le 27/09 : l'ancien `@retry(stop_after_attempt(3))` posé sur
        TOUT `generate_video` rejouait `subscribe_async` (soumission +
        attente + résultat) sur n'importe quelle exception — y compris une
        coupure pendant l'attente d'une génération DÉJÀ acceptée : jusqu'à
        trois générations payées pour un clip. Une boucle limitée aux
        `httpx.TransportError` ne suffit pas : ReadTimeout, ReadError et
        RemoteProtocolError arrivent APRÈS l'envoi de la requête.

        RISQUE RÉSIDUEL (daté 27/09, fal_client 1.0.1) : `submit_async`
        passe par `_async_maybe_retry_request`, qui rejoue SEUL la même POST
        jusqu'à `MAX_ATTEMPTS = 10` fois sur toute erreur de transport
        (dont ReadError / RemoteProtocolError après l'envoi) et sur les
        codes 408/409/429 et 502-504 d'ingress. Sondé sur un transport
        simulé : 10 POST pour une ReadError. Rien dans l'API publique ne le
        coupe : `start_timeout` ne neutralise que le rejeu des timeouts
        (1 POST sur ReadTimeout, toujours 10 sur ReadError) et change la
        sémantique côté serveur ; baisser `fal_client.client.MAX_ATTEMPTS`
        serait global (sondes d'état et résultats compris). Assumé tel quel."""
        return await fal_client.submit_async(endpoint, arguments=arguments)

    @staticmethod
    async def generate_video(
        image_url: str,
        prompt: str,
        negative_prompt: str = "",
        end_image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080p",
        seed: Optional[int] = None,
        model_id: str = DEFAULT_VIDEO_MODEL,
    ) -> dict:
        """Submit a video job to the selected fal model and wait for completion.

        `model_id` picks the VIDEO_MODELS entry (default = Seedance 2.5 since
        27/09; Seedance 1.0 Pro keeps its routing — Lite endpoint when an end
        frame is given — byte-for-byte). Args are mapped per family by
        build_fal_args.

        Returns dict with at least 'video' field (URL) and possibly 'seed'.
        """
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY is not configured. Set it in .env")

        endpoint, arguments, notes = build_fal_args(
            model_id,
            image_url=image_url,
            prompt=prompt,
            negative_prompt=negative_prompt,
            end_image_url=end_image_url,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            seed=seed,
        )
        logger.info(
            f"Submitting video job [{model_id}] to {endpoint} -- "
            f"duration={arguments.get('duration')}, ratio={aspect_ratio}, "
            f"res={resolution}, end_image={'yes' if end_image_url else 'no'}"
            + (f" -- caps: {'; '.join(notes)}" if notes else "")
        )

        try:
            handle = await FalSeedanceClient._soumettre(endpoint, arguments)
            # Accepted from here on: nothing is ever resubmitted.
            async for update in handle.iter_events(with_logs=True):
                logger.debug(f"fal.ai update: {update}")
            result = await handle.get()
        except Exception as e:
            # Provider-prefix so the UI surfaces a clear, linkable error
            # (credit / quota / billing failures on fal.ai).
            raise RuntimeError(f"fal.ai: {e}") from e
        logger.info(f"Video job [{model_id}] complete; result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        return result

    @staticmethod
    def extract_video_url(result: dict) -> Optional[str]:
        """fal.ai may return either {video: {url}} or {video_url} or {url}."""
        if not isinstance(result, dict):
            return None
        v = result.get("video")
        if isinstance(v, dict) and "url" in v:
            return v["url"]
        if isinstance(v, str):
            return v
        return result.get("video_url") or result.get("url")

    @staticmethod
    def extract_seed(result: dict) -> Optional[int]:
        """fal.ai sometimes returns the seed used so we can reproduce."""
        if not isinstance(result, dict):
            return None
        seed = result.get("seed")
        if isinstance(seed, (int, float)):
            return int(seed)
        return None

    @staticmethod
    async def download_video(video_url: str, dest_path: Path) -> Path:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading video -> {dest_path}")
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as client:
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                with dest_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        logger.info(f"Download complete: {dest_path} ({dest_path.stat().st_size // 1024} KB)")
        return dest_path
