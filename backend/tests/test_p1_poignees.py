# -*- coding: utf-8 -*-
"""P1 #7 (28/09/2026) — POIGNEES DE PLAN : UN VRAI FONDU NE DECALE PLUS RIEN.

Defauts MESURES le 28/09 (source numerotee, 25 i/s, ffmpeg 9.0.1) :
  - un fondu de 0,4 s entre A et B couvrait [t0-0,4 ; t0] puis B et TOUT ce
    qui suit arrivaient 0,4 s trop tot (a t0, B montrait l'image in+10) ; deux
    fondus : 20 images ; rendu 5,6 s pour 6,0 s de timeline -- et l'audio,
    pose par adelay sur la timeline, ne reculait pas : image et son decales ;
  - un trou suivi d'un plan en coupe : a start(B) le rendu montrait encore
    le NOIR, la 1re image de B (n°75) n'apparaissait jamais.
Le lecteur, lui, CENTRE le voile sur la jonction [t0-t/2 ; t0+t/2] (dzmVeil).
Decision de l'utilisateur (28/09) : VRAIES poignees -- les images de la
SOURCE au-dela de la sortie de A et avant l'entree de B ; a defaut de
source, l'image se fige ; effets, masque et zoom ne s'appliquent pas aux
poignees.

METHODE (celle de test_retours_horloge) : source NUMEROTEE 64x32 sans perte
(moitie gauche 16+8*(N%28), droite 16+8*(N//28)), rendu reel par
_build_montage_command, lecture image par image. Les poignees se PROUVENT par
la luminance : au milieu d'un fondu, l'image de sortie est le melange de deux
images connues, et une poignee REELLE (image hors [in, out]) donne une autre
valeur qu'une image FIGEE. Temoin : le montage_service de la base de branche
(git show) importe dans un module temporaire -- il doit rougir la ou le
nouveau est vert. Faute n6 : details par _d().
Run : & $PY tests/test_p1_poignees.py   (depuis backend/, PATH avec le ffmpeg de l'app)
"""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzpoig_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
from app.services import montage_service as MS            # noqa: E402

BASE = "303506b"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:500]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


FF = shutil.which("ffmpeg")
OLD = None
try:
    _src = subprocess.run(["git", "show", f"{BASE}:backend/app/services/montage_service.py"], cwd=ROOT,
                          capture_output=True).stdout
    if _src:
        _p = pathlib.Path(TMP) / "montage_service_base.py"
        _p.write_bytes(_src)
        _spec = importlib.util.spec_from_file_location("app.services._ms_base_poig", str(_p))
        OLD = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(OLD)
except Exception as e:                                      # noqa: BLE001
    print("  (temoin indisponible :", e, ")")

W, H, FPS = 64, 32, 25


def src():
    p = pathlib.Path(TMP) / "src25.mp4"
    if not p.exists():
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r=25:d=12",
                        "-vf", "geq=lum='if(lt(X,32),16+8*mod(N,28),16+8*floor(N/28))':cb=128:cr=128",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-qp", "0", str(p)], check=True)
    return p


def lum(n):
    """Luminance gauche attendue de l'image source n."""
    return 16 + 8 * (n % 28)


