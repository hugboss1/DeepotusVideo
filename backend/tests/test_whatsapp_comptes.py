# -*- coding: utf-8 -*-
"""t310 tâche 1 (27/10/2026) — B1 WhatsApp via Kapso : la plateforme d'espace `whatsapp` et la clé Kapso PLATE.
Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md, spec §6.1 (une seule KAPSO_API_KEY partagée par tous les
espaces ; des champs publics par espace, posés par la liaison). t328 (27/10/2026) : WhatsApp DEVIENT une cible du
Planificateur (diffusions) : W5 garde la cible permise, le refus d'un compte d'un autre espace,
et CIBLES_EXPLICITES (jamais un canal par défaut).
Ce que ce banc garde (routes réelles, TestClient, data-dir et sqlite temporaires, aucun réseau) :
  W1 (a) GET /api/comptes : 200, `whatsapp` décrit avec ses 5 champs publics, aucun champ KAPSO_API_KEY.
  W2 (b) clé plate posée, aucun compte : aucun compte `historique-whatsapp`.
  W3 (c) `disponible` : faux sans WHATSAPP_PHONE_ID, faux sans clé, vrai avec les deux.
  W4 (d) POST /api/comptes/{id} avec un champ whatsapp ou KAPSO_API_KEY dans `valeurs` : 400, rien d'écrit.
  W5 (e) t328 : verifier_cibles accepte un compte whatsapp de l'espace (R._poser_comptes aussi), refuse celui d'un autre.
  W6 (f) la vue ne porte jamais la valeur de la clé.
  W7 (g) coffre posé et fermé : GET /api/comptes 200, `cle_plate.posee` faux, sans exception.
  W8 (h) export d'un paquet d'espace : aucun champ whatsapp ; import d'un paquet qui en porte : ignoré.
  W9 (i) KAPSO_API_KEY dans coffre.SECRETES, _ALLOWED_ENV_KEYS, RUBRIQUE_DE_CLE, appairage.CONSOLES et Settings.
Run (depuis backend/) : & $PY tests/test_whatsapp_comptes.py"""
import io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwacpt_"))
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


from fastapi import HTTPException                                    # noqa: E402
from fastapi.testclient import TestClient                            # noqa: E402
from app.config import settings, ENV_FILE                            # noqa: E402
from app.main import app                                             # noqa: E402
from app.api import routes as R                                      # noqa: E402
from app.services import comptes as CP, espaces as E, coffre as K, appairage as AP, espaces_paquet as EP  # noqa: E402
from app.services import storage                                     # noqa: E402

WA_PUBLICS = ["KAPSO_CUSTOMER_ID", "WHATSAPP_PHONE_ID", "WHATSAPP_NUMERO", "WHATSAPP_WABA_ID", "WHATSAPP_FACTURATION_META"]
SECRET = "SECRET-KAPSO-123"


def _leve(f, exc):
    try:
        f()
    except exc:
        return True
    return False


def poser_cle(v):
    """La clé plate, comme la pose Réglages (à chaud) : os.environ + settings."""
    os.environ["KAPSO_API_KEY"] = v
    if hasattr(settings, "KAPSO_API_KEY"):
        setattr(settings, "KAPSO_API_KEY", v)


def lire_doc():
    f = _tmp / "espaces" / "comptes.json"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


c = TestClient(app, client=("127.0.0.1", 50000))
c.__enter__()
E.lire()
rip = E.creer({"nom": "Rippled"})["id"]
autre = E.creer({"nom": "Autre"})["id"]

print("\n[a] la plateforme décrite")
g = c.get(f"/api/comptes?espace={rip}")
pw = (g.json().get("plateformes") or {}).get("whatsapp") if g.status_code == 200 else None
check("W1.1 GET /api/comptes : 200 et whatsapp listée", g.status_code == 200 and isinstance(pw, dict), g.text[:200])
check("W1.2 ses 5 champs publics, dans l'ordre, aucun secret",
      lambda: [x["nom"] for x in pw["champs"]] == WA_PUBLICS and not any(x["secret"] for x in pw["champs"]), repr(pw))
