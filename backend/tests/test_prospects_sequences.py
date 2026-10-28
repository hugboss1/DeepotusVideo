# -*- coding: utf-8 -*-
"""t355 (28/10/2026) — Veille & prospection P4 : les SÉQUENCES d'un prospect (service prospects_sequences).
Proposer (canal possible, 1 à 3 étapes, délais, objet, longueurs, mots interdits), valider (porte humaine : jamais l'agent),
planifier (consentement revérifié, heures calmes, plafond e-mail 10/20/30), marquer envoyé (canaux manuels seulement),
arrêt automatique quand la fiche répond ou s'oppose, liens « ouvrir ».
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_prospects_sequences.py"""
import json, os, pathlib, sys, tempfile
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzseq355_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import espaces as E, prospects as P, prospects_score as SC, prospects_sequences as S   # noqa: E402

for m in (P, SC):
    m._aujourdhui = lambda: date(2026, 10, 28)
PARIS = ZoneInfo("Europe/Paris")
LUNDI = datetime(2026, 11, 2, 10, 0, tzinfo=PARIS).astimezone(timezone.utc)       # lundi 2 nov. 10 h, heure de Paris
S._maintenant = lambda: LUNDI

A = E.creer({"nom": "Prospection"})["id"]
SRC = {"type": "web", "url": "https://studio-lune.fr", "date": "2026-10-20"}


def fiche(nom, canaux, base="interet_legitime_b2b", statut="qualifie"):
    f = P.creer(A, {"nom": nom, "entreprise": nom, "source": SRC, "base_legale": base, "canaux": canaux})
    if statut != "propose":
        P.changer_statut(A, f["id"], "qualifie")
    if statut == "contacte":
        P.changer_statut(A, f["id"], "contacte")
    return f["id"]


def refus(fn, code=None):
    try:
        fn()
    except S.RefusSequence as e:
        return code is None or e.code == code, e.code
    return False, "aucun refus"


E1 = [{"objet": "Vos vidéos produit", "texte": "Bonjour, une idée pour vos vidéos.", "delai_jours": 0},
      {"objet": "Relance", "texte": "Je me permets de revenir vers vous.", "delai_jours": 3},
      {"objet": "Dernier mot", "texte": "Dernier message de ma part.", "delai_jours": 7}]
mail = fiche("Studio Lune", [{"type": "email", "valeur": "contact@studio-lune.fr"}, {"type": "x", "valeur": "@studiolune"}])

print("[1] proposer")
s = S.proposer(A, mail, "email", E1, interdits=["gratuit"], qui="agent")
check("1a séquence proposée, 3 étapes en brouillon", s["statut"] == "proposee" and [e["statut"] for e in s["etapes"]] == ["brouillon"] * 3, s)
check("1b id sq_ et prospect", s["id"].startswith("sq_") and s["pid"] == mail and s["cree_par"] == "agent")
check("1c canal impossible refusé (whatsapp sans accord)", refus(lambda: S.proposer(A, mail, "whatsapp", [{"texte": "x", "delai_jours": 0}]), "canal")[0])
check("1d 4 étapes refusées", refus(lambda: S.proposer(A, mail, "email", E1 + [E1[1]]), "champ")[0])
check("1e aucune étape refusée", refus(lambda: S.proposer(A, mail, "email", []), "champ")[0])
check("1f e-mail sans objet refusé", refus(lambda: S.proposer(A, mail, "email", [{"texte": "x", "delai_jours": 0}]), "champ")[0])
check("1g 1re étape avec délai refusée", refus(lambda: S.proposer(A, mail, "email", [dict(E1[0], delai_jours=2)]), "champ")[0])
check("1h relance à 1 jour refusée", refus(lambda: S.proposer(A, mail, "email", [E1[0], dict(E1[1], delai_jours=1)]), "champ")[0])
check("1i relance à 31 jours refusée", refus(lambda: S.proposer(A, mail, "email", [E1[0], dict(E1[1], delai_jours=31)]), "champ")[0])
check("1j texte trop long refusé (X > 2000)", refus(lambda: S.proposer(A, mail, "x", [{"texte": "a" * 2001, "delai_jours": 0}]), "champ")[0])
r = refus(lambda: S.proposer(A, mail, "email", [dict(E1[0], texte="Essai GRATUIT pour vous")], interdits=["gratuit"]), "interdit")
check("1k mot interdit (casse libre) refusé", r[0], r)
check("1l mot interdit dans l'objet refusé", refus(lambda: S.proposer(A, mail, "email", [dict(E1[0], objet="Gratuit")], interdits=["gratuit"]), "interdit")[0])
check("1m « gratuité » n'est pas « gratuit »", S.proposer(A, mail, "x", [{"texte": "Sans gratuité cachée", "delai_jours": 0}], interdits=["gratuit"])["statut"] == "proposee")
neuf = fiche("Nouveau", [{"type": "email", "valeur": "a@nouveau.fr"}], statut="propose")
check("1n fiche encore « proposé » : refus (qualifier d'abord)", refus(lambda: S.proposer(A, neuf, "email", E1), "etat")[0])
check("1o prospect inconnu : refus inconnu", refus(lambda: S.proposer(A, "pr_00000000", "email", E1), "inconnu")[0])
s2 = S.proposer(A, mail, "email", E1[:2], qui="agent")
l = {x["id"]: x for x in S.lister(A, mail)}
check("1p une nouvelle proposition remplace l'ancienne non validée", l[s["id"]]["statut"] == "annulee" and l[s2["id"]]["statut"] == "proposee")

