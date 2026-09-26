# -*- coding: utf-8 -*-
"""Retours L6 — T1 : ECHO et REVERBE, le « mix » dose la part d'effet, le son
SEC reste a son niveau. En-tete recopie de test_montage_l6.py (env, check, J,
TestClient sans port ouvert ; fin : fermeture des handles puis rmtree) :
dossier de donnees NEUF par execution, toute lecture gardee — un banc qui
meurt sur un acces nu ne dit pas quelles assertions manquent (faute n6 : le
DETAIL est evalue AVANT le court-circuit de la condition, il ne doit donc
jamais lever).
Run : & $PY tests/test_retours_sfx.py   (depuis backend/)
Deux binaires : rejouer avec %LOCALAPPDATA%\\DeepotusVideoGen\\bin en tete du
PATH (`effects_preview.ffmpeg_bin()` prend celui du PATH d'abord).

Diagnostic (26/09) : `aecho=0.9:{mix/100}:…` — `aecho` est un filtre a
PROPAGATION AVANT (mesure a l'impulsion sur 8.1.1 et 9.0.1) :
  sortie = (entree·in_gain + Σ entree(t−d_k)·decay_k) · out_gain
donc out_gain = mix baissait le SEC (mix 22 % → −14,1 dB). Forme retenue :
  aecho=0.25:1:<delais>:<0,25·mix·r_k>,volume=4
- sec = 0,25 × 1 × 4 = 1 EXACT (puissances de deux) ;
- r_k = fb^(k−1) pour l'echo (1re repetition = mix, comme l'audition WebAudio
  du rack : dry 1, ewet = mix, boucle de retour fb) ; r_k = gper^k pour la
  reverbe (prises inchangees) ;
- 0,25 = marge : `aecho` ECRETE a ±1 en INTERNE, meme en flottant (mesure :
  8 echantillons a 1,0 exact sur un bruit rose a −6 dBFS, mix 100, fb 90) ;
  pire somme coherente 1 + 1 + 0,9 + 0,81 = 3,71 < 4 ; `volume=4` rend le
  niveau sans ecreter en flottant (l'aval decide : bus, loudnorm, codeur) ;
- le fragment commence toujours par « aecho » et reste LINEAIRE (virgules).
Changement voulu (26/09) : les rendus qui utilisent echo/reverbe deviennent
plus forts (sec a 0 dB au lieu de −14/−18 dB).
"""
import array, json, math, os, random, re, sys, tempfile, subprocess, pathlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzrsfx_")
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


def SAN(raw):
    """sanitize_fx sans exception."""
    try:
        return S.sanitize_fx(raw)
    except Exception as e:                               # noqa: BLE001
        return [{"type": "EXC", "params": {"e": repr(e)}}]


def CH(raw, **kw):
    """fx_chain(sanitize_fx(raw), **kw) — une exception devient une chaine."""
    try:
        return S.fx_chain(SAN(raw), **kw)
    except Exception as e:                               # noqa: BLE001
        return "EXC " + repr(e)


def AE(frag):
    """Premier `aecho=` du fragment -> (in_gain, out_gain, [delais], [decays],
    gain du `volume=` qui le SUIT immediatement ou 1.0) ; None si illisible."""
    try:
        parts = frag.split(",")
        for i, p in enumerate(parts):
            if p.startswith("aecho="):
                a = p[len("aecho="):].split(":")
                vol = 1.0
                if i + 1 < len(parts) and parts[i + 1].startswith("volume="):
                    vol = float(parts[i + 1][len("volume="):])
                return (float(a[0]), float(a[1]), [float(x) for x in a[2].split("|")],
                        [float(x) for x in a[3].split("|")], vol)
    except Exception:                                    # noqa: BLE001
        return None
    return None


def SEC(ae):
    """Gain du signal sec d'un fragment parse (in·out·volume) ; None sinon."""
    return (ae[0] * ae[1] * ae[4]) if ae else None


# ═══════════════════════ [1] forme des commandes ══════════════════════════════
print("\n[1] forme des commandes (echo, reverbe, autres types inchanges)")

USER_ECHO = [{"type": "echo", "time_ms": 210, "feedback": 35, "mix": 22}]
USER_REV = [{"type": "reverb", "mix": 55, "decay_s": 3.5}]

