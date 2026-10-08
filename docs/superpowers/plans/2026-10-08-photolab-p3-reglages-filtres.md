# Photolab P3 — réglages, filtres, fusion, styles — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** dans le Photolab, chaque filtre et chaque réglage du moteur photocraft s'ouvre dans un dialogue (généré depuis la description `params` de la commande, sur mesure pour Courbes, Niveaux et Style de calque) avec un aperçu calculé par le moteur ; les 16 calques de réglage se créent et se modifient dans Propriétés ; les styles de calque se posent par un dialogue ; le pont n'admet plus que ce que le registre du moteur épinglé décrit (liste blanche), sans perdre les refus de fichiers.

**Architecture :** le BACKEND parse une seule fois la grammaire `params` du registre (`engine.commands`) en champs typés (`photolab_registre.py`) ; ces champs servent (1) la liste blanche de `/executer` et (2) l'écran, qui les reçoit par `/commandes` et en fabrique les formulaires. L'aperçu est calculé par le moteur sur une COPIE du document (`image.duplicate`, sélection conservée, calque actif reposé par position), ce qui laisse l'original, son historique et sa pile de rétablissement intacts. L'écran n'invente aucun pixel, sauf l'aperçu JS (table de correspondance) pendant le glisser d'un point de Courbes / d'un curseur de Niveaux, remplacé au relâchement par l'aperçu moteur.

**Spec :** `docs/superpowers/specs/2026-10-07-photolab-design.md` (D1, D3 : génériques depuis `params`, sur mesure Courbes / Niveaux / Style de calque ; D9 : Camera Raw, Liquify, Vanishing Point, Adaptive Wide Angle, Puppet Warp hors périmètre, grisés « bientôt ») ; inventaire `2026-10-07-photocraft-inventaire.md` (B §4 réglages, filtres, modes, styles ; A6 look du dialogue « Flou gaussien »). Plans précédents : `2026-10-07-photolab-p1-moteur.md`, `2026-10-07-photolab-p2-ecran.md`.

**Tech :** FastAPI + Python 3.13 embarqué, Pillow (histogramme), HTML/CSS/JS ES modules sans framework, node pour les bancs JS.

**Hors t138 :** P3b (peinture, retouche, texte, formes, plume), dialogues « Envoyer vers » (P4/t139), panneaux Nuancier / Dégradés / Couches, Galerie de filtres (`filter.filterGallery` et les 47 `filter.gallery.*`), masques de calque, filtres dynamiques.

---

## Faits établis (relevés le 08/10/2026 sur le VRAI `photocraft-cli` 0.3.0)

Sources : relevé `scratchpad/t138/registre.md` (sondes s1-s14), relevé du code `scratchpad/t138/code.md`, sonde s20 (copie et sélection). `scratchpad` = `C:\Users\olivi\AppData\Local\Temp\claude\C--Users-olivi-DeepotusVideo--claude-worktrees-gifted-meitner-531e8d\2efb2784-3902-4f22-b7a7-f61a1a5af1a3\scratchpad`.

**Registre.** `engine.commands` (méthode de `serve`) = 776 entrées `{id, label, menu[], shortcut, params, enabled}` ; `params` est un texte « JSON-ish » : `{ENTREE, …}` puis une queue libre (` (note)`, ` → résultat`, ` — phrase`) ; `ENTREE = "clé":TYPE[=DEFAUT][?][ (note)]`. Exemples réels :
- `filter.blur.gaussianBlur` → `{"radius":0.1..1000=1}`
- `filter.noise.addNoise` → `{"amount":0.1..400=12.5,"distribution":"uniform|gaussian","monochromatic":bool,"seed":u32=0}`
- `layer.newAdjustmentLayer.levels` → `{"inBlack":0..253=0,"gamma":0.01..9.99=1,"inWhite":2..255=255,"outBlack":0..255=0,"outWhite":0..255=255,"red":json,"green":json,"blue":json} (top level = composite; per channel {"inBlack","gamma","inWhite","outBlack","outWhite"} under red/green/blue, …)`
- `layer.newAdjustmentLayer.curves` → `{"points":json,"red":json,"green":json,"blue":json} (curves as [[in,out],…] in 0..255, 2..19 points: …)`
- `layer.setProps` → `{"layer":id?,"name":str?,"visible":bool?,"opacity":0..1?,"fill":0..1?,"blend":"Multiply|…"?,"clipped":bool?,"locked":bool?,"locks":{…}?,"channels":[bool,…]? (…)}` — `"Multiply|…"` est une énumération OUVERTE (dernier élément `…`).
- `edit.fill` → `…,"color":"#rrggbb|[r,g,b,a]"=foreground (contents=color),"pattern":id|name (contents=pattern),"scale":%=100,"angle":deg,…` — une couleur sous deux formes, une union d'identifiants, des unités.
- `layer.setAdjustment` → `{"layer":id?, …params of that adjustment kind}`.
Le parseur de référence (`scratchpad/t138/grammaire.py`, 150 lignes) structure SANS résidu les 75 filtres, les 47 effets de galerie, les 39 réglages et les 19 styles ; 138 descriptions du registre gardent un fragment non typé avec ce parseur de référence, dont `style.presets.edit` (périmètre P3) ; le portage A1 reconnaît `group`, `n` et l'union `name|[names]` → 126. Défaut connu à corriger au portage : `"#rrggbb|[r,g,b,a]"` est classé `enum` (tester la couleur AVANT l'énumération), et une énumération dont le dernier élément est `…` est ouverte.

**Validation par le moteur.** Clés inconnues ignorées en silence. Filtres : mauvais type → défaut en silence (`radius:"2"` → 1), hors bornes → borné (`radius 5000` → 1000) ; la réponse rend `result.filter` (valeurs réellement appliquées). Réglages : type faux ou énumération inconnue refusés. Styles : tout accepté et remplacé en silence. `layer.setProps {blend: 3}` répond ok sans rien changer. D'où la liste blanche côté pont.

**Sécurité.** Le moteur refuse lui-même plus de 40 commandes à fichier (« uses ambient filesystem paths and is disabled »). Mais 5 commandes NON gardées lisent un chemin arbitraire (absolu, `..`) : `image.mode.{rgb,grayscale,cmyk,lab}` (clé `profile`), `brush.presets.importAbr` (`path`), `gradient.presets.importGrd` (`path`), `plugin.install` (`path`, `data` base64 = module WebAssembly exécutable), `plugin.reload` (`path`) ; `prefs.set`/`prefs.reset` écrivent les préférences persistantes. Dans le périmètre P3, `source` et `output` ne sont JAMAIS des fichiers : `layer.layerStyle.innerGlow.source` = `edge|center`, `image.adjustments.matchColor.source` = index de document ; le mélangeur de couches n'a pas de clé `output` (la couche de sortie EST la clé `red|green|blue|gray`, valeur `[R%,V%,B%,constante%]`). `colorLookup.lut` = énumération intégrée (`none|warm|cool|tealOrange|bleachBypass|fadedFilm|dayForNight|monoContrast|crossProcess`) ; `colorLookup.file` est refusé par le moteur ; `colorLookup.data` = contenu de fichier LUT en ligne (à refuser : texte arbitraire). `filter.distort.displace.mapPath` refusé par le moteur ; `filter.render.flame.path` = nom d'un tracé (P3b).

