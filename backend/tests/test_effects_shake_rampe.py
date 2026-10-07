"""t128 : la rampe du shake. Un shake ne se fond pas (mélanger une image secouée avec l'image fixe la dédouble) :
son AMPLITUDE suit la courbe, dans l'expression du crop. On le vérifie au rendu, par la géométrie : la source est
un dégradé horizontal (Y = x), donc le décalage horizontal du recadrage se lit directement dans les pixels
(sortie(c) − c). Le rapport « avec rampe / sans rampe » à la même image doit valoir A(t), la courbe dessinée."""
import os, subprocess, sys, tempfile
os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzshk_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")


def _ffmpeg():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    print("SKIP: ffmpeg introuvable — rampe du shake ignoree")
    sys.exit(0)


FF = _ffmpeg()
from app.services.effects_engine import build_chain, _rampe_expr, _bornes
from app.services.animation_service import ease

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def evaluer(expr, t):
    """L'expression ffmpeg évaluée en Python : gte/lt/between et la variable t, rien d'autre."""
    return eval(expr, {"__builtins__": {}}, {"t": t, "gte": lambda a, b: float(a >= b), "lt": lambda a, b: float(a < b),
                                              "between": lambda x, a, b: float(a <= x <= b)})


print("\n[1] A(t) : l'expression de la courbe, évaluée")
A = _rampe_expr(1.0, 5.0, 2.0, 1.0, "linear", "linear")
check("0 avant le début", evaluer(A, 0.5) == 0 and evaluer(A, 0.999) == 0, A[:120])
# un escalier au pas des rampes (1/25 s) : exact AUX instants d'échantillonnage — 1,48 s = 12 pas sur 50
check("rampe d'entrée linéaire : 0,24 à 1,48 s, 0,5 à 2 s ; constante dans un pas", abs(evaluer(A, 1.48) - 0.24) < 1e-9
      and abs(evaluer(A, 2.0) - 0.5) < 1e-9 and evaluer(A, 1.50) == evaluer(A, 1.48), (evaluer(A, 1.48), evaluer(A, 2.0)))
check("plein entre les rampes", evaluer(A, 3.0) == 1 and evaluer(A, 3.99) == 1)
check("rampe de sortie : 1 − 12/25 à 4,48 s", abs(evaluer(A, 4.48) - 0.52) < 1e-9, evaluer(A, 4.48))
check("0 après la fin", evaluer(A, 5.01) == 0 and evaluer(A, 6) == 0)
B = _rampe_expr(1.0, 5.0, 2.0, 1.0, "cubic-bezier(0.9,0,1,0.2)", "smooth")
check("courbe asymétrique : la valeur de la courbe aux pas d'échantillonnage (écrite à 4 décimales)",
      all(abs(evaluer(B, 1.0 + (k + 0.5) * 0.04) - ease("cubic-bezier(0.9,0,1,0.2)", k * 0.04 / 2.0)) < 1e-4 for k in range(50)),
      [round(evaluer(B, 1.0 + k * 0.04), 4) for k in (10, 25, 40)])
check("jamais deux pas comptés au même instant (somme ≤ 1)", max(evaluer(B, k / 100) for k in range(600)) <= 1.0 + 1e-12)

print("\n[2] chaîne : sans rampe, le shake d'avant ; avec rampe, l'amplitude modulée")
ctx = {"w": 256, "h": 256, "dur": 6.0, "fps": 25}
nu = ";".join(build_chain([{"type": "shake", "intensity": 100}], "0:v", "vout", "u0", ctx))
franc = ";".join(build_chain([{"type": "shake", "intensity": 100, "t0": 1, "t1": 5}], "0:v", "vout", "u0", ctx))
check("sans bornes ni rampe : aucune expression de rampe", "gte(t" not in nu and "lt(t" not in nu, nu[:160])
check("bornes sans rampe : porte franche, aucune expression de rampe", "gte(t" not in franc, franc[:160])
sortie = ";".join(build_chain([{"type": "shake", "intensity": 100, "t0": 1, "t1": 5, "fade_out": 1}], "0:v", "vout", "u0", ctx))
check("rampe de sortie SEULE : l'amplitude rampe aussi (axes x ET y)", sortie.count("gte(t,4.9600)") == 2, sortie[:200])
deux = ";".join(build_chain([{"type": "shake", "intensity": 100, "t0": 1, "t1": 5, "fade_in": 1}], "0:v", "vout", "u0", ctx))
check("la même amplitude sur les deux axes (sin en x, cos en y)", deux.count("gte(t,1.0000)") == 2, deux.count("gte(t,1.0000)"))
check("bornes : t1 ramené à la durée du clip, rampes au plus à la moitié de l'intervalle",
      _bornes({"t0": 1, "t1": 10, "fade_in": 5, "fade_out": 1}, {"dur": 6}) == (1.0, 6.0, 2.5, 1.0),
      _bornes({"t0": 1, "t1": 10, "fade_in": 5, "fade_out": 1}, {"dur": 6}))

