# -*- coding: utf-8 -*-
"""t311 tâche 6 (27/10/2026) — la validation d'un post par le CLIENT, par WhatsApp (`whatsapp_validation`).
Ce que ce banc garde (routes réelles par TestClient, data-dir et sqlite temporaires, faux `kapso._requete` qui range les
corps envoyés : aucun réseau, aucune clé réelle) :
  V0  `WE._plat` : `bouton` {id, titre} d'une réponse interactive, {payload, titre} d'un bouton de modèle ; clés gardées.
  V1  fenêtre ouverte : image du post téléversée (PNG), corps `interactive` EXACT (en-tête image, titre + légende, ids
      `val:<post>:ok|corr`, « Valider »/« Corriger ») ; validation rangée `envoye` dans whatsapp_brouillons.json.
  V2  fenêtre fermée sans modèle -> 400, rien d'envoyé ; avec modèle -> composants EXACTS (en-tête image, corps, boutons
      0 et 1 aux payloads `val:`).
  V3  fiche en anglais -> « Approve »/« Request changes » ; post sans image -> aucun téléversement, pas d'en-tête.
  V4  refus : post pas `a_valider` -> 409 ; post inconnu -> 404 ; aucun compte relié -> 400 ; pas d'accord -> 409
      `accord` (rien téléversé) ; post sans client -> 409 ; fiche sans contact -> 400 ; produit -> compte du client.
  V5  réponses : « Valider » -> post `draft` + `valide_client_le` + journal de la fiche `validation` (qui client) ;
      deuxième réponse -> ignorée ; autre contact -> ignorée ; post supprimé -> ignorée ; chaque ignorée notée au journal
      de whatsapp.json `validation_ignoree` SANS texte.
  V6  « Corriger » (bouton de modèle) -> `a_corriger`, puis le texte suivant du contact -> `note` (≤ 2000), `corrige` ;
      GET /api/schedule/{id}/client rend `validation_whatsapp.note` ; un texte sans correction en attente -> False ;
      au-delà de 24 h -> rien.
  V7  la route t309 `validation-client` répond comme avant (400 réponse inconnue, 200 valide) ; la logique vit dans
      `services/validation_client.valider_post` (RefusValidation traduite à l'identique).
  V9  relecture : contenu modifié après l'envoi -> « Valider » sans effet (empreinte) ; décision au PC (moyen ≠ whatsapp)
      -> demande `perimee` ; `en_attente` ignore une demande de plus de 30 jours ou d'un post qui n'est plus a_valider ;
      bouton forgé pour le post d'un autre client -> rien ; réponse venue de l'alias BSUID -> acceptée.
  V8  journal (logger) : aucun texte de message ni clé.
Run (depuis backend/) : & $PY tests/test_whatsapp_validation.py"""
import asyncio, json, os, pathlib, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwaval_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "KAPSO_API_KEY", "ANTHROPIC_MODEL", "AGENT_MODEL"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
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
        fail += 1; print(f"  FAIL  {label} {str(detail)[:900]}")


from datetime import datetime, timedelta, timezone                  # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import comptes as CP, espaces as E, fiche_client as F, kapso as KA, pricing as PR   # noqa: E402
from app.services import whatsapp as WA, whatsapp_echanges as WE, agent_whatsapp as AW, storage      # noqa: E402
try:
    from app.services import whatsapp_validation as WV               # noqa: E402
except ImportError as e:                                             # banc rouge : le module n'existe pas encore
    print(f"  FAIL  import whatsapp_validation ({e})")
    print(f"\n{ok} ok, 1 fail")
    sys.exit(1)

_loop = asyncio.new_event_loop()


def run(coro):
    return _loop.run_until_complete(coro)


run(storage.init_db())
GRILLE = {"33": {"marketing": 0.0859, "utility": 0.0300, "authentication": 0.0300, "service": 0.0100}}
PR._PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
PR._PRICING_FILE.write_text(json.dumps({"whatsapp_meta_usd": GRILLE, "whatsapp_service_gratuits_mois": 0}), encoding="utf-8")
KA_CLE = "CLE-KAPSO-SECRETE-VALIDATION"
os.environ["KAPSO_API_KEY"] = KA_CLE
setattr(settings, "KAPSO_API_KEY", KA_CLE)


# ---- le faux Kapso ----------------------------------------------------------------------------------------------------
class Faux:
    def __init__(self):
        self.envois, self.medias, self.msgs, self.ouvertes, self.modeles = [], [], {}, set(), []


