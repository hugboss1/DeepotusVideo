"""ElevenLabs voiceover service. Optional — disabled if API key missing.

v1.3.1: Reads voice_ids and settings from persona JSON when available
(consolidation pack). Falls back to .env settings if persona has no voice_ids.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


PERSONAS_DIR = Path(__file__).parent.parent / "personas"


def _load_persona_voice_ids(persona_id: str = "deepotus") -> dict:
    """Load voice_ids block from persona JSON, or empty dict if absent."""
    path = PERSONAS_DIR / f"{persona_id}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("voice_ids", {}) or {}
    except Exception as e:
        logger.warning(f"Could not load persona voice_ids: {e}")
        return {}


# ── W-b (plan §2) — modèles TTS ElevenLabs ──────────────────────────────────
# Catalogue vérifié sur les docs ElevenLabs le 22/07/2026 (turbo v2.5
# déprécié — absent volontairement). max_chars = limite de caractères par
# requête API (borne le chunking ET le maxlength des UI) ; settings = clés
# voice_settings supportées par le modèle. Le multiplicateur de prix par
# modèle vit dans pricing.py (elevenlabs_model_mult) — changer LÀ-BAS d'abord.
ELEVEN_MODELS = {
    "eleven_multilingual_v2": {
        "label": "Multilingual v2 · qualité",
        "max_chars": 10_000,
        "settings": ("stability", "similarity_boost", "style", "speed"),
    },
    "eleven_v3": {
        "label": "Eleven v3 · expressif",
        "max_chars": 5_000,
        # v3 n'accepte que la stabilité, en valeurs discrètes 0 / 0.5 / 1
        # (Creative / Natural / Robust) — snappée par clamp_voice_settings.
        "settings": ("stability",),
    },
    "eleven_flash_v2_5": {
        "label": "Flash v2.5 · rapide, −50 %",
        "max_chars": 40_000,
        "settings": ("stability", "similarity_boost", "style", "speed"),
    },
}
DEFAULT_ELEVEN_MODEL = "eleven_multilingual_v2"

# Bornes API des voice_settings (speed : plage documentée 0.7–1.2).
_SETTING_BOUNDS = {"stability": (0.0, 1.0), "similarity_boost": (0.0, 1.0),
                   "style": (0.0, 1.0), "speed": (0.7, 1.2)}


def default_model_id() -> str:
    """Modèle TTS par défaut de l'app (ELEVENLABS_MODEL, sinon multilingual v2)."""
    mid = (getattr(settings, "ELEVENLABS_MODEL", "") or "").strip()
    return mid if mid in ELEVEN_MODELS else DEFAULT_ELEVEN_MODEL


def resolve_model(model_id: Optional[str]) -> str:
    """Id demandé (ou défaut app) validé contre le catalogue. ValueError si
    inconnu — les routes la traduisent en 400 propre."""
    mid = (model_id or "").strip() or default_model_id()
    if mid not in ELEVEN_MODELS:
        raise ValueError(f"Unknown TTS model: {mid!r} — modèles connus : "
                         + ", ".join(ELEVEN_MODELS))
    return mid


def clamp_voice_settings(model_id: str, base: Optional[dict],
                         override: Optional[dict]) -> dict:
    """voice_settings effectifs : défauts persona/app + overrides UI, clampés
    aux bornes API et filtrés aux clés que le modèle supporte (v3 : stabilité
    seule, snappée sur 0/0.5/1). use_speaker_boost (bool, persona) passe tel
    quel hors v3."""
    mid = resolve_model(model_id)
    allowed = set(ELEVEN_MODELS[mid]["settings"])
    merged = dict(base or {})
    for k, v in (override or {}).items():
        if v is not None:
            merged[k] = v
    out: dict = {}
    for k, v in merged.items():
        if k == "use_speaker_boost":
            if mid != "eleven_v3":
                out[k] = bool(v)
            continue
        if k not in allowed:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        lo, hi = _SETTING_BOUNDS.get(k, (0.0, 1.0))
        f = min(max(f, lo), hi)
        if mid == "eleven_v3" and k == "stability":
            f = min((0.0, 0.5, 1.0), key=lambda s: abs(s - f))
        out[k] = round(f, 3)
    return out


