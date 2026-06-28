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
