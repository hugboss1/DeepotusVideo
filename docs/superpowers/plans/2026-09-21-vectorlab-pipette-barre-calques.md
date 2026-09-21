# Vectorlab — pipette de classe Affinity, barre contextuelle en icônes, arbre des calques, et le crayon pixel « qui s'efface » — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** (1) l'outil Pipette du persona Vecteur prélève une COULEUR sur le rendu (loupe, rayon 1×1…9×9, source Global / Calque courant, « Appliquer à la sélection »), comme le Sélecteur de couleur d'Affinity ; (2) la barre contextuelle porte des ICÔNES à bulle pour ses actions (nœuds, plume, alignement, configuration) au lieu d'encarts de texte ; (3) le panneau Calques montre, sous chaque calque, ses objets, et sous chaque objet ses masques (écrêtage, masque de transparence) et effets, indentés avec une icône de type ; (4) le bug du crayon pixel : investigation consignée, reproduction demandée à l'utilisateur.

**Architecture :** trois modules purs bancables — `mod-pipette.js` (`echantillon_rayon`, `hex_de_rgb`, `champs_pipette`, `pipette_decision`), `mod-icones.js` étendu (icônes d'actions : vif, lisse, intelligent, fractionner, ouvrir, fermer, courbe lisse, relier, inverser, six alignements, configuration, paramètres, plus les types d'objets et masques), `mod-layers.js` (`arbre_calques(doc, calqueActif, plies)` → rangées `{niveau, genre, id, calque, nom, icone, ...}`) — puis le DOM : `mod-pipetteui.js` (capture sur `#stage` quand `etat.outil === "pipette"`, rendu offscreen du document par la voie de `capture.js`, loupe `.vl-loupe`, lecture RGB, Maj = loupe, Alt = appliquer, Ctrl = style de l'objet = l'ancienne pipette), `mod-barrecontexte` (`type: "bouton"` + `icone` → `<button class="cb-bouton cb-icone">`), `mod-layers` (rangées enfants repliables, clic = sélection de l'objet, œil / verrou par objet via `op_verrou`/`op_visible` s'ils existent, sinon lecture seule).

**Tech :** ES modules, bancs `node frontend/vectorlab/qa/run.mjs`, preuve 8799 à 1400 × 900, déploiement par hash, statiques seuls.

---

## Relevé (code lu le 21/09/2026 à `8815cba`)