tmp = tempfile.mkdtemp(prefix="dzshk_out_")
src = os.path.join(tmp, "src.mp4")
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:size=256x256:rate=25:duration=6",
                "-vf", "geq=lum='X':cb=128:cr=128", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-qp", "0", src], check=True)


def rendre(eff, nom):
    out = os.path.join(tmp, nom)
    chain = build_chain([eff], "0:v", "vout", "u1", ctx)
    subprocess.run([FF, "-y", "-v", "error", "-i", src, "-filter_complex", ";".join(chain), "-map", "[vout]",
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-qp", "0", out], check=True, timeout=180)
    return out


def decalages(video):
    """Décalage horizontal (px) de chaque image : médiane de sortie(c) − c sur la ligne du milieu, colonnes 72..184."""
    # le plan Y brut du yuv420p (Y = x à la source) : un passage en « gray » réétalerait la plage (16-235 -> 0-255)
    # et ajouterait un faux décalage
    r = subprocess.run([FF, "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], capture_output=True, check=True)
    # 256 de haut : la ligne du milieu reste dans l'image quel que soit le secouement vertical (±32 px)
    b, w, h = r.stdout, 256, 256
    taille = w * h * 3 // 2
    n = len(b) // taille
    out = []
    for k in range(n):
        ligne = b[k * taille + (h // 2) * w: k * taille + (h // 2) * w + w]
        d = sorted(ligne[c] - c for c in range(72, 184))
        out.append(d[len(d) // 2])
    return out


plein = decalages(rendre({"type": "shake", "intensity": 100}, "plein.mp4"))
eff = {"type": "shake", "intensity": 100, "t0": 1.0, "t1": 5.0, "fade_in": 2.0, "fade_out": 1.0,
       "ease_in": "linear", "ease_out": "linear"}
rampe = decalages(rendre(eff, "rampe.mp4"))
print(f"  décalage plein régime : max {max(abs(v) for v in plein)} px ; images {len(rampe)}")
check("le shake plein bouge vraiment, sans dépasser son amplitude (20 à 32 px)", 20 <= max(abs(v) for v in plein) <= 33, max(abs(v) for v in plein))
check("immobile avant le début (t < 1 s)", all(abs(v) <= 1 for v in rampe[:25]), rampe[:25])
check("immobile après la fin (t > 5 s)", all(abs(v) <= 1 for v in rampe[126:]), rampe[126:])
# le modèle EXACT du recadrage : crop évalue x en flottant, l'arrondit à l'entier le plus proche (lrint), puis au PAIR (chroma
# sous-échantillonnée en yuv420p) — le décalage avance par pas de 2 px, d'où une comparaison au pixel près plutôt
# qu'un rapport (sur 14 px, un pas de 2 px ferait 0,14 d'erreur)
import math
m, f = 32, 2 + 5 * 0.5
def modele(t, a):
    return (round(m + m * a * math.sin(2 * math.pi * t * f)) & ~1) - m
A = _rampe_expr(1.0, 5.0, 2.0, 1.0, "linear", "linear")
ec_plein = max(abs(plein[k] - modele(k / 25, 1.0)) for k in range(len(plein)))
check("le shake plein suit le modèle du recadrage (± 1 px)", ec_plein <= 1, ec_plein)
ecarts = [(k / 25, evaluer(A, k / 25), rampe[k], modele(k / 25, evaluer(A, k / 25))) for k in range(len(rampe))]
pire = max(abs(r - mo) for _, _, r, mo in ecarts)
check("avec rampe : chaque image = le modèle à l'amplitude A(t) (± 1 px)", pire <= 1, pire)
mont = [abs(r) for t, a, r, mo in ecarts if 1.0 < t < 3.0 and abs(modele(t, 1.0)) >= 20]
check("l'amplitude monte pendant la rampe d'entrée (aux crêtes du sinus)", len(mont) > 5 and mont[-1] >= mont[0] + 15, mont)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