FK = Faux()


async def faux_requete(methode, url, *, json=None, params=None, fichiers=None):
    await asyncio.sleep(0)
    chemin = url.replace(KA.PROXY, "").replace(KA.PLATFORM, "").split("?")[0]
    parts = chemin.strip("/").split("/")
    if methode == "POST" and len(parts) == 2 and parts[1] == "media":
        FK.medias.append((parts[0], {k: (v[0], v[2] if len(v) > 2 else v[1]) for k, v in (fichiers or {}).items()},
                          len((fichiers or {}).get("file", (None, b""))[1] or b"")))
        return 200, {"id": f"MEDIA{len(FK.medias)}"}, {}
    if methode == "POST" and len(parts) == 2 and parts[1] == "messages":
        FK.envois.append((parts[0], json))
        return 200, {"messaging_product": "whatsapp", "messages": [{"id": f"wamid.V{len(FK.envois)}"}]}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "messages":
        return 200, {"data": [dict(x) for x in FK.msgs.get(parts[0], [])], "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "conversations":
        il_y_a = datetime.now(timezone.utc) - timedelta(hours=1)
        data = [{"id": "conv-" + tel, "phone_number": tel, "kapso": {"last_inbound_at": il_y_a.isoformat()}}
                for (p, tel) in FK.ouvertes if p == parts[0]]
        return 200, {"data": data, "paging": {"cursors": {}}}, {}
    if methode == "GET" and len(parts) == 2 and parts[1] == "message_templates":
        return 200, {"data": FK.modeles, "paging": {}}, {}
    return 500, {"error": "chemin inconnu du faux"}, {}


async def faux_dormir(_s):
    return None


KA._requete = faux_requete
KA._dormir = faux_dormir


# ---- les espaces, comptes, posts --------------------------------------------------------------------------------------
E.lire()


def compte_wa(eid, pid=None):
    cid = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
    if pid:
        CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": pid, "WHATSAPP_WABA_ID": "WABA-" + pid})
    return cid


def client(nom, contact="06 12 34 56 78", langue="fr"):
    eid = E.creer({"nom": nom, "type": "client"})["id"]
    F.ecrire(eid, {"societe": nom + " SARL", "contact": {"nom": "Mme " + nom, "email": "", "whatsapp": contact},
                   "langue": langue})
    return eid


C1 = client("Salon Lune")
P1E = E.creer({"nom": "Coffrets", "type": "produit", "parent": C1})["id"]
cW = compte_wa(C1, "PN-V")
F.ajouter_consentement(C1, "whatsapp:PN-V", ["messages"], "ecrit")
TEL = "33612345678"
IDENT = "tel:" + TEL
WA.noter_accord(cW, IDENT, "formulaire")
C2 = client("Garage Sans Numéro")                                    # aucun compte relié
compte_wa(C2)                                                        # un compte whatsapp NON relié ne compte pas
C3 = client("Fleuriste Sans Accord", contact="+33 6 99 88 77 66")
cW3 = compte_wa(C3, "PN-W")
F.ajouter_consentement(C3, "whatsapp:PN-W", ["messages"], "ecrit")
C4 = client("Client Muet", contact="")
compte_wa(C4, "PN-M")
MQ = E.creer({"nom": "Marque Ciel", "type": "marque"})["id"]

from PIL import Image                                                # noqa: E402
Image.new("RGB", (8, 8), (200, 30, 30)).save(_tmp / "images" / "apercu.png")
(_tmp / "images" / "anim.gif").write_bytes(b"GIF89a" + b"\0" * 20)


def poser(eid, status="a_valider", title="Teaser", caption="Texte du post", source_image="apercu.png"):
    pid = str(uuid.uuid4())

    async def _p():
        async with storage.async_session_factory() as s:
            s.add(storage.ScheduledPost(id=pid, title=title, caption=caption, channels="x", status=status, mode="assisted",
                                        run_at=datetime.utcnow() + timedelta(days=3), espace_id=eid, comptes=None,
                                        source_image=source_image))
            await s.commit()
    run(_p())
    return pid


def lire_post(pid):
    async def _l():
        async with storage.async_session_factory() as s:
            return await s.get(storage.ScheduledPost, pid)
    return run(_l())


def supprimer_post(pid):
    async def _d():
        async with storage.async_session_factory() as s:
            p = await s.get(storage.ScheduledPost, pid)
            await s.delete(p)
            await s.commit()
    run(_d())


def plat(msg):
    return WE._plat(msg)


N = [0]


def bouton_inter(tel, ident_bouton, titre="Valider"):
    N[0] += 1
    return {"id": f"wamid.IN{N[0]}", "type": "interactive", "from": tel,
            "interactive": {"type": "button_reply", "button_reply": {"id": ident_bouton, "title": titre}},
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())), "kapso": {"direction": "inbound"}}


