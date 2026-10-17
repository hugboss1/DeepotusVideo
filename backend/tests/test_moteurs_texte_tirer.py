# -*- coding: utf-8 -*-
"""t232 (Studio : Animation, 17/10/2026) — le moteur commun « tirer un texte ».

Plan docs/superpowers/plans/2026-10-17-studio-animation.md (t232), spec § B4. `vector_illustration.tirer` était le
seul endroit qui savait appeler UN moteur et UN modèle précis ; le chorégraphe (t234) en a besoin hors Vectorlab. Il
devient `moteurs_texte.tirer(moteur, modele, prompt, systeme, max_tokens, json=False)`, et le Vectorlab l'appelle sans
changement de comportement.

Zéro dépense : un FAUX OLLAMA écoute sur 127.0.0.1 (port tiré au hasard, jamais 8765) dans ce processus, un FAUX
FOURNISSEUR LIBRE répond en mémoire (transport httpx de `fournisseurs_llm`, DNS remplacé).
Ce que ce banc garde :
  [M] le module : `tirer`, `tirer_garde`, `estimer`, `nature_cout`, `extraire_json` existent ; `tirer` a `json=False` ;
  [O] Ollama intégré : POST /api/generate au modèle demandé (sinon `modele_sain`), système transmis ; json=True →
      `format: "json"` et un objet rendu ;
  [F] fournisseur libre fl:<id> : POST {base}/chat/completions au modèle choisi ; json=True → l'objet est extrait d'une
      réponse entourée de ``` ;
  [L] serveur local local:<id> (type ollama, sur le faux Ollama) : POST /api/chat ;
  [G] gardes : moteur inconnu, aucun modèle, modèle qui ressemble à une CLÉ (rien n'est envoyé), JSON illisible,
      réponse trop longue → RuntimeError ; une sortie n'est jamais évaluée ;
  [P] `tirer_garde` : estimation AVANT l'appel (op llm au moteur choisi, out_tok = max_tokens) ; plafond dépassé →
      402 et AUCUNE requête ; Ollama / local passent (gratuit) ; moteur non configuré → RuntimeError sans requête ;
  [C] nature de coût : ollama / local:<id> gratuit, fl:<id> a_mesurer, intégrés payant ;
  [V] Vectorlab : `vector_illustration.tirer` délègue (aucun appel HTTP dans son corps), même texte rendu ;
  [R] GET /api/motion/moteurs = etat() + `cout` par ligne ; 403 depuis un autre appareil.
Run (depuis backend/) : & $PY tests/test_moteurs_texte_tirer.py"""
import asyncio, inspect, json, os, pathlib, socket, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import fournisseurs_llm as FL                     # noqa: E402
from app.services import serveurs_locaux as SL                      # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import vector_illustration as VI                  # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402

CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "", "OLLAMA_MODEL": "",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


# ── le faux Ollama (un vrai serveur HTTP, dans ce processus) ───────────────────────────────────────────────────────
OLL = []                                    # (chemin, corps) reçus
OLL_REP = {"texte": "Réponse du faux Ollama."}


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _rendre(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/tags":
            return self._rendre(200, {"models": [{"name": "llama3"}, {"name": "qwen2.5:7b"}]})
        self._rendre(404, {})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        OLL.append((self.path, corps))
        txt = OLL_REP["texte"] + " [" + str(corps.get("model")) + "]"
        if self.path == "/api/generate":
            return self._rendre(200, {"response": txt, "done": True})
        if self.path == "/api/chat":
            return self._rendre(200, {"message": {"role": "assistant", "content": txt}, "done": True})
        self._rendre(404, {})


_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
PORT = _srv.server_address[1]
assert PORT != 8765
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL_OLL = f"http://127.0.0.1:{PORT}"

# ── le faux fournisseur libre (en mémoire) ────────────────────────────────────────────────────────────────────────
CLE = "sk-faussecle-banc-t232-0000000000"
REQ = []
FL_REP = {"texte": "Texte du faux fournisseur."}


def _faux(req: httpx.Request) -> httpx.Response:
    REQ.append(req)
    if req.headers.get("authorization") != f"Bearer {CLE}":
        return httpx.Response(401, json={"error": {"message": "clé refusée"}})
    if req.method == "GET" and req.url.path.endswith("/models"):
        return httpx.Response(200, json={"object": "list", "data": [{"id": "deepseek-chat"}]})
    if req.method == "POST" and req.url.path.endswith("/chat/completions"):
        corps = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant",
                                                                  "content": FL_REP["texte"].replace("{m}", corps["model"])}}]})
    return httpx.Response(404, json={})


FL._TRANSPORT = httpx.MockTransport(_faux)
FL._resoudre = lambda hote, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

