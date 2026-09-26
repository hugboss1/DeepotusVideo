# -*- coding: utf-8 -*-
"""Retours L6 (26/09/2026), tache 3 — `grade-frame` en MODE CADRE, `scopes` en
TAILLE. En-tete recopie de test_montage_l5.py (env, check, J, TestClient sans
port ouvert ; fin : fermeture des handles puis rmtree) : dossier de donnees
NEUF par execution, toute lecture gardee — un banc qui meurt sur un acces nu
ne dit pas quelles assertions manquent (faute n6 : le DETAIL est evalue AVANT
le court-circuit de la condition, il ne doit donc jamais lever).
Run : & $PY tests/test_retours_grade.py   (depuis backend/)
Rejoue sur l'autre binaire : PATH=C:\\Users\\olivi\\AppData\\Local\\DeepotusVideoGen\\bin;$PATH

[1] SANS `cadre` : OCTET POUR OCTET le comportement de 62f0c75 — le module
    `grading` de 62f0c75 (git show) est charge a cote du courant ; memes
    commandes ffmpeg (espion sur `_MM._run`), memes noms de cache, memes
    octets d'image (PNG, JPEG, scopes).
[2] AVEC `cadre` (route) : l'image est au format du CADRE du projet (cover +
    crop du rendu, `_reframe_crop` D-40 au temps de SOURCE, zoompan D-13
    `_dz_filter` au temps LOCAL sur `cadre.dur`), largeur 96..1280 paire
    (defaut 720) ; masque au centre du CADRE ; effets bornes au temps local.
[3] `scopes` : `size` 256..1024 pair (defaut 512 inchange), `cadre` aussi.
[4] semaphore 2 sur `grade-frame` (comme `/scopes`), 499 client parti.
[5] l'image `cadre` == une image d'un RENDU Preview REEL
    (`_build_montage_command`) au meme instant : ecart moyen par pixel <= 6/255.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil, time, threading, importlib.util
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzrg_")
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

import asyncio                                           # noqa: E402
from PIL import Image as _PI                             # noqa: E402
from app.services import effects_preview as PV           # noqa: E402
from app.services import montage_media as MM             # noqa: E402
from app.services import montage_service as MS           # noqa: E402
from app.services import grading as GR                   # noqa: E402

FF = shutil.which("ffmpeg") or PV.ffmpeg_bin()
try:
    _ver = subprocess.run([FF, "-version"], capture_output=True, text=True, timeout=30).stdout.split("\n")[0]
except Exception:                                        # noqa: BLE001
    _ver = ""
print("  ffmpeg :", _ver[:60] or "INJOIGNABLE")


def CALL(mod, nom, *a, **k):
    """mod.nom(*a, **k), ou une chaine temoin — jamais d'exception."""
    f = getattr(mod, nom, None) if mod is not None else None
    if f is None:
        return "ABSENT"
    try:
        return f(*a, **k)
    except Exception as e:                               # noqa: BLE001
        return "EXC %s: %s" % (type(e).__name__, e)


def IMG(p):
    try:
        return _PI.open(p).convert("RGB").copy()
    except Exception:                                    # noqa: BLE001
        return None


def SZ(p):
    im = IMG(p)
    return im.size if im is not None else None


def PX(p, fx, fy):
    """Pixel RVB a la FRACTION (fx, fy) de l'image, ou None."""
    im = p if isinstance(p, _PI.Image) else IMG(p)
    try:
        return im.getpixel((min(im.size[0] - 1, int(fx * im.size[0])),
                            min(im.size[1] - 1, int(fy * im.size[1]))))
    except Exception:                                    # noqa: BLE001
        return None


def LUM(p, fx=0.5, fy=0.5):
    v = PX(p, fx, fy)
    return None if v is None else round(sum(v) / 3.0, 1)


def DOM(p, fx=0.5, fy=0.5):
    """Canal dominant 'r'|'g'|'b' (ou '?') du pixel a (fx, fy)."""
    v = PX(p, fx, fy)
    if v is None:
        return None
    m = max(v)
    if m < 80 or sorted(v)[1] > m - 60:
        return "?"
    return "rgb"[v.index(m)]


def ECART(a, b):
    """Ecart moyen par pixel et par canal (0..255) de deux images, `b` mise a
    la taille de `a` ; None si illisible."""
    try:
        ia = a if isinstance(a, _PI.Image) else IMG(a)
        ib = b if isinstance(b, _PI.Image) else IMG(b)
        ib = ib.resize(ia.size, _PI.BILINEAR)
        pa, pb = ia.tobytes(), ib.tobytes()
        return round(sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa), 2)
    except Exception:                                    # noqa: BLE001
        return None


def OCTETS(p):
    try:
        return pathlib.Path(p).read_bytes()
    except Exception:                                    # noqa: BLE001
        return None


# --- fixtures (480x270 = 16:9, 25 i/s, 4 s) ---------------------------------
FXD = pathlib.Path(TMP) / "rg"
FXD.mkdir(parents=True, exist_ok=True)


