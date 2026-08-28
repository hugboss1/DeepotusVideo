# Deepotus — Design spec : iconographie, couleurs par catégorie, zones escamotables

> **Comment intégrer ce fichier.** Ce document est écrit pour être collé dans
> `C:\Users\olivi\DeepotusVideo\design.md`. Les cinq sections numérotées ci-dessous sont
> autonomes : si `design.md` contient déjà une section icônes, couleurs ou panneaux
> repliables, **celles-ci les remplacent**. Rien d'autre dans le fichier existant n'est
> concerné.
>
> **Nature du livrable.** La maquette de référence est `Icônes Deepotus.dc.html` (livrée
> à côté de ce fichier). C'est un **prototype HTML de référence**, pas du code à copier :
> il montre l'apparence et le comportement attendus. Le travail consiste à **recréer ces
> designs dans l'environnement existant de la codebase** (React / Vite / Tailwind ou ce
> qui est en place), avec ses conventions, ses composants et sa librairie de styles.
>
> **Fidélité : haute (hifi).** Couleurs, tailles, durées et courbes d'animation sont
> définitives. Le tracé SVG de chaque icône est donné intégralement et doit être repris
> tel quel. Les libellés sont ceux de l'application et ne doivent pas être réécrits.

---

## 0. Périmètre de la mise à jour

Trois chantiers, dans cet ordre de dépendance :

| # | Chantier | Portée |
|---|---|---|
| 1 | **Jeu d'icônes « glyphe bicolore » (variante 1b)** | 27 icônes : 11 du bandeau de navigation, 10 du bandeau Card Forge, 6 de la barre horizontale |
| 2 | **Barre horizontale colorée à bords droits (variante 2a)** + **propagation de la teinte** | La barre `Game Assets` et **toute l'UI de la section pilotée** par l'onglet actif |
| 3 | **Chevrons de repli / expansion unifiés** | Tous les panneaux escamotables de l'application, sans exception |

---

## 1. Design tokens

### 1.1 Surfaces et texte (inchangés, rappelés pour référence)

```css
--srf-app:        #0a0c0f;  /* fond application */
--srf-panel:      #13171c;  /* bandeaux, panneaux latéraux */
--srf-raised:     #171c22;  /* onglet inactif, champ */
--srf-hover:      #181d23;  /* survol de ligne */
--srf-active:     #191f26;  /* ligne sélectionnée */
--brd-hard:       #20262d;  /* bordure de panneau */
--brd-soft:       #1c2229;  /* filet interne, séparateur */

--txt-hi:         #eef2f6;  /* libellé sélectionné */
--txt-base:       #cfd6dd;  /* libellé de navigation */
--txt-mid:        #8b959f;  /* icône au repos, libellé secondaire */
--txt-low:        #5f6873;  /* sous-titre mono, numéro d'étape */
--txt-faint:      #4d5661;  /* légende, zone vide */
```

Typographie : libellés en sans-serif système (`Helvetica Neue, Helvetica, sans-serif`),
12,5 px / 500 pour les entrées de navigation, 12 px / 400 pour les étapes Card Forge.
Toutes les métadonnées techniques (numéros d'étape, sous-titres, en-têtes de bandeau,
valeurs de mesure) en **IBM Plex Mono** 9,5 px, `letter-spacing: .12em` pour les en-têtes
en capitales.

### 1.2 Palette de catégories — la clé de voûte

Six teintes, **toutes à clarté et chroma identiques** en OKLCH. C'est ce qui empêche une
catégorie de dominer visuellement les autres : seule la teinte varie.

```css
--cat-3d:        oklch(.72 .13 255);  /* bleu     — 3D */
--cat-3dstudio:  oklch(.72 .13 300);  /* violet   — 3D Studio */
--cat-sprites:   oklch(.72 .13 200);  /* cyan     — Sprites 2D */
--cat-tuiles:    oklch(.72 .13 145);  /* vert     — Tuiles */
--cat-matieres:  oklch(.72 .13  80);  /* ambre    — Matières */
--cat-cartes:    oklch(.72 .13  25);  /* rouge    — Cartes */
```

