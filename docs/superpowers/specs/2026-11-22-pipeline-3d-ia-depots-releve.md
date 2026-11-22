# Pipeline 3D par IA : relevé des 14 dépôts (22/11/2026)

Source : un post X qui liste 14 projets GitHub pour « faire piloter un atelier 3D par Claude Code »
(x.com/0xKense1/status/2123879132090245223, 20/11/2026). Chaque dépôt a été relu le 22/11/2026 (licence, dernière
activité, pilotage sans interface). Rien n'a été cloné ni exécuté.

| # | Dépôt | Licence | Dernière activité | Verdict pour DeepotusVideo |
|---|---|---|---|---|
| 1 | ahujasid/blender-mcp (paquet `mcp-for-blender`) | MIT | 18/11/26 | **DÉJÀ BRANCHÉ** (pont « Scène Blender », t331). Ajouté au catalogue MCP des Réglages. Ne pas l'embarquer dans l'installeur : la socket exécute du Python. |
| 2 | EL4CTEO/blender-skills | MIT | 21/11/26 | **UTILE** : savoir-faire repris dans les fiches de l'agent (retopo, UV, LOD, rig, ARKit). Ses scripts demandent Blender ≥ 5.2. Il n'a pas de minutage audio vers visèmes : c'est ce que fait visage_blender. |
| 3 | gumyr/build123d | Apache-2.0 | 21/11/26 | OPTIONNEL : socles, présentoirs et boîtes imprimables pour Card Forge (fiche cartes-3d). |
| 4 | ranjian0/building_tools | MIT | 24/09/26 | OPTIONNEL : bâtiments procéduraux pour le Plateau et le Studio virtuel (fiche decors-3d). |
| 5 | Tripo-Developer/tripo-3d-for-blender | MIT | 06/11/**2025** | À ÉCARTER : abandonné, s'appuie sur l'API v2 de Tripo fermée le 31/10/2026. |
| 6 | Tripo-Developer/tripo-python-sdk (`tripo3d` 1.x) | MIT | 14/10/26 | **UTILE** : rig et retarget en un appel, smart_lowpoly, mesh_uv, segmentation. À brancher comme fournisseur, à côté de fal et Meshy (lot à venir). |
| 7 | huxingyi/autoremesher | MIT | 07/10/26 | **UTILE** : quads propres en ligne de commande (`autoremesher.exe --input … --target-quads N`). À embarquer dans l'Établi (lot à venir). |
| 8 | CGCookie/retopoflow | **GPL-3.0** | 09/11/26 | À ÉCARTER : interactif et sous GPL. |
| 9 | cnr-isti-vclab/PyMeshLab | **GPL-3.0** | 03/02/26 | À ÉCARTER du produit vendu (GPL). Possible seulement comme processus séparé installé par l'utilisateur. |
| 10 | jpcy/xatlas (PyPI `xatlas`) | MIT | 2024 (le paquet PyPI date de 07/25) | **UTILE** : dépliage UV sans Blender. Vérifier la roue pour le Python embarqué. |
| 11 | RodZill4/material-maker | MIT | 11/11/26 | OPTIONNEL externe : matières PBR procédurales. |
| 12 | armory3d/armorpaint | zlib (binaires payants) | 20/11/26 | À ÉCARTER : ni script ni Python. |
| 13 | zeux/meshoptimizer (`gltfpack`) | MIT | 21/11/26 | **LE PLUS UTILE** : LOD (`-si`), compression (`-cc`), WebP / KTX2. Un seul exe ; complète mesh_lod et mesh_optimize. |
| 14 | donmccurdy/glTF-Transform | MIT | 20/10/26 | UTILE si Node est présent (`inspect`, `optimize`, `draco`). Sinon gltfpack suffit. |

## Livré le 22/11/2026 (branche claude/agent-3d-mcp)

- **Animation faciale** (`backend/app/services/visage_blender.py`) :
  - Synchronisation labiale à partir d'un texte, d'un JSON Rhubarb ou d'un WAV ; expressions ; clignements.
  - Trois façons d'animer : clés de forme ARKit ou visèmes, os du visage (personnages de Blender Studio, Rigify), ou clés DZ_ sculptées sur un personnage généré.
  - Script fixe à un seul trou JSON ; il passe le validateur du mode sûr de mcp-for-blender.
  - Accès :
    - routes `POST /api/blender/visage` (Blender ouvert) et `/visage/fichier` (arrière-plan) ;
    - ligne de commande `scripts/blender/animer_visage.py` ;
    - outil d'agent `visage_preparer`.
  - Banc : `test_visage_blender` (50 vérifications, dont un vrai Blender 5.3).
- **Fiches de compétences des agents métier** (`docs/agent/metiers/competences/`) :
  - personnage-3d ;
  - nettoyage-export-3d ;
  - animation-faciale ;
  - scene-blender ;
  - cartes-3d ;
  - decors-3d.
- **Catalogue « MCP utiles à connecter »** (Réglages › Serveur MCP) :
  - serveurs : deepotus, blender, elevenlabs, figma, canva, notion, github ;
  - pour chacun : commande à copier, écrans aidés, licence et état local ;
  - banc : `test_mcp_catalogue`.

## Essai sur Rain (Blender Studio, CC-BY, rig CloudRig v3.4) — 22/11/2026

- Premier passage : le tri par nom prenait des os de MÉCANIQUE (P-BB-JawLine_3.L, N-BB-Eyelid_Top_2.L, AIM-TAN-…)
  et le maillage du corps (79 clés de correction) au lieu de la tête.
- Corrigé :
  - les os sont classés par `rang()` : forme de commande, collection visible « Face Main », préfixes MSTR-/ACT-/CTR- ;
    les préfixes CloudRig P-, N-, AIM-, TAN-, GRP-, SK-, HLP- sont écartés ;
  - le maillage choisi est celui dont les clés parlent du visage ;
  - les clés pilotées par un driver (20 sur la tête de Rain) sont laissées au rig : en automatique, on anime alors ses os.
- Résultat : MSTR-Jaw, ACT-Lips_Corner, ACT-Eyelid_Upper et MSTR-Eyebrow animés. Au rendu EEVEE, les yeux se ferment,
  la mâchoire s'ouvre (dents visibles), le sourire et les sourcils bougent.
- Banc : cas « rig façon Blender Studio » B11-B13 (53 vérifications).

## Lots suivants proposés
1. gltfpack dans l'Établi : densités et compression d'un clic.
2. AutoRemesher : remaillage en quads avant le rig d'un visage parlant.
3. SDK Tripo 1.x : rig et retarget d'un personnage généré.
4. Rhubarb Lip Sync embarqué : minutage réel des visèmes depuis la voix off.
5. Bouton « Animer le visage » dans la Scène Blender et le Studio 3D.
