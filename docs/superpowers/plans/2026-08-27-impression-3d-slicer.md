# Impression 3D — exports vers le slicer (Elegoo Centauri Carbon 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [x]`) syntax for tracking.

> **PLAN VALIDÉ PAR L'UTILISATEUR LE 27/08 (« le plan me va ») — PHASES
> 0→4 EXÉCUTÉES LE JOUR MÊME, sauf le chapitre de guide (reste connu).**
>
> **RELEVÉ (27/08) :** TDD tenu de bout en bout — banc `test_print3d.py`
> **11 tests** (lecteur GLB pur à fixtures fabriquées à l'octet — cube à
> matrices composées parent×enfant —, refus motivés draco/meshopt/externe/
> non-triangles, STL binaire aux octets, 3MF zip+xml `millimeter` à
> sommets DÉDUPLIQUÉS mesurés, échelle mm/pose au sol, routes
> from-assets3d/from-stl/exports/open à ouvreur MOCKÉ et chemin CONTENU,
> garde du plateau 256 qui avertit sans interdire, miroirs des trois
> écrans) ; le GLB du producteur MAISON (build_glb) se lit tel quel.
> **Phase 1** : bouton « → Impression 3D » de la Forge 3D quand le STL du
> gate est écrit (étanchéité GARANTIE dite par le producteur) —
> cards_forge3d 44 s vert. **Phase 2** : `patch_bundle_print3d.py`
> (nouvelle queue de chaîne, +1567 o, helper `__dzPrint3d` + bouton par
> job de la rangée des formats, node --check OK). **Phase 3** :
> `mod-extrude.js` PUR (oreilles à ponts de trous — **piège attrapé au
> banc : un sommet exactement sur la diagonale d'une oreille doit la
> bloquer, le L concave rendait 400 pour 300** —, prisme fermé prouvé par
> arête-et-son-inverse, volume exact, STL binaire ; **13 contrôles qa,
> 288 cumulés**) + « → Impression 3D… » au menu Exporter du Vectorlab
> (aplatissement martinez éprouvé, union par calque, hauteur par calque
> `nom=mm`, y retourné SVG→plateau, textes ignorés et DITS). **Phase 4** :
> garde 256 TDD ; SLICER_PATH documenté dans le message d'échec
> d'association. Déployé sha-vérifié (backend 2 + statiques 7 + bundle),
> stop+relance, santé 2.5.0. **Preuves réelles** : un job Game Assets 3D
> RÉEL (144 274 triangles) → dossier `preuve-figurine-80-*` STL+3MF,
> dimensions MESURÉES 57,3 × **80,0** × 3,2 mm Z=0, **ouvert dans le
> slicer par association Windows (mode « association » constaté)** ; le
> VRAI « Vitrail - baie generee » extrudé par le vrai menu (prompt
> « 2, contours=5 ») → 7 504 triangles, **161,4 × 246,1 mm** (tient sur
> le plateau, aucun avertissement) **aux niveaux z EXACTS [0 · 2,0 ·
> 5,0 mm] — les verres à 2, les plombs à 5 : le relief vitrail par
> surcharge de calque** ; dossier de preuve vitrail supprimé, l'export
> figurine LAISSÉ (ouvert dans le slicer de l'utilisateur — à lui de le
> jeter ou l'imprimer). **RESTE CONNU (assumé)** : le chapitre « Imprimer
> ses créations » du guide FR/EN + PDF (phase 4) n'est pas écrit — les
> trois boutons portent leurs infobulles complètes en attendant.
>
> La phase 0 était détaillée au pas TDD ; les phases 1→4 cadrées par
> contrats et preuves — exécutées comme telles.

**Contexte matériel :** l'utilisateur a acquis une **Elegoo Centauri
Carbon 2** (FDM, annoncée 27/08/2026). Specs utiles au plan : volume
d'impression **256 × 256 × 256 mm**, buse jusqu'à 350 °C, lit 110 °C
(PLA/PETG/TPU/ABS/ASA), variante Combo 4 couleurs. Elle est livrée avec
**ElegooSlicer**, un fork d'OrcaSlicer/BambuStudio qui embarque le profil
machine de la CC2.

**Goal :** tous les workflows qui produisent du 3D (Forge 3D des cartes,
Game Assets 3D, Studio 3D/Material Forge) **et** les illustrations (le
Vectorlab d'abord) deviennent exportables en un geste vers le slicer :
un dossier d'impression par export (STL + 3MF aux mm réels) et un bouton
« Ouvrir dans le slicer » — personnages de cartes, plateaux, socles,
plaques-décors imprimables sans étape manuelle obscure.

**Architecture :** un service backend `print3d` 100 % local et 100 %
python PUR (le style maison : `gltf_builder.py` écrit déjà du GLB sans
numpy, `forge3d.py` écrit déjà du STL) — lecteur GLB minimal, écrivains
STL/3MF, mise à l'échelle en mm ; l'extrusion des illustrations se calcule
CLIENT dans le Vectorlab (réutilise l'aplatissement martinez éprouvé) et
POSTe le maillage ; le handoff slicer = FICHIER + association Windows
(`os.startfile`), jamais d'API slicer.

**Tech stack :** stdlib python (json/struct/zipfile/xml), PIL déjà présent
(12.3.0), banc `scripts\run-tests.ps1` (un processus par fichier), banc qa
node du Vectorlab pour la géométrie d'extrusion, patcher bundle
assert-gardé (patron `patch_bundle_vectorlab.py`) pour le seul écran qui
vit dans le minifié (Game Assets 3D).

---

## Inventaire des sorties 3D existantes (mesuré dans le code, 27/08)

| Producteur | Sortie | État imprimabilité |
|---|---|---|
| **Forge 3D cartes** (`backend/app/services/cards/forge3d.py`) | GLB toujours + **STL quand le solide est FERMÉ** (gate motivé sur le drapeau `closed` déclaré par les éléments, borne mémoire au refus) + metadata ERC-721 | Le meilleur point de départ : un STL étanche par construction existe déjà |
| **Game Assets 3D** (`asset3d_service.py`, moteurs fal Tripo/Hunyuan/TRELLIS/Rodin/TripoSR) | `model.glb` toujours téléchargé ; `model.{fbx\|obj\|stl\|usdz}` quand le moteur les fournit ; `model.opt.glb` = gltfpack (compression **meshopt — illisible sans décodeur**) ; streaming par `/assets3d/{job}/model.{fmt}` | GLB source lisible (buffers non compressés) ; l'`opt.glb` doit être REFUSÉ motivé par le convertisseur |
| **Studio 3D / Material Forge** | GLB (matériaux PBR) | Convertible par la même voie GLB→STL (la matière ne s'imprime pas, seule la géométrie compte) |
| **Vectorlab** | SVG vectoriel (JSON vérité), PNG rasterisés | Aucune sortie 3D — c'est le pont « illustrations imprimables » à créer (extrusion) |
| **mesh_optimize / gltfpack** | binaire embarqué, résolution `bin/` du dépôt → `%LOCALAPPDATA%\DeepotusVideoGen\bin\gltfpack.exe` | LE patron de provisioning si une dépendance binaire nouvelle devenait nécessaire |

**Contrainte runtime mesurée** : le python embarqué n'a **ni numpy ni
trimesh** (vérifié le 27/08 : `ModuleNotFoundError` sur les deux ; PIL
12.3.0 présent) et ignore `PYTHONPATH` (`._pth`) — toute dépendance
nouvelle passe par le provisioning du build, jamais par pip au vol.

## Choix du slicer (recherche web du 27/08)

**Tranché : ElegooSlicer est le slicer CIBLE ; OrcaSlicer est le repli
compatible.** Motifs, sourcés :

- ElegooSlicer est **livré avec la Centauri Carbon 2** et embarque son
  profil machine ; c'est un fork d'OrcaSlicer/BambuStudio — même moteur,
  mêmes formats ([SimplyPrint — compatibilité CC2](https://simplyprint.io/compatibility/elegoo-centauri-carbon-2-combo),
  [Elegoo officiel](https://www.elegoo.com/pages/elegoo-centauri-carbon-2-combo),
  [Tom's Hardware — test CC2](https://www.tomshardware.com/3d-printing/elegoo-centauri-carbon-2-review)).
- Des profils communautaires CC2 (machine, filaments, calibration)
  s'importent indifféremment dans ElegooSlicer ET OrcaSlicer
  ([dépôt Botmans-Printing-Paradise](https://github.com/Botmans-Printing-Paradise/Elegoo-Centauri-Carbon-2)).
- Formats d'import de la famille Orca : **STL, OBJ, AMF, 3MF, STEP** (+
  ZIP les contenant) ([wiki OrcaSlicer — Import/Export](https://github.com/OrcaSlicer/OrcaSlicer/wiki/import_export)).
- Conséquence d'architecture : **aucune intégration API** n'existe ni ne
  manque — le handoff robuste et pérenne est le FICHIER : produire
  STL/3MF, laisser Windows ouvrir le `.3mf` par association (les deux
  slicers l'enregistrent), l'utilisateur tranche profils/supports/G-code
  dans le slicer, qui est fait pour ça.

## Décisions d'architecture (tranchées)

**D1 — Formats produits : STL binaire (pivot) + 3MF (ouverture).** Le STL
binaire est le pivot minimal pérenne (80 o d'en-tête + 50 o/triangle —
`forge3d.py` sait déjà l'écrire) ; le **3MF** est le fichier qu'on OUVRE :
c'est un ZIP + XML (stdlib pure) qui porte SANS ambiguïté l'unité
(`unit="millimeter"`), le nom de l'objet et plusieurs objets par plateau —
là où l'échelle d'un STL nu se devine. Chaque export écrit les DEUX dans
son dossier. STEP : jamais (nos sorties sont des maillages, pas de la CAO).

**D2 — Conversion GLB→maillage : lecteur GLB minimal PYTHON PUR, refus
motivés.** Écarté : vendoriser trimesh+numpy (deux wheels binaires à
provisionner, des mégaoctets, pour un besoin couvert en stdlib — et le
dépôt ÉCRIT déjà du GLB en python pur, le lire est symétrique). Le lecteur
couvre : GLB v2 (JSON chunk + BIN chunk), accessors POSITION float32 +
indices u16/u32 (+ mode non indexé), hiérarchie de nœuds avec TRS/matrices
COMPOSÉES, primitives TRIANGLES. Il REFUSE PARLANT : extensions de
compression (`KHR_draco_mesh_compression`, `EXT_meshopt_compression` — donc
`model.opt.glb` : le message dit « prends model.glb, l'optimisé est pour
les moteurs de jeu »), primitives non triangulaires, buffers externes
(.bin séparé — nos GLB sont monolithiques). Un GLB fal exotique qui
tomberait hors périmètre a toujours la voie `model.obj`/`model.stl` du
moteur quand elle existe — le service la préfère même quand elle est là
(zéro conversion = zéro risque).

**D3 — Étanchéité : TAGGÉE, jamais réparée.** Le STL de la Forge 3D est
étanche par construction (gate `closed` existant). Les maillages fal sont
pris TELS QUELS : le dossier d'export contient un `impression.json` qui
dit la provenance et si l'étanchéité est GARANTIE (forge3d) ou INCONNUE
(fal, extrusion tolérante) — les slicers de la famille Orca réparent à
l'import et le disent ; on ne réimplémente pas netfabb. Aucune promesse
qu'on ne peut pas tenir.

**D4 — Échelle : mm réels, cible = plus grande dimension.** Les GLB fal
sortent à des échelles arbitraires (l'unité glTF est le mètre mais rien ne
la respecte). Le dialogue d'export demande UNE grandeur : la plus grande
dimension cible en mm, avec presets du domaine — **Figurine 80 mm ·
Pièce/pion 40 mm · Socle 100 mm · Plateau 250 mm** (≤ 256 : le volume CC2
est 256³ ; toute cible > 256 déclenche l'avertissement « dépasse le
plateau de la Centauri Carbon 2 — le slicer devra couper »). Le service
centre le maillage sur l'origine XY, pose Z=0 au sol, met à l'échelle
uniformément. Les sorties DÉJÀ en mm (Forge 3D cartes : géométrie aux mm
du format de carte) s'exportent à l'identité par défaut (preset « tel
quel »).

**D5 — Illustrations → 3D : l'extrusion se calcule CLIENT dans le
Vectorlab.** La voie royale : l'aplatissement des objets vectoriels
(`aplatir_objet`, tolérance 0,25 px, transforms composés, trous
d'orientation FORCÉE — phase 3 du plan Vectorlab, 217 contrôles qa) court
déjà en JS et est verrouillé au banc. L'extrusion d'un polygone à trous en
prisme = murs (quads triviaux par arête) + deux capots (triangulation par
**ear clipping avec ponts trous→extérieur**, module pur nouveau
`mod-extrude.js` testé au banc qa node RED d'abord — aires re-mesurées
contre `aire_multi` existante). Le client produit le STL binaire
(ArrayBuffer) et le POSTe au backend (corps binaire, patron de la route
vignette) qui emballe dossier + 3MF + échelle mm (1 px SVG = choix
utilisateur, presets « plaque 100 mm » / « socle » / hauteur en mm).
Périmètre v1 : UNE hauteur d'extrusion globale + hauteur PAR CALQUE
optionnelle (un vitrail = plombs plus hauts que les verres → relief) ;
les textes refusés parlant (vectorisation hors périmètre, comme les
booléens). PNG→lithophanie (heightmap PIL → grille décimée) : **option
v2**, notée, pas dans ce plan d'exécution.

**D6 — UX : trois boutons, un dossier, une ouverture.**
- Où : **Forge 3D cartes** (l'écran P9 du Cardforge, `mod-forge3d.js` —
  le STL existe déjà : le bouton emballe et ouvre), **Game Assets 3D**
  (bouton par job dans le panneau 3D — c'est le SEUL écran de ce plan qui
  vit dans le bundle → patcher neuf assert-gardé en queue de chaîne,
  patron `patch_bundle_vectorlab.py`), **Vectorlab** (le menu Exporter
  gagne « → Impression 3D (extrusion)… »).
- Dossier : `DeepotusVideoGenData\assets\print3d\<slug>-<date>\`
  (`<nom>.stl`, `<nom>.3mf`, `impression.json`) — un dossier par export,
  jamais d'écrasement muet.
- Ouverture : `POST /api/print3d/open {chemin}` → `os.startfile()` du
  `.3mf` (association Windows d'ElegooSlicer) ; repli : `SLICER_PATH`
  optionnel du `.env` (patron Settings existant — les clés vivent dans
  `DeepotusVideoGenData\.env`) lancé par subprocess ; sinon message
  parlant « installe ElegooSlicer (livré avec la Centauri Carbon 2) ou
  renseigne SLICER_PATH ». Le champ dans l'ÉCRAN Settings du bundle =
  option v2 (un patch de plus, pas nécessaire au flux).

**D7 — Coûts : 0 $.** Conversion, extrusion, emballage, ouverture : tout
est local. Aucun tir fal/Meshy nulle part dans ce plan — les boutons
consomment des sorties DÉJÀ payées ou des vecteurs gratuits.

## Structure de fichiers (prévue)

```
backend/app/services/print3d.py       NEUF — lecteur GLB pur, écrivains STL
                                      binaire + 3MF, échelle/centrage mm,
                                      dossier d'export, ouverture slicer
backend/app/api/routes.py             + section /print3d (from-assets3d,
                                      from-forge3d, from-stl [corps binaire],
                                      liste, open)
backend/tests/test_print3d.py         NEUF — banc complet du service
frontend/vectorlab/js/mod-extrude.js  NEUF — ear clipping + prisme (PUR)
frontend/vectorlab/qa/extrude.test.mjs NEUF — RED d'abord
frontend/vectorlab/js/mod-export.js   + entrée de menu → dialogue extrusion
frontend/cardforge/js/mod-forge3d.js  + bouton « → Impression 3D »
scripts/patch_bundle_print3d.py       NEUF — bouton par job du panneau
                                      Game Assets 3D (queue de chaîne)
```

---

## Phase 0 — Le service `print3d` (noyau, détaillée au pas TDD)

Livrable : le service pur + les routes, prouvés au banc — un GLB de
référence devient un dossier d'impression STL+3MF aux mm demandés, ouvert
dans le slicer par association. Preuve réelle : l'utilisateur ouvre le
`.3mf` produit dans ElegooSlicer et voit l'objet à la bonne taille.

### Task 0.1 : lecteur GLB minimal + triangles monde

**Files:** Create `backend/app/services/print3d.py`,
`backend/tests/test_print3d.py`.

- [x] **Step 1 : test RED** — deux fixtures fabriquées PAR LE BANC :
  (a) un GLB écrit par NOTRE `gltf_builder` (le producteur réel de
  l'app) ; (b) un GLB minimal artisanal (JSON+BIN à la main : un cube
  indexé u16, un nœud avec translation + un enfant avec matrice) :

```python
def test_le_lecteur_glb_sort_les_triangles_en_monde():
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_glb_cube_translate())   # bytes -> list
    assert len(tris) == 12                       # 12 triangles du cube
    xs = [v[0] for t in tris for v in t]
    assert min(xs) == 9.0 and max(xs) == 11.0    # translation x+10 appliquée

def test_le_lecteur_refuse_parlant_les_glb_compresses():
    from app.services import print3d as P3
    import pytest
    with pytest.raises(ValueError, match="meshopt"):
        P3.lire_glb_triangles(_glb_ext_requise("EXT_meshopt_compression"))
    with pytest.raises(ValueError, match="draco"):
        P3.lire_glb_triangles(_glb_ext_requise("KHR_draco_mesh_compression"))
```

- [x] **Step 2 : le voir échouer** (`run-tests.ps1 -Filter print3d` →
  ModuleNotFoundError)
- [x] **Step 3 : implémenter** — parse GLB v2 (magic `glTF`, chunks JSON
  et BIN), accessors POSITION/indices (5126 f32, 5123 u16, 5125 u32),
  parcours des scènes/nœuds avec composition TRS→matrice (ordre T·R·S,
  quaternions) et `matrix` littérale, primitives mode 4 seulement ;
  `extensionsRequired` intersecté avec la liste refusée → ValueError
  nommant l'extension et le remède
- [x] **Step 4 : le voir passer**
- [x] **Step 5 : commit** — `print3d : lecteur GLB pur (triangles monde, refus motives des compressions)`

### Task 0.2 : écrivains STL binaire + 3MF, échelle mm

**Files:** Modify `backend/app/services/print3d.py` ; Test idem.

- [x] **Step 1 : test RED** :

```python
def test_l_ecrivain_stl_binaire_est_conforme_aux_octets():
    from app.services import print3d as P3
    data = P3.ecrire_stl(_deux_triangles())
    assert len(data) == 80 + 4 + 2 * 50
    import struct
    assert struct.unpack("<I", data[80:84])[0] == 2

def test_l_echelle_cible_la_plus_grande_dimension_et_pose_au_sol():
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_glb_cube_translate())     # cube 2 unités
    monde = P3.mettre_a_l_echelle(tris, cible_mm=80.0)
    bb = P3.bbox(monde)
    assert max(b[1] - b[0] for b in bb) == pytest.approx(80.0)
    assert bb[2][0] == pytest.approx(0.0)                   # Z posé au sol
    assert bb[0][0] == pytest.approx(-(bb[0][1]))           # centré en X

def test_le_3mf_est_un_zip_xml_en_millimetres():
    from app.services import print3d as P3
    import io, zipfile, xml.etree.ElementTree as ET
    data = P3.ecrire_3mf(_deux_triangles(), nom="Banc")
    z = zipfile.ZipFile(io.BytesIO(data))
    xml = z.read("3D/3dmodel.model").decode("utf-8")
    root = ET.fromstring(xml)
    assert root.get("unit") == "millimeter"
    assert "[Content_Types].xml" in z.namelist()
```

- [x] **Step 2 : échec constaté** → **Step 3 : implémenter** (STL :
  struct little-endian, normale recalculée par produit vectoriel ; 3MF :
  `[Content_Types].xml` + `_rels/.rels` + `3D/3dmodel.model` — vertices
  dédupliqués, un `<object>` + `<build>`) → **Step 4 : passer** →
  **Step 5 : commit** — `print3d : STL binaire et 3MF stdlib, echelle mm cible et pose au sol`

### Task 0.3 : dossier d'export + routes + ouverture slicer

**Files:** Modify `backend/app/api/routes.py`, `print3d.py` ; Test idem.

- [x] **Step 1 : test RED (app bootée, patron test_vector_docs)** —
  `POST /api/print3d/from-assets3d/{job} {cible_mm, nom?}` → crée
  `assets/print3d/<slug>/` avec `.stl` + `.3mf` + `impression.json`
  (provenance, cible_mm, étanchéité "inconnue"), préfère `model.stl` du
  moteur quand il existe, 404 job inconnu, 409 parlant sur `opt.glb`
  seul ; `POST /api/print3d/from-stl {corps binaire, nom, cible_mm?}`
  (la voie du Vectorlab et de la Forge 3D — magic `solid`/binaire
  vérifié) ; `GET /api/print3d/exports` → liste datée ;
  `POST /api/print3d/open {dossier}` → appelle l'ouvreur (mocké au banc
  par monkeypatch — le banc N'OUVRE RIEN), 404 dossier inconnu, chemin
  contenu dans `assets/print3d` sinon 400 (jamais de startfile
  arbitraire)
- [x] **Step 2 : échec** → **Step 3 : implémenter** (ouvreur :
  `os.startfile(3mf)` ; si association absente (WinError) ou
  `SLICER_PATH` posé → `subprocess.Popen([slicer, chemin])` ; message
  parlant sinon) → **Step 4 : passer + suites voisines** →
  **Step 5 : commit** — `print3d : dossiers d'export, routes, ouverture slicer par association (garde de chemin)`

### Task 0.4 : preuve réelle

- [x] Déploiement patron sha+stop+relance+santé ; par l'API réelle :
  un job Game Assets 3D EXISTANT converti en 80 mm → dossier né, `.3mf`
  ouvert dans ElegooSlicer (l'œil de l'utilisateur : l'objet fait 80 mm
  sur le plateau CC2) ; nettoyage du dossier de test ; relevé au plan

## Phase 1 — Forge 3D cartes → impression

Contrats : dans P9 (mod-forge3d), un bouton « → Impression 3D » par
génération dont le STL existe (le gate `closed` du backend fait déjà foi) :
il emballe le STL déjà écrit via `POST /print3d/from-stl` (preset « tel
quel » — la géométrie carte est déjà en mm — et presets figurine/socle),
puis propose « Ouvrir dans le slicer ». Étanchéité taguée « garantie ».
Miroirs pytest au patron sections K/L/O de test_vector_docs. **Preuve :**
une carte réelle du jeu témoin → figurine 3MF ouverte dans le slicer,
dimensions constatées ; zéro tir.

## Phase 2 — Game Assets 3D → impression

Contrats : le panneau 3D du hub (bundle) gagne un bouton par job —
patcher NEUF `patch_bundle_print3d.py` (queue de chaîne, ancres uniques,
backup dédié, sondes, patron vectorlab) — qui appelle
`POST /print3d/from-assets3d/{job}` avec le dialogue d'échelle (presets
D4) puis l'ouverture. Refus motivé sur les jobs sans GLB source lisible ;
préférence automatique au `model.stl`/`model.obj` du moteur. **Preuve :**
un personnage généré existant → 80 mm dans le slicer ; le message du refus
`opt.glb` constaté sur un job optimisé.

## Phase 3 — Vectorlab → extrusion imprimable

Contrats : `mod-extrude.js` PUR (ear clipping à ponts pour trous, prisme
murs+capots, normales sortantes) testé RED d'abord au banc qa node (aires
des capots = `aire_multi` des anneaux ±0,5 %, volume = aire × hauteur,
maillage fermé : chaque arête partagée par exactement 2 triangles) ; menu
Exporter → « Impression 3D… » : hauteur globale mm, hauteur par calque
optionnelle (relief vitrail), largeur cible mm (presets plaque/socle) ;
le client compile STL binaire → `POST /print3d/from-stl` → ouverture.
Textes refusés parlant. **Preuve :** la « Baie vitrail - demo » réelle en
plaque-relief 120 mm ouverte dans le slicer, plombs surélevés visibles ;
le banc qa node reste vert (217 + les neufs).

## Phase 4 — Finitions : presets, garde plateau, guide

Contrats : garde > 256 mm (avertit, n'interdit pas), `SLICER_PATH`
documenté (Settings `.env` — patron des clés existantes), page du guide
utilisateur (FR/EN, chapitre « Imprimer ses créations » : installer
ElegooSlicer, profils CC2, où vivent les trois boutons) ; `impression.json`
relu par `GET /print3d/exports` pour un futur onglet Library. **Preuve :**
guide régénéré (patron build-packaging), les trois chemins re-déroulés.

## Ordre, dépendances, estimation

0 → 1 → 2 → 3 → 4 (0 est le socle ; 1 est la plus courte — le STL existe ;
3 est la plus riche — géométrie nouvelle au banc). Grossièrement : P0 une
session, P1 une demi, P2 une, P3 une à deux, P4 une demi. Discipline
transverse : TDD RED d'abord partout, un processus par fichier de banc,
commits français sobres, déploiement sha+stop+relance+santé, **ZÉRO
dépense API**.

## Hors périmètre (assumé)

Découpe multi-pièces et clés d'assemblage ; supports/orientation
automatiques (métier du slicer) ; réparation de maillage (D3 : taguer,
pas réparer) ; multi-couleur/AMS (la CC2 Combo gère 4 couleurs — c'est un
réglage slicer, pas un export) ; génération de G-code ; lithophanie PNG
(option v2 notée en D5) ; champ SLICER_PATH dans l'écran Settings du
bundle (v2) ; formats STEP/USD.
