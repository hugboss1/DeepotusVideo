# -*- coding: utf-8 -*-
"""t334 (A4 du lot Scenario, 29/10/2026) — l'ÉCRAN des passes Blender du plan.
  [C] /shared/dz-passes-plan.js : copie dist octet pour octet, balise dans l'Atelier (après la revue et le
      comparateur, avant atelier.js), syntaxe (node --check), banc de comportement node vert
      (frontend/shared/qa/passes_plan.test.mjs) ;
  [B] l'Atelier : renderBoard() appelle __dzPassesPlan.vignettes(list, chapter.id) en FIN de rendu des cartes ;
      saisie L8 t334 à jour (--check) ; dictionnaire assemblé à jour ;
  [T] chaque clé passesplan.* employée existe en FR et en EN avec les mêmes variables, aucune orpheline ; les messages
      du serveur passes.* aussi ; les nouvelles clés de la revue (profondeur mesurée) aussi ;
  [H] honnêteté : « gratuit » affiché avant le clic, la profondeur de la revue dite « pas estimée » côté rendu.
Run (depuis backend/) : & $PY tests/test_passes_plan_ecran.py"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
SH = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
PAGE = RACINE / "frontend" / "atelier" / "index.html"
AT = RACINE / "frontend" / "atelier" / "atelier.js"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


js = (SH / "dz-passes-plan.js").read_text(encoding="utf-8")
page = PAGE.read_text(encoding="utf-8")
at = AT.read_text(encoding="utf-8")
PY = sys.executable

print("[C] fichiers")
check("C1 dz-passes-plan.js : copie dist identique", (DIST / "dz-passes-plan.js").read_bytes()
      == (SH / "dz-passes-plan.js").read_bytes())
tags = re.findall(r'<script src="([^"]+)"></script>', page)
try:
    i = {t: tags.index(t) for t in ("/shared/dz-comparateur.js", "/shared/dz-revue-plan.js", "/shared/dz-passes-plan.js",
                                    "/shared/dz-i18n.js", "atelier.js")}
    bon = i["/shared/dz-i18n.js"] < i["/shared/dz-comparateur.js"] < i["/shared/dz-passes-plan.js"] < i["atelier.js"] \
        and i["/shared/dz-revue-plan.js"] < i["/shared/dz-passes-plan.js"]
except ValueError:
    bon = False
check("C2 balise de la boîte dans l'Atelier, après la revue et le comparateur, avant atelier.js", bon, tags)
noeud = shutil.which("node")
if noeud:
    r = subprocess.run([noeud, "--check", str(SH / "dz-passes-plan.js")], capture_output=True, text=True)
    check("C3 syntaxe (node --check)", r.returncode == 0, r.stderr)
    r = subprocess.run([noeud, str(SH / "qa" / "passes_plan.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8")
    check("C4 banc de comportement node vert", r.returncode == 0 and r.stdout.startswith("OK"), r.stdout + r.stderr)
else:
    print("  SKIP  C3-C4 : node introuvable")

print("[B] l'Atelier")
m = re.search(r"function renderBoard\(\) \{(.*?)\r?\n\}\r?\n", at, re.S)
corps = m.group(1) if m else ""
check("B1 renderBoard appelle __dzPassesPlan.vignettes(list, chapter.id) APRÈS les écouteurs des cartes",
      "window.__dzPassesPlan.vignettes(list, chapter.id)" in corps
      and corps.rfind("window.__dzPassesPlan.vignettes") > corps.rfind('querySelectorAll(".shot-card")'), corps[-400:])
for script, quoi in (("i18n_l8_generer.py", "saisie L8"), ("i18n_assembler.py", "dictionnaire assemblé")):
    r = subprocess.run([PY, str(RACINE / "scripts" / script), "--check"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(RACINE),
                       env={**__import__("os").environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    check(f"B2 {quoi} à jour (--check)", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])

print("[T] textes")
dico = json.loads((SH / "i18n" / "passesplan.json").read_text("utf-8"))
code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
# toute chaîne "passesplan.…" du code (T(cle), T(cond ? "a" : "b")) ; les préfixes "passesplan.passe." + p sont bâtis
employees = set(re.findall(r'"(passesplan\.[a-z0-9_.]*[a-z0-9_])"', code))
dynamiques = {f"passesplan.passe.{p}" for p in ("clay", "look", "profondeur", "normales", "masques")} \
    | {f"passesplan.aide.{p}" for p in ("clay", "look", "profondeur", "normales", "masques")}
manque = sorted(k for k in employees | dynamiques if k not in dico)
check("T1 chaque clé employée existe (y compris passe.* et aide.* bâties par nom)", not manque, manque)
orph = sorted(k for k in dico if k not in employees | dynamiques)
check("T2 aucune clé orpheline", not orph, orph)
mauvais = [k for k, v in dico.items() if not v.get("fr") or not v.get("en")
           or set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
check("T3 FR et EN présents, mêmes variables", not mauvais, mauvais)
msgs = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
pm = {k: v for k, v in msgs.items() if k.startswith("passes.")}
routes = (RACINE / "backend" / "app" / "api" / "passes_routes.py").read_text("utf-8")
emp = set(re.findall(r'i18n\.msg\("(passes\.[a-z_]+)"', routes))
check("T4 messages du serveur passes.* : employés = définis, FR/EN mêmes variables",
      emp == set(pm) and all(set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
                             for v in pm.values()), (sorted(emp ^ set(pm))))
rv = json.loads((SH / "i18n" / "revueplan.json").read_text("utf-8"))
rvjs = (SH / "dz-revue-plan.js").read_text("utf-8")
nouvelles = ("revueplan.mesures.profondeur_proche", "revueplan.mesures.profondeur_ecart",
             "revueplan.mesures.profondeur_aide")
check("T5 la revue du plan : les clés de la profondeur mesurée existent et sont employées",
      all(k in rv and f'"{k}"' in rvjs for k in nouvelles) and (DIST / "dz-revue-plan.js").read_bytes()
      == (SH / "dz-revue-plan.js").read_bytes())

print("[H] honnêteté")
check("H1 « gratuit » affiché avant tout clic (texte du prix posé à la construction)",
      'T("passesplan.rendre.gratuit")' in code and "gratuit" in dico["passesplan.rendre.gratuit"]["fr"].lower()
      and "free" in dico["passesplan.rendre.gratuit"]["en"].lower())
check("H2 la revue dit que la profondeur du rendu n'est pas estimée",
      "pas estimée" in rv["revueplan.mesures.profondeur_aide"]["fr"]
      and "not estimated" in rv["revueplan.mesures.profondeur_aide"]["en"])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
