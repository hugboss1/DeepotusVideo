"""Cost / pricing model for the Cost Widget (v1.15.1).

Gives the Scheduler/Quick/Studio a *preview budget* before any spend, and the
top-bar widget a per-provider usage + monetary picture. Prices are DIRECTIONAL
estimates (each provider bills you directly, BYO keys) and are user-editable via
pricing.json in the data dir / the Settings panel.

Live remaining balances are only available for providers that expose them
(HeyGen credits, ElevenLabs characters); fal.ai and the LLMs are pay-as-you-go,
so for those the widget shows cumulative *estimated* spend + the preview.
"""
import json
from pathlib import Path

from app.config import DATA_ROOT

_PRICING_FILE = DATA_ROOT / "pricing.json"

# Directional defaults (USD). Editable in Settings -> Pricing & budget.
DEFAULTS = {
    "flux_image_usd": 0.003,          # fal.ai FLUX schnell, per image
    "gpt_image_2_usd": 0.12,          # OpenAI gpt-image-2, per image (portrait, directional)
    "gpt_image_1_usd": 0.06,          # OpenAI gpt-image-1, per image
    "gpt_image_1_mini_usd": 0.015,    # OpenAI gpt-image-1-mini, per image
    "seedance_usd_per_s": 0.04,       # fal.ai Seedance, per second of video
    "heygen_credits_per_min": 6.0,    # HeyGen avatar credits per minute
    "heygen_credit_usd": 0.04,        # $ value of one HeyGen credit
    "heygen_chars_per_min": 850.0,    # ~speaking rate to map a script to minutes
    "elevenlabs_usd_per_char": 0.00024,
    # LLM $ per 1M tokens (input/output) — used for plan/script estimates
    "llm_usd_per_mtok": {
        "anthropic": {"in": 0.80, "out": 4.00},
        "openai":    {"in": 0.15, "out": 0.60},
        "gemini":    {"in": 0.075, "out": 0.30},
    },
    "monthly_budget_usd": 0.0,        # 0 = no cap
}

# image-gen model id -> (label, billing provider, pricing key in DEFAULTS)
_IMAGE_MODELS = {
    "flux":             ("FLUX image",       "fal",    "flux_image_usd"),
    "gpt-image-2":      ("GPT Image 2",      "openai", "gpt_image_2_usd"),
    "gpt-image-1":      ("GPT Image 1",      "openai", "gpt_image_1_usd"),
    "gpt-image-1-mini": ("GPT Image 1 mini", "openai", "gpt_image_1_mini_usd"),
}


def load() -> dict:
    """Defaults merged with the user's pricing.json overrides (if any)."""
    data = dict(DEFAULTS)
    try:
        if _PRICING_FILE.is_file():
            override = json.loads(_PRICING_FILE.read_text(encoding="utf-8"))
            if isinstance(override, dict):
                for k, v in override.items():
                    data[k] = v
    except Exception:
        pass
    return data


def save(d: dict) -> dict:
    """Persist only known keys; returns the merged effective pricing."""
    clean = {k: d[k] for k in DEFAULTS if k in d}
    try:
        _PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PRICING_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception:
        pass
    return load()


def _line(provider, label, units, unit, usd):
    return {"provider": provider, "label": label,
            "units": round(units, 2), "unit": unit, "usd": round(usd, 4)}


