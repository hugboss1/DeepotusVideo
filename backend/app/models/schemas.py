"""Pydantic schemas for API I/O — v1.2 with end_image, seed, prompt builder."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class StylePreset(str, Enum):
    UGC_RAW = "ugc_raw"
    CINEMATIC = "cinematic"
    HYBRID = "hybrid"


class CameraMove(str, Enum):
    PUSH_IN = "slow push-in"
    PULL_OUT = "slow pull-out"
    ORBIT = "360-degree orbit"
    TRACKING = "tracking shot"
    HANDHELD = "handheld with subtle shake"
    STATIC = "static, locked-off"
    LOW_ANGLE = "low angle dramatic"
    RACK_FOCUS = "rack focus reveal"
    DOLLY_ZOOM = "dolly zoom (vertigo effect)"
    WHIP_PAN = "whip pan transition"
    CRANE_DOWN = "crane shot descending"


class Lighting(str, Enum):
    SOFT_WINDOW = "soft natural window light"
    GOLDEN_HOUR = "golden hour rim light"
    NEON = "neon city lights, cyan and magenta"
    TUNGSTEN = "warm tungsten practicals"
    OVERCAST = "overcast diffused light"
    DARK_MOODY = "dark moody chiaroscuro"
    BIOLUMINESCENT = "bioluminescent underwater glow"
    STROBE = "rhythmic strobe pulses"


class AspectRatio(str, Enum):
    VERTICAL = "9:16"
    SQUARE = "1:1"
    HORIZONTAL = "16:9"


class Language(str, Enum):
    EN = "EN"
    FR = "FR"


class VoiceMode(str, Enum):
    """Brand voice modes from DESIGN.md section 1.3.

    Drives prompt style hints, caption tone, vocabulary filtering,
    and ElevenLabs voice settings.
    """
    ORACLE = "oracle"
    ALPHA = "alpha"
    ZEN = "zen"
    MEMER = "memer"


class Provider(str, Enum):
    """Which video generation backend to use."""
    SEEDANCE = "seedance"
    HEYGEN = "heygen"
    COMPOSITION = "composition"
    TEMPLATE = "template"
    NEWS = "news"


class CompositionLayout(str, Enum):
    """How two clips are combined for composition jobs."""
    SEQUENTIAL = "sequential"      # clip A then clip B with brief transition
    SPLIT_VSTACK = "split_vstack"  # top (Seedance) / bottom (HeyGen)
    SPLIT_HSTACK = "split_hstack"  # left / right


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROMPT_BUILDING = "prompt_building"
    UPLOADING = "uploading_image"
    GENERATING_VIDEO = "generating_video"
    DOWNLOADING = "downloading_video"
    GENERATING_VOICEOVER = "generating_voiceover"
    MERGING = "merging"
    DONE = "done"
    FAILED = "failed"


class PromptSource(str, Enum):
    """How the final prompt was built."""
    TEMPLATE = "template"
    BUILDER = "builder"        # generated from keywords
    CUSTOM = "custom"          # user wrote it from scratch


# ============ Templates ============

class PromptTemplate(BaseModel):
    id: str
    name: str
    description: str
    subject_pattern: str
    action: str
    camera: CameraMove
    setting: str
    lighting: Lighting
    pacing: Literal["slow", "medium", "fast"] = "medium"
    duration_s: int = 5
    voiceover_script_en: Optional[str] = None
    voiceover_script_fr: Optional[str] = None
    caption_pattern_en: Optional[str] = None
    caption_pattern_fr: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)


# ============ Job request/response ============

class GenerateRequest(BaseModel):
    image_filename: str = Field(..., description="Start image filename")
    image_filename_end: Optional[str] = Field(None, description="Optional end frame for transition video")

    # Prompt source — exactly one path:
    template_id: Optional[str] = None
    custom_prompt: Optional[str] = None    # raw or builder-generated, used as-is

    style: StylePreset = StylePreset.HYBRID
    camera: Optional[CameraMove] = None
    lighting: Optional[Lighting] = None
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    # Up to 60s in 5s increments. Seedance generates <=10s natively; longer
    # targets are extended via ffmpeg (extend_mode) to fit a HeyGen avatar.
    duration_s: int = Field(5, ge=3, le=60)
    extend_mode: Literal["loop", "hold"] = "loop"
    resolution: Literal["720p", "1080p"] = "1080p"

    voiceover_enabled: bool = True
    voiceover_language: Language = Language.EN
    voiceover_script: Optional[str] = None

    custom_caption: Optional[str] = None
    notes: Optional[str] = None

    seed: Optional[int] = Field(None, description="Reuse a seed for reproducibility")
    prompt_source: PromptSource = PromptSource.TEMPLATE
    voice_mode: Optional[VoiceMode] = Field(None, description="Brand voice mode: oracle/alpha/zen/memer")


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


# v1.3: Batch generation — N variations of the same job with offset seeds
class GenerateBatchRequest(GenerateRequest):
    """Same shape as GenerateRequest, plus variations_count.

    If `seed` is provided, the N jobs use seeds [seed, seed+1, ..., seed+N-1].
    If `seed` is None, a random base is generated server-side, then offset.
    """
    variations_count: int = Field(4, ge=1, le=8, description="Number of variations to queue")


class GenerateBatchResponse(BaseModel):
    batch_id: str
    job_count: int
    base_seed: int
    seeds: list[int]
    message: str


# ============ HeyGen v1.4 ============

class HeyGenAvatar(BaseModel):
    avatar_id: str
    name: Optional[str] = None
    gender: Optional[str] = None
    preview_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    avatar_type: str = "avatar"  # "avatar" | "talking_photo"


class HeyGenVoice(BaseModel):
    voice_id: str
    name: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    preview_audio: Optional[str] = None


class GenerateHeyGenRequest(BaseModel):
    """Generate a HeyGen avatar video from text + avatar/voice."""
    avatar_id: str = Field(..., description="HeyGen avatar_id or talking_photo_id")
    voice_id: str
    script: str = Field(..., max_length=4900)
    avatar_type: Literal["avatar", "talking_photo"] = "avatar"
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    speed: float = Field(1.0, ge=0.5, le=2.0)
    background_color: str = "#02060d"
    use_avatar_iv: bool = False
    voice_mode: Optional[VoiceMode] = None
    custom_caption: Optional[str] = None


class CompositionRequest(BaseModel):
    """Combine a Seedance generation with a HeyGen generation into one final.

    The Seedance side uses the existing GenerateRequest fields (image, template/prompt, etc.).
    The HeyGen side uses GenerateHeyGenRequest fields (avatar, voice, script).
    The layout decides how they're combined.
    """
    # Seedance side (the animation clip)
    seedance: GenerateRequest

    # HeyGen side (the avatar clip)
    heygen: GenerateHeyGenRequest

    # Composition specifics
    layout: CompositionLayout = CompositionLayout.SEQUENTIAL
    transition_duration_s: float = Field(0.4, ge=0.0, le=2.0)
    target_duration_s: Optional[int] = None
    audio_source: Literal["seedance", "heygen"] = "heygen"


class CompositionResponse(BaseModel):
    composition_id: str
    job_id: str
    message: str


# ============ v1.5 ============

class PhotoAvatarCreateResponse(BaseModel):
    """Response after creating a photo avatar from a local image."""
    photo_avatar_id: str
    group_id: str
    status: str
    avatar_name: str
    asset_url: Optional[str] = None
    message: str


class BuildScriptRequest(BaseModel):
    """Generate a HeyGen avatar script from a free-text intent."""
    intent: str = Field(..., min_length=3, max_length=2000)
    voice_mode: Optional[VoiceMode] = None
    voiceover_language: Language = Language.EN
    max_words: int = Field(60, ge=10, le=400, description="Target script length in words")
    inject_persona: bool = True


class BuildScriptResponse(BaseModel):
    script: str
    suggested_caption: str
    word_count: int
    voice_mode_applied: Optional[str] = None
    rationale: list[str] = []


class BuildCompositionRequest(BaseModel):
    """Generate BOTH a Seedance prompt and a HeyGen script from one intent.

    The two outputs are coherent: avatar speaks an intro, Seedance shows the visual.
    For split layouts: avatar reacts to what Seedance shows.
    """
    intent: str = Field(..., min_length=3, max_length=2000)
    layout: CompositionLayout = CompositionLayout.SEQUENTIAL
    style: StylePreset = StylePreset.HYBRID
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    duration_s: int = Field(5, ge=3, le=10)
    voice_mode: Optional[VoiceMode] = None
    voiceover_language: Language = Language.EN
    max_script_words: int = Field(50, ge=10, le=300)
    inject_persona: bool = True


class BuildCompositionResponse(BaseModel):
    seedance_prompt: str
    seedance_caption: str
    heygen_script: str
    coherence_rationale: str
    voice_mode_applied: Optional[str] = None


class JobDetails(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    image_filename: str
    image_filename_end: Optional[str] = None
    final_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    final_video_path: Optional[str] = None
    caption_text: Optional[str] = None
    caption_path: Optional[str] = None
    seed: Optional[int] = None
    duration_s: Optional[int] = None
    aspect_ratio: Optional[str] = None
    style: Optional[str] = None
    template_id: Optional[str] = None
    voiceover_language: Optional[str] = None
    voice_mode: Optional[str] = None
    provider: Optional[str] = None
    composition_id: Optional[str] = None
    composition_layout: Optional[str] = None
    layer_index: Optional[int] = None
    error: Optional[str] = None
    current_step: Optional[str] = None
    batch_id: Optional[str] = None
    batch_index: Optional[int] = None
    batch_size: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ImageItem(BaseModel):
    filename: str
    path: str
    size_kb: int
    width: Optional[int] = None
    height: Optional[int] = None


# ============ Prompt Builder ============

class BuildPromptRequest(BaseModel):
    """Generate a Seedance prompt from free-text keywords or raw prompt.

    The engine injects deepotus DNA (mascot, deep sea, brand) and structures
    output for Seedance 2.0 ([Subject][Action][Camera][Setting][Lighting][Style][Pacing]).
    """
    intent: str = Field(..., description="Free-text intent or keywords")
    style: StylePreset = StylePreset.HYBRID
    duration_s: int = 5
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    voiceover_language: Language = Language.EN
    inject_persona: bool = Field(True, description="Add deepotus mascot/deep-sea/brand DNA")
    preserve_user_words: bool = Field(True, description="Keep user words verbatim where possible")
    voice_mode: Optional[VoiceMode] = Field(None, description="Apply brand voice mode style hints")


class BuildPromptResponse(BaseModel):
    prompt: str
    negative_prompt: str
    suggested_caption: str
    suggested_voiceover: Optional[str] = None
    detected_camera: Optional[str] = None
    detected_lighting: Optional[str] = None
    explanation: str


# ============ v1.6: Split-Screen / Node Templates ============

class TemplateSlot(BaseModel):
    """A single fillable input declared by a template region."""
    slot_name: str
    slot_label: str
    region_id: str
    type: Literal["video_slot", "image_slot", "text_slot"]
    default_provider: Optional[str] = None
    default_text: Optional[str] = None
    max_chars: Optional[int] = None


class TemplateSlotValue(BaseModel):
    """One filled slot at render time.

    `source_kind` selects which of the optional payloads is used:
      - seedance -> generate a Seedance clip via the existing pipeline
      - heygen   -> generate a HeyGen avatar clip via the existing pipeline
      - upload   -> use an existing file under assets/images or assets/outputs
      - file     -> use an absolute path (advanced)
      - job      -> reuse the final video of a previously rendered job
      - text     -> literal text for a text_slot
    """
    source_kind: Literal["seedance", "heygen", "upload", "file", "job", "text"]
    seedance: Optional[GenerateRequest] = None
    heygen: Optional[GenerateHeyGenRequest] = None
    upload_filename: Optional[str] = None
    file_path: Optional[str] = None
    job_id: Optional[str] = None
    text: Optional[str] = None


class TemplateRenderRequest(BaseModel):
    template_id: str
    slot_values: dict[str, TemplateSlotValue]
    # Propagates to every Seedance/HeyGen sub-job that has no explicit mode.
    voice_mode: Optional[VoiceMode] = None
    # Optional inline template: render unsaved editor edits exactly as seen.
    template: Optional[dict] = None
    # Human label for the rendered job (queue / "existing" pickers).
    title: Optional[str] = Field(None, max_length=200)


class TemplateRenderResponse(BaseModel):
    template_id: str
    job_id: str
    message: str


class JobRenameRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)


class TemplateSaveRequest(BaseModel):
    """Raw template JSON; validated by TemplateEngine._validate."""
    template: dict


class TemplateSaveResponse(BaseModel):
    template_id: str
    message: str


# ============ v1.7: News / RSS pipeline ============

class AddNewsSourceRequest(BaseModel):
    url: str
    name: Optional[str] = None
    type: Literal["rss", "article"] = "rss"


class NewsSourceToggleRequest(BaseModel):
    enabled: bool


class NewsScriptItem(BaseModel):
    title: str
    summary: Optional[str] = ""
    source_name: Optional[str] = ""
    link: Optional[str] = ""


class NewsScriptRequest(BaseModel):
    items: List[NewsScriptItem] = Field(..., min_length=1)
    voice_mode: Optional[VoiceMode] = None
    language: Language = Language.EN
    max_words: int = Field(250, ge=20, le=6000)
    angle: Optional[str] = Field(None, max_length=200)
    read_articles: bool = True
    summary_words: int = Field(150, ge=40, le=2000)


class NewsEssence(BaseModel):
    title: str = ""
    essence: str = ""
    image: Optional[str] = None
    link: str = ""
    status: str = ""


class NewsScriptResponse(BaseModel):
    script: str
    suggested_caption: str
    word_count: int
    voice_mode_applied: Optional[str] = None
    rationale: List[str] = []
    sources_read: int = 0
    images: List[str] = []
    essences: List[NewsEssence] = []


class NewsIllustrationRequest(BaseModel):
    items: List[NewsScriptItem] = Field(..., min_length=1)
    per_card_s: float = Field(3.5, ge=2.0, le=12.0)
    engine: Literal["ffmpeg", "remotion"] = "ffmpeg"


class NewsIllustrationResponse(BaseModel):
    job_id: str
    message: str
