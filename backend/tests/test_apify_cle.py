# -*- coding: utf-8 -*-
"""t364 (28/10/2026) — socle Apify, tâche 2 : la clé APIFY_TOKEN « comme les autres clés ». Secret du coffre, admise
par Réglages › Clés d'API (rubrique keys), console rappelée après une révocation, guide FR/EN, test du Diagnostic
(GET /v2/users/me, jeton en en-tête, jamais recopié), voyage dans l'archive chiffrée (même posée seulement en variable
d'environnement), état lu par l'onglet Prospects. Aucun réseau.
Run (depuis backend/) : & $PY tests/test_apify_cle.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzapifycle_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["APIFY_TOKEN"] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.api.routes import _ALLOWED_ENV_KEYS                         # noqa: E402
from app.api import settings_routes as SR                            # noqa: E402
from app.services import appairage as APR, coffre as CF, diagnostic as D, guides_fournisseurs as G   # noqa: E402

JETON = "apify_api_SECRET-CLE-42"
c = TestClient(app)

print("[1] la clé comme les autres")
check("1.1 secret du coffre", "APIFY_TOKEN" in CF.SECRETES)
check("1.2 admise par Réglages (allowlist)", "APIFY_TOKEN" in _ALLOWED_ENV_KEYS)
check("1.3 se règle dans Clés d'API", SR.RUBRIQUE_DE_CLE.get("APIFY_TOKEN") == "keys" and SR.rubrique_de("APIFY_TOKEN") == "keys")
con = [x for x in APR.CONSOLES if x["cle"] == "APIFY_TOKEN"]
check("1.4 console Apify rappelée après une révocation", con and con[0]["url"].startswith("https://console.apify.com/"), con)
g = G.GUIDES.get("APIFY_TOKEN") or {}
check("1.5 guide FR/EN, console et tarifs", g.get("fr") and g.get("en") and g.get("console", "").startswith("https://console.apify.com/")
      and g.get("tarifs", "").startswith("https://apify.com/"), g)
check("1.6 testable au Diagnostic", D.testable("APIFY_TOKEN"))
r = c.get("/api/settings/keys")
check("1.7 GET /api/settings/keys la liste", r.status_code == 200 and "APIFY_TOKEN" in {k["key"] for k in r.json()["keys"]}, r.text[:200])

print("[2] test du Diagnostic")
APPELS = []


async def faux_get(url, headers=None, timeout=15.0):
    APPELS.append((url, dict(headers or {})))
    if (headers or {}).get("Authorization") == f"Bearer {JETON}":
        return 200, {"data": {"username": "olivier", "plan": {"id": "FREE"}}}
    return 401, {"error": {"type": "token-not-valid", "message": "invalid " + (headers or {}).get("Authorization", "")}}


D._get = faux_get
r = asyncio.run(D.tester_cle("APIFY_TOKEN", JETON))
check("2.1 jeton accepté, compte rendu", r["ok"] is True and (r.get("details") or {}).get("compte") == "olivier", r)
check("2.2 GET /v2/users/me, jeton en en-tête, jamais dans l'URL",
      APPELS and APPELS[0][0] == "https://api.apify.com/v2/users/me" and all(JETON not in u for u, _h in APPELS), APPELS)
r = asyncio.run(D.tester_cle("APIFY_TOKEN", JETON + "x"))
check("2.3 jeton refusé : ok False, sans recopier la clé", r["ok"] is False and JETON not in json.dumps(r), r)   # le faux renvoie le jeton soumis

print("[3] transfert : l'archive chiffrée emporte la clé")
CF.poser("motdepasse-solide-1", {})
CF.ouvrir("motdepasse-solide-1")
CF.enregistrer_cle("APIFY_TOKEN", JETON)
a = CF.dechiffrer(CF.archiver("archive-solide-2"), "archive-solide-2")
check("3.1 posée au coffre : dans l'archive", a["cles"].get("APIFY_TOKEN") == JETON)
CF.ecrire_cle("APIFY_TOKEN", "")
a = CF.dechiffrer(CF.archiver("archive-solide-2"), "archive-solide-2")
check("3.2 retirée : plus dans l'archive", not a["cles"].get("APIFY_TOKEN"), a["cles"].get("APIFY_TOKEN"))
os.environ["APIFY_TOKEN"] = JETON
a = CF.dechiffrer(CF.archiver("archive-solide-2"), "archive-solide-2")
check("3.3 posée seulement en variable d'environnement : dans l'archive aussi", a["cles"].get("APIFY_TOKEN") == JETON)
os.environ["APIFY_TOKEN"] = ""
CF.fermer()

print("[4] l'onglet Prospects voit l'état, jamais la clé")
from app.config import settings                                      # noqa: E402
settings.APIFY_TOKEN = JETON
r = c.get("/api/prospects/recherche")
check("4.1 apify : configuré, plafonds", r.status_code == 200 and r.json().get("apify", {}).get("configure") is True
      and r.json()["apify"].get("plafonds_usd") == {"veille": 2.0, "leads": 1.0}, r.text[:300])
check("4.2 jamais le jeton", JETON not in r.text)
settings.APIFY_TOKEN = ""
check("4.3 sans clé : non configuré", c.get("/api/prospects/recherche").json()["apify"]["configure"] is False)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
