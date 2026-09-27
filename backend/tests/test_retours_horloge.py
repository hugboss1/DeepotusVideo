# -*- coding: utf-8 -*-
"""RETOURS 26/09 — A : HORLOGE DU RENDU (plan 2026-09-27, tache 1).

Symptome rapporte : le rendu montre l'image SUIVANTE de celle du lecteur (une
image d'avance), et davantage sur plusieurs plans en coupe. Deux causes
MESUREES le 26/09/2026 (identiques sous ffmpeg 9.0.1 et 8.1.1) :
  1. `fps={fps}` de la chaine V1 part de la premiere image dont le pts vaut
     plus de 0 (le -ss d'entree laisse un pts residuel) : `trim` garde 29
     images sur 30 et `setpts=PTS-STARTPTS` recule tout d'une image.
     Correctif : `fps={fps}:start_time=0` aux trois poses (prefixe sf,
     variante vitesse, variante recadrage/zoom).
  2. `_XFADE["cut"] = ("fade", 0.04)` chevauche deux plans jointifs sans
     compensation : chaque coupe avance le plan entrant de 0,04 s, et l'effet
     est cumulatif. Correctif : tout plan V1 qui suit DIRECTEMENT un autre
     plan par une coupe recoit, APRES ses effets et son masque, une amorce
     `[n{k}l]tpad=start_mode=clone:start_duration=0.04[n{k}]` et
     `seg_durs[k] += 0.04` — l'offset du xfade tombe alors sur son `start`,
     et `total` egale la timeline (rendu ET /measure, meme graphe).
  Trous et vraies transitions : INCHANGES (ecarts dates : un vrai fondu
  avance encore les plans suivants de tau ; un trou suivi d'un plan en coupe
  avale la premiere image du plan).

METHODE. Source de synthese NUMEROTEE (64x32, x264 sans perte) : moitie
gauche luminance 16+8*(N%28), moitie droite 16+8*(N//28) — chaque image de
sortie dit quelle image SOURCE elle montre. Rendu reel par
`_build_montage_command` (comme les bancs l3 et l7), ffmpeg du PATH (lancer
le banc deux fois : PATH prefixe par %LOCALAPPDATA%\\DeepotusVideoGen\\bin =
9.0.1, puis sans = 8.1.1). Aucun appel reseau.
Controles par plan : n images = attendu ; j0 (premiere image de sortie du
plan) = start*fps ; img0 (premiere image source montree) = image `in` ;
ecart median a l'image source ideale = 0.

TEMOIN. La chaine de `e0ab545` (lue par `git show` et importee dans un module
temporaire) donne +1 sur les cas desalignes et 31/90 sur le pire cas : c'est
la preuve que la mesure voit le defaut. Le cas `in` 0 est vert avant ET apres.
ETAT VIDE : sans correctif, les controles du code courant sont ceux du temoin
(rouges). Regle des assertions negatives : chaque « absent » est precede d'un
temoin positif dans la meme expression. Faute n6 : les details sont
construits par `_d()` sur des `.get`, jamais par un acces nu.
Run : & $PY tests/test_retours_horloge.py   (depuis backend/)
"""
import importlib.util, json, math, os, pathlib, shutil, statistics, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzhorl_")
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

# --- temoin : la chaine de e0ab545 dans un module temporaire -----------------
OLD = None
try:
    _src = subprocess.run(["git", "show", "e0ab545:backend/app/services/montage_service.py"],
                          cwd=str(BACKEND.parent), capture_output=True).stdout
    if _src:
        _p = pathlib.Path(TMP) / "montage_service_e0ab545.py"
        _p.write_bytes(_src)
        _spec = importlib.util.spec_from_file_location("app.services._ms_e0ab545", str(_p))
        OLD = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(OLD)
except Exception as e:
    print(f"  (temoin e0ab545 indisponible : {e})")
    OLD = None

W, H = 64, 32
RATES = {"30": "30", "25": "25", "2997": "30000/1001"}
RVAL = {"30": 30.0, "25": 25.0, "2997": 30000 / 1001}


def src_of(rk):
    p = pathlib.Path(TMP) / f"src_{rk}.mp4"
    if not p.exists():
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"color=black:s={W}x{H}:r={RATES[rk]}:d=7",
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


