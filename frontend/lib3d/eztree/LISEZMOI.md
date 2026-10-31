# ez-tree 1.1.0 — vendorisé pour le Décor du 3D Studio (t401, 31/10/2026)

Source : paquet npm `@dgreenheck/ez-tree@1.1.0` (https://github.com/dgreenheck/ez-tree), licence **MIT**
(fichier `LICENSE`, © 2024 Daniel Greenheck). Seul `src/lib` est repris : l'application de démonstration
(`src/app`, sons, polices, rochers) ne l'est pas.

Textures d'écorce (`assets/bark`) : le paquet ne porte pas leur licence écrite ; son `assets/bark/README.md` cite
leurs sources, Poly Haven (bark_brown_02, bark_willow_02) et TextureCan, deux bibliothèques publiées en CC0. Sur la
branche principale du dépôt amont, les écorces sont désormais d'ambientCG (CC0). Textures de feuilles
(`assets/leaves`) : fournies avec le paquet, sous sa licence MIT. Relevé t387 :
`docs/superpowers/specs/2026-10-31-api-3d-releve.md`.

Adaptations, toutes mécaniques (script `vendoriser_eztree.py` de la session t401, rejouable) :
- extensions `.js` ajoutées aux imports relatifs (le navigateur ne les devine pas) ;
- `textures.js` : les `import x from './assets/…jpg'` (propres à Vite) deviennent
  `new URL('./assets/…', import.meta.url).href` ;
- les préréglages JSON sont recopiés dans `presets/donnees.js` (module JS, sans attribut d'import).

Aucune autre ligne n'est modifiée. `three` est résolu par la carte d'import de la page (/assets/three).
