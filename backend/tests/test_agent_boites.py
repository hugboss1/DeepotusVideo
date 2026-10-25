# -*- coding: utf-8 -*-
"""t305 (lot A0, boîtes à outils de l'agent) — banc des boîtes à outils de l'agent.
Ce que ce banc garde, par sections numérotées :
  1. Compatibilité : l'agent Campagnes voit exactement les dix outils figés à e0d6e51e
     (fixture agent_definitions_campagnes.json, écrite par _agent_definitions_capture.py).
  2. Invariants des boîtes (registre sain, une boîte par outil, natures connues, Campagnes inchangé, paquet mobile).
  3. Le refus hors boîte : un outil hors de la boîte de l'agent du tour est refusé par executer.
La section 4 arrive avec la tâche 3 du lot A0.
Données isolées (DEEPOTUS_DATA_DIR temporaire), clés vidées, rien de payé.
Run (depuis backend/) : & $PY tests/test_agent_boites.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzboites_"))
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


from app.services import agent_outils as ao                         # noqa: E402

print("[1] compatibilite : Campagnes voit les memes outils qu'a e0d6e51e")
fige = json.loads((_ICI / "agent_definitions_campagnes.json").read_text(encoding="utf-8"))
check("1a definitions() inchangees a l'octet", ao.definitions() == fige)
check("1b dix outils", len(fige) == 10)

from app.services import agent_boites as B                          # noqa: E402

print("\n[2] invariants des boites")
check("2a registre sain", B.verifier() == [], B.verifier())
check("2b chaque outil a exactement une boite",
      all(sum(o in b["outils"] for b in B.BOITES.values()) == 1 for o in ao.OUTILS))
check("2c natures connues", all(ao.OUTILS[o]["nature"] in B.NATURES for b in B.BOITES.values() for o in b["outils"]))
check("2d Campagnes inchange via les boites", B.definitions_pour("campagnes") == fige)
check("2e agent inconnu = aucun outil", B.definitions_pour("personne") == [])
check("2f paquet mobile", [b["id"] for b in B.paquet_mobile()] == ["campagnes"]
      and B.paquet_mobile()[0]["outils"] == fige)

print("\n[3] le refus hors boite")
r = asyncio.run(ao.executer("lire_espace", {}, ao.Ctx(cid="c1", agent="whatsapp")))
check("3a outil hors de la boite refuse", r["ok"] is False and "boîte" in r["resume"], r)
r = asyncio.run(ao.executer("chercher_app", {"question": "vectorlab"}, ao.Ctx(cid="c1")))
check("3b Campagnes garde ses outils", r["ok"] is True, r)

print("\n[4] le paquet du compagnon transporte les boites")
from app.api import agent_campagnes_routes as R                     # noqa: E402

p = R._paquet(None)
check("4a boites.json servi", "boites.json" in p["fichiers"])
check("4b contenu = paquet_mobile", json.loads(p["fichiers"].get("boites.json", "null")) == B.paquet_mobile())

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
