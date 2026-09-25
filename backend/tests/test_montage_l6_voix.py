# -*- coding: utf-8 -*-
"""L6 — D-26 voix off : route `POST /api/audio/recording`. ECART au plan (mesure
du 25/09/2026) : `POST /api/audio/voiceover` EXISTE DEJA — c'est la synthese
vocale ElevenLabs PAYANTE (`create_voiceover`, Quick / Studio / Chapitres /
son-vfx-montage) ; la prise du micro prend donc un chemin a elle, et le banc
verifie que la route payante reste seule a son chemin, intacte, jamais appelee
avec un script (un POST sans script y rend 400 AVANT toute depense).
En-tete recopie de
test_montage_l5.py (env, check, J, TestClient sans port ouvert ; fin :
fermeture des handles puis rmtree) : dossier de donnees NEUF par execution,
toute lecture gardee (faute n6 : le DETAIL est evalue AVANT le court-circuit
de la condition, il ne doit donc jamais lever).
Run : & $PY tests/test_montage_l6_voix.py   (depuis backend/)

Les prises sont FABRIQUEES par `effects_preview.ffmpeg_bin()` : un .webm opus
mono ecrit « live » (`-f webm -live 1` : aucune duree d'en-tete, comme un
MediaRecorder — verifie par ffprobe), un .ogg opus, un .wav s16 44,1 k
stereo. Chacune doit ressortir en WAV PCM s16 48 kHz MONO, nom
`voix-off-AAAAMMJJ-HHMMSS[-n].wav`, jamais ecrase. Aucune depense : aucune
route payante n'est appelee.
"""
import hashlib, json, os, re, sys, tempfile, subprocess, pathlib, shutil, wave
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl6v_")
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
import inspect                                           # noqa: E402
from app.api import routes as R                          # noqa: E402
from app.services import montage_service as MS           # noqa: E402
from app.services.effects_preview import ffmpeg_bin      # noqa: E402
from app.config import settings                          # noqa: E402

FF = ffmpeg_bin()
FP = str(pathlib.Path(FF).with_name("ffprobe" + pathlib.Path(FF).suffix)) \
    if os.path.sep in FF or "/" in FF else "ffprobe"
SRC = pathlib.Path(TMP) / "sources"
SRC.mkdir(parents=True, exist_ok=True)
ADIR = settings.images_path.parent / "audio"
NOM_RE = re.compile(r"^voix-off-\d{8}-\d{6}(-\d+)?\.wav$")


def FAB(nom, args):
    """Fabrique une source par ffmpeg ; rend le chemin ou None (jamais d'exception)."""
    p = SRC / nom
    try:
        subprocess.run([FF, "-y", "-loglevel", "error", *args, str(p)],
                       capture_output=True, timeout=60, check=False)
    except Exception as e:                               # noqa: BLE001
        print("  (ffmpeg injoignable : %s)" % e)
        return None
    return p if p.is_file() and p.stat().st_size > 0 else None


def PROBE_DUR(p):
    """format.duration par ffprobe : None si absente, 'EXC …' si ffprobe meurt."""
    try:
        out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                              "-of", "json", str(p)], capture_output=True, text=True,
                             timeout=30).stdout
        d = (json.loads(out or "{}").get("format") or {}).get("duration")
        return None if d in (None, "N/A") else float(d)
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


def WAV(p):
    """(rate, canaux, octets/ech, duree) du WAV, ou ('EXC …',)."""
    try:
        with wave.open(str(p), "rb") as w:
            return (w.getframerate(), w.getnchannels(), w.getsampwidth(),
                    w.getnframes() / float(w.getframerate()))
    except Exception as e:                               # noqa: BLE001
        return (f"EXC {e!r}",)


def H(p):
    try:
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


def LISTE():
    try:
        if not ADIR.exists():                            # etat vide : dossier pas encore cree
            return []
        return sorted(x.name for x in ADIR.iterdir())
    except Exception as e:                               # noqa: BLE001
        return [f"EXC {e!r}"]


def RESTES():
    """Temporaires de la route laisses dans outputs (prefixe dzvo_)."""
    try:
        return sorted(str(x) for x in pathlib.Path(settings.outputs_path).rglob("dzvo_*"))
    except Exception as e:                               # noqa: BLE001
        return [f"EXC {e!r}"]


def POST(p, nom=None, mime="application/octet-stream", client=None, octets=None):
    cl = client or c
    try:
        corps = octets if octets is not None else pathlib.Path(p).read_bytes()
        r = cl.post("/api/audio/recording", files={"file": (nom or pathlib.Path(p).name, corps, mime)})
        return r.status_code, J(r)
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}", {}


