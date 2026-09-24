# -*- coding: utf-8 -*-
"""L5 T2 — D-30 MASQUE STATIQUE + EFFETS RENDUS SUR LES OVERLAYS V2 (backend).
En-tete et fin RECOPIES de tests/test_montage_l3.py (l.102-134, 1073-1086) :
dossier de donnees NEUF par execution, TestClient sans port ouvert, toute
lecture gardee — un banc qui meurt sur un acces nu ne dit pas quelles
assertions manquent. Fichier propre a T2 (ajustement du controleur, 24/09/2026 :
T1 cree tests/test_montage_l5.py en parallele).
Run : & $PY tests/test_montage_l5_masque.py   (depuis backend/)
      $env:L5_FF = "<ffmpeg.exe>" pour rejouer les rendus reels sur un autre
      binaire (production = %LOCALAPPDATA%/DeepotusVideoGen/bin, 9.0.1).

[1] mask_region.py (pur) : `mask_of` borne le champ `mask` d'un clip,
`mask_graph` rend UNE instruction de filtergraph — geq calcule UNE fois puis
`trim=end_frame=1,loop=loop=-1` (gris, V1) ou une image unique a quatre plans
gbrap (V2), jamais drawbox (mesure du plan : 235 en gris), `min()` a DEUX
arguments.
[2] Chaine V1 : sans masque (ou masque sans effet, ou masque invalide) la
commande est OCTET POUR OCTET celle de 81bfde3 — reference construite en
important le module depuis `git show 81bfde3:…/montage_service.py` ecrit dans
TMP (meme moteur d'effets pour les deux : seul le service change) ; avec
effets + masque : split / alphamerge / overlay=0:0:shortest=1.
[3] Rendu reel V1 : effet masque au centre, coin intact, 50 images.
[4] Chaine V2 : sans effet, commande identique a 81bfde3 (cover, transforme,
ombre, opacite, points) ; avec effets : pile rendue apres la mise a l'echelle,
avant opacite/coins/rotation, `format=rgba` ensuite ; avec masque :
maskedmerge gbrap, masque calcule a la taille de l'overlay (revue T2 second
tour : plus de scale2ref, deprecie) ; la pile recoit une copie OPAQUE
(lutrgb=a=255 : sinon alpha AU CARRE) ; `_timed` au format de l'overlay
(ctx fmt=gbrap), sans fmt octet pour octet 27b6b87 ; transforme sans dims ->
pile ignoree + warning (M1).
[5] Rendus reels V2 : effet `invert` visible sur l'overlay, ALPHA du PNG
conserve jusqu'a l'overlay, masque V2 (cover et transforme), 50 images ;
revue T2 : alpha restaure apres une pile qui le perd (vignette, invert borne
t0/t1 via `_timed`) ou le cree (chromakey), avec et sans masque ; second
tour, SANS PERTE (graphe rejoue en PNG) : PNG a zones alpha 128 / 0 / 255,
grade_basic neutre, curves, invert (temoin = PNG inverse sans effet), avec
et sans masque, +-3 ; invert borne sur damier 2 px, hors fenetre +-3.
[6] Espion /render : `mask` (V1, V2) et `effects` (V2) lus et assainis ;
masque invalide / pile vide -> cle ABSENTE (dict historique) ; espion
_probe_dims : sonde seulement si un type connu (M3), sonde en echec -> rendu
sans pile + warning (M1).

L'ETAT VIDE DE CE BANC : avant l'implementation `app.services.mask_region`
n'existe pas (A_MR rend des temoins "ABSENT"), la commande V1 ignore `mask`
(pas d'alphamerge) et la commande V2 ignore `effects` (pas de negate) : [1]
[2 alphamerge] [3] [4 effets] [5] [6] ROUGISSENT, les egalites a 81bfde3
restent vertes (temoins positifs : elles comparent des commandes non vides
qui commencent par ffmpeg).
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl5m_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON, ou {} — le banc doit ROUGIR, pas mourir sur un .json() nu."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

from app.services import montage_service as MS           # noqa: E402
try:
    from app.services import mask_region as MR           # noqa: E402
except Exception as _e:                                  # etat vide : rougir
    print("  (mask_region absent : %s)" % _e)
    MR = None


def A_MR(nom, defaut):
    """Attribut de mask_region, ou un temoin — jamais un AttributeError nu."""
    return getattr(MR, nom, defaut) if MR is not None else defaut


# --- reference 81bfde3 : le module du service tel qu'il etait --------------
_REPO = pathlib.Path(__file__).resolve().parents[2]
MSREF = None
try:
    _src = subprocess.run(["git", "show", "81bfde3:backend/app/services/montage_service.py"],
                          cwd=str(_REPO), capture_output=True, timeout=60).stdout
    _refp = pathlib.Path(TMP) / "ms_ref_81bfde3.py"
    _refp.write_bytes(_src)
    _spec = importlib.util.spec_from_file_location("ms_ref_81bfde3", str(_refp))
    MSREF = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(MSREF)
except Exception as _e:
    print("  (reference 81bfde3 injoignable : %s)" % _e)
    MSREF = None
check("ref_le_service_de_81bfde3_est_charge_depuis_git_show",
      MSREF is not None and hasattr(MSREF, "_build_montage_command") and MSREF is not MS,
      MSREF)

V1F = str(pathlib.Path(TMP) / "v1.mp4")
pathlib.Path(V1F).write_bytes(b"x")


def V1SPEC(**kw):
    """Forme d'un clip V1 pour `_build_montage_command`, RECOPIEE de
    tests/test_montage_l3.py (`V1SPEC`) — `d.update(kw)` accepte `mask=` et
    `effects=` comme n'importe quel champ."""
    d = {"path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def TL(name="l5", n=1, dur=4, src=None):
    """Timeline minimale pour /render — recopiee de tests/test_montage_l3.py."""
    return {"name": name, "ratio": "9:16", "duration": dur, "mix": {},
            "clips": [{"tr": "v1", "id": "v%d" % i, "start": 0, "end": 4,
                       "src": {"file_path": src or V1F}} for i in range(n)]}


def BUILD(mod=None, **kw):
    """`_build_montage_command` (module `mod`, defaut le service courant) avec
    les arguments constants de la section. Les mots-cles du clip vont au clip,
    le reste aux arguments nommes. Toute exception rend un temoin (faute n°6)."""
    mod = mod or MS
    clip = {k: kw.pop(k) for k in ("effects", "mask", "speed", "dz", "src_in") if k in kw}
    a = {"w": 64, "h": 64, "fps": 25, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": True,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    try:
        cmd, _ = mod._build_montage_command([V1SPEC(**clip)], [], [], None, **a)
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)
    return FLAT(cmd)


OVF = str(pathlib.Path(TMP) / "ov.png")
pathlib.Path(OVF).write_bytes(b"x")


def OVBUILD(mod=None, w=64, h=64, **ov):
    """`_build_montage_command` avec un V1 et UN overlay V2 (forme de la liste
    `v2` de /render) — RECOPIE de tests/test_montage_l3.py (`OVBUILD`) ;
    `motion_points=` passe par MS._motion_points comme /render le fait."""
    mod = mod or MS
    o = {"path": OVF, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
         "end": 3.0, "opacity": None, "tf": None, "mp": None, "layer": 0}
    mpts = ov.pop("motion_points", None)
    o.update(ov)
    if mpts is not None:
        o["mp"] = MS._motion_points({"start": o["start"], "end": o["end"], "motion_points": mpts})
    try:
        cmd, _ = mod._build_montage_command([V1SPEC()], [o], [], None, w=w, h=h, fps=25, mix_db={},
                                            ducking=False, duration_master=False, preview=True,
                                            out=os.path.join(TMP, "o.mp4"))
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)
    return FLAT(cmd)


