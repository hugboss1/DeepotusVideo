# Cardforge — Phase 6 : la mise au ton, les plans du décor, les éléments

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking.

**Goal :** Rescaper gratuitement des cases Wałkuski par une mise au ton
déterministe (rebut + voie de campagne), rendre le décor haut obéissant aux
plans de l'éditeur (bug gemme/texte), pérenniser MESHY_MOCK, préparer le
chantier « tous les éléments ajustables », inventorier le GC des bancs, solder
les finitions transmises.

**Architecture :** Backend seul pour T1/T2/T5 (face.py + style_walkuski +
config data-side) ; frontend source `frontend/cardforge/js` pour T3/T6 (pas le
bundle patché — le Cardforge est en fichiers isolés, déployés par le verrou
cardforge). T4 est BLOQUÉ sur 4 arbitrages utilisateur, posés en fin de plan.

**Tech stack :** Python 3 (FastAPI, PIL), tests pytest UN PROCESSUS PAR
FICHIER (`scripts/run-tests.ps1`), JS vanilla (qa/ banc de contrat node),
zéro dépense réelle partout (sentinelles clés, aucun `_payer` nouveau).

**Contraintes d'argent (inchangées) :** `SERIE_PLAFOND_USD` ne se touche que
sur ordre utilisateur ; la mise au ton est GRATUITE par construction (PIL pur,
aucun appel fournisseur) ; les opt-ins (meshy-7, décor IA, rembg) restent à
l'utilisateur ; le juge (fiche + verifier) ne se relâche JAMAIS.

---

## 1. Faits de reconnaissance (25/08, vérifiés sur pièces)

- **Campagne close** : 2/108 (stained_tower 92,9 · vista_monolith 78,6),
  7,467 $/8 $, reste 0,533 $. `vista_pines` refusée à 87,5 avec 2 axes rouges
  TOUS tonals (part claire, L médian) — témoin idéal du rescapage.
- **Le rebut** `DATA_ROOT/rebut_serie_walkuski_2026-08-25/` : 292 png + 1 jpg
  + `_POURQUOI.txt`. Les `gen_*.png` sont des OCTETS BRUTS fournisseur
  (JFIF/JPEG sous extension .png), AUCUNE métadonnée interne. La
  correspondance candidat→case n'existe QUE dans le journal.
- **Le journal** `DATA_ROOT/logs/deepotus-2026-08-25.log` (73 Ko) couvre LES
  DEUX enveloppes (01:41→10:02, `plafond 6.00` puis `8.00`) : lignes
  `_payer` = `cardforge/serie <case> : <modele> xN = ...` ; lignes FLUX =
  `FLUX: saved N image(s), seed=S: ['gen_a.png', ...]` (112 lignes gen_).
- **La graine FLUX est LA CLÉ DU MAPPING** : `graine = fnv1a32("walkuski:" +
  case) & 0x7FFFFFFF` (face.py:2078), tirée en 4+2 avec `seed` puis `seed+1`
  (le correctif « FLUX max 4 img/appel »). Le seed du log identifie la case
  SANS appariement temporel. Les tirs nano-banana/gpt-image-2 (1 image) n'ont
  pas de seed → appariement temporel `_payer`→sauvegarde suivante, sinon
  COMPTÉS non mappés (couverture honnête).
- **L'échelle** (`_fabriquer_case`, face.py:2033) : flux×6 → `_juger` (boucle
  `juger_image` = `style_walkuski.mesurer` + `verifier` vs `fiche_style()`) →
  `meilleur_candidat` → retouche banana si A RETOUCHER → gpt → refus.
  `_payer` journalise AVANT chaque tir ; `manifeste_fusionner(case, ligne,
  gagnee, delta_usd)` fusionne sur disque, `gagnee=True` pop le refus.
- **Le juge** : `backend/app/services/cards/style_walkuski.py` (copie datée du
  skill), fiche `metriques[cle] = {med, ...}`, verdicts via `verifier()` →
  `lignes[{cle, metrique, valeur, etat, critique}]`. `juger_image` ~90 ms.
- **MESHY_MOCK** : `config.py:90` (`MESHY_MOCK: bool = False`), et le `.env`
  du DATA_ROOT est chargé `override=True` AVANT `Settings()`
  (config.py:46-51) → une ligne au .env survit à toute relance. Le backend
  qui tourne (2.4.0, orphelin pré-déploiement) porte encore le mock du
  lanceur ; la PROCHAINE relance sert la 2.5.0 et le perdrait sans T2.
- **Le décor haut** : le peintre P3 (mod-type.js) peint en STRATES —
  cadre de base (40) → calques utilisateur (l'ordre de la liste EST l'ordre
  de peinture ; boutons devant/derrière/tout devant/tout derrière,
  mod-type.js:754-762) → décor haut (70, `resDecor`, mod-type.js:3542-3554)
  TOUJOURS AU-DESSUS. La gemme est un élément du plan d'occupation
  (`placeGem`, mod-frame.js:1041 → `{id:"gem", z:70, movable:true, manual}`),
  le bandeau aussi (`placeBanner`, mod-frame.js:983 → `{id:"banner", z:70,
  movable:true}`). D'où LE BUG : une gemme déplacée à la main couvre 100 %
  du texte, aucun réglage de plan des calques ne peut la battre.
- **elements:[]** : `models.py:1259-1261` — un modèle perso n'a pas de palette
  d'éléments (contrat §6.1 tenu par une liste vide). Les 4 arbitrages de la
  dette sont posés au plan de phase 5 (§T6) et repris en §4 ci-dessous.
- **v2.5.0 publiée** (release GitHub + installeur 123,5 Mio, sha `da4275…`),
  branche `claude/audit-cleanup-2026-08` propre sur `0dd05af` = tag v2.5.0.

## 2. Décisions de conception

