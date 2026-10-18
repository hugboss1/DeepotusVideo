# -*- coding: utf-8 -*-
"""t239 (Studio : Animation, 18/10/2026) — l'EFFORT du modèle dans `moteurs_texte`.

Plan docs/superpowers/plans/2026-10-17-studio-animation.md (t239), spec 2026-10-18-studio-animation-personnalisation.md
§ 1.5 et P7. `tirer(…, effort=None)` / `tirer_garde(…, effort=None)` : None / "auto" = rien n'est envoyé ; sinon le
niveau est traduit par fournisseur, SEULEMENT si le modèle réellement choisi l'accepte (celui de l'appel, sinon celui
des Réglages › Valeurs par défaut — jamais un défaut figé du code).

Zéro dépense : Anthropic, OpenAI et Gemini sont de FAUX SERVEURS (httpx.post / httpx.get détournés dans ce processus
pour leurs seules adresses, corps reçus enregistrés) ; un FAUX OLLAMA écoute sur 127.0.0.1 (port tiré au hasard,
jamais 8765) et répond à /api/show avec les niveaux de « réflexion » du modèle.
Ce que ce banc garde :
  [M] le module : `efforts`, `effort_applique`, `sortie_max`, `noter_capacites` ; `effort=None` sur tirer/tirer_garde ;
  [A] table de familles Anthropic (repli quand l'API Modèles n'a rien dit) : niveaux et défaut par modèle ;
  [K] les `capabilities` de l'API Modèles priment sur la table (lues par `publies`, déjà appelée pour la liste) ;
  [E] Anthropic : `output_config.effort` présent si accepté, absent sinon ; modèle = celui des Réglages quand l'appel
      n'en donne pas ; la sortie maximale envoyée grandit avec le niveau ;
  [O] OpenAI `reasoning_effort` (modèles de raisonnement seulement) ; [G] Gemini `thinkingConfig.thinkingLevel`
      (modèles relevés seulement) ; [L] Ollama `think` (niveaux lus par /api/show) ; fl:/local: → Auto seul ;
  [S] estimation par niveau AVANT l'appel, sous les plafonds ;
  [R] GET /api/motion/moteurs (modèle des Réglages + efforts) et /settings/provider-defaults/modeles (liste publiée
      complète, défaut en tête, efforts par modèle) ;
  [C] le chorégraphe accepte `effort` et rend `effort_applique` ; [V] Vitrail / Vectorlab inchangés (aucun effort).
Run (depuis backend/) : & $PY tests/test_moteurs_effort.py"""
import asyncio, inspect, json, os, pathlib, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzeff_"))
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
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import vector_illustration as VI                  # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


CINQ = ["low", "medium", "high", "xhigh", "max"]

# ── les faux serveurs des fournisseurs (corps reçus) ──────────────────────────────────────────────────────────────
RECUS = []                                  # (fournisseur, url, corps)
SORTIE = {"texte": "ok"}


def _caps(niveaux, actif=True, feuilles=None):
    e = {"supported": bool(actif and niveaux)}
    for n in CINQ:
        e[n] = {"supported": n in (niveaux if feuilles is None else feuilles)}
    return {"effort": e, "thinking": {"supported": True}}


# la liste PUBLIÉE (14 modèles, comme le 18/10), avec les capabilities de l'API Modèles ; `claude-futur-1` n'est dans
# aucune table : seules ses capabilities disent ce qu'il accepte
MODELES_A = {
    "claude-fable-5-1": CINQ, "claude-fable-5": CINQ, "claude-opus-5-5": CINQ, "claude-opus-5": CINQ,
    "claude-opus-4-8": CINQ, "claude-opus-4-7": CINQ, "claude-opus-4-6": ["low", "medium", "high", "max"],
    "claude-sonnet-5-5": CINQ, "claude-sonnet-5": CINQ, "claude-sonnet-4-6": ["low", "medium", "high", "max"],
    "claude-haiku-5-5": CINQ, "claude-haiku-4-5-20251001": [], "claude-opus-4-5-20251101": ["low", "medium", "high"],
    "claude-futur-1": ["low", "high"],
}
_post0, _get0 = httpx.post, httpx.get


def _rep(code, obj):
    return httpx.Response(code, json=obj, request=httpx.Request("GET", "http://faux"))