def FC(flat):
    """Le filtergraph d'une commande aplatie (entre -filter_complex et -map)."""
    if "-filter_complex " not in flat:
        return ""
    return flat.split("-filter_complex ", 1)[1].split(" -map ", 1)[0]


ELL = {"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.1}
FXD = [{"type": "grade_basic", "exposure": -100}]

print("\n[1] mask_region : mask_of borne, mask_graph calcule le masque UNE fois")
mask_of = A_MR("mask_of", lambda raw: "ABSENT")
mask_graph = A_MR("mask_graph", lambda *a, **k: "ABSENT")
_m1 = mask_of(dict(ELL))
check("m1_un_masque_valide_est_rendu_borne_et_arrondi",
      _m1 == {"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.1, "inv": False}, _m1)
_m2 = mask_of({"shape": "rect", "x": -1, "y": 0.8, "w": 3, "h": 0.5, "soft": 9, "inv": True})
check("m1_bornes_x_dans_0_1_w_jusqu_au_bord_soft_0_5_inv_vrai",
      _m2 == {"shape": "rect", "x": 0.0, "y": 0.8, "w": 1.0, "h": 0.2, "soft": 0.5, "inv": True}, _m2)
_m3 = mask_of({"shape": "rect", "x": 0.123456, "y": 0.1, "w": 0.333333, "h": 0.3, "inv": "oui"})
check("m1_arrondi_1e_4_soft_absent_zero_inv_non_booleen_faux",
      _m3 == {"shape": "rect", "x": 0.1235, "y": 0.1, "w": 0.3333, "h": 0.3, "soft": 0.0, "inv": False}, _m3)
# negations avec temoin positif (_m1 est un dict valide dans la meme expression)
_nuls = [mask_of(v) for v in ({}, None, "rect", [1], {"shape": "star", "x": 0, "y": 0, "w": .5, "h": .5},
                               {"shape": "rect", "x": 0, "y": 0, "w": 0.005, "h": .5},
                               {"shape": "rect", "x": 0.995, "y": 0, "w": .5, "h": .5},
                               {"shape": "ellipse", "x": "a", "y": 0, "w": .5, "h": .5},
                               {"shape": "ellipse", "x": float("nan"), "y": 0, "w": .5, "h": .5},
                               {"shape": "rect", "x": 0, "y": 0, "h": .5})]
check("m1_forme_inconnue_non_dict_trop_petit_ou_illisible_rend_None",
      isinstance(_m1, dict) and _nuls == [None] * 10, _nuls)
# Revue T1 (24/09) : un BOOLEEN n'est pas un nombre (float(True) == 1.0).
# x/y/w/h booleens -> None comme illisibles ; soft booleen -> 0 ; inv vrai
# seulement pour le booleen True. Temoins : les memes valeurs en nombres
# (0 / 1 entiers, soft 0.2) sont lues.
_bool = [mask_of({"shape": "rect", "x": False, "y": 0, "w": .5, "h": .5}),
         mask_of({"shape": "rect", "x": 0, "y": False, "w": .5, "h": .5}),
         mask_of({"shape": "rect", "x": 0, "y": 0, "w": True, "h": .5}),
         mask_of({"shape": "ellipse", "x": 0, "y": 0, "w": .5, "h": True})]
_bnum = mask_of({"shape": "rect", "x": 0, "y": 0, "w": 1, "h": .5})
check("m1_booleens_x_y_w_h_illisibles_temoin_entiers_lus",
      _bool == [None] * 4
      and _bnum == {"shape": "rect", "x": 0.0, "y": 0.0, "w": 1.0, "h": 0.5, "soft": 0.0, "inv": False},
      str((_bool, _bnum)))
_bs = mask_of({"shape": "rect", "x": 0, "y": 0, "w": .5, "h": .5, "soft": True})
_bs2 = mask_of({"shape": "rect", "x": 0, "y": 0, "w": .5, "h": .5, "soft": 0.2})
_bi1 = mask_of({"shape": "rect", "x": 0, "y": 0, "w": .5, "h": .5, "inv": 1})
_biT = mask_of({"shape": "rect", "x": 0, "y": 0, "w": .5, "h": .5, "inv": True})
check("m1_soft_booleen_zero_inv_vrai_seulement_pour_True",
      isinstance(_bs, dict) and _bs.get("soft") == 0.0
      and isinstance(_bs2, dict) and _bs2.get("soft") == 0.2
      and isinstance(_bi1, dict) and _bi1.get("inv") is False
      and isinstance(_biT, dict) and _biT.get("inv") is True,
      str((_bs, _bs2, _bi1, _biT)))
# Revue T4 (24/09, point T4-4) : une CHAINE n'est lue que si elle est du decimal ASCII -- la MEME expression que la
# regle des courbes (effects_engine._CURVE_NUM) : float() de Python accepte « 1_0 » (10) et les chiffres Unicode
# (« ٠.٥ », « ０.５ ») que Number() de JS refuse (dzmRfNum) -> divergence avec la couche. Mesure avant correctif :
# les chaines decimales ASCII (« 0.5 », « 0.5 » entoure de blancs, « 5e-1 », « .5 », « 5. ») sont LUES : gardees.
_sA = [mask_of({"shape": "rect", "x": 0, "y": 0, "w": w, "h": .5}) for w in ("0.5", " 0.5 ", "5e-1", ".5", "+0.5")]
_sR = [mask_of({"shape": "rect", "x": 0, "y": 0, "w": w, "h": .5}) for w in ("1_0", "٠.٥", "０.５", "0x1", "inf", "1e999")]
_sS = [mask_of({"shape": "rect", "x": 0, "y": 0, "w": .5, "h": .5, "soft": s}) for s in ("1_0", "0.2")]
_W5 = {"shape": "rect", "x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5, "soft": 0.0, "inv": False}
check("m1_chaines_decimal_ascii_lues_underscore_et_chiffres_unicode_refuses_soft_1_0_zero",
      _sA == [_W5] * 5 and _sR == [None] * 6
      and _sS == [_W5, dict(_W5, soft=0.2)], str((_sA, _sR, _sS)))
try:
    from app.services import mask_region as _mr_mod, effects_engine as _ee_mod
    _mr_num = (getattr(getattr(_mr_mod, "_NUM", None), "pattern", None), getattr(_ee_mod, "_CURVE_NUM", None))
except Exception as _e:
    _mr_num = ("import", repr(_e))
check("m1_expression_des_chaines_identique_a_celle_des_courbes",
      isinstance(_mr_num[1], str) and len(_mr_num[1]) > 20 and _mr_num[0] == _mr_num[1], _mr_num)
_g1 =mask_graph(_m1, 320, 180, 25, "mk0") if isinstance(_m1, dict) else "ABSENT"
check("m1_mask_graph_geq_une_fois_trim_loop_gris_etiquette",
      isinstance(_g1, str) and _g1.startswith("color=c=black:s=320x180:r=25:d=1,format=gray,geq=lum='")
      and _g1.endswith(",trim=end_frame=1,loop=loop=-1:size=1:start=0[mk0]") and "hypot(" in _g1
      and "drawbox" not in _g1 and "255-(" not in _g1, _g1)
_gi = mask_graph(dict(_m1, inv=True), 320, 180, 25, "mk0") if isinstance(_m1, dict) else "ABSENT"
check("m1_inv_est_255_moins_le_masque",
      isinstance(_gi, str) and "geq=lum='255-(255*clip(" in _gi and "255-(" not in _g1, (_gi, _g1))
_gr = mask_graph(_m2, 320, 180, 25, "mk1") if isinstance(_m2, dict) else "ABSENT"
_nmin = 0
if isinstance(_gr, str):
    # chaque min( doit avoir exactement UNE virgule de premier niveau
    for _i in [k for k in range(len(_gr)) if _gr.startswith("min(", k)]:
        _d, _v, _j = 0, 0, _i + 4
        while _j < len(_gr):
            if _gr[_j] == "(":
                _d += 1
            elif _gr[_j] == ")":
                if _d == 0:
                    break
                _d -= 1
            elif _gr[_j] == "," and _d == 0:
                _v += 1
            _j += 1
        _nmin += 1 if _v == 1 else 100
check("m1_rectangle_min_a_deux_arguments_seulement_et_255_moins_si_inv",
      isinstance(_gr, str) and _nmin == 3 and "geq=lum='255-(" in _gr and "drawbox" not in _gr, (_nmin, _gr))
_g4 = mask_graph(_m1, 320, 180, 25, "omk0", planes="gbrap", loop=False) if isinstance(_m1, dict) else "ABSENT"
check("m1_v2_quatre_plans_gbrap_image_unique_sans_loop",
      isinstance(_g4, str) and _g4.startswith("color=c=black@0:s=320x180:r=25:d=1,format=gbrap,geq=r='")
      and ":g='" in _g4 and ":b='" in _g4 and ":a='" in _g4 and _g4.endswith(",trim=end_frame=1[omk0]")
      and "loop=" not in _g4 and "loop=loop=-1" in _g1, _g4)

print("\n[2] chaine V1 : sans masque octet pour octet 81bfde3, avec masque alphamerge")
_ref0, _ref1 = BUILD(MSREF), BUILD(MSREF, effects=FXD)
check("v1_sans_effet_sans_masque_identique_a_81bfde3",
      _ref0.startswith("ffmpeg") and BUILD() == _ref0, (BUILD()[:200], _ref0[:200]))
check("v1_avec_effets_sans_masque_identique_a_81bfde3",
      _ref1.startswith("ffmpeg") and "eq=" in _ref1 and BUILD(effects=FXD) == _ref1, FC(BUILD(effects=FXD))[-300:])
check("v1_masque_sans_effet_ignore_identique_a_81bfde3",
      _ref0.startswith("ffmpeg") and BUILD(mask=ELL) == _ref0 and BUILD(mask=ELL, effects=[]) == _ref0,
      FC(BUILD(mask=ELL))[-200:])
check("v1_masque_invalide_ignore_identique_a_81bfde3",
      _ref1.startswith("ffmpeg") and BUILD(effects=FXD, mask={"shape": "star"}) == _ref1
      and BUILD(effects=FXD, mask="x") == _ref1, FC(BUILD(effects=FXD, mask={"shape": "star"}))[-200:])
_fm = FC(BUILD(effects=FXD, mask=ELL))
check("v1_effets_et_masque_split_alphamerge_overlay_shortest",
      "[n0pre]split[mo0][me0]" in _fm and "[mf0]format=yuva420p[mfa0]" in _fm
      and "trim=end_frame=1,loop=loop=-1:size=1:start=0[mk0]" in _fm and "[mfa0][mk0]alphamerge[mm0]" in _fm
      and "[mo0][mm0]overlay=0:0:shortest=1,format=yuv420p[n0]" in _fm
      and "[me0]" in _fm and "[mf0]" in _fm.split("[mf0]format")[0] and "alphamerge" not in FC(_ref1),
      _fm[-600:])

# --- ffmpeg reel -----------------------------------------------------------
_FB = None
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    _FB = os.environ.get("L5_FF") or _fb()
    print("  (ffmpeg : %s)" % subprocess.run([_FB, "-version"], capture_output=True, text=True,
                                            timeout=30).stdout.splitlines()[0])
except Exception as _e:
    _FB = None
    print("  (ffmpeg injoignable : %s)" % _e)
try:
    from PIL import Image as _Im
except Exception:
    _Im = None
_FP = None
if _FB:
    _FP = os.path.join(os.path.dirname(_FB), "ffprobe")


def GEN(nom, lavfi, d=2):
    p = str(pathlib.Path(TMP) / nom)
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i", lavfi, "-t", str(d),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", p], check=False, capture_output=True, timeout=60)
    return p


def RENDER(v1, v2, out, w=320, h=180):
    """(rc, erreur, images) du rendu reel de la commande du service."""
    try:
        cmd, _ = MS._build_montage_command(v1, v2, [], None, w=w, h=h, fps=25, mix_db={},
                                           ducking=False, duration_master=False, preview=True, out=out)
    except Exception as e:                 # faute n°6 : rougir, pas mourir
        return -1, "%s: %s" % (type(e).__name__, e), -1, ""
    try:                                   # un graphe qui ne finit pas (masque infini) : rougir
        r = subprocess.run([_FB] + list(cmd[1:]), check=False, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "le graphe ne finit pas en 90 s", -1, FLAT(cmd)
    nb = -1
    try:
        p = subprocess.run([_FP, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", out],
                           check=False, capture_output=True, text=True, timeout=60)
        nb = int((p.stdout or "").strip() or -1)
    except (ValueError, OSError):
        pass
    return r.returncode, (r.stderr or "")[-400:], nb, FLAT(cmd)


def PX(mp4, t, pts):
    """Pixels RGB aux points `pts` de l'image a t, ou None."""
    png = mp4 + ".%s.png" % t
    subprocess.run([_FB, "-y", "-loglevel", "error", "-ss", str(t), "-i", mp4, "-frames:v", "1", png],
                   check=False, capture_output=True, timeout=60)
    if _Im is None or not os.path.isfile(png):
        return None
    im = _Im.open(png).convert("RGB")
    return [im.getpixel(p) for p in pts]


def ECART(a, b):
    return max(abs(x - y) for x, y in zip(a, b)) if a and b else -1


print("\n[3] rendu reel V1 : effet masque au centre, coin intact, 50 images")
if not _FB or _Im is None:
    check("v1_rendu_reel_SKIP_sans_ffmpeg_ou_pillow", True)
else:
    _G = GEN("gris.mp4", "color=c=gray:s=320x180:r=25")
    _PTS = [(160, 90), (8, 8), (312, 172)]
    _res = {}
    for _k, _mk in (("sans", None), ("ell", ELL), ("inv", dict(ELL, inv=True)),
                    ("rect", {"shape": "rect", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.0})):
        _o = os.path.join(TMP, "v1_%s.mp4" % _k)
        _sp = V1SPEC(path=_G, src_dur=2.0, end=2.0, effects=FXD, **({"mask": _mk} if _mk else {}))
        _rc, _er, _nb, _cm = RENDER([_sp], [], _o)
        _res[_k] = (_rc, _nb, PX(_o, 1, _PTS) if _rc == 0 else None, _er, _cm)
    _base = PX(_G, 1, _PTS)
    _s, _e, _i, _r = _res["sans"], _res["ell"], _res["inv"], _res["rect"]
    check("v1_temoin_effet_plein_cadre_assombrit_tout",
          _s[0] == 0 and _s[2] and _base and ECART(_s[2][0], _base[0]) >= 20 and ECART(_s[2][1], _base[1]) >= 20,
          (_s[:3], _base, _s[3]))
    check("v1_ellipse_centre_assombri_coins_intacts_50_images",
          _e[0] == 0 and _e[1] == 50 and _e[2] and _base and ECART(_e[2][0], _base[0]) >= 20
          and ECART(_e[2][1], _base[1]) <= 2 and ECART(_e[2][2], _base[2]) <= 2 and "alphamerge" in _e[4],
          (_e[:3], _base, _e[3]))
    check("v1_inv_centre_intact_coins_assombris_50_images",
          _i[0] == 0 and _i[1] == 50 and _i[2] and _base and ECART(_i[2][0], _base[0]) <= 2
          and ECART(_i[2][1], _base[1]) >= 20 and ECART(_i[2][2], _base[2]) >= 20, (_i[:3], _base, _i[3]))
    check("v1_rectangle_net_centre_assombri_coin_intact",
          _r[0] == 0 and _r[1] == 50 and _r[2] and _base and ECART(_r[2][0], _base[0]) >= 20
          and ECART(_r[2][1], _base[1]) <= 2, (_r[:3], _base, _r[3]))

print("\n[4] chaine V2 : sans effet 81bfde3, effets apres l'echelle, masque maskedmerge")
TFS = {"x": 0.5, "y": 0.5, "scale": 0.5, "rotate": 0.0}
_cas = {"cover": {}, "opacite": {"opacity": 0.5}, "tf": {"tf": dict(TFS)},
        "tf_rot_coins_ombre": {"tf": dict(TFS, rotate=12.0, radius=20, shadow=True), "opacity": 0.7},
        "points": {"motion_points": [{"t": 0, "x": .5, "y": .5, "scale": .5, "opacity": 1},
                                     {"t": 2, "x": .5, "y": .5, "scale": 1.0, "opacity": .2}]}}
_eg = {k: (OVBUILD(MSREF, **dict(v)), OVBUILD(**dict(v))) for k, v in _cas.items()}
check("v2_sans_effet_commande_identique_a_81bfde3_cinq_formes",
      all(a.startswith("ffmpeg") and a == b for a, b in _eg.values()),
      {k: (a[:80], b[:80]) for k, (a, b) in _eg.items() if a != b})
_eg2 = {k: OVBUILD(**dict(v, effects=[], mask=ELL)) for k, v in _cas.items()}
check("v2_pile_vide_et_masque_seul_ignores_identiques_a_81bfde3",
      all(_eg[k][0].startswith("ffmpeg") and _eg2[k] == _eg[k][0] for k in _cas), [k for k in _cas if _eg2[k] != _eg[k][0]])
INV = [{"type": "invert"}]
_fc = FC(OVBUILD(effects=INV))
check("v2_cover_effets_apres_fps_puis_format_rgba_puis_setpts",
      "[1:v]scale=64:64:force_original_aspect_ratio=increase,crop=64:64,setsar=1,fps=25[ofi0]" in _fc
      and "[ofa0]negate[ofq0]" in _fc and "[ofx0]format=rgba,setpts=PTS-STARTPTS+1.0/TB[ov0]" in _fc
      and "negate" not in FC(_eg["cover"][0]), _fc[-400:])
# Revue T2 second tour (C1, mesure 24/09/2026) : la pile recevait l'alpha
# d'origine et le RENDAIT (28 effets le conservent) -> blend multiply =
# alpha AU CARRE (PNG a=128 : 128 -> 64). La pile recoit une copie OPAQUE.
check("v2_pile_recoit_une_copie_opaque_lutrgb_a_255",
      "[ofs0]lutrgb=a=255[ofa0]" in _fc and "[ofs0]negate" not in _fc and "lutrgb" not in FC(_eg["cover"][0]),
      _fc[-600:])
# Revue T2 (24/09/2026, ffmpeg 9.0.1) : 14 effets du catalogue et toute
# enveloppe `_timed` (format=yuv420p) PERDAIENT l'alpha du PNG -> cadre noir
# opaque. Alpha final = alpha d'ORIGINE x alpha de sortie de la pile : les
# deux branches en gbrap, blend c3 multiply (c0..c2 : normal, opacite 1 = la
# pile telle quelle) — pas de gris intermediaire (piege 235 de la plage).
# `format=rgba` AVANT le split : les sorties d'un split partagent UN format,
# un effet sans alpha (vignette) tirait sinon l'original en yuv420p (mesure).
check("v2_alpha_restaure_split_origine_blend_c3_multiply_gbrap",
      "[ofi0]format=rgba,split[ofo0][ofs0]" in _fc and "[ofq0]format=gbrap[ofg0]" in _fc
      and "[ofo0]format=gbrap[ofb0]" in _fc and "[ofg0][ofb0]blend=c3_mode=multiply[ofx0]" in _fc
      and "blend=c3_mode" not in FC(_eg["cover"][0]), _fc[-600:])
_fco = FC(OVBUILD(effects=INV, opacity=0.5, tf=dict(TFS, rotate=12.0, radius=20), dims=(64, 64)))
_ip, _io, _ig, _ir = (_fco.find("negate"), _fco.find("colorchannelmixer=aa=0.5"), _fco.find("geq=r="),
                      _fco.find("rotate="))
check("v2_transforme_effet_apres_echelle_avant_opacite_coins_rotation",
      "[1:v]scale=32:-2,setsar=1,fps=25,format=rgba[ofi0]" in _fco and 0 < _ip < _io < _ig < _ir
      and "[ofx0]format=rgba,colorchannelmixer=aa=0.5" in _fco, _fco[-600:])
_fcp = FC(OVBUILD(effects=INV, motion_points=_cas["points"]["motion_points"], dims=(64, 64)))
check("v2_points_sendcmd_reste_en_tete_effet_avant_opacite_animee",
      _fcp.find("[1:v]sendcmd=c='") >= 0 and _fcp.find("[ofi0]") < _fcp.find("negate")
      < _fcp.find("colorchannelmixer@mpo0=aa=") and "[ofx0]format=rgba,colorchannelmixer@mpo0" in _fcp, _fcp[-500:])
# Revue T2 second tour (I1) : scale2ref est DEPRECIE (8.1.1 et 9.0.1
# l'impriment, mesure 24/09/2026) -> le masque est calcule DIRECTEMENT a la
# taille de l'overlay (fxw x fxh : exacte, _ov_fx_dims mesuree contre scale ;
# cover = w x h) ; plus de mise a l'echelle du masque du tout.
_fcm = FC(OVBUILD(effects=INV, mask=ELL))
check("v2_masque_maskedmerge_gbrap_copie_opaque_masque_a_la_taille_de_l_overlay",
      "[ofi0]format=rgba,split[omo0][ome0]" in _fcm and "[ome0]lutrgb=a=255[oma0]" in _fcm
      and "[oma0]negate[omf0]" in _fcm
      and "[omo0]format=gbrap,split[omb0][omq0]" in _fcm and "[omf0]format=gbrap[omg0]" in _fcm
      and "[omg0][omq0]blend=c3_mode=multiply[omh0]" in _fcm
      and "color=c=black@0:s=64x64:r=25:d=1,format=gbrap,geq=r='" in _fcm and ",trim=end_frame=1[omk0]" in _fcm
      and "[omb0][omh0][omk0]maskedmerge[ofx0]" in _fcm
      and "scale2ref" not in _fcm and "rw:rh" not in _fcm
      and "loop=loop" not in _fcm and "maskedmerge" not in _fc, _fcm[-700:])
_fcmt = FC(OVBUILD(effects=INV, mask=ELL, tf=dict(TFS), dims=(200, 100)))
check("v2_masque_transforme_calcule_a_fxw_fxh_sans_scale2ref",
      "color=c=black@0:s=32x16:r=25:d=1,format=gbrap,geq=r='" in _fcmt
      and "[omb0][omh0][omk0]maskedmerge[ofx0]" in _fcmt and "scale2ref" not in _fcmt
      and "s=64x64:r=25:d=1,format=gbrap" not in _fcmt, _fcmt[-700:])
_fcd = FC(OVBUILD(effects=[{"type": "kaleido"}], tf=dict(TFS), dims=(200, 100)))
check("v2_contexte_des_effets_taille_reelle_de_l_overlay_mise_a_l_echelle",
      "scale=16:8" in _fcd and "scale=32:32" not in _fcd, _fcd[-400:])

# Revue T2 second tour (M1) : chaine TRANSFORMEE sans `dims` (ffprobe en
# echec) -> la taille de l'overlay est inconnue, 16 effets du catalogue font
# tomber le graphe (pad/crop/hstack sur ctx w/h faux) : pile (et masque)
# ignores avec warning, commande = celle sans effet. Cover : la taille est
# w x h quelles que soient les dims -> la pile reste (temoin).
from loguru import logger as _LG                          # noqa: E402
WARN = []
_LG.add(lambda m: WARN.append(str(m)), level="WARNING")
WARN.clear()
_sans_dims = OVBUILD(effects=INV, mask=ELL, tf=dict(TFS))
_w_sd = [x for x in WARN if "pile" in x and "dimensions" in x]
check("m1_transforme_sans_dims_pile_ignoree_warning_commande_sans_effet",
      _sans_dims.startswith("ffmpeg") and _sans_dims == OVBUILD(tf=dict(TFS)) and "negate" not in _sans_dims
      and "maskedmerge" not in _sans_dims and len(_w_sd) == 1
      and "negate" in OVBUILD(effects=INV, tf=dict(TFS), dims=(64, 64)), (FC(_sans_dims)[-300:], WARN))
WARN.clear()
_cov_sd = OVBUILD(effects=INV)
check("m1_cover_sans_dims_pile_gardee_sans_warning",
      "negate" in _cov_sd and not [x for x in WARN if "pile" in x], (FC(_cov_sd)[-200:], WARN))

# Revue T2 second tour (I2) : `_timed` passait l'overlay V2 par yuv420p ->
# hors fenetre, chroma sous-echantillonnee et alpha perdu. Le format de
# l'enveloppe vient de ctx["fmt"] ; SANS fmt la chaine est OCTET POUR OCTET
# celle de HEAD (V1, D-9, apercu, grading, template) — reference : le moteur
# de 27b6b87 charge depuis git show.
FXREF = None
try:
    _srcf = subprocess.run(["git", "show", "27b6b87:backend/app/services/effects_engine.py"],
                           cwd=str(_REPO), capture_output=True, timeout=60).stdout
    _reff = pathlib.Path(TMP) / "fx_ref_27b6b87.py"
    _reff.write_bytes(_srcf)
    _spf = importlib.util.spec_from_file_location("fx_ref_27b6b87", str(_reff))
    FXREF = importlib.util.module_from_spec(_spf)
    _spf.loader.exec_module(FXREF)
except Exception as _e:
    print("  (moteur 27b6b87 injoignable : %s)" % _e)
from app.services import effects_engine as FXC            # noqa: E402
_BORNES = [dict(e, t0=0.5, t1=1.5, fade_in=0.2) for e in
           ({"type": "invert"}, {"type": "bloom"}, {"type": "vignette"}, {"type": "chromakey"},
            {"type": "grade_basic", "exposure": 20}, {"type": "shake"}, {"type": "pixelate"}, {"type": "grain"})]
_CTX = {"w": 320, "h": 180, "dur": 4.0, "fps": 25}
_eqs = []
for _e in _BORNES:
    try:
        _a, _b = FXREF.build_chain([_e], "i", "o", "u", dict(_CTX)), FXC.build_chain([_e], "i", "o", "u", dict(_CTX))
    except Exception as _x:
        _a, _b = ["REF"], [str(_x)]
    _eqs.append(_a == _b and any("format=yuv420p,split=2" in s for s in _a))
check("i2_sans_fmt_enveloppe_octet_pour_octet_27b6b87_huit_effets_bornes",
      FXREF is not None and _eqs == [True] * 8, _eqs)
_g = FXC.build_chain([_BORNES[0]], "i", "o", "u", dict(_CTX, fmt="gbrap"))
check("i2_fmt_gbrap_enveloppe_sans_yuv420p",
      "[i]format=gbrap,split=2[ue0enva][ue0envb]" in _g and "[ue0envw]format=gbrap[ue0envwf]" in _g
      and not any("yuv420p" in s for s in _g), _g)
_fct = FC(OVBUILD(effects=[dict(INV[0], t0=0.5, t1=1.0)], tf=dict(TFS), dims=(64, 64)))
check("i2_v2_borne_enveloppe_en_gbrap", "format=gbrap,split=2[ofe0e0enva]" in _fct
      and "format=yuv420p,split=2[ofe0e0env" not in _fct, _fct[-600:])

print("\n[5] rendus reels V2 : effet visible, alpha conserve, masque")
if not _FB or _Im is None:
    check("v2_rendu_reel_SKIP_sans_ffmpeg_ou_pillow", True)
else:
    _B = GEN("bleu.mp4", "color=c=blue:s=320x180:r=25")
    _PNGH = str(pathlib.Path(TMP) / "demi.png")
    _ph = _Im.new("RGBA", (320, 180), (0, 0, 0, 0))
    _ph.paste((220, 20, 20, 255), (0, 0, 160, 180))
    _ph.save(_PNGH)
    _P2 = [(80, 90), (240, 90), (150, 90), (20, 90), (90, 90)]

    def OV(**kw):
        o = {"path": _PNGH, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 0.0, "end": 2.0,
             "opacity": None, "tf": None, "mp": None, "layer": 0, "dims": (320, 180)}
        o.update(kw)
        return o
    _v1b = V1SPEC(path=_B, src_dur=2.0, end=2.0)
    _rv = {}
    for _k, _ov in (("sans", OV()), ("inv", OV(effects=INV)), ("inv_masque", OV(effects=INV, mask=ELL)),
                    ("tf_inv_masque", OV(effects=INV, mask=ELL, tf=dict(TFS)))):
        _o = os.path.join(TMP, "v2_%s.mp4" % _k)
        _rc, _er, _nb, _cm = RENDER([_v1b], [_ov], _o)
        _rv[_k] = (_rc, _nb, PX(_o, 1, _P2) if _rc == 0 else None, _er)
    _s, _i, _m, _t = _rv["sans"], _rv["inv"], _rv["inv_masque"], _rv["tf_inv_masque"]

    def ROUGE(p): return p[0] >= 180 and p[1] <= 70 and p[2] <= 70
    def CYAN(p): return p[0] <= 70 and p[1] >= 180 and p[2] >= 180
    def BLEU(p): return p[0] <= 60 and p[1] <= 60 and p[2] >= 200
    check("v2_temoin_sans_effet_rouge_a_gauche_bleu_a_droite",
          _s[0] == 0 and _s[1] == 50 and _s[2] and ROUGE(_s[2][0]) and BLEU(_s[2][1]), _s)
    check("v2_invert_rendu_sur_l_overlay_et_alpha_du_png_conserve",
          _i[0] == 0 and _i[1] == 50 and _i[2] and CYAN(_i[2][0]) and BLEU(_i[2][1]) and ROUGE(_s[2][0]), _i)
    check("v2_masque_cover_effet_dans_l_ellipse_seulement_alpha_conserve",
          _m[0] == 0 and _m[1] == 50 and _m[2] and CYAN(_m[2][2]) and ROUGE(_m[2][3]) and BLEU(_m[2][1]), _m)
    check("v2_masque_transforme_scale2ref_a_la_taille_de_l_overlay",
          _t[0] == 0 and _t[1] == 50 and _t[2] and CYAN(_t[2][2]) and ROUGE(_t[2][4]) and BLEU(_t[2][3]), _t)

    # Revue T2 (24/09/2026, 9.0.1) : une pile qui PERD l'alpha (vignette, et
    # toute enveloppe `_timed` bornee t0/t1, passee par yuv420p) rendait le
    # cadre NOIR OPAQUE sur tout le clip ; chromakey doit au contraire CREER
    # de la transparence. Points : gauche rouge, droite dans l'ellipse ELL,
    # droite hors ellipse, centre, bord gauche hors ellipse.
    _P3 = [(80, 90), (200, 90), (300, 90), (160, 90), (20, 90)]
    _GV = GEN("vert.mp4", "color=c=0x00FF00:s=320x180:r=25")
    VIG = [{"type": "vignette"}]
    TINV = [{"type": "invert", "t0": 0.5, "t1": 1.0}]
    CK = [{"type": "chromakey"}]
    _VID = {"path": _GV, "is_image": False, "src_dur": 2.0}
    _ra = {}
    for _k, _ov in (("vig", OV(effects=VIG)), ("tinv", OV(effects=TINV)),
                    ("ck", OV(effects=CK, **_VID)), ("ck_masque", OV(effects=CK, mask=ELL, **_VID)),
                    ("vig_masque", OV(effects=VIG, mask=ELL))):
        _o = os.path.join(TMP, "v2a_%s.mp4" % _k)
        _rc, _er, _nb, _cm = RENDER([_v1b], [_ov], _o)
        _ra[_k] = (_rc, _nb, {_t: PX(_o, _t, _P3) for _t in (0.2, 0.7, 1.5)} if _rc == 0 else None, _er)

    def PA(k, t, i):
        """Pixel i du rendu k a t, ou None (jamais d'indexation nue)."""
        try:
            return _ra[k][2][t][i]
        except (TypeError, KeyError, IndexError):
            return None

    def EST(f, p): return p is not None and f(p)
    def VERT(p): return p[0] <= 70 and p[1] >= 180 and p[2] <= 70
    def ROUGEATRE(p): return p[0] >= 90 and p[1] <= 70 and p[2] <= 70
    def OK50(k): return _ra[k][0] == 0 and _ra[k][1] == 50

    def DET(k): return (_ra[k][0], _ra[k][1], _ra[k][2], (_ra[k][3] or "")[-200:])
    check("v2_vignette_non_bornee_alpha_du_png_conserve_v1_bleu_visible",
          OK50("vig") and EST(BLEU, PA("vig", 0.7, 1)) and EST(BLEU, PA("vig", 0.7, 2))
          and EST(ROUGEATRE, PA("vig", 0.7, 0)), DET("vig"))
    check("v2_invert_borne_bleu_avant_et_apres_la_fenetre_effet_dedans",
          OK50("tinv") and all(EST(BLEU, PA("tinv", _t, 1)) and EST(BLEU, PA("tinv", _t, 2))
                               for _t in (0.2, 0.7, 1.5))
          and EST(ROUGE, PA("tinv", 0.2, 0)) and EST(CYAN, PA("tinv", 0.7, 0)) and EST(ROUGE, PA("tinv", 1.5, 0)),
          DET("tinv"))
    check("v2_chromakey_source_verte_opaque_v1_visible_partout",
          OK50("ck") and all(EST(BLEU, PA("ck", 0.7, _i)) for _i in range(5)), DET("ck"))
    check("v2_chromakey_masque_v1_dans_l_ellipse_vert_dehors",
          OK50("ck_masque") and EST(BLEU, PA("ck_masque", 0.7, 3)) and EST(BLEU, PA("ck_masque", 0.7, 1))
          and EST(VERT, PA("ck_masque", 0.7, 4)) and EST(VERT, PA("ck_masque", 0.7, 2)), DET("ck_masque"))
    check("v2_vignette_masque_alpha_conserve_dedans_et_dehors",
          OK50("vig_masque") and EST(BLEU, PA("vig_masque", 0.7, 1)) and EST(BLEU, PA("vig_masque", 0.7, 2))
          and EST(ROUGE, PA("vig_masque", 0.7, 4)), DET("vig_masque"))

    # Revue T2 second tour (C1, I2) — mesures SANS PERTE : le graphe du
    # service est rejoue avec une sortie PNG d'une seule image a t (-ss de
    # sortie), jamais par l'encodeur (l'image x264 depend des images voisines).
    def RAWF(ov, t, nom):
        """Image RGB a t du graphe du service (V1 bleu + `ov`), ou le texte
        de l'erreur (faute n°6 : jamais d'exception nue)."""
        out = os.path.join(TMP, "raw_%s.mp4" % nom)
        try:
            cmd, _ = MS._build_montage_command([_v1b], [ov], [], None, w=320, h=180, fps=25, mix_db={},
                                               ducking=False, duration_master=False, preview=True, out=out)
            cmd = [str(x) for x in cmd]
            i = cmd.index("-filter_complex")
            png = os.path.join(TMP, "raw_%s_%s.png" % (nom, t))
            r = subprocess.run([_FB, "-y", "-v", "error"] + cmd[1:i] + ["-filter_complex", cmd[i + 1], "-map",
                                cmd[cmd.index("-map") + 1], "-ss", str(t), "-frames:v", "1", png],
                               capture_output=True, text=True, timeout=120)
            if r.returncode or not os.path.isfile(png):
                return "rc=%s %s" % (r.returncode, (r.stderr or "")[-300:])
            return _Im.open(png).convert("RGB")
        except Exception as e:
            return "%s: %s" % (type(e).__name__, e)

    def DMAX(a, b, box):
        """Ecart RGB max entre deux images sur la boite (x0, y0, x1, y1), -1 si
        l'une manque."""
        if isinstance(a, str) or isinstance(b, str):
            return -1
        return max(max(abs(p - q) for p, q in zip(a.getpixel((x, y)), b.getpixel((x, y))))
                   for x in range(box[0], box[2]) for y in range(box[1], box[3]))

    # PNG a TROIS zones d'alpha : 128 (gauche), 0 (milieu), 255 (droite).
    def A3(col, nom):
        p = str(pathlib.Path(TMP) / nom)
        im = _Im.new("RGBA", (320, 180), (0, 0, 0, 0))
        im.paste(col + (128,), (0, 0, 106, 180))
        im.paste(col + (255,), (214, 0, 320, 180))
        im.save(p)
        return p
    _A3 = A3((200, 60, 40), "a3.png")
    _A3I = A3((55, 195, 215), "a3_inv.png")          # la meme, couleur inversee
    _Z = {"a128": (20, 40, 86, 140), "a0": (126, 40, 194, 140), "a255": (234, 40, 300, 140)}
    FULL = {"shape": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "soft": 0}
    GBN = [{"type": "grade_basic"}]
    CRV = [{"type": "curves", "pts_m": "0/0 0.5/0.502 1/1"}]
    _t = RAWF(OV(path=_A3), 0.7, "a3_sans")
    _ti = RAWF(OV(path=_A3I), 0.7, "a3i_sans")
    _zb = {k: DMAX(_t, _ti, b) for k, b in _Z.items()}
    check("c1_temoins_a3_rendus_zone_a0_identique_zones_128_255_distinctes",
          _zb.get("a0") == 0 and _zb.get("a128", 0) >= 40 and _zb.get("a255", 0) >= 100, (_zb, _t, _ti))
    for _nom, _pile, _ref in (("grade_basic_neutre", GBN, _t), ("curves_quasi_neutre", CRV, _t),
                              ("invert", INV, _ti)):
        for _mq in (None, FULL):
            _r = RAWF(OV(path=_A3, effects=_pile, **({"mask": _mq} if _mq else {})), 0.7,
                      "a3_%s_%s" % (_nom, "m" if _mq else "n"))
            _ec = {k: DMAX(_r, _ref, b) for k, b in _Z.items()}
            check("c1_%s_%s_alpha_d_origine_128_0_255_egal_au_temoin_3" % (_nom, "masque" if _mq else "sans_masque"),
                  all(0 <= v <= 3 for v in _ec.values()), (_ec, _r if isinstance(_r, str) else ""))

    # I2 : invert borne 0.5..1.0 sur un DAMIER 2 px (alpha 255 / 128 / 0) :
    # hors fenetre, l'overlay == temoin sans effet (+-3) ; dedans, inverse.
    _DM = str(pathlib.Path(TMP) / "damier.png")
    _dm = _Im.new("RGBA", (320, 180), (0, 0, 0, 0))
    for _x in range(214):
        for _y in range(180):
            _dm.putpixel((_x, _y), ((255, 0, 0) if (_x // 2 + _y // 2) % 2 else (0, 255, 0))
                         + (255 if _x < 106 else 128,))
    _dm.save(_DM)
    _BOX = (0, 0, 320, 180)
    _ds = {t: RAWF(OV(path=_DM), t, "dm_sans") for t in (0.2, 0.7, 1.5)}
    _dt = {t: RAWF(OV(path=_DM, effects=[dict(INV[0], t0=0.5, t1=1.0)]), t, "dm_tinv") for t in (0.2, 0.7, 1.5)}
    _dx = {t: DMAX(_ds[t], _dt[t], _BOX) for t in _ds}
    check("i2_invert_borne_damier_2px_hors_fenetre_egal_au_temoin_3_dedans_inverse",
          0 <= _dx[0.2] <= 3 and 0 <= _dx[1.5] <= 3 and _dx[0.7] >= 200,
          (_dx, [v for v in list(_ds.values()) + list(_dt.values()) if isinstance(v, str)][:2]))

print("\n[6] espion /render : mask V1/V2 et effects V2 lus et assainis")
_SRCR = GEN("src_r.mp4", "testsrc2=s=64x64:r=25", d=4) if _FB else V1F
_PNGR = str(pathlib.Path(TMP) / "ovr.png")
if _Im is not None:
    _Im.new("RGBA", (64, 64), (255, 0, 0, 255)).save(_PNGR)
_cap = {}
_vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg


def _espion(*a, **k):
    _cap["v1"], _cap["v2"] = (a[0] if a else None), (a[1] if len(a) > 1 else None)
    _cmd = _vrai_build(*a, **k)
    _cap["cmd"] = FLAT(_cmd[0] if isinstance(_cmd, tuple) else _cmd)
    return _cmd


def RENDU(v1extra, v2extra):
    _cap.clear()
    tl = TL("rendu", n=1, src=_SRCR); tl["preview"] = True
    tl["clips"][0].update(v1extra)
    tl["clips"].append(dict({"tr": "v2", "id": "o", "src": {"file_path": _PNGR}, "start": 0, "end": 2}, **v2extra))
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        r = c.post("/api/montage/render", json=tl)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
    v1 = (_cap.get("v1") or [{}])[0] if isinstance(_cap.get("v1"), list) else {}
    v2 = (_cap.get("v2") or [{}])[0] if isinstance(_cap.get("v2"), list) and _cap.get("v2") else {}
    return r.status_code, v1, v2


_st, _a1, _a2 = RENDU({"effects": FXD, "mask": dict(ELL, x=-3, inv=1, extra="z")},
                      {"effects": INV + ["x", {"type": "nope"}], "mask": dict(ELL, shape="rect", soft=2)})
check("r_mask_v1_lu_et_borne",
      _st == 200 and _a1.get("mask") == {"shape": "ellipse", "x": 0.0, "y": 0.25, "w": 0.5, "h": 0.5,
                                         "soft": 0.1, "inv": False}, (_st, _a1.get("mask")))
check("r_effects_v2_lus_seuls_les_dicts_et_mask_v2_borne",
      _st == 200 and _a2.get("effects") == [{"type": "invert"}, {"type": "nope"}]
      and _a2.get("mask") == {"shape": "rect", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.5, "inv": False}
      and "negate" in (_cap.get("cmd") or "") and "maskedmerge" in (_cap.get("cmd") or ""),
      (_st, _a2.get("effects"), _a2.get("mask"), (_cap.get("cmd") or "")[-300:]))
check("r_dims_v2_sondees_quand_une_pile_est_posee",
      _st == 200 and tuple(_a2.get("dims") or ()) == (64, 64), _a2.get("dims"))
_st0, _b1, _b2 = RENDU({"mask": {"shape": "star"}}, {"mask": "x", "effects": []})
check("r_masque_invalide_et_pile_vide_cles_absentes_dict_historique",
      isinstance(_a1.get("mask"), dict) and _st0 == 200 and "path" in _b1 and "path" in _b2
      and "mask" not in _b1 and "mask" not in _b2 and "effects" not in _b2 and "dims" not in _b2,
      (_st0, sorted(_b1), sorted(_b2)))

# Revue T2 second tour (M1, M3) : espion sur _probe_dims.
_vrai_dims = MS._probe_dims
_sondes = []


def _dims_espion(p):
    _sondes.append(str(p))
    return _vrai_dims(p)


def RENDU_D(v2extra, dims_fn):
    MS._probe_dims = dims_fn
    try:
        return RENDU({}, v2extra)
    finally:
        MS._probe_dims = _vrai_dims


_sondes.clear()
_s3a = RENDU_D({"effects": [{"type": "nope"}, {"type": "zz"}]}, _dims_espion)
_n_inc = len([p for p in _sondes if p.endswith("ovr.png")])
_sondes.clear()
_s3b = RENDU_D({"effects": INV}, _dims_espion)
_n_con = len([p for p in _sondes if p.endswith("ovr.png")])
check("m3_dims_sondees_seulement_si_la_pile_porte_un_effet_connu",
      _s3a[0] == 200 and _n_inc == 0 and "effects" not in _s3a[2] and "dims" not in _s3a[2]
      and _s3b[0] == 200 and _n_con == 1 and tuple(_s3b[2].get("dims") or ()) == (64, 64),
      (_s3a[0], _n_inc, sorted(_s3a[2]), _s3b[0], _n_con, _s3b[2].get("dims")))
WARN.clear()
_s1 = RENDU_D({"effects": INV, "mask": dict(ELL), "scale": 0.5}, lambda p: None)
_cm1 = _cap.get("cmd") or ""
_w1 = [x for x in WARN if "pile" in x and "dimensions" in x]
_s1t = RENDU_D({"effects": INV, "scale": 0.5}, _vrai_dims)
_cm1t = _cap.get("cmd") or ""
check("m1_espion_sonde_en_echec_rendu_construit_sans_pile_et_warning",
      _s1[0] == 200 and _cm1.startswith("ffmpeg") and "negate" not in _cm1 and "maskedmerge" not in _cm1
      and len(_w1) == 1 and _s1t[0] == 200 and "negate" in _cm1t,
      (_s1[0], _cm1[-300:], WARN, _s1t[0]))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
# Nettoyage : le journal loguru et le pool sqlite tiennent encore des handles
# apres le lifespan (mesure : logs/*.log, t.db-wal/-shm survivaient a un
# rmtree nu) — on les ferme d'abord, puis on efface sans jamais rougir.
try:
    from loguru import logger as _lg
    _lg.remove()
    import asyncio as _aio
    from app.services import storage as _st
    _aio.run(_st._engine.dispose())
except Exception as _e:
    print("  (fermeture des handles : %s)" % _e)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
