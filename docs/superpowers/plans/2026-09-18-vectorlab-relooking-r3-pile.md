# Vectorlab relooking Affinity — R3 pile de droite à onglets — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `…-relooking-design.md` (R-D4 ids conservés, R-D5 correspondance, §3 rangée de calque).

**Goal :** la pile de droite est celle d'Affinity — trois groupes de
panneaux à onglets par persona (Vecteur : Couleur · Échantillons · Trait ·
Apparence · Texte | Calques · Tracé · Image · Planches · Grille · Plateau ·
Carte · Vitrail · Stock | Transformer · Navigateur · Historique · Repères ·
Exporter ; Pixel : Couleur | Calques · Pixel · Image · Stock | Navigateur ·
Transformer · Historique · Exporter), rangées de calques Affinity avec
vignette, nom, œil, verrou, sélection bleue, tête « Opacité · Normal »
(mode de fusion de calque nouveau), boutons d'action en bas ; Navigateur
avec vignette et curseur de zoom ; Transformer et Trait séparés de
l'Apparence sans réécrire `mod-style`.

**Architecture :** `mod-onglets.js` feuille (groupes / onglets → sections
`<details>`, onglet actif mémorisé `dz_vl_onglets`) ; `mod-navigateur.js`
feuille (cadre de vue, échelle du curseur) ; `mod-doc.js` gagne
`calque.fusion` + `op_calque_fusion` (compilé `mix-blend-mode` sur le `<g
data-calque>`) ; `mod-pile.js` UI : construit les trois groupes, DÉPLACE
les `<details>` existants dans le groupe de leur onglet (summary masqué,
onglet actif = section ouverte, `mod-panneaux` continue de mémoriser),
redistribue les rangées de `#panneauStyle` par libellé vers
`#panneauTransformer` / `#panneauTrait` après chaque rendu (les écouteurs
suivent les nœuds), rend Échantillons et Navigateur, pose `VL.ouvrirOnglet`
(les menus de R1 l'appellent) ; `mod-layers.js` : rangée Affinity, tête
opacité + fusion, barre d'actions.

**Tech :** vanilla ESM, CSS ; node `qa/run.mjs` ; pytest `test_vector_docs.py` (aller-retour d'un calque avec `fusion`).

---

### Task 1 : `calque.fusion` (modèle + commande + compilation)

**Files :** Modify `frontend/vectorlab/js/mod-doc.js` (validation des calques dans `parserDoc`, compilation, `op_calque_fusion` près de `op_calque_opacite`), Test `frontend/vectorlab/qa/calques.test.mjs` (ajout), `backend/tests/test_vector_docs.py` (aller-retour).

- [ ] **RED** (dans `calques.test.mjs`) :
```js
import { op_calque_fusion, MODES_FUSION_CALQUE } from "../js/mod-doc.js";
// … dans un bloc : doc = nouveau doc avec un calque c1
op_calque_fusion(doc, "c1", "multiply");
ok("fusion : posée, compilée en mix-blend-mode sur le <g data-calque>", doc.calques[0].fusion === "multiply" && compilerSVG(doc).includes('data-calque="c1"') && /data-calque="c1"[^>]*style="[^"]*mix-blend-mode:multiply/.test(compilerSVG(doc)));
op_calque_fusion(doc, "c1", "normal");
ok("normal : le champ est RETIRÉ, rien de compilé", doc.calques[0].fusion === undefined && !compilerSVG(doc).includes("mix-blend-mode"));
ok("mode inconnu : refusé", (() => { try { op_calque_fusion(doc, "c1", "zz"); return false; } catch { return true; } })());
ok("parser : un calque à fusion inconnue est refusé, un mode connu passe", (() => { const d = JSON.parse(JSON.stringify(doc)); d.calques[0].fusion = "screen"; parserDoc(JSON.stringify(d)); d.calques[0].fusion = "zz"; try { parserDoc(JSON.stringify(d)); return false; } catch { return true; } })());
ok("état vide : sans fusion → normal implicite, 16 modes exposés", MODES_FUSION_CALQUE.length === 16 && MODES_FUSION_CALQUE[0] === "normal");
```
- [ ] **Code** : `export const MODES_FUSION_CALQUE = MODES_FUSION;` ; dans la validation des calques de `parserDoc` : `if (c.fusion !== undefined && !MODES_FUSION.includes(c.fusion)) throw new Error(`calque ${c.id}: mode de fusion inconnu ${c.fusion}`);` ; `op_calque_fusion(doc, id, mode)` : refuse si `!MODES_FUSION.includes(mode)`, `delete` si `normal`, sinon pose ; compilation : `const fusion = c.fusion && c.fusion !== "normal" ? \`mix-blend-mode:${escAttr(c.fusion)}\` : ""` fusionné dans l'attribut `style` du `<g>` (avec `display:none` si caché).
- [ ] pytest : `test_calque_fusion_aller_retour` — PUT d'un doc dont un calque porte `"fusion": "multiply"`, GET → le champ revient tel quel (le store ne le connaît pas et ne le perd pas).
- [ ] vert, commit.

### Task 2 : `mod-onglets.js`

**Files :** Create `frontend/vectorlab/js/mod-onglets.js`, Test `qa/onglets.test.mjs`.

```js
// RED
import { ONGLETS, GROUPES, onglets_de, onglet_de_section, actif_lire, actif_poser, actif_de, sections_ouvertes } from "../js/mod-onglets.js";
ok("Vecteur : 3 groupes, 5 / 9 / 5 onglets ; Pixel : 1 / 4 / 4", …);
ok("chaque onglet a un libellé et ≥ 1 section, chaque section n'appartient qu'à un onglet", …);
ok("onglet_de_section : styleDetails → couleur, exportPlusDetails → exporter, inconnu → null", …);
ok("actif_lire : défauts (couleur, calques, transformer en Vecteur ; couleur, calques, navigateur en Pixel), JSON illisible → défauts", …);
ok("actif_poser : pose par persona et groupe, refuse un onglet hors du groupe", …);
ok("sections_ouvertes : les sections de l'onglet actif de chaque groupe, rien d'autre", …);
```
Module : `ONGLETS = { couleur: { libelle: "Couleur", sections: ["styleDetails"] }, echantillons: {…, ["echantillonsDetails"]}, trait: ["traitDetails"], apparence: ["apparence2Details"], texte: ["texteDetails"], calques: ["calquesDetails"], trace: ["noeudsDetails", "formeDetails"], image: ["imageDetails"], planches, grille, plateau, carte, vitrail, stock: ["assetsDetails"], transformer: ["transformerDetails"], navigateur: ["navigateurDetails"], historique: ["instantanesDetails"], reperes, exporter: ["exportDetails", "exportPlusDetails"], pixel: ["pixelDetails"] }` ; `GROUPES = { vecteur: [["couleur","echantillons","trait","apparence","texte"], ["calques","trace","image","planches","grille","plateau","carte","vitrail","stock"], ["transformer","navigateur","historique","reperes","exporter"]], pixel: [["couleur"], ["calques","pixel","image","stock"], ["navigateur","transformer","historique","exporter"]] }` ; état `{ vecteur: [a,b,c], pixel: [a,b,c] }`.

### Task 3 : `mod-navigateur.js`

```js
// RED
import { cadre_vue, zoom_de_curseur, curseur_de_zoom, echelle_vignette } from "../js/mod-navigateur.js";
ok("échelle : la page tient dans 240 × 150", echelle_vignette({w:640,h:960},240,150).k ≈ 0.15625 et offsets centrés);
ok("cadre : la portion de page visible dans la scène, en coordonnées vignette, bornée à la page", …);
ok("curseur ↔ zoom : 0 → 5 %, 1000 → 1600 %, aller-retour à 1 % près, 100 % au milieu environ", …);
ok("état vide : sans doc → null", cadre_vue(null, …) === null);
```

### Task 4 : `mod-pile.js` + `mod-layers.js` + `index.html` + CSS

- `index.html` : `<aside id="panneauCalques" class="panneau">` garde toutes ses `<details>` (ordre libre) plus trois nouvelles : `transformerDetails` (`#panneauTransformer`), `traitDetails` (`#panneauTrait`), `echantillonsDetails` (`#panneauEchantillons`), `navigateurDetails` (`#panneauNavigateur`) ; les deux zones `.panneau-defile` / `.panneau-calques` disparaissent (les groupes prennent le relais). `PANNEAUX_DEFAUT` de `mod-panneaux` gagne les quatre ids.
- `mod-pile.js` : construit `<div class="groupe" data-g="0|1|2"><div class="onglets"></div><div class="groupe-corps"></div></div>` ×3 ; à chaque `setPersona` (crochet `surPersona` chaîné) : recalcule les onglets du persona, déplace chaque `<details>` de chaque onglet dans le corps de son groupe (ordre des onglets), pose `open` selon `sections_ouvertes`, rend les boutons d'onglet (actif marqué) ; clic sur un onglet → `actif_poser` + localStorage + réouverture ; `VL.ouvrirOnglet(id)` = activer l'onglet (et le persona s'il n'y est pas : couleur/calques/… existent dans les deux) ; redistribution des rangées de `#panneauStyle` (`X · Y`, `L · H`, `Incliner`, `Puissance` → `#panneauTransformer` ; `Contour`, `Trait`, `Pointillés`, `Joint` → `#panneauTrait`) après chaque rendu ; Échantillons = pastilles de `doc.palette` (clic → `op_style` fond sur la sélection, sinon `styleCourant`) ; Navigateur = vignette (`compilerSVG` re-dimensionné) + cadre + `input[type=range]` ; le chevron de repli `⌄` d'un groupe replie son corps (classe `replie`).
- `mod-layers.js` : tête `#calquesTete` (`Opacité [n] % · [select fusion]` sur le calque actif, `op_calque_opacite` / `op_calque_fusion`), rangée `.calque` = `[vig][nom][🔒][👁]`, barre `#calquesActions` : ✎ renommer · Réglage (`VL.ouvrirOnglet("pixel")`) · Masque (`ouvrirOnglet("apparence")`) · Calque pixel (`VL.actions.image.biblio`) · FX (`ouvrirOnglet("apparence")`) | Groupe (`VL.actions.selection.grouper`) · ＋ (`#btnCalquePlus` reste) · ▲ ▼ · 🗑 (sur le calque actif) ; les `data-act` existants (oeil, verrou, monter, descendre, poubelle, exemple) restent ; `.calque.actif` bleu.
- CSS R3 : `.groupe` (flex column, `border-bottom`), `.onglets` (flex wrap, gap 2, padding 4 8, fond `--aff-barre`, bouton 22 px, actif fond #3c3c3c radius 4), `.groupe-corps` (overflow-y auto, `flex: 1 1 0`), `details > summary.panneau-tete { display: none }` dans la pile, `.calque` 34 px grille `18px 28px 1fr 22px 22px`, `.calque.actif { background: var(--aff-sel); color: #fff }`, `.calque-vig` 26 × 26, `#calquesTete`, `#calquesActions` (24 px, icônes), `.nav-vignette` 240 × 150 sur fond `--aff-canevas`, `.nav-cadre` bordure blanche.

### Task 5 : preuve, déploiement, relevé

8799, 1400 × 900 : `.panneau` 264 ; 3 `.groupe` ; onglets Vecteur 5 / 9 / 5, Pixel 1 / 4 / 4 ; l'onglet actif ouvre sa section (`details.open`) et les autres sont fermées (offsetHeight 0) ; clic « Trait » → `#traitDetails` ouvert avec les rangées Contour / Trait ; « Transformer » → X · Y · L · H visibles avec une sélection ; rechargement → onglets actifs relus ; `VL.ouvrirOnglet("planches")` → groupe 2 sur Planches ; rangée de calque 34 px, vignette 26, active bleue ; tête « Opacité 100 % · Normal » → choisir `multiply` → `doc.calques[i].fusion === "multiply"` et `<g data-calque>` porte `mix-blend-mode` ; Navigateur : vignette ≤ 240 × 150, curseur → `VL.etat.zoom` ; audit lisibilité des deux personas ; taskkill ; déploiement hash-object ; relevé ; mémoire ; push.