def _faux_post(url, *a, **k):
    u = str(url)
    corps = k.get("json") or {}
    if u.startswith("https://api.anthropic.com/"):
        RECUS.append(("anthropic", u, corps))
        return _rep(200, {"content": [{"type": "text", "text": SORTIE["texte"]}]})
    if u.startswith("https://api.openai.com/"):
        RECUS.append(("openai", u, corps))
        return _rep(200, {"choices": [{"message": {"content": SORTIE["texte"]}}]})
    if u.startswith("https://generativelanguage.googleapis.com/"):
        RECUS.append(("gemini", u, corps))
        return _rep(200, {"candidates": [{"content": {"parts": [{"text": SORTIE["texte"]}]}}]})
    return _post0(url, *a, **k)


def _faux_get(url, *a, **k):
    u = str(url)
    if u.startswith("https://api.anthropic.com/v1/models"):
        return _rep(200, {"data": [{"id": i, "display_name": i, "capabilities": _caps(n)}
                                   for i, n in MODELES_A.items()]})
    if u.startswith("https://api.openai.com/v1/models"):
        return _rep(200, {"data": [{"id": i} for i in ("gpt-4o", "o3", "gpt-5.5")]})
    return _get0(url, *a, **k)


httpx.post, httpx.get = _faux_post, _faux_get

# ── le faux Ollama (un vrai serveur HTTP) ─────────────────────────────────────────────────────────────────────────
OLL = []


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
            return self._rendre(200, {"models": [{"name": "gpt-oss:20b"}, {"name": "llama3"}]})
        self._rendre(404, {})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        OLL.append((self.path, corps))
        if self.path == "/api/show":
            if str(corps.get("model")) == "dz-auto":        # un modèle dont un niveau s'appellerait « auto »
                return self._rendre(200, {"thinking": {"values": ["auto", "high"], "default": "auto"}})
            if str(corps.get("model")).startswith("gpt-oss"):
                return self._rendre(200, {"capabilities": ["completion", "thinking"],
                                          "thinking": {"values": ["low", "medium", "high"], "default": "medium"}})
            return self._rendre(200, {"capabilities": ["completion"]})
        if self.path == "/api/generate":
            return self._rendre(200, {"response": "ok", "done": True})
        self._rendre(404, {})


_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
PORT = _srv.server_address[1]
assert PORT != 8765
threading.Thread(target=_srv.serve_forever, daemon=True).start()

