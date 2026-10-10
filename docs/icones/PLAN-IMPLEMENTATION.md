# Icônes « Deepotus Glyph » — plan d'implémentation

État au 10/10/2026. L'utilisateur a fait ses choix dans l'inventaire (artifact https://claude.ai/artifact/6owMyDz4H4UCCTDNdY1DuD,
collection `choix`, recopiée dans `choix-utilisateur.json`) : la refonte partout, sauf trois préférences
(logo Deepotus et splash gardés en image, pointeur Lucide pour l'outil Doigt du Photolab).

## Sources

| Fichier | Rôle |
|---|---|
| `suite-finale/svg/dz-*.svg` | la refonte : 524 icônes, une par fonction |
| `suite-finale/lexique.json` | sens de chaque clé, voisines à ne pas confondre, usages, drapeau mobile |
| `suite-finale/implementation.json` | **la liste de travail** : pour chaque usage (PC et mobile), `source` (fichier:ligne ou offset du bundle + extrait), l'ancien dessin, `cle_finale`, ou `emoji_conserve` / texte seul avec `raison_finale` |
| `choix-utilisateur.json` | les choix de l'utilisateur |
| `generateurs/refonte/CHARTE.md` | la charte de dessin (règle du monochrome, deux tons, badges, séries) |
| `inventaire-icones.json` / `.csv` | le relevé complet de départ |

## G0 — socle partagé (ce lot)

`scripts/icones/construire_suite.py` écrit `frontend/shared/icons/` et sa copie servie `frontend/dist/shared/icons/`
(identiques octet pour octet) :

- `dz-icons.svg` : sprite, un `<symbol id="dz-…">` par icône dessinée ;
- `dz-icons.js` : `window.dzIcone(cle, {taille, titre, classe})` rend le balisage (SVG en ligne, ou `<img>` pour le
  logo et le splash) ; `window.DZ_ICONS`, `window.DZ_ICONS_IMAGES` ;
- `dz-icons.css` : classe `.dzi` (1em, `currentColor`), tailles `.dzi--16/18/20/24`.

Banc : `backend/tests/test_icones_suite.py`.

### Règles d'emploi dans les labs

```html
<link rel="stylesheet" href="/shared/icons/dz-icons.css">
<script src="/shared/icons/dz-icons.js"></script>   <!-- après dz-i18n.js, avant les modules du lab -->
```

```js
bouton.innerHTML = dzIcone("dz-action-supprimer", {taille: 16});
bouton.setAttribute("aria-label", dzT("…"));          // le sens est porté par le bouton, jamais par l'icône seule
```

- Une icône = une fonction : la clé est celle de `implementation.json`, jamais une autre « qui ressemble ».
- Emojis conservés (`emoji_conserve: true`) : ne pas toucher.
- Texte seul (`cle_finale` vide, sans emoji) : ne rien ajouter.
- Taille : 16 dans les listes et menus, 18 dans les barres d'outils et le rail, 20–24 dans les en-têtes.

## Lots

| Lot | Périmètre | Usages à poser | Remarques |
|---|---|---|---|
| G0 | socle partagé | — | ce lot |
| G1 | coque React (bundle `index-BEOJX8L5.js` + couches `frontend/patches/*.js`) | ~1 056 | maillon de queue `patch_bundle_dzglyph.py`, AVANT `version` ; ajoute les clés à la carte `Sh` et repointe chaque site d'appel (`X`, `K icon`, `se`, `le`), `__dzCatSVG`, catégories de nœuds `Qr`, `DZM_TB_TRACES`, emojis et glyphes des écrans ; le code qui vit dans une couche se modifie dans la couche puis `refresh_layer` ; corrige `save`/`undo` absents et les flèches du Scheduler |
| G2 | Card Forge (`frontend/cardforge`) | 166 | `RAIL_SVG`, chevron unique, natures de blocs |
| G3 | Vectorlab (`frontend/vectorlab`) | 288 | sprite `mod-icones.js` remplacé, flyouts, panneaux |
| G4 | Photolab (`frontend/photolab`) | 289 | dossier `icones/` (amont photocraft) remplacé par la suite ; outil Doigt = pointeur Lucide (choix utilisateur) |
| G5 | Spritelab + Tilelab | 124 | emojis et glyphes → suite |
| G6 | Atelier, Matières, Établi, Plateau, Studio 3D, partagés (`dz-champ-ia.js`…) | ~190 | |
| G7 | compagnon mobile (`deepotus-mobile`, dépôt séparé) | 82 | `dz-icons.mobile.ts` + `react-native-svg` ; icône d'app, splash, notification Android |

Chaque lot : une branche `chantier/icones-glyph-<lot>` depuis G0, une PR, bancs verts du périmètre (y compris ceux qui
figent des glyphes : les mettre à jour dans le même lot), preuve à l'écran sur le backend de preuve.
