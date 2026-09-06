# Deepotus — Design spec : barre d'outils déportable de la timeline

> **Comment intégrer ce fichier.** Ce document complète
> `C:\Users\olivi\DeepotusVideo\design.md` — il ne le remplace pas. Il ajoute une
> section autonome consacrée à la barre d'outils flottante de la timeline. Les tokens de
> couleur, de mouvement et les règles de dessin d'icônes viennent du fichier
> `design_handoff_icones_couleurs/design.md` livré précédemment ; **ce fichier en dépend
> et n'en redéfinit rien**. Si le chantier icônes/couleurs n'est pas encore intégré,
> l'intégrer d'abord : la palette de catégories est le socle de cette barre.
>
> **Nature du livrable.** La maquette de référence est `Barre Outils Flottante.dc.html`,
> livrée à côté de ce fichier. C'est un **prototype HTML de référence**, pas du code à
> copier : il montre l'apparence, la géométrie et le comportement attendus. Le travail
> consiste à **recréer ce design dans la codebase existante** (React / Vite / Tailwind ou
> ce qui est en place), avec ses conventions et ses composants.
>
> **Fidélité : haute (hifi).** Couleurs, tailles, durées et courbes sont définitives. Les
> tracés SVG sont donnés intégralement et doivent être repris tels quels. Les libellés
> sont ceux de l'application et ne doivent pas être réécrits.
>
> **Point ouvert signalé en section 8** : trois fonctionnalités nouvelles sont proposées
> parce que le déport de la barre les rend possibles. Elles sont explicitement marquées
> comme propositions ; ne pas les implémenter sans validation.

---

## 0. Périmètre

Le bandeau de transport de la timeline porte aujourd'hui, sur une seule ligne, le
transport, les outils de coupe, le zoom **et** neuf actions de création (`+ piste vidéo`,
`+ piste audio`, `Bibliothèque…`, `MOT couleur / rebond / glow`, `emoji`, `texte`,
`projets`). La ligne est saturée : les commandes de montage courantes — collage, coupe,
sous-titres, panneau son, déroulement des pistes — n'ont plus de place lisible.

Deux chantiers, dans cet ordre de dépendance :

| # | Chantier | Portée |
|---|---|---|
| 1 | **Barre d'outils déportable** | Nouveau composant flottant, déplaçable, repliable sur un onglet ; 9 actions réparties en 5 groupes colorés ; 9 nouvelles icônes |
| 2 | **Redistribution du bandeau fixe** | Retrait des 9 actions ; réattribution de la place libérée aux commandes de montage |

Rien d'autre dans la timeline n'est concerné : les pistes, la règle temporelle, la tête de
lecture et les clips restent inchangés.

---

## 1. Tokens

### 1.1 Repris tels quels

Surfaces, texte et mouvement : voir `design.md` §1.1 et §1.3. Employés ici :
`--srf-panel` `#13171c`, `--srf-raised` `#171c22`, `--srf-hover` `#181d23`,
`--brd-hard` `#20262d`, `--brd-soft` `#1c2229`, `--txt-hi` `#eef2f6`,
`--txt-base` `#cfd6dd`, `--txt-mid` `#8b959f`, `--txt-low` `#5f6873`,
`--txt-faint` `#4d5661`, `--ease-panel`, `--ease-pop`, `--dur-press`, `--dur-label`.

### 1.2 Palette de groupes — cinq des six teintes de catégorie

La barre réutilise **la palette existante**, sans y ajouter de teinte. Même clarté, même
chroma, seule la teinte varie : aucun groupe ne domine visuellement les autres.

```css
--grp-pistes:  oklch(.72 .13 200);  /* cyan   — pistes */
--grp-biblio:  oklch(.72 .13 255);  /* bleu   — bibliothèque */
--grp-mot:     oklch(.72 .13 300);  /* violet — mot */
--grp-ajouts:  oklch(.72 .13  80);  /* ambre  — ajouts */
--grp-projets: oklch(.72 .13 145);  /* vert   — projets */
```