# anciennes chaines (62f0c75) : le temoin du defaut
ANC_ECHO = "aecho=0.9:0.22:210|420|630:0.35|0.1225|0.0429"
ANC_REV = "aecho=0.9:0.55:150|354|654|1096:0.4925|0.2426|0.1195|0.0588"
check("f0_temoin_ancienne_forme_baissait_le_sec",
      SEC(AE(ANC_ECHO)) is not None and abs(20 * math.log10(SEC(AE(ANC_ECHO))) + 14.07) < 0.05
      and abs(20 * math.log10(SEC(AE(ANC_REV))) + 6.11) < 0.05, str((SEC(AE(ANC_ECHO)), SEC(AE(ANC_REV)))))

_ue, _ur = CH(USER_ECHO), CH(USER_REV)
check("f1_echo_du_projet_forme_exacte",
      _ue == "aecho=0.25:1:210|420|630:0.055|0.0192|0.0067,volume=4", _ue)
check("f2_reverbe_du_projet_forme_exacte",
      _ur == "aecho=0.25:1:150|354|654|1096:0.0677|0.0334|0.0164|0.0081,volume=4", _ur)

# sec = 1 EXACT pour tout mix (22/55/100, et quelques autres) ; gains dans les bornes d'aecho
_sec = {}
for typ, base in (("echo", {"time_ms": 300, "feedback": 30}), ("reverb", {"decay_s": 2})):
    for mix in (1, 22, 55, 100):
        _sec[(typ, mix)] = AE(CH([dict(base, type=typ, mix=mix)]))
check("f3_sec_exactement_1_pour_tout_mix",
      all(a is not None and SEC(a) == 1.0 for a in _sec.values()), str(_sec))
check("f4_gains_dans_les_bornes_aecho",
      all(a is not None and 0 < a[0] <= 1 and 0 < a[1] <= 1 and all(0 < d <= 1 for d in a[3])
          for a in _sec.values()), str(_sec))
check("f5_marge_interne_somme_coherente_sous_1",
      all(a is not None and a[0] + sum(a[3]) <= 1.0 for a in _sec.values())
      and all(a is not None for a in (AE(CH([{"type": "echo", "mix": 100, "feedback": 90}])),
                                      AE(CH([{"type": "reverb", "mix": 100, "decay_s": 8}]))))
      and AE(CH([{"type": "echo", "mix": 100, "feedback": 90}]))[0]
      + sum(AE(CH([{"type": "echo", "mix": 100, "feedback": 90}]))[3]) <= 1.0
      and AE(CH([{"type": "reverb", "mix": 100, "decay_s": 8}]))[0]
      + sum(AE(CH([{"type": "reverb", "mix": 100, "decay_s": 8}]))[3]) <= 1.0,
      str((CH([{"type": "echo", "mix": 100, "feedback": 90}]), CH([{"type": "reverb", "mix": 100, "decay_s": 8}]))))


def WET(a):
    """Part d'effet relative au sec (Σ decays / in_gain) ; None sinon."""
    return (sum(a[3]) / a[0]) if a else None


_we = [WET(_sec[("echo", m)]) for m in (1, 22, 55, 100)]
_wr = [WET(_sec[("reverb", m)]) for m in (1, 22, 55, 100)]
check("f6_part_d_effet_strictement_croissante_avec_mix",
      None not in _we + _wr and _we == sorted(_we) and len(set(_we)) == 4
      and _wr == sorted(_wr) and len(set(_wr)) == 4, str((_we, _wr)))
# loi de l'audition WebAudio : ewet = mix/100 -> part d'effet PROPORTIONNELLE a mix
check("f7_part_d_effet_proportionnelle_au_mix_comme_ewet",
      None not in _we + _wr and abs(_we[3] / _we[1] - 100 / 22) < 0.02 * 100 / 22
      and abs(_wr[3] / _wr[2] - 100 / 55) < 0.02 * 100 / 55, str((_we, _wr)))
# echo : 1re repetition = mix (WebAudio : dl -> ewet), puis ×fb (boucle fb)
_e = AE(CH([{"type": "echo", "time_ms": 300, "feedback": 40, "mix": 50}]))
check("f8_echo_repetitions_mix_puis_fois_fb",
      _e is not None and _e[2] == [300.0, 600.0, 900.0]
      and abs(_e[3][0] / _e[0] - 0.5) < 1e-3 and abs(_e[3][1] / _e[3][0] - 0.4) < 2e-3
      and abs(_e[3][2] / _e[3][1] - 0.4) < 5e-3, str(_e))
