# -*- coding: utf-8 -*-
"""Les routes News du filtre et du classement (plan 2026-09-03 T5, tache #33 du suivi, 30/09/2026).

Aucun reseau : le cache est ECRIT a la main sur le disque, `summarizer._chat_dispatch` est un espion qui compte ses
appels. Banc-miroir : JSON rendu par la route, fichier de reglages relu sur le disque, lignes du registre des
depenses relues en base. Le score LLM est PAYANT : par defaut zero appel ; `llm=true` passe par la garde des
plafonds (402 sans depense au-dessus du plafond, puis un appel et une ligne « news » une fois confirme).
Run (depuis backend/) : & $PY tests/test_news_routes.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewsr_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import summarizer, plafonds as P                  # noqa: E402
from app.services.news_service import news_service                  # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


appels = []
def _espion(p, s, m):
    appels.append(p)
    return json.dumps([{"id": "a1", "score": 91, "pourquoi": "coeur du brief"}]), "anthropic"
summarizer._chat_dispatch = _espion
summarizer.active_provider = lambda: "anthropic"      # une cle « reglee » : le devis n'est pas gratuit

# Dates RELATIVES a l'horloge : en dur (2026-09-03), a2 puis a1 sortaient de la fenetre de 30 jours au fil des
# jours et [E] tombait en KeyError 'a2' le 03/10/2026 sans changement de code. Ordre garde : a2 < a1 < fetched_at.
_MAINTENANT = datetime.now(timezone.utc).replace(microsecond=0)
PUBLIE_A1 = (_MAINTENANT - timedelta(hours=1)).isoformat()
PUBLIE_A2 = (_MAINTENANT - timedelta(hours=2)).isoformat()
RAMASSE_LE = (_MAINTENANT - timedelta(minutes=30)).isoformat()
FRAICHEUR_BANC_H = 24 * 30                            # la fenetre que les sections posent avant de classer

ARTICLES = [
    {"id": "a1", "source_id": "s1", "source_name": "CoinDesk", "title": "Solana network hits record daily transactions",
     "summary": "", "link": "https://c/1", "published": PUBLIE_A1, "doublons": []},
    {"id": "a2", "source_id": "s2", "source_name": "Spammy Feed", "title": "Free giveaway airdrop inside",
     "summary": "", "link": "https://s/1", "published": PUBLIE_A2, "doublons": []},
]


def _poser_cache(items=None):
    news_service.cache_path.parent.mkdir(parents=True, exist_ok=True)
    news_service.cache_path.write_text(json.dumps(
        {"fetched_at": RAMASSE_LE, "items": ARTICLES if items is None else items,
         "errors": [], "source_count": 2, "merged_count": 0}, ensure_ascii=False), encoding="utf-8")


def _lignes():
    async def f():
        async with async_session_factory() as s:
            return (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()
    return asyncio.run(f())


asyncio.run(init_db())
print("\n[0] temoin d'horloge : le banc ne depend pas de la date du jour")
_ages_h = [(datetime.now(timezone.utc) - datetime.fromisoformat(a["published"])).total_seconds() / 3600 for a in ARTICLES]
check("T1 chaque article du fixture est DANS la fenetre de fraicheur du banc (et date du passe)",
      all(0 < h < FRAICHEUR_BANC_H for h in _ages_h), str(_ages_h))
check("T2 l'ordre est garde : a2 plus ancien que a1, ramasse apres les deux",
      PUBLIE_A2 < PUBLIE_A1 < RAMASSE_LE, f"{PUBLIE_A2} {PUBLIE_A1} {RAMASSE_LE}")

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[A] reglages du filtre")
    r = c.get("/api/news/filter")
    check("A1 GET /news/filter : 200 et la fraicheur", r.status_code == 200 and "fraicheur_h" in r.json(), f"{r.status_code} {r.text[:200]}")
    r = c.put("/api/news/filter", json={"mots_cles": ["Solana"], "sources_noires": [], "mots_noirs": ["giveaway"],
                                        "fraicheur_h": 24 * 30})
    check("A2 PUT rend les reglages NORMALISES", r.status_code == 200 and r.json().get("mots_cles") == ["solana"], r.text[:200])
    from app.services import news_filter as F
    sur = json.loads(F.chemin_reglages().read_text("utf-8")) if F.chemin_reglages().is_file() else {}
    check("A3 et les ecrit sur le disque", sur.get("mots_noirs") == ["giveaway"], str(sur))
    check("A4 fraicheur 0 : 422", c.put("/api/news/filter", json={"fraicheur_h": 0}).status_code == 422)
    check("A5 fraicheur > 30 jours : 422", c.put("/api/news/filter", json={"fraicheur_h": 24 * 31}).status_code == 422)

    print("\n[B] classement du jour, gratuit par defaut")
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": ["giveaway"], "fraicheur_h": 24 * 30})
    _poser_cache()
    appels.clear()
    r = c.post("/api/news/rank", json={"brief": "crypto Solana"})
    j = r.json() if r.status_code == 200 else {}
    check("B1 POST /news/rank : 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    check("B2 garde a1, en tete, score deterministe", [i["id"] for i in j.get("items", [])] == ["a1"]
          and j["items"][0]["en_tete"] is True and j["items"][0]["score_origine"] == "deterministe", str(j)[:300])
    check("B3 l'ecarte et son motif sont rendus", j.get("ecartes") == [{"id": "a2", "title": "Free giveaway airdrop inside",
                                                                         "motif": "mot sur liste noire"}], str(j.get("ecartes")))
    check("B4 le compte", j.get("compte") == {"lus": 2, "gardes": 1, "ecartes": 1}, str(j.get("compte")))
    check("B5 AUCUN appel payant et rien au registre sans llm", appels == [] and _lignes() == [], f"{len(appels)} {len(_lignes())}")

    print("\n[C] le LLM sur demande, sous la garde des plafonds")
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post("/api/news/rank", json={"brief": "crypto Solana", "llm": True})
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
    dp = (d or {}).get("dz_plafond", {}) if isinstance(d, dict) else {}
    check("C1 au-dessus du plafond : 402 dz_plafond, categorie news", r.status_code == 402 and dp.get("motif") == "global"
          and "news" in dp.get("message", ""), f"{r.status_code} {r.text[:300]}")
    check("C2 refus : zero appel, rien au registre", appels == [] and _lignes() == [], f"{len(appels)}")
    r = c.post("/api/news/rank", json={"brief": "crypto Solana", "llm": True}, headers={"X-DZ-Plafond": "confirme"})
    j = r.json() if r.status_code == 200 else {}
    L = _lignes()
    check("C3 confirme : 200, UN appel, score du LLM", r.status_code == 200 and len(appels) == 1
          and j["items"][0]["score"] == 91 and j["items"][0]["score_origine"] == "anthropic", f"{r.status_code} {str(j)[:300]}")
    check("C4 la depense est inscrite : anthropic, news, llm", len(L) == 1 and L[0].moteur == "anthropic"
          and L[0].categorie == "news" and L[0].op == "llm" and L[0].estime_usd > 0,
          str([(l.moteur, l.categorie, l.op, l.estime_usd) for l in L]))
    check("C5 l'ecarte n'est PAS envoye au LLM (P1)", "giveaway" not in appels[0] if appels else False)
    P.enregistrer({"global_usd": 0, "par_moteur": {}})
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": ["solana", "giveaway"],
                                    "fraicheur_h": 24 * 30})
    appels.clear()
    n0 = len(_lignes())
    r = c.post("/api/news/rank", json={"brief": "x", "llm": True})
    check("C6 llm demande mais tout est ecarte : ni appel ni ligne", r.status_code == 200 and appels == []
          and len(_lignes()) == n0 and r.json()["items"] == [], f"{r.status_code} {len(appels)}")

    print("\n[D] bords")
    _poser_cache(items=[])
    r = c.post("/api/news/rank", json={"brief": ""})
    check("D1 cache vide : liste vide, lus 0", r.status_code == 200 and r.json()["items"] == []
          and r.json()["compte"]["lus"] == 0, r.text[:200])
    check("D2 brief trop long : 422", c.post("/api/news/rank", json={"brief": "x" * 2001}).status_code == 422)

print("\n[E] memoire et equilibre dans le classement (T8, tache #34)")
from app.services import news_memory as M                           # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    if M.chemin_couverture().is_file():
        M.chemin_couverture().unlink()
    _poser_cache()
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": [], "fraicheur_h": 24 * 30})
    avant = {i["id"]: i for i in c.post("/api/news/rank", json={"brief": ""}).json()["items"]}
    check("E0 temoin : memoire vide, aucune marque ni malus", avant["a1"].get("deja_couvert") is None
          and "sur-representee" not in avant["a1"]["score_pourquoi"], str(avant.get("a1")))
    M.noter_couverture([{"title": "Solana network hits a record in daily transactions", "source_id": "s1",
                         "source_name": "CoinDesk"}], post_id="p1")
    j = {i["id"]: i for i in c.post("/api/news/rank", json={"brief": ""}).json()["items"]}
    check("E1 un sujet deja couvert est marque, l'autre non", j["a1"].get("deja_couvert") == "Solana network hits a record in daily transactions"
          and j["a2"].get("deja_couvert") is None, str(j.get("a1")))
    for n in range(6):
        M.noter_couverture([{"title": f"Un sujet CoinDesk de plus numero {n}", "source_id": "s1", "source_name": "CoinDesk"}], post_id=f"q{n}")
    M.noter_couverture([{"title": "Un sujet Spammy", "source_id": "s2", "source_name": "Spammy Feed"}], post_id="q9")
    j = {i["id"]: i for i in c.post("/api/news/rank", json={"brief": ""}).json()["items"]}
    check("E2 la source sur-representee perd des points, et le motif le dit", j["a1"]["score"] < avant["a1"]["score"]
          and "source sur-representee" in j["a1"]["score_pourquoi"] and j["a2"]["score"] == avant["a2"]["score"],
          f'{avant["a1"]["score"]} -> {j["a1"]["score"]} {j["a1"]["score_pourquoi"]}')
    if M.chemin_couverture().is_file():
        M.chemin_couverture().unlink()

print("\n[F] formes, tendances et signal X (T11, T14, tache #35)")
from app.config import settings                                     # noqa: E402
from app.services import news_trends as NT                           # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    f = c.get("/api/news/forms").json().get("forms", [])
    check("F1 GET /news/forms : cinq formes, chacune dit si elle est payante et disponible",
          len(f) == 5 and f[0]["id"] == "cartes" and f[0]["disponible"] is True and all("payant" in x and "disponible" in x for x in f), str(f)[:200])
    r = c.post("/api/news/forms/estimate", json={"forme": "illustration_ia", "items": [ARTICLES[0]], "options": {"model": "flux"}})
    check("F2 devis d'une forme payante : 200 et un total > 0", r.status_code == 200 and r.json()["total_usd"] > 0, r.text[:200])
    r = c.post("/api/news/forms/estimate", json={"forme": "cartes", "items": [ARTICLES[0]]})
    check("F3 devis des cartes : 0 $", r.status_code == 200 and r.json()["total_usd"] == 0, r.text[:200])
    r = c.post("/api/news/forms/estimate", json={"forme": "hologramme", "items": [ARTICLES[0]]})
    check("F4 forme inconnue : 400 motive", r.status_code == 400 and "hologramme" in r.text, r.text[:200])
    check("F5 selection vide : 422", c.post("/api/news/forms/estimate", json={"forme": "cartes", "items": []}).status_code == 422)
    fondu = dict(ARTICLES[0], doublons=[{"source_name": "Decrypt"}, {"source_name": "The Block"}])
    _poser_cache([fondu, ARTICLES[1]])
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": [], "fraicheur_h": 24 * 30})
    j = {i["id"]: i for i in c.post("/api/news/rank", json={"brief": ""}).json()["items"]}
    check("F6 le classement porte la tendance : a1 (3 medias fondus) oui, a2 non", j["a1"]["tendance"] is True
          and j["a1"]["tendance_sources"] == 3 and j["a2"]["tendance"] is False, str(j.get("a1"))[:200])
    lus = []
    NT._lire_x = lambda q: (lus.append(q), {"posts": 10})[1]
    r = c.get("/api/news/trends").json()
    check("F7 GET /news/trends sans requete : tendances locales, AUCUNE lecture X", r["x"] is None and lus == []
          and [t["id"] for t in r["tendances"]] == ["a1"], str(r))
    cles = (settings.X_API_KEY, settings.X_API_SECRET, settings.X_ACCESS_TOKEN, settings.X_ACCESS_SECRET)
    settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = ""
    r = c.get("/api/news/trends?x_query=solana").json()
    check("F8 sans cle X : refus lisible, aucune lecture", r["x"]["posts"] is None and "cle X" in r["x"]["motif"] and lus == [], str(r["x"]))
    settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = "k"
    r = c.get("/api/news/trends?x_query=solana").json()
    check("F9 avec cle : une lecture, comptee", r["x"]["posts"] == 10 and lus == ["solana"], str(r["x"]))
    settings.X_API_KEY, settings.X_API_SECRET, settings.X_ACCESS_TOKEN, settings.X_ACCESS_SECRET = cles
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
with TestClient(app, client=("203.0.113.9", 50000), headers=_JA.entetes(app)) as c2:
    check("F10 hors de la machine : la lecture X est refusee (403), la tendance locale reste lisible",
          c2.get("/api/news/trends?x_query=solana").status_code == 403 and c2.get("/api/news/trends").status_code == 200 and lus == ["solana"])

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
