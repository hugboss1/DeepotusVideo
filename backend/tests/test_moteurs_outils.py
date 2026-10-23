# -*- coding: utf-8 -*-
"""t285a (agent Campagnes, 23/10/2026) : un tour de modèle AVEC OUTILS, Anthropic, HTTP simple.

Spec docs/superpowers/specs/2026-10-23-agent-interne-design.md § 4.1. `moteurs_texte.converser` envoie UN tour
(système, messages, outils) et rend les blocs, l'arrêt et les jetons ; la boucle (T6) et les routes (T7) l'appellent.
Zéro dépense : la couture `_POSTER` est remplacée, la clé est factice.
Ce que ce banc garde :
  [E] l'envoi : corps avec model / max_tokens / system / messages / tools, en-têtes x-api-key et anthropic-version ;
  [B] la réponse : blocs `tool_use` rendus tels quels, `arret`, jetons ;
  [K] sans clé : RuntimeError("sans_cle"), aucune requête ;
  [F] un statut différent de 200 : RuntimeError au corps rogné, la clé n'y est JAMAIS ;
  [P] `op_tour` : l'op llm anthropic que `pricing.estimate` chiffre ;
  [M] `MODELE_AGENT_DEFAUT` / `modele_agent()` : AGENT_MODEL, sinon le modèle Anthropic des Réglages ; AGENT_MODEL
      est dans la liste blanche et se règle dans « defaults ».
Run (depuis backend/) : & $PY tests/test_moteurs_outils.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmo_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("ANTHROPIC_MODEL", "AGENT_MODEL", "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import pricing as PR                              # noqa: E402
from app.api import routes as R                                     # noqa: E402
from app.api import settings_routes as SR                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

CLE = "sk-ant-FACTICE-0123456789abcdef"
OUTILS = [{"name": "lire_dossier", "description": "x", "input_schema": {"type": "object", "properties": {}}}]
MSGS = [{"role": "user", "content": "Bonjour"}]


class Rep:
    def __init__(self, code=200, data=None, text=""):
        self.status_code, self._d, self.text = code, data, text
    def json(self):
        return self._d


class Couture:
    def __init__(self, rep):
        self.rep, self.appels = rep, []
    def __call__(self, url, **kw):
        self.appels.append((url, kw))
        return self.rep


REPONSE = {"content": [{"type": "text", "text": "Je regarde."},
                       {"type": "tool_use", "id": "toolu_1", "name": "lire_dossier", "input": {"a": 1}}],
           "stop_reason": "tool_use", "usage": {"input_tokens": 120, "output_tokens": 45}}
_poster0 = MT._POSTER

print("[E] envoi")
settings.ANTHROPIC_API_KEY = CLE
c = Couture(Rep(200, REPONSE)); MT._POSTER = c
res = MT.converser("claude-haiku-4-5-20251001", "Tu es l'agent.", MSGS, OUTILS, 512)
url, kw = c.appels[0]
corps = kw.get("json", {})
check("E1 URL de l'API Messages", url == "https://api.anthropic.com/v1/messages", url)
check("E2 corps : model, max_tokens, system, messages, tools",
      corps.get("model") == "claude-haiku-4-5-20251001" and corps.get("max_tokens") == 512
      and corps.get("system") == "Tu es l'agent." and corps.get("messages") == MSGS and corps.get("tools") == OUTILS,
      str(corps)[:200])
h = kw.get("headers", {})
check("E3 en-têtes anthropic-version et x-api-key", h.get("anthropic-version") == "2023-06-01" and h.get("x-api-key") == CLE)
check("E4 timeout par défaut 120 s", kw.get("timeout") == 120.0, str(kw.get("timeout")))
c = Couture(Rep(200, REPONSE)); MT._POSTER = c
MT.converser("m", "", MSGS, [], 64, timeout=30.0)
corps = c.appels[0][1]["json"]
check("E5 sans système ni outils : aucune clé vide envoyée", "system" not in corps and "tools" not in corps, str(corps))
check("E6 timeout transmis", c.appels[0][1]["timeout"] == 30.0)

print("[B] réponse")
c = Couture(Rep(200, REPONSE)); MT._POSTER = c
res = MT.converser("m", "s", MSGS, OUTILS, 64)
check("B1 blocs rendus tels quels, tool_use compris", res["blocs"] == REPONSE["content"]
      and res["blocs"][1]["type"] == "tool_use" and res["blocs"][1]["input"] == {"a": 1})
check("B2 arrêt et jetons", res["arret"] == "tool_use" and res["in_tok"] == 120 and res["out_tok"] == 45, str(res))
c = Couture(Rep(200, {"content": [], "stop_reason": "end_turn"})); MT._POSTER = c
res = MT.converser("m", "s", MSGS, [], 64)
check("B3 usage absent : jetons à 0", res["in_tok"] == 0 and res["out_tok"] == 0 and res["blocs"] == [], str(res))

print("[K] sans clé")
settings.ANTHROPIC_API_KEY = ""
c = Couture(Rep(200, REPONSE)); MT._POSTER = c
try:
    MT.converser("m", "s", MSGS, OUTILS, 64); lev = None
except RuntimeError as e:
    lev = str(e)
check("K1 RuntimeError('sans_cle')", lev == "sans_cle", str(lev))
check("K2 aucune requête partie", c.appels == [])

print("[F] erreur HTTP")
settings.ANTHROPIC_API_KEY = CLE
long = "x" * 5000 + CLE
c = Couture(Rep(401, None, long + " invalid x-api-key " + CLE)); MT._POSTER = c
try:
    MT.converser("m", "s", MSGS, OUTILS, 64); lev = None
except RuntimeError as e:
    lev = str(e)
check("F1 statut différent de 200 : RuntimeError avec le statut", lev is not None and "401" in lev, str(lev)[:100])
check("F2 corps rogné (400 caractères au plus)", lev is not None and len(lev) <= 400, str(len(lev or "")))
check("F3 la clé n'est JAMAIS dans le message", lev is not None and CLE not in lev and "FACTICE" not in lev, str(lev)[-80:])
c = Couture(Rep(429, None, "rate " + CLE + " limit")); MT._POSTER = c
try:
    MT.converser("m", "s", MSGS, OUTILS, 64); lev = None
except RuntimeError as e:
    lev = str(e)
check("F4 une clé au milieu du corps ne fuit pas non plus", lev is not None and CLE not in lev, str(lev))

print("[P] op_tour")
op = MT.op_tour("claude-haiku-4-5-20251001", 1000, 500)
check("P1 op llm anthropic", op["kind"] == "llm" and op["provider"] == "anthropic" and op["in_tok"] == 1000
      and op["out_tok"] == 500, str(op))
est = PR.estimate(op)
usd = est.get("total_usd", est.get("total"))
attendu = 1000 / 1e6 * 0.80 + 500 / 1e6 * 4.00
check("P2 pricing.estimate chiffre l'op au tarif Anthropic de la grille", usd is not None and abs(usd - attendu) < 1e-9,
      str(est)[:200])
check("P3 jetons négatifs ramenés à 0", MT.op_tour("m", -5, -1)["in_tok"] == 0 and MT.op_tour("m", -5, -1)["out_tok"] == 0)

print("[M] modèle de l'agent")
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
settings.AGENT_MODEL = ""
check("M1 AGENT_MODEL vide : le modèle Anthropic des Réglages", MT.modele_agent() == "claude-haiku-4-5-20251001", MT.modele_agent())
settings.AGENT_MODEL = "claude-sonnet-5-5"
check("M2 AGENT_MODEL posé : lu à chaud", MT.modele_agent() == "claude-sonnet-5-5", MT.modele_agent())
settings.AGENT_MODEL = CLE
check("M3 un AGENT_MODEL qui ressemble à une clé n'est jamais rendu", MT.modele_agent() == "claude-haiku-4-5-20251001")
settings.AGENT_MODEL = ""
check("M4 MODELE_AGENT_DEFAUT est un nom de modèle claude", MT.MODELE_AGENT_DEFAUT.startswith("claude-"), MT.MODELE_AGENT_DEFAUT)
check("M5 AGENT_MODEL dans la liste blanche des clés", "AGENT_MODEL" in R._ALLOWED_ENV_KEYS)
check("M6 AGENT_MODEL se règle dans « defaults »", SR.RUBRIQUE_DE_CLE.get("AGENT_MODEL") == "defaults")
check("M7 AGENT_MODEL est un réglage (défaut vide)", "AGENT_MODEL" in type(settings).model_fields
      and type(settings).model_fields["AGENT_MODEL"].default == "")

print("[R] la ligne de Réglages › Modèles par défaut")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
settings.ANTHROPIC_API_KEY = ""
check("R0 sans clé Anthropic : AGENT_MODEL → keys (poser la clé d'abord)", SR.rubrique_de("AGENT_MODEL") == "keys")
settings.ANTHROPIC_API_KEY = CLE
check("R0b clé posée : AGENT_MODEL → defaults", SR.rubrique_de("AGENT_MODEL") == "defaults")
c = TestClient(app); c.__enter__()
g = c.get("/api/settings/provider-defaults").json()
ag = next((m for m in g.get("moteurs", []) if m["moteur"] == "agent"), None)
check("R1 GET provider-defaults : une ligne « agent » (AGENT_MODEL), configurée avec la clé Anthropic",
      bool(ag) and ag["cle_modele"] == "AGENT_MODEL" and ag["configure"] is True and ag["fautif"] is False, str(ag))
check("R2 etat() ne contient PAS l'agent (ce n'est pas un moteur de texte)",
      all(m["moteur"] != "agent" for m in MT.etat()) and not MT.connu("agent"))
r = c.post("/api/settings/provider-defaults", json={"modeles": {"agent": "claude-sonnet-5-5"}})
check("R3 POST modeles.agent écrit AGENT_MODEL, appliqué à chaud",
      r.status_code == 200 and r.json()["written"] == {"AGENT_MODEL": "claude-sonnet-5-5"}
      and MT.modele_agent() == "claude-sonnet-5-5", r.text[:200])
r = c.post("/api/settings/provider-defaults", json={"modeles": {"agent": CLE}})
check("R4 une clé collée dans le modèle de l'agent → 400, rien d'écrit",
      r.status_code == 400 and CLE not in r.text and MT.modele_agent() == "claude-sonnet-5-5", r.text[:200])
r = c.post("/api/settings/provider-defaults/tester", json={"moteur": "agent", "modele": CLE})
check("R5 tester une clé comme modèle d'agent → 400", r.status_code == 400 and CLE not in r.text, r.text[:160])
r = c.get("/api/settings/provider-defaults/modeles", params={"moteur": "agent"})
check("R6 GET modeles?moteur=agent répond (liste d'Anthropic)", r.status_code == 200, r.text[:160])
c.post("/api/settings/provider-defaults", json={"modeles": {"agent": ""}})
settings.AGENT_MODEL = ""
check("R7 vide = retour au modèle Anthropic des Réglages", MT.modele_agent() == settings.ANTHROPIC_MODEL)
settings.ANTHROPIC_API_KEY = ""

MT._POSTER = _poster0
check("Z1 la couture d'origine est httpx.post", _poster0 is __import__("httpx").post)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
