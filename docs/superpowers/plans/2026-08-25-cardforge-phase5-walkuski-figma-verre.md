# Cardforge — Phase 5 : la série Wałkuski, l'éditabilité Figma, les matériaux verre

**Demande utilisateur (24/08, verbatim résumé)** : (1) régénérer les SUJETS de P1 en
conservant nom et type/thème, dans le langage visuel de Wiesław Wałkuski, via un
skill d'analyse des proportions et de la palette (FAIT : skill `walkuski-style`,
user-level, fiche mesurée sur corpus de 16 affiches 1986-2018) et « le générateur
le plus pertinent » ; (2) rendre TOUS les éléments d'un jeu généré ÉDITABLES —
gemmes de rareté, ornements — avec bandeaux/menus façon Figma : étirer, ajouter
des formes (bouts fléchés), aligner ; peupler ensuite les nouvelles régions dans
les sections typo etc. ; la main sur les bordures des zones d'illustration et des
encarts ; (3) en 3D : textures, occlusions, effets verre / verre dépoli /
translucide.

**Branche** : `claude/audit-cleanup-2026-08`. **Méthode** : inchangée (une tâche =
un agent opus, RED d'abord, mutation + témoin avoué — un aveu SE MESURE —,
commits français locaux, revue adverse, ronde au même agent, clôtures ici,
amendements à la source, suite quiescente, poussée en fin de phase). **Argent** :
la génération de la série est un OPT-IN EXPLICITE de l'utilisateur — plafond dur
au plan (D2), prix re-vérifiés à la table avant le premier tir, tout AUTRE appel
payant reste interdit dans les tests (sentinelles en place).

---

## 1. Faits de reconnaissance (24/08, vérifiés sur pièces)

- **Le catalogue P1 est 100 % VECTORIEL** : 18 SUJETS (`mod-face.js:121-140`,
  miroir face.py — tower/pines/monolith/dragon/sphinx/portal/crystals/ship/wolf/
  knight/citadel/whale/phoenix/serpent/golem/archer/grimoire/beacon) × 6 COMPOS
  (:158-165 — vista/medallion/heraldry/depths/backlight/stained) = 108 dessins,
  × 12 palettes = 1296 ids `face_<pal>_<compo>_<sujet>`, calculés client, zéro
  octet réseau. La série Wałkuski est donc une NOUVELLE VOIE D'IMAGES à côté du
  vectoriel, jamais un remplacement.
- **Génération** : `POST /images/generate` (routes.py:3668-3745) route
  gpt-image-* (inline) / `nano-banana` (délégué à image_providers.py:105-139 —
  fal-ai/nano-banana, SEUL chemin Gemini) / FLUX (défaut). `GET /image-models`
  (:4096-4121) gated par clés. **nano-banana N'A PAS de prix dans pricing.py**
  (`_IMAGE_MODELS` :78-83 : flux 0,003 / gpt-image-2 0,12 / gpt-image-1 0,06 /
  mini 0,015) → « tarif non tabulé » partout. Passerelle unique `CF.images`
  (core.js:1336-1354), règle 8/17 : tout fetch brut hors passerelle LÈVE.
- **Figma-gap (P3)** : les poignées de redimensionnement EXISTENT (8 points,
  mod-type.js:5431+), la fluidité §9.6 est IMPLÉMENTÉE (rAF coalescing P2+P3) ;
  MANQUENT : multi-sélection (sel singulier :5528), outils aligner/distribuer,
  primitives de formes (KINDS = ["text","image"] seulement :225), poignée de
  rotation (valeur numérique seule), guides objet-à-objet (snap grille 0,25 mm
  seul), gestes z au canvas (liste Monter/Descendre seule).
- **Gemmes de rareté** : géométrie CALCULÉE `placeGem` (mod-frame.js:879-918,
  {z: seat?40:70, movable:true, cx, cy, r}), 6 palettes de rareté (:519-524),
  toggle f.gem ; **ornements de coin** : catalogue CORNERS 6 entrées (:164-171),
  peints en z=70. Ni l'une ni l'autre ne sont SÉLECTIONNABLES/déplaçables à la
  main aujourd'hui.
- **Bordures** : la « bordure » d'une zone P3 = plate_color/alpha/radius SANS
  contour propre (outline = le trait des GLYPHES) ; la fenêtre d'illustration
  P2 = un rect nu, son liseré est l'anneau de la famille.
- **3D** : le writer GLB porte déjà baseColor/MR/normal/OCCLUSION/emissive +
  extensions iridescence/clearcoat/anisotropy au patron « recette → bloc
  conditionnel » (forge3d_scene.py:1740-1767, _HOLO_RECIPES :551-556) ;
  **transmission/volume/ior/specular ABSENTS du backend mais PRÉSENTS dans le
  viewer embarqué** (model-viewer.min.js — chaînes vérifiées) : le verre est
  l'ajout 3D le moins risqué. Le lab PBR (derive_maps, 8 cartes) est DÉJÀ
  consommé par P9 (mat: sources, forge3d.py:1582).
- **Skill `walkuski-style`** (user-level, C:\Users\olivi\.claude\skills\) :
  fiche mesurée (palette maître 9 teintes dont 66,2 % de budget neutre, bandes
  p10-p90 : chroma médiane 9,9, vide 43 %, masse 50,6 %, portrait 0,695),
  gabarits de prompt SANS nom d'artiste, **juge étalonné leave-one-out**
  (authentiques ≥78 % TIENT, témoin saturé 59 % HORS STYLE sur 4 axes, exit
  code 1 = triable par lot), mesure_style.py 16 img/6 s. LA CORRECTION DE
  MESURE : le régime réel = tirage à UNE famille (ocre 50 %/rouge 25 %/
  graphite 19 %/violet 6 %), pas « accent sur fond éteint » (l'accent, quand
  il existe — 6/16 — fait 4,6 % de toile).
