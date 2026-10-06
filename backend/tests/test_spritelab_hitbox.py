# -*- coding: utf-8 -*-
"""T112 — le panneau Hitboxes du Spritelab. Le module PUR (frontend/spritelab/hitbox.js) est jugé par son banc node
qa/hitbox.test.mjs, lancé ICI (aucun banc Python ne lançait le harnais qa/ du Spritelab) ; ce fichier vérifie le
câblage : chaque élément lu par le panneau existe, le module est exposé en window.SLH et rechargé à son arrivée
(module différé), le panneau se charge à chaque feuille affichée, l'enregistrement part sur la route du backend, les
raccourcis ne touchent ni les champs ni le Playground, et aucun dialogue natif.
Témoin positif : la base (fdababf3) n'a pas hitbox.js.
Run (depuis backend/) : & $PY tests/test_spritelab_hitbox.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SL = RACINE / "frontend" / "spritelab"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "fdababf3:frontend/spritelab/hitbox.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas hitbox.js", r0.returncode != 0)

r = subprocess.run(["node", str(SL / "qa" / "hitbox.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                   timeout=60)
check("Q1 le banc node du module pur passe", r.returncode == 0 and "PASS" in r.stdout, (r.stdout + r.stderr)[-600:])

HTML = (SL / "index.html").read_text(encoding="utf-8")
JS = (SL / "spritelab.js").read_text(encoding="utf-8")
bloc = JS[JS.index("T112 (spec sorceress"):JS.index("async function applyEditor()")]
ids = sorted(set(re.findall(r'\$\("#(hb[A-Za-z]+|hitboxes)"\)', bloc)) | {i for i, _ in re.findall(r'\["(hb[A-Za-z]+)", "(\w)"\]', bloc)})
check(f"H1 les {len(ids)} éléments du panneau existent dans index.html", ids and all(f'id="{i}"' in HTML for i in ids),
      str([i for i in ids if f'id="{i}"' not in HTML]))
check("H2 le panneau est caché tant qu'aucune feuille n'est affichée", '<div id="hitboxes" class="editor hidden">' in HTML)
check("H3 hitbox.js exposé en window.SLH, et le panneau rechargé à son arrivée (module différé)",
      'import * as SLH from "./hitbox.js"; window.SLH = SLH; document.dispatchEvent(new Event("slh-pret"));' in HTML
      and 'document.addEventListener("slh-pret", () => { if (sheet) hbCharger(sheet.short, sheet.manifest); });' in JS)
check("W1 chaque feuille affichée recharge les hitboxes de SON manifeste (après un réassemblage aussi)",
      re.search(r"renderEditor\(\);\n  hbCharger\(short, m\);\n\}", JS) is not None)
check("W2 l'enregistrement part sur la route du backend, avec le corps du module pur",
      "api.send(\"POST\", `/assets/sprite/${short}/hitboxes`, window.SLH.corps(hb))" in bloc)
check("W3 raccourcis : jamais dans un champ, seulement après un geste sur le panneau",
      "if (!hb || !hbActif" in bloc and "/^(INPUT|TEXTAREA|SELECT)$/" in bloc and "(ev.ctrlKey || ev.metaKey) && k === \"c\"" in bloc)
check("W4 le Playground n'écoute ni C, ni V, ni Suppr (pas de conflit)",
      not re.search(r'k === "(c|v|delete|backspace)"', JS[JS.index("function playgroundWire()"):JS.index("async function saveToLibrary()")]))
check("W5 aucun dialogue natif dans le panneau", not re.search(r"\b(alert|confirm|prompt)\(", bloc))
check("W6 hbWire est branché au démarrage", "  hbWire();" in JS)
CSS = (SL / "spritelab.css").read_text(encoding="utf-8")
check("C1 le volet Préviz défile (sinon le panneau, sous la préviz et l'éditeur, est inatteignable — vu à l'écran)",
      ".out-pane{overflow-y:auto}" in CSS and CSS.index(".out-pane{overflow-y:auto}") > CSS.index(".pane{"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