| Sujet | Fait | Décision |
|---|---|---|
| Pipette actuelle | `mod-tools.js:150` : outil `pipette` = copie du STYLE de l'objet cliqué (fond, contour, épaisseur, pointillés, joint, opacité) vers la sélection ou `styleCourant` ; famille `mesure` (`mod-familles.js:16`, raccourci I) ; `VL.hints.pipette` | devient **Ctrl + clic** de la nouvelle pipette (« prélever le style ») ; le clic nu prélève la COULEUR |
| Rendu offscreen | `mod-export.rasteriser(k, transparent, cadre)` compile le document en SVG → Image → canvas ; le skill `capture.js` sérialise `#canvasHost svg` (inline des `<image href>`, retrait du transform CSS) | `mod-pipetteui` : `svgCourant` n'est pas exporté → sérialiser `#canvasHost svg` (exactement `capture.js` : clone, transform retiré, images inlinées, `image-rendering` recopié) à l'échelle écran ×1 en coordonnées du stage, UNE fois au pointerdown ; « Calque courant » = clone avec les autres `[data-calque]` retirés |
| Barre contextuelle | `mod-contexte.champs_de` : `ACTIONS_PLUME` (9 boutons texte), `ALIGN_NOEUDS` (6 glyphes), `configDoc` / `parametres` ; `mod-barrecontexte.rendre` → `<button class="cb-bouton">` texte ; `.cb-bouton { height: 24px; padding: 0 10px }` | champ `bouton` gagne `icone` (id de `ICONES`) ; rendu `<button class="cb-bouton cb-icone" title="libellé">` + `icone_svg(id, 16)` ; libellé conservé dans `title` → bulle `mod-infobulle` ; un séparateur `.cb-sep` entre groupes |
| Icônes | `mod-icones.js` : 40 clés (outils), `icone_svg(id, taille)`, repli pointillé, `outils_sans_icone` | + `vif lisse intelligent fractionner ouvrir fermer lisserCourbe relier inverser al-gauche al-centreH al-droite al-haut al-centreV al-bas configDoc parametres` et types `groupe path texte image ecretage masque effet` |
| Calques | `rendreCalques` : une rangée par calque `[chevron][vignette][nom][🔒][👁]`, chevron inerte ; objets : `rect ellipse path texte textechemin cadre image groupe instance tuile forme` ; groupe : `enfants` + `clip` (= écrêtage par l'enfant `clip`) ; style : `masque = grad:<id>` (masque de transparence), `effets` (liste) | `arbre_calques` pur : rangées calque → objets (ordre de peinture inversé) → enfants de groupe (niveau +1, l'enfant `clip` marqué **Masque d'écrêtage**) → sous-rangées « Masque de transparence » / « Effets (n) » ; plié par défaut sauf le calque actif ; `plies` persistés en `localStorage` |
| Bug crayon | données prouvées saines sur 8799 (tampon et PNG servi portent le pixel dans 5 scénarios : onglet Calques → Pixel, calque pixel sur modèle, persona) ; document réel `b03cb918deab` : journal `img9.pix4…pix10` écrit (les commits arrivent au serveur) ; la capture 3 montre le persona Vecteur + l'outil Nœud | pas de cause racine sans reproduction → question à l'utilisateur (séquence exacte, onglet, outil) ; aucun correctif à l'aveugle |

---

### Task 1 : arbre des calques (pur, RED → GREEN) + rangées enfants

**Files :** Modify `frontend/vectorlab/js/mod-layers.js`, `frontend/vectorlab/js/mod-icones.js`, `frontend/vectorlab/vectorlab.css` ; Test `frontend/vectorlab/qa/arbre_calques.test.mjs`.

- [ ] Banc : document à deux calques (Fond : rect, groupe {enfants: [ellipse, path], clip: path.id} ; pixel : image avec `style.masque = "grad:g1"` et `style.effets = [{type:"ombre"}]`) → `arbre_calques(doc, "c2", new Set())` rend, dans l'ordre d'affichage (dessus en haut) : calque `pixel` (niveau 0, actif), image (niveau 1), « Masque de transparence » (niveau 2, genre `masque`), « Effets (1) » (niveau 2, genre `effet`) ; calque `Fond` (niveau 0) puis, s'il n'est pas plié, groupe (1), path « Masque d'écrêtage » (2, genre `ecretage`), ellipse (2), rect (1) ; `plies = new Set(["c1"])` → les rangées de Fond disparaissent ; état vide : doc null → [] ; chaque rangée porte `icone` connue d'`ICONES`.
- [ ] RED → implémenter `arbre_calques` (export) + `icone_objet(o)` + les icônes de types → GREEN.
- [ ] DOM : `rendreCalques` rend les rangées de l'arbre : `.calque` (inchangé) puis `.calque-objet` avec `style="--niv:N"` (retrait `calc(14px * var(--niv))`), `icone_svg`, nom (`o.nom || type · id`), état `.selectionne` si dans `etat.selection` ; clic sur une rangée objet = `VL.setSelection([id])` (Maj = ajout) ; chevron du calque = plier / déplier (`plies` en `localStorage` `dz_vl_calques_plies`) ; les genres `masque` / `ecretage` / `effet` sont en lecture (clic = ouvrir l'onglet Apparence).
- [ ] CSS aux jetons : `.calque-objet` 26 px, icône 14 px muette, indentation, `.selectionne` fond `--aff-sel` à 20 % ; `run.mjs` vert ; commit.

### Task 2 : la barre contextuelle en icônes

**Files :** Modify `mod-contexte.js`, `mod-barrecontexte.js`, `mod-icones.js`, `vectorlab.css` ; Test `qa/contexte.test.mjs` (existant : compléter).