def bouton_modele(tel, payload, texte="Corriger"):
    N[0] += 1
    return {"id": f"wamid.IN{N[0]}", "type": "button", "from": tel, "button": {"payload": payload, "text": texte},
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())), "kapso": {"direction": "inbound"}}


def texte_in(tel, texte):
    N[0] += 1
    return {"id": f"wamid.IN{N[0]}", "type": "text", "from": tel, "text": {"body": texte},
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())), "kapso": {"direction": "inbound"}}


def ignorees(cid):
    return [x for x in WA.etat(cid)["journal"] if x.get("statut") == "validation_ignoree"]


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
client_http = TestClient(app, client=("127.0.0.1", 50000))          # sans `with` : pas de lifespan (ni boucles de fond)


def envoyer(pid):
    return client_http.post(f"/api/schedule/{pid}/validation-whatsapp")


def detail(r):
    try:
        return r.json().get("detail")
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
print("[V0] WE._plat : les boutons")
pi = plat(bouton_inter(TEL, "val:abc:ok", "Valider"))
check("V0.1 réponse interactive : bouton {id, titre}", pi.get("bouton") == {"id": "val:abc:ok", "titre": "Valider"}, pi)
pm = plat(bouton_modele(TEL, "val:abc:corr", "Corriger"))
check("V0.2 bouton de modèle : bouton {payload, titre}", pm.get("bouton") == {"payload": "val:abc:corr", "titre": "Corriger"}, pm)
pt = plat(texte_in(TEL, "bonjour"))
check("V0.3 clés gardées ; pas de `bouton` pour un texte",
      {"id", "identite", "sens", "type", "texte", "quand", "statut"} <= set(pi) and "bouton" not in pt
      and pt["texte"] == "bonjour" and pi["identite"] == IDENT and pi["sens"] == "entrant", (pi, pt))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V1] fenêtre ouverte : message à boutons")
P1 = poser(C1)
FK.ouvertes.add(("PN-V", TEL))
r = envoyer(P1)
check("V1.1 200 {envoi: boutons, id}", r.status_code == 200 and r.json() == {"envoi": "boutons", "id": "wamid.V1"},
      (r.status_code, r.text))
check("V1.2 l'image du post est téléversée (PNG, octets du fichier)",
      len(FK.medias) == 1 and FK.medias[0][0] == "PN-V" and FK.medias[0][1].get("type") == (None, "image/png")
      and FK.medias[0][2] == (_tmp / "images" / "apercu.png").stat().st_size, FK.medias)
ATTENDU = {"messaging_product": "whatsapp", "to": TEL, "type": "interactive", "interactive": {
    "type": "button", "header": {"type": "image", "image": {"id": "MEDIA1"}}, "body": {"text": "Teaser\n\nTexte du post"},
    "action": {"buttons": [{"type": "reply", "reply": {"id": f"val:{P1}:ok", "title": "Valider"}},
                           {"type": "reply", "reply": {"id": f"val:{P1}:corr", "title": "Corriger"}}]}}}
check("V1.3 corps interactive EXACT", FK.envois == [("PN-V", ATTENDU)], FK.envois)
v1 = AW.validations(C1).get(P1) or {}
check("V1.4 validation rangée : identité, compte, envoye_le, état envoye",
      v1.get("identite") == IDENT and v1.get("cid") == cW and v1.get("etat") == "envoye" and v1.get("envoye_le")
      and v1.get("id") == "wamid.V1", v1)

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V2] fenêtre fermée")
FK.ouvertes.clear()
P2 = poser(C1)
n0 = len(FK.envois)
r = envoyer(P2)
check("V2.1 sans modèle de validation : 400, rien d'envoyé ni téléversé",
      r.status_code == 400 and "modèle" in str(detail(r)) and len(FK.envois) == n0 and len(FK.medias) == 1,
      (r.status_code, r.text))
