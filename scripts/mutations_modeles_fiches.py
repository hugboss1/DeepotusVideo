# -*- coding: utf-8 -*-
"""Mutations t475 (09/11/2026) : fiches modèle (contrat, tronc commun, service `modeles_fiches`, règle « pas de nom de
modèle » des rôles métier et des méthodes). Chaque mutation doit faire ÉCHOUER backend/tests/test_modeles_fiches.py.
Les sources sont copiées AVANT, restaurées après chaque mutation et comparées octet à octet à la fin ; une fiche créée
par une mutation est supprimée. Aucune ne touche le bundle ni un registre.
Run (depuis la racine) : & $PY scripts/mutations_modeles_fiches.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_fiches_"))
F = {"svc": RACINE / "backend/app/services/modeles_fiches.py",
     "cfr": RACINE / "docs/agent/modeles/fr/_commun.md", "cen": RACINE / "docs/agent/modeles/en/_commun.md",
     "monteur": RACINE / "docs/agent/metiers/monteur.md", "methodes": RACINE / "backend/app/knowledge/methodes.json",
     "agents": RACINE / "AGENTS.md", "licence": RACINE / "docs/licences/scenario-mit.md"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
BANC = [sys.executable, "backend/tests/test_modeles_fiches.py"]
CREEE = RACINE / "docs/agent/modeles/fr/zz-mutation.md"
M = [
 # données et documents
 ("cfr", "## Exemple\n", "## Exemples\n"),
 ("cen", "description: Use when reading", "description: Read when reading"),
 ("monteur", "(un modèle de retouche vidéo, une seule", "(Seedance, une seule"),
 ("methodes", "Flèches dans le sens du flux", "Flèches dans le sens du FLUX"),
 ("agents", "| `backend/app/services/modeles_fiches.py` (+", "| `backend/app/services/modeles_fiche.py` (+"),
 ("licence", "## Fiches modèle (t475", "## Fiches (t475"),
 ("CREER", "", ""),                                                        # fiche FR sans traduction EN
 # règles du contrat
 ("svc", "(?:jusqu['’]à|up to|", "(?:up to|"),
 ("svc", "            if i in proprietaire:", "            if False:"),
 ("svc", "            if e[\"id\"] not in proprietaire:", "            if False:"),
 ("svc", "for fam in sorted(set(fr) ^ set(en)):", "for fam in sorted(set()):"),
 ("svc", "            if fr[fam][0].get(cle) != en[fam][0].get(cle):", "            if False:"),
 ("svc", "    elif len(desc) > DESCRIPTION_MAX:", "    elif False:"),
 ("svc", "    if n > lim:", "    if False:"),
 ("svc", "    if titres != list(TITRES[lg]):", "    if False:"),
 ("svc", "            if i not in servis:", "            if False:"),
 ("svc", "            if n not in connues:", "            if False:"),
 ("svc", "    if fam != COMMUN and not _NOM_FAMILLE.fullmatch(fam):", "    if False:"),
 ("svc", "    if not re.fullmatch(r\"\\d{4}-\\d{2}-\\d{2}\", str(meta.get(\"releve\", \"\"))):", "    if False:"),
 ("svc", "    if not meta.get(\"source\"):", "    if False:"),
 ("svc", "    if meta.get(\"famille\") != fam:", "    if False:"),
 ("svc", "        if COMMUN not in toutes[lg]:", "        if False:"),
 # règle des noms
 ("svc", "r\"\\b(?i:seedance|", "r\"\\b(?:seedance|"),
 ("svc", "(\"titre\", \"resume\", \"etapes\", \"controles\", \"pieges\")", "(\"titre\", \"resume\", \"etapes\", \"pieges\")"),
 # service
 ("svc", "        if val.startswith(\"[\") and val.endswith(\"]\"):", "        if False:"),
 ("svc", "vues.setdefault(e[\"id\"], dict(e, natures=[]))[\"natures\"].append(nature)",
  "vues.setdefault(e[\"id\"], dict(e, natures=[nature]))"),
 ("svc", "vues[m[\"id\"]].update(", "vues[m[\"id\"]].get("),
 ("svc", "    if langue != \"fr\" and not fiches:", "    if False:"),
 ("svc", "\"price to be measured\" if en else \"prix à mesurer\")", "\"price to be measured\" if en else \"gratuit\")"),
]
tues = 0
try:
    for i, (k, a, b) in enumerate(M, 1):
        if k == "CREER":
            CREEE.write_text((RACINE / "docs/agent/modeles/fr/_commun.md").read_text(encoding="utf-8")
                             .replace("famille: _commun", "famille: zz-mutation"), encoding="utf-8")
            etiquette = "fiche FR sans EN"
        else:
            p = F[k]; s = p.read_bytes().decode("utf-8")
            a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
            assert s.count(a2) == 1, (i, k, a, s.count(a2))
            p.write_bytes(s.replace(a2, b2).encode("utf-8"))
            etiquette = f"{k}: {a.strip()[:64]!r}"
        r = subprocess.run(BANC, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONUTF8": "1"})
        if k == "CREER":
            CREEE.unlink()
        else:
            shutil.copy2(SAUVE / (k + ".orig"), F[k])
        ok = r.returncode != 0; tues += ok
        print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {etiquette}")
finally:
    for k, p in F.items():
        shutil.copy2(SAUVE / (k + ".orig"), p)
    if CREEE.exists():
        CREEE.unlink()
    print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
          and not CREEE.exists())
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