**Calques de réglage** (16 kinds) : créer = `layer.newAdjustmentLayer.<kind> {…}` → `{layer: id}` (au-dessus du calque actif, devient actif, historique « New Levels Layer ») ; modifier = `layer.setAdjustment {layer?, …params du kind}` (FUSION : les clés absentes gardent leur valeur ; historique « Modify Adjustment » ; clés d'un autre kind ignorées en silence) ; destructif = `image.adjustments.<kind>` (mêmes paramètres). Kinds : `brightnessContrast levels curves exposure vibrance hueSaturation colorBalance blackWhite photoFilter channelMixer invert posterize threshold gradientMap selectiveColor colorLookup`. Destructifs seuls : `desaturate equalize shadowsHighlights replaceColor matchColor hdrToning` (+ `colorLookup.list` → 8 LUT `{id,label}`). Un filtre ou un réglage destructif sur un calque de réglage est refusé (« filters need a pixel layer »).

**`doc.inspect` d'un calque de réglage** : `{"kind":"Adjustment","name":"Curves 1","bounds":null,…,"adjustment":{"Curves":{…}}}` — structure INTERNE, pas les paramètres de commande :

| kind | `adjustment` | conversion vers les paramètres de commande |
|---|---|---|
| brightnessContrast | `{"BrightnessContrast":{brightness,contrast,legacy}}` | mêmes unités |
| levels | `{"Levels":{"master":{in_black,gamma,in_white,out_black,out_white},"per_channel":[×3],"black":{…},"space":"Rgb"}}` | ×255 et arrondi pour in/out (gamma tel quel) ; `per_channel[0..2]` → `red/green/blue` |
| curves | `{"Curves":{"master":[{input,output}],"per_channel":[[…]×3],"black":[],"space":"Rgb"}}` | `[[round(input×255), round(output×255)]…]` ; canaux → `red/green/blue` (liste vide = absent) |
| exposure | `{"Exposure":{exposure,offset,gamma}}` | mêmes unités |
| vibrance | `{"Vibrance":{vibrance,saturation}}` | mêmes unités |
| hueSaturation | `{"HueSaturation":{hue,saturation,lightness,colorize,ranges:[{bounds:[4],hue,saturation,lightness}×6]}}` | `ranges[0..5]` → `reds yellows greens cyans blues magentas` = `{hue,saturation,lightness,range: bounds}` |
| colorBalance | `{"ColorBalance":{shadows:[3],midtones:[3],highlights:[3],preserve_luminosity}}` | `preserve_luminosity` → `preserveLuminosity` |
| blackWhite | `{"BlackWhite":{weights:[6],tint:null\|[r,g,b] 0..1}}` | `weights[0..5]` → `reds…magentas` ; `tint` → `tint:true, tintColor:"#rrggbb"` |
| photoFilter | `{"PhotoFilter":{color:[r,g,b] 0..1,density:0..1,preserve_luminosity}}` | `color` → `"#rrggbb"`, `density×100` ; le nom du préréglage `filter` est PERDU (l'écran garde `color`) |
| channelMixer | `{"ChannelMixer":{matrix:[[r,g,b,c]×3] (1.0 = 100 %),monochrome}}` | `red/green/blue = matrix[i]×100` ; en monochrome, `gray = matrix[0]×100` |
| invert | `"Invert"` (chaîne) | `{}` |
| posterize | `{"Posterize":{levels}}` | tel quel |
| threshold | `{"Threshold":{level}}` (0..1) | `round(level×255)` |
| gradientMap | `{"GradientMap":{stops:[[pos,[r,g,b]]],reverse,dither}}` | couleurs → `"#rrggbb"` (forme exacte de `stops` côté commande : à relire dans la note du registre et à vérifier en Task A4) |
| selectiveColor | `{"SelectiveColor":{adjustments:[[c,m,y,k]×9],relative}}` | gammes `reds yellows greens cyans blues magentas whites neutrals blacks` ; `relative:false` → `method:"absolute"` |
| colorLookup | `{"ColorLookup":{lut:null\|[107 811 nombres],name,size,tetrahedral,dither}}` | l'id du LUT est PERDU (seul `name`, ex. « Warm Filter ») → retrouver l'id par le libellé de `colorLookup.list` ; `tetrahedral` → `interpolation` |

Un seul calque Color Lookup porte `doc.inspect` de 1 Ko à 2,19 Mo (tableau `lut` de 107 811 nombres) : le pont l'ÉLAGUE avant de répondre à l'écran.

**Styles de calque** : `layer.layerStyle.<kind> {layer?, enabled?, add?, …}` (kinds `dropShadow innerShadow outerGlow innerGlow stroke colorOverlay gradientOverlay patternOverlay bevelEmboss satin`) ; `layer` et `enabled` sont honorés bien que non documentés dans 9 styles sur 10 ; ré-appeler un kind REMPLACE son effet par les défauts + les clés données (rien n'est fusionné) ; `enabled:false` éteint l'effet (en renvoyant tous ses paramètres) ; `layer.layerStyle.clear {layer}` retire tout ; `layer.layerStyle.blendingOptions {layer, blend, opacity 0..100, fillOpacity 0..100, blendIf}`. `doc.inspect` ne rend que `effects:{enabled, items:[{enabled, kind:"Drop Shadow"}]}`, AUCUN paramètre → l'écran garde les siens. Paramètres (T4 du relevé) : dropShadow `color, opacity 0..100=75, blend="multiply", angle deg=120, useGlobalLight bool, distance px=5, spread 0..100, size px=5, knocksOut bool` ; innerShadow `color, opacity, blend, angle, distance, choke 0..100, size` ; outerGlow `color, opacity, blend="screen", technique softer|precise, spread, size, range 0..100` ; innerGlow `color, opacity, blend="screen", technique, source edge|center, choke, size` ; stroke `size px=3, position outside|inside|center, color, from, to, style, angle, opacity, blend` ; colorOverlay `color, opacity=100, blend` ; gradientOverlay `from, to, style linear|radial|angle|reflected|diamond, angle=90, scale 10..150=100, reverse, opacity, blend` ; patternOverlay `pattern id|name, opacity, blend, scale 1..1000, angle, link, phaseX, phaseY` ; bevelEmboss `style inner|outer|emboss|pillow|stroke, technique smooth|chiselHard|chiselSoft, contour, contourRange, texture, textureScale, textureDepth, textureInvert, textureLink, depth 1..1000=100, direction up|down, size px=5, soften px, angle, altitude` ; satin `color, opacity=50, blend, angle, distance, size, invert`. Valeurs invalides acceptées et remplacées en silence par le moteur.

**Modes de fusion** (28 ids camelCase de `layer.setProps.blend`) : `passThrough normal dissolve darken multiply colorBurn linearBurn darkerColor lighten screen colorDodge linearDodge lighterColor overlay softLight hardLight vividLight linearLight pinLight hardMix difference exclusion subtract divide hue saturation color luminosity` ; `inspect` rend les libellés anglais (« Linear Dodge (Add) ») ; la comparaison du moteur ignore casse, espaces, tirets, soulignés ; `add`, `mul`, `pass` refusés ; un nombre accepté sans effet ; les styles acceptent n'importe quelle chaîne. `MODES_FUSION` existe déjà dans `frontend/photolab/js/mod-calques.js:61-80` (+ `idFusion`).

**Filtres** : 75 au menu Filtre (8 à la racine + 10 sous-menus, ids et paramètres en T2 du relevé). D9 : `filter.cameraRaw`, `filter.liquify`, `filter.vanishingPoint`, `filter.adaptiveWideAngle` (Puppet Warp = `layer.smartObjects.puppetWarp`, hors menu Filtre). Champ requis non éditable (« opaque ») : `filter.filterGallery` (`effects`), `filter.distort.displace` (`mapPath`/`mapDocument`) → « bientôt ». Durées 1920×1080 : la plupart 40-130 ms ; radial 1,2-1,9 s, médiane r5 0,7 s, mouvement d=40 0,7 s, extrude 0,25 s. Un `edit.undo` après chaque filtre rend l'image identique à l'octet.

**Aperçu (sonde s20)** : `image.duplicate {name}` → `{document: index}` crée une copie ACTIVE qui garde la sélection (même elliptique et progressive, `selectionBounds` identiques) mais PAS le calque actif (la copie active son calque du haut ; les ids sont renumérotés → apparier par POSITION dans `layers`, puis `layer.select {layer, mode:"replace"}`). Un filtre appliqué sur la copie puis rendu donne un PNG identique à l'octet au même filtre appliqué sur l'original. Après `doc.close {index: <index copie>}` puis `doc.select {index: <index original>}` (attention : les deux attendent `index` ; `doc.close {document: n}` IGNORE la clé et ferme le document ACTIF — vu en A3), l'original garde son calque actif, sa sélection, `canRedo`, `revision` et son historique. Copie ≈ 340 ms sur 1920×1080 un calque ; rendu ≈ 170 ms. (Appliquer puis annuler sur l'original laisserait l'étape dans la pile de rétablissement : écarté.)

**Histogramme** : aucune commande moteur par canal → calculé par Pillow sur un `doc.render` de la copie.

**Écran (P2, à modifier)** : `mod-menus.js:28-31` `parametresRequis(texte)` ; `:97-103` `actionEntree` → `"dialogue"` ; `:251-273` `activer` (l. 264 : `PL.post("/executer")` EN DIRECT, hors file FIFO — défaut à corriger) ; `:267-269` dialogue « arrive en P3 » (`photolab.menu.p3`). `mod-cycle.js:232-240` `PL.executer(command, params={}, {cycle=true})` → `{ok, r}` par la file FIFO `PL.file`. `mod-fichier.js:82-122` `ouvrirDialogue(PL, {titre, classe, construire, boutons})` (modal, centré, masque l'image). `mod-proprietes.js` panneau en LECTURE SEULE, `#grpProprietes` hauteur fixe 170 px (`photolab.css:81`). `mod-calques.js:146-157` pied : `bFx`, `bMasque`, `bReglage` « bientôt ». Le rendu s'affiche par `PL.vue.poserRendu({image, maxSide})` puis `PL.vue.dessiner()` (`mod-vue.js`). Rail : bouton `reglages` replie `#grpProprietes` (titre « Ajustements »). Bancs figés : `qa/zones.test.mjs` 2.3 (exactement 3 `<section>`) et 2.4 (5 boutons de rail) ; `qa/menus.test.mjs` 7.1 (`REFUSES` == `PREFIXES_REFUSES` lus par regex `PREFIXES_REFUSES = \(([\s\S]*?)\)\s*#` dans le .py — GARDER le commentaire après la parenthèse) et 8.6 (`actionEntree(gauss) === "dialogue"`) ; `test_photolab_moteur.py:177-208` (refus 3a-3d) ; `test_photolab_textes.py` (aucune chaîne FR en dur dans `js/`, toute clé écrite en toutes lettres existe fr+en) ; `qa/textes.test.mjs` (clés COMPOSÉES recensées).

**Commandes que l'écran P2 envoie (doivent rester admises par la liste blanche)** : `layer.new.layer {name?}`, `layer.delete`, `layer.duplicate`, `layer.select {layer, mode}`, `layer.renameLayer {layer, name}`, `layer.setProps {layer, name|visible|opacity|fill|blend|locks}`, `layer.moveTo {layer, target, position}`, `layer.groupLayers`, `layer.mergeDown`, `layer.new.layerFromBackground`, `layer.new.layerViaCopy`, `layer.translate {layer?, dx, dy}`, `layer.pickAt {x, y, target, select, list?}`, `select.all|deselect|inverse|reselect`, `select.rect {x,y,width,height,mode,ellipse,antiAlias,feather}`, `select.lasso {points, mode, antiAlias, feather}`, `select.magicWand {x,y,tolerance,contiguous,antiAlias,sampleAllLayers,mode}`, `select.quick {points,size,mode,sampleAllLayers,enhanceEdge}`, `edit.transform {matrix}`, `image.crop {x,y,width,height,deleteCroppedPixels}` et `image.crop {}`, `document.pixel {x,y}`, `tools.setColors {foreground?, background?}`, `tools.swapColors`, `tools.defaultColors`, `edit.undo`, `edit.redo`. L'implémenteur de A2 RELIT `frontend/photolab/js/mod-*.js` (grep `executer(`, `post("/executer"`) pour compléter cette liste avant d'écrire le banc.

## Conventions (rappel)

Bancs Python : scripts `__main__`, `check(nom, cond)`, fin `=== N passed, M failed ===`, lancés depuis `backend/` avec `& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -X utf8 tests/<banc>.py` ; dossier de données temporaire (`tempfile.mkdtemp` + `DEEPOTUS_DATA_DIR`, `DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER`, comme `test_photolab_ecran_api.py`) ; faux moteur `backend/tests/faux_photocraft.py` branché par `PM.FABRIQUE` ; sections « VRAI moteur » rouges si le binaire manque. Bancs JS : `frontend/photolab/qa/<nom>.test.mjs` (fonctions PURES importées sous node, traducteur injecté `t = (c) => c`), lancés par `node qa/run.mjs` depuis `frontend/photolab/`. Textes : clés `photolab.*` dans `frontend/shared/i18n/photolab.json` (`{fr, en}`, français de référence), puis `python scripts/i18n_assembler.py` (régénère `frontend/shared/dz-i18n-dico.js` et sa copie `frontend/dist/shared/dz-i18n-dico.js`) ; dans le JS : `const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle)` ; données moteur/utilisateur affichées telles quelles marquées `data-dz-brut` (`brut(el)` de `mod-cycle.js`). CSS : aucune couleur en dur, uniquement `var(--…)` des jetons. `node --check` sur chaque module JS touché. Write/Edit pour tout fichier contenant `\n` ou `\` (jamais de heredoc bash). Ne JAMAIS lancer `tests/mutations_*.py`. **Aucun commit** : l'utilisateur dit « commit et ouvre la PR » à la fin ; chaque tâche se termine sur des bancs verts, sans `git commit`. Commentaires en français qui disent la raison.

## Fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/services/photolab_registre.py` (créé) | parseur de la grammaire `params`, registre structuré, liste blanche `verifier(...)` |
| `backend/app/services/photolab_moteur.py` (modifié) | `commande_autorisee` délègue à la liste blanche ; `registre(s)` mis en cache par génération ; `elaguer_inspect` ; `apercu(s, etapes, max_side)` ; `histogramme(s, sans, max_side)` |
| `backend/app/api/photolab_routes.py` (modifié) | `/executer` (liste blanche, kind de `setAdjustment`), `/commandes` (+ `champs`), `/inspecter` et `/historique` élagués, `POST /apercu`, `GET /histogramme` |
| `backend/tests/photocraft_commandes_0.3.0.json` (créé) | copie du registre réel (`scratchpad/t138/commands.json`) : banc hors ligne et faux moteur |
| `backend/tests/faux_photocraft.py` (modifié) | `engine.commands` rendu depuis la copie ; `image.duplicate`/`doc.close`/`doc.select {index}` déjà là (vérifier) |
| `backend/tests/test_photolab_registre.py` (créé) | parseur + liste blanche (hors ligne sur la copie du registre) |
| `backend/tests/test_photolab_apercu.py` (créé) | `/apercu`, `/histogramme`, élagage ; VRAI moteur : aperçu == application, original intact |
| `backend/tests/test_photolab_reglages_moteur.py` (créé) | VRAI moteur : écrit/compare `frontend/photolab/qa/fixtures/reglages-inspect.json` |
| `backend/tests/test_photolab_moteur.py` (modifié) | refus 3a-3d revus pour la liste blanche |
| `frontend/photolab/js/mod-champs.js` (créé) | PUR : champs → modèle de formulaire, coercition, libellés, « bientôt » |
| `frontend/photolab/js/mod-dialogue-reglage.js` (créé) | dialogue générique non modal avec aperçu moteur |
| `frontend/photolab/js/mod-courbes.js` (créé) | PUR + éditeurs Courbes et Niveaux (points, LUT, histogramme) |
| `frontend/photolab/js/mod-reglages.js` (créé) | calques de réglage : `depuisInspect`, onglet Réglages, éditeur dans Propriétés |
| `frontend/photolab/js/mod-styles.js` (créé) | dialogue Style de calque |
| `frontend/photolab/js/mod-menus.js`, `mod-calques.js`, `mod-proprietes.js`, `mod-vue.js`, `core.js`, `index.html`, `photolab.css` (modifiés) | branchements |
| `frontend/photolab/qa/champs.test.mjs`, `courbes.test.mjs`, `reglages.test.mjs`, `styles.test.mjs` (créés) ; `menus.test.mjs`, `textes.test.mjs`, `zones.test.mjs`, `panneaux.test.mjs` (modifiés) | bancs JS |
| `frontend/photolab/qa/fixtures/reglages-inspect.json` (créé, écrit par le banc A4) | paires paramètres envoyés ↔ `adjustment` de `doc.inspect`, 16 kinds |
| `frontend/shared/i18n/photolab.json` (+ réassemblage des deux `dz-i18n-dico.js`) | libellés des paramètres, des valeurs, des dialogues |

---

## Phase A — le pont

### Task A1 : parseur de la grammaire et registre structuré

**Files :** Create `backend/app/services/photolab_registre.py`, `backend/tests/photocraft_commandes_0.3.0.json` (copie octet pour octet de `scratchpad/t138/commands.json` ; vérifier qu'il contient 776 entrées), `backend/tests/test_photolab_registre.py`.

Porter `scratchpad/t138/grammaire.py` (lire le fichier ; le relevé §6 décrit la grammaire) dans `photolab_registre.py` avec ces corrections et cette API :

```python
# Un champ décrit par le registre du moteur. type ∈ number, int, bool, enum, color, str, layerId, index,
# docIndex, json, struct, intArray, union, ? ; les champs « opaques » (json, struct, intArray, union, ?) n'ont pas
# d'éditeur générique : l'écran ne les montre pas et le pont les borne en taille.
def parser(texte: str) -> dict:
    """{"ok": bool, "champs": [{cle, type, optionnel, defaut?, min?, max?, entier?, unite?, valeurs?, ouverte?, note?, brut?}], "inconnus": [...], "queue": str}"""

def structurer(commandes: list[dict]) -> dict[str, dict]:
    """id -> {"id", "label", "menu", "enabled", "champs"} pour tout le registre (une seule passe, ~776 entrées)."""
```

Corrections au portage : (1) une couleur `"#rrggbb"` OU `"#rrggbb|[r,g,b,a]"` → `{"type": "color", "formes": ["hex"]}` / `["hex", "rgba"]`, testée AVANT l'énumération ; (2) une énumération dont le dernier élément est `…` (U+2026) ou `...` → `{"type": "enum", "valeurs": [...sans …], "ouverte": True}` ; (3) `deg`, `px`, `%`, `mm`, `ppi`, `pt` → `number` avec `unite` ; `u32 i32 int u64` → `int` ; (4) le défaut en prose (`=foreground`, `=first library pattern`) reste `{"texte": …}` et n'est jamais envoyé.

Banc `test_photolab_registre.py` (rouge d'abord) :
1. Les 10 exemples bruts de « Faits établis » donnent les champs attendus (écrire chaque attendu en clair : `gaussianBlur` → `[{"cle":"radius","type":"number","min":0.1,"max":1000,"defaut":1,"optionnel":False}]` ; `addNoise.distribution` → enum `["uniform","gaussian"]` ; `seed` → int défaut 0 ; `edit.fill.color` → color `["hex","rgba"]` ; `layer.setProps.blend` → enum ouverte ; `levels.red` → json ; `layer.setAdjustment` → `[{"cle":"layer","type":"layerId","optionnel":True}]` + `inconnus` éventuel ; etc.).
2. Sur la copie du registre : `structurer` rend 776 ids ; pour les 75 filtres du menu Filtre (ids = `filter.*` dont `menu[0]` est le menu Filtre ; ou la liste T2 du relevé), les 16 `layer.newAdjustmentLayer.*`, les 23 `image.adjustments.*` (colorLookup.list compris) et les 19 `layer.layerStyle.*` + `style.presets.*` : `ok` est vrai (aucun inconnu) ; compter et ÉCRIRE dans le banc le nombre total d'`ok` faux (attendu 138, à confirmer ; le banc échoue si ce nombre CHANGE, pour attraper une régression du parseur).
3. Aucun champ du périmètre P3 n'est de type `?`.

- [ ] Step 1 : copier la fixture, écrire le banc ; le lancer → rouge (module absent).
- [ ] Step 2 : écrire `photolab_registre.py` ; banc vert.

### Task A2 : liste blanche à la place de la liste de refus

**Files :** Modify `backend/app/services/photolab_registre.py` (+ `verifier`), `backend/app/services/photolab_moteur.py` (`commande_autorisee`, `registre(s)`, `elaguer_inspect`), `backend/app/api/photolab_routes.py` (`/executer`, `/commandes`, `/inspecter`, `/historique`), `backend/tests/faux_photocraft.py`, `backend/tests/test_photolab_moteur.py` (3a-3d), `backend/tests/test_photolab_registre.py` ; `frontend/photolab/js/mod-menus.js` + `qa/menus.test.mjs` 7.1 si `PREFIXES_REFUSES` change.

Règles de `verifier(registre, cid, params, kind=None) -> dict` (rend les params tels quels si admis ; lève `ValueError(message français)` sinon) :
1. `cid` lisible (`_ID_COMMANDE` actuel) ET présent dans le registre (« commande inconnue du moteur »).
2. Refus par famille, CONSERVÉS et complétés : `PREFIXES_REFUSES` actuel (`file. app. automate. plugin. script window. help. edit.preferences edit.presets edit.keyboardshortcuts edit.menus`) + `image.mode.` + `brush.presets.import` + `gradient.presets.import` + `prefs.` + `measurementlog.export` (comparaison en minuscules, comme aujourd'hui). Garder la déclaration `PREFIXES_REFUSES = (...)  # …` sur le même motif (regex du banc JS 7.1) et recopier la liste dans `REFUSES` de `mod-menus.js`.
3. `params` dict (None → `{}`). Clés admises = clés des `champs` de la commande ; en plus `layer` et `enabled` pour `layer.layerStyle.<kind>` ; pour `layer.setAdjustment` : `layer` + les champs de `layer.newAdjustmentLayer.<kind>` où `kind` est passé par l'appelant (voir 6). Toute autre clé → « paramètre inconnu : <clé> ».
4. Valeurs selon le type du champ : `number` → nombre fini (pas booléen), dans `[min, max]` s'il y a des bornes (hors bornes → refus, message avec les bornes), entier si `entier` ; `int`, `layerId`, `index`, `docIndex` → entier (≥ 0 pour les trois derniers) ; `bool` → vrai booléen ; `enum` fermée → valeur de la liste ; `enum` ouverte → chaîne ≤ 64 car. ; `color` → `"#rrggbb"` (regex), ou, si `"rgba"` ∈ formes, liste de 3 ou 4 nombres dans 0..255 ; `str` → chaîne ≤ 256 car. et la clé n'est pas dans `CLES_CHEMIN = {"path","file","mappath","dir","directory","folder","input","output","droplet","script","data"}` (comparaison en minuscules) ; opaques (`json struct intArray union ?`) → profondeur ≤ 6, ≤ 5000 feuilles, chaînes ≤ 64 car., aucune clé de `CLES_CHEMIN` à aucun niveau.
5. Défense en profondeur gardée : toute chaîne, à tout niveau, qui « ressemble à un fichier » (`_valeur_fichier` actuel : `/`, `\`, `X:`, extensions) est refusée — SAUF une valeur d'énumération fermée validée. Toute clé `blend` (à tout niveau) doit être une chaîne qui, normalisée (minuscules, sans espaces/tirets/soulignés/parenthèses), égale un des 28 ids normalisés ou un libellé anglais normalisé (« lineardodgeadd ») — sinon refus (le moteur accepterait `3` sans rien faire).
6. `layer.setAdjustment` : la route lit `doc.inspect`, trouve le calque `params.layer` (ou `activeLayer`), prend la variante de `adjustment` (`"Levels"` → `levels`, chaîne `"Invert"` → `invert` ; table `KINDS` variante→kind dans `photolab_registre.py`) et appelle `verifier(..., kind=kind)` ; calque sans `adjustment` → 400 « le calque n'est pas un calque de réglage ».

`photolab_moteur.py` : `commande_autorisee(cid, params, registre=None, kind=None)` garde sa signature d'appel actuelle compatible (si `registre` est None → ancien comportement INTERDIT : lever `ValueError("registre du moteur indisponible")`) ; `registre(s)` = `structurer(appeler engine.commands)` mis en cache par génération de session (une seule lecture par démarrage du moteur). `elaguer_inspect(doc)` : remplace, dans tout calque (récursif dans `children`), `adjustment.ColorLookup.lut` par `None` et ajoute `"lutElague": True`.

Routes : `/executer` → `PM.commande_autorisee(cid, params, PM.registre(s), kind)` ; `/commandes` → chaque entrée gagne `"champs"` (liste de `structurer`) ; `/inspecter` et la réponse de `/historique` passent par `elaguer_inspect`.

Faux moteur : `engine.commands` rend le contenu de `backend/tests/photocraft_commandes_0.3.0.json`.

Banc (`test_photolab_registre.py`, section liste blanche, hors ligne sur la fixture) :
- Admises (une ligne par commande P2 de « Faits établis », paramètres réalistes) : toutes passent.
- Admises P3 : `filter.blur.gaussianBlur {radius: 4}` ; `layer.layerStyle.innerGlow {source:"center", layer: 3, enabled: True}` ; `layer.newAdjustmentLayer.colorLookup {lut:"tealOrange"}` ; `image.adjustments.channelMixer {red:[100,0,0,0], monochrome: False}` ; `image.adjustments.levels {inBlack: 10, red: {outWhite: 200}}` ; `layer.setProps {blend:"linearDodge"}` et `{blend:"Linear Dodge (Add)"}` ; `layer.setAdjustment {layer: 3, gamma: 1.4}` avec `kind="levels"` ; `filter.lensCorrection {profile:"auto"}`.
- Refusées (message vérifié pour chacune) : `image.mode.rgb {profile:"C:/x.icc"}` (famille) ; `plugin.install {path:"x.wasm"}` ; `brush.presets.importAbr {path:"../a.abr"}` ; `prefs.set {path:"a.b", value:1}` ; `layer.newAdjustmentLayer.colorLookup {file:"../x.cube"}` ; `{lut:"../x.cube"}` (énumération) ; `{data:{"text":"…"}}` ; `filter.distort.displace {mapPath:"m.psd"}` ; `filter.blur.gaussianBlur {radius:"2"}` (type) ; `{radius: 5000}` (bornes) ; `{radius: 4, zorglub: 1}` (inconnue) ; `layer.setProps {blend: 3}` et `{blend:"zorg"}` ; `layer.setAdjustment {points:[[0,0],[255,255]]}` avec `kind="levels"` ; une commande absente du registre `filter.zorg {}` ; `layer.renameLayer {name:"C:\\x.png"}` (valeur-fichier).
- `elaguer_inspect` : un document factice avec un calque Color Lookup portant `lut: [0.1]*1000` dans un groupe → `lut` None, `lutElague` True, les autres clés intactes.

`test_photolab_moteur.py` 3a-3d : réécrire les cas selon ces règles (les cas « colorLookup lut ../x.cube » et « lut {file} » restent REFUSÉS, `levels {"lightness":{"outBlack":60}}` reste admis car `lightness` est… à vérifier dans le registre : s'il n'est pas une clé du registre de `image.adjustments.levels`, le cas devient refusé et le banc le dit). Relancer `test_photolab_routes.py`, `test_photolab_ecran_api.py`, `test_photolab_fidelite.py`, `qa/run.mjs` (menus 7.1) : verts.

- [ ] Step 1 : bancs rouges (liste blanche, élagage, 3a-3d revus).
- [ ] Step 2 : implémenter ; tous les bancs `test_photolab_*.py` et `node qa/run.mjs` verts.

### Task A3 : aperçu sur copie et histogramme

**Files :** Modify `backend/app/services/photolab_moteur.py`, `backend/app/api/photolab_routes.py`, `backend/tests/faux_photocraft.py` (si besoin) ; Create `backend/tests/test_photolab_apercu.py`.

Contrats :
1. `POST /api/photolab/apercu {"etapes": [{"command", "params"}…] (1 à 12), "maxSide": 64..2048 = 1024}` → chaque étape passe `commande_autorisee` AVANT tout appel moteur (une étape refusée → 400, aucun appel) ; seules sont admises les familles `filter.`, `image.adjustments.`, `layer.layerStyle.`, `layer.setAdjustment`, `layer.setProps` (sinon 400 « aperçu impossible pour cette commande »). Service `apercu(s, etapes, max_side)` sous UNE `s.sequence` : `session.list` (index de l'original) ; `doc.inspect` (position du calque actif dans l'arbre `layers`, aplati en préordre comme `vignettes`) ; `image.duplicate {"name": "dz-apercu"}` ; `doc.inspect` de la copie → `layer.select {layer: <id à la même position>, mode:"replace"}` ; les étapes, dont l'id `layer` éventuel est TRADUIT de l'original vers la copie par position (sinon un style viserait un mauvais calque) ; `doc.render {maxSide, path:"rendus/apv-<gen>-<n>.png"}` ; dans un `finally` : `doc.close {index: <index copie>}` puis `doc.select {index: <index original>}`. Rend `{"url": "/api/photolab/rendus/apv-….png", "ms": …, "resultats": [result de chaque étape]}` (le `result.filter` d'un filtre donne les valeurs réellement appliquées). Trois aperçus `apv-*` gardés au plus (les plus anciens supprimés). Une étape refusée PAR LE MOTEUR → 422 avec son message, et la copie est fermée quand même.
2. `GET /api/photolab/histogramme?maxSide=256&sans=<id>` (maxSide 64..1024 ; `sans` facultatif = id d'un calque de l'ORIGINAL à masquer, ex. le calque de réglage en cours d'édition) → même séquence sur copie : `layer.setProps {layer: <id traduit>, visible:false}` si `sans`, `doc.render`, fermeture ; Pillow : `{"r":[256], "g":[256], "b":[256], "l":[256]}` (l = luminance `round(0.299 R + 0.587 G + 0.114 B)`, pixels d'alpha nul ignorés).

Banc `test_photolab_apercu.py` :
- [1] faux moteur : une étape non admise (`layer.delete`) → 400 sans appel (le compteur `dz.compte` ne bouge pas) ; une étape avec `{radius:"2"}` → 400 ; maxSide 32 → 422/400 ; quatre aperçus de suite → trois fichiers `apv-*` restent ; la copie est fermée même si `dz.erreur` est injecté dans l'étape (le faux moteur ne garde qu'un document à la fin).
- [2] VRAI moteur, document 400×300 : nuages (`filter.render.clouds {seed: 7}`), un calque « haut » rempli dans un rectangle, un calque vide au-dessus, calque actif = « haut », sélection elliptique progressive (`select.rect {…, ellipse: True, feather: 8}`) : `apercu([gaussianBlur r=12])` PUIS `executer gaussianBlur r=12` + `/rendu` au même maxSide → les deux PNG sont identiques à l'octet ; et AVANT l'exécution : `doc.inspect` de l'original identique (même `revision`, `activeLayer`, `selectionBounds`, `canRedo`, `history`) à celui d'avant l'aperçu. Même vérification avec `[image.adjustments.levels {inBlack: 40}]` et `[layer.layerStyle.dropShadow {layer: <id haut>, distance: 12, color:"#0000ff"}]` (l'id de l'original est bien traduit : l'ombre apparaît sur « haut », pas sur le calque du haut). `session.list` après : un seul document.
- [3] VRAI moteur : histogramme d'un document blanc 64×64 → `l[255] == 4096`, somme 4096 ; avec un calque de réglage Inverser et `sans=<id>` → toujours blanc ; sans `sans` → `l[0] == 4096`.

- [ ] Step 1 : banc rouge ; Step 2 : implémenter ; vert ; relancer les autres `test_photolab_*.py`.

### Task A4 : table de conversion inspect → paramètres, sur le vrai moteur

**Files :** Create `backend/tests/test_photolab_reglages_moteur.py`, `frontend/photolab/qa/fixtures/reglages-inspect.json` (écrit par le banc avec `--ecrire`).

Le banc, VRAI moteur, document 64×64 : pour chacun des 16 kinds, un jeu de paramètres NON par défaut écrit en clair dans le banc (ex. levels `{inBlack:20, gamma:1.3, inWhite:230, outBlack:5, outWhite:250, red:{inBlack:10}}` ; curves `{points:[[0,0],[64,40],[192,220],[255,255]], blue:[[0,0],[128,150],[255,255]]}` ; hueSaturation `{hue:25, saturation:-10, lightness:5, reds:{hue:10, saturation:5, lightness:0}}` ; colorBalance `{shadows:[10,-5,0], midtones:[0,0,20], highlights:[-10,0,0], preserveLuminosity:false}` ; blackWhite `{reds:50, tint:true, tintColor:"#c08040"}` ; photoFilter `{filter:"cooling80", density:40}` ; channelMixer `{red:[80,20,0,0], green:[0,100,0,0], blue:[0,0,100,0]}` ; posterize `{levels:6}` ; threshold `{level:100}` ; gradientMap `{stops: …}` (forme exacte lue dans la note du registre puis vérifiée) ; selectiveColor `{method:"absolute", reds:{cyan:10, magenta:0, yellow:-5, black:0}}` ; colorLookup `{lut:"warm"}` ; exposure, vibrance, brightnessContrast, invert). Pour chaque kind : `layer.newAdjustmentLayer.<kind>` avec ces paramètres, `doc.inspect`, et on garde `{"kind", "envoye": params, "adjustment": <adjustment élagué>, "lut_list": colorLookup.list}`. Vérification de l'aller-retour : un `layer.setAdjustment` avec les paramètres envoyés NE change pas le rendu (empreinte identique) — preuve que les paramètres décrivent bien l'état. Avec `--ecrire`, écrit `frontend/photolab/qa/fixtures/reglages-inspect.json` (JSON trié, indenté) ; sans, compare au fichier et échoue sur tout écart (le moteur épinglé ne doit pas bouger).

- [ ] Step 1 : écrire le banc ; `--ecrire` ; relancer sans `--ecrire` : vert.

---

## Phase B — l'écran

### Task B1 : champs → formulaire (PUR) et branchement des menus

**Files :** Create `frontend/photolab/js/mod-champs.js`, `frontend/photolab/qa/champs.test.mjs` ; Modify `frontend/photolab/js/mod-menus.js`, `frontend/photolab/qa/menus.test.mjs`.

Fonctions PURES de `mod-champs.js` (écrire les bancs d'abord, champs factices recopiés du registre) :

```js
// Clés que l'écran ne montre jamais : elles désignent la cible ou une variante d'appel, pas un réglage.
export const CLES_CACHEES = new Set(["layer", "add", "enabled", "list", "wait"]);
// D9 : interfaces lourdes écartées au départ (grisées « bientôt »).
export const D9 = new Set(["filter.cameraRaw", "filter.liquify", "filter.vanishingPoint", "filter.adaptiveWideAngle", "layer.smartObjects.puppetWarp"]);
export const OPAQUES = new Set(["json", "struct", "intArray", "union", "?"]);

// Un champ montré à l'écran : tout sauf les clés cachées et les opaques.
export function champsVisibles(champs) { return (champs || []).filter((c) => !CLES_CACHEES.has(c.cle) && !OPAQUES.has(c.type)); }
// « bientôt » : D9, ou un champ requis (non optionnel, sans défaut) que l'écran ne sait pas éditer.
export function sansEcran(id, champs) {
  if (D9.has(id)) return true;
  return (champs || []).some((c) => !c.optionnel && c.defaut === undefined && OPAQUES.has(c.type) && !CLES_CACHEES.has(c.cle));
}
// Contrôle de chaque champ : curseur+nombre (borné), nombre (unité ou entier), liste, case, couleur, texte.
export function controleDe(c) {
  if (c.type === "number" && c.min !== undefined) return "curseur";
  if (c.type === "number" || c.type === "int") return "nombre";
  if (c.type === "enum") return "liste";
  if (c.type === "bool") return "case";
  if (c.type === "color") return "couleur";
  return "texte";
}
// Valeur initiale : la valeur connue, sinon le défaut numérique/booléen/chaîne du registre, sinon un neutre.
export function valeurInitiale(c, connue) { /* connue ?? défaut (sauf {texte}) ?? min-borné-à-0 pour curseur ?? false ?? 1re valeur ?? "#000000" ?? "" */ }
// Coercition à l'envoi : nombre fini borné (entier si entier/int), bool strict, enum dans la liste, couleur #rrggbb.
export function coercer(c, brut) { /* … */ }
// Paramètres à envoyer : uniquement les champs visibles (les opaques restent au défaut du moteur).
export function parametres(champs, valeurs) { /* {cle: coercer(c, valeurs[cle])} pour champsVisibles */ }
// Libellé d'un paramètre : dico photolab.param.<cle>, sinon la clé camelCase en mots (« blurAngle » → « Blur angle »).
export function libelleParam(cle, t) { /* t("photolab.param."+cle) !== clé ? traduit : humaniser(cle) */ }
export function libelleValeur(v, t) { /* t("photolab.valeur."+v) sinon humaniser(v) */ }
export function humaniser(cle) { /* séparer avant chaque majuscule, première lettre majuscule, reste minuscule */ }
// Pas du curseur : 0,01 si l'écart ≤ 2 ou des bornes décimales, 0,1 si ≤ 20 non entier, sinon 1.
export function pasDe(c) { /* … */ }
```

Le corps de chaque fonction est à écrire complet par l'implémenteur ; le banc `champs.test.mjs` fixe (au moins 30 vérifications) : `champsVisibles` sur `gaussianBlur`, `addNoise` (4 visibles), `levels` (5 visibles, `red/green/blue` cachés), styles (`layer`, `add`, `enabled` cachés) ; `sansEcran` vrai pour les 4 D9 + `filter.filterGallery` (`effects` json requis) + `filter.distort.displace` si `mapDocument` est requis (lire la fixture), faux pour `filter.blur.gaussianBlur`, `filter.lensCorrection`, `filter.render.lightingEffects` (opaques optionnels) ; `controleDe` pour chaque type ; `coercer` : `"12.7"` → 12.7, `5000` → borné à `max`, `NaN` → défaut, `true` pour bool, `"zorg"` → 1re valeur d'enum, `"#ABCDEF"` → `"#abcdef"` ; `parametres` ne rend jamais une clé cachée ni opaque ; `humaniser("blurAngle") === "Blur angle"`, `humaniser("cooling80") === "Cooling80"` ; `pasDe` (0..1 → 0.01, 0.1..1000 → 0.1, 0..255 entier → 1).

Branchement dans `mod-menus.js` :
- `construireMenus` reçoit le registre AVEC `champs` (route A2) ; chaque entrée commande gagne `champs`.
- `etatDe` : `sansEcran(id, champs)` → `bientot` (avant les autres règles sauf `TRAITES_PAR_ECRAN`).
- `actionEntree` : `"dialogue"` si `champsVisibles(champs).length > 0` ; sinon `"executer"` (une commande dont tous les champs sont cachés ou optionnels opaques s'exécute directement, ex. `layer.layerMask.revealAll`). Supprimer `parametresRequis` et son banc ; mettre à jour `menus.test.mjs` 8.6 (Flou gaussien → `"dialogue"` par ses champs ; Révéler tout → `"executer"`).
- `activer` : `executer` passe par `PL.executer(e.id, {})` (file FIFO, cycle inclus) au lieu de `PL.post` direct ; `dialogue` appelle `PL.ouvrirReglage(e)` (défini en B2 ; tant que B2 n'existe pas, garder le message « p3 » derrière `if (!PL.ouvrirReglage)`).
- Les familles sur mesure sont aiguillées AVANT le générique : `image.adjustments.curves` / `image.adjustments.levels` → `PL.ouvrirCourbes(e)` / `PL.ouvrirNiveaux(e)` (B3) ; `layer.newAdjustmentLayer.*` → `PL.creerReglage(kind)` (B4) ; `layer.layerStyle.<kind>` (les 10 styles et `blendingOptions`) → `PL.ouvrirStyles(kind)` (B5). Écrire cet aiguillage comme fonction PURE `aiguillage(id)` → `"courbes"|"niveaux"|"reglage"|"style"|"generique"` bancée.

- [ ] Step 1 : `champs.test.mjs` + `menus.test.mjs` revus, rouges ; Step 2 : implémenter ; `node --check` des modules ; `node qa/run.mjs` vert.

### Task B2 : le dialogue générique avec aperçu moteur

**Files :** Create `frontend/photolab/js/mod-dialogue-reglage.js` ; Modify `frontend/photolab/js/core.js` (init), `frontend/photolab/js/mod-vue.js` (aperçu), `frontend/photolab/photolab.css`, `frontend/photolab/qa/` (bancs des fonctions pures ajoutées) ; lire l'inventaire A6 (look du dialogue « Flou gaussien » de photocraft : titre, case « Aperçu », curseur + champ numérique + unité, boutons OK / Annuler, Réinitialiser au clic Alt sur Annuler) et reprendre sa disposition dans nos jetons.

Comportement :
- `PL.ouvrirReglage(entree)` : boîte NON modale `.pl-dlg.pl-reglage` (pas de voile ; placée en haut à droite de `#scene`, déplaçable par sa tête), une seule ouverte à la fois ; titre = libellé de l'entrée sans « … » ; un contrôle par champ visible (libellé `libelleParam`, curseur `<input type=range>` + `<input type=number>` liés, unité affichée `px`/`°`/`%`, liste dont les options passent par `libelleValeur`, case, `<input type=color>`) ; case « Aperçu » cochée par défaut ; boutons « Annuler » (Alt enfoncé → libellé « Réinitialiser » et remet les défauts), « OK » (principal). Échap = Annuler, Entrée = OK ; les touches ne fuient pas vers les raccourcis.
- Aperçu : seulement pour les familles `filter.` et `image.adjustments.` ; à chaque changement (relâchement d'un curseur, saisie validée, liste, case), après 250 ms sans autre changement : `POST /apercu {etapes:[{command, params: parametres(...)}], maxSide: PL.vue.maxSideVoulu()}` ; une seule requête en vol, la plus récente gagne (réutiliser `fileUnique` de `mod-cycle.js` ou une fonction pure équivalente `derniereGagne` bancée) ; l'image reçue s'affiche par `PL.vue.poserApercu(image)` (nouveau dans `mod-vue.js` : pose l'image comme rendu courant SANS toucher à `PL.etat.doc`) ; décocher « Aperçu » → `PL.cycle()` (rendu réel). Pendant le calcul : indicateur discret dans la tête du dialogue (`aria-busy`). Les valeurs effectivement appliquées (`resultats[0].filter`) remplacent celles du formulaire si elles diffèrent (bornage du moteur).
- OK → `PL.executer(id, params)` (file FIFO, puis cycle) et fermeture ; Annuler → fermeture + `PL.cycle()` si un aperçu a été posé.
- Une erreur d'aperçu (422) s'affiche dans `.pl-erreur` du dialogue sans le fermer.

CSS : styles de `input[type=range]` (piste `--stroke`, pouce `--accent`), `.pl-reglage` (largeur 320 px, ombre et fond des panneaux), aucune couleur en dur.

Banc JS : les fonctions pures ajoutées (`derniereGagne`, `positionInitiale(scene, boite)`, `estFamilleApercu(id)`) ; `zones.test.mjs` reste vert (aucune section ajoutée).

- [ ] Step 1 : bancs rouges ; Step 2 : implémenter ; `node --check` ; `node qa/run.mjs` vert.

### Task B3 : textes des paramètres, des valeurs et des dialogues

**Files :** Modify `frontend/shared/i18n/photolab.json`, régénérer les deux `dz-i18n-dico.js` (`python scripts/i18n_assembler.py`) ; Modify `frontend/photolab/qa/textes.test.mjs` ; Create une section dans `backend/tests/test_photolab_registre.py` (« libellés »).

- Pour CHAQUE clé visible (au sens de `champsVisibles`) des commandes du périmètre (75 filtres du menu sauf D9 et « bientôt », 22 `image.adjustments.*`, 16 `layer.newAdjustmentLayer.*`, 10 styles + `blendingOptions` + `globalLight`) : une entrée `photolab.param.<cle>` `{fr, en}` ; pour chaque valeur d'énumération fermée de ces champs : `photolab.valeur.<valeur>` (une valeur partagée entre commandes n'a qu'une entrée ; choisir le sens le plus courant). Français : prendre le libellé de l'amont dans `scratchpad/t138/fr.tsv` (empreinte git 453fa2ad21254713c30f12d9a3ac017d1e3ded05 ; format `contexte\tanglais\tfrançais` ; anglais = clé humanisée, ex. `Radius` → `Rayon`, `Amount` → `Quantité`, `Threshold` → `Seuil`) ; à défaut, traduire soi-même au plus près du vocabulaire Photoshop français. Anglais : le libellé anglais de l'amont (fr.tsv colonne 2) ou la clé humanisée.
- Textes des dialogues : `photolab.reglage.apercu` (« Aperçu »), `.ok`, `.annuler`, `.reinitialiser`, `.calcul` (« Calcul de l'aperçu… »), `.erreur_apercu`, `photolab.reglages.*` (onglet Réglages, en-têtes de Propriétés), `photolab.courbes.*`, `photolab.niveaux.*`, `photolab.styles.*` (titres des 10 styles si le catalogue ne les a pas déjà, « Options de fusion », « Aperçu », « Paramètres non relisibles : valeurs par défaut affichées »), `photolab.kind.<kind>` (16 noms de réglages). Retirer `photolab.menu.p3` quand B1 n'y fait plus référence.
- Banc `test_photolab_registre.py` « libellés » (hors ligne, fixture du registre + `photolab.json`) : toute clé visible et toute valeur d'énumération fermée du périmètre ont leur entrée fr ET en non vides ; aucune entrée `photolab.param.*` ou `photolab.valeur.*` orpheline (absente du périmètre).
- `qa/textes.test.mjs` : recenser les familles composées `photolab.param.`, `photolab.valeur.`, `photolab.kind.`.
- Relancer `test_photolab_textes.py` et `test_i18n_l0.py` (assemblage à jour) : verts.

- [ ] Step 1 : banc « libellés » rouge ; Step 2 : dictionnaire + assemblage ; verts.

### Task B4 : Courbes et Niveaux sur mesure

**Files :** Create `frontend/photolab/js/mod-courbes.js`, `frontend/photolab/qa/courbes.test.mjs` ; Modify `photolab.css`, `core.js`.

Fonctions PURES (bancs d'abord, ≥ 40 vérifications) :
- `lutNiveaux({inBlack, gamma, inWhite, outBlack, outWhite})` → `Uint8ClampedArray(256)` : `x = clamp((v - inBlack) / (inWhite - inBlack), 0, 1)` ; `y = x ** (1 / gamma)` ; `round(outBlack + y * (outWhite - outBlack))`. (Aperçu de geste seulement ; le moteur fait foi au relâchement.)
- `lutCourbe(points)` (points `[[in,out]…]` 0..255, triés) → 256 valeurs par interpolation monotone (Fritsch-Carlson) ; constante avant le premier et après le dernier point.
- `ajouterPoint(points, x, y)` (refus si < 4 unités d'un x existant ou déjà 19 points), `deplacerPoint(points, i, x, y)` (x strictement entre les voisins, bornes 0..255, extrémités : x figé), `retirerPoint(points, i)` (jamais en dessous de 2 points ; les extrémités ne se retirent pas).
- `appliquerLuts(donnees, {r, g, b})` sur un `ImageData`-like `{data, width, height}` (alpha intact) — pour l'aperçu pendant le glisser, appliqué à une COPIE des pixels du dernier rendu moteur (canevas hors écran) puis posé par `PL.vue.poserApercu`.
- `cheminHistogramme(h, largeur, hauteur)` → chaîne `d` de `<path>` (échelle racine carrée, comme photocraft) ; `normaliserNiveaux(v)` (contraintes `inBlack ≤ inWhite - 2`, gamma 0.01..9.99, bornes du registre) ; `gammaDepuisCurseur(pos, noir, blanc)` et l'inverse pour le curseur gris du milieu.

Écrans :
- `PL.ouvrirCourbes(entree, cible?)` / `PL.ouvrirNiveaux(entree, cible?)` : dialogue non modal (même boîte que B2) ; sélecteur de canal RVB / Rouge / Vert / Bleu (→ `points` ou `red/green/blue`) ; Courbes : grille 256×256 en SVG, diagonale, histogramme (`GET /histogramme`) en fond, points déplaçables (glisser = aperçu JS par `appliquerLuts` ; relâcher = aperçu moteur `/apercu`), clic sur la courbe = ajouter, double-clic / glisser hors de la grille = retirer, champs Entrée/Sortie du point actif ; Niveaux : histogramme, trois curseurs d'entrée (noir, gris = gamma, blanc) + deux de sortie, champs numériques liés. OK → `PL.executer("image.adjustments.curves"|"…levels", params)`. `cible` (B4/B5 : calque de réglage) remplace l'aperçu/OK par `layer.setAdjustment` (voir B5).
- Raccourcis : Ctrl+M et Ctrl+L passent déjà par `PL.menus.activer` → l'aiguillage B1 les mène ici.

- [ ] Step 1 : `courbes.test.mjs` rouge ; Step 2 : implémenter ; `node --check` ; `node qa/run.mjs` vert.

### Task B5 : calques de réglage — Réglages et Propriétés

**Files :** Create `frontend/photolab/js/mod-reglages.js`, `frontend/photolab/qa/reglages.test.mjs` ; Modify `mod-proprietes.js`, `mod-calques.js`, `core.js`, `index.html` (onglets DANS `#grpProprietes`, aucune `<section>` ni bouton de rail ajouté), `photolab.css` (`#grpProprietes` : hauteur souple bornée + défilement au lieu de 170 px fixes ; vérifier les cotes figées de `zones.test.mjs`), `qa/panneaux.test.mjs`.

Fonctions PURES (bancs d'abord) :
- `KINDS` : les 16 kinds dans l'ordre de photocraft avec `{kind, variante: "Levels"…, icone, cle: "photolab.kind.<kind>"}` ; `kindDe(calque)` : variante de `calque.adjustment` (chaîne `"Invert"` comprise) → kind, sinon `null`.
- `depuisInspect(kind, adjustment, lutList)` → paramètres de commande (table de « Faits établis »). Banc : pour CHAQUE entrée de `qa/fixtures/reglages-inspect.json` (A4), `depuisInspect(kind, adjustment, lut_list)` égale `envoye` à l'arrondi près (tolérance 1 sur 0..255, 0,01 sur gamma, exact pour bool/enum ; photoFilter : `color` attendu à la place de `filter`) — 16 cas.
- `difference(avant, apres)` → seulement les clés changées (comparaison profonde) : c'est ce qu'envoie `layer.setAdjustment` (le moteur fusionne).

Écrans :
- Onglets dans `#grpProprietes` : « Propriétés » | « Réglages ». « Réglages » = grille de 16 boutons (icône + infobulle `photolab.kind.*`) qui appellent `PL.creerReglage(kind)` → `PL.executer("layer.newAdjustmentLayer."+kind, {})` (valeurs par défaut du moteur), puis bascule sur « Propriétés ».
- « Propriétés » d'un calque de réglage actif (`kindDe` non nul) : en-tête icône + nom du kind ; éditeur : Courbes / Niveaux = l'éditeur de B4 intégré au panneau (mêmes fonctions, `cible = calque`), les 14 autres = formulaire généré (`champsVisibles` de `layer.newAdjustmentLayer.<kind>`, valeurs initiales `depuisInspect`) ; plus les champs « par canal » utiles écrits à la main : Teinte/Saturation (sélecteur de gamme Global/Rouges/…/Magentas → `reds…` `{hue,saturation,lightness}`), Balance des couleurs (Tons : Ombres/Tons moyens/Tons clairs, trois curseurs Cyan–Rouge, Magenta–Vert, Jaune–Bleu de -100 à 100), Mélangeur de couches (sortie Rouge/Vert/Bleu, 4 curseurs -200..200), Couleur sélective (gamme + 4 curseurs). Chaque relâchement → `PL.executer("layer.setAdjustment", {layer: id, ...difference(avant, apres)})` (cycle normal : le rendu moteur EST l'aperçu ; pendant le glisser des Courbes/Niveaux, l'aperçu JS de B4) ; histogramme des Niveaux = `GET /histogramme?sans=<id du calque>`.
- Calques : une ligne de calque de réglage montre l'icône de son kind à la place de la vignette ; double-clic sur l'icône → onglet Propriétés ; pied : `bReglage` actif → petit menu des 16 kinds (même `PL.creerReglage`).
- Menu Calque › Nouveau calque de réglage › X et Image › Réglages (destructifs) restent distincts : le premier crée le calque (B1 → `PL.creerReglage`), le second ouvre le dialogue (générique, ou Courbes/Niveaux).
- `colorLookup` : la liste des LUT vient de `PL.executer("image.adjustments.colorLookup.list", {}, {cycle:false})` (une fois) ; `data`/`file` jamais montrés.

- [ ] Step 1 : `reglages.test.mjs` + `panneaux.test.mjs` revus, rouges ; Step 2 : implémenter ; `node --check` ; `node qa/run.mjs` vert.

### Task B6 : Style de calque

**Files :** Create `frontend/photolab/js/mod-styles.js`, `frontend/photolab/qa/styles.test.mjs` ; Modify `mod-calques.js` (`bFx` actif, badge « fx » d'une ligne qui a des effets), `core.js`, `photolab.css`.

Fonctions PURES (bancs d'abord) :
- `STYLES` : les 10 kinds dans l'ordre du dialogue de photocraft (`blendingOptions` en tête, puis bevelEmboss, stroke, innerShadow, innerGlow, satin, colorOverlay, gradientOverlay, patternOverlay, outerGlow, dropShadow — vérifier l'ordre dans l'inventaire B §4 / `layer_style.rs` et le corriger si besoin) avec le libellé `kind` de `doc.inspect` (« Drop Shadow »…).
- `etatStyles(memoire, effetsInspect)` : fusionne ce que l'écran a gardé (`PL.etat.styles[cleDoc][idCalque][kind] = {actif, params}`) avec `effects.items` du moteur : un kind présent au moteur mais inconnu de la mémoire (document rouvert) → `{actif: item.enabled, params: défauts, inconnu: true}`.
- `etapesStyles(avant, apres, idCalque)` → liste minimale d'étapes : kind activé ou modifié → `layer.layerStyle.<kind> {layer, ...params complets}` ; kind désactivé alors qu'il était actif → `{layer, enabled:false, ...params complets}` (le moteur remplace : il faut tout renvoyer) ; options de fusion changées → `layer.layerStyle.blendingOptions {layer, blend, opacity, fillOpacity}` ; rien de changé → `[]`. Banc : 8 cas (aucun changement, un ajout, une modification d'un seul paramètre = tous les paramètres renvoyés, une désactivation, deux kinds, options de fusion, mode de fusion validé contre `MODES_FUSION`, couleur normalisée).

Écran : `PL.ouvrirStyles(kindInitial?)` (depuis le menu Calque › Style de calque › X, le bouton fx, ou le double-clic sur le badge fx) : dialogue LARGE non modal (colonne gauche : « Options de fusion » + les 10 styles avec case à cocher, colonne droite : formulaire du style sélectionné généré par `champsVisibles` de `layer.layerStyle.<kind>`, `blend` présenté comme une liste des modes de `MODES_FUSION`), case « Aperçu » ; chaque changement (250 ms) → `/apercu {etapes: etapesStyles(initial, courant, id)}` ; OK → les étapes une à une par `PL.executer(..., {cycle:false})` puis `PL.cycle()`, et la mémoire `PL.etat.styles` mise à jour ; un style marqué `inconnu` affiche la mention « Paramètres non relisibles : valeurs par défaut affichées ». Sans calque actif, ou calque d'arrière-plan verrouillé : le moteur accepte (comme l'original) — ne rien interdire de plus.

- [ ] Step 1 : `styles.test.mjs` rouge ; Step 2 : implémenter ; `node --check` ; `node qa/run.mjs` vert.

---

## Phase C — finition

### Task C1 : mutations, balayage, preuve, compte rendu

- [ ] **Mutations** (sources copiées dans `scratchpad/t138/mut-src/` AVANT, comparées par `cmp` APRÈS ; script de mutation dans le scratchpad, restauration retentée et vérifiée ; jamais `tests/mutations_*.py`) : au moins 14 mutants, chacun doit rougir son banc : (1) `verifier` n'exige plus que la commande soit au registre ; (2) n'exige plus que la clé soit connue ; (3) oublie les bornes ; (4) accepte une chaîne pour un nombre ; (5) retire `image.mode.` des familles refusées ; (6) retire `data` de `CLES_CHEMIN` ; (7) accepte `blend: 3` ; (8) `apercu` ne repose plus le calque actif par position ; (9) `apercu` ne traduit plus l'id `layer` des étapes ; (10) `apercu` oublie `doc.select` de l'original ; (11) `elaguer_inspect` ne descend plus dans `children` ; (12) `depuisInspect` levels ne multiplie plus par 255 ; (13) `etapesStyles` n'envoie que le paramètre modifié ; (14) `sansEcran` oublie D9 ; (15) `lutCourbe` linéaire au lieu de monotone ; (16) `actionEntree` envoie au dialogue une commande sans champ visible.
- [ ] **Balayage** : tous les `backend/tests/test_photolab_*.py`, `test_i18n_l0.py`, `test_p2_plafonds_ecran.py`, `test_assets2d_lanceur.py`, `test_plafonds_garde.py` (recensement des routes payantes : aucune route Photolab payante), et `node qa/run.mjs` ; `python scripts/restaurer_bak_montage.py` avant les bancs du bundle si l'un d'eux en dépend. Rapporter chaque total.
- [ ] **Preuve sur 8799** (`.claude/launch.json` « preuve-t138 » : `serve8799.py` du scratchpad, backend du worktree, données jetables, aucune clé ; volet 1400×900, lire le DOM) : ouvrir une image de la Bibliothèque ; Filtre › Flou › Flou gaussien… → le dialogue, l'aperçu change avec le rayon, OK → l'historique gagne « Flou gaussien » ; Image › Réglages › Niveaux… (Ctrl+L) sur mesure avec histogramme ; Courbes… (Ctrl+M) avec un point ajouté ; Réglages › Teinte/Saturation → un calque de réglage visible dans Calques, modifié dans Propriétés ; Style de calque › Ombre portée sur un calque → aperçu puis OK, badge fx ; un mode de fusion changé ; annuler (Ctrl+Z) jusqu'à l'image d'origine. Captures + valeurs lues dans le DOM. Mesurer la latence de l'aperçu du flou sur une image 1920×1080.
- [ ] **Compte rendu** + note du suivi t138 + fichier mémoire `photolab-reglages-138.md` (+ ligne dans MEMORY.md) ; attendre « commit et ouvre la PR ».

## Auto-revue

- Spec P3 : 16 calques de réglage (B5 ; Courbes et Niveaux sur mesure B4), 75 filtres en dialogue générique avec aperçu (B1, B2 ; D9 et champs requis opaques grisés), 27 modes (validation pont A2 ; liste existante), Style de calque (B6), liste blanche (A2), aperçu moteur (A3), bilingue (B3).
- Ordre d'exécution : A1 → A2 → A3 → A4 → B1 → B2 → B3 → B4 → B5 → B6 → C1. B3 (textes) passe avant les éditeurs pour que leurs libellés existent ; chaque tâche B ajoute en plus les clés `photolab.*` qu'elle écrit en toutes lettres (sinon `test_photolab_textes.py` rougit).
- Noms partagés : `champsVisibles`, `sansEcran`, `parametres`, `libelleParam` (B1) ; `PL.ouvrirReglage` (B2) ; `PL.ouvrirCourbes`, `PL.ouvrirNiveaux`, `lutNiveaux`, `lutCourbe`, `appliquerLuts` (B4) ; `PL.creerReglage`, `depuisInspect`, `kindDe`, `difference` (B5) ; `PL.ouvrirStyles`, `etapesStyles` (B6) ; `PL.vue.poserApercu` (B2) ; routes `/apercu`, `/histogramme` (A3), `/commandes` avec `champs` (A2).
