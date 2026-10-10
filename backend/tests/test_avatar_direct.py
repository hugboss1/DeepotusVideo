# -*- coding: utf-8 -*-
"""Avatar live G4 (t165, 10/10/2026) — le Direct sur PC, côté serveur : la clé Decart posée À CHAUD depuis l'écran
(/api/settings/keys, coffre ou .env), l'enregistrement du direct (webm du navigateur) rangé en RENDU mp4 de l'app
(job provider recast / modèle « direct », lignée vers le Personnage dans le titre), et le module SDK Decart vendu
avec l'écran (version épinglée, licences).

Le flux vidéo du direct ne passe JAMAIS par le backend (WebRTC navigateur ⇄ Decart) : ce banc ne le simule pas.
Run (depuis backend/) : & $PY tests/test_avatar_direct.py"""
import base64, io, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdirect_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("DECART_API_KEY", None)
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
_RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
WEBM = _tmp / "direct.webm"   # ce que rend MediaRecorder : VP8/VP9 + Opus, SANS durée dans l'en-tête (webm « live »)
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25:duration=3", "-f", "lavfi",
                "-i", "sine=frequency=300:duration=3", "-shortest", "-c:v", "libvpx", "-b:v", "1M", "-c:a", "libopus",
                "-f", "webm", "-live", "1", str(WEBM)], check=True, timeout=180)
from app.services.fal_video_tools import probe as _probe0      # noqa: E402
_t0 = _probe0(WEBM)


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (600, 600), (200, 80, 40)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import recast_service as RS                       # noqa: E402

print("\n[V] le SDK Decart vendu avec l'écran")
V = _RACINE / "frontend" / "avatar" / "vendor"
sdk = V / "decart-sdk-0.2.8.js"
check("V1 le module ESM épinglé 0.2.8 est là et exporte createDecartClient et models",
      sdk.is_file() and b"createDecartClient" in sdk.read_bytes() and sdk.stat().st_size > 200_000)
lic = (V / "LICENCES.txt").read_text(encoding="utf-8") if (V / "LICENCES.txt").is_file() else ""
check("V2 les licences des paquets embarqués sont jointes (SDK MIT, livekit-client Apache-2.0, jose, zod, mitt, p-retry)",
      all(n in lic for n in ("@decartai/sdk", "livekit-client", "Apache License", "jose", "zod", "mitt", "p-retry")))
direct = (_RACINE / "frontend" / "avatar" / "direct.js").read_text(encoding="utf-8") if (_RACINE / "frontend" / "avatar" / "direct.js").is_file() else ""
check("V3 l'écran importe le module LOCAL (aucun CDN) et ne lit jamais une clé permanente",
      './vendor/decart-sdk-0.2.8.js' in direct and "http" not in direct.split("import")[1].split(";")[0]
      and "DECART_API_KEY" in direct and "apiKey: st.sess.jeton" in direct)

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    print("\n[K] la clé posée depuis l'écran")
    check("K1 sans clé : l'état le dit", loc.get("/api/avatar-live/etat").json()["cle"] is False)
    r = loc.post("/api/settings/keys", json={"name": "DECART_API_KEY", "value": "dct_essai_123"})
    check("K2 posée par /api/settings/keys : appliquée À CHAUD (l'état passe à vrai sans redémarrage)",
          r.status_code == 200 and loc.get("/api/avatar-live/etat").json()["cle"] is True
          and settings.DECART_API_KEY == "dct_essai_123", r.text[:200])
    check("K3 la valeur ne revient jamais : /etat ne montre qu'un booléen",
          "dct_essai_123" not in loc.get("/api/avatar-live/etat").text)

    print("\n[E] l'enregistrement du direct devient un rendu")
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True}).json()["id"]
    with open(WEBM, "rb") as fh:
        rdep = loc.post("/api/avatar-live/recast/source", files={"fichier": ("direct.webm", fh, "video/webm")}).json()
    dep = rdep.get("depot", "")
    check("E0 témoin : ce webm « live » n'a PAS de durée lisible (relevé en preuve le 10/10 sur un vrai MediaRecorder)",
          not _t0["duration_s"] and _t0["width"] == 1280, str(_t0))
    check("E1 le webm du navigateur est accepté comme dépôt, sa durée MESURÉE (3 s)", dep.endswith(".webm") and abs((rdep.get("duree_s") or 0) - 3) < 0.3, str(rdep))
    r = loc.post("/api/avatar-live/direct/enregistrer", json={"depot": dep, "personnage_id": pid})
    jid = r.json().get("job_id", "") if r.status_code == 200 else ""
    fin = time.time() + 90
    j = {}
    while time.time() < fin and jid:
        j = loc.get(f"/api/jobs/{jid}").json()
        if j.get("status") in ("done", "failed"):
            break
        time.sleep(0.3)
    sortie = _tmp / "outputs" / "final" / f"{jid}.mp4"
    from app.services.fal_video_tools import probe                  # noqa: E402
    check("E2 job done, modèle « direct », titre au nom du Personnage, mp4 h264 avec son, 3 s, 16:9",
          j.get("status") == "done" and j.get("video_model") == "direct" and "Oli" in (j.get("title") or "")
          and sortie.is_file() and RS.a_du_son(sortie) and abs(probe(sortie)["duration_s"] - 3) < 0.3
          and probe(sortie)["ratio"] == "16:9", str(j)[:250])
    check("E3 le dépôt webm est retiré après conversion (pas de doublon sur le disque)", RS.chemin_depot(dep) is None)
    r = loc.post("/api/avatar-live/direct/enregistrer", json={"depot": "f" * 24 + ".webm"})
    check("E4 dépôt inconnu : 404", r.status_code == 404, r.text[:200])
    check("E5 depuis le Wi-Fi : écriture refusée (le téléphone viendra en G6)",
          lan.post("/api/avatar-live/direct/enregistrer", json={"depot": dep},
                   headers={"Authorization": "Bearer " + "0" * 64}).status_code in (401, 403))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
