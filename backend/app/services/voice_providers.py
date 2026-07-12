"""v1.26 — fournisseurs de voix interchangeables (spec voicebox 2026-07-11).

Le réglage atelier `voice_provider` choisit qui synthétise les voix off :
- elevenlabs : cloud, clé API, catalogue du compte (comportement historique)
- voicebox   : serveur local Voicebox (127.0.0.1:17493), gratuit/offline —
  moteur par défaut Kokoro (POC 2026-07-11 : 0,6× temps réel CPU), Chatterbox
  pour le clonage sur GPU récent. Les profils (dont voix clonées) se créent
  dans l'UI Voicebox ; ici on ne fait que les consommer via /profiles.

Défauts (spec) : elevenlabs si sa clé est présente, sinon voicebox s'il est
joignable. Voicebox n'est jamais une régression forcée.

Gotchas du contrat Voicebox v0.5.0 figés derrière cette façade :
- POST /generate est ASYNCHRONE → poller GET /history/{id} jusqu'à completed;
- engine doit être passé explicitement (le défaut serveur est qwen, jamais
  téléchargé chez nous) → on lit default_engine/preset_engine du profil;
- la sortie est du wav → conversion mp3 ffmpeg quand la destination l'exige.
"""
import re
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.config import settings

DEFAULT_VOICEBOX_URL = "http://127.0.0.1:17493"

PROVIDERS = {
    "elevenlabs": {"label": "ElevenLabs (cloud, clé API)"},
    "voicebox": {"label": "Voicebox (local, gratuit)"},
}


def voicebox_url() -> str:
    return (getattr(settings, "VOICEBOX_URL", "") or "").strip().rstrip("/") \
        or DEFAULT_VOICEBOX_URL


