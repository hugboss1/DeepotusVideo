# -*- coding: utf-8 -*-
"""t500 (G10, 26/11/2026) — banc de « X, la même boucle » (faux HTTP : le fetcher X et le publieur sont remplacés,
tout appel réseau réel lève).

1. tarifs : la table datée de l'API X (pricing.x_api_usd, relue sur docs.x.com le 26/11/2026), le devis `x_api`
   (lecture par post, post, post AVEC LIEN plus cher, média) ;
2. jalons : seuls les posts X dont le jalon courant (J1, J3, J7, J30) n'est pas encore relevé sont à relever ;
3. relevé : devis gratuit ; relevé PAYANT seulement sous accord (max_usd), garde `plafonds.verifier` catégorie « x »
   AVANT le fetcher, refus du plafond X propre (moteur « x ») sans rien lire ; multiplicateur X ensuite dans le tableau ;
4. jamais automatique sans accord enregistré : la passe quotidienne saute X ; l'accord auto exige un plafond X ;
5. publication : devis par message (lien plus cher), le publieur X passe la garde « x » et s'arrête au plafond ;
6. contrôles du fil : 280 caractères par message (lien compté 23), accroche dans le premier, appel dans le dernier,
   un lien au plus et à la fin ;
7. recyclage : l'élément « x_video » (reel → post vidéo X), le fil X rédigé est contrôlé et part en VRAI fil
   (thread_of / thread_index), la carte dit le coût de mise en ligne X ;
8. gagnants : la niche filtrée aux fils X (relevés par Apify, aucune API X) ;
9. routes : /api/croissance/x/* ; la route payante est recensée (PAYANTES, _recensement_payant) et gardée.
Run (depuis backend/) : & $PY tests/test_croissance_x.py"""
import asyncio, json, os, pathlib, socket, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzg10_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "FAL_KEY", "APIFY_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


RESEAU = []
_connect0 = socket.socket.connect
def _pas_de_reseau(self, adresse):
    hote = adresse[0] if isinstance(adresse, tuple) and adresse else adresse
    if hote in ("127.0.0.1", "::1", "localhost"):          # la paire de sockets de la boucle asyncio (Windows)
        return _connect0(self, adresse)
    RESEAU.append(adresse)
    raise OSError("réseau interdit dans le banc")
socket.socket.connect = _pas_de_reseau

from app.config import settings                                    # noqa: E402
from app.services import pricing, plafonds, croissance_x as CX, metrics_service as MS, marketing, quota   # noqa: E402
from app.services import script_court as SC, recyclage as RC, croissance_gagnants as CG, espaces   # noqa: E402
from app.services.storage import init_db, async_session_factory, ScheduledPost, PostMetric, Depense   # noqa: E402
from sqlalchemy import select                                       # noqa: E402

settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = "banc"
LUS = []


async def faux_x(ids):
    """Le faux HTTP de l'API X : public_metrics normalisés pour chaque id demandé."""
    LUS.append(list(ids))
    return {i: {"views": 1000 if i == "tw_j1" else 100, "likes": 3, "comments": 1, "shares": 2, "saves": 0,
                "brut": {"impression_count": 100}} for i in ids}
MS.FETCHERS["x"] = faux_x
PUBLIES = []
def faux_publier(caption, video_path, image_path, reply_to=None):
    PUBLIES.append((caption, reply_to))
    return True, "tweet 42", "42"
marketing._publish_x_sync = faux_publier

NOW = datetime.utcnow().replace(microsecond=0)


def _m(pid, at, views, ch="x"):
    return PostMetric(id=f"{pid}-{at.isoformat()}", post_id=pid, channel=ch, remote_id="r" + pid, fetched_at=at,
                      views=views, likes=0, comments=0, shares=0, saves=0)