_e0 = AE(CH([{"type": "echo", "time_ms": 300, "feedback": 0, "mix": 50}]))
check("f9_echo_feedback_0_une_seule_repetition_a_mix_temoin_fb_40",
      _e0 is not None and _e0[2] == [300.0] and abs(_e0[3][0] / _e0[0] - 0.5) < 1e-3
      and _e is not None and len(_e[2]) == 3, str((_e0, _e)))

# identite a mix < 0,5 (les deux types), temoin a mix 1
check("f10_identite_mix_0_et_0_4_temoin_mix_1",
      CH([{"type": "echo", "mix": 0}]) == "" and CH([{"type": "echo", "mix": 0.4}]) == ""
      and CH([{"type": "reverb", "mix": 0}]) == "" and CH([{"type": "reverb", "mix": 0.4}]) == ""
      and CH([{"type": "echo", "mix": 1}]).startswith("aecho=")
      and CH([{"type": "reverb", "mix": 1}]).startswith("aecho="),
      str((CH([{"type": "echo", "mix": 0}]), CH([{"type": "reverb", "mix": 0}]), CH([{"type": "echo", "mix": 1}]))))

# lineaire : aucune etiquette, aucun asplit, aucun ';' — le fragment s'insere dans une chaine a virgules
_frags = [CH([dict(type=t, mix=m)]) for t in ("echo", "reverb") for m in (1, 22, 100)]
check("f11_fragments_lineaires_commencent_par_aecho",
      all(f.startswith("aecho=") and ";" not in f and "[" not in f and "asplit" not in f
          and f.count("aecho=") == 1 for f in _frags), str(_frags))
# decays jamais « 0 » apres arrondi (aecho REFUSE decay <= 0)
_tiny = CH([{"type": "echo", "mix": 0.5, "feedback": 1}])
check("f12_decay_minuscule_jamais_zero", AE(_tiny) is not None and min(AE(_tiny)[3]) > 0, _tiny)

# autres types : chaines de 62f0c75 recopiees EN DUR ; et la chaine complete garde l'ordre
AUTRES = [
    ([{"type": "filter", "mode": "high", "freq": 300, "q": 0.7}], "highpass=f=300:width_type=q:w=0.7"),
    ([{"type": "eq3", "bass_db": -4, "treble_db": 2}], "bass=g=-4:f=110,treble=g=2:f=8000"),
    ([{"type": "distortion", "drive": 30}], "volume=6.7,asoftclip=type=atan"),
    ([{"type": "stereo", "pan": -40, "width": 130}],
     "stereowiden=delay=15:feedback=0.275:crossfeed=0.255:drymix=0.85,"
     "aformat=channel_layouts=stereo,pan=stereo|c0=1*c0|c1=0.642*c1"),
    ([{"type": "compressor"}], "acompressor=threshold=0.1:ratio=4:attack=50:release=250"),
    ([{"type": "denoise", "amount": 20, "nf": -50}],
     "aresample=48000,apad=pad_len=1200,afftdn=nr=20:nf=-50,atrim=start_sample=1200,"
     "asetpts=PTS-STARTPTS,asetnsamples=n=4096:p=0"),
    ([{"type": "deesser", "intensity": 40}], "deesser=i=0.4"),
    ([{"type": "normalize", "target_lufs": -14}], "loudnorm=I=-14:TP=-1.5:LRA=11"),
    ([{"type": "eq6", "p2_g": 3, "hs_g": -2}],
     "aformat=sample_fmts=fltp,equalizer=f=800:t=q:w=1:g=3,highshelf=f=8000:g=-2"),
    ([{"type": "dehum", "base": 60, "harmonics": 2}],
     "bandreject=f=60:width_type=q:w=10:m=1,bandreject=f=120:width_type=q:w=10:m=1"),
]
_diff = [(l, CH(l), e) for l, e in AUTRES if CH(l) != e]
check("f13_autres_types_inchanges_62f0c75", len(AUTRES) == 10 and not _diff, str(_diff))
_tout = CH([{"type": "stereo", "width": 150}] + USER_REV + [{"type": "distortion", "drive": 30}] + USER_ECHO)
check("f14_ordre_distortion_echo_reverbe_stereo_tenu",
      0 <= _tout.find("asoftclip") < _tout.find("aecho=0.25:1:210") < _tout.find("aecho=0.25:1:150")
      < _tout.find("stereowiden"), _tout)


