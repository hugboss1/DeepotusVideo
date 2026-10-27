# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : les routes /api/prospects et la purge planifiée.
Ce que ce banc garde : le cycle complet propose → client par HTTP (l'espace démonstration naît puis devient client) ;
chaque refus rend {code, message} au bon statut HTTP, traduit en anglais quand la langue est EN (L10) ; l'export arrive
en pièce jointe ; un effacé ne se recrée pas ; un appel venu du réseau est refusé (local seulement) ; un espace
démonstration n'a pas de prospects (404) ; la purge lit en brut (espaces.json ni relu par lire() ni réécrit) ; aucun
module du lot n'importe de quoi dépenser ou envoyer. Data-dir isolé, aucun réseau.
Run (depuis backend/) : & $PY tests/test_prospects_routes.py"""
import os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzprr_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
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
from app.services import espaces as E, prospects as P               # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 27)
c = TestClient(app)
lan = TestClient(app, client=("192.168.1.20", 50000))
EN = {"Accept-Language": "en"}
A = E.creer({"nom": "Prospection"})["id"]
SRC = {"type": "web", "url": "https://studio-lune.fr/contact", "date": "2026-10-20"}
CORPS = {"nom": "Léa Martin", "entreprise": "Studio Lune", "source": SRC, "base_legale": "interet_legitime_b2b",
         "offre": "prestation", "canaux": [{"type": "email", "valeur": "lea@studio-lune.fr"}]}

print("[1] cycle complet")
r = c.post(f"/api/prospects/{A}", json=CORPS)
check("1a création 201", r.status_code == 201 and r.json()["statut"] == "propose", r.text)
pid = r.json()["id"]
for s in ("qualifie", "contacte", "repondu", "rdv"):
    r = c.post(f"/api/prospects/{A}/{pid}/statut", json={"statut": s})
demo = r.json()["prospect"]["espace_demo"]
check("1b rdv : espace démonstration", r.status_code == 200 and E.est_demonstration(demo), r.text)
r = c.post(f"/api/prospects/{A}/{pid}/statut", json={"statut": "client", "detail": "devis signé"})
check("1c signature : client", r.status_code == 200 and E.lire()["espaces"][demo]["type"] == "client")
r = c.get(f"/api/prospects/{A}")
j = r.json()
check("1d liste, comptes par statut, registre", r.status_code == 200 and len(j["prospects"]) == 1
      and j["compte_par_statut"].get("client") == 1 and j["oppositions"] == 0, str(j)[:300])
check("1e filtre par statut", c.get(f"/api/prospects/{A}?statut=perdu").json()["prospects"] == [])
r = c.patch(f"/api/prospects/{A}/{pid}", json={"score": 80, "prochaine_action": {"texte": "relancer", "le": "2026-11-03"}})
check("1f modifier", r.status_code == 200 and r.json()["score"] == 80 and r.json()["prochaine_action"]["texte"] == "relancer")
r = c.post(f"/api/prospects/{A}/{pid}/consentements", json={"canal": "email", "base_legale": "consentement", "moyen": "ecrit"})
check("1g consentement", r.status_code == 200 and r.json()["consentements"][0]["canal"] == "email")
r = c.post(f"/api/prospects/{A}/{pid}/consentements/revoquer", json={"canal": "email"})
check("1h révocation", r.status_code == 200 and r.json()["consentements"][0]["revoque_le"])
r = c.post(f"/api/prospects/{A}/{pid}/contacts", json={"sens": "entrant", "detail": "a répondu"})
check("1i contact entrant", r.status_code == 200 and r.json()["dernier_contact_entrant"] == "2026-10-27")

print("[2] refus structurés, FR / EN")
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, source=None))
check("2a source : 422 {code, message}", r.status_code == 422 and r.json()["detail"]["code"] == "source"
      and "source" in r.json()["detail"]["message"], r.text)
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, base_legale=None), headers=EN)
check("2b base légale traduite en anglais", r.status_code == 422 and r.json()["detail"]["code"] == "base_legale"
      and "legal basis" in r.json()["detail"]["message"].lower(), r.text)
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, nom="x", canaux=[{"type": "email", "valeur": "x@gmail.com"}]), headers=EN)
check("2c email_perso 409 en anglais", r.status_code == 409 and r.json()["detail"]["code"] == "email_perso"
      and "business" in r.json()["detail"]["message"].lower(), r.text)
r = c.post(f"/api/prospects/{A}", json=CORPS)
check("2d doublon 409 avec l'id existant", r.status_code == 409 and r.json()["detail"]["code"] == "doublon"
      and r.json()["detail"]["pid"] == pid, r.text)
r = c.post(f"/api/prospects/{A}/{pid}/statut", json={"statut": "qualifie"}, headers=EN)
check("2e transition 409 en anglais", r.status_code == 409 and r.json()["detail"]["code"] == "transition"
      and "cannot" in r.json()["detail"]["message"].lower(), r.text)
check("2f prospect inconnu 404", c.get(f"/api/prospects/{A}/pr_00000000").status_code == 404)
check("2g espace inconnu 404", c.get("/api/prospects/esp_inconnu").status_code == 404)

print("[3] export, effacement, opposition saisie")
r = c.get(f"/api/prospects/{A}/{pid}/export")
check("3a export en pièce jointe", r.status_code == 200 and "attachment" in r.headers.get("content-disposition", "")
      and f"prospect-{pid}.json" in r.headers.get("content-disposition", "") and r.json()["nom"] == "Léa Martin")
r = c.delete(f"/api/prospects/{A}/{pid}")
check("3b effacé", r.status_code == 200 and c.get(f"/api/prospects/{A}/{pid}").status_code == 404)
r = c.post(f"/api/prospects/{A}", json=CORPS)
check("3c effacer puis recréer : opposition 409", r.status_code == 409 and r.json()["detail"]["code"] == "opposition", r.text)
r = c.post("/api/prospects/oppositions", json={"identifiant": "Paul@agence-m.fr"})
check("3d opposition saisie, rien en clair", r.status_code == 200 and r.json() == {"inscrit": True})
check("3e déjà inscrit", c.post("/api/prospects/oppositions", json={"identifiant": "paul@agence-m.fr"}).json() == {"inscrit": False})
check("3f identifiant illisible : 422", c.post("/api/prospects/oppositions", json={"identifiant": "bonjour"}).status_code == 422)
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, nom="Ninon", canaux=[{"type": "email", "valeur": "ninon@agence-n.fr"}]))
n = r.json()["id"]
r = c.post(f"/api/prospects/{A}/{n}/opposer")
check("3g opposer : anonymisé", r.status_code == 200 and r.json()["statut"] == "oppose" and r.json()["nom"] == "")
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, nom="Erreur", canaux=[{"type": "email", "valeur": "faute@agence-e.fr"}]))
e = r.json()["id"]
c.delete(f"/api/prospects/{A}/{e}?inscrire_opposition=0")
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, nom="Erreur", canaux=[{"type": "email", "valeur": "faute@agence-e.fr"}]))
check("3h saisie erronée effacée sans inscription : recréable", r.status_code == 201, r.text)

print("[4] local seulement ; démonstration")
check("4a lecture distante refusée", lan.get(f"/api/prospects/{A}").status_code in (401, 403))
check("4b écriture distante refusée", lan.post(f"/api/prospects/{A}", json=CORPS).status_code in (401, 403))
r = c.post(f"/api/prospects/{A}", json=dict(CORPS, nom="Rémi", canaux=[{"type": "email", "valeur": "remi@agence-r.fr"}]))
rid = r.json()["id"]
for s in ("qualifie", "contacte", "repondu", "rdv"):
    r = c.post(f"/api/prospects/{A}/{rid}/statut", json={"statut": s})
d2 = r.json()["prospect"]["espace_demo"]
check("4c espace démonstration : 404", c.get(f"/api/prospects/{d2}").status_code == 404
      and c.post(f"/api/prospects/{d2}", json=CORPS).status_code == 404)

print("[5] purge brute")
f = E.dossier() / "espaces.json"
avant = f.read_bytes()
appels = []
_lire = E.lire
E.lire = lambda *a, **k: appels.append(1) or _lire(*a, **k)
r = P.purger(date(2040, 1, 1))
E.lire = _lire
check("5a tout est échu en 2040, retiré", r.get(A, 0) >= 3, str(r))
check("5b espaces.json ni lu par lire() ni réécrit", not appels and f.read_bytes() == avant)
import asyncio                                                       # noqa: E402
P._aujourdhui = lambda: date(2026, 10, 27)
compte = []
_purger = P.purger
P.purger = lambda j: compte.append(j) or {}


async def _une_boucle():
    t = asyncio.create_task(P.purge_loop(premier=0, intervalle=3600))
    await asyncio.sleep(0.3)
    t.cancel()


asyncio.run(_une_boucle())
P.purger = _purger
check("5c la boucle purge au démarrage", len(compte) == 1)

print("[6] aucune dépense, aucun envoi")
racine = _ICI.parent / "app"
for fichier in ("services/prospects.py", "services/oppositions.py", "api/prospects_routes.py"):
    src = (racine / fichier).read_text(encoding="utf-8")
    interdits = [m for m in ("plafonds", "pricing", "httpx", "kapso", "smtplib", "moteurs_texte") if m in src]
    check(f"6 {fichier} n'importe rien qui dépense ou envoie", not interdits, str(interdits))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
