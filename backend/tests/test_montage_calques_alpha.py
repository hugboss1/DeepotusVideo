# -*- coding: utf-8 -*-
"""t282 (23/10/2026) — les overlays vidéo TRANSPARENTS se voient : au rendu, dans le lecteur vivant, sur leur piste.

CONSTAT (campagne pilote du 22-23/10) : un mix 60 s importé en couches (v2 textes, v3 transitions, v4 effets en MOV
QuickTime Animation `qtrle`/`argb`) ne montrait ses overlays ni sur les pistes, ni dans l'aperçu, ni au rendu.
MESURÉ avant correction (scratchpad repro.py) :
  * le RENDU composait déjà les MOV qtrle : 46,6 dB contre le rendu de référence à 12 s. En revanche un overlay WebM
    VP9 + alpha passait par le décodeur vp9 NATIF de ffmpeg, qui ignore la couche alpha : un cadre opaque (noir)
    recouvrait tout le plan — seuls les mattes (t186) passaient par `matte_service.decodeur_entree` ;
  * le LECTEUR VIVANT chargeait `/api/jobs/{id}/video` brut : Chromium ne décode ni qtrle ni ProRes ni le codec png
    du QuickTime — l'élément <video> reste vide, l'overlay n'apparaît pas ;
  * les PISTES HAUTES n'avaient aucune vignette (le filmstrip était réservé à V1), et l'extracteur de vignettes lit
    lui aussi le fichier brut.
CORRECTION : `montage_media.calque(src)` rend la source telle quelle si le navigateur sait la lire (h264, vp8, vp9,
av1), sinon un APERÇU DE CALQUE WebM VP9 + alpha 480p en cache ; `GET /api/montage/calque?src=` le sert ; le lecteur
vivant (rôle « o ») et les vignettes des pistes hautes passent par lui ; les entrées d'overlay du rendu prennent le
décodeur libvpx-vp9 pour un .webm.

Run : & $PY tests/test_montage_calques_alpha.py   (depuis backend/)
"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt282_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REPO = os.path.abspath(os.path.join(BACKEND, ".."))
sys.path.insert(0, BACKEND)


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand
    print(f"SKIP: {name} introuvable — le banc-miroir ne peut rien mesurer")
    sys.exit(0)


FF, FP = _exe("ffmpeg"), _exe("ffprobe")
from PIL import Image                                   # noqa: E402
from app.services import montage_service as M           # noqa: E402
from app.services import montage_media as MM            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")

def fixture(label, cmd):
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture {label} : {r.stderr[-400:]}")
        sys.exit(1)

def probe(path):
    d = json.loads(sh([FP, "-v", "error", "-select_streams", "v:0", "-show_entries",
                       "stream=codec_name,pix_fmt:stream_tags=alpha_mode", "-of", "json", path]).stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return s.get("codec_name"), s.get("pix_fmt"), (s.get("tags") or {}).get("alpha_mode")

def frame_rgba(path, t, webm_alpha=False):
    """Une image RGBA de `path` à `t` — un .webm se lit par libvpx-vp9 (le décodeur natif perd l'alpha)."""
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    dec = ["-c:v", "libvpx-vp9"] if webm_alpha else []
    sh([FF, "-y", "-v", "error", "-ss", str(t), *dec, "-i", path, "-frames:v", "1", "-pix_fmt", "rgba", png])
    return Image.open(png).convert("RGBA")

def mean(im, box):
    c = im.crop(box); px = [c.getpixel((x, y)) for y in range(c.height) for x in range(c.width)]; n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 1) for i in range(len(px[0])))