FK.modeles = [{"name": "validation_post", "language": "fr", "category": "UTILITY", "status": "APPROVED", "components": [
    {"type": "HEADER", "format": "IMAGE"}, {"type": "BODY", "text": "Publication à valider : {{1}}"},
    {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "Valider"}, {"type": "QUICK_REPLY", "text": "Corriger"}]}]}]
WA.regler_espace(C1, {"agent": {"modele_validation": {"nom": "validation_post", "langue": "fr"}}})
r = envoyer(P2)
check("V2.2 avec modèle : 200 {envoi: modele}", r.status_code == 200 and r.json().get("envoi") == "modele",
      (r.status_code, r.text))
ATT_M = {"messaging_product": "whatsapp", "to": TEL, "type": "template", "template": {
    "name": "validation_post", "language": {"code": "fr"}, "components": [
        {"type": "header", "parameters": [{"type": "image", "image": {"id": "MEDIA2"}}]},
        {"type": "body", "parameters": [{"type": "text", "text": "Teaser"}]},
        {"type": "button", "sub_type": "quick_reply", "index": "0", "parameters": [{"type": "payload", "payload": f"val:{P2}:ok"}]},
        {"type": "button", "sub_type": "quick_reply", "index": "1",
         "parameters": [{"type": "payload", "payload": f"val:{P2}:corr"}]}]}}
check("V2.3 composants EXACTS (en-tête image, corps, boutons 0 et 1)", lambda: FK.envois[-1] == ("PN-V", ATT_M), FK.envois[-1:])
check("V2.4 validation du second post rangée", (AW.validations(C1).get(P2) or {}).get("etat") == "envoye")

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V3] anglais, sans image")
FK.ouvertes.add(("PN-V", TEL))
F.ecrire(C1, {"langue": "en"})
PS = poser(C1, source_image=None, title="", caption="Spring sale")
m0 = len(FK.medias)
r = envoyer(PS)
corps = ((FK.envois[-1][1] if FK.envois else None) or {}).get("interactive") or {}
check("V3.1 fiche en anglais : « Approve » / « Request changes »",
      r.status_code == 200 and [b["reply"]["title"] for b in corps.get("action", {}).get("buttons", [])]
      == ["Approve", "Request changes"], (r.status_code, corps))
check("V3.2 sans image : aucun téléversement, aucun en-tête ; texte = la légende",
      len(FK.medias) == m0 and "header" not in corps and corps.get("body") == {"text": "Spring sale"}, corps)
PG = poser(C1, source_image="anim.gif")
r = envoyer(PG)
check("V3.3 image GIF : texte seul (ni JPEG ni PNG)", lambda: r.status_code == 200 and len(FK.medias) == m0
      and "header" not in ((FK.envois[-1][1] or {}).get("interactive") or {}), FK.envois[-1:])
F.ecrire(C1, {"langue": "fr"})
PP = poser(P1E)
r = envoyer(PP)
check("V3.4 post d'un PRODUIT : envoyé par le compte du client, validation rangée chez le client",
      lambda: r.status_code == 200 and FK.envois[-1][0] == "PN-V" and (AW.validations(C1).get(PP) or {}).get("etat") == "envoye",
      (r.status_code, r.text))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V4] refus")
n0, m0 = len(FK.envois), len(FK.medias)
r = envoyer(poser(C1, status="draft"))
check("V4.1 post pas a_valider -> 409", r.status_code == 409, (r.status_code, r.text))
r = envoyer("inconnu-" + uuid.uuid4().hex[:8])
check("V4.2 post inconnu -> 404", r.status_code == 404, (r.status_code, r.text))
r = envoyer(poser(C2))
check("V4.3 aucun compte relié -> 400 « aucun numéro WhatsApp relié pour ce client »",
      r.status_code == 400 and detail(r) == "aucun numéro WhatsApp relié pour ce client", (r.status_code, r.text))
FK.ouvertes.add(("PN-W", "33699887766"))
r = envoyer(poser(C3))
check("V4.4 aucun accord du contact -> 409 code accord, rien téléversé",
      r.status_code == 409 and isinstance(detail(r), dict) and detail(r).get("code") == "accord" and len(FK.medias) == m0,
      (r.status_code, r.text))
