# -*- coding: utf-8 -*-
"""Icônes G2 (10/10/2026) — la suite « Deepotus Glyph » posée dans le Card Forge (frontend/cardforge).

  [1] le runtime : /shared/icons/dz-icons.css et dz-icons.js chargés par index.html APRÈS dz-i18n.js et AVANT
      js/core.js ; le CORE publie CF.icone et dérive CF.chevronSVG de dz-action-deplier ; chaque pièce lit CF.icone
      gardé `typeof` (patron sanscore) et son `icon:` porte la clé de son entrée de rail.
  [2] la liste de travail (docs/icones/suite-finale/implementation.json, sources frontend/cardforge/*) : chaque site
      porte sa `cle_finale` ; compte EXACT de chaque clé par fichier (table CLES ci-dessous) ; chaque clé posée existe
      dans le sprite ; les chevrons dessinés en CSS (::before) passent par le masque --cf-chev-mask, dont le tracé est
      celui de dz-action-deplier.
  [3] plus aucun ancien glyphe/emoji remplacé dans les fichiers du périmètre (commentaires retirés) ; les glyphes
      qui restent sont des TEXTES nommés (RESTES).
  [4] node --check de chaque JS du périmètre.
Run : & $PY tests/test_icones_g2.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys, urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
CFD = ROOT / "frontend" / "cardforge"
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


def lire(rel):
    return (CFD / rel).read_text(encoding="utf-8")


def sans_commentaires(t, kind):
    """Retire les commentaires : /* */ (précédé d'un blanc, d'un début de ligne ou de ( ; , — jamais `image/*`),
    // en fin de ligne (précédé d'un blanc — jamais `http://`), <!-- --> en HTML."""
    if kind == "html":
        return re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"(?:(?<=[\s(;,])|^)/\*.*?\*/", "", t, flags=re.S | re.M)
    if kind == "js":
        t = re.sub(r"(?:(?<=\s)|^)//[^\n]*", "", t, flags=re.M)
    return t


MODS = ["face", "frame", "type", "data", "solid", "texture", "print", "gltf", "forge3d", "capture", "edition"]
RAIL = {"face": "dz-nav-cf-face", "frame": "dz-nav-cf-cadre", "type": "dz-nav-cf-typo", "data": "dz-nav-cf-donnees",
        "solid": "dz-nav-cf-volume", "texture": "dz-nav-cf-matieres", "print": "dz-nav-cf-impression",
        "gltf": "dz-nav-cf-export-3d", "forge3d": "dz-nav-cf-forge-3d", "capture": "dz-nav-cf-import",
        "edition": "dz-nav-cf-edition"}

