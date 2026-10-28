# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2, relecture finale : les cinq défauts relevés, gardés.
I1 : le nom de la personne ne survit pas dans l'espace démonstration (nom par l'entreprise ou l'id, renommé à
     l'opposition, à l'effacement et à la purge) ; un espace démonstration archivé ne compte plus dans le plafond.
I2 : une erreur de lecture passagère n'écrase ni le registre des oppositions ni la fiche Prospects (refus 503) ; un
     registre mis de côté est signalé à l'écran.
I3 : une opposition inscrite (ailleurs, ou par STOP) anonymise aussi les fiches DÉJÀ enregistrées des autres espaces.
I4 : les routes /api/prospects tournent sur la boucle (async) et la purge aussi : espaces.json n'a qu'un écrivain.
M3 : la fiche d'un espace archivé reste exportable, effaçable et opposable (droits RGPD).
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_relecture.py"""
import asyncio, inspect, json, os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzprl_"))
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
    except Exception as e:  # noqa: BLE001
        return ("autre", type(e).__name__)
    return None


from app.services import espaces as E, oppositions as O, prospects as P   # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 27)
E.lire()
A = E.creer({"nom": "Prospection A"})["id"]
B = E.creer({"nom": "Prospection B"})["id"]
SRC = {"type": "web", "url": "https://exemple.fr/contact", "date": "2026-10-20"}


def prospect(eid, nom, email, entreprise=""):
    return P.creer(eid, {"nom": nom, "entreprise": entreprise, "source": SRC, "base_legale": "consentement",
                         "canaux": [{"type": "email", "valeur": email}]})


def jusqua(eid, pid, *statuts):
    r = None
    for s in statuts:
        r = P.changer_statut(eid, pid, s)
    return r


def octets_espace(eid):
    return (E.dossier() / "espaces.json").read_bytes() + (E.dossier() / eid / "persona.json").read_bytes()


print("[I1] le nom de la personne ne survit pas dans l'espace démonstration")
jd = prospect(A, "Jean Dupont", "jean.dupont@exemple.fr")
demo = jusqua(A, jd["id"], "qualifie", "contacte", "repondu", "rdv")["prospect"]["espace_demo"]
check("I1a sans entreprise : l'espace porte l'id, pas le nom", E.lire()["espaces"][demo]["nom"] == f"Démo · {jd['id']}"
      and "Dupont".encode() not in octets_espace(demo), E.lire()["espaces"][demo]["nom"])
lune = prospect(A, "Léa Martin", "lea@studio-lune.fr", entreprise="Studio Lune")
d2 = jusqua(A, lune["id"], "qualifie", "contacte", "repondu", "rdv")["prospect"]["espace_demo"]
check("I1b avec entreprise : le nom de l'entreprise", E.lire()["espaces"][d2]["nom"] == "Démo · Studio Lune")
P.opposer(A, lune["id"])
check("I1c opposition : l'espace démo est renommé (espaces.json et persona)", "Studio Lune".encode() not in octets_espace(d2)
      and E.lire()["espaces"][d2]["nom"] == f"Démo · {lune['id']}" and E.lire()["espaces"][d2]["archive"])
mx = prospect(A, "Max", "max@maison-x.fr", entreprise="Maison X")
d3 = jusqua(A, mx["id"], "qualifie", "contacte", "repondu", "rdv")["prospect"]["espace_demo"]
P.effacer(A, mx["id"])
check("I1d effacement : l'espace démo renommé et archivé", "Maison X".encode() not in octets_espace(d3)
      and E.lire()["espaces"][d3]["archive"])
vx = P.creer(A, {"nom": "Vieux", "entreprise": "Vieille Maison", "source": dict(SRC, date="2023-10-01"), "base_legale": "consentement",
                 "canaux": [{"type": "email", "valeur": "vieux@vieille-maison.fr"}]})
d4 = jusqua(A, vx["id"], "qualifie", "contacte", "repondu")["prospect"]
# la fiche date son dernier contact entrant au 27/10/2026 : on la vieillit à la main pour la purge
f = E.chemin(A, "prospects.json"); doc = json.loads(f.read_text(encoding="utf-8"))
for p in doc["prospects"]:
    if p["id"] == vx["id"]:
        p["purge_le"] = "2026-10-01"
f.write_text(json.dumps(doc), encoding="utf-8")
E.archiver(d2, True)
d4 = E.creer_demonstration("Démo · Vieille Maison", "#123456", {"espace": A, "prospect": vx["id"]})["id"]
doc = json.loads(f.read_text(encoding="utf-8"))
for p in doc["prospects"]:
    if p["id"] == vx["id"]:
        p["espace_demo"] = d4
f.write_text(json.dumps(doc), encoding="utf-8")
asyncio.run(P.purger_tout(date(2026, 10, 27)))
check("I1e purge : l'espace démo renommé et archivé", "Vieille Maison".encode() not in octets_espace(d4)
      and E.lire()["espaces"][d4]["archive"])
_max = E.MAX_ESPACES
E.MAX_ESPACES = len([e for e in E.lire()["espaces"].values() if not (e.get("archive") and e.get("type") == "demonstration")])
zo = prospect(A, "Zoé", "zoe@agence-z.fr", entreprise="Agence Z")
r = jusqua(A, zo["id"], "qualifie", "contacte", "repondu", "rdv")
E.MAX_ESPACES = _max
check("I1f les démos archivées ne comptent pas dans le plafond", r["note"] == "plafond_espaces")
E.MAX_ESPACES = len([e for e in E.lire()["espaces"].values() if not (e.get("archive") and e.get("type") == "demonstration")]) + 1
r = P.changer_statut(A, zo["id"], "perdu"); r = jusqua(A, zo["id"], "qualifie", "contacte", "repondu", "rdv")
E.MAX_ESPACES = _max
check("I1g …et une place libre suffit", r["note"] is None and r["prospect"]["espace_demo"], str(r["note"]))

print("[I2] une erreur de lecture n'écrase rien")
O.inscrire(["garde@exemple.fr"], "saisie")
reg = E.dossier() / "oppositions.json"
avant = reg.read_bytes()
_rb = pathlib.Path.read_bytes


def verrouille(self):
    if self.name in ("oppositions.json", "prospects.json"):
        raise PermissionError(32, "fichier verrouillé")
    return _rb(self)


pathlib.Path.read_bytes = verrouille
try:
    try:
        O.inscrire(["autre@exemple.fr"], "saisie"); leve = False
    except O.RegistreIndisponible:
        leve = True
    check("I2a inscrire : refus, rien d'écrit", leve and _rb(reg) == avant)
    check("I2b créer un prospect : refus 503", refus(prospect, B, "Nina", "nina@exemple.fr") == ("indisponible", 503),
          str(refus(prospect, B, "Nina", "nina@exemple.fr")))
    fp = E.chemin(A, "prospects.json"); pa = _rb(fp)
    check("I2c fiche verrouillée : lister refuse 503, rien d'écrit", refus(P.lister, A) == ("indisponible", 503) and _rb(fp) == pa)
finally:
    pathlib.Path.read_bytes = _rb
reg.write_bytes(b"{casse")
n_apres = O.compte()                                                 # la lecture met le registre illisible de côté
check("I2d registre mis de côté : signalé", n_apres == 0 and O.mis_de_cote() == 1, f"{n_apres} {O.mis_de_cote()}")

print("[I3] une opposition touche les fiches déjà enregistrées ailleurs")
kb = prospect(B, "Karim", "karim@agence-k.fr", entreprise="Agence K")
O.inscrire(["KARIM@agence-k.fr"], "whatsapp")
lb = {p["id"]: p for p in P.lister(B)}
check("I3a dans B, la fiche est anonymisée à la lecture", lb[kb["id"]]["statut"] == "oppose" and lb[kb["id"]]["nom"] == ""
      and b"Karim" not in E.chemin(B, "prospects.json").read_bytes())

print("[I4] un seul écrivain d'espaces.json : la boucle")
from app.api import prospects_routes as R                           # noqa: E402
fonctions = [r.endpoint for r in R.router.routes]
check("I4a toutes les routes /api/prospects sont async", fonctions and all(inspect.iscoroutinefunction(f) for f in fonctions),
      [f.__name__ for f in fonctions if not inspect.iscoroutinefunction(f)])
check("I4b la boucle de purge ne passe pas par un thread", "to_thread" not in inspect.getsource(P.purge_loop)
      and inspect.iscoroutinefunction(P.purger_tout))

print("[M3] espace archivé : export, opposition et effacement restent possibles")
C = E.creer({"nom": "Prospection C"})["id"]
pc = prospect(C, "Paula", "paula@agence-p.fr", entreprise="Agence P")
pd = prospect(C, "Pierre", "pierre@agence-p2.fr", entreprise="Agence P2")
E.archiver(C, True)
check("M3a export", P.exporter(C, pc["id"])["nom"] == "Paula")
check("M3b opposition", P.opposer(C, pc["id"])["statut"] == "oppose")
P.effacer(C, pd["id"])
check("M3c effacement", O.oppose(["pierre@agence-p2.fr"]))
check("M3d mais pas de création", refus(prospect, C, "Neuf", "neuf@agence-n.fr") == ("inconnu", 404))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
