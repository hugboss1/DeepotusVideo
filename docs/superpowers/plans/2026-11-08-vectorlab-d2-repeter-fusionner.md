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
  - `lignes` et `colonnes` : 1-50 chacun, ≤ 200 copies au total ;
  - `pasX` et `pasY` : par défaut, la boîte de la source, sans espace ;
  - `decalage`, le type de grille d'Illustrator : `"aucun"`, `"brique_lignes"` (une ligne sur deux décalée de
    `pasX/2`) ou `"brique_colonnes"` ;
  - `miroirLignes` et `miroirColonnes` : une rangée sur deux retournée.
- **Pavage hexagonal** : `brique_colonnes` avec `pasX = 1,5 r` et `pasY = √3 r` pave sans jour un hexagone à
  sommet plat de rayon r. Un préréglage « Hexagones » du dialogue le pose à partir de la boîte de la source. C'est
  l'usage des plateaux.
- Banc :
  - grille 3 × 4 → 12 objets aux bons pas ;
  - brique : décalage d'une ligne sur deux ;
  - miroir alterné : `scale(-1 1)` sur les colonnes impaires ;
  - hexagones : 7 hexagones collés → aire de l'union = somme des aires (± 0,1 %), donc pas de recouvrement ni de jour ;
  - plus de 200 copies → refus.

### T3 (t452) — Répétition en miroir

- Mode `"miroir"` : la source plus sa réflexion par un **axe**.
  - L'axe est donné par `angle` (90° par défaut, donc vertical) et `ecart`, la distance de l'axe au bord droit de la
    source (0 par défaut, l'axe touche la source).
  - La copie est un `matrix(...)` de réflexion préfixé au transform de la source.
- Banc :
  - axe vertical à ecart 0 → copie collée, symétrique ;
  - axe à 45° → les points se correspondent par réflexion (± 0,01) ;
  - modifier la source → le reflet suit.

### T4 (t453) — Fusion : créer et interpoler

- `op_fusionner(doc, [idA, idB], { mode, etapes, pas })` → groupe `fusion_vive`. Il faut exactement deux objets (refus
  sinon). A est celui du dessous ; l'ordre de superposition est gardé.
- Trois modes, comme Illustrator :
  - `"etapes"` : 1-200 intermédiaires ;
  - `"distance"` : un intermédiaire tous les `pas` px entre les centres ;
  - `"couleur"` (couleur lissée) : assez d'étapes pour que deux voisins ne diffèrent pas de plus de 4 niveaux sur un
    canal, plafonnées à 200.
- **Interpolation de forme** :
  - A et B passent en polylignes (`polylignes_objet`, transform compris) ;
  - chaque sous-chemin est rééchantillonné à N points égaux en longueur (N = max des deux, au moins 32) ;
  - le point de départ et le sens de B sont alignés sur A, avec le décalage circulaire qui minimise la somme des
    distances (un sens inversé est essayé) ;
  - interpolation linéaire, puis `lisser_vers_d` (`mod-crayon.js`) ;
  - sous-chemins en nombre différent : les sous-chemins en trop se réduisent vers leur centre.
- **Interpolation de style** :
  - couleurs hex de `fond` et `contour` : interpolation en RVB ;
  - `epaisseur` et `opacite` : interpolation linéaire.
  - Un dégradé, un motif ou une couleur globale ne s'interpole pas : le style bascule à mi-chemin. C'est un **écart
    assumé**, dit dans le guide.
- Banc :
  - deux carrés, 3 étapes → 3 intermédiaires équidistants, aires interpolées ;
  - carré → cercle : le milieu a une aire intermédiaire et aucun auto-croisement ;
  - rouge → bleu → le milieu vaut #800080 (± 1) ;
  - mode distance : 300 px avec un pas de 50 → 5 intermédiaires ;
  - mode couleur : #000 → #fff → 63 étapes ;
  - modifier A → les intermédiaires suivent ;
  - un seul objet → refus ; échec → aucune mutation.

### T5 (t454) — Fusion : trajectoire, inversions, options

- `op_fusion_regler(doc, id, opts)` change mode, étapes ou pas.
- `op_fusion_trajectoire(doc, idFusion, idChemin)` : « Remplacer la trajectoire ».
  - Les centres de A, des intermédiaires et de B sont posés à intervalles égaux en longueur le long du chemin.
  - Le chemin devient un enfant source de la fusion, non rendu par défaut, comme la trajectoire d'Illustrator. Il
    reste éditable par Ctrl+clic, et les intermédiaires suivent.
- `op_fusion_inverser_trajectoire` (A ↔ B sur la trajectoire) et `op_fusion_inverser_ordre` (la superposition).
- Option **« Orienter selon la trajectoire »** : chaque intermédiaire tourne selon la tangente.
- Banc :
  - trajectoire en arc → les centres sont sur l'arc à pas égaux ;
  - les deux inversions changent ce qu'elles doivent, et rien d'autre ;
  - éditer le chemin → les intermédiaires suivent ;
  - décomposer → groupe ordinaire avec la trajectoire visible.

### T6 (t455) — Copies protégées et câblage UI

- **Protection** :
  - l'itérateur des cibles (R11) saute les enfants `genere` ;
  - un clic sur une copie sélectionne le groupe vivant ;
  - les ops qui reçoivent un id généré refusent.
  - Ces règles ont leur banc.
- **Menus** (`mod-menus.js`), menu Objet :
  - bloc « Répétition » : Radiale, Grille, Miroir, Options de répétition…, Décomposer ;
  - bloc « Fusion » : Créer (**Ctrl+Alt+B**, raccourci à vérifier libre), Options de fusion…, Annuler la fusion,
    Décomposer, Remplacer la trajectoire, Inverser la trajectoire, Inverser l'ordre.
  - Chaque entrée a son `peut()` exact dans `mod-charpente.js`. « Annuler la fusion » rend A et B seuls.
- **Dialogues** (`VL.demander`, sur le modèle de `mod-tracesui.js`) :
  - Options de répétition : réglages du mode, préréglage « Hexagones » ;
  - Options de fusion : mode, étapes ou pas, orienter.
  - Tous les deux ont un **aperçu en direct** sur le document : chaque changement passe par l'op de réglage, et
    Annuler revient en arrière.
- **Onglet Apparence**, section « vivant » :
  - un objet répété ou fondu y montre sa recette en une ligne, avec un bouton « Options… » et le bouton
    « Détacher » existant (qui décompose) ;
  - c'est une édition de base, consignée dans `t450.py`.
- Clés FR/EN `vectorlab.repeter.*` et `vectorlab.fusion.*`. Les phrases d'aide de la barre d'état ne s'appliquent
  pas : elles décrivent les outils, pas les commandes, comme décidé en D1.
- Banc `qa/repeterui.test.mjs`, avec un VL factice comme `tracesui` : grisage, appels, annulation d'un dialogue,
  libellés traduits.

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
