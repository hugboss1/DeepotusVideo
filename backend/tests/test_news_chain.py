# -*- coding: utf-8 -*-
"""La chaine article -> post (plan 2026-09-03 T12-T13, tache #35 du suivi, 30/09/2026).

Decisions de l'utilisateur : preparer est GRATUIT (aucun appel LLM meme avec une cle) ; polir est payant et garde ;
valider programme UN post avec le job_id de son reel « cartes » (ffmpeg local), la couverture est notee au rendu
reussi. Aucun reseau : `summarizer.rewrite_script` est un espion, `pipeline.run_news_illustration` un faux.
Temoin positif : a la base (8d9ea97), generate_news_script n'a pas de `polir` et aucune route /news/chain n'existe.
Run (depuis backend/) : & $PY tests/test_news_chain.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewsc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.api.routes import pipeline                                 # noqa: E402
from app.services import summarizer, news_chain as NC, news_memory as M, plafonds as P, schedule_slots  # noqa: E402
from app.services.news_service import news_service                  # noqa: E402
from app.services.storage import ScheduledPost, async_session_factory, init_db  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


polis = []
summarizer.available = lambda: True                    # une cle « reglee » : le polissage SERAIT possible
summarizer.active_provider = lambda: "anthropic"
summarizer.rewrite_script = lambda s, **k: (polis.append(s), ("Poli par le modele. " + s, "anthropic"))[1]
rendus = []
async def _faux_rendu(items, **k):
    rendus.append((k.get("job_id"), [i.get("title") for i in items]))
    if items and items[0].get("title", "").startswith("ECHEC"):
        raise RuntimeError("rendu en echec")
    return k.get("job_id")
pipeline.run_news_illustration = _faux_rendu

MAINTENANT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
# Creneaux de [D] RELATIFS au jour : en dur (2026-10-04/05/06), ils passaient dans le passe au fil des jours.
# Heures fixes (17:30 UTC, 10:00) pour garder la forme des assertions ; J+1, J+2, J+3 donc toujours dans le futur.
_JOUR = datetime.now(timezone.utc).date()
CRENEAU_D1 = f"{_JOUR + timedelta(days=1)}T17:30"
CRENEAU_D7 = f"{_JOUR + timedelta(days=2)}T10:00"
CRENEAU_D8 = f"{_JOUR + timedelta(days=3)}T10:00"
ARTICLES = [
    {"id": "a1", "source_id": "s1", "source_name": "CoinDesk", "title": "Solana network hits record daily transactions",
     "summary": "Solana usage climbs.", "link": "https://www.coindesk.com/a", "published": MAINTENANT, "doublons": []},
    {"id": "a2", "source_id": "s2", "source_name": "BBC", "title": "Storm Bernard floods southern Spain",
     "summary": "Heavy rain.", "link": "https://bbc.co.uk/b", "published": MAINTENANT, "doublons": []},
    {"id": "a3", "source_id": "s3", "source_name": "Decrypt", "title": "Bitcoin ETF outflows accelerate this week",
     "summary": "Outflows.", "link": "https://decrypt.co/c", "published": MAINTENANT, "doublons": []},
]


def _poser_cache(items):
    news_service.cache_path.parent.mkdir(parents=True, exist_ok=True)
    news_service.cache_path.write_text(json.dumps({"fetched_at": MAINTENANT, "items": items, "errors": []}), encoding="utf-8")


def _posts():
    async def f():
        async with async_session_factory() as s:
            return (await s.execute(select(ScheduledPost))).scalars().all()
    return asyncio.run(f())


print("\n[T] temoins")
r0 = subprocess.run(["git", "show", "8d9ea97:backend/app/services/prompt_engine.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", "8d9ea97:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 a la base, generate_news_script n'a pas de polir et /news/chain n'existe pas",
      r0.returncode == 0 and b"polir" not in r0.stdout and b"/news/chain" not in r1.stdout)

print("\n[A] creneau propose (Scheduler)")
schedule_slots.save({"x": ["08:30", "19:30"], "_tz": -120})           # Paris l'ete : local = UTC + 2 h
ref = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)                  # 14 h locale
check("A1 le prochain creneau local (19:30) converti en UTC (17:30)", NC._creneau_propose("x", ref) == "2026-09-03T17:30:00+00:00",
      NC._creneau_propose("x", ref))
ref = datetime(2026, 9, 3, 18, 0, tzinfo=timezone.utc)                  # 20 h locale : 19:30 passe
check("A2 creneaux passes : le premier de demain (08:30 local = 06:30 UTC)", NC._creneau_propose("x", ref) == "2026-09-04T06:30:00+00:00",
      NC._creneau_propose("x", ref))
check("A3 un canal sans creneau regle prend ceux par defaut du Scheduler", NC._creneau_propose("telegram", ref).startswith("2026-09-04T"))

asyncio.run(init_db())
_poser_cache(ARTICLES)
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": [], "fraicheur_h": 48})
    print("\n[B] preparer : gratuit")
    polis.clear()
    r = c.post("/api/news/chain/preview", json={"brief": "crypto Solana", "articles_max": 2})
    lot = r.json() if r.status_code == 200 else {}
    check("B1 200 ; deux articles, le brief devant", r.status_code == 200 and [a["id"] for a in lot.get("articles", [])][:1] == ["a1"]
          and len(lot["articles"]) == 2, f"{r.status_code} {r.text[:300]}")
    check("B2 AUCUN appel de polissage, meme avec une cle, et le lot le dit (poli = false)", polis == [] and lot.get("poli") is False, str(len(polis)))
    check("B3 forme par defaut : les cartes gratuites, devis 0 $", lot.get("forme") == "cartes" and lot["cout"]["total_usd"] == 0)
    check("B4 legende avec sa ligne de sources, voix choisie avec son motif", lot["caption"].rstrip().endswith(lot["sources_line"])
          and lot["sources_line"].startswith("Sources: ") and lot["voice_mode"] in ("oracle", "alpha", "zen", "memer") and lot["voice_mode_reason"])
    check("B5 creneau propose au format ISO, dans le futur", datetime.fromisoformat(lot["creneau"]) > datetime.now(timezone.utc), lot.get("creneau"))
    check("B6 rien n'est ecrit : aucun post, aucune couverture", _posts() == [] and M.sujets_couverts() == [])
    r = c.post("/api/news/chain/preview", json={"forme": "plans_seedance", "articles_max": 1})
    check("B7 une forme payante est CHIFFREE (rien de tire)", r.status_code == 200 and r.json()["cout"]["total_usd"] > 0 and polis == [])
    check("B8 forme inconnue : 400 motive", c.post("/api/news/chain/preview", json={"forme": "hologramme"}).status_code == 400)
    c.put("/api/news/filter", json={"mots_cles": ["introuvable"], "sources_noires": [], "mots_noirs": [], "fraicheur_h": 48})
    r = c.post("/api/news/chain/preview", json={})
    check("B9 rien ne passe le filtre : 400 qui dit quoi faire", r.status_code == 400 and "filtre" in r.text, r.text[:200])
    c.put("/api/news/filter", json={"mots_cles": [], "sources_noires": [], "mots_noirs": [], "fraicheur_h": 48})

    print("\n[C] polir : payant, garde")
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post("/api/news/chain/polish", json={"script": lot["script"], "voice_mode": lot["voice_mode"]})
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else {}
    check("C1 au-dessus du plafond : 402 dz_plafond, AUCUN appel", r.status_code == 402 and isinstance(d, dict) and "dz_plafond" in d and polis == [],
          f"{r.status_code} {r.text[:200]}")
    r = c.post("/api/news/chain/polish", json={"script": lot["script"], "voice_mode": lot["voice_mode"]}, headers={"X-DZ-Plafond": "confirme"})
    j = r.json()
    check("C2 confirme : un appel, script poli (et filtre de marque applique)", r.status_code == 200 and len(polis) == 1 and j["poli"] is True
          and j["script"].startswith("Poli par le modele.") and j["fournisseur"] == "anthropic", r.text[:200])
    summarizer.rewrite_script = lambda s, **k: (polis.append(s), ("Buy the lambo now, LFG friends.", "anthropic"))[1]
    j = c.post("/api/news/chain/polish", json={"script": "brouillon"}, headers={"X-DZ-Plafond": "confirme"}).json()
    check("C2b le texte poli repasse le filtre de marque (lambo, LFG retires)", "lambo" not in j["script"].lower()
          and "lfg" not in j["script"].lower() and j["script"].startswith("Buy the"), j["script"])
    P.enregistrer({"global_usd": 0, "par_moteur": {}})
    summarizer.rewrite_script = lambda s, **k: (polis.append(s), (None, ""))[1]
    r = c.post("/api/news/chain/polish", json={"script": "brouillon"}).json()
    check("C3 sans reponse du fournisseur : brouillon garde, dit", r["script"] == "brouillon" and r["poli"] is False and r["motif"])
    check("C4 script vide : 422", c.post("/api/news/chain/polish", json={"script": ""}).status_code == 422)

    print("\n[D] valider : un post programme avec son reel cartes")
    _maint = datetime.now(timezone.utc)
    check("D0 temoin d'horloge : les trois creneaux de [D] sont dans le FUTUR, quelle que soit la date du jour",
          all(datetime.fromisoformat(f"{x}:00+00:00") > _maint for x in (CRENEAU_D1, CRENEAU_D7, CRENEAU_D8)),
          f"{CRENEAU_D1} {CRENEAU_D7} {CRENEAU_D8}")
    lot2 = dict(lot, creneau=f"{CRENEAU_D1}:00+00:00")
    r = c.post("/api/news/chain/commit", json={"lot": lot2, "channels": ["x", "telegram"], "mode": "assisted"})
    j = r.json() if r.status_code == 200 else {}
    posts = [p for p in _posts() if p.id == j.get("post_id")]
    p = posts[0] if posts else None
    check("D1 200 : post programme, canaux, creneau, legende", r.status_code == 200 and p is not None and p.status == "scheduled"
          and set(p.channels.split(",")) == {"x", "telegram"} and p.run_at.isoformat().startswith(CRENEAU_D1) and p.caption == lot["caption"],
          f"{r.status_code} {r.text[:200]}")
    check("D2 le post porte le job_id de son reel (il a donc un media pour le Scheduler)", p is not None and p.job_id == j.get("job_id") and p.job_id)
    check("D3 le reel cartes a ete lance avec CE job_id et les articles du lot", rendus and rendus[-1][0] == j.get("job_id")
          and rendus[-1][1] == [a["title"] for a in lot["articles"]], str(rendus[-1:]))
    s = M.sujets_couverts()
    check("D4 rendu reussi : la couverture est notee UNE fois, avec le post_id", len(s) == len(lot["articles"]) and {x["post_id"] for x in s} == {j.get("post_id")},
          str(s)[:200])
    n_posts, n_suj = len(_posts()), len(M.sujets_couverts())
    r = c.post("/api/news/chain/commit", json={"lot": dict(lot, creneau="demain matin"), "channels": ["x"]})
    check("D5 creneau illisible : 400 AVANT toute ecriture", r.status_code == 400 and "creneau" in r.text
          and len(_posts()) == n_posts and len(M.sujets_couverts()) == n_suj, r.text[:200])
    r = c.post("/api/news/chain/commit", json={"lot": dict(lot, articles=[]), "channels": ["x"]})
    check("D6 lot sans article : 400 motive, rien ecrit", r.status_code == 400 and "aucun article" in r.text and len(_posts()) == n_posts)
    echec = dict(lot, articles=[dict(lot["articles"][0], title="ECHEC du rendu")], creneau=f"{CRENEAU_D7}:00+00:00")
    r = c.post("/api/news/chain/commit", json={"lot": echec, "channels": ["x"]})
    check("D7 rendu en echec : le post existe (job failed lisible), mais AUCUNE couverture notee", r.status_code == 200
          and len(_posts()) == n_posts + 1 and len(M.sujets_couverts()) == n_suj)
    r = c.post("/api/news/chain/commit", json={"lot": dict(lot, creneau=f"{CRENEAU_D8}:00"), "channels": [""]})
    p = [x for x in _posts() if x.id == r.json().get("post_id")]
    check("D8 creneau sans fuseau = UTC ; canal vide -> x", r.status_code == 200 and p and p[0].channels == "x"
          and p[0].run_at.isoformat().startswith(CRENEAU_D8), r.text[:200])

print("\n[E] le chemin d'avant (/news/script) polit toujours par defaut")
polis.clear()
summarizer.rewrite_script = lambda s, **k: (polis.append(s), ("Poli par le modele. " + s, "anthropic"))[1]
b = pipeline.engine.generate_news_script(ARTICLES[:1], max_words=60)
check("E1 temoin : sans polir=False, UN appel et le script poli", len(polis) == 1 and b.script.startswith("Poli par le modele.")
      and any("LLM-polished" in x for x in b.rationale), str(b.rationale))
b = pipeline.engine.generate_news_script(ARTICLES[:1], max_words=60, polir=False)
check("E2 polir=False : aucun appel de plus, et le motif le dit", len(polis) == 1 and any("not requested" in x for x in b.rationale), str(b.rationale))

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
