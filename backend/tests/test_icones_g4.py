# -*- coding: utf-8 -*-
"""Icônes G4 (10/10/2026) — le Photolab passe à la suite « Deepotus Glyph ».

Avant : les modules du Photolab chargeaient les SVG Lucide de l'amont (frontend/photolab/icones/*.svg, fetch par
PL.icone) et dessinaient des glyphes (✓ ⊘ ⛓ Δ ⫷ ≡ ☰ ▸ ▾ ⚠ × • fx TT Tt ↕T ⇄ ◧). Décision de l'utilisateur : la suite
remplace les icônes de l'amont, SAUF l'outil Doigt (pointeur Lucide, exposé par la suite sous dz-outil-photo-doigt).

  [1] runtime : index.html charge /shared/icons/dz-icons.css et dz-icons.js APRÈS /shared/dz-i18n.js et AVANT les
      modules du lab ; PL.icone (core.js) rend dzIcone, plus aucun fetch de icones/.
  [2] les sites de docs/icones/suite-finale/implementation.json dont la source est sous frontend/photolab/ (289 clés) :
      chaque clé existe dans la suite ; chaque site porte sa clé (présente dans son fichier source, ou dans la table
      exécutée qui le sert) ; compte de chaque clé par fichier = table figée ci-dessous.
  [3] tables EXÉCUTÉES sous node (outils, flyouts, verrous, 16 kinds × 4 emplacements, modes de sélection, alignements,
      compositions) confrontées au relevé : multiensembles de clés identiques.
  [4] plus aucun ancien dessin : aucun SVG dans frontend/photolab/icones/ (la licence Lucide reste, pour le Doigt),
      aucun nom Lucide passé comme icône, aucun des glyphes remplacés dans le code ; ATTRIBUTION.md à jour.
  [5] node --check de chaque module du Photolab et du lien QA vers la suite.
Run : & $PY tests/test_icones_g4.py   (depuis backend/)
"""
import collections, json, pathlib, re, shutil, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
PL = ROOT / "frontend" / "photolab"
SUITE_JS = ROOT / "frontend" / "shared" / "icons" / "dz-icons.js"
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


def lire(rel):
    return (PL / rel).read_text(encoding="utf-8")


def code(t):
    """Le code sans les lignes de commentaire (//, /* *, <!-- -->) ni les commentaires de fin de ligne « // … »."""
    out = []
    for l in t.splitlines():
        s = l.strip()
        if s.startswith(("//", "/*", "*", "<!--")):
            continue
        out.append(re.sub(r"\s//\s.*$", "", l))
    return "\n".join(out)


SUITE = SUITE_JS.read_text(encoding="utf-8")
CLES = set(re.findall(r'^"(dz-[a-z0-9-]+)": "', SUITE, re.M))
RELEVE = [e for e in json.loads((ROOT / "docs" / "icones" / "suite-finale" / "implementation.json").read_text(encoding="utf-8"))
          if str(e.get("source", "")).startswith("frontend/photolab/")]
SITES = [e for e in RELEVE if e.get("cle_finale")]
FICHIERS = sorted({e["source"].split(":")[0][len("frontend/photolab/"):] for e in SITES})