print("[2] valider (porte humaine)")
check("2a l'agent ne valide jamais", refus(lambda: S.valider(A, s2["id"], qui="agent"), "etat")[0])
v = S.valider(A, s2["id"])
check("2b l'utilisateur valide", v["statut"] == "validee" and v["valide_le"])
check("2c une séquence validée bloque une nouvelle proposition sur le canal", refus(lambda: S.proposer(A, mail, "email", E1), "etat")[0])
check("2d revalider : refus", refus(lambda: S.valider(A, s2["id"]), "etat")[0])
check("2e planifier une séquence non validée : refus", refus(lambda: S.planifier(A, S.proposer(A, mail, "x", [{"texte": "Bonjour", "delai_jours": 0}])["id"]), "etat")[0])

print("[3] planifier : heures calmes, délais")
p = S.planifier(A, s2["id"], qui="agent")
q = [datetime.fromisoformat(e["quand"]) for e in p["etapes"]]
check("3a planifiée, étapes planifiées", p["statut"] == "planifiee" and all(e["statut"] == "planifiee" for e in p["etapes"]), p)
check("3b 1re étape tout de suite (dans les horaires)", q[0] == LUNDI, q)
check("3c relance 3 jours après", q[1] - q[0] == timedelta(days=3), q)
check("3d heures en UTC", all(x.utcoffset() == timedelta(0) for x in q))
sx = S.proposer(A, mail, "x", [{"texte": "Bonjour", "delai_jours": 0}, {"texte": "Relance", "delai_jours": 5}])
S.valider(A, sx["id"])
samedi = datetime(2026, 11, 7, 20, 0, tzinfo=PARIS)
px = S.planifier(A, sx["id"], debut=samedi.isoformat())
q = [datetime.fromisoformat(e["quand"]).astimezone(PARIS) for e in px["etapes"]]
check("3e samedi soir → lundi 9 h (heures calmes)", (q[0].weekday(), q[0].hour, q[0].minute) == (0, 9, 0), q[0])
check("3f relance + 5 jours (samedi) → lundi suivant 9 h", (q[1].date(), q[1].hour) == (date(2026, 11, 16), 9), q[1])
dim = datetime(2026, 11, 8, 12, 16, 36, tzinfo=PARIS)
check("3i hors horaires : posé à l'ouverture pile (lundi 9 h 00 min 00 s)", S.prochain_calme(S._agent(A), dim.astimezone(timezone.utc)).astimezone(PARIS)
      == datetime(2026, 11, 9, 9, 0, tzinfo=PARIS), S.prochain_calme(S._agent(A), dim.astimezone(timezone.utc)).astimezone(PARIS))