# ═══════════════════════ [2] mesures reelles ═════════════════════════════════
print("\n[2] mesures reelles (sec, part d'effet, crete, audition WebAudio)")
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

    def ROSE(n, seed=1, crete_db=-6.0):
        """Bruit rose (filtre de Kellet) deterministe, crete a `crete_db` dBFS."""
        rnd = random.Random(seed)
        b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
        out = []
        for _ in range(n):
            w = rnd.uniform(-1, 1)
            b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759
            b2 = 0.96900 * b2 + w * 0.1538520; b3 = 0.86650 * b3 + w * 0.3104856
            b4 = 0.55000 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.0168980
            out.append(b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362); b6 = w * 0.115926
        g = 10 ** (crete_db / 20) / max(abs(x) for x in out)
        return array.array("f", (x * g for x in out))

    def REND(sig, af):
        """f32le mono -> af -> f32le mono ; array vide si echec."""
        try:
            r = subprocess.run([FF, "-hide_banner", "-nostdin", "-v", "error", "-f", "f32le", "-ar", str(SR),
                                "-ac", "1", "-i", "-", "-af", af, "-f", "f32le", "-c:a", "pcm_f32le",
                                "-ar", str(SR), "-ac", "1", "-"],
                               input=sig.tobytes(), capture_output=True, timeout=120)
            if r.returncode:
                print("   (ffmpeg :", r.stderr.decode("utf-8", "replace")[-200:], ")")
                return array.array("f")
            a = array.array("f"); a.frombytes(r.stdout)
            return a
        except Exception as e:                           # noqa: BLE001
            print("   (REND :", e, ")")
            return array.array("f")

    def RMS(a, s, e):
        seg = a[s:e]
        return math.sqrt(sum(x * x for x in seg) / len(seg)) if len(seg) else 0.0

    def DB(x):
        return 20 * math.log10(x) if x and x > 0 else -999.0

    # --- rafale de 80 ms puis silence : le SEC se lit AVANT la 1re prise (>= 150 ms) --------
    NB = int(0.080 * SR)
    RAF = ROSE(NB, seed=7) + array.array("f", [0.0] * (2 * SR))
    R_IN = RMS(RAF, 0, NB)
    E_IN = sum(x * x for x in RAF[:NB])

    def SEC_DB(af):
        o = REND(RAF, af)
        return (DB(RMS(o, 0, NB)) - DB(R_IN)) if len(o) >= NB else None

    def EFFET_DB(af):
        """Energie de la QUEUE (apres la rafale) relative a l'energie de la rafale d'entree."""
        o = REND(RAF, af)
        if len(o) < NB + SR:
            return None
        return 10 * math.log10(max(1e-30, sum(x * x for x in o[NB:])) / E_IN)

    _sec_anc = SEC_DB(ANC_ECHO)
    _sec_anc2 = SEC_DB(ANC_ECHO + "," + ANC_REV)
    check("m0_temoin_ancienne_forme_sec_mesure_moins_14_et_moins_20",
          _sec_anc is not None and _sec_anc2 is not None and abs(_sec_anc + 14.07) < 0.3
          and abs(_sec_anc2 + 20.17) < 0.3, str((_sec_anc, _sec_anc2)))
    _mes = {}
    for typ, base in (("echo", {"time_ms": 210, "feedback": 35}), ("reverb", {"decay_s": 3.5})):
        for mix in (22, 55, 100):
            _mes[(typ, mix)] = SEC_DB(CH([dict(base, type=typ, mix=mix)]))
    check("m1_sec_preserve_0_5_db_mix_22_55_100_echo_et_reverbe",
          all(v is not None and abs(v) <= 0.5 for v in _mes.values()),
          str({k: (round(v, 3) if v is not None else None) for k, v in _mes.items()}))
    _proj = SEC_DB(CH(USER_ECHO + USER_REV))
    check("m2_sec_du_projet_echo_plus_reverbe_preserve", _proj is not None and abs(_proj) <= 0.5, str(_proj))

    _eff = {}
    for typ, base in (("echo", {"time_ms": 210, "feedback": 35}), ("reverb", {"decay_s": 3.5})):
        _eff[typ] = [EFFET_DB(CH([dict(base, type=typ, mix=m)])) for m in (22, 55, 100)]
    check("m3_part_d_effet_mesuree_strictement_croissante",
          all(None not in v and v[0] < v[1] < v[2] for v in _eff.values()), str(_eff))
    # loi WebAudio (ewet = mix/100) : 100 vs 22 -> +13,15 dB d'energie de queue
    check("m4_part_d_effet_proportionnelle_au_mix_mesuree",
          all(None not in v and abs((v[2] - v[0]) - 20 * math.log10(100 / 22)) < 0.3 for v in _eff.values()),
          str({k: (v[2] - v[0]) if None not in v else None for k, v in _eff.items()}))
    _eff_anc = EFFET_DB(ANC_ECHO)
    check("m5_effet_du_projet_plus_fort_qu_avant_temoin",
          _eff_anc is not None and _eff["echo"][0] is not None and _eff["echo"][0] > _eff_anc + 6,
          str((_eff_anc, _eff["echo"][0])))

    # --- impulsion : reponse de l'echo == modele WebAudio (dry 1, mix, mix·fb, mix·fb²) ------
    IMP = array.array("f", [0.0] * SR); IMP[100] = 0.5
    _ir = REND(IMP, CH(USER_ECHO))
    _taps = [(_ir[100 + int(round(k * 0.210 * SR))] / 0.5) if len(_ir) > 100 + int(0.63 * SR) else None
             for k in range(4)]
    _web = [1.0, 0.22, 0.22 * 0.35, 0.22 * 0.35 ** 2]
    check("m6_reponse_impulsionnelle_echo_egale_audition_webaudio_trois_prises",
          None not in _taps and all(abs(a - b) <= 0.005 * max(b, 0.01) + 2e-4 for a, b in zip(_taps, _web)),
          str((_taps, _web)))

    # --- crete sur bruit rose continu a -6 dBFS ------------------------------------------------
    ROSEC = ROSE(3 * SR, seed=3)
    P_IN = max(abs(x) for x in ROSEC)

    def CRETE(af):
        o = REND(ROSEC, af)
        return (DB(max(abs(x) for x in o)) - DB(P_IN), sum(1 for x in o if abs(x) == 1.0)) if len(o) else None

    _cr = {"projet": CRETE(CH(USER_ECHO + USER_REV)), "defauts_echo": CRETE(CH([{"type": "echo"}])),
           "defauts_reverbe": CRETE(CH([{"type": "reverb"}]))}
    check("m7_crete_au_plus_entree_plus_6_db_projet_et_defauts",
          all(v is not None and v[0] <= 6.0 for v in _cr.values()), str(_cr))
    _ext = CRETE(CH([{"type": "echo", "mix": 100, "feedback": 90, "time_ms": 20}]))
    _ext_sans_marge = CRETE("aecho=1:1:20|40|60:1|0.9|0.81")
    # temoin : sans marge, aecho ecrete EN INTERNE (echantillons a 1,0 exact) ; avec la marge, aucun
    check("m8_aucun_ecretage_interne_au_coin_extreme_temoin_sans_marge",
          _ext is not None and _ext_sans_marge is not None and _ext[1] == 0 and _ext_sans_marge[1] > 0
          and _ext[0] > _ext_sans_marge[0], str((_ext, _ext_sans_marge)))
    print("   crete (dB au-dessus de l'entree, echantillons a 1,0) :", _cr, "extreme :", _ext)

    # --- reverbe vs audition WebAudio (convolueur NORMALISE, spec Web Audio) : ecart DIT --------
    for dec in (2.0, 3.5, 8.0):
        n = int(SR * dec)
        web = 20 * math.log10(0.00125 * 44100 / SR * math.sqrt(n))       # gain efficace de la queue a mix 100
        a = AE(CH([{"type": "reverb", "mix": 100, "decay_s": dec}]))
        nous = 10 * math.log10(sum((d / a[0]) ** 2 for d in a[3])) if a else None
        print(f"   reverbe decay {dec} s, mix 100 : queue WebAudio {web:+.1f} dB, nous {nous:+.1f} dB"
              if nous is not None else "   reverbe illisible")

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
