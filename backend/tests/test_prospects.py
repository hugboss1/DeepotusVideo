# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — Veille & prospection P2 : la FICHE PROSPECT d'un espace (`prospects.json`, CRM léger, RGPD).
Ce que ce banc garde (spec §3, §6) : `source` et `base_legale` obligatoires côté serveur ; l'intérêt légitime B2B refusé
sur une messagerie grand public ; le registre GLOBAL des oppositions bloque la création dans tout espace ; pas de doublon
dans un espace ; transitions de statut bornées, `oppose` terminal ; purge 3 ans après le dernier contact VENU DU PROSPECT ;
opposition = anonymisation immédiate ; export complet ; effacement qui inscrit au registre (sauf saisie erronée) ;
purge des fiches échues ; plafond ; fichier illisible mis de côté. Data-dir isolé, aucun réseau, aucune dépense.
Run (depuis backend/) : & $PY tests/test_prospects.py"""
import json, os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpro_"))
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


from app.services import espaces as E, oppositions as O, prospects as P   # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 27)


def refus(fn, *a, **k):
    """(code, statut) du RefusProspect levé, ou None."""
    try:
        fn(*a, **k)
    except P.RefusProspect as r:
        return (r.code, r.statut)
    return None


A = E.creer({"nom": "Agence A"})["id"]
B = E.creer({"nom": "Agence B"})["id"]
SRC = {"type": "web", "url": "https://studio-lune.fr/contact", "date": "2026-10-20", "detail": "page contact"}


def base(**k):
    d = {"nom": "Léa Martin", "entreprise": "Studio Lune", "role": "gérante", "source": dict(SRC),
         "base_legale": "interet_legitime_b2b", "offre": "prestation", "signal": "cherche des vidéos courtes",
         "canaux": [{"type": "email", "valeur": "lea@studio-lune.fr"}]}
    d.update(k)
    return d


print("[1] source et base légale obligatoires")
check("1a sans source", refus(P.creer, A, base(source=None)) == ("source", 422))
check("1b type de source inconnu", refus(P.creer, A, base(source=dict(SRC, type="achat"))) == ("source", 422))
check("1c web sans url", refus(P.creer, A, base(source=dict(SRC, url=""))) == ("source", 422))
check("1d url non http", refus(P.creer, A, base(source=dict(SRC, url="javascript:alert(1)"))) == ("source", 422))
check("1e date future", refus(P.creer, A, base(source=dict(SRC, date="2026-11-01"))) == ("source", 422))
check("1f date mal formée", refus(P.creer, A, base(source=dict(SRC, date="20/10/2026"))) == ("source", 422))
check("1g liste d'attente sans url passe",
      P.creer(A, base(nom="Inscrit", canaux=[{"type": "email", "valeur": "inscrit@agence-z.fr"}],
                      source={"type": "liste_attente", "date": "2026-10-21"}, base_legale="consentement"))["statut"] == "propose")
check("1h sans base légale", refus(P.creer, A, base(base_legale=None)) == ("base_legale", 422))
check("1i base légale inconnue", refus(P.creer, A, base(base_legale="interet")) == ("base_legale", 422))
check("1j ni nom ni entreprise", refus(P.creer, A, base(nom="", entreprise="")) == ("champ", 422))

print("[2] e-mail grand public et intérêt légitime")
check("2a gmail + interet_legitime_b2b refusé",
      refus(P.creer, A, base(canaux=[{"type": "email", "valeur": "lea.martin@gmail.com"}])) == ("email_perso", 409))
check("2b hotmail.fr aussi", refus(P.creer, A, base(canaux=[{"type": "email", "valeur": "x@hotmail.fr"}])) == ("email_perso", 409))
check("2c gmail + consentement passe",
      P.creer(A, base(nom="Perso", canaux=[{"type": "email", "valeur": "perso@gmail.com"}], base_legale="consentement"))["id"].startswith("pr_"))
lea = P.creer(A, base())
check("2d domaine pro + intérêt légitime passe", lea["statut"] == "propose" and lea["base_legale"] == "interet_legitime_b2b")
check("2e historique de création", lea["historique"][0]["quoi"] == "creation")

print("[3] doublons et registre global")
check("3a même e-mail dans le même espace = doublon",
      refus(P.creer, A, base(nom="Autre", canaux=[{"type": "email", "valeur": "LEA@studio-lune.fr "}])) == ("doublon", 409))
leaB = P.creer(B, base())
check("3b même personne dans un autre espace : permis", leaB["id"] != lea["id"])
O.inscrire(["paul@agence-m.fr"], "saisie")
check("3c opposé depuis le registre : refusé dans A",
      refus(P.creer, A, base(nom="Paul", canaux=[{"type": "email", "valeur": "Paul@agence-m.fr"}])) == ("opposition", 409))
check("3d et dans B", refus(P.creer, B, base(nom="Paul", canaux=[{"type": "email", "valeur": "paul@agence-m.fr"}])) == ("opposition", 409))
check("3e espace inconnu", refus(P.creer, "esp_inconnu", base()) == ("inconnu", 404))

print("[4] transitions")
f = P.creer(A, base(nom="Tom", canaux=[{"type": "telephone", "valeur": "06 11 22 33 44"}]))
ordre = ["qualifie", "contacte", "repondu", "rdv", "client"]
for s in ordre:
    f = P.changer_statut(A, f["id"], s)["prospect"]
check("4a chaîne propose→client", f["statut"] == "client")
g = P.creer(A, base(nom="Zoé", canaux=[{"type": "email", "valeur": "zoe@agence-k.fr"}]))
check("4b propose→contacte interdit", refus(P.changer_statut, A, g["id"], "contacte") == ("transition", 409))
check("4c propose→rdv interdit", refus(P.changer_statut, A, g["id"], "rdv") == ("transition", 409))
check("4d statut inconnu : un champ fautif (t353 suite, M5)", refus(P.changer_statut, A, g["id"], "gagne") == ("champ", 422))
g = P.changer_statut(A, g["id"], "perdu")["prospect"]
check("4e perdu → qualifie (réouverture)", P.changer_statut(A, g["id"], "qualifie")["prospect"]["statut"] == "qualifie")
paires_ok = all(t in P.STATUTS for v in P.TRANSITIONS.values() for t in v) and set(P.TRANSITIONS) == set(P.STATUTS)
check("4f table complète", paires_ok and P.TRANSITIONS["oppose"] == ())
check("4g modifier ne change pas le statut", refus(P.modifier, A, g["id"], {"statut": "client"}) == ("champ", 422))

print("[5] purge_le : dernier contact venu du prospect")
h = P.creer(A, base(nom="Hugo", canaux=[{"type": "email", "valeur": "hugo@agence-h.fr"}]))
check("5a depuis la collecte", h["purge_le"] == "2029-10-20", h["purge_le"])
h = P.noter_contact(A, h["id"], "sortant", "premier message")
check("5b un contact sortant ne prolonge rien", h["purge_le"] == "2029-10-20" and h["historique"][-1]["quoi"] == "contact_sortant")
h = P.noter_contact(A, h["id"], "entrant", "il répond")
check("5c un contact entrant repousse", h["purge_le"] == "2029-10-27" and h["dernier_contact_entrant"] == "2026-10-27")
check("5d 29 février → 28 février", P.purge_le({"dernier_contact_entrant": "2028-02-29"}) == "2031-02-28")
check("5e sens inconnu", refus(P.noter_contact, A, h["id"], "lateral", "") == ("champ", 422))

print("[6] consentements")
h = P.ajouter_consentement(A, h["id"], "email", "consentement", "formulaire")
check("6a ajouté et daté", h["consentements"][-1]["date"] == "2026-10-27" and h["consentements"][-1]["revoque_le"] is None)
check("6b un seul actif par canal", refus(P.ajouter_consentement, A, h["id"], "email", "consentement", "ecrit") == ("champ", 422))
check("6c moyen inconnu", refus(P.ajouter_consentement, A, h["id"], "whatsapp", "consentement", "pigeon") == ("champ", 422))
h = P.revoquer_consentement(A, h["id"], "email")
check("6d révoqué, la preuve reste", h["consentements"][-1]["revoque_le"] == "2026-10-27" and len(h["consentements"]) == 1)
check("6e révoquer sans consentement", refus(P.revoquer_consentement, A, h["id"], "email") == ("inconnu", 404))

print("[7] opposition = anonymisation")
o = P.creer(A, base(nom="Ondine Secret", entreprise="Maison Secrète", canaux=[{"type": "email", "valeur": "ondine@secrete.fr"},
                                                                              {"type": "whatsapp", "valeur": "07 98 76 54 32"}]))
o = P.opposer(A, o["id"])
octets = E.chemin(A, "prospects.json").read_bytes()
check("7a ni le nom ni l'adresse ni le numéro sur le disque",
      b"Ondine" not in octets and b"secrete" not in octets.lower() and b"987654" not in octets)
check("7b statut oppose, comptes gardés", o["statut"] == "oppose" and o["offre"] == "prestation" and o["source"]["type"] == "web")
check("7c au registre (e-mail et numéro)", O.oppose(["ondine@secrete.fr"]) and O.oppose(["+33 7 98 76 54 32"]))
check("7d oppose est terminal", refus(P.changer_statut, A, o["id"], "qualifie") == ("transition", 409))
check("7e une fiche opposée ne se modifie plus", refus(P.modifier, A, o["id"], {"nom": "x"}) == ("transition", 409))
q = P.creer(A, base(nom="Quentin", canaux=[{"type": "email", "valeur": "quentin@agence-q.fr"}]))
check("7f changer_statut(oppose) anonymise aussi", P.changer_statut(A, q["id"], "oppose")["prospect"]["nom"] == ""
      and O.oppose(["quentin@agence-q.fr"]))

print("[8] export et effacement")
x = P.exporter(A, lea["id"])
check("8a export complet", x["nom"] == "Léa Martin" and x["canaux"] and x["espace"] == A and x["oppose"] is False
      and "exporte_le" in x and x["historique"])
P.effacer(A, lea["id"])
check("8b effacé de la liste", all(p["id"] != lea["id"] for p in P.lister(A)))
check("8c effacement inscrit au registre par défaut", O.oppose(["lea@studio-lune.fr"]))
s = P.creer(A, base(nom="Erreur", canaux=[{"type": "email", "valeur": "faute@agence-e.fr"}]))
P.effacer(A, s["id"], inscrire_opposition=False)
check("8d saisie erronée : pas inscrit", not O.oppose(["faute@agence-e.fr"]))
check("8e effacer un inconnu", refus(P.effacer, A, "pr_00000000") == ("inconnu", 404))

print("[9] purge des fiches échues")
v = P.creer(B, base(nom="Vieux", canaux=[{"type": "email", "valeur": "vieux@agence-v.fr"}],
                    source=dict(SRC, date="2023-10-01")))
check("9a purge_le passée", v["purge_le"] == "2026-10-01")
avant = len(P.lister(B))
r = P.purger(date(2026, 10, 27))
check("9b retirée, les autres restent", r.get(B) == 1 and len(P.lister(B)) == avant - 1, str(r))
check("9c rien à purger ailleurs", A not in r)

print("[10] filtre, champs hors schéma, plafond, illisible")
check("10a filtre par statut", all(p["statut"] == "client" for p in P.lister(A, statut="client")) and P.lister(A, statut="client"))
check("10b score hors 0-100 refusé", refus(P.creer, A, base(nom="W", canaux=[], score=140)) == ("champ", 422))
w = P.creer(A, base(nom="Wanda", canaux=[{"type": "email", "valeur": "wanda@agence-w.fr"}], pirate="<script>", score=70))
check("10b' champ inconnu ignoré, score gardé", "pirate" not in w and w["score"] == 70)
check("10c canal de type inconnu", refus(P.creer, A, base(nom="C", canaux=[{"type": "pigeon", "valeur": "x"}])) == ("champ", 422))
_max = P.MAX_PROSPECTS
P.MAX_PROSPECTS = len(P.lister(A))
check("10d plafond", refus(P.creer, A, base(nom="Trop", canaux=[{"type": "email", "valeur": "trop@agence-t.fr"}])) == ("plafond", 409))
P.MAX_PROSPECTS = _max
fp = E.chemin(B, "prospects.json")
fp.write_bytes(b"\xff{casse")
check("10e illisible : liste vide", P.lister(B) == [])
cotes = list(fp.parent.glob("prospects.json.illisible-*"))
check("10f mis de côté avec ses octets", len(cotes) == 1 and cotes[0].read_bytes() == b"\xff{casse")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
