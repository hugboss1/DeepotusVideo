# Étape 2 — Dessiner la suite « Deepotus Glyph »

Dossier `R\` = `C:\Users\olivi\AppData\Local\Temp\claude\C--Users-olivi-DeepotusVideo\5f390379-8af8-4f85-bbcd-1718a3c27423\scratchpad\refonte\`. N'écris que dans `R\svg\` (les SVG), `R\motifs.js` (si ta mission le dit) et ton script `R\dessin\<ta-mission>.js`.

## À lire avant de dessiner
- `R\CHARTE.md` — la loi. Surtout §2 (grille, épaisseurs mini 2, espaces mini 1,6), §3 (deux tons .38/1, **règle du monochrome** : le sujet est DÉCOUPÉ dans le support avec une réserve 1,4–1,6, jamais posé par-dessus), §4 (badges), §6 (séries).
- `R\geo.js` — primitives (rect, circle, ring, poly, ngon, star, pill, arrow, plus, cross, rot, check, badge, svg). Assemble des sous-chemins dans un path `evenodd` pour faire des trous.
- `R\motifs.js` — les motifs partagés (document, dossier, image, loupe, cadenas, œil, etc.). **Réutilise-les** : le même objet doit avoir le même dessin dans toute la suite (le dossier de « nouveau dossier » = le dossier de « Bibliothèque » réduit ou recadré, etc.).
- `R\lexique.json` — pour chaque clé : `sens`, `dessin` (métaphore, sujet, support, badge, série), `ne_pas_confondre_avec`. Le brief du lexique fait foi ; tu peux améliorer la composition, jamais changer la métaphore sans le noter.
- Références (idées, PAS à recopier tel quel car elles violent la règle du monochrome) : le kit `..\kit_zip\deepotusvideo-icons\*.svg`, les 27 icônes en production `R\design15_27_icones.md`, et l'icône actuelle de chaque usage (`..\out2\inventaire-icones.json`, champ `rendu`).

## Méthode
1. Écris `R\dessin\<mission>.js` : `const G=require("../geo.js"), M=require("../motifs.js")` ; une fonction par icône ; écrit `R\svg\<clé>.svg` via `G.svg([...])`.
2. Lance `python -I ..\qa\lint.py R\svg` (depuis `R\`) : 0 erreur exigée sur tes fichiers.
3. Contrôle toi-même, pour chaque icône : à 16 px (1 unité = 0,67 px) chaque partie pleine ≥ 2 unités et chaque espace ≥ 1,6 ; silhouette en un seul ton différente de ses `ne_pas_confondre_avec` ; masse visuelle comparable à ses voisines (pas d'icône minuscule perdue au centre, pas de pavé plein).
4. Évite les silhouettes génériques : un carré ou un disque plein en support d'une famille entière est interdit (CHARTE §3). Donne à chaque icône une forme extérieure qui lui est propre.
5. Séries (CHARTE §6) : mêmes gabarits, même épaisseur, même position du sujet ; seule la partie qui porte la différence change.

## Réponse finale
Nombre d'icônes écrites, liste de celles dont tu doutes (lisibilité à 16 px ou proximité avec une autre clé) et pourquoi. Le banc visuel (rendu navigateur, comparaison de silhouettes deux à deux) sera lancé ensuite par le coordinateur, qui te renverra une liste de corrections.

## Retour d'expérience des fondations (à appliquer)
- Charge TOUJOURS `const M = require("../motifs.js")` (il corrige aussi `G.pill`/`G.check` en mémoire ; geo.js est maintenant corrigé à la source).
- Compose tes icônes à deux tons avec `M.icone([{d: sujet}, {d: support, op: .38}, ...])` (calques du HAUT vers le BAS) : la réserve monochrome est calculée automatiquement par soustraction exacte. Un trou posé à la main en evenodd qui DÉBORDE de la forme se remplit : ne le fais pas.
- N'utilise pas `G.check` (jonction trouée) : `M.coche`. Les badges : `M.badge(type)` en tête de `M.icone`.
- Si tu passes par `G.svg` directement, applique `M.fin` (arrondi final au dixième).
- **Ne modifie pas les signatures de `motifs.js`** (d'autres dessinateurs travaillent en parallèle). Tu peux AJOUTER un motif dans un fichier à toi `R\dessin\motifs-<mission>.js` ; si un objet manque à motifs.js et sert à plusieurs familles, signale-le dans ta réponse.
- Contrôle visuel : `node ..\fond_tmp\planche.js R\svg <filtre>` écrit une planche HTML (16, 24, silhouette, 72 px) — ouvre-la si tu sais produire un PNG, sinon relis les coordonnées.
- Ne réécris JAMAIS un fichier `R\svg\` qui n'est pas de ta famille.