# compte exact de chaque clé, par fichier (une clé écrite = un site, sauf les tables RAIL_ICO / PICTO / KIND_GLYPHE
# qui en posent une par entrée, et les paires d'état ajoutées au même site : visible/cache, verrouille/libre,
# succes/erreur, avertissement/erreur).
CLES = {
    "index.html": {"dz-action-ajuster-vue": 1, "dz-action-deplier": 2, "dz-action-element-precedent": 1,
                   "dz-action-element-suivant": 1, "dz-action-retour": 1, "dz-action-telecharger": 1,
                   "dz-action-theme": 1, "dz-action-zoom-arriere": 1, "dz-action-zoom-avant": 1, "dz-cat-cartes": 1,
                   "dz-edit-reperes": 1, "dz-nav-cf-galerie": 1},
    "js/core.js": {"dz-action-deplier": 1, "dz-action-dupliquer": 1, "dz-action-enregistrer-modele": 1,
                   "dz-action-fermer": 1, "dz-action-importer": 1, **{v: 1 for v in RAIL.values()}},
    "js/mod-capture.js": {"dz-action-detourer": 1, "dz-action-importer": 1, "dz-action-mesurer": 1,
                          "dz-nav-cf-forge-3d": 1, "dz-nav-cf-import": 1},
    "js/mod-data.js": {"dz-action-coller": 1, "dz-action-exporter": 2, "dz-action-nouveau": 1, "dz-action-quantite": 1,
                       "dz-action-supprimer": 4, "dz-action-trier": 1, "dz-edit-lier": 1, "dz-etat-avertissement": 1,
                       "dz-etat-erreur": 1, "dz-etat-exclu": 1, "dz-etat-succes": 1, "dz-media-fichier": 1, "dz-nav-cf-donnees": 1},
    "js/mod-edition.js": {"dz-action-envoyer-vers": 1, "dz-action-exporter": 2, "dz-nav-cf-edition": 1},
    "js/mod-face.js": {"dz-action-retirer": 1, "dz-action-supprimer": 1, "dz-action-telecharger": 1,
                       "dz-etat-sans-apercu": 1, "dz-media-generer-image": 1, "dz-nav-cf-face": 1},
    "js/mod-forge3d.js": {"dz-action-annuler": 2, "dz-action-exporter": 2, "dz-calque-pixel": 1,
                          "dz-edit-transformer": 1, "dz-etat-inconnu": 1, "dz-lab3d-artefact": 1,
                          "dz-lab3d-assemblage": 1, "dz-lab3d-extrusion": 1, "dz-lab3d-impression-3d": 1,
                          "dz-lab3d-maillage": 1, "dz-lab3d-materiau": 1, "dz-lab3d-plan": 1, "dz-lab3d-relief": 1,
                          "dz-nav-cf-forge-3d": 1},
    "js/mod-frame.js": {"dz-action-annuler": 2, "dz-action-deplier": 1, "dz-action-retablir": 1,
                        "dz-action-supprimer": 1, "dz-action-telecharger": 2, "dz-edit-descendre": 1,
                        "dz-edit-monter": 1, "dz-etat-erreur": 1, "dz-etat-succes": 6, "dz-media-generer-image": 1,
                        "dz-nav-cf-cadre": 1},
    "js/mod-gltf.js": {"dz-action-annuler": 2, "dz-action-telecharger": 1, "dz-nav-cf-export-3d": 1},
    "js/mod-print.js": {"dz-action-annuler": 1, "dz-action-telecharger": 2, "dz-edit-reperes": 2, "dz-etat-succes": 4,
                        "dz-nav-cf-impression": 1},
    "js/mod-solid.js": {"dz-action-ajuster-vue": 1, "dz-action-zoom-arriere": 1, "dz-action-zoom-avant": 1,
                        "dz-lab3d-filaire": 1, "dz-lab3d-hdri": 1, "dz-lab3d-rotation": 1, "dz-nav-cf-volume": 1},
    "js/mod-texture.js": {"dz-action-aleatoire": 1, "dz-action-annuler": 1, "dz-action-retablir": 1,
                          "dz-etat-avertissement": 2, "dz-lab3d-deriver-maps": 1, "dz-lab3d-lumiere": 1,
                          "dz-nav-cf-matieres": 1},
    "js/mod-type.js": {"dz-action-annuler": 1, "dz-action-disposition-colonne": 1, "dz-action-mesurer": 2,
                       "dz-action-retablir": 1, "dz-action-supprimer": 1, "dz-calque-pixel": 2, "dz-calque-texte": 2,
                       "dz-edit-aligner-bas": 2, "dz-edit-aligner-centre-h": 1, "dz-edit-aligner-centre-v": 2,
                       "dz-edit-aligner-droite": 1, "dz-edit-aligner-gauche": 1, "dz-edit-aligner-haut": 2,
                       "dz-edit-arriere-plan": 1, "dz-edit-cadres-edition": 1, "dz-edit-descendre": 2,
                       "dz-edit-distribuer-h": 1, "dz-edit-distribuer-v": 1, "dz-edit-inverser-sens": 1,
                       "dz-edit-justifier": 1, "dz-edit-meme-hauteur": 1, "dz-edit-meme-largeur": 1,
                       "dz-edit-monter": 2, "dz-edit-pointe-fleche": 4, "dz-edit-premier-plan": 1,
                       "dz-edit-texte-aligner-centre": 1, "dz-edit-texte-aligner-droite": 1,
                       "dz-edit-texte-aligner-gauche": 1, "dz-etat-attente": 4, "dz-etat-avertissement": 2,
                       "dz-etat-cache": 1, "dz-etat-erreur": 3, "dz-etat-information": 1, "dz-etat-libre": 1,
                       "dz-etat-selection-multiple": 1, "dz-etat-succes": 1, "dz-etat-verrouille": 3,
                       "dz-etat-visible": 1, "dz-nav-cf-typo": 1, "dz-outil-vec-ellipse": 1, "dz-outil-vec-fleche": 1,
                       "dz-outil-vec-ligne": 1, "dz-outil-vec-rectangle": 1},
}
CLE_RE = re.compile(r"(?<![\w-])dz-(?:nav|action|edit|etat|media|lab3d|calque|outil|cat)-[a-z0-9-]+")

