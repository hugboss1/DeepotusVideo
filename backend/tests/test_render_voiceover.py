"""Chantier V-b — VO mixée au render (spec §6.2) : _resolve_voiceover,
merge réel ffmpeg (piste AAC), post-merge template, schémas `voiceover`.
Run: <embedded python> backend/tests/test_render_voiceover.py"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-11l")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "audio").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ffmpeg : PATH courant, sinon bin/ de l'app installée (spec §6.2).
if not shutil.which("ffmpeg"):
    _bin = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                        "DeepotusVideoGen", "bin")
    if os.path.isfile(os.path.join(_bin, "ffmpeg.exe")):
        os.environ["PATH"] = _bin + os.pathsep + os.environ["PATH"]

from app.services.pipeline import _resolve_voiceover, _apply_voiceover_post  # noqa: E402
from app.services.ffmpeg_service import FFmpegMerger                         # noqa: E402
from app.models.schemas import (GenerateRequest, GenerateHeyGenRequest,      # noqa: E402
                                GenerateHeyGenImageRequest,
                                TemplateRenderRequest)

AUDIO_DIR = pathlib.Path(_tmp, "audio")
WORK = pathlib.Path(_tmp, "work")
WORK.mkdir(exist_ok=True)


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"cmd failed: {' '.join(cmd)}\n{r.stderr[-800:]}"


def _probe_streams(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-400:]
    return json.loads(r.stdout).get("streams", [])


def _mk_video(dest, dur="1", with_audio=False):
    cmd = ["ffmpeg", "-y", "-f", "lavfi",
           "-i", f"testsrc=duration={dur}:size=320x240:rate=15"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=220:duration={dur}",
                "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)]
    _run(cmd)


def _mk_mp3(dest, dur="0.6", freq="440"):
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"sine=frequency={freq}:duration={dur}",
          "-c:a", "libmp3lame", str(dest)])


def test_resolve_voiceover():
    vo = AUDIO_DIR / "vo_ok.mp3"
    vo.write_bytes(b"ID3fake")
    # nominal : nom simple présent dans le dossier audio
    p = _resolve_voiceover({"file": "vo_ok.mp3"})
    assert p == vo, p
    # absent / invalides
    assert _resolve_voiceover({"file": "missing.mp3"}) is None
    assert _resolve_voiceover(None) is None
    assert _resolve_voiceover({}) is None
    assert _resolve_voiceover({"file": ""}) is None
    assert _resolve_voiceover("vo_ok.mp3") is None            # pas un dict
    # traversée : seul le basename est résolu, DANS le dossier audio
    evil = pathlib.Path(_tmp, "images", "evil.mp3")
    evil.write_bytes(b"ID3fake")
    assert _resolve_voiceover({"file": "../images/evil.mp3"}) is None
    sub = AUDIO_DIR / "evil.mp3"
    sub.write_bytes(b"ID3fake")
    p2 = _resolve_voiceover({"file": "../../anywhere/evil.mp3"})
    assert p2 == sub, p2                                      # basename → audio/


def test_schemas_accept_voiceover():
    g = GenerateRequest(image_filename="a.png", voiceover={"file": "vo.mp3"})
    assert g.voiceover == {"file": "vo.mp3"}
    assert GenerateRequest(image_filename="a.png").voiceover is None
    h = GenerateHeyGenRequest(avatar_id="av", voice_id="v", script="s",
                              voiceover={"file": "vo.mp3"})
    assert h.voiceover == {"file": "vo.mp3"}
    hi = GenerateHeyGenImageRequest(image_filename="a.png", script="s",
                                    voice_id="v", voiceover={"file": "vo.mp3"})
    assert hi.voiceover == {"file": "vo.mp3"}
    t = TemplateRenderRequest(template_id="tpl", slot_values={},
                              voiceover={"file": "vo.mp3"})
    assert t.voiceover == {"file": "vo.mp3"}
    assert TemplateRenderRequest(template_id="tpl", slot_values={}).voiceover is None


def test_merge_vo_real():
    v = WORK / "v_silent.mp4"
    _mk_video(v)
    vo = AUDIO_DIR / "vo_sine.mp3"
    _mk_mp3(vo)
    out = WORK / "merged_vo.mp4"
    FFmpegMerger.merge(v, _resolve_voiceover({"file": "vo_sine.mp3"}), out)
    st = _probe_streams(out)
    kinds = {s["codec_type"]: s["codec_name"] for s in st}
    assert kinds.get("audio") == "aac", st                    # piste VO en AAC
    assert kinds.get("video") == "h264", st


def test_merge_vo_over_music():
    v = WORK / "v_silent2.mp4"
    _mk_video(v)
    vo = AUDIO_DIR / "vo_sine2.mp3"
    _mk_mp3(vo, freq="880")
    bgm = AUDIO_DIR / "bgm.mp3"
    _mk_mp3(bgm, dur="0.4", freq="110")
    out = WORK / "merged_vo_bgm.mp4"
    FFmpegMerger.merge(v, vo, out, music_path=bgm, music_volume_db=-14.0)
    st = _probe_streams(out)
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in st), st


def test_merge_none_is_copy():
    v = WORK / "v_copy.mp4"
    _mk_video(v)
    out = WORK / "copy.mp4"
    FFmpegMerger.merge(v, None, out)
    assert out.stat().st_size == v.stat().st_size             # fast path copy2
    assert out.read_bytes() == v.read_bytes()


def test_apply_voiceover_post():
    # sans VO : la sortie EST l'entrée (aucun fichier créé)
    comp = WORK / "composite.mp4"
    _mk_video(comp, with_audio=True)                          # composite avec BGM
    assert _apply_voiceover_post(comp, None) == comp
    # avec VO : nouveau fichier *_vo.mp4, piste audio mixée (composite + VO)
    vo = AUDIO_DIR / "vo_post.mp3"
    _mk_mp3(vo, freq="660")
    outp = _apply_voiceover_post(comp, vo)
    assert outp != comp and outp.name.endswith("_vo.mp4"), outp
    assert outp.is_file()
    st = _probe_streams(outp)
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in st), st
    # le composite d'origine reste intact (non-régression)
    assert comp.is_file() and _probe_streams(comp)


TESTS = [test_resolve_voiceover, test_schemas_accept_voiceover,
         test_merge_vo_real, test_merge_vo_over_music,
         test_merge_none_is_copy, test_apply_voiceover_post]

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
