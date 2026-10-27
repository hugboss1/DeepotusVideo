# -*- coding: utf-8 -*-
"""t310 tâche 3 (27/10/2026) — B1 WhatsApp via Kapso : liaison d'un numéro par LIEN D'INSTALLATION, et vérification.
Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md (tâche 3, Review Focus 3 et 5), spec §6.1 « Liaison d'un
numéro dans l'assistant ». Routes réelles (TestClient), data-dir et sqlite temporaires, AUCUN réseau : `kapso._requete` est
remplacé par un faux Kapso à états (customers, liens, numéros), qui compte ses appels.
Ce que ce banc garde :
  L1  espace client sans consentement daté (ou daté de travers) : 400, aucun appel à Kapso.
  L2  avec consentement : un customer puis un lien ; le `token` du lien n'est ni dans la réponse, ni dans whatsapp.json,
      ni dans comptes.json ; customer et facturation rangés dans le compte, liaison dans whatsapp.json.
  L3  second lien du même compte : customer réutilisé ; facturation différente : 400, aucun lien de plus.
  L4  `pending` : `en_cours`, rien n'est rangé ; au plus un `liens` et un `numeros` par relecture.
  L5  `failed` : `echouee`, erreur du fournisseur nettoyée (jeton, clé), rien n'est rangé.
  L6  numéro déjà porté par un autre compte : `echouee` (« déjà relié à l'espace X »), rien n'est rangé (RF 5).
  L7  `completed` : phone_id rangé, consentement `whatsapp:<id>` ajouté (espace client), vérification verte ; relecture
      suivante sans réseau, consentement jamais doublé ; un consentement qui court déjà ne fait pas échouer.
  L8  lien expiré (statut Kapso, ou date dépassée) : `expiree`.
  L9  clé Kapso absente : vérification orange `cle_kapso_absente`, sans réseau, GET /api/comptes 200 (RF 3).
  L10 espace Deepotus (non client) : aucun consentement exigé, aucun ajouté.
  L11 vérification : qualité YELLOW orange, RED rouge, numéro déconnecté rouge ; liaison en cours orange, échouée rouge.
  L12 erreurs : compte inconnu 404, compte non whatsapp 400, refus Kapso 502 {message, code} nettoyé, hors boucle locale
      refusé (401 sans jeton d'appareil, 403 sinon).
  L13 verif_canaux.CODES et les textes FR/EN des quatre codes neufs.
  Reprise 1 (revue de 162aaae6) :
  L14 deux liens, le client termine le PREMIER : terminee (le customer est propre au compte).
  L15 deux creer_lien simultanés sur un compte sans customer : un seul POST /customers (verrou par compte).
  L16 produit gouverné par un client (§11 bis) : consentement exigé ; ajouté sur la fiche DU CLIENT à la fin.
  L17 le premier « Vérifier » après la fin de liaison : vert, jamais `ecartee` (vérification pure) ; panne Kapso : orange.
  L18 convergence : consentement qui échoue une fois (OSError) -> rien de rangé, la relecture suivante l'ajoute ;
      une révocation n'est jamais défaite ; une autre ValueError de la fiche remonte (400), rien de rangé.
  L19 whatsapp.json : absent = {}, JSON illisible mis de côté, autre erreur de lecture levée (fichier jamais réécrit).
  L20 codes d'erreur de liaison (numero_deja_relie + espace, fournisseur, expire).
Run (depuis backend/) : & $PY tests/test_whatsapp_liaison.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwalia_"))
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
REPO = BACKEND.parent
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


from fastapi.testclient import TestClient                            # noqa: E402
from app.config import settings                                      # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import comptes as CP, espaces as E, fiche_client as FC, kapso as KA, verif_canaux as VC  # noqa: E402
from app.services import whatsapp as WA                              # noqa: E402

CLE = "CLE-KAPSO-SECRETE-42"
JETON = "JETON-SECRET-DU-LIEN"
PL = KA.PLATFORM


def poser_cle(v):
    os.environ["KAPSO_API_KEY"] = v
    setattr(settings, "KAPSO_API_KEY", v)


# ---- le faux Kapso à états --------------------------------------------------------------------------------------------
class Faux:
    def __init__(self):
        self.customers = []           # ids créés
        self.liens = {}               # customer_id -> [lien (dict brut), plus récent d'abord]
        self.numeros = {}             # customer_id -> [numéro brut]
        self.details = {}             # phone_number_id -> détail brut
        self.appels = []              # (méthode, chemin)
        self.refus = None             # (statut, corps) rendu au prochain POST setup_links

    def lien(self, cust, **maj):
        self.liens[cust][0].update(maj)


F = Faux()


async def faux_requete(methode, url, *, json=None, params=None):
    await asyncio.sleep(0)            # rend la main : deux gestes simultanés s'entrelacent vraiment
    chemin = url.replace(PL, "")
    F.appels.append((methode, chemin))
    if methode == "POST" and chemin == "/customers":
        cid = f"cust-{len(F.customers) + 1}"
        F.customers.append(cid)
        F.liens[cid] = []
        return 201, {"data": {"id": cid, "name": json["customer"]["name"],
                              "external_customer_id": json["customer"]["external_customer_id"]}}, {}
    if chemin.startswith("/customers/") and chemin.endswith("/setup_links"):
        cust = chemin.split("/")[2]
        if methode == "POST":
            if F.refus:
                st, corps = F.refus
                F.refus = None
                return st, corps, {}
            n = sum(len(v) for v in F.liens.values()) + 1
            brut = {"id": f"lien-{n}", "status": "active", "created_at": "2026-10-27T10:00:00Z",
                    "expires_at": "2099-11-26T10:00:00Z", "url": f"https://app.kapso.ai/setup/abc{n}", "token": JETON,
                    "meta_billing_mode": json["setup_link"]["meta_billing_mode"], "whatsapp_setup_status": "pending",
                    "whatsapp_setup_error": None}
            F.liens.setdefault(cust, []).insert(0, brut)
            return 201, {"data": dict(brut)}, {}
        return 200, {"data": [dict(x) for x in F.liens.get(cust, [])], "meta": {"page": 1}}, {}
    if chemin == "/whatsapp/phone_numbers":
        return 200, {"data": [dict(x) for x in F.numeros.get((params or {}).get("customer_id"), [])]}, {}
    if chemin.startswith("/whatsapp/phone_numbers/"):
        pid = chemin.rsplit("/", 1)[1]
        if pid in F.details:
            return 200, {"data": dict(F.details[pid])}, {}
        return 404, {"error": "Phone number not found"}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


async def faux_dormir(_s):
    return None


KA._requete = faux_requete
KA._dormir = faux_dormir


def numero_brut(pid, num="+33 6 00 00 00 01", nom="Boulangerie Lune", q="GREEN", st="CONNECTED", waba="WABA-1"):
    return {"id": pid, "phone_number_id": pid, "display_phone_number": num, "verified_name": nom,
            "quality_rating": q, "status": st, "business_account_id": waba}


def wa_json(eid):
    f = _tmp / "espaces" / eid / "whatsapp.json"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


def comptes_json():
    f = _tmp / "espaces" / "comptes.json"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


def publics(cid):
    return {ch["nom"]: ch.get("valeur") for ch in CP.obtenir(cid)["champs"]}


def nouveau_compte(eid):
    r = c.post("/api/comptes", json={"espace_id": eid, "plateforme": "whatsapp"})
    assert r.status_code == 200, r.text
    return r.json()["compte"]["id"]


def lien(cid, corps):
    return c.post(f"/api/comptes/{cid}/whatsapp/lien", json=corps)


def liaison(cid):
    return c.get(f"/api/comptes/{cid}/whatsapp/liaison")


def verifier(cid):
    return c.post(f"/api/comptes/{cid}/verifier")


CONS = {"moyen": "ecrit", "date": "2026-10-20"}

c = TestClient(app, client=("127.0.0.1", 50000))
c.__enter__()
E.lire()
poser_cle(CLE)
lune = E.creer({"nom": "Boulangerie Lune", "type": "client"})["id"]
autre = E.creer({"nom": "Atelier Soleil"})["id"]
cid = nouveau_compte(lune)

print("\n[L1] espace client : consentement daté exigé")
F.appels.clear()
r = lien(cid, {"facturation": "customer_managed"})
check("L1.1 sans consentement : 400", r.status_code == 400, r.text)
check("L1.2 message : consentement daté exigé", "consentement daté du client exigé avant la liaison" in r.text, r.text)
r2 = lien(cid, {"facturation": "customer_managed", "consentement": {"moyen": "ecrit", "date": "20/10/2026"}})
r3 = lien(cid, {"facturation": "customer_managed", "consentement": {"moyen": "pigeon", "date": "2026-10-20"}})
r4 = lien(cid, {"facturation": "customer_managed", "consentement": {"moyen": "ecrit", "date": "2026-02-31"}})
check("L1.3 date hors forme, moyen inconnu, date impossible : 400", (r2.status_code, r3.status_code, r4.status_code) == (400, 400, 400),
      (r2.text, r3.text, r4.text))
check("L1.4 aucun appel à Kapso, rien de rangé", F.appels == [] and not wa_json(lune) and not publics(cid)["KAPSO_CUSTOMER_ID"],
      F.appels)
r5 = lien(cid, {"facturation": "gratuit", "consentement": CONS})
check("L1.5 facturation inconnue : 400, aucun appel", r5.status_code == 400 and F.appels == [], r5.text)

print("\n[L2] lien créé avec consentement")
r = lien(cid, {"facturation": "customer_managed", "consentement": CONS, "langue": "en"})
check("L2.1 200", r.status_code == 200, r.text)
j = r.json() if r.status_code == 200 else {}
check("L2.2 réponse {url, expire_le, facturation}", set(j) == {"url", "expire_le", "facturation"}
      and j["url"] == "https://app.kapso.ai/setup/abc1" and j["expire_le"] == "2099-11-26T10:00:00Z"
      and j["facturation"] == "customer_managed", j)
check("L2.3 un customer créé (externe = l'espace), puis un lien",
      [a for a in F.appels] == [("POST", "/customers"), ("POST", "/customers/cust-1/setup_links")], F.appels)
check("L2.4 le token du lien absent de la réponse, de whatsapp.json, de comptes.json",
      JETON not in r.text and JETON not in wa_json(lune) and JETON not in comptes_json() and wa_json(lune))
check("L2.5 la clé Kapso absente de la réponse et des fichiers",
      CLE not in r.text and CLE not in wa_json(lune) and CLE not in comptes_json())
p = publics(cid)
check("L2.6 compte : KAPSO_CUSTOMER_ID et WHATSAPP_FACTURATION_META rangés, phone_id vide",
      p["KAPSO_CUSTOMER_ID"] == "cust-1" and p["WHATSAPP_FACTURATION_META"] == "customer_managed" and not p["WHATSAPP_PHONE_ID"], p)
doc = json.loads(wa_json(lune) or "{}")
li = ((doc.get("liaison") or {}).get(cid)) or {}
check("L2.7 whatsapp.json : liaison {lien_id, cree_le, expire_le, facturation, consentement}",
      li.get("lien_id") == "lien-1" and li.get("cree_le") and li.get("expire_le") == "2099-11-26T10:00:00Z"
      and li.get("facturation") == "customer_managed" and li.get("consentement") == CONS, doc)
check("L2.8 whatsapp.json passe par la liste blanche espaces.chemin", E.chemin(lune, "whatsapp.json") is not None
      and "whatsapp.json" in E.FICHIERS)

print("\n[L3] second lien, facturation figée")
F.appels.clear()
r = lien(cid, {"facturation": "customer_managed", "consentement": CONS})
check("L3.1 second lien : 200, customer réutilisé (aucun POST /customers)",
      r.status_code == 200 and F.appels == [("POST", "/customers/cust-1/setup_links")] and F.customers == ["cust-1"], (r.text, F.appels))
li = json.loads(wa_json(lune))["liaison"][cid]
check("L3.2 la liaison suit le lien le plus récent", li["lien_id"] == "lien-2", li)
F.appels.clear()
r = lien(cid, {"facturation": "partner_managed", "consentement": CONS})
check("L3.3 facturation différente : 400 « ne se change plus », aucun appel",
      r.status_code == 400 and "la facturation Meta ne se change plus" in r.text and F.appels == [], (r.text, F.appels))
check("L3.4 facturation du compte inchangée", publics(cid)["WHATSAPP_FACTURATION_META"] == "customer_managed")

print("\n[L4] pending : en cours, rien de rangé")
avant = comptes_json()
F.appels.clear()
r = liaison(cid)
check("L4.1 200, etat en_cours, erreur et numero nuls", r.status_code == 200
      and r.json() == {"etat": "en_cours", "erreur": None, "numero": None, "code": None}, r.text)
check("L4.2 rien de rangé (comptes.json identique)", comptes_json() == avant)
check("L4.3 un seul appel `liens`, aucun `numeros` (jamais de boucle)", F.appels == [("GET", "/customers/cust-1/setup_links")],
      F.appels)
F.lien("cust-1", whatsapp_setup_status="processing")
F.appels.clear()
for _ in range(3):
    r = liaison(cid)
check("L4.4 « processing » relu trois fois : toujours en_cours, trois appels en tout",
      r.json()["etat"] == "en_cours" and len(F.appels) == 3, (r.text, F.appels))
r = verifier(cid)
v = (r.json().get("compte") or {}).get("verification") or {}
check("L4.5 vérification : orange liaison_en_cours", v.get("etat") == "orange" and v.get("code") == "liaison_en_cours", v)

print("\n[L5] failed : échouée, erreur nettoyée")
F.lien("cust-1", whatsapp_setup_status="failed",
       whatsapp_setup_error=f"facebook_auth_failed : token={JETON} cle {CLE}")
avant = comptes_json()
r = liaison(cid)
j = r.json()
check("L5.1 etat echouee, erreur du fournisseur, code fournisseur", j.get("etat") == "echouee"
      and "facebook_auth_failed" in (j.get("erreur") or "") and j.get("code") == "fournisseur", j)
check("L5.2 erreur nettoyée (ni jeton ni clé)", JETON not in r.text and CLE not in r.text, r.text)
check("L5.3 rien de rangé", comptes_json() == avant)
r = verifier(cid)
v = (r.json().get("compte") or {}).get("verification") or {}
check("L5.4 vérification : rouge liaison_echouee, raison nettoyée", v.get("etat") == "rouge" and v.get("code") == "liaison_echouee"
      and "facebook_auth_failed" in v.get("raison", "") and JETON not in r.text and CLE not in r.text, v)

print("\n[L6] numéro déjà porté par un autre compte (Review Focus 5)")
cx = nouveau_compte(autre)
CP.poser_publics_serveur(cx, {"WHATSAPP_PHONE_ID": "PN-PRIS"})
F.lien("cust-1", whatsapp_setup_status="completed", whatsapp_setup_error=None, status="used")
F.numeros["cust-1"] = [numero_brut("PN-PRIS")]
avant = comptes_json()
F.appels.clear()
r = liaison(cid)
j = r.json()
check("L6.1 etat echouee, « déjà relié à l'espace Atelier Soleil »",
      j.get("etat") == "echouee" and "ce numéro est déjà relié à l'espace Atelier Soleil" in (j.get("erreur") or "")
      and j.get("code") == "numero_deja_relie" and j.get("espace") == "Atelier Soleil", j)
check("L6.2 rien de rangé : phone_id vide, comptes.json identique", comptes_json() == avant and not publics(cid)["WHATSAPP_PHONE_ID"])
check("L6.3 aucun consentement ajouté", FC.consentements_en_cours(lune) == [])
check("L6.4 un `liens` et un `numeros`, pas plus",
      F.appels == [("GET", "/customers/cust-1/setup_links"), ("GET", "/whatsapp/phone_numbers")], F.appels)

print("\n[L7] completed : numéro rangé, consentement, vérification verte")
F.numeros["cust-1"] = [numero_brut("PN-PRIS"), numero_brut("PN2", num="+33 6 11 22 33 44", waba="WABA-2")]
F.details["PN2"] = numero_brut("PN2", num="+33 6 11 22 33 44", waba="WABA-2")
r = liaison(cid)
j = r.json()
check("L7.1 etat terminee, numero PN2", j.get("etat") == "terminee" and j.get("erreur") is None
      and (j.get("numero") or {}).get("phone_number_id") == "PN2", j)
p = publics(cid)
check("L7.2 compte : WHATSAPP_PHONE_ID, WHATSAPP_NUMERO, WHATSAPP_WABA_ID rangés",
      p["WHATSAPP_PHONE_ID"] == "PN2" and p["WHATSAPP_NUMERO"] == "+33 6 11 22 33 44" and p["WHATSAPP_WABA_ID"] == "WABA-2", p)
cons = FC.consentements_en_cours(lune)
check("L7.3 consentement whatsapp:PN2, permis [messages], moyen de la liaison",
      len(cons) == 1 and cons[0]["canal_id"] == "whatsapp:PN2" and cons[0]["permis"] == ["messages"]
      and cons[0]["moyen"] == "ecrit", cons)
check("L7.4 l'autre compte garde son numéro", publics(cx)["WHATSAPP_PHONE_ID"] == "PN-PRIS")
r = verifier(cid)
vue = r.json().get("compte") or {}
v = vue.get("verification") or {}
check("L7.5 vérification verte : ok, id_distant PN2, nom vérifié", v.get("etat") == "vert" and v.get("code") == "ok"
      and v.get("id_distant") == "PN2" and v.get("nom_distant") == "Boulangerie Lune", v)
check("L7.6 canal_id whatsapp:PN2, compte disponible", vue.get("canal_id") == "whatsapp:PN2" and vue.get("disponible") is True, vue)
F.appels.clear()
r = liaison(cid)
check("L7.7 relecture suivante : terminee sans aucun appel réseau", r.json().get("etat") == "terminee" and F.appels == [],
      (r.text, F.appels))
check("L7.8 consentement jamais doublé", len(FC.consentements_en_cours(lune)) == 1)
check("L7.9 lien refusé une fois le numéro relié (400)",
      lien(cid, {"facturation": "customer_managed", "consentement": CONS}).status_code == 400)
check("L7.10 aucun jeton ni clé dans les fichiers", JETON not in wa_json(lune) + comptes_json()
      and CLE not in wa_json(lune) + comptes_json())
# un consentement qui court déjà sur le canal ne fait pas échouer la liaison
lune2 = E.creer({"nom": "Fromagerie Lune", "type": "client"})["id"]
c2 = nouveau_compte(lune2)
lien(c2, {"facturation": "customer_managed", "consentement": {"moyen": "whatsapp", "date": "2026-10-21"}})
cust2 = publics(c2)["KAPSO_CUSTOMER_ID"]
FC.ajouter_consentement(lune2, "whatsapp:PN3", ["messages"], "doigt")
F.lien(cust2, whatsapp_setup_status="completed")
F.numeros[cust2] = [numero_brut("PN3")]
r = liaison(c2)
check("L7.11 consentement déjà en cours : terminee quand même, un seul consentement",
      r.json().get("etat") == "terminee" and publics(c2)["WHATSAPP_PHONE_ID"] == "PN3"
      and len(FC.consentements_en_cours(lune2)) == 1, r.text)

print("\n[L8] lien expiré")
c3 = nouveau_compte(autre)
lien(c3, {"facturation": "partner_managed"})
cust3 = publics(c3)["KAPSO_CUSTOMER_ID"]
F.lien(cust3, status="expired")
r = liaison(c3)
check("L8.1 statut Kapso expired : expiree, code expire", r.json().get("etat") == "expiree"
      and r.json().get("code") == "expire", r.text)
F.lien(cust3, status="active")
fw = _tmp / "espaces" / autre / "whatsapp.json"
dw = json.loads(fw.read_text("utf-8"))
dw["liaison"][c3]["expire_le"] = "2020-01-01T00:00:00Z"          # la date rangée à la création du lien est passée
fw.write_text(json.dumps(dw), "utf-8")
r = liaison(c3)
check("L8.2 date d'expiration dépassée (Kapso encore « active ») : expiree", r.json().get("etat") == "expiree", r.text)
check("L8.3 rien de rangé", not publics(c3)["WHATSAPP_PHONE_ID"])
c4 = nouveau_compte(autre)
r = liaison(c4)
check("L8.4 aucun lien créé : etat aucune, sans réseau",
      r.json() == {"etat": "aucune", "erreur": None, "numero": None, "code": None}, r.text)

print("\n[L9] clé Kapso absente (Review Focus 3)")
poser_cle("")
F.appels.clear()
r = verifier(c3)
v = (r.json().get("compte") or {}).get("verification") or {}
check("L9.1 vérification orange cle_kapso_absente", r.status_code == 200 and v.get("etat") == "orange"
      and v.get("code") == "cle_kapso_absente", r.text)
r = verifier(cid)
v = (r.json().get("compte") or {}).get("verification") or {}
check("L9.2 même pour un compte relié", v.get("code") == "cle_kapso_absente", v)
check("L9.3 aucun appel réseau", F.appels == [], F.appels)
check("L9.4 GET /api/comptes répond 200", c.get("/api/comptes?espace=*").status_code == 200)
r = lien(c4, {"facturation": "customer_managed"})
check("L9.5 lien sans clé : 502 code cle_absente, aucun appel", r.status_code == 502
      and (r.json().get("detail") or {}).get("code") == "cle_absente" and F.appels == [], r.text)
poser_cle(CLE)

print("\n[L10] espace Deepotus : ni consentement exigé, ni ajouté")
cd = nouveau_compte("deepotus")
r = lien(cd, {"facturation": "customer_managed"})
check("L10.1 lien sans consentement : 200", r.status_code == 200, r.text)
check("L10.2 consentement null dans la liaison", json.loads(wa_json("deepotus"))["liaison"][cd]["consentement"] is None)
custd = publics(cd)["KAPSO_CUSTOMER_ID"]
F.lien(custd, whatsapp_setup_status="completed")
F.numeros[custd] = [numero_brut("PN-DZ", nom="Deepotus")]
r = liaison(cd)
check("L10.3 terminee, numéro rangé", r.json().get("etat") == "terminee" and publics(cd)["WHATSAPP_PHONE_ID"] == "PN-DZ", r.text)
check("L10.4 aucune fiche client écrite", not (_tmp / "espaces" / "deepotus" / "client.json").exists())

print("\n[L11] qualité du numéro")
for q, st, etat, code in (("YELLOW", "CONNECTED", "orange", "qualite_basse"), ("RED", "CONNECTED", "rouge", "qualite_basse"),
                          ("GREEN", "DISCONNECTED", "rouge", "refuse"), (None, "CONNECTED", "vert", "ok"),
                          # relecture finale (Minor 2) : casse indifférente ; rouge pour un mauvais statut CONNU,
                          # orange `indetermine` pour une valeur inconnue
                          ("GREEN", "connected", "vert", "ok"), ("GREEN", "flagged", "rouge", "refuse"),
                          ("GREEN", "Restricted", "rouge", "refuse"), ("GREEN", "BANNED", "rouge", "refuse"),
                          ("GREEN", "disconnected", "rouge", "refuse"), ("GREEN", "active", "orange", "indetermine"),
                          ("GREEN", "PENDING_REVIEW", "orange", "indetermine")):
    F.details["PN2"] = numero_brut("PN2", q=q, st=st)
    v = (verifier(cid).json().get("compte") or {}).get("verification") or {}
    check(f"L11 {q}/{st} : {etat} {code}", v.get("etat") == etat and v.get("code") == code, v)
F.details.pop("PN2")
v = (verifier(cid).json().get("compte") or {}).get("verification") or {}
check("L11.5 numéro inconnu chez Kapso (404) : orange, jamais une 500", v.get("etat") == "orange", v)

print("\n[L12] erreurs")
check("L12.1 compte inconnu : 404", lien("cdeadbeef", {"facturation": "customer_managed"}).status_code == 404
      and liaison("cdeadbeef").status_code == 404)
tg = c.post("/api/comptes", json={"espace_id": autre, "plateforme": "telegram"}).json()["compte"]["id"]
r = lien(tg, {"facturation": "customer_managed"})
check("L12.2 compte telegram : 400", r.status_code == 400 and "ce compte n'est pas un compte WhatsApp" in r.text, r.text)
check("L12.3 relecture d'un compte telegram : 400", liaison(tg).status_code == 400)
c5 = nouveau_compte(autre)
F.refus = (401, {"error": f"Invalid API key {CLE} token={JETON}", "code": "unauthorized"})
r = lien(c5, {"facturation": "customer_managed"})
d = r.json().get("detail") if r.status_code == 502 else {}
check("L12.4 refus Kapso : 502 {message, code}", r.status_code == 502 and isinstance(d, dict) and d.get("code") == "unauthorized"
      and "Invalid API key" in d.get("message", ""), r.text)
check("L12.5 refus nettoyé (ni clé ni jeton)", CLE not in r.text and JETON not in r.text, r.text)
check("L12.6 aucun lien rangé après le refus", c5 not in (json.loads(wa_json(autre) or "{}").get("liaison") or {}))
check("L12.7 customer gardé pour le prochain essai", bool(publics(c5)["KAPSO_CUSTOMER_ID"]))
dist = TestClient(app, client=("192.168.1.20", 50000))
F.appels.clear()
st = (dist.post(f"/api/comptes/{c5}/whatsapp/lien", json={"facturation": "customer_managed"}).status_code,
      dist.get(f"/api/comptes/{c5}/whatsapp/liaison").status_code)
check("L12.8 hors boucle locale : refusé (401 sans jeton / 403), aucun appel Kapso",
      all(s in (401, 403) for s in st) and F.appels == [], st)

print("\n[L13] codes et textes")
NEUFS = ("cle_kapso_absente", "liaison_en_cours", "liaison_echouee", "qualite_basse")
check("L13.1 verif_canaux.CODES porte les quatre codes neufs", all(x in VC.CODES for x in NEUFS), VC.CODES)
I18N = json.loads((REPO / "frontend" / "shared" / "i18n" / "espaces.json").read_text("utf-8"))
check("L13.2 textes FR et EN des quatre codes", all((I18N.get(f"espaces.assistant.code_{x}") or {}).get("fr", "").strip()
                                                    and (I18N.get(f"espaces.assistant.code_{x}") or {}).get("en", "").strip()
                                                    for x in NEUFS))
check("L13.3 whatsapp.FACTURATIONS", __import__("app.services.whatsapp", fromlist=["x"]).FACTURATIONS
      == ("customer_managed", "partner_managed"))

print("\n[L14] deux liens, le client termine le premier")
c6 = nouveau_compte(autre)
lien(c6, {"facturation": "customer_managed"})
lien(c6, {"facturation": "customer_managed"})
cust6 = publics(c6)["KAPSO_CUSTOMER_ID"]
check("L14.1 deux liens chez Kapso, la liaison suit le dernier", len(F.liens[cust6]) == 2
      and json.loads(wa_json(autre))["liaison"][c6]["lien_id"] == F.liens[cust6][0]["id"])
F.liens[cust6][1].update(whatsapp_setup_status="completed", status="used")        # le PREMIER lien, pas le suivi
F.numeros[cust6] = [numero_brut("PN-L14")]
F.appels.clear()
r = liaison(c6)
check("L14.2 terminee, numéro rangé", r.json().get("etat") == "terminee" and publics(c6)["WHATSAPP_PHONE_ID"] == "PN-L14", r.text)
check("L14.3 un `liens` et un `numeros`",
      F.appels == [("GET", f"/customers/{cust6}/setup_links"), ("GET", "/whatsapp/phone_numbers")], F.appels)

print("\n[L15] deux creer_lien simultanés")
c7 = nouveau_compte(autre)
F.appels.clear()


async def _deux():
    return await asyncio.gather(WA.creer_lien(c7, "customer_managed", None, None),
                                WA.creer_lien(c7, "customer_managed", None, None), return_exceptions=True)


res = asyncio.run(_deux())
check("L15.1 les deux rendent une URL", all(isinstance(x, dict) and x.get("url") for x in res), res)
check("L15.2 un seul POST /customers", F.appels.count(("POST", "/customers")) == 1, F.appels)
check("L15.3 deux liens sur le même customer",
      sum(1 for a in F.appels if a[0] == "POST" and a[1].endswith("/setup_links")) == 2, F.appels)

print("\n[L16] produit gouverné par un client")
pain = E.creer({"nom": "Pain Lune", "type": "produit", "parent": lune})["id"]
check("L16.0 client_responsable(produit) = le client", E.client_responsable(pain) == lune)
c8 = nouveau_compte(pain)
F.appels.clear()
r = lien(c8, {"facturation": "customer_managed"})
check("L16.1 sans consentement : 400, aucun appel", r.status_code == 400 and "consentement daté" in r.text and F.appels == [],
      r.text)
r = lien(c8, {"facturation": "customer_managed", "consentement": {"moyen": "doigt", "date": "2026-10-22"}})
check("L16.2 avec consentement : 200", r.status_code == 200, r.text)
cust8 = publics(c8)["KAPSO_CUSTOMER_ID"]
F.lien(cust8, whatsapp_setup_status="completed")
F.numeros[cust8] = [numero_brut("PN-PAIN")]
r = liaison(c8)
cons = [x for x in FC.consentements_en_cours(lune) if x["canal_id"] == "whatsapp:PN-PAIN"]
check("L16.3 terminee, consentement whatsapp:PN-PAIN sur la fiche du CLIENT (moyen doigt)",
      r.json().get("etat") == "terminee" and len(cons) == 1 and cons[0]["moyen"] == "doigt", (r.text, cons))
check("L16.4 aucune fiche pour le produit", not (_tmp / "espaces" / pain / "client.json").exists())

print("\n[L17] le premier Vérifier après la fin de liaison est vert")
c9 = nouveau_compte(lune2)
lien(c9, {"facturation": "customer_managed", "consentement": CONS})
cust9 = publics(c9)["KAPSO_CUSTOMER_ID"]
F.lien(cust9, whatsapp_setup_status="completed")
F.numeros[cust9] = [numero_brut("PN-L17")]
F.details["PN-L17"] = numero_brut("PN-L17", nom="Fromagerie Lune")
r = verifier(c9)
vue = r.json().get("compte") or {}
v = vue.get("verification") or {}
check("L17.1 vert, id_distant PN-L17, pas d'ecartee", r.status_code == 200 and v.get("etat") == "vert"
      and v.get("id_distant") == "PN-L17" and "ecartee" not in vue, r.text)
check("L17.2 numéro rangé, consentement ajouté", publics(c9)["WHATSAPP_PHONE_ID"] == "PN-L17"
      and FC.consentement_en_cours(lune2, "whatsapp:PN-L17"))
c10 = nouveau_compte(autre)
lien(c10, {"facturation": "customer_managed"})
cust10 = publics(c10)["KAPSO_CUSTOMER_ID"]
F.lien(cust10, whatsapp_setup_status="completed")
F.numeros[cust10] = [numero_brut("PN-L17B")]
avant = comptes_json()
with CP.sous_compte(c10):
    rr = asyncio.run(VC.verifier_plateforme("whatsapp"))
check("L17.3 verifier_plateforme seul (sans `verifier`) ne range rien", comptes_json() == avant
      and not publics(c10)["WHATSAPP_PHONE_ID"], rr)
_liens_vrai = KA.liens


async def _liens_ko(cust):
    raise KA.KapsoErreur("Kapso injoignable", code="reseau", reessayable=True)


KA.liens = _liens_ko
c11 = nouveau_compte(autre)
lien(c11, {"facturation": "customer_managed"})
r = verifier(c11)
v = (r.json().get("compte") or {}).get("verification") or {}
check("L17.4 panne Kapso pendant la relecture : 200, orange reseau (jamais une 500)", r.status_code == 200
      and v.get("etat") == "orange" and v.get("code") == "reseau", r.text)
KA.liens = _liens_vrai

print("\n[L18] convergence du consentement")
lune3 = E.creer({"nom": "Crèmerie Lune", "type": "client"})["id"]
c12 = nouveau_compte(lune3)
lien(c12, {"facturation": "customer_managed", "consentement": CONS})
cust12 = publics(c12)["KAPSO_CUSTOMER_ID"]
F.lien(cust12, whatsapp_setup_status="completed")
F.numeros[cust12] = [numero_brut("PN-L18")]
_ajout = FC.ajouter_consentement
_coups = []


def _ajout_casse(*a, **k):
    if not _coups:
        _coups.append(1)
        raise OSError("disque plein")
    return _ajout(*a, **k)


FC.ajouter_consentement = _ajout_casse
r = liaison(c12)
check("L18.1 écriture du consentement en échec : pas de 200, aucun numéro rangé", r.status_code != 200
      and not publics(c12)["WHATSAPP_PHONE_ID"], r.text)
r = liaison(c12)
check("L18.2 relecture suivante : terminee, consentement ajouté", r.json().get("etat") == "terminee"
      and FC.consentement_en_cours(lune3, "whatsapp:PN-L18"), r.text)
FC.ajouter_consentement = _ajout
FC.revoquer(lune3, "whatsapp:PN-L18")
r = liaison(c12)
check("L18.3 révocation jamais défaite par une relecture", r.json().get("etat") == "terminee"
      and not FC.consentement_en_cours(lune3, "whatsapp:PN-L18"), r.text)
c13 = nouveau_compte(lune3)
lien(c13, {"facturation": "customer_managed", "consentement": CONS})
cust13 = publics(c13)["KAPSO_CUSTOMER_ID"]
fw = _tmp / "espaces" / lune3 / "whatsapp.json"
dw = json.loads(fw.read_text("utf-8"))
dw["liaison"][c13]["consentement"]["moyen"] = "pigeon"            # la fiche refusera ce moyen (ValueError)
fw.write_text(json.dumps(dw), "utf-8")
F.lien(cust13, whatsapp_setup_status="completed")
F.numeros[cust13] = [numero_brut("PN-L18B")]
r = liaison(c13)
check("L18.4 autre ValueError de la fiche : 400, rien de rangé", r.status_code == 400
      and "moyen de consentement inconnu" in r.text and not publics(c13)["WHATSAPP_PHONE_ID"], r.text)

print("\n[L19] lecture de whatsapp.json")
vide = E.creer({"nom": "Vide"})["id"]
check("L19.1 absent : {}", WA._lire_doc(vide) == {})
fv = _tmp / "espaces" / vide / "whatsapp.json"
fv.parent.mkdir(parents=True, exist_ok=True)
fv.write_text("{pas du json", "utf-8")
check("L19.2 JSON illisible : {} et fichier mis de côté", WA._lire_doc(vide) == {} and not fv.exists()
      and any(x.name.startswith("whatsapp.json.illisible-") for x in fv.parent.iterdir()))
fv.mkdir()                                                         # une lecture qui échoue autrement (pas FileNotFound)
leve = False
try:
    WA._lire_doc(vide)
except OSError as e:
    leve = not isinstance(e, FileNotFoundError)
check("L19.3 autre erreur de lecture : levée, rien réécrit", leve and fv.is_dir())

print("\n[L20] codes d'erreur")
check("L20.1 CODES_ERREUR", WA.CODES_ERREUR == ("numero_deja_relie", "fournisseur", "expire"))
check("L20.2 ETATS_LIAISON retiré", not hasattr(WA, "ETATS_LIAISON"))

c.__exit__(None, None, None)
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
