# -*- coding: utf-8 -*-
"""COUPE FRANCHE SOUS LA DEMI-IMAGE (27/09/2026) — GIF 480 a 12 i/s.

Symptome (revue T1 du chantier retours-ia-26-09) : `/render` passe `fps=12` a
tout le graphe pour le preset `gif_480` ; 3 plans de 1 s en coupe rendent 12
images au lieu de 36 (le GIF s'arrete au premier plan), et 14/24 en mp4 a
12 i/s pour 2 plans.

CAUSE MESUREE (showinfo, ffmpeg 9.0.1 = 8.1.1). La coupe franche est un
`xfade` de 0,04 s + une amorce `tpad=start_mode=clone:start_duration=0.04`
sur le plan entrant (T1, `3e01fbe`). A 12 i/s, 0,04 s = 0,48 image :
  1. tpad arrondit l'amorce a ZERO image, mais `seg_durs[k] += 0.04` la
     compte quand meme ;
  2. l'offset du xfade vaut alors 0,96 s = 11,52 images, arrondi a 12, alors
     que le plan sortant finit a pts 11 : xfade voit l'EOF de sa premiere
     entree avant l'offset et termine le flux — tout le reste est jete.
A 24/25/30/60 i/s, 0,04 s >= une demi-image : une image d'amorce, offset
atteignable (le cas des bancs horloge). Toute cadence < 12,5 i/s est touchee.
CORRECTIF : `_cut_tau(fps)` — la coupe dure 0,04 s tant que c'est au moins
une demi-image, UNE image (1/fps arrondie au ms superieur) en deca ; meme
duree pour l'amorce, les trous (coupe entrante et sortante) et le plancher
des vraies transitions. A >= 12,5 i/s la commande est identique octet pour
octet a celle d'avant (controle [4]).

METHODE. Source de synthese NUMEROTEE (64x32, x264 sans perte, 12 ou 25 i/s)
comme `test_retours_horloge.py` : chaque image de sortie dit quelle image
source elle montre. Rendu reel par `_build_montage_command`, en mp4 (queue
historique) et en GIF (preset `gif_480` resolu par `_deliver_resolve`, comme
`/render`). Lancer deux fois : PATH prefixe par
%LOCALAPPDATA%\\DeepotusVideoGen\\bin (9.0.1), puis sans (8.1.1).
TEMOIN : la chaine de `f7ee2d8` (tete de la branche avant correctif, lue par
`git show`) rend 12 images GIF / 14 mp4 sur les memes cas — la mesure voit
le defaut ; a 25 i/s elle est alignee (temoin vert).
Regle des assertions negatives : chaque « absent » est precede d'un temoin
positif. Faute n6 : details construits par `_d()` sur des `.get`.
Run : & $PY tests/test_coupe_cadence.py   (depuis backend/)
"""
import importlib.util, json, math, os, pathlib, shutil, statistics, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzcoupe_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
from app.services import montage_service as MS            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