**Le rouge `oklch(.72 .13 25)` reste hors de la barre**, réservé au destructif. C'est
pourquoi `supprimer` vit dans le bandeau fixe et y est le seul élément rouge.

Dérivés, par calcul depuis la teinte du groupe, jamais en dur :

```css
--grp-fill: oklch(from var(--grp) l c h / .16);  /* fond de bouton actif */
--grp-line: var(--grp);                          /* bordure de bouton actif */
```

### 1.3 Nouveaux tokens propres à la barre

```css
--bar-srf:     #13171c;                    /* fond de la barre */
--bar-brd:     #2a323b;                    /* bordure de la barre — plus claire qu'un
                                              panneau ancré : la barre flotte */
--bar-shadow:  0 14px 34px rgba(0,0,0,.62); /* seule ombre portée de l'application */

--dur-bar-open: 220ms;  /* apparition / repli de la barre */
--dur-bar-snap: 180ms;  /* aimantation de la position au relâchement */
```

L'ombre portée est **le seul signal de flottement**. Ne pas ajouter de flou d'arrière-plan,
ni de transparence : la timeline défile sous la barre, un fond translucide rendrait les
icônes illisibles pendant la lecture.

---

## 2. Anatomie

### 2.1 L'onglet d'appel

Un onglet à cheval sur le **bord supérieur** du bandeau fixe, débordant vers le haut.

- **21 px de haut**, `padding: 0 11px`, `top: -21px; left: 14px` relativement au bandeau.
- `border: 1px solid var(--bar-brd); border-bottom: 0; border-radius: 0`.
- Contenu, dans cet ordre : **cinq pastilles de 5 × 5 px** aux cinq teintes de groupe
  (`gap: 2px`), le libellé `OUTILS` en IBM Plex Mono 10 px / 500, `letter-spacing: .1em`,
  puis un chevron `▾` / `▴` à `opacity: .6`.
- Les pastilles sont l'aperçu du contenu : on voit les cinq familles avant d'ouvrir.

| État | Fond | Texte |
|---|---|---|
| Barre repliée | `--srf-raised` | `--txt-mid` |
| Barre ouverte | `--srf-panel` — l'onglet et la barre se lisent comme une seule pièce | `--txt-hi` |

Le bandeau fixe doit donc passer en `position: relative` et laisser déborder l'onglet
(`overflow: visible`). Vérifier qu'aucun conteneur parent ne le rogne.

### 2.2 La barre

`display: flex; align-items: stretch` sur `--bar-srf`, `border: 1px solid var(--bar-brd)`,
`box-shadow: var(--bar-shadow)`, **`border-radius: 0`** — même langage à angles droits que
la barre horizontale 2a. Hauteur résultante ≈ **74 px** avec les libellés, ≈ **50 px** sans.

Trois zones, de gauche à droite :

**a. Poignée** — 26 px de large, pleine hauteur, fond `--srf-raised`, filet droit
`--brd-hard`, glyphe *grip* 14 px en `--txt-low`. `cursor: grab`, `grabbing` pendant le
glissement. Au survol : glyphe en `--txt-mid`, fond `--srf-hover`.

**b. Groupes** — `padding: 9px 10px 8px`. Chaque groupe est une colonne :

- **En-tête** : IBM Plex Mono 8,5 px / 500, `letter-spacing: .14em`, en `var(--grp)`,
  `padding: 0 4px 7px`. Libellés verbatim : `PISTES` · `BIBLIOTHÈQUE` ·
  `MOT` · `AJOUTS` · `PROJETS`. L'en-tête `MOT` porte un suffixe
  `— sélection` à `opacity: .5` et `letter-spacing: .06em`, qui rappelle que le groupe agit
  sur la sélection courante du sous-titre.
- **Boutons** : rangée en `gap: 2px`.
- **Séparation** : filet droit de 1 px `--brd-soft` entre groupes, `padding: 0 11px`.
  Pas de filet après le dernier groupe.

