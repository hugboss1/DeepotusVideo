# -*- coding: utf-8 -*-
"""Retours L6, T2 — LA MUSIQUE D'UNE PISTE EN BOUCLE RESPECTE LES BORNES DE
SON CLIP. En-tete recopie de test_montage_l4.py (env, check, J, A, FLAT) :
dossier de donnees NEUF par execution, TestClient sans port ouvert, toute
lecture gardee — un banc qui meurt sur un acces nu ne dit pas quelles
assertions manquent.
Run : & $PY tests/test_retours_musique.py   (depuis backend/)
Rejoue sur l'autre binaire : PATH=C:\\Users\\olivi\\AppData\\Local\\DeepotusVideoGen\\bin;$PATH

DIAGNOSTIC (26/09/2026, plan 2026-09-26-plan-montage-retours-L6.md) : /render
ne transmettait a la musique ni `start`, ni `end`, ni `srcIn` — elle jouait de
0 jusqu'a la fin du rendu en `-stream_loop -1` quel que soit son clip (11,1 s
affichees, 53,6 s jouees). Meme lecture dans /measure.

FORME RETENUE (mesuree le 26/09/2026 sur 8.1.1 et 9.0.1, scratchpad
t2/mesure_boucle.py, source de 4 s dont le niveau dit la seconde) :
- entree `-stream_loop -1` GARDEE (boucle de la SOURCE) ; `atrim=src_in:src_in+D`
  sur le flux boucle : lu depuis src_in, la boucle repart du DEBUT de la source
  (niveaux 2,3,4,1,2,3,4,1 pour src_in 1). `-ss src_in` en entree donne la MEME
  reprise a 0 sur les deux binaires : atrim est garde (precis a l'echantillon,
  dans le graphe comme les clips a1/a3) ;
- `asetpts`, vitesse + rack, fondus cales sur la duree du CLIP (plus sur le
  total du rendu), gain, `adelay=start`, puis l'automation `volume_points` en
  temps GLOBAL : APRES adelay, `t` est l'horloge du rendu (mesure : volume
  if(lt(t,3)) apres adelay 2000 coupe exactement 0-3 s globales) — les points
  envoyes par l'UI restent tels quels ;
- `apad=whole_dur=total` en queue : le flux musique dure encore tout le rendu
  (silence apres le clip) — la chaine laterale du ducking et l'invariant
  « audio aussi long que la video avec musique » (test_montage_pistes_rendu)
  tiennent.
Le dict `music` porte `bornes = {start, end, src_in}` et `src_dur_sonde` ;
SANS `bornes` (dicts des bancs anterieurs, qui passent un clip a1 complet
comme musique — test_montage_l6 `den_learn_music`) la commande reste
l'historique OCTET POUR OCTET. ECART AU PLAN (dit) : le plan ecrit « le dict
music porte start, end, src_in » ; a plat, ces cles existent DEJA dans les dicts
des bancs l6 et auraient change leur commande pinnee — elles sont donc
regroupees sous `bornes`.
Vitesse : la source est coupee a D x vitesse puis atempo → le clip dure D sur
la timeline (borne tenue ; les clips a1/a3 gardent leur convention d/vitesse).
PLUSIEURS CLIPS sur la piste en boucle : /render classe le PREMIER (ordre du
payload) en musique, les suivants en bruitages a3 (poses, non boucles, non
duckes) — inchange, seul le premier change.

ETAT VIDE : avant l'implementation `bornes` est ignore → la musique joue de 0
au total : les checks de silence ROUGISSENT (chacun precede de son temoin de
presence dans la MEME expression), rien ne meurt.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil, array, math
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzrm_")
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
from app.services import effects_preview as PV           # noqa: E402


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


# ── binaire : celui du PATH (le service lance un « ffmpeg » NU) ───────────
FF = shutil.which("ffmpeg") or PV.ffmpeg_bin()
_ver = ""
try:
    _ver = subprocess.run([FF, "-version"], capture_output=True, text=True, timeout=30).stdout.split("\n")[0]
except Exception as e:                                   # noqa: BLE001
    _ver = repr(e)
print("ffmpeg :", FF, "|", _ver[:60])


# ── fabriques de dicts (formes RECOPIEES de /render) ──────────────────────
def V1SPEC(path="V1.mp4", dur=20.0):
    return {"path": path, "src_dur": dur, "src_in": 0.0, "start": 0.0, "end": dur,
            "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}


def ASPEC(path="VOX.wav", dur=3.0, **kw):
    d = {"tr": "a1", "path": path, "src_dur": dur, "src_in": 0.0, "start": 0.0, "end": dur,
         "gain": 1.0, "fade_in": 0, "fade_out": 0, "fade_in_curve": None, "fade_out_curve": None,
         "fx_chain": "", "speed": 0.0, "volume_points": None}
    d.update(kw)
    return d


def MSPEC(path="MUS.wav", bornes=None, **kw):
    d = {"path": path, "gain": 0.5, "fade_in": 0.5, "fade_out": 2.0, "fade_in_curve": None,
         "fade_out_curve": None, "fx_chain": "", "fx_list": [], "speed": 0.0,
         "volume_points": [(0.0, -6.0), (4.0, 0.0)]}
    d.update(kw)
    if bornes is not None:
        d["bornes"] = bornes
    return d


KW = dict(w=64, h=64, fps=30, mix_db={}, ducking=True, duration_master=True, preview=False, out="OUT.mp4")


def BUILD(a_clips, music, **kw):
    a = dict(KW); a.update(kw)
    try:
        cmd, total = MS._build_montage_command([V1SPEC(**a.pop("_v1", {}))], [], a_clips, music, **a)
    except Exception as e:                               # faute n°6 : rougir, pas mourir
        return ["EXC", "%s: %s" % (type(e).__name__, e)], -1
    return cmd, total


def FC(cmd):
    return cmd[cmd.index("-filter_complex") + 1] if isinstance(cmd, list) and "-filter_complex" in cmd else ""


# ═══════════════ [1] commandes : historique pinne, bornes ═══════════════
print("\n[1] commande : historique octet pour octet sans bornes, chaine bornee avec")
# Constantes de 62f0c75 (capturees AVANT l'implementation, sortie brute du builder).
_SANS = ("ffmpeg -y -t 20.0 -i V1.mp4 -i VOX.wav -filter_complex [0:v]scale=64:64:force_original_aspect_ratio="
         "increase,crop=64:64,setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=20.0,trim=0:20.0,"
         "setpts=PTS-STARTPTS[n0];[1:a]atrim=0.0:3.0,asetpts=PTS-STARTPTS,aresample=async=1,aformat=sample_rates="
         "44100:channel_layouts=stereo,volume=1.0,adelay=0|0[va0];[va0]anull[vall];[vall]aresample=async=1[outa];"
         "[n0]format=yuv420p[outv] -map [outv] -map [outa] -t 20.0 -c:v libx264 -profile:v high -level 4.0 "
         "-preset medium -crf 20 -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -movflags +faststart OUT.mp4")
_HIST = ("ffmpeg -y -t 20.0 -i V1.mp4 -i VOX.wav -stream_loop -1 -i MUS.wav -filter_complex [0:v]scale=64:64:"
         "force_original_aspect_ratio=increase,crop=64:64,setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:"
         "stop_duration=20.0,trim=0:20.0,setpts=PTS-STARTPTS[n0];[1:a]atrim=0.0:3.0,asetpts=PTS-STARTPTS,"
         "aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0,adelay=0|0[va0];"
         "[2:a]afade=t=in:st=0:d=0.5,afade=t=out:st=18.0:d=2.0,volume='pow(10,(if(lt(t,0),-6,if(lt(t,4),"
         "-6+(6)*(t-0)/4,0)))/20)':eval=frame,aresample=async=1,aformat=sample_rates=44100:channel_layouts="
         "stereo,volume=0.5[mtrk];[va0]anull[vall];[vall]asplit=2[vsc0][vmix];[vsc0]apad=whole_dur=20.0[vsc];"
         "[mtrk][vsc]sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400[mduck];[vmix][mduck]amix="
         "inputs=2:duration=longest:normalize=0,aresample=async=1[outa];[n0]format=yuv420p[outv] -map [outv] "
         "-map [outa] -t 20.0 -c:v libx264 -profile:v high -level 4.0 -preset medium -crf 20 -pix_fmt yuv420p "
         "-r 30 -c:a aac -b:a 192k -movflags +faststart OUT.mp4")
_c_sans, _ = BUILD([ASPEC()], None)
check("h_sans_musique_commande_de_62f0c75", FLAT(_c_sans) == _SANS, FLAT(_c_sans)[:300])
_c_hist, _ = BUILD([ASPEC()], MSPEC())
check("h_musique_sans_bornes_commande_de_62f0c75", FLAT(_c_hist) == _HIST, FLAT(_c_hist)[:300])
# un dict « clip a1 complet » passe comme musique (forme des bancs l6) : start/end/src_in A PLAT
# n'y changent rien — seul `bornes` borne.
_c_plat, _ = BUILD([ASPEC()], MSPEC(start=5.0, end=15.0, src_in=1.0))
check("h_cles_a_plat_ignorees_seul_bornes_borne", FLAT(_c_plat) == _HIST, FLAT(_c_plat)[:300])

_B = {"start": 5.0, "end": 15.0, "src_in": 1.0}
_cb, _tb = BUILD([ASPEC()], MSPEC(bornes=_B, src_dur_sonde=4.0))
_fb = FC(_cb)
_mt = next((p for p in _fb.split(";") if p.endswith("[mtrk]")), "")
_attendu = ("[2:a]atrim=1.0:11.0,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.5,afade=t=out:st=8.0:d=2.0,"
            "aresample=async=1,aformat=sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=5000|5000,"
            "volume='pow(10,(if(lt(t,0),-6,if(lt(t,4),-6+(6)*(t-0)/4,0)))/20)':eval=frame,"
            "apad=whole_dur=20.0[mtrk]")
check("b_chaine_bornee_exacte", _mt == _attendu, "\n      recu    %s\n      attendu %s" % (_mt, _attendu))
check("b_boucle_de_la_source_gardee", "-stream_loop -1 -i MUS.wav" in FLAT(_cb), FLAT(_cb)[:200])
check("b_ducking_inchange_avec_bornes",
      "[mtrk][vsc]sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400[mduck]" in _fb
      and "[vsc0]apad=whole_dur=20.0[vsc]" in _fb, _fb[-400:])
# le reste du graphe (hors maillon musique) est celui de l'historique
_reste_b = ";".join(p for p in _fb.split(";") if not p.endswith("[mtrk]"))
_reste_h = ";".join(p for p in FC(_c_hist).split(";") if not p.endswith("[mtrk]"))
check("b_seul_le_maillon_musique_change", bool(_reste_h) and _reste_b == _reste_h, _reste_b[:200])

# fondus : bornes au clip (fondu d'entree plus long que le clip → borne a D)
_cf, _ = BUILD([], MSPEC(bornes={"start": 0.0, "end": 1.5, "src_in": 0.0}, fade_in=3.0, fade_out=3.0,
                         volume_points=None))
_mf = next((p for p in FC(_cf).split(";") if p.endswith("[mtrk]")), "")
check("b_fondus_bornes_a_la_duree_du_clip",
      "atrim=0.0:1.5," in _mf and "afade=t=in:st=0:d=1.5" in _mf and "afade=t=out:st=0.0:d=1.5" in _mf, _mf)
# vitesse : la source est coupee a D x vitesse, atempo rend D
_cs, _ = BUILD([], MSPEC(bornes={"start": 2.0, "end": 10.0, "src_in": 0.5}, speed=2.0, volume_points=None,
                         fade_in=0, fade_out=0))
_ms = next((p for p in FC(_cs).split(";") if p.endswith("[mtrk]")), "")
check("b_vitesse_source_coupee_a_D_fois_vitesse",
      _ms.startswith("[1:a]atrim=0.5:16.5,asetpts=PTS-STARTPTS,atempo=2,") and "adelay=2000|2000" in _ms, _ms)
# src_in au-dela de la source : ramene modulo la duree sondee (la boucle le ferait, sans decoder N tours)
_cm, _ = BUILD([], MSPEC(bornes={"start": 0.0, "end": 2.0, "src_in": 9.0}, src_dur_sonde=4.0,
                         volume_points=None, fade_in=0, fade_out=0))
_mm = next((p for p in FC(_cm).split(";") if p.endswith("[mtrk]")), "")
check("b_src_in_modulo_la_duree_sondee", "atrim=1.0:3.0," in _mm, _mm)
# bornes degenerees (end <= start) : historique (jamais un atrim vide), temoin : bornes saines bornent
_cd, _ = BUILD([ASPEC()], MSPEC(bornes={"start": 5.0, "end": 5.0, "src_in": 0.0}))
check("b_bornes_degenerees_historique_temoin_bornees",
      "adelay=5000|5000" in _fb and FLAT(_cd) == _HIST, FLAT(_cd)[:200])


# ═══════════════ [2] mesure reelle ═══════════════
print("\n[2] rendu reel (audio_only → f32 mono 8 kHz), binaire :", _ver[:40])
V1 = os.path.join(TMP, "v1.mp4")
MUSC = os.path.join(TMP, "mus_const.wav")        # sinus 440 Hz constant, 4 s
MUSM = os.path.join(TMP, "mus_marq.wav")         # niveau = seconde de source + 1 (0,1 .. 0,4)
VOX = os.path.join(TMP, "vox.wav")               # 3000 Hz fort, 0-3 s
_gen = [
    [FF, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30:d=20", "-pix_fmt", "yuv420p", V1],
    [FF, "-v", "error", "-y", "-f", "lavfi", "-i", "aevalsrc=0.3*sin(2*PI*440*t):s=44100:d=4", MUSC],
    [FF, "-v", "error", "-y", "-f", "lavfi", "-i", "aevalsrc=0.1*(floor(t)+1)*sin(2*PI*440*t):s=44100:d=4", MUSM],
    [FF, "-v", "error", "-y", "-f", "lavfi", "-i", "aevalsrc=0.5*sin(2*PI*3000*t):s=44100:d=3", VOX],
]
_gok = all(subprocess.run(g, capture_output=True, timeout=60).returncode == 0 for g in _gen)
check("r_sources_generees", _gok)

SR = 8000


def RUN(a_clips, music, ducking=False):
    """Commande audio_only du builder, sortie f32 mono 8 kHz → array (ou message)."""
    a = dict(KW); a.update(ducking=ducking, out=None, audio_only=True)
    try:
        cmd, total = MS._build_montage_command([V1SPEC(V1)], [], a_clips, music, **a)
    except Exception as e:                               # noqa: BLE001
        return "EXC %r" % e, ""
    cmd = list(cmd)
    cmd[0] = FF
    j = len(cmd) - 3                                     # « -f null - » en queue
    if cmd[j:] != ["-f", "null", "-"]:
        return "queue inattendue %r" % cmd[-4:], FC(cmd)
    cmd = cmd[:j] + ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if r.returncode:
        return "rc %d %s" % (r.returncode, r.stderr[-300:]), FC(cmd)
    x = array.array("f"); x.frombytes(r.stdout[: len(r.stdout) // 4 * 4])
    return x, FC(cmd)


def rms_db(x, t0, t1):
    if not isinstance(x, array.array):
        return None
    s = x[int(t0 * SR):int(t1 * SR)]
    if not len(s):
        return None
    e = sum(v * v for v in s) / len(s)
    return round(10 * math.log10(e), 2) if e > 0 else -200.0


def goertzel_db(x, t0, t1, f):
    """energie a la frequence f sur la fenetre (dB relatifs) — bande de la musique."""
    if not isinstance(x, array.array):
        return None
    s = x[int(t0 * SR):int(t1 * SR)]
    if not len(s):
        return None
    k = 2 * math.cos(2 * math.pi * f / SR)
    q1 = q2 = 0.0
    for v in s:
        q1, q2 = v + k * q1 - q2, q1
    p = q1 * q1 + q2 * q2 - k * q1 * q2
    return round(10 * math.log10(p / len(s) ** 2), 2) if p > 0 else -200.0


def pic(x, t0, t1):
    if not isinstance(x, array.array):
        return None
    s = x[int(t0 * SR):int(t1 * SR)]
    return round(max((abs(v) for v in s), default=0.0) * 10, 1)


def M(path, bornes, **kw):
    d = MSPEC(path=path, bornes=bornes, gain=1.0, fade_in=0, fade_out=0, volume_points=None,
              src_dur_sonde=4.0)
    d.update(kw)
    return d


if _gok:
    # A. clip 0–11,1 : presente 0–11, silence de 12 s a la fin
    xa, fa = RUN([], M(MUSC, {"start": 0.0, "end": 11.1, "src_in": 0.0}))
    pa = [rms_db(xa, k + 0.2, k + 0.8) for k in range(11)]
    sa = rms_db(xa, 12.0, 20.0)
    check("rA_presente_sur_tout_le_clip_puis_silence_apres_12s",
          all(v is not None and v > -20 for v in pa) and sa is not None and sa < -80, (pa, sa, str(xa)[:200]))
    check("rA_flux_aussi_long_que_le_rendu",
          isinstance(xa, array.array) and abs(len(xa) / SR - 20.0) < 0.1,
          len(xa) / SR if isinstance(xa, array.array) else xa)
    # B. clip 5–15 : silence avant 5, presente 5–15, silence apres
    xb, _ = RUN([], M(MUSC, {"start": 5.0, "end": 15.0, "src_in": 0.0}))
    pb, s0, s1 = rms_db(xb, 5.3, 14.7), rms_db(xb, 0.0, 4.9), rms_db(xb, 15.2, 20.0)
    check("rB_presente_5_15_silence_avant_5_et_apres_15",
          pb is not None and pb > -20 and s0 is not None and s0 < -80 and s1 is not None and s1 < -80,
          (pb, s0, s1))
    # C. clip plus long que la source (18 s pour 4 s) → boucle : presente a chaque seconde
    xc, _ = RUN([], M(MUSC, {"start": 0.0, "end": 18.0, "src_in": 0.0}))
    pc = [rms_db(xc, k + 0.2, k + 0.8) for k in range(18)]
    sc = rms_db(xc, 18.3, 20.0)
    check("rC_boucle_presente_sur_18s_silence_apres",
          all(v is not None and v > -20 for v in pc) and sc is not None and sc < -80, (pc, sc))
    # D. srcIn 1, clip 2–10 : niveaux par seconde = position de source ; reprise au DEBUT de la source
    xd, _ = RUN([], M(MUSM, {"start": 2.0, "end": 10.0, "src_in": 1.0}))
    pd = [pic(xd, k + 0.1, k + 0.9) for k in range(2, 10)]
    check("rD_src_in_respecte_et_boucle_depuis_le_debut",
          pd == [2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0, 1.0] and pic(xd, 0.0, 1.9) == 0.0, (pd, pic(xd, 0.0, 1.9)))
    # E. fondu de sortie cale sur la fin du CLIP (0–11,1, fondu 2 s) : bas juste avant 11,1, plein a 8 s
    xe, _ = RUN([], M(MUSC, {"start": 0.0, "end": 11.1, "src_in": 0.0}, fade_out=2.0))
    e_plein, e_fin, e_ap = rms_db(xe, 7.5, 8.5), rms_db(xe, 10.8, 11.05), rms_db(xe, 12.0, 20.0)
    check("rE_fondu_de_sortie_a_la_fin_du_clip",
          e_plein is not None and e_fin is not None and e_plein > -20 and e_fin < e_plein - 12
          and e_ap is not None and e_ap < -80, (e_plein, e_fin, e_ap))
    # F. automation en temps GLOBAL : clip 5–15, points −40 dB jusqu'a 6,5 s globales, 0 dB des 7 s
    xf, ff_ = RUN([], M(MUSC, {"start": 5.0, "end": 15.0, "src_in": 0.0},
                        volume_points=[(0.0, -40.0), (6.5, -40.0), (7.0, 0.0)]))
    # Revue T2 (M-1) : fenetre « haut » 8–11 s, la ou une automation en temps LOCAL (t − 5) vaudrait
    # encore −40 dB — sur 8–14 la mutation « automation avant adelay » passait (−18,23 dB).
    f_bas, f_haut = rms_db(xf, 5.3, 6.3), rms_db(xf, 8.0, 11.0)
    check("rF_automation_en_temps_global",
          f_bas is not None and f_haut is not None and f_haut > -20 and f_bas < f_haut - 30, (f_bas, f_haut))
    # G. ducking inchange : voix 0–3 s, musique 0–11,1 → bande 440 Hz baissee pendant la voix
    xg, fg = RUN([ASPEC(VOX, 3.0)], M(MUSC, {"start": 0.0, "end": 11.1, "src_in": 0.0}), ducking=True)
    g_pen, g_apr, g_sil = goertzel_db(xg, 0.5, 2.5, 440), goertzel_db(xg, 5.0, 9.0, 440), rms_db(xg, 12.0, 20.0)
    check("rG_ducking_la_musique_baisse_sous_la_voix_et_se_tait_apres_le_clip",
          "sidechaincompress" in fg and g_pen is not None and g_apr is not None and g_apr > g_pen + 4
          and g_sil is not None and g_sil < -80, (g_pen, g_apr, g_sil))
    check("rG_flux_aussi_long_que_le_rendu_avec_ducking",
          isinstance(xg, array.array) and abs(len(xg) / SR - 20.0) < 0.1,
          len(xg) / SR if isinstance(xg, array.array) else xg)
    print("    mesures dB : A clip %s / apres %s ; B avant %s pendant %s apres %s ; E plein %s fin %s ; "
          "F bas %s haut %s ; G 440 Hz pendant voix %s apres %s, apres clip %s ; D niveaux %s"
          % (min(v for v in pa if v is not None) if any(v is not None for v in pa) else None, sa, s0, pb, s1,
             e_plein, e_fin, f_bas, f_haut, g_pen, g_apr, g_sil, pd))
    # I. revue T2 (I-1) : end 1e20 → D plafonne au total, commande acceptee (rc 0), musique jusqu'au bout
    xi, fi_ = RUN([], M(MUSC, {"start": 2.0, "end": 1e20, "src_in": 0.0}, fade_out=1.0))
    _mi = next((p for p in fi_.split(";") if p.endswith("[mtrk]")), "")
    check("rI_end_1e20_plafonne_au_total_rc0",
          isinstance(xi, array.array) and "atrim=0.0:18.0," in _mi and "e+" not in _mi
          and (rms_db(xi, 3.0, 18.5) or -200) > -20 and (rms_db(xi, 0.0, 1.9) or 0) < -80,
          (str(xi)[:200], _mi))
    # J. clip qui demarre apres la fin du rendu (25–30 s, total 20) : rc 0, silence (pas l'historique)
    xj, fj_ = RUN([], M(MUSC, {"start": 25.0, "end": 30.0, "src_in": 0.0}))
    _mj = next((p for p in fj_.split(";") if p.endswith("[mtrk]")), "")
    check("rJ_clip_apres_la_fin_du_rendu_silence_rc0",
          isinstance(xj, array.array) and "adelay=20000|20000" in _mj
          and (rms_db(xj, 0.0, 19.9) or 0) < -80, (str(xj)[:200], _mj))
    # H. temoin historique reel : SANS bornes la musique joue jusqu'au bout (le bug, conserve hors /render)
    xh, _ = RUN([], M(MUSC, None))
    check("rH_temoin_sans_bornes_la_musique_va_au_bout", (rms_db(xh, 15.0, 19.5) or -200) > -20,
          rms_db(xh, 15.0, 19.5))


# ═══════════════ [3] /render et /measure : ce que la route transmet ═══════════════
print("\n[3] espions /render et /measure : le dict musique porte ses bornes")
_cap = {}
_vb, _vr = MS._build_montage_command, MS._run_ffmpeg


def _esp(*a, **k):
    _cap.setdefault("music", []).append(a[3] if len(a) > 3 else k.get("music"))
    _cap.setdefault("a_clips", []).append(a[2] if len(a) > 2 else k.get("a_clips"))
    return _vb(*a, **k)


def _ff_faux(cmd, out, *a, **k):
    pathlib.Path(out).write_bytes(b"0" * 64)


def TLR(clips_a):
    return {"name": "rm", "ratio": "9:16", "preview": True, "mix": {},
            "clips": [{"tr": "v1", "id": "v0", "start": 0, "end": 20, "src": {"file_path": V1}}] + clips_a}


_A2 = {"tr": "a2", "id": "m1", "start": 5, "end": 15, "srcIn": 1, "src": {"file_path": MUSC}}
_A2b = {"tr": "a2", "id": "m2", "start": 16, "end": 18, "srcIn": 0, "src": {"file_path": MUSM}}
_ran = False
if _gok:
    MS._build_montage_command, MS._run_ffmpeg = _esp, _ff_faux
    try:
        _rr = c.post("/api/montage/render", json=TLR([_A2, _A2b]))
        _jid = J(_rr).get("job_id") or "sans-job"
        for _ in range(100):
            _st = J(c.get("/api/jobs/" + str(_jid))).get("status")
            if _st in ("done", "failed"):
                break
            import time; time.sleep(0.1)
        _mr = c.post("/api/montage/measure", json=TLR([_A2, _A2b]))
        _ran = True
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vb, _vr
_mus = [m for m in _cap.get("music", []) if isinstance(m, dict)]
_acl = _cap.get("a_clips", [])
check("s_render_et_measure_ont_appele_le_builder", _ran and len(_mus) == 2, (_ran, len(_mus)))
for _i, _nom in enumerate(("render", "measure")):
    _m = _mus[_i] if len(_mus) > _i else {}
    check(f"s_{_nom}_bornes_du_premier_clip",
          _m.get("bornes") == {"start": 5.0, "end": 15.0, "src_in": 1.0}
          and abs(float(_m.get("src_dur_sonde") or 0) - 4.0) < 0.05, _m)
    _ac = _acl[_i] if len(_acl) > _i and isinstance(_acl[_i], list) else []
    # second clip de la piste en boucle : range en bruitage a3 pose a 16 s (comportement inchange)
    check(f"s_{_nom}_second_clip_en_bruitage_a3_inchange",
          len(_ac) == 1 and _ac[0].get("tr") == "a3" and _ac[0].get("start") == 16.0
          and "bornes" not in _ac[0], _ac)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