check("W1.3 aucun champ KAPSO_API_KEY ; requis = WHATSAPP_PHONE_ID ; pas d'OAuth",
      lambda: "KAPSO_API_KEY" not in [x["nom"] for x in pw["champs"]] and pw["requis"] == ["WHATSAPP_PHONE_ID"]
      and pw["oauth"] is False, repr(pw))
# t310 tâche 7, fix 1 (27/10/2026) : la plateforme dit le nom de sa clé plate et si elle est posée (cocher ne crée plus de compte)
check("W1.7 plateformes.whatsapp.cle_plate = {nom: KAPSO_API_KEY, posee: faux} sans clé ; aucune autre plateforme n'en a",
      lambda: pw["cle_plate"] == {"nom": "KAPSO_API_KEY", "posee": False}
      and not any("cle_plate" in v for k, v in g.json()["plateformes"].items() if k != "whatsapp"), repr(pw))
check("W1.4 PLATEFORMES garde 4 positions par entrée", all(len(v) == 4 for v in CP.PLATEFORMES.values()))
check("W1.5 constantes : CLE_PLATE, SANS_HISTORIQUE, CIBLES_EXPLICITES ; NON_PUBLIABLES retiré (t328)",
      lambda: CP.CLE_PLATE == {"whatsapp": "KAPSO_API_KEY"} and CP.SANS_HISTORIQUE == frozenset({"whatsapp"}) | CP.LIVE
      and CP.CIBLES_EXPLICITES == frozenset({"whatsapp"}) and not hasattr(CP, "NON_PUBLIABLES"))   # t318 : + comptes.LIVE (fusion t320)
check("W1.6 champs_poses_par_serveur(whatsapp) = tous ses champs publics",
      lambda: tuple(CP.champs_poses_par_serveur("whatsapp")) == tuple(WA_PUBLICS) and CP.champs_poses_par_serveur("x") == ())

print("\n[b] pas de compte historique")
poser_cle(SECRET)
gd = c.get("/api/comptes?espace=deepotus")
check("W2.1 clé plate posée, aucun compte : 200, aucun historique-whatsapp",
      gd.status_code == 200 and not any(x["id"] == "historique-whatsapp" for x in gd.json()["comptes"]), gd.text[:200])
check("W2.2 cle_kapso() lit la clé plate", lambda: CP.cle_kapso() == SECRET)
check("W2.3 clé posée : plateformes.whatsapp.cle_plate.posee vrai, la valeur nulle part dans la réponse",
      lambda: gd.json()["plateformes"]["whatsapp"]["cle_plate"] == {"nom": "KAPSO_API_KEY", "posee": True}
      and SECRET not in gd.text, gd.text[:200])

print("\n[c] disponible")
cw = c.post("/api/comptes", json={"espace_id": rip, "plateforme": "whatsapp", "libelle": "WA Rippled"})
check("W3.0 créer un compte whatsapp (sans valeurs) : 200", cw.status_code == 200, cw.text[:200])
wid = cw.json()["compte"]["id"] if cw.status_code == 200 else "c00000000"
check("W3.1 sans WHATSAPP_PHONE_ID : disponible faux", lambda: CP.obtenir(wid)["disponible"] is False)
CP.poser_publics_serveur(wid, {"WHATSAPP_PHONE_ID": "1234567890", "KAPSO_CUSTOMER_ID": "cus_1",
                               "WHATSAPP_FACTURATION_META": "customer_managed"})
check("W3.2 phone_id posé par le service et clé : disponible vrai", lambda: CP.obtenir(wid)["disponible"] is True)
check("W3.3 la vue porte cle_plate {nom, posee: vrai}",
      lambda: CP.obtenir(wid)["cle_plate"] == {"nom": "KAPSO_API_KEY", "posee": True})
poser_cle("")
check("W3.4 phone_id mais pas de clé : disponible faux, cle_plate.posee faux",
      lambda: CP.obtenir(wid)["disponible"] is False and CP.obtenir(wid)["cle_plate"]["posee"] is False)
poser_cle(SECRET)
check("W3.5 poser_publics_serveur change la révision et périme la vérification", lambda: (
    CP.noter_verification(wid, {"etat": "vert", "id_distant": "1234567890"}) is not None
    and (lambda r0: (CP.poser_publics_serveur(wid, {"WHATSAPP_NUMERO": "+33600000000"}),
                     CP.revision(wid) != r0 and CP.obtenir(wid)["verification"] is None)[1])(CP.revision(wid))))
