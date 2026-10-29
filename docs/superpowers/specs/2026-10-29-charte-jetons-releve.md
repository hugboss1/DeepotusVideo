# Charte visuelle : relevé et jetons communs (t370)

Date : 29/10/2026. Lot A du plan `2026-10-29-finitions-esthetiques-chemins-fils-apparence.md` (décisions D1-D6
validées). t370 est la fondation : elle pose les jetons et la feuille partagée. L'harmonisation écran par écran
reste à t374, les curseurs à t373, les lecteurs à t372, la palette à t382 et le thème clair à t383.

## 1. Méthode

`scripts/charte_releve.py` parcourt :

- la **coque** : feuille et bundle prébâtis (`frontend/dist/assets/index-*.css|js`), `theme-v2.css`,
  `dist/index.html` et les feuilles servies dans `dist/shared` ;
- chaque **lab** (`frontend/<lab>`) et `frontend/shared`, sans le code tiers ni le code généré (`vendor/`, `qa/`,
  `*.min.*`, three.js, dictionnaire i18n, sprite d'icônes).

Il compte trois formes d'écriture : les déclarations CSS (feuilles et chaînes CSS injectées par les modules), les
objets de style React (`borderRadius:6`, où un nombre nu vaut des px) et les classes Tailwind du bundle. Les
tableaux complets par zone sont en annexe (§7). On les régénère avec
`python scripts/charte_releve.py --md <fichier>`.

## 2. Ce que montre le relevé

**Couleurs de texte.** On trouve quatre encres partout, sous des noms différents :

| Niveau | Coque et labs | Bundle (Son & VFX, sous-titres) | `/shared` (DESIGN §15) | Vectorlab |
|---|---|---|---|---|
| fort | `--ink-strong` (#f2efe9) | — | `--txt-hi` (jamais défini, repli `--ink-strong`) | `--aff-texte` #d0d0d0 |
| corps | `--ink` (#c4bfb6) | `--ink2`, `--sub-ink2` | `--txt-base` (repli) | — |
| discret | `--ink-soft` (#8a857d) | `--ink3`, `--sub-ink3` | — | `--aff-muet` #9a9a9a |
| muet | `--ink-muted` (#55514c) | `--ink4`, `--sub-ink4` | `--txt-mid` (repli `--ink-muted`) | — |

La coque écrit 315 couleurs de texte distinctes en 2 152 occurrences. Les plus fréquentes sont des variables, mais
on relève aussi des hexadécimaux en dur : `#fff`, `#e6e9ee`, `#e08a8a`, `#ddd` et les replis de `/shared`. Le
Vectorlab garde sa propre échelle de gris (aspect Affinity), et `/shared` emploie `--txt-mid` pour le niveau
« muet », alors que DESIGN.md §15 en fait le niveau secondaire. Ces écarts sont à traiter en t374.

**Polices.** Elles sont déjà presque toutes en variables : `var(--f-mono)` (×198 dans la coque), `var(--f-ui)`,
`var(--f-display)`. Les écarts sont les alias de Son & VFX (`--sub-mono`, `--vfx-mono`) et quelques piles en dur
(`JetBrains Mono,monospace`, `Consolas, monospace` dans le Vectorlab).

**Tailles.** La coque en compte 72 distinctes. Entre 9 et 13,5 px, presque chaque demi-pixel est employé : `11`
×275, `12` ×167, `10.5` ×142, `10px` ×134, `11.5` ×113, `9.5px` ×43… Les labs vont de 8 à 13 valeurs chacun,
toutes entre 8,5 et 17 px.

**Graisses.** Pour l'essentiel 600, puis 500 et 700. On trouve aussi un 800 dans le Vectorlab et un `bolder` dans
la coque.

**Rayons.** C'est l'écart le plus net avec la consigne « angles vifs ». La coque écrit `var(--r-sm)` ×122 et
`var(--r)` ×28, mais aussi des littéraux (`6` ×78, `4` ×59, `6px` ×55, `8` ×43…). Les labs ont 1 à 103 rayons
littéraux chacun. Le Photolab écrit `3px` ×59, et le Cardforge `8px` ×34 et `99px` ×29.

**Espacements.** On relève 317 valeurs de padding distinctes dans la coque. Les marches de 4 dominent (0, 4, 6, 8,
10, 12, 14), avec beaucoup de valeurs impaires entre elles (3, 5, 7, 9). Pour les `gap`, ce sont surtout 6 et 8.

## 3. Les jetons (feuille `frontend/shared/dz-charte.css`)

| Jeton | Valeur | Rôle |
|---|---|---|
| `--fg-1` | `var(--ink-strong)` | titres, valeurs, libellé sélectionné |
| `--fg-2` | `var(--ink)` | corps, libellés |
| `--fg-3` | `var(--ink-soft)` | méta, légendes, en-têtes de panneau |
| `--fg-4` | `var(--ink-muted)` | indices, placeholders, désactivé |
| `--fg-accent`, `--fg-on-accent` | `var(--accent)`, `var(--accent-ink)` | action, coût ; texte sur aplat doré |
| `--font-ui`, `--font-mono`, `--font-display` | `var(--f-ui)`, `var(--f-mono)`, `var(--f-display)` (repli : pile complète) | sans pour l'interface, mono pour les mesures et les en-têtes en capitales |
| `--fs-1` … `--fs-5` | 10 · 11 · 12 · 13,5 · 16 px | 54 % des 2 760 tailles en px relevées tombent pile sur un palier, 91 % à ±0,5 px près |
| `--fw-1` … `--fw-3` | 400 · 500 · 600 | trois graisses seulement |
| `--ls-caps` | .12em | interlettrage des en-têtes mono en capitales |
| `--pad-1` … `--pad-4` | 4 · 8 · 12 · 16 px | puce, contrôle (marge de panneau t371), carte, dialogue |
| `--radius` | `0` | angles vifs |
| `--r-sm`, `--r`, `--r-lg` | `var(--radius)` | les anciens rayons, rebranchés |

**Règles.**

1. La feuille ne contient **qu'un bloc `:root` de propriétés personnalisées**. La charger ne modifie aucun
   sélecteur d'élément, donc aucun écran ne casse.
2. **Tout passe par des variables.** Les couleurs et les polices pointent vers les jetons de base (`--ink-*`,
   `--accent`, `--f-*`), avec un repli sur les valeurs Cinema.
3. **Pour t382 (palette) et t383 (thème clair)** : il faut redéfinir les jetons de BASE (`--bg-*`, `--ink-*`,
   `--accent`, `--green`, `--red`) sur `:root` de la coque et de chaque iframe de lab. `--fg-*` suivent alors
   d'eux-mêmes. `deepotus.tokens.css` porte déjà un bloc `[data-theme="light"]`. Attention : une portée qui
   redéfinit `--ink-*` sur un sous-arbre (par exemple `.dzsvm` de Son & VFX) ne change pas `--fg-*`, qui est
   résolu sur `:root`. Dans ces portées, il faut écrire `--ink-*` ou redéclarer `--fg-*`.
4. **`--r-pill` (999px) n'est pas touché.** Il sert aux pastilles d'état rondes.

## 4. Chargement : une feuille, partout

| Hôte | Comment |
|---|---|
| Coque (`frontend/dist/index.html`) | `<link href="/shared/dz-charte.css">` en dernier, **après** la feuille du bundle (sinon `--r-sm:6px` du bundle l'emporte) |
| Avatar, Cardforge, Établi, Material Forge, Photolab, Plateau, 3D Studio (+ Comparer), Vectorlab, WhatsApp | `@import` en tête de `deepotus.tokens.css`, que leur feuille importe déjà |
| Atelier (`index.html`, `preview.html`) | `@import` en tête de `atelier.css` (cette feuille recopie les jetons) |
| Sprite Lab, Tile Lab | `@import` en tête de `spritelab.css`, que le Tile Lab charge aussi |

Un `@import` placé après une règle est **ignoré** par le navigateur. Le banc vérifie donc la chaîne d'`@import`
*valides* jusqu'à la feuille.

## 5. Ce qui est déjà branché (trivial) et ce qui reste

**Branché par t370.** `--r-sm`, `--r` et `--r-lg` valent 0 partout : dans la coque (162 usages de `var(--r*)`
dans le bundle), dans `deepotus.tokens.css` (et donc dans tous les labs qui l'importent), et dans les copies de
l'Atelier et du Sprite Lab. Le pouce de défilement commun de `deepotus.tokens.css` (99px) est lui aussi passé à
angle vif.

**Reste à t374.** Il faut retirer les rayons littéraux (le cliquet ci-dessous les compte), ramener les couleurs
de texte en dur et les échelles parallèles (`--ink2..4`, `--txt-*`, `--aff-*`) sur `--fg-*`, et réduire les
tailles et les marges aux paliers `--fs-*` et `--pad-*`.

## 6. Bancs

`backend/tests/test_charte_jetons.py` (50 contrôles) :

- **[J]** jetons présents, un seul bloc `:root` qui ne contient que des `--*`, couleurs et polices en
  `var(--…)`, `--fg-1..4` dans l'ordre des quatre encres, `--radius:0`, rayons hérités rebranchés,
  `--r-pill` intact, paliers croissants ;
- **[C]** copie `frontend/dist/shared/dz-charte.css` identique ;
- **[L]** les 14 pages de labs et la coque chargent la feuille (lien, ou `@import` valide transitif), et la coque
  la lie après la feuille du bundle ;
- **[R]** la charte ne déclare aucun `border-radius`, `deepotus.tokens.css` n'a aucun rayon > 0 hors
  **exceptions listées**, aucune feuille servie ne redéfinit `--r-sm/--r/--r-lg` autrement que par
  `var(--radius)`, et le **cliquet** par zone (`scripts/charte_rayons_plafond.json`) ne peut que baisser.

**Exceptions listées (rond assumé).**

| Où | Valeur | Raison |
|---|---|---|
| `.dt-dot` (`deepotus.tokens.css`) | 99px | pastille d'état ronde (ok / off / idle) |
| cliquet, toutes zones | `50%`, `99px`, ≥ 100 px, `var(--r-pill)`, `rounded-full` | pastilles, points de couleur, poignées circulaires, avatars : ronds par nature, non comptés |

**Cliquet au 29/10/2026** (rayons littéraux > 0, hors ronds) : coque 519 · Cardforge 103 · Photolab 93 ·
Vectorlab 87 · 3D Studio 28 · Atelier 27 · Material Forge 27 · Sprite Lab 26 · `/shared` 21 · Tile Lab 20 ·
Avatar 3 · Plateau 2 · WhatsApp 2 · Établi 1 · lib3d 0 · meshy 0. t374 baisse le plafond à chaque écran traité.

**Mutations** (`scripts/mutations_charte.py`) : 14 sur 14 sont tuées. Voici ce que chacune fait :

- retire le lien de la coque ;
- place le lien avant la feuille du bundle ;
- retire l'`@import` des jetons partagés ;
- place un `@import` après une règle ;
- retire du Photolab l'import des jetons ;
- passe `--radius` à 2px ;
- passe `--r` à 10px ;
- retire `--fg-2` ;
- écrit `--fg-1` en hexadécimal ;
- ajoute une règle d'élément dans la charte ;
- passe `--r-lg` à 14px dans les jetons ;
- arrondit le pouce de défilement ;
- passe `--r-sm` à 6px dans l'Atelier ;
- ajoute un rayon dans le lab WhatsApp.

## 6-bis. Preuve sur backend jetable (29/10/2026)

Deux backends de preuve ont été lancés avec le python embarqué, un dossier de données jetable et aucune clé :
« avant » sur 8798 (main 7dc0d907) et « après » sur 8799 (cette branche). On a compté les éléments visibles dont le
rayon calculé est > 0, à écran et langue identiques :

| Écran | Langue | Éléments visibles | Arrondis avant | Arrondis après | Restent (t374) |
|---|---|---:|---:|---:|---|
| Quick (coque) | FR | 487 | 78 | 42 | 29 pilules 999px + 2 ronds (exceptions), 11 littéraux (7/8/4/3/20 px) |
| Quick (coque) | EN | 487 | 78 | 42 | idem |
| Établi | FR | 101 | 31 | 1 | 1 pilule 999px |
| Établi | EN | 101 | 31 | 1 | idem |
| Card Forge | FR | 362 | 118 | 117 | littéraux 8/7/10/5/3 px du lab (cliquet 103) |

Dans les deux langues, `--fg-1` se résout en `#f2efe9` et `--r` en `0`. Les mises en page sont identiques (même
nombre d'éléments visibles) : la feuille ne casse aucun écran. Le Card Forge ne change presque pas, car ses
rayons sont écrits en dur. C'est précisément ce que t374 traitera.

## 7. Annexe : relevé complet par zone

#### coque (10 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 315 | 2152 | `var(--ink-soft)` ×348 · `var(--ink-strong)` ×226 · `var(--ink)` ×206 · `var(--ink-muted)` ×158 · `var(--ink2)` ×71 · `var(--ink3)` ×71 · `var(--red)` ×65 · `var(--ink4)` ×56 · `var(--amber)` ×55 · `var(--cyan)` ×53 · `var(--sub-ink4)` ×41 · `var(--accent)` ×35 |
| Couleurs de texte (classes Tailwind) | 9 | 13 | `text-slate-100` ×3 · `text-slate-200` ×3 · `text-amber-300` ×1 · `text-amber-400` ×1 · `text-slate-300` ×1 · `text-slate-400` ×1 · `text-slate-500` ×1 · `text-slate-600` ×1 · `text-white` ×1 |
| Polices | 25 | 393 | `var(--f-mono)` ×198 · `var(--sub-mono)` ×36 · `inherit` ×30 · `var(--f-ui)` ×30 · `var(--f-mono,monospace)` ×27 · `var(--f-mono` ×26 · `var(--vfx-mono)` ×19 · `JetBrains Mono,monospace` ×3 · `var(--f-mono, Consolas, monospace)` ×3 · `ui-sans-serif,system-ui,sans-serif` ×2 · `Space Grotesk,system-ui,sans-serif` ×2 · `var(--f-display)` ×2 |
| Polices (Tailwind) | 3 | 17 | `font-display` ×15 · `font-mono` ×1 · `font-sans` ×1 |
| Tailles | 72 | 1570 | `11` ×275 · `12` ×167 · `10.5` ×142 · `10px` ×134 · `11.5` ×113 · `11px` ×103 · `12px` ×68 · `10` ×65 · `12.5` ×61 · `9px` ×59 · `10.5px` ×56 · `9.5px` ×43 |
| Tailles (Tailwind) | 3 | 5 | `text-xs` ×2 · `text-sm` ×2 · `text-2xl` ×1 |
| Graisses | 9 | 174 | `600` ×111 · `700` ×22 · `500` ×22 · `400 700` ×6 · `inherit` ×3 · `400` ×3 · `400 600` ×3 · `400 500` ×3 · `bolder` ×1 |
| Graisses (Tailwind) | 3 | 3 | `font-bold` ×1 · `font-medium` ×1 · `font-semibold` ×1 |
| Rayons | 51 | 784 | `var(--r-sm)` ×122 · `6` ×78 · `4` ×59 · `6px` ×55 · `8` ×43 · `8px` ×37 · `7px` ×34 · `50%` ×32 · `999px` ×30 · `var(--r)` ×28 · `999` ×27 · `5px` ×27 |
| Rayons (Tailwind) | 4 | 11 | `rounded` ×7 · `rounded-lg` ×2 · `rounded-full` ×1 · `rounded-md` ×1 |
| Marges internes (padding) | 234 | 1013 | `8` ×36 · `0 8px` ×30 · `6px 8px` ×29 · `0` ×28 · `4px 8px` ×26 · `10` ×24 · `6px 10px` ×22 · `14` ×21 · `0 10px` ×18 · `8px 10px` ×17 · `14px 18px` ×17 · `3px 8px` ×16 |
| Marges internes (Tailwind) | 21 | 30 | `py-1` ×4 · `p-1` ×2 · `px-2` ×2 · `px-3` ×2 · `py-2` ×2 · `px-4` ×2 · `py-3` ×2 · `p-2` ×1 · `p-3` ×1 · `p-4` ×1 · `py-0` ×1 · `px-1` ×1 |
| Écarts (gap) | 50 | 865 | `8` ×128 · `6` ×121 · `8px` ×73 · `10` ×73 · `6px` ×70 · `12` ×49 · `4px` ×48 · `4` ×43 · `7px` ×33 · `5px` ×31 · `14` ×26 · `2px` ×23 |

#### atelier (2 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 20 | 123 | `var(--ink-strong)` ×29 · `var(--ink-soft)` ×24 · `var(--ink-muted)` ×20 · `var(--ink)` ×13 · `var(--amber)` ×7 · `var(--cyan)` ×5 · `var(--red)` ×4 · `var(--accent-ink)` ×2 · `transparent` ×2 · `var(--k-character)` ×2 · `var(--k-place)` ×2 · `var(--k-object)` ×2 |
| Polices | 3 | 50 | `var(--f-mono)` ×32 · `var(--f-ui)` ×15 · `var(--f-display)` ×3 |
| Polices (Tailwind) | 1 | 4 | `font-display` ×4 |
| Tailles | 8 | 94 | `11px` ×20 · `12.5px` ×19 · `10.5px` ×16 · `10px` ×13 · `12px` ×13 · `11.5px` ×8 · `13px` ×3 · `13.5px` ×2 |
| Graisses | 6 | 12 | `600` ×6 · `400 700` ×2 · `400 600` ×1 · `400 500` ×1 · `500` ×1 · `400` ×1 |
| Rayons | 14 | 56 | `8px` ×18 · `var(--r)` ×13 · `var(--r-lg)` ×5 · `var(--r-sm)` ×4 · `99px` ×4 · `999px` ×2 · `9px` ×2 · `4px` ×2 · `6px` ×1 · `3px` ×1 · `50%` ×1 · `10px` ×1 |
| Marges internes (padding) | 41 | 76 | `9px 14px` ×5 · `14px` ×5 · `6px 9px` ×4 · `8px 10px` ×4 · `8px` ×4 · `3px 9px` ×3 · `10px` ×3 · `2px 7px` ×3 · `14px 16px` ×3 · `3px 8px` ×2 · `7px 11px` ×2 · `7px 10px` ×2 |
| Écarts (gap) | 10 | 69 | `8px` ×16 · `6px` ×14 · `12px` ×9 · `7px` ×6 · `10px` ×6 · `14px` ×5 · `9px` ×5 · `4px` ×4 · `5px` ×3 · `2px` ×1 |

#### avatar (6 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 10 | 36 | `var(--ink-soft)` ×15 · `var(--ink-strong)` ×8 · `var(--ink)` ×3 · `var(--red)` ×3 · `var(--accent-ink)` ×2 · `inherit` ×1 · `var(--accent)` ×1 · `var(--ink-muted)` ×1 · `var(--green)` ×1 · `#fff` ×1 |
| Tailles | 3 | 15 | `12.5px` ×7 · `13px` ×4 · `12px` ×4 |
| Graisses | 1 | 2 | `600` ×2 |
| Rayons | 7 | 18 | `var(--r)` ×7 · `var(--r-sm)` ×6 · `var(--r-lg)` ×1 · `999px` ×1 · `2px` ×1 · `4px` ×1 · `10px` ×1 |
| Marges internes (padding) | 12 | 17 | `12px` ×4 · `var(--gap-lg)` ×2 · `10px` ×2 · `6px var(--gap-lg)` ×1 · `6px 12px` ×1 · `7px 9px` ×1 · `8px 14px` ×1 · `4px 8px` ×1 · `8px 10px` ×1 · `3px 10px` ×1 · `2px` ×1 · `2px 8px` ×1 |
| Écarts (gap) | 11 | 25 | `8px` ×6 · `6px` ×5 · `4px` ×3 · `var(--gap)` ×3 · `12px` ×2 · `6px var(--gap-lg)` ×1 · `var(--gap-lg)` ×1 · `10px` ×1 · `2px` ×1 · `16px` ×1 · `14px` ×1 |

#### cardforge (24 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 23 | 656 | `var(--ink-muted)` ×175 · `var(--ink-strong)` ×157 · `var(--ink-soft)` ×110 · `var(--red)` ×66 · `var(--green)` ×41 · `var(--accent)` ×34 · `var(--ink)` ×24 · `var(--amber)` ×18 · `var(--amber, var(--accent))` ×6 · `var(--accent-ink)` ×5 · `var(--sel-ink)` ×4 · `var(--cat)` ×4 |
| Polices | 4 | 101 | `var(--f-mono)` ×79 · `var(--f-ui)` ×11 · `inherit` ×9 · `\` ×2 |
| Tailles | 20 | 417 | `10.5px` ×90 · `11px` ×72 · `10px` ×62 · `9.5px` ×49 · `11.5px` ×40 · `12px` ×32 · `9px` ×22 · `12.5px` ×18 · `13px` ×9 · `8.5px` ×5 · `14px` ×2 · `13.5px` ×2 |
| Graisses | 4 | 62 | `600` ×46 · `500` ×8 · `400` ×5 · `700` ×3 |
| Rayons | 17 | 184 | `var(--r)` ×41 · `8px` ×34 · `99px` ×29 · `7px` ×13 · `4px` ×12 · `5px` ×12 · `6px` ×11 · `10px` ×8 · `2px` ×6 · `50%` ×4 · `var(--r-sm)` ×4 · `3px` ×3 |
| Marges internes (padding) | 119 | 268 | `2px 9px` ×12 · `8px` ×12 · `10px` ×8 · `5px 9px` ×7 · `6px` ×7 · `2px` ×7 · `7px 10px` ×6 · `6px 9px` ×6 · `0 4px` ×6 · `7px 9px` ×5 · `6px 10px` ×5 · `4px 7px` ×5 |
| Écarts (gap) | 29 | 304 | `6px` ×52 · `10px` ×38 · `7px` ×36 · `8px` ×34 · `5px` ×28 · `4px` ×26 · `3px` ×22 · `12px` ×16 · `9px` ×13 · `2px` ×7 · `1px` ×7 · `14px` ×4 |

#### etabli (7 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 10 | 137 | `var(--ink-soft)` ×51 · `var(--ink-strong)` ×42 · `var(--ink)` ×17 · `var(--ink-muted)` ×8 · `var(--red)` ×7 · `var(--accent)` ×4 · `var(--amber)` ×4 · `var(--green)` ×2 · `couleur, depthTest: false, depthWrite: false` ×1 · `0x4da3ff, transparent: true` ×1 |
| Polices | 4 | 13 | `var(--f-mono)` ×10 · `inherit` ×1 · `var(--f-display)` ×1 · `var(--f-mono), ui-monospace, monospace` ×1 |
| Tailles | 7 | 52 | `11px` ×25 · `10.5px` ×14 · `10px` ×6 · `9.5px` ×3 · `11.5px` ×2 · `12px` ×1 · `14px` ×1 |
| Graisses | 3 | 17 | `600` ×9 · `500` ×7 · `400` ×1 |
| Rayons | 4 | 34 | `var(--r-sm)` ×31 · `var(--r)` ×1 · `999px` ×1 · `3px` ×1 |
| Marges internes (padding) | 31 | 51 | `12px` ×4 · `6px 8px` ×3 · `4px 6px` ×3 · `3px 5px` ×3 · `0 6px` ×3 · `4px 2px` ×2 · `3px 8px` ×2 · `4px 8px` ×2 · `6px 14px` ×2 · `5px 4px` ×2 · `10px` ×2 · `2px 5px` ×2 |
| Écarts (gap) | 9 | 62 | `6px` ×23 · `4px` ×14 · `2px` ×10 · `8px` ×7 · `10px` ×3 · `5px` ×2 · `16px` ×1 · `7px` ×1 · `3px` ×1 |

#### lib3d (6 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 6 | 6 | `0x0e1116, transparent: true` ×1 · `0xf0c060, transparent: true` ×1 · `0xe08a2e, transparent: true, opacity: 0.75, side` ×1 · `COULEUR_REGLE, transparent: true, opacity: 0.85` ×1 · `0x4d7fd0, transparent: true, opacity: 0.9, depth` ×1 · `couleur, depthWrite: false, depthTest: false` ×1 |

#### materialforge (2 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 16 | 185 | `var(--ink-muted)` ×42 · `var(--ink-strong)` ×42 · `var(--ink-soft)` ×42 · `var(--ink)` ×20 · `var(--accent)` ×11 · `var(--red)` ×9 · `var(--green)` ×4 · `var(--sel-ink)` ×3 · `var(--bg-base)` ×3 · `var(--sm-c)` ×2 · `var(--stroke-strong)` ×2 · `color-mix(in srgb, var(--sel-ink) 72%, transpare` ×1 |
| Polices | 3 | 42 | `var(--f-mono)` ×29 · `var(--f-ui)` ×11 · `inherit` ×2 |
| Tailles | 16 | 120 | `10px` ×18 · `11px` ×17 · `10.5px` ×16 · `11.5px` ×12 · `9.5px` ×11 · `12px` ×10 · `8.5px` ×10 · `9px` ×9 · `12.5px` ×7 · `13.5px` ×2 · `8px` ×2 · `13px` ×2 |
| Graisses | 3 | 21 | `600` ×9 · `500` ×7 · `400` ×5 |
| Rayons | 13 | 54 | `99px` ×15 · `8px` ×10 · `var(--r)` ×6 · `6px` ×6 · `50%` ×6 · `5px` ×3 · `7px` ×2 · `0 6px 6px 0` ×1 · `2px` ×1 · `4px` ×1 · `3px` ×1 · `12px` ×1 |
| Marges internes (padding) | 64 | 85 | `4px 8px` ×4 · `10px` ×3 · `5px 7px` ×3 · `7px` ×3 · `5px 8px` ×3 · `3px 8px` ×2 · `2px 8px` ×2 · `8px` ×2 · `3px 7px` ×2 · `2px 0` ×2 · `14px` ×2 · `3px 6px` ×2 |
| Écarts (gap) | 13 | 58 | `6px` ×10 · `8px` ×9 · `10px` ×8 · `5px` ×8 · `7px` ×6 · `3px` ×4 · `4px` ×4 · `1px` ×3 · `9px` ×2 · `12px` ×1 · `14px` ×1 · `3px 8px` ×1 |

#### meshy (1 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|

#### photolab (56 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 28 | 280 | `var(--ink-strong)` ×73 · `var(--ink-soft)` ×64 · `var(--ink-muted)` ×54 · `var(--ink)` ×28 · `var(--accent)` ×23 · `fg` ×5 · `var(--red)` ×4 · `coul.value` ×3 · `fg()` ×3 · `var(--accent-ink)` ×3 · `sCou.value` ×2 · `inherit` ×2 |
| Polices | 2 | 7 | `var(--f-mono)` ×4 · `var(--f-ui)` ×3 |
| Tailles | 8 | 46 | `11px` ×27 · `13px` ×7 · `12px` ×4 · `10px` ×4 · `28px` ×1 · `8px` ×1 · `16px` ×1 · `14px` ×1 |
| Graisses | 3 | 16 | `600` ×14 · `700` ×1 · `400` ×1 |
| Rayons | 11 | 98 | `3px` ×59 · `4px` ×16 · `2px` ×8 · `50%` ×5 · `6px` ×4 · `4px 4px 0 0` ×1 · `0 0 4px 4px` ×1 · `14px` ×1 · `1px` ×1 · `2px 0 0 0` ×1 · `11px` ×1 |
| Marges internes (padding) | 49 | 109 | `0 6px` ×15 · `0 4px` ×9 · `0 8px` ×8 · `6px` ×6 · `0 10px` ×5 · `2px` ×5 · `0 12px` ×4 · `4px 0` ×4 · `8px` ×4 · `10px` ×3 · `6px 8px` ×3 · `4px` ×3 |
| Écarts (gap) | 16 | 134 | `6px` ×30 · `4px` ×25 · `8px` ×21 · `2px` ×17 · `10px` ×17 · `12px` ×6 · `1px` ×5 · `3px` ×4 · `18px` ×2 · `28px` ×1 · `16px` ×1 · `4px 10px` ×1 |

#### plateau (3 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 8 | 36 | `var(--ink-soft)` ×12 · `var(--ink)` ×6 · `var(--accent)` ×6 · `var(--ink-strong)` ×5 · `var(--amber)` ×3 · `var(--red)` ×2 · `COUL_FAISCEAU, emissive: COUL_FAISCEAU, emissive` ×1 · `coul, roughness: 0.8, metalness: 0` ×1 |
| Polices | 3 | 17 | `var(--f-mono)` ×15 · `inherit` ×1 · `var(--f-display)` ×1 |
| Tailles | 7 | 28 | `11px` ×11 · `10px` ×7 · `12px` ×3 · `10.5px` ×3 · `11.5px` ×2 · `9.5px` ×1 · `14px` ×1 |
| Graisses | 1 | 3 | `600` ×3 |
| Rayons | 3 | 11 | `var(--r-sm)` ×8 · `2px` ×2 · `999px` ×1 |
| Marges internes (padding) | 14 | 14 | `12px` ×1 · `0 7px` ×1 · `0 9px` ×1 · `5px 7px` ×1 · `8px` ×1 · `0 14px` ×1 · `6px 10px` ×1 · `3px 8px` ×1 · `6px 14px` ×1 · `8px 14px 10px` ×1 · `6px` ×1 · `18px` ×1 |
| Écarts (gap) | 8 | 18 | `3px` ×5 · `6px` ×4 · `5px` ×3 · `4px` ×2 · `8px` ×1 · `10px` ×1 · `16px` ×1 · `4px 10px` ×1 |

#### spritelab (8 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 12 | 88 | `var(--ink-strong)` ×21 · `var(--ink-soft)` ×15 · `var(--ink)` ×11 · `var(--cyan)` ×10 · `var(--ink-muted)` ×10 · `var(--red)` ×6 · `var(--amber)` ×6 · `var(--ink3, #8a857d)` ×3 · `var(--green)` ×3 · `inherit` ×1 · `var(--ink, #f2efe9)` ×1 · `$(` ×1 |
| Polices | 2 | 12 | `var(--f-mono)` ×10 · `var(--f-ui)` ×2 |
| Polices (Tailwind) | 1 | 3 | `font-display` ×3 |
| Tailles | 9 | 54 | `12px` ×15 · `12.5px` ×11 · `11.5px` ×9 · `11px` ×7 · `10.5px` ×3 · `10px` ×3 · `13px` ×3 · `14px` ×2 · `13.5px` ×1 |
| Graisses | 5 | 5 | `400 600` ×1 · `400 700` ×1 · `400 500` ×1 · `700` ×1 · `500` ×1 |
| Rayons | 8 | 36 | `8px` ×17 · `var(--r)` ×5 · `6px` ×5 · `99px` ×3 · `9px` ×2 · `50%` ×2 · `10px` ×1 · `4px` ×1 |
| Marges internes (padding) | 40 | 59 | `10px` ×4 · `6px 9px` ×3 · `8px 0` ×3 · `8px 10px` ×3 · `10px 12px` ×3 · `8px 10px 10px` ×3 · `0 6px` ×3 · `6px 10px` ×2 · `9px 16px` ×2 · `0 10px 10px` ×2 · `2px 4px` ×2 · `10px 16px` ×1 |
| Écarts (gap) | 12 | 54 | `6px` ×14 · `8px` ×12 · `4px` ×7 · `10px` ×6 · `12px` ×4 · `5px` ×3 · `2px` ×2 · `3px` ×2 · `14px` ×1 · `9px` ×1 · `1px` ×1 · `7px` ×1 |

#### studio3d (13 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 13 | 131 | `var(--ink-soft)` ×50 · `var(--ink-strong)` ×28 · `var(--ink)` ×24 · `var(--accent)` ×11 · `var(--accent-ink)` ×4 · `var(--ink-muted)` ×4 · `var(--amber)` ×2 · `var(--green)` ×2 · `$` ×2 · `var(--red)` ×1 · `0xb9b2a6, roughness: 0.9, metalness: 0` ×1 · `0x9fc3e8, wireframe: true` ×1 |
| Polices | 4 | 51 | `var(--f-mono)` ×43 · `var(--f-display)` ×4 · `inherit` ×3 · `var(--f-ui)` ×1 |
| Tailles | 12 | 88 | `10px` ×23 · `12px` ×16 · `12.5px` ×13 · `10.5px` ×13 · `11px` ×7 · `11.5px` ×4 · `13px` ×4 · `14px` ×4 · `17px` ×1 · `7px` ×1 · `9px` ×1 · `9.5px` ×1 |
| Graisses | 3 | 16 | `600` ×10 · `400` ×3 · `500` ×3 |
| Rayons | 8 | 49 | `var(--r-sm)` ×11 · `8px` ×11 · `999px` ×10 · `6px` ×9 · `9px` ×4 · `10px` ×2 · `12px` ×1 · `5px` ×1 |
| Marges internes (padding) | 34 | 54 | `7px 8px` ×5 · `8px 10px` ×5 · `4px 8px` ×5 · `6px 10px` ×3 · `14px` ×3 · `12px` ×2 · `10px 12px` ×2 · `5px 9px` ×2 · `8px` ×2 · `10px 16px` ×1 · `14px 16px` ×1 · `40px 24px` ×1 |
| Écarts (gap) | 13 | 55 | `6px` ×10 · `10px` ×10 · `8px` ×9 · `5px` ×8 · `4px` ×7 · `12px` ×3 · `14px` ×2 · `2px 8px` ×1 · `18px` ×1 · `7px` ×1 · `9px` ×1 · `4px 10px` ×1 |

#### tilelab (7 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 7 | 19 | `var(--ink-soft)` ×8 · `var(--ink-strong)` ×4 · `var(--red)` ×2 · `var(--ink-muted)` ×2 · `var(--cyan)` ×1 · `#ddd` ×1 · `var(--ink)` ×1 |
| Polices | 1 | 1 | `var(--f-mono)` ×1 |
| Tailles | 6 | 13 | `11.5px` ×5 · `11px` ×4 · `12px` ×1 · `9px` ×1 · `10.5px` ×1 · `12.5px` ×1 |
| Rayons | 5 | 20 | `6px` ×9 · `8px` ×7 · `4px` ×2 · `7px` ×1 · `3px` ×1 |
| Marges internes (padding) | 15 | 17 | `6px` ×3 · `4px 2px` ×1 · `5px 10px` ×1 · `8px 12px` ×1 · `10px 10px 0` ×1 · `8px 10px 0` ×1 · `5px 6px` ×1 · `8px 10px` ×1 · `0 4px` ×1 · `2px 6px` ×1 · `4px 8px` ×1 · `3px 6px` ×1 |
| Écarts (gap) | 5 | 24 | `6px` ×8 · `8px` ×7 · `4px` ×5 · `12px` ×2 · `10px` ×2 |

#### vectorlab (82 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 28 | 183 | `var(--aff-muet)` ×73 · `var(--aff-texte)` ×61 · `#fff` ×10 · `var(--pan-texte)` ×5 · `#e08a8a` ×4 · `var(--ink-soft)` ×4 · `#e0b34a` ×2 · `var(--pan-muet)` ×2 · `#c8c8c8` ×2 · `var(--ink)` ×2 · `T(` ×1 · `Color` ×1 |
| Polices | 3 | 4 | `&quot` ×2 · `Consolas, monospace` ×1 · `var(--f-ui)` ×1 |
| Polices (Tailwind) | 1 | 1 | `font-display` ×1 |
| Tailles | 15 | 126 | `12px` ×51 · `11px` ×36 · `13px` ×10 · `15px` ×6 · `11.5px` ×5 · `10px` ×4 · `10.5px` ×4 · `9.5px` ×2 · `0` ×2 · `$` ×1 · `14px` ×1 · `16px` ×1 |
| Graisses | 6 | 21 | `600` ×10 · `700` ×6 · `800` ×2 · `$` ×1 · `500` ×1 · `400` ×1 |
| Rayons | 14 | 123 | `0` ×29 · `4px` ×25 · `3px` ×24 · `6px` ×19 · `50%` ×7 · `5px` ×5 · `8px` ×4 · `2px` ×4 · `18px` ×1 · `13px` ×1 · `1px` ×1 · `4px 4px 0 0` ×1 |
| Marges internes (padding) | 70 | 153 | `4px` ×8 · `0 4px` ×7 · `0 8px` ×7 · `6px 10px` ×6 · `0 6px` ×6 · `0 10px` ×6 · `2px 4px` ×5 · `8px` ×5 · `3px 6px` ×5 · `2px 0` ×5 · `12px` ×5 · `6px 8px` ×4 |
| Écarts (gap) | 16 | 115 | `6px` ×34 · `8px` ×18 · `4px` ×15 · `3px` ×11 · `5px` ×10 · `var(--pan-gap)` ×6 · `10px` ×5 · `2px` ×5 · `14px` ×3 · `12px` ×2 · `7px` ×1 · `6px 8px` ×1 |

#### whatsapp (4 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 7 | 42 | `var(--ink-strong)` ×13 · `var(--ink-soft)` ×12 · `var(--ink)` ×5 · `var(--accent)` ×4 · `var(--red)` ×4 · `var(--green)` ×3 · `var(--c-av)` ×1 |
| Polices | 4 | 11 | `var(--f-mono)` ×6 · `var(--f-display)` ×3 · `var(--f-ui)` ×1 · `inherit` ×1 |
| Tailles | 7 | 24 | `12px` ×7 · `11px` ×5 · `10px` ×5 · `13px` ×3 · `15px` ×2 · `17px` ×1 · `18px` ×1 |
| Graisses | 1 | 1 | `600` ×1 |
| Rayons | 4 | 16 | `var(--r-sm)` ×8 · `var(--r)` ×4 · `99px` ×2 · `3px` ×2 |
| Marges internes (padding) | 17 | 22 | `7px 10px` ×3 · `8px` ×2 · `8px 10px` ×2 · `10px` ×2 · `10px 16px` ×1 · `0 8px` ×1 · `4px` ×1 · `6px 8px` ×1 · `0 10px` ×1 · `0 16px` ×1 · `24px` ×1 · `8px 16px 0` ×1 |
| Écarts (gap) | 8 | 32 | `6px` ×12 · `8px` ×8 · `4px` ×5 · `10px` ×2 · `3px` ×2 · `14px` ×1 · `2px` ×1 · `12px` ×1 |

#### shared (46 fichiers)

| Propriété | distinctes | occurrences | valeurs les plus fréquentes |
|---|---:|---:|---|
| Couleurs de texte (CSS) | 51 | 323 | `var(--txt-hi,var(--ink-strong,#e6e9ee))` ×66 · `var(--txt-mid,var(--ink-muted,#9aa4ae))` ×58 · `var(--txt-base,var(--ink,#cfd6e2))` ×21 · `inherit` ×20 · `var(--red,#e5484d)` ×18 · `var(--ink-soft,#8a857d)` ×14 · `var(--accent-ink,#ffffff)` ×11 · `var(--amber,#f0b429)` ×11 · `var(--green,#3fb950)` ×7 · `var(--ink-strong,#f2efe9)` ×7 · `#e6e9ee` ×7 · `#fff` ×6 |
| Polices | 6 | 22 | `var(--f-mono,monospace)` ×7 · `inherit` ×4 · `var(--f-ui,system-ui,sans-serif)` ×4 · `var(--f-mono)` ×3 · `var(--f-mono` ×3 · `var(--f-ui)` ×1 |
| Polices (Tailwind) | 1 | 4 | `font-display` ×4 |
| Tailles | 9 | 160 | `12px` ×60 · `11.5px` ×35 · `11px` ×33 · `12.5px` ×15 · `13px` ×10 · `14px` ×3 · `10px` ×2 · `13.5px` ×1 · `10.5px` ×1 |
| Graisses | 6 | 21 | `600` ×15 · `400 700` ×2 · `400 600` ×1 · `400 500` ×1 · `500` ×1 · `700` ×1 |
| Rayons | 13 | 101 | `0` ×70 · `6px` ×7 · `8px` ×5 · `999px` ×4 · `50%` ×3 · `10px` ×3 · `var(--r,10px)` ×2 · `var(--r-sm,6px)` ×2 · `var(--r-sm)` ×1 · `var(--radius)` ×1 · `99px` ×1 · `8px 8px 0 0` ×1 |
| Marges internes (padding) | 54 | 212 | `10px 14px` ×18 · `9px 14px` ×17 · `12px 14px` ×17 · `0 12px` ×16 · `8px` ×13 · `5px 12px` ×11 · `6px 8px` ×11 · `3px 6px` ×9 · `8px 10px` ×8 · `10px 12px` ×6 · `4px 6px` ×6 · `0 14px 8px` ×6 |
| Écarts (gap) | 15 | 174 | `8px` ×52 · `6px` ×46 · `4px` ×22 · `10px` ×14 · `3px` ×9 · `12px` ×7 · `5px` ×6 · `2px` ×6 · `14px` ×4 · `7px` ×2 · `4px 8px` ×2 · `4px 16px` ×1 |
