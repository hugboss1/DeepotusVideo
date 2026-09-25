# -*- coding: utf-8 -*-
"""L6 — AUDIO cote backend. En-tete recopie de test_montage_l5.py (env,
check, J, TestClient sans port ouvert ; fin : fermeture des handles puis
rmtree) : dossier de donnees NEUF par execution, toute lecture gardee — un
banc qui meurt sur un acces nu ne dit pas quelles assertions manquent (faute
n6 : le DETAIL est evalue AVANT le court-circuit de la condition, il ne doit
donc jamais lever).
Run : & $PY tests/test_montage_l6.py   (depuis backend/)

[1] D-23 / D-25 — VOCABULAIRE `sfx_service`. Deux types neufs (`eq6`
egaliseur 6 bandes, `dehum` anti-ronflement), `denoise` gagne un plancher
`nf`, un apprentissage `learn_in/learn_out` (secondes de SOURCE) et la
compensation du retard d'afftdn (1200 echantillons a 48 kHz, mesure),
`stereo.pan` passe a la loi a PUISSANCE CONSTANTE, `build_audition_command`
sait prefixer le bruit appris. Non-regression : chaines et commandes de
`9aca870` recopiees EN DUR (calculees sur le code d'avant le lot). Les
mesures reelles utilisent `effects_preview.ffmpeg_bin()` (SKIP si
injoignable).
"""
import array, json, math, os, sys, tempfile, subprocess, pathlib, shutil, wave
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl6_")
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

from app.services import sfx_service as S                # noqa: E402
from app.services import effects_preview as PV           # noqa: E402


def F(nom, defaut=None):
    """`getattr` module — un attribut ABSENT (avant l'implementation) fait
    ROUGIR les checks qui le lisent, jamais TUER le banc."""
    return getattr(S, nom, defaut)


def SAN(raw):
    """sanitize_fx sans exception."""
    try:
        return S.sanitize_fx(raw)
    except Exception as e:                               # noqa: BLE001
        return [{"type": "EXC", "params": {"e": repr(e)}}]


def P0(raw):
    """params du PREMIER module normalise, {} sinon."""
    v = SAN(raw)
    return (v[0].get("params") or {}) if v and isinstance(v[0], dict) else {}


def CH(raw, **kw):
    """fx_chain(sanitize_fx(raw), **kw) — une exception devient une chaine."""
    try:
        return S.fx_chain(SAN(raw), **kw)
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


def CALL(fn, *a, **kw):
    """Appel garde : ('ok', valeur) ou ('exc', type)."""
    try:
        f = F(fn) if isinstance(fn, str) else fn
        if f is None:
            return ("absent", None)
        return ("ok", f(*a, **kw))
    except Exception as e:                               # noqa: BLE001
        return ("exc", type(e).__name__)


# ════════════════════════ [1] vocabulaire sfx_service ═════════════════════════
print("\n[1] vocabulaire sfx_service (eq6, dehum, denoise appris, pan)")

