# Vectorlab — lot D3 « Déformer » (plan, 08/11/2026)

> **Spec** : `docs/superpowers/specs/2026-11-08-illustrator-vectorlab-inventaire.md`, décision D3. L'utilisateur a demandé
> d'enchaîner les lots après D2 (« puis enchaîne sur les lots suivants », 08/11). **Branche** :
> `claude/vectorlab-d3-deformer`, tirée d'origin/main 2ba171f3. **Une PR pour le lot**, un commit par tâche.
> **Suivi** : t460-t468.
>
> **But** : les déformations d'Illustrator, en objets VIVANTS comme les répétitions de D2 :
> - Enveloppe par déformation prédéfinie, avec les 15 styles ;
> - Distorsion libre ;
> - Torsion ;
> - Rugosité ;
> - Zigzag ;
> - Contraction et dilatation ;
> - Pointes de flèche.

## Le modèle (repris de D2)

Une déformation est un **groupe qui porte sa recette** : `{ deformation: { effet, params, edition?, empreinte },
enfants: [source, ...résultat] }`.

- **Le résultat**
  - Ce sont un ou plusieurs chemins générés (`genere: true`, ids `<groupe>_d<k>`), en coordonnées du document.
  - Il est stocké : l'export, l'impression et les versions anciennes le voient.
- **La source**
  - Elle reste l'objet d'origine, intact, mais elle est **cachée** (`cache: true`) tant qu'on n'est pas en
    « Modifier le contenu ».
  - C'est la première édition de base du lot : le rendu de `mod-doc.js` saute un objet `cache`, et les booléens de
    `mod-bool.js` aussi.
- **Modifier le contenu** (`op_deformation_editer`, comme « Modifier le contenu » d'une enveloppe d'Illustrator)
  - La source redevient visible et le résultat est caché ; on modifie la source par Ctrl+clic.
  - Refaire la commande revient au résultat, recalculé.
- **Recalcul**
  - Il se fait par empreinte (source et réglages), comme les répétitions, dans `deformations_rafraichir`
    (`mod-deformer.js`), appelée à la fin de `vivants_d2_rafraichir` (`mod-repeter.js`, module neuf) : aucune
    nouvelle édition de `mod-vivants.js`. Seule la condition de Décomposer (`op_derive_detacher`), portée par l'entrée
    S de `t450.py`, est étendue à `o.deformation`.
  - (FAIT, T1) Pendant « Modifier le contenu », le recalcul continue mais le résultat reste caché.
  - Un recalcul impossible garde le dernier état.
- **Décomposer**
  - Il ne reste que le résultat, en chemins ordinaires ; la source part.
  - **Annuler la déformation** fait l'inverse : il ne reste que la source, visible.
