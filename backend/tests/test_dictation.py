# -*- coding: utf-8 -*-
"""T7 (retours IA, 27/09/2026) — H serveur : routes de dictée.

Contrat lu par T10 (client) :
  POST /api/dictation/estimate  multipart {file}
       -> {duration_s, provider, usd, available: bool, reason?}
  POST /api/dictation           multipart {file, max_usd, language?}
       -> {text, usd, provider}
  402 si usd recalculé > max_usd ; 415 prise vide ou illisible ; 413 au-delà
  de 25 Mo ; 503 {detail} si aucune clé (ELEVENLABS_API_KEY, puis
  OPENAI_API_KEY).

ZÉRO transcription réelle : `transcribe_service.transcribe` est remplacé par
un ESPION pendant tout le banc (et l'espion vérifie qu'il reçoit bien un WAV
16 kHz mono, transcodé selon le patron de /audio/recording). Aucune route
payante n'est appelée. Les prises sont FABRIQUÉES par ffmpeg (lavfi
anoisesrc) en webm/opus « live » (comme un MediaRecorder) et en ogg/opus.

Style du dépôt : check(label, cond, detail), assertions négatives avec
témoin positif, état vide, faute n°6 (le DETAIL est évalué AVANT le
court-circuit de cond : il ne doit jamais lever).
Run : & $PY tests/test_dictation.py   (depuis backend/)
"""
import os, sys, tempfile, subprocess, pathlib, shutil, wave
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzdictb_")
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

from app.api import routes as R                          # noqa: E402
from app.services import transcribe_service as TS        # noqa: E402
from app.services.effects_preview import ffmpeg_bin      # noqa: E402
from app.config import settings                          # noqa: E402

FF = ffmpeg_bin()
SRC = pathlib.Path(TMP) / "sources"
SRC.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(settings.outputs_path)


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


def OCTETS(p):
    try:
        return pathlib.Path(p).read_bytes()
    except Exception:                                    # noqa: BLE001
        return b""


def RESTES():
    """Temporaires de la dictée laissés dans outputs (doit rester [])."""
    try:
        if not OUT.exists():
            return []
        return sorted(x.name for x in OUT.iterdir() if x.name.startswith("dzdict"))
    except Exception as e:                               # noqa: BLE001
        return [f"EXC {e!r}"]


def CLES(el, oa):
    settings.ELEVENLABS_API_KEY = el
    settings.OPENAI_API_KEY = oa


# ── Espion : aucune transcription réelle ────────────────────────────────────
APPELS = []
MODE = {"leve": None}
_VRAI = TS.transcribe


def ESPION(audio_path, *, provider=None, language=None, timeout=600.0):
    p = pathlib.Path(audio_path)
    info = {"path": str(p), "provider": provider, "language": language,
            "existe": p.is_file(), "parent": p.parent.name,
            "dans_outputs": OUT.resolve() in p.resolve().parents}
    try:
        with wave.open(str(p), "rb") as w:
            info["wav"] = (w.getframerate(), w.getnchannels(), w.getsampwidth(),
                           round(w.getnframes() / float(w.getframerate()), 2))
    except Exception as e:                               # noqa: BLE001
        info["wav"] = f"EXC {e!r}"
    APPELS.append(info)
    if MODE["leve"]:
        raise MODE["leve"]
    return {"ok": True, "text": "texte simulé de la dictée", "words": [],
            "usd_estimated": 0.0}


TS.transcribe = ESPION

WEBM = FAB("prise.webm", ["-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.2:r=48000",
                          "-ac", "1", "-c:a", "libopus", "-b:a", "32k",
                          "-f", "webm", "-live", "1"])
OGG = FAB("prise.ogg", ["-f", "lavfi", "-i", "anoisesrc=d=3:c=pink:a=0.2:r=48000",
                        "-ac", "1", "-c:a", "libopus", "-b:a", "32k"])
COURT = FAB("court.ogg", ["-f", "lavfi", "-i", "anoisesrc=d=0.03:c=pink:a=0.2:r=48000",
                          "-ac", "1", "-c:a", "libopus"])
check("fabrication : webm, ogg et prise tres courte", bool(WEBM and OGG and COURT),
      f"webm={WEBM} ogg={OGG} court={COURT}")

B_WEBM, B_OGG, B_COURT = OCTETS(WEBM), OCTETS(OGG), OCTETS(COURT)
B_FAUX = b"ceci n'est pas un son " * 40


def EST(octets, nom="prise.webm"):
    return c.post("/api/dictation/estimate",
                  files={"file": (nom, octets, "audio/webm")})


