# -*- coding: utf-8 -*-
"""t221 (Menus : Réglages, 16/10/2026) — Diagnostic : chaque clé a son endroit. Banc SERVEUR (l'écran a son banc à
part : test_reglages_diagnostic_ecran.py).

Défaut relevé le 15/10 : le Diagnostic listait toutes les clés de l'allowlist (`_ALLOWED_ENV_KEYS`), mais rien ne
disait où les régler, et plusieurs ne se réglaient NULLE PART : DECART_API_KEY (hors de l'écran Avatar live),
ARTICLE_READER_FALLBACK, ELEVENLABS_VOICE_ID_FR / _EN ; PLANNER/SUMMARIZER_PROVIDER et les *_MODEL jusqu'à t220.

Ce que ce banc garde :
  [T] la table clé → rubrique (`settings_routes.RUBRIQUE_DE_CLE`) couvre TOUTE l'allowlist, rien d'autre, et ne vise
      que des rubriques de la barre des Réglages (`ym`, lue dans le bundle livré) ;
  [R] les rubriques attendues : modèles et rôles → defaults, Decart et voix → keys, lecteur → news, réseaux → accounts ;
      un *_MODEL dont le moteur n'est pas configuré renvoie vers Clés d'API (Fournisseurs par défaut n'en montrerait
      aucune ligne), un moteur fautif reste dans defaults (la ligne s'y montre pour être corrigée) ;
  [D] GET /api/reglages/diagnostic : chaque ligne porte `rubrique`, y compris la ligne fautive et les lignes du coffre
      fermé ; aucune valeur ne fuit ;
  [P] chaque clé est AFFICHÉE dans sa rubrique (bundle livré) — « Régler » ne mène jamais dans le vide ;
  [S] /api/health : `decart_configured` et `article_reader_fallback` ; la bascule s'écrit au .env et s'applique à chaud.
Témoin : origin/main c784c6e8 n'a ni table ni champ `rubrique`.
Run (depuis backend/) : & $PY tests/test_reglages_diagnostic.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdiag221_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "OLLAMA_URL", "ANTHROPIC_API_KEY",
           "OPENAI_API_KEY", "GEMINI_API_KEY", "DECART_API_KEY", "ARTICLE_READER_FALLBACK"):
    os.environ.pop(_k, None)
CLE_G = "AIzaFAUSSECLEDEBANC000000000000000"
SECRET = "sk-DZSECRET-diag221-ne-sort-jamais"
(_tmp / ".env").write_text(f"OPENAI_API_KEY={SECRET}\nGEMINI_API_KEY={CLE_G}\nGEMINI_MODEL={CLE_G}\n"
                           f"DECART_API_KEY=dct-banc-221-xyz\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
import app.api.settings_routes as SR                                # noqa: E402
from app.api.routes import _ALLOWED_ENV_KEYS                       # noqa: E402

CAC.appliquer({"OPENAI_API_KEY": SECRET, "GEMINI_API_KEY": CLE_G, "GEMINI_MODEL": CLE_G, "ANTHROPIC_API_KEY": "",
               "OLLAMA_MODEL": "", "DECART_API_KEY": "dct-banc-221-xyz"})

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


RACINE = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_ym = re.search(r'\bym=\[([^\]]*)\]', BUNDLE)
YM = re.findall(r'"([a-z]+)"', _ym.group(1)) if _ym else []

print("[0] témoin : origin/main c784c6e8")
_b = subprocess.run(["git", "show", "c784c6e8:backend/app/api/settings_routes.py"], cwd=RACINE,
                    capture_output=True).stdout.decode("utf-8")
check("0.1 TÉMOIN : ni table clé → rubrique ni champ rubrique", _b and "RUBRIQUE_DE_CLE" not in _b
      and '"rubrique": ru' not in _b)

print("[T] la table")
T = getattr(SR, "RUBRIQUE_DE_CLE", {})
if not hasattr(SR, "rubrique_de"):
    SR.rubrique_de = lambda k: ""
# t345 (29/10) : 15e rubrique « mcp » (Serveur MCP), posée par le maillon dzmcp.
check("T0 la barre des Réglages est lue dans le bundle (15 rubriques, dont mcp)", len(YM) == 15 and "defaults" in YM
      and "mcp" in YM, repr(YM))
check("T1 AUCUNE clé de l'allowlist sans rubrique", T and not (_ALLOWED_ENV_KEYS - set(T)),
      repr(sorted(_ALLOWED_ENV_KEYS - set(T))))
check("T2 aucune clé hors de l'allowlist", set(T) <= _ALLOWED_ENV_KEYS, repr(sorted(set(T) - _ALLOWED_ENV_KEYS)))
check("T3 chaque rubrique est une rubrique de la barre (ym)", T and set(T.values()) <= set(YM), repr(set(T.values()) - set(YM)))
check("T4 rubrique_de couvre aussi toute l'allowlist", all(SR.rubrique_de(k) in YM for k in _ALLOWED_ENV_KEYS),
      repr([k for k in _ALLOWED_ENV_KEYS if SR.rubrique_de(k) not in YM]))

print("[R] les rubriques attendues")
attendu = {"PLANNER_PROVIDER": "defaults", "SUMMARIZER_PROVIDER": "defaults", "DECART_API_KEY": "keys",
           "ELEVENLABS_VOICE_ID_FR": "keys", "ELEVENLABS_VOICE_ID_EN": "keys", "ARTICLE_READER_FALLBACK": "news",
           "FAL_KEY": "keys", "FIGMA_TOKEN": "keys", "OLLAMA_URL": "keys", "X_API_KEY": "accounts",
           "TIKTOK_AUDITED": "accounts", "TELEGRAM_CHAT_ID": "accounts",
           "KAPSO_API_KEY": "keys"}                     # t310 (27/10/2026) : clé de fournisseur partagée, Clés d'API
check("R1 table : rôles → defaults, Decart/voix → keys, lecteur → news, réseaux → accounts",
      all(T.get(k) == v for k, v in attendu.items()), repr({k: T.get(k) for k, v in attendu.items() if T.get(k) != v}))
check("R2 table : chaque *_MODEL d'un moteur → defaults", all(T.get(k) == "defaults" for k in MT.CLE_MODELE.values()),
      repr({k: T.get(k) for k in MT.CLE_MODELE.values()}))
check("R3 moteur configuré (OpenAI) : OPENAI_MODEL → defaults", SR.rubrique_de("OPENAI_MODEL") == "defaults")
check("R4 moteur fautif (Gemini, clé dans le modèle) : GEMINI_MODEL → defaults, où il se corrige",
      SR.rubrique_de("GEMINI_MODEL") == "defaults")
check("R5 moteur NON configuré (Anthropic, sans clé) : ANTHROPIC_MODEL → keys (poser la clé d'abord)",
      SR.rubrique_de("ANTHROPIC_MODEL") == "keys")
check("R6 Ollama sans modèle : OLLAMA_MODEL → keys (l'encart LLM local)", SR.rubrique_de("OLLAMA_MODEL") == "keys")
CAC.appliquer({"ANTHROPIC_API_KEY": "sk-ant-banc-221"})
check("R7 la clé Anthropic posée : ANTHROPIC_MODEL → defaults", SR.rubrique_de("ANTHROPIC_MODEL") == "defaults")
CAC.appliquer({"ANTHROPIC_API_KEY": ""})

print("[D] le Diagnostic")
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    rep = c.get("/api/reglages/diagnostic")
    brut = rep.text
    L = {x["cle"]: x for x in rep.json().get("cles", [])} if rep.status_code == 200 else {}
    h = c.get("/api/health").json()
    w = c.post("/api/settings/keys", json={"name": "ARTICLE_READER_FALLBACK", "value": "false"})
    h2 = c.get("/api/health").json()
    env_apres = (_tmp / ".env").read_text(encoding="utf-8")
    c.post("/api/settings/keys", json={"name": "ARTICLE_READER_FALLBACK", "value": "true"})
    h3 = c.get("/api/health").json()
check("D1 une ligne par clé de l'allowlist", set(L) == _ALLOWED_ENV_KEYS, repr(sorted(set(L) ^ _ALLOWED_ENV_KEYS)))
check("D2 chaque ligne porte `rubrique` = rubrique_de", L and all(L[k].get("rubrique") == SR.rubrique_de(k) for k in L),
      repr([(k, L[k].get("rubrique")) for k in L if L[k].get("rubrique") != SR.rubrique_de(k)][:4]))
check("D3 la ligne fautive (GEMINI_MODEL) garde son alerte ET sa rubrique",
      L.get("GEMINI_MODEL", {}).get("alerte") and L["GEMINI_MODEL"].get("rubrique") == "defaults", repr(L.get("GEMINI_MODEL")))
check("D4 PLANNER_PROVIDER absent → defaults ; DECART posé → keys",
      L.get("PLANNER_PROVIDER", {}).get("rubrique") == "defaults" and L.get("DECART_API_KEY", {}).get("definie") is True
      and L["DECART_API_KEY"].get("rubrique") == "keys")
check("D5 aucune valeur ne fuit (ni secret, ni clé du modèle fautif)", SECRET not in brut and CLE_G not in brut
      and "dct-banc-221-xyz" not in brut)

# coffre posé mais FERMÉ : la branche « coffre-verrouille » porte aussi sa rubrique
from app.services import coffre as C                                # noqa: E402
_v = C.verrouille
C.verrouille = lambda: True
try:
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        Lv = {x["cle"]: x for x in c.get("/api/reglages/diagnostic").json()["cles"]}
finally:
    C.verrouille = _v
fer = [k for k, x in Lv.items() if x.get("source") == "coffre-verrouille"]
check("D6 coffre fermé : les lignes verrouillées portent leur rubrique", fer and all(Lv[k].get("rubrique") == SR.rubrique_de(k)
                                                                                    for k in fer), repr(fer[:3]))

print("[S] santé et bascule du lecteur")
check("S1 /api/health : decart_configured vrai (clé posée)", h.get("decart_configured") is True, repr(h.get("decart_configured")))
check("S2 /api/health : article_reader_fallback (défaut du code : vrai)", h.get("article_reader_fallback") is True,
      repr(h.get("article_reader_fallback")))
check("S3 écrire false : 200, au .env, appliqué à chaud (sans redémarrage)",
      w.status_code == 200 and "ARTICLE_READER_FALLBACK=false" in env_apres and h2.get("article_reader_fallback") is False
      and not w.json().get("restart_required"), w.text[:200])
check("S4 rétablir true", h3.get("article_reader_fallback") is True and settings.ARTICLE_READER_FALLBACK is True)

print("[P] chaque clé est affichée dans sa rubrique (bundle livré)")
def tranche(a, b):
    i = BUNDLE.find(a)
    j = BUNDLE.find(b, i + 1) if i >= 0 else -1
    return BUNDLE[i:j] if 0 <= i < j else ""
fu = tranche("const Fu=[", "function bm(")
fu += tranche("function dzFuNeuves(", "function dzRgCle(") if "Fu.concat(dzFuNeuves())" in BUNDLE else ""   # t221 : lignes neuves
keys_ecran = set(re.findall(r'\{k:"([A-Z_0-9]+)",label:', fu))
wm = tranche("function wm({serverKeys:e,onSaved:t})", "function Tm(")
keys_ecran |= set(re.findall(r'name:"([A-Z_]+)"', wm))
tm = BUNDLE[BUNDLE.find("function Tm("):BUNDLE.find("function Tm(") + 9000]
comptes = set(re.findall(r'k:"([A-Z][A-Z_]+)"', tm))
zm = tranche("function zm(", "function Cm(") + tranche("function DzNewsLecteur(", "function DzDiag(")
fourn = set(MT.CLE_MODELE.values()) | {"SUMMARIZER_PROVIDER", "PLANNER_PROVIDER", "AGENT_MODEL"}   # t285a : AGENT_MODEL = ligne_agent()
vide = []
for k, ru in T.items():
    if ru == "keys" and k not in keys_ecran:
        vide.append(k)
    elif ru == "accounts" and k not in comptes:
        vide.append(k)
    elif ru == "news" and not ('"' + k + '"' in zm and "r.jsx(DzNewsLecteur,{})" in BUNDLE):
        vide.append(k)
    elif ru == "defaults" and k not in fourn:
        vide.append(k)
    elif ru not in ("keys", "accounts", "news", "defaults"):
        vide.append(k)
check("P1 « Régler » ne mène jamais dans le vide : chaque clé est montrée par sa rubrique", T and not vide, repr(vide))
check("P2 un *_MODEL non configuré renvoie vers une rubrique qui l'affiche (Clés d'API)",
      all(k in keys_ecran or k == "OLLAMA_MODEL" and "OLLAMA_MODEL" in wm for k in ("OLLAMA_MODEL",))
      and "ANTHROPIC_API_KEY" in keys_ecran)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