- **D1 — La passe vise les grandeurs du juge, PAR le juge.** Les trois
  métriques tonales (L médian, part claire L>200, part sombre L<64) se
  calculent par les fonctions MÊMES de `style_walkuski` (refactor
  d'exposition : une aide `tonales(img) -> dict` que `mesurer` appelle —
  AUCUN changement de verdict, épinglé par un test d'or avant/après sur
  2 images du magasin). La courbe = points noir/blanc + gamma appliqués en
  LUT sur la luminance du mesureur ; premier jet ANALYTIQUE depuis
  l'histogramme, puis raffinement en grille déterministe bornée (≤ 27
  évaluations tonales, pas de `juger_image` dans la boucle). AUCUN aléa.
  Le fichier ajusté est un NOUVEAU fichier ; on ne sert QUE ce que le juge a
  jugé (l'ajustée servie = l'ajustée jugée). La fiche et `verifier` ne
  changent PAS (la barre prouvée 2× reste la barre).
- **D2 — La voie de campagne gagne un frère ajusté par candidat rescuable.**
  Dans `_fabriquer_case`, après le jugement d'un lot : chaque candidat
  non-TIENT dont TOUS les `axes_rouges` sont tonals produit UN frère mis au
  ton, jugé, ajouté aux notes (marqué `mise_au_ton: True`). Zéro `_payer`
  ajouté, zéro appel fournisseur (test sentinelle qui fait échouer tout
  `_tirer_*`). `meilleur_candidat` départage naturellement.
- **D3 — Le rescapage du rebut est une route SANS dépense, dry-run d'abord.**
  `POST /serie/rescaper` : sans corps → RAPPORT (ce qui serait tenté, la
  couverture du mapping, rien d'écrit) ; `{"appliquer": true}` → sert. Le
  mapping : seeds FLUX recalculés depuis les cases du manifeste (`refus` en
  tête), appariement temporel pour banana/gpt, fichiers pris dans le rebut
  (chemin par défaut `rebut_serie_walkuski_2026-08-25`, surchargable
  `{"dossier": ...}`). Non-mappés et absents COMPTÉS au rapport (pas de
  plafonnement silencieux). Un gagnant TIENT → PNG RÉEL écrit au magasin
  (nouveau nom `gen_<hex>.png`, PIL save, pas les octets bruts),
  `manifeste_fusionner(case, ligne{..., prix_usd: 0.0, voie: <voie
  d'origine>, mise_au_ton: True, rescape: <horodate>}, gagnee=True,
  delta_usd=0.0)` — la dépense totale NE BOUGE PAS. Cases déjà servies
  sautées (idempotent). Le rebut n'est PAS modifié (la suppression reste à
  l'utilisateur).
- **D4 — MESHY_MOCK=1 s'écrit au .env du DATA_ROOT** (décision produit
  validée par l'utilisateur avec l'ordre d'attaque) : l'état devient
  explicite et durable ; le Meshy réel = éditer/retirer la ligne (opt-in
  conscient). Le repo n'est pas touché (c'est une donnée utilisateur) ; le
  CHANGELOG de la phase le documente.
- **D5 — Un ornement posé à la main descend dans la pile des calques.** La
  gemme (et le bandeau une fois libéré) en régime MANUEL quitte la strate 70
  et devient membre de l'ordre réordonnable (devant/derrière le voient) ; en
  régime automatique, la strate 70 demeure (le décor protège les coins par
  construction). Écran ET export par le même chemin (le painter ne distingue
  pas — invariant phase 5). Le message de la preuve d'empilement accuse les
  couches RÉELLEMENT en cause, et sa non-détermination au 1er tour
  post-édition se corrige à la même occasion (même zone). `placeMenu` se
  borne au viewport (≥ 320 px) au lieu de déborder sous 618 px.
- **D6 — (BLOQUÉ utilisateur) Les éléments.** Voir §4 : 4 arbitrages + la
  demande neuve « tous les éléments ajustables, remplaçables par des formes
  primitives ». Aucun code avant les réponses.
- **D7 — Le GC déplace au rebut, il ne supprime pas.** Critère STRICT : nom
  exactement « Nouveau jeu » ET aucun contenu adopté/importé (le dossier du
  deck ne contient que ce que le squelette écrit). Outil
  `scripts/gc_decks.py` : `--dry-run` par défaut (inventaire chiffré),
  `--deplacer` → `DATA_ROOT/rebut_decks_<date>/` + un `_POURQUOI.txt` au
  patron du rebut de série. La suppression définitive appartient à
  l'utilisateur.

## 3. Tâches

### T1 — La mise au ton déterministe (D1, D2, D3)

**Fichiers :**
- Modifier : `backend/app/services/cards/style_walkuski.py` (exposer
  `tonales`), `backend/app/services/cards/face.py` (la passe, la voie, la
  route rescaper)
- Créer : `backend/tests/test_cards_serie_ton.py` (NOUVEAU fichier — la règle
  un-processus-par-fichier garde la suite rapide)

- [x] **T1-A (RED)** : écrire `test_cards_serie_ton.py` — les tests d'or du
  refactor juge (métriques identiques avant/après sur 2 PNG synthétiques
  fabriqués dans le test), `tonales()` existe et rend les 3 clés de la fiche,
  `mise_au_ton` : (1) image trop claire synthétique → les 3 métriques entrent
  dans leurs bandes ; (2) image déjà dans les bandes → octets de sortie
  IDENTIQUES sur deux appels (déterminisme) et score tonal jamais dégradé ;
  (3) axes non tonals intouchés par la promesse (la fonction ne prétend
  corriger que le ton : le rapport liste `axes_vises`). Lancer : ROUGE.
