# -*- coding: utf-8 -*-
"""t118 — Smooth Cut, préréglage « corriger », courbes restantes (spec montage-vs-resolve D-17, D-18, D-29).
Banc-MIROIR : chaque effet passe par le VRAI `effects_engine.build_chain` et le ffmpeg de la machine, on lit l'image
produite.

D-18 (Smooth Cut) est ECARTE apres mesure, voir la spec : minterpolate ne glisse proprement qu'en
deca d'un saut d'environ 6 % de la largeur, et traine au-dela (pire qu'une coupe).
[1] D-17 objectif. Mesuré le 07/10 sur une grille : `coussinet` à l'intensité par défaut REPLIAIT l'image dans les coins
    (avec k2 < 0, r·(1 + k1·r² + k2·r⁴) cesse de croître vers r ≈ 0,99 — r = 1 au coin, demi-diagonale de ffmpeg).
    « corriger » est l'INVERSE CALCULÉ du barillet de même intensité : une grille déformée par le barillet (sans
    recadrage, comme un vrai grand-angle) puis corrigée doit retomber sur la grille d'origine.
Run : & $PY tests/test_montage_t118.py   (depuis backend/)"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzt118_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


FF = shutil.which("ffmpeg")
if not FF:
    print("SKIP: ffmpeg introuvable"); sys.exit(0)

from PIL import Image, ImageChops                    # noqa: E402
from app.services import effects_engine as E         # noqa: E402

W, H = 320, 180
GRILLE = pathlib.Path(TMP) / "grille.png"
# UNE ligne verticale à x = 60 (à gauche, là où le barillet courbe le plus) : une grille faisait lire la ligne
# VOISINE dès que le barillet décale les lignes de plus d'un pas (mesuré)
subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=white:s={W}x{H},drawbox=x=59:y=0:w=3:h={H}:c=black:t=fill",
                "-frames:v", "1", str(GRILLE)], check=True)


def passe(src, graphe, nom):
    out = pathlib.Path(TMP) / f"{nom}.png"
    r = subprocess.run([FF, "-v", "error", "-y", "-i", str(src), "-filter_complex", graphe, "-map", "[o]",
                        "-frames:v", "1", str(out)], capture_output=True, text=True)
    return out if r.returncode == 0 else r.stderr[-300:]


def effet(src, eff, nom):
    g = ";".join(E.build_chain([eff], "0:v", "o", "fx", {"w": W, "h": H, "dur": 1.0, "fps": 30}))
    return passe(src, g, nom)


def ecart(a, b):
    """écart moyen par pixel (0..255) entre deux images, en niveaux de gris"""
    d = ImageChops.difference(Image.open(a).convert("L"), Image.open(b).convert("L"))
    return sum(d.getdata()) / (W * H)


def coefs(graphe):
    m = re.search(r"lenscorrection=k1=(-?[0-9.]+):k2=(-?[0-9.]+)", graphe)
    return (float(m.group(1)), float(m.group(2))) if m else None


def monotone(k1, k2):
    """r·(1 + k1·r² + k2·r⁴) strictement croissante sur [0, 1] — sinon l'image se replie"""
    return all(1 + 3 * k1 * (i / 100) ** 2 + 5 * k2 * (i / 100) ** 4 > 0 for i in range(101))


print("\n[1] D-17 — distorsion d'objectif : « corriger », et plus de repliement")
spec = E.param_spec("preset", "lensdistort")
check("o1_le_preset_corriger_est_au_catalogue", "corriger" in (spec.get("choices") or []), spec.get("choices"))
for preset in ("barillet", "coussinet", "corriger"):
    for t in (0, 55, 100):
        g = ";".join(E.build_chain([{"type": "lensdistort", "preset": preset, "intensity": t}], "0:v", "o", "fx",
                                   {"w": W, "h": H, "dur": 1.0, "fps": 30}))
        k = coefs(g)
        check(f"o1_{preset}_{t}_ne_se_replie_pas", k is not None and monotone(*k), (k, g[:120]))
