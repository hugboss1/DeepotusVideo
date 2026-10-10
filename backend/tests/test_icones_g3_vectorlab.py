# -*- coding: utf-8 -*-
"""Icônes G3 (10/10/2026) — le Vectorlab passe à la suite « Deepotus Glyph » (/shared/icons).

  [1] le runtime : index.html charge /shared/icons/dz-icons.css (avant vectorlab.css) et /shared/icons/dz-icons.js
      APRÈS /shared/dz-i18n.js et AVANT les modules du lab (js/core.js).
  [2] la liste de travail (docs/icones/suite-finale/implementation.json, entrées dont la source est frontend/vectorlab/) :
      288 sites à clé, chacun porte SA clé dans le fichier qui le pose ; le compte de chaque clé dans le périmètre (code,
      hors commentaires et bancs) est figé ci-dessous ; chaque clé posée existe dans la suite (lexique).
  [3] plus aucun ancien dessin : le sprite fin de mod-icones est remplacé par des clés dz-*, le sprite <svg> d'index.html
      (17 symboles #t-* jamais référencés + 4 #v-* du Vitrail) est retiré et plus rien ne le cite, aucun glyphe ni emoji
      remplacé ne reste en tête d'un contenu de bouton ou d'un libellé (les titres et les phrases restent du texte).
  [4] node --check de chaque module du Vectorlab ; le banc node qa/icones.test.mjs (dzi, repli, clés) passe.
Run : & $PY tests/test_icones_g3_vectorlab.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
VL = ROOT / "frontend" / "vectorlab"
DOCS = ROOT / "docs" / "icones" / "suite-finale"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:500]}")


def lire(p):
    return p.read_text(encoding="utf-8")


def sans_commentaires(s, css=False):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    if not css:
        s = re.sub(r"(?m)^\s*//.*$", "", s)                      # ligne de commentaire
        s = re.sub(r"(?<=[;,{}()\]])\s*//[^\n]*", "", s)          # commentaire de fin de ligne après du code
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return s


PERIMETRE = sorted(p for p in VL.rglob("*") if p.suffix in (".js", ".html", ".css")
                   and "vendor" not in p.parts and "qa" not in p.parts and "aide" not in p.parts)
# t146 (traduction L6) : les modules passent par T(clé) — le banc lit leur texte français d'avant la traduction
# (test_i18n_l6 garantit qu'elle se défait exactement)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402
CODE = {p: sans_commentaires(AIDE.source_avant_i18n_l6(lire(p), p.relative_to(VL).as_posix()) if p.suffix == ".js" else lire(p),
                             css=p.suffix == ".css") for p in PERIMETRE}
LEXIQUE = {x["cle"] for x in json.loads(lire(DOCS / "lexique.json"))}
CLE = re.compile(r"(?<![\w-])dz-[a-z0-9]+(?:-[a-z0-9]+)+")

# ── [1] runtime
print("[1] runtime de la suite chargé par la page")
h = lire(VL / "index.html")
i_css, i_vcss = h.find('href="/shared/icons/dz-icons.css"'), h.find('href="vectorlab.css"')
i18n, ico, core = h.find('src="/shared/dz-i18n.js"'), h.find('src="/shared/icons/dz-icons.js"'), h.find('src="js/core.js"')
check("1.1 dz-icons.css chargé, avant vectorlab.css", 0 <= i_css < i_vcss, (i_css, i_vcss))
check("1.2 dz-icons.js APRÈS dz-i18n.js et AVANT js/core.js", 0 <= i18n < ico < core, (i18n, ico, core))
check("1.3 un seul chargement du runtime", h.count("/shared/icons/dz-icons.js") == 1 and h.count("/shared/icons/dz-icons.css") == 1)

# ── [2] les sites de la liste
print("[2] chaque site de la liste porte sa clé")
impl = json.loads(lire(DOCS / "implementation.json"))
sites = [e for e in impl if e["source"].startswith("frontend/vectorlab/") and e["cle_finale"]]
textes = [e for e in impl if e["source"].startswith("frontend/vectorlab/") and not e["cle_finale"]]
check("2.1 la liste : 288 sites à clé, 82 en texte seul, aucun emoji conservé", len(sites) == 288 and len(textes) == 82
      and not any(e.get("emoji_conserve") for e in sites + textes), (len(sites), len(textes)))
# où la clé est posée quand ce n'est plus le fichier relevé : les chevrons CSS ::before des sections sont devenus
# l'icône posée par mod-panneaux ; les icônes de la colonne d'outils, de la barre contextuelle et des rangées
# d'objet vivent dans les tables de mod-icones
POSE = {"vectorlab.pile.section-ferme": ["js/mod-panneaux.js"], "vectorlab.pile.vitrail-ferme": ["js/mod-panneaux.js"],
        "vectorlab.pile.vitrail-ouvert": ["js/mod-panneaux.js"]}
manque = []
for e in sites:
    fichiers = POSE.get(e["id"]) or (["js/mod-icones.js"] if "mod-icones.js" in e["source"]
                                     else sorted(set(re.findall(r"frontend/vectorlab/([\w./-]+\.(?:js|html|css))", e["source"]))))
    if not any(e["cle_finale"] in CLE.findall(CODE[VL / f]) for f in fichiers if (VL / f) in CODE):
        manque.append((e["id"], e["cle_finale"], fichiers))
check("2.2 les 288 sites : la clé finale est posée dans le fichier du site (hors commentaires)", not manque, manque[:6])
COMPTES = {
    "dz-action-abandonner": 1, "dz-action-aide": 1, "dz-action-ajouter": 13, "dz-action-ajuster-vue": 1, "dz-action-aleatoire": 1,
    "dz-action-annuler": 2, "dz-action-choisir-bibliotheque": 1, "dz-action-coller": 1, "dz-action-deplier": 4, "dz-action-dupliquer": 3,
    "dz-action-element-precedent": 2, "dz-action-element-suivant": 2, "dz-action-enregistrer": 1, "dz-action-exporter": 1,
    "dz-action-fermer": 8, "dz-action-importer": 4, "dz-action-modifier": 1, "dz-action-nouveau": 1, "dz-action-raccourcis": 1,
    "dz-action-recalculer": 1, "dz-action-reglages": 1, "dz-action-reinitialiser": 3, "dz-action-renommer": 2, "dz-action-retablir": 1,
    "dz-action-supprimer": 10, "dz-action-telecharger": 1, "dz-action-valider": 1, "dz-action-vider": 2, "dz-action-zoom-arriere": 1,
    "dz-action-zoom-avant": 1, "dz-calque-ecretage": 2, "dz-calque-groupe": 1, "dz-calque-masque": 2, "dz-calque-nouveau": 2,
    "dz-calque-pixel": 1, "dz-calque-reglage": 1, "dz-calque-texte": 2, "dz-calque-vectoriel": 1, "dz-cat-cartes": 1, "dz-cat-sprites": 1,
    "dz-cat-tuiles": 1, "dz-edit-aimanter": 1, "dz-edit-aligner-bas": 3, "dz-edit-aligner-centre-h": 3, "dz-edit-aligner-centre-v": 3,
    "dz-edit-aligner-droite": 3, "dz-edit-aligner-gauche": 3, "dz-edit-aligner-haut": 3, "dz-edit-arriere-plan": 1,
    "dz-edit-convertir-en-cadre": 2, "dz-edit-convertir-en-chemin": 2, "dz-edit-couleur-contour": 1, "dz-edit-couleur-fond": 1,
    "dz-edit-courbes-niveau": 1, "dz-edit-degrade-conique": 2, "dz-edit-degrade-lineaire": 2, "dz-edit-degrade-radial": 2,
    "dz-edit-degrouper": 1, "dz-edit-descendre": 2, "dz-edit-detacher": 3, "dz-edit-distribuer-h": 1, "dz-edit-distribuer-v": 1,
    "dz-edit-division": 1, "dz-edit-effet": 4, "dz-edit-epaissir": 1, "dz-edit-grille": 2, "dz-edit-grille-hex": 2, "dz-edit-grouper": 2,
    "dz-edit-incliner": 1, "dz-edit-intersection": 1, "dz-edit-inverser-sens": 1, "dz-edit-miroir-h": 1, "dz-edit-miroir-v": 1,
    "dz-edit-monter": 2, "dz-edit-motif": 2, "dz-edit-pivot": 1, "dz-edit-premier-plan": 1, "dz-edit-sans-contour": 2, "dz-edit-sans-couleur": 4,
    "dz-edit-soustraire": 1, "dz-edit-symbole": 2, "dz-edit-texte-aligner-centre": 1, "dz-edit-texte-aligner-droite": 1,
    "dz-edit-texte-aligner-gauche": 1, "dz-edit-union": 1, "dz-edit-vectoriser": 3, "dz-etat-avertissement": 1, "dz-etat-enregistre": 3,
    "dz-etat-inconnu": 3, "dz-etat-libre": 2, "dz-etat-modifie": 1, "dz-etat-sans-apercu": 1, "dz-etat-verrouille": 3,
    "dz-etat-visible": 1, "dz-lab3d-impression-3d": 4, "dz-lab3d-relief": 1, "dz-media-fond-carte": 1, "dz-media-generer-image": 4,
    "dz-media-image": 2, "dz-media-lecture": 2, "dz-media-pause": 2, "dz-media-police": 1, "dz-nav-bible": 2, "dz-nav-bibliotheque": 1,
    "dz-nav-chapitres": 1, "dz-nav-documents": 1, "dz-nav-espace-pixel": 2, "dz-nav-espace-vecteur": 1, "dz-nav-reglages": 1,
    "dz-outil-photo-densite-moins": 1, "dz-outil-photo-densite-plus": 1, "dz-outil-photo-flou": 1, "dz-outil-photo-recadrer": 1,
    "dz-outil-photo-tampon": 1, "dz-outil-px-baguette": 1, "dz-outil-px-crayon": 1, "dz-outil-px-degrade": 1, "dz-outil-px-gomme": 1,
    "dz-outil-px-lasso": 1, "dz-outil-px-ligne": 1, "dz-outil-px-pinceau": 1, "dz-outil-px-pot": 1, "dz-outil-px-rectangle": 1,
    "dz-outil-px-selection": 1, "dz-outil-px-symetrie": 2, "dz-outil-vec-apparence": 1, "dz-outil-vec-cadre-texte": 1,
    "dz-outil-vec-coin": 1, "dz-outil-vec-constructeur": 1, "dz-outil-vec-couteau": 1, "dz-outil-vec-crayon": 1, "dz-outil-vec-donut": 1,
    "dz-outil-vec-ellipse": 2, "dz-outil-vec-engrenage": 1, "dz-outil-vec-etoile": 1, "dz-outil-vec-fermer-chemin": 1,
    "dz-outil-vec-fleche": 1, "dz-outil-vec-forme": 2, "dz-outil-vec-fractionner": 1, "dz-outil-vec-gomme": 1, "dz-outil-vec-halo": 1,
    "dz-outil-vec-hexagone": 1, "dz-outil-vec-iris": 1, "dz-outil-vec-ligne": 1, "dz-outil-vec-lisser": 1, "dz-outil-vec-loupe": 1,
    "dz-outil-vec-main": 1, "dz-outil-vec-mesure": 1, "dz-outil-vec-noeud": 1, "dz-outil-vec-noeud-intelligent": 1,
    "dz-outil-vec-noeud-lisse": 1, "dz-outil-vec-noeud-vif": 1, "dz-outil-vec-ouvrir-chemin": 1, "dz-outil-vec-pinceau": 1,
    "dz-outil-vec-pipette": 1, "dz-outil-vec-plan-de-travail": 1, "dz-outil-vec-plume": 1, "dz-outil-vec-polygone": 1,
    "dz-outil-vec-profil-calligraphie": 1, "dz-outil-vec-profil-fuseau": 1, "dz-outil-vec-profil-plat": 1, "dz-outil-vec-rayons": 1,
    "dz-outil-vec-rectangle": 2, "dz-outil-vec-relier": 1, "dz-outil-vec-selection": 1, "dz-outil-vec-spirale": 1,
    "dz-outil-vec-texte": 1, "dz-outil-vec-texte-sur-chemin": 2, "dz-outil-vec-tranche": 2, "dz-outil-vec-transparence": 3,
    "dz-outil-vec-tuiles": 2, "dz-outil-vec-vitrail-arc": 1, "dz-outil-vec-vitrail-grille": 1, "dz-outil-vec-vitrail-plomb": 1,
    "dz-outil-vec-vitrail-rosette": 1,
}
compte = {}
for s in CODE.values():
    for k in CLE.findall(s):
        if k in LEXIQUE:
            compte[k] = compte.get(k, 0) + 1
ecarts = {k: (compte.get(k, 0), COMPTES.get(k, 0)) for k in set(compte) | set(COMPTES) if compte.get(k, 0) != COMPTES.get(k, 0)}
check(f"2.3 compte par clé dans le périmètre = figé ({len(COMPTES)} clés)", not ecarts, sorted(ecarts.items())[:8])
check("2.4 chaque clé de la liste est comptée au moins une fois", {e["cle_finale"] for e in sites} <= set(compte),
      sorted({e["cle_finale"] for e in sites} - set(compte)))
inconnues = sorted({k for s in CODE.values() for k in CLE.findall(s)
                    if k.startswith(("dz-action-", "dz-edit-", "dz-outil-", "dz-etat-", "dz-calque-", "dz-media-", "dz-nav-",
                                     "dz-cat-", "dz-lab3d-")) and k not in LEXIQUE})
check("2.5 aucune clé inventée : toute clé posée existe dans la suite", not inconnues, inconnues)

ic0 = CODE[VL / "js/mod-icones.js"]
cd, pa = re.search(r'configDoc: "([^"]+)"', ic0), re.search(r'parametres: "([^"]+)"', ic0)
check("2.6 deux fonctions, deux icônes : Configuration du document = dz-action-reglages, Paramètres de l'appli = dz-nav-reglages",
      bool(cd and pa) and cd.group(1) == "dz-action-reglages" and pa.group(1) == "dz-nav-reglages", (cd and cd.group(1), pa and pa.group(1)))

fl, st = CODE[VL / "js/mod-flyout.js"], CODE[VL / "js/mod-style.js"]
sf = re.search(r'id: "sansfond"[^}]*icone: "([^"]+)"', fl); sc = re.search(r'id: "sanscontour"[^}]*icone: "([^"]+)"', fl)
bf = re.search(r'title="Sans fond"[^>]*>\$\{dzi\("([^"]+)"', st); bc = re.search(r'title="Sans contour"[^>]*>\$\{dzi\("([^"]+)"', st)
check("2.7 arbitrage : Sans fond = dz-edit-sans-couleur, Sans contour = dz-edit-sans-contour (menu Apparence et panneau), jamais la même clé",
      all((sf, sc, bf, bc)) and sf.group(1) == bf.group(1) == "dz-edit-sans-couleur" and sc.group(1) == bc.group(1) == "dz-edit-sans-contour",
      [m and m.group(1) for m in (sf, sc, bf, bc)])

# ── [3] plus aucun ancien dessin
print("[3] plus aucun ancien dessin")
ic = CODE[VL / "js/mod-icones.js"]
check("3.1 mod-icones : plus de fragment <path>/<rect>/<circle> maison ni de repli pointillé",
      not re.search(r"<(?:path|rect|circle|ellipse)\b", ic) and "stroke-dasharray" not in ic)
check("3.2 mod-icones : ICONES et RANGEES ne contiennent que des clés dz-*",
      all(re.fullmatch(r"dz-[a-z0-9-]+", v) for v in re.findall(r':\s*"([^"]*)"', ic.split("export const ICONES", 1)[1].split("export const cle_de", 1)[0])))
check("3.3 index.html : le sprite <svg> retiré (aucun <symbol>)", "<symbol" not in h)
cites = [str(p.relative_to(VL)) for p, s in CODE.items() if re.search(r'#(?:t|v)-[a-z]+["\'`]', s) or re.search(r'href="#(?:t|v)-', s)]
check("3.4 plus aucune référence aux symboles #t-* ni #v-*", not cites, cites)
anciens = set()
for e in sites:
    v = e["cle_visuelle"]
    if v.startswith(("glyphe ", "emoji ")):
        anciens.update(v.split(" ", 1)[1].split())
anciens -= {"?", "−", "×", "×n"}        # trop courants dans le code (ternaires, cotes) : contrôlés à part ci-dessous
alt = "|".join(re.escape(g) for g in sorted(anciens, key=len, reverse=True))
# un ancien glyphe en TÊTE d'un contenu de bouton (>✕) ou d'une chaîne (« "⇤ Aligner », « ⬆ Fichier… »)
tete = re.compile(r'(?:>|["\'`])[ \t]*(?:' + alt + r')(?=[\s<"\'`]|$)')
TOLERES = ["✎ Symbole «", "</vl-bascule> → swatches"]   # hors liste : en-tête d'édition de symbole, légende d'une bascule
restes = []
for p, s in CODE.items():
    for m in tete.finditer(s):
        ctx = s[max(0, m.start() - 30):m.end() + 20]
        if not any(t in s[max(0, m.start() - 20):m.end() + 20] for t in TOLERES):
            restes.append(f"{p.relative_to(VL)}: …{ctx}…")
check(f"3.5 aucun des {len(anciens)} glyphes / emojis remplacés en tête d'un bouton ou d'un libellé", not restes, restes[:6])
precis = {"js/mod-didact.js": ['textContent = "?"'], "js/mod-layers.js": ['">fx</button>'], "js/mod-style.js": [">×n<"],
          "js/mod-ia.js": [">×</button>"], "js/mod-vitrail.js": [">×</button>"], "js/mod-pile.js": [">−</button>", ">+</button>"],
          "js/mod-plateau.js": ["− surcharge", "⊞"], "index.html": [">?</button>"], "js/mod-pixelui.js": ["glyphe:"],
          "js/mod-flyout.js": ["glyphe:", "e.glyphe", "GLYPHES"], "js/core.js": ['"●"', '"✓"'],
          "vectorlab.css": ['content: "▸', 'content: "▾']}
vus = [(f, x) for f, xs in precis.items() for x in xs if x in CODE[VL / f]]
check("3.6 les anciens dessins ponctuels (?, fx, ×n, ×, −/+, ⊞, glyphe:, ●/✓, chevrons CSS) ont disparu", not vus, vus)

# ── [4] node
print("[4] node")
if not NODE:
    check("4.0 node disponible", False)
else:
    ko = []
    for p in sorted((VL / "js").glob("*.js")):
        r = subprocess.run([NODE, "--check", str(p)], capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            ko.append((p.name, r.stderr[-200:]))
    check("4.1 node --check de chaque module du Vectorlab", not ko, ko)
    r = subprocess.run([NODE, str(VL / "qa" / "icones.test.mjs")], capture_output=True, text=True, encoding="utf-8", cwd=str(VL))
    check("4.2 banc node qa/icones.test.mjs (dzi, repli dz-etat-inconnu, clés)", r.returncode == 0 and "PASS" in r.stdout, r.stdout[-300:] + r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
