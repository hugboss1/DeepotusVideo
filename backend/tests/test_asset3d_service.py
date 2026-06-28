from app.services.asset3d_service import (
    view_prompts, ENGINES, build_engine_args, parse_engine_result,
)


def test_view_prompts_count_and_subject():
    ps = view_prompts(3, "a knight")
    assert len(ps) == 3
    assert all("a knight" in p for p in ps)
    assert "front" in ps[0].lower() and "back" in ps[1].lower()


def test_view_prompts_clamped():
    assert len(view_prompts(0, "")) == 1
    assert len(view_prompts(9, "")) == 4


def test_engines_registry_has_fal_models():
    for k in ("tripo", "hunyuan", "trellis", "rodin", "triposr"):
        assert k in ENGINES and ENGINES[k]["endpoint"].startswith(("fal-ai/", "tripo3d/"))


def test_build_args_tripo_includes_image_and_format():
    args = build_engine_args("tripo", ["https://x/img.png"], {"format": "glb", "textures": True, "quality": "standard"})
    assert args.get("image_url") == "https://x/img.png" or args.get("image_urls")
    assert "glb" in str(args).lower()


def test_parse_result_picks_mesh_and_textures():
    res = {"model_mesh": {"url": "https://x/m.glb"}, "textures": [{"url": "https://x/t.png"}]}
    out = parse_engine_result("rodin", res)
    assert out["mesh_url"].endswith(".glb") and out["texture_urls"] == ["https://x/t.png"]