def DIC(octets, max_usd, language=None, nom="prise.webm"):
    data = {"max_usd": str(max_usd)}
    if language is not None:
        data["language"] = language
    return c.post("/api/dictation", data=data,
                  files={"file": (nom, octets, "audio/webm")})


print("\n== Etat vide ==")
check("etat vide : aucun temporaire de dictee avant tout appel", RESTES() == [],
      f"restes={RESTES()}")
check("etat vide : espion jamais appele", APPELS == [], f"appels={APPELS}")

print("\n== Routes montees ==")
# FastAPI récent : `app.routes` porte des `_IncludedRouter` sans `.path`
# (mesuré) ; le schéma OpenAPI, lui, liste chaque chemin monté.
try:
    chemins = set((app.openapi() or {}).get("paths") or {})
except Exception as e:                                   # noqa: BLE001
    chemins = {f"EXC {e!r}"}
check("temoin : /api/audio/recording est monte (lecture des routes valide)",
      "/api/audio/recording" in chemins)
check("/api/dictation/estimate est monte", "/api/dictation/estimate" in chemins)
check("/api/dictation est monte", "/api/dictation" in chemins)

print("\n== Estimation ==")
CLES("test-el", "")
r = EST(B_WEBM)
d = J(r)
check("estimate webm : 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
check("estimate webm : available vrai et fournisseur elevenlabs",
      d.get("available") is True and d.get("provider") == "elevenlabs", f"{d}")
dur = d.get("duration_s") if isinstance(d.get("duration_s"), (int, float)) else -1
check("estimate webm : duree mesuree ~6 s (transcodee)", 5.8 <= dur <= 6.2, f"dur={dur}")
_attendu = TS.estimate_transcription(dur if dur > 0 else 0, "elevenlabs").get("usd")
check("estimate webm : usd = transcribe_service.estimate_transcription(duree)",
      d.get("usd") == _attendu and (_attendu or 0) > 0, f"usd={d.get('usd')} attendu={_attendu}")
check("estimate webm : pas de reason quand disponible", "reason" not in d, f"{d}")
check("estimate : espion jamais appele", APPELS == [], f"appels={len(APPELS)}")
check("estimate : aucun temporaire laisse", RESTES() == [], f"restes={RESTES()}")

r = EST(B_OGG, "prise.ogg")
d = J(r)
dur_ogg = d.get("duration_s") if isinstance(d.get("duration_s"), (int, float)) else -1
check("estimate ogg : 200 et ~3 s", r.status_code == 200 and 2.8 <= dur_ogg <= 3.2,
      f"{r.status_code} {d}")

CLES("", "test-oa")
d = J(EST(B_OGG, "prise.ogg"))
_attendu = TS.estimate_transcription(dur_ogg if dur_ogg > 0 else 0, "openai").get("usd")
check("estimate sans ElevenLabs : repli openai et son tarif",
      d.get("provider") == "openai" and d.get("usd") == _attendu, f"{d} attendu={_attendu}")

CLES("", "")
r = EST(B_WEBM)
d = J(r)
check("estimate sans cle : 200, available faux, reason lisible",
      r.status_code == 200 and d.get("available") is False
      and isinstance(d.get("reason"), str) and len(d.get("reason") or "") > 10,
      f"{r.status_code} {d}")
check("estimate sans cle : duree tout de meme mesuree, usd 0",
      5.8 <= (d.get("duration_s") or -1) <= 6.2 and d.get("usd") == 0, f"{d}")

CLES("test-el", "")
r = EST(b"")
check("estimate prise vide : 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")
r = EST(B_FAUX)
check("estimate prise illisible : 415 avec detail",
      r.status_code == 415 and bool(J(r).get("detail")), f"{r.status_code} {r.text[:200]}")
r = EST(B_COURT, "court.ogg")
check("estimate prise trop courte (< 0,1 s) : 415", r.status_code == 415,
      f"{r.status_code} {r.text[:200]}")
r = EST(b"\0" * (25 * 1024 * 1024 + 1))
check("estimate au-dela de 25 Mo : 413", r.status_code == 413, f"{r.status_code} {r.text[:200]}")
check("estimate (refus) : espion jamais appele", APPELS == [], f"appels={len(APPELS)}")
check("estimate (refus) : aucun temporaire laisse", RESTES() == [], f"restes={RESTES()}")

print("\n== Transcription : refus AVANT toute depense ==")
d = J(EST(B_WEBM))
USD = d.get("usd") or 0
check("temoin : usd de la prise de 6 s strictement positif", USD > 0, f"{d}")
r = DIC(B_WEBM, 0)
check("dictation max_usd=0 : 402", r.status_code == 402, f"{r.status_code} {r.text[:200]}")
r = DIC(B_WEBM, round(USD - 0.0001, 4))
check("dictation max_usd juste sous l'estimation : 402 avec detail",
      r.status_code == 402 and bool(J(r).get("detail")), f"{r.status_code} {r.text[:200]}")
check("402 : espion jamais appele", APPELS == [], f"appels={len(APPELS)}")

CLES("", "")
r = DIC(B_WEBM, 1)
check("dictation sans cle : 503 avec detail",
      r.status_code == 503 and bool(J(r).get("detail")), f"{r.status_code} {r.text[:200]}")
CLES("test-el", "")
r = DIC(b"", 1)
check("dictation prise vide : 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")
r = DIC(B_FAUX, 1)
check("dictation prise illisible : 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")
r = DIC(b"\0" * (25 * 1024 * 1024 + 1), 1)
check("dictation au-dela de 25 Mo : 413", r.status_code == 413, f"{r.status_code} {r.text[:200]}")
r = c.post("/api/dictation", files={"file": ("prise.webm", B_WEBM, "audio/webm")})
check("dictation sans max_usd : refusee (4xx)", 400 <= r.status_code < 500,
      f"{r.status_code} {r.text[:200]}")
r = DIC(B_WEBM, "abc")
check("dictation max_usd non numerique : refusee (4xx)", 400 <= r.status_code < 500,
      f"{r.status_code} {r.text[:200]}")
check("402 / 503 / 415 / 413 / 4xx : espion jamais appele", APPELS == [],
      f"appels={len(APPELS)}")
check("refus : aucun temporaire laisse", RESTES() == [], f"restes={RESTES()}")

_garde = R._require_localhost
def _refuse(request):
    from fastapi import HTTPException
    raise HTTPException(403, "garde locale simulee")
R._require_localhost = _refuse
try:
    r1 = DIC(B_WEBM, 1)
    r2 = EST(B_WEBM)
finally:
    R._require_localhost = _garde
check("garde locale (routes._require_localhost) appliquee aux deux routes : 403",
      r1.status_code == 403 and r2.status_code == 403, f"{r1.status_code} {r2.status_code}")
check("garde locale : espion jamais appele", APPELS == [], f"appels={len(APPELS)}")

print("\n== Transcription : accord ==")
r = DIC(B_WEBM, USD, language="fr-FR")
d = J(r)
check("dictation max_usd = montant affiche : 200", r.status_code == 200,
      f"{r.status_code} {r.text[:200]}")
check("dictation : texte simule rendu", d.get("text") == "texte simulé de la dictée", f"{d}")
check("dictation : usd recalcule et fournisseur", d.get("usd") == USD
      and d.get("provider") == "elevenlabs", f"{d} usd attendu={USD}")
check("dictation : UN appel espionne", len(APPELS) == 1, f"appels={len(APPELS)}")
a = APPELS[0] if APPELS else {}
check("espion : recoit un WAV 16 kHz mono s16 d'environ 6 s",
      isinstance(a.get("wav"), tuple) and a["wav"][:3] == (16000, 1, 2)
      and 5.8 <= a["wav"][3] <= 6.2, f"{a.get('wav')}")
check("espion : fournisseur resolu passe (elevenlabs), langue ramenee a 'fr'",
      a.get("provider") == "elevenlabs" and a.get("language") == "fr", f"{a}")
check("temoin : le temporaire vit dans outputs pendant l'appel",
      a.get("existe") is True and a.get("dans_outputs") is True
      and str(a.get("parent", "")).startswith("dzdict"), f"{a}")
check("accord : temporaire supprime apres l'appel", RESTES() == [], f"restes={RESTES()}")

r = DIC(B_OGG, 1, nom="prise.ogg")
check("dictation sans langue : 200, langue None transmise",
      r.status_code == 200 and len(APPELS) == 2 and APPELS[-1].get("language") is None,
      f"{r.status_code} {APPELS[-1] if APPELS else None}")

MODE["leve"] = RuntimeError("ElevenLabs: HTTP 500 — panne simulee")
r = DIC(B_WEBM, 1)
MODE["leve"] = None
check("echec du fournisseur : 502 avec detail",
      r.status_code == 502 and "panne simulee" in str(J(r).get("detail", "")),
      f"{r.status_code} {r.text[:200]}")
check("echec du fournisseur : temporaire supprime", RESTES() == [], f"restes={RESTES()}")

TS.transcribe = _VRAI
CLES("", "")
try:
    c.__exit__(None, None, None)
except Exception:                                        # noqa: BLE001
    pass
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