CAC.appliquer({"ANTHROPIC_API_KEY": "sk-ant-faussecle-t239", "OPENAI_API_KEY": "sk-faussecle-t239",
               "GEMINI_API_KEY": "AIzaFausseCleT239", "OLLAMA_MODEL": "llama3",
               "ANTHROPIC_MODEL": "claude-opus-5-5", "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})
settings.OLLAMA_URL = f"http://127.0.0.1:{PORT}"

c = TestClient(app)
c.__enter__()

# ── [M] le module ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[M] le module")
for nom in ("efforts", "effort_applique", "sortie_max", "noter_capacites"):
    check(f"M1 moteurs_texte.{nom} existe", callable(getattr(MT, nom, None)))
if not callable(getattr(MT, "efforts", None)):
    _srv.shutdown()
    print(f"\n{ok} PASS, {fail + 1} FAIL")
    sys.exit(1)
for f in (MT.tirer, MT.tirer_garde, MT.estimer):
    p = inspect.signature(f).parameters
    check(f"M2 {f.__name__}(…, effort=None)", "effort" in p and p["effort"].default is None, str(inspect.signature(f)))

# ── [A] table de familles (aucune capability notée) ───────────────────────────────────────────────────────────────
print("[A] table de familles Anthropic")
MT._CAPS.clear()


def niv(m, moteur="anthropic"):
    e = MT.efforts(moteur, m)
    return e["niveaux"], e["defaut"]


for m in ("claude-fable-5-1", "claude-fable-5", "claude-mythos-5-1", "claude-opus-5", "claude-opus-4-8",
          "claude-opus-4-7", "claude-sonnet-5-5", "claude-sonnet-5"):
    check(f"A1 {m} → low…max, défaut high", niv(m) == (CINQ, "high"), niv(m))
for m in ("claude-opus-5-5", "claude-haiku-5-5"):
    check(f"A2 {m} → low…max (xhigh et max acceptés), défaut medium", niv(m) == (CINQ, "medium"), niv(m))
for m in ("claude-opus-4-6", "claude-sonnet-4-6"):
    check(f"A3 {m} → low/medium/high/max (pas xhigh), défaut high",
          niv(m) == (["low", "medium", "high", "max"], "high"), niv(m))
check("A4 claude-opus-4-5-20251101 → low/medium/high", niv("claude-opus-4-5-20251101") == (["low", "medium", "high"], "high"),
      niv("claude-opus-4-5-20251101"))
for m in ("claude-haiku-4-5-20251001", "claude-haiku-4-5", "claude-sonnet-4-5", "claude-3-5-sonnet-20241022",
          "claude-opus-4-1", "claude-inconnu"):
    check(f"A5 {m} → Auto seul, sans défaut affiché", niv(m) == ([], ""), niv(m))
check("A6 modèle absent → celui des Réglages (claude-opus-5-5)",
      MT.efforts("anthropic", None)["modele"] == "claude-opus-5-5" and niv(None) == (CINQ, "medium"), MT.efforts("anthropic", None))

# ── [K] les capabilities de l'API Modèles priment ─────────────────────────────────────────────────────────────────
print("[K] capabilities")
check("K0 sans capability, un modèle hors table → Auto", niv("claude-futur-1")[0] == [])
MT.noter_capacites("anthropic", "claude-futur-1", _caps(["low", "high"]))
check("K1 capabilities lues : claude-futur-1 → low, high", niv("claude-futur-1")[0] == ["low", "high"], niv("claude-futur-1"))
MT.noter_capacites("anthropic", "claude-opus-5-5", _caps(["low", "medium", "high"]))
check("K2 les capabilities priment sur la table (opus-5-5 sans xhigh/max ici), défaut gardé",
      niv("claude-opus-5-5") == (["low", "medium", "high"], "medium"), niv("claude-opus-5-5"))
MT.noter_capacites("anthropic", "claude-opus-4-5-20251101", _caps([], actif=False, feuilles=CINQ))
check("K3 effort.supported = false (même feuilles vraies) → Auto", niv("claude-opus-4-5-20251101")[0] == [])
check("K3b source dite (api / table / aucune)", MT.efforts("anthropic", "claude-futur-1").get("source") == "api"
      and MT.efforts("anthropic", "claude-opus-4-8").get("source") == "table", MT.efforts("anthropic", "claude-futur-1"))
MT._CAPS.clear()
VI._CATALOGUE.pop("anthropic", None)
pub = VI.publies("anthropic")
check("K4 publies (GET /v1/models) note les capabilities au passage", len(pub) == 14 and niv("claude-futur-1")[0] == ["low", "high"],
      (len(pub), niv("claude-futur-1")))

# ── [E] Anthropic : le corps reçu ─────────────────────────────────────────────────────────────────────────────────
print("[E] Anthropic")


def dernier(f):
    l = [r for r in RECUS if r[0] == f]
    return l[-1][2] if l else {}


RECUS.clear()
MT.tirer("anthropic", "", "Bonjour", "S", 1000, effort="max")
b = dernier("anthropic")
check("E1 modèle des Réglages (claude-opus-5-5) quand l'appel n'en donne pas", b.get("model") == "claude-opus-5-5", b.get("model"))
check("E2 Opus 5.5 + max → output_config.effort = max", b.get("output_config") == {"effort": "max"}, b.get("output_config"))
check("E3 la sortie maximale envoyée grandit avec l'effort (sortie_max)", b.get("max_tokens") == MT.sortie_max(1000, "max") > 1000,
      b.get("max_tokens"))
MT.tirer("anthropic", "claude-opus-5-5", "Bonjour", "S", 1000, effort="xhigh")
check("E4 Opus 5.5 + xhigh → présent", dernier("anthropic").get("output_config") == {"effort": "xhigh"})
for eff in (None, "auto", "AUTO", "", "turbo", 7):
    MT.tirer("anthropic", "claude-opus-5-5", "Bonjour", "S", 1000, effort=eff)
    bb = dernier("anthropic")
    check(f"E5 effort {eff!r} → rien envoyé, max_tokens inchangé", "output_config" not in bb and bb.get("max_tokens") == 1000, bb)
MT.tirer("anthropic", "claude-haiku-4-5-20251001", "Bonjour", "S", 1000, effort="max")
bb = dernier("anthropic")
check("E6 modèle ancien (Haiku 4.5) + max → JAMAIS envoyé", "output_config" not in bb and bb.get("max_tokens") == 1000, bb)
MT.tirer("anthropic", "claude-opus-4-6", "Bonjour", "S", 1000, effort="xhigh")
check("E7 Opus 4.6 + xhigh (non accepté) → rien", "output_config" not in dernier("anthropic"))
MT.tirer("anthropic", "claude-opus-4-6", "Bonjour", "S", 1000, effort="max")
check("E8 Opus 4.6 + max → présent", dernier("anthropic").get("output_config") == {"effort": "max"})
CAC.appliquer({"ANTHROPIC_MODEL": "claude-haiku-4-5-20251001"})
MT.tirer("anthropic", "", "Bonjour", "S", 1000, effort="max")
check("E9 Réglages = Haiku 4.5 → le niveau se décide sur LUI (rien envoyé)",
      dernier("anthropic").get("model") == "claude-haiku-4-5-20251001" and "output_config" not in dernier("anthropic"))
check("E9b Réglages = Haiku 4.5 : efforts() et estimer() sans modèle suivent LUI (jamais un défaut figé)",
      {k: MT.efforts("anthropic", None)[k] for k in ("modele", "niveaux", "defaut")}
      == {"modele": "claude-haiku-4-5-20251001", "niveaux": [], "defaut": ""}
      and MT.estimer("anthropic", "p", "s", 1000, effort="max")["out_tok"] == 1000, MT.efforts("anthropic", None))
CAC.appliquer({"ANTHROPIC_MODEL": "claude-opus-5-5"})
check("E10 effort_applique : accepté → niveau, refusé → \"\"",
      MT.effort_applique("anthropic", "claude-opus-5-5", "max") == "max"
      and MT.effort_applique("anthropic", "claude-haiku-4-5-20251001", "max") == ""
      and MT.effort_applique("anthropic", "", "Medium") == "medium", MT.effort_applique("anthropic", "", "Medium"))

# ── [O] OpenAI, [G] Gemini, [L] Ollama, fl/local ──────────────────────────────────────────────────────────────────
print("[O] OpenAI")
check("O1 o3 → low/medium/high, défaut medium", niv("o3", "openai") == (["low", "medium", "high"], "medium"), niv("o3", "openai"))
check("O2 gpt-4o → Auto seul", niv("gpt-4o", "openai")[0] == [])
MT.tirer("openai", "o3", "Bonjour", "S", 1000, effort="high")
check("O3 o3 + high → reasoning_effort = high", dernier("openai").get("reasoning_effort") == "high", dernier("openai"))
MT.tirer("openai", "gpt-4o", "Bonjour", "S", 1000, effort="high")
check("O4 gpt-4o + high → rien", "reasoning_effort" not in dernier("openai"))
MT.tirer("openai", "o3", "Bonjour", "S", 1000, effort="max")
check("O5 o3 + max (non relevé) → rien", "reasoning_effort" not in dernier("openai"))

print("[G] Gemini")
check("G1 gemini-3-pro-preview → low, high (défaut high)",
      niv("gemini-3-pro-preview", "gemini") == (["low", "high"], "high"), niv("gemini-3-pro-preview", "gemini"))
check("G2 gemini-3-flash-preview → minimal…high", niv("gemini-3-flash-preview", "gemini")[0] == ["minimal", "low", "medium", "high"])
check("G3 gemini-2.5-flash (réglage non sûr par generateContent) → Auto", niv("gemini-2.5-flash", "gemini")[0] == [])
MT.tirer("gemini", "gemini-3-pro-preview", "Bonjour", "S", 1000, effort="low")
check("G4 gemini-3-pro-preview + low → generationConfig.thinkingConfig.thinkingLevel = low",
      dernier("gemini").get("generationConfig", {}).get("thinkingConfig") == {"thinkingLevel": "low"}, dernier("gemini"))
MT.tirer("gemini", "gemini-3-pro-preview", "Bonjour", "S", 1000, effort="medium")
check("G5 gemini-3-pro-preview + medium (non accepté) → rien", "thinkingConfig" not in dernier("gemini").get("generationConfig", {}))

print("[L] Ollama et serveurs libres")
check("L1 gpt-oss:20b → niveaux lus par /api/show (low/medium/high, défaut medium)",
      niv("gpt-oss:20b", "ollama") == (["low", "medium", "high"], "medium"), niv("gpt-oss:20b", "ollama"))
check("L2 llama3 (sans réflexion) → Auto seul", niv("llama3", "ollama")[0] == [])
OLL.clear()
MT.tirer("ollama", "gpt-oss:20b", "Bonjour", "S", 1000, effort="high")
g = [cc for p, cc in OLL if p == "/api/generate"]
check("L3 gpt-oss + high → think = high", g and g[-1].get("think") == "high", g)
OLL.clear()
MT.tirer("ollama", "", "Bonjour", "S", 1000, effort="high")
g = [cc for p, cc in OLL if p == "/api/generate"]
check("L4 llama3 (Réglages) + high → pas de think", g and "think" not in g[-1], g)
OLL.clear()
MT.tirer("ollama", "dz-auto", "Bonjour", "S", 1000, effort="auto")
g = [cc for p, cc in OLL if p == "/api/generate"]
check("L4b « auto » ne part JAMAIS, même si le modèle nomme un niveau ainsi", g and "think" not in g[-1], g)
check("L5 fl:<id> et local:<id> → Auto seul", MT.efforts("fl:x", "m")["niveaux"] == [] and MT.efforts("local:x", "m")["niveaux"] == [])

# ── [S] estimation ────────────────────────────────────────────────────────────────────────────────────────────────
print("[S] estimation")
outs = [MT.estimer("anthropic", "p" * 400, "s", 1000, effort=e, modele="claude-opus-5-5")["out_tok"]
        for e in (None, "low", "medium", "high", "xhigh", "max")]
check("S1 Opus 5.5 : la sortie estimée croît strictement avec l'effort", outs == sorted(set(outs)) and outs[0] == 1000, outs)
check("S2 effort absent → estimation inchangée (out = max_tokens)", MT.estimer("anthropic", "p", "s", 900)["out_tok"] == 900)
check("S3 Haiku 4.5 + max → estimation inchangée (niveau non envoyé)",
      MT.estimer("anthropic", "p", "s", 1000, effort="max", modele="claude-haiku-4-5-20251001")["out_tok"] == 1000)
check("S4 l'estimation sans modèle suit le modèle des Réglages",
      MT.estimer("anthropic", "p", "s", 1000, effort="max")["out_tok"] == MT.sortie_max(1000, "max"))
ORDRE = []
_v0 = PLAF.verifier


async def _espion(o, categorie="", ref=None, confirme=None):
    ORDRE.append((o.get("out_tok"), len(RECUS)))
    return await _v0(o, categorie, ref, confirme)


PLAF.verifier = _espion
RECUS.clear()
asyncio.run(MT.tirer_garde("anthropic", "claude-opus-5-5", "Bonjour", "", 1000, effort="xhigh"))
check("S5 tirer_garde : estimation AVANT l'appel, à la sortie de l'effort, puis le niveau envoyé",
      ORDRE == [(MT.sortie_max(1000, "xhigh"), 0)] and dernier("anthropic").get("output_config") == {"effort": "xhigh"},
      (ORDRE, dernier("anthropic")))
PLAF.verifier = _v0
from app.services import pricing                                    # noqa: E402
_deja = sum(v["effectif_usd"] for v in asyncio.run(PLAF._cumul(PLAF.mois_courant()))["par_moteur"].values())
_d = [pricing.estimate(MT.estimer("anthropic", "Bonjour", "", 400, e, modele="claude-opus-5-5"))["total_usd"]
      for e in (None, "max")]
check("S5b le devis à l'effort max dépasse celui d'Auto", _d[1] > _d[0] > 0, _d)
PLAF.enregistrer({"global_usd": round(_deja + (_d[0] + _d[1]) / 2, 6), "par_moteur": {}})
RECUS.clear()
try:
    asyncio.run(MT.tirer_garde("anthropic", "claude-opus-5-5", "Bonjour", "", 400, effort="max"))
    r402 = None
except Exception as e:                                                # noqa: BLE001
    r402 = e
check("S6 plafond dépassé à l'effort max → 402, AUCUNE requête",
      getattr(r402, "status_code", 0) == 402 and not RECUS, (r402, len(RECUS)))
t = asyncio.run(MT.tirer_garde("anthropic", "claude-opus-5-5", "Bonjour", "", 400))
check("S7 le même appel en Auto passe sous le même plafond", t == "ok" and RECUS, t)
PLAF.enregistrer({"global_usd": 0, "par_moteur": {}})

# ── [R] les routes ────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] routes")
VI._CATALOGUE.clear()
MT._CAPS.clear()
r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "anthropic"})
j = r.json() if r.status_code == 200 else {}
mods = j.get("modeles", [])
check("R1 provider-defaults/modeles : liste publiée complète (14), modèle des Réglages en tête",
      len(mods) == 14 and mods[:1] == ["claude-opus-5-5"] and j.get("defaut") == "claude-opus-5-5", (len(mods), mods[:2], j.get("defaut")))