Dérivés, à générer **par calcul depuis la teinte active**, jamais en dur :

```css
--cat:        <teinte de la catégorie active>;   /* posée par le conteneur de section */
--cat-fill:   oklch(from var(--cat) l c h / .14);  /* fond de ligne active, pastille */
--cat-line:   oklch(from var(--cat) l c h / .55);  /* bordure d'élément actif */
--cat-ink:    #14181d;                             /* texte sur aplat de teinte */
```

Si `oklch(from …)` n'est pas disponible dans la cible de build, exposer trois variables
par catégorie (`--cat-3d`, `--cat-3d-fill`, `--cat-3d-line`) générées à la compilation.
Ne pas repasser par du hexadécimal saisi à la main : la cohérence de clarté serait perdue.

L'or historique `#e6b23c` **reste** la couleur de marque, mais son emploi est désormais
restreint à ce qui n'appartient à aucune catégorie : barre supérieure, compteur de crédits,
puce d'enregistrement, badges de version, rail de navigation global.

### 1.3 Mouvement

```css
--ease-panel:  cubic-bezier(.22, 1, .36, 1);   /* repli, glissement, remplissage */
--ease-pop:    cubic-bezier(.34, 1.56, .64, 1); /* enfoncement de bouton, rebond */

--dur-panel:   460ms;  /* largeur/hauteur de zone escamotable, rotation du chevron */
--dur-fill:    440ms;  /* balayage du remplissage d'onglet */
--dur-label:   200ms;  /* disparition des libellés au repli */
--dur-press:   170ms;  /* durée de l'état enfoncé */
```

Respecter `prefers-reduced-motion: reduce` : conserver les changements d'état, ramener
toutes les durées à `1ms` et supprimer les cascades décalées.

---

## 2. Système d'icônes — glyphe bicolore (variante 1b)

### 2.1 Règles de dessin

- Grille **24 × 24**, rendu à **18 px** dans les bandeaux, **16 px** dans le rail Card
  Forge, **17 px** dans la barre horizontale.
- **Masses pleines** (`fill="currentColor"`), aucun contour, sauf l'icône News dont
  l'objet même est un trait (`stroke-width: 2.6`).
- **Deux niveaux d'opacité** : le sujet à `1`, le support/contenant entre `.26` et `.45`.
  C'est ce contraste interne qui rend le glyphe lisible à 16 px sur fond sombre, là où un
  filaire se referme.
- Une découpe interne se fait par `fill-rule="evenodd"` dans le même `path`, **jamais**
  par un tracé peint en couleur de fond : le glyphe doit rester valide sur un aplat coloré.
- Couleur pilotée exclusivement par `currentColor` : au repos `--txt-mid`, actif
  `var(--cat)`, sur aplat `--cat-ink`.

### 2.2 Bandeau de navigation — 11 icônes

Chaque entrée : `viewBox="0 0 24 24" fill="currentColor"`, rendu 18 px.

