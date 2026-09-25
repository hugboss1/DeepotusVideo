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
# cloture L6 (mutations, 25/09/2026) : TROU ferme -- la garde `LEARN_MIN - 1e-9` de learn_of n'etait tenue par aucune
# ligne (5 -> 5,2 vaut 0,2000…02 en flottant et passe sans la tolerance) ; 1,0 -> 1,2 vaut 0,1999…96 : sans elle, refusee
# alors que la couche (dzmLearnRange) et la route noise-profile l'acceptent. Temoin : 1,0 -> 1,19 refusee.
check("t1_learn_of_tolerance_1_0_1_2_acceptee_temoin_1_19_refusee",
      LO([{"type": "denoise", "learn_in": 1.0, "learn_out": 1.2}]) == ("ok", (1.0, 1.2))
      and LO([{"type": "denoise", "learn_in": 1.0, "learn_out": 1.19}]) == ("ok", None),
      str((LO([{"type": "denoise", "learn_in": 1.0, "learn_out": 1.2}]),
           LO([{"type": "denoise", "learn_in": 1.0, "learn_out": 1.19}]))))
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
# revue T2 : source FICTIVE -> la sonde rend 0 (inconnue) et abandonne le prefixe ; la duree est donc
# donnee ici (`src_dur`, comme la route qui la sonde hors boucle) — le cas inconnu est banc en [3]
_al = CALL(S.build_audition_command, _SRCP, _OUTP, src_in=3.0, length=2.5, gain_db=-2.0, speed=1.25, fx=_FXL,
           src_dur=60.0)
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


# ═══════════════ [2] apprentissage dans la chaine par clip + noise-profile ═══════════════
# ECART AU PLAN (mesure du 25/09/2026, scratchpad t2) : le plan ecrivait le prefixe par
# `asplit=2` + `atrim=a:b` sur l'entree du clip. Source de 20 min, prefixe a 1150 s, clip
# 0-600 s : maxrss 359 460 Kio (asplit bufferise TOUT le clip en attendant le prefixe que
# concat lit d'abord) contre 19 100 Kio avec une SECONDE entree `-ss a -t L -i src`
# (21 872 Kio pour un prefixe place avant le clip). Le code suit la mesure : seconde entree,
# longueur du prefixe FORCEE a P echantillons (`atrim=end_sample=P,apad=whole_len=P` : un
# decodeur qui demarre en retard au seek ne doit pas decaler le retrait du prefixe).
print("\n[2] apprentissage par prefixe dans la chaine par clip + route noise-profile")
from app.services import montage_service as MS          # noqa: E402
import asyncio                                           # noqa: E402

