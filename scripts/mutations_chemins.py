# -*- coding: utf-8 -*-
"""Mutations t378 (30/10/2026) : les emplacements de Réglages › Chemins (service backend/app/services/emplacements.py,
écran frontend/shared/dz-chemins.js et sa copie, dictionnaire chemins.json, maillon patch_bundle_dzchemins).
Chaque mutation doit faire ÉCHOUER son banc : backend/tests/test_emplacements.py (« serveur ») ou
backend/tests/test_emplacements_ecran.py (« ecran », qui joue aussi frontend/shared/qa/chemins.test.mjs). Les fichiers
sont copiés AVANT, restaurés après chaque mutation et comparés octet à octet à la fin (le bundle compris).
Une mutation « js » touche la source ET sa copie de frontend/dist/shared : c'est le comportement qui doit rougir, pas
la seule égalité des copies.
Run (depuis la racine) : & $PY scripts/mutations_chemins.py [index…]   (sans index : toutes)"""
import filecmp, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_chemins_"))
F = {"service": RACINE / "backend/app/services/emplacements.py", "routes": RACINE / "backend/app/api/settings_routes.py",
     "js": RACINE / "frontend/shared/dz-chemins.js", "jsdist": RACINE / "frontend/dist/shared/dz-chemins.js",
     "dico": RACINE / "frontend/shared/i18n/chemins.json", "aide": RACINE / "backend/tests/_i18n_l1_aide.py",
     "maillon": RACINE / "scripts/patch_bundle_dzchemins.py", "page": RACINE / "frontend/dist/index.html",
     "bundle": RACINE / "frontend/dist/assets/index-BEOJX8L5.js"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
BANCS = {"serveur": [sys.executable, "backend/tests/test_emplacements.py"],
         "ecran": [sys.executable, "backend/tests/test_emplacements_ecran.py"]}
M = [
 # ── le service : validation ──
 ("serveur", "service", '_UTILISATEUR = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,63}$")',
  '_UTILISATEUR = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}$")'),
 ("serveur", "service", '_DISTANT = re.compile(r"^/[^\\"\\\\\\x00-\\x1f\\x7f]{0,400}$")',
  '_DISTANT = re.compile(r"^/[^\\"\\x00-\\x1f\\x7f]{0,400}$")'),
 ("serveur", "service", "if _dans(Path(s), Path(interdit)) or _dans(Path(interdit), Path(s)):",
  "if _dans(Path(s), Path(interdit)):"),
 ("serveur", "service", "        port = 22 if port in (None, \"\") else int(port)", "        port = int(port or 22)"),
 ("serveur", "service", '    if not isinstance(v, (list, tuple)) or any(r not in ROLES for r in v):',
  '    if not isinstance(v, (list, tuple)):'),
 # ── le service : secret ──
 ("serveur", "service", "    _poser_secret(eid, \"\")\n    doc[\"emplacements\"].pop(eid)", "    doc[\"emplacements\"].pop(eid)"),
 ("serveur", "service", "        v[\"secret_pose\"] = bool(_secret(eid))", "        v[\"secret_pose\"] = _secret(eid)"),
 ("serveur", "service", "    _coffre_libre(bool(secret))\n    eid = _id_neuf", "    eid = _id_neuf"),
 # ── le service : test et vérification ──
 ("serveur", "service", "            f.unlink(missing_ok=True)", "            pass"),
 ("serveur", "service", "    return bool(roles) and set(roles) == {\"bibliotheque\"}", "    return False"),
 ("serveur", "service", "**_essayer(k, e, leger=True)}", "**_essayer(k, e, leger=False)}"),
 ("serveur", "service", "        neuf.pop(\"dernier_test\", None)", "        pass"),
 ("serveur", "service", "for motif, code in ((\"permission denied\", \"acces_refuse\"),", "for motif, code in ((\"permission denied\", \"echec\"),"),
 # ── le service : sftp.exe ──
 ("serveur", "service", '            args += ["-o", "BatchMode=no", ', '            args += ["-o", "BatchMode=yes", '),
 ("serveur", "service", ' and k not in coffre.SECRETES}', '}'),
 ("serveur", "service", '"-o", f"UserKnownHostsFile={_known_hosts()}",\n', ''),
 ("serveur", "service", "        if mdp:\n            sortie = sortie.replace(mdp, \"•••\")\n", ""),
 # ── les routes ──
 ("serveur", "routes", "async def verifier_emplacements(request: Request):\n    \"\"\"Le Diagnostic : chaque emplacement est-il joignable ? (lecture seule là-bas).\"\"\"\n    import asyncio\n    _local(request)",
  "async def verifier_emplacements(request: Request):\n    \"\"\"Le Diagnostic : chaque emplacement est-il joignable ? (lecture seule là-bas).\"\"\"\n    import asyncio"),
 ("serveur", "routes", "        return HTTPException(409, f\"Coffre verrouillé : {e}\")\n    if isinstance(e, _E.EmplacementInconnu)",
  "        return HTTPException(400, f\"Coffre verrouillé : {e}\")\n    if isinstance(e, _E.EmplacementInconnu)"),
 # ── l'écran (source ET copie) ──
 ("ecran", "js", "      if (c.secret) b.secret = c.secret;", "      b.secret = c.secret;"),
 ("ecran", "js", "      if (!es.length) return es;", ""),
 ("ecran", "js", "    var avecCoffre = f.id && f.secret_pose && !f.champs.secret && !f.champs.effacer_secret;",
  "    var avecCoffre = false;"),
 ("ecran", "js", "    if (!hote || hote.__dzChemins) return hote && hote.__dzChemins;", "    if (!hote) return null;"),
 ("ecran", "js", "      if (!v) return null;\n", ""),
 ("ecran", "js", "    if (r.libre_octets != null) t += ", "    if (false) t += "),
 ("ecran", "js", "    return (langue() === \"en\" ? t : t.replace(\".\", \",\")) + \" \" + u[i];", "    return t + \" \" + u[i];"),
 ("ecran", "js", 'T("chemins.emplacements.vide")', '"Aucun emplacement pour l\'instant."'),
 ("ecran", "js", "border-radius:0;background:var(--srf-sunken", "border-radius:3px;background:var(--srf-sunken"),
 # ── le dictionnaire ──
 ("ecran", "dico", '"en": "Write and read succeeded"', '"en": "Écriture et lecture réussies"'),
 ("ecran", "dico", '"en": "Failed: {erreur}"', '"en": "Failed: {error}"'),
 ("ecran", "dico", ' "chemins.etat.delai": {\n  "fr": "Délai dépassé",\n  "en": "Timed out"\n },\n', ''),
 # ── la page, le maillon et son inverse ──
 ("ecran", "page", '    <script src="/shared/dz-chemins.js"></script>\r\n', ''),
 ("ecran", "aide", "    bundle = avant_dzchemins(bundle)             # 30/10 (t378)", "    # 30/10 (t378)"),
 ("ecran", "maillon", '    ("dza2d", "/*dza2d*/", 1),\n', ''),
 ("ecran", "bundle", "window.__dzChemins.diag(el)", "window.__dzChemins.monter(el)"),
]


def restaurer():
    for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)