# Compte de chaque clé par fichier (code seul), relevé après la pose G4. Les tables (outils, kinds, verrous, alignements)
# servent plusieurs emplacements : [3] les confronte au relevé.
ATTENDU = {
    "index.html": {"dz-action-choisir-bibliotheque": 1, "dz-action-nouveau": 1, "dz-nav-panneau-ajustements": 1,
                   "dz-nav-panneau-calques": 1, "dz-nav-panneau-couleur": 1, "dz-nav-panneau-historique": 1,
                   "dz-nav-panneau-infos": 1, "dz-nav-panneau-navigateur": 1, "dz-nav-panneau-pinceaux": 1, "dz-nav-panneau-texte": 1},
    "js/mod-calques.js": {"dz-action-deplier": 2, "dz-action-dupliquer": 1, "dz-action-nouveau-dossier": 1, "dz-action-reglages": 1, "dz-action-supprimer": 2,
                          "dz-calque-fusionner": 1, "dz-calque-groupe": 1, "dz-calque-masque": 1, "dz-calque-nouveau": 1,
                          "dz-calque-objet-dynamique": 1, "dz-calque-reglage": 1, "dz-edit-effet": 2,
                          "dz-edit-lier": 3, "dz-etat-cache": 3, "dz-etat-verrou-pixels": 1, "dz-etat-verrou-plan-travail": 1,
                          "dz-etat-verrou-position": 1, "dz-etat-verrou-transparence": 1, "dz-etat-verrouille": 2, "dz-etat-visible": 3},
    "js/mod-compositions.js": {"dz-action-ajouter": 1, "dz-action-element-precedent": 1, "dz-action-element-suivant": 1,
                               "dz-action-redefinir": 1, "dz-action-supprimer": 1, "dz-edit-effet": 1, "dz-etat-avertissement": 1,
                               "dz-etat-visible": 1, "dz-edit-position": 1},
    "js/mod-couches.js": {"dz-action-ajouter": 1, "dz-action-supprimer": 1, "dz-edit-charger-selection": 1,
                          "dz-edit-enregistrer-selection": 1, "dz-etat-cache": 1, "dz-etat-visible": 1},
    "js/mod-couleur.js": {"dz-edit-couleurs-defaut": 1, "dz-edit-echanger-couleurs": 1},
    "js/mod-documents.js": {"dz-action-fermer": 1, "dz-etat-modifie": 1},
    "js/mod-espaces.js": {"dz-nav-espace-travail": 1},
    "js/mod-galerie.js": {"dz-action-ajouter": 1, "dz-action-supprimer": 1, "dz-edit-descendre": 1, "dz-edit-monter": 1,
                          "dz-etat-cache": 1, "dz-etat-visible": 1},
    "js/mod-historique.js": {"dz-action-annuler": 1, "dz-action-retablir": 1},
    "js/mod-infos.js": {"dz-etat-avertissement": 1},
    "js/mod-menus.js": {"dz-action-deplier": 1, "dz-etat-option-active": 1},
    "js/mod-nuancier.js": {"dz-action-ajouter": 1, "dz-action-deplier": 1, "dz-action-nouveau-dossier": 1, "dz-action-supprimer": 1},
    "js/mod-outils.js": {k: 1 for k in [
        "dz-edit-annotation", "dz-edit-couleurs-defaut", "dz-edit-echanger-couleurs", "dz-outil-photo-affiner-contour",
        "dz-outil-photo-compteur", "dz-outil-photo-correcteur", "dz-outil-photo-correcteur-tache", "dz-outil-photo-densite-moins",
        "dz-outil-photo-densite-plus", "dz-outil-photo-deplacer", "dz-outil-photo-doigt", "dz-outil-photo-eponge",
        "dz-outil-photo-flou", "dz-outil-photo-nettete", "dz-outil-photo-piece", "dz-outil-photo-pinceau-historique",
        "dz-outil-photo-recadrer", "dz-outil-photo-selection-ajouter", "dz-outil-photo-selection-intersection",
        "dz-outil-photo-selection-nouvelle", "dz-outil-photo-selection-objet", "dz-outil-photo-selection-soustraire",
        "dz-outil-photo-selection-sujet", "dz-outil-photo-selection-tranche", "dz-outil-photo-tampon", "dz-outil-px-baguette",
        "dz-outil-px-crayon", "dz-outil-px-degrade", "dz-outil-px-gomme", "dz-outil-px-gomme-fond", "dz-outil-px-gomme-magique",
        "dz-outil-px-lasso", "dz-outil-px-lasso-polygonal", "dz-outil-px-pinceau", "dz-outil-px-pinceau-melangeur", "dz-outil-px-pot",
        "dz-outil-px-selection", "dz-outil-px-selection-ellipse", "dz-outil-px-selection-rapide", "dz-outil-vec-ellipse",
        "dz-outil-vec-forme-perso", "dz-outil-vec-ligne", "dz-outil-vec-loupe", "dz-outil-vec-main", "dz-outil-vec-mesure",
        "dz-outil-vec-pipette", "dz-outil-vec-plume", "dz-outil-vec-polygone", "dz-outil-vec-rectangle", "dz-outil-vec-selection",
        "dz-outil-vec-texte", "dz-outil-vec-tranche", "dz-outil-vec-triangle"]},
    "js/mod-pinceaux.js": {"dz-action-supprimer": 1},
    "js/mod-presets.js": {"dz-action-ajouter": 1, "dz-action-deplier": 1, "dz-action-nouveau-dossier": 1, "dz-action-supprimer": 1},
    "js/mod-reglages.js": {k: 1 for k in [
        "dz-calque-balance-couleurs", "dz-calque-couleur-selective", "dz-calque-courbes", "dz-calque-exposition",
        "dz-calque-filtre-photo", "dz-calque-inverser", "dz-calque-luminosite-contraste", "dz-calque-mappage-degrade",
        "dz-calque-melangeur-couches", "dz-calque-niveaux", "dz-calque-noir-blanc", "dz-calque-posteriser", "dz-calque-reglage",
        "dz-calque-seuil", "dz-calque-table-couleurs", "dz-calque-teinte-saturation", "dz-calque-vibrance"]},
    "js/mod-texte.js": {"dz-action-abandonner": 1, "dz-action-ajouter": 1, "dz-action-dupliquer": 1, "dz-action-redefinir": 1,
                        "dz-action-reinitialiser": 1, "dz-action-supprimer": 1, "dz-action-valider": 1, "dz-edit-justifier": 1,
                        "dz-edit-justifier-centre": 1, "dz-edit-justifier-droite": 1, "dz-edit-justifier-gauche": 1,
                        "dz-edit-orientation-texte": 2, "dz-edit-texte-aligner-centre": 1, "dz-edit-texte-aligner-droite": 1,
                        "dz-edit-texte-aligner-gauche": 1, "dz-edit-texte-barre": 1, "dz-edit-texte-capitales": 1,
                        "dz-edit-texte-gras": 1, "dz-edit-texte-italique": 1, "dz-edit-texte-petites-capitales": 1,
                        "dz-edit-texte-souligne": 1},
    "js/mod-trace.js": {"dz-action-ajouter": 1, "dz-action-supprimer": 1, "dz-edit-charger-selection": 1, "dz-edit-contour-trace": 1,
                        "dz-edit-remplir-trace": 1, "dz-edit-selection-vers-trace": 1},
    "js/mod-transformer.js": {"dz-action-abandonner": 1, "dz-action-valider": 1, "dz-edit-conserver-proportions": 1,
                              "dz-edit-point-reference": 1, "dz-edit-relatif": 1},
}


