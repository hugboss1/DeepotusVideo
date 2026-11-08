# Vectorlab — lot D1 « Tracés » (plan, 08/11/2026)

> **Spec** : `docs/superpowers/specs/2026-11-08-illustrator-vectorlab-inventaire.md` (décision D1, validée par
> l'utilisateur le 08/11). **Branche** : `claude/vectorlab-d1-traces`, partie d'origin/main 076690cb. **Une PR pour le
> lot**, un commit par tâche.
>
> **But** : donner au Vectorlab les commandes de tracé d'Illustrator qui lui manquent. Ce sont des commandes de pure
> géométrie, testables en banc node, utiles d'abord pour les cartes et les plateaux.

## Contrats du dépôt à respecter (relevés dans le code)

- **Opérations pures** `op_*(doc, …)`. Tout se calcule AVANT de muter : un refus ne laisse aucune trace (règle de
  `mod-bool.js`). L'UI les appelle par `VL.executer(op, …)`, ce qui donne l'annulation pour rien.
- **Géométrie** :
  - `aplatir_objet` / `polylignes_objet` : tolérance 0,25 px, transform appliqué ;
  - `_versMulti`, `_dDeMulti`, `_dDePoly` ; martinez par `_martinez()` (`union`, `diff`, `intersection`, `xor`) ;
  - `chemin_parser` / `chemin_serialiser` (`mod-doc.js`) : commandes absolues M L C Q Z seulement.
- **Menus** : `MENUS_BARRE` (`mod-menus.js`), actions résolues par `resoudre` (`mod-charpente.js`), qui donne le
  grisage par `peut()`.
  - Les booléens passent par `bool:<mode>` → `VL.actions.selection.booleen` (`mod-style.js`).
  - Les nœuds passent par `noeuds:<arg>`.
- **Libellés** : FR + EN dans `frontend/shared/i18n/vectorlab.json`, lus par `T(...)` ; jamais une chaîne en dur.
- **Icônes** : `mod-icones.js`, règles de DESIGN.md §15. Phrases d'aide : `VL.hints`.
- **Bancs** : `frontend/vectorlab/qa/*.test.mjs`, lancés par `node qa/run.mjs` ; martinez y est injecté par
  `fournirMartinez`.

## Nouveau module

`js/mod-traces.js` porte toutes les opérations du lot. `mod-bool.js` (579 lignes) garde les booléens existants et
**exporte** les aides dont D1 a besoin : `_contourEnMulti` → `contour_en_multi` existe déjà ; à exporter en plus :
`multi_vers_d` (`_dDeMulti`), `ciblesOrdonnees` (`_ciblesOrdonnees`), `martinez()`. Aucune copie de code.

Banc : `qa/traces.test.mjs`, écrit **rouge d'abord** à chaque tâche.

## Tâches

### T1 — Vectoriser le contour (Objet › Tracé › Vectoriser le contour)

- `op_contour_vectoriser(doc, ids) → ids`. Pour chaque objet à contour (`style.contour` ≠ none, `epaisseur` > 0) :
  - `contour_en_multi(objet)` donne un chemin plein, `fond` = l'ancienne couleur du contour, sans contour ;
  - si l'objet avait un fond, il reste à sa place sans contour, et l'objet vectorisé est posé juste au-dessus. Les deux
    sont groupés (`op_grouper`), comme le fait Illustrator ;
  - objet sans contour : refus traduit `vectorlab.traces.sans_contour`.
- **Écart assumé** : jointures et extrémités rondes seulement (c'est ce que `_contourEnMulti` construit). Les styles
  `joint` biseau ou angle viendront plus tard, en ligne de suivi.
- Banc :
  - carré 100 non rempli, épaisseur 10 → aire = 4 × 100 × 10 + π·5² (± 0,5 %) ;
  - ligne ouverte → un seul anneau ;
  - objet rempli → groupe de 2 ;
  - refus sans contour ; annulation intacte (JSON identique après échec).

### T2 — Simplifier (Objet › Tracé › Simplifier…)

- `op_simplifier(doc, ids, { precision, droites })`, sur `path` (les formes passent d'abord par `op_forme_en_chemin`).
  Pour chaque sous-chemin :
  - `polylignes_objet`, puis `simplifier` RDP de `mod-crayon.js` avec une tolérance tirée de `precision` (0-100 %,
    100 = original) ;
  - puis `lisser_vers_d` (déjà dans `mod-crayon.js`), ou des segments droits si `droites`.
- Dialogue maison (`VL.dialogue`) : curseur de précision avec **aperçu en direct** (le nombre de points avant → après
  est affiché, comme Illustrator) et une case « Lignes droites ».
- Banc :
  - cercle en polyligne de 200 points → ≤ 12 ancres, aire ± 1 % ;
  - carré à 4 angles → reste 4 angles avec `droites` ;
  - precision 100 → d inchangé ;
  - sous-chemins multiples conservés.

### T3 — Ajouter des points d'ancrage / Supprimer des points d'ancrage

- `op_points_ajouter(doc, ids)` : un point au milieu de CHAQUE segment, en réutilisant `op_noeud_inserer(…, 0.5)` du
  dernier segment au premier, pour que les indices restent valides. Les formes sont converties en chemin d'abord.
- « Supprimer des points » : entrée de menu sur la sélection de nœuds (`noeuds:supprimer`), branchée sur l'existant
  `op_noeud_supprimer`. Grisée sans nœud sélectionné.
- Banc :
  - carré de 4 segments → 8 ancres ;
  - forme identique (aire inchangée, chaque point neuf sur son segment) ;
  - cubique coupée en t = 0,5 → la courbe passe par le point neuf.

### T4 — Moyenne (Objet › Tracé › Moyenne…)

- `op_noeuds_aligner` fait déjà la moyenne sur UN axe, dans UN chemin. Ajouter :
  - le mode `deux` (les deux axes à la fois) ;
  - une entrée de menu « Moyenne… », avec un dialogue à 3 choix (Horizontale / Verticale / Les deux).
- Banc : 3 nœuds → tous au barycentre en mode `deux` ; un seul nœud → refus existant `err_aligner`.
- La moyenne sur plusieurs chemins à la fois sort du lot (le modèle de sélection de nœuds est par chemin). C'est
  noté en suivi.

### T5 — Nettoyer (Objet › Tracé › Nettoyer…)

- `op_nettoyer(doc, { isoles, invisibles, textesVides }) → { isoles: n, invisibles: n, textesVides: n }` :
  - points isolés = `path` réduit à un `M` sans segment ;
  - invisibles = fond none ET (contour none ou épaisseur 0), hors groupes et masques ;
  - textes vides = texte sans caractère non blanc ;
  - les calques verrouillés sont ignorés.
- Dialogue à 3 cases, puis un toast « n objets supprimés » ; si rien n'est trouvé, toast « Rien à nettoyer » et aucune
  écriture dans l'historique.
- Banc : un document semé des trois cas, plus des objets légitimes → seuls les bons partent ; calque verrouillé
  intact ; compte exact.

### T6 — Diviser les objets en dessous

- `op_diviser_dessous(doc, idCouteau) → ids` :
  - le chemin du dessus (fermé : son aire ; ouvert : son contour, comme `op_division`) découpe chaque objet NON
    verrouillé situé SOUS lui et qui l'intersecte ;
  - chaque morceau garde le style de son objet d'origine, puis le couteau est supprimé.
- Réutiliser le cœur de `op_division` : extraire `_decouper(plaqueMp, cutMp)` dans `mod-bool.js`, appelé par les deux.
- Banc :
  - cercle posé sur 2 rectangles → 4 morceaux ;
  - objet non touché intact ;
  - objet verrouillé intact ;
  - couteau supprimé.

### T7 — Lignes et colonnes… (Objet › Tracé)

- `op_lignes_colonnes(doc, id, { lignes, colonnes, gouttiereH, gouttiereV, reperes })` : la bbox de l'objet est
  découpée en `lignes × colonnes` rectangles séparés par des gouttières, au style de l'objet ; l'objet source est
  supprimé. Avec `reperes`, des repères sont ajoutés sur les bords (`op_guide_ajouter`).
- Dialogue avec aperçu. C'est directement utile pour les planches de cartes.
- Banc :
  - 100 × 100, 2 × 2, gouttière 10 → 4 rectangles de 45 × 45 aux bonnes positions ;
  - 1 × 1 → un rectangle identique ;
  - gouttière trop grande → refus traduit.

### T8 — Pathfinder complet

- Ajouter à `op_booleen` / `mod-traces.js` :
  - **exclusion** : martinez `xor` en cascade ;
  - **soustraction arrière** : le plus HAUT moins tous ceux du dessous ;
  - **découpage** : chaque objet moins l'union de tous ceux du dessus, sans fusion ; les contours sont retirés,
    comme dans Illustrator ;
  - **fusion** : découpage, puis union des morceaux de même `fond` ;
  - **recadrage** : chaque objet du dessous ∩ le plus haut ; le plus haut est supprimé ;
  - **contour** : division, puis chaque arête devient un chemin ouvert, sans fond, contour = l'ancien fond.
- Ajouter **« Répéter le dernier Pathfinder »** (raccourci Ctrl+4, comme Illustrator), à vérifier libre dans
  `mod-menus.js`.
- Banc, avec deux carrés 100 qui se chevauchent de 50 :
  - exclusion : aire 10 000 ;
  - soustraction arrière : 5 000 ;
  - découpage : 2 objets, aires 5 000 + 10 000 ;
  - fusion de même couleur : 1 objet de 15 000 ;
  - recadrage : 5 000 ;
  - contour : uniquement des chemins ouverts sans fond.
  - Plus : moins de 2 objets → refus ; échec → aucune mutation.

### T9 — Câblage UI (une seule fois, après T1-T8)

- `mod-menus.js`, menu Vecteur :
  - un bloc « Tracé » après « joindre / inverser / diviser / coins » : Vectoriser le contour, Simplifier…, Ajouter des
    points, Supprimer des points, Moyenne…, Nettoyer…, Diviser les objets en dessous, Lignes et colonnes… ;
  - le bloc booléen passe de 4 à 10 entrées, plus « Répéter le dernier Pathfinder ».
- `mod-charpente.js` : chaque action avec son `peut()` exact (≥ 1 objet à contour, ≥ 2 objets, nœuds sélectionnés,
  document ouvert).
- `mod-flyout.js` : le flyout Sélection reçoit les 6 booléens neufs. Les icônes suivent DESIGN.md §15 (pas d'emoji).
- `VL.hints` : une phrase par commande.
- Clés i18n FR + EN, plus l'aide F1, qui se construit seule depuis les menus.
- Banc : `qa/menus` (ou celui qui garde MENUS_BARRE) mis à jour ; `peut()` vérifié pour chaque entrée neuve.

### T10 — Connaissance, aide, guide

- Skill `connaissance-agent` : fiches catalogue FR/EN des entrées neuves, puis `catalogue.py --check` vert.
- Skill `didacticiel-option` : une fiche animée par commande neuve (8 + Pathfinder), d'après de vraies captures sur le
  backend de preuve 8799.
- Skill `guide-deepotus` : un paragraphe « Tracés » au chapitre Vectorlab du guide.

### T11 — Preuve et livraison

- `node qa/run.mjs` vert en entier, plus les bancs Python touchés (i18n, catalogue).
- Preuve à l'écran sur une instance isolée 8799, avec une capture par commande, d'abord en FR puis en EN.
- PR unique. **Installation dans %LOCALAPPDATA% seulement sur accord de l'utilisateur**, selon la procédure
  « Déploiement vers %LOCALAPPDATA% : vérifier » (git hash-object, pré-vol).

## Hors lot (lignes de suivi)

- Jointures biseau / angle et extrémités carrées dans Vectoriser le contour.
- Moyenne sur des nœuds de plusieurs chemins.
- Pathfinder vivant (en effet).
- « Contour de l'objet » en effet.
