# Vectorlab — lot D2 « Répéter et fusionner » (plan, 08/11/2026)

> **Spec** : `docs/superpowers/specs/2026-11-08-illustrator-vectorlab-inventaire.md`, décision D2, choisie par
> l'utilisateur le 08/11. **Branche** : `claude/vectorlab-d2-repeter`, tirée d'origin/main 70307bbe. **Une PR pour le
> lot**, un commit par tâche. **Suivi** : t450-t458. Les numéros t433-t443 sont réservés au chantier Méthodes.
>
> **But** : donner au Vectorlab les deux objets vivants d'Illustrator qui lui manquent :
> - la **Répétition**, en trois modes : radiale, grille, miroir ;
> - la **Fusion** (blend) entre deux formes.
>
> Les deux servent d'abord les ornements de cartes, les rosaces et les plateaux hexagonaux.

## Ce qui existe déjà (relevé dans le code d'origin/main)

- **Objets vivants** (`mod-vivants.js`, t123). `derives_rafraichir(doc)` passe après CHAQUE commande dans
  `core.executer`, sur le même clone. Un dérivé garde le lien vers sa source et l'**empreinte** JSON de celle-ci. Seule
  une empreinte changée coûte un recalcul. Une source disparue laisse le dérivé à son dernier état, jamais d'exception.
  Conséquence : un Ctrl+Z défait ensemble la source et son dérivé. D2 suit le même modèle.
- `op_derive_detacher(doc, id)` rend un dérivé ordinaire. Il porte le bouton « Détacher » de l'onglet Apparence
  (section « vivant », `mod-apparence2.js`).
- **Groupes** :
  - `op_grouper` et `op_degrouper` (`mod-doc.js`) ;
  - les enfants sont des cibles à part entière par Ctrl+clic (R11, itérateur des cibles de `mod-doc.js`).
- **Transformations** : `transform` est une chaîne SVG composée par préfixe (`op_tourner` écrit
  `rotate(a cx cy) <ancien>`). `polylignes_objet` (`mod-bool.js`) l'applique déjà.
- **Ids** : `idLibre` donne `o<n>`. `_bboxObjet` (`mod-doc.js`) donne la boîte géométrique sans DOM ; il est à
  exporter, pas à recopier.
- **Ce que nous avons et qui n'est PAS vivant** : `op_dupliquer_puissance` (n copies figées) et `op_miroir` (miroir
  ponctuel). Ils restent tels quels.
- `parserDoc` tolère les clés inconnues d'un objet : `derive` y passe déjà. Un document D2 s'ouvre donc dans une
  version plus ancienne, qui montre les copies comme un groupe ordinaire. Il n'y a rien à migrer.

## Le modèle des deux objets vivants

Un objet vivant D2 est un **groupe** qui porte sa recette. Ses enfants sont de deux sortes :

- les **sources**, qui restent éditables par Ctrl+clic ;
- les **copies générées**, marquées `genere: true`, avec des ids `<idGroupe>_r<k>` (répétition) et `<idGroupe>_f<k>`
  (fusion). Ces ids ne recroisent jamais `o<n>`.

```
répétition : { type: "groupe", repetition: { mode, params, empreinte }, enfants: [source, ...copies] }
fusion     : { type: "groupe", fusion_vive: { mode, etapes|pas, trajectoire?, inverse?, empreinte },
               enfants: [A, ...intermédiaires, B] }
```

**Copies stockées, pas calculées au rendu.** C'est pour que l'export SVG/PDF, l'impression, les tranches, le
serveur et les versions anciennes les voient sans rien changer. Plafond : 200 copies, comme la duplication puissance.

**Recalcul.** Un nouveau module `mod-repeter.js` exporte `vivants_d2_rafraichir(doc)`. `derives_rafraichir` l'appelle,
et c'est la seule édition de base de `mod-vivants.js`, consignée dans `scripts/i18n_l6/t450.py`. L'empreinte couvre
la source (ou A et B) **et** les réglages. Changer un réglage passe donc par une op qui réécrit `params`, et le
recalcul suit tout seul.

