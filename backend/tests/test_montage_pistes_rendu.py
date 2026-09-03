# -*- coding: utf-8 -*-
"""P0 — chaque piste arrive au rendu. Banc-MIROIR : on lit le FICHIER rendu
(ffprobe, PIL, astats), jamais le code qui pretend le produire.
Sources synthetiques : V1 bleu 4 s muet, overlay PNG rouge, musique 440 Hz,
voix 880 Hz. Deux chemins : _build_montage_command en direct, puis la ROUTE
POST /api/montage/render (TestClient, tache de fond executee avant le retour).
Run : & $PY tests/test_montage_pistes_rendu.py   (depuis backend/)

CONSTAT DU 03/09/2026 - le banc est sorti ROUGE au premier tour, sur les trois
chemins a la fois : `*_musique_audible_seule_3s` a -inf dB entre 3,0 et 3,8 s.
Cause racine MESUREE (pas deduite) : `sidechaincompress` s'arrete a la fin de
son entree la PLUS COURTE (framesync). La voix sert de detecteur ; une voix de
2 s coupait donc la musique bouclee a 2 s. ffprobe sur les trois fichiers
rendus : flux video 4,000 s, flux audio 2,000 s. Isole hors du depot :
    ffmpeg -f lavfi -i sine=d=6 -f lavfi -i sine=d=2 -filter_complex
           "[0:a][1:a]sidechaincompress=..." out.wav   ->   1,97 s
Correction : la chaine laterale [vsc] est prolongee par apad=whole_dur=total
(montage_service, section ducking). C'est ce que verrouille desormais
`*_audio_aussi_long_que_video`, l'assertion qui NOMME le mecanisme.
La musique disparaissait a la derniere syllabe du commentaire - ce qui
correspond au signalement « la piste musique n'est pas rendue ». Les overlays
V2, eux, sont sortis VERTS des le premier tour, sur les trois chemins : cette
moitie du signalement n'est PAS reproduite cote backend.

DEUX HYPOTHESES COTE ECRAN, NON MESUREES ICI, laissees a P1 et P7 (ce banc ne
touche pas au frontend) :
 (a) le bouton M d'une piste ecrit -40 dB dans `proj.mixDb`, autosauvegarde ET
     envoye au rendu (`svmTrackMute`, frontend/patches/son-vfx-montage.js
     ~l. 2943) : une musique « mise en sourdine pour ecouter la voix » repart
     au rendu a -40 dB, donc inaudible sans que rien ne le dise ;
 (b) le lecteur vivant ne joue ni A2 ni A3 (commentaire du vu-metre, meme
     fichier ~l. 2077) : ce que l'utilisateur entend AVANT de rendre n'est pas
     le mix - apercu et rendu peuvent diverger sans qu'il soit alerte."""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp0_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
FP = shutil.which("ffprobe") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffprobe.exe")
from PIL import Image                                   # noqa: E402
from app.services import montage_service as M           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