def clip(start, end, src_in, **kw):
    d = {"path": str(src()), "src_dur": 12.0, "src_in": src_in, "start": start, "end": end,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


_n = [0]
def rendre(mod, clips):
    _n[0] += 1
    out = pathlib.Path(TMP) / f"o{_n[0]}.mp4"
    try:
        cmd, total = mod._build_montage_command(clips, [], [], None, w=W, h=H, fps=FPS, mix_db={}, ducking=False,
                                                duration_master=False, preview=False, out=str(out))
    except Exception as e:                                  # noqa: BLE001
        return {"err": f"build : {e}"}
    r = subprocess.run([FF] + cmd[1:], capture_output=True, text=True)
    if r.returncode:
        return {"err": r.stderr[-300:], "cmd": cmd}
    raw = subprocess.run([FF, "-v", "error", "-i", str(out), "-pix_fmt", "yuv420p", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fs = W * H * 3 // 2
    fr = [raw[i * fs:i * fs + W * H] for i in range(len(raw) // fs)]

    def zone(f, x0):
        v = [f[y * W + x] for y in range(12, 20) for x in range(x0, x0 + 8)]
        return sum(v) / len(v)
    L = [zone(f, 12) for f in fr]
    R = [zone(f, 44) for f in fr]
    num = [round((l - 16) / 8) + 28 * round((r - 16) / 8) for l, r in zip(L, R)]
    return {"n": len(fr), "total": total, "L": L, "num": num, "cmd": cmd}


def img(res, t):
    j = int(round(t * FPS))
    return res["num"][j] if "num" in res and j < len(res["num"]) else None


def lg(res, t):
    j = int(round(t * FPS))
    return res["L"][j] if "L" in res and j < len(res["L"]) else None


def total_audio(mod, clips):
    try:
        return mod._build_montage_command(clips, [], [], None, w=W, h=H, fps=FPS, mix_db={}, ducking=False,
                                          duration_master=False, preview=False, out=str(pathlib.Path(TMP) / "a.m4a"),
                                          audio_only=True)[1]
    except Exception as e:                                  # noqa: BLE001
        return f"err {e}"


print("\n[0] preconditions")
check("0.1 ffmpeg present ; temoin de la base importe", bool(FF) and OLD is not None, _d(FF, OLD is not None))

# A lit 0,48 s (image 12 exacte), B lit 3,0 s (75..), C lit 6,0 s (150..) -- entrees sur des images ENTIERES
FONDU = [clip(0, 2, 0.48), clip(2, 4, 3.0, transition="xfade", transition_s=0.8), clip(4, 6, 6.0)]
DEUX = [clip(0, 2, 0.48), clip(2, 4, 3.0, transition="xfade", transition_s=0.8),
        clip(4, 6, 6.0, transition="xfade", transition_s=0.4)]
TROU = [clip(0, 2, 0.48), clip(3, 5, 3.0)]
COUPES = [clip(0, 2, 0.48), clip(2, 4, 3.0), clip(4, 6, 6.0)]

N = {k: rendre(MS, v) for k, v in (("fondu", FONDU), ("deux", DEUX), ("trou", TROU), ("coupes", COUPES))}
O = {k: rendre(OLD, v) for k, v in (("fondu", FONDU), ("deux", DEUX), ("trou", TROU))} if OLD else {}
check("0.2 tous les rendus s'executent", all("err" not in r for r in N.values()),
      _d({k: r.get("err") for k, r in N.items() if "err" in r}))

print("\n[1] un fondu ne decale plus rien")
f = N["fondu"]
check("1.1 temoin : a la base, apres un fondu de 0,8 s, B montre in+20 a son start et le rendu dure 5,2 s",
      bool(O) and img(O["fondu"], 2.0) == 95 and O["fondu"].get("n") == 130, _d(img(O.get("fondu", {}), 2.0), O.get("fondu", {}).get("n")))
check("1.2 duree rendue = timeline (150 images, total 6,0)", f.get("n") == 150 and f.get("total") == 6.0, _d(f.get("n"), f.get("total")))
check("1.3 hors fondu, chaque plan montre son image exacte : A a 1,56 s, B a 2,44 s et 3,96 s, C a 4,0 s et 5,96 s",
      [img(f, 1.56), img(f, 2.44), img(f, 3.96), img(f, 4.0), img(f, 5.96)] == [51, 86, 124, 150, 199],
      _d([img(f, t) for t in (1.56, 2.44, 3.96, 4.0, 5.96)]))
d2 = N["deux"]
check("1.4 deux fondus : rien ne se cumule (C exacte a 4,24 s et 5,96 s ; 150 images)",
      d2.get("n") == 150 and [img(d2, 4.24), img(d2, 5.96)] == [156, 199], _d(d2.get("n"), img(d2, 4.24), img(d2, 5.96)))
check("1.5 le fondu est CENTRE sur la jonction (comme le voile du lecteur) : A pur a 1,56 s, melange de 1,6 a 2,4, B pur a 2,44 s",
      img(f, 1.56) == 51 and img(f, 2.44) == 86 and all(abs(lg(f, t) - lum(img(f, t) or 0)) > 1.5 for t in (1.8, 2.0, 2.2)),
      _d([(t, lg(f, t)) for t in (1.8, 2.0, 2.2)]))
_ta, _to = total_audio(MS, FONDU), (total_audio(OLD, FONDU) if OLD else None)
check("1.6 la mesure audio (/measure) dit aussi 6,0 s (temoin : 5,2)", _ta == 6.0 and _to == 5.2, _d(_ta, _to))

print("\n[2] vraies poignees (luminance au coeur du fondu)")
# t=1,8 s (p=0,25) : A montre son image 57 (dans le plan) ; B montre sa POIGNEE 70 (reelle) ou 75 (figee)
# t=2,2 s (p=0,75) : A montre sa POIGNEE 67 (reelle) ou 61 (figee) ; B montre 80
reel_b = {round(0.75 * lum(57) + 0.25 * lum(70), 1), round(0.25 * lum(57) + 0.75 * lum(70), 1)}
fige_b = {round(0.75 * lum(57) + 0.25 * lum(75), 1), round(0.25 * lum(57) + 0.75 * lum(75), 1)}
reel_a = {round(0.25 * lum(67) + 0.75 * lum(80), 1), round(0.75 * lum(67) + 0.25 * lum(80), 1)}
fige_a = {round(0.25 * lum(61) + 0.75 * lum(80), 1), round(0.75 * lum(61) + 0.25 * lum(80), 1)}
proche = lambda v, S: v is not None and any(abs(v - s) <= 3 for s in S)
check("2.1 avant la jonction, B entre par sa VRAIE poignee (image 70, pas 75 figee)",
      proche(lg(f, 1.8), reel_b) and not proche(lg(f, 1.8), fige_b), _d(lg(f, 1.8), sorted(reel_b), sorted(fige_b)))
check("2.2 apres la jonction, A sort par sa VRAIE poignee (image 67, pas 61 figee)",
      proche(lg(f, 2.2), reel_a) and not proche(lg(f, 2.2), fige_a), _d(lg(f, 2.2), sorted(reel_a), sorted(fige_a)))
BORD = [clip(0, 2, 0.48), clip(2, 4, 0.08, transition="xfade", transition_s=0.8), clip(4, 6, 6.0)]
b = rendre(MS, BORD)
# B lit 0,08 s (image 2) : 0,4 s de poignee demandee, 0,08 s seulement de source -> image FIGEE (2)
fige_bord = {round(0.75 * lum(57) + 0.25 * lum(2), 1), round(0.25 * lum(57) + 0.75 * lum(2), 1)}
check("2.3 source trop courte avant l'entree : B fige sa 1re image, et le calage reste exact",
      "err" not in b and proche(lg(b, 1.8), fige_bord) and b.get("n") == 150 and img(b, 2.44) == 13 and img(b, 4.0) == 150,
      _d(b.get("err"), lg(b, 1.8), sorted(fige_bord), b.get("n"), img(b, 2.44), img(b, 4.0)))
_cmd = " ".join(str(x) for x in f.get("cmd", []))
check("2.4 la commande lit les poignees dans la SOURCE (-ss 2.48 -t 0.4 pour A, -ss 2.6 -t 0.4 pour B)",
      "-ss 2.48 -t 0.4 -i" in _cmd and "-ss 2.6 -t 0.4 -i" in _cmd, _d(_cmd[:600]))

print("\n[3] trou puis coupe : la 1re image n'est plus avalee")
t3 = N["trou"]
check("3.1 temoin : a la base, a start(B)=3,0 s le rendu montrait encore le noir", bool(O) and img(O["trou"], 3.0) == 0,
      _d(img(O.get("trou", {}), 3.0)))
check("3.2 a 3,0 s : l'image 75 de B, pure ; a 2,96 s : le noir ; 125 images",
      img(t3, 3.0) == 75 and abs(lg(t3, 3.0) - lum(75)) <= 1.5 and img(t3, 2.96) == 0 and t3.get("n") == 125,
      _d(img(t3, 3.0), lg(t3, 3.0), img(t3, 2.96), t3.get("n")))

print("\n[4] non-regression : coupes seules et vitesse")
c4 = N["coupes"]
check("4.1 coupes franches : images exactes a chaque start, 150 images",
      c4.get("n") == 150 and [img(c4, 0.0), img(c4, 2.0), img(c4, 4.0)] == [12, 75, 150], _d(c4.get("n"), [img(c4, t) for t in (0.0, 2.0, 4.0)]))
VIT = [clip(0, 2, 0.48), clip(2, 4, 3.0, speed=2.0, transition="xfade", transition_s=0.8), clip(4, 6, 6.0)]
v = rendre(MS, VIT)
check("4.2 fondu sur un plan a x2 : C reste exacte (4,0 s -> 150), 150 images",
      "err" not in v and v.get("n") == 150 and img(v, 4.0) == 150 and img(v, 2.44) == 97,
      _d(v.get("err"), v.get("n"), img(v, 4.0), img(v, 2.44)))

_vc = " ".join(str(x) for x in v.get("cmd", []))
check("4.3 a x2, la poignee d'entree lit 0,8 s de SOURCE pour 0,4 s de timeline (-ss 2.2 -t 0.8)",
      "-ss 2.2 -t 0.8 -i" in _vc, _d(_vc[:500]))

print("\n[5] cas limites (mutants survivants du 28/09)")
PLANCHER = [clip(0, 2, 0.48), clip(2, 4, 3.0, transition="xfade", transition_s=0.02), clip(4, 6, 6.0)]
pl = rendre(MS, PLANCHER)
check("5.1 fondu plancher : au moins une image de chaque cote -> la jonction (2,0 s) est un MELANGE, 150 images",
      "err" not in pl and pl.get("n") == 150 and abs(lg(pl, 2.0) - lum(img(pl, 2.0) or 0)) > 1.5 and img(pl, 2.04) == 76,
      _d(pl.get("err"), pl.get("n"), lg(pl, 2.0), img(pl, 2.0), img(pl, 2.04)))
TROU_FONDU = [clip(0, 2, 0.48), clip(3, 5, 3.0, transition="xfade", transition_s=0.4)]
tf = rendre(MS, TROU_FONDU)
check("5.2 trou puis plan qui porte un fondu : pas de fondu joue (le lecteur n'en montre pas), image 75 PURE a 3,0 s, noir pur a 2,92 s",
      "err" not in tf and tf.get("n") == 125 and img(tf, 3.0) == 75 and abs(lg(tf, 3.0) - lum(75)) <= 1.5
      and abs(lg(tf, 2.92) - 16) <= 1.5,          # juste avant : NOIR pur, pas un fondu noir -> B
      _d(tf.get("err"), tf.get("n"), img(tf, 3.0), lg(tf, 3.0), lg(tf, 2.92)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
