"""P4 (plan Quick T4, tâche #50 du suivi, 01/10/2026) — la finition d'un rendu Quick : graver les sous-titres SUR le
mp4 final.

Deux chemins, un seul par défaut :
  * `align` (défaut, GRATUIT, hors ligne) — le texte est déjà connu (script de l'avatar, voix off réellement dite, ou
    champ « texte à caler ») : transcribe_service le cale sur les silences RÉELS du fichier ;
  * `transcribe` (PAYANT) — seulement si l'écran l'a DEMANDÉ explicitement (case « Transcrire (payant) ») ; la route
    l'a alors chiffré dans sa garde des plafonds AVANT le rendu. Écart daté au plan : le plan basculait seul sur la
    transcription quand le texte manquait — c'était une dépense non demandée.

Le mp4 final n'est remplacé qu'APRÈS une gravure réussie (temporaire + `replace`) : un ffmpeg qui échoue laisse le
rendu payé intact. Et `apply` ne laisse jamais remonter d'exception : un sous-titre raté ne coûte pas un rendu.
"""
import asyncio
import subprocess
from pathlib import Path

from loguru import logger

from app.services import subtitle_service as S
from app.services import transcribe_service as T
from app.services.effects_preview import ffmpeg_bin

CANVAS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
CPS_MIN, CPS_MAX = 16, 84


def segments_for(video, text: str, *, lang: str = "fr", source: str = "align", provider: str = "", cps: int = 42) -> list:
    """Répliques datées pour ce mp4. `align` ne coûte rien ; `transcribe` paie (et doit avoir été demandé)."""
    video = Path(video)
    cps = max(CPS_MIN, min(CPS_MAX, int(cps or 42)))
    if source == "transcribe":
        res = T.transcribe(video, provider=provider or None, language=lang)
    elif source == "align":
        if not (text or "").strip():
            raise ValueError("Sous-titres : aucun texte à caler. Écrivez le texte (ou le script), "
                             "ou cochez la transcription payante.")
        res = T.align_to_audio(text.strip(), video, lang=lang)
    else:
        raise ValueError(f"Sous-titres : source inconnue {source!r} (align ou transcribe)")
    cues = T.group_words(res["words"], max_chars=cps)
    return [{"id": f"q{i + 1}", "start": c["start"], "end": c["end"], "text": c["text"], "words": c.get("words") or []}
            for i, c in enumerate(cues)]


def burn(video, segments: list, *, style="standard", ratio: str = "9:16") -> Path:
    """Grave les répliques sur `video`, en place via un temporaire. Rend l'.ass."""
    video = Path(video)
    if not segments:
        raise ValueError("Sous-titres : aucune réplique à graver")
    ass = video.with_suffix(".ass")
    ass.write_text(S.to_ass(segments, style, canvas=CANVAS.get(ratio, CANVAS["9:16"])), encoding="utf-8")
    tmp = video.with_name(video.stem + ".subs.mp4")
    r = subprocess.run(
        [ffmpeg_bin(), "-y", "-v", "error", "-i", str(video), "-vf", S.subtitles_filter(ass), "-c:a", "copy",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(tmp)],
        capture_output=True, timeout=1800)
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1024:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError("Gravure des sous-titres : " + r.stderr.decode("utf-8", "replace")[-400:])
    tmp.replace(video)
    return ass


def transcription_demandee(opts) -> bool:
    """Vrai seulement si l'écran a explicitement demandé la transcription payante."""
    return isinstance(opts, dict) and bool(opts.get("on")) and str(opts.get("source") or "") == "transcribe"


async def apply(video, opts, *, text: str, ratio: str) -> dict:
    """Crochet du pipeline. Ne lève JAMAIS : rend un compte rendu que le job peut journaliser.
    `opts` = le champ `subtitles` de la requête."""
    if not isinstance(opts, dict) or not opts.get("on"):
        return {"on": False}
    try:
        segs = await asyncio.to_thread(
            segments_for, video, text, lang=str(opts.get("lang") or "fr"),
            source="transcribe" if transcription_demandee(opts) else "align",
            provider=str(opts.get("provider") or ""), cps=opts.get("cps") or 42)
        ass = await asyncio.to_thread(burn, video, segs, style=opts.get("style") or "standard", ratio=ratio)
        return {"on": True, "segments": len(segs), "ass": ass.name}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"quick_finish: sous-titres sautés ({e})")
        return {"on": True, "error": str(e)[:300]}
