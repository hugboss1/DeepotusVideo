# -*- coding: utf-8 -*-
"""t200 (Espaces de marque E0, 13/10/2026) — le socle des ESPACES : plusieurs marques/projets sur une instance.
Spec docs/superpowers/specs/2026-10-13-espaces-de-marque.md, plan docs/superpowers/plans/2026-10-13-espaces-de-marque.md.
Ce que ce banc garde : la migration fait de l'existant l'espace « deepotus » A L'OCTET (persona.json = le fichier
livre, contenus.json = la liste Quick ACTUELLE tiree de prompts.jsx/screens.jsx, kit = le kit « deepotus ») ; un
espaces.json illisible est mis de cote, jamais ecrase ; on n'archive ni l'espace actif ni le dernier ; activer un
espace active son kit ; un id d'espace hors liste blanche n'atteint jamais le disque. Data-dir isole, rien de paye.
Temoin positif : la base (d71c971c) n'a ni le module ni les routes /espaces.
Run (depuis backend/) : & $PY tests/test_espaces_socle.py"""
import json, os, pathlib, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzesp_"))
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
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "d71c971c"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/espaces.py"], capture_output=True, cwd=str(RACINE))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a ni le module ni les routes /espaces", r0.returncode != 0 and r1.returncode == 0 and b'"/espaces"' not in r1.stdout)

print("[S] la graine Deepotus = la liste Quick actuelle")
rs = subprocess.run(["node", "scripts/espaces/extraire_contenus_deepotus.mjs", "--check"], capture_output=True, text=True, cwd=str(RACINE))
check("S1 deepotus_contenus.json est a jour de prompts.jsx + VIBES (node --check)", rs.returncode == 0, rs.stdout + rs.stderr)
GRAINE = json.loads((RACINE / "backend/app/espaces/deepotus_contenus.json").read_text(encoding="utf-8"))
ids = [t["id"] for t in GRAINE["prompt_templates"]]
check("S2 la graine porte les 15 modeles (deep-throne en tete), 7 categories, 7 ingredients, 8 vibes",
      ids[:1] == ["deep-throne"] and len(ids) == 15 and len(GRAINE["prompt_cats"]) == 7
      and len(GRAINE["ingredients"]) == 7 and len(GRAINE["vibes"]) == 8, str(ids))

try:
    from app.services import espaces as ES                          # noqa: E402
    from app.services import brand_kits as BK                       # noqa: E402
except ImportError as e:
    ES = None
    check("T2 le module existe", False, str(e))

PERSONA_LIVRE = (RACINE / "backend/app/personas/deepotus.json").read_bytes()
D = _tmp / "espaces"

print("[M] la migration")
if ES:
    BK.enregistrer({"name": "Client X"})                             # un 2e kit : le kit de deepotus reste « deepotus »
    doc = ES.lire()
    e0 = doc["espaces"].get("deepotus", {})
    check("M1 l'existant devient l'espace « deepotus », ACTIF, au kit « deepotus », non archive",
          doc["actif"] == "deepotus" and e0.get("nom") == "Deepotus" and e0.get("kit_id") == "deepotus" and e0.get("archive") is False, str(doc))
    check("M2 persona.json de l'espace = le persona livre A L'OCTET", (D / "deepotus" / "persona.json").read_bytes() == PERSONA_LIVRE)
    check("M3 contenus.json de l'espace = la graine (liste Quick actuelle) A L'OCTET",
          (D / "deepotus" / "contenus.json").read_bytes() == (RACINE / "backend/app/espaces/deepotus_contenus.json").read_bytes())
    b1 = (D / "espaces.json").read_bytes(); ES.lire(); ES.actif(); ES.lister()
    check("M4 idempotente : relire ne reecrit rien", (D / "espaces.json").read_bytes() == b1)
    (D / "deepotus" / "persona.json").write_text('{"modifie": true}', encoding="utf-8")
    (D / "espaces.json").write_text("{pas du json", encoding="utf-8")
    doc2 = ES.lire()
    cote = sorted(D.glob("espaces.json.illisible-*"))
    check("M5 espaces.json ILLISIBLE : mis de cote (intact), jamais ecrase ; deepotus repart",
          len(cote) == 1 and cote[0].read_text(encoding="utf-8") == "{pas du json" and list(doc2["espaces"]) == ["deepotus"], str([c.name for c in cote]))
    check("M6 ... et la migration ne RECOPIE pas par-dessus un persona deja present (modifie par l'utilisateur)",
          (D / "deepotus" / "persona.json").read_text(encoding="utf-8") == '{"modifie": true}')
    time.sleep(1.1)
    (D / "espaces.json").write_text(json.dumps({"actif": "x", "espaces": {"../evasion": {}}}), encoding="utf-8")
    ES.lire()
    check("M7 structure invalide (id interdit) : mise de cote aussi", len(sorted(D.glob("espaces.json.illisible-*"))) == 2)
    (D / "deepotus" / "persona.json").write_bytes(PERSONA_LIVRE)

