"""ElevenLabs voiceover service. Optional — disabled if API key missing.

v1.3.1: Reads voice_ids and settings from persona JSON when available
(consolidation pack). Falls back to .env settings if persona has no voice_ids.
"""
import json
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


class VoiceoverService:
    """Generates voiceover audio (mp3) from script text via ElevenLabs."""

    def __init__(self, persona_id: str = "deepotus"):
        self.persona_id = persona_id
        self._persona_voice_ids = _load_persona_voice_ids(persona_id)

    @staticmethod
    def is_enabled() -> bool:
        return settings.has_voiceover

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
    ) -> Path:
        """Synthesize voiceover audio from text and save to disk.

        Returns the path to the generated mp3 file.
        """
        if not self.is_enabled():
            raise RuntimeError("ElevenLabs API key not configured")

        # Lazy import so the module loads even without elevenlabs installed
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        vid = voice_id or self.voice_id_for_language(language)
        v_settings = self.voice_settings()

        logger.info(
            f'Synthesizing voiceover ({language}, voice={vid}, '
            f'stability={v_settings.get("stability")}): "{text[:60]}..."'
        )
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=vid,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=v_settings,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
        logger.info(f"Voiceover saved: {output_path} ({output_path.stat().st_size // 1024} KB)")
        return output_path
