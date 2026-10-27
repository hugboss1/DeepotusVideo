# -*- coding: utf-8 -*-
"""t352 (27/10/2026) : la veille par espace — stockage sous espaces/<id>/veille/<date>/, collecte de fond (une à la fois),
état fantôme après un redémarrage, import d'une veille faite hors de l'app, route /api/veille.
La collecte réseau est SIMULÉE (couture veille._COLLECTER). Run : & $PY tests/test_veille_routes.py (depuis backend/)."""
import asyncio, json, os, sys, tempfile, pathlib, time
sys.stdout.reconfigure(encoding="utf-8")
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzt352_routes_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(TMP)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (str(TMP) + "/t.db").replace("\\", "/")
for d in ("images", "outputs"):
    (TMP / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(TMP / "images")
os.environ["OUTPUTS_FOLDER"] = str(TMP / "outputs")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import espaces, veille as V, veille_collecte as VC   # noqa: E402

EID = espaces.creer({"nom": "Veille test"})["id"]
EID2 = espaces.creer({"nom": "Autre"})["id"]
APPELS = []
ATTENTE = {"duree": 0.0}


async def faux_collecter(perimetre, brut, echeance, journal):
    APPELS.append([c["id"] for c in perimetre["concurrents"]])
    await asyncio.sleep(ATTENTE["duree"])
    brut.mkdir(parents=True, exist_ok=True)
    lignes = [{"concurrent": "runway", "source": "hn", "url": f"https://n/{i}", "date": "2026-06-01", "auteur_hash": f"a{i}",
               "texte": f"credits way too expensive, refund please {i}", "score": None, "collecte_le": "x", "requete": "q"}
              for i in range(4)]
    (brut / "hn-runway.jsonl").write_text("".join(json.dumps(l) + "\n" for l in lignes), encoding="utf-8")
    journal("hn runway : +4")
    return {"ajoutes": {"hn": 4}, "limites": ["youtube : yt-dlp introuvable, source indisponible"]}

V._COLLECTER = faux_collecter
c = TestClient(app)


def attendre_fin(eid, n=100):
    for _ in range(n):
        e = c.get(f"/api/veille/{eid}").json()["etat"]
        if e and e.get("etat") != "en_cours":
            return e
        time.sleep(0.05)
    return None


print("[1] sans veille")
r = c.get(f"/api/veille/{EID}")
check("test_lire_sans_veille : 200, rapport null", r.status_code == 200 and r.json()["rapport"] is None
      and r.json()["veilles"] == [], r.text)
check("test_espace_inconnu_404", c.get("/api/veille/esp_inconnu0").status_code == 404)
check("test_espace_inconnu_404 : collecte", c.post("/api/veille/esp_inconnu0/collectes", json={}).status_code == 404)
p = c.get(f"/api/veille/{EID}/perimetre").json()
check("test_perimetre : défaut", len(p["concurrents"]) == 13, p)

print("\n[2] collecte de fond")
with c:   # la boucle de l'application vit le temps du bloc (tâche de fond)
    r = c.post(f"/api/veille/{EID}/collectes", json={"perimetre": {"concurrents": [{"id": "runway", "hn": ["runwayml"]}]}})
    check("test_lancer : 202", r.status_code == 202 and r.json()["concurrents"] == ["runway"], r.text)
    e = attendre_fin(EID)
    check("test_lancer_puis_rapport : fini_partiel (une limite)", e and e["etat"] == "fini_partiel", e)
    g = c.get(f"/api/veille/{EID}").json()
    R = g["rapport"]
    check("test_lancer_puis_rapport : rapport", R and R["volumes"]["gardes"] == 4 and R["douleurs"][0]["theme"] == "prix_credits", R)
    check("test_lancer_puis_rapport : limites reprises", any("yt-dlp" in l for l in R["limites"]), R["limites"])
    check("test_lancer_puis_rapport : liste", len(g["veilles"]) == 1 and g["veilles"][0]["classement"] == "auto", g["veilles"])
    d = V.dossier(EID, R["date"])
    check("test_donnees_sous_l_espace", d == espaces.dossier() / EID / "veille" / R["date"]
          and all((d / f).exists() for f in ("perimetre.json", "verbatims.jsonl", "rapport.json", "brut/hn-runway.jsonl")))
    vb = c.get(f"/api/veille/{EID}/verbatims", params={"theme": "prix_credits", "limite": 2}).json()
    check("test_verbatims : filtre et limite", len(vb["verbatims"]) == 2 and all(v["theme"] == "prix_credits" for v in vb["verbatims"]), vb)
    check("test_verbatims : sans auteur", all("auteur_hash" not in v for v in vb["verbatims"]))
    check("test_perimetre : le dernier repris", c.get(f"/api/veille/{EID}/perimetre").json()["concurrents"][0]["id"] == "runway")

    ATTENTE["duree"] = 0.5
    r1 = c.post(f"/api/veille/{EID2}/collectes", json={})
    r2 = c.post(f"/api/veille/{EID2}/collectes", json={})
    check("test_conflit_409", r1.status_code == 202 and r2.status_code == 409, (r1.status_code, r2.status_code))
    check("test_conflit : autre espace libre", c.post(f"/api/veille/{EID}/collectes", json={}).status_code == 202)
    attendre_fin(EID2); attendre_fin(EID)
    ATTENTE["duree"] = 0.0
    check("test_perimetre_invalide_422", c.post(f"/api/veille/{EID}/collectes",
                                                json={"perimetre": {"concurrents": [{"id": "../x"}]}}).status_code == 422)

print("\n[3] état fantôme")
f = espaces.dossier() / EID2 / "veille" / "etat.json"
etat = json.loads(f.read_text(encoding="utf-8"))
etat.update(etat="en_cours", debut_ts=time.time() - VC.DUREE_MAX - 300)
f.write_text(json.dumps(etat), encoding="utf-8")
check("test_etat_fantome : lu interrompu", V.etat(EID2)["etat"] == "interrompu", V.etat(EID2))
with c:
    check("test_etat_fantome : ne bloque pas", c.post(f"/api/veille/{EID2}/collectes", json={}).status_code == 202)
    attendre_fin(EID2)

print("\n[4] dossiers confinés")
for mauvais in (("../x", None), ("esp_zz", "../../etc"), (EID, "2026-13-99"), (EID, "2026-10-27/../..")):
    def _refuse(m=mauvais):
        try:
            V.dossier(*m)
        except ValueError:
            return True
        return False
    check(f"test_dossier_confine : {mauvais}", _refuse)

print("\n[5] import")
src = TMP / "source" / "2026-10-20"   # pas aujourd'hui : le cas du même jour est la série [6]
src.mkdir(parents=True)
VERB = [{"concurrent": "capcut", "source": "hn", "url": f"https://news.ycombinator.com/item?id={i}", "date": "2026-06-08T22:55:01Z",
         "auteur_hash": f"h{i}", "auteur": "PseudoEnClair", "texte": f"Two paid features of CapCut I rebuilt myself {i}", "score": None,
         "collecte_le": "2026-10-27T12:34:12+00:00", "requete": "capcut", "theme": "prix_credits", "polarite": "faiblesse",
         "intensite": 1, "resume": "Deux fonctions payantes refaites soi-même.", "chez_nous": "regle"} for i in range(5)]
(src / "verbatims.jsonl").write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in VERB) + "{cassé\n", encoding="utf-8")
(src / "rapport.md").write_text("ne jamais lire", encoding="utf-8")
r = c.post(f"/api/veille/{EID}/importer", json={"dossier": str(src)})
j = r.json()
check("test_import_veille_n1 : 200", r.status_code == 200 and j["lignes"] == 5 and j["ignorees"] == 1, r.text)
check("test_import_veille_n1 : date du dossier source", j["date"] == "2026-10-20")
R = c.get(f"/api/veille/{EID}").json()
check("test_import_veille_n1 : classement importé", any(v["date"] == "2026-10-20" and v["classement"] == "importe" for v in R["veilles"]))
dv = V.dossier(EID, "2026-10-20")
check("test_import_hostile : champ auteur retiré", b"PseudoEnClair" not in (dv / "verbatims.jsonl").read_bytes())
check("test_import_hostile : seul verbatims.jsonl lu", not (dv / "rapport.md").exists())
check("test_import : fichier direct", c.post(f"/api/veille/{EID}/importer", json={"dossier": str(src / "verbatims.jsonl")}).status_code == 200)
check("test_import_hostile : autre fichier refusé", c.post(f"/api/veille/{EID}/importer",
                                                           json={"dossier": str(src / "rapport.md")}).status_code == 422)
