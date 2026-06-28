from pathlib import Path


def test_safe_rename_basic_and_extension(tmp_path, monkeypatch):
    from app.api import routes
    from app.config import settings
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "old.png").write_bytes(b"x")
    # extension enforced from the source even if omitted in new name
    assert routes._safe_rename_image("old.png", "hero") == "hero.png"
    assert (tmp_path / "hero.png").exists() and not (tmp_path / "old.png").exists()


def test_safe_rename_sanitizes_and_strips_path(tmp_path, monkeypatch):
    from app.api import routes
    from app.config import settings
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "a.png").write_bytes(b"x")
    # path components stripped, weird chars -> underscore, provided ext dropped (original kept)
    out = routes._safe_rename_image("a.png", "my/../bad@name.jpg")
    assert out == "bad_name.png" and (tmp_path / out).exists()


def test_safe_rename_collision_autosuffix(tmp_path, monkeypatch):
    from app.api import routes
    from app.config import settings
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    (tmp_path / "hero.png").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"x")
    assert routes._safe_rename_image("b.png", "hero") == "hero_2.png"


def test_safe_rename_missing_source(tmp_path, monkeypatch):
    from app.api import routes
    from app.config import settings
    monkeypatch.setattr(type(settings), "images_path", property(lambda self: tmp_path))
    try:
        routes._safe_rename_image("nope.png", "x")
        assert False, "should raise"
    except FileNotFoundError:
        pass
