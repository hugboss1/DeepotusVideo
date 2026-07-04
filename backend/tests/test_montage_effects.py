"""Sequential-montage (Concatenate) must apply Effects-node output:
global post_effects (whole render) AND per-region effects (a targeted source).

Regression: build_sequential_command ignored both, so an Effects node on a
Concatenate graph rendered with no effect. Uses fixed-length clips + fake paths
so it needs no ffmpeg/ffprobe. Run: <embedded python> backend/tests/test_montage_effects.py
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.template_service import build_sequential_command

# build_sequential_command only checks that slot paths EXIST (fixed length_mode
# means no ffprobe), so two empty temp files are enough.
_dir = tempfile.mkdtemp()
_A = os.path.join(_dir, "a.mp4"); open(_A, "wb").close()
_B = os.path.join(_dir, "b.mp4"); open(_B, "wb").close()
_OUT = os.path.join(_dir, "out.mp4")


def _tpl(post=None, region0_effects=None):
    r0 = {"id": "r0", "type": "video_slot", "act": 0, "slot_name": "clip0",
          "length_s": 3, "length_mode": "fixed", "transition": {"type": "cut"}}
    r1 = {"id": "r1", "type": "video_slot", "act": 1, "slot_name": "clip1",
          "length_s": 3, "length_mode": "fixed",
          "transition": {"type": "crossfade", "duration_s": 0.4}}
    if region0_effects:
        r0["effects"] = region0_effects
    tpl = {"canvas": {"width": 1080, "height": 1920, "fps": 30,
                      "background_color": "#000000"},
           "regions": [r0, r1]}
    if post:
        tpl["post_effects"] = post
    return tpl


SV = {"clip0": {"path": _A}, "clip1": {"path": _B}}


def main():
    # 1) Global post-effects ("apply on the whole render").
    cmd, _ = build_sequential_command(
        None, _tpl(post=[{"type": "grade", "preset": "matrix"}]), SV, _OUT)
    fg = " ".join(cmd)
    assert "postfx" in fg, "global post_effects NOT applied in sequential montage"

    # 2) Per-region effect (a specific source targeted).
    cmd, _ = build_sequential_command(
        None, _tpl(region0_effects=[{"type": "grade", "preset": "noir"}]),
        SV, _OUT)
    fg = " ".join(cmd)
    assert "n0pre" in fg, "per-region effect NOT applied to montage act 0"

    # 3) No effects -> no effect labels (unchanged behaviour).
    cmd, _ = build_sequential_command(None, _tpl(), SV, _OUT)
    fg = " ".join(cmd)
    assert "postfx" not in fg and "n0pre" not in fg, "unexpected effect labels"

    print("MONTAGE EFFECTS TEST: PASS")


main()
