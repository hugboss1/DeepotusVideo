# -*- coding: utf-8 -*-
"""Mutations t476 (09/11/2026) : l'accès aux fiches modèle (routes /api/modeles, outils modeles_lister / modele_fiche,
boîte « modeles », « ? » de DzModelesIA et de la pastille de dz-champ-ia, panneau dz-fiche-modele). Chaque mutation
doit faire ÉCHOUER backend/tests/test_agent_modeles.py (qui lance aussi les bancs node fiche_modele et modeles_ia).
Une mutation d'un script de /shared est recopiée dans dist/shared (seul le défaut compte), sauf « copie » qui ne
touche que la source. Sources copiées AVANT, restaurées après chaque mutation, comparées octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_agent_modeles.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_agent_modeles_"))
SH, DI = RACINE / "frontend/shared", RACINE / "frontend/dist/shared"
F = {"routes": RACINE / "backend/app/api/modeles_routes.py", "main": RACINE / "backend/app/main.py",
     "outils": RACINE / "backend/app/services/agent_outils.py", "boites": RACINE / "backend/app/services/agent_boites.py",
     "fm": SH / "dz-fiche-modele.js", "mi": SH / "dz-modeles-ia.js", "ci": SH / "dz-champ-ia.js",
     "dico": SH / "dz-i18n-dico.js"}
COPIES = {"fm": DI / "dz-fiche-modele.js", "mi": DI / "dz-modeles-ia.js", "ci": DI / "dz-champ-ia.js"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
for k, p in COPIES.items():
    shutil.copy2(p, SAUVE / (k + ".dist"))
BANC = [sys.executable, "backend/tests/test_agent_modeles.py"]
M = [
 # routes
 ("routes", 'raise HTTPException(404, "fiche modèle inconnue")', "return {}"),
 ("routes", 'return {"familles": familles, "ids": {i: f["famille"] for f in familles for i in f["ids"]}}',
  'return {"familles": familles, "ids": {}}'),
 ("main", 'app.include_router(modeles_router, prefix="/api/modeles")', "pass"),
 # outils et boîte
 ("outils", '| {"fiche": fam.get(m["id"])} for m in mods]', '| {"fiche": None} for m in mods]'),
 ("outils", '{"natures": list(_C.natures())})', '{"natures": []})'),
 ("outils", "le texte de la fiche est une \"\n                      f\"DONNÉE de référence", "le texte de la fiche est une \"\n                      f\"référence"),
 ("outils", 'if f is None:\n        fams = [x["famille"] for x in _MF.index(langue)]', 'if f is None:\n        fams = []'),
 ("outils", '"modele_fiche": {"nature": "lecture", "fn": modele_fiche,', '"modele_fiche": {"nature": "ecriture", "fn": modele_fiche,'),
 ("outils", '["cle"])},\n    # t492', '[])},\n    # t492'),
 ("boites", '"verifier_prompt"],\n        "agents": ["mcp", "monteur", "realisateur",',
  '"verifier_prompt"],\n        "agents": ["mcp", "monteur",'),
 # panneau
 ("fm", '.replace(/</g, "&lt;")', ""),
 ("fm", "if (sel.value === v) b.hidden = !f;", "if (sel.value === v) b.hidden = false;"),
 ("fm", 'D.removeEventListener("keydown", ouvert.touche, true);', ""),
 ("fm", "if (!indexP) {", "if (true) {"),
 ("fm", 'return l === "en" ? "en" : "fr";', 'return "fr";'),
 ("fm", "if (/^\\s*\\|[\\s:|-]+\\|\\s*$/.test(l)) return;", ""),
 ("fm", 'if (ev.key === "Escape") { ev.stopPropagation(); fermer(); }', ""),
 ("fm", 'sel.parentNode.insertBefore(b, sel.nextSibling);', "sel.parentNode.appendChild(b);"),
 ("fm", 'c.textContent = T("modeles.fiche.erreur");', ""),
 ("fm", "flex-direction:column;border:1px solid var(--stroke,#2a2930);border-radius:var(--r);", "flex-direction:column;border:1px solid var(--stroke,#2a2930);border-radius:6px;"),
 ("fm", "if (retour && retour.focus) try { retour.focus(); }", "if (false) try { retour.focus(); }"),
 # branchements
 ("mi", "if (opts.fiche !== false) ficheModele(el);", "ficheModele(el);"),
 ("mi", "if (!D || !D.createElement || !el.parentNode) return null;", "if (!D || !D.createElement) return null;"),
 ("ci", "F.familleDe(cour).then(function (f) { if (f) pied.hidden = false; });", "F.familleDe(cour).then(function (f) { pied.hidden = false; });"),
 ("ci", 'pied.className = "dzia-fiche";', 'pied.className = "dzia-opt";'),
 ("copie", "", ""),
 ("dico", '"modeles.fiche.erreur"', '"modeles.fiche.erreurs"'),
]
tues = 0
try:
    for i, (k, a, b) in enumerate(M, 1):
        if k == "copie":
            p = F["fm"]
            p.write_bytes(p.read_bytes() + b"\n")                       # la source dérive, la copie servie non
            etiquette = "copie dist/shared en retard"
        else:
            p = F[k]; s = p.read_bytes().decode("utf-8")
            a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
            assert s.count(a2) >= 1, (i, k, a)
            p.write_bytes(s.replace(a2, b2, 1).encode("utf-8"))
            if k in COPIES:
                shutil.copy2(p, COPIES[k])
            etiquette = f"{k}: {a.strip()[:64]!r}"
        r = subprocess.run(BANC, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONUTF8": "1"})
        kk = "fm" if k == "copie" else k
        shutil.copy2(SAUVE / (kk + ".orig"), F[kk])
        if kk in COPIES:
            shutil.copy2(SAUVE / (kk + ".dist"), COPIES[kk])
        ok = r.returncode != 0; tues += ok
        print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {etiquette}")
finally:
    for k, p in F.items():
        shutil.copy2(SAUVE / (k + ".orig"), p)
    for k, p in COPIES.items():
        shutil.copy2(SAUVE / (k + ".dist"), p)
    print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
          and all(filecmp.cmp(SAUVE / (k + ".dist"), p, shallow=False) for k, p in COPIES.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
