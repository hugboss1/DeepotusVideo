# -*- coding: utf-8 -*-
"""Coupe franche d'un gabarit SEQUENTIEL sous la demi-image (03/10/2026).
MESURE (ffmpeg 9.0.1 de l'application, comme 8.1.1) : build_sequential_command enchaine les actes par un xfade
« cut » de 0,04 s FIXE. Quand 0,04 s fait moins d'une demi-image (10 ou 12 i/s), xfade voit l'EOF de sa premiere
entree et TERMINE le flux : deux actes de 4 s et 2 s a 10 i/s -> 4,0 s au lieu de 5,9 s, le second acte perdu sans
erreur. A 24, 25 et 30 i/s, 0,04 s tient (5,958 / 5,96 / 5,967 s mesures).
CORRECTIF : la duree de coupe vient de `_cut_tau(fps)` — la regle que le Montage applique deja (P 27/09) —, desormais
definie dans template_service (a cote de la table _XFADE dont elle lit la coupe) et reprise par montage_service.
Garde d'identite : a 30, 25 et 24 i/s, la commande est la MEME, a l'octet, que celle de la base.
Temoin positif : la commande de la base, rendue a 10 i/s, perd bien le second acte.
Run (depuis backend/) : & $PY tests/test_templates_coupe_fps.py"""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcoupefps_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY"):
    os.environ[k] = ""
# Le ffmpeg LIVRE avec l'application (9.0.1) passe devant celui du PATH : c'est lui que le bug a ete mesure.
_BIN = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGen" / "bin"
if (_BIN / "ffmpeg.exe").is_file():
    os.environ["PATH"] = str(_BIN) + os.pathsep + os.environ.get("PATH", "")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "aa65a65f"
from app.services import template_service as TS                     # noqa: E402
E = TS.TemplateEngine()
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"],
                                                 capture_output=True, cwd=str(RACINE)).stdout)
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
FF, FP = shutil.which("ffmpeg"), shutil.which("ffprobe")
print(f"ffmpeg : {FF}")

A, B = _tmp / "images" / "a.png", _tmp / "images" / "b.png"
VA, VB = _tmp / "images" / "va.mp4", _tmp / "images" / "vb.mp4"
if FF:
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=red:s=64x64", "-frames:v", "1", str(A)], check=True)
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=64x64", "-frames:v", "1", str(B)], check=True)
    # Deux clips a 30 i/s (une source Seedance typique), plus longs que leur acte : le trim/tpad du gabarit les coupe.
    for p, d in ((VA, 5), (VB, 3)):
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=s=64x64:r=30:d={d}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)], check=True)


def tpl(fps, kind="image_slot", transition="cut"):
    def act(i, slot, ln):
        r = {"id": f"r{i}", "type": kind, "x": 0, "y": 0, "width": 360, "height": 640, "z_index": 0, "act": i,
             "slot_name": slot, "fit": "cover", "length_s": ln, "length_mode": "fixed"}
        if i:
            r["transition"] = {"type": transition, "duration_s": 0.5}
        return r
    return {"id": "tpl_coupe", "name": "coupe", "render_mode": "sequential",
            "canvas": {"width": 360, "height": 640, "fps": fps, "duration_s": 6, "background_color": "#000000"},
            "regions": [act(0, "s1", 4), act(1, "s2", 2)]}


def slots(kind="image_slot"):
    return {"s1": {"path": A if kind == "image_slot" else VA}, "s2": {"path": B if kind == "image_slot" else VB}}


def duree(p):
    """Duree de la VIDEO, en images comptees / cadence — pas celle du conteneur : la piste muette (anullsrc) court
    jusqu'a `-t` et masque une video tronquee (base a 10 i/s : conteneur 5,96 s, video 4,0 s)."""
    o = subprocess.run([FP, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout
    num, den = o.strip().split(",")[0].split("/")
    return int(o.strip().split(",")[1]) * int(den) / int(num)


def rendre(nom, fps, kind="image_slot"):
    return duree(E.render("tpl_coupe", slots(kind), _tmp / "outputs" / f"{nom}.mp4", template=tpl(fps, kind)))


def cmd(mod, fps, kind="image_slot", transition="cut"):
    return mod.build_sequential_command(E, tpl(fps, kind, transition), slots(kind), _tmp / "outputs" / "x.mp4")[0]


print("[T] la regle")
tau = getattr(TS, "_cut_tau", None)
check("T1 template_service a `_cut_tau` : 0,04 tant que c'est au moins une demi-image, une image (ms superieur) en deca",
      tau is not None and [tau(f) for f in (60, 30, 25, 24, 15, 12, 10)] == [0.04, 0.04, 0.04, 0.04, 0.04, 0.084, 0.1],
      str(tau and [tau(f) for f in (60, 30, 25, 24, 15, 12, 10)]))
from app.services import montage_service as MS                      # noqa: E402
check("T2 le Montage et les gabarits partagent LA MEME regle (une seule definition)", tau is not None and MS._cut_tau is tau)

print("\n[G] la commande")
same = [(f, k) for f in (30, 25, 24) for k in ("image_slot", "video_slot") if cmd(TS, f, k) != cmd(TSB, f, k)]
check("G1 a 30, 25 et 24 i/s (images et clips) la commande est IDENTIQUE a celle de la base, a l'octet", not same, str(same))
check("G2 un fondu (crossfade 0,5 s) est intact a 10 i/s : seule la COUPE change", cmd(TS, 10, transition="crossfade") ==
      cmd(TSB, 10, transition="crossfade"))
c10 = " ".join(map(str, cmd(TS, 10)))
check("G3 a 10 i/s la coupe dure UNE image (0,1 s) et l'offset recule d'autant (3,9) ; -t = 5,9",
      "xfade=transition=fade:duration=0.1:offset=3.9[" in c10 and " -t 5.9 " in c10, c10[-700:])

print("\n[R] rendus, durees lues dans le MP4")
if FF and FP:
    b10 = _tmp / "outputs" / "base10.mp4"
    subprocess.run(cmd(TSB, 10)[:-1] + [str(b10)], check=True, capture_output=True)
    db = duree(b10)
    check("R0 temoin : la commande de la BASE a 10 i/s perd le second acte (~4,0 s au lieu de 5,9)", abs(db - 4.0) < 0.06, f"{db:.3f}")
    for f in (10, 12, 24, 30):
        t = TS._cut_tau(f) if tau else 0.04
        att = 4 + 2 - t
        di = rendre(f"img{f}", f)
        dv = rendre(f"vid{f}", f, "video_slot")
        tol = 1.0 / f + 0.01
        check(f"R{f} a {f} i/s, images ET clips : duree = 4 + 2 - {t} = {att:.3f} s (a une image pres)",
              abs(di - att) <= tol and abs(dv - att) <= tol, f"images {di:.3f} clips {dv:.3f}")
else:
    check("R0 ffmpeg/ffprobe disponibles", False, f"{FF} {FP}")

shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
