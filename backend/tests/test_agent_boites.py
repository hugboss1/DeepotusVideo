# -*- coding: utf-8 -*-
"""t305 (lot A0, boîtes à outils de l'agent) — banc des boîtes à outils de l'agent.
Ce que ce banc garde, par sections numérotées :
  1. Compatibilité : l'agent Campagnes voit exactement les dix outils figés à e0d6e51e
     (fixture agent_definitions_campagnes.json, écrite par _agent_definitions_capture.py).
Les sections 2 à 4 arrivent avec les tâches 2 à 3 du lot A0.
Données isolées (DEEPOTUS_DATA_DIR temporaire), clés vidées, rien de payé.
Run (depuis backend/) : & $PY tests/test_agent_boites.py"""
import json, os, pathlib, sys, tempfile
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

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
