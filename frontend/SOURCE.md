# Code source React — provenance et état

## D'où vient `frontend/src`

Retrouvé le 03/08/2026 sur cette machine dans
`C:\Users\olivi\Projects\deepotus-video-gen-v1.6\frontend\src`
(dernier fichier modifié le 16/06/2026 — le dépôt est né le 19/06/2026 avec le
commit « Initial commit: Deepotus Video Gen v1.15.1 »).
Copies plus anciennes : `D:\olivi\telechargements\deepotus-video-gen[-v1.1]`.

## Preuve d'authenticité (reproduite le 03/08/2026)

`npm ci && npm run build` sur ce source (Node v22.23.1, lockfile du repo)
produit **exactement** les assets du dossier retrouvé, aux mêmes noms hachés
par Vite :

| Asset | sha256 (16 premiers hex) |
|---|---|
| `assets/index-BEOJX8L5.js` (434 732 o) | `b470122ee0eaa7a3` |
| `assets/index-CBtHJYWz.css` | `289c97842c40ffe1` |

Le bundle du commit initial (455 547 o, mêmes noms de fichiers) = **ce build +
les 5 patchs historiques** (`patch_bundle_{engine,animate,concat,numbering,
presets}.py`, ~20 Ko injectés, marqueurs `__dz`). Les 6 fichiers de config du
repo (`package.json`, lockfile, `vite.config.js`, `tailwind.config.js`,
`postcss.config.js`, `index.html`) sont identiques à ceux du dossier retrouvé
(fins de ligne près).

## ⚠️ L'écart avec le bundle actuel

Ce source correspond à l'état **v1.15.1 avant tout patch**. Depuis, TOUTES les
évolutions UI ont été faites par patchs chirurgicaux du bundle minifié
(`scripts/patch_bundle_*.py` + chantiers 11/V/W : Shell Pro, Quick Voice Over,
nœud Voiceover, modèles vidéo/voix à la volée, Gemini, spritelab/tilelab,
thème Cinema v2…).

Conséquences pratiques :

1. **Ne jamais écraser `frontend/dist/` avec un `npm run build`** de ce source :
   on perdrait toutes les fonctionnalités patchées. `dist/` reste la référence
   exécutée tant que le source n'a pas été remis à niveau.
2. Remise à niveau (chantier futur) : rejouer les deltas des patchs dans le
   source (chaque `patch_bundle_*.py` documente son injection), jusqu'à ce que
   `npm run build` reproduise l'équivalent du bundle patché — le jour où c'est
   fait, les patchs pourront être retirés et `src/` redeviendra la seule
   source de vérité.

## Rebuild de contrôle

```bash
cd frontend
npm ci
npm run build   # NE PAS committer le dist résultant (v1.15.1 nu)
```
