# -*- coding: utf-8 -*-
"""t331 (A1 du lot Scenario, 29/10/2026) — l'ÉCRAN du pont « Scène Blender » (section « Blender ouvert » de la boîte
« Passes Blender » de la fiche d'un plan).
  [C] /shared/dz-blender-scene.js : copie dist octet pour octet (et dz-passes-plan.js aussi), balise dans l'Atelier AVANT
      dz-passes-plan.js, syntaxe (node --check), bancs de comportement node verts (blender_scene, passes_plan) ;
  [T] chaque clé blenderscene.* employée existe en FR et en EN avec les mêmes variables, aucune orpheline ; les messages
      du serveur blender.* employés par le pont existent tous, FR/EN mêmes variables ; dictionnaire assemblé à jour ;
  [H] honnêteté : « gratuit » posé à la construction ; la page n'envoie jamais de code (aucun « code » dans un corps).
Run (depuis backend/) : & $PY tests/test_blender_scene_ecran.py"""
import json
import os
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

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


js = (SH / "dz-blender-scene.js").read_text(encoding="utf-8")
code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
print("[C] fichiers")
for nom in ("dz-blender-scene.js", "dz-passes-plan.js"):
    check(f"C1 {nom} : copie dist identique", (DIST / nom).read_bytes() == (SH / nom).read_bytes())
tags = re.findall(r'<script src="([^"]+)"></script>', PAGE.read_text(encoding="utf-8"))
try:
    bon = tags.index("/shared/dz-i18n.js") < tags.index("/shared/dz-blender-scene.js") < tags.index("/shared/dz-passes-plan.js")
except ValueError:
    bon = False
check("C2 balise dans l'Atelier, après dz-i18n.js et AVANT dz-passes-plan.js (qui monte la section)", bon, tags)
check("C3 dz-passes-plan.js monte la section quand la boîte est chargée",
      "window.__dzBlenderScene.monter(E.corps" in (SH / "dz-passes-plan.js").read_text(encoding="utf-8"))
noeud = shutil.which("node")
if noeud:
    r = subprocess.run([noeud, "--check", str(SH / "dz-blender-scene.js")], capture_output=True, text=True)
    check("C4 syntaxe (node --check)", r.returncode == 0, r.stderr)
    for banc in ("blender_scene", "passes_plan"):
        r = subprocess.run([noeud, str(SH / "qa" / f"{banc}.test.mjs")], capture_output=True, text=True, encoding="utf-8")
        check(f"C5 banc de comportement {banc} vert", r.returncode == 0 and r.stdout.startswith("OK"), r.stdout + r.stderr)
else:
    print("  SKIP  C4-C5 : node introuvable")

print("[T] textes")
dico = json.loads((SH / "i18n" / "blenderscene.json").read_text("utf-8"))
employees = set(re.findall(r'"(blenderscene\.[a-z0-9_.]*[a-z0-9_])"', code))
dynamiques = ({f"blenderscene.element.{k}" for k in ("camera", "eclairage", "blocking", "cles")}
              | {f"blenderscene.element_aide.{k}" for k in ("camera", "eclairage", "blocking", "cles")}
              | {f"blenderscene.mode.{k}" for k in ("camera", "viewport", "angles")})
manque = sorted(k for k in employees | dynamiques if k not in dico)
check("T1 chaque clé employée existe (éléments, aides et modes bâtis par nom compris)", not manque, manque)
orph = sorted(k for k in dico if k not in employees | dynamiques)
check("T2 aucune clé orpheline", not orph, orph)
mauvais = [k for k, v in dico.items() if not v.get("fr") or not v.get("en")
           or set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
check("T3 FR et EN présents, mêmes variables", not mauvais, mauvais)
msgs = json.loads((RACINE / "backend" / "app" / "i18n" / "messages.json").read_text("utf-8"))
bm = {k: v for k, v in msgs.items() if k.startswith("blender.")}
src = "".join((RACINE / "backend" / "app" / p).read_text("utf-8")
              for p in ("api/blender_routes.py", "services/blender_mcp.py"))
emp = set(re.findall(r'"(blender\.[a-z_]+)"', src)) - {"blender.exe"}
check("T4 messages du serveur blender.* : employés = définis, FR/EN mêmes variables",
      emp == set(bm) and all(set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
                             for v in bm.values()), sorted(emp ^ set(bm)))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                   env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
check("T5 dictionnaire assemblé à jour (--check)", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])

print("[H] honnêteté")
check("H1 « gratuit » posé à la construction, avant tout clic",
      'T("blenderscene.section.gratuit")' in code and "gratuit" in dico["blenderscene.section.gratuit"]["fr"].lower()
      and "free" in dico["blenderscene.section.gratuit"]["en"].lower())
corps = re.findall(r"appel\([^;]*?,\s*(\{[^;]*?\})\)", code)
check("H2 la page n'envoie que des éléments, un mode ou un plan — jamais de code",
      corps and all("code" not in c for c in corps) and "elements: elements" in code, corps)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