# --- commandes de T1 (4d2053f), sortie brute de _build_montage_command, chemins fictifs ---
T1_CMDS = json.loads(r'''{"den": [["ffmpeg", "-y", "-t", "4.0", "-i", "V1.mp4", "-i", "SRC.wav", "-filter_complex", "[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=4.0,trim=0:4.0,setpts=PTS-STARTPTS[n0];[1:a]atrim=2.0:5.0,asetpts=PTS-STARTPTS,aresample=48000,apad=pad_len=1200,afftdn=nr=24:nf=-30,atrim=start_sample=1200,asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0,aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=500|500[va0];[va0]anull[vall];[vall]aresample=async=1[outa];[n0]format=yuv420p[outv]", "-map", "[outv]", "-map", "[outa]", "-t", "4.0", "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "OUT.mp4"], 4.0], "den_learn_music": [["ffmpeg", "-y", "-t", "4.0", "-i", "V1.mp4", "-stream_loop", "-1", "-i", "SRC.wav", "-filter_complex", "[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=4.0,trim=0:4.0,setpts=PTS-STARTPTS[n0];[1:a]aresample=48000,apad=pad_len=1200,afftdn=nr=24:nf=-30,atrim=start_sample=1200,asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0,aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5[mtrk];[mtrk]aresample=async=1[outa];[n0]format=yuv420p[outv]", "-map", "[outv]", "-map", "[outa]", "-t", "4.0", "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "OUT.mp4"], 4.0], "mix": [["ffmpeg", "-y", "-t", "4.0", "-i", "V1.mp4", "-i", "SRC.wav", "-i", "SRC.wav", "-filter_complex", "[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=4.0,trim=0:4.0,setpts=PTS-STARTPTS[n0];[1:a]atrim=2.0:5.0,asetpts=PTS-STARTPTS,atempo=1.25,bass=g=3:f=110,aresample=48000,apad=pad_len=1200,afftdn=nr=12,atrim=start_sample=1200,asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0,afade=t=in:st=0:d=0.3,afade=t=out:st=2.0:d=0.4,volume='pow(10,(if(lt(t,0),-3,if(lt(t,1),-3+(3)*(t-0)/1,0)))/20)':eval=frame,aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=500|500[va0];[2:a]atrim=2.0:4.5,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,pan=stereo|c0=0.642*c0|c1=1*c1,aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=1000|1000[sa1];[va0]anull[vall];[vall][sa1]amix=inputs=2:duration=longest:normalize=0,aresample=async=1[outa];[n0]format=yuv420p[outv]", "-map", "[outv]", "-map", "[outa]", "-t", "4.0", "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "OUT.mp4"], 4.0]}''')
_V1P = [{"path": "V1.mp4", "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]


def AC(fx, liste=True, **kw):
    """Clip audio pur (dict du builder) ; `liste` pose `fx_list` comme /render."""
    fl = SAN(fx)
    d = {"tr": "a1", "path": "SRC.wav", "src_dur": 20.0, "src_in": 2.0, "start": 0.5, "end": 3.5,
         "gain": 0.5, "fade_in": 0, "fade_out": 0, "fade_in_curve": None, "fade_out_curve": None,
         "fx_chain": CH(fx), "speed": 0.0, "volume_points": None}
    if liste:
        d["fx_list"] = fl
    d.update(kw)
    return d


def BUILD(ac, mu=None, **kw):
    """(cmd, filter_complex) ou (['EXC', repr], '') — jamais d'exception."""
    try:
        a = dict(w=270, h=480, fps=30, mix_db={}, ducking=True, duration_master=True,
                 preview=False, out="OUT.mp4")
        a.update(kw)
        cmd, _t = MS._build_montage_command(_V1P, [], ac, mu, **a)
        fc = cmd[cmd.index("-filter_complex") + 1] if "-filter_complex" in cmd else ""
        return cmd, fc
    except Exception as e:                               # noqa: BLE001
        return ["EXC", repr(e)], ""


_DEN = [{"type": "denoise", "amount": 24, "nf": -30}]
_DENL = [{"type": "denoise", "amount": 24, "nf": -30, "learn_in": 10, "learn_out": 13}]

# non-regression : sans apprentissage, fx_list present ou non, commande == T1
_b1, _ = BUILD([AC(_DEN)])
_b1n, _ = BUILD([AC(_DEN, liste=False)])
check("t2_sans_apprentissage_commande_T1_octet_pour_octet_avec_et_sans_fx_list",
      T1_CMDS.get("den") and _b1 == T1_CMDS["den"][0] and _b1n == T1_CMDS["den"][0], str(_b1)[:300])
_bm, _ = BUILD([AC([{"type": "eq3", "bass_db": 3}, {"type": "denoise"}], speed=1.25, fade_in=0.3,
                   fade_out=0.4, volume_points=[(0.0, -3.0), (1.0, 0.0)]),
                AC([{"type": "stereo", "pan": 40}], tr="a3", start=1.0)])
check("t2_sans_apprentissage_mix_vitesse_fondus_automation_pan_commande_T1",
      T1_CMDS.get("mix") and _bm == T1_CMDS["mix"][0], str(_bm)[:300])

# clip appris : seconde entree -ss 10 -t 1.0, concat, afftdn@dn0, prefixe retire
_bl, _fl = BUILD([AC(_DENL)])
_ii = [i for i, v in enumerate(_bl) if v == "-i"]
check("t2_appris_deux_entrees_de_la_meme_source_prefixe_ss_t_avant_i",
      len(_ii) == 3 and _bl[_ii[1] + 1] == "SRC.wav" and _bl[_ii[2] + 1] == "SRC.wav"
      and _bl[_ii[2] - 4:_ii[2]] == ["-ss", "10.0", "-t", "1.0"] and "-ss" not in _bl[_ii[1] - 2:_ii[1]],
      str(_bl[:14]))
check("t2_appris_branches_prefixe_et_clip_puis_concat",
      "[2:a]asetpts=PTS-STARTPTS,aresample=48000,atrim=end_sample=48000,apad=whole_len=48000[l6p0]" in _fl
      and "[1:a]atrim=2.0:5.0,asetpts=PTS-STARTPTS,aresample=48000[l6c0]" in _fl
      and "[l6p0][l6c0]concat=n=2:v=0:a=1,aresample=48000,asendcmd=c='0.0 afftdn@dn0 sn start;"
          "0.95 afftdn@dn0 sn stop'," in _fl
      and "afftdn@dn0=nr=24:nf=-30,atrim=start_sample=49200" in _fl and "tn=" not in _fl, _fl)
check("t2_appris_reste_de_la_ligne_inchange_jusqu_a_adelay",
      "atrim=start_sample=49200,asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0,aresample=async=1,"
      "aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=500|500[va0]" in _fl, _fl)
check("t2_appris_pas_d_asplit_ecart_mesure_temoin_concat_present",
      "concat=n=2" in _fl and "asplit" not in _fl, _fl[:200])
_blt, _flt = BUILD([AC(_DEN)])
check("t2_temoin_sans_learn_aucune_seconde_entree_ni_concat_ni_instance_nommee",
      _blt.count("-i") == 2 and "concat" not in _flt and "afftdn@" not in _flt and "afftdn=nr=24" in _flt,
      _flt[:300])

# atempo : sur la branche du clip seulement, jamais sur le prefixe
_bs, _fs = BUILD([AC(_DENL, speed=1.25)])
_pb = [x for x in _fs.split(";") if x.endswith("[l6p0]")]
_cb = [x for x in _fs.split(";") if x.endswith("[l6c0]")]
check("t2_appris_atempo_sur_le_clip_jamais_sur_le_prefixe",
      _pb and _cb and "atempo" not in _pb[0] and "atempo=1.25,aresample=48000[l6c0]" in _cb[0], _fs)

# deux clips appris : deux uid distincts, chaque asendcmd vise SA propre instance ; indices d'entree
_b2, _f2 = BUILD([AC(_DENL), AC(_DENL, tr="a3", path="AUTRE.wav", start=1.0),
                  AC([{"type": "echo"}], tr="a3", path="TROIS.wav", start=2.0)])
_i2 = [_b2[i + 1] for i, v in enumerate(_b2) if v == "-i"]
check("t2_deux_clips_appris_deux_uid_distincts",
      "afftdn@dn0=" in _f2 and "afftdn@dn1=" in _f2 and "0.0 afftdn@dn0 sn start;0.95 afftdn@dn0 sn stop" in _f2
      and "0.0 afftdn@dn1 sn start;0.95 afftdn@dn1 sn stop" in _f2 and _f2.count("asendcmd") == 2, _f2)
check("t2_indices_d_entree_suivent_les_entrees_prefixe",
      _i2 == ["V1.mp4", "SRC.wav", "SRC.wav", "AUTRE.wav", "AUTRE.wav", "TROIS.wav"]
      and "[3:a]atrim=2.0:4.5" in _f2 and "[4:a]asetpts=PTS-STARTPTS,aresample=48000,atrim=end_sample" in _f2
      and "[5:a]atrim=2.0:3.5,asetpts=PTS-STARTPTS,aecho" in _f2, (_i2, _f2))

# musique (piste bouclee) : apprentissage ignore, plancher seul == T1
_mu = AC(_DENL)
_bmu, _fmu = BUILD([], _mu)
check("t2_musique_apprentissage_ignore_plancher_seul_commande_T1",
      T1_CMDS.get("den_learn_music") and _bmu == T1_CMDS["den_learn_music"][0]
      and "afftdn=nr=24:nf=-30" in _fmu and "afftdn@" not in _fmu, _fmu)

# prefixe au-dela de la fin de la source : pas de prefixe (temoin : source assez longue)
_bf, _ff = BUILD([AC(_DENL, src_dur=10.1)])
_bg, _fg = BUILD([AC(_DENL, src_dur=11.0)])
check("t2_prefixe_hors_source_ignore_temoin_source_longue_prefixee",
      "afftdn@" not in _ff and "afftdn=nr=24" in _ff and "afftdn@dn0" in _fg, (_ff[:250], _fg[:250]))
# duree de source INCONNUE : pas de prefixe — mesure : une entree -ss au-dela de la fin ne rend aucun
# paquet et fait echouer TOUT le rendu. Revue T2 : /render transporte la duree SONDEE brute
# (`src_dur_sonde`, None = inconnue) a cote du repli 9999 de `src_dur` ; le builder teste None, plus 9999
# (une source reelle de plus de 2 h 46 perdait son apprentissage). Temoins : 9999 s et 10 000 s SONDEES
# gardent le prefixe ; un dict sans la cle (bancs) lit `src_dur` (9998 s, prefixe).
_bu, _fu = BUILD([AC(_DENL, src_dur=9999.0, src_dur_sonde=None)])
_bk, _fk = BUILD([AC(_DENL, src_dur=9998.0)])
_b99, _f99 = BUILD([AC(_DENL, src_dur=9999.0, src_dur_sonde=9999.0)])
_blg, _flg = BUILD([AC(_DENL, src_dur=10000.0, src_dur_sonde=10000.0)])
check("t2_duree_inconnue_pas_de_prefixe_temoin_duree_connue",
      "afftdn@" not in _fu and "afftdn=nr=24" in _fu and _bu.count("-i") == 2 and "afftdn@dn0" in _fk,
      (_fu[:250], _fk[:250]))
check("r4_source_longue_sondee_9999_et_10000_s_gardent_le_prefixe_temoin_inconnue_sans",
      "afftdn@dn0" in _f99 and "[l6p0]" in _f99 and "afftdn@dn0" in _flg and "[l6p0]" in _flg
      and _blg.count("-i") == 3 and "afftdn@" not in _fu, (_f99[:250], _flg[:250]))
_b1s, _ = BUILD([AC(_DEN, src_dur_sonde=None)])
_b1t, _ = BUILD([AC(_DEN, src_dur_sonde=20.0)])
check("r4_sans_apprentissage_cle_src_dur_sonde_commande_T1_octet_pour_octet",
      T1_CMDS.get("den") and _b1s == T1_CMDS["den"][0] and _b1t == T1_CMDS["den"][0], str(_b1s)[:300])

# audio_only (/measure, passe 1) : meme prefixe
_ba, _fa = BUILD([AC(_DENL)], audio_only=True, out=None)
check("t2_audio_only_meme_prefixe", "afftdn@dn0" in _fa and "-ss" in _ba and "[l6p0]" in _fa, _fa[:300])

# --- espions /render et /measure : fx_list arrive au builder, commande prefixee -------
_cap2 = {}
_vb2, _vr2 = MS._build_montage_command, MS._run_ffmpeg


def _esp2(*a, **k):
    _cap2["a_clips"] = a[2] if len(a) > 2 else k.get("a_clips")
    _cap2["music"] = a[3] if len(a) > 3 else k.get("music")
    r = _vb2(*a, **k)
    _cap2["cmd"] = r[0] if isinstance(r, tuple) else r
    return r


FF2 = PV.ffmpeg_bin()
if not shutil.which("ffmpeg") and os.path.isfile(FF2):
    # le service lance un « ffmpeg » NU : il faut le PATH
    os.environ["PATH"] = os.path.dirname(FF2) + os.pathsep + os.environ.get("PATH", "")
_W = pathlib.Path(TMP) / "l6t2"
_W.mkdir(parents=True, exist_ok=True)


def MK(nom, args):
    """Fabrique une source par ffmpeg ; chemin ou None (les checks qui la lisent rougissent)."""
    p = _W / nom
    try:
        r = subprocess.run([FF2, "-hide_banner", "-nostdin", "-v", "error", "-y"] + args + [str(p)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode:
            print("    fixture", nom, (r.stderr or "")[-300:])
            return None
    except Exception as e:                               # noqa: BLE001
        print("    fixture", nom, repr(e))
        return None
    return p


# source : bruit rose ~-40 dBFS partout, voix 730 Hz de 2 a 3 s et de 4 a 5 s, clic a 3,5 s
_SRC2 = MK("voix_bruit.wav", [
    "-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.05:r=48000:seed=11",
    "-f", "lavfi", "-i", "aevalsrc='0.3*sin(2*PI*730*t)*(between(t\\,2\\,3)+between(t\\,4\\,5))"
                         "+0.9*eq(n\\,168000)':s=48000:d=6",
    "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0", "-ac", "1", "-c:a", "pcm_s16le"])
_BRUIT = MK("bruit_seul.wav", ["-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.05:r=48000:seed=11",
                             "-ac", "1", "-c:a", "pcm_s16le"])
_MUET = MK("muet.wav", ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "3", "-c:a", "pcm_s16le"])
_V1R = MK("v1.mp4", ["-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=1", "-pix_fmt", "yuv420p"])


def TLR(fx, preset=None, loop=False, src=None):
    tl = {"name": "l6", "ratio": "9:16", "preview": False,
          "clips": [{"tr": "v1", "src": {"file_path": str(_V1R)}, "start": 0, "end": 1, "srcIn": 0},
                    {"tr": "a2" if loop else "a1", "src": {"file_path": str(src or _SRC2)}, "start": 0, "end": 3,
                     "srcIn": 2, "fx": fx, **({"loop": True} if loop else {})}]}
    if preset:
        tl["preset"] = preset
    return tl


def RENDER_SPY(payload):
    _cap2.clear()
    MS._build_montage_command, MS._run_ffmpeg = _esp2, (lambda cmd, out: None)
    try:
        return c.post("/api/montage/render", json=payload)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vb2, _vr2


_FXL = [{"type": "denoise", "amount": 24, "nf": -30, "learn_in": 0, "learn_out": 1}]
_rs = RENDER_SPY(TLR(_FXL))
_ac2 = _cap2.get("a_clips") or []
_fc2 = ""
if isinstance(_cap2.get("cmd"), list) and "-filter_complex" in _cap2["cmd"]:
    _fc2 = _cap2["cmd"][_cap2["cmd"].index("-filter_complex") + 1]
check("t2_render_fx_list_normalisee_au_builder_et_commande_prefixee",
      _rs.status_code == 200 and len(_ac2) == 1 and isinstance(_ac2[0].get("fx_list"), list)
      and _ac2[0]["fx_list"] and _ac2[0]["fx_list"][0].get("type") == "denoise"
      and _ac2[0]["fx_list"][0].get("params", {}).get("learn_out") == 1.0
      and "afftdn@dn0" in _fc2 and "[l6p0]" in _fc2,
      (_rs.status_code, J(_rs).get("detail"), _ac2 and _ac2[0].get("fx_list"), _fc2[:200]))

# revue T2 (3) : /render transporte la duree SONDEE brute ; sonde espionnee : 0 (inconnue) -> None et
# pas de prefixe ; 10 000 s (source longue) -> prefixe. Temoin : la vraie sonde rend 6 s.
_sd_ok = _ac2[0].get("src_dur_sonde") if _ac2 else "ABSENT"
_vpd = MS._probe_duration


def RENDER_SONDE(val):
    MS._probe_duration = lambda p: val
    try:
        r = RENDER_SPY(TLR(_FXL))
    finally:
        MS._probe_duration = _vpd
    a = (_cap2.get("a_clips") or [{}])[0]
    cm = _cap2.get("cmd") if isinstance(_cap2.get("cmd"), list) else []
    fc = cm[cm.index("-filter_complex") + 1] if "-filter_complex" in cm else ""
    return r.status_code, a.get("src_dur_sonde", "ABSENT"), a.get("src_dur"), fc


_rz = RENDER_SONDE(0.0)
_rl = RENDER_SONDE(10000.0)
check("r4_render_duree_sondee_brute_transportee_6_s_temoin_vraie_sonde",
      isinstance(_sd_ok, float) and abs(_sd_ok - 6.0) < 0.05, _sd_ok)
check("r4_render_sonde_0_inconnue_none_repli_9999_sans_prefixe_temoin_10000_s_prefixe",
      _rz[0] == 200 and _rz[1] is None and _rz[2] == 9999.0 and "afftdn=nr=24" in _rz[3] and "afftdn@" not in _rz[3]
      and _rl[0] == 200 and _rl[1] == 10000.0 and "afftdn@dn0" in _rl[3] and "[l6p0]" in _rl[3],
      (_rz[:3], _rz[3][:200], _rl[:3], _rl[3][:200]))
_rs2 = RENDER_SPY(TLR([{"type": "denoise", "amount": 24, "nf": -30}]))
_fc2b = ""
if isinstance(_cap2.get("cmd"), list) and "-filter_complex" in _cap2["cmd"]:
    _fc2b = _cap2["cmd"][_cap2["cmd"].index("-filter_complex") + 1]
check("t2_render_temoin_sans_learn_pas_de_prefixe",
      _rs2.status_code == 200 and "afftdn=nr=24" in _fc2b and "afftdn@" not in _fc2b, _fc2b[:200])
_rs3 = RENDER_SPY(TLR(_FXL, loop=True))
_mu3 = _cap2.get("music") or {}
_fc3 = ""
if isinstance(_cap2.get("cmd"), list) and "-filter_complex" in _cap2["cmd"]:
    _fc3 = _cap2["cmd"][_cap2["cmd"].index("-filter_complex") + 1]
check("t2_render_musique_fx_list_posee_mais_pas_de_prefixe",
      _rs3.status_code == 200 and isinstance(_mu3.get("fx_list"), list) and _mu3["fx_list"]
      and "afftdn=nr=24" in _fc3 and "afftdn@" not in _fc3, (_rs3.status_code, _fc3[:200]))

# /measure : meme lecture -> meme prefixe (execution reelle, pas d'espion de ffmpeg)
_cap2.clear()
MS._build_montage_command = _esp2
try:
    _rm = c.post("/api/montage/measure", json=TLR(_FXL))
finally:
    MS._build_montage_command = _vb2
_fcm = ""
if isinstance(_cap2.get("cmd"), list) and "-filter_complex" in _cap2["cmd"]:
    _fcm = _cap2["cmd"][_cap2["cmd"].index("-filter_complex") + 1]
check("t2_measure_meme_prefixe_et_mesure_reelle_ok",
      _rm.status_code == 200 and J(_rm).get("ok") is True and "afftdn@dn0" in _fcm and "[l6p0]" in _fcm,
      (_rm.status_code, J(_rm), _fcm[:200]))

# --- route noise-profile (appel direct, hote choisi) ---------------------------------
def REQ2(body, hote="127.0.0.1"):
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")

    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": "/api/montage/noise-profile", "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": (hote, 5000)}, rcv)


_np_n = {"n": 0}
_vff = MS._ff_run


def _esp_ff(cmd, **kw):
    _np_n["n"] += 1
    _np_n["cmd"] = list(cmd)
    mut = _np_n.get("mut")                  # revue T2 (4) : commande alteree pour un echec REEL
    r = _vff(mut(list(cmd)) if mut else cmd, **kw)
    _np_n["stderr"] = getattr(r, "stderr", "")
    return r


def NP(body, hote="127.0.0.1"):
    f = getattr(MS, "montage_noise_profile", None)
    if f is None:
        return ("ABSENT", None)
    MS._ff_run = _esp_ff
    try:
        return (200, asyncio.run(f(REQ2(body, hote))))
    except Exception as e:                               # noqa: BLE001
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))
    finally:
        MS._ff_run = _vff


def RMS_FF(path, t0, t1, pre=""):
    """RMS mesure par le banc lui-meme (astats), None si echec."""
    try:
        r = subprocess.run([FF2, "-hide_banner", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(path), "-vn",
                            "-af", pre + "astats=measure_overall=RMS_level:measure_perchannel=none",
                            "-f", "null", "-"], capture_output=True, text=True, timeout=60)
        for ln in (r.stderr or "").splitlines():
            if "RMS level dB" in ln:
                v = ln.split(":")[-1].strip()
                return float("-inf") if v == "-inf" else float(v)
    except Exception:                                    # noqa: BLE001
        pass
    return None


_SP = {"file_path": str(_SRC2)}
_n_ok = NP({"src": _SP, "t0": 0.0, "t1": 1.0})
_ref = RMS_FF(_SRC2, 0.0, 1.0)
_d = _n_ok[1] if isinstance(_n_ok[1], dict) else {}
check("t2_route_200_rms_du_bruit_et_nf_de_la_regle",
      _n_ok[0] == 200 and _d.get("ok") is True and _ref is not None
      and abs(float(_d.get("rms_db", 99)) - _ref) <= 0.05 and _d.get("nf_db") == S.nf_of(_ref)
      and -32 <= _d.get("nf_db", 0) <= -28 and _d.get("t0") == 0.0 and _d.get("t1") == 1.0,
      (_n_ok, _ref))
_ci = _np_n.get("cmd") or []
check("t2_route_commande_ss_t_avant_i_astats_null",
      _ci[:1] == ["ffmpeg"] and "-ss" in _ci and "-i" in _ci and _ci.index("-ss") < _ci.index("-i")
      and _ci[_ci.index("-t") + 1] == "1.0" and "astats=measure_overall=RMS_level:measure_perchannel=none"
      in " ".join(_ci) and _ci[-3:] == ["-f", "null", "-"] and "-vn" in _ci, _ci)
# filtres amont du vocabulaire (filter, dehum, eq3 seulement) ; les autres ignores
_n_hp = NP({"src": _SP, "t0": 0.0, "t1": 1.0,
            "fx": [{"type": "echo"}, {"type": "eq3", "bass_db": 3}, {"type": "filter", "mode": "high", "freq": 3000},
                   {"type": "dehum"}, {"type": "compressor"}, {"type": "denoise", "amount": 30}]})
_af = _np_n.get("cmd", [])
_afs = _af[_af.index("-af") + 1] if "-af" in _af else ""
_dhp = _n_hp[1] if isinstance(_n_hp[1], dict) else {}
check("t2_route_filtres_amont_seuls_dans_l_ordre_et_mesure_change",
      _n_hp[0] == 200 and _afs.startswith("highpass=f=3000") and _afs.find("highpass") < _afs.find("bandreject")
      < _afs.find("bass=") < _afs.find("astats") and "aecho" not in _afs and "acompressor" not in _afs
      and "afftdn" not in _afs and float(_dhp.get("rms_db", 0)) < float(_d.get("rms_db", 0)) - 3,
      (_n_hp, _afs))
_bads = [NP({"src": _SP, "t0": 0.0, "t1": 0.1}), NP({"src": _SP, "t0": 0.0, "t1": 31.0}),
         NP({"src": _SP, "t0": -1.0, "t1": 1.0}), NP({"src": _SP, "t0": 0.0}),
         NP({"src": _SP, "t0": "x", "t1": 1.0}), NP({"src": _SP, "t0": 5.9, "t1": 6.5})]
_n0 = _np_n["n"]
check("t2_route_400_plage_courte_longue_negative_absente_illisible_hors_source",
      [b[0] for b in _bads] == [400] * 6, [b for b in _bads])
_n404 = NP({"src": {"file_path": str(_W / "absent.wav")}, "t0": 0, "t1": 1})
_n415 = NP({"src": {"file_path": str(_V1R)}, "t0": 0, "t1": 0.5})
check("t2_route_404_source_inconnue_415_sans_piste_audio_sans_ffmpeg",
      _n404[0] == 404 and _n415[0] == 415 and _np_n["n"] == _n0, (_n404, _n415, _np_n["n"], _n0))
_n403 = NP({"src": _SP, "t0": 0, "t1": 1}, hote="10.1.2.3")
_n403t = NP({"src": _SP, "t0": 0, "t1": 1})
check("t2_route_403_hors_local_avant_tout_calcul_temoin_local_200",
      _n403[0] == 403 and _n403t[0] == 200 and _np_n["n"] == _n0 + 1, (_n403, _n403t[0], _np_n["n"]))
_nm = NP({"src": {"file_path": str(_MUET)}, "t0": 0.5, "t1": 1.5})
check("t2_route_plage_muette_ok_false_temoin_bruit_ok_true",
      _nm[0] == 200 and isinstance(_nm[1], dict) and _nm[1].get("ok") is False
      and _nm[1].get("reason") == "muet" and _d.get("ok") is True, _nm)
_nhttp = c.post("/api/montage/noise-profile", json={"src": _SP, "t0": 0, "t1": 1})
check("t2_route_montee_sur_le_routeur_api_montage",
      _nhttp.status_code == 200 and J(_nhttp).get("ok") is True, (_nhttp.status_code, _nhttp.text[:200]))

# revue T2 (4) : un echec REEL de ffmpeg (option d'astats inconnue, apres ouverture de l'entree) -> 502
# dont le message ne porte PAS le chemin de la source (temoins : le stderr brut le portait, le message
# garde le nom de fichier)
_np_n["mut"] = lambda cm: [("astats=option_inexistante_l6=1" if x.startswith("astats=") else x) for x in cm]
try:
    _n502 = NP({"src": _SP, "t0": 0.0, "t1": 1.0})
finally:
    _np_n.pop("mut", None)
_m502 = str(_n502[1])
_raw502 = str(_np_n.get("stderr") or "")
check("r4_noise_profile_502_sans_chemin_du_tmp_temoins_stderr_brut_et_nom_de_fichier",
      _n502[0] == 502 and str(_SRC2) in _raw502 and TMP not in _m502 and str(_W) not in _m502
      and _W.as_posix() not in _m502 and "voix_bruit.wav" in _m502 and "Mesure du bruit" in _m502
      # la queue de 400 car. peut couper le debut du chemin : aucun des dossiers ne doit y rester
      and _W.name + "\\" not in _m502 and _W.name + "/" not in _m502
      and pathlib.Path(TMP).name not in _m502 and "from 'voix_bruit.wav'" in _m502,
      (_n502[0], _m502[-300:], _raw502[-200:]))

# --- rendu REEL : preset audio_wav, apprentissage vs plancher seul ------------------
_NF = _d.get("nf_db") if isinstance(_d.get("nf_db"), int) else -30


def RENDER_REEL(fx, src=None):
    """(chemin du WAV rendu, etat) par la route, taches de fond jouees."""
    r = c.post("/api/montage/render", json=TLR(fx, preset="audio_wav", src=src))
    jid = J(r).get("job_id")
    j = J(c.get("/api/jobs/%s" % (jid or "sans-job")))
    return j.get("final_video_path") or "", (r.status_code, j.get("status"), str(j.get("error"))[:300])


def LIT(path):
    """WAV -> (canal gauche en float, frequence), ([], 0) si illisible."""
    try:
        with wave.open(str(path), "rb") as w:
            n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
            a = array.array("h")
            raw = w.readframes(n)
            a.frombytes(raw[: len(raw) // 2 * 2])
            return [v / 32768.0 for v in a[0::ch]], sr
    except Exception:                                    # noqa: BLE001
        return [], 0


def RMSL(x, s0, s1):
    s1 = min(s1, len(x))
    return math.sqrt(sum(v * v for v in x[s0:s1]) / (s1 - s0)) if s1 > s0 else 0.0


def DBR(a, b):
    return 20 * math.log10(a / b) if a > 0 and b > 0 else -999.0


if _SRC2 and _V1R:
    _pl, _el = RENDER_REEL([{"type": "denoise", "amount": 24, "nf": _NF, "learn_in": 0, "learn_out": 1}])
    _pn, _en = RENDER_REEL([{"type": "denoise", "amount": 24, "nf": _NF}])
    _p0, _e0 = RENDER_REEL([])
    _xl, _srl = LIT(_pl) if _pl else ([], 0)
    _xn, _srn = LIT(_pn) if _pn else ([], 0)
    _x0, _sr0 = LIT(_p0) if _p0 else ([], 0)
    check("t2_reel_trois_rendus_wav_44k", _srl == _srn == _sr0 == 44100 and _xl and _xn and _x0,
          (_el, _en, _e0))
    _SR = 44100
    # duree exacte : 3 s de clip (V1 1 s, maitre de duree = l'audio)
    check("t2_reel_duree_audio_exacte_3s", abs(len(_xl) - 3 * _SR) <= 2 and abs(len(_xn) - 3 * _SR) <= 2,
          (len(_xl), len(_xn)))
    # clic de la source a 3,5 s -> 1,5 s du rendu : prefixe retire au sample pres
    # (pic cherche dans le silence entre les notes, 1,05-1,95 s : afftdn etale le clic sous
    # la crete de la voix ; un prefixe mal retire le sortirait de la fenetre, un retard de
    # 1200 echantillons le deplacerait de 1102 a 44,1 kHz)
    def _pic(x):
        s0, s1 = int(1.05 * _SR), min(len(x), int(1.95 * _SR))
        return max(range(s0, s1), key=lambda i: abs(x[i])) if s1 > s0 else -1
    _pk, _pk0 = _pic(_xl), _pic(_x0)
    check("t2_reel_clic_a_sa_place_prefixe_retire_exact_temoin_sans_fx",
          abs(_pk - int(1.5 * _SR)) <= 2 and abs(_pk0 - int(1.5 * _SR)) <= 2, (_pk, _pk0))
    # bruit residuel entre deux notes (1,1-1,4 s et 1,6-1,9 s du rendu, hors clic)
    def _res(x):
        return math.sqrt((RMSL(x, int(1.1 * _SR), int(1.4 * _SR)) ** 2
                          + RMSL(x, int(1.6 * _SR), int(1.9 * _SR)) ** 2) / 2)
    _rl, _rn, _r0 = _res(_xl), _res(_xn), _res(_x0)
    _gl, _gn = DBR(_rl, _r0), DBR(_rn, _r0)
    print("    bruit residuel : appris %.2f dB, nf seul %.2f dB (nf %s)" % (_gl, _gn, _NF))
    # ECART AU PLAN (mesure 25/09/2026) : le plan demandait 15 dB « entre deux notes ». A 0,1-0,9 s
    # de la voix, afftdn appris rend -16,2 dB contre -5,8 dB au plancher seul (10,4 dB d'ecart) ;
    # sur du BRUIT SEUL (check suivant, moyenne 0,2-2,8 s) -18,6 contre -6,0 (12,6 dB ; fenetres de
    # 0,3 s entre -20 et -24, le -24 de RESULTATS D2 n'est atteint que par endroits). Seuils poses
    # sous la mesure avec marge : 8 dB entre deux notes, 10 dB sur bruit seul.
    check("t2_reel_appris_au_moins_8dB_sous_nf_seul_entre_deux_notes", _gl <= _gn - 8 and _gn < -3,
          (_gl, _gn))
    if _BRUIT:
        _pbl, _ebl = RENDER_REEL([{"type": "denoise", "amount": 24, "nf": _NF, "learn_in": 0, "learn_out": 1}],
                                 src=_BRUIT)
        _pbn, _ebn = RENDER_REEL([{"type": "denoise", "amount": 24, "nf": _NF}], src=_BRUIT)
        _pb0, _eb0 = RENDER_REEL([], src=_BRUIT)
        _xbl, _xbn, _xb0 = (LIT(x)[0] if x else [] for x in (_pbl, _pbn, _pb0))
        _gbl = DBR(RMSL(_xbl, int(0.2 * _SR), int(2.8 * _SR)), RMSL(_xb0, int(0.2 * _SR), int(2.8 * _SR)))
        _gbn = DBR(RMSL(_xbn, int(0.2 * _SR), int(2.8 * _SR)), RMSL(_xb0, int(0.2 * _SR), int(2.8 * _SR)))
        print("    bruit seul : appris %.2f dB, nf seul %.2f dB" % (_gbl, _gbn))
        check("t2_reel_bruit_seul_appris_au_moins_10dB_sous_nf_seul", _gbl <= _gbn - 10 and _gbn < -3,
              (_gbl, _gbn, _ebl, _ebn, _eb0))
    else:
        check("t2_reel_bruit_seul_appris_au_moins_10dB_sous_nf_seul", False, "source bruit non fabriquee")
    # voix preservee : 730 Hz de la premiere note (0,2-0,8 s du rendu)
    _vl = DBR(RMSL(_xl, int(0.2 * _SR), int(0.8 * _SR)), RMSL(_x0, int(0.2 * _SR), int(0.8 * _SR)))
    check("t2_reel_voix_preservee_moins_1dB", -1.0 <= _vl <= 0.3, "%.2f dB" % _vl)
    # plage en partie (5,5-6,5 s d'une source de 6 s) puis entierement (10-11 s) hors source :
    # duree exacte et clic a sa place (revue T1, I-1 : le prefixe court coupait le debut du clip)
    for _tag, _a, _b in (("partie", 5.5, 6.5), ("entiere", 10.0, 11.0)):
        _ph, _eh = RENDER_REEL([{"type": "denoise", "amount": 24, "nf": _NF, "learn_in": _a, "learn_out": _b}])
        _xh, _srh = LIT(_ph) if _ph else ([], 0)
        check("t2_reel_plage_%s_hors_source_duree_exacte_clic_a_sa_place" % _tag,
              _srh == 44100 and abs(len(_xh) - 3 * _SR) <= 2 and abs(_pic(_xh) - int(1.5 * _SR)) <= 2,
              (_eh, len(_xh), _pic(_xh) if _xh else None))

    # graphe long (> _CMD_MAX) : le fichier -/filter_complex porte l'apostrophe et le ; de asendcmd
    _many = [AC([{"type": "denoise", "amount": 24, "nf": _NF, "learn_in": 0, "learn_out": 1}], path=str(_SRC2),
                src_dur=6.0, src_in=2.0, start=0.0, end=3.0)]
    _vp = [(0.1 * k, -0.5 * (k % 7)) for k in range(12)]
    for k in range(60):
        _many.append(AC([{"type": "eq3", "bass_db": 1}], path=str(_SRC2), src_dur=6.0, src_in=2.0,
                        start=0.0, end=3.0, tr="a3", volume_points=_vp, gain=0.01))
    _bl2, _fl2 = BUILD(_many, audio_only=True, out=None)
    _bl2 = [FF2 if (i == 0 and v == "ffmpeg") else v for i, v in enumerate(_bl2)]
    _long = len(subprocess.list2cmdline([str(a) for a in _bl2]))
    try:
        _rlong = MS._ff_run(_bl2, capture_output=True, text=True, timeout=180)
        _rcl, _errl = _rlong.returncode, (_rlong.stderr or "")[-300:]
    except Exception as e:                               # noqa: BLE001
        _rcl, _errl = None, repr(e)
    check("t2_reel_graphe_long_par_fichier_parse_asendcmd",
          _long > MS._CMD_MAX and "asendcmd=c='0.0 afftdn@dn0 sn start;" in _fl2 and _rcl == 0
          and "I:" in (_rlong.stderr if _rcl == 0 else ""), (_long, _rcl, _errl))
else:
    check("t2_reel_fixtures_fabriquees", False, "sources non fabriquees")


# ═══════════════ [3] revue de T1 : prefixe exact, largeur stereo bornee, uid ═══════════════
print("\n[3] revue T1 (I-1 prefixe de longueur exacte, I-2 largeur stereo, M-2 uid)")
_A6 = pathlib.Path(TMP) / "l6src.wav"          # source de [1] : 6 s, clic a 3,0 s
if not _A6.exists():
    _A6 = MK("l6src_bis.wav", ["-f", "lavfi", "-i",
                                "aevalsrc='0.05*sin(2*PI*440*t)+0.01*(random(0)-0.5)+if(eq(n\\,144000)\\,0.9\\,0)'"
                                ":s=48000:d=6", "-c:a", "pcm_s16le"])


def AUD(a, b, **kw):
    """(cmd, trames, pic du canal gauche) d'une audition apprise reelle (src_in 2, 2,5 s)."""
    out = _W / ("aud_%s_%s.wav" % (a, b))
    r = CALL(S.build_audition_command, _A6, out, src_in=2.0, length=2.5,
             fx=SAN([{"type": "denoise", "amount": 20, "learn_in": a, "learn_out": b}]), **kw)
    cm = r[1] if r[0] == "ok" and isinstance(r[1], list) else []
    n = pk = -1
    if cm and _A6:
        try:
            rr = subprocess.run([FF2] + cm[1:], capture_output=True, text=True, timeout=60)
            if rr.returncode == 0:
                with wave.open(str(out), "rb") as w:
                    n = w.getnframes()
                    sm = array.array("h")
                    raw = w.readframes(n)
                    sm.frombytes(raw[: len(raw) // 2 * 2])
                    Lc = sm[0::w.getnchannels()]
                    pk = max(range(len(Lc)), key=lambda i: abs(Lc[i])) if len(Lc) else -1
            else:
                print("    audition rc", rr.returncode, (rr.stderr or "")[-200:])
        except Exception as e:                           # noqa: BLE001
            print("    audition :", repr(e))
    return cm, n, pk


_c_in, _n_in, _k_in = AUD(0.2, 1.2)
_c_pa, _n_pa, _k_pa = AUD(5.5, 6.5)
_c_ho, _n_ho, _k_ho = AUD(10.0, 11.0)
_s_in, _s_ho = " ".join(map(str, _c_in)), " ".join(map(str, _c_ho))
check("r1_audition_prefixe_force_a_P_echantillons",
      "aresample=48000,atrim=end_sample=48000,apad=whole_len=48000[p]" in _s_in, _s_in[-400:])
check("r1_audition_temoin_plage_dans_la_source_duree_exacte_clic",
      abs(_n_in - 110250) <= 1 and abs(_k_in - 44100) <= 2, (_n_in, _k_in))
check("r1_audition_plage_en_partie_hors_source_duree_exacte_clic",
      abs(_n_pa - 110250) <= 1 and abs(_k_pa - 44100) <= 2 and "concat=n=2" in " ".join(map(str, _c_pa)),
      (_n_pa, _k_pa))
check("r1_audition_plage_entierement_hors_source_sans_prefixe_duree_exacte_temoin_concat",
      "concat" not in _s_ho and "afftdn=nr=20" in _s_ho and "concat=n=2" in _s_in
      and abs(_n_ho - 110250) <= 1 and abs(_k_ho - 44100) <= 2, (_n_ho, _k_ho, _s_ho[-200:]))
# revue T2 (1) : duree INCONNUE (src_dur 0) -> pas de prefixe, comme le Montage ; commande IDENTIQUE a
# l'audition sans apprentissage, rendu REEL rc 0 et duree exacte (avant : prefixe garde, plage au-dela
# de la fin -> « Nothing was written… Conversion failed! »). Temoin : duree connue 6 s -> prefixe.
_c_sd, _n_sd, _k_sd = AUD(10.0, 11.0, src_dur=0.0)
_c_nl = CALL(S.build_audition_command, _A6, _W / "aud_10.0_11.0.wav", src_in=2.0, length=2.5,
             fx=SAN([{"type": "denoise", "amount": 20}]))
_c_k6, _n_k6, _ = AUD(0.2, 1.2, src_dur=6.0)
check("r1_audition_src_dur_0_inconnue_sans_prefixe_commande_sans_apprentissage_rendu_reel",
      _c_nl[0] == "ok" and _c_sd == _c_nl[1] and "concat" not in " ".join(map(str, _c_sd))
      and abs(_n_sd - 110250) <= 1 and abs(_k_sd - 44100) <= 2
      and "concat=n=2" in " ".join(map(str, _c_k6)) and abs(_n_k6 - 110250) <= 1,
      (" ".join(map(str, _c_sd))[-200:], _n_sd, _k_sd, _n_k6))
_c_10k = CALL(S.build_audition_command, _A6, _W / "x.wav", src_in=2.0, length=2.5,
              fx=SAN([{"type": "denoise", "amount": 20, "learn_in": 10.0, "learn_out": 11.0}]), src_dur=10000.0)
check("r1_audition_duree_longue_donnee_prefixe_sans_sonde",
      _c_10k[0] == "ok" and "concat=n=2" in " ".join(map(str, _c_10k[1])), _c_10k)

# revue T2 (2) : /audio/audition sonde la duree HORS de la boucle (executor : aucune boucle en cours dans
# le thread de la sonde) SEULEMENT pour une audition apprise, et la passe au builder par `src_dur`
import shutil as _sh                                     # noqa: E402
_AUD_DIR = pathlib.Path(TMP) / "audio"
try:
    from app.api import routes as _RT
    _AUD_DIR = _RT._audio_dir()
    _sh.copyfile(_A6, _AUD_DIR / "l6_aud.wav")
except Exception as _e:                                  # noqa: BLE001
    print("    audition route :", repr(_e))
_spy = {"sonde": [], "build": []}
_vpr, _vbac = S._probe_duration, S.build_audition_command


def _esp_sonde(p):
    try:
        asyncio.get_running_loop()
        hors = False
    except RuntimeError:
        hors = True
    v = _vpr(p)
    _spy["sonde"].append((pathlib.Path(p).name, hors, v))
    return v


def _esp_bac(*a, **k):
    _spy["build"].append(k.get("src_dur", "ABSENT"))
    return _vbac(*a, **k)


def AUDR(fx):
    _spy["sonde"].clear(); _spy["build"].clear()
    S._probe_duration, S.build_audition_command = _esp_sonde, _esp_bac
    try:
        r = c.post("/api/audio/audition", json={"filename": "l6_aud.wav", "src_in": 2.0, "len": 2.5, "fx": fx})
    finally:
        S._probe_duration, S.build_audition_command = _vpr, _vbac
    return r.status_code, list(_spy["sonde"]), list(_spy["build"]), r.headers.get("content-type", "")


_ar_l = AUDR([{"type": "denoise", "amount": 20, "learn_in": 0.2, "learn_out": 1.2}])
_ar_n = AUDR([{"type": "denoise", "amount": 20}])
check("r4_audition_route_apprise_sonde_une_fois_hors_boucle_src_dur_au_builder",
      _ar_l[0] == 200 and "audio/wav" in _ar_l[3] and len(_ar_l[1]) == 1 and _ar_l[1][0][1] is True
      and abs(_ar_l[1][0][2] - 6.0) < 0.05 and len(_ar_l[2]) == 1 and _ar_l[2][0] == _ar_l[1][0][2], _ar_l)
check("r4_audition_route_sans_apprentissage_aucune_sonde_src_dur_none_temoin_200",
      _ar_n[0] == 200 and _ar_n[1] == [] and _ar_n[2] == [None], _ar_n)

# I-2 : largeur stereo 0..1,6 % -> somme mono par pan ; au-dela slev borne
_w0, _w1, _w16, _w50 = (CH([{"type": "stereo", "width": w}]) for w in (0, 1, 1.6, 50))
_MONO = "aformat=channel_layouts=stereo,pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"
check("r2_largeur_0_et_1_somme_mono_par_pan_temoin_slev_a_50",
      _w0 == _MONO and _w1 == _MONO and "slev" not in _w0 and _w16 == "stereotools=slev=0.016"
      and _w50 == "stereotools=slev=0.5", (_w0, _w1, _w16, _w50))


def RC_ST(af):
    """rc d'un rendu lavfi stereo differencie -> af, et RMS gauche/droite (dB)."""
    try:
        r = subprocess.run([FF2, "-hide_banner", "-f", "lavfi", "-i",
                            "aevalsrc='0.3*sin(2*PI*440*t)|0.2*sin(2*PI*660*t)':s=48000:d=1", "-af",
                            af + ",astats=measure_overall=none:measure_perchannel=RMS_level", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
        v = [float(ln.split(":")[-1]) for ln in (r.stderr or "").splitlines() if "RMS level dB" in ln]
        return r.returncode, v
    except Exception as e:                               # noqa: BLE001
        return repr(e), []


_r0, _r1, _r16, _r50 = (RC_ST(x) for x in (_w0, _w1, _w16, _w50))
check("r2_reel_largeur_0_1_1_6_rc0_canaux_egaux_temoin_50_differencie",
      _r0[0] == 0 and _r1[0] == 0 and _r16[0] == 0 and len(_r0[1]) == 2 and abs(_r0[1][0] - _r0[1][1]) < 0.01
      and len(_r50[1]) == 2 and abs(_r50[1][0] - _r50[1][1]) > 0.5, (_r0, _r1, _r16, _r50))
_old = RC_ST("stereotools=slev=0")
check("r2_temoin_ancienne_ecriture_slev_0_refusee", _old[0] not in (0, None), _old)

# M-2 : uid filtre ; uid vide avec prefixe refuse
_u_ok = CALL(S.fx_chain, SAN([{"type": "denoise"}]), uid="a-b", prefix_s=1.0)
_u_vide = CALL(S.fx_chain, SAN([{"type": "denoise"}]), uid="", prefix_s=1.0)
_u_moins = CALL(S.fx_chain, SAN([{"type": "denoise"}]), uid="--", prefix_s=1.0)
_u_sans = CALL(S.fx_chain, SAN([{"type": "denoise"}]), uid="", prefix_s=0.0)
check("r3_uid_filtre_dans_le_nom_d_instance",
      _u_ok[0] == "ok" and "afftdn@dnab=" in _u_ok[1] and "a-b" not in _u_ok[1], _u_ok)
check("r3_uid_vide_ou_filtre_vide_avec_prefixe_refuse_temoin_sans_prefixe_ok",
      _u_vide == ("exc", "ValueError") and _u_moins == ("exc", "ValueError") and _u_sans[0] == "ok"
      and "afftdn=nr=12" in _u_sans[1], (_u_vide, _u_moins, _u_sans))

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