| Entrée | Sens retenu | Tracé |
|---|---|---|
| **Quick** | éclair — générateur 1-shot | `<path d="M13.8 2.6 6 14.2h4.6L9.6 21.4 18 9.6h-4.8z"/>` |
| **Studio** | graphe de nœuds | `<path d="M8.4 11.2h3.2V6.4h4v1.6h-2.4V12H8.4zM11.6 12.8h3.2v3.6h2.4V18h-4v-3.6h-1.6z" opacity=".45"/><rect x="2.8" y="9.2" width="5.6" height="5.6" rx="1.4"/><rect x="15.6" y="4" width="5.6" height="5.6" rx="1.4"/><rect x="15.6" y="14.4" width="5.6" height="5.6" rx="1.4"/>` |
| **Chapitres** | livre ouvert + lecture | `<path d="M3.8 4h6.6a1.6 1.6 0 0 1 1.6 1.6V20a2.4 2.4 0 0 0-1.7-.7H3.8z" opacity=".38"/><path fill-rule="evenodd" d="M20.2 4h-6.6A1.6 1.6 0 0 0 12 5.6V20a2.4 2.4 0 0 1 1.7-.7h6.5zM14.6 9.4 18 11.4l-3.4 2z"/>` |
| **Son & VFX** | forme d'onde | `<rect x="3" y="10.4" width="2.2" height="3.2" rx="1.1" opacity=".45"/><rect x="7.2" y="7" width="2.2" height="10" rx="1.1"/><rect x="11.4" y="4.2" width="2.2" height="15.6" rx="1.1"/><rect x="15.6" y="8" width="2.2" height="8" rx="1.1"/><rect x="19.8" y="10.4" width="2.2" height="3.2" rx="1.1" opacity=".45"/>` |
| **Montage** | pistes + tête de lecture | `<rect x="3" y="5.6" width="10.4" height="2.6" rx="1.3" opacity=".45"/><rect x="3" y="10.7" width="14.6" height="2.6" rx="1.3" opacity=".45"/><rect x="3" y="15.8" width="7.6" height="2.6" rx="1.3" opacity=".45"/><rect x="18.6" y="3.4" width="2" height="17.2" rx="1"/>` |
| **Scheduler** | calendrier + horloge | `<rect x="3.2" y="5.4" width="17.6" height="14.8" rx="2" opacity=".3"/><path d="M3.2 7.4a2 2 0 0 1 2-2h13.6a2 2 0 0 1 2 2V10H3.2z"/><path d="M12.9 12.6h-1.8v3.5l2.7 1.6.9-1.5-1.8-1z"/>` |
| **Templates** | blocs de mise en page | `<rect x="3.2" y="4.2" width="8.2" height="15.6" rx="1.6"/><rect x="13.2" y="4.2" width="7.6" height="6.8" rx="1.6" opacity=".38"/><rect x="13.2" y="13" width="7.6" height="6.8" rx="1.6" opacity=".38"/>` |
| **News** | ondes RSS *(tracé, pas masse)* | `fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"` puis `<path d="M5 11.4a8.2 8.2 0 0 1 8.2 8.2" opacity=".4"/><path d="M5 5.4a14.2 14.2 0 0 1 14.2 14.2"/><circle cx="5.6" cy="18.6" r="1.4" fill="currentColor" stroke="none"/>` |
| **Library** | couches empilées | `<path d="M12 2.8 21 7.2 12 11.6 3 7.2z"/><path d="M12 13.6 4.6 10l-1.6.8L12 15.2l9-4.4-1.6-.8zM12 18.2 4.6 14.6l-1.6.8L12 19.8l9-4.4-1.6-.8z" opacity=".42"/>` |
| **Game Assets** | grille + volume | `<rect x="3.4" y="3.4" width="7.4" height="7.4" rx="1.4" opacity=".42"/><rect x="13.2" y="3.4" width="7.4" height="7.4" rx="1.4" opacity=".42"/><rect x="3.4" y="13.2" width="7.4" height="7.4" rx="1.4" opacity=".42"/><path d="M16.9 12.6 20.6 14.8v4.4l-3.7 2.2-3.7-2.2v-4.4z"/>` |
| **Settings** | curseurs de réglage | `<rect x="3" y="7" width="18" height="2.2" rx="1.1" opacity=".42"/><rect x="3" y="14.8" width="18" height="2.2" rx="1.1" opacity=".42"/><circle cx="15.2" cy="8.1" r="2.8"/><circle cx="8.8" cy="15.9" r="2.8"/>` |

### 2.3 Bandeau Card Forge — 10 icônes

Rendu 16 px, alignées **à droite** de la ligne (le numéro d'étape occupe la gouttière
gauche).

