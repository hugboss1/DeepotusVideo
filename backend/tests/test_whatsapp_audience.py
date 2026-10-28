# -*- coding: utf-8 -*-
"""t328 tâche 2 (27/10/2026) — audience d'une diffusion, devis par quantité, plafond de messages.
Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (Décisions 1, 3, 4). Aucun réseau. Ce que ce banc garde :
  A1  `audience_diffusion` marketing : accord `entrant` écarté, stop écarté, désinscrit écarté, bsuid écarté et compté
  A2  `audience_diffusion` utility : revue finale M8 (Décision 1) — un accord `entrant` est ÉCARTÉ comme en marketing
      (un message entrant n'est pas un accord de diffusion) ; désinscrit marketing retenu, stop écarté
  A3  liste explicite : filtrée par les mêmes règles ; alias tel/bsuid ; identité mal formée refusée
  A4  refus : consentement client absent (`consentement`), audience vide (`accord`) ; même verdict que `controler`
  A5  fichier d'état et fiche client lus UNE fois pour toute la liste
  P1  `verifier_plafond_mois` : 990 déjà + 20 > 1000 -> `plafond` ; 990 + 10 passe ; n invalide -> ValueError
  Q1  devis : n=3 = 3 x prix, libellé dit la quantité ; n=1 inchangé ; marché inconnu -> ValueError ; n invalide
  Q2  service : part gratuite du mois par message (seuil 5, déjà 3, n=4 -> 2 gratuits, 2 facturés)
  M1  `modeles(cid)` porte `meta_id` (l'id brut de Meta, "" s'il manque)
Run (depuis backend/) : & $PY tests/test_whatsapp_audience.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwaud_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["KAPSO_API_KEY"] = ""
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
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from datetime import datetime, timezone                              # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import comptes as CP, espaces as E, fiche_client as FC, kapso as KA, pricing as PR  # noqa: E402
from app.services import whatsapp as WA, whatsapp_echanges as WE     # noqa: E402


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except WA.WhatsappRefus as e:
        return e.code
    return None


def leve(fn, exc, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    return False


GRILLE = {"33": {"marketing": 0.0859, "utility": 0.03, "authentication": 0.03, "service": 0.01}}
E.lire()
PR.save({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0})

boite = E.creer({"nom": "Atelier Soleil"})["id"]
cid = CP.creer({"espace_id": boite, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": "PN-1", "WHATSAPP_WABA_ID": "WABA-1"})

SAISI, ENTRANT, STOPPE, DESINSCRIT, MIXTE = ("tel:33600000001", "tel:33600000002", "tel:33600000003", "tel:33600000004",
                                             "tel:33600000005")
WA.noter_accord(cid, SAISI, "formulaire")
WA.noter_accord(cid, ENTRANT, "entrant")
WA.noter_accord(cid, STOPPE, "formulaire"); WA.noter_stop(cid, STOPPE)
WA.noter_accord(cid, DESINSCRIT, "formulaire"); WA.noter_desinscription(cid, DESINSCRIT)
WA.noter_accord(cid, "bsuid:FR.ABC123", "entrant")

print("\n[A1] marketing")
a = WA.audience_diffusion(cid, categorie="marketing")
check("A1.1 seul l'accord saisi, ni stop ni désinscrit ni entrant", a["retenus"] == [SAISI], a)
check("A1.2 écartés comptés", a["ecartes"] == {"bsuid": 1, "stop": 1, "accord": 1, "marketing": 1}, a)
check("A1.3 la casse de la catégorie ne compte pas", WA.audience_diffusion(cid, categorie="MARKETING") == a)

print("\n[A2] utility")
a = WA.audience_diffusion(cid, categorie="utility")
check("A2.1 M8 : accord saisi et désinscrit marketing retenus ; entrant écarté, stop écarté",
      sorted(a["retenus"]) == sorted([SAISI, DESINSCRIT]), a)
check("A2.2 écartés : stop, bsuid et l'accord né d'un entrant", a["ecartes"] == {"bsuid": 1, "stop": 1, "accord": 1, "marketing": 0}, a)
check("A2.3 M8 : utility avec que des entrants -> accord", refus(WA.audience_diffusion, cid, categorie="utility",
                                                                 identites=[ENTRANT]) == "accord")
check("A2.4 M8 : authentication aussi", refus(WA.audience_diffusion, cid, categorie="authentication",
                                              identites=[ENTRANT]) == "accord")

print("\n[A3] liste explicite")
a = WA.audience_diffusion(cid, categorie="marketing",
                          identites=[SAISI, ENTRANT, STOPPE, "tel:33699999999", "bsuid:FR.ABC123", SAISI])
check("A3.1 filtrée, doublon compté une fois", a["retenus"] == [SAISI]
      and a["ecartes"] == {"bsuid": 1, "stop": 1, "accord": 2, "marketing": 0}, a)
check("A3.2 identité mal formée -> ValueError", leve(WA.audience_diffusion, ValueError, cid, categorie="utility", identites=["33612"]))
WA.noter_accord(cid, MIXTE, "formulaire")
WA._noter(cid, lambda e: (e["alias"].__setitem__(MIXTE, "bsuid:FR.MIXTE"), e["alias"].__setitem__("bsuid:FR.MIXTE", MIXTE),
                          e["accords"].__setitem__("bsuid:FR.MIXTE", {"date": "x", "source": "entrant"})))
a = WA.audience_diffusion(cid, categorie="marketing")
check("A3.3 un BSUID relié à un numéro n'est ni compté ni doublé", a["retenus"] == [SAISI, MIXTE] and a["ecartes"]["bsuid"] == 1, a)

print("\n[A4] refus")
WA.noter_accord(cid, "bsuid:FR.SEUL", "formulaire")
WA._noter(cid, lambda e: (e["alias"].__setitem__("bsuid:FR.SEUL", "tel:33600000009"),
                          e["alias"].__setitem__("tel:33600000009", "bsuid:FR.SEUL")))
a = WA.audience_diffusion(cid, categorie="marketing", identites=["bsuid:FR.SEUL", "tel:33600000009", "bsuid:FR.SEUL"])
check("A3.4 accord sur le seul BSUID relié : retenu une fois, sous son numéro", a["retenus"] == ["tel:33600000009"]
      and a["ecartes"]["bsuid"] == 0, a)
a = WA.audience_diffusion(cid, categorie="marketing", identites=["bsuid:FR.SEUL"])
check("A3.5 BSUID relié seul en liste : substitué par le numéro", a["retenus"] == ["tel:33600000009"], a)
check("A3.6 BSUID non relié : reste écarté et compté", WA.audience_diffusion(cid, categorie="marketing",
      identites=[SAISI, "bsuid:FR.ABC123"])["ecartes"]["bsuid"] == 1)
check("A4.1 aucune identité à accord -> accord", refus(WA.audience_diffusion, cid, categorie="utility", identites=[STOPPE]) == "accord")
check("A4.2 marketing : que des entrants -> accord", refus(WA.audience_diffusion, cid, categorie="marketing", identites=[ENTRANT]) == "accord")
lune = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
cl = CP.creer({"espace_id": lune, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cl, {"WHATSAPP_PHONE_ID": "PN-CL", "WHATSAPP_WABA_ID": "WABA-CL"})
WA.noter_accord(cl, SAISI, "formulaire")
check("A4.3 client sans consentement en cours -> consentement", refus(WA.audience_diffusion, cl, categorie="utility") == "consentement")
check("A4.4 … comme `controler`", refus(WA.controler, cl, SAISI, type="modele", categorie="UTILITY", dernier_entrant=None,
                                       maintenant=datetime.now(timezone.utc)) == "consentement")
FC.ajouter_consentement(lune, "whatsapp:PN-CL", ["messages"], "ecrit")
check("A4.5 consentement posé -> retenu", WA.audience_diffusion(cl, categorie="utility")["retenus"] == [SAISI])

print("\n[A5] une seule lecture")
lectures = {"doc": 0, "fiche": 0}
_ld, _ce = WA._lire_doc, FC.consentement_en_cours
WA._lire_doc = lambda eid: (lectures.__setitem__("doc", lectures["doc"] + 1), _ld(eid))[1]
FC.consentement_en_cours = lambda *a, **k: (lectures.__setitem__("fiche", lectures["fiche"] + 1), _ce(*a, **k))[1]
try:
    WA.audience_diffusion(cl, categorie="marketing", identites=[SAISI] * 3 + [ENTRANT, STOPPE])
finally:
    WA._lire_doc, FC.consentement_en_cours = _ld, _ce
check("A5.1 fichier d'état lu une fois, fiche client lue une fois", lectures == {"doc": 1, "fiche": 1}, lectures)

print("\n[P1] plafond de messages")
mois = WA._mois(datetime.now(timezone.utc))
WA._noter(cid, lambda e: e["compteur"].__setitem__(mois, {"sortants": 700, "entrants": 290}))
check("P1.1 990 déjà + 20 > 1000 -> plafond", refus(WA.verifier_plafond_mois, cid, 20) == "plafond")
check("P1.2 990 + 10 = 1000 passe", refus(WA.verifier_plafond_mois, cid, 10) is None)
check("P1.2b horloge injectable : mois suivant, compteur vide", refus(WA.verifier_plafond_mois, cid, 20,
      maintenant=datetime(2099, 1, 15, tzinfo=timezone.utc)) is None)
check("P1.3 n invalide -> ValueError", all(leve(WA.verifier_plafond_mois, ValueError, cid, n) for n in (0, -1, True, 2.5, "3")))

print("\n[Q1] devis par quantité")
p = PR.load()
un = PR._ligne_whatsapp({"kind": "whatsapp", "categorie": "marketing", "marche": "33"}, p)
check("Q1.1 n absent = n=1 : forme inchangée", un == {"provider": "meta", "label": "WhatsApp marketing (33)", "units": 1,
                                                       "unit": "msg", "usd": 0.0859}, un)
trois = PR._ligne_whatsapp({"kind": "whatsapp", "categorie": "marketing", "marche": "33", "n": 3}, p)
check("Q1.2 n=3 = 3 x prix, unités 3", trois["usd"] == round(3 * 0.0859, 4) and trois["units"] == 3, trois)
check("Q1.3 le libellé dit la quantité", "3" in trois["label"] and trois["label"].startswith("WhatsApp marketing (33)"), trois)
check("Q1.4 n=1 explicite = n absent",
      PR._ligne_whatsapp({"kind": "whatsapp", "categorie": "marketing", "marche": "33", "n": 1}, p) == un)
check("Q1.5 marché inconnu -> ValueError existante", leve(PR._ligne_whatsapp, ValueError,
                                                          {"kind": "whatsapp", "categorie": "marketing", "marche": "999", "n": 3}, p))
check("Q1.6 n invalide -> ValueError", all(leve(PR._ligne_whatsapp, ValueError,
                                               {"kind": "whatsapp", "categorie": "marketing", "marche": "33", "n": n}, p)
                                          for n in (0, -2, True, 1.5, "2")))
dev = PR.estimate({"kind": "whatsapp", "categorie": "utility", "marche": "33", "n": 4})
check("Q1.7 `estimate` suit : 4 x 0,03", dev["total_usd"] == 0.12, dev)

print("\n[Q2] service : gratuits par message")
p5 = {**p, "whatsapp_service_gratuits_mois": 5}
op = {"kind": "whatsapp", "categorie": "service", "marche": "33"}
check("Q2.1 n=4, déjà 3 : 2 gratuits, 2 facturés", PR._ligne_whatsapp({**op, "n": 4, "service_deja_mois": 3}, p5)["usd"] == 0.02)
check("Q2.1b libellé : × 4 dont 2 gratuits", PR._ligne_whatsapp({**op, "n": 4, "service_deja_mois": 3}, p5)["label"]
      == "WhatsApp service (33) × 4 dont 2 gratuits")
check("Q2.2 n=2, déjà 3 : tout gratuit", PR._ligne_whatsapp({**op, "n": 2, "service_deja_mois": 3}, p5)["usd"] == 0.0)
check("Q2.3 déjà 5 : tout facturé", PR._ligne_whatsapp({**op, "n": 3, "service_deja_mois": 5}, p5)["usd"] == 0.03)
check("Q2.4 n=1 déjà 4 : gratuit, libellé d'origine", PR._ligne_whatsapp({**op, "service_deja_mois": 4}, p5)
      == {"provider": "meta", "label": "WhatsApp service (33) — dans les 5 gratuits", "units": 1, "unit": "msg", "usd": 0.0})

print("\n[M1] meta_id")
plat = WE._modele_plat({"id": 1234567890, "name": "promo", "language": "fr", "category": "MARKETING", "status": "APPROVED",
                        "components": []})
check("M1.1 `_modele_plat` : meta_id en chaîne", plat.get("meta_id") == "1234567890", plat)
check("M1.2 absent -> chaîne vide", WE._modele_plat({"name": "x", "language": "fr"}).get("meta_id") == "")


async def faux_requete(methode, url, *, json=None, params=None, fichiers=None):
    if "message_templates" in url:
        return 200, {"data": [{"id": "999", "name": "promo", "language": "fr", "category": "MARKETING", "status": "APPROVED",
                               "components": []}], "paging": {}}, {}
    return 500, {}, {}


KA._requete = faux_requete
os.environ["KAPSO_API_KEY"] = "CLE-BANC"
setattr(settings, "KAPSO_API_KEY", "CLE-BANC")
mods = asyncio.run(WE.modeles(cid))
check("M1.3 `modeles(cid)` porte meta_id", bool(mods) and mods[0].get("meta_id") == "999", mods)

print(f"\n{ok} OK, {fail} KO")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
