"""Chantier W-a — nœud vidéo multi-modèles (plan §1) : registre VIDEO_MODELS,
mapping modèle→endpoint/provider, clamps caps, client Google Veo, pricing par
modèle, schémas video_model, endpoint /video-models.
Run: <embedded python> backend/tests/test_video_models.py"""
import asyncio
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.pop("GEMINI_API_KEY", None)  # boot without Google key (flip later)
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


EXPECTED_IDS = {
    "seedance-v1-pro", "seedance-2", "seedance-2-fast", "seedance-2.5",
    "kling-v3-pro", "kling-v3-standard", "pixverse-v6",
    "veo-3.1-fast-fal", "veo-3.1-google", "veo-3.1-fast-google",
    "veo-3.1-lite-google",
}


def test_registry_shape():
    assert set(VIDEO_MODELS) == EXPECTED_IDS, set(VIDEO_MODELS) ^ EXPECTED_IDS
    assert DEFAULT_VIDEO_MODEL == "seedance-v1-pro"
    for mid, m in VIDEO_MODELS.items():
        for k in ("label", "provider", "family", "endpoint", "durations",
                  "ratios", "resolutions", "end_image", "seed", "audio_param"):
            assert k in m, f"{mid} missing {k}"
        assert m["provider"] in ("fal", "google"), mid
        assert m["durations"], mid
        # every model has a pricing row (audio-off column / flat)
        assert pricing.video_rate(mid, "1080p") is not None, f"no price for {mid}"


def test_resolve():
    assert resolve_video_model(None)["id"] == DEFAULT_VIDEO_MODEL
    assert resolve_video_model("")["id"] == DEFAULT_VIDEO_MODEL
    assert resolve_video_model("kling-v3-pro")["endpoint"] == \
        "fal-ai/kling-video/v3/pro/image-to-video"
    try:
        resolve_video_model("nope-model")
        raise AssertionError("unknown id must raise")
    except ValueError as e:
        assert "Unknown video model" in str(e) and "seedance-2" in str(e)


def test_clamps():
    veo = resolve_video_model("veo-3.1-fast-fal")
    assert clamp_duration(veo, 4) == 4          # exact
    assert clamp_duration(veo, 5) == 6          # round up to next native
    assert clamp_duration(veo, 60) == 8         # cap at max (ffmpeg extends)
    pix = resolve_video_model("pixverse-v6")
    assert clamp_duration(pix, 3) == 5 and clamp_duration(pix, 6) == 8
    sd2 = resolve_video_model("seedance-2")
    assert clamp_duration(sd2, 3) == 4 and clamp_duration(sd2, 12) == 12
    # resolutions: 720p-only model downgrades 1080p; kling has no param
    fast = resolve_video_model("seedance-2-fast")
    assert clamp_resolution(fast, "1080p") == "720p"
    assert clamp_resolution(resolve_video_model("kling-v3-pro"), "1080p") is None


def test_args_seedance1_legacy():
    # byte-identical legacy contract: pro single image / lite first-last
    ep, args, _ = build_fal_args(
        "seedance-v1-pro", image_url="u", prompt="p", negative_prompt="n",
        duration=5, aspect_ratio="9:16", resolution="1080p", seed=42)
    assert ep == SEEDANCE_PRO_I2V
    assert args == {"image_url": "u", "prompt": "p", "duration": 5,
                    "aspect_ratio": "9:16", "resolution": "1080p",
                    "negative_prompt": "n", "seed": 42}
    ep2, args2, _ = build_fal_args(
        "seedance-v1-pro", image_url="u", prompt="p", end_image_url="e",
        duration=5, aspect_ratio="9:16", resolution="720p")
    assert ep2 == SEEDANCE_LITE_I2V and args2["end_image_url"] == "e"


def test_args_seedance2():
    ep, args, notes = build_fal_args(
        "seedance-2", image_url="u", prompt="p", negative_prompt="n",
        duration=3, aspect_ratio="9:16", resolution="1080p", seed=7)
    assert ep == "bytedance/seedance-2.0/image-to-video"
    assert args["duration"] == 4 and args["generate_audio"] is False
    assert "seed" not in args and "negative_prompt" not in args
    assert any("seed" in n for n in notes)
    assert args["aspect_ratio"] == "9:16" and args["resolution"] == "1080p"