print("\n[E] le service")
if ES:
    kits_avant = set(BK.lire()["kits"])
    r = ES.creer({"nom": "  Rippled  ", "couleur": "#3355ff"})
    eid = r["id"]
    vue = {e["id"]: e for e in ES.lister()}
    check("E1 creer : id esp_xxxxxxxx, nom nettoye, couleur gardee, NON actif", eid.startswith("esp_") and len(eid) == 12
          and vue[eid]["nom"] == "Rippled" and vue[eid]["couleur"] == "#3355ff" and vue[eid]["actif"] is False, str(vue.get(eid)))
    pers = json.loads((D / eid / "persona.json").read_text(encoding="utf-8"))
    cont = json.loads((D / eid / "contenus.json").read_text(encoding="utf-8"))
    check("E2 un espace neuf a un persona SQUELETTE a son nom (rien de Deepotus) et des contenus vides",
          pers.get("persona_id") == eid and pers.get("display_name") == "Rippled" and "deepotus" not in json.dumps(pers).lower()
          and cont == {"version": 1, "prompt_templates": [], "prompt_cats": [], "ingredients": {}, "vibes": []}, str(pers) + str(cont))
    check("E3 un espace neuf recoit son PROPRE kit (cree, au nom de l'espace) — il ne partage pas celui de Deepotus",
          vue[eid]["kit_id"] not in kits_avant and BK.lire()["kits"][vue[eid]["kit_id"]]["name"] == "Rippled")
    _k = BK.lire()["kits"][vue[eid]["kit_id"]]
    check("E3b ... et ce kit ne porte rien de Deepotus (taglines comprises : t202, vu à l'écran)",
          _k["app_name"] == "RIPPLED" and _k["tagline_1"] == "Rippled" and "deep" not in json.dumps(_k).lower(), str(_k))
    r2 = ES.creer({"nom": "Client", "kit_id": "deepotus"})
    check("E4 creer avec un kit EXISTANT le reprend sans en creer", r2["kit_id"] == "deepotus")
    for mauvais, quoi in (({"nom": ""}, "nom vide"), ({"nom": "A", "couleur": "rouge"}, "couleur"), ({"nom": "A", "kit_id": "inconnu"}, "kit inconnu")):
        try:
            ES.creer(mauvais); check(f"E5 refus ({quoi})", False)
        except ValueError:
            check(f"E5 refus ({quoi})", True)
    ES.activer(eid)
    check("E6 activer : l'espace devient actif ET son kit devient le kit actif", ES.actif()["id"] == eid and BK.actif()["id"] == vue[eid]["kit_id"])
    for x, attendu in ((eid, "actif"), ("absent", "absent")):
        check(f"E7 archiver refuse : {attendu}", ES.archiver(x, True) == attendu)
    ES.activer("deepotus")
    check("E8 archiver un espace inactif", ES.archiver(r2["id"], True) == "ok" and all(e["id"] != r2["id"] for e in ES.lister()))
    check("E9 ... il reste listable avec les archives, et non activable", any(e["id"] == r2["id"] and e["archive"] for e in ES.lister(archives=True)))
    try:
        ES.activer(r2["id"]); check("E10 activer un archive est refuse", False)
    except ValueError:
        check("E10 activer un archive est refuse", True)
    check("E11 desarchiver", ES.archiver(r2["id"], False) == "ok" and any(e["id"] == r2["id"] for e in ES.lister()))
    ES.archiver(r2["id"], True); ES.archiver(eid, True)
    check("E12 on n'archive pas le DERNIER espace non archive", ES.archiver("deepotus", True) in ("actif", "seul"))
    ES.modifier(eid, {"nom": "Rippled XRPL", "couleur": "#000000"})
    check("E13 modifier nom/couleur", {e["id"]: e for e in ES.lister(archives=True)}[eid]["nom"] == "Rippled XRPL")
    for evil in ("..", "../deepotus", "a/b", "deepotus\\..", "", "x" * 60):
        check(f"E14 id refuse sans toucher le disque : {evil!r}", ES.chemin(evil, "persona.json") is None)
    check("E15 chemin valide = DATA_ROOT/espaces/<id>/<fichier>", ES.chemin("deepotus", "persona.json") == D / "deepotus" / "persona.json")
    check("E16 contenus(id) lit le fichier de l espace",
          ES.contenus("deepotus")["prompt_templates"][0]["id"] == "deep-throne")

