# -*- coding: utf-8 -*-
"""openai_llm (résumés, chat, plans) — la sortie maximale et la température des modèles de RAISONNEMENT (18/10/2026).

Référence Chat Completions (developers.openai.com, relevée le 18/10/2026) : `max_tokens` est déprécié au profit de
`max_completion_tokens` et « n'est pas compatible avec les modèles o-series ». Guide « latest model », section
« Update API and model parameters » : quand l'effort de raisonnement n'est pas `none`, retirer `temperature`, `top_p`
et `top_logprobs`. openai_llm n'envoie pas d'effort, le modèle prend donc son défaut (raisonnement actif) : pour ces
modèles (même filtre que moteurs_texte : `_openai_raisonne`), `max_completion_tokens` remplace `max_tokens` et
`temperature` n'est plus envoyée. Les autres modèles (gpt-4o, gpt-4.1, variantes chat) ne changent pas.

Zéro dépense : OpenAI est un FAUX SERVEUR (httpx.post et httpx.AsyncClient.post détournés dans ce processus pour sa
seule adresse, corps reçus enregistrés) qui répond 400 comme le vrai quand un modèle de raisonnement reçoit
`max_tokens` ou `temperature`.
Ce que ce banc garde, pour summarize, chat et generate_plan :
  [R] modèles de raisonnement → `max_completion_tokens` = la sortie prévue, ni `max_tokens` ni `temperature` ;
      l'appel aboutit (texte rendu, pas None) ;
  [N] autres modèles → `max_tokens` inchangé, `temperature` gardée pour chat, jamais `max_completion_tokens`.
Run (depuis backend/) : & $PY tests/test_openai_llm_sortie.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzols_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("OPENAI_MODEL", "OPENAI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import openai_llm as OL                           # noqa: E402
from app.services import plan_schema                                # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


RAISONNEMENT = ("o1", "o3", "o4-mini", "gpt-5", "gpt-5.5", "gpt-6.1-sol")
AUTRES = ("gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-5-chat-latest")
RECUS = []
PLAN = '{"posts": [{"day": 1, "channel": "x", "text": "Bonjour"}]}'
_post0 = httpx.post
_apost0 = httpx.AsyncClient.post


def _rep(code, obj):
    return httpx.Response(code, json=obj, request=httpx.Request("POST", "http://faux"))


def _refus(param):
    return _rep(400, {"error": {"message": f"Unsupported parameter: '{param}' is not supported with this model.",
                                "type": "invalid_request_error", "param": param,
                                "code": "unsupported_parameter"}})


def _repondre(corps):
    RECUS.append(corps)
    if corps.get("model") in RAISONNEMENT:
        for p in ("max_tokens", "temperature"):
            if p in corps:
                return _refus(p)
    texte = PLAN if any(m.get("role") == "system" for m in corps.get("messages") or []) else "Résumé neutre."
    return _rep(200, {"choices": [{"message": {"content": texte}}]})


def _faux_post(url, *a, **k):
    if str(url).startswith("https://api.openai.com/"):
        return _repondre(k.get("json") or {})
    return _post0(url, *a, **k)


async def _faux_apost(self, url, *a, **k):
    if str(url).startswith("https://api.openai.com/"):
        return _repondre(k.get("json") or {})
    return await _apost0(self, url, *a, **k)


ARTICLE = "Un article assez long pour être résumé. " * 10
SORTIE_RESUME = max(400, min(4000, int(150 * 2.0) + 200))


def _trois(m):
    """Les trois appels pour le modèle m → [(nom, corps reçu, résultat)]."""
    settings.OPENAI_MODEL = m
    out = []
    RECUS.clear()
    r = OL.summarize(ARTICLE, title="T", target_words=150)
    out.append(("summarize", RECUS[-1] if RECUS else {}, r))
    RECUS.clear()
    r = OL.chat("Bonjour", system="S", max_tokens=321, temperature=0.7)
    out.append(("chat", RECUS[-1] if RECUS else {}, r))
    RECUS.clear()
    r = asyncio.run(OL.generate_plan("Plan", 1, 1, ["x"], "FR", None))
    out.append(("generate_plan", RECUS[-1] if RECUS else {}, r))
    return out


def _vu(b, r):
    """Le détail d'un échec : le corps reçu sans les messages, et si l'appel a abouti."""
    return ({k: v for k, v in b.items() if k != "messages"}, "aboutit" if r else "None")


ATTENDU = {"summarize": SORTIE_RESUME, "chat": 321, "generate_plan": plan_schema.MAX_TOKENS}

httpx.post = _faux_post
httpx.AsyncClient.post = _faux_apost
CAC.appliquer({"OPENAI_API_KEY": "sk-faussecle-llm"})
_modele0 = settings.OPENAI_MODEL

try:
    print("[R] modèles de raisonnement")
    for m in RAISONNEMENT:
        for nom, b, r in _trois(m):
            check(f"R {m} {nom} : max_completion_tokens = {ATTENDU[nom]}, ni max_tokens ni temperature, aboutit",
                  b.get("max_completion_tokens") == ATTENDU[nom] and "max_tokens" not in b
                  and "temperature" not in b and r, _vu(b, r))

    print("[N] autres modèles : inchangés")
    for m in AUTRES:
        for nom, b, r in _trois(m):
            temp_ok = b.get("temperature") == 0.7 if nom == "chat" else "temperature" not in b
            check(f"N {m} {nom} : max_tokens = {ATTENDU[nom]}, pas de max_completion_tokens, température d'origine",
                  b.get("max_tokens") == ATTENDU[nom] and "max_completion_tokens" not in b and temp_ok and r,
                  _vu(b, r))
finally:
    httpx.post = _post0
    httpx.AsyncClient.post = _apost0
    settings.OPENAI_MODEL = _modele0

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
