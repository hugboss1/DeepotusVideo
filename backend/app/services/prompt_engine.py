"""Seedance 2.0 prompt engine — v1.2.

New in v1.2:
- generate_from_intent(): builds a Seedance prompt from free-text keywords
- Deepotus DNA injection: ensures persona elements (mascot, deep sea, brand) are present
- Smart category detection (camera/lighting/mood from input text)
"""
import json
import random
import re
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.schemas import (
    GenerateRequest,
    PromptTemplate,
    StylePreset,
    CameraMove,
    Lighting,
    BuildPromptRequest,
    BuildPromptResponse,
    Language,
    VoiceMode,
    BuildScriptRequest,
    BuildScriptResponse,
)


PERSONAS_DIR = Path(__file__).parent.parent / "personas"


STYLE_DESCRIPTORS = {
    StylePreset.UGC_RAW: (
        "authentic UGC, shot on iPhone 15 Pro, "
        "subtle natural camera shake, slight handheld imperfection, "
        "real lighting, no post production look, raw and unfiltered"
    ),
    StylePreset.CINEMATIC: (
        "cinematic, shot on ARRI Alexa, anamorphic lens, "
        "shallow depth of field, 35mm film grain, "
        "Kodak Portra 400 color tones, professional grade"
    ),
    StylePreset.HYBRID: (
        "cinematic UGC, shot on iPhone 15 Pro Max, "
        "shallow depth of field, subtle film grain, "
        "natural color grade with slight cinematic LUT"
    ),
}

# Keyword detection dictionaries — used by the builder
CAMERA_KEYWORDS = {
    "slow push-in": ["push", "zoom in", "approach", "close in", "intimate"],
    "slow pull-out": ["pull out", "zoom out", "reveal", "back away", "dolly out"],
    "360-degree orbit": ["orbit", "rotate", "spin", "around", "circle"],
    "tracking shot": ["track", "follow", "moving", "walk with", "running with"],
    "handheld with subtle shake": ["handheld", "shaky", "vlog", "reaction", "ugc", "raw"],
    "static, locked-off": ["static", "locked", "still", "fixed"],
    "low angle dramatic": ["low angle", "looking up", "powerful", "dominant", "authority"],
    "rack focus reveal": ["rack focus", "focus shift", "blur", "reveal detail"],
    "dolly zoom (vertigo effect)": ["vertigo", "dolly zoom", "dramatic shift", "tense"],
    "whip pan transition": ["whip", "fast pan", "transition", "sweep"],
    "crane shot descending": ["crane", "descend", "from above", "drop down", "aerial down"],
}

LIGHTING_KEYWORDS = {
    "soft natural window light": ["window", "morning", "soft light", "natural", "daylight", "kitchen"],
    "golden hour rim light": ["golden", "sunset", "sunrise", "warm", "magic hour", "dawn", "dusk"],
    "neon city lights, cyan and magenta": ["neon", "cyberpunk", "cyan", "magenta", "nightlife", "city night", "synth"],
    "warm tungsten practicals": ["tungsten", "indoor", "warm bulb", "lamp", "cozy", "office"],
    "overcast diffused light": ["overcast", "cloudy", "soft diffused", "moody day", "grey"],
    "dark moody chiaroscuro": ["dark", "moody", "shadow", "chiaroscuro", "black background", "dramatic dark"],
    "bioluminescent underwater glow": ["underwater", "bioluminescent", "deep sea", "abyss", "ocean glow", "glowing"],
    "rhythmic strobe pulses": ["strobe", "club", "rave", "party", "pulse"],
}

PACING_KEYWORDS = {
    "slow": ["slow", "calm", "meditative", "zen", "intimate", "moody"],
    "medium": ["medium", "balanced", "steady"],
    "fast": ["fast", "punchy", "energetic", "chaotic", "shock", "react"],
}

# Deepotus DNA elements — pulled in by the builder when persona injection is on
DEEPOTUS_DNA = {
    "subject_flavors": [
        "with subtle bioluminescent cyan accents",
        "with a deepotus emblem visible in the scene",
        "in deepotus brand colors (cyan and violet glow)",
        "with a faint underwater shimmer overlay",
    ],
    "setting_flavors": [
        "with deep blue ambient atmosphere",
        "with subtle underwater particles drifting",
        "with a hint of deep sea aesthetic in the background",
    ],
    "default_subject": "the deepotus character (octopus mascot with bioluminescent details)",
    "default_setting": "deep blue ambient environment with cyan accent lighting",
}