print("\n[0] etat vide : dossier audio sans prise, aucune route payante")
_vide = [n for n in LISTE() if n.startswith("voix-off-")]
check("v0_etat_vide_aucune_prise_avant_le_banc_temoin_dossier_lisible",
      _vide == [] and not any(n.startswith("EXC") for n in LISTE()), str(LISTE()))
# FastAPI de ce python : `app.routes` ne porte que des `_IncludedRouter` (mesure) —
# on lit le routeur de routes.py (chemins SANS le prefixe /api).
_rt = [(getattr(x, "path", ""), sorted(getattr(x, "methods", None) or []),
        getattr(getattr(x, "endpoint", None), "__name__", "")) for x in R.router.routes]
_paths = [p for p, _m, _n in _rt]
_i_up = _paths.index("/audio/upload") if "/audio/upload" in _paths else -9
_i_rec = _paths.index("/audio/recording") if "/audio/recording" in _paths else -1
check("v0_route_recording_declaree_juste_apres_audio_upload",
      _i_up >= 0 and _i_rec == _i_up + 1 and _rt[_i_rec][1] == ["POST"]
      and _rt[_i_rec][2] == "audio_recording", str([x for x in _rt if "/audio" in x[0]]))
_vo = [x for x in _rt if x[0] == "/audio/voiceover"]
check("v0_route_payante_voiceover_intacte_seule_a_son_chemin_temoin_recording_distincte",
      _vo == [("/audio/voiceover", ["POST"], "create_voiceover")] and _i_rec >= 0, str(_vo))
try:
    _srcf = inspect.getsource(R.audio_recording)
except Exception as e:                                   # noqa: BLE001
    _srcf = f"EXC {e!r}"
check("v0_garde_locale_et_ffmpeg_en_thread_dans_la_route",
      "_require_localhost(request)" in _srcf and "await asyncio.to_thread(" in _srcf
      # la garde passe AVANT toute lecture du fichier recu
      and 0 <= _srcf.find("_require_localhost(request)") < _srcf.find("await file.read(")
      # aucune synthese ni fournisseur payant dans la prise
      and "Voiceover" not in _srcf and "elevenlabs" not in _srcf.lower(),
      _srcf[:300])

print("\n[1] trois formats de prise -> WAV s16 48 kHz mono")
WEBM = FAB("prise.webm", ["-f", "lavfi", "-i", "sine=f=440:d=1.5:r=48000", "-ac", "1",
                          "-c:a", "libopus", "-f", "webm", "-live", "1"])
OGG = FAB("prise.ogg", ["-f", "lavfi", "-i", "sine=f=330:d=2.0:r=48000", "-ac", "1",
                        "-c:a", "libopus"])
WAVS = FAB("prise.wav", ["-f", "lavfi", "-i", "sine=f=220:d=1.25:r=44100", "-ac", "2",
                         "-c:a", "pcm_s16le"])
_pd = PROBE_DUR(WEBM) if WEBM else "ABSENT"
_pn = PROBE_DUR(OGG) if OGG else "ABSENT"
check("v1_imitation_live_webm_sans_duree_d_en_tete_temoin_ogg_avec_duree",
      WEBM is not None and _pd is None and isinstance(_pn, float) and abs(_pn - 2.0) < 0.05,
      f"webm={_pd} ogg={_pn}")

