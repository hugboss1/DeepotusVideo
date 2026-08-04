"""Pipeline orchestrator — v1.4."""
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schemas import (
    GenerateRequest,
    GenerateHeyGenRequest,
    CompositionRequest,
    CompositionLayout,
    JobStatus,
    Provider,
)
from app.services.fal_service import (
    FalSeedanceClient,
    DEFAULT_VIDEO_MODEL,
    clamp_duration,
    resolve_video_model,
)
from app.services.google_video import GoogleVeoClient
from app.services.heygen_service import HeyGenClient
from app.services.composition_service import CompositionService
from app.services.elevenlabs_service import VoiceoverService
from app.services.ffmpeg_service import FFmpegMerger
from app.services.prompt_engine import PromptEngine
from app.services.template_service import TemplateEngine
from app.services.news_illustration import news_illustration_engine
from app.services.storage import JobRecord, async_session_factory


def _delete_provider_output_dir(job) -> None:
    """sprite2d/asset3d write a whole per-job folder (frames, manifests,
    previews) under outputs/{sprites,assets3d}/{short} — the four *_path
    columns only cover single files, so deleting a job left the folder
    behind (fix 20/07/2026)."""
    sub = {"sprite2d": "sprites", "asset3d": "assets3d"}.get(job.provider or "")
    if not sub:
        return
    d = settings.outputs_path / sub / job.id[:8]
    try:
        if d.is_dir():
            import shutil
            shutil.rmtree(d)
            logger.info(f"Deleted output dir: {d}")
    except Exception as e:
        logger.warning(f"Could not delete output dir {d}: {e}")


def _save_source_graph(job_id: str, graph) -> None:
    """Couple a Studio node graph to a render job (for 'Reopen in Studio')."""
    if not graph:
        return
    try:
        import json
        gdir = settings.outputs_path / "_graphs"
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / f"{job_id}.json").write_text(
            json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"source_graph save failed for {job_id}: {e}")


def _preview_placeholder() -> Path:
    """A neutral avatar-ish still used in preview for HeyGen slots (no gen)."""
    p = settings.outputs_path / "_preview_avatar.png"
    if not p.exists():
        try:
            from PIL import Image, ImageDraw
            im = Image.new("RGB", (720, 720), (18, 22, 30))
            d = ImageDraw.Draw(im)
            d.ellipse([270, 190, 450, 370], fill=(58, 68, 88))
            d.rectangle([230, 400, 490, 640], fill=(58, 68, 88))
            d.text((250, 660), "AVATAR (preview)", fill=(150, 170, 190))
            p.parent.mkdir(parents=True, exist_ok=True)
            im.save(p)
        except Exception as e:
            logger.warning(f"preview placeholder failed: {e}")
    return p


def _preview_slot_values(slot_values: dict) -> dict:
    """Swap Seedance -> its source still, HeyGen -> a placeholder still, so a
    preview renders the composition without paying for generation."""
    from app.models.schemas import TemplateSlotValue
    out = {}
    for k, v in slot_values.items():
        sk = getattr(v, "source_kind", None)
        sd = getattr(v, "seedance", None)
        img = getattr(sd, "image_filename", None) if sd else None
        if sk == "seedance" and img:
            out[k] = TemplateSlotValue(source_kind="upload", upload_filename=img)
        elif sk == "heygen":
            out[k] = TemplateSlotValue(source_kind="file", file=str(_preview_placeholder()))
        else:
            out[k] = v
    return out


def _shorten_for_preview(tpl: dict, secs: float = 3.0) -> dict:
    """Cap the preview clip length and drop the 'from_slot' duration master
    (a still has no media duration to key off)."""
    t = dict(tpl)
    c = dict(t.get("canvas") or {})
    try:
        c["duration_s"] = min(float(c.get("duration_s", secs) or secs), secs)
    except (TypeError, ValueError):
        c["duration_s"] = secs
    t["canvas"] = c
    a = dict(t.get("audio") or {})
    if str(a.get("master_track", "")).startswith("from_slot"):
        a.pop("master_track", None)
    t["audio"] = a
    return t


def _resolve_music(music) -> tuple[Path | None, float]:
    """Resolve a {'file','volume_db'} BGM spec to (audio_dir path, volume_db).

    Returns (None, -14.0) when no/invalid music so callers can pass it through
    to merge() unconditionally. The file is looked up by basename in the shared
    audio asset dir (same dir the Library + audio endpoints use)."""
    vol = -14.0
    if not music or not isinstance(music, dict) or not music.get("file"):
        return None, vol
    try:
        vol = float(music.get("volume_db", -14) or -14)
    except (TypeError, ValueError):
        vol = -14.0
    mp = settings.images_path.parent / "audio" / Path(str(music["file"])).name
    if not mp.is_file():
        logger.warning(f"BGM file not found, skipping: {music.get('file')}")
        return None, vol
    return mp, vol


def _resolve_voiceover(voiceover) -> Path | None:
    """Resolve a {'file'} voice-over spec (pre-generated mp3, Studio Voiceover
    node) to its path in the shared audio asset dir, or None.

    Mirror of `_resolve_music` minus the volume: the VO track is mixed at
    0 dB (v1 — ducking is a §9 follow-up). Basename-only lookup keeps the
    file inside the audio dir (no path traversal)."""
    if not voiceover or not isinstance(voiceover, dict) or not voiceover.get("file"):
        return None
    vp = settings.images_path.parent / "audio" / Path(str(voiceover["file"])).name
    if not vp.is_file():
        logger.warning(f"Voiceover file not found, skipping: {voiceover.get('file')}")
        return None
    return vp


def _apply_voiceover_post(final_path: Path, vo_path: Path | None) -> Path:
    """Mix a pre-generated voice-over over an already-composited render
    (template path: the composite's own audio — BGM/master track — is kept
    under the VO). No VO -> the input path is returned untouched; otherwise
    a sibling `<stem>_vo.mp4` is written and returned."""
    if vo_path is None:
        return final_path
    out = final_path.with_name(final_path.stem + "_vo.mp4")
    FFmpegMerger.merge(final_path, vo_path, out, keep_video_audio=True)
    return out