- [x] **T1-B (GREEN)** : implémenter `tonales()` dans style_walkuski (extraite
  de `mesurer`, appelée par lui), puis `mise_au_ton(src, dst, fiche) -> dict`
  dans face.py (premier jet analytique noir/blanc/gamma depuis l'histogramme
  de luminance, raffinement grille 3×3×3, LUT PIL `point`). Suite du fichier
  verte.
- [x] **T1-C (RED)** : tests de la voie — `_fabriquer_case` monkey-patché
  (tirages factices, juge réel sur images synthétiques) : un candidat « HORS
  STYLE aux axes tous tonals » gagne un frère ajusté qui TIENT et la case est
  servie SANS tir supplémentaire (sentinelle : tout `_tirer_*` non prévu
  lève) ; un candidat aux axes mixtes n'en gagne pas ; le journal de dépense
  est inchangé par la passe. Lancer : ROUGE.
- [x] **T1-D (GREEN)** : brancher la passe dans `_fabriquer_case` (après
  chaque `_juger` de lot, avant `meilleur_candidat`). Vert.
- [x] **T1-E (RED)** : tests du rescapage — DATA_ROOT temporaire avec faux
  journal (lignes `_payer` + `FLUX: saved` aux seeds fnv1a32 réels), faux
  rebut (images synthétiques nommées comme le journal), manifeste avec refus :
  dry-run rend le rapport (mappées/non mappées/absentes, rien d'écrit) ;
  `{"appliquer": true}` sert la case rescuable, `depense_totale_usd`
  INCHANGÉE, `prix_usd: 0.0`, refus popé, magasin peuplé d'un PNG réel ;
  re-POST → `deja_servie` (idempotent) ; clés fournisseur neutralisées au
  banc (patron des tests de campagne existants). Lancer : ROUGE.
- [x] **T1-F (GREEN)** : implémenter le parseur de journal (regex `[0-9]`,
  jamais `\d` — parité multi-langages) + `POST /serie/rescaper`. Vert, puis
  la SUITE ENTIÈRE cards (`scripts/run-tests.ps1` sur les fichiers cards) :
  verte. **RELEVÉ : 11/11 serie_ton + 147/147 face** ; le juge recopié au
  skill et RE-ÉPINGLÉ (`copie_le` 25/08, sha `81a0e9e5…` — le refactor
  `tonales()` appartient au mesureur, la copie ne diverge pas).
- [x] **T1-G** : commit `6e8ea1e`.
- [x] **T1-H (RÉEL) — LE RESCAPAGE A GAGNÉ 2 CASES, 0,000 $.** Dry-run réel :
  16 journaux lus, 11 cases tentables, 234 candidats mappés par la graine,
  42 non-mappés (tirs gpt/banana sans nom au journal) + 73 absents COMPTÉS,
  stained_tower sautée (déjà servie). `{"appliquer": true}` :
  **vista_pines 87,5→93,8 TIENT** (le témoin prédit) et **vista_tower
  65,6→78,1 TIENT** ; les 9 autres butent sur des rouges NON tonals
  (68,8–82,1, chroma/part de vide — hors du champ promis, dit au rapport).
  `depense_totale_usd` 7,467 INCHANGÉE, manifeste 4/108, `prix_usd: 0.0` +
  `mise_au_ton` + `source_rebut` sur les deux lignes, le rebut intact.
- [x] **T1-I (RÉEL) — LA RELANCE DU 26/08 : +6 CASES SUR 7 SONDES, 0,486 $,
  L'ENVELOPPE ÉPUISÉE.** Le rebut supprimé (§4bis), la relance = reprise de
  la GÉNÉRATION par la voie armée de la mise au ton (D2/T1-D), sur des cases
  JAMAIS tentées, variées en familles ET en sujets — la campagne close
  n'avait vu que les 13 premières du catalogue. Protocole tenu à chaque tir :
  `?cases=<case>` (une case à la fois), POST nu → devis relu, puis la MÊME
  requête `{"confirmer": true}` ; tarif du jour RELU au devis : nano-banana
  0,039 (et non 0,02 au 25/08) → échelle 0,177 $/case, 3 ouvrables au départ
  (reste 0,533). **Six servies** :
  - `vista_citadel` ocre, flux, **84,4 TIENT**, 0,018 $ (`gen_440bed3b_ton`)
  - `stained_wolf` rouge, flux, **87,5 TIENT**, 0,018 $ (`gen_1a8bcbae_ton`)
  - `depths_whale` violet, gpt, **85,7 TIENT**, 0,138 $ (`gen_0368bdc2_ton`)
  - `vista_sphinx` graphite, flux, **82,1 TIENT**, 0,018 $ (`gen_e76b70b4` —
    la seule DIRECTE, sans mise au ton)
  - `vista_portal` ocre, flux, **93,8 TIENT**, 0,018 $ (`gen_b4096cfb_ton`)
  - `vista_serpent` ocre, gpt, **89,3 TIENT**, 0,138 $ (`gen_36dfe11a_ton`)
  Cinq des six gagnantes sont des FRÈRES AJUSTÉS (`mise_au_ton: true`, img
  `*_ton.png`) : c'est la voie en ligne qui porte le taux de 2/66 (campagne
  close) à 6/7 — et la voie gpt-image-2 GAGNE désormais (2 cases : ses refus
  d'hier n'étaient que tonals, le frère gratuit les rentre). UN refus :
  `backlight_grimoire` (ocre, gpt, 85,7 HORS STYLE, 0,138 $) — la mise au
  ton a TOURNÉ (`mise_au_ton: true`) mais `part claire (L>200)` RESTE rouge
  (écarts : L p95, étendue tonale) : le contre-jour exige plus de lumière
  que la courbe ne peut en rentrer sans casser l'étendue — backlight est
  0/3 toutes époques, structurellement dure, à ne pas re-sonder sans levier
  neuf. Compositions : vista INVAINCUE 6/6 ; les 4 familles sont servies
  (ocre 6 · rouge 2 · violet 1 · graphite 1). **Série 10/108, dépense
  7,953 $/8,00 $ au manifeste relu, reste 0,047 $ < échelle 0,177 → PLUS
  AUCUNE case ouvrable : relever l'enveloppe ou clore appartient à
  l'utilisateur.**
