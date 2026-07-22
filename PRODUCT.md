# Product

## Register

product

## Users

Un utilisateur unique : le solo founder du memecoin Solana **deepotus**.
Ingénieur produit, exigeant sur l'esthétique, à l'aise avec les outils pro
(Linear, Resolve, n8n). Il monte ~1 post vidéo par jour, jusqu'à 5 en
campagne, souvent la nuit sur un écran 1440p dans une pièce sombre, entre
deux renders de 30 s à 5 min. Contexte : app Windows locale, desktop only,
navigation clavier prioritaire.

## Product Purpose

Studio local de génération de vidéos virales 9:16 (X / Reels / Shorts)
autour de deepotus. Pipelines : Seedance (image → clip cinématique), HeyGen
(avatar parlant), Composition, Templates spatiaux, News (RSS → script
"prophet" → reel), Timeline (montage multi-clips), Sprite/Tile Lab et
Atelier (game assets, écrans standalone). Le succès : passer de "remplir 4
formulaires puis attendre" à "construire, voir la preview, ship". Le
sentiment cible : **"je pilote un studio, pas un formulaire"**.

## Brand Personality

*Editorial Lab* bioluminescent — un sous-marin scientifique, pas un SaaS.
Trois mots : **calme, dense, pilotable**. Voix sobre et précise ; la touche
deepotus (🐙, "From the deep, for the deep") vit dans le branding et les
empty states, jamais dans les contrôles. L'émotion vient du drame maîtrisé
des renders (halo pulsé, propagation en cascade), pas de la décoration.

## Anti-references

- Le look "AI tool 2023" : gradients mauve/rose, glassmorphism flou, hero
  "✨ Powered by AI".
- Le dashboard SaaS générique : cards identiques, hero-metrics, side-stripes.
- Neumorphism mou, verres pop-corn, illustrations stock.
- Emojis dans les boutons primaires ; modales lourdes là où l'inline suffit ;
  transitions > 400 ms ; boutons fantômes sans affordance sur fond
  non-uniforme.

## Design Principles

1. **Un studio, pas un formulaire** : chaque écran privilégie le canvas et le
   résultat visible ; la configuration sert la preview, jamais l'inverse.
2. **70 % neutre, l'accent fait le travail** : cyan = action/génération,
   violet = composition/batch, amber = sources/attention, vert =
   audio/succès, rouge = destructif/erreur. Un accent a toujours un sens.
3. **Calme, dense, clavier d'abord** : densité grille 4 px, raccourcis
   partout, confirmations inline, rien ne vole la hauteur du canvas 9:16.
4. **Le drame au bon endroit** : la seule théâtralité autorisée est l'état
   des renders (pulse 1.2 Hz, cascade) — la dopamine du studio.
5. **Jamais perdre un brouillon** : tout draft persiste (localStorage),
   toute action destructive se confirme inline avec undo quand possible.

## Accessibility & Inclusion

Contraste AA sur tout texte ≥ 14 px, AAA sur les titres. Focus ring
`2 px solid var(--cyan)` jamais coupé. `prefers-reduced-motion: reduce` →
halo pulse et cascades désactivés, transitions réduites à l'opacité.
Utilisable à 1366×768 et à 200 % de zoom OS. Navigation clavier complète
(palette `/` et Cmd-K, J/K entre nœuds, Esc ferme les panneaux).
