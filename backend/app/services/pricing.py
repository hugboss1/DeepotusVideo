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
    # t182 (G0) : modèles d'image fal « simples », l'image au cadre 1K que la
    # requête épingle. Relevé le 11/10/2026 sur fal.ai/models/<endpoint> :
    # - nano-banana-2.1 : facturé aux jetons ; coût représentatif publié pour
    #   UNE image 1K, prompt court, thinking medium : 0,040 $ (0,044 $ en edit
    #   avec deux images 1K) ;
    # - flux-3 : 0,048 $ l'image 1 MP (promo -50 % terminée le 08/10) ;
    # - seedream-5-pro : 0,0675 $ l'image <= 1536x1536 (t2i ET edit ; +0,0045 $
    #   par image d'entrée au-delà de la première) ;
    # - ideogram-4.5 : 0,22 $ l'image en qualité `high` (celle que la requête
    #   écrit ; la taille ne change pas le prix) ;
    # - qwen-image-3 : 0,04 $ l'image 1K ;
    # - recraft-4.1-vecteur : la page dit 0,08 $ l'image dans son encart de
    #   prix, mais 0,007 $ (« 100 images 0,70 $ ») dans son texte : écart
    #   daté, on retient le PLUS HAUT pour que la garde de dépense ne passe
    #   pas sous la facture.
    # Une clé à 0 se dit « prix à mesurer » (catalogue_ia), jamais « gratuit ».
    "nano_banana_21_usd": 0.04,
    "flux3_usd": 0.048,
    "seedream5_pro_usd": 0.0675,
    "ideogram45_usd": 0.22,
    "qwen_image3_usd": 0.04,
    "recraft41_vecteur_usd": 0.08,
    # Ancien tarif forfaitaire Seedance (avant le registre W-a). Il ne sert
    # plus qu'au coût HISTORIQUE des jobs d'avant la colonne `video_model`
    # (op `legacy: True`) : un modèle vide se résout au défaut du registre.
    "seedance_usd_per_s": 0.04,
    # Avatar live G0 (t161, 10/10/2026) : Decart Lucy 2.5 en temps réel, à la seconde de génération active.
    # Relevé le 10/10 sur docs.platform.decart.ai/getting-started/pricing : 0,02 $/s (720p), 0,04 $/s en
    # mode rapide (x2).
    "decart_realtime_usd_per_s": 0.02,
    # t168f (11/10) : le même Lucy 2.5 par fal (decart/lucy-2-5/realtime, llms.txt relu le 11/10) : 0,02 $/s, pas de
    # mode rapide. Facturé par fal (clé fal seule).
    "fal_lucy_realtime_usd_per_s": 0.02,
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
        # t184 (G2) — fal_prix.py du 11/10/2026, colonne SANS audio (le
        # pipeline coupe l'interrupteur). Veo 3.1 : même tarif sur l'endpoint
        # first-last-frame que sur l'i2v. Lite : 0,03 $/s 720p, 0,05 $/s 1080p.
        "veo-3.1-fal":         {"*": 0.20},
        "veo-3.1-lite-fal":    {"720p": 0.03, "1080p": 0.05},
        # MiniMax H3 Max : tarif PLEIN (0,05/0,08/0,16 $/s, 5 s minimum) ;
        # fal affiche une promo de -40 % (0,03/0,048/0,096) que la garde ne
        # suppose pas. 720p = la colonne 768P (fal_service `res_alias`).
        "h3-max":              {"480p": 0.05, "720p": 0.08, "768p": 0.08, "1080p": 0.16},
        "wan-3.0":             {"480p": 0.05, "720p": 0.10, "1080p": 0.20},
        "gemini-omni-flash":   {"720p": 0.10, "1080p": 0.15},
        # LTX 2.5 Fast : audio natif inclus à toutes les résolutions
        "ltx-2.5-fast":        {"720p": 0.09, "1080p": 0.13},
        "kling-v3-turbo-pro":  {"*": 0.14},
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
    # t186 (G4, 12/10/2026) : le registre du détourage (app.services.detourage.REGISTRE), pages fal relues le
    # 12/10/2026. 0.0 = « à mesurer » (lire le tableau de bord fal après le premier tir, écrire ici, daté).
    "bria_rmbg_usd": 0.018,           # fal-ai/bria/background/remove, par image (SANS prompt : 0,03 avec)
    "pixelcut_rmbg_usd": 0.0,         # pixelcut/background-removal — à mesurer (la page n'affiche que la vidéo)
    "ideogram_rmbg_usd": 0.01,        # fal-ai/ideogram/remove-background, par image
    "feynobg_usd": 0.0,               # fal-ai/feynobg — à mesurer
    "sam3_image_usd": 0.005,          # fal-ai/sam-3/image, par image
    "bria_objet_usd": 0.0,            # bria/extract-object — à mesurer
    "bria_video_usd_per_s": 0.05,     # bria/video/background-removal/v3, par seconde
    "veed_rmbg_usd_per_30f": 0.012,   # veed/video-background-removal/fast, par tranche de 30 images (refine ON, prudent)
    "pixelcut_video_usd_per_30f": 0.022,   # pixelcut/video-background-removal, par tranche de 30 images
    "sam31_video_usd_per_16f": 0.01,  # fal-ai/sam-3-1/video, par tranche de 16 images
    # t187 (G5, 12/10/2026) : le registre des bruitages (app.services.sfx_service.SFX_MODELS), pages fal relues le
    # 12/10/2026. 0.0 = « à mesurer » (lire le tableau de bord fal après le premier tir, écrire ici, daté).
    "elevenlabs_sfx_fal_usd": 0.0,    # fal-ai/elevenlabs/sound-effects/v2 — prix non affiché : à mesurer
    "sonilo_sfx_usd_per_s": 0.0018,   # sonilo/v1.1/text-to-sound-effects, par seconde de sortie et par échantillon
    "mirelo_sfx_usd": 0.0,            # mirelo-ai/sfx1.6/text-to-audio — à mesurer
    "stable_audio3_sfx_usd": 0.0,     # fal-ai/stable-audio-3/small/sfx/text-to-audio — à mesurer
    "sonilo_video_usd_per_s": 0.009,  # sonilo/v1.1/video-to-sound-effects, par seconde de sortie et par échantillon
    "mirelo_video_usd": 0.0,          # mirelo-ai/sfx1.6/video-to-video — à mesurer
    "kling_v2a_usd": 0.035,           # fal-ai/kling-video/video-to-audio, par vidéo
    "hunyuan_foley_usd": 0.0,         # fal-ai/hunyuan-video-foley — à mesurer
    # fal-ai/thinksound : 0,001 $ par seconde de CALCUL, durée de calcul inconnue d'avance — aucune durée inventée,
    # 0 « à mesurer » tant qu'un premier tir n'a pas été lu sur le tableau de bord fal
    "thinksound_usd": 0.0,
    # t188 (G6, 12/10/2026) : les VFX IA (app.services.vfx_ia.REGISTRE), pages fal relues le 12/10/2026. Un tarif
    # par résolution quand la page en donne plusieurs ; 0.0 = « à mesurer ».
    "vfx_relight_usd_per_s": {"480P": 0.05, "768P": 0.08, "1080P": 0.16, "2K": 0.32},   # minimax/h3-max/relight,
                                      # par seconde de vidéo (= durée de la source)
    "vfx_insert_usd_per_s": {"480p": 0.05, "768p": 0.06},   # minimax/h3-max/insert-video, par seconde de SCÈNE
                                      # générée (`duration`) ; au-delà de 4 096 jetons de référence, 0,02 $ / 1 000 (non chiffrable)
    "vfx_ltx_usd_per_mp": 0.0024075,  # fal-ai/ltx-2.3-quality/{clean-plate,day-to-night,water-simulation}, par MP généré
    "vfx_colorisation_usd_per_mp": 0.0,   # fal-ai/ltx-2.3-quality/colorization — la page n'affiche aucun prix : à mesurer
    "vfx_void_usd": {"passe1": 0.05, "passe2": 0.10, "masque": 0.05},   # fal-ai/void-video-inpainting, par vidéo ;
                                      # + 0,05 $ pour le masque SAM 3 (mask_prompt)
    "vfx_kling_edit_usd_per_s": 0.168,   # fal-ai/kling-video/o3/pro/video-to-video/edit, par seconde générée
    "vfx_flux3_edit_usd_per_s": 0.03,    # blackforestlabs/flux-3/edit-video, par seconde (720p)
    "vfx_reframe_usd_per_s": {"720p": 0.10, "1080p": 0.20},   # fal-ai/ltx-2.3/reframe, par seconde de la source
    "vfx_topaz_usd_per_10s": {"720p": 0.10, "1080p": 0.20, "4k": 0.60},   # topaz/upscale/video/precision (Proteus),
                                      # par tranche de 10 s de sortie, arrondie une fois par travail
    "vfx_pixverse_usd_5s": {"360p": 0.15, "540p": 0.15, "720p": 0.20, "1080p": 0.40},   # fal-ai/pixverse/v5.5/effects,
                                      # clip unique sans audio, 5 s ; 8 s = x2, 10 s = x2,2
    # t189 (G7, 12/10/2026) : le storyboard 3D (app.services.storyboard3d.MODELES). Les deux pages fal affichent
    # « $0.02 per unit » SANS dire l'unité : chiffré 0,02 $ par REQUÊTE, unité à confirmer au premier tir (tableau de
    # bord fal). Ne pas confondre avec sam3_image_usd (fal-ai/sam-3/image, le détourage, 0,005 $).
    "sam3_3d_objects_usd": 0.02,      # fal-ai/sam-3/3d-objects, par requête (unité fal à confirmer)
    "sam3_3d_body_usd": 0.02,         # fal-ai/sam-3/3d-body, par requête (unité fal à confirmer)
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
    # t182 (G0) : chacun SA clé — un id absent d'ici retombait sur le tarif
    # FLUX dans `estimate`.
    "nano-banana-2.1":     ("Nano Banana 2.1 (via fal)", "fal", "nano_banana_21_usd"),
    "flux-3":              ("FLUX 3 (via fal)", "fal", "flux3_usd"),
    "seedream-5-pro":      ("Seedream 5 Pro (via fal)", "fal", "seedream5_pro_usd"),
    "ideogram-4.5":        ("Ideogram 4.5 (via fal)", "fal", "ideogram45_usd"),
    "qwen-image-3":        ("Qwen Image 3 (via fal)", "fal", "qwen_image3_usd"),
}

