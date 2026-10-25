# -*- coding: utf-8 -*-
"""L4.1 T3, final (25/10/2026) : le VRAI chemin `moteurs_texte._poster_flux` -> `converser`, sans réseau. Les autres
bancs de l'agent remplacent la couture `_POSTER` ; celui-ci la laisse en place et injecte un `httpx.MockTransport`
dans le client que `_poster_flux` ouvre (httpx.Client patché), pour éprouver la vraie lecture d'un flux httpx :
- p1 flux normal : deltas dans l'ordre, texte accentué (UTF-8 en octets), `input_json_delta` recollé, usage ;
- p2 flux coupé avant `message_stop` -> FluxCoupe qui porte l'usage annoncé ;
- p3 HTTP 500 : RuntimeError, la clé est remplacée par `***` dans le corps rendu ;
- p4 requête : `stream: true`, clé en en-tête seulement.
Run : & $PY tests/test_agent_poster_flux.py   (depuis la racine du dépôt ou backend/, PYTHONUTF8=1)."""
import json, os, sys, pathlib, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzl41_poster_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
for _k in ("ANTHROPIC_MODEL", "AGENT_MODEL", "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import httpx                                                        # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import moteurs_texte as MT                         # noqa: E402
from _faux_sse import evt                                            # noqa: E402

CLE = "sk-ant-FACTICE-poster"
settings.ANTHROPIC_API_KEY = CLE
VUES: list = []
_Client0 = httpx.Client


def installer(gestionnaire):
    """`_poster_flux` ouvre `httpx.Client(timeout=, verify=)` : on lui glisse un transport simulé."""
    def fabrique(*a, **kw):
        kw["transport"] = httpx.MockTransport(gestionnaire)
        return _Client0(*a, **kw)
    MT.httpx.Client = fabrique
    MT._POSTER = MT._poster_flux


def sse(lignes):
    return "\n".join(lignes).encode("utf-8")           # octets UTF-8, comme sur le fil


def flux_normal():
    L = evt("message_start", {"type": "message_start", "message": {"usage": {"input_tokens": 321, "output_tokens": 1}}})
    L += evt("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
    for m in ("Été ", "à Noël, ", "« ça va » ?"):
        L += evt("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": m}})
    L += evt("content_block_stop", {"type": "content_block_stop", "index": 0})
    L += evt("content_block_start", {"type": "content_block_start", "index": 1, "content_block": {
        "type": "tool_use", "id": "toolu_p", "name": "chercher_app", "input": {}}})
    for m in ('{"question": "caf', 'é crème", "n"', ': 3}'):
        L += evt("content_block_delta", {"type": "content_block_delta", "index": 1,
                                         "delta": {"type": "input_json_delta", "partial_json": m}})
    L += evt("content_block_stop", {"type": "content_block_stop", "index": 1})
    L += evt("message_delta", {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 77}})
    L += evt("message_stop", {"type": "message_stop"})
    return L


def main():
    print("[p1] flux normal par le vrai _poster_flux")
    def h1(req):
        VUES.append(req)
        return httpx.Response(200, content=sse(flux_normal()), headers={"content-type": "text/event-stream"})
    installer(h1)
    deltas: list = []
    r = MT.converser("claude-banc", "Système.", [{"role": "user", "content": "Salut"}], [], 100, sur_delta=deltas.append)
    check("p1 deltas dans l'ordre, accents intacts", deltas == ["Été ", "à Noël, ", "« ça va » ?"], str(deltas))
    check("p1 bloc texte recollé", r["blocs"][0]["text"] == "Été à Noël, « ça va » ?", str(r["blocs"][0]))
    check("p1 input_json_delta recollé en un objet, accents intacts",
          r["blocs"][1]["input"] == {"question": "café crème", "n": 3}, str(r["blocs"][1]))
    check("p1 usage : entrée de message_start, sortie de message_delta, arrêt",
          (r["in_tok"], r["out_tok"], r["arret"]) == (321, 77, "tool_use"), str(r))
    corps = json.loads(VUES[0].content)
    check("p1 la requête demande le flux, la clé est dans l'en-tête seulement",
          corps.get("stream") is True and VUES[0].headers.get("x-api-key") == CLE and CLE not in json.dumps(corps),
          str(corps)[:200])

    print("[p2] flux coupé avant message_stop")
    def h2(req):
        L = flux_normal()
        return httpx.Response(200, content=sse(L[:L.index('event: message_delta')]))
    installer(h2)
    try:
        MT.converser("claude-banc", "", [{"role": "user", "content": "x"}], [], 100)
        check("p2 FluxCoupe levée", False, "aucune exception")
    except MT.FluxCoupe as e:
        check("p2 FluxCoupe levée, avec l'usage annoncé (entrée 321)", e.in_tok == 321, f"{e!r} {e.in_tok}")

    print("[p3] HTTP 500 : la clé est ôtée du corps")
    installer(lambda req: httpx.Response(500, text=f"boum, la clé {CLE} a fuité"))
    try:
        MT.converser("claude-banc", "", [{"role": "user", "content": "x"}], [], 100)
        check("p3 RuntimeError levée", False, "aucune exception")
    except RuntimeError as e:
        check("p3 statut dans le message, clé rendue en ***",
              "HTTP 500" in str(e) and CLE not in str(e) and "***" in str(e), str(e))

    MT.httpx.Client = _Client0
    print(f"\n=== {ok} passed, {fail} failed ===")


if __name__ == "__main__":
    main()
    sys.exit(1 if fail else 0)