async def seed(eid):
    async with async_session_factory() as s:
        # six anciens posts X (habituel : 100 vues à J1)
        for i in range(6):
            d = NOW - timedelta(days=40 + i)
            s.add(ScheduledPost(id=f"xa{i}", title=f"Ancien {i}", channels="x", run_at=d, status="posted", posted_at=d,
                                format="post", espace_id=eid, remote_ids=json.dumps({"x": f"tw_a{i}"})))
            s.add(_m(f"xa{i}", d + timedelta(days=1, hours=2), 100))
            s.add(_m(f"xa{i}", d + timedelta(days=30, hours=2), 150))      # J30 relevé : plus rien à lire
        d = NOW - timedelta(days=1, hours=5)                                   # J1 dû
        s.add(ScheduledPost(id="x_j1", title="Le fil qui part", channels="x", run_at=d, status="posted", posted_at=d,
                            format="post", espace_id=eid, remote_ids=json.dumps({"x": "tw_j1"})))
        d = NOW - timedelta(days=3, hours=12)                                  # J3 dû (J1 déjà là)
        s.add(ScheduledPost(id="x_j3", title="Moyen", channels="x", run_at=d, status="posted", posted_at=d,
                            format="post", espace_id=eid, x_post_id="tw_j3"))
        s.add(_m("x_j3", d + timedelta(days=1, hours=1), 120))
        d = NOW - timedelta(days=2)                                            # J1 déjà relevé : rien
        s.add(ScheduledPost(id="x_ok", title="À jour", channels="x", run_at=d, status="posted", posted_at=d,
                            format="post", espace_id=eid, remote_ids=json.dumps({"x": "tw_ok"})))
        s.add(_m("x_ok", d + timedelta(days=1, hours=1), 90))
        d = NOW - timedelta(hours=10)                                          # trop tôt
        s.add(ScheduledPost(id="x_tot", title="Tôt", channels="x", run_at=d, status="posted", posted_at=d,
                            format="post", espace_id=eid, remote_ids=json.dumps({"x": "tw_tot"})))
        d = NOW - timedelta(days=1, hours=5)                                   # Instagram : pas l'API X
        s.add(ScheduledPost(id="ig1", title="Reel", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="reel", espace_id=eid, remote_ids=json.dumps({"instagram": "ig_1"})))
        await s.commit()


async def lignes_x():
    async with async_session_factory() as s:
        return list((await s.execute(select(Depense).where(Depense.moteur == "x"))).scalars().all())


