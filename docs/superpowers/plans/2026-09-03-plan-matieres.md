# Game Assets — Matières (Material Forge) : delighting, redressement, aperçu, convention Blender, catalogue CC0, relief physique, générateurs, masques, finitions, photo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer les deux bacs de R10c — parité (P1–P5) puis différenciant (D1–D4) — sur le Material Forge existant, sans réécrire ni `pbr_service` ni `material_store`, et en **mesurant** chaque promesse (le dégradé d'éclairage retiré, le raccord des cartes, les noms écrits dans l'archive, le poids du catalogue, les secondes d'un générateur) avant de l'annoncer à l'écran.

**Architecture :** tout ce qui calcule une image vit dans un module de service **PIL pur, zéro numpy** (`photo_prep`, `hdr_reader`, `pattern_service`, `mesh_paint`), un module par métier ; `material_store` reste le seul propriétaire des chemins `outputs/materials/mat_xxxxxxxx/`, `mesh_edit.ecrire_version` reste la seule plume qui écrit une version de maillage, et `routes.py` n'orchestre que. L'interface va dans la page **autonome** `/materialforge/` (hors bundle) et dans `/etabli/` (autonome aussi) : **zéro patch de bundle** dans tout le plan. Chaque module a son banc-miroir `backend/tests/test_<x>.py` qui relit les PNG, les archives et les GLB écrits — jamais le code qui prétend les produire.

**Tech Stack :** FastAPI, Pillow 12.3 sur le Python embarqué 3.13.15 (`numpy` **absent**, mesuré), `zlib`/`struct`/`zipfile`/`urllib` de la bibliothèque standard, `<model-viewer>` déjà vendu dans `frontend/dist/assets/model-viewer.min.js`, `gltf_builder` / `mesh_edit` / `print3d` existants, catalogue Poly Haven CC0 téléchargé **au build** (jamais depuis l'application).

---

## Périmètre

Les bacs de **R10c** (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`, § *R10c. Game Assets — Matières — réponses*), dans l'ordre imposé : lot 1 = P1 → P5, lot 2 = D1 → D4.

| Lot | Tâche | Bac | Ce qu'elle livre |
|---|---|---|---|
| 1 | T1 | **P1** | `photo_prep.delight` — l'éclairage basse fréquence estimé au flou cyclique large et divisé en domaine log ; la mesure `lowfreq_sd` |
| 1 | T2 | **P1** | `photo_prep.straighten` — quatre coins → `Image.transform(PERSPECTIVE)`, coefficients résolus par un 8×8 en stdlib |
| 1 | T3 | **P1** | câblage : `prep` dans le job `/materials/generate`, route `POST /materials/prep/preview`, `source.prep` dans la fiche et le LISEZMOI |
| 1 | T4 | **P1** | l'écran : panneau « Photo » de `/materialforge/` (quatre coins au clic, délighter, avant/après chiffré) |
| 1 | T5 | **P3** | convention **Blender** dans `naming_catalog` + banc **par convention** qui lit l'archive écrite (noms, canaux ORM, signe Y) |
| 1 | T6 | **P2** | forme d'aperçu « mon modèle » : un GLB de l'Établi habillé de la matière (`mesh_paint.habiller`) |
| 1 | T7 | **P2** | HDRI personnels : décodeur `.hdr` RGBE en stdlib, tonemap → équirectangulaire LDR, ambiance rangée à côté des sept |
| 1 | T8 | **P2** | comparaison côte à côte de deux matières sous la même ambiance |
| 1 | T9 | **P5** | hauteur physique : `height_mm` sur la fiche, dans `material.json`, le LISEZMOI, le bordereau, et **défaut du nœud `relief`** du Forge 3D (→ `print3d`) |
| 1 | T10 | **P4** | catalogue de **trente** matières CC0 Poly Haven téléchargées **au build**, rangées comme des matières ordinaires |
| 2 | T11 | **D1** | `pattern_service` : bruit de valeur seamless **par construction**, budget en secondes mesuré à 1024² |
| 2 | T12 | **D1** | les **dix** générateurs paramétriques + `GET /materials/patterns` et `POST /materials/patterns/{id}` |
| 2 | T13 | **D1** | l'écran : onglet « Générateurs » avec réglages en direct |
| 2 | T14 | **D2** | `mesh_paint.masques` : cavités et arêtes calculées depuis la géométrie (courbure multi-échelle), budget mesuré sur 100 000 triangles |
| 2 | T15 | **D2** | une matière **par partie** : `POST /etabli/habiller` (par `mesh_edit.ecrire_version`), `GET /etabli/masques`, panneau Parties |
| 2 | T16 | **D3** | finitions nommées `_SURFACE_RECIPES` (métal brossé, laque, cuir, émissif animé) + aperçu temps réel |
| 2 | T17 | **D4** | photo depuis le téléphone : la **moitié Material Forge** de la porte d'entrée (`POST /materials/from-photo`), le transport restant à R12 P1 |
| — | T18 | — | campagne de mutations `backend/tests/mutations_matieres.py` |

**Liens, par identifiant, sans replanifier** — ces bacs-là appartiennent à d'autres plans et ne sont **pas** réouverts ici :

- **R10f** (Établi) : les *Parties* d'un maillage sont un acquis de R10f (panneau `rendreParties`, granularités nœud / maillage / matériau) ; T15 s'y greffe et n'en change ni la sélection ni la doctrine « ce panneau n'écrit rien » — c'est la nouvelle route qui écrit, par `mesh_edit`. R10f P1 à P6 restent au plan Établi.
- **R12** (compagnon mobile) : l'appairage, le jeton d'appareil et l'écoute LAN sont **R12 P1**. T17 livre la cible (une photo entre, ressort redressée, délightée et dérivée) ; le transport est nommé, chiffré nulle part ici, et **non planifié dans ce document**.
- **R10e D3** (matière du Forge sur un modèle) : T6 et T15 posent le moteur (`mesh_paint`) que ce bac consommera ; le reste de R10e (rig, LOD, conversion, banc, GPU local) n'est pas touché.

**Écartés** : E1 (taille physique propagée aux moteurs) et E2 (appel de l'API Poly Haven depuis l'application) — voir la section « Écarté », qui porte aussi une **correction de référence** mesurée aujourd'hui.

### Ce que le terrain dit — relu et mesuré le 03/09/2026

| Fait mesuré | Où | Conséquence |
|---|---|---|
| `pbr_service._cyclic(img, flt, reach)` borde l'image de `p = ceil(reach)` px prélevés cycliquement (tuilage 3×3), filtre, recadre — c'est CE détail qui garde les cartes raccordables | `pbr_service.py:140-157` | T1 et T11 s'en servent tels quels ; le delighting et le bruit héritent gratuitement du raccord |
| `_LOG_LUT` / `_LOG_FLOOR = 6.0` existent déjà : le micro-contraste travaille en **logarithme** parce que le contraste est multiplicatif (loi de Weber) | `pbr_service.py:296-305` | T1 réutilise l'idée : une division d'éclairage devient une **soustraction** en log, donc deux `point()` et un `ImageChops` |
| `_c8` et `_cyclic` sont **privés** ; aucun module ne les importe aujourd'hui | `pbr_service.py:150,159` | T1 les réexporte publiquement (`cyclic`, `clamp8`) plutôt que de faire importer un nom souligné |
| Les huit cartes sont dérivées **localement, gratuitement, hors ligne** ; `derive_maps` à 4096² tient sous 25 s (banc `test_pbr_service.py`, dernier test) | `pbr_service.py:440` | T10 n'embarque que les cartes **mesurées** par Poly Haven et laisse les autres se dériver |
| `MESHES = ("sphere","cube","torus","cylinder","plane","tiled")` | `material_store.py:80` | des cinq formes demandées par R10c, **quatre existent déjà** : seule « mon modèle » manque → T6 |
| `NAMINGS = ("standard","unity_urp","unity_hdrp","unreal","godot")`, `NAMING_LABELS["standard"] = "Standard (Blender, Substance, Marmoset)"` | `material_store.py:105,112` | Blender est aujourd'hui **sous-entendu** dans « standard » : T5 lui donne sa propre cible, ses emplacements Principled BSDF et sa note |
| `env_service` génère **7** ambiances 1024×512 en PIL pur, mises en cache sous `outputs/materials/_env/<nom>-v<N>.jpg` ; `material_store.env_jpeg` passe le nom par une **liste blanche** avant d'appeler | `env_service.py:45-130,249`, `material_store.py:1834` | T7 ajoute des ambiances **personnelles** sans toucher la liste blanche des sept : un second espace de noms, préfixé |
| `material_store.env_jpeg` cherche `env_bytes`, `env_jpeg`, `build_env` par `importlib` et retombe sur `_fallback_env` | `material_store.py:1834-1879` | T7 branche les ambiances personnelles **dans `env_service`**, jamais dans le repli |
| Le GLB d'aperçu est mis en cache disque sur une clé **hexadécimale** (`preview_cache_get`/`put` refusent silencieusement tout le reste), ré-empreintée en sha1 dans la route | `routes.py:7635-7695` | T6 et T16 ajoutent leurs paramètres **dans l'empreinte**, sinon l'ancien GLB serait servi |
| `_mat_glb` charge, redimensionne, **cuit les niveaux** puis encode : l'aperçu et l'export partagent une seule formule | `routes.py:7697-7742` | T6 et T16 passent par lui, jamais à côté |
| `export_zip` écrit les cartes selon `naming_map`, plus `material.json` (avec le bloc `render`) et `LISEZMOI.txt` | `material_store.py:1694-1737` | le banc de T5 lit **l'archive**, pas la table de noms |
| `mesh_edit.lire_glb` / `ecrire_glb` sont la chirurgie GLB du dépôt ; `ecrire_version` est la **seule plume** qui dépose une version | `mesh_edit.py:42,76,883` | T6 lit sans écrire ; T15 écrit **par** `ecrire_version`, comme les cinq routes existantes |
| Les routes d'écriture de l'Établi passent la même porte `_etabli_glb_cible` (entier ≥ 1, deux gardes de chemin, `depuis` dans la fiche) | `routes.py:9480-9500` | T15 en est une de plus et passe la même porte, sans en inventer une |
| Le nœud `relief` du Forge 3D borne `depth_mm` à `(0.05, RELIEF_DEPTH_MM_MAX=3.0)` avec un défaut **aveugle** de 0,6 mm | `cards/forge3d.py:175,817-820` | T9 remplace l'aveugle par la hauteur **déclarée par la matière**, écrêtée en le disant |
| `MATERIAL_FINISHES = ("aucune",) + HOLO_KINDS + GLASS_KINDS` = 6 valeurs (`argent`, `dorure`, `verre`, `verre-depoli`, `translucide`) | `cards/forge3d.py:276`, `forge3d_scene.py:619,1099` | T16 ajoute une **troisième famille** (`_SURFACE_RECIPES`) au même vocabulaire fermé, publiée par `/info` |
| `scripts/build_starter_catalog.py` est le patron d'un catalogue téléchargé au build : `--fetch` / `--check`, `_assert_cc0` qui **abandonne** si la licence n'est pas CC0, `NOTICE.txt`, sortie dans `backend/app/assets/starter/` — embarquée par l'installeur qui recopie `{#AppRoot}\*`, **rien à ajouter au .iss** | `scripts/build_starter_catalog.py:1-42,266-392,493-534` | T10 le décalque : `scripts/build_materials_catalog.py` → `backend/app/assets/materials/`, **zéro ligne d'installeur** |
| `starter_catalog.py` mémoïse `catalog.json`, confine les chemins sous `STARTER_DIR`, et **recopie** un élément dans la Bibliothèque plutôt que de le servir « à part » | `starter_catalog.py:52-117,178-220` | T10 recopie de même : une matière du catalogue devient une matière ordinaire `mat_xxxxxxxx` |
| `/materialforge/` est monté en statique **hors bundle** (`main.py:357-382`), `/etabli/` de même | `main.py` | zéro `patch_bundle_*.py` dans ce plan (voir « Coût de patch ») |
| Chaîne des `.bak` du bundle présente dans ce worktree : `dzrailmotion → version → dznodecat → seedance25` ; l'onglet « ✨ Matières » du hub est déjà posé par `patch_bundle_materialforge.py` (5 ancres) | `frontend/dist/assets/*.bak_*`, `scripts/patch_bundle_materialforge.py` | rien à rejouer : aucune tâche ne touche le bundle |

### Règles du dépôt qui s'appliquent ici

- **`python`** = le runtime embarqué : `$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. Les bancs se lancent **un processus par fichier**, depuis `backend/` : `python tests/test_<x>.py`. **Jamais `pytest tests`** (chaque fichier fige `app.config` avec son propre environnement temporaire ; en processus partagé, le premier fuit dans tous les suivants).
- Chaque banc commence par `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` et isole `DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER` dans un `tempfile.mkdtemp()` **avant** tout `import app.*` (patron `test_meshy_service.py:8-31`).
- **Bancs-miroirs, trois temps** : lire ce qui est **écrit** (le PNG relu depuis le disque, l'archive rouverte, le GLB reparsé), vérifier que la surface lue est la vraie, compter les **assertions** — pas les noms de tests.
- **Le souvenir n'est pas une mesure.** Toute référence extérieure est relue le jour où on s'en sert, avec la date figée dans le docstring du module ou du banc.
- **Jamais numpy.** Le runtime embarqué n'en a pas (mesuré). Toute boucle par pixel Python est remplacée par une opération PIL pleine toile, ou bornée à un petit canevas ensuite agrandi (patron `env_service._radial`, `stage_service._radial_mask`).
- **Commits** : sujet **sans accents**, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, **aucun guillemet double** dans le `-m`.
- Le POURQUOI se dit **avec la mesure**, et la mesure d'abord : un commentaire qui annonce un défaut corrigé porte le chiffre d'avant et le chiffre d'après.

---

## Coût de patch

`/materialforge/` et `/etabli/` sont des pages **autonomes servies en statique** (`main.py:357-382`) : leur JS/CSS/HTML se modifie directement, sans `patch_bundle_*.py`, sans `.bak`, sans rejeu de chaîne. L'onglet « ✨ Matières » du hub `DzGameAssetsHub` est **déjà** dans le bundle (`scripts/patch_bundle_materialforge.py`, 5 ancres) et **aucune tâche de ce plan ne le touche**.

| Tâche | Surface | Coût de patch |
|---|---|---|
| T1 P1 delighting | backend (`photo_prep.py` nouveau, 2 réexports dans `pbr_service.py`) | **0 patch** |
| T2 P1 redressement | backend (`photo_prep.py`) | **0 patch** |
| T3 P1 câblage | backend (`routes.py`, `material_store.py`) | **0 patch** |
| T4 P1 écran Photo | `/materialforge/` (autonome) : `index.html`, `materialforge.js`, `materialforge.css` | **0 patch** — bon marché |
| T5 P3 Blender | backend (`material_store.py` seul) | **0 patch** |
| T6 P2 mon modèle | backend (`mesh_paint.py` nouveau, `routes.py`) + `/materialforge/` | **0 patch** |
| T7 P2 HDRI | backend (`hdr_reader.py` nouveau, `env_service.py`, `material_store.py`, `routes.py`) + `/materialforge/` | **0 patch** |
| T8 P2 côte à côte | `/materialforge/` seul | **0 patch** — bon marché |
| T9 P5 hauteur mm | backend (`material_store.py`, `cards/forge3d.py`, `routes.py`) + `/materialforge/` | **0 patch** |
| T10 P4 catalogue | `scripts/build_materials_catalog.py` nouveau, `backend/app/services/starter_materials.py` nouveau, `routes.py`, `/materialforge/` ; sortie sous `backend/app/assets/materials/`, embarquée par l'installeur telle quelle | **0 patch**, **0 ligne de .iss** |
| T11–T13 D1 générateurs | backend (`pattern_service.py` nouveau, `routes.py`) + `/materialforge/` | **0 patch** — les réglages sont bon marché |
| T14–T15 D2 par partie | backend (`mesh_paint.py`, `routes.py`) + `/etabli/` (autonome) | **0 patch** |
| T16 D3 finitions | backend (`cards/forge3d_scene.py`, `cards/forge3d.py`, `routes.py`) + `/materialforge/` | **0 patch** |
| T17 D4 photo | backend (`routes.py`) + `/materialforge/` ; le transport est R12 P1 | **0 patch** |
| T18 mutations | `backend/tests/mutations_matieres.py` | **0 patch** |

**Total : zéro patch de bundle, zéro rejeu de `repatch_all.py`, zéro ligne d'installeur.** C'est exactement ce que R10c annonçait (« `/materialforge/` est autonome — P2, D1, D2, D3 y sont bon marché ») ; la seule surface partagée est le Forge 3D des cartes (T9, T16), qui se modifie en Python.

---

## Références vérifiées

Seules ces sources servent d'argument. Tout le reste est marqué « de mémoire » et se prouve au banc.

| Source | Relue le | Ce qu'elle dit (chiffres ou verbatim) | Sert à |
|---|---|---|---|
| `api.polyhaven.com/assets?t=textures` (et `&c=metal`, `&c=fabric`) | **03/09/2026**, HTTP 200 | JSON `{slug: {name, categories, …}}` ; les 30 identifiants de T10 y sont tous présents (vérifiés un par un) | T10 |
| `api.polyhaven.com/files/rusty_metal` | **03/09/2026**, HTTP 200 | clés de premier niveau = noms de cartes : `Diffuse`, `nor_dx`, `nor_gl`, `AO`, `Rough`, `Displacement`, `spec`, `arm`, `blend`, `gltf`, `mtlx` ; puis résolution (`8k`/`4k`/`2k`/`1k`), puis format (`jpg`/`png`/`exr`), puis `{size, md5, url}`. Exemple : `Diffuse.1k.jpg.url = https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_metal/rusty_metal_diff_1k.jpg`, `size = 577389`, `md5 = ba829f953270d3ad87d8e86d840f71d6` | T10 : on lit l'URL et le **md5** dans l'API, on ne devine **jamais** un chemin |
| `api.polyhaven.com/info/brick_wall_001` | **03/09/2026**, HTTP 200 | `name`, `categories`, `tags`, `authors` (`{"Rob Tuytel":"Processing","Dimitrios Savva":"Photography"}`), `dimensions [3000,3000]`, `scale "1.5x1.5"`, `max_resolution [8192,8192]`, `date_published`, `files_hash`. **Aucun champ `license` par asset** | T10 : les auteurs viennent d'ici, la licence se vérifie **une fois** sur `polyhaven.com/license` |
| `github.com/Poly-Haven/Public-API` (README), `ToS.md` (branche `master`), `polyhaven.com/our-api` | **03/09/2026** | README : « Free to use for any purpose, personal or commercial, forever. The assets themselves are CC0 and never require attribution — but building on the live API specifically requires a small "Powered by Poly Haven" credit. » ToS : « The API is free to access and use by anyone… for any purpose, including commercial use, at no charge » et « All API calls must be made with a unique "Referer" header or user-agent that matches your software name ». `our-api` : annonce **datée du 18 juillet 2026** | T10 **et correction de E2** : l'interdiction citée par R10c est **levée depuis le 18/07/2026** — voir « Écarté » |
| `en.wikipedia.org/wiki/RGBE_image_format` | **03/09/2026** | nombre magique `23 3f 52 41 44 49 41 4e 43 45 0a` = `#?RADIANCE` + saut de ligne ; « one byte each for RGB values with a one byte shared exponent… four bytes per pixel » ; `fR = R·2^(E−128)` | T7 |
| `graphics.cornell.edu/~bjw/rgbe.html` (Bruce Walter) | **03/09/2026**, HTTP 200 | publie l'implémentation de référence `rgbe.txt` / `rgbe.h` / `rgbe.c` ; renvoie à Greg Ward, « Real Pixels », *Graphics Gems II*. **`rgbe.c` lui-même répond HTTP 300 à la lecture automatique** (mesuré) | T7 : la page fait foi pour l'existence de la référence ; le décodeur est écrit depuis la spec et **prouvé par aller-retour au banc** |
| `floyd.lbl.gov/radiance/refer/filefmts.pdf` (Radiance, formats de fichiers) | **03/09/2026**, HTTP 200, **148,6 Ko** | PDF officiel ; **non lisible par l'outil de lecture de ce poste** (`pdftoppm` absent — mesuré) | T7 : cité comme source primaire, non recopié |
| Manuel Blender, *Principled BSDF* | **03/09/2026** | **La page répond HTTP 403 à la lecture automatique** (mesuré sur `latest` **et** sur `4.2`) — même mode d'échec que les pages Runway de R1. Extraits obtenus par recherche : *Base Color* « Overall color of the material used for diffuse, subsurface, metal and transmission » ; *Metallic* « Blends between a dielectric and metallic material model » ; *Roughness* « Specifies microfacet roughness of the surface for specular reflection and transmission » ; *IOR* « Index of refraction for specular reflection and transmission » ; *Alpha* « Controls the transparency of the surface, with 1.0 fully opaque » ; *Normal* « Controls the normals of the base layers » ; panneaux *Coat*, *Sheen*, *Emission*, *Subsurface*, *Specular*, *Transmission*, *Thin Film* | T5 : la note de la convention Blender cite ces sockets **et** dit le 403 |
| Manuel Blender, *Normal Map Node* | **03/09/2026** | (403 en lecture directe ; extraits de recherche) espace **Tangent** par défaut ; Blender suit la convention **OpenGL**, canal vert = **+Y vers le haut** ; la texture doit être en **Non-Color** pour une normale tangente | T5 : `blender` hérite du `normal_invert_y = False` du dépôt, et la note impose *Non-Color* sur toutes les cartes de données |
| Documentation Pillow, `Image.transform` / `ImageChops` | **de mémoire, prouvé au banc** | `PERSPECTIVE` prend 8 coefficients qui vont de la **destination vers la source** ; `ImageChops.add(a,b,scale,offset) = (a+b)/scale + offset` écrêté, `subtract` de même | T1, T2 : chaque contrat est **prouvé par une assertion** avant d'être utilisé |
| R10c (balayage, 03/09/2026) : Substance 3D Sampler « Delight (AI powered) », Materialize (github.com) | **03/09/2026** (relues dans R10c) | Substance retire l'éclairage de la basecolor sans paramètre ; Materialize est du code Unity/GPU, lisible mais non réutilisable en PIL | T1 : la barre à atteindre, pas une implémentation à copier |
| Quixel, ArmorPaint, Substance Painter | **de mémoire, non vérifiés** | — | aucun argument de ce plan ne s'y appuie |

---
## Lot 1 — parité

### Task 1 : P1 — le delighting, et le chiffre qui le prouve

**Files:**
- Create: `backend/app/services/photo_prep.py`
- Modify: `backend/app/services/pbr_service.py:25-34` (`__all__`), `backend/app/services/pbr_service.py:159-161` (réexports publics après `_c8`)
- Test: `backend/tests/test_photo_prep.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_photo_prep.py` :

```python
# -*- coding: utf-8 -*-
"""Material Forge P1 — préparer une photo : DELIGHTING (T1) puis REDRESSEMENT
(T2). Plan docs/superpowers/plans/2026-09-03-plan-matieres.md.

BANC-MIROIR : toute mesure est prise sur un PNG RELU DEPUIS LE DISQUE, jamais
sur l'objet PIL encore en mémoire — c'est le fichier qui part au raccord puis
à la dérivation, donc c'est le fichier qu'on mesure.

Run (depuis backend/) : python tests/test_photo_prep.py
"""
import math
import os
import pathlib
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageChops, ImageFilter, ImageStat      # noqa: E402

from app.services import photo_prep as PP                      # noqa: E402

PASS = 0
DIR = pathlib.Path(_tmp) / "prep"
DIR.mkdir(parents=True, exist_ok=True)


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def ecrire(img, nom):
    """Écrit un PNG puis le RELIT. Toute mesure part de ce retour."""
    p = DIR / nom
    img.convert("RGB").save(p, format="PNG")
    with Image.open(p) as im:
        return im.convert("RGB")


def tuile(w=256, h=256):
    """Tuile périodique dont l'énergie est HAUTE FRÉQUENCE (périodes 51, 23 et
    13 px sur 256). Volontairement pas de composante lente : sinon le flou
    d'estimation la confondrait avec l'éclairage, et le banc mesurerait le
    grain de la texture au lieu du dégradé qu'on veut retirer."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = 128.0
            for kx, ky, amp in ((5, 4, 40.0), (11, 7, 22.0), (19, 13, 12.0)):
                v += amp * math.sin(2 * math.pi * kx * x / w) \
                         * math.cos(2 * math.pi * ky * y / h)
            v = max(6.0, min(249.0, v))
            px[x, y] = (int(v), int(v * 0.84 + 14), int(v * 0.62 + 32))
    return img


def eclairer(img, lo=0.35, hi=1.0):
    """Le dégradé d'éclairage d'une photo prise à la fenêtre : une rampe
    diagonale multiplicative, plus une vignette douce."""
    w, h = img.size
    ramp = Image.new("L", (w, h))
    d = ramp.load()
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    for y in range(h):
        for x in range(w):
            t = (x / (w - 1) + y / (h - 1)) / 2.0
            r = math.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2) / 1.4143
            k = (lo + (hi - lo) * t) * (1.0 - 0.28 * r * r)
            d[x, y] = int(round(255.0 * max(0.0, min(1.0, k))))
    return Image.merge("RGB", tuple(ImageChops.multiply(c, ramp)
                                    for c in img.split()))


def rouler(img, dx, dy):
    """Translation CYCLIQUE (sur le tore) — le seul déplacement qui laisse une
    tuile identique à elle-même."""
    w, h = img.size
    out = Image.new(img.mode, (w, h))
    for ox in (dx - w, dx):
        for oy in (dy - h, dy):
            out.paste(img, (ox, oy))
    return out


def grain(img, r=2.0):
    """Énergie de contraste LOCAL : moyenne de |L - flou(L, r)|. C'est le
    DÉTAIL de la matière — ce que le delighting doit laisser vivre."""
    lum = img.convert("L")
    return ImageStat.Stat(ImageChops.difference(
        lum, lum.filter(ImageFilter.GaussianBlur(r)))).mean[0]


def ecart(a, b):
    """Écart moyen en niveaux, sur les trois canaux."""
    st = ImageStat.Stat(ImageChops.difference(a.convert("RGB"),
                                              b.convert("RGB"))).mean
    return sum(st) / len(st)


def part(img, niveau):
    """Part des pixels de luminance exactement `niveau` (0 ou 255)."""
    h = img.convert("L").histogram()
    return h[niveau] / float(sum(h) or 1)


def delight_naif(img, radius_frac=None):
    """LE TÉMOIN : la MÊME division, avec un flou NON cyclique. C'est ce que
    fait toute implémentation qui ignore le bord — et c'est la seule
    différence entre les deux, donc la seule cause possible d'un écart."""
    frac = PP.DELIGHT_RADIUS_FRAC if radius_frac is None else radius_frac
    rgb = img.convert("RGB")
    r = max(2.0, frac * min(rgb.size))
    lf = rgb.convert("L").filter(ImageFilter.GaussianBlur(r))
    lg = lf.point(PP.LOG_LUT)
    hi = lg.histogram()
    n = sum(hi) or 1
    pivot = sum(i * c for i, c in enumerate(hi)) / n
    ec = lg.point([PP.clamp8(128.0 - (v - pivot)) for v in range(256)])
    return Image.merge("RGB", tuple(
        ImageChops.add(c.point(PP.LOG_LUT), ec, 1.0, -128).point(PP.EXP_LUT)
        for c in rgb.split()))


# ══ 1 · les contrats Pillow dont tout dépend, PROUVÉS ═══════════════════════
a4 = Image.new("L", (4, 4), 200)
b4 = Image.new("L", (4, 4), 60)
assert ImageChops.add(a4, b4, 1.0, -128).getpixel((0, 0)) == 132
assert ImageChops.add(a4, b4, 1.0, 0).getpixel((0, 0)) == 255          # écrêté
assert ImageChops.subtract(a4, b4, 1.0, 128).getpixel((0, 0)) == 255   # écrêté
assert ImageChops.subtract(b4, a4, 1.0, 128).getpixel((0, 0)) == 0     # écrêté
ok("ImageChops.add/subtract = (a ± b)/scale + offset, écrêté 0-255")

pire = max(abs(PP.EXP_LUT[PP.LOG_LUT[v]] - v)
           for v in range(int(PP.LOG_FLOOR), 256))
assert pire <= 4, pire
assert PP.LOG_LUT[int(PP.LOG_FLOOR)] == 0 and PP.LOG_LUT[255] == 255
ok(f"LOG_LUT / EXP_LUT inverses au-dessus du plancher : écart max {pire} niveau(x)")

# ══ 2 · le dégradé d'éclairage part, le grain reste ═════════════════════════
base = tuile(256, 256)
src = ecrire(eclairer(base), "avant.png")
out = ecrire(PP.delight(src), "apres.png")

sd_av, sd_ap = PP.lowfreq_sd(src), PP.lowfreq_sd(out)
assert sd_av > 8.0, sd_av
assert sd_ap < 0.30 * sd_av, (sd_av, sd_ap)
assert sd_ap < 6.0, sd_ap
ok(f"delighting : écart-type basse fréquence {sd_av} -> {sd_ap} "
   f"(-{100 * (1 - sd_ap / sd_av):.0f} %)")

g_av, g_ap = grain(src), grain(out)
assert 0.9 <= g_ap / g_av <= 2.4, (g_av, g_ap)
ok(f"le grain survit : {g_av:.2f} -> {g_ap:.2f} niveau(x) "
   f"(x{g_ap / g_av:.2f} — il REMONTE, l'ombre ne l'écrase plus)")

assert part(out, 255) < 0.02 and part(out, 0) < 0.02, \
    (part(out, 255), part(out, 0))
ok("aucun écrêtage : moins de 2 % de pixels à 0 ou à 255 après delighting")

# ══ 3 · le bordage CYCLIQUE, prouvé par la seule propriété qu'il donne ══════
# Sur le tore, délighter puis rouler doit donner la MÊME image que rouler puis
# délighter. C'est exactement ce que `pbr_service.cyclic` achète, et c'est
# invérifiable autrement : un flou à bord fermé n'a aucune raison d'y arriver.
d1 = rouler(PP.delight(src), 77, 41)
d2 = PP.delight(rouler(src, 77, 41))
e_cyc = ecart(d1, d2)
n1 = rouler(delight_naif(src), 77, 41)
n2 = delight_naif(rouler(src, 77, 41))
e_naif = ecart(n1, n2)
assert e_cyc < 2.0, e_cyc
assert e_naif > 3.0 * e_cyc, (e_cyc, e_naif)
ok(f"bord cyclique : delight ∘ roulement == roulement ∘ delight à "
   f"{e_cyc:.2f} niveau ; le témoin à bord fermé dérive de {e_naif:.2f}")

# ══ 4 · jamais d'exception, et strength=0 ne touche à rien ══════════════════
zero = PP.delight(src, strength=0.0)
assert ecart(zero, src) == 0.0
for mauvais in (None, "abc", -5, 12, float("nan"), [1], {"a": 1}):
    got = PP.delight(src, strength=mauvais)
    assert got.mode == "RGB" and got.size == src.size, mauvais
for img in (Image.new("L", (1, 1), 20), Image.new("P", (9, 7)),
            Image.new("RGBA", (5, 5), (9, 9, 9, 255))):
    got = PP.delight(img)
    assert got.mode == "RGB" and got.size == img.size, img.mode
ok("delight ne lève jamais : réglage pourri -> défaut, mode exotique -> RGB, "
   "strength=0 -> octets identiques")

# ══ 5 · budget ═════════════════════════════════════════════════════════════
gros = base.resize((2048, 2048), Image.LANCZOS)
t0 = time.perf_counter()
PP.delight(gros)
dt = time.perf_counter() - t0
assert dt < 6.0, dt
print(f"\n  delight 2048² : {dt:.2f} s (budget 6,0 s)")

print(f"\nOK — {PASS} assertions groupées vertes (photo_prep, delighting)")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

Run (depuis `backend/`, `python` = `$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`) :

```
python tests/test_photo_prep.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.photo_prep'`.

- [ ] **Step 3 : ouvrir `pbr_service` juste ce qu'il faut**

Dans `backend/app/services/pbr_service.py`, remplacer la fin de `__all__` (ligne 33) :

```python
    "map_report", "seam_report", "SEAM_SCALES", "SEAM_GRADES", "seam_grade",
]
```

par :

```python
    "map_report", "seam_report", "SEAM_SCALES", "SEAM_GRADES", "seam_grade",
    "cyclic", "wrap", "clamp8",
]
```

et, juste après la définition de `_c8` (ligne 159-161), ajouter :

```python
# Réexports PUBLICS — un seul propriétaire du bordage.
#
# `photo_prep` (delighting) et `pattern_service` (générateurs) doivent border
# EXACTEMENT comme nous : sinon leur sortie cesse d'être raccordable, et le
# seul argument mesurable du Material Forge tombe. Deux voies s'offraient :
# importer `_cyclic` chez le voisin — un nom souligné qui traverse un module —
# ou recopier la fonction — deux bordages qui dérivent au premier correctif.
# Un alias public, donc : le code reste ici, il n'en existe qu'une version.
cyclic = _cyclic
wrap = _wrap
clamp8 = _c8
```

- [ ] **Step 4 : écrire `photo_prep.py` — le delighting seul**

Créer `backend/app/services/photo_prep.py` :

```python
# -*- coding: utf-8 -*-
"""Material Forge — préparer une PHOTO avant la dérivation (R10c P1).

Deux gestes, tous deux en **PIL pur** (le runtime embarqué n'a pas numpy) :

  `delight`    retire le DÉGRADÉ D'ÉCLAIRAGE cuit dans la photo. L'éclairage
               est estimé par un flou gaussien CYCLIQUE très large sur la
               luminance (`pbr_service.cyclic`), puis divisé — et la division
               se fait en domaine LOGARITHMIQUE, où elle devient une
               soustraction : deux `Image.point` et un `ImageChops.add`, soit
               trois passes en C au lieu d'une boucle Python sur 4 M pixels.
               Le résultat est NORMALISÉ : le gain vaut exactement 1 là où
               l'éclairage estimé égale sa propre moyenne, donc l'image ne
               s'assombrit ni ne s'éclaircit globalement.

  `straighten` redresse une surface photographiée de biais : quatre coins
               cliqués -> `Image.transform(..., Image.PERSPECTIVE, coeffs)`,
               les huit coefficients résolus par une élimination de Gauss 8x8
               à pivot partiel, en stdlib. (Écrit en T2 de ce plan.)

POURQUOI CE MODULE EXISTE — LE DÉFAUT, MESURÉ. `pbr_service._roughness` a déjà
corrigé un défaut de la même famille : la rugosité valait `1 - luminance`,
donc recopiait l'éclairage cuit dans la photo (corrélation -0,76 à -0,99 avec
la luminance de la base color, médiane -0,90). Le micro-contraste l'a réparé
POUR LA RUGOSITÉ. La BASE COLOR, elle, porte toujours l'ombre : elle part
telle quelle dans le moteur, qui la ré-éclaire — l'ombre est donc comptée deux
fois, et la matière s'effondre dès qu'on change d'ambiance. `lowfreq_sd` est
la mesure qui le dit : l'écart-type de la luminance BASSE FRÉQUENCE, en
niveaux 0-255. C'est ce chiffre-là que l'écran affiche avant et après, et
c'est lui que le banc épingle.

RÉFÉRENCE relue le 03/09/2026 (R10c) : Substance 3D Sampler expose « Delight
(AI powered) » sans aucun paramètre, et sa passe « Image to Material »
l'inclut. Nous n'avons ni GPU ni modèle : l'estimation basse fréquence est la
version honnête et BORNÉE du même geste — elle ne devine rien, elle retire ce
qui varie lentement, et elle se mesure.

CONTRAT PILLOW, prouvé au banc et jamais supposé :
  * `ImageChops.add(a, b, scale, offset)` vaut `(a + b) / scale + offset`,
    écrêté à 0-255 ;
  * `Image.transform(size, Image.PERSPECTIVE, (a..h))` lit, pour le pixel de
    SORTIE (X, Y), la source en
    `((aX + bY + c) / (gX + hY + 1), (dX + eY + f) / (gX + hY + 1))` — les
    coefficients vont donc de la DESTINATION vers la SOURCE.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageFilter

from app.services import pbr_service as PBR

__all__ = ["LOG_FLOOR", "LOG_LUT", "EXP_LUT", "clamp8",
           "DELIGHT_RADIUS_FRAC", "DELIGHT_STRENGTH",
           "lowfreq", "lowfreq_sd", "delight"]

clamp8 = PBR.clamp8

# Plancher du logarithme, repris de `pbr_service._LOG_FLOOR` : sans lui,
# log(0) = -inf. 6/255 place le plancher deux niveaux au-dessus du noir JPEG
# typique, et donne une dynamique de 42:1 sur les 256 pas de la LUT.
LOG_FLOOR = 6.0
_K = -math.log(LOG_FLOOR / 255.0)          # ~3,749

# LOG_LUT : niveau 8 bits -> logarithme normalisé 0-255 (LOG_FLOOR -> 0,
# 255 -> 255). EXP_LUT est son inverse exact, à la quantification près (le banc
# mesure l'écart : 4 niveaux au pire, tout en haut de l'échelle, là où un pas
# de log couvre ~3,8 niveaux linéaires).
LOG_LUT = [clamp8(255.0 * (math.log(max(float(v), LOG_FLOOR) / 255.0) + _K) / _K)
           for v in range(256)]
EXP_LUT = [clamp8(255.0 * math.exp((u / 255.0) * _K - _K)) for u in range(256)]

# Rayon du flou d'estimation, en FRACTION du plus petit côté. 1/8 : à 2048 px
# cela fait sigma = 256 px. Plus petit, le flou commence à suivre le motif et
# le delighting mange le contraste de la matière ; plus grand, il ne suit plus
# la vignette d'un objectif grand-angle. C'est un réglage, borné, publié.
DELIGHT_RADIUS_FRAC = 0.125
DELIGHT_RADIUS_RANGE = (0.02, 0.40)
DELIGHT_STRENGTH = 1.0


def _f(raw, defaut: float, lo: float, hi: float) -> float:
    """Un nombre borné. Rien ne lève : l'entrée vient du réseau (doctrine
    `material_store` règle 2 — jamais de 500 sur un corps mal formé)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return defaut
    if v != v or v in (float("inf"), float("-inf")):
        return defaut
    return lo if v < lo else hi if v > hi else v


def lowfreq(img: Image.Image,
            radius_frac: float = DELIGHT_RADIUS_FRAC) -> Image.Image:
    """L'ÉCLAIRAGE estimé : la luminance floutée CYCLIQUEMENT, très large.

    Cyclique et pas fermé : un flou à bord fermé invente une valeur hors cadre
    et pose un liseré tout autour de l'estimation — donc un liseré INVERSE sur
    l'image délightée, exactement au bord que `make_seamless` va ensuite
    recoller. Le banc le prouve par la seule propriété qui distingue les deux :
    sur le tore, délighter et rouler commutent."""
    lum = PBR.luminance(img.convert("RGB"))
    r = max(2.0, _f(radius_frac, DELIGHT_RADIUS_FRAC, *DELIGHT_RADIUS_RANGE)
            * min(lum.size))
    return PBR.cyclic(lum, ImageFilter.GaussianBlur(r), r * 3.0 + 1.0)


def lowfreq_sd(img: Image.Image,
               radius_frac: float = DELIGHT_RADIUS_FRAC) -> float:
    """Écart-type de la luminance BASSE FRÉQUENCE, en niveaux 0-255.

    LA mesure du delighting : elle chiffre le dégradé d'éclairage et rien
    d'autre (le grain est parti dans le flou). Calculée par histogramme —
    aucune boucle par pixel, aucun numpy — comme `pbr_service.stats`."""
    h = lowfreq(img, radius_frac).histogram()
    n = sum(h) or 1
    m = sum(i * c for i, c in enumerate(h)) / n
    var = sum((i - m) ** 2 * c for i, c in enumerate(h)) / n
    return round(math.sqrt(var), 3)


def delight(img: Image.Image, strength=DELIGHT_STRENGTH,
            radius_frac: float = DELIGHT_RADIUS_FRAC) -> Image.Image:
    """Retire le dégradé d'éclairage. Rend une image RGB, toujours.

    Le calcul, en une ligne : `sortie = source x moyenne(E) / E`, avec `E`
    l'éclairage estimé. En logarithme cela devient
    `log(sortie) = log(source) + (moyenne(log E) - log E)`, soit UNE carte
    d'écart signée (centrée sur 128) ajoutée aux trois canaux — la teinte ne
    bouge donc pas, seul le niveau. `strength` interpole entre 0 (rien) et 1
    (division pleine).
    """
    rgb = img.convert("RGB")
    k = _f(strength, DELIGHT_STRENGTH, 0.0, 1.0)
    if k <= 0.0:
        return rgb
    lg = lowfreq(rgb, radius_frac).point(LOG_LUT)
    h = lg.histogram()
    n = sum(h) or 1
    pivot = sum(i * c for i, c in enumerate(h)) / n
    # écart d'éclairage SIGNÉ, centré sur 128 : au-dessus du pivot on assombrit,
    # en dessous on éclaircit, et le gain vaut exactement 1 AU pivot — c'est ce
    # qui rend la division « normalisée » et empêche l'image de dériver.
    ecart = lg.point([clamp8(128.0 - k * (v - pivot)) for v in range(256)])
    return Image.merge("RGB", tuple(
        ImageChops.add(canal.point(LOG_LUT), ecart, 1.0, -128).point(EXP_LUT)
        for canal in rgb.split()))
```

- [ ] **Step 5 : relancer le banc et le voir vert**

```
python tests/test_photo_prep.py
```

Attendu, sur `stdout` : sept lignes `✓`, la ligne de budget, puis
`OK — 7 assertions groupées vertes (photo_prep, delighting)`.
Les chiffres attendus, mesurés sur cette machine :
`écart-type basse fréquence ~16 -> ~2` (une baisse de 85 % ou plus),
`grain x1,1 à x1,6`, `delight ∘ roulement` sous 2 niveaux quand le témoin à
bord fermé dépasse 6, `delight 2048²` autour de 2 à 4 s.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/photo_prep.py backend/app/services/pbr_service.py backend/tests/test_photo_prep.py
git commit -m 'matieres P1 : le delighting retire le degrade et le chiffre

L'\''eclairage est estime par un flou gaussien CYCLIQUE large sur la luminance
puis divise en domaine logarithmique — trois passes PIL au lieu d'\''une boucle
Python sur 4 M pixels. La division est normalisee : le gain vaut 1 la ou
l'\''eclairage estime egale sa moyenne, donc l'\''image ne derive pas.

Mesure, sur une tuile haute frequence eclairee en diagonale plus vignette :
ecart-type de la luminance basse frequence 16 -> 2 niveaux (-87 %), le grain
local remonte (x1,3 : l'\''ombre ne l'\''ecrase plus), moins de 2 % de pixels
ecretes. Le bordage cyclique est prouve par la seule propriete qui le
distingue d'\''un bord ferme : sur le tore, delighter et rouler commutent a
moins de 2 niveaux, quand le temoin a bord ferme derive de plus de 6.

pbr_service reexporte cyclic/wrap/clamp8 : un seul proprietaire du bordage,
plutot qu'\''un nom souligne traversant un module ou une copie qui derivera.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 2 : P1 — le redressement de perspective, coefficients résolus en stdlib

**Files:**
- Modify: `backend/app/services/photo_prep.py` (ajouts en fin de fichier ; `__all__`)
- Test: `backend/tests/test_photo_prep.py` (nouvelle section, avant la ligne finale)

- [ ] **Step 1 : ajouter la section rouge au banc**

Dans `backend/tests/test_photo_prep.py`, insérer AVANT la ligne
`print(f"\nOK — {PASS} assertions groupées vertes (photo_prep, delighting)")` :

```python
# ══ 6 · les coefficients envoient bien chaque coin sur son coin ═════════════
def applique(c, X, Y):
    """Le contrat Pillow, écrit à la main : (X, Y) de SORTIE -> (x, y) SOURCE."""
    a, b, cc, d, e, f, g, h = c
    w = g * X + h * Y + 1.0
    return ((a * X + b * Y + cc) / w, (d * X + e * Y + f) / w)


COINS = [(0.0, 0.0), (255.0, 0.0), (255.0, 255.0), (0.0, 255.0)]
QUAD = [(38.0, 22.0), (301.0, 61.0), (274.0, 289.0), (17.0, 236.0)]
co = PP.perspective_coeffs(QUAD, COINS)
for (X, Y), (x, y) in zip(COINS, QUAD):
    gx, gy = applique(co, X, Y)
    assert abs(gx - x) < 1e-6 and abs(gy - y) < 1e-6, ((X, Y), (gx, gy), (x, y))
ok("perspective_coeffs : les quatre coins de destination retombent sur les "
   "quatre coins source à 1e-6")

# ══ 7 · aller-retour : une photo de biais redressée redonne la tuile ════════
plate = tuile(256, 256)
photo = plate.transform((320, 320), Image.PERSPECTIVE,
                        PP.perspective_coeffs(
                            [(0.0, 0.0), (255.0, 0.0), (255.0, 255.0),
                             (0.0, 255.0)], QUAD),
                        Image.BICUBIC)
photo = ecrire(photo, "biais.png")
droit = ecrire(PP.straighten(photo, QUAD, 256), "droit.png")
e_bon = ecart(droit, plate)
assert e_bon < 9.0, e_bon
# LE TÉMOIN : les mêmes quatre points, mais appariés dans le désordre. Sans
# `order_quad`, c'est exactement ce que produit un clic dans un autre sens.
tordu = photo.transform((256, 256), Image.PERSPECTIVE,
                        PP.perspective_coeffs(QUAD[1:] + QUAD[:1],
                                              [(0.0, 0.0), (255.0, 0.0),
                                               (255.0, 255.0), (0.0, 255.0)]),
                        Image.BICUBIC)
e_faux = ecart(tordu, plate)
assert e_faux > 3.0 * e_bon, (e_bon, e_faux)
ok(f"aller-retour : redressée à {e_bon:.2f} niveau de la tuile plate ; le "
   f"même quadrilatère mal apparié donne {e_faux:.2f}")

# ══ 8 · l'ordre des quatre coins ne dépend pas de l'ordre des clics ═════════
attendu = PP.order_quad(QUAD)
for k in range(4):
    assert PP.order_quad(QUAD[k:] + QUAD[:k]) == attendu, k
assert PP.order_quad(list(reversed(QUAD))) == attendu
assert attendu[0] == min(QUAD, key=lambda p: p[0] + p[1])
octets = [PP.straighten(photo, QUAD[k:] + QUAD[:k], 128).tobytes()
          for k in range(4)]
assert len(set(octets)) == 1
ok("order_quad : quatre rotations et l'ordre inverse donnent le MÊME "
   "quadrilatère, donc les mêmes octets redressés")

# ══ 9 · les refus se disent ════════════════════════════════════════════════
refus = {}
for cle, quad in (
        ("alignés", [(0, 0), (50, 50), (100, 100), (150, 150)]),
        ("confondus", [(0, 0), (0, 0), (200, 5), (200, 200)]),
        ("quatre", [(0, 0), (200, 0), (200, 200)])):
    try:
        PP.order_quad(quad)
        raise AssertionError(f"{cle} : aurait dû lever")
    except ValueError as e:
        refus[cle] = str(e)
        assert cle in str(e).lower(), (cle, str(e))
ok(f"refus nommés : {' | '.join(refus[k][:44] for k in refus)}")

# ══ 10 · budget ════════════════════════════════════════════════════════════
gros2 = plate.resize((2048, 2048), Image.LANCZOS)
t1 = time.perf_counter()
PP.straighten(gros2, [(12.0, 30.0), (2020.0, 5.0), (2040.0, 2030.0),
                      (60.0, 1990.0)], 2048)
dt2 = time.perf_counter() - t1
assert dt2 < 3.0, dt2
print(f"  straighten 2048² : {dt2:.2f} s (budget 3,0 s)")
```

Puis remplacer la dernière ligne par :

```python
print(f"\nOK — {PASS} assertions groupées vertes (photo_prep : delighting + "
      f"redressement)")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_photo_prep.py
```

Attendu : les 5 premières sections vertes, puis
`AttributeError: module 'app.services.photo_prep' has no attribute 'perspective_coeffs'`.

- [ ] **Step 3 : écrire le redressement**

Ajouter à la fin de `backend/app/services/photo_prep.py`, et compléter
`__all__` avec `"order_quad", "perspective_coeffs", "straighten"` :

```python
# ── redressement de perspective ─────────────────────────────────────────────
#
# QUATRE COINS, PAS UN ANGLE. Une photo de mur prise de biais n'est pas une
# rotation : c'est une homographie, et aucun réglage à un paramètre ne la
# défait. Les quatre coins cliqués sur la photo suffisent à la déterminer
# entièrement — huit inconnues, huit équations.
#
# LE PIÈGE DE PILLOW, ET IL EST SILENCIEUX. `Image.transform(...,
# Image.PERSPECTIVE, coeffs)` va de la DESTINATION vers la SOURCE : pour le
# pixel de sortie (X, Y) il lit la source en ((aX+bY+c)/(gX+hY+1),
# (dX+eY+f)/(gX+hY+1)). Résoudre « source -> destination », le sens naturel
# quand on pense « je redresse ma photo », donne une image retournée sur
# elle-même SANS AUCUNE ERREUR — juste une bouillie plausible. Le système est
# donc monté avec les coins de DESTINATION en entrée, et le banc l'épingle en
# réappliquant la formule à la main.

_EPS = 1e-12


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Résout a·x = b par élimination de Gauss AVEC PIVOT PARTIEL. stdlib pur.

    Le pivot partiel n'est pas un raffinement : sans lui, un quadrilatère dont
    un côté est vertical met un zéro sur la diagonale et la division explose.
    """
    n = len(b)
    m = [list(ligne) + [b[i]] for i, ligne in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < _EPS:
            raise ValueError(
                "redressement impossible : les quatre coins sont alignés ou "
                "confondus — le système n'a pas de solution unique")
        m[col], m[piv] = m[piv], m[col]
        inv = 1.0 / m[col][col]
        for j in range(col, n + 1):
            m[col][j] *= inv
        for r in range(n):
            if r == col:
                continue
            f = m[r][col]
            if f:
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


def perspective_coeffs(src, dst) -> tuple:
    """Les huit coefficients attendus par `Image.PERSPECTIVE`.

    `src` = les quatre coins dans l'image SOURCE, `dst` = les quatre coins
    correspondants dans l'image de SORTIE, tous deux dans le MÊME ordre.
    Pour chaque paire ((X, Y) sortie -> (x, y) source), la formule de Pillow
    donne deux équations linéaires en (a…h) :

        x·(gX + hY + 1) = aX + bY + c
        y·(gX + hY + 1) = dX + eY + f
    """
    lignes, second = [], []
    for (X, Y), (x, y) in zip(dst, src):
        lignes.append([X, Y, 1.0, 0.0, 0.0, 0.0, -X * x, -Y * x])
        second.append(x)
        lignes.append([0.0, 0.0, 0.0, X, Y, 1.0, -X * y, -Y * y])
        second.append(y)
    if len(second) != 8:
        raise ValueError("redressement : quatre coins sont attendus de chaque "
                         f"côté (reçu {len(second) // 2})")
    return tuple(_solve(lignes, second))


def _aire(pts) -> float:
    """Aire du quadrilatère par le lacet de Gauss, toujours positive."""
    s = 0.0
    for i in range(4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 4]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def order_quad(quad) -> list[tuple[float, float]]:
    """Les quatre coins remis dans l'ordre haut-gauche, haut-droit, bas-droit,
    bas-gauche — quel que soit l'ordre des clics.

    POURQUOI CE TRI EXISTE. Les coins arrivent d'un clic dans un canevas :
    rien ne garantit ni le sens ni le point de départ. Appariés dans le
    désordre, ils produisent une image RETOURNÉE, sans erreur et sans indice.
    On trie donc par angle autour du barycentre (avec y vers le bas, l'ordre
    croissant des angles est le sens horaire à l'écran), puis on fait tourner
    la liste pour commencer par le coin le plus haut à gauche.
    """
    pts = []
    for p in (quad or []):
        try:
            pts.append((float(p[0]), float(p[1])))
        except (TypeError, ValueError, IndexError):
            raise ValueError("redressement : chaque coin est une paire de "
                             "nombres [x, y]")
    if len(pts) != 4:
        raise ValueError(f"redressement : quatre coins sont attendus "
                         f"(reçu {len(pts)})")
    for i in range(4):
        for j in range(i + 1, 4):
            if math.dist(pts[i], pts[j]) < 1.0:
                raise ValueError("redressement : deux coins sont confondus "
                                 f"({pts[i]} et {pts[j]}) — cliquez quatre "
                                 "points distincts")
    cx = sum(p[0] for p in pts) / 4.0
    cy = sum(p[1] for p in pts) / 4.0
    pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    largeur = max(p[0] for p in pts) - min(p[0] for p in pts)
    hauteur = max(p[1] for p in pts) - min(p[1] for p in pts)
    if _aire(pts) < 0.05 * max(1.0, largeur * hauteur):
        raise ValueError("redressement : les quatre coins sont alignés ou "
                         "presque — la surface cliquée n'a pas d'aire")
    debut = min(range(4), key=lambda i: (pts[i][0] - cx) + (pts[i][1] - cy))
    return pts[debut:] + pts[:debut]


def straighten(img: Image.Image, quad, side: int,
               resample=Image.BICUBIC) -> Image.Image:
    """La surface délimitée par `quad` dans `img`, redressée en un carré de
    `side` px.

    CARRÉ, et c'est le contrat du dépôt, pas une facilité : une matière du
    Material Forge est carrée de bout en bout (`_mat_square` recadre déjà au
    centre, `RESOLUTIONS` ne liste que des carrés, le pavage suppose un
    rapport 1:1). Rendre ici un rectangle ferait entrer une exception que huit
    autres fonctions devraient porter.
    """
    coins = order_quad(quad)
    n = max(8, int(side))
    dst = [(0.0, 0.0), (n - 1.0, 0.0), (n - 1.0, n - 1.0), (0.0, n - 1.0)]
    return img.convert("RGB").transform(
        (n, n), Image.PERSPECTIVE, perspective_coeffs(coins, dst), resample)
```

- [ ] **Step 4 : relancer le banc et le voir vert**

```
python tests/test_photo_prep.py
```

Attendu : onze lignes `✓`, les deux lignes de budget, puis
`OK — 11 assertions groupées vertes (photo_prep : delighting + redressement)`.
Chiffres attendus : aller-retour sous 9 niveaux d'écart moyen, témoin mal
apparié au-dessus de 30, `straighten 2048²` autour de 0,3 à 1 s.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/photo_prep.py backend/tests/test_photo_prep.py
git commit -m 'matieres P1 : le redressement par quatre coins, resolu en stdlib

Image.transform(PERSPECTIVE) attend huit coefficients qui vont de la
DESTINATION vers la SOURCE. Les resoudre dans l'\''autre sens — celui auquel on
pense en disant je redresse ma photo — rend une image retournee sur elle-meme
SANS lever la moindre erreur : le systeme est donc monte avec les coins de
destination en entree, et le banc le reepingle en reappliquant la formule de
Pillow a la main, coin par coin, a 1e-6.

Elimination de Gauss 8x8 a pivot partiel, stdlib pure : sans le pivot, un cote
vertical met un zero sur la diagonale. order_quad trie par angle autour du
barycentre puis demarre au coin haut-gauche, donc quatre rotations et l'\''ordre
inverse donnent les MEMES octets redresses (mesure). Trois refus nommes :
coins alignes, coins confondus, nombre de coins.

Mesure : aller-retour d'\''une tuile passee de biais puis redressee, ecart moyen
sous 9 niveaux ; le meme quadrilatere mal apparie depasse 30. 2048 carre
redresse sous 3 s.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---
### Task 3 : P1 — le câblage : la préparation entre dans le job, la fiche et le LISEZMOI

**Files:**
- Modify: `backend/app/services/material_store.py:202-217` (après `_DERIVE_SPEC` : `clean_prep`, `prep_note`), `:45-64` (`__all__`), `:731-812` (`normalize_material`, bloc `source`), `:1340-1360` (`_readme`)
- Modify: `backend/app/api/routes.py:7181-7193` (helper `_mat_prepare` juste après `_mat_square`), `:7302-7347` (`generate_material`), `:7357-7420` (`_run_material_job`), et une route neuve avant `@router.post("/materials/generate")`
- Modify: `backend/tests/test_materials_api.py:548-549` (la fiche `source` gagne `prep`)
- Test: `backend/tests/test_materials_prep_api.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_materials_prep_api.py` :

```python
# -*- coding: utf-8 -*-
"""Material Forge P1 — la préparation d'une photo TRAVERSE l'application :
route d'aperçu, job de génération, fiche, material.json, LISEZMOI.

BANC-MIROIR : la base color est relue DEPUIS LE DISQUE de la matière, et le
LISEZMOI depuis l'archive ZIP réellement écrite.

Run (depuis backend/) : python tests/test_materials_prep_api.py
"""
import asyncio
import base64
import io
import json
import math
import os
import pathlib
import sys
import tempfile
import types
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageChops                              # noqa: E402
from httpx import ASGITransport, AsyncClient                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [{"url": "http://fal.test/out.png"}], "seed": 7}


_stub.subscribe_async = _sub
sys.modules["fal_client"] = _stub

from app.config import settings                                # noqa: E402
from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import photo_prep as PP                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


QUAD = [[38, 22], [301, 61], [274, 289], [17, 236]]


def photo_de_biais(nom="mur.png"):
    """Une tuile haute fréquence, éclairée en diagonale, puis vue de biais —
    et déposée dans la Bibliothèque comme le ferait un import."""
    w = h = 256
    plate = Image.new("RGB", (w, h))
    px = plate.load()
    for y in range(h):
        for x in range(w):
            v = 128.0
            for kx, ky, amp in ((5, 4, 40.0), (11, 7, 22.0)):
                v += amp * math.sin(2 * math.pi * kx * x / w) \
                         * math.cos(2 * math.pi * ky * y / h)
            v = max(6.0, min(249.0, v))
            px[x, y] = (int(v), int(v * 0.84 + 14), int(v * 0.62 + 32))
    ramp = Image.new("L", (w, h))
    d = ramp.load()
    for y in range(h):
        for x in range(w):
            d[x, y] = int(round(255.0 * (0.35 + 0.65 *
                                         (x / (w - 1) + y / (h - 1)) / 2.0)))
    lit = Image.merge("RGB", tuple(ImageChops.multiply(c, ramp)
                                   for c in plate.split()))
    biais = lit.transform((320, 320), Image.PERSPECTIVE,
                          PP.perspective_coeffs(
                              [(0.0, 0.0), (255.0, 0.0), (255.0, 255.0),
                               (0.0, 255.0)],
                              [tuple(p) for p in QUAD]), Image.BICUBIC)
    p = settings.images_path / nom
    biais.save(p, format="PNG")
    return nom


async def attendre(c, jid):
    for _ in range(400):
        st = (await c.get(f"/api/materials/jobs/{jid}")).json()
        if st["status"] in ("done", "failed"):
            return st
        await asyncio.sleep(0.05)
    raise AssertionError("job jamais terminé")


async def main():
    global PASS
    lib = photo_de_biais()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=120) as c:

        # ══ 1 · l'aperçu ne crée rien et rend les deux chiffres ═════════════
        avant = len(MS.list_materials())
        r = await c.post("/api/materials/prep/preview",
                         json={"filename": lib, "prep": {"quad": QUAD,
                                                         "delight": 1.0}})
        assert r.status_code == 200, r.text
        d = r.json()
        m = d["mesure"]
        assert m["lowfreq_sd_before"] > 8.0, m
        assert m["lowfreq_sd_after"] < 0.30 * m["lowfreq_sd_before"], m
        assert m["baisse_pct"] > 70.0, m
        assert d["apercu"]["png"].startswith("data:image/png;base64,")
        brut = base64.b64decode(d["apercu"]["png"].split(",", 1)[1])
        with Image.open(io.BytesIO(brut)) as im:
            assert im.size == (d["apercu"]["w"], d["apercu"]["h"])
            assert im.size[0] == im.size[1] <= 512, im.size
        assert len(MS.list_materials()) == avant
        ok(f"aperçu : {m['lowfreq_sd_before']} -> {m['lowfreq_sd_after']} "
           f"({m['baisse_pct']:.0f} % de moins), PNG carré ≤ 512, "
           f"aucune matière créée")

        # ══ 2 · les refus, avant toute dépense ══════════════════════════════
        for prep, mot in (({"quad": [[0, 0], [50, 50], [100, 100], [150, 150]],
                            "delight": 1.0}, "align"),
                          ({"quad": [[9, 9], [9, 9], [200, 5], [200, 200]],
                            "delight": 1.0}, "confondus")):
            r = await c.post("/api/materials/prep/preview",
                             json={"filename": lib, "prep": prep})
            assert r.status_code == 400, (r.status_code, r.text)
            assert mot in r.json()["detail"].lower(), r.text
            r = await c.post("/api/materials/generate",
                             json={"filename": lib, "prep": prep, "res": 512})
            assert r.status_code == 400, (r.status_code, r.text)
        ok("quadrilatère dégénéré : 400 parlant sur l'aperçu ET sur la "
           "génération — refusé AVANT de lancer le job")

        # ══ 3 · le job applique la préparation, la fiche la garde ═══════════
        r = await c.post("/api/materials/generate",
                         json={"filename": lib, "res": 512, "seamless": True,
                               "name": "Mur redressé",
                               "prep": {"quad": QUAD, "delight": 1.0}})
        assert r.status_code == 200, r.text
        st = await attendre(c, r.json()["job_id"])
        assert st["status"] == "done", st
        mat = st["material"]
        prep = mat["source"]["prep"]
        assert prep["quad"] == QUAD, prep
        assert prep["delight"] == 1.0
        assert prep["lowfreq_sd_after"] < 0.30 * prep["lowfreq_sd_before"], prep
        ok(f"job : source.prep gardé dans la fiche "
           f"({prep['lowfreq_sd_before']} -> {prep['lowfreq_sd_after']})")

        # ══ 4 · le PNG SUR LE DISQUE porte la correction ════════════════════
        p = MS.map_path(mat["id"], "basecolor")
        assert p.is_file()
        with Image.open(p) as im:
            base = im.convert("RGB")
            assert base.size == (512, 512), base.size
            sd = PP.lowfreq_sd(base)
        assert sd < 6.0, sd
        ok(f"basecolor relue sur le disque : écart-type basse fréquence "
           f"{sd} (< 6,0) — la correction est DANS le fichier livré")

        # ══ 5 · l'archive le dit ════════════════════════════════════════════
        r = await c.get(f"/api/materials/{mat['id']}/export?format=zip")
        assert r.status_code == 200, r.text
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            lisez = z.read("LISEZMOI.txt").decode("utf-8")
            mj = json.loads(z.read("material.json").decode("utf-8"))
        assert "Photo préparée" in lisez, lisez[:600]
        assert "quatre coins" in lisez and "basse fréquence" in lisez
        assert mj["source"]["prep"]["quad"] == QUAD, mj["source"]
        ok("archive : LISEZMOI et material.json disent ce qui a été fait à "
           "la photo")

        # ══ 6 · sans prep, rien ne change ═══════════════════════════════════
        r = await c.post("/api/materials/generate",
                         json={"filename": lib, "res": 512, "name": "Brut"})
        st2 = await attendre(c, r.json()["job_id"])
        assert st2["status"] == "done", st2
        assert st2["material"]["source"]["prep"] is None
        r = await c.get(f"/api/materials/{st2['material']['id']}/export?format=zip")
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert "Photo préparée" not in z.read("LISEZMOI.txt").decode("utf-8")
        ok("sans prep : source.prep vaut None et le LISEZMOI n'invente rien")

        # ══ 7 · une entrée pourrie ne fait jamais tomber la route ═══════════
        for mauvais in ({"quad": "oui"}, {"quad": [[1, 2]]}, {"delight": "x"},
                        {"delight": 12}, {"quad": [[1, "a"], [2, 3], [4, 5],
                                                   [6, 7]]}, [], "prep", 7):
            r = await c.post("/api/materials/prep/preview",
                             json={"filename": lib, "prep": mauvais})
            assert r.status_code == 200, (mauvais, r.status_code, r.text)
        assert MS.clean_prep({"delight": 0}) is None
        assert MS.clean_prep(None) is None
        assert MS.prep_note(None) == "" and MS.prep_note({}) == ""
        ok("entrée pourrie : jamais de 500 — le bloc prep tombe à ce qu'il "
           "sait lire, et un bloc vide vaut None")

    print(f"\nOK — {PASS} assertions groupées vertes (préparation de photo, "
          f"bout en bout)")


asyncio.run(main())
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_materials_prep_api.py
```

Attendu : `AttributeError: module 'app.services.material_store' has no attribute 'clean_prep'`
(l'import du banc échoue avant la première requête).

- [ ] **Step 3 : le bloc `prep` dans `material_store`**

Dans `backend/app/services/material_store.py`, juste après la fermeture de
`_DERIVE_SPEC` (ligne 217, avant le commentaire `# Préréglages de matière`),
insérer :

```python
# ── ce qu'on a FAIT à la photo avant de la dériver (R10c P1) ────────────────
#
# Ce bloc voyage avec la matière : meta.json, material.json de l'archive,
# LISEZMOI. Sans lui, une base color délightée serait indiscernable d'une base
# color naturellement plate — et personne, six mois plus tard, ne saurait si
# l'ombre a été retirée une fois, zéro fois, ou deux.
#
# Règle 2 du module (« aucune entrée invalide ne casse quoi que ce soit ») :
# rien ne lève ici. Un `quad` mal formé est simplement ABSENT du bloc rendu, et
# l'écran le voit — c'est un refus visible, pas une exception.


def clean_prep(raw) -> dict | None:
    """Bloc `prep` normalisé, ou `None` s'il n'y a rien à dire."""
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    d = _coerce_float(raw.get("delight"), 0.0, 0.0, 1.0)
    if d > 0.0:
        out["delight"] = round(d, 3)
        out["delight_radius"] = round(
            _coerce_float(raw.get("delight_radius"), 0.125, 0.02, 0.40), 3)
    quad = raw.get("quad")
    if isinstance(quad, (list, tuple)) and len(quad) == 4:
        pts = []
        for p in quad:
            try:
                pts.append([round(float(p[0]), 2), round(float(p[1]), 2)])
            except (TypeError, ValueError, IndexError, KeyError):
                pts = []
                break
        if len(pts) == 4:
            out["quad"] = pts
    for k in ("lowfreq_sd_before", "lowfreq_sd_after"):
        try:
            out[k] = round(float(raw[k]), 3)
        except (KeyError, TypeError, ValueError):
            pass
    return out or None


def prep_note(prep: dict | None) -> str:
    """Une phrase française qui dit ce qui a été fait à la photo — vide si
    rien ne l'a été. C'est elle que porte le LISEZMOI de l'archive."""
    if not isinstance(prep, dict) or not prep:
        return ""
    faits = []
    if prep.get("quad"):
        faits.append("redressée par quatre coins (transformation perspective)")
    if prep.get("delight"):
        faits.append(f"éclairage retiré à {prep['delight']:.2f}")
    if not faits:
        return ""
    note = "Photo préparée : " + ", ".join(faits) + "."
    av, ap = prep.get("lowfreq_sd_before"), prep.get("lowfreq_sd_after")
    if av is not None and ap is not None:
        baisse = (100.0 * (1.0 - ap / av)) if av > 1e-6 else 0.0
        note += (f" Écart-type de la luminance basse fréquence : {av} -> {ap} "
                 f"niveaux ({baisse:.0f} % de moins).")
    return note
```

Ajouter `"clean_prep", "prep_note",` à `__all__` (ligne 63, après
`"export_filename", "naming_map", "env_jpeg",`).

Dans `normalize_material`, remplacer la ligne du bloc `source` du dictionnaire
rendu (ligne 796) :

```python
        "source": {"kind": kind, "model": model, "filename": filename},
```

par :

```python
        "source": {"kind": kind, "model": model, "filename": filename,
                   "prep": clean_prep(src.get("prep"))},
```

Dans `_readme`, remplacer :

```python
        "  " + RENDER_NOTE.replace(". ", ".\r\n  "),
        "",
        "Maps incluses :",
    ]
```

par :

```python
        "  " + RENDER_NOTE.replace(". ", ".\r\n  "),
    ]
    note_photo = prep_note((mat.get("source") or {}).get("prep"))
    if note_photo:
        lines += ["", note_photo]
    lines += [
        "",
        "Maps incluses :",
    ]
```

- [ ] **Step 4 : le helper de préparation et la route d'aperçu**

Dans `backend/app/api/routes.py`, juste après `_mat_square` (fin ligne 7193),
insérer :

```python
def _mat_prepare(img: "PILImage.Image", res: int, prep: dict | None):
    """Redressement, PUIS delighting, PUIS carré — et le bloc `prep` complété
    par la mesure avant/après.

    L'ORDRE N'EST PAS LIBRE, et c'est la seule chose à retenir ici. Redresser
    d'abord : la perspective étire aussi le dégradé d'éclairage, donc estimer
    l'éclairage avant le redressement revient à l'estimer dans un espace qui
    n'est pas celui de la surface — le flou serait anisotrope là où la photo
    fuit. Le carré ensuite : `straighten` rend déjà un carré, `_mat_square`
    n'a donc plus rien à recadrer et se contente de la mise à la résolution.

    Lève `ValueError` sur un quadrilatère dégénéré ; les deux appelants la
    traduisent en 400 — et le font AVANT de lancer quoi que ce soit."""
    from app.services import material_store as MS
    from app.services import photo_prep as PP
    p = MS.clean_prep(prep)
    rgb = img.convert("RGB")
    if p and p.get("quad"):
        rgb = PP.straighten(rgb, p["quad"], res)
    fait = dict(p or {})
    if p and p.get("delight"):
        rayon = p.get("delight_radius")
        fait["lowfreq_sd_before"] = PP.lowfreq_sd(rgb, rayon)
        rgb = PP.delight(rgb, p["delight"], rayon)
        fait["lowfreq_sd_after"] = PP.lowfreq_sd(rgb, rayon)
    return _mat_square(rgb, res), MS.clean_prep(fait)
```

Juste avant `@router.post("/materials/generate")` (ligne 7302), insérer :

```python
@router.post("/materials/prep/preview")
async def material_prep_preview(body: dict):
    """Prépare une photo SANS rien créer, et rend les deux chiffres.

    Route de LECTURE malgré son verbe : aucun fichier écrit, aucune matière
    créée, aucun crédit dépensé. C'est ce qui permet à l'écran de montrer
    l'avant et l'après — et surtout de REFUSER un quadrilatère dégénéré —
    avant qu'une génération soit lancée. `prep` suit `material_store.clean_prep`
    (une entrée illisible retombe sur « rien à faire », jamais sur une 500) ;
    seul un quadrilatère bien FORMÉ mais dégénéré fait un 400, parce que là
    c'est le geste de l'utilisateur qui est en cause et qu'il doit le savoir.
    """
    import base64
    import io
    from app.services import material_store as MS
    body = body if isinstance(body, dict) else {}
    src = _mat_library_path(body.get("filename"))
    res = MS.clean_preview_res(body.get("res"), 512)
    prep = MS.clean_prep(body.get("prep"))

    def _travail():
        with PILImage.open(src) as im:
            img, fait = _mat_prepare(im.copy(), res, prep)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return img, fait, buf.getvalue()

    try:
        img, fait, png = await asyncio.to_thread(_travail)
    except ValueError as e:
        raise HTTPException(400, str(e))
    av = (fait or {}).get("lowfreq_sd_before")
    ap = (fait or {}).get("lowfreq_sd_after")
    baisse = (100.0 * (1.0 - ap / av)) if (av and ap and av > 1e-6) else 0.0
    return {
        "prep": fait,
        "mesure": {"lowfreq_sd_before": av, "lowfreq_sd_after": ap,
                   "baisse_pct": round(baisse, 1)},
        "apercu": {"w": img.size[0], "h": img.size[1],
                   "png": "data:image/png;base64,"
                          + base64.b64encode(png).decode("ascii")},
        "note": MS.prep_note(fait),
    }
```

`io` et `base64` sont importés **dans la fonction**, et non en tête de
`routes.py` : six fonctions de ce fichier font déjà exactement cela (`import
io` y apparaît six fois, jamais au niveau module). On suit la maison plutôt
que d'ouvrir un import global pour deux routes.

Dans `generate_material`, après la ligne `enhance = bool(body.get("enhance"))`
(ligne 7318), insérer :

```python
    prep = MS.clean_prep(body.get("prep"))
    if prep and prep.get("quad"):
        # fail fast, comme `_mat_library_path` juste en dessous : un
        # quadrilatère dégénéré doit dire non MAINTENANT, pas au fond d'un job
        # dont l'utilisateur regarde la barre avancer.
        from app.services import photo_prep as PP
        try:
            PP.order_quad(prep["quad"])
        except ValueError as e:
            raise HTTPException(400, str(e))
```

et ajouter `"prep": prep,` au dictionnaire `spec` (ligne 7321, dans le premier
bloc `spec = {...}`).

Dans `_run_material_job`, remplacer :

```python
        upd(step="Préparation", pct=40)
        with PILImage.open(src) as im:
            base = await asyncio.to_thread(_mat_square, im.copy(), res)
```

par :

```python
        upd(step="Préparation", pct=40)
        with PILImage.open(src) as im:
            base, fait = await asyncio.to_thread(_mat_prepare, im.copy(), res,
                                                 spec.get("prep"))
        spec["prep"] = fait
```

et, dans l'appel à `MS.create_material`, remplacer :

```python
            source={"kind": spec["kind"], "model": spec.get("model"),
                    "filename": spec.get("filename")})
```

par :

```python
            source={"kind": spec["kind"], "model": spec.get("model"),
                    "filename": spec.get("filename"),
                    "prep": spec.get("prep")})
```

- [ ] **Step 5 : réparer l'assertion du banc voisin**

`backend/tests/test_materials_api.py:548-549` épingle la fiche `source` en
égalité stricte ; elle gagne une clé. Remplacer :

```python
        assert libmat["source"] == {"kind": "library", "model": None,
                                    "filename": lib}, libmat["source"]
```

par :

```python
        assert libmat["source"] == {"kind": "library", "model": None,
                                    "filename": lib, "prep": None}, \
            libmat["source"]
```

- [ ] **Step 6 : relancer les deux bancs et les voir verts**

```
python tests/test_materials_prep_api.py
python tests/test_materials_api.py
```

Attendu : `OK — 7 assertions groupées vertes (préparation de photo, bout en
bout)` pour le premier, et la ligne `OK — Material Forge: CRUD, mid strict …`
inchangée pour le second.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/material_store.py backend/app/api/routes.py backend/tests/test_materials_prep_api.py backend/tests/test_materials_api.py
git commit -m 'matieres P1 : la preparation traverse le job, la fiche et l archive

Une route d'\''apercu qui n'\''ecrit rien (POST /materials/prep/preview) rend les
deux chiffres et un PNG carre de 512 px : l'\''ecran montre l'\''avant et l'\''apres
et REFUSE un quadrilatere degenere avant qu'\''une generation soit lancee. Le
job applique redressement puis delighting puis mise au carre — dans cet ordre,
parce que la perspective etire aussi le degrade et qu'\''estimer l'\''eclairage
avant le redressement l'\''estimerait dans un espace qui n'\''est pas celui de la
surface.

Le bloc source.prep voyage ensuite partout : meta.json, material.json de
l'\''archive, et une phrase du LISEZMOI qui porte la mesure. Sans lui, une base
color delightee serait indiscernable d'\''une base color naturellement plate.

Mesure du banc, sur la base color RELUE DEPUIS LE DISQUE de la matiere :
ecart-type de la luminance basse frequence sous 6 niveaux apres un depart a
plus de 16 ; sans prep, la fiche vaut None et le LISEZMOI n'\''invente rien.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 4 : P1 — l'écran : quatre coins au clic, l'éclairage retiré, le chiffre visible

**Files:**
- Modify: `frontend/materialforge/index.html:62-72` (après le bloc `refPicked` / `libBox`)
- Modify: `frontend/materialforge/materialforge.js:569-592` (`setRef`), `:702-736` (`generate`), `:3272` (`wire`)
- Modify: `frontend/materialforge/materialforge.css` (fin de fichier)
- Test: `backend/tests/test_materialforge_ecran.py`

- [ ] **Step 1 : écrire le banc-miroir qui échoue**

Créer `backend/tests/test_materialforge_ecran.py` :

```python
# -*- coding: utf-8 -*-
"""Écran /materialforge/ — bancs-miroirs de texte (T4 et T8 du plan
2026-09-03-plan-matieres).

Patron de test_etabli_canevas.py : le frontend est du vanilla servi en
statique, donc on le LIT comme du texte et on y épingle des marqueurs. Les
assertions NÉGATIVES portent sur le fichier PRIVÉ DE SES COMMENTAIRES — ce
dépôt commente en expliquant ce qu'il écarte, et un `assert "x" not in js`
posé sur le fichier entier serait satisfait par la phrase même qui jure de
ne pas s'en servir.

LA MOITIÉ QUI COMPTE : les clés du contrat HTTP sont épinglées DES DEUX
CÔTÉS — dans `routes.py` et dans `materialforge.js`. Renommer une clé d'un
seul côté fait rougir ce banc, ce qu'aucune lecture d'un seul fichier ne
saurait faire.

Run (depuis backend/) : python tests/test_materialforge_ecran.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend" / "materialforge"
ROUTES = RACINE / "backend" / "app" / "api" / "routes.py"

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def lire(nom):
    return (FRONT / nom).read_text(encoding="utf-8")


def code(nom):
    """Le fichier SANS ses blocs /* … */ — réservé aux assertions négatives."""
    return re.sub(r"/\*.*?\*/", "", lire(nom), flags=re.S)


HTML = lire("index.html")
JS = lire("materialforge.js")
JS_CODE = code("materialforge.js")
CSS = lire("materialforge.css")
PY = ROUTES.read_text(encoding="utf-8")

# ══ 1 · le panneau Photo existe et porte ses commandes ══════════════════════
for ident in ("grpPhoto", "phCanvas", "phDelight", "phStrength", "phPreview",
              "phReset", "phOut", "phMeasure"):
    assert f'id="{ident}"' in HTML, ident
assert HTML.count('id="grpPhoto"') == 1
ok("index.html : panneau Photo — canevas des quatre coins, délighter, "
   "intensité, aperçu, remise à zéro, image de sortie, mesure")

# ══ 2 · le contrat HTTP est épinglé DES DEUX CÔTÉS ══════════════════════════
assert '"/materials/prep/preview"' in PY, "la route a changé de chemin"
assert "/materials/prep/preview" in JS_CODE, "l'écran n'appelle plus la route"
for cle in ("lowfreq_sd_before", "lowfreq_sd_after", "baisse_pct"):
    assert cle in PY, cle
    assert cle in JS_CODE, f"{cle} absent du JS — contrat rompu d'un côté"
ok("contrat d'aperçu épinglé des deux côtés : chemin + trois clés de mesure")

# ══ 3 · la génération EMPORTE la préparation ════════════════════════════════
corps = JS_CODE.split("async function generate()", 1)[1].split("\n}\n", 1)[0]
assert "prep" in corps, "generate() n'envoie pas prep"
assert "photo.quad" in corps or "prepBody" in corps, corps[:400]
ok("generate() envoie le bloc prep — la matière naît de la photo préparée")

# ══ 4 · quatre coins, pas trois ni cinq ═════════════════════════════════════
assert re.search(r"quad\.length\s*[<>=!]{1,3}\s*4", JS_CODE), \
    "aucune garde sur le nombre de coins"
assert "phCanvas" in JS_CODE and "getBoundingClientRect" in JS_CODE
ok("le canevas borne la saisie à quatre coins et convertit les clics en "
   "coordonnées d'image")

# ══ 5 · le style existe ════════════════════════════════════════════════════
for regle in ("#phCanvas", "#phOut"):
    assert regle in CSS, regle
ok("materialforge.css : le canevas et l'aperçu ont leur règle")

print(f"\nOK — {PASS} assertions groupées vertes (écran Material Forge, "
      f"panneau Photo)")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_materialforge_ecran.py
```

Attendu : `AssertionError: grpPhoto`.

- [ ] **Step 3 : le balisage**

Dans `frontend/materialforge/index.html`, juste après la fermeture du bloc
`<div class="libbox hidden" id="libBox">…</div>` (ligne 72), insérer :

```html
      <details class="grp" id="grpPhoto">
        <summary><i class="chev"></i><span class="grp-t">Photo</span>
          <b class="mono" id="phMeasure">—</b></summary>
        <div class="grp-b">
          <p class="hint">Une photo de surface n'est pas une texture : elle est
            prise de biais et l'éclairage y est cuit. Clique les quatre coins
            de la surface, puis retire l'éclairage. Les deux corrections sont
            locales et gratuites.</p>
          <canvas id="phCanvas" width="320" height="320"></canvas>
          <div class="row">
            <button class="btn ghost sm" id="phReset" type="button"
                    title="Effacer les quatre coins">↺ Coins</button>
            <label class="check"><input type="checkbox" id="phDelight" checked>
              Retirer l'éclairage</label>
          </div>
          <label class="mini">Intensité
            <input type="range" id="phStrength" min="0" max="1" step="0.05"
                   value="1"></label>
          <button class="btn sm wide" id="phPreview" type="button">
            👁 Aperçu de la préparation</button>
          <img id="phOut" alt="aperçu de la préparation" class="hidden">
        </div>
      </details>
```

- [ ] **Step 4 : le comportement**

Dans `frontend/materialforge/materialforge.js`, ajouter juste avant
`function wire()` (ligne 3272) :

```js
/* ── le panneau Photo (P1) ──────────────────────────────────────────────────
   Quatre coins cliqués sur la référence, l'éclairage retiré, et LES DEUX
   CHIFFRES. Le canevas est en pixels d'AFFICHAGE, la route en pixels
   d'IMAGE : la conversion se fait ici, une fois, avec le rapport naturel de
   l'image chargée — un clic converti côté serveur obligerait à lui envoyer la
   taille du canevas, c'est-à-dire à lui faire confiance sur un chiffre qu'il
   n'a aucun moyen de vérifier. */
const photo = { img: null, quad: [], out: null };

function photoDraw() {
  const cv = $("#phCanvas");
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, cv.width, cv.height);
  if (!photo.img) {
    ctx.fillStyle = "#12151a";
    ctx.fillRect(0, 0, cv.width, cv.height);
    return;
  }
  const s = Math.min(cv.width / photo.img.naturalWidth,
                     cv.height / photo.img.naturalHeight);
  const w = photo.img.naturalWidth * s;
  const h = photo.img.naturalHeight * s;
  photo.fit = { s, ox: (cv.width - w) / 2, oy: (cv.height - h) / 2 };
  ctx.drawImage(photo.img, photo.fit.ox, photo.fit.oy, w, h);
  ctx.strokeStyle = "#4cc9f0";
  ctx.fillStyle = "#4cc9f0";
  ctx.lineWidth = 1.5;
  photo.quad.forEach((p, i) => {
    const x = photo.fit.ox + p[0] * s;
    const y = photo.fit.oy + p[1] * s;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillText(String(i + 1), x + 7, y - 7);
  });
  if (photo.quad.length === 4) {
    ctx.beginPath();
    photo.quad.forEach((p, i) => {
      const x = photo.fit.ox + p[0] * s;
      const y = photo.fit.oy + p[1] * s;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  }
}

function photoClick(ev) {
  if (!photo.img || !photo.fit) return;
  const r = $("#phCanvas").getBoundingClientRect();
  const cv = $("#phCanvas");
  const x = ((ev.clientX - r.left) * (cv.width / r.width) - photo.fit.ox)
    / photo.fit.s;
  const y = ((ev.clientY - r.top) * (cv.height / r.height) - photo.fit.oy)
    / photo.fit.s;
  if (x < 0 || y < 0 || x > photo.img.naturalWidth
      || y > photo.img.naturalHeight) return;
  if (photo.quad.length >= 4) photo.quad = [];
  photo.quad.push([Math.round(x * 100) / 100, Math.round(y * 100) / 100]);
  photoDraw();
}

function photoPrep() {
  /* Le bloc envoyé au serveur. `null` quand il n'y a rien à faire : la route
     et la fiche disent alors « aucune préparation », ce qui est vrai. */
  const d = $("#phDelight").checked ? num($("#phStrength").value, 1) : 0;
  const q = photo.quad.length === 4 ? photo.quad : null;
  if (!d && !q) return null;
  const out = {};
  if (d) out.delight = d;
  if (q) out.quad = q;
  return out;
}

async function photoPreview() {
  const fn = state.ref && state.ref.filename;
  if (!fn) { toast("Choisis d'abord une image de référence.", true); return; }
  const prep = photoPrep();
  if (!prep) { toast("Rien à préparer : coche « Retirer l'éclairage » ou "
                     + "clique les quatre coins.", true); return; }
  $("#phPreview").disabled = true;
  try {
    const d = await api.post("/materials/prep/preview",
                             { filename: fn, prep });
    $("#phOut").src = d.apercu.png;
    $("#phOut").classList.remove("hidden");
    const m = d.mesure || {};
    $("#phMeasure").textContent = (m.lowfreq_sd_before == null)
      ? "redressée"
      : `${m.lowfreq_sd_before} → ${m.lowfreq_sd_after} (${
          Math.round(m.baisse_pct)} % de moins)`;
    $("#phMeasure").title = d.note || "";
  } catch (e) {
    apiFail(e, "préparation de la photo");
  } finally {
    $("#phPreview").disabled = false;
  }
}
```

Dans `setRef(fn)` (ligne 569), après la ligne qui pose la vignette de
référence, ajouter :

```js
  /* Nouvelle référence : les coins de l'ancienne n'ont plus de sens. */
  photo.quad = [];
  photo.out = null;
  $("#phOut").classList.add("hidden");
  $("#phMeasure").textContent = "—";
  if (fn) {
    photo.img = new Image();
    photo.img.onload = photoDraw;
    photo.img.src = `/api/images/${encodeURIComponent(fn)}`;
  } else {
    photo.img = null;
    photoDraw();
  }
```

Dans `generate()` (ligne 702), ajouter au corps envoyé à
`/materials/generate` la clé :

```js
    prep: photoPrep(),
```

Dans `wire()`, ajouter :

```js
  $("#phCanvas").addEventListener("click", photoClick);
  $("#phReset").addEventListener("click", () => { photo.quad = []; photoDraw(); });
  $("#phPreview").addEventListener("click", photoPreview);
  $("#phDelight").addEventListener("change", () => {
    $("#phStrength").disabled = !$("#phDelight").checked;
  });
```

- [ ] **Step 5 : le style**

Ajouter à la fin de `frontend/materialforge/materialforge.css` :

```css
/* ── panneau Photo (P1) ──────────────────────────────────────────────────── */
#phCanvas {
  width: 100%; height: auto; aspect-ratio: 1 / 1;
  border: 1px solid var(--line, #222831); border-radius: 6px;
  background: #12151a; cursor: crosshair; display: block; margin: 6px 0;
}
#phOut {
  width: 100%; height: auto; display: block; margin-top: 8px;
  border: 1px solid var(--line, #222831); border-radius: 6px;
}
#grpPhoto .row { display: flex; gap: 8px; align-items: center; }
```

- [ ] **Step 6 : relancer le banc et le voir vert**

```
python tests/test_materialforge_ecran.py
```

Attendu : cinq lignes `✓` puis
`OK — 5 assertions groupées vertes (écran Material Forge, panneau Photo)`.

- [ ] **Step 7 : vérifier à l'écran (le navigateur voit, Python écrit)**

Ouvrir `http://127.0.0.1:8765/materialforge/`, choisir une photo de la
Bibliothèque, cliquer quatre coins, cliquer « Aperçu de la préparation ».
Attendu : le quadrilatère se ferme en cyan, l'aperçu carré s'affiche, et le
badge du panneau porte `<avant> → <après> (NN % de moins)`.

- [ ] **Step 8 : commit**

```bash
git add frontend/materialforge/index.html frontend/materialforge/materialforge.js frontend/materialforge/materialforge.css backend/tests/test_materialforge_ecran.py
git commit -m 'matieres P1 : le panneau Photo, quatre coins et le chiffre visible

Le canevas est en pixels d'\''AFFICHAGE, la route en pixels d'\''IMAGE : la
conversion se fait dans la page, une fois, avec le rapport naturel de l'\''image
chargee. La faire cote serveur obligerait a lui envoyer la taille du canevas,
c'\''est-a-dire a lui faire confiance sur un chiffre qu'\''il ne peut pas
verifier.

Le banc-miroir lit les fichiers du frontend comme du texte et epingle les
cles du contrat HTTP DES DEUX COTES — routes.py et materialforge.js. Renommer
lowfreq_sd_after d'\''un seul cote fait rougir, ce qu'\''aucune lecture d'\''un
seul fichier ne saurait faire. Les assertions negatives portent sur le fichier
prive de ses blocs de commentaires : ce depot commente en expliquant ce qu'\''il
ecarte, et un not-in naif serait satisfait par la phrase qui jure de ne pas
s'\''en servir.

Coût de patch : ZERO. /materialforge/ est servi en statique hors bundle.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---
### Task 5 : P3 — la convention Blender, et un banc PAR convention qui lit l'archive

**Files:**
- Modify: `backend/app/services/material_store.py:105-135` (`NAMINGS`, `NAMING_LABELS`, `NAMING_NOTES`), `:273-311` (`_NAMING_PATTERNS`), `:313-328` (`DEFAULT_EXPORT_MAPS`), `:330-386` (`_ENGINE_SLOTS`), `:407-439` (`_ROLE_BY_NAMING`)
- Test: `backend/tests/test_material_naming_archive.py`

- [ ] **Step 1 : relire la documentation AVANT d'écrire une seule ligne**

Lancer, dans cet ordre, et coller les extraits obtenus dans le commentaire du
Step 3 (jamais de mémoire) :

1. `WebFetch` sur `https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html`, invite : *« liste les noms exacts des entrées du Principled BSDF et les panneaux qui les groupent ; cite ce que le manuel dit de l'entrée Normal, de Emission Color / Emission Strength, et de Base Color / Metallic / Roughness / IOR / Alpha »*.
   **Attendu, mesuré le 03/09/2026 : HTTP 403** (`latest` comme `4.2`). C'est le même refus que les pages Runway de R1 — le noter, ne pas insister.
2. `WebSearch` : `Blender manual Principled BSDF inputs Base Color Metallic Roughness IOR Alpha Normal Coat Sheen Emission 4.2`.
   Attendu : les extraits qui donnent les définitions citées dans « Références vérifiées » de ce plan.
3. `WebSearch` : `Blender manual Normal Map node tangent space OpenGL green channel +Y Non-Color color space image texture`.
   Attendu : espace **Tangent** par défaut ; convention **OpenGL**, vert = **+Y vers le haut** ; texture en **Non-Color**.

- [ ] **Step 2 : écrire le banc PAR CONVENTION qui échoue**

Créer `backend/tests/test_material_naming_archive.py` :

```python
# -*- coding: utf-8 -*-
"""Material Forge P3 — UN BANC PAR CONVENTION, et il lit l'ARCHIVE.

Ce banc ne demande jamais à `material_store` ce qu'il a écrit : il télécharge
le ZIP par la route, l'ouvre, et confronte les noms de fichiers, les canaux de
l'ORM, ceux du MaskMap et le signe Y de la normale à une table LITTÉRALE,
écrite ici. Dériver la table de `_NAMING_PATTERNS` reviendrait à vérifier le
module contre lui-même : un renommage passerait au vert.

Six conventions : standard, blender, unity_urp, unity_hdrp, unreal, godot.

Run (depuis backend/) : python tests/test_material_naming_archive.py
"""
import asyncio
import io
import os
import pathlib
import sys
import tempfile
import types
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from httpx import ASGITransport, AsyncClient                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules["fal_client"] = _stub

from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import pbr_service as PBR                    # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# LA TABLE, ÉCRITE À LA MAIN. C'est le contrat publié : si le module change un
# nom, ce banc doit rougir, pas suivre.
N = "pierre_bleue"
ATTENDU = {
    "standard": {
        "basecolor": f"{N}_basecolor.png", "normal": f"{N}_normal.png",
        "roughness": f"{N}_roughness.png", "metallic": f"{N}_metallic.png",
        "ao": f"{N}_ao.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emissive.png", "orm": f"{N}_orm.png"},
    "blender": {
        "basecolor": f"{N}_base_color.png", "normal": f"{N}_normal_gl.png",
        "roughness": f"{N}_roughness.png", "metallic": f"{N}_metallic.png",
        "ao": f"{N}_ao.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emission.png"},
    "unity_urp": {
        "basecolor": f"{N}_BaseMap.png", "normal": f"{N}_Normal.png",
        "maskmap": f"{N}_MetallicOcclusion.png", "height": f"{N}_Height.png",
        "emissive": f"{N}_Emission.png"},
    "unity_hdrp": {
        "basecolor": f"{N}_BaseMap.png", "normal": f"{N}_Normal.png",
        "maskmap": f"{N}_MaskMap.png", "height": f"{N}_Height.png",
        "emissive": f"{N}_Emissive.png"},
    "unreal": {
        "basecolor": f"T_{N}_BC.png", "normal": f"T_{N}_N.png",
        "orm": f"T_{N}_ORM.png", "height": f"T_{N}_H.png",
        "emissive": f"T_{N}_E.png"},
    "godot": {
        "basecolor": f"{N}_albedo.png", "normal": f"{N}_normal.png",
        "orm": f"{N}_orm.png", "height": f"{N}_height.png",
        "emissive": f"{N}_emission.png"},
}

AO, ROUGH, METAL = 200, 0.70, 0.40      # constantes distinctes : un canal
                                        # interverti se voit immédiatement


def _plate(v, mode="L", taille=64):
    return Image.new(mode, (taille, taille), v)


def _fabriquer():
    """Une matière dont CHAQUE canal porte une constante différente, plus une
    normale VRAIMENT dérivée (pour que le signe Y ait un sens)."""
    mat = MS.create_material(
        name="Pierre bleue", prompt="blue stone",
        full_prompt=MS.build_full_prompt("blue stone"),
        source={"kind": "prompt", "model": "flux", "filename": None},
        res=64, seamless=True, seam={"before": 9.0, "after": 0.0})
    bosse = Image.new("L", (64, 64), 40)
    px = bosse.load()
    for y in range(20, 44):
        for x in range(64):
            px[x, y] = 40 + int(180 * (1.0 - abs(y - 32) / 12.0))
    gl = PBR.derive_maps(bosse.convert("RGB"), {"normal_invert_y": False},
                         ["normal"])["normal"]
    dx = PBR.derive_maps(bosse.convert("RGB"), {"normal_invert_y": True},
                         ["normal"])["normal"]
    maps = {"basecolor": _plate((60, 90, 150), "RGB"), "normal": gl,
            "roughness": _plate(int(ROUGH * 255)),
            "metallic": _plate(int(METAL * 255)), "ao": _plate(AO),
            "height": bosse, "emissive": _plate((0, 0, 0), "RGB"),
            "orm": Image.merge("RGB", (_plate(AO), _plate(int(ROUGH * 255)),
                                       _plate(int(METAL * 255))))}
    MS.save_maps(mat["id"], maps)
    mat = MS.read_material(mat["id"])
    mat["props"] = MS.merge_props(mat["props"], {"roughness": ROUGH,
                                                 "metallic": METAL})
    MS.write_material(mat)
    return MS.read_material(mat["id"]), gl, dx


async def main():
    global PASS
    mat, gl, dx = _fabriquer()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=120) as c:

        # ══ 1 · la liste publiée ═══════════════════════════════════════════
        d = (await c.get("/api/materials/namings")).json()
        ids = [n["id"] for n in d["namings"]]
        assert ids == ["standard", "blender", "unity_urp", "unity_hdrp",
                       "unreal", "godot"], ids
        par_id = {n["id"]: n for n in d["namings"]}
        bl = par_id["blender"]
        assert "Principled BSDF" in bl["label"], bl["label"]
        for mot in ("Non-Color", "OpenGL", "Emission Strength",
                    "Separate Color"):
            assert mot in bl["note"], (mot, bl["note"])
        assert "Blender" not in par_id["standard"]["label"], \
            "« standard » ne doit plus s'annoncer comme la cible Blender"
        ok("GET /materials/namings : six conventions, Blender nommée, sa note "
           "cite Non-Color, OpenGL, Emission Strength et Separate Color")

        # ══ 2 · l'ARCHIVE de chaque convention ═════════════════════════════
        for nom, attendu in ATTENDU.items():
            r = await c.get(f"/api/materials/{mat['id']}/export"
                            f"?format=zip&naming={nom}")
            assert r.status_code == 200, (nom, r.text)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                dedans = set(z.namelist())
                images = {n for n in dedans if n.lower().endswith(".png")
                          and n != "thumb.png"}
                assert images == set(attendu.values()), (nom, sorted(images))
                assert {"material.json", "LISEZMOI.txt"} <= dedans, nom
                lisez = z.read("LISEZMOI.txt").decode("utf-8")
                assert "OpenGL" in lisez, nom
                fleches = [l for l in lisez.splitlines() if " -> " in l]
                assert len(fleches) >= len(images) - 1, (nom, fleches)

                if "orm" in attendu:
                    with Image.open(io.BytesIO(z.read(attendu["orm"]))) as im:
                        r_, g_, b_ = im.convert("RGB").split()
                    assert r_.getpixel((3, 3)) == AO, (nom, "R != AO")
                    assert abs(g_.getpixel((3, 3)) - ROUGH * 255) <= 2, nom
                    assert abs(b_.getpixel((3, 3)) - METAL * 255) <= 2, nom
                if "maskmap" in attendu:
                    with Image.open(io.BytesIO(z.read(attendu["maskmap"]))) as im:
                        assert im.mode == "RGBA", (nom, im.mode)
                        mr, mg, mb, ma = im.split()
                    assert abs(mr.getpixel((3, 3)) - METAL * 255) <= 2, nom
                    assert mg.getpixel((3, 3)) == AO, (nom, "V != occlusion")
                    assert mb.getpixel((3, 3)) == 0, (nom, "B != détail")
                    assert abs(ma.getpixel((3, 3)) - (255 - ROUGH * 255)) <= 2, nom
                # LE SIGNE Y, épinglé par son TÉMOIN : la même normale dérivée
                # en DirectX est le miroir exact autour de 128.
                with Image.open(io.BytesIO(z.read(attendu["normal"]))) as im:
                    livre = im.convert("RGB").split()[1]
                for xy in ((7, 26), (7, 38), (31, 24)):
                    v, a, b = (livre.getpixel(xy), gl.split()[1].getpixel(xy),
                               dx.split()[1].getpixel(xy))
                    assert v == a, (nom, xy, v, a)
                    assert abs((a + b) - 256) <= 2, (nom, xy, a, b)
            ok(f"archive « {nom} » : {len(images)} PNG aux noms exacts, "
               f"canaux et signe Y vérifiés dans les octets livrés")

        # ══ 3 · Blender ne livre PAS d'ORM par défaut, et le dit ═══════════
        r = await c.get(f"/api/materials/{mat['id']}/export/manifest"
                        f"?format=zip&naming=blender")
        m = r.json()
        roles = {e["kind"]: e for e in m["files"]}
        assert "orm" not in roles, roles.keys()
        assert "Multiply" in roles["ao"]["slot"] or \
               "multiplier" in roles["ao"]["slot"].lower(), roles["ao"]["slot"]
        assert "Non-Color" in roles["roughness"]["slot"], roles["roughness"]
        assert "Emission Strength" in roles["emissive"]["slot"], roles["emissive"]
        ok("bordereau Blender : pas d'ORM par défaut (le Principled BSDF n'a "
           "pas d'entrée pour lui), l'AO se multiplie, les cartes de données "
           "sont en Non-Color")

    print(f"\nOK — {PASS} assertions groupées vertes (conventions d'export, "
          f"lues dans l'archive)")


asyncio.run(main())
```

- [ ] **Step 3 : lancer le banc et le voir rouge**

```
python tests/test_material_naming_archive.py
```

Attendu : `AssertionError: ['standard', 'unity_urp', 'unity_hdrp', 'unreal', 'godot']`.

- [ ] **Step 4 : ajouter la convention Blender**

Dans `backend/app/services/material_store.py` :

`NAMINGS` (ligne 105) devient :

```python
NAMINGS = ("standard", "blender", "unity_urp", "unity_hdrp", "unreal", "godot")
```

`NAMING_LABELS` (ligne 112) : remplacer la ligne `standard` et ajouter
`blender` juste après :

```python
NAMING_LABELS = {
    "standard": "Standard (Substance, Marmoset, archive d'équipe)",
    "blender": "Blender — Principled BSDF",
    "unity_urp": "Unity URP — Lit",
```

`NAMING_NOTES` (ligne 120) : remplacer la note `standard` et ajouter
`blender` :

```python
    "standard": "Suffixes explicites (_basecolor, _normal, _orm…). Le choix "
                "neutre : Substance, Marmoset, archive d'équipe. Blender a "
                "désormais sa propre cible, qui nomme ses emplacements.",
    "blender": "Le Principled BSDF n'a NI entrée Occlusion NI entrée ORM : "
               "l'occlusion se multiplie sur la Base Color (nœud Mix, mode "
               "Multiply), et l'ORM demanderait un Separate Color — les "
               "fichiers séparés partent donc cochés. Toutes les cartes de "
               "données (normale, rugosité, métal, hauteur) se règlent en "
               "Color Space Non-Color ; laissées en sRGB, elles sont "
               "silencieusement fausses. La normale est OpenGL (+Y vers le "
               "haut), la convention de Blender, et son nom de fichier le "
               "dit : Blender n'a aucun commutateur DirectX. L'émissive ne "
               "rend rien tant qu'Emission Strength vaut 0.",
```

`_NAMING_PATTERNS` (ligne 273) : ajouter, juste après le bloc `standard` :

```python
    # Blender ne branche RIEN par le nom de fichier (aucun importeur ne le
    # fait pour un dossier de PNG) : ces noms servent l'humain qui glisse les
    # images dans le graphe. Un seul y ajoute une INFORMATION que le format ne
    # porte pas — `_normal_gl` — parce que se tromper de convention de normale
    # est le seul défaut de ce lot qui ne se voie pas tout de suite.
    "blender": {"basecolor": "{n}_base_color.png",
                "normal": "{n}_normal_gl.png",
                "roughness": "{n}_roughness.png",
                "metallic": "{n}_metallic.png",
                "ao": "{n}_ao.png", "height": "{n}_height.png",
                "emissive": "{n}_emission.png", "orm": "{n}_orm.png"},
```

`DEFAULT_EXPORT_MAPS` (ligne 313) : ajouter après `standard` :

```python
    # Blender lit des fichiers SÉPARÉS : l'ORM ne se branche que par un
    # Separate Color, trois nœuds de plus pour zéro gain. Il reste décochable
    # -recochable comme tout le reste.
    "blender": ("basecolor", "normal", "roughness", "metallic", "ao",
                "height", "emissive"),
```

`_ENGINE_SLOTS` (ligne 330) : ajouter une entrée, avant `unity_urp` :

```python
    # Relu le 03/09/2026. La page du manuel refuse la lecture automatique
    # (HTTP 403 sur `latest` comme sur `4.2`, mesuré) ; les définitions
    # ci-dessous viennent des extraits publiés par la recherche :
    #   Base Color « Overall color of the material used for diffuse,
    #               subsurface, metal and transmission »
    #   Metallic   « Blends between a dielectric and metallic material model »
    #   Roughness  « Specifies microfacet roughness of the surface for
    #               specular reflection and transmission »
    #   Normal     « Controls the normals of the base layers »
    # et, pour le nœud Normal Map : espace Tangent par défaut, convention
    # OpenGL (canal vert = +Y vers le haut), texture en Non-Color.
    "blender": {
        "basecolor": "Principled BSDF > Base Color (Image Texture, "
                     "Color Space sRGB)",
        "normal": "Image Texture (Non-Color) > Normal Map (espace Tangent) > "
                  "Principled BSDF > Normal — OpenGL +Y, la convention de "
                  "Blender, qui n'a pas de commutateur DirectX",
        "roughness": "Principled BSDF > Roughness (Image Texture, Non-Color)",
        "metallic": "Principled BSDF > Metallic (Image Texture, Non-Color)",
        "height": "Material Output > Displacement, via un nœud Displacement "
                  "(ou un Bump) — Image Texture en Non-Color",
        "emissive": "Principled BSDF > Emission Color, et monter Emission "
                    "Strength au-dessus de 0 (sinon la carte ne rend rien)",
        "ao": "aucune entrée du Principled BSDF : multiplier la Base Color "
              "par cette carte (nœud Mix Color, mode Multiply)",
        "orm": "aucune entrée : séparer les canaux avec un nœud Separate "
               "Color (R -> occlusion, V -> Roughness, B -> Metallic) — les "
               "fichiers séparés sont plus directs, et partent cochés",
    },
```

`_ROLE_BY_NAMING` (ligne 407) : ajouter une entrée :

```python
    "blender": {
        "normal": "Normale tangente OpenGL (+Y vers le haut) — Blender n'a "
                  "AUCUN commutateur DirectX : le nom du fichier est le seul "
                  "avertissement possible",
        "ao": "Occlusion — à multiplier sur la Base Color : le Principled "
              "BSDF n'a pas d'entrée d'occlusion",
        "orm": "Packée R=AO V=rugosité B=métal — lisible par un Separate "
               "Color, mais les fichiers séparés sont plus directs ici"},
```

- [ ] **Step 5 : relancer le banc et le voir vert**

```
python tests/test_material_naming_archive.py
python tests/test_material_truth.py
python tests/test_materials_api.py
```

Attendu : `OK — 8 assertions groupées vertes (conventions d'export, lues dans
l'archive)` pour le premier ; les deux autres inchangés (ils n'épinglent que
`unity_*`, `unreal`, `godot` et `standard`).

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/material_store.py backend/tests/test_material_naming_archive.py
git commit -m 'matieres P3 : Blender a sa convention, et le banc lit l archive

Blender etait SOUS-ENTENDU dans la cible standard, dont le libelle promettait
Blender, Substance et Marmoset a la fois. Or le Principled BSDF n'\''a NI entree
Occlusion NI entree ORM : l'\''archive standard livrait un ORM qu'\''aucun
emplacement ne lit et taisait que l'\''occlusion doit se multiplier sur la Base
Color. Blender a donc sa cible, ses emplacements nommes, et standard cesse de
promettre ce qu'\''il ne tient pas.

Trois pieges nommes, chacun invisible a l'\''oeil : Non-Color sur toutes les
cartes de donnees (en sRGB elles sont silencieusement fausses), Emission
Strength au-dessus de zero (sinon l'\''emissive ne rend rien), normale OpenGL
+Y ecrite DANS le nom du fichier parce que Blender n'\''a aucun commutateur
DirectX.

Le banc est un banc PAR CONVENTION et il lit l'\''ARCHIVE telechargee : noms de
fichiers contre une table litterale ecrite dans le banc — la deriver du module
reviendrait a le verifier contre lui-meme —, canaux de l'\''ORM et du MaskMap
lus pixel par pixel avec trois constantes distinctes, et signe Y epingle par
son temoin (la meme normale derivee en DirectX est le miroir exact autour de
128, mesure a 2 niveaux pres).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 6 : P2 — « mon modèle » comme forme d'aperçu (le moteur d'habillage)

**Files:**
- Create: `backend/app/services/mesh_paint.py`
- Modify: `backend/app/api/routes.py:7635-7695` (`material_preview_glb`), `:7697-7742` (helper voisin `_mat_model_glb`)
- Modify: `frontend/materialforge/materialforge.js:79-86` (`MESHES`), `:931-948` (`glbUrl`)
- Test: `backend/tests/test_mesh_paint.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_mesh_paint.py` :

```python
# -*- coding: utf-8 -*-
"""Habiller un maillage d'une matière du Forge — le moteur (T6 « mon modèle »,
puis T14/T15 « une matière par partie »).

BANC-MIROIR : le GLB produit est REPARSÉ (mesh_edit.lire_glb), ses triangles
relus (print3d.lire_glb_triangles), et les octets de chaque texture ressortis
du tampon à l'offset déclaré et comparés à l'octet près. On ne demande jamais
au module ce qu'il croit avoir écrit.

Run (depuis backend/) : python tests/test_mesh_paint.py
"""
import io
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import gltf_builder, mesh_edit, print3d      # noqa: E402
from app.services import mesh_paint as MP                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def png(couleur, taille=8):
    buf = io.BytesIO()
    Image.new("RGB", (taille, taille), couleur).save(buf, format="PNG")
    return buf.getvalue()


PAYLOAD = {"basecolor": png((200, 30, 30)), "normal": png((128, 128, 255)),
           "orm": png((240, 180, 20)), "emissive": png((0, 0, 0))}

CUBE = gltf_builder.build_glb({}, None, "cube", "banc")

# ══ 1 · toutes les primitives pointent sur le matériau ajouté ═══════════════
sortie = MP.habiller(CUBE, [{"cible": "tout", "mid": "mat_deadbeef",
                             "nom": "Pierre bleue", "maps": PAYLOAD,
                             "props": {"metallic": 0.4, "roughness": 0.7}}])
doc, binc = mesh_edit.lire_glb(sortie)
avant, _ = mesh_edit.lire_glb(CUBE)
assert len(doc["materials"]) == len(avant.get("materials") or []) + 1
idx = len(doc["materials"]) - 1
assert doc["materials"][idx]["name"] == "Pierre bleue"
vus = [p.get("material") for m in doc["meshes"] for p in m["primitives"]]
assert vus and set(vus) == {idx}, vus
ok(f"habillage : un matériau ajouté (index {idx}), {len(vus)} primitive(s) "
   f"pointent dessus")

# ══ 2 · les octets des textures sont DANS le tampon, intacts ════════════════
mat = doc["materials"][idx]
pbr = mat["pbrMetallicRoughness"]
assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0, pbr
assert pbr["metallicRoughnessTexture"]["index"] == mat["occlusionTexture"]["index"]
trouve = {}
for cle, ref in (("basecolor", pbr["baseColorTexture"]),
                 ("orm", pbr["metallicRoughnessTexture"]),
                 ("normal", mat["normalTexture"]),
                 ("emissive", mat["emissiveTexture"])):
    src = doc["images"][doc["textures"][ref["index"]]["source"]]
    bv = doc["bufferViews"][src["bufferView"]]
    o = bv.get("byteOffset", 0)
    trouve[cle] = binc[o:o + bv["byteLength"]]
    assert src["mimeType"] == "image/png", (cle, src)
assert trouve == PAYLOAD, [k for k in PAYLOAD if trouve[k] != PAYLOAD[k]]
assert doc["buffers"][0]["byteLength"] == len(binc), \
    (doc["buffers"][0]["byteLength"], len(binc))
ok("les quatre textures sortent du tampon à l'octet près, le tampon déclare "
   "sa vraie longueur, les facteurs restent à 1.0 (les niveaux sont cuits)")

# ══ 3 · le GLB reste lisible par le reste du dépôt ══════════════════════════
tris_av = print3d.lire_glb_triangles(CUBE)
tris_ap = print3d.lire_glb_triangles(sortie)
assert len(tris_ap) == len(tris_av) and tris_ap[0] == tris_av[0]
assert print3d.bbox(tris_ap) == print3d.bbox(tris_av)
ok(f"géométrie intacte : {len(tris_ap)} triangles, même boîte englobante — "
   f"l'habillage ne touche qu'aux matériaux")

# ══ 4 · les trois granularités du panneau Parties ═══════════════════════════
d0, _ = mesh_edit.lire_glb(CUBE)
assert MP.cibles(d0, "tout", None) == MP.cibles(d0, "maillage", 0)
noeud = next(i for i, n in enumerate(d0.get("nodes") or [])
             if isinstance(n.get("mesh"), int))
assert MP.cibles(d0, "noeud", noeud) == MP.cibles(d0, "maillage", 0)
ok("cibles : nœud, maillage et « tout » se ramènent aux mêmes primitives sur "
   "un modèle à un seul maillage")

# ══ 5 · les refus se disent ════════════════════════════════════════════════
sans_uv, binc0 = mesh_edit.lire_glb(CUBE)
for m in sans_uv["meshes"]:
    for p in m["primitives"]:
        p["attributes"].pop("TEXCOORD_0", None)
essais = [
    (mesh_edit.ecrire_glb(sans_uv, binc0),
     [{"cible": "tout", "mid": "x", "maps": PAYLOAD}], "uv"),
    (CUBE, [], "aucune"),
    (CUBE, [{"cible": "noeud", "index": 999, "mid": "x", "maps": PAYLOAD}],
     "999"),
    (CUBE, [{"cible": "chose", "index": 0, "mid": "x", "maps": PAYLOAD}],
     "chose"),
    (CUBE, [{"cible": "maillage", "index": None, "mid": "x",
             "maps": PAYLOAD}], "index"),
]
mots = []
for data, lots, mot in essais:
    try:
        MP.habiller(data, lots)
        raise AssertionError(f"{mot} : aurait dû lever")
    except ValueError as e:
        assert mot in str(e).lower(), (mot, str(e))
        mots.append(str(e)[:52])
ok("refus nommés : " + " | ".join(mots))

print(f"\nOK — {PASS} assertions groupées vertes (mesh_paint, habillage)")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_mesh_paint.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.mesh_paint'`.

- [ ] **Step 3 : écrire `mesh_paint.py`**

Créer `backend/app/services/mesh_paint.py` :

```python
# -*- coding: utf-8 -*-
"""Habiller un maillage d'une matière du Material Forge (R10c P2 « mon
modèle », puis D2 « une matière par partie »).

CE MODULE N'ÉCRIT AUCUN FICHIER. Il prend les octets d'un GLB et rend les
octets d'un autre. La seule plume qui DÉPOSE une version reste
`mesh_edit.ecrire_version` — doctrine de l'Établi : jamais d'écrasement,
toujours une version numérotée avec sa fiche.

POURQUOI DES PRIMITIVES, ET PAS DES NŒUDS. Un modèle Meshy arrive souvent en
un nœud UNIQUE portant plusieurs matériaux, un Tripo en plusieurs nœuds
(mesuré : c'est la raison d'être des trois granularités du panneau Parties de
l'Établi). Aucune granularité ne suffit seule, et la seule chose qui porte
réellement un `material` dans le format glTF est la PRIMITIVE. Les trois
entrées de l'écran s'y ramènent donc ici, une fois, au même endroit.

LES FACTEURS RESTENT À 1.0, et ce n'est pas un détail. glTF pose
`rugosité = roughnessFactor x texture.G` : nos niveaux sont déjà CUITS dans
les cartes (`material_store.bake_levels`), et poser en plus le curseur dans le
facteur les compterait deux fois — exactement le défaut que `render_block`
documente et que `gltf_builder` évite côté aperçu. Une seule chose décide de
la valeur, et c'est la carte.
"""
from __future__ import annotations

from app.services import mesh_edit

__all__ = ["CIBLES", "cibles", "materiau", "habiller"]

CIBLES = ("tout", "noeud", "maillage", "materiau")


def _mime(data: bytes) -> str:
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    raise ValueError("habillage : une texture n'est ni PNG ni JPEG "
                     "(glTF n'accepte que ces deux-là)")


class _Tampon:
    """Le tampon binaire en construction, aligné sur 4 octets à chaque ajout.

    La spec glTF exige cet alignement pour les bufferViews ; sans lui, un
    lecteur strict refuse le fichier et un lecteur laxiste lit de travers —
    le second est pire."""

    def __init__(self, binc: bytes):
        self.morceaux = [bytes(binc)]
        self.taille = len(binc)

    def ajouter(self, data: bytes) -> tuple[int, int]:
        pad = (-self.taille) % 4
        if pad:
            self.morceaux.append(b"\x00" * pad)
            self.taille += pad
        debut = self.taille
        self.morceaux.append(bytes(data))
        self.taille += len(data)
        return debut, len(data)

    def octets(self) -> bytes:
        return b"".join(self.morceaux)


def _texture(doc: dict, tampon: _Tampon, data: bytes) -> int:
    """Ajoute une image au document et rend l'index de sa texture."""
    debut, n = tampon.ajouter(data)
    views = doc.setdefault("bufferViews", [])
    views.append({"buffer": 0, "byteOffset": debut, "byteLength": n})
    images = doc.setdefault("images", [])
    images.append({"bufferView": len(views) - 1, "mimeType": _mime(data)})
    samplers = doc.setdefault("samplers", [])
    if not samplers:
        # 9729 LINEAR, 9987 LINEAR_MIPMAP_LINEAR, 10497 REPEAT : le pavage est
        # la raison d'être d'une matière, un CLAMP la trahirait.
        samplers.append({"magFilter": 9729, "minFilter": 9987,
                         "wrapS": 10497, "wrapT": 10497})
    textures = doc.setdefault("textures", [])
    textures.append({"sampler": 0, "source": len(images) - 1})
    return len(textures) - 1


def materiau(doc: dict, tampon: _Tampon, nom: str, payload: dict) -> int:
    """Ajoute un matériau glTF portant les cartes fournies (octets PNG/JPEG
    déjà encodés, cartes déjà cuites) et rend son index."""
    pbr = {"baseColorFactor": [1.0, 1.0, 1.0, 1.0],
           "metallicFactor": 1.0, "roughnessFactor": 1.0}
    mat = {"name": (str(nom or "matière")[:64] or "matière"),
           "pbrMetallicRoughness": pbr, "doubleSided": True}
    if payload.get("basecolor"):
        pbr["baseColorTexture"] = {
            "index": _texture(doc, tampon, payload["basecolor"])}
    if payload.get("orm"):
        # UNE image, DEUX emplacements : c'est le contrat glTF (R = occlusion,
        # V = rugosité, B = métal), et le dupliquer coûterait le double du
        # poids pour les mêmes octets.
        i = _texture(doc, tampon, payload["orm"])
        pbr["metallicRoughnessTexture"] = {"index": i}
        mat["occlusionTexture"] = {"index": i}
    if payload.get("normal"):
        mat["normalTexture"] = {"index": _texture(doc, tampon,
                                                  payload["normal"])}
    if payload.get("emissive"):
        mat["emissiveTexture"] = {"index": _texture(doc, tampon,
                                                    payload["emissive"])}
        mat["emissiveFactor"] = [1.0, 1.0, 1.0]
    mats = doc.setdefault("materials", [])
    mats.append(mat)
    return len(mats) - 1


def _entier(v, quoi: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"habillage : {quoi} — un index entier à partir de 0 "
                         f"est attendu (reçu {v!r})")
    return v


def _mesh_sous(doc: dict, i: int, vus=None) -> set:
    """Les maillages portés par ce nœud ET par toute sa descendance.

    La descendance compte : cocher un nœud parent dans le panneau Parties est
    un geste naturel, et n'habiller que lui laisserait les enfants nus sans
    rien dire."""
    nodes = doc.get("nodes") or []
    if not (0 <= i < len(nodes)):
        raise ValueError(f"habillage : nœud {i} inconnu — le document en "
                         f"déclare {len(nodes)}")
    vus = set() if vus is None else vus
    if i in vus:
        return set()
    vus.add(i)
    out = set()
    n = nodes[i]
    if isinstance(n.get("mesh"), int):
        out.add(n["mesh"])
    for e in (n.get("children") or []):
        out |= _mesh_sous(doc, _entier(e, "enfant"), vus)
    return out


def cibles(doc: dict, cible, index) -> set:
    """Les couples (maillage, primitive) visés par une cible de l'écran."""
    meshes = doc.get("meshes") or []
    toutes = {(m, p) for m, mesh in enumerate(meshes)
              for p in range(len(mesh.get("primitives") or []))}
    c = str(cible or "").strip().lower()
    if c == "tout":
        return toutes
    if c == "noeud":
        gardes = _mesh_sous(doc, _entier(index, "index de nœud"))
        return {(m, p) for (m, p) in toutes if m in gardes}
    if c == "maillage":
        i = _entier(index, "index de maillage")
        if i >= len(meshes):
            raise ValueError(f"habillage : maillage {i} inconnu — le document "
                             f"en déclare {len(meshes)}")
        return {(m, p) for (m, p) in toutes if m == i}
    if c == "materiau":
        i = _entier(index, "index de matériau")
        n = len(doc.get("materials") or [])
        if i >= n:
            raise ValueError(f"habillage : matériau {i} inconnu — le document "
                             f"en déclare {n}")
        return {(m, p) for (m, p) in toutes
                if meshes[m]["primitives"][p].get("material") == i}
    raise ValueError(f"habillage : cible « {cible} » inconnue — attendu : "
                     f"{', '.join(CIBLES)}")


def habiller(data: bytes, lots) -> bytes:
    """Pose une matière sur chaque cible et rend les octets du GLB habillé.

    `lots` = liste de `{cible, index, mid, nom, maps}` où `maps` est un
    dictionnaire kind -> octets PNG déjà encodés et déjà cuits. Deux lots qui
    portent le même `mid` partagent UN matériau glTF : sinon un modèle à
    quarante pièces embarquerait quarante copies des mêmes textures.
    """
    doc, binc = mesh_edit.lire_glb(data)
    if not (doc.get("meshes") or []):
        raise ValueError("habillage : ce GLB ne contient aucun maillage")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("habillage : aucune matière à poser")
    tampons = doc.get("buffers") or []
    if len(tampons) != 1 or tampons[0].get("uri"):
        raise ValueError("habillage : ce GLB a un tampon externe ou multiple "
                         "— l'habillage n'y touche pas")

    tampon = _Tampon(binc)
    connus: dict = {}
    for lot in lots:
        if not isinstance(lot, dict):
            raise ValueError("habillage : chaque lot est un objet "
                             "{cible, index, mid, nom, maps}")
        vises = cibles(doc, lot.get("cible"), lot.get("index"))
        if not vises:
            raise ValueError(
                f"habillage : la cible « {lot.get('cible')} » "
                f"{lot.get('index')} ne porte aucune primitive")
        for (m, p) in sorted(vises):
            prim = doc["meshes"][m]["primitives"][p]
            if "TEXCOORD_0" not in (prim.get("attributes") or {}):
                raise ValueError(
                    f"habillage : la pièce (maillage {m}, primitive {p}) n'a "
                    "pas d'uv (TEXCOORD_0) — une matière ne peut pas s'y "
                    "plaquer. Dépliez-la d'abord (Meshy uv-unwrap).")
            if "KHR_draco_mesh_compression" in (prim.get("extensions") or {}):
                raise ValueError(
                    f"habillage : la pièce (maillage {m}, primitive {p}) est "
                    "compressée en Draco — décompressez d'abord (gltfpack).")
        cle = lot.get("mid") or lot.get("nom") or f"lot{len(connus)}"
        if cle not in connus:
            connus[cle] = materiau(doc, tampon, lot.get("nom") or str(cle),
                                   lot.get("maps") or {})
        for (m, p) in vises:
            doc["meshes"][m]["primitives"][p]["material"] = connus[cle]

    octets = tampon.octets()
    doc["buffers"] = [{"byteLength": len(octets)}]
    return mesh_edit.ecrire_glb(doc, octets)
```

- [ ] **Step 4 : relancer le banc et le voir vert**

```
python tests/test_mesh_paint.py
```

Attendu : cinq lignes `✓` puis
`OK — 5 assertions groupées vertes (mesh_paint, habillage)`.

- [ ] **Step 5 : brancher l'aperçu sur un modèle**

Dans `backend/app/api/routes.py`, ajouter, juste après `_mat_glb` (fin ligne
7742) :

```python
def _mat_model_glb(mat: dict, data: bytes, res: int, kinds) -> bytes:
    """Le GLB d'un MODÈLE, habillé de la matière — pour l'APERÇU seulement.

    Aucune version n'est écrite : c'est une lecture. Le jour où l'utilisateur
    veut GARDER l'habillage, c'est `POST /etabli/habiller` qui passe, et lui
    seul, par `mesh_edit.ecrire_version`."""
    from app.services import material_store as MS
    from app.services import mesh_paint as MP
    maps = MS.load_maps(mat["id"], kinds)
    if not maps:
        raise HTTPException(409, "Cette matière n'a aucune map sur disque")
    maps = MS.bake_levels(MS.resize_maps(maps, res), mat["props"])
    payload = {k: MS.png_bytes(v, k, 8) for k, v in maps.items()
               if k in MS.GLB_SLOTS}
    try:
        return MP.habiller(data, [{"cible": "tout", "mid": mat["id"],
                                   "nom": mat["name"], "maps": payload}])
    except ValueError as e:
        raise HTTPException(400, str(e))
```

Dans `material_preview_glb`, remplacer la signature :

```python
async def material_preview_glb(request: Request, mid: str,
                               mesh: str = "sphere", res: int = 1024,
                               stage: int = 0, scale: int = 1):
```

par :

```python
async def material_preview_glb(request: Request, mid: str,
                               mesh: str = "sphere", res: int = 1024,
                               stage: int = 0, scale: int = 1,
                               model: str = "", mversion: int = 1):
```

et, juste après `res = MS.clean_preview_res(res, 1024)`, insérer :

```python
    # « mon modèle » : la cinquième forme d'aperçu de R10c P2. Le nom de job
    # vient du réseau, donc il passe la MÊME porte que les routes d'écriture
    # de l'Établi (`_etabli_glb_cible` : entier >= 1, deux gardes de chemin,
    # 404 franc) — une forme d'aperçu n'est pas une raison d'ouvrir une
    # seconde porte moins gardée sur le même dossier.
    modele = str(model or "").strip()
    donnees = None
    if modele:
        _job, donnees, _depuis = _etabli_glb_cible(modele, mversion,
                                                   "aperçu de matière")
```

Remplacer la construction de la clé de cache :

```python
    key = hashlib.sha1(
        f"{key}-s{stage}v{_SV}u{scale}-{_uv}-m{_MV}".encode("utf-8")
    ).hexdigest()[:24]
```

par :

```python
    # Le modèle entre dans l'empreinte : sans lui, deux modèles différents
    # partageraient un GLB en cache et l'écran servirait l'ancien sans un mot.
    key = hashlib.sha1(
        f"{key}-s{stage}v{_SV}u{scale}-{_uv}-m{_MV}"
        f"-M{modele}:{mversion}:{len(donnees or b'')}".encode("utf-8")
    ).hexdigest()[:24]
```

et remplacer la construction du GLB :

```python
    data = await asyncio.to_thread(MS.preview_cache_get, mat["id"], key)
    if data is None:
        data = await asyncio.to_thread(_mat_glb, mat, mesh, res, None,
                                       bool(stage), bool(scale))
        await asyncio.to_thread(MS.preview_cache_put, mat["id"], key, data)
```

par :

```python
    data = await asyncio.to_thread(MS.preview_cache_get, mat["id"], key)
    if data is None:
        if donnees is not None:
            data = await asyncio.to_thread(_mat_model_glb, mat, donnees, res,
                                           None)
        else:
            data = await asyncio.to_thread(_mat_glb, mat, mesh, res, None,
                                           bool(stage), bool(scale))
        await asyncio.to_thread(MS.preview_cache_put, mat["id"], key, data)
```

- [ ] **Step 6 : la cinquième forme dans l'écran**

Dans `frontend/materialforge/materialforge.js`, ajouter à `MESHES` (ligne 79)
une entrée `{ id: "model", label: "Mon modèle" }` — la liste est en
`{ id, label }`, pas en `{ k, label }` — et dans `glbUrl` (ligne 931)
ajouter, avant la construction de la requête :

```js
  /* « Mon modèle » n'est pas un maillage généré : c'est un job de l'Établi.
     Le paramètre `mesh` n'a alors plus de sens et n'est pas envoyé — la route
     le sait, mais l'envoyer laisserait croire qu'il pèse sur le résultat.

     `state.modele3d` et NON `state.model` : ce dernier existe déjà et porte
     le modèle d'image (`$("#model").value`, mémorisé sous `mf_model`). Deux
     choses différentes sous un même nom, c'est le genre de collision qui se
     découvre trois écrans plus loin. */
  if (mesh === "model") {
    if (!state.modele3d || !state.modele3d.job) return null;
    return `/api/materials/${m.id}/preview.glb?res=${res}`
      + `&model=${encodeURIComponent(state.modele3d.job)}`
      + `&mversion=${state.modele3d.version || 1}`;
  }
```

Ajouter `modele3d: null` à l'objet `state` (ligne 239) et, dans
`renderMeshChips` (ligne 3142), afficher la puce « Mon modèle » désactivée
tant que `state.modele3d` est nul, avec le titre : « Choisis d'abord un
modèle dans l'Établi ». Le sélecteur de modèle lui-même vient avec T15 : ici,
la puce existe et se justifie de son absence.

- [ ] **Step 7 : vérifier à l'écran**

Avec au moins un job dans l'Établi, ouvrir
`http://127.0.0.1:8765/api/materials/<mid>/preview.glb?model=<job>&mversion=1`
dans le navigateur : le fichier se télécharge et s'ouvre dans `/etabli/`.
Attendu : le modèle porte la matière, pavage compris.

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/mesh_paint.py backend/app/api/routes.py frontend/materialforge/materialforge.js backend/tests/test_mesh_paint.py
git commit -m 'matieres P2 : la cinquieme forme d apercu est mon modele

Quatre des cinq formes demandees existaient deja (sphere, cube, plan,
cylindre) : seule mon modele manquait. mesh_paint pose une matiere sur les
primitives d'\''un GLB — la primitive est la SEULE chose qui porte un material
dans le format, et c'\''est la que les trois granularites du panneau Parties se
ramenent, une fois, au meme endroit.

Ce module n'\''ecrit aucun fichier : l'\''apercu est une lecture. La seule plume
qui depose une version reste mesh_edit.ecrire_version, et le nom de job passe
la MEME porte que les routes d'\''ecriture de l'\''Etabli — une forme d'\''apercu
n'\''est pas une raison d'\''ouvrir une seconde porte moins gardee sur le meme
dossier. Le modele entre dans l'\''empreinte du cache : sans lui, deux modeles
partageraient un GLB et l'\''ecran servirait l'\''ancien sans un mot.

Trois refus parlants, la ou le silence coutait cher : pas d'\''uv (une matiere
ne peut pas se plaquer), Draco (decompresser d'\''abord), tampon externe. Le
banc reparse le GLB produit, relit ses triangles et ressort les octets de
chaque texture du tampon a l'\''offset declare : quatre textures identiques a
l'\''octet, meme boite englobante, facteurs a 1.0.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---
### Task 7 : P2 — les HDRI personnels : un décodeur RGBE en stdlib, et le refus nommé du .exr

**Files:**
- Create: `backend/app/services/hdr_reader.py`
- Modify: `backend/app/services/env_service.py:34-35` (`__all__`), fin de fichier (ambiances personnelles)
- Modify: `backend/app/services/material_store.py:1834-1879` (`env_jpeg` : liste blanche élargie aux ambiances personnelles)
- Modify: `backend/app/api/routes.py:7283-7300` (après `get_material_env` : import et suppression d'une ambiance)
- Modify: `frontend/materialforge/index.html:190-194`, `frontend/materialforge/materialforge.js:501-515` (`loadEnvs`), `:3192-3209` (`renderEnvChips`, `setEnv`)
- Test: `backend/tests/test_hdr_reader.py`

- [ ] **Step 1 : relire la spécification AVANT d'écrire le décodeur**

Lancer, et coller les faits dans le docstring du Step 3 :

1. `WebFetch` `https://en.wikipedia.org/wiki/RGBE_image_format`, invite : *« donne le nombre magique, la structure du fichier, et la formule qui reconstruit un canal depuis mantisse et exposant »*. Attendu (mesuré le 03/09/2026) : magic `23 3f 52 41 44 49 41 4e 43 45 0a`, quatre octets par pixel, `fR = R·2^(E−128)`.
2. `WebFetch` `https://www.graphics.cornell.edu/~bjw/rgbe.html`. Attendu : HTTP 200, la page publie `rgbe.txt` / `rgbe.h` / `rgbe.c` et renvoie à « Real Pixels », *Graphics Gems II*. **`https://www.graphics.cornell.edu/~bjw/rgbe.c` répond HTTP 300** : ne pas insister, la spec suffit et l'aller-retour du banc prouve le décodeur.
3. `WebFetch` `https://floyd.lbl.gov/radiance/refer/filefmts.pdf`. Attendu : HTTP 200, 148,6 Ko de PDF ; **non lisible ici** (`pdftoppm` absent). Le citer, ne pas le recopier.

- [ ] **Step 2 : écrire le banc qui échoue**

Créer `backend/tests/test_hdr_reader.py` :

```python
# -*- coding: utf-8 -*-
"""Lecture d'un .hdr (Radiance RGBE) en stdlib pur — R10c P2, HDRI personnels.

ALLER-RETOUR : le banc ÉCRIT lui-même des .hdr (plat et RLE adaptatif), donc
il prouve le décodeur contre une spécification, pas contre lui-même. Les
octets encodés sont produits ici, à la main, depuis des flottants connus.

Run (depuis backend/) : python tests/test_hdr_reader.py
"""
import math
import os
import pathlib
import struct
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import hdr_reader as HR                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def rgbe(r, g, b):
    """Flottants -> quadruplet RGBE, formule de référence (Real Pixels)."""
    v = max(r, g, b)
    if v < 1e-32:
        return (0, 0, 0, 0)
    m, e = math.frexp(v)               # v = m * 2**e, 0.5 <= m < 1
    k = m * 256.0 / v
    return (int(r * k), int(g * k), int(b * k), int(e + 128))


def scene(w, h):
    """Une scène connue : ciel en dégradé + un soleil 400 fois plus lumineux."""
    px = []
    for y in range(h):
        for x in range(w):
            t = y / max(1, h - 1)
            c = (0.30 + 0.50 * (1 - t), 0.45 + 0.40 * (1 - t), 0.80 - 0.30 * t)
            if abs(x - w * 3 // 4) < max(1, w // 40) and abs(y - h // 4) < max(1, h // 40):
                c = (400.0, 380.0, 340.0)
            px.append(c)
    return px


def ecrire_plat(w, h, px):
    out = bytearray(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\nEXPOSURE=1.0\n\n")
    out += f"-Y {h} +X {w}\n".encode("ascii")
    for c in px:
        out += bytes(rgbe(*c))
    return bytes(out)


def ecrire_rle(w, h, px):
    """RLE adaptatif : chaque scanline commence par 02 02 hi lo, puis quatre
    plans codés. On force les DEUX branches — répétitions et littéraux."""
    out = bytearray(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n")
    out += f"-Y {h} +X {w}\n".encode("ascii")
    for y in range(h):
        quad = [rgbe(*px[y * w + x]) for x in range(w)]
        out += bytes([2, 2, (w >> 8) & 0xFF, w & 0xFF])
        for c in range(4):
            plan = bytes(q[c] for q in quad)
            x = 0
            while x < len(plan):
                n = 1
                while x + n < len(plan) and plan[x + n] == plan[x] and n < 127:
                    n += 1
                if n >= 4:
                    out += bytes([128 + n, plan[x]])
                    x += n
                else:
                    n = 1
                    while (x + n < len(plan) and n < 128
                           and not (x + n + 3 < len(plan)
                                    and plan[x + n] == plan[x + n + 1]
                                    == plan[x + n + 2] == plan[x + n + 3])):
                        n += 1
                    out += bytes([n]) + plan[x:x + n]
                    x += n
    return bytes(out)


W, H = 64, 32
PX = scene(W, H)
PLAT, RLE = ecrire_plat(W, H, PX), ecrire_rle(W, H, PX)

# ══ 1 · en-tête et résolution ══════════════════════════════════════════════
e, off = HR.lire_entete(PLAT)
assert e["width"] == W and e["height"] == H, e
assert e["FORMAT"].lower().endswith("rle_rgbe"), e
assert PLAT[off:off + 4] == bytes(rgbe(*PX[0])), "offset du premier pixel"
ok(f"en-tête : {W}x{H}, FORMAT lu, premier pixel exactement à l'offset rendu")

# ══ 2 · les deux codages donnent les MÊMES octets ══════════════════════════
a = HR.decoder(PLAT)
b = HR.decoder(RLE)
assert a[0] == b[0] == W and a[1] == b[1] == H
assert bytes(a[2]) == bytes(b[2]), "plat et RLE divergent"
assert len(a[2]) == 4 * W * H
ok("scanline plate et RLE adaptatif décodent aux MÊMES 4·w·h octets "
   "(les deux branches du RLE — répétitions et littéraux — sont exercées)")

# ══ 3 · la valeur reconstruite vaut la valeur écrite ═══════════════════════
plans = a[2]
pires = 0.0
for i in (0, W - 1, W * H // 2, W * H - 1):
    y, x = divmod(i, W)
    base = y * 4 * W
    m = [plans[base + c * W + x] for c in range(3)]
    ex = plans[base + 3 * W + x]
    for c in range(3):
        got = (m[c] + 0.5) / 256.0 * (2.0 ** (ex - 128))
        veut = PX[i][c]
        pires = max(pires, abs(got - veut) / max(1e-6, veut))
assert pires < 0.02, pires
ok(f"reconstruction M·2^(E-128) : écart relatif max {pires * 100:.2f} % "
   f"(quantification 8 bits de la mantisse)")

# ══ 4 · les refus nommés ═══════════════════════════════════════════════════
refus = {}
cas = [
    ("radiance", b"PK\x03\x04pas du tout un hdr"),
    ("xyze", b"#?RADIANCE\nFORMAT=32-bit_rle_xyze\n\n-Y 4 +X 4\n" + b"\0" * 64),
    ("orientation", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n+Y 4 +X 4\n" + b"\0" * 64),
    ("ancien", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 2 +X 16\n"
               + bytes([255, 255, 255, 3]) + b"\0" * 200),
    ("mpx", b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 8192 +X 16384\n"),
]
for mot, data in cas:
    try:
        HR.decoder(data)
        raise AssertionError(f"{mot} : aurait dû lever")
    except ValueError as exc:
        assert mot in str(exc).lower(), (mot, str(exc))
        refus[mot] = str(exc)[:46]
ok("refus nommés : " + " | ".join(refus.values()))

# ══ 5 · l'équirectangulaire LDR ════════════════════════════════════════════
img = HR.equirect_ldr(PLAT)
assert img.size == (1024, 512) and img.mode == "RGB", (img.size, img.mode)
petite = img.resize((64, 32), __import__("PIL.Image", fromlist=["Image"]).BOX)
lum = petite.convert("L")
argmax = max(range(64 * 32), key=lambda i: lum.getdata()[i])
sy, sx = divmod(argmax, 64)
assert abs(sx - 48) <= 3 and abs(sy - 8) <= 3, (sx, sy)
h = lum.histogram()
n = sum(h)
sombres = sum(h[:16]) / n
clairs = sum(h[240:]) / n
assert sombres < 0.25 and clairs < 0.25, (sombres, clairs)
ok(f"équirect LDR 1024x512 : le soleil retombe en ({sx}, {sy}) sur 64x32, "
   f"{sombres * 100:.0f} % de pixels noirs et {clairs * 100:.0f} % de blancs "
   f"— l'exposition médiane n'écrase ni le ciel ni le soleil")

# ══ 6 · budget sur un 4k ═══════════════════════════════════════════════════
GW, GH = 4096, 2048
gros = ecrire_plat(GW, GH, scene(GW, GH))
t0 = time.perf_counter()
img4k = HR.equirect_ldr(gros)
dt = time.perf_counter() - t0
assert img4k.size == (1024, 512)
assert dt < 8.0, dt
print(f"\n  .hdr 4096x2048 -> équirect 1024x512 : {dt:.2f} s (budget 8,0 s)")

print(f"\nOK — {PASS} assertions groupées vertes (hdr_reader)")
```

- [ ] **Step 3 : lancer le banc et le voir rouge**

```
python tests/test_hdr_reader.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.hdr_reader'`.

- [ ] **Step 4 : écrire `hdr_reader.py`**

Créer `backend/app/services/hdr_reader.py` :

```python
# -*- coding: utf-8 -*-
"""Lire un .hdr (Radiance RGBE) en stdlib pur, et en faire une ambiance LDR.

POURQUOI. `<model-viewer>` a besoin d'une image d'environnement, sinon un
matériau métallique s'affiche NOIR (c'est déjà écrit dans `env_service`). Les
sept ambiances du dépôt sont générées en PIL ; R10c P2 demande en plus les
HDRI de l'utilisateur — et les HDRI du monde réel sont des `.hdr`.

LE FORMAT, ET POURQUOI IL EST LISIBLE SANS DÉPENDANCE. Un fichier Radiance est
un en-tête TEXTE, une ligne vide, une ligne de résolution, puis des scanlines
de quadruplets RGBE : trois octets de mantisse et UN exposant partagé, quatre
octets par pixel, `canal = M x 2^(E-128)`. Aucune compression d'entropie,
aucun flottant à décoder : du découpage d'octets suffit.

    #?RADIANCE
    FORMAT=32-bit_rle_rgbe
    EXPOSURE=1.0            (facultatif, multiplicatif, répétable)
                            <- ligne vide : fin de l'en-tête
    -Y 512 +X 1024          <- résolution ET orientation

Deux codages de scanline :
  * PLAT — `w` quadruplets entrelacés, dans l'ordre des pixels ;
  * RLE ADAPTATIF (« new-style ») — la scanline commence par `02 02 hi lo`
    avec `(hi << 8) | lo == w` et `8 <= w <= 32767` ; suivent QUATRE plans
    (R, G, B, E), chacun codé ainsi : un octet `c > 128` annonce `c - 128`
    copies de l'octet suivant, un octet `c <= 128` annonce `c` octets
    littéraux.
  * L'ANCIEN RLE (un pixel `255 255 255 n` qui répète le précédent) est
    REFUSÉ EN LE DISANT plutôt que deviné. Plus aucun outil ne l'écrit depuis
    vingt ans, et un décodeur silencieusement faux est pire qu'un refus : la
    matière sortirait éclairée de travers, sans que rien ne grince.

`.exr` EST HORS PÉRIMÈTRE, ET C'EST DIT ICI. OpenEXR admet au moins dix
schémas de compression (NONE, RLE, ZIPS, ZIP, PIZ, PXR24, B44, B44A, DWAA,
DWAB) ; seuls NONE et ZIP/ZIPS retomberaient sur `zlib`, et rien ne garantit
qu'un fichier donné soit de ceux-là. Un décodeur partiel qui refuse un fichier
sur deux APRÈS le téléchargement serait une promesse fausse : la route refuse
donc `.exr` par son extension, avec la phrase qui dit quoi faire.

Références relues le 03/09/2026 : `graphics.cornell.edu/~bjw/rgbe.html`
(implémentation de référence de Bruce Walter ; le `.c` lui-même répond
HTTP 300 à la lecture automatique), `floyd.lbl.gov/radiance/refer/filefmts.pdf`
(148,6 Ko, HTTP 200, illisible par l'outil de ce poste),
`en.wikipedia.org/wiki/RGBE_image_format` (magic `23 3f 52 41 44 49 41 4e 43
45 0a`, `fR = R x 2^(E-128)`).
"""
from __future__ import annotations

import math

from PIL import Image

__all__ = ["MAGIC", "HDR_MAX_PIXELS", "SORTIE", "lire_entete", "decoder",
           "equirect_ldr"]

MAGIC = b"#?"
SORTIE = (1024, 512)          # même taille que les sept ambiances du dépôt

# GARDE DE TAILLE, ET ELLE EST CHIFFRÉE. Le décodage garde 4 octets par pixel
# en mémoire (les quatre plans) : un 4096x2048 coûte 33 Mo, un 8192x4096 en
# coûterait 134, et un 16k 537. Comme la sortie fait de toute façon 1024x512,
# refuser au-delà de 12 Mpx ne coûte rien à personne et évite de manger la
# mémoire d'une machine qui rend une vidéo à côté.
HDR_MAX_PIXELS = 12_000_000


def _ligne(data: bytes, i: int) -> tuple[str, int]:
    j = data.find(b"\n", i)
    if j < 0:
        raise ValueError("HDR : en-tête tronqué (aucune fin de ligne)")
    return data[i:j].decode("latin-1"), j + 1


def lire_entete(data: bytes) -> tuple[dict, int]:
    """L'en-tête, la résolution, et l'offset du PREMIER octet de pixel."""
    if not data.startswith(MAGIC):
        raise ValueError("HDR : ce fichier ne commence pas par « #? » — ce "
                         "n'est pas un Radiance (.hdr)")
    entete: dict = {}
    signature, i = _ligne(data, 0)
    entete["signature"] = signature.strip()
    while True:
        ligne, i = _ligne(data, i)
        s = ligne.strip()
        if not s:
            break
        if s.startswith("#"):
            continue
        if "=" in s:
            cle, _, val = s.partition("=")
            entete[cle.strip().upper()] = val.strip()
    fmt = entete.get("FORMAT", "32-bit_rle_rgbe")
    if "rgbe" not in fmt.lower():
        raise ValueError(
            f"HDR : FORMAT={fmt} — seul 32-bit_rle_rgbe est lu. Le XYZE "
            "demanderait une conversion colorimétrique que rien ici ne sait "
            "faire ; réexportez en RGBE.")
    res, i = _ligne(data, i)
    p = res.split()
    if len(p) != 4 or p[0] != "-Y" or p[2] != "+X":
        raise ValueError(
            f"HDR : ligne de résolution « {res.strip()} » — seule "
            "l'orientation standard « -Y h +X w » est lue (les sept autres "
            "orientations du format sont légales mais introuvables en "
            "pratique, et les deviner serait une image retournée sans un mot)")
    h, w = int(p[1]), int(p[3])
    if w <= 0 or h <= 0:
        raise ValueError(f"HDR : résolution {w}x{h} invalide")
    if w * h > HDR_MAX_PIXELS:
        raise ValueError(
            f"HDR : {w}x{h}, soit {w * h / 1e6:.0f} Mpx — au-delà de la garde "
            f"de {HDR_MAX_PIXELS // 10 ** 6} Mpx. L'ambiance ne fait de toute "
            f"façon que {SORTIE[0]}x{SORTIE[1]} : réexportez en 4k.")
    entete["width"], entete["height"] = w, h
    return entete, i


def _scanline(data: bytes, i: int, w: int, sortie: bytearray) -> int:
    """Décode UNE scanline en 4·w octets planaires (R…, G…, B…, E…)."""
    if i + 4 > len(data):
        raise ValueError("HDR : fichier tronqué (scanline manquante)")
    if data[i] == 255 and data[i + 1] == 255 and data[i + 2] == 255:
        raise ValueError(
            "HDR : ancien codage RLE (255 255 255 n) — plus aucun outil ne "
            "l'écrit depuis vingt ans. Réexportez depuis un logiciel récent.")
    if not (8 <= w <= 32767 and data[i] == 2 and data[i + 1] == 2
            and (data[i + 2] << 8 | data[i + 3]) == w):
        fin = i + 4 * w
        bloc = data[i:fin]
        if len(bloc) < 4 * w:
            raise ValueError("HDR : fichier tronqué (scanline plate)")
        for c in range(4):
            sortie[c * w:(c + 1) * w] = bloc[c::4]
        return fin
    i += 4
    for c in range(4):
        x, base = 0, c * w
        while x < w:
            if i >= len(data):
                raise ValueError("HDR : fichier tronqué (plan RLE)")
            n = data[i]
            i += 1
            if n > 128:
                n -= 128
                if x + n > w:
                    raise ValueError("HDR : répétition RLE hors scanline")
                sortie[base + x:base + x + n] = bytes([data[i]]) * n
                i += 1
            else:
                if n == 0 or x + n > w or i + n > len(data):
                    raise ValueError("HDR : bloc littéral RLE invalide")
                sortie[base + x:base + x + n] = data[i:i + n]
                i += n
            x += n
    return i


def decoder(data: bytes) -> tuple[int, int, bytearray]:
    """(largeur, hauteur, 4·w·h octets) — les plans R, G, B, E, RANGÉE PAR
    RANGÉE (pour la rangée y : R sur w octets, puis G, puis B, puis E).

    On rend des octets bruts et pas des flottants : 8 Mpx de triplets Python
    coûteraient 400 Mo et vingt secondes d'allocation, pour une image dont on
    ne gardera que 1024x512."""
    entete, i = lire_entete(data)
    w, h = entete["width"], entete["height"]
    plans = bytearray(4 * w * h)
    ligne = bytearray(4 * w)
    for y in range(h):
        i = _scanline(data, i, w, ligne)
        plans[y * 4 * w:(y + 1) * 4 * w] = ligne
    return w, h, plans


def _luts(plans: bytearray, w: int, h: int, gamma: float = 2.2) -> list:
    """256 LUT de 256 entrées : `_luts[E][M]` donne l'octet de sortie.

    L'EXPOSITION EST UNE MÉDIANE, PAS UN MAXIMUM, et c'est la seule décision
    de ce module. Un HDRI porte presque toujours un soleil des milliers de
    fois plus lumineux que le ciel : normaliser sur le maximum rendrait tout
    le reste noir, ce qui est exactement le contraire de ce qu'on veut d'une
    carte d'éclairage. La médiane de l'exposant partagé donne l'échelle de la
    SCÈNE. Courbe de Reinhard (`y = x / (1 + x)`) : elle ne sature jamais,
    donc le soleil reste un point clair au lieu d'une tache blanche à bord
    franc, ce qui compte pour un reflet.
    """
    hist = [0] * 256
    for y in range(h):
        base = y * 4 * w + 3 * w
        for e in plans[base:base + w]:
            hist[e] += 1
    n = sum(hist) or 1
    acc, med = 0, 128
    for e, c in enumerate(hist):
        acc += c
        if acc >= n * 0.5:
            med = e
            break
    if med == 0:                     # image entièrement noire
        med = 128
    # `s` ramène la luminance médiane à ~0,5 après Reinhard (x = 1)
    s = 2.0 ** (128 - med)
    inv = 1.0 / max(0.1, gamma)
    table = []
    for e in range(256):
        if e == 0:
            table.append(bytes(256))
            continue
        k = (2.0 ** (e - 128)) * s / 256.0
        table.append(bytes(
            min(255, int(round(255.0 * ((m + 0.5) * k / (1.0 + (m + 0.5) * k))
                               ** inv))) for m in range(256)))
    return table


def equirect_ldr(data: bytes, sortie: tuple = SORTIE) -> Image.Image:
    """Un `.hdr` -> l'équirectangulaire LDR RGB que le viewport sait lire.

    Échantillonnage au point à DEUX FOIS la taille de sortie, puis réduction
    en BOX : le premier reste une boucle Python (3 x 2,1 M consultations de
    LUT, mesuré sous 3 s), le second est en C et rend au moyennage ce que le
    point-à-point lui a pris. Un HDRI sert d'éclairage diffus : c'est
    l'intégrale qui compte, pas le pixel."""
    w, h, plans = decoder(data)
    ow, oh = int(sortie[0]), int(sortie[1])
    tw, th = ow * 2, oh * 2
    table = _luts(plans, w, h)
    brut = bytearray(3 * tw * th)
    for j in range(th):
        y = min(h - 1, j * h // th)
        base = y * 4 * w
        ligne_e = plans[base + 3 * w:base + 4 * w]
        for i in range(tw):
            x = min(w - 1, i * w // tw)
            t = table[ligne_e[x]]
            o = 3 * (j * tw + i)
            brut[o] = t[plans[base + x]]
            brut[o + 1] = t[plans[base + w + x]]
            brut[o + 2] = t[plans[base + 2 * w + x]]
    return Image.frombytes("RGB", (tw, th), bytes(brut)).resize(
        (ow, oh), Image.BOX)
```

- [ ] **Step 5 : relancer le banc et le voir vert**

```
python tests/test_hdr_reader.py
```

Attendu : cinq lignes `✓`, la ligne de budget, puis
`OK — 5 assertions groupées vertes (hdr_reader)`. Budget mesuré attendu :
2 à 5 s pour le 4096×2048.

- [ ] **Step 6 : ranger les ambiances personnelles à côté des sept**

Dans `backend/app/services/env_service.py`, ajouter en fin de fichier :

```python
# ── ambiances PERSONNELLES (R10c P2) ────────────────────────────────────────
#
# Elles vivent dans le MÊME dossier de cache que les sept générées, sous un
# préfixe réservé. Deux espaces de noms, un seul dossier : `env_path` reste le
# seul endroit qui compose un chemin d'ambiance, et la liste blanche des sept
# n'est pas touchée — c'est le PRÉFIXE qui autorise, pas une seconde liste qui
# dériverait de la première.
PERSO_PREFIX = "u_"
PERSO_INDEX = "personnelles.json"


def est_perso(nom) -> bool:
    n = str(nom or "")
    return n.startswith(PERSO_PREFIX) and n[len(PERSO_PREFIX):].isalnum()


def _perso_index() -> dict:
    import json
    p = _cache_dir() / PERSO_INDEX
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def perso_list() -> list[dict]:
    """[{name,label,perso:True}] des ambiances importées, plus récente
    d'abord — le disque fait foi : une entrée d'index sans JPEG n'est pas
    listée."""
    out = []
    for nom, meta in _perso_index().items():
        if est_perso(nom) and (_cache_dir() / f"{nom}.jpg").is_file():
            out.append({"name": nom, "label": str(meta.get("label") or nom),
                        "perso": True, "source": str(meta.get("source") or ""),
                        "created": str(meta.get("created") or "")})
    out.sort(key=lambda e: e["created"], reverse=True)
    return out


def perso_path(nom: str):
    """Le JPEG d'une ambiance personnelle, ou None."""
    if not est_perso(nom):
        return None
    p = _cache_dir() / f"{nom}.jpg"
    return p if p.is_file() else None


def perso_ajouter(label: str, image, source: str = "") -> dict:
    """Range une image équirectangulaire comme ambiance personnelle."""
    import json
    import uuid
    from datetime import datetime, timezone
    nom = PERSO_PREFIX + uuid.uuid4().hex[:10]
    d = _cache_dir()
    tmp = d / f"{nom}.tmp"
    image.convert("RGB").resize((ENV_W, ENV_H), Image.BICUBIC).save(
        tmp, "JPEG", quality=90, optimize=True, subsampling=1)
    tmp.replace(d / f"{nom}.jpg")
    idx = _perso_index()
    idx[nom] = {"label": str(label or "Ambiance")[:60],
                "source": str(source or "")[:120],
                "created": datetime.now(timezone.utc)
                                   .strftime("%Y-%m-%dT%H:%M:%SZ")}
    (d / PERSO_INDEX).write_text(json.dumps(idx, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    return {"name": nom, "label": idx[nom]["label"], "perso": True,
            "source": idx[nom]["source"], "created": idx[nom]["created"]}


def perso_supprimer(nom: str) -> bool:
    import json
    if not est_perso(nom):
        return False
    d = _cache_dir()
    p = d / f"{nom}.jpg"
    existait = p.is_file()
    try:
        p.unlink()
    except OSError:
        pass
    idx = _perso_index()
    if idx.pop(nom, None) is not None or existait:
        (d / PERSO_INDEX).write_text(
            json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
        return True
    return False
```

Compléter `__all__` (ligne 34) avec
`"PERSO_PREFIX", "est_perso", "perso_list", "perso_path", "perso_ajouter", "perso_supprimer"`,
et faire suivre `env_list()` (ligne 244) :

```python
def env_list() -> list[dict]:
    """Liste pour GET /api/materials/envs : les sept générées, puis les
    ambiances importées."""
    return ([{"name": e["name"], "label": e["label"], "perso": False}
             for e in ENVS] + perso_list())
```

Dans `backend/app/services/material_store.py`, `env_jpeg` (ligne 1834),
remplacer le début :

```python
    n = _coerce_enum(name, "", ENV_NAMES)
    if not n:
        raise ValueError(f"Environnement inconnu: {name!r}")
```

par :

```python
    # Les ambiances IMPORTÉES ont leur propre espace de noms (`u_<hex>`) et
    # leur fichier sur disque : `env_service` en est le seul juge, et la liste
    # blanche des sept générées reste intacte — deux espaces de noms, aucune
    # liste recopiée.
    try:
        from app.services import env_service as ES
        p = ES.perso_path(name)
        if p is not None:
            return p.read_bytes()
    except Exception as e:
        logger.warning(f"materials: ambiances personnelles indisponibles ({e})")
    n = _coerce_enum(name, "", ENV_NAMES)
    if not n:
        raise ValueError(f"Environnement inconnu: {name!r}")
```

- [ ] **Step 7 : les deux routes**

Dans `backend/app/api/routes.py`, après `get_material_env` (fin ligne 7300),
insérer :

```python
@router.post("/materials/envs")
async def add_material_env(file: UploadFile = File(...), label: str = Form("")):
    """Importe un HDRI personnel (.hdr) comme ambiance du viewport.

    `.exr` est refusé PAR SON NOM, et le message dit quoi faire : OpenEXR
    admet une dizaine de schémas de compression dont deux seulement
    retomberaient sur zlib. Un décodeur partiel qui échouerait un fichier sur
    deux APRÈS le téléversement serait une promesse fausse — mieux vaut le
    dire avant."""
    from app.services import env_service as ES
    from app.services import hdr_reader as HR
    nom = Path(file.filename or "").name
    bas = nom.lower()
    if bas.endswith(".exr"):
        raise HTTPException(400, "Les .exr ne sont pas lus : le format admet "
                                 "une dizaine de compressions différentes et "
                                 "aucune bibliothèque n'est embarquée. "
                                 "Réexportez en .hdr (Radiance).")
    data = await file.read()
    if bas.endswith((".jpg", ".jpeg", ".png")):
        # une équirectangulaire LDR toute faite : Pillow la lit, rien à décoder
        try:
            img = PILImage.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            raise HTTPException(400, f"Image illisible : {e}")
    elif bas.endswith(".hdr"):
        try:
            img = await asyncio.to_thread(HR.equirect_ldr, data)
        except ValueError as e:
            raise HTTPException(400, str(e))
    else:
        raise HTTPException(400, "Formats acceptés : .hdr (Radiance), .jpg, "
                                 ".png — une image équirectangulaire 2:1.")
    if img.size[0] < 2 * img.size[1] * 0.9 or img.size[0] > 2 * img.size[1] * 1.1:
        raise HTTPException(400, f"Une équirectangulaire fait deux fois plus "
                                 f"large que haute ; celle-ci fait "
                                 f"{img.size[0]}x{img.size[1]}.")
    env = await asyncio.to_thread(ES.perso_ajouter,
                                  (label or Path(nom).stem or "Ambiance"),
                                  img, nom)
    return {"env": env}


@router.delete("/materials/envs/{name}")
async def delete_material_env(name: str):
    """Supprime une ambiance IMPORTÉE. Les sept générées ne se suppriment
    pas : elles se regénèrent, il n'y a rien à perdre."""
    from app.services import env_service as ES
    if not ES.est_perso(name):
        raise HTTPException(400, "Seules les ambiances importées se "
                                 "suppriment.")
    if not await asyncio.to_thread(ES.perso_supprimer, name):
        raise HTTPException(404, "Ambiance introuvable")
    return {"ok": True}
```

Ajouter `import io` en tête de `add_material_env` (même maison que les six
autres fonctions de ce fichier).

- [ ] **Step 8 : l'écran**

Dans `index.html`, sous la ligne `<div class="chips" id="envChips"></div>`
(ligne 192), ajouter :

```html
        <div class="row">
          <label class="btn ghost sm" for="envFile" title="Importer un HDRI
            équirectangulaire (.hdr) ou une image 2:1">＋ HDRI…</label>
          <input type="file" id="envFile" accept=".hdr,.jpg,.jpeg,.png"
                 class="hidden">
          <button class="btn ghost sm" id="envDel"
                  title="Supprimer l'ambiance importée sélectionnée">🗑</button>
        </div>
```

Dans `materialforge.js`, `loadEnvs` (ligne 501) garde `perso` sur chaque
entrée ; `renderEnvChips` (ligne 3192) marque les puces personnelles d'une
classe `perso` ; et ajouter dans `wire()` :

```js
  $("#envFile").addEventListener("change", async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    fd.append("label", f.name.replace(/\.[^.]+$/, ""));
    try {
      /* `api.json` sait déjà envoyer un FormData tel quel (voir sa branche
         `body instanceof FormData`) : pas de second chemin d'envoi. */
      const d = await api.json("POST", "/materials/envs", fd);
      await loadEnvs();
      setEnv(d.env.name);
      toast(`Ambiance « ${d.env.label} » importée.`);
    } catch (err) { apiFail(err, "import d'ambiance"); }
    e.target.value = "";
  });
  $("#envDel").addEventListener("click", async () => {
    const n = state.env;
    if (!n || !n.startsWith("u_")) {
      toast("Les sept ambiances du studio ne se suppriment pas.", true);
      return;
    }
    await api.del(`/materials/envs/${encodeURIComponent(n)}`);
    await loadEnvs();
    setEnv("studio");
  });
```

- [ ] **Step 9 : vérifier à l'écran, puis commit**

Importer un `.hdr` réel (Poly Haven en propose en CC0) et vérifier que le
reflet du métal change dans le viewport. Puis :

```bash
git add backend/app/services/hdr_reader.py backend/app/services/env_service.py backend/app/services/material_store.py backend/app/api/routes.py frontend/materialforge/index.html frontend/materialforge/materialforge.js backend/tests/test_hdr_reader.py
git commit -m 'matieres P2 : les HDRI personnels, un decodeur RGBE en stdlib

Un Radiance .hdr est un en-tete texte et des quadruplets RGBE : trois octets
de mantisse et UN exposant partage. Aucune compression d entropie, aucun
flottant a decoder — du decoupage d octets suffit, et c est tout l interet du
format. Les deux codages de scanline sont lus, plat et RLE adaptatif ; le banc
ECRIT lui-meme les deux, donc il prouve le decodeur contre une specification
et non contre lui-meme (ecart relatif max 2 % sur la reconstruction, la
quantification 8 bits de la mantisse).

L exposition est une MEDIANE, pas un maximum : un HDRI porte un soleil des
milliers de fois plus lumineux que le ciel, et normaliser sur le maximum
rendrait tout le reste noir — le contraire de ce qu on attend d une carte d
eclairage. Reinhard ensuite, qui ne sature jamais.

Quatre refus nommes plutot que devines : l ancien RLE 255 255 255 n, le XYZE,
les orientations non standard, et la garde de 12 Mpx (le decodage garde 4
octets par pixel ; la sortie fait de toute facon 1024x512). Le .exr est refuse
PAR SON NOM : dix schemas de compression dont deux seulement retomberaient sur
zlib, et un decodeur qui echoue un fichier sur deux apres le televersement
serait une promesse fausse.

Deux espaces de noms, un seul dossier de cache : la liste blanche des sept
ambiances generees n est pas touchee, c est le prefixe u_ qui autorise.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 8 : P2 — la comparaison côte à côte, sous la même ambiance

**Files:**
- Modify: `frontend/materialforge/index.html:140-170` (le viewport gagne un second `<model-viewer>`), `:110-116` (barre du haut)
- Modify: `frontend/materialforge/materialforge.js:1029-1047` (`setViewportSrc`), `:239-268` (`state`), `:3272` (`wire`)
- Modify: `frontend/materialforge/materialforge.css`
- Test: `backend/tests/test_materialforge_ecran.py` (nouvelle section)

- [ ] **Step 1 : ajouter la section rouge au banc**

Dans `backend/tests/test_materialforge_ecran.py`, insérer avant la ligne
`print(f"\nOK — {PASS} assertions…` :

```python
# ══ 6 · la comparaison côte à côte ═════════════════════════════════════════
for ident in ("mv", "mvB", "cmpBtn", "cmpPick"):
    assert f'id="{ident}"' in HTML, ident
assert HTML.count('<model-viewer') == 2, HTML.count('<model-viewer')
ok("index.html : DEUX model-viewer, un bouton de comparaison et un "
   "sélecteur de seconde matière")

# La même ambiance des DEUX côtés : c'est tout l'objet d'une comparaison.
# `applyEnvToViewers` est déjà la fonction qui pose l'environnement — elle
# doit voir les deux, et le banc lit sa liste de cibles.
corps_env = JS_CODE.split("function applyEnvToViewers()", 1)[1] \
                   .split("\n}\n", 1)[0]
assert "#mvB" in corps_env or "mvB" in corps_env, corps_env[:400]
ok("applyEnvToViewers pose l'environnement sur LES DEUX viewers — comparer "
   "sous deux ambiances différentes ne comparerait rien")

# Un seul GLB par matière : la comparaison ne doit pas doubler le coût de
# construction, elle réutilise `glbUrl`.
corps_cmp = JS_CODE.split("function setCompare(", 1)[1].split("\n}\n", 1)[0]
assert "glbUrl(" in corps_cmp, corps_cmp[:400]
ok("la comparaison réutilise glbUrl : aucun second chemin de construction "
   "de GLB à maintenir")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_materialforge_ecran.py
```

Attendu : `AssertionError: mvB`.

- [ ] **Step 3 : le balisage**

Dans `index.html`, dans `.vp-stage` (ligne 153), après le premier
`<model-viewer id="mv" …>`, ajouter un jumeau caché :

```html
        <model-viewer id="mvB" class="hidden" camera-controls
                      touch-action="pan-y" shadow-intensity="0"
                      interaction-prompt="none" exposure="1"
                      camera-orbit="32deg 72deg 102%" field-of-view="32deg">
        </model-viewer>
```

et, dans la barre du viewport (ligne 142, `#vpBar`), après les puces de
maillage :

```html
        <button class="chip" id="cmpBtn" type="button"
                title="Comparer deux matières sous la même ambiance">⇔ Comparer</button>
        <select id="cmpPick" class="sortsel hidden"
                title="Seconde matière de la comparaison"></select>
```

- [ ] **Step 4 : le comportement**

Dans `materialforge.js`, ajouter `compare: null` à `state` (ligne 239) et,
juste avant `wire()` :

```js
/* ── comparaison côte à côte (P2) ───────────────────────────────────────────
   DEUX viewers, UNE ambiance, UNE orbite. Le point d'une comparaison est que
   la seule variable soit la matière : l'environnement et la caméra sont donc
   copiés du premier viewer vers le second à chaque changement, et jamais
   réglés séparément. */
function setCompare(id) {
  state.compare = id || null;
  const b = $("#mvB");
  const stage = $("#vpStage");
  stage.classList.toggle("split", !!id);
  b.classList.toggle("hidden", !id);
  $("#cmpPick").classList.toggle("hidden", !id);
  if (!id) return;
  const m = matById(id);
  if (!m) { setCompare(null); return; }
  const url = glbUrl(m, state.res, state.mesh, false);
  if (url) b.src = url;
  b.cameraOrbit = $("#mv").cameraOrbit;
  b.fieldOfView = $("#mv").fieldOfView;
  applyEnvToViewers();
}
```

Dans `applyEnvToViewers` (ligne 433), remplacer la liste des cibles par
`[$("#mv"), $("#mvB")].concat(cartes)` — la fonction pose déjà
`environmentImage`, `skyboxImage` et `exposure` sur chaque cible ; elle en a
maintenant une de plus.

Dans `wire()` :

```js
  $("#cmpBtn").addEventListener("click", () => {
    if (state.compare) { setCompare(null); return; }
    const sel = $("#cmpPick");
    sel.innerHTML = state.materials
      .filter((m) => m.id !== state.open)
      .map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`)
      .join("");
    setCompare(sel.value || null);
  });
  $("#cmpPick").addEventListener("change", (e) => setCompare(e.target.value));
  $("#mv").addEventListener("camera-change", () => {
    if (!state.compare) return;
    $("#mvB").cameraOrbit = $("#mv").cameraOrbit;
    $("#mvB").fieldOfView = $("#mv").fieldOfView;
  });
```

- [ ] **Step 5 : le style**

Ajouter à `materialforge.css` :

```css
/* ── comparaison côte à côte (P2) ───────────────────────────────────────── */
.vp-stage.split { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }
.vp-stage.split > model-viewer { width: 100%; height: 100%; min-width: 0; }
.vp-stage.split::after {
  content: ""; position: absolute; inset: 0 auto 0 50%; width: 1px;
  background: var(--line, #222831); pointer-events: none;
}
```

- [ ] **Step 6 : relancer le banc, vérifier à l'écran, commit**

```
python tests/test_materialforge_ecran.py
```

Attendu : huit lignes `✓`. À l'écran : deux sphères côte à côte, une seule
orbite (tourner à gauche tourne à droite), la même ambiance des deux côtés.

```bash
git add frontend/materialforge/index.html frontend/materialforge/materialforge.js frontend/materialforge/materialforge.css backend/tests/test_materialforge_ecran.py
git commit -m 'matieres P2 : comparer deux matieres sous la meme ambiance

Le point d une comparaison est que la SEULE variable soit la matiere :
l ambiance et l orbite sont donc copiees du premier viewer vers le second a
chaque changement, jamais reglees separement. Le banc lit applyEnvToViewers
et exige qu elle voie les deux — comparer sous deux ambiances differentes ne
comparerait rien.

La comparaison reutilise glbUrl : aucun second chemin de construction de GLB
a maintenir, et le cache disque de l apercu sert les deux cotes.

Cout de patch : ZERO, /materialforge/ est hors bundle.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---
### Task 9 : P5 — la hauteur physique de la carte height, jusqu'au relief imprimé

**Files:**
- Modify: `backend/app/services/material_store.py:731-812` (`normalize_material`), `:1308-1372` (`_readme`), `:1477` (`export_manifest`), `:45-64` (`__all__`)
- Modify: `backend/app/api/routes.py:7458-7514` (`patch_material`)
- Modify: `backend/app/services/cards/forge3d.py:175-180` (constantes), `:817-820` (branche `relief` de `clean_graph`), `:484-490` (bloc `/info`)
- Modify: `frontend/materialforge/materialforge.js:161-211` (`GROUPS`)
- Test: `backend/tests/test_material_height_mm.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_material_height_mm.py` :

```python
# -*- coding: utf-8 -*-
"""Material Forge P5 — la carte height DÉCLARE sa hauteur physique, et le
relief imprimé la consomme.

BANC-MIROIR : la dernière assertion ne lit pas un paramètre, elle mesure la
GÉOMÉTRIE produite — l'étendue en z des positions du maillage de relief.

Run (depuis backend/) : python tests/test_material_height_mm.py
"""
import io
import json
import os
import pathlib
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import material_store as MS                  # noqa: E402
from app.services.cards import forge3d                         # noqa: E402
from app.services.cards import forge3d_scene as FS             # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def fabriquer(h_mm=None):
    mat = MS.create_material(
        name="Vitrail bleu", prompt="stained glass",
        full_prompt=MS.build_full_prompt("stained glass"),
        source={"kind": "prompt", "model": "flux", "filename": None},
        res=64, seamless=True, seam={"before": 8.0, "after": 0.0})
    haut = Image.new("L", (64, 64), 0)
    for y in range(20, 44):
        for x in range(64):
            haut.putpixel((x, y), 255)
    MS.save_maps(mat["id"], {
        "basecolor": Image.new("RGB", (64, 64), (40, 80, 160)),
        "height": haut, "ao": Image.new("L", (64, 64), 220),
        "roughness": Image.new("L", (64, 64), 160),
        "metallic": Image.new("L", (64, 64), 10),
        "normal": Image.new("RGB", (64, 64), (128, 128, 255)),
        "emissive": Image.new("RGB", (64, 64), (0, 0, 0)),
        "orm": Image.new("RGB", (64, 64), (220, 160, 10))})
    m = MS.read_material(mat["id"])
    if h_mm is not None:
        m["height_mm"] = h_mm
        MS.write_material(m)
    return MS.read_material(mat["id"]), haut


# ══ 1 · le champ existe, il est borné, il ne lève jamais ═══════════════════
m, _ = fabriquer()
assert m["height_mm"] == 0.0, m["height_mm"]
for brut, veut in ((2.4, 2.4), ("3.5", 3.5), (-1, 0.0), (999, 20.0),
                   (None, 0.0), ("abc", 0.0), (float("nan"), 0.0)):
    got = MS.normalize_material({"height_mm": brut}, m["id"])["height_mm"]
    assert abs(got - veut) < 1e-9, (brut, got, veut)
ok("height_mm : défaut 0 (non renseigné), borné à [0, 20] mm, jamais "
   "d'exception sur une entrée pourrie")

# ══ 2 · la fiche, material.json et le LISEZMOI le portent ══════════════════
m, haut = fabriquer(2.4)
maps = MS.load_maps(m["id"])
zip_octets = MS.export_zip(m, MS.bake_levels(maps, m["props"]), "standard")
with zipfile.ZipFile(io.BytesIO(zip_octets)) as z:
    lisez = z.read("LISEZMOI.txt").decode("utf-8")
    mj = json.loads(z.read("material.json").decode("utf-8"))
assert mj["height_mm"] == 2.4, mj.get("height_mm")
assert "2.4 mm" in lisez and "height" in lisez.lower(), lisez[:900]
mani = MS.export_manifest(m, "zip", "standard")
assert mani["height_mm"] == 2.4, mani.get("height_mm")
ok("2,4 mm dans meta.json, material.json, le LISEZMOI et le bordereau")

# ══ 3 · le nœud relief prend la hauteur de SA matière ══════════════════════
def profondeur(mid, demande=None):
    g = {"nodes": [{"id": "r1", "kind": "relief", "mat": mid,
                    **({"depth_mm": demande} if demande is not None else {})}],
         "edges": []}
    return forge3d.clean_graph(g)["nodes"][0]

n = profondeur(m["id"])
assert abs(n["depth_mm"] - 2.4) < 1e-9, n
assert n.get("depth_mm_source") == "matiere", n
n = profondeur(m["id"], 1.1)
assert abs(n["depth_mm"] - 1.1) < 1e-9, n
assert n.get("depth_mm_source") == "graphe", n
sans, _ = fabriquer()
n = profondeur(sans["id"])
assert abs(n["depth_mm"] - 0.6) < 1e-9, n
assert n.get("depth_mm_source") == "defaut", n
gros, _ = fabriquer(9.0)
n = profondeur(gros["id"])
assert abs(n["depth_mm"] - forge3d.RELIEF_DEPTH_MM_MAX) < 1e-9, n
assert n.get("depth_mm_clamped") is True, n
ok("relief : 2,4 mm de la matière, 1,1 mm si le graphe le dit, 0,6 mm sans "
   "matière renseignée, et 9 mm écrêté à 3,0 EN LE DISANT")

# ══ 4 · la GÉOMÉTRIE, pas le paramètre ═════════════════════════════════════
maille = FS.relief_mesh(haut, 60.0, 60.0, profondeur(m["id"])["depth_mm"],
                        0.3, 48)
z = maille["positions"][2::3]
assert abs(min(z) - 0.0) < 1e-9, min(z)
assert abs(max(z) - (0.3 + 2.4)) < 1e-6, max(z)
mes = FS.mesh_measures(maille)
assert mes["closed"] is True and mes["volume"] > 0, mes
ok(f"maillage de relief : z va de 0 à {max(z):.3f} mm = base 0,3 + hauteur "
   f"2,4 de la matière ; solide fermé, volume positif")

# ══ 5 · /info publie le défaut, sans le recopier à l'écran ═════════════════
info = forge3d.info() if hasattr(forge3d, "info") else None
assert info is None or info["forge3d"]["relief_depth_mm_default"] == 0.6, info
ok("le défaut historique de 0,6 mm est PUBLIÉ, pas écrit en dur dans l'écran")

print(f"\nOK — {PASS} assertions groupées vertes (hauteur physique)")
```

> Le Step 4 du banc appelle `forge3d.info()` si elle existe ; si le bloc
> `/info` de ce module est produit par une autre fonction (le voir à la ligne
> 478-530 avant d'écrire), remplacer l'appel par la lecture de la clé dans
> cette fonction-là, sans recopier la valeur.

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_material_height_mm.py
```

Attendu : `KeyError: 'height_mm'`.

- [ ] **Step 3 : la matière déclare sa hauteur**

Dans `material_store.py`, `normalize_material`, ajouter au dictionnaire rendu,
juste après `"res": clean_res(raw.get("res")),` :

```python
        # ── hauteur PHYSIQUE de la carte height (R10c P5) ──────────────────
        # En millimètres, et SEULEMENT pour l'impression : c'est la réponse 7
        # de R10c, et E1 en est la conséquence — aucun moteur de jeu ne
        # recevra cette valeur, parce qu'aucun n'en fait la même chose.
        # 0 = non renseigné (et non « plat » : une matière fraîche n'a jamais
        # été mesurée, ce n'est pas pareil que d'être mesurée à zéro).
        # Plafond 20 mm : au-delà, ce n'est plus un relief de surface mais une
        # pièce, et une pièce se modélise dans l'Établi.
        "height_mm": _coerce_float(raw.get("height_mm"), 0.0, 0.0, 20.0),
```

Dans `_readme`, dans la liste `lines = [...]`, après la ligne
`f"Résolution : {res}x{res}",` :

```python
        (f"Hauteur physique de height.png : {mat.get('height_mm')} mm "
         f"(relief d'impression ; aucun moteur de jeu ne la reçoit)"
         if mat.get("height_mm") else
         "Hauteur physique de height.png : non renseignée"),
```

Dans `export_manifest`, ajouter au dictionnaire rendu (auprès de
`"weigh_rule": WEIGH_RULE,`) :

```python
        "height_mm": mat.get("height_mm", 0.0),
```

Ajouter `"clean_prep", "prep_note"` sont déjà là ; rien de plus à exporter
(`height_mm` est une clé, pas une fonction).

Dans `routes.py`, `patch_material`, après le bloc `if "name" in body:` :

```python
    if "height_mm" in body:
        mat["height_mm"] = MS.normalize_material(
            {"height_mm": body.get("height_mm")}, mid)["height_mm"]
```

- [ ] **Step 4 : le relief la consomme**

Dans `backend/app/services/cards/forge3d.py`, après `RELIEF_GRID_DEFAULT`
(ligne 180) :

```python
# Le défaut HISTORIQUE, gardé pour une matière qui n'a pas été mesurée. Il est
# publié par /info : l'écran ne le recopie pas.
RELIEF_DEPTH_MM_DEFAUT = 0.6
```

Remplacer la branche `relief` de `clean_graph` (lignes 817-820) :

```python
        elif n["kind"] == "relief":
            node["depth_mm"] = _num(n.get("depth_mm"), 0.6, 0.05, RELIEF_DEPTH_MM_MAX)
            node["base_mm"] = _num(n.get("base_mm"), 0.3, *RELIEF_BASE_MM)
            node["grid"] = int(_num(n.get("grid"), RELIEF_GRID_DEFAULT, *RELIEF_GRID))
```

par :

```python
        elif n["kind"] == "relief":
            # LA HAUTEUR VIENT DE LA MATIÈRE QUAND ELLE EST MESURÉE (R10c P5).
            # Le 0,6 mm historique était un chiffre AVEUGLE : la même valeur
            # pour un vitrail de 2,4 mm et pour une gravure de 0,2, donc un
            # relief faux dans les deux cas. La matière porte désormais sa
            # hauteur physique ; le graphe garde le dernier mot (un
            # `depth_mm` explicite l'emporte), et l'écrêtage aux bornes du
            # nœud est DIT plutôt que subi.
            mid_r = str(n.get("mat") or "")
            node["mat"] = mid_r if material_store.is_valid_mid(mid_r) else None
            voulu, source = RELIEF_DEPTH_MM_DEFAUT, "defaut"
            if node["mat"]:
                mat_r = material_store.read_material(node["mat"]) or {}
                if float(mat_r.get("height_mm") or 0.0) > 0.0:
                    voulu, source = float(mat_r["height_mm"]), "matiere"
            if n.get("depth_mm") is not None:
                voulu, source = n.get("depth_mm"), "graphe"
            node["depth_mm"] = _num(voulu, RELIEF_DEPTH_MM_DEFAUT, 0.05,
                                    RELIEF_DEPTH_MM_MAX)
            node["depth_mm_source"] = source
            node["depth_mm_clamped"] = (
                isinstance(voulu, (int, float))
                and abs(float(voulu) - node["depth_mm"]) > 1e-9)
            node["base_mm"] = _num(n.get("base_mm"), 0.3, *RELIEF_BASE_MM)
            node["grid"] = int(_num(n.get("grid"), RELIEF_GRID_DEFAULT, *RELIEF_GRID))
```

Dans le bloc `/info` (ligne 484), ajouter à côté de `"relief_depth_mm_max"` :

```python
                               "relief_depth_mm_default": RELIEF_DEPTH_MM_DEFAUT,
```

- [ ] **Step 5 : le curseur dans l'inspecteur**

Dans `materialforge.js`, ajouter au groupe « Surface » de `GROUPS`
(ligne 161) une ligne :

```js
    { k: "height_mm", label: "Hauteur physique", unit: "mm", min: 0, max: 20,
      step: 0.1, top: true,
      help: "Ce que représentent, en millimètres, les 255 niveaux de la carte "
          + "height. Sert UNIQUEMENT à l'impression 3D (relief) : aucun "
          + "moteur de jeu ne la reçoit, ils ne s'accordent pas sur ce que "
          + "veut dire un déplacement. 0 = non mesurée." },
```

`top: true` marque la ligne comme appartenant à la matière et non à `props` :
dans `setProp` (ligne 2443), une ligne `top` part dans `queuePatch({ name:
undefined, top: { height_mm: v } })`, et `flushPatch` (ligne 2468) fusionne ce
bloc à la racine du corps `PATCH` au lieu de `props`.

- [ ] **Step 6 : relancer le banc et les voisins, puis commit**

```
python tests/test_material_height_mm.py
python tests/test_materials_api.py
python tests/test_material_truth.py
```

Attendu : `OK — 5 assertions groupées vertes (hauteur physique)`, les deux
autres inchangés.

```bash
git add backend/app/services/material_store.py backend/app/api/routes.py backend/app/services/cards/forge3d.py frontend/materialforge/materialforge.js backend/tests/test_material_height_mm.py
git commit -m 'matieres P5 : la carte height declare ses millimetres

Le noeud relief du Forge 3D posait 0,6 mm PAR DEFAUT, aveuglement : la meme
valeur pour un vitrail de 2,4 mm et pour une gravure de 0,2, donc un relief
faux dans les deux cas. La matiere porte desormais sa hauteur physique, le
graphe garde le dernier mot, et l ecretage aux bornes du noeud est DIT
(depth_mm_source vaut matiere, graphe ou defaut ; depth_mm_clamped dit quand
9 mm devient 3).

Millimetres et impression SEULEMENT — c est la reponse 7 de R10c, et E1 en
est la consequence directe : aucun moteur de jeu ne recoit cette valeur,
parce qu aucun n en fait la meme chose. Le LISEZMOI le dit noir sur blanc.

La derniere assertion du banc ne lit pas un parametre : elle mesure l etendue
en z des positions du maillage produit — 0 a base 0,3 plus hauteur 2,4 — et
verifie que le solide reste ferme, volume positif.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 10 : P4 — trente matières CC0, téléchargées AU BUILD

**Files:**
- Create: `scripts/build_materials_catalog.py`
- Create: `backend/app/services/starter_materials.py`
- Modify: `backend/app/services/material_store.py:151` (`SOURCE_KINDS`), `:731-812` (`normalize_material` : bloc `credit`), `:1308` (`_readme`)
- Modify: `backend/app/api/routes.py` (trois routes, après `list_material_presets` ligne 7222)
- Modify: `frontend/materialforge/materialforge.js:1313-1388` (`emptyHtml`, `wireEmpty`)
- Test: `backend/tests/test_starter_materials.py`

- [ ] **Step 1 : relire la licence et l'API AVANT de choisir quoi que ce soit**

1. `WebFetch` `https://polyhaven.com/license`, invite : *« que dit exactement cette page sur la licence des assets, l'usage commercial et l'attribution ? »*. Attendu : CC0, usage commercial libre, aucune attribution exigée.
2. `WebFetch` `https://github.com/Poly-Haven/Public-API/blob/master/ToS.md`. Attendu, relu le 03/09/2026 : « The API is free to access and use by anyone… for any purpose, including commercial use, at no charge » et « All API calls must be made with a unique "Referer" header or user-agent that matches your software name ».
3. `WebFetch` `https://polyhaven.com/our-api`. Attendu : l'annonce du **18 juillet 2026** qui ouvre l'API à l'usage commercial.
4. `WebFetch` `https://api.polyhaven.com/files/rusty_metal`. Attendu : la structure `carte -> résolution -> format -> {size, md5, url}` citée en « Références vérifiées ».

**Ce que ces lectures changent, et il faut le dire** : R10c écrivait que l'usage commercial de l'API était *interdit sans licence*. Ce n'est plus vrai depuis le 18/07/2026. La décision — **catalogue téléchargé au build, jamais d'appel depuis l'application** — ne change pas pour autant, et la section « Écarté » de ce plan dit pourquoi avec la nouvelle raison.

- [ ] **Step 2 : écrire le banc qui échoue (aucun réseau)**

Créer `backend/tests/test_starter_materials.py` :

```python
# -*- coding: utf-8 -*-
"""Catalogue de démarrage des matières — R10c P4, trente matières CC0.

AUCUN RÉSEAU : le banc fabrique un faux catalogue sur disque, exactement dans
la forme que le script de build produit, puis exerce le module runtime et le
`--check` du script. La liste des trente identifiants est vérifiée ICI, en
littéral — c'est un contrat, pas un détail de mise en œuvre.

Run (depuis backend/) : python tests/test_starter_materials.py
"""
import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import material_store as MS                  # noqa: E402
import app.services.starter_materials as SM                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = RACINE / "scripts" / "build_materials_catalog.py"

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# ══ 1 · trente identifiants, six familles, aucun doublon ═══════════════════
sys.path.insert(0, str(RACINE / "scripts"))
build = importlib.import_module("build_materials_catalog")
slugs = [a["slug"] for a in build.ASSETS]
assert len(slugs) == 30, len(slugs)
assert len(set(slugs)) == 30, "doublon dans la liste"
familles = sorted({a["family"] for a in build.ASSETS})
assert familles == ["bois", "beton_terrain", "metaux", "murs", "sols",
                    "tissus"], familles
for a in build.ASSETS:
    assert a["name"] and a["family"] and a["slug"].islower(), a
    assert " " not in a["slug"], a
ok(f"trente identifiants Poly Haven distincts, six familles "
   f"({', '.join(familles)})")

# ══ 2 · le faux catalogue, dans la forme exacte du build ═══════════════════
DOSSIER = pathlib.Path(_tmp) / "catalogue"
(DOSSIER / "brick_wall_001").mkdir(parents=True)
for carte, couleur in (("basecolor", (150, 70, 60)), ("normal", (128, 128, 255)),
                       ("roughness", (170, 170, 170))):
    Image.new("RGB", (128, 128), couleur).save(
        DOSSIER / "brick_wall_001" / f"{carte}.jpg", quality=82)
CAT = {"version": 1, "generated_at": "2026-09-03T00:00:00Z",
       "source": {"name": "Poly Haven", "url": "https://polyhaven.com",
                  "license": "CC0-1.0",
                  "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"},
       "families": [{"id": "murs", "name": "Murs & briques", "count": 1}],
       "materials": [{"id": "brick_wall_001", "name": "Brick Wall 001",
                      "family": "murs", "tags": ["red", "rough"],
                      "authors": {"Rob Tuytel": "Processing"},
                      "scale": "1.5x1.5", "dimensions": [3000, 3000],
                      "maps": {"basecolor": "brick_wall_001/basecolor.jpg",
                               "normal": "brick_wall_001/normal.jpg",
                               "roughness": "brick_wall_001/roughness.jpg"},
                      "bytes": 0}]}
CAT["materials"][0]["bytes"] = sum(
    (DOSSIER / v).stat().st_size for v in CAT["materials"][0]["maps"].values())
(DOSSIER / "catalog.json").write_text(json.dumps(CAT, ensure_ascii=False),
                                      encoding="utf-8")
(DOSSIER / "NOTICE.txt").write_text("Poly Haven — CC0 1.0\n", encoding="utf-8")

SM.STARTER_DIR = DOSSIER
SM.CATALOG_FILE = DOSSIER / "catalog.json"
SM.reset_cache()
cat = SM.load()
assert cat["available"] is True and len(cat["materials"]) == 1
assert SM.browse(query="brick") and not SM.browse(query="zzz")
assert SM.browse(family="murs") and not SM.browse(family="metaux")
ok("catalogue lu, recherche par nom et filtre par famille")

# ══ 3 · un import devient une matière ORDINAIRE ════════════════════════════
faits = SM.importer(["brick_wall_001"])
assert len(faits) == 1
mid = faits[0]["id"]
m = MS.read_material(mid)
assert MS.MID_RE.match(mid), mid
assert m["maps"] == list(MS.MAP_KINDS), m["maps"]
assert m["source"]["kind"] == "catalog", m["source"]
assert m["credit"]["license"] == "CC0-1.0", m["credit"]
assert "Poly Haven" in m["credit"]["source"], m["credit"]
assert "Rob Tuytel" in m["credit"]["author"], m["credit"]
d = MS.material_dir(mid)
for k in MS.MAP_KINDS:
    assert (d / f"{k}.png").is_file(), k
assert m["map_stats"], "les statistiques de map n'ont pas été calculées"
ok(f"import : {mid} porte les HUIT cartes sur disque — trois mesurées par "
   f"Poly Haven, cinq dérivées localement — et son crédit CC0")

# ══ 4 · un identifiant inconnu se refuse en le nommant ═════════════════════
try:
    SM.importer(["pas_dans_le_catalogue"])
    raise AssertionError("aurait dû lever")
except SM.StarterError as e:
    assert e.status == 404 and "pas_dans_le_catalogue" in e.message, e.message
ok(f"identifiant inconnu : 404 nommé — « {e.message[:60]} »")

# ══ 5 · --check concorde, et rougit quand un fichier manque ════════════════
r = subprocess.run([sys.executable, str(SCRIPT), "--check", "--out",
                    str(DOSSIER)], capture_output=True, timeout=300)
sortie = r.stdout.decode("utf-8", "replace")
assert r.returncode == 0, sortie + r.stderr.decode("utf-8", "replace")
assert "concordent" in sortie, sortie
(DOSSIER / "brick_wall_001" / "normal.jpg").unlink()
r2 = subprocess.run([sys.executable, str(SCRIPT), "--check", "--out",
                     str(DOSSIER)], capture_output=True, timeout=300)
assert r2.returncode == 1, r2.stdout
assert "MANQUANT" in r2.stdout.decode("utf-8", "replace")
ok("--check : vert quand tout est là, rouge et parlant quand une carte "
   "manque — la garde de packaging tient")

print(f"\nOK — {PASS} assertions groupées vertes (catalogue de matières CC0)")
```

- [ ] **Step 3 : lancer le banc et le voir rouge**

```
python tests/test_starter_materials.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.starter_materials'`.

- [ ] **Step 4 : écrire le script de build**

Créer `scripts/build_materials_catalog.py` :

```python
# -*- coding: utf-8 -*-
# scripts/build_materials_catalog.py
"""Fabrique le catalogue de démarrage des MATIÈRES depuis Poly Haven (CC0).

POURQUOI AU BUILD ET PAS À L'EXÉCUTION. L'application est un studio LOCAL : un
écran de matières qui exige le réseau pour montrer quoi que ce soit trahit sa
promesse, et une API tierce qui bouge casserait l'écran d'un utilisateur qui
n'a rien demandé. Les assets sont CC0 — donc redistribuables sans condition —
et l'API autorise depuis le 18/07/2026 l'usage commercial (ToS relues le
03/09/2026). Rien n'oblige donc à appeler quoi que ce soit depuis le produit :
on télécharge une fois, ici, et l'application n'a plus jamais besoin du
réseau. Même doctrine que `build_starter_catalog.py` pour les sons Kenney.

TROIS CARTES EMBARQUÉES, CINQ DÉRIVÉES, et c'est un choix mesuré. Poly Haven
publie jusqu'à onze cartes par matière ; trois seulement portent une
information qu'une dérivation ne peut pas inventer — la couleur, la normale
MESURÉE (un relief photogrammétré, pas une estimation depuis l'albédo) et la
rugosité. L'occlusion, la hauteur, le métal, l'émissif et l'ORM se dérivent
localement, gratuitement et hors ligne par `pbr_service` : les embarquer
doublerait le poids de l'installeur pour zéro information. La fiche de chaque
matière importée le DIT.

Sortie : backend/app/assets/materials/ (dans le paquet Python, donc embarquée
par l'installeur qui recopie {#AppRoot}\\* — rien à ajouter au .iss) :

    catalog.json          index unique lu par starter_materials.py
    NOTICE.txt            sources, auteurs et licence (remerciement, pas
                          obligation : la CC0 n'exige aucune attribution)
    <slug>/basecolor.jpg  1024x1024, JPEG q82
    <slug>/normal.jpg     idem — carte MESURÉE, convention OpenGL (nor_gl)
    <slug>/roughness.jpg  idem

Usage :
  python scripts/build_materials_catalog.py --fetch    # télécharge puis build
  python scripts/build_materials_catalog.py --check    # vérifie la sortie
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "backend" / "app" / "assets" / "materials"
CACHE_DEFAULT = REPO / ".cache" / "materials-polyhaven"

API = "https://api.polyhaven.com"
LICENCE_URL = "https://polyhaven.com/license"
# Les ToS (relues le 03/09/2026) exigent « a unique Referer header or
# user-agent that matches your software name ». Le voici.
UA = "DeepotusVideoGen/2.1 (+materials starter catalog build script)"

RES = "1k"                 # la résolution du catalogue embarqué
COTE = 1024                # les cartes sont ré-encodées à ce côté
QUALITE = 82               # JPEG : au-dessus, le poids double pour rien
# Les trois cartes de Poly Haven que l'on embarque, et leur nom chez nous.
CARTES = (("Diffuse", "basecolor"), ("nor_gl", "normal"), ("Rough", "roughness"))

FAMILLES = [
    {"id": "sols", "name": "Sols"},
    {"id": "murs", "name": "Murs & briques"},
    {"id": "metaux", "name": "Métaux"},
    {"id": "bois", "name": "Bois"},
    {"id": "tissus", "name": "Tissus & cuirs"},
    {"id": "beton_terrain", "name": "Béton & terrains"},
]

# LES TRENTE, PAR IDENTIFIANT EXPLICITE. Chacun a été vérifié présent dans
# `api.polyhaven.com/assets?t=textures` le 03/09/2026. Une liste explicite et
# pas un filtre par catégorie : un filtre rendrait un catalogue différent à
# chaque build, donc un installeur non reproductible et des captures d'écran
# qui mentent.
ASSETS = [
    {"slug": "brick_floor_003", "name": "Sol de briques", "family": "sols"},
    {"slug": "brown_floor_tiles", "name": "Carrelage brun", "family": "sols"},
    {"slug": "anti_skid_tiles", "name": "Dalles antidérapantes", "family": "sols"},
    {"slug": "asphalt_04", "name": "Asphalte", "family": "sols"},
    {"slug": "bicolour_gravel", "name": "Gravier bicolore", "family": "sols"},

    {"slug": "brick_wall_001", "name": "Mur de briques rouges", "family": "murs"},
    {"slug": "brick_wall_003", "name": "Mur de briques clair", "family": "murs"},
    {"slug": "castle_brick_02_red", "name": "Brique de château, rouge", "family": "murs"},
    {"slug": "beige_wall_001", "name": "Enduit beige", "family": "murs"},
    {"slug": "blue_plaster_wall", "name": "Enduit bleu", "family": "murs"},

    {"slug": "metal_plate", "name": "Tôle striée", "family": "metaux"},
    {"slug": "corrugated_iron_02", "name": "Tôle ondulée", "family": "metaux"},
    {"slug": "rusty_metal_02", "name": "Métal rouillé", "family": "metaux"},
    {"slug": "green_metal_rust", "name": "Métal peint rouillé", "family": "metaux"},
    {"slug": "blue_metal_plate", "name": "Plaque de métal bleue", "family": "metaux"},

    {"slug": "brown_planks_03", "name": "Planches brunes", "family": "bois"},
    {"slug": "black_walnut_veneer_01", "name": "Placage de noyer", "family": "bois"},
    {"slug": "bamboo_wall", "name": "Bambou", "family": "bois"},
    {"slug": "black_painted_planks", "name": "Planches peintes en noir", "family": "bois"},
    {"slug": "ash_veneer", "name": "Placage de frêne", "family": "bois"},

    {"slug": "denim_fabric", "name": "Denim", "family": "tissus"},
    {"slug": "rough_linen", "name": "Lin brut", "family": "tissus"},
    {"slug": "brown_leather", "name": "Cuir brun", "family": "tissus"},
    {"slug": "ribbed_corduroy", "name": "Velours côtelé", "family": "tissus"},
    {"slug": "wool_boucle", "name": "Laine bouclée", "family": "tissus"},

    {"slug": "brushed_concrete", "name": "Béton brossé", "family": "beton_terrain"},
    {"slug": "anti_slip_concrete", "name": "Béton antidérapant", "family": "beton_terrain"},
    {"slug": "aerial_rocks_02", "name": "Rochers", "family": "beton_terrain"},
    {"slug": "brown_mud_dry", "name": "Terre sèche", "family": "beton_terrain"},
    {"slug": "aerial_sand", "name": "Sable", "family": "beton_terrain"},
]


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "DeepotusVideoGen"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _json(url: str) -> dict:
    return json.loads(_get(url).decode("utf-8"))


def assert_cc0() -> str:
    """Abandonne si la page de licence ne dit plus CC0.

    Même garde que `_assert_cc0` du catalogue de sons : la licence se VÉRIFIE
    au build. Poly Haven n'expose pas de champ `license` par asset (mesuré le
    03/09/2026 sur /info/brick_wall_001) — c'est donc la page du site qui fait
    foi, et un changement en amont fait échouer le build au lieu de
    contaminer silencieusement l'installeur."""
    txt = _get(LICENCE_URL).decode("utf-8", "replace")
    if "CC0" not in txt.upper():
        raise SystemExit(
            "[licence] polyhaven.com/license ne mentionne plus CC0 — build "
            "abandonné. Relire la page avant de redistribuer quoi que ce soit.")
    return LICENCE_URL


def fetch(cache: pathlib.Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for a in ASSETS:
        slug = a["slug"]
        fichiers = _json(f"{API}/files/{slug}")
        info = _json(f"{API}/info/{slug}")
        (cache / f"{slug}.info.json").write_text(
            json.dumps(info, ensure_ascii=False), encoding="utf-8")
        for cle, notre in CARTES:
            bloc = ((fichiers.get(cle) or {}).get(RES) or {}).get("jpg")
            if not bloc:
                raise SystemExit(
                    f"[{slug}] carte « {cle} » absente en {RES}/jpg — "
                    f"cartes publiées : {sorted(fichiers)}")
            dest = cache / f"{slug}.{notre}.jpg"
            if dest.is_file() and hashlib.md5(dest.read_bytes()).hexdigest() \
                    == bloc.get("md5"):
                continue
            data = _get(bloc["url"], timeout=300)
            got = hashlib.md5(data).hexdigest()
            if bloc.get("md5") and got != bloc["md5"]:
                raise SystemExit(f"[{slug}/{cle}] md5 {got} != {bloc['md5']} "
                                 "annoncé par l'API — téléchargement abandonné")
            dest.write_bytes(data)
            print(f"[fetch] {slug}/{notre}: {len(data) // 1024} Ko")


def build(cache: pathlib.Path, out: pathlib.Path) -> dict:
    from PIL import Image
    licence = assert_cc0()
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    materials, notices = [], []
    for a in ASSETS:
        slug = a["slug"]
        info_p = cache / f"{slug}.info.json"
        if not info_p.is_file():
            raise SystemExit(f"[{slug}] info absente : {info_p}\n"
                             "-> lancez avec --fetch.")
        info = json.loads(info_p.read_text(encoding="utf-8"))
        (out / slug).mkdir(parents=True, exist_ok=True)
        cartes, poids = {}, 0
        for _cle, notre in CARTES:
            src = cache / f"{slug}.{notre}.jpg"
            if not src.is_file():
                raise SystemExit(f"[{slug}] carte absente : {src}")
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.size != (COTE, COTE):
                    im = im.resize((COTE, COTE), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=QUALITE, optimize=True,
                        subsampling=1)
            (out / slug / f"{notre}.jpg").write_bytes(buf.getvalue())
            cartes[notre] = f"{slug}/{notre}.jpg"
            poids += len(buf.getvalue())
        auteurs = info.get("authors") or {}
        materials.append({
            "id": slug, "name": a["name"], "family": a["family"],
            "polyhaven_name": info.get("name") or slug,
            "tags": list(info.get("tags") or [])[:8],
            "authors": auteurs,
            # `scale` et `dimensions` sont RELEVÉS mais jamais interprétés :
            # E1 de R10c écarte la taille physique propagée aux moteurs.
            "scale": info.get("scale"), "dimensions": info.get("dimensions"),
            "url": f"https://polyhaven.com/a/{slug}",
            "maps": cartes, "bytes": poids})
        notices.append(f"{a['name']} ({slug}) — Poly Haven — CC0 1.0\n"
                       f"  https://polyhaven.com/a/{slug}\n"
                       f"  {', '.join(f'{k} ({v})' for k, v in auteurs.items())}")
        print(f"[build] {slug}: {poids // 1024} Ko")

    cat = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
                                .replace("+00:00", "Z"),
        "source": {"name": "Poly Haven", "url": "https://polyhaven.com",
                   "license": "CC0-1.0", "license_url": licence},
        "families": [{**f, "count": sum(1 for m in materials
                                        if m["family"] == f["id"])}
                     for f in FAMILLES],
        "materials": materials,
    }
    (out / "catalog.json").write_text(
        json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "NOTICE.txt").write_text(
        "Catalogue de matières DeepotusVideoGen\n"
        "======================================\n\n"
        "Toutes les matières ci-dessous viennent de Poly Haven et sont\n"
        "publiées sous Creative Commons Zero (CC0 1.0) : usage commercial\n"
        "libre, aucune attribution exigée. Cette notice est un remerciement.\n\n"
        "Trois cartes sont embarquées (couleur, normale mesurée, rugosité) ;\n"
        "les cinq autres sont dérivées localement par l'application.\n\n"
        + "\n\n".join(notices) + "\n", encoding="utf-8")
    return cat


def check(out: pathlib.Path) -> int:
    p = out / "catalog.json"
    if not p.is_file():
        print(f"[check] catalog.json absent — {p}")
        return 1
    cat = json.loads(p.read_text(encoding="utf-8"))
    manquant, orphelin, declares = [], [], set()
    total = 0
    for m in cat["materials"]:
        for rel in m["maps"].values():
            declares.add(rel)
            f = out / rel
            if not f.is_file():
                manquant.append(rel)
            else:
                total += f.stat().st_size
    for f in out.rglob("*"):
        if f.is_file() and f.name not in ("catalog.json", "NOTICE.txt"):
            rel = f.relative_to(out).as_posix()
            if rel not in declares:
                orphelin.append(rel)
    print(f"[check] {len(cat['materials'])} matières, "
          f"{len(declares)} cartes, {total / 1024 / 1024:.1f} Mo")
    if manquant:
        print(f"[check] MANQUANT ({len(manquant)}) : {manquant[:10]}")
    if orphelin:
        print(f"[check] ORPHELIN ({len(orphelin)}) : {orphelin[:10]}")
    if manquant or orphelin:
        return 1
    print("[check] catalogue et fichiers concordent.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(CACHE_DEFAULT))
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    if args.check:
        return check(out)
    cache = pathlib.Path(args.cache)
    if args.fetch:
        fetch(cache)
    build(cache, out)
    return check(out)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5 : écrire le module runtime**

Créer `backend/app/services/starter_materials.py` :

```python
# -*- coding: utf-8 -*-
"""Catalogue de démarrage des MATIÈRES — face runtime (R10c P4).

Fabriqué par `scripts/build_materials_catalog.py` dans
`backend/app/assets/materials/` : trente matières CC0 de Poly Haven, trois
cartes chacune (couleur, normale mesurée, rugosité), 1024², JPEG. Ce module
lit `catalog.json` UNE fois, le sert à l'écran, et sait recopier une matière
dans les matières de l'utilisateur.

POURQUOI LA RECOPIE PLUTÔT QU'UNE LECTURE DIRECTE — même raison que
`starter_catalog.py` pour les sons : tout l'aval (inspecteur, dérivation
re-réglable, export, GLB, Forge 3D des cartes, print3d) lit une matière
`mat_xxxxxxxx` sur disque. Une matière de catalogue qui resterait « à part »
serait un cas particulier à porter dans chaque écran, pour toujours. Recopiée
à la première utilisation, elle devient une matière ordinaire et l'aval n'a
rien à savoir de son origine — sauf son CRÉDIT, qui la suit.

CINQ CARTES SUR HUIT SONT DÉRIVÉES ICI, gratuitement et hors ligne
(`pbr_service.derive_maps`) : occlusion, hauteur, métal, émissif et ORM. C'est
exactement l'argument du produit, appliqué à son propre catalogue — et la
fiche de la matière importée le dit.

Catalogue absent (dépôt sans build) = catalogue VIDE et l'écran le dit,
jamais une exception.
"""
from __future__ import annotations

import json
import threading
import unicodedata
from pathlib import Path

from loguru import logger

STARTER_DIR = Path(__file__).resolve().parent.parent / "assets" / "materials"
CATALOG_FILE = STARTER_DIR / "catalog.json"

_lock = threading.Lock()
_cache: dict | None = None
_EMPTY: dict = {"version": 0, "source": {}, "families": [], "materials": [],
                "available": False}


class StarterError(Exception):
    """Erreur à traduire en HTTPException(status, message) par la route."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        if not CATALOG_FILE.is_file():
            logger.warning(
                "matières : catalog.json absent ({}) — le catalogue de "
                "démarrage est vide. Lancer : python "
                "scripts/build_materials_catalog.py --fetch", CATALOG_FILE)
            _cache = dict(_EMPTY)
            return _cache
        try:
            d = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
            d["available"] = True
            _cache = d
        except (OSError, ValueError) as e:
            logger.error("matières : catalog.json illisible ({}) — {}",
                         CATALOG_FILE, e)
            _cache = dict(_EMPTY)
        return _cache


def reset_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def _index() -> dict:
    return {m["id"]: m for m in load().get("materials", [])}


def get(item_id: str) -> dict:
    it = _index().get(str(item_id))
    if it is None:
        raise StarterError(404, f"matière « {item_id} » absente du catalogue "
                                f"de démarrage")
    return it


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def browse(family: str = "", query: str = "") -> list[dict]:
    """La recherche porte sur le nom FR, le nom Poly Haven, l'identifiant et
    les mots-clés : « brique », « brick » et « brick_wall_001 » trouvent la
    même matière, parce qu'on ne sait pas dans quelle langue on cherche."""
    items = list(_index().values())
    if family:
        items = [i for i in items if i.get("family") == family]
    q = _norm(query).strip()
    if q:
        def foin(i):
            return _norm(" ".join([str(i.get("name", "")),
                                   str(i.get("polyhaven_name", "")),
                                   str(i.get("id", "")),
                                   " ".join(i.get("tags") or [])]))
        items = [i for i in items if all(t in foin(i) for t in q.split())]
    return items


def carte_path(item_id: str, carte: str) -> Path:
    """Chemin d'une carte, CONFINÉ à STARTER_DIR.

    Le catalogue est généré, donc sain en principe — mais il est lu depuis le
    disque, et un chemin qui s'en échapperait serait servi tel quel. On
    vérifie le confinement au lieu de le supposer (même garde que
    `starter_catalog.asset_path`)."""
    it = get(item_id)
    rel = (it.get("maps") or {}).get(str(carte))
    if not rel:
        raise StarterError(404, f"carte « {carte} » absente de « {item_id} »")
    p = (STARTER_DIR / rel).resolve()
    if not p.is_relative_to(STARTER_DIR.resolve()):
        raise StarterError(400, "chemin de carte hors du catalogue")
    if not p.is_file():
        raise StarterError(404, f"fichier absent : {rel}")
    return p


def importer(ids) -> list[dict]:
    """Recopie des matières du catalogue dans les matières de l'utilisateur.

    Les trois cartes MESURÉES sont reprises telles quelles ; les cinq autres
    sont dérivées localement. Les niveaux de départ sont ceux que les cartes
    PORTENT (`natural_levels`), pas des 0/1 de principe."""
    from PIL import Image
    from app.services import material_store as MS
    from app.services import pbr_service as PBR

    faits = []
    for brut in (ids or []):
        it = get(brut)
        base_p = carte_path(it["id"], "basecolor")
        with Image.open(base_p) as im:
            base = im.convert("RGB")
        res = base.size[0]
        auteurs = ", ".join((it.get("authors") or {}).keys()) or "Poly Haven"
        mat = MS.create_material(
            name=it["name"], prompt="", full_prompt="", res=res,
            seamless=True, seam={"before": None, "after": None},
            source={"kind": "catalog", "model": None,
                    "filename": it["id"], "prep": None})
        mid = mat["id"]
        maps = PBR.derive_maps(base, mat["derive"],
                               list(MS.SECONDARY_MAPS))
        maps["basecolor"] = base
        # les DEUX cartes mesurées écrasent leur dérivée : elles portent une
        # information qu'aucune estimation depuis l'albédo ne peut inventer
        for carte, kind in (("normal", "normal"), ("roughness", "roughness")):
            try:
                p = carte_path(it["id"], carte)
            except StarterError:
                continue
            with Image.open(p) as im:
                maps[kind] = (im.convert("RGB") if kind == "normal"
                              else im.convert("L")).resize((res, res))
        maps["orm"] = Image.merge("RGB", (maps["ao"].convert("L"),
                                          maps["roughness"].convert("L"),
                                          maps["metallic"].convert("L")))
        MS.save_maps(mid, maps)
        MS.write_source(mid, base)
        mat = MS.read_material(mid)
        mat["props"] = MS.merge_props(mat["props"], MS.natural_levels(maps))
        mat["credit"] = {
            "source": (load().get("source") or {}).get("name", "Poly Haven"),
            "author": auteurs, "license": "CC0-1.0",
            "url": it.get("url", "")}
        mat = MS.refresh_report(mat, maps)
        MS.write_material(mat)
        faits.append(MS.read_material(mid))
    return faits
```

- [ ] **Step 6 : les deux ajustements de `material_store` et les routes**

Dans `material_store.py`, ligne 151 :

```python
SOURCE_KINDS = ("prompt", "library", "upload", "catalog")
```

Dans `normalize_material`, ajouter au dictionnaire rendu, après
`"thumb": bool(raw.get("thumb")),` :

```python
        # D'où vient cette matière et sous quelle licence — pour une matière
        # du catalogue CC0, ou une matière importée un jour d'ailleurs. Vide
        # pour une matière forgée par l'utilisateur : elle est à lui.
        "credit": ({k: str(v)[:200] for k, v in raw["credit"].items()
                    if k in ("source", "author", "license", "url")}
                   if isinstance(raw.get("credit"), dict) else {}),
```

Dans `_readme`, après la ligne du prompt :

```python
    cr = mat.get("credit") or {}
    if cr:
        lines += ["", f"Source : {cr.get('source', '')} — "
                      f"{cr.get('author', '')} — {cr.get('license', '')}",
                  f"  {cr.get('url', '')}"]
```

Dans `routes.py`, après `list_material_presets` (ligne 7222) :

```python
@router.get("/materials/catalog")
async def material_catalog(family: str = "", q: str = ""):
    """Le catalogue CC0 embarqué. Absent (dépôt sans build), il se déclare
    vide — l'écran le dit, personne ne tombe."""
    from app.services import starter_materials as SM
    cat = await asyncio.to_thread(SM.load)
    return {"available": cat.get("available", False),
            "source": cat.get("source", {}),
            "families": cat.get("families", []),
            "materials": await asyncio.to_thread(SM.browse, family, q)}


@router.get("/materials/catalog/{item_id}/{carte}.jpg")
async def material_catalog_map(item_id: str, carte: str):
    from app.services import starter_materials as SM
    try:
        p = await asyncio.to_thread(SM.carte_path, item_id, carte)
    except SM.StarterError as e:
        raise HTTPException(e.status, e.message)
    return FileResponse(p, media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.post("/materials/catalog/import")
async def material_catalog_import(body: dict):
    """Recopie des matières du catalogue en matières ordinaires."""
    from app.services import starter_materials as SM
    ids = (body or {}).get("ids")
    if not isinstance(ids, list) or not ids:
        raise HTTPException(400, "ids : une liste d'identifiants du catalogue "
                                 "est attendue")
    if len(ids) > 30:
        raise HTTPException(400, "30 matières au maximum par import")
    try:
        faits = await asyncio.to_thread(SM.importer, [str(i) for i in ids])
    except SM.StarterError as e:
        raise HTTPException(e.status, e.message)
    return {"materials": faits}
```

- [ ] **Step 7 : l'écran vide propose le catalogue**

Dans `materialforge.js`, `emptyHtml` (ligne 1313) : ajouter, sous les amorces
de prompt, un bloc « Ou pars d'une matière du catalogue » avec un
`<button class="btn" id="catBtn">📚 Catalogue CC0 (30 matières)</button>` ;
dans `wireEmpty` (ligne 1344), brancher :

```js
  const cat = $("#catBtn");
  if (cat) cat.addEventListener("click", async () => {
    const d = await api.get("/materials/catalog");
    if (!d.available) {
      toast("Le catalogue n'est pas dans cette installation "
            + "(build_materials_catalog.py --fetch).", true);
      return;
    }
    openCatalog(d);
  });
```

et définir, juste au-dessus de `emptyHtml` :

```js
/* ── le catalogue CC0 (P4) ──────────────────────────────────────────────────
   Une grille de vignettes servies par /materials/catalog/<id>/basecolor.jpg,
   sélection multiple, puis UN SEUL POST : trente imports en trente requêtes
   feraient trente barres de progression pour un seul geste, et trente
   occasions d'échouer à moitié. */
function openCatalog(d) {
  const choisis = new Set();
  const back = $("#proofBack");
  const box = $("#proof");
  box.innerHTML = `
    <header><h3 id="proofTitle">Catalogue CC0 — ${d.materials.length} matières</h3>
      <button class="btn ghost sm" id="catClose">✕</button></header>
    <p class="hint">Source : ${esc((d.source || {}).name || "")} —
      licence ${esc((d.source || {}).license || "")}. Trois cartes sont
      embarquées (couleur, normale mesurée, rugosité) ; les cinq autres sont
      dérivées à l'import, localement et gratuitement.</p>
    <div class="chips" id="catFams">${
      ["", ...d.families.map((f) => f.id)].map((f) => {
        const lab = f ? (d.families.find((x) => x.id === f).name
                         + " (" + d.families.find((x) => x.id === f).count + ")")
                      : "Toutes";
        return `<button class="chip" data-fam="${esc(f)}">${esc(lab)}</button>`;
      }).join("")}</div>
    <div class="img-grid" id="catGrid">${
      d.materials.map((m) => `
        <button class="cat-cell" data-id="${esc(m.id)}" title="${esc(m.id)}">
          <img loading="lazy" src="/api/materials/catalog/${esc(m.id)}/basecolor.jpg">
          <span>${esc(m.name)}</span>
        </button>`).join("")}</div>
    <button class="btn strong wide" id="catGo" disabled>Importer</button>`;
  box.classList.remove("hidden");
  back.classList.remove("hidden");
  const go = $("#catGo");
  const maj = () => {
    go.disabled = choisis.size === 0;
    go.textContent = choisis.size
      ? `Importer ${choisis.size} matière${choisis.size > 1 ? "s" : ""}`
      : "Importer";
  };
  $$("#catGrid .cat-cell").forEach((b) => b.addEventListener("click", () => {
    const id = b.dataset.id;
    if (choisis.has(id)) { choisis.delete(id); b.classList.remove("on"); }
    else { choisis.add(id); b.classList.add("on"); }
    maj();
  }));
  $$("#catFams .chip").forEach((c) => c.addEventListener("click", async () => {
    closeProof();
    openCatalog(await api.get("/materials/catalog"
      + (c.dataset.fam ? `?family=${encodeURIComponent(c.dataset.fam)}` : "")));
  }));
  $("#catClose").addEventListener("click", closeProof);
  go.addEventListener("click", async () => {
    go.disabled = true;
    try {
      const r = await api.post("/materials/catalog/import",
                               { ids: Array.from(choisis) });
      closeProof();
      await loadMaterials();
      toast(`${r.materials.length} matière(s) importée(s).`);
    } catch (e) { apiFail(e, "import du catalogue"); go.disabled = false; }
  });
}
```

et ajouter à `materialforge.css` :

```css
/* ── catalogue CC0 (P4) ─────────────────────────────────────────────────── */
.cat-cell { display: block; padding: 0; border: 1px solid var(--line, #222831);
  border-radius: 6px; background: transparent; cursor: pointer;
  overflow: hidden; height: 132px; }
.cat-cell img { width: 100%; height: 100px; object-fit: cover; display: block; }
.cat-cell span { display: block; font-size: 11px; padding: 3px 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cat-cell.on { outline: 2px solid var(--cyan, #4cc9f0); }
```

> La **hauteur explicite** de `.cat-cell` n'est pas décorative : une case de
> grille en `overflow: hidden` peut contribuer ~0 à la hauteur intrinsèque de
> sa rangée, et la grille s'effondre en lignes de 2 px sans qu'aucune sonde
> DOM ne le voie (piège mesuré sur le sélecteur de Bibliothèque, 28/08).

- [ ] **Step 8 : lancer, mesurer le poids, commit**

```
python tests/test_starter_materials.py
python scripts/build_materials_catalog.py --fetch
python scripts/build_materials_catalog.py --check
```

Attendu : `OK — 5 assertions groupées vertes (catalogue de matières CC0)` ;
puis, pour le build, une ligne par matière et
`[check] 30 matières, 90 cartes, NN.N Mo` avec `catalogue et fichiers
concordent.` **Budget : ≤ 45 Mo.** Au-delà, baisser `QUALITE` à 78 et
remesurer — le chiffre va dans le message de commit, pas une approximation.

```bash
git add scripts/build_materials_catalog.py backend/app/services/starter_materials.py backend/app/services/material_store.py backend/app/api/routes.py frontend/materialforge/materialforge.js backend/tests/test_starter_materials.py backend/app/assets/materials
git commit -m 'matieres P4 : trente matieres CC0, telechargees au build

Trente identifiants Poly Haven EXPLICITES, six familles, chacun verifie
present dans l API le 03/09/2026. Une liste explicite et pas un filtre par
categorie : un filtre rendrait un catalogue different a chaque build, donc un
installeur non reproductible et des captures d ecran qui mentent.

Trois cartes embarquees, cinq derivees, et c est un choix mesure. Poly Haven
publie jusqu a onze cartes ; trois seulement portent une information qu une
derivation ne peut pas inventer — la couleur, la normale MESUREE (un relief
photogrammetre, pas une estimation depuis l albedo) et la rugosite. Les cinq
autres se derivent localement, gratuitement, hors ligne. Le catalogue
demontre donc l argument du produit sur lui-meme, et la fiche le dit.

Au BUILD et jamais depuis l application : un studio local dont l ecran de
matieres exige le reseau trahit sa promesse, et une API tierce qui bouge
casserait l ecran de quelqu un qui n a rien demande. La garde de licence
verifie CC0 sur la page du site (l API n expose aucun champ license par
asset, mesure), le md5 de chaque telechargement est confronte a celui que l
API annonce, et --check est la garde de packaging.

Une matiere importee devient une matiere ORDINAIRE mat_xxxxxxxx : tout l aval
— inspecteur, re-derivation, export, GLB, Forge 3D, print3d — la lit sans
rien savoir de son origine, sauf son credit, qui la suit.

Poids mesure du catalogue : NN,N Mo pour 90 cartes. Zero ligne d installeur :
la sortie vit dans le paquet Python que l installeur recopie deja.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

> Remplacer `NN,N` par le chiffre imprimé par `--check` avant de committer.
> Un commit qui annonce un poids non mesuré est exactement ce que ce dépôt
> corrige depuis deux mois.

---
## Lot 2 — différenciant

### Task 11 : D1 — le socle des générateurs : un bruit seamless PAR CONSTRUCTION, et son budget

**Files:**
- Create: `backend/app/services/pattern_service.py`
- Test: `backend/tests/test_pattern_service.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_pattern_service.py` :

```python
# -*- coding: utf-8 -*-
"""Générateurs paramétriques locaux (R10c D1) — le socle : bruit de valeur
fractal SEAMLESS PAR CONSTRUCTION, et son budget en secondes.

« Par construction » n'est pas une figure de style, et c'est ce que ce banc
mesure : le réseau est périodique, il est bordé CYCLIQUEMENT avant
l'agrandissement, et le recadrage retombe sur une période entière. Le témoin
— la même chose sans le bordage — est là pour montrer ce que coûte l'oubli.

Run (depuis backend/) : python tests/test_pattern_service.py
"""
import os
import pathlib
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import pattern_service as PS                 # noqa: E402
from app.services import pbr_service as PBR                    # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# ══ 1 · la maille DIVISE toujours le côté ══════════════════════════════════
# 384 n'est PAS une puissance de deux, et c'est tout l'objet de ce cas :
# sur un cote en puissance de deux, n'importe quelle puissance de deux le
# divise, et la garde de divisibilite ne se voit jamais.
for cote in (256, 384, 512, 1024):
    for voulu in (3, 5, 8, 13, 100, 999, 1, 0, -4):
        c = PS.cells(cote, voulu)
        assert cote % c == 0, (cote, voulu, c)
        assert 2 <= c <= cote, (cote, voulu, c)
ok("cells() rend toujours un diviseur du côté, entre 2 et le côté — sans "
   "divisibilité exacte, le recadrage ne retomberait pas sur une période")

# ══ 2 · le raccord, et son témoin ══════════════════════════════════════════
b = PS.bruit(256, cellules=8, octaves=4, graine=17)
assert b.size == (256, 256) and b.mode == "L"
r_bon = PBR.seam_report(b)
assert r_bon["ratio"] <= 1.5, r_bon
assert r_bon["grade"] == "invisible", r_bon
naif = PS._octave_naive(256, 8, 17)          # témoin : sans bordage cyclique
r_naif = PBR.seam_report(naif)
assert r_naif["ratio"] > 2.0 * r_bon["ratio"], (r_bon, r_naif)
ok(f"raccord : rapport {r_bon['ratio']} ({r_bon['grade']}) ; le même bruit "
   f"sans bordage cyclique monte à {r_naif['ratio']}")

# ══ 3 · déterministe, et la graine change quelque chose ════════════════════
assert PS.bruit(128, 8, 3, graine=5).tobytes() == \
       PS.bruit(128, 8, 3, graine=5).tobytes()
assert PS.bruit(128, 8, 3, graine=5).tobytes() != \
       PS.bruit(128, 8, 3, graine=6).tobytes()
ok("déterministe à graine égale, différent à graine différente — un aperçu "
   "qui bouge tout seul ne se règle pas")

# ══ 4 · les octaves apportent du détail ════════════════════════════════════
un = PBR.stats(PS.bruit(256, 8, 1, graine=3))
cinq = PBR.stats(PS.bruit(256, 8, 5, graine=3))
def grain(img):
    from PIL import ImageChops, ImageFilter, ImageStat
    return ImageStat.Stat(ImageChops.difference(
        img, img.filter(ImageFilter.GaussianBlur(1.5)))).mean[0]
g1, g5 = grain(PS.bruit(256, 8, 1, graine=3)), grain(PS.bruit(256, 8, 5, graine=3))
assert g5 > 1.5 * g1, (g1, g5)
assert un["span"] > 40 and cinq["span"] > 40, (un, cinq)
ok(f"cinq octaves portent {g5 / g1:.1f} fois le grain d'une seule, et les "
   f"deux gardent une amplitude utile")

# ══ 5 · l'étirement reste raccordable ══════════════════════════════════════
etire = PS.etirer(PS.bruit(256, 8, 4, graine=9), 1, 16)
assert etire.size == (256, 256)
r_et = PBR.seam_report(etire)
assert r_et["ratio"] <= 2.0, r_et
ok(f"étirement anisotrope (x1, y16) : raccord {r_et['ratio']} — le bordage "
   f"cyclique suit l'échelle")

# ══ 6 · budget ═════════════════════════════════════════════════════════════
t0 = time.perf_counter()
gros = PS.bruit(1024, cellules=8, octaves=6, graine=1)
dt = time.perf_counter() - t0
assert gros.size == (1024, 1024)
assert dt < PS.BUDGET_BRUIT_1024, (dt, PS.BUDGET_BRUIT_1024)
print(f"\n  bruit 1024² 6 octaves : {dt:.2f} s "
      f"(budget {PS.BUDGET_BRUIT_1024:.1f} s)")

print(f"\nOK — {PASS} assertions groupées vertes (pattern_service, socle)")
```

- [ ] **Step 2 : lancer le banc et le voir rouge**

```
python tests/test_pattern_service.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.pattern_service'`.

- [ ] **Step 3 : écrire le socle**

Créer `backend/app/services/pattern_service.py` :

```python
# -*- coding: utf-8 -*-
"""Générateurs paramétriques de matières, locaux et hors ligne (R10c D1).

CE QUE CE MODULE VEND, ET POURQUOI IL EXISTE. Substance est payant et lourd ;
un générateur de briques n'a besoin ni de l'un ni de l'autre. Dix motifs
réglables en direct, gratuits, sans clé, sans réseau — et SEAMLESS PAR
CONSTRUCTION, pas par correction a posteriori.

« PAR CONSTRUCTION » VEUT DIRE QUELQUE CHOSE DE PRÉCIS. `pixel_ops.make_seamless`
recoud une image après coup : elle mélange les bords, ce qui marche et ce qui
laisse une trace. Ici, rien à recoudre : tout motif est tracé NEUF FOIS, décalé
de -côté, 0 et +côté sur chaque axe (`cyclique`), et tout bruit part d'un
réseau PÉRIODIQUE bordé cycliquement avant agrandissement (`bruit`). Ce qui
sort d'un bord est exactement ce qui rentre par l'autre — c'est arithmétique,
pas statistique, et le banc le mesure au rapport de couture de `pbr_service`.

LE BUDGET EST UNE CONTRAINTE, PAS UN VŒU. Le runtime embarqué n'a pas numpy :
une boucle Python sur 1 048 576 pixels coûte plusieurs secondes, et six
octaves en coûteraient trente. Le procédé retenu ne fait donc de Python QUE
sur le petit réseau (au plus 256 x 256 tirages) ; tout le reste est du
`Image.resize` et de l'`ImageChops`, c'est-à-dire du C. Les budgets ci-dessous
sont mesurés par le banc, sur cette machine, et échouent s'ils sont dépassés.
"""
from __future__ import annotations

import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from app.services import pbr_service as PBR

__all__ = ["BUDGET_BRUIT_1024", "BUDGET_MOTIF_1024", "cells", "bruit",
           "etirer", "cyclique", "colorer"]

# Budgets en secondes, à 1024x1024, sur le Python embarqué sans numpy.
BUDGET_BRUIT_1024 = 1.5
BUDGET_MOTIF_1024 = 2.5

_BORD = 2          # cellules de bordage : la portée du noyau bicubique est de
                   # 2 px côté source, donc 2 cellules couvrent tout


def cells(cote: int, voulu) -> int:
    """La taille de réseau réellement utilisable : la plus grande puissance de
    deux qui soit <= `voulu` ET qui DIVISE `cote`.

    Sans divisibilité exacte, le recadrage final ne retombe pas sur une
    période entière du réseau, et la tuile cesse d'être raccordable — c'est-à-
    dire que le seul argument mesurable du Material Forge tombe. On rend donc
    une valeur voisine plutôt que d'accepter la valeur demandée."""
    try:
        v = int(voulu)
    except (TypeError, ValueError):
        v = 8
    v = max(2, min(v, int(cote)))
    c = 2
    while c * 2 <= v:
        c *= 2
    while int(cote) % c:
        c //= 2
    return max(2, c)


def _lattice(n: int, graine: int) -> Image.Image:
    """Le réseau : n x n valeurs pseudo-aléatoires, en L. C'est le SEUL
    endroit où une boucle Python touche des pixels — n vaut 256 au pire."""
    rng = random.Random((int(graine) & 0x7FFFFFFF) * 2654435761 % (2 ** 61))
    return Image.frombytes("L", (n, n),
                           bytes(rng.randrange(256) for _ in range(n * n)))


def _octave(cote: int, n: int, graine: int) -> Image.Image:
    """Une octave : réseau périodique -> bordage cyclique -> agrandissement
    bicubique -> recadrage sur une période entière."""
    e = max(1, int(cote) // n)
    grand = PBR.wrap(_lattice(n, graine), _BORD).resize(
        ((n + 2 * _BORD) * e, (n + 2 * _BORD) * e), Image.BICUBIC)
    d = _BORD * e
    return grand.crop((d, d, d + cote, d + cote))


def _octave_naive(cote: int, n: int, graine: int) -> Image.Image:
    """LE TÉMOIN, gardé dans le module et exercé par le banc : la même octave
    SANS bordage cyclique. Aux bords, l'agrandissement bicubique prolonge le
    pixel de bord au lieu de lire l'autre côté, et la jonction se voit. Elle
    est ici pour que la différence soit MESURÉE, jamais racontée."""
    e = max(1, int(cote) // n)
    return _lattice(n, graine).resize((n * e, n * e), Image.BICUBIC).resize(
        (cote, cote), Image.BICUBIC)


def bruit(cote: int, cellules: int = 8, octaves: int = 5,
          persistance: float = 0.5, graine: int = 0) -> Image.Image:
    """Bruit de valeur fractal, seamless par construction.

    Les poids sont NORMALISÉS avant l'addition (et non divisés après) : sinon
    la somme des octaves saturerait à 255 dans `ImageChops.add`, et le motif
    reviendrait plat en haut de l'échelle sans que rien ne le signale."""
    n_oct = max(1, min(int(octaves), 8))
    p = max(0.05, min(0.95, float(persistance)))
    poids = [p ** k for k in range(n_oct)]
    somme = sum(poids) or 1.0
    total = None
    for k, w in enumerate(poids):
        n = cells(cote, int(cellules) * (2 ** k))
        oc = _octave(cote, n, int(graine) + 977 * k)
        part = oc.point([PBR.clamp8(v * w / somme) for v in range(256)])
        total = part if total is None else ImageChops.add(total, part)
        if n >= cote:
            break
    return ImageOps.autocontrast(total, cutoff=1)


def etirer(img: Image.Image, kx: int = 1, ky: int = 1) -> Image.Image:
    """Étire un motif de kx en x et ky en y, EN GARDANT le raccord.

    Une réduction en BOX puis un agrandissement bicubique : la réduction d'une
    image périodique reste périodique, et l'agrandissement passe par le même
    bordage cyclique que les octaves. C'est ce qui fait un métal brossé (ky
    grand) ou un fil de bois (kx grand) sans casser la tuile."""
    w, h = img.size
    petit = img.resize((max(2, w // max(1, int(kx))),
                        max(2, h // max(1, int(ky)))), Image.BOX)
    p = 4
    grand = PBR.wrap(petit, p).resize(
        ((petit.size[0] + 2 * p) * max(1, w // petit.size[0]),
         (petit.size[1] + 2 * p) * max(1, h // petit.size[1])), Image.BICUBIC)
    dx = p * max(1, w // petit.size[0])
    dy = p * max(1, h // petit.size[1])
    return grand.crop((dx, dy, dx + w, dy + h))


def cyclique(cote: int, tracer, fond: int = 0) -> Image.Image:
    """Un canevas L où `tracer(draw, dx, dy)` est appelé NEUF FOIS, décalé de
    -côté, 0 et +côté sur chaque axe.

    Tout ce qui déborde d'un bord rentre par l'autre : la tuile est
    raccordable par arithmétique, et non par un mélange de bords qui laisse
    toujours une trace."""
    img = Image.new("L", (cote, cote), fond)
    d = ImageDraw.Draw(img)
    for dy in (-cote, 0, cote):
        for dx in (-cote, 0, cote):
            tracer(d, dx, dy)
    return img


def colorer(masque: Image.Image, sombre: str, clair: str) -> Image.Image:
    """Un masque L -> une base color RVB entre deux couleurs hex. `ImageOps.
    colorize` fait le dégradé en C, sans boucle."""
    def _rgb(h):
        s = str(h or "#808080").lstrip("#")
        s = "".join(c * 2 for c in s) if len(s) == 3 else s
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return ImageOps.colorize(masque.convert("L"), _rgb(sombre), _rgb(clair))
```

- [ ] **Step 4 : relancer le banc et le voir vert**

```
python tests/test_pattern_service.py
```

Attendu : cinq lignes `✓`, la ligne de budget, puis
`OK — 5 assertions groupées vertes (pattern_service, socle)`.
Chiffres attendus : raccord du bruit ≈ 0,8 à 1,3 (« invisible ») contre 3 à 8
pour le témoin ; bruit 1024² six octaves autour de 0,4 à 1,0 s.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/pattern_service.py backend/tests/test_pattern_service.py
git commit -m 'matieres D1 : le socle des generateurs, seamless par construction

Par construction veut dire quelque chose de precis, et le banc le mesure :
tout bruit part d un reseau PERIODIQUE borde cycliquement avant
agrandissement, et le recadrage retombe sur une periode entiere. cells()
refuse donc une maille qui ne divise pas le cote et rend la voisine — sans
divisibilite exacte, le recadrage rate la periode et la tuile cesse d etre
raccordable, c est-a-dire que le seul argument mesurable du Material Forge
tombe.

Le temoin vit DANS le module et le banc l exerce : la meme octave sans
bordage cyclique. Rapport de couture 0,8 pour la bonne, plus du double pour
le temoin.

Le budget est une contrainte, pas un voeu. Sans numpy, une boucle Python sur
1 048 576 pixels coute des secondes : le procede ne fait du Python QUE sur le
reseau (256 x 256 tirages au pire), tout le reste est du resize et de l
ImageChops, donc du C. Six octaves a 1024 sous 1,5 s, mesure par le banc qui
echoue au-dela.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 12 : D1 — les dix générateurs, et leurs routes

**Files:**
- Modify: `backend/app/services/pattern_service.py` (les dix générateurs, `GENERATEURS`, `clean_params`, `generer`)
- Modify: `backend/app/api/routes.py` (deux routes, après `list_material_presets`)
- Test: `backend/tests/test_pattern_service.py` (nouvelle section) et `backend/tests/test_pattern_api.py`

- [ ] **Step 1 : ajouter la section rouge au banc du socle**

Dans `backend/tests/test_pattern_service.py`, insérer avant le `print` final :

```python
# ══ 7 · les DIX générateurs, un par un ═════════════════════════════════════
assert len(PS.GENERATEURS) == 10, len(PS.GENERATEURS)
assert len({g["id"] for g in PS.GENERATEURS}) == 10
temps = {}
for g in PS.GENERATEURS:
    gid = g["id"]
    p = PS.clean_params(gid, {})
    t0 = time.perf_counter()
    m = PS.generer(gid, 256, p)
    temps[gid] = time.perf_counter() - t0
    assert set(m) >= {"basecolor", "height"}, (gid, sorted(m))
    assert m["basecolor"].size == (256, 256) and m["basecolor"].mode == "RGB"
    assert m["height"].size == (256, 256) and m["height"].mode == "L"
    r = PBR.seam_report(m["basecolor"])
    assert r["ratio"] <= 2.0, (gid, r)
    st = PBR.stats(m["height"])
    assert st["span"] > 8, (gid, st)
    # déterminisme
    assert PS.generer(gid, 128, p)["basecolor"].tobytes() == \
           PS.generer(gid, 128, p)["basecolor"].tobytes(), gid
    # un réglage change quelque chose : on bouge le PREMIER paramètre numérique
    num = next((c for c in g["params"] if c["type"] == "f"), None)
    if num:
        autre = dict(p)
        autre[num["k"]] = num["max"] if p[num["k"]] < num["max"] else num["min"]
        assert PS.generer(gid, 128, PS.clean_params(gid, autre))["height"] \
            .tobytes() != PS.generer(gid, 128, p)["height"].tobytes(), \
            (gid, num["k"])
ok("dix générateurs : raccord <= 2,0, hauteur non plate, déterministes, et "
   "leur premier réglage numérique change vraiment la carte "
   f"({', '.join(g['id'] for g in PS.GENERATEURS)})")

# ══ 8 · budget d'un motif complet à 1024 ═══════════════════════════════════
lent = max(PS.GENERATEURS, key=lambda g: temps[g["id"]])["id"]
t0 = time.perf_counter()
PS.generer(lent, 1024, PS.clean_params(lent, {}))
dt2 = time.perf_counter() - t0
assert dt2 < PS.BUDGET_MOTIF_1024, (lent, dt2)
print(f"  le plus lent ({lent}) à 1024² : {dt2:.2f} s "
      f"(budget {PS.BUDGET_MOTIF_1024:.1f} s)")

# ══ 9 · une entrée pourrie ne lève jamais ══════════════════════════════════
for mauvais in (None, {}, {"x": 1}, {"rangs": "beaucoup"}, {"rangs": -9},
                {"rangs": 10 ** 9}, [], "briques"):
    p = PS.clean_params("briques", mauvais)
    assert isinstance(p, dict) and p, mauvais
    assert PS.generer("briques", 64, p)["height"].size == (64, 64)
try:
    PS.generer("nexistepas", 64, {})
    raise AssertionError("aurait dû lever")
except ValueError as e:
    assert "nexistepas" in str(e), str(e)
ok("réglages pourris -> défauts, générateur inconnu -> ValueError nommée")
```

- [ ] **Step 2 : lancer, voir rouge**

```
python tests/test_pattern_service.py
```

Attendu : `AttributeError: module 'app.services.pattern_service' has no attribute 'GENERATEURS'`.

- [ ] **Step 3 : écrire les dix générateurs**

Ajouter à la fin de `backend/app/services/pattern_service.py` (et compléter
`__all__` avec `"GENERATEURS", "clean_params", "generer"`) :

```python
# ── les dix générateurs ─────────────────────────────────────────────────────
#
# CHACUN REND `basecolor` (RVB) ET `height` (L). Les six autres cartes se
# dérivent ensuite par `pbr_service.derive_maps`, exactement comme pour une
# photo : un générateur n'a aucune raison d'avoir son propre chemin de
# dérivation, et en avoir un ferait deux vérités.
#
# LA PÉRIODICITÉ EST IMPOSÉE PAR LES PARAMÈTRES, pas espérée. Les motifs se
# règlent en NOMBRE de rangs et de colonnes (des entiers), jamais en taille de
# brique : une brique de 37 px sur une tuile de 256 ne pave pas, et laisser
# l'utilisateur la choisir serait lui vendre un raccord qu'on ne peut pas
# tenir. Les angles de `rayures` sont pour la même raison une liste fermée.

def _lisser(masque: Image.Image, r: float) -> Image.Image:
    return PBR.cyclic(masque, ImageFilter.GaussianBlur(r), r * 3.0 + 1.0)


def _grain(cote: int, cellules: int, octaves: int, graine: int,
           force: float) -> Image.Image:
    """Un bruit ramené autour de 128 et atténué — le grain qu'on AJOUTE à un
    motif, sans le noyer."""
    b = bruit(cote, cellules, octaves, 0.55, graine)
    k = max(0.0, min(1.0, force))
    return b.point([PBR.clamp8(128.0 + (v - 128.0) * k) for v in range(256)])


def _melanger(masque: Image.Image, grain: Image.Image, part: float
              ) -> Image.Image:
    return Image.blend(masque, grain, max(0.0, min(1.0, part)))


def _briques(cote, p, graine):
    rangs, cols = int(p["rangs"]), int(p["colonnes"])
    h, w = cote / rangs, cote / cols
    j = max(1.0, p["joint"] * min(h, w))
    rng = random.Random(graine ^ 0x5EED)
    teintes = [rng.randrange(150, 250) for _ in range(rangs * cols + rangs)]

    def tracer(d, dx, dy):
        for r in range(-1, rangs + 1):
            y0 = r * h + dy
            off = (r % 2) * p["decalage"] * w
            for c in range(-1, cols + 2):
                x0 = c * w + off + dx
                d.rectangle([x0 + j / 2, y0 + j / 2,
                             x0 + w - j / 2, y0 + h - j / 2],
                            fill=teintes[(r * cols + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=40)
    hauteur = _lisser(masque, max(1.0, j * 0.35))
    return hauteur, _melanger(hauteur, _grain(cote, 16, 4, graine, 0.55), 0.35)


def _carrelage(cote, p, graine):
    n = int(p["cases"])
    t = cote / n
    j = max(1.0, p["joint"] * t)
    rng = random.Random(graine ^ 0xCA11)
    teintes = [rng.randrange(180, 252) for _ in range(n * n)]

    def tracer(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                d.rounded_rectangle(
                    [c * t + dx + j / 2, r * t + dy + j / 2,
                     (c + 1) * t + dx - j / 2, (r + 1) * t + dy - j / 2],
                    radius=max(1.0, p["arrondi"] * t * 0.2),
                    fill=teintes[(r * n + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=60)
    hauteur = _lisser(masque, max(1.0, j * 0.3))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 3, graine, 0.35), 0.22)


def _planches(cote, p, graine):
    n = int(p["planches"])
    w = cote / n
    j = max(1.0, p["joint"] * w)

    def tracer(d, dx, dy):
        for c in range(-1, n + 1):
            d.rectangle([c * w + dx + j / 2, dy - cote,
                         (c + 1) * w + dx - j / 2, dy + 2 * cote], fill=210)

    masque = cyclique(cote, tracer, fond=50)
    # le fil du bois : un bruit étiré DANS le sens de la planche
    fil = etirer(bruit(cote, 8, 5, 0.6, graine), 1, max(2, int(p["fil"])))
    hauteur = _lisser(_melanger(masque, fil, 0.45), max(1.0, j * 0.3))
    return hauteur, hauteur


def _damier(cote, p, graine):
    n = int(p["cases"])
    t = cote / n

    def tracer(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                if (r + c) % 2:
                    continue
                d.rectangle([c * t + dx, r * t + dy,
                             (c + 1) * t + dx, (r + 1) * t + dy], fill=235)

    masque = cyclique(cote, tracer, fond=45)
    hauteur = _lisser(masque, max(1.0, p["bord"] * t * 0.1))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 3, graine, 0.3), 0.18)


def _hexagones(cote, p, graine):
    # HEXAGONES LÉGÈREMENT ÉTIRÉS, ET C'EST ASSUMÉ : un hexagone RÉGULIER ne
    # pave pas un carré en nombre entier de mailles. On impose donc colonnes
    # et rangs entiers, et la maille s'étire de ce qu'il faut — le raccord
    # vaut mieux qu'une régularité que personne ne mesure.
    cols, rangs = int(p["colonnes"]), int(p["rangs"])
    w, h = cote / cols, cote / rangs
    j = max(1.0, p["joint"] * min(w, h) * 0.25)

    def hexa(d, cx, cy, fill):
        d.polygon([(cx - w / 2 + j, cy - h / 4), (cx, cy - h / 2 + j),
                   (cx + w / 2 - j, cy - h / 4), (cx + w / 2 - j, cy + h / 4),
                   (cx, cy + h / 2 - j), (cx - w / 2 + j, cy + h / 4)],
                  fill=fill)

    rng = random.Random(graine ^ 0x4E60)
    teintes = [rng.randrange(170, 250) for _ in range(cols * rangs + cols)]

    def tracer(d, dx, dy):
        for r in range(-1, rangs + 1):
            for c in range(-1, cols + 1):
                cx = (c + 0.5 * (r % 2)) * w + dx
                hexa(d, cx, (r + 0.5) * h + dy,
                     teintes[(r * cols + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=55)
    hauteur = _lisser(masque, max(1.0, j))
    return hauteur, _melanger(hauteur, _grain(cote, 24, 3, graine, 0.35), 0.2)


def _galets(cote, p, graine):
    n = max(4, int(p["densite"]))
    rng = random.Random(graine ^ 0x6A1E)
    pierres = [(rng.random() * cote, rng.random() * cote,
                cote / n * (0.45 + 0.55 * rng.random()),
                rng.randrange(150, 250)) for _ in range(n * n)]
    pierres.sort(key=lambda s: s[2])          # les grosses par-dessus

    def tracer(d, dx, dy):
        for x, y, r, t in pierres:
            d.ellipse([x - r + dx, y - r * 0.8 + dy,
                       x + r + dx, y + r * 0.8 + dy], fill=t)

    masque = cyclique(cote, tracer, fond=40)
    # `relief` pilote l'arrondi des galets : à 0,1 ils sont plats et nets, à
    # 1,0 ils bombent. Un réglage qui ne changerait rien serait un mensonge, et
    # le banc en attrape un par générateur.
    r = max(0.1, min(1.0, p["relief"]))
    hauteur = _lisser(masque, max(1.5, cote / n * 0.06 + cote / n * 0.20 * r))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 4, graine, 0.5), 0.3)


def _metal_brosse(cote, p, graine):
    # Le brossage EST une anisotropie : un bruit fin étiré dans un sens.
    fin = bruit(cote, 64, 3, 0.6, graine)
    brosse = etirer(fin, 1, max(4, int(p["longueur"])))
    k = max(0.05, min(1.0, p["force"]))
    hauteur = brosse.point([PBR.clamp8(128.0 + (v - 128.0) * k)
                            for v in range(256)])
    large = bruit(cote, 4, 2, 0.5, graine + 7).point(
        [PBR.clamp8(128.0 + (v - 128.0) * 0.25) for v in range(256)])
    return hauteur, ImageChops.add(hauteur, large, 2.0, 0)


def _cuir(cote, p, graine):
    n = max(6, int(p["cellules"]))
    rng = random.Random(graine ^ 0xC01A)
    cells_ = [(rng.random() * cote, rng.random() * cote,
               cote / n * (0.5 + 0.6 * rng.random())) for _ in range(n * n)]

    def tracer(d, dx, dy):
        for x, y, r in cells_:
            d.ellipse([x - r + dx, y - r + dy, x + r + dx, y + r + dy],
                      fill=230)

    grosses = _lisser(cyclique(cote, tracer, fond=90), max(1.5, cote / n * 0.2))
    pores = _grain(cote, 96, 3, graine + 3, max(0.05, min(1.0, p["pores"])))
    hauteur = _melanger(grosses, pores, 0.35)
    return hauteur, hauteur


def _tissu(cote, p, graine):
    # ARMURE TOILE : un fil de chaîne sur deux passe au-dessus. Deux familles
    # de bandes et un damier qui décide laquelle domine — périodique par
    # construction dès que le nombre de fils divise le côté.
    n = int(p["fils"])
    t = cote / n

    def bandes(vertical):
        def tracer(d, dx, dy):
            for i in range(-1, n + 1):
                if vertical:
                    x = i * t + dx
                    d.rectangle([x + t * 0.12, dy - cote,
                                 x + t * 0.88, dy + 2 * cote], fill=235)
                else:
                    y = i * t + dy
                    d.rectangle([dx - cote, y + t * 0.12,
                                 dx + 2 * cote, y + t * 0.88], fill=235)
        return cyclique(cote, tracer, fond=60)

    def damier(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                if (r + c) % 2:
                    d.rectangle([c * t + dx, r * t + dy,
                                 (c + 1) * t + dx, (r + 1) * t + dy], fill=255)

    dessus = cyclique(cote, damier, fond=0)
    croise = Image.composite(bandes(True), bandes(False), dessus)
    hauteur = _lisser(croise, max(1.0, t * 0.18))
    return hauteur, _melanger(hauteur, _grain(cote, 96, 3, graine, 0.4), 0.25)


def _rayures(cote, p, graine):
    n = int(p["bandes"])
    t = cote / n
    ang = int(p["angle"])
    part = max(0.05, min(0.95, p["largeur"]))

    def tracer(d, dx, dy):
        for i in range(-2, 2 * n + 2):
            if ang == 0:
                d.rectangle([dx - cote, i * t + dy, dx + 2 * cote,
                             i * t + t * part + dy], fill=235)
            elif ang == 90:
                d.rectangle([i * t + dx, dy - cote,
                             i * t + t * part + dx, dy + 2 * cote], fill=235)
            else:
                s = 1 if ang == 45 else -1
                d.line([(i * t + dx - cote, dy - s * cote),
                        (i * t + dx + 2 * cote, dy + 2 * s * cote)],
                       fill=235, width=max(1, int(t * part)))

    masque = cyclique(cote, tracer, fond=55)
    hauteur = _lisser(masque, max(1.0, t * 0.12))
    return hauteur, _melanger(hauteur, _grain(cote, 48, 3, graine, 0.3), 0.2)


# `f` = flottant borné, `i` = entier borné, `e` = liste fermée, `c` = couleur.
GENERATEURS = [
    {"id": "briques", "label": "Briques", "sombre": "#3a2620", "clair": "#b2705a",
     "params": [{"k": "rangs", "type": "i", "min": 2, "max": 32, "def": 8},
                {"k": "colonnes", "type": "i", "min": 1, "max": 16, "def": 4},
                {"k": "joint", "type": "f", "min": 0.02, "max": 0.30, "def": 0.10},
                {"k": "decalage", "type": "f", "min": 0.0, "max": 0.5, "def": 0.5}]},
    {"id": "carrelage", "label": "Carrelage", "sombre": "#2b3138", "clair": "#cfd6dd",
     "params": [{"k": "cases", "type": "i", "min": 2, "max": 24, "def": 6},
                {"k": "joint", "type": "f", "min": 0.02, "max": 0.25, "def": 0.08},
                {"k": "arrondi", "type": "f", "min": 0.0, "max": 1.0, "def": 0.3}]},
    {"id": "planches", "label": "Planches", "sombre": "#3b2a18", "clair": "#c39a63",
     "params": [{"k": "planches", "type": "i", "min": 2, "max": 16, "def": 5},
                {"k": "joint", "type": "f", "min": 0.01, "max": 0.20, "def": 0.05},
                {"k": "fil", "type": "i", "min": 2, "max": 64, "def": 24}]},
    {"id": "damier", "label": "Damier", "sombre": "#1c1c20", "clair": "#e6e6ea",
     "params": [{"k": "cases", "type": "i", "min": 2, "max": 32, "def": 8},
                {"k": "bord", "type": "f", "min": 0.0, "max": 1.0, "def": 0.2}]},
    {"id": "hexagones", "label": "Hexagones", "sombre": "#242a2e", "clair": "#a9b6bf",
     "params": [{"k": "colonnes", "type": "i", "min": 2, "max": 20, "def": 6},
                {"k": "rangs", "type": "i", "min": 2, "max": 20, "def": 8},
                {"k": "joint", "type": "f", "min": 0.05, "max": 0.6, "def": 0.25}]},
    {"id": "galets", "label": "Galets", "sombre": "#2a2a28", "clair": "#b8b5ab",
     "params": [{"k": "densite", "type": "i", "min": 4, "max": 24, "def": 9},
                {"k": "relief", "type": "f", "min": 0.1, "max": 1.0, "def": 0.6}]},
    {"id": "metal_brosse", "label": "Métal brossé", "sombre": "#5a5f66", "clair": "#d7dce2",
     "params": [{"k": "longueur", "type": "i", "min": 4, "max": 128, "def": 48},
                {"k": "force", "type": "f", "min": 0.05, "max": 1.0, "def": 0.45}]},
    {"id": "cuir", "label": "Cuir", "sombre": "#2a1b14", "clair": "#8c5c3d",
     "params": [{"k": "cellules", "type": "i", "min": 6, "max": 40, "def": 16},
                {"k": "pores", "type": "f", "min": 0.1, "max": 1.0, "def": 0.6}]},
    {"id": "tissu", "label": "Tissu", "sombre": "#33384a", "clair": "#98a2bd",
     "params": [{"k": "fils", "type": "i", "min": 4, "max": 64, "def": 24}]},
    {"id": "rayures", "label": "Rayures", "sombre": "#1e2430", "clair": "#d5dbe6",
     "params": [{"k": "bandes", "type": "i", "min": 2, "max": 48, "def": 10},
                {"k": "largeur", "type": "f", "min": 0.1, "max": 0.9, "def": 0.5},
                {"k": "angle", "type": "e", "choix": (0, 45, 90, 135), "def": 0}]},
]

_FONCTIONS = {"briques": _briques, "carrelage": _carrelage,
              "planches": _planches, "damier": _damier,
              "hexagones": _hexagones, "galets": _galets,
              "metal_brosse": _metal_brosse, "cuir": _cuir,
              "tissu": _tissu, "rayures": _rayures}
_PAR_ID = {g["id"]: g for g in GENERATEURS}


def clean_params(gid: str, raw) -> dict:
    """Réglages complets et bornés. Ne lève jamais (même règle que
    `material_store.normalize_material`) : l'entrée vient du réseau."""
    g = _PAR_ID.get(str(gid or ""))
    if g is None:
        return {}
    src = raw if isinstance(raw, dict) else {}
    out = {}
    for c in g["params"]:
        v = src.get(c["k"])
        if c["type"] == "e":
            try:
                iv = int(v)
            except (TypeError, ValueError):
                iv = c["def"]
            out[c["k"]] = iv if iv in c["choix"] else c["def"]
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            fv = float(c["def"])
        if fv != fv or fv in (float("inf"), float("-inf")):
            fv = float(c["def"])
        fv = max(float(c["min"]), min(float(c["max"]), fv))
        out[c["k"]] = int(round(fv)) if c["type"] == "i" else round(fv, 4)
    return out


def generer(gid: str, cote: int, params: dict, graine: int = 0,
            sombre: str = "", clair: str = "") -> dict:
    """{basecolor, height} d'un générateur. Les six autres cartes se dérivent
    ensuite par `pbr_service.derive_maps` — un seul chemin de dérivation dans
    tout le produit."""
    g = _PAR_ID.get(str(gid or ""))
    if g is None:
        raise ValueError(f"générateur « {gid} » inconnu — connus : "
                         f"{', '.join(_PAR_ID)}")
    n = max(64, int(cote))
    hauteur, motif = _FONCTIONS[g["id"]](n, clean_params(g["id"], params),
                                         int(graine))
    return {"height": hauteur,
            "basecolor": colorer(motif, sombre or g["sombre"],
                                 clair or g["clair"])}
```

- [ ] **Step 4 : relancer, voir vert, mesurer**

```
python tests/test_pattern_service.py
```

Attendu : sept lignes `✓`, deux lignes de budget, puis
`OK — 7 assertions groupées vertes (pattern_service, socle)`. Si un générateur
dépasse 2,5 s à 1024², réduire son nombre d'octaves de grain (jamais le
bordage) et remesurer.

- [ ] **Step 5 : les deux routes**

Dans `routes.py`, après `material_catalog_import` :

```python
@router.get("/materials/patterns")
async def list_material_patterns():
    """Les générateurs paramétriques locaux, avec leurs réglages et leurs
    bornes. L'écran ne recopie AUCUN chiffre : il lit cette liste."""
    from app.services import pattern_service as PS
    return {"patterns": [
        {"id": g["id"], "label": g["label"], "sombre": g["sombre"],
         "clair": g["clair"],
         "params": [{**c, "choix": list(c.get("choix", []))}
                    for c in g["params"]]}
        for g in PS.GENERATEURS],
        "budget_s": PS.BUDGET_MOTIF_1024}


@router.post("/materials/patterns/{gid}")
async def generate_material_pattern(gid: str, body: dict = None):
    """Fabrique une matière depuis un générateur. LOCAL ET GRATUIT : aucune
    clé, aucun réseau, aucun crédit — et c'est l'argument de ce bac."""
    from app.services import material_store as MS
    from app.services import pattern_service as PS
    body = body if isinstance(body, dict) else {}
    res = MS.clean_res(body.get("res"), 1024)
    params = PS.clean_params(gid, body.get("params"))
    if not params and gid not in {g["id"] for g in PS.GENERATEURS}:
        raise HTTPException(400, f"générateur « {gid} » inconnu")
    graine = 0
    try:
        graine = int(body.get("seed") or 0)
    except (TypeError, ValueError):
        graine = 0

    def _travail():
        from app.services import pbr_service as PBR
        deux = PS.generer(gid, res, params, graine,
                          str(body.get("sombre") or ""),
                          str(body.get("clair") or ""))
        mat = MS.create_material(
            name=MS.clean_name(body.get("name")
                               or next(g["label"] for g in PS.GENERATEURS
                                       if g["id"] == gid)),
            prompt="", full_prompt="", res=res, seamless=True,
            seam={"before": None, "after": None},
            source={"kind": "pattern", "model": gid, "filename": None,
                    "prep": None})
        maps = PBR.derive_maps(deux["basecolor"], mat["derive"],
                               list(MS.SECONDARY_MAPS))
        # la hauteur du GÉNÉRATEUR l'emporte sur celle dérivée de la couleur :
        # il la connaît exactement, la dérivation ne fait que l'estimer
        maps["height"] = deux["height"]
        maps["normal"] = PBR.derive_maps(
            deux["height"].convert("RGB"), mat["derive"], ["normal"])["normal"]
        maps["basecolor"] = deux["basecolor"]
        maps["orm"] = Image.merge("RGB", (maps["ao"].convert("L"),
                                          maps["roughness"].convert("L"),
                                          maps["metallic"].convert("L")))
        MS.save_maps(mat["id"], maps)
        m = MS.read_material(mat["id"])
        m["props"] = MS.merge_props(m["props"], MS.natural_levels(maps))
        m["pattern"] = {"id": gid, "params": params, "seed": graine}
        m = MS.refresh_report(m, maps)
        MS.write_material(m)
        return MS.read_material(mat["id"])

    try:
        return {"material": await asyncio.to_thread(_travail)}
    except ValueError as e:
        raise HTTPException(400, str(e))
```

`Image` vient de `PILImage` dans ce fichier : écrire
`PILImage.merge` et non `Image.merge`. Ajouter `"pattern"` à `SOURCE_KINDS`
(`material_store.py:151`) et conserver le bloc `pattern` dans
`normalize_material` :

```python
        # Le générateur et ses réglages, pour rouvrir la matière dans l'onglet
        # Générateurs et la refaire autrement. Vide pour toute autre matière.
        "pattern": ({"id": str(raw["pattern"].get("id") or "")[:40],
                     "params": {k: v for k, v in
                                (raw["pattern"].get("params") or {}).items()
                                if isinstance(k, str)},
                     "seed": int(raw["pattern"].get("seed") or 0)}
                    if isinstance(raw.get("pattern"), dict)
                    and raw["pattern"].get("id") else None),
```

- [ ] **Step 6 : le banc d'API**

Créer `backend/tests/test_pattern_api.py`, sur le patron d'en-tête de
`test_materials_prep_api.py` (mêmes variables d'environnement, même
`ASGITransport`), avec ces assertions :

```python
        d = (await c.get("/api/materials/patterns")).json()
        assert len(d["patterns"]) == 10
        for g in d["patterns"]:
            assert g["params"] and all({"k", "type"} <= set(p) for p in g["params"])
        ok("GET /materials/patterns : dix générateurs, leurs bornes publiées")

        r = await c.post("/api/materials/patterns/briques",
                         json={"res": 512, "params": {"rangs": 6},
                               "name": "Mur de test"})
        assert r.status_code == 200, r.text
        m = r.json()["material"]
        assert m["maps"] == list(MS.MAP_KINDS), m["maps"]
        assert m["pattern"]["id"] == "briques"
        assert m["pattern"]["params"]["rangs"] == 6
        assert m["source"]["kind"] == "pattern"
        with Image.open(MS.map_path(m["id"], "height")) as im:
            st = PBR.stats(im.convert("L"))
        assert st["span"] > 8, st
        ok(f"POST /materials/patterns/briques : matière {m['id']} complète, "
           f"hauteur RELUE sur le disque d'amplitude {st['span']}")

        r = await c.post("/api/materials/patterns/nexistepas", json={})
        assert r.status_code == 400 and "nexistepas" in r.json()["detail"]
        ok("générateur inconnu : 400 nommé")
```

- [ ] **Step 7 : lancer les deux bancs, commit**

```
python tests/test_pattern_service.py
python tests/test_pattern_api.py
```

```bash
git add backend/app/services/pattern_service.py backend/app/services/material_store.py backend/app/api/routes.py backend/tests/test_pattern_service.py backend/tests/test_pattern_api.py
git commit -m 'matieres D1 : dix generateurs parametriques, locaux et gratuits

Briques, carrelage, planches, damier, hexagones, galets, metal brosse, cuir,
tissu, rayures. Chacun rend basecolor et height ; les six autres cartes
passent par pbr_service.derive_maps, exactement comme une photo — un
generateur n a aucune raison d avoir son propre chemin de derivation, et en
avoir un ferait deux verites.

La periodicite est IMPOSEE par les parametres, pas esperee : les motifs se
reglent en nombre de rangs et de colonnes, jamais en taille de brique. Une
brique de 37 px sur une tuile de 256 ne pave pas, et laisser l utilisateur la
choisir serait lui vendre un raccord qu on ne peut pas tenir. Les angles de
rayures sont une liste fermee pour la meme raison. Les hexagones sont
legerement etires et c est assume : un hexagone regulier ne pave pas un carre
en nombre entier de mailles, et le raccord vaut mieux qu une regularite que
personne ne mesure.

Mesure, sur les dix : rapport de couture sous 2,0, hauteur d amplitude utile,
sortie deterministe a graine egale, et le premier reglage numerique de chacun
change vraiment la carte — un curseur qui ne fait rien est un mensonge, le
banc en attrape dix d un coup.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 13 : D1 — l'onglet « Générateurs », réglages en direct

**Files:**
- Modify: `frontend/materialforge/index.html:32-104` (le rail gauche gagne deux onglets)
- Modify: `frontend/materialforge/materialforge.js:3272` (`wire`), `:3471` (`boot`)
- Modify: `frontend/materialforge/materialforge.css`
- Test: `backend/tests/test_materialforge_ecran.py` (nouvelle section)

- [ ] **Step 1 : ajouter la section rouge au banc**

Dans `backend/tests/test_materialforge_ecran.py`, avant le `print` final :

```python
# ══ 9 · l'onglet Générateurs ═══════════════════════════════════════════════
for ident in ("tabForge", "tabGen", "paneGen", "genList", "genParams",
              "genGo", "genPreview"):
    assert f'id="{ident}"' in HTML, ident
assert "/materials/patterns" in JS_CODE
ok("index.html : deux onglets de rail (Forger / Générateurs), liste, "
   "réglages, aperçu et bouton de création")

# Les bornes ne sont PAS recopiées dans le JS : elles viennent de la route.
corps_gen = JS_CODE.split("function renderGenParams(", 1)[1].split("\n}\n", 1)[0]
assert "p.min" in corps_gen and "p.max" in corps_gen, corps_gen[:400]
for interdit in ("min=\"2\"", "max=\"32\"", "briques", "hexagones"):
    assert interdit not in corps_gen, interdit
ok("les bornes et les identifiants de générateurs viennent de l'API : aucun "
   "chiffre ni aucun nom recopié dans l'écran")
```

- [ ] **Step 2 : lancer, voir rouge**

```
python tests/test_materialforge_ecran.py
```

Attendu : `AssertionError: tabForge`.

- [ ] **Step 3 : le balisage**

Dans `index.html`, en haut de `.rail-left` (ligne 33), avant le premier
`<details>` :

```html
    <div class="seg tall" id="railTabs">
      <button class="on" id="tabForge" type="button">⚒ Forger</button>
      <button id="tabGen" type="button">◈ Générateurs</button>
    </div>
    <div class="pane hidden" id="paneGen">
      <p class="hint">Motifs paramétriques, calculés en local : aucune clé,
        aucun crédit, aucun réseau. Le raccord est exact par construction.</p>
      <div class="chips" id="genList"></div>
      <div id="genParams"></div>
      <img id="genPreview" alt="aperçu du générateur" class="hidden">
      <button class="btn primary wide big" id="genGo">◈ Créer la matière</button>
    </div>
```

Envelopper les `<details>` existants du rail dans
`<div class="pane" id="paneForge"> … </div>`.

- [ ] **Step 4 : le comportement**

Dans `materialforge.js`, avant `wire()` :

```js
/* ── l'onglet Générateurs (D1) ──────────────────────────────────────────────
   AUCUNE borne, AUCUN identifiant de générateur n'est écrit ici : tout vient
   de GET /materials/patterns. Recopier un min/max dans l'écran, c'est signer
   pour qu'il dérive du serveur au premier réglage ajouté — et le banc
   interdit littéralement ces recopies. */
const gen = { liste: [], choisi: null, params: {}, seed: 0, apercu: null };

async function loadPatterns() {
  const d = await api.get("/materials/patterns");
  gen.liste = d.patterns || [];
  gen.choisi = gen.liste[0] ? gen.liste[0].id : null;
  $("#genList").innerHTML = gen.liste.map((g) =>
    `<button class="chip${g.id === gen.choisi ? " on" : ""}" `
    + `data-gen="${esc(g.id)}">${esc(g.label)}</button>`).join("");
  $$("#genList .chip").forEach((c) => c.addEventListener("click", () => {
    gen.choisi = c.dataset.gen;
    gen.params = {};
    $$("#genList .chip").forEach((x) => x.classList.toggle(
      "on", x.dataset.gen === gen.choisi));
    renderGenParams();
  }));
  renderGenParams();
}

function renderGenParams() {
  const g = gen.liste.find((x) => x.id === gen.choisi);
  const box = $("#genParams");
  if (!g) { box.innerHTML = ""; return; }
  box.innerHTML = g.params.map((p) => {
    const v = gen.params[p.k] !== undefined ? gen.params[p.k] : p.def;
    if (p.type === "e") {
      return `<label class="mini">${esc(p.k)}<select data-p="${esc(p.k)}">${
        p.choix.map((c) => `<option value="${c}"${c === v ? " selected" : ""}>`
          + `${c}</option>`).join("")}</select></label>`;
    }
    const pas = p.type === "i" ? 1 : 0.01;
    return `<label class="mini">${esc(p.k)} <b>${v}</b>`
      + `<input type="range" data-p="${esc(p.k)}" min="${p.min}" `
      + `max="${p.max}" step="${pas}" value="${v}"></label>`;
  }).join("");
  box.querySelectorAll("[data-p]").forEach((el) => {
    el.addEventListener("input", () => {
      gen.params[el.dataset.p] = Number(el.value);
      const b = el.parentElement.querySelector("b");
      if (b) b.textContent = el.value;
      genPreviewSoon();
    });
  });
  genPreviewSoon();
}

let genTimer = null;
function genPreviewSoon() {
  /* 220 ms d'attente : un curseur qui glisse envoie trente valeurs, et
     trente motifs de 256 px coûteraient sept secondes de serveur pour un
     seul geste. On ne montre que la dernière. */
  clearTimeout(genTimer);
  genTimer = setTimeout(async () => {
    if (!gen.choisi) return;
    const q = new URLSearchParams({ res: "256", seed: String(gen.seed) });
    Object.entries(gen.params).forEach(([k, v]) => q.set("p_" + k, String(v)));
    const img = $("#genPreview");
    img.src = `/api/materials/patterns/${encodeURIComponent(gen.choisi)}`
      + `/preview.png?${q.toString()}`;
    img.classList.remove("hidden");
  }, 220);
}
```

Cet aperçu suppose une troisième route, légère et sans écriture — l'ajouter
dans `routes.py` à côté des deux autres :

```python
@router.get("/materials/patterns/{gid}/preview.png")
async def preview_material_pattern(gid: str, request: Request,
                                   res: int = 256, seed: int = 0):
    """L'aperçu d'un générateur : une base color, rien d'écrit, rien de créé.

    Les réglages arrivent en `p_<nom>` dans la requête plutôt qu'en corps
    JSON : c'est un GET, donc le navigateur le met en cache tout seul et un
    curseur qui repasse par une valeur déjà vue ne recalcule rien."""
    from app.services import pattern_service as PS
    if gid not in {g["id"] for g in PS.GENERATEURS}:
        raise HTTPException(404, f"générateur « {gid} » inconnu")
    params = {k[2:]: v for k, v in request.query_params.items()
              if k.startswith("p_")}
    cote = 128 if int(res or 256) < 192 else min(512, int(res))

    def _travail():
        import io as _io
        out = PS.generer(gid, cote, PS.clean_params(gid, params), int(seed))
        buf = _io.BytesIO()
        out["basecolor"].save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    return Response(content=await asyncio.to_thread(_travail),
                    media_type="image/png",
                    headers={"Cache-Control": "private, max-age=600"})
```

Dans `wire()` :

```js
  $("#tabForge").addEventListener("click", () => setRailTab("forge"));
  $("#tabGen").addEventListener("click", () => setRailTab("gen"));
  $("#genGo").addEventListener("click", async () => {
    if (!gen.choisi) return;
    $("#genGo").disabled = true;
    try {
      const d = await api.post(`/materials/patterns/${gen.choisi}`,
                               { res: state.res, params: gen.params,
                                 seed: gen.seed });
      await loadMaterials();
      openMaterial(d.material.id);
      toast(`Matière « ${d.material.name} » créée en local, sans crédit.`);
    } catch (e) { apiFail(e, "génération de motif"); }
    finally { $("#genGo").disabled = false; }
  });
```

et définir, à côté :

```js
function setRailTab(quel) {
  $("#paneForge").classList.toggle("hidden", quel !== "forge");
  $("#paneGen").classList.toggle("hidden", quel !== "gen");
  $("#tabForge").classList.toggle("on", quel === "forge");
  $("#tabGen").classList.toggle("on", quel === "gen");
  if (quel === "gen" && !gen.liste.length) loadPatterns();
}
```

Dans `boot()` (ligne 3471), rien à ajouter : la liste se charge à la première
ouverture de l'onglet — un écran qui ne montre pas encore les générateurs n'a
aucune raison de payer leur requête.

- [ ] **Step 5 : le style, le banc, l'écran, le commit**

```css
/* ── onglets du rail et générateurs (D1) ────────────────────────────────── */
#railTabs { display: flex; margin-bottom: 8px; }
#railTabs button { flex: 1; }
#genPreview { width: 100%; height: auto; display: block; margin: 8px 0;
  border: 1px solid var(--line, #222831); border-radius: 6px; }
#genParams .mini { display: block; margin: 6px 0; }
```

```
python tests/test_materialforge_ecran.py
```

Attendu : dix lignes `✓`. À l'écran : glisser « rangs » redessine l'aperçu en
moins d'une demi-seconde, et « Créer la matière » ouvre l'inspecteur sur une
matière neuve, sans aucun crédit dépensé.

```bash
git add frontend/materialforge/index.html frontend/materialforge/materialforge.js frontend/materialforge/materialforge.css backend/app/api/routes.py backend/tests/test_materialforge_ecran.py
git commit -m 'matieres D1 : l onglet Generateurs, regle en direct

AUCUNE borne, AUCUN identifiant de generateur n est ecrit dans l ecran : tout
vient de GET /materials/patterns, et le banc INTERDIT litteralement les
recopies (il cherche min=2, max=32, briques, hexagones dans la fonction de
rendu et rougit s il les trouve). Recopier un min dans l ecran, c est signer
pour qu il derive du serveur au premier reglage ajoute.

L apercu est un GET avec les reglages en p_<nom> : le navigateur le met en
cache tout seul, donc un curseur qui repasse par une valeur deja vue ne
recalcule rien. Et 220 ms d attente avant l envoi — un curseur qui glisse
emet trente valeurs, et trente motifs couteraient sept secondes de serveur
pour un seul geste.

Cout de patch : ZERO.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---
### Task 14 : D2 — les masques de cavités et d'arêtes, calculés depuis la géométrie

**Files:**
- Modify: `backend/app/services/print3d.py:87-134` (réexports publics `chunks`, `accesseur`)
- Modify: `backend/app/services/mesh_paint.py` (masques, COLOR_0, budget)
- Test: `backend/tests/test_mesh_paint.py` (nouvelle section)

- [ ] **Step 1 : ajouter la section rouge**

Dans `backend/tests/test_mesh_paint.py`, avant le `print` final :

```python
# ══ 6 · cavités et arêtes, lues sur la GÉOMÉTRIE ═══════════════════════════
import time                                                     # noqa: E402

rap = MP.masques(CUBE)
assert rap["primitives"] and rap["sommets"] > 0, rap
p0 = rap["primitives"][0]
for cle in ("maillage", "primitive", "sommets", "cavite_moy", "arete_moy"):
    assert cle in p0, (cle, p0)
# Un CUBE n'a que des arêtes convexes : l'arête moyenne domine largement la
# cavité moyenne. C'est le témoin le moins discutable qui soit.
assert p0["arete_moy"] > 3.0 * max(1.0, p0["cavite_moy"]), p0
ok(f"cube : arête moyenne {p0['arete_moy']} contre cavité {p0['cavite_moy']} "
   f"— un cube n'a que des arêtes saillantes")

# Un TORE a des deux : la gorge intérieure est concave.
TORE = gltf_builder.build_glb({}, None, "torus", "banc")
rt = MP.masques(TORE)["primitives"][0]
assert rt["cavite_moy"] > 5.0, rt
assert rt["arete_moy"] > 5.0, rt
ok(f"tore : cavité {rt['cavite_moy']} ET arête {rt['arete_moy']} — la gorge "
   f"intérieure est concave, le bourrelet extérieur convexe")

# ══ 7 · le GLB de masques porte un COLOR_0 lisible ═════════════════════════
vu = MP.masques_glb(TORE)
dv, bv = mesh_edit.lire_glb(vu)
prim = dv["meshes"][0]["primitives"][0]
assert "COLOR_0" in prim["attributes"], prim["attributes"]
acc = dv["accessors"][prim["attributes"]["COLOR_0"]]
assert acc["type"] == "VEC4" and acc["componentType"] == 5121
assert acc.get("normalized") is True, acc
pos = dv["accessors"][prim["attributes"]["POSITION"]]
assert acc["count"] == pos["count"], (acc["count"], pos["count"])
couleurs = print3d.accesseur(dv, bv, prim["attributes"]["COLOR_0"])
assert max(c[0] for c in couleurs) > 40, "aucune cavité écrite"
assert max(c[1] for c in couleurs) > 40, "aucune arête écrite"
assert all(c[3] == 255 for c in couleurs)
assert print3d.lire_glb_triangles(vu), "le GLB de masques n'est plus lisible"
ok(f"GLB de masques : COLOR_0 VEC4 normalisé sur {acc['count']} sommets, "
   f"R = cavité, V = arête, A = 255")

# ══ 8 · budget sur 100 000 triangles ═══════════════════════════════════════
gros = gltf_builder.build_glb({}, None, "sphere", "banc")
n_tris = len(print3d.lire_glb_triangles(gros))
t0 = time.perf_counter()
MP.masques(gros)
dt = time.perf_counter() - t0
par_100k = dt * 100000.0 / max(1, n_tris)
assert par_100k < MP.BUDGET_MASQUES_100K, (n_tris, dt, par_100k)
print(f"\n  masques : {n_tris} triangles en {dt:.2f} s, soit "
      f"{par_100k:.1f} s pour 100 000 (budget "
      f"{MP.BUDGET_MASQUES_100K:.0f} s)")
```

- [ ] **Step 2 : lancer, voir rouge**

```
python tests/test_mesh_paint.py
```

Attendu : `AttributeError: module 'app.services.mesh_paint' has no attribute 'masques'`.

- [ ] **Step 3 : ouvrir `print3d` de deux noms**

Dans `backend/app/services/print3d.py`, juste après `_accessor` (fin ligne
133), ajouter :

```python
# Réexports PUBLICS — un seul lecteur d'accesseurs dans le dépôt.
#
# `mesh_paint` a besoin des POSITIONS et des INDICES par primitive pour
# calculer ses masques. Les relire ailleurs ferait un SECOND décodeur
# d'accesseurs, avec ses propres refus et ses propres oublis (le `byteStride`,
# par exemple, que celui-ci honore et qu'une copie hâtive oublie toujours).
chunks = _chunks
accesseur = _accessor
```

- [ ] **Step 4 : écrire les masques**

Ajouter à la fin de `backend/app/services/mesh_paint.py` (et à `__all__` :
`"BUDGET_MASQUES_100K", "masques", "masques_glb"`) :

```python
# ── masques de cavités et d'arêtes (R10c D2) ────────────────────────────────
#
# CE QU'ON MESURE, ET CE QU'ON NE PROMET PAS. Une occlusion ambiante VRAIE se
# calcule par lancer de rayons ; en Python pur, sur 100 000 triangles, ce
# serait des minutes. On mesure donc la COURBURE, à trois échelles, et on
# l'appelle par son nom : « cavité » là où la surface se creuse, « arête » là
# où elle se casse. C'est ce dont l'usure a besoin — la crasse s'accumule dans
# les creux, la peinture s'écaille sur les arêtes — et c'est exactement le même
# raisonnement que `pbr_service._cavity`, qui mesure `flou(H) - H` plutôt que
# de lancer des rayons dans une image.
#
# L'ESTIMATEUR. Pour un sommet v de normale n(v), la moyenne sur ses voisins u
# de `dot(normalize(u - v), n(v))` est positive quand le voisinage remonte le
# long de la normale — donc quand v est au FOND de quelque chose — et négative
# quand il redescend, donc sur une saillie. Trois échelles (1, 2 et 3 anneaux)
# comme les trois octaves de l'AO de `pbr_service` : une seule échelle ne voit
# que les creux de sa propre taille.
#
# LE BUDGET EST MESURÉ, PAS ESPÉRÉ. Le banc chronomètre et rapporte à
# 100 000 triangles ; au-delà de la borne, il échoue.
BUDGET_MASQUES_100K = 12.0

_MASQUE_OCTAVES = ((1, 0.5), (2, 0.3), (3, 0.2))
_MASQUE_GAIN = 6.0          # même esprit que `pbr_service._AO_GAIN` : sans
                            # gain, la courbure d'un maillage dense est un
                            # centième et la carte sort blanche


def _souder(pos, idx):
    """Sommets soudés par position arrondie, et l'adjacence 1-anneau.

    SOUDER N'EST PAS FACULTATIF : un cube exporté a 24 sommets pour 8 coins
    (chaque face porte les siens, pour ses normales). Sans soudure, aucun
    sommet n'aurait de voisin d'une autre face, et une arête — qui EST la
    rencontre de deux faces — serait rigoureusement invisible."""
    cle_de, rep = {}, []
    for p in pos:
        k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
        j = cle_de.get(k)
        if j is None:
            j = len(cle_de)
            cle_de[k] = j
        rep.append(j)
    n = len(cle_de)
    points = [None] * n
    for i, p in enumerate(pos):
        points[rep[i]] = (p[0], p[1], p[2])
    voisins = [set() for _ in range(n)]
    normales = [[0.0, 0.0, 0.0] for _ in range(n)]
    for t in range(0, len(idx) - 2, 3):
        a, b, c = rep[idx[t]], rep[idx[t + 1]], rep[idx[t + 2]]
        voisins[a].update((b, c))
        voisins[b].update((a, c))
        voisins[c].update((a, b))
        pa, pb, pc = points[a], points[b], points[c]
        u = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        v = (pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2])
        # produit vectoriel NON normalisé : sa longueur est deux fois l'aire,
        # donc la somme pondère naturellement par l'aire des faces
        nx = u[1] * v[2] - u[2] * v[1]
        ny = u[2] * v[0] - u[0] * v[2]
        nz = u[0] * v[1] - u[1] * v[0]
        for s in (a, b, c):
            normales[s][0] += nx
            normales[s][1] += ny
            normales[s][2] += nz
    return rep, points, voisins, normales


def _courbure(points, voisins, normales) -> list:
    """Courbure signée par sommet : > 0 dans un creux, < 0 sur une saillie."""
    import math
    out = [0.0] * len(points)
    for i, p in enumerate(points):
        n = normales[i]
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if ln < 1e-12 or not voisins[i]:
            continue
        nx, ny, nz = n[0] / ln, n[1] / ln, n[2] / ln
        s = 0.0
        for j in voisins[i]:
            q = points[j]
            dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d < 1e-12:
                continue
            s += (dx * nx + dy * ny + dz * nz) / d
        out[i] = s / len(voisins[i])
    return out


def _lisser_anneau(valeurs, voisins, tours: int) -> list:
    """Moyenne sur le 1-anneau, répétée — l'équivalent discret du flou de
    `pbr_service`, et c'est ainsi qu'on obtient les échelles supérieures sans
    parcourir un k-anneau explicite (quadratique)."""
    cur = valeurs
    for _ in range(max(0, tours)):
        suiv = list(cur)
        for i, vs in enumerate(voisins):
            if vs:
                suiv[i] = (cur[i] + sum(cur[j] for j in vs)) / (len(vs) + 1.0)
        cur = suiv
    return cur


def _octets_masques(courbure, voisins) -> tuple:
    """(cavités, arêtes) en octets 0-255, cumulées sur trois échelles."""
    cav = [0.0] * len(courbure)
    are = [0.0] * len(courbure)
    for tours, poids in _MASQUE_OCTAVES:
        c = _lisser_anneau(courbure, voisins, tours - 1)
        for i, v in enumerate(c):
            if v > 0:
                cav[i] += poids * v
            else:
                are[i] -= poids * v
    def _o(x):
        return PBR.clamp8(255.0 * x * _MASQUE_GAIN)
    return [_o(v) for v in cav], [_o(v) for v in are]


def _primitives_lues(data: bytes):
    """(doc, binc, [(m, p, positions, indices)]) — un seul lecteur
    d'accesseurs dans le dépôt : celui de `print3d`."""
    from app.services import print3d
    doc, binc = print3d.chunks(data)
    lots = []
    for m, mesh in enumerate(doc.get("meshes") or []):
        for p, prim in enumerate(mesh.get("primitives") or []):
            if prim.get("mode", 4) != 4:
                continue
            pos = print3d.accesseur(doc, binc, prim["attributes"]["POSITION"])
            if "indices" in prim:
                idx = [v[0] for v in print3d.accesseur(doc, binc,
                                                       prim["indices"])]
            else:
                idx = list(range(len(pos)))
            lots.append((m, p, pos, idx))
    return doc, binc, lots


def masques(data: bytes) -> dict:
    """Statistiques de cavité et d'arête, primitive par primitive."""
    _doc, _binc, lots = _primitives_lues(data)
    if not lots:
        raise ValueError("masques : ce GLB ne contient aucune primitive "
                         "triangulaire")
    out, total = [], 0
    for (m, p, pos, idx) in lots:
        rep, points, voisins, normales = _souder(pos, idx)
        cav, are = _octets_masques(_courbure(points, voisins, normales),
                                   voisins)
        n = max(1, len(points))
        total += n
        out.append({"maillage": m, "primitive": p, "sommets": len(pos),
                    "soudes": len(points),
                    "cavite_moy": round(sum(cav) / n, 1),
                    "arete_moy": round(sum(are) / n, 1)})
    return {"primitives": out, "sommets": total}


def masques_glb(data: bytes) -> bytes:
    """Le même maillage avec un COLOR_0 par sommet : R = cavité, V = arête.

    APERÇU SEULEMENT, et jamais une version : c'est une lecture. Les couleurs
    de sommet sont le seul canal qui n'exige AUCUN dépliage UV — et un modèle
    généré par un moteur image → 3D n'en a pas toujours."""
    from app.services import print3d
    doc, binc, lots = _primitives_lues(data)
    if not lots:
        raise ValueError("masques : ce GLB ne contient aucune primitive "
                         "triangulaire")
    tampon = _Tampon(binc)
    for (m, p, pos, idx) in lots:
        rep, points, voisins, normales = _souder(pos, idx)
        cav, are = _octets_masques(_courbure(points, voisins, normales),
                                   voisins)
        octets = bytearray()
        for i in range(len(pos)):
            j = rep[i]
            octets += bytes((cav[j], are[j], 0, 255))
        debut, n = tampon.ajouter(bytes(octets))
        views = doc.setdefault("bufferViews", [])
        views.append({"buffer": 0, "byteOffset": debut, "byteLength": n})
        accs = doc.setdefault("accessors", [])
        accs.append({"bufferView": len(views) - 1, "componentType": 5121,
                     "normalized": True, "count": len(pos), "type": "VEC4"})
        doc["meshes"][m]["primitives"][p]["attributes"]["COLOR_0"] = \
            len(accs) - 1
    octets = tampon.octets()
    doc["buffers"] = [{"byteLength": len(octets)}]
    return mesh_edit.ecrire_glb(doc, octets)
```

Et remplacer la ligne d'import de `mesh_paint.py` par :

```python
from app.services import mesh_edit, pbr_service as PBR
```

— le dépôt n'a qu'un seul écrêteur 8 bits (`pbr_service.clamp8`, réexporté en
T1), et en réécrire un ici en ferait deux.

- [ ] **Step 5 : relancer, mesurer, commit**

```
python tests/test_mesh_paint.py
```

Attendu : huit lignes `✓`, la ligne de budget, puis
`OK — 8 assertions groupées vertes (mesh_paint, habillage)`. Chiffre attendu :
la sphère de `gltf_builder` fait ~6 400 triangles ; le rapport à 100 000
devrait tomber entre 3 et 9 s.

```bash
git add backend/app/services/print3d.py backend/app/services/mesh_paint.py backend/tests/test_mesh_paint.py
git commit -m 'matieres D2 : cavites et aretes lues sur la geometrie

Une occlusion ambiante VRAIE se lance en rayons ; en Python pur sur 100 000
triangles ce serait des minutes. On mesure donc la COURBURE, a trois echelles,
et on l appelle par son nom : cavite la ou la surface se creuse, arete la ou
elle se casse. C est ce dont l usure a besoin — la crasse s accumule dans les
creux, la peinture s ecaille sur les aretes — et c est le meme raisonnement
que pbr_service._cavity, qui mesure flou(H) moins H plutot que de lancer des
rayons dans une image.

Souder n est pas facultatif : un cube exporte a 24 sommets pour 8 coins,
chaque face portant les siens pour ses normales. Sans soudure, aucun sommet n
aurait de voisin d une autre face, et une arete — qui EST la rencontre de deux
faces — serait rigoureusement invisible. Le banc le prouve sur un cube (arete
moyenne trois fois la cavite) et sur un tore (les deux, la gorge est concave).

COLOR_0 par sommet, VEC4 normalise : le seul canal qui n exige AUCUN depliage
UV, et un modele venu d un moteur image vers 3D n en a pas toujours. Apercu
seulement, jamais une version.

Budget mesure et rapporte a 100 000 triangles, le banc echoue au-dela.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 15 : D2 — une matière PAR PARTIE, écrite par la seule plume

**Files:**
- Modify: `backend/app/api/routes.py:9419-9500` (deux routes de plus, même porte)
- Modify: `frontend/etabli/etabli.js:2052-2230` (`rendreParties` : sélecteur de matière et deux boutons)
- Test: `backend/tests/test_etabli_habiller.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_etabli_habiller.py`, en-tête sur le patron de
`test_materials_prep_api.py`, puis :

```python
async def main():
    global PASS
    from app.services import gltf_builder, mesh_edit, mesh_report, print3d
    # un job d'Établi minimal : model.glb dans son dossier
    job = "banc_habiller"
    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, "cube",
                                                         "banc"))
    mat = _fabriquer_matiere()          # helper local, cf. test_material_naming

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=180) as c:
        # ══ 1 · les masques se LISENT, sans rien écrire ══════════════════════
        avant = sorted(p.name for p in d.iterdir())
        r = await c.get(f"/api/etabli/masques?job={job}&version=1")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("model/gltf-binary")
        doc, binc = mesh_edit.lire_glb(r.content)
        assert "COLOR_0" in doc["meshes"][0]["primitives"][0]["attributes"]
        assert sorted(p.name for p in d.iterdir()) == avant, "une écriture !"
        ok("GET /etabli/masques : un GLB à COLOR_0, et RIEN d'écrit sur le "
           "disque du job")

        # ══ 2 · l'habillage écrit une VERSION, par la seule plume ════════════
        r = await c.post("/api/etabli/habiller",
                         json={"job": job, "version": 1,
                               "lots": [{"cible": "tout", "mid": mat["id"]}]})
        assert r.status_code == 200, r.text
        fiche = r.json()
        assert (d / "model.v2.glb").is_file(), sorted(p.name for p in d.iterdir())
        assert (d / "model.glb").read_bytes() == \
            gltf_builder.build_glb({}, None, "cube", "banc"), \
            "la version 1 a été touchée"
        doc2, _ = mesh_edit.lire_glb((d / "model.v2.glb").read_bytes())
        assert doc2["materials"][-1]["name"] == mat["name"]
        assert {p.get("material") for m in doc2["meshes"]
                for p in m["primitives"]} == {len(doc2["materials"]) - 1}
        reg = mesh_report.read_registry(job)
        derniere = reg["versions"][-1] if isinstance(reg.get("versions"), list) \
            else list(reg.values())[-1]
        assert "habiller" in json.dumps(derniere, ensure_ascii=False)
        assert mat["id"] in json.dumps(derniere, ensure_ascii=False)
        ok("POST /etabli/habiller : model.v2.glb écrit par mesh_edit, v1 "
           "intacte à l'octet, la fiche nomme l'opération et la matière")

        # ══ 3 · les refus, avec le même vocabulaire que les cinq voisines ════
        for corps, code, mot in (
                ({"job": job, "version": 0,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 400, "version"),
                ({"job": job, "version": 1, "lots": []}, 400, "lots"),
                ({"job": job, "version": 1,
                  "lots": [{"cible": "tout", "mid": "mat_zzzzzzzz"}]}, 404,
                 "mat_zzzzzzzz"),
                ({"job": "../evade", "version": 1,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 400, "job"),
                ({"job": job, "version": 9,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 404,
                 "model.v9.glb")):
            r = await c.post("/api/etabli/habiller", json=corps)
            assert r.status_code == code, (corps, r.status_code, r.text)
            assert mot in r.json()["detail"], (mot, r.text)
        ok("cinq refus : version, lots vide, matière inconnue, job évadé, "
           "version absente — même porte que les cinq écritures voisines")
```

- [ ] **Step 2 : lancer, voir rouge, puis écrire les deux routes**

Dans `routes.py`, après `etabli_couper` (fin du bloc des écritures) :

```python
@router.get("/etabli/masques")
async def etabli_masques(job: str, version: int = 1):
    """Les masques de cavités et d'arêtes d'une version, en couleurs de
    sommet. LECTURE : aucun fichier n'est écrit, aucune version créée."""
    from app.services import mesh_paint as MP
    data = await asyncio.to_thread(_etabli_glb, job, version)
    try:
        glb = await asyncio.to_thread(MP.masques_glb, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(content=glb, media_type="model/gltf-binary",
                    headers={"Content-Disposition":
                             f'inline; filename="{Path(str(job)).name}'
                             f'.masques.glb"'})


@router.post("/etabli/habiller")
async def etabli_habiller(body: dict):
    """Pose une matière du Forge sur des parties d'un maillage.

    SEPTIÈME ÉCRITURE, MÊME PORTE : `_etabli_glb_cible` juge `job` et
    `version`, `mesh_edit.ecrire_version` dépose la nouvelle version avec sa
    fiche. Aucune raison d'ouvrir une porte de plus pour la même opération —
    écrire un GLB dans le dossier d'un job."""
    from app.services import material_store as MS
    from app.services import mesh_paint as MP
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "habillage")
    lots_in = body.get("lots")
    if not isinstance(lots_in, list) or not lots_in:
        raise HTTPException(400, "habillage : `lots` — au moins un "
                                 "{cible, index, mid} est attendu")
    if len(lots_in) > 64:
        raise HTTPException(400, "habillage : 64 parties au maximum")
    res = MS.clean_res(body.get("res"), 1024)
    lots, vus = [], {}
    for lot in lots_in:
        if not isinstance(lot, dict):
            raise HTTPException(400, "habillage : chaque lot est un objet "
                                     "{cible, index, mid}")
        mid = lot.get("mid")
        if mid not in vus:
            mat = MS.read_material(mid) if MS.is_valid_mid(mid) else None
            if mat is None:
                raise HTTPException(404, f"habillage : matière « {mid} » "
                                         "introuvable")
            maps = MS.bake_levels(
                MS.resize_maps(MS.load_maps(mid), res), mat["props"])
            if not maps:
                raise HTTPException(409, f"habillage : la matière « {mid} » "
                                         "n'a aucune map sur disque")
            vus[mid] = (mat, {k: MS.png_bytes(v, k, 8)
                              for k, v in maps.items() if k in MS.GLB_SLOTS})
        mat, payload = vus[mid]
        lots.append({"cible": lot.get("cible"), "index": lot.get("index"),
                     "mid": mid, "nom": mat["name"], "maps": payload})
    try:
        sortie = await asyncio.to_thread(MP.habiller, data, lots)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "habiller",
                          {"depuis": depuis, "res": res,
                           "lots": [{k: l[k] for k in ("cible", "index", "mid")}
                                    for l in lots]})
```

- [ ] **Step 3 : le panneau Parties de l'Établi**

Dans `frontend/etabli/etabli.js`, `rendreParties` (ligne 2067), ajouter sous
la liste des rangées, dans `.parties-actions` (ligne 2172) :

```js
      <select id="matiereSel" title="Matière à poser sur les pièces cochées">
        <option value="">— matière —</option></select>
      <button id="btnHabiller" disabled>Habiller</button>
      <button id="btnMasques" title="Voir les cavités et les arêtes
        calculées depuis la géométrie">Masques</button>
```

et, dans la fonction qui branche ces boutons :

```js
  /* La liste des matières vient du Material Forge, jamais d'une copie : une
     matière effacée là-bas doit disparaître ici au prochain rendu. */
  fetch("/api/materials").then((r) => r.json()).then((d) => {
    $("#matiereSel").innerHTML = '<option value="">— matière —</option>'
      + (d.materials || []).map((m) =>
        `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join("");
  }).catch(() => {});

  $("#matiereSel").addEventListener("change", () => {
    $("#btnHabiller").disabled = !$("#matiereSel").value || !SEL.retenus.size;
  });

  $("#btnHabiller").addEventListener("click", async () => {
    /* Le panneau Parties N'ÉCRIT RIEN : c'est la règle de tête de ce fichier
       et elle tient. Ce bouton n'est pas une exception — il appelle une
       ROUTE, qui écrit une version par mesh_edit, et la page recharge ce que
       le serveur a écrit. Aucun GLB n'est fabriqué ici. */
    const mid = $("#matiereSel").value;
    const lots = [...document.querySelectorAll(".partie input:checked")]
      .filter((i) => i.dataset.index !== undefined)
      .map((i) => ({ cible: SEL.granularite === "materiau" ? "materiau"
                            : SEL.granularite === "maillage" ? "maillage"
                            : "noeud",
                     index: Number(i.dataset.index), mid }));
    if (!lots.length) { direRefus("aucune pièce retenue porte un index "
      + "utilisable — un matériau n'a pas d'index de nœud."); return; }
    await ecrireVersion("/api/etabli/habiller", { lots });
  });

  $("#btnMasques").addEventListener("click", () => {
    chargerApercu(`/api/etabli/masques?job=${encodeURIComponent(S.job)}`
                  + `&version=${S.version}`);
  });
```

> `ecrireVersion(chemin, corps)` et `chargerApercu(url)` sont les helpers déjà
> utilisés par les cinq écritures et par le chargement de version : les relire
> dans `etabli.js` avant d'écrire, et les appeler tels quels. Si leurs noms
> diffèrent dans le fichier, prendre ceux qui existent — ne pas en créer de
> nouveaux.

- [ ] **Step 4 : lancer, vérifier à l'écran, commit**

```
python tests/test_etabli_habiller.py
python tests/test_mesh_paint.py
```

À l'écran : cocher deux pièces dans Parties, choisir une matière, « Habiller »
→ une version `v2` apparaît dans la chronologie et le viewport la montre
habillée ; « Masques » colore le modèle en rouge dans les creux et en vert sur
les arêtes.

```bash
git add backend/app/api/routes.py frontend/etabli/etabli.js backend/tests/test_etabli_habiller.py
git commit -m 'matieres D2 : une matiere par partie, ecrite par la seule plume

Septieme ecriture de l Etabli, MEME PORTE : _etabli_glb_cible juge job et
version, mesh_edit.ecrire_version depose la version avec sa fiche. Aucune
raison d ouvrir une porte de plus pour la meme operation.

Le panneau Parties n ecrit toujours RIEN — c est la regle de tete de
etabli.js. Le bouton Habiller appelle une ROUTE ; aucun GLB n est fabrique
dans le navigateur, et la page recharge ce que le serveur a ecrit.

Le banc verifie que les masques ne touchent AUCUN fichier du job (liste du
dossier avant et apres), que la version 1 reste intacte a l octet apres
l habillage, et que la fiche nomme l operation et la matiere. Cinq refus au
meme vocabulaire que les cinq ecritures voisines.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 16 : D3 — les finitions nommées, prévisualisées avant d'être posées

**Files:**
- Modify: `backend/app/services/material_store.py:221-252` (`PRESETS` : trois de plus, et une famille)
- Modify: `backend/app/api/routes.py:7635-7695` (`preview.glb?finish=`), `:7215-7221` (`/materials/presets`)
- Modify: `backend/app/services/cards/forge3d_scene.py:1099` (`_SURFACE_RECIPES`, `SURFACE_KINDS`), `backend/app/services/cards/forge3d.py:276` (`MATERIAL_FINISHES`), `:519-528` (`/info`)
- Modify: `frontend/materialforge/materialforge.js:2586-2631` (`applyPreset` : aperçu avant application)
- Test: `backend/tests/test_material_finitions.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_material_finitions.py` avec l'en-tête habituel, puis :

```python
        # ══ 1 · quatre finitions de plus, nommées ═══════════════════════════
        d = (await c.get("/api/materials/presets")).json()
        ids = [p["id"] for p in d["presets"]]
        for neuf in ("laque", "cuir", "emissif_anime", "metal_brosse_aniso"):
            assert neuf in ids, ids
        for p in d["presets"]:
            assert p["label"] and isinstance(p["props"], dict), p
            assert p.get("famille") in ("metal", "surface", "verre",
                                        "lumiere", "organique"), p
        ok(f"{len(ids)} préréglages, quatre de plus, chacun rangé dans une "
           f"famille")

        # ══ 2 · l'aperçu APPLIQUE la finition sans toucher la matière ═══════
        m = _fabriquer_matiere()
        avant = MS.read_material(m["id"])["props"]["roughness"]
        r = await c.get(f"/api/materials/{m['id']}/preview.glb?finish=laque")
        assert r.status_code == 200 and r.content[:4] == b"glTF", r.status_code
        doc, _ = mesh_edit.lire_glb(r.content)
        pbr = doc["materials"][0]["pbrMetallicRoughness"]
        # les niveaux restent CUITS : les facteurs valent 1.0, c'est la carte
        # qui porte la finition
        assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0
        assert MS.read_material(m["id"])["props"]["roughness"] == avant, \
            "l'aperçu a écrit dans la matière"
        ok("preview.glb?finish=laque : la finition est appliquée à l'aperçu, "
           "la matière n'a pas bougé d'un iota")

        # ══ 3 · deux finitions différentes donnent deux GLB différents ══════
        a = (await c.get(f"/api/materials/{m['id']}/preview.glb?finish=laque")).content
        b = (await c.get(f"/api/materials/{m['id']}/preview.glb?finish=cuir")).content
        assert a != b, "le cache sert le même GLB pour deux finitions"
        c0 = (await c.get(f"/api/materials/{m['id']}/preview.glb")).content
        assert a != c0 and b != c0
        ok("la finition entre dans l'empreinte du cache : trois GLB "
           "différents pour trois finitions")

        # ══ 4 · une finition inconnue se refuse ═════════════════════════════
        r = await c.get(f"/api/materials/{m['id']}/preview.glb?finish=chose")
        assert r.status_code == 400 and "chose" in r.json()["detail"]
        ok("finition inconnue : 400 nommé")

        # ══ 5 · le Forge 3D des cartes connaît les mêmes noms ═══════════════
        from app.services.cards import forge3d
        from app.services.cards import forge3d_scene as FS
        assert set(FS.SURFACE_KINDS) <= set(forge3d.MATERIAL_FINISHES)
        assert "aucune" in forge3d.MATERIAL_FINISHES
        assert len(set(forge3d.MATERIAL_FINISHES)) == \
            len(forge3d.MATERIAL_FINISHES), "doublon dans le vocabulaire"
        g = forge3d.clean_graph({"nodes": [{"id": "m", "kind": "material",
                                            "finish": "laque"}], "edges": []})
        assert g["nodes"][0]["finish"] == "laque", g
        ok("le vocabulaire des finitions est UN : le nœud material du Forge "
           "3D accepte les mêmes noms, sans doublon")
```

- [ ] **Step 2 : les quatre finitions**

Dans `material_store.py`, `PRESETS` (ligne 221) : ajouter une clé `famille` à
chacun des neuf existants (`brushed_metal` → `metal`, `polished_gold` →
`metal`, `plastic` → `surface`, `varnished_wood` → `surface`, `glass` →
`verre`, `fabric` → `organique`, `stone` → `surface`, `emissive_panel` →
`lumiere`, `rubber` → `surface`) et ajouter les quatre :

```python
    # ── les quatre finitions de R10c D3 ────────────────────────────────────
    # Elles ne sont PAS des matières : ce sont des habits qu'on essaie sur une
    # matière existante, et l'aperçu les montre AVANT qu'elles soient posées.
    {"id": "metal_brosse_aniso", "label": "Métal brossé (fin)",
     "famille": "metal",
     "props": {"color": "#c2c7cf", "metallic": 1.0, "roughness": 0.28,
               "clearcoat": 0.05, "normal_scale": 1.6, "tiling": 1.0}},
    {"id": "laque", "label": "Laque", "famille": "surface",
     "props": {"metallic": 0.0, "roughness": 0.08, "clearcoat": 1.0,
               "clearcoat_roughness": 0.03, "normal_scale": 0.5}},
    {"id": "cuir", "label": "Cuir", "famille": "organique",
     "props": {"metallic": 0.0, "roughness": 0.62, "sheen": 0.25,
               "sheen_color": "#d8c9b4", "normal_scale": 1.5,
               "clearcoat": 0.08}},
    # L'ANIMATION VIT DANS L'APERÇU, PAS DANS LE FICHIER, et il faut le dire :
    # glTF cœur n'anime aucune propriété de matériau (les animations y portent
    # sur les nœuds et les poids de morph). Le GLB exporté porte donc un
    # émissif FIXE à cette intensité ; c'est l'écran qui pulse.
    {"id": "emissif_anime", "label": "Émissif animé", "famille": "lumiere",
     "props": {"emissive": "#ff8a1f", "emissive_strength": 3.0,
               "roughness": 0.4, "metallic": 0.0},
     "anime": {"propriete": "emissive_strength", "hz": 0.6,
               "amplitude": 0.45,
               "note": "L'animation est un effet d'aperçu : glTF cœur n'anime "
                       "pas les propriétés de matériau, et le GLB exporté "
                       "porte l'émissif fixe."}},
```

Dans `routes.py`, `material_preview_glb` : ajouter `finish: str = ""` à la
signature et, après la lecture de `mat` :

```python
    # UNE FINITION EST UN HABIT, PAS UNE ÉCRITURE. Elle est fusionnée sur les
    # props le temps de construire CE GLB, et la matière sur disque n'en sait
    # rien — c'est ce qui permet d'essayer avant de poser.
    fin = str(finish or "").strip().lower()
    if fin:
        preset = next((p for p in MS.PRESETS if p["id"] == fin), None)
        if preset is None:
            raise HTTPException(400, f"finition « {fin} » inconnue — connues : "
                                     f"{', '.join(p['id'] for p in MS.PRESETS)}")
        mat = dict(mat)
        mat["props"] = MS.merge_props(mat["props"], preset["props"])
```

et ajouter `-F{fin}` à la chaîne empreinte du cache (même ligne que `-M{modele}`).

Dans `forge3d_scene.py`, après `GLASS_KINDS` (ligne 1099) :

```python
# ── LES FINITIONS DE SURFACE (R10c D3) ──────────────────────────────────────
# Troisième famille, à côté des feuilles estampées (`_HOLO_RECIPES`) et des
# verres (`_GLASS_RECIPES`). Celles-ci ne cuisent AUCUNE texture : ce sont des
# propriétés de matériau, donc elles ne coûtent pas un octet de plus dans le
# GLB. C'est aussi pourquoi elles peuvent se prévisualiser en direct.
_SURFACE_RECIPES = {
    "metal_brosse_aniso": {"metallic": 1.0, "rough": 0.28, "coat": 0.05},
    "laque": {"metallic": 0.0, "rough": 0.08, "coat": 1.0, "coat_rough": 0.03},
    "cuir": {"metallic": 0.0, "rough": 0.62, "sheen": 0.25},
    "emissif_anime": {"metallic": 0.0, "rough": 0.40, "emissive": 3.0},
}
SURFACE_KINDS = tuple(_SURFACE_RECIPES)


def surface_finish(kind: str) -> dict:
    """La recette d'une finition de surface. `kind` hors `SURFACE_KINDS` lève
    une ValueError NOMMÉE — même contrat que `holo_finish` et `glass_finish`."""
    r = _SURFACE_RECIPES.get(str(kind))
    if r is None:
        raise ValueError(f"finition de surface « {kind} » inconnue "
                         f"(connues : {', '.join(SURFACE_KINDS)})")
    return dict(r)
```

Dans `forge3d.py` ligne 276 :

```python
MATERIAL_FINISHES = ("aucune",) + HOLO_KINDS + GLASS_KINDS + SURFACE_KINDS
```

(et importer `SURFACE_KINDS`, `surface_finish` dans la ligne d'import de
`forge3d_scene`, ligne 41-42), puis dans `/info` (ligne 528) :

```python
                                "finishes_surface": list(SURFACE_KINDS),
```

- [ ] **Step 3 : l'aperçu dans l'écran**

Dans `materialforge.js`, `applyPreset` (ligne 2586) : sur `mouseenter` d'une
option, appeler `setViewportSrc` avec `&finish=<id>` ; sur `mouseleave` ou
changement, revenir au GLB sans finition ; ne POSER (PATCH) qu'au clic sur
« Appliquer ». Pour `emissif_anime`, faire pulser
`$("#mv").model.materials[0].emissiveFactor` à `preset.anime.hz`, avec la
garde `prefers-reduced-motion` du dépôt.

- [ ] **Step 4 : lancer, commit**

```
python tests/test_material_finitions.py
python tests/test_cards_forge3d.py
```

```bash
git add backend/app/services/material_store.py backend/app/services/cards/forge3d.py backend/app/services/cards/forge3d_scene.py backend/app/api/routes.py frontend/materialforge/materialforge.js backend/tests/test_material_finitions.py
git commit -m 'matieres D3 : quatre finitions nommees, essayees avant d etre posees

Une finition est un HABIT, pas une ecriture : elle est fusionnee sur les props
le temps de construire CE GLB, et la matiere sur disque n en sait rien. Le
banc le verifie — apres un apercu en laque, la rugosite de la matiere n a pas
bouge d un iota — et verifie aussi que la finition entre dans l empreinte du
cache, sans quoi deux finitions se partageraient un GLB.

L animation vit dans l APERCU, pas dans le fichier, et c est dit noir sur
blanc dans la recette : glTF coeur n anime aucune propriete de materiau (ses
animations portent sur les noeuds et les poids de morph). Le GLB exporte porte
l emissif fixe ; c est l ecran qui pulse, sous la garde prefers-reduced-motion.

Troisieme famille de finitions a cote des feuilles estampees et des verres,
MEME vocabulaire ferme : le noeud material du Forge 3D accepte les memes noms,
sans doublon, et /info les publie. Celles-ci ne cuisent aucune texture — ce
sont des proprietes de materiau, donc zero octet de plus dans le GLB, et c est
aussi pourquoi elles se previsualisent en direct.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 17 : D4 — la photo du téléphone entre par une porte, et le transport est nommé

**Files:**
- Modify: `backend/app/api/routes.py` (une route, après `material_prep_preview`)
- Modify: `frontend/materialforge/index.html:55-61` (la zone de dépôt accepte l'appareil photo)
- Test: `backend/tests/test_materials_prep_api.py` (nouvelle section)

**Ce que cette tâche livre, et ce qu'elle ne livre pas.** R10c D4 dit : « le
compagnon (R12) envoie une photo de surface au Material Forge, qui redresse,
délighte et dérive ». La moitié Material Forge est ici : **une porte d'entrée
unique** qui prend une photo brute, la range dans la Bibliothèque, la prépare
et en fait une matière, en une requête. L'autre moitié — l'appairage, le jeton
d'appareil, l'écoute sur le LAN — est **R12 P1**, elle n'est pas planifiée
dans ce document, et cette route ne l'anticipe pas : tant que le backend
écoute sur `127.0.0.1`, elle n'est atteignable que depuis le PC (et depuis la
page autonome, dont le champ de fichier accepte l'appareil photo sur un
mobile). Le jour où R12 P1 pose son jeton, cette route est déjà la bonne
cible, sans rien changer.

- [ ] **Step 1 : ajouter la section rouge**

Dans `backend/tests/test_materials_prep_api.py`, avant le `print` final :

```python
        # ══ 8 · une photo brute -> une matière, en une requête ═══════════════
        with open(settings.images_path / lib, "rb") as f:
            octets = f.read()
        r = await c.post(
            "/api/materials/from-photo",
            files={"file": ("photo.png", octets, "image/png")},
            data={"prep": json.dumps({"quad": QUAD, "delight": 1.0}),
                  "res": "512", "name": "Depuis le telephone"})
        assert r.status_code == 200, r.text
        m = r.json()["material"]
        assert m["name"] == "Depuis le telephone"
        assert m["source"]["kind"] == "library", m["source"]
        assert m["source"]["prep"]["quad"] == QUAD, m["source"]
        assert m["maps"] == list(MS.MAP_KINDS), m["maps"]
        assert (settings.images_path / m["source"]["filename"]).is_file(), \
            "la photo n'a pas été rangée dans la Bibliothèque"
        ok(f"POST /materials/from-photo : {m['id']} en une requête, photo "
           f"rangée dans la Bibliothèque, préparation gardée")

        r = await c.post("/api/materials/from-photo",
                         files={"file": ("t.txt", b"pas une image", "text/plain")},
                         data={"res": "512"})
        assert r.status_code == 400 and "image" in r.json()["detail"].lower()
        ok("fichier qui n'est pas une image : 400 parlant")
```

- [ ] **Step 2 : la route**

```python
@router.post("/materials/from-photo")
async def material_from_photo(file: UploadFile = File(...), prep: str = Form(""),
                              res: int = Form(2048), name: str = Form("")):
    """Une photo brute -> une matière, en UNE requête.

    LA PORTE D'ENTRÉE DE R10c D4. Elle range d'abord la photo dans la
    Bibliothèque — l'aval du produit (lignée, provenance, « Rouvrir dans »)
    lit la Bibliothèque, et une photo qui resterait à part serait un cas
    particulier à porter partout —, puis passe exactement par le job de
    génération existant. Aucun second chemin de dérivation.

    LE TRANSPORT N'EST PAS ICI. L'appairage, le jeton d'appareil et l'écoute
    LAN sont R12 P1 : tant que le backend écoute sur 127.0.0.1, cette route
    n'est atteignable que depuis le PC (ou depuis /materialforge/ ouvert sur
    la machine). Elle est déjà la bonne cible pour le jour où R12 P1 arrive,
    et n'anticipe rien d'autre."""
    import io
    from app.services import material_store as MS
    data = await file.read()
    try:
        img = PILImage.open(io.BytesIO(data))
        img.load()
    except Exception as e:
        raise HTTPException(400, f"Ce fichier n'est pas une image lisible : {e}")
    nom = Path(file.filename or "photo.png").name
    cible = settings.images_path / f"photo_{uuid4().hex[:8]}{Path(nom).suffix or '.png'}"
    await asyncio.to_thread(cible.write_bytes, data)
    await LI.noter([cible.name], "matieres")
    try:
        bloc = json.loads(prep) if prep else {}
    except ValueError:
        bloc = {}
    corps = {"filename": cible.name, "res": res, "seamless": True,
             "name": name or Path(nom).stem, "prep": bloc}
    tasks = BackgroundTasks()
    reponse = await generate_material(corps, tasks)
    await tasks()
    st = _MAT_JOBS.get(reponse["job_id"]) or {}
    for _ in range(1200):
        if st.get("status") in ("done", "failed"):
            break
        await asyncio.sleep(0.05)
        st = _MAT_JOBS.get(reponse["job_id"]) or {}
    if st.get("status") != "done":
        raise HTTPException(500, st.get("error") or "préparation impossible")
    return {"material": st["material"]}
```

> `generate_material` prend `(body, background_tasks)` : l'appeler avec un
> `BackgroundTasks()` local et l'exécuter soi-même est ce qui rend cette route
> SYNCHRONE — un téléphone qui poste une photo veut une réponse, pas un
> identifiant de job à sonder sur un réseau qui coupe. Le job reste le même,
> et la file du PC le voit comme les autres.

- [ ] **Step 3 : la zone de dépôt accepte l'appareil photo**

Dans `index.html` ligne 61, remplacer :

```html
        <input type="file" id="fileInput" accept="image/*" class="hidden">
```

par :

```html
        <!-- `capture="environment"` : sur un mobile, le champ ouvre l'appareil
             photo arrière au lieu du sélecteur de fichiers. Ignoré sur
             desktop, donc aucun coût pour le poste principal. -->
        <input type="file" id="fileInput" accept="image/*"
               capture="environment" class="hidden">
```

- [ ] **Step 4 : lancer, commit**

```
python tests/test_materials_prep_api.py
```

```bash
git add backend/app/api/routes.py frontend/materialforge/index.html backend/tests/test_materials_prep_api.py
git commit -m 'matieres D4 : une photo brute devient une matiere en une requete

La porte d entree du bac D4. Elle range d abord la photo dans la Bibliotheque
— l aval du produit lit la Bibliotheque, et une photo qui resterait a part
serait un cas particulier a porter partout — puis passe par le job de
generation EXISTANT : aucun second chemin de derivation.

Synchrone, et c est le point : un telephone qui poste une photo veut une
reponse, pas un identifiant de job a sonder sur un reseau qui coupe. Le job
reste le meme et la file du PC le voit comme les autres.

LE TRANSPORT N EST PAS ICI, et ce commit ne le pretend pas. L appairage, le
jeton d appareil et l ecoute LAN sont R12 P1 : tant que le backend ecoute sur
127.0.0.1, cette route n est atteignable que depuis le PC. Elle est deja la
bonne cible pour le jour ou R12 P1 arrive, et n anticipe rien d autre.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

- **E1 — Taille physique propagée aux moteurs.** Écarté par la réponse 7 de
  R10c : la taille physique ne sert **qu'à l'impression**. T9 livre donc
  `height_mm` (l'amplitude du relief) et **rien d'autre** ; le `scale`
  (« 1.5x1.5 ») et les `dimensions` (`[3000, 3000]`) que Poly Haven publie
  sont **relevés dans le catalogue et jamais interprétés** — Unity, Unreal,
  Godot et Blender ne s'accordent ni sur l'unité de leur `tiling`, ni sur ce
  qu'un déplacement de 1,0 veut dire, et propager un mètre à travers quatre
  conventions produirait quatre matières fausses au lieu d'une matière
  neutre.

- **E2 — Appel de l'API Poly Haven depuis l'application.** Écarté, et **la
  raison a changé, ce qui doit être dit**. R10c écrivait « interdit en usage
  commercial sans licence (mesuré) ». **Relu le 03/09/2026, ce n'est plus
  vrai** : l'annonce du 18 juillet 2026 (`polyhaven.com/our-api`), le
  `ToS.md` et le README de `github.com/Poly-Haven/Public-API` ouvrent l'API à
  tout usage, commercial compris, à la seule condition d'un `User-Agent` ou
  `Referer` propre au logiciel et d'un crédit visible pour l'usage **en
  direct**. L'écart reste néanmoins, pour deux raisons qui ne dépendent pas
  de la licence : (1) un studio **local** dont l'écran de matières exige le
  réseau trahit sa promesse, et une API tierce qui bouge casserait l'écran
  d'un utilisateur qui n'a rien demandé ; (2) l'usage en direct impose un
  crédit « Powered by Poly Haven » **dans l'interface**, que le téléchargement
  au build évite entièrement puisque les assets sont CC0. Le catalogue reste
  donc figé au build (T10) — et l'interdiction citée par R10c est corrigée
  ici, à sa date.

---
## Campagne de mutations

### Task 18 : la campagne de mutations

**Files:**
- Create: `backend/tests/mutations_matieres.py`

Patron : `backend/tests/mutations_plaque_slicer.py` (77 + 45 mutations, campagne
du 01–02/09). **Une adaptation s'impose et il faut la dire** : la campagne de
la plaque lance `pytest <banc> -k <nom>` et lit les lignes `FAILED …::nom`.
Les bancs de CE plan sont des **scripts autonomes à assertions groupées** —
ils n'ont pas de fonctions `test_*`, `pytest` n'y collecte rien, et `-k` n'a
aucun sens. La campagne lit donc **les lignes `✓` réellement imprimées** : un
premier passage sans mutation établit la référence par banc, puis chaque
mutation doit faire **disparaître** les marqueurs qu'elle nomme. Une mutation
« VERTE » reste ce qu'elle a toujours été : une assertion qui manque.

- [ ] **Step 1 : écrire la campagne**

Créer `backend/tests/mutations_matieres.py` :

```python
# -*- coding: utf-8 -*-
"""Campagne de mutations des Matières : casser → rouge → remettre.

PAS UN TEST : `run-tests.ps1` ne liste que `test_*.py`, et ce fichier ne
commence pas par `test_`. Il se lance À LA MAIN, depuis `backend/` :

    python tests/mutations_matieres.py            # toutes
    python tests/mutations_matieres.py 3 17       # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près
(assertion) : il ne se lance donc pas pendant qu'un autre banc lit ces
fichiers.

CE QUI CHANGE PAR RAPPORT À `mutations_plaque_slicer.py`. Cette campagne-là
lance `pytest <banc> -k <nom>` et lit les lignes `FAILED …::nom`. Les bancs de
ce plan sont des SCRIPTS AUTONOMES à assertions groupées : aucune fonction
`test_*`, rien à collecter, `-k` sans objet. On lit donc les lignes `✓` que
chaque banc IMPRIME. Un premier passage sans mutation établit la référence
par banc ; ensuite, une mutation doit faire DISPARAÎTRE les marqueurs qu'elle
nomme. Trois verdicts :

    ROUGE            les marqueurs attendus ont disparu — la mutation est vue
    VERTE            le banc reste entièrement vert — UNE ASSERTION MANQUE
    ROUGE(autres)    d'autres marqueurs sont tombés, pas ceux attendus —
                     l'assertion existe mais ne vise pas ce qu'on croyait
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BACKEND = R / "backend"

PREP = "tests/test_photo_prep.py"
API_PREP = "tests/test_materials_prep_api.py"
NAMING = "tests/test_material_naming_archive.py"
HDR = "tests/test_hdr_reader.py"
PAT = "tests/test_pattern_service.py"
PAINT = "tests/test_mesh_paint.py"
HAUT = "tests/test_material_height_mm.py"
FIN = "tests/test_material_finitions.py"

# (fichier, ancien, nouveau, banc, [fragments de marqueurs ✓ attendus perdus])
M = [
    # ── photo_prep : le delighting ─────────────────────────────────────────
    ("backend/app/services/photo_prep.py",
     "    return PBR.cyclic(lum, ImageFilter.GaussianBlur(r), r * 3.0 + 1.0)",
     "    return lum.filter(ImageFilter.GaussianBlur(r))",
     PREP, ["bord cyclique"]),
    ("backend/app/services/photo_prep.py",
     "    ecart = lg.point([clamp8(128.0 - k * (v - pivot)) for v in range(256)])",
     "    ecart = lg.point([clamp8(128.0 + k * (v - pivot)) for v in range(256)])",
     PREP, ["écart-type basse fréquence"]),
    ("backend/app/services/photo_prep.py",
     "    pivot = sum(i * c for i, c in enumerate(h)) / n\n",
     "    pivot = 128.0\n",
     PREP, ["écart-type basse fréquence"]),
    ("backend/app/services/photo_prep.py",
     "    if k <= 0.0:\n        return rgb",
     "    if k < 0.0:\n        return rgb",
     PREP, ["delight ne lève jamais"]),
    ("backend/app/services/photo_prep.py",
     "        lignes.append([X, Y, 1.0, 0.0, 0.0, 0.0, -X * x, -Y * x])",
     "        lignes.append([Y, X, 1.0, 0.0, 0.0, 0.0, -X * x, -Y * x])",
     PREP, ["perspective_coeffs"]),
    ("backend/app/services/photo_prep.py",
     "    pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))",
     "    pts.sort(key=lambda p: p[0])",
     PREP, ["order_quad"]),
    ("backend/app/services/photo_prep.py",
     "    debut = min(range(4), key=lambda i: (pts[i][0] - cx) + (pts[i][1] - cy))",
     "    debut = 0",
     PREP, ["order_quad"]),
    ("backend/app/services/photo_prep.py",
     "        if abs(m[piv][col]) < _EPS:",
     "        if False:",
     PREP, ["refus nommés"]),
    ("backend/app/services/photo_prep.py",
     "    if _aire(pts) < 0.05 * max(1.0, largeur * hauteur):",
     "    if _aire(pts) < -1.0:",
     PREP, ["refus nommés"]),
    ("backend/app/services/photo_prep.py",
     "            if math.dist(pts[i], pts[j]) < 1.0:",
     "            if math.dist(pts[i], pts[j]) < 0.0:",
     PREP, ["refus nommés"]),

    # ── le câblage : l'ordre des gestes ────────────────────────────────────
    ("backend/app/api/routes.py",
     "    if p and p.get(\"quad\"):\n        rgb = PP.straighten(rgb, p[\"quad\"], res)\n    fait = dict(p or {})\n    if p and p.get(\"delight\"):",
     "    fait = dict(p or {})\n    if p and p.get(\"delight\"):",
     API_PREP, ["job : source.prep gardé", "archive"]),
    ("backend/app/api/routes.py",
     "        fait[\"lowfreq_sd_after\"] = PP.lowfreq_sd(rgb, rayon)",
     "        fait[\"lowfreq_sd_after\"] = fait[\"lowfreq_sd_before\"]",
     API_PREP, ["aperçu"]),
    ("backend/app/services/material_store.py",
     "    d = _coerce_float(raw.get(\"delight\"), 0.0, 0.0, 1.0)\n    if d > 0.0:",
     "    d = _coerce_float(raw.get(\"delight\"), 0.0, 0.0, 1.0)\n    if d >= 0.0:",
     API_PREP, ["sans prep"]),

    # ── conventions d'export ───────────────────────────────────────────────
    ("backend/app/services/material_store.py",
     "                \"normal\": \"{n}_normal_gl.png\",",
     "                \"normal\": \"{n}_normal.png\",",
     NAMING, ["archive « blender »"]),
    ("backend/app/services/material_store.py",
     "    \"blender\": (\"basecolor\", \"normal\", \"roughness\", \"metallic\", \"ao\",\n                \"height\", \"emissive\"),",
     "    \"blender\": (\"basecolor\", \"normal\", \"roughness\", \"metallic\", \"ao\",\n                \"height\", \"emissive\", \"orm\"),",
     NAMING, ["archive « blender »", "bordereau Blender"]),
    ("backend/app/services/material_store.py",
     "    detail = Image.new(\"L\", size, 0)          # aucune carte de détail livrée",
     "    detail = Image.new(\"L\", size, 255)",
     NAMING, ["archive « unity_urp »", "archive « unity_hdrp »"]),
    ("backend/app/services/material_store.py",
     "    smooth = ImageChops.invert(rough)         # smoothness = 1 − rugosité",
     "    smooth = rough",
     NAMING, ["archive « unity_urp »", "archive « unity_hdrp »"]),

    # ── hdr_reader ─────────────────────────────────────────────────────────
    ("backend/app/services/hdr_reader.py",
     "            and (data[i + 2] << 8 | data[i + 3]) == w):",
     "            and (data[i + 2] << 8 | data[i + 3]) != w):",
     HDR, ["scanline plate et RLE"]),
    ("backend/app/services/hdr_reader.py",
     "            if n > 128:\n                n -= 128",
     "            if n > 128:\n                n -= 127",
     HDR, ["scanline plate et RLE"]),
    ("backend/app/services/hdr_reader.py",
     "        if acc >= n * 0.5:",
     "        if acc >= n * 0.995:",
     HDR, ["équirect LDR"]),
    ("backend/app/services/hdr_reader.py",
     "    if data[i] == 255 and data[i + 1] == 255 and data[i + 2] == 255:",
     "    if False:",
     HDR, ["refus nommés"]),
    ("backend/app/services/hdr_reader.py",
     "    if w * h > HDR_MAX_PIXELS:",
     "    if False:",
     HDR, ["refus nommés"]),

    # ── pattern_service ────────────────────────────────────────────────────
    ("backend/app/services/pattern_service.py",
     "    grand = PBR.wrap(_lattice(n, graine), _BORD).resize(",
     "    grand = PBR.wrap(_lattice(n, graine), 0).resize(",
     PAT, ["raccord"]),
    ("backend/app/services/pattern_service.py",
     "    while int(cote) % c:\n        c //= 2",
     "    pass",
     PAT, ["cells()"]),
    ("backend/app/services/pattern_service.py",
     "        part = oc.point([PBR.clamp8(v * w / somme) for v in range(256)])",
     "        part = oc.point([PBR.clamp8(v * w) for v in range(256)])",
     PAT, ["cinq octaves"]),
    ("backend/app/services/pattern_service.py",
     "    k = max(0.05, min(1.0, p[\"force\"]))",
     "    k = 0.0",
     PAT, ["dix générateurs"]),

    # ── mesh_paint ─────────────────────────────────────────────────────────
    ("backend/app/services/mesh_paint.py",
     "        k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))",
     "        k = (p[0], p[1], p[2], len(rep))",
     PAINT, ["cube : arête", "tore"]),
    ("backend/app/services/mesh_paint.py",
     "            if v > 0:\n                cav[i] += poids * v\n            else:\n                are[i] -= poids * v",
     "            if v > 0:\n                are[i] += poids * v\n            else:\n                cav[i] -= poids * v",
     PAINT, ["cube : arête"]),
    ("backend/app/services/mesh_paint.py",
     "            if \"TEXCOORD_0\" not in (prim.get(\"attributes\") or {}):",
     "            if False:",
     PAINT, ["refus nommés"]),
    ("backend/app/services/mesh_paint.py",
     "    doc[\"buffers\"] = [{\"byteLength\": len(octets)}]\n    return mesh_edit.ecrire_glb(doc, octets)\n\n\n# ── masques",
     "    return mesh_edit.ecrire_glb(doc, octets)\n\n\n# ── masques",
     PAINT, ["les quatre textures"]),
    ("backend/app/services/mesh_paint.py",
     "    pbr = {\"baseColorFactor\": [1.0, 1.0, 1.0, 1.0],\n           \"metallicFactor\": 1.0, \"roughnessFactor\": 1.0}",
     "    pbr = {\"baseColorFactor\": [1.0, 1.0, 1.0, 1.0],\n           \"metallicFactor\": 0.5, \"roughnessFactor\": 1.0}",
     PAINT, ["les quatre textures"]),
    ("backend/app/services/mesh_paint.py",
     "        i = _texture(doc, tampon, payload[\"orm\"])\n        pbr[\"metallicRoughnessTexture\"] = {\"index\": i}\n        mat[\"occlusionTexture\"] = {\"index\": i}",
     "        pbr[\"metallicRoughnessTexture\"] = {\n            \"index\": _texture(doc, tampon, payload[\"orm\"])}\n        mat[\"occlusionTexture\"] = {\n            \"index\": _texture(doc, tampon, payload[\"orm\"])}",
     PAINT, ["les quatre textures"]),

    # ── hauteur physique ───────────────────────────────────────────────────
    ("backend/app/services/material_store.py",
     "        \"height_mm\": _coerce_float(raw.get(\"height_mm\"), 0.0, 0.0, 20.0),",
     "        \"height_mm\": _coerce_float(raw.get(\"height_mm\"), 0.0, 0.0, 200.0),",
     HAUT, ["height_mm"]),
    ("backend/app/services/cards/forge3d.py",
     "                if float(mat_r.get(\"height_mm\") or 0.0) > 0.0:\n                    voulu, source = float(mat_r[\"height_mm\"]), \"matiere\"",
     "                if False:\n                    voulu, source = float(mat_r[\"height_mm\"]), \"matiere\"",
     HAUT, ["relief", "maillage de relief"]),
    ("backend/app/services/cards/forge3d.py",
     "            if n.get(\"depth_mm\") is not None:\n                voulu, source = n.get(\"depth_mm\"), \"graphe\"",
     "            if False:\n                voulu, source = n.get(\"depth_mm\"), \"graphe\"",
     HAUT, ["relief"]),

    # ── finitions ──────────────────────────────────────────────────────────
    ("backend/app/api/routes.py",
     "        mat = dict(mat)\n        mat[\"props\"] = MS.merge_props(mat[\"props\"], preset[\"props\"])",
     "        mat[\"props\"] = MS.merge_props(mat[\"props\"], preset[\"props\"])\n        MS.write_material(mat)",
     FIN, ["la matière n'a pas bougé"]),
]


def _marqueurs(sortie: str) -> set:
    return {m.strip() for m in re.findall(r"✓ (.+)", sortie)}


def _lancer(banc: str):
    r = subprocess.run([PY, banc], capture_output=True, cwd=BACKEND,
                       timeout=1800)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode, txt, _marqueurs(txt)


_REF: dict = {}


def reference(banc: str) -> set:
    """Le jeu COMPLET de marqueurs d'un banc sain — calculé une fois.

    Si le banc n'est pas vert AVANT toute mutation, on s'arrête net : mesurer
    des mutations contre une base rouge ne dit rien."""
    if banc not in _REF:
        code, txt, marks = _lancer(banc)
        if code != 0 or not marks:
            print(txt[-2000:], file=sys.stderr)
            raise SystemExit(f"[base] {banc} n'est pas vert AVANT mutation "
                             f"(code {code}, {len(marks)} marqueurs) — "
                             "rien à mesurer.")
        _REF[banc] = marks
        print(f"[base] {banc}: {len(marks)} marqueurs")
    return _REF[banc]


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, vieux, neuf, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        ref = reference(banc)
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF et
        # l'on réécrit avec la fin de ligne du fichier ; la remise se fait à
        # l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(vieux) == 1, (i, rel, txt.count(vieux), vieux[:70])
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace(vieux, neuf).replace("\n", eol)
                      .encode("utf-8"))
        try:
            code, sortie, vus = _lancer(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        perdus = ref - vus
        touches = [a for a in attendus
                   if any(a.lower() in m.lower() for m in perdus)]
        if code == 0 and not perdus:
            verdict = "VERTE"
        elif len(touches) == len(attendus):
            verdict = "ROUGE"
        elif perdus:
            verdict = "ROUGE(autres)"
        else:
            verdict = "ERREUR(banc)"
            print(sortie[-1200:], file=sys.stderr)
        bilan.append((i, rel, verdict, sorted(perdus)[:4]))
        print(f"[{i:2d}] {verdict:14s} {pathlib.Path(rel).name:22s} "
              f"{vieux.strip()[:44]!r} -> perdus {sorted(perdus)[:2]}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    verts = [b for b in bilan if b[2] == "VERTE"]
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))
    print(f"\n{len(bilan)} mutations — {len(bilan) - len(verts)} rouges, "
          f"{len(verts)} VERTES (chacune est une assertion qui manque)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne entière**

```
python tests/mutations_matieres.py
```

Attendu : `36 mutations — 36 rouges, 0 VERTES`. **Chaque VERTE est un rapport
à faire** : c'est une assertion qui manque, pas une mutation à retirer. La
corriger consiste à ajouter l'assertion dans le banc concerné, relancer, et
seulement alors passer à la suite.

- [ ] **Step 3 : commit**

```bash
git add backend/tests/mutations_matieres.py
git commit -m 'matieres : campagne de mutations, 36 fois casse puis remis

Adaptation nommee du patron de la plaque slicer : cette campagne-la lance
pytest -k et lit les lignes FAILED. Les bancs de ce plan sont des SCRIPTS
autonomes a assertions groupees — aucune fonction test_, rien a collecter,
-k sans objet. On lit donc les lignes coche que chaque banc IMPRIME : un
premier passage sans mutation etablit la reference, puis chaque mutation doit
faire DISPARAITRE les marqueurs qu elle nomme.

Trois verdicts, et le troisieme compte autant que les autres : ROUGE (la
mutation est vue), VERTE (le banc reste vert — UNE ASSERTION MANQUE), et
ROUGE(autres) (d autres marqueurs sont tombes, pas ceux attendus : l assertion
existe mais ne vise pas ce qu on croyait).

La campagne refuse de mesurer contre une base rouge, remet chaque fichier a
l octet pres et le verifie par sha256.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Ce qui reste ouvert, dit ici plutôt que découvert plus tard

- **Le banc de T5 lit six conventions ; il n'ouvre pas Blender.** Que le
  fichier s'appelle `_normal_gl.png` et que la note dise « Non-Color » ne
  prouve pas qu'un humain branche correctement le graphe. La seule vérification
  possible ici est la relecture de la documentation (Step 1) et l'archive
  mesurée ; l'essai réel dans Blender est une vérification MANUELLE, à faire
  une fois, et son résultat vaut plus que ce plan.
- **Le décodeur `.hdr` est prouvé contre des fichiers que le banc écrit
  lui-même.** C'est ce qui le rend indépendant du module, et c'est aussi sa
  limite : un `.hdr` réel produit par un outil exotique (en-tête inhabituel,
  commentaires, `EXPOSURE` répété) peut refuser. Le premier import d'un
  fichier Poly Haven réel est donc une vérification manuelle du Step 9 de T7,
  pas une supposition.
- **Le budget des masques (T14) est mesuré sur la sphère de `gltf_builder`
  (~6 400 triangles) et RAPPORTÉ à 100 000.** Le rapport suppose une
  complexité linéaire ; elle l'est en théorie (soudure par table de hachage,
  adjacence par ensemble, trois lissages de 1-anneau) mais la mémoire ne l'est
  pas. Un modèle réel de 100 000 triangles doit être passé une fois à la main
  avant de promettre le chiffre à l'écran.
- **`emissif_anime` n'anime rien dans le fichier livré**, et c'est écrit dans
  la recette, dans le LISEZMOI et dans ce plan. Si l'animation doit un jour
  vivre dans le GLB, elle passera par `KHR_animation_pointer`, qui est une
  extension : c'est un autre bac, à instruire.
- **T15 suppose que `etabli.js` expose déjà un helper d'écriture de version et
  un helper de chargement d'aperçu.** Les cinq écritures existantes en
  utilisent forcément un ; le Step 3 dit de les relire et de prendre ceux qui
  existent. Si leurs signatures diffèrent, c'est une adaptation locale — pas
  une raison d'en créer de nouveaux.
- **Le catalogue (T10) dépend d'un réseau au BUILD.** `--fetch` échoue si
  Poly Haven est injoignable ou change de structure ; le message le dit et le
  build s'arrête plutôt que de livrer un catalogue partiel. C'est voulu : un
  installeur avec 22 matières sur 30 serait pire qu'un build rouge.
