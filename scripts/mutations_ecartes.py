# -*- coding: utf-8 -*-
"""Mutations t375 (29/10/2026) : la puce « N écartés ce jour » de News (maillon patch_bundle_dzecartes, clés
news.liste.ecartes_*). Chaque mutation du bundle écrit, du dictionnaire, des textes ou de l'inverse doit faire ÉCHOUER
backend/tests/test_news_ecartes_ecran.py. Les fichiers sont copiés AVANT, restaurés après chaque mutation et comparés
octet à octet à la fin (le bundle compris).
Run (depuis la racine) : & $PY scripts/mutations_ecartes.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_ecartes_"))
F = {"bundle": RACINE / "frontend/dist/assets/index-BEOJX8L5.js", "news": RACINE / "frontend/shared/i18n/news_survol.json",
     "dico": RACINE / "frontend/dist/shared/dz-i18n-dico.js", "aide": RACINE / "backend/tests/_i18n_l1_aide.py",
     "maillon": RACINE / "scripts/patch_bundle_dzecartes.py"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
BANC = [sys.executable, "backend/tests/test_news_ecartes_ecran.py"]
M = [
 # le survol
 ("bundle", 'title:dzNewsEcartesResume(ranked.ecartes),', 'title:ranked.ecartes.map(function(z){return z.title}).join("\\n"),'),
 ("bundle", 'o.sort(function(a,b){return m[b]-m[a]});', ''),
 ("bundle", 'var k=z.motif||"?";', 'var k=z.title||"?";'),
 ("bundle", '.concat([dzT("news.liste.ecartes_tout_aide")])', ''),
 ("bundle", '{n:(l||[]).length}', '{n:o.length}'),
 ("bundle", 'return m[k]+" · "+k', 'return k'),
 # « Tout afficher »
 ("bundle", 'children:dzT("news.liste.ecartes_tout")}', 'children:"Tout afficher"}'),
 ("bundle", 'maxHeight:"50vh",', ''),
 ("bundle", 'maxHeight:"50vh",overflow:"auto",background:"var(--bg-panel)"', 'maxHeight:"50vh",overflow:"auto",background:"#16161a"'),
 ("bundle", 'border:"1px solid var(--stroke-strong)",boxShadow:', 'border:"1px solid var(--stroke-strong)",borderRadius:6,boxShadow:'),
 ("bundle", 'r.jsx("div",{role:"list",', 'r.jsx("div",{'),
 ("bundle", 'children:z.motif})]},z.id)', 'children:""})]},z.id)'),
 ("bundle", 'children:z.motif})]},z.id)', 'children:z.motif})]})'),
 ("bundle", 'r.jsxs("details",{className:"dz-news-ecartes"', 'r.jsxs("div",{className:"dz-news-ecartes"'),
 # textes et dictionnaire
 ("news", '"en": "List all"}', '"en": "Tout afficher"}'),
 ("news", '"fr": "Écartés par le filtre : {n}"', '"fr": "{n} écartés"'),
 ("dico", '"news.liste.ecartes_tout_aide"', '"news.liste.ecartes_tout_aideX"'),
 # l'inverse et le maillon
 ("aide", "    bundle = avant_dzecartes(bundle)             # 29/10 (t375)", "    # 29/10 (t375)"),
 ("maillon", '("dzcurseur", "/*dzcurseur*/", 1),', '("dzmcp", "/*dzmcp*/", 1),'),
 ("maillon", "    (ECRAN, RESUME + ECRAN),", "    (ECRAN, RESUME + ECRAN + \"\"),\n    (\"/*x*/\", \"/*x*/\"),"),
]
tues = 0
try:
  for i, (k, a, b) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    assert s.count(a) == 1, (i, a, s.count(a))
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    r = subprocess.run(BANC, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
