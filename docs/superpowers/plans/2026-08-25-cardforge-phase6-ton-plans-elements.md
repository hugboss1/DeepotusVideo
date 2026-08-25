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

- [ ] **T1-A (RED)** : écrire `test_cards_serie_ton.py` — les tests d'or du
  refactor juge (métriques identiques avant/après sur 2 PNG synthétiques
  fabriqués dans le test), `tonales()` existe et rend les 3 clés de la fiche,
  `mise_au_ton` : (1) image trop claire synthétique → les 3 métriques entrent
  dans leurs bandes ; (2) image déjà dans les bandes → octets de sortie
  IDENTIQUES sur deux appels (déterminisme) et score tonal jamais dégradé ;
  (3) axes non tonals intouchés par la promesse (la fonction ne prétend
  corriger que le ton : le rapport liste `axes_vises`). Lancer : ROUGE.
- [ ] **T1-B (GREEN)** : implémenter `tonales()` dans style_walkuski (extraite
  de `mesurer`, appelée par lui), puis `mise_au_ton(src, dst, fiche) -> dict`
  dans face.py (premier jet analytique noir/blanc/gamma depuis l'histogramme
  de luminance, raffinement grille 3×3×3, LUT PIL `point`). Suite du fichier
  verte.
- [ ] **T1-C (RED)** : tests de la voie — `_fabriquer_case` monkey-patché
  (tirages factices, juge réel sur images synthétiques) : un candidat « HORS
  STYLE aux axes tous tonals » gagne un frère ajusté qui TIENT et la case est
  servie SANS tir supplémentaire (sentinelle : tout `_tirer_*` non prévu
  lève) ; un candidat aux axes mixtes n'en gagne pas ; le journal de dépense
  est inchangé par la passe. Lancer : ROUGE.
- [ ] **T1-D (GREEN)** : brancher la passe dans `_fabriquer_case` (après
  chaque `_juger` de lot, avant `meilleur_candidat`). Vert.
