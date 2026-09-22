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
[3] D-16 STABILISATION. Un clip V1 porte un champ OPTIONNEL `stab` : {on,
smooth 1..100 (defaut 15), crop keep|black, zoom -30..30}. `_v1_stab` le
clampe (None hors `on`). Le `.trf` de vidstabdetect est un cache PAR SOURCE
(`montage_media.stab_path` / `stab_detect`, extension `.trf`, jamais fabrique
par une lecture). Dans la chaine, un segment `stab` AVEC `trf` existant lit sa
source ENTIERE (plus de -ss/-t : le .trf est indexe par image d'entree) et
commence par `vidstabtransform=input='C\\:/…':smoothing:crop:zoom:optzoom=1:
interpol=bilinear,trim=start=src_in:duration=d_src,setpts=PTS-STARTPTS,`
AVANT `scale=` ; `stab` sans `trf` (ou trf disparu) = commande historique.
MESURE (grep ":a]") : l'audio d'une entree V1 n'entre jamais dans le graphe,
l'entree entiere ne desynchronise rien. Etat vide : `A("_v1_stab")` rend
"ABSENT", `_EXT` sans "stab", `stab_path` absent, `BUILD(stab=…)` ignore.
Mesure reelle : testsrc2 3 s → .trf > 1 000 o, rendu rc 0 et 75 images.
[6] D-16 ROUTES /stab. `POST /stab` = le contrat de `POST /proxy` ({ok,
ready, job_id}, provider `montage_stab`, suivi par GET /api/jobs/{id}) ;
`GET /stab` = {ready} sans jamais fabriquer. Espion /render : un clip V1 avec
`stab:{on:true}` → la spec V1 porte `stab.trf` (= stab_path de la source) et la
commande contient vidstabtransform ; sans `stab`, ni le champ ni le filtre.

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


def TL(name="l3", n=1, dur=4, src=None):
    """Timeline minimale pour /render — recopiee de tests/test_montage_l2.py."""
    return {"name": name, "ratio": "9:16", "duration": dur, "mix": {},
            "clips": [{"tr": "v1", "id": "v%d" % i, "start": 0, "end": 4,
                       "src": {"file_path": src or V1F}} for i in range(n)]}


def BUILD(**kw):
    """`_build_montage_command` avec les arguments constants de la section.
    Les mots-cles de V1SPEC (`dz`, `speed`) vont au clip ; le reste aux
    arguments nommes. Un `TypeError` (mot-cle inconnu : l'ETAT VIDE) rend un
    temoin au lieu de tuer le banc."""
    clip = {k: kw.pop(k) for k in ("dz", "speed", "retime", "stab", "src_in") if k in kw}
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

print("\n[3] D-16 stabilisation : analyse en cache, transformation avant le recadrage")
from app.services import montage_media as MM                 # noqa: E402
_v1_stab = A("_v1_stab", lambda c: "ABSENT")
check("d16_stab_absent_ou_faux_rend_none",
      _v1_stab({}) is None and _v1_stab({"stab": "x"}) is None and _v1_stab({"stab": {"on": False}}) is None,
      [_v1_stab(x) for x in ({}, {"stab": "x"}, {"stab": {"on": False}})])
check("d16_stab_vrai_porte_les_defauts_15_keep_0",
      _v1_stab({"stab": {"on": True}}) == {"smooth": 15, "crop": "keep", "zoom": 0}, _v1_stab({"stab": {"on": True}}))
check("d16_stab_est_clampe_smooth_1_100_zoom_m30_30_crop_black_ou_keep",
      _v1_stab({"stab": {"on": True, "smooth": 999, "crop": "black", "zoom": -80}}) == {"smooth": 100, "crop": "black", "zoom": -30}
      and _v1_stab({"stab": {"on": True, "smooth": 0, "crop": "zzz", "zoom": "7"}}) == {"smooth": 1, "crop": "keep", "zoom": 7}
      and _v1_stab({"stab": {"on": True, "smooth": "nan", "zoom": None}}) == {"smooth": 15, "crop": "keep", "zoom": 0},
      (_v1_stab({"stab": {"on": True, "smooth": 999, "crop": "black", "zoom": -80}}),
       _v1_stab({"stab": {"on": True, "smooth": 0, "crop": "zzz", "zoom": "7"}}),
       _v1_stab({"stab": {"on": True, "smooth": "nan", "zoom": None}})))
check("d16_le_cache_stab_a_son_extension_trf", getattr(MM, "_EXT", {}).get("stab") == ".trf", getattr(MM, "_EXT", None))
_sp = getattr(MM, "stab_path", None)
_src = os.path.join(TMP, "s.txt"); open(_src, "wb").write(b"x")
_spp = _sp(pathlib.Path(_src)) if callable(_sp) else None
check("d16_stab_path_est_dans_montage_cache_et_ne_fabrique_rien",
      _spp is not None and str(_spp).endswith("_stab.trf") and _spp.parent.name == "montage_cache"
      and not _spp.exists(), _spp)
_c0 = BUILD()
check("d16_sans_stab_la_commande_est_l_historique",
      "fps=25,format=yuv420p" in _c0 and BUILD(stab=None) == _c0 and "vidstab" not in _c0, _c0[:200])
_trf = os.path.join(TMP, "a b.trf"); open(_trf, "wb").write(b"TRF1")
_cs = BUILD(stab={"smooth": 20, "crop": "black", "zoom": 5, "trf": _trf}, src_in=1.5)
_ch = BUILD(src_in=1.5)     # temoin : SANS stab, src_in=1.5 passe bien par -ss/-t
check("d16_avec_stab_l_entree_n_est_plus_tronquee_par_ss_t",
      " -ss 1.5 " in _ch and " -t 2.5 " in _ch.split("-filter_complex")[0]
      and "vidstabtransform=" in _cs and " -ss 1.5" not in _cs
      and " -t " not in _cs.split("-filter_complex")[0], _cs[:300])
check("d16_la_transformation_precede_trim_puis_le_recadrage",
      "vidstabtransform=input='" in _cs
      and ":smoothing=20:crop=black:zoom=5:optzoom=1:interpol=bilinear,trim=start=1.5:duration=2.5,setpts=PTS-STARTPTS,scale=64:64" in _cs
      and 0 < _cs.find("vidstabtransform=") < _cs.find("scale=64:64"), _cs[:400])
check("d16_le_chemin_trf_est_echappe_comme_un_ass",
      "vidstabtransform=" in _cs and "input='" + _trf.replace("\\", "/").replace(":", r"\:") + "':" in _cs, _cs[:400])
check("d16_stab_sans_trf_est_ignore_avec_la_commande_historique",
      "vidstabtransform=" in _cs and BUILD(stab={"smooth": 20, "crop": "keep", "zoom": 0}) == _c0
      and BUILD(stab={"smooth": 20, "crop": "keep", "zoom": 0, "trf": os.path.join(TMP, "absent.trf")}) == _c0)

# --- mesure ffmpeg reelle : vidstabdetect sur 3 s, puis la transformation
# dans la chaine → 75 images a 25 i/s (vidstabtransform preserve le compte).
if _FB is None:
    check("d16_analyse_reelle_SKIP_sans_ffmpeg", True)
else:
    _SRC3 = str(pathlib.Path(TMP) / "src3.mp4")
    _g3 = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                          "testsrc2=s=64x64:r=25:d=3", "-c:v", "libx264", "-pix_fmt",
                          "yuv420p", _SRC3], check=False, capture_output=True, timeout=60)
    _sd = getattr(MM, "stab_detect", None)
    _trf3, _err3 = None, "ABSENT"
    try:
        _trf3 = _sd(pathlib.Path(_SRC3)) if callable(_sd) else None
        _trf3b = _sd(pathlib.Path(_SRC3)) if callable(_sd) else None   # idempotent
    except Exception as _e:
        _err3, _trf3b = str(_e)[-300:], None
    _n3 = os.path.getsize(_trf3) if _trf3 and os.path.isfile(_trf3) else -1
    check("d16_analyse_reelle_ecrit_un_trf_de_plus_de_1000_octets_en_cache",
          _g3.returncode == 0 and _trf3 is not None and _n3 > 1000
          and _trf3 == _sp(pathlib.Path(_SRC3)) and _trf3b == _trf3
          and not list(pathlib.Path(_trf3).parent.glob("*.tmp*")), (_n3, _err3))
    _OUT3 = os.path.join(TMP, "stab.mp4")
    _cmd3, _rc3, _e3 = None, -1, "commande absente"
    try:
        _cmd3, _ = MS._build_montage_command(
            [V1SPEC(path=_SRC3, src_dur=3.0, src_in=0.0, start=0.0, end=3.0,
                    stab={"smooth": 10, "crop": "black", "zoom": 5, "trf": str(_trf3)})],
            [], [], None, w=64, h=64, fps=25, mix_db={}, ducking=False,
            duration_master=False, preview=True, out=_OUT3)
        _r3 = subprocess.run([_FB] + list(_cmd3[1:]), check=False, capture_output=True,
                             text=True, timeout=180)
        _rc3, _e3 = _r3.returncode, (_r3.stderr or "")[-400:]
    except (TypeError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (rendu stab : %s)" % _e)
    _nb3 = -1
    try:
        _p3 = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                              "-count_frames", "-select_streams", "v:0", "-show_entries",
                              "stream=nb_read_frames", "-of", "csv=p=0", _OUT3],
                             check=False, capture_output=True, text=True, timeout=60)
        _nb3 = int((_p3.stdout or "").strip() or -1)
    except (ValueError, OSError, subprocess.TimeoutExpired) as _e:
        print("  (ffprobe stab : %s)" % _e)
    check("d16_rendu_reel_avec_vidstabtransform_rend_0_et_75_images",
          _n3 > 1000 and _rc3 == 0 and "vidstabtransform=" in FLAT(_cmd3 or [])
          and _nb3 == 75, (_rc3, _nb3, _e3))