# --- constantes recopiees de 9aca870 (code d'AVANT le lot, sortie brute) ------
LISTES = [
    [],
    [{"type": "filter", "mode": "low", "freq": 800, "q": 2}],
    [{"type": "eq3", "bass_db": 3, "mid_db": -2, "treble_db": 4}],
    [{"type": "echo"}],
    [{"type": "reverb", "mix": 40, "decay_s": 3}],
    [{"type": "distortion", "drive": 50}],
    [{"type": "stereo", "width": 50}],
    [{"type": "stereo", "width": 150}],
    [{"type": "normalize", "target_lufs": -14}, {"type": "deesser", "intensity": 70},
     {"type": "compressor", "threshold_db": -30, "ratio": 6}],
    [{"type": "normalize"}, {"type": "reverb", "mix": 20}, {"type": "filter", "mode": "band", "freq": 2000},
     {"type": "eq3", "mid_db": 5}, {"type": "stereo", "width": 180}, {"type": "echo", "time_ms": 120},
     {"type": "compressor"}, {"type": "distortion", "drive": 10}, {"type": "deesser"}],
]
CHAINES_9ACA870 = [
    '',
    'lowpass=f=800:width_type=q:w=2',
    'bass=g=3:f=110,equalizer=f=1000:t=q:w=1:g=-2,treble=g=4:f=8000',
    'aecho=0.9:0.3:300|600|900:0.3|0.09|0.027',
    'aecho=0.9:0.4:129|303|561|939:0.465|0.2162|0.1005|0.0468',
    'volume=10.5,asoftclip=type=atan',
    'stereotools=slev=0.5',
    'stereowiden=delay=15:feedback=0.325:crossfeed=0.325:drymix=0.85',
    'deesser=i=0.7,acompressor=threshold=0.0316:ratio=6:attack=50:release=250,loudnorm=I=-14:TP=-1.5:LRA=11',
    'bandpass=f=2000:width_type=q:w=1,equalizer=f=1000:t=q:w=1:g=5,deesser=i=0.5,acompressor=threshold=0.1:ratio=4:attack=50:release=250,volume=2.9,asoftclip=type=atan,aecho=0.9:0.3:120|240|360:0.3|0.09|0.027,aecho=0.9:0.2:86|202|374|626:0.41|0.1681|0.0689|0.0283,stereowiden=delay=15:feedback=0.4:crossfeed=0.43:drymix=0.85,loudnorm=I=-16:TP=-1.5:LRA=11',
]
AUDITIONS_9ACA870 = [
    ['ffmpeg', '-y', '-hide_banner', '-t', '4.0', '-i', 'C:\\l6\\src.wav', '-vn', '-ar', '44100', '-ac', '2', '-f', 'wav', 'C:\\l6\\out.wav'],
    ['ffmpeg', '-y', '-hide_banner', '-ss', '2.5', '-t', '6.0', '-i', 'C:\\l6\\src.wav', '-vn', '-af', 'atempo=1.25,bass=g=3:f=110,equalizer=f=1000:t=q:w=1:g=-2,treble=g=4:f=8000,aecho=0.9:0.3:300|600|900:0.3|0.09|0.027,volume=0.7079', '-ar', '44100', '-ac', '2', '-f', 'wav', 'C:\\l6\\out.wav'],
    ['ffmpeg', '-y', '-hide_banner', '-ss', '10.0', '-t', '12.0', '-i', 'C:\\l6\\src.wav', '-vn', '-af', 'bandpass=f=2000:width_type=q:w=1,equalizer=f=1000:t=q:w=1:g=5,deesser=i=0.5,acompressor=threshold=0.1:ratio=4:attack=50:release=250,volume=2.9,asoftclip=type=atan,aecho=0.9:0.3:120|240|360:0.3|0.09|0.027,aecho=0.9:0.2:86|202|374|626:0.41|0.1681|0.0689|0.0283,stereowiden=delay=15:feedback=0.4:crossfeed=0.43:drymix=0.85,loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '2', '-f', 'wav', 'C:\\l6\\out.wav'],
]

# --- contrats : ordre, constantes -------------------------------------------
_ord = F("_FX_ORDER", ())
check("t1_ordre_contrat_douze_types",
      tuple(_ord) == ("filter", "dehum", "eq3", "denoise", "eq6", "deesser", "compressor",
                      "distortion", "echo", "reverb", "stereo", "normalize"), str(_ord))
check("t1_constantes_dn_learn",
      (F("DN_RATE"), F("DN_DELAY"), F("LEARN_MAX"), F("LEARN_MIN")) == (48000, 1200, 1.0, 0.2),
      str((F("DN_RATE"), F("DN_DELAY"), F("LEARN_MAX"), F("LEARN_MIN"))))

# --- sanitize_fx ---------------------------------------------------------------
_EQ6_DEF = {"hp_hz": 0.0, "ls_f": 100.0, "ls_g": 0.0,
            "p1_f": 250.0, "p1_g": 0.0, "p1_q": 1.0, "p2_f": 800.0, "p2_g": 0.0, "p2_q": 1.0,
            "p3_f": 2500.0, "p3_g": 0.0, "p3_q": 1.0, "p4_f": 6000.0, "p4_g": 0.0, "p4_q": 1.0,
            "hs_f": 8000.0, "hs_g": 0.0}
_e6 = P0([{"type": "eq6"}])
check("t1_sanitize_eq6_defauts_complets", _e6 == _EQ6_DEF, str(_e6))
_dh = P0([{"type": "dehum"}])
check("t1_sanitize_dehum_defauts", _dh == {"base": 50.0, "harmonics": 4.0, "amount": 100.0}, str(_dh))
_e6b = P0([{"type": "eq6", "ls_g": 40, "p1_q": 0, "hp_hz": 900, "p4_f": 5}])
check("t1_sanitize_eq6_bornes",
      (_e6b.get("ls_g"), _e6b.get("p1_q"), _e6b.get("hp_hz"), _e6b.get("p4_f")) == (12.0, 0.3, 300.0, 40.0),
      str(_e6b))
_b55 = P0([{"type": "dehum", "base": 55}]).get("base")
_b54 = P0([{"type": "dehum", "base": 54}]).get("base")
_b99 = P0([{"type": "dehum", "base": 99}]).get("base")
check("t1_sanitize_dehum_base_bornee_sans_arrondi", (_b55, _b54, _b99) == (55.0, 54.0, 60.0),
      str((_b55, _b54, _b99)))
_dn = P0([{"type": "denoise"}])
check("t1_sanitize_denoise_nf_auto_et_learn_defauts",
      _dn == {"amount": 12.0, "nf": 0.0, "learn_in": 0.0, "learn_out": 0.0}, str(_dn))
_dnl = P0([{"type": "denoise", "nf": -45, "learn_in": 10, "learn_out": 13}])
check("t1_sanitize_denoise_learn_gardes",
      (_dnl.get("nf"), _dnl.get("learn_in"), _dnl.get("learn_out")) == (-45.0, 10.0, 13.0), str(_dnl))
_dnx = P0([{"type": "denoise", "nf": -300, "learn_in": -5, "learn_out": 1e9}])
check("t1_sanitize_denoise_bornes",
      (_dnx.get("nf"), _dnx.get("learn_in"), _dnx.get("learn_out")) == (-80.0, 0.0, 86400.0), str(_dnx))
_pan_seul = SAN([{"type": "pan", "pan": 50}])
_st_temoin = SAN([{"type": "stereo", "pan": 50}])
check("t1_type_pan_inconnu_ignore_temoin_stereo_pan",
      _pan_seul == [] and len(_st_temoin) == 1 and _st_temoin[0].get("params", {}).get("pan") == 50.0,
      str((_pan_seul, _st_temoin)))

# --- fx_chain : eq6 ------------------------------------------------------------
_ch_neutre = CH([{"type": "eq6"}])
_ch_p2 = CH([{"type": "eq6", "p2_g": 3}])
check("t1_eq6_neutre_vide_temoin_p2",
      _ch_neutre == "" and "equalizer=f=800:t=q:w=1:g=3" in _ch_p2, str((_ch_neutre, _ch_p2)))
check("t1_eq6_ouvre_par_fltp_sans_plateau_neutre",
      _ch_p2.startswith("aformat=sample_fmts=fltp,") and "lowshelf" not in _ch_p2
      and "highshelf" not in _ch_p2 and "highpass" not in _ch_p2
      and _ch_p2.count("equalizer=") == 1, _ch_p2)
_ch_hp = CH([{"type": "eq6", "hp_hz": 80}])
check("t1_eq6_passe_haut", _ch_hp == "aformat=sample_fmts=fltp,highpass=f=80", _ch_hp)
_ch_all = CH([{"type": "eq6", "hp_hz": 40, "ls_g": 2, "p1_g": -3, "p2_g": 1, "p2_q": 2.5,
               "p3_g": 4, "p4_g": -1, "hs_f": 10000, "hs_g": 5}])
check("t1_eq6_six_bandes_dans_l_ordre",
      _ch_all == ("aformat=sample_fmts=fltp,highpass=f=40,lowshelf=f=100:g=2,"
                  "equalizer=f=250:t=q:w=1:g=-3,equalizer=f=800:t=q:w=2.5:g=1,"
                  "equalizer=f=2500:t=q:w=1:g=4,equalizer=f=6000:t=q:w=1:g=-1,"
                  "highshelf=f=10000:g=5"), _ch_all)

# --- fx_chain : dehum -----------------------------------------------------------
_ch_dh = CH([{"type": "dehum"}])
check("t1_dehum_defauts_quatre_crans_50",
      _ch_dh == ("bandreject=f=50:width_type=q:w=10:m=1,bandreject=f=100:width_type=q:w=10:m=1,"
                 "bandreject=f=150:width_type=q:w=10:m=1,bandreject=f=200:width_type=q:w=10:m=1"), _ch_dh)
_ch_dh60 = CH([{"type": "dehum", "base": 60, "harmonics": 3, "amount": 50}])
check("t1_dehum_60_trois_crans_dose",
      _ch_dh60 == ("bandreject=f=60:width_type=q:w=10:m=0.5,bandreject=f=120:width_type=q:w=10:m=0.5,"
                   "bandreject=f=180:width_type=q:w=10:m=0.5"), _ch_dh60)
_ch_dh0 = CH([{"type": "dehum", "amount": 0}])
check("t1_dehum_amount0_vide_temoin_defaut", _ch_dh0 == "" and _ch_dh.count("bandreject") == 4,
      str((_ch_dh0, _ch_dh)))
_ch_55 = CH([{"type": "dehum", "base": 55, "harmonics": 1}])
_ch_54 = CH([{"type": "dehum", "base": 54, "harmonics": 1}])
check("t1_dehum_base55_vers60_base54_vers50",
      _ch_55.startswith("bandreject=f=60:") and _ch_54.startswith("bandreject=f=50:"), str((_ch_55, _ch_54)))
_ch_h6 = CH([{"type": "dehum", "harmonics": 6.4}])
check("t1_dehum_harmoniques_entieres", _ch_h6.count("bandreject") == 6 and "f=300:" in _ch_h6, _ch_h6)

# --- ordre et non-regression ---------------------------------------------------
_ch_ord = CH([{"type": "stereo", "width": 50}, {"type": "eq6", "p1_g": 2}, {"type": "denoise"},
              {"type": "dehum"}, {"type": "filter", "freq": 5000}])
_pos = [_ch_ord.find(k) for k in ("lowpass=", "bandreject=", "afftdn=", "equalizer=f=250", "stereotools=")]
check("t1_ordre_fragments_contrat", all(p >= 0 for p in _pos) and _pos == sorted(_pos), str((_pos, _ch_ord)))
_nr = [CH(L) for L in LISTES]
_nr_diff = [(i, a, b) for i, (a, b) in enumerate(zip(_nr, CHAINES_9ACA870)) if a != b]
check("t1_non_regression_dix_listes_9aca870",
      len(_nr) == 10 and len(CHAINES_9ACA870) == 10 and not _nr_diff and _nr[9].count(",") > 5, str(_nr_diff))

# --- stereo : pan a puissance constante ---------------------------------------
_st0 = CH([{"type": "stereo", "pan": 0, "width": 50}])
check("t1_pan0_aucun_pan_temoin_width", "pan=" not in _st0 and "balance" not in _st0
      and _st0 == "stereotools=slev=0.5", _st0)
_st50 = CH([{"type": "stereo", "pan": 50}])
check("t1_pan50_loi_puissance_constante",
      _st50 == "aformat=channel_layouts=stereo,pan=stereo|c0=0.5412*c0|c1=1*c1", _st50)
_stm100 = CH([{"type": "stereo", "pan": -100}])
check("t1_pan_moins100_canal_droit_eteint",
      _stm100 == "aformat=channel_layouts=stereo,pan=stereo|c0=1*c0|c1=0*c1", _stm100)
_stw = CH([{"type": "stereo", "pan": -50, "width": 150}])
check("t1_pan_et_width_largeur_puis_pan_jamais_balance",
      _stw.startswith("stereowiden=") and _stw.endswith("pan=stereo|c0=1*c0|c1=0.5412*c1")
      and "balance" not in _stw, _stw)

# --- denoise --------------------------------------------------------------------
_DN_DEF = ("aresample=48000,apad=pad_len=1200,afftdn=nr=12,atrim=start_sample=1200,"
           "asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0")
_d0 = CH([{"type": "denoise"}])
check("t1_denoise_defaut_retard_compense", _d0 == _DN_DEF, _d0)
_d45 = CH([{"type": "denoise", "nf": -45}])
check("t1_denoise_nf_moins45", "afftdn=nr=12:nf=-45," in _d45 and "tn=" not in _d45, _d45)
_d10 = CH([{"type": "denoise", "nf": -10}])
check("t1_denoise_nf_moins10_borne_a_moins20", "afftdn=nr=12:nf=-20," in _d10, _d10)
_d_off = CH([{"type": "denoise", "amount": 0}])
check("t1_denoise_amount0_vide_temoin_defaut", _d_off == "" and _d0.startswith("aresample="), str((_d_off, _d0)))
_dl = CH([{"type": "denoise", "learn_in": 10, "learn_out": 13}], uid="7", prefix_s=1.0)
check("t1_denoise_appris_asendcmd_nomme",
      "asendcmd=c='0.0 afftdn@dn7 sn start;0.95 afftdn@dn7 sn stop'" in _dl
      and "afftdn@dn7=nr=12" in _dl and "atrim=start_sample=49200," in _dl, _dl)
check("t1_denoise_appris_jamais_tn_temoin_sn", "tn=" not in _dl and " sn start" in _dl
      and "tn=" not in _d0, _dl)
_dl_sans = CH([{"type": "denoise", "learn_in": 10, "learn_out": 13}])
check("t1_denoise_learn_sans_prefixe_commande_simple", _dl_sans == _DN_DEF and "asendcmd" in _dl, _dl_sans)
_ns = CH([{"type": "eq6", "p1_g": 3}], uid="7", prefix_s=1.0)
check("t1_prefixe_ignore_sans_denoise", "asendcmd" not in _ns and "atrim" not in _ns
      and _ns == CH([{"type": "eq6", "p1_g": 3}]) and "equalizer" in _ns, _ns)
_dd = CH([{"type": "denoise", "learn_in": 0, "learn_out": 1}, {"type": "denoise", "amount": 30}],
         uid="3", prefix_s=0.5)
check("t1_deux_denoise_seul_le_premier_apprend",
      _dd.count("asendcmd") == 1 and _dd.count("afftdn@dn3") == 3 and _dd.count("afftdn=nr=30") == 1
      and _dd.count("atrim=start_sample=25200,") == 1 and _dd.count("atrim=start_sample=1200,") == 1, _dd)

# --- learn_of / nf_of -----------------------------------------------------------
def LO(raw):
    return CALL("learn_of", SAN(raw))

check("t1_learn_of_absent_none", LO([{"type": "denoise"}]) == ("ok", None) and LO([]) == ("ok", None),
      str((LO([{"type": "denoise"}]), LO([]))))
check("t1_learn_of_court_none_temoin_long",
      LO([{"type": "denoise", "learn_in": 5, "learn_out": 5.1}]) == ("ok", None)
      and LO([{"type": "denoise", "learn_in": 5, "learn_out": 5.2}]) == ("ok", (5.0, 5.2)),
      str((LO([{"type": "denoise", "learn_in": 5, "learn_out": 5.1}]),
           LO([{"type": "denoise", "learn_in": 5, "learn_out": 5.2}]))))
check("t1_learn_of_borne_a_une_seconde",
      LO([{"type": "denoise", "learn_in": 10, "learn_out": 13}]) == ("ok", (10.0, 11.0)),
      str(LO([{"type": "denoise", "learn_in": 10, "learn_out": 13}])))
check("t1_learn_of_denoise_coupe_none_temoin",
      LO([{"type": "denoise", "amount": 0, "learn_in": 1, "learn_out": 2}]) == ("ok", None)
      and LO([{"type": "denoise", "amount": 1, "learn_in": 1, "learn_out": 2}]) == ("ok", (1.0, 2.0)),
      str(LO([{"type": "denoise", "amount": 0, "learn_in": 1, "learn_out": 2}])))
check("t1_nf_of_regle",
      (CALL("nf_of", -40.2), CALL("nf_of", -5), CALL("nf_of", -95)) == (("ok", -30), ("ok", -20), ("ok", -80)),
      str((CALL("nf_of", -40.2), CALL("nf_of", -5), CALL("nf_of", -95))))
check("t1_nf_of_non_fini_leve_temoin_fini",
      CALL("nf_of", float("-inf")) == ("exc", "ValueError") and CALL("nf_of", float("nan")) == ("exc", "ValueError")
      and CALL("nf_of", -50.0) == ("ok", -40),
      str((CALL("nf_of", float("-inf")), CALL("nf_of", float("nan")))))

# --- build_audition_command : non-regression + apprentissage --------------------
_SRCP, _OUTP = pathlib.Path("C:/l6/src.wav"), pathlib.Path("C:/l6/out.wav")
_JEUX = [dict(),
         dict(src_in=2.5, length=6.0, gain_db=-3.0, speed=1.25, fx=SAN(LISTES[2] + LISTES[3])),
         dict(src_in=10.0, length=20.0, gain_db=0.02, speed=0.0, fx=SAN(LISTES[9]))]
_aud = [CALL(S.build_audition_command, _SRCP, _OUTP, **k) for k in _JEUX]
check("t1_audition_non_regression_trois_jeux_9aca870",
      [a[1] for a in _aud] == AUDITIONS_9ACA870 and len(AUDITIONS_9ACA870) == 3, str(_aud))
_FXL = SAN([{"type": "denoise", "amount": 20, "learn_in": 1, "learn_out": 2}, {"type": "eq3", "mid_db": 3}])
_al = CALL(S.build_audition_command, _SRCP, _OUTP, src_in=3.0, length=2.5, gain_db=-2.0, speed=1.25, fx=_FXL)
_alc = _al[1] if _al[0] == "ok" and isinstance(_al[1], list) else []
_als = " ".join(map(str, _alc))
check("t1_audition_apprise_deux_entrees_concat",
      _alc.count("-i") == 2 and "concat=n=2:v=0:a=1" in _als and "-filter_complex" in _alc
      and "afftdn@dn" in _als and "asendcmd" in _als, str(_al))
_i1 = _alc.index("-i") if "-i" in _alc else -1
check("t1_audition_prefixe_ss_t_avant_premier_i",
      _i1 > 3 and _alc[_i1 - 4:_i1] == ["-ss", "1.0", "-t", "1.0"], str(_alc[:12]))
_fc = _alc[_alc.index("-filter_complex") + 1] if "-filter_complex" in _alc else ""
_p_part = _fc.split(";")[0] if _fc else ""
check("t1_audition_atempo_jamais_sur_prefixe_temoin_clip",
      "atempo" not in _p_part and "atempo=1.25" in _fc and "volume=" in _fc.split("concat")[-1], _fc)
check("t1_audition_prefixe_traverse_eq3_retire_dans_denoise",
      _fc.find("concat") < _fc.find("equalizer=f=1000") < _fc.find("afftdn@dn") and "atrim=start_sample=49200" in _fc,
      _fc)

# --- rendu REEL ------------------------------------------------------------------
FF = PV.ffmpeg_bin()
try:
    _ver = subprocess.run([FF, "-version"], capture_output=True, text=True, timeout=30).stdout.split("\n")[0]
except Exception:                                        # noqa: BLE001
    _ver = ""
if not _ver:
    print("  SKIP rendu reel : ffmpeg injoignable")
else:
    print("  ffmpeg :", _ver[:60], "(", FF, ")")
    SR = 48000

    def REND(lavfi, af, ch=1):
        """lavfi -> af -> f32le entrelace (liste de canaux), [] si echec."""
        args = [FF, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i", lavfi]
        if af:
            args += ["-af", af]
        args += ["-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-c:a", "pcm_f32le", "-"]
        try:
            p = subprocess.run(args, capture_output=True, timeout=120)
        except Exception:                                # noqa: BLE001
            return []
        if p.returncode != 0:
            print("    ffmpeg rc", p.returncode, p.stderr.decode("utf-8", "replace")[-300:])
            return []
        a = array.array("f")
        a.frombytes(p.stdout[: len(p.stdout) // 4 * 4])
        return [a[k::ch] for k in range(ch)]

    def RMS(x, s0=0, s1=None):
        s1 = len(x) if s1 is None else min(s1, len(x))
        n = s1 - s0
        if n <= 0:
            return 0.0
        return math.sqrt(sum(v * v for v in x[s0:s1]) / n)

    def DB(a, b):
        return 20 * math.log10(a / b) if a > 0 and b > 0 else -999.0

    def GOE(x, f, s0, s1):
        """Amplitude d'une composante f sur [s0,s1) (Goertzel, fenetre de Hann)."""
        n = s1 - s0
        if n <= 1 or len(x) < s1:
            return 0.0
        w = 2 * math.pi * f / SR
        cw = 2 * math.cos(w)
        q1 = q2 = 0.0
        for i in range(n):
            h = 0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
            q0 = cw * q1 - q2 + x[s0 + i] * h
            q2, q1 = q1, q0
        re = q1 - q2 * math.cos(w)
        im = q2 * math.sin(w)
        return math.sqrt(re * re + im * im) * 4 / n

    def PIC(x):
        return max(range(len(x)), key=lambda i: abs(x[i])) if len(x) else -1

    # eq6 : +12 dB a 800 Hz
    _sin800 = "sine=f=800:sample_rate=48000:duration=2"
    _ref = REND(_sin800, "")
    _eq = REND(_sin800, CH([{"type": "eq6", "p2_g": 12}]))
    _g800 = DB(RMS(_eq[0], 24000, 72000), RMS(_ref[0], 24000, 72000)) if _eq and _ref else -999.0
    check("t1_reel_eq6_p2_plus12_a_800", 11.5 <= _g800 <= 12.5, "%.2f dB" % _g800)
    _eq0 = REND(_sin800, CH([{"type": "eq6", "p1_g": 12}]))
    _g800b = DB(RMS(_eq0[0], 24000, 72000), RMS(_ref[0], 24000, 72000)) if _eq0 and _ref else -999.0
    check("t1_reel_eq6_cloche_voisine_moins_forte_temoin", 0.5 < _g800b < 9.0 and _g800 > _g800b + 3,
          "%.2f dB" % _g800b)

    # dehum : 50 Hz ecrase, 1000 Hz intact
    _hum = "aevalsrc='0.1*sin(2*PI*50*t)+0.1*sin(2*PI*1000*t)':s=48000:d=3"
    _h0 = REND(_hum, "")
    _h1 = REND(_hum, CH([{"type": "dehum"}]))
    if _h0 and _h1:
        _d50 = DB(GOE(_h1[0], 50, 96000, 144000), GOE(_h0[0], 50, 96000, 144000))
        _d1k = DB(GOE(_h1[0], 1000, 96000, 144000), GOE(_h0[0], 1000, 96000, 144000))
    else:
        _d50 = _d1k = 999.0
    check("t1_reel_dehum_50hz_moins25_1khz_intact", _d50 <= -25.0 and abs(_d1k) < 0.5,
          "50 Hz %.2f dB, 1 kHz %.2f dB" % (_d50, _d1k))

    # denoise : clic a 0,5 s — decalage et longueur
    _clic = "aevalsrc='if(eq(n\\,24000)\\,0.9\\,0)':s=48000:d=1"
    _c_new = REND(_clic, CH([{"type": "denoise"}]))
    _c_old = REND(_clic, "afftdn=nr=12")
    _pn = PIC(_c_new[0]) if _c_new else -1
    _po = PIC(_c_old[0]) if _c_old else -1
    _ln = len(_c_new[0]) if _c_new else -1
    check("t1_reel_denoise_decalage_nul_longueur_exacte", abs(_pn - 24000) <= 1 and _ln == 48000,
          "pic %d longueur %d" % (_pn, _ln))
    check("t1_reel_denoise_temoin_ancienne_chaine_decale", 1100 <= _po - 24000 <= 1300, "pic %d" % _po)
    _c_nf = REND(_clic, CH([{"type": "denoise", "nf": -30, "amount": 24}]))
    check("t1_reel_denoise_nf_rend", bool(_c_nf) and len(_c_nf[0]) == 48000 and abs(PIC(_c_nf[0]) - 24000) <= 1,
          "longueur %s" % (len(_c_nf[0]) if _c_nf else None))

    # dehum + denoise + eq6 enchaines : longueur exacte (asetnsamples p=0)
    _ch3 = CH([{"type": "eq6", "p3_g": 4}, {"type": "denoise"}, {"type": "dehum"}])
    _c3 = REND(_clic, _ch3)
    check("t1_reel_chaine_complete_longueur_et_decalage",
          bool(_c3) and len(_c3[0]) == 48000 and abs(PIC(_c3[0]) - 24000) <= 1,
          "%s %s" % ((len(_c3[0]), PIC(_c3[0])) if _c3 else None, _ch3))

    # pan 50 sur source mono : ecart G/D 5,33 dB
    _mono = "sine=f=440:sample_rate=48000:duration=1"
    _pa = REND(_mono, CH([{"type": "stereo", "pan": 50}]), ch=2)
    _gd = DB(RMS(_pa[1], 4800), RMS(_pa[0], 4800)) if _pa else -999.0
    check("t1_reel_pan50_mono_ecart_5_33", abs(_gd - 5.33) <= 0.3, "%.2f dB" % _gd)
    _pz = REND(_mono, CH([{"type": "stereo", "pan": -100}]), ch=2)
    _rz = RMS(_pz[1], 4800) if _pz else -1.0
    check("t1_reel_pan_moins100_droite_muette_temoin_gauche",
          _pz and _rz < 1e-6 and RMS(_pz[0], 4800) > 0.01, "droite %s" % _rz)

    # build_audition_command apprise : execution reelle
    _src = pathlib.Path(TMP) / "l6src.wav"
    _mk = subprocess.run([FF, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
                          "aevalsrc='0.05*sin(2*PI*440*t)+0.01*(random(0)-0.5)+if(eq(n\\,144000)\\,0.9\\,0)'"
                          ":s=48000:d=6", "-c:a", "pcm_s16le", str(_src)], capture_output=True, timeout=60)
    _out = pathlib.Path(TMP) / "l6aud.wav"
    _cmd = CALL(S.build_audition_command, _src, _out, src_in=2.0, length=2.5, fx=SAN(
        [{"type": "denoise", "amount": 20, "learn_in": 0.2, "learn_out": 1.2}]))
    _rc, _nfr, _pk = None, -1, -1
    if _mk.returncode == 0 and _cmd[0] == "ok":
        _cm = [FF] + list(_cmd[1][1:])
        try:
            _r = subprocess.run(_cm, capture_output=True, text=True, timeout=60)
            _rc = _r.returncode
            if _rc:
                print("    ", (_r.stderr or "")[-400:])
            with wave.open(str(_out), "rb") as w:
                _nfr = w.getnframes()
                _raw = w.readframes(_nfr)
                _sm = array.array("h")
                _sm.frombytes(_raw[: len(_raw) // 2 * 2])
                _L = _sm[0::w.getnchannels()]
                _pk = max(range(len(_L)), key=lambda i: abs(_L[i])) if len(_L) else -1
        except Exception as e:                           # noqa: BLE001
            print("    audition :", repr(e))
    check("t1_reel_audition_apprise_rc0_duree_exacte", _rc == 0 and abs(_nfr - 110250) <= 1,
          "rc %s trames %s" % (_rc, _nfr))
    check("t1_reel_audition_apprise_clic_a_sa_place", abs(_pk - 44100) <= 2, "pic %s" % _pk)

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
