# -*- coding: utf-8 -*-
"""Avatar live t168f (11/10/2026) — le Direct par fal (decart/lucy-2-5/realtime), la clé fal seule.

Relevé par l'essai réel du 11/10 (spec 2026-10-10-higgsfield-genjutsu-inventaire.md, section 10) et qui commande ce
banc : signalisation par un WebSocket fal en msgpack (entrée, ready, iceServers, offer/answer, icecandidate) ; la
fermeture du WebSocket ARRÊTE la génération, l'expiration d'un jeton non. Donc le backend tient ce WebSocket et
relaie : la clé ne va jamais à la page, la borne est tenue par le serveur, la durée facturée est MESURÉE par lui.

Aucun réseau : `avatar_live._ouvrir_fal` est remplacé par un fal simulé. Data-dir isolé, aucune clé réelle.
Run (depuis backend/) : & $PY tests/test_avatar_direct_fal.py"""
import asyncio, base64, io, json, os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdirectfal_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("DECART_API_KEY", "FAL_KEY"):
    os.environ.pop(k, None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
import msgpack                                                      # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def png(w=300, h=300):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (w, h), (200, 80, 40)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


class FauxFal:
    """Le WebSocket fal simulé : décode ce qu'on lui envoie, répond comme le vrai (relevé du 11/10)."""
    ouverts = []

    def __init__(self, refus=None):
        self.recus, self.ferme, self.refus, self.q = [], False, refus, None
        self.boucle = asyncio.get_running_loop()
        FauxFal.ouverts.append(self)

    def _file(self):
        if self.q is None:
            self.q = asyncio.Queue()
        return self.q

    async def send(self, b):
        m = msgpack.unpackb(b)
        self.recus.append(m)
        q = self._file()
        if "prompt" in m and len([x for x in self.recus if "prompt" in x]) == 1:
            for r in ({"type": "x-fal-message", "action": "timings", "timing": 0.0},
                      {"type": "ready", "sdp": None, "candidate": None, "iceServers": None, "error": None},
                      {"type": "iceServers", "sdp": None, "candidate": None, "error": None,
                       "iceServers": [{"urls": "stun:stun.l.google.com:19302"}]}):
                await q.put(msgpack.packb(r))
        elif m.get("type") == "offer":
            if self.refus:
                await q.put(msgpack.packb({"type": "error", "sdp": None, "candidate": None, "iceServers": None,
                                           "error": self.refus}))
                return
            await q.put(msgpack.packb({"type": "answer", "sdp": "v=0 réponse", "candidate": None, "iceServers": None,
                                       "error": None}))
            await q.put(msgpack.packb({"type": "icecandidate", "candidate": {"candidate": "candidate:1 1 udp 1 1.2.3.4 9 typ srflx",
                                                                              "sdpMid": "0", "sdpMLineIndex": 0}}))
            await q.put(msgpack.packb({"type": "x-fal-message", "action": "timings", "timing": 2.0}))

    async def recv(self):
        b = await self._file().get()
        if b is None:
            raise ConnectionError("fermé")
        return b

    async def close(self):
        self.ferme = True
        await self._file().put(None)


from fastapi.testclient import TestClient                           # noqa: E402
from starlette.websockets import WebSocketDisconnect               # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import avatar_live as AL, pricing, plafonds       # noqa: E402

_MODE = {"refus": None, "panne": False}


async def _faux_ouvrir():
    if _MODE["panne"]:
        raise OSError("hôte injoignable")
    return FauxFal(_MODE["refus"])
AL._ouvrir_fal = _faux_ouvrir


def lignes(ref):
    async def lire():
        from sqlalchemy import select
        from app.services.storage import Depense
        async with plafonds._registre() as s:
            return [(l.moteur, l.estime_usd, l.reel_usd, l.reel_unites) for l in
                    (await s.execute(select(Depense).where(Depense.ref == ref))).scalars().all()]
    return asyncio.run(lire())


def recevoir_jusqua(ws, types, n=12):
    vus = []
    for _ in range(n):
        m = ws.receive_json()
        vus.append(m)
        if m.get("type") in types:
            break
    return vus


print("\n[P] le prix")
d = pricing.estimate({"kind": "direct", "seconds": 300, "fournisseur": "fal"})
check("P1 300 s de Lucy 2.5 par fal = 6,00 $ chez fal (0,02 $/s, llms.txt du 11/10)",
      abs(d["total_usd"] - 6.0) < 1e-6 and d["breakdown"][0]["provider"] == "fal", str(d))
d2 = pricing.estimate({"kind": "direct", "seconds": 300})
check("P2 sans fournisseur : Decart, comme avant (aucun Direct existant ne change de moteur)",
      d2["breakdown"][0]["provider"] == "decart")
check("P3 pas de mode rapide chez fal : le prix ne double pas",
      abs(pricing.estimate({"kind": "direct", "seconds": 300, "fournisseur": "fal", "rapide": True})["total_usd"] - 6.0) < 1e-6)

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    print("\n[F] le choix du fournisseur")
    e = loc.get("/api/avatar-live/etat").json()
    check("F1 aucune clé : aucun fournisseur, pas de défaut", e["fournisseurs"] == {"decart": False, "fal": False, "defaut": None}, str(e))
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True}).json()["id"]
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60})
    check("F2 aucune clé : 409 qui nomme les DEUX clés, rien de réservé",
          r.status_code == 409 and "FAL_KEY" in r.text and "DECART_API_KEY" in r.text and not FauxFal.ouverts, r.text[:200])
    settings.FAL_KEY = "fal_cle_permanente_secrete"
    e = loc.get("/api/avatar-live/etat")
    check("F3 la clé fal seule : fal par défaut, la valeur n'apparaît jamais",
          e.json()["fournisseurs"] == {"decart": False, "fal": True, "defaut": "fal"} and "secrete" not in e.text
          and abs(e.json()["prix_fal_usd_s"] - 0.02) < 1e-9)
    settings.DECART_API_KEY = "dct_x"
    check("F4 les deux clés : Decart par défaut (mode rapide, borne chez Decart)",
          loc.get("/api/avatar-live/etat").json()["fournisseurs"]["defaut"] == "decart")
    settings.DECART_API_KEY = ""
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60, "fournisseur": "decart"})
    check("F5 Decart demandé sans sa clé : 409, rien de réservé", r.status_code == 409 and "DECART_API_KEY" in r.text, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60, "fournisseur": "fal", "rapide": True})
    check("F6 mode rapide chez fal : 400 qui le dit", r.status_code == 400 and "rapide" in r.text, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60, "fournisseur": "openai"})
    check("F7 fournisseur inconnu : 400", r.status_code == 400, r.text[:200])

    print("\n[S] la réservation : garde des plafonds, aucune clé vers la page")
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 120})
    s1 = r.json()
    check("S1 fal par défaut : la session rend un relais, AUCUN jeton ni clé",
          r.status_code == 200 and s1.get("fournisseur") == "fal" and s1["relais"].startswith("/api/avatar-live/fal/relais?jeton=")
          and "jeton" not in s1 and "secrete" not in r.text and s1["modele"] == "decart/lucy-2-5/realtime", r.text[:300])
    check("S2 réserver n'ouvre RIEN chez fal (le relais le fera)", not FauxFal.ouverts)
    lg = lignes(f"fal-direct:{s1['session_id']}")
    check("S3 la réservation est au registre : moteur fal, 120 s × 0,02 = 2,40 $ estimés, pas de réel",
          lg == [("fal", 2.4, None, None)], str(lg))
    plafonds.enregistrer({"par_moteur": {"fal": 5.0}})
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 600})
    check("S4 12 $ demandés sous un plafond fal de 5 $ : 402 dz_plafond, aucun relais",
          r.status_code == 402 and "dz_plafond" in r.text and "relais" not in r.text, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})

    print("\n[R] le relais : signalisation, consigne à chaud, clé gardée au serveur")
    url = s1["relais"]
    with loc.websocket_connect(url) as ws:
        ws.send_json({"type": "etat", "prompt": "Swap the person for the character in the reference image, on a beach.",
                      "personnage_id": pid})
        vus = recevoir_jusqua(ws, ("iceServers",))
        fal = FauxFal.ouverts[-1]
        entree = fal.recus[0]
        ref = entree.get("reference_image_url") or ""
        from PIL import Image
        im = Image.open(io.BytesIO(base64.b64decode(ref.split(",", 1)[1]))) if ref.startswith("data:image/jpeg;base64,") else None
        check("R1 l'entrée part EN PREMIER : consigne + Personnage en data URI JPEG agrandie à 512 px (photo 300 px)",
              entree.get("prompt", "").startswith("Swap the person") and im is not None and min(im.size) >= 512
              and entree.get("enable_prompt_expansion") is True, str(entree)[:200])
        check("R2 la page reçoit ready puis iceServers, jamais les x-fal-message",
              [m.get("type") for m in vus] == ["ready", "iceServers"] and vus[1]["iceServers"][0]["urls"].startswith("stun:"), str(vus))
        ws.send_json({"type": "offer", "sdp": "v=0 offre", "pirate": "x"})
        ws.send_json({"type": "icecandidate", "candidate": {"candidate": "candidate:9 1 udp 1 10.0.0.2 5 typ host",
                                                             "sdpMid": "0", "sdpMLineIndex": 0, "usernameFragment": "zz"}})
        vus = recevoir_jusqua(ws, ("icecandidate",))
        check("R3 l'offre part telle quelle (sans champ étranger) ; la réponse et le candidat reviennent",
              {"type": "offer", "sdp": "v=0 offre"} in fal.recus and [m["type"] for m in vus] == ["answer", "icecandidate"]
              and vus[0]["sdp"] == "v=0 réponse", str(vus))
        cand = [m for m in fal.recus if m.get("type") == "icecandidate"]
        check("R4 un candidat ICE n'emporte que candidate/sdpMid/sdpMLineIndex",
              cand and set(cand[0]["candidate"]) == {"candidate", "sdpMid", "sdpMLineIndex"}, str(cand))
        ws.send_json({"type": "etat", "prompt": "Turn the whole scene into a watercolor painting.", "personnage_id": None})
        t0 = time.time()
        while len([m for m in fal.recus if "prompt" in m]) < 2 and time.time() - t0 < 3:
            time.sleep(0.02)
        chaud = [m for m in fal.recus if "prompt" in m][-1]
        check("R5 consigne à chaud : l'état COMPLET (fal le remplace), sans Personnage = reference_image_url nul",
              chaud == {"prompt": "Turn the whole scene into a watercolor painting.", "reference_image_url": None,
                        "enable_prompt_expansion": True}, str(chaud)[:200])
        try:
            with loc.websocket_connect(url) as ws2:
                m2 = ws2.receive_json()
                try:
                    ws2.receive_json(); ferme2 = False
                except WebSocketDisconnect as x:
                    ferme2 = x.code == 4403
        except WebSocketDisconnect as x:      # un relais qui ACCEPTE le jeton attend la page, puis ferme (4408)
            m2, ferme2 = {"ferme": x.code}, False
        check("R6 le jeton du relais est à usage UNIQUE : un second branchement est refusé (4403), fal pas rouvert",
              m2.get("type") == "error" and ferme2 and len(FauxFal.ouverts) == 1, str(m2))
        time.sleep(0.3)
        r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s1["session_id"], "secondes": 999})
        f1 = r.json()
        check("R7 la fin : secondes MESURÉES par le serveur (la page en annonçait 999)",
              r.status_code == 200 and 0.2 < f1["secondes"] < 5 and f1.get("mesure") == "serveur"
              and abs(f1["reel_usd"] - round(f1["secondes"] * 0.02, 6)) < 1e-9, r.text[:200])
        fin = recevoir_jusqua(ws, ("fin",))
        check("R8 le relais coupe fal et le dit à la page (raison arret, même facture)",
              fin[-1].get("type") == "fin" and fin[-1].get("raison") == "arret" and fal.ferme
              and abs(fin[-1].get("secondes", -1) - f1["secondes"]) < 1e-9, str(fin))
    lg = lignes(f"fal-direct:{s1['session_id']}")
    check("R9 le réel est noté sur la ligne de la réservation", len(lg) == 1 and abs(lg[0][2] - f1["reel_usd"]) < 1e-9, str(lg))
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s1["session_id"], "secondes": 3})
    check("R10 une seconde fin rend la MÊME facture (aucun double compte)",
          r.status_code == 200 and r.json()["secondes"] == f1["secondes"] and r.json().get("deja_close") is True
          and len(lignes(f"fal-direct:{s1['session_id']}")) == 1, r.text[:200])
    pages = json.dumps(vus + fin + [s1], ensure_ascii=False)
    check("R11 la clé fal ne traverse jamais vers la page (ni réponse, ni relais)", "fal_cle_permanente" not in pages)
    src = (_ICI.parent / "app" / "services" / "avatar_live.py").read_text(encoding="utf-8")
    check("R12 le vrai fal est ouvert par le serveur, clé en EN-TÊTE (jamais dans l'URL)",
          '"Authorization": "Key " + settings.FAL_KEY.strip()' in src and "fal_jwt_token" not in src)

    print("\n[B] la borne et les fins subies")
    s2 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 10}).json()
    AL._SESSIONS[s2["session_id"]]["duree_s"] = 1          # 1 s au lieu de 10 : le banc n'attend pas
    import threading
    def garde_fou(sid, s=6.0):
        """Un banc qui ATTEND ne prouve rien : passé `s`, la session est close de force (raison « arret »)."""
        def coupe():
            r_ = (AL._SESSIONS.get(sid) or {}).get("relais") or {}
            if r_.get("arret") is not None:
                FauxFal.ouverts[-1].boucle.call_soon_threadsafe(r_["arret"].set)
        th = threading.Timer(s, coupe); th.daemon = True; th.start()
        return th
    with loc.websocket_connect(s2["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": pid})
        gf = garde_fou(s2["session_id"])
        t0 = time.time()
        fin = recevoir_jusqua(ws, ("fin",), n=20)
        dt = time.time() - t0
        gf.cancel()
    check("B1 la borne est tenue PAR LE SERVEUR : fal coupé à la durée réservée, la page le sait",
          fin[-1].get("raison") == "borne" and FauxFal.ouverts[-1].ferme and 0.8 < dt < 4 and fin[-1]["secondes"] <= 1.0, str(fin[-1]) + f" {dt:.2f}s")
    check("B2 la borne close la session : le réel est noté sans la page",
          s2["session_id"] not in AL._SESSIONS and lignes(f"fal-direct:{s2['session_id']}")[0][2] is not None)

    def attendre_reel(sid, s=3.0):
        t0 = time.time()
        while (lignes(f"fal-direct:{sid}")[0][2] is None) and time.time() - t0 < s:   # le réel ÉCRIT
            time.sleep(0.05)

    # la page se DÉCONNECTE (onglet fermé) sans que le serveur annule le gestionnaire (uvicorn ne l'annule pas)
    s3 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()
    with loc.websocket_connect(s3["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": None})
        recevoir_jusqua(ws, ("iceServers",))
        fal3 = FauxFal.ouverts[-1]
        ws.close(1001)                        # le message de déconnexion SEUL, le gestionnaire continue
        attendre_reel(s3["session_id"])
        ferme3, ouverte3 = fal3.ferme, s3["session_id"] in AL._SESSIONS
    check("B3 la page s'en va (onglet fermé) : fal est coupé AUSSITÔT et le réel noté",
          ferme3 and not ouverte3 and lignes(f"fal-direct:{s3['session_id']}")[0][2] is not None,
          f"ferme={ferme3} ouverte={ouverte3} lignes={lignes('fal-direct:' + s3['session_id'])}")
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s3["session_id"], "secondes": 50})
    check("B4 la fin envoyée APRÈS par la page rend la facture du relais (pas 404, pas 50 s)",
          r.status_code == 200 and r.json()["secondes"] < 5, r.text[:200])
    # le gestionnaire ANNULÉ (arrêt du serveur ; le TestClient annule à la sortie du bloc) : fal est coupé quand même
    s3b = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()
    with loc.websocket_connect(s3b["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": None})
        recevoir_jusqua(ws, ("iceServers",))
        fal3b = FauxFal.ouverts[-1]
    attendre_reel(s3b["session_id"])
    check("B3b gestionnaire annulé : la clôture protégée coupe fal et note le réel",
          fal3b.ferme and lignes(f"fal-direct:{s3b['session_id']}")[0][2] is not None,
          f"ferme={fal3b.ferme} lignes={lignes('fal-direct:' + s3b['session_id'])}")

    _MODE["refus"] = "Concurrent session limit reached."
    s4 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()
    with loc.websocket_connect(s4["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": None})
        recevoir_jusqua(ws, ("iceServers",))
        ws.send_json({"type": "offer", "sdp": "v=0"})
        er = recevoir_jusqua(ws, ("error",))
    _MODE["refus"] = None
    check("B5 le refus de fal (limite de sessions simultanées, relevé le 11/10) arrive à la page tel quel",
          er[-1] == {"type": "error", "error": "Concurrent session limit reached."}, str(er))
    time.sleep(0.3)
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s4["session_id"], "secondes": 20})
    check("B5b refus AVANT toute réponse SDP : 0 s et 0 $ (aucun flux n'a pu être généré ; relevé en preuve le 11/10)",
          r.status_code == 200 and r.json()["secondes"] == 0 and r.json()["reel_usd"] == 0, r.text[:200])

    _MODE["panne"] = True
    n0 = len(FauxFal.ouverts)
    s5 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()
    with loc.websocket_connect(s5["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": None})
        m = ws.receive_json()
    _MODE["panne"] = False
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s5["session_id"], "secondes": 60})
    check("B6 fal injoignable : la page le sait, la fin note 0 s et 0 $ (rien n'a pu être généré)",
          m.get("type") == "error" and "rien n'a été facturé" in m.get("error", "") and len(FauxFal.ouverts) == n0
          and r.json()["secondes"] == 0 and r.json()["reel_usd"] == 0, str(m) + r.text[:200])

    s6 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()
    AL._SESSIONS[s6["session_id"]]["relais"]["expire"] = time.time() - 1
    loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 10})
    lg = lignes(f"fal-direct:{s6['session_id']}")
    check("B7 une réservation jamais branchée (page fermée) est close à 0 $ réel à la réservation suivante",
          s6["session_id"] not in AL._SESSIONS and lg and lg[0][2] == 0.0, str(lg))
    with loc.websocket_connect(s6["relais"]) as ws:
        m = ws.receive_json()
    check("B8 son jeton ne branche plus rien", m.get("type") == "error")

    print("\n[M] le téléphone")
    s7 = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}).json()   # une session OUVERTE
    n7 = len(FauxFal.ouverts)
    with lan.websocket_connect("/api/avatar-live/fal/relais?jeton=faux") as ws:
        m = ws.receive_json()
    check("M1 depuis le Wi-Fi, un faux jeton est refusé même quand une session attend son relais",
          m.get("type") == "error" and len(FauxFal.ouverts) == n7 and not AL._SESSIONS[s7["session_id"]]["relais"]["pris"], str(m))
    with lan.websocket_connect(s7["relais"]) as ws:
        ws.send_json({"type": "etat", "prompt": "x", "personnage_id": None})
        vus7 = recevoir_jusqua(ws, ("iceServers",))
    check("M2 le téléphone branche SON relais par le jeton reçu (aucun en-tête : pas de middleware HTTP sur un WS)",
          vus7[-1].get("type") == "iceServers", str(vus7))

    print("\n[A] le recensement des routes payantes")
    import _recensement_payant as RP
    rec = RP.recenser()
    k = ("avatar_live", "WS", "/fal/relais")
    check("A1 le relais WebSocket est recensé et atteint un puits (relayer_fal)", k in rec and "relayer_fal" in rec[k]["puits"], str(rec.get(k)))
    check("A2 la réservation (POST /sessions) reste gardée", rec[("avatar_live", "POST", "/sessions")]["garde"])