async def main():
    await init_db()
    E = espaces.creer({"nom": "Fil G10"})["id"]
    await seed(E)

    print("[1] tarifs de l'API X")
    t = CX.tarifs()
    check("1a table datée et sourcée", CX.RELU["le"] == "2026-11-26" and CX.RELU["source"].startswith("https://docs.x.com/"), CX.RELU)
    check("1b lecture 0,005 $ par post, post 0,015 $, post avec lien 0,20 $, média 0,005 $",
          t == {"lecture": 0.005, "post": 0.015, "post_lien": 0.2, "media": 0.005}, t)
    e = pricing.estimate({"kind": "x_api", "lectures": 4})
    check("1c devis de quatre lectures : 0,02 $, moteur « x »", e["total_usd"] == 0.02 and e["breakdown"][0]["provider"] == "x", e)
    e = pricing.estimate({"kind": "x_api", "posts": 2, "liens": 1, "medias": 1})
    check("1d deux posts, un avec lien, un média : 0,235 $", abs(e["total_usd"] - 0.235) < 1e-9 and len(e["breakdown"]) == 3, e)
    check("1e la catégorie « x » est au vocabulaire des plafonds", "x" in plafonds.CATEGORIES)
    p = pricing.load()
    check("1f les tarifs se corrigent dans pricing.json (fusion)", p["x_api_usd"]["post_lien"] == 0.2)

    print("[2] jalons à relever")
    dus = await CX.a_relever(NOW)
    check("2a J1 et J3 dus ; à jour, trop tôt, anciens et Instagram non", sorted((d["post_id"], d["jalon"]) for d in dus)
          == [("x_j1", 1), ("x_j3", 3)], dus)
    check("2b l'id X d'avant le socle (x_post_id seul) est repris", any(d["remote_id"] == "tw_j3" for d in dus), dus)

    print("[3] relevé sous accord")
    dv = await CX.devis_releve()
    check("3a devis gratuit : deux posts, 0,01 $, aucune lecture", dv["n"] == 2 and dv["usd"] == 0.01 and not LUS, dv)
    try:
        await CX.relever(None)
        sans = False
    except ValueError:
        sans = True
    check("3b sans accord (max_usd) : refus, rien lu", sans and not LUS)
    try:
        await CX.relever(0.004)
        bas = False
    except CX.CoutChange as x:
        bas = x.usd == 0.01
    check("3c accord sous le devis : coût changé, rien lu", bas and not LUS)
    plafonds.enregistrer({"par_moteur": {"x": 0.005}})
    try:
        await CX.relever(0.01)
        plaf = False
    except Exception as x:   # noqa: BLE001
        plaf = getattr(x, "status_code", 0) == 402
    check("3d plafond X propre (moteur « x ») atteint : 402, rien lu", plaf and not LUS and not await lignes_x())
    plafonds.enregistrer({"par_moteur": {"x": 5.0}})
    r = await CX.relever(0.01)
    lx = await lignes_x()
    check("3e relevé : deux posts lus d'un coup", r["releves"] == 2 and len(LUS) == 1
          and sorted(LUS[0]) == ["tw_j1", "tw_j3"], (r, LUS))
    check("3f une ligne au registre : moteur x, catégorie x, 0,01 $", len(lx) == 1 and lx[0].categorie == "x"
          and abs(lx[0].estime_usd - 0.01) < 1e-9, [(l.moteur, l.categorie, l.estime_usd) for l in lx])
    check("3g plus rien à relever ensuite", (await CX.devis_releve())["n"] == 0)
    tab = await MS.tableau(30, E)
    x1 = next((d for d in tab["gagnants"] if d["id"] == "x_j1"), None)
    check("3h multiplicateur X dans le tableau : 10× l'habituel, gagnant, jalon J1", x1 is not None
          and x1["croissance"]["multiplicateur"] == 10.0 and x1["croissance"]["jalon"] == 1, tab["gagnants"])
    r2 = await CX.relever(0.01)
    check("3i rien de dû : aucun appel, aucune dépense", r2["releves"] == 0 and len(LUS) == 1 and len(await lignes_x()) == 1, r2)

    print("[4] jamais automatique sans accord enregistré")
    LUS.clear()
    c = await MS.refresh_all(max_per_channel=10)
    check("4a sans accord : la passe quotidienne ne lit rien sur X", "x" not in c and not LUS, (c, LUS))
    try:
        CX.regler_accord(True, 0)
        sansplaf = False
    except ValueError:
        sansplaf = True
    check("4b l'accord automatique exige un plafond X", sansplaf and CX.lire_accord()["auto"] is False)
    a = CX.regler_accord(True, 2.5)
    check("4c accord enregistré, daté ; le plafond X devient celui du moteur « x »", a["auto"] is True and a["le"]
          and plafonds.charger()["par_moteur"].get("x") == 2.5, (a, plafonds.charger()))
    c = await MS.refresh_all(max_per_channel=10)
    lx = await lignes_x()
    check("4d avec l'accord : la passe lit X ET passe la garde « x »", c.get("x", 0) >= 1 and LUS and len(lx) == 2
          and lx[-1].categorie == "x", (c, LUS, [(l.categorie, l.estime_usd) for l in lx]))
    plafonds.enregistrer({"par_moteur": {"x": 0.0001}})
    LUS.clear()
    c = await MS.refresh_all(max_per_channel=10)
    check("4e plafond X atteint : la passe saute X sans lire", "x" not in c and not LUS, (c, LUS))
    CX.regler_accord(False, 5.0)
    check("4f accord retiré", CX.lire_accord()["auto"] is False)

    print("[5] publication X")
    d = CX.devis_publication(["Premier message sans lien", "Le lien : https://deepotus.tech/videogen"], medias=1)
    check("5a devis par message : le lien coûte 0,20 $, l'autre 0,015 $, un média 0,005 $",
          [m["usd"] for m in d["messages"]] == [0.015, 0.2] and abs(d["usd"] - 0.22) < 1e-9 and d["messages"][1]["lien"] is True, d)
    plafonds.enregistrer({"par_moteur": {"x": 5.0}})
    res = await marketing._pub_x("Un post avec https://deepotus.tech", None, None, {"post_id": "p", "brief": {}})
    lx = await lignes_x()
    check("5b le publieur passe la garde « x » au tarif avec lien, puis publie", res.ok and PUBLIES and lx[-1].categorie == "x"
          and abs(lx[-1].estime_usd - 0.2) < 1e-9, (res, [(l.categorie, l.estime_usd) for l in lx]))
    plafonds.enregistrer({"par_moteur": {"x": 0.0001}})
    PUBLIES.clear()
    res = await marketing._pub_x("Encore un post", None, None, {"post_id": "p", "brief": {}})
    check("5c plafond X atteint : rien ne part, c'est dit", not res.ok and not PUBLIES and "plafond" in res.detail.lower(), res)
    plafonds.enregistrer({"par_moteur": {"x": 5.0}})
    async with async_session_factory() as s:
        s.add(ScheduledPost(id="fil0", title="Fil", caption="Tu paies encore chaque mois pour monter tes vidéos ?",
                            channels="x", run_at=NOW, status="draft", format="post", espace_id=E))
        s.add(ScheduledPost(id="fil1", title="Fil (2)", caption="Lien : https://deepotus.tech", channels="x", run_at=NOW,
                            status="draft", format="post", espace_id=E, thread_of="fil0", thread_index=1))
        await s.commit()
    dp = await CX.devis_publication_post("fil0")
    check("5d devis d'un post et de sa suite de fil : 0,015 + 0,20", len(dp["messages"]) == 2 and abs(dp["usd"] - 0.215) < 1e-9, dp)

    print("[6] contrôles du fil")
    bon = ["Tu paies encore chaque mois pour monter tes vidéos ?", "VideoGen se paie une fois.",
           "Les mises à jour sont comprises.", "Le lien est en bio, essaie-le : https://deepotus.tech/" + "x" * 300]
    r = SC.controler_fil(bon, langue="fr")
    check("6a fil conforme (le lien compte 23 caractères)", r["ok"], r)
    r = SC.controler_fil(["🧵 Un fil", "x" * 281, "https://a.b/c au milieu", "Merci d'avoir lu."], langue="fr")
    c = r["controles"]
    check("6b trop long, accroche absente du premier, lien au milieu, pas d'appel : tous KO", not r["ok"]
          and not c["fil_longueur"]["ok"] and c["fil_longueur"]["detail"] == [{"message": 2, "caracteres": 281}]
          and not c["fil_accroche"]["ok"] and not c["fil_lien"]["ok"] and not c["fil_appel"]["ok"], c)
    check("6c le verdict se met en controle.md", "280 caractères par message" in SC.controle_md(r, "fr")
          and "280 characters per post" in SC.controle_md(r, "en"))
    check("6d fil vide : KO", SC.controler_fil([], langue="fr")["ok"] is False)

    print("[7] recyclage vers X")
    check("7a l'élément « x_video » (reel → post vidéo X)", "x_video" in RC.ELEMENTS and RC.ELEMENTS[:4] == ("carrousel", "accroches", "fil_x", "branche"))
    sortie = RC._lire_sortie("x_video", {"texte": "x" * 400})
    check("7b post vidéo : un texte de 280 caractères au plus", len(sortie["texte"]) == 280, sortie)
    fil = RC._lire_sortie("fil_x", {"fil": ["Tu paies encore chaque mois ?", "Une fois.", "Lien en bio, essaie-le."]})
    check("7c le fil rédigé porte ses contrôles X", fil.get("controle", {}).get("ok") is True, fil)
    pub = RC.publication_x("fil_x")
    check("7d la carte dit le coût de mise en ligne X (au plus, un lien compris)", pub["usd_post"] == 0.015
          and pub["usd_post_lien"] == 0.2 and abs(pub["usd_max"] - ((RC.FIL_MAX - 1) * 0.015 + 0.2)) < 1e-9, pub)
    # un gagnant reel de l'espace, rédaction « gardée » (aucun appel) : les brouillons X
    async with async_session_factory() as s:
        for i in range(6):
            d = NOW - timedelta(days=60 + i)
            s.add(ScheduledPost(id=f"ra{i}", title=f"R{i}", channels="instagram", run_at=d, status="posted", posted_at=d,
                                format="reel", espace_id=E))
            s.add(_m(f"ra{i}", d + timedelta(days=1, hours=1), 100, "instagram"))
        d = NOW - timedelta(days=9)
        s.add(ScheduledPost(id="rg", title="Le reel gagnant", hook="Tu paies encore ?", channels="instagram", run_at=d,
                            status="posted", posted_at=d, format="reel", job_id="job-rg", espace_id=E))
        s.add(_m("rg", d + timedelta(days=1, hours=2), 900, "instagram"))
        await s.commit()
    rec = RC.lire("rg")
    rec["espace_id"] = E
    rec["redactions"]["fil_x"] = dict(fil, element="fil_x", usd=0.006, le="2026-11-26T10:00:00", interdits=[])
    rec["redactions"]["x_video"] = {"texte": "Tu paies encore chaque mois ? Lien en bio.", "element": "x_video",
                                    "usd": 0.002, "le": "2026-11-26T10:00:00", "interdits": [], "controle": {"ok": True}}
    RC._ecrire(rec)
    b = await RC.creer_brouillons("rg", ["fil_x", "x_video"])
    async with async_session_factory() as s:
        tous = {p.id: p for p in (await s.execute(select(ScheduledPost))).scalars().all()}
    tete = next(tous[x["post"]["id"]] for x in b["brouillons"] if x["element"] == "fil_x")
    suites = sorted((p for p in tous.values() if p.thread_of == tete.id), key=lambda p: p.thread_index)
    check("7e le fil X part en VRAI fil : la tête puis deux suites, en brouillon", tete.caption == fil["fil"][0]
          and [p.caption for p in suites] == fil["fil"][1:] and [p.thread_index for p in suites] == [1, 2]
          and all(p.status == "draft" and p.channels == "x" for p in suites), [(p.thread_index, p.caption, p.status) for p in suites])
    xv = next(tous[x["post"]["id"]] for x in b["brouillons"] if x["element"] == "x_video")
    check("7f le post vidéo X : le rendu du reel, le texte rédigé, sur X, en brouillon", xv.job_id == "job-rg"
          and xv.channels == "x" and xv.caption.startswith("Tu paies") and xv.status == "draft", (xv.job_id, xv.channels, xv.status))

    print("[8] gagnants des fils X suivis (Apify)")
    vus = []
    CG._lignes_niche, _ln = (lambda eid, seuil: vus.append(eid) or [
        {"id": "aaaa0001", "plateforme": "x", "published": NOW.isoformat() + "+00:00", "gagnant": True, "multiplicateur": 5.0},
        {"id": "aaaa0002", "plateforme": "instagram", "published": NOW.isoformat() + "+00:00", "gagnant": True, "multiplicateur": 9.0}]), CG._lignes_niche
    g = CG.lire_gagnants(E, plateforme="x")
    check("8a la niche filtrée aux fils X", [x["id"] for x in g["gagnants"]] == ["aaaa0001"] and g.get("plateforme") == "x", g)
    CG._lignes_niche = _ln

    print("[9] routes et recensement")
    from fastapi.testclient import TestClient                       # noqa: E402
    from app.main import app                                        # noqa: E402
    tc = TestClient(app, client=("127.0.0.1", 50000))
    r = tc.get("/api/croissance/x/devis")
    check("9a GET /x/devis : gratuit, tarifs datés", r.status_code == 200 and r.json()["relu"]["le"] == "2026-11-26"
          and "n" in r.json(), r.text[:300])
    r = tc.post("/api/croissance/x/releve", json={})
    check("9b POST /x/releve sans accord : 400", r.status_code == 400, r.text[:200])
    r = tc.put("/api/croissance/x/accord", json={"auto": True, "plafond_usd": 0})
    check("9c PUT /x/accord auto sans plafond : 400", r.status_code == 400, r.text[:200])
    r = tc.put("/api/croissance/x/accord", json={"auto": False, "plafond_usd": 3})
    check("9d PUT /x/accord : 200, plafond X posé", r.status_code == 200 and plafonds.charger()["par_moteur"].get("x") == 3.0, r.text[:200])
    r = tc.post("/api/croissance/x/controle-fil", json={"messages": bon, "langue": "fr"})
    check("9e POST /x/controle-fil : gratuit", r.status_code == 200 and r.json()["ok"] is True, r.text[:200])
    r = tc.get("/api/croissance/x/devis-publication", params={"post_id": "fil0"})
    check("9f GET /x/devis-publication", r.status_code == 200 and abs(r.json()["usd"] - 0.215) < 1e-9, r.text[:200])
    r = tc.get("/api/croissance/gagnants", params={"espace_id": E, "plateforme": "x"})
    check("9g GET /gagnants?plateforme=x", r.status_code == 200 and r.json().get("plateforme") == "x", r.text[:200])
    import _recensement_payant as RP                                # noqa: E402
    rec = RP.recenser()
    k = ("croissance", "POST", "/x/releve")
    check("9h la route du relevé atteint un puits et est gardée", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))
    pg = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("9i inscrite dans PAYANTES", '("croissance", "POST", "/x/releve")' in pg)
    src = (RACINE / "backend" / "app" / "services" / "croissance_x.py").read_text(encoding="utf-8")
    rl = src[src.find("async def relever("):src.find("# ---- fin du relevé")]
    check("9j dans relever : l'accord, puis plafonds.verifier « x », puis le fetcher", 0 < rl.find("raise CoutChange(")
          < rl.find("plafonds.verifier(") < rl.find("FETCHERS"), "")
    mk = (RACINE / "backend" / "app" / "services" / "marketing.py").read_text(encoding="utf-8")
    px = mk[mk.find("async def _pub_x("):]
    check("9k le publieur X garde AVANT publish_x", 0 < px.find("garder_publication(") < px.find("publish_x("), "")

    print("[10] aucun réseau")
    check("10a aucune connexion réelle", not RESEAU, RESEAU)


def test_croissance_x():
    asyncio.run(main())
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
