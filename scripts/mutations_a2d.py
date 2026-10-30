# -*- coding: utf-8 -*-
"""Mutations t377 (30/10/2026) : les cartes de l'onglet Assets 2D illustrées et traduites (maillon
patch_bundle_dza2d, dictionnaire frontend/shared/i18n/a2d.json, illustrations frontend/dist/assets2d/cartes/).
Chaque mutation doit faire ÉCHOUER le banc backend/tests/test_assets2d_cartes_ecran.py. Les fichiers sont copiés AVANT,
restaurés après chaque mutation et comparés octet à octet à la fin (le bundle compris).
Run (depuis la racine) : & $PY scripts/mutations_a2d.py"""
import filecmp, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_a2d_"))
F = {"bundle": RACINE / "frontend/dist/assets/index-BEOJX8L5.js", "dico": RACINE / "frontend/shared/i18n/a2d.json",
     "dicojs": RACINE / "frontend/shared/dz-i18n-dico.js", "aide": RACINE / "backend/tests/_i18n_l1_aide.py",
     "maillon": RACINE / "scripts/patch_bundle_dza2d.py", "img": RACINE / "frontend/dist/assets2d/cartes/tiles.webp"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
BANC = [sys.executable, "backend/tests/test_assets2d_cartes_ecran.py"]
M = [
 # ── le bundle : un texte remis en dur, l'image perdue ou rendue gourmande ──
 ("bundle", 'children:/*dza2d*/dzT("a2d.outils.choisir")', 'children:/*dza2d*/"Choisir un outil"'),
 ("bundle", 'p:dzT("a2d.carte.pixel")', 'p:"Retouche au pixel : ligne de temps des cadres, tuile iso 2:1 et ses diagonales, rastériser une image générée."'),
 ("bundle", 'children:dzT("a2d.carte.ouvrir")}', 'children:"Ouvrir"}'),
 ("bundle", 'title:dzT("a2d.carte.ouvrir_titre",{outil:c.t})', 'title:"Ouvrir "+c.t'),
 ("bundle", '.webp",alt:"",loading:"lazy",', '.webp",alt:"",'),
 ("bundle", 'src:"/assets2d/cartes/"+c.id+".webp"', 'src:"/assets2d/cartes/"+c.id+".png"'),
 ("bundle", 'r.jsx("span",{style:{width:40,height:40,display:"flex"},dangerouslySetInnerHTML:{__html:__dzCatSVG[c.id]||""}},"s"),',
  ''),
 # ── le dictionnaire ──
 ("dico", '"en": "Choose a tool"', '"en": "Choisir un outil"'),
 ("dico", '"en": "Open {outil}"', '"en": "Open {tool}"'),
 ("dico", '"fr": "Ouvrir {outil}"', '"fr": "Ouvrir l\'outil {outil}"'),
 ("dico", '  "a2d.carte.guide_absent": {"fr": "Pas encore de chapitre « {outil} » dans le guide", "en": "No “{outil}” chapter in the guide yet"}\n',
  '  "a2d.carte.guide_absent": {"fr": "Pas encore de chapitre « {outil} » dans le guide", "en": "No “{outil}” chapter in the guide yet"},\n'
  '  "a2d.carte.orpheline": {"fr": "x", "en": "x"}\n'),
 # ── l'inverse et le maillon ──
 ("aide", "    bundle = avant_dza2d(bundle)                 # 30/10 (t377)", "    # 30/10 (t377)"),
 ("maillon", '    ("dzga3d", "/*dzga3d*/", 1),\n', ''),
 # ── l'illustration ──
 ("img", None, None),
]


def restaurer():
    for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)


tues = survivants = 0
try:
    for cle, avant, apres in M:
        p = F[cle]
        if cle == "img":
            from PIL import Image                                    # une vignette aux mauvaises dimensions
            with Image.open(SAUVE / "img.orig") as im:
                im.resize((320, 180)).save(p, "WEBP")
        else:
            b = p.read_bytes().decode("utf-8")
            lf = b.replace("\r\n", "\n")
            if lf.count(avant.replace("\r\n", "\n")) != 1:
                print(f"  ??    ancre x{lf.count(avant)} dans {cle} : {avant[:70]!r}"); survivants += 1; continue
            neuf = lf.replace(avant.replace("\r\n", "\n"), apres.replace("\r\n", "\n"), 1)
            if "\r\n" in b: neuf = neuf.replace("\n", "\r\n")
            p.write_bytes(neuf.encode("utf-8"))
        r = subprocess.run(BANC, cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            tues += 1; print(f"  TUÉ      {cle} : {str(avant)[:70]!r}")
        else:
            survivants += 1; print(f"  SURVIT   {cle} : {str(avant)[:70]!r}")
        restaurer()
finally:
    restaurer()
    egaux = all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
    print(f"\n{tues} tués / {survivants} survivants ; sources restaurées à l'octet : {egaux}")
    sys.exit(0 if survivants == 0 and egaux else 1)
