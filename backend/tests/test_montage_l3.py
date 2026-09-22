# -*- coding: utf-8 -*-
"""L3 — PROPRIETES DE PLAN cote backend. En-tete recopie de
test_montage_l2.py (env, check, J, A, V1SPEC/FLAT/BUILD) : dossier de donnees
NEUF par execution, TestClient sans port ouvert, toute lecture gardee — un
banc qui meurt sur un acces nu ne dit pas quelles assertions manquent.
Run : & $PY tests/test_montage_l3.py   (depuis backend/)

[1] D-13 DYNAMIC ZOOM. Un clip V1 porte un champ OPTIONNEL `dz` :
{x0, y0, w0, x1, y1, w1, ease?} en FRACTIONS du cadre. `_dz_spec` le clampe
(w dans [0.1, 1], x et y dans [0, 1-w]) et rend None pour tout ce qui ne doit
JAMAIS entrer dans un filtergraph (absent, non-dict, NaN, None) ainsi que pour
le plein cadre aux deux bouts (aucun zoom). `_dz_filter` le traduit en UN
`zoompan` a d=1 (une image de sortie par image d'entree : duree et compte
d'images preserves) pose APRES `fps=` et AVANT `format=yuv420p` — MESURE le
22/09/2026 sur ffmpeg 8.1.1 : `crop=w='…t…'` echoue a la configuration (-22),
`scale:eval=frame` fige la taille, et un zoompan pose AVANT fps sur un flux
`setpts=PTS/2` dupliquerait chaque image. Le temps est `it` (timestamp
d'entree), jamais `t`.

L'ETAT VIDE DE CE BANC : avant l'implementation `MS._dz_spec` et
`MS._dz_filter` n'existent pas — `A(nom, defaut)` les lit par `getattr` avec un
repli qui rend "ABSENT", pour que l'absence FASSE ROUGIR les checks au lieu de
TUER le banc. `BUILD(dz=...)` sur un `_build_montage_command` qui ne connait
pas encore le champ : la spec V1 est un dict, donc le champ inconnu est
simplement ignore et le zoompan manque → les checks rougissent aussi. Regle
des assertions negatives : chaque negation (« pas de zoompan sans dz », « pas
de *t ») est precedee dans la MEME expression du temoin positif qui etablit
que la mesure a eu lieu (`isinstance(f, str)`, `"zoompan" in _cz`…).
[2] D-15 RETIME. Un clip V1 porte un champ OPTIONNEL `retime` : "nearest"
(historique : fps= duplique ou saute), "blend" (tblend moyenne de deux images
voisines) ou "flow" (minterpolate a compensation de mouvement). `_v1_retime`
ne rend que "blend" | "flow", None pour tout le reste. Ordre MESURE le 22/09
(revue) : setpts → [minterpolate] → fps → [tblend] → [zoompan] → format —
`flow` AVANT fps= (il fabrique ses images a la cadence demandee), `blend`
APRES fps= (avant : (A+B)/2,(A+B)/2,… tout flou ; apres : A,(A+B)/2,B,… = le
Frame Blend de Resolve) ; scd au defaut fdiff ; tpad/trim en aval ramenent a
seg_durs[k] ; sans vitesse le champ est IGNORE (commande historique). Etat
vide : `A("_v1_retime")` rend "ABSENT" ; `BUILD(retime=…)` sur une spec qui
ne connait pas le champ produit la commande historique → rouge. Mesure reelle :
flow a x0.5 sur 2 s de source → 4 s et 100 images (SKIP sans ffmpeg).

La mesure ffmpeg reelle (fin de section) est en SKIP si ffmpeg est injoignable,
comme les bancs-miroirs du depot.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl3_")
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


def A(nom, defaut):
    """`getattr` module — un attribut ABSENT (avant l'implementation) doit
    faire ROUGIR les checks qui le lisent, jamais TUER le banc sur un
    AttributeError nu."""
    return getattr(MS, nom, defaut)


V1F = str(pathlib.Path(TMP) / "v1.mp4")
pathlib.Path(V1F).write_bytes(b"x")


def V1SPEC(**kw):
    """Forme d'un clip V1 pour `_build_montage_command`, RECOPIEE de
    tests/test_montage_l2.py (`V1SPEC`) — `d.update(kw)` accepte `dz=` et
    `speed=` comme n'importe quel champ."""
    d = {"path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def BUILD(**kw):
    """`_build_montage_command` avec les arguments constants de la section.
    Les mots-cles de V1SPEC (`dz`, `speed`) vont au clip ; le reste aux
    arguments nommes. Un `TypeError` (mot-cle inconnu : l'ETAT VIDE) rend un
    temoin au lieu de tuer le banc."""
    clip = {k: kw.pop(k) for k in ("dz", "speed", "retime") if k in kw}
    a = {"w": 64, "h": 64, "fps": 25, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": True,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    try:
        cmd, _ = MS._build_montage_command([V1SPEC(**clip)], [], [], None, **a)
    except TypeError as e:
        return "TypeError: %s" % e
    return FLAT(cmd)


print("\n[1] D-13 dynamic zoom : le champ dz devient un zoompan apres fps")
_dz_spec = A("_dz_spec", lambda c: "ABSENT")
_dz_filter = A("_dz_filter", lambda *a, **k: "ABSENT")
DZ_IN = {"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6}
check("d13_un_dz_valide_est_clampe_et_porte_ease_doux",
      _dz_spec({"dz": DZ_IN}) == {"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"},
      _dz_spec({"dz": DZ_IN}))
check("d13_les_bornes_sont_tenues_w_min_0_1_et_x_dans_le_cadre",
      _dz_spec({"dz": {"x0": 0.9, "y0": -1, "w0": 0.02, "x1": 5, "y1": 5, "w1": 3}})
      == {"x0": 0.9, "y0": 0.0, "w0": 0.1, "x1": 0.0, "y1": 0.0, "w1": 1.0, "ease": "doux"},
      _dz_spec({"dz": {"x0": 0.9, "y0": -1, "w0": 0.02, "x1": 5, "y1": 5, "w1": 3}}))
check("d13_plein_cadre_des_deux_cotes_ne_vaut_aucun_zoom",
      _dz_spec({"dz": {"x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0, "w1": 1}}) is None,
      _dz_spec({"dz": {"x0": 0, "y0": 0, "w0": 1, "x1": 0, "y1": 0, "w1": 1}}))
check("d13_absent_non_dict_ou_nan_rend_none",
      _dz_spec({}) is None and _dz_spec({"dz": "x"}) is None
      and _dz_spec({"dz": dict(DZ_IN, w1="nan")}) is None and _dz_spec({"dz": dict(DZ_IN, x1=None)}) is None,
      (_dz_spec({}), _dz_spec({"dz": "x"}), _dz_spec({"dz": dict(DZ_IN, w1="nan")}),
       _dz_spec({"dz": dict(DZ_IN, x1=None)})))
def _ease(v):
    """Lecture GARDEE de `ease` : le repli "ABSENT" (chaine, donc vraie) ferait
    mourir un `(x or {}).get(...)` — faute n6, le banc doit rougir."""
    return v.get("ease") if isinstance(v, dict) else v


check("d13_ease_lin_est_gardee_tout_autre_mot_retombe_a_doux",
      _ease(_dz_spec({"dz": dict(DZ_IN, ease="lin")})) == "lin"
      and _ease(_dz_spec({"dz": dict(DZ_IN, ease="zzz")})) == "doux",
      (_dz_spec({"dz": dict(DZ_IN, ease="lin")}), _dz_spec({"dz": dict(DZ_IN, ease="zzz")})))
f = _dz_filter({"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "lin"}, 64, 64, 25, 3.0)
check("d13_le_filtre_est_un_zoompan_d1_a_la_taille_du_canvas",
      isinstance(f, str) and f.startswith("zoompan=z='") and ":d=1:s=64x64:fps=25" in f, f)
check("d13_le_temps_est_it_sur_la_duree_jamais_t",
      isinstance(f, str) and "clip(it/3,0,1)" in f and "*t" not in f and "(t" not in f, f)
check("d13_z_est_l_inverse_de_la_largeur_x_y_en_fraction_du_cadre",
      isinstance(f, str) and "z='1/(1+(-0.4)*" in f and ":x='iw*(0+(0.2)*" in f and ":y='ih*(0+(0.2)*" in f, f)
fd = _dz_filter({"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, 64, 64, 25, 3.0)
check("d13_ease_doux_est_la_smoothstep_u_u_3_2u",
      isinstance(fd, str) and "*(3-2*" in fd and fd != f, fd)
_c0 = BUILD()
check("d13_sans_dz_la_commande_est_octet_pour_octet_l_historique",
      BUILD(dz=None) == _c0 and "fps=25,format=yuv420p" in _c0 and "zoompan" not in _c0, _c0[:200])
_cz = BUILD(dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"})
check("d13_avec_dz_le_zoompan_est_pose_apres_fps_et_avant_format",
      "zoompan" in _cz and _cz.find("fps=25,zoompan=") > 0 and _cz.find(":fps=25,format=yuv420p,tpad=") > 0, _cz[:400])
_czs = BUILD(dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, speed=2.0)
check("d13_avec_vitesse_le_zoompan_reste_apres_le_fps_qui_suit_setpts",
      "setpts=PTS/2" in _czs and _czs.find("setpts=PTS/2,fps=25,zoompan=") > 0, _czs[:400])
def _apres(s, motif, fin):
    """Nombre lu apres `motif` jusqu'a `fin`, ou None — lecture GARDEE (faute
    n6 : aucun split()[1] nu). MESURE le 22/09 : seg_durs est ecrit par str()
    (`stop_duration=4.0`) et le zoompan par fnum (`clip(it/4,`) — meme
    nombre, chaines differentes, on compare les VALEURS."""
    i = s.find(motif)
    if i < 0:
        return None
    j = s.find(fin, i + len(motif))
    try:
        return float(s[i + len(motif):j]) if j > 0 else None
    except ValueError:
        return None


_sd, _it = _apres(_cz, "stop_duration=", ","), _apres(_cz, "clip(it/", ",")
check("d13_la_duree_du_zoom_est_celle_du_segment",
      _sd is not None and _it is not None and _sd == _it == 4.0, (_sd, _it))
_sds, _its = _apres(_czs, "stop_duration=", ","), _apres(_czs, "clip(it/", ",")
check("d13_avec_vitesse_la_duree_du_zoom_est_la_duree_timeline_pas_source",
      _sds is not None and _its is not None and _sds == _its == 2.0, (_sds, _its))

# --- mesure ffmpeg reelle : d=1 preserve le compte d'images ----------------
# testsrc2 2 s a 25 i/s → rendu avec un dz → ffprobe compte 50 images.
_FB = None
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    _FB = _fb()
    _SRC = str(pathlib.Path(TMP) / "src.mp4")
    _gen = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                           "testsrc2=s=64x64:r=25:d=2", "-c:v", "libx264",
                           "-pix_fmt", "yuv420p", _SRC],
                          check=False, capture_output=True, timeout=60)
    if _gen.returncode != 0 or not os.path.isfile(_SRC):
        _FB = None
        print("  (ffmpeg present mais testsrc2 a echoue : %r)" % _gen.stderr[-300:])
except Exception as _e:
    _FB = None
    print("  (ffmpeg injoignable : %s)" % _e)
if _FB is None:
    check("d13_rendu_reel_SKIP_sans_ffmpeg", True)
else:
    _OUT = os.path.join(TMP, "dz.mp4")
    _spec = V1SPEC(path=_SRC, src_dur=2.0, src_in=0.0, start=0.0, end=2.0,
                   dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2,
                       "w1": 0.6, "ease": "doux"})
    _cmd = None
    try:
        _cmd, _tot = MS._build_montage_command([_spec], [], [], None, w=64, h=64,
                                               fps=25, mix_db={}, ducking=False,
                                               duration_master=False, preview=True,
                                               out=_OUT)
    except TypeError as _e:
        print("  (BUILD reel : %s)" % _e)
    _rc, _err = -1, "commande absente"
    if isinstance(_cmd, list) and _cmd:
        _cmd = [_FB] + list(_cmd[1:])          # meme binaire que la source
        _r = subprocess.run(_cmd, check=False, capture_output=True, text=True,
                            timeout=120)
        _rc, _err = _r.returncode, (_r.stderr or "")[-400:]
    check("d13_rendu_reel_ffmpeg_rend_0_avec_un_zoompan_dans_la_chaine",
          _rc == 0 and "zoompan" in FLAT(_cmd or []) and os.path.isfile(_OUT), (_rc, _err))
    _nb = -1
    try:
        _p = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                             "-count_frames", "-select_streams", "v:0", "-show_entries",
                             "stream=nb_read_frames", "-of", "csv=p=0", _OUT],
                            check=False, capture_output=True, text=True, timeout=60)
        _nb = int((_p.stdout or "").strip() or -1)
    except (ValueError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (ffprobe : %s)" % _e)
    # Temoin positif OBLIGATOIRE : sans zoompan dans la chaine, 50 images
    # seraient triviales (mesure le 22/09 : ce check passait a VIDE sans lui).
    check("d13_rendu_reel_d1_preserve_les_50_images",
          _rc == 0 and "zoompan" in FLAT(_cmd or []) and _nb == 50, _nb)

    # --- start_time > 0 : le zoom n'est PAS decale (mesure demandee par la
    # revue de T1). `it` du zoompan est le timestamp d'ENTREE et le
    # setpts=PTS-STARTPTS de la chaine vient APRES lui ; mais le CLI ffmpeg
    # remet lui-meme l'horloge de chaque entree a zero (ts_offset = -start_time
    # sans -copyts). Preuve : la MEME source encodee avec start_time 1,5 s
    # (-output_ts_offset, verifie par ffprobe) rend des images IDENTIQUES a
    # celles de la source a 0 aux instants 0 et fin ; temoin positif : les
    # images 0 et fin d'un meme rendu different (le zoom a bien eu lieu).
    _FP = os.path.join(os.path.dirname(_FB), "ffprobe")
    _SRC15 = str(pathlib.Path(TMP) / "src15.mp4")
    _g15 = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                           "testsrc2=s=64x64:r=25:d=2", "-c:v", "libx264", "-pix_fmt",
                           "yuv420p", "-output_ts_offset", "1.5", _SRC15],
                          check=False, capture_output=True, timeout=60)
    _st = subprocess.run([_FP, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=start_time", "-of", "csv=p=0", _SRC15],
                         check=False, capture_output=True, text=True, timeout=30).stdout.strip()
    _OUT15 = os.path.join(TMP, "dz15.mp4")
    _rc15 = -1
    try:
        _c15, _ = MS._build_montage_command([dict(_spec, path=_SRC15)], [], [], None, w=64,
                                            h=64, fps=25, mix_db={}, ducking=False,
                                            duration_master=False, preview=True, out=_OUT15)
        _rc15 = subprocess.run([_FB] + list(_c15[1:]), check=False, capture_output=True,
                               timeout=120).returncode
    except (TypeError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (rendu start_time 1.5 : %s)" % _e)

    def _img(src, k):
        """Image k (1-based) d'un rendu, en niveaux de gris — None si absente."""
        d = src + "_f"
        os.makedirs(d, exist_ok=True)
        if not os.listdir(d):
            subprocess.run([_FB, "-y", "-loglevel", "error", "-i", src,
                            os.path.join(d, "%03d.png")], check=False, timeout=60)
        p = os.path.join(d, "%03d.png" % k)
        if not os.path.isfile(p):
            return None
        from PIL import Image
        return Image.open(p).convert("L")

    def _ecart(a, b):
        """Part des pixels dont l'ecart depasse 8 niveaux — 1.0 si une image manque."""
        if a is None or b is None or a.size != b.size:
            return 1.0
        from PIL import ImageChops
        h = ImageChops.difference(a, b).histogram()
        return sum(h[8:]) / max(1, sum(h))

    _a1, _a50, _b1, _b50 = _img(_OUT, 1), _img(_OUT, 50), _img(_OUT15, 1), _img(_OUT15, 50)
    check("d13_une_source_a_start_time_1_5_rend_le_meme_zoom_qu_a_0",
          _g15.returncode == 0 and _st.startswith("1.5") and _rc == 0 and _rc15 == 0
          and _ecart(_a1, _a50) > 0.5 and _ecart(_a1, _b1) == 0.0 and _ecart(_a50, _b50) == 0.0,
          (_st, _rc15, _ecart(_a1, _a50), _ecart(_a1, _b1), _ecart(_a50, _b50)))

    # Variante -ss (src_in=0.5) sur les deux sources : 1,5 s de source restante
    # → 37 images ; memes images aux deux bouts, temoin : le zoom a eu lieu.
    _rss = {}
    for _nom, _src in (("s0", _SRC), ("s15", _SRC15)):
        _o = os.path.join(TMP, "dzss_" + _nom + ".mp4")
        _rss[_nom] = (-1, _o)
        try:
            _cs_, _ = MS._build_montage_command([dict(_spec, path=_src, src_in=0.5)], [], [], None,
                                                w=64, h=64, fps=25, mix_db={}, ducking=False,
                                                duration_master=False, preview=True, out=_o)
            _rss[_nom] = (subprocess.run([_FB] + list(_cs_[1:]), check=False, capture_output=True,
                                         timeout=120).returncode, _o)
        except (TypeError, OSError, subprocess.TimeoutExpired) as _e:
            print("  (rendu -ss %s : %s)" % (_nom, _e))
    _s1, _s37, _t1, _t37 = (_img(_rss["s0"][1], 1), _img(_rss["s0"][1], 37),
                            _img(_rss["s15"][1], 1), _img(_rss["s15"][1], 37))
    check("d13_avec_ss_la_source_a_start_time_1_5_rend_le_meme_zoom_qu_a_0",
          _st.startswith("1.5") and _rss["s0"][0] == 0 and _rss["s15"][0] == 0
          and _ecart(_s1, _s37) > 0.5 and _ecart(_s1, _t1) == 0.0 and _ecart(_s37, _t37) == 0.0,
          (_rss["s0"][0], _rss["s15"][0], _ecart(_s1, _s37), _ecart(_s1, _t1), _ecart(_s37, _t37)))

print("\n[2] D-15 retime : blend / flow s'intercalent entre setpts et fps")
_v1_retime = A("_v1_retime", lambda c: "ABSENT")
check("d15_nearest_absent_ou_inconnu_rend_none",
      _v1_retime({}) is None and _v1_retime({"retime": "nearest"}) is None
      and _v1_retime({"retime": "zzz"}) is None and _v1_retime({"retime": 3}) is None,
      [_v1_retime(x) for x in ({}, {"retime": "nearest"}, {"retime": "zzz"}, {"retime": 3})])
check("d15_blend_et_flow_sont_les_deux_valeurs",
      _v1_retime({"retime": "blend"}) == "blend" and _v1_retime({"retime": "flow"}) == "flow",
      (_v1_retime({"retime": "blend"}), _v1_retime({"retime": "flow"})))
_c0 = BUILD(); _cs = BUILD(speed=2.0)
check("d15_sans_retime_les_commandes_sont_l_historique",
      "setpts=PTS/2,fps=25," in _cs and BUILD(retime=None) == _c0 and BUILD(retime=None, speed=2.0) == _cs
      and "tblend" not in _cs and "minterpolate" not in _cs, _cs[:400])
_cb = BUILD(speed=2.0, retime="blend")
# Revue 22/09 : tblend AVANT fps= a x0.5 rendrait (A+B)/2,(A+B)/2,(B+C)/2…
# (tout flou) ; APRES fps= : A,(A+B)/2,B,… = le Frame Blend de Resolve.
# tblend consomme la premiere image (49/50 mesure, pts des 0,04) : le
# setpts=PTS-STARTPTS qui le suit rebase a 0, le tpad aval clone la fin.
check("d15_blend_pose_tblend_average_apres_fps_avant_format",
      "setpts=PTS/2,fps=25,tblend=all_mode=average,setpts=PTS-STARTPTS,format=yuv420p," in _cb, _cb[:400])
_cf = BUILD(speed=0.5, retime="flow")
# scd au defaut ffmpeg (fdiff) : `scd=none` interpolerait a travers une coupe.
check("d15_flow_pose_minterpolate_mci_a_la_cadence_du_canvas_entre_setpts_et_fps",
      "setpts=PTS/0.5,minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,fps=25," in _cf
      and "scd=" not in _cf, _cf[:400])
check("d15_sans_vitesse_retime_ne_change_rien",
      "fps=25,format=yuv420p" in _c0 and BUILD(retime="flow") == _c0 and BUILD(retime="blend") == _c0, _c0[:200])
check("d15_un_retime_inconnu_avec_vitesse_reste_l_historique",
      "setpts=PTS/2,fps=25," in _cs and BUILD(speed=2.0, retime="zzz") == _cs
      and BUILD(speed=2.0, retime="nearest") == _cs)
_cfz = BUILD(speed=0.5, retime="flow", dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "lin"})
check("d15_avec_dz_l_ordre_est_setpts_minterpolate_fps_zoompan_format",
      _cfz.find("setpts=PTS/0.5,minterpolate=") > 0 and _cfz.find(":vsbmc=1,fps=25,zoompan=") > 0
      and _cfz.find(":fps=25,format=yuv420p,tpad=") > 0, _cfz[:500])
_cbz = BUILD(speed=0.5, retime="blend", dz={"x0": 0.0, "y0": 0.0, "w0": 1.0, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "lin"})
_pf, _pb, _pz = (_cbz.find("setpts=PTS/0.5,fps=25,"), _cbz.find(",tblend=all_mode=average,setpts=PTS-STARTPTS,zoompan="),
                 _cbz.find(":fps=25,format=yuv420p,tpad="))
check("d15_avec_dz_l_ordre_est_setpts_fps_tblend_zoompan_format",
      0 < _pf < _pb < _pz and "minterpolate" not in _cbz, (_pf, _pb, _pz, _cbz[:500]))

# --- mesure ffmpeg reelle : flow a x0.5 sur 2 s de source → 4 s, 100 images.
# d timeline = min(want, d_src/spd) : end-start=4 et src_dur=2 → d_src=2, d=4 ;
# minterpolate CHANGE le compte d'images en amont, tpad/trim en aval ramenent
# a seg_durs[k]. Temoin positif : minterpolate DANS la commande executee.
if _FB is None:
    check("d15_rendu_reel_SKIP_sans_ffmpeg", True)
else:
  # blend : tblend sort N-1 images (la premiere), rebasees a 0 puis le tpad
  # clone la derniere → 100 images, 4,000 s. Durée lue sur le FLUX VIDEO :
  # celle du format est dominee par l'audio anullsrc de 4 s (99 images y
  # lisaient 4,0 s — mesure).
  for _rt, _tem in (("flow", "minterpolate=fps=25"), ("blend", "tblend=all_mode=average")):
    _OUTF = os.path.join(TMP, _rt + ".mp4")
    _cmdf, _rcf, _errf = None, -1, "commande absente"
    try:
        _cmdf, _ = MS._build_montage_command(
            [V1SPEC(path=_SRC, src_dur=2.0, src_in=0.0, start=0.0, end=4.0, speed=0.5, retime=_rt)],
            [], [], None, w=64, h=64, fps=25, mix_db={}, ducking=False,
            duration_master=False, preview=True, out=_OUTF)
        _cmdf = [_FB] + list(_cmdf[1:])
        _rf = subprocess.run(_cmdf, check=False, capture_output=True, text=True, timeout=300)
        _rcf, _errf = _rf.returncode, (_rf.stderr or "")[-400:]
    except (TypeError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (rendu %s : %s)" % (_rt, _e))
    _nbf, _durf = -1, -1.0
    try:
        _pf = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                              "-count_frames", "-select_streams", "v:0", "-show_entries",
                              "stream=duration,nb_read_frames", "-of", "csv=p=0", _OUTF],
                             check=False, capture_output=True, text=True, timeout=60)
        _lig = [x for x in (_pf.stdout or "").strip().split(",") if x]   # duration,nb
        _durf = float(_lig[0]) if _lig else -1.0
        _nbf = int(_lig[-1]) if len(_lig) > 1 else -1
    except (ValueError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (ffprobe %s : %s)" % (_rt, _e))
    check(f"d15_rendu_reel_{_rt}_x0_5_rend_0_avec_{_tem.split('=')[0]}_dans_la_chaine",
          _rcf == 0 and _tem in FLAT(_cmdf or []) and os.path.isfile(_OUTF), (_rcf, _errf))
    check(f"d15_rendu_reel_{_rt}_x0_5_dure_4_s_et_100_images",
          _rcf == 0 and _tem in FLAT(_cmdf or []) and _nbf == 100 and abs(_durf - 4.0) < 0.05,
          (_nbf, _durf))

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