def build(mod, clips, fps, out, v2=None, **kw):
    return mod._build_montage_command(clips, list(v2 or []), [], None, w=W, h=H, fps=fps, mix_db={},
                                      ducking=False, duration_master=False, preview=False,
                                      out=str(out), **kw)


_nrun = [0]
def run_case(mod, clips, fps, rk, subs_ass=None, v2=None):
    """Rend et mesure ; {'err': ...} si ffmpeg echoue (le banc rougit, ne meurt pas).
    Mesure chaque plan V1 PUIS chaque overlay V2 (`_rk` : cadence de SA source)."""
    _nrun[0] += 1
    out = pathlib.Path(TMP) / f"o_{_nrun[0]}.mp4"
    try:
        cmd, total = build(mod, clips, fps, out, v2=v2, **({"subs_ass": subs_ass} if subs_ass else {}))
    except Exception as e:
        return {"err": f"build : {e}"}
    r = subprocess.run([FF] + cmd[1:], capture_output=True, text=True)
    if r.returncode:
        return {"err": r.stderr[-400:], "cmd": cmd}
    raw = frames(out)
    fr = decode(raw)
    per = []
    for k, c in enumerate(list(clips) + list(v2 or [])):
        R = RVAL[c.get("_rk") or rk]
        spd = float(c.get("speed") or 0.0) or 1.0
        lo = c["src_in"] * R - 1.5
        hi = (c["src_in"] + (c["end"] - c["start"]) * spd) * R + 1.5
        js = [j for j, (n, b) in enumerate(fr) if not b and lo <= n <= hi]
        if not js:
            per.append({"clip": k, "absent": True}); continue
        j0 = js[0]
        ec = []
        for j in js:
            if j / fps - c["start"] < 0:
                continue
            # ideal : 1re image = 1re pts >= in, puis horloge LOCALE (pts - in)/vitesse
            # arrondie au plus proche a la cadence du canevas
            jl = j - int(round(c["start"] * fps))
            n = math.ceil(c["src_in"] * R - 1e-6)
            while math.floor(((n + 1) / R - c["src_in"]) / spd * fps + 0.5) <= jl:
                n += 1
            ec.append(fr[j][0] - n)
        per.append({"clip": k, "j0": j0, "j0_att": int(round(c["start"] * fps)),
                    "img0": fr[j0][0], "img0_att": math.ceil(c["src_in"] * R - 1e-6),
                    "ecart_med": (statistics.median(ec) if ec else None), "n": len(js)})
    return {"n": len(fr), "n_att": int(round(max(c["end"] for c in clips) * fps)), "total": total,
            "clips": per, "raw": raw, "cmd": cmd}


def aligne(res):
    """Vrai si le rendu tombe pile : n, et pour chaque plan j0, img0, ecart median 0."""
    if "err" in res:
        return False
    if res.get("n") != res.get("n_att"):
        return False
    for c in res.get("clips", []):
        if c.get("absent") or c.get("j0") != c.get("j0_att") or c.get("img0") != c.get("img0_att") \
                or c.get("ecart_med") not in (0, 0.0):
            return False
    return True


def resume(res):
    if "err" in res:
        return {"err": res["err"][-200:]}
    return {"n": f"{res.get('n')}/{res.get('n_att')}", "total": res.get("total"),
            "clips": [{k: v for k, v in c.items() if k != "clip"} for c in res.get("clips", [])]}


FX0 = [{"type": "grade_basic", "exposure": 0}]
MASQUE_COIN = {"shape": "ellipse", "x": 0.0, "y": 0.0, "w": 0.1, "h": 0.1, "soft": 0.0}