ef = j.get("efforts", {})
check("R2 efforts pour CHAQUE modèle de la liste", set(ef) == set(mods), set(mods) - set(ef))
check("R3 opus-5-5 : xhigh et max listés, défaut medium",
      ef.get("claude-opus-5-5", {}).get("niveaux") == CINQ and ef.get("claude-opus-5-5", {}).get("defaut") == "medium",
      ef.get("claude-opus-5-5"))
check("R4 haiku-4-5 : Auto seul ; claude-futur-1 : low/high (capabilities)",
      ef.get("claude-haiku-4-5-20251001", {}).get("niveaux") == []
      and ef.get("claude-futur-1", {}).get("niveaux") == ["low", "high"], (ef.get("claude-haiku-4-5-20251001"), ef.get("claude-futur-1")))
r = c.get("/api/motion/moteurs")
lig = {l["moteur"]: l for l in (r.json().get("moteurs", []) if r.status_code == 200 else [])}
a = lig.get("anthropic", {})
check("R5 /motion/moteurs : modèle des Réglages + efforts jusqu'à max, défaut medium",
      a.get("modele") == "claude-opus-5-5" and a.get("efforts", {}).get("niveaux") == CINQ
      and a.get("efforts", {}).get("defaut") == "medium", a)
check("R6 /motion/moteurs : chaque ligne a ses efforts (gpt-oss absent → ollama llama3 Auto)",
      all("efforts" in l for l in lig.values()) and lig.get("ollama", {}).get("efforts", {}).get("niveaux") == [], lig.get("ollama"))