check("W3.6 poser_publics_serveur refuse un champ étranger (ValueError)", lambda: _leve(
    lambda: CP.poser_publics_serveur(wid, {"KAPSO_API_KEY": "x"}), ValueError))
check("W3.7 un compte x n'a pas de cle_plate dans sa vue", lambda: "cle_plate" not in CP.obtenir(
    CP.creer({"espace_id": rip, "plateforme": "x", "libelle": "X Rippled"})["id"]))


print("\n[d] rien ne se saisit")
avant_doc, avant_env = lire_doc(), (ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else "")
for champ in WA_PUBLICS + ["KAPSO_API_KEY"]:
    r = c.post(f"/api/comptes/{wid}", json={"libelle": "renommé", "valeurs": {champ: "999"}})
    check(f"W4 POST valeurs {champ} : 400", r.status_code == 400, f"{r.status_code} {r.text[:160]}")
check("W4.1 rien d'écrit (comptes.json et .env inchangés, libellé gardé)",
      lire_doc() == avant_doc and (ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else "") == avant_env
      and CP.obtenir(wid)["libelle"] == "WA Rippled")
n0 = len(CP.lister(rip))
r = c.post("/api/comptes", json={"espace_id": rip, "plateforme": "whatsapp", "valeurs": {"WHATSAPP_PHONE_ID": "1"}})
check("W4.2 créer avec un champ posé par le serveur : 400, aucun compte créé", r.status_code == 400 and len(CP.lister(rip)) == n0,
      f"{r.status_code} {r.text[:160]}")

print("\n[e] t328 : une cible de publication (diffusion), de son espace seulement")
vues = CP.verifier_cibles(rip, [wid])
check("W5.1 verifier_cibles accepte le compte whatsapp de l'espace", len(vues) == 1 and vues[0]["plateforme"] == "whatsapp")
p = storage.ScheduledPost(title="t", channels="x", espace_id=rip)
try:
    R._poser_comptes(p, [wid]); code = None
except HTTPException as e:
    code = e.status_code
check("W5.2 R._poser_comptes : le post prend le compte, canal whatsapp",
      code is None and json.loads(p.comptes) == [wid] and p.channels == "whatsapp", repr((code, p.comptes, p.channels)))
try:
    CP.verifier_cibles(autre, [wid]); refuse = False
except PermissionError:
    refuse = True
check("W5.3 verifier_cibles refuse le compte whatsapp d'un autre espace (PermissionError)", refuse)

print("\n[f] jamais la valeur de la clé")
tout = json.dumps([c.get(f"/api/comptes?espace={rip}").json(), c.get("/api/comptes?espace=*").json(), CP.obtenir(wid)])
check("W6 la clé posée n'apparaît dans aucun JSON rendu", SECRET not in tout and "posee" in tout)
check("W6.1 ni dans comptes.json", SECRET not in lire_doc())

print("\n[g] coffre posé et fermé")
poser_cle("")
K.poser("mot-de-passe-de-banc", {"KAPSO_API_KEY": SECRET})
K.ouvrir("mot-de-passe-de-banc")
check("W7.0 coffre ouvert : cle_kapso() lit le coffre", lambda: CP.cle_kapso() == SECRET)
K.fermer()
poser_cle("")
check("W7.1 coffre posé et fermé", K.verrouille())
g7 = c.get(f"/api/comptes?espace={rip}")
vw = [x for x in g7.json().get("comptes", []) if x["id"] == wid] if g7.status_code == 200 else []
check("W7.2 GET /api/comptes 200, cle_plate.posee faux", g7.status_code == 200 and vw and vw[0]["cle_plate"]["posee"] is False
      and vw[0]["disponible"] is False, g7.text[:200])
_valeur = K.valeur
K.valeur = lambda nom: (_ for _ in ()).throw(K.CoffreVerrouille("fermé"))
try:
    check("W7.3 cle_kapso() ne lève jamais (coffre qui lève) : \"\"", lambda: CP.cle_kapso() == "")
finally:
    K.valeur = _valeur
