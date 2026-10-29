# -*- coding: utf-8 -*-
"""t372 (29/10/2026, lot A « Finitions esthétiques ») — banc des LECTEURS audio/vidéo à la charte
(frontend/shared/dz-lecteur.js, plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md).
  1. le script partagé : copie octet pour octet, aucun innerHTML, aucun texte visible en dur (tout passe par T(…)) ;
  2. la feuille injectée : fond --bg-panel, lecture --amber, temps --font-mono, marges --pad-*, angles var(--radius),
     AUCUN rayon littéral ni couleur en dur ;
  3. les branchements : la coque (après le runtime dz-i18n) et CHAQUE page de lab dont les sources posent un lecteur
     natif (relevé ci-dessous) chargent /shared/dz-lecteur.js avant leur propre script ;
  4. le relevé du bundle : 16 lecteurs natifs (8 audio, 8 vidéo), aucun maillon — tous passent par l'observateur de la
     coque ; le bundle n'est pas modifié par t372 ;
  5. les textes : chaque clé lecteur.* lue par le script existe en FR et en EN, assemblée (i18n_assembler --check) ;
  6. le comportement : frontend/shared/qa/lecteur.test.mjs (DOM simulé) passe.
Run (depuis backend/) : & $PY tests/test_lecteur_ecran.py"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


SRC = REPO / "frontend" / "shared" / "dz-lecteur.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-lecteur.js"
js = SRC.read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-lecteur.js"></script>'

print("[1] le script partagé")
check("1.1 copie identique dans frontend/dist/shared", DIST.exists() and DIST.read_bytes() == SRC.read_bytes())
check("1.2 aucun innerHTML", ".innerHTML" not in js and "insertAdjacentHTML" not in js)
check("1.3 script classique (pas de module) : chargeable tel quel par les labs", not re.search(r"^\s*(import|export)\s", js, re.M))
_litteraux = re.findall(r'(?:textContent\s*=|"aria-label"\s*:|title\s*:)\s*"([^"]*[A-Za-zÀ-ÿ][^"]*)"', js)
check("1.4 aucun libellé visible en dur (textContent, aria-label, title passent par T)", not _litteraux, _litteraux)
check("1.5 un média « natif » garde ses contrôles, seuls audio[controls] / video[controls] sont visés",
      'data-dz-lecteur") === "natif"' in js and 'var SELECTEUR = "audio[controls],video[controls]";' in js)
check("1.6 le média n'est jamais déplacé : la barre se pose après lui (insertBefore … nextSibling)",
      "parent.insertBefore(barre, media.nextSibling)" in js and ".appendChild(media)" not in js)

print("\n[2] la feuille injectée")
m = re.search(r"var CSS = \[(.*?)\]\.join\(\"\"\);", js, re.S)
css = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))) if m else ""
check("2.1 la feuille est trouvée", len(css) > 500, len(css))
check("2.2 fond --bg-panel, lecture --amber, temps --font-mono, marges --pad-*, encres --fg-*",
      "background:var(--bg-panel)" in css and "background:var(--amber)" in css and "font-family:var(--font-mono)" in css
      and re.search(r"var\(--pad-[1-4]\)", css) and "var(--fg-1)" in css and "var(--fg-3)" in css)
_rayons = re.findall(r"border-radius:([^;}]*)", css)
check("2.3 chaque rayon vaut var(--radius) (angles vifs, aucun rayon littéral)", _rayons and all(r == "var(--radius)" for r in _rayons), _rayons)
check("2.4 aucune couleur en dur (#hex, rgb, hsl)", not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", css))
check("2.5 tailles de texte aux paliers de la charte", re.findall(r"font-size:([^;}]*)", css) and
      all(v.startswith("var(--fs-") for v in re.findall(r"font-size:([^;}]*)", css)))
# t373 (29/10/2026) : le fader D1 est désormais LA règle commune /shared/dz-curseur.css (banc test_curseur_ecran) ;
# le lecteur ne dessine plus ses curseurs, il ne leur donne que leur place dans la barre
check("2.6 progression et volume : dessinés par la règle commune (aucun pouce ni piste ici), placés en flex",
      "slider" not in css and "--dz-lecteur-pos" not in js and ".dz-lecteur input[type=range]{flex:1 1 auto" in css)

print("\n[3] les branchements")
coque = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
check("3.1 la coque charge le lecteur une fois, après le runtime dz-i18n",
      coque.count(BALISE) == 1 and coque.index('<script src="/shared/dz-i18n.js"></script>') < coque.index(BALISE))
# relevé des labs : une page de lab dont les sources posent un lecteur natif doit charger dz-lecteur
NATIF = re.compile(r"<(audio|video)\b[^>]*\bcontrols\b|\bcontrols\s*:\s*(true|!0)|\.controls\s*=\s*(true|!0)")
porteurs = {}
for lab in sorted(p for p in (REPO / "frontend").iterdir() if p.is_dir() and p.name not in ("dist", "shared", "src", "patches", "node_modules")):
    for f in lab.rglob("*"):
        if f.suffix not in (".js", ".html", ".mjs") or any(x in f.parts for x in ("vendor", "qa", "node_modules")) or ".min." in f.name:
            continue
        if NATIF.search(f.read_text(encoding="utf-8", errors="replace")):
            porteurs.setdefault(lab.name, []).append(f.name)
check("3.2 relevé des labs : l'Atelier et l'Avatar live posent des lecteurs natifs", set(porteurs) == {"atelier", "avatar"}, porteurs)
for lab in sorted(porteurs):
    page = (REPO / "frontend" / lab / "index.html").read_text(encoding="utf-8")
    propre = {"atelier": '<script src="atelier.js"></script>', "avatar": '<script src="avatar.js"></script>'}[lab]
    check(f"3.3 {lab} : dz-lecteur chargé une fois, après dz-i18n, avant {propre}",
          page.count(BALISE) == 1 and page.index('<script src="/shared/dz-i18n.js"></script>') < page.index(BALISE) < page.index(propre))
partages = [f.name for f in (REPO / "frontend" / "shared").glob("*.js") if f.name != "dz-lecteur.js"
            and NATIF.search(f.read_text(encoding="utf-8", errors="replace"))]
check("3.4 /shared : seuls les tutoriels posent un lecteur natif, et ils vivent dans la coque",
      partages == ["dz-tutoriels.js"] and '<script type="module" src="/shared/dz-tutoriels.js"></script>' in coque, partages)

print("\n[4] le relevé du bundle")
B = next((REPO / "frontend" / "dist" / "assets").glob("index-*.js"))
bundle = B.read_text(encoding="utf-8")
natifs = re.findall(r'r\.jsx\("(audio|video)",\{[^}]*?controls:!0', bundle)
check("4.1 16 lecteurs natifs relevés (8 audio, 8 vidéo) : tous couverts par l'observateur de la coque",
      len(natifs) == 16 and natifs.count("audio") == 8 and natifs.count("video") == 8, (len(natifs), natifs.count("audio")))
check("4.2 aucun data-dz-lecteur=\"natif\" dans le bundle (aucun lecteur n'échappe à la charte)", 'data-dz-lecteur":"natif"' not in bundle)
check("4.3 t372 ne touche pas le bundle (aucun maillon dzlecteur, aucune marque data-dz-lecteur)", "data-dz-lecteur" not in bundle
      and not (REPO / "scripts" / "patch_bundle_dzlecteur.py").exists())

print("\n[5] les textes")
dico = {}
for f in (REPO / "frontend" / "shared" / "i18n").glob("*.json"):
    dico.update(json.loads(f.read_text("utf-8")))
cles = sorted(set(re.findall(r'"(lecteur\.[a-z_]+\.[a-z_]+)"', js)))
check("5.1 le script lit au moins 9 clés lecteur.*", len(cles) >= 9, cles)
manque = [k for k in cles if not (dico.get(k, {}).get("fr") and dico.get(k, {}).get("en"))]
check("5.2 chaque clé existe en FR et en EN", not manque, manque)
check("5.3 la valeur parlée garde {t} et {d} dans les deux langues",
      all("{t}" in dico["lecteur.curseur.position_valeur"][l] and "{d}" in dico["lecteur.curseur.position_valeur"][l] for l in ("fr", "en")))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
check("5.4 dictionnaire assemblé à jour", r.returncode == 0, ((r.stdout or "") + (r.stderr or ""))[-300:])

print("\n[6] le comportement (DOM simulé)")
r = subprocess.run(["node", str(REPO / "frontend" / "shared" / "qa" / "lecteur.test.mjs")], capture_output=True, text=True, encoding="utf-8")
check("6.1 frontend/shared/qa/lecteur.test.mjs passe", r.returncode == 0 and "OK " in r.stdout, (r.stdout + r.stderr)[-500:])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