# t182 (G0) : modèles d'image VECTORIELS (sortie SVG). Hors de _IMAGE_MODELS,
# que lisent les consommateurs raster (Cardforge, lots d'art, sélecteurs) : ils
# ne doivent jamais les proposer. Tarifés quand même (estimate, catalogue_ia).
_IMAGE_MODELS_VECTEUR = {
    "recraft-4.1-vecteur": ("Recraft 4.1 vecteur SVG (via fal)", "fal",
                            "recraft41_vecteur_usd"),
}


def image_model_spec(model: str) -> tuple:
    """(libellé, fournisseur, clé de prix) d'un id d'image, raster ou
    vectoriel ; repli FLUX pour un id inconnu (comportement d'avant)."""
    return (_IMAGE_MODELS.get(model)
            or _IMAGE_MODELS_VECTEUR.get(model)
            or _IMAGE_MODELS["flux"])


def load() -> dict:
    """Defaults merged with the user's pricing.json overrides (if any)."""
    data = dict(DEFAULTS)
    try:
        if _PRICING_FILE.is_file():
            override = json.loads(_PRICING_FILE.read_text(encoding="utf-8"))
            if isinstance(override, dict):
                for k, v in override.items():
                    data[k] = v
                # t184 (G2) : la table vidéo se FUSIONNE par modèle (puis par
                # résolution) — une table enregistrée avant l'arrivée d'un
                # modèle ne le prive plus de son tarif ; les valeurs de
                # l'utilisateur gagnent toujours.
                tv = override.get("video_usd_per_s")
                if isinstance(tv, dict):
                    fus = {m: dict(r) for m, r in DEFAULTS["video_usd_per_s"].items()}
                    for m, r in tv.items():
                        # un « * » de l'utilisateur vaut pour TOUTES les
                        # résolutions : aucune colonne par défaut ne le masque
                        fus[m] = r if (not isinstance(r, dict) or "*" in r) else {**fus.get(m, {}), **r}
                    data["video_usd_per_s"] = fus
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