**Copies protégées** :
- une copie générée n'est jamais une cible : le Ctrl+clic la saute, et sélectionner le groupe le sélectionne entier ;
- les ops qui visent un id généré refusent, avec la clé traduite `vectorlab.repeter.copie_generee`.

**Décomposer.** `op_derive_detacher` apprend les deux recettes. Il retire la recette et les marques `genere`. Il reste
un groupe ordinaire, dont les copies reçoivent des ids `o<n>` neufs (`_idLibre`), comme dans Illustrator.

## Tâches

### T1 (t450) — Répétition : le modèle, et le mode radial

- `mod-repeter.js` :
  - `op_repeter(doc, ids, "radiale", params) → id du groupe`. Plusieurs objets sélectionnés sont d'abord groupés en
    une seule source.
  - Réglages radiaux :
    - `nombre` : 2-100, 8 par défaut ;
    - `rayon` : par défaut, la demi-diagonale de la source ;
    - `orienter` : vrai par défaut. Faux veut dire que chaque copie reste droite et ne fait que se déplacer.
  - Le centre de la rosace est à `rayon` SOUS le centre de la source : la source est en haut du cercle, comme dans
    Illustrator. Pas d'angle de départ (Illustrator n'en a pas) : tourner le groupe entier suffit.
- `vivants_d2_rafraichir`, `op_repetition_regler(doc, id, params)`, et l'extension d'`op_derive_detacher`.
- **Fait au passage** (édition de base dans `t450.py`) : la matrice des booléens (`_matriceDe`, `mod-bool.js`) ne lisait
  que `rotate`. Elle lit maintenant toute la liste SVG (translate, scale, rotate, skewX, skewY, matrix) ; un objet
  incliné était aplati sans son inclinaison.
- Banc `qa/repeter.test.mjs`, **rouge d'abord** :
  - les 8 copies sont à 45° d'écart, sur un cercle de rayon r (± 0,01) ;
  - modifier la source par une op → les copies suivent dans la même étape, et l'annulation rend le document identique ;
  - régler le nombre de 8 à 12 → 12 enfants ;
  - aucun recalcul quand l'empreinte est inchangée ;
  - décomposer → groupe ordinaire, ids `o<n>`, plus de recette ;
  - nombre hors bornes → refus sans mutation ;
  - source supprimée → le groupe reste à son dernier état, sans exception.
- Mutants : la procédure de D1, par fichier JSON.

### T2 (t451) — Répétition en grille, dont les pavages en brique et en hexagone

- Mode `"grille"` :
  - `lignes` et `colonnes` : 1-50 chacun, 3 × 3 par défaut, au moins 2 cases, ≤ 200 au total ;
  - `ecartX` et `ecartY` : l'espace entre deux cases, 0 par défaut, négatif pour un recouvrement. Le pas vaut la
    boîte **courante** de la source plus l'écart : il se relit à chaque recalcul, donc une source agrandie ne se
    recouvre pas. (Le plan disait `pasX` / `pasY` fixes : ils auraient cassé le pavage dès que la source change.)
  - `decalage` : `"aucun"`, `"brique_lignes"` (une ligne sur deux décalée d'un demi-pas), `"brique_colonnes"` ou
    `"hexagones"` ;
  - `miroirLignes` et `miroirColonnes` : une rangée sur deux retournée autour du centre de la source.
- **Pavage hexagonal** (`decalage: "hexagones"`), lu sur la boîte de la source :
  - plus large que haute (sommet plat) : les colonnes se recouvrent d'un quart (pas = 0,75 × largeur), une colonne
    sur deux descend d'un demi-pas ;
  - plus haute que large (en pointe) : même chose avec les lignes.
  - L'écart s'ajoute (plateau à joints). Les transformations sont écrites au millionième : arrondi au centième,
    le pas √3 r ouvrirait un jour d'un millième de pixel par rangée.
- Banc (fait) :
  - grille 3 × 4 → 12 objets aux bons pas, ordre ligne par ligne ; la source s'élargit → le pas suit ;
  - écarts positifs et négatifs ; briques par lignes et par colonnes ;
  - miroirs sur un triangle rectangle (sommets relus), lignes, colonnes, et les deux ;
  - hexagones à plat et en pointe, 3 × 3 : aire de l'union = somme (± 0,1 %) ET un seul polygone sans trou ;
  - refus traduits : 0 ligne, 51 colonnes, 1 × 1, 15 × 15, décalage inconnu, écart qui annule le pas, écart non
    numérique ; aucune trace.

### T3 (t452) — Répétition en miroir

- Mode `"miroir"` : la source plus sa réflexion par un **axe**.
  - `angle` : la direction de l'axe en degrés, 90° par défaut (vertical), ramenée dans [0, 360). La normale de
    l'axe (angle − 90°) pointe hors de la source : à 90° vers la droite, à 0° vers le haut, à 270° vers la gauche.
  - `ecart` : 0 par défaut. L'axe passe par la plus grande avancée de la source le long de la normale (le bord, pas
    la boîte : exact à 45°), plus l'écart. Le reflet est donc collé à la source, comme dans Illustrator.
  - La copie est un `matrix(...)` de réflexion préfixé au transform de la source ; l'axe se relit à chaque recalcul.