def _voice_mode_block(persona: dict, mode_value: Optional[str]) -> Optional[dict]:
    """Resolve a voice mode dict from the persona JSON, or None if absent.

    Gracefully handles personas that don't have voice_modes (pre-consolidation).
    """
    if not mode_value:
        return None
    voice_modes = persona.get("voice_modes")
    if not voice_modes:
        return None
    return voice_modes.get(mode_value)


def _filter_avoid_words(persona: dict, text: str) -> str:
    """Strip forbidden vocabulary from a caption in a non-destructive way.

    Replaces avoid_completely words (case-insensitive, word-boundary) with
    blanks, then collapses double spaces. If persona has no vocabulary block,
    returns text unchanged.
    """
    vocab = persona.get("vocabulary")
    if not vocab:
        return text
    avoid = vocab.get("avoid_completely", [])
    if not avoid:
        return text
    out = text
    for word in avoid:
        if not word:
            continue
        # Word-boundary replace, case-insensitive
        out = re.sub(rf"\b{re.escape(word)}\b", "", out, flags=re.IGNORECASE)
    # Collapse double spaces and clean orphan punctuation
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([.,!?;:])", r"\1", out)
    return out.strip()


# Canonical deepotus-banned hype vocabulary (DESIGN bible / handoff). Applied
# to INGESTED news text regardless of whether the persona ships a vocabulary
# block — echoing external hype verbatim is exactly the brand risk on the
# news path. Merged with persona.vocabulary.avoid_completely when present.
_DEFAULT_NEWS_AVOID = [
    "moon", "mooning", "moonshot", "lambo", "wen", "lfg", "1000x", "100x",
    "ape", "aping", "hodl", "rekt", "ngmi", "wagmi", "gm", "fud", "shill",
    "degen", "pumpamentals", "to the moon",
]