# anciens glyphes et emojis remplacés : plus AUCUNE occurrence hors commentaires (table : fichier -> jetons)
ANCIENS = {
    "index.html": ["&#x1F0CF;", "&#9638;", "&#x25D0;", "&#8592;", "&#9635;", "&#8249;", "&#8250;", "&#8722;",
                   'd="M14.8 5.6 9 12l5.8 6.4z"'],
    "js/core.js": ["&#10005;", "RAIL_SVG", "SVG_O", 'd="M14.8 5.6 9 12l5.8 6.4z"', "\\u{1F"],
    "js/mod-capture.js": ["\\u{1F4E5}"],
    "js/mod-data.js": ["\\u{1F4CA}", "&times;", "&#128196;", "&#8693;", "✕", "⚠", "●", '"→ " + esc(slotLabel'],
    "js/mod-edition.js": ["\\u{1F4E6}"],
    "js/mod-face.js": ["\\u{1F3A8}", "◧", "✕", ">×<"],
    "js/mod-forge3d.js": ["⬢", "▤", "▭", "◧", "▢", "◍", "✥", "⧉", "◆", "⭳", '"○"', "↶", "'→ "],
    "js/mod-frame.js": ["\\u{1F5BC}", "↶", "↷", "&#8249;", 'bt("↑"', 'bt("↓"', 'bt("✕"', "✓", "✗"],
    "js/mod-gltf.js": ["\\u{1F4E6}", "↶"],
    "js/mod-print.js": ["\\u{1F5A8}", "&#9635;", "&#9634;", "&#8630;", "&#10003;"],
    "js/mod-solid.js": ["\\u{1F9CA}", "&#9638;", "&#8635;", "&minus;</button>", 'title="Zoom avant (molette)">+<'],
    "js/mod-texture.js": ["\\u{1F9F5}", "&#8630;", "&#8631;", "↻", "&#8635;", "⚠"],
    "js/mod-type.js": ["\\u{1F524}", "\\u{1F5BC}", "&#8630;", "&#8631;", "&#9635;", "&#9673;", "&#9636;", "&#9679;",
                       "&#9675;", "&#128274;", "&#128275;", "&#9650;", "&#10005;", "▬", "⬭", "╱", "&#8676;",
                       "&#8677;", "&#8607;", "&#8615;", "&#8801;", "&#8660;", "&#8661;", "&#9776;", "↗", "↘", "◀",
                       "▶", "&#9888;", "&#8987;", "&#9432;", "&#10003;", "&#9678;", ">+ Slot", ">+ Image"],
    "css/mod-face.css": ['content: "▸"', 'content: "▾"'],
    "css/mod-forge3d.css": ['content: "\\25B8"', 'content: "\\25BE"'],
    "css/mod-type.css": ['content: "\\25B8"', 'content: "\\25BE"'],
}
# glyphes encore présents, et pourquoi (texte seul selon implementation.json, ou indicateur d'état non relevé)
RESTES = {
    ("js/mod-data.js", "&#9660;"): "tri descendant actif (indicateur d'état, non relevé)",
    ("js/mod-data.js", "&#9650;"): "tri ascendant actif (indicateur d'état, non relevé)",
    ("js/mod-data.js", "▸ "): "menus de mappage colonne → slot : texte seul (mod-data.js:50)",
    ("js/mod-data.js", "&#9166;"): "retour à la ligne dans une cellule : texte seul (mod-data.js:2637)",
    ("js/mod-data.js", '"→ " + esc(cur)'): "mappage courant d'une case : texte (non relevé)",
    ("js/mod-solid.js", "&minus;</dt>"): "légende clavier de la visionneuse : texte",
    ("js/mod-print.js", "&#8212;"): "tiret « non vérifié » des tableaux de contrôle (texte)",
    ("js/mod-type.js", "&#9660;"): "aucun : doit avoir disparu",
}