r = envoyer(poser(MQ))
check("V4.5 post sans client -> 409", r.status_code == 409, (r.status_code, r.text))
r = envoyer(poser(C4))
check("V4.6 fiche sans contact WhatsApp -> 400", r.status_code == 400, (r.status_code, r.text))
check("V4.7 aucun envoi pour les refus", len(FK.envois) == n0, FK.envois[n0:])
check("V4.8 route locale seulement (un client distant -> 401/403)",
      TestClient(app, client=("203.0.113.9", 4000)).post(f"/api/schedule/{P1}/validation-whatsapp").status_code in (401, 403))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V5] réponses")
j0 = len(F.lire(C1)["journal"])
ok1 = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{P1}:ok"))))
p = lire_post(P1)
check("V5.1 « Valider » : True, post draft, valide_client_le posé", ok1 is True and p.status == "draft"
      and p.valide_client_le is not None, (ok1, p.status, p.valide_client_le))
jf = F.lire(C1)["journal"][j0:]
check("V5.2 journal de la fiche : une ligne validation (qui client)",
      any(x["quoi"] == "validation" and x["qui"] == "client" for x in jf), jf)
check("V5.3 validation à l'état valide", (AW.validations(C1).get(P1) or {}).get("etat") == "valide")
i0 = len(ignorees(cW))
m2 = bouton_inter(TEL, f"val:{P1}:corr", "Corriger")
r2 = run(WV.traiter_reponse(cW, C1, plat(m2)))
p = lire_post(P1)
check("V5.4 deuxième réponse après décision : ignorée (False), post inchangé", r2 is False and p.status == "draft"
      and p.valide_client_le is not None and (AW.validations(C1).get(P1) or {}).get("etat") == "valide", (r2, p.status))
ig = ignorees(cW)[i0:]
check("V5.5 notée au journal de whatsapp.json : validation_ignoree, sans texte",
      len(ig) == 1 and ig[0]["id"] == m2["id"] and ig[0]["identite"] == IDENT and "texte" not in ig[0], ig)
r3 = run(WV.traiter_reponse(cW, C1, plat(bouton_inter("33600000099", f"val:{PS}:ok"))))
check("V5.6 réponse d'un autre contact : ignorée, post et validation inchangés",
      r3 is False and lire_post(PS).status == "a_valider" and (AW.validations(C1).get(PS) or {}).get("etat") == "envoye"
      and len(ignorees(cW)) == i0 + 2, (r3, lire_post(PS).status))
supprimer_post(PG)
r4 = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{PG}:ok"))))
check("V5.7 post supprimé : ignorée (False), validation périmée, notée", r4 is False
      and (AW.validations(C1).get(PG) or {}).get("etat") == "perimee" and len(ignorees(cW)) == i0 + 3, r4)
r5 = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, "b1", "Oui"))))
check("V5.8 un bouton qui n'est pas une validation : False, rien noté", r5 is False and len(ignorees(cW)) == i0 + 3)

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V6] « Corriger » puis la note")
r6 = run(WV.traiter_reponse(cW, C1, plat(bouton_modele(TEL, f"val:{P2}:corr"))))
p = lire_post(P2)
v = AW.validations(C1).get(P2) or {}
check("V6.1 bouton de modèle « Corriger » : True, post a_valider sans date, état a_corriger",
      r6 is True and p.status == "a_valider" and p.valide_client_le is None and v.get("etat") == "a_corriger", (r6, v))
check("V6.2 en attente : l'espace a une correction ouverte", run(WV.en_attente(C1)) is True)
NOTE = "Changez la photo, mettez le logo en haut " + "x" * 2100
r7 = run(WV.traiter_reponse(cW, C1, plat(texte_in(TEL, NOTE))))
v = AW.validations(C1).get(P2) or {}
check("V6.3 le texte suivant du contact : note rangée (≤ 2000), état corrige", r7 is True and v.get("etat") == "corrige"
      and v.get("note") == NOTE[:2000] and v.get("note_le"), v)
g = client_http.get(f"/api/schedule/{P2}/client")
vw = (g.json() or {}).get("validation_whatsapp") if g.status_code == 200 else None
check("V6.4 GET /schedule/{id}/client : validation_whatsapp.note, sans identité ni compte",
      g.status_code == 200 and "exigences" in g.json() and (vw or {}).get("note") == NOTE[:2000]
      and (vw or {}).get("etat") == "corrige" and "identite" not in (vw or {}) and "cid" not in (vw or {}), g.text[:300])
