# -*- coding: utf-8 -*-
"""t318 (28/10/2026) (D4, tâches 1 et 2) — banc des destinations du direct (comptes.py) et du service live.py.
Plan docs/superpowers/plans/2026-10-28-t318-live.md, spec boîte à outils §8.6.
Sections :
  [P] plateformes live dans comptes.py : 4 positions, hors historiques, hors canaux (lister par défaut, /api/comptes
      sans live=1), jamais cible d'un post ;
  [S] service : serveur RTMP validé (séparateurs de tee refusés), masque des clés, destinations (espace, clé,
      serveur par défaut, lien public), commande ffmpeg (un encodage, tee onfail=ignore), sessions (une à la fois,
      marqueurs bornés), annonce Discord (webhook validé, sans mention, sans URL en retour), terminer (.dzlive.json
      sans secret) ;
  [F] ffmpeg RÉEL : une destination fermée + un récepteur local `-listen 1` ; la destination fermée est « panne », le
      récepteur reçoit une vidéo lisible, l'erreur est masquée, le processus est fini après fermer().
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau hors boucle locale.
Run (depuis backend/) : & $PY tests/test_live_service.py"""
import asyncio, json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlive_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.pop("DZ_LIVE_PREUVE", None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


from app.services import comptes as CP, espaces as ES, live as L, capture as C   # noqa: E402


def refus(f, statut):
    try:
        f()
    except L.RefusLive as e:
        return e.statut == statut
    return False


ES.lire()
rip = ES.creer({"nom": "Rippled"})["id"]
autre = ES.creer({"nom": "Autre"})["id"]
CLE_T = "live_123456_SECRETTWITCHabc"
CLE_Y = "abcd-efgh-SECRET-ijkl"

print("[P] plateformes live")
check("P1 4 positions, LIVE = twitch, youtube_live, kick, rtmp, discord", all(len(v) == 4 for v in CP.PLATEFORMES.values())
      and CP.LIVE == {"twitch", "youtube_live", "kick", "rtmp", "discord"} and CP.LIVE <= set(CP.PLATEFORMES))
check("P2 clés de stream et webhook SECRETS, serveurs et liens publics",
      dict(CP.PLATEFORMES["twitch"][1]) == {"TWITCH_STREAM_KEY": True, "TWITCH_SERVEUR": False}
      and dict(CP.PLATEFORMES["discord"][1]) == {"DISCORD_WEBHOOK": True}
      and dict(CP.PLATEFORMES["rtmp"][1])["RTMP_CLE"] is True and dict(CP.PLATEFORMES["kick"][1])["KICK_STREAM_KEY"] is True)
check("P3 aucune historique ni publication pour LIVE", CP.LIVE <= CP.SANS_HISTORIQUE and CP.LIVE <= CP.NON_PUBLIABLES)
tw = CP.creer({"espace_id": rip, "plateforme": "twitch", "libelle": "Ma chaîne", "handle": "rippled_tv",
               "valeurs": {"TWITCH_STREAM_KEY": CLE_T}})["id"]
x = CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "X"})["id"]
check("P4 lister() par défaut sans destination du direct ; lister(live=True) seulement elles",
      [v["id"] for v in CP.lister(rip)] == [x] and [v["id"] for v in CP.lister(rip, live=True)] == [tw]
      and all(v["plateforme"] not in CP.LIVE for v in CP.lister()))


def _ve(eid, ids):
    try:
        CP.verifier_cibles(eid, ids)
    except ValueError as e:
        return "direct" in str(e)
    return False


check("P5 un compte live n'est jamais une cible de post", lambda: _ve(rip, [tw]))
check("P6 la vue d'un compte live ne porte jamais la clé", CLE_T not in json.dumps(CP.lister(rip, live=True))
      and CLE_T not in (_tmp / "espaces" / "comptes.json").read_text("utf-8"))

print("[S] service")
check("S1 serveur valide gardé (sans / final)", L.valider_serveur("rtmps://ingest.example.com:443/app/") == "rtmps://ingest.example.com:443/app")
check("S2 serveurs piégés refusés (tee, guillemet, espace, autre schéma, vide)",
      all(refus(lambda u=u: L.valider_serveur(u), 400) for u in
          ["rtmp://a/b|[f=flv]file:x.flv", "rtmp://a/[x]", "http://a/b", "rtmp://a b/c", "rtmp://a/b'c", "", None,
           "file:out.flv", "rtmp:///x", "rtmp://a/b\\c"]))