PRISES = {}
for _nom, _p, _dur, _mime in (("webm", WEBM, 1.5, "audio/webm;codecs=opus"),
                              ("ogg", OGG, 2.0, "audio/ogg"),
                              ("wav", WAVS, 1.25, "audio/wav")):
    _avant = LISTE()
    _st, _d = POST(_p, mime=_mime) if _p else ("ABSENT", {})
    _fn = str(_d.get("filename") or "")
    _w = WAV(ADIR / _fn) if _fn else ("ABSENT",)
    PRISES[_nom] = _fn
    check(f"v1_{_nom}_200_nom_voix_off_wav_48k_mono_16_bits_duree_fabriquee",
          _st == 200 and _d.get("ok") is True and bool(NOM_RE.match(_fn))
          and _w[:3] == (48000, 1, 2) and abs(_w[3] - _dur) <= 0.05,
          f"{_st} {_d} {_w}")
    check(f"v1_{_nom}_reponse_dur_et_size_kb_coherents_avec_le_fichier_ecrit",
          isinstance(_d.get("dur"), (int, float)) and len(_w) == 4
          and abs(float(_d.get("dur") or 0) - _w[3]) <= 0.01
          and _d.get("size_kb") == ((ADIR / _fn).stat().st_size // 1024 if _fn and (ADIR / _fn).is_file() else -1),
          f"{_d} {_w}")
    check(f"v1_{_nom}_un_seul_fichier_neuf_dans_le_dossier_audio_hors_fiche",
          [n for n in LISTE() if n not in _avant and n != "_sfx_meta.json"] == ([_fn] if _fn else ["?"]),
          str(sorted(set(LISTE()) - set(_avant))))
check("v1_aucun_temporaire_laisse_apres_trois_prises", RESTES() == [], str(RESTES()))

print("\n[2] jamais ecrase : deux prises dans la meme seconde")
_reel_dt = R.datetime


class _Fige(_reel_dt):
    @classmethod
    def now(cls, tz=None):
        return _reel_dt(2026, 9, 25, 10, 15, 0)


R.datetime = _Fige
try:
    _s1, _d1 = POST(OGG) if OGG else ("ABSENT", {})
    _f1 = str(_d1.get("filename") or "")
    _h1 = H(ADIR / _f1) if _f1 else "ABSENT"
    _s2, _d2 = POST(WAVS) if WAVS else ("ABSENT", {})
    _f2 = str(_d2.get("filename") or "")
    _s3, _d3 = POST(WEBM) if WEBM else ("ABSENT", {})
    _f3 = str(_d3.get("filename") or "")
finally:
    R.datetime = _reel_dt
check("v2_meme_seconde_trois_noms_distincts_base_puis_2_puis_3",
      (_s1, _s2, _s3) == (200, 200, 200) and _f1 == "voix-off-20260925-101500.wav"
      and _f2 == "voix-off-20260925-101500-2.wav" and _f3 == "voix-off-20260925-101500-3.wav",
      f"{_s1} {_f1} | {_s2} {_f2} | {_s3} {_f3}")
check("v2_la_premiere_prise_reste_intacte_apres_les_suivantes_temoin_durees_distinctes",
      _f1 != "" and H(ADIR / _f1) == _h1 and not str(_h1).startswith("EXC")
      and len(WAV(ADIR / _f1)) == 4 and abs(WAV(ADIR / _f1)[3] - 2.0) <= 0.05
      and len(WAV(ADIR / _f2)) == 4 and abs(WAV(ADIR / _f2)[3] - 1.25) <= 0.05,
      f"{_h1} {WAV(ADIR / _f1) if _f1 else ''} {WAV(ADIR / _f2) if _f2 else ''}")

print("\n[3] liste, fiche, Bibliotheque, resolution Montage, aucun job")
_la = J(c.get("/api/audio")).get("audio") or []
_noms = [str(x.get("name")) for x in _la if isinstance(x, dict)]
check("v3_get_audio_liste_toutes_les_prises",
      all(PRISES.get(k) in _noms for k in ("webm", "ogg", "wav")) and _f1 in _noms and _f2 in _noms,
      str(_noms))
_meta = J(c.get("/api/audio/meta")).get("meta") or {}
_m = _meta.get(PRISES.get("webm") or "?") or {}
check("v3_fiche_sons_kind_voix_que_le_tiroir_range_sur_a1_et_date",
      _m.get("kind") == "voix" and bool(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", str(_m.get("created") or ""))),
      str(_m))
try:
    _rs = asyncio.run(MS._resolve_src({"audio": PRISES.get("ogg") or "?"}))
except Exception as e:                                   # noqa: BLE001
    _rs = f"EXC {e!r}"
try:
    _rs0 = asyncio.run(MS._resolve_src({"audio": "voix-off-absente.wav"}))
except Exception as e:                                   # noqa: BLE001
    _rs0 = f"EXC {e!r}"
check("v3_montage_resolve_src_audio_trouve_la_prise_temoin_absente_none",
      isinstance(_rs, pathlib.Path) and _rs.name == PRISES.get("ogg") and _rs.is_file() and _rs0 is None,
      f"{_rs} {_rs0}")
_g = c.get("/api/audio/" + (PRISES.get("wav") or "x"))
check("v3_prise_servie_par_get_audio_filename",
      _g.status_code == 200 and _g.content[:4] == b"RIFF" and _g.content[8:12] == b"WAVE",
      f"{_g.status_code} {_g.content[:12]!r}")

# Espion sur l'index Bibliotheque (appel REEL conserve) + jobs avant/apres.
_appels = []
_noter0 = R.LI.noter


async def _espion(files, source, kind="image", **kw):
    _appels.append((list(files), source, kind))
    return await _noter0(files, source, kind=kind, **kw)


R.LI.noter = _espion
_jobs0 = J(c.get("/api/jobs?limit=200"))
try:
    _s4, _d4 = POST(OGG) if OGG else ("ABSENT", {})
finally:
    R.LI.noter = _noter0
_jobs1 = J(c.get("/api/jobs?limit=200"))
_f4 = str(_d4.get("filename") or "")
check("v3_bibliotheque_notee_import_kind_audio_pour_la_prise",
      _s4 == 200 and _appels == [([_f4], "import", "audio")], f"{_s4} {_appels}")
check("v3_aucun_job_cree_par_une_prise_temoin_liste_des_jobs_lisible",
      _jobs0 == _jobs1 and _jobs0 != {}, f"{str(_jobs0)[:120]} / {str(_jobs1)[:120]}")

print("\n[4] refus : 415 format illisible, 413 taille, 403 hors local — rien d'ecrit")
_txt = SRC / "note.txt"
_txt.write_text("ceci n'est pas une prise\n" * 20, encoding="utf-8")
_avant = LISTE()
_s5, _d5 = POST(_txt, mime="text/plain")
check("v4_texte_415_detail_et_aucun_fichier_neuf_ni_temporaire",
      _s5 == 415 and bool(_d5.get("detail")) and LISTE() == _avant and RESTES() == [],
      f"{_s5} {_d5} {sorted(set(LISTE()) - set(_avant))} {RESTES()}")
_s6, _d6 = POST(None, nom="vide.webm", octets=b"")
check("v4_fichier_vide_415_et_rien_d_ecrit", _s6 == 415 and LISTE() == _avant, f"{_s6} {_d6}")
# prise trop courte (< 0,1 s) : ffmpeg reussit mais la duree est refusee
COURT = FAB("court.wav", ["-f", "lavfi", "-i", "sine=f=440:d=0.05:r=48000", "-ac", "1", "-c:a", "pcm_s16le"])
_s7, _d7 = POST(COURT) if COURT else ("ABSENT", {})
check("v4_prise_de_0_05_s_415_trop_courte_et_rien_d_ecrit",
      _s7 == 415 and "court" in str(_d7.get("detail") or "").lower() and LISTE() == _avant and RESTES() == [],
      f"{_s7} {_d7}")
_LIM = 50 * 1024 * 1024
_s8, _d8 = POST(None, nom="gros.webm", octets=b"\0" * (_LIM + 1))
_s9, _d9 = POST(None, nom="pile.webm", octets=b"\0" * _LIM)
check("v4_50_mo_plus_un_octet_413_temoin_50_mo_pile_passe_la_garde_de_taille_415",
      _s8 == 413 and "50" in str(_d8.get("detail") or "") and _s9 == 415
      and LISTE() == _avant and RESTES() == [], f"{_s8} {_d8} | {_s9} {_d9}")
_loin = TestClient(app, raise_server_exceptions=False, client=("10.1.2.3", 50000))
_s10, _d10 = POST(OGG, client=_loin) if OGG else ("ABSENT", {})
_ap10 = LISTE()
_s11, _d11 = POST(OGG) if OGG else ("ABSENT", {})
check("v4_hors_local_403_rien_d_ecrit_temoin_meme_prise_locale_200",
      _s10 == 403 and _ap10 == _avant and _s11 == 200 and len(LISTE()) == len(_avant) + 1,
      f"{_s10} {_d10} | {_s11} {_d11}")
check("v4_aucun_temporaire_laisse_apres_les_refus", RESTES() == [], str(RESTES()))

print("\n[5] revue : plafond 2 h, 504 au timeout, nettoyage du nom reserve, 413 precoce")
_run0 = subprocess.run
_cmds = []


def _espion_run(cmd, *a, **kw):
    _cmds.append((list(cmd), dict(kw)))
    return _run0(cmd, *a, **kw)


subprocess.run = _espion_run
try:
    _s12, _d12 = POST(OGG) if OGG else ("ABSENT", {})
finally:
    subprocess.run = _run0
_ff = [x for x in _cmds if x[0] and "ffmpeg" in str(x[0][0]).lower()]
_cm, _kw = (_ff[0] if len(_ff) == 1 else ([], {}))
def _ix(lst, v):
    return lst.index(v) if v in lst else -1


_it, _ii, _in = _ix(_cm, "-t"), _ix(_cm, "-i"), _ix(_cm, "-nostdin")
check("v5_commande_ffmpeg_plafonnee_t_7200_avant_la_sortie_nostdin_temoin_200",
      _s12 == 200 and _ii >= 0 and _it > _ii + 1 and _it < len(_cm) - 2
      and _cm[_it + 1] == "7200" and str(_cm[-1]).endswith("prise.wav")
      and 0 <= _in < _ii,
      f"{_s12} {_cm}")
check("v5_stderr_decode_utf8_replace_et_stdin_devnull",
      _kw.get("encoding") == "utf-8" and _kw.get("errors") == "replace"
      and _kw.get("stdin") is subprocess.DEVNULL and _kw.get("timeout") == 180,
      str({k: v for k, v in _kw.items() if k != "input"}))


def _trop_long(cmd, *a, **kw):
    if cmd and "ffmpeg" in str(cmd[0]).lower():
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout") or 180)
    return _run0(cmd, *a, **kw)


_avant = LISTE()
subprocess.run = _trop_long
try:
    _s13, _d13 = POST(OGG) if OGG else ("ABSENT", {})
finally:
    subprocess.run = _run0
check("v5_timeout_ffmpeg_504_transcodage_trop_long_rien_d_ecrit_ni_temporaire",
      _s13 == 504 and "trop long" in str(_d13.get("detail") or "").lower()
      and LISTE() == _avant and RESTES() == [],
      f"{_s13} {_d13} {sorted(set(LISTE()) - set(_avant))} {RESTES()}")
_s14, _d14 = POST(OGG) if OGG else ("ABSENT", {})
check("v5_temoin_meme_prise_sans_espion_200_un_fichier_neuf",
      _s14 == 200 and len(LISTE()) == len(_avant) + 1, f"{_s14} {_d14}")

# os.replace ET shutil.copyfile echouent vers le dossier audio : le nom reserve
# (cree vide par _recording_name) doit repartir, rien ne reste.
_rep0, _cop0 = os.replace, shutil.copyfile
_echecs = []


def _rep_ko(a, b, *r, **k):
    if pathlib.Path(b).name.startswith("voix-off-"):
        _echecs.append(("replace", pathlib.Path(b).name))
        raise OSError(18, "volume different (simule)")
    return _rep0(a, b, *r, **k)


def _cop_ko(a, b, *r, **k):
    if pathlib.Path(b).name.startswith("voix-off-"):
        _echecs.append(("copyfile", pathlib.Path(b).name))
        raise OSError(28, "disque plein (simule)")
    return _cop0(a, b, *r, **k)


_avant = LISTE()
os.replace, shutil.copyfile = _rep_ko, _cop_ko
try:
    _s15, _d15 = POST(OGG) if OGG else ("ABSENT", {})
finally:
    os.replace, shutil.copyfile = _rep0, _cop0
check("v5_replace_et_copie_en_echec_les_deux_voies_traversees_vers_le_meme_nom",
      [x[0] for x in _echecs] == ["replace", "copyfile"] and len({x[1] for x in _echecs}) == 1
      and bool(NOM_RE.match(_echecs[0][1] if _echecs else "")), str(_echecs))
check("v5_ecriture_impossible_500_nom_reserve_supprime_dossier_inchange_sans_temporaire",
      _s15 == 500 and "impossible" in str(_d15.get("detail") or "").lower()
      and LISTE() == _avant and RESTES() == [],
      f"{_s15} {_d15} {sorted(set(LISTE()) - set(_avant))} {RESTES()}")

# 413 precoce sur l'en-tete content-length : appel direct de la route, le
# fichier factice compte ses lectures.
from starlette.requests import Request as _Req           # noqa: E402
from fastapi import HTTPException as _HE                 # noqa: E402


class _Fich:
    def __init__(self):
        self.lus = 0

    async def read(self, n=-1):
        self.lus += 1
        return b""


def _direct(cl):
    f = _Fich()
    rq = _Req({"type": "http", "method": "POST", "path": "/api/audio/recording",
               "headers": [(b"content-length", str(cl).encode())],
               "client": ("127.0.0.1", 50001), "query_string": b""})
    try:
        asyncio.run(R.audio_recording(rq, f))
        return "SANS_REFUS", "", f.lus
    except _HE as e:
        return e.status_code, str(e.detail), f.lus
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}", "", f.lus


_avant = LISTE()
_g1 = _direct(_LIM + 65536 + 1)
_g0 = _direct(_LIM + 65536)
check("v5_en_tete_au_dela_de_50_mo_plus_64_kio_413_sans_lecture_temoin_a_la_limite_lu_puis_415",
      _g1[0] == 413 and "50" in _g1[1] and _g1[2] == 0
      and _g0[0] == 415 and _g0[2] == 1 and LISTE() == _avant, f"{_g1} {_g0}")

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
# Nettoyage : le journal loguru et le pool sqlite tiennent encore des handles
# apres le lifespan — on les ferme d'abord, puis on efface sans jamais rougir.
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