r8 = run(WV.traiter_reponse(cW, C1, plat(texte_in(TEL, "merci beaucoup"))))
check("V6.5 un autre texte sans correction en attente : False, note inchangée",
      r8 is False and (AW.validations(C1).get(P2) or {}).get("note") == NOTE[:2000], r8)
run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{PP}:corr", "Corriger"))))


def vieillir(vals):
    vals[PP]["decide_le"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(timespec="seconds")
    return vals


AW.modifier_validations(C1, vieillir)
r9 = run(WV.traiter_reponse(cW, C1, plat(texte_in(TEL, "trop tard"))))
check("V6.6 texte plus de 24 h après « Corriger » : rien (False), pas de note",
      r9 is False and "note" not in (AW.validations(C1).get(PP) or {}), AW.validations(C1).get(PP))
g = client_http.get(f"/api/schedule/{P1}/client")
check("V6.7 GET /client d'un post validé : validation_whatsapp sans note",
      g.status_code == 200 and (g.json().get("validation_whatsapp") or {}).get("etat") == "valide"
      and "note" not in (g.json().get("validation_whatsapp") or {}), g.text[:300])
g = client_http.get(f"/api/schedule/{poser(MQ)}/client")
check("V6.8 GET /client d'un post sans client : réponse t309 inchangée {exigences: null}", g.status_code == 200
      and g.json() == {"exigences": None}, g.text[:300])

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V7] la route t309 validation-client inchangée")
P7 = poser(C1)
r = client_http.post(f"/api/schedule/{P7}/validation-client", json={"reponse": "peut-etre", "moyen": "ecrit"})
check("V7.1 réponse inconnue -> 400 (même message)",
      r.status_code == 400 and detail(r) == "réponse du client inconnue (valide ou corriger)", r.text)