print("\n[J] la page : direct-fal.js sous node (WebSocket et RTCPeerConnection simulés)")
_FRONT = _ICI.parents[1] / "frontend" / "avatar"
HARNAIS = r"""
import { connecterFal } from "MODULE";
const journal = [];
class FauxWS {
  constructor(url) { this.url = url; this.readyState = 0; this.envoyes = []; FauxWS.dernier = this; setTimeout(() => { this.readyState = 1; this.onopen && this.onopen(); }, 0); }
  send(t) { this.envoyes.push(JSON.parse(t)); }
  close(c) { if (this.readyState === 3) return; this.readyState = 3; this.ferme = c; setTimeout(() => this.onclose && this.onclose({ code: c || 1000 }), 0); }
  recoit(m) { return this.onmessage({ data: JSON.stringify(m) }); }
  coupe(code) { this.readyState = 3; this.onclose && this.onclose({ code }); }
}
class FauxPC {
  constructor(cfg) { this.cfg = cfg; this.pistes = []; this.ajoutes = []; FauxPC.dernier = this; }
  addTrack(t) { this.pistes.push(t); }
  async createOffer() { return { type: "offer", sdp: "v=0 offre" }; }
  async setLocalDescription() {}
  async setRemoteDescription(d) { this.distante = d; }
  async addIceCandidate(c) { this.ajoutes.push(c); }
  close() { this.ferme = true; }
}
const flux = { getTracks: () => ["piste-video"] };
const opts = (o) => Object.assign({ relais: "/api/avatar-live/fal/relais?jeton=abc", etat: { prompt: "p1", personnage_id: "0123456789abcdef" },
  FabriqueWS: FauxWS, FabriquePC: FauxPC, origine: { protocol: "http:", host: "127.0.0.1:8799" }, delaiIceMs: 30, delaiReponseMs: 400 }, o || {});
const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
const res = {};
// 1. le chemin nominal
let recu = null;
const p = connecterFal(flux, opts({ onRemoteStream: (f) => { recu = f; } }));
await attendre(5);
const ws = FauxWS.dernier;
res.url = ws.url; res.premier = ws.envoyes[0];
await ws.recoit({ type: "ready" });
await ws.recoit({ type: "iceServers", iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
await attendre(5);
res.ice = FauxPC.dernier.cfg; res.offre = ws.envoyes[1];
await ws.recoit({ type: "icecandidate", candidate: { candidate: "c-avant" } });
await ws.recoit({ type: "answer", sdp: "v=0 réponse" });
const api = await p;
res.distante = FauxPC.dernier.distante; res.ajoutes = FauxPC.dernier.ajoutes.slice();
FauxPC.dernier.onicecandidate({ candidate: { candidate: "c-local", sdpMid: "0", sdpMLineIndex: 0, usernameFragment: "x" } });
res.candidatLocal = ws.envoyes[ws.envoyes.length - 1];
await api.set({ prompt: "p2", personnage_id: null });
res.chaud = ws.envoyes[ws.envoyes.length - 1];
FauxPC.dernier.ontrack({ streams: ["flux-sortie"] });
res.sortie = recu;
let fin = null; api.on("sessionEnded", (e) => { fin = e; });
await ws.recoit({ type: "fin", raison: "borne", secondes: 9.5, reel_usd: 0.19 });
res.fin = fin; res.wsFerme = ws.ferme; res.pcFerme = FauxPC.dernier.ferme;
// 2. un refus de fal avant la réponse
const p2 = connecterFal(flux, opts());
await attendre(5);
await FauxWS.dernier.recoit({ type: "error", error: "Concurrent session limit reached." });
try { await p2; res.refus = "résolu ?!"; } catch (e) { res.refus = { cle: e.cle, vars: e.vars }; }
// 3. le relais fermé avant la réponse
const p3 = connecterFal(flux, opts());
await attendre(5);
FauxWS.dernier.coupe(4403);
try { await p3; res.coupe = "résolu ?!"; } catch (e) { res.coupe = { cle: e.cle, vars: e.vars }; }
// 4. ready sans serveurs ICE : le secours STUN après le délai
const p4 = connecterFal(flux, opts());
await attendre(5);
await FauxWS.dernier.recoit({ type: "ready" });
await attendre(60);
res.secours = FauxPC.dernier.cfg; res.offreSecours = FauxWS.dernier.envoyes[1];
// 5. pas de réponse : délai
try { await p4; res.delai = "résolu ?!"; } catch (e) { res.delai = { cle: e.cle, vars: e.vars }; }
console.log(JSON.stringify(res));
"""
_h = _tmp / "harnais_fal.mjs"
_h.write_text(HARNAIS.replace("MODULE", (_FRONT / "direct-fal.js").as_uri()), encoding="utf-8")
import subprocess                                                   # noqa: E402
_r = subprocess.run(["node", str(_h)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    J = json.loads(_r.stdout.strip().splitlines()[-1])
except Exception:  # noqa: BLE001
    J = {}
check("J0 le module se charge et le harnais finit", bool(J), (_r.stdout + _r.stderr)[-600:])
if J:
    check("J1 la page ne parle qu'au serveur (ws://hôte/relais) et envoie l'état EN PREMIER",
          J["url"] == "ws://127.0.0.1:8799/api/avatar-live/fal/relais?jeton=abc"
          and J["premier"] == {"type": "etat", "prompt": "p1", "personnage_id": "0123456789abcdef"}, str(J.get("premier")))
    check("J2 iceServers de fal -> le pair WebRTC, puis l'offre", J["ice"] == {"iceServers": [{"urls": "stun:stun.l.google.com:19302"}]}
          and J["offre"] == {"type": "offer", "sdp": "v=0 offre"}, str(J.get("offre")))
    check("J3 la réponse est posée ; un candidat reçu AVANT elle est ajouté après",
          J["distante"] == {"type": "answer", "sdp": "v=0 réponse"} and J["ajoutes"] == [{"candidate": "c-avant"}], str(J.get("ajoutes")))
    check("J4 un candidat local part avec ses trois champs seulement",
          J["candidatLocal"] == {"type": "icecandidate", "candidate": {"candidate": "c-local", "sdpMid": "0", "sdpMLineIndex": 0}})
    check("J5 consigne à chaud = l'état complet", J["chaud"] == {"type": "etat", "prompt": "p2", "personnage_id": None})
    check("J6 la sortie transformée arrive à la page", J["sortie"] == "flux-sortie")
    check("J7 la fin du serveur (borne) : sessionEnded avec la mesure, tout est fermé",
          J["fin"] == {"reason": "borne", "secondes": 9.5, "reel_usd": 0.19} and J["wsFerme"] == 1000 and J["pcFerme"] is True, str(J.get("fin")))
    check("J8 refus de fal : l'ouverture échoue avec une clé du dictionnaire et la raison de fal",
          J["refus"] == {"cle": "avatar.direct.fal_refus", "vars": {"raison": "Concurrent session limit reached."}}, str(J.get("refus")))
    check("J9 relais fermé avant la réponse : échec avec son code", J["coupe"] == {"cle": "avatar.direct.fal_relais_ferme", "vars": {"code": 4403}}, str(J.get("coupe")))
    check("J10 ready sans serveurs ICE : le STUN de secours après le délai, puis l'offre",
          J["secours"] == {"iceServers": [{"urls": "stun:stun.l.google.com:19302"}]} and J["offreSecours"]["type"] == "offer", str(J.get("secours")))
    check("J11 pas de réponse SDP dans le délai : échec explicite", J["delai"] == {"cle": "avatar.direct.fal_sans_reponse", "vars": {"s": 0.4}}, str(J.get("delai")))
    av = json.loads((_ICI.parents[1] / "frontend" / "shared" / "i18n" / "avatar.json").read_text(encoding="utf-8"))
    import re as _re
    cles = set(_re.findall(r'"(avatar\.direct\.[a-z_]+)"', (_FRONT / "direct-fal.js").read_text(encoding="utf-8")))
    check("J12 les clés d'erreur du module sont au dictionnaire, en français et en anglais",
          cles and all(c in av and av[c]["fr"] and av[c]["en"] for c in cles), str(cles))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