print("\n[6] D-16 routes /stab")
r = c.post("/api/montage/stab", json={"src": {"job_id": "nope"}}); d = J(r)
check("d16_post_stab_source_inconnue_400_ou_404", r.status_code in (400, 404), (r.status_code, d))
r = c.get("/api/montage/stab", params={"src": json.dumps({"job_id": "nope"})}); d = J(r)
check("d16_get_stab_repond_ready_false_ou_404_sans_fabriquer",
      r.status_code in (200, 404) and (r.status_code == 404 or d.get("ready") is False), (r.status_code, d))
if _FB is None:
    check("d16_routes_reelles_SKIP_sans_ffmpeg", True)
else:
    # Une source NEUVE (4 s) : son cache est vide, POST doit lancer un job.
    _SRC4 = str(pathlib.Path(TMP) / "src4.mp4")
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=s=64x64:r=25:d=4", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", _SRC4], check=False, capture_output=True, timeout=60)
    r = c.get("/api/montage/stab", params={"src": json.dumps({"file_path": _SRC4})}); d0 = J(r)
    r1 = c.post("/api/montage/stab", json={"src": {"file_path": _SRC4}}); d1 = J(r1)
    check("d16_get_puis_post_stab_lancent_un_job_sans_avoir_fabrique",
          r.status_code == 200 and d0.get("ready") is False
          and r1.status_code == 200 and d1.get("ok") is True and d1.get("ready") is False
          and isinstance(d1.get("job_id"), str), (r.status_code, d0, r1.status_code, d1))
    import time as _time
    _st, _t0 = {}, _time.time()
    while _time.time() - _t0 < 60:
        _st = J(c.get("/api/jobs/%s" % d1.get("job_id")))
        if str(_st.get("status", "")).lower() in ("done", "failed"):
            break
        _time.sleep(0.5)
    _spp4 = _sp(pathlib.Path(_SRC4)) if callable(_sp) else None
    check("d16_le_job_stab_finit_done_et_le_trf_existe",
          str(_st.get("status", "")).lower() == "done" and _st.get("provider") == "montage_stab"
          and _spp4 is not None and _spp4.exists() and _spp4.stat().st_size > 1000, (_st, _spp4))
    # Le job d'analyse est INVISIBLE des jobs et du cout (pipeline.list_jobs,
    # cost_usage, _JOBS_SANS_DEPENSE) — temoin : un job `ugc` pose a la main
    # est liste, et la reponse de cout porte total_usd. Le job est depose
    # dans un finally : cost_usage lit TOUS les jobs done. Les coroutines
    # passent par le portail du TestClient (`c.portal.call`) : le moteur
    # aiosqlite vit sur SA boucle, un `asyncio.run` neuf ne la partage pas.
    from app.services.storage import JobRecord as _JR, async_session_factory as _asf
    _JID = "cafe0000-d16d-4000-8000-000000000001"

    async def _pose(jid, prov):
        async with _asf() as s:
            s.add(_JR(id=jid, status="done", progress=100, title="temoin d16",
                      image_filename="ugc_temoin", provider=prov))
            await s.commit()

    async def _depose(jid):
        async with _asf() as s:
            j = await s.get(_JR, jid)
            if j is not None:
                await s.delete(j); await s.commit()

    _jobs, _cout = [], {}
    try:
        c.portal.call(_pose, _JID, "ugc")
        _rj = c.get("/api/jobs", params={"limit": 200}); _jobs = _rj.json() if _rj.status_code == 200 else []
        _rc = c.get("/api/cost/usage"); _cout = J(_rc)
    except Exception as _e:
        print("  (temoin jobs/cout : %s)" % _e)
    finally:
        c.portal.call(_depose, _JID)
    _ids = [j.get("job_id") for j in _jobs if isinstance(j, dict)]   # cle `job_id` (_job_to_dict)
    check("d16_le_job_stab_est_invisible_de_get_jobs_le_temoin_ugc_y_est",
          str(_st.get("status", "")).lower() == "done" and _JID in _ids and d1.get("job_id") not in _ids,
          (len(_ids), d1.get("job_id") in _ids, _JID in _ids,
           [(j.get("job_id"), j.get("provider"), j.get("status")) for j in _jobs if isinstance(j, dict)][:5]))
    _byp = _cout.get("by_provider") if isinstance(_cout.get("by_provider"), dict) else None
    check("d16_le_cout_ignore_le_job_stab_sans_cle_non_tarife",
          _rc.status_code == 200 and "total_usd" in _cout and _byp is not None
          and not any("montage_stab" in str(k) for k in _byp), (_rc.status_code, _byp))
    # Banc croise : la chaine litterale de la table des jobs sans depense EST
    # la constante du service (pipeline/routes l'importent, la table non).
    from app.api import routes as _routes
    check("d16_montage_stab_est_dans_les_jobs_sans_depense_et_vaut_la_constante",
          A("_STAB_PROVIDER", None) == "montage_stab"
          and A("_STAB_PROVIDER", None) in getattr(_routes, "_JOBS_SANS_DEPENSE", {})
          and "montage_proxy" in getattr(_routes, "_JOBS_SANS_DEPENSE", {}),
          (A("_STAB_PROVIDER", None), sorted(getattr(_routes, "_JOBS_SANS_DEPENSE", {}))))
    r2 = c.post("/api/montage/stab", json={"src": {"file_path": _SRC4}}); d2 = J(r2)
    r3 = c.get("/api/montage/stab", params={"src": json.dumps({"file_path": _SRC4})}); d3 = J(r3)
    check("d16_second_post_repond_ready_sans_job_et_get_ready_true",
          r2.status_code == 200 and d2 == {"ok": True, "ready": True, "job_id": None}
          and r3.status_code == 200 and d3.get("ready") is True, (d2, d3))
    # Espion /render : la spec V1 porte `stab` avec le trf de la source.
    _cap = {}
    _vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg

    def _espion(*a, **k):
        _cap["v1"] = a[0] if a else None
        _cmd = _vrai_build(*a, **k)
        _cap["cmd"] = FLAT(_cmd[0] if isinstance(_cmd, tuple) else _cmd)
        return _cmd

    _tlr = TL("rendu", n=1, src=_SRC4); _tlr["preview"] = True
    _tlr["clips"][0]["stab"] = {"on": True, "smooth": 30}
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        _rr = c.post("/api/montage/render", json=_tlr)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
    _v1c = (_cap.get("v1") or [{}])[0] if isinstance(_cap.get("v1"), list) else {}
    _stc = _v1c.get("stab") if isinstance(_v1c, dict) else None
    check("d16_le_rendu_porte_stab_avec_le_trf_de_la_source_et_vidstabtransform",
          _rr.status_code == 200 and isinstance(_stc, dict) and _stc.get("smooth") == 30
          and _stc.get("trf") == str(_spp4) and "vidstabtransform=input=" in (_cap.get("cmd") or ""),
          (_rr.status_code, _stc, (_cap.get("cmd") or "")[:200]))
    # Etat vide : le MEME rendu sans `stab` ne porte ni le champ ni le filtre.
    _cap.clear(); _tlr["clips"][0].pop("stab")
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        _rr0 = c.post("/api/montage/render", json=_tlr)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
    _v1c0 = (_cap.get("v1") or [{}])[0] if isinstance(_cap.get("v1"), list) else {}
    check("d16_sans_stab_le_rendu_ne_porte_ni_le_champ_ni_le_filtre",
          isinstance(_stc, dict) and _rr0.status_code == 200 and isinstance(_v1c0, dict) and "path" in _v1c0
          and _v1c0.get("stab") is None and "vidstab" not in (_cap.get("cmd") or "x"),
          (_rr0.status_code, _v1c0.get("stab"), (_cap.get("cmd") or "")[:120]))

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