V1, OV, MUS, VOX = (os.path.join(TMP, n) for n in ("v1.mp4", "ov.png", "theme_music.wav", "voice.wav"))
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])
Image.new("RGB", (96, 96), (255, 40, 40)).save(OV)
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6", MUS])
sh([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100:duration=2", VOX])

def probe(path):
    d = json.loads(sh([FP, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                       "-of", "json", path]).stdout or "{}")
    return [s["codec_type"] for s in d.get("streams", [])], float(d.get("format", {}).get("duration") or 0)

def stream_dur(path, kind):
    """Duree du PREMIER flux d'un type. C'est la mesure qui NOMME le defaut
    ferme ici : une piste audio plus courte que la video = du mix coupe."""
    d = json.loads(sh([FP, "-v", "error", "-select_streams", kind[0],
                       "-show_entries", "stream=duration", "-of", "json",
                       path]).stdout or "{}")
    ss = d.get("streams", [])
    return float(ss[0].get("duration") or 0) if ss else 0.0

def frame(path, t):
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    sh([FF, "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png])
    return Image.open(png).convert("RGB")

def mean_rgb(im, box=None):
    if box: im = im.crop(box)
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 1) for i in range(3))

def rms_db(path, t0, t1):
    r = sh([FF, "-hide_banner", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-vn",
            "-af", "astats=measure_overall=RMS_level:measure_perchannel=none", "-f", "null", "-"])
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            v = ln.split(":")[-1].strip()
            return -999.0 if v == "-inf" else float(v)
    return -999.0

def v1_spec():
    return [{"path": V1, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
             "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]
def ov_spec(tf=None):
    return {"path": OV, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
            "end": 3.0, "opacity": None, "tf": tf, "mp": None}
AUD = {"fade_in": 0, "fade_out": 0, "fade_in_curve": None, "fade_out_curve": None,
       "fx_chain": "", "speed": 0.0, "volume_points": None}
def vox_spec():
    return [dict(AUD, tr="a1", path=VOX, src_dur=2.0, src_in=0.0, start=0.0, end=2.0,
                 gain=M._db_to_gain(-6))]
def mus_spec():
    return dict(AUD, path=MUS, gain=M._db_to_gain(-18))

def verify(tag, out, cover=True):
    kinds, dur = probe(out)
    check(f"{tag}_une_video_une_audio", kinds.count("video") == 1 and kinds.count("audio") == 1, str(kinds))
    check(f"{tag}_duree_4s", abs(dur - 4.0) < 0.15, f"{dur}")
    da, dv = stream_dur(out, "audio"), stream_dur(out, "video")
    check(f"{tag}_audio_aussi_long_que_video", da >= dv - 0.15,
          f"audio {da}s, video {dv}s")
    b0, b2, b35 = mean_rgb(frame(out, 0.5)), mean_rgb(frame(out, 2.0)), mean_rgb(frame(out, 3.5))
    check(f"{tag}_overlay_absent_avant", b0[2] > b0[0] + 60, f"{b0}")
    if cover:
        check(f"{tag}_overlay_visible_pendant", b2[0] > 180 and b2[0] > b2[2] + 100, f"{b2}")
    else:
        im = frame(out, 2.0); w, h = im.size
        c = mean_rgb(im, (w // 2 - 8, h // 2 - 8, w // 2 + 8, h // 2 + 8))
        k = mean_rgb(im, (0, 0, 16, 16))
        check(f"{tag}_overlay_centre_rouge", c[0] > 180 and c[0] > c[2] + 100, f"{c}")
        check(f"{tag}_overlay_coin_bleu", k[2] > k[0] + 60, f"{k}")
    check(f"{tag}_overlay_absent_apres", b35[2] > b35[0] + 60, f"{b35}")
    m = rms_db(out, 3.0, 3.8); v = rms_db(out, 0.2, 1.8)
    check(f"{tag}_musique_audible_seule_3s", m > -45, f"{m} dB")
    check(f"{tag}_voix_plus_forte_que_musique", v > m + 6, f"voix {v} dB, musique {m} dB")

print("\n[1] _build_montage_command en direct — overlay cover, voix, musique bouclee")
out1 = os.path.join(TMP, "direct.mp4")
cmd, total = M._build_montage_command(v1_spec(), [ov_spec()], vox_spec(), mus_spec(), w=270, h=480,
                                      fps=30, mix_db={}, ducking=True, duration_master=True,
                                      preview=False, out=out1)
r = sh(cmd); check("direct_ffmpeg_ok", r.returncode == 0 and os.path.getsize(out1) > 0, r.stderr[-300:])
verify("direct", out1)

print("\n[2] overlay TRANSFORME (scale 0,3 au centre) + apercu 480p")
out2 = os.path.join(TMP, "tf.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [ov_spec({"x": .5, "y": .5, "scale": .3, "rotate": 0.0})],
                                  vox_spec(), mus_spec(), w=66, h=120, fps=30, mix_db={},
                                  ducking=True, duration_master=True, preview=True, out=out2)
r = sh(cmd); check("tf_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
verify("tf", out2, cover=False)

print("\n[3] par la ROUTE — clips v2 / a1 / a2 en {file_path}, tache de fond")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
body = {"name": "p0", "ratio": "9:16", "preview": False, "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
        "clips": [{"tr": "v1", "src": {"file_path": V1}, "start": 0, "end": 4, "srcIn": 0, "transition": "cut"},
                  {"tr": "v2", "src": {"file_path": OV}, "start": 1, "end": 3},
                  {"tr": "a1", "src": {"file_path": VOX}, "start": 0, "end": 2},
                  {"tr": "a2", "src": {"file_path": MUS}, "start": 0, "end": 4, "loop": True}]}
with TestClient(app) as c:
    r = c.post("/api/montage/render", json=body)
    check("route_lancee", r.status_code == 200 and r.json().get("job_id"), r.text[:200])
    j = c.get("/api/jobs/" + r.json()["job_id"]).json()
    check("route_job_done", j.get("status") == "done", str(j.get("error") or j.get("status")))
    fp = j.get("final_video_path") or ""
    check("route_fichier_present", fp and os.path.exists(fp), fp)
    if fp and os.path.exists(fp):
        # le rendu reel est 1080x1920 : memes lectures, seuls les seuils sont relatifs
        verify("route", fp)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