FF = shutil.which("ffmpeg")
_ver = ""
if FF:
    try:
        _ver = subprocess.run([FF, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    except Exception:
        _ver = ""
print(f"ffmpeg : {FF} — {_ver}")

BASE = "f7ee2d8"
OLD = None
try:
    _src = subprocess.run(["git", "show", f"{BASE}:backend/app/services/montage_service.py"],
                          cwd=str(BACKEND.parent), capture_output=True).stdout
    if _src:
        _p = pathlib.Path(TMP) / f"montage_service_{BASE}.py"
        _p.write_bytes(_src)
        _spec = importlib.util.spec_from_file_location(f"app.services._ms_{BASE}", str(_p))
        OLD = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(OLD)
except Exception as e:
    print(f"  (temoin {BASE} indisponible : {e})")
    OLD = None

W, H = 64, 32
RVAL = {"12": 12.0, "25": 25.0}


def src_of(rk):
    p = pathlib.Path(TMP) / f"src_{rk}.mp4"
    if not p.exists():
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"color=black:s={W}x{H}:r={rk}:d=7",
                        "-vf", "geq=lum='if(lt(X,32),16+8*mod(N,28),16+8*floor(N/28))':cb=128:cr=128",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-qp", "0", str(p)], check=True)
    return p


def frames(out):
    raw = subprocess.run([FF, "-v", "error", "-i", str(out), "-pix_fmt", "yuv420p",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fs = W * H * 3 // 2
    return [raw[i * fs:i * fs + W * H] for i in range(len(raw) // fs)]


def decode(fr):
    """(numero d'image source, fondu?) par image de sortie."""
    res = []
    for f in fr:
        def m(x0):
            vals = [f[y * W + x] for y in range(12, 20) for x in range(x0, x0 + 8)]
            return sum(vals) / len(vals)
        kl, kr = (m(12) - 16) / 8, (m(44) - 16) / 8
        blend = abs(kl - round(kl)) > 0.3 or abs(kr - round(kr)) > 0.3
        res.append((round(kl) + 28 * round(kr), blend))
    return res


def clip(rk, start, end, src_in, **kw):
    d = {"path": str(src_of(rk)), "src_dur": 7.0, "src_in": src_in, "start": start, "end": end,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


GIF = MS._deliver_resolve("gif_480")


def build(mod, clips, fps, out, gif=False, **kw):
    if gif:
        kw["preset"] = (mod._deliver_resolve("gif_480"))
    return mod._build_montage_command(clips, [], [], None, w=W, h=H, fps=fps, mix_db={},
                                      ducking=False, duration_master=False, preview=False,
                                      out=str(out), **kw)


_nrun = [0]
def run_case(mod, clips, fps, rk, gif=False):
    """Rend et mesure ; {'err': ...} si ffmpeg echoue (le banc rougit, ne meurt pas)."""
    _nrun[0] += 1
    out = pathlib.Path(TMP) / f"o_{_nrun[0]}.{'gif' if gif else 'mp4'}"
    try:
        cmd, total = build(mod, clips, fps, out, gif=gif)
    except Exception as e:
        return {"err": f"build : {e}"}
    r = subprocess.run([FF] + cmd[1:], capture_output=True, text=True)
    if r.returncode:
        return {"err": r.stderr[-400:], "cmd": cmd}
    fr = decode(frames(cmd[-1]))
    R = RVAL[rk]
    per = []
    for k, c in enumerate(clips):
        lo = c["src_in"] * R - 1.5
        hi = (c["src_in"] + (c["end"] - c["start"])) * R + 1.5
        # GIF : palette 256 couleurs — le decodage garde la tolerance de fondu
        # mais le numero reste lisible (niveaux de gris espaces de 8).
        js = [j for j, (n, b) in enumerate(fr) if (gif or not b) and lo <= n <= hi]
        if not js:
            per.append({"clip": k, "absent": True}); continue
        j0 = js[0]
        ec = []
        for j in js:
            jl = j - int(round(c["start"] * fps))
            if jl < 0:
                continue
            n = math.ceil(c["src_in"] * R - 1e-6)
            while math.floor(((n + 1) / R - c["src_in"]) * fps + 0.5) <= jl:
                n += 1
            ec.append(fr[j][0] - n)
        per.append({"clip": k, "j0": j0, "j0_att": int(round(c["start"] * fps)),
                    "img0": fr[j0][0], "img0_att": math.ceil(c["src_in"] * R - 1e-6),
                    "ecart_med": (statistics.median(ec) if ec else None), "n": len(js)})
    return {"n": len(fr), "n_att": int(round(max(c["end"] for c in clips) * fps)), "total": total,
            "clips": per, "cmd": cmd}


def aligne(res, tol_apres_trou=()):
    """n, et pour chaque plan : present, j0, img0, ecart median 0. Les plans de
    `tol_apres_trou` tolerent +1 sur j0/img0 (ecart date de T1 : un trou suivi
    d'un plan en coupe avale la premiere image du plan)."""
    if "err" in res or res.get("n") != res.get("n_att"):
        return False
    for i, c in enumerate(res.get("clips", [])):
        if c.get("absent") or c.get("ecart_med") not in (0, 0.0):
            return False
        tol = (0, 1) if i in tol_apres_trou else (0,)
        if (c.get("j0", -9) - c.get("j0_att", 0)) not in tol \
                or (c.get("img0", -9) - c.get("img0_att", 0)) not in tol:
            return False
    return True


def resume(res):
    if "err" in res:
        return {"err": res["err"][-200:]}
    return {"n": f"{res.get('n')}/{res.get('n_att')}", "total": res.get("total"),
            "clips": [{k: v for k, v in c.items() if k != "clip"} for c in res.get("clips", [])]}


FX0 = [{"type": "grade_basic", "exposure": 0}]
MASQUE_COIN = {"shape": "ellipse", "x": 0.0, "y": 0.0, "w": 0.1, "h": 0.1, "soft": 0.0}

# nom : (cadence source, clips, plans tolerant +1 apres un trou)
CASES = {
    "2 plans en coupe":               ("12", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0)], ()),
    "3 plans en coupe":               ("12", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0),
                                                         clip(rk, 2, 3, 4.0)], ()),
    "3 plans source 25, in 0,5/2,3/4,1": ("25", lambda rk: [clip(rk, 0, 1, 0.5), clip(rk, 1, 2, 2.3),
                                                            clip(rk, 2, 3, 4.1)], ()),
    "2 plans en coupe, effets+masque sur le 2e": ("12", lambda rk: [
        clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0, effects=FX0, mask=MASQUE_COIN)], ()),
    "trou au milieu (1 -> 1,5)":      ("12", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1.5, 2.5, 2.0)], (1,)),
    "trou en tete 0,5 + 2 plans":     ("12", lambda rk: [clip(rk, 0.5, 1.5, 1.0), clip(rk, 1.5, 2.5, 3.0)], (0,)),
}