check("3g une date passée vaut maintenant", S._quand_depart("2020-01-01T00:00:00") == LUNDI)
check("3h date illisible refusée", refus(lambda: S._quand_depart("demain"), "champ")[0])

print("[4] plafond e-mail 10/20/30 par jour")
pids = [fiche(f"Studio {i}", [{"type": "email", "valeur": f"contact@studio{i}.fr"}]) for i in range(12)]
jours = []
for pid in pids:
    t = S.proposer(A, pid, "email", [E1[0]])
    S.valider(A, t["id"])
    jours.append(datetime.fromisoformat(S.planifier(A, t["id"])["etapes"][0]["quand"]).astimezone(PARIS).date())
compte = {d: jours.count(d) for d in set(jours)}
# la 1re étape de s2 (lundi) compte : 10 le lundi au total, le reste mardi
check("4a 1re semaine : 10 e-mails le premier jour, le reste au lendemain", compte.get(date(2026, 11, 2)) == 9 and compte.get(date(2026, 11, 3)) == 3, compte)
check("4b plafond du jour : 10 / 20 / 30", [S.plafond_email(date(2026, 11, 2), date(2026, 11, 2) + timedelta(days=d)) for d in (0, 6, 7, 13, 14, 60)] == [10, 10, 20, 20, 30, 30])
check("4c les canaux manuels ne comptent pas", px["statut"] == "planifiee")

print("[5] marquer envoyé (manuel) et arrêt automatique")
check("5a e-mail : pas de « marquer envoyé » (envoi automatique, P5)", refus(lambda: S.marquer_envoye(A, s2["id"], 0), "canal")[0])
check("5b X : la relance avant la 1re étape refusée", refus(lambda: S.marquer_envoye(A, sx["id"], 1), "etat")[0])
m = S.marquer_envoye(A, sx["id"], 0)
f = P.lire(A, mail)
check("5c étape envoyée, fiche contactée, historique noté", m["etapes"][0]["statut"] == "envoyee" and f["statut"] == "contacte"
      and any(h["quoi"] == "contact_sortant" for h in f["historique"]), (m["etapes"][0], f["statut"]))
check("5d deux fois : refus", refus(lambda: S.marquer_envoye(A, sx["id"], 0), "etat")[0])
m = S.marquer_envoye(A, sx["id"], 1)
check("5e dernière étape envoyée : séquence terminée", m["statut"] == "terminee")
P.changer_statut(A, mail, "repondu")
l = {x["id"]: x for x in S.lister(A, mail)}
check("5f la fiche a répondu : la séquence e-mail s'arrête (étapes annulées)", l[s2["id"]]["statut"] == "annulee"
      and all(e["statut"] == "annulee" for e in l[s2["id"]]["etapes"]) and "repondu" in (l[s2["id"]].get("motif") or ""), l[s2["id"]])
check("5g la séquence terminée reste terminée", l[sx["id"]]["statut"] == "terminee")
op = fiche("Opposé", [{"type": "email", "valeur": "a@oppose.fr"}])
so = S.proposer(A, op, "email", [E1[0]]); S.valider(A, so["id"])
P.opposer(A, op)
check("5h fiche opposée avant la planification : refus", refus(lambda: S.planifier(A, so["id"]))[0])

print("[6] dû, liens, annuler")
d = fiche("Dû", [{"type": "instagram", "valeur": "studio.du"}, {"type": "linkedin", "valeur": "https://www.linkedin.com/company/studio-du"}])
sd = S.proposer(A, d, "instagram", [{"texte": "Bonjour", "delai_jours": 0}]); S.valider(A, sd["id"]); S.planifier(A, sd["id"])
x = [y for y in S.lister(A, d) if y["id"] == sd["id"]][0]
check("6a étape à l'heure : « due » et lien Instagram", x["etapes"][0]["due"] is True and x["ouvrir"] == "https://www.instagram.com/studio.du/", x)
check("6b lien X depuis @pseudo", S.lien({"canaux": [{"type": "x", "valeur": "@studiolune"}]}, "x") == "https://x.com/studiolune")
check("6c lien LinkedIn = URL de la fiche", S.lien({"canaux": [{"type": "linkedin", "valeur": "https://www.linkedin.com/company/studio-du"}]}, "linkedin")
      == "https://www.linkedin.com/company/studio-du")
