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
   cap format. *(T1 livrée SANS `motifs` : la clé naît en T3 avec son
   consommateur — voir la note de fin de T1.)* « 3D uniquement » = scope {screen:false, print:false,
   mesh:true} — une configuration de PREMIER RANG (le défaut du modèle
   fragments, §6.2bis-d). L'écran DIT toujours la portée active.
2. **Le peintre écran (a)** est DÉTERMINISTE À PHASE FIXÉE : la phase
   CANONIQUE 0.35 est celle du fichier livré ; l'aperçu animé (survol)
   passe par LE MÊME peintre avec une phase de pointeur — mais tout rendu
   CF.renderCard sort à 0.35 (l'utilisateur voit littéralement la frame
   livrée).
   **AMENDEMENT T1 (ronde 2) — l'APERÇU AU POINTEUR EST REPORTÉ, et
   c'est dit plutôt que découvert.** La T1 livre la moitié déterministe
   seule : `sealStops(f, phase)` prend déjà la phase en PARAMÈTRE et
   `paintSeal` la lui passe (`SEAL_PHASE`), donc le peintre est prêt à
   recevoir autre chose — il ne manque que le branchement pointeur et sa
   boucle de rendu. Reporté **à la passe navigateur de la T6**, pour deux
   raisons : (1) l'animation ne se juge qu'à l'œil, sur une vraie carte,
   et la T6 est déjà la passe qui ouvre le navigateur ; (2) une boucle de
   repeinte au survol touche la fluidité du CORE, un sujet qui a déjà
   coûté une passe entière en 2b (« 1 patch/frame ») et qui n'a rien à
   faire dans la tâche qui pose le schéma. Si la T6 ne le prend pas, il
   part en phase 4 avec cette même raison.
   *À ne pas confondre avec l'interdiction du test* : `test_la_phase_du
   _fichier_livre_est_canonique` interdit `clientX` / `event` / `Date.now`
   DANS `paintSeal` — c'est-à-dire les entrées CACHÉES d'un rendu LIVRÉ,
   pas un paramètre d'aperçu explicite. Le jour où le survol arrive, il
   passe par l'argument `phase`, et le test reste vert par construction. Pile : clip de l'anneau (rrPath externe + dilaté −width) →
   dégradé HSL 70-90 % → bande de reflet en overlay → paillettes
   PRNG(seed = index de carte) allumées par hash(x,y,floor(phase·N)).
   `overlay` casse le mode « isolée » de la preuve d'empilement → la
   couche cadre bascule en « empreinte » (le mécanisme §4.2 CONÇU pour
   ça — delta des cumulatifs, exact par construction) : DIT au plan et
   au test, pas découvert. scope.screen=false → base calme (le métal du
   kind, sans arc-en-ciel).
   **AMENDEMENT T1 (23/08) — la raison exacte de la bascule.** Un
   `overlay` ne casse PAS l'isolation à lui seul : là où la couche pose
   sa propre base OPAQUE sous le mélange, le fond en dessous ne compte
   pas et `solo` re-empilé donne le même pixel que le cumulatif. Ce qui
   bascule la couche, c'est l'endroit où sa base n'est pas opaque — la
   frange d'ANTICRÉNELAGE du découpage de l'anneau (un rectangle arrondi
   : des centaines de pixels de bord partiels) — et la comparaison
   STRICTE de `samePixels` (zéro pixel d'écart, core.js:845). Conséquence
   pratique pour la suite : le mode réel de CETTE carte est une mesure de
   NAVIGATEUR (l'anticrénelage n'existe pas hors d'un vrai canvas). La
   suite pytest prouve donc le MÉCANISME — une couche non-empilable est
   gardée en « empreinte » et `stack_ok` tient quand même — en faisant
   tourner la VRAIE `layers()` de core.js sur un contexte raster minimal
   (`BANC_EMPILEMENT`, test_cards_frame.py) ; le mode observé sur une
   carte réelle se relève au navigateur (T6). Jusqu'ici ce chemin n'avait
   AUCUN test exécutable dans la suite — seulement une lecture de source
   (test_cards_forge3d.py:185).
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

- [x] RED : parité seal deux côtés (st imbriqué ↔ frame.py) ; LIMITS
      seal_width_mm ; le peintre : anneau peint DANS la bande (pixels
      échantillonnés dedans/dehors), déterminisme (2 rendus = octets
      identiques à phase fixe), paillettes par carte (carte 1 ≠ carte 2,
      même carte = même champ), phase canonique 0.35 au fichier
      (CF.renderCard) ; scope.screen=false → base calme (pas
      d'arc-en-ciel mesuré) ; la preuve d'empilement TIENT (bascule
      empreinte attendue et assertée) ; presets/rendu existants
      byte-identiques seal.on=false.
- [x] Panneau : groupe « Sceau prismatique » (case + kind + largeur +
      les 3 interrupteurs de portée + l'état dit).
- [x] Mutation : Math.random introduit (déterminisme rougit), phase non
      canonique au fichier, clip absent (déborde), scope ignoré.

**LIVRÉ le 23/08 — suite 184/184 verte (159 avant), lint 9/9 0 violation,
`node --check` vert.** Ce qui est en place et ce qu'il faut savoir avant
la T2 :

- **Schéma** `doc.frame.seal = {on, kind, width_mm, scope:{screen,
  print, mesh}}` — 29e clé de `doc.frame`, branche imbriquée `sealOf()`
  dans `st()` (rend TOUJOURS un objet neuf : `DEFAULTS.seal` est le même
  objet que celui remis au registre du CORE). Miroir `frame.seal_of()`.
  `motifs` NON ajouté : rien ne le consomme en T1 et une liste vide
  publiée serait un contrat qu'aucun test ne tient — il naîtra en T3,
  avec son consommateur (règle « la provenance se dit à la naissance »).
- **Bornes** `LIMITS.seal_width_mm = [0.2, 6]` des deux côtés + une borne
  de FORMAT `sealMaxMM(tw, th, edge, win)` / `seal_max_mm(...)` au patron
  `bandMaxMM` : l'anneau doit tenir ENTRE la coupe rentrée et la FENÊTRE
  (au-delà ce n'est plus un contour, c'est une plaque sur l'illustration)
  ET ne pas s'inverser (min(tw,th) − 2·edge − 0,2). Elle MORD partout :
  5,0 mm en poker (contre 6 au curseur), et l'écran l'écrit « (borne du
  format) » comme pour `edge_mm`/`inner_mm`.
- **Identité de carte** : `card.id` (FNV-1a de la chaîne), repli sur
  `"c" + (i + 1)` — l'identité que `normCard` du CORE donne déjà. La spec
  dit « seed = id de carte » ; le plan disait « index » : c'est `id` qui
  a été retenu.
  **CORRIGÉ EN RONDE 2 — la phrase de la ronde 1 (« l'id survit à un
  réordonnancement ») était FAUSSE sur le deck par défaut.** `data.py`
  assigne un identifiant POSITIONNEL (« c » + le rang de la ligne) quand
  aucune colonne `id` n'est mappée, et c'est le cas par défaut : déplacer
  une carte change alors son identifiant, donc son scintillement. Mesuré :
  sans colonne mappée 4/4 cartes changent au déplacement, avec 0/4. La
  phrase tenable est conditionnelle — **la graine est l'IDENTITÉ de la
  carte ; mappez une colonne `id` et le scintillement suit la carte au
  déplacement.** Le repli `"c" + (i + 1)` est du **code mort en
  pratique** (`normCard` et `data.py` fournissent toujours un id) : il
  n'est là que pour qu'un `card` nu passe au banc, et le code le dit.
  Un test épingle le fait dont la phrase dépend (le repli positionnel de
  `data.py`) et interdit le retour de l'affirmation inconditionnelle.
- **Le Sceau passe SOUS les filets** (début de l'étape 6 de `paintFront`,
  même source de chemin `m.outer`) : le filet extérieur garde son arête
  nette POSÉE SUR la bande, au lieu d'en être à moitié recouvert.
  **RECTO SEUL** — `paintBack` ne le peint pas. C'est ce que le plan
  demandait (« s'insère dans paintFront ») et ce qu'un foil de production
  fait le plus souvent ; si le verso doit le porter, c'est une décision à
  prendre avec la T4 (verso custom), pas un oubli à rattraper en silence.
- **L'axe du dégradé est FIXE (118°) et ne suit pas `grad_angle`** : celui-là
  incline la matière de la BANDE ; faire tourner le Sceau avec lui ferait
  bouger le fichier livré au réglage d'une autre grandeur.
- **Parité des nombres** : `/metrics` publie `seal_mm [largeur tracée,
  borne]` et `seal_px [largeur, x, y, w, h, r]` — l'anneau EXTÉRIEUR, en
  pixels de toile. Deux TABLEAUX et non un sous-objet : la pastille de
  vérification compare des `JSON.stringify` clé par clé, et deux
  dictionnaires dont l'ordre d'insertion diffère se comparent faux sans
  qu'un nombre ait bougé. **La T2 hérite de ces nombres tels quels.**
- **Amendement de test, dit** : `st()` et `seal_of()` ne sont PAS
  identiques hors bornes, et c'est la doctrine déjà en place pour
  `win_r_mm` : l'écran RÉPARE un document qu'il possède (clamp), la route
  REFUSE un corps de requête (400 nommant la borne). La divergence ne
  peut pas mordre — l'écran n'envoie que du `st()` déjà normalisé.
- **Habillages 3a** : les sept archétypes portent `seal` ÉTEINT (copie
  profonde par entrée). Un archétype qui l'allumerait changerait l'aspect
  de tout deck déjà instancié — le défaut du modèle `deepotus-fragments`
  (« 3D uniquement », décision 1) est une entrée de la phase 4, pas une
  réécriture rétroactive des sept.
- **Reste d'œil pour la T6** : le chatoiement et la lisibilité de la
  bande à l'écran ; le MODE réel de la couche cadre (isolée/empreinte)
  sur une vraie carte (voir l'amendement de la décision 2) ; et **la
  lisibilité de la bande SOUS le bandeau et la gemme** — ils peignent en
  z=70, donc PAR-DESSUS le Sceau (z=40). Mesuré, poker, `inner_mm` 5,5 :
  au défaut (1,2 mm) le bandeau et la gemme ne touchent pas la bande
  (0,0 %) ; à 3 mm, 20,8 % de la surface du bandeau et 4,4 % de celle de
  la gemme tombent dessus ; à 5 mm (la borne du format), 59,2 % et
  39,5 %. Ce n'est donc pas un défaut au réglage livré, mais ça le
  devient dès qu'on élargit la bande — et le chiffre monte encore avec
  un libellé de rareté long ou une marge intérieure plus petite.

### Ronde de revue 2 (23/08) — ce qui a été corrigé

- **F1, CODE** : `sealMaxMM` / `seal_max_mm` rabotaient la largeur à la
  place disponible sans jamais confronter le résultat au plancher qu'ils
  prétendaient tenir. Mesuré : fenêtre à 1,61 mm de la coupe → bande
  **DESSINÉE de 0,01 mm** (0,118 px à 300 DPI), panneau lisant
  « 0.01 mm », `/metrics` publiant `seal_mm[0] = 0.01` — la largeur même
  que le préflight de la T2 est spécifié refuser. L'écran dessinait ce
  que la presse rejette. Corrigé des deux côtés (`v >= SEAL_MIN_MM`,
  comparaison sur la valeur NON arrondie) : sous le plancher, **pas
  d'anneau du tout**, et la ligne d'état donne le remède (« rapprocher le
  filet de la coupe ou reculer la fenêtre »). Contrôle négatif : la
  borne d'avant fait revenir les 0,01 mm.
  *Le cas exactement à 0,2 mm n'est pas épinglé : `1.8 - 1.6` vaut
  0,19999999999999973 en IEEE 754 et le verdict y bascule sur le dernier
  bit. Le doute tombe volontairement du côté du REFUS.*
- **Parité, trou comblé** : le test inter-formats ne comparait JAMAIS
  `seal_mm[0]` / `seal_px[0]` — le seul nombre que la borne CHANGE.
  72 cas sains ne prouvaient rien. Il compare désormais 12 formats × 6
  largeurs (dont 0,205 et 2,005 pour l'arrondi), largeur TRACÉE comprise,
  et exige qu'au moins un cas voie la borne mordre.
- **`width_mm: null`** : l'écran rendait 0,2 (le générique `num()` prend
  `Number(null) === 0`, puis clamp au plancher) là où le backend rendait
  1,2. Aligné sur « absent = défaut » des deux côtés.
- **Banc d'empilement** : son mélangeur ne connaît que `source-over` et
  `overlay` ; un `multiply` futur serait passé en silence pour du
  source-over et le banc aurait rendu « isolée » sur une couche qui ne
  l'est pas. Il REFUSE maintenant en nommant le mode (+ son test).
- **`mulberry32` (spec) vs `prng`/xorshift32 (livré)** : dit au code —
  même famille de générateurs seedés, et c'est la règle de la pièce qui
  prime ; un second générateur dans le même fichier serait une seconde
  source de hasard à auditer. La spec nomme l'esprit, pas la marque.
- **Net déclaré** : mod-frame.js +380/−5 = **+375** (5033 → 5408) en
  ronde 1, au-dessus de la cible ≤ 350 — après une passe de rasage qui a
  sorti la conversion hexadécimal→TSL du produit pour la mettre dans
  l'instrument de mesure (le test), là où elle appartient. La ronde 2
  ajoute ses lignes de garde et de vérité.
- **Suite** : 159 → 184 (ronde 1) → **188** (ronde 2). Huit mutations
  tuées : plancher retiré, `null` ramené à zéro, blend inconnu accepté
  au banc, `Math.random`, phase 0,71, clip retiré, portée écran ignorée,
  graine constante.

> **CLOSE (T1 — ad7d9e2 + ronde 4bec4af, revue adverse : FIX-FIRST soldé).**
> Le Sceau écran vit : seal 29e clé (1er sous-objet, alias DEFAULTS fermé —
> muté, il corrompait le SCHÉMA), peintre déterministe phase 0.35 (12 puis
> 8 mutations tuées, byte-identité par traces d'ops — la grille FNV ne peut
> pas juger un recto plein), graine = FNV(card.id) avec LA PHRASE VRAIE
> (« l'identité suit la carte SI une colonne id est mappée » — 4/4 vs 0/4
> mesurés ; le test épingle le FAIT dont la phrase dépend : si data.py
> stabilise ses ids, il rougit et la phrase se réécrit dans le bon sens),
> BANC_EMPILEMENT = première couverture exécutable du §4.2 (l'amendement :
> ce n'est pas overlay seul, c'est la frange d'anticrénelage + le zéro
> strict). Ronde : le PLANCHER s'applique au résultat cappé (bande 0,01 mm
> dessinée+publiée AVANT — l'écran qui dessine ce que la presse rejette),
> comparé NON arrondi avec l'appel IEEE écrit (« le doute tombe du côté du
> refus ») ; l'aperçu-pointeur REPORTÉ à la source (sealStops prend déjà la
> phase — le branchement seul manque) ; melange refuse les blends inconnus ;
> null = défaut des deux côtés ; parité élargie aux LARGEURS (le nombre que
> le cap change) ; bannière/bande re-mesuré : 0,0 % au défaut, écrit ainsi.
> 188 tests, net +422 déclaré. **Hérité par T2, écrit** : l'anneau défaut à
> 1,6 mm est DANS la zone ≥3,2 mm du foil — l'écran devra DIRE le remède.

> **CLOSE (T3 — 592ce41/a9b5bc1 + ronde e076754, revue adverse : FIX-FIRST
> soldé).** Les motifs incrustés vivent : min-avant-gain rendant l'ordre
> porteur (les alternatives commutatives vérifiées à la main), cache
> explicite borné sur empreintes (le lru_cache RETIENT ses arguments — une
> image de deck vivrait à jamais), arc-en-ciel caché à part (412→36 ms),
> **Pearson r=0,606 sur le GLB LIVRÉ** (0,161 sous le mutant non-borné),
> sha des OCTETS recalculé par build (le papier écrasé en place → nouvelle
> clé), la transparence PNG-8 palette attrapée en couture. Ronde : la
> PROSE remise à la mesure (à gain 1,0 — LE défaut — l'opérateur
> s'effondrait dans la somme commutative désavouée : identité de
> permutation ÉPINGLÉE comme fait) ; le défaut passé à 0,5 (blanc
> plein-cadre à 1,0 → UN niveau, les franges disparaissaient — et 0,5
> répare la SUBSTANCE de F1 : le défaut exhibe désormais l'ordre) ; un
> calque mort ne coûte plus LA FINITION et garde son nom ; fullmatch (le
> piège une 3e fois) ; l'« ondulation normale douce » NON livrée AVOUÉE au
> plan (la seule clause sans aveu). **scope.mesh câblé** : « le Sceau
> remplit le silence, il ne couvre jamais une parole dite » — l'explicite
> gagne Y COMPRIS échoué (substituer cacherait la faute) ; l'aveu au
> bordereau, le Sceau écarté à ignored (l'invariant 2c) ; un cadre porté
> par un nœud MOTEUR ne peut pas le recevoir — muet avant, avoué. Leçon :
> un grep de prose est un cliquet, pas une preuve (ré-ancré sur l'égalité
> écrite en toutes lettres). 123 tests, 10 mutants.

### Task 2 : le masque de foil (P7)

**Files:** print.py, frame.py (miroir seal mm), mod-print.js (l'état/les
téléchargements), test_cards_print.py (+ test_cards_frame.py parité).

- [x] RED : PDF avec seal.scope.print → OCG « Foil » présent +
      /Separation « Foil » + les ops vectoriels de l'anneau (relus dans
      les octets du PDF : BDC/EMC, re×2 even-odd ou m/l/c), Overprint ;
      sans scope.print → aucun ; préflight : largeur 0,1 mm → err
      nommée, distance coupe < 3,2 → warn/err, la variance écrite ;
      endpoint masque raster : PNG 1-bit 600 dpi SANS AA (octets : 2
      valeurs uniques), coupe+fond perdu ; PDF/X tombé DIT.
- [x] Mutation : AA laissé au raster (>2 valeurs → rougit), l'anneau au
      mauvais cadre (coupe vs fond perdu), OCG sans Separation.

**T2 LIVRÉE** — suite `cards_print` 90 → **100**, lint 9/9 0 violation,
`node --check` vert, **15/15 mutants tués**. print.py 3880 → **4467**
(+595/−8), mod-print.js 2149 → **2288** (+140/−1), test_cards_print.py
2516 → 2929. `frame.py` NON TOUCHÉ : la T1 y avait déjà tout
(`seal_of`, `seal_max_mm`, `seal_mm`/`seal_px` de `frame_metrics`).

- **MIROIR, PAS IMPORT — et la raison n'est pas de style.** `foil_of` /
  `foil_max_mm` / `_foil_win` sont des jumeaux locaux de `frame.py`
  (patron `forge3d._sceau_du_doc` de la T3), parité prouvée par un test
  qui, lui, importe les deux côtés. *(Compte corrigé en ronde : la
  livraison écrivait « 12 corps + 4 formats », c'était 11 corps bruts et
  UN format × 4 triples. La ronde a élargi pour de bon — 12 corps,
  **12 formats × 6 couples** plus les trois fenêtres de plancher — et
  épinglé les constantes jumelles.)* Ce qui TRANCHE :
  `seal_of` normalise un CORPS DE REQUÊTE et **lève** hors bornes ;
  l'importer aurait transformé un document à 0,1 mm modifié à la main en
  **400** — c'est-à-dire aurait rendu INATTEIGNABLE la ligne d'erreur
  nommée que ce plan demande. La divergence est épinglée dans les deux sens.
- **LE CADRE DANS LEQUEL ON DESSINE, tranché et écrit.** « coupe + FOND
  PERDU » du tableau §6.2bis décrit la **toile du masque**, pas la position
  de l'anneau : l'anneau épouse `m.outer` (la coupe rentrée de `edge_mm`),
  exactement comme le peintre d'écran. Dans le PDF il n'y a pas de toile —
  la page est la planche — donc l'anneau est posé au **coin de toile de
  chaque carte**, le même point que son XObject. Mesuré : bbox des ops
  contre `cell_rect + edge`, 4 abscisses sur une grille 2×3, tolérance
  0,001 pt (celle de l'écriture, pas du confort).
- **RECTO SEUL, hérité de la T1 et dit.** `paintBack` ne peint pas le
  Sceau ; dorer le verso ici promettrait une plaque que l'écran ne montre
  nulle part. Le contrôle l'écrit quand le recto-verso est actif.
- **Convention NOIR = dorure**, nommée dans le nom de fichier
  (`masque-foil_600dpi_noir-sur-blanc.png`), l'en-tête `X-CF-Foil-Ink` et
  l'écran. C'est ce que dit la spec (« noir 100 % ») et ce qu'attendent les
  portails ; une convention qu'il faut deviner est une convention qu'on
  inversera.
- **UN SEUL masque pour tout le jeu**, et c'est un FAIT : l'anneau ne
  descend que des mm du cadre, il est identique sur les 300 cartes. Livrer
  300 PNG identiques ferait croire à une variation qui n'existe pas
  (`X-CF-Foil-Scope`). La définition (600/1200) reconstruit la géométrie,
  elle n'agrandit jamais un PNG de 300 dpi.
- **`_rr_quarts` : UNE définition du coin arrondi** pour les deux
  rasterisations (`_rr_ops` en `m`/`l`/`c`, `_rr_poly` aplati pour PIL).
  Deux définitions du même coin, c'était « le piège des deux cadres » une
  marche plus bas. Le garde-fou existant `test_le_module_ne_dessine_aucune
  _carte` (qui INTERDIT `rounded_rectangle` dans print.py) a été **tenu, pas
  amendé** — et c'est lui qui a poussé vers la bonne solution.
- **Le compte de valeurs uniques ne prouve PAS l'absence d'anticrénelage.**
  Trouvé au banc : en mode « 1 » il ne peut y avoir que deux valeurs, donc
  l'assertion est inatteignable — et un seuil à **diffusion d'erreur** sur
  un bord lissé reste 1 bit tout en émiettant les coins en damier. La
  mesure qui mord est le nombre de **plages noires par ligne** (2 sur un
  anneau propre, **664** sous ce mutant), lignes de coin balayées une par
  une. Le premier mutant « anticrénelage » écrit était **ÉQUIVALENT** (il
  laissait le seuil en place : le produit restait juste) — dit plutôt que
  compté comme un tué.
- **La distance à la coupe est un AVERTISSEMENT, jamais une erreur** (le
  défaut du cadre vaut 1,6 mm : une erreur refuserait tout jeu neuf), et
  l'écran écrit le **remède** avant l'export — monter `edge_mm` au-delà de
  3,2 mm, *ce qui déplace aussi le filet extérieur*, ou accepter la variance
  de 1 à 2 mm. Le trait sous 0,2 mm, lui, est une **erreur** et la porte
  409 s'appuie dessus — *sans condition depuis la ronde : `foil_gate_rows`
  juge le foil sur le seul document, là où `preflight_safe` se tait faute
  de cartes.* Zéro ligne quand le Sceau n'est pas en portée impression :
  les 9 règles de fichier gardent leur compte.
- **Recouvrement bandeau/gemme : signalé, PAS chiffré.** z=70 contre z=40
  est un fait du code ; le pourcentage, lui, dépend du format et de la
  rareté de chaque carte. Recopier les 20,8 % mesurés en poker aurait été
  un chiffre faux — « un chiffre faux vaut moins que pas de chiffre ».
- **PDF/X : la chute est RE-DITE** à l'écran et au contrôle quand le foil
  est actif, avec sa vraie cause (les calques, contrainte héritée) — et il
  est dit qu'une encre d'appoint, elle, n'interdit rien.
- **15 mutants tués** : 1 bit abandonné · anticrénelage réel · damier par
  diffusion d'erreur · anneau au cadre du fond perdu · surimpression
  retirée · avertissement changé en erreur · portée impression ignorée ·
  nom de plaque faux · calque sans encre d'appoint · plancher 0,2 mm
  retiré · cadre non joint à la demande · calque écrit sans anneau · verso
  doré · anneau ne suivant plus la case · remplissage non-nul (plaque
  pleine — tué par les **aires signées**, pas par un grep de `f*`).
- **Reste d'œil pour la T6** : le masque téléchargé ouvert dans un
  visualiseur (l'aperçu doré de la `/Separation`), et la plaque confrontée
  à une carte réelle là où le bandeau la recouvre.

### Ronde de revue adverse T2 (23/08) — 3 FIX-FIRST + 1 should-fix + 4 nits

Suite `cards_print` 100 → **104**, lint 0, `node --check` vert, **13/13
mutants de ronde tués** (+ les 15 de la livraison). print.py 4467 → 4558,
mod-print.js 2288 → 2316, test_cards_print.py 2929 → 3223.

- **F1 — la couture de parité était posée à un centième de la règle qu'elle
  devait tenir.** Les quatre triples livrés mettaient le résultat exactement
  SUR 0,00 ou franchement au-dessus de 0,2 — jamais DANS l'intervalle
  (0 ; 0,2) que le plancher de la T1 existe pour refuser. Mesuré au banc
  (frame.py muté PAR ATTRIBUT, sans toucher au fichier qu'un autre agent
  éditait) : `v >= SEAL_MIN_MM` → `v > 0` laissait les quatre triples VERTS ;
  `SEAL_MIN_MM` 0,2 → 0,3 aussi. Deux fenêtres neuves posent désormais le
  résultat brut à **0,10** (refusé → 0,00) et **0,21** (accepté tel quel) :
  le premier mutant fait dire 0,10 à P2 contre 0,00 à P7, le second 0,00
  contre 0,21. Ajoutés avec : les **quatre constantes jumelles** épinglées
  (`FOIL_MIN_MM`/`FOIL_BAND_MIN_MM`/`FOIL_KINDS`/`FOIL_DEFAULTS` — quatre et
  non cinq : `FOIL_TRIM_MM` n'a PAS de jumeau, c'est une contrainte
  d'imprimeur que P2 n'a aucune raison de connaître, elle est donc épinglée
  sur la spec), les **trois portées** comparées (`screen` et `mesh`
  dérivaient librement) et le balayage porté aux **12 formats × 6 couples**.
- **F2 — le message dont le chiffre réfutait la phrase.** `width_mm: 0` édité
  à la main donnait « il ne reste que **5,00 mm**, sous le trait minimal de
  0,2 mm — rapprocher le filet » : 5,00 n'est pas sous 0,2, et bouger le
  filet ne soigne pas une largeur nulle. `foil_sans_anneau()` branche
  maintenant sur la VRAIE cause — la PLACE (`cap_mm < 0,2`) ou la LARGEUR DU
  DOCUMENT — et la même fonction sert au contrôle avant vol, au 409 de
  `/foil-mask` et à l'écran : deux textes pour un seul fait finissent par se
  contredire.
- **F3 — un `edge_mm` négatif dorait la carte du VOISIN.** Mesuré, poker 2×3,
  `edge -5` : l'anneau sortait de 5 mm hors de la rogne et celui de la
  colonne 1 traversait le trait de coupe de la colonne 0 de **1,00 mm**,
  pendant que le contrôle conseillait « acceptez la variance ». Les deux
  moitiés du correctif, parce qu'aucune ne suffit : la GÉOMÉTRIE est ramenée
  au trait de coupe (`max(0.0, …)` — le plancher que les deux surfaces de P2
  tiennent déjà en amont, mais **une plaque n'est pas un écran**) ET le
  document est AVOUÉ par une ligne d'**erreur** nommée, qui bloque. Réparer
  sans le dire aurait été le pire des deux.
- **MF1 — « la porte 409 s'appuie dessus » n'était vrai que si le corps
  portait des cartes.** `preflight_safe` rend `None` sans `slots`/`cards`, et
  la porte devenait alors muette : sans cartes, un anneau de 0,1 mm sortait
  en **200**. `foil_gate_rows` calcule les erreurs de foil du SEUL document
  et `gate` s'en sert quand le contrôle par carte n'a rien à dire. Choix
  assumé et écrit : la porte juge LE TIRAGE, pas l'objet demandé — c'est
  déjà ce que font les règles par colonne, qui refusent une carte seule pour
  une donnée que la PLANCHE n'imprimerait pas.
- **LE BANC D'ÉCRAN, ET CE QU'IL A TROUVÉ.** Deux mutants d'écran ont
  SURVÉCU à la première passe de ronde : la condition des deux causes forcée
  à `true` et l'aveu du retrait négatif désactivé — parce que le test
  d'écran ne faisait que chercher les phrases dans les octets pendant que la
  BRANCHE ne s'exécutait plus. La leçon de la T3 (« un grep de prose est un
  cliquet, pas une preuve ») re-payée. `paintFoil` tourne désormais POUR DE
  BON sous node (patron du banc `measureLine` de P2), et le test juge le
  HTML rendu. Le banc a immédiatement trouvé un **défaut réel que personne
  n'avait vu** : le bouton de téléchargement ne regardait que `plan.foil`,
  jamais le document — décocher « impression » laissait donc un bouton actif
  sous un panneau qui écrivait « hors portée impression », et le clic partait
  chercher un masque que la route refuse en 409. Les deux doivent être
  d'accord.
- **Nits** : le compte de la couture corrigé au plan (ci-dessus) · l'écart
  de `_rr_poly` ré-attribué au rayon **DESSINÉ** (coin moins retrait), avec
  le réglage livré (66,1 px → 0,036 px) et le pire cas du dépôt (377,9 px →
  0,20 px) au lieu d'un « coin de 3 mm » qui n'est pas ce qui est tracé ·
  l'espacement entre zones (0,25 mm) dit **SANS OBJET à l'écran**, là où
  l'utilisateur lit les deux autres contraintes, et plus seulement dans un
  commentaire Python · la seconde divergence avec `seal_of` — un nombre
  ILLISIBLE (NaN, infini, chaîne) fait lever P2 et retombe au DÉFAUT ici —
  nommée et testée à côté de celle des bornes.

**CE QUE LA T1 A LAISSÉ SUR LA TABLE POUR LA T2 — lire avant de coder :**

- **Les nombres sont déjà là** : `/frame/metrics` publie `seal_mm
  [largeur TRACÉE, borne du format]` et `seal_px [largeur, x, y, w, h,
  r]` (l'anneau EXTÉRIEUR, en pixels de toile). Ne pas recalculer :
  l'écran calcule les mêmes et la pastille les confronte déjà.
- **LE PRÉFLIGHT REFUSERA LE DECK PAR DÉFAUT, et l'écran doit le DIRE
  avant qu'il le découvre.** L'anneau est posé à `edge_mm` de la coupe,
  soit **1,6 mm au défaut** — DANS la zone interdite « distance au trait
  de coupe ≥ 3,2 mm » de §6.2bis-b. Un utilisateur qui coche
  « impression » sur un deck neuf verra donc son masque refusé par
  construction. La T2 doit écrire le REMÈDE à l'écran (monter `edge_mm`
  au-delà de 3,2 mm — ce qui déplace aussi le filet extérieur, à dire —
  ou accepter l'avertissement en connaissance de cause), pas laisser le
  préflight le révéler. C'est le même défaut de forme que F1 : refuser
  sans donner la sortie.
- **Le foil hérite la géométrie du bandeau et de la gemme.** Ils peignent
  en z=70, donc PAR-DESSUS l'anneau : à 3 mm de bande, 20,8 % du bandeau
  et 4,4 % de la gemme tombent sur la bande ; à 5 mm, 59,2 % et 39,5 %
  (poker, `inner_mm` 5,5 — mesuré). Un masque de foil qui ignore ce
  recouvrement pose du métal sous une encre opaque.
- **Le plancher de 0,2 mm est déjà tenu EN AMONT** (T1-F1) : aucune
  largeur sous 0,2 mm ne peut plus sortir de `sealMaxMM`. Le contrôle du
  préflight reste utile (il vaut sur d'autres chemins), mais il ne doit
  pas être la PREMIÈRE ligne de défense.

### Task 3 : les motifs incrustés (canal G) + portée mesh

**Files:** forge3d_scene.py, forge3d.py (si route motifs), mod-forge3d.js
(UI du nœud material), test_cards_forge3d.py.

- [x] RED : _holo_thickness_png(out_px, pile) — même pile = mêmes octets,
      piles ≠ = octets ≠, addition BORNÉE (canal G ≤ max), ordre
      d'addition = ordre des calques (permutation → octets ≠) ; le motif
      RELU dans le canal G du GLB livré (le sigle se voit dans les
      épaisseurs — corrélation mesurée avec l'image source, pas
      l'intention) ; cache re-clé sans fuite (2 cartes, 2 piles, pas de
      collision) ; holo_finish reste NON caché (pin).
- [x] UI : sur le nœud material à finition holo — « motifs dans
      l'hologramme » (1-4, source = image du deck OU matière), aperçu
      3D à l'appui (le viewer existant) ; ~~scope.mesh du seal~~ →
      REPORTÉ (le seal n'existe pas encore : T1 en cours en parallèle) ;
      l'honnêteté de PORTÉE qui appartenait à cette tâche est livrée à sa
      place — « le motif couvre TOUT l'élément et suit ses proportions,
      on n'isole pas une bande ».
- [x] Mutation : addition non bornée, hash de pile ignoré au cache,
      permutation silencieuse.

**T3 LIVRÉE** (suite `cards_forge3d` 106 → 123 après la ronde de revue,
lint 0, `node --check`, `--geom` vert ; forge3d_scene.py 1668→1909,
forge3d.py 2940→3309, mod-forge3d.js 5639→5849, mod-forge3d.css 371→389).

- **Le mécanisme de l'addition bornée, NOMMÉ** : chaque calque ne dépose que
  ce que l'épaisseur RESTANTE lui laisse — `min(luminance, 255 − g)` PUIS la
  part (`gain`). C'est ce `min` AVANT le gain qui rend l'ordre load-bearing :
  une somme finalement écrêtée est COMMUTATIVE (`min(255, g+a+b)` ne sait pas
  qui est arrivé le premier), et « ordre des calques = ordre d'addition » n'y
  voudrait rien dire. Le « screen » (part du reste, `a+b−ab`) est commutatif
  lui aussi — vérifié à la main avant de choisir. Mesuré : A(lum 100, part
  1,0) puis B(lum 200, part 0,5) sur fond nul = 178, l'ordre inverse = 200.
- **Le cache quitte `lru_cache`**, et pour une raison mesurable : sa clé
  RETIENT tous les arguments, donc les octets sources des calques (une image
  de jeu pèse des dizaines de Mo) resteraient vivants pour la durée de
  l'entrée. Cache explicite borné, clé `(out_px, ((sha256, gain), …))` — il ne
  garde QUE des empreintes et la sortie. `cache_info()`/`cache_clear()`
  gardent l'orthographe de functools. La boucle Python chère (l'arc-en-ciel)
  est cachée À PART sur le seul `out_px` (`_holo_base_g`) : sans elle un cran
  de curseur de part repayait 412 ms à 1024² ; avec elle, 36 ms.
- **Barre de qualité TENUE** (spec :445-446) : sur le GLB LIVRÉ, corrélation
  de Pearson **r = 0,606** entre le canal G et l'image source relue sur le
  disque du jeu ; moyenne de G **255,0 dans le motif contre 127,5 dehors**
  (Δ 127,6). Le motif est relu, pas déclaré.
- **Route neuve `GET forge3d/motif-sources`** — décision : l'écran P9 ne peut
  pas aller chercher les images de P3 (règle 8), donc le serveur AGRÈGE
  (images de calque du jeu + matière de support + boutique) et rend le `src`
  EXACT que `clean_graph` accepte. Un test épingle que tout `src` servi
  traverse le nettoyage : une recette servie que le nettoyage jetterait serait
  un piège. Les BORNES (`motif_max`, `motif_gain`) partent par `/info` avec
  les autres, jamais recopiées à l'écran.
- **Partage du refus** : hors vocabulaire = jeté EN SILENCE par `clean_graph`
  (son contrat : réparer, pas raconter) ; bien formé mais absent du disque =
  AVOUÉ nommément au bordereau `ignored` par la construction, qui seule sait.
  Et des motifs posés sans finition holo sont avoués aussi — l'écran garde
  alors le bloc VISIBLE (seule surface d'où les retirer) en le disant.
- **`did` lié au point d'appel** : `_habille` gagne un `did` en dernier, lié
  par `partial` dans `_element_local` — le sidecar forge3d_apercu.py garde son
  contrat d'injection à cinq positions INTACT (fichier non touché).
- **Mutants** : ordre ignoré (`pris = lum`) → 1 mort ; clé de cache sans la
  pile → 2 morts ; aveu du motif mort supprimé → 1 mort ; plafond de 4 ignoré
  → 1 mort ; addition vraiment non bornée (ni `min`, ni écrêtage) → 2 morts,
  dont la corrélation du GLB livré qui tombe de 0,606 à **0,161**.
  **UN MUTANT SURVIT, ET IL A RAISON** : `ImageChops.add` → `add_modulo` SEUL
  ne change aucun octet — la borne est portée par le `min(lum, reste)`, pas
  par l'écrêtage de l'addition. Écrit dans le code à l'endroit exact plutôt
  que de fabriquer un test qui ferait semblant de le tuer.
- **Trouvé en revue de couture, corrigé + testé** : un sigle DÉTOURÉ en mode
  « P » (l'export « PNG-8 » ordinaire) n'a AUCUNE bande alpha — sa
  transparence vit dans `info["transparency"]`. Un test sur `getbands()` seul
  la manquait entièrement et le sigle revenait OPAQUE, épaississant toute la
  carte. Garde + test dédié ; le mutant qui retire la garde palette est tué.
### Ronde de revue adverse T3 (23/08) — 4 FIX-FIRST + nits + le câblage

La revue a rendu quatre corrections de fond. Toutes RED d'abord, toutes
tuées par mutation. Suite 115 → 123.

- **F1 — la prose promettait plus que les octets.** À part PLEINE l'opérateur
  DÉGÉNÈRE : `g + min(lum, 255 − g)` VAUT `min(g + lum, 255)`, donc
  commutatif — et la part pleine était mon DÉFAUT des deux côtés. Vérifié
  exhaustivement : 24 permutations de 4 calques à 1,0 → UNE sortie. La spec
  n'est pas violée (elle ne demande que l'addition dans l'ordre de liste, qui
  tient) ; c'est la docstring qui désavouait une somme commutative en la
  décrivant. Correctif : paragraphe de docstring, clause au hint de l'écran
  (« l'ordre compte dès qu'une part est < 1 »), et un test qui épingle
  l'IDENTITÉ de permutation à 1,0 — le fait est DIT, plus redécouvert. **Zéro
  octet livré ne change.** (Le premier pin de docstring cherchait deux mots
  trop communs pour mourir avec la phrase : mutant SURVIVANT, mesuré, puis
  ré-ancré sur l'égalité écrite en toutes lettres.)
- **F2 — un calque corrompu coûtait TOUTE la finition, sans nommer le
  calque.** La docstring promettait « un calque mort ne coûte ni l'artefact ni
  la finition… DIT, avec sa source » : vrai d'un fichier ABSENT, faux d'un
  fichier PRÉSENT MAIS TRONQUÉ — l'échec explosait dans `holo_finish` et
  atterrissait dans l'`except` de `_habille`, qui jetait la recette entière
  avec un « finition ignoree » anonyme. Chaque calque est désormais VALIDÉ un
  par un (`motif_probe`) là où l'on sait d'où il vient. Coût assumé : un
  décodage de plus par calque (≤ 4), écrit dans la docstring ; l'alternative
  (compositeur tolérant) mettrait en cache une pile PARTIELLE sous une clé qui
  prétend les porter tous.
- **F3 — le défaut de part était le MAXIMUM de la plage.** Mesuré : une source
  claire PLEIN-CADRE — et `paper`/`mat:` le sont exactement — à part pleine
  remplit tout le film. Blanc pur → le canal G tombe à **UN SEUL niveau**, les
  franges pour lesquelles la recette 2b existe DISPARAISSENT ; papier à 240 →
  5,9 % de l'étendue, 2 niveaux sur 8. `MOTIF_GAIN_DEFAULT = 0,5` : les huit
  marches survivent (étendue 127/255, ~50 %), le sigle découpé se lit encore
  (écart de moyennes 63,5) — ET le défaut cesse d'être précisément le point où
  la propriété d'ordre s'évanouit (F1). Le hint NOMME la conséquence en plus.
  Le défaut part par `/info` (`motif_gain_default`) : l'écran ne le recopie
  pas, il le lit.
- **F4 — deux chaînes qui envoyaient au mauvais endroit.** Une matière de la
  boutique est APP-WIDE : « fichier absent de ce jeu » est le message qu'une
  machine ÉTRANGÈRE produira dès qu'un deck voyagera sans sa boutique → « …
  absente de la boutique de ce poste (les matieres ne voyagent pas avec le
  jeu) ». Et « rien où incruster », l'accent avalé par l'ASCII du bordereau,
  se relisait « rien ou incruster » → « aucun endroit ou s'incruster ».
- **Nits** : `_motif_src_ok` passe en `fullmatch` (le piège du `$` + `match`
  pour la TROISIÈME fois dans ce dépôt — « img:img_1.png\n » traversait) ;
  400/404 de `motif-sources` épinglés.

**LE CÂBLAGE `scope.mesh` (décision 4, les deux moitiés existent).** P9 LIT
`doc.frame.seal` dans le document du jeu — lecture d'état partagé, aucun
import de frame.py (lecteur local `_sceau_du_doc`, parité testée contre
`frame.seal_of`). Quand `seal.on && seal.scope.mesh` et qu'une couche de rôle
`cadre` est au graphe, la recette du kind habille l'élément.

- **Règle en une phrase : le Sceau COMBLE LE SILENCE, il ne couvre jamais une
  parole.** Un nœud `material` qui NOMME une finition l'emporte — y compris
  quand cette finition a ÉCHOUÉ (motif corrompu) : substituer alors la recette
  du Sceau masquerait la panne sous un résultat plausible. Un `material` qui
  ne nomme rien laisse le Sceau parler, et le bordereau le dit.
- **L'honnêteté de portée va au BORDEREAU, pas à `ignored`** : appliquer le
  Sceau est un FAIT (« la COUCHE ENTIERE recoit la finition — l'isolation
  d'une sous-region n'existe pas »), pas une perte, et `ignored` ne nomme que
  ce qui a été PERDU (invariant 2c, épinglé). Le Sceau ÉCARTÉ par un nœud
  explicite, lui, est bien une perte : il va dans `ignored`.
- **Divergence VOULUE avec `seal_of`, testée** : un métal ABSENT prend le
  défaut du schéma partagé (les deux côtés s'accordent) ; un métal DIT MAIS
  ILLISIBLE est REFUSÉ ici (P2 le remplace par l'argent — il doit peindre),
  parce que livrer un métal faux sans un mot est ce que `holo_finish` existe
  pour empêcher.
- **L'aperçu de nœud reçoit le même traitement** (barre :443, « aperçu ==
  fichier ») : sans quoi l'inspecteur montrerait un cadre nu que la
  construction livrerait iridescent.
- Le Sceau n'a PAS de `motifs` (T1 ne l'a pas ajouté, à raison) : sa finition
  implicite part donc avec une pile VIDE, et sans anisotropie (aucun
  interrupteur ne la demande — pas de réglage, pas de revendication).

**Trouvé en revue de couture DE CETTE RONDE** (le câblage neuf en ouvrait la
possibilité) : un cadre porté par un nœud `mesh3d` ne peut pas recevoir le
Sceau — le GLB du moteur porte déjà ses matériaux. Sans un mot, cocher la
portée 3D sur un tel cadre ne faisait RIEN, en silence : le pire des deux.
Avoué désormais, au MÊME patron que la matière chaînée sur un mesh3d (avouée
depuis la 2b) ; mutant tué. Nettoyage joint : le message d'un calque illisible
ne se lit plus « motif … motif illisible » au bordereau (le préfixe de source
appartient à l'appelant, la description au module scène).

**Mutants de la ronde, 10 tués** : clause d'ordre retirée du hint · phrase qui
porte le fait retirée de la docstring · validation par calque retirée · défaut
de part remis au maximum · magasin app-wide re-dit « de ce jeu » · `fullmatch`
redevenu `match` · `scope.mesh` ignoré · l'explicite ne gagne plus · honnêteté
« couche entière » retirée du bordereau · sceau-sur-moteur redevenu silencieux.
**Un mutant a SURVÉCU puis a été soldé** : le premier pin de docstring de F1
cherchait « part pleine » et « commutatif », deux mots trop communs dans ce
paragraphe pour mourir avec la phrase qui porte le fait — ré-ancré sur
l'égalité `min(g + lum, 255)`, écrite en toutes lettres, et re-tué.

**Clause de spec NON LIVRÉE, dite ici faute d'un aveu ailleurs** : §6.2bis-d
demande les motifs « + **ondulation normale douce** » — une normal map dérivée
du relief des calques, qui ferait ONDULER la lumière en plus de décaler les
franges. Elle est HORS du périmètre de la décision 4 (qui ne parle que du
canal G de l'épaisseur) et n'a **pas** été construite : aucun élément ne reçoit
de `mat_maps.normal` du fait d'un motif. C'est la seule clause du volet (d)
sans aveu jusqu'ici — à reprendre avec l'anneau-contour EXTRUDÉ, en phase 4.

- **Reste pour une tâche ultérieure** : ~~la ligne d'honnêteté « le cadre
  entier reçoit la finition » du `scope.mesh`~~ → LIVRÉE dans cette ronde (au
  bordereau du build ; le hint d'écran du Sceau appartient à P2, que la T1 a
  livré neutre).

### Task 4 : le verso custom

**Files:** mod-frame.js, mod-frame.css, frame.py, test_cards_frame.py,
models.py + test_cards_models.py (admission à l'allow-list + purge).

- [x] RED : BACKS+custom parité ; route /frame/image durcie (LE MÊME
      quintette de tests que T2-3b : réservation concurrente, bombe,
      whitelist-avant-disque, compteur troué, cap 8) ; paintBack custom :
      image + ≤6 calques, multiply PRÉCOMPOSÉ (la preuve d'empilement
      verte sur un verso custom à multiply — LE test), opacité/échelle ;
      l'aperçu par #sideBtn ; « enregistrer comme modèle » : back admis,
      src purgés avec note (test des octets du modèle).
- [x] Panneau : dos « custom » → import + liste de calques (patron liste
      P3 : ordre/opacité/suppression).
- [x] Mutation : blend vivant (preuve rougit), src non purgé au modèle,
      cap dépassé.

**T4 LIVRÉE — `cards_frame` 188 → 215 → **220** (ronde de revue),
`cards_models` 155 → 160 → **161**, lint 9/9 0 violation, `node --check`
vert, les 11 suites `cards` vertes. `cards/type.py` touché par la ronde
(N3, le défaut était dans les deux magasins).**

- **Schéma** : `BACKS += custom` (8e entrée, EN DERNIER — les sept motifs
  gardent leur rang, donc `card.back` et les sept habillages aussi) ;
  `doc.frame.back_image` (30e clé) et `back_layers` (31e, LA PREMIÈRE PILE
  ORDONNÉE de P2) ; `LIMITS.back_opacity [0,1]` / `back_scale [0.25,4]` ;
  `BACK_BLENDS` (normal, multiply), `BACK_LAYERS_MAX 6`, `BACK_IMAGES_MAX 8`.
  L'échelle part de 0,25 et non de 0 : un calque à l'échelle nulle n'est pas
  un réglage, c'est un calque qu'on aurait dû éteindre.
- **PARITÉ D'EXÉCUTION, et la divergence de la T1 NON rejouée** : `seal_of`
  REFUSE hors bornes parce que `/metrics` reçoit un sceau dans un corps de
  requête ; AUCUNE route ne reçoit `back_image`/`back_layers`, le miroir n'a
  donc rien à refuser — il NORMALISE, comme `st()`. La parité se mesure sur
  les valeurs, hors bornes comprises (7 corps hostiles, deux côtés). Piège
  attrapé au passage : le générique `num()` prend `Number(null) === 0` là où
  `float(None)` LÈVE — d'où `bnum()`, qui n'accepte qu'un nombre ou une
  chaîne numérique (la leçon `width_mm: null` de la T1, rejouée avant qu'elle
  ne morde).
- **LE MULTIPLY EST CUIT DANS LES PIXELS**, sur une toile de cuisson à part
  (réutilisée d'un calque à l'autre — lui ré-affecter sa largeur l'efface —
  et relâchée à la fin, patron `release()` de core.js), formule du canvas
  `Cs·(1−αf) + (Cs×Cf)·αf`. Sans le terme de gauche, multiplier par un fond
  ABSENT donne du NOIR : le rendu par couches de P9 peint sur toile
  transparente à chaque appel, et le verso en sortirait noir (mutant tué).
- **CE QUE LA PRÉCOMPOSITION N'ACHÈTE PAS, MESURÉ ET ÉCRIT.** Il serait
  commode d'écrire « sans elle, la preuve d'empilement tombe ». C'est FAUX :
  un `globalCompositeOperation = "multiply"` vif rend **exactement les mêmes
  octets**, sur fond opaque comme sur fond transparent (empreintes égales au
  banc RGBA), donc le même verdict §4.2. Ce qu'elle achète est la SUITE
  D'OPÉRATIONS — la couche du cadre ne demande jamais autre chose que
  `source-over` — et c'est cela que le banc de §4.2 sait vérifier (il REFUSE
  un mode qu'il ne modélise pas). Un test épingle l'égalité des pixels pour
  que la phrase ne pourrisse pas : le jour où elles divergeraient, il rougit
  et la phrase se réécrit dans le bon sens. *(Même famille que T3-F1 : la
  prose remise à la mesure, zéro octet livré ne change.)*
- **BANC_EMPILEMENT étendu, et il conduit le VRAI peintre** : `save/restore`,
  `globalAlpha` et `drawImage(img, dx, dy, dw, dh)` ajoutés au contexte
  minimal, la tranche de mod-frame.js chargée en 4e argument, `face: "back"`.
  Sur un verso custom à multiply la couche « cadre » reste **isolée** (là où
  le Sceau la faisait basculer en empreinte) et **porte les pixels de
  l'image** : le pixel central de la couche livrée vaut l'image MULTIPLIÉE
  PAR ELLE-MÊME (le calque est posé sur l'image de fond), ce qui prouve d'un
  coup que l'export par couches livre le verso (§6.2ter, conséquences).
- **CADRAGE « COVER » DEPUIS LE BORD DE TOILE**, pas depuis la coupe : une
  image calée sur la seule rogne laisserait la matière de bande dans les 3 mm
  de fond perdu, et un massicot décalé d'un millimètre poserait ce liseré sur
  l'arête de la carte livrée. Mutant « cover sur la coupe » tué sur les
  pixels des quatre coins de toile.
- **Le verso personnalisé remplace le MOTIF, pas le CADRE** : filets,
  ornements de coin et nom du jeu restent (ce dernier a son interrupteur) ; il
  est peint AVANT `matter()` — le carton est le même des deux côtés de la
  carte ; le MÉDAILLON central, lui, est un meuble du catalogue et ne vient
  pas s'écraser au milieu de l'image de l'utilisateur.
- **Route jumelle, jamais un appel** (règle 8) : `POST/GET frame/image` →
  `decks/{did}/frame/img_{n}.png`, avec le quintette 3b (réservation
  `O_CREAT|O_EXCL` + temporaire à jeton, bombe de pixels lue à l'EN-TÊTE,
  liste blanche `fullmatch` DANS la fonction qui compose le chemin, compteur
  MAX+1, plafond 8 recompté après réservation). **Pas de route de
  suppression** : une image encore référencée effacée d'un clic ferait un
  damier sans rien pour le défaire — le ramassage des orphelines reste la
  dette consignée.
- **PURGE AU MODÈLE, décision 5 tranchée et justifiée** : `back`,
  `back_image` et `back_layers` sont ADMIS à l'allow-list (ils y arrivent
  TOUT SEULS — elle dérive des habillages d'archétype, où les deux clés
  naissent vides) ; `back: "custom"` VOYAGE (le jeu instancié dit « ce dos est
  une image à toi » au lieu de retomber en silence sur un motif) ; les `src`
  sont VIDÉS et **les calques LÂCHÉS ENTIERS**. Raison mesurée : un calque n'a
  rien d'autre que son fichier — opacité, échelle et fusion décrivent COMMENT
  montrer une image absente. Les garder rendrait le modèle avec jusqu'à six
  rangées mortes à supprimer une par une. C'est l'inverse exact du choix fait
  pour les TEXTES des slots (doctrine 3 de models.py) et **pour la même
  raison** : là, purger casse la mise en page ; ici, garder la peuple de
  fantômes. La note part dans le `hint` — l'endroit où l'on choisit un modèle
  dans la galerie — et SEULEMENT si quelque chose a été perdu (invariant 2c).
  Le même filtre joue aux DEUX passages (écriture depuis un jeu, lecture d'un
  fichier déposé à la main).
- **DEUX SEUILS DE LA PIÈCE AMENDÉS À LA SOURCE, portée RESSERRÉE plutôt
  qu'ouverte.** `test_le_module_ne_charge_aucune_image` interdisait `new
  Image` / `createImageBitmap` dans tout le fichier — ce qui interdit
  §6.2ter. Ce que le seuil protège n'est pas « aucun décodeur d'image », c'est
  « LE CADRE n'a pas de résolution » : deux chargeurs sont désormais admis,
  NOMMÉMENT et à **un seul endroit chacun** (assertion de comptage), tandis
  que `data:image/`, `<img>`, `createElement('img')` et `createPattern` — une
  texture de cadre déguisée — restent interdits PARTOUT, et le dépôt ne livre
  toujours aucun bitmap. Même resserrage pour le panneau de preuve.
- **UN MUTANT SURVIT, ET IL A RAISON** : retirer la garde d'ENTRÉE du plafond
  (`if n >= BACK_IMAGES_MAX`) ne fait rougir aucun test — le recompte d'APRÈS
  la réservation tient encore la ligne. Elle n'est donc pas la défense, elle
  est la politesse (refuser avant de décoder 64 Mo pour rien) : écrit dans le
  code à l'endroit exact plutôt que d'inventer un test qui ferait semblant de
  le tuer. Le mutant qui relève la CONSTANTE, lui, meurt.
- **Mutants : 14 tués / 15** (blend vif · ordre trié · fond qui ne pèse plus ·
  cover sur la coupe · alias du schéma · damier retiré · O_EXCL retiré ·
  plafond relevé · compteur qui reprend les trous · `fullmatch` → `match` ·
  bombe non lue à l'en-tête · liste blanche du lecteur retirée · purge
  abandonnée · note supprimée).
- **Cache d'images : clé = le seul NOM DE FICHIER, et le fait dont ça dépend
  est ÉPINGLÉ AILLEURS.** `img_1.png` existe dans tous les jeux ; ce qui
  empêche le mélange n'est pas dans P2, c'est `galGo()` du CORE, qui RECHARGE
  la page (`location.assign`, repli `location.reload`). Un test lit le corps
  de `galGo` : le jour où le CORE échangerait le document en place, il rougit,
  et c'est là qu'une clé de jeu s'ajoute.
- **Net déclaré, AU-DESSUS DE LA CIBLE et dit** : mod-frame.js **+612/−21 =
  +591** (5450 → 6041) à la ronde 1, **+55 de plus à la ronde de revue**
  (6041 → 6096, soit **+646 au total**), pour une cible « viser court ».
  Mesuré après une passe de rasage : 175 lignes de commentaire, 422 de
  code, 19 vides. La tâche pose
  TROIS choses d'un coup — un schéma à deux normaliseurs, un peintre avec son
  cache d'images et sa cuisson, et une liste d'interface complète avec import
  (dépôt / collage / fichier) — là où la T1 n'en posait qu'une (+422 pour une
  cible ≤ 350). mod-frame.css 199 → 225. Un délestage futur prendrait la
  liste de calques ; il n'y a pas de sidecar JS possible (règle 1).
- **Reste d'œil pour la T6** : un vrai import au navigateur (dépôt, collage,
  fichier) ; la lisibilité de la liste de calques sur un panneau étroit.

### Ronde de revue adverse T4 (23/08) — 4 FIX-FIRST + les nits

La revue a rendu quatre corrections de fond. **Les pixels étaient sains ;
trois PHRASES ne l'étaient pas, et un défaut réel se cachait derrière la
quatrième.** Toutes RED d'abord, toutes tuées par mutation. Suite `cards_frame`
215 → 220, `cards_models` 160 → 161. **12 mutants sur 12.**

- **F1 — LE DAMIER D'UN CALQUE MORT EFFAÇAIT LA CARTE, et le commentaire
  promettait le contraire.** La boîte passait par le cadrage du calque avec une
  image 1 x 1, c'est-à-dire un « cover » CARRÉ du côté le plus LONG de la
  toile. Mesuré à poker : `[-147,5 ; 0 ; 1110 ; 1110]` — toute la carte, et
  **0 point d'échantillon sur 6** gardait l'image de fond. Le code disait
  « pas sur toute la carte, sinon on effacerait l'image de fond » en faisant
  exactement cela. Mon test ne pouvait pas le voir : son cas de calque mort
  n'avait PAS de fond et n'assertait que les textes. Correctif : un ENCART
  CENTRÉ et NOMMÉ (« calque 3 manquant » + le fichier, 62 % × 18 % de la
  coupe) ; le damier de l'IMAGE DE FOND, lui, garde la toile entière — quand
  c'est le fond qui manque il n'y a rien à laisser respirer. Trois mutants
  (boîte pleine toile · encart appliqué AUSSI au fond · rang non dit).
- **F2 — « exactement les mêmes octets » était FAUX pour un calque semi-
  transparent.** Le premier pin ne faisait varier que la COULEUR, jamais
  l'ALPHA — et `_decode_bounded` garde la bande alpha PAR CHOIX (« sa
  transparence porte »), donc un calque translucide est une entrée de premier
  rang. Mesuré : à alpha 64, un canal diffère d'**un niveau**. L'algèbre est
  exacte (re-dérivée à la main contre la formule W3C) ; l'écart est la
  QUANTIFICATION — la cuisson passe par `getImageData`/`putImageData`, donc
  par un aller-retour en entiers 8 bits, là où le compositeur garde ses
  flottants. La phrase est qualifiée aux TROIS endroits (code, test, cette
  note) : **mêmes octets à ±1 niveau, EXACTEMENT les mêmes pour un calque
  opaque** — et le pin porte désormais un cas translucide (écart borné à 1,
  asserté ; vérifié non vacuux : le cas mesure bien 1). *Zéro octet livré ne
  change.*
- **F3 — `bnum` était porteur, mais le mutant `bnum` → `num` SURVIVAIT.** Les
  7 corps hostiles ne donnaient jamais `opacity: null` ni `""` — LE cas que
  `bnum` existe pour fermer. Mesuré : `{"opacity": null}` → **0 à l'écran
  contre 1,0 au backend** ; un calque qui DISPARAÎT sur la carte pendant que le
  serveur le croit opaque. C'est la divergence `width_mm: null` de la T1, sur
  une autre clé. `null` / `""` / `"  "` / `[]` entrent dans la batterie ; le
  mutant meurt.
- **F4 — divergence RÉSIDUELLE sur les chaînes numériques, dans le produit
  livré.** `Number()` et `float()` ne lisent pas les mêmes chaînes : « 0x10 »
  vaut 16 en JS et lève en Python (→ **échelle 4 à l'écran contre 1,0 au
  backend**) ; « 1_0 » vaut 10 en Python et NaN en JS (→ **1 contre 4,0**).
  Atteignable par un fichier de jeu édité à la main — le scénario que ce dépôt
  traite partout ailleurs. `BACK_NUM_RE` (`^-?\d+(\.\d+)?$`) borne les DEUX
  côtés à la seule forme que les deux langages lisent identiquement ; les
  quatre formes sont dans la batterie, deux mutants tués (un par côté).
- **N3, ET LE DÉFAUT ÉTAIT DANS LES DEUX MAGASINS** : un jalon de réservation
  de zéro octet (la fenêtre `os.close` → `os.replace`, qu'une panne dure
  traverse) était **SERVI en 200, corps vide, `Cache-Control: immutable`** —
  un an de cache sur un fichier vide. Hérité mot pour mot par P2 de sa jumelle
  `type.py`, donc corrigé dans LES DEUX (`return data or None`, dans la
  fonction qui compose le chemin). **Le NUMÉRO, lui, reste compté au plafond,
  et c'est le choix assumé** : ce que le plafond protège est le numéro, pas
  les octets ; un jalon a pris le sien et le compteur MAX+1 ne le réattribuera
  jamais. Le refus dit déjà le geste (supprimer le fichier du dossier du jeu).
- **N4** : la note du verso était câblée sur l'écriture mais pas sur la
  LECTURE — or le filtre joue aux deux passages, et un fichier déposé à la
  main était purgé en silence. La raison de la note ne dépend pas du sens dans
  lequel on traverse : câblée dans `_normaliser_perso`, témoin compris.
- **N5** : la toile de cuisson (~21 Mo en tarot 600 DPI) fuyait si une
  exception traversait la pile — et le CORE ATTRAPE les exceptions de painter,
  donc la fuite aurait été silencieuse et répétée à chaque frame. `try/finally`.
- **N6** : `drawBackLayer` / `backLayerRect` relisaient l'opacité et l'échelle
  au générique `num()` — un SECOND lecteur qui rouvrait le piège de F3.
  Inatteignable aujourd'hui (le painter ne reçoit que du `st()` normalisé),
  une ligne pour le prochain appelant.
- **LE PIÈGE DU GREP DE PROSE, ATTRAPÉ UNE FOIS DE PLUS.** Le premier pin de
  N5 cherchait le mot « finally » — que le commentaire du code emploie pour se
  justifier. Le mutant qui SORT la libération du `finally` a donc SURVÉCU, en
  laissant sa propre prose le couvrir. Ré-ancré sur la structure (`} finally {`
  après retrait des commentaires) et re-tué. Même leçon qu'en 3c-T3 : un grep
  de prose est un cliquet, pas une preuve.

**CONSIGNÉ POUR LA SUITE (nits de portée, avec leur raison) :**

- **N1 — le dos PAR CARTE peut être « personnalisé », et il REND.**
  `back_same` décoché fait lire `card.back` (colonne du CSV, pièce 04) et le
  catalogue accepte « custom » : une carte peut donc porter le verso
  personnalisé alors que le jeu porte un motif. C'était atteignable et MUET :
  ni test, ni ligne de plan. Désormais TESTÉ (le dos EFFECTIF `backOf` est ce
  que `paintBack` lit ET ce que le painter attend — mutant tué sur ce second
  point). **Ce qui ne suit pas, et c'est la décision** : les FICHIERS restent
  ceux du jeu (`doc.frame.back_image`), donc une carte à dos personnalisé rend
  le verso personnalisé DU JEU. Une image PAR CARTE demanderait une colonne de
  plus et un magasin par carte — **hors 3c**. L'affordance du panneau (la zone
  d'import est gated au niveau du jeu) part avec elle : à reprendre en 3d avec
  le vocabulaire par carte, pas à bricoler ici.
- **N2 — LE COÛT DE LA CUISSON DÉPASSE LE BUDGET DU PAINTER dans le pire cas,
  et c'est chiffré.** Mesure de la revue : tarot 1200 DPI, **1536 ms par
  calque à multiply** — six calques font **~9,2 s** contre les **4 000 ms**
  que le CORE laisse à un painter (`PAINTER_MS`). Au-delà, le painter est
  coupé et la couche est perdue avec un bandeau. Ce n'est PAS atteignable au
  réglage livré (300 DPI, une poignée de calques) mais ça l'est en poussant les
  deux curseurs. Remèdes possibles, non construits : borner la cuisson à
  l'INTERSECTION du calque avec la toile (sans effet à l'échelle ≥ 1), cuire à
  définition réduite pour l'aperçu et à pleine définition pour l'export, ou
  refuser le 6e calque à multiply au-delà d'une définition. **À trancher en
  T6 avec une mesure fraîche sur la machine de l'atelier.**
- **N7 — GC, un cas de plus pour la dette déjà consignée** : supprimer une
  rangée de calque PENDANT un import en vol laisse le fichier orphelin sur l'un
  des 8 emplacements (l'import aboutit et écrit son PNG ; plus rien ne le
  référence). Aucune route de suppression n'existe, donc l'emplacement est
  perdu jusqu'à un ménage manuel dans le dossier du jeu. À joindre au
  ramassage des images orphelines de la T6.

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