def MKV(nom, extra, d=4):
    out = FXD / nom
    args = [FF, "-y", "-v", "error"] + extra + ["-t", str(d), "-pix_fmt", "yuv420p", str(out)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return str(out) if r.returncode == 0 and out.is_file() else None
    except Exception:                                    # noqa: BLE001
        return None


_C = lambda col, s: ["-f", "lavfi", "-i", f"color=c={col}:s={s}:r=25:d=4"]  # noqa: E731
# Trois bandes verticales rouge | vert | bleu (160 px chacune) : un cadre 9:16
# CENTRE (largeur 0,316 de la source) ne voit que du vert.
BANDES = MKV("bandes.mp4", _C("0xdd2020", "160x270") + _C("0x20dd20", "160x270") + _C("0x2020dd", "160x270")
             + ["-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3"])
# Haut blanc, bas noir : le zoom D-13 fenetre en haut -> tout blanc.
HB = MKV("hb.mp4", _C("white", "480x135") + _C("black", "480x135") + ["-filter_complex", "[0:v][1:v]vstack"])
PLAT = MKV("plat.mp4", _C("0x808080", "480x270"))
TS = MKV("ts.mp4", ["-f", "lavfi", "-i", "testsrc2=s=480x270:r=25:d=4"])
check("r0_fixtures_fabriquees", None not in (BANDES, HB, PLAT, TS), str((BANDES, HB, PLAT, TS)))

EXPO = [{"type": "grade_basic", "exposure": -100}]
MSK = {"shape": "ellipse", "x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4, "soft": 0}


def _vide_cache():
    try:
        for f in MM._cache_dir().glob("*"):
            if f.name.endswith(("_grade.png", "_grade.jpg", "_scopes.png")):
                f.unlink(missing_ok=True)
    except Exception:                                    # noqa: BLE001
        pass


# =============================================================================
print("\n[1] sans cadre : octet pour octet 62f0c75")
# =============================================================================
_ANC = None
try:
    _src = subprocess.run(["git", "show", "62f0c75:backend/app/services/grading.py"], capture_output=True,
                          timeout=60, cwd=os.path.dirname(os.path.abspath(__file__))).stdout
    _pa = pathlib.Path(TMP) / "grading_62f0c75.py"
    _pa.write_bytes(_src)
    _sp = importlib.util.spec_from_file_location("grading_62f0c75", str(_pa))
    _ANC = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(_ANC)
except Exception as _e:                                  # noqa: BLE001
    print("  (grading de 62f0c75 illisible : %r)" % _e)
check("r1_temoin_module_62f0c75_charge_sans_cadre_ni_size",
      _ANC is not None and hasattr(_ANC, "graded_frame")
      and "cadre" not in getattr(getattr(_ANC, "graded_frame", None), "__code__", type("x", (), {"co_varnames": ()})).co_varnames,
      str(_ANC))

_vrai_run = MM._run
_cmds = []


def _run_espion(cmd, **k):
    _cmds.append(list(cmd))
    return _vrai_run(cmd, **k)


def JUMEAUX(mod_nom, *a):
    """(nom, octets, commandes) pour l'ancien PUIS le courant, cache vide
    avant chacun ; chaque element est un temoin lisible en cas d'echec."""
    res = []
    for mod in (_ANC, GR):
        _vide_cache()
        _cmds.clear()
        MM._run = _run_espion
        try:
            p = CALL(mod, mod_nom, *a)
        finally:
            MM._run = _vrai_run
        # Le DERNIER argument est le temporaire d'ecriture (`_tmp_de` : suffixe
        # aleatoire, mesure) : il est ramene au nom de la cible.
        res.append((getattr(p, "name", p), OCTETS(p) if isinstance(p, pathlib.Path) else None,
                    [x[:-1] + [pathlib.Path(x[-1]).name.split(".")[0]] for x in _cmds if x and x[0] == "ffmpeg"]))
    return res


for _lbl, _nom, _args in (
        ("png_512_defaut", "graded_frame", (TS, 1.0)),
        ("jpg_240_pile_masque", "graded_frame", (TS, 1.0, EXPO, MSK, 240, "jpg")),
        ("png_640_borne", "graded_frame", (BANDES, 2.0, [dict(EXPO[0], t0=5, t1=6)], None, 640, "png")),
        ("scopes_512", "scopes_png", (TS, 1.0, EXPO, MSK))):
    _a, _b = JUMEAUX(_nom, *_args)
    check(f"r1_{_lbl}_meme_nom_memes_octets_meme_commande",
          _a[1] is not None and _a == _b and len(_a[2]) >= 1,
          str((_a[0], _b[0], len(_a[1] or b""), len(_b[1] or b""), _a[2] == _b[2],
               [" ".join(x)[-160:] for x in _b[2]] if _a[2] != _b[2] else "")))

# Temoin : l'espion VOIT une difference (une largeur autre change la commande).
_d1 = JUMEAUX("graded_frame", TS, 1.0, None, None, 240, "jpg")
_d2 = JUMEAUX("graded_frame", TS, 1.0, None, None, 242, "jpg")
check("r1_temoin_une_largeur_autre_change_commande_et_nom",
      _d1[1][2] != _d2[1][2] and _d1[1][0] != _d2[1][0], str((_d1[1][0], _d2[1][0])))


# --- routes : Request starlette reelle (patron test_montage_l5.py) ---------
def RQ(body, hote="127.0.0.1", path="/api/montage/x"):
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")

    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": path, "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": (hote, 5000)}, rcv)


def RQ_PARTI(body, hote="127.0.0.1", path="/api/montage/x"):
    """Request dont le client est PARTI : le corps, puis `http.disconnect` a chaque lecture."""
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")
    msgs = [{"type": "http.request", "body": raw, "more_body": False}]

    async def rcv():
        return msgs.pop(0) if msgs else {"type": "http.disconnect"}
    return _R({"type": "http", "method": "POST", "path": path, "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": (hote, 5000)}, rcv)


def ROUTE(nom, body, hote="127.0.0.1"):
    """(statut, chemin, entetes) ; l'absence de la route est un temoin."""
    f = getattr(MS, nom, None)
    if f is None:
        return ("ABSENT", None, None)
    try:
        r = asyncio.run(f(RQ(body, hote)))
    except Exception as e:                               # noqa: BLE001
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)), None)
    return (getattr(r, "status_code", None), getattr(r, "path", None), dict(getattr(r, "headers", {}) or {}))


def GF(src, t=1.0, **kw):
    """POST grade-frame -> (statut, image PIL|detail)."""
    b = {"src": {"file_path": src}, "t": t}
    b.update(kw)
    st, p, _ = ROUTE("montage_grade_frame", b)
    return st, (IMG(p) if st == 200 else p)


