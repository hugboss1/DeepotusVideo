"""Vérifie que l'enveloppe temporelle des effets produit un filtergraph
accepté par ffmpeg ET visible aux bons instants."""
import os, subprocess, sys, tempfile
os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzfxt_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

def _ffmpeg():
    """ffmpeg du PATH, sinon celui embarque par l'app."""
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    print("SKIP: ffmpeg introuvable — test d'enveloppe temporelle ignore")
    sys.exit(0)


FF = _ffmpeg()
from app.services.effects_engine import build_chain, catalog, _opacity_cmds

tmp = tempfile.mkdtemp(prefix="dzfxt_out_")
src = os.path.join(tmp, "src.mp4")
# 6 s, gris uni : un effet visible se mesure sur la luminance moyenne
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi",
                "-i", "color=c=0x2040a0:size=320x568:rate=25:duration=6",
                "-pix_fmt", "yuv420p", src], check=True)

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

print("\n[1] Expression d'opacité : bornes et monotonie")
e = _opacity_cmds("blend@u", 1.0, 3.0, 0.5, 0.5, "smooth", "smooth")
check("commandes produites", e.count("all_opacity") > 10)
check("part de 0", e.startswith("0.000 blend@u all_opacity 0.0000"))
check("separateur echappe", "\;" in e)
# Le plein regime ne doit PAS s'ecrire « all_opacity 1.0000 » : blend ignore
# une valeur >= 1 (vf_blend.c, config_params n'applique all_opacity que si elle
# est < 1), la commande est acceptee mais l'opacite ne bouge pas et l'effet ne
# s'allume jamais. Il s'ecrit « all_opacity 1 » suivi des quatre opacites de
# plan. Voir scripts/qa/qa_effects_render.py (mesure au rendu).
check("atteint le plein regime", " all_opacity 1\\;" in e or e.endswith(" all_opacity 1"))
check("plein regime pose plan par plan", e.count("c0_opacity 1") >= 1
      and e.count("c3_opacity 1") >= 1)
check("jamais all_opacity 1.0000 (ignore par blend)", " all_opacity 1.0000" not in e)
check("finit a 0", e.rstrip().endswith("0.0000"))

print("\n[2] Filtergraph accepté par ffmpeg — les 20 effets, bornés + rampés")
cat = catalog()
bad = []
for name, spec in cat.items():
    eff = {"type": name, "intensity": 70, "t0": 1.5, "t1": 4.0,
           "fade_in": 0.5, "fade_out": 0.5,
           "ease_in": "smooth", "ease_out": "cubic-bezier(0.36,0,0.66,-0.56)"}
    if "preset" in (spec.get("params") or []) and spec.get("presets"):
        eff["preset"] = spec["presets"][0]
    if name == "letterbox": eff["ratio"] = "2.39"
    if name == "gradient": eff.update({"c0": "#22d3ee", "c1": "#a855f7", "angle": 45, "opacity": 60})
    chain = build_chain([eff], "0:v", "vout", "u1", {"w": 320, "h": 568, "dur": 6.0, "fps": 25})
    out = os.path.join(tmp, f"{name}.mp4")
    r = subprocess.run([FF, "-y", "-v", "error", "-i", src,
                        "-filter_complex", ";".join(chain), "-map", "[vout]",
                        "-frames:v", "150", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        bad.append((name, (r.stderr or "").strip().splitlines()[-1][:150] if r.stderr else "vide"))
print(f"  {len(cat)-len(bad)}/{len(cat)} effets rendus avec bornes + rampe")
for n, why in bad: print(f"    - {n}: {why}")
check("aucun effet en échec", not bad)

print("\n[3] L'effet est bien ABSENT hors de l'intervalle (invert, t0=2 t1=4)")
eff = {"type": "invert", "t0": 2.0, "t1": 4.0, "fade_in": 0.3, "fade_out": 0.3,
       "ease_in": "smooth", "ease_out": "smooth"}
chain = build_chain([eff], "0:v", "vout", "u2", {"w": 320, "h": 568, "dur": 6.0, "fps": 25})
out = os.path.join(tmp, "invert_timed.mp4")
subprocess.run([FF, "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(chain),
                "-map", "[vout]", "-pix_fmt", "yuv420p", out], check=True, timeout=180)
def lum(t):
    png = os.path.join(tmp, f"f{t}.png")
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", png],
                   check=True, timeout=60)
    from PIL import Image
    im = Image.open(png).convert("L")
    px = list(im.getdata())
    return sum(px) / len(px)
l0, l3, l5 = lum(0.5), lum(3.0), lum(5.5)
print(f"  luminance : t=0.5s -> {l0:.1f} | t=3s -> {l3:.1f} | t=5.5s -> {l5:.1f}")
check("original avant l'intervalle", abs(l0 - l5) < 6, f"({l0:.1f})")
check("inversé au milieu de l'intervalle", l3 > l0 + 40 or l3 < l0 - 40, f"({l3:.1f})")
check("gris d'origine après l'intervalle", abs(l5 - l0) < 12, f"({l5:.1f})")

print("\n[4] SANS rampe (fade_in = fade_out = 0), l'effet s'allume quand meme")
# Regression : la seule valeur « pleine » envoyee etait alors 1.0000, que blend
# ignore — l'effet n'apparaissait sur AUCUN effet et sur AUCUN chemin de rendu.
eff = {"type": "invert", "t0": 2.0, "t1": 4.0, "fade_in": 0, "fade_out": 0}
chain = build_chain([eff], "0:v", "vout", "u3", {"w": 320, "h": 568, "dur": 6.0, "fps": 25})
out = os.path.join(tmp, "invert_gate.mp4")
subprocess.run([FF, "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(chain),
                "-map", "[vout]", "-pix_fmt", "yuv420p", out], check=True, timeout=180)
g0, g3, g5 = lum(0.5), lum(3.0), lum(5.5)
print(f"  luminance : t=0.5s -> {g0:.1f} | t=3s -> {g3:.1f} | t=5.5s -> {g5:.1f}")
check("porte franche : inverse au milieu", abs(g3 - g0) > 40, f"({g3:.1f})")
check("porte franche : original avant", abs(g0 - 64.0) < 6, f"({g0:.1f})")
check("porte franche : original apres", abs(g5 - g0) < 6, f"({g5:.1f})")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