- Banc (fait) : axe vertical collé (sommets relus), écart 10, axe horizontal, axe à 45° (chaque sommet a son
  reflet, du bon côté), source élargie → l'axe suit, source réduite à un point → reflet gardé, régler, angles 450°
  et −90°, refus traduits sans trace.

### T4 (t453) — Fusion : créer et interpoler (FAIT)

- `op_fusionner(doc, [idA, idB], { mode, etapes, pas })`, dans `mod-repeter.js` (un seul module pour le lot) → groupe
  `fusion_vive: { mode, etapes, pas, empreinte }`. Exactement deux rectangles, ellipses, formes ou tracés du premier
  niveau d'un calque déverrouillé ; le groupe prend la place du plus haut. Intermédiaires `<groupe>_f<k>`, chemins
  en coordonnées du document.
- Modes : `etapes` (1-200, 5 par défaut), `distance` (un intermédiaire tous les `pas` px entre les centres, 20 par
  défaut), `couleur` (deux voisins ne diffèrent pas de plus de 4 niveaux sur un canal de fond ou de contour ; un
  seul intermédiaire si les couleurs sont égales). Toujours 1 à 200.
- **Forme** : sous-chemins appariés dans l'ordre. Mêmes nombres de sommets → sommets un à un (un carré reste un
  carré exact) ; sinon rééchantillonnage à N = max(32, sommets) points égaux en longueur, fermeture comprise.
  Fermé : B mis dans le sens de A (aire signée) puis tourné pour viser le plus proche ; ouvert : B retourné si
  c'est plus proche. Un sous-chemin sans partenaire naît de son propre centre (ou s'y réduit). Pas de lissage :
  les intermédiaires sont des polygones (un lissage arrondirait les angles d'un carré).
- **Style** : celui de A avant mi-chemin, de B ensuite ; `fond` et `contour` (#rgb ou #rrggbb) interpolés en RVB,
  `epaisseur` et `opacite` linéairement. Dégradé, motif, couleur globale : bascule à mi-chemin (écart assumé).
- Recalcul par empreinte (A, B, réglages) dans `vivants_d2_rafraichir` ; A ou B disparu → dernier état gardé.
  Décomposer : `op_derive_detacher` (entrée S de `t450.py` étendue à `fusion_vive`).
- Banc (fait) : places et ids, équidistance, aires, rouge → bleu = #800080, vivant sur A et sur B, décomposer,
  20 → 40 = 900, carré → cercle (aires décroissantes, sans auto-croisement), sens et départ opposés, sous-chemins en
  trop côté A et côté B, point de fermeture répété, 4 sommets contre 5, carré de 4 contre 8 points, chemins
  ouverts à rebours, style (dégradé, opacité, #000 et #f00 courts), modes distance / couleur / plafond 200 /
  défauts, refus traduits (1 ou 3 objets, texte, groupe, verrou, étapes, pas, mode, intermédiaire généré).
  40/41 mutants tués (le 41e équivalent).

### T5 (t454) — Fusion : trajectoire, inversions, options (FAIT)

- La recette identifie A et B par leurs ids (`fusion_vive.a`, `.b`) : l'ordre des enfants peut s'inverser. Chaque
  forme est CENTRÉE (sa boîte), interpolée, tournée si `orienter`, puis posée sur la trajectoire. Conséquence voulue :
  un sous-chemin sans partenaire suit le mouvement de la fusion (il garde sa place relative) au lieu de rester sur
  place — les attendus de T4 ont été corrigés en ce sens.
- `op_fusion_regler(doc, id, { mode, etapes, pas, orienter })` : les réglages absents restent.
- `op_fusion_trajectoire(doc, idFusion, idChemin)` — « Remplacer la trajectoire » : un tracé, une forme, un
  rectangle ou une ellipse du premier niveau, qui a une longueur, devient le premier enfant de la fusion,
  **invisible** (fond et contour `none`, son style gardé dans `styleTrajectoire` et rendu à la décomposition) et
  protégé de « Nettoyer » (`mod-traces.js`). A et B sont posés à ses deux bouts (un `translate` préfixé, seulement
  s'ils ont bougé : pas d'accumulation), les intermédiaires à pas égaux en longueur ; en mode distance, la longueur
  est celle du chemin. Une trajectoire déjà posée ne se remplace pas : refus « décomposez d'abord » (écart à
  Illustrator, qui remplace).
- `op_fusion_inverser_trajectoire` : avec un chemin, il se parcourt à rebours (`inverse`) ; sans, A et B échangent
  leurs places. `op_fusion_inverser_ordre` : B dessous, A dessus (`ordreInverse`), les intermédiaires à rebours.
- **Orienter** : chaque intermédiaire tourne de (tangente du chemin − direction A → B). Sur une droite rien ne tourne ;
  A et B gardent leur orientation (écart à Illustrator, qui les tourne aussi).
- Tout passe par un ESSAI (copies de A, B, trajectoire) : un recalcul qui échoue en route ne laisse rien à moitié
  posé. A, B ou la trajectoire supprimé → dernier état gardé.
- Banc (fait) : chemin en L (positions, invisibilité, style gardé, stabilité, pas d'accumulation, réglage hors op,
  chemin édité, deuxième trajectoire refusée, Nettoyer, décomposer), déplacement purement vertical, échec en route,
  trajectoire disparue, inversions avec et sans chemin, ordre (couleurs et places), orienter (angles, centres,
  aires), régler, refus traduits. 30/30 mutants tués ; jeux T1-T4 réajustés et repassés.

### T6 (t455) — Copies protégées et câblage UI (FAIT)

- **Protection** :
  - `_objetsCibles` (`mod-doc.js`) ne rend jamais une copie générée ni son intérieur : aucune opération ne la vise ;
  - un Ctrl+clic sur une copie (ou l'intérieur d'une copie, ou un intermédiaire) vise le groupe vivant le plus proche
    (`id_non_genere`, câblé dans `mod-tools.js`) ; la source reste ciblable. Un clic simple remontait déjà au sommet.
- **Menu Vecteur** (il n'y a pas de menu Objet au Vectorlab), après « Formes paramétriques… » : Répétition radiale…,
  en grille…, en miroir…, Options de répétition ou de fusion…, Décomposer (une entrée pour les deux) ; Créer une
  fusion (**Ctrl+Alt+B**, libre, écouté par `initRepeterUI` comme Ctrl+4), Options de fusion…, Annuler la fusion
  (`op_fusion_annuler` : A, B et la trajectoire visible reviennent à la place du groupe), Remplacer la trajectoire
  (une fusion + un chemin sélectionnés), Inverser la trajectoire, Inverser l'ordre de superposition. `peut()` exacts.
- **Dialogues** (`mod-repeterui.js`, formulaire de `mod-tracesui.js` exporté en `formulaire_dom` avec un `surChange`) :
  pré-remplis (`repetition_defauts`, ou la recette) ; **aperçu en direct** : chaque changement rejoue l'op sur une
  copie du document d'avant, sans historique ; Annuler / Échap rend le document d'avant ; Appliquer = UNE exécution.
- **Onglet Apparence** : section « Répétition vivante » / « Fusion vivante » avec la recette en une phrase, Options…
  et Décomposer (le bouton `a2Detacher` existant).
- Clés FR/EN `vectorlab.repeter.*` et `vectorlab.fusion.*` (`t455.py`), éditions de base positionnelles sur des
  fragments qui ne recouvrent aucun libellé traduit.
- **Écart** : la trajectoire d'une fusion est invisible, donc pas cliquable sur la toile ; pour la modifier, Annuler la
  fusion (elle redevient visible) ou Décomposer. Pas d'icônes pour les nouvelles entrées (glyphes à dessiner).
- Bancs : `qa/repeterui.test.mjs` (VL factice qui exécute vraiment : grisage, dialogues, aperçu, annulation, appels,
  Apparence, menus, Ctrl+Alt+B unique) 31/32 mutants (1 équivalent) ; briques moteur dans `qa/repeter.test.mjs`
  11/11. Preuve 8799 au vrai clic et clavier : menu Vecteur grisé, grille hexagonale 4 × 5 avec aperçu (historique
  vide pendant l'aperçu), Ctrl+clic sur une copie → le groupe, sur la source → la source, la source change → 20
  instances suivent, Ctrl+Alt+B, Remplacer la trajectoire au menu, Options… depuis Apparence avec aperçu 8 étapes
  puis Échap → 5, Ctrl+Z défait la trajectoire ; menus et Apparence en anglais.

### T7 (t456) — Poignées sur la toile (petite tâche, à confirmer en revue)

- Répétition radiale sélectionnée : une poignée de rayon et une poignée de nombre sur le cercle, comme les widgets
  d'Illustrator.
- Miroir : l'axe se glisse et se tourne.
- Glisser passe par `op_repetition_regler`, donc une seule étape d'annulation par geste.
- **Si le coût dépasse une journée, la tâche sort du lot** en ligne de suivi : le dialogue suffit à tout régler.

### T8 (t457) — Connaissance, guide

- Skill `connaissance-agent` : fiches FR/EN des entrées neuves, puis `catalogue.py --check` et les bancs agent verts.
- Skill `guide-deepotus` : cartes « Répétition » et « Fusion » au chapitre Vectorlab (FR/EN), qui disent les écarts
  (pas de dégradé interpolé, 200 copies au plus).
- Fiches didactiques animées : **non**, même décision qu'en D1 (l'encart ne vise que des boutons de panneau).

### T9 (t458) — Preuve et livraison

- `node qa/run.mjs` vert en entier, plus les bancs Python touchés (i18n L6, icônes G3, catalogue, guide).
- Preuve sur une instance isolée 8799 (config `preuve-vl-d1` du `.claude/launch.json` principal) :
  - rosace de 12, grille hexagonale 5 × 5, miroir ;
  - fusion carré → cercle sur un arc ;
  - éditer la source et voir suivre ;
  - Ctrl+Z ; décomposer ;
  - export SVG relu ;
  - FR puis EN.
- PR unique. **Installation dans %LOCALAPPDATA% seulement sur accord de l'utilisateur**, selon la procédure
  `git hash-object` + instantané `git archive` + sauvegarde.

## Hors lot (lignes de suivi)

- Interpolation des dégradés et des motifs dans la fusion.
- Fusion de plus de deux objets (A → B → C).
- Répétition le long d'un chemin quelconque : Illustrator ne la fait pas, mais une frise de carte en profiterait.
- Copies non stockées, calculées au rendu, si la taille des documents devient un problème.