CASES = {
    # nom : (fps canevas, cadence source, clips)
    "1 plan in 0 (temoin vert)":           (30, "30", lambda rk: [clip(rk, 0, 1, 0.0)]),
    "1 plan in 0,5 source 25":             (30, "25", lambda rk: [clip(rk, 0, 1, 0.5)]),
    "1 plan de 2 s in 0,37":               (30, "30", lambda rk: [clip(rk, 0, 2, 0.37)]),
    "canevas 25, in 0,5":                  (25, "25", lambda rk: [clip(rk, 0, 1, 0.5)]),
    "x0,5 flow source 25":                 (30, "25", lambda rk: [clip(rk, 0, 2, 0.5, speed=0.5, retime="flow")]),
    "x0,5 blend source 25":                (30, "25", lambda rk: [clip(rk, 0, 2, 0.5, speed=0.5, retime="blend")]),
    "zoom dz source 25":                   (30, "25", lambda rk: [clip(rk, 0, 1, 0.5, dz={
                                                "x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0, "w1": 0.9, "ease": "lin"})]),
    "2 plans en coupe":                    (30, "30", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0)]),
    "3 plans en coupe a 30":               (30, "30", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0),
                                                                  clip(rk, 2, 3, 4.0)]),
    "3 plans en coupe a 29,97":            (30, "2997", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0),
                                                                    clip(rk, 2, 3, 4.0)]),
    "3 plans a 25, in 0,5/2,3/4,1":        (30, "25", lambda rk: [clip(rk, 0, 1, 0.5), clip(rk, 1, 2, 2.3),
                                                                  clip(rk, 2, 3, 4.1)]),
    "2 plans en coupe, effets+masque sur le 2e": (30, "30", lambda rk: [
        clip(rk, 0, 1, 0.0), clip(rk, 1, 2, 2.0, effects=FX0, mask=MASQUE_COIN)]),
    "2 plans en coupe, effets sur le 2e":  (30, "30", lambda rk: [clip(rk, 0, 1, 0.0),
                                                                  clip(rk, 1, 2, 2.0, effects=FX0)]),
}
# Cas desalignes au temoin (e0ab545) : +1 ou pire, et le pire cas 31/90.
DESALIGNES = ["1 plan in 0,5 source 25", "1 plan de 2 s in 0,37", "canevas 25, in 0,5",
              "2 plans en coupe", "3 plans en coupe a 30", "3 plans en coupe a 29,97",
              "3 plans a 25, in 0,5/2,3/4,1"]
PIRE = "3 plans a 25, in 0,5/2,3/4,1"

print("\n[0] preconditions")
check("0.1 ffmpeg present dans le PATH", bool(FF), _d(FF))
check("0.2 temoin e0ab545 importe (git show) et porte _build_montage_command",
      OLD is not None and callable(getattr(OLD, "_build_montage_command", None)), _d(OLD is not None))
if not FF:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

print("\n[1] chaine emise (sans rendu)")
_o = pathlib.Path(TMP) / "x.mp4"
_c1, _t1 = build(MS, [clip("25", 0, 1, 0.5)], 30, _o)
_g1 = " ".join(_c1)
check("1.1 prefixe sf : fps=30:start_time=0 (et plus de fps=30, nu)",
      "fps=30:start_time=0," in _g1 and "fps=30," not in _g1, _d(_g1[-600:]))
_c2, _t2 = build(MS, [clip("25", 0, 2, 0.5, speed=0.5, retime="blend")], 30, _o)
_g2 = " ".join(_c2)
check("1.2 variante vitesse : fps=30:start_time=0 devant tblend",
      "fps=30:start_time=0,tblend" in _g2 and "fps=30,tblend" not in _g2, _d(_g2[-600:]))
_c3, _t3 = build(MS, [clip("25", 0, 1, 0.5, dz={"x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0,
                                                 "w1": 0.9, "ease": "lin"})], 30, _o)
_g3 = " ".join(_c3)
check("1.3 variante zoom : fps=30:start_time=0 devant zoompan",
      "fps=30:start_time=0,zoompan" in _g3 and "fps=30,zoompan" not in _g3, _d(_g3[-600:]))
_c4, _t4 = build(MS, [clip("30", 0, 1, 0.0), clip("30", 1, 2, 2.0), clip("30", 2, 3, 4.0)], 30, _o)
_g4 = " ".join(_c4)
check("1.4 coupe franche : amorce clonee de 0,04 s sur le 2e ET le 3e plan",
      "[n1l]tpad=start_mode=clone:start_duration=0.04[n1]" in _g4
      and "[n2l]tpad=start_mode=clone:start_duration=0.04[n2]" in _g4, _d(_g4[-900:]))
check("1.5 ... et jamais sur le 1er plan (temoin : n1 l'a)",
      "[n1l]tpad" in _g4 and "[n0l]" not in _g4, _d(_g4[-900:]))
