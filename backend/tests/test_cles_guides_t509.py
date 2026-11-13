# -*- coding: utf-8 -*-
"""t509 (13/11/2026) — chaque clé de service de Réglages › Clés d'API a son « Guide » et son « Tester », comme HeyGen ou
Figma ; les clés des écrans Campagnes, Prospects, Veille, Croissance et du Planificateur qui manquaient à la page y sont ;
les blocs de Comptes connectés ont leur lien « Guide » ; le refus Meta « API access blocked » (sous-code 5258005) est dit
en clair, en français et en anglais. Aucun réseau : chaque appel est simulé.
Run (depuis backend/) : & $PY tests/test_cles_guides_t509.py"""
import asyncio, json, os, pathlib, re, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt509_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("DECART_API_KEY", "KAPSO_API_KEY", "APIFY_TOKEN", "TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY",
          "IG_ACCESS_TOKEN", "IG_BUSINESS_ID"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.api.routes import _ALLOWED_ENV_KEYS                         # noqa: E402
from app.api import settings_routes as SR                            # noqa: E402
from app.services import appairage as APR, coffre as CF, diagnostic as D, guides_fournisseurs as G   # noqa: E402

# Les clés de SERVICE de la page Clés d'API (hors modèles, identifiants de voix, URL locale) : toutes ont Guide et Tester.
SERVICES = ("FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
            "MESHY_API_KEY", "FIGMA_TOKEN", "APIFY_TOKEN", "DECART_API_KEY", "KAPSO_API_KEY",
            "TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY")
NEUVES = ("DECART_API_KEY", "KAPSO_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY")

print("[1] chaque clé de service : guide, test, rangement")
for k in SERVICES:
    g = G.guide(k) or {}
    check(f"1.1 {k} : guide FR/EN, console et tarifs https, date de relecture",
          g.get("fr") and g.get("en") and str(g.get("console", "")).startswith("https://")
          and (str(g.get("tarifs", "")).startswith("https://") or g.get("tarifs") == "")   # vide = gratuit (Figma)
          and re.fullmatch(r"20\d\d-\d\d-\d\d", g.get("verifie_le", "")), g)
    check(f"1.2 {k} : testable", D.testable(k))
    check(f"1.3 {k} : admise par Réglages et rangée dans Clés d'API", k in _ALLOWED_ENV_KEYS and SR.rubrique_de(k) == "keys")
for k in NEUVES:
    check(f"1.4 {k} : secret du coffre", k in CF.SECRETES)
    check(f"1.5 {k} : console rappelée après une révocation",
          any(x["cle"] == k and x["url"].startswith("https://") for x in APR.CONSOLES))

print("[2] Comptes connectés : un guide par réseau (lu par le lien « Guide » du bloc)")
for k in ("X_API_KEY", "TELEGRAM_BOT_TOKEN", "YOUTUBE_CLIENT_ID", "IG_ACCESS_TOKEN", "TIKTOK_CLIENT_KEY"):
    g = G.guide(k) or {}
    check(f"2.1 {k} : guide FR/EN, console https", g.get("fr") and g.get("en") and str(g.get("console", "")).startswith("https://"), g)
gi = G.guide("IG_ACCESS_TOKEN") or {}
check("2.2 le guide Instagram nomme Unified login et les quatre autorisations",
      all(m in gi.get("fr", "") and m in gi.get("en", "") for m in ("Unified login", "instagram_basic", "instagram_content_publish",
                                                                     "instagram_manage_insights", "instagram_manage_comments")), gi)
check("2.3 le guide Instagram renvoie au chapitre du guide", "guide/fr.html#instagram" in gi.get("doc_fr", "")
      and "guide/en.html#instagram" in gi.get("doc_en", ""), gi)

print("[3] tests des clés neuves (appels simulés, gratuits, en lecture)")
APPELS = []
REPONSES = {}


async def faux_get(url, headers=None, timeout=15.0):
    APPELS.append((url, dict(headers or {})))
    for debut, rep in REPONSES.items():
        if url.startswith(debut):
            return rep(url, headers or {})
    return 599, {"error": "url inattendue"}


D._get = faux_get
SECRET = "SECRET-CLE-509-xyz"


def _attendu(entete, valeur, corps_ok):
    def rep(url, h):
        if h.get(entete) == valeur:
            return 200, corps_ok
        return 401, {"error": {"message": "invalid key " + str(h.get(entete))}}
    return rep


REPONSES["https://api.decart.ai/v1/credits"] = _attendu("x-api-key", SECRET, {"balance": 12.5})
r = asyncio.run(D.tester_cle("DECART_API_KEY", SECRET))
check("3.1 Decart : GET /v1/credits, clé en en-tête x-api-key", r["ok"] is True and APPELS[-1][0] == "https://api.decart.ai/v1/credits"
      and APPELS[-1][1].get("x-api-key") == SECRET, (r, APPELS[-1:]))
r = asyncio.run(D.tester_cle("DECART_API_KEY", SECRET + "z"))
check("3.2 Decart refusé : ok False, clé jamais recopiée", r["ok"] is False and SECRET not in json.dumps(r), r)

REPONSES["https://api.kapso.ai/platform/v1/whatsapp/phone_numbers"] = _attendu("X-API-Key", SECRET, {"data": [], "meta": {}})
r = asyncio.run(D.tester_cle("KAPSO_API_KEY", SECRET))
check("3.3 Kapso : GET phone_numbers?per_page=1, clé en en-tête X-API-Key",
      r["ok"] is True and APPELS[-1][0] == "https://api.kapso.ai/platform/v1/whatsapp/phone_numbers?per_page=1"
      and APPELS[-1][1].get("X-API-Key") == SECRET, (r, APPELS[-1:]))
r = asyncio.run(D.tester_cle("KAPSO_API_KEY", SECRET + "z"))
check("3.4 Kapso refusé : ok False, clé jamais recopiée", r["ok"] is False and SECRET not in json.dumps(r), r)
REPONSES["https://api.tavily.com/usage"] = _attendu("Authorization", f"Bearer {SECRET}", {"key": {"usage": 3, "limit": 1000}})
r = asyncio.run(D.tester_cle("TAVILY_API_KEY", SECRET))
check("3.6 Tavily : GET /usage (compteur, pas une recherche), Bearer", r["ok"] is True and APPELS[-1][0] == "https://api.tavily.com/usage"
      and APPELS[-1][1].get("Authorization") == f"Bearer {SECRET}", (r, APPELS[-1:]))
r = asyncio.run(D.tester_cle("TAVILY_API_KEY", SECRET + "z"))
check("3.7 Tavily refusé : ok False, clé jamais recopiée", r["ok"] is False and SECRET not in json.dumps(r), r)
n = len(APPELS)
for k in ("EXA_API_KEY", "SERPER_API_KEY"):
    r = asyncio.run(D.tester_cle(k, SECRET))
    check(f"3.8 {k} : aucun appel gratuit chez le fournisseur -> rien n'est appelé, on le dit (ok None)",
          r["ok"] is None and "gratuit" in r["message"] and len(APPELS) == n, r)
check("3.5 aucune clé dans une URL", all(SECRET not in u for u, _h in APPELS), APPELS)

print("[4] le message du test parle la langue de l'écran")
c = TestClient(app, client=("127.0.0.1", 50000))
REPONSES["https://api.decart.ai/v1/credits"] = _attendu("x-api-key", SECRET, {"balance": 3})
rf = c.post("/api/reglages/diagnostic/cle", json={"nom": "DECART_API_KEY", "valeur": SECRET}, headers={"Accept-Language": "fr"})
re_ = c.post("/api/reglages/diagnostic/cle", json={"nom": "DECART_API_KEY", "valeur": SECRET}, headers={"Accept-Language": "en"})
check("4.1 FR : « clé acceptée »", rf.status_code == 200 and rf.json()["message"].startswith("clé acceptée"), rf.text[:200])
check("4.2 EN : « key accepted »", re_.status_code == 200 and re_.json()["message"].startswith("key accepted"), re_.text[:200])
re2 = c.post("/api/reglages/diagnostic/cle", json={"nom": "DECART_API_KEY", "valeur": SECRET + "z"}, headers={"Accept-Language": "en"})
check("4.3 EN : refus « rejected (401) »", re2.json()["message"].startswith("rejected (401)") and SECRET not in re2.text, re2.text[:200])
re3 = c.post("/api/reglages/diagnostic/cle", json={"nom": "ELEVENLABS_VOICE_ID_FR", "valeur": "abc"}, headers={"Accept-Language": "en"})
check("4.4 EN : « no test for this key »", re3.json()["message"] == "no test for this key", re3.text[:200])
check("4.5 sans en-tête : le français d'avant, à l'octet",
      asyncio.run(D.tester_cle("ELEVENLABS_VOICE_ID_FR", "abc"))["message"] == "pas de test pour cette clé")

print("[5] Instagram : « API access blocked » (5258005) dit en clair")
from app.services import meta_erreurs as ME                          # noqa: E402
from app.i18n import texte as _texte                                  # noqa: E402
BLOQUE = {"error": {"message": "API access blocked.", "type": "OAuthException", "code": 200, "error_subcode": 5258005,
                    "fbtrace_id": "Axyz"}}
m = ME.expliquer(BLOQUE)
check("5.1 5258005 reconnu", m is not None and "5258005" in _texte(m, "fr") and "5258005" in _texte(m, "en"), m)
check("5.2 FR : l'application Meta est bloquée, renvoi au guide", m is not None and "application Meta" in _texte(m, "fr")
      and "guide" in _texte(m, "fr").lower(), m)
check("5.3 EN : the Meta app is blocked", m is not None and "Meta app" in _texte(m, "en"), m and _texte(m, "en"))
for sc, mot in ((5258004, "archiv"), (5258006, "supprim")):
    mm = ME.expliquer({"error": {"code": 200, "error_subcode": sc, "type": "OAuthException"}})
    check(f"5.4 {sc} reconnu ({mot})", mm is not None and mot in _texte(mm, "fr"), mm)
mm = ME.expliquer({"error": {"code": 190, "type": "OAuthException", "message": "Error validating access token"}})
check("5.5 code 190 : jeton expiré ou révoqué", mm is not None and "jeton" in _texte(mm, "fr").lower() and "token" in _texte(mm, "en"), mm)
check("5.6 autre erreur : rien (le détail brut reste)", ME.expliquer({"error": {"code": 4}}) is None and ME.expliquer("x") is None
      and ME.expliquer('{"error":{"code":200,"error_subcode":5258005}}') is not None)

from app.services import verif_canaux as V                          # noqa: E402
check("5.7 verif_canaux : code « app_bloquee » au jeu fermé", "app_bloquee" in V.CODES)
from app.services import comptes as CPT                               # noqa: E402


async def get_bloque(url, headers=None, params=None):
    return 400, BLOQUE


V._get = get_bloque
os.environ["IG_ACCESS_TOKEN"] = "EAAbanc-SECRET-IG"; os.environ["IG_BUSINESS_ID"] = "17840000000000000"
from app.config import settings                                       # noqa: E402
settings.IG_ACCESS_TOKEN = "EAAbanc-SECRET-IG"; settings.IG_BUSINESS_ID = "17840000000000000"
rv = asyncio.run(V.verifier_plateforme("instagram"))
check("5.8 verif_canaux : rouge, code app_bloquee, raison claire, jeton absent",
      rv["etat"] == "rouge" and rv["code"] == "app_bloquee" and "5258005" in rv["raison"] and "EAAbanc" not in json.dumps(rv), rv)

from app.services import instagram_publisher as IP                   # noqa: E402


class _R:
    status_code = 400
    text = json.dumps(BLOQUE)
    def json(self):
        return BLOQUE


class _C:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def get(self, *a, **k): return _R()


IP._client = lambda *a, **k: _C()
rf = c.post("/api/channels/test", json={"channel": "instagram"}, headers={"Accept-Language": "fr"})
re_ = c.post("/api/channels/test", json={"channel": "instagram"}, headers={"Accept-Language": "en"})
check("5.9 « Vérifier les identifiants » FR : explication puis détail brut",
      rf.status_code == 200 and rf.json()["ok"] is False and rf.json()["detail"].startswith("Meta bloque")
      and "5258005" in rf.json()["detail"] and "EAAbanc" not in rf.text, rf.text[:300])
check("5.10 « Verify credentials » EN : explanation first",
      re_.json()["detail"].startswith("Meta is blocking") and "EAAbanc" not in re_.text, re_.text[:300])

print("[6] traductions")
dico = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
neufs = {k: v for k, v in dico.items() if k.startswith(("diag.cle.", "meta.erreur."))}
check("6.1 messages diag.cle.* et meta.erreur.* : FR et EN, mêmes variables",
      len(neufs) >= 8 and all(v.get("fr") and v.get("en") and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
                              for v in neufs.values()), neufs)
esp = json.loads((RACINE / "frontend" / "shared" / "i18n" / "espaces.json").read_text("utf-8"))
check("6.2 espaces.assistant.code_app_bloquee FR/EN", esp.get("espaces.assistant.code_app_bloquee", {}).get("en"))
reg = json.loads((RACINE / "frontend" / "shared" / "i18n" / "reglages.json").read_text("utf-8"))
for k in ("reglages.cles.tester_sans_cle", "reglages.cles.tavily", "reglages.cles.tavily_why", "reglages.cles.exa",
          "reglages.cles.exa_why", "reglages.cles.serper", "reglages.cles.serper_why", "reglages.comptes.guide_titre"):
    check(f"6.3 {k} FR/EN", reg.get(k, {}).get("fr") and reg.get(k, {}).get("en"))

print("[7] l'écran (maillon dzclesguides)")
B = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text("utf-8")
check("7.1 marqueur posé une fois", B.count("/*dzclesguides*/") >= 1)
check("7.2 Tester visible même sans clé, grisé avec sa raison",
      'gu?r.jsx(K,{icon:"dz-action-tester"' in B and "disabled:!def_" in B and 'dzT("reglages.cles.tester_sans_cle")' in B)
check("7.3 lignes Tavily, Exa, Serper dans Clés d'API",
      all(f'{{k:"{k}",label:dzT("reglages.cles.{n}")' in B for k, n in (("TAVILY_API_KEY", "tavily"), ("EXA_API_KEY", "exa"),
                                                                       ("SERPER_API_KEY", "serper"))))
check("7.4 Comptes connectés : lien Guide par bloc (guide de son premier champ)", "DzGuideCompte" in B and "k.fields[0].k" in B)

sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                                          # noqa: E402
import patch_bundle_dzclesguides as PM                                # noqa: E402
check("7.5 avant_dzclesguides == defaire, et sans marqueur rendu tel quel",
      AIDE.avant_dzclesguides(B) == PM.defaire(B) and AIDE.avant_dzclesguides(PM.defaire(B)) == PM.defaire(B))
aide = (_ICI / "_i18n_l1_aide.py").read_text("utf-8")
i = aide.index("def avant_dzigformat(")
corps = aide[i:aide.index("\ndef ", i + 10)]
check("7.6 appelé EN TÊTE de avant_dzigformat", "bundle = avant_dzclesguides(bundle)" in corps
      and corps.index("avant_dzclesguides(") < corps.index("if _m.MARKER not in bundle"))
check("7.7 marqueur x4, une pose par paire", B.count(PM.MARKER) == PM.MARKER_ATTENDU == 4)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