- [ ] **T1-E (RED)** : tests du rescapage — DATA_ROOT temporaire avec faux
  journal (lignes `_payer` + `FLUX: saved` aux seeds fnv1a32 réels), faux
  rebut (images synthétiques nommées comme le journal), manifeste avec refus :
  dry-run rend le rapport (mappées/non mappées/absentes, rien d'écrit) ;
  `{"appliquer": true}` sert la case rescuable, `depense_totale_usd`
  INCHANGÉE, `prix_usd: 0.0`, refus popé, magasin peuplé d'un PNG réel ;
  re-POST → `deja_servie` (idempotent) ; clés fournisseur neutralisées au
  banc (patron des tests de campagne existants). Lancer : ROUGE.
- [ ] **T1-F (GREEN)** : implémenter le parseur de journal (regex `[0-9]`,
  jamais `\d` — parité multi-langages) + `POST /serie/rescaper`. Vert, puis
  la SUITE ENTIÈRE cards (`scripts/run-tests.ps1` sur les fichiers cards) :
  verte.
- [ ] **T1-G** : commit (« serie : la mise au ton déterministe — la voie et le
  rescapage, zéro centime »).
- [ ] **T1-H (RÉEL)** : déployer sur l'app (le verrou cardforge), relancer le
  backend (T2 D'ABORD — le .env doit porter le mock avant la relance),
  `POST /serie/rescaper` dry-run RÉEL → lire le rapport (couverture du
  mapping sur les 292), puis `{"appliquer": true}` → bilan RÉEL (combien de
  cases montent au-dessus de 2/108 ?). Vérifier `GET /serie` + 2-3 images
  servies à l'œil (les métriques ne disent pas tout — l'utilisateur juge en
  dernier). AUCUNE dépense au registre (vérifier `depense_totale_usd`
  avant/après : 7,467 identique).

### T2 — MESHY_MOCK au .env (D4)

- [ ] **T2-A** : lire le `.env` du DATA_ROOT (grep `MESHY_MOCK` seulement — on
  ne lit pas les clés), ajouter/mettre à jour la ligne `MESHY_MOCK=1` avec
  un commentaire daté (`# 25/08/2026 : simulateur par defaut — mettre 0 pour
  le Meshy reel (credits)`). Encodage UTF-8 sans BOM préservé.
- [ ] **T2-B** : relancer le backend de l'app (tuer l'orphelin :8765 APRÈS
  T2-A, relancer par le lanceur de l'app), vérifier `GET /api/health` :
  `version: "2.5.0"` ET `meshy_mock: true` — la 2.5.0 servie et le mock
  survivant prouvés d'un coup.
- [ ] **T2-C** : noter la décision au CHANGELOG (une ligne, phase 6).

### T3 — Les plans du décor : gemme/bandeau, empilement, placeMenu (D5)

**Fichiers :** `frontend/cardforge/js/mod-type.js` (peintre strates,
empilement, placeMenu), `frontend/cardforge/js/mod-frame.js` (plan
d'occupation — régime manuel), `frontend/cardforge/qa/` (banc).

- [ ] **T3-A (RED)** : au banc qa (patron `test_core_contract.mjs`), épingler
  le défaut : plan avec gemme MANUELLE + calque texte au-dessus dans l'ordre
  → l'ordre de peinture rendu place ENCORE la gemme au-dessus. Le test
  échoue sur l'attendu inverse. + un cas bandeau. Lancer : ROUGE.
- [ ] **T3-B (GREEN)** : l'ornement en régime manuel rejoint la pile
  réordonnable (position initiale : juste au-dessus du calque le plus haut au
  moment du passage en manuel — le geste ne change rien à l'œil, puis les
  boutons devant/derrière agissent). Strate 70 conservée en automatique.
  Écran et export par le même chemin (vérifier le painter unique). Vert.
- [ ] **T3-C (RED→GREEN)** : la preuve d'empilement — reproduire la
  non-détermination du 1er tour post-édition (le banc la décrit au plan de
  phase 5 §transmis), corriger la course, et le message nomme les couches
  RÉELLEMENT en recouvrement (pas « les mauvaises »).
- [ ] **T3-D (RED→GREEN)** : `placeMenu` sous 618 px : le menu se borne au
  viewport (clamp + repli), cas au banc si le banc porte le DOM, sinon
  preuve au navigateur (fenêtre 590 px, capture).
- [ ] **T3-E** : commit + déploiement + preuve dans l'app déployée (la carte
  témoin `deck_14154201` : gemme déplacée sur le titre, passer le titre
  devant → il SE VOIT), capture d'écran au bilan.

### T4 — Les éléments ajustables + primitives + elements:[] — BLOQUÉ (D6)

AUCUN code avant les réponses de l'utilisateur (§4). À la levée du blocage :
RED d'abord, ~8 tests backend (elements) + banc frontend (libération), est.
3-4 h backend + 2-3 h frontend, dans une session dédiée si besoin.

### T5 — Le GC des bancs (D7)

- [ ] **T5-A** : inventaire MESURÉ (script jetable au scratchpad) :
  combien de jeux au nom « Nouveau jeu », leur poids, la part sans contenu
  adopté, les 96 restants nommés. Rapport chiffré au bilan.
- [ ] **T5-B (RED)** : `backend/tests/test_gc_decks.py` — le critère STRICT
  (nom exact + rien d'adopté), le dry-run n'écrit rien, `--deplacer` déplace
  et écrit `_POURQUOI.txt`, un deck nommé autrement ou avec un import N'EST
  PAS déplacé, idempotence. ROUGE puis GREEN (`scripts/gc_decks.py`).
- [ ] **T5-C** : dry-run RÉEL sur le magasin (rapport à l'utilisateur — le
  `--deplacer` n'est lancé QUE sur son ordre).

### T6 — Finitions transmises

- [ ] **T6-A** : le jeton du banc de contrat (le banc reconnaît SON modèle
  par un suffixe jeton, plus par égalité de libellé — la trouvaille de la
  ronde de phase 5).
- [ ] **T6-B** : le calque d'image dit encore « mention du cadre » (libellé) ;
  la liste des blocs s'affiche fond-vers-surface OU bandes façon Figma —
  trancher pour LA MÊME CONVENTION que les bandes (le décor haut « ouvre »
  la liste, mod-type.js:3448) et le dire dans l'aide.
- [ ] **T6-C** : le redimensionnement de LOT (multi-sélection → poignées
  d'échelle groupée, ancre au coin opposé — comportement Figma).
- [ ] **T6-D** : le contour SVG d'extrude v2 (transmis phase 4) : SEULEMENT
  si le reste est soldé et le budget de session le permet ; sinon re-transmis
  tel quel.
- [ ] **T6-E** : suite complète verte + lint + déploiement + poussée +
  clôture de phase au présent document.

## 4. Les arbitrages utilisateur (T4 — à trancher avant tout code)

La demande neuve : « ajuster manuellement TOUS les éléments (ex. bandeau de
rareté) et ÉVENTUELLEMENT les remplacer par des formes primitives. » Elle
recouvre deux chantiers : (i) la LIBÉRATION frontend des ornements (bandeau,
socles, logements, fenêtre — au patron de la gemme de phase 5 : manuel dit,
Ctrl+Z, retour à l'automatique) + « remplacer » = éteindre l'ornement et
poser à la place des formes primitives héritant position/taille ; (ii) la
palette `elements:[]` des modèles perso (backend). Les 4 arbitrages de la
phase 5, avec recommandation :

- **(a)** Contre quelle grille se mesure un slot « non standard » quand le
  jeu n'a AUCUN modèle d'origine (gabarit local, montage main) ?
  *Recommandation : sans `preset = "modele:<id>"` connu, AUCUN élément déduit
  — la palette reste vide et l'écran le dit ; on ne devine pas une grille.*
- **(b)** Les extras restent-ils AUSSI dans `type.slots` ?
  *Recommandation : OUI — l'élément POINTE le slot, il ne le déplace pas ;
  appliquer le modèle re-pose tout sans perte.*
- **(c)** Toute forme devient-elle un élément, ou seulement celles hors
  grille ? *Recommandation : seulement hors grille — la grille standard
  reste la grille ; un élément est ce qui la dépasse.*
- **(d)** Un élément par slot extra, ou un élément qui GROUPE les slots
  parents (patron d'usine « 7e statistique ») ? *Recommandation : GROUPER
  quand les slots extra partagent un même parent nommé, un élément par slot
  sinon — et le nom du groupe vient du parent, rien n'est deviné.*

## 5. Consigne de sortie de phase

- Bilan par tâche au présent document (cases cochées, preuves mesurées,
  captures pour T3), leçons durables aux clôtures, mémoire projet mise à
  jour, poussée. Le rescapage dit ses chiffres RÉELS (cases gagnées, part du
  rebut mappée). La décision du rebut (supprimer ou garder) revient à
  l'utilisateur APRÈS le bilan du rescapage. T4 part dans sa propre session
  avec les arbitrages tranchés.