def GFS(src, t=1.0, **kw):
    st, im = GF(src, t, **kw)
    return (st, im.size if isinstance(im, _PI.Image) else im)


# =============================================================================
print("\n[2] grade-frame en mode cadre")
# =============================================================================
check("r2_temoin_sans_cadre_240_rapport_source_bande_rouge_a_gauche",
      GFS(BANDES) == (200, (240, 136)) and DOM(GF(BANDES)[1], 0.05) == "r", str((GFS(BANDES), DOM(GF(BANDES)[1], 0.05))))
_s916 = GF(BANDES, cadre={"ratio": "9:16", "t_local": 1.0})
check("r2_cadre_916_sur_source_169_image_720x1280_toute_verte",
      _s916[0] == 200 and isinstance(_s916[1], _PI.Image) and _s916[1].size == (720, 1280)
      and [DOM(_s916[1], x, 0.5) for x in (0.02, 0.5, 0.98)] == ["g", "g", "g"],
      str((_s916[0], getattr(_s916[1], "size", _s916[1]), [DOM(_s916[1], x, 0.5) for x in (0.02, 0.5, 0.98)])))
_rat = {r: GFS(BANDES, cadre={"ratio": r, "t_local": 0}) for r in ("16:9", "1:1", "4:5")}
check("r2_cadre_quatre_ratios_dimensions_du_canvas",
      _rat == {"16:9": (200, (720, 406)), "1:1": (200, (720, 720)), "4:5": (200, (720, 900))}, str(_rat))
_ww = {k: GFS(BANDES, cadre={"ratio": "9:16", "t_local": 0}, w=v)
       for k, v in (("w1280", 1280), ("w1281", 1281), ("w90", 90), ("abc", "abc"), ("w721", 721), ("inf", "inf"))}
check("r2_cadre_w_96_1280_pair_defaut_720",
      _ww == {"w1280": (200, (1280, 2276)), "w1281": (200, (1280, 2276)), "w90": (200, (96, 170)),
              "abc": (200, (720, 1280)), "w721": (200, (720, 1280)), "inf": (200, (720, 1280))}, str(_ww))
check("r2_temoin_sans_cadre_w_1280_reste_borne_a_640",
      GFS(BANDES, w=1280) == (200, (640, 360)), str(GFS(BANDES, w=1280)))
_rinc = GFS(BANDES, cadre={"ratio": "7:3", "t_local": 0})
check("r2_cadre_ratio_inconnu_9_16_comme_le_rendu", _rinc == (200, (720, 1280)), str(_rinc))
_bad = {k: GF(BANDES, cadre=v)[0] for k, v in (
    ("texte", "9:16"), ("liste", [1]), ("tl_abc", {"ratio": "9:16", "t_local": "abc"}),
    ("tl_neg", {"ratio": "9:16", "t_local": -1}), ("vide", {}))}
check("r2_cadre_illisible_400_temoin_objet_vide_200",
      _bad == {"texte": 400, "liste": 400, "tl_abc": 400, "tl_neg": 400, "vide": 200}, str(_bad))
# Revue T3 (I) : un ratio NON HACHABLE levait TypeError dans `in _CANVAS` -> 500.
_rh = {k: GFS(PLAT, cadre={"ratio": v, "t_local": 0}, w=96)
       for k, v in (("liste", [1]), ("objet", {}), ("bool", True), ("nul", None), ("nombre", 916))}
check("r2_cadre_ratio_liste_objet_booleen_nul_nombre_200_en_9_16",
      _rh == {k: (200, (96, 170)) for k in ("liste", "objet", "bool", "nul", "nombre")}, str(_rh))
# ... et AUCUN champ du cadre (ni w/size, ni bornes d'effet) ne fait un 500, sur les deux routes.
_ETR = ([1], {}, True, "x", None, [[{}, []]], {"t": [1], "x": {}})
_fz = []
for _champ in ("ratio", "t_local", "dur", "reframe", "dz"):
    for _v in _ETR:
        _fz.append(({"cadre": {"ratio": "9:16", "t_local": 0, _champ: _v}, "w": 96}, {"size": 256}))
for _v in ({"mode": [1]}, {"mode": {}}, {"mode": "manuel", "x": [1]}, {"mode": "manuel", "x": True},
           {"mode": "suivi", "points": [[{}, []], {"t": {}, "x": [1]}, 5]}, {"mode": "suivi", "points": {}}):
    _fz.append(({"cadre": {"ratio": "9:16", "t_local": 0, "reframe": _v}, "w": 96}, {"size": 256}))
for _v in ({"x0": [1], "y0": {}, "w0": True, "x1": 0, "y1": 0, "w1": 1}, {"ease": [1], "x0": 0, "y0": 0, "w0": 0.5,
           "x1": 0, "y1": 0, "w1": 0.5}):
    _fz.append(({"cadre": {"ratio": "9:16", "t_local": 0, "dur": 2, "dz": _v}, "w": 96}, {"size": 256}))
_fz.append(({"cadre": {"ratio": "9:16", "t_local": 0}, "w": [1],
             "effects": [dict(EXPO[0], t0=[1], t1={}), dict(EXPO[0], t0=True, t1="x")]}, {"size": {}}))
_fzs = []
for _b, _extra in _fz:
    _s1 = ROUTE("montage_grade_frame", dict({"src": {"file_path": PLAT}, "t": 1.0}, **_b))[0]
    _bs = {k: v for k, v in _b.items() if k != "w"}
    _s2 = ROUTE("montage_scopes", dict({"src": {"file_path": PLAT}, "t": 1.0}, **_bs, **_extra))[0]
    _fzs.append((_s1, _s2))
