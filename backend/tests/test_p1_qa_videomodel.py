# -*- coding: utf-8 -*-
"""P1 #13 (28/09/2026) — LA RECETTE scripts/qa/qa-videomodel.js RESTEE SUR seedance-v1-pro.

Mesure du 28/09 : la recette (Puppeteer, mode SMOKE) jouee contre le backend de
preuve 8799 avec le bundle de main donnait 2/8 -- W1 attendait le libelle
« v1.21.0 » (l'app dit v2.8.0), W2 cherchait le select « Open graph » (devenu
une icone en R8og1), W3 attendait « Defaut (seedance-v1-pro) » et 11 options
(Defaut + 10 modeles figes dans une table REG recopiee a la main, sans
seedance-2.5), W4 un cout fige a $1.12 calcule sur des durees INVENTEES
(4/6/8) ; E1 attendait 10 modeles et le defaut v1-pro.
Decision : la recette ne recopie plus rien. En SMOKE, le catalogue simule est
le VRAI GET /api/video-models du backend vise (tout rendu disponible) ; W1 lit
APP_VERSION (backend/app/config.py) ; W3 attend « Defaut (<defaut reel>) » et
N+1 options ; W4 attend le montant que le SERVEUR calcule (POST /cost/estimate,
op `video` de #9) ; W5 exige aussi `max_usd` (garde de #9) ; E1 lit
DEFAULT_VIDEO_MODEL et le nombre de modeles dans fal_service.py.
Ce banc est STATIQUE (la recette elle-meme est jouee pour la preuve) : plus
aucun litteral fige, et les deux lectures par regex de la recette rendent ce
que Python importe. Temoin : la recette de la base (git show).
Run : & $PY tests/test_p1_qa_videomodel.py   (depuis backend/)
"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
from app.config import APP_VERSION                        # noqa: E402
from app.services.fal_service import DEFAULT_VIDEO_MODEL, VIDEO_MODELS  # noqa: E402

BASE = "f195c72"
RECETTE = ROOT / "scripts" / "qa" / "qa-videomodel.js"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:500]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


neuf = RECETTE.read_text(encoding="utf-8")
vieux = subprocess.run(["git", "show", f"{BASE}:scripts/qa/qa-videomodel.js"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")

print("\n[0] temoin : la recette de la base (%s)" % BASE)
check("0.1 TEMOIN : la base attend le defaut seedance-v1-pro (l.53, 231, 325), v1.21.0 et une table REG figee",
      vieux.count("default: 'seedance-v1-pro'") == 1 and "Défaut \\(seedance-v1-pro\\)" in vieux
      and "vm.default === 'seedance-v1-pro'" in vieux and "v1.21.0" in vieux and "const REG = [" in vieux, "")

print("\n[1] plus aucun litteral fige")
for lit in ("seedance-v1-pro", "v1.21.0", "const REG = [", "w3opts.count === 11", "w4.val === '$1.12'", "ids.length === 10",
            "durations: [4, 6, 8]", "open graph|no saved graphs"):
    check(f"1.x absent de la recette : {lit}", lit not in neuf, _d(neuf.count(lit)))

print("\n[2] ce que la recette lit a la place")
for jet in ("process.env.DZ_BASE", "APP_VERSION", "DEFAULT_VIDEO_MODEL", "'/api/video-models'", "'/api/cost/estimate'",
            "kind: 'video'", "typeof w5.max === 'number' && w5.max > 0",   # la CONDITION, pas le mot (mutant Q3)
            'aria-label="Ouvrir un graphe"', ".dz-opengraph-item"):
    check(f"2.x present dans la recette : {jet}", jet in neuf, "")

print("\n[3] les lectures par regex de la recette rendent ce que Python importe")
m_v = re.search(r"/\^APP_VERSION = \"\(\[\^\"\]\+\)\"/m", neuf)
m_d = re.search(r"/\^DEFAULT_VIDEO_MODEL = \"\(\[\^\"\]\+\)\"/m", neuf)
check("3.0 la recette porte les deux regex attendues", bool(m_v) and bool(m_d), "")
cfg = (BACKEND / "app" / "config.py").read_text(encoding="utf-8")
fal = (BACKEND / "app" / "services" / "fal_service.py").read_text(encoding="utf-8")
v = re.search(r'^APP_VERSION = "([^"]+)"', cfg, re.M)
d = re.search(r'^DEFAULT_VIDEO_MODEL = "([^"]+)"', fal, re.M)
check("3.1 APP_VERSION lu par la regex == importe", bool(v) and v.group(1) == APP_VERSION, _d(v and v.group(1), APP_VERSION))
check("3.2 DEFAULT_VIDEO_MODEL lu par la regex == importe", bool(d) and d.group(1) == DEFAULT_VIDEO_MODEL,
      _d(d and d.group(1), DEFAULT_VIDEO_MODEL))
# le compte des modeles : la recette compte les cles d'indentation 4 dans le bloc VIDEO_MODELS
i = fal.find("VIDEO_MODELS: dict = {")
j = fal.find("\n}\n", i)
ids = re.findall(r'^    "([^"]+)": \{', fal[i:j], re.M) if i >= 0 and j > i else []
check("3.3 le bloc VIDEO_MODELS lu comme la recette == les ids importes, dans l'ordre", ids == list(VIDEO_MODELS), _d(ids, list(VIDEO_MODELS)))
check("3.4 la recette compte les modeles de la meme facon (motif et bornes)",
      "VIDEO_MODELS: dict = {" in neuf and '\\n}\\n' in neuf and '/^    "([^"]+)": \\{/gm' in neuf, "")
_nc = subprocess.run(["node", "--check", str(RECETTE)], capture_output=True, text=True)
check("3.5 node --check de la recette", _nc.returncode == 0, _d(_nc.stderr[-300:]))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