- [ ] Banc : `champs_de("noeuds", etat)` → chaque bouton porte `icone` présent dans `ICONES` et un `libelle` ; `champs_de("plume", …)` idem ; `champs_de("select", {selection: []})` → `configDoc` et `parametres` avec icône ; `boutons_groupes(champs)` (pur) rend les groupes séparés (`ACTIONS`, `ALIGN`) pour poser un séparateur.
- [ ] RED → ajouter `icone` aux tables, les 17 icônes, `boutons_groupes` → GREEN.
- [ ] DOM : `rendre()` : `<button class="cb-bouton cb-icone" data-champ title="…">` + svg ; séparateur `<span class="cb-sep">` entre groupes ; CSS : `.cb-icone { width: 28px; padding: 0 }`, `.cb-sep { width: 1px; height: 18px; background: var(--aff-bord) }`. Preuve : outil Nœuds → aucune rangée de texte, bulles au survol (`VL.infobulle`), clic réel sur « Lisse » agit.

### Task 3 : la pipette de classe Affinity

**Files :** Create `mod-pipette.js`, `mod-pipetteui.js`, `qa/pipette.test.mjs` ; Modify `mod-contexte.js` (champs), `mod-tools.js` (l'ancienne branche `pipette` → sous Ctrl), `core.js`, `vectorlab.css`, `VL.hints`.

- [ ] Banc pur : `echantillon_rayon(img, x, y, rayon)` (moyenne des pixels opaques dans le carré 2r+1, bornée, ignore l'alpha 0, rend `{r,g,b,a,n}` ; état vide : hors image → null) ; `hex_de_rgb` ; `champs_pipette(etat)` → `[bascule pipAppliquer, bascule pipLoupe, select pipSource (global | calque), select pipRayon (0,1,2,4 → « Point (1×1) », « 3 × 3 », « 5 × 5 », « 9 × 9 »)]` ; `pipette_decision({appliquer, alt, ctrl, selection, hex, cible})` → `{action: "style" | "fond" | "contour" | "courant"}` (Ctrl = style de l'objet, Alt inverse « appliquer », clic droit = contour).
- [ ] RED → GREEN.
- [ ] DOM `initPipetteUI(VL)` : capture `pointerdown` sur `#stage` quand `etat.outil === "pipette"` (`stopImmediatePropagation` — patron mod-plumeui) ; Ctrl → délègue à l'ancienne branche (mod-tools garde son code, appelé via `VL.actions.pipette.style(id)`) ; sinon rasterise (une fois) → `ImageData` ; loupe `.vl-loupe` (120 px, `background-image` = canvas zoomé ×8 autour du curseur, `image-rendering: pixelated`, croix 1 px, lecture `R : G : B` sous la loupe) suit le pointeur ; `pointerup` : `echantillon_rayon` → hex ; `pipette_decision` → `op_style(sel, {fond|contour: hex})` ou `etat.styleCourant.fond = hex` + toast ; `etat.pipette = {appliquer: true, loupe: true, source: "global", rayon: 0}` persisté dans `dz_vl_params` ; `VL.hints.pipette` = « **Cliquer** ou **glisser** pour prélever une couleur · **Ctrl** : le style de l'objet · **Maj** : loupe · **Alt** : appliquer à la sélection ».
- [ ] Preuve : rectangle violet, `PointerEvent` down/move/up réels sur lui → `.vl-loupe` visible pendant le glisser (mesurer `offsetWidth = 120`), lecture `R : 207 G : 111 B : 227`, sélection vide → `styleCourant.fond = #CF6FE3` ; avec un second rectangle sélectionné et « Appliquer » → son `style.fond` change ; Ctrl + clic → style copié (ancien contrat).

### Task 4 : le crayon pixel — consigner, demander

- [ ] Relevé des cinq scénarios rejoués et du journal `pix4…pix10` (fait) ; dans le rapport, demander la séquence exacte (persona, onglet cliqué, outil, image ou calque pixel, zoom) et si le pixel revient après un rechargement.

### Task 5 : preuve, déploiement, relevé, push
