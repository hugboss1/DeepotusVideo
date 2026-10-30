# -*- coding: utf-8 -*-
"""Mutations t382 (30/10/2026) : la palette de Réglages › Apparence — serveur (services/apparence.py, routes
/api/reglages/apparence de settings_routes.py ; banc backend/tests/test_apparence.py) et écran
(frontend/shared/dz-apparence.js et sa copie, dictionnaire apparence.json, maillon patch_bundle_dzapparence, inverse,
balise de la SPA ; banc backend/tests/test_apparence_ecran.py, qui joue frontend/shared/qa/apparence.test.mjs). Chaque
mutation doit faire ÉCHOUER son banc. Les fichiers sont copiés AVANT, restaurés après chaque mutation et comparés
octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_apparence.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_apparence_"))
F = {"sv": RACINE / "backend/app/services/apparence.py", "rt": RACINE / "backend/app/api/settings_routes.py",
     "js": RACINE / "frontend/shared/dz-apparence.js", "jsd": RACINE / "frontend/dist/shared/dz-apparence.js",
     "dico": RACINE / "frontend/shared/i18n/apparence.json", "bundle": RACINE / "frontend/dist/assets/index-BEOJX8L5.js",
     "aide": RACINE / "backend/tests/_i18n_l1_aide.py", "maillon": RACINE / "scripts/patch_bundle_dzapparence.py",
     "html": RACINE / "frontend/dist/index.html"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
SERVEUR = [sys.executable, "tests/test_apparence.py"]
ECRAN = [sys.executable, "tests/test_apparence_ecran.py"]
M = [
 # ── serveur ──
 ("sv", SERVEUR, 'PRESETS = ("sombre", "clair", "contraste", "deeplab")', 'PRESETS = ("sombre", "clair", "contraste")'),
 ("sv", SERVEUR, '        raise ValueError(f"Préréglage inconnu : {preset}")', '        return {"preset": "sombre"}'),
 ("sv", SERVEUR, '    if trop:\n', '    if False:\n'),
 ("sv", SERVEUR, '        propres[j] = v.lower()', '        propres[j] = v'),
 ("sv", SERVEUR, "if not isinstance(v, str) or not _HEX.match(v.lower()):", "if not isinstance(v, str):"),
 ("sv", SERVEUR, '    if fort is True:\n        etat["fort"] = True\n', ''),
 ("sv", SERVEUR, '    except (OSError, ValueError):\n        return dict(DEFAUT)', '    except OSError:\n        return dict(DEFAUT)'),
 ("sv", SERVEUR, "    etat = normaliser(corps)\n    f = _fichier()", "    etat = corps\n    f = _fichier()"),
 ("rt", SERVEUR, "async def apparence_poser(body: dict, request: Request):\n    _local(request)\n", "async def apparence_poser(body: dict, request: Request):\n"),
 ("rt", SERVEUR, '        raise HTTPException(400, str(e))\n\n\n@router.get("/index")', '        return {"etat": None}\n\n\n@router.get("/index")'),
 ("rt", SERVEUR, '"palette couleurs thème clair sombre contraste élevé', '"couleurs sombre élevé'),
 # ── écran : logique ──
 ("js", ECRAN, "    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);", "    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.5);"),
 ("js", ECRAN, "  function sombre(c) { return lum(c.fond) < 0.18; }", "  function sombre(c) { return lum(c.fond) < 0.01; }"),
 ("js", ECRAN, "    return contraste(noire, fond) >= contraste(BLANC, fond) ? noire : BLANC;", "    return BLANC;"),
 ("js", ECRAN, "  var POIDS = { sombre: [0.2, 0.45, 0.65], clair: [0.15, 0.32, 0.6]", "  var POIDS = { sombre: [0.2, 0.45, 0.65], clair: [0.15, 0.5, 0.6]"),
 ("js", ECRAN, '    v["--bg-panel-3"] = contexte === "lab"', '    v["--bg-panel-3"] = contexte === "labo"'),
 ("js", ECRAN, '    v["--cyan"] = c.accent;', '    v["--cyan"] = c.succes;'),
 ("js", ECRAN, '["accent_panneau", c.accent, c.panneau, 3]', '["accent_panneau", c.accent, c.panneau, 4.5]'),
 ("js", ECRAN, "    if (e.fort === true) n.fort = true;\n", ""),
 # ── écran : application ──
 ("js", ECRAN, "      if (marque === null) return;\n", ""),
 ("js", ECRAN, '      if (avant !== null) { r.setAttribute("data-theme", avant);', '      if (false) { r.setAttribute("data-theme", avant);'),
 ("js", ECRAN, "      if (d) appliquerArbre(d, \"lab\", prof + 1);", "      if (d && false) appliquerArbre(d, \"lab\", prof + 1);"),
 ("js", ECRAN, '    if (typeof f.addEventListener === "function") f.addEventListener("load", function () { peindreCadre(f, p); });', "    // load"),
 ("js", ECRAN, "    try { var d = f.contentDocument; return d && d.documentElement ? d : null; } catch (e) { return null; }", "    var d = f.contentDocument; return d && d.documentElement ? d : null;"),
 # ── écran : persistance ──
 ("js", ECRAN, "    garderLocal(n);\n    envoyer(n);", "    envoyer(n);"),
 ("js", ECRAN, "    if (minuterie) clearTimeout(minuterie);\n", ""),
 ("js", ECRAN, "        if (n && !choisiDepuisDemarrage && JSON.stringify(n)", "        if (false && JSON.stringify(n)"),
 ("js", ECRAN, "      if (!ev || ev.key !== CLE) return;", "      if (!ev) return;"),
 ("js", ECRAN, "appliquer(lireLocal() || { preset: \"sombre\" });\n  observer", "appliquer({ preset: \"sombre\" });\n  observer"),
 # ── écran : panneau ──
 ("js", ECRAN, "      choisir({ preset: \"libre\", couleurs: c, fort: fortDe(ETAT) });", "      choisir({ preset: \"libre\", couleurs: c });\n      c = null;"),
 ("js", ECRAN, "          h.value = couleursDe(ETAT)[j];\n", ""),
 ("js", ECRAN, "        if (v.charAt(0) !== \"#\") v = \"#\" + v;\n", ""),
 ("js", ECRAN, '      libre.textContent = ETAT.preset === "libre" ? T("apparence.preset.libre") : "";', '      libre.textContent = "";'),
 ("js", ECRAN, "      if (rates) zoneAlerte", "      if (false) zoneAlerte"),
 ("js", ECRAN, '    return (langue() === "en" ? t : t.replace(".", ",")) + ":1";', '    return t + ":1";'),
 ("js", ECRAN, "    if (hote.__dzApparence) { hote.__dzApparence.rafraichir(); return; }", "    if (false) { return; }"),
 ("js", ECRAN, "    PANNEAUX.forEach(function (p) { p.rafraichir(); });", "    // rafraichir"),
 ("js", ECRAN, '.catch(function (err) { statut(T("apparence.statut.echec"', '.catch(function (err) { statut(T("apparence.statut.hex_invalide"'),
 ("jsd", ECRAN, '  var URL_API = "/api/reglages/apparence";', '  var URL_API = "/api/reglages/apparence/";'),
 ("dico", ECRAN, '"en": "Deepotus dark"', '"en": "Deepotus sombre"'),
 ("dico", ECRAN, '  "apparence.verdict.ko"', '  "apparence.verdict.koX"'),
 # ── maillon, chaîne, page ──
 ("bundle", ECRAN, 'window.__dzApparence.monter(el)', 'window.__dzApparence.monter(el.parentNode)'),
 ("aide", ECRAN, "    bundle = avant_dzapparence(bundle)           # 30/10 (t382)", "    # 30/10 (t382)"),
 ("maillon", ECRAN, '    ("dzfils", "/*dzfils*/", 1),\n', ""),
 ("html", ECRAN, '    <script src="/shared/dz-apparence.js"></script>\n', ""),
]
QUE = {int(x) for x in os.environ.get("DZ_MUT", "").split(",") if x.strip()}   # DZ_MUT=9,13 : rejouer celles-là
if QUE:
    M = [m if i in QUE else None for i, m in enumerate(M, 1)]
tues = 0
try:
  for i, mut in enumerate(M, 1):
    if mut is None:
        continue
    k, banc, a, b = mut
    p = F[k]; s = p.read_bytes().decode("utf-8")
    if "\r\n" in s:
        a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    assert s.count(a) == 1, (i, a, s.count(a))
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    if k == "js":                                    # la copie de dist suit la source : la mutation vise le COMPORTEMENT
        shutil.copy2(p, F["jsd"])
    r = subprocess.run(banc, cwd=RACINE / "backend", capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
jouees = sum(1 for m in M if m is not None)
print(f"{tues}/{jouees} mutations tuées")
sys.exit(0 if tues == jouees else 1)