def estimate(op: dict, p: dict | None = None) -> dict:
    """Estimate the cost of an operation.

    op kinds:
      {"kind":"image"}                          -> 1 FLUX image
      {"kind":"seedance","duration_s":10}
      {"kind":"heygen","chars":300}             -> avatar minutes from char count
      {"kind":"elevenlabs","chars":500}
      {"kind":"episode","images":6,"chars":4200}  -> N illustrations + narration
      {"kind":"llm","provider":"openai","in_tok":1500,"out_tok":500}
      {"kind":"composition","parts":[op,...]}
      {"kind":"news_reel","items":3,"per_card_s":3.5}
      {"kind":"marketing_plan","posts":7,"per_post":[op,...]}
      {"kind":"campaign","ops":[op,...]}
    Returns {breakdown:[line...], total_usd, credits:{provider:n}}.
    """
    p = p or load()
    kind = (op or {}).get("kind", "")
    lines = []

    if kind == "image":
        n = int(op.get("n", 1))
        model = str(op.get("model") or "flux").lower()
        label, prov, key = _IMAGE_MODELS.get(model, _IMAGE_MODELS["flux"])
        unit = p.get(key, p["flux_image_usd"])
        lines.append(_line(prov, f"{label} x{n}", n, "image", n * unit))
    elif kind == "seedance":
        n = int(op.get("n", 1))
        dur = float(op.get("duration_s", 10)) * n
        lines.append(_line("fal", "Seedance video", dur, "s",
                           dur * p["seedance_usd_per_s"]))
    elif kind == "heygen":
        chars = float(op.get("chars", 0))
        mins = max(0.1, chars / max(1.0, p["heygen_chars_per_min"])) if chars \
            else float(op.get("minutes", 1.0))
        credits = mins * p["heygen_credits_per_min"]
        lines.append(_line("heygen", "HeyGen avatar", credits, "credits",
                           credits * p["heygen_credit_usd"]))
    elif kind == "elevenlabs":
        chars = float(op.get("chars", 0))
        lines.append(_line("elevenlabs", "Voiceover", chars, "chars",
                           chars * p["elevenlabs_usd_per_char"]))
    elif kind == "episode":
        # Narrated illustrated episode: N illustrations + the ElevenLabs
        # narration. Ken Burns / still motion is local ffmpeg (free); only
        # add Seedance if real animated scenes are billed (seedance_s).
        imgs = int(op.get("images", op.get("scenes", 1)))
        chars = float(op.get("chars", 0))
        model = str(op.get("model") or "flux").lower()
        ilabel, iprov, ikey = _IMAGE_MODELS.get(model, _IMAGE_MODELS["flux"])
        iunit = p.get(ikey, p["flux_image_usd"])
        if imgs:
            lines.append(_line(iprov, f"{ilabel} x{imgs}", imgs, "image",
                               imgs * iunit))
        if chars:
            lines.append(_line("elevenlabs", "Narration", chars, "chars",
                               chars * p["elevenlabs_usd_per_char"]))
        sd = float(op.get("seedance_s", 0))
        if sd:
            lines.append(_line("fal", "Seedance video", sd, "s",
                               sd * p["seedance_usd_per_s"]))
    elif kind == "llm":
        prov = op.get("provider", "openai")
        rates = p["llm_usd_per_mtok"].get(prov, p["llm_usd_per_mtok"]["openai"])
        it = float(op.get("in_tok", 1000)); ot = float(op.get("out_tok", 400))
        usd = it / 1e6 * rates["in"] + ot / 1e6 * rates["out"]
        lines.append(_line(prov, "LLM tokens", it + ot, "tok", usd))
    elif kind in ("composition", "campaign"):
        for sub in op.get("parts") or op.get("ops") or []:
            lines.extend(estimate(sub, p)["breakdown"])
    elif kind == "news_reel":
        items = int(op.get("items", 1))
        per = float(op.get("per_card_s", 3.5))
        dur = items * per
        lines.append(_line("fal", "News reel (ffmpeg)", dur, "s", 0.0))  # local ffmpeg = free
        # the cards usually reuse fetched images; add nothing unless generating
    elif kind == "marketing_plan":
        posts = int(op.get("posts", 1))
        _img = {"kind": "image"}
        if op.get("model"):
            _img["model"] = op["model"]
        per_post = op.get("per_post") or [_img, {"kind": "seedance", "duration_s": 10}]
        for _ in range(posts):
            for sub in per_post:
                lines.extend(estimate(sub, p)["breakdown"])

    # aggregate
    total = round(sum(l["usd"] for l in lines), 4)
    credits = {}
    for l in lines:
        if l["unit"] == "credits":
            credits[l["provider"]] = round(credits.get(l["provider"], 0) + l["units"], 2)
    return {"breakdown": lines, "total_usd": total, "credits": credits}
