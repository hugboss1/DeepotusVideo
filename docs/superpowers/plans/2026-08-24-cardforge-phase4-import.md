# Cardforge — Phase 4 : import et isolation (P10 « capture ») + preuve deepotus-fragments

**Contrat** : spec `docs/superpowers/specs/2026-08-19-cardforge-universel-design.md`
§3.2 (:54-68, la pièce P10, id `capture` parce que `import` est un mot réservé), §7.1
(:488-513, le chemin en six étapes), §7.2 (:515-577, la preuve de bout en bout),
§8 (:579-589, doctrine d'erreurs — refus mesuré du fond non uni), §9.1/§9.4 (:601-604,
:618-622, cartes synthétiques à vérité connue, lint sans painter pour `capture`).
**Branche** : `claude/audit-cleanup-2026-08` dans `C:\Users\olivi\DeepotusVideo`.
Déploiement : `scripts\qa\cf_deploy.ps1` → `%LOCALAPPDATA%\DeepotusVideoGen`.

**Méthode** (inchangée depuis la phase 1) : une tâche = un agent opus, RED d'abord,
mutation avec témoin survivant volontaire, commits français locaux (pousser = fin de
phase seulement), revue adverse, ronde de corrections au MÊME agent, notes de CLÔTURE
écrites ici par l'orchestrateur APRÈS la livraison réelle — jamais avant. Fautes de
plan amendées À LA SOURCE avec la mesure. Suite complète uniquement sur arbre au
repos. **Zéro dépense réelle** : MESHY_MOCK=1 par héritage d'environnement, moteurs
fal jamais lancés, génération d'images IA uniquement sous espion. Les opt-ins payants
(tir meshy-7, un décor IA) restent à l'utilisateur.

---

## 1. Faits de reconnaissance (2026-08-24, vérifiés sur pièces)

### 1.1 Les deux faits porteurs

**F1 — Le PDF fabricant ne contient PAS les 92 faces.** Vérifié sur les octets (grep
brut + pypdf, recoupés) : `DOSSIER_FABRICANT_DEEPOTUS_FRAGMENTS.pdf` = 3 151 838
octets, 16 pages, **10 images distinctes** toutes en `/FlateDecode` `/DeviceRGB` 8 bpc
(zéro `/DCTDecode`), dont UNE SEULE à **1060×1484** (objet `86 0`, page 5 — le gabarit
illustré 4.1, quasi certainement « The Patriarch of the Old Houses », la carte type de
la spec). Les neuf autres sont des plateaux/boîtes/schémas. La page 16 est une liste
« Fichiers à fournir au fabricant » : *« 92 faces de cartes (PNG/TIFF) + 1 dos »* est
un livrable que le studio DOIT ENCORE — pas un contenu du dossier. Le `.docx` du
cahier de règles ne contient que 21 médias de 15-220 Ko (schémas de règles). **La
preuve §7.2 roule donc sur LA SEULE face disponible** — exactement ce que la spec
anticipait (:546 « à recaler sur le FICHIER dès que son chemin est fourni »).
`pypdf>=5.1.0` est déjà dans requirements (:31) et déjà utilisé en LECTURE
(`print.py:2981`, `marketing.py:326`) : l'extraction est triviale, aucun outil neuf.

**F2 — `doc.forge3d` est silencieusement perdu par le backend AUJOURD'HUI.**
`contract.py:75-76` fige `MODULE_IDS` à 8 (« les huit pièces d'origine », verrouillé
par `test_cards_core.py:1050`) ; `normalize_deck` (`core.py:173-175`) jette toute clé
hors liste, `default_doc` (:149) ne sème pas `forge3d`, `patch_deck` (:311-313) ne
l'accepte pas — or `saveBody` (`core.js:1404`) l'ENVOIE (tout id sale du tableau JS
`MODULES`, qui contient `forge3d`). Le graphe P9 (« doc.forge3d.graph reste LA
vérité », plan 2a:18) ne survit donc à aucun cycle PATCH→lecture en ligne. Aucun test
ne l'épinglait (grep `forge3d` dans test_cards_core.py → 0). `doc.capture` hériterait
du même trou. **La doctrine du partitionnement est juste, la liste est périmée** — la
phase 4 étend `MODULE_IDS` à 10 (D1).

### 1.2 La coquille du 10e module (checklist exacte)

- `core.js:77` `MODULES` : ajouter `"capture"` (10e). `Z_TABLE` (:82) : INTOUCHÉ —
  `register()` (:472-526) ne valide les z que des painters déclarés ; `painters: []`
  saute tout le bloc (précédent : data/solid/print/gltf/forge3d). Titre/icône : AUCUNE
  table côté core — `buildRail()` (:938-956) lit `REG[id].title/icon` posés par le
  `CF.register` du module lui-même.
- `lint_cardforge.py` : `MODULES` (:108-109) + `"capture": set()` dans son `Z_TABLE`
  (:97-107) ; `EXTRA_PY` (:126) intouché (un seul `capture.py`). Aucun painter
  autorisé (§9.4).
- `index.html` (164 l.) : 3 insertions au patron des 9 — `<link>` css après :21,
  `<section class="cf-panel" id="cf-panel-capture" data-mod="capture">` dans
  `<section class="work">` après :140, `<script>` après :162.
