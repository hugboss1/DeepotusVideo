# Chantier 11 — UI Shell Pro : job queue à la demande, toolbars, audit visuel

Brief validé par Olivier le 20/07/2026 (4/4 réponses = recommandations).
Registre : **product** (le design sert l'outil ; familiarité gagnée, pas
d'étrangeté). Révision assumée du DESIGN.md §5 : le Job Dock bas d'écran
« toujours visible » y était spécifié — décision annulée, un studio de vidéos
**9:16 verticales** ne peut pas sacrifier sa hauteur à un dock horizontal.

## 1. Résumé

Sortir la job queue de l'écran (icône topbar + panneau latéral droit à la
demande), corriger le bug des vignettes qui flottent par-dessus les vues,
normaliser les toolbars au-dessus des canvas (icônes + tooltips + accents de
domaine), et passer toute l'app au crible alignements/débordements avec un
harnais de mesure automatisé.

## 2. Action utilisateur primaire

Travailler plein écran sur son canvas ; d'un coup d'œil à la topbar, savoir
si quelque chose tourne (badge) ; d'un clic, ouvrir/fermer la file.

## 3. Direction

- **Stratégie couleur : Restrained** (DESIGN.md §3-4 : 70 % neutre, l'accent
  fait le travail). Icônes `--ink-soft`, accent de domaine au hover/actif
  SEULEMENT : cyan génération/action, violet composition/batch, amber
  sources/attention, vert audio/succès, rouge destructif/erreur.
- **Scène** : le solo founder monte ses posts la nuit, écran 1440p dans une
  pièce sombre, entre deux renders de 3 min — l'UI doit être calme, dense,
  navigable au clavier. (Thème sombre déjà acté par le DESIGN.md.)
- **Ancres** : Linear (topbar + panneaux + focus ring), Resolve (file de
  rendu), Krea (canvas + bibliothèque).
- Guard-rails DESIGN.md §13 inchangés : pas de modales lourdes, transitions
  < 400 ms, pas d'emojis dans les boutons primaires, confirmations inline.

## 4. Périmètre (validé)

Production-ready, toute l'app : shell (topbar/queue) + bug vignettes + audit
global incluant les pages standalone (/spritelab, /tilelab, /atelier).
Implémentation en **session dédiée** (cette spec = livrable de la session
plan). PRODUCT.md absent : lancer `/impeccable teach` en ouverture de la
session 11 pour le générer depuis DESIGN.md §1 (10 min, une fois).

## 5. Sous-chantiers

### 11a — Queue panel (l'architecture)

- Le Job Dock disparaît du flux : plus AUCUNE surface persistante en bas.
- Topbar : icône « file » (style `se`/`X` icons existants) + badge compteur
  `N` (jobs pending+processing, poll déjà en place). Badge : pastille cyan,
  halo pulsé 1.2 Hz pendant un run (keyframe halo-pulse existant), rouge fixe
  si un job failed non lu. Tooltip « File de rendu — N en cours ».
- Clic → panneau latéral DROIT en slide-in 320 ms `--ease` (spec préviz
  §6.7), largeur 360, scrim léger cliquable, Esc ferme. Contenu = les
  JobCards actuelles du dock (thumb `rr()` 56px, titre, progress, ETA,
  rename/clone/delete/open) en liste verticale, «N recent» au-dessous.
- États : vide (« Nothing rendering. Press ▶ Run… » + 🐙 doux, DESIGN.md §9),
  running (cards live), failed en tête bordure rouge. `prefers-reduced-motion`
  → pas de pulse, slide remplacé par fade opacity.
- Reformuler le toast Studio « still rendering — check the Job Dock »
  (bundle pos ~278273) → « — suis-le depuis l'icône File en haut ».
- Patch bundle à anchors (`scripts/patch_bundle_shellqueue.py`, backup
  `.bak_shellqueue`) : localiser le composant dock au runtime (DevTools /
  poignées `__dz*`) avant d'écrire les anchors. Poignée QA `window.__dzQueue`
  {open(), state}.

### 11b — Bug vignettes flottantes (cause racine d'abord)

Symptôme (screenshots d'Olivier, 2 occurrences) : des thumbs `rr()` badgés
OUT/IMG flottent PAR-DESSUS les panneaux du Sprite Lab et de la liste
renders. Suspects : portal/position du hover-preview des JobCards, z-index
du dock au-dessus de l'iframe, overflow non clippé pendant le drag.
Reproduire via Puppeteer (job réel gratuit remove_bg none pendant que la vue
/spritelab est active), identifier, fixer, et ajouter l'assertion au harnais
(aucun élément `rr` hors de son conteneur : bounding-box ⊂ parent).

### 11c — Toolbars au-dessus des canvas

- Une barre par vue, même vocabulaire partout (registre product : cohérence
  = affordance) : icônes 20 px neutres, accent domaine hover/actif, tooltip
  sombre 100 ms max-width 280 (spec §7) pour TOUT élément SAUF les selects/
  dropdowns (qui gardent leur libellé visible).
- Grille 4 px, gaps 12/16/24, alignement vertical unique par rangée (±2 px).
- Pas de nouvelle « feature » : réorganisation des actions existantes de
  chaque vue (Studio topbar spec §8.2 comme référence).

### 11d — Audit alignements & débordements (harnais)

`scripts/qa/qa-shell-audit.js` (Puppeteer) : pour chaque vue (Quick, Studio,
Chapitres, Scheduler, Templates, News, Library, Game Assets ×3 sous-onglets,
Settings + /spritelab /tilelab /atelier) :
- scan débordements : tout élément avec `scrollWidth > clientWidth + 1` non
  volontairement scrollable, et tout texte dont la box sort de l'encart
  parent (ex. connu : textarea « Action à animer » du Sprite Lab) ;
- scan alignements : rangées de réglages `.grid2`/toolbars, tops alignés ±2 px ;
- sortie JSON + screenshots annotés ; boucle mesurer→corriger jusqu'à 0.
Le harnais reste dans le repo (recette re-jouable à chaque chantier UI).

## 6. Recette globale

1. Screenshots avant/après sur 5 vues : plus aucun dock, canvas pleine
   hauteur.
2. Job réel gratuit lancé → badge « 1 » + pulse visibles topbar, panneau
   s'ouvre avec la card live, se ferme à Esc (captures).
3. `qa-shell-audit.js` = 0 débordement, 0 désalignement (JSON en preuve).
4. Bug vignettes : repro rouge avant fix, verte après, assertion au harnais.
5. Non-régression : qa-previz-restore 8/8, qa-tilelab 14/14.
6. Déploiement backups `.bak_shellqueue`/`.bak_11*` + restart + health OK.

## 7. Hors périmètre

Node Studio interne, Scheduler, refonte des vues elles-mêmes (contenu),
backend (zéro endpoint modifié), mobile.
