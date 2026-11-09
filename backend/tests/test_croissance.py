# -*- coding: utf-8 -*-
"""t491 (lot G1 « boucle de croissance », 09/11/2026) — mesures jalonnées, multiplicateur « × habituel », temps de
visionnage ; et les fiches de compétences des agents (Campagnes, Publicitaire, WhatsApp).

[A] pur            croissance.habituel / multiplicateur_habituel / jalon_courant / jalons_mesures / gagnant
[B] agrégat        metrics_service.analytics : jalons J1/J3/J7/J30, multiplicateur à ÂGE ÉGAL contre les 10 posts
                   précédents du même canal et du même format, « — » sous 5 posts, temps de visionnage lu dans `raw`
[C] Instagram      fetch_insights : le temps de visionnage vient d'un second appel, toléré s'il est refusé
[D] agent          lire_planificateur rend la croissance de chaque post
[E] compétences    fiches injectées selon le rôle, l'espace client et le rôle WhatsApp ; servies au compagnon
Data-dir temporaire, aucun réseau.
Run : & $PY tests/test_croissance.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcroi_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_db = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import croissance as CR                           # noqa: E402

print("\n[A] les fonctions pures")
check("A1 habituel : médiane des 10 DERNIERS (les plus anciens sont ignorés)",
      CR.habituel([1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]) == 550, str(CR.habituel([1] + list(range(100, 1001, 100)))))
check("A2 habituel : médiane impaire", CR.habituel([10, 1000, 30, 20, 40]) == 30)
check("A3 habituel : sous 5 posts, pas d'habituel", CR.habituel([100, 200, 300, 400]) is None)
check("A4 habituel : exactement 5 posts suffisent", CR.habituel([100, 200, 300, 400, 500]) == 300)
check("A5 multiplicateur : vues / habituel, une décimale", CR.multiplicateur_habituel(720, [100, 200, 300, 400, 500]) == 2.4)
check("A6 multiplicateur : None sous 5 posts", CR.multiplicateur_habituel(720, [100, 200]) is None)
check("A7 multiplicateur : None si l'habituel est nul (pas de division)", CR.multiplicateur_habituel(50, [0, 0, 0, 0, 0]) is None)
check("A8 multiplicateur : les valeurs absentes de l'historique sont ignorées",
      CR.multiplicateur_habituel(600, [None, 100, 200, 300, 400, 500, None]) == 2.0)
check("A9 gagnant : au seuil (3×) oui, en dessous non, None non",
      CR.gagnant(3.0) is True and CR.gagnant(2.9) is False and CR.gagnant(None) is False)
check("A10 jalon_courant : le plus grand jalon atteint", [CR.jalon_courant(a) for a in (0.5, 1, 2.9, 3, 6.99, 7, 29, 30, 400)]
      == [None, 1, 1, 3, 3, 7, 7, 30, 30])
T0 = datetime(2026, 11, 1, 8, 0, 0)
SN = [{"fetched_at": T0 + timedelta(hours=h), "views": v} for h, v in
      ((2, 50), (25, 400), (49, 600), (73, 800), (169, 1500), (200, 1600))]
J = CR.jalons_mesures(T0, SN)
check("A11 jalons : le PREMIER instantané pris à l'âge du jalon ou après", J[1]["views"] == 400 and J[3]["views"] == 800
      and J[7]["views"] == 1500, str(J))
check("A12 jalons : pas encore atteint = None", J[30] is None)
check("A13 jalons : l'âge du relevé est rendu en jours", abs(J[1]["age_j"] - 25 / 24) < 0.01, str(J[1]))
check("A14 jalons : un relevé trop tardif ne vaut pas pour le jalon (fenêtre dépassée)",
      CR.jalons_mesures(T0, [{"fetched_at": T0 + timedelta(days=6), "views": 900}])[1] is None)
check("A15 jalons : sans date de publication, tout est None", CR.jalons_mesures(None, SN) == {1: None, 3: None, 7: None, 30: None})
check("A16 jalons : l'ordre des instantanés ne compte pas", CR.jalons_mesures(T0, list(reversed(SN)))[3]["views"] == 800)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from app.services.storage import init_db, ScheduledPost, PostMetric, async_session_factory  # noqa: E402
from app.services import metrics_service as ms                      # noqa: E402

NOW = datetime.utcnow().replace(microsecond=0)


def _m(pid, ch, at, views, raw=None, **k):
    return PostMetric(id=f"{pid}-{ch}-{at.isoformat()}", post_id=pid, channel=ch, remote_id="r" + pid, fetched_at=at,
                      views=views, likes=k.get("likes", 0), comments=0, shares=0, saves=0,
                      raw=json.dumps(raw) if raw is not None else None)


async def seed():
    async with async_session_factory() as s:
        # dix reels Instagram anciens (20 à 29 jours), relevés à J1 (100..1000 vues) et J7 (le double)
        for i in range(10):
            d = NOW - timedelta(days=20 + i)
            s.add(ScheduledPost(id=f"a{i}", title=f"Ancien {i}", channels="instagram", run_at=d, status="posted",
                                posted_at=d, format="reel", remote_ids=json.dumps({"instagram": f"ra{i}"})))
            s.add(_m(f"a{i}", "instagram", d + timedelta(days=1, hours=1), 100 * (i + 1)))
            s.add(_m(f"a{i}", "instagram", d + timedelta(days=7, hours=1), 200 * (i + 1)))
        # un reel de 8 jours : J1 = 1650 (3× l'habituel J1 de 550), J7 = 2200 (2× l'habituel J7 de 1100)
        d = NOW - timedelta(days=8)
        s.add(ScheduledPost(id="g1", title="Gagnant", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="reel", remote_ids=json.dumps({"instagram": "rg1"})))
        s.add(_m("g1", "instagram", d + timedelta(days=1, hours=2), 1650))
        s.add(_m("g1", "instagram", d + timedelta(days=7, hours=2), 2200, raw={"views": 2200, "avg_watch_ms": 23300}))
        # un reel de 2 jours : comparé à J1 (son seul jalon atteint), 3300 = 6× 550
        d = NOW - timedelta(days=2)
        s.add(ScheduledPost(id="j1", title="Jeune", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="reel", remote_ids=json.dumps({"instagram": "rj1"})))
        s.add(_m("j1", "instagram", d + timedelta(days=1, hours=3), 3300))
        # un reel de 5 heures : aucun jalon atteint
        d = NOW - timedelta(hours=5)
        s.add(ScheduledPost(id="n1", title="Neuf", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="reel", remote_ids=json.dumps({"instagram": "rn1"})))
        s.add(_m("n1", "instagram", d + timedelta(hours=2), 40))
        # une IMAGE Instagram : autre format, pas d'historique → pas d'habituel
        d = NOW - timedelta(days=9)
        s.add(ScheduledPost(id="i1", title="Image", channels="instagram", run_at=d, status="posted", posted_at=d,
                            format="image", remote_ids=json.dumps({"instagram": "ri1"})))
        s.add(_m("i1", "instagram", d + timedelta(days=7, hours=1), 5000))
        # X : quatre posts seulement → pas assez de recul
        for i in range(4):
            d = NOW - timedelta(days=9 + i)
            s.add(ScheduledPost(id=f"x{i}", title=f"X {i}", channels="x", run_at=d, status="posted", posted_at=d,
                                format="reel", x_post_id=f"tw{i}", remote_ids=json.dumps({"x": f"tw{i}"})))
            s.add(_m(f"x{i}", "x", d + timedelta(days=7, hours=1), 300 + i))
        await s.commit()


async def main():
    await init_db()
    await seed()
    print("\n[B] l'agrégat")
    a = await ms.analytics(days=15)
    it = {(d["id"], d["channel"]): d for d in a["items"]}
    g, j, n, im, x0 = it[("g1", "instagram")], it[("j1", "instagram")], it[("n1", "instagram")], it[("i1", "instagram")], it[("x0", "x")]
    check("B1 chaque item porte croissance", all("croissance" in d for d in a["items"]), str(list(g)))
    cg = g.get("croissance") or {}
    check("B2 jalons du gagnant : J1 1650, J3 absent (aucun relevé dans la fenêtre), J7 2200, J30 pas encore",
          cg.get("jalons") == {"j1": 1650, "j3": None, "j7": 2200, "j30": None}, str(cg.get("jalons")))
    check("B3 à 8 jours on compare à J7 : 2200 contre la médiane J7 des 10 précédents (1100) = 2×",
          cg.get("jalon") == 7 and cg.get("habituel") == 1100 and cg.get("multiplicateur") == 2.0, str(cg))
    check("B4 2× n'est pas un gagnant (seuil 3×)", cg.get("gagnant") is False and a.get("seuil_gagnant") == 3.0, str(cg))
    cj = j.get("croissance") or {}
    check("B5 à 2 jours on compare à J1, à âge égal : 3300 contre 550 = 6×, gagnant",
          cj.get("jalon") == 1 and cj.get("habituel") == 550 and cj.get("multiplicateur") == 6.0 and cj.get("gagnant") is True, str(cj))
    cn = n.get("croissance") or {}
    check("B6 à 5 heures : aucun jalon, aucun multiplicateur, raison « trop_tot »",
          cn.get("jalon") is None and cn.get("multiplicateur") is None and cn.get("raison") == "trop_tot", str(cn))
    ci = im.get("croissance") or {}
    check("B7 autre format (image) : pas d'historique du même format, raison « peu_de_recul »",
          ci.get("multiplicateur") is None and ci.get("raison") == "peu_de_recul" and ci.get("recul") == 0, str(ci))
    cx = x0.get("croissance") or {}
    check("B8 X, 3 posts précédents seulement : « peu_de_recul », le compte de recul est rendu",
          cx.get("multiplicateur") is None and cx.get("raison") == "peu_de_recul" and cx.get("recul") == 3, str(cx))
    check("B9 l'historique ne lit que des posts ANTÉRIEURS (le plus ancien X n'en a aucun)",
          (it[("x3", "x")].get("croissance") or {}).get("recul") == 0, str(it[("x3", "x")].get("croissance")))
    check("B10 temps de visionnage moyen lu dans `raw` (23,3 s) ; absent ailleurs",
          cg.get("visionnage_s") == 23.3 and cj.get("visionnage_s") is None, str(cg))
    check("B11 `gagnants` : les items au-dessus du seuil, du plus fort au plus faible",
          [d["id"] for d in a.get("gagnants", [])] == ["j1"], str(a.get("gagnants")))
    check("B12 l'ancien contrat tient : channels, formats, weeks, items, top, quotas, notes",
          {"days", "channels", "formats", "weeks", "items", "top", "quotas", "notes"} <= set(a), str(sorted(a)))
    check("B13 l'engagement et les vues courantes ne changent pas", g["views"] == 2200 and "engagement" in g)
    c2 = await ms.croissance_posts(["g1", "j1", "inconnu"])
    check("B14 croissance_posts : par post puis par canal, les inconnus sont absents",
          set(c2) == {"g1", "j1"} and c2["j1"]["instagram"]["multiplicateur"] == 6.0, str(c2))

    print("\n[C] Instagram : le temps de visionnage")
    from app.services import instagram_publisher as ig
    appels = []

    class _R:
        def __init__(self, code, data): self.status_code, self._d = code, data
        def json(self): return self._d

    class _C:
        refus = False
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            appels.append((url, dict(params or {})))
            if params["metric"] == ig.METRIC_VISIONNAGE:
                if _C.refus:
                    return _R(400, {"error": {"message": "metric not supported"}})
                return _R(200, {"data": [{"name": ig.METRIC_VISIONNAGE, "total_value": {"value": 14600}}]})
            return _R(200, {"data": [{"name": "views", "total_value": {"value": 900}}, {"name": "saved", "values": [{"value": 7}]}]})

    ig._client = lambda timeout=60.0: _C()
    from app.services.comptes import cred
    settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = "IGbanc", "1"
    r = await ig.fetch_insights(["m1"])
    check("C1 deux appels par média : les cinq mesures, puis le temps de visionnage SEUL",
          [p["metric"] for _u, p in appels] == [ig.METRICS, ig.METRIC_VISIONNAGE], str(appels))
    check("C2 le temps de visionnage rejoint la mesure (ms)", r.get("m1", {}).get("avg_watch_ms") == 14600
          and r["m1"]["views"] == 900 and r["m1"]["saves"] == 7, str(r))
    _C.refus = True
    r = await ig.fetch_insights(["m2"])
    check("C3 refusé (400) : les cinq mesures restent, sans la clé", r.get("m2", {}).get("views") == 900
          and "avg_watch_ms" not in r["m2"], str(r))
    check("C4 le jeton n'est dans aucune URL", all("IGbanc" not in u for u, _p in appels))

    print("\n[D] l'agent lit la croissance")
    from app.services import agent_outils as ao
    src = pathlib.Path(ao.__file__).read_text(encoding="utf-8")
    check("D1 lire_planificateur appelle metrics_service.croissance_posts", "croissance_posts" in src.split("async def lire_planificateur")[1].split("\nasync def ")[0].split("\ndef ")[0])

    print("\n[E] les compétences des agents")
    from app.services import agent_campagnes as AC, espaces
    docs = AC.DOCS
    fiches = ("competences.md", "competence-accroches.md", "competence-script-court.md", "competence-formats-instagram.md",
              "competence-fil-x.md", "competence-mesures.md", "competence-recyclage.md", "competence-client.md",
              "competence-compagnon.md")
    check("E1 les neuf fiches existent", all((docs / f).is_file() for f in fiches), str([f for f in fiches if not (docs / f).is_file()]))
    tout = "\n".join((docs / f).read_text(encoding="utf-8") for f in fiches if (docs / f).is_file())
    check("E2 aucune fiche ne nomme un outil absent de la table", all(o in ao.OUTILS for o in
          set(__import__("re").findall(r"`([a-z_]+)`", tout)) - {"controle"}), str(sorted(set(__import__("re").findall(r"`([a-z_]+)`", tout)))))
    check("E3 ni « skill », ni ~/.claude, ni promesse d'outil de publication", "skill" not in tout.lower() and "~/.claude" not in tout)
    check("E4 chaque fiche reste courte (< 1300 octets)", all(len((docs / f).read_bytes()) < 1300 for f in fiches),
          str({f: len((docs / f).read_bytes()) for f in fiches}))
    a_id = espaces.creer({"nom": "Marque banc", "couleur": "#112233"})["id"]
    c_id = espaces.creer({"nom": "Client banc", "couleur": "#445566", "type": "client"})["id"]
    sc = AC.systeme_pour("campagnes", a_id, "fr")
    check("E5 rôle campagnes : l'index et les six fiches de métier", all(t in sc for t in (
        "## Compétences", "## Compétence : accroches", "## Compétence : script court", "## Compétence : formats Instagram",
        "## Compétence : X", "## Compétence : lire les mesures", "## Compétence : recycler un gagnant")))
    check("E6 espace de marque : pas la fiche client", "## Compétence : espace client" not in sc)
    check("E7 espace client : la fiche client", "## Compétence : espace client" in AC.systeme_pour("campagnes", c_id, "fr"))
    sb = AC.systeme_pour("bilan", a_id, "fr")
    check("E8 rôle bilan : mesures et recyclage seulement", "## Compétence : lire les mesures" in sb
          and "## Compétence : recycler un gagnant" in sb and "## Compétence : accroches" not in sb)
    sd = AC.systeme_pour("demonstrateur", a_id, "fr")
    check("E9 démonstrateur : aucune fiche de métier", "## Compétence : accroches" not in sd and "## Compétence : lire les mesures" not in sd)
    check("E9b démonstrateur sur un espace client : toujours aucune fiche, pas même l'index",
          "## Compétence" not in AC.systeme_pour("demonstrateur", c_id, "fr"))
    so = AC.systeme_pour("orienteur", a_id, "fr")
    check("E10 orienteur et campagnes (rôles du téléphone) : la fiche « sur le téléphone »",
          "## Compétence : sur le téléphone" in so and "## Compétence : sur le téléphone" in sc)
    check("E11 la langue reste la DERNIÈRE section", sc.rstrip().endswith("Réponds en français.")
          and AC.systeme_pour("campagnes", a_id, "en").rstrip().endswith("Answer in English."))
    check("E12 CAMPAGNES.md reste en tête", sc.startswith("# Agent Campagnes"))
    from app.api import agent_campagnes_routes as RT
    p = RT._paquet(None)
    check("E13 le paquet du compagnon sert les neuf fiches", all(f in p["fichiers"] for f in fiches))
    from app.services import agent_metier as AM
    sp = AM.systeme("publicitaire", "fr")
    check("E14 le Publicitaire reçoit accroches et script court, après ses méthodes",
          "## Compétence : accroches" in sp and "## Compétence : script court" in sp
          and sp.index("## Tes méthodes") < sp.index("## Compétence : accroches"))
    check("E15 le Monteur ne les reçoit pas", "## Compétence :" not in AM.systeme("monteur", "fr"))
    from app.services import agent_whatsapp as AW
    check("E16 WhatsApp : la fiche de validation seulement si le rôle « validation » est coché",
          "## Compétence : validation des publications" in AW.systeme(c_id, {"roles": ["validation"]}, "fr")
          and "## Compétence : validation des publications" not in AW.systeme(c_id, {"roles": ["faq"]}, "fr"))


asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