def taux_detourage(mid: str, p: dict | None = None) -> float:
    """t186 (G4) — LE taux d'un modèle du registre du détourage, dans son unité (« image », « s », « 30 images »,
    « 16 images ») : la clé de prix de l'entrée lue dans la table (`p`, sinon pricing.load), repli DEFAULTS. 0 pour
    une voie LOCALE, un id inconnu ou une valeur illisible. Source unique du catalogue (catalogue_ia), de la note
    du matte (matte_service.note_prix) et du devis (_ligne_detourage)."""
    from app.services import detourage as _DT
    e = _DT.REGISTRE.get(str(mid or ""))
    if not e or e["voie"] == "local" or not e.get("prix"):
        return 0.0
    p = p if p is not None else load()
    try:
        return float(p.get(e["prix"], DEFAULTS.get(e["prix"], 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def taux_sfx(mid: str, p: dict | None = None) -> float:
    """t187 (G5) — LE taux d'un modèle du registre des bruitages (app.services.sfx_service.SFX_MODELS), dans son
    unité (« s » : par seconde de sortie et par échantillon ; « video » ; « son ») : la clé de prix de l'entrée lue
    dans la table (`p`, sinon pricing.load), repli DEFAULTS. ElevenLabs direct : la grille ElevenLabs d'avant
    (crédits par seconde x $ par caractère). 0 pour un id inconnu ou une valeur illisible. Source unique du
    catalogue (catalogue_ia) et du devis (_ligne_sfx)."""
    from app.services import sfx_service as _S
    e = _S.SFX_MODELS.get(str(mid or ""))
    if not e:
        return 0.0
    p = p if p is not None else load()
    try:
        if e["voie"] == "elevenlabs":
            return float(p.get("elevenlabs_sfx_credits_per_s", 40.0)) * float(
                p.get("elevenlabs_usd_per_char", DEFAULTS["elevenlabs_usd_per_char"]))
        return float(p.get(e["prix"], DEFAULTS.get(e["prix"], 0.0)) or 0.0) if e.get("prix") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _ligne_sfx(op: dict, p: dict) -> dict:
    """t187 (G5) — UNE ligne de devis pour un bruitage fal du registre (kind « sfx » avec `modele`, ou
    « sfx_video »), nommée par le libellé du modèle et suffixée « — prix à mesurer » quand son taux vaut 0.
      · unité « s »     : `secondes` (la durée qui partira, sinon le défaut du schéma ; en vidéo, la durée de la
                          source) x `echantillons` x le tarif ;
      · unité « video » / « son » : `echantillons` x le tarif.
    Un id inconnu se dit « non chiffré »."""
    from app.services import sfx_service as _S
    mid = str(op.get("modele") or "")
    e = _S.SFX_MODELS.get(mid)
    if e is None:
        return _line("fal", f"Bruitage : modèle inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    try:
        n = max(1, min(4, int(op.get("echantillons", op.get("n", op.get("variations", 1))) or 1)))
    except (TypeError, ValueError):
        n = 1
    taux = taux_sfx(mid, p)
    from app.i18n import Message, Nom   # t192 : la ligne se dit dans la langue de la requête (/cost/estimate)
    label = Nom(mid, e["label"]) if taux else Message("pricing.a_mesurer", label=Nom(mid, e["label"]))
    if e["unite"] == "s":
        sec = op.get("secondes", op.get("duration_s"))
        if e["nature"] == _S.SFX_TEXTE:
            try:
                sec = _S.secondes_facturees(mid, sec)
            except ValueError:
                sec = _S.secondes_facturees(mid, None)
        try:
            sec = max(0.0, float(sec or 0))
        except (TypeError, ValueError):
            sec = 0.0
        return _line("fal", Message("pricing.ligne_sec", label=label, sec=f"{sec:g}", n=n), sec * n, "s",
                     sec * n * taux)
    return _line("fal", Message("pricing.ligne_x", label=label, n=n), n, e["unite"], n * taux)


_VFX_MULT_PIXVERSE = {"5": 1.0, "8": 2.0, "10": 2.2}


def taux_vfx(mid: str, op: dict | None = None, p: dict | None = None) -> float:
    """t188 (G6) — LE taux d'un geste VFX IA (app.services.vfx_ia.REGISTRE), dans son unité : « s » (selon la
    résolution choisie), « mp », « video » (passe 1 ou 2, + le masque SAM 3 quand mask_prompt part), « tranche10s »
    (classe du côté court de sortie ; au catalogue, la plus basse : « dès »), « effet » (base 5 s de la résolution x 1 / 2 / 2,2 selon la durée). `op` : les
    options et dimensions de la demande (None : les défauts du geste — le prix affiché au catalogue). Clé de prix lue
    dans la table (`p`, sinon pricing.load), repli DEFAULTS. 0 pour un id inconnu ou une valeur illisible (« à
    mesurer »). Source unique du catalogue (catalogue_ia), du devis (_ligne_vfx) et donc de la garde."""
    from app.services import vfx_ia as _V
    e = _V.REGISTRE.get(str(mid or ""))
    if not e:
        return 0.0
    p = p if p is not None else load()
    op = op or {}
    o = _V.options_completees(mid, op.get("options"))
    brut = p.get(e["prix"], DEFAULTS.get(e["prix"], 0.0))
    try:
        u = e["unite"]
        if u == "video":
            d = brut if isinstance(brut, dict) else {}
            base = float(d.get("passe2" if o.get("enable_pass2_refinement") else "passe1", 0.0) or 0.0)
            # le masque SAM 3 : quand mask_prompt part — au catalogue (sans op), il est compté puisque le geste
            # l'exige (le prix affiché est celui du tir le plus simple)
            masque = o.get("mask_prompt") or (not op and e["options"].get("mask_prompt", {}).get("requis"))
            return base + (float(d.get("masque", 0.0) or 0.0) if masque else 0.0)
        if u == "tranche10s":
            cl = _V.classe_topaz(op.get("largeur"), op.get("hauteur"), o.get("upscale_factor")) if op else "720p"
            return float((brut or {}).get(cl, 0.0) or 0.0)
        if u == "effet":
            return float((brut or {}).get(str(o.get("resolution")), 0.0) or 0.0) * _VFX_MULT_PIXVERSE.get(
                str(o.get("duration")), 1.0)
        if isinstance(brut, dict):
            return float(brut.get(str(o.get("resolution")), 0.0) or 0.0)
        return float(brut or 0.0)
    except (TypeError, ValueError, AttributeError):
        return 0.0


def _ligne_vfx(op: dict, p: dict) -> dict:
    """t188 (G6) — UNE ligne de devis pour un geste VFX IA : quantité (vfx_ia.unites) x taux (taux_vfx), nommée par
    le libellé du geste et suffixée « — prix à mesurer » quand le taux vaut 0. L'insertion H3 rappelle que les jetons
    de référence au-delà de 4 096 (0,02 $ / 1 000) ne sont pas chiffrables d'avance. Un id inconnu se dit « non
    chiffré »."""
    from app.services import vfx_ia as _V
    mid = str(op.get("modele") or "")
    e = _V.REGISTRE.get(mid)
    if e is None:
        return _line("fal", f"VFX IA : geste inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    q, det = _V.unites(mid, op)
    taux = taux_vfx(mid, op, p)
    from app.i18n import Message, Nom   # t192 : la ligne se dit dans la langue de la requête (route /vfx-ia, devis)
    label = Message("pricing.vfx.ligne" + ("_a_mesurer" if not taux else "") + ("_jetons" if mid == "inserer-h3" else ""),
                    modele=Nom(mid, e['label']), det=det)
    return _line("fal", label, q, e["unite"], q * taux)


def taux_objets3d(mid: str, p: dict | None = None) -> float:
    """t189 (G7) — LE taux par requête d'un modèle du storyboard 3D (app.services.storyboard3d.MODELES) : sa clé de
    prix lue dans la table (`p`, sinon pricing.load), repli DEFAULTS ; 0 pour un id inconnu ou une valeur illisible.
    Source unique du catalogue (catalogue_ia) et du devis (_ligne_objets3d), donc de la garde."""
    from app.services import storyboard3d as _SB
    e = _SB.MODELES.get(str(mid or ""))
    if not e:
        return 0.0
    p = p if p is not None else load()
    try:
        v = float(p.get(e["prix"], DEFAULTS.get(e["prix"], 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) and v >= 0 else 0.0


def _ligne_objets3d(op: dict, p: dict) -> dict:
    """t189 (G7) — UNE ligne de devis pour `n` requêtes SAM 3 (storyboard 3D), qui DIT que l'unité de fal est à
    confirmer (la page affiche « per unit » sans la nommer). Un id inconnu se dit « non chiffré »."""
    from app.services import storyboard3d as _SB
    mid = str(op.get("modele") or _SB.DEFAUT)
    e = _SB.MODELES.get(mid)
    if e is None:
        return _line("fal", f"Storyboard 3D : modèle inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    n = max(1, int(op.get("n", 1) or 1))
    taux = taux_objets3d(mid, p)
    from app.i18n import Message, Nom   # t192
    label = Message("pricing.objets3d.ligne" + ("" if taux else "_a_mesurer"), modele=Nom(mid, e['label']), n=n)
    return _line("fal", label, n, "requete", n * taux)


def _ligne_detourage(op: dict, p: dict) -> dict:
    """t186 (G4) — UNE ligne de devis pour un détourage du registre (app.services.detourage.REGISTRE), nommée
    par le libellé du modèle et suffixée « — prix à mesurer » quand son taux vaut 0.
      · unité « image » : `images` (défaut 1) x le tarif par image ;
      · unité « s »     : `secondes` x le tarif par seconde (ou `images_video` / `fps` si seules les images
                          sont connues) ;
      · unité « 30 images » / « 16 images » : ceil(`images_video` / taille) tranches. Si seul `secondes` est
        donné, les images se déduisent avec `fps` (défaut 30 — prudent : un rendu à 24 i/s est surestimé,
        jamais sous-estimé, ce qui est le bon sens pour une garde de plafond).
    Une voie LOCALE est une ligne 0 $ du fournisseur « local ». Un id inconnu se dit « non chiffré »."""
    from app.services import detourage as _DT
    mid = str(op.get("modele") or "")
    e = _DT.REGISTRE.get(mid)
    if e is None:
        return _line("fal", f"Détourage : modèle inconnu {mid[:24]!r} (non chiffré)", 1, "job", 0.0)
    n_img = max(1, int(op.get("images", 1) or 1))
    from app.i18n import Message, Nom   # t192
    if e["voie"] == "local":
        return _line("local", Nom(mid, e["label"]), n_img, "img", 0.0)
    taux = taux_detourage(mid, p)
    label = Nom(mid, e["label"]) if taux else Message("pricing.a_mesurer", label=Nom(mid, e["label"]))
    fps = float(op.get("fps") or 30) or 30.0
    unite = e["unite"]
    if unite == "image":
        return _line("fal", Message("pricing.ligne_x", label=label, n=n_img), n_img, "img", n_img * taux)
    if unite == "s":
        sec = op.get("secondes")
        if sec is None and op.get("images_video") is not None:
            sec = float(op["images_video"]) / fps
        sec = max(0.0, float(sec or 0))
        return _line("fal", label, sec, "s", sec * taux)
    taille = _DT.TRANCHES[unite]
    imgs = op.get("images_video")
    if imgs is None:
        imgs = math.ceil(max(0.0, float(op.get("secondes") or 0)) * fps)
    tranches = math.ceil(max(0, int(imgs)) / taille)
    return _line("fal", Message("pricing.detour.tranches", label=label, imgs=int(imgs), t=tranches, taille=taille),
                 tranches, unite, tranches * taux)


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
      {"kind":"detourage","modele":"bria-rmbg","images":1}   (t186 : secondes / images_video / fps en vidéo)
      {"kind":"vfx_ia","modele":"retoucher-flux3","secondes":5}   (t188 : options, largeur, hauteur)
      {"kind":"objets3d","modele":"sam-3-3d-objects","n":1}   (t189 : storyboard 3D SAM 3, par requête)
    Returns {breakdown:[line...], total_usd, credits:{provider:n}}.
    """
    p = p or load()
    kind = (op or {}).get("kind", "")
    lines = []

    if kind == "image":
        n = int(op.get("n", 1))
        model = str(op.get("model") or "flux").lower()
        label, prov, key = image_model_spec(model)
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
        ilabel, iprov, ikey = image_model_spec(model)
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
        from app.i18n import Message   # t192
        lines.append(_line("fal", Message("pricing.matte.ligne" + ("" if taux else "_a_mesurer")),
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
    elif kind == "detourage":
        lines.append(_ligne_detourage(op, p))
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
        if op.get("fournisseur") == "fal":
            # t168f : le Direct par fal — la borne est tenue par NOTRE relais (fal n'en expose aucune)
            rate = float(p.get("fal_lucy_realtime_usd_per_s", DEFAULTS["fal_lucy_realtime_usd_per_s"]))
            lines.append(_line("fal", "fal · Decart Lucy 2.5 (direct)", sec, "s", sec * rate))
        else:
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
        from app.i18n import Message   # t192 : lignes traduisibles (/cost/estimate)
        mid = str(op.get("model") or "").strip() or _mu.DEFAULT_MUSIC_MODEL
        m = _mu.MUSIC_MODELS.get(mid) or _mu.MUSIC_MODELS[_mu.DEFAULT_MUSIC_MODEL]
        n = max(1, int(op.get("n", 1)))
        if m.get("usd_unit") == "s":
            # T102 : ACE-Step est facturé À LA SECONDE — la durée chiffrée est celle que `_payload`
            # enverra (même fonction, même défaut), sinon le devis et la garde mentiraient. t187 : le prix passe
            # par la règle unique usd_de, comme les deux autres branches.
            sec = _mu.billed_seconds(m, op.get("duration_s"))
            lines.append(_line("fal", Message("pricing.musique.sec", modele=_mu._nom(m), sec=sec, n=n), n * sec, "s",
                               n * _mu.usd_de(m, op.get("duration_s"))))
        elif m.get("usd_unit") == "min":
            # t187 (G5) : ElevenLabs Music — 0,60 $ par minute de sortie ARRONDIE À LA MINUTE SUPÉRIEURE (usd_de)
            sec = _mu.billed_seconds(m, op.get("duration_s"))
            mins = math.ceil((sec or 0) / 60)
            lines.append(_line("fal", Message("pricing.musique.min", modele=_mu._nom(m), sec=sec, mins=mins, n=n),
                               n * mins, "min", n * _mu.usd_de(m, op.get("duration_s"))))
        else:
            # t187 (G5) : Mureka — le prix dépend de la présence de paroles (`paroles` dans l'op) ; « à mesurer »
            # quand le tarif vaut 0 (Lyria 3.5, MiniMax Music 3, Stable Audio 3)
            par = bool(op.get("paroles"))
            usd = _mu.usd_de(m, None, par)
            lbl = (Message("pricing.musique.avec_paroles", modele=_mu._nom(m)) if par and m.get("usd_paroles") is not None
                   else Message("pricing.musique.sans_paroles", modele=_mu._nom(m)) if m.get("usd_paroles") is not None
                   else _mu._nom(m))
            lines.append(_line("fal", Message("pricing.musique.piste" + ("" if usd else "_a_mesurer"), modele=lbl, n=n),
                               n, "piste", n * usd))
    elif kind == "vfx_ia":
        lines.append(_ligne_vfx(op, p))   # t188 (G6) : un geste VFX IA (registre vfx_ia)
    elif kind == "objets3d":
        lines.append(_ligne_objets3d(op, p))   # t189 (G7) : le storyboard 3D (SAM 3 objets / corps)
    elif kind == "sfx_video":
        lines.append(_ligne_sfx(op, p))   # t187 (G5) : une vidéo -> son bruitage (registre sfx_service)
    elif kind == "sfx" and str(op.get("modele") or "") not in ("", "elevenlabs-direct"):
        lines.append(_ligne_sfx(op, p))   # t187 (G5) : un modèle fal du registre ; sans `modele` : ElevenLabs direct
    elif kind == "sfx":
        n = max(1, min(4, int(op.get("n", op.get("variations", op.get("echantillons", 1))) or 1)))
        d = op.get("duration_s", op.get("secondes"))
        if d not in (None, "", 0):
            # t187 : la durée bornée comme generate_sfx (0,5-22 s) — le devis ne chiffre que ce qui part
            d = max(0.5, min(22.0, float(d)))
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
