# Vectorlab relooking Affinity — R5 barre contextuelle par outil — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `…-relooking-design.md` (R-D7).

**Goal :** la barre contextuelle suit l'outil ET la sélection comme dans
Affinity : à gauche le libellé de la sélection (« Aucune sélection », « 1
objet · rect », « 3 objets »), puis les réglages de l'outil courant en
champs inline (forme courante, profil et largeur du pinceau, largeur de
la gomme, rayon du coin, terrain, police, rayon / dureté / tolérance des
outils raster, mode de tranche), les bascules Grille / Aimant / Unité
existantes, et — sans sélection — « Configuration du document… » (taille,
dpi, unité, fond) et « Paramètres de l'appli… » (bulles, pas de grille par
défaut, aimantation par défaut).

**Architecture :** `mod-contexte.js` feuille : `libelle_selection(objets)`,
`champs_de(outil, etat)` → liste de champs `{id, type, libelle, valeur,
options?, min?, max?, pas?}` par outil, `appliquer_champ(etat, id, valeur)`
→ nouvel état partiel (pur : rend l'objet patché à poser sur `etat` /
`etat.px` / `etat.pinceauv`), `PARAMS_DEFAUT` + `params_lire / params_poser`
(localStorage `dz_vl_params`) ; `mod-barrecontexte.js` UI : rend les champs
dans `#cbSelection` / `#cbOutil` à chaque `surOutil` / `surSelection` /
`surRendu`, applique les changements puis `VL.rendre()` ; dialogues
`VL.configurerDocument()` (commandes : `d.taille`, `d.unites`, `d.fond`) et
`VL.parametresAppli()` ; `mod-charpente` les appelle déjà.

**Tech :** vanilla ESM, CSS ; node `qa/run.mjs`.

---

### Task 1 : `mod-contexte.js` (RED → vert)

```js
// contexte.test.mjs
import { libelle_selection, champs_de, appliquer_champ, PARAMS_DEFAUT, params_lire, params_poser } from "../js/mod-contexte.js";
ok("libellé : aucune / 1 objet · type / n objets", libelle_selection([]) === "Aucune sélection" && libelle_selection([{ type: "rect" }]) === "1 objet · rect" && libelle_selection([{ type: "rect" }, { type: "path" }]) === "2 objets" && libelle_selection(null) === "Aucune sélection");
ok("select sans sélection : boutons Configuration et Paramètres", champs_de("select", { selection: [] }).map((c) => c.id).join() === "configDoc,parametres");
ok("select avec sélection : opacité de l'objet de tête", champs_de("select", { selection: ["a"], objets: [{ type: "rect", style: { opacite: 0.5 } }] }).some((c) => c.id === "opacite" && c.valeur === 50));
ok("forme : un select des formes avec la courante ; gomme / coin : un nombre", (() => { const f = champs_de("forme", { formeCourante: "etoile", formes: [{ id: "etoile", libelle: "Étoile" }, { id: "polygone", libelle: "Polygone" }] }); return f[0].type === "select" && f[0].valeur === "etoile" && f[0].options.length === 2 && champs_de("gomme", { gommeLargeur: 12 })[0].valeur === 12 && champs_de("coin", { coinRayon: 10 })[0].id === "coinRayon"; })());
ok("pinceau vectoriel / crayon : profil + largeur", champs_de("pinceauv", { pinceauv: { profil: "plat", largeur: 8 }, profils: ["plat", "fuseau"] }).map((c) => c.id).join() === "pvProfil,pvLargeur");
ok("raster : rayon + dureté pour le pinceau, tolérance + global pour le seau, rien pour le lasso", champs_de("px-pinceau", { px: { rayon: 4, durete: 1 } }).map((c) => c.id).join() === "pxRayon,pxDurete" && champs_de("px-seau", { px: { tolerance: 16, global: false } }).map((c) => c.id).join() === "pxTolerance,pxGlobal" && champs_de("px-lasso", { px: {} }).length === 0);
ok("tuiles : le terrain courant parmi les terrains ; texte : la police courante", champs_de("tuiles", { terrainCourant: "mer", terrains: { mer: { nom: "Mer" }, plaine: { nom: "Plaine" } } })[0].options.length === 2 && champs_de("texte", { typo: { courante: "lib:a", polices: [{ id: "lib:a", famille: "A" }] } })[0].valeur === "lib:a");
ok("état vide : outil inconnu → [], état absent → []", champs_de("zz", {}).length === 0 && champs_de("gomme", null).length === 0);
ok("appliquer : gommeLargeur borné ≥ 1, pxDurete borné 0..1, pvProfil posé sous pinceauv, formeCourante posée", appliquer_champ({}, "gommeLargeur", 0).gommeLargeur === 1 && appliquer_champ({}, "pxDurete", 250).px.durete === 1 && appliquer_champ({ pinceauv: { largeur: 8 } }, "pvProfil", "plat").pinceauv.profil === "plat" && appliquer_champ({}, "formeCourante", "etoile").formeCourante === "etoile");
ok("appliquer : champ inconnu → objet vide ; opacite → patch de style 0..1", Object.keys(appliquer_champ({}, "zz", 1)).length === 0 && appliquer_champ({}, "opacite", 50).style.opacite === 0.5);
ok("params : défauts (bulles, grille 8, aimant), lecture tolérante, pose", PARAMS_DEFAUT.bulles === true && params_lire("{oops").grillePas === 8 && params_lire('{"bulles":false,"zz":1}').bulles === false && params_poser(PARAMS_DEFAUT, "grillePas", 16).grillePas === 16 && params_poser(PARAMS_DEFAUT, "zz", 1) === PARAMS_DEFAUT);
```