print("\n[R] les routes")
if ES:
    from fastapi.testclient import TestClient                       # noqa: E402
    from app.main import app                                        # noqa: E402
    c = TestClient(app)
    g = c.get("/api/espaces")
    check("R1 GET /api/espaces : liste + actif", g.status_code == 200 and g.json()["actif"] == "deepotus"
          and any(e["id"] == "deepotus" for e in g.json()["espaces"]), g.text[:200])
    p = c.post("/api/espaces", json={"nom": "Banc"})
    nid = p.json().get("espace", {}).get("id", "")
    check("R2 POST /api/espaces cree", p.status_code == 200 and nid.startswith("esp_"), p.text[:200])
    check("R3 POST nom vide -> 400", c.post("/api/espaces", json={"nom": " "}).status_code == 400)
    a = c.post(f"/api/espaces/{nid}/activate")
    check("R4 activate -> espace et kit actifs", a.status_code == 200 and a.json()["actif"] == nid and c.get("/api/espaces/actif").json()["id"] == nid)
    check("R5 activate inconnu -> 404", c.post("/api/espaces/esp_inconnu/activate").status_code == 404)
    check("R6 archiver l'actif -> 400", c.post(f"/api/espaces/{nid}/archive", json={"archive": True}).status_code == 400)
    c.post("/api/espaces/deepotus/activate")
    check("R7 archiver un inactif -> 200", c.post(f"/api/espaces/{nid}/archive", json={"archive": True}).status_code == 200)
    ct = c.get("/api/espaces/deepotus/contenus")
    check("R8 GET contenus de deepotus = la graine", ct.status_code == 200 and ct.json() == GRAINE)
    check("R9 GET contenus d'un id hors liste blanche -> 404", c.get("/api/espaces/a.b/contenus").status_code == 404)
    h = c.get("/api/espaces/..%2Fdeepotus/contenus")
    check("R9b ..%2F n'atteint pas la route (page de l'app servie, jamais les contenus)", h.headers.get("content-type", "").startswith("text/html"))
    check("R10 POST /espaces/{id} modifie", c.post(f"/api/espaces/{nid}", json={"nom": "Banc 2"}).status_code == 200)
    dist = TestClient(app, client=("192.168.1.20", 50000))
    nb = len(c.get("/api/espaces?archives=true").json()["espaces"])
    check("R11 ecriture depuis le reseau local sans jeton d'appareil -> refusee (401/403), rien de cree",
          dist.post("/api/espaces", json={"nom": "Intrus"}).status_code in (401, 403) and len(c.get("/api/espaces?archives=true").json()["espaces"]) == nb)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