def comptes(rel):
    c = collections.Counter(k for k in re.findall(r"dz-[a-z0-9]+(?:-[a-z0-9]+)*", code(lire(rel))) if k in CLES)
    return dict(c)


print("[1] runtime")
html = lire("index.html")
i_i18n = html.find('<script src="/shared/dz-i18n.js"></script>')
i_css = html.find('<link rel="stylesheet" href="/shared/icons/dz-icons.css">')
i_js = html.find('<script src="/shared/icons/dz-icons.js"></script>')
i_mod = html.find('<script type="module" src="js/core.js"></script>')
check("1.1 index.html charge dz-icons.css et dz-icons.js une fois chacun",
      html.count("/shared/icons/dz-icons.css") == 1 and html.count("/shared/icons/dz-icons.js") == 1)
check("1.2 ordre : dz-i18n.js < dz-icons.css/js < modules du lab", 0 <= i_i18n < i_css < i_mod and i_i18n < i_js < i_mod
      and all(i_js < html.find(m) for m in re.findall(r'<script type="module"[^>]*>', html)), (i_i18n, i_css, i_js, i_mod))
core = lire("js/core.js")
check("1.3 PL.icone rend dzIcone (synchrone), plus aucun fetch de icones/",
      "window.dzIcone(cle, { taille })" in core and 'fetch("icones/' not in core and "PL.icone = function icone(cle, taille = 16)" in core)
tous_js = {p.relative_to(PL).as_posix(): p.read_text(encoding="utf-8") for p in (PL / "js").glob("*.js")}
check("1.4 aucun module n'attend une promesse de PL.icone", not any(re.search(r"PL\.icone\([^)]*\)\.then|await PL\.icone", t) for t in tous_js.values()),
      [n for n, t in tous_js.items() if re.search(r"PL\.icone\([^)]*\)\.then|await PL\.icone", t)])

print("[2] sites du relevé")
check("2.1 289 sites à clé dans le périmètre (10 sans clé : texte seul / fichiers inutilisés)",
      len(SITES) == 289 and len(RELEVE) == 299 and not any(e.get("emoji_conserve") for e in RELEVE), (len(SITES), len(RELEVE)))
manq = sorted({e["cle_finale"] for e in SITES} - CLES)
check("2.2 chaque clé posée existe dans la suite", not manq, manq)
TABLES_PAR_FICHIER = {"js/mod-calques.js": set()}      # complété en [3] : vignettes de réglage servies par KINDS
non_portes = []
cpt = {f: comptes(f) for f in FICHIERS}
for e in SITES:
    f = e["source"].split(":")[0][len("frontend/photolab/"):]
    k = e["cle_finale"]
    if k not in cpt.get(f, {}) and not (f == "js/mod-calques.js" and k.startswith("dz-calque-") and k in cpt["js/mod-reglages.js"]):
        non_portes.append((e["id"], f, k))