# le témoin du défaut : les coefficients d'AVANT (coussinet, intensité 55 : k1 = −0,2425, k2 = −0,0606) se repliaient
check("o1_temoin_l_ancien_coussinet_se_repliait", not monotone(-0.2425, -0.0606))
# un grand-angle synthétique : la grille passée par le barillet SANS recadrage (ce que fait la lentille), puis corrigée
for t in (30, 55, 100):
    k1 = 0.05 + 0.35 * t / 100
    deforme = passe(GRILLE, f"[0:v]lenscorrection=k1={k1:.4f}:k2={k1 * 0.25:.4f}:i=bilinear[o]", f"bar{t}")
    corrige = effet(deforme, {"type": "lensdistort", "preset": "corriger", "intensity": t}, f"cor{t}")
    if isinstance(deforme, str) or isinstance(corrige, str):
        check(f"o1_corriger_{t}_rend", False, (deforme, corrige)); continue
    # GÉOMÉTRIE, pas pixels (un écart pixel à pixel sur des traits de 2 px mesure surtout le flou de deux
    # rééchantillonnages — mesuré : grille visiblement redressée, écart moyen inchangé) : la ligne verticale
    # d'origine x = 60 (à gauche, là où le barillet courbe le plus) est lue au milieu (y = 90) et en haut (y = 20).
    # Droite = mêmes x ; fidèle = x d'origine.
    def x_ligne(img, y, x0=60):
        im = Image.open(img).convert("L")
        # après le premier pixel BLANC : la bordure noire du barillet n'est pas la ligne
        x1 = next((x for x in range(W // 2) if im.getpixel((x, y)) > 200), W // 2)
        xs = [x for x in range(x1, W // 2) if im.getpixel((x, y)) < 100]
        return sum(xs) / len(xs) if xs else None
    xg, xb, xb2, xc, xc2 = (x_ligne(GRILLE, 90), x_ligne(deforme, 90), x_ligne(deforme, 20), x_ligne(corrige, 90),
                            x_ligne(corrige, 20))
    ok_mes = None not in (xg, xb, xb2, xc, xc2)
    check(f"o1_corriger_{t}_redresse_la_ligne_et_la_remet_a_sa_place",
          ok_mes and abs(xb - xb2) >= 2 and abs(xc - xc2) <= 1.0 and abs(xc - xg) <= 1.5,
          f"barillet : x {xb} (milieu) / {xb2} (haut) ; corrigé : {xc} / {xc2} ; origine {xg}")

print("\n[2] D-29 — les courbes restantes : Lum vs Sat, Sat vs Sat ; Hue vs Hue est DÉJÀ couvert")
cat = E.catalog()
for typ, cles in (("lumsat", ["ombres", "milieux", "lumieres"]), ("satsat", ["faibles", "moyennes", "fortes"])):
    c = cat.get(typ) or {}
    check(f"c2_{typ}_au_catalogue_etalonnage_trois_reglages_a_100",
          c.get("cat") == "etalonnage" and c.get("params") == cles
          and all(E.param_spec(k, typ).get("default") == 100 and E.param_spec(k, typ).get("max") == 200 for k in cles),
          (c.get("cat"), c.get("params"), [E.param_spec(k, typ) for k in cles]))
    g = ";".join(E.build_chain([{"type": typ}], "0:v", "o", "fx", {"w": W, "h": H, "dur": 1.0, "fps": 30}))
    check(f"c2_{typ}_a_100_partout_ne_fait_rien_(null,_pas_de_geq)", "null" in g and "geq" not in g, g)


def deux(c1, c2, nom):
    """une image : moitié gauche c1, moitié droite c2 (couleurs hex 0xRRGGBB)"""
    p = pathlib.Path(TMP) / f"{nom}.png"
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c={c1}:s={W}x{H},drawbox=x={W // 2}:y=0:w={W // 2}:h={H}:c={c2}:t=fill",
                    "-frames:v", "1", str(p)], check=True)
    return p


def sat(px):
    return max(px) - min(px)


src = deux("0x502020", "0xF0A0A0", "lum")           # rouge SOMBRE | rouge CLAIR
res = effet(src, {"type": "lumsat", "ombres": 0, "milieux": 100, "lumieres": 100}, "lumsat")
if isinstance(res, str):
    check("c2_lumsat_rend", False, res)
else:
    a, b = Image.open(src).convert("RGB"), Image.open(res).convert("RGB")
    g, d = b.getpixel((W // 4, H // 2)), b.getpixel((3 * W // 4, H // 2))
    check("c2_lumsat_ombres_a_0_le_rouge_sombre_devient_gris_le_clair_reste_rouge",
          sat(a.getpixel((W // 4, H // 2))) > 40 and sat(g) < sat(a.getpixel((W // 4, H // 2))) * 0.5
          and sat(d) > sat(a.getpixel((3 * W // 4, H // 2))) * 0.7,
          (a.getpixel((W // 4, H // 2)), g, a.getpixel((3 * W // 4, H // 2)), d))
src = deux("0xC8A8A8", "0xDC1E1E", "satsrc")        # rose PÂLE (faible saturation) | rouge VIF
res = effet(src, {"type": "satsat", "faibles": 0, "moyennes": 100, "fortes": 100}, "satsat")
if isinstance(res, str):
    check("c2_satsat_rend", False, res)
else:
    a, b = Image.open(src).convert("RGB"), Image.open(res).convert("RGB")
    g, d = b.getpixel((W // 4, H // 2)), b.getpixel((3 * W // 4, H // 2))
    check("c2_satsat_faibles_a_0_le_pale_devient_gris_le_vif_reste_vif",
          sat(g) <= 2 < 20 < sat(a.getpixel((W // 4, H // 2))) and sat(d) > sat(a.getpixel((3 * W // 4, H // 2))) * 0.85,
          (a.getpixel((W // 4, H // 2)), g, a.getpixel((3 * W // 4, H // 2)), d))
# Hue vs Hue : la teinte PAR BANDE de `huesat` (lot L5) — la spec le disait écarté ; mesuré le 07/10, il marche
src = deux("0xC82828", "0x28C828", "hue")
res = effet(src, {"type": "huesat", "colors": "r", "hue": 120, "sat": 0}, "huehue")
if isinstance(res, str):
    check("c2_huesat_rend", False, res)
else:
    b = Image.open(res).convert("RGB")
    g, d = b.getpixel((W // 4, H // 2)), b.getpixel((3 * W // 4, H // 2))
    check("c2_hue_vs_hue_est_couvert_le_rouge_tourne_au_vert_le_vert_ne_bouge_pas",
          g[1] > 150 and g[0] < 80 and d[1] > 150 and d[0] < 80 and abs(d[1] - 200) < 15, (g, d))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