err = f"[tee @ 0x1] Slave '[f=flv:onfail=ignore]rtmp://h.example/app/{CLE_T}': error opening ; cle%3Dabc"
m = L.masquer(err, [CLE_T, "cle=abc"])
check("S3 masque : la clé, sa forme %-codée et le dernier segment d'une URL rtmp disparaissent",
      CLE_T not in m and "SECRET" not in m and "cle%3Dabc" not in m and "rtmp://h.example/app/••••" in m, m)
check("S3b masque sans secret connu : le dernier segment d'une URL rtmp disparaît",
      L.masquer("rtmps://x.y/app/sk_us-west_ABC def") == "rtmps://x.y/app/•••• def")
d = L.destinations(rip, [tw])
check("S4 destination Twitch : serveur par défaut + clé, lien public d'après le handle",
      d[0]["url"] == "rtmp://live.twitch.tv/app/" + CLE_T and d[0]["lien"] == "https://www.twitch.tv/rippled_tv"
      and d[0]["plateforme"] == "twitch", d)
yt = CP.creer({"espace_id": rip, "plateforme": "youtube_live", "libelle": "YT",
               "valeurs": {"YOUTUBE_STREAM_KEY": CLE_Y, "YOUTUBE_LIVE_LIEN": "https://youtube.com/live/abc"}})["id"]
kk = CP.creer({"espace_id": rip, "plateforme": "kick", "libelle": "Kick", "valeurs": {"KICK_STREAM_KEY": "sk_k"}})["id"]
rt = CP.creer({"espace_id": rip, "plateforme": "rtmp", "libelle": "Perso",
               "valeurs": {"RTMP_SERVEUR": "rtmp://127.0.0.1:1935/live|[f=flv]x"}})["id"]
tw2 = CP.creer({"espace_id": autre, "plateforme": "twitch", "libelle": "T2", "valeurs": {"TWITCH_STREAM_KEY": "k2"}})["id"]
twv = CP.creer({"espace_id": rip, "plateforme": "twitch", "libelle": "Sans clé"})["id"]
check("S5 YouTube Live : serveur par défaut, lien public posé", L.destinations(rip, [yt])[0]["url"]
      == "rtmp://a.rtmp.youtube.com/live2/" + CLE_Y and L.destinations(rip, [yt])[0]["lien"] == "https://youtube.com/live/abc")
check("S6 refus : autre espace 409, compte non-live 400, inconnu 404, sans clé 400, Kick sans serveur 400, serveur piégé 400, liste vide 400",
      refus(lambda: L.destinations(rip, [tw2]), 409) and refus(lambda: L.destinations(rip, [x]), 400)
      and refus(lambda: L.destinations(rip, ["c00000000"]), 404) and refus(lambda: L.destinations(rip, [twv]), 400)
      and refus(lambda: L.destinations(rip, [kk]), 400) and refus(lambda: L.destinations(rip, [rt]), 400)
      and refus(lambda: L.destinations(rip, []), 400))
cmd = L.commande(["rtmp://a/app/k1", "rtmps://b/app/k2"])
check("S7 commande : entrée pipe, UN encodage x264 zerolatency GOP 2 s + AAC, tee onfail=ignore par sortie",
      cmd[cmd.index("-i") + 1] == "pipe:0" and cmd.count("-c:v") == 1 and "zerolatency" in cmd
      and cmd[cmd.index("-g") + 1] == "60" and cmd[cmd.index("-f", cmd.index("-flags")) + 1] == "tee"
      and cmd[-1] == "[f=flv:onfail=ignore]rtmp://a/app/k1|[f=flv:onfail=ignore]rtmps://b/app/k2", cmd)


class FauxProc:
    def __init__(self, *a, **k):
        import io
        self.stdin, self.stdout, self.stderr = io.BytesIO(), io.BytesIO(b"frame=30\nfps=30.0\ndrop_frames=2\nspeed=1.01x\nprogress=continue\n"), \
            io.BytesIO(f"[tee @ 1] Slave '[f=flv:onfail=ignore]rtmp://live.twitch.tv/app/{CLE_T}': error opening\n[tee @ 1] Slave muxer #0 failed: x\n".encode())
        self.stdin.flush = lambda: None
        self.code = None
        self.cmd = a[0] if a else None
    def poll(self): return self.code
    def wait(self, timeout=None): self.code = 0; return 0
    def kill(self): self.code = -9


s = L.ouvrir(rip, [tw, yt], "Mon direct")
check("S8 ouvrir : vue publique sans URL ni clé, état prêt", s["etat"] == "pret" and CLE_T not in json.dumps(s)
      and "url" not in s["destinations"][0] and s["destinations"][0]["lien"] == "https://www.twitch.tv/rippled_tv")
