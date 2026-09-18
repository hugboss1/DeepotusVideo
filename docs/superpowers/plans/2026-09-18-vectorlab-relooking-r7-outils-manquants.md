# Vectorlab relooking Affinity — R7 campagne de test et outils manquants — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant le module pur).
> Demande de l'utilisateur (18/09, après R6) : retirer les deux pastilles
> « a » (fait, `98f9a8c`, déployé), « teste toutes les fonctions et outils
> de Vectorlab et rajoute des outils manquants qui sont présents dans
> Affinity et pas encore présents dans Vectorlab ».

**Goal :** (1) une campagne de test en réel de TOUS les outils (gestes
pointeur sur la scène), de toutes les entrées de menu disponibles, de
tous les onglets et des actions de panneau, sans erreur de console ni
document invalide, les défauts trouvés corrigés ; (2) les outils
d'Affinity absents du Vectorlab et réalisables sans dépendance : **Main**
(H), **Loupe** (Z), **Plan de travail** (planche au glisser), **Dégradé**
(G′ : glisser pose un dégradé linéaire de fond sur la sélection),
**Transparence** (Y : dégradé de masque au glisser), **Cadre de texte**
(glisser un cadre à paragraphes), **Recadrer** (C′ : rognage d'une image au
glisser), et trois pinceaux raster de retouche **Flou**, **Éclaircir**,
**Assombrir** (densité − / +) — chacun dans sa famille, avec icône,
raccourci, phrase d'état et champs de contexte.

**Architecture :** `mod-outils3.js` feuille : `zoom_rect(rect, scene,
bornes)` → {zoom, tx, ty}, `zoom_point(vue, pt, facteur)`,
`degrade_de_glisser(p1, p2, couleurs)` → spec de `op_degrade_creer`,
`rognage_de_rect(objetImage, rectDoc)` → rognage en pixels natifs borné,
`cadre_de_rect(rect, style, contenu)` → objet cadre, `rect_normalise(a, b,
min)`, `disque_masque(w, h, cx, cy, r)` → Uint8Array pour les pinceaux de
retouche ; `mod-outils3ui.js` : gestes en CAPTURE sur `#stage` (patron de
mod-exportplus), une commande par geste via `VL.executer`, aperçu dans
`#ovTmp` ; pinceaux raster branchés sur les primitives de `mod-pixel`
(`flou`, `hsl` avec masque disque) et le journal existant de mod-pixelui
(`VL.pixelAppliquer` exposé) ; familles / icônes / contexte / hints étendus.

**Tech :** vanilla ESM ; node `qa/run.mjs` ; campagne navigateur (script de preuve).

---

### Task 1 : `mod-outils3.js` (RED → vert)

```js
// outils3.test.mjs
import { zoom_rect, zoom_point, degrade_de_glisser, rognage_de_rect, cadre_de_rect, rect_normalise, disque_masque } from "../js/mod-outils3.js";
ok("rect_normalise : deux points → {x,y,w,h} positif ; sous le minimum → null", …);
ok("zoom_rect : la scène cadre le rectangle (marge 40), bornée 0,05..16", …);
ok("zoom_point : ×1,25 autour du point, le point reste fixe à l'écran", …);
ok("degrade_de_glisser : linéaire de p1 à p2, deux stops couleur de fond → blanc", …);
ok("rognage_de_rect : rect document → pixels natifs, borné à nat, null si vide", …);
ok("cadre_de_rect : objet cadre avec contenu par défaut, style police / corps", …);
ok("disque_masque : 255 dans le disque, 0 dehors, borné au tampon", …);
```

### Task 2 : `mod-outils3ui.js` + familles + icônes + contexte + hints

- Outils : `main` (glisser = panoramique, curseur grab), `loupe` (clic ×1,25 au point, Alt = ÷1,25, glisser ≥ 6 px = cadrer), `planche` (glisser → `op_planche_ajouter`, nom « Planche n »), `degrade` (glisser sur la sélection → `op_degrade_creer` + `op_style` fond `grad:<id>` ; sans sélection : toast), `transparence` (glisser → `op_degrade_transparence(sel, rect)`), `cadre` (glisser → `op_ajouter` cadre, puis `VL.editerTexte` si dispo), `recadrer` (glisser sur une image sélectionnée → `op_image_rogner` ; double-clic = retirer le rognage), `px-flou`, `px-eclaircir`, `px-assombrir` (persona Pixel : à chaque point du glisser, `flou(t, 1, disque)` / `hsl(t, {l: ±6}, disque)` sur `etat.px.tampon`, puis `VL.pixelValider()` au pointerup — exposer dans mod-pixelui `VL.pixelValider = () => ecrire()` ou équivalent existant).
- `mod-familles` : Vecteur — `deplacer`, `noeuds`, `plume`, `formes`, `constructeur`, `texte [texte, cadre]`, `image [image, recadrer]`, `degrade [degrade, transparence]`, `apparence`, `symbole`, `mesure`, `tuiles`, `planche [planche]`, `ia`, `vue [main, loupe]`, `tranche` ; Pixel — `deplacer`, `pxselection`, `pxpinceau`, `pxretouche [px-flou, px-eclaircir, px-assombrir]`, `pxseau`, `pxart`, `recadrer`, `vue`, `tranche` (banc familles : 16 Vecteur / 9 Pixel).
- `mod-icones` : main, loupe, planche, degrade, transparence, cadre, recadrer, px-flou, px-eclaircir, px-assombrir (banc icônes : toutes les familles couvertes).
- `mod-persona.persona_de_outil` : `main`, `loupe`, `recadrer` → « tous ».
- `mod-contexte` : `loupe` → bascule « Cadrer au glisser » (non, YAGNI : rien) ; `px-flou / px-eclaircir / px-assombrir` → rayon + dureté ; `degrade` → aucun ; `planche` → aucun.
- Raccourcis (surTouche chaîné) : H main, Z loupe, Y transparence ; `VL.hints` : phrases des dix outils.

### Task 3 : campagne de test en réel

Script de preuve (8799, 1400 × 900) qui, pour chaque outil visible des deux personas, joue un geste pointeur réel (`pointerdown` / `pointermove` / `pointerup` sur `document.elementFromPoint` de la scène) puis vérifie : aucune exception (`window.onerror` capturé), `parserDoc(etat.doc)` accepte le document, le compteur d'objets a bougé quand l'outil crée ; pour chaque entrée de menu dont `VL.menuPeut` est vrai (prompt / confirm / open stubés, exports et IA exclus), l'action s'exécute sans erreur ; chaque onglet s'active ; chaque bouton de `#calquesActions` et de la barre contextuelle répond. Les défauts trouvés sont corrigés dans ce lot et listés dans le relevé.

### Task 4 : déploiement, relevé, mémoire, push.
