# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T12, D3b) — indexation et recherche : le client parle le contrat Clapbox à un VRAI serveur
HTTP stub (http.server dans un fil, pas un monkeypatch de la fonction qui parle), l'index sur disque est RELU
(banc-miroir : on lit le fichier, pas l'objet qui l'a écrit), la recherche ordonne, la similarité s'exclut, la
signature mtime:taille évite de repayer, un fichier effacé quitte l'index, un changement de modèle se dit. Les
routes passent AVANT /audio/{filename} (sinon « search » serait lu comme un nom de fichier). Le fichier d'index
lui-même n'est JAMAIS listé comme un son.
Run: python tests/test_sound_search_index.py (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
_tmp = tempfile.mkdtemp(prefix="dzclapix_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

# ── le stub : un vecteur orthogonal par « son », un vecteur texte qui pointe vers l'un d'eux. Pas de modèle :
#    de la géométrie qui se lit.
DIM = 4
AXES = {"porte.wav": [1, 0, 0, 0], "pluie.wav": [0, 1, 0, 0], "boom.wav": [0, 0, 1, 0]}
SEEN = {"text": [], "audio": [], "auth": []}
MODELE = {"nom": "stub-clap", "dim": DIM}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/health": self._send({"ok": True, "model": MODELE["nom"], "dim": MODELE["dim"]})
        else: self.send_response(404); self.end_headers()
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        SEEN["auth"].append(self.headers.get("Authorization"))
        if self.path == "/embed/text":
            txt = json.loads(body)["texts"]
            SEEN["text"] += txt
            v = [([1, 0, 0, 0] if "grince" in t else [0, 0, 0, 1]) + [0] * (MODELE["dim"] - DIM) for t in txt]
            self._send({"dim": MODELE["dim"], "model": MODELE["nom"], "vectors": v})
        elif self.path == "/embed/audio":
            names = [p.split(b'filename="', 1)[1].split(b'"', 1)[0].decode()
                     for p in body.split(b"--") if b'filename="' in p]
            SEEN["audio"] += names
            self._send({"dim": MODELE["dim"], "model": MODELE["nom"],
                        "vectors": [AXES.get(n, [0, 0, 0, 1]) + [0] * (MODELE["dim"] - DIM) for n in names]})
        else: self.send_response(404); self.end_headers()
srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
from app.config import settings
settings.CLAPBOX_URL = f"http://127.0.0.1:{srv.server_port}"
from app.services import sound_search as SS, sfx_service as S
SS._reach_cache.update(t=0.0, ok=False)

print("\n[1] l'indexation")
check("le stub est vu comme Clapbox (vrai GET /health)", SS.resolve_embedder() == "clapbox")
audio = S._audio_dir()
for n in AXES: (audio / n).write_bytes(b"RIFF" + n.encode() + b"\0" * 200)
(audio / "notes.txt").write_text("pas un son", encoding="utf-8")
settings.CLAP_REMOTE_KEY = "ne-doit-pas-partir"
r = asyncio.run(SS.reindex())
check("trois sons indexés (pas le .txt), dimension prise du service", r["indexed"] == 3 and r["dim"] == DIM
      and r["total"] == 3 and "notes.txt" not in SEEN["audio"], str(r))
doc = json.loads((audio / "_clap_index.json").read_text(encoding="utf-8"))
check("le FICHIER d'index porte dim, modèle, provider et trois items",
      doc["dim"] == DIM and doc["model"] == "stub-clap" and doc["provider"] == "clapbox" and set(doc["items"]) == set(AXES),
      str(doc)[:200])
check("chaque item porte sa signature mtime:taille", all(":" in doc["items"][n]["sig"] for n in AXES))
check("clé distante POSÉE mais service LOCAL : elle ne part pas", SEEN["auth"] == [None], str(SEEN["auth"]))
settings.CLAP_REMOTE_KEY = ""
r2 = asyncio.run(SS.reindex())
check("rien n'a bougé : 0 réindexé, 0 appel audio de plus",
      r2["indexed"] == 0 and r2["skipped"] == 3 and len(SEEN["audio"]) == 3, str(r2) + str(SEEN["audio"]))
(audio / "boom.wav").write_bytes(b"RIFF" + b"boom plus long" + b"\0" * 400)
r2b = asyncio.run(SS.reindex())
check("un son MODIFIÉ (taille) repasse, lui seul", r2b["indexed"] == 1 and SEEN["audio"][-1] == "boom.wav", str(r2b))

print("\n[2] chercher, comparer")
res = asyncio.run(SS.search("une porte qui grince", k=2))
check("par description : porte.wav en tête, score ≈ 1, k respecté",
      res[0]["name"] == "porte.wav" and res[0]["score"] > 0.99 and len(res) == 2 and res[0]["url"] == "/api/audio/porte.wav", str(res))
check("le texte est parti tel quel au service", SEEN["text"][-1] == "une porte qui grince", str(SEEN["text"]))
check("requête vide : rien, aucun appel", asyncio.run(SS.search("   ")) == [] and len(SEEN["text"]) == 1)
sim = asyncio.run(SS.similar("porte.wav", k=2))
check("similarité : le demandeur est EXCLU", all(x["name"] != "porte.wav" for x in sim) and len(sim) == 2, str(sim))

print("\n[3] ce qui bouge")
(audio / "pluie.wav").unlink()
r3 = asyncio.run(SS.reindex())
check("fichier effacé : retiré de l'index et DIT", r3["dropped"] == ["pluie.wav"] and SS.Index.load().count() == 2, str(r3))
check("un son absent de l'index : similar rend [], pas une erreur", asyncio.run(SS.similar("pluie.wav", k=3)) == [])
MODELE.update(nom="autre-clap", dim=8)
(audio / "neuf.wav").write_bytes(b"RIFF neuf" + b"\0" * 100)
try:
    asyncio.run(SS.reindex()); check("changement de dimension : refus nommé", False)
except SS.SearchUnavailable as e:
    check("changement de dimension du service : refus qui dit « tout réindexer »", "réindexe" in str(e).lower(), str(e))
r4 = asyncio.run(SS.reindex(force=True))
check("force=True : l'index repart dans la NOUVELLE dimension", r4["dim"] == 8 and r4["model"] == "autre-clap" and r4["total"] == 3, str(r4))
MODELE.update(nom="stub-clap", dim=DIM)
asyncio.run(SS.reindex(force=True))

print("\n[4] service coupé")
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False); settings.CLAP_REMOTE_URL = ""
try: asyncio.run(SS.search("porte", k=2)); check("service coupé : refus explicite", False)
except SS.SearchUnavailable as e: check("service coupé : refus explicite nommant Clapbox", "Clapbox" in str(e), str(e))
check("service coupé : similar reste servi depuis l'index (0 $)",
      [x["name"] for x in asyncio.run(SS.similar("porte.wav", k=1))] == ["boom.wav"])
from httpx import AsyncClient, ASGITransport
from app.main import app
async def routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        d = (await c.get("/api/audio/search/status")).json()
        check("GET /audio/search/status : indisponible, raison, compte", d["ready"] is False and d["indexed"] == 3
              and "Clapbox" in d["hint"], str(d))
        d = (await c.get("/api/audio/similar/porte.wav", params={"k": 1})).json()
        check("GET /audio/similar : servi sans service", d["items"][0]["name"] == "boom.wav", str(d))
        r4 = await c.get("/api/audio/search", params={"q": "porte"})
        check("GET /audio/search sans service : 503 lisible", r4.status_code == 503 and "Clapbox" in r4.json()["detail"], r4.text[:160])
        r5 = await c.post("/api/audio/search/index", json={})
        check("POST /audio/search/index sans service, RIEN de neuf : compte rendu 200, aucun appel",
              r5.status_code == 200 and r5.json()["indexed"] == 0, str(r5.status_code))
        (audio / "nouveau.wav").write_bytes(b"RIFF nouveau" + b"\0" * 64)
        r5b = await c.post("/api/audio/search/index", json={})
        check("POST /audio/search/index sans service, un son NEUF : 503 lisible", r5b.status_code == 503
              and "Clapbox" in r5b.json()["detail"], r5b.text[:160])
        (audio / "nouveau.wav").unlink()
        r6 = await c.get("/api/audio/similar/..%5Cevil.mp3")
        check("similar : nom à antislash refusé (400)", r6.status_code == 400, str(r6.status_code))
        vrai = SS.Index.load()
        grand = SS.Index(dim=DIM, model="stub-clap", provider="clapbox")
        for j in range(60):
            grand.put(f"g{j}.wav", [1.0, (j + 1) / 61.0, 0.0, 0.0], sig="0:0")
        grand.save()
        r7 = await c.get("/api/audio/similar/g0.wav", params={"k": 9999})
        check("similar : k borné à 50 (index de 60)", r7.status_code == 200 and len(r7.json()["items"]) == 50, str(len(r7.json().get("items", []))))
        vrai.save()
        lst = (await c.get("/api/audio")).json()
        noms = [a.get("name") for a in (lst.get("audio") or lst.get("items") or [])]
        check("GET /audio ne liste PAS l'index comme un son", "_clap_index.json" not in noms, str(noms))
        SS._reach = lambda url, timeout=2.0: True
        SS._reach_cache.update(t=0.0, ok=False)
        d = (await c.get("/api/audio/search", params={"q": "ça grince", "k": 1})).json()
        check("GET /audio/search avec service : porte.wav", [x["name"] for x in d["items"]] == ["porte.wav"], str(d))
        d = (await c.post("/api/audio/search/index", json={})).json()
        check("POST /audio/search/index : compte rendu (rien de neuf)", d.get("indexed") == 0 and d.get("total") == 3, str(d))
asyncio.run(routes())

print("\n[5] l'endpoint distant reçoit sa clé")
SS._reach = lambda url, timeout=2.0: False
SS._reach_cache.update(t=0.0, ok=False)
settings.CLAP_REMOTE_URL = f"http://127.0.0.1:{srv.server_port}"
settings.CLAP_REMOTE_KEY = "secret-xyz"
asyncio.run(SS.search("grince", k=1))
check("distant : Authorization Bearer posée", SEEN["auth"][-1] == "Bearer secret-xyz", str(SEEN["auth"][-1:]))
srv.shutdown()
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
