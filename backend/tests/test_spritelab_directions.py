# -*- coding: utf-8 -*-
"""t111 (plan-sprites T9-T11, écrans) — les onglets Bible et Prompt du Spritelab. Le module PUR
(frontend/spritelab/directions.js) est jugé par son banc node qa/directions.test.mjs, lancé ICI ; ce fichier vérifie le
câblage : chaque élément lu par les deux onglets existe, le module est exposé en window.SLD et attendu avant usage
(module différé), les routes de #237 sont appelées avec les corps du module, la source « images » ne part plus en
`job_id: undefined` (extraction ET génération passent par sourceBody), le viewport de capture n'est jamais en
display:none (un `<model-viewer>` caché ne rend rien), le tir payant affiche son devis, et aucun dialogue natif.
Témoin positif : la base (48ebf72c) n'a ni directions.js ni onglet Bible.
Run (depuis backend/) : & $PY tests/test_spritelab_directions.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SL = RACINE / "frontend" / "spritelab"
BASE = "48ebf72c"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


r0 = subprocess.run(["git", "show", f"{BASE}:frontend/spritelab/directions.js"], capture_output=True, cwd=str(RACINE))
h0 = subprocess.run(["git", "show", f"{BASE}:frontend/spritelab/index.html"], capture_output=True, cwd=str(RACINE)).stdout
j0 = subprocess.run(["git", "show", f"{BASE}:frontend/spritelab/spritelab.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 témoin : la base n'a ni directions.js, ni onglet Bible, et sa génération envoyait job_id seul",
      r0.returncode != 0 and h0 and b'data-src="bible"' not in h0
      and b"source: { kind: source.kind, job_id: source.job_id }" in j0)

r = subprocess.run(["node", str(SL / "qa" / "directions.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                   timeout=60)
check("Q1 le banc node du module pur passe", r.returncode == 0 and "PASS" in r.stdout, (r.stdout + r.stderr)[-600:])

HTML = (SL / "index.html").read_text(encoding="utf-8")
JS = (SL / "spritelab.js").read_text(encoding="utf-8")
CSS = (SL / "spritelab.css").read_text(encoding="utf-8")
DEB, FIN = "t111 (plan-sprites T9-T11) : onglets Bible et Prompt", "/* ───────── wiring ───────── */"
check("B0 le bloc des deux onglets est délimité", DEB in JS and FIN in JS and JS.index(DEB) < JS.index(FIN))
bloc = JS[JS.index(DEB):JS.index(FIN)] if DEB in JS and FIN in JS else ""

ids = sorted(set(re.findall(r'\$\("#([A-Za-z0-9]+)"\)', bloc)))
check(f"H1 les {len(ids)} éléments lus par les deux onglets existent dans index.html",
      ids and all(f'id="{i}"' in HTML for i in ids), str([i for i in ids if f'id="{i}"' not in HTML]))
check("H2 deux onglets, deux panneaux cachés au départ",
      'data-src="bible"' in HTML and 'data-src="prompt"' in HTML
      and '<div id="srcBible" class="src-body hidden">' in HTML and '<div id="srcPrompt" class="src-body hidden">' in HTML)
sw = JS[JS.index("function switchSrcTab(which)"):JS.index("/* ───────── packs de démarrage CC0")]
check("H3 switchSrcTab montre / cache les deux panneaux et charge leurs données",
      '$("#srcBible").classList.toggle("hidden", which !== "bible");' in sw
      and '$("#srcPrompt").classList.toggle("hidden", which !== "prompt");' in sw
      and 'if (which === "bible") loadEntities();' in sw and 'if (which === "prompt") loadPersona();' in sw)
check("H4 directions.js exposé en window.SLD, et attendu avant usage (module différé, arrive APRÈS ce script)",
      'import * as SLD from "./directions.js"; window.SLD = SLD; document.dispatchEvent(new Event("sld-pret"));' in HTML
      and 'document.addEventListener("sld-pret"' in JS and "await SLD_PRET;" in JS)
check("H7 la barre des 7 onglets passe à la ligne (429 px dans 339 : la colonne débordait et défilait — mesuré)",
      "#srcTabs{flex-wrap:wrap}" in CSS)
check("H5 model-viewer chargé (module vendorisé du bundle) et un viewport de capture",
      '<script type="module" src="/assets/model-viewer.min.js"></script>' in HTML and '<model-viewer id="mv3d"' in HTML)
mv = re.search(r"\.mv-hold\{([^}]*)\}", CSS)
check("H6 le viewport n'est JAMAIS display:none (model-viewer caché ne rend rien : toBlob rendrait du vide)",
      mv and "display:none" not in mv.group(1).replace(" ", "") and "width:" in mv.group(1)
      and 'class="mv-hold' in HTML and 'class="mv-hold hidden' not in HTML)

# la source : extraction ET génération passent par le module
check("S1 plus aucun corps de source écrit à la main (la source images partait en job_id: undefined)",
      "source: { kind: source.kind, job_id: source.job_id }" not in JS and JS.count("window.SLD.sourceBody(source)") == 2)
ex = JS[JS.index("async function extract()"):JS.index("function renderStrip()")]
check("S2 l'extraction attend le module avant de lire la source", "await SLD_PRET;" in ex and "window.SLD.sourceBody(source)" in ex)

# Bible : les routes de #237, avec les réglages de la colonne du milieu
check("W1 la découpe appelle /assets/sprite/from-board avec l'entité, la cellule, le pixel et le post",
      '"/assets/sprite/from-board"' in bloc and "entity_id: e.id" in bloc and "cell: cellOpts()" in bloc
      and "pixelOpts()" in bloc and "postOpts()" in bloc)
check("W2 la capture pose l'orbite du module, capture par toBlob, dépose sur /assets/sprite/capture",
      'mv.setAttribute("camera-orbit", window.SLD.orbite(theta))' in bloc and "mv.toBlob(" in bloc
      and "/api/assets/sprite/capture?dir=${nom}&prefix=${prefix}" in bloc)
check("W3 la MESURE de l'alpha (réponse de la route) décide du détourage, via le corps du module",
      "if (!d.alpha) sansAlpha.push(nom);" in bloc and "window.SLD.corpsOrbites(noms, sansAlpha," in bloc)
check("W4 le GLB est celui de l'entité, servi par /api/assets/3d/{job}/glb",
      "/api/assets/3d/${encodeURIComponent(e.model3d_job)}/glb" in bloc)
check("W5 la liste ne propose que les entités découpables (personnage + planche)",
      "window.SLD.entitesDecoupables(entities," in bloc)
check("W6 un geste à la fois : les deux boutons Bible se coupent pendant le travail",
      "busyBible = true; majBible();" in bloc and "busyBible = false; majBible();" in bloc)

# Prompt : payant — devis d'abord, source « sprites », puis la feuille par la source images
check("P1 le tir payant part sur /images/generate avec le corps du module (source « sprites »)",
      '"/images/generate", window.SLD.corpsPrompt(' in bloc)
check("P2 le devis est affiché avant le tir (/cost/estimate, kind image, le modèle par défaut des Réglages)",
      '"/cost/estimate"' in bloc and 'kind: "image"' in bloc and "image_model_default" in bloc)
check("P3 les images rendues deviennent la source (images) : filmstrip puis feuille, rien de plus payé",
      'setSource({ kind: "images", filenames: noms,' in bloc)
check("P4 un tir à la fois", "if (busyPrompt) return;" in bloc and '$("#pmGen").disabled = true;' in bloc)
check("P5 aucun dialogue natif dans les deux onglets", not re.search(r"\b(alert|confirm|prompt)\(", bloc))
check("P6 câblé au démarrage", "bibleWire();" in JS[JS.index("function wire()"):])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
