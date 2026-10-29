# -*- coding: utf-8 -*-
"""t314 (28/10/2026) (C2 Scan, tâche 4) — banc de l'outil `calques_illustration` de la boîte d'agent `scan` (carte du
devis du détourage d'un schéma ; rien n'est appelé). Aucun réseau.
Run (depuis backend/) : & $PY tests/test_agent_schema.py"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagschema_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["FAL_KEY"] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from PIL import Image                                               # noqa: E402
from app import config                                              # noqa: E402
from app.services import agent_outils as ao, agent_boites as B, pricing, detourage as DT   # noqa: E402
from app.services import matte_service as MT                        # noqa: E402

APPELS = []
async def _espion(*a, **k):
    APPELS.append(a)
    raise RuntimeError("aucun appel attendu")
MT._upload = MT._fal_subscribe = MT._download = _espion
Image.new("RGB", (120, 80), (255, 255, 255)).save(config.settings.images_path / "schema.png")


def lancer(args, agent="demo"):
    return asyncio.run(ao.executer("calques_illustration", args, ao.Ctx(cid="c1", agent=agent, espace_id=None)))


print("[1] registre")
check("4d verifier() sain", B.verifier() == [], B.verifier())
check("4d nature carte, boîte scan déclarée par le seul agent mcp (t345), qui ne voit pas cette carte",
      ao.OUTILS["calques_illustration"]["nature"] == "carte" and B.boite_de("calques_illustration") == "scan"
      and B.BOITES["scan"]["agents"] == ["mcp"] and "calques_illustration" not in B.outils_pour("mcp"))
fige = json.loads((_ICI / "agent_definitions_campagnes.json").read_text(encoding="utf-8"))
check("4e Campagnes inchangé (fixture figée)", B.definitions_pour("campagnes") == fige)
check("4e refusé hors boîte", lancer({"image": "schema.png"}, agent="campagnes")["ok"] is False)

B.BOITES["scan"]["agents"].append("demo")
try:
    print("[2] la carte")
    r = lancer({"image": "schema.png"})
    c = r["carte"] or {}
    check("4a carte locale à 0 $", r["ok"] and c.get("genre") == "devis" and c.get("action") == "calques_illustration"
          and c["arguments"] == {"genre": "calques_illustration", "image": "schema.png", "detourage": "local-chroma",
                                 "usd": 0.0}, r)
    r = lancer({"image": "schema.png", "detourage": "bria-rmbg"})
    attendu = round(float(pricing.estimate(DT.op_cout("bria-rmbg", images=1))["total_usd"]), 4)
    check("4b modèle fal : devis du registre", r["ok"] and r["carte"]["devis"] == attendu and attendu > 0, (r, attendu))
    for nom in ("../x.png", "a/b.png", "C:schema.png", "absente.png", "schema.txt"):
        check(f"4c refus : {nom}", lancer({"image": nom})["ok"] is False)
    check("4c détourage inconnu ou à sujet refusé", lancer({"image": "schema.png", "detourage": "sam3-sujet"})["ok"] is False
          and lancer({"image": "schema.png", "detourage": "zz"})["ok"] is False)
    check("rien n'est appelé", APPELS == [], APPELS)
finally:
    B.BOITES["scan"]["agents"].remove("demo")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