print("[1] runtime")
html = lire("index.html")
i_dico, i_run = html.find('<script src="/shared/dz-i18n.js"></script>'), html.find('<script src="/shared/icons/dz-icons.js"></script>')
i_css, i_core = html.find('<link rel="stylesheet" href="/shared/icons/dz-icons.css">'), html.find('<script src="js/core.js"></script>')
check("1.1 index.html charge dz-icons.css et dz-icons.js une fois chacun",
      html.count("/shared/icons/dz-icons.css") == 1 and html.count("/shared/icons/dz-icons.js") == 1)
check("1.2 ordre : dz-i18n.js < dz-icons.js < js/core.js (et la feuille dans le <head>)",
      0 <= i_dico < i_run < i_core and 0 <= i_css < html.find("</head>"), (i_dico, i_run, i_core, i_css))
core = lire("js/core.js")
check("1.3 le CORE publie CF.icone, rendu par window.dzIcone avec repli à clé", "icone: icone," in core
      and 'typeof window.dzIcone === "function"' in core and 'data-cle="' in core)
check("1.4 CF.chevronSVG = dz-action-deplier tourné par .cf-chev",
      'const CHEVRON_SVG = icone("dz-action-deplier", 16, "cf-chev");' in core)
check("1.5 le rail lit RAIL_ICO, puis l'`icon:` du module s'il porte une clé",
      "railIcone(id, m)" in core and all(f'{m}: "{k}"' in core for m, k in RAIL.items()))
for m in MODS:
    t = lire(f"js/mod-{m}.js")
    check(f"1.6 mod-{m} : icon = {RAIL[m]} et ICO gardé `typeof CF.icone`",
          f'icon: "{RAIL[m]}",' in t and 'const ICO = (k, t, c) => (typeof CF.icone === "function"' in t)
css = lire("cardforge.css")
check("1.7 cardforge.css : écarts cf-ic/cf-ic-d, rotation .cf-chev, pointes de flèche orientées",
      ".cf-ic{" in css and ".cf-ic-d{" in css and ".cf-chev{ transform:rotate(90deg); }" in css
      and ".cf-fl-fin{" in css and ".cf-fl-deb{" in css)

print("[2] liste de travail")
impl = json.loads((DOCS / "implementation.json").read_text(encoding="utf-8"))
sites = [e for e in impl if e["source"].startswith("frontend/cardforge/") and e["cle_finale"]]
check("2.0 167 sites à poser dans le périmètre (image trouvée / introuvable scindées le 10/10)", len(sites) == 167, len(sites))
data_src = lire("js/mod-data.js")
check("2.0b image trouvée = dz-etat-succes, image INTROUVABLE = dz-etat-erreur",
      re.search(r'td\.classList\.add\("ok"\);\s*dot\.innerHTML = ICO\("dz-etat-succes", 16\);', data_src) is not None
      and re.search(r'td\.classList\.add\("miss"\);\s*dot\.innerHTML = ICO\("dz-etat-erreur", 16\);', data_src) is not None)
