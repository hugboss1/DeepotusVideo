# -*- coding: utf-8 -*-
"""t321 (Compagnon M4, 26/11/2026) — WhatsApp vu et nourri par le téléphone : GET /api/sync/whatsapp (l'état des numéros)
et POST /api/sync/whatsapp (écriture PC n° 7 : accords saisis, STOP, envois). Aucun réseau (Kapso n'est jamais appelé).
Banc-miroir : vraies requêtes depuis une IP du réseau local avec un vrai jeton d'appareil, fichiers relus sur disque.
  T1  témoin : la base (9376e17e) n'a ni sync_whatsapp ni la route ouverte
  L1  sans jeton : 401 ; avec jeton : l'espace et son numéro, les accords / STOP / compteurs ; jamais le journal
  L2  le consentement du client responsable est dit (faux sans consentement, vrai après), l'espace sans numéro est absent
  E1  accord saisi + stop + envoi appliqués ; mêmes effets que noter_accord / noter_stop / noter_envoi (compteurs du mois)
  E2  renvoi identique : « deja », rien ne bouge ; même id autre contenu : « conflit », rien n'est écrasé
  E3  refus : source « entrant », genre inconnu, compte inconnu, identité invalide, date future, type inconnu
  E4  le STOP rejoint le registre des oppositions (espace sans client) ; un envoi d'espace archivé est refusé
  E5  plus de 200 événements : 413 ; corps sans liste : 400 ; la route est ouverte au Wi-Fi, ELLE SEULE de plus
  E6  les identifiants sont rangés PAR APPAREIL : un autre téléphone peut réutiliser le même id sans être « deja »
Run (depuis backend/) : & $PY tests/test_sync_whatsapp.py"""
import json, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsyncwa_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["KAPSO_API_KEY"] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "9376e17e"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_whatsapp.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 témoin : la base n'a ni sync_whatsapp ni /sync/whatsapp ouverte",
      r0.returncode != 0 and r1.returncode == 0 and b"/api/sync/whatsapp" not in r1.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402
from app.services import comptes as CP, espaces as E, fiche_client as FC, oppositions as OP  # noqa: E402
from app.services import whatsapp as WA                             # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
LAN = ("192.168.1.42", 50000)
NOW = datetime.now(timezone.utc).replace(microsecond=0)
ISO = lambda d: d.isoformat().replace("+00:00", "Z")               # noqa: E731


def js(r):
    try:
        return r.json()
    except Exception:                                               # noqa: BLE001
        return {}


def _refus_stop():
    try:
        WA.controler(cid, "tel:33600000002", type="modele", categorie="UTILITY", dernier_entrant=None, maintenant=NOW)
    except WA.WhatsappRefus as e:
        return e.code == "stop"
    return False