- `backend/app/services/cards/__init__.py` : import (:40, pas d'alias — c'est
  pourquoi la spec a choisi `capture`), `include_router(..., prefix="/{did}/capture")`
  AVANT le filet attrape-tout (:83, Starlette matche dans l'ordre), ligne de
  docstring (:13-26).
- `qa/contract.html` : PAS de casse mécanique (le rail rend `.off` + title
  synthétique pour tout id non enregistré, comportement déjà épinglé par
  `test_core_contract.mjs:305-307` ; aucune assertion de compte). L'écart de
  couverture du banc s'élargit (déjà : forge3d absent) — ACCEPTÉ, le banc teste le
  CORE sur modules factices, pas les modules.
  **AMENDEMENT T1 (mesuré le 24/08)** : `contract.html` ne casse pas, mais
  `test_core_contract.mjs:353-360` SI — le banc épinglait le toast du
  placeholder au texte (`indexOf("phase 4 — l'import arrive") >= 0`) ET le fait
  que le clic NE referme PAS la galerie. Les deux deviennent faux par
  construction dès que `galImport` câble P10 : 2 contrôles OUVERTS sur 118,
  mesuré avant correction. Réécrits sur la vérité neuve (la galerie se ferme,
  la rangée `capture` du rail devient `.active` — la preuve se prend sur le
  RAIL, `contract.html` n'ayant pas de `<section data-mod="capture">`), plus
  une réouverture avant le contrôle d'Échap qui, sinon, lisait un écran déjà
  fermé et ne prouvait plus rien. `test_core_contract.mjs` s'ajoute donc aux
  fichiers de T1.

### 1.3 Primitives d'analyse (ce qui existe, ce qui manque)

- `pixel_ops.chroma_key(img, tolerance=28, feather=1.6) -> (RGBA, ok)`
  (`pixel_ops.py:348-390`) : clé = couleur médiane du périmètre ; REFUSE (`ok=False`,
  image intacte) sur deux portes mesurées — uniformité du périmètre < 60 % (:374) ou
  couverture opaque hors [5 %, 95 %] (:386). C'est la philosophie `bg_failed`
  verbatim (précédent d'avoeu : `sprite_service.py:640-641`).
- `pbr_service._micro_contrast(lum, radius)` (:308-321) : carte d'énergie
  pleine-résolution (passe-haut log-luminance) — pas des blocs. `stats(img)`
  (:545-563) : histogramme pur PIL {mean, median, p1/p5/p95, span}.
- **AUCUN chercheur de boîtes / composants connexes n'existe** (grep pixel_ops +
  pbr_service) : carte d'énergie → boîtes candidates = code NEUF de phase 4.
- rembg : prix `pricing.py:43` `rembg_api_usd: 0.003` ; voie API
  `sprite_service._rembg_api` (:199-209, fal `imageutils/rembg`) ; voie locale
  `_rembg_local_bytes` (:219-221, `from rembg import remove`) ; patron de
  disponibilité réutilisé 2× (`routes.py:710-716`, `:3837-3873`). NOTE : routes.py
  répond 400 sur dépendance absente, la doctrine cards §8 dit 503 littéral — chez
  cards, §8 fait loi.

### 1.4 Admission d'images

Patron `texture.py:post_paper` (:2230-2241 → `_store_image` :2178-2213) : corps brut
→ 400 vide → 400 > `SRC_MAX_BYTES` 64 Mo → taille lue dans l'EN-TÊTE avant décodage →
413 > `IMG_MAX_PIXELS` 32 Mpx → `load()` gardé → RGB → LANCZOS si > cap → écriture
atomique tmp+replace. **C'est le patron de P10** (fichier fixe par côté), PAS le
quintette 3b (galerie comptée O_EXCL — pour des piles numérotées ouvertes, ce que la
capture n'est pas). `MAX_IMPORT_PX = 4096` : recopié 6× (doctrine `type.py:552`
« RECOPIÉ et non partagé ») — capture.py porte la 7e copie.

### 1.5 Surfaces d'adoption

- **P1** : `setArt(id)` (`mod-face.js:2164-2169`), schémas `cat:`/`local:`/`img:`
  résolus par `artSource` (:1692-1734) ; import dans la pile locale via le mécanisme
  `afterImport` (:2171-2176). **Pas de 4e schéma** : adopter = importer les octets du
  sujet dans la pile P1 puis `setArt("local:"+clé)`.
- **P2** : `FAMILIES` (`frame.py:75-90`, 7 familles id/label/hint), `LIMITS`
  (:156-165). **Aucune table de traits numériques par famille** (largeur de bande
  typique…) n'existe — le « famille la plus proche » de §7.1.5 exige une table neuve
  (D6). La QA silhouettes est JS-seul (`SIL_SEUIL=4`, `mod-frame.js:3960-3966`).
- **P3** : `naitre(specs, quoi)` (`mod-type.js:1856-1864`) — naissance atomique
  multi-slots, un seul pas d'undo, `normSlots` validant. L'adoption des zones = UN
  appel groupé.
- **P9** : `LAYER_ROLES` 6 rôles figés (`forge3d.py:85-92`, miroir parité) ; le nœud
  `layer` (:115) résout via `_lire_manifeste` (:1172-1184) qui lit
  `layers_{carte}_{side}.json`, écrit UNIQUEMENT par `post_layers` (:916+) après
  preuve d'empilement des peintres. **Les couches importées n'ont aucun chemin
  honnête vers ce manifeste** (elles ne passeraient pas la preuve d'empilement) →
  côté `capture` dédié (D7).

### 1.6 Modèle fragments + transmis de phase 3

- 7 modèles d'usine (`models.py:1326`, `_usine` :823-839). `deepotus-fragments`
  n'est PAS un 8e d'usine : la spec le fait naître par « enregistré comme modèle »
  (voie perso `POST /models`, :1333+) depuis un deck vivant configuré. Le Sceau 3c
  est prêt : `SEAL_DEFAULTS` (`frame.py:228-231`), portée 3D-seule =
  `scope:{screen:false, print:false, mesh:true}`.
- Transmis 3c vérifiés : nœud `extrude` ABSENT (`NODE_KINDS` = 9, `forge3d.py:114-125` ;
  `relief` est « l'extrusion v1 ») ; « ondulation normale douce » non livrée (avoué
  3c) ; phase-pointeur : `sealStops(f, phase)` prêt (`mod-frame.js:1856`), aucun
  branchement pointeur ; **meta.json illisible-qui-se-redate : DÉJÀ implémenté et
  testé** (`core.py:219-223`, `test_cards_core.py:618,643`) — la transmission se
  clôt ici, aucun travail.
- Restes §6.4 : duplication LIVRÉE (`core.py:494`) ; bouton galerie « Importer une
  carte » = placeholder honnête (`core.js:1730`, toast :2005) à câbler.
- Tailles : core.js 2325 l., index.html 164 l., lint 1030 l. ; P9 est la pièce la
  plus lourde (mod-forge3d.js 316 Ko, forge3d.py 181 Ko, test 496 Ko).

---

## 2. Décisions de conception

**D1 — `MODULE_IDS` passe de 8 à 10 (`forge3d`, `capture`).** La doctrine du
partitionnement (:73-74 « un id hors de cette liste est refusé partout ») est juste ;
c'est la liste qui a deux pièces de retard. Conséquences tenues ensemble :
`default_doc` sème `forge3d:{}` et `capture:{}`, `normalize_deck` et `patch_deck` les
acceptent (garde dict tolérante, comme les 8), docstrings « huit » → « dix » partout
où le mot est un fait (grep), `test_cards_core.py:1050` réécrit sur la vérité
nouvelle. RED d'abord sur la perte d'aujourd'hui : PATCH `{forge3d:{graph:…}}` →
lecture → présent (échoue avant le fix), rejoué par la ROUTE réelle, pas par
`write_deck` direct. Ceci répare rétroactivement la promesse 2a (« le graphe est LA
vérité ») — le bug utilisateur réel : toute édition de graphe était perdue au
rechargement en ligne.

**D2 — Admission = patron `post_paper`, fichiers fixes par côté.** `POST
/api/cards/{did}/capture/card?side=recto|verso` (défaut recto), corps brut,
`MAX_IMPORT_PX=4096` (7e copie avouée), écriture atomique
`decks/{did}/capture/source_{side}.png`, ré-import = remplacement (pas d'historique —
une capture est un point de départ, pas une pile). `GET .../capture/{nom}.png` sert
les fichiers du dossier capture par liste blanche de noms (regex stricte, pas de
traversée). Un `?side` hors liste = refus français nommé, pas un 422 FastAPI.
Jamais-500 partout.
**AMENDEMENT ronde T1 (mesuré le 24/08)** : deux POST concurrents sur le même côté
rendaient un 500 à 10 % (tmp CONSTANT partagé + `replace` disputé — WinError 32) —
la règle devient : tmp à suffixe unique + `replace` gardé (dernier gagnant propre,
refus nommé si l'OS refuse), prouvée EN CONCURRENCE par le test. Et le joker
`GET /{nom}` à la racine du préfixe avalait d'avance toutes les routes GET futures
de T2/T3/T5 (mesuré : `/ai-options` → 404 « fichier inconnu ») — le service passe
sous `GET /file/{nom}` : le piège de classe meurt au lieu d'être documenté.

**D3 — `doc.capture` est publié par la PIÈCE, pas par la route.** Le POST analyse et
RÉPOND (le JSON d'analyse complet) ; mod-capture.js fait `M.patch({capture:{…}})` →
la voie d'autosave unique (que D1 rend enfin étanche). Une seule écriture du
document ; les PNG, eux, sont stockés serveur par la route.
*(Précision T2, T1 ayant livré `POST /card` en admission seule : « le POST » se lit
`POST /analyse`, qui court sur le recto STOCKÉ — relançable sans re-dépôt, geste
« Analyser » explicite à l'écran ; l'admission ne calcule rien.)*
**AMENDEMENT T2 (schéma livré, la ligne ci-dessus est périmée de trois clés)** :
la réponse porte AUSSI `echelle` {mm_par_px, image_px, carte_mm, fmt, trim_mm,
ratio_image, ratio_format} (un mm sans son cadre de référence ne veut rien dire
si le format change), `ecart_ratio` et `notes` (l'aveu de ce qui n'a pas pu être
mesuré) ; `border` s'étend (bords, regularite, nettete, epaisseurs_mm PAR BORD)
et `bg` porte ses deux formes (mesure | refus {bg_failed, motif, uniformite,
seuil, couverture, couverture_bornes, option_ia}). Tout en mm sauf `echelle`,
imposé par un balayage DÉRIVÉ des clés de la réponse (jamais une liste en dur). Schéma §7.1.4 :
`doc.capture = {analyzed, border:{mm,color,radius_mm,confidence}, boxes:[…],
bg:{color,confidence}, palette, layers:{…}}`. Les boîtes sont en MM dans le doc
(une unité par frontière, convertie au bord de l'API).
**AMENDEMENT ronde T1 (décision de plan)** : l'analyse est une propriété du RECTO
SEUL — les adoptions §7.1.5 (illustration, bordure, zones) sont des gestes de
recto ; le verso est stocké pour l'adoption future en back_image (§6.2ter).
Déposer un verso ne remet PAS l'analyse à zéro (seul un nouveau recto le fait), et
l'écran le dit. Le schéma §7.1.4 reste sans axe de côté, en connaissance de cause —
la trouvaille de ronde (« importer le verso effacera les mesures du recto ») est
close par cette asymétrie, pas par un axe.

**D4 — L'analyse réutilise ce qui se mesure déjà, n'invente que le chercheur de
boîtes.** Bordure : balayage de gradient depuis les 4 bords (code neuf, pur PIL) →
épaisseur mm + couleur dominante + rayon de coin estimé + confiance = régularité de
bande, clampée [0,1], cas dégénéré nommé (« aucun front trouvé » = bordure absente,
jamais 0 mm confiance 1). Zones : `_micro_contrast` + `stats` PAR BLOCS — **grille
de 1,5 mm, PAS « ~32 px » (amendement T2, mesuré le 24/08 et REPRODUIT par la
revue)** : un bloc en pixels rend le relevé dépendant de la résolution du scan
(mêmes boîtes au 1/100 mm à 630/1060/2926 px avec 1,5 mm ; trois relevés
différents + une boîte fantôme avec 32 px), pire IoU 0,735 à 1,5 mm contre 0,118
à 3,2 mm et 0,050 à 2,5 mm — le millimètre est l'invariant, pas le pixel →
seuillage → composants connexes sur la grille grossière (code neuf) → boîtes mm +
densité + netteté ; la bande de retrait le long des bords (bordure + portée du
passe-haut) est EXCLUE du regard : elle se NOMME en mm dans les notes et toute
boîte qui la touche porte `tronquee:true` (amendement ronde T2 — une coupe qui ne
se dit pas devient une fausse mesure chez l'adoptant). Fond : `pixel_ops.chroma_key` tel quel — ses deux
portes mesurées SONT le refus §8 (« fond non uni → refus mesuré, pas détouré de
travers ») ; le refus publie la mesure qui l'a causé. Palette : quantification
(`pixel_ops`). **Chaque détection publie sa confiance chiffrée ; l'écran affiche le
chiffre, jamais une certitude.**

**D5 — rembg opt-in au basculement sprite, doctrine cards.** Disponibilité rapportée
honnêtement par `GET /capture/ai-options` (local présent ? clé fal ?) avec le prix de
`pricing.py` (jamais recopié — test d'égalité à la table) AVANT tout appel ; option
absente = pas proposée (aucune erreur) ; invoquée quand même = 503 littéral (§8,
l'écart routes.py-400 ne fait pas jurisprudence chez cards). Tests sous espion
étanche patché au point de CONSOMMATION (la leçon spy 3c), zéro dépense prouvée
(compteur d'appels réels = 0).
**AMENDEMENT ronde T3 (mesuré le 24/08)** : (1) le banc NEUTRALISE la vraie clé —
`config._load_dotenv(override=True)` écrase le `setdefault` du test : la clé
réelle vivait dans le processus de test, le filet était simple là où l'en-tête le
croyait double ; `settings.FAL_KEY` est forcé à la valeur de banc APRÈS l'import
de config, et l'en-tête dit pourquoi ; (2) la doctrine du détourage vaut de SES
DEUX MOITIÉS : une couche qui garde ~tout (couverture ≥ seuil mesuré) est refusée
avec son chiffre, comme la transparente — c'est le mode d'échec ordinaire de
rembg (pas de sujet trouvé → image quasi intacte payée) ; (3) DEUX CLICS NE
PAIENT PAS DEUX FOIS EN SILENCE : les POST /rembg concurrents sur un même jeu se
COALESCENT (un seul appel fournisseur, tous servis du même résultat) — ou, si la
coalescence mesurée s'avère fragile, l'aveu explicite à l'écran et ici ; (4) la
réponse du fournisseur est PLAFONNÉE en octets (le même SRC_MAX_BYTES que
l'admission) et sa destination contrôlée (loopback/privé/link-local refusés —
l'API locale :8765 n'a pas d'authentification) ; (5) le sujet hérite de la
RÉDUCTION d'admission (MAX_IMPORT_PX) comme toute image entrante ; (6) sans prix
tabulé, la voie payante N'EST PAS OFFERTE (§8 « prix AVANT » — un bouton payant
sans chiffre est un écart de spec, pas un libellé honnête).

**D6 — Les adoptions vivent chez chaque pièce (cloisonnement §7.1.5).** P10 publie,
ne touche jamais l'état des autres. P1, P2, P3 lisent `doc.capture` avec tolérance
(dérivation pure, patron sectionsBasses — un bouton d'adoption sans matière à
adopter n'existe pas) et offrent LEUR bouton. P2 : nouvelle table `FAMILY_TRAITS`
(bande mm typique + teinte par famille) dans le bloc miroir CF-FRAME-CATALOG (parité
testée §9.2 — ET la copie du lint si le lint en porte une : la parité compte TOUS
les miroirs) ; « adopter la bordure » choisit la famille au plus proche des mesures
(distance à teinte CIRCULAIRE — min(d, 360−d)), pose les réglages MESURÉS clampés
par `LIMITS`, respecte le verrou 3b (lock = non-départ), et AFFICHE l'écart
(« bande 2,1 mm ↔ sable 2,0 mm, teinte à N° » — l'unité d'un angle est le degré ;
spec :510 amendée en ce sens le 24/08) — le test §9.1 exige que l'écart affiché
SOIT l'écart calculé, même chiffre.
**AMENDEMENT ronde T4 (l'aller-retour mesuré : 2/8 avant correction)** :
(1) les axes de FAMILY_TRAITS se mesurent PAR LA VOIE DE PRODUCTION — le banc
rend chaque famille puis la passe dans les analyseurs de P10 EUX-MÊMES
(`_analyse_bordure`, `_couleur_bande`, teinte sur le dominant ARRONDI 8 bits —
la seule forme que la frontière peut porter) : `border.mm` est une profondeur
de premier front, pas une épaisseur de trait, et la table doit parler la même
langue que l'entrée ; (2) la dégénérescence est un FAIT AVOUÉ : cinq familles
froides (runic/arcane/timber/deco/sable) sont indiscernables depuis leur
lisière (même front ~0,9 mm, même teinte de rareté ~211°) — le test
d'aller-retour épingle l'issue honnête (gravure/filigrane se reconnaissent par
la teinte chaude, néon par son front creux ; les jumelles froides tombent sur
la première du groupe et la PHRASE avoue la quasi-égalité) au lieu de
prétendre une reconnaissance que la géométrie interdit ; (3) la teinte d'un
GRIS est un bruit : seuil de saturation mesuré (pas d'égalité exacte), et la
phrase le dit ; (4) `win_lock` est un verrou de PROPORTIONS : le rayon n'en
est pas une, il s'adopte même sous verrou (« le verrou ne gate jamais le
panneau », 3b) ; (5) adopter un rayon fige la fenêtre auto en manuelle
(−16 mm de hauteur mesurés au passage poker→tarot) : la ligne d'écart LE DIT
quand la fenêtre était auto, et Ctrl+Z rend l'auto ; (6) l'id de la 8e famille
est `filigrane` (un trait d'union casserait les lectures `\w+` des trois
tables — limite d'outillage assumée), le libellé porte le nom de la spec.

**D7 — P9 : côté `capture` + manifeste propre, jamais une preuve empruntée.** Les
couches importées ne passeraient pas la preuve d'empilement des peintres — leur
manifeste est le leur : P10 écrit `layers_{carte}_capture.json` au MÊME schéma
(fichiers, sha256, boîtes) avec `source:"capture"` et pour preuve la confiance de
recomposition MESURÉE (fond+sujet vs original, taille de mesure avouée). Le nœud
`layer` gagne `side:"capture"` (miroir + grammaire + validation ; cohérence
nom-du-fichier ↔ contenu exigée), `_lire_manifeste` lit le fichier, le bordereau
avoue la provenance. Rôles mappés : sujet→`illustration`, bordure→`cadre`,
fond→`fond-matiere`. « Une carte importée peut partir en 3D sans être reconstruite »
(§7.1.6) devient un test. L'implémenteur vérifie les portes exactes de
`_lire_manifeste` à la source avant d'écrire.
**AMENDEMENT T5 (la réalité des tâches livrées)** : le mappage ci-dessus a été
écrit avant T2/T3 — les fichiers qui EXISTENT sont source_recto(.verso).png et
sujet_recto.png ; AUCUNE tâche n'a découpé de bordure ni de fond isolés. Le
manifeste capture ne liste QUE ce qui existe, avec sa provenance honnête :
sujet→`illustration` (si présent), et le RECTO ENTIER comme entrée propre
(la face complète de la carte — c'est le chemin minimal vrai de « partir en 3D
sans reconstruction » : la face importée texture un plan au format carte) ;
il n'invente jamais un `cadre` ou un `fond-matiere` qu'aucun fichier ne porte.
La preuve du manifeste = empreintes sha256 + la couverture mesurée du sujet
(le premier chiffre de recomposition disponible, T3) — la recomposition
fond+sujet attendra qu'un fond isolé existe (dette nommée, pas simulée).

**D8 — Le nœud `extrude` (10e kind) : l'anneau-contour en objet.** Le transmis 3c :
contour fermé → anneau extrudé (largeur mm, profondeur mm — plancher partagé avec
`SEAL_MIN_MM`, jumeau épinglé), matériau assignable par référence de nœud (le Sceau
prismatique 3c s'y branche — c'est la « profondeur d'extrusion » du parcours
§7.2:569). Deux contours nommés v1 : le rectangle arrondi du format, l'anneau du
Sceau. Bloc miroir + writer + grammaire + preuve `mesh_report` (fermé — arêtes
appariées —, volume positif calculé SANS compter le trou de l'anneau, orientation
des capuchons testée, imprimable §9.1) ; segments au plancher pour que les capuchons
ne dégénèrent pas. Le filigrane du Patriarche est son cas d'usage nommé (:574
« filigrane en extrusion + matériau Sceau prismatique »).

**D9 — La preuve fragments roule sur la seule face qui existe (F1).** Extraction du
Patriarche par pypdf (page 5, l'image 1060×1484) vers
`.superpowers/samples/patriarch.png` — HORS dépôt (vérifier l'ignore AVANT
d'écrire ; l'incident nom-réel du gauntlet interdit tout actif personnel commité ;
purger les métadonnées du PNG extrait). Pseudonyme fixe dans tous les gabarits et
tests. Le modèle `deepotus-fragments` naît par la voie perso (« enregistré comme
modèle ») depuis le deck de preuve — zéro code modèle neuf. La famille P2 nouvelle
« filigrane-instrument » (double filets ~2,1/~3,2 mm, instruments de coin,
médaillons de mi-chant — vectoriel déterministe) entre au catalogue avec silhouette
QA pairwise + parité. Le dos commun étant ABSENT des sources (F1), le verso de la
preuve = verso 3c par défaut, avoué. Les 91 autres faces n'existant nulle part, le
plan les ATTEND sans les bloquer (le chemin peut arriver à tout moment).

**D10 — Pas d'assistant modal.** Le « parcours guidé » §7.2:564-570 = les 4
capacités réelles (importer l'illustration, choisir/importer la bordure, régler le
Sceau, éditer le verso), affichées comme une liste d'étapes-liens (`CF.show` + ancre
+ dépli des sections escamotées 2d si besoin) sur le panneau P10 quand une capture
est publiée. Un wizard serait du chrome sans substance — avoué ici.

---

## 3. Tâches

Ordre : T1 → T2 → (T3 ∥ T4, propriété de fichiers disjointe) → T5 → T6.

### T1 — La coquille P10 + la persistance élargie (D1, D2)

Les 4 fichiers de la règle 1 (`mod-capture.js`, `mod-capture.css`, `capture.py`,
`test_cards_capture.py`) ; la checklist 1.2 entière (MODULES, lint, index.html,
`__init__.py` avant le filet) ; **`MODULE_IDS` 8→10 avec RED d'abord sur la perte de
`doc.forge3d`** (F2, rejouée par la route réelle) et le test :1050 réécrit ; `POST
/capture/card` (patron post_paper, ?side avec refus nommé, 7e copie
`MAX_IMPORT_PX`) + `GET` de service par liste blanche ; le panneau P10 minimal
(dépôt de fichier recto/verso, aperçu, état « analysé/pas analysé ») sans painter ;
`galImport` câblé (`core.js:2005` : le toast placeholder meurt, `CF.show("capture")`
naît). Jamais-500 partout.
**Fichiers** : les 4 neufs + core.js + index.html + lint_cardforge.py +
`__init__.py` + contract.py + core.py + test_cards_core.py
(+ test_core_contract.mjs, amendement §1.2).

- [x] LIVRÉ — commits `8906ecd` (livraison, 13 fichiers, +1276/−41) puis `bd8f599`
  (ronde, 7 fichiers, +815/−120). RED F2 prouvé par la ROUTE réelle (PATCH→GET :
  forge3d PERDU avant, graphe identique à l'octet après — et un 3e rouge est tombé
  seul : le test qui gardait le chiffre « huit » périmé, celui qui faisait passer
  la perte pour une décision). MODULE_IDS = 10, conséquences tenues ensemble,
  parité core.js↔contract.py testée en lisant le JS depuis Python. Admission
  post_paper complète + concurrence PROUVÉE (40 envois simultanés, recouvrement
  ×34,7 → 40 servis, brouillon unique uuid + replace patient 5×20 ms, 409 nommé
  SANS chemin absolu — la jurisprudence de la fuite de nom). Service sous
  `GET /file/{nom}` (D2 amendé). Analyse = propriété du recto (D3 amendé, règle
  dans une fonction PURE `effacements(side)` exécutée dans node par le test —
  la 1re écriture textuelle ne voyait pas un `|| true`). 8 copies de
  MAX_IMPORT_PX confrontées (4 py + 4 js). galImport câblé, toast placeholder
  mort. Banc mjs : 2 contrôles réécrits sur la vérité neuve + réouverture avant
  Échap. « huit »→« dix » : 7+ corrigés, l'histoire gardée. 29 tests capture,
  93 core, lint 10/10, banc de contrat vert (contre l'arbre du dépôt via serveur
  de scratchpad — le :8765 sert la copie déployée, le banc nu n'aurait rien
  prouvé).
- [x] Ronde adverse (opus) : 18 trouvailles réelles + 4 rejetées part-du-critique.
  Le bloquant : deux POST concurrents = 500 mesuré à 10 % (tmp CONSTANT partagé)
  — et la 1re moitié du fix rendait `{409:40}` dossier VIDE : « jamais-500 » seul
  aurait vu un système poli qui ne sert PERSONNE → le test exige un PLANCHER DE
  SERVICE (≥90 %, fichier final entier). Autres : DecompressionBombError écrasé
  en « corps illisible » (le refus qui se trompe de raison au-delà de 179 Mpx) ;
  le $-NEWLINE POUR LA 4e FOIS (FILE_RE `$`+`.match` — fullmatch d'office sur
  toute liste blanche, désormais) ; le joker GET qui condamnait les routes
  T2/T3/T5 ; le 404 deck-supprimé traduit « backend absent » (le remède jsonNamed
  existait, P10 refaisait le geste à la main) ; le commentaire-doctrine FAUX sur
  le gel du schéma (le code était juste pour une AUTRE raison — patchAs lève —
  et c'est elle qui est écrite maintenant) ; mébipixels étiquetés « millions »
  (137 vs 144 à vingt lignes d'écart dans le même fichier) ; 2 tests-au-texte
  remplacés par les preuves DYNAMIQUES que le critique a mesurées possibles ;
  témoin LANCZOS fermé en 3 lignes (damier : σ 6,0 vs 127,5, seuil 40) ; les
  4 miroirs de la leçon F2 gardés (lint + index.html comptés dans l'ordre) ;
  l'hygiène pré-existante de cards_core réparée (le deck abîmé laissé sur disque,
  intermittence 1/17 antérieure à T1). RED de ronde : 19 défauts remis un à un,
  18 vus.
- [x] CLOSE : leçons — (a) « jamais-500 » sous concurrence est un demi-contrat :
  il faut AUSSI le plancher de service, sinon le refus poli généralisé passe
  vert ; (b) $-newline ×4 : toute liste blanche naît en `fullmatch`/`\Z`, le
  test porte `%0A` d'office ; (c) le témoin survivant nouveau : retirer la
  reprise patiente SEULE n'est vue qu'~1 fois sur 2 (exiger 40/40 rougirait à
  tort sur machine chargée — entre un trou connu écrit et une intermittence
  rouge, le trou écrit gagne). Résidu banc-qa-modele : auto-nettoyé au passage
  suivant du banc (vérifié parti, 8 modèles en place). Incident :8765 clos
  (backend vivant, health 177 ms ; la lenteur 13,8 s du listing à froid est
  antérieure — jalon séparé posé hors phase).

### T2 — L'analyse locale gratuite (D3, D4)

Bordure (balayage 4 bords), zones (blocs + composants connexes NEUFS), fond
(`chroma_key`, refus mesuré §8), palette ; confiances chiffrées publiées ;
`doc.capture` publié par `M.patch` (D3, boîtes en mm) ; l'écran P10 affiche mesures
+ chiffres de confiance (jamais une certitude) ; **tests §9.1 à vérité connue** :
bordure de x mm POSÉE par le test → retrouvée à tolérance chiffrée ; boîtes posées
→ retrouvées ; fond non uni → refus motivé portant la mesure.
**Fichiers** : capture.py, mod-capture.js, mod-capture.css, test_cards_capture.py.

- [x] LIVRÉ — commits `b41ba19` (+1948/−62) puis ronde `7b24997` (+839/−137).
  `POST /analyse` gratuite, PIL pur, to_thread, répond sans publier (la pièce
  publie, D3). Bordure au PREMIER front L1 (le front-au-max était le défaut :
  bandeau de titre battant la bordure 540 vs 455 — tombé contre la vérité
  connue AVANT les tests) ; rayon corrigé du biais de rastérisation par
  INVERSION de la formule connue (r−√r ; posés 10..90 px retrouvés < 0,10 mm,
  tolérance 1,0→0,15 mm) ; zones grille 1,5 MM (amendement D4 : le mm est
  l'invariant, le px dépend du scan — mêmes boîtes au 1/100 mm sur 3
  résolutions, reproduit par la revue) + composants connexes neufs + bande de
  retrait NOMMÉE en mm + `tronquee:true` sur toute boîte qui la touche ;
  chroma_key tel quel, refus portant SA porte (motif) et ses bornes ; palette ;
  échelle par le format (3 formats → mm exacts 1e-3) + bandeau de divergence
  sur core:geom (« le format a changé depuis cette mesure ») ; epaisseurs_mm
  PAR BORD en dict (l'appariement par indice était faux 4/4 sur le banc de la
  ronde) ; isFinite(Number(null))→0,00 fermé par estNombre + test de classe.
  67 tests (vérités connues posées→retrouvées aux tolérances avouées), lint
  10/10, écran vérifié Chrome sans tête (4 états, 0 erreur). Régression T1
  trouvée en chemin (pin forge3d « 9 modules ») réparée par l'orchestrateur
  (`1b2e1e7`).
- [x] Ronde adverse (opus) : 1 bloquant + 6 réels + 9 mineurs + 4 REJETÉS par
  la mesure (l'incrustation-ratio est juste PAR CONSTRUCTION — les % dérivent
  de l'image ; le 409-illisible tient sur vraie troncature IDAT ; 4 témoins
  rejoués exacts ; zéro prix recopié). Le bloquant : la bande morte du retrait
  (3-9 mm aveugles au bord) publiait des boîtes COUPÉES indiscernables de
  mesures — précisément où vivent les bandeaux de titre (le cas Patriarche),
  et T3 en fera naître des slots. Réels marquants : bords/epaisseurs triés par
  des clés DIFFÉRENTES ; l'écran nommait la mauvaise porte du refus ; l'aveu
  BORD_FRONT_RATIO faux dans ses DEUX moitiés (le ratio mord sur profil
  texturé ×31 et pas sur l'image minuscule — l'inverse exact de l'aveu) ;
  coûts réécrits sur la mesure au plafond (1,1 s à 4096², c'est CE chiffre qui
  justifie to_thread) ; le balayage « tout en mm » dérivé des clés au lieu
  d'une liste en dur (la revue avait fait passer une clé px déclarée proprement
  — 56 verts, aucun contrôle ne voyait). Ronde : 11 tests neufs tous RED
  d'abord, 19/19 mutations vues dont 2 trous que la ronde elle-même a ouverts
  et fermés (le contrôle-par-texte dépouillé par _code_js ; le chemin de panne
  joué en faisant mourir _grille), ré-extension (c) REFUSÉE avec sa raison
  (une boîte fausse est pire qu'une boîte courte avouée).
- [x] CLOSE : leçons — (a) une coupe qui ne se dit pas devient une fausse
  mesure chez l'adoptant (`tronquee` est né de là) ; (b) L'AVEU DE TÉMOIN SE
  MESURE comme une affirmation de succès — le « témoin qui n'en était pas
  un » a quitté la liste (6 restants) et est devenu une garde vivante avec
  diagnostic (texture|plat) ; (c) la grille en mm est l'invariant du relevé.
  Dettes T3+ : bg.color d'un bordé = la couleur du POURTOUR (dit à l'écran,
  T3 en tient compte pour la couche fond) ; la phrase option_ia promet le prix
  que T3 apporte de pricing.py ; layers reste vide jusqu'à T3/T5.

### T3 — Le détourage IA opt-in + adoptions P1/P3 (D5, D6)

`GET /capture/ai-options` (disponibilité honnête + prix pricing.py) ; `POST
/capture/rembg` (bascule locale/fal du patron sprite, doctrine 503 §8, espion
étanche zéro dépense) → couche « sujet » ; P1 « adopter l'illustration » (octets du
sujet — ou du recadrage art — dans la pile locale + `setArt("local:…")`, pas de 4e
schéma, undo un pas) ; P3 « adopter les zones » (boîtes → `naitre` groupé, un pas
d'undo, slots éditables §6.1) ; les deux boutons dérivés purs de `doc.capture`
(lecture tolérante).
**Fichiers** : capture.py, mod-capture.js, mod-face.js, mod-type.js,
test_cards_capture.py, test_cards_type.py (si la naissance se teste là).

- [x] LIVRÉ — commits `bbaa115` (+~1000) puis ronde `842ab7f`. ai-options
  honnête (voie local|fal|null, prix de pricing par ÉGALITÉ testée, motifs
  composés, servie même jeu supprimé) ; rembg au basculement sprite (local
  d'abord — ABSENT des deux runtimes, prouvé find_spec, joué par faux module —
  sinon fal, sinon 503 littéral composant les DEUX motifs ; 502 préfixé avec
  l'étape) ; sujet RGBA deck-local au patron atomique T1, réduit comme toute
  image (MAX_IMPORT_PX), couverture publiée ; adoption P1 (sujet sinon recto
  entier avoué, pile locale + setArt local:, pas de 4e schéma, un pas d'undo,
  dédoublonnage avoué) ; adoption P3 (naitre UN appel, zones s'ajoutent,
  SLOTS_MAX confronté, tronquee adoptées + phrase « leur taille est un
  minimum », le drapeau ne traverse pas la frontière du document) ; galerie
  de tests 103→119 capture + 232 type.
- [x] Ronde adverse (opus) : 1 bloquant + 7 réels + 7 mineurs + les grandes
  affirmations vérifiées VRAIES (le périmètre AST fonction-par-fonction jugé
  MEILLEUR que la liste de portes revendiquée ; zero() jamais masqué ;
  tronquee ne casse rien en traversant norm_slots). LE BLOQUANT : la vraie
  clé fal VIVAIT dans le processus de test — config._load_dotenv(override=True)
  écrasait le setdefault du banc : le filet était simple là où l'en-tête le
  croyait double. Fermé en TROIS couches (settings forcé après import +
  fixture autouse + test-preuve) et la sentinelle étendue de 5 à SEIZE noms
  de fal_client. Réels : la régression du repeint (paint() derrière un fetch
  sans délai — le panneau montrait le jeu précédent sans fin) ; la moitié
  « garde-tout » de la doctrine (rembg sans sujet rend l'image quasi intacte
  PAYÉE — seuil 0,995 posé entre 0,99456 et 1,00000 mesurés) ; DEUX CLICS =
  DEUX FACTURES (12 simultanés → 12 invocations mesurées ; réparé par
  COALESCENCE par jeu : 12→1 invocation, tous servis, l'échec aussi se
  partage) ; aucun plafond d'octets sur la réponse fournisseur (borné à la
  LECTURE) ; la garde d'URL jugeait le schéma pas la destination
  (127.0.0.1:8765 passait — loopback/privé/lien-local refusés avec le mot
  juste par cas) ; le sujet non réduit (6000 px intact vs recto 4096) ;
  TROIS témoins non avoués dont imageBlob jouée NULLE PART (le métier
  « garder l'alpha qu'on vient de payer » — un fillRect blanc ne faisait
  bouger aucun contrôle ; désormais banc node, la mutation rougit) ;
  l'adoption répétée polluait en silence (dédoublonnage + phrase). Mutation
  de ronde 22/22 dont 2 qui ont fait corriger LE CONTRÔLE (le mot juste par
  branche ; la mutation qui portait sur le test au lieu du code). RÉSEAU : 0
  prouvé pile socket coupée sur les deux suites (351 tests).
- [x] CLOSE : leçons — (a) UN BANC QUI CROIT NEUTRALISER UNE CLÉ LE PROUVE
  (setdefault ne tient pas contre un dotenv override=True ; le test-preuve de
  neutralisation est né de là) ; (b) l'argent se garde en COUCHES quantifiées
  (périmètre AST + sentinelle complète + clé neutralisée — et le compte de
  noms d'un module se vérifie, 5≠16) ; (c) la concurrence d'un geste PAYANT
  se coalesce, elle ne se « sert » pas (le contrat « tout le monde est servi »
  gravait « tout le monde paie »). Dettes → T5/T6 : layers ne porte que
  sujet ; la recomposition attend un fond isolé (D7 amendé) ; FAL_TIMEOUT_S
  non gardé (avoué) ; rembg local à empaqueter (installeur, dette 3c).

### T4 — L'adoption P2 + la famille « filigrane-instrument » (D6, D9)

`FAMILY_TRAITS` au miroir CF-FRAME-CATALOG (parité §9.2, TOUS les miroirs lint
compris) ; « adopter la bordure » = famille la plus proche (teinte circulaire) +
réglages MESURÉS clampés `LIMITS` + verrou 3b respecté + écart AFFICHÉ = écart
CALCULÉ (test d'égalité au chiffre, §9.1) ; 8e famille « filigrane-instrument »
(double filets ~2,1/~3,2 mm, instruments de coin, médaillons mi-chant, vectoriel
déterministe) + silhouette QA pairwise (`SIL_SEUIL=4`) + parité.
**Fichiers** : frame.py, mod-frame.js, test_cards_frame.py (+ mod-frame.css en
ronde).

- [x] LIVRÉ — commits `be65fd4` (+1941/−12) puis ronde `2c28306` (+1236/−409).
  FAMILY_TRAITS mesurée d'abord au banc propre (chaque famille rendue avec/sans
  sa signature — deux définitions naïves rejetées avec leurs chiffres), puis
  RE-MESURÉE PAR LA VOIE DE PRODUCTION après la ronde (le banc rend, recadre à
  la coupe, et ce sont `_analyse_bordure`/`_couleur_bande` de P10 EUX-MÊMES qui
  relèvent — l'axe s'appelle `front_mm`, la teinte se lit sur l'hexa 8 bits
  publié). Adoption P2 : mapping vérifié à la source (mm→inner_mm ;
  couleur→line_color + metal:false car inkPaint ne lit jamais line_color métal
  allumé ; rayon→window.r reposée entière ; rayon négatif REFUSÉ — une mesure
  qui n'a pas eu lieu — et null jamais 0) ; pondération par l'étendue que le
  catalogue occupe sur chaque axe (publiée /catalog family_scales, étendue de
  teinte CIRCULAIRE par paires) ; verrou : le rayon s'adopte même sous
  win_lock (un rayon n'est pas une proportion) ; le gel de la fenêtre auto se
  DIT quand elle était auto (−16 mm mesurés poker→tarot sinon invisibles),
  Ctrl+Z rend l'auto. 8e famille id `filigrane` (libellé « Filigrane à
  instruments » — le trait d'union casserait les lectures \w+, limite
  d'outillage assumée) : double filet FIL_MM 2,1/3,2 de la coupe, instruments
  au chemin, médaillons ; REDESSINÉE quand elle serrait Gravure (jonc plein =
  la forme de Gravure en gris normalisé → 4 médaillons discrets : 22,43→33,90)
  — silhouettes 8×8 = 168 mesures, minimum 31,60 IDENTIQUE au catalogue à 7 :
  la 8e ne coûte rien. 271 tests frame (30 neufs T4), lint 10/10, Chrome sans
  tête sur le bloc d'adoption, le -1%6 JS/Python fermé par fmod (parité
  d'exécution 14 mesures + 19 couleurs + 2 crêtes + 3 dièses).
- [x] Ronde adverse (opus) : 1 bloquant + 9 réels/mineurs + 7 REJETÉS par la
  mesure (étendue circulaire correcte, instruments sur tarot 0,3 % rognés — la
  crainte du livreur ne se réalisait pas, mm1 0 divergence sur 16 pièges…).
  LE BLOQUANT : l'aller-retour P10→P2 mesuré de bout en bout par la revue =
  2/8 — border.mm (profondeur de premier front, 0,88 mm pour 7 familles !) et
  bande_mm (épaisseur de trait) étaient DEUX GRANDEURS SOUS LE MÊME NOM, et
  test_cards_frame n'importait jamais cards.capture : la boucle n'avait jamais
  été fermée. Après re-mesure par la voie de production : 6/8 se reconnaissent
  (néon par son front creux 3,2, gravure/filigrane par la teinte chaude),
  arcane/deco PROUVÉS indiscernables (même relevé que runic à l'octet — le
  test le prouve au lieu de le supposer) et la phrase avoue les voisines.
  Autres : la teinte d'un gris à 1 LSB choisissait une famille au hasard
  (DEUX planchers nés d'un échec du propre banc du livreur : chroma ≥ 5 ET
  sat ≥ 0,03 — la saturation seule laissait passer #141516 à 3× le seuil) ;
  la teinte de table float irreproductible en 8 bits (4° qui faisaient perdre
  à Gravure sa famille) ; le repli silencieux de Néon (lisière blanche,
  prélèvement sur la demi-carte) résolu structurellement ; la tolérance 2×
  plus large que l'écart qu'elle protégeait → égalité EXACTE sur le front
  (une tolérance ne servirait qu'à cacher une table fausse) ; le témoin
  survivant à raison FAUSSE (sur crête il changeait la famille — crêtes au
  banc, l'ancien témoin rougit, le neuf : échanger sextant/plume de coin,
  décision de dessin pas propriété mesurable) ; L'AMENDEMENT DE SPEC
  REVENDIQUÉ N'EXISTAIT PAS (fait par l'orchestrateur — spec :510 % → degré
  avec trace — et le test LIT désormais la spec au lieu de revendiquer).
  Mutation de ronde : 11/11 rougissent.
- [x] CLOSE : leçons — (a) UNE TABLE DE CORRESPONDANCE SE MESURE PAR LA VOIE
  QUI LA CONSOMMERA : deux grandeurs sous le même nom ne se voient qu'en
  fermant la boucle de bout en bout (le test d'aller-retour est né de là) ;
  (b) une revendication d'amendement se vérifie comme un fait — le test lit
  la source amendée, il ne l'affirme pas ; (c) l'indiscernabilité prouvée
  vaut mieux qu'une reconnaissance prétendue (arcane==runic à l'octet, dit).
  Dettes → T6 : confirmer sur le VRAI Patriarche (≈2,1 mm ; or chaud →
  filigrane sans voisine — sinon publier la mesure, pas retoucher la table) ;
  badge silhouettes au navigateur (l'arbitre reste le badge) ; la table est
  mesurée sans le grain de matter() (avoué aux deux miroirs).

### T5 — P9 : le nœud `extrude` + la source `capture` (D7, D8)

`extrude` 10e kind (params `width_mm`/`depth_mm`/`contour` ; preuves D8 par
`mesh_report` ; matériau assignable — le Sceau s'y branche) ; côté `capture` du nœud
`layer` (grammaire + miroir + validation, cohérence nom↔contenu) ; manifeste capture
écrit par P10 (`layers_{carte}_capture.json`, même schéma, `source:"capture"`,
preuve = recomposition mesurée, taille de mesure avouée) ; `_lire_manifeste`
l'accepte ; bordereau avoue la provenance ; test « une carte importée part en 3D
sans reconstruction » (graphe : layer capture → assemble → artifact, GLB servi).
**Fichiers** : forge3d.py, forge3d_scene.py, mod-forge3d.js, test_cards_forge3d.py,
capture.py (l'écrivain du manifeste), test_cards_capture.py.

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE

### T6 — La preuve deepotus-fragments + intégration (D9, D10)

Extraction Patriarche (pypdf, page 5, 1060×1484, script one-shot sous scripts/qa,
erreur littérale si le PDF manque) → `.superpowers/samples/` hors dépôt (ignore
vérifié AVANT écriture, métadonnées purgées) ; le parcours §7.2 REJOUÉ ET MESURÉ
sur le vrai fichier dans l'app déployée : import → analyse (mesures vs table
d'anatomie :549-556, tolérances avouées ; NB : portrait pleine carte = fond non uni
attendu → le REFUS local est la bonne réponse, rembg reste opt-in non tiré) →
adoptions P1/P2/P3 → famille filigrane-instrument → Sceau 3D-seul → verso (dos
commun absent : verso 3c par défaut, avoué) → « enregistré comme modèle » → galerie
→ export par couches → graphe (illustration mesh, filigrane extrude+Sceau, typo
relief) → GLB+metadata+STL+masque de foil ; parcours guidé D10 (étapes-liens) ;
suite complète sur arbre au repos ; déploiement ; vérification navigateur réelle
zéro dépense ; mémoire ; poussée.
**Fichiers** : mod-capture.js (étapes-liens), scripts/qa (extraction),
test_cards_capture.py (la preuve scriptée sur SYNTHÉTIQUE — le vrai fichier reste
hors CI), + intégration.

- [ ] LIVRÉ
- [ ] Ronde adverse + corrections
- [ ] CLOSE DE PHASE (consigne de sortie ci-dessous)

---

## 4. Consigne de sortie de phase (à remplir en clôture)

- [ ] Bilan de phase (livré, chiffres, poussée).
- **Attendus de l'utilisateur (courant, aucune bloquante)** : les 92 faces + le dos
  commun (le dossier fabricant ne les contient pas — F1) ; le tir meshy-7 réel
  (~30-35 cr) ; UN décor IA réel (~0,03-0,08 $) ; l'œil ~5 min (liste permanente +
  P10 neuf).
- **Transmis potentiels (à arbitrer en clôture)** : ondulation douce (2 phases
  d'aveu — trancher ou enterrer), phase-pointeur (prêt, jamais branché), contour
  SVG d'extrude (v2), empaquetage rembg local (installeur), GC images orphelines
  (17,4 Mo mesurés en 3c), perf cuisson verso 1200 dpi (9,2 s vs budget 4 s).
