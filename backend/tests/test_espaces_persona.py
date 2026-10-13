# -*- coding: utf-8 -*-
"""t201 (Espaces de marque E1, 13/10/2026) — le persona v2 PAR ESPACE.
Ce que ce banc garde : le moteur de prompt, la voix (voice_ids), News (modes de voix), la musique (squelette de
paroles), /persona et /templates lisent le persona de l'ESPACE ACTIF — plus de persona_id="deepotus" en dur ; un
travail lance sous un espace GARDE cet espace meme si l'utilisateur en active un autre pendant qu'il tourne (l'espace
est fige par requete) ; GET/PUT /api/espaces/{id}/persona valident (templates passes a PromptTemplate) et n'ecrivent
qu'apres validation ; Deepotus reste identique : son persona.json n'est pas reecrit par une lecture, et ce que lit le
moteur pour lui est le persona livre. Data-dir isole, rien de paye.
Temoin positif : la base (8a3aa1c2) a Pipeline(persona_id="deepotus") en dur et pas de route /espaces/{id}/persona.
Run (depuis backend/) : & $PY tests/test_espaces_persona.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzespp_"))
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


BASE = "8a3aa1c2"
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a le persona deepotus en dur et pas de route persona d'espace",
      b'Pipeline(persona_id="deepotus")' in r1.stdout and b'"/espaces/{espace_id}/persona"' not in r1.stdout)
src_routes = (RACINE / "backend/app/api/routes.py").read_text(encoding="utf-8")
check("T2 plus de persona « deepotus » en dur dans routes.py (Pipeline, lyrics_skeleton)",
      'Pipeline(persona_id="deepotus")' not in src_routes and 'lyrics_skeleton("deepotus"' not in src_routes)
for f in ("services/prompt_engine.py", "services/elevenlabs_service.py", "services/pipeline.py", "services/music_service.py", "services/news_voice.py"):
    s = (RACINE / "backend/app" / f).read_text(encoding="utf-8")
    check(f"T3 {f} : aucun persona_id par defaut « deepotus »", 'persona_id: str = "deepotus"' not in s
          and 'PromptEngine("deepotus")' not in s and 'or "deepotus"' not in s)

from app.services import espaces as ES                              # noqa: E402
from app.services.prompt_engine import PromptEngine                 # noqa: E402
from app.services import elevenlabs_service as EL                   # noqa: E402
from app.services import music_service as MU                        # noqa: E402
from app.services import news_voice as NV                           # noqa: E402

LIVRE = json.loads((RACINE / "backend/app/personas/deepotus.json").read_text(encoding="utf-8"))
P_DEEP = _tmp / "espaces" / "deepotus" / "persona.json"

print("[D] Deepotus inchange")
ES.lire()
octets = P_DEEP.read_bytes()
eng = PromptEngine()
check("D1 le moteur (sans argument) lit le persona de l'espace actif = Deepotus livre",
      eng.persona["display_name"] == LIVRE["display_name"] and len(eng.list_templates()) == len(LIVRE["templates"]))
check("D2 ... et pour Deepotus, ses champs livres sont rendus tels quels",
      all(eng.persona[k] == v for k, v in LIVRE.items()))
check("D3 lire le persona ne reecrit pas le fichier", P_DEEP.read_bytes() == octets)
check("D4 voix : les voice_ids de Deepotus (s'il en a) sont lus de l'espace",
      EL.VoiceoverService()._persona_voice_ids == (LIVRE.get("voice_ids") or {}))
check("D5 News : les modes de voix viennent du persona actif", set(NV._persona().get("voice_modes") or {}) == set(LIVRE.get("voice_modes") or {}))
check("D6 musique : le squelette porte le nom de Deepotus", LIVRE["display_name"].split(" — ")[0] in MU.lyrics_skeleton(theme="t"))

print("\n[A] un autre espace")
r = ES.creer({"nom": "Rippled"})
eid = r["id"]
ES.activer(eid)
check("A1 le MEME moteur suit l'espace actif (pas de persona fige a l'import)",
      eng.persona["display_name"] == "Rippled" and eng.list_templates() == [])
p2 = ES.persona(eid)
check("A2 persona v2 normalise : version 2, cles par defaut presentes (rien de Deepotus)",
      p2["version"] == 2 and p2["voice_modes"] == {} and p2["voice_ids"] == {} and p2["templates"] == []
      and "deepotus" not in json.dumps(p2).lower(), str(p2))
check("A3 musique et voix suivent", "Rippled" in MU.lyrics_skeleton(theme="t") and EL.VoiceoverService()._persona_voice_ids == {})
try:
    eng.get_template(LIVRE["templates"][0]["id"]); check("A4 un modele de Deepotus n'est pas visible depuis Rippled", False)
except KeyError:
    check("A4 un modele de Deepotus n'est pas visible depuis Rippled", True)

print("\n[F] l'espace fige pour un travail")
ES.activer("deepotus")
async def travail():
    with ES.sous_espace(eid):
        await asyncio.sleep(0)
        avant = PromptEngine().persona["display_name"]
        ES.activer("deepotus")                                       # l'utilisateur change d'espace pendant le travail
        await asyncio.sleep(0)
        return avant, PromptEngine().persona["display_name"]
check("F1 sous_espace : le travail garde son espace jusqu'au bout", asyncio.run(travail()) == ("Rippled", "Rippled"))
check("F2 hors du bloc, retour a l'espace actif", PromptEngine().persona["display_name"] == LIVRE["display_name"])
check("F3 PromptEngine(id) explicite lit cet espace", PromptEngine(eid).persona["display_name"] == "Rippled")
check("F4 un espace inconnu ou hostile ne lit rien du disque : repli sur l'espace actif",
      PromptEngine("../deepotus").persona["display_name"] == LIVRE["display_name"]
      and PromptEngine("esp_inconnu").persona["display_name"] == LIVRE["display_name"])

print("\n[V] ecrire un persona")
tpl = dict(LIVRE["templates"][0], id="rip_hero", name="Hero")
bon = {"display_name": "Rippled — XRPL", "vibe_keywords": ["ledger", "speed"], "default_negative_prompt": "no blur",
       "default_hashtags_pool": ["#XRPL"], "templates": [tpl], "identite": {"mission": "payer vite"},
       "audience": {"qui": "devs"}, "ton": {"registre": "net"}, "visuel": {}}
v = ES.ecrire_persona(eid, bon)
check("V1 ecrire : relu tel quel, persona_id force a l'id de l'espace, version 2",
      v["display_name"] == "Rippled — XRPL" and v["persona_id"] == eid and v["version"] == 2 and v["identite"] == {"mission": "payer vite"})
check("V2 le moteur voit le nouveau modele aussitot (fichier relu a la modification)",
      PromptEngine(eid).get_template("rip_hero").name == "Hero")
avant = ES.chemin(eid, "persona.json").read_bytes()
for mauvais, quoi in (({"display_name": ""}, "nom vide"), (dict(bon, templates=[{"id": "x"}]), "modele incomplet"),
                      (dict(bon, vibe_keywords="pas une liste"), "liste attendue"), (dict(bon, ton="texte"), "objet attendu"),
                      (dict(bon, default_negative_prompt=5), "texte attendu"), ("pas un objet", "pas un objet"),
                      (dict(bon, templates=[tpl, tpl]), "ids de modele en double")):
    try:
        ES.ecrire_persona(eid, mauvais); check(f"V3 refus : {quoi}", False)
    except ValueError:
        check(f"V3 refus : {quoi}", True)
check("V4 un refus n'ecrit RIEN", ES.chemin(eid, "persona.json").read_bytes() == avant)

print("\n[R] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
g = c.get(f"/api/espaces/{eid}/persona")
check("R1 GET persona d'un espace", g.status_code == 200 and g.json()["display_name"] == "Rippled — XRPL")
check("R2 GET persona inconnu / hors liste blanche -> 404",
      c.get("/api/espaces/esp_inconnu/persona").status_code == 404 and c.get("/api/espaces/a.b/persona").status_code == 404)
pu = c.put(f"/api/espaces/{eid}/persona", json=dict(bon, display_name="Rippled 2"))
check("R3 PUT ecrit", pu.status_code == 200 and pu.json()["display_name"] == "Rippled 2")
check("R4 PUT invalide -> 400", c.put(f"/api/espaces/{eid}/persona", json={"display_name": ""}).status_code == 400)
c.post(f"/api/espaces/{eid}/activate")
check("R5 /api/persona et /api/templates suivent l'espace actif",
      c.get("/api/persona").json()["display_name"] == "Rippled 2" and c.get("/api/templates").json()["persona"] == "Rippled 2")
c.post("/api/espaces/deepotus/activate")
check("R6 retour a Deepotus", c.get("/api/persona").json()["display_name"] == LIVRE["display_name"])
check("R7 Deepotus n'a jamais ete reecrit", P_DEEP.read_bytes() == octets)
print("\n[H] l'espace fige PAR REQUETE (middleware), herite par une tache de fond")
from fastapi.routing import APIRoute                                # noqa: E402
VU = {}
async def _banc_espace():
    async def fond():
        await asyncio.sleep(0.05)
        VU["fond"] = PromptEngine().persona["display_name"]
    VU["requete"] = PromptEngine().persona["display_name"]
    VU["tache"] = asyncio.get_running_loop().create_task(fond())
    return {"ok": True}
app.router.routes.insert(0, APIRoute("/api/__banc_espace", _banc_espace, methods=["POST"]))
async def scenario():
    import httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as ac:
        await ac.post(f"/api/espaces/{eid}/activate")
        await ac.post("/api/__banc_espace")
        await ac.post("/api/espaces/deepotus/activate")              # l'utilisateur change d'espace pendant le travail
        await VU["tache"]
asyncio.run(scenario())
check("H1 la requete lit l'espace actif a son arrivee", VU.get("requete") == "Rippled 2", str(VU))
check("H2 la tache de fond qu'elle a lancee GARDE cet espace apres le changement", VU.get("fond") == "Rippled 2", str(VU))
check("H3 apres coup, l'espace actif est bien Deepotus", PromptEngine().persona["display_name"] == LIVRE["display_name"])

dist = TestClient(app, client=("192.168.1.20", 50000))
check("R8 PUT depuis le reseau local sans jeton -> refuse", dist.put(f"/api/espaces/{eid}/persona", json=bon).status_code in (401, 403))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