c = TestClient(app)
c.__enter__()

# ── [M] le module ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[M] le module")
for nom in ("tirer", "tirer_garde", "estimer", "nature_cout", "extraire_json"):
    check(f"M1 moteurs_texte.{nom} existe", callable(getattr(MT, nom, None)))
if not callable(getattr(MT, "tirer", None)):
    print(f"\n{ok} PASS, {fail + 1} FAIL")
    sys.exit(1)
sig = inspect.signature(MT.tirer)
check("M2 signature (moteur, modele, prompt, systeme, max_tokens, json=False)",
      list(sig.parameters)[:6] == ["moteur", "modele", "prompt", "systeme", "max_tokens", "json"]
      and sig.parameters["json"].default is False, str(sig))
check("M3 tirer_garde est une coroutine", inspect.iscoroutinefunction(getattr(MT, "tirer_garde", None)))

# ── [O] Ollama intégré ────────────────────────────────────────────────────────────────────────────────────────────
print("[O] Ollama intégré")
CAC.appliquer({"OLLAMA_MODEL": "llama3"})
settings.OLLAMA_URL = URL_OLL
OLL.clear()
t = MT.tirer("ollama", "", "Bonjour", "Tu es bref.", 200)
check("O1 texte rendu par le faux Ollama, modèle par défaut", t == "Réponse du faux Ollama. [llama3]", t)
check("O2 POST /api/generate, système et stream false",
      OLL and OLL[-1][0] == "/api/generate" and OLL[-1][1].get("system") == "Tu es bref."
      and OLL[-1][1].get("stream") is False and OLL[-1][1].get("prompt") == "Bonjour", OLL[-1:])
