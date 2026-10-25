# -*- coding: utf-8 -*-
"""t306 (25/10/2026) — Boite a outils, lot A1 : le TYPE d'un espace (marque / produit / client), son PARENT et le
CLIENT RESPONSABLE. Ce que ce banc garde : l'absence de `type` dans espaces.json vaut « marque » sans reecriture ;
un parent n'existe que pour un produit, et c'est une marque ou un client existant ; le client responsable d'un
espace est lui-meme (client) ou son parent client, MEME ARCHIVE, sinon rien. Data-dir isole, rien de paye.
Sections : 1 type et parent, 2 client responsable, 3 fiche client et consentements, 4 routes,
5 la fiche dans le paquet d'espace, 6 client.json illisible mis de cote (t306, Task 6).
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
# t306 (25/10/2026) : le parent ne compte que pour un produit ; une marque retouchee a la main avec un parent client : aucun
_doc_h = E.lire(); _mq = E.creer({"nom": "Marque a la main", "type": "marque"})
_doc_h = E.lire(); _doc_h["espaces"][_mq["id"]]["parent"] = c["id"]; E._ecrire(_doc_h)
check("2f marque avec un parent pose a la main : client_responsable = None", E.client_responsable(_mq["id"]) is None)

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

check("4m canal_id de la plateforme x accepte, ':123' refuse", bool(F.CANAL_ID.match("x:123")) and not F.CANAL_ID.match(":123")
      and not F.CANAL_ID.match("x 123"))
F.ajouter_consentement(cl["id"], "x:123", ["publier"], "ecrit")
check("4n consentement x:123 ajoute (le precedent etait revoque)", F.consentement_en_cours(cl["id"], "x:123"))
check("4o second consentement en cours sur le meme canal refuse", _leve(ValueError, F.ajouter_consentement, cl["id"], "x:123", ["publier"], "doigt"))
check("4p permis : vide, trop long, mot invalide refuses", all(_leve(ValueError, F.ajouter_consentement, cl["id"], "tiktok:1", p, "ecrit")
      for p in ([], ["a"] * 11, ["Publier!"], "publier")))

print("[5] la fiche dans le paquet d'espace")
import io, zipfile                                                  # noqa: E402
from app.services import espaces_paquet as PQ                       # noqa: E402


def _zip(entrees):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, v in entrees.items():
            z.writestr(n, v if isinstance(v, (bytes, str)) else json.dumps(v))
    return b.getvalue()


def _sans_journal(x):
    return {k: v for k, v in x.items() if k != "journal"}


pc = E.creer({"nom": "Epicerie Paquet", "type": "client"})
F.ecrire(pc["id"], {"societe": "Epicerie SARL", "pays": "fr", "mode_publication": "publie_en_son_nom",
                    "contact": {"nom": "Jo", "email": "jo@example.org"}})
F.ajouter_consentement(pc["id"], "instagram:555", ["publier"], "whatsapp")
F.ajouter_consentement(pc["id"], "facebook:42", ["publier"], "ecrit")
F.revoquer(pc["id"], "facebook:42")
src = F.lire(pc["id"])
data, _nom = PQ.exporter(pc["id"])
zf = zipfile.ZipFile(io.BytesIO(data))
tout = b"".join(zf.read(n) for n in zf.namelist()).decode("utf-8", "replace").lower()
check("5a l'export d'un client contient client.json, sans sk- ni jeton", "client.json" in zf.namelist()
      and "sk-" not in tout and "jeton" not in tout)
check("5b client.json = la fiche validee", json.loads(zf.read("client.json")) == F.valider(src))
ent = json.loads(zf.read("espace.json"))["espace"]
check("5c espace.json porte type et parent", ent["type"] == "client" and ent["parent"] is None)
r = PQ.importer(data)
nv = F.lire(r["espace"]["id"])
check("5d import : espace neuf de type client", r["espace"]["type"] == "client" and r["espace"]["id"] != pc["id"])
check("5e fiche identique hors journal", _sans_journal(nv) == _sans_journal(src))
check("5f une ligne import ajoutee au journal", nv["journal"][:-1] == src["journal"] and nv["journal"][-1]["quoi"] == "import")
check("5g rien a signaler pour un paquet propre", r["ignores"] == [])

paq = json.loads(zf.read("client.json")); del paq["mode_publication"]
r2 = PQ.importer(_zip({"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": paq}))
check("5h fiche sans mode_publication : valide_par_client", F.lire(r2["espace"]["id"])["mode_publication"] == "valide_par_client")

prod = E.creer({"nom": "Confiture", "type": "produit", "parent": pc["id"]})
d_prod, _ = PQ.exporter(prod["id"])
check("5i un produit n'emporte pas de client.json", "client.json" not in zipfile.ZipFile(io.BytesIO(d_prod)).namelist())
r3 = PQ.importer(d_prod)
check("5j parent present : garde", r3["espace"]["type"] == "produit" and r3["espace"]["parent"] == pc["id"])
tete = json.loads(zf.read("espace.json")); tete["espace"].update(type="produit", parent="esp_zzzzzzzz")
r4 = PQ.importer(_zip({"espace.json": tete, "persona.json": zf.read("persona.json")}))
check("5k parent absent : None et motif dans ignores", r4["espace"]["parent"] is None and r4["espace"]["type"] == "produit"
      and any("parent" in x for x in r4["ignores"]), str(r4["ignores"]))

mauvaise = dict(paq, consentements=paq["consentements"] + [{"canal_id": "pas un canal", "permis": ["publier"],
                                                              "date": "2026-10-25T10:00:00"}])
avant = len(E.lire()["espaces"])
r5 = PQ.importer(_zip({"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": mauvaise}))
check("5l ligne de consentement fautive : ecartee ET dite", len(F.lire(r5["espace"]["id"])["consentements"]) == len(paq["consentements"])
      and any("consentement n°3" in x for x in r5["ignores"]), str(r5["ignores"]))
moyen = dict(paq, consentements=[dict(paq["consentements"][0], moyen="telepathie")], journal=[
    {"quand": "2026-10-25T10:00:00", "quoi": "consentement", "canal_id": "xx yy", "qui": "robot"},
    {"quand": "", "quoi": "import", "canal_id": "", "qui": "client"}])
r6 = PQ.importer(_zip({"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": moyen}))
mots = " | ".join(r6["ignores"])
check("5m moyen reecrit, canal et auteur de journal reecrits, ligne sans date ecartee : tout dit",
      "moyen inconnu" in mots and "canal invalide" in mots and "auteur inconnu" in mots and "journal n°2 écartée" in mots, mots)
avant = len(E.lire()["espaces"])
check("5n client.json qui n'est pas un objet : paquet refuse, rien d'ecrit", _leve(ValueError, PQ.importer, _zip(
    {"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": "[1,2]"}))
      and len(E.lire()["espaces"]) == avant)
check("5o client.json non JSON : paquet refuse, rien d'ecrit", _leve(ValueError, PQ.importer, _zip(
    {"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": "{pas du json"}))
      and len(E.lire()["espaces"]) == avant)
_vrai = F._poser
def _casse(eid, fiche):
    raise OSError("disque plein")
F._poser = _casse
try:
    leve = _leve(OSError, PQ.importer, data)
finally:
    F._poser = _vrai
check("5p retour arriere si l'ecriture de la fiche echoue", leve and len(E.lire()["espaces"]) == avant)

# t306 (25/10/2026) : un seul consentement actif par canal
print("[5b] deux consentements actifs sur un meme canal")
dbl = E.creer({"nom": "Double SA", "type": "client"})
ligne = lambda d, m: {"canal_id": "instagram:9", "permis": ["publier"], "date": d, "moyen": m, "revoque_le": None}
brut_dbl = dict(F.valider({}), consentements=[ligne("2026-10-01T10:00:00", "ecrit"), ligne("2026-10-02T10:00:00", "doigt")])
fd = E.chemin(dbl["id"], "client.json")
_vraie_valider = F.valider
F.valider = lambda d: d          # contourne la normalisation : la carte contient bien DEUX lignes actives sur le disque
try:
    fd.write_text(json.dumps(brut_dbl), encoding="utf-8")
    F.revoquer(dbl["id"], "instagram:9")
    apres = json.loads(fd.read_text(encoding="utf-8"))
finally:
    F.valider = _vraie_valider
check("5q revoquer ferme TOUTES les lignes actives du canal", all(x["revoque_le"] for x in apres["consentements"])
      and len(apres["consentements"]) == 2 and not F.consentement_en_cours(dbl["id"], "instagram:9")
      and sum(1 for x in apres["journal"] if x["quoi"] == "revocation") == 1)
fd.write_text(json.dumps(brut_dbl), encoding="utf-8")
lu_dbl = F.lire(dbl["id"])["consentements"]
check("5r valider/lire : une seule ligne active, la plus recente ; l'autre est close, pas supprimee",
      len(lu_dbl) == 2 and [x["revoque_le"] is None for x in lu_dbl] == [False, True] and lu_dbl[1]["moyen"] == "doigt"
      and lu_dbl[0]["revoque_le"] == "2026-10-02T10:00:00")
F.revoquer(dbl["id"], "instagram:9")
check("5s apres lecture normalisee puis revoquer : le canal est ferme", not F.consentement_en_cours(dbl["id"], "instagram:9"))
dpq = dict(paq, consentements=[ligne("2026-10-01T10:00:00", "ecrit"), ligne("2026-10-02T10:00:00", "doigt")])
r7 = PQ.importer(_zip({"espace.json": zf.read("espace.json"), "persona.json": zf.read("persona.json"), "client.json": dpq}))
cs7 = F.lire(r7["espace"]["id"])["consentements"]
check("5t import de deux actifs sur un canal : un seul reste actif, et ignores le dit",
      sum(1 for x in cs7 if x["revoque_le"] is None) == 1 and any("consentement n°1" in x and "plus récent" in x for x in r7["ignores"]),
      str(r7["ignores"]))

print("[6] client.json illisible : mis de cote, jamais perdu")
fch = E.chemin(pc["id"], "client.json")
garbage = bytes([0xFF, 0xFE]) + b"{pas du json ###"
fch.write_bytes(garbage)
lu = F.lire(pc["id"])
cotes = sorted(fch.parent.glob("client.json.illisible-*"))
check("6a fiche illisible : lue aux defauts", lu == F.valider({}))
check("6b copie .illisible- avec les octets d'origine, original retire", len(cotes) == 1 and cotes[0].read_bytes() == garbage
      and not fch.exists())
F.ecrire(pc["id"], {"societe": "Epicerie bis"})
check("6c un ecrire ulterieur ne detruit pas la copie", cotes[0].is_file() and cotes[0].read_bytes() == garbage
      and F.lire(pc["id"])["societe"] == "Epicerie bis")
fch.write_text("{illisible encore", encoding="utf-8")
F.lire(pc["id"])
check("6d un second fichier illisible ne remplace pas le premier", len(sorted(fch.parent.glob("client.json.illisible-*"))) == 2
      and cotes[0].read_bytes() == garbage)
fch.unlink(missing_ok=True)
check("6e fichier absent : defauts, rien de mis de cote", F.lire(pc["id"]) == F.valider({})
      and len(sorted(fch.parent.glob("client.json.illisible-*"))) == 2)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
