# -*- coding: utf-8 -*-
"""Studio : Animation (18/10/2026) — OpenAI : la sortie maximale des modèles de RAISONNEMENT.

Référence Chat Completions (developers.openai.com, relevée le 18/10/2026) : `max_tokens` est déprécié, remplacé par
`max_completion_tokens`, et « n'est pas compatible avec les modèles o-series » ; les modèles de raisonnement (o1, o3,
o4-mini, gpt-5*, gpt-6*) refusent la requête qui le porte. `moteurs_texte._appeler` envoie donc
`max_completion_tokens` à CES modèles (même filtre que l'effort t239 : `_OPENAI_RAISONNEMENT` hors `_OPENAI_EXCLUS`)
et `max_tokens`, inchangé, à tous les autres.

Zéro dépense : OpenAI est un FAUX SERVEUR (httpx.post détourné dans ce processus pour sa seule adresse, corps reçus
enregistrés) qui répond 400 comme le vrai quand un modèle de raisonnement reçoit `max_tokens`.
Ce que ce banc garde :
  [R] modèles de raisonnement → `max_completion_tokens` = la sortie demandée, jamais `max_tokens` ; l'appel aboutit ;
  [N] autres modèles (gpt-4o, gpt-4.1, variantes chat) → `max_tokens` inchangé, jamais `max_completion_tokens` ;
  [E] avec l'effort : `reasoning_effort` ET `max_completion_tokens` = `sortie_max` du niveau ; json → response_format.
Run (depuis backend/) : & $PY tests/test_moteurs_openai_sortie.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzoas_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("OPENAI_MODEL", "OPENAI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


RAISONNEMENT = ("o1", "o3", "o3-mini", "o4-mini", "gpt-5", "gpt-5.5", "gpt-5.4-mini", "gpt-6", "gpt-6.1-sol")
AUTRES = ("gpt-4o", "gpt-4.1", "gpt-4o-mini", "gpt-5-chat-latest")
RECUS = []
_post0 = httpx.post


def _rep(code, obj):
    return httpx.Response(code, json=obj, request=httpx.Request("POST", "http://faux"))


def _faux_post(url, *a, **k):
    u = str(url)
    if u.startswith("https://api.openai.com/"):
        corps = k.get("json") or {}
        RECUS.append(corps)
        if corps.get("model") in RAISONNEMENT and "max_tokens" in corps:
            return _rep(400, {"error": {"message": "Unsupported parameter: 'max_tokens' is not supported with this "
                                                  "model. Use 'max_completion_tokens' instead.",
                                        "type": "invalid_request_error", "param": "max_tokens",
                                        "code": "unsupported_parameter"}})
        return _rep(200, {"choices": [{"message": {"content": '{"ok": 1}'}}]})
    return _post0(url, *a, **k)


httpx.post = _faux_post
CAC.appliquer({"OPENAI_API_KEY": "sk-faussecle-sortie"})

try:
    print("[R] modèles de raisonnement")
    for m in RAISONNEMENT:
        RECUS.clear()
        try:
            txt, err = MT.tirer("openai", m, "Bonjour", "S", 1234), ""
        except RuntimeError as e:
            txt, err = "", str(e)
        b = RECUS[-1] if RECUS else {}
        check(f"R {m} : max_completion_tokens = 1234, pas de max_tokens, l'appel aboutit",
              b.get("max_completion_tokens") == 1234 and "max_tokens" not in b and txt and not err, (b, err))

    print("[N] autres modèles : inchangés")
    for m in AUTRES:
        RECUS.clear()
        MT.tirer("openai", m, "Bonjour", "S", 1234)
        b = RECUS[-1] if RECUS else {}
        check(f"N {m} : max_tokens = 1234, pas de max_completion_tokens",
              b.get("max_tokens") == 1234 and "max_completion_tokens" not in b, b)

    print("[E] effort et json")
    RECUS.clear()
    MT.tirer("openai", "o3", "Bonjour", "S", 1000, effort="high")
    b = RECUS[-1] if RECUS else {}
    check("E1 o3 + high : reasoning_effort et max_completion_tokens = sortie_max(1000, high)",
          b.get("reasoning_effort") == "high" and b.get("max_completion_tokens") == MT.sortie_max(1000, "high")
          and "max_tokens" not in b, b)
    RECUS.clear()
    r = MT.tirer("openai", "gpt-5.5", "Bonjour", "S", 500, json=True)
    b = RECUS[-1] if RECUS else {}
    check("E2 gpt-5.5 json : response_format gardé, max_completion_tokens = 500",
          b.get("response_format") == {"type": "json_object"} and b.get("max_completion_tokens") == 500
          and r == {"ok": 1}, (b, r))
    RECUS.clear()
    MT.tirer("openai", "gpt-4o", "Bonjour", "S", 1000, effort="high")
    b = RECUS[-1] if RECUS else {}
    check("E3 gpt-4o + high : ni effort ni max_completion_tokens, max_tokens 1000",
          "reasoning_effort" not in b and "max_completion_tokens" not in b and b.get("max_tokens") == 1000, b)
finally:
    httpx.post = _post0

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
