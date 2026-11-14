# -*- coding: utf-8 -*-
"""t492 (lot G2 « boucle de croissance », 09/11/2026) — le tableau « Croissance ».

[A] pur         croissance.regularite : jours LOCAUX, série qui tolère un aujourd'hui encore vide, semainier
[B] service     metrics_service.tableau : totaux, canaux, top par vues, gagnants, filtre par espace
[C] Instagram   fetch_compte : une mesure par appel, ventilation abonnés / non-abonnés, illisibles nommés, cache, jeton masqué
[D] route       GET /api/schedule/croissance : bornes, compte, panne réseau tolérée
Data-dir temporaire, aucun réseau.
Run : & $PY tests/test_croissance_tableau.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcrt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import croissance as CR                           # noqa: E402

print("\n[A] la régularité")
FIN = datetime(2026, 11, 9, 23, 30)                                 # UTC
J = lambda j, h=12: datetime(2026, 11, j, h, 0)
r = CR.regularite([J(9), J(8), J(8, 18), J(7), J(5), J(1), datetime(2026, 10, 1, 12, 0)], FIN, 30)
check("A1 jours avec un post : deux posts le même jour comptent pour un jour, hors fenêtre ignoré",
      r["jours"] == 30 and r["jours_avec_post"] == 5, str(r))
check("A2 série : 9, 8, 7 puis un trou", r["serie"] == 3, str(r))
check("A3 aujourd'hui encore vide : la série part d'hier", CR.regularite([J(8), J(7)], FIN, 30)["serie"] == 2)
check("A4 ni aujourd'hui ni hier : série nulle", CR.regularite([J(6), J(5)], FIN, 30)["serie"] == 0)
check("A5 semainier : 7 jours, du plus ancien à aujourd'hui, avec leur nombre de posts",
      [d["posts"] for d in r["semaine"]] == [0, 0, 1, 0, 1, 2, 1] and r["semaine"][-1]["jour"] == "2026-11-09"
      and r["semaine"][0]["jour"] == "2026-11-03", str(r["semaine"]))
# 23:30 UTC le 9 = 00:30 le 10 à UTC+1 : aujourd'hui LOCAL est le 10
rl = CR.regularite([J(9, 23)], FIN, 30, tz_min=60)
check("A6 les jours sont LOCAUX : un post du 9 à 23 h UTC tombe le 10 à UTC+1", rl["semaine"][-1] == {"jour": "2026-11-10", "posts": 1}, str(rl["semaine"]))
check("A7 fenêtre d'un jour : semainier d'un jour", len(CR.regularite([J(9)], FIN, 1)["semaine"]) == 1)
check("A8 dates None ignorées, liste vide tolérée", CR.regularite([None], FIN, 7)["jours_avec_post"] == 0 and CR.regularite([], FIN, 7)["serie"] == 0)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
for _k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID"):
    setattr(settings, _k, "")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db, ScheduledPost, PostMetric, async_session_factory  # noqa: E402
from app.services import metrics_service as ms, instagram_publisher as ig  # noqa: E402

NOW = datetime.utcnow().replace(microsecond=0)


async def seed():
    async with async_session_factory() as s:
        for i, (eid, ch, vues) in enumerate((("e1", "instagram", 900), ("e1", "instagram", 300), ("e1", "x", 50),
                                             ("e2", "instagram", 7000))):
            d = NOW - timedelta(days=i + 1, hours=1)
            s.add(ScheduledPost(id=f"p{i}", title=f"Post {i}", channels=ch, run_at=d, status="posted", posted_at=d,
                                format="reel", espace_id=eid, remote_ids=json.dumps({ch: f"r{i}"})))
            s.add(PostMetric(id=f"m{i}", post_id=f"p{i}", channel=ch, remote_id=f"r{i}", fetched_at=NOW,
                             views=vues, likes=10, comments=1, shares=2, saves=3))
        s.add(ScheduledPost(id="sansmesure", title="Sans mesure", channels="instagram", run_at=NOW, status="posted",
                            posted_at=NOW - timedelta(hours=2), format="reel", espace_id="e1"))
        s.add(ScheduledPost(id="brouillon", title="Brouillon", channels="instagram", run_at=NOW, status="draft", espace_id="e1"))
        await s.commit()


class _R:
    def __init__(self, code, data): self.status_code, self._d = code, data
    def json(self): return self._d


class _C:
    appels: list = []
    refuse: set = set()
    panne = False
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def get(self, url, params=None):
        if _C.panne:
            raise RuntimeError("réseau coupé IGbanc")
        p = dict(params or {})
        _C.appels.append((url, p))
        if "fields" in p:
            return _R(200, {"username": "banc", "followers_count": 8931})
        m = p["metric"]
        if m in _C.refuse:
            return _R(400, {"error": {"message": "unsupported"}})
        if m == "views":
            return _R(200, {"data": [{"name": "views", "total_value": {"value": 2000, "breakdowns": [{"results": [
                {"dimension_values": ["FOLLOWER"], "value": 80}, {"dimension_values": ["NON_FOLLOWER"], "value": 1920}]}]}}]})
        if m == "follows_and_unfollows":
            return _R(200, {"data": [{"name": m, "total_value": {"breakdowns": [{"results": [
                {"dimension_values": ["FOLLOWER"], "value": 120}, {"dimension_values": ["NON_FOLLOWER"], "value": 20}]}]}}]})
        return _R(200, {"data": [{"name": m, "total_value": {"value": {"reach": 763, "total_interactions": 239}[m]}}]})


async def main():
    await init_db()
    await seed()
    print("\n[B] le tableau")
    t = await ms.tableau(30)
    check("B1 totaux tous espaces : 4 posts mesurés, vues additionnées", t["totaux"]["posts"] == 4 and t["totaux"]["views"] == 8250, str(t["totaux"]))
    check("B2 par canal", t["canaux"]["instagram"]["posts"] == 3 and t["canaux"]["x"]["views"] == 50, str(t["canaux"]))
    check("B3 top par vues décroissantes, chaque ligne avec sa croissance",
          [d["id"] for d in t["top"]] == ["p3", "p0", "p1", "p2"] and all("croissance" in d for d in t["top"]), str([d["id"] for d in t["top"]]))
    check("B4 régularité : le post sans mesure compte (5 jours avec post), les brouillons non",
          t["regularite"]["jours_avec_post"] == 5 and t["regularite"]["jours"] == 30, str(t["regularite"]))
    t1 = await ms.tableau(30, "e1")
    check("B5 un espace : ses posts seulement", t1["espace_id"] == "e1" and t1["totaux"]["posts"] == 3 and t1["totaux"]["views"] == 1250
          and all(d["espace_id"] == "e1" for d in t1["top"]), str(t1["totaux"]))
    check("B6 un espace : sa régularité seulement", t1["regularite"]["jours_avec_post"] == 4, str(t1["regularite"]))
    check("B7 espace inconnu : tableau vide, pas d'erreur", (await ms.tableau(30, "nulle-part"))["totaux"]["posts"] == 0)
    check("B8 seuil et gagnants présents", t["seuil_gagnant"] == 3.0 and t["gagnants"] == [])
    check("B9 fenêtre courte : 2 jours ne gardent que les posts récents", (await ms.tableau(2))["totaux"]["posts"] == 1)

    print("\n[C] le compte Instagram")
    check("C1 aucun compte relié : None, aucun appel", await ig.fetch_compte(30) is None)
    ig._client = lambda timeout=60.0: _C()
    settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = "IGbanc", "42"
    c = await ig.fetch_compte(30, maintenant=1_000_000.0)
    check("C2 profil et quatre mesures lus", c and c["username"] == "banc" and c["followers"] == 8931 and c["reach"] == 763
          and c["views"] == 2000 and c["interactions"] == 239 and c["follows"] == 120 and c["unfollows"] == 20, str(c))
    check("C3 part de non-abonnés : 1920 / 2000 = 96 %", c["non_abonnes_pct"] == 96 and c["illisibles"] == [], str(c))
    mets = [p.get("metric") for _u, p in _C.appels if "metric" in p]
    check("C4 UNE mesure par appel, dans l'ordre", mets == list(ig.METRIQUES_COMPTE), str(mets))
    check("C5 fenêtre : since/until sur 30 jours, total_value",
          all(p["until"] - p["since"] == 30 * 86400 and p["metric_type"] == "total_value" for _u, p in _C.appels if "metric" in p))
    check("C6 le jeton n'est dans aucune URL", all("IGbanc" not in u for u, _p in _C.appels))
    n = len(_C.appels)
    await ig.fetch_compte(30, maintenant=1_000_000.0 + 60)
    check("C7 relu dans le quart d'heure : servi du cache, aucun appel", len(_C.appels) == n)
    await ig.fetch_compte(30, maintenant=1_000_000.0 + ig.CACHE_COMPTE_S + 1)
    check("C8 après le quart d'heure : relu", len(_C.appels) == 2 * n, str(len(_C.appels)))
    _C.refuse = {"views", "follows_and_unfollows"}
    c = await ig.fetch_compte(7, maintenant=2_000_000.0)
    check("C9 deux mesures refusées : les autres restent, les refusées sont nommées",
          c["reach"] == 763 and c["views"] is None and c["non_abonnes_pct"] is None
          and c["illisibles"] == ["views", "follows_and_unfollows"] and c["jours"] == 7, str(c))
    check("C10 fenêtre bornée à 30 jours", (await ig.fetch_compte(365, maintenant=3_000_000.0))["jours"] == 30)
    _C.refuse = set()

    print("\n[D] la route")
    ig._cache_compte.clear()
    with TestClient(app) as cl:
        r = cl.get("/api/schedule/croissance?days=30")
        j = r.json()
        check("D1 200 : tableau + compte Instagram", r.status_code == 200 and j["totaux"]["posts"] == 4
              and j["compte"]["instagram"]["username"] == "banc", str(r.status_code))
        check("D2 clés du contrat", {"days", "espace_id", "totaux", "canaux", "top", "gagnants", "seuil_gagnant", "regularite",
                                    "notes", "compte"} <= set(j), str(sorted(j)))
        check("D3 espace_id filtré", cl.get("/api/schedule/croissance?espace_id=e2").json()["totaux"]["views"] == 7000)
        check("D4 days borné (0 → 1, 9999 → 365)", cl.get("/api/schedule/croissance?days=0").json()["days"] == 1
              and cl.get("/api/schedule/croissance?days=9999").json()["days"] == 365)
        check("D5 tz transmis à la régularité (semainier de 7 jours)", len(cl.get("/api/schedule/croissance?tz=60").json()["regularite"]["semaine"]) == 7)
        ig._cache_compte.clear()
        _C.panne = True
        r = cl.get("/api/schedule/croissance")
        check("D6 réseau coupé : 200, posts lisibles, compte None, jeton absent de la réponse",
              r.status_code == 200 and r.json()["compte"] == {"instagram": None, "erreur": True}
              and r.json()["totaux"]["posts"] == 4 and "IGbanc" not in r.text, r.text[:200])
        _C.panne = False
        check("D7 l'ancienne route analytics tient", cl.get("/api/schedule/analytics").status_code == 200)
        # 10/11/2026 (essai réel) : le compte lu est celui de L'ESPACE demandé, pas le compte historique
        from app.services import comptes as CP, espaces as ES
        perso = ES.creer({"nom": "Perso banc"})["id"]
        vide = ES.creer({"nom": "Sans compte"})["id"]
        CP.creer({"espace_id": perso, "plateforme": "instagram",
                  "valeurs": {"IG_ACCESS_TOKEN": "EAAperso", "IG_BUSINESS_ID": "1784"}})
        ig._cache_compte.clear()
        _C.appels.clear()
        r = cl.get(f"/api/schedule/croissance?espace_id={perso}")
        check("D8 un espace : SON compte Instagram est lu (son identifiant, son jeton, son hôte)",
              r.status_code == 200 and r.json()["compte"]["instagram"] is not None and _C.appels
              and all(u.startswith("https://graph.facebook.com/") and "/1784" in u and p["access_token"] == "EAAperso"
                      for u, p in _C.appels), str(_C.appels[:1]))
        check("D9 le jeton de l'espace n'est pas dans la réponse", "EAAperso" not in r.text)
        _C.appels.clear()
        r = cl.get(f"/api/schedule/croissance?espace_id={vide}")
        check("D10 un espace sans compte Instagram : None, aucun appel, jamais le compte d'un autre",
              r.json()["compte"] == {"instagram": None} and not _C.appels, str(_C.appels[:1]))
        ES.activer(perso)
        ig._cache_compte.clear()
        _C.appels.clear()
        r = cl.get("/api/schedule/croissance")
        check("D11 tous les espaces : le compte de l'espace ACTIF",
              r.json()["compte"]["instagram"] is not None and all("/1784" in u for u, _p in _C.appels) and _C.appels,
              str(_C.appels[:1]))
        ES.activer("deepotus")
        ig._cache_compte.clear()
        _C.appels.clear()
        r = cl.get("/api/schedule/croissance?espace_id=deepotus")
        check("D12 l'espace Deepotus garde son compte historique (clés plates)",
              r.json()["compte"]["instagram"] is not None and all("/42" in u and p["access_token"] == "IGbanc"
                                                                  for u, p in _C.appels) and _C.appels, str(_C.appels[:1]))


asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
