# -*- coding: utf-8 -*-
"""t305 (lot A0, boîtes à outils de l'agent) — capteur de la fixture des définitions de Campagnes.
Écrit `agent_definitions_campagnes.json` à côté de lui : `agent_outils.definitions()` tel qu'il est
au commit e0d6e51e (dix outils). Le banc `test_agent_boites.py` relit ce fichier pour garder Campagnes
à l'octet près pendant les tâches suivantes. Données isolées, rien de payé, aucune clé.
Run (depuis backend/) : & $PY tests/_agent_definitions_capture.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcapt_"))
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
from app.services import agent_outils as ao                         # noqa: E402

SORTIE = _ICI / "agent_definitions_campagnes.json"
texte = json.dumps(ao.definitions(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"
with open(SORTIE, "w", encoding="utf-8", newline="\n") as f:
    f.write(texte)
print(f"ecrit {SORTIE} : {len(ao.definitions())} outils")