def voicebox_reachable(timeout: float = 2.0) -> bool:
    """Détection 'Voicebox lancé' (GET /health). Locale, pas de SSL."""
    try:
        r = httpx.get(voicebox_url() + "/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def configured_provider() -> str:
    """Réglage atelier `voice_provider`. Lecture sqlite SYNCHRONE en mode
    read-only : les appelants (VoiceoverService.generate) tournent hors boucle
    asyncio (run_in_executor), on ne peut pas réutiliser la session aiosqlite."""
    m = re.search(r"sqlite\+aiosqlite:///(.+)", settings.DATABASE_URL or "")
    if not m:
        return ""
    try:
        con = sqlite3.connect(f"file:{m.group(1)}?mode=ro", uri=True, timeout=2)
        try:
            row = con.execute(
                "SELECT value FROM atelier_settings WHERE key='voice_provider'"
            ).fetchone()
        finally:
            con.close()
        return (row[0] or "").strip().lower() if row else ""
    except Exception:
        return ""


def resolve_provider(requested: Optional[str] = None) -> str:
    """Provider effectif : demandé (ou réglage atelier) s'il est utilisable,
    sinon défauts de la spec. "" = aucune voix possible."""
    req = (requested if requested is not None else configured_provider())
    req = (req or "").strip().lower()
    if req == "elevenlabs" and settings.has_voiceover:
        return "elevenlabs"
    if req == "voicebox" and voicebox_reachable():
        return "voicebox"
    if settings.has_voiceover:
        return "elevenlabs"
    if voicebox_reachable():
        return "voicebox"
    return ""


def available() -> list[dict]:
    """Pour l'UI : chaque provider avec son état de disponibilité."""
    ready = {"elevenlabs": settings.has_voiceover,
             "voicebox": voicebox_reachable()}
    return [{"id": pid, "label": meta["label"], "ready": bool(ready[pid])}
            for pid, meta in PROVIDERS.items()]


# ─────────────────────────── catalogue Voicebox ───────────────────────────

def _preset_gender(preset_voice_id: str) -> str:
    """Convention des presets Kokoro (af_bella, am_adam, ff_siwis…) :
    2e lettre du préfixe = genre. Vide pour les clones (pas de preset)."""
    m = re.match(r"^[a-z]([fm])_", (preset_voice_id or "").lower())
    return {"f": "female", "m": "male"}[m.group(1)] if m else ""


def map_voicebox_profiles(profiles: list[dict]) -> list[dict]:
    """Pur (testable) : GET /profiles → catalogue au format du casting
    ({voice_id, name, category, labels, preview_url}, comme _fetch_11l_voices).
    Étape 3 spec : labels plus pauvres qu'ElevenLabs — on récupère ce qu'on
    peut (genre via le preset Kokoro, personality, description) et le prompt
    du casting complète en inférant depuis le nom/la description."""
    out = []
    for p in profiles or []:
        labels = {
            "language": (p.get("language") or "").lower(),
            "gender": _preset_gender(p.get("preset_voice_id")),
            "type": p.get("voice_type") or "",
            "engine": p.get("default_engine") or p.get("preset_engine") or "",
            "voice_preset": p.get("preset_voice_id") or "",
            "personality": p.get("personality") or "",
            "description": p.get("description") or "",
        }
        out.append({"voice_id": p.get("id"), "name": p.get("name"),
                    "category": "voicebox",
                    "labels": {k: v for k, v in labels.items() if v},
                    "preview_url": None})
    return [v for v in out if v["voice_id"]]


def _profiles_payload(data) -> list[dict]:
    if isinstance(data, list):
        return data
    return (data or {}).get("items") or (data or {}).get("profiles") or []


def list_voicebox_voices(timeout: float = 10.0) -> list[dict]:
    r = httpx.get(voicebox_url() + "/profiles", timeout=timeout)
    r.raise_for_status()
    return map_voicebox_profiles(_profiles_payload(r.json()))


# ─────────────────────────────── TTS Voicebox ───────────────────────────────

def build_generate_payload(profile: dict, text: str, language: str) -> dict:
    """Pur (testable) : payload POST /generate. L'engine vient du PROFIL
    (default_engine, sinon preset_engine, sinon kokoro) — le défaut serveur
    est qwen, non installé chez nous."""
    engine = (profile.get("default_engine") or profile.get("preset_engine")
              or "kokoro")
    return {"profile_id": profile["id"], "text": text,
            "language": (language or "en").strip().lower()[:2] or "en",
            "engine": engine}


def _pick_default_profile(client: httpx.Client, language: str) -> dict:
    """Sans voice_id : profil de la langue, en préférant le moteur Kokoro
    (décision POC 2026-07-12 : Kokoro par défaut — 0,6× temps réel CPU,
    Chatterbox ~12× réservé aux machines à GPU récent). Sinon premier profil."""
    r = client.get("/profiles")
    r.raise_for_status()
    profiles = _profiles_payload(r.json())
    if not profiles:
        raise RuntimeError(
            "Voicebox: aucun profil de voix — crée-en un dans l'app Voicebox "
            "(Voices) ou via son API /profiles.")
    lang = (language or "").strip().lower()[:2]
    pool = [p for p in profiles
            if (p.get("language") or "").lower().startswith(lang)] or profiles
    for p in pool:
        engine = p.get("default_engine") or p.get("preset_engine") or ""
        if engine == "kokoro":
            return p
    return pool[0]


def voicebox_tts(text: str, output_path: Path, language: str = "EN",
                 voice_id: Optional[str] = None, poll_s: float = 1.0,
                 timeout: float = 3600.0) -> Path:
    """texte → fichier audio via Voicebox. voice_id = id de profil Voicebox ;
    absent ou inconnu → profil par défaut de la langue (le casting croisé
    catalogue/personnages est l'étape 3 de la spec)."""
    with httpx.Client(base_url=voicebox_url(), timeout=120.0) as client:
        profile = None
        if voice_id:
            r = client.get(f"/profiles/{voice_id}")
            if r.status_code == 200:
                profile = r.json()
            else:
                logger.warning(
                    f"Voicebox: profil {voice_id} introuvable "
                    f"({r.status_code}) — repli sur le profil par défaut")
        if profile is None:
            profile = _pick_default_profile(client, language)

        payload = build_generate_payload(profile, text, language)
        logger.info(f"Voicebox TTS ({payload['language']}, "
                    f"profil={profile.get('name')}, engine={payload['engine']}): "
                    f'"{text[:60]}..."')
        r = client.post("/generate", json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"Voicebox: /generate {r.status_code}: "
                               f"{r.text[:200]}")
        gen = r.json()

        # statuts transitoires observés : generating, loading_model (1er appel
        # après démarrage) — on polle jusqu'à un statut TERMINAL.
        terminal = {"completed", "error", "failed", "cancelled"}
        t0 = time.monotonic()
        while gen.get("status") not in terminal:
            if time.monotonic() - t0 > timeout:
                raise RuntimeError("Voicebox: timeout de génération "
                                   f"({int(timeout)}s) — texte trop long ou "
                                   "moteur trop lent sur cette machine.")
            time.sleep(poll_s)
            rr = client.get(f"/history/{gen['id']}")
            rr.raise_for_status()
            gen = rr.json()
        if gen.get("status") != "completed":
            raise RuntimeError(
                f"Voicebox: génération {gen.get('status')}: "
                f"{gen.get('error') or 'erreur inconnue'}")

        audio = client.get(f"/audio/{gen['id']}")
        audio.raise_for_status()
        wav = audio.content

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".wav":
        output_path.write_bytes(wav)
    else:  # les pipelines attendent du mp3 (concat ffmpeg des VO par scène)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tf.write(wav)
            tmp = Path(tf.name)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(tmp), "-b:a", "128k",
                 str(output_path)],
                check=True, capture_output=True, timeout=300)
        finally:
            tmp.unlink(missing_ok=True)
    logger.info(f"Voicebox VO: {output_path} "
                f"({output_path.stat().st_size // 1024} KB)")
    return output_path