K.ouvrir("mot-de-passe-de-banc")
K.ecrire_cle("KAPSO_API_KEY", "")
K.fermer()
K.FICHIER.unlink()
poser_cle(SECRET)

print("\n[h] le paquet d'espace")
data, _nom = EP.exporter(rip)
z = zipfile.ZipFile(io.BytesIO(data))
cj = json.loads(z.read("comptes.json"))
check("W8.1 export : aucun compte ni champ whatsapp", not any(x["plateforme"] == "whatsapp" for x in cj)
      and not any(k in json.dumps(cj) for k in WA_PUBLICS), json.dumps(cj)[:300])
cj.append({"plateforme": "whatsapp", "libelle": "WA glissé", "handle": "",
           "publics": {"WHATSAPP_PHONE_ID": "1234567890", "KAPSO_CUSTOMER_ID": "cus_1"}, "a_ressaisir": []})
b = io.BytesIO()
with zipfile.ZipFile(b, "w") as z2:
    for n in z.namelist():
        z2.writestr(n, json.dumps(cj) if n == "comptes.json" else z.read(n))
res = EP.importer(b.getvalue())
neuf = res["espace"]["id"]
check("W8.2 import : aucun compte whatsapp dans l'espace neuf",
      not any(x["plateforme"] == "whatsapp" for x in CP.lister(neuf)), json.dumps(CP.lister(neuf))[:300])
phones = [ch.get("valeur") for v in CP.lister(None) for ch in v["champs"] if ch["nom"] == "WHATSAPP_PHONE_ID"
          and ch.get("valeur")]
check("W8.3 deux espaces ne partagent jamais un WHATSAPP_PHONE_ID", len(phones) == len(set(phones)), repr(phones))
check("W8.4 l'import le dit dans `ignores`", any("WhatsApp" in x for x in res.get("ignores") or []), repr(res.get("ignores")))
# relecture finale (Minor 8) : un espace CLIENT exporté avec un consentement `whatsapp:<numéro>` : à l'import, ce
# consentement est écarté (le compte ne voyage pas), les autres consentements restent, et `ignores` le dit
from app.services import fiche_client as FC                          # noqa: E402
cli = E.creer({"nom": "Client paquet", "type": "client"})["id"]
FC.ajouter_consentement(cli, "whatsapp:PN-PAQUET", ["messages"], "ecrit")
FC.ajouter_consentement(cli, "telegram:chat-1", ["posts"], "ecrit")
data_c, _n = EP.exporter(cli)
zc = zipfile.ZipFile(io.BytesIO(data_c))
check("W8.5 l'export porte encore les deux consentements (la fiche voyage telle quelle)",
      sorted(x["canal_id"] for x in json.loads(zc.read("client.json"))["consentements"])
      == ["telegram:chat-1", "whatsapp:PN-PAQUET"])
res_c = EP.importer(data_c)
neuf_c = res_c["espace"]["id"]
canaux = [x["canal_id"] for x in FC.lire(neuf_c)["consentements"]]
check("W8.6 import : le consentement whatsapp:* est écarté, telegram gardé", canaux == ["telegram:chat-1"], repr(canaux))
check("W8.7 … et `ignores` le dit (consentement whatsapp:PN-PAQUET)",
      any("whatsapp:PN-PAQUET" in x and "WhatsApp" in x for x in res_c.get("ignores") or []), repr(res_c.get("ignores")))

print("\n[i] la clé connue partout")
from app.api.settings_routes import RUBRIQUE_DE_CLE                 # noqa: E402
check("W9.1 coffre.SECRETES", "KAPSO_API_KEY" in K.SECRETES)
check("W9.2 _ALLOWED_ENV_KEYS", "KAPSO_API_KEY" in R._ALLOWED_ENV_KEYS)
check("W9.3 RUBRIQUE_DE_CLE", "KAPSO_API_KEY" in RUBRIQUE_DE_CLE)
check("W9.4 appairage.CONSOLES (https)", any(x["cle"] == "KAPSO_API_KEY" and x["url"].startswith("https://") for x in AP.CONSOLES))
check("W9.5 Settings (str, vide par défaut)", "KAPSO_API_KEY" in type(settings).model_fields
      and type(settings).model_fields["KAPSO_API_KEY"].default == "")

c.__exit__(None, None, None)
print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
