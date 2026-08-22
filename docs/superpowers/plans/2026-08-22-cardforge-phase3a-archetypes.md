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

> **CLOSE (T1 — 7fd0811, revue combinée : MERGEABLE AS-IS, zéro ronde).** Le
> réviseur a mesuré AU-DELÀ des tests livrés : rotation+plaque prouvée par
> balayage (boîte 213→485 px, aire conservée ~constante), le double-clamp du
> rayon PORTEUR (sans le clamp-boîte : couverture 73 %→51 %),
> `opacity × plate_alpha` MULTIPLIE (alpha mesuré 102 = 0,5×0,8×255 exact,
> jamais un remplacement) ; les clamps serveur sondés sous 8 entrées hostiles,
> parité ligne-à-ligne. 2 mutants re-dérivés indépendamment sur copies.
> *Consigné pour la 3b (non bloquant)* : la branche `arcTo` de repli de
> `platePath` n'est pas exerçable par le banc actuel (son contexte ne suit pas
> moveTo/arcTo — l'ajouter demanderait l'accumulation de chemin) ; les 3
> neutralisations d'encre sont des COPIES comptées (`count == 3`) — une 4e
> passe d'encre future qui oublierait `plate_color: null` passerait en
> silence : helper partagé à envisager quand la 3b touche ces passes ; le
> filtre de noms R14 (`Html|paint`) ne balaie pas `renderInsp` — élargir le
> filtre au lint (1 ligne, vérifié sûr à la main aujourd'hui).

### Task 2 : P2 — l'habillage des 7 archétypes (familles : mesure d'abord)

**Files:** mod-frame.js, frame.py, test_cards_frame.py.

- [x] Pour CHAQUE archétype §6.2 (superstar, duel, créature, arcane, monstre,
      légende, gravée) : composer l'habillage avec les familles EXISTANTES
      (réglages doc.frame complets — famille, rareté, ligne, métal, coins,
      bannière, plaque…) ; si la signature est inatteignable, famille
      NOUVELLE (FAMILIES deux côtés + FAM_FN + WIN_SHAPE + PROFILE) — la
      décision est PUBLIÉE dans la note de tâche avec sa raison.
- [x] QA silhouettes re-mesurée APRÈS chaque famille ajoutée (les deux
      surfaces) ; le pire couple publié ; `SIL_SEUIL` intouché — si une
      famille nouvelle passe sous 4, elle se REDESSINE, le seuil ne bouge pas.
- [x] Le commentaire périmé « 22 clés » (mod-frame.js:205) corrigé en passant.
- [x] Tests : parité catalogue étendue ; un rendu par famille nouvelle
      (pixels non vides aux bandes attendues) ; silhouette QA verte.

> **Livré (T2)** — commit `8e20d1e`, +173 lignes NETTES dans mod-frame.js (le
> plan en autorisait ~300 avant découpe), +145 dans frame.py, +631 de tests.
> Les sept habillages sont `FR.ARCHETYPE_FRAMES` (frame.py, après le bloc
> CF-FRAME-OCC) : 27 clés écrites chacun — les 28 de `DEFAULTS` moins
> `art_window`, que le painter PUBLIE. **La T3 les IMPORTE**
> (`from .frame import ARCHETYPE_FRAMES` : R8 n'interdit que d'importer le
> ROUTER d'un voisin) ; les retaper serait une seconde source de vérité.
>
> · **SIX archétypes sur sept sortent des familles déjà livrées.** superstar →
>   `deco` (la « plaque à pans coupés 4,4 → 55 × 80 » EST `edge_mm = 4` :
>   63 − 8 = 55, 88 − 8 = 80 ; les pans coupés eux-mêmes viennent de la
>   fenêtre chanfreinée et de la plaque étagée de `deco`) ; duel → `sable`
>   (plaque « epure » = le rectangle strict du tableau zébré, « PAS
>   d'ellipse », et `grad:false` = le papier mat) ; créature → `timber`
>   (seule bande de 3 mm de masse, rivets, métal or = le gros liseré) ;
>   arcane → `arcane` (arc, volutes, `edge_mm = 2,5` = la « bordure 2,5 mm »)
>   ; monstre → `runic` (fenêtre CARRÉE 47 × 47, verrou de proportions armé,
>   anneau plein ; `grad:false` rend le « cadre couleur pleine = catégorie »,
>   code propre = mythic + filet d'argent) ; légende → `sable` (anneau CLAIR
>   = la bordure blanche vintage, filet 0,35 mm, fenêtre 58 × 69,5 : la
>   plaque tombe alors à 73,8 → 84,3 mm, soit le bandeau de nom « 0,74 » de
>   la spec EN HAUTEUR — la largeur pleine 63 mm n'existe pas dans ce moteur,
>   la plaque est inscrite dans la bande ; « photo pleine page » est un
>   glissement de fenêtre, pas un autre archétype).
>
> · **UNE famille nouvelle, `gravure` (« Gravure »), pour « Arcane gravée ».**
>   Raison mesurée : il lui faut une marge de PAPIER IVOIRE et un aplat de
>   pochoir au repérage décalé de 0,2 mm. Les six familles encrent l'anneau
>   depuis `PAL`, dont les six raretés sont SOMBRES — même `sable`, le plus
>   clair, ne fait qu'ÉCLAIRCIR la rareté ; et aucune ne pose d'aplat décalé.
>   Quatre colonnes neuves : zone « ivoire », kind « burin » (croix de
>   repérage aux coins de bande + taille dans la marge basse), moulure
>   « pochoir » (aplat de 2,6 mm décalé de `POCHOIR_MM = 0,2`, le trait
>   restant à sa place), plaque « cartouche » (rectangle à coins entaillés).
>   Les quatre encres de la spec (vermillon/bleu/ocre/vert) sont les raretés
>   mythic/rare/legendary/uncommon : chez cette famille la rareté n'est plus
>   la couleur du cadre mais celle de l'ENCRE.
>
> · **AMENDEMENT AU PLAN.** Le plan attendait la famille neuve POUR le
>   « double filet 1,5/3 mm ». Il sort du moteur EXISTANT : `paintFront` pose
>   le second filet à `edge + line/2 + gap + 0,3·line`, donc edge 1,5 +
>   line 0,5 + gap 1,1 = **3,00 mm pile**, le premier restant sur son axe à
>   1,5 mm. Ce n'est donc pas le filet qui justifie `gravure` — la raison
>   publiée (ivoire + décalage) est la vraie, et un test verrouille
>   l'arithmétique pour que personne ne recopie la supposition.
>
> · **QA DE SILHOUETTES, les deux surfaces, mesurées au NAVIGATEUR** (badge du
>   panneau sur l'app déployée, six raretés, masque des couches voisines
>   actif, fenêtre 1700 × 1000 pour que les vignettes restent comparables) :
>
>   | état | toile livrée | vignettes | paire la plus serrée |
>   |---|---|---|---|
>   | avant — 6 familles, 90 paires | 5,2 | 6,84 | Runique × Art déco, Mythique |
>   | 1er jet de Gravure (ivoire d'un seul ton) | **4,61** | 6,84 | **Épure × Gravure, Rare** |
>   | après REDESSIN — 7 familles, 126 paires | **5,2** | **6,84** | Runique × Art déco, Mythique |
>
>   Le premier jet restait au-dessus du seuil (4,61 ≥ 4) mais c'était la
>   famille NEUVE qui tirait le catalogue vers le bas : deux anneaux clairs
>   uniformes ne se distinguent pas sur gris normalisé, qui efface la teinte
>   et ne garde que la RÉPARTITION. La famille a donc été REDESSINÉE (anneau
>   partagé en deux par la cuvette : papier nu dehors, surface encrée dedans),
>   le seuil non touché — et le pire couple est redevenu EXACTEMENT celui
>   d'avant, à la même valeur : la septième famille n'a rien coûté au
>   catalogue. 42/42 signatures de pixels distinctes ; hors fenêtre
>   d'illustration 7,88/255, inchangé lui aussi.
>
> · **Ce que les tests ajoutent :** un RASTÉRISEUR de contrôle (banc node,
>   grille de 0,5 mm, courbes aplaties, remplissages par balayage de lignes,
>   CLIP honoré) qui fait tourner les VRAIS painters, COMPTE les cellules
>   encrées et rend l'EMPREINTE du bitmap de chaque signature de famille — les
>   familles n'avaient jusqu'ici pour juge qu'un badge d'écran, absent de la
>   suite. Il prouve au passage, en le COMPTANT, que l'anneau traverse le trait
>   de coupe et remplit le fond perdu (**1,00 pour CINQ familles** — runic,
>   arcane, timber, sable, gravure —, 0,74 pour `deco` dont seuls les bras
>   d'angle encrent, 0 pour `neon` dont la zone est « vide ») : la correction
>   du tour 4 n'était épinglée que sur le source.
>
> · **Mutations tuées** : peintre de famille vidé (ops 4 → 0 ; test PERMANENT
>   de la suite) ; entrée de catalogue retirée d'un seul côté ; mesure
>   inscrite sous le seuil ; colonnes de `PROFILE` clonées sur `sable`. Et au
>   NAVIGATEUR, la preuve que le plancher MESURÉ peut rougir : `gravure`
>   aliasée sur le painter d'`Épure` dans la copie de l'app → pire couple
>   **5,2 → 0,17/255** (vignettes 0,28), badge rouge, paire nommée
>   « Épure × Gravure ». Fichier restauré ensuite, app identique au dépôt.
>   À noter : les 42 signatures de pixels restaient « distinctes » sous cette
>   mutation (la graine de `matter` dépend de l'index de famille) — le compte
>   de signatures ne suffit pas, c'est l'écart sur gris normalisé qui voit.
>
> · **Rendu réel** : les 7 habillages instanciés dans le vrai lab (deck de
>   travail `deck_3b3b7206`, « QA 3a-2 habillages (supprimable) », laissé en
>   place) — recto ET verso rendus par `CF.renderCard`, `cv.cfErrors` VIDE
>   partout, aucune `pageerror`, aucune boîte d'erreur d'écran, et
>   `frame.art_window` publiée = la zone §6.2 au dixième de mm pour les six
>   archétypes qui en citent une (légende n'en cite pas : sa fenêtre est un
>   choix d'implémenteur, publié ci-dessus).
>
> · **⚠ CE QUI N'EST GARDÉ PAR AUCUN TEST — À LIRE AVANT DE TOUCHER UNE
>   FAMILLE.** Le redessin de la cuvette (4,61 → 5,2) n'a **aucune protection
>   en intégration** : le rastériseur est DALTONIEN par conception — il compte
>   des cellules encrées, il ne juge pas les TONS, et c'est justement un écart
>   de tons entre deux anneaux clairs qui avait fait tomber le chiffre. Le
>   seul instrument qui voit cela est le badge « silhouettes » du panneau, qui
>   tourne dans un navigateur, hors CI. **Qui modifie une famille (couleurs,
>   masses, zone, moulure) DOIT rouvrir le volet Cadre et relire le badge** ;
>   la suite, elle, ne verra rien. Ce qu'elle garde, en revanche : que deux
>   familles ne DESSINENT pas la même chose (empreintes deux à deux
>   distinctes) et que le pire couple PUBLIÉ reste au-dessus du seuil.
>
> · **Restes à l'œil (jugement esthétique utilisateur, hors mesure)** : la
>   fidélité visuelle de chaque habillage à son archétype, et le fait que les
>   captures montrent les habillages SOUS les slots du deck de test — la T3
>   posera les slots de l'archétype.
>
> **Ronde adverse (22/08, après livraison)** — la revue a rendu FIX-FIRST et
> avait raison sur trois points sérieux ; tout est corrigé dans le même
> fichier de tests, painter et habillages indemnes (chaque nombre re-dérivé).
> · **La leçon publiée n'était pas ARMÉE** : « le compte de signatures ne
>   suffit pas » était écrit mais rien ne le tenait — aliaser
>   `deco: famDeco → famRunic` laissait **154/154 VERTS**. Le banc rend
>   désormais l'EMPREINTE (FNV-1a) du bitmap de signature et la suite exige
>   les sept **deux à deux distinctes** — relevé re-dérivé indépendamment,
>   identique au chiffre pour chiffre de la revue : runic `9eb83889`:1134,
>   arcane `185c2317`:230, timber `37b9d043`:1972, deco `b33056cd`:520,
>   neon `e47ffc52`:591, sable `29a699ed`:24, gravure `80e086d5`:386. Plus un
>   contrôle négatif permanent (l'alias, joué sur la COPIE du banc, doit rendre
>   deux empreintes ÉGALES) et l'exigence que `FAM_FN` porte sept peintres
>   distincts. Mutation re-jouée : l'alias **TUE** maintenant deux tests.
> · **Le banc dessinait une plaque que le fichier ne porte pas** : `paintFront`
>   exige `m.plate.h > u * 6`, le banc non. Mesuré : une fenêtre de « gravée »
>   à 63 mm laisse **5,0 mm** de plaque — painter muet, banc qui lisait
>   **0,9774**. La garde est reflétée, et les sept habillages épinglent
>   maintenant `plaque_mm > 6` : **« gravée » livre 7,0 mm, à 1 mm de la
>   falaise** — la prochaine retouche de fenêtre le saura.
> · **La seule géométrie choisie à la main n'était pas épinglée** : `legende`
>   manquait à la table des fenêtres attendues (w 58 → 40 restait vert). Elle y
>   est, avec sa raison (« pas de zone §6.2 — choix d'implémenteur »).
> · Aussi : cas « /dos » renommés **« /miroir »** avec une docstring honnête
>   (six des sept dos sont des MOTIFS, hors de la tranche extraite, non
>   mesurés) ; `POCHOIR_MM = 0,2` — la raison publiée de la 7e famille —
>   épinglé au source (0,2 mm = 2,36 px, la grille de 0,5 mm ne peut pas le
>   voir) ; `win_lock` de « monstre » lié à sa fenêtre CARRÉE par un test ;
>   deux commentaires du banc qui surclamaient corrigés (il n'appelle PAS
>   `matter()` — ses hachures saturent une grille de 0,5 mm — et il ne mesure
>   pas les dos à motif) ; « 3,2 mm » et « 2,6 mm » du pochoir désambiguïsés
>   (bord externe depuis la fenêtre vs LARGEUR de l'aplat).
> · Mutations de la ronde, toutes **TUÉES** : alias deco→runic · garde de
>   plaque retirée · fenêtre de légende 58→40 · `win_lock` retiré ·
>   `POCHOIR_MM` à 0. Contrôle : suite verte sans mutation (159 tests).

> **CLOSE (T2 — 8e20d1e/21d4bab + ronde 32b03fd/a051d8b, revue adverse :
> FIX-FIRST [F1-F3] soldé, painter INDEMNE).** Six réutilisations prouvées à
> l'arithmétique (superstar : edge 4 → 55×80 EXACT ; le « double filet
> 1,5/3 mm » sort du moteur EXISTANT : 1,5+0,25+1,1+0,15 = 3,00 — le plan
> attendait une famille pour lui, amendé) + UNE famille neuve `gravure`
> (marge ivoire + aplat pochoir décalé 0,2 mm), premier jet REDESSINÉ
> (4,61 → pire couple revenu à l'antérieur 5,2/6,84 : la 7e famille n'a rien
> coûté). F1 = la leçon publiée non armée : aliaser une famille EXISTANTE
> restait 154/154 vert — le banc rend désormais l'empreinte FNV du bitmap de
> signature et exige la DISTINCTION PAIRWISE des 7, avec contrôle négatif
> permanent (l'alias joué sur la copie DOIT rendre deux empreintes égales).
> F3 = le banc dessinait une plaque que le fichier ne porte pas (garde
> `plate.h > 6·u` reflétée ; gravée livre 7 mm — à 1 mm de la falaise,
> épinglé). F2 = legende, seule géométrie choisie-main, épinglée avec sa
> raison. F5-F7 : zones = poker_eu (sur micro la plaque devient NÉGATIVE,
> win_lock ne protège que les éditions utilisateur — phrase + test),
> win_lock de monstre lié à son carré, POCHOIR_MM épinglé à la source (la
> grille 0,5 mm ne voit pas 2,36 px). F9 : `archetype_frame(nom)` → COPIE
> PROFONDE (KeyError sinon) — T3 consomme LA FONCTION, jamais la table.
> F8 en avertissement : le redessin de la cuvette n'a AUCUNE protection CI
> (rasteriseur daltonien par conception) — qui touche une famille rouvre le
> panneau navigateur. 159 tests, 72 cas FNV byte-identiques vs 7fd0811,
> 21/21 rendus sans exception, badge navigateur inchangé 5,2/6,84.

### Task 3 : backend — modèles, instanciation, duplication, enregistrer-comme-modèle

**Files:** backend/app/services/cards/models.py (NOUVEAU — les données + routes,
monté dans cards/__init__.py AVANT le joker), core.py (create accepte model),
test_cards_core.py ou test dédié test_cards_models.py (règle 1 : nouveau py =
nouveau test).

> **Entrées laissées par la T2 — à lire AVANT d'écrire models.py :**
> · **L'habillage se prend par `FR.archetype_frame(nom)`, JAMAIS par
>   `FR.ARCHETYPE_FRAMES[nom]`.** La table est un objet de module : ses
>   sous-dicts (`window`) sont PARTAGÉS, et une instanciation qui écrirait
>   dedans contaminerait tous les decks suivants du même processus, sans rien
>   casser tout de suite. La fonction rend une COPIE PROFONDE et lève une
>   `KeyError` nommée sur un archétype inconnu — à la T3 d'en faire un 404 en
>   français. (`import` de données entre modules : autorisé, R8 n'interdit que
>   le ROUTER d'un voisin.)
> · **Les zones sont celles du POKER 63 x 88.** Mesuré sur les douze formats :
>   `winMM` re-borne la fenêtre dès que le format est plus petit — le carré
>   47 x 47 de « monstre » (qui EST l'archétype) devient 44,45 x 47 sur
>   `domino` et 31,75 x 44,45 sur `micro` —, et la plaque de bas de carte
>   passe à une hauteur NÉGATIVE sur `micro`, `mini` et `square_eu` (le
>   painter n'en dessine alors aucune). `win_lock` ne protège rien de tout
>   cela : il n'agit que sur les retailles de l'utilisateur. Un modèle doit
>   donc DÉCLARER son format (et le dire à l'écran), ou re-dériver ses zones.
> · Les slots P3 de chaque archétype restent à écrire (la T2 n'a livré que le
>   cadre) ; les captures de la T2 montrent les habillages sous les slots d'un
>   deck de test.

- [x] `GET /api/cards/models` : les 7 modèles d'usine (données Python,
      zone-par-zone §6.2:323-354 transcrites en mm) + les modèles perso de
      `{DATA_ROOT}/cardforge_models/` (lecture tolérante : un JSON malformé
      est LISTÉ comme illisible avec son nom, jamais un 500).
- [x] `POST /api/cards/decks` étendu : `{model: "superstar"}` → create_deck
      puis pré-remplissage des sous-arbres frame/type/texture (le PATCH
      interne existant, patron core.py:244-276) + `palette`/`finish` là où
      leur module les lit ; modèle inconnu → 404 nommé. Un deck instancié
      est ORDINAIRE (aucune référence au modèle après coup — le seed, pas un
      lien).
- [x] `POST /api/cards/decks/{did}/duplicate` : copie du doc + des fichiers
      deck-locaux (illustrations exclues ? NON — une duplication copie TOUT,
      c'est « enregistrer comme modèle » qui exclut les illustrations) ;
      nouveau did, nom « copie de … ».
- [x] `POST /api/cards/models` (perso) : sérialise format/frame/type/palette/
      texture du deck courant, PAS les illustrations (les slots gardent leurs
      réglages, `src`/images purgés) ; nom demandé ; écrit
      `cardforge_models/{slug}.json` (slug sûr, collision → suffixe) ;
      re-listé par GET.
- [x] Chaque modèle d'usine VALIDÉ par test : instancier → GET /{did} → les
      slots sont dans les bornes de la carte (boxes ⊂ trim), la famille
      existe, le preset P3 est légal ; le painter rend sans erreur
      (cv.cfErrors vide) sur une carte de test. *(le rendu NAVIGATEUR est la
      seule part non close ici — il demande l'app déployée et la galerie de
      la T4 ; substitut mesuré côté serveur : le JUGE de P3, ci-dessous.)*
- [x] jamais-500 ; French messages ; fontes : repli nommé (décision 2).
- [x] *(ajout de la ronde, demandé par la T4)* `DELETE /api/cards/models/{id}` :
      perso supprimable depuis l'écran ; modèle d'usine → 403 nommé ;
      inconnu → 404 ; identifiant hostile → le motif de l'écriture.

> **Livré (T3)** — `backend/app/services/cards/models.py` (NEUF, 1014 l.),
> `core.py` (+62 l. : `model` à la création, `duplicate_deck` + sa route),
> `cards/__init__.py` (montage), `backend/tests/test_cards_models.py` (NEUF,
> **135 tests verts**). Lint intégral **0 violation**, les **11 suites cards
> vertes** (601 s), aucun octet de frontend touché.
>
> · **LES MODÈLES SE MONTENT AVANT `core`, pas seulement avant le joker.**
>   Le plan disait « AVANT le joker » ; le joker `/{did}` vit DANS
>   `core.router`, et Starlette apparie dans l'ordre à travers tout l'arbre
>   inclus. `/models` est UN segment : monté après `core`, il tombait dans
>   `/{did}` et `GET /api/cards/models` répondait « identifiant de deck
>   invalide ». L'inverse est sans risque (models.py ne déclare que
>   `/models`). Mutant joué : montage inversé → test rouge.
>   `/decks/{did}/duplicate`, lui, a TROIS segments : il ne peut tomber dans
>   aucun joker, il reste donc dans `core.py`, à côté de `POST /decks`.
>
> · **AMENDEMENT — `palette` n'a PAS de module qui la lise.** Le plan disait
>   « + `palette`/`finish` là où leur module les lit ». `finish` en a un
>   (`doc.gltf.finish`, M_STATE_DEFAULT de mod-gltf.js — c'est là qu'il est
>   écrit) ; `palette`, non : aucun sous-arbre du document ne porte de
>   palette, et le partitionnement de `normalize_deck` jetterait une clé de
>   plus. D'où la décision : **`palette` est une LECTURE du modèle**
>   (`palette_of` : encre dominante des slots, plaque dominante, teinte du
>   support) et non une quatrième table de couleurs. Écrite à la main, elle
>   aurait menti dès la première retouche d'encre sans que rien ne le dise ;
>   relue, elle ne peut pas. Mutant joué (palette écrite en dur) → 7 tests
>   rouges.
>
> · **AMENDEMENT — un « élément » est un GROUPE de slots.** Le plan les
>   décrivait comme des presets de slot (au singulier). Une attaque de
>   « créature » fait TROIS slots (coût, nom, dégâts) et une ligne de tableau
>   de « duel » en fait deux (libellé, valeur tabulaire) : la forme livrée est
>   `{id, label, hint, slots: [...]}`. C'est aussi ce qui permet d'épingler
>   « 1-2 attaques » et « 5-7 lignes » : le premier exemplaire est POSÉ, le
>   second est l'élément, et la réunion des deux tient dans la zone §6.2 (au
>   millimètre pour créature : 6,51 → 51 x 22 EXACT).
>
> · **Le format est DÉCLARÉ, le reste du bloc `format` ne l'est pas.** Un
>   modèle porte `"format": "poker_eu"` (l'entrée de la T2 : les zones sont
>   celles du poker). La définition, le fond perdu et le rayon de coin
>   restent au DECK — ce sont des réglages d'impression, pas de gabarit ;
>   l'instanciation les laisse à leurs défauts.
>
> · **« Enregistrer comme modèle » GARDE les textes des slots.** Décision
>   prise sur une mesure de la T1, pas sur un goût : un slot dont le texte est
>   vide ne peint PAS sa plaque (`drawSlot` sous `if (!m.empty)`). Purger les
>   textes aurait rendu des modèles SANS CARTOUCHES — une mise en page à
>   trous, là où l'on croyait n'enlever que du contenu. Ce qui est purgé l'est
>   vraiment : `doc.face` n'est pas sérialisé du tout, et un papier importé
>   (`texture.paper = "__import"` + `texture.custom`) retombe sur la matière
>   par défaut. Le test relit les OCTETS du fichier écrit : ni `local:`, ni
>   l'identifiant de dessin, ni `paper.png`. Mutant joué → rouge.
>
> · **LE LAB N'A AUCUNE ROMAINE DE LABEUR.** Les 23 familles chargeables
>   (`FONTS_LOCAL`, miroir de `FONT_META`) comptent UNE romaine, Cinzel, et
>   c'est une police de TITRAGE. Les archétypes qui demandent un corps de
>   texte serif — « arcane » (EB Garamond) et « gravée » (IM Fell/Cormorant
>   SC) — replient donc sur Cinzel pour les titres et sur IBM Plex Sans pour
>   le corps, et le modèle le DIT : chaque modèle porte un `fonts_note`
>   `{spec, police, pourquoi}`. Le test exige que toute police EMPLOYÉE soit
>   déclarée là et présente au lab. Les autres replis : Oswald → Bebas Neue,
>   Barlow Condensed → Staatliches, Titan One → Bungee, Nunito/Barlow →
>   Inter, Lato/PT Sans/Roboto Condensed → IBM Plex Sans, Jost → Space
>   Grotesk, Spectral SC/Alegreya SC → Cinzel, Saira Condensed → Bebas Neue,
>   Archivo → Archivo Black. Anton et Archivo Black, eux, sont au lab : aucune
>   substitution. Les valeurs que la spec veut TABULAIRES (duel, tableau
>   saisonnier de légende) passent en JetBrains Mono — la seule chasse FIXE du
>   lab : les colonnes s'alignent par la POLICE, pas par des espaces.
>
> · **LE JUGE DE P3 A TRANCHÉ SUR LES SEPT** (`type.layout`, poker 300 DPI,
>   textes par défaut). Sans encombrement mesuré par le navigateur, il juge
>   sur la BOÎTE — le verdict le plus sévère. Résultat : **0 slot hors zone
>   sûre sur 6 modèles**, 0 bloc sous son plancher de lisibilité, 0 glyphe
>   manquant, et UNE exception nommée : le bandeau de nom de « légende »
>   (0,74 → 63 x 10), qui touche le trait de coupe PARCE QUE LA SPEC LE VEUT
>   à fond perdu. Dans l'app, ce même juge tranche sur l'ENCRE et un nom
>   centré reste loin du bord. L'exception est épinglée nommément : une zone
>   déplacée par mégarde ne pourra pas se glisser à côté d'elle. Mutant joué
>   (pied de « duel » poussé à 82,5 mm) → rouge.
>
> · **Ce que les tests gardent encore** : les 35 clés par slot ET
>   l'IDEMPOTENCE de `norm_slot` (la graine est de la donnée propre, pas
>   réparable) ; les zones §6.2 recopiées de la spec dans une table-ORACLE et
>   comparées à la réunion des boîtes (exacte pour les grilles, incluse pour
>   les zones « 1-2 » / « 5-7 », coin seul pour les zones citées sans
>   dimension) ; les fenêtres d'illustration des six archétypes qui en citent
>   une, relues sur `archetype_frame` (la spec, la table de P2 et le modèle
>   disent la même chose) ; **aucun chevauchement** entre deux slots d'une
>   même face, ni entre un élément ajoutable et un slot posé (un preset qui
>   tombe sur un texte existant est un cadeau empoisonné : l'utilisateur croit
>   que l'ajout a échoué) ; tout texte par défaut écrit dans une police qui
>   sait l'écrire (relevé de cmap, avec un contrôle que le relevé MESURE
>   quelque chose — `PolandKaito` doit rester signalée sans « é ») ; le
>   catalogue de matières/effets extrait de `mod-texture.js` (le backend n'en
>   a pas de miroir : il ne dessine pas) ; les signatures écrites de la spec
>   (plaque de titre de « duel » à rayon 0 = « rectangle, PAS d'ellipse »,
>   attribut ⌀7 de « monstre » dont le rayon vaut la moitié du côté, « nom
>   capitales », « étoiles alignées à droite », « règles romain + ambiance
>   italique », « capitales espacées »).
>
> · **`type.preset` reçoit l'ARCHÉTYPE, pas l'un des 4 gabarits de P3** — et
>   c'est sans danger POUR UNE RAISON MESURÉE, pas par convention :
>   `presetSlots` replie un identifiant inconnu sur `champion`
>   (mod-type.js:366) et `seedIfEmpty` ne re-sème JAMAIS un document qui porte
>   déjà des slots (:1372). Les deux lignes sont épinglées au source. Le deck
>   instancié porte `seeded: true` : même si l'utilisateur supprimait tous ses
>   slots, le gabarit « champion » ne viendrait pas se poser par-dessus.
>
> · **Mutations jouées, 11 sur 11 TUÉES** : copie profonde retirée
>   (`model()` + `instancier`) · branche 404 du modèle inconnu retirée ·
>   purge des illustrations retirée · slug rendu tel quel (collision) · id
>   perso pris dans le CONTENU du fichier (un perso pouvait alors masquer un
>   modèle d'usine) · modèles montés après `core` · duplication du seul
>   document (dossier non copié) · plaque sans texte par défaut · zone de la
>   spec décalée de 1 mm · palette écrite à la main · pied de « duel » poussé
>   sous la zone sûre. *Premier jet du mutant « slug » SURVIVANT et pourquoi :
>   il ne coupait que la boucle de suffixe, pas le repli `uuid` qui suivait —
>   le test avait raison, le mutant était faux. Re-joué correctement : tué.*
>
> · **Restes / entrées pour la suite.** (a) Le RENDU navigateur des sept
>   modèles (T5) : le painter est au navigateur, aucun test serveur ne peut
>   le voir — c'est là que se jugeront les fontes réellement chargées, les
>   plaques peintes et la fidélité visuelle. (b) Les icônes, drapeaux,
>   écussons et pastilles d'école de la spec sont des IMAGES : la 3a n'a que
>   des slots de TEXTE, ces zones existent donc à leur place et à leur taille
>   avec un texte de remplacement, et le `hint` de chaque modèle le dit — les
>   calques d'image sont la 3b. (c) `§6.4` de la spec dit « les 8 » modèles :
>   c'est « taverne » comprise (2e fournée) — la galerie de la T4 en affichera
>   **7** d'usine plus les perso. (d) Lecture publiée de « grille 6 stats
>   2 x 3 » : DEUX colonnes de TROIS lignes (23,5 x 7 mm par case), qui
>   remplit 8,56 → 47 x 21 exactement.

> **Ronde adverse (22/08, après livraison T3)** — la revue a rendu FIX-FIRST
> [F2, F3, F9, F1] plus douze suivis, et elle avait raison sur les quatre :
> **tout est corrigé**, les 43 zones re-dérivées à la main par la revue
> étaient bien présentes — *c'était la PREUVE qui manquait, pas la donnée*.
> **154 tests** (135 → +19), **27 mutants joués, 27 TUÉS**, lint 0, **11/11
> suites cards vertes** (609 s).
>
> · **[F2] Les tests MESURAIENT des zones, ils n'en COMPTAIENT aucune.** Cinq
>   zones NOMMÉES par la spec — le pied d'icônes de « superstar », la ligne
>   légale et la rareté de « créature », le pied de référence de « duel », la
>   ligne de type et la boîte d'effet de « monstre » — pouvaient être
>   SUPPRIMÉES du modèle en laissant 135/135 vert : les tables de géométrie ne
>   jugent que ce qu'elles citent. Table `ZONES_PRESENTES` (une entrée par
>   zone que la spec nomme, message d'échec qui cite la zone), plus « TOTAL en
>   gras » (§6.2-6) épinglé. Deux mutants (pied supprimé, rareté supprimée) :
>   tués.
> · **[F3] Un fichier `superstar.json` déposé à la main USURPAIT un
>   archétype.** Deux lignes au même id dans le catalogue (une liste à clés
>   doubles finit par en perdre une), et la perso était morte-née puisque
>   `model()` sert l'usine d'abord. **Choix : LISTER ET SIGNALER** —
>   `id: "perso-superstar"` + `illisible: true` + la raison ET LE GESTE
>   (« renommez le fichier »). Pourquoi pas le préfixe seul : un id préfixé
>   serait cliquable et ne résoudrait rien (`perso-superstar.json` n'existe
>   pas) ; pourquoi pas le refus seul : sans id distinct, le doublon de clé
>   reste. Et `model()` DOIT continuer à servir l'usine d'abord — c'est ce qui
>   empêche un fichier déposé de détourner un archétype.
> · **[F9] Un verdict publié que rien ne mesurait.** `layout()` sans `posed`
>   rend `under_read` vide PAR CONSTRUCTION (le corps composé, seul le
>   navigateur le mesure) — et le test ne l'assertait même pas. Ajouté :
>   l'assertion, plus le contrôle STATIQUE qui, lui, porte —
>   `size_pt >= read_pt` sur les 79 slots (l'ajustement automatique ne fait
>   que descendre : un bloc qui PART sous son plancher ne se lira jamais).
>   Deux mutants (planchers à zéro, titre à 5 pt) : tués.
> · **[F1] Le cadre n'était pas filtré, la matière l'était.** La revue a
>   planté `frame.back_image = "local:VERSO-SECRET"` par l'autosave ORDINAIRE :
>   les octets partaient dans le fichier de modèle. Rien ne fuit aujourd'hui
>   (la clé n'existe pas encore) — mais **§6.2ter fera du verso personnalisé
>   une image importée « SAUVÉE dans les modèles »**. **Choix : LISTE
>   BLANCHE**, `_FRAME_CLES = frozenset(archetype_frame("superstar")) |
>   {"art_window"}` — DÉRIVÉE, pas retapée : `test_cards_frame.py` exige déjà
>   que les sept habillages portent exactement les clés du bloc DEFAULTS de
>   mod-frame.js, donc la liste suit P2 toute seule. Une liste noire écrite
>   aujourd'hui ne connaîtrait pas la clé de demain ; la liste blanche refuse
>   par défaut et OBLIGE la 3c à décider ce qu'un modèle emporte.
>
> · **Les douze suivis, tous pris.** **F5** course du double-clic : mesurée
>   par la revue à `[200,200,200,500,200,500]` avec trois réponses au MÊME id
>   (deux modèles écrasés en silence) — le nom se réserve désormais par
>   CRÉATION EXCLUSIVE (`open("x")`), c'est le système de fichiers qui
>   tranche ; test = 6 POST simultanés, 6 ids distincts, zéro 500. **F6** les
>   500 publiaient `str(OSError)`, donc le chemin absolu, donc le nom de
>   compte (le dépôt a déjà payé cette fuite) : cinq messages réécrits
>   (`e.strerror` seul), détail au journal, et un test qui LIT LE SOURCE des
>   deux fichiers pour interdire `{e}` dans un `HTTPException`. **F7** écho du
>   modèle inconnu borné à 40 signes (3 000 caractères, du balisage et un
>   U+202E repartaient tels quels). **F8** `perso_total` + `perso_tronque`
>   publiés — et le test ABAISSE VRAIMENT le plafond (5 fichiers, plafond 3) :
>   sans cela le contrôle ne mesurait rien, le mutant a survécu au premier
>   jet. **F10** « PV + élément 44,4 » se lit PAR PAIRES (x 44, y 4) : x=44,
>   w=15, et l'oracle du test corrigé — il portait le nombre de
>   l'implémentation, pas celui de la spec. **F11** le tableau de « duel » ne
>   POUVAIT PAS atteindre les sept lignes de la spec (7 x 4,8 = 33,6 > 29) :
>   pas ramené à 4,1 mm (7 x 4,1 = 28,7), deux éléments distincts (6e et 7e
>   ligne), et la collision d'ids d'élément traitée par une PROPRIÉTÉ MESURÉE
>   plutôt que par du code neuf — `norm_slots` RENOMME les doublons au lieu
>   d'en perdre un, épinglé pour les sept modèles. **F12** les trois copies
>   profondes d'`instancier` étaient redondantes ET le commentaire affirmait
>   un danger inexistant : copies retirées, commentaire remplacé par la
>   mesure (la protection tient à `model()`, le test poison la vérifie des
>   deux côtés). **F13** identité, pas égalité : `is not` sur le cadre, sur
>   son sous-dictionnaire `window` et sur la table. **F14** modèles perso
>   demi-validés : cadre par la liste blanche, matière par le filtre
>   d'import, slots par `norm_slots`, et un « élément » sans slots n'est pas
>   un élément. **F15** `seeded: bool(slots)` — posé en dur, il condamnait un
>   modèle SANS slots à un document éternellement vide (plus de modèle, plus
>   de gabarit). **F16** `datetime.now()` naïf aligné sur l'UTC de `_now_iso`.
>
> · **TROUVÉ EN CORRIGEANT (n'était dans aucun rapport)** : `SLUG_RE`
>   refusait le tiret BAS, si bien qu'un `mon_modele.json` déposé à la main
>   était **LISTÉ mais pas ouvrable** — une vignette qui répond 404 au clic.
>   Le motif accepte désormais `_`, et surtout **le même motif décide de la
>   liste et de l'ouverture** (`_id_utilisable`) : un fichier au nom
>   inutilisable est listé ILLISIBLE avec la règle en clair, au lieu de
>   promettre ce qu'il ne peut pas tenir.
>
> · **AJOUT DE LA RONDE — `DELETE /api/cards/models/{id}`** (demandé par la
>   T4, qui a livré la galerie) : on pouvait CRÉER un modèle perso depuis
>   l'écran et jamais le retirer. Quatre branches : usine → **403 nommé** (les
>   sept ne sont pas sur le disque ; un « supprimé » qui réapparaît au
>   rafraîchissement est pire qu'un refus), perso → fichier effacé + 200,
>   inconnu → 404, id hostile → le MÊME motif que l'écriture. *La T4 peut
>   basculer le nettoyage de son banc sur cette route à sa prochaine passe et
>   jeter son miroir de `config._data_root`.*
>
> · **Deux mutants ont SURVÉCU au premier jet, et les deux disaient vrai sur
>   les tests, pas sur le code.** (a) `perso_total` : avec cinq modèles sous
>   un plafond de 400, un total faux est indiscernable du vrai — le test
>   abaisse maintenant le plafond pour de bon. (b) La traversée de `DELETE` :
>   le client et le routeur RÉSOLVENT `..` avant que la route ne voie quoi que
>   ce soit, si bien que le test mesurait le TRANSPORT et non la garde ; il
>   appelle désormais `supprimer()` et `model()` EN DIRECT avec onze
>   identifiants hostiles, un témoin posé à côté du dossier. Sans la garde,
>   l'appel direct efface le témoin — mutant tué.
>
> · **Trouvé en relisant le correctif de F5** (aucun rapport ne l'avait vu) :
>   une réservation qui échoue à l'écriture laissait derrière elle un fichier
>   VIDE — listé « illisible » à chaque ouverture de la galerie, et un nom de
>   modèle pris pour rien. Un incident passager devenait un déchet permanent.
>   La réservation se REND désormais (mutant : `except` restreint → rouge).
>   Même relecture, même classe, un cran plus loin : la LIGNE « illisible »
>   du catalogue recopiait elle aussi `str(OSError)`, donc le chemin — et
>   elle part en HTTP, pas seulement au journal. Le pin de F6 balaie
>   maintenant les appels `HTTPException(` **parenthèses appariées** (un
>   message coupé sur trois lignes ne montrait que sa première ligne au
>   contrôle) ET les appels `_illisible(`. Ce qu'on publie d'une erreur JSON
>   est nommé (`_detail_json` : motif, ligne, colonne), jamais l'exception.
>
> · **Restes inchangés** : le rendu navigateur des sept modèles (T5) ; les
>   icônes/drapeaux/écussons restent des slots de TEXTE jusqu'aux calques
>   d'image (3b) ; « les 8 » de §6.4 = 7 + taverne (2e fournée).

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
