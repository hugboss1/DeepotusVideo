# -*- coding: utf-8 -*-
"""Harmonisation typo et bords, écran par écran (t374, 29/10/2026) — lot A « Finitions esthétiques ».
Sections :
  [G] `frontend/shared/dz-bords.css` est la sortie EXACTE de scripts/charte_bords.py (feuille générée, à jour) et
      sa copie de dist est identique ;
  [L] la coque la lie EN DERNIER (après dz-charte et dz-curseur), une seule fois ;
  [A] chaque règle de la coque qui écrit un rayon littéral > 0 est couverte par son sélecteur ; aucun rond assumé
      (disque carré, 50 %, pilule) n'est visé ;
  [B] chaque rayon en ligne de React du bundle est couvert par un sélecteur d'attribut, et seulement ceux-là ;
  [F] finitions : sélecteur de modèle sur une ligne, coin d'ascenseur, gris Tailwind sur --fg-*, aucun rayon ni
      couleur en dur ;
  [P] labs : plus aucun rayon littéral à aplatir (scripts/charte_aplatir_rayons.py --check), cliquet des labs à 0,
      échelles de texte parallèles du Vectorlab (--aff-texte, --aff-muet) rebranchées sur --fg-*.
Run (depuis backend/) : & $PY tests/test_charte_bords.py"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

import charte_bords  # noqa: E402
import charte_releve  # noqa: E402
import charte_aplatir_rayons  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


FEUILLE = RACINE / "frontend" / "shared" / "dz-bords.css"
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-bords.css"
INDEX = RACINE / "frontend" / "dist" / "index.html"


def _css(p):
    return re.sub(r"/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)


def _regles(css):
    """{sélecteur: corps} pour chaque règle de premier niveau."""
    res = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        for s in m.group(1).split(","):
            res.setdefault(s.strip(), []).append(m.group(2))
    return res


print("[G] feuille générée")
attendu = charte_bords.generer()
check("G1 dz-bords.css existe", FEUILLE.is_file())
check("G2 dz-bords.css = sortie de charte_bords.py", FEUILLE.is_file() and FEUILLE.read_text(encoding="utf-8") == attendu)
check("G3 copie dist identique", COPIE.is_file() and COPIE.read_bytes() == FEUILLE.read_bytes())

print("[L] liée en dernier par la coque")
html = INDEX.read_text(encoding="utf-8")
liens = re.findall(r'<link rel="stylesheet"[^>]*href="([^"]+)"', html)
check("L1 un seul lien /shared/dz-bords.css", liens.count("/shared/dz-bords.css") == 1, liens)
check("L2 c'est la DERNIÈRE feuille de la page", liens and liens[-1] == "/shared/dz-bords.css", liens[-3:])
check("L3 après dz-charte et dz-curseur",
      all(x in liens and liens.index(x) < liens.index("/shared/dz-bords.css")
          for x in ("/shared/dz-charte.css", "/shared/dz-curseur.css")) if "/shared/dz-bords.css" in liens else False)

css = _css(FEUILLE) if FEUILLE.is_file() else ""
R = _regles(css)
plat = {s for s, corps in R.items() if any("border-radius:var(--radius)!important" in c for c in corps)}

print("[A] règles de la coque")
couverts = manquants = 0
ronds, litteraux, sels_js = set(), set(), set()
for p in charte_releve.fichiers_zone("coque") + charte_bords.scripts_partages():
    if p.name == "dz-bords.css":
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    sels = charte_bords.selecteurs_css(t, js=p.suffix == ".js", html=p.suffix == ".html")
    if p.suffix == ".js":
        sels_js |= sels
    for s in sels:
        if s in plat:
            couverts += 1
        else:
            manquants += 1
    # ronds assumés : un sélecteur qui n'écrit QUE des ronds, dans TOUTES les feuilles de la coque, ne doit pas être aplati
    if p.suffix == ".css":
        for s, corps in _regles(re.sub(r"/\*.*?\*/", "", t, flags=re.S)).items():
            vals = [charte_releve._normal(v) for c in corps
                    for v in re.findall(r"(?<![\w-])border(?:-[a-z]+)*-radius\s*:\s*([^;}]+)", c)]
            if vals:
                (litteraux if any(charte_releve.rayon_compte(v) for v in vals) else ronds).add(s.strip())
ronds_vises = sorted((ronds - litteraux - sels_js) & plat)
check(f"A1 sélecteurs à rayon littéral couverts ({couverts})", couverts > 150 and manquants == 0, manquants)
check("A2 aucun sélecteur aux seuls ronds assumés (50 %, pilule, var(--r-pill)) n'est aplati",
      not ronds_vises, ronds_vises[:5])
check("A3 un disque carré reste rond (règle width = height, rayon ≥ moitié)",
      charte_bords.selecteurs_css(".rond{width:14px;height:14px;border-radius:7px}", js=False) == set()
      and charte_bords.selecteurs_css(".carre{width:14px;height:20px;border-radius:7px}", js=False) == {".carre"})
check("A4 rien de générique : ni *, ni :focus-visible seul, ni html/body",
      not any(s in plat for s in ("*", "html", "body")) and not any(s.endswith(" :focus-visible") for s in plat))
check("A6 sélecteurs propres : ni code JS (guillemet, = ou ; hors [attribut]), une règle par sélecteur",
      plat and all(not re.search(r"[=\"';]", re.sub(r"\[[^\]]*\]", "", x)) for x in plat)
      and css.count("{border-radius:var(--radius)!important}") >= len(plat) - 30)
check("A7 page : le CSS d'un <script> d'index.html est lu dans ses chaînes, pas son code",
      charte_bords.selecteurs_css("<script>st.textContent='.dz-tip{border-radius:6px}';</script>", html=True)
      == {".dz-tip"})
check("A5 les étapes d'@keyframes ne sont pas des sélecteurs",
      not any(re.fullmatch(r"(from|to|\d+%)", s) for s in plat))

print("[B] rayons en ligne de React")
bundle = next((RACINE / "frontend" / "dist" / "assets").glob("index-*.js")).read_text(encoding="utf-8", errors="replace")
vals = charte_bords.valeurs_en_ligne(bundle)
attrs = set(re.findall(r'\[style\*="border-radius: ([^"]+)"\]', css))
check(f"B1 chaque valeur en ligne du bundle est couverte ({len(vals)})", vals and vals <= attrs, sorted(vals - attrs))
check("B2 aucune valeur ronde visée (50 %, 999px, var(--r-pill))",
      not any(v in attrs for v in ("50%", "999px", "99px", "var(--r-pill)")) and all(
          charte_releve.rayon_compte(v) for v in attrs))
check("B3 sérialisation du navigateur : « 3px 0 0 3px » devient « 3px 0px 0px 3px »",
      charte_bords._serialise("3px 0 0 3px") == "3px 0px 0px 3px")
check("B4 nombre nu de React = px", charte_bords.valeurs_en_ligne('x={borderRadius:6}') == {"6px"})
check("B5 un 0 de React n'est pas visé", charte_bords.valeurs_en_ligne('x={borderRadius:0}') == set())
check("B6 Tailwind rounded* aplatis, rounded-full laissé",
      ".rounded-lg" in plat and ".rounded" in plat and ".rounded-full" not in plat)

print("[F] finitions")
check("F1 sélecteur de modèle : libellé sur une ligne, points de suspension",
      any("white-space:nowrap" in c and "text-overflow:ellipsis" in c
          for c in R.get("button[data-dzselect]>span:first-child", [])))
check("F2 coin d'ascenseur transparent",
      any("background:transparent" in c for c in R.get("::-webkit-scrollbar-corner", [])))
check("F3 gris Tailwind sur les encres de la charte",
      all(any(f"color:var(--fg-{n})" in c for c in R.get(s, [])) for s, n in
          ((".text-slate-100", 1), (".text-slate-300", 2), (".text-slate-400", 3), (".text-slate-600", 4))))
check("F4 aucune couleur en dur ni rayon littéral dans la feuille",
      not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", css)
      and not any(charte_releve.rayon_compte(charte_releve._normal(v))
                  for v in re.findall(r'(?<![\w"-])border-radius\s*:\s*([^;}]+)', css)))
check("F5 .text-white n'est pas repeint (texte sur aplat coloré)", ".text-white" not in R)

print("[P] labs")
reste = {}
for p in charte_aplatir_rayons.fichiers(list(charte_releve.LABS)):
    _neuf, n = charte_aplatir_rayons.aplatir(p.read_text(encoding="utf-8"))
    if n:
        reste[p.name] = n
check("P1 aucun rayon littéral à aplatir dans les feuilles des labs et de /shared", not reste, reste)
plaf = json.loads((RACINE / "scripts" / "charte_rayons_plafond.json").read_text(encoding="utf-8"))
mes = charte_releve.rayons_par_zone()
# studio3d.js est GÉNÉRÉ (L9) : son rayon est passé par la saisie scripts/i18n_l9/t374.py. /shared garde les seuls
# rayons des scripts FIGÉS de « Demander » (test_tutoriels_ecran P3), aplatis dans la page par dz-bords.css
figes = sum(n for f in charte_aplatir_rayons.FIGES
            for v, n in charte_releve.extraire((RACINE / "frontend" / "shared" / f).read_text(encoding="utf-8"))
            ["border-radius"].items() if charte_releve.rayon_compte(v))
check(f"P2 cliquet : labs à 0, /shared = les {figes} rayons des scripts figés",
      all(plaf[z] == 0 for z in charte_releve.LABS if z != "shared") and plaf["shared"] == figes == mes["shared"],
      {z: plaf[z] for z in charte_releve.LABS})
sels_figes = set().union(*(charte_bords.selecteurs_css((RACINE / "frontend" / "dist" / "shared" / f)
                                                       .read_text(encoding="utf-8"), js=True)
                           for f in charte_aplatir_rayons.FIGES))
check(f"P2b les règles à rayon des scripts figés sont aplaties par dz-bords ({len(sels_figes)})",
      sels_figes and sels_figes <= plat, sorted(sels_figes - plat)[:5])
check("P3 mesure ≤ plafond partout", all(mes[z] <= plaf[z] for z in mes), {z: (mes[z], plaf[z]) for z in mes if mes[z] > plaf[z]})
check("P4 un rond de lab reste rond : disque carré → 50 %",
      charte_aplatir_rayons.aplatir(".p{width:12px;height:12px;border-radius:6px}")[0]
      == ".p{width:12px;height:12px;border-radius:50%}")
check("P5 un rayon de lab devient var(--r)",
      charte_aplatir_rayons.aplatir(".b{border-radius:4px 4px 0 0;padding:2px}")[0]
      == ".b{border-radius:var(--r);padding:2px}")
vl = _css(RACINE / "frontend" / "vectorlab" / "vectorlab.css")
dernier_root = vl[vl.rfind(":root"):]
check("P6 Vectorlab : --aff-texte et --aff-muet rebranchés sur --fg-2 / --fg-3 (dernier :root)",
      "--aff-texte: var(--fg-2)" in dernier_root and "--aff-muet: var(--fg-3)" in dernier_root)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "charte_bords.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("P7 charte_bords.py --check sort en 0", r.returncode == 0, r.stdout[-200:])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)