def test_args_seedance25():
    # Seedance 2.5 (ajouté 28/08, fal OpenAPI relu le jour même) : durées
    # natives 4..30 s, ratio « auto » SEULEMENT (l'endpoint suit l'image ->
    # aucun param envoyé), 480p/720p au registre — 1080p est accepté par
    # l'endpoint mais fal ne publie pas son $/s (facturation aux tokens,
    # seuls 480p/720p sont chiffrés) : hors registre tant que le chiffre
    # n'est pas affiché, et le clamp le DIT dans les notes.
    ep, args, notes = build_fal_args(
        "seedance-2.5", image_url="u", prompt="p", negative_prompt="n",
        end_image_url="e", duration=31, aspect_ratio="9:16",
        resolution="1080p", seed=7)
    assert ep == "bytedance/seedance-2.5/image-to-video"
    assert args["duration"] == 30                    # plafond natif 30 s
    assert args["resolution"] == "720p"              # 1080p -> 720p (prix)
    assert "aspect_ratio" not in args                # l'endpoint suit l'image
    assert args["end_image_url"] == "e"              # first-last supporté
    assert args["generate_audio"] is False           # l'app possède l'audio
    assert "seed" not in args and "negative_prompt" not in args
    assert any("seed" in n for n in notes)
    assert any("resolution" in n for n in notes)
    # une durée native mi-chemin passe telle quelle (4..30 continu)
    _, args2, _ = build_fal_args(
        "seedance-2.5", image_url="u", prompt="p", duration=17,
        aspect_ratio="9:16", resolution="480p")
    assert args2["duration"] == 17 and args2["resolution"] == "480p"


def test_args_kling():
    ep, args, _ = build_fal_args(
        "kling-v3-standard", image_url="u", prompt="p", negative_prompt="n",
        end_image_url="e", duration=7, aspect_ratio="1:1", resolution="1080p")
    assert ep == "fal-ai/kling-video/v3/standard/image-to-video"
    assert args["start_image_url"] == "u" and "image_url" not in args
    assert "aspect_ratio" not in args and "resolution" not in args
    assert args["end_image_url"] == "e" and args["duration"] == 7
    assert args["generate_audio"] is False and args["negative_prompt"] == "n"


def test_args_pixverse_and_veo():
    ep, args, _ = build_fal_args(
        "pixverse-v6", image_url="u", prompt="p", duration=6,
        aspect_ratio="9:16", resolution="720p", seed=5)
    assert ep == "fal-ai/pixverse/v6/image-to-video"
    assert args["duration"] == 8 and args["generate_audio_switch"] is False
    assert args["seed"] == 5
    ep, args, notes = build_fal_args(
        "veo-3.1-fast-fal", image_url="u", prompt="p", duration=8,
        aspect_ratio="1:1", resolution="1080p", seed=9)
    assert ep == "fal-ai/veo3.1/fast/image-to-video"
    assert args["duration"] == "8s"          # veo wants "Ns" strings
    assert "aspect_ratio" not in args        # 1:1 unsupported -> model default
    assert any("ratio" in n for n in notes)
    assert args["resolution"] == "1080p" and args["seed"] == 9
    assert args["generate_audio"] is False


def test_args_guards():
    try:  # end frame on a model without support -> clean error
        build_fal_args("pixverse-v6", image_url="u", prompt="p",
                       end_image_url="e", duration=5,
                       aspect_ratio="9:16", resolution="720p")
        raise AssertionError("end_image guard must raise")
    except ValueError as e:
        assert "end frame" in str(e)
    try:  # google model through the fal builder -> clean error
        build_fal_args("veo-3.1-google", image_url="u", prompt="p",
                       duration=4, aspect_ratio="9:16", resolution="720p")
        raise AssertionError("provider guard must raise")
    except ValueError as e:
        assert "not a fal model" in str(e)


def test_google_params():
    # Veo 3.1 previews REJECT negativePrompt (HTTP 400, probed 22/07) — the
    # params builder must never include it, and clamps ratio/resolution.
    from app.services.google_video import build_google_params
    p = build_google_params(8, "9:16", "720p")
    assert p == {"aspectRatio": "9:16", "durationSeconds": 8,
                 "resolution": "720p"}
    assert "negativePrompt" not in p
    p2 = build_google_params(6, "1:1", "4k")
    assert p2["aspectRatio"] == "9:16" and p2["resolution"] == "720p"


