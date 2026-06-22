"""ElevenLabs voiceover service. Optional — disabled if API key missing.

v1.3.1: Reads voice_ids and settings from persona JSON when available
(consolidation pack). Falls back to .env settings if persona has no voice_ids.
"""
import json
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

    def generate_long(
        self,
        text: str,
        output_path: Path,
        language: str = "EN",
        voice_id: Optional[str] = None,
        max_chars: int = 2500,
    ) -> Path:
        """Synthesize possibly-long narration: chunk on sentence boundaries,
        TTS each chunk, then concat into a single mp3. Falls back to one
        generate() call when the text fits in a single request."""
        chunks = _chunk_text(text, max_chars)
        if not chunks:
            raise ValueError("Empty narration text")
        if len(chunks) == 1:
            return self.generate(text=chunks[0], output_path=output_path,
                                  language=language, voice_id=voice_id)
        tmpdir = Path(tempfile.mkdtemp(prefix="dz_vo_"))
        try:
            parts = []
            for i, ch in enumerate(chunks):
                part = tmpdir / f"part_{i:03d}.mp3"
                self.generate(text=ch, output_path=part,
                              language=language, voice_id=voice_id)
                parts.append(part)
            listfile = tmpdir / "concat.txt"
            listfile.write_text(
                "".join(f"file '{p.as_posix()}'\n" for p in parts),
                encoding="utf-8")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(listfile), "-c", "copy", str(output_path)],
                check=True, capture_output=True, timeout=180)
            logger.info(f"Long narration: {len(chunks)} chunks -> {output_path} "
                        f"({output_path.stat().st_size // 1024} KB)")
            return output_path
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
