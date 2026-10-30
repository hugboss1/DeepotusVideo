# -*- coding: utf-8 -*-
"""Mutations t383 (30/10/2026) : le thème clair complet — feuille frontend/shared/dz-palette.css (et sa copie), alias
--pal-* et damier de frontend/shared/dz-apparence.js, accent clair et 8e contrôle, damiers des labs, lien de la SPA ;
bancs backend/tests/test_clair_ecran.py et test_apparence_ecran.py (qui joue frontend/shared/qa/apparence.test.mjs).
Chaque mutation doit faire ÉCHOUER son banc. Les fichiers sont copiés AVANT, restaurés après chaque mutation et
comparés octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_clair.py   (DZ_MUT=3,7 : rejouer celles-là)"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_clair_"))
F = {"pal": RACINE / "frontend/shared/dz-palette.css", "pald": RACINE / "frontend/dist/shared/dz-palette.css",
     "js": RACINE / "frontend/shared/dz-apparence.js", "jsd": RACINE / "frontend/dist/shared/dz-apparence.js",
     "html": RACINE / "frontend/dist/index.html", "vl": RACINE / "frontend/vectorlab/vectorlab.css",
     "tl": RACINE / "frontend/tilelab/tilelab.css", "sl": RACINE / "frontend/spritelab/spritelab.css",
     "mf": RACINE / "frontend/materialforge/materialforge.css", "ag": RACINE / "AGENTS.md"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
CLAIR = [sys.executable, "tests/test_clair_ecran.py"]
ECRAN = [sys.executable, "tests/test_apparence_ecran.py"]
M = [
 # ── la feuille ──
 ("pal", CLAIR, "  --bg:var(--pal-fond); --panel:var(--pal-panneau);", "  --panel:var(--pal-panneau);"),
 ("pal", CLAIR, "--ink:var(--pal-encre-1); --ink2:var(--pal-encre-2);", "--ink:var(--pal-encre-1); --ink2:#413d36;"),
 ("pal", CLAIR, "  --accent:var(--pal-accent); --accent-ink:var(--pal-encre-accent);", "  --accent:var(--pal-accent);"),
 ("pal", CLAIR, "--panel3:var(--pal-puits);", "--panel3:var(--pal-sol);"),
 ("pal", CLAIR, ':root[data-dz-apparence="light"] .dzsvm select{color-scheme:light}', ':root[data-dz-apparence="light"] .dzsvm select{color-scheme:dark}'),
 ("pal", CLAIR, "  --cyan:var(--pal-accent) !important;", "  --cyan:var(--pal-accent);"),
 ("pal", CLAIR, ":root[data-dz-apparence] body{", ".dzsvm body{"),
 ("pal", CLAIR, "  --violet:#5d4f96; --violet-soft:#5d4f9622;", "  --violet:#9b8ec4; --violet-soft:#9b8ec422;"),
 ("pal", CLAIR, "  --node-av:#5d4f96; --node-text:#6b5c47;", "  --node-av:#5d4f96; --node-text:#6b5c47; --brand:#b8282a;"),
 ("pal", CLAIR, '[style*="radial-gradient(circle at center"]{', "{"),
 ("pal", CLAIR, "  background-color:var(--pal-fond) !important;\n", "  background-color:#f2f0ec !important;\n"),
 ("pald", CLAIR, "  --c-av:#5d4f96;", "  --c-av:#9b8ec4;"),
 ("html", CLAIR, '    <link rel="stylesheet" href="/shared/dz-palette.css">\n', ""),
 # ── dz-apparence.js : alias, damier, accent, contrôles ──
 ("js", CLAIR, '    v["--pal-encre-3"] = v["--ink-soft"];', '    v["--pal-encre-3"] = v["--ink"];'),
 ("js", CLAIR, '    v["--pal-puits"] =', '    v["--pal-sol"] ='),
 ("js", CLAIR, '    v["--damier-a"] = melange(c.panneau, c.texte, 0.1);', '    v["--damier-a"] = melange(c.panneau, c.texte, 0.6);'),
 ("js", CLAIR, '    v["--damier-b"] = melange(c.panneau, c.texte, 0.03);', '    v["--damier-b"] = melange(c.panneau, c.texte, 0.1);'),
 ("js", ECRAN, 'accent: "#8c5c00"', 'accent: "#a06a00"'),
 ("js", ECRAN, ' ["accent_fond", c.accent, c.fond, 4.5],', ''),
 ("js", ECRAN, "clair: [0.15, 0.32, 0.6]", "clair: [0.15, 0.4, 0.6]"),
 # ── damiers des labs ──
 ("vl", CLAIR, "repeating-conic-gradient(var(--damier-a,#2a2a2a) 0 25%, var(--damier-b,#1c1c1c) 0 50%)", "repeating-conic-gradient(#2a2a2a 0 25%, #1c1c1c 0 50%)"),
 ("tl", CLAIR, "var(--damier-a,#2a2a2a) 0 25%, var(--damier-b,#1c1c1c) 0 50%) 0 0 / 16px 16px", "var(--damier-a,#333333) 0 25%, var(--damier-b,#1c1c1c) 0 50%) 0 0 / 16px 16px"),
 ("sl", CLAIR, "repeating-conic-gradient(var(--damier-a,#1e293b) 0% 25%, var(--damier-b,#0f172a) 0% 50%) 0 0/18px 18px", "repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 0 0/18px 18px"),
 ("mf", CLAIR, "var(--damier-a,#1a1a1f)", "var(--damier-a,#1a1a1a)"),
 # ── documentation ──
 ("ag", CLAIR, "| `frontend/shared/dz-palette.css` (+ `scripts/clair_audit.js`)", "| `frontend/shared/dz-palette.css`"),
]
QUE = {int(x) for x in os.environ.get("DZ_MUT", "").split(",") if x.strip()}
tues = jouees = 0
try:
  for i, (k, banc, a, b) in enumerate(M, 1):
    if QUE and i not in QUE:
        continue
    jouees += 1
    p = F[k]; s = p.read_bytes().decode("utf-8")
    if "\r\n" in s:
        a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    assert s.count(a) == 1, (i, a, s.count(a))
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    if k in ("js", "pal"):                     # la copie de dist suit la source : la mutation vise le COMPORTEMENT
        shutil.copy2(p, F[k + "d"])
    r = subprocess.run(banc, cwd=RACINE / "backend", capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{jouees} mutations tuées")
sys.exit(0 if tues == jouees else 1)