**c. Contrôles de fenêtre** — colonne de 26 px, filet gauche `--brd-hard`, deux boutons
empilés à hauteur égale, séparés d'un filet `--brd-hard` :

| Bouton | Glyphe | Action | `aria-label` |
|---|---|---|---|
| Recentrer | `⌖` mono 11 px | remet la position d'origine | « Recentrer la barre d'outils » |
| Replier | `×` mono 13 px | replie sur l'onglet | « Replier la barre d'outils » |

Au repos `--txt-low` ; au survol `#e6b23c` sur `#1e242b`.

### 2.3 Le bouton d'action

C'est l'unité qui se répète neuf fois. Un seul composant.

```
largeur 60px (70px pour un groupe à bouton unique)
padding  7px 0 6px
display  flex; flex-direction: column; align-items: center; gap: 6px
border   1px solid transparent
icône    18px, fill="currentColor", color: var(--grp)
libellé  IBM Plex Mono 9,5px / 400, --txt-mid
```

| État | Fond | Bordure | Icône | Libellé |
|---|---|---|---|---|
| Repos | transparent | transparente | `var(--grp)` | `--txt-mid` |
| Survol | `--srf-hover` | `--brd-hard` | `var(--grp)` | `--txt-mid` |
| Enfoncé | — | — | `scale(.94) translateY(1px)` pendant `--dur-press`, `--ease-pop` | — |
| **Actif** (bascules seulement) | `--grp-fill` | `var(--grp)` | `--txt-hi` | `--txt-hi` |

Transition `background .14s ease, border-color .14s ease`.

L'icône **garde la teinte de son groupe au repos** : c'est le point central de la
proposition, comme pour la barre 2a. La couleur identifie la famille d'action, elle ne
signale pas la sélection. On reconnaît « ajouter une piste » au cyan avant de lire le mot.
À l'état actif l'icône passe au contraire en `--txt-hi` sur fond teinté — inversion
franche, pas une variation de saturation.

**Les libellés sont masquables** (`--lbl: none`), pas supprimables : en mode compact,
chaque bouton exige un `title` et un `aria-label`. Ne pas livrer un mode compact sans
infobulles.

### 2.4 Contenu, verbatim

| Groupe | Teinte | Boutons | Type |
|---|---|---|---|
| `PISTES` | cyan 200 | `vidéo` · `incrust.` · `audio` | action |
| `BIBLIOTHÈQUE` | bleu 255 | `lier` | ouvre un panneau |
| `MOT — sélection` | violet 300 | `couleur` · `rebond` · `glow` | **bascules** |
| `AJOUTS` | ambre 80 | `emoji` · `texte` | outils de placement |
| `PROJETS` | vert 145 | `projets` | ouvre un panneau |

---

## 3. Les neuf icônes

Mêmes règles que le jeu 1b (`design.md` §2.1) : grille **24 × 24**, rendu **18 px**,
`fill="currentColor"`, masses pleines sans contour, deux niveaux d'opacité — sujet à `1`,
support entre `.26` et `.45`. Angles droits, aucun `rx`, cohérence avec la barre 2a.

Chaque entrée : `viewBox="0 0 24 24" fill="currentColor"`.