### Task 2 : `mod-barrecontexte.js` + dialogues + CSS

- Rendu : `#cbSelection` = `libelle_selection(objets de la sélection)` ; `#cbOutil` = les champs (`select` → `<select>`, `number` → `<input type=number>`, `bascule` → `<label><input type=checkbox>`, `bouton` → `<button>`) chacun avec son libellé court ; `change` → `appliquer_champ(etat, id, valeur)` fusionné dans `etat` (`Object.assign` par clé : `px`, `pinceauv`, `style` → `VL.executer(op_style, sel, patch)`) puis `VL.rendre()` ; boutons `configDoc` / `parametres` → `VL.configurerDocument()` / `VL.parametresAppli()`.
- `VL.configurerDocument()` : dialogue `.vl-dlg` (largeur, hauteur, dpi, unité, fond) → une commande `executer((d) => { d.taille = {w,h}; d.unites = {…}; d.fond = … })`, puis `VL.zoomAjuster()`.
- `VL.parametresAppli()` : dialogue (bulles ☐, pas de grille par défaut, aimantation par défaut) → `params_poser` + localStorage ; à l'ouverture le cœur lit `dz_vl_params` (bulles → `VL.infobulle.desactiver()` si exposé, sinon `document.body.classList.toggle("sans-bulles")`, grille pas via `#selGrille`).
- CSS : `.cb-champ` (libellé 11 px muet + champ 24 px), `.cb select` 24 px, `.cb input[type=number]` 56 px.

### Task 3 : preuve, déploiement, relevé

8799, 1400 × 900 : sans sélection `#cbSelection` = « Aucune sélection » et deux boutons ; rect sélectionné → « 1 objet · rect » + champ Opacité, saisir 40 → `style.opacite` 0,4 ; outil gomme → champ « Largeur » 12, saisir 30 → `etat.gommeLargeur` 30 ; outil forme → select à 8+ options, choisir « etoile » → `etat.formeCourante` ; persona Pixel + px-pinceau → Rayon / Dureté ; « Configuration du document… » → dialogue, largeur 800 → `doc.taille.w` 800 et onglet mis à jour ; « Paramètres… » → décocher bulles → `dz_vl_params` relu au rechargement ; audit : la barre ne déborde pas ; taskkill ; déploiement ; relevé ; mémoire ; push.