_mauvais = [(_fz[i][0], s) for i, s in enumerate(_fzs) if not all(x in (200, 400) for x in s)]
check("r2_cadre_types_inattendus_jamais_500_sur_les_deux_routes_%d_cas" % (2 * len(_fz)),
      not _mauvais and len(_fzs) == len(_fz) >= 40 and (200, 200) in _fzs and any(400 in s for s in _fzs),
      str(_mauvais[:4]))

# D-40 : recadrage manuel et suivi (temps ABSOLU de source = `t`).
_rm = {x: DOM(GF(BANDES, cadre={"ratio": "9:16", "t_local": 0, "reframe": {"mode": "manuel", "x": x}})[1])
       for x in (0.0, 0.5, 1.0)}
check("r2_reframe_manuel_x0_rouge_x05_vert_x1_bleu", _rm == {0.0: "r", 0.5: "g", 1.0: "b"}, str(_rm))
_SUIVI = {"mode": "suivi", "points": [{"t": 0, "x": 0}, {"t": 4, "x": 1}]}
_rs = (DOM(GF(BANDES, 0.2, cadre={"ratio": "9:16", "t_local": 0.2, "reframe": _SUIVI})[1]),
       DOM(GF(BANDES, 3.8, cadre={"ratio": "9:16", "t_local": 0.1, "reframe": _SUIVI})[1]),
       DOM(GF(BANDES, 3.8, cadre={"ratio": "9:16", "t_local": 0.1})[1]))
check("r2_reframe_suivi_lu_au_temps_de_source_t_rouge_puis_bleu_temoin_centre_vert",
      _rs == ("r", "b", "g"), str(_rs))
_rinv = GF(BANDES, cadre={"ratio": "9:16", "t_local": 0, "reframe": {"mode": "rien"}})
check("r2_reframe_invalide_ignore_cadrage_centre", _rinv[0] == 200 and DOM(_rinv[1]) == "g", str(_rinv[0]))

