# Cardforge — phase 3c : le Sceau prismatique complet, le verso custom, l'IA cadres, les dettes

Dernière sous-phase de la phase 3. Contrat : spec §6.2bis a/b/d (:365-446),
§6.2ter (:448-464), §6.3 (:466-473) + les dettes héritées consignées
(2c N2/N4/N7, molette 2b, pagination /decks, GC images, banc
boutons-de-rangée, branche arcTo). Le volet c (3D iridescence) est LIVRÉ
depuis la 2b — cette phase le complète par la portée et les motifs.
Amender à la source (leçon ×10).

## Faits de reconnaissance (23/08, ancres vérifiées)

- **L'anneau de coupe est TOUJOURS `rrPath`** quelle que soit la famille
  (outerRing mod-frame.js:683-688, le filet :1675 — seule la FENÊTRE varie
  par WIN_SHAPE) → la vérité vectorielle du Sceau = un rectangle arrondi à
  `m.outer` + une largeur de bande : **portable en NOMBRES PURS**
  (x,y,w,h,r,width_mm), pas de bézier à porter en Python.
- **Table z GELÉE** : frame possède 40 (paintFront/Back) et 70 (paintTop) —
  AUCUN z neuf possible (core.js:504-508 le jette). Le peintre écran du
  Sceau s'insère dans paintFront, étape « 6. LES FILETS » (:1669-1686,
  même source de chemin que le filet externe). Isolation de sous-région
  pour l'export par couches : N'EXISTE PAS (only_z par bande entière,
  core.js:651-688) — la bande du Sceau partira DANS la couche « cadre ».