print("\n[0] preconditions")
check("0.1 ffmpeg present dans le PATH", bool(FF), _d(FF))
check(f"0.2 temoin {BASE} importe (git show) et porte _build_montage_command",
      OLD is not None and callable(getattr(OLD, "_build_montage_command", None)), _d(OLD is not None))
check("0.3 preset gif_480 : 12 i/s, sortie GIF", GIF.get("fps") == 12 and GIF.get("gif") is True, _d(GIF))
if not FF or OLD is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

print("\n[1] chaine emise a 12 i/s (sans rendu)")
_o = pathlib.Path(TMP) / "x.mp4"
_c1, _t1 = build(MS, CASES["3 plans en coupe"][1]("12"), 12, _o)
_g1 = " ".join(_c1)
check("1.1 _cut_tau : 0,04 a >= 12,5 i/s, une image (ms superieur) en deca",
      [getattr(MS, "_cut_tau", lambda f: None)(f) for f in (60, 30, 25, 24, 15, 12.5, 12, 10)]
      == [0.04, 0.04, 0.04, 0.04, 0.04, 0.04, 0.084, 0.1],
      _d([getattr(MS, "_cut_tau", lambda f: None)(f) for f in (60, 30, 25, 24, 15, 12.5, 12, 10)]))
check("1.2 amorce d'UNE image (0,084 s) sur le 2e et le 3e plan, jamais 0,04",
      "[n1l]tpad=start_mode=clone:start_duration=0.084[n1]" in _g1
      and "[n2l]tpad=start_mode=clone:start_duration=0.084[n2]" in _g1
      and "start_duration=0.04[" not in _g1, _d(_g1[-900:]))
check("1.3 xfade de coupe d'une image, offsets sur une image entiere (11 et 23)",
      "xfade=transition=fade:duration=0.084:offset=0.916[x1]" in _g1
      and "xfade=transition=fade:duration=0.084:offset=1.916[x2]" in _g1, _d(_g1[-900:]))
check("1.4 total = timeline (3,0 s)", _t1 == 3.0, _d(_t1))
try:
    _cm, _tm = build(MS, CASES["3 plans en coupe"][1]("12"), 12, _o, audio_only=True)
except Exception as e:
    _cm, _tm = [], f"ERR {e}"
check("1.5 /measure (audio_only) : meme total = 3,0 s", _tm == _t1 == 3.0, _d(_tm, _t1))
_c2, _t2 = build(MS, CASES["trou au milieu (1 -> 1,5)"][1]("12"), 12, _o)
check("1.6 trou : total = timeline 2,5 s", _t2 == 2.5, _d(_t2))
_c3, _ = build(MS, CASES["3 plans en coupe"][1]("12"), 12, pathlib.Path(TMP) / "x.gif", gif=True)
_g3 = " ".join(_c3)
check("1.7 queue GIF a 12 i/s : palette presente et PAS de fps=12 redondant",
      "[x2]split[g0][g1];[g0]palettegen[pal];[g1][pal]paletteuse[outv]" in _g3 and "fps=12," not in _g3,
      _d(_g3[-400:]))
_c4, _ = build(MS, CASES["3 plans en coupe"][1]("12"), 30, pathlib.Path(TMP) / "x.gif", gif=True)
_g4 = " ".join(_c4)
check("1.8 queue GIF d'un graphe a 30 i/s : fps=12 garde (sous-echantillonnage)",
      "[x2]fps=12,split[g0][g1]" in _g4, _d(_g4[-400:]))

print("\n[2] rendus mesures a 12 i/s — mp4 et GIF (code courant)")
RES = {}
for name, (rk, mk, tol) in CASES.items():
    for gif in (False, True):
        r = run_case(MS, mk(rk), 12, rk, gif=gif)
        RES[(name, gif)] = r
        check(f"2 {name} [{'gif' if gif else 'mp4'}] : aligne (n, j0, img0, ecart median 0)",
              aligne(r, tol), _d(resume(r)))
check("2.x GIF 3 plans : 36 images sur 36 (le symptome rapporte)",
      RES.get(("3 plans en coupe", True), {}).get("n") == 36, _d(resume(RES.get(("3 plans en coupe", True), {}))))