check("2.3 chaque site porte sa clé dans son fichier (vignettes de réglage : table KINDS de mod-reglages)", not non_portes, non_portes)
ecarts = {f: (cpt.get(f), ATTENDU.get(f)) for f in set(ATTENDU) | set(FICHIERS) if (comptes(f) if (PL / f).exists() else None) != ATTENDU.get(f)}
check("2.4 compte de chaque clé par fichier = table figée", not ecarts, ecarts)

print("[3] tables exécutées sous node")
D = {}
if NODE:
    sonde = "\n".join([
        f'import {{ EMPLACEMENTS, ICONES_MODES, optionsPour }} from "{(PL / "js" / "mod-outils.js").as_uri()}";',
        f'import {{ VERROUS }} from "{(PL / "js" / "mod-calques.js").as_uri()}";',
        f'import {{ KINDS }} from "{(PL / "js" / "mod-reglages.js").as_uri()}";',
        f'import {{ OPTIONS }} from "{(PL / "js" / "mod-compositions.js").as_uri()}";',
        f'import {{ ICONES_ALIGN, ALIGNS }} from "{(PL / "js" / "mod-texte.js").as_uri()}";',
        "const sel = optionsPour('magicWand');",
        "console.log(JSON.stringify({ outils: EMPLACEMENTS.map((g) => g.map((o) => [o.id, o.icone])), modes: ICONES_MODES,",
        "  boutons: sel.filter((o) => o.type === 'bouton').map((o) => [o.cle, o.icone]), modeIcones: sel[0].icones,",
        "  verrous: VERROUS.map((v) => [v.cle, v.icone]), kinds: KINDS.map((k) => [k.kind, k.icone]),",
        "  compositions: OPTIONS.map((o) => [o.cle, o.icone]), aligns: ALIGNS.map((a) => [a, ICONES_ALIGN[a]]) }));",
    ])
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzg4_"))
    (d / "sonde.mjs").write_text(sonde, encoding="utf-8")
    r = subprocess.run([NODE, str(d / "sonde.mjs")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    shutil.rmtree(d, ignore_errors=True)
    try:
        D = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (r.stderr or r.stdout)[-600:], ")")
check("3.0 les modules s'importent sous node", bool(D))
if D:
    def releve(pred):
        return collections.Counter(e["cle_finale"] for e in SITES if pred(e))
    outils = [o for g in D["outils"] for o in g]
    check("3.1 45 outils, chacun une clé de la suite", len(outils) == 45 and all(k in CLES for _, k in outils),
          [o for o in outils if o[1] not in CLES])
    check("3.2 barre d'outils : multiensemble des clés = relevé (45 emplacements)",
          collections.Counter(k for _, k in outils) == releve(lambda e: e["emplacement"].startswith("barre d'outils verticale")))
    check("3.3 menus volants : clés des emplacements groupés = relevé (37 lignes)",
          collections.Counter(k for g in D["outils"] if len(g) > 1 for _, k in g)
          == releve(lambda e: e["emplacement"].startswith("menu volant de l'emplacement")))
    check("3.4 Doigt = dz-outil-photo-doigt (pointeur Lucide gardé, choix de l'utilisateur)", dict(outils)["smudge"] == "dz-outil-photo-doigt")
    m = re.search(r'"dz-outil-photo-doigt": "([^\n]*)",?\n', SUITE)
    check("3.5 la suite sert bien le pointeur Lucide sous dz-outil-photo-doigt",
          bool(m) and "M22 14a8 8 0 0 1-8 8" in m.group(1) and "M10 9.5V4a2 2 0 0 0-2-2a2 2 0 0 0-2 2v10" in m.group(1))
    check("3.6 modes de sélection (4) et boutons Sujet / Sélectionner et masquer = relevé",
          D["modeIcones"] == D["modes"] and collections.Counter(list(D["modes"].values()) + [k for _, k in D["boutons"]])
          == releve(lambda e: e["id"].startswith("photolab.options.")))
    check("3.7 verrous (5) : en-tête du panneau Calques = relevé",
          collections.Counter(k for _, k in D["verrous"]) == releve(lambda e: e["emplacement"].startswith("en-tête, ligne « Verr. : »")))
    kinds = collections.Counter(k for _, k in D["kinds"])
    check("3.8 16 kinds, 16 clés distinctes", len(D["kinds"]) == 16 and len(kinds) == 16 and all(k in CLES for k in kinds))
    for emp in ("grille de 16 boutons", "menu volant ouvert par le bouton cercle", "en-tête de l'éditeur", "vignette d'une ligne de calque de réglage"):
        check(f"3.9 kinds : « {emp} » = relevé", kinds == releve(lambda e, emp=emp: e["emplacement"].startswith(emp)))
    check("3.10 compositions : 3 bascules = relevé",
          collections.Counter(k for _, k in D["compositions"]) == releve(lambda e: e["emplacement"].startswith("à droite de chaque ligne de composition")))
    al = dict(D["aligns"])
    check("3.11 alignements : Paragraphe (7) et barre d'options (3) = relevé",
          collections.Counter(al.values()) == releve(lambda e: e["id"].startswith("photolab.paragraphe.align-"))
          and collections.Counter(al[a] for a in ("left", "center", "right")) == releve(lambda e: e["id"].startswith("photolab.options-texte.align-")))

print("[4] plus aucun ancien dessin")
check("4.1 frontend/photolab/icones : plus aucun SVG, la licence Lucide reste (pointeur du Doigt)",
      not list((PL / "icones").glob("*.svg")) and (PL / "icones" / "LICENSE-lucide.txt").is_file())
att = lire("ATTRIBUTION.md")
check("4.2 ATTRIBUTION.md : Lucide seulement pour le Doigt (dz-outil-photo-doigt), suite Deepotus Glyph pour le reste",
      "dz-outil-photo-doigt" in att and "Deepotus Glyph" in att and "LICENSE-lucide.txt" in att and "dossier `icones/`) sont des icônes" not in att)
LUCIDE = ("move|rectangle-horizontal|circle|lasso|pentagon|wand|lasso-select|scan|crop|scissors|mouse-pointer-2|pipette|ruler|"
          "message-square|hash|bandage|brush|pencil|stamp|history|eraser|eraser-background|eraser-magic|blend|paint-bucket|droplet|"
          "triangle|pointer|sun|flame|cloud|pen-tool|type|minus|diamond|hand|search|eye|eye-off|chevron-down|chevron-right|"
          "chevron-up|chevrons-left|chevrons-right|link|lock|grid-3x3|sliders|sliders-horizontal|palette|layers|copy|trash-2|"
          "folder-plus|file-plus|plus|circle-dashed|square-dashed|rotate-cw|sparkles|undo-2|redo-2|app-window|compass|info")
noms = re.compile(r'(?:icone:\s*|icone\(|PL\.icone\(|data-icone=|dataset\.icone\s*=\s*)"(' + LUCIDE + r')"'
                  r'|bouton\("(' + LUCIDE + r')",|\? "(' + LUCIDE + r')" : "(?:' + LUCIDE + r')"')     # (un curseur CSS « move » : "crosshair" n'est pas une icône)
restes = {n: noms.findall(code(t)) for n, t in list(tous_js.items()) + [("index.html", html)] if noms.search(code(t))}
check("4.3 aucun nom d'icône Lucide passé comme icône (tables, boutons, ternaires, data-icone)", not restes, restes)
GLYPHES = ['"✓"', '"⊘"', '"⛓"', '"Δ"', '"⫷"', '"⫸"', '"≡"', '"☰', '"▸"', '"▾"', '"⚠"', '"×"', '" •"', '"fx"', '"↕T', '"T↔"',
           '"TT"', '"Tt"', '"⇄', '"◧']
glyphes = {n: [g for g in GLYPHES if g in code(t)] for n, t in tous_js.items() if any(g in code(t) for g in GLYPHES)}
check("4.4 aucun des glyphes remplacés dans le code des modules", not glyphes, glyphes)
css = lire("photolab.css")
check("4.5 photolab.css : plus de mise en forme des lettres « T » des bascules ; chevron unique orienté par CSS",
      "tx-fauxBold { font-weight" not in css and ".pl-replie svg.dzi" in css and "rotate(-90deg)" in css)

print("[5] node --check")
if NODE:
    mauvais = []
    for p in sorted((PL / "js").glob("*.js")) + [PL / "qa" / "outils" / "suite-icones.mjs"]:
        r = subprocess.run([NODE, "--check", str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            mauvais.append((p.name, r.stderr[-200:]))
    check("5.1 node --check de chaque module du Photolab et du lien QA", not mauvais, mauvais)
else:
    check("5.1 node disponible", False, "node introuvable")

print(f"\n=== {ok} passed, {fail} failed ===")


def test_icones_g4():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