def _chunk_text(text: str, max_chars: int = 2500) -> list[str]:
    """Split long narration into <=max_chars chunks on sentence boundaries
    (ElevenLabs caps text per request). Over-long single sentences are
    hard-split as a fallback."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []
    units = re.split(r"(?<=[.!?…])\s+", text)
    chunks: list[str] = []
    cur = ""
    for u in units:
        u = u.strip()
        if not u:
            continue
        while len(u) > max_chars:  # a single giant sentence
            if cur:
                chunks.append(cur.strip())
                cur = ""
            chunks.append(u[:max_chars])
            u = u[max_chars:].strip()
        if len(cur) + len(u) + 1 > max_chars and cur:
            chunks.append(cur.strip())
            cur = u
        else:
            cur = (cur + " " + u).strip()
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


class VoiceoverService:
    """Generates voiceover audio (mp3) from script text via ElevenLabs."""

    def __init__(self, persona_id: str = "deepotus"):
        self.persona_id = persona_id
        self._persona_voice_ids = _load_persona_voice_ids(persona_id)

    @staticmethod
    def is_enabled() -> bool:
        """Une voix est possible : ElevenLabs (clé) OU Voicebox local joignable,
        selon le réglage atelier voice_provider (voir voice_providers)."""
        from app.services import voice_providers as VP
        return bool(VP.resolve_provider())

    def voice_id_for_language(self, language: str) -> str:
        """Resolve voice_id from persona (preferred) or .env fallback."""
        lang_key = language.upper()
        # Persona-driven (post-consolidation)
        if self._persona_voice_ids and lang_key in self._persona_voice_ids:
            entry = self._persona_voice_ids[lang_key]
            if isinstance(entry, dict) and "voice_id" in entry:
                return entry["voice_id"]
            if isinstance(entry, str):
                return entry
        # Fallback to .env (pre-consolidation behavior)
        if lang_key == "FR":
            return settings.ELEVENLABS_VOICE_ID_FR
        return settings.ELEVENLABS_VOICE_ID_EN

    def voice_settings(self) -> dict:
        """Return ElevenLabs voice_settings from persona, or sensible defaults."""
        defaults = {"stability": 0.55, "similarity_boost": 0.75}
        if self._persona_voice_ids and "settings" in self._persona_voice_ids:
            s = self._persona_voice_ids["settings"]
            if isinstance(s, dict):
                return {**defaults, **s}
        return defaults

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        reraise=True,
    )
    def generate(
        self,
        text: str,
        output_path: Path,
        language: str = "EN",
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        settings_override: Optional[dict] = None,
    ) -> Path:
        """Synthesize voiceover audio from text and save to disk.

        Routes to the configured voice provider (atelier voice_provider):
        ElevenLabs (historical default when its key is set) or the local
        Voicebox server. Returns the path to the generated audio file.

        W-b : model_id (catalogue ELEVEN_MODELS, défaut app) + settings_override
        (curseurs précision UI, clampés/filtrés par modèle) ; écriture atomique
        .part → rename pour ne jamais laisser de fichier partiel en Library.
        """
        from app.services import voice_providers as VP
        provider = VP.resolve_provider()
        if not provider:
            raise RuntimeError(
                "Aucune voix disponible : configure une clé ElevenLabs "
                "(Réglages) ou lance Voicebox en local.")
        if provider == "voicebox":
            # voice_id = profil Voicebox; les ids ElevenLabs hérités sont
            # ignorés proprement (repli profil par défaut) dans la façade.
            # model_id/settings_override sont propres à ElevenLabs : ignorés.
            return VP.voicebox_tts(text=text, output_path=output_path,
                                   language=language, voice_id=voice_id)

        # Lazy import so the module loads even without elevenlabs installed
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        vid = voice_id or self.voice_id_for_language(language)
        mid = resolve_model(model_id)
        v_settings = clamp_voice_settings(mid, self.voice_settings(),
                                          settings_override)

        logger.info(
            f'Synthesizing voiceover ({language}, voice={vid}, model={mid}, '
            f'stability={v_settings.get("stability")}): "{text[:60]}..."'
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_name(output_path.name + ".part")
        try:
            audio_stream = client.text_to_speech.convert(
                text=text,
                voice_id=vid,
                model_id=mid,
                output_format="mp3_44100_128",
                voice_settings=v_settings,
            )
            with tmp.open("wb") as f:
                for chunk in audio_stream:
                    if chunk:
                        f.write(chunk)
            os.replace(tmp, output_path)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            # Prefix the provider so the UI surfaces a clear, linkable error
            # for credit / paid-plan / quota failures on ElevenLabs.
            raise RuntimeError(f"ElevenLabs: {e}") from e
        logger.info(f"Voiceover saved: {output_path} ({output_path.stat().st_size // 1024} KB)")
        return output_path

    def generate_long(
        self,
        text: str,
        output_path: Path,
        language: str = "EN",
        voice_id: Optional[str] = None,
        max_chars: Optional[int] = None,
        model_id: Optional[str] = None,
        settings_override: Optional[dict] = None,
    ) -> Path:
        """Synthesize possibly-long narration: chunk on sentence boundaries,
        TTS each chunk, then concat into a single mp3. Falls back to one
        generate() call when the text fits in a single request.
        W-b : max_chars par défaut = plafond du modèle choisi (ELEVEN_MODELS) ;
        concat ffmpeg en .part → rename (zéro résidu partiel)."""
        mid = resolve_model(model_id)
        if max_chars is None:
            max_chars = ELEVEN_MODELS[mid]["max_chars"]
        chunks = _chunk_text(text, max_chars)
        if not chunks:
            raise ValueError("Empty narration text")
        if len(chunks) == 1:
            return self.generate(text=chunks[0], output_path=output_path,
                                  language=language, voice_id=voice_id,
                                  model_id=mid,
                                  settings_override=settings_override)
        tmpdir = Path(tempfile.mkdtemp(prefix="dz_vo_"))
        tmp_out = output_path.with_name(output_path.name + ".part")
        try:
            parts = []
            for i, ch in enumerate(chunks):
                part = tmpdir / f"part_{i:03d}.mp3"
                self.generate(text=ch, output_path=part,
                              language=language, voice_id=voice_id,
                              model_id=mid, settings_override=settings_override)
                parts.append(part)
            listfile = tmpdir / "concat.txt"
            listfile.write_text(
                "".join(f"file '{p.as_posix()}'\n" for p in parts),
                encoding="utf-8")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # .part n'est pas un suffixe connu de ffmpeg → format explicite.
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(listfile), "-c", "copy", "-f", "mp3",
                 str(tmp_out)],
                check=True, capture_output=True, timeout=180)
            os.replace(tmp_out, output_path)
            logger.info(f"Long narration: {len(chunks)} chunks -> {output_path} "
                        f"({output_path.stat().st_size // 1024} KB)")
            return output_path
        finally:
            tmp_out.unlink(missing_ok=True)
            shutil.rmtree(tmpdir, ignore_errors=True)