check("6d lien douteux : aucun", S.lien({"canaux": [{"type": "linkedin", "valeur": "javascript:alert(1)"}]}, "linkedin") is None
      and S.lien({"canaux": [{"type": "x", "valeur": "a b"}]}, "x") is None)
a = S.annuler(A, sd["id"])
check("6e annuler : étapes non envoyées annulées", a["statut"] == "annulee" and a["etapes"][0]["statut"] == "annulee")
check("6f annuler deux fois : refus", refus(lambda: S.annuler(A, sd["id"]), "etat")[0])
check("6g séquence inconnue : refus inconnu", refus(lambda: S.valider(A, "sq_00000000"), "inconnu")[0])
check("6h espace inconnu : refus", refus(lambda: S.lister("es_inconnu00"))[0])

print("[8] relecture : RGPD, registre indisponible, consentement retiré")
def brut():
    return E.chemin(A, S.FICHIER).read_text(encoding="utf-8")
e1 = fiche("Efface", [{"type": "email", "valeur": "a@efface.fr"}])
S.proposer(A, e1, "email", [dict(E1[0], texte="Texte secret EFFACE-1")])
P.effacer(A, e1)
check("8a effacement : le texte des étapes quitte le fichier tout de suite", "EFFACE-1" not in brut())
o1 = fiche("Oppose2", [{"type": "email", "valeur": "a@oppose2.fr"}])
so1 = S.proposer(A, o1, "email", [dict(E1[0], texte="Texte secret OPPOSE-1", objet="Objet OPPOSE-1")])
P.opposer(A, o1)
check("8b opposition : textes et objets effacés", "OPPOSE-1" not in brut())
x1 = fiche("Export", [{"type": "email", "valeur": "a@export.fr"}])
S.proposer(A, x1, "email", [dict(E1[0], texte="Texte EXPORT-1")])
check("8c export (droit d'accès) : les séquences de la fiche y sont", "EXPORT-1" in json.dumps(P.exporter(A, x1), ensure_ascii=False))
pu = fiche("Purge", [{"type": "email", "valeur": "a@purge.fr"}])
S.proposer(A, pu, "email", [dict(E1[0], texte="Texte PURGE-1")])
P.purger(date(2040, 1, 1))
check("8d purge à 3 ans : textes effacés", "PURGE-1" not in brut() and "EXPORT-1" not in brut())
c1 = fiche("Consent", [{"type": "email", "valeur": "a@consent.fr"}])
sc = S.proposer(A, c1, "email", [E1[0]]); S.valider(A, sc["id"]); S.planifier(A, sc["id"])
P.modifier(A, c1, {"base_legale": "consentement"})
x = [y for y in S.lister(A, c1) if y["id"] == sc["id"]][0]
check("8e base légale changée (plus de canal possible) : séquence arrêtée, motif canal", x["statut"] == "annulee" and x["motif"] == "canal", (x["statut"], x["motif"]))
r1 = fiche("Registre", [{"type": "email", "valeur": "a@registre.fr"}])
sr = S.proposer(A, r1, "email", [E1[0]]); S.valider(A, sr["id"]); S.planifier(A, sr["id"])
_opp = P._op.opposes
def panne(*a):
    raise P._op.RegistreIndisponible("registre verrouillé")
P._op.opposes = panne
r = refus(lambda: S.lister(A, r1), "indisponible")
P._op.opposes = _opp
check("8f registre indisponible : refus 503, jamais une étape « due »", r[0], r)

print("[7] fichier illisible")
f = E.chemin(A, S.FICHIER)
f.write_text("{pas du json", encoding="utf-8")
check("7a illisible : mis de côté, liste vide", S.lister(A) == [] and any(x.name.startswith("sequences.json.illisible-") for x in f.parent.iterdir()))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