with TestClient(app, client=("127.0.0.1", 50001)) as loc:
    E.lire()
    marque = E.creer({"nom": "Atelier Soleil"})["id"]
    cid = CP.creer({"espace_id": marque, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": "PN-1", "WHATSAPP_WABA_ID": "WABA-1", "WHATSAPP_NUMERO": "+33 1 23"})
    client = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
    cidc = CP.creer({"espace_id": client, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cidc, {"WHATSAPP_PHONE_ID": "PN-2", "WHATSAPP_WABA_ID": "WABA-2"})
    vide = E.creer({"nom": "Sans numéro"})["id"]
    CP.creer({"espace_id": vide, "plateforme": "whatsapp"})
    WA.noter_accord(cid, "tel:33600000001", "formulaire")
    WA.noter_entrant(cid, {"from": "33600000002", "type": "text", "text": {"body": "Bonjour"}, "id": "wamid.A"})
    WA.noter_envoi(cid, "tel:33600000001", type="texte", categorie=None, statut="sent", id="wamid.S", maintenant=NOW)

    lan = TestClient(app, client=LAN)
    H = JA.entetes(app)
    H2 = JA.entetes(app, ip="192.168.1.43")

    print("[L] lecture")
    check("L1a sans jeton : 401", lan.get("/api/sync/whatsapp").status_code == 401)
    r = lan.get("/api/sync/whatsapp", headers=H)
    lu = js(r)
    esp = {e["espace_id"]: e for e in lu.get("espaces", [])}
    check("L1b 200, version 1, les deux espaces à numéro (pas celui sans numéro)",
          r.status_code == 200 and lu.get("version") == 1 and set(esp) == {marque, client}, r.text[:300])
    n1 = (esp.get(marque) or {}).get("numeros", [{}])[0]
    check("L1c numéro : cid, phone_number_id, waba_id, numéro public", n1.get("cid") == cid and n1.get("phone_number_id") == "PN-1"
          and n1.get("waba_id") == "WABA-1" and n1.get("numero") == "+33 1 23", str(n1)[:300])
    et = n1.get("etat") or {}
    mois = NOW.strftime("%Y-%m")
    check("L1d état : accord saisi, accord entrant, compteur du mois (1 sortant, 1 entrant), JAMAIS de journal",
          et.get("accords", {}).get("tel:33600000001", {}).get("source") == "formulaire"
          and et.get("accords", {}).get("tel:33600000002", {}).get("source") == "entrant"
          and et.get("compteur", {}).get(mois, {}).get("sortants") == 1 and et.get("compteur", {}).get(mois, {}).get("entrants") == 1
          and "journal" not in et and "Bonjour" not in r.text, str(et)[:300])
    check("L1e réglages de l'espace (plafond, marché, agent en brouillon) et total du mois (2)",
          esp[marque]["reglages"]["plafond_mois"] == WA.PLAFOND_DEFAUT and esp[marque]["reglages"]["agent"]["mode"] == "brouillon"
          and esp[marque]["total_mois"] == 2 and esp[marque]["mois"] == mois)
    check("L1f aucun secret ni clé Kapso dans la réponse", "KAPSO_API_KEY" not in r.text and "secret" not in r.text.lower())
    nc = esp[client]["numeros"][0]
    check("L2a espace client : client_responsable posé, consentement absent -> faux",
          esp[client]["client_responsable"] == client and nc["consentement_client"] is False
          and n1["consentement_client"] is True and esp[marque]["client_responsable"] is None)
    FC.ajouter_consentement(client, "whatsapp:PN-2", ["messages"], FC.MOYENS[0])
    nc = {e["espace_id"]: e for e in js(lan.get("/api/sync/whatsapp", headers=H))["espaces"]}[client]["numeros"][0]
    check("L2b après le consentement daté du client : vrai", nc["consentement_client"] is True)

    print("\n[E] écriture n° 7")
    evs = [{"id": "ev-acc-1", "genre": "accord", "cid": cid, "identite": "tel:33600000009", "source": "papier", "quand": ISO(NOW)},
           {"id": "ev-stop-1", "genre": "stop", "cid": cid, "identite": "tel:33600000002", "quand": ISO(NOW)},
           {"id": "ev-env-1", "genre": "envoi", "cid": cid, "identite": "tel:33600000001", "type": "texte", "categorie": None,
            "statut": "sent", "wamid": "wamid.T1", "quand": ISO(NOW)},
           {"id": "ev-env-2", "genre": "envoi", "cid": cid, "identite": "tel:33600000009", "type": "modele", "categorie": "UTILITY",
            "statut": "accepted", "wamid": "wamid.T2", "quand": ISO(NOW)}]
    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": evs})
    b = js(r)
    check("E1a 200 : quatre appliqués", r.status_code == 200 and b.get("appliques") == ["ev-acc-1", "ev-stop-1", "ev-env-1", "ev-env-2"]
          and not b.get("refuses") and not b.get("deja"), r.text[:300])
    e = WA.etat(cid)
    check("E1b accord saisi préfixé telephone: (vaut pour le marketing : source ≠ entrant)",
          e["accords"]["tel:33600000009"]["source"] == "telephone:papier")
    check("E1c STOP rangé", "tel:33600000002" in e["stops"])
    check("E1d compteurs : sortants 1 + 2 = 3, service 1 + 1 = 2 (le modèle ne compte pas au service)",
          e["compteur"][mois]["sortants"] == 3 and e["compteur"][mois]["service"] == 2, str(e["compteur"]))
    check("E1e journal : deux sortants d'origine telephone, sans texte",
          [j.get("id") for j in e["journal"] if j.get("origine") == "telephone"] == ["wamid.T1", "wamid.T2"])
    check("E1f le contrôle du PC voit le STOP déposé par le téléphone", _refus_stop)

    avant = (E.chemin(marque, WA.FICHIER)).read_text(encoding="utf-8")
    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": evs})
    check("E2a renvoi identique : tous « deja », fichier inchangé",
          js(r).get("deja") == [x["id"] for x in evs] and not js(r).get("appliques")
          and (E.chemin(marque, WA.FICHIER)).read_text(encoding="utf-8") == avant, r.text[:200])
    autre = dict(evs[0], source="oral")
    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": [autre]})
    check("E2b même id, autre contenu : « conflit », rien n'est écrasé",
          js(r).get("conflits") == ["ev-acc-1"] and WA.etat(cid)["accords"]["tel:33600000009"]["source"] == "telephone:papier")

    mauvais = [{"id": "x1", "genre": "accord", "cid": cid, "identite": "tel:33600000010", "source": "entrant", "quand": ISO(NOW)},
               {"id": "x2", "genre": "entrant", "cid": cid, "identite": "tel:33600000010", "quand": ISO(NOW)},
               {"id": "x3", "genre": "stop", "cid": "inconnu", "identite": "tel:33600000010", "quand": ISO(NOW)},
               {"id": "x4", "genre": "stop", "cid": cid, "identite": "33600000010", "quand": ISO(NOW)},
               {"id": "x5", "genre": "stop", "cid": cid, "identite": "tel:33600000010", "quand": ISO(NOW + timedelta(days=1))},
               {"id": "x6", "genre": "envoi", "cid": cid, "identite": "tel:33600000010", "type": "video", "statut": "sent", "quand": ISO(NOW)},
               {"id": "x 7", "genre": "stop", "cid": cid, "identite": "tel:33600000010", "quand": ISO(NOW)}]
    avant = (E.chemin(marque, WA.FICHIER)).read_text(encoding="utf-8")
    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": mauvais})
    check("E3 sept refus (entrant, genre, compte, identité, futur, type, id) et rien n'est écrit",
          r.status_code == 200 and len(js(r).get("refuses", [])) == 7 and not js(r).get("appliques")
          and (E.chemin(marque, WA.FICHIER)).read_text(encoding="utf-8") == avant, r.text[:400])

    check("E4a le STOP (espace sans client) est au registre des oppositions",
          lambda: OP.oppose(["tel:33600000002"]))
    E.archiver(marque)
    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": [dict(evs[2], id="ev-env-arch")]})
    check("E4b espace archivé : un envoi est refusé, rien n'est appliqué",
          len(js(r).get("refuses", [])) == 1 and not js(r).get("appliques"), r.text[:200])
    E.archiver(marque, False)

    r = lan.post("/api/sync/whatsapp", headers=H, json={"evenements": [evs[1]] * 201})
    check("E5a plus de 200 : 413", r.status_code == 413)
    check("E5b corps sans liste : 400", lan.post("/api/sync/whatsapp", headers=H, json={}).status_code == 400)
    check("E5c sans jeton : 401", lan.post("/api/sync/whatsapp", json={"evenements": []}).status_code == 401)
    base_ouv = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent)).stdout
    check("E5d la route est ouverte au Wi-Fi, ELLE SEULE de plus que la base (22 = 21 + 1)",
          ("POST", "/api/sync/whatsapp") in _MAIN._ECRITURES_OUVERTES and len(_MAIN._ECRITURES_OUVERTES) == 22
          and b'("POST", "/api/agent/campagnes/{cid}/depot")})' in base_ouv, str(len(_MAIN._ECRITURES_OUVERTES)))

    r = lan.post("/api/sync/whatsapp", headers=H2, json={"evenements": [dict(evs[0], identite="tel:33600000011")]})
    check("E6 un autre appareil, même id : appliqué (les ids sont rangés par appareil)", js(r).get("appliques") == ["ev-acc-1"], r.text[:200])



print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
