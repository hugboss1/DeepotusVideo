# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 1 : les SOURCES de prospects (lecteurs purs).
WhatsApp entrant (accord, sans STOP ni désinscription ni registre ni fiche existante ; whatsapp.json jamais réécrit), CSV
déposé (séparateur détecté, consentement daté exigé, formule neutralisée, 500 lignes au plus), signaux de la veille (thème
de besoin ou lexique, jamais d'auteur). Data-dir isolé, aucun réseau.
Run (depuis backend/) : & $PY tests/test_prospects_sources.py"""
import json, os, pathlib, sys, tempfile
from datetime import date
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpsrc_"))
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
from app.services import prospects_sources as S                          # noqa: E402

P._aujourdhui = lambda: date(2026, 10, 28)
S._aujourdhui = lambda: date(2026, 10, 28)
E.lire()
A = E.creer({"nom": "Prospection"})["id"]

print("[1] WhatsApp entrant")
doc = {"etat": {"111": {
    "accords": {"tel:33600000001": {"date": "2026-10-20T10:00:00+00:00", "source": "entrant"},
                "tel:33600000002": {"date": "2026-10-21T10:00:00+00:00", "source": "formulaire"},
                "tel:33600000003": {"date": "2026-10-22T10:00:00+00:00", "source": "entrant"},
                "tel:33600000004": {"date": "2026-10-22T10:00:00+00:00", "source": "entrant"},
                "bsuid:XYZ": {"date": "2026-10-22T10:00:00+00:00", "source": "entrant"},
                "tel:33600000006": {"date": "2026-10-23T10:00:00+00:00", "source": "entrant"},
                "tel:33600000007": {"date": "2026-10-24T10:00:00+00:00", "source": "entrant"}},
    "stops": {"tel:33600000003": "2026-10-23T10:00:00+00:00", "tel:33600000005": "2026-10-23T10:00:00+00:00"},
    "desinscrits_marketing": {"tel:33600000004": "2026-10-23T10:00:00+00:00"},
    "alias": {"bsuid:XYZ": "tel:33600000005", "tel:33600000005": "bsuid:XYZ"},
    "compteur": {},
    "journal": [{"quand": "2026-10-25T09:00:00+00:00", "sens": "entrant", "identite": "tel:33600000001"},
                {"quand": "2026-10-24T09:00:00+00:00", "sens": "entrant", "identite": "tel:33600000002"}]}}}
fw = E.chemin(A, "whatsapp.json")
fw.write_text(json.dumps(doc), encoding="utf-8")
O.inscrire(["tel:33600000006"], "saisie")
P.creer(A, {"nom": "Déjà là", "source": {"type": "whatsapp", "date": "2026-10-20"}, "base_legale": "consentement",
            "canaux": [{"type": "whatsapp", "valeur": "+33600000007"}]})
avant = fw.read_bytes()
r = S.whatsapp_entrants(A)
ids = [x["identite"] for x in r]
check("1a accord entrant et accord saisi proposés", ids[:2] == ["tel:33600000001", "tel:33600000002"], ids)
check("1b STOP, désinscrit, alias stoppé, registre, fiche existante exclus", set(ids) == {"tel:33600000001", "tel:33600000002"}, ids)
check("1c forme : numéro masqué, accord, dernier entrant, compte", r[0]["numero_masque"].endswith("0001") and "33600" not in r[0]["numero_masque"]
      and r[0]["accord"]["source"] == "entrant" and r[0]["dernier_entrant"] == "2026-10-25" and r[0]["compte"] == "111", r[0])
check("1d whatsapp.json jamais réécrit", fw.read_bytes() == avant)
B = E.creer({"nom": "Vide"})["id"]
check("1e espace sans WhatsApp : liste vide", S.whatsapp_entrants(B) == [])

print("[2] CSV déposé")
csv = ("Email;Prénom;Nom;Entreprise;Date;Consentement;Téléphone;Colonne inconnue\n"
       "lea@studio-lune.fr;Léa;Martin;Studio Lune;2026-10-20;oui;+33611111111;x\n"
       "tom@agence-t.fr;Tom;;Agence T;2026-10-21;non;;\n"
       "zoe@agence-z.fr;Zoé;;=HYPERLINK(\"http://x\");2026-10-22;1;;\n"
       "max@maison-x.fr;Max;;Maison X;2030-01-01;oui;;\n"
       "sans@date.fr;Sans;;;;oui;;\n")
r = S.lire_csv(csv, "liste_attente")
L = r["lignes"]
check("2a séparateur ; détecté, deux lignes valides", len(L) == 2, [x.get("nom") for x in L])
l0 = L[0]
check("2b champs creer : nom, entreprise, canaux, source, base, consentements", l0["nom"] == "Léa Martin" and l0["entreprise"] == "Studio Lune"
      and {"type": "email", "valeur": "lea@studio-lune.fr"} in l0["canaux"] and {"type": "telephone", "valeur": "+33611111111"} in l0["canaux"]
      and l0["source"] == {"type": "liste_attente", "date": "2026-10-20", "url": ""} and l0["base_legale"] == "consentement"
      and l0["consentements"] == [{"canal": "email", "base_legale": "consentement", "moyen": "inscription", "date": "2026-10-20"}], l0)
check("2c formule neutralisée", L[1]["entreprise"] == 'HYPERLINK("http://x")', L[1]["entreprise"])
raisons = {x["ligne"]: x["raison"] for x in r["refus"]}
check("2d sans consentement, date future, sans date : refusées et nommées", set(raisons) == {3, 5, 6} and all(raisons.values()), raisons)
r = S.lire_csv("email,nom,consentement,date\n" + "".join(f"p{i}@a.fr,P{i},oui,2026-10-01\n" for i in range(501)), "formulaire")
check("2e 500 lignes au plus, le reste refusé (plafond)", len(r["lignes"]) == 500 and r["refus"][-1]["ligne"] == 502
      and "500" in r["refus"][-1]["raison"], (len(r["lignes"]), r["refus"][-1:]))
check("2f formulaire : moyen formulaire", r["lignes"][0]["consentements"][0]["moyen"] == "formulaire")
try:
    S.lire_csv("a,b\n1,2\n", "salon"); bad = False
except ValueError:
    bad = True
check("2g origine inconnue refusée", bad)
r = S.lire_csv("nom,consentement,date\nSansCanal,oui,2026-10-01\n", "liste_attente")
check("2h ligne sans aucun canal refusée", not r["lignes"] and r["refus"][0]["ligne"] == 2)

print("[3] signaux de la veille")
d = E.dossier() / A / "veille" / "2026-10-27"
d.mkdir(parents=True)
(d / "rapport.json").write_text(json.dumps({"version": 1, "date": "2026-10-27"}), encoding="utf-8")
lignes = [
    {"concurrent": "runway", "source": "hn", "url": "https://news.ycombinator.com/item?id=1", "date": "2026-10-20",
     "auteur_hash": "a1b2c3d4e5", "texte": "Les crédits partent trop vite", "theme": "prix_credits", "polarite": "faiblesse"},
    {"concurrent": "kling", "source": "youtube", "url": "https://youtube.com/watch?v=2", "date": "2026-10-21",
     "auteur_hash": "a1b2c3d4e6", "texte": "Je cherche une alternative à Kling", "theme": "qualite_sortie", "polarite": "faiblesse"},
    {"concurrent": "kling", "source": "youtube", "url": "https://youtube.com/watch?v=3", "date": "2026-10-21",
     "auteur_hash": "a1b2c3d4e7", "texte": "Super rendu", "theme": "qualite_sortie", "polarite": "force"}]
(d / "verbatims.jsonl").write_text("\n".join(json.dumps(x) for x in lignes), encoding="utf-8")
r = S.signaux_veille(A)
check("3a thème de besoin et lexique retenus, force écartée", [x["url"][-1] for x in r] == ["1", "2"], r)
check("3b jamais d'auteur", all("auteur_hash" not in x and "auteur" not in x for x in r) and set(r[0]) == {"theme", "concurrent", "source", "date", "url", "texte"}, r[0])
check("3c aucune veille : []", S.signaux_veille(B) == [])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
