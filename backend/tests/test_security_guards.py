"""Non-régression des gardes de sécurité (audit 2026-08).

Chaque test correspond à une faille réellement présente avant l'audit ; ils
existent pour qu'elle ne puisse pas revenir en silence.
"""
import pytest


# ---- Traversée de chemin sur les noms de média -------------------------------
# Avant: `settings.images_path / request.image_filename` sans validation. Un
# chemin absolu remplace la base (sémantique pathlib) et `..\..` en sort ; le
# fichier résolu était ensuite envoyé chez fal.ai / HeyGen.

ESCAPES = [
    r"C:\Users\someone\Documents\secret.png",
    r"..\..\..\Windows\System32\drivers\etc\hosts",
    "../../etc/passwd",
    "sub/dir/img.png",
    r"sub\dir\img.png",
    "/abs/img.png",
    "..",
    "",
]


@pytest.mark.parametrize("bad", ESCAPES)
def test_generate_request_rejects_path_components(bad):
    from pydantic import ValidationError
    from app.models.schemas import GenerateRequest
    with pytest.raises(ValidationError):
        GenerateRequest(image_filename=bad, custom_prompt="x")


@pytest.mark.parametrize("good", [
    "gen_ab12cd34.png", "news_1234abcd.png", "my shot 01.jpg", "éclair_v2.webp",
])
def test_generate_request_accepts_plain_filenames(good):
    from app.models.schemas import GenerateRequest
    assert GenerateRequest(image_filename=good, custom_prompt="x").image_filename == good


def test_end_frame_and_heygen_image_are_guarded_too():
    from pydantic import ValidationError
    from app.models.schemas import GenerateRequest, GenerateHeyGenImageRequest
    with pytest.raises(ValidationError):
        GenerateRequest(image_filename="a.png", custom_prompt="x",
                        image_filename_end=r"C:\evil.png")
    with pytest.raises(ValidationError):
        GenerateHeyGenImageRequest(image_filename=r"..\..\secret.png",
                                   script="hi", voice_id="v1")


def test_cinematic_reference_images_are_guarded():
    from pydantic import ValidationError
    from app.models.schemas import GenerateHeyGenCinematicRequest
    with pytest.raises(ValidationError):
        GenerateHeyGenCinematicRequest(prompt="p", look_ids=["l1"],
                                       reference_images=["ok.png", r"..\out.png"])


# ---- SSRF --------------------------------------------------------------------
# Avant: /images/fetch n'avait aucun garde, et celui de /images/import-url ne
# regardait que l'hôte d'origine (une URL publique pouvait rediriger vers
# 127.0.0.1).

@pytest.mark.parametrize("host,private", [
    ("127.0.0.1", True), ("localhost", True), ("192.168.1.1", True),
    ("10.0.0.5", True), ("172.16.0.1", True), ("169.254.169.254", True),
    ("::1", True), ("printer.local", True), ("", True),
    ("example.com", False), ("8.8.8.8", False), ("v3.fal.media", False),
])
def test_private_host_detection(host, private):
    from app.api.routes import _is_private_host
    assert _is_private_host(host) is private


def test_redirect_to_private_address_is_blocked():
    # coroutine pilotée à la main : la suite n'installe pas pytest-asyncio
    import asyncio
    import httpx
    from fastapi import HTTPException
    from app.api.routes import _block_private_redirect

    def hop(location):
        return httpx.Response(302, headers={"location": location},
                              request=httpx.Request("GET", "https://example.com/i.png"))

    with pytest.raises(HTTPException):
        asyncio.run(_block_private_redirect(hop("http://127.0.0.1:8765/admin")))
    with pytest.raises(HTTPException):
        asyncio.run(_block_private_redirect(hop("http://169.254.169.254/latest/meta-data/")))
    # une redirection publique reste permise
    asyncio.run(_block_private_redirect(hop("https://cdn.example.com/i.png")))


# ---- Injection de filtergraph ffmpeg ------------------------------------------
# Avant: le chemin de LUT .cube entrait dans -filter_complex avec un simple
# échappement de ':'. Une apostrophe sortait du filtre (`movie=` lit alors
# n'importe quel fichier local dans le rendu).

@pytest.mark.parametrize("bad", [
    r"..\..\..\Windows\win.ini",
    "/etc/passwd",
    "evil.cube'; movie=x.mp4[a];[a]null",
    "sub/dir/x.cube",
    "notalut.txt",
    "",
])
def test_lut_path_rejects_escapes_and_injection(bad):
    from app.services.effects_engine import _lut_path
    assert _lut_path(bad) is None


def test_grade_falls_back_to_preset_instead_of_injecting():
    from app.services.effects_engine import build_chain
    chain = " ".join(build_chain(
        [{"type": "grade", "file": "x.cube'; movie=/etc/passwd[z]"}],
        "in", "out", "u", {}))
    assert "movie=" not in chain
    assert "lut3d" not in chain          # aucun LUT valide -> preset


def test_lut_path_accepts_a_real_cube_in_the_lut_dir(tmp_path, monkeypatch):
    from app.config import settings
    from app.services import effects_engine
    monkeypatch.setattr(type(settings), "luts_path", property(lambda self: tmp_path))
    (tmp_path / "teal.cube").write_text("LUT_3D_SIZE 2\n", encoding="utf-8")
    assert effects_engine._lut_path("teal.cube") == tmp_path / "teal.cube"
    assert effects_engine._lut_path("absent.cube") is None


# ---- Fuite du token Telegram --------------------------------------------------
# Avant: les erreurs httpx contiennent l'URL complète (token inclus) et étaient
# stockées sur le post, affichées dans l'UI et journalisées.

def test_telegram_token_is_scrubbed_from_errors(monkeypatch):
    from app.config import settings
    from app.services.marketing import _scrub_token
    token = "123456789:AAFakeTokenForTestingOnly_abcdef"
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", token)
    msg = f"ConnectError: https://api.telegram.org/bot{token}/sendVideo failed"
    out = _scrub_token(msg)
    assert token not in out and "AAFakeTokenForTestingOnly" not in out
    assert "sendVideo" in out          # le message reste exploitable


def test_scrub_token_works_without_a_configured_token(monkeypatch):
    from app.config import settings
    from app.services.marketing import _scrub_token
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    out = _scrub_token("GET /bot987654321:AAAnotherToken_xyz/sendMessage -> 401")
    assert "AAAnotherToken_xyz" not in out


# ---- Confinement des assets de template ---------------------------------------

def test_brand_mark_cannot_escape_the_templates_dir(tmp_path, monkeypatch):
    from app.services.template_service import TemplateEngine
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    builtin = tmp_path / "templates"
    (builtin / "marks").mkdir(parents=True)
    (builtin / "marks" / "logo.png").write_bytes(b"x")
    eng = TemplateEngine()
    monkeypatch.setattr(eng, "builtin_dir", builtin)
    assert eng.mark_path("marks/logo.png") == (builtin / "marks" / "logo.png").resolve()
    assert eng.mark_path("../outside.png") is None
