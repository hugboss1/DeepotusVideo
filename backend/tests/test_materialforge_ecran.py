# -*- coding: utf-8 -*-
"""Écran /materialforge/ — bancs-miroirs de texte (T4 et T8 du plan
2026-09-03-plan-matieres).

Patron de test_etabli_canevas.py : le frontend est du vanilla servi en
statique, donc on le LIT comme du texte et on y épingle des marqueurs. Les
assertions NÉGATIVES portent sur le fichier PRIVÉ DE SES COMMENTAIRES — ce
dépôt commente en expliquant ce qu'il écarte, et un `assert "x" not in js`
posé sur le fichier entier serait satisfait par la phrase même qui jure de
ne pas s'en servir.

LA MOITIÉ QUI COMPTE : les clés du contrat HTTP sont épinglées DES DEUX
CÔTÉS — dans `routes.py` et dans `materialforge.js`. Renommer une clé d'un
seul côté fait rougir ce banc, ce qu'aucune lecture d'un seul fichier ne
saurait faire.

Run (depuis backend/) : python tests/test_materialforge_ecran.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend" / "materialforge"
ROUTES = RACINE / "backend" / "app" / "api" / "routes.py"

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def lire(nom):
    return (FRONT / nom).read_text(encoding="utf-8")


def code(nom):
    """Le fichier SANS ses blocs /* … */ — réservé aux assertions négatives."""
    return re.sub(r"/\*.*?\*/", "", lire(nom), flags=re.S)


HTML = lire("index.html")
JS = lire("materialforge.js")
JS_CODE = code("materialforge.js")
CSS = lire("materialforge.css")
PY = ROUTES.read_text(encoding="utf-8")

# ══ 1 · le panneau Photo existe et porte ses commandes ══════════════════════
for ident in ("grpPhoto", "phCanvas", "phDelight", "phStrength", "phPreview",
              "phReset", "phOut", "phMeasure"):
    assert f'id="{ident}"' in HTML, ident
assert HTML.count('id="grpPhoto"') == 1
assert '<div class="grp-body">' in HTML.split('id="grpPhoto"', 1)[1].split("</details>", 1)[0]
ok("index.html : panneau Photo — canevas des quatre coins, délighter, "
   "intensité, aperçu, remise à zéro, image de sortie, mesure")

# ══ 2 · le contrat HTTP est épinglé DES DEUX CÔTÉS ══════════════════════════
assert '"/materials/prep/preview"' in PY, "la route a changé de chemin"
assert "/materials/prep/preview" in JS_CODE, "l'écran n'appelle plus la route"
for cle in ("lowfreq_sd_before", "lowfreq_sd_after", "baisse_pct"):
    assert cle in PY, cle
    assert cle in JS_CODE, f"{cle} absent du JS — contrat rompu d'un côté"
ok("contrat d'aperçu épinglé des deux côtés : chemin + trois clés de mesure")

# ══ 3 · la génération EMPORTE la préparation ════════════════════════════════
corps = JS_CODE.split("async function generate()", 1)[1].split("\n}\n", 1)[0]
assert re.search(r"if \(state\.ref\) \{\s*body\.filename = state\.ref;\s*body\.prep = photoPrep\(\);",
                 corps), corps[:900]
ok("generate() envoie le bloc prep AVEC la référence, et seulement avec elle")

# ══ 3b · state.ref est une CHAÎNE, et un refus n'est pas une API absente ════
pv = JS_CODE.split("async function photoPreview()", 1)[1].split("\n}\n", 1)[0]
assert "const fn = state.ref;" in pv and "state.ref.filename" not in JS_CODE, pv[:300]
assert "if (e.missing) apiFail(" in pv and "toast(" in pv, pv
ok("photoPreview lit le nom de la référence tel quel ; un 400 se dit en toast, "
   "apiFail reste aux routes absentes")

# ══ 4 · quatre coins, pas trois ni cinq ═════════════════════════════════════
assert re.search(r"quad\.length\s*[<>=!]{1,3}\s*4", JS_CODE), \
    "aucune garde sur le nombre de coins"
assert "phCanvas" in JS_CODE and "getBoundingClientRect" in JS_CODE
# la regex ci-dessus est satisfaite par photoPrep() seule : on épingle aussi le
# geste lui-même — un CINQUIÈME clic recommence la saisie, il ne l'allonge pas
clic = JS_CODE.split("function photoClick(ev)", 1)[1].split("\n}\n", 1)[0]
assert "if (photo.quad.length >= 4) photo.quad = [];" in clic, clic
# la conversion affichage -> image se fait DANS photoClick (getBoundingClientRect
# existe ailleurs dans le fichier : le chercher partout laissait un mutant vert)
assert '$("#phCanvas").getBoundingClientRect()' in clic and "/ photo.fit.s" in clic, clic
# et une NOUVELLE référence oublie les coins de l'ancienne
ref = JS_CODE.split("function setRef(fn)", 1)[1].split("\n}\n", 1)[0]
assert "photo.quad = [];" in ref and '$("#phMeasure").textContent = "—";' in ref, ref
ok("le canevas borne la saisie à quatre coins et convertit les clics en "
   "coordonnées d'image")

# ══ 5 · le style existe ════════════════════════════════════════════════════
for regle in ("#phCanvas", "#phOut"):
    assert regle in CSS, regle
ok("materialforge.css : le canevas et l'aperçu ont leur règle")

# ══ 7 · chaque convention PUBLIÉE par le serveur a son bouton ══════════════
# (T096 : le plan ajoutait « blender » à NAMINGS sans bouton dans l'export —
# la convention aurait existé sans qu'aucun clic n'y mène)
MS_PY = (RACINE / "backend" / "app" / "services" / "material_store.py").read_text(encoding="utf-8")
noms = re.findall(r'"(\w+)"', re.search(r"^NAMINGS = \((.*?)\)", MS_PY, re.M).group(1))
seg = HTML.split('id="exNaming"', 1)[1].split("</div>", 1)[0]
boutons = re.findall(r'data-v="(\w+)"', seg)
assert "blender" in noms and boutons == noms, (noms, boutons)
ok(f"export : un bouton par convention publiée, dans le même ordre ({len(noms)})")

# ══ 8 · « Mon modèle » : le viewport SEUL, un sélecteur, un cadrage libre ══
mesh_js = re.search(r"^const MESHES = \[(.*?)\];", JS_CODE, re.M | re.S).group(1)
assert '"model"' not in mesh_js, "la galerie suit MESHES : un modèle par carte"
gu = JS_CODE.split("function glbUrl(", 1)[1].split("\n}\n", 1)[0]
assert 'if (mesh === "model")' in gu and "&model=" in gu and "&mversion=" in gu, gu
assert "&mesh=" not in gu.split('if (mesh === "model")', 1)[1].split("return \"/api", 1)[0]
assert "modele3d" in JS_CODE and "state.model.job" not in JS_CODE
fv = JS_CODE.split("function frameViewport(", 1)[1].split("\n}\n", 1)[0]
assert "if (state.vpModele)" in fv and 'camera-target", "auto auto auto"' in fv, fv[:500]
sv = JS_CODE.split("async function setVpMesh(", 1)[1].split("\n}\n", 1)[0]
assert '"/etabli/sources' in sv and 'j.source === "assets3d"' in sv, sv
# une étape sans numéro (model.opt.glb) n'est pas une version : on prend le
# plus grand ENTIER, jamais « la dernière étape » (preuve 8799 : « v » vide)
assert "Number.isInteger(v) && v >= 1" in sv and "Math.max(...j.versions)" in sv, sv
assert "j.etapes[j.etapes.length - 1]" not in JS_CODE
assert 'id="modelPick"' in HTML
for cle in ('model: str = ""', "mversion: int = 1"):
    assert cle in PY, cle
ok("Mon modèle : hors de la galerie, URL model+mversion sans mesh, sélecteur "
   "nourri par /etabli/sources, cadrage rendu à <model-viewer>")

# ══ 9 · les ambiances importées (T7) ═══════════════════════════════════════
for ident in ("envFile", "envDel"):
    assert f'id="{ident}"' in HTML, ident
assert 'accept=".hdr,.jpg,.jpeg,.png"' in HTML
le = JS_CODE.split("async function loadEnvs()", 1)[1].split("\n}\n", 1)[0]
assert "perso: !!e.perso" in le, le
assert '"perso": bool(r.get("perso"))' in (RACINE / "backend" / "app" / "services" /
                                            "material_store.py").read_text(encoding="utf-8")
assert "if (err.missing) apiFail(err, \"import d'ambiance\")" in JS_CODE
assert '@router.post("/materials/envs")' in PY and '@router.delete("/materials/envs/{name}")' in PY
ok("ambiances importées : bouton et suppression, drapeau `perso` porté du "
   "serveur à la puce, un refus de fichier n'éteint pas l'API")

# ══ 10 · la comparaison côte à côte (T8) ═══════════════════════════════════
for ident in ("mv", "mvB", "cmpBtn", "cmpPick"):
    assert f'id="{ident}"' in HTML, ident
assert HTML.count("<model-viewer") == 2, HTML.count("<model-viewer")
# La MÊME ambiance des deux côtés : applyEnvToViewers parcourt TOUS les
# <model-viewer> (le plan voulait y ajouter #mvB — c'était déjà le cas ; on
# épingle le parcours général, qui couvre aussi tout futur viewer).
env = JS_CODE.split("function applyEnvToViewers()", 1)[1].split("\n}\n", 1)[0]
assert '$$("model-viewer").forEach' in env, env[:300]
# La caméra se LIT, elle ne se recopie pas par l'attribut.
sync = JS_CODE.split("function compareSync()", 1)[1].split("\n}\n", 1)[0]
assert "getCameraOrbit()" in sync and "getCameraTarget()" in sync and "getFieldOfView()" in sync, sync
assert '"min-camera-orbit", "max-camera-orbit"' in sync, "les bornes de #mv doivent suivre (2,2 m tenus pour 6 m)"
assert "b.cameraOrbit = a.cameraOrbit" not in JS_CODE and "$(\"#mv\").cameraOrbit" not in JS_CODE
# Un seul chemin de GLB, et la même forme que le viewport (« Mon modèle » compris)
cmp = JS_CODE.split("function setCompare(", 1)[1].split("\n}\n", 1)[0]
assert 'glbUrl(m, 1024, state.vpModele ? "model" : state.mesh, true)' in cmp, cmp
assert "state.open" not in JS_CODE, "le dépôt dit state.sel"
assert '"camera-change", compareSync' in JS_CODE
# la vue principale change (matière, forme, modèle) : la seconde SUIT
vs = JS_CODE.split("function setViewportSrc(m)", 1)[1].split("\n}\n", 1)[0]
assert "if (state.compare) setCompare(" in vs, vs[-400:]
assert ".vp-stage.split { display: grid; grid-template-columns: 1fr 1fr;" in CSS, \
    "la GRILLE à deux colonnes (le sélecteur seul existe aussi dans ::after)"
ok("comparaison : deux viewers, ambiance par le parcours général, caméra lue "
   "par getCameraOrbit, un seul chemin de GLB qui suit « Mon modèle »")

# ══ 11 · la hauteur physique : une ligne `top` (T097) ══════════════════════
groups = JS_CODE.split("const GROUPS = [", 1)[1].split("\n];\n", 1)[0]
assert 'k: "height_mm"' in groups and "top: 1" in groups, groups[:300]
ins = JS_CODE.split("row.top\n", 1)
assert len(ins) == 2 and "setTop(row, v, livePass)" in ins[1][:200] and "Number(m[row.k])" in ins[1][:200]
st = JS_CODE.split("function setTop(", 1)[1].split("\n}\n", 1)[0]
assert "queuePatch({ top: { [row.k]: v } })" in st and "m[row.k] = v" in st, st
fl = JS_CODE.split("async function flushPatch()", 1)[1].split("\n}\n", 1)[0]
assert "Object.assign(body, patchPending.top)" in fl, "les lignes top vont à la RACINE du PATCH"
assert "props: { [row.k]" not in st
ok("hauteur physique : ligne `top` lue sur la matière, PATCH à la racine du corps (pas dans props)")

# ══ 12 · le catalogue CC0 (T10) ════════════════════════════════════════════
oc = JS_CODE.split("async function ouvrirCatalogue(", 1)[1].split("\nfunction emptyHtml(", 1)[0]
assert '$("#proofTitle").textContent' in oc and '$("#proofBody").innerHTML' in oc, oc[:300]
assert '$("#proof").innerHTML' not in oc and "box.innerHTML" not in oc, "le dialogue PARTAGÉ garde son cadre"
assert '"/materials/catalog/import"' in oc and "if (e.missing) apiFail(" in oc
assert 'id="catBtnHead"' in HTML and 'data-empty="catalog"' in JS_CODE
assert '@router.post("/materials/catalog/import")' in PY and '@router.get("/materials/catalog")' in PY
assert ".cat-cell {" in CSS and "height: 132px" in CSS.split(".cat-cell {", 1)[1].split("}", 1)[0]
ok("catalogue : bouton permanent + galerie vide, dialogue partagé gardé (titre et corps seulement), "
   "un POST pour tout l'import, cases à hauteur explicite")

# ══ 13 · l'onglet Générateurs (T098) ═══════════════════════════════════════════════
for ident in ("tabForge", "tabGen", "paneGen", "genList", "genParams",
              "genGo", "genPreview"):
    assert f'id="{ident}"' in HTML, ident
assert "/materials/patterns" in JS_CODE
ok("index.html : deux onglets de rail (Forger / Générateurs), liste, "
   "réglages, aperçu et bouton de création")

# Les bornes ne sont PAS recopiées dans le JS : elles viennent de la route.
corps_gen = JS_CODE.split("function renderGenParams(", 1)[1].split("\n}\n", 1)[0]
assert "p.min" in corps_gen and "p.max" in corps_gen, corps_gen[:400]
for interdit in ("min=\"2\"", "max=\"32\"", "briques", "hexagones"):
    assert interdit not in corps_gen, interdit
ok("les bornes et les identifiants de générateurs viennent de l'API : aucun "
   "chiffre ni aucun nom recopié dans l'écran")
# l'aperçu ne CRÉE rien : c'est un GET, réglages en p_<nom>
assert '@router.get("/materials/patterns/{gid}/preview.png")' in PY
pv = JS_CODE.split("function genPreviewSoon()", 1)[1].split("\n}\n", 1)[0]
assert '"p_" + k' in pv and "/preview.png?" in pv and "setTimeout" in pv, pv
st = JS_CODE.split("function setRailTab(", 1)[1].split("\n}\n", 1)[0]
assert '"#footForge"' in st and "loadPatterns()" in st, "le pied du rail Forger se cache avec son onglet"
ok("aperçu par GET sans écriture, retardé ; l'onglet cache le corps ET le pied du rail Forger, "
   "et ne charge la liste qu'à sa première ouverture")
assert 'if (e.missing) apiFail(e, "génération de motif"); else toast(' in JS_CODE, \
    "un refus de génération n'éteint pas l'API"
assert "openMaterial(d.material.id)" in JS_CODE

print(f"\nOK — {PASS} assertions groupées vertes (écran Material Forge)")