- **Géométrie commune**
  - La source est aplatie (`polylignes_objet`), puis subdivisée pour qu'aucun segment ne dépasse 2 px : une ligne
    droite peut ainsi se courber.
  - Chaque point est transformé, puis le chemin est réécrit (fermé si la source l'était).
  - Le style de la source est recopié sur le résultat.

## Tâches

### T1 (t460) — Le modèle vivant et l'Enveloppe (15 styles)

- `mod-deformer.js` (neuf), qui couvre :
  - `op_deformer(doc, ids, "enveloppe", params) → id` ;
  - `op_deformation_regler` ;
  - `op_deformation_editer` ;
  - `op_deformation_annuler` ;
  - le recalcul.
- Les éditions de base :
  - `cache` respecté par le rendu et par les booléens ;
  - Décomposer par `op_derive_detacher`.
- **Enveloppe** : chaque point est d'abord ramené à des coordonnées normalisées (u, v) dans la boîte de la source.
  - Les 15 styles sont des fonctions de déplacement : arc, arc inférieur, arc supérieur, arche, renflement,
    coquille inférieure, coquille supérieure, drapeau, vague, poisson, montée, œil de poisson, gonflement,
    pression, torsion.
  - Leurs réglages sont ceux d'Illustrator : courbure de −100 à 100 %, orientation horizontale ou verticale,
    distorsion horizontale et verticale de −100 à 100 %.
- Banc :
  - courbure 0 → la forme est inchangée (aire ± 0,5 %) ;
  - Arc 50 % sur un rectangle → les bords haut et bas deviennent des arcs, les coins restent en place ;
  - Arche : le bas ne bouge pas ;
  - Gonflement : le centre gonfle, les coins restent ;
  - orientation verticale = horizontale tournée de 90° ;
  - distorsion H → la forme passe d'un rectangle à un trapèze ;
  - vivant (la source change → le résultat suit) ;
  - Modifier le contenu : source visible et résultat caché, puis l'inverse ;
  - Décomposer et Annuler ;
  - refus sans trace ;
  - export SVG sans la source cachée.

### T2 (t461) — Distorsion libre et Torsion

- **Distorsion libre** : les quatre coins de la boîte sont déplacés (`coins: [[dx, dy] × 4]`), puis chaque point suit
  une interpolation bilinéaire. Coins à zéro → identité.
- **Torsion** : `angle`. Chaque point tourne autour du centre d'un angle proportionnel à sa distance au centre
  (0 au centre, `angle` au plus loin), comme l'effet d'Illustrator.
- Banc :
  - identités ;
  - un coin tiré → le sommet correspondant suit exactement ;
  - torsion de 90° → le point le plus loin a tourné de 90° ;
  - le centre ne bouge pas.

### T3 (t462) — Rugosité et Zigzag

- **Rugosité** :
  - `taille` (px), `details` (points par 100 px), `lisse` (sinon pointes) ;
  - `graine`, pour un résultat stable : le même document donne le même dessin à chaque recalcul.
- **Zigzag** : `taille` (px), `cretes` (par segment d'origine), `lisse`. Le déplacement alterne de part et d'autre du
  tracé, selon sa normale.
- Banc :
  - même graine → même tracé ;
  - aucun point ne s'écarte de plus de `taille` ;
  - le nombre de crêtes est juste ;
  - `lisse` donne des courbes (C), sinon des droites (L).

### T4 (t463) — Contraction et dilatation

- Sur les ancres du chemin (`chemin_parser`, les L passés en C) : pour un pourcentage p, les ancres s'éloignent du
  centre de p % et les poignées s'en rapprochent de p %. Au signe opposé, c'est l'inverse, comme Illustrator.
- Banc :
  - 0 % → identité ;
  - dilatation → l'aire augmente et les ancres s'éloignent ;
  - contraction → l'aire baisse ;
  - le nombre d'ancres est gardé.

### T5 (t464) — Pointes de flèche

- Sur un chemin OUVERT, avec des réglages par bout :
  - `debut` et `fin`, chacun parmi aucune, triangle, flèche ouverte, cercle, carré, barre ;
  - `echelle` en %, proportionnelle à l'épaisseur du trait.
- Les pointes sont des formes générées, orientées selon la tangente du bout, et le trait est raccourci de leur
  longueur, comme Illustrator.
- (FAIT) Même modèle que les autres effets, plutôt qu'une source visible : la source est cachée, et le résultat est
  le trait raccourci plus les pointes. « Modifier le contenu » marche donc aussi pour les flèches. Tailles : triangle
  3 × 2,5 épaisseurs (le trait raccourci de 3), cercle de rayon 1,5, carré de côté 3, barre de 4, flèche ouverte au
  trait ; le tout × échelle.
- Banc :
  - orientation au bout ;
  - taille proportionnelle à l'épaisseur ;
  - refus sur un chemin fermé ;
  - la source modifiée → les pointes suivent.

### T6 (t465) — Copies protégées et câblage UI

- **Menu Vecteur**, bloc « Déformer » :
  - Enveloppe…, Distorsion libre…, Torsion…, Rugosité…, Zigzag…, Contraction et dilatation…, Pointes de flèche… ;
  - Modifier le contenu, Options de déformation…, Annuler la déformation (ou Décomposer, qui sert déjà à D2).
- Dialogues pré-remplis avec aperçu en direct (formulaire de D2) ; Apparence : la recette, Options…, Modifier le
  contenu, Décomposer.
- Clés FR/EN `vectorlab.deformer.*`. Le Ctrl+clic et `_objetsCibles` protègent déjà les objets `genere`.
- Banc `qa/deformerui.test.mjs`.

### T7 (t466) — Poignées de la Distorsion libre

- Les quatre coins sont tirables sur la toile, comme les poignées de D2 : aperçu en direct, une seule étape
  d'annulation par geste.
- Banc et preuve au vrai glisser.

### T8 (t467) — Connaissance et guide

- Fiches de catalogue de l'assistant pour les entrées neuves (skill `connaissance-agent`).
- Carte « Déformer » au chapitre Vectorlab du guide, FR et EN (skill `guide-deepotus`).

### T9 (t468) — Preuve et livraison (FAIT)

- `origin/main` (chantier Méthodes t443b) fusionnée sans conflit ; guide, L6 et catalogue relancés : rien ne change.
- Bancs : `node qa/run.mjs` vert ; `test_i18n_l6` 24, `test_icones_g3_vectorlab` 18, agent 117 + 12 + 23 + 21,
  `test_guide_v3` 494, `test_vectorlab_guide_devis` 17. Mutants : T1 37/37, T2 14/14, T3 19/19, T4 9/9, T5 20/20,
  T6 18/18, T7 13/13.
- Preuve 8799 (FR puis EN) :
  - au vrai clic et clavier : menu Vecteur › Enveloppe… (15 styles, aperçu), Drapeau à 60 % appliqué ;
  - Apparence « Déformation vivante » : Modifier le contenu (l'original revient, le bouton dit « Terminer »),
    original élargi, Terminer → résultat recalculé à 330 px ;
  - Distorsion libre, puis le coin haut-gauche tiré au vrai glisser (≈ −40, −30) ;
  - Pointes de flèche (cercle au début, triangle à la fin) et Contraction et dilatation −60 % validées à Entrée ;
  - export SVG valide : 5 tracés et 1 cercle, ni source cachée ni recette ;
  - enregistré puis rechargé : toujours vivant ;
  - Annuler la déformation au menu → la source revient ;
  - menu et Apparence en anglais.
- PR unique. Installation seulement sur accord.

## Hors lot

- Enveloppe par filet (mesh) et par objet du dessus.
- Perspective libre, et les effets de fluidité (Tourbillon, Festons, Cristallisation…).
- Pointes de flèche sur un chemin fermé.
