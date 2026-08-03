# Chantier 9e — Tuiles seamless (Tile Lab) + détourage chroma

Reporté par la spec 2D du 19/07 (« tuiles seamless (chantier 9e reporté) ») ;
acté par Olivier le 20/07 (« go pour 9e »). S'appuie sur les briques 9b :
op `tile-preview` + `seam_score` de `pixel_ops.py`, route `/api/images/process`.

## Périmètre

1. **Op locale `seamless`** (`/api/images/process`, pur PIL, gratuit, sync) :
   - `method: "offset"` (défaut) — décalage 50/50 (`ImageChops.offset`) puis
     fondu de la croix centrale avec l'original (masque en tente, largeur
     `blend` % du petit côté, 5-45, défaut 20). Les bords opposés deviennent
     des colonnes/lignes adjacentes de l'image source → raccord quasi parfait.
   - `method: "mirror"` — mosaïque 2×2 en miroir (quadrants symétriques),
     raccord mathématiquement parfait (score 0), rendu kaléidoscope.
   - `square: true` (défaut) — recadrage centré au carré ; `target_px`
     optionnel (64-1024) — redimensionnement LANCZOS.
   - Réponse : `{images: [gen_*.png], seam_before, seam_after, method}` ;
     `seam_score` refactorisé en helper public (réutilisé par `tile-preview`).

2. **Tile Lab** (`/tilelab`, standalone hors bundle comme `/spritelab`) :
   picker d'images Library (recherche) → réglages (méthode, fondu, carré,
   taille, pixel-art 9b optionnel enchaîné) → « Rendre seamless » → préviz
   pavage 3×3 avant/après avec les deux scores → le résultat est déjà dans la
   Library (`gen_*.png`) ; « → Studio » (nœud Image) en iframe comme 9d.
   Poignée QA `window.__tl`.

3. **Hub Game Assets** : sous-onglet « Tuiles » (3D | Sprites 2D | Tuiles),
   `deepotus:navigate` accepte `subtab: "tiles"` — patcher à anchors
   `scripts/patch_bundle_tilelab.py` (backup `.bak_tilelab`).

4. **Détourage `chroma` du Sprite Lab** (notes 9e : Seedance n'honore pas
   toujours le fond vert et rembg mange les sujets sombres) :
   `pixel_ops.chroma_key(img, tolerance)` — clé = couleur médiane du pourtour,
   alpha 0 sous `tolerance` (défaut 28), rampe jusqu'à ×1,6 ; garde-fou : si
   la couverture opaque sort de [5 %, 95 %], la frame d'origine est conservée
   et marquée `bg_failed` (philosophie 9a). `remove_bg: "chroma"` accepté par
   `normalize_opts` (+ `chroma_tolerance` 4-80), branche locale gratuite dans
   `generate_sprites`, option « Chroma (fond uni) » dans le Sprite Lab.

## Hors périmètre (inchangé)

Tileset Forge complet (grille multi-outils), Wang tiles, génération IA de
textures, vignettes 404 de la file d'attente (cosmétique bundle, à part).

## Recette

- pytest `backend/tests/test_pixel_seamless.py` : normalisations (bornes,
  erreurs), offset — même taille, déterminisme byte-identique,
  `seam_after < seam_before` et `≤ 10` sur pseudo-photo ; mirror —
  `seam_after == 0` ; carré/target_px honorés ; chroma_key — fond vert
  transparent, sujet sombre conservé, garde-fou uni/plein ; suites 9a/9b
  existantes toujours vertes.
- QA Puppeteer `scripts/qa/qa-tilelab.js` : sous-onglet « Tuiles » présent,
  run réel sur une image Library (scores affichés, after < before), résultat
  dans la Library, option chroma visible dans le Sprite Lab ; re-run de
  `qa-previz-restore.js` (non-régression T1).
- Déploiement : backend + frontends + bundle patché, restart, health OK.
