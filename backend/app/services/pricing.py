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
import math
from pathlib import Path

from app.config import DATA_ROOT

_PRICING_FILE = DATA_ROOT / "pricing.json"

# Directional defaults (USD). Editable in Settings -> Pricing & budget.
DEFAULTS = {
    "flux_image_usd": 0.003,          # fal.ai FLUX schnell, per image
    # fal.ai nano-banana (Gemini), per image — text-to-image AND /edit share
    # the same rate. Re-verified 2026-08-24 on fal.ai/models/fal-ai/nano-banana:
    # "Your request will cost $0.039 per image. For $1.00, you can run this
    # model 25 times." Untabulated until then, which made `estimate` fall back
    # to the FLUX rate (0.003) for it — a price 13x too low, served as if it
    # were the model's own.
    "nano_banana_usd": 0.039,
    # fal.ai nano-banana-pro (Gemini 3 Pro Image), per image at 1K/2K.
    # Re-verified 2026-08-27 on fal.ai/models/fal-ai/nano-banana-pro: "Your
    # request will cost $0.15 per image. For $1.00, you can run this model
    # 7 times." 4K outputs are charged double — the série never asks for 4K.
    "nano_banana_pro_usd": 0.15,
    "gpt_image_2_usd": 0.12,          # OpenAI gpt-image-2, per image (portrait, directional)
    # GPT Image 2 servi PAR fal (endpoint openai/gpt-image-2, facturé fal —
    # pas de clé OpenAI sur ce chemin). Tarif du 27/08/2026, table fal par
    # taille × qualité : 0,145 $ l'image en qualité `high` (le défaut, que
    # la requête épingle) au format 768×1024 (`portrait_4_3`). La voie
    # OpenAI directe garde SA clé de prix ci-dessus : deux chemins de
    # facturation, deux entrées — un seul chiffre pour les deux mentirait
    # sur l'une des deux factures.
    "gpt_image_2_fal_usd": 0.145,
    # GPT Image 2.5 Flare / Sunburst (doc OpenAI et fal lue le 27/09/2026).
    # Qualité `high` ÉCRITE sur les deux voies (le défaut fal) : table fal
    # 1024² high = 0,05268 $ l'image, tarif token OpenAI identique à GPT
    # Image 2. Un prix fixe par image, quatre clés (deux voies × deux
    # variantes) : écart daté, ni la qualité ni la taille ne modulent le
    # devis (1024×1536 high vaut 0,04116 chez fal).
    "gpt_image_25_flare_usd": 0.053,
    "gpt_image_25_sunburst_usd": 0.053,
    "gpt_image_25_flare_fal_usd": 0.053,
    "gpt_image_25_sunburst_fal_usd": 0.053,
    "gpt_image_1_usd": 0.06,         # OpenAI gpt-image-1, per image
    "gpt_image_1_mini_usd": 0.015,    # OpenAI gpt-image-1-mini, per image
    # Ancien tarif forfaitaire Seedance (avant le registre W-a). Il ne sert
    # plus qu'au coût HISTORIQUE des jobs d'avant la colonne `video_model`
    # (op `legacy: True`) : un modèle vide se résout au défaut du registre.
    "seedance_usd_per_s": 0.04,
    # Avatar live G0 (t161, 10/10/2026) : Decart Lucy 2.5 en temps réel, à la seconde de génération active.
    # Relevé le 10/10 sur docs.platform.decart.ai/getting-started/pricing : 0,02 $/s (720p), 0,04 $/s en
    # mode rapide (x2). Via fal (decart/lucy-2-5/realtime) le tarif relevé est 0,04 $/s — chemin non retenu.
    "decart_realtime_usd_per_s": 0.02,
    # Garde de coût serveur (retours-ia F3/F4, 27/09) : une requête vidéo
    # (/generate, /generate/batch, /generate/composition, rendu de layout)
    # dont l'estimation dépasse ce plafond est refusée en 402 AVANT toute
    # génération ; 0 = pas de plafond. `video_max_gen_s` plafonne la durée
    # GÉNÉRÉE (facturée) ; au-delà, ffmpeg prolonge comme avant.
    "video_max_usd_per_request": 10.0,
    "video_max_gen_s": 10,
    # W-a (v1.19) — per-model $ / second of video, audio OFF where the model
    # has a switch (the pipeline always turns it off; Veo-google audio is
    # baked in and priced flat). Keys mirror fal_service.VIDEO_MODELS; "*"
    # = flat whatever the resolution. Frozen 22/07/2026 from the fal catalog
    # pricing strings; Google-native rates are directional estimates.
    "video_usd_per_s": {
        "seedance-v1-pro":     {"720p": 0.054, "1080p": 0.124},
        "seedance-2":          {"720p": 0.3034, "1080p": 0.682},
        "seedance-2-fast":     {"720p": 0.2419},
        # fal.ai bytedance/seedance-2.5, relu 2026-08-28 : facturation aux
        # tokens (0,0214 $/1k), soit ~0,2205 $/s en 480p et ~0,4730 $/s en
        # 720p (cas 16:9) — 1080p accepté mais non chiffré par fal, donc
        # absent ici ET du registre (voir fal_service.VIDEO_MODELS). Même
        # prix avec ou sans audio (doc fal du 26/09) : pas de colonne
        # « audio off » pour ce modèle.
        "seedance-2.5":        {"480p": 0.2205, "720p": 0.473},
        "kling-v3-pro":        {"*": 0.112},
        "kling-v3-standard":   {"*": 0.084},
        "pixverse-v6":         {"720p": 0.045, "1080p": 0.090},
        "veo-3.1-fast-fal":    {"*": 0.10},
        "veo-3.1-google":      {"*": 0.40},
        "veo-3.1-fast-google": {"*": 0.15},
        "veo-3.1-lite-google": {"*": 0.10},
    },
    "rembg_api_usd": 0.003,           # fal.ai imageutils/rembg, per image (sprite frames)
    "seedream_edit_usd": 0.03,        # fal.ai bytedance/seedream/v4/edit, par vue (T104, plan-moteurs-3d T1)
    "meshy_credit_usd": 0.02,         # valeur $ directionnelle d'un crédit Meshy
                                      # (~plan Pro 1000 cr/mois) ; éditable comme
                                      # le reste — Meshy facture en crédits, la
                                      # vérité comptable est consumed_credits
    "heygen_credits_per_min": 6.0,    # HeyGen avatar credits per minute
    "heygen_credit_usd": 0.04,        # $ value of one HeyGen credit
    "heygen_chars_per_min": 850.0,    # ~speaking rate to map a script to minutes
    "elevenlabs_usd_per_char": 0.00024,
    # Tâche #16 (29/09/2026) : les dépenses que la grille ne savait pas chiffrer (garde des plafonds mensuels).
    # MESURÉ : l'avatar photo HeyGen coûte 1,32 $ (migration HeyGen v3, 28/09). DIRECTIONNELS, À VÉRIFIER
    # (de mémoire, éditables dans Tarifs) : SFX ElevenLabs en crédits (≈ caractères) — 40 par seconde
    # demandée, 200 quand le modèle choisit la durée ; l'upscale fal esrgan par image ; une tâche Meshy
    # générique (proxy) à 20 crédits quand l'endpoint ne dit pas mieux.
    "heygen_photo_avatar_usd": 1.32,
    "elevenlabs_sfx_credits_per_s": 40.0,
    "elevenlabs_sfx_credits_auto": 200.0,
    "esrgan_usd": 0.002,
    "meshy_task_credits_defaut": 20.0,
    # W-b (v1.20) — multiplicateur de tarif par modèle TTS ElevenLabs,
    # appliqué à elevenlabs_usd_per_char (flash v2.5 = −50 %, docs 22/07/2026).
    # Keys mirror elevenlabs_service.ELEVEN_MODELS.
    "elevenlabs_model_mult": {
        "eleven_multilingual_v2": 1.0,
        "eleven_v3": 1.0,
        "eleven_flash_v2_5": 0.5,
    },
    # Sous-titres — transcription (piste s1). $/minute d'audio, par
    # fournisseur À HORODATAGE AU MOT (cf. transcribe_service.STT_PROVIDERS).
    # Le calage d'un texte DÉJÀ connu (narration écrite dans le Montage) est
    # local et gratuit : il n'apparaît pas ici, par construction.
    # Plan Quick T2 (tâche #51, 01/10/2026) — extension générative ($/s AJOUTÉE), relevée sur fal.ai le 01/10 ;
    # miroir de fal_video_tools.EXTEND_MODELS[...]["usd_per_s"].
    "extend_usd_per_s": {
        "veo-3.1-fast-extend": {"son": 0.15, "muet": 0.10},
        "veo-3.1-extend": {"son": 0.40, "muet": 0.20},
    },
    # Plan Quick T5 (tâche #52) — lip-sync Kling : $/s de VIDÉO d'entrée, au palier de 5 s (relevé fal.ai le 01/10).
    "lipsync_usd_per_s": {"kling-lipsync": 0.014},
    # Son & VFX (plan 03/09, T099 le 06/10). Demucs : page fal relue le 03/09, « $0.0007 per second ». BiRefNet
    # vidéo : la page affiche « $0 per compute second » — chiffre non crédible, gardé à 0 et LIBELLÉ « à mesurer »
    # tant qu'un premier tir n'a pas été lu sur le tableau de bord fal. Isolation ElevenLabs : 1 000 caractères
    # par minute d'audio. (ACE-Step et MiniMax Music 2.0 entreront au registre MUSIC_MODELS avec leur tâche.)
    "demucs_usd_per_s": 0.0007,
    "birefnet_video_usd_per_s": 0.0,
    "birefnet_image_usd": 0.0,        # t168d : BiRefNet image (fal-ai/birefnet/v2) — fal n'affiche que $0 : à mesurer
    "elevenlabs_isolation_chars_per_min": 1000.0,
    # Avatar live G2 (t163, 10/10/2026) : Voice Changer (voix -> voix), ~1 000 crédits par minute (relevé tiers
    # du 07/2026 sur la liste officielle, même grille que l'isolation) — à confirmer sur elevenlabs.io/pricing.
    "elevenlabs_sts_chars_per_min": 1000.0,
    "stt_usd_per_min": {
        "elevenlabs": 0.0067,   # Scribe v1, ≈ 0,40 $/h
        "openai": 0.006,        # whisper-1
    },
    # Tâche #82 PR C (04/10/2026) — modèles VISION des légendes de la Bibliothèque, $ / M jetons, relevé du 04/10 sur
    # ai.google.dev/gemini-api/docs/pricing (palier payant, standard). Une image <= 384 px = 258 jetons.
    "vision_usd_per_mtok": {
        "gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40},
        "gemini-2.5-flash":      {"in": 0.30, "out": 2.50},
    },
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
    # id + label mirror routes.list_image_models so the Cardforge screens can
    # join the two tables on the id alone.
    "nano-banana":      ("Nano Banana (Gemini)", "fal", "nano_banana_usd"),
    "nano-banana-pro":  ("Nano Banana Pro (Gemini 3)", "fal",
                         "nano_banana_pro_usd"),
    "gpt-image-2":      ("GPT Image 2",      "openai", "gpt_image_2_usd"),
    "gpt-image-2-fal":  ("GPT Image 2 (via fal)", "fal",
                         "gpt_image_2_fal_usd"),
    "gpt-image-2.5-flare":        ("GPT Image 2.5 Flare (OpenAI)", "openai",
                                   "gpt_image_25_flare_usd"),
    "gpt-image-2.5-sunburst":     ("GPT Image 2.5 Sunburst (OpenAI)", "openai",
                                   "gpt_image_25_sunburst_usd"),
    "gpt-image-2.5-flare-fal":    ("GPT Image 2.5 Flare (via fal)", "fal",
                                   "gpt_image_25_flare_fal_usd"),
    "gpt-image-2.5-sunburst-fal": ("GPT Image 2.5 Sunburst (via fal)", "fal",
                                   "gpt_image_25_sunburst_fal_usd"),
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
    """Persist only known keys; returns the merged effective pricing.

    P1 #9 (28/09/2026) : les clés reçues sont FUSIONNÉES dans les surcharges
    existantes — l'écran Tarifs n'envoie que ses champs, et remplacer le
    fichier effaçait tout le reste (tarifs vidéo par modèle, plafonds posés à
    la main). Un fichier illisible ou qui n'est pas un objet repart de vide."""
    clean = {k: d[k] for k in DEFAULTS if k in d}
    try:
        cur = json.loads(_PRICING_FILE.read_text(encoding="utf-8")) if _PRICING_FILE.is_file() else {}
    except Exception:
        cur = {}
    if not isinstance(cur, dict):
        cur = {}
    clean = {**cur, **clean}
    try:
        _PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PRICING_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception:
        pass
    return load()


def _line(provider, label, units, unit, usd):
    return {"provider": provider, "label": label,
            "units": round(units, 2), "unit": unit, "usd": round(usd, 4)}


def no_spend(label: str, provider: str = "local") -> dict:
    """Un devis de ZERO qui SE DIT — même forme de retour qu'`estimate`.

    Sert les deux cas où un job ne doit rien facturer : l'opération est
    locale (ffmpeg/PIL, un fichier téléversé, un job parent dont les
    sous-jobs paient déjà), ou son provider n'est PAS TARIFÉ et l'aveu vaut
    mieux qu'un chiffre inventé. La ligne reste dans le `breakdown` — donc
    dans `by_provider` — précisément pour que le blanc porte un nom.
    """
    return {"breakdown": [_line(provider, label, 1, "job", 0.0)],
            "total_usd": 0.0, "credits": {}}


def video_rate(model_id: str, resolution: str = "1080p",
               p: dict | None = None) -> float | None:
    """W-a — $/s for a video model at a resolution, honoring pricing.json
    overrides. None for unknown models (caller falls back to legacy)."""
    p = p or load()
    table = p.get("video_usd_per_s") or {}
    rates = table.get(model_id)
    if not isinstance(rates, dict) or not rates:
        return None
    v = rates.get(resolution)
    if v is None:
        v = rates.get("*")
    if v is None:  # e.g. 1080p asked of a 720p-only model — price its max
        v = max(rates.values())
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def elevenlabs_mult(model_id: str | None, p: dict | None = None) -> float:
    """W-b — multiplicateur de coût du modèle TTS (1.0 si inconnu/None),
    pricing.json honoré."""
    p = p or load()
    mults = p.get("elevenlabs_model_mult") or {}
    try:
        return float(mults.get(model_id or "", 1.0))
    except (TypeError, ValueError):
        return 1.0


def elevenlabs_rate(model_id: str | None = None, p: dict | None = None) -> float:
    """W-b — $/caractère effectif d'un modèle TTS (base × multiplicateur)."""
    p = p or load()
    try:
        base = float(p.get("elevenlabs_usd_per_char",
                           DEFAULTS["elevenlabs_usd_per_char"]))
    except (TypeError, ValueError):
        base = DEFAULTS["elevenlabs_usd_per_char"]
    return base * elevenlabs_mult(model_id, p)


def _default_video_model() -> str:
    try:
        from app.services.fal_service import DEFAULT_VIDEO_MODEL
        return DEFAULT_VIDEO_MODEL
    except Exception:
        return "seedance-2.5"


def video_gen_seconds(model_id: str | None, duration_s, p: dict | None = None) -> int:
    """Seconds GENERATED (billed) by the provider for a requested clip length:
    native clamp of the model, then the `video_max_gen_s` cap. Mirrors what
    the pipeline sends (fal_service.generated_duration)."""
    from app.services.fal_service import generated_duration, resolve_video_model
    p = p or load()
    cap = _reglage_fini(p, "video_max_gen_s")
    return generated_duration(resolve_video_model(model_id), int(duration_s or 5),
                              cap or None)


def video_request_op(model_id: str | None, duration_s, resolution: str | None,
                     n: int = 1, p: dict | None = None) -> dict:
    """`estimate` op of a video generation request, on the seconds that will
    ACTUALLY be generated (not the ffmpeg-extended target)."""
    mid = (model_id or "").strip() or _default_video_model()
    return {"kind": "seedance", "model": mid, "n": int(n),
            "resolution": resolution or "1080p",
            "duration_s": video_gen_seconds(mid, duration_s, p)}


def _reglage_fini(p: dict, cle: str) -> float:
    """Réglage numérique de pricing.json : une valeur illisible, non finie
    (NaN, Infinity) ou négative retombe sur le défaut — elle n'ouvre jamais
    la garde. 0 reste 0 (« aucun plafond »), comme monthly_budget_usd."""
    try:
        v = float(p.get(cle, DEFAULTS[cle]))
    except (TypeError, ValueError):
        v = float(DEFAULTS[cle])
    if not math.isfinite(v) or v < 0:
        v = float(DEFAULTS[cle])
    return v


def _usd_fr(v: float) -> str:
    # round(...) + 0.0 : -0.0 et -0,001 s'affichent « 0,00 », pas « -0,00 »
    return f"{round(float(v), 2) + 0.0:.2f}".replace(".", ",")


def cost_guard(total_usd: float, max_usd: float | None = None,
               p: dict | None = None) -> str | None:
    """None when the request may be spent, else the refusal message naming
    the amounts. Limit = the client's `max_usd` (if sent) AND the server cap
    `video_max_usd_per_request` (0 = no cap): the lower one wins, a higher
    `max_usd` never lifts the server cap."""
    p = p or load()
    try:
        total = float(total_usd)
    except (TypeError, ValueError):
        total = float("nan")
    if not math.isfinite(total):
        # un tarif illisible (NaN) rendrait toute comparaison fausse, donc la
        # garde ouverte : un devis qu'on ne sait pas chiffrer est refusé
        return ("Estimation non chiffrable (tarif non fini dans les tarifs) "
                "— rien n'a été généré.")
    plafond = _reglage_fini(p, "video_max_usd_per_request")
    limites = []
    if max_usd is not None:
        limites.append((float(max_usd), "max_usd envoyé"))
    if plafond > 0:
        limites.append((plafond, "video_max_usd_per_request des tarifs"))
    if not limites:
        return None
    lim, source = min(limites, key=lambda x: x[0])
    tot = round(total, 2)
    if tot > round(lim, 2) + 1e-9:
        return (f"Estimation {_usd_fr(tot)} $ > plafond {_usd_fr(lim)} $ "
                f"({source}) — rien n'a été généré.")
    return None


def _video_label_provider(model_id: str) -> tuple:
    """(display label, billing provider) from the registry; safe fallback."""
    try:
        from app.services.fal_service import VIDEO_MODELS
        m = VIDEO_MODELS.get(model_id)
        if m:
            return f"Video ({m['label']})", m["provider"]
    except Exception:
        pass
    return f"Video ({model_id})", "fal"


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
      {"kind":"sprite2d","frames":16,"remove_bg":"api"}
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
        # Un modèle vide ou absent se résout au DÉFAUT du registre (Seedance
        # 2.5), jamais à l'ancien forfait 0,04 $/s qui sous-estimait ×12. Le
        # forfait ne sert plus qu'à l'historique, sur demande explicite.
        model = str(op.get("model") or "").strip() or _default_video_model()
        rate = None if op.get("legacy") else \
            video_rate(model, str(op.get("resolution") or "1080p"), p)
        if rate is not None:
            label, prov = _video_label_provider(model)
            lines.append(_line(prov, label, dur, "s", dur * rate))
        else:
            # historique (job d'avant la colonne video_model) ou modèle
            # inconnu du tableau des tarifs
            lines.append(_line("fal", "Seedance video", dur, "s",
                               dur * p["seedance_usd_per_s"]))
    elif kind == "video":
        # P1 #9 (28/09/2026) : UNE requête vidéo telle que la GARDE la chiffre
        # (`_devis_video` : bornage natif, plafond `video_max_gen_s`,
        # résolution 1080p par défaut, × n) — l'estimation « ≈ $ » du Studio
        # l'envoie, et c'est son total qui part en `max_usd`. Durée illisible
        # -> 5 s (le `or 5` de video_gen_seconds) ; modèle inconnu -> ligne
        # « seedance » brute (même repli qu'avant, rien n'est refusé ici).
        try:
            dur = float(op.get("duration_s") or 5)
            if not math.isfinite(dur):
                dur = 5.0
        except (TypeError, ValueError):
            dur = 5.0
        try:
            n = max(1, int(op.get("n", 1)))
        except (TypeError, ValueError):
            n = 1
        try:
            sub = video_request_op(op.get("model"), dur, op.get("resolution"), n=n, p=p)
        except ValueError:
            sub = {"kind": "seedance", "model": op.get("model"), "n": n,
                   "resolution": op.get("resolution"), "duration_s": dur}
        lines.extend(estimate(sub, p)["breakdown"])
    elif kind == "heygen":
        chars = float(op.get("chars", 0))
        mins = max(0.1, chars / max(1.0, p["heygen_chars_per_min"])) if chars \
            else float(op.get("minutes", 1.0))
        credits = mins * p["heygen_credits_per_min"]
        lines.append(_line("heygen", "HeyGen avatar", credits, "credits",
                           credits * p["heygen_credit_usd"]))
    elif kind == "elevenlabs":
        chars = float(op.get("chars", 0))
        model = str(op.get("model") or "").strip()
        label = f"Voiceover ({model})" if model else "Voiceover"
        lines.append(_line("elevenlabs", label, chars, "chars",
                           chars * elevenlabs_rate(model or None, p)))
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
            # au tarif du modèle vidéo (défaut du registre), plus au forfait
            lines.extend(estimate({"kind": "seedance", "duration_s": sd,
                                   "model": op.get("video_model") or "",
                                   "resolution": op.get("resolution")},
                                  p)["breakdown"])
        # P1 #6 (28/09) : les scènes Seedance d'un épisode, chacune à SON
        # modèle et SA résolution (episode_video.video_ops / cost_meta).
        for v in op.get("videos") or []:
            if isinstance(v, dict):
                lines.extend(estimate(dict(v, kind="seedance"), p)["breakdown"])
    elif kind == "extend":
        # Plan Quick T2 (tâche #51) : l'extension générative d'un clip, au tarif du modèle, son compris ou non.
        model = str(op.get("model") or "veo-3.1-fast-extend")
        secs = float(op.get("duration_s", 7))
        rates = p.get("extend_usd_per_s") or DEFAULTS["extend_usd_per_s"]
        tarif = rates.get(model) or DEFAULTS["extend_usd_per_s"].get(model) or {"son": 0.40, "muet": 0.20}
        try:
            rate = float(tarif["son" if op.get("son", True) else "muet"])
        except (TypeError, ValueError, KeyError):
            rate = 0.40
        lines.append(_line("fal", f"Extension ({model}, {'son' if op.get('son', True) else 'muet'})", secs, "s", secs * rate))
    elif kind == "lipsync":
        # Plan Quick T5 (tâche #52) : arrondi au palier de 5 s supérieur, comme fal le facture (math : import du module).
        model = str(op.get("model") or "kling-lipsync")
        secs = max(0.0, float(op.get("duration_s", 0)))
        facture = max(1, math.ceil(secs / 5.0)) * 5.0
        rates = p.get("lipsync_usd_per_s") or DEFAULTS["lipsync_usd_per_s"]
        try:
            rate = float(rates.get(model, DEFAULTS["lipsync_usd_per_s"].get(model, 0.014)))
        except (TypeError, ValueError):
            rate = 0.014
        lines.append(_line("fal", f"Lip-sync ({model}, palier de 5 s)", facture, "s", facture * rate))
    elif kind == "transcribe":
        # Sous-titres, chemin « texte inconnu ». Le chemin « texte connu »
        # (calage local d'une narration déjà écrite) coûte 0 et le dit.
        prov = str(op.get("provider") or "elevenlabs").lower()
        mins = float(op.get("duration_s", 0)) / 60.0
        rates = p.get("stt_usd_per_min") or DEFAULTS["stt_usd_per_min"]
        try:
            rate = float(rates.get(prov, DEFAULTS["stt_usd_per_min"]["openai"]))
        except (TypeError, ValueError, AttributeError):
            rate = DEFAULTS["stt_usd_per_min"]["openai"]
        lines.append(_line(prov, "Transcription (mots horodatés)", mins,
                           "min", mins * rate))
    elif kind == "align":
        # Calage d'un texte connu : ffmpeg + arithmétique locale = 0 $.
        lines.append(_line("local", "Calage sous-titres (local)",
                           float(op.get("duration_s", 0)), "s", 0.0))
    elif kind == "legende":
        # tâche #82 PR C : n images légendées par un modèle vision (image 384 px + consigne en entrée, ~40 mots en sortie)
        n = int(op.get("n", 1))
        model = str(op.get("model") or "gemini-2.5-flash-lite")
        tarif = (p.get("vision_usd_per_mtok") or {}).get(model) or DEFAULTS["vision_usd_per_mtok"]["gemini-2.5-flash-lite"]
        it, ot = n * (258 + 90), n * 70
        usd = it / 1e6 * float(tarif["in"]) + ot / 1e6 * float(tarif["out"])
        lines.append(_line("gemini", f"Légendes {model} x{n}", n, "image", usd))
    elif kind == "stems":
        dur = float(op.get("duration_s", 0))
        lines.append(_line("fal", "Séparation en stems (Demucs)", dur, "s",
                           dur * float(p.get("demucs_usd_per_s", DEFAULTS["demucs_usd_per_s"]))))
    elif kind == "matte":
        # T103 (plan son-vfx T9) : BiRefNet vidéo. Le taux reste 0 tant qu'un premier tir n'a pas été lu sur le
        # tableau de bord fal (la page n'affiche que « $0 per compute second ») — et la LIGNE le dit : un zéro
        # qui se lit « à mesurer » n'est pas un zéro qui se lit « gratuit ».
        dur = float(op.get("duration_s", 0))
        taux = float(p.get("birefnet_video_usd_per_s", DEFAULTS["birefnet_video_usd_per_s"]))
        lines.append(_line("fal", "Détourage vidéo (BiRefNet)" + (" — prix à mesurer" if not taux else ""),
                           dur, "s", dur * taux))
    elif kind == "matte_image":
        # t168d : l'aperçu du détourage, UNE image — même règle que la vidéo : un taux inconnu se dit « à mesurer »
        n = max(1, int(op.get("images", 1) or 1))
        taux = float(p.get("birefnet_image_usd", DEFAULTS["birefnet_image_usd"]))
        lines.append(_line("fal", "Détourage d'une image (BiRefNet)" + (" — prix à mesurer" if not taux else ""),
                           n, "img", n * taux))
    elif kind == "voix_sts":
        mins = max(0.0, float(op.get("duration_s", 0) or 0)) / 60.0
        chars = mins * float(p.get("elevenlabs_sts_chars_per_min", DEFAULTS["elevenlabs_sts_chars_per_min"]))
        lines.append(_line("elevenlabs", "Voix → voix (Voice Changer)", chars, "chars", chars * elevenlabs_rate(None, p)))
    elif kind == "isolate":
        mins = float(op.get("duration_s", 0)) / 60.0
        chars = mins * float(p.get("elevenlabs_isolation_chars_per_min",
                                   DEFAULTS["elevenlabs_isolation_chars_per_min"]))
        lines.append(_line("elevenlabs", "Isolation de voix", chars, "chars", chars * elevenlabs_rate(None, p)))
    elif kind == "matte":
        dur = float(op.get("duration_s", 0))
        rate = float(p.get("birefnet_video_usd_per_s", DEFAULTS["birefnet_video_usd_per_s"]))
        lines.append(_line("fal", "Détourage vidéo (BiRefNet) — prix à mesurer au premier tir"
                           if rate == 0.0 else "Détourage vidéo (BiRefNet)", dur, "s", dur * rate))
    elif kind == "llm":
        prov = op.get("provider", "openai")
        it = float(op.get("in_tok", 1000)); ot = float(op.get("out_tok", 400))
        if prov in ("ollama", "local"):
            # tâche #16 (29/09/2026) : un LLM LOCAL (Ollama) est gratuit — il tombait sur le tarif OpenAI par repli
            lines.append(_line("local", "LLM local (Ollama)", it + ot, "tok", 0.0))
        else:
            rates = p["llm_usd_per_mtok"].get(prov, p["llm_usd_per_mtok"]["openai"])
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
    elif kind == "asset3d":
        # Game Assets 3D: a 3D mesh generation (engine-priced) + optional
        # multi-view edits. Rates seeded from each provider's docs (editable).
        engine = str(op.get("engine") or "tripo").lower()
        tex = bool(op.get("textures", True))
        hd = str(op.get("quality") or "").lower() in ("high", "hd")
        rates = {"tripo": 0.30 if tex else 0.20, "triposr": 0.07,
                 "hunyuan": 0.48 if tex else 0.16, "trellis": 0.35, "rodin": 0.40,
                 # Tripo H3.1, page fal relue le 29/08/2026 : « $0.20 (without
                 # textures), $0.30 (with standard textures), or $0.40 (with HD
                 # textures), plus an additional $0.20 for detailed geometry
                 # and $0.05 for quad mesh if selected. »
                 "tripo-h3.1": (0.40 if hd else 0.30) if tex else 0.20}
        unit = 0.0 if engine == "hunyuan-local" else rates.get(engine, 0.30)
        # T107 : le service GPU local est gratuit — c'est l'argument, et une ligne « fal » le ferait mentir
        lines.append(_line("local", "3D mesh local (Hunyuan3D, GPU)", 1, "gen", 0.0) if engine == "hunyuan-local"
                     else _line("fal", f"3D mesh ({engine})", 1, "gen", unit))
        if engine == "tripo-h3.1":
            # suppléments FACTURÉS, donc affichés : les taire ferait mentir la
            # pastille de coût au moment précis où l'utilisateur décide
            if op.get("geometry_detaillee"):
                lines.append(_line("fal", "Géométrie détaillée", 1, "opt", 0.20))
            if op.get("quad"):
                lines.append(_line("fal", "Maillage quad", 1, "opt", 0.05))
        # formats the first call doesn't return get re-exported = one more paid
        # generation each (worst case), so surface them in the estimate
        extra = len({str(f).lower() for f in (op.get("formats") or [])} - {"glb"})
        if extra:
            lines.append(_line("fal", "Extra format re-exports", extra, "gen", extra * unit))
        if op.get("multiview"):
            v = int(op.get("views", 3))
            lines.append(_line("fal", "Multi-view edits", v, "img",
                               v * float(p.get("seedream_edit_usd", DEFAULTS["seedream_edit_usd"]))))
    elif kind == "asset3d_rig":
        # Rig Meshy d'un job fal (T104, plan-moteurs-3d T2). docs.meshy.ai/en/api/rigging et /animation relues le
        # 06/10/2026 : rig 5 cr (marche + course INCLUSES, basic_animations) ; > 300 000 faces → remesh d'abord ;
        # chaque action de la bibliothèque : 3 cr. UNE LIGNE PAR TÂCHE Meshy, dans l'ordre du tir : la garde des
        # plafonds écrit une dépense par ligne, et la route rattache chacune au coût réel de SA tâche.
        from app.services import meshy_service as _MS
        usd_cr = float(p.get("meshy_credit_usd", DEFAULTS["meshy_credit_usd"]))
        if op.get("remesh_requis"):
            cr = _MS.CREDITS_FLAT["remesh"]
            lines.append(_line("meshy", "Remesh (> 300 000 faces, exigé par le rig)", cr, "credits", cr * usd_cr))
        cr = _MS.CREDITS_FLAT["rigging"]
        lines.append(_line("meshy", "Auto-rig humanoïde (marche + course incluses)", cr, "credits", cr * usd_cr))
        for aid in op.get("actions") or []:
            cr = _MS.CREDITS_FLAT["animations"]
            nom = _MS.ACTIONS_RIG.get(int(aid), f"action {int(aid)}")
            lines.append(_line("meshy", f"Animation {int(aid)} · {nom}", cr, "credits", cr * usd_cr))
    elif kind == "asset3d_views":
        v = int(op.get("views", 4))
        if v:   # un détourage fal seul (T106) n'a aucune vue à facturer
            lines.append(_line("fal", "Vues quasi-orthographiques (Seedream)", v, "img",
                               v * float(p.get("seedream_edit_usd", DEFAULTS["seedream_edit_usd"]))))
        n = int(op.get("rembg", 0) or 0)
        if n:
            lines.append(_line("fal", f"Détourage fal x{n}", n, "img",
                               n * float(p.get("rembg_api_usd", DEFAULTS["rembg_api_usd"]))))
    elif kind == "asset3d_convert":
        if str(op.get("via") or "local") == "meshy":
            from app.services import meshy_service as _MS
            cr = _MS.CREDITS_FLAT["convert"]
            lines.append(_line("meshy", "Conversion Meshy (fbx/usdz/blend)", cr, "credits",
                               cr * float(p.get("meshy_credit_usd", DEFAULTS["meshy_credit_usd"]))))
        else:
            lines.append(_line("local", "Conversion locale (obj/stl/3mf)", 1, "fichier", 0.0))
    elif kind in ("asset3d_lod", "asset3d_textures", "asset3d_local"):
        libelle = {"asset3d_lod": "Chaîne LOD (gltfpack)",
                   "asset3d_textures": "Export textures (PIL)",
                   "asset3d_local": "Hunyuan3D local (GPU)"}[kind]
        lines.append(_line("local", libelle, 1, "op", 0.0))
    elif kind == "asset3d_texture":
        # Texturage Meshy d'un maillage DÉJÀ généré (chaîne Tripo → Meshy).
        # Facturé en CRÉDITS Meshy, jamais en $ chez fal : la grille partagée
        # de meshy_service est la seule source, la conversion $ reste
        # directionnelle (meshy_credit_usd, éditable dans les réglages).
        from app.services import meshy_service as _MS
        res = str(op.get("texture_resolution") or "2k")
        cr = _MS.credits_retexture(res)
        lines.append(_line("meshy", f"Retexture {res}"
                           + (" PBR" if op.get("pbr", True) else ""),
                           cr, "credits",
                           cr * float(p.get("meshy_credit_usd",
                                            DEFAULTS["meshy_credit_usd"]))))
    elif kind == "recast":
        # Avatar live G1 (t162) : prix PAR SECONDE de vidéo source, relevés le 10/10 et tenus dans le
        # catalogue du service (une seule source). Modèle inconnu -> ligne à 0 QUI LE DIT.
        from app.services import recast_service as _rs
        mod = str(op.get("modele") or "")
        try:
            sec = max(0.0, float(op.get("seconds") or 0))
            if not math.isfinite(sec):
                sec = 0.0
        except (TypeError, ValueError):
            sec = 0.0
        if mod in _rs.MODELES:
            res = _rs.resolution(mod, op.get("resolution"))
            lines.append(_line("fal", f"Recast {_rs.MODELES[mod]['label']} ({res})", sec, "s",
                               sec * _rs.prix_usd_s(mod, res)))
        else:
            lines.append(_line("fal", f"Recast : modèle inconnu {mod[:24]!r} (non chiffré)", sec, "s", 0.0))
    elif kind == "direct":
        # Avatar live G0 (t161) : UNE session du Direct, réservée ENTIÈRE (Decart la coupe à cette borne,
        # maxSessionDuration). Durée illisible -> la durée par défaut du Direct, jamais 0.
        from app.services.avatar_live import borner_duree as _bd, DUREE_DEFAUT_S as _dd
        raw = op.get("seconds")
        try:
            ok_ = raw is not None and float(raw) > 0
        except (TypeError, ValueError):
            ok_ = False
        sec = _bd(raw) if ok_ else _dd
        rate = float(p.get("decart_realtime_usd_per_s", DEFAULTS["decart_realtime_usd_per_s"]))
        rapide = bool(op.get("rapide"))
        rate *= 2 if rapide else 1
        lines.append(_line("decart", "Decart Lucy 2.5 (direct" + (", rapide)" if rapide else ")"),
                           sec, "s", sec * rate))
    elif kind == "sprite2d":
        # Game Assets 2D (Sprite Lab): ffmpeg extraction + PIL assembly are
        # local (free); the only billable part is the per-frame fal remove-bg.
        frames = int(op.get("frames", op.get("max_frames", 16)) or 0)
        method = str(op.get("remove_bg") or "none").lower()
        if method == "api" and frames:
            lines.append(_line("fal", f"Remove-BG x{frames}", frames, "img",
                               frames * p.get("rembg_api_usd",
                                             DEFAULTS["rembg_api_usd"])))
        lines.append(_line("local", "Sprite sheet (ffmpeg+PIL)", 1, "sheet", 0.0))
    elif kind == "music":
        # tâche #16 : le prix PAR GÉNÉRATION du catalogue de music_service (une seule source)
        from app.services import music_service as _mu
        mid = str(op.get("model") or "").strip() or _mu.DEFAULT_MUSIC_MODEL
        m = _mu.MUSIC_MODELS.get(mid) or _mu.MUSIC_MODELS[_mu.DEFAULT_MUSIC_MODEL]
        n = max(1, int(op.get("n", 1)))
        if m.get("usd_unit") == "s":
            # T102 : ACE-Step est facturé À LA SECONDE — la durée chiffrée est celle que `_payload`
            # enverra (même fonction, même défaut), sinon le devis et la garde mentiraient.
            sec = _mu.billed_seconds(m, op.get("duration_s"))
            lines.append(_line("fal", f"Musique ({m['label']}) {sec} s x{n}", n * sec, "s",
                               n * sec * float(m["usd"])))
        else:
            lines.append(_line("fal", f"Musique ({m['label']}) x{n}", n, "piste", n * float(m["usd"])))
    elif kind == "sfx":
        n = max(1, min(4, int(op.get("n", op.get("variations", 1)) or 1)))
        d = op.get("duration_s")
        cr = (float(d) * float(p.get("elevenlabs_sfx_credits_per_s", 40.0)) if d not in (None, "", 0)
              else float(p.get("elevenlabs_sfx_credits_auto", 200.0)))
        lines.append(_line("elevenlabs", f"Bruitage x{n}", cr * n, "chars", cr * n * float(p["elevenlabs_usd_per_char"])))
    elif kind == "upscale":
        n = max(1, int(op.get("n", 1)))
        lines.append(_line("fal", f"Upscale esrgan x{n}", n, "image", n * float(p.get("esrgan_usd", 0.002))))
    elif kind == "heygen_photo_avatar":
        lines.append(_line("heygen", "Avatar photo HeyGen", 1, "avatar", float(p.get("heygen_photo_avatar_usd", 1.32))))
    elif kind == "meshy":
        cr = float(op["credits"] if op.get("credits") is not None else p.get("meshy_task_credits_defaut", 20.0))
        lines.append(_line("meshy", "Tâche Meshy", cr, "credits", cr * float(p["meshy_credit_usd"])))
    elif kind == "animate":
        # Animation node: per-frame Pillow + ffmpeg, all local compute, no
        # external API -> $0 (kept in the breakdown so the cost pill is honest).
        dur = float(op.get("duration_s", 8))
        lines.append(_line("local", "Animation (ffmpeg)", dur, "s", 0.0))
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
