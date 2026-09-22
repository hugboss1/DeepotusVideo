# -*- coding: utf-8 -*-
"""L3 — BANC CROISE client/backend : les BORNES que la couche `montage.js`
ecrit en dur doivent etre CELLES du service, sinon le client envoie ce que
le backend clampe en silence (ou l'inverse : le lecteur montre en direct une
fenetre que le 480p ne rendra jamais). Fichier SEPARE de test_montage_l3.py
(un processus, un code de sortie) : il ne monte NI TestClient NI l'app —
il lit la couche en OCTETS et importe le service seul.
Run : & $PY tests/test_montage_l3_croise.py   (depuis backend/)

CE QUI EST COMPARE, ET COMMENT. Chaque literal de la couche est extrait par
une regex GARDEE : le temoin positif (la regex trouve EXACTEMENT UNE fois) est
une assertion a part entiere, avant toute lecture du groupe — faute n°6 :
aucune lecture nue, une regex qui ne trouve rien fait ROUGIR le banc, pas
mourir. Cote service, deux mesures pour chaque borne : le LITERAL dans la
source (meme regle, regex gardee sur montage_service.py) et le COMPORTEMENT
de la fonction sur une valeur hors borne (`_dz_spec`, `_v1_stab`,
`_motion_points`, `_v1_speed`) — un literal peut etre juste et la fonction
ne pas s'en servir.

  [1] D-13 : dzmDzNorm (w dans [.1, 1], x/y dans [0, 1−w], ease lin|doux)
      vs _dz_spec / _DZ_EASES ;
  [2] D-16 : dzmStabNorm (smooth 1..100 defaut 15, zoom −30..30 defaut 0,
      crop black|keep) vs _v1_stab ;
  [3] D-15 : dzmRetimeOf (blend|flow) vs les cles de _RETIME ; les bornes de
      vitesse de la rampe (`cl` : .25..4) vs _v1_speed ;
  [4] D-14 : DZM_MP_EXTRA (scale [.05, 3] au millieme, opacity [0, 1] au
      centieme) vs les 6-uplets de _motion_points (bornes de scale et
      d'opacity).

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
"""
import os
import re
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl3x_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    """Le fichier en OCTETS, decode, LF — ou "" (le banc rougit, ne meurt pas)."""
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def un(motif, texte, flags=0):
    """LA regex gardee : rend le match si le motif est trouve EXACTEMENT une
    fois, None sinon. Le compte est rendu a part pour le detail des lignes."""
    ms = list(re.finditer(motif, texte, flags))
    return (ms[0] if len(ms) == 1 else None), len(ms)


def num(m, i):
    """Groupe i du match en float, ou None — jamais un float() nu."""
    try:
        return float(m.group(i)) if m else None
    except (TypeError, ValueError):
        return None