# D-13 : zoom dynamique, progression = t_local / cadre.dur (comme le rendu).
_DZ = {"x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0, "w1": 0.5, "ease": "lin"}
_dz = {tl: LUM(GF(HB, cadre={"ratio": "9:16", "t_local": tl, "dur": 4, "dz": _DZ})[1], 0.5, 0.8)
       for tl in (0.0, 4.0)}
_dz_sans_dur = LUM(GF(HB, cadre={"ratio": "9:16", "t_local": 4.0, "dz": _DZ})[1], 0.5, 0.8)
_dz_temoin = LUM(GF(HB, cadre={"ratio": "9:16", "t_local": 4.0, "dur": 4})[1], 0.5, 0.8)
check("r2_dz_debut_plein_cadre_noir_en_bas_fin_fenetre_haute_blanche",
      _dz[0.0] is not None and _dz[0.0] < 30 and _dz[4.0] is not None and _dz[4.0] > 225, str(_dz))
check("r2_dz_sans_dur_ignore_temoin_sans_dz_noir",
      _dz_sans_dur is not None and _dz_sans_dur < 30 and _dz_temoin is not None and _dz_temoin < 30,
      str((_dz_sans_dur, _dz_temoin)))
_dzm = LUM(GF(HB, cadre={"ratio": "9:16", "t_local": 2.0, "dur": 4, "dz": dict(_DZ, ease="doux")})[1], 0.5, 0.8)
check("r2_dz_mi_parcours_fenetre_075_bas_noir", _dzm is not None and _dzm < 30, str(_dzm))

# Masque au centre du CADRE.
_mk = GF(PLAT, cadre={"ratio": "9:16", "t_local": 0}, effects=EXPO, mask=MSK)
_mk0 = GF(PLAT, cadre={"ratio": "9:16", "t_local": 0})
check("r2_masque_ellipse_centre_du_cadre_assombri_coin_intact",
      _mk[0] == 200 and LUM(_mk[1]) is not None and LUM(_mk[1]) < LUM(_mk0[1]) - 30
      and abs(LUM(_mk[1], 0.03, 0.03) - LUM(_mk0[1], 0.03, 0.03)) <= 3
      and _mk[1].size == (720, 1280),
      str((_mk[0], LUM(_mk[1]), LUM(_mk0[1]), LUM(_mk[1], 0.03, 0.03), LUM(_mk0[1], 0.03, 0.03))))

# Effets bornes au temps LOCAL.
_B56 = [dict(EXPO[0], t0=5, t1=6, fade_in=0.3)]
_lb = {tl: LUM(GF(PLAT, cadre={"ratio": "9:16", "t_local": tl}, effects=_B56)[1]) for tl in (2.0, 5.5, 6.0)}
_l0 = LUM(_mk0[1])
check("r2_effet_borne_5_6_absent_a_2_present_a_5_5_absent_a_6",
      None not in _lb.values() and abs(_lb[2.0] - _l0) <= 2 and _lb[5.5] < _l0 - 30 and abs(_lb[6.0] - _l0) <= 2,
      str((_lb, _l0)))
check("r2_temoin_sans_cadre_effet_borne_juge_en_plein",
      LUM(GF(PLAT, effects=_B56)[1]) is not None and LUM(GF(PLAT, effects=_B56)[1]) < _l0 - 30,
      str(LUM(GF(PLAT, effects=_B56)[1])))
_ldur = LUM(GF(PLAT, cadre={"ratio": "9:16", "t_local": 7.0, "dur": 6},
               effects=[dict(EXPO[0], t0=5, t1=10)])[1])
_lcourt = LUM(GF(PLAT, cadre={"ratio": "9:16", "t_local": 1.0}, effects=[dict(EXPO[0], t0=5, t1=5.01)])[1])
_lnb = LUM(GF(PLAT, cadre={"ratio": "9:16", "t_local": 1.0}, effects=EXPO)[1])
_loff = LUM(GF(PLAT, cadre={"ratio": "9:16", "t_local": 1.0}, effects=[dict(EXPO[0], off=True)])[1])
check("r2_bornes_comme_le_rendu_t1_borne_a_dur_intervalle_court_plein_sans_borne_plein_off_eteint",
      None not in (_ldur, _lcourt, _lnb, _loff) and abs(_ldur - _l0) <= 2 and _lcourt < _l0 - 30
      and _lnb < _l0 - 30 and abs(_loff - _l0) <= 2, str((_ldur, _lcourt, _lnb, _loff, _l0)))

# Revue T3 (m) : bornes INFINIES alignees sur `_timed` (t1 = +inf ramene a la
# duree du plan, t0 = -inf a 0) — avant : « tout le plan », l'apercu montrait
# un effet que le rendu n'a pas. JSON `Infinity` (accepte par json.loads).
_INF = float("inf")
_li = {k: LUM(GF(PLAT, cadre=dict({"ratio": "9:16", "t_local": tl}, **({"dur": d} if d else {})),
                 effects=[dict(EXPO[0], t0=a, t1=b)])[1])
       for k, (a, b, tl, d) in {"t1inf_a2": (5, _INF, 2.0, 6), "t1inf_a5_5": (5, _INF, 5.5, 6),
                                "t1inf_a6_5_dur6": (5, _INF, 6.5, 6), "t1inf_a7_sans_dur": (5, _INF, 7.0, None),
                                "t0moinsinf_a2": (-_INF, 3, 2.0, 6), "t0moinsinf_a4": (-_INF, 3, 4.0, 6)}.items()}
_pres = {k: (v is not None and v < _l0 - 30) for k, v in _li.items()}
check("r2_bornes_infinies_comme_le_rendu_t1_inf_a_dur_t0_moins_inf_a_0",
      _pres == {"t1inf_a2": False, "t1inf_a5_5": True, "t1inf_a6_5_dur6": False, "t1inf_a7_sans_dur": True,
                "t0moinsinf_a2": True, "t0moinsinf_a4": False}, str((_pres, _li)))
# Cloture (26/09) : NaN MESURE au rendu (8.1.1 et 9.0.1, effet invert) — t0 NaN -> [0, t1[ (max(0, nan) = 0) ;
# t1 NaN -> [t0, inf) si t0 > 0, JAMAIS si t0 = 0. Les cas v, u, s rendent le check DISCRIMINANT (t_local 2 < t0 = 3 ;
# t0 0 ; t0 NaN hors de [0, 1[) : l'ancienne lecture « NaN = tout le plan » les gardait tous.
_NAN = float("nan")
_ai = CALL(GR, "_au_temps", [{"type": "x", "t0": 5, "t1": _INF}, {"type": "y", "t0": _INF, "t1": 3},
                             {"type": "z", "t0": _NAN, "t1": 3}, {"type": "w", "t0": 1, "t1": _NAN},
                             {"type": "v", "t0": 3, "t1": _NAN}, {"type": "u", "t0": 0, "t1": _NAN},
                             {"type": "s", "t0": _NAN, "t1": 1}, {"type": "r", "t0": _NAN, "t1": _NAN}],
           2.0, 6.0)
_ai3 = CALL(GR, "_au_temps", [{"type": "v", "t0": 3, "t1": _NAN}], 3.0, 6.0)
check("r2_au_temps_t0_inf_tout_le_plan_nan_comme_le_rendu_mesure",
      isinstance(_ai, list) and [e["type"] for e in _ai] == ["y", "z", "w"]
      and isinstance(_ai3, list) and [e["type"] for e in _ai3] == ["v"], str((_ai, _ai3)))

# Cache : la cle porte le cadre ; un second appel identique ne lance rien.
_cmds.clear()
MM._run = _run_espion
try:
    _k1 = CALL(GR, "graded_frame", BANDES, 1.5, EXPO, None, 720, "jpg",
               cadre=MS._cadre_of({"ratio": "9:16", "t_local": 0.5}) if hasattr(MS, "_cadre_of") else None)
    _n1 = len(_cmds)
    _k2 = CALL(GR, "graded_frame", BANDES, 1.5, EXPO, None, 720, "jpg",
               cadre=MS._cadre_of({"ratio": "9:16", "t_local": 0.5}) if hasattr(MS, "_cadre_of") else None)
    _n2 = len(_cmds)
    _k3 = CALL(GR, "graded_frame", BANDES, 1.5, EXPO, None, 720, "jpg",
               cadre=MS._cadre_of({"ratio": "1:1", "t_local": 0.5}) if hasattr(MS, "_cadre_of") else None)
    _k4 = CALL(GR, "graded_frame", BANDES, 1.5, EXPO, None, 720, "jpg")
finally:
    MM._run = _vrai_run
check("r2_cache_cle_porte_le_cadre_second_appel_sans_sous_processus",
      isinstance(_k1, pathlib.Path) and _k1 == _k2 and _n1 >= 1 and _n2 == _n1
      and isinstance(_k3, pathlib.Path) and _k3 != _k1 and isinstance(_k4, pathlib.Path)
      and _k4 != _k1 and _k1.name.endswith("_grade.jpg"),
      str((_k1, _k2, _k3, _k4, _n1, _n2)))
_st415 = GF(str(FXD / "absent.mp4"), cadre={"ratio": "9:16", "t_local": 0})[0]
check("r2_cadre_source_absente_404", _st415 == 404, str(_st415))

# =============================================================================
print("\n[3] scopes en taille")
# =============================================================================


def SC(src, t=1.0, **kw):
    b = {"src": {"file_path": src}, "t": t}
    b.update(kw)
    st, p, hd = ROUTE("montage_scopes", b)
    return st, (IMG(p) if st == 200 else p), hd


_sz = {k: (lambda r: (r[0], getattr(r[1], "size", r[1])))(SC(TS, size=v))
       for k, v in (("s1024", 1024), ("s100", 100), ("s2000", 2000), ("s777", 777), ("abc", "abc"), ("s256", 256))}
check("r3_scopes_size_256_1024_pair_defaut_512",
      _sz == {"s1024": (200, (1024, 1024)), "s100": (200, (256, 256)), "s2000": (200, (1024, 1024)),
              "s777": (200, (776, 776)), "abc": (200, (512, 512)), "s256": (200, (256, 256))}, str(_sz))
_sd = SC(TS)
check("r3_scopes_defaut_512_no_store", _sd[0] == 200 and _sd[1].size == (512, 512)
      and (_sd[2] or {}).get("cache-control") == "no-store", str((_sd[0], _sd[2])))
_sc_c = SC(BANDES, cadre={"ratio": "9:16", "t_local": 0})
_sc_n = SC(BANDES)
_sc_c2 = SC(BANDES, cadre={"ratio": "9:16", "t_local": 0}, size=768)
check("r3_scopes_cadre_512_differe_du_plein_source_et_taille_768",
      _sc_c[0] == 200 and _sc_c[1].size == (512, 512) and _sc_n[0] == 200
      and ECART(_sc_c[1], _sc_n[1]) is not None and ECART(_sc_c[1], _sc_n[1]) > 1
      and _sc_c2[0] == 200 and _sc_c2[1].size == (768, 768),
      str((_sc_c[0], _sc_n[0], ECART(_sc_c[1], _sc_n[1]), _sc_c2[0])))
check("r3_scopes_cadre_illisible_400", SC(TS, cadre=[1])[0] == 400, str(SC(TS, cadre=[1])[0]))

# =============================================================================
print("\n[4] semaphore 2 sur grade-frame")
# =============================================================================
_vrai_gf = GR.graded_frame
_gs = {"n": 0, "max": 0, "appels": 0}
_lk = threading.Lock()
_JPG = FXD / "un.jpg"
_PI.new("RGB", (16, 16), (1, 2, 3)).save(str(_JPG))


def _gf_lent(*a, **k):
    with _lk:
        _gs["n"] += 1
        _gs["appels"] += 1
        _gs["max"] = max(_gs["max"], _gs["n"])
    try:
        time.sleep(0.25)
        return _JPG
    finally:
        with _lk:
            _gs["n"] -= 1


async def _gf_rafale(k=5):
    rs = await asyncio.gather(*[MS.montage_grade_frame(RQ({"src": {"file_path": TS}, "t": 1.0}))
                                for _ in range(k)], return_exceptions=True)
    return [getattr(r, "status_code", type(r).__name__) for r in rs]


async def _gf_un(rq):
    try:
        r = await asyncio.wait_for(MS.montage_grade_frame(rq), 5)
        return getattr(r, "status_code", None)
    except Exception as e:                               # noqa: BLE001
        return getattr(e, "status_code", type(e).__name__)


async def _gf_nu(k=5):
    await asyncio.gather(*[asyncio.to_thread(_gf_lent) for _ in range(k)])

_gA = _gB = _gP = None
GR.graded_frame = _gf_lent
try:
    _gs["max"] = 0
    _gA = (asyncio.run(_gf_rafale()), _gs["max"])
    _gs["max"] = 0
    _gB = (asyncio.run(_gf_rafale()), _gs["max"])
    _gs["appels"] = 0
    _gP = (asyncio.run(_gf_un(RQ_PARTI({"src": {"file_path": TS}, "t": 1.0}))), _gs["appels"])
finally:
    GR.graded_frame = _vrai_gf
_gs["max"] = 0
asyncio.run(_gf_nu())
check("r4_grade_frame_deux_au_plus_sur_deux_boucles_temoin_nu_cinq",
      _gA == ([200] * 5, 2) and _gB == ([200] * 5, 2) and _gs["max"] == 5, str((_gA, _gB, _gs["max"])))
check("r4_grade_frame_client_parti_499_sans_calcul", _gP == (499, 0), str(_gP))
# Revue T3 (m) : deux requetes LENTES (0,5 s et 1,2 s) tiennent les deux places ;
# une troisieme part DES que la premiere libere la sienne (pas apres la seconde),
# et une requete dont le client est PARTI pendant l'attente rend 499 sans calcul.
_dep = {}


def _gf_dure(p, t, *a, **k):
    _dep[t] = time.perf_counter()
    time.sleep({1.0: 0.5, 2.0: 1.2}.get(float(t), 0.05))
    return _JPG


async def _gf_trois():
    f = MS.montage_grade_frame
    t0 = time.perf_counter()
    ta = asyncio.ensure_future(f(RQ({"src": {"file_path": TS}, "t": 1.0})))
    tb = asyncio.ensure_future(f(RQ({"src": {"file_path": TS}, "t": 2.0})))
    await asyncio.sleep(0.1)
    td = asyncio.ensure_future(_gf_un(RQ_PARTI({"src": {"file_path": TS}, "t": 4.0})))
    await asyncio.sleep(0.05)
    tc = asyncio.ensure_future(f(RQ({"src": {"file_path": TS}, "t": 3.0})))
    rs = await asyncio.gather(ta, tb, tc, td, return_exceptions=True)
    return [getattr(r, "status_code", r) for r in rs], t0

_g3 = None
GR.graded_frame = _gf_dure
try:
    _st3, _t03 = asyncio.run(_gf_trois())
    _g3 = (_st3, {k: round(v - _t03, 2) for k, v in _dep.items()})
except Exception as _e:                                  # noqa: BLE001
    _g3 = repr(_e)
finally:
    GR.graded_frame = _vrai_gf
check("r4_troisieme_part_des_la_premiere_place_libre_client_parti_499_sans_calcul",
      isinstance(_g3, tuple) and _g3[0] == [200, 200, 200, 499] and 4.0 not in _g3[1]
      and 0.4 <= _g3[1].get(3.0, -1) <= 0.9 and _g3[1].get(2.0, 9) < 0.2, str(_g3))
check("r4_grade_frame_semaphore_distinct_de_scopes",
      hasattr(MS, "_grade_sem") and MS._grade_sem is not MS._scopes_sem, str(getattr(MS, "_grade_sem", None)))

# =============================================================================
print("\n[5] image cadre == image d'un rendu Preview reel au meme instant")
# =============================================================================
# Plan V1 lu depuis srcIn 0,5, 0..3 s de timeline, projet 9:16 en Preview
# (270x480, 30 i/s) : recadrage SUIVI (D-40), zoom D-13, pile exposition +
# un negatif BORNE [1, 2] (temps local : present a 1,5, absent a 0,5 et 2,6),
# masque. Le client envoie t = srcIn + t_local (vitesse 1) et les objets bruts
# reframe / dz du plan, plus `dur` = fin - debut.
# MESURE le 26/09 (8.1.1, scratchpad/t3/diag*.py) : le RENDU est EN AVANCE
# d'environ une image SOURCE sur la timeline (sa chaine V1 finit par
# `setpts=PTS-STARTPTS` apres fps/trim : la premiere image sortie de fps
# n'est pas a 0, 89 images pour 3 s a 30 i/s) — l'image a 1,5 s du rendu
# montre la source a srcIn + 1,5 + ~0,04. Sur testsrc2 (qui bouge a chaque
# image) cela seul vaut ~5,5/255 d'ecart. L'image `cadre` suit la TIMELINE
# (celle du lecteur qu'elle recouvre) et ne reproduit PAS ce decalage : la
# comparaison se fait donc sur une source FIXE (une image de testsrc2 tenue
# 4 s : detaillee, donc sensible au moindre pixel de geometrie) avec un
# recadrage et un zoom LENTS ; le decalage lui-meme est MESURE a part.
FIXE = MKV("fixe.mp4", ["-f", "lavfi", "-i", "testsrc2=s=480x270:r=25:d=4",
                        "-vf", "trim=end_frame=1,loop=loop=-1:size=1,setpts=N/25/TB", "-r", "25"])
# Geometrie FIXE dans le temps (recadrage manuel, fenetre de zoom constante) :
# l'egalite porte sur la geometrie, la pile, les bornes et le masque ; les
# recadrage et zoom ANIMES sont prouves plus bas, a l'avance du rendu pres.
_RF = {"mode": "manuel", "x": 0.35}
_DZR = {"x0": 0.1, "y0": 0.1, "w0": 0.8, "x1": 0.1, "y1": 0.1, "w1": 0.8, "ease": "lin"}
_FX = [{"type": "grade_basic", "exposure": -30, "saturation": 40}, {"type": "invert", "t0": 1.0, "t1": 2.0}]
_MKR = {"shape": "rect", "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.5, "soft": 0}


def RENDU(src, rf, dz, fx, mk, nom):
    """Rendu Preview REEL (commande de `_build_montage_command`) -> chemin ou None."""
    brut = {"reframe": rf, "dz": dz, "srcIn": 0.5, "start": 0.0, "end": 3.0, "label": "rg"}
    v1 = {"path": src, "src_dur": 4.0, "src_in": 0.5, "start": 0.0, "end": 3.0, "transition": "cut",
          "transition_s": 0.0, "speed": 0.0, "effects": fx, "mask": mk,
          "reframe": MS._reframe_of(brut), "dz": MS._dz_spec(brut)}
    out = FXD / nom
    try:
        cmd, _ = MS._build_montage_command([v1], [], [], None, w=270, h=480, fps=30, mix_db={}, ducking=False,
                                           duration_master=False, preview=True, out=str(out))
        cmd = [FF if x == "ffmpeg" else x for x in cmd]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and out.is_file():
            return out
        print("  (rendu : %s)" % (r.stderr or "")[-400:])
    except Exception as e:                               # noqa: BLE001
        print("  (rendu : %r)" % e)
    return None


def IMAGE_RENDU(rendu, tl):
    out = FXD / ("%s_%s.png" % (pathlib.Path(str(rendu)).stem, tl))
    try:
        subprocess.run([FF, "-y", "-v", "error", "-ss", "%.3f" % tl, "-i", str(rendu), "-frames:v", "1", str(out)],
                       capture_output=True, timeout=60)
        return IMG(out)
    except Exception:                                    # noqa: BLE001
        return None


REND = RENDU(FIXE, _RF, _DZR, _FX, _MKR, "rendu.mp4") if FIXE else None
check("r5_temoin_rendu_preview_reel_produit", REND is not None, str(REND))
_CAD = lambda tl: {"ratio": "9:16", "t_local": tl, "dur": 3.0, "reframe": _RF, "dz": _DZR}  # noqa: E731
_ec = {}
for _tl in (0.5, 1.5, 2.6):
    _ir = IMAGE_RENDU(REND, _tl) if REND else None
    _ic = GF(FIXE, round(0.5 + _tl, 3), effects=_FX, mask=_MKR, w=270, cadre=_CAD(_tl))
    _ic7 = GF(FIXE, round(0.5 + _tl, 3), effects=_FX, mask=_MKR, cadre=_CAD(_tl))
    _in = GF(FIXE, round(0.5 + _tl, 3), effects=_FX, mask=_MKR, w=270)
    # Temoin : la MEME pile sans ses bornes (le negatif partout).
    _ib = GF(FIXE, round(0.5 + _tl, 3), effects=[_FX[0], {"type": "invert"}], mask=_MKR, w=270, cadre=_CAD(_tl))
    _ec[_tl] = tuple(ECART(_ir, x[1]) if x[0] == 200 else x for x in (_ic, _ic7, _in, _ib)) + (
        getattr(_ic[1], "size", None),)
print("  ecarts (cadre 270, cadre 720 ramene, temoin sans cadre, temoin sans bornes) :", _ec)
check("r5_image_cadre_270_egale_rendu_preview_ecart_moyen_6_sur_trois_instants",
      REND is not None and all(isinstance(v[0], float) and v[0] <= 6 and v[4] == (270, 480) for v in _ec.values()),
      str(_ec))
check("r5_image_cadre_720_ramenee_egale_rendu_ecart_moyen_6",
      REND is not None and all(isinstance(v[1], float) and v[1] <= 6 for v in _ec.values()), str(_ec))
# Le residu de la route (~4-5/255) est celui du JPEG (-q:v 3) sur un motif
# tres detaille : le service rendu en PNG tombe sous 1,5 (mesure : 0,7-0,8).
_ep = {}
for _tl in (0.5, 1.5, 2.6):
    _gp = CALL(GR, "graded_frame", FIXE, round(0.5 + _tl, 3), _FX, _MKR, 270, "png",
               cadre=MS._cadre_of(_CAD(_tl)) if hasattr(MS, "_cadre_of") else None)
    _ep[_tl] = ECART(IMAGE_RENDU(REND, _tl), _gp) if REND and isinstance(_gp, pathlib.Path) else _gp
print("  ecarts service PNG :", _ep)
check("r5_service_png_egal_rendu_ecart_moyen_1_5_geometrie_exacte",
      all(isinstance(v, float) and v <= 1.5 for v in _ep.values()), str(_ep))
check("r5_temoin_image_sans_cadre_loin_du_rendu_20",
      REND is not None and all(isinstance(v[2], float) and v[2] > 20 for v in _ec.values()), str(_ec))
check("r5_temoin_bornes_ignorees_loin_du_rendu_hors_intervalle_20",
      REND is not None and isinstance(_ec[0.5][3], float) and _ec[0.5][3] > 20
      and isinstance(_ec[2.6][3], float) and _ec[2.6][3] > 20, str(_ec))

# L'AVANCE du rendu, mesuree : recadrage RAPIDE (170 px/s), l'image cadre au
# temps de source t + k/150 la plus proche de l'image du rendu a t_local.
_RFV = {"mode": "suivi", "points": [{"t": 0.5, "x": 0.2}, {"t": 3.5, "x": 0.8}]}
RENDV = RENDU(FIXE, _RFV, None, None, None, "rendu_rapide.mp4") if FIXE else None
_av = {}
for _tl in (0.5, 1.5):
    _ir = IMAGE_RENDU(RENDV, _tl) if RENDV else None
    _sc = []
    for _k in range(-3, 13):
        _g = GF(FIXE, round(0.5 + _tl + _k / 150, 4), w=270,
                cadre={"ratio": "9:16", "t_local": _tl, "reframe": _RFV})
        _sc.append((ECART(_ir, _g[1]) if _g[0] == 200 else 999, _k))
    _av[_tl] = min(_sc)
print("  avance du rendu, recadrage suivi (ecart, k/150 s) :", _av)
check("r5_recadrage_suivi_egal_au_rendu_a_son_avance_pres_une_image_source_au_plus",
      RENDV is not None and all(0 <= v[1] <= 7 and v[0] <= 3 for v in _av.values()), str(_av))
# Zoom ANIME (D-13) : meme mesure sur `t_local` (le zoompan du rendu lit `it`
# AVANT le setpts final, il avance donc comme le reste du segment).
_DZV = {"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.3, "w1": 0.6, "ease": "doux"}
RENDZ = RENDU(FIXE, None, _DZV, None, None, "rendu_zoom.mp4") if FIXE else None
_az = {}
for _tl in (0.5, 1.5):
    _ir = IMAGE_RENDU(RENDZ, _tl) if RENDZ else None
    _sc = []
    for _k in range(-3, 13):
        _g = GF(FIXE, round(0.5 + _tl, 3), w=270,
                cadre={"ratio": "9:16", "t_local": round(_tl + _k / 150, 4), "dur": 3.0, "dz": _DZV})
        _sc.append((ECART(_ir, _g[1]) if _g[0] == 200 else 999, _k))
    _az[_tl] = min(_sc)
print("  avance du rendu, zoom anime (ecart, k/150 s) :", _az)
check("r5_zoom_anime_egal_au_rendu_a_son_avance_pres_une_image_au_plus",
      RENDZ is not None and all(0 <= v[1] <= 7 and v[0] <= 3 for v in _az.values()), str(_az))
# Information : la meme comparaison sur testsrc2 qui BOUGE (non bornee).
_RT = RENDU(TS, None, None, _FX, _MKR, "rendu_ts.mp4") if TS else None
_imv = GF(TS, 2.0, effects=_FX, mask=_MKR, w=270, cadre={"ratio": "9:16", "t_local": 1.5, "dur": 3.0})
print("  information : testsrc2 anime, ecart a 1,5 s =",
      ECART(IMAGE_RENDU(_RT, 1.5), _imv[1]) if _RT and _imv[0] == 200 else _imv[0])

# Cout mesure (cache vide) : ms par image a 720 et a 1280.
_cout = {}
for _w in (720, 1280):
    _vide_cache()
    _t0 = time.perf_counter()
    _p = GF(TS, 2.0, effects=_FX, mask=_MKR, w=_w, cadre=_CAD(1.5))
    _cout[_w] = (round((time.perf_counter() - _t0) * 1000), _p[0])
print("  cout (ms, cache vide) :", _cout)
check("r5_cout_mesure_720_et_1280_200", all(v[1] == 200 for v in _cout.values()), str(_cout))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
try:
    from loguru import logger as _lg
    _lg.remove()
    from app.services import storage as _st
    asyncio.run(_st._engine.dispose())
except Exception as _e:
    print("  (fermeture des handles : %s)" % _e)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