class Pipeline:
    def __init__(self, persona_id: str = "deepotus"):
        self.engine = PromptEngine(persona_id=persona_id)
        self.fal = FalSeedanceClient()
        self.voice = VoiceoverService()
        self.merger = FFmpegMerger()
        self.template_engine = TemplateEngine()
        # HeyGen client is lazily initialized (requires key)
        self._heygen: HeyGenClient | None = None
        # W-a — Google-native video client (requires GEMINI_API_KEY)
        self._google: GoogleVeoClient | None = None

    @property
    def heygen(self) -> HeyGenClient:
        if self._heygen is None:
            self._heygen = HeyGenClient()
        return self._heygen

    @property
    def google(self) -> GoogleVeoClient:
        if self._google is None:
            self._google = GoogleVeoClient()
        return self._google

    async def _update(self, session: AsyncSession, job: JobRecord, **fields):
        for k, v in fields.items():
            setattr(job, k, v)
        await session.commit()
        await session.refresh(job)

    async def run(
        self,
        request: GenerateRequest,
        batch_id: str | None = None,
        batch_index: int | None = None,
        batch_size: int | None = None,
    ) -> str:
        """Run the full pipeline. Returns the job_id.

        Optional batch_id/batch_index/batch_size let multiple jobs be grouped
        in the UI as variations of the same prompt.
        """
        job_id = str(uuid4())
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                image_filename=request.image_filename,
                image_filename_end=request.image_filename_end,
                duration_s=request.duration_s,
                aspect_ratio=request.aspect_ratio.value,
                style=request.style.value,
                template_id=request.template_id,
                voiceover_language=request.voiceover_language.value,
                voice_mode=request.voice_mode.value if request.voice_mode else None,
                seed=request.seed,
                batch_id=batch_id,
                batch_index=batch_index,
                batch_size=batch_size,
                provider=Provider.SEEDANCE.value,
                video_model=(getattr(request, "video_model", None)
                             or DEFAULT_VIDEO_MODEL),
                created_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            _save_source_graph(job_id, getattr(request, "source_graph", None))

            try:
                # 1. Build prompt
                await self._update(session, job,
                                   status=JobStatus.PROMPT_BUILDING.value,
                                   current_step="Building prompt",
                                   progress=5)
                prompt, negative = self.engine.build_prompt(request)
                caption = self.engine.build_caption(request)
                vo_script = self.engine.build_voiceover_script(request)
                await self._update(session, job,
                                   final_prompt=prompt,
                                   negative_prompt=negative,
                                   caption_text=caption,
                                   progress=10)

                # 2. Resolve the video model (W-a) and prepare image(s).
                # fal uploads to fal storage; Google takes inline bytes (no
                # third-party upload). Guards fail the job with a clean error.
                model = resolve_video_model(getattr(request, "video_model", None))
                if model["provider"] == "google" and not settings.has_gemini:
                    raise RuntimeError(
                        "google: GEMINI_API_KEY not configured "
                        "(Settings -> Keys -> Google Gemini)")
                if model["provider"] == "fal" and not settings.FAL_KEY:
                    raise RuntimeError(
                        "fal.ai: FAL_KEY is not configured. Set it in .env")

                await self._update(session, job,
                                   status=JobStatus.UPLOADING.value,
                                   current_step="Preparing start image",
                                   progress=15)
                image_path = settings.images_path / request.image_filename
                if not image_path.exists():
                    raise FileNotFoundError(f"Start image not found: {image_path}")

                end_image_path = None
                if request.image_filename_end:
                    end_image_path = settings.images_path / request.image_filename_end
                    if not end_image_path.exists():
                        raise FileNotFoundError(
                            f"End image not found: {end_image_path}")
                    if not model["end_image"]:
                        raise RuntimeError(
                            f"{model['label']}: end frame (first-last) not "
                            "supported by this model — use a Seedance model")

                image_url = None
                end_image_url = None
                if model["provider"] == "fal":
                    await self._update(session, job,
                                       current_step="Uploading start image",
                                       progress=18)
                    image_url = await self.fal.upload_image(image_path)
                    if end_image_path is not None:
                        await self._update(session, job,
                                           current_step="Uploading end image",
                                           progress=21)
                        end_image_url = await self.fal.upload_image(end_image_path)

                await self._update(session, job, progress=25)

                # 3. Generate video
                step_label = (f"Generating video ({model['label']}"
                              + (", first-last)" if end_image_path else ")"))
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step=step_label,
                                   progress=30)
                # Each model has its own native duration set (clamped here);
                # longer targets are extended via ffmpeg afterwards
                # (1 generation, same cost).
                gen_dur = clamp_duration(model, max(3, request.duration_s))
                if model["provider"] == "google":
                    video_client = self.google
                    result = await self.google.generate_video(
                        image_path=image_path,
                        prompt=prompt,
                        negative_prompt=negative,
                        duration=gen_dur,
                        aspect_ratio=request.aspect_ratio.value,
                        resolution=request.resolution,
                        model=model["endpoint"],
                    )
                else:
                    video_client = self.fal
                    result = await self.fal.generate_video(
                        image_url=image_url,
                        end_image_url=end_image_url,
                        prompt=prompt,
                        negative_prompt=negative,
                        duration=gen_dur,
                        aspect_ratio=request.aspect_ratio.value,
                        resolution=request.resolution,
                        seed=request.seed,
                        model_id=model["id"],
                    )
                video_url = video_client.extract_video_url(result)
                if not video_url:
                    raise RuntimeError(
                        f"No video URL in provider response: {result}")

                # Persist seed used by the model (so user can regenerate)
                used_seed = video_client.extract_seed(result) or request.seed
                if used_seed is not None:
                    await self._update(session, job, seed=used_seed)

                # 4. Download video
                await self._update(session, job,
                                   status=JobStatus.DOWNLOADING.value,
                                   current_step="Downloading video",
                                   progress=70)
                video_dest = settings.outputs_path / "videos" / f"{job_id}.mp4"
                await video_client.download_video(video_url, video_dest)

                # Extend to the requested 5s-increment target if longer than
                # what Seedance produced (fit a HeyGen avatar length).
                if request.duration_s > gen_dur:
                    await self._update(
                        session, job,
                        current_step=(f"Extending {gen_dur}s -> "
                                      f"{request.duration_s}s "
                                      f"({request.extend_mode})"),
                        progress=74)
                    ext = (settings.outputs_path / "videos"
                           / f"{job_id}_ext.mp4")
                    self.merger.extend(video_dest, ext,
                                       request.duration_s,
                                       request.extend_mode)
                    video_dest = ext

                await self._update(session, job,
                                   video_path=str(video_dest), progress=78)

                # 5. Voiceover (optional) — an explicit pre-generated file
                # (request.voiceover, Studio Voiceover node) replaces persona
                # synthesis: no double track, no surprise ElevenLabs cost.
                vo_path = _resolve_voiceover(getattr(request, "voiceover", None))
                audio_dest = None
                if (request.voiceover_enabled and vo_script
                        and self.voice.is_enabled() and vo_path is None):
                    await self._update(session, job,
                                       status=JobStatus.GENERATING_VOICEOVER.value,
                                       current_step="Synthesizing voiceover",
                                       progress=85)
                    audio_dest = settings.outputs_path / "audio" / f"{job_id}.mp3"
                    self.voice.generate(
                        text=vo_script,
                        output_path=audio_dest,
                        language=request.voiceover_language.value,
                    )
                    await self._update(session, job, audio_path=str(audio_dest))

                # 6. Merge
                await self._update(session, job,
                                   status=JobStatus.MERGING.value,
                                   current_step="Merging audio + video",
                                   progress=92)
                final_dest = settings.outputs_path / "final" / f"{job_id}.mp4"
                _mus_path, _mus_vol = _resolve_music(request.music)
                self.merger.merge(video_dest, audio_dest or vo_path, final_dest,
                                  music_path=_mus_path, music_volume_db=_mus_vol)
                await self._update(session, job, final_video_path=str(final_dest))

                # 7. Save caption
                if caption:
                    cap_dest = settings.outputs_path / "captions" / f"{job_id}.txt"
                    cap_dest.parent.mkdir(parents=True, exist_ok=True)
                    cap_dest.write_text(caption, encoding="utf-8")
                    await self._update(session, job, caption_path=str(cap_dest))

                # 8. Done
                await self._update(
                    session, job,
                    status=JobStatus.DONE.value,
                    current_step="Complete",
                    progress=100,
                    completed_at=datetime.utcnow(),
                )
                logger.success(f"Job {job_id} complete -> {final_dest}")

            except Exception as e:
                logger.exception(f"Job {job_id} failed: {e}")
                await self._update(
                    session, job,
                    status=JobStatus.FAILED.value,
                    current_step="Failed",
                    error=str(e),
                    completed_at=datetime.utcnow(),
                )
                raise

        return job_id

    # ----- HeyGen pipeline (v1.4) -----

    async def run_heygen(
        self,
        request: GenerateHeyGenRequest,
        *,
        composition_id: str | None = None,
        layer_index: int | None = None,
    ) -> str:
        """Generate a HeyGen avatar video. Returns the job_id.

        Optional composition_id/layer_index link this job to a composition.
        """
        job_id = str(uuid4())
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                image_filename=request.avatar_id,  # store the avatar_id where image lives
                aspect_ratio=request.aspect_ratio.value,
                voice_mode=request.voice_mode.value if request.voice_mode else None,
                provider=Provider.HEYGEN.value,
                composition_id=composition_id,
                layer_index=layer_index,
                created_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            _save_source_graph(job_id, getattr(request, "source_graph", None))

            try:
                # 1. Build the script (apply voice-mode tone if requested)
                await self._update(session, job,
                                   status=JobStatus.PROMPT_BUILDING.value,
                                   current_step="Preparing script",
                                   progress=10)
                script = request.script.strip()
                # Optional: inject voice-mode flavor on the front of the script
                if request.voice_mode:
                    mode_block = self.engine.persona.get("voice_modes", {}).get(request.voice_mode.value)
                    if mode_block and mode_block.get("style_hints"):
                        # Don't modify the user's script, but log the mode being applied
                        logger.info(f"HeyGen job uses voice_mode={request.voice_mode.value} "
                                    f"({mode_block.get('description', '')})")

                # Build a caption from the script if user didn't provide one
                caption = request.custom_caption or self._heygen_caption_from_script(
                    script, request.voice_mode
                )
                await self._update(session, job,
                                   final_prompt=script,
                                   caption_text=caption,
                                   progress=15)

                # 2. Submit to HeyGen
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step="Submitting HeyGen video",
                                   progress=25)
                # v1.16 — an explicit engine (avatar_iii/iv/v) routes through
                # HeyGen API v3; no engine = untouched legacy v2 path. Talking
                # photos always stay on v2 (v3 talking_photo mapping is
                # undocumented).
                use_v3 = bool(getattr(request, "engine", None)) \
                    and request.avatar_type != "talking_photo"
                if use_v3:
                    video_id = await self.heygen.generate_video_v3(
                        text=script,
                        avatar_id=request.avatar_id,
                        voice_id=request.voice_id,
                        engine=request.engine,
                        aspect_ratio=request.aspect_ratio.value,
                        speed=request.speed,
                        background_color=request.background_color,
                        motion_prompt=getattr(request, "motion_prompt", None),
                        expressiveness=getattr(request, "expressiveness", None),
                    )
                else:
                    video_id = await self.heygen.generate_video(
                        text=script,
                        avatar_id=request.avatar_id,
                        voice_id=request.voice_id,
                        avatar_type=request.avatar_type,
                        aspect_ratio=request.aspect_ratio.value,
                        speed=request.speed,
                        background_color=request.background_color,
                        use_avatar_iv=request.use_avatar_iv,
                    )

                # 3. Poll until complete
                await self._update(session, job,
                                   current_step="Rendering on HeyGen servers",
                                   progress=45)
                if use_v3:
                    result = await self.heygen.poll_video_status_v3(video_id)
                else:
                    result = await self.heygen.poll_video_status(video_id)
                video_url = result.get("video_url")
                if not video_url:
                    raise RuntimeError(f"No video_url in HeyGen result: {result}")

                # 4. Download
                await self._update(session, job,
                                   status=JobStatus.DOWNLOADING.value,
                                   current_step="Downloading HeyGen video",
                                   progress=80)
                video_dest = settings.outputs_path / "videos" / f"{job_id}.mp4"
                await self.heygen.download_video(video_url, video_dest)
                # Optional looped BGM and/or pre-generated VO under the talking
                # avatar (keep its voice: avatar + VO is the wanted mix).
                final_path = video_dest
                _mus_path, _mus_vol = _resolve_music(request.music)
                _vo_path = _resolve_voiceover(getattr(request, "voiceover", None))
                if _mus_path is not None or _vo_path is not None:
                    final_path = settings.outputs_path / "final" / f"{job_id}.mp4"
                    self.merger.merge(video_dest, _vo_path, final_path,
                                      music_path=_mus_path, music_volume_db=_mus_vol,
                                      keep_video_audio=True)
                await self._update(session, job,
                                   video_path=str(video_dest),
                                   final_video_path=str(final_path),
                                   progress=95)

                # 5. Save caption
                if caption:
                    cap_dest = settings.outputs_path / "captions" / f"{job_id}.txt"
                    cap_dest.parent.mkdir(parents=True, exist_ok=True)
                    cap_dest.write_text(caption, encoding="utf-8")
                    await self._update(session, job, caption_path=str(cap_dest))

                await self._update(
                    session, job,
                    status=JobStatus.DONE.value,
                    current_step="Complete",
                    progress=100,
                    completed_at=datetime.utcnow(),
                )
                logger.success(f"HeyGen job {job_id} complete -> {video_dest}")

            except Exception as e:
                logger.exception(f"HeyGen job {job_id} failed: {e}")
                await self._update(
                    session, job,
                    status=JobStatus.FAILED.value,
                    current_step="Failed",
                    error=str(e),
                    completed_at=datetime.utcnow(),
                )
                raise

        return job_id

    async def run_heygen_image(self, request) -> str:
        """v1.16 (D) — animate a Library still (HeyGen v3 type=image).

        Same job lifecycle as run_heygen: record → submit → poll → download →
        optional BGM merge → caption. request: GenerateHeyGenImageRequest."""
        job_id = str(uuid4())
        img_path = settings.images_path / request.image_filename
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                image_filename=request.image_filename,
                aspect_ratio=request.aspect_ratio.value,
                voice_mode=request.voice_mode.value if request.voice_mode else None,
                provider=Provider.HEYGEN.value,
                title=f"Animate · {request.image_filename}",
                created_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            _save_source_graph(job_id, getattr(request, "source_graph", None))
            try:
                script = request.script.strip()
                caption = request.custom_caption or self._heygen_caption_from_script(
                    script, request.voice_mode)
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step="Submitting animated image (v3)",
                                   final_prompt=script, caption_text=caption,
                                   progress=20)
                video_id = await self.heygen.generate_image_video_v3(
                    img_path, script, request.voice_id,
                    engine=request.engine,
                    aspect_ratio=request.aspect_ratio.value,
                    speed=request.speed,
                    motion_prompt=request.motion_prompt,
                    expressiveness=request.expressiveness,
                    title=f"Animate {request.image_filename}",
                )
                await self._update(session, job,
                                   current_step="Rendering on HeyGen servers",
                                   progress=45)
                result = await self.heygen.poll_video_status_v3(video_id)
                video_url = result.get("video_url")
                if not video_url:
                    raise RuntimeError(f"No video_url in HeyGen v3 result: {result}")
                await self._update(session, job,
                                   status=JobStatus.DOWNLOADING.value,
                                   current_step="Downloading video",
                                   progress=80)
                video_dest = settings.outputs_path / "videos" / f"{job_id}.mp4"
                await self.heygen.download_video(video_url, video_dest)
                final_path = video_dest
                _mus_path, _mus_vol = _resolve_music(request.music)
                _vo_path = _resolve_voiceover(getattr(request, "voiceover", None))
                if _mus_path is not None or _vo_path is not None:
                    final_path = settings.outputs_path / "final" / f"{job_id}.mp4"
                    self.merger.merge(video_dest, _vo_path, final_path,
                                      music_path=_mus_path,
                                      music_volume_db=_mus_vol,
                                      keep_video_audio=True)
                await self._update(session, job,
                                   video_path=str(video_dest),
                                   final_video_path=str(final_path),
                                   progress=95)
                if caption:
                    cap_dest = settings.outputs_path / "captions" / f"{job_id}.txt"
                    cap_dest.parent.mkdir(parents=True, exist_ok=True)
                    cap_dest.write_text(caption, encoding="utf-8")
                    await self._update(session, job, caption_path=str(cap_dest))
                await self._update(session, job, status=JobStatus.DONE.value,
                                   current_step="Complete", progress=100,
                                   completed_at=datetime.utcnow())
                logger.success(f"HeyGen image job {job_id} complete -> {video_dest}")
            except Exception as e:
                logger.exception(f"HeyGen image job {job_id} failed: {e}")
                await self._update(session, job, status=JobStatus.FAILED.value,
                                   current_step="Failed", error=str(e),
                                   completed_at=datetime.utcnow())
                raise
        return job_id

    async def run_heygen_cinematic(self, request) -> str:
        """v1.16 (D) — HeyGen v3 cinematic avatar (prompt-driven, no script).
        request: GenerateHeyGenCinematicRequest."""
        job_id = str(uuid4())
        refs = [settings.images_path / f for f in (request.reference_images or [])]
        refs = [p for p in refs if p.exists()]
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                image_filename=(request.reference_images[0]
                                if request.reference_images else "cinematic"),
                aspect_ratio=request.aspect_ratio,
                provider=Provider.HEYGEN.value,
                title=f"Cinematic · {request.prompt[:60]}",
                created_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()
            _save_source_graph(job_id, getattr(request, "source_graph", None))
            try:
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step="Submitting cinematic video (v3)",
                                   final_prompt=request.prompt,
                                   caption_text=request.custom_caption,
                                   progress=20)
                video_id = await self.heygen.generate_cinematic_v3(
                    request.prompt, request.look_ids,
                    reference_paths=refs,
                    duration_s=request.duration_s,
                    auto_duration=request.auto_duration,
                    aspect_ratio=request.aspect_ratio,
                    resolution=request.resolution,
                    title=f"Cinematic {job_id[:8]}",
                )
                await self._update(session, job,
                                   current_step="Rendering on HeyGen servers",
                                   progress=45)
                result = await self.heygen.poll_video_status_v3(video_id)
                video_url = result.get("video_url")
                if not video_url:
                    raise RuntimeError(f"No video_url in HeyGen v3 result: {result}")
                await self._update(session, job,
                                   status=JobStatus.DOWNLOADING.value,
                                   current_step="Downloading video", progress=80)
                video_dest = settings.outputs_path / "videos" / f"{job_id}.mp4"
                await self.heygen.download_video(video_url, video_dest)
                await self._update(session, job,
                                   video_path=str(video_dest),
                                   final_video_path=str(video_dest),
                                   status=JobStatus.DONE.value,
                                   current_step="Complete", progress=100,
                                   completed_at=datetime.utcnow())
                logger.success(f"HeyGen cinematic job {job_id} complete -> {video_dest}")
            except Exception as e:
                logger.exception(f"HeyGen cinematic job {job_id} failed: {e}")
                await self._update(session, job, status=JobStatus.FAILED.value,
                                   current_step="Failed", error=str(e),
                                   completed_at=datetime.utcnow())
                raise
        return job_id

    def _heygen_caption_from_script(self, script: str, voice_mode) -> str:
        """Generate a basic caption from a HeyGen script, optionally voice-mode aware."""
        first_line = script.split(".")[0].strip()[:80]
        # Pull hashtags from persona
        tags = " ".join(self.engine.persona.get("default_hashtags_pool", [])[:4])
        # Apply voice mode example if available
        mode_block = None
        if voice_mode:
            mode_block = self.engine.persona.get("voice_modes", {}).get(voice_mode.value)
        if mode_block:
            ex = mode_block.get("example_caption_en", "")
            if "\n" in ex:
                tail = ex.split("\n", 1)[1].strip()
            else:
                tail = ex
            return f"{first_line}.\n\n{tail}\n\n{tags}"
        return f"{first_line}.\n\nFrom the deep. 🐙\n\n{tags}"

    # ----- Composition pipeline (v1.4) -----

    async def run_episode(self, *, job_id: str, title=None, voice_id=None,
                          language: str = "en", scenes: list | None = None) -> str:
        """Render a narrated illustrated episode: per-scene TTS narration + a
        Ken Burns (or still) image clip, concatenated into one 9:16 video.
        Seedance-marked scenes fall back to Ken Burns in v1."""
        import asyncio
        import shutil
        scenes = scenes or []
        loop = asyncio.get_running_loop()
        async with async_session_factory() as session:
            first_img = next((s.get("image_filename") for s in scenes
                              if s.get("image_filename")), None)
            # v1.15.6 — capture cost inputs so /cost/usage prices the episode
            # correctly: N illustrations + the ElevenLabs narration (total
            # chars). Ken Burns / still motion is local ffmpeg = free, so no
            # Seedance line (unlike the old default "image + 10s seedance").
            import json as _json
            _ep_chars = sum(len((s.get("text") or "")) for s in scenes)
            _ep_imgs = sum(1 for s in scenes if s.get("image_filename")) \
                or max(1, len(scenes))
            job = JobRecord(
                id=job_id, title=(title or "Épisode")[:200],
                status=JobStatus.QUEUED.value,
                image_filename=(first_img or "episode")[:255],
                aspect_ratio="9:16", provider="episode",
                cost_meta=_json.dumps({"images": _ep_imgs, "chars": _ep_chars}),
                created_at=datetime.utcnow())
            session.add(job)
            await session.commit()
            try:
                work = settings.outputs_path / "_tmp_episode" / job_id
                if work.exists():
                    shutil.rmtree(work, ignore_errors=True)
                work.mkdir(parents=True, exist_ok=True)
                n = max(1, len(scenes))
                clips = []
                for i, sc in enumerate(scenes):
                    await self._update(
                        session, job, status=JobStatus.GENERATING_VOICEOVER.value,
                        current_step=f"Scène {i+1}/{n} — narration",
                        progress=int(5 + (i / n) * 80))
                    text = (sc.get("text") or "").strip()
                    audio_i = work / f"a{i:03d}.mp3"
                    if text and self.voice.is_enabled():
                        await loop.run_in_executor(
                            None, lambda t=text, a=audio_i: self.voice.generate_long(
                                t, a, language=language, voice_id=voice_id))
                    dur = self.merger.probe_dur(audio_i) if audio_i.exists() else 0.0
                    if dur <= 0.1:
                        dur = 3.0
                    img = sc.get("image_filename")
                    img_path = (settings.images_path / img) if img else None
                    clip_i = work / f"c{i:03d}.mp4"
                    a_arg = audio_i if audio_i.exists() else None
                    motion = sc.get("motion") or "kenburns"
                    await loop.run_in_executor(
                        None, lambda ip=img_path, a=a_arg, o=clip_i, m=motion, d=dur:
                        self.merger.scene_clip(ip, a, o, motion=m, dur=d))
                    clips.append(clip_i)
                await self._update(session, job, status=JobStatus.MERGING.value,
                                   current_step="Assemblage de l'épisode", progress=90)
                final = settings.outputs_path / "final" / f"{job_id}.mp4"
                await loop.run_in_executor(
                    None, lambda: self.merger.concat_clips(clips, final))
                await self._update(
                    session, job, status=JobStatus.DONE.value,
                    current_step="Complete", final_video_path=str(final),
                    progress=100, completed_at=datetime.utcnow())
                logger.success(f"Episode {job_id} complete -> {final}")
                shutil.rmtree(work, ignore_errors=True)
            except Exception as e:
                logger.exception(f"Episode {job_id} failed: {e}")
                await self._update(session, job, status=JobStatus.FAILED.value,
                                   current_step="Failed", error=str(e),
                                   completed_at=datetime.utcnow())
                raise
        return job_id

    async def run_composition(self, request: CompositionRequest) -> tuple[str, str, str]:
        """Generate both clips in parallel, then compose them.

        Returns (composition_id, seedance_job_id, heygen_job_id).
        The composition output is stored as a new "final" file.
        """
        import asyncio
        composition_id = str(uuid4())
        logger.info(f"Starting composition {composition_id} (layout={request.layout.value})")

        # 1. Kick off both generations in parallel
        seedance_task = asyncio.create_task(
            self.run(request.seedance, batch_id=None,
                     batch_index=None, batch_size=None)
        )
        heygen_task = asyncio.create_task(
            self.run_heygen(request.heygen, composition_id=composition_id, layer_index=1)
        )

        # Tag the Seedance job AFTER it's created with the composition_id.
        # We do this by waiting until both complete then patching.
        seedance_job_id = await seedance_task
        heygen_job_id = await heygen_task

        # Tag the Seedance job with composition metadata
        async with async_session_factory() as session:
            seedance_job = await session.get(JobRecord, seedance_job_id)
            if seedance_job:
                seedance_job.composition_id = composition_id
                seedance_job.layer_index = 0
                seedance_job.composition_layout = request.layout.value
                await session.commit()

            heygen_job = await session.get(JobRecord, heygen_job_id)
            if heygen_job:
                heygen_job.composition_layout = request.layout.value
                await session.commit()

        # 2. Resolve clip paths
        async with async_session_factory() as session:
            seedance_job = await session.get(JobRecord, seedance_job_id)
            heygen_job = await session.get(JobRecord, heygen_job_id)

            if not seedance_job or not heygen_job:
                raise RuntimeError("One of the composition jobs vanished from DB")
            if seedance_job.status != JobStatus.DONE.value:
                raise RuntimeError(f"Seedance job failed: {seedance_job.error}")
            if heygen_job.status != JobStatus.DONE.value:
                raise RuntimeError(f"HeyGen job failed: {heygen_job.error}")

            seedance_clip = Path(seedance_job.final_video_path)
            heygen_clip = Path(heygen_job.final_video_path)

        # 3. Compose
        out_path = settings.outputs_path / "final" / f"composition_{composition_id}.mp4"

        if request.layout == CompositionLayout.SEQUENTIAL:
            CompositionService.sequential(
                clip_a=heygen_clip,    # avatar speaks first
                clip_b=seedance_clip,  # then animation plays
                output=out_path,
                aspect_ratio=request.seedance.aspect_ratio.value,
                transition_duration_s=request.transition_duration_s,
                target_duration_s=request.target_duration_s,
            )
        elif request.layout in (CompositionLayout.SPLIT_VSTACK, CompositionLayout.SPLIT_HSTACK):
            layout_mode = "vstack" if request.layout == CompositionLayout.SPLIT_VSTACK else "hstack"
            CompositionService.split_screen(
                clip_top=seedance_clip,
                clip_bottom=heygen_clip,
                output=out_path,
                layout=layout_mode,
                aspect_ratio=request.seedance.aspect_ratio.value,
                target_duration_s=request.target_duration_s,
                audio_source=request.audio_source,
            )
        else:
            raise ValueError(f"Unknown composition layout: {request.layout}")

        # 4. Create a "composition" parent job pointing to the final
        async with async_session_factory() as session:
            comp_job = JobRecord(
                id=composition_id,
                status=JobStatus.DONE.value,
                progress=100,
                current_step="Composition complete",
                image_filename=request.seedance.image_filename,
                aspect_ratio=request.seedance.aspect_ratio.value,
                voice_mode=(request.heygen.voice_mode.value if request.heygen.voice_mode else None),
                provider=Provider.COMPOSITION.value,
                composition_id=composition_id,
                composition_layout=request.layout.value,
                layer_index=-1,  # -1 marks the parent
                final_video_path=str(out_path),
                video_path=str(out_path),
                caption_text=heygen_job.caption_text if heygen_job else None,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            session.add(comp_job)
            await session.commit()

        logger.success(f"Composition {composition_id} complete -> {out_path}")
        return composition_id, seedance_job_id, heygen_job_id

    # ----- Template render pipeline (v1.6) -----

    async def render_template(
        self,
        template_id: str,
        slot_values: dict,
        *,
        voice_mode=None,
        job_id: str | None = None,
        template: dict | None = None,
        title: str | None = None,
        source_graph: dict | None = None,
        preview: bool = False,
        voiceover: dict | None = None,
    ) -> str:
        """Resolve every slot (Seedance/HeyGen in parallel, upload/file/text
        inline), then composite via the template engine. If `template` (an
        inline dict) is given, unsaved editor edits render exactly as seen.
        Returns the parent job_id. A parent JobRecord (provider='template')
        tracks progress; sub-jobs are tagged with composition_id=job_id.
        """
        import asyncio

        job_id = job_id or str(uuid4())
        if template is not None:
            tpl = template
        else:
            tpl = self.template_engine.get_template(template_id)
        # Overlays (TextOverlay/Ticker/Separator wired to the Render node) are
        # rebuilt from the source graph so they apply on EVERY render branch
        # (UGC, Concatenate, ...), not just Spatial compose. See graph_overlays.
        if source_graph:
            try:
                from app.services import graph_overlays
                tpl = graph_overlays.inject_overlays(tpl, source_graph)
            except Exception as e:
                logger.warning(f"overlay injection skipped for {job_id}: {e}")
            # Effects/Mask nodes -> per-layer region effects + global post_effects.
            try:
                from app.services import graph_effects
                tpl = graph_effects.inject_effects(tpl, source_graph, slot_values)
            except Exception as e:
                logger.warning(f"effects injection skipped for {job_id}: {e}")
        # Preview pass: swap Seedance/HeyGen slots for their source still (no
        # fal/HeyGen cost) and shorten, so the composition/overlays/effects can
        # be visualised before the paid Run. Done AFTER injections so effect
        # node->region mapping still uses the real seedance slot_values.
        if preview:
            slot_values = _preview_slot_values(slot_values)
            tpl = _shorten_for_preview(tpl)
        slots = self.template_engine.slots_from(tpl)

        async with async_session_factory() as session:
            parent = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                current_step="Queued (template render)",
                progress=0,
                title=(title or "").strip() or None,
                image_filename=f"template:{template_id}",
                provider=Provider.TEMPLATE.value,
                template_id=template_id,
                composition_id=job_id,
                composition_layout=template_id,
                layer_index=-1,
                aspect_ratio=str(tpl.get("canvas", {}).get("width", 1080)) + "x"
                + str(tpl.get("canvas", {}).get("height", 1920)),
                voice_mode=voice_mode.value if voice_mode else None,
                created_at=datetime.utcnow(),
            )
            session.add(parent)
            await session.commit()

        try:
            # Phase 1: dispatch sub-generations / resolve static inputs
            tasks: dict[str, "asyncio.Task"] = {}
            static_paths: dict[str, Path] = {}
            text_values: dict[str, str] = {}
            is_seq = tpl.get("render_mode") == "sequential"
            for slot in slots:
                sname = slot["slot_name"]
                sv = slot_values.get(sname)
                if sv is None:
                    if slot["type"] == "text_slot":
                        continue  # engine falls back to region default_text
                    if is_seq:
                        continue  # montage act left empty -> skipped
                    raise ValueError(f"Slot '{sname}' has no value provided")
                kind = sv.source_kind
                if kind == "seedance":
                    if sv.seedance is None:
                        raise ValueError(
                            f"Slot '{sname}': source_kind=seedance but no payload")
                    if voice_mode and not sv.seedance.voice_mode:
                        sv.seedance.voice_mode = voice_mode
                    tasks[sname] = asyncio.create_task(self.run(sv.seedance))
                elif kind == "heygen":
                    if sv.heygen is None:
                        raise ValueError(
                            f"Slot '{sname}': source_kind=heygen but no payload")
                    if voice_mode and not sv.heygen.voice_mode:
                        sv.heygen.voice_mode = voice_mode
                    tasks[sname] = asyncio.create_task(
                        self.run_heygen(sv.heygen, composition_id=job_id,
                                        layer_index=len(tasks)))
                elif kind in ("upload", "file"):
                    if kind == "file":
                        p = Path(sv.file_path or "")
                    else:
                        name = sv.upload_filename or ""
                        p = settings.images_path / name
                        if not p.exists():
                            p = settings.outputs_path / name
                    if not p.exists():
                        raise FileNotFoundError(
                            f"Slot '{sname}': source file not found ({p})")
                    static_paths[sname] = p
                elif kind == "job":
                    if not sv.job_id:
                        raise ValueError(
                            f"Slot '{sname}': source_kind=job but no job_id")
                    async with async_session_factory() as session:
                        jr = await session.get(JobRecord, sv.job_id)
                    fp = jr and (jr.final_video_path or jr.video_path)
                    if not fp:
                        raise FileNotFoundError(
                            f"Slot '{sname}': job {sv.job_id} has no video")
                    jp = Path(fp)
                    if not jp.exists():
                        raise FileNotFoundError(
                            f"Slot '{sname}': job video missing ({jp})")
                    static_paths[sname] = jp
                elif kind == "text":
                    text_values[sname] = sv.text or ""
                else:
                    raise ValueError(
                        f"Slot '{sname}': unknown source_kind {kind}")

            async with async_session_factory() as session:
                p = await session.get(JobRecord, job_id)
                p.status = JobStatus.GENERATING_VIDEO.value
                p.current_step = f"Resolving {len(tasks)} clip(s) in parallel"
                p.progress = 20
                await session.commit()

            # Phase 2: await generations, collect resolved sources
            resolved: dict[str, dict] = {}
            caption: str | None = None
            for sname, task in tasks.items():
                sub_id = await task
                async with async_session_factory() as session:
                    jr = await session.get(JobRecord, sub_id)
                    if jr is None:
                        raise RuntimeError(
                            f"Sub-job vanished for slot '{sname}'")
                    if jr.status != JobStatus.DONE.value:
                        raise RuntimeError(
                            f"Slot '{sname}' generation failed: {jr.error}")
                    jr.composition_id = job_id
                    jr.composition_layout = template_id
                    await session.commit()
                    fp = jr.final_video_path or jr.video_path
                    if caption is None and jr.caption_text:
                        caption = jr.caption_text
                if not fp:
                    raise RuntimeError(f"Slot '{sname}' produced no video")
                resolved[sname] = {"path": Path(fp)}
            for sname, sp in static_paths.items():
                resolved[sname] = {"path": sp}
            for sname, tv in text_values.items():
                resolved[sname] = {"text": tv}

            if is_seq:
                vid_names = {
                    s["slot_name"] for s in slots
                    if s["type"] in ("video_slot", "image_slot")
                }
                n_clips = sum(
                    1 for k, v in resolved.items()
                    if k in vid_names and v.get("path"))
                if n_clips < 2:
                    raise ValueError(
                        "Montage needs at least 2 filled clips "
                        f"(got {n_clips}).")

            async with async_session_factory() as session:
                p = await session.get(JobRecord, job_id)
                p.status = JobStatus.MERGING.value
                p.current_step = "Compositing template (ffmpeg)"
                p.progress = 75
                await session.commit()

            # Phase 3: render the composite (sync -> executor)
            out_path = settings.outputs_path / "final" / f"template_{job_id}.mp4"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.template_engine.render(
                    template_id, resolved, out_path, template=tpl),
            )

            # Phase 3b: mix the pre-generated voice-over (Studio Voiceover
            # node) over the composite — its own audio (BGM/master) is kept.
            final_out = out_path
            vo_path = _resolve_voiceover(voiceover)
            if vo_path is not None:
                async with async_session_factory() as session:
                    p = await session.get(JobRecord, job_id)
                    p.current_step = "Mixing voice-over (ffmpeg)"
                    p.progress = 90
                    await session.commit()
                final_out = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _apply_voiceover_post(out_path, vo_path))

            # Phase 4: finalize parent
            async with async_session_factory() as session:
                p = await session.get(JobRecord, job_id)
                p.status = JobStatus.DONE.value
                p.current_step = "Template render complete"
                p.progress = 100
                p.final_video_path = str(final_out)
                p.video_path = str(out_path)
                if caption:
                    p.caption_text = caption
                p.completed_at = datetime.utcnow()
                await session.commit()
            logger.success(f"Template render {job_id} complete -> {out_path}")
            return job_id

        except Exception as e:
            logger.exception(f"Template render {job_id} failed: {e}")
            async with async_session_factory() as session:
                p = await session.get(JobRecord, job_id)
                if p:
                    p.status = JobStatus.FAILED.value
                    p.current_step = "Failed"
                    p.error = str(e)
                    p.completed_at = datetime.utcnow()
                    await session.commit()
            raise

    # ----- News illustration pipeline (v1.7) -----

    async def run_news_illustration(
        self,
        items: list,
        *,
        per_card_s: float = 3.5,
        engine: str = "ffmpeg",
        job_id: str | None = None,
    ) -> str:
        """Render a branded news-illustration reel from selected headlines.

        Produces a silent 1080x1920 MP4 (the avatar carries audio when this is
        composed via a template/Composition). Lands as a DONE JobRecord with
        provider='news' so it shows in the queue and is reusable in template
        slots via source_kind='job'.
        """
        import asyncio

        job_id = job_id or str(uuid4())
        async with async_session_factory() as session:
            job = JobRecord(
                id=job_id,
                status=JobStatus.QUEUED.value,
                current_step="Queued (news illustration)",
                progress=0,
                image_filename=f"news:{len(items)} items",
                aspect_ratio="1080x1920",
                provider=Provider.NEWS.value,
                created_at=datetime.utcnow(),
            )
            session.add(job)
            await session.commit()

            try:
                await self._update(session, job,
                                   status=JobStatus.GENERATING_VIDEO.value,
                                   current_step="Rendering news reel",
                                   progress=30)
                out_path = (settings.outputs_path / "final"
                            / f"news_{job_id}.mp4")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: news_illustration_engine.render(
                        items, out_path, per_card_s=per_card_s, engine=engine),
                )
                await self._update(
                    session, job,
                    status=JobStatus.DONE.value,
                    current_step="Complete",
                    progress=100,
                    video_path=str(out_path),
                    final_video_path=str(out_path),
                    completed_at=datetime.utcnow(),
                )
                logger.success(
                    f"News illustration {job_id} -> {out_path}")
            except Exception as e:
                logger.exception(f"News illustration {job_id} failed: {e}")
                await self._update(
                    session, job,
                    status=JobStatus.FAILED.value,
                    current_step="Failed",
                    error=str(e),
                    completed_at=datetime.utcnow(),
                )
                raise
        return job_id

    @staticmethod
    async def get_job(job_id: str) -> JobRecord | None:
        async with async_session_factory() as session:
            res = await session.execute(select(JobRecord).where(JobRecord.id == job_id))
            return res.scalar_one_or_none()

    @staticmethod
    async def rename_job(job_id: str, title: str | None) -> JobRecord | None:
        async with async_session_factory() as session:
            res = await session.execute(
                select(JobRecord).where(JobRecord.id == job_id))
            job = res.scalar_one_or_none()
            if not job:
                return None
            job.title = (title or "").strip() or None
            await session.commit()
            await session.refresh(job)
            return job

    @staticmethod
    async def list_jobs(limit: int = 50) -> list[JobRecord]:
        async with async_session_factory() as session:
            res = await session.execute(
                select(JobRecord).order_by(JobRecord.created_at.desc()).limit(limit)
            )
            return list(res.scalars().all())

    @staticmethod
    async def delete_job(job_id: str) -> bool:
        """Delete a job's DB record + all associated files on disk.
        Returns True if deletion succeeded, False if job not found.
        """
        async with async_session_factory() as session:
            res = await session.execute(select(JobRecord).where(JobRecord.id == job_id))
            job = res.scalar_one_or_none()
            if not job:
                return False

            # Best-effort file cleanup — don't fail the whole op if a file is missing
            for path_str in [job.video_path, job.audio_path,
                             job.final_video_path, job.caption_path]:
                if path_str:
                    try:
                        p = Path(path_str)
                        if p.exists():
                            p.unlink()
                            logger.info(f"Deleted file: {p}")
                    except Exception as e:
                        logger.warning(f"Could not delete {path_str}: {e}")
            _delete_provider_output_dir(job)

            await session.execute(delete(JobRecord).where(JobRecord.id == job_id))
            await session.commit()
            logger.info(f"Job {job_id} deleted")
            return True

    @staticmethod
    async def delete_batch(batch_id: str) -> int:
        """Delete all jobs in a batch and their files. Returns count deleted."""
        async with async_session_factory() as session:
            res = await session.execute(
                select(JobRecord).where(JobRecord.batch_id == batch_id)
            )
            jobs = list(res.scalars().all())
            count = 0
            for job in jobs:
                for path_str in [job.video_path, job.audio_path,
                                 job.final_video_path, job.caption_path]:
                    if path_str:
                        try:
                            p = Path(path_str)
                            if p.exists():
                                p.unlink()
                        except Exception as e:
                            logger.warning(f"Could not delete {path_str}: {e}")
                _delete_provider_output_dir(job)
                count += 1
            await session.execute(
                delete(JobRecord).where(JobRecord.batch_id == batch_id)
            )
            await session.commit()
            logger.info(f"Batch {batch_id}: deleted {count} jobs")
            return count