t = MT.tirer("ollama", "qwen2.5:7b", "Bonjour", "", 200)
check("O3 le modèle demandé est celui envoyé", OLL[-1][1].get("model") == "qwen2.5:7b", OLL[-1:])
check("O3b sans json : pas de champ format", "format" not in OLL[-1][1])
OLL.clear()
_orig = _Ollama.do_POST
try:
    def _post_json(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        OLL.append((self.path, corps))
        return self._rendre(200, {"response": '{"elements": [1, 2], "model": "' + corps["model"] + '"}'})
    _Ollama.do_POST = _post_json
    o = MT.tirer("ollama", "", "Chorégraphie", "Rends du JSON.", 300, json=True)
    check("O4 json=True : un objet est rendu", o == {"elements": [1, 2], "model": "llama3"}, repr(o))
    check("O5 json=True : format json demandé à Ollama", OLL and OLL[-1][1].get("format") == "json", OLL[-1:])
    check("O5b json=True : le système dit JSON", "JSON" in (OLL[-1][1].get("system") or ""), OLL[-1:])
finally:
    _Ollama.do_POST = _orig

# ── [F] fournisseur libre ─────────────────────────────────────────────────────────────────────────────────────────
print("[F] fournisseur libre")
v = FL.creer({"nom": "DeepSeek", "base": "https://api.deepseek.com/v1", "cle": CLE, "modeles": ["deepseek-chat"],
              "defaut": "deepseek-chat"})
FLM = FL.PREFIXE + v["id"]
check("F0 fl:<id> configuré et connu", MT.configure(FLM) and MT.connu(FLM), FLM)
REQ.clear()
FL_REP["texte"] = "Texte du faux fournisseur. [{m}]"
t = MT.tirer(FLM, "", "Résume", "Tu résumes.", 100)
check("F1 texte du faux fournisseur, modèle par défaut", t == "Texte du faux fournisseur. [deepseek-chat]", t)
corps = json.loads(REQ[-1].content) if REQ else {}
check("F2 POST {base}/chat/completions, système en tête, max_tokens transmis",
      REQ and str(REQ[-1].url) == "https://api.deepseek.com/v1/chat/completions"
      and corps.get("messages", [{}])[0] == {"role": "system", "content": "Tu résumes."} and corps.get("max_tokens") == 100,
      corps)
FL_REP["texte"] = "Voici :\n```json\n{\"elements\": [{\"type\": \"text\", \"m\": \"{m}\"}]}\n```\nVoilà."
o = MT.tirer(FLM, "autre-modele", "Chorégraphie", "", 100, json=True)
check("F3 json=True : objet extrait d'un bloc ```json", o == {"elements": [{"type": "text", "m": "autre-modele"}]}, repr(o))
check("F3b json=True : le système envoyé dit JSON",
      "JSON" in json.loads(REQ[-1].content)["messages"][0]["content"], json.loads(REQ[-1].content)["messages"][:1])

# ── [L] serveur local ─────────────────────────────────────────────────────────────────────────────────────────────
print("[L] serveur local")
s = SL.creer({"url": URL_OLL, "type": "ollama", "nom": "Mon PC", "modeles": ["llama3"], "defaut": "llama3"})
LOC = SL.PREFIXE + s["id"]
OLL.clear()
t = MT.tirer(LOC, "", "Bonjour", "Bref.", 50)
check("L1 local:<id> : POST /api/chat au faux Ollama", OLL and OLL[-1][0] == "/api/chat" and t.endswith("[llama3]"),
      (OLL[-1:], t))

# ── [G] gardes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[G] gardes")


def leve(f):
    try:
        f()
    except RuntimeError as e:
        return str(e) or "RuntimeError"
    except Exception as e:                                          # noqa: BLE001
        return f"AUTRE {type(e).__name__}: {e}"
    return ""


check("G1 moteur inconnu → RuntimeError", leve(lambda: MT.tirer("inconnu", "m", "p", "", 10)).startswith("moteur inconnu"))
check("G1b fl:absent → RuntimeError", "inconnu" in leve(lambda: MT.tirer("fl:absent", "m", "p", "", 10)))
CAC.appliquer({"OLLAMA_MODEL": ""})
check("G2 aucun modèle → RuntimeError", "aucun modèle" in leve(lambda: MT.tirer("ollama", "", "p", "", 10)))
CAC.appliquer({"OLLAMA_MODEL": "llama3"})
OLL.clear(); REQ.clear()
e = leve(lambda: MT.tirer("ollama", "sk-proj-abcdefghijklmnopqrstuvwxyz", "p", "", 10))
check("G3 modèle qui ressemble à une clé → RuntimeError, rien envoyé", e and not e.startswith("AUTRE") and not OLL, e)
check("G3b la clé n'est pas recopiée dans le message", "abcdefghijkl" not in e, e)
e = leve(lambda: MT.tirer(FLM, "AIzaSyD-xxxxxxxxxxxxxxxxxxxxxxxxx", "p", "", 10))
check("G3c idem pour un fournisseur libre", e and not REQ, e)
FL_REP["texte"] = "je ne sais pas faire de JSON"
check("G4 JSON illisible → RuntimeError", "JSON" in leve(lambda: MT.tirer(FLM, "", "p", "", 10, json=True)))
FL_REP["texte"] = '__import__("os").system("echo piege")'
check("G5 une sortie n'est jamais évaluée (code Python → RuntimeError, pas d'exécution)",
      "JSON" in leve(lambda: MT.tirer(FLM, "", "p", "", 10, json=True)))
check("G6 extraire_json : tableau, objet, texte autour",
      MT.extraire_json("[1,2]") == [1, 2] and MT.extraire_json('blabla {"a": 1} fin') == {"a": 1})
check("G7 extraire_json : trop long → RuntimeError", "long" in leve(lambda: MT.extraire_json("{" + " " * 300_000 + "}")))
check("G8 extraire_json : un nombre seul n'est pas un document", leve(lambda: MT.extraire_json("42")) != "")

# ── [C] nature de coût ────────────────────────────────────────────────────────────────────────────────────────────
print("[C] nature de coût")
check("C1 ollama gratuit", MT.nature_cout("ollama") == "gratuit")
check("C2 local:<id> gratuit", MT.nature_cout(LOC) == "gratuit")
check("C3 fl:<id> a_mesurer", MT.nature_cout(FLM) == "a_mesurer")
check("C4 intégrés payants", all(MT.nature_cout(m) == "payant" for m in ("anthropic", "openai", "gemini")))

# ── [P] tirer_garde : plafonds, estimation avant l'appel ──────────────────────────────────────────────────────────
print("[P] tirer_garde")
op = MT.estimer(FLM, "x" * 400, "y" * 400, 900)
check("P1 estimer : op llm au moteur choisi, out_tok = max_tokens, in_tok > 0",
      op.get("kind") == "llm" and op.get("provider") == FLM and op.get("out_tok") == 900 and op.get("in_tok", 0) >= 200, op)
ORDRE = []
_v0 = PLAF.verifier


async def _espion(o, categorie="", ref=None, confirme=None):
    ORDRE.append(("verifier", o.get("provider"), categorie, len(REQ)))
    return await _v0(o, categorie, ref, confirme)


PLAF.verifier = _espion
REQ.clear()
FL_REP["texte"] = "ok [{m}]"
t = asyncio.run(MT.tirer_garde(FLM, "", "Bonjour", "", 100, categorie="motion"))
check("P2 tirer_garde : texte rendu", t == "ok [deepseek-chat]", t)
check("P3 plafond vérifié AVANT la requête, au moteur choisi, catégorie transmise",
      ORDRE and ORDRE[0] == ("verifier", FLM, "motion", 0) and len(REQ) == 1, (ORDRE, len(REQ)))
PLAF.verifier = _v0
PLAF.enregistrer({"global_usd": 0.000001, "par_moteur": {}})
REQ.clear()
try:
    asyncio.run(MT.tirer_garde(FLM, "", "Bonjour", "", 4000))
    r402 = None
except HTTPException as e:
    r402 = e
check("P4 plafond dépassé → 402 dz_plafond, AUCUNE requête",
      r402 is not None and r402.status_code == 402 and "dz_plafond" in r402.detail and not REQ, (r402, len(REQ)))
OLL.clear()
t = asyncio.run(MT.tirer_garde("ollama", "", "Bonjour", "", 4000))
check("P5 Ollama passe sous le même plafond (gratuit)", t.endswith("[llama3]") and OLL, t)
t = asyncio.run(MT.tirer_garde(LOC, "", "Bonjour", "", 4000))
check("P5b local:<id> passe aussi (gratuit)", t.endswith("[llama3]"), t)
PLAF.enregistrer({"global_usd": 0, "par_moteur": {}})
REQ.clear()
try:
    asyncio.run(MT.tirer_garde("anthropic", "claude-x", "p", "", 10))
    e = ""
except RuntimeError as x:
    e = str(x)
check("P6 moteur non configuré → RuntimeError, sans requête", "configur" in e and not REQ, e)
o = asyncio.run(MT.tirer_garde("ollama", "", "p", "", 10, json=False))
check("P7 tirer_garde json=False rend du texte", isinstance(o, str))

# ── [V] Vectorlab ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] Vectorlab")
corps_vi = inspect.getsource(VI.tirer)
check("V1 vector_illustration.tirer délègue à moteurs_texte.tirer (aucun httpx dans son corps)",
      "moteurs_texte" in corps_vi and "httpx" not in corps_vi.split('"""')[-1], corps_vi[-300:])
OLL.clear()
check("V2 même texte par le Vectorlab", VI.tirer("ollama", "", "Bonjour", "S") == MT.tirer("ollama", "", "Bonjour", "S"))
check("V3 le Vectorlab garde son max_tokens de 4000 (Ollama n'en reçoit pas, fl le reçoit)",
      inspect.signature(VI.tirer).parameters["max_tokens"].default == 4000)
REQ.clear()
FL_REP["texte"] = "<svg/>"
VI.tirer(FLM, "", "dessine", "S")
check("V4 Vectorlab → fl : max_tokens 4000 transmis", json.loads(REQ[-1].content).get("max_tokens") == 4000)

# ── [R] la route ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] GET /api/motion/moteurs")
r = c.get("/api/motion/moteurs")
check("R1 200 depuis la boucle locale", r.status_code == 200, r.status_code)
j = r.json() if r.status_code == 200 else {}
lignes = {l["moteur"]: l for l in j.get("moteurs", [])}
check("R2 une ligne par moteur de etat(), dans l'ordre", [l["moteur"] for l in j.get("moteurs", [])]
      == [l["moteur"] for l in MT.etat()], list(lignes))
check("R3 champs de etat() conservés", all(set(e) <= set(lignes.get(e["moteur"], {})) for e in MT.etat()))
check("R4 cout : ollama gratuit, local gratuit, fl a_mesurer, intégrés payant",
      lignes.get("ollama", {}).get("cout") == "gratuit" and lignes.get(LOC, {}).get("cout") == "gratuit"
      and lignes.get(FLM, {}).get("cout") == "a_mesurer"
      and all(lignes.get(m, {}).get("cout") == "payant" for m in ("anthropic", "openai", "gemini")), lignes)
check("R5 configure reflété (ollama oui, anthropic non)",
      lignes.get("ollama", {}).get("configure") is True and lignes.get("anthropic", {}).get("configure") is False)
check("R6 aucune clé dans la réponse", CLE not in r.text)
cd = TestClient(app, client=("192.168.1.50", 5000))
check("R7 autre appareil → refusé (401 du middleware d'appairage, ou 403)",
      cd.get("/api/motion/moteurs").status_code in (401, 403))
import types                                                        # noqa: E402
from app.api import routes as RT                                    # noqa: E402
try:
    asyncio.run(RT.motion_moteurs(types.SimpleNamespace(client=types.SimpleNamespace(host="192.168.1.50"))))
    g = 0
except HTTPException as e:
    g = e.status_code
check("R7b la route a sa propre garde de boucle locale (403, même appairé)", g == 403, g)

_srv.shutdown()
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