| Icône | Sens retenu | Tracé |
|---|---|---|
| **piste vidéo** | deux pistes + croix d'ajout | `<rect x="2.6" y="4.2" width="18.8" height="5.6" opacity=".34"/><rect x="2.6" y="11.6" width="10.4" height="5.6"/><path d="M17 12.6h1.9V15h2.4v1.9h-2.4v2.4H17v-2.4h-2.4V15H17z"/>` |
| **piste audio** | forme d'onde + croix d'ajout | `<rect x="2.6" y="10.2" width="2.2" height="3.6" opacity=".45"/><rect x="6.2" y="6.6" width="2.2" height="10.8"/><rect x="9.8" y="8.8" width="2.2" height="6.4"/><rect x="13.4" y="4.6" width="2.2" height="15" opacity=".45"/><path d="M17.6 12.6h1.9V15h2.4v1.9h-2.4v2.4h-1.9v-2.4h-2.4V15h2.4z"/>` |
| **bibliothèque** | couches empilées — *identique à l'icône `Library` du bandeau de navigation, volontairement* | `<path d="M12 2.8 21 7.2 12 11.6 3 7.2z"/><path d="M12 13.6 4.6 10l-1.6.8L12 15.2l9-4.4-1.6-.8zM12 18.2 4.6 14.6l-1.6.8L12 19.8l9-4.4-1.6-.8z" opacity=".42"/>` |
| **couleur** | mot à moitié teinté + nuancier | `<rect x="2.8" y="7.4" width="18.4" height="6.2" opacity=".34"/><rect x="2.8" y="7.4" width="8.8" height="6.2"/><rect x="2.8" y="16.4" width="4.8" height="3.6"/><rect x="9.6" y="16.4" width="4.8" height="3.6" opacity=".5"/><rect x="16.4" y="16.4" width="4.8" height="3.6" opacity=".34"/>` |
| **rebond** | lettres décalées en arc sur une ligne de base | `<rect x="2.8" y="16.8" width="18.4" height="4.2" opacity=".34"/><rect x="3.2" y="8.6" width="4.6" height="4.6"/><rect x="9.7" y="3.4" width="4.6" height="4.6"/><rect x="16.2" y="8.6" width="4.6" height="4.6" opacity=".55"/>` |
| **glow** | masse centrale + rayons | `<rect x="6.6" y="9.4" width="10.8" height="5.2"/><rect x="11.2" y="2.2" width="1.6" height="4.2" opacity=".45"/><rect x="11.2" y="17.6" width="1.6" height="4.2" opacity=".45"/><rect x="2.2" y="11.2" width="4.2" height="1.6" opacity=".45"/><rect x="17.6" y="11.2" width="4.2" height="1.6" opacity=".45"/>` |
| **emoji** | visage à angles droits | `<rect x="3" y="3" width="18" height="18" opacity=".3"/><rect x="7.4" y="7.6" width="2.8" height="3.6"/><rect x="13.8" y="7.6" width="2.8" height="3.6"/><rect x="7.4" y="14.2" width="9.2" height="2.6"/>` |
| **texte** | T + ligne de base | `<rect x="3.4" y="3.8" width="17.2" height="3.4"/><rect x="10.3" y="7.2" width="3.4" height="11.6"/><rect x="5.2" y="20.2" width="13.6" height="1.8" opacity=".34"/>` |
| **projets** | dossier + feuille derrière | `<rect x="6" y="3" width="15.4" height="11.6" opacity=".3"/><path d="M2.6 6.2h6.2l1.7 2.1h11.1v12.5H2.6z"/>` |
| **poignée** *(grip, 14 px, `--txt-low`)* | six points en deux colonnes | `<rect x="8" y="4" width="2.6" height="2.6"/><rect x="13.4" y="4" width="2.6" height="2.6"/><rect x="8" y="10.7" width="2.6" height="2.6"/><rect x="13.4" y="10.7" width="2.6" height="2.6"/><rect x="8" y="17.4" width="2.6" height="2.6"/><rect x="13.4" y="17.4" width="2.6" height="2.6"/>` |

