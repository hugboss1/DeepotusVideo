# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 3 : le geste QUALIFIER (barème + ajustement borné, offre, canaux
possibles), l'origine « agent » et la date d'information de l'art. 14 (collecte indirecte → collecte + 30 jours).
Qualifier ne touche jamais le statut ; un opposé est refusé. Route POST /api/prospects/{eid}/{pid}/qualifier (locale).
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_qualifier.py"""
import os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpq_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except P.RefusProspect as r:
        return (r.code, r.statut)
    return None


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import espaces as E, prospects as P, prospects_score as SC   # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 28)
SC._aujourdhui = lambda: date(2026, 10, 28)
c = TestClient(app)
lan = TestClient(app, client=("192.168.1.20", 50000))
A = E.creer({"nom": "Prospection"})["id"]
WEB = {"type": "web", "url": "https://studio-lune.fr/contact", "date": "2026-10-28"}

print("[1] qualifier")
f = P.creer(A, {"entreprise": "Studio Lune", "source": WEB, "base_legale": "interet_legitime_b2b", "signal": "studio vidéo",
                "canaux": [{"type": "email", "valeur": "contact@studio-lune.fr"}]}, qui="agent")
q = P.qualifier(A, f["id"], "prestation", 10, "studio de 12 personnes, besoin de volume", qui="agent")
Q = q["qualification"]
check("1a base = barème (web 15 + canal 15 + pro 10 + signal 5 = 45)", Q["base"] == 45 and Q["details"], Q)
check("1b score = base + ajustement, offre posée", q["score"] == 55 and q["offre"] == "prestation" and Q["ajustement"] == 10
      and Q["raison"].startswith("studio") and Q["qui"] == "agent" and Q["le"], q["score"])
check("1c canaux possibles gardés", Q["canaux_possibles"][0]["canal"] == "email")
check("1d le statut ne bouge pas", q["statut"] == "propose")
check("1e historique : une ligne qualification", q["historique"][-1]["quoi"] == "qualification" and q["historique"][-1]["qui"] == "agent")
check("1f ajustement 25 refusé (422)", refus(P.qualifier, A, f["id"], "licence", 25, "trop") == ("champ", 422))
check("1g ajustement sans raison refusé (422)", refus(P.qualifier, A, f["id"], "licence", 5, "  ") == ("champ", 422))
check("1h offre inconnue refusée (422)", refus(P.qualifier, A, f["id"], "abonnement") == ("champ", 422))
check("1i ajustement 0 sans raison permis", P.qualifier(A, f["id"], "licence")["score"] == 45)
check("1j relu tel quel", P.lire(A, f["id"])["qualification"]["base"] == 45)

print("[2] origine agent, information art. 14")
check("2a par_agent posé par creer(qui=agent)", f["par_agent"] is True)
check("2b gardé par modifier", P.modifier(A, f["id"], {"role": "gérante"})["par_agent"] is True)
g = P.creer(A, {"nom": "Léa", "source": {"type": "liste_attente", "date": "2026-10-20"}, "base_legale": "consentement",
                "canaux": [{"type": "email", "valeur": "lea@gmail.com"}]})
check("2c utilisateur : par_agent faux ; collecte directe : pas d'information à faire", g["par_agent"] is False
      and g["informer_avant"] is None, (g["par_agent"], g["informer_avant"]))
check("2d collecte indirecte (web) : informer avant collecte + 30 j", f["informer_avant"] == "2026-11-27", f["informer_avant"])
h = P.creer(A, {"nom": "Reco", "source": {"type": "recommandation", "date": "2026-10-28"}, "base_legale": "interet_legitime_b2b",
                "canaux": [{"type": "email", "valeur": "reco@agence-r.fr"}]})
check("2e recommandation : indirecte aussi", h["informer_avant"] == "2026-11-27")

print("[3] opposé")
P.opposer(A, h["id"])
check("3a qualifier un opposé : 409", refus(P.qualifier, A, h["id"], "licence") == ("transition", 409))

print("[4] route")
r = c.post(f"/api/prospects/{A}/{f['id']}/qualifier", json={"offre": "licence", "ajustement": -5, "raison": "petit budget"})
check("4a 200, recalculé", r.status_code == 200 and r.json()["score"] == 40 and r.json()["qualification"]["qui"] == "utilisateur", r.text[:200])
r = c.post(f"/api/prospects/{A}/{f['id']}/qualifier", json={"offre": "licence", "ajustement": 50, "raison": "x"}, headers={"Accept-Language": "en"})
check("4b 422 champ, en anglais", r.status_code == 422 and r.json()["detail"]["code"] == "champ" and "adjustment" in r.json()["detail"]["message"], r.text[:200])
check("4c 404 inconnu", c.post(f"/api/prospects/{A}/pr_00000000/qualifier", json={"offre": "licence"}).status_code == 404)
check("4d local seulement", lan.post(f"/api/prospects/{A}/{f['id']}/qualifier", json={"offre": "licence"}).status_code in (401, 403))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
