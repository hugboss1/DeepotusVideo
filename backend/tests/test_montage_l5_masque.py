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
maskedmerge gbrap + scale2ref.
[5] Rendus reels V2 : effet `invert` visible sur l'overlay, ALPHA du PNG
conserve jusqu'a l'overlay, masque V2 (cover et transforme), 50 images.
[6] Espion /render : `mask` (V1, V2) et `effects` (V2) lus et assainis ;
masque invalide / pile vide -> cle ABSENTE (dict historique).

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
_g1 = mask_graph(_m1, 320, 180, 25, "mk0") if isinstance(_m1, dict) else "ABSENT"
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
          _e[0] == 0 and _e[1] == 50 and _e[2] and ECART(_e[2][0], _base[0]) >= 20
          and ECART(_e[2][1], _base[1]) <= 2 and ECART(_e[2][2], _base[2]) <= 2 and "alphamerge" in _e[4],
          (_e[:3], _base, _e[3]))
    check("v1_inv_centre_intact_coins_assombris_50_images",
          _i[0] == 0 and _i[1] == 50 and _i[2] and ECART(_i[2][0], _base[0]) <= 2
          and ECART(_i[2][1], _base[1]) >= 20 and ECART(_i[2][2], _base[2]) >= 20, (_i[:3], _base, _i[3]))
    check("v1_rectangle_net_centre_assombri_coin_intact",
          _r[0] == 0 and _r[1] == 50 and _r[2] and ECART(_r[2][0], _base[0]) >= 20
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
      and "[ofi0]negate[ofx0]" in _fc and "[ofx0]format=rgba,setpts=PTS-STARTPTS+1.0/TB[ov0]" in _fc
      and "negate" not in FC(_eg["cover"][0]), _fc[-400:])
_fco = FC(OVBUILD(effects=INV, opacity=0.5, tf=dict(TFS, rotate=12.0, radius=20)))
_ip, _io, _ig, _ir = (_fco.find("negate"), _fco.find("colorchannelmixer=aa=0.5"), _fco.find("geq=r="),
                      _fco.find("rotate="))
check("v2_transforme_effet_apres_echelle_avant_opacite_coins_rotation",
      "[1:v]scale=32:-2,setsar=1,fps=25,format=rgba[ofi0]" in _fco and 0 < _ip < _io < _ig < _ir
      and "[ofx0]format=rgba,colorchannelmixer=aa=0.5" in _fco, _fco[-600:])
_fcp = FC(OVBUILD(effects=INV, motion_points=_cas["points"]["motion_points"]))
check("v2_points_sendcmd_reste_en_tete_effet_avant_opacite_animee",
      _fcp.find("[1:v]sendcmd=c='") >= 0 and _fcp.find("[ofi0]") < _fcp.find("negate")
      < _fcp.find("colorchannelmixer@mpo0=aa=") and "[ofx0]format=rgba,colorchannelmixer@mpo0" in _fcp, _fcp[-500:])
_fcm = FC(OVBUILD(effects=INV, mask=ELL))
check("v2_masque_maskedmerge_gbrap_scale2ref_image_unique",
      "[ofi0]split[omo0][ome0]" in _fcm and "[ome0]negate[omf0]" in _fcm and "[omo0]format=gbrap[omb0]" in _fcm
      and "[omf0]format=gbrap[omg0]" in _fcm and "format=gbrap,geq=r='" in _fcm and ",trim=end_frame=1[omk0m]" in _fcm
      and "[omk0m][omg0]scale2ref[omk0][omr0]" in _fcm and "[omb0][omr0][omk0]maskedmerge[ofx0]" in _fcm
      and "loop=loop" not in _fcm and "maskedmerge" not in _fc, _fcm[-700:])
_fcd = FC(OVBUILD(effects=[{"type": "kaleido"}], tf=dict(TFS), dims=(200, 100)))
check("v2_contexte_des_effets_taille_reelle_de_l_overlay_mise_a_l_echelle",
      "scale=16:8" in _fcd and "scale=32:32" not in _fcd, _fcd[-400:])

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
