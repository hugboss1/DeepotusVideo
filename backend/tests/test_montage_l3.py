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
[4] D-14 KEYFRAMES D'ECHELLE ET D'OPACITE. Les points `motion_points` d'un
overlay V2 portent en plus `scale?` (0.05..3) et `opacity?` (0..1) :
`_motion_points` rend des 6-uplets (t, x, y, rotate|None, scale|None,
opacity|None). Candidat MESURE le 22/09/2026 sur ffmpeg 8.1.1 (scratchpad
d14/mesure*.py) : `sendcmd` sur `scale@mps w` rend 0 et scale change bien ses
images (showinfo 100x50 → 300x150) mais `overlay` garde la taille INITIALE de
sa 2e entree (100 px a t=0,2 ET t=2,5) → ECARTE ; retenu B : pad rgba + zoompan
en horloge `it` sur une toile FIXE owmax x min(2·owmax, 3·h) (rognage vertical
invisible, y clampe −0,5..1,5), media pose a sa largeur MINIMALE puis grossi
(zoompan clampe z a 1..10 → smin releve a smax/10 avec warning ; net jusqu'a
~2x). Opacite : `sendcmd` en tete de chaine sur `colorchannelmixer@mpo<j> aa`,
UNE commande `[expr]` par segment (TI 0..1) + une plate finale — l'echantillon-
nage a 1/25 du plan depassait le plafond CreateProcess des 30 s. Points tous
egaux → filtre statique qui fait foi sur tf/opacity ; aucun point porteur →
chaine de L2 octet pour octet (temoin positif). Etat vide : 4-uplets, `_mp_cmds`
ABSENT, chaine sans zoompan/sendcmd. Mesure reelle (SKIP sans ffmpeg OU sans
Pillow) : fond gris + PNG rouge, 75 images, largeur 80 → 240 px, rouge 0,9 → 0,2.
[5] D-9 PISTE D'AJUSTEMENT. `_build_montage_command(…, adjust_clips=)` : une
liste de {start, end, effects} (clips SANS source, piste de genre `adjust`, id
`j1` cote client). Chaque clip devient un post-pass `[aj<j>]` sur le cadre
COMPOSE (apres le dernier overlay `[ob<n>]` et le maitre de duree, AVANT les
titres `[tt<j>]` et S1), par `_fx.build_chain(…, f"aj{j}", f"ajfx{j}", ctx)`
en horloge GLOBALE : [start, end] devient t0/t1 de chaque effet (bornage de
effects_engine._timed : split + sendcmd + blend, PAS enable=), un effet qui
porte deja t0/t1 (bornes LOCALES du rack) est ramene dans le clip. Pin MESURE
des bornes (22/09/2026) : l'enveloppe se nomme `<prefixe>e<idx>env` (uid_e =
f"{uid}e{idx}" dans build_chain), donc `1.000 blend@ajfx0e0env all_opacity 1`
et `2.500 blend@ajfx0e0env all_opacity 0.0000` (_opacity_cmds : `%.3f`, `1` a
100 % par la garde vf_blend, `%.4f` ailleurs). PROUVE que le pin rougit sans
bornage : e2 sans t0/t1 → _timed rend la chaine nue, aucun sendcmd (mesure en
commentant le bornage, puis remis). Sans clip, clip sans effet, type inconnu,
bornes illisibles ou hors duree : commande historique octet pour octet. Etat
vide : `adjust_clips` inconnu de la signature → TypeError (BUILD le rend en
temoin). Mesure reelle (SKIP sans ffmpeg ou Pillow) : fond GRIS 3 s (statique,
pas testsrc2 : seul un fond fixe rend le bornage mesurable par un pixel) +
vignette sur [1, 2] → rc 0, 75 images, coin sombre a t=1,5 seulement. Espion
/render : piste {id:"j1", kind:"adjust"} + clip sans src → `adjust_clips`
porte {start:1.0, end:2.0, effects:[…]} ; sans effets, transmis avec
effects == [] et absent de la commande.
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
    temoin au lieu de tuer le banc — et TOUTE autre exception du service
    aussi : MESURE le 23/09/2026 (mutations_montage_l3.py n°3), un
    `KeyError` (`_RETIME["nearest"]`) tuait le banc au lieu de le faire
    rougir ; le temoin nomme le type, la ligne compare et rougit."""
    clip = {k: kw.pop(k) for k in ("dz", "speed", "retime", "stab", "src_in") if k in kw}
    a = {"w": 64, "h": 64, "fps": 25, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": True,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    try:
        cmd, _ = MS._build_montage_command([V1SPEC(**clip)], [], [], None, **a)
    except Exception as e:                 # faute n°6 : rougir, pas mourir
        return "%s: %s" % (type(e).__name__, e)
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
# Revue (4) : un gap AVANT le clip stabilise — le gap est l'entree [0:v]
# (lavfi color), le clip stabilise l'entree [1:v] : seg_stab est indexe par
# SEGMENT (gap compris), pas par clip.
_cg = FLAT((MS._build_montage_command(
    [V1SPEC(start=2.0, end=6.0, stab={"smooth": 20, "crop": "keep", "zoom": 0, "trf": _trf})],
    [], [], None, w=64, h=64, fps=25, mix_db={}, ducking=False, duration_master=False,
    preview=True, out=os.path.join(TMP, "g.mp4")) or [[]])[0])
check("d16_un_gap_avant_le_clip_stabilise_garde_les_index_d_entree",
      "[0:v]setsar=1" in _cg and "[1:v]vidstabtransform=" in _cg and _cg.count("vidstabtransform=") == 1, _cg[:400])
# Revue (Important 1) : deux threads sur la MEME source → UN seul ffmpeg,
# deux resultats identiques (verrou par cible ; `_run` compte par
# monkeypatch, et fabrique un faux .trf de 16 octets a la place de ffmpeg).
import threading as _thr
_SRCL = os.path.join(TMP, "lock.mp4"); open(_SRCL, "wb").write(b"lockmp4")
_vrai_run_mm, _n_ff = MM._run, []


class _R:
    returncode, stderr = 0, b""


def _faux_run(cmd, *, timeout, quoi):
    _n_ff.append(timeout)
    import time as _t; _t.sleep(0.3)      # laisse le second thread arriver
    pathlib.Path(str(cmd[-4]).split("result='")[1].rstrip("'").replace("\\:", ":")).write_bytes(b"x" * 16)
    return _R()


_res, _thr_err = [], []
def _appel():
    try:
        _res.append(str(MM.stab_detect(pathlib.Path(_SRCL))))
    except Exception as _e:
        _thr_err.append(str(_e))
MM._run = _faux_run
try:
    _ts = [_thr.Thread(target=_appel) for _ in range(2)]
    [t.start() for t in _ts]; [t.join(10) for t in _ts]
finally:
    MM._run = _vrai_run_mm
check("d16_deux_analyses_concurrentes_ne_lancent_qu_un_ffmpeg_meme_resultat",
      callable(getattr(MM, "stab_detect", None)) and _thr_err == [] and len(_n_ff) == 1
      and len(_res) == 2 and _res[0] == _res[1] and _res[0].endswith("_stab.trf")
      and os.path.isfile(_res[0]) and not list(pathlib.Path(_res[0]).parent.glob("*.tmp*")),
      (_n_ff, _res, _thr_err))
check("d16_le_timeout_d_analyse_a_un_plancher_de_900_s", _n_ff == [900], _n_ff)
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

print("\n[4] D-14 keyframes d'echelle et d'opacite sur les overlays")
# Etat vide : `_motion_points` historique rend des 4-uplets (scale/opacity
# ignores), `_mp_cmds` n'existe pas, la chaine overlay ne connait ni zoompan ni
# sendcmd → chaque check rougit sans tuer le banc.
_mp = A("_motion_points", lambda c: "ABSENT")
pts = _mp({"start": 1, "end": 4, "motion_points": [{"t": 0, "x": .5, "y": .5, "scale": .5, "opacity": 1},
                                                   {"t": 3, "x": .5, "y": .5, "scale": 1.5, "opacity": .2, "rotate": 10}]})
check("d14_les_points_portent_scale_et_opacity_ou_none",
      isinstance(pts, list) and len(pts) == 2 and len(pts[0]) == 6 and pts[0][4] == .5 and pts[0][5] == 1.0
      and pts[1][4] == 1.5 and pts[1][5] == .2 and pts[1][3] == 10.0, pts)
pts2 = _mp({"start": 0, "end": 3, "motion_points": [{"t": 0, "x": .5, "y": .5}, {"t": 3, "x": .6, "y": .5, "scale": 9, "opacity": -1}]})
check("d14_scale_clampe_0_05_3_opacity_0_1_absent_none",
      isinstance(pts2, list) and len(pts2) == 2 and len(pts2[0]) == 6 and pts2[0][4] is None and pts2[0][5] is None
      and pts2[1][4] == 3.0 and pts2[1][5] == 0.0, pts2)
pts3 = _mp({"start": 0, "end": 3, "motion_points": [{"t": 0, "x": .5, "y": .5, "scale": "nan", "opacity": "x"}]})
check("d14_scale_ou_opacity_invalide_retombe_a_none_sans_tuer_le_point",
      isinstance(pts3, list) and len(pts3) == 1 and len(pts3[0]) == 6 and pts3[0][4] is None and pts3[0][5] is None, pts3)
_mp_cmds = A("_mp_cmds", lambda *a, **k: "ABSENT")
cm = _mp_cmds([(0.0, 0.5), (2.0, 1.5), (3.0, 1.0)], "colorchannelmixer@mpo0", "aa", lambda v: "%.3f" % v)
# Forme MESUREE (22/09, ffmpeg 8.1.1, scratchpad d14/mesure3.py) : UNE commande
# « t0-t1 [expr] cible opt v0+(dv)*TI » par segment (TI 0..1 dans l'intervalle,
# rc 0, alpha 0,90/0,58/0,20/0,54/0,76 a t=0,2/1,0/1,9/2,5/2,9 pour 1→0,2→0,8)
# + une commande plate finale ; « ; » echappe « \; » ; JAMAIS de virgule dans
# l'expression (lerp(a,b,TI) casse le parseur). Remplace l'echantillonnage a
# 1/25 du plan : 30 s de cles faisaient 28 824 caracteres (CreateProcess 32 767).
check("d14_mp_cmds_une_commande_expr_par_segment_plus_une_plate_finale",
      isinstance(cm, str) and cm.count("\\;") == 2 and cm.startswith("0-2 [expr] colorchannelmixer@mpo0 aa 0.5+(1)*TI\\;")
      and "\\;2-3 [expr] colorchannelmixer@mpo0 aa 1.5+(-0.5)*TI\\;" in cm and cm.endswith("\\;3 colorchannelmixer@mpo0 aa 1.000")
      and all("," not in s and s.count(" ") in (3, 4) for s in cm.split("\\;")) and ";" not in cm.replace("\\;", ""), cm)
cm2 = _mp_cmds([(1.0, 0.2)], "colorchannelmixer@mpo0", "aa", lambda v: "%.3f" % v)
check("d14_mp_cmds_une_seule_cle_est_une_commande_plate_sans_segment",
      cm2 == "1 colorchannelmixer@mpo0 aa 0.200", cm2)
cm8 = _mp_cmds([(i * 8.0, 0.1 * i) for i in range(8)], "colorchannelmixer@mpo0", "aa", lambda v: "%.3f" % v)
check("d14_mp_cmds_8_points_sur_56_s_tiennent_en_moins_de_420_caracteres",
      isinstance(cm8, str) and cm8.count("\\;") == 7 and cm8.count("[expr]") == 7 and len(cm8) <= 420, len(cm8) if isinstance(cm8, str) else cm8)

OVF = str(pathlib.Path(TMP) / "ov.png")
pathlib.Path(OVF).write_bytes(b"x")


def OVBUILD(w=64, h=64, **ov):
    """`_build_montage_command` avec un V1 et UN overlay V2 (forme de la liste
    `v2` de /render : path, is_image, src_dur, src_in, start, end, opacity, tf,
    mp, layer — recopiee de tests/test_montage_pistes_rendu.py ov_spec).
    `motion_points=` passe par MS._motion_points comme /render le fait."""
    o = {"path": OVF, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
         "end": 3.0, "opacity": None, "tf": None, "mp": None, "layer": 0}
    mpts = ov.pop("motion_points", None)
    o.update(ov)
    if mpts is not None:
        o["mp"] = MS._motion_points({"start": o["start"], "end": o["end"], "motion_points": mpts})
    try:
        cmd, _ = MS._build_montage_command([V1SPEC()], [o], [], None, w=w, h=h, fps=25, mix_db={},
                                           ducking=False, duration_master=False, preview=True,
                                           out=os.path.join(TMP, "o.mp4"))
    except Exception as e:                 # mutation n°8 : IndexError sur des 5-uplets
        return "%s: %s" % (type(e).__name__, e)
    return FLAT(cmd)


# Candidat retenu pour l'echelle (MESURE 22/09/2026, ffmpeg 8.1.1, scratchpad
# d14/mesure.py) : A (`sendcmd` sur `scale@mps w`) rend 0 et scale CHANGE bien
# la taille de ses images (showinfo 100x50 → 300x150) mais `overlay` garde la
# taille INITIALE de sa 2e entree (largeur mesuree 100 px a t=0,2 ET t=2,5) →
# A echoue ; B (`pad` rgba + `zoompan` sur l'horloge `it`) rend 0, 75 images,
# largeur 120 → 302 px, alpha conserve (coin gris 128). L'opacite : `sendcmd`
# sur `colorchannelmixer@mpo aa` (option commandable « T ») : alpha 0,90 a
# t=0,2 et 0,19 a t=2,5. zoompan ne fait QUE grossir (z clampe 1..10) : l'overlay
# est pose a sa largeur MINIMALE puis grossi ; la toile est owmax x 2·owmax.
_ov = OVBUILD(motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .5, "opacity": 1},
                             {"t": 2, "x": .5, "y": .5, "scale": 1.5, "opacity": .2}])
_zp = _ov[_ov.find("zoompan=z='"):] if "zoompan=z='" in _ov else ""
check("d14_l_echelle_animee_passe_par_pad_rgba_et_zoompan_en_horloge_it",
      "scale=w=32:h=192:force_original_aspect_ratio=decrease" in _ov and ",pad=w=96:h=192:x=(ow-iw)/2:y=(oh-ih)/2:color=black@0," in _ov
      and _zp.startswith("zoompan=z='if(lt(it,0),1,") and ":d=1:s=96x192:fps=25" in _zp and "(t-" not in _zp[:_zp.find("[ov0]")]
      and _ov.find("fps=25,format=rgba") < _ov.find("zoompan"), _ov[_ov.find("[1:v]"):][:420])
check("d14_l_opacite_animee_passe_par_colorchannelmixer_at_mpo_et_sendcmd_expr",
      "[1:v]sendcmd=c='0-2 [expr] colorchannelmixer@mpo0 aa 1+(-0.8)*TI\\;2 colorchannelmixer@mpo0 aa 0.200',scale=w=32" in _ov
      and "format=rgba,colorchannelmixer@mpo0=aa=1.0,pad=" in _ov, _ov[_ov.find("[1:v]"):][:300])
_ov0 = OVBUILD(motion_points=[{"t": 0, "x": .5, "y": .5}, {"t": 2, "x": .6, "y": .5}])
check("d14_sans_scale_ni_opacity_sur_les_points_la_chaine_est_celle_de_l2",
      "[1:v]scale=64:-2,setsar=1,fps=25,format=rgba,setpts=" in _ov0 and "overlay=x='(" in _ov0 and "-w/2'" in _ov0
      and "sendcmd" not in _ov0 and "zoompan" not in _ov0 and "@mpo" not in _ov0 and ",pad=w=" not in _ov0, _ov0[_ov0.find("[1:v]"):][:300])
_ovr = OVBUILD(motion_points=[{"t": 0, "x": .2, "y": .2, "rotate": 0}, {"t": 2, "x": .8, "y": .8, "rotate": 90}])
check("d14_les_lecteurs_rotate_x_y_gardent_leur_forme_sur_les_6_uplets",
      ",rotate='if(lt(t,0),0," in _ovr and ":ow='hypot(iw,ih)':oh=ow:c=none" in _ovr
      and "overlay=x='(if(lt(t,1),12.8," in _ovr and "-w/2':y='(if(lt(t,1),12.8," in _ovr, _ovr[_ovr.find("[1:v]"):][:400])
_ovs = OVBUILD(tf={"x": .5, "y": .5, "scale": 1.0, "rotate": 0.0},
               motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .75}, {"t": 2, "x": .5, "y": .5, "scale": .75}])
check("d14_des_points_de_meme_echelle_restent_statiques_et_font_foi_sur_tf",
      "[1:v]scale=48:-2,setsar=1,fps=25,format=rgba,setpts=" in _ovs and "zoompan" not in _ovs and ",pad=w=" not in _ovs, _ovs[_ovs.find("[1:v]"):][:200])
class _Journal:
    """Remplace MS.logger le temps d'un appel : capte les warning."""
    def __init__(self): self.msgs = []
    def warning(self, m, *a, **k): self.msgs.append(str(m))
    def __getattr__(self, k): return lambda *a, **k2: None
