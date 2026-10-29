# -*- coding: utf-8 -*-
"""Mutations t371 (29/10/2026) : docks lisibles et marges du Photolab. Chaque mutation (photolab.css, js/mod-docks.js,
js/core.js) doit faire ÉCHOUER frontend/photolab/qa/docks.test.mjs. Les sources sont copiées AVANT, restaurées après
chaque mutation et comparées octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_docks_photolab.py"""
import filecmp, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "photolab"
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_docks_"))
F = {"css": R / "photolab.css", "js": R / "js/mod-docks.js", "core": R / "js/core.js"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
M = [
 ("css", "overflow-y: hidden; scrollbar-width: none;", "overflow-y: auto; scrollbar-width: none;"),
 ("css", "scrollbar-width: none; }", "scrollbar-width: thin; }"),
 ("css", ".groupe-tete::-webkit-scrollbar { display: none; }", ""),
 ("css", "max-width: 132px; overflow: hidden; white-space: nowrap;", "max-width: 132px; overflow: hidden; white-space: normal;"),
 ("css", "flex: 0 0 auto; max-width: 132px;", "flex: 1 1 auto; max-width: 132px;"),
 ("css", "padding: 0 var(--pad-2); color: var(--ink-muted);", "padding: 0 8px; color: var(--ink-muted);"),
 ("css", "overflow: auto; padding: var(--pad-2); }", "overflow: auto; padding: 8px; }"),
 ("css", "gap: 4px; padding: var(--pad-2);", "gap: 4px; padding: 6px 8px;"),
 ("css", "::-webkit-scrollbar-corner { background: transparent; }", ""),
 ("css", "var(--stroke-strong) 55% 62%", "white 55% 62%"),
 ("css", ".groupe-tete:not(.deborde) .groupe-plus { display: none; }", ""),
 ("css", "  position: sticky; right: 0;", "  position: relative; right: 0;"),
 ("css", "align-items: stretch; gap: 0; padding: 0;", "align-items: stretch; gap: 0; padding: 0 6px;"),
 ("css", "border: 1px solid var(--stroke-strong); border-radius: var(--radius);", "border: 1px solid var(--stroke-strong); border-radius: 3px;"),
 ("js", "return Number(largeurContenu) - Number(largeurVue) > 1;", "return Number(largeurContenu) - Number(largeurVue) > 0;"),
 ("js", "if (gauche < defil || largeur > utile) return gauche;", "if (gauche < defil) return gauche;"),
 ("js", "const utile = Math.max(0, vue - reserve);", "const utile = Math.max(0, vue);"),
 ("js", "Math.abs(dx) > Math.abs(dy) ? dx : dy", "dy"),
 ("js", "Math.min(Math.max(defil + pas, 0), Math.max(0, max))", "Math.max(defil + pas, 0)"),
 ("js", ".filter((o) => o.texte);", ";"),
 ("js", "export const RESERVE_PLUS = 24;", "export const RESERVE_PLUS = 0;"),
 ("core", "initDocks(PL);           //", "//"),
]
tues = 0
try:
  for i, (k, a, b) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    assert s.count(a) == 1, (i, a)
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    r = subprocess.run(["node", "qa/docks.test.mjs"], cwd=R, capture_output=True, text=True, encoding="utf-8")
    shutil.copy2(SAUVE / (k + ".orig"), p)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:60]}")
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
