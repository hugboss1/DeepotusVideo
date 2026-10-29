# -*- coding: utf-8 -*-
"""Mutations t373 (29/10/2026) : les curseurs façon table de mixage (frontend/shared/dz-curseur.css, maillon
patch_bundle_dzcurseur, styles locaux retirés). Chaque mutation de la feuille, de ses branchements, d'un style local
ou du maillon doit faire ÉCHOUER backend/tests/test_curseur_ecran.py. Les sources sont copiées AVANT, restaurées après
chaque mutation et comparées octet à octet à la fin. AUCUNE ne touche le bundle (le maillon est muté dans son script :
son --check le voit alors « partiellement appliqué »).
Run (depuis la racine) : & $PY scripts/mutations_curseur.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_curseur_"))
COPIE = RACINE / "frontend/dist/shared/dz-curseur.css"
F = {"css": RACINE / "frontend/shared/dz-curseur.css", "dist": COPIE,
     "coque": RACINE / "frontend/dist/index.html", "jetons": RACINE / "frontend/shared/deepotus.tokens.css",
     "photolab": RACINE / "frontend/photolab/photolab.css", "vector": RACINE / "frontend/vectorlab/vectorlab.css",
     "mforge": RACINE / "frontend/materialforge/materialforge.css", "lecteur": RACINE / "frontend/shared/dz-lecteur.js",
     "aide": RACINE / "backend/tests/_i18n_l1_aide.py", "maillon": RACINE / "scripts/patch_bundle_dzcurseur.py"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
BANC = [sys.executable, "backend/tests/test_curseur_ecran.py"]
M = [
 # la feuille commune
 ("css", "--dz-curseur-piste:3px;", "--dz-curseur-piste:5px;"),
 ("css", "background:transparent;overflow:hidden;cursor:pointer;", "background:transparent;cursor:pointer;"),
 ("css", "var(--amber)) 60%,transparent);", "var(--amber)) 100%,transparent);"),
 ("css", "  border-image:linear-gradient(90deg,var(--dz-curseur-rempli) 50%,transparent 0)", "  border-image:none;--x:linear-gradient(90deg,var(--dz-curseur-rempli) 50%,transparent 0)"),
 ("css", "outline:1px solid var(--amber);outline-offset:2px;", "outline:none;"),
 ("css", ":where(input[type=range]:disabled){opacity:.45;cursor:default}", ""),
 ("css", "  border:0;border-radius:var(--radius);\n  background:repeating-linear-gradient(var(--dz-curseur-stries,to bottom),var(--dz-curseur-strie) 0 1px,var(--dz-curseur-bouton) 1px 3px);\n  box-shadow:inset 0 0 0 1px var(--dz-curseur-filet);\n  border-image",
         "  border:0;border-radius:50%;\n  background:repeating-linear-gradient(var(--dz-curseur-stries,to bottom),var(--dz-curseur-strie) 0 1px,var(--dz-curseur-bouton) 1px 3px);\n  box-shadow:inset 0 0 0 1px var(--dz-curseur-filet);\n  border-image"),
 ("css", "--dz-curseur-rainure:var(--bg-base);", "--dz-curseur-rainure:#0a0a0c;"),
 ("css", "::-moz-range-progress{", "::-moz-range-x{"),
 ("css", "--dz-curseur-longueur:96px;--dz-curseur-stries:to right;", "--dz-curseur-longueur:96px;"),
 ("css", ":where(input[type=range].dz-gradue){", "input[type=range].dz-gradue{"),
 ("css", "div.dzsvp-stems{flex-direction:row;", "div.dzsvp-stems{flex-direction:column;"),
 ("css", "grid-area:v;--dz-curseur-longueur:112px;--dz-curseur-stries:to right;", "grid-area:v;--dz-curseur-longueur:112px;"),
 ("css", ".svm-mixfill,.svm-thmixfill{border-radius:var(--radius);", ".svm-mixfill,.svm-thmixfill{border-radius:999px;"),
 ("css", "  height:var(--dz-curseur-piste,3px);border-radius:var(--radius);\n  background:var(--bg-base);",
         "  height:5px;border-radius:var(--radius);\n  background:var(--bg-base);"),
 ("dist", "--dz-curseur-bouton-l:8px;", "--dz-curseur-bouton-l:9px;"),
 # branchements
 ("coque", '    <link rel="stylesheet" href="/shared/dz-curseur.css">\n', ""),
 ("jetons", '@import url("/shared/dz-curseur.css");', '/* @import url("/shared/dz-curseur.css"); */'),
 # un seul style
 ("photolab", "input[type=range] { width: 100%; }", "input[type=range] { width: 100%; }\ninput[type=range]::-webkit-slider-thumb { width: 12px; }"),
 ("lecteur", '".dz-lecteur input[type=range]{flex:1 1 auto;min-width:40px}",', '".dz-lecteur input[type=range]{flex:1 1 auto;min-width:40px}.dz-lecteur input[type=range]::-webkit-slider-thumb{width:8px}",'),
 ("vector", "--dz-curseur-piste: 12px; --dz-curseur-rainure: transparent; --dz-curseur-rempli: transparent; }", "--dz-curseur-piste: 12px; --dz-curseur-rempli: transparent; }"),
 ("vector", "margin: -6px 0 0 -4px; border-radius: var(--radius); background: repeating", "margin: -6px 0 0 -4px; border-radius: 50%; background: repeating"),
 ("vector", "vl-curseur:focus-visible { outline: 1px solid var(--amber); outline-offset: 2px; }", ""),
 ("mforge", "calc(4px + (100% - 8px) * var(--dp, 0))", "calc(6px + (100% - 12px) * var(--dp, 0))"),
 ("mforge", ".prop.mod .rng input[type=range] { --dz-curseur-strie: var(--mod); }", ""),
 # le maillon et son inverse
 ("aide", "    bundle = avant_dzcurseur(bundle)             # 29/10 (t373)", "    # 29/10 (t373)"),
 ("maillon", '"aria-label":a,', ""),
]
tues = 0
try:
  for i, (k, a, b) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
    assert s.count(a2) == 1, (i, a)
    p.write_bytes(s.replace(a2, b2).encode("utf-8"))
    if k == "css": shutil.copy2(p, COPIE)           # la copie suit : seul le défaut compte
    if k == "lecteur": shutil.copy2(p, RACINE / "frontend/dist/shared/dz-lecteur.js")
    r = subprocess.run(BANC, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    shutil.copy2(SAUVE / "lecteur.orig", RACINE / "frontend/dist/shared/dz-lecteur.js")
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  shutil.copy2(SAUVE / "lecteur.orig", RACINE / "frontend/dist/shared/dz-lecteur.js")
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
        and filecmp.cmp(SAUVE / "lecteur.orig", RACINE / "frontend/dist/shared/dz-lecteur.js", shallow=False))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
