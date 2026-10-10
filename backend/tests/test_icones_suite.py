# -*- coding: utf-8 -*-
"""Icônes G0 (10/10/2026) — la suite « Deepotus Glyph » servie à toute l'application.

  [1] la source : docs/icones/suite-finale/svg (une icône par fonction du lexique), chaque dessin conforme à la charte
      (docs/icones/generateurs/refonte/CHARTE.md, contrôlée par lint.py : viewBox 24, currentColor, deux tons .38/1,
      traits 2,6, aucune balise ni attribut actif).
  [2] les choix de l'utilisateur (docs/icones/choix-utilisateur.json, relus dans l'artifact de l'inventaire) : chaque
      clé choisie existe ; les trois préférences « actuel » sont appliquées (logo et splash en image, pointeur Lucide).
  [3] le générateur scripts/icones/construire_suite.py : --check vert (sorties à jour), sprite = un <symbol> par icône
      dessinée et ids uniques, frontend/shared/icons identique octet pour octet à la copie servie frontend/dist/shared/icons.
  [4] le runtime dz-icons.js EXÉCUTÉ sous node : dzIcone rend chaque clé (classe dzi, taille, aria-hidden sans titre,
      role=img + aria-label avec titre, échappement du titre), image pour les clés « image », chaîne vide et
      avertissement pour une clé inconnue.
Run : & $PY tests/test_icones_suite.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
DOCS = ROOT / "docs" / "icones"
SRC = ROOT / "frontend" / "shared" / "icons"
DIST = ROOT / "frontend" / "dist" / "shared" / "icons"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:400]}")


lexique = json.loads((DOCS / "suite-finale" / "lexique.json").read_text(encoding="utf-8"))
cles = {x["cle"] for x in lexique}
svgs = {p.stem for p in (DOCS / "suite-finale" / "svg").glob("dz-*.svg")}

print("[1] source")
check("1.1 une icône dessinée par clé du lexique (524)", svgs == cles and len(cles) == 524,
      sorted(cles ^ svgs)[:10])
r = subprocess.run([sys.executable, "-I", str(DOCS / "generateurs" / "refonte" / "lint.py"), str(DOCS / "suite-finale" / "svg")],
                   capture_output=True, text=True, encoding="utf-8")
check("1.2 lint de la charte : 0 erreur", r.returncode == 0 and '"en_erreur": 0' in r.stdout, r.stdout[-400:] + r.stderr[-200:])
sens = [x["sens"] for x in lexique]
check("1.3 un sens par clé, jamais deux fois le même", len(set(sens)) == len(sens))

print("[2] choix de l'utilisateur")
choix = json.loads((DOCS / "choix-utilisateur.json").read_text(encoding="utf-8"))
check("2.1 chaque clé choisie existe dans la suite", set(choix) <= cles, sorted(set(choix) - cles))
check("2.2 options valides", all(re.fullmatch(r"refonte|kit:dz-[a-z0-9-]+|actuel:.+", v["option"]) for v in choix.values()))
check("2.3 cinq préférences « actuel » (logo, icônes d application = logo, splash, pointeur Lucide)",
      {k for k, v in choix.items() if v["option"].startswith("actuel:")} == {"dz-marque-poulpe", "dz-marque-splash", "dz-outil-photo-doigt", "dz-marque-icone-app", "dz-marque-icone-adaptative"})

print("[3] générateur et copies")
r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "icones" / "construire_suite.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8")
check("3.1 construire_suite --check : sorties à jour", r.returncode == 0, r.stdout + r.stderr)
for nom in ("dz-icons.svg", "dz-icons.js", "dz-icons.css"):
    a, b = SRC / nom, DIST / nom
    check(f"3.2 {nom} : copie servie identique à la source",
          a.exists() and b.exists() and a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n"))
sprite = (SRC / "dz-icons.svg").read_text(encoding="utf-8")
ids = re.findall(r'<symbol id="([^"]+)"', sprite)
check("3.3 sprite : un symbole par icône dessinée (520 = 524 − logo, splash et icônes d application en image), ids uniques",
      len(ids) == 520 and len(set(ids)) == 520 and set(ids) == cles - {"dz-marque-poulpe", "dz-marque-splash", "dz-marque-icone-app", "dz-marque-icone-adaptative"}, len(ids))
css = (SRC / "dz-icons.css").read_text(encoding="utf-8")
check("3.5 css : le remplissage currentColor épargne les icônes au trait (fill=none, pointeur Lucide)",
      'svg.dzi:not([fill="none"]){fill:currentColor}' in css and "svg.dzi{fill" not in css)
check("3.4 sprite sans script ni gestionnaire", "<script" not in sprite.lower() and not re.search(r"\son\w+=", sprite))

print("[4] runtime dz-icons.js sous node")
if not NODE:
    check("4.0 node disponible", False)
else:
    prog = r"""
global.window = {console: {warn: (m) => { window.__warn = m; }}};
require(process.argv[1]);
const w = window, out = {};
out.n = Object.keys(w.DZ_ICONS).length;
out.img = w.DZ_ICONS_IMAGES;
out.toutes = Object.keys(w.DZ_ICONS).every(k => { const h = w.dzIcone(k, {taille: 18});
  return h.startsWith('<svg class="dzi" width="18" height="18" aria-hidden="true" focusable="false"') && (h.match(/ width="/g) || []).length === 1; });
out.titre = w.dzIcone("dz-action-fermer", {titre: 'Fermer <"x">'});
out.classe = w.dzIcone("dz-action-fermer", {classe: "dzi--24"});
out.image = w.dzIcone("dz-marque-poulpe", {taille: 24, titre: "Deepotus"});
out.inconnue = w.dzIcone("dz-nexiste-pas");
out.warn = w.__warn;
console.log(JSON.stringify(out));
"""
    r = subprocess.run([NODE, "-e", prog, str(SRC / "dz-icons.js")], capture_output=True, text=True, encoding="utf-8")
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {}
    check("4.1 520 dessins et 4 images", o.get("n") == 520 and set((o.get("img") or {})) == {"dz-marque-poulpe", "dz-marque-splash", "dz-marque-icone-app", "dz-marque-icone-adaptative"}, r.stderr[-300:])
    check("4.2 chaque clé se rend (classe dzi, taille posée une fois, décorative par défaut)", o.get("toutes") is True)
    check("4.3 avec titre : role=img et aria-label échappé",
          'role="img" aria-label="Fermer &lt;&quot;x&quot;&gt;"' in (o.get("titre") or "") and "aria-hidden" not in (o.get("titre") or ""))
    check("4.4 classe additionnelle", (o.get("classe") or "").startswith('<svg class="dzi dzi--24"'))
    check("4.5 clé « image » : balise img vers le logo, alt = titre",
          o.get("image") == '<img class="dzi" src="/api/branding/logo" width="24" height="24" alt="Deepotus">')
    check("4.6 clé inconnue : chaîne vide et avertissement", o.get("inconnue") == "" and "dz-nexiste-pas" in (o.get("warn") or ""))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
