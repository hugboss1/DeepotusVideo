"""Chantier W-a — nœud vidéo multi-modèles (plan §1) : registre VIDEO_MODELS,
mapping modèle→endpoint/provider, clamps caps, client Google Veo, pricing par
modèle, schémas video_model, endpoint /video-models.

Réécrit le 27/09 (retours-ia, tâche 5) : le défaut épinglé passe de
`seedance-v1-pro` à `seedance-2.5`, et un modèle VIDE ne vaut plus le forfait
hérité 0,04 $/s mais le tarif du défaut ; le forfait ne s'atteint plus que
par le drapeau `legacy` (historique des jobs d'avant la colonne). Style des
bancs du dépôt : `check(label, cond, detail)`, ligne `=== N passed, M
failed ===`, code de sortie. La garde de coût est tenue par
`test_seedance_garde.py`.

Run: & $PY tests/test_video_models.py   (un processus, depuis backend/)
"""
import asyncio
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
_tmp = tempfile.mkdtemp(prefix="vmodels_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp          # jamais le .env de l'utilisateur
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ.pop("GEMINI_API_KEY", None)  # boot without Google key (flip later)
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.config import settings                                    # noqa: E402
from app.services.fal_service import (                             # noqa: E402
    DEFAULT_VIDEO_MODEL, SEEDANCE_LITE_I2V, SEEDANCE_PRO_I2V,
    VIDEO_MODELS, build_fal_args, clamp_duration, clamp_resolution,
    resolve_video_model)
from app.services import pricing                                   # noqa: E402
from app.services.google_video import GoogleVeoClient              # noqa: E402
from app.models.schemas import (GenerateRequest, GenerateBatchRequest,  # noqa: E402
                                TemplateSlotValue)
from app.services.storage import V1_2_NEW_COLUMNS, JobRecord       # noqa: E402

ok = fail = 0
_plantages = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def temoin(e):
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


def args(model_id, **kw):
    """(endpoint, args, notes) ou un témoin distinguable si ça lève."""
    try:
        return build_fal_args(model_id, **kw)
    except Exception as e:  # noqa: BLE001
        return temoin(e), {}, []


EXPECTED_IDS = {
    "seedance-v1-pro", "seedance-2", "seedance-2-fast", "seedance-2.5",
    "kling-v3-pro", "kling-v3-standard", "pixverse-v6",
    "veo-3.1-fast-fal", "veo-3.1-google", "veo-3.1-fast-google",
    "veo-3.1-lite-google",
}

# ── registre ────────────────────────────────────────────────────────────────
print("\n[registre]")
check("registre_ids", set(VIDEO_MODELS) == EXPECTED_IDS, repr(set(VIDEO_MODELS) ^ EXPECTED_IDS))
check("defaut_seedance_25", DEFAULT_VIDEO_MODEL == "seedance-2.5", repr(DEFAULT_VIDEO_MODEL))
check("ancien_defaut_toujours_au_registre", "seedance-v1-pro" in VIDEO_MODELS)
_cles = ("label", "provider", "family", "endpoint", "durations",
         "ratios", "resolutions", "end_image", "seed", "audio_param")
_manque = [(mid, k) for mid, m in VIDEO_MODELS.items() for k in _cles if k not in m]
check("registre_forme_complete", _manque == [], repr(_manque))
check("registre_providers", all(m["provider"] in ("fal", "google") for m in VIDEO_MODELS.values()))
check("registre_durees_non_vides", all(m["durations"] for m in VIDEO_MODELS.values()))
_sans_prix = [mid for mid in VIDEO_MODELS if pricing.video_rate(mid, "1080p") is None]
check("chaque_modele_a_un_prix", _sans_prix == [], repr(_sans_prix))

# ── résolution d'id ─────────────────────────────────────────────────────────
print("\n[resolve]")
check("resolve_none_defaut", resolve_video_model(None)["id"] == DEFAULT_VIDEO_MODEL)
check("resolve_vide_defaut", resolve_video_model("")["id"] == DEFAULT_VIDEO_MODEL)
check("resolve_kling_endpoint",
      resolve_video_model("kling-v3-pro")["endpoint"] == "fal-ai/kling-video/v3/pro/image-to-video")
try:
    resolve_video_model("nope-model")
    _err = "aucune erreur"
except ValueError as e:
    _err = str(e)
check("resolve_inconnu_leve_et_liste", "Unknown video model" in _err and "seedance-2" in _err, repr(_err))

# ── clamps ──────────────────────────────────────────────────────────────────
print("\n[clamps]")
veo = resolve_video_model("veo-3.1-fast-fal")
check("veo_4_exact", clamp_duration(veo, 4) == 4)
check("veo_5_arrondi_6", clamp_duration(veo, 5) == 6)
check("veo_60_plafond_8", clamp_duration(veo, 60) == 8)
pix = resolve_video_model("pixverse-v6")
check("pixverse_3_5_et_6_8", clamp_duration(pix, 3) == 5 and clamp_duration(pix, 6) == 8)
sd2 = resolve_video_model("seedance-2")
check("seedance2_3_4_et_12_12", clamp_duration(sd2, 3) == 4 and clamp_duration(sd2, 12) == 12)
check("fast_1080_vers_720",
      clamp_resolution(resolve_video_model("seedance-2-fast"), "1080p") == "720p")
check("kling_sans_resolution",
      clamp_resolution(resolve_video_model("kling-v3-pro"), "1080p") is None)

# ── arguments par famille ───────────────────────────────────────────────────
print("\n[build_fal_args]")
ep, a, _ = args("seedance-v1-pro", image_url="u", prompt="p", negative_prompt="n",
                duration=5, aspect_ratio="9:16", resolution="1080p", seed=42)
check("v1_pro_contrat_historique",
      ep == SEEDANCE_PRO_I2V and a == {"image_url": "u", "prompt": "p", "duration": 5,
                                       "aspect_ratio": "9:16", "resolution": "1080p",
                                       "negative_prompt": "n", "seed": 42}, f"{ep} {a}")
ep, a, _ = args("seedance-v1-pro", image_url="u", prompt="p", end_image_url="e",
                duration=5, aspect_ratio="9:16", resolution="720p")
check("v1_lite_premiere_derniere", ep == SEEDANCE_LITE_I2V and a.get("end_image_url") == "e",
      f"{ep} {a}")

ep, a, notes = args("seedance-2", image_url="u", prompt="p", negative_prompt="n",
                    duration=3, aspect_ratio="9:16", resolution="1080p", seed=7)
check("seedance2_endpoint", ep == "bytedance/seedance-2.0/image-to-video", repr(ep))
check("seedance2_duree_4_audio_off", a.get("duration") == 4 and a.get("generate_audio") is False, repr(a))
check("seedance2_sans_seed_ni_negatif", "seed" not in a and "negative_prompt" not in a, repr(a))
check("seedance2_note_seed", any("seed" in n for n in notes), repr(notes))
check("seedance2_ratio_resolution", a.get("aspect_ratio") == "9:16" and a.get("resolution") == "1080p", repr(a))

# Seedance 2.5 : durées natives 4..30 s, ratio « auto » seulement (l'endpoint
# suit l'image), 480p/720p au registre (1080p non chiffré par fal).
ep, a, notes = args("seedance-2.5", image_url="u", prompt="p", negative_prompt="n",
                    end_image_url="e", duration=31, aspect_ratio="9:16",
                    resolution="1080p", seed=7)
check("s25_endpoint", ep == "bytedance/seedance-2.5/image-to-video", repr(ep))
check("s25_plafond_natif_30", a.get("duration") == 30, repr(a))
check("s25_1080_vers_720", a.get("resolution") == "720p", repr(a))
check("s25_pas_de_ratio", "aspect_ratio" not in a, repr(a))
check("s25_premiere_derniere", a.get("end_image_url") == "e", repr(a))
check("s25_audio_off", a.get("generate_audio") is False, repr(a))
check("s25_sans_seed_ni_negatif", "seed" not in a and "negative_prompt" not in a, repr(a))
check("s25_notes_seed_et_resolution",
      any("seed" in n for n in notes) and any("resolution" in n for n in notes), repr(notes))
_, a2, _ = args("seedance-2.5", image_url="u", prompt="p", duration=17,
                aspect_ratio="9:16", resolution="480p")
check("s25_17s_480p_tels_quels", a2.get("duration") == 17 and a2.get("resolution") == "480p", repr(a2))

ep, a, _ = args("kling-v3-standard", image_url="u", prompt="p", negative_prompt="n",
                end_image_url="e", duration=7, aspect_ratio="1:1", resolution="1080p")
check("kling_endpoint", ep == "fal-ai/kling-video/v3/standard/image-to-video", repr(ep))
check("kling_start_image", a.get("start_image_url") == "u" and "image_url" not in a, repr(a))
check("kling_sans_ratio_ni_resolution", "aspect_ratio" not in a and "resolution" not in a, repr(a))
check("kling_fin_duree_audio_negatif",
      a.get("end_image_url") == "e" and a.get("duration") == 7
      and a.get("generate_audio") is False and a.get("negative_prompt") == "n", repr(a))

ep, a, _ = args("pixverse-v6", image_url="u", prompt="p", duration=6,
                aspect_ratio="9:16", resolution="720p", seed=5)
check("pixverse", ep == "fal-ai/pixverse/v6/image-to-video" and a.get("duration") == 8
      and a.get("generate_audio_switch") is False and a.get("seed") == 5, f"{ep} {a}")
ep, a, notes = args("veo-3.1-fast-fal", image_url="u", prompt="p", duration=8,
                    aspect_ratio="1:1", resolution="1080p", seed=9)
check("veo_fal_endpoint", ep == "fal-ai/veo3.1/fast/image-to-video", repr(ep))
check("veo_fal_duree_chaine", a.get("duration") == "8s", repr(a))
check("veo_fal_ratio_1_1_ecarte", "aspect_ratio" not in a and any("ratio" in n for n in notes),
      f"{a} {notes}")
check("veo_fal_resolution_seed_audio",
      a.get("resolution") == "1080p" and a.get("seed") == 9 and a.get("generate_audio") is False,
      repr(a))

try:
    build_fal_args("pixverse-v6", image_url="u", prompt="p", end_image_url="e",
                   duration=5, aspect_ratio="9:16", resolution="720p")
    _err = "aucune erreur"
except ValueError as e:
    _err = str(e)
check("garde_image_de_fin", "end frame" in _err, repr(_err))
try:
    build_fal_args("veo-3.1-google", image_url="u", prompt="p",
                   duration=4, aspect_ratio="9:16", resolution="720p")
    _err = "aucune erreur"
except ValueError as e:
    _err = str(e)
check("garde_provider_google", "not a fal model" in _err, repr(_err))

# ── Google ──────────────────────────────────────────────────────────────────
print("\n[google]")
from app.services.google_video import build_google_params   # noqa: E402
gp = build_google_params(8, "9:16", "720p")
check("google_params", gp == {"aspectRatio": "9:16", "durationSeconds": 8, "resolution": "720p"}, repr(gp))
check("google_pas_de_negatif", "negativePrompt" not in gp)
gp2 = build_google_params(6, "1:1", "4k")
check("google_clamps", gp2.get("aspectRatio") == "9:16" and gp2.get("resolution") == "720p", repr(gp2))
settings.GEMINI_API_KEY = ""
try:
    GoogleVeoClient._require_key()
    _err = "aucune erreur"
except RuntimeError as e:
    _err = str(e)
check("google_sans_cle_erreur_claire", "GEMINI_API_KEY" in _err, repr(_err))
png = pathlib.Path(_tmp, "images", "a.png"); png.write_bytes(b"\x89PNG_x")
jpg = pathlib.Path(_tmp, "images", "b.jpg"); jpg.write_bytes(b"\xff\xd8_x")
p1 = GoogleVeoClient._image_part(png)
p2 = GoogleVeoClient._image_part(jpg)
check("google_mime", p1["mimeType"] == "image/png" and p2["mimeType"] == "image/jpeg")
check("google_base64", bool(p1["bytesBase64Encoded"]))
r = {"video": {"url": "https://x/f:download?alt=media"}}
check("google_extract_url", GoogleVeoClient.extract_video_url(r) == "https://x/f:download?alt=media")
check("google_extract_vide", GoogleVeoClient.extract_video_url({}) is None)
check("google_pas_de_seed", GoogleVeoClient.extract_seed(r) is None)
check("google_endpoints", all(VIDEO_MODELS[m]["endpoint"].startswith("veo-3.1")
                              for m in ("veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google")))

# ── pricing ─────────────────────────────────────────────────────────────────
print("\n[pricing]")
p = pricing.load()
check("prix_s2_720", pricing.video_rate("seedance-2", "720p", p) == 0.3034)
check("prix_s2_1080", pricing.video_rate("seedance-2", "1080p", p) == 0.682)
check("prix_kling_forfait", pricing.video_rate("kling-v3-pro", "1080p", p) == 0.112)
check("prix_fast_1080_colonne_max", pricing.video_rate("seedance-2-fast", "1080p", p) == 0.2419)
check("prix_s25_480", pricing.video_rate("seedance-2.5", "480p", p) == 0.2205)
check("prix_s25_720", pricing.video_rate("seedance-2.5", "720p", p) == 0.473)
check("prix_s25_1080_colonne_max", pricing.video_rate("seedance-2.5", "1080p", p) == 0.473)
check("prix_inconnu_none", pricing.video_rate("unknown-model", "1080p", p) is None)
try:
    line = pricing.estimate({"kind": "seedance", "duration_s": 5, "model": "veo-3.1-lite-google",
                             "resolution": "720p"}, p)["breakdown"][0]
except Exception as e:  # noqa: BLE001
    line = {"_temoin": temoin(e)}
check("estimation_modele_nomme", line.get("provider") == "google"
      and abs(line.get("usd", -1) - 0.5) < 1e-6 and "Veo 3.1 Lite" in line.get("label", ""), repr(line))
# modèle absent -> le DÉFAUT du registre (2.5), plus le forfait 0,04
try:
    l2 = pricing.estimate({"kind": "seedance", "duration_s": 5}, p)["breakdown"][0]
except Exception as e:  # noqa: BLE001
    l2 = {"_temoin": temoin(e)}
_attendu = round(5 * 0.473, 4)
check("estimation_sans_modele_tarif_25", l2.get("usd") == _attendu and "Seedance 2.5" in l2.get("label", ""),
      f"{l2} vs {_attendu}")
check("estimation_sans_modele_jamais_forfait", l2.get("usd") != round(5 * p["seedance_usd_per_s"], 4),
      repr(l2))
# le forfait reste atteignable par le drapeau explicite (historique)
try:
    l3 = pricing.estimate({"kind": "seedance", "duration_s": 5, "legacy": True}, p)["breakdown"][0]
except Exception as e:  # noqa: BLE001
    l3 = {"_temoin": temoin(e)}
check("estimation_legacy_forfait", l3.get("label") == "Seedance video"
      and abs(l3.get("usd", -1) - 5 * p["seedance_usd_per_s"]) < 1e-9, repr(l3))

# ── schémas et base ─────────────────────────────────────────────────────────
print("\n[schemas]")
rq = GenerateRequest(image_filename="a.png", video_model="kling-v3-pro")
check("schema_video_model", rq.video_model == "kling-v3-pro")
check("schema_video_model_none", GenerateRequest(image_filename="a.png").video_model is None)
_mu = getattr(GenerateRequest(image_filename="a.png"), "max_usd", "CHAMP ABSENT")
check("schema_max_usd_absent_par_defaut", _mu is None, repr(_mu))
b = GenerateBatchRequest(image_filename="a.png", video_model="seedance-2", variations_count=2)
check("schema_lot_herite", b.video_model == "seedance-2")
sv = TemplateSlotValue(source_kind="seedance", seedance=rq)
check("schema_slot_porte_modele", sv.seedance.video_model == "kling-v3-pro")
check("base_colonne_video_model", hasattr(JobRecord, "video_model")
      and ("video_model", "VARCHAR(48)") in V1_2_NEW_COLUMNS)

# ── /video-models ───────────────────────────────────────────────────────────
print("\n[/video-models]")
from app.api.routes import list_video_models   # noqa: E402
settings.GEMINI_API_KEY = ""
try:
    out = asyncio.run(list_video_models())
except Exception as e:  # noqa: BLE001
    out = {"_temoin": temoin(e)}
check("endpoint_defaut_25", out.get("default") == "seedance-2.5", repr(out.get("default")))
by_id = {m["id"]: m for m in out.get("models") or []}
check("endpoint_ids", set(by_id) == EXPECTED_IDS, repr(set(by_id) ^ EXPECTED_IDS))
check("endpoint_v1_dispo_avec_fal", (by_id.get("seedance-v1-pro") or {}).get("available") is True)
check("endpoint_veo_google_indispo", (by_id.get("veo-3.1-google") or {}).get("available") is False)
check("endpoint_veo_google_audio_inclus", (by_id.get("veo-3.1-google") or {}).get("audio_included") is True)
check("endpoint_prix_s2", ((by_id.get("seedance-2") or {}).get("usd_per_s") or {}).get("1080p") == 0.682)
check("endpoint_prix_s25", ((by_id.get("seedance-2.5") or {}).get("usd_per_s") or {}).get("720p") == 0.473)
check("endpoint_s25_dispo", (by_id.get("seedance-2.5") or {}).get("available") is True)
settings.GEMINI_API_KEY = "test-google"
try:
    out2 = asyncio.run(list_video_models())
except Exception as e:  # noqa: BLE001
    out2 = {"_temoin": temoin(e)}
check("endpoint_cle_google_bascule",
      {m["id"]: m for m in out2.get("models") or []}.get("veo-3.1-google", {}).get("available") is True)
settings.GEMINI_API_KEY = ""

check("aucun_appel_n_a_plante", _plantages == 0, f"{_plantages} appel(s) ont levé")
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
