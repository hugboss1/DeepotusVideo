# Finitions UI — chantier 4 : l'aide didactique animée et son skill — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** chaque option du Vectorlab peut porter une **fiche didactique** (titre, phrase « pour un enfant de cinq ans », animation à trois temps faite de vraies captures) montrée au survol long (≥ 900 ms) ou par un « ? » ; un skill réutilisable `didacticiel-option` FABRIQUE une fiche à partir du code de l'option.

**Architecture :** `mod-didact.js` (pur : `fiche_pour`, `compter_mots`, `valider_fiche`, constantes ; DOM : charge `aide/index.json`, minuteur de survol long à 900 ms sur les éléments à id, encart `.vl-didact` 320 px positionné par `bulle_position` de mod-infobulle, bouton « ? » posé à côté de l'élément) ; `frontend/vectorlab/aide/index.json` + `aide/<module>.<id>.webp` (320 × 200, 1,2 s par temps, boucle) ; le skill dans `C:\Users\olivi\.claude\skills\didacticiel-option\` avec ses scripts (`capture.js` in-page : sérialisation SVG → canvas → PNG des trois temps, avec surlignage du geste ; `assembler.py` : Pillow WebP animé, APNG en repli ; `verifier.py` : trois PNG distincts, phrase ≤ 25 mots, entrée d'index) et `evals/evals.json` (Contour sombre, Dépouille, Créer le calque pixel).

**Tech :** ES modules, Pillow 12.3 du python embarqué (WebP animé vérifié : 3 frames, loop 0), navigateur intégré sur 8799.

---

## Relevé (code lu le 20/09/2026 à `f858582`)

