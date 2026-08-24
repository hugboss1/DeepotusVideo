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

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T2 — Les éléments libérés + les formes + les bordures (D3)
Gemme/ornements édités (position/taille persistées, défaut calculé, aveu du
gel), KINDS rect/ellipse/line/arrow (+ palette d'éléments des modèles perso
NOURRIE — le transmis), plate_stroke sur toute zone, liseré propre de la
fenêtre P2. Parité miroirs, silhouettes intactes (les gemmes déplacées ne
cassent pas la QA — vérifier), norm_slots étendu des deux côtés.
**Fichiers** : mod-type.js, type.py, test_cards_type.py, mod-frame.js,
frame.py, test_cards_frame.py.

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T3 — Les outils Figma (D4)
Multi-sélection, aligner/distribuer/égaliser, rotation à la poignée, guides
objet-à-objet débrayables, gestes z, un pas d'undo par geste, phase-pointeur
du Sceau. Bancs node sur les fonctions pures (aligne/distribue/aimante), et la
vérification Chrome du geste réel.
**Fichiers** : mod-type.js, test_cards_type.py (+ mod-frame.js si la
sélection s'étend aux éléments P2 — dire lequel possède quoi AVANT de coder).

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T4 — Le verre, l'occlusion, l'ondulation tranchée (D5)
_GLASS_RECIPES ×3 + extensions au writer (PESÉES dans le GLB : transmission/
ior/volume relus aux octets), finish élargi au nœud material (miroir+parité),
AO exposée à l'UI, ondulation douce TRANCHÉE (mesure ou enterrement motivé).
Le viewer vérifié en réel (un artefact verre chargé, vu).
**Fichiers** : forge3d_scene.py, forge3d.py, mod-forge3d.js,
test_cards_forge3d.py.

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T5 — LA CAMPAGNE RÉELLE (D2 — la seule tâche qui dépense)
Déploiement de la machinerie T1 → campagne sur le backend déployé (vraies
clés) : les 108 cases, plafond 6,00 $, journal centime par centime, le juge
trie, le bilan par case (TIENT/retouchée/sauvée/restée vectorielle avec ses
axes), le manifeste posé, P1 montre la série. Échantillon vérifié à l'œil
navigateur + le juge rejoué sur 10 cases au hasard depuis les fichiers servis.
**Prérequis** : T1 clos ; prix re-vérifiés LE JOUR MÊME ; l'utilisateur a déjà
donné l'opt-in (24/08) — le plafond et le journal sont la protection.

- [ ] LIVRÉ (le bilan de campagne : cases, dépense totale, refus)
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T6 — Intégration, preuve, poussée
Un deck témoin remonté de bout en bout (série Wałkuski + formes/flèches +
gemme déplacée + bordures custom + artefact 3D verre dépoli), suite complète
quiescente, lint, banc de contrat, déploiement final, vérification navigateur,
mémoire, poussée.

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE DE PHASE

## 4. Consigne de sortie (à remplir)

- [ ] Bilan, dépense réelle totale vs plafond, poussée.
- Restes attendus de l'utilisateur : l'œil sur la série (~5 min), les 92 faces
  fabricant (toujours à fournir), meshy-7/décor IA/rembg réels (opt-ins
  distincts de la campagne).
