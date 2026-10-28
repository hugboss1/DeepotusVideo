# -*- coding: utf-8 -*-
"""t318 (28/10/2026) (D4, tâche 3) — banc des routes /api/live (app/api/live_routes.py).
Plan docs/superpowers/plans/2026-10-28-t318-live.md, spec boîte à outils §8.6.
  R1 ouvrir : vue sans URL ni clé ; refus traduits (L10) ; comptes live listés par /api/comptes?live=1 seulement ;
  R2 WebSocket : Origin étranger refusé (aucun ffmpeg lancé) ;
  R3 WebSocket : les morceaux vont dans un VRAI ffmpeg, un récepteur RTMP local `-listen 1` reçoit la vidéo, l'état
     revient par le même WebSocket (« en_direct »), la destination fermée est « panne » ;
  R4 déconnexion = ffmpeg fini ; marqueurs ; terminer écrit <capture>.dzlive.json ; journaux sans clé ;
  R5 annonce : faux serveur local (DZ_LIVE_PREUVE), réponse {ok, statut} sans URL ;
  R6 hors machine locale : 403 partout.
Données jetables. Réseau : boucle locale seulement. Run (depuis backend/) : & $PY tests/test_live_routes.py"""
import json, os, pathlib, shutil, socket, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlivert_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
os.environ["DZ_LIVE_PREUVE"] = "1"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
_JOURNAL = []
logger.add(lambda m: _JOURNAL.append(str(m)), level="DEBUG")
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


from app.main import app                                            # noqa: E402
from app.services import comptes as CP, espaces as ES, live as L, capture as C   # noqa: E402

FF = shutil.which("ffmpeg")
CLE = "live_99_SECRETROUTES"


def port_libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


# faux Discord local
RECUS = []
class _Discord(BaseHTTPRequestHandler):
    def do_POST(self):
        RECUS.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
        self.send_response(204); self.end_headers()
    def log_message(self, *a): pass
pd = port_libre()
srv = HTTPServer(("127.0.0.1", pd), _Discord)
threading.Thread(target=srv.serve_forever, daemon=True).start()

ES.lire()
eid = ES.lire()["actif"]
pr = port_libre()
tw = CP.creer({"espace_id": eid, "plateforme": "twitch", "libelle": "Fermé", "handle": "chaine",
               "valeurs": {"TWITCH_SERVEUR": "rtmp://127.0.0.1:1/app", "TWITCH_STREAM_KEY": CLE}})["id"]
rt = CP.creer({"espace_id": eid, "plateforme": "rtmp", "libelle": "Récepteur local",
               "valeurs": {"RTMP_SERVEUR": f"rtmp://127.0.0.1:{pr}/live", "RTMP_CLE": "cle-locale"}})["id"]