| Étape | Sens retenu | Tracé |
|---|---|---|
| **01 Face** | recto : fenêtre d'illustration | `<rect x="5" y="3" width="14" height="18" rx="2.2" opacity=".3"/><rect x="7.4" y="5.4" width="9.2" height="8" rx="1.2"/>` |
| **02 Cadre** | double filet, centre évidé | `<path fill-rule="evenodd" d="M3.4 4.4h17.2v15.2H3.4zm2.8 2.8v9.6h11.6V7.2z"/><rect x="7.4" y="8.4" width="9.2" height="7.2" opacity=".3"/>` |
| **03 Typo** | lettre + ligne de base | `<path d="M12 3.6 19.6 18h-3.9L12 10.4 8.3 18H4.4z"/><rect x="8.4" y="13.4" width="7.2" height="2.4"/><rect x="4.4" y="19.8" width="15.2" height="1.8" rx=".9" opacity=".35"/>` |
| **04 Données** | tableau de champs | `<rect x="3.4" y="5" width="17.2" height="14" rx="2" opacity=".28"/><path d="M3.4 7a2 2 0 0 1 2-2h13.2a2 2 0 0 1 2 2v2.4H3.4z"/><rect x="6" y="11.8" width="5" height="1.9" rx=".9"/><rect x="13" y="11.8" width="5" height="1.9" rx=".9"/><rect x="6" y="15.3" width="5" height="1.9" rx=".9"/><rect x="13" y="15.3" width="5" height="1.9" rx=".9"/>` |
| **05 Volume** | plaques décalées = épaisseur | `<rect x="7.4" y="3.4" width="12.2" height="14.6" rx="2" opacity=".32"/><rect x="4.4" y="6.4" width="12.2" height="14.6" rx="2"/>` |
| **06 Matières** | sphère d'échantillon | `<circle cx="12" cy="12" r="8.6" opacity=".3"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/>` |
| **07 Impression** | presse + feuille sortante | `<rect x="3.4" y="8" width="17.2" height="8" rx="1.8" opacity=".32"/><path d="M7 3.4h10V8H7z"/><rect x="7" y="13.6" width="10" height="7" rx="1.2"/>` |
| **08 Export 3D** | flèche sortante du bac | `<path d="M3.6 13.4h2.8v4.4h11.2v-4.4h2.8v6.2a1.8 1.8 0 0 1-1.8 1.8H5.4a1.8 1.8 0 0 1-1.8-1.8z" opacity=".32"/><path d="M12 2.6 17.2 8h-3.6v7.6h-3.2V8H6.8z"/>` |
| **09 Forge 3D** | cube + étincelle = génération | `<path d="M10.4 5.2 17.2 9v7.4l-6.8 3.8-6.8-3.8V9z" opacity=".32"/><path d="M10.4 5.2 17.2 9l-6.8 3.9L3.6 9z"/><path d="M19.6 2.2l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9z"/>` |
| **10 Import** | flèche entrante dans le bac | `<path d="M3.6 13.4h2.8v4.4h11.2v-4.4h2.8v6.2a1.8 1.8 0 0 1-1.8 1.8H5.4a1.8 1.8 0 0 1-1.8-1.8z" opacity=".32"/><path d="M12 15.8 6.8 10.4h3.6V2.8h3.2v7.6h3.6z"/>` |

**Deux définitions à confirmer avant implémentation** — signalées ici parce qu'elles
changent le dessin :