_lg0, _jl = MS.logger, _Journal()
MS.logger = _jl
try:
    _ovz = OVBUILD(motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .05}, {"t": 2, "x": .5, "y": .5, "scale": 3}])
finally:
    MS.logger = _lg0
_zpz = _ovz[_ovz.find("zoompan=z='"):_ovz.find("[ov0]")] if "zoompan=z='" in _ovz else ""
# smin = 3/10 = 0,3 (relevee de 0,05, warning) ; toile 192 x min(384, 3·64 = 192)
check("d14_le_zoom_est_borne_a_10_la_largeur_de_base_remonte_a_smax_sur_10_avec_warning",
      "scale=w=20:h=192:" in _ovz and ":s=192x192:" in _zpz and _zpz.startswith("zoompan=z='if(lt(it,0),1,if(lt(it,2),1+(9)*(it-0)/2,10))'")
      and any("relevée à 0.30" in m for m in _jl.msgs), (_zpz[:120], _jl.msgs))
_ovh = OVBUILD(w=1920, h=1080, motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .5}, {"t": 2, "x": .5, "y": .5, "scale": 3}])
check("d14_la_toile_est_rognee_a_3h_en_hauteur_1080p_smax_3_donne_5760x3240",
      ",pad=w=5760:h=3240:" in _ovh and ":s=5760x3240:" in _ovh and "scale=w=960:h=3240:" in _ovh, _ovh[_ovh.find("[1:v]"):][:200])
