# Cardforge — phase 3a : fondations archétypes (modèles serveur, plaque P3, familles P2, galerie)

Phase 3 lancée par l'utilisateur le 22/08 (« ok lance la phase 3 »). Découpée en
trois sous-phases livrables seules : **3a (CE plan)** = les 7 archétypes
instanciables en decks ordinaires ; 3b = l'édition directe type Figma complète
(§6.1 — palette d'ajout, liste de calques, côté P2) ; 3c = Sceau prismatique
complet (§6.2bis a/b/d) + verso custom (§6.2ter) + IA cadres (§6.3) + dettes
héritées (N2/N4/N7 2c, résidus molette 2b).

Source de vérité : spec §6 (docs/superpowers/specs/2026-08-19-cardforge-universel-design.md:280-484).
Toute divergence découverte s'amende À LA SOURCE (leçon ×7 des phases 2).

## Faits de reconnaissance (22/08, ancres vérifiées)

- **P3 slots** : 32 clés par slot (`SLOT_DEFAULTS`, mod-type.js:109-117 miroir
  type.py:382-430, parité = ÉGALITÉ JSON stricte — le bloc JS est du JSON
  littéral, test_cards_type.py:158-168) ; **AUCUN champ de plaque de fond**
  (grep plate/plaque/bg = 0) — le gap §6.1:299-300 exact. 4 presets
  (champion/sort/arcane/minimal, bloc CF-TYPE-PRESETS). Painter unique z=60,
  async (fontes), mod-type.js:1136-1155.
- **La manipulation directe P3 EXISTE déjà en partie** : calque flottant
  (mod-type.js:4012-4205) — 8 poignées `HANDLES=[nw,n,ne,e,se,s,sw,w]`, drag à
  pointer-capture + patch coalescé rAF (patron core.js:158), snap 0,25 mm
  (Alt le lève), flèches 0,5 mm / Maj 5 mm / Alt=redimensionner. La 3b
  s'appuiera dessus ; la 3a n'y touche pas (sauf le rendu de la plaque).
- **P2** : 6 familles (runic/arcane/timber/deco/neon/sable), blocs
  CF-FRAME-CATALOG (mod-frame.js:32-113 ↔ frame.py:67-119, parité par tuples
  id/label), `FAM_FN` (mod-frame.js:1380) + `WIN_SHAPE` (:161) + PROFILE
  JS-seuls ; **QA de silhouettes** : `SIL_SEUIL = 4` (mod-frame.js:2785,
  épinglé test_cards_frame.py:2242), pire couple mesuré 4,94/255 sur toile
  livrée (:2762) et 8,12 « Runique × Neon » en Mythique sur vignettes
  (:2717-2718) — une famille nouvelle NE DOIT PAS dégrader le pire couple
  sous le seuil (mesuré, pas décrété). Le dos = `paintBack` if/else
  (mod-frame.js:1608-1679). doc.frame = 28 clés réelles (DEFAULTS :123-142 ;
  le commentaire « 22 clés » à :205 est PÉRIMÉ — le corriger en passant).
- **Deck/routes** : création `POST /api/cards/decks` → `default_doc` donne des
  sous-arbres `{}` VIDES (core.py:140-149, 344-354) ; `PATCH /{did}` =
  remplacement de sous-arbre entier (jamais de merge profond, core.py:244-276)
  — l'instanciation d'un modèle = create + pré-remplissage des sous-arbres par
  la MÊME écriture. **Aucune route /models**. Le routeur cards vit dans
  cards/__init__.py:45-78 (core AVANT le joker /{did}). P4 ne sème AUCUNE
  carte (data.py = moteur de mapping, pas de seed).
- **Tailles (risque de délestage)** : mod-frame.js 4857 l., mod-type.js
  4206 l. — les familles/presets nouveaux doivent rester des AJOUTS de
  données + petites fonctions, pas des refontes ; frame.py 1253 / type.py
  1109 / core.py 436 : marge saine côté backend.

## Décisions de conception 3a

1. **Le modèle SEED un deck ordinaire** (§6.1 actée) : un modèle est un JSON
   serveur `{id, label, hint, format, frame:{…}, type:{preset, slots:[…]},
   palette, finish, texture:{…}, elements:[…]}` — source UNIQUE côté serveur
   (données, PAS de table miroir JS ; l'écran consomme `GET models`).
   L'instanciation écrit les sous-arbres par le PATCH existant — après quoi le
   deck est indiscernable d'un deck construit à la main. `elements` (presets de
   slots ajoutables) est EMBARQUÉ dès la 3a (données prêtes) ; l'UI qui pioche
   dedans est la 3b.
2. **Les zones §6.2 sont la loi** : chaque modèle transcrit SES zones en mm
   (poker 63×88) depuis la spec :318-357 — slots P3 (boxes mm depuis le coin
   rogné, patron type.py:34-35) + réglages frame/palette/typo par archétype.
   Les polices citées (Oswald, Nunito, Cinzel…) : n'utiliser QUE celles que
   `ensureFonts` sait charger — vérifier la liste réelle des fontes du lab et
   REPLIER nommément (le modèle dit « Oswald→repli Archivo Black » si absente,
   jamais un échec silencieux).
3. **Familles P2 : la MESURE décide, pas le catalogue de la spec** — pour
   chaque archétype, d'abord essayer d'habiller avec les 6 familles réelles
   (le modèle règle famille+rareté+métal+coins+bannière…) ; créer une famille
   NOUVELLE seulement quand aucun habillage n'approche la signature §6.2
   (attendu : « gravée » exige le double filet 1,5/3 mm — famille nouvelle
   probable ; « superstar » la plaque à pans coupés — `deco` (chamfer) à
   éprouver d'abord). CHAQUE ajout re-mesure la QA de silhouettes (les DEUX
   surfaces : vignettes et toile livrée) et la note de tâche PUBLIE le
   nouveau pire couple.
4. **Galerie de démarrage** (§6.4) : écran CORE léger — « nouveau deck depuis
   modèle » (les 7 + modèles perso), « reprendre un deck » (GET /decks enfin
   consommé), « importer une carte » = bouton PRÉSENT mais refus nommé
   (« phase 4 — l'import arrive ») ; duplication + « enregistrer comme
   modèle » (sans illustrations) au même écran. Le renommage existe déjà.
5. **Modèles perso** : `{DATA_ROOT}/cardforge_models/*.json`, mêmes clés que
   les modèles d'usine + `custom: true` ; « enregistrer comme modèle »
   sérialise format/frame/type/palette/texture du deck courant, JAMAIS les
   illustrations (spec :481-484).

### Task 1 : P3 — la plaque de fond par slot

**Files:** mod-type.js, type.py, test_cards_type.py (+ mod-type.css si besoin).

- [x] RED : parité JSON des DEFAULTS étendus ; un slot avec
      `plate_color/plate_alpha/plate_radius` rend une plaque SOUS le texte
      (pixels mesurés au painter : coin de plaque teinté, texte par-dessus) ;
      plaque à alpha 0 = aucun pixel ; les 32 clés existantes inchangées
      (l'égalité JSON des deux côtés est le verrou).
- [x] `SLOT_DEFAULTS` += `plate_color` (hex ou null = pas de plaque),
      `plate_alpha` (0..1), `plate_radius` (mm, borné LIMITS) — DEUX côtés,
      JSON littéral. Le painter z=60 dessine la plaque AVANT le texte du slot
      (même passe, même clip de boîte). Les presets existants restent
      byte-identiques (nouvelles clés aux défauts neutres).
- [x] Panneau : les 3 réglages dans l'éditeur de slot existant (patron des
      réglages voisins) ; l'aperçu réagit.
- [x] Mutation : plaque après le texte (le texte disparaît sous la plaque →
      pixel-test rougit), alpha non appliqué, rayon non borné.

> **Livré (T1)** — 32 → **35 clés** par slot, l'égalité JSON stricte tenue des
> deux côtés (`plate_color: null` / `plate_alpha: 1.0` / `plate_radius: 0.0`,
> mod-type.js:114-115 ↔ type.py:424-436). Bornes NOMMÉES côté serveur
> (`PLATE_ALPHA_MIN/MAX` 0..1, `PLATE_RADIUS_MIN/MAX` 0..30 mm,
> type.py:474-479) ; **il n'existe pas de miroir LIMITS pour les slots** — le
> patron du fichier est `_num(v, def, lo, hi)` côté Python et `num(v, d, lo, hi)`
> côté JS avec la seule constante partagée quand elle sert au dessin
> (`PLATE_RADIUS_MAX_MM`, mod-type.js:227). Le painter z=60 pose la plaque dans
> `drawSlot`, APRÈS la rotation du slot et AVANT les passes d'ombre/contour/
> glyphes (mod-type.js:1157-1161) : une plaque suit son slot quand on le tourne.
>
> · **La boîte du painter, pas la boîte dégonflée.** La plaque prend `m.box`
>   (la boîte du slot en pixels de toile), pas la boîte rétrécie par la marge
>   optique : c'est le FOND du bloc, il doit border le texte.
> · **Rayon borné AU DESSIN** (`Math.min(mm2px(r), w/2, h/2)`) et pas seulement
>   à la saisie : le painter reçoit les slots du document TELS QUELS — un
>   modèle de la T3, un import, une main dans le JSON — `normSlot` ne sert que
>   le panneau. Prouvé au pixel (rayon 9999 → le coin n'est plus peint, le
>   centre l'est ; mutant « rayon non borné » tué).
> · **DÉFAUT NON PRÉVU PAR LE PLAN, trouvé en écrivant l'implémentation :**
>   trois passes redessinent un slot SEUL pour mesurer son ENCRE (contrôle
>   photométrique :3410, bbox du halo :3704, relevé sur fichier :3908). La
>   plaque y aurait rendu CHAQUE pixel de la boîte « corps de glyphe » — taux
>   de masquage et contraste auraient rendu n'importe quoi, sans rougir nulle
>   part. Les trois neutralisent désormais `plate_color: null`, au même titre
>   que l'ombre et l'opacité, et un test compte les trois. Dans le COMPOSITE la
>   plaque reste : c'est même le bon fond à mesurer derrière le texte.
> · **Un slot VIDE ne peint pas sa plaque** (elle vit dans `drawSlot`, sous la
>   garde `if (!m.empty)` que la pièce s'est donnée en 03). Assumé : un slot
>   dont le texte ET le défaut sont vides est un « rien ici » explicite. À
>   savoir pour la T3 — un modèle qui veut une plaque toujours visible donne un
>   `text` par défaut à son slot.
> · **Panneau** : groupe `Plaque de fond`, ouvert, inséré AVANT `Contour,
>   ombre, arc` (l'ordre épinglé de l'inspecteur ne bouge pas). Widgets =
>   patrons voisins EXACTS : `input[type=color]` comme la couleur de contour +
>   deux `nfield`. **Écart assumé au brief** : pas de curseur pour l'alpha —
>   l'inspecteur de P3 n'a AUCUN `input[type=range]` (mod-solid en a, pas
>   celui-ci), en poser un demandait du CSS neuf et un second chemin de
>   câblage. Ajout non demandé mais nécessaire : bouton **« Sans plaque »** —
>   un `input[type=color]` ne sait pas dire « rien », sans lui une couleur
>   posée par erreur ne se reprenait plus.
>
> **Le banc de pixels (nouveau).** Le banc de la section 8 NOTE les appels de
> dessin : il ne peut RIEN dire d'un recouvrement, donc rien de l'ordre
> plaque/texte. Un second banc (`BANC_PLAQUE`, test_cards_type.py:2882) donne
> au painter un contexte 2D qui COMPOSITE pour de vrai — source-over,
> `globalAlpha`, transformations affines, rect arrondi rasterisé par test
> d'appartenance — dans un tampon RGBA de la taille de la toile. Les glyphes y
> sont les pavés pleins de la chasse mesurée : ce qu'on juge n'est pas la forme
> d'un « e », c'est qui recouvre quoi. Mesures : pixel libre = (48,80,160,**204**)
> — la couleur et l'alpha demandés ; pixel de corps de glyphe = (239,231,214,255)
> — l'encre, donc la plaque est passée dessous.
>
> **100 → 108 verts** (7 tests neufs, 1 amendé pour 35/30 clés). Lint intégral
> 0 violation, `node --check` OK, suites voisines vertes (core/data/face/print).
> Mutations tuées, fichier entier à chaque fois : plaque APRÈS le texte (le
> glyphe vire au bleu de la plaque) · `plate_alpha` ignoré (l'alpha du pixel
> libre quitte 204) · rayon non borné (le coin reste peint à rayon 9999).

### Task 2 : P2 — l'habillage des 7 archétypes (familles : mesure d'abord)

**Files:** mod-frame.js, frame.py, test_cards_frame.py.

- [ ] Pour CHAQUE archétype §6.2 (superstar, duel, créature, arcane, monstre,
      légende, gravée) : composer l'habillage avec les familles EXISTANTES
      (réglages doc.frame complets — famille, rareté, ligne, métal, coins,
      bannière, plaque…) ; si la signature est inatteignable, famille
      NOUVELLE (FAMILIES deux côtés + FAM_FN + WIN_SHAPE + PROFILE) — la
      décision est PUBLIÉE dans la note de tâche avec sa raison.
- [ ] QA silhouettes re-mesurée APRÈS chaque famille ajoutée (les deux
      surfaces) ; le pire couple publié ; `SIL_SEUIL` intouché — si une
      famille nouvelle passe sous 4, elle se REDESSINE, le seuil ne bouge pas.
- [ ] Le commentaire périmé « 22 clés » (mod-frame.js:205) corrigé en passant.
- [ ] Tests : parité catalogue étendue ; un rendu par famille nouvelle
      (pixels non vides aux bandes attendues) ; silhouette QA verte.

### Task 3 : backend — modèles, instanciation, duplication, enregistrer-comme-modèle

**Files:** backend/app/services/cards/models.py (NOUVEAU — les données + routes,
monté dans cards/__init__.py AVANT le joker), core.py (create accepte model),
test_cards_core.py ou test dédié test_cards_models.py (règle 1 : nouveau py =
nouveau test).

- [ ] `GET /api/cards/models` : les 7 modèles d'usine (données Python,
      zone-par-zone §6.2:323-354 transcrites en mm) + les modèles perso de
      `{DATA_ROOT}/cardforge_models/` (lecture tolérante : un JSON malformé
      est LISTÉ comme illisible avec son nom, jamais un 500).
- [ ] `POST /api/cards/decks` étendu : `{model: "superstar"}` → create_deck
      puis pré-remplissage des sous-arbres frame/type/texture (le PATCH
      interne existant, patron core.py:244-276) + `palette`/`finish` là où
      leur module les lit ; modèle inconnu → 404 nommé. Un deck instancié
      est ORDINAIRE (aucune référence au modèle après coup — le seed, pas un
      lien).
- [ ] `POST /api/cards/decks/{did}/duplicate` : copie du doc + des fichiers
      deck-locaux (illustrations exclues ? NON — une duplication copie TOUT,
      c'est « enregistrer comme modèle » qui exclut les illustrations) ;
      nouveau did, nom « copie de … ».
- [ ] `POST /api/cards/models` (perso) : sérialise format/frame/type/palette/
      texture du deck courant, PAS les illustrations (les slots gardent leurs
      réglages, `src`/images purgés) ; nom demandé ; écrit
      `cardforge_models/{slug}.json` (slug sûr, collision → suffixe) ;
      re-listé par GET.
- [ ] Chaque modèle d'usine VALIDÉ par test : instancier → GET /{did} → les
      slots sont dans les bornes de la carte (boxes ⊂ trim), la famille
      existe, le preset P3 est légal ; le painter rend sans erreur
      (cv.cfErrors vide) sur une carte de test.
- [ ] jamais-500 ; French messages ; fontes : repli nommé (décision 2).

### Task 4 : la galerie de démarrage (CORE, écran léger)

**Files:** core.js, cardforge.css, index.html (si ancrage), qa (pins),
mod-frame.js/mod-type.js NON touchés.

- [ ] Un panneau « Modèles » accessible depuis la topbar (patron des boutons
      existants) : cartes-vignettes des 7 modèles d'usine + perso (vignette =
      rendu miniature du modèle par le VRAI moteur `CF.renderCard` sur un
      deck éphémère ? NON — trop lourd : vignette statique servie par
      GET /models (`thumb` optionnel) ou dessin procédural léger ; décision
      implémenteur, publiée) ; « nouveau deck depuis ce modèle » → POST +
      bascule sur le deck créé ; « reprendre un deck » (liste GET /decks avec
      dates) ; « importer une carte » → refus nommé phase 4 ; « dupliquer » ;
      « enregistrer comme modèle ».
- [ ] Le registre gelé du CORE intouché (MODULES, freeze) ; les octets de
      core.js vérifiés après édition (leçon 19/08) ; pins de contrat (les
      boutons existent, la galerie s'ouvre/se ferme, AUCUNE géométrie dans le
      harnais).
- [ ] R13 sur les fichiers touchés ; l'escamotage T3-2d non régressé (pins
      existants verts).

### Task 5 : intégration 3a

- [ ] Suite complète cards 10/10 (+ test_cards_models si fichier neuf → 11),
      lint intégral 0, contrat complet, node --check.
- [ ] cf_deploy -Backend + -Check 0 écart ; navigateur réel : galerie →
      instancier « superstar » → le deck s'ouvre habillé (frame+type+palette),
      slots visibles aux zones §6.2, plaque de fond rendue ; dupliquer ;
      enregistrer comme modèle → re-listé → instancier LE PERSO ; « importer
      une carte » → refus nommé. QA silhouettes finale publiée.
- [ ] Plan+mémoire+push ; restes à l'œil (fidélité visuelle des habillages
      par archétype — jugement esthétique utilisateur).

## Auto-revue du plan

- Les zones §6.2 sont transcrites une fois, côté serveur (source unique) ;
  l'écran ne recopie jamais la table (patron « données, pas miroir »).
- La plaque P3 (T1) précède les modèles (T3) qui l'utilisent ; les familles
  (T2) précèdent les modèles qui les référencent ; la galerie (T4) consomme
  T3. L'ordre 1→2→3→4→5 est sans rebase.
- Risques nommés : la QA de silhouettes comme ARBITRE des familles nouvelles
  (mesurée après chaque ajout, pire couple publié) ; l'égalité JSON stricte
  de P3 (le bloc JS doit rester du JSON littéral) ; core.js gelé + octets ;
  les fontes des archétypes (repli nommé, jamais silencieux) ; mod-frame.js
  à 4857 l. (les familles = données + petites fonctions, PAS de refonte —
  si une tâche dépasse ~300 l. nettes dans ce fichier, elle le DIT et on
  découpe).
- Hors périmètre 3a, consigné : palette d'ajout d'éléments + liste de
  calques + côté P2 de la manipulation directe (3b) ; Sceau écran/impression/
  portée/motifs (3c) ; verso custom (3c) ; IA cadres (3c) ; « taverne »
  (2e fournée, spec) ; dettes N2/N4/N7 + molette 2b (3c).
