# -*- coding: utf-8 -*-
"""t310 tâche 6 (27/10/2026) — B1 WhatsApp via Kapso : lecture et envoi, sous les règles (routes /api/whatsapp/{cid}/*).
Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md (tâche 6, Review Focus 1, 2 et 4), spec §6.1 (Coûts Meta,
Identité) et §6.3. Routes réelles (TestClient), data-dir et sqlite temporaires, AUCUN réseau : `kapso._requete` est un faux
Kapso (proxy WhatsApp et Platform) qui compte ses appels et ÉCHOE la clé et un `download_url` à jeton dans ses erreurs.
Ce que ce banc garde :
  W1  envoi texte dans la fenêtre : un POST Kapso (`to`, texte), une ligne `Depense` (catégorie whatsapp, espace,
      rattachée au wamid), journal sans texte, compteurs sortants/service ; marché = indicatif le plus long de la grille.
  W2  chaque `WhatsappRefus` -> 409 {message, code} : consentement, stop, accord, fenetre, marketing,
      bsuid_authentification, plafond, prix ; aucun envoi Kapso, aucune dépense, rien au compteur.
      Refus sans réseau du tout : consentement, stop, accord, plafond (pré-contrôle avant toute lecture chez Kapso).
  W3  plafond en dollars de l'espace dépassé -> 402 `dz_plafond` inchangé, aucun envoi.
  W4  grille vide -> 409 `prix`, aucun envoi.
  W5  `marketing_preference_stopped` (422) -> désinscription notée, dépense remise à 0, rien au compteur ; le second
      envoi marketing est refusé AVANT Kapso ; 131050 idem ; préférence Kapso `marketing_allowed: false` lue avant un
      modèle marketing -> refus, désinscription notée, aucun envoi.
  W6  131047 -> 409 `fenetre`, jamais renvoyé en texte libre (un seul POST), dépense à 0.
  W7  lecture : messages à plat {id, identite, sens, type, texte, quand, statut, media_id?} ; un entrant « STOP » -> stop
      noté, l'envoi suivant refusé ; un entrant relu deux fois n'est journalisé qu'une fois ; curseur `suivant`.
  W8  conversations {id, identite, nom, dernier_entrant, fenetre_ouverte, stop} ; modèles approuvés seulement
      {nom, langue, categorie, parametres nommes|positionnels, n_parametres}.
  W9  boutons (1 à 3 titres de 20 caractères au plus, ids b1..b3) et modèle (paramètres positionnels ou nommés, corps
      seulement) : forme exacte du corps Kapso ; envoi invalide -> 400 sans aucun appel.
  W10 BSUID seul (RF 4) : envoi par `recipient`, marché par défaut ; modèle d'authentification refusé.
  W11 RF 1 : un 502 dont le corps porte la clé et un `download_url` à jeton -> réponse nettoyée (envoi et média).
  W12 médias : octets rendus avec le type du fournisseur, rien sur disque.
  W13 accords et stop par route ; erreurs : compte inconnu 404, compte non whatsapp 404, autre espace 404, hors boucle
      locale refusé.
  W14 RF 2 : POST /api/schedule avec un compte whatsapp en cible -> 400.
  W15 deux envois simultanés sous un plafond mensuel de 1 : un seul part (verrou du compte).
Run (depuis backend/) : & $PY tests/test_whatsapp_routes.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwarou_"))
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
JOURNAL = []
logger.add(lambda m: JOURNAL.append(str(m)), level="DEBUG")

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


from datetime import datetime, timedelta, timezone                  # noqa: E402
from fastapi.testclient import TestClient                            # noqa: E402
from sqlalchemy import select                                        # noqa: E402
from app.config import settings                                      # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import comptes as CP, espaces as E, kapso as KA, pricing as PR  # noqa: E402
from app.services import whatsapp as WA                              # noqa: E402
from app.services.storage import Depense, async_session_factory     # noqa: E402

CLE = "CLE-KAPSO-SECRETE-77"
JETON = "JETON-MEDIA-SECRET-99"
TXT = "Bonjour, voici le TEXTE-PRIVE-DU-MESSAGE"
PL, PX = KA.PLATFORM, KA.PROXY


def poser_cle(v):
    os.environ["KAPSO_API_KEY"] = v
    setattr(settings, "KAPSO_API_KEY", v)


def maintenant():
    return datetime.now(timezone.utc)


def iso(d):
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ---- le faux Kapso ----------------------------------------------------------------------------------------------------
class Faux:
    def __init__(self):
        self.appels = []              # (méthode, chemin sans hôte, params)
        self.envois = []              # corps des POST /messages (hors accusés de lecture)
        self.convs = {}               # pid -> [conversation brute]
        self.msgs = {}                # pid -> [pages de messages bruts] (page 0 = la plus récente)
        self.modeles = {}             # waba -> [modèle brut]
        self.prefs = {}               # contact -> liste brute (absent = 404 « Marketing preference not found »)
        self.refus_envoi = []         # [(statut, corps)] rendus aux prochains POST /messages
        self.media = {}               # media_id -> (octets, mime)
        self.refus_media = None


F = Faux()


async def faux_requete(methode, url, *, json=None, params=None):
    await asyncio.sleep(0)            # rend la main : deux envois simultanés s'entrelacent vraiment
    chemin = url.replace(PX, "").replace(PL, "").replace(f"https://{KA.HOTE}", "").split("?")[0]
    F.appels.append((methode, chemin, dict(params or {})))
    parts = chemin.strip("/").split("/")
    if methode == "POST" and len(parts) == 2 and parts[1] == "messages":
        if (json or {}).get("status") == "read":
            return 200, {"success": True}, {}
        F.envois.append(json)
        if F.refus_envoi:
            st, corps = F.refus_envoi.pop(0)
            return st, corps, {}
        return 200, {"messaging_product": "whatsapp", "messages": [{"id": f"wamid.ENVOI{len(F.envois)}"}]}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "conversations":
        return 200, {"data": [dict(x) for x in F.convs.get(parts[0], [])], "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "messages":
        pages = F.msgs.get(parts[0], [[]])
        i = int((params or {}).get("after") or 0)
        page = pages[i] if i < len(pages) else []
        apres = str(i + 1) if i + 1 < len(pages) else None
        return 200, {"data": [dict(x) for x in page], "paging": {"cursors": {"after": apres} if apres else {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "message_templates":
        return 200, {"data": [dict(x) for x in F.modeles.get(parts[0], [])], "paging": {}}, {}
    if methode == "GET" and chemin.startswith("/whatsapp/contacts/") and chemin.endswith("/marketing_preferences"):
        contact = chemin.split("/")[3]
        if contact in F.prefs:
            return 200, {"data": F.prefs[contact]}, {}
        return 404, {"error": "Marketing preference not found"}, {}
    if methode == "GET" and parts[0] == "dl":
        mid = parts[1]
        octets, mime = F.media[mid]
        return 200, octets, {"content-type": mime}
    if methode == "GET" and len(parts) == 1 and parts[0] in F.media:
        if F.refus_media:
            st, corps = F.refus_media
            F.refus_media = None
            return st, corps, {}
        return 200, {"id": parts[0], "mime_type": F.media[parts[0]][1],
                     "download_url": f"https://api.kapso.ai/dl/{parts[0]}?token={JETON}"}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


async def faux_dormir(_s):
    return None


KA._requete = faux_requete
KA._dormir = faux_dormir


def envois_kapso():
    return [a for a in F.appels if a[0] == "POST" and a[1].endswith("/messages")]


async def _depenses():
    async with async_session_factory() as s:
        return list((await s.execute(select(Depense))).scalars().all())


def depenses():
    return asyncio.run(_depenses())


def compte(eid, pid, waba="WABA-1"):
    cid_ = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    CP.poser_publics_serveur(cid_, {"WHATSAPP_PHONE_ID": pid, "WHATSAPP_WABA_ID": waba})
    return cid_


def conv(pid, *, tel=None, bsuid=None, il_y_a=timedelta(hours=1), nom="Client"):
    F.convs.setdefault(pid, []).append({
        "id": f"conv-{len(F.convs[pid]) + 1}", "phone_number": tel, "business_scoped_user_id": bsuid, "status": "active",
        "kapso": {"contact_name": nom, "last_inbound_at": iso(maintenant() - il_y_a) if il_y_a is not None else None}})


def envoyer(cid_, ident, envoi, **kw):
    return c.post(f"/api/whatsapp/{cid_}/envoyer", json={"identite": ident, "envoi": envoi}, **kw)


def code409(r):
    try:
        d = r.json()["detail"]
        return r.status_code == 409 and d.get("code"), d
    except Exception:                                       # noqa: BLE001
        return None, r.text


GRILLE = {"1": {"marketing": 0.025, "utility": 0.004, "authentication": 0.004, "service": 0.003},
          "33": {"marketing": 0.0859, "utility": 0.0300, "authentication": 0.0300, "service": 0.0100},
          "336": {"marketing": 0.09, "utility": 0.031, "authentication": 0.031, "service": 0.0111}}
MODELES = [
    {"id": "t1", "name": "promo_automne", "language": "fr", "status": "APPROVED", "category": "MARKETING",
     "components": [{"type": "BODY", "text": "Bonjour {{1}}, -{{2}} % ce week-end"}]},
    {"id": "t2", "name": "rappel_rdv", "language": "fr", "status": "APPROVED", "category": "UTILITY",
     "components": [{"type": "HEADER", "format": "TEXT", "text": "Rappel"},
                    {"type": "BODY", "text": "Bonjour {{prenom}}, rendez-vous le {{date}}",
                     "example": {"body_text_named_params": [{"param_name": "prenom", "example": "Léa"},
                                                            {"param_name": "date", "example": "lundi"}]}}]},
    {"id": "t3", "name": "code_connexion", "language": "fr", "status": "APPROVED", "category": "AUTHENTICATION",
     "components": [{"type": "BODY", "text": "Votre code : {{1}}"}]},
    {"id": "t4", "name": "brouillon", "language": "fr", "status": "PENDING", "category": "MARKETING",
     "components": [{"type": "BODY", "text": "pas encore"}]},
]

c = TestClient(app, client=("127.0.0.1", 50000))
c.__enter__()
E.lire()
poser_cle(CLE)
PR.save({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0})

boite = E.creer({"nom": "Atelier Soleil"})["id"]
cid = compte(boite, "PN-1")
F.modeles["WABA-1"] = MODELES
TEL = "tel:33612345678"
WA.noter_accord(cid, TEL, "formulaire")
conv("PN-1", tel="+33 6 12 34 56 78", nom="Léa")

print("\n[W1] envoi texte dans la fenêtre")
F.appels.clear()
r = envoyer(cid, TEL, {"type": "texte", "texte": TXT})
check("W1.1 200", r.status_code == 200, r.text)
j = r.json() if r.status_code == 200 else {}
check("W1.2 réponse {id, statut, devis}", set(j) == {"id", "statut", "devis"} and j["id"] == "wamid.ENVOI1"
      and j["statut"] == "accepted", j)
check("W1.3 un seul POST Kapso, vers le numéro du compte", len(envois_kapso()) == 1
      and envois_kapso()[0][1] == "/PN-1/messages", F.appels)
check("W1.4 corps Kapso : to, type text, texte", F.envois[-1] == {"messaging_product": "whatsapp", "to": "33612345678",
                                                                   "type": "text", "text": {"body": TXT}}, F.envois[-1])
check("W1.5 marché = indicatif le plus long de la grille (336), catégorie service",
      j.get("devis", {}).get("breakdown", [{}])[0].get("label") == "WhatsApp service (336)"
      and abs(j["devis"]["total_usd"] - 0.0111) < 1e-9, j.get("devis"))
dd = depenses()
check("W1.6 une ligne Depense : catégorie whatsapp, moteur meta, espace, rattachée au wamid",
      len(dd) == 1 and dd[0].categorie == "whatsapp" and dd[0].moteur == "meta" and dd[0].espace_id == boite
      and dd[0].ref == "wamid.ENVOI1" and dd[0].op == "whatsapp" and abs(dd[0].estime_usd - 0.0111) < 1e-9,
      [(d.categorie, d.moteur, d.espace_id, d.ref) for d in dd])
e = WA.etat(cid)
mois = maintenant().strftime("%Y-%m")
check("W1.7 compteur : 1 sortant, 1 service", e["compteur"].get(mois) == {"sortants": 1, "service": 1}, e["compteur"])
dern = e["journal"][-1] if e["journal"] else {}
check("W1.8 journal : sortant texte service, id du message, sans le texte",
      dern.get("sens") == "sortant" and dern.get("type") == "texte" and dern.get("categorie") == "service"
      and dern.get("id") == "wamid.ENVOI1" and TXT not in json.dumps(e), dern)
check("W1.9 la clé n'est ni dans la réponse ni dans whatsapp.json",
      CLE not in r.text and CLE not in (_tmp / "espaces" / boite / "whatsapp.json").read_text(encoding="utf-8"))
F.appels.clear()
r = envoyer(cid, TEL, {"type": "texte", "texte": "deux"})
j2 = r.json() if r.status_code == 200 else {}
check("W1.10 second envoi : 2 au compteur, service_deja_mois compté (toujours payant, seuil 0)",
      r.status_code == 200 and WA.etat(cid)["compteur"][mois] == {"sortants": 2, "service": 2}, r.text)
PR.save({"whatsapp_service_gratuits_mois": 1000})
r = envoyer(cid, TEL, {"type": "texte", "texte": "trois"})
check("W1.11 sous le seuil des 1 000 gratuits : devis 0, aucune ligne Depense de plus",
      r.status_code == 200 and r.json()["devis"]["total_usd"] == 0 and len(depenses()) == 2, (r.text, len(depenses())))
PR.save({"whatsapp_service_gratuits_mois": 0})

print("\n[W2] chaque WhatsappRefus -> 409, aucun envoi, aucune dépense")


def refus_sans_trace(label, cid_, ident, envoi, code_attendu, sans_reseau=False):
    F.appels.clear()
    n_dep, cpt = len(depenses()), json.dumps(WA.etat(cid_)["compteur"])
    r_ = envoyer(cid_, ident, envoi)
    code_, det = code409(r_)
    check(f"{label} 409 code {code_attendu}", code_ == code_attendu and isinstance(det, dict) and det.get("message"),
          (r_.status_code, det))
    check(f"{label} aucun envoi Kapso, aucune dépense, compteur intact",
          not envois_kapso() and len(depenses()) == n_dep and json.dumps(WA.etat(cid_)["compteur"]) == cpt,
          (F.appels, len(depenses())))
    if sans_reseau:
        check(f"{label} aucun appel Kapso du tout", F.appels == [], F.appels)


# consentement : espace client, numéro relié, aucun consentement en cours
lune = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
cl = compte(lune, "PN-CL")
WA.noter_accord(cl, TEL, "formulaire")
conv("PN-CL", tel="33612345678")
refus_sans_trace("W2.1 consentement :", cl, TEL, {"type": "texte", "texte": "x"}, "consentement", sans_reseau=True)
# stop
WA.noter_accord(cid, "tel:33611111111", "papier")
WA.noter_stop(cid, "tel:33611111111")
conv("PN-1", tel="33611111111")
refus_sans_trace("W2.2 stop :", cid, "tel:33611111111", {"type": "texte", "texte": "x"}, "stop", sans_reseau=True)
# accord
conv("PN-1", tel="33622222222")
refus_sans_trace("W2.3 accord :", cid, "tel:33622222222", {"type": "texte", "texte": "x"}, "accord", sans_reseau=True)
# fenetre : dernier entrant il y a 30 h
WA.noter_accord(cid, "tel:33633333333", "papier")
conv("PN-1", tel="33633333333", il_y_a=timedelta(hours=30))
refus_sans_trace("W2.4 fenetre :", cid, "tel:33633333333", {"type": "texte", "texte": "x"}, "fenetre")
# fenetre : aucune conversation, aucun message entrant connu
WA.noter_accord(cid, "tel:33644444444", "papier")
refus_sans_trace("W2.5 fenetre (jamais d'entrant) :", cid, "tel:33644444444", {"type": "boutons", "texte": "x",
                 "boutons": ["Oui"]}, "fenetre")
# marketing (désinscrit noté chez nous)
WA.noter_accord(cid, "tel:33655555555", "papier")
WA.noter_desinscription(cid, "tel:33655555555")
refus_sans_trace("W2.6 marketing :", cid, "tel:33655555555",
                 {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["Léa", "20"]}, "marketing")
# bsuid_authentification
BS = "bsuid:FR.ABCDEF123"
WA.noter_accord(cid, BS, "entrant")
refus_sans_trace("W2.7 bsuid_authentification :", cid, BS,
                 {"type": "modele", "nom": "code_connexion", "langue": "fr", "parametres": ["123456"]},
                 "bsuid_authentification")
# plafond mensuel de messages
cp = compte(E.creer({"nom": "Plafond messages"})["id"], "PN-P")
WA.noter_accord(cp, TEL, "papier")
conv("PN-P", tel="33612345678")
WA.regler(cp, plafond_mois=0)
refus_sans_trace("W2.8 plafond :", cp, TEL, {"type": "texte", "texte": "x"}, "plafond", sans_reseau=True)

print("\n[W3] plafond en dollars de l'espace -> 402 dz_plafond")
ep = E.creer({"nom": "Plafond dollars"})["id"]
cd = compte(ep, "PN-D")
WA.noter_accord(cd, TEL, "papier")
conv("PN-D", tel="33612345678")
E.modifier(ep, {"plafond_usd": 0.001})
F.appels.clear()
n_dep = len(depenses())
r = envoyer(cd, TEL, {"type": "texte", "texte": "x"})
det = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else {}
check("W3.1 402 avec dz_plafond motif espace", r.status_code == 402 and isinstance(det, dict)
      and det.get("dz_plafond", {}).get("motif") == "espace", r.text)
check("W3.2 aucun envoi, aucune dépense, compteur vide", not envois_kapso() and len(depenses()) == n_dep
      and not WA.etat(cd)["compteur"], F.appels)

print("\n[W4] grille vide -> 409 prix")
PR.save({"whatsapp_meta_usd": {}})
refus_sans_trace("W4.1 prix :", cid, TEL, {"type": "texte", "texte": "x"}, "prix")
PR.save({"whatsapp_meta_usd": GRILLE})

print("\n[W5] désinscription marketing de Meta")
MK = "tel:33677777777"
WA.noter_accord(cid, MK, "papier")
F.refus_envoi.append((422, {"error": "Contact stopped marketing messages on this WhatsApp number",
                            "code": "marketing_preference_stopped"}))
F.appels.clear()
n_dep = len(depenses())
cpt = json.dumps(WA.etat(cid)["compteur"])
r = envoyer(cid, MK, {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["Léa", "20"]})
code_, det = code409(r)
check("W5.1 409 marketing", code_ == "marketing", (r.status_code, det))
check("W5.2 préférence lue AVANT l'envoi (Platform), puis un seul POST",
      [a[1] for a in F.appels if "marketing_preferences" in a[1] or (a[0] == "POST" and a[1].endswith("/messages"))]
      == ["/whatsapp/contacts/33677777777/marketing_preferences", "/PN-1/messages"], F.appels)
check("W5.3 désinscription notée", MK in WA.etat(cid)["desinscrits_marketing"], WA.etat(cid)["desinscrits_marketing"])
nd = depenses()
check("W5.4 la réservation est remise à 0 (réel 0) ; compteur intact",
      len(nd) == n_dep + 1 and nd[-1].reel_usd == 0.0 and json.dumps(WA.etat(cid)["compteur"]) == cpt,
      [(d.estime_usd, d.reel_usd) for d in nd[n_dep:]])
refus_sans_trace("W5.5 second envoi marketing refusé avant Kapso :", cid, MK,
                 {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["Léa", "20"]}, "marketing")
# le service reste permis : un modèle utility part
F.appels.clear()
r = envoyer(cid, MK, {"type": "modele", "nom": "rappel_rdv", "langue": "fr",
                      "parametres": {"prenom": "Léa", "date": "lundi"}})
check("W5.6 un modèle utility part encore", r.status_code == 200 and len(envois_kapso()) == 1, r.text)
# 131050 (forme proxy Meta)
M2 = "tel:33688888888"
WA.noter_accord(cid, M2, "papier")
F.refus_envoi.append((400, {"error": {"message": "(#131050) User has opted out of marketing", "type": "OAuthException",
                                      "code": 131050}}))
r = envoyer(cid, M2, {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["A", "1"]})
check("W5.7 131050 -> 409 marketing, désinscription notée", code409(r)[0] == "marketing"
      and M2 in WA.etat(cid)["desinscrits_marketing"], r.text)
# préférence Kapso : arrêtée sur ce numéro -> refus avant l'envoi
M3 = "tel:33699999999"
WA.noter_accord(cid, M3, "papier")
F.prefs["33699999999"] = [{"phone_number_id": "PN-AUTRE", "status": "resumed", "marketing_allowed": True},
                          {"phone_number_id": "PN-1", "status": "stopped", "marketing_allowed": False}]
refus_sans_trace("W5.8 préférence Kapso arrêtée :", cid, M3,
                 {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["A", "1"]}, "marketing")
check("W5.9 … et la désinscription est notée", M3 in WA.etat(cid)["desinscrits_marketing"])

print("\n[W6] 131047 -> fenetre, jamais renvoyé en texte libre")
WA.noter_accord(cid, "tel:33612000000", "papier")
conv("PN-1", tel="33612000000")
F.refus_envoi.append((422, {"error": {"message": "(#131047) Re-engagement message", "type": "OAuthException",
                                      "code": 131047}}))
F.appels.clear()
n_dep = len(depenses())
r = envoyer(cid, "tel:33612000000", {"type": "texte", "texte": "x"})
check("W6.1 409 fenetre", code409(r)[0] == "fenetre", r.text)
check("W6.2 un seul POST (aucun renvoi)", len(envois_kapso()) == 1, F.appels)
nd = depenses()
check("W6.3 dépense remise à 0, rien au journal des sortants pour ce contact",
      len(nd) == n_dep + 1 and nd[-1].reel_usd == 0.0
      and not [x for x in WA.etat(cid)["journal"] if x["identite"] == "tel:33612000000"], nd[-1].reel_usd if nd else None)

print("\n[W7] lecture des messages")
cl2 = compte(E.creer({"nom": "Lecture"})["id"], "PN-L")
T_IN = int((maintenant() - timedelta(minutes=10)).timestamp())
F.msgs["PN-L"] = [
    [{"id": "wamid.IN3", "timestamp": str(T_IN + 120), "type": "text", "from": "33600000003", "text": {"body": "STOP"},
      "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "c3"}},
     {"id": "wamid.OUT1", "timestamp": str(T_IN + 60), "type": "text", "to": "33600000002",
      "text": {"body": "Réponse"}, "kapso": {"direction": "outbound", "status": "delivered",
                                             "whatsapp_conversation_id": "c2"}}],
    [{"id": "wamid.IN2", "timestamp": str(T_IN + 30), "type": "image", "from": "33600000002", "from_user_id": "FR.L2",
      "image": {"id": "MEDIA-1", "mime_type": "image/jpeg"},
      "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "c2", "has_media": True}},
     {"id": "wamid.IN1", "timestamp": str(T_IN), "type": "text", "from": "33600000002", "from_user_id": "FR.L2",
      "text": {"body": "Bonjour"}, "kapso": {"direction": "inbound", "status": "received",
                                             "whatsapp_conversation_id": "c2"}}],
]
r = c.get(f"/api/whatsapp/{cl2}/messages")
j = r.json() if r.status_code == 200 else {}
check("W7.1 200, première page et curseur suivant", r.status_code == 200 and len(j.get("messages", [])) == 2
      and j.get("suivant") == "1", r.text)
m0 = (j.get("messages") or [{}])[0]
check("W7.2 message à plat : id, identite, sens, type, texte, quand, statut",
      m0 == {"id": "wamid.IN3", "identite": "tel:33600000003", "sens": "entrant", "type": "text", "texte": "STOP",
             "quand": datetime.fromtimestamp(T_IN + 120, timezone.utc).isoformat(timespec="seconds"),
             "statut": "received"}, m0)
m1 = (j.get("messages") or [{}, {}])[1]
check("W7.3 sortant : identité du destinataire, sens sortant", m1.get("identite") == "tel:33600000002"
      and m1.get("sens") == "sortant" and m1.get("texte") == "Réponse", m1)
check("W7.4 STOP noté par la lecture", "tel:33600000003" in WA.etat(cl2)["stops"], WA.etat(cl2)["stops"])
r = c.get(f"/api/whatsapp/{cl2}/messages", params={"apres": "1"})
j = r.json() if r.status_code == 200 else {}
mi = (j.get("messages") or [{}])[0]
check("W7.5 page suivante : média avec media_id, BSUID d'abord, plus de curseur",
      mi.get("media_id") == "MEDIA-1" and mi.get("identite") == "bsuid:FR.L2" and mi.get("type") == "image"
      and j.get("suivant") is None, j)
e = WA.etat(cl2)
check("W7.6 un entrant vaut accord (BSUID et numéro liés)", "bsuid:FR.L2" in e["accords"] and "tel:33600000002" in e["accords"],
      e["accords"])
n_j = len(e["journal"])
c.get(f"/api/whatsapp/{cl2}/messages")
c.get(f"/api/whatsapp/{cl2}/messages", params={"apres": "1"})
check("W7.7 relu deux fois : journalisé une fois", len(WA.etat(cl2)["journal"]) == n_j == 3, (n_j, WA.etat(cl2)["journal"]))
check("W7.8 le texte des messages n'est jamais rangé", "Bonjour" not in json.dumps(WA.etat(cl2)), "")
conv("PN-L", tel="33600000003", il_y_a=timedelta(minutes=8))
F.appels.clear()
r = envoyer(cl2, "tel:33600000003", {"type": "texte", "texte": "encore ?"})
check("W7.9 l'envoi suivant au contact STOP est refusé, sans envoi", code409(r)[0] == "stop" and not envois_kapso(), r.text)
r = c.get(f"/api/whatsapp/{cl2}/messages", params={"depuis": "2026-10-01T00:00:00Z"})
check("W7.10 depuis= passe en `since` chez Kapso",
      any(a[2].get("since") == "2026-10-01T00:00:00Z" for a in F.appels if a[1] == "/PN-L/messages"), F.appels[-1:])
# dernier entrant tiré des messages quand la conversation ne le donne pas
F.convs["PN-L"] = []
F.msgs["PN-L"] = [[{"id": "wamid.IN9", "timestamp": str(int((maintenant() - timedelta(hours=2)).timestamp())),
                    "type": "text", "from": "33600000009", "text": {"body": "salut"},
                    "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "c9"}}]]
WA.noter_accord(cl2, "tel:33600000009", "papier")
r = envoyer(cl2, "tel:33600000009", {"type": "texte", "texte": "bonjour"})
check("W7.11 sans last_inbound_at : le dernier entrant des messages ouvre la fenêtre", r.status_code == 200, r.text)

print("\n[W8] conversations et modèles")
r = c.get(f"/api/whatsapp/{cid}/conversations")
lst = r.json() if r.status_code == 200 else []
lea = next((x for x in lst if x.get("identite") == TEL), {})
check("W8.1 conversation à plat", r.status_code == 200 and set(lea) == {"id", "identite", "nom", "dernier_entrant",
                                                                      "fenetre_ouverte", "stop"}
      and lea["nom"] == "Léa" and lea["fenetre_ouverte"] is True and lea["stop"] is False and lea["dernier_entrant"], lea)
vieux = next((x for x in lst if x.get("identite") == "tel:33633333333"), {})
st = next((x for x in lst if x.get("identite") == "tel:33611111111"), {})
check("W8.2 fenêtre fermée à 30 h ; stop vu", vieux.get("fenetre_ouverte") is False and st.get("stop") is True, (vieux, st))
check("W8.3 conversations lues avec fields=kapso()",
      any(a[2].get("fields") == "kapso()" for a in F.appels if a[1].endswith("/conversations")), "")
r = c.get(f"/api/whatsapp/{cid}/modeles")
mods = r.json() if r.status_code == 200 else []
check("W8.4 approuvés seulement", r.status_code == 200 and [m["nom"] for m in mods]
      == ["promo_automne", "rappel_rdv", "code_connexion"], mods)
check("W8.5 forme {nom, langue, categorie, parametres, n_parametres}",
      mods and mods[0] == {"nom": "promo_automne", "langue": "fr", "categorie": "marketing", "parametres": "positionnels",
                           "n_parametres": 2}
      and mods[1]["parametres"] == "nommes" and mods[1]["n_parametres"] == 2 and mods[1]["categorie"] == "utility", mods)

print("\n[W9] boutons et modèles : forme exacte ; envoi invalide -> 400")
F.appels.clear()
r = envoyer(cid, TEL, {"type": "boutons", "texte": "On confirme ?", "boutons": ["Oui", "Non", "Plus tard"]})
check("W9.1 boutons : 200", r.status_code == 200, r.text)
check("W9.2 corps interactif, ids b1..b3", F.envois[-1] == {
    "messaging_product": "whatsapp", "to": "33612345678", "type": "interactive",
    "interactive": {"type": "button", "body": {"text": "On confirme ?"}, "action": {"buttons": [
        {"type": "reply", "reply": {"id": "b1", "title": "Oui"}}, {"type": "reply", "reply": {"id": "b2", "title": "Non"}},
        {"type": "reply", "reply": {"id": "b3", "title": "Plus tard"}}]}}}, F.envois[-1])
r = envoyer(cid, TEL, {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": ["Léa", 20]})
check("W9.3 modèle positionnel : composant body, paramètres dans l'ordre", r.status_code == 200 and F.envois[-1] == {
    "messaging_product": "whatsapp", "to": "33612345678", "type": "template",
    "template": {"name": "promo_automne", "language": {"code": "fr"}, "components": [
        {"type": "body", "parameters": [{"type": "text", "text": "Léa"}, {"type": "text", "text": "20"}]}]}},
    (r.text, F.envois[-1]))
check("W9.4 modèle marketing : catégorie de prix marketing", r.json()["devis"]["breakdown"][0]["label"]
      == "WhatsApp marketing (336)", r.text)
r = envoyer(cid, TEL, {"type": "modele", "nom": "rappel_rdv", "langue": "fr", "parametres": {"prenom": "Léa", "date": "lundi"}})
check("W9.5 modèle nommé : parameter_name", r.status_code == 200 and F.envois[-1]["template"]["components"] == [
    {"type": "body", "parameters": [{"type": "text", "parameter_name": "prenom", "text": "Léa"},
                                    {"type": "text", "parameter_name": "date", "text": "lundi"}]}], F.envois[-1])
journ = WA.etat(cid)["journal"][-1]
check("W9.6 journal du modèle : type modele, catégorie utility", journ["type"] == "modele"
      and journ["categorie"] == "utility", journ)
F.appels.clear()
mauvais = [
    {"type": "boutons", "texte": "x", "boutons": []},
    {"type": "boutons", "texte": "x", "boutons": ["a", "b", "c", "d"]},
    {"type": "boutons", "texte": "x", "boutons": ["un titre bien trop long ici"]},
    {"type": "boutons", "texte": "x", "boutons": [""]},
    {"type": "texte", "texte": ""},
    {"type": "texte"},
    {"type": "fax", "texte": "x"},
    {"type": "modele", "nom": "", "langue": "fr"},
    {"type": "modele", "nom": "promo_automne", "langue": "fr", "parametres": "Léa"},
    "pas un dict",
]
codes = [envoyer(cid, TEL, m).status_code for m in mauvais]
codes.append(c.post(f"/api/whatsapp/{cid}/envoyer", json={"identite": "33612345678",
                                                           "envoi": {"type": "texte", "texte": "x"}}).status_code)
check("W9.7 envois invalides (et identité invalide) : 400", codes == [400] * len(codes), codes)
check("W9.8 … sans aucun appel Kapso", F.appels == [], F.appels)
r = envoyer(cid, TEL, {"type": "modele", "nom": "inconnu", "langue": "fr", "parametres": []})
check("W9.9 modèle inconnu ou non approuvé : 400, aucun envoi", r.status_code == 400 and not envois_kapso(), r.text)
r = envoyer(cid, TEL, {"type": "modele", "nom": "brouillon", "langue": "fr", "parametres": []})
check("W9.10 modèle en attente (PENDING) : 400, aucun envoi", r.status_code == 400 and not envois_kapso(), r.text)

print("\n[W10] BSUID seul (RF 4)")
conv("PN-1", bsuid="FR.ABCDEF123", tel=None)
F.appels.clear()
r = envoyer(cid, BS, {"type": "texte", "texte": "bonjour"})
check("W10.1 envoi par recipient, jamais to", r.status_code == 200 and F.envois[-1].get("recipient") == "FR.ABCDEF123"
      and "to" not in F.envois[-1], (r.text, F.envois[-1:]))
check("W10.2 marché par défaut (33)", r.json()["devis"]["breakdown"][0]["label"] == "WhatsApp service (33)", r.text)
WA.regler(cid, marche_defaut="1")
r = envoyer(cid, BS, {"type": "texte", "texte": "hello"})
check("W10.3 marché par défaut réglé (1)", r.status_code == 200
      and r.json()["devis"]["breakdown"][0]["label"] == "WhatsApp service (1)", r.text)
r = envoyer(cid, "tel:4477001122", {"type": "texte", "texte": "x"})   # aucun accord : refus, mais le marché ne compte pas
WA.noter_accord(cid, "tel:4477001122", "papier")
conv("PN-1", tel="+44 7700 1122")
r = envoyer(cid, "tel:4477001122", {"type": "texte", "texte": "x"})
check("W10.4 numéro hors grille : marché par défaut", r.status_code == 200
      and r.json()["devis"]["breakdown"][0]["label"] == "WhatsApp service (1)", r.text)
WA.regler(cid, marche_defaut="33")

print("\n[W11] RF 1 : 502 nettoyé (clé, download_url à jeton)")
F.refus_envoi.append((500, {"error": {"message": f"panne interne cle={CLE} voir https://api.kapso.ai/dl/x?token={JETON}",
                                      "type": "Internal", "code": "panne_kapso"}}))
JOURNAL.clear()
n_dep = len(depenses())
cpt = json.dumps(WA.etat(cid)["compteur"])
r = envoyer(cid, TEL, {"type": "texte", "texte": "x"})
d = r.json().get("detail") if r.status_code == 502 else {}
check("W11.1 envoi : 502 {message, code}", r.status_code == 502 and isinstance(d, dict) and d.get("code") == "panne_kapso"
      and d.get("message"), r.text)
check("W11.2 ni la clé ni le jeton dans la réponse ni dans le journal",
      CLE not in r.text and JETON not in r.text and not any(CLE in x or JETON in x for x in JOURNAL), r.text)
check("W11.3 5xx (issue incertaine) : réservation GARDÉE (réel vide), compteur intact",
      depenses()[-1].reel_usd is None and len(depenses()) == n_dep + 1 and json.dumps(WA.etat(cid)["compteur"]) == cpt,
      depenses()[-1].reel_usd)
check("W11.3b … et une ligne au journal : chemin et type seulement",
      any("issue incertaine" in x and "/PN-1/messages" in x and "KapsoErreur" in x for x in JOURNAL), JOURNAL[-3:])
F.media["MEDIA-X"] = (b"x", "image/png")
F.refus_media = (404, {"error": {"message": f"introuvable {CLE} download_url=https://api.kapso.ai/dl/y?token={JETON}",
                                 "code": 100}})
r = c.get(f"/api/whatsapp/{cid}/medias/MEDIA-X")
check("W11.4 média : 502 nettoyé", r.status_code == 502 and CLE not in r.text and JETON not in r.text, r.text)
check("W11.5 rien dans les fichiers de l'espace", all(CLE not in f.read_text(encoding="utf-8", errors="ignore")
                                                      and JETON not in f.read_text(encoding="utf-8", errors="ignore")
                                                      for f in (_tmp / "espaces").rglob("*.json")), "")

print("\n[W12] médias")
OCTETS = b"\xff\xd8\xff-OCTETS-MEDIA-UNIQUES-\x00\x01"
F.media["MEDIA-1"] = (OCTETS, "image/jpeg")
avant = {p for p in _tmp.rglob("*") if p.is_file()}
r = c.get(f"/api/whatsapp/{cid}/medias/MEDIA-1")
check("W12.1 octets rendus, type du fournisseur", r.status_code == 200 and r.content == OCTETS
      and r.headers.get("content-type", "").startswith("image/jpeg"), (r.status_code, r.headers.get("content-type")))
apres = {p for p in _tmp.rglob("*") if p.is_file()}
check("W12.2 aucun fichier neuf ne garde les octets", not any(OCTETS in p.read_bytes() for p in apres - avant)
      and not any(OCTETS in p.read_bytes() for p in apres if p.suffix != ".db"), sorted(str(p) for p in apres - avant))
check("W12.3 identifiant de média invalide : 400", c.get(f"/api/whatsapp/{cid}/medias/a%20b").status_code == 400, "")

print("\n[W13] accords, stop, erreurs")
r = c.post(f"/api/whatsapp/{cid}/accords", json={"identite": "tel:33601010101", "source": "formulaire"})
check("W13.1 accord noté", r.status_code == 200 and WA.etat(cid)["accords"].get("tel:33601010101", {}).get("source")
      == "formulaire", r.text)
r = c.post(f"/api/whatsapp/{cid}/accords", json={"identite": "tel:33601010101"})
check("W13.2 accord sans source : 400", r.status_code == 400, r.text)
r = c.post(f"/api/whatsapp/{cid}/stop", json={"identite": "tel:33601010101"})
check("W13.3 stop noté", r.status_code == 200 and "tel:33601010101" in WA.etat(cid)["stops"], r.text)
r = c.post(f"/api/whatsapp/{cid}/stop", json={"identite": "n'importe"})
check("W13.4 stop identité invalide : 400", r.status_code == 400, r.text)
check("W13.5 compte inconnu : 404", c.get("/api/whatsapp/inconnu/conversations").status_code == 404
      and envoyer("inconnu", TEL, {"type": "texte", "texte": "x"}).status_code == 404, "")
tg = CP.creer({"espace_id": boite, "plateforme": "telegram"})["id"]
check("W13.6 compte non whatsapp : 404", c.get(f"/api/whatsapp/{tg}/modeles").status_code == 404
      and envoyer(tg, TEL, {"type": "texte", "texte": "x"}).status_code == 404, "")
check("W13.7 autre espace que celui demandé : 404",
      c.get(f"/api/whatsapp/{cid}/conversations", params={"espace": lune}).status_code == 404
      and c.post(f"/api/whatsapp/{cid}/envoyer?espace={lune}", json={"identite": TEL, "envoi": {"type": "texte",
                                                                                                  "texte": "x"}}).status_code == 404
      and c.get(f"/api/whatsapp/{cid}/conversations", params={"espace": boite}).status_code == 200, "")
nr = compte(boite, "")
check("W13.8 compte non relié : 400", c.get(f"/api/whatsapp/{nr}/conversations").status_code == 400, "")
dehors = TestClient(app, client=("10.0.0.9", 50000))
codes = [dehors.get(f"/api/whatsapp/{cid}/conversations").status_code,
         dehors.get(f"/api/whatsapp/{cid}/messages").status_code,
         dehors.get(f"/api/whatsapp/{cid}/modeles").status_code,
         dehors.get(f"/api/whatsapp/{cid}/medias/MEDIA-1").status_code,
         dehors.post(f"/api/whatsapp/{cid}/envoyer", json={"identite": TEL, "envoi": {"type": "texte", "texte": "x"}}).status_code,
         dehors.post(f"/api/whatsapp/{cid}/accords", json={"identite": TEL, "source": "x"}).status_code,
         dehors.post(f"/api/whatsapp/{cid}/stop", json={"identite": TEL}).status_code]
check("W13.9 hors boucle locale : refusé (401/403) partout", all(x in (401, 403) for x in codes), codes)

print("\n[W14] RF 2 : un compte whatsapp n'est pas une cible de post")
r = c.post("/api/schedule", json={"title": "t", "caption": "c", "run_at": "2026-12-01T10:00:00Z", "espace_id": boite,
                                  "comptes": [cid]})
check("W14.1 POST /api/schedule avec un compte whatsapp : 400", r.status_code == 400, r.text)

print("\n[W15] deux envois simultanés sous un plafond de 1 message")
from app.services import whatsapp_echanges as WE                    # noqa: E402
es = E.creer({"nom": "Simultané"})["id"]
cs = compte(es, "PN-S")
WA.noter_accord(cs, TEL, "papier")
conv("PN-S", tel="33612345678")
WA.regler(cs, plafond_mois=1)
F.appels.clear()


async def _deux():
    return await asyncio.gather(WE.envoyer(cs, TEL, {"type": "texte", "texte": "a"}),
                                WE.envoyer(cs, TEL, {"type": "texte", "texte": "b"}), return_exceptions=True)

res = asyncio.run(_deux())
oks = [x for x in res if isinstance(x, dict)]
refs = [x for x in res if isinstance(x, WA.WhatsappRefus)]
check("W15.1 un envoi part, l'autre est refusé « plafond »", len(oks) == 1 and len(refs) == 1 and refs[0].code == "plafond",
      res)
check("W15.2 un seul POST Kapso, compteur à 1", len([a for a in envois_kapso() if a[1] == "/PN-S/messages"]) == 1
      and WA.etat(cs)["compteur"][mois]["sortants"] == 1, F.appels)

print("\n[W17] fix 1 : un STOP jamais lu dans l'écran bloque l'envoi")
ex = E.creer({"nom": "Stop non lu"})["id"]
cx = compte(ex, "PN-X")
T_X = str(int((maintenant() - timedelta(minutes=5)).timestamp()))
WA.noter_accord(cx, "tel:33600000071", "papier")
conv("PN-X", tel="33600000071", il_y_a=timedelta(minutes=5))
F.msgs["PN-X"] = [[{"id": "wamid.X1", "timestamp": T_X, "type": "text", "from": "33600000071", "text": {"body": "Stop !"},
                    "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "x1"}}]]
F.appels.clear()
r = envoyer(cx, "tel:33600000071", {"type": "texte", "texte": "bonjour"})
check("W17.1 STOP seulement chez Kapso : 409 stop, aucun POST", code409(r)[0] == "stop" and not envois_kapso(), r.text)
check("W17.2 … et le STOP est rangé", "tel:33600000071" in WA.etat(cx)["stops"], WA.etat(cx)["stops"])
r = envoyer(cx, "tel:33600000071", {"type": "modele", "nom": "rappel_rdv", "langue": "fr",
                                     "parametres": {"prenom": "A", "date": "B"}})
check("W17.3 un modèle aussi est refusé", code409(r)[0] == "stop" and not envois_kapso(), r.text)
# STOP sous le BSUID, envoi vers le numéro lié (le message porte from et from_user_id)
WA.noter_accord(cx, "tel:33600000072", "papier")
conv("PN-X", tel="33600000072", il_y_a=timedelta(minutes=5))
F.msgs["PN-X"] = [[{"id": "wamid.X2", "timestamp": T_X, "type": "text", "from": "33600000072", "from_user_id": "FR.X72",
                    "text": {"body": "STOP"},
                    "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "x2"}},
                   {"id": "wamid.X1", "timestamp": T_X, "type": "text", "from": "33600000071", "text": {"body": "Stop !"},
                    "kapso": {"direction": "inbound", "status": "received", "whatsapp_conversation_id": "x1"}}]]
F.appels.clear()
r = envoyer(cx, "tel:33600000072", {"type": "texte", "texte": "bonjour"})
check("W17.4 STOP sous le BSUID lié : 409 stop pour le numéro, aucun POST", code409(r)[0] == "stop" and not envois_kapso(),
      r.text)
check("W17.5 X1 déjà journalisé n'est pas rejournalisé",
      len([x for x in WA.etat(cx)["journal"] if x.get("id") == "wamid.X1"]) == 1, WA.etat(cx)["journal"])
# entrant sans id : ignoré (jamais journalisé, jamais doublé) ; dates d'accord dans l'ordre chronologique
cy = compte(E.creer({"nom": "Sans id"})["id"], "PN-Y")
t1 = int((maintenant() - timedelta(hours=3)).timestamp())
F.msgs["PN-Y"] = [[{"id": "wamid.Y2", "timestamp": str(t1 + 60), "type": "text", "from": "33600000081", "text": {"body": "re"},
                    "kapso": {"direction": "inbound"}},
                   {"timestamp": str(t1 + 30), "type": "text", "from": "33600000082", "text": {"body": "STOP"},
                    "kapso": {"direction": "inbound"}},
                   {"id": "wamid.Y1", "timestamp": str(t1), "type": "text", "from": "33600000081", "text": {"body": "salut"},
                    "kapso": {"direction": "inbound"}}]]
c.get(f"/api/whatsapp/{cy}/messages")
c.get(f"/api/whatsapp/{cy}/messages")
ey = WA.etat(cy)
check("W17.6 entrant sans id ignoré ; les deux autres journalisés une fois, du plus ancien au plus récent",
      [x["id"] for x in ey["journal"]] == ["wamid.Y1", "wamid.Y2"] and "tel:33600000082" not in ey["stops"], ey["journal"])
check("W17.7 la date d'accord est celle du plus récent (jamais reculée)",
      ey["accords"]["tel:33600000081"]["date"] == datetime.fromtimestamp(t1 + 60, timezone.utc).isoformat(timespec="seconds"),
      ey["accords"])

print("\n[W16] garde des plafonds : la route d'envoi est recensée et gardée")
sys.path.insert(0, str(BACKEND / "tests"))
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("routes", "POST", "/whatsapp/{cid}/envoyer")
check("W16.1 la route d'envoi atteint un puits et appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"],
      rec.get(k))
src = (BACKEND / "app" / "services" / "whatsapp_echanges.py").read_text(encoding="utf-8")
corps = src[src.find("async def _envoyer_sous_verrou("):]
check("W16.2 dans le service : plafonds.verifier( précède kapso.envoyer(",
      0 < corps.find("plafonds.verifier(") < corps.find("kapso.envoyer("), "")

c.__exit__(None, None, None)
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