def test_google_client():
    # no key -> clean actionable error (job.error friendly)
    settings.GEMINI_API_KEY = ""
    try:
        GoogleVeoClient._require_key()
        raise AssertionError("missing key must raise")
    except RuntimeError as e:
        assert "GEMINI_API_KEY" in str(e)
    # image part: mime by extension, base64 payload
    png = pathlib.Path(_tmp, "images", "a.png"); png.write_bytes(b"\x89PNG_x")
    jpg = pathlib.Path(_tmp, "images", "b.jpg"); jpg.write_bytes(b"\xff\xd8_x")
    p1 = GoogleVeoClient._image_part(png)
    p2 = GoogleVeoClient._image_part(jpg)
    assert p1["mimeType"] == "image/png" and p2["mimeType"] == "image/jpeg"
    assert p1["bytesBase64Encoded"]
    # result contract mirrors the fal client
    r = {"video": {"url": "https://x/f:download?alt=media"}}
    assert GoogleVeoClient.extract_video_url(r) == "https://x/f:download?alt=media"
    assert GoogleVeoClient.extract_video_url({}) is None
    assert GoogleVeoClient.extract_seed(r) is None
    # registry endpoints exist on the google side
    for mid in ("veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"):
        assert VIDEO_MODELS[mid]["endpoint"].startswith("veo-3.1")


def test_pricing():
    p = pricing.load()
    assert pricing.video_rate("seedance-2", "720p", p) == 0.3034
    assert pricing.video_rate("seedance-2", "1080p", p) == 0.682
    assert pricing.video_rate("kling-v3-pro", "1080p", p) == 0.112   # flat "*"
    # 720p-only model asked at 1080p -> priced at its max column
    assert pricing.video_rate("seedance-2-fast", "1080p", p) == 0.2419
    # seedance-2.5 : 480p/720p chiffrés par fal ; 1080p demandé -> colonne max
    assert pricing.video_rate("seedance-2.5", "480p", p) == 0.2205
    assert pricing.video_rate("seedance-2.5", "720p", p) == 0.473
    assert pricing.video_rate("seedance-2.5", "1080p", p) == 0.473
    assert pricing.video_rate("unknown-model", "1080p", p) is None
    # estimate with a model routes label+provider through the registry
    est = pricing.estimate({"kind": "seedance", "duration_s": 5,
                            "model": "veo-3.1-lite-google",
                            "resolution": "720p"}, p)
    line = est["breakdown"][0]
    assert line["provider"] == "google" and abs(line["usd"] - 0.5) < 1e-6
    assert "Veo 3.1 Lite" in line["label"]
    # no model -> legacy line untouched (0.04 default $/s)
    est2 = pricing.estimate({"kind": "seedance", "duration_s": 5}, p)
    l2 = est2["breakdown"][0]
    assert l2["provider"] == "fal" and l2["label"] == "Seedance video"
    assert abs(l2["usd"] - 5 * p["seedance_usd_per_s"]) < 1e-9


def test_schemas_and_storage():
    r = GenerateRequest(image_filename="a.png", video_model="kling-v3-pro")
    assert r.video_model == "kling-v3-pro"
    assert GenerateRequest(image_filename="a.png").video_model is None
    b = GenerateBatchRequest(image_filename="a.png",
                             video_model="seedance-2", variations_count=2)
    assert b.video_model == "seedance-2"       # inherited by batch
    sv = TemplateSlotValue(source_kind="seedance", seedance=r)
    assert sv.seedance.video_model == "kling-v3-pro"  # template slots carry it
    # DB: mapped column + auto-migration entry for existing installs
    assert hasattr(JobRecord, "video_model")
    assert ("video_model", "VARCHAR(48)") in V1_2_NEW_COLUMNS


def test_video_models_endpoint():
    from app.api.routes import list_video_models
    settings.GEMINI_API_KEY = ""              # google unavailable
    out = asyncio.run(list_video_models())
    assert out["default"] == DEFAULT_VIDEO_MODEL
    by_id = {m["id"]: m for m in out["models"]}
    assert set(by_id) == EXPECTED_IDS
    assert by_id["seedance-v1-pro"]["available"] is True        # FAL_KEY set
    assert by_id["veo-3.1-google"]["available"] is False
    assert by_id["veo-3.1-google"]["audio_included"] is True
    assert by_id["seedance-2"]["usd_per_s"]["1080p"] == 0.682
    assert by_id["seedance-2.5"]["usd_per_s"]["720p"] == 0.473
    assert by_id["seedance-2.5"]["available"] is True
    settings.GEMINI_API_KEY = "test-google"   # key present -> flips available
    out2 = asyncio.run(list_video_models())
    assert {m["id"]: m for m in out2["models"]}["veo-3.1-google"]["available"] is True
    settings.GEMINI_API_KEY = ""


TESTS = [test_registry_shape, test_resolve, test_clamps,
         test_args_seedance1_legacy, test_args_seedance2, test_args_seedance25,
         test_args_kling,
         test_args_pixverse_and_veo, test_args_guards, test_google_params,
         test_google_client, test_pricing, test_schemas_and_storage,
         test_video_models_endpoint]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