def muter(cle, avant, apres):
    p = F[cle]
    b = p.read_bytes().decode("utf-8")
    lf = b.replace("\r\n", "\n")
    a, z = avant.replace("\r\n", "\n"), apres.replace("\r\n", "\n")
    if lf.count(a) != 1:
        return f"ancre x{lf.count(a)}"
    neuf = lf.replace(a, z, 1)
    if "\r\n" in b: neuf = neuf.replace("\n", "\r\n")
    p.write_bytes(neuf.encode("utf-8"))
    if cle == "js":
        shutil.copyfile(p, F["jsdist"])
    return None


tues = survivants = 0
try:
    SEULES = {int(x) for x in sys.argv[1:]}
    for i, (banc, cle, avant, apres) in enumerate(M):
        if SEULES and i not in SEULES:
            continue
        err = muter(cle, avant, apres)
        if err:
            print(f"  ??       {err} dans {cle} : {avant[:70]!r}"); survivants += 1; restaurer(); continue
        r = subprocess.run(BANCS[banc], cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
        if r.returncode != 0:
            tues += 1; print(f"  TUÉ      {banc}/{cle} : {avant[:70]!r}")
        else:
            survivants += 1; print(f"  SURVIT   {banc}/{cle} : {avant[:70]!r}")
        restaurer()
finally:
    restaurer()
    egaux = all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
    print(f"\n{tues} tués / {survivants} survivants ; sources restaurées à l'octet : {egaux}")
    sys.exit(0 if survivants == 0 and egaux else 1)
