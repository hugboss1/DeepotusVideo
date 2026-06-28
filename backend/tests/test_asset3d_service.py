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


def test_pricing_asset3d():
    from app.services.pricing import estimate
    r = estimate({"kind": "asset3d", "engine": "tripo", "textures": True, "multiview": True, "views": 3})
    assert r["total_usd"] > 0
    cheap = estimate({"kind": "asset3d", "engine": "triposr", "multiview": False})["total_usd"]
    assert cheap < r["total_usd"]


def test_generate_asset3d_writes_files(tmp_path, monkeypatch):
    import asyncio
    from app.services import asset3d_service as A
    from app.config import settings
    monkeypatch.setattr(type(settings), "outputs_path", property(lambda self: tmp_path))
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "src.png").write_bytes(b"\x89PNG\r\n\x1a\n0000")

    async def fake_upload(p):
        return "https://fal/src.png"

    async def fake_run(engine, args):
        return {"mesh_url": "https://x/m.glb", "format_urls": {}, "texture_urls": [], "preview_url": "https://x/p.png"}

    def fake_download(url, dest):
        dest.write_bytes(b"FILE")
        return True

    monkeypatch.setattr(A, "_upload", fake_upload)
    monkeypatch.setattr(A, "_run_engine", fake_run)
    monkeypatch.setattr(A, "_download", fake_download)

    out = asyncio.run(A.generate_asset3d(
        {"image_filename": "src.png", "engine": "triposr", "multiview": False, "formats": ["glb"]}, "job1"))
    d = tmp_path / "assets3d" / "job1"
    assert (d / "model.glb").exists() and (d / "shot_0.png").exists()
    assert out["glb"].endswith("model.glb") and out["shots"] == ["shot_0.png"] and out["engine"] == "triposr"