- **Transmis phase 4 pris ici** : primitives de formes (pas de cercle — le halo
  Patriarche posé en calque d'image), palette d'éléments des modèles perso
  vide, border.color aveugle à l'or pré-front, ondulation douce (3 aveux),
  phase-pointeur, contour SVG d'extrude.

## 2. Décisions de conception

**D1 — La série est une VOIE, le vectoriel reste le socle.** `doc.face.serie`
(ou sélecteur d'app ?) : P1 gagne un sélecteur de série (« Vectoriel » |
« Affiche polonaise ») ; la série Wałkuski = 108 images PNG dans le magasin
d'images de l'APP + un MANIFESTE de série (DATA_ROOT, patron modèles perso)
mappant `<compo>_<sujet>` → id d'image ; le catalogue P1 montre le rendu de la
série active, retombe sur le vectoriel pour toute case absente (l'aveu à
l'écran : « n/108 générées »). Noms et thèmes CONSERVÉS : les 18 sujets et 6
compos existants sont la grille — le prompt de chaque case naît de
(sujet, compo, fiche de style, tirage de famille mesuré 54 ocre/27 rouge/
20 graphite/7 violet).

**D2 — La génération : FLUX atelier + le juge sélectionneur, PLAFOND DUR.**
Prix RE-VÉRIFIÉS à la table + à la source fal avant le premier tir ;
`nano_banana_usd` tabulé dans pricing.py (0,039 vérifié une fois). Pipeline par
case : jusqu'à 6 candidats FLUX schnell 2:3 → mesure_style.py juge → le
meilleur TIENT gagne ; A RETOUCHER → 1 édition nano-banana ; toujours refusé →
1 GPT Image 2 ; toujours refusé → la case reste vectorielle, AVOUÉE. **Plafond
de campagne : 6,00 $ US** — le compteur s'affiche, la campagne S'ARRÊTE au
plafond avec le bilan (cases faites/restantes), reprenable. Les TESTS de la
machinerie roulent en espion/faux (zéro dépense) ; seule LA CAMPAGNE réelle
dépense, sur le backend déployé, en une tâche dédiée qui journalise chaque
centime.
**AMENDEMENT ronde T1 (mesuré le 25/08)** : (1) LE PIRE CAS EST 19,12 $ =
3,19× le plafond (échelle complète 0,177 $/case × 108) — 33 cases seulement
tiennent au pire ; le plafond reste 6,00 $ par SESSION et la campagne est
MULTI-SESSION par construction ; le taux de passage FLUX (il faut ≥ 76,4 %
pour finir en une session) est INCONNU : T5 le mesure sur ses premières cases
et ré-estime AVANT de continuer. (2) La route de campagne exige une
CONFIRMATION EXPLICITE (corps {"confirmer": true}) — sans elle, elle répond
le DEVIS (cases manquantes, pire cas, dépense courante, plafond) sans rien
dépenser : l'incident de ronde (une sonde de critique a émis 436 requêtes
refusées à l'authentification — la clé neutralisée du banc a tenu, zéro
centime) a prouvé qu'un POST nu lançait la série entière. (3) Le manifeste
s'écrit APRÈS CHAQUE CASE (une panne d'image au milieu ne perd plus les cases
payées ni la dépense — l'except s'élargit : un juge qui tombe = un
fournisseur qui tombe), et une case ne S'OUVRE que si l'échelle complète
tient sous le plafond (le reliquat inutilisable est avoué au bilan).
(4) Sélection vide (?cases= ou ,,,) = RIEN, jamais tout — 400 nommé sur une
route qui dépense.
**PRÉCISION T5 (lue à la source par la sonde d'assurance)** : le plafond de
6,00 $ est une ENVELOPPE TOTALE délibérée, pas un plafond par session —
`campagne()` reprend son cumul du manifeste sur disque et le mur tient d'un
POST à l'autre (épinglé par test). « Multi-session » signifie : chaque POST
reprend où le précédent s'est arrêté, DANS l'enveloppe. La relever
(SERIE_PLAFOND_USD) est une décision de l'UTILISATEUR, jamais un
contournement d'agent — avec l'estimation ≈4,30 $ les 108 cases tiennent ;
sous ~76 % de taux FLUX, la campagne bute vers la case ~90-100 et s'arrête
proprement là. La phrase « 6,00 $ par SESSION » de l'amendement ci-dessus
était une erreur de plan : la machinerie, plus sûre, fait foi.

**D3 — Les éléments libérés + les formes.** Les gemmes et ornements de coin
deviennent des ÉLÉMENTS ÉDITABLES : la gemme gagne des clés de position/taille
persistées (le placement calculé devient le DÉFAUT, la main de l'utilisateur
gagne — patron fenêtre auto/manuelle T4, avec l'aveu au même endroit) et entre
dans la sélection/poignées de P2 ; les ornements de coin : offset/échelle par
coin. P3 gagne des KINDS de formes : `rect`, `ellipse` (ferme le transmis
cercle — le halo devient une vraie ellipse à rayon), `line`, `arrow` (bout
fléché paramétrable — tête mm, épaisseur), chacun avec fill/stroke/stroke_width
propres ; et TOUTE zone gagne son contour : `plate_stroke`, `plate_stroke_mm`
(la « main sur les bordures des encarts ») ; la fenêtre d'illustration P2
expose un liseré propre (win_stroke/couleur/mm) indépendant de l'anneau de
famille. Tout slot de forme est peuplable ensuite (le texte par-dessus une
forme = deux slots — pas d'imbrication, dit à l'écran).

**D4 — Les outils Figma.** Multi-sélection (clic+Maj, lasso), barre
contextuelle : aligner (6) / distribuer (2) / égaliser tailles, rotation À LA
POIGNÉE (le coin, Maj = pas de 15°), guides objet-à-objet (aimantation aux
bords/centres des voisins + à la fenêtre d'illustration, seuil mm, TOUJOURS
débrayable Alt), gestes z (devant/derrière + tout-devant/tout-derrière), le
tout au-dessus du rAF §9.6 existant. L'undo reste UN pas par geste (le
multi-patch groupé — vérifier le patron HIST à la source). Phase-pointeur du
Sceau branchée en passant (le transmis 3 fois avoué — sealStops(f, phase) est
prêt depuis 3c).

**D5 — Le verre et les matières.** Recettes `_GLASS_RECIPES` au patron holo :
`verre` (transmission 1.0, ior 1.5, roughness 0.05), `verre-depoli`
(transmission 1.0, roughness ~0.4, KHR_materials_specular), `translucide`
(transmission ~0.7, volume thickness + attenuation teintée par la couleur du
nœud) — extensions transmission/volume/ior/specular ajoutées au writer au
patron C8, `extensionsUsed` exacts, viewer déjà prêt (vérifié aux chaînes du
bundle) ; finitions exposées sur le nœud material (`finish` s'élargit), miroir
+ parité + le GLB PESÉ (les leçons T5). Occlusion : la carte AO du lab PBR
déjà branchée — l'UI du nœud l'expose (elle existe côté writer). L'« ondulation
normale douce » (3 aveux) se tranche ICI : une normal map basse fréquence sur
l'anneau du Sceau, mesurée, ou l'enterrement motivé — plus d'aveu reconduit.

**D6 — Le pipeline de prompts est ANCRÉ sur la fiche, jamais sur le nom.** Le
skill walkuski-style fait loi : palette imposée en hex du tirage, bornes
tonales, composition en fractions, vocabulaire de matière ; le juge REFUSE
(exit 1) et le refus se journalise avec ses axes rouges. Aucun nom d'artiste
vivant dans aucun prompt payant (les générateurs les refusent ET c'est la
ligne du projet).

## 3. Tâches

Ordre : T1 ∥ T2 (fichiers disjoints) → T3 (sur T2) ∥ T4 → T5 (campagne réelle)
→ T6 (intégration/preuve/poussée).

### T1 — La voie de série + la machinerie de génération (D1, D2, D6)
Manifeste de série (DATA_ROOT, schéma versionné), sélecteur P1 (retombée
vectorielle avouée), route de campagne (`POST /face/serie/generer` ? — patron à
poser : itère les cases manquantes, prompt depuis la fiche du skill + tirage,
candidats FLUX via la passerelle unique, juge en process, compteur de dépense
JOURNALISÉ, plafond dur, reprenable), `nano_banana_usd` tabulé après
re-vérification, prix affichés avant. TESTS en espion intégral (le juge tourne
sur des synthétiques teintés — un « généré » conforme passe, un saturé est
refusé), ZÉRO dépense.
**Fichiers** : face.py, mod-face.js, test_cards_face.py, pricing.py,
image_providers.py (si un délégué manque), routes.py (si liste de modèles).

- [x] LIVRÉ — commits `f4ea790`+`791f032` (+6151) puis ronde `74193a2`.
  Manifeste global-app {DATA_ROOT}/cardforge_series/walkuski.json (cases et
  refus SÉPARÉS — une case refusée reste manquante et se re-tente, son refus
  garde ses axes), doc.face.serie porté par le DOCUMENT (la voie voyage avec
  le jeu), sélecteur P1 (n/108, retombée vectorielle avouée par insigne,
  compteur de dépense affiché), copie du juge EN DÉPÔT (style_walkuski.py/
  .json, empreintes à fins-de-ligne normalisées + test de fraîcheur vs
  l'amont), nano_banana_usd 0,039 re-vérifié à la source fal datée, pipeline
  6-candidats-FLUX→juge→nano-edit→GPT→vectoriel-avoué, poids de familles
  RE-DÉRIVÉS du juge (8/4/3/1 œuvres → 54/27/20/7 aux plus forts restes),
  coalescence 6 POST→1 tir, sentinelle 16 noms fal + preuve de prise, clé du
  banc neutralisée STRUCTURELLEMENT (DEEPOTUS_DATA_DIR — le banc ne charge
  plus le vrai .env : le bloquant T3-phase-4 refermé à la racine pour cette
  pièce), zéro nom d'artiste prouvé par empoisonnement aux trois voies.
  142 tests face (98→142), lint 10/10.
- [x] Ronde adverse (opus) : 1 bloquant + 5 réels + 4 mineurs + 4 rejetés,
  ET UN INCIDENT INSTRUCTIF AVOUÉ PAR LE CRITIQUE : sa propre sonde a émis
  436 requêtes vers fal — TOUTES refusées à l'authentification (la clé
  neutralisée du banc a tenu, zéro centime) — prouvant qu'un POST nu lançait
  la série entière → la CONFIRMATION-DEVIS est née de là (D2-2). Le
  bloquant : une image illisible (UnidentifiedImageError EST un OSError,
  hors de l'except étroit) effaçait la SESSION ENTIÈRE — cases payées
  perdues, compteur à 0,00 → le manifeste s'écrit APRÈS CHAQUE CASE par
  FUSION-DELTA (relecture disque + delta de dépense, qui tue aussi le
  double-écrivain mesuré 5,0→3,018). Réels : le pire cas 19,12 $ = 3,19× le
  plafond ÉCRIT AU PLAN (multi-session, 33 cases ouvrables par session de
  6 $, T5 mesure le taux FLUX) ; le mur en cours de case brûlait sans trace
  → une case ne s'ouvre que si l'échelle complète tient (UNE arithmétique
  partagée — l'unification a tué le mutant survivant) ; sélection vide =
  RIEN jamais tout (400) ; l'aveu de cadre refait sur la géométrie vraie
  (0,635 était… la taille de refus de la barre ! coupe réelle 0,7159 ;
  portrait_4_3 = LE MEILLEUR cadre — le 2:3 exact coûterait 9,2 % de la
  hauteur ; et la marche GPT livre le 2:3 EXACT de la fiche — bonus
  épinglé aux DEUX miroirs) ; le compteur affiché. En écrivant les preuves :
  une FUITE DE CHEMIN ABSOLU dans les motifs de refus (le nom de compte
  serait parti dans le manifeste public de T5 — filtrée ; dette jumelle
  frame.py:ai_models routée vers la ronde T2) et le journal loguru en %s
  jamais formaté (la ligne dont T5 dépend). Mutation 12/12 dont 2 qui ont
  corrigé le CONTRÔLE, et la mutation sans-confirmation MESURANT le coût du
  défaut (3 min de banc, 19 $ en vrai).
- [x] CLOSE : leçons — (a) une route qui dépense répond un DEVIS à un appel
  nu, elle ne part pas (l'incident de sonde est la preuve par l'exemple
  que la défense en couches marche : c'est la clé neutralisée qui a arrêté
  436 requêtes, pas une garde) ; (b) le journal d'une dépense s'écrit en
  FUSION-DELTA après chaque unité payée, jamais en total après la boucle ;
  (c) un chiffre d'aveu se vérifie contre la géométrie qu'il prétend citer
  (0,635 venait d'une constante sans rapport). Dettes → T5 : mesurer le
  taux FLUX sur les premières cases et ré-estimer ; relire pricing.load()
  avant ; les candidats perdants au magasin (~648 PNG — purge à trancher
  T5/T6) ; l'œil T6 : le témoin refreshSel (data-ai/data-cat).

### T2 — Les éléments libérés + les formes + les bordures (D3)
Gemme/ornements édités (position/taille persistées, défaut calculé, aveu du
gel), KINDS rect/ellipse/line/arrow (+ palette d'éléments des modèles perso
NOURRIE — le transmis), plate_stroke sur toute zone, liseré propre de la
fenêtre P2. Parité miroirs, silhouettes intactes (les gemmes déplacées ne
cassent pas la QA — vérifier), norm_slots étendu des deux côtés.
**Fichiers** : mod-type.js, type.py, test_cards_type.py, mod-frame.js,
frame.py, test_cards_frame.py.

- [x] LIVRÉ — commits `2f48339`+`bddf8ed`+`af0128e`+`9729c35` puis ronde
  `76046e8`. 8 clés frame (gem_x/y/r null=auto, corner global ×4 au repère
  miroir, win_stroke) + 10 clés slot (49 au total) + KINDS×6 (rect/ellipse/
  line/arrow — LE CERCLE du halo fermé : ellipse à boîte carrée, IoU 0,9973
  contre le disque main, couverture π/4 à −0,0006). Gemme libérée (auto=écrin
  z40, manuelle=z70 crans-selon-position, TROIS surfaces d'aveu, Ctrl+Z rend
  l'auto), ornements globaux ×4, formes = slots z60 (pas de couche neuve),
  contours d'encarts + liseré de fenêtre propre. Silhouettes 31,60 INCHANGÉ
  avec la preuve d'impossibilité-par-construction (le banc arbitre part de
  DEFAULTS, n'appelle ni paintTop ni cornerOrn). QUATRE bugs trouvés en
  chemin dans ses fichiers : la parité num() cassée sur TOUTES les clés
  numériques (null=0 écran vs défaut backend), l'attente de police des
  formes (2,5 s), la boîte plate inattrapable, les formes traitées en
  mentions du cadre. RED avoué rejoué par stash sur le bloc A. 298 frame +
  271 type.
- [x] Ronde adverse (opus) : 1 bloquant + 8 réels + 4 mineurs + 7 REJETÉS
  mesurés (la rotation des formes MARCHE sur les deux bancs, la QA
  silhouettes ne peut pas voir une gemme posée — par construction). LE
  BLOQUANT : layout() ne connaissait pas les formes — SHAPES était du CODE
  MORT au backend, une flèche au plafond livré encrait 2 mm HORS COUPE en
  ok:True, aveugle des deux côtés → SHAPES branché, et l'encre d'une forme
  DÉRIVÉE DU DOCUMENT SEUL par layout() (le verdict tient sans client) ; le
  livreur a attrapé SON PROPRE premier jet faux (gonfler de head/2 aux 4
  côtés créait un FAUX débord — l'enveloppe exacte des points réels, chiffres
  mesurés remplaçant les prédits). Réels marquants : \d Unicode-Python vs
  ASCII-JS — les chiffres arabes faisaient BASCULER LE RÉGIME de la gemme
  (manuel backend / auto écran) → [0-9] dans 6 motifs py + 4 JS + un test qui
  REFUSE \d des deux côtés ; la garde du liseré morte (st() normalisait
  « bleu » → #000000 AVANT le painter — liseré noir muet) → défaut "" ;
  L'AVEU « sans qu'un pixel bouge » ÉTAIT FAUX — le déploiement CHANGE
  l'apparence des decks portant une valeur non numérique (plate_alpha:null :
  plaque invisible→pleine, mesuré aux empreintes) : la correction est bonne,
  l'aveu réécrit avec la mesure et le comportement épinglé ; gem_r/head_mm
  bornés PAR LE FORMAT (la gemme 20 mm était plus large qu'une carte micro ;
  un premier jet à min/2 mordait les 12 formats — corrigé min(tw,th), le
  non-borné restant DIT) ; cornerOrn : le trait suit enfin l'échelle ; le
  champ de gemme montre l'EFFECTIF ; LES DEUX TÉMOINS PINNÉS (séparables à
  une sonde près — morts comme témoins, la leçon de phase 4 mot pour mot,
  le bout de trait pinné DANS CHROME car le banc node n'a pas de notion de
  cap) ; inspPlaque cohérent avec la garde. Dette T1 fermée (_sans_chemin
  chez frame.py:ai_models, emprunt avoué). Ronde : 19/19 RED d'abord,
  18/18 mutations dont 2 qui ont corrigé LE CONTRÔLE, les deux bancs Chrome
  rejoués.
- [x] CLOSE : leçons — (a) une constante « pour poser la même question au
  même endroit » se VÉRIFIE branchée (SHAPES mort au backend = la garantie
  vendue absente) ; (b) \d n'est pas un vocabulaire partagé entre langages —
  [0-9] est la forme de parité, et le test refuse \d désormais ; (c) UN FAUX
  DÉFAUT EST PIRE QU'UN DÉFAUT MANQUÉ (l'enveloppe exacte contre le
  gonflement grossier) ; (d) 2e paire de témoins-couvercles de la phase —
  pinnés. Dettes → T3 : le plancher d'affichage 12 px vs boîte nulle du
  document (lasso/aimant lisent s.box, jamais le DOM), égaliser-les-tailles
  sur une ligne la rendrait diagonale (à trancher et dire), bouts fléchés en
  lot ; → T6 : models.py elements:[] (transmis à moitié fermé), le calque
  d'image encore mention du cadre (dette écrite aux miroirs).

### T3 — Les outils Figma (D4)
Multi-sélection, aligner/distribuer/égaliser, rotation à la poignée, guides
objet-à-objet débrayables, gestes z, un pas d'undo par geste, phase-pointeur
du Sceau. Bancs node sur les fonctions pures (aligne/distribue/aimante), et la
vérification Chrome du geste réel.
**Fichiers** : mod-type.js, test_cards_type.py (+ mod-frame.js si la
sélection s'étend aux éléments P2 — dire lequel possède quoi AVANT de coder).

- [x] LIVRÉ — commits `0d6d8fc` (P3) + `14496a1` (le Sceau) + `5c10247`
  (les gestes que le lot rendait faux) + `4d29acc` (les deux derniers
  lecteurs de `sel`). 329 tests type verts, 304 frame, lint 0 violation.
  **QUI POSSÈDE QUOI, tranché AVANT de coder** : la multi-sélection reste
  chez P3 et NE s'étend PAS aux éléments P2 cette phase. Trois raisons
  mesurées : (a) gemme/fenêtre/ornements n'ont pas de boîte comparable —
  (cx, cy, r), (x, y, w, h, r) et quatre décalages globaux ne partagent pas
  d'enveloppe, donc « aligner à gauche » n'y a pas de sens ; (b) leur
  annulation vit dans une AUTRE pile (`HIST` de mod-frame) que celle de P3
  (`UNDO/REDO`), et un lot mixte demanderait une annulation inter-pièces —
  de la machinerie neuve, pas un outil ; (c) leur surface de geste est la
  MINI-CARTE (`mapHit`), celle de P3 le calque sur la carte : deux
  surfaces, deux tests de prise. **Seul touché chez P2** : la
  phase-pointeur (D4, dernier point), plus trois lignes de CSS pour la
  bande — l'aimantation, elle, ne fait que LIRE `frame.art_window`, le
  contrat publié.
  **CONTRAT DE SÉLECTION NOUVEAU** : `doc.type.sel` est une LISTE (premier =
  « key object » Figma). Migration douce EN LECTURE, en UN endroit
  (`selIds`, seul `CF.get("type.sel")` de la pièce, prouvé par le compte) :
  chaîne -> liste d'un, vide -> liste vide, identifiants morts filtrés. Les
  anciens lecteurs appellent `selId()` = premier du lot : aucun n'a bougé.
  `models.py` écrit toujours une chaîne, elle est lue telle quelle ; le
  backend ne lit jamais `sel` (aucun miroir).
  **LIVRÉ** : clic+Maj (bascule, sans démarrer de glisser), clic nu qui
  GARDE le lot, Échap qui le vide, LASSO sur un fond de calque neuf (le
  calque était `pointer-events: none` — rien n'attrapait en terrain vide),
  glisser de lot à UN pas d'undo et UN delta partagé, barre contextuelle
  (6 alignements sur l'enveloppe, 2 distributions à espaces égaux, 2
  égalisations sur le premier sélectionné), réglages communs en lot avec
  « mixte » et les bouts fléchés (qui ne visent que les flèches, dit à
  l'écran), poignée de rotation (Maj 15°, GRISÉE en lot avec sa raison),
  guides objet-à-objet (voisins + `art_window` + centre de carte, seuil
  0,6 mm, Alt débraye, grille 0,25 en repli), gestes de profondeur par la
  MÊME mécanique que les flèches de rangée (`ordreApres`, un seul
  appelant). **LES DEUX PIÈGES TRANSMIS SONT MESURÉS** : lasso ET aimant
  lisent `s.box`, chacun avec sa mutation qui fait lire la boîte gonflée
  du calque et déplace le résultat de 0,5 mm. **LA DÉCISION TRANSMISE EST
  TRANCHÉE** : égaliser la hauteur d'une ligne plate la rendrait DIAGONALE
  — elle est ignorée et le toast le nomme ; en RÉFÉRENCE, l'égalisation
  entière est refusée. **Sceau (D4)** : `sealStops(f, phase)` a enfin un
  appelant — une BANDE D'APERÇU dans le panneau P2, ±0,15 autour de 0,35,
  retour canonique au `pointerleave`. Écran seul PROUVÉ EN EXÉCUTION :
  `sealPhaseLive` forcée à 0,71 laisse la trace du peintre IDENTIQUE, avec
  le contrôle négatif qui la fait bouger.
  **CE QUE LE LOT A RENDU FAUX, ET QUI EST RÉPARÉ DANS LA TÂCHE** : Suppr,
  Ctrl+D, les flèches, le collage et la surbrillance de la liste lisaient
  tous `selSlot()` — LE PREMIER du lot. Les cinq visent maintenant le lot
  (verrou tenu en UN endroit, `lotLibre`, pour les trois gestes de
  clavier). Et le danger qu'Échap venait de créer est fermé : `selSlot()`
  retombe sur le premier bloc quand rien n'est désigné, et Échap rend cet
  état COURANT — sans correction, « je relâche tout » serait devenu
  l'antichambre d'un effacement au hasard. Le clavier ET le panneau disent
  maintenant la même chose au même instant.
  **UN TÉMOIN SURVIVANT AVOUÉ** : la tangence du lasso (`<=` contre `<`
  dans `dansLasso`) est séparable en théorie — un rectangle dont un bord
  coïncide EXACTEMENT avec celui d'une boîte — mais le pin dépendrait de
  l'aller-retour flottant px -> mm, donc d'un arrondi et non d'une règle.
  Non pinné, et dit.
  **UN PIN A RATTRAPÉ UNE DÉRIVE DE RANGEMENT** : les fonctions de lot
  s'étaient glissées dans la tranche `placeOu` -> `dupSlot` que
  `test_TOUTES_les_naissances_passent_par_LA_MEME_porte` mesure (une
  annulation, aucun `commit`) — le pin est resté juste, c'est le code qui
  était mal rangé.
  ~66 tests neufs (271 -> 329 type, 296 -> 304 frame), 11 mutants de
  contrôle, banc Chrome des quatre gestes réels, lint cardforge
  0 violation, pylint sans un seul signalement dans le code ajouté.
  **Dettes vues en chemin, transmises à T6** : la liste de blocs se lit du
  FOND vers la surface (rang 0 = peint en premier) alors que les bandes
  fixes qui l'encadrent adoptent la convention Figma inverse — les
  infobulles des gestes de profondeur nomment l'équivalence, mais les deux
  moitiés de la même liste se lisent en sens contraires ; et le
  redimensionnement d'un LOT (échelle autour de l'enveloppe) n'est pas de
  cette phase — les poignées ne sont servies qu'en solo, et le lot montre
  son enveloppe pour que l'absence se voie.
- [x] Ronde adverse (opus) : 1 bloquant + 3 réels + 3 mineurs + 7 rejetés
  mesurés (l'aimant-sur-soi exclu prouvé au témoin 0,25 mm, le survol-Sceau
  vs drag-P2 = trois rAF séparés…). LE BLOQUANT : la barre contextuelle
  IGNORAIT LE VERROU — dix commandes de géométrie sans une garde, le même
  bloc verrouillé tenait au glisser (« n'a pas suivi ») puis BOUGEAIT à
  l'alignement un clic plus tard, sans un mot → le verrou vaut en ANCRE par
  UNE porte (lotLibre) : il compte dans l'enveloppe et donne sa taille en
  référence, ne reçoit jamais le patch, la phrase nomme le geste ;
  l'infobulle du cadenas mise à jour et LUE par un test. Réels : la garde
  d'égalisation testait le KIND pas la dimension (un TEXTE à hauteur 0 —
  champ sans min — aplatissait le lot en silence) → refus sur la dimension
  nulle quelle que soit la nature + plancher d'entrée QUI SUIT LA NATURE
  (les lignes restent atteignables) ; la distribution prenait le bord GAUCHE
  maximal (sur une carte normale — fond+titre+stat — le titre sautait SUR la
  stat) → l'enveloppe fait la portée, l'ordre est celui des centres, et
  L'INVARIANT DU LIVREUR S'EST RÉVÉLÉ IMPOSSIBLE (« aucun membre ne sort »
  quand les objets ne tiennent pas — l'invariant exact écrit, le
  chevauchement avoué avec son chiffre à l'écran) ; LE TÉMOIN DE TANGENCE
  PINNÉ (4 faces + 3 contrôles au millième — l'excuse de l'arrondi était
  fausse DE MESURE, 4e application de la leçon) et la tâche NE REVENDIQUE
  PLUS AUCUN témoin survivant. Mineurs : les comptes des messages de commit
  contredits par leurs diffs (mesurés et rectifiés au rapport — les totaux
  finaux exacts ; LA PROSE D'UN COMMIT SE MESURE AUSSI) ; le dépassement de
  procédure f0f7dbf (le livreur cochait sa case LIVRÉ — ronde/CLOSE
  intactes ; les cases sont à l'orchestrateur, acte pris) ; les gestes de
  lot agissent sur le VISIBLE (règle tranchée CONTRE Figma avec sa raison :
  l'œil de la rangée doit vouloir dire quelque chose — toast qui compte les
  masqués ignorés). Ronde : 344/344 type + 304 frame, banc Chrome ÉTENDU
  (cadenas par la rangée, B1/R1/R2 verts du premier coup).
- [x] CLOSE : leçons — (a) DIX COMMANDES NEUVES = DIX RENCONTRES AVEC LE
  VERROU (une écriture de géométrie qui n'a pas croisé lock n'est pas
  finie) ; (b) un invariant s'écrit APRÈS avoir cherché le cas qui le casse
  (celui du livreur était arithmétiquement impossible) ; (c) 4e témoin
  démasqué par la mesure — la tâche qui n'a pas de témoin honnête n'en
  revendique aucun ; (d) la prose des commits se mesure comme le reste.
  Dettes → T6 : la liste de blocs se lit du fond vers la surface vs les
  bandes fixes en sens Figma (les infobulles nomment l'équivalence — à
  arbitrer à l'œil) ; le redimensionnement de LOT (échelle d'enveloppe) non
  livré — l'enveloppe s'affiche pour que l'absence se voie ; la bande du
  Sceau vérifiée au banc node seul (sa preuve qui compte — le déterminisme
  d'export — est exécutée).

### T4 — Le verre, l'occlusion, l'ondulation tranchée (D5)
_GLASS_RECIPES ×3 + extensions au writer (PESÉES dans le GLB : transmission/
ior/volume relus aux octets), finish élargi au nœud material (miroir+parité),
AO exposée à l'UI, ondulation douce TRANCHÉE (mesure ou enterrement motivé).
Le viewer vérifié en réel (un artefact verre chargé, vu).
**Fichiers** : forge3d_scene.py, forge3d.py, mod-forge3d.js,
test_cards_forge3d.py.

- [x] LIVRÉ — commits `89aacc8`+`173eff1`+`f874033`+`1a9aa05` puis ronde
  `f17a53c`. _GLASS_RECIPES ×3 au patron holo (chaque paramètre justifié à
  la source : F0 4 %, le dépoli achromatique, la diffusion volumique pas
  comptée deux fois ; LE PIÈGE D'UNITÉS épinglé — thickness en mm-maillage,
  attenuationDistance en mètres-monde après le 0,001 de racine) ;
  extensionsUsed DISTINCT par recette, extensionsRequired absent, la
  chimère holo+verre LÈVE dans les deux sens, STL identique à l'octet sur
  les 5 finitions ; le viewer VU (verre 118 niveaux d'écart à travers, le
  voile du dépoli, le bleu du translucide). L'ONDULATION DOUCE LIVRÉE — la
  clause aux 3 aveux SOLDÉE : sinusoïde radiale (la phase sin ferme la
  singularité du centre), 6,843° nominal / 7,073° aux octets, mesurée au
  viewer (de face 15,04 = le maximum — la prose « dépend du rasage » était
  fausse dans le bon sens, phi se compte depuis +Y), PLAFOND DE RÉSOLUTION
  MESURÉ (256² vs 1024² : 0,122 niveau pour 7× moins d'octets, épinglé).
  Occlusion : le pipeline EXISTAIT (tile_maps demandait ao, le writer
  posait) — il manquait la vue et l'interrupteur ; défaut allumé = les
  octets d'avant AU BIT PRÈS (prouvé sur les deux arbres) ; corollaires
  honnêtes (l'aniso par famille — sha identiques, aucun aveu dû ; holo
  dérivé des listes servies). 169 tests.
- [x] Ronde adverse (opus) : 2 bloquants + 5 réels + 5 mineurs + 5 rejetés
  mesurés (BLEND+transmission autorisé et fonctionnel ; l'invariant
  Sceau-vs-verre TIENT — « l'explicite l'emporte » au bordereau pesé).
  B1 : LA RONDE DE MUTATION AVAIT TUÉ L'ORACLE, PAS LE PRODUIT — le mutant
  phare changeait une constante JAMAIS ATTEINTE (les recettes portent leur
  ripple explicite) et rougissait parce que le test dérivait son attendu de
  la même constante ; 3 essais du critique → 3 survivants réels (dont
  emissive retirable en silence — 0 occurrence dans 10 899 lignes de banc,
  sur LA constante fraîchement extraite). LA RÈGLE EST NÉE ET ÉCRITE : un
  mutant qui ne change pas le produit ne compte pas (empreinte à quatre
  faces) — ronde REJOUÉE : 42/42 changent le produit, 42 vus, 0 survivant,
  avec DEUX façons de s'absoudre rencontrées et écrites (l'empreinte trop
  étroite absolvait 18 vrais mutants ; un filtre -k périmé rapportait
  survivant un mutant qui mourait — LE FILTRE FAIT PARTIE DE L'ORACLE).
  B2 : 5 clés de production dans le banc de LA pièce payante — et le .env
  n'était pas la seule porte (HEYGEN venait de l'environnement du LANCEUR) :
  deux verrous, purge par FORME DE NOM (_KEY/_TOKEN/_SECRET/_PASSWORD),
  le test pèse le résultat. R1 : l'ondulation BYTE-INVISIBLE dès qu'une
  matière est posée (derive_maps dérive toujours normal — sha identiques
  avant/après sur le cas courant) → l'aveu au bordereau patron _SANS_HOLO +
  l'écran + la carte plus cuite pour la poubelle. R2 : sur l'anneau que la
  clause NOMME, verre et dépoli rendaient LA MÊME IMAGE (100,0 % des pixels,
  aplat blanc saturé — les 23,77 venaient d'une plaque texturée, jamais
  d'une extrusion) → GLASS_BASE_NU (le vert-bleu du verre flotté) agit où
  la physique le permet (translucide : 100 %→21 % saturés), l'aveu CHIFFRÉ
  partout ailleurs — plus jamais silencieux. R4 : le témoin volume était un
  COUVERCLE (3e de la phase — le drapeau closed vit sur le maillage, la
  garde jumelle deux lignes au-dessus) → porte à trois voies (fermé=volume,
  ouvert=paroi mince AVOUÉE), le témoin meurt. R5 : LE CHIFFRE A CONDAMNÉ
  L'AVEU — ΔE76 médian 86,4 entre props.color et la moyenne des cartes,
  16/18 matières encore #ffffff : « teinté par la couleur du nœud » ne
  teintait RIEN → la teinte vient de la carte basecolor désormais (le
  réglage = repli sans image). R3 : prose des caméras corrigée (le verdict
  LIVRÉE renforcé — de face est le maximum).
- [x] CLOSE : leçons — (a) UN MUTANT QUI NE CHANGE PAS LE PRODUIT NE COMPTE
  PAS, et l'empreinte comme le filtre font partie de l'oracle (la règle des
  rondes de mutation du chantier, désormais) ; (b) un banc se purge par la
  FORME DES NOMS de secrets, pas par une liste de fournisseurs ; (c) un
  aveu de teinte se mesure en ΔE contre la vérité qu'il prétend porter
  (86,4 = un défaut, pas un témoin) ; (d) 3e témoin-couvercle de la phase.
  Pour T6 à l'œil (~2 min) : le dépoli contre le verre clair au viewer, le
  translucide teinté par SA carte, l'anneau ondulé (subtil sur 1,2 mm —
  c'est sur un plan que le pli se voit), la case occlusion et ses phrases.

### T5 — LA CAMPAGNE RÉELLE (D2 — la seule tâche qui dépense)
Déploiement de la machinerie T1 → campagne sur le backend déployé (vraies
clés) : les 108 cases, plafond 6,00 $, journal centime par centime, le juge
trie, le bilan par case (TIENT/retouchée/sauvée/restée vectorielle avec ses
axes), le manifeste posé, P1 montre la série. Échantillon vérifié à l'œil
navigateur + le juge rejoué sur 10 cases au hasard depuis les fichiers servis.
**Prérequis** : T1 clos ; prix re-vérifiés LE JOUR MÊME ; l'utilisateur a déjà
donné l'opt-in (24/08) — le plafond et le journal sont la protection.

- [x] LIVRÉ — commits `d850346`+`8f3d769`+`f5f0e9a`+`1399e39`+`4f500aa` +
  le pin modèles `338a2d7` (orchestrateur). LA CAMPAGNE RÉELLE : enveloppe
  close à **5,892 $ / 6,00 $** (facturé ≈5,676 $ — 0,216 $ d'écriture
  prudente pour des appels refusés à la validation), 5 sessions, 54 cases
  tentées, **1 SERVIE** (`stained_tower`, voie FLUX, score **92,9 = le
  Król Lear authentique en aveugle**, 0 axe rouge, vérifiée sur les octets
  SERVIS + l'écran « 1/108 » + l'adoption setArt mesurée). Le mur machinerie
  a fermé la campagne de lui-même, reliquat avoué (0,108 $), AUCUN garde-fou
  contourné, AUCUN tir au-delà.
  CE QUE L'ENVELOPPE A ACHETÉ : (1) l'assurance de l'étape A a attrapé une
  régression de suite (le pin 39→49 du 3e lecteur de SLOT_DEFAULTS — que
  seule la suite complète pouvait voir) ; (2) TROIS défauts de machinerie
  réels corrigés en conditions réelles (cf_deploy aveugle à pricing.py —
  l'app servait nano-banana à prix null ; FLUX refuse >4 images/appel —
  deux tirs 4+2 ; le gabarit) ; (3) LE DIAGNOSTIC INVERSÉ : les générateurs
  SUR-OBÉISSENT à la retenue (ils vidaient la toile — 84/84 au-dessus du
  plafond de vide — l'hypothèse du brief était fausse, réfutée par l'agent
  SANS re-télécharger le corpus sous droits, dont il a refusé le
  téléchargement : le consentement est à l'utilisateur seul) ; (4) la
  preuve que LA BARRE EST ATTEIGNABLE ; (5) le pipeline entier prouvé
  (génération→juge→manifeste→écran→adoption). Trajectoire des sondes :
  méd 65,7 → 78,6 → 73,5 avec le pendule TRAVERSÉ TROIS FOIS (vider →
  éclairer → re-éclairer : « la borne et la pression vont ensemble » — le
  correctif final garde « dark » ET borne le point clair, déployé).
  L'agent a aussi avoué TROIS défauts de ses propres bancs (l'oracle qui
  cite l'accusé, le BOM+CRLF double piège, le contrôle sain rouge) et un
  4e (son banc accusait le produit d'un échec d'adoption qui était le sien
  — il lisait face.art, une clé inexistante).
- [x] Ronde adverse + corrections — T5 est une tâche d'OPÉRATIONS : ses
  arrêts-et-rapports (étape A, règle des 8 $, règle D, l'enveloppe) ONT ÉTÉ
  ses rondes, chacun vérifié par l'orchestrateur ; ses trois commits de
  machinerie portent tests + mutation (5/5, 6/6, 4/6 avec 2 équivalents-au-
  contrat avoués : un test qui garde des PROPRIÉTÉS laisse passer les
  mutants de PROSE, c'est voulu).
- [x] CLOSE : leçons — (a) L'ASSURANCE AVANT DE PAYER (la suite complète)
  attrape ce que les filtres par-fichier ne voient pas ; (b) le réel est le
  seul banc des intégrations de fournisseurs (3 défauts en 2 sondes) ;
  (c) UN RÉGLAGE À LA FOIS, et la borne avec la pression — le pendule coûte
  une sonde par traversée ; (d) un agent ne télécharge pas des œuvres sous
  droits sur l'ordre d'un autre agent, et ne relève JAMAIS un plafond
  d'argent. LA DÉCISION UTILISATEUR EST POSÉE (relever l'enveloppe ~2 $
  pour une sonde post-correctif / ~15 $ pour pousser au taux courant —
  déconseillé / en rester là : 1/108 honnête et reprenable). Dettes → T6 :
  les textes « par session » (route + écran) vs l'enveloppe TOTALE réelle ;
  les 6×404 P9 sur deck neuf ; LES 293 CANDIDATS PERDANTS (261,6 Mo) à
  purger-ou-garder.

### T6 — Intégration, preuve, poussée
Un deck témoin remonté de bout en bout (série Wałkuski + formes/flèches +
gemme déplacée + bordures custom + artefact 3D verre dépoli), suite complète
quiescente, lint, banc de contrat, déploiement final, vérification navigateur,
mémoire, poussée.

- [ ] LIVRÉ — commits `52c522a` (les deux dettes de code) + `8624442` (le banc
  de contrat). **LES DETTES ROUTÉES.** (1) « par session » → ENVELOPPE
  TOTALE aux DEUX textes servis (le devis de la route, le compteur de P1),
  contrôlés À L'ÉGALITÉ — une sous-chaîne resterait verte sur une phrase qui
  garde les deux formules — et le balayage de la pièce porte sur les CHAÎNES
  seules : le commentaire qui documente la dette CITE forcément la formule
  fautive (le grep de prose, 4e rencontre). (2) LES SIX 404 DE P9 : ils
  étaient déjà attrapés côté JavaScript ; le bruit vivait côté NAVIGATEUR,
  au niveau réseau, hors de portée de tout `try`. Nouvelle route
  `GET /forge3d/layers/<carte>` — les trois côtés en UNE réponse qui existe
  toujours, `null` par côté absent. MESURÉ SUR L'APP SERVIE, avant/après, en
  posant l'ancien JS puis en le reprenant : **6 requêtes toutes en 404 → 2
  requêtes toutes deux en 200**, même page, même jeu. L'inventaire mis en
  cache dans `/info` aurait été la solution la moins chère et la plus fausse
  (P10 écrit le manifeste de capture depuis une AUTRE pièce) ; la lecture est
  fraîche à chaque appel, et le repli sur les trois sondes reste — TOUS les
  cas déjà écrits du banc node passent par lui, il n'est pas mort.
  (3) LA PURGE DES CANDIDATS PERDANTS : 357 `gen_*` au magasin, sondés
  contre TOUS les consommateurs (toutes les colonnes texte de la base, tout
  fichier texte sous DATA_ROOT — les 2 206 documents de jeu compris —, et le
  dépôt) ; les journaux ne comptent PAS comme consommateurs (une trace n'est
  pas une référence). **293 fichiers non consommés et datés du jour de la
  campagne = 261,6 Mo**, exactement le chiffre transmis par T5, retrouvé par
  une voie indépendante. Magasin 411 → 118 fichiers, 359,7 → 98,1 Mo. GARDÉS
  et DITS : la case servie `gen_6c573ebd.png` (référencée deux fois : le
  manifeste ET `deck_631a955e/meta.json`), 19 autres consommés (posts
  programmés, jobs, graphes Studio, deux matières), et **44 orphelins
  ANTÉRIEURS à la campagne (8,5 Mo) laissés en place** — ils ne sont pas de
  cette campagne, et « en cas de doute on garde ». Les 293 sont DÉPLACÉS
  (`DATA_ROOT/rebut_serie_walkuski_2026-08-25/`, avec son `_POURQUOI.txt`),
  pas détruits : le magasin est propre et l'écran ne les voit plus, le geste
  irréversible reste à l'utilisateur. Manifeste INTACT — 1 case servie, 11
  refus avec leurs scores, 5,892 $ / 6,00 $. (4) LE TÉMOIN `refreshSel`
  SOLDÉ À L'ŒIL : la vignette de la case servie porte bien `data-ai` ET
  `data-cat` ; cliquée, elle s'allume, et elle est **la seule** allumée —
  l'ordre inverse n'aurait rien allumé du tout.
  **LE DECK TÉMOIN « Vitrine Deepotus » (`deck_14154201`)**, monté au
  navigateur : série active (l'écran lit « enveloppe totale », la case
  `stained_tower` adoptée en `img:gen_6c573ebd.png`, les autres vignettes
  marquées « vectoriel ») ; P3 = flèche à DEUX bouts armés (tête 3 mm),
  ellipse à boîte carrée (le halo), rect à contour `plate_stroke` #e0b64a de
  0,4 mm tapé au clavier ; multi-sélection de 3 par Maj+clics RÉELS sur la
  carte, ALIGNER (centre vertical) → rect 20→27, flèche 44→32, **l'ellipse
  VERROUILLÉE tient à 30 et la phrase sort** (« 1 bloc(s) verrouillé(s) n'ont
  pas été alignés »), DISTRIBUER → espaces 4,000 / 4,000 mm, extrêmes fixes ;
  **un guide qui aimante pendant un vrai glisser** — le bord droit du rect
  tombe sur 48,590 mm = le bord droit du slot `artist` au micron, là où le
  glisser nu aurait donné 48,407 et la grille 0,25 mm 48,5. P2 = famille
  Filigrane/Légendaire, gemme GLISSÉE à la main (50,42 × 12,85 mm, r 5,64) avec
  son aveu, **Ctrl+Z rend l'automatique** (`null/null/null`, « logement de
  atk ») et Ctrl+Y la repose, ornement de coin ×1,3, liseré de fenêtre 0,5 mm,
  Sceau allumé en portée **écran + 3D**. P9 = artefact construit (12
  éléments, GLB **8 380 276 octets**) : `extensionsUsed` porte
  **transmission + ior + specular** (+ clearcoat/iridescence du Sceau),
  `extensionsRequired` **ABSENT** ; le matériau `illustration` en
  verre-dépoli pèse `transmission=1.0 ior=1.5 specular=0.5` avec sa carte
  d'occlusion (`illustration-ao`, la case cochée) ; et **l'ondulation se lit
  exactement où la clause le dit** — `cadre`, `cadre_verso` et
  `extrude_sceau`, qui n'ont AUCUN nœud matière, portent tous
  `cadre-ondulation` en carte normale, tandis qu'`illustration`, qui en a un,
  porte `illustration-normal` : l'aveu R1 de T4 vérifié aux octets servis.
  Le bordereau dit l'habillage automatique de l'extrusion (« l'extrusion de
  contour « sceau » EST le corps du Sceau du document — son métal et sa
  largeur viennent de lui ») et le refus nommé du STL. **Viewer 3D chargé**
  (`loaded=true`, dimensions 0,063 × 0,088 × 0,0018 m = la carte au
  millimètre), le Sceau arc-en-ciel visible sur la tranche.
  **Console : 0 erreur sur un chargement propre** — 60 requêtes, toutes en
  200 ou 304, les deux `layers/c01` comprises.
  **DETTE TRANSMISE, NON LIVRÉE — `models.py:1260 elements: []`.** La moitié
  restante n'est pas une implémentation, c'est QUATRE arbitrages produit que
  le plan ne tranche pas : (a) contre quelle grille « standard » se mesure un
  slot « non standard » — le seul repère connu du backend est le modèle
  d'origine (`preset = "modele:<id>"`), et un jeu né d'un gabarit local ou
  monté à la main n'en a AUCUN (la dette resterait à moitié ouverte) ;
  (b) les extras restent-ils AUSSI dans `type.slots` (sans quoi appliquer le
  modèle perd ce qu'il devait porter) ; (c) toute forme devient-elle un
  élément, ou seulement celles hors grille ; (d) un élément par slot extra,
  ou un élément qui GROUPE les slots parents (le patron d'usine groupe —
  « 7e statistique » — et rien dans le code ne dit comment deviner le
  groupe). Estimation à 3–4 h avec RED d'abord, ~8 tests et la ronde de
  mutation, une fois les quatre arbitrages posés — au-delà du plafond de 2 h,
  donc pas de demi-livraison. **Vu en chemin et déjà mesuré** : `naitre` →
  `normSlots` renomme les identifiants en collision, donc la re-pose d'un
  élément ne demande AUCUN changement d'écran ; le travail est backend seul.
- [x] Ronde adverse (sonnet, revue courte pré-poussée) : verdict « la poussée
  peut partir » — UNE trouvaille cosmétique (le banc de contrat reconnaît son
  modèle par ÉGALITÉ DE LIBELLÉ — la classe du défaut corrigé déplacée d'un
  cran, probabilité quasi nulle, transmise : suffixer d'un jeton). Vérifiés
  en direct : la purge (293+1 au rebut, 5 fichiers au hasard à 0 référence
  dans 2 206 meta.json + le manifeste + la base, la case servie toujours au
  magasin ET servie 200) ; la route layers (fullmatch \Z, traversée en octets
  littéraux → 404, le %0A → 400, avec un FAUX POSITIF creusé et résolu —
  c'était curl qui normalisait, pas une faille) ; les textes « enveloppe
  totale » lus SERVIS ; deepotus-fragments protégé et présent ; health 200 +
  mock + 0 écart ; 147 face + 174 forge3d + lint verts.
- [x] CLOSE DE PHASE — consigne ci-dessous.

## 4. Consigne de sortie de phase

- [x] **PHASE 5 CLOSE 25/08** : les trois axes de la demande utilisateur
  LIVRÉS — la voie de série Wałkuski (skill mesuré, machinerie
  devis/enveloppe, campagne RÉELLE close à 5,892 $/6,00 $ : 1/108 servie à
  92,9 = LE SCORE DU KRÓL LEAR AUTHENTIQUE — la barre prouvée atteignable,
  le correctif final déployé, LA DÉCISION UTILISATEUR POSÉE : relever
  l'enveloppe ~2 $ pour une sonde post-correctif / ~15 $ au taux courant
  déconseillé / en rester à 1/108 honnête ; SERIE_PLAFOND_USD ne se touche
  que sur son ordre) ; l'éditabilité Figma entière (formes/flèches/ellipse,
  multi-sélection au verrou-ancre, guides au micron, gemme et ornements
  libérés, phase-pointeur écran-seul) ; le verre 3D (3 recettes pesées aux
  octets, occlusion, l'ondulation aux 3 aveux SOLDÉE). Le deck témoin
  `deck_14154201` « Vitrine Deepotus » traverse tout, mesuré. Suite complète
  64/64 (1 599 s), lint 10/10, banc de contrat tenu (et son défaut
  DESTRUCTEUR corrigé — il a failli emporter deepotus-fragments), déployé à
  0 écart, ~37 commits poussés en clôture. Dépense totale de phase :
  5,892 $ au registre (≈5,68 $ facturés), zéro hors campagne, aucun
  garde-fou contourné.
- **Restes attendus de l'utilisateur** : LA DÉCISION D'ENVELOPPE (la série) ;
  l'œil ~5 min (Vitrine Deepotus : la carte Wałkuski + Sceau, la gemme, les
  formes, le verre dépoli + l'ondulation au viewer) ; le rebut
  `rebut_serie_walkuski_2026-08-25/` (261,6 Mo) à supprimer ou garder ; les
  92 faces fabricant (toujours à fournir) ; meshy-7/décor IA/rembg réels
  (opt-ins distincts).
- **Transmis (chantier suivant)** : elements:[] des modèles perso (4
  arbitrages produit posés noir sur blanc ci-dessus, est. 3-4 h) ;
  MESHY_MOCK ne vit que dans l'environnement du LANCEUR (toute relance du
  backend le perd — l'écrire au .env est une décision produit) ; la preuve
  d'empilement non déterministe au 1er tour post-édition (et son message qui
  accuse les mauvaises couches) ; placeMenu déborde sous 618 px ; 2 206
  jeux/8,36 Go dans outputs/decks (2 110 « Nouveau jeu » de bancs, GC à
  trancher) ; le jeton du banc de contrat ; le calque d'image encore mention
  du cadre ; la liste fond-vers-surface vs bandes Figma ; le
  redimensionnement de LOT ; contour SVG d'extrude (v2, depuis la phase 4).
