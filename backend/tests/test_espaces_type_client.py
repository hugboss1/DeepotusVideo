# -*- coding: utf-8 -*-
"""t306 (25/10/2026) — Boite a outils, lot A1 : le TYPE d'un espace (marque / produit / client), son PARENT et le
CLIENT RESPONSABLE. Ce que ce banc garde : l'absence de `type` dans espaces.json vaut « marque » sans reecriture ;
un parent n'existe que pour un produit, et c'est une marque ou un client existant ; le client responsable d'un
espace est lui-meme (client) ou son parent client, MEME ARCHIVE, sinon rien. Data-dir isole, rien de paye.
Sections : 1 type et parent, 2 client responsable, 3 fiche client et consentements, 4 routes.
Run (depuis backend/) : & $PY tests/test_espaces_type_client.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzetc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
os.environ["HEYGEN_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _leve(exc, fn, *a, **k):
    """True si fn(*a, **k) leve exc."""
    try:
        fn(*a, **k)
    except exc:
        return True
    except Exception:  # noqa: BLE001 — une autre exception n'est pas celle qu'on attend
        return False
    return False


from app.services import espaces as E                               # noqa: E402

print("[1] type et parent")
check("1a Deepotus est une marque", E.actif()["type"] == "marque" and E.actif()["parent"] is None)
octets = (E.dossier() / "espaces.json").read_bytes(); E.lister()
check("1b lire n'ecrit pas le type", (E.dossier() / "espaces.json").read_bytes() == octets)
c = E.creer({"nom": "Boulangerie Lune", "type": "client"})
p = E.creer({"nom": "Pain du matin", "type": "produit", "parent": c["id"]})
check("1c produit d'un client", p["type"] == "produit" and p["parent"] == c["id"])
check("1d type inconnu refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "agence"}))
check("1e parent sur une marque refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "marque", "parent": c["id"]}))
check("1f produit d'un produit refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": p["id"]}))
check("1g parent inconnu refuse", _leve(ValueError, E.creer, {"nom": "x", "type": "produit", "parent": "esp_00000000"}))

# 1h-1m : modifier(type / parent) — mêmes règles qu'à la création
m = E.creer({"nom": "Marque Soleil", "type": "marque"})
q = E.creer({"nom": "Produit libre", "type": "produit"})
check("1h produit sans parent recoit un parent par modifier",
      E.modifier(q["id"], {"parent": m["id"]})["parent"] == m["id"])
check("1i un espace utilise comme parent ne devient pas produit",
      _leve(ValueError, E.modifier, m["id"], {"type": "produit"}) and E.lister()[0]["type"] in E.TYPES
      and next(v for v in E.lister() if v["id"] == m["id"])["type"] == "marque")
r = E.modifier(q["id"], {"type": "marque"})
check("1j produit -> marque efface le parent", r["type"] == "marque" and r["parent"] is None)
q2 = E.creer({"nom": "Produit deux", "type": "produit", "parent": m["id"]})
r = E.modifier(q2["id"], {"type": "client"})
check("1k produit -> client efface le parent", r["type"] == "client" and r["parent"] is None)
q3 = E.creer({"nom": "Produit trois", "type": "produit"})
try:
    E.modifier(q3["id"], {"parent": q3["id"]}); msg = ""
except ValueError as ex:
    msg = str(ex)
check("1l parent = soi-meme refuse, message dit « propre parent »", "propre parent" in msg, msg)
cx = E.creer({"nom": "Client Consent", "type": "client"})
_orig = E._consentements_en_cours
E._consentements_en_cours = lambda eid: [{"canal_id": "x:1"}]
check("1m client -> marque avec consentements : ConflitClient", _leve(E.ConflitClient, E.modifier, cx["id"], {"type": "marque"})
      and next(v for v in E.lister() if v["id"] == cx["id"])["type"] == "client")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app) as tc:
    rr = tc.post(f"/api/espaces/{cx['id']}", json={"type": "marque"})
    rv = tc.post(f"/api/espaces/{cx['id']}", json={"type": "agence"})
check("1n la route repond 409 (consentements en cours)", rr.status_code == 409, f"{rr.status_code} {rr.text[:120]}")
check("1o la route repond 400 pour un type inconnu", rv.status_code == 400, f"{rv.status_code} {rv.text[:120]}")
E._consentements_en_cours = _orig
check("1p sans consentement, client -> marque passe", E.modifier(cx["id"], {"type": "marque"})["type"] == "marque")

print("[2] client responsable")
check("2a client lui-meme", E.client_responsable(c["id"]) == c["id"])
check("2b produit -> son client", E.client_responsable(p["id"]) == c["id"])
check("2c marque -> aucun", E.client_responsable("deepotus") is None)
E.archiver(c["id"])
check("2d client archive reste responsable", E.client_responsable(p["id"]) == c["id"])

print("[3] fiche client et consentements (c est archive depuis 2d : sa fiche reste lisible et ecrivible)")
from app.services import fiche_client as F                          # noqa: E402
f = F.lire(c["id"])
check("3a defauts prudents", f["mode_publication"] == "valide_par_client" and f["consentements"] == [])
check("3b marque sans fiche", _leve(ValueError, F.lire, "deepotus"))
check("3b' espace inconnu : KeyError", _leve(KeyError, F.lire, "esp_inconnu"))
F.ecrire(c["id"], {"societe": "Lune SARL", "mode_publication": "publie_en_son_nom", "jeton_x": "sk-123"})
brut = E.chemin(c["id"], "client.json").read_text(encoding="utf-8")
check("3c cle inconnue jamais ecrite", "jeton_x" not in brut and "sk-123" not in brut)
check("3d changement de mode au journal", F.lire(c["id"])["journal"][-1]["quoi"] == "mode")
check("3e canal_id fautif refuse", _leve(ValueError, F.ajouter_consentement, c["id"], "x 123", ["publier"], "ecrit"))
F.ajouter_consentement(c["id"], "instagram:17841400000", ["publier"], "doigt")
check("3f consentement en cours", F.consentement_en_cours(c["id"], "instagram:17841400000"))
check("3g ecrire ne touche pas aux consentements", _leve(ValueError, F.ecrire, c["id"], {"consentements": []})
      and _leve(ValueError, F.ecrire, c["id"], {"journal": []}))
check("2e retrait du type client refuse", _leve(E.ConflitClient, E.modifier, c["id"], {"type": "marque"})
      and E.client_responsable(c["id"]) == c["id"])
F.revoquer(c["id"], "instagram:17841400000")
check("3h revoque", not F.consentement_en_cours(c["id"], "instagram:17841400000")
      and F.lire(c["id"])["journal"][-1]["quoi"] == "revocation")
check("3i rien a revoquer : KeyError", _leve(KeyError, F.revoquer, c["id"], "instagram:17841400000"))
check("3j pays, langue, notes, mode refuses", all(_leve(ValueError, F.ecrire, c["id"], x) for x in (
    {"pays": "FRA"}, {"langue": "de"}, {"notes": "x" * 4001}, {"mode_publication": "auto"})))
check("3k pays en majuscules, mode inchange sans ligne de journal", F.ecrire(c["id"], {"pays": "fr", "mode_publication": "publie_en_son_nom"})["pays"] == "FR"
      and [j["quoi"] for j in F.lire(c["id"])["journal"]] == ["mode", "consentement", "revocation"])
F.noter(c["id"], "publication", "instagram:17841400000", "telephone")
check("3l noter ajoute une ligne", F.lire(c["id"])["journal"][-1]["qui"] == "telephone")
doc_long = {"journal": [{"quand": f"2026-10-25T10:00:{i % 60:02d}", "quoi": "import", "canal_id": "", "qui": "client"}
                        for i in range(F.MAX_JOURNAL + 50)]}
check("3m journal borne a 2000 lignes", len(F.valider(doc_long)["journal"]) == F.MAX_JOURNAL)
check("3n valider(n'importe quoi) rend la fiche complete", F.valider(None) == F.valider({}) and F.valider([1])["version"] == 1
      and F.valider({"consentements": "x", "contact": 3})["contact"]["nom"] == "")
fx = json.loads((_ICI / "fixtures_client_v1.json").read_text(encoding="utf-8"))
check("3o la fixture v1 est un point fixe de valider", F.valider(fx) == fx and len(fx["consentements"]) == 2
      and len(fx["journal"]) == 3 and any(x["revoque_le"] for x in fx["consentements"]))
check("3p retrait du type client possible une fois revoque", E.modifier(c["id"], {"type": "marque"})["type"] == "marque")

print("[4] routes")
ENT = "/api/espaces/%s/client"
cl = E.creer({"nom": "Client Routes", "type": "client"})
with TestClient(app) as tc:
    g = tc.get(ENT % cl["id"])
    check("4a GET 200, mode prudent", g.status_code == 200 and g.json()["mode_publication"] == "valide_par_client", g.text[:120])
    pu = tc.put(ENT % cl["id"], json={"societe": "Soleil SA", "contact": {"nom": "Ana"}, "langue": "en"})
    check("4b PUT 200", pu.status_code == 200 and pu.json()["societe"] == "Soleil SA" and pu.json()["contact"]["nom"] == "Ana", pu.text[:120])
    po = tc.post(ENT % cl["id"] + "/consentements", json={"canal_id": "facebook:123", "permis": ["publier"], "moyen": "ecrit"})
    check("4c POST consentement 200", po.status_code == 200 and po.json()["consentements"][0]["canal_id"] == "facebook:123", po.text[:120])
    check("4d consentement fautif 400", tc.post(ENT % cl["id"] + "/consentements", json={"canal_id": "x 1", "permis": ["publier"], "moyen": "ecrit"}).status_code == 400)
    check("4e PUT champ interdit 400", tc.put(ENT % cl["id"], json={"journal": []}).status_code == 400)
    check("4f retrait du type par la route : 409 tant que le consentement court",
          tc.post(f"/api/espaces/{cl['id']}", json={"type": "marque"}).status_code == 409)
    r1 = tc.post(ENT % cl["id"] + "/consentements/revoquer", json={"canal_id": "facebook:123"})
    r2 = tc.post(ENT % cl["id"] + "/consentements/revoquer", json={"canal_id": "facebook:123"})
    check("4g revoquer 200 puis 404", r1.status_code == 200 and r1.json()["consentements"][0]["revoque_le"] and r2.status_code == 404, f"{r1.status_code} {r2.status_code}")
    check("4h espace inconnu 404 partout", all(x.status_code == 404 for x in (
        tc.get(ENT % "esp_nope"), tc.put(ENT % "esp_nope", json={}),
        tc.post(ENT % "esp_nope" + "/consentements", json={}), tc.post(ENT % "esp_nope" + "/consentements/revoquer", json={}))))
    check("4i marque sans fiche : 400", tc.get(ENT % "deepotus").status_code == 400 and tc.put(ENT % "deepotus", json={}).status_code == 400)
sys.path.insert(0, str(_ICI))
from _jeton_appareil import entetes                                 # noqa: E402
jeton = entetes(app)
lan = TestClient(app, client=("192.168.1.20", 50000))
check("4j reseau local avec jeton : lecture 200", lan.get(ENT % cl["id"], headers=jeton).status_code == 200)
w = [lan.put(ENT % cl["id"], json={"societe": "Pirate"}, headers=jeton),
     lan.post(ENT % cl["id"] + "/consentements", json={"canal_id": "facebook:9", "permis": ["publier"], "moyen": "ecrit"}, headers=jeton),
     lan.post(ENT % cl["id"] + "/consentements/revoquer", json={"canal_id": "facebook:123"}, headers=jeton)]
check("4k reseau local avec jeton : ecritures 403", [x.status_code for x in w] == [403, 403, 403], str([x.status_code for x in w]))
check("4l rien n'a ete ecrit", F.lire(cl["id"])["societe"] == "Soleil SA" and len(F.lire(cl["id"])["consentements"]) == 1)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