def _scrub_news(persona: dict, text: str) -> str:
    """Destructively remove brand-banned hype tokens from external text.

    Word-boundary, case-insensitive; collapses the resulting double spaces
    and orphan punctuation. Uses the built-in list plus any persona vocab.
    """
    if not text:
        return ""
    out = text
    # Built-in list: inflection-tolerant (apes/mooning/aped/...).
    for word in _DEFAULT_NEWS_AVOID:
        out = re.sub(rf"\b{re.escape(word)}(?:s|es|ing|ed|in')?\b",
                     "", out, flags=re.IGNORECASE)
    # Persona vocab: exact word-boundary (respect their explicit config).
    vocab = persona.get("vocabulary") or {}
    for word in (w for w in vocab.get("avoid_completely", []) if w):
        out = re.sub(rf"\b{re.escape(word)}\b", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([.,!?;:])", r"\1", out)
    return out.strip()


def _detect(text: str, taxonomy: dict) -> Optional[str]:
    """Find the first taxonomy key whose keywords appear in text."""
    lower = text.lower()
    for canonical, keywords in taxonomy.items():
        for kw in keywords:
            if kw in lower:
                return canonical
    return None


def _has_persona_dna(text: str) -> bool:
    """Check if text already mentions deepotus persona elements."""
    persona_words = ["deepotus", "octopus", "tentacle", "deep sea", "abyss", "underwater",
                     "bioluminescent", "solana", "memecoin"]
    lower = text.lower()
    return any(w in lower for w in persona_words)


class PromptEngine:
    def __init__(self, persona_id: str = "deepotus"):
        self.persona_id = persona_id
        self.persona = self._load_persona(persona_id)
        self.templates: dict[str, PromptTemplate] = {
            t["id"]: PromptTemplate(**t) for t in self.persona["templates"]
        }

    @staticmethod
    def _load_persona(persona_id: str) -> dict:
        path = PERSONAS_DIR / f"{persona_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Persona file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_templates(self) -> list[PromptTemplate]:
        return list(self.templates.values())

    def get_template(self, template_id: str) -> PromptTemplate:
        if template_id not in self.templates:
            raise KeyError(f"Unknown template: {template_id}")
        return self.templates[template_id]

    # ------- Build prompt for a generation job -------

    def build_prompt(self, request: GenerateRequest) -> tuple[str, str]:
        """Build (positive, negative) prompts for Seedance 2.0."""
        if request.custom_prompt:
            base_prompt = request.custom_prompt.strip()
            # Even with custom prompt, append voice mode flavor if requested
            mode_block = _voice_mode_block(self.persona, getattr(request, "voice_mode", None) and request.voice_mode.value)
            if mode_block and mode_block.get("style_hints"):
                base_prompt = f"{base_prompt} Tone: {mode_block['style_hints']}"
            return (
                base_prompt,
                self.persona["default_negative_prompt"],
            )

        if not request.template_id:
            raise ValueError("Either template_id or custom_prompt is required")

        tpl = self.get_template(request.template_id)
        camera = request.camera.value if request.camera else tpl.camera.value
        lighting = request.lighting.value if request.lighting else tpl.lighting.value
        style_desc = STYLE_DESCRIPTORS[request.style]
        notes_addition = f"\nAdditional context: {request.notes}" if request.notes else ""

        # Voice mode injection — appends tonal direction to the prompt
        mode_value = request.voice_mode.value if request.voice_mode else None
        mode_block = _voice_mode_block(self.persona, mode_value)
        voice_addition = ""
        if mode_block and mode_block.get("style_hints"):
            voice_addition = f"\nTone direction ({mode_value}): {mode_block['style_hints']}"

        positive = (
            f"Subject: {tpl.subject_pattern}. "
            f"Action: {tpl.action}. "
            f"Camera: {camera}. "
            f"Setting: {tpl.setting}. "
            f"Lighting: {lighting}. "
            f"Style: {style_desc}. "
            f"Pacing: {tpl.pacing}, {request.duration_s} seconds."
            f"{notes_addition}"
            f"{voice_addition}"
        )

        return positive.strip(), self.persona["default_negative_prompt"].strip()

    def build_caption(self, request: GenerateRequest) -> str:
        if request.custom_caption:
            # Even with custom caption, filter forbidden vocabulary
            return _filter_avoid_words(self.persona, request.custom_caption.strip())

        if not request.template_id:
            return self._generic_caption(request.voiceover_language)

        tpl = self.get_template(request.template_id)

        if request.voiceover_language.value == "FR":
            base = tpl.caption_pattern_fr or tpl.caption_pattern_en or ""
        else:
            base = tpl.caption_pattern_en or tpl.caption_pattern_fr or ""

        # If voice_mode is set and the persona has a mode-specific example caption,
        # use that as a stronger anchor (overrides template caption).
        mode_value = request.voice_mode.value if request.voice_mode else None
        mode_block = _voice_mode_block(self.persona, mode_value)
        if mode_block:
            if request.voiceover_language.value == "FR":
                example = mode_block.get("example_caption_fr")
            else:
                example = mode_block.get("example_caption_en")
            if example:
                # Use voice-mode example as the lead, append the template's hashtags
                base = example

        tags = tpl.hashtags or self.persona.get("default_hashtags_pool", [])[:4]
        tag_line = " ".join(tags)

        if base and tag_line:
            full = f"{base}\n\n{tag_line}"
        else:
            full = base or tag_line

        return _filter_avoid_words(self.persona, full)

    def build_voiceover_script(self, request: GenerateRequest) -> Optional[str]:
        if not request.voiceover_enabled:
            return None
        if request.voiceover_script:
            return request.voiceover_script.strip()
        if not request.template_id:
            return None
        tpl = self.get_template(request.template_id)
        if request.voiceover_language.value == "FR":
            return tpl.voiceover_script_fr or tpl.voiceover_script_en
        return tpl.voiceover_script_en or tpl.voiceover_script_fr

    def _generic_caption(self, language: Language) -> str:
        tags = self.persona.get("default_hashtags_pool", [])[:4]
        tag_line = " ".join(tags)
        if language.value == "FR":
            return f"From the deep. 🐙\n\n{tag_line}"
        return f"From the deep. 🐙\n\n{tag_line}"

    # ------- Builder: generate prompt from free-text intent -------

    def generate_from_intent(self, req: BuildPromptRequest) -> BuildPromptResponse:
        """Convert free-text intent/keywords into a structured Seedance prompt
        with deepotus DNA injection.
        """
        intent = req.intent.strip()
        if not intent:
            raise ValueError("Intent cannot be empty")

        # Step 1: detect structural elements from input
        detected_camera = _detect(intent, CAMERA_KEYWORDS)
        detected_lighting = _detect(intent, LIGHTING_KEYWORDS)
        detected_pacing = _detect(intent, PACING_KEYWORDS) or "medium"

        # Step 2: pick defaults if missing
        camera = detected_camera or random.choice([
            "slow push-in", "tracking shot", "handheld with subtle shake",
        ])
        lighting = detected_lighting or random.choice([
            "neon city lights, cyan and magenta",
            "bioluminescent underwater glow",
            "dark moody chiaroscuro",
        ])

        # Step 3: build subject + action — keep user words verbatim, add DNA if missing
        subject = intent
        if req.inject_persona and not _has_persona_dna(intent):
            flavor = random.choice(DEEPOTUS_DNA["subject_flavors"])
            subject = f"{intent}, {flavor}"

        # Step 4: derive setting — try to extract from intent, else use deepotus default
        setting_match = re.search(
            r"\b(in|at|inside|on)\s+([a-z][a-z\s]{3,40}?)(?:[.,;]|$)",
            intent.lower()
        )
        if setting_match:
            setting = setting_match.group(2).strip()
            if req.inject_persona and not _has_persona_dna(setting):
                setting = f"{setting}, {random.choice(DEEPOTUS_DNA['setting_flavors'])}"
        else:
            setting = (DEEPOTUS_DNA["default_setting"] if req.inject_persona
                       else "neutral environment")

        # Step 5: action — try to detect verb phrase, else use generic motion
        action_match = re.search(
            r"\b(showing|holding|reaching|opening|closing|spinning|emerging|"
            r"falling|rising|breaking|bursting|smiling|laughing|reacting|pointing|"
            r"walking|running|sitting|standing|looking|staring|whispering)\b[^.,;]{0,80}",
            intent.lower()
        )
        action = action_match.group(0) if action_match else (
            "performing the central motion of the scene with subtle dynamic energy"
        )

        # Step 6: assemble the structured prompt
        style_desc = STYLE_DESCRIPTORS[req.style]

        # Voice mode tone injection
        mode_value = req.voice_mode.value if req.voice_mode else None
        mode_block = _voice_mode_block(self.persona, mode_value)
        voice_addition = ""
        if mode_block and mode_block.get("style_hints"):
            voice_addition = f" Tone direction ({mode_value}): {mode_block['style_hints']}"

        prompt = (
            f"Subject: {subject}. "
            f"Action: {action}. "
            f"Camera: {camera}. "
            f"Setting: {setting}. "
            f"Lighting: {lighting}. "
            f"Style: {style_desc}. "
            f"Pacing: {detected_pacing}, {req.duration_s} seconds."
            f"{voice_addition}"
        )

        # Step 7: suggested caption + voiceover
        caption = self._suggest_caption_from_intent(intent, req.voiceover_language, mode_block)
        voiceover = self._suggest_voiceover_from_intent(intent, req.voiceover_language)
        # Filter forbidden vocab on caption
        caption = _filter_avoid_words(self.persona, caption)

        explanation = self._explain_build(detected_camera, detected_lighting,
                                          detected_pacing, req.inject_persona)

        return BuildPromptResponse(
            prompt=prompt,
            negative_prompt=self.persona["default_negative_prompt"],
            suggested_caption=caption,
            suggested_voiceover=voiceover,
            detected_camera=camera,
            detected_lighting=lighting,
            explanation=explanation,
        )

    def _suggest_caption_from_intent(self, intent: str, lang: Language,
                                     mode_block: Optional[dict] = None) -> str:
        """Build a minimalistic deepotus-flavored caption around the intent.

        If a voice_mode block is provided, lean toward its example caption style.
        """
        tags = " ".join(self.persona.get("default_hashtags_pool", [])[:4])
        snippet = intent.strip().rstrip(".").split(".")[0][:80]
        if mode_block:
            # Use the example caption as inspiration for the closing line
            if lang.value == "FR":
                inspiration = mode_block.get("example_caption_fr", "")
            else:
                inspiration = mode_block.get("example_caption_en", "")
            # Take the second line of the example (first line is usually content,
            # second is the brand sign-off) to use as a closing
            if "\n" in inspiration:
                closing = inspiration.split("\n", 1)[1].strip()
            else:
                closing = inspiration
            return f"{snippet}.\n\n{closing}\n\n{tags}"
        if lang.value == "FR":
            base = f"{snippet}.\n\nDes profondeurs. 🐙"
        else:
            base = f"{snippet}.\n\nFrom the deep. 🐙"
        return f"{base}\n\n{tags}"

    def _suggest_voiceover_from_intent(self, intent: str, lang: Language) -> str:
        """Generate a short punchy voiceover line from the intent."""
        snippet = intent.strip().rstrip(".").split(".")[0]
        if len(snippet) > 80:
            snippet = snippet[:80]
        if lang.value == "FR":
            return f"{snippet}. Voila pourquoi deepotus."
        return f"{snippet}. That's why deepotus."

    # ---------- v1.5: Universal Builder extensions ----------

    def generate_script_from_intent(
        self,
        intent: str,
        *,
        voice_mode: Optional[VoiceMode] = None,
        language: Language = Language.EN,
        max_words: int = 60,
        inject_persona: bool = True,
    ) -> "BuildScriptResponse":
        """Generate a HeyGen avatar SCRIPT (spoken words) from a free-text intent.

        Different from generate_from_intent which creates VISUAL prompts.
        Output is structured to be read aloud by an avatar:
        - Hook (1 sentence) — grab attention
        - Body (1-2 sentences) — develop the idea
        - Sign-off (1 phrase) — brand close

        Applies voice_mode tone if provided, deepotus vocabulary filter,
        and the persona's example caption style as anchor.
        """
        # Import here to avoid circular references at module load time
        from app.models.schemas import BuildScriptResponse

        intent_clean = intent.strip()
        rationale: list[str] = []
        mode_value = voice_mode.value if voice_mode else None
        mode_block = _voice_mode_block(self.persona, mode_value)

        # Compute approximate sentence count from word budget (avg 12 words/sentence)
        target_sentences = max(2, min(6, max_words // 12))

        # Pull the intent's core noun phrase
        snippet = intent_clean.rstrip(".").split(".")[0]

        # Build the script structurally based on the voice mode
        if mode_block:
            rationale.append(f"voice_mode={mode_value} applied ({mode_block.get('description', '')[:60]})")
        if inject_persona:
            rationale.append("deepotus persona injected (brand cues + sign-off)")

        # Tone-specific scaffolds
        if language == Language.FR:
            scaffolds = {
                "oracle": [
                    f"Ecoute attentivement.",
                    f"{snippet}.",
                    "Les profondeurs parlent rarement. Mais quand elles parlent, on ecoute.",
                    "Deepotus.",
                ],
                "alpha": [
                    f"Pas de blabla.",
                    f"{snippet}.",
                    "Tu as une fenetre. Elle se ferme.",
                    "Deepotus. Maintenant.",
                ],
                "zen": [
                    "Respire.",
                    f"{snippet}.",
                    "Les marches montent et descendent. Ta posture ne devrait pas suivre.",
                    "Deepotus. Patience.",
                ],
                "memer": [
                    f"POV: {snippet[:60]}.",
                    "T'es la, je suis la.",
                    "On va pas faire semblant.",
                    "Deepotus.",
                ],
            }
            default = [
                f"{snippet}.",
                "C'est ce qu'il y a en dessous qui compte.",
                "Deepotus. Des profondeurs.",
            ]
        else:
            scaffolds = {
                "oracle": [
                    "Listen carefully.",
                    f"{snippet}.",
                    "The deep rarely speaks. But when it does, you listen.",
                    "Deepotus.",
                ],
                "alpha": [
                    "Cut the noise.",
                    f"{snippet}.",
                    "You have a window. It's closing.",
                    "Deepotus. Now.",
                ],
                "zen": [
                    "Breathe.",
                    f"{snippet}.",
                    "Markets rise and fall. Your posture shouldn't follow them.",
                    "Deepotus. Patience.",
                ],
                "memer": [
                    f"POV: {snippet[:60]}.",
                    "You see it. I see it.",
                    "Let's not pretend.",
                    "Deepotus.",
                ],
            }
            default = [
                f"{snippet}.",
                "What matters is underneath.",
                "Deepotus. From the deep.",
            ]

        if mode_value and mode_value in scaffolds:
            parts = scaffolds[mode_value]
        else:
            parts = default
            rationale.append("used default tone scaffold (no voice_mode set)")

        # Cap to target sentences
        script = " ".join(parts[:target_sentences + 1])
        # Filter vocabulary
        script = _filter_avoid_words(self.persona, script)
        rationale.append("vocabulary filter applied (avoid_completely from persona)")

        # v1.15.1 — honest AI: when an LLM key is configured, polish the
        # deterministic draft into genuinely-written copy (brand voice kept),
        # then re-apply the vocabulary filter. Falls back to the draft.
        try:
            from app.services import summarizer as _sum
            _polished, _prov = _sum.rewrite_script(
                script,
                voice_desc=(mode_block.get("description", "")
                            if mode_block else ""),
                language=("FR" if language == Language.FR else "EN"),
                max_words=max_words,
            )
            if _polished:
                script = _filter_avoid_words(self.persona, _polished)
                rationale.append(f"LLM-polished via {_prov}")
            else:
                rationale.append("deterministic draft (no LLM key)")
        except Exception:
            rationale.append("deterministic draft (LLM rewrite skipped)")

        # Caption: short version of the script + hashtags
        tags = " ".join(self.persona.get("default_hashtags_pool", [])[:4])
        first_line = snippet[:80]
        if mode_block:
            ex = mode_block.get(
                f"example_caption_{'fr' if language == Language.FR else 'en'}",
                "",
            )
            closing = ex.split("\n", 1)[1].strip() if "\n" in ex else ex
            caption = f"{first_line}.\n\n{closing}\n\n{tags}"
        else:
            sign = "Des profondeurs. 🐙" if language == Language.FR else "From the deep. 🐙"
            caption = f"{first_line}.\n\n{sign}\n\n{tags}"
        caption = _filter_avoid_words(self.persona, caption)

        word_count = len(script.split())
        return BuildScriptResponse(
            script=script,
            suggested_caption=caption,
            word_count=word_count,
            voice_mode_applied=mode_value,
            rationale=rationale,
        )

    def generate_news_script(
        self,
        items: list,
        *,
        voice_mode: Optional[VoiceMode] = None,
        language: Language = Language.EN,
        max_words: int = 90,
        angle: Optional[str] = None,
    ) -> "BuildScriptResponse":
        """Turn selected news items into a deepotus-voice spoken script.

        Deterministic + persona-driven (no LLM, like the rest of the engine):
        voice-mode hook -> optional angle framing -> one concise line per
        headline -> brand sign-off. Vocabulary filter + FR/EN handled. The
        script is trimmed to `max_words` by dropping trailing headlines (hook
        and sign-off are always kept) so the avatar read stays on-budget.
        FR strings are intentionally accent-free, matching this engine's
        existing convention (TTS / encoding safety).
        """
        from app.models.schemas import BuildScriptResponse

        def _g(it, key, default=""):
            if isinstance(it, dict):
                return (it.get(key) or default)
            return getattr(it, key, default) or default

        mode_value = voice_mode.value if voice_mode else None
        mode_block = _voice_mode_block(self.persona, mode_value)
        is_fr = language == Language.FR
        rationale: list[str] = []

        if is_fr:
            hooks = {
                "oracle": "Les profondeurs observaient.",
                "alpha": "Point signal. Zero bruit.",
                "zen": "Respire. Puis regarde.",
                "memer": "Bon, revue de presse, version deepotus.",
                "prophet": "Les profondeurs ont deja vu ce film. Ca finit "
                           "rarement bien.",
            }
            default_hook = hooks["prophet"]
            signoffs = {
                "oracle": "Le courant decide. Deepotus.",
                "alpha": "Agis en consequence. Deepotus.",
                "zen": "Reste stable. Deepotus.",
                "memer": "Voila le lore. Deepotus.",
                "prophet": "Restez liquides, restez sceptiques. Deepotus.",
            }
            default_sign = signoffs["prophet"]
            conns = ["Apparemment,", "Comme par hasard,",
                     "Au programme du cirque,", "Sans surprise,",
                     "Accrochez-vous,"]
            angle_tpl = "Lecture deepotus : {a}."
        else:
            hooks = {
                "oracle": "The deep has been watching.",
                "alpha": "Signal check. No noise.",
                "zen": "Breathe. Then look.",
                "memer": "Okay, news dump, deepotus style.",
                "prophet": "The deep has seen this script before. It "
                           "rarely ends well.",
            }
            default_hook = hooks["prophet"]
            signoffs = {
                "oracle": "The current decides. Deepotus.",
                "alpha": "Move accordingly. Deepotus.",
                "zen": "Stay steady. Deepotus.",
                "memer": "That's the lore. Deepotus.",
                "prophet": "Stay liquid, stay skeptical. Deepotus.",
            }
            default_sign = signoffs["prophet"]
            conns = ["Apparently,", "Somehow,", "In today's circus,",
                     "Predictably,", "Brace yourselves,"]
            angle_tpl = "The deepotus read: {a}."

        # News default voice = the deepotus "prophet" (cynical + dry-witty).
        # An explicit voice_mode still overrides hook/sign-off; the cynical
        # connectors stay (that IS the deepotus news character).
        tone = mode_value if mode_value else "prophet"
        hook = hooks.get(tone, default_hook)
        signoff = signoffs.get(tone, default_sign)
        rationale.append(
            f"tone={tone}"
            + (f" ({mode_block.get('description','')[:40]})"
               if mode_block else " (cynical/humorous prophet)"))

        def _condense(text: str, limit: int = 28) -> str:
            t = " ".join((text or "").split())
            for sep in (" - ", " | ", " — "):
                if sep in t and len(t.split(sep)[-1]) <= 30:
                    t = sep.join(t.split(sep)[:-1])
            words = t.split()
            if len(words) > limit:
                t = " ".join(words[:limit])
            t = _scrub_news(self.persona, t)
            return t.rstrip(".,;:")

        segs: list[str] = [hook]
        n_angle = 0
        if angle and angle.strip():
            segs.append(angle_tpl.format(a=angle.strip().rstrip(".")))
            n_angle = 1
            rationale.append("angle framing injected")
        used = 0
        for i, it in enumerate(items):
            # Prefer the article "essence" (real content summary) over the
            # bare headline when the article was read.
            # Use the FULL summary essence (no per-line truncation) so the
            # prophet script tracks the summary length the user asked for.
            raw = (_g(it, "essence") or _g(it, "summary")
                   or _g(it, "title"))
            body = _scrub_news(
                self.persona, " ".join(raw.split())).rstrip(".,;:")
            if not body:
                continue
            segs.append(f"{conns[i % len(conns)]} {body}.")
            used += 1
        segs.append(signoff)

        # Trim to budget: drop trailing headlines, keep hook(+angle) & signoff
        floor = 1 + n_angle  # indices [0..floor-1] are hook/angle, [-1] signoff
        while (len(" ".join(segs).split()) > max_words
               and len(segs) > floor + 2):
            del segs[-2]
        kept = len(segs) - floor - 1
        rationale.append(f"{kept}/{used} headlines kept within {max_words} words")

        script = _scrub_news(
            self.persona, _filter_avoid_words(self.persona, " ".join(segs)))
        rationale.append("brand scrub + vocabulary filter applied")

        # v1.15.1 — honest AI: LLM-polish the prophet draft when a key exists,
        # then re-apply the brand scrub + vocabulary filter. Deterministic
        # fallback on no-key / any error.
        try:
            from app.services import summarizer as _sum
            _polished, _prov = _sum.rewrite_script(
                script,
                voice_desc=(mode_block.get("description", "") if mode_block
                            else "cynical, dry-witty deep-sea prophet"),
                language=("FR" if is_fr else "EN"),
                max_words=max_words,
            )
            if _polished:
                script = _scrub_news(
                    self.persona,
                    _filter_avoid_words(self.persona, _polished))
                rationale.append(f"LLM-polished via {_prov}")
            else:
                rationale.append("deterministic draft (no LLM key)")
        except Exception:
            rationale.append("deterministic draft (LLM rewrite skipped)")

        tags = " ".join(self.persona.get("default_hashtags_pool", [])[:4])
        lead = _condense(_g(items[0], "title"))[:90] if items else "Deepotus"
        if mode_block:
            ex = mode_block.get(
                f"example_caption_{'fr' if is_fr else 'en'}", "")
            closing = ex.split("\n", 1)[1].strip() if "\n" in ex else ex
        else:
            closing = ("Des profondeurs. 🐙" if is_fr
                       else "From the deep. 🐙")
        caption = _filter_avoid_words(
            self.persona, f"{lead}.\n\n{closing}\n\n{tags}")

        return BuildScriptResponse(
            script=script,
            suggested_caption=caption,
            word_count=len(script.split()),
            voice_mode_applied=mode_value,
            rationale=rationale,
        )

    def generate_composition_from_intent(
        self,
        intent: str,
        *,
        layout,  # CompositionLayout
        style: StylePreset = StylePreset.HYBRID,
        aspect_ratio = None,  # AspectRatio
        duration_s: int = 5,
        voice_mode: Optional[VoiceMode] = None,
        language: Language = Language.EN,
        max_script_words: int = 50,
        inject_persona: bool = True,
    ):
        """From ONE intent, generate BOTH a Seedance prompt AND a HeyGen script
        that are coherent with each other.

        Layout determines coherence pattern:
        - SEQUENTIAL: avatar introduces topic, then Seedance shows visual payoff
        - SPLIT_VSTACK / SPLIT_HSTACK: avatar reacts to / narrates what Seedance shows

        Returns BuildCompositionResponse (imported lazily).
        """
        from app.models.schemas import (
            BuildCompositionResponse,
            BuildPromptRequest,
            CompositionLayout,
            AspectRatio,
        )

        if aspect_ratio is None:
            aspect_ratio = AspectRatio.VERTICAL

        # 1. Generate the Seedance side using existing builder logic
        seedance_req = BuildPromptRequest(
            intent=intent,
            style=style,
            duration_s=duration_s,
            aspect_ratio=aspect_ratio,
            voiceover_language=language,
            inject_persona=inject_persona,
            voice_mode=voice_mode,
        )
        seedance_out = self.generate_from_intent(seedance_req)

        # 2. Generate the HeyGen script side
        # Adapt the script to the layout:
        # - sequential: avatar SETS UP the visual that follows ("Watch what happens.")
        # - split: avatar NARRATES alongside the visual ("Here's what you're seeing.")
        if layout == CompositionLayout.SEQUENTIAL:
            framed_intent = f"Setup phrase introducing: {intent}"
            rationale_layout = (
                "Sequential layout: avatar script SETS UP the visual that follows. "
                "Script ends on a transition cue ('Watch.', 'Now.', 'Look.')."
            )
        else:
            framed_intent = f"Narration of: {intent}"
            rationale_layout = (
                "Split-screen layout: avatar NARRATES what Seedance is showing simultaneously. "
                "Script and visual happen in parallel."
            )

        script_out = self.generate_script_from_intent(
            intent=framed_intent,
            voice_mode=voice_mode,
            language=language,
            max_words=max_script_words,
            inject_persona=inject_persona,
        )

        # For sequential, append a transition cue if not already present
        if layout == CompositionLayout.SEQUENTIAL:
            cue_en = "Watch."
            cue_fr = "Regarde."
            cue = cue_fr if language == Language.FR else cue_en
            if cue.lower() not in script_out.script.lower():
                script_out.script = script_out.script.rstrip(".") + f". {cue}"

        return BuildCompositionResponse(
            seedance_prompt=seedance_out.prompt,
            seedance_caption=seedance_out.suggested_caption,
            heygen_script=script_out.script,
            coherence_rationale=rationale_layout,
            voice_mode_applied=(voice_mode.value if voice_mode else None),
        )

    @staticmethod
    def _explain_build(camera: Optional[str], lighting: Optional[str],
                       pacing: str, inject: bool) -> str:
        bits = []
        if camera:
            bits.append(f"detected camera move from your text ({camera})")
        else:
            bits.append("picked a camera move (no hint detected)")
        if lighting:
            bits.append(f"detected lighting ({lighting})")
        else:
            bits.append("picked default cinematic lighting")
        bits.append(f"pacing inferred: {pacing}")
        if inject:
            bits.append("deepotus DNA injected (mascot/deep-sea/brand cues)")
        return ". ".join(bits) + "."
