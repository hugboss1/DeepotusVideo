# -*- coding: utf-8 -*-
"""t380 (30/10/2026) — FILS SOCIAUX SUIVIS dans News (serveur et outil des agents), décision D4 du plan du 29/10.

Ce que ce banc garde, par sections :
  1. Les identifiants : une plateforme de la liste (X, Instagram, TikTok, YouTube, Reddit ; jamais LinkedIn), un
     identifiant normalisé (pseudo, communauté, chaîne UC…), le flux gratuit de YouTube et de Reddit.
  2. L'ajout à la main par les routes /api/news/fils : origine « main », fréquence choisie, pause, retrait.
  3. La lecture GRATUITE (RSS/Atom) : éléments normalisés vers le cache de News, sans auteur tiers (Reddit).
  4. La lecture PAYANTE (Apify) : devis, accord (confirme_cout, plafond par relevé), refus avant tout run (sans
     clé, sans accord, devis au-delà du plafond du fil, plafond mensuel « news »), coût réel noté, échec noté.
  5. La boucle : un fil n'est lu qu'à son heure, jamais en pause, jamais un fil Apify sans accord.
  6. Les suggestions : `proposer_fil` (agent Campagnes, boîte « fils ») ne fait que SUGGÉRER ; accepter, écarter.
  7. Le classement : un élément de fil entre dans /api/news/rank avec sa plateforme ; un rafraîchissement complet
     des sources ne l'efface pas.
Aucun réseau : flux XML écrits ici (feedparser lit une chaîne), Apify remplacé par des faux (`AP.devis`,
`AP.lancer`, `AP.configure`). Données isolées. Run (depuis backend/) : & $PY tests/test_news_fils.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfils_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "APIFY_TOKEN"):
    os.environ[k] = ""
os.environ.setdefault("FAL_KEY", "cle-de-banc")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
from sqlalchemy import select                                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import apify as AP, news_fils as NF, plafonds as P, espaces as E   # noqa: E402
from app.services import agent_outils as ao, agent_boites as B      # noqa: E402
from app.services.news_service import news_service                  # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


_MAINT = datetime.now(timezone.utc).replace(microsecond=0)
def _rfc(h):   # une date RSS relative à l'horloge (un banc daté en dur finit par sortir de la fenêtre de fraîcheur)
    return (_MAINT - timedelta(hours=h)).strftime("%a, %d %b %Y %H:%M:%S +0000")


XML_REDDIT = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>r/videoediting</title>
<entry><title>Best free tool to cut vertical videos?</title><link href="https://www.reddit.com/r/videoediting/comments/abc123/best_free_tool/"/>
<id>t3_abc123</id><updated>{(_MAINT - timedelta(hours=2)).isoformat()}</updated>
<content type="html">&lt;div class="md"&gt;&lt;p&gt;I need something local for 9:16 shorts.&lt;/p&gt;&lt;/div&gt; submitted by &lt;a href="https://www.reddit.com/user/bob_le_monteur"&gt; /u/bob_le_monteur &lt;/a&gt; &lt;br/&gt; &lt;span&gt;&lt;a href="https://www.reddit.com/r/videoediting/comments/abc123/"&gt;[link]&lt;/a&gt;&lt;/span&gt; &lt;span&gt;&lt;a href="https://www.reddit.com/r/videoediting/comments/abc123/"&gt;[comments]&lt;/a&gt;&lt;/span&gt;</content>
<author><name>/u/bob_le_monteur</name></author></entry>
</feed>"""