check("1.6 total = timeline (3,0 s pour 3 plans de 1 s en coupe)", _t4 == 3.0, _d(_t4))
check("1.7 offsets des xfade sur les start (1.0 puis 2.0 moins le cut 0,04 amorce)",
      "offset=0.96[x1]" in _g4 and "offset=1.96[x2]" in _g4, _d(_g4[-900:]))
try:
    _cm, _tm = build(MS, [clip("30", 0, 1, 0.0), clip("30", 1, 2, 2.0), clip("30", 2, 3, 4.0)], 30,
                     _o, audio_only=True)
except Exception as e:
    _cm, _tm = [], f"ERR {e}"
check("1.8 /measure (audio_only) : meme total que le rendu, = timeline", _tm == _t4 == 3.0, _d(_tm, _t4))
check("1.9 audio_only : aucune amorce video emise (temoin : la commande existe)",
      bool(_cm) and "tpad=start_mode" not in " ".join(_cm), _d(" ".join(_cm)[-300:]))
_c5, _t5 = build(MS, [clip("30", 0, 1, 0.0), clip("30", 1.5, 2.5, 2.0)], 30, _o)
_g5 = " ".join(_c5)
check("1.10 trou : segment noir present et AUCUNE amorce (inchange)",
      "color=c=black" in _g5 and "start_mode=clone" not in _g5, _d(_g5[-600:]))
check("1.11 trou : total inchange = 2,5 s", _t5 == 2.5, _d(_t5))
_c6, _t6 = build(MS, [clip("30", 0, 1, 0.0), clip("30", 1, 2, 2.0, transition="fade",
                                                   transition_s=0.4)], 30, _o)
_g6 = " ".join(_c6)
check("1.12 vrai fondu : xfade fade present et AUCUNE amorce (inchange)",
      "xfade=transition=fade:duration=0.4" in _g6 and "start_mode=clone" not in _g6, _d(_g6[-600:]))
_c7, _t7 = build(MS, [clip("30", 0, 1, 0.0), clip("30", 1, 2, 2.0, effects=FX0, mask=MASQUE_COIN)], 30, _o)
_g7 = " ".join(_c7)
_i_ov, _i_tp = _g7.find("overlay=0:0:shortest=1"), _g7.find("[n1l]tpad=start_mode=clone")
check("1.13 amorce posee APRES le masque (overlay du masque puis tpad)",
      _i_ov >= 0 and _i_tp > _i_ov, _d(_i_ov, _i_tp))

print("\n[2] rendus mesures (code courant) et temoin e0ab545")
RES, OLDRES = {}, {}
for name, (fps, rk, mk) in CASES.items():
    RES[name] = run_case(MS, mk(rk), fps, rk)
    if OLD is not None and (name in DESALIGNES or name.startswith("1 plan in 0 ")):
        OLDRES[name] = run_case(OLD, mk(rk), fps, rk)
    r = RES[name]
    check(f"2 {name} : aligne (n, j0, img0, ecart median 0)", aligne(r), _d(resume(r)))

print("\n[3] temoin : la chaine de e0ab545 voit le defaut")
_o0 = OLDRES.get("1 plan in 0 (temoin vert)", {"err": "absent"})
check("3.1 temoin vert : `in` 0 aligne aussi avec e0ab545", aligne(_o0), _d(resume(_o0)))
for name in DESALIGNES:
    r = OLDRES.get(name, {"err": "absent"})
    _ecs = [c.get("ecart_med") for c in r.get("clips", []) if not c.get("absent")]
    _mauvais = ("err" not in r) and (
        r.get("n") != r.get("n_att")
        or any(c.get("absent") for c in r.get("clips", []))
        or any((e or 0) >= 1 for e in _ecs))
    check(f"3 temoin {name} : desaligne (+1 ou pire) avec e0ab545", _mauvais, _d(resume(r)))
_pr = OLDRES.get(PIRE, {"err": "absent"})
check("3.9 pire cas au temoin : 31 images sur 90", _pr.get("n") == 31 and _pr.get("n_att") == 90,
      _d(resume(_pr)))
_pn = RES.get(PIRE, {})
check("3.10 pire cas corrige : 90 images sur 90", _pn.get("n") == 90 and _pn.get("n_att") == 90,
      _d(resume(_pn)))