check("S9 un seul direct à la fois (409)", refus(lambda: L.ouvrir(rip, [tw]), 409))
diff = L.brancher(s["id"], lancer=FauxProc)
time.sleep(0.3)
e = diff.etat()
check("S10 santé : images, fps, perdues, vitesse ; destination #0 en panne, #1 ok ; erreur masquée",
      e["etat"] == "en_direct" and e["fps"] == 30.0 and e["images_perdues"] == 2 and e["vitesse"] == 1.01
      and e["destinations"] == ["panne", "ok"] and CLE_T not in json.dumps(e) and e["erreur"], e)
check("S11 brancher deux fois : 409", refus(lambda: L.brancher(s["id"], lancer=FauxProc), 409))
check("S12 marqueurs : posés, instant invalide 400", L.marquer(s["id"], 1500, "Intro")["t"] == 1500
      and refus(lambda: L.marquer(s["id"], -1), 400) and refus(lambda: L.marquer(s["id"], "x"), 400))
dc = CP.creer({"espace_id": rip, "plateforme": "discord", "libelle": "Salon",
               "valeurs": {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/123456789/" + "T" * 40}})["id"]
dcl = CP.creer({"espace_id": rip, "plateforme": "discord", "libelle": "Local",
                "valeurs": {"DISCORD_WEBHOOK": "http://127.0.0.1:59999/api/webhooks/1/abcd"}})["id"]
recu = []


async def poster(url, corps):
    recu.append((url, corps))
    return 204


r = asyncio.run(L.annoncer(s["id"], dc, "On est en direct", poster=poster))
check("S13 annonce : texte + liens publics, aucune mention, réponse sans URL",
      r == {"ok": True, "statut": 204} and recu[0][1]["allowed_mentions"] == {"parse": []}
      and recu[0][1]["content"] == "On est en direct\nhttps://www.twitch.tv/rippled_tv\nhttps://youtube.com/live/abc", recu)
check("S14 webhook local refusé hors preuve, accepté en preuve ; compte non-discord 400",
      refus(lambda: asyncio.run(L.annoncer(s["id"], dcl, "x", poster=poster)), 400)
      and refus(lambda: asyncio.run(L.annoncer(s["id"], tw, "x", poster=poster)), 400))
os.environ["DZ_LIVE_PREUVE"] = "1"
check("S14a une seule annonce par direct (409 à la seconde)", refus(lambda: asyncio.run(L.annoncer(s["id"], dc, "x", poster=poster)), 409))
L._SESSIONS[s["id"]]["annonce"] = None
check("S14b en preuve, webhook 127.0.0.1 accepté", asyncio.run(L.annoncer(s["id"], dcl, "x", poster=poster))["ok"])
os.environ.pop("DZ_LIVE_PREUVE")
cap = C.creer({"mode": "app"})["id"]
fin = L.terminer(s["id"], cap)
f = C.racine() / cap / f"{cap}.dzlive.json"
doc = json.loads(f.read_text("utf-8")) if f.is_file() else {}
check("S15 terminer : ffmpeg fermé, .dzlive.json écrit à côté de la capture, sans secret",
      fin["fichier"] == f"{cap}.dzlive.json" and doc.get("marqueurs") == [{"t": 1500, "libelle": "Intro"}]
      and [x["etat"] for x in doc["destinations"]] == ["panne", "ok"] and CLE_T not in f.read_text("utf-8")
      and CLE_Y not in f.read_text("utf-8") and diff.ferme, doc)
check("S16 après terminer : marqueur 409, nouveau direct possible, capture inconnue 404",
      refus(lambda: L.marquer(s["id"], 1), 409) and refus(lambda: L.terminer(L.ouvrir(rip, [tw])["id"], "0" * 16), 404))
check("S17 après le direct, plus aucune URL ni clé en mémoire ; annonce refusée (409)",
      all(not x["url"] and not x["cle"] for x in L._SESSIONS[s["id"]]["destinations"])
      and refus(lambda: asyncio.run(L.annoncer(s["id"], dc, "x", poster=poster)), 409))
for lid in list(L._SESSIONS):
    L.abandonner(lid)

# revue finale I1 : une session ouverte mais jamais branchée expire (onglet fermé pendant le choix d'écran)
v1 = L.ouvrir(rip, [tw])
L._SESSIONS[v1["id"]]["t0"] -= L.PRET_MAX_S + 1
v2 = L.ouvrir(rip, [tw])
check("S18 session « pret » périmée : un nouveau direct s'ouvre, l'ancienne est close sans secret",
      L._SESSIONS[v1["id"]]["etat"] == "termine" and not L._SESSIONS[v1["id"]]["destinations"][0]["cle"]
      and L._SESSIONS[v2["id"]]["etat"] == "pret")


# revue finale C1 : une destination FIGÉE (ffmpeg ne lit plus son entrée) ne bloque ni l'appelant ni fermer()
class ProcFige(FauxProc):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        import io, threading as th
        self.debloque = th.Event()
        fige = self

        class Entree(io.BytesIO):
            def write(self, b):
                fige.debloque.wait(60)          # bloqué jusqu'au kill
                raise OSError("tube cassé")
        self.stdin = Entree()
        self.stdin.flush = lambda: None
        self.stdout, self.stderr = io.BytesIO(b""), io.BytesIO(b"")
    def wait(self, timeout=None):
        if self.code is None:
            self.debloque.wait(timeout)
            if self.code is None:
                import subprocess as sp
                raise sp.TimeoutExpired("ffmpeg", timeout)
        return self.code
    def kill(self):
        self.code = -9
        self.debloque.set()


L.BLOCAGE_S = 0.5
dg = L.brancher(v2["id"], lancer=ProcFige)
t0 = time.time()
r1 = dg.ecrire(b"x" * 10)
time.sleep(0.8)
r2 = dg.ecrire(b"y")
e = dg.etat()
L.debrancher(v2["id"])
duree_fermer = time.time() - t0
check("S19 écriture figée : ecrire() ne bloque pas, puis refuse ; état en_panne ; debrancher tue ffmpeg en moins de 7 s",
      r1 is True and r2 is False and e["etat"] == "en_panne" and dg.proc.code == -9 and duree_fermer < 7.5
      and L._SESSIONS[v2["id"]]["etat"] == "fini", (r1, r2, e, duree_fermer))
check("S20 brancher après la fin : 409 (aucun second ffmpeg)", refus(lambda: L.brancher(v2["id"], lancer=FauxProc), 409))
L.BLOCAGE_S = 10
for lid in list(L._SESSIONS):
    L.abandonner(lid)


# deux fermetures concurrentes (WebSocket fermé ET « terminer » du bilan) : la seconde attend la première, le bilan est complet
class ProcLent(FauxProc):
    def wait(self, timeout=None):
        time.sleep(1.0); self.code = 0; return 0


import threading as _th
v3 = L.ouvrir(rip, [tw])
L.brancher(v3["id"], lancer=ProcLent)
time.sleep(0.3)
a_ = _th.Thread(target=L.debrancher, args=(v3["id"],)); a_.start()
time.sleep(0.2)
cap3 = C.creer({"mode": "app"})["id"]
fin3 = L.terminer(v3["id"], cap3)
a_.join()
check("S21 fermetures concurrentes : terminer attend la fin de la première, bilan avec durée et états",
      fin3["live"]["duree_ms"] > 0 and fin3["live"]["destinations"][0]["etat"] != "attente", fin3["live"])
for lid in list(L._SESSIONS):
    L.abandonner(lid)

print("[F] ffmpeg réel (boucle locale)")
FF = shutil.which("ffmpeg")
if not FF:
    check("F0 ffmpeg présent sur la machine", False)
else:
    src = _tmp / "src.webm"
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "4", "-c:v", "libvpx", "-deadline", "realtime",
                    "-b:v", "500k", "-c:a", "libopus", str(src)], check=True, timeout=120)
    so = socket.socket(); so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]; so.close()
    sortie = _tmp / "recu.flv"
    recep = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-listen", "1", "-i",
                              f"rtmp://127.0.0.1:{port}/live/cle-locale", "-c", "copy", str(sortie)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        dfr = L.Diffusion([f"rtmp://127.0.0.1:1/app/{CLE_T}", f"rtmp://127.0.0.1:{port}/live/cle-locale"], [CLE_T], fps=30)
        octets = src.read_bytes()
        for i in range(0, len(octets), 16384):
            dfr.ecrire(octets[i:i + 16384])
            time.sleep(0.02)
        t0 = time.time()
        while time.time() - t0 < 20 and not (dfr.etat()["destinations"][0] == "panne" and (dfr.etat()["images"] or 0) > 60):
            time.sleep(0.2)
        e = dfr.etat()
        code = dfr.fermer()
        recep.wait(timeout=20)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(sortie)],
                             capture_output=True, text=True).stdout.strip()
        check("F1 destination fermée en panne, l'autre ok (onfail=ignore)", e["destinations"] == ["panne", "ok"], e)
        check("F2 le récepteur local a reçu une vidéo lisible (> 2 s)", dur and float(dur) > 2, dur)
        check("F3 erreurs masquées (aucune clé) et ffmpeg fini après fermer()",
              CLE_T not in json.dumps(dfr.erreurs) and dfr.erreurs and code is not None and not dfr.vivant(), dfr.erreurs)
    finally:
        if recep.poll() is None:
            recep.kill()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
