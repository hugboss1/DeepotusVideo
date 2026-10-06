# -*- coding: utf-8 -*-
"""t111 (plan-sprites T12) — le panneau Squelette du Spritelab. Le module PUR (frontend/spritelab/skeleton.js) est jugé
par son banc node qa/skeleton.test.mjs, lancé ICI ; ce fichier vérifie le câblage : chaque élément lu par le panneau
existe, le module est exposé en window.SLK et le panneau rechargé à son arrivée (module différé), le panneau se charge
à chaque feuille affichée, l'écriture part sur la route du backend avec le corps du module, l'export n'est montré que
quand le manifeste dit que le rig existe, les noms se saisissent dans la liste — AUCUN prompt() (le plan en posait
deux), et aucun dialogue natif.
Témoin positif : la base (48ebf72c) n'a pas skeleton.js.
Run (depuis backend/) : & $PY tests/test_spritelab_squelette.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SL = RACINE / "frontend" / "spritelab"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", "48ebf72c:frontend/spritelab/skeleton.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base n'a pas skeleton.js", r0.returncode != 0)

r = subprocess.run(["node", str(SL / "qa" / "skeleton.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                   timeout=60)
check("Q1 le banc node du module pur passe", r.returncode == 0 and "PASS" in r.stdout, (r.stdout + r.stderr)[-600:])

HTML = (SL / "index.html").read_text(encoding="utf-8")
JS = (SL / "spritelab.js").read_text(encoding="utf-8")
CSS = (SL / "spritelab.css").read_text(encoding="utf-8")
DEB, FIN = "t111 (plan-sprites T12) : squelette Spine", "async function applyEditor()"
check("B0 le bloc du panneau est délimité", DEB in JS and FIN in JS and JS.index(DEB) < JS.index(FIN))
bloc = JS[JS.index(DEB):JS.index(FIN)] if DEB in JS and FIN in JS else ""
ids = sorted(set(re.findall(r'\$\("#([A-Za-z0-9]+)"\)', bloc)))
check(f"H1 les {len(ids)} éléments du panneau existent dans index.html", ids and all(f'id="{i}"' in HTML for i in ids),
      str([i for i in ids if f'id="{i}"' not in HTML]))
check("H2 le panneau est caché tant qu'aucune feuille n'est affichée", '<div id="squelette" class="editor hidden">' in HTML)
check("H3 skeleton.js exposé en window.SLK, et le panneau rechargé à son arrivée (module différé)",
      'import * as SLK from "./skeleton.js"; window.SLK = SLK; document.dispatchEvent(new Event("slk-pret"));' in HTML
      and 'document.addEventListener("slk-pret", () => { if (sheet) skCharger(sheet.short, sheet.manifest); });' in JS)
check("W1 chaque feuille affichée recharge le panneau sur SON manifeste",
      re.search(r"hbCharger\(short, m\);\n  skCharger\(short, m\);\n\}", JS.replace("\r\n", "\n")) is not None)
check("W2 l'écriture part sur la route du backend, avec le corps du module pur",
      "api.send(\"POST\", `/assets/sprite/${short}/skeleton`, window.SLK.corps(sk))" in bloc)
check("W3 l'export Spine n'est montré que si le manifeste dit que le rig existe",
      '$("#dlSpine").classList.toggle("hidden", !(m.files && m.files.spine));' in bloc
      and "`/api/assets/sprite/${short}/skeleton`" in bloc)
check("W4 les noms se saisissent dans la liste (renommerOs / renommerPiece), jamais par prompt()",
      "window.SLK.renommerOs(sk," in bloc and "window.SLK.renommerPiece(sk," in bloc
      and not re.search(r"\b(alert|confirm|prompt)\(", bloc))
check("W5 les gestes passent par le module (os et pièces au glisser)",
      "window.SLK.ajouterOs(sk," in bloc and "window.SLK.ajouterPiece(sk," in bloc)
check("W6 le panneau est branché au démarrage", "  skWire();" in JS)
check("W7 Écrire le rig coupé tant qu'il manque un os ou une pièce", '$("#skSave").disabled = !window.SLK.pret(sk)' in bloc)
check("C1 la liste du rig a son style", ".sklist{" in CSS)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