CAC.appliquer({"ANTHROPIC_MODEL": "claude-haiku-4-5-20251001"})
a = {l["moteur"]: l for l in c.get("/api/motion/moteurs").json()["moteurs"]}["anthropic"]
check("R7 Réglages = Haiku 4.5 → Auto seul", a.get("efforts", {}).get("niveaux") == [], a)
CAC.appliquer({"ANTHROPIC_MODEL": "claude-opus-5-5"})
VI._CATALOGUE.clear()
check("R8 aucune clé dans les réponses", "sk-ant-faussecle" not in c.get("/api/motion/moteurs").text
      and "sk-ant-faussecle" not in c.get("/api/settings/provider-defaults/modeles", params={"moteur": "anthropic"}).text)

# ── [C] le chorégraphe ────────────────────────────────────────────────────────────────────────────────────────────
print("[C] chorégraphe")
SORTIE["texte"] = json.dumps({"elements": [{"type": "text", "text": "DEEP", "keyframes": [{"t": 0, "x": 50, "y": 50}]}]})
RECUS.clear()
r = c.post("/api/motion/choregraphier", json={"script": "DEEP", "direction": {"style": "", "source": None},
                                              "moteur": "anthropic", "modele": "", "effort": "max", "marque": False})
j = r.json() if r.status_code == 200 else {}
check("C1 effort max reçu par le faux Anthropic (modèle des Réglages)",
      dernier("anthropic").get("output_config") == {"effort": "max"} and dernier("anthropic").get("model") == "claude-opus-5-5",
      (r.status_code, r.text[:200], dernier("anthropic")))