dc = CP.creer({"espace_id": eid, "plateforme": "discord", "libelle": "Salon",
               "valeurs": {"DISCORD_WEBHOOK": f"http://127.0.0.1:{pd}/api/webhooks/42/jetonlocal"}})["id"]

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("[1] ouvrir")
    g0, g1 = c.get("/api/comptes"), c.get("/api/comptes?live=1")
    check("R1.1 /api/comptes : sans live=1, ni comptes ni plateformes live ; avec, seulement eux",
          not ({x["plateforme"] for x in g0.json()["comptes"]} & CP.LIVE) and not (set(g0.json()["plateformes"]) & CP.LIVE)
          and {x["id"] for x in g1.json()["comptes"]} == {tw, rt, dc} and set(g1.json()["plateformes"]) == CP.LIVE
          and CLE not in g1.text, g1.text[:300])
    r = c.post("/api/live/sessions", json={"comptes": [tw, rt], "titre": "Banc"})
    v = r.json()
    check("R1.2 ouvrir : 200, vue sans URL ni clé", r.status_code == 200 and CLE not in r.text and "cle-locale" not in r.text
          and [x["plateforme"] for x in v["destinations"]] == ["twitch", "rtmp"], r.text)
    rx = c.post("/api/live/sessions", json={"comptes": [dc]}, headers={"Accept-Language": "en"})
    check("R1.3 un compte Discord n'est pas une destination : 400 traduit", rx.status_code == 400
          and rx.json()["detail"] == "This account is not a live destination.", rx.text)
    check("R1.4 un second direct : 409", c.post("/api/live/sessions", json={"comptes": [rt]}).status_code == 409)
    lid = v["id"]

    print("[2] WebSocket : origine")
    refuse = False
    try:
        with c.websocket_connect(f"/api/live/sessions/{lid}/flux", headers={"origin": "https://mechant.example"}) as w:
            w.receive_text()
    except Exception:                                               # noqa: BLE001
        refuse = True
    check("R2.1 Origin étranger refusé, aucun ffmpeg lancé", refuse and L._SESSIONS[lid]["diffusion"] is None)
    refuse = False
    try:      # rebond DNS : Origin et Host concordent, mais Host n'est pas la boucle locale
        with c.websocket_connect(f"/api/live/sessions/{lid}/flux",
                                 headers={"host": "mechant.example:8796", "origin": "http://mechant.example:8796"}) as w:
            w.receive_text()
    except Exception:                                               # noqa: BLE001
        refuse = True
    check("R2.2 Host non local refusé (rebond DNS), aucun ffmpeg lancé", refuse and L._SESSIONS[lid]["diffusion"] is None)

    print("[3] WebSocket : flux réel")
    if not FF:
        check("R3.0 ffmpeg présent", False)
    else:
        src = _tmp / "src.webm"
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
                        "-f", "lavfi", "-i", "sine", "-t", "4", "-c:v", "libvpx", "-deadline", "realtime", "-b:v", "500k",
                        "-c:a", "libopus", str(src)], check=True, timeout=120)
        sortie = _tmp / "recu.flv"
        recep = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-listen", "1", "-i",
                                  f"rtmp://127.0.0.1:{pr}/live/cle-locale", "-c", "copy", str(sortie)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        etats = []
        try:
            time.sleep(1)
            with c.websocket_connect(f"/api/live/sessions/{lid}/flux", headers={"host": "127.0.0.1:8796", "origin": "http://127.0.0.1:8796"}) as w:
                octets = src.read_bytes()
                for i in range(0, len(octets), 16384):
                    w.send_bytes(octets[i:i + 16384])
                    time.sleep(0.02)
                check("R3.4 marqueur posé pendant le direct", c.post(f"/api/live/sessions/{lid}/marqueurs",
                                                                     json={"t": 2000, "libelle": "Démo"}).status_code == 200)
                a = c.post(f"/api/live/sessions/{lid}/annonce", json={"compte": dc, "texte": "En direct !"})
                check("R5.1 annonce sur le faux Discord : {ok, statut}, sans URL ; mentions coupées",
                      a.json() == {"ok": True, "statut": 204} and RECUS and RECUS[0][0] == "/api/webhooks/42/jetonlocal"
                      and RECUS[0][1]["allowed_mentions"] == {"parse": []}
                      and RECUS[0][1]["content"] == "En direct !\nhttps://www.twitch.tv/chaine", (a.text, RECUS))
                t0 = time.time()
                while time.time() - t0 < 20:
                    e = json.loads(w.receive_text())
                    etats.append(e)
                    if e.get("etat") == "en_direct" and e["destinations"] == ["panne", "ok"] and (e.get("images") or 0) > 60:
                        break
            diff = L._SESSIONS[lid]["diffusion"]
            time.sleep(0.5)
            recep.wait(timeout=20)
            dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(sortie)],
                                 capture_output=True, text=True).stdout.strip()
            check("R3.1 l'état revient par le WebSocket (en_direct, images/s)", etats and etats[-1]["etat"] == "en_direct"
                  and etats[-1]["type"] == "etat", etats[-1:] )
            check("R3.2 destination fermée en panne, récepteur ok", etats[-1]["destinations"] == ["panne", "ok"], etats[-1:])
            check("R3.3 le récepteur local a reçu une vidéo lisible", dur and float(dur) > 2, dur)
            check("R4.1 WebSocket fermé = ffmpeg fini, session « fini »", diff and not diff.vivant()
                  and L._SESSIONS[lid]["etat"] == "fini")
            check("R4.2 aucune clé dans l'état renvoyé", CLE not in json.dumps(etats) and "cle-locale" not in json.dumps(etats))
        finally:
            if recep.poll() is None:
                recep.kill()
    cap = C.creer({"mode": "app"})["id"]
    t = c.post(f"/api/live/sessions/{lid}/terminer", json={"capture_id": cap})
    f = C.racine() / cap / f"{cap}.dzlive.json"
    check("R4.3 terminer : .dzlive.json à côté de la capture, marqueur gardé, sans clé",
          t.status_code == 200 and f.is_file() and json.loads(f.read_text("utf-8"))["marqueurs"] == [{"t": 2000, "libelle": "Démo"}]
          and CLE not in f.read_text("utf-8") and "cle-locale" not in f.read_text("utf-8"), t.text)
    check("R4.4 journaux sans clé ni URL de destination", not any(CLE in x or "cle-locale" in x or "jetonlocal" in x for x in _JOURNAL))
    check("R4.5 direct inconnu : 404", c.get("/api/live/sessions/0123456789abcdef").status_code == 404)

sys.path.insert(0, str(_ICI))
import _jeton_appareil as _JA                                       # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    print("[6] hors machine locale")
    codes = [c2.post("/api/live/sessions", json={"comptes": [rt]}).status_code,
             c2.get(f"/api/live/sessions/{lid}").status_code,
             c2.post(f"/api/live/sessions/{lid}/marqueurs", json={"t": 1}).status_code,
             c2.post(f"/api/live/sessions/{lid}/annonce", json={"compte": dc}).status_code,
             c2.post(f"/api/live/sessions/{lid}/terminer", json={}).status_code,
             c2.delete(f"/api/live/sessions/{lid}").status_code]
    check("R6.1 403 partout", codes == [403] * 6, codes)
    refuse = False
    try:
        with c2.websocket_connect(f"/api/live/sessions/{lid}/flux") as w:
            w.receive_text()
    except Exception:                                               # noqa: BLE001
        refuse = True
    check("R6.2 WebSocket hors machine locale refusé", refuse)
srv.shutdown()
L.arreter_tout()
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
