# Vectorlab relooking Affinity — R4 thème et densité — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Conception : `…-relooking-design.md` (R-D8 thème, R-D2 canevas uni).

**Goal :** tout le Vectorlab est dans les couleurs et la densité d'Affinity
— gris anthracite #2b2b2b / #232323, canevas uni #262626 sans damier,
texte #d0d0d0, sélection bleue, champs de 24 px, rangées de 28 px, texte
12 px, coins 4 px, curseurs à poignée ronde blanche, `select` sombres,
règles assorties — et le nuancier vit EN PLACE dans l'onglet Couleur ;
l'ancienne palette bleu-nuit (#171a20, #232833, #313847, #2c4a75…)
n'apparaît plus dans aucune règle active.

**Architecture :** `mod-theme.js` feuille : la table des jetons
(`TOKENS`), `theme_css()` (le bloc `:root`), `LEGACY` (les hex à bannir) ;
un banc-garde `qa/theme.test.mjs` qui lit `vectorlab.css` et refuse tout
hex hérité hors commentaire (comme le banc AST d'hygiène des imports) ;
`vectorlab.css` : les hex hérités sont REMPLACÉS par les variables `--aff-*`
(sed contrôlé, valeur par valeur), le damier du canevas retiré, une couche
« R4 densité » (champs, curseurs, selects, boutons, règles) ; `mod-couleur`
: `VL.ouvrirNuancier` accepte un HÔTE (`#panneauCouleurInline`) — le
nuancier se pose dans l'onglet Couleur au lieu du popover quand l'onglet
est visible ; `mod-style` : libellé « Décaler » pour la rangée du contour
décalé.

**Tech :** vanilla ESM, CSS ; node `qa/run.mjs`.

---

### Task 1 : `mod-theme.js` + banc-garde

```js
// theme.test.mjs — RED
import { TOKENS, theme_css, LEGACY, hex_herites } from "../js/mod-theme.js";
import { readFileSync } from "node:fs";
ok("jetons : fond, barre, canevas, bord, texte, muet, sel, cyan, violet, menu, champ", ["fond","barre","canevas","bord","texte","muet","sel","cyan","violet","menu","champ"].every((k) => /^#[0-9a-f]{6}$/i.test(TOKENS[k])));
ok("theme_css : un bloc :root avec une variable --aff-<jeton> par jeton", theme_css().startsWith(":root {") && Object.keys(TOKENS).every((k) => theme_css().includes(`--aff-${k}: ${TOKENS[k]}`)));
ok("hex_herites : trouve les hex de LEGACY hors commentaires, ignore les commentaires", hex_herites("a { color: #171a20; } /* #232833 */").join() === "#171a20" && hex_herites("").length === 0);
const css = readFileSync(new URL("../vectorlab.css", import.meta.url), "utf8");
ok("vectorlab.css : plus aucun hex hérité actif", hex_herites(css).length === 0, [...new Set(hex_herites(css))].join(","));
ok("vectorlab.css : plus de damier sur #stage", !/#stage\s*\{[^}]*linear-gradient/.test(css));
```
Module : `TOKENS = { fond: "#2b2b2b", barre: "#232323", canevas: "#262626", bord: "#3a3a3a", texte: "#d0d0d0", muet: "#9a9a9a", sel: "#2b6fd6", cyan: "#22c3d8", violet: "#cf6fe3", menu: "#1e1e1e", champ: "#1f1f1f" }`, `LEGACY = ["#171a20", "#232833", "#313847", "#2c4a75", "#191d23", "#14171d", "#8b93a0", "#d6d9de", "#101216", "#262b34", "#20242d", "#1c2028", "#3a4150", "#1b2028", "#333b49", "#5b82b8", "#3c5f92", "#20293a", "#eef1f5", "#9db4d6", "#2b3140", "#35588a", "#1f2530", "#0d1015", "#12161a", "#1a1e26", "#2c323d", "#9aa3b2", "#e2e6ec", "#97a0ae", "#cfd6e2", "#1c2129", "#222731", "#2a303b", "#16191f"]`, `hex_herites(css)` (retire les commentaires `/* … */`, cherche chaque hex de LEGACY insensible à la casse).

### Task 2 : `vectorlab.css` — remplacement contrôlé

Table de remplacement (valeur → variable ou nouvelle valeur) : `#101216 #171a20 #14171d #12161a #0d1015 → var(--aff-barre)` ; `#191d23 #1c2028 #1a1e26 #1b2028 #1f2530 → var(--aff-fond)` (le `#stage` : `var(--aff-canevas)`, damier retiré) ; `#232833 #20242d #2b3140 #1c2129 #222731 #2a303b #16191f → var(--aff-champ)` ; `#262b34 #313847 #3a4150 #333b49 #2c323d → var(--aff-bord)` ; `#8b93a0 #9aa3b2 #97a0ae #9db4d6 → var(--aff-muet)` ; `#d6d9de #eef1f5 #e2e6ec #cfd6e2 → var(--aff-texte)` ; `#2c4a75 #20293a #35588a #3c5f92 → var(--aff-sel)` ; `#5b82b8 → #4a90e2`. Puis la couche « R4 densité » en fin de feuille : `body { background: var(--aff-fond); color: var(--aff-texte); font-size: 12px }`, `button` 24 px radius 4 fond #3b3b3b sans bordure, `input/select` 24 px fond `--aff-champ` bordure `--aff-bord` radius 3, `input[type=range]` (piste 4 px #555, poignée 12 px blanche cerclée #2b2b2b), `.regle` fond `--aff-barre`, `#canvasHost svg { box-shadow: 0 0 0 1px #111 }`, `.ap-ligne` 26 px, libellés 11 px, `--pan-champ-h: 24px`, `#nuancier` en place (`position: static; width: auto; box-shadow: none`) quand hébergé.

### Task 3 : le nuancier en place (mod-couleur) et le libellé « Décaler » (mod-style)

- `mod-couleur` : `VL.ouvrirNuancier(hex, cb, ancre, hote)` — si `hote` est fourni (ou si `#panneauCouleurInline` est visible), le nuancier y est déplacé (`hote.appendChild(hote)`) et n'est plus positionné ; `VL.nuancierInline(hote)` ; `mod-pile` : l'onglet Couleur reçoit un `<div id="panneauCouleurInline">` sous `#panneauStyle`, et la pastille Fond y ouvre le nuancier en place (le popover reste pour les autres pastilles).
- `mod-style` : la rangée « Contour » du décalage prend le libellé « Décaler » (id `apDecaler` inchangé).

### Task 4 : preuve, déploiement, relevé

8799, 1400 × 900 : `getComputedStyle(document.body).backgroundColor` = rgb(43,43,43) ; `#stage` background rgb(38,38,38) sans image ; un `input[type=number]` de Transformer fait 24 px ; un `select` fond rgb(31,31,31) ; le nuancier : clic sur la pastille Fond dans l'onglet Couleur → `#nuancier` est un descendant de `#panneauCouleurInline` et `position` static ; choisir une couleur → `style.fond` de l'objet change ; audit de lisibilité (rangées, champs ≥ 22 px) dans les deux personas ; banc-garde vert ; taskkill ; déploiement ; relevé ; mémoire ; push.