check("test_import_hostile : absent 422", c.post(f"/api/veille/{EID}/importer", json={"dossier": str(TMP / "rien")}).status_code == 422)
print("\n[6] import et collecte le même jour : les deux restent")
import datetime as _dt
jour = _dt.date.today().isoformat()
src2 = TMP / "source2" / jour
src2.mkdir(parents=True)
(src2 / "verbatims.jsonl").write_text("".join(json.dumps(dict(v, url=v["url"] + "#j")) + "\n" for v in VERB), encoding="utf-8")
avant = c.get(f"/api/veille/{EID}").json()["rapport"]
check("test_meme_jour : une collecte du jour existe", avant["date"] == jour and avant["volumes"]["gardes"] >= 4, avant["date"])
r = c.post(f"/api/veille/{EID}/importer", json={"dossier": str(src2)})
R = c.get(f"/api/veille/{EID}", params={"date": jour}).json()["rapport"]
check("test_meme_jour : import + collecte comptés", r.status_code == 200 and R["volumes"]["gardes"] == avant["volumes"]["gardes"] + 5, R["volumes"])
with c:
    ATTENTE["duree"] = 0.3
    c.post(f"/api/veille/{EID}/collectes", json={})
    check("test_import_pendant_collecte_409", c.post(f"/api/veille/{EID}/importer", json={"dossier": str(src2)}).status_code == 409)
    attendre_fin(EID)
    ATTENTE["duree"] = 0.0
