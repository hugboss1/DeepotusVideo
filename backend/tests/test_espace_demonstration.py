# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : le type d'espace `demonstration` (spec §9.2). Ce que ce banc garde :
créé AUTOMATIQUEMENT quand un prospect passe à `rdv` (jamais à la main), réutilisé s'il existe, archivé si le prospect est
`perdu` (sauf s'il est l'espace actif : note), converti en espace CLIENT à la signature, sans aucun consentement, la
campagne témoin (posts brouillons) gardée ; il ne PUBLIE JAMAIS (aucun compte, aucun lien WhatsApp, aucun post programmé
ni parti) ; le STOP WhatsApp va au registre global hors espaces clients. Data-dir isolé, aucun réseau.
Run (depuis backend/) : & $PY tests/test_espace_demonstration.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import date, datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdemo_"))
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


def leve(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


from app.services import comptes as CP, espaces as E, fiche_client as FC, oppositions as O   # noqa: E402
from app.services import prospects as P, regles_client as RC, whatsapp as WA                 # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 27)
E.lire()
A = E.creer({"nom": "Deepotus prospection", "couleur": "#123456"})["id"]
SRC = {"type": "web", "url": "https://studio-lune.fr/contact", "date": "2026-10-20"}


def prospect(nom, email, entreprise="Studio Lune"):
    return P.creer(A, {"nom": nom, "entreprise": entreprise, "source": SRC, "base_legale": "interet_legitime_b2b",
                       "canaux": [{"type": "email", "valeur": email}]})


def jusqua(pid, *statuts):
    r = None
    for s in statuts:
        r = P.changer_statut(A, pid, s)
    return r


print("[1] rdv : l'espace démonstration naît")
lea = prospect("Léa Martin", "lea@studio-lune.fr")
r = jusqua(lea["id"], "qualifie", "contacte", "repondu", "rdv")
demo = r["prospect"]["espace_demo"]
vues = {v["id"]: v for v in E.lister(archives=True)}
check("1a espace créé, type demonstration", demo in vues and vues[demo]["type"] == "demonstration", str(vues.get(demo)))
check("1b nom et couleur", vues[demo]["nom"] == "Démo · Studio Lune" and vues[demo]["couleur"] == "#123456")
check("1c origine rangée", E.lire()["espaces"][demo].get("origine") == {"espace": A, "prospect": lea["id"]})
check("1d non actif", E.actif()["id"] != demo and r["note"] is None)
check("1e est_demonstration (normal et brut)", E.est_demonstration(demo) and E.est_demonstration(demo, brut=True)
      and not E.est_demonstration(A))

print("[2] jamais à la main")
check("2a creer(type=demonstration) refusé", leve(ValueError, E.creer, {"nom": "x", "type": "demonstration"}))
check("2b marque -> demonstration refusé", leve(ValueError, E.modifier, A, {"type": "demonstration"}))
check("2c demonstration -> marque refusé", leve(ValueError, E.modifier, demo, {"type": "marque"})
      and E.lire()["espaces"][demo]["type"] == "demonstration")
check("2d produit d'une démo refusé", leve(ValueError, E.creer, {"nom": "p", "type": "produit", "parent": demo}))
check("2e pas de prospects dans une démo", leve(P.RefusProspect, P.lister, demo))

print("[3] ne publie jamais")
check("3a aucun compte de diffusion", leve(ValueError, CP.creer, {"espace_id": demo, "plateforme": "x"})
      and not CP.lister(demo))
post = {"espace_id": demo, "comptes": []}
try:
    RC.controler(post); code = None
except RC.RefusClient as e:
    code = e.code
check("3b programmer refusé, code demonstration", code == "demonstration", str(code))
try:
    RC.controler(post, brut=True); code = None
except RC.RefusClient as e:
    code = e.code
check("3c idem en lecture brute", code == "demonstration", str(code))
check("3d la boucle le saute", RC.en_pause(post) is True)
check("3e Deepotus n'est pas touché", RC.controler({"espace_id": "deepotus", "comptes": []}) is None)
# un compte d'un espace marque, puis l'espace devenu démonstration à la main dans le fichier : le lien est refusé
M = E.creer({"nom": "Marque M"})["id"]
cid = CP.creer({"espace_id": M, "plateforme": "whatsapp"})["id"]
f = E.dossier() / "espaces.json"
doc = json.loads(f.read_text(encoding="utf-8")); doc["espaces"][M]["type"] = "demonstration"
f.write_text(json.dumps(doc), encoding="utf-8")
appels = []
WA.kapso.creer_customer = lambda *a, **k: appels.append(a)
try:
    asyncio.run(WA.creer_lien(cid, "customer_managed", None, None)); lien = "cree"
except ValueError:
    lien = "refuse"
except Exception as e:  # noqa: BLE001
    lien = type(e).__name__
check("3f lien WhatsApp refusé, Kapso jamais appelé", lien == "refuse" and not appels, lien)
doc["espaces"][M]["type"] = "marque"; f.write_text(json.dumps(doc), encoding="utf-8")

print("[4] perdu : archivé ; rdv de nouveau : le même, désarchivé")
P.changer_statut(A, lea["id"], "perdu")
check("4a archivé", E.lire()["espaces"][demo]["archive"] is True)
r = jusqua(lea["id"], "qualifie", "contacte", "repondu", "rdv")
check("4b même espace, désarchivé", r["prospect"]["espace_demo"] == demo and not E.lire()["espaces"][demo]["archive"]
      and sum(1 for e in E.lire()["espaces"].values() if e.get("type") == "demonstration") == 1)
E.activer(demo)
r = P.changer_statut(A, lea["id"], "perdu")
check("4c actif : pas archivé, note demo_active", r["note"] == "demo_active" and not E.lire()["espaces"][demo]["archive"]
      and r["prospect"]["statut"] == "perdu")
E.activer("deepotus")
jusqua(lea["id"], "qualifie", "contacte", "repondu", "rdv")

print("[5] signature : devient client, campagne témoin gardée")


async def _poser_post():
    from app.services.storage import ScheduledPost, async_session_factory, init_db
    await init_db()
    async with async_session_factory() as s:
        s.add(ScheduledPost(id="post-temoin", title="Témoin", caption="c", run_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                            status="draft", espace_id=demo))
        await s.commit()


async def _lire_post():
    from sqlalchemy import select
    from app.services.storage import ScheduledPost, async_session_factory
    async with async_session_factory() as s:
        return (await s.execute(select(ScheduledPost).where(ScheduledPost.id == "post-temoin"))).scalar_one_or_none()


asyncio.run(_poser_post())
r = P.changer_statut(A, lea["id"], "client")
e = E.lire()["espaces"][demo]
fiche = FC.lire(demo)
check("5a type client, renommé", e["type"] == "client" and e["nom"] == "Studio Lune" and r["note"] is None, str(e))
check("5b fiche client : société, contact, 0 consentement", fiche["societe"] == "Studio Lune"
      and fiche["contact"]["nom"] == "Léa Martin" and fiche["contact"]["email"] == "lea@studio-lune.fr"
      and fiche["consentements"] == [] and fiche["mode_publication"] == "valide_par_client")
pt = asyncio.run(_lire_post())
check("5c le post témoin reste, brouillon", pt is not None and pt.espace_id == demo and pt.status == "draft")
check("5d plus une démo", not E.est_demonstration(demo))
P.changer_statut(A, lea["id"], "oppose")
check("5e un client qui s'oppose : son espace client n'est pas archivé", not E.lire()["espaces"][demo]["archive"])

print("[6] signature sans démo ; plafond d'espaces")
tom = prospect("Tom", "tom@agence-t.fr", entreprise="Agence T")
r = jusqua(tom["id"], "qualifie", "contacte", "repondu", "client")
nv = r["prospect"]["espace_demo"]
check("6a sans démo : un espace client neuf, note demo_absente", r["note"] == "demo_absente" and nv
      and E.lire()["espaces"][nv]["type"] == "client", str(r["note"]))
zoe = prospect("Zoé", "zoe@agence-z.fr", entreprise="Agence Z")
jusqua(zoe["id"], "qualifie", "contacte", "repondu")
_max = E.MAX_ESPACES
E.MAX_ESPACES = len(E.lire()["espaces"])
r = P.changer_statut(A, zoe["id"], "rdv")
E.MAX_ESPACES = _max
check("6b plafond : statut rdv quand même, note plafond_espaces", r["prospect"]["statut"] == "rdv"
      and r["prospect"]["espace_demo"] is None and r["note"] == "plafond_espaces", str(r["note"]))

print("[7] STOP WhatsApp et registre global")
cm = CP.creer({"espace_id": M, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cm, {"WHATSAPP_PHONE_ID": "111"})
WA.noter_stop(cm, "tel:33611112222")
check("7a espace marque : STOP inscrit au registre", O.oppose(["tel:33611112222"]))
cl = E.creer({"nom": "Client C", "type": "client"})["id"]
cc = CP.creer({"espace_id": cl, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cc, {"WHATSAPP_PHONE_ID": "222"})
WA.noter_stop(cc, "tel:33633334444")
check("7b espace client : pas au registre", not O.oppose(["tel:33633334444"]))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