check("C2 la réponse dit effort_applique = max", j.get("effort_applique") == "max", j.get("effort_applique"))
RECUS.clear()
r = c.post("/api/motion/choregraphier", json={"script": "DEEP", "direction": {"style": "", "source": None},
                                              "moteur": "anthropic", "modele": "claude-haiku-4-5-20251001",
                                              "effort": "max", "marque": False})
j = r.json() if r.status_code == 200 else {}
check("C3 modèle ancien : rien envoyé, effort_applique vide (Auto)",
      "output_config" not in dernier("anthropic") and j.get("effort_applique") == "", (j.get("effort_applique"), dernier("anthropic")))
SORTIE["texte"] = "ok"

# ── [V] non-régression Vectorlab / Vitrail ────────────────────────────────────────────────────────────────────────
print("[V] Vectorlab")
RECUS.clear()
VI.tirer("anthropic", "claude-opus-5-5", "dessine", "S")
bb = dernier("anthropic")
check("V1 Vectorlab → Anthropic : aucun effort, max_tokens 4000 inchangé", "output_config" not in bb and bb.get("max_tokens") == 4000, bb)
check("V2 /vector/vitrail répond toujours", c.get("/api/vector/vitrail").status_code == 200)

_srv.shutdown()
httpx.post, httpx.get = _post0, _get0
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