XML_YT = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Chaîne</title>
<item><title>Nouveau tuto montage</title><link>https://www.youtube.com/watch?v=vid00000001</link>
<description>Vingt minutes de montage vertical.</description><pubDate>{_rfc(3)}</pubDate></item>
</channel></rss>"""

LUS = []
def faux_rss(src):
    LUS.append(src["url"])
    xml = XML_REDDIT if "reddit.com" in src["url"] else XML_YT
    return news_service._fetch_rss(dict(src, url=xml))
NF._RSS = faux_rss

DEVIS = {"usd": 0.12}
RUNS = []
ECHEC = {"lever": None}
ITEMS_X = [{"text": "On sort la v2 de l'outil : montage 9:16 en local, sans abonnement.\nDétails dans le fil.",
            "url": "https://x.com/deepotus/status/1850000000000000001", "createdAt": (_MAINT - timedelta(hours=1)).isoformat(),
            "author": {"userName": "deepotus"}, "likeCount": 12}]


async def faux_devis(cle, n, entree=None):
    return DEVIS["usd"]


async def faux_lancer(cle, entree, n, plafond=None):
    RUNS.append({"cle": cle, "entree": entree, "n": n, "plafond": plafond})
    if ECHEC["lever"]:
        raise ECHEC["lever"]
    return {"items": ITEMS_X, "cout_usd": 0.05, "statut": "SUCCEEDED", "partiel": False, "run_id": "R1",
            "devis_usd": DEVIS["usd"]}


CLE = {"posee": True}
AP.devis = faux_devis
AP.lancer = faux_lancer
AP.configure = lambda: CLE["posee"]

c = TestClient(app)
H = {"host": "127.0.0.1"}


async def _depenses():
    async with async_session_factory() as s:
        return [(d.categorie, d.estime_usd, d.reel_usd, d.ref) for d in (await s.execute(select(Depense))).scalars().all()]


def main():
    asyncio.run(init_db())

    print("[1] identifiants")
    n = NF.normaliser
    check("1a YouTube : chaîne UC… -> flux Atom gratuit",
          n("youtube", "UC_x5XG1OV2P6uZZ5FSM9Ttw")["url_flux"]
          == "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw")
    check("1b YouTube : adresse /channel/UC… lue",
          n("youtube", "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw/videos")["identifiant"]
          == "UC_x5XG1OV2P6uZZ5FSM9Ttw")
    for brut in ("@deepotus", "https://www.youtube.com/@deepotus", "UC123", "chaine UC_x5XG1OV2P6uZZ5FSM9Ttw"):
        try:
            n("youtube", brut); r = None
        except ValueError as e:
            r = str(e)
        check(f"1c YouTube : {brut} refusé (un @pseudo n'a pas de flux)", bool(r) and "UC" in r, r)
    check("1d Reddit : communauté (r/…, adresse, nom nu) -> flux .rss",
          n("reddit", "r/videoediting")["url_flux"] == "https://www.reddit.com/r/videoediting/.rss"
          and n("reddit", "https://www.reddit.com/r/VideoEditing/top/")["identifiant"] == "r/VideoEditing"
          and n("reddit", "videoediting")["identifiant"] == "r/videoediting")
    check("1e Reddit : un compte u/…", n("reddit", "u/spez")["url_flux"] == "https://www.reddit.com/user/spez/.rss")
    check("1f X : @pseudo et adresse -> pseudo, lecture Apify",
          n("x", "@Deepotus")["identifiant"] == "Deepotus" and n("x", "https://x.com/deepotus?s=20")["identifiant"]
          == "deepotus" and n("x", "twitter.com/deepotus")["lecture"] == "apify" and n("x", "@a")["url_flux"] is None)
    check("1g Instagram et TikTok",
          n("instagram", "https://www.instagram.com/deepotus.studio/")["identifiant"] == "deepotus.studio"
          and n("tiktok", "https://www.tiktok.com/@deepotus")["identifiant"] == "deepotus"
          and n("tiktok", "@deepotus")["lecture"] == "apify")
    for p, brut in (("linkedin", "deepotus"), ("x", "pas un pseudo !"), ("x", "a" * 16), ("reddit", "r/a"),
                    ("instagram", "")):
        try:
            n(p, brut); r = None
        except ValueError as e:
            r = str(e)
        check(f"1h refus : {p} {brut[:12]!r}", bool(r), r)
    check("1i les cinq plateformes, LinkedIn exclu", set(NF.PLATEFORMES) == {"x", "instagram", "tiktok", "youtube", "reddit"})

    print("\n[2] ajout a la main")
    r = c.post("/api/news/fils", json={"plateforme": "reddit", "identifiant": "r/videoediting"}, headers=H)
    check("2a POST : 200, fil cree", r.status_code == 200, r.text[:300])
    f_rd = r.json()["fil"]
    check("2b origine main, frequence par defaut, actif, jamais lu",
          f_rd["origine"]["type"] == "main" and f_rd["frequence_h"] == NF.FREQUENCE_DEFAUT_H and f_rd["pause"] is False
          and f_rd["derniere_lecture"] is None and f_rd["lecture"] == "rss" and f_rd["id"].startswith("fil_"), f_rd)
    r = c.post("/api/news/fils", json={"plateforme": "reddit", "identifiant": "https://www.reddit.com/r/videoediting/"}, headers=H)
    check("2c meme fil deux fois : 409", r.status_code == 409, r.text[:200])
    r = c.post("/api/news/fils", json={"plateforme": "youtube", "identifiant": "@deepotus"}, headers=H)
    check("2d identifiant illisible : 400 qui dit quoi coller", r.status_code == 400 and "UC" in r.text, r.text[:200])
    r = c.post("/api/news/fils", json={"plateforme": "reddit", "identifiant": "r/shorts", "frequence_h": 5}, headers=H)
    check("2e frequence hors liste : 400", r.status_code == 400, r.text[:200])
    r = c.post("/api/news/fils", json={"plateforme": "youtube", "identifiant": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                                       "nom": "Google Dev", "frequence_h": 6}, headers=H)
    f_yt = r.json()["fil"]
    check("2f nom et frequence choisis", r.status_code == 200 and f_yt["nom"] == "Google Dev" and f_yt["frequence_h"] == 6, r.text[:200])
    r = c.post("/api/news/fils", json={"plateforme": "x", "identifiant": "@deepotus", "frequence_h": 24}, headers=H)
    f_x = r.json()["fil"]
    check("2g fil X : lecture apify, sans accord", f_x["lecture"] == "apify" and f_x["accord"] is None
          and f_x["etat"] == "devis_a_accepter", f_x)
    r = c.patch(f"/api/news/fils/{f_yt['id']}", json={"pause": True, "frequence_h": 12}, headers=H)
    check("2h PATCH : pause et frequence", r.status_code == 200 and r.json()["fil"]["pause"] is True
          and r.json()["fil"]["frequence_h"] == 12, r.text[:200])
    g = c.get("/api/news/fils", headers=H).json()
    check("2i GET : fils, suggestions, plateformes, frequences",
          {x["id"] for x in g["fils"]} == {f_rd["id"], f_yt["id"], f_x["id"]} and g["suggestions"] == []
          and g["plateformes"]["x"]["lecture"] == "apify" and g["plateformes"]["reddit"]["lecture"] == "rss"
          and NF.FREQUENCE_DEFAUT_H in g["frequences_h"] and "configure" in g["apify"], json.dumps(g)[:300])
    check("2j les fils ne touchent pas sources.json (une autre sorte de source)",
          all(not s["id"].startswith("fil_") for s in news_service.list_sources()))
    NET = TestClient(app, client=("192.168.1.20", 50000))
    check("2k un poste non appairé : 401 (middleware d'appairage)", NET.get("/api/news/fils").status_code == 401)
    news_service._save_sources([])          # le lifespan de l'appairage ne doit rien aller lire sur le réseau
    import _jeton_appareil as _JA
    TEL = TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app))
    check("2l même un téléphone appairé : 403 (lecture comme relevé)", TEL.get("/api/news/fils").status_code == 403
          and TEL.post(f"/api/news/fils/{f_x['id']}/lire").status_code == 403
          and TEL.post("/api/news/fils", json={"plateforme": "reddit", "identifiant": "r/shorts"}).status_code == 403)

    print("\n[3] lecture gratuite (RSS / Atom)")
    r = c.post(f"/api/news/fils/{f_rd['id']}/lire", headers=H)
    check("3a lire : 200, un element, cout 0", r.status_code == 200 and r.json()["lus"] == 1
          and r.json()["cout_usd"] == 0, r.text[:300])
    check("3b le flux lu est celui de Reddit", LUS[-1] == "https://www.reddit.com/r/videoediting/.rss", LUS)
    items = [i for i in news_service.get_items().get("items", []) if i["source_id"] == f_rd["id"]]
    it = items[0] if items else {}
    check("3c l'element est dans le cache de News, normalise",
          it.get("title") == "Best free tool to cut vertical videos?" and it.get("plateforme") == "reddit"
          and it.get("link", "").startswith("https://www.reddit.com/r/videoediting/comments/abc123")
          and it.get("published", "").startswith(str(_MAINT.year)), it)
    tout = json.dumps(news_service.get_items(), ensure_ascii=False) + (NF._ITEMS_PATH().read_text("utf-8") if NF._ITEMS_PATH().exists() else "")
    check("3d aucun auteur tiers garde (ni pseudo, ni [link] [comments])",
          "bob_le_monteur" not in tout and "[comments]" not in it.get("summary", "") and "local for 9:16" in it.get("summary", ""),
          it.get("summary"))
    fr = NF.lire_fil(f_rd["id"])
    check("3e derniere lecture posee, etat ok", fr["derniere_lecture"] and fr["etat"] == "ok" and fr["dernier_nombre"] == 1, fr)
    check("3f aucune depense pour un flux gratuit", asyncio.run(_depenses()) == [])

    print("\n[4] lecture payante (Apify) : devis, accord, plafonds")
    r = c.get(f"/api/news/fils/{f_x['id']}/devis", headers=H)
    dv = r.json()
    check("4a devis gratuit : montant, max, plafond par releve et plafond de l'usage",
          r.status_code == 200 and dv["devis_usd"] == 0.12 and dv["max"] == NF.MAX_DEFAUT
          and dv["plafond_max_usd"] == AP.PLAFONDS["veille"] and dv["gratuit"] is False, r.text[:300])
    check("4b devis d'un flux gratuit", c.get(f"/api/news/fils/{f_rd['id']}/devis", headers=H).json().get("gratuit") is True)
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    check("4c lire sans accord : 409 devis_a_accepter, aucun run", r.status_code == 409
          and "devis_a_accepter" in r.text and RUNS == [], r.text[:300])
    r = c.post(f"/api/news/fils/{f_x['id']}/accord", json={"plafond_usd": 0.5}, headers=H)
    check("4d accord sans confirme_cout : 409 avec le devis", r.status_code == 409 and r.json()["detail"]["code"] == "confirme_cout"
          and r.json()["detail"]["devis_usd"] == 0.12, r.text[:300])
    r = c.post(f"/api/news/fils/{f_x['id']}/accord", json={"plafond_usd": 0.05, "confirme_cout": True}, headers=H)
    check("4e plafond par releve sous le devis : 400", r.status_code == 400, r.text[:200])
    r = c.post(f"/api/news/fils/{f_x['id']}/accord", json={"plafond_usd": 5, "confirme_cout": True}, headers=H)
    check("4f plafond au-dela de celui de l'usage (2 $) : 400", r.status_code == 400, r.text[:200])
    CLE["posee"] = False
    r = c.post(f"/api/news/fils/{f_x['id']}/accord", json={"plafond_usd": 0.5, "confirme_cout": True}, headers=H)
    check("4g sans cle Apify : 503", r.status_code == 503, r.text[:200])
    CLE["posee"] = True
    r = c.post(f"/api/news/fils/{f_x['id']}/accord", json={"plafond_usd": 0.5, "confirme_cout": True}, headers=H)
    fx = r.json().get("fil", {})
    check("4h accord pose : plafond, devis du jour, etat a lire", r.status_code == 200 and fx["accord"]["plafond_usd"] == 0.5
          and fx["accord"]["devis_usd"] == 0.12 and fx["etat"] == "jamais_lu", r.text[:300])
    check("4i aucun run ni depense a l'accord", RUNS == [] and asyncio.run(_depenses()) == [])
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    check("4j lire : 200, un run borne par le plafond du fil", r.status_code == 200 and len(RUNS) == 1
          and RUNS[0]["cle"] == "x" and RUNS[0]["plafond"] == 0.5 and RUNS[0]["n"] == NF.MAX_DEFAUT, (r.text[:300], RUNS))
    check("4k entree du run : les publications du compte, les plus recentes",
          RUNS[0]["entree"] == {"searchTerms": ["from:deepotus"], "sort": "Latest"}, RUNS[0]["entree"])
    dep = asyncio.run(_depenses())
    check("4l une ligne « news » au registre : devis puis reel", len(dep) == 1 and dep[0][0] == "news"
          and abs(dep[0][1] - 0.12) < 1e-9 and abs((dep[0][2] or 0) - 0.05) < 1e-9 and dep[0][3] == f_x["id"], dep)
    ix = [i for i in news_service.get_items()["items"] if i["source_id"] == f_x["id"]]
    check("4m element X : lien sans pseudo, titre = premiere ligne, plateforme",
          ix and ix[0]["link"] == "https://x.com/i/status/1850000000000000001" and ix[0]["plateforme"] == "x"
          and ix[0]["title"].startswith("On sort la v2") and "Détails" not in ix[0]["title"], ix)
    fx = NF.lire_fil(f_x["id"])
    check("4n cout du dernier releve et cumul gardes", fx["dernier_cout_usd"] == 0.05 and fx["cout_cumule_usd"] == 0.05, fx)
    CLE["posee"] = False
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    check("4n2 lire sans cle (accord pose) : 503, aucun run", r.status_code == 503 and len(RUNS) == 1
          and NF.lire_fil(f_x["id"])["etat"] == "sans_cle", r.text[:200])
    CLE["posee"] = True
    DEVIS["usd"] = 0.8
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    check("4o devis au-dela du plafond du fil : 409 devis_depasse, aucun run", r.status_code == 409
          and "devis_depasse" in r.text and len(RUNS) == 1 and NF.lire_fil(f_x["id"])["etat"] == "devis_depasse", r.text[:300])
    DEVIS["usd"] = 0.12
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    check("4p plafond mensuel : 402 dz_plafond, aucun run", r.status_code == 402 and "dz_plafond" in r.text and len(RUNS) == 1,
          r.text[:300])
    P.enregistrer({"global_usd": 0, "par_moteur": {}})
    ECHEC["lever"] = AP.ApifyEchec("le run Apify a échoué (apidojo~tweet-scraper)", 0.03)
    r = c.post(f"/api/news/fils/{f_x['id']}/lire", headers=H)
    dep = asyncio.run(_depenses())
    check("4q run en echec : 502, cout reel note quand meme, etat erreur", r.status_code == 502 and len(RUNS) == 2
          and abs((dep[-1][2] or 0) - 0.03) < 1e-9 and NF.lire_fil(f_x["id"])["etat"] == "erreur"
          and NF.lire_fil(f_x["id"])["cout_cumule_usd"] == 0.08, (r.text[:200], dep))
    ECHEC["lever"] = None
    r = c.delete(f"/api/news/fils/{f_x['id']}/accord", headers=H)
    check("4r retirer l'accord", r.status_code == 200 and r.json()["fil"]["accord"] is None
          and r.json()["fil"]["etat"] == "devis_a_accepter", r.text[:200])

    print("\n[5] la boucle : a son heure seulement")
    r = c.post("/api/news/fils", json={"plateforme": "tiktok", "identifiant": "@deepotus", "frequence_h": 1}, headers=H)
    f_tt = r.json()["fil"]
    n_runs, n_lus = len(RUNS), len(LUS)
    rep = asyncio.run(NF.tic())
    check("5a Reddit lu il y a peu (24 h) : pas relu ; YouTube en pause : pas lu", f_rd["id"] not in rep["lus"]
          and f_yt["id"] not in rep["lus"] and len(LUS) == n_lus, rep)
    check("5b fils Apify sans accord : jamais lus, aucun devis demande", len(RUNS) == n_runs
          and f_tt["id"] in rep["sans_accord"] and f_x["id"] in rep["sans_accord"], rep)
    c.patch(f"/api/news/fils/{f_yt['id']}", json={"pause": False}, headers=H)
    c.post(f"/api/news/fils/{f_tt['id']}/accord", json={"plafond_usd": 0.4, "confirme_cout": True}, headers=H)
    rep = asyncio.run(NF.tic())
    check("5c YouTube repris : lu ; TikTok avec accord et du : un run", f_yt["id"] in rep["lus"] and f_tt["id"] in rep["lus"]
          and len(RUNS) == n_runs + 1 and RUNS[-1]["entree"] == {"profiles": ["deepotus"]} and RUNS[-1]["plafond"] == 0.4, (rep, RUNS[-1:]))
    rep = asyncio.run(NF.tic())
    check("5d tout juste lu : rien a lire", rep["lus"] == [] and len(RUNS) == n_runs + 1, rep)
    NF._modifier(f_rd["id"], derniere_tentative=(datetime.now(timezone.utc) - timedelta(hours=25)).isoformat())
    rep = asyncio.run(NF.tic())
    check("5e frequence ecoulee : relu", rep["lus"] == [f_rd["id"]], rep)
    CLE["posee"] = False
    NF._modifier(f_tt["id"], derniere_tentative=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    rep = asyncio.run(NF.tic())
    check("5f cle retiree : le fil Apify le dit, aucun run", len(RUNS) == n_runs + 1 and NF.lire_fil(f_tt["id"])["etat"] == "sans_cle", rep)
    CLE["posee"] = True

    print("\n[6] suggestions des agents")
    check("6a outil dans la boite « fils », agent Campagnes seul", B.boite_de("proposer_fil") == "fils"
          and "proposer_fil" in B.outils_pour("campagnes") and "proposer_fil" not in B.outils_pour("mcp")
          and B.verifier() == [], B.verifier())
    A = E.creer({"nom": "Fils"})["id"]
    ctx = ao.Ctx(cid="conv-fils-1", espace_id=A)
    nfils = len(NF.lister()["fils"])
    r = asyncio.run(ao.executer("proposer_fil", {"plateforme": "instagram", "identifiant": "@runwayapp",
                                                 "raison": "le concurrent y annonce ses sorties", "pour": "veille"}, ctx))
    check("6b proposer_fil : ok, rien d'abonne", r["ok"] is True and len(NF.lister()["fils"]) == nfils, r)
    sg = NF.lister()["suggestions"]
    s0 = sg[0] if sg else {}
    check("6c suggestion avec son origine (agent, cadre, conversation, espace)",
          s0.get("plateforme") == "instagram" and s0.get("identifiant") == "runwayapp" and s0.get("etat") == "proposee"
          and s0.get("origine") == {"type": "agent", "agent": "campagnes", "cadre": "veille", "conversation": "conv-fils-1",
                                    "espace_id": A} and s0.get("raison") == "le concurrent y annonce ses sorties", s0)
    r2 = asyncio.run(ao.executer("proposer_fil", {"plateforme": "instagram", "identifiant": "runwayapp",
                                                  "raison": "encore", "pour": "campagne"}, ctx))
    check("6d la meme suggestion deux fois : une seule", r2["ok"] is True and len(NF.lister()["suggestions"]) == 1, r2)
    r3 = asyncio.run(ao.executer("proposer_fil", {"plateforme": "reddit", "identifiant": "r/videoediting",
                                                  "raison": "x", "pour": "prospects"}, ctx))
    check("6e un fil deja suivi : dit, aucune suggestion", r3["ok"] is True and "déjà" in r3["resume"]
          and len(NF.lister()["suggestions"]) == 1, r3)
    r4 = asyncio.run(ao.executer("proposer_fil", {"plateforme": "linkedin", "identifiant": "x", "raison": "x", "pour": "veille"}, ctx))
    check("6f plateforme hors liste : refus (schema ou service)", r4["ok"] is False, r4)
    r5 = asyncio.run(ao.executer("proposer_fil", {"plateforme": "youtube", "identifiant": "@chaine", "raison": "x",
                                                  "pour": "campagne"}, ctx))
    check("6g identifiant illisible : refus dit au modele", r5["ok"] is False and "UC" in r5["resume"], r5)
    r = c.post(f"/api/news/fils/suggestions/{s0['id']}/accepter", json={"frequence_h": 72}, headers=H)
    nf = r.json().get("fil", {})
    check("6h accepter : le fil nait avec l'origine de la suggestion", r.status_code == 200 and nf.get("plateforme") == "instagram"
          and nf.get("origine", {}).get("cadre") == "veille" and nf.get("frequence_h") == 72
          and nf.get("etat") == "devis_a_accepter", r.text[:300])
    check("6i suggestion acceptee (gardee pour l'historique)", NF.lister()["suggestions"][0]["etat"] == "acceptee")
    asyncio.run(ao.executer("proposer_fil", {"plateforme": "tiktok", "identifiant": "@pika", "raison": "x", "pour": "campagne"}, ctx))
    sid = [s for s in NF.lister()["suggestions"] if s["identifiant"] == "pika"][0]["id"]
    r = c.post(f"/api/news/fils/suggestions/{sid}/ecarter", headers=H)
    check("6j ecarter", r.status_code == 200 and r.json()["suggestion"]["etat"] == "ecartee", r.text[:200])
    r6 = asyncio.run(ao.executer("proposer_fil", {"plateforme": "tiktok", "identifiant": "pika", "raison": "x", "pour": "campagne"}, ctx))
    check("6k une suggestion ecartee n'est pas reproposee", r6["ok"] is False and "écart" in r6["resume"], r6)
    check("6l suggestion inconnue : 404", c.post("/api/news/fils/suggestions/sug_zzz/accepter", json={}, headers=H).status_code == 404)

    print("\n[7] le classement")
    c.put("/api/news/filter", json={"fraicheur_h": 24 * 30}, headers=H)
    r = c.post("/api/news/rank", json={"brief": ""}, headers=H)
    par = {i["source_id"]: i for i in r.json().get("items", [])}
    check("7a les elements des fils entrent dans le classement, avec leur plateforme",
          r.status_code == 200 and par.get(f_rd["id"], {}).get("plateforme") == "reddit"
          and par.get(f_x["id"], {}).get("plateforme") == "x", r.text[:400])
    news_service._save_sources([])
    news_service._refresh_blocking()
    ids = {i["source_id"] for i in news_service.get_items()["items"]}
    check("7b un rafraichissement des sources garde les fils actifs", {f_rd["id"], f_x["id"], f_yt["id"]} <= ids, ids)
    c.patch(f"/api/news/fils/{f_rd['id']}", json={"pause": True}, headers=H)
    c.delete(f"/api/news/fils/{f_yt['id']}", headers=H)
    ids = {i["source_id"] for i in news_service.get_items()["items"]}
    check("7c0 retirer un fil sort ses elements du cache tout de suite", f_yt["id"] not in ids and f_rd["id"] in ids, ids)
    news_service._refresh_blocking()
    ids = {i["source_id"] for i in news_service.get_items()["items"]}
    check("7c fil en pause ou retire : ses elements sortent au rafraichissement", f_rd["id"] not in ids and f_yt["id"] not in ids, ids)
    check("7d retirer : 200 puis 404", c.delete(f"/api/news/fils/{f_yt['id']}", headers=H).status_code == 404)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