- **PRNG P2** : `prng(seed)` xorshift32 (:190), zéro Math.random ; les 3
  usages actuels = graines FIXES par famille/rareté — **JAMAIS par carte**.
  Le champ de paillettes du Sceau (« seed = id de carte ») est un patron
  NEUF ; paintFront reçoit `card` (lit .art/.back seulement — .i existe
  app-wide, print.py l'indexe).
- **doc.frame = 28 clés plates**, st() n'itère que Object.keys(DEFAULTS)
  (:195-226) — un sous-objet `seal` exige sa branche de validation imbriquée
  (patron winMM :233-245) + le miroir frame.py (parité /metrics-occupancy).
  LIMITS plat (:81-88 ↔ frame.py:129-139) ; largeur : la spec ne donne
  qu'un plancher (≥0,2 mm si portée impression) — max à choisir + cap
  format (patron bandMaxMM).
- **P7 : les cartes sont 100 % RASTER dans le PDF** (build_pdf prend des
  PIL Image, _image_xobject :1972-2017 ; le SEUL vectoriel = repères de
  coupe + cartouche, via _registration_cs :2032-2046). OCG_LAYERS
  (marks, slug) + _oc_open/close :2049-2101 = le mécanisme exact d'une
  couche « Foil » ; **pdf_header 1.5 SI layers, et layers ⇒ la revendication
  PDF/X TOMBE déjà** (:2216, :2220 — contrainte pré-existante héritée).
  frame.py n'a AUCUN code de chemin (grep vide) → l'écrivain de chemins
  Foil (m/l/c d'un anneau arrondi) est du code NEUF côté print.py,
  alimenté par les nombres de doc.frame.seal (bloc miroir, parité).
  Préflight : lignes {kind, level, card…} :3023+ — les contrôles
  vectoriels s'y ajoutent tels quels.
- **Machinerie holo 2b** : _holo_thickness_png(out_px) lru_cache clé
  UNIQUE out_px (forge3d_scene.py:301-342) ; holo_finish VOLONTAIREMENT
  non caché (:295-300, listes mutables) ; le finish s'attache au nœud
  material (params mat/tile_mm/finish/aniso, mod-forge3d.js:105,
  forge3d.py:1085+). **Motifs = re-clé du cache en (out_px, hash de la
  pile)**, l'enveloppe reste non cachée. Sources d'images disponibles :
  images de slots P3 (type/img_N.png), papier texture, matières Material
  Forge (boutique), sigil à téléverser (aucune route dédiée — le patron
  compteur P3 est le plus récent).
- **§6.2bis-d « PROFONDEUR d'extrusion du contour 3D » : le nœud `extrude`
  N'EXISTE PAS au vocabulaire** — l'anneau-objet-3D est un chantier de
  vocabulaire (bloc miroir + writer + UI), PAS une option de finition.
  Scopé HORS 3c (voir décision 4).
- **Verso** : paintBack :1760-1882 (6 motifs + else miroir), BACKS = 7 ids
  SANS « custom » (deux côtés) ; **P2 n'a AUCUNE pile ordonnée** (tout
  booléen/enum) — les calques du verso seront LA PREMIÈRE, au patron de la
  liste P3 ; la preuve d'empilement impose source-over/multiply-PRÉCOMPOSÉ
  (§4.2 — un blend vivant casse la preuve ; le multiply se cuit dans les
  pixels du calque). Route d'images : P2 ne peut PAS importer celle de P3
  (frame.py:7-10 « jamais d'un voisin ») → sa PROPRE route au même patron
  durci (réservation O_EXCL, bombe de pixels, whitelist — les leçons
  T2-3b). CF.side() = la face du DERNIER rendu (pas une sélection vive,
  core.js:583/683/2257) ; #sideBtn au CORE :2195-2199.
- **IA cadres** : le patron complet EXISTE dans face.py (:872-953 —
  /ai-models = pricing._IMAGE_MODELS + load(), jamais de liste recopiée ;
  génération par CF.images.generate, core-level ; prix AVANT dans le
  select + coût du clic + toast après, mod-face.js:3548-3744). Le décor
  s'insère dans le bloc DÉJÀ clippé « toile moins fenêtre » de paintFront
  (:1613-1624, où matter() peint) — z40, sous la moulure, hors fenêtre.
  Stockage : `img:` = magasin d'images APP-WIDE (/api/images —
  mod-face.js:1652-1661) vs deck-scoped — trancher par la PORTABILITÉ
  (décision 5).
- **Interaction 3a-F1 (allow-list des modèles)** : l'allow-list de
  « enregistrer comme modèle » DÉRIVE des clés d'archetype_frame — les
  clés neuves (`seal`, `back`, calques verso, `decor`) seront REFUSÉES par
  défaut ; la spec veut le verso custom et le Sceau DANS le modèle
  fragments (§6.2ter :458-459, §6.2bis « mis en avant par
  deepotus-fragments ») → l'admission est une DÉCISION par clé, testée
  (les images référencées : voir décision 5).
- **Dettes, état exact** : N2 IMGS sans éviction intra-session
  (mod-forge3d.js:3184-3234) ; N4 registres `{}` nus (rowModel:983,
  rewireRow:5012+, maillonsAval:5053+, freeId:5076) ; N7 to_thread =
  exécuteur par défaut partagé (lectures courtes vs téléchargements
  120 s) ; molette 2b = restes MANUELS d'œil (chatoiement, fluidité,
  2 onglets) ; GET /decks sans pagination (core.py:363-366 — 13,4 Mo/18 s
  mesurés en 3a) ; GC images orphelines (type/img_N jamais réclamées,
  nœuds forge3d) ; banc boutons-de-rangée (querySelectorAll de paille →
  [], remède esquissé au plan 3b:1013-1015) ; branche arcTo (accumulation
  de chemin au banc, 3a/3b « RESTE »).
- **Délestage** : mod-frame.js 5033 l. va absorber Sceau-écran + verso +
  IA cadres — la règle 1 (1 JS/module) INTERDIT un sidecar JS : chaque
  tâche déclare son net et vise court ; mod-forge3d.js 5639 (motifs UI),
  print.py 3880 (Foil).

## Décisions de conception 3c

1. **`doc.frame.seal`** : sous-objet UNIQUE
   `{on, kind ("argent"|"dorure"), width_mm, scope: {screen, print,
   mesh}, motifs: [...]}` — validé dans st() (branche imbriquée patron
   window) + miroir frame.py + parité ; LIMITS `seal_width_mm` [0.2, 6] +
   cap format. « 3D uniquement » = scope {screen:false, print:false,
   mesh:true} — une configuration de PREMIER RANG (le défaut du modèle
   fragments, §6.2bis-d). L'écran DIT toujours la portée active.