print("\n[4] inchanges : trou et vrai fondu (ecarts dates)")
_INCH = {
    "2 plans avec un trou": (30, "30", lambda rk: [clip(rk, 0, 1, 0.0), clip(rk, 1.5, 2.5, 2.0)]),
    "2 plans en fondu 0,4": (30, "30", lambda rk: [clip(rk, 0, 1, 0.0),
                                                   clip(rk, 1, 2, 2.0, transition="fade", transition_s=0.4)]),
}
for name, (fps, rk, mk) in _INCH.items():
    rn = run_case(MS, mk(rk), fps, rk)
    ro = run_case(OLD, mk(rk), fps, rk) if OLD is not None else {"err": "temoin absent"}
    _sn, _so = resume(rn), resume(ro)
    check(f"4 {name} : rendu mesure identique a e0ab545 (temoin : les deux ont rendu)",
          "err" not in rn and "err" not in ro and _sn == _so, _d(_sn, _so))
    check(f"4 {name} : images identiques octet pour octet a e0ab545",
          "err" not in rn and "err" not in ro and rn.get("raw") == ro.get("raw") and bool(rn.get("raw")),
          _d(len(rn.get("raw") or b""), len(ro.get("raw") or b"")))

print("\n[5] sous-titres ASS de 1,00 a 2,00 s : images 30 a 59")
_ass = pathlib.Path(TMP) / "t.ass"
_ass.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 64
PlayResY: 32

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,D,,0,0,0,,{\\p1}m -40 -20 l 40 -20 40 20 -40 20{\\p0}
""", encoding="utf-8")
for name in ("3 plans en coupe a 30", PIRE):
    fps, rk, mk = CASES[name]
    sans = RES.get(name, {})
    avec = run_case(MS, mk(rk), fps, rk, subs_ass=str(_ass))
    fa, fs_ = avec.get("raw") or [], sans.get("raw") or []
    na, ns = len(fa), len(fs_)
    diff = [i for i in range(min(na, ns)) if fa[i] != fs_[i]]
    check(f"5 {name} : ASS present exactement sur les images 30 a 59 (temoin : 90 images des deux cotes)",
          na == ns == 90 and diff == list(range(30, 60)),
          _d(na, ns, diff[:3], diff[-3:], len(diff), avec.get("err", "")[-200:]))


# --- revue T1 (27/09) : temoin 3e01fbe (T1 livre, avant la revue) ---------------
T3E = None
try:
    _src3 = subprocess.run(["git", "show", "3e01fbe:backend/app/services/montage_service.py"],
                           cwd=str(BACKEND.parent), capture_output=True).stdout
    if _src3:
        _p3 = pathlib.Path(TMP) / "montage_service_3e01fbe.py"
        _p3.write_bytes(_src3)
        _spec3 = importlib.util.spec_from_file_location("app.services._ms_3e01fbe", str(_p3))
        T3E = importlib.util.module_from_spec(_spec3)
        _spec3.loader.exec_module(T3E)
except Exception as e:
    print(f"  (temoin 3e01fbe indisponible : {e})")
    T3E = None
check("6.0 temoin 3e01fbe importe (git show)", T3E is not None
      and callable(getattr(T3E, "_build_montage_command", None)), _d(T3E is not None))

print("\n[6] trou EN TETE de timeline (revue T1) : pas de coupe entrante, pas de +0,04")
# src_in != 0 : le noir du trou (luminance 16 = image 0) ne se confond pas avec un plan.
_TETE = {
    "trou initial 0,5 s + 2 plans en coupe": [clip("30", 0.5, 1.5, 1.0), clip("30", 1.5, 2.5, 3.0)],
    "trou initial 0,5 s + 3 plans en coupe": [clip("30", 0.5, 1.5, 1.0), clip("30", 1.5, 2.5, 3.0),
                                              clip("30", 2.5, 3.5, 5.0)],
}


def aligne_tete(res):
    """Comme aligne(), sauf le plan qui suit le trou : j0/img0 a +1 au plus (ecart
    date : un trou suivi d'un plan en coupe avale sa premiere image)."""
    if "err" in res or res.get("n") != res.get("n_att"):
        return False
    for i, c in enumerate(res.get("clips", [])):
        if c.get("absent") or c.get("ecart_med") not in (0, 0.0):
            return False
        tol = (0, 1) if i == 0 else (0,)
        if (c.get("j0", -9) - c.get("j0_att", 0)) not in tol or (c.get("img0", -9) - c.get("img0_att", 0)) not in tol:
            return False
    return True


for name, cl in _TETE.items():
    fin = cl[-1]["end"]
    rn = run_case(MS, cl, 30, "30")
    check(f"6 {name} : total = timeline {fin} s, n images, ecart median 0 par plan",
          rn.get("total") == fin and aligne_tete(rn), _d(resume(rn)))
    try:
        _cma, _tma = build(MS, cl, 30, _o, audio_only=True)
    except Exception as e:
        _tma = f"ERR {e}"
    check(f"6 {name} : /measure (audio_only) meme total = {fin} s", _tma == fin, _d(_tma))
    ro = run_case(T3E, cl, 30, "30") if T3E is not None else {"err": "temoin absent"}
    _eco = [c.get("ecart_med") for c in ro.get("clips", []) if not c.get("absent")]
    check(f"6 temoin 3e01fbe {name} : total + 0,04, une image de trop, plans a -1",
          "err" not in ro and ro.get("total") == round(fin + 0.04, 3)
          and ro.get("n") == ro.get("n_att", 0) + 1 and _eco and all(e == -1 for e in _eco), _d(resume(ro)))

print("\n[7] overlays V2 VIDEO (revue T1) : fps depuis 0, flux borne a sa duree")


def V2(start, end, src_in, **kw):
    d = {"path": str(src_of("25")), "is_image": False, "src_dur": 7.0, "src_in": src_in,
         "start": start, "end": end, "opacity": None, "tf": None, "mp": None, "layer": 0, "_rk": "25"}
    d.update(kw)
    return d


# V1 lu a partir de 5 s (images 150+) : jamais confondu avec l'overlay (images 13..38).
_V2CAS = {
    "V2 plein cadre, source 25, in 0,5, canevas 30": V2(0.4, 1.4, 0.5),
    "V2 transforme (tf), source 25, in 0,5": V2(0.4, 1.4, 0.5, tf={"x": 0.5, "y": 0.5, "scale": 1.0,
                                                                    "rotate": 0.0}),
}
for name, ov in _V2CAS.items():
    base = [clip("30", 0, 2, 5.0)]
    rn = run_case(MS, base, 30, "30", v2=[ov])
    cv = (rn.get("clips") or [{}, {}])[-1]
    check(f"7 {name} : image 0 = image in, j0 = start, ecart median 0, 30 images (1 s)",
          "err" not in rn and cv.get("j0") == cv.get("j0_att") == 12 and cv.get("img0") == cv.get("img0_att") == 13
          and cv.get("ecart_med") in (0, 0.0) and cv.get("n") == 30, _d(resume(rn)))
    ro = run_case(T3E, base, 30, "30", v2=[ov]) if T3E is not None else {"err": "temoin absent"}
    co = (ro.get("clips") or [{}, {}])[-1]
    check(f"7 temoin 3e01fbe {name} : l'overlay avancait d'une image (ecart median 1)",
          "err" not in ro and co.get("img0") == 13 and co.get("ecart_med") == 1, _d(resume(ro)))
_ci, _ = build(MS, [clip("30", 0, 2, 5.0)], 30, _o, v2=[V2(0.4, 1.4, 0.5)])
_gi = " ".join(_ci)
check("7.5 chaine V2 video : fps=30:start_time=0,trim=duration=1.0 puis setpts decale",
      "setsar=1,fps=30:start_time=0,trim=duration=1.0,setpts=PTS-STARTPTS+0.4/TB[ov0]" in _gi, _d(_gi[-500:]))
_png = pathlib.Path(TMP) / "ov.png"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=red:s=16x16", "-frames:v", "1", str(_png)])
_cp, _ = build(MS, [clip("30", 0, 2, 5.0)], 30, _o, v2=[V2(0.4, 1.4, 0.0, path=str(_png), is_image=True)])
_gp = " ".join(_cp)
check("7.6 overlay IMAGE : chaine historique, sans start_time ni trim (temoin : l'overlay est la)",
      "[ov0]" in _gp and "setsar=1,fps=30,setpts=PTS-STARTPTS+0.4/TB[ov0]" in _gp
      and "start_time" not in _gp.split("[ov0]")[0].split(";")[-1], _d(_gp[-500:]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