r = client_http.post(f"/api/schedule/{P7}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
check("V7.2 valide/ecrit -> 200 {post}, status draft", r.status_code == 200 and r.json()["post"]["status"] == "draft"
      and r.json()["post"]["valide_client_le"], r.text[:300])
r = client_http.post(f"/api/schedule/{poser(MQ)}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
check("V7.3 post sans client -> 409", r.status_code == 409 and detail(r) == "ce post n'est gouverné par aucun client", r.text)
src = (_ICI.parent / "app" / "api" / "routes.py").read_text(encoding="utf-8")
corps_route = src[src.find('@router.post("/schedule/{post_id}/validation-client")'):]
corps_route = corps_route[:corps_route.find("\n\n\n")]
check("V7.4 la route appelle validation_client.valider_post (logique extraite dans un service, réutilisée)",
      "await _vc.valider_post(" in corps_route and "RefusValidation" in corps_route, corps_route[:400])
from app.services import validation_client as VC                   # noqa: E402
try:
    run(VC.valider_post("nexistepas", "valide", "ecrit"))
    _r = None
except VC.RefusValidation as e:
    _r = (e.statut, e.message)
check("V7.5 le service lève RefusValidation(404, « post inconnu ») ; la route le traduit à l'identique",
      _r == (404, "post inconnu") and client_http.post("/api/schedule/nexistepas/validation-client",
                                                       json={"reponse": "valide", "moyen": "ecrit"}).status_code == 404, _r)

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V9] relecture : empreinte, décision au PC, en_attente, post d'un autre client, alias")
FK.ouvertes.add(("PN-V", TEL))


def changer_titre(pid, titre):
    async def _c():
        async with storage.async_session_factory() as s_:
            q = await s_.get(storage.ScheduledPost, pid)
            q.title = titre
            await s_.commit()
    run(_c())


PE = poser(C1)
check("V9.0 envoi : empreinte du contenu rangée", envoyer(PE).status_code == 200
      and len((AW.validations(C1).get(PE) or {}).get("empreinte") or "") == 16, AW.validations(C1).get(PE))
changer_titre(PE, "Teaser modifié")
r = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{PE}:ok"))))
p = lire_post(PE)
check("V9.1 contenu modifié après l'envoi, puis « Valider » : rien ne change (False), validation périmée",
      r is False and p.status == "a_valider" and p.valide_client_le is None
      and (AW.validations(C1).get(PE) or {}).get("etat") == "perimee", (r, p.status))
PD = poser(C1)
envoyer(PD)
rr = client_http.post(f"/api/schedule/{PD}/validation-client", json={"reponse": "valide", "moyen": "ecrit"})
check("V9.2 décision au PC (moyen écrit) : la demande WhatsApp envoyée devient périmée",
      rr.status_code == 200 and (AW.validations(C1).get(PD) or {}).get("etat") == "perimee", AW.validations(C1).get(PD))
PD2 = poser(C1)
envoyer(PD2)
run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{PD2}:corr", "Corriger"))))
etat_av = (AW.validations(C1).get(PD2) or {}).get("etat")
client_http.post(f"/api/schedule/{PD2}/validation-client", json={"reponse": "valide", "moyen": "doigt"})
check("V9.3 a_corriger puis décision au PC : périmée (le texte suivant ne devient plus une note)",
      etat_av == "a_corriger" and (AW.validations(C1).get(PD2) or {}).get("etat") == "perimee"
      and run(WV.traiter_reponse(cW, C1, plat(texte_in(TEL, "une remarque tardive")))) is False, AW.validations(C1).get(PD2))
PW = poser(C1)
envoyer(PW)
client_http.post(f"/api/schedule/{PW}/validation-client", json={"reponse": "corriger", "moyen": "whatsapp"})
check("V9.4 décision saisie avec moyen whatsapp : la demande reste envoyée", (AW.validations(C1).get(PW) or {}).get("etat") == "envoye")
C6 = client("Espace Attente")
PA6, PB6 = poser(C6), poser(C6, status="draft")
vieux = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(timespec="seconds")
neuf_ = datetime.now(timezone.utc).isoformat(timespec="seconds")
AW.modifier_validations(C6, lambda v: {PA6: {"identite": IDENT, "etat": "envoye", "envoye_le": vieux},
                                       PB6: {"identite": IDENT, "etat": "envoye", "envoye_le": neuf_}})
check("V9.5 en_attente : demande de plus de 30 jours, ou post qui n'est plus a_valider -> False",
      run(WV.en_attente(C6)) is False)
AW.modifier_validations(C6, lambda v: {**v, PA6: {**v[PA6], "envoye_le": neuf_}})
check("V9.6 en_attente : demande récente d'un post a_valider -> True", run(WV.en_attente(C6)) is True)
PX = poser(C3)
AW.modifier_validations(C1, lambda v: {**v, PX: {"identite": IDENT, "cid": cW, "etat": "envoye", "envoye_le": neuf_,
                                                 "empreinte": WV.empreinte(lire_post(PX))}})
r = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{PX}:ok"))))
check("V9.7 bouton forgé pour le post d'un AUTRE client, depuis le bon contact : rien (False), post inchangé",
      r is False and lire_post(PX).status == "a_valider" and lire_post(PX).valide_client_le is None, r)
r = run(WV.traiter_reponse(cW, C1, plat(bouton_inter(TEL, f"val:{poser(C3)}:ok"))))
check("V9.8 bouton forgé sans validation rangée : rien (False)", r is False)
WA._noter(cW, lambda e: e["alias"].update({"bsuid:BS-LUNE": IDENT, IDENT: "bsuid:BS-LUNE"}))
PL = poser(C1)
envoyer(PL)
N[0] += 1
m_bs = {"id": f"wamid.IN{N[0]}", "type": "interactive", "from_user_id": "BS-LUNE",
        "interactive": {"type": "button_reply", "button_reply": {"id": f"val:{PL}:ok", "title": "Valider"}},
        "timestamp": str(int(datetime.now(timezone.utc).timestamp())), "kapso": {"direction": "inbound"}}
pb = plat(m_bs)
r = run(WV.traiter_reponse(cW, C1, pb))
check("V9.9 réponse venue de l'alias (BSUID du même contact) : acceptée, post validé",
      pb["identite"] == "bsuid:BS-LUNE" and r is True and lire_post(PL).status == "draft", (pb.get("identite"), r))

# ---------------------------------------------------------------------------------------------------------------------
print("\n[V8] journal")
check("V8.1 aucun texte de message ni clé au journal",
      not any(("Changez la photo" in l or "Texte du post" in l or "trop tard" in l or KA_CLE in l) for l in JOURNAL),
      [l for l in JOURNAL if "Changez" in l][:3])
doc = json.loads((E.dossier() / C1 / "whatsapp.json").read_text(encoding="utf-8"))
check("V8.2 whatsapp.json ne contient aucun texte de message", "Changez la photo" not in json.dumps(doc, ensure_ascii=False)
      and "Texte du post" not in json.dumps(doc, ensure_ascii=False))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