- [x] **T1-J (RÉEL) — L'ENVELOPPE À 10 $ (ordre du 26/08) : +14 CASES SUR
  26 SONDES, LA SÉRIE À 24/108, LE MUR REFERMÉ À 9,900 $.** L'ordre
  utilisateur explicite (« relève l'enveloppe à 10$ ») est arrivé sur le
  rapport T1-I. Le relèvement est un commit SÉPARÉ (`5eeb4fe`) :
  `SERIE_PLAFOND_USD` 8,00 → 10,00 (l'historique 6 → 8 → 10 au
  commentaire), pins retendus dans test_cards_face.py (état/devis à 10,
  reliquat 2,92 → 4,92, frontière du mur 9+1 / 9+1,01, plafond dur 4 → 5
  cases, ratio du devis 1,91×), suites cards_face 147 et serie_ton 11
  VERTES au harnais ; déployé par copie sha-vérifiée vers l'app installée
  (le face.py installé était identique au dépôt), stop.ps1 + relance
  uvicorn (santé en 2 s, 2.5.0), et le devis machine a dit le mur neuf :
  reste 2,047, 11 ouvrables. **Quatorze servies** (toutes voie flux
  0,018 $ ; 8 par frère ajusté, 6 directes) : stained_monolith graphite
  **100,0** (LE PREMIER SCORE PARFAIT — un frère ajusté) · stained_golem
  rouge **96,4** (record des directes) · medallion_wolf ocre 93,8 ·
  stained_sphinx ocre 93,8 · medallion_crystals ocre 92,9 ·
  stained_crystals ocre 92,9 · vista_crystals ocre 89,3 · heraldry_wolf
  ocre 89,3 · vista_wolf ocre 87,5 · medallion_sphinx ocre 85,7 ·
  heraldry_crystals graphite 85,7 · vista_ship graphite 84,4 ·
  medallion_monolith graphite 84,4 · stained_citadel rouge 78,6. DOUZE
  refus (1,617 $) en trois modes : (a) « gpt trop clair » ×6 — flux rate,
  gpt rend une image dont `part claire` RESTE rouge après mise au ton
  (vista_dragon 71,4, depths_knight 78,6, stained_archer 85,7,
  stained_serpent 78,6, vista_whale 62,5, depths_wolf 78,6) ; (b) trop
  plein/saturé (non tonal, hors du champ de la passe) — vista_phoenix
  78,6, stained_beacon 82,1, vista_golem 68,8, heraldry_monolith 85,7,
  depths_citadel 78,1 ; (c) heraldry_sphinx 75,0 A RETOUCHER à l'échelle
  COMPLÈTE 0,177 (seul tir banana du jour). LES RÉGULARITÉS MESURÉES :
  les 18 sujets ont tous été sondés ≥ 1 fois ; 5 compositions sur 6 ont
  servi (vista 10 · stained 7 · medallion 4 · heraldry 2 · depths 1 —
  backlight 0, structurelle) ; les sujets « masse sombre » portent
  (crystals 4/4, wolf 4/5, sphinx 3/4, monolith 3/5, citadel 2/3) quand
  les lumineux et les figures humaines échouent (phoenix, dragon, beacon,
  knight, archer : 0/5) ; 22 des 24 cases servies l'ont été par flux
  (0,018 $ ou 0 $ rescapées), 2 par gpt. **Bilan du 26/08, les deux
  enveloppes : la série passe de 4/108 à 24/108 (+20) pour 2,433 $ — 20
  servies sur 33 sondes (61 %), contre 2 directes sur 66 tirs à la
  campagne close ; 13 des 20 gagnantes sont des frères ajustés. État
  final au manifeste relu : dépense 9,900 $/10,00 $, reste 0,100 $ <
  échelle 0,177 → 0 case ouvrable, le devis machine le confirme. La
  suite (relever encore, ou clore à 24) appartient à l'utilisateur.**
- [x] **T1-K (RÉEL) — L'ENVELOPPE À 12 $ (second ordre du 26/08) : +10 CASES
  SUR 22 SONDES, LA SÉRIE À 34/108, LE MUR REFERMÉ À 11,853 $.** Relèvement
  au commit séparé `d9fe431` (10,00 → 12,00 ; pins retendus dont la garde
  d'ouverture RE-DÉRIVÉE — à 12 ce sont DEUX cases de banc qui s'ouvrent,
  10,16 payés / reliquat 1,84 avoué / journal 6 —, plafond dur 6 cases,
  devis 67 ouvrables, ratio 1,59× ; 147+11 verts ; déployé sha-vérifié,
  backend relancé, devis neuf : 2,100 / 11 ouvrables). **Dix servies**
  (toutes flux 0,018 $ ; 5 par frère ajusté) : stained_dragon graphite
  **100,0 (2e SCORE PARFAIT — le dragon était 0/2)** · depths_portal rouge
  **96,9** · stained_portal graphite 93,8 · heraldry_portal ocre 93,8 ·
  depths_grimoire ocre 90,6 · vista_grimoire ocre 87,5 · medallion_grimoire
  ocre 84,4 · stained_grimoire rouge 84,4 · stained_knight graphite 82,1
  (le chevalier était 0/2) · heraldry_grimoire ocre 78,1. LE FAIT SAILLANT :
  **le grimoire gagne dans les CINQ compositions servables** (0/2 avant
  l'enveloppe) et **le portail finit 4/4** (93,8 · 93,8 · 93,8 · 96,9) —
  quand le sujet rend une masse sombre, la composition ne compte presque
  plus. Douze refus (1,773 $) : 9 « gpt trop clair » (ship×2, whale,
  citadel, golem, sphinx, serpent, dragon-medallion, knight-vista — la
  passe ne rentre jamais un gpt sur-éclairé), depths_monolith 89,3 (claire
  en voie flux), depths_crystals 87,5 (chroma, échelle complète),
  stained_phoenix 65,6 (le phénix 0/2, condamné comme sujet). État final
  VÉRIFIÉ (GET + devis machine) : **34/108, 11,853 $/12,00 $, reste
  0,147 < 0,177 → 0 ouvrable**. Servies par composition : vista 11 ·
  stained 11 · medallion 5 · heraldry 4 · depths 3 (backlight 0) ; par
  famille : ocre 19 · graphite 8 · rouge 6 · violet 1 ; médiane 87,5,
  quatorze ≥ 90, deux 100,0. **Cumul du 26/08 : 4/108 → 34/108 (+30) pour
  4,386 $ en trois enveloppes — 30 servies sur 55 sondes (55 %).**

### T2 — MESHY_MOCK au .env (D4)

- [x] **T2-A** : `MESHY_MOCK=1` écrit au .env du DATA_ROOT avec commentaire
  daté, UTF-8 sans BOM, sans lire les clés.
- [x] **T2-B** : orphelin 2.4.0 (PID 47764, parent disparu) arrêté par
  `stop.ps1`, relance à l'identique (`runtime\python -m uvicorn`, cwd
  backend) : health rend `version: "2.5.0"` ET `meshy_mock: true` — la
  2.5.0 servie et le mock survivant prouvés d'un coup (le processus neuf n'a
  AUCUNE variable du lanceur).
