# -*- coding: utf-8 -*-
"""t353 suite (28/10/2026) — Veille & prospection P2, les MINEURS de la relecture finale, gardés.
M1 : un PATCH qui programme un post d'un espace démonstration est refusé (409 demonstration), comme sa création.
M2 : un paquet d'espace démonstration s'importe, comme marque, et l'import le dit.
M4 : une écriture de la fiche en échec défait le geste sur l'espace démonstration (jamais de 2e démo) ; une opposition
     dont le registre est indisponible ne touche pas la démo.
M5 : un statut absent ou inconnu est un 422 « champ », pas un 409 « transition ».
M6 : un STOP avec espaces.json illisible va au registre (refus par défaut) ; un réabonnement retire le STOP du registre ;
     une saisie (ou un effacement) se retire du registre, journalisé, local seulement ; une opposition de la personne, non.
M7 : un pseudo X / Instagram / LinkedIn sans https compte au registre et aux doublons, sous une forme unique.
M9 : renommer l'entreprise après le rdv renomme l'espace démonstration (espaces.json et persona).
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_mineurs.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzprm_"))
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
from app.services import comptes as CP, espaces as E, espaces_paquet as PQ, oppositions as O   # noqa: E402
from app.services import prospects as P, whatsapp as WA                                        # noqa: E402

from app.services.storage import init_db                             # noqa: E402

asyncio.run(init_db())                  # les tables du Scheduler, sans le lifespan (aucun réseau)
P._aujourdhui = lambda: date(2026, 10, 27)
c = TestClient(app)
lan = TestClient(app, client=("192.168.1.20", 50000))
EN = {"Accept-Language": "en"}
A = E.creer({"nom": "Prospection"})["id"]
SRC = {"type": "web", "url": "https://exemple.fr/contact", "date": "2026-10-20"}


def prospect(nom, canaux, entreprise="", eid=None):
    return P.creer(eid or A, {"nom": nom, "entreprise": entreprise, "source": SRC, "base_legale": "consentement",
                              "canaux": canaux})


def jusqua(pid, *statuts, eid=None):
    r = None
    for s in statuts:
        r = P.changer_statut(eid or A, pid, s)
    return r


def demos_vivantes():
    return [k for k, e in E.lire()["espaces"].items() if e.get("type") == "demonstration" and not e.get("archive")]


print("[M1] un post d'espace démonstration ne se programme pas par PATCH")
lune = prospect("Léa", [{"type": "email", "valeur": "lea@studio-lune.fr"}], entreprise="Studio Lune")
demo = jusqua(lune["id"], "qualifie", "contacte", "repondu", "rdv")["prospect"]["espace_demo"]
r = c.post("/api/schedule", json={"title": "Témoin", "caption": "c", "run_at": "2026-11-02T10:00:00",
                                  "status": "draft", "espace_id": demo, "channels": ["x"]})
post = r.json()["id"]
r = c.patch(f"/api/schedule/{post}", json={"status": "scheduled"})
d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
check("M1a PATCH scheduled : 409 demonstration", r.status_code == 409 and isinstance(d, dict)
      and d.get("code") == "demonstration", r.text[:300])
check("M1b le post reste brouillon", c.get("/api/schedule?espace=*").json()
      and [p for p in c.get("/api/schedule?espace=*").json() if p["id"] == post][0]["status"] == "draft")
r = c.patch(f"/api/schedule/{post}", json={"caption": "autre"})
check("M1c un PATCH de contenu reste permis", r.status_code == 200, r.text[:200])
M = E.creer({"nom": "Marque M"})["id"]
r = c.post("/api/schedule", json={"title": "M", "caption": "c", "run_at": "2026-11-02T10:00:00", "status": "draft",
                                  "espace_id": M, "channels": ["x"]})
check("M1d espace marque : PATCH scheduled permis", c.patch(f"/api/schedule/{r.json()['id']}",
                                                               json={"status": "scheduled"}).status_code == 200)

print("[M2] un paquet d'espace démonstration s'importe comme marque")
data, _nom = PQ.exporter(demo)
try:
    res = PQ.importer(data); err = None
except Exception as e:  # noqa: BLE001
    res, err = None, e
check("M2a import accepté", res is not None, repr(err))
if res:
    check("M2b type marque", res["espace"]["type"] == "marque", str(res["espace"]))
    check("M2c l'import le dit", any("démonstration" in x for x in res["ignores"]), str(res["ignores"]))

print("[M4] une écriture en échec défait le geste sur la démo")
mx = prospect("Max", [{"type": "email", "valeur": "max@maison-x.fr"}], entreprise="Maison X")
jusqua(mx["id"], "qualifie", "contacte", "repondu")
avant = set(demos_vivantes())
_poser = P._poser


def poser_casse(eid, fiches):
    raise OSError(28, "disque plein")


P._poser = poser_casse
try:
    P.changer_statut(A, mx["id"], "rdv"); leve = False
except OSError:
    leve = True
P._poser = _poser
check("M4a l'échec remonte", leve)
check("M4b aucune démo vivante de plus", set(demos_vivantes()) == avant, str(set(demos_vivantes()) - avant))
r = P.changer_statut(A, mx["id"], "rdv")
check("M4c le nouvel essai crée UNE démo", len(set(demos_vivantes()) - avant) == 1 and r["prospect"]["espace_demo"]
      in demos_vivantes())
d_mx = r["prospect"]["espace_demo"]
P._poser = poser_casse
try:
    P.changer_statut(A, mx["id"], "perdu")
except OSError:
    pass
P._poser = _poser
check("M4d perdu en échec : la démo reste ouverte", not E.lire()["espaces"][d_mx]["archive"])
_ins = O.inscrire


def inscrire_casse(*a, **k):
    raise O.RegistreIndisponible("registre des oppositions momentanément illisible : réessayez dans un instant")


O.inscrire = inscrire_casse
try:
    P.opposer(A, mx["id"]); code = None
except P.RefusProspect as e:
    code = e.code
O.inscrire = _ins
check("M4e opposition, registre indisponible : 503, la démo n'est ni renommée ni archivée", code == "indisponible"
      and E.lire()["espaces"][d_mx]["nom"] == "Démo · Maison X" and not E.lire()["espaces"][d_mx]["archive"], str(code))

print("[M5] statut absent ou inconnu : 422 champ")
r = c.post(f"/api/prospects/{A}/{mx['id']}/statut", json={})
check("M5a statut absent : 422 champ", r.status_code == 422 and r.json()["detail"]["code"] == "champ", r.text[:200])
r = c.post(f"/api/prospects/{A}/{mx['id']}/statut", json={"statut": "gagne"}, headers=EN)
check("M5b statut inconnu : 422 champ, en anglais", r.status_code == 422 and r.json()["detail"]["code"] == "champ"
      and "status" in r.json()["detail"]["message"].lower(), r.text[:200])
r = c.post(f"/api/prospects/{A}/{mx['id']}/statut", json={"statut": "propose"})
check("M5c statut connu mais impossible : toujours 409 transition", r.status_code == 409
      and r.json()["detail"]["code"] == "transition")

print("[M6] registre : STOP en doute, réabonnement, retrait journalisé")
cm = CP.creer({"espace_id": M, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cm, {"WHATSAPP_PHONE_ID": "111"})
fe = E.dossier() / "espaces.json"
sauve = fe.read_bytes()
from app.services import regles_client as RC                          # noqa: E402
_brut = RC._brut_espaces


def brut_casse():
    raise RC._Illisible("espaces.json")


RC._brut_espaces = brut_casse
WA.noter_stop(cm, "tel:33655556666")
RC._brut_espaces = _brut
check("M6a espaces.json illisible : le STOP va au registre (refus par défaut)", O.oppose(["tel:33655556666"]))
WA.noter_stop(cm, "tel:33677778888")
check("M6b (témoin) STOP inscrit", O.oppose(["tel:33677778888"]))
WA.lever_stop(cm, "tel:33677778888", "écrit du 28/10")
check("M6c réabonnement : retiré du registre", not O.oppose(["tel:33677778888"]))
O.inscrire(["erreur@exemple.fr"], "saisie")
r = c.post("/api/prospects/oppositions/retirer", json={"identifiant": "ERREUR@exemple.fr"})
check("M6d saisie erronée : retirée", r.status_code == 200 and r.json() == {"retire": True}
      and not O.oppose(["erreur@exemple.fr"]), r.text[:200])
doc = json.loads((E.dossier() / "oppositions.json").read_text(encoding="utf-8"))
j = doc.get("journal") or []
check("M6e retrait journalisé, sans identifiant en clair", j and j[-1].get("geste") == "retrait"
      and j[-1].get("origine") == "saisie" and "erreur" not in json.dumps(doc), str(j)[-200:])
op = prospect("Olga", [{"type": "email", "valeur": "olga@agence-o.fr"}], entreprise="Agence O")
P.opposer(A, op["id"])
r = c.post("/api/prospects/oppositions/retirer", json={"identifiant": "olga@agence-o.fr"})
check("M6f opposition de la personne : refusée (409), toujours au registre", r.status_code == 409
      and O.oppose(["olga@agence-o.fr"]), r.text[:200])
r = c.post("/api/prospects/oppositions/retirer", json={"identifiant": "personne@exemple.fr"})
check("M6g identifiant absent : retire false", r.status_code == 200 and r.json() == {"retire": False}, r.text[:200])
r = lan.post("/api/prospects/oppositions/retirer", json={"identifiant": "x@exemple.fr"})
check("M6h local seulement", r.status_code in (401, 403), str(r.status_code))

print("[M7] pseudos de réseaux au registre et aux doublons")
check("M7a @pseudo X = x.com/pseudo = twitter.com/pseudo",
      O.normaliser_canal("x", "@Lune_Studio") == O.normaliser_canal("x", "https://twitter.com/lune_studio/")
      == O.normaliser_canal("x", "x.com/Lune_Studio") == "profil:https://x.com/lune_studio",
      str([O.normaliser_canal("x", "@Lune_Studio"), O.normaliser_canal("x", "https://twitter.com/lune_studio/")]))
check("M7b Instagram et LinkedIn", O.normaliser_canal("instagram", "@studio.lune") == "profil:https://instagram.com/studio.lune"
      and O.normaliser_canal("linkedin", "www.linkedin.com/in/lea-martin") == "profil:https://linkedin.com/in/lea-martin"
      == O.normaliser_canal("linkedin", "https://www.linkedin.com/in/Lea-Martin/"),
      str([O.normaliser_canal("instagram", "@studio.lune"), O.normaliser_canal("linkedin", "www.linkedin.com/in/lea-martin")]))
check("M7c saisie manuelle x:@pseudo", O.normaliser("x:@Lune_Studio") == "profil:https://x.com/lune_studio")
ps = prospect("Pseudo", [{"type": "x", "valeur": "@Pseudo_Seul"}])
P.opposer(A, ps["id"])
B = E.creer({"nom": "Prospection B"})["id"]
try:
    prospect("Pseudo", [{"type": "x", "valeur": "https://x.com/pseudo_seul"}], eid=B); code = None
except P.RefusProspect as e:
    code = e.code
check("M7d opposé par pseudo : refusé ailleurs sous une autre forme", code == "opposition", str(code))
prospect("Ig", [{"type": "instagram", "valeur": "@ig.seul"}], eid=B)
try:
    prospect("Ig bis", [{"type": "instagram", "valeur": "instagram.com/ig.seul"}], eid=B); code = None
except P.RefusProspect as e:
    code = e.code
check("M7e doublon reconnu sous une autre forme", code == "doublon", str(code))

print("[M9] renommer l'entreprise après le rdv renomme la démo")
zo = prospect("Zoé", [{"type": "email", "valeur": "zoe@agence-z.fr"}], entreprise="Agence Z")
dz = jusqua(zo["id"], "qualifie", "contacte", "repondu", "rdv")["prospect"]["espace_demo"]
P.modifier(A, zo["id"], {"entreprise": "Agence Zèbre"})
persona = json.loads(E.chemin(dz, "persona.json").read_text(encoding="utf-8"))
check("M9a espaces.json et persona renommés", E.lire()["espaces"][dz]["nom"] == "Démo · Agence Zèbre"
      and persona["display_name"] == "Démo · Agence Zèbre", E.lire()["espaces"][dz]["nom"])
P.modifier(A, zo["id"], {"role": "directrice"})
check("M9b une autre modification ne touche pas la démo", E.lire()["espaces"][dz]["nom"] == "Démo · Agence Zèbre")
P.modifier(A, zo["id"], {"entreprise": ""})
check("M9c entreprise effacée : la démo prend l'id, jamais le nom", E.lire()["espaces"][dz]["nom"] == f"Démo · {zo['id']}")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