JS = lire("frontend/patches/montage.js")
SVC = lire("backend/app/services/montage_service.py")
check("x0_la_couche_et_le_service_sont_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(SVC) > 100_000, (len(JS), len(SVC)))

try:
    from app.services import montage_service as MS      # noqa: E402
except Exception as e:                                  # le banc rougit
    MS = None
    print(f"  (import du service impossible : {e!r})")


def A(nom, defaut):
    return getattr(MS, nom, defaut) if MS is not None else defaut


# ── [1] D-13 : dzmDzNorm vs _dz_spec ─────────────────────────────────────
print("\n[1] D-13 : les bornes de la fenetre de zoom")
_fn = JS[JS.find("function dzmDzNorm(raw){"):JS.find("function dzmDzOf(c){")]
check("x1_dzmDzNorm_est_isole_dans_la_couche", 200 < len(_fn) < 2000, len(_fn))
mW, nW = un(r'o\["w"\+s\]=Math\.max\((\.\d+|\d+(?:\.\d+)?),Math\.min\((\d+(?:\.\d+)?),o\["w"\+s\]\)\);', _fn)
check("x1_la_borne_de_w_est_lue_une_fois_dans_la_couche", nW == 1 and mW is not None, nW)
mX, nX = un(r'o\["x"\+s\]=dzmDzR\(Math\.max\((\d+),Math\.min\((\d+)-o\["w"\+s\],o\["x"\+s\]\)\)\);', _fn)
mY, nY = un(r'o\["y"\+s\]=dzmDzR\(Math\.max\((\d+),Math\.min\((\d+)-o\["w"\+s\],o\["y"\+s\]\)\)\);', _fn)
check("x1_les_bornes_de_x_et_y_sont_lues_une_fois_chacune", nX == 1 and nY == 1, (nX, nY))
js_w = (num(mW, 1), num(mW, 2))
js_x = (num(mX, 1), num(mX, 2))
js_y = (num(mY, 1), num(mY, 2))
# le literal du service, par la meme regle
mSW, nSW = un(r'out\["w" \+ i\] = max\((\d+\.\d+), min\((\d+\.\d+), out\["w" \+ i\]\)\)', SVC)
mSX, nSX = un(r'out\["x" \+ i\] = max\((\d+\.\d+), min\((\d+\.\d+) - out\["w" \+ i\], out\["x" \+ i\]\)\)', SVC)
check("x1_le_service_ecrit_les_memes_literaux_de_w_et_x", nSW == 1 and nSX == 1
      and (num(mSW, 1), num(mSW, 2)) == js_w and (num(mSX, 1), num(mSX, 2)) == js_x, (nSW, nSX))
check("x1_w_est_borne_0_1_a_1_des_deux_cotes_et_x_y_dans_0_1_moins_w",
      js_w == (0.1, 1.0) and js_x == (0.0, 1.0) and js_y == (0.0, 1.0), (js_w, js_x, js_y))
# le COMPORTEMENT du service sur les bornes lues dans la couche
_dz = A("_dz_spec", lambda c: None)
_lo = _dz({"dz": {"x0": 0, "y0": 0, "w0": 1, "x1": 5, "y1": -1, "w1": 0.02}})
_hi = _dz({"dz": {"x0": 0.3, "y0": 0.3, "w0": 3, "x1": 0, "y1": 0, "w1": 0.5}})
check("x1_le_service_clampe_w_x_y_exactement_aux_bornes_de_la_couche",
      js_w[0] is not None and isinstance(_lo, dict) and isinstance(_hi, dict)
      and _lo["w1"] == js_w[0] and _hi["w0"] == js_w[1]
      and _lo["x1"] == js_x[1] - js_w[0] and _lo["y1"] == js_y[0]
      and _hi["x0"] == js_x[0] and _hi["y0"] == js_y[0], (_lo, _hi))
mE, nE = un(r'o\.ease=raw\.ease==="(\w+)"\?"\w+":"(\w+)";', _fn)
_eases = A("_DZ_EASES", ())
check("x1_les_deux_ease_de_la_couche_sont_ceux_du_service_et_le_defaut_est_doux",
      nE == 1 and mE is not None and set(_eases) == {mE.group(1), mE.group(2)}
      and mE.group(2) == "doux" and len(_eases) == 2, (nE, _eases))

# ── [2] D-16 : dzmStabNorm vs _v1_stab ───────────────────────────────────
print("\n[2] D-16 : les bornes de la stabilisation")
_fs = JS[JS.find("function dzmStabNorm(raw){"):JS.find("function dzmStabOf(c){")]
check("x2_dzmStabNorm_est_isole_dans_la_couche", 100 < len(_fs) < 1000, len(_fs))
mS, nS = un(r'smooth:n\(raw\.smooth,(-?\d+),(-?\d+),(-?\d+)\)', _fs)
mZ, nZ = un(r'zoom:n\(raw\.zoom,(-?\d+),(-?\d+),(-?\d+)\)', _fs)
mC, nC = un(r'crop:raw\.crop==="(\w+)"\?"\w+":"(\w+)"', _fs)
check("x2_smooth_zoom_et_crop_sont_lus_une_fois_chacun", nS == 1 and nZ == 1 and nC == 1, (nS, nZ, nC))
js_s = (num(mS, 1), num(mS, 2), num(mS, 3))
js_z = (num(mZ, 1), num(mZ, 2), num(mZ, 3))
mSS, nSS = un(r'"smooth": num\("smooth", (-?\d+), (-?\d+), (-?\d+)\)', SVC)
mSZ, nSZ = un(r'"zoom": num\("zoom", (-?\d+), (-?\d+), (-?\d+)\)', SVC)
check("x2_le_service_ecrit_les_memes_literaux_de_smooth_et_zoom",
      nSS == 1 and nSZ == 1 and (num(mSS, 1), num(mSS, 2), num(mSS, 3)) == js_s
      and (num(mSZ, 1), num(mSZ, 2), num(mSZ, 3)) == js_z, (nSS, nSZ, js_s, js_z))
check("x2_smooth_1_100_defaut_15_zoom_m30_30_defaut_0_des_deux_cotes",
      js_s == (1.0, 100.0, 15.0) and js_z == (-30.0, 30.0, 0.0), (js_s, js_z))
_st = A("_v1_stab", lambda c: None)
_sh = _st({"stab": {"on": True, "smooth": 10 ** 6, "zoom": 10 ** 6, "crop": mC.group(1) if mC else "?"}})
_sl = _st({"stab": {"on": True, "smooth": -(10 ** 6), "zoom": -(10 ** 6), "crop": "zzz"}})
_sd = _st({"stab": {"on": True}})
check("x2_le_service_clampe_et_defaute_exactement_aux_bornes_de_la_couche",
      js_s[0] is not None and isinstance(_sh, dict) and isinstance(_sl, dict) and isinstance(_sd, dict)
      and _sh["smooth"] == js_s[1] and _sl["smooth"] == js_s[0] and _sd["smooth"] == js_s[2]
      and _sh["zoom"] == js_z[1] and _sl["zoom"] == js_z[0] and _sd["zoom"] == js_z[2]
      and mC is not None and _sh["crop"] == mC.group(1) and _sl["crop"] == mC.group(2)
      and _sd["crop"] == mC.group(2), (_sh, _sl, _sd))
check("x2_crop_est_black_ou_keep_et_keep_est_le_defaut",
      mC is not None and (mC.group(1), mC.group(2)) == ("black", "keep"), mC and mC.groups())

# ── [3] D-15 : dzmRetimeOf vs _RETIME, la rampe vs _v1_speed ─────────────
print("\n[3] D-15 : le jeu de valeurs du retime et les bornes de vitesse")
mR, nR = un(r'function dzmRetimeOf\(c\)\{var v=c&&c\.retime;return v==="(\w+)"\|\|v==="(\w+)"\?v:null\}', JS)
_rt = A("_RETIME", {})
check("x3_dzmRetimeOf_est_lu_une_fois_et_ses_deux_valeurs_sont_les_cles_de_RETIME",
      nR == 1 and mR is not None and isinstance(_rt, dict) and len(_rt) == 2
      and set(_rt) == {mR.group(1), mR.group(2)}, (nR, sorted(_rt)))
_v1r = A("_v1_retime", lambda c: "ABSENT")
check("x3_le_service_accepte_les_deux_valeurs_de_la_couche_et_rien_d_autre",
      mR is not None and _v1r({"retime": mR.group(1)}) == mR.group(1)
      and _v1r({"retime": mR.group(2)}) == mR.group(2)
      and _v1r({"retime": "nearest"}) is None and _v1r({"retime": "zzz"}) is None,
      mR and mR.groups())
_fr = JS[JS.find("function dzmRampe(clips,id,t,spdL,spdR){"):JS.find("function dzmStabNorm(raw){")]
mV, nV = un(r'var cl=function\(v\)\{v=Number\(v\);return v>0\?Math\.max\((\.\d+|\d+(?:\.\d+)?),Math\.min\((\d+(?:\.\d+)?),v\)\):1\}', _fr)
check("x3_la_borne_de_vitesse_de_la_rampe_est_lue_une_fois", nV == 1 and mV is not None, nV)
js_v = (num(mV, 1), num(mV, 2))
mSV, nSV = un(r'f = max\((\d+\.\d+), min\((\d+\.\d+), f\)\)', SVC)
_sp = A("_v1_speed", lambda c: None)
check("x3_la_vitesse_est_bornee_0_25_4_des_deux_cotes_literal_et_comportement",
      js_v == (0.25, 4.0) and nSV == 1 and (num(mSV, 1), num(mSV, 2)) == js_v
      and _sp({"speed": 100}) == js_v[1] and _sp({"speed": 0.001}) == js_v[0], (js_v, nSV))
# une rampe a 0,3 s des bords : la couche refuse — le service, lui, borne la
# duree source a 0,05 s (d_src) ; la couche est PLUS stricte, et c'est voulu
mB, nB = un(r'if\(t-s<(\.\d+)\|\|e-t<(\.\d+)\)return ko\("bord"\);', _fr)
check("x3_la_rampe_refuse_a_0_3_s_des_deux_bords_meme_valeur_des_deux_cotes",
      nB == 1 and mB is not None and num(mB, 1) == num(mB, 2) == 0.3, (nB, mB and mB.groups()))

# ── [4] D-14 : DZM_MP_EXTRA vs _motion_points ────────────────────────────
print("\n[4] D-14 : les bornes d'echelle et d'opacite des points")
mM, nM = un(r'var DZM_MP_EXTRA=\{scale:\[(\.\d+|\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+)\],opacity:\[(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+)\]\};', JS)
check("x4_DZM_MP_EXTRA_est_lu_une_fois", nM == 1 and mM is not None, nM)
js_sc = (num(mM, 1), num(mM, 2))
js_op = (num(mM, 4), num(mM, 5))
mSc, nSc = un(r'\("scale", (\d+\.\d+), (\d+\.\d+)\)', SVC)
mOp, nOp = un(r'\("opacity", (\d+\.\d+), (\d+\.\d+)\)', SVC)
check("x4_le_service_ecrit_les_memes_literaux_de_scale_et_opacity",
      nSc == 1 and nOp == 1 and (num(mSc, 1), num(mSc, 2)) == js_sc
      and (num(mOp, 1), num(mOp, 2)) == js_op, (nSc, nOp, js_sc, js_op))
check("x4_scale_0_05_3_et_opacity_0_1_des_deux_cotes",
      js_sc == (0.05, 3.0) and js_op == (0.0, 1.0), (js_sc, js_op))
_mp = A("_motion_points", lambda c: None)
_p = _mp({"start": 0, "end": 3, "motion_points": [
    {"t": 0, "x": .5, "y": .5, "scale": 10 ** 6, "opacity": 10 ** 6},
    {"t": 1, "x": .5, "y": .5, "scale": -(10 ** 6), "opacity": -(10 ** 6)}]})
check("x4_le_service_clampe_scale_et_opacity_exactement_aux_bornes_de_la_couche",
      js_sc[0] is not None and isinstance(_p, list) and len(_p) == 2 and len(_p[0]) == 6
      and _p[0][4] == js_sc[1] and _p[1][4] == js_sc[0]
      and _p[0][5] == js_op[1] and _p[1][5] == js_op[0], _p)
# la precision de la couche (millieme / centieme) est CELLE du filtergraph :
# fnum ecrit scale a 3 decimales, colorchannelmixer aa a `%.3f`, l'opacite
# arrondie au centieme par la couche est transmise sans perte
check("x4_la_couche_arrondit_scale_au_millieme_et_opacity_au_centieme",
      mM is not None and num(mM, 3) == 1000 and num(mM, 6) == 100, mM and mM.groups())
# le plafond des points n'est PAS dans la couche : `SVM_MP_CAP` vit dans le
# corps du bundle (section R4b, lot anterieur) — lu dans le BUNDLE LIVRE.
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
mMax, nMax = un(r'^_MP_MAX_POINTS = (\d+)$', SVC, re.M)
mJmax, nJmax = un(r'var SVM_MP_CAP=(\d+),', BUN)
check("x4_le_plafond_de_huit_points_est_le_meme_service_et_bundle",
      len(BUN) > 1_000_000 and nMax == 1 and nJmax == 1
      and num(mMax, 1) == num(mJmax, 1) == 8 and A("_MP_MAX_POINTS", None) == 8,
      (len(BUN), nMax, nJmax))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