# Vraies transitions a 12 i/s : ecart date de T1 (un fondu avance les plans
# suivants de tau) — on garde n = total * fps et chaque plan PRESENT. Le
# plancher 0,02 s est porte a une image (`_cut_tau`), comme la coupe.
for name, cl in {
    "fondu 0,4 s": [clip("12", 0, 1, 0.0), clip("12", 1, 2, 2.0, transition="fade", transition_s=0.4)],
    "fondu 0,02 s (plancher)": [clip("12", 0, 1, 0.0), clip("12", 1, 2, 2.0, transition="fade",
                                                             transition_s=0.02)],
}.items():
    for gif in (False, True):
        r = run_case(MS, cl, 12, "12", gif=gif)
        _natt = int(round((r.get("total") or 0) * 12))
        check(f"2 {name} [{'gif' if gif else 'mp4'}] : n = total x 12 ({_natt}), les deux plans presents",
              "err" not in r and _natt >= 19 and r.get("n") == _natt
              and len(r.get("clips", [])) == 2 and not any(c.get("absent") for c in r.get("clips", [])),
              _d(resume(r)))

# Temoin de la queue : la MEME commande, `fps=12,` reinjecte devant split,
# perd la derniere image (la mesure voit ce defaut-la aussi).
_cq = list(RES.get(("3 plans en coupe", True), {}).get("cmd") or [])
_nq = None
if "-filter_complex" in _cq:
    _i = _cq.index("-filter_complex")
    _cq[_i + 1] = _cq[_i + 1].replace("[x2]split[g0]", "[x2]fps=12,split[g0]")
    _cq[-1] = str(pathlib.Path(TMP) / "temoin_queue.gif")
    if subprocess.run([FF] + _cq[1:], capture_output=True).returncode == 0:
        _nq = len(frames(_cq[-1]))
check("2.y temoin queue : avec fps=12 redondant, 35 images sur 36", _nq == 35, _d(_nq))

print(f"\n[3] temoin {BASE} : la mesure voit le defaut a 12 i/s, pas a 25")
_og = run_case(OLD, CASES["3 plans en coupe"][1]("12"), 12, "12", gif=True)
check("3.1 temoin GIF 3 plans : 12 images sur 36 (s'arrete au 1er plan)",
      _og.get("n") == 12 and _og.get("n_att") == 36, _d(resume(_og)))
_om = run_case(OLD, CASES["2 plans en coupe"][1]("12"), 12, "12")
check("3.2 temoin mp4 2 plans : 14 images sur 24", _om.get("n") == 14 and _om.get("n_att") == 24,
      _d(resume(_om)))
_om3 = run_case(OLD, CASES["3 plans en coupe"][1]("12"), 12, "12")
check("3.3 temoin mp4 3 plans : non aligne (plan absent)", not aligne(_om3)
      and any(c.get("absent") for c in _om3.get("clips", [])), _d(resume(_om3)))
_ov = run_case(OLD, CASES["3 plans en coupe"][1]("25"), 25, "25")
check("3.4 temoin vert : 3 plans en coupe a 25 i/s alignes avec le temoin", aligne(_ov), _d(resume(_ov)))
_nv = run_case(MS, CASES["3 plans en coupe"][1]("25"), 25, "25")
check("3.5 ... et avec le code courant", aligne(_nv), _d(resume(_nv)))

print("\n[4] >= 12,5 i/s : commande identique octet pour octet au temoin")
_NR = {
    "3 plans en coupe": lambda rk: CASES["3 plans en coupe"][1](rk),
    "trou au milieu": lambda rk: CASES["trou au milieu (1 -> 1,5)"][1](rk),
    "trou en tete": lambda rk: CASES["trou en tete 0,5 + 2 plans"][1](rk),
    "fondu 0,4": lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0, transition="fade", transition_s=0.4)],
    "fondu 0,02 (plancher)": lambda rk: [clip(rk, 0, 1, 0.0),
                                         clip(rk, 1, 2, 2.0, transition="fade", transition_s=0.02)],
    "effets+masque": lambda rk: CASES["2 plans en coupe, effets+masque sur le 2e"][1](rk),
}
for fps in (24, 25, 30, 60):
    for name, mk in _NR.items():
        for gif in ((False, True) if fps == 30 else (False,)):
            try:
                cn, tn = build(MS, mk("25"), fps, _o, gif=gif)
                co, to = build(OLD, mk("25"), fps, _o, gif=gif)
            except Exception as e:
                cn, tn, co, to = [f"ERR {e}"], None, [], None
            check(f"4 {fps} i/s {name}{' [gif]' if gif else ''} : commande et total identiques (temoin : non vide)",
                  bool(co) and cn == co and tn == to, _d(tn, to, len(cn), len(co)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