2. **Le peintre écran (a)** est DÉTERMINISTE À PHASE FIXÉE : la phase
   CANONIQUE 0.35 est celle du fichier livré ; l'aperçu animé (survol)
   passe par LE MÊME peintre avec une phase de pointeur — mais tout rendu
   CF.renderCard sort à 0.35 (l'utilisateur voit littéralement la frame
   livrée). Pile : clip de l'anneau (rrPath externe + dilaté −width) →
   dégradé HSL 70-90 % → bande de reflet en overlay → paillettes
   PRNG(seed = index de carte) allumées par hash(x,y,floor(phase·N)).
   `overlay` casse le mode « isolée » de la preuve d'empilement → la
   couche cadre bascule en « empreinte » (le mécanisme §4.2 CONÇU pour
   ça — delta des cumulatifs, exact par construction) : DIT au plan et
   au test, pas découvert. scope.screen=false → base calme (le métal du
   kind, sans arc-en-ciel).
3. **Le masque de foil (b)** : quand scope.print — la couche OCG « Foil »
   dans le PDF (3e entrée OCG_LAYERS + /Separation « Foil » réel au
   patron _registration_cs), l'anneau écrit en VECTORIEL (m/l/c d'un
   rectangle arrondi ×2, even-odd, depuis les nombres mm du seal — coupe
   + FOND PERDU par construction) ; Overprint posé. Repli raster : un
   endpoint « masque de foil » PNG 1-bit 600 dpi SANS anti-aliasing
   (seuil 50 %). Préflight AVANT rasterisation : trait ≥ 0,2 mm, distance
   au trait de coupe ≥ 3,2 mm (l'écart entre zones ne s'applique pas à un
   anneau unique — dit) ; l'écran ÉCRIT la variance de fabrication
   (1-2 mm) et la limite produit (spot pur vs foil+CMJN, spec :405-406).
   Layers ⇒ PDF/X tombe : hérité, RE-dit à l'écran quand Foil est actif.
