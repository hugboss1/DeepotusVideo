# -*- coding: utf-8 -*-
"""Banc du CATALOGUE des serveurs MCP utiles (Réglages › Serveur MCP, services/mcp_catalogue.py, 22/11/2026).

  [C] le catalogue : chaque entrée a un rôle FR et EN, ses écrans, une commande `claude mcp add` (sauf « deepotus »,
      dont la commande vient de mcp_pont), aucune clé en clair (seulement le repère <VOTRE_CLE>) ; l'état « branché »
      se lit dans les NOMS de ~/.claude.json (un faux dossier personnel) sans rien rendre d'autre de ce fichier ;
  [R] la route GET /api/mcp/catalogue : locale seulement, langue de la requête ;
  [E] l'écran : dz-mcp.js monte le bloc « MCP utiles à connecter » (copie identique dans dist/shared), clés i18n
      présentes dans mcp.json et dans le dictionnaire assemblé.
Aucun appel réseau. Run (depuis backend/) : & $PY tests/test_mcp_catalogue.py"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmcpcat_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir()
(_tmp / "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from loguru import logger  # noqa: E402
logger.remove()

from app.services import mcp_catalogue as MC  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {str(detail)[:400]}")


print("[C] catalogue")
ids = [e["id"] for e in MC.CATALOGUE]
check("C1 identifiants uniques, « deepotus » et « blender » présents", len(ids) == len(set(ids))
      and {"deepotus", "blender"} <= set(ids), ids)
check("C2 rôle FR et EN, écrans, type stdio|http pour chaque entrée",
      all(e["role"]["fr"] and e["role"]["en"] and e["ecrans"] and e["type"] in ("stdio", "http") for e in MC.CATALOGUE))
cmds = [e["commande"] for e in MC.CATALOGUE if e["id"] != "deepotus"]
check("C3 une commande « claude mcp add --scope user <id> » par serveur externe",
      all(c and c.startswith("claude mcp add --scope user") for c in cmds)
      and all(f" {e['id']} " in e["commande"] for e in MC.CATALOGUE if e["id"] != "deepotus"), cmds)
check("C4 aucune clé en clair : seulement le repère <VOTRE_CLE>",
      all("=" not in c.split("-e ")[-1].split(" ")[0] or "<VOTRE_CLE>" in c or "true" in c or "=1" in c for c in cmds)
      and "sk_" not in json.dumps(MC.CATALOGUE) and "tsk_" not in json.dumps(MC.CATALOGUE))
check("C5 le pont Blender reste en mode sûr dans la commande", "BLENDER_MCP_SAFE_MODE=1" in
      next(e["commande"] for e in MC.CATALOGUE if e["id"] == "blender"))

maison = _tmp / "maison"
maison.mkdir()
(maison / ".claude.json").write_text(json.dumps({"mcpServers": {"figma": {"type": "http", "url": "https://secret"},
                                                                 "notion": {"command": "x", "env": {"K": "secret"}}},
                                                 "autre": "secret"}), encoding="utf-8")
_home = pathlib.Path.home
pathlib.Path.home = classmethod(lambda cls: maison)
try:
    L = MC.liste("fr")
finally:
    pathlib.Path.home = _home
par_id = {s["id"]: s for s in L["serveurs"]}
check("C6 « branché » lu dans les noms de ~/.claude.json", par_id["figma"]["etat"] == "branche"
      and par_id["notion"]["branche"] and par_id["canva"]["etat"] == "a_brancher", {k: v["etat"] for k, v in par_id.items()})
check("C7 rien d'autre de ~/.claude.json ne ressort (URL, env, clés)", "secret" not in json.dumps(L))
check("C8 « deepotus » : la commande du pont de l'app, et son état actif/inactif",
      par_id["deepotus"]["commande"].startswith("claude mcp add --scope user deepotus")
      and par_id["deepotus"]["etat"] in ("actif", "inactif"))
check("C9 « blender » : état trouvé / uvx / absent", par_id["blender"]["etat"] in ("trouve", "uvx", "absent"))
check("C10 langue anglaise", MC.liste("en")["serveurs"][1]["role"].startswith("Drives"))

print("[R] route")
from fastapi.testclient import TestClient  # noqa: E402

import app.main as _MAIN  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
_b = asyncio.new_event_loop()
asyncio.set_event_loop(_b)
_b.run_until_complete(init_db())
with TestClient(_MAIN.app, client=("127.0.0.1", 50001)) as cl:
    r = cl.get("/api/mcp/catalogue", headers={"Accept-Language": "en"})
    check("R1 GET /api/mcp/catalogue : 200, serveurs listés", r.status_code == 200
          and len(r.json()["serveurs"]) == len(MC.CATALOGUE), r.text[:300])
with TestClient(_MAIN.app, client=("192.168.1.20", 50000)) as lan:
    check("R2 un appareil du réseau local est refusé", lan.get("/api/mcp/catalogue").status_code in (401, 403))

print("[E] écran")
js = (RACINE / "frontend" / "shared" / "dz-mcp.js").read_bytes()
check("E1 copie identique dans dist/shared (au retour à la ligne près)",
      js.replace(b"\r\n", b"\n") == (RACINE / "frontend" / "dist" / "shared" / "dz-mcp.js").read_bytes().replace(b"\r\n", b"\n"))
t = js.decode("utf-8")
check("E2 le bloc « utiles » appelle /catalogue, sans innerHTML", 'cadre("utiles"' in t and '"/catalogue"' in t
      and "innerHTML" not in t.split("Deux surfaces")[1].split("*/")[1])
cles = json.loads((RACINE / "frontend" / "shared" / "i18n" / "mcp.json").read_text(encoding="utf-8"))
utilisees = {"mcp.utiles.titre", "mcp.utiles.aide", "mcp.utiles.ecrans", "mcp.utiles.licence", "mcp.utiles.doc",
             "mcp.utiles.erreur"} | {"mcp.utiles.etat_" + e for e in ("actif", "inactif", "trouve", "uvx", "absent",
                                                                     "branche", "a_brancher")}
dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("E3 clés i18n FR/EN présentes et assemblées", all(k in cles and cles[k]["fr"] and cles[k]["en"] and f'"{k}"' in dico
                                                       for k in utilisees), sorted(utilisees - set(cles)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