**Écart du 06/09/2026 :** le groupe `PISTES` offre une troisième action, `incrust.`, et
ce §3 une dixième icône — onze tracés avec la poignée (mesuré : au rendu toute piste vidéo
≠ V1 est une incrustation ; l'utilisateur doit pouvoir choisir). « vidéo » crée une piste
vidéo plein cadre (ses plans recouvrent V1 pendant leur durée, leur son est extrait sur la
piste de dialogue ; V1 reste la séquence maîtresse), « incrust. » une piste d'incrustation
(image dans l'image, réglable, muette). Le §5.1 reste à neuf : ce bouton est né dans la
barre, il n'a jamais été dans le bandeau. Même grille, mêmes règles ; la croix d'ajout est
celle de « piste vidéo », reprise telle quelle.

| Icône | Sens retenu | Tracé |
|---|---|---|
| **piste incrustation** | cadre en support + cadre intérieur plein décalé en bas à droite + croix d'ajout | `<rect x="2.6" y="4.2" width="13.6" height="10.4" opacity=".34"/><rect x="8.4" y="8.4" width="6" height="4.2"/><path d="M17 12.6h1.9V15h2.4v1.9h-2.4v2.4H17v-2.4h-2.4V15H17z"/>` |

**Parentés à préserver.** `bibliothèque` est *le même glyphe* que l'entrée `Library` du
rail de navigation : même objet, même dessin, deux emplacements. `couleur`, `rebond` et
`glow` partagent tous trois la même métaphore de départ — un mot posé sur sa ligne de
base — et ne se distinguent que par ce qui lui arrive. Cette parenté est ce qui fait lire
les trois comme un groupe avant même leur teinte commune.

Livraison : `src/icons/toolbar/*`, un composant par icône, couleur par `currentColor`,
taille par prop `size`. Aucune couleur en dur, aucun PNG.

---

## 4. Comportement

### 4.1 Ouverture et repli

- L'onglet `OUTILS` **bascule** l'état. `aria-expanded` obligatoire, `aria-controls`
  pointant sur la barre.
- Apparition : `opacity 0 → 1` et `translateY(6px → 0)` sur `--dur-bar-open`,
  `--ease-panel`. Repli : l'inverse. **Ne pas animer la hauteur** — le contenu se
  déformerait.
- Les icônes n'entrent pas en cascade ici : la barre est un objet unique et compact, la
  cascade est réservée au repli des rails verticaux (`design.md` §4.4).
- Raccourci clavier : `T`. À l'ouverture, le focus va au premier bouton.

### 4.2 Déport

- Glissement **par la poignée uniquement**. Ne pas rendre la barre entière déplaçable :
  neuf cibles de clic y vivent.
- `pointerdown` sur la poignée, `pointermove` / `pointerup` sur `window`, jamais sur
  l'élément — le pointeur sort de la poignée dès le premier geste rapide.
- Position stockée en **décalage** (`dx`, `dy`) depuis l'ancrage d'origine, pas en
  coordonnées absolues : la barre reste à sa place relative quand la fenêtre est
  redimensionnée.
- **Bornes** : la barre doit rester entièrement dans la zone timeline + zone de prévisualisation.
  Bornage à l'intérieur du conteneur, avec une marge de 8 px. Une barre à moitié sortie de
  l'écran n'est pas récupérable.
- Au relâchement, **aimantation** sur `--dur-bar-snap` si un bord de la barre passe à moins
  de 12 px d'un bord du conteneur ou de l'axe de la tête de lecture.
- `⌖` **recentrer** remet `dx = dy = 0`. Ce bouton est le filet de sécurité de tout le
  système de déport ; il ne doit jamais être masqué en mode compact.
- Pendant le glissement : `cursor: grabbing` sur `document.body` — pas seulement sur la
  poignée — et `user-select: none` pour ne pas sélectionner les libellés de piste.

### 4.3 Bascules du groupe MOT

`couleur`, `rebond`, `glow` sont **indépendantes et cumulables** : un mot peut être coloré,
rebondissant et lumineux à la fois. Ce ne sont pas des boutons radio.

- Elles agissent sur la **sélection courante dans la piste de sous-titres**. Sans
  sélection : boutons désactivés à `opacity: .38`, `cursor: not-allowed`, et
  `title` explicatif (« Sélectionner un mot dans les sous-titres »). Ne pas les masquer —
  la barre changerait de largeur, ce qui déplacerait tous les autres boutons.
- L'état actif reflète **la sélection**, pas un mode d'outil : changer de mot met les trois
  bascules à jour. Sur une sélection multiple hétérogène, état indéterminé : bordure
  `var(--grp)` mais fond transparent.
- `couleur` : au clic, ouvre un sélecteur de teinte **ancré sous le bouton**. Proposer un
  jeu restreint (les six teintes de catégorie + blanc + l'or de marque), pas un
  sélecteur libre — un nuancier ouvert produit des sous-titres illisibles.
- `rebond` et `glow` sont des bascules directes, sans panneau.

### 4.4 Persistance

Clé par utilisateur, dans le même espace de nommage que les panneaux existants :

```
deepotus.toolbar.open       boolean
deepotus.toolbar.offset     { dx: number, dy: number }
deepotus.toolbar.labels     boolean
```

Restauration au chargement **sans animation** : poser l'état final, réactiver les
transitions à la frame suivante — même règle qu'en `design.md` §4.6.

### 4.5 Clavier et accessibilité

- La barre est un `role="toolbar"` avec `aria-orientation="horizontal"` et
  `aria-label="Outils de création"`.
- Navigation aux flèches gauche/droite **entre les boutons, en traversant les groupes** ;
  un seul point d'entrée dans l'ordre de tabulation (`tabindex` roving).
- `Échap` replie la barre et rend le focus à l'onglet.
- La poignée est un bouton focusable : flèches = déplacement de 8 px, `Maj + flèches` = 1 px.
  Un objet déplaçable à la souris seule n'est pas accessible.
- La couleur n'est jamais le seul porteur d'information : chaque groupe a son en-tête en
  clair, chaque bouton son libellé ou son infobulle, chaque bascule active son inversion de
  texte en plus de son fond teinté.
- `prefers-reduced-motion: reduce` : durées à `1ms`, aimantation immédiate, aucun
  enfoncement.

---

## 5. Redistribution du bandeau fixe

### 5.1 Ce qui quitte le bandeau

Les neuf contrôles suivants sont **retirés** du bandeau de transport et n'existent plus
qu'au sein de la barre flottante : `+ piste vidéo`, `+ piste audio`, `Bibliothèque…`,
l'étiquette `MOT` et ses trois options `couleur` / `rebond` / `glow`, `emoji`, `texte`,
`projets`.

Ne pas les laisser en double. Un contrôle présent aux deux endroits annule le bénéfice de
place et crée deux sources de vérité pour l'état des bascules.

### 5.2 Ce que devient le bandeau

Hauteur **46 px**, `padding: 0 14px`, fond `--srf-panel`, filets haut et bas `--brd-hard`,
`position: relative` pour l'onglet. Ordre de gauche à droite, séparateurs verticaux de
1 px `--brd-hard` avec `margin: 0 12px` entre chaque bloc :

1. **Timecode** — position en `--txt-hi`, durée totale en `--txt-low`, IBM Plex Mono 11 px.
2. **Transport** — cinq boutons de 30 px (`◀◀` `|◀` `▶` `▶|` `▶▶`), `gap: 2px`. Le bouton
   de lecture est le seul en or `#e6b23c` sur texte `#14181d` : c'est une commande de
   marque, hors catégorie.
3. **Outils de coupe** — `aimanter` · `lame` (avec son raccourci `ALT+C` en mono 9 px
   `--txt-low`) · `ripple`. Inchangés.
4. **Édition — bloc qui gagne la place** : `couper` · `coller` · `scinder` ·
   `supprimer`. Ce dernier est le **seul élément rouge** du bandeau,
   `color: oklch(.72 .13 25)`.
5. **Sous-titres** — `sous-titres` avec son compteur en pastille or (`9 · 64 %`),
   mono 9 px sur `#e6b23c`, texte `#14181d`.
6. **Son — bloc qui gagne la place** : bouton `panneau son`, puis un contrôle de mix inline
   (étiquette `mix` en mono 9 px `--txt-low`, rail de 64 × 4 px `--brd-hard` rempli en
   `--txt-mid`, valeur `-6` en mono 9 px). Le réglage le plus courant devient accessible
   sans ouvrir le panneau.
7. **Poussé à droite** (`flex: 1` intercalaire) : zoom — étiquette `zoom`, rail de
   86 × 4 px, valeur `100 %` — puis `ajuster`, puis les **deux chevrons de hauteur de
   piste** empilés (24 × 11 px chacun, `▲` / `▼`, `gap: 2px`).

Style commun des boutons du bandeau : hauteur 26 px, `padding: 0 9px`, 11 px,
`border: 1px solid var(--brd-hard)`, fond `--srf-raised`, survol `#1e242b`,
`border-radius: 0`.

### 5.3 Comportement en largeur réduite

Le bandeau ne doit **jamais** passer sur deux lignes ni provoquer de défilement
horizontal. Ordre de dégradation, du premier sacrifié au dernier :

1. Le contrôle de mix inline se réduit à son bouton `panneau son`.
2. Les libellés des outils de coupe passent en icônes seules avec infobulles.
3. Le bloc d'édition se replie dans un menu `⋯`.
4. Le timecode perd sa durée totale.

Le transport, les sous-titres, le zoom et l'onglet `OUTILS` ne se dégradent jamais.

---

## 6. Câblage fonctionnel

Ce que chaque bouton doit faire. Là où une action existe déjà dans la codebase, réutiliser
l'action existante : la barre est un **nouveau point d'entrée**, pas une nouvelle
implémentation.

| Bouton | Action attendue | État touché |
|---|---|---|
| `PISTES · vidéo` | Ajoute une piste vidéo sous la dernière piste vidéo, la nomme `V{n}`, la sélectionne, fait défiler la timeline jusqu'à elle | `tracks[]` |
| `PISTES · incrust.` | *(écart du 06/09/2026)* Ajoute une piste d'incrustation — image dans l'image, réglable, muette — nommée `V{n}` ; « vidéo » ci-dessus ajoute désormais une piste vidéo **plein cadre** | `tracks[]` |
| `PISTES · audio` | Idem pour l'audio, nommage `A{n}` | `tracks[]` |
| `BIBLIOTHÈQUE · lier` | Ouvre le panneau de bibliothèque en mode « lier à la timeline » ; un double-clic sur un média l'insère à la tête de lecture, sur la piste sélectionnée | panneau, `selection` |
| `MOT · couleur` | Ouvre le nuancier ancré ; applique la teinte aux mots sélectionnés | `subtitles[].words[].color` |
| `MOT · rebond` | Bascule l'animation de rebond sur les mots sélectionnés | `…words[].fx.bounce` |
| `MOT · glow` | Bascule le halo sur les mots sélectionnés | `…words[].fx.glow` |
| `AJOUTS · emoji` | Ouvre le sélecteur d'emoji ; le choix crée un clip d'overlay sur la première piste `overlay/VFX` libre, à la tête de lecture, durée par défaut 2 s | `tracks[]`, `clips[]` |
| `AJOUTS · texte` | Crée un clip de texte sur la piste `overlay/VFX`, à la tête de lecture, et entre directement en édition du contenu | `clips[]`, `editing` |
| `PROJETS · projets` | Ouvre le sélecteur de projets. **Si le projet courant a des modifications non enregistrées, demander confirmation avant de quitter** | route, `project` |

Trois exigences transversales :

- **Toutes les actions passent par le même historique d'annulation** que le reste de la
  timeline. Une action déclenchée depuis une barre flottante doit s'annuler par `Ctrl+Z`
  comme n'importe quelle autre.
- **Aucune action ne déplace la tête de lecture.** Les insertions se font *à* la tête de
  lecture ; elles ne la bougent pas.
- Les insertions à la tête de lecture respectent l'état `aimanter` s'il est actif.

---

## 7. État applicatif

```ts
type ToolGroup = 'pistes' | 'biblio' | 'mot' | 'ajouts' | 'projets';

toolbar: {
  open:    boolean                  // onglet OUTILS ; persisté
  offset:  { dx: number, dy: number } // décalage depuis l'ancrage ; persisté
  labels:  boolean                  // libellés visibles ; persisté
  dragging: boolean                 // transitoire, jamais persisté
}

wordFx: {                           // dérivé de la sélection, jamais stocké en double
  color:  string | 'mixed' | null
  bounce: boolean | 'mixed'
  glow:   boolean | 'mixed'
}
```

`wordFx` est **calculé depuis la sélection**, pas conservé dans l'état de la barre. La
barre est un contrôle, la sélection est la source de vérité. Toute autre disposition
produira des bascules désynchronisées du contenu.

---

## 8. Trois propositions — à valider avant implémentation

Le déport rend ces trois choses possibles ; aucune n'était demandée. Elles sont listées
ici pour décision, pas pour être implémentées d'office.

1. **Barre en colonne verticale.** Le même composant en `flex-direction: column`, ancré
   contre le bord gauche de la zone timeline. Utile sur écran large où la hauteur est la
   ressource rare. Coût : les en-têtes de groupe doivent passer en pastilles de couleur,
   les libellés disparaissent.
2. **Deuxième instance de la barre.** Une palette flottante pouvant être dupliquée, chaque
   instance filtrée sur un ou deux groupes — `MOT` seul près des sous-titres, `PISTES` seul
   près des en-têtes de piste. Coût : `toolbar` devient un tableau d'instances ; la
   persistance change de forme. À ne faire que si l'usage réel le réclame.
3. **Groupes escamotables individuellement.** Un clic sur un en-tête replie son groupe sur
   sa seule pastille de couleur. Réduit la barre sans perdre les libellés des groupes
   ouverts. Coût : la largeur de la barre devient variable, ce qui déplace les boutons
   voisins — à mesurer contre le bénéfice.

---

## 9. Ordre d'implémentation conseillé

1. **Tokens** — `--grp-*`, dérivés, `--bar-*`, `--dur-bar-*`. Rien ne peut avancer avant.
2. **Les 9 icônes** — module `src/icons/toolbar/*`, tracés de la section 3.
3. **Le bouton d'action** — un composant, prop `group`, prop `toggle`, tous les états de
   la section 2.3. C'est la pièce qui se répète ; la faire juste une fois.
4. **La barre et son onglet** — géométrie, ouverture, repli, persistance de `open`.
5. **Le déport** — poignée, bornage, aimantation, recentrage, persistance de `offset`.
   Tester d'abord le bornage : c'est là que se logent les régressions.
6. **Retrait des neuf contrôles du bandeau fixe** et redistribution de la section 5.
   *Après* que la barre fonctionne, jamais avant : ne pas laisser l'application dans un
   état où les actions ne sont accessibles nulle part.
7. **Câblage** de la section 6, en réutilisant les actions existantes.
8. **Clavier, `role="toolbar"`, `prefers-reduced-motion`**, et vérification des contrastes :
   `--txt-hi` sur `--grp-fill` doit dépasser 4,5:1 pour les cinq teintes.

---

## 10. Fichiers de référence

| Fichier | Contenu |
|---|---|
| `Barre Outils Flottante.dc.html` | Prototype interactif. Tour **2**, variante `2a` : la barre flottante en situation au-dessus du bandeau fixe redistribué et de la timeline. La poignée est réellement déplaçable, `×` replie sur l'onglet, `⌖` recentre, les trois options de `MOT` sont des bascules cliquables. |
| `design_handoff_icones_couleurs/design.md` | **Prérequis.** Tokens de surface, palette de catégories, règles de dessin des icônes, tokens de mouvement, système de chevrons. |
| `Icônes Deepotus.dc.html` | Prototype du jeu d'icônes 1b et de la barre horizontale 2a — la référence de style dont les 9 icônes de cette barre sont issues. |

Ouvrir les prototypes dans un navigateur : les durées, les courbes et les états au survol
sont ceux à reproduire.