W, H = 160, 288
# Le calque : un carré rouge OPAQUE au centre d'un cadre TRANSPARENT (alpha 0 ailleurs).
OVPNG = os.path.join(TMP, "ov.png")
im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for yy in range(H // 2 - 40, H // 2 + 40):
    for xx in range(W // 2 - 40, W // 2 + 40):
        im.putpixel((xx, yy), (230, 30, 30, 255))
im.save(OVPNG)
V1 = os.path.join(TMP, "v1.mp4")
fixture("v1", [FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x2040a0:s={W}x{H}:r=30:d=2",
               "-pix_fmt", "yuv420p", V1])
SRC = {"webm_vp9_alpha": ("ov.webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30"]),
       "mov_qtrle": ("ov_qtrle.mov", ["-c:v", "qtrle", "-pix_fmt", "argb"]),
       "mov_prores4444": ("ov_prores.mov", ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le"]),
       "mov_png": ("ov_png.mov", ["-c:v", "png", "-pix_fmt", "rgba"])}
PATHS = {}
for k, (nom, enc) in SRC.items():
    PATHS[k] = os.path.join(TMP, nom)
    fixture(k, [FF, "-y", "-v", "error", "-loop", "1", "-t", "2", "-r", "30", "-i", OVPNG, *enc, PATHS[k]])
OPAQUE = os.path.join(TMP, "opaque.mp4")
fixture("opaque", [FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x30c030:s={W}x{H}:r=30:d=2",
                   "-pix_fmt", "yuv420p", OPAQUE])

CENTRE = (W // 2 - 20, H // 2 - 20, W // 2 + 20, H // 2 + 20)
COIN = (4, 4, 24, 24)


def rendu(ov_path, tf=None, opacity=None, tag="r"):
    out = os.path.join(TMP, f"{tag}.mp4")
    v1 = [{"path": V1, "src_dur": 2.0, "src_in": 0.0, "start": 0.0, "end": 2.0,
           "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]
    v2 = [{"path": __import__("pathlib").Path(ov_path), "is_image": False, "src_dur": 2.0, "src_in": 0.0,
           "start": 0.0, "end": 2.0, "opacity": opacity, "tf": tf, "mp": None, "layer": 0, "tr": "v2"}]
    cmd, _t = M._build_montage_command(v1, v2, [], None, w=W, h=H, fps=30, mix_db={}, ducking=False,
                                       duration_master=True, preview=False, out=out)
    r = sh(cmd)
    return out if r.returncode == 0 else None, r.stderr[-300:]


print("\n[1] RENDU — un overlay vidéo transparent se compose sur le plan, quel que soit son format")
for k in SRC:
    out, err = rendu(PATHS[k], tag="cover_" + k)
    check(f"rendu_{k}_ffmpeg_ok", out is not None, err)
    if out:
        f = frame_rgba(out, 1.0)
        c, b = mean(f, CENTRE), mean(f, COIN)
        check(f"rendu_{k}_centre_rouge", c[0] > 180 and c[2] < 90, f"{c}")
        # le coin doit montrer le PLAN (bleu), pas un fond opaque du calque (noir) : c'est l'alpha qui passe
        check(f"rendu_{k}_coin_montre_le_plan_bleu", b[2] > 130 and b[0] < 80, f"{b}")
    out, err = rendu(PATHS[k], tf={"x": 0.5, "y": 0.5, "scale": 1.0, "rotate": 0.0}, opacity=0.5,
                     tag="tf_" + k)
    check(f"rendu_{k}_transforme_ffmpeg_ok", out is not None, err)
    if out:
        f = frame_rgba(out, 1.0)
        c, b = mean(f, CENTRE), mean(f, COIN)
        check(f"rendu_{k}_transforme_opacite_moitie", 90 < c[0] < 190 and c[2] > 50, f"{c}")
        check(f"rendu_{k}_transforme_coin_bleu", b[2] > 130 and b[0] < 80, f"{b}")

print("\n[2] APERÇU DE CALQUE — montage_media.calque")
for k in SRC:
    try:
        cq = MM.calque(PATHS[k])
    except Exception as e:                              # noqa: BLE001
        cq = None
        check(f"calque_{k}_fabrique", False, repr(e))
        continue
    if k == "webm_vp9_alpha":
        # le navigateur lit déjà un VP9 + alpha : la source est servie TELLE QUELLE, rien n'est réencodé
        check("calque_webm_est_la_source", str(cq) == str(PATHS[k]), str(cq))
        continue
    codec, pf, am = probe(str(cq))
    check(f"calque_{k}_webm_vp9", str(cq).endswith(".webm") and codec == "vp9", f"{cq} {codec}")
    check(f"calque_{k}_alpha_mode_1", am == "1", f"alpha_mode={am!r}")
    f = frame_rgba(str(cq), 1.0, webm_alpha=True)
    ww, hh = f.size
    # 480 px de haut AU PLUS : une source plus petite n'est jamais agrandie
    check(f"calque_{k}_hauteur_bornee", hh == min(480, H), f"{f.size}")
    cc = mean(f, (ww // 2 - 20, hh // 2 - 20, ww // 2 + 20, hh // 2 + 20))
    bb = mean(f, (4, 4, 30, 30))
    check(f"calque_{k}_centre_opaque_rouge", cc[3] > 240 and cc[0] > 180, f"{cc}")
    check(f"calque_{k}_coin_transparent", bb[3] < 10, f"{bb}")
    check(f"calque_{k}_cache_stable", str(MM.calque(PATHS[k])) == str(cq))
cq = MM.calque(OPAQUE)
check("calque_mp4_h264_est_la_source", str(cq) == str(OPAQUE), str(cq))
check("calque_besoin_qtrle", MM.calque_necessaire(PATHS["mov_qtrle"]) is True)
check("calque_besoin_h264_non", MM.calque_necessaire(OPAQUE) is False)

print("\n[3] ROUTE — GET /api/montage/calque")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
def q(p): return "/api/montage/calque?src=" + json.dumps({"file_path": p})
with TestClient(app) as c:
    r = c.get(q(PATHS["mov_qtrle"]))
    check("route_qtrle_200_webm", r.status_code == 200 and r.headers.get("content-type", "").startswith("video/webm"),
          f"{r.status_code} {r.headers.get('content-type')}")
    check("route_qtrle_corps_non_vide", len(r.content) > 1000, str(len(r.content)))
    r = c.get(q(OPAQUE))
    check("route_mp4_200_source", r.status_code == 200 and r.headers.get("content-type", "").startswith("video/mp4")
          and len(r.content) == os.path.getsize(OPAQUE), f"{r.status_code} {r.headers.get('content-type')}")
    r = c.get(q(OVPNG))
    check("route_image_415", r.status_code == 415, str(r.status_code))
    r = c.get("/api/montage/calque?src=" + json.dumps({"file_path": os.path.join(TMP, "absent.mov")}))
    check("route_absent_404", r.status_code == 404, str(r.status_code))

print("\n[4] ÉCRAN — le lecteur vivant et les vignettes des pistes hautes passent par l'aperçu de calque")
SRCJS = open(os.path.join(REPO, "frontend", "patches", "son-vfx-montage.js"), encoding="utf-8").read()
check("ecran_svmCalqueUrl", 'function svmCalqueUrl(s){return "/api/montage/calque?src="' in SRCJS)
# le lecteur vivant : rôle « o » sur l'aperçu de calque, à LONGUEUR ÉGALE (tables L4/G1 par position, voir t280)
check("ecran_lecteur_role_o_calque", 'el.src=svU(src,role);/* t282 : calque */el.preload="auto";' in SRCJS
      and 'function svU(src,role){return role==="o"?svmCalqueUrl(src):"/api/jobs/"+src.job_id+"/video"}' in SRCJS)
check("ecran_vignette_calque", "var url=svmCalqueUrl(src);" in SRCJS and 'var key="c"+svmSrcKey(src)+"@"+sec' in SRCJS)
check("ecran_vignette_damier", "svmDamier(g,SVM_THUMB_W,SVM_THUMB_H);" in SRCJS)
check("ecran_filmstrip_pistes_hautes",
      "else if(svV(tr.id,c)&&c.src.job_id)" in SRCJS
      and "media=r.jsx(SvFilmstripO,{src:c.src,k:svK(c.src,tr.id)," in SRCJS
      and 'function svK(s,t){return (t==="v1"?"":"c")+svmSrcKey(s)}' in SRCJS)
BUNDLE = open(os.path.join(REPO, "frontend", "dist", "assets", "index-BEOJX8L5.js"), "rb").read()
check("bundle_porte_le_lecteur_calque",
      b'el.src=svU(src,role);/* t282 : calque */el.preload="auto";' in BUNDLE)
r = sh([sys.executable, os.path.join(REPO, "scripts", "refresh_layer.py"), "--layer", "sonvfx", "--check"])
check("bundle_couche_sonvfx_a_jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])

print("\n[5] JEU RÉEL — les quatre couches du mix 60 s contre le rendu de référence (PSNR > 35 dB)")
U = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGenData\assets\outputs\uploads")
REEL = {n: os.path.join(U, "DVG_mix60s_" + n) for n in
        ("couche1_plans_FR.mp4", "couche2_textes_FR.mov", "couche3_transitions.mov", "couche4_effets.mov", "FR.mp4")}
if not all(os.path.isfile(p) for p in REEL.values()):
    print("  SKIP  fichiers du mix pilote absents de cette machine")
else:
    import pathlib
    for t0 in (3.0, 12.0, 40.0):
        v1 = [{"path": pathlib.Path(REEL["couche1_plans_FR.mp4"]), "src_dur": 60.0, "src_in": t0, "start": 0.0,
               "end": 1.0, "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]
        v2 = [{"path": pathlib.Path(REEL[n]), "is_image": False, "src_dur": 60.0, "src_in": t0, "start": 0.0,
               "end": 1.0, "opacity": None, "tf": None, "mp": None, "layer": k, "tr": f"v{k + 2}"}
              for k, n in enumerate(("couche2_textes_FR.mov", "couche3_transitions.mov", "couche4_effets.mov"))]
        out = os.path.join(TMP, f"reel_{t0}.mp4")
        cmd, _t = M._build_montage_command(v1, v2, [], None, w=1080, h=1080, fps=30, mix_db={}, ducking=False,
                                           duration_master=True, preview=False, out=out)
        rr = sh(cmd, timeout=600)
        check(f"reel_{t0}_rendu_ok", rr.returncode == 0, rr.stderr[-300:])
        def psnr(a, ta, b, tb):
            r2 = sh([FF, "-hide_banner", "-ss", str(ta), "-i", a, "-ss", str(tb), "-i", b, "-frames:v", "1",
                     "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"])
            for tok in r2.stderr.split():
                if tok.startswith("average:"):
                    v = tok.split(":")[1]
                    return 99.0 if v == "inf" else float(v)
            return 0.0
        p_ref = psnr(out, 0.5, REEL["FR.mp4"], t0 + 0.5)
        p_plan = psnr(out, 0.5, REEL["couche1_plans_FR.mp4"], t0 + 0.5)
        check(f"reel_{t0}_psnr_ref_sup_35", p_ref > 35, f"{p_ref} dB")
        # témoin : la recomposition n'est PAS le plan nu (sinon le PSNR ci-dessus ne dirait rien des couches)
        check(f"reel_{t0}_differe_du_plan_nu", p_ref > p_plan + 3, f"ref {p_ref} dB, plan nu {p_plan} dB")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