- [ ] **T2-C** : noter la décision au CHANGELOG (une ligne, à la clôture de
  phase avec la section v2.6).

### T3 — Les plans du décor : gemme/bandeau, empilement, placeMenu (D5)

**Fichiers :** `frontend/cardforge/js/mod-type.js` (peintre strates,
empilement, placeMenu), `frontend/cardforge/js/mod-frame.js` (plan
d'occupation — régime manuel), `frontend/cardforge/qa/` (banc).

- [x] **T3-A (RED)** : RECALÉ EN EXÉCUTION MESURÉE (mieux que le plan) : les
  strates sont VERROUILLÉES par le CORE (`Z_TABLE`, un painter ne peint que
  son z — un ornement ne PEUT PAS rejoindre la pile de P3). Le remède
  conforme : le PLAN d'ornement (`gem_plan`/`banner_plan`, « dessus » 70 /
  « dessous » 40). RED en 5 tests backend (section 25 de
  test_cards_frame.py) : défaut/valeurs inconnues au bit près, dessous→40,
  MIROIR python↔JS au banc de rangées, répartition `ornementsAuPlan`
  exécutée au banc node, pin DEFAULTS 40→42.
- [x] **T3-B (GREEN)** : python (`_plan_ornement`, `_place_gem`/`_place_banner`
  + habillage commun — la liste blanche des modèles suit d'elle-même) ; JS
  (`planOrnement`, `ornementsAuPlan`, `st()` normalise, occupancy passe,
  `paintTop(…, couche)` peint 70 ET 40 — le même peintre écran/export, le
  z=40 l'appelle en queue de `paintFront`) ; UI : select « Plan » dans les
  rangées gemme et bandeau (Ctrl+Z par `set()`) ; la liste des calques DIT
  « (sous les blocs) ». **308/308 frame, 166/166 models, coutures type
  retendues.** Commit `dcca7d3`.
- [x] **T3-C — SOLDÉ (26/08, méthode systématique).** CAUSE RACINE mesurée
  sur pièces : le painter échange le global `MEAS` à CHAQUE passe et la
  garde `IN_AUDIT` avale la montée d'`AUDIT_STAMP` pour TOUTE passe achevée
  pendant l'audit (pas seulement la sienne) ; `runAudit` lisait `MEAS`
  APRÈS la fenêtre `await asFile` — **fenêtre mesurée à ~2,9 s sur le deck
  réel** (montée à ~140 ms, audit de ~790 à ~3 725 ms). Une passe
  retardataire (fonte/image qui finit de charger : le 1er tour post-édition,
  exactement) glissait SA mise en page sous le composite d'une autre →
  l'encre-solo d'une passe comptée contre le fichier d'une autre, masquage
  fantôme non déterministe, publié SANS invalidation (la montée avalée).
  Les protocoles pilotés par l'inspecteur ne le reproduisent pas : deux
  chemins d'auto-guérison les couvrent (l'audit re-rend le document
  COURANT ; `renderAll` ré-arme le minuteur) — c'est pourquoi seul le
  terrain le voyait. L'INVARIANT RÉPARÉ : « une preuve publiée vient d'UNE
  passe » — génération `MEAS_GEN` montée à chaque échange, passe FIGÉE à la
  résolution du rendu (`const meas = MEAS, side = MEAS_SIDE, gen =
  MEAS_GEN;` AVANT `asFile`, épinglé), DEUX gardes qui REFUSENT la
  publication et re-planifient sur passe étrangère, la boucle lit
  l'instantané (mutant « MEAS[id] » vérifié absent), le côté publié est
  celui de la passe. ET LE MESSAGE NOMME : `couvreursDe` (fonction PURE
  exécutée au banc node — chevauchement ≥ 0,2 mm², sinon bruit
  d'anticrénelage) confronte le pavé d'encre aux couches peintes AU-DESSUS
  (blocs de P3 postérieurs + décor haut au plan « dessus » via la pose
  publiée `decor_pose`) ; badge et détail disent « recouvert par : … ».
  2 tests neufs (section 26 de test_cards_type.py). **Prouvé dans l'app
  déployée** : gemme r14 au plan « dessus » posée sur le titre → badge
  « 63 % masqué », infobulle « 9 461 px d'encre recouverts — recouvert
  par : gemme (décor haut) ».
- [x] **T3-D (GREEN)** : `placeMenu` se cale sur SA largeur MESURÉE
  (getBoundingClientRect après pose), marge droite 8 px, `max-width` au
  viewport — la cause était le paramètre (420) plus étroit que la boîte
  réelle, sans borne de largeur : débordement dès `r.left > vw − 420`
  (~618 px). Prouvé au navigateur : viewport 590 px, menu right 582,
  **débordement 0 px**, max-width 574 posé.
- [x] **T3-E (preuves dans l'app déployée, backend relancé 2.5.0)** : sonde
  pixel sur `CF.renderCard` (le composite du FICHIER) du deck témoin
  `deck_14154201` — gemme manuelle (50,42 ; 12,85) sous la fenêtre du titre :
  plan « dessus » = or de gemme au centre ; bascule par le SELECT réel de
  l'UI → `gem_plan: "dessous"` persisté, **6 644 pixels changent** dans la
  zone titre∩gemme entre les deux rendus — le titre se peint PAR-DESSUS. Le
  deck vitrine reste en « dessous » (la demande utilisateur exacte).

### T4 — Les éléments ajustables + primitives + elements:[] (D6, DÉBLOQUÉ 26/08)

- [x] **T4-A — la palette `elements:[]` des modèles perso, LIVRÉE** (les 4
  arbitrages §4). RED 8 tests (section 21 de test_cards_models.py) puis
  GREEN : `_souche` (l'id sans suffixe numérique — la convention que
  `dupSlot`/`norm_slots` écrivent eux-mêmes), `_grille_de_reference`
  (`modele:<id>` usine puis perso sur disque, gabarit du catalogue, sinon
  DIVINATION par meilleur recouvrement d'identifiants, départage par
  l'ordre du catalogue, et l'aveu `grille`/`grille_devinee` SURVIT au
  disque par `_normaliser_perso`), `_elements_du_deck` (hors grille
  seulement, groupés par souche, label du premier slot sans ses chiffres,
  hint qui dit la provenance ET la divination). L'écran n'a besoin
  d'AUCUN changement (mesuré en phase 5 : la palette lit le modèle).
  **174/174 models verts.**
- [x] **T4-B — le bandeau posé à la main + les formes du décor, LIVRÉS.**
  `banner_x`/`banner_y` au patron exact de la gemme (coin haut-gauche,
  clés indépendantes, bornées au format, `manual` + lane « posée à la
  main » au plan, python↔JS au bit près — 6 tests neufs section 26,
  DEFAULTS 45 clés, pins retendus, **313/313 frame**) ; UI : champs
  Bandeau X/Y à l'EFFECTIF + Auto + ligne d'état ; le peintre suit la
  boîte du plan sans une ligne de plus. « Formes du décor » (P3) :
  **premier jet RECALÉ PAR LES PINS D'ARCHITECTURE** — un `fetch(` nu vers
  `/frame/occupancy` violait « aucun réseau nu dans une pièce » ET la
  porte unique des naissances (2 rouges au banc type, mérités). Le remède
  conforme est le patron `art_window` : **P2 PUBLIE `frame.decor_pose`**
  (gemme visible — écrin exclu — et bandeau, la mesure du calcul qui
  peint, différée-gardée-par-comparaison, 45e clé jamais saisie à la
  main, exclue des archétypes comme art_window), P3 la lit avec tolérance
  et fait naître ses formes PAR LA PORTE (`naitre`, nommée au pin des
  naissances 7→8). Éteindre l'ornement reste le geste de P2, le toast le
  dit. **Prouvé dans l'app déployée (chemin final)** : champ banY 61,5 →
  « Bandeau posé à la main — coin 17,9 x 61,5 mm » ; pose publiée lue,
  bouton → `bandeauforme` rect à [17,9 ; 61,5 ; 27,2 ; 5,2] et
  `gemmeforme` ellipse 11,3×11,3 au cercle exact de la gemme, re-clics
  renommés (`…2`, `…3`). Zéro réseau depuis P3.

### T5 — Le GC des bancs (D7)

- [x] **T5-A** : inventaire MESURÉ le 25/08 : **2 206 jeux, dont 2 110
  « Nouveau jeu » = 6,1 Go** ; les 96 autres sont tous NOMMÉS (vitrine
  27,7 Mo, campagne, démos 24-88 Mo, preuves de phases). Le critère « nom
  exact » est discriminant à lui seul sur ce magasin — T5-B ajoutera la
  ceinture « rien d'adopté ».
- [x] **T5-B (RED→GREEN)** : `test_gc_decks.py` (5 tests) +
  `scripts/gc_decks.py`. Le critère a été RECALÉ au réel pendant l'écriture :
  « rien d'adopté » aurait tout gardé (les jeux de banc PORTENT du contenu —
  6,1 Go/2110 ≈ 3 Mo pièce) ; la vraie ceinture est nom EXACT « Nouveau
  jeu » ET ZÉRO référence externe (octets de la base + tout .json du
  dossier de données, magasin et rebuts exclus — un rebut d'hier ne
  vaccine pas le GC du jour, épinglé). Méta illisible / dossier hors forme
  = gardé. L'outil DÉPLACE vers `rebut_decks_<date>/` + `_POURQUOI.txt`,
  ne supprime JAMAIS un octet (compte de fichiers prouvé identique).
- [x] **T5-C (RÉEL, sur ordre utilisateur « construit » du 26/08)** :
  dry-run — 2 206 vus, 2 109 candidats, gardés : 93 nommés + 3 métas
  illisibles + **1 « Nouveau jeu » SAUVÉ par la ceinture** (cité dans
  deepotus.db) ; puis rangement — **2 109 jeux (6 213,9 Mo) →
  `rebut_decks_2026-08-26/`**. L'app relue : 94 jeux au listing, série
  4/108 et 7,467 $ inchangés, vitrine et deck de campagne en place. La
  suppression définitive du rebut appartient à l'utilisateur.

### T6 — Finitions transmises

- [x] **T6-A** : le jeton du banc de contrat POSÉ — `NOM_MODELE_BANC` porte
  un suffixe aléatoire par passage : l'égalité de libellé ne peut plus
  reconnaître (donc DÉTRUIRE) qu'une carte que CE passage-ci a écrite. Un
  modèle utilisateur nommé par hasard « Banc QA modele » est hors
  d'atteinte.
- [ ] **T6-B (repro requis)** : « le calque d'image dit encore mention du
  cadre » — INTROUVABLE au grep (aucun libellé « mention du cadre » dans
  frontend/cardforge). L'observation venait de l'écran de phase 5 sans
  repro consigné : demander à l'utilisateur OÙ il l'a vu avant de
  corriger au hasard. La liste des blocs fond-vers-surface vs bandes
  Figma reste à trancher (même convention que les bandes — le décor haut
  ouvre la liste, mod-type.js:3448) : chirurgie UI à faire posément.
- [ ] **T6-C** : le redimensionnement de LOT (multi-sélection → poignées
  d'échelle groupée, ancre au coin opposé — comportement Figma).
- [ ] **T6-D** : le contour SVG d'extrude v2 (transmis phase 4) : SEULEMENT
  si le reste est soldé et le budget de session le permet ; sinon re-transmis
  tel quel.
- [ ] **T6-E** : suite complète verte + lint + déploiement + poussée +
  clôture de phase au présent document.

#### Demande utilisateur du 26/08 (2e session) — T6-F/G/H

Trois livrables d'ergonomie des écrans 02 Cadre et 03 Typographie, dans la
SOURCE (`frontend/cardforge/`), au patron des mécanismes déjà prouvés :

- [x] **T6-F — le bandeau à la souris (priorité), LIVRÉ.** Le bandeau a ses
  clés (`banner_x`/`banner_y`, T4-B) et ses champs ; il lui manquait le
  GESTE. La carte des poignées (`wireMap`, mod-frame.js) a gagné la prise
  « ban » : le bandeau est DESSINÉ sur le plan (trait plein manuel /
  pointillé auto, le vocabulaire de la gemme), glisser écrit
  `banner_x`/`banner_y` (coalesceur partagé, un patch par frame, bornés
  miroir du backend `tw−w`/`th−h`), double-clic = `banAuto()`, une entrée
  d'annulation par geste (l'état d'AVANT, nuls compris), le gel se DIT une
  fois (`ditLeGelBandeau`). Priorité de prise = ordre de peinture : gemme >
  bandeau > fenêtre. L'aperçu central n'a PAS de drag de gemme (vérifié) :
  le plan est la seule surface de geste, le bandeau y entre par la même
  porte. RED section 27 de test_cards_frame.py (4 tests : pins de source +
  banc Chrome rejoué du patron gemme — encre par différence, empreintes
  auto≠manuel, prises) ; pin RETENDU dit : la page du banc gemme gagne un
  bouchon `banDe` (drawMapWith dessine désormais aussi le bandeau).
  **PROUVÉ dans l'app déployée (banc CDP, vrais événements souris)** :
  coin auto 14,5×76,04 → glisser +9/−6 mm → **23,5×70,04 au centième
  près**, ligne d'état « posé à la main » + toast du gel ; **Ctrl+Z rend
  les deux clés à null** (l'automatique, pas « repose où c'était ») ;
  double-clic → null + « automatique — voie libre, ruban aminci ».
- [x] **T6-G — les colonnes coulissantes (02 et 03), LIVRÉES.** Le
  mécanisme 2d (classe sur `.cf`, la VARIABLE bascule, dz_cf_*, absence de
  clé = déployé, replié gagne sur la media-query) est ÉTENDU au niveau des
  panneaux, pas dupliqué : le gabarit de `.cf` devient
  `var(--rail-w) var(--scene-col) var(--travail-col) auto` (UN gabarit,
  défauts identiques à l'existant), et le CORE a gagné `CF.coulisse(mod,
  niveau)` — une pièce DIT combien de ses colonnes dorment (0/1/2),
  `applyFold` pose `travail-mince`/`travail-bande` selon la pièce ACTIVE,
  et la scène absorbe chaque pixel au-delà du plafond (`--scene-col:
  minmax(var(--stage-w), 1fr)`, travail plafonné 470 px / 200 px). La
  colonne carte REPLIÉE garde le dernier mot (ses variables re-déclarées
  après, l'ordre tranche). P2 : chaque colonne (`cff-colA` épreuve &
  catalogue, `cff-colB` réglages) porte son chevron → bande verticale de
  réouverture (patron stage-fold, contenu RETIRÉ du flux), clés
  `dz_cf_frame_colA`/`colB`. P3 : chip « 1 colonne » (`dz_cf_type_mono`),
  liste et inspecteur EMPILÉS, gabarit de `.cf-type-cols` par la variable
  `--cft-cols` (la media query redéclare la MÊME variable). L'appel
  `CF.coulisse` est GARDÉ par `typeof` (patron « sanscore » : un CORE plus
  vieux que la pièce — c'est le cas des CF de paille des bancs node, 121
  rouges mérités avant la garde). RED : banc core (2 tests grille/service),
  frame section 28, type section 30. **PROUVÉ dans l'app déployée** :
  replier « réglages du cadre » → grille `188/384/912` → `188/826/470`
  (la scène +442 px), carte 355 → 459 px, `dz_cf_frame_colB=1` ; les deux
  → `travail-bande` ; rechargement → P1 SANS coulisse (par pièce), P2 la
  retrouve ; mono P3 : carte à pleine largeur (717 px, 1723 px zoomée).
- [x] **T6-H — le zoom d'aperçu (02 et 03, la scène étant une), LIVRÉ.**
  État d'ÉCRAN SEUL (patron phase-pointeur) : `ZOOM` multiplie le facteur
  d'adaptation (`PREV_SCALE = fit × ZOOM`), ne touche NI le document NI
  l'export (renderRaw/saveBody l'ignorent — épinglé), persiste
  `dz_cf_zoom` RELATIF à l'adaptation (absence de clé = adapter ; même
  facteur = même taille de carte à l'écran d'un DPI à l'autre). Le pied
  « N % aperçu » est devenu la COMMANDE : − / % / + / Adapter / 100 %
  (100 % = un pixel du fichier = un pixel d'écran). Ctrl+molette zoome
  vers le pointeur, la molette nue défile, le bouton du milieu glisse.
  Centrage par `margin: auto` (un flex centré rendait le coin haut-gauche
  inatteignable), `overflow: auto`, `max-width/height: 100 %` retirés du
  canevas, la définition PLAFOND du bitmap reste la source
  (`min(PREV_SCALE·dpr, 1)` — le CSS grossit, honnête, la loupe fait
  mieux). DEUX REMÈDES MESURÉS AU BANC (le calque d'édition de P3 est du
  DOM fixé sur body par-dessus le canevas) : (1) le calque se ROGNE à la
  boîte visible de la colonne (`clip-path`, dessin ET prise — non rogné il
  couvrait le pied et VOLAIT les clics des commandes ; le premier jet
  inversait l'inset bas, démasqué par `elementFromPoint` = `cf-type-hbox`
  sous le bouton +) ; (2) molette et bouton-milieu s'écoutent en PHASE DE
  CAPTURE sur document, garde géométrique `surScene` (un écouteur sur la
  colonne ne voyait JAMAIS le geste sous le calque). Resynchronisations :
  `core:scene` (émis par drawPreview) + scroll de `.stage-wrap`
  (rAF-coalescé). RED : banc core (3 tests), type section 30. **PROUVÉ
  dans l'app déployée** : 42 % → **161 %** aux boutons du pied, toile/coupe
  INCHANGÉES (les mm restent les mm), défilement né, calque calé à 0 px
  d'écart, pan milieu +120/+60 px suivi par le calque, **glisser de bloc à
  161 % juste à 0,08 mm de l'attendu** puis Ctrl+Z, rechargement → 161 %
  restitué, Adapter → 44 % et la clé s'efface.

## 4. Les arbitrages utilisateur (T4 — à trancher avant tout code)

La demande neuve : « ajuster manuellement TOUS les éléments (ex. bandeau de
rareté) et ÉVENTUELLEMENT les remplacer par des formes primitives. » Elle
recouvre deux chantiers : (i) la LIBÉRATION frontend des ornements (bandeau,
socles, logements, fenêtre — au patron de la gemme de phase 5 : manuel dit,
Ctrl+Z, retour à l'automatique) + « remplacer » = éteindre l'ornement et
poser à la place des formes primitives héritant position/taille ; (ii) la
palette `elements:[]` des modèles perso (backend). Les 4 arbitrages de la
phase 5, avec recommandation :

**TRANCHÉS PAR L'UTILISATEUR (26/08)** :

- **(a) DEVINER UNE GRILLE.** Sans `preset = "modele:<id>"` connu, la grille
  de référence se DEVINE : le gabarit connu dont l'ensemble d'identifiants
  de slots recouvre le mieux celui du jeu (départage déterministe par
  l'ordre du catalogue). La divination SE DIT : le modèle porte la grille
  retenue (`grille` + `grille_devinee: true`) — une carte devinée qui ne le
  dit pas est une carte fausse.
- **(b) OUI** — les extras restent AUSSI dans `type.slots` : l'élément
  POINTE le slot, il ne le déplace pas ; appliquer le modèle re-pose tout
  sans perte.
- **(c) HORS GRILLE seulement** — la grille standard reste la grille ; un
  élément est ce qui la dépasse (toutes les formes en font partie : aucun
  gabarit d'usine n'en porte).
- **(d) GROUPÉ** — les slots extra qui partagent un même parent nommé font
  UN élément (patron d'usine « 7e statistique ») ; un élément par slot
  orphelin sinon, et le nom du groupe vient du parent, rien n'est deviné.

## 4bis. Ordres utilisateur exécutés en cours de phase (26/08)

- **« 3) supprimer »** : le rebut de série
  `rebut_serie_walkuski_2026-08-25/` est SUPPRIMÉ (294 fichiers,
  261,6 Mo) — après archivage au magasin des 2 sources brutes que le
  manifeste nomme (`source_rebut` : gen_0c881927, gen_2e1f4397 — la
  provenance reste vraie, ~2 Mo).
- **« 4) publie »** : la release GitHub **v2.2.0 « Catalogue de
  démarrage »** est EN LIGNE (installeur 148 Mo du Bureau Export, notes
  du dépôt, `--latest=false` — la v2.5.0 garde « Latest »). L'échelle des
  releases est complète : 1.15.1 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5.

## 5. Consigne de sortie de phase

- Bilan par tâche au présent document (cases cochées, preuves mesurées,
  captures pour T3), leçons durables aux clôtures, mémoire projet mise à
  jour, poussée. Le rescapage dit ses chiffres RÉELS (cases gagnées, part du
  rebut mappée). La décision du rebut (supprimer ou garder) revient à
  l'utilisateur APRÈS le bilan du rescapage. T4 part dans sa propre session
  avec les arbitrages tranchés.
