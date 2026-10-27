# -*- coding: utf-8 -*-
"""t311 tâche 1 (27/10/2026) — agent WhatsApp par espace : réglages d'agent, routes d'état et levée d'un STOP.
Plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md (tâche 1). Routes réelles (TestClient), data-dir et sqlite
temporaires, AUCUN réseau : `kapso._requete` est un faux qui ÉCHOUE si on l'appelle (aucune de ces routes ne parle à Kapso).
Ce que ce banc garde :
  G1  défauts complets d'un espace neuf (`AGENT_DEFAUT`, `ROLES_AGENT`, `MODES`), clés t310 inchangées, rien d'écrit en lecture.
  G2  `regler_espace` refuse chaque valeur hors bornes (une assertion par champ) et n'écrit rien au refus.
  G3  fusion champ par champ : un champ posé garde les autres ; `horaires` partiel garde les autres clés d'horaires.
  G4  `regler(cid, …)` t310 : même signature, même effet, mêmes réglages d'espace.
  G5  `dans_horaires` (pure) : mardi 10:00 Paris vrai, samedi faux, 18:00 pile faux, fuseau New York décale.
  G6  `lever_stop` : retire l'identité ET son alias, pose un accord SAISI `reabonnement:…`, refuse une source vide.
  G7  routes : GET /etat (+ agent, jamais de clé `texte`), GET/PUT réglages, POST stop/lever ; 200, 400, 404, hors localhost.
  G8  `espaces.FICHIERS` porte `whatsapp_brouillons.json` ; les clés d'agent inconnues déjà en place survivent.
Run (depuis backend/) : & $PY tests/test_whatsapp_reglages.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwareg_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
          "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
          "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "KAPSO_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
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
from fastapi.testclient import TestClient                            # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA    # noqa: E402
from app.services import whatsapp as WA                              # noqa: E402

APPELS_KAPSO = []


async def faux_requete(methode, url, *, json=None, params=None):
    APPELS_KAPSO.append((methode, url))
    return 500, {"error": "ce banc n'appelle jamais Kapso"}, {}


KA._requete = faux_requete

c = TestClient(app, client=("127.0.0.1", 50000))
c.__enter__()
E.lire()
UTC = timezone.utc


def compte(eid, pid, waba="WABA-1"):
    cid_ = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cid_, {"WHATSAPP_PHONE_ID": pid, "WHATSAPP_WABA_ID": waba})
    return cid_


def doc_wa(eid):
    f = _tmp / "espaces" / eid / "whatsapp.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def refuse(eid, champs):
    avant = doc_wa(eid)
    try:
        WA.regler_espace(eid, champs)
    except ValueError:
        return doc_wa(eid) == avant
    return False


def cles(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from cles(v)
    elif isinstance(o, list):
        for v in o:
            yield from cles(v)


boite = E.creer({"nom": "Atelier Soleil"})["id"]
autre = E.creer({"nom": "Atelier Lune"})["id"]
cid = compte(boite, "PN-1")
DEFAUT = {"actif": False, "mode": "brouillon", "roles": [],
          "horaires": {"jours": [0, 1, 2, 3, 4], "debut": "09:00", "fin": "18:00", "fuseau": "Europe/Paris"},
          "message_hors_horaires": "", "plafond_jour_contact": 5, "mots_humain": [], "modele_validation": None,
          "plafond_redactions_jour": 20}      # relecture finale : borne des rédactions du relevé par contact et par jour

print("\n[G1] défauts d'un espace neuf")
check("G1.1 constantes", WA.AGENT_DEFAUT == DEFAUT and WA.ROLES_AGENT == ("faq", "rendez_vous", "commande", "validation")
      and WA.MODES == ("brouillon", "auto"), WA.AGENT_DEFAUT)
r = WA.reglages(boite)
check("G1.2 reglages(eid) = t310 + agent complet", r == {"plafond_mois": 1000, "marche_defaut": "33", "agent": DEFAUT}, r)
check("G1.3 la copie rendue n'est pas l'original (muter n'altère rien)",
      (r["agent"]["roles"].append("faq"), r["agent"]["horaires"]["jours"].append(6), WA.reglages(boite)["agent"] == DEFAUT)[-1])
check("G1.4 lire n'écrit rien", doc_wa(boite) == {}, doc_wa(boite))


def leve(exc, f):
    try:
        f()
    except exc:
        return True
    return False


def _message(f):
    try:
        f()
    except ValueError as e:
        return str(e)
    return None


check("G1.5 id invalide -> KeyError", leve(KeyError, lambda: WA.reglages("../x")))

print("\n[G2] bornes : chaque valeur hors bornes est refusée, rien n'est écrit")
for lib, ch in [
    ("plafond_mois 0", {"plafond_mois": 0}), ("plafond_mois 1_000_001", {"plafond_mois": 1_000_001}),
    ("plafond_mois booléen", {"plafond_mois": True}), ("plafond_mois texte", {"plafond_mois": "12"}),
    ("marche_defaut vide", {"marche_defaut": ""}), ("marche_defaut 5 chiffres", {"marche_defaut": "12345"}),
    ("marche_defaut lettres", {"marche_defaut": "3a"}), ("marche_defaut entier", {"marche_defaut": 33}),
    ("agent non objet", {"agent": "oui"}), ("champ d'agent inconnu", {"agent": {"pirate": 1}}),
    ("champ d'espace inconnu", {"couleur": "rouge"}),
    ("actif non booléen", {"agent": {"actif": "oui"}}),
    ("mode inconnu", {"agent": {"mode": "libre"}}),
    ("roles non liste", {"agent": {"roles": "faq"}}), ("role inconnu", {"agent": {"roles": ["faq", "magie"]}}),
    ("jour 7", {"agent": {"horaires": {"jours": [7]}}}), ("jour -1", {"agent": {"horaires": {"jours": [-1]}}}),
    ("jour booléen", {"agent": {"horaires": {"jours": [True]}}}), ("jours non liste", {"agent": {"horaires": {"jours": "0"}}}),
    ("debut 24:00", {"agent": {"horaires": {"debut": "24:00"}}}), ("debut 9h", {"agent": {"horaires": {"debut": "9h"}}}),
    ("fin 12:60", {"agent": {"horaires": {"fin": "12:60"}}}), ("fin 9:00 sans zéro", {"agent": {"horaires": {"fin": "9:00"}}}),
    ("fuseau inconnu", {"agent": {"horaires": {"fuseau": "Mars/Olympus"}}}),
    ("fuseau chemin", {"agent": {"horaires": {"fuseau": "../etc"}}}), ("fuseau vide", {"agent": {"horaires": {"fuseau": ""}}}),
    ("horaires clé inconnue", {"agent": {"horaires": {"semaine": 1}}}),
    ("hors horaires 1025 car.", {"agent": {"message_hors_horaires": "x" * 1025}}),
    ("hors horaires non texte", {"agent": {"message_hors_horaires": 5}}),
    ("plafond contact 51", {"agent": {"plafond_jour_contact": 51}}), ("plafond contact -1", {"agent": {"plafond_jour_contact": -1}}),
    ("plafond contact booléen", {"agent": {"plafond_jour_contact": True}}),
    ("rédactions 201", {"agent": {"plafond_redactions_jour": 201}}), ("rédactions -1", {"agent": {"plafond_redactions_jour": -1}}),
    ("rédactions booléen", {"agent": {"plafond_redactions_jour": False}}),
    ("rédactions texte", {"agent": {"plafond_redactions_jour": "20"}}),
    ("31 mots humain", {"agent": {"mots_humain": [f"m{i}" for i in range(31)]}}),
    ("mot humain 41 car.", {"agent": {"mots_humain": ["x" * 41]}}), ("mot humain vide", {"agent": {"mots_humain": [""]}}),
    ("mot humain non texte", {"agent": {"mots_humain": [3]}}),
    ("modele_validation texte", {"agent": {"modele_validation": "rappel"}}),
    ("modele_validation sans langue", {"agent": {"modele_validation": {"nom": "rappel"}}}),
    ("modele_validation nom vide", {"agent": {"modele_validation": {"nom": "", "langue": "fr"}}}),
    ("modele_validation clé en trop", {"agent": {"modele_validation": {"nom": "a", "langue": "fr", "x": 1}}}),
]:
    check(f"G2 refusé : {lib}", refuse(boite, ch), ch)
check("G2.x corps non objet -> ValueError", leve(ValueError, lambda: WA.regler_espace(boite, [1])))
check("G2.y espace inconnu -> KeyError", leve(KeyError, lambda: WA.regler_espace("nope", {"plafond_mois": 5})))
check("G2.z bornes acceptées : 1, 1_000_000, 50, 30 mots de 40 car., 1024 car.", lambda: WA.regler_espace(autre, {
    "plafond_mois": 1, "agent": {"plafond_jour_contact": 50, "mots_humain": ["x" * 40] * 30,
                                 "message_hors_horaires": "y" * 1024}})["plafond_mois"] == 1
      and WA.regler_espace(autre, {"plafond_mois": 1_000_000, "marche_defaut": "1234",
                                   "agent": {"plafond_jour_contact": 0}})["plafond_mois"] == 1_000_000)
check("G2.r rédactions par contact : 0 et 200 acceptées ; 201 refusé avec le message L10",
      lambda: WA.regler_espace(autre, {"agent": {"plafond_redactions_jour": 0}})["agent"]["plafond_redactions_jour"] == 0
      and WA.regler_espace(autre, {"agent": {"plafond_redactions_jour": 200}})["agent"]["plafond_redactions_jour"] == 200
      and leve(ValueError, lambda: WA.regler_espace(autre, {"agent": {"plafond_redactions_jour": 201}}))
      and _message(lambda: WA.regler_espace(autre, {"agent": {"plafond_redactions_jour": 201}}))
      == "agent : rédactions par contact et par jour : un entier de 0 à 200 est attendu")
WA.regler_espace(autre, {"plafond_mois": 1000, "marche_defaut": "33", "agent": DEFAUT})

print("\n[G3] fusion champ par champ")
r = WA.regler_espace(boite, {"agent": {"actif": True, "roles": ["faq", "commande"]}})
check("G3.1 deux champs posés, le reste en défaut", r["agent"] == {**DEFAUT, "actif": True, "roles": ["faq", "commande"]}
      and r["plafond_mois"] == 1000, r)
r = WA.regler_espace(boite, {"agent": {"mode": "auto", "horaires": {"debut": "08:30"}}})
check("G3.2 mode posé, actif et rôles gardés, horaires partiel garde jours/fin/fuseau",
      r["agent"]["mode"] == "auto" and r["agent"]["actif"] is True and r["agent"]["roles"] == ["faq", "commande"]
      and r["agent"]["horaires"] == {"jours": [0, 1, 2, 3, 4], "debut": "08:30", "fin": "18:00", "fuseau": "Europe/Paris"}, r)
r = WA.regler_espace(boite, {"plafond_mois": 250, "marche_defaut": "1"})
check("G3.3 champs d'espace seuls : l'agent est gardé", r["plafond_mois"] == 250 and r["marche_defaut"] == "1"
      and r["agent"]["mode"] == "auto", r)
r = WA.regler_espace(boite, {"agent": {"modele_validation": {"nom": "rappel_rdv", "langue": "fr"},
                                      "mots_humain": ["humain", "conseiller"], "plafond_jour_contact": 0,
                                      "message_hors_horaires": "Nous répondons de 9 h à 18 h.",
                                      "horaires": {"jours": [5, 6, 5], "fuseau": "America/New_York"}}})
check("G3.4 tous les types de champs rangés", r["agent"]["modele_validation"] == {"nom": "rappel_rdv", "langue": "fr"}
      and r["agent"]["mots_humain"] == ["humain", "conseiller"] and r["agent"]["plafond_jour_contact"] == 0
      and r["agent"]["message_hors_horaires"] == "Nous répondons de 9 h à 18 h."
      and r["agent"]["horaires"]["jours"] == [5, 6] and r["agent"]["horaires"]["fuseau"] == "America/New_York", r)
r = WA.regler_espace(boite, {"agent": {"modele_validation": None}})
check("G3.5 modele_validation remis à None", r["agent"]["modele_validation"] is None, r)
check("G3.6 relu tel quel ; l'autre espace n'a pas bougé", WA.reglages(boite) == r and WA.reglages(autre)["agent"] == DEFAUT
      and WA.reglages(autre)["plafond_mois"] == 1000)
WA.regler_espace(boite, {"agent": DEFAUT, "plafond_mois": 1000, "marche_defaut": "33"})

print("\n[G4] regler(cid, …) t310")
WA.regler(cid, plafond_mois=0)
check("G4.1 regler garde sa borne t310 (0 permis) et écrit les réglages de l'espace", WA.reglages(boite)["plafond_mois"] == 0
      and doc_wa(boite)["reglages"]["plafond_mois"] == 0)
WA.regler(cid, plafond_mois=7, marche_defaut="1")
check("G4.2 regler(plafond, marché)", WA.reglages(boite)["plafond_mois"] == 7 and WA.reglages(boite)["marche_defaut"] == "1"
      and WA.etat(cid)["plafond_mois"] == 7)
check("G4.3 regler refuse toujours -1 et tout autre kwarg", leve(ValueError, lambda: WA.regler(cid, plafond_mois=-1))
      and leve(TypeError, lambda: WA.regler(cid, agent={})))
WA.regler(cid, plafond_mois=1000, marche_defaut="33")

print("\n[G5] dans_horaires")
ag = WA.reglages(boite)["agent"]
mar = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)            # mardi 27/10/2026, 10:00 à Paris (CET depuis le 25/10)
check("G5.1 mardi 10:00 Paris : vrai", WA.dans_horaires(ag, mar) is True)
check("G5.2 samedi 10:00 Paris : faux", WA.dans_horaires(ag, datetime(2026, 10, 31, 9, 0, tzinfo=UTC)) is False)
check("G5.3 mardi 18:00 pile : faux (fin exclue)", WA.dans_horaires(ag, datetime(2026, 10, 27, 17, 0, tzinfo=UTC)) is False)
check("G5.4 mardi 17:59 : vrai ; 09:00 pile : vrai (début inclus) ; 08:59 : faux",
      WA.dans_horaires(ag, datetime(2026, 10, 27, 16, 59, tzinfo=UTC)) is True
      and WA.dans_horaires(ag, datetime(2026, 10, 27, 8, 0, tzinfo=UTC)) is True
      and WA.dans_horaires(ag, datetime(2026, 10, 27, 7, 59, tzinfo=UTC)) is False)
ny = {**ag, "horaires": {**ag["horaires"], "fuseau": "America/New_York"}}
check("G5.5 fuseau New York : le même instant y est 05:00 -> faux ; 14:00 UTC y est 10:00 -> vrai",
      WA.dans_horaires(ny, mar) is False and WA.dans_horaires(ny, datetime(2026, 10, 27, 14, 0, tzinfo=UTC)) is True)
check("G5.6 le jour se lit dans le fuseau : lundi 23:30 UTC = mardi 00:30 Paris ; fenêtre 00:00-23:59 mardi -> vrai ; 09-18 -> faux",
      WA.dans_horaires({**ag, "horaires": {**ag["horaires"], "debut": "00:00", "fin": "23:59", "jours": [1]}},
                       datetime(2026, 10, 26, 23, 30, tzinfo=UTC)) is True
      and WA.dans_horaires(ag, datetime(2026, 10, 26, 23, 30, tzinfo=UTC)) is False)
check("G5.7 aucun jour : toujours faux", WA.dans_horaires({**ag, "horaires": {**ag["horaires"], "jours": []}}, mar) is False)
check("G5.8 heure d'été : 08:00 UTC en juillet = 10:00 Paris -> vrai", WA.dans_horaires(ag, datetime(2026, 7, 14, 8, 0, tzinfo=UTC)) is True)
check("G5.9 date naïve lue comme UTC", WA.dans_horaires(ag, datetime(2026, 10, 27, 9, 0)) is True)

print("\n[G6] lever_stop")
TEL, BS = "tel:33612345678", "bsuid:FR.ABC123"
T0 = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
WA.noter_accord(cid, TEL, "entrant", T0)
WA.noter_entrant(cid, {"id": "m1", "from": "33612345678", "from_user_id": "FR.ABC123", "type": "text",
                       "text": {"body": "STOP"}}, T0)
e = WA.etat(cid)
check("G6.0 départ : STOP posé sur l'identité ET l'alias", TEL in e["stops"] and BS in e["stops"]
      and e["alias"].get(TEL) == BS, e)
T1 = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
check("G6.1 source vide refusée, rien ne change", leve(ValueError, lambda: WA.lever_stop(cid, TEL, ""))
      and leve(ValueError, lambda: WA.lever_stop(cid, TEL, "   ")) and TEL in WA.etat(cid)["stops"])
check("G6.2 identité invalide refusée", leve(ValueError, lambda: WA.lever_stop(cid, "n'importe quoi", "message")))
WA.lever_stop(cid, TEL, "message client « réabonne-moi »", T1)
e = WA.etat(cid)
check("G6.3 l'identité ET son alias n'ont plus de STOP", TEL not in e["stops"] and BS not in e["stops"], e["stops"])
check("G6.4 accord SAISI daté, source reabonnement:<source>",
      e["accords"][TEL] == {"date": "2026-10-27T09:00:00+00:00", "source": "reabonnement:message client « réabonne-moi »"}, e["accords"])
WA.lever_stop(cid, BS, "x" * 80, T1)
check("G6.5 source tronquée à 50 caractères après le préfixe", WA.etat(cid)["accords"][BS]["source"] == "reabonnement:" + "x" * 50,
      WA.etat(cid)["accords"][BS])
check("G6.6 lever un STOP absent : sans erreur, accord posé", (WA.lever_stop(cid, "tel:33699999999", "formulaire", T1),
                                                                WA.etat(cid)["accords"]["tel:33699999999"]["source"])[1] == "reabonnement:formulaire")
check("G6.7 compte inconnu -> KeyError", leve(KeyError, lambda: WA.lever_stop("c00000000", TEL, "x")))
check("G6.8 un STOP reçu après la levée vaut de nouveau", (WA.noter_entrant(cid, {"id": "m2", "from": "33612345678", "type": "text",
                                                                                   "text": {"body": "stop"}}, T1),
                                                           TEL in WA.etat(cid)["stops"])[1])
WA.lever_stop(cid, TEL, "formulaire", T1)

print("\n[G7] routes")
APPELS_KAPSO.clear()
rg = c.get(f"/api/whatsapp/{cid}/etat?espace={boite}")
j = rg.json() if rg.status_code == 200 else {}
check("G7.1 GET /etat 200 : état du numéro + réglages t310 + agent", rg.status_code == 200 and j.get("agent") == WA.reglages(boite)["agent"]
      and "accords" in j and j.get("plafond_mois") == 1000 and "journal" in j, rg.text[:300])
check("G7.2 aucune clé `texte` nulle part dans /etat", "texte" not in set(cles(j)) and "text" not in set(cles(j)), sorted(set(cles(j))))
sans_numero = CP.creer({"espace_id": boite, "plateforme": "whatsapp"})["id"]
check("G7.3 /etat sans ?espace= : 200 aussi ; autre espace : 404 ; compte inconnu : 404 ; compte sans numéro : 400",
      c.get(f"/api/whatsapp/{cid}/etat").status_code == 200
      and c.get(f"/api/whatsapp/{cid}/etat?espace={autre}").status_code == 404
      and c.get("/api/whatsapp/c00000000/etat").status_code == 404
      and c.get(f"/api/whatsapp/{sans_numero}/etat").status_code == 400)
rr = c.get(f"/api/espaces/{boite}/whatsapp/reglages")
check("G7.4 GET réglages 200 = reglages(eid)", rr.status_code == 200 and rr.json() == WA.reglages(boite), rr.text[:200])
check("G7.5 GET réglages espace inconnu 404", c.get("/api/espaces/nope/whatsapp/reglages").status_code == 404)
rp = c.put(f"/api/espaces/{boite}/whatsapp/reglages", json={"agent": {"actif": True, "roles": ["faq"]}})
check("G7.6 PUT partiel 200 -> réglages complets, rangés", rp.status_code == 200 and rp.json()["agent"]["actif"] is True
      and rp.json()["agent"]["roles"] == ["faq"] and rp.json()["agent"]["horaires"] == DEFAUT["horaires"]
      and rp.json()["plafond_mois"] == 1000 and WA.reglages(boite) == rp.json(), rp.text[:300])
rp2 = c.put(f"/api/espaces/{boite}/whatsapp/reglages", json={"plafond_mois": 500})
check("G7.7 PUT d'un champ d'espace garde l'agent", rp2.status_code == 200 and rp2.json()["plafond_mois"] == 500
      and rp2.json()["agent"]["actif"] is True, rp2.text[:200])
b400 = c.put(f"/api/espaces/{boite}/whatsapp/reglages", json={"agent": {"mode": "libre"}})
check("G7.8 PUT hors bornes -> 400, rien n'a bougé", b400.status_code == 400 and WA.reglages(boite) == rp2.json(), b400.text[:200])
check("G7.9 PUT espace inconnu -> 404 ; corps non objet -> 400, rien d'écrit",
      c.put(f"/api/espaces/{boite}/whatsapp/reglages", json=[1]).status_code == 400
      and c.put(f"/api/espaces/{boite}/whatsapp/reglages", json="x").status_code == 400
      and WA.reglages(boite)["plafond_mois"] == 500 and
      c.put("/api/espaces/nope/whatsapp/reglages", json={"plafond_mois": 5}).status_code == 404)
c.put(f"/api/espaces/{boite}/whatsapp/reglages", json={"plafond_mois": 1000, "agent": {"actif": False, "roles": []}})
WA.noter_stop(cid, TEL)
rl = c.post(f"/api/whatsapp/{cid}/stop/lever?espace={boite}", json={"identite": TEL, "source": "message client"})
check("G7.10 POST stop/lever 200 {ok:true}, STOP retiré, accord reabonnement:",
      rl.status_code == 200 and rl.json() == {"ok": True} and TEL not in WA.etat(cid)["stops"]
      and WA.etat(cid)["accords"][TEL]["source"] == "reabonnement:message client", rl.text)
check("G7.11 source vide / identité invalide -> 400 ; compte inconnu, autre espace -> 404",
      c.post(f"/api/whatsapp/{cid}/stop/lever", json={"identite": TEL, "source": ""}).status_code == 400
      and c.post(f"/api/whatsapp/{cid}/stop/lever", json={"identite": "zzz", "source": "x"}).status_code == 400
      and c.post("/api/whatsapp/c00000000/stop/lever", json={"identite": TEL, "source": "x"}).status_code == 404
      and c.post(f"/api/whatsapp/{cid}/stop/lever?espace={autre}", json={"identite": TEL, "source": "x"}).status_code == 404)
dist = TestClient(app, client=("203.0.113.9", 50000))
dist.__enter__()
codes = [dist.get(f"/api/whatsapp/{cid}/etat").status_code, dist.get(f"/api/espaces/{boite}/whatsapp/reglages").status_code,
         dist.put(f"/api/espaces/{boite}/whatsapp/reglages", json={"plafond_mois": 5}).status_code,
         dist.post(f"/api/whatsapp/{cid}/stop/lever", json={"identite": TEL, "source": "x"}).status_code]
check("G7.12 hors boucle locale : /etat, GET et PUT réglages, stop/lever refusés (401/403), rien n'a bougé",
      all(x in (401, 403) for x in codes) and WA.reglages(boite)["plafond_mois"] == 1000, codes)
check("G7.13 aucun appel à Kapso, nulle part", APPELS_KAPSO == [], APPELS_KAPSO)

print("\n[G8] fichiers de l'espace et clés inconnues")
check("G8.1 whatsapp_brouillons.json est un fichier d'espace", "whatsapp_brouillons.json" in E.FICHIERS
      and "whatsapp.json" in E.FICHIERS, E.FICHIERS)
d = doc_wa(boite)
d["reglages"]["agent"]["inconnu_futur"] = {"a": 1}
d["reglages"]["inconnu_espace"] = 5
(_tmp / "espaces" / boite / "whatsapp.json").write_text(json.dumps(d), encoding="utf-8")
WA.regler_espace(boite, {"agent": {"actif": True}})
d2 = doc_wa(boite)
check("G8.2 une clé inconnue déjà en place (agent ou espace) survit à un réglage", d2["reglages"]["agent"].get("inconnu_futur") == {"a": 1}
      and d2["reglages"].get("inconnu_espace") == 5 and "inconnu_futur" not in WA.reglages(boite)["agent"], d2)
(_tmp / "espaces" / boite / "whatsapp.json").write_text(json.dumps({"reglages": {"agent": {"mode": "nimporte", "roles": "x",
                                                                                          "plafond_jour_contact": 999}}}), encoding="utf-8")
check("G8.3 un agent abîmé sur disque est relu complété par les défauts", WA.reglages(boite)["agent"] == DEFAUT, WA.reglages(boite))

print("\n[G9] relecture : reglages() ne touche jamais espaces.lire() ; écriture sans effet ; débuts et fins ; nuit")
vrai_lire = E.lire


def lire_interdit(*a, **k):
    raise AssertionError("espaces.lire() appelé")


E.lire = lire_interdit
try:
    check("G9.1 reglages(eid) sans espaces.lire() (espace connu, et id valide sans fichier)",
          WA.reglages(boite)["agent"] == WA.reglages(boite)["agent"] and WA.reglages("zz-sans-fichier")["agent"] == DEFAUT)
    check("G9.2 id invalide -> KeyError, toujours sans lire()", leve(KeyError, lambda: WA.reglages("../x")))
finally:
    E.lire = vrai_lire
check("G9.3 reglages(eid) d'un espace inconnu : GET route 404 (la route vérifie)", c.get("/api/espaces/nope/whatsapp/reglages").status_code == 404)
f = _tmp / "espaces" / boite / "whatsapp.json"
WA.regler_espace(boite, {"plafond_mois": 321})
m1, o1 = f.stat().st_mtime_ns, f.read_bytes()
import time; time.sleep(0.05)
WA.regler_espace(boite, {"plafond_mois": 321, "agent": {"mode": WA.reglages(boite)["agent"]["mode"]}})
check("G9.4 réglage sans changement effectif : fichier non réécrit", f.stat().st_mtime_ns == m1 and f.read_bytes() == o1)
WA.regler_espace(boite, {"plafond_mois": 322})
check("G9.5 un vrai changement réécrit", f.stat().st_mtime_ns != m1 and WA.reglages(boite)["plafond_mois"] == 322)
vide = E.creer({"nom": "Atelier Vide"})["id"]
WA.regler_espace(vide, {"agent": {"mode": "brouillon", "horaires": {"debut": "09:00"}}})
check("G9.6 sur un espace sans fichier, un réglage égal aux défauts n'en crée pas",
      not (_tmp / "espaces" / vide / "whatsapp.json").exists())
check("G9.7 début == fin refusé (dont par fusion), rien d'écrit",
      refuse(boite, {"agent": {"horaires": {"debut": "10:00", "fin": "10:00"}}})
      and refuse(boite, {"agent": {"horaires": {"fin": "09:00"}}}))
WA.regler_espace(boite, {"agent": {"horaires": {"debut": "22:00", "fin": "06:00", "jours": [0, 1, 2, 3, 4]}}})
nuit = WA.reglages(boite)["agent"]
check("G9.8 plage de nuit 22:00-06:00 lun-ven : accepté ; mardi 23:00 Paris vrai, mardi 07:00 faux",
      WA.dans_horaires(nuit, datetime(2026, 10, 27, 22, 0, tzinfo=UTC)) is True
      and WA.dans_horaires(nuit, datetime(2026, 10, 27, 6, 0, tzinfo=UTC)) is False
      and WA.dans_horaires(nuit, datetime(2026, 10, 27, 4, 0, tzinfo=UTC)) is True and True)
check("G9.9 dans_horaires tolère un agent brut abîmé : champ par champ sur les défauts",
      WA.dans_horaires({}, mar) is True and WA.dans_horaires(None, mar) is True
      and WA.dans_horaires({"horaires": {"fuseau": "Nope/Zone", "debut": "zz", "jours": "x", "fin": 5}}, mar) is True
      and WA.dans_horaires({"horaires": {"jours": [1], "debut": "bad"}}, datetime(2026, 10, 28, 9, 0, tzinfo=UTC)) is False
      and WA.dans_horaires("pas un dict", mar) is True)
WA.regler_espace(boite, {"agent": {"horaires": {"debut": "09:00", "fin": "18:00"}}})

print("\n[G10] /etat : le message de l'espace figure sous agent ; aucun texte de contact")
WA.regler_espace(boite, {"agent": {"message_hors_horaires": "Nous sommes fermés, à demain."}})
WA.noter_entrant(cid, {"id": "m9", "from": "33677777777", "type": "text", "text": {"body": "TEXTE-PRIVE-DU-CONTACT"}}, T1)
re_ = c.get(f"/api/whatsapp/{cid}/etat")
je = re_.json()
check("G10.1 message_hors_horaires de l'espace présent sous agent", je["agent"]["message_hors_horaires"] == "Nous sommes fermés, à demain.")
check("G10.2 aucune clé texte/text, et le texte du contact n'apparaît nulle part",
      "texte" not in set(cles(je)) and "text" not in set(cles(je)) and "TEXTE-PRIVE-DU-CONTACT" not in re_.text)
check("G10.3 le journal a des entrées et aucune n'a de clé texte", len(je["journal"]) > 0
      and all("texte" not in ent and "text" not in ent for ent in je["journal"]), je["journal"][-1:])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
