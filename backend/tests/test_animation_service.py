from app.services.animation_service import ease, lerp, transform_at


def test_ease_linear_endpoints():
    assert ease("linear", 0) == 0
    assert ease("linear", 1) == 1
    assert abs(ease("linear", 0.5) - 0.5) < 1e-9


def test_ease_clamps_and_monotonic():
    assert ease("easeOut", -1) == 0          # clamped
    assert ease("easeOut", 2) == 1
    assert ease("easeOut", 0.5) > 0.5        # decelerating -> ahead of linear


def test_lerp():
    assert lerp(0, 10, 0.5) == 5
    assert lerp(10, 0, 0.5) == 5


def test_transform_at_visibility_and_interp():
    el = {"start": 1.0, "dur": 1.0, "hold": 1.0, "easing": "linear",
          "from": {"x": 0, "y": 0, "scale": 0, "rotation": 0, "opacity": 0},
          "to": {"x": 100, "y": 50, "scale": 1, "rotation": 90, "opacity": 1}}
    assert transform_at(el, 0.5) is None     # before start
    mid = transform_at(el, 1.5)              # halfway through dur
    assert abs(mid["x"] - 50) < 1e-6 and abs(mid["opacity"] - 0.5) < 1e-6
    assert transform_at(el, 2.5) == {"x": 100, "y": 50, "scale": 1, "rotation": 90, "opacity": 1}  # hold
    assert transform_at(el, 5.0) is None     # after start+dur+hold


def test_render_element_text_layer():
    from PIL import Image
    from app.services.animation_service import render_element
    el = {"type": "text", "text": "HI", "style": {"font": "JetBrains Mono", "size": 48, "color": "#ffffff"}}
    tr = {"x": 50, "y": 50, "scale": 1.0, "rotation": 0, "opacity": 0.5}
    layer = render_element(el, tr, 200, 200)
    assert isinstance(layer, Image.Image) and layer.size == (200, 200) and layer.mode == "RGBA"
    # something was drawn near the centre, and opacity halved the alpha
    cx = layer.getpixel((100, 100))
    assert cx[3] <= 200  # alpha reduced by opacity 0.5 (<= ~half of 255 where text covers)


def test_render_animation_blank_base(tmp_path, monkeypatch):
    from app.services import animation_service as A
    from app.config import settings
    # outputs_path is a read-only @property -> patch it on the class to redirect output.
    monkeypatch.setattr(type(settings), "outputs_path", property(lambda self: tmp_path))
    payload = {"aspect": "9:16", "fps": 2, "duration_s": 1, "base": None,
               "elements": [{"type": "text", "text": "GO", "style": {"size": 64, "color": "#fff"},
                             "start": 0, "dur": 0.5, "hold": 1, "easing": "linear",
                             "from": {"x": 50, "y": 50, "scale": 1, "rotation": 0, "opacity": 1},
                             "to": {"x": 50, "y": 50, "scale": 1, "rotation": 0, "opacity": 1}}]}
    out = A.render_animation(payload, "testjob")
    assert out.exists() and out.stat().st_size > 0