| Fait | Où | Décision |
|---|---|---|
| Bulle courte : `mod-infobulle.js`, 450 ms, `bulle_position(ancre, taille, fenetre, marge)` pure, `VL.infobulle.montrer/cacher` | infobulle.js:7, 50-70 | l'encart didactique réutilise `bulle_position` ; il vient APRÈS la bulle courte (900 ms) et la remplace |
| Options du banc : « Contour sombre » = `#pxContour` (mod-pixelui:526, `contour_sombre(im, secondaire ∥ #101010, épaisseur)`), « Dépouille » = `#impDepouilleR` / `#impDepouille` (mod-impression:323, ±45°, `extruder_depouille` via `extruder_biseau`), « Créer le calque pixel » = `#pxCreerCalque` (mod-pixelui:502, `creerCalquePixel` : image transparente cible posée sur le modèle) | | ids d'ancrage = ids DOM ; les fiches se nomment `pixelui.pxContour`, `impression.impDepouille`, `pixelui.pxCreerCalque` |
| Options des captures : Remplissage = `#a2Conique` / `#a2Transp` (mod-apparence2), Pixel-art = `#pxTuileOK` (tuile W × H → `op_pixelart`), Modèle = `#pxDesigner` (`designerModele`) | | trois fiches de plus : `apparence2.a2Conique`, `pixelui.pxTuileOK`, `pixelui.pxDesigner` |
| Scène : `#canvasHost` porte le `<svg>` du document, `#overlay` le `<svg>` des poignées | index.html:123-124 | capture = sérialisation des deux SVG (images `<image href>` inlinées en data-URL d'abord : un href relatif dans un blob SVG ne charge pas) → `Image` (par `onload`, pas `decode()`) → canvas 640 × 400 → `toDataURL` ; le panneau (HTML) n'est pas sérialisable proprement : le geste est **surligné** par un cadre et un chip « nom de l'option » dessinés au temps 2 |
| Pillow embarqué : 12.3.0, WebP oui, `save(format="WEBP", save_all=True, duration=1200, loop=0)` → 3 frames mesurées ; APNG idem | | WebP par défaut, APNG en repli si `webp` manque |
| Pas de dossier `aide/` | | créer `frontend/vectorlab/aide/index.json` = `[]` au départ ; le panneau lit l'index (`fetch("aide/index.json")`), une option sans fiche garde la bulle courte |
| Volet caché : pas de rAF, `Image.decode()` suspendu, `toBlob` ≈ 1 s | mémoire | capture par `onload` + `toDataURL` synchrone |

---

### Task 1 : `mod-didact.js` pur + banc (RED → GREEN)

**Files :** Create `frontend/vectorlab/js/mod-didact.js`, `frontend/vectorlab/qa/didact.test.mjs`, `frontend/vectorlab/aide/index.json`.

- [ ] Banc : `fiche_pour(index, id)` (rend la fiche dont `id` = id DOM, sinon null ; état vide : index null / [] → null) ; `compter_mots("…")` (mots = suites de lettres/chiffres, apostrophes et traits d'union collés) ; `valider_fiche(f)` → liste d'erreurs (id, titre, phrase ≤ 25 mots, fichier `.webp`/`.png`, version entier) ; `DIDACT_DELAI_MS === 900`, `DIDACT_LARGEUR === 320` ; `didact_html(f)` → chaîne avec `<img src="aide/<fichier>">`, titre et phrase échappés.
- [ ] RED → module → GREEN → commit.

### Task 2 : DOM — encart `.vl-didact`, survol long, « ? »

- [ ] `initDidact(VL)` : `fetch("aide/index.json")` (silencieux si absent) ; `pointerover` en capture sur `document` : cible = `ev.target.closest("[id]")` dont l'id a une fiche ; minuteur 900 ms → `montrer(el)` : encart `#vlDidact.vl-didact` (320 px) positionné par `bulle_position` ; `pointerout` / `pointerdown` / Échap → cacher ; pour chaque élément à fiche, un bouton `.vl-didact-q` « ? » inséré après l'élément (une fois, après chaque rendu de panneau via un `MutationObserver` sur `#panneauCalques`) qui ouvre l'encart au clic ; `VL.didact = { montrer, cacher, index, element }` pour la preuve.
- [ ] CSS `.vl-didact` (jetons `--aff-*`, 320 px, image 320 × 200, titre gras, phrase 13 px), `.vl-didact-q` (18 × 18, rond, muet).
- [ ] `core.js` : import + `initDidact(VL)` après `initInfobulle(VL)`. Bench vert, commit.

### Task 3 : le skill `didacticiel-option`

**Files :** `C:\Users\olivi\.claude\skills\didacticiel-option\{SKILL.md, scripts/capture.js, scripts/assembler.py, scripts/verifier.py, evals/evals.json, references/procedure.md}`.

- [ ] `SKILL.md` : description « pushy » (déclencheurs : « fiche », « didacticiel », « aide animée », « explique l'option X », « à un enfant de cinq ans », toute nouvelle option du Vectorlab) ; le déroulé en six temps du spec ; ce qu'il ne faut pas faire (dessiner à la main, inventer ce que fait l'option, capture d'écran du volet).
- [ ] `scripts/capture.js` : à coller dans la page (`javascript_tool`) — pose `window.__didact = { capturer(temps, {surligner: "#id" | {x,y,w,h}, chip: "texte"}) → dataURL PNG 640×400 }` ; inlining des `<image href>` ; halo + chip au temps 2.
- [ ] `scripts/assembler.py <sortie.webp> t1.png t2.png t3.png` : redimensionne en 320 × 200 (letterbox sur `--aff-canevas`), WebP animé 1200 ms boucle, APNG en repli, vérifie `n_frames == 3`.
- [ ] `scripts/verifier.py <racine vectorlab> <id>` : l'entrée d'index existe, phrase ≤ 25 mots, le fichier existe, 3 frames, les trois frames diffèrent deux à deux (hash des octets RGB), sortie 0/1.
- [ ] `evals/evals.json` : trois évals (Contour sombre, Dépouille, Créer le calque pixel) avec assertions (index, phrase, 3 frames distincts, survol long prouvé).

### Task 4 : les trois fiches du banc, puis les trois des captures (preuve à chaque fois)

- [ ] Pour chacune : lire le code, document de démo sur 8799 (image 32 × 32 pour Contour sombre / Créer le calque pixel / Modèle / Pixel-art ; rectangle pour Remplissage et Dépouille — la Dépouille se capture dans `#impDlg` : l'aperçu 3D est un `<model-viewer>`, non sérialisable → temps capturés sur la scène 2D avec le chip « Dépouille ±45° » et le curseur, et la note dans la fiche), capture des trois temps, assemblage, phrase, index, `verifier.py` = 0, preuve : `pointerover` réel sur l'élément → après 900 ms `#vlDidact` visible, `img.naturalWidth === 320`, `n_frames = 3` côté python.
- [ ] Commit par lot de fiches ; `run.mjs` vert.

### Task 5 : déploiement (statiques), relevé, mémoire, push.
