# -*- coding: utf-8 -*-
"""Mutations t372 (29/10/2026) : le lecteur audio/vidéo commun à la charte (frontend/shared/dz-lecteur.js). Chaque
mutation du script, de sa copie servie ou d'une page qui le charge doit faire ÉCHOUER frontend/shared/qa/lecteur.test.mjs
(comportement) OU backend/tests/test_lecteur_ecran.py (branchements, feuille, textes). Les sources sont copiées AVANT,
restaurées après chaque mutation et comparées octet à octet à la fin. Aucune ne touche le bundle.
Run (depuis la racine) : & $PY scripts/mutations_lecteur.py"""
import filecmp, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_lecteur_"))
F = {"js": RACINE / "frontend/shared/dz-lecteur.js", "coque": RACINE / "frontend/dist/index.html",
     "atelier": RACINE / "frontend/atelier/index.html", "i18n": RACINE / "frontend/shared/i18n/lecteur.json"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
NOEUD = ["node", "frontend/shared/qa/lecteur.test.mjs"]
BANC = [sys.executable, "backend/tests/test_lecteur_ecran.py"]
M = [
 # comportement (banc node)
 ("js", 'media.removeAttribute("controls");\n    media.setAttribute("data-dz-lecteur", "ameliore");', 'media.setAttribute("data-dz-lecteur", "ameliore");', NOEUD),
 ("js", "parent.insertBefore(barre, media.nextSibling);", "parent.appendChild(barre);", NOEUD),
 ("js", 'if (media.getAttribute("data-dz-lecteur") === "natif") return null;', "", NOEUD),
 ("js", 'if (m.hasAttribute("controls")) ameliorer(m);', "ameliorer(m);", NOEUD),
 ("js", "if (!L.plein && m.hasAttribute(\"controls\")) m.removeAttribute(\"controls\");", "", NOEUD),
 ("js", "if (L.media.isConnected) return true;", "return true;", NOEUD),
 ("js", "if (!isFinite(s) || s < 0) return \"--:--\";", "if (!isFinite(s)) return \"--:--\";", NOEUD),
 ("js", 'return h ? h + ":" + (m < 10 ? "0" : "") + m + ":" + xx : m + ":" + xx;', 'return m + ":" + xx;', NOEUD),
 ("js", "if (isFinite(d) && d > 0) media.currentTime = Number(pos.value) / PAS * d;", "", NOEUD),
 ("js", "if (!L.glisse) pos.value =", "pos.value =", NOEUD),
 ("js", 'pos.addEventListener("change", function () { L.glisse = false; });', "", NOEUD),
 ("js", "media.volume = Number(vol.value) / 100; media.muted = false;", "media.volume = Number(vol.value) / 100;", NOEUD),
 ("js", '".dz-lecteur input[type=range]{flex:1 1 auto;min-width:40px}",', '".dz-lecteur input[type=range]{flex:1 1 auto;min-width:40px}::-webkit-slider-thumb{}",', BANC),   # t373
 ("js", 'barre.setAttribute("data-visible", !joue || L.survol || L.focus ? "1" : "0");', 'barre.setAttribute("data-visible", "1");', NOEUD),
 ("js", 'if (ps === "static") parent.style.position = "relative";', "", NOEUD),
 ("js", 'barre.style.top = (media.offsetTop + media.offsetHeight - HAUTEUR) + "px";', 'barre.style.top = media.offsetTop + "px";', NOEUD),
 ("js", 'media.setAttribute("controls", "");      //', "//", NOEUD),
 ("js", 'lire.setAttribute("disabled", "");', "", NOEUD),
 ("js", 'ecouter(media, "click", basculer);', "", NOEUD),
 ("js", 'muet ? ICONES.muet : ICONES.son', "ICONES.son", NOEUD),
 ("js", "if (!document.head || document.getElementById(\"dz-lecteur-css\")) return;", "if (!document.head) return;", NOEUD),
 ("js", "  observer();\n})();", "})();", NOEUD),
 # feuille, textes, branchements (banc python)
 ("js", "background:var(--amber);border-color:var(--amber)", "background:#f0b429;border-color:var(--amber)", BANC),
 ("js", "border:1px solid var(--stroke);border-radius:var(--radius);", "border:1px solid var(--stroke);border-radius:4px;", BANC),
 ("js", "font-family:var(--font-mono);", "font-family:monospace;", BANC),
 ("js", '"aria-label": T("lecteur.curseur.volume")', '"aria-label": "Volume"', BANC),
 ("i18n", '"lecteur.curseur.volume": {"fr": "Volume", "en": "Volume"},', '"lecteur.curseur.volume": {"fr": "Volume", "en": ""},', BANC),
 ("coque", '<script src="/shared/dz-lecteur.js"></script>', "", BANC),
 ("atelier", '<script src="/shared/dz-lecteur.js"></script>', "", BANC),
]
tues = 0
try:
  for i, (k, a, b, banc) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
    assert s.count(a2) == 1, (i, a)
    p.write_bytes(s.replace(a2, b2).encode("utf-8"))
    if k == "js": shutil.copy2(p, RACINE / "frontend/dist/shared/dz-lecteur.js")   # la copie suit : seul le défaut compte
    r = subprocess.run(banc, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**__import__("os").environ, "PYTHONUTF8": "1"})
    shutil.copy2(SAUVE / (k + ".orig"), p)
    if k == "js": shutil.copy2(SAUVE / "js.orig", RACINE / "frontend/dist/shared/dz-lecteur.js")
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}")
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  shutil.copy2(SAUVE / "js.orig", RACINE / "frontend/dist/shared/dz-lecteur.js")
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
        and filecmp.cmp(SAUVE / "js.orig", RACINE / "frontend/dist/shared/dz-lecteur.js", shallow=False))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