- **05 Volume** est lu comme *épaisseur / relief physique de la carte* → plaques décalées.
  S'il s'agit du **tirage** (nombre d'exemplaires), l'icône doit devenir une pile de cartes.
- **09 Forge 3D** est lu comme *génération d'un volume* → cube + étincelle. Si l'étape est
  un simple réglage de relief, l'étincelle est à retirer.

### 2.4 Barre horizontale — 6 icônes, **bords droits**

Rendu 17 px. Ces six-là sont dessinées **sans aucun rayon** (`rx` supprimé partout),
en cohérence avec la barre à angles vifs de la section 3. Ne pas réutiliser les variantes
arrondies.

| Onglet | Sens retenu | Tracé |
|---|---|---|
| **3D** | cube isométrique = le modèle | `<path d="M12 2.8 20.6 7.4v9.2L12 21.2 3.4 16.6V7.4z" opacity=".34"/><path d="M12 2.8 20.6 7.4 12 11.9 3.4 7.4z"/>` |
| **3D Studio** | viewport + cube = la scène | `<rect x="2.6" y="4" width="18.8" height="16" opacity=".3"/><path d="M12 7.4 16.2 9.8v4.8L12 17l-4.2-2.4V9.8z"/>` |
| **Sprites 2D** | planche de sprites | `<rect x="3" y="5" width="18" height="14" opacity=".3"/><rect x="5.4" y="7.4" width="5.4" height="4.6"/><rect x="13.2" y="12" width="5.4" height="4.6"/>` |
| **Tuiles** | damier raccordable | `<rect x="3" y="4.8" width="8.4" height="6.6"/><rect x="12.6" y="4.8" width="8.4" height="6.6" opacity=".34"/><rect x="3" y="12.6" width="8.4" height="6.6" opacity=".34"/><rect x="12.6" y="12.6" width="8.4" height="6.6"/>` |
| **Matières** | sphère d'échantillon | `<circle cx="12" cy="12" r="8.6" opacity=".34"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/>` |
| **Cartes** | cartes empilées | `<rect x="4.6" y="6.4" width="10.4" height="13.8" opacity=".34" transform="rotate(-10 9.8 13.3)"/><rect x="10.2" y="4.6" width="9.6" height="15"/>` |

**Deux niveaux de sens volontaires**, à préserver : *3D* et *3D Studio* partagent le même
cube, l'un seul, l'autre posé dans un viewport — la parenté est lisible. *Matières* garde
exactement la même sphère dans la barre horizontale et à l'étape 06 de Card Forge : même
objet, même glyphe, deux emplacements.

### 2.5 Livraison technique suggérée

Un module par famille, exportant des composants dont la couleur vient de `currentColor` et
la taille d'une prop `size` :

```
src/icons/nav/*        11 icônes de navigation
src/icons/forge/*      10 icônes Card Forge
src/icons/category/*    6 icônes de catégorie, bords droits
src/icons/chevron.tsx   le chevron unique de la section 4
```

Aucune icône ne porte de couleur en dur. Aucune n'est un fichier PNG.

---

## 3. Barre horizontale colorée et propagation de la teinte

### 3.1 La barre (variante 2a)

Structure : `display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px;` sur un fond
`--brd-hard`, avec `border: 1px solid var(--brd-hard)`. Le `gap` de 1 px **est** le
séparateur : pas de bordure par bouton, pas de pastille flottante.

**`border-radius: 0` sur la barre et sur chaque onglet.** C'est la demande explicite : la
barre remplace les onglets à coins arrondis de la version actuelle.

Chaque onglet, hauteur **46 px**, `display:flex; align-items:center; justify-content:center; gap:7px` :

1. Un **liséré bas de 2 px** dans la teinte de la catégorie, `position:absolute; left:0; right:0; bottom:0`, **toujours visible, y compris inactif**. C'est le point central de la proposition : la couleur *identifie* la catégorie, elle ne signale pas seulement la sélection. Un utilisateur reconnaît « Tuiles » au vert avant de lire le mot.
2. Un **calque de remplissage** `position:absolute; inset:0; background: var(--cat-n); transform-origin: left center; transform: scaleX(0 → 1); transition: transform var(--dur-fill) var(--ease-panel)`.
3. L'icône (17 px, section 2.4) et le libellé (11,5 px / 500), tous deux en `position:relative` pour passer au-dessus du remplissage.

États :

| État | Icône + libellé | Fond |
|---|---|---|
| Inactif | `var(--cat-n)` pour l'icône, `--txt-mid` pour le texte | `--srf-raised` |
| Survol | idem, `--srf-hover` | — |
| **Actif** | `--cat-ink` (#14181d) | aplat `var(--cat-n)`, balayé de gauche à droite |
| Enfoncé | — | `transform: scale(.94) translateY(1px)` pendant `--dur-press`, courbe `--ease-pop` |

L'animation au clic est donc double et lisible : le bouton s'enfonce brièvement, l'aplat
de couleur balaie la largeur de l'onglet, glyphe et libellé s'inversent en sombre. Aucun
indicateur ne se déplace d'un onglet à l'autre — chaque onglet possède sa propre couleur,
un curseur glissant serait contradictoire.

Libellés, verbatim : `3D` · `3D Studio` · `Sprites 2D` · `Tuiles` · `Matières` · `Cartes`.

### 3.2 Propagation de la teinte dans la section pilotée

**C'est la partie à ne pas sous-traiter au CSS de chaque écran.** L'onglet actif pose une
seule variable sur le conteneur de la section, et tout ce qui est en dessous l'hérite :

```jsx
const CAT_HUE = {
  '3d': 'oklch(.72 .13 255)',
  '3d-studio': 'oklch(.72 .13 300)',
  'sprites-2d': 'oklch(.72 .13 200)',
  'tuiles': 'oklch(.72 .13 145)',
  'matieres': 'oklch(.72 .13 80)',
  'cartes': 'oklch(.72 .13 25)',
};

<section data-category={active} style={{ '--cat': CAT_HUE[active] }}>
  {/* toute l'UI de la section, y compris Card Forge, ne lit plus que var(--cat) */}
</section>
```

Ce qui **doit** basculer sur `var(--cat)` dans le corps de la section — en remplacement
de l'or `#e6b23c` actuel :

- Étape active du bandeau Card Forge : numéro, icône, fond `--cat-fill`, filet gauche de 2 px.
- En-têtes de sous-panneau et leur filet supérieur (`ÉPREUVE DE CONTRÔLE`, `ROBUSTESSE`, `DÉCOR DE CADRE PAR IA`, `FENÊTRE D'ILLUSTRATION`).
- Boutons primaires de la section (`Construire l'épreuve de contrôle`, `Générer le décor`, `Relancer le balayage`) : fond `--cat-fill`, bordure `--cat-line`, texte `--txt-hi`.
- Remplissage de curseur (`OPACITÉ DU DÉCOR`), poignée comprise.
- Cadre de sélection et poignées dans `FENÊTRE D'ILLUSTRATION`, liséré de la carte en aperçu.
- Puces de bascule actives (`600` dans DÉFINITION, `Repères`), anneau de focus clavier.
- Chevrons de repli **de la section** (voir 4.3).

Ce qui **ne bascule pas** et reste neutre ou en or de marque :

- Barre supérieure, compteur de crédits, badges de service (`fal`, `heygen`, `voice`, `v2.5.0`), puce d'enregistrement — hors périmètre de catégorie.
- Rail de navigation gauche global : il pilote des sections *frères*, pas la catégorie courante ; il conserve l'or.
- Tout texte courant, toute mesure, tout tableau de contrôle. **Les couleurs sémantiques restent sémantiques** : les ✓ verts et les ✗ rouges des tableaux de robustesse ne prennent jamais la teinte de catégorie, même quand la catégorie est verte ou rouge. Ils utilisent des tokens dédiés (`--ok`, `--fail`) qui doivent être introduits s'ils n'existent pas.

**Budget de couleur : ~10 % de la surface de la section au maximum.** La teinte marque les
points d'action et l'état actif. Un fond de panneau teinté, un texte courant teinté ou une
bordure de conteneur teintée sortent du cadre.

**Transition entre catégories** : la variable change, tout ce qui l'hérite anime sa couleur
sur `300ms ease`. Ne pas animer la position ou la taille pendant un changement d'onglet.

**Accessibilité.** Les six teintes ont la même clarté, ce qui garantit un contraste uniforme
mais **ne suffit pas** : la couleur ne doit jamais être le seul porteur d'information.
L'onglet actif porte aussi son aplat plein et son inversion de texte ; l'étape Card Forge
active porte aussi son filet gauche. À vérifier au moment de l'intégration : texte
`--cat-ink` sur aplat `var(--cat)` doit dépasser 4,5:1 pour les six teintes.

---

## 4. Chevrons de repli / expansion — un seul système, partout

Aujourd'hui l'application mélange plusieurs affordances de repli. La règle devient unique.

### 4.1 Le glyphe

Un chevron plein, 12 px, à angles nets, dans la même famille bicolore que le reste :

```html
<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
  <path d="M14.8 5.6 9 12l5.8 6.4z"/>
</svg>
```

Pointe vers la **gauche** à l'état déployé. Une seule icône dans toute la codebase ; toutes
les orientations sont obtenues par rotation.

### 4.2 Le bouton porteur

Carré de **22 × 22**, `border-radius: 6px` (le bouton, pas le glyphe), fond
`--cat-fill` — ou `--srf-active` hors contexte de catégorie —, glyphe en `var(--cat)`.
Cible tactile portée à 32 px par du padding transparent. `aria-expanded` obligatoire,
`aria-controls` pointant sur le panneau, `aria-label` explicite
(« Replier le bandeau Card Forge »).

### 4.3 Orientations, par type de zone

Le chevron **pointe toujours dans la direction du mouvement de fermeture**. Un seul
composant, une prop `edge` :

| `edge` | Zone concernée | Déployé | Replié |
|---|---|---|---|
| `left` | bandeau de navigation, bandeau Card Forge (rails de gauche) | `rotate(0deg)` | `rotate(180deg)` |
| `right` | panneaux d'inspection à droite (`DÉCOR DE CADRE PAR IA`, `FENÊTRE D'ILLUSTRATION`) | `rotate(180deg)` | `rotate(0deg)` |
| `down` | sections empilables verticalement (`ÉPREUVE DE CONTRÔLE`, `ROBUSTESSE`, groupes de formulaire) | `rotate(-90deg)` | `rotate(90deg)` |

Rotation : `transition: transform var(--dur-panel) var(--ease-panel)`. **La rotation du
chevron et le mouvement du panneau partagent durée et courbe** — c'est ce qui donne
l'impression que le chevron pousse le panneau.

### 4.4 Comportement de repli d'un rail horizontal

Le rail passe de **236 px à 62 px** (navigation) ou de **210 px à 58 px** (Card Forge).

- La **largeur seule** s'anime, sur `--dur-panel` / `--ease-panel`. `overflow: hidden` et
  `white-space: nowrap` sur le conteneur.
- Chaque ligne reste un `flex` à trois zones : icône `flex:none`, libellé `flex:1; min-width:0; overflow:hidden`, méta `flex:none`. **L'icône ne bouge pas d'un pixel** pendant le repli — c'est le repère qui rend l'état replié utilisable.
- Le libellé s'échappe : `opacity: 1 → 0` sur `--dur-label`, `translateX(0 → -22px)` sur `380ms`, avec un **décalage en cascade de 25 ms par ligne** de haut en bas.
- Les icônes rebondissent en cascade au même rythme (`scale: 1 → .74 → 1.08 → 1` sur 460 ms), ce qui donne à la fermeture une lecture de haut en bas plutôt qu'un effondrement en bloc.
- L'état replié doit servir de vraie navigation : `title` ou infobulle sur chaque icône, ligne active toujours marquée par son filet gauche de 2 px.

### 4.5 Comportement de repli d'une section verticale

`grid-template-rows: 1fr` → `0fr`, ou `height` animée depuis `scrollHeight`, sur
`--dur-panel` / `--ease-panel`. L'en-tête reste visible et cliquable **sur toute sa
largeur** (pas seulement sur le chevron). Le contenu passe en `opacity: 0` sur
`--dur-label`.

### 4.6 Inventaire à couvrir

Repérés sur l'écran `Game Assets` ; à balayer dans l'ensemble de l'application, l'objectif
étant qu'**aucune autre affordance de repli ne subsiste** :

1. Rail de navigation gauche (`edge: left`)
2. Bandeau d'étapes Card Forge 01–10 (`edge: left`)
3. Panneau `DÉCOR DE CADRE PAR IA` (`edge: right`)
4. Panneau `FENÊTRE D'ILLUSTRATION` (`edge: right`)
5. Bloc `ÉPREUVE DE CONTRÔLE — TRAITS DE COUPE ET MIRES` (`edge: down`)
6. Bloc `ROBUSTESSE — LES 12 FORMATS, LES 2 BORNES DU RAYON` (`edge: down`)
7. Barre de format / définition / fond perdu (`edge: down`)
8. Colonne d'aperçu de carte (`edge: left`)
9. Tout groupe de formulaire replié dans les autres sections

**Persistance** : l'état de chaque zone est mémorisé par utilisateur, clé
`deepotus.panel.<id>.collapsed`, restauré au chargement **sans animation** (poser l'état
final, puis réactiver les transitions à la frame suivante).

---

## 5. État applicatif

```ts
type CategoryId = '3d' | '3d-studio' | 'sprites-2d' | 'tuiles' | 'matieres' | 'cartes';

activeCategory: CategoryId          // onglet de la barre horizontale ; pose --cat
pressedTab:     CategoryId | null   // effacé après --dur-press (170 ms)
panels:         Record<string, boolean>   // id de zone → replié ; persisté
forgeStep:      number              // 1..10, étape Card Forge active
```

`activeCategory` doit vivre au niveau de la section, pas dans la barre : la barre en est le
contrôle, la section en est la consommatrice via `--cat`. Chaque catégorie conserve son
propre `forgeStep` et son propre état de panneaux si le produit le justifie ; sinon,
partagés.

---

## 6. Ordre d'implémentation conseillé

1. **Tokens** — poser `--cat-*`, les dérivés, les tokens de mouvement, `--ok` / `--fail`. Rien d'autre ne peut avancer proprement avant.
2. **Chevron unique** — un composant, prop `edge`, `aria-expanded`. Remplacer les affordances existantes une par une (section 4.6). Chantier le plus large, le plus mécanique.
3. **Icônes** — les 27 tracés, en trois modules. Substitution 1:1, aucun changement de layout.
4. **Barre 2a** — bords droits, gap de 1 px, liséré permanent, remplissage balayé.
5. **Propagation** — poser `--cat` sur le conteneur de section, puis remplacer `#e6b23c` par `var(--cat)` **uniquement** dans la liste de la section 3.2. Passer en revue chaque occurrence restante de l'or : soit elle est de marque, soit elle est un oubli.
6. **Persistance** des panneaux, restauration sans animation.
7. **Passe `prefers-reduced-motion`** et vérification des contrastes.

---

## 7. Fichiers de référence

| Fichier | Contenu |
|---|---|
| `Icônes Deepotus.dc.html` | Prototype interactif. Tour **1** : variantes `1a` (filaire technique) et `1b` (glyphe bicolore, **retenue**), les 27 icônes en situation, repli des deux bandeaux cliquable. Tour **2** : variante `2a`, barre horizontale colorée à bords droits, clic animé. La grille de correspondances en bas du tour 1 documente le sens de chaque icône. |

Ouvrir le fichier dans un navigateur, cliquer les chevrons et les onglets : les durées et
les courbes du prototype sont celles à reproduire.
