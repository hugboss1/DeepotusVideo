# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T14, D4a) — clonage instantané ElevenLabs rattaché à une
ENTITÉ de la bible.

Endpoint relu le 06/10/2026 (elevenlabs.io/docs/api-reference/voices/ivc/create) :
POST /v1/voices/add, multipart — `name` et `files` requis, `description`,
`labels`, `remove_background_noise` facultatifs ; réponse `voice_id` et
`requires_verification`. La page ne documente AUCUNE limite de nombre ni de
taille : les bornes ci-dessous (1 à 25 prises, 100 Mo) sont les nôtres, pour
ne pas envoyer un dossier entier par erreur.

Pourquoi ici et pas dans elevenlabs_service : c'est un acte de BIBLE (une
entité gagne une voix), pas un acte de synthèse. Ce n'est pas une dépense au
caractère : un clone instantané occupe un emplacement de voix du compte
ElevenLabs (selon son plan) — l'écran le dit et demande confirmation. Voicebox
ne clone pas par API — ses profils se créent dans son application ; on le dit
plutôt que de faire semblant."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services import sfx_service
from app.services.sfx_service import SfxError

ADD_URL = "https://api.elevenlabs.io/v1/voices/add"
MIN_FILES, MAX_FILES = 1, 25
MAX_TOTAL_BYTES = 100 * 1024 * 1024


def _post_voice_add(key: str, name: str, files: list, description: str,
                    labels: dict, remove_noise: bool) -> dict:          # seam
    data = {"name": name, "description": description[:500],
            "labels": json.dumps(labels, ensure_ascii=False),
            "remove_background_noise": "true" if remove_noise else "false"}
    payload = [("files", (n, b, "application/octet-stream")) for n, b in files]
    with httpx.Client(verify=SSL_VERIFY, timeout=600.0) as c:
        r = c.post(ADD_URL, headers={"xi-api-key": key}, data=data, files=payload)
    if r.status_code not in (200, 201):
        st = r.status_code if 400 <= r.status_code < 500 else 502
        raise SfxError(st, f"ElevenLabs : {sfx_service._eleven_detail(r)}")
    d = r.json() or {}
    if not d.get("voice_id"):
        raise SfxError(502, "ElevenLabs : clonage sans voice_id en retour.")
    return d


def clone_for_entity(entity_id: str, entity_name: str, filenames: list,
                     description: str = "") -> dict:
    """Bloquant (httpx synchrone) — à appeler via run_in_executor. Les prises
    sont des NOMS du dossier audio de la Bibliothèque : un chemin (« ../ »,
    antislash) est refusé avant toute lecture, rien ne part."""
    key = (settings.ELEVENLABS_API_KEY or "").strip()
    if not key:
        # 503 : décision du 28/09 pour toute clé ou configuration de fournisseur absente
        raise SfxError(503, "Clonage de voix : clé ElevenLabs requise (Réglages → Clés). "
                            "Voicebox clone dans sa propre application, pas par cette API.")
    brut = [str(f) for f in (filenames or []) if str(f).strip()]
    if not brut or len(brut) > MAX_FILES:
        raise SfxError(400, f"Clonage : donne entre {MIN_FILES} et {MAX_FILES} prises du dossier "
                            "audio (1 à 2 minutes d'audio propre suffisent).")
    noms = []
    for f in brut:
        n = Path(f).name
        if n != f or "\\" in f or n in ("", ".", ".."):
            raise SfxError(400, f"prise refusée (un nom du dossier audio, pas un chemin) : {f[:60]}")
        noms.append(n)
    folder = sfx_service._audio_dir()
    files, total = [], 0
    for n in noms:
        p = folder / n
        if not p.is_file():
            raise SfxError(404, f"prise introuvable dans le dossier audio : {n}")
        b = p.read_bytes()
        total += len(b)
        if total > MAX_TOTAL_BYTES:
            raise SfxError(400, "Clonage : plus de 100 Mo de prises — refusé avant l'envoi.")
        files.append((n, b))
    d = _post_voice_add(key, str(entity_name)[:100], files, description,
                        {"deepotus_entity": entity_id}, True)
    logger.info(f"clone voix « {entity_name} » → {d['voice_id']} ({len(files)} prises, {total // 1024} Ko)")
    return {"voice_id": d["voice_id"], "voice_name": entity_name,
            "requires_verification": bool(d.get("requires_verification"))}