R = c.get(f"/api/veille/{EID}", params={"date": jour}).json()["rapport"]
check("test_meme_jour : la collecte suivante garde l'import", R["volumes"]["gardes"] == avant["volumes"]["gardes"] + 5, R["volumes"])

print("\n[7] relecture finale : import bancal, pseudos, BOM, périmètre de l'agent, exclusion import/collecte")
src3 = TMP / "source3" / "2026-10-21"
src3.mkdir(parents=True)
bancales = [dict(VERB[0], concurrent=["a"], url="https://b/1"), dict(VERB[1], url="https://b/2", source="appstore-us", score=float("nan"),
            polarite=None, theme=None), dict(VERB[2], url="https://b/3", auteur_hash="PseudoClairBis"), dict(VERB[3], url="https://b/4")]
txt = "﻿" + "".join(json.dumps(v, ensure_ascii=False) + "\n" for v in bancales)   # BOM (Bloc-notes, PowerShell)
(src3 / "verbatims.jsonl").write_text(txt, encoding="utf-8")
r = c.post(f"/api/veille/{EID}/importer", json={"dossier": str(src3)})
check("test_import_bancal : 200, rien ne casse", r.status_code == 200, r.text[:300])
check("test_import_bom : la 1re ligne est lue", r.status_code == 200 and r.json()["lignes"] + r.json()["ignorees"] == 4
      and r.json()["lignes"] >= 3, r.text[:200])
dv3 = V.dossier(EID, "2026-10-21")
check("test_import_pseudo : un auteur_hash qui n'est pas une empreinte n'est pas écrit",
      all(b"PseudoClairBis" not in f.read_bytes() for f in dv3.glob("*.jsonl")))
import math as _m
lus = [json.loads(l) for l in (dv3 / "importe.jsonl").read_text(encoding="utf-8").splitlines() if l]
check("test_import_types : chaînes et nombres finis seulement", all(isinstance(l.get("concurrent"), (str, type(None)))
      and (l.get("score") is None or (isinstance(l["score"], (int, float)) and _m.isfinite(l["score"]))) for l in lus), lus)
p0 = V.perimetre(EID)
with c:
    async def _lancer_sous():
        return await V.lancer(EID, {"concurrents": [{"id": "pika"}]}, retenir=False)
    import anyio as _anyio
    c.portal.call(_lancer_sous)
    attendre_fin(EID)
check("test_sous_ensemble_agent_non_retenu", V.perimetre(EID) == p0, V.perimetre(EID)["concurrents"][:2])
V._IMPORTS.add(EID)
try:
    check("test_collecte_pendant_import_409", c.post(f"/api/veille/{EID}/collectes", json={}).status_code == 409)
finally:
    V._IMPORTS.discard(EID)

gros = TMP / "gros"
gros.mkdir()
with open(gros / "verbatims.jsonl", "wb") as fh:
    fh.truncate(V.MAX_IMPORT + 1)
check("test_import_hostile : trop gros 413", c.post(f"/api/veille/{EID}/importer", json={"dossier": str(gros)}).status_code == 413)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