4. **Portée 3D + motifs (d), scope HONNÊTE** : le volet 3D du Sceau =
   les RECETTES 2b déjà livrées (argent/dorure sur le nœud material) ;
   la 3c y AJOUTE les MOTIFS INCRUSTÉS : `motifs: [{src, gain}]` (1-4
   calques) encodés dans le canal G par ADDITION BORNÉE (ordre = ordre
   d'addition), _holo_thickness_png re-clé (out_px, hash de pile
   d'octets), déterministe (mêmes calques → mêmes octets, relu dans le
   fichier livré). Sources v1 : une image du deck (les images P3
   type/img_N + le papier texture) OU une matière Material Forge — le
   sigil à téléverser passe par la route P3 existante (l'utilisateur
   importe puis choisit ; pas de 4e magasin). **L'anneau-contour EXTRUDÉ
   en objet 3D (« profondeur d'extrusion sur le nœud extrude ») est HORS
   3c** — il exige un kind de vocabulaire nouveau (bloc miroir + writer
   + grammaire) : consigné en tête du plan phase 4/suivant, avec sa
   raison. Le scope.mesh actionne les recettes sur le matériau du CADRE
   (la couche entière — l'isolation de sous-région n'existe pas : DIT à
   l'écran « le cadre entier reçoit la finition »).
5. **Verso custom (§6.2ter)** : `BACKS += "custom"` (parité) ;
   `doc.frame.back_image` (src) + `back_layers: [{src, opacity, scale,
   blend: "normal"|"multiply"} ×≤6]` — la PREMIÈRE pile ordonnée de P2
   (données seulement : l'UI de réordonnancement = la liste du panneau,
   patron P3) ; le multiply se PRÉCOMPOSE dans les pixels du calque au
   moment du rendu (la preuve d'empilement reste source-over — mécanisme
   §4.2). Route d'images P2 : `POST /frame/image` → decks/{did}/frame/
   img_{n}.png, LE MÊME durcissement que T2-3b (réservation O_EXCL,
   bombe de pixels à l'en-tête, whitelist avant disque, compteur max+1,
   cap 8) — pas d'import du voisin. Aperçu par #sideBtn existant.
   **Portabilité modèle** : back_image/back_layers ADMIS à l'allow-list
   MAIS leurs `src` pointent des fichiers deck-locaux → « enregistrer
   comme modèle » EMBARQUE les octets ? NON (un modèle n'embarque pas
   d'illustrations, 3a) — le modèle garde les réglages, les `src`
   deck-locaux sont PURGÉS avec une note dans le modèle (le fragments
   officiel fournira ses fichiers en phase 4) ; dit et testé.
6. **IA cadres (§6.3)** : panneau P2 « générer le décor de cadre par
   IA » — la liste/prix par une petite route frame.py au patron
   face.py:ai-models (import pricing, jamais de liste recopiée),
   génération par CF.images.generate (core-level, existant), prix AVANT +
   coût du clic + toast après (les trois jambes du patron P1). L'image
   devient `doc.frame.decor = {src: "img:fichier", alpha}` peinte dans le
   bloc clippé de matter() (z40, sous la moulure, hors fenêtre) ; prompt
   pré-rempli par l'archétype ACTIF (le preset modele: du deck → hint du
   modèle). Stockage : le magasin app-wide `img:` (le patron P1 exact —
   c'est le même générateur) ; à l'allow-list, `decor` ADMIS mais src
   purgé (comme décision 5).
7. **Dettes** : N4 sansProto (4 registres, mécanique) + banc
   boutons-de-rangée (le remède esquissé : vrai querySelectorAll de
   paille) + arcTo (accumulation de chemin si ≤ ~30 l.) + pagination
   /decks (param limit + le rabot de la galerie documenté) = CORRIGÉS en
   3c ; N2 (éviction IMGS), N7 (exécuteur), GC images = CONSIGNÉS avec
   mesure à l'appui (pas de symptôme réel — écrit une fois de plus, avec
   chiffres) ; molette 2b = la liste d'œil permanente (rien à coder).

### Task 1 : le Sceau à l'écran (schema seal + peintre P2 + portée)

**Files:** mod-frame.js, mod-frame.css (si badge), frame.py,
test_cards_frame.py.

- [ ] RED : parité seal deux côtés (st imbriqué ↔ frame.py) ; LIMITS
      seal_width_mm ; le peintre : anneau peint DANS la bande (pixels
      échantillonnés dedans/dehors), déterminisme (2 rendus = octets
      identiques à phase fixe), paillettes par carte (carte 1 ≠ carte 2,
      même carte = même champ), phase canonique 0.35 au fichier
      (CF.renderCard) ; scope.screen=false → base calme (pas
      d'arc-en-ciel mesuré) ; la preuve d'empilement TIENT (bascule
      empreinte attendue et assertée) ; presets/rendu existants
      byte-identiques seal.on=false.
- [ ] Panneau : groupe « Sceau prismatique » (case + kind + largeur +
      les 3 interrupteurs de portée + l'état dit).
- [ ] Mutation : Math.random introduit (déterminisme rougit), phase non
      canonique au fichier, clip absent (déborde), scope ignoré.

### Task 2 : le masque de foil (P7)

**Files:** print.py, frame.py (miroir seal mm), mod-print.js (l'état/les
téléchargements), test_cards_print.py (+ test_cards_frame.py parité).

- [ ] RED : PDF avec seal.scope.print → OCG « Foil » présent +
      /Separation « Foil » + les ops vectoriels de l'anneau (relus dans
      les octets du PDF : BDC/EMC, re×2 even-odd ou m/l/c), Overprint ;
      sans scope.print → aucun ; préflight : largeur 0,1 mm → err
      nommée, distance coupe < 3,2 → warn/err, la variance écrite ;
      endpoint masque raster : PNG 1-bit 600 dpi SANS AA (octets : 2
      valeurs uniques), coupe+fond perdu ; PDF/X tombé DIT.
- [ ] Mutation : AA laissé au raster (>2 valeurs → rougit), l'anneau au
      mauvais cadre (coupe vs fond perdu), OCG sans Separation.

### Task 3 : les motifs incrustés (canal G) + portée mesh

**Files:** forge3d_scene.py, forge3d.py (si route motifs), mod-forge3d.js
(UI du nœud material), test_cards_forge3d.py.

- [ ] RED : _holo_thickness_png(out_px, pile) — même pile = mêmes octets,
      piles ≠ = octets ≠, addition BORNÉE (canal G ≤ max), ordre
      d'addition = ordre des calques (permutation → octets ≠) ; le motif
      RELU dans le canal G du GLB livré (le sigle se voit dans les
      épaisseurs — corrélation mesurée avec l'image source, pas
      l'intention) ; cache re-clé sans fuite (2 cartes, 2 piles, pas de
      collision) ; holo_finish reste NON caché (pin).
- [ ] UI : sur le nœud material à finition holo — « motifs dans
      l'hologramme » (1-4, source = image du deck OU matière), aperçu
      3D à l'appui (le viewer existant) ; scope.mesh du seal actionne la
      finition sur le matériau du cadre avec l'honnêteté « couche
      entière » à l'écran.
- [ ] Mutation : addition non bornée, hash de pile ignoré au cache,
      permutation silencieuse.

### Task 4 : le verso custom

**Files:** mod-frame.js, frame.py, test_cards_frame.py.

- [ ] RED : BACKS+custom parité ; route /frame/image durcie (LE MÊME
      quintette de tests que T2-3b : réservation concurrente, bombe,
      whitelist-avant-disque, compteur troué, cap 8) ; paintBack custom :
      image + ≤6 calques, multiply PRÉCOMPOSÉ (la preuve d'empilement
      verte sur un verso custom à multiply — LE test), opacité/échelle ;
      l'aperçu par #sideBtn ; « enregistrer comme modèle » : back admis,
      src purgés avec note (test des octets du modèle).
- [ ] Panneau : dos « custom » → import + liste de calques (patron liste
      P3 : ordre/opacité/suppression).
- [ ] Mutation : blend vivant (preuve rougit), src non purgé au modèle,
      cap dépassé.

### Task 5 : l'IA cadres

**Files:** mod-frame.js, frame.py (route ai-models miroir), test_cards_frame.py.

- [ ] RED : GET /frame/ai-models = pricing (jamais recopiée — pin
      d'import), prix AVANT au select + coût du clic ; génération par
      CF.images.generate → doc.frame.decor ; le décor peint dans le bloc
      clippé (pixels hors fenêtre, sous moulure) ; prompt pré-rempli de
      l'archétype actif (preset modele: → hint) ; decor admis à
      l'allow-list, src purgé au modèle.
- [ ] Mutation : liste recopiée (pin), décor peint SUR la fenêtre
      (pixels), prix absent.

### Task 6 : dettes + intégration 3c

- [ ] N4 : sansProto sur les 4 registres (mod-forge3d.js) + pin.
- [ ] Banc boutons-de-rangée : querySelectorAll réel au banc de paille +
      les 4 boutons joués + dragstart/drop (le remède du plan 3b).
- [ ] arcTo : accumulation de chemin au banc si ≤ ~30 l., sinon consigné
      chiffré.
- [ ] Pagination /decks : param `limit` (défaut raisonnable) + total ;
      la galerie l'utilise (le rabot 24 documenté devient une vraie
      requête bornée).
- [ ] N2/N7/GC : consignés AVEC mesure fraîche (une ligne de chiffres
      chacun) dans la note de clôture.
- [ ] Suite complète, lint intégral, contrat, cf_deploy -Backend +
      -Check 0 écart, navigateur réel (Sceau à l'écran sur une carte —
      l'arc-en-ciel et la phase canonique, le masque de foil téléchargé,
      un motif dans l'hologramme au viewer, un verso custom multiply,
      un décor IA si clé — SINON le refus nommé), plan+mémoire+push.
- [ ] **Consigne de sortie de phase** : l'anneau-contour EXTRUDÉ 3D
      (nœud `extrude`) transmis NOMMÉMENT à la phase 4/suivante avec la
      raison (vocabulaire nouveau) ; les restes d'œil cumulés listés.

## Auto-revue du plan

- La vérité vectorielle unique (§6.2bis) est tenue par les NOMBRES du
  seal (l'anneau est rrPath partout) — les trois rasterisations dérivent
  de ces nombres, jamais d'un PNG partagé (le piège des deux cadres).
- `overlay` du peintre écran → bascule « empreinte » de la preuve :
  mécanisme §4.2 CONÇU pour ça, asserté plutôt que découvert.
- Les leçons 3b réappliquées d'office : réservation O_EXCL et bombe de
  pixels sur la route P2, parité d'EXÉCUTION pour seal/normalisation,
  pins de couture si une règle est rejouée, « la provenance se dit à la
  naissance » pour scope.
- Risques nommés : mod-frame.js (déclaration par tâche, viser court) ;
  la revendication PDF/X qui tombe avec les layers (héritée, dite) ;
  l'allow-list 3a-F1 amendée clé par clé avec purge des src ; le canal G
  re-clé sans casser le lru_cache existant ; l'extrude HORS phase avec
  sa raison écrite.