sprite = (ROOT / "frontend" / "shared" / "icons" / "dz-icons.svg").read_text(encoding="utf-8")
ids = set(re.findall(r'<symbol id="([^"]+)"', sprite))
absents = []
for e in sites:
    rel = e["source"].split(":")[0].replace("frontend/cardforge/", "")
    t = lire(rel)
    if rel.endswith(".css"):
        bon = e["cle_finale"] == "dz-action-deplier" and "var(--cf-chev-mask)" in t
    else:
        bon = e["cle_finale"] in t
    if not bon:
        absents.append((e["id"], rel, e["cle_finale"]))
check("2.1 chaque site de la liste porte sa clé_finale dans son fichier", not absents, absents)
for rel, att in CLES.items():
    vu = {}
    for k in CLE_RE.findall(sans_commentaires(lire(rel), "html" if rel.endswith(".html") else "js")):
        vu[k] = vu.get(k, 0) + 1
    check(f"2.2 {rel} : compte exact par clé ({sum(att.values())} poses)", vu == att,
          {k: (vu.get(k), att.get(k)) for k in set(vu) | set(att) if vu.get(k) != att.get(k)})
    inconnues = sorted(k for k in vu if k not in ids)
    check(f"2.3 {rel} : chaque clé posée existe dans le sprite", not inconnues, inconnues)
uses = re.findall(r'<use href="/shared/icons/dz-icons\.svg#([^"]+)"></use>', html)
check("2.4 index.html : chaque <use> vise un symbole du sprite, en aria-hidden",
      uses and all(u in ids for u in uses) and html.count('aria-hidden="true" focusable="false"><use') == len(uses), uses)
d = re.search(r'\sd="([^"]+)"', (DOCS / "svg" / "dz-action-deplier.svg").read_text(encoding="utf-8")).group(1)
m = re.search(r'--cf-chev-mask:url\("data:image/svg\+xml,([^"]+)"\)', css)
check("2.5 le masque --cf-chev-mask porte EXACTEMENT le tracé de dz-action-deplier",
      bool(m) and f"d='{d}'" in urllib.parse.unquote(m.group(1)), m and urllib.parse.unquote(m.group(1))[:120])
for rel, n in (("css/mod-face.css", 2), ("css/mod-forge3d.css", 2), ("css/mod-type.css", 4)):
    t = lire(rel)
    check(f"2.6 {rel} : le repli du <summary> passe par le masque (fermé -90°, ouvert droit)",
          t.count("var(--cf-chev-mask)") == n and "rotate(-90deg)" in t, t.count("var(--cf-chev-mask)"))

print("[3] anciens glyphes")
for rel, jetons in ANCIENS.items():
    kind = "html" if rel.endswith(".html") else ("css" if rel.endswith(".css") else "js")
    t = sans_commentaires(lire(rel), kind)
    restes = [j for j in jetons if j in t]
    check(f"3.1 {rel} : aucun ancien glyphe ({len(jetons)} jetons)", not restes, restes)
for (rel, j), pourquoi in RESTES.items():
    t = sans_commentaires(lire(rel), "js")
    if pourquoi.startswith("aucun"):
        check(f"3.2 {rel} : {j} a disparu", j not in t)
    else:
        check(f"3.2 {rel} : {j} reste — {pourquoi}", j in t)

print("[4] node --check")
if not NODE:
    check("4.0 node disponible", False)
else:
    for p in sorted((CFD / "js").glob("*.js")):
        r = subprocess.run([NODE, "--check", str(p)], capture_output=True, text=True, encoding="utf-8")
        check(f"4.1 node --check {p.name}", r.returncode == 0, r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