_ovo = OVBUILD(opacity=0.5, motion_points=[{"t": 0, "x": .5, "y": .5, "opacity": .8}, {"t": 1, "x": .5, "y": .5, "opacity": .8}])
check("d14_une_opacite_constante_sur_les_points_est_statique_et_fait_foi_sur_le_clip",
      "format=rgba,colorchannelmixer=aa=0.8,setpts=" in _ovo and "sendcmd" not in _ovo and "@mpo" not in _ovo, _ovo[_ovo.find("[1:v]"):][:200])

# --- mesure ffmpeg reelle : fond gris 3 s + PNG rouge 200x100 en overlay dont
# l'echelle va de 0,25 a 0,75 et l'opacite de 1 a 0,2 → rc 0, 75 images ;
# largeur du rouge plus grande a t=2,5 qu'a t=0,2, rouge plus pale (Pillow).
try:
    from PIL import Image as _Im
except Exception:
    _Im = None
if _FB is None or _Im is None:
    check("d14_rendu_reel_SKIP_sans_ffmpeg_ou_sans_pillow", True)
else:
    _SRCG = str(pathlib.Path(TMP) / "gris.mp4")
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=gray:s=320x240:r=25:d=3", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", _SRCG], check=False, capture_output=True, timeout=60)
    _PNG = str(pathlib.Path(TMP) / "rouge.png")
    if _Im is not None:
        _Im.new("RGBA", (200, 100), (255, 0, 0, 255)).save(_PNG)
    _OUT4 = os.path.join(TMP, "d14.mp4")
    _o4 = {"path": _PNG, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 0.0,
           "end": 3.0, "opacity": None, "tf": None, "layer": 0,
           "mp": MS._motion_points({"start": 0, "end": 3, "motion_points": [
               {"t": 0, "x": .5, "y": .5, "scale": .25, "opacity": 1},
               {"t": 2, "x": .5, "y": .5, "scale": .75, "opacity": .2}]})}
    _cmd4, _rc4, _e4 = None, -1, "commande absente"
    try:
        _cmd4, _ = MS._build_montage_command(
            [V1SPEC(path=_SRCG, src_dur=3.0, start=0.0, end=3.0)], [_o4], [], None,
            w=320, h=240, fps=25, mix_db={}, ducking=False, duration_master=False,
            preview=True, out=_OUT4)
    except Exception as _e:                # faute n°6 : rougir, pas mourir (mutation n°8)
        _e4 = "%s: %s" % (type(_e).__name__, _e)
    if isinstance(_cmd4, list) and _cmd4 and _Im is not None:
        _cmd4 = [_FB] + list(_cmd4[1:])
        _r4 = subprocess.run(_cmd4, check=False, capture_output=True, text=True, timeout=180)
        _rc4, _e4 = _r4.returncode, (_r4.stderr or "")[-400:]
    _nb4 = -1
    try:
        _p4 = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                              "-count_frames", "-select_streams", "v:0", "-show_entries",
                              "stream=nb_read_frames", "-of", "csv=p=0", _OUT4],
                             check=False, capture_output=True, text=True, timeout=60)
        _nb4 = int((_p4.stdout or "").strip() or -1)
    except (ValueError, OSError):
        pass
    check("d14_rendu_reel_zoompan_et_sendcmd_rendent_0_et_75_images",
          _rc4 == 0 and _nb4 == 75 and "zoompan" in FLAT(_cmd4 or []) and "sendcmd" in FLAT(_cmd4 or []), (_rc4, _nb4, _e4))

    def _mesure(t):
        """(largeur du rouge, rouge moyen 0..1) sur la ligne mediane a t."""
        _png = os.path.join(TMP, "d14_%s.png" % t)
        subprocess.run([_FB, "-y", "-loglevel", "error", "-ss", str(t), "-i", _OUT4,
                        "-frames:v", "1", _png], check=False, capture_output=True, timeout=60)
        if _Im is None or not os.path.isfile(_png):
            return (-1, -1.0)
        _im = _Im.open(_png).convert("RGB"); _px = _im.load(); _w, _h = _im.size
        _red = [x for x in range(_w) if _px[x, _h // 2][0] > 150 and _px[x, _h // 2][1] < 110]
        _cen = [_px[x, _h // 2][0] for x in range(_w // 2 - 10, _w // 2 + 10)]
        return ((_red[-1] - _red[0] + 1) if _red else 0, round((sum(_cen) / len(_cen) - 128) / 127, 2))
    _m02, _m25 = _mesure(0.2), _mesure(2.5)
    # attendus : largeur 320·0,25 = 80 px (+ ~8 a t=0,2) puis 320·0,75 = 240 px ;
    # rouge ~0,9 puis ~0,2.
    check("d14_rendu_reel_l_overlay_est_plus_large_et_plus_pale_a_la_fin",
          _rc4 == 0 and 70 <= _m02[0] <= 110 and 220 <= _m25[0] <= 260
          and 0.8 <= _m02[1] <= 1.0 and 0.1 <= _m25[1] <= 0.35, (_m02, _m25))

print("\n[5] D-9 piste d'ajustement : un post-pass borne apres les overlays, avant les titres")
# Etat vide : `adjust_clips=` est un mot-cle INCONNU de la signature → BUILD
# rend "TypeError: …", qui n'est ni la commande historique ni une commande.
_c0 = BUILD()
check("d9_sans_adjust_clips_la_commande_est_l_historique",
      _c0.startswith("ffmpeg") and BUILD(adjust_clips=None) == _c0 and BUILD(adjust_clips=[]) == _c0,
      (_c0[:60], BUILD(adjust_clips=None)[:120]))
AJ = [{"start": 1.0, "end": 2.5, "effects": [{"type": "vignette", "intensity": 60}]}]
_ca = BUILD(adjust_clips=AJ, subs_ass=None)
# `[aj0]` ne peut venir QUE de la signature (V1SPEC ne connait pas
# adjust_clips) ; `ajfx0` est le prefixe passe a build_chain, dont l'enveloppe
# de _timed se nomme `<prefixe>e<idx>env` (mesure : uid_e = f"{uid}e{idx}").
check("d9_un_clip_d_ajustement_pose_build_chain_sur_le_cadre_final",
      _ca.startswith("ffmpeg") and "[aj0]" in _ca and "ajfx0" in _ca
      and "[n0]format=yuv420p,split=2[ajfx0e0enva][ajfx0e0envb]" in _ca
      and "[aj0]format=yuv420p[outv]" in _ca,
      _ca[:600])
# Bornes : _opacity_cmds ecrit `%.3f` ; a 100 % il pose `all_opacity 1`
# (garde vf_blend), a 0 `all_opacity 0.0000`. Sans bornage, _timed rend la
# chaine nue (aucun sendcmd) — prouve en commentant le bornage (voir
# docstring).
_PIN_T0 = "1.000 blend@ajfx0e0env all_opacity 1"
_PIN_T1 = "2.500 blend@ajfx0e0env all_opacity 0.0000"
check("d9_les_bornes_du_clip_deviennent_t0_t1_de_chaque_effet",
      "[aj0]" in _ca and "sendcmd" in _ca and "blend@ajfx0" in _ca
      and _PIN_T0 in _ca and _PIN_T1 in _ca,
      [s for s in _ca.split("\\;") if "blend@ajfx0" in s][:6])
# Apres les overlays : le post-pass lit `[ob0]`, la sortie du dernier overlay.
_ov = {"path": V1F, "is_image": False, "src_dur": 4.0, "src_in": 0.0, "start": 0.0,
       "end": 4.0, "opacity": None, "tf": None, "mp": None, "layer": 0}
try:
    _cov, _ = MS._build_montage_command([V1SPEC()], [_ov], [], None, w=64, h=64, fps=25,
                                        mix_db={}, ducking=False, duration_master=False,
                                        preview=True, out=os.path.join(TMP, "o.mp4"),
                                        adjust_clips=AJ)
    _cov = FLAT(_cov)
except TypeError as _e:
    _cov = "TypeError: %s" % _e
check("d9_l_ajustement_lit_la_sortie_du_dernier_overlay",
      "[ob0]" in _cov and "[aj0]" in _cov and _cov.find("[aj0]") > _cov.find("[ob0]")
      and "[ob0]format=yuv420p,split=2[ajfx0e0enva]" in _cov, _cov[:600])
_t0 = os.path.join(TMP, "t0.ass")
open(_t0, "w", encoding="utf-8").write("[Script Info]\n")
_cat = BUILD(adjust_clips=AJ, titles_ass=[_t0])
check("d9_l_ajustement_precede_les_titres_et_s1",
      "[tt0]" in _cat and "[aj0]" in _cat and _cat.find("[aj0]") < _cat.find("[tt0]")
      and "[aj0]subtitles=" in _cat, _cat[:600])
_c2 = BUILD(adjust_clips=[AJ[0], {"start": 3, "end": 4, "effects": [{"type": "vignette", "intensity": 30}]}])
check("d9_deux_clips_s_enchainent_aj0_puis_aj1",
      "[aj0]" in _c2 and "[aj1]" in _c2 and _c2.find("[aj0]") < _c2.find("[aj1]")
      and "[aj0]format=yuv420p,split=2[ajfx1e0enva]" in _c2
      and "3.000 blend@ajfx1e0env all_opacity 1" in _c2, _c2[:600])
# Temoin positif : _ca differe de _c0 ; les clips vides, inconnus ou hors
# duree (V1SPEC dure 4 s, 900 > 4) rendent la commande historique.
check("d9_un_clip_sans_effet_ou_hors_duree_est_ignore",
      _ca != _c0 and _c0.startswith("ffmpeg")
      and BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": []}]) == _c0
      and BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": [{"type": "inconnu"}]}]) == _c0
      and BUILD(adjust_clips=[{"start": 900, "end": 950, "effects": AJ[0]["effects"]}]) == _c0
      and BUILD(adjust_clips=[{"start": "x", "end": 2, "effects": AJ[0]["effects"]}]) == _c0,
      (BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": []}])[:80],
       BUILD(adjust_clips=[{"start": 900, "end": 950, "effects": AJ[0]["effects"]}])[:80]))
_cl = BUILD(adjust_clips=[{"start": 1, "end": 3, "effects": [{"type": "vignette", "intensity": 60, "t0": 0.5, "t1": 9}]}])
check("d9_un_effet_avec_ses_propres_bornes_locales_est_ramene_dans_le_clip",
      "blend@ajfx0" in _cl and "1.500 blend@ajfx0e0env all_opacity 1" in _cl
      and "3.000 blend@ajfx0e0env all_opacity 0.0000" in _cl,
      [s for s in _cl.split("\\;") if "blend@ajfx0" in s][:6])
# Revue (23/09) : des bornes LOCALES hors du clip (t0 5, t1 6 dans un clip
# [1, 2]) ou trop courtes (0,98..1,0) donnaient t1-t0 < 0,05 → _timed rendait
# la chaine NUE : `[n0]vignette=angle=0.600[aj0]` sans sendcmd, l'effet PLEIN
# CADRE de 0 a total (mesure avant correctif). Attendu : l'effet est ignore,
# commande historique. Temoin positif : _cl porte bien un blend@ajfx0.
_chors = BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": [{"type": "vignette", "intensity": 60, "t0": 5, "t1": 6}]}])
check("d9_des_bornes_locales_hors_du_clip_ignorent_l_effet_jamais_plein_cadre",
      _c0.startswith("ffmpeg") and "blend@ajfx0" in _cl and _chors == _c0,
      [s for s in _chors.split(";") if "aj0" in s][:3])
_ccourt = BUILD(adjust_clips=[{"start": 1, "end": 2, "effects": [{"type": "vignette", "intensity": 60, "t0": 0.98, "t1": 1.0}]}])
check("d9_des_bornes_locales_trop_courtes_ignorent_l_effet_jamais_plein_cadre",
      _c0.startswith("ffmpeg") and "blend@ajfx0" in _cl and _ccourt == _c0,
      [s for s in _ccourt.split(";") if "aj0" in s][:3])
# --- mesure ffmpeg reelle : fond gris 3 s + ajustement vignette sur [1, 2] →
# rc 0, 75 images ; le coin est plus sombre a t=1,5 qu'a t=0,5 et a t=2,5
# (source STATIQUE, pas testsrc2 : seul un fond fixe rend le bornage mesurable
# par un pixel). SKIP sans ffmpeg ou sans Pillow, comme les sections voisines.
if _FB is None or _Im is None:
    check("d9_rendu_reel_SKIP_sans_ffmpeg_ou_sans_pillow", True)
else:
    _SRCG9 = str(pathlib.Path(TMP) / "gris9.mp4")
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=gray:s=64x64:r=25:d=3", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", _SRCG9], check=False, capture_output=True, timeout=60)
    _OUT9 = os.path.join(TMP, "d9.mp4")
    _cmd9, _rc9, _e9 = None, -1, "commande absente"
    try:
        _cmd9, _ = MS._build_montage_command(
            [V1SPEC(path=_SRCG9, src_dur=3.0, start=0.0, end=3.0)], [], [], None,
            w=64, h=64, fps=25, mix_db={}, ducking=False, duration_master=False,
            preview=True, out=_OUT9,
            adjust_clips=[{"start": 1.0, "end": 2.0, "effects": [{"type": "vignette", "intensity": 100}]}])
    except Exception as _e:                # faute n°6 : rougir, pas mourir
        _e9 = "%s: %s" % (type(_e).__name__, _e)
    if isinstance(_cmd9, list) and _cmd9:
        _cmd9 = [_FB] + list(_cmd9[1:])
        _r9 = subprocess.run(_cmd9, check=False, capture_output=True, text=True, timeout=180)
        _rc9, _e9 = _r9.returncode, (_r9.stderr or "")[-400:]
    _nb9 = -1
    try:
        _p9 = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                              "-count_frames", "-select_streams", "v:0", "-show_entries",
                              "stream=nb_read_frames", "-of", "csv=p=0", _OUT9],
                             check=False, capture_output=True, text=True, timeout=60)
        _nb9 = int((_p9.stdout or "").strip() or -1)
    except (ValueError, OSError):
        pass
    check("d9_rendu_reel_l_ajustement_rend_0_et_75_images",
          _rc9 == 0 and _nb9 == 75 and "[aj0]" in FLAT(_cmd9 or []), (_rc9, _nb9, _e9))

    def _coin(t):
        """Luminance du coin haut-gauche (moyenne 4x4) a t, -1 si illisible."""
        _png = os.path.join(TMP, "d9_%s.png" % t)
        subprocess.run([_FB, "-y", "-loglevel", "error", "-ss", str(t), "-i", _OUT9,
                        "-frames:v", "1", _png], check=False, capture_output=True, timeout=60)
        if not os.path.isfile(_png):
            return -1
        _im = _Im.open(_png).convert("L"); _px = _im.load()
        return sum(_px[x, y] for x in range(4) for y in range(4)) / 16.0
    _k05, _k15, _k25 = _coin(0.5), _coin(1.5), _coin(2.5)
    check("d9_rendu_reel_le_coin_n_est_sombre_qu_entre_les_bornes",
          _rc9 == 0 and _k05 > 0 and _k15 >= 0 and _k15 < _k05 - 20 and abs(_k25 - _k05) < 6,
          (_k05, _k15, _k25))
    # Espion /render : un clip sur une piste de genre `adjust`, SANS src, est
    # transmis a la commande avec ses bornes ; sans effets il est transmis
    # aussi (effects == []) mais n'entre pas dans la commande.
    _cap9 = {}
    _vb9, _vr9 = MS._build_montage_command, MS._run_ffmpeg

    def _espion9(*a, **k):
        _cap9["adjust_clips"] = k.get("adjust_clips", "ABSENT")
        _cmd = _vb9(*a, **k)
        _cap9["cmd"] = FLAT(_cmd[0] if isinstance(_cmd, tuple) else _cmd)
        return _cmd

    _tl9 = TL("adj", n=1, src=_SRCG9); _tl9["preview"] = True
    _tl9["tracks"] = [{"id": "v1", "kind": "video"}, {"id": "j1", "kind": "adjust"},
                      {"id": "a1", "kind": "audio", "bus": "dialogue"}]
    _tl9["clips"].append({"tr": "j1", "id": "j1c", "start": 1, "end": 2, "kind": "adjust",
                          "effects": [{"type": "vignette", "intensity": 60}]})
    MS._build_montage_command, MS._run_ffmpeg = _espion9, (lambda cmd, out: None)
    try:
        _rr9 = c.post("/api/montage/render", json=_tl9)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vb9, _vr9
    _aj9 = _cap9.get("adjust_clips")
    check("d9_le_rendu_transmet_le_clip_d_ajustement_avec_ses_bornes",
          _rr9.status_code == 200 and isinstance(_aj9, list)
          and _aj9 == [{"start": 1.0, "end": 2.0, "effects": [{"type": "vignette", "intensity": 60}]}]
          and "[aj0]" in (_cap9.get("cmd") or "") and "1.000 blend@ajfx0e0env all_opacity 1" in (_cap9.get("cmd") or ""),
          (_rr9.status_code, _aj9, (_cap9.get("cmd") or "")[:200]))
    _cap9.clear(); _tl9["clips"][-1].pop("effects")
    MS._build_montage_command, MS._run_ffmpeg = _espion9, (lambda cmd, out: None)
    try:
        _rr9b = c.post("/api/montage/render", json=_tl9)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vb9, _vr9
    check("d9_sans_effets_le_clip_est_transmis_vide_et_absent_de_la_commande",
          isinstance(_aj9, list) and _rr9b.status_code == 200
          and _cap9.get("adjust_clips") == [{"start": 1.0, "end": 2.0, "effects": []}]
          and "ffmpeg" in (_cap9.get("cmd") or "") and "[aj0]" not in (_cap9.get("cmd") or "x"),
          (_rr9b.status_code, _cap9.get("adjust_clips"), (_cap9.get("cmd") or "")[:120]))

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
