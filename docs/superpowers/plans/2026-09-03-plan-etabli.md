# L'Établi — outils de préparation : réparer, profils, ranger, creuser, mesurer, extraire, et le guide de démarrage

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** donner à l'Établi ce qu'un préparateur d'impression attend avant d'ouvrir le slicer — réparer en un clic, connaître l'imprimante, ranger sur le plateau, creuser, mesurer, extraire pièce par pièce, retrouver la lignée dans la Bibliothèque — puis, en lot 2, ce qu'aucune référence ne fait : un guide de démarrage FR/EN, l'aperçu des surplombs et des couches, les connecteurs, les booléens, l'orientation automatique.

**Architecture :** la règle de l'option C ne bouge pas (spec `2026-08-29-etabli-inspecteur-3d-design.md` §2.1) : le navigateur voit et manipule, Python écrit ; `mesh_edit.ecrire_glb` / `ecrire_version` restent la seule plume à GLB. Chaque outil géométrique est un module stdlib pur (`mesh_repair`, `print_profiles`, `nesting`, `hollow`, `mesh_slice`, `mesh_connect`, `mesh_boolean`, `orient`) qui compose un document et le rend à `mesh_edit` ; chaque route `/api/etabli/*` juge son corps puis traduit les `ValueError` en 400 ; chaque écriture est une version de plus avec sa fiche (`depuis`, compte rendu). Les décisions géométriques côté navigateur vivent dans des fonctions PURES exécutées au banc dans node (leçon du plan Établi).

**Tech Stack :** Python 3 embarqué (stdlib + Pillow, **pas de numpy**), FastAPI, three.js 0.185.1 vendorisé (`frontend/lib3d/`), bancs `python -m pytest tests/test_<x>.py` un processus par fichier, node 24.18 pour exécuter le JS pur, campagnes de mutations `backend/tests/mutations_*.py`.

---

## Périmètre — les bacs de R10f, exactement

Source : `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`, `### R10f`. Réponses de l'utilisateur (03/09) : préparation + aperçu de tranchage indicatif et **un guide style tutoriel débutant FR-EN avec lexique et ressources** (mot pour mot en R10f, réponse 1) ; réparation « un clic, et le détail si je veux » ; creusage + drainage + décimation dans l'Établi ; auto-arrange vrai ; profils d'imprimante + import Orca/Elegoo ; l'association de fichier suffit ; Measure, connecteurs, booléens, auto-orient dans cet ordre ; T5, T6, lecture chiffrée du glisser et les deux dettes.

| Lot | Bac | Tâches |
|---|---|---|
| **Lot 1 — parité** | P1 réparer en un clic + détail | 1, 2 |
| | P2 profils d'imprimante (Centauri Carbon 2 par défaut, import OrcaSlicer/ElegooSlicer, lecture seule) | 3, 4 |
| | P3 auto-arrange vrai (rotation, espacement, plusieurs plateaux) | 5 |
| | P4 creusage + drainage + décimation | 6, 7 |
| | P5 Measure | 8 |
| | P6 = T5 extraction par pièce, T6 Bibliothèque hiérarchique, lecture chiffrée du glisser, dette des deux lecteurs, dette assise/recentrer | 9, 10, 11, 12, 13 |
| **Lot 2 — différenciant** | D1 guide de démarrage FR/EN (chapitre 20 étendu + aide dans `/etabli`) | 14, 15 |
| | D2 aperçu de tranchage indicatif (surplombs, couches) | 16 |
| | D3 connecteurs du couteau | 17 |
| | D4 booléens (choix d'algorithme mesuré, sans promesse) | 18 |
| | D5 auto-orient | 19 |
| **Campagne** | mutations `backend/tests/mutations_etabli_outils.py` | 20 |
| **Écarté** | E1 mini-slicer, peinture de supports, hauteurs variables ; E2 envoi réseau ; E3 le connecteur « snap » | section « Écarté » |

**Deux bancs neufs**, un processus chacun, depuis `backend/` : `tests/test_etabli_outils.py` (services Python et routes ; patron `test_etabli_socle.py`, en-tête d'environnement identique) et `tests/test_etabli_outils_page.py` (miroirs de `etabli.js`, `plaque.js`, `viewer.js`, du guide et du bundle ; patron `test_etabli_canevas.py`, avec ses aides `_lire`, `_code`, `_node`, `_fonction_etabli`, `_fonction_etabli_async`, `_constantes_etabli` et `_table_js` recopiées — une soixantaine de lignes — plutôt qu'importées d'un module de 9 700 lignes qui figerait `settings` deux fois ; les tâches 8 et 16 y ajoutent `_fonction_mesure` et `_fonction_surplomb`, bâties sur le même patron). Les trois temps des bancs-miroirs : lire ce qui est ÉCRIT, vérifier la surface (l'id existe dans `index.html`, le nœud existe dans le GLB), compter les assertions.

**Le POURQUOI avec la mesure, mesure d'abord** : chaque module lourd commence par un script de mesure `backend/tests/mesure_etabli_outils.py` (pas collecté : nom sans `test_`) qui fixe le budget sur un maillage de **100 352 triangles** (`build_torus_glb(path, 224, 224)` de `tests/test_mesh_optimize.py`) et sur le modèle réel `%LOCALAPPDATA%\DeepotusVideoGenData\assets\outputs\assets3d\6e0a8a5f\model.v5.glb` (144 274 triangles, douze pièces — le même que `test_etabli_socle.py`, sauté s'il est absent). Un GLB de test n'existe pas dans le dépôt (`find -iname *.glb` → rien, mesuré 03/09) : tout GLB de banc est FABRIQUÉ par `gltf_builder.build_glb` ou `build_torus_glb`.

## Coût de patch

| Tâche | Où | Coût |
|---|---|---|
| 1–2 réparer | `mesh_repair.py`, `routes.py`, `/etabli` (autonome) | backend + page autonome : bon marché ; `ORDRE_ECRITURE` change une fois (ancre 22 de `mutations_assise_couteau.py` à mettre à jour, dite en tâche 2) |
| 3–4 profils | `print_profiles.py`, `print3d.py`, `routes.py`, `/etabli`, `viewer.js` | backend + page autonome ; aucun bundle (le menu « Impression 3D » du bundle passe par la route, qui prend le profil actif) |
| 5 nesting | `nesting.py`, `routes.py`, `plaque.js`, `/etabli` | backend + page autonome |
| 6–7 creuser, percer, décimer | `hollow.py`, `mesh_optimize.py`, `routes.py`, `/etabli` | backend + page autonome |
| 8 Measure | `lib3d/mesure.js`, `/etabli` | page autonome |
| 9 T5 | `mesh_edit.py`, `routes.py`, `/etabli` | backend + page autonome |
| **10 T6** | `routes.py` + **bundle** `scripts/patch_bundle_lignee.py` | **le seul patch de bundle du plan** : tag NEUF `lignee`, `.js.bak_lignee`, EN QUEUE après `etabli`, **deux** ancres uniques mesurées 03/09 (`function __dzEtabli(cb){` ×1, `q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]))` ×1) et cinq sondes amont dont `__dzSrcChips` ×2 ; delta **+458 caractères / +460 octets** (calculé le 03/09 sur le texte exact du replieur), aucun littéral « Établi » ajouté (le compte `("Établi", 2)` de `patch_bundle_etabli.py` tient), rejouable par `python scripts/repatch_all.py --from lignee` |
| 11–13 P6 reste | `/etabli`, `mesh_edit.py`, `mesh_cut.py`, `print3d.py` | page autonome + backend |
| 14–15 guide | `docs/guide/fr.html`, `en.html`, PDF, `frontend/etabli/aide.js` | documents + page autonome |
| 16–19 lot 2 | `surplomb.js`, `mesh_slice.py`, `mesh_connect.py`, `mesh_boolean.py`, `orient.py`, `/etabli` | backend + page autonome |

Le bundle est CRLF et son `.bak_*` est ignoré par git (`.gitignore:58`) : dans un worktree frais seuls quatre `.bak_*` existent (mesuré) — le patcher `lignee` crée le sien depuis le bundle courant, qui est déjà post-`etabli`.

## Références vérifiées (WebFetch, 03/09/2026 sauf mention)

- **OrcaSlicer wiki, Home** (github.com/SoftFever/OrcaSlicer/wiki/Home) : sections « Printer Settings », « Material Settings », « Process Settings », « Prepare », « Calibrations » (Temperature, Volumetric Speed, Pressure Advance, Flow Ratio, Retraction, Tolerance, Cornering, Input Shaping, VFA), « Guides ».
- **OrcaSlicer wiki, Prepare** : `prepare_auto_orient` — « analyzes the mesh geometry to extract face normals and areas », quatre critères (overhang area, bottom contact, support interface, contour complexity), « selects the orientation with the lowest unprintability score », avertissement « may not always find the best orientation » ; `prepare_auto_arrange` — options « Spacing », « Auto rotate for arrangement », « Allow multiple materials on same plate », « Align to Y axis » ; `prepare_mesh_boolean` — Union / Difference (« useful for creating holes or cutouts ») / Intersection ; `prepare_object_manipulation` — Move, Rotate (relatif/absolu), Scale (% ou mm), « Lay on Face … one of the fastest ways to properly orient a model for printing » ; `prepare_cutting_tool` — page existante, contenu rendu par script (seule la phrase d'accroche lue) ; l'inventaire des connecteurs (dovetail, dowel, plug, snap) est celui relevé le 02/09 dans `2026-09-01-etabli-plaque-et-extraction.md`, Task 4.
- **OrcaSlicer wiki, `user_profiles`** : « %APPDATA%\OrcaSlicer », sous-dossier `user` avec `default`, `<UUID>`, `<10 chiffres>`. **Mesuré sur cette machine** (`Get-ChildItem "$env:APPDATA\OrcaSlicer" -Recurse -Depth 2`) : `system\Elegoo\machine\ECC2\Elegoo Centauri Carbon 2 0.4 nozzle.json` porte `printable_area = ["0x0","256x0","256x256","0x256"]`, `printable_height = 256`, `bed_exclude_area = ["246x0","256x0","256x20","246x20"]`, `inherits = "fdm_elegoo_3dp_001_common"` ; le preset 0.2 hérite du 0.4 sans porter `printable_area` (l'héritage DOIT se résoudre) ; `system\Elegoo.json` → `machine_model_list[].sub_path` ; `user\default\machine` est vide ; `OrcaSlicer.conf` n'est PAS du JSON pur (une ligne `MD5 checksum …` en queue — `ConvertFrom-Json` échoue, mesuré) et son bloc `"presets": {"machine": "Elegoo Centauri Carbon 2 0.4 nozzle"}` dit le profil actif. **ElegooSlicer n'est pas installé ici** (`%APPDATA%\ElegooSlicer` absent) : son chemin est un CANDIDAT non mesuré, dérivé de sa filiation (README github.com/ELEGOO-3D/ElegooSlicer : « ElegooSlicer is based on Orca Slicer by SoftFever »).
- **gltfpack** (`gltf/gltfpack.cpp`, aide en ligne de commande) : `-si R: simplify meshes targeting triangle/point count ratio R`, `-sa: aggressively simplify to the target ratio disregarding quality`, `-slb: lock border vertices during simplification`, `-se E: limit simplification error to E (default: 0.01 = 1% deviation)`, `-noq: disable quantization` ; licence MIT (README).
- **Prusa Knowledge Base** : `support-material_1698` (« The Overhang threshold value represents the most horizontal slope … that you can print without support material (90=vertical) », styles Grid / Snug / Organic) ; `modeling-with-3d-printing-in-mind_164135` (« A 3D printer can cleanly print overhanging structures with an angle between 45 and 60 degrees », paroi mini ≈ 0,45 mm à un périmètre, 0,9 mm à deux, jeu ≥ 0,3 mm entre pièces mobiles, « Ensure models are manifold ») ; `poor-bridging_1802` (« Bridging is a term for printing layers over thin air without the use of supports ») ; `pla_2062` (buse 215 °C première couche / 210 °C, lit 60 °C) ; `petg_2059` (buse 230 / 240 °C, lit 85 / 90 °C) ; `layers-and-perimeters_1748` (layer height « Height of the individual slices », perimeters « minimum number of outlines that form the wall ») ; `skirt-and-brim_133969` (skirt « printed outline of all of the models … to stabilize the flow ») ; `infill-patterns_177130` (Gyroid, Cubic, Rectilinear, Grid, Honeycomb, Lightning…) ; `seam-position_151069` (« each perimeter loop has to start and end somewhere … a potentially visible vertical seam », Nearest / Aligned / Random / Rear) ; `warping_2011` (coins soulevés, remèdes : surface propre, brim, enceinte, jupe) ; `filament-material-guide` (page d'entrée : PLA, PETG, ASA/ABS, PC, PA, Flex, composites).
- **Simplify3D, Print Quality Troubleshooting Guide** : page vivante, 26 sujets (Not Sticking to the Bed, Under-Extrusion, Stringing or Oozing, Layer Shifting…).
- **Elegoo wiki** : `wiki.elegoo.com/centauri-carbon-2-combo` (titre « Centauri 2 Series | ELEGOO Wiki », contenu rendu par script), `…/how-to/how-to-control-the-printer-via-lan` (vérifié en R10f le 03/09), `wiki.elegoo.com/Centauri-carbon/centauri-carbon-how-to-print-at-the-full-size` (titre vérifié). La cote 256 × 256 × 256 mm vient du profil Orca mesuré ci-dessus, pas d'un souvenir ; la page produit us.elegoo.com n'a rendu que sa navigation.
- **Non utilisables** : wiki.bambulab.com (HTTP 402 aux deux pages tentées) ; Microsoft 3D Builder (déprécié 07/2024) et Meshmixer (abandonné) — R10f.

## Fichiers

- Créer : `backend/app/services/mesh_repair.py`, `print_profiles.py`, `nesting.py`, `hollow.py`, `mesh_slice.py`, `mesh_connect.py`, `mesh_boolean.py`, `orient.py` ; `frontend/lib3d/mesure.js`, `frontend/lib3d/surplomb.js` ; `frontend/etabli/aide.js` ; `scripts/patch_bundle_lignee.py` ; `backend/tests/test_etabli_outils.py`, `test_etabli_outils_page.py`, `mesure_etabli_outils.py`, `mutations_etabli_outils.py`.
- Modifier : `backend/app/services/mesh_edit.py` (`lire_accesseur`, neuve — tâche 12), `mesh_cut.py` (son lecteur délègue), `print3d.py` (`creer_export(profil=)`, `_accessor`, `lire_glb_triangles(noeuds=)`, `glb_de_triangles`), `mesh_optimize.py` (`decimer_version`), `backend/app/api/routes.py` (routes `/etabli/*`, `/print3d/profils`), `frontend/etabli/etabli.js`, `index.html`, `etabli.css`, `frontend/lib3d/plaque.js`, `viewer.js` (`dessinerContourPlateau`, `dessinerTranches`), `docs/guide/fr.html`, `en.html`, `Deepotus-Guide-FR.pdf`, `Deepotus-Guide-EN.pdf`, `backend/tests/mutations_assise_couteau.py` (ancre 22, tâche 2), `backend/tests/test_etabli_canevas.py` (cinq assertions nommées, tâches 2, 7, 8, 9 et 15).

Conventions de commit : sujet SANS accents, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, jamais de guillemets doubles dans `-m` (guillemets simples).

---

## Lot 1 — parité

### Task 1 : P1 — la mesure, puis `mesh_repair` (soudure, doublons, dégénérés, normales, trous)

**Files :** créer `backend/app/services/mesh_repair.py`, `backend/tests/mesure_etabli_outils.py`, `backend/tests/test_etabli_outils.py`.

- [ ] **Step 1 : le script de mesure, et le budget qu'il fixe**

```python
# backend/tests/mesure_etabli_outils.py — PAS UN TEST (nom sans test_) : mesures des budgets
# python tests/mesure_etabli_outils.py reparer|creuser|nesting|booleen|tranches|orienter
import os, pathlib, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("FAL_KEY", "test-key")
_tmp = tempfile.mkdtemp()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
REEL = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGenData" / \
    "assets" / "outputs" / "assets3d" / "6e0a8a5f" / "model.v5.glb"

def tore():
    from test_mesh_optimize import build_torus_glb
    p = pathlib.Path(_tmp, "tore.glb"); n = build_torus_glb(p, 224, 224)
    print(f"tore : {n['tris']} triangles"); return p.read_bytes()

def chrono(nom, f):
    t0 = time.perf_counter(); r = f(); print(f"{nom} : {time.perf_counter() - t0:.2f} s"); return r

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    quoi = sys.argv[1] if len(sys.argv) > 1 else "reparer"
    data = tore()
    if quoi == "reparer":
        from app.services import mesh_repair
        chrono("reparer tore 100k", lambda: mesh_repair.reparer(data, None, list(mesh_repair.ACTIONS)))
        if REEL.is_file():
            chrono("reparer reel 144k", lambda: mesh_repair.reparer(REEL.read_bytes(), None, list(mesh_repair.ACTIONS)))
```

Run : `python tests/mesure_etabli_outils.py reparer` (depuis `backend/`, python embarqué `%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`)
Expected : `ModuleNotFoundError: No module named 'app.services.mesh_repair'` — le module n'existe pas encore. **Budget fixé ici, avant d'écrire : 100 352 triangles réparés en moins de 20 s** ; au-delà, l'UI proposera la version décimée d'abord (même doctrine que `mesh_report.MAX_TRIS_TOPOLOGIE`).

- [ ] **Step 2 : les tests qui échouent — le cube du dépôt, cassé de cinq façons**

```python
# backend/tests/test_etabli_outils.py — en-tête IDENTIQUE à test_etabli_socle.py (lignes 9-27), puis :
def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")

def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)

def _topo(data):
    from app.services import mesh_edit, mesh_report
    p = pathlib.Path(_tmp, "topo.glb"); p.write_bytes(data)
    return mesh_report.geometry(p)["topologie"]

def _cube_casse(quoi) -> bytes:
    """Le cube du dépôt (24 sommets, 12 triangles, fermé) abîmé d'UNE façon."""
    from app.services import mesh_cut, mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    pr = doc["meshes"][0]["primitives"][0]
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    tris = [tuple(idx[k:k + 3]) for k in range(0, 36, 3)]
    if quoi == "trou": tris = tris[2:]                         # une face (2 triangles) ôtée
    if quoi == "doublons": tris = tris + tris[:3]              # trois triangles en double
    if quoi == "degeneres": tris = tris + [(0, 0, 1), (5, 6, 6)]
    if quoi == "normales": tris = [(t[0], t[2], t[1]) for t in tris[:5]] + tris[5:]
    tampon = bytearray(binc)
    pr["indices"] = mesh_cut._ajouter_indices(doc, tampon, tris)
    doc["buffers"] = [{"byteLength": len(tampon)}]
    return mesh_edit.ecrire_glb(doc, bytes(tampon))

def test_reparer_soude_les_sommets_confondus_SANS_casser_les_coutures_UV():
    from app.services import mesh_edit, mesh_repair, print3d
    sortie, r = mesh_repair.reparer(_cube(), None, ["souder"])
    assert r["pieces"][0]["soudes"] == 0            # 24 sommets, 8 positions, UV différents : rien à souder
    doc, binc = mesh_edit.lire_glb(_cube())
    # le même cube avec un sommet DUPLIQUÉ à l'identique (position ET attributs) : soudé
    from app.services import mesh_cut
    pr = doc["meshes"][0]["primitives"][0]
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    pos = mesh_cut._lire_accesseur(doc, binc, pr["attributes"]["POSITION"])
    assert len(pos) == 24 and len({p for p in pos}) == 8
    assert len(print3d.lire_glb_triangles(sortie)) == 12

def test_reparer_retire_doublons_et_degeneres_et_le_DIT():
    from app.services import mesh_repair, print3d
    for quoi, cle in (("doublons", "doublons"), ("degeneres", "degeneres")):
        assert _topo(_cube_casse(quoi))["ferme"] is False
        sortie, r = mesh_repair.reparer(_cube_casse(quoi), None, [cle])
        assert r["pieces"][0][cle] == (3 if quoi == "doublons" else 2)
        assert len(print3d.lire_glb_triangles(sortie)) == 12 and _topo(sortie)["ferme"] is True

def test_reparer_unifie_les_normales_par_propagation_et_par_le_volume():
    from app.services import mesh_repair, print3d
    casse = _cube_casse("normales")
    assert _volume(print3d.lire_glb_triangles(casse)) < 8.0 - 1e-9
    sortie, r = mesh_repair.reparer(casse, None, ["normales"])
    assert r["pieces"][0]["retournes"] == 5
    assert abs(_volume(print3d.lire_glb_triangles(sortie)) - 8.0) < 1e-9
    # tout à l'envers : la propagation ne voit rien, le VOLUME signé retourne tout
    from app.services import mesh_cut, mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    pr = doc["meshes"][0]["primitives"][0]
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    tampon = bytearray(binc)
    pr["indices"] = mesh_cut._ajouter_indices(doc, tampon, [(idx[k], idx[k + 2], idx[k + 1]) for k in range(0, 36, 3)])
    doc["buffers"] = [{"byteLength": len(tampon)}]
    sortie, r = mesh_repair.reparer(mesh_edit.ecrire_glb(doc, bytes(tampon)), None, ["normales"])
    assert r["pieces"][0]["retournes"] == 12 and abs(_volume(print3d.lire_glb_triangles(sortie)) - 8.0) < 1e-9

def test_reparer_bouche_un_trou_et_refuse_ce_qu_il_ne_sait_pas_boucher_en_le_disant():
    from app.services import mesh_repair, print3d
    troue = _cube_casse("trou")
    assert _topo(troue)["aretes_de_bord"] == 4
    sortie, r = mesh_repair.reparer(troue, None, ["trous"])
    t = r["pieces"][0]["trous"]
    assert t["bouches"] == 1 and t["non_bouches"] == 0 and t["triangles"] == 2
    assert _topo(sortie)["ferme"] is True
    assert abs(_volume(print3d.lire_glb_triangles(sortie)) - 8.0) < 1e-9   # capuchon bien orienté
    assert r["ferme_avant"] is False and r["ferme_apres"] is True
    # un GLB compressé refuse, comme le couteau, en le disant
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube()); doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with pytest.raises(ValueError, match="draco"):
        mesh_repair.reparer(mesh_edit.ecrire_glb(doc, binc), None, ["trous"])
    with pytest.raises(ValueError, match="action inconnue"):
        mesh_repair.reparer(_cube(), None, ["lisser"])
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k reparer`
Expected : `4 failed` — `ModuleNotFoundError`.

- [ ] **Step 3 : le module — tout est une réécriture d'index, les attributs ne bougent jamais**

```python
# -*- coding: utf-8 -*-
"""Réparer en un clic — et DIRE ce qui a été fait. Stdlib pure, sans numpy.

TOUT EST UNE RÉÉCRITURE D'INDEX : UV, normales et tangentes restent ceux du
fichier ; seul le tableau d'indices de chaque primitive est refait. Cinq
actions, dans cet ordre : soudure (même position À tol ET mêmes attributs —
une couture UV n'est PAS un sommet confondu), doublons (même triplet de
positions), dégénérés (deux positions égales), normales (propagation par
arêtes partagées, puis signe de chaque composante par son volume signé),
trous (bords dirigés sans jumelle → boucles → capuchon par les oreilles de
mesh_cut, orienté par −Newell de la boucle). Le document ressort compacté par
mesh_edit._extraire_doc, comme le couteau ; mesh_edit reste la seule plume.
"""
from __future__ import annotations
from app.services.mesh_edit import _extraire_doc, _l, ecrire_glb, lire_glb
from app.services.mesh_cut import (_ajouter_indices, _base_du_plan, _lire_accesseur, _trianguler)

ACTIONS = ("souder", "doublons", "degeneres", "normales", "trous")
_TOL_SOUDURE = 1e-6          # fraction de la diagonale de la pièce

def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)

def souder(pos, attrs, idx, tol):
    vus, rep = {}, list(range(len(pos)))
    for i, p in enumerate(pos):
        k = (tuple(round(c / tol) for c in p),) + tuple(a[i] for a in attrs)
        rep[i] = vus.setdefault(k, i)
    return [rep[i] for i in idx], sum(1 for i, r in enumerate(rep) if r != i)

def degeneres(pos, tris):
    ok = [t for t in tris if len({pos[t[0]], pos[t[1]], pos[t[2]]}) == 3]
    return ok, len(tris) - len(ok)

def doublons(pos, tris):
    vus, ok = set(), []
    for t in tris:
        k = frozenset(pos[i] for i in t)
        if k not in vus:
            vus.add(k); ok.append(t)
    return ok, len(tris) - len(ok)

def _dirs(pos, t):
    return {(pos[t[e]], pos[t[(e + 1) % 3]]) for e in range(3)}

def normales(pos, tris):
    """Enroulement cohérent par composante connexe. Une arête à plus de deux
    triangles (non-manifold) propage au premier venu : dit dans le rapport."""
    tris, adj = [tuple(t) for t in tris], {}
    for n, t in enumerate(tris):
        for (a, b) in _dirs(pos, t):
            adj.setdefault(frozenset((a, b)), []).append(n)
    vus, retournes = [False] * len(tris), 0
    for depart in range(len(tris)):
        if vus[depart]: continue
        comp, pile, vus[depart] = [], [depart], True
        while pile:
            n = pile.pop(); comp.append(n)
            for (a, b) in _dirs(pos, tris[n]):
                for m in adj[frozenset((a, b))]:
                    if vus[m] or m == n: continue
                    if (a, b) in _dirs(pos, tris[m]):          # même sens = incohérent
                        tris[m] = (tris[m][0], tris[m][2], tris[m][1]); retournes += 1
                    vus[m] = True; pile.append(m)
        if _volume([tuple(pos[i] for i in tris[n]) for n in comp]) < 0:
            for n in comp: tris[n] = (tris[n][0], tris[n][2], tris[n][1])
            retournes += len(comp)
    return tris, retournes

def trous(pos, tris):
    """Rend (triangles ajoutés, rapport). Boucle = suite de bords dirigés a→b
    sans jumelle b→a ; un sommet à deux sorties est une JONCTION, dite."""
    ar = {}
    for n, t in enumerate(tris):
        for (a, b) in _dirs(pos, t): ar[(a, b)] = n
    premier = {}
    for t in tris:
        for i in t: premier.setdefault(pos[i], i)
    suivant, sorties = {}, {}
    for (a, b) in ar:
        if (b, a) not in ar:
            sorties[a] = sorties.get(a, 0) + 1; suivant[a] = b
    ajout, vus, r = [], set(), {"bouches": 0, "non_bouches": 0, "triangles": 0, "raisons": [],
                               "jonctions": sum(1 for v in sorties.values() if v > 1)}
    for a0 in list(suivant):
        if a0 in vus: continue
        boucle, cur = [], a0
        while cur in suivant and cur not in vus:
            vus.add(cur); boucle.append(cur); cur = suivant[cur]
        if cur != a0 or len(boucle) < 3:
            r["non_bouches"] += 1; r["raisons"].append(f"chaîne ouverte de {len(boucle)} bord(s)"); continue
        nw = [0.0, 0.0, 0.0]                                   # −Newell : la normale SORTANTE du capuchon
        for i in range(len(boucle)):
            p, q = boucle[i - 1], boucle[i]
            nw[0] -= (p[1] - q[1]) * (p[2] + q[2]); nw[1] -= (p[2] - q[2]) * (p[0] + q[0]); nw[2] -= (p[0] - q[0]) * (p[1] + q[1])
        ln = (nw[0] ** 2 + nw[1] ** 2 + nw[2] ** 2) ** 0.5
        if ln < 1e-24:
            r["non_bouches"] += 1; r["raisons"].append("boucle d'aire nulle"); continue
        n = (nw[0] / ln, nw[1] / ln, nw[2] / ln)
        e1, e2 = _base_du_plan(n)
        plan = [(p[0] * e1[0] + p[1] * e1[1] + p[2] * e1[2], p[0] * e2[0] + p[1] * e2[1] + p[2] * e2[2]) for p in boucle]
        t = _trianguler(plan)
        if t is None:
            r["non_bouches"] += 1; r["raisons"].append(f"boucle de {len(boucle)} points non triangulable"); continue
        ajout += [(premier[boucle[i]], premier[boucle[j]], premier[boucle[k]]) for i, j, k in t]
        r["bouches"] += 1; r["triangles"] += len(t)
    return ajout, r

def _ferme(pos, tris):
    c = {}
    for t in tris:
        for (a, b) in _dirs(pos, t):
            k = (a, b) if a <= b else (b, a); c[k] = c.get(k, 0) + 1
    return all(v == 2 for v in c.values())

def reparer(data: bytes, noeuds=None, actions=None):
    """(glb, rapport). `noeuds` None = toutes les pièces de la scène active."""
    from app.services import print3d
    actions = list(ACTIONS) if actions is None else list(actions)
    for a in actions:
        if a not in ACTIONS: raise ValueError(f"action inconnue : {a} (attendu {', '.join(ACTIONS)})")
    doc, binc = lire_glb(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in print3d._REFUS_EXTENSIONS: raise ValueError(print3d._REFUS_EXTENSIONS[ext])
    nodes = _l(doc, "nodes"); scenes = doc.get("scenes") or [{"nodes": []}]
    racines = list(scenes[int(doc.get("scene", 0))].get("nodes") or [])
    dans, pile = [], list(racines)
    while pile:
        i = pile.pop()
        if i in dans or not (0 <= i < len(nodes)): continue
        dans.append(i); pile.extend(_l(nodes[i], "children"))
    cibles = [i for i in dans if nodes[i].get("mesh") is not None] if noeuds is None else sorted({int(x) for x in noeuds})
    tampon, rapport = bytearray(binc), {"actions": actions, "pieces": []}
    ferme_avant = ferme_apres = True
    for i in cibles:
        if not (0 <= i < len(nodes)) or nodes[i].get("mesh") is None:
            raise ValueError(f"noeud {i} sans maillage — rien à réparer")
        piece = {"noeud_avant": i, "nom": nodes[i].get("name") or f"noeud_{i}", "soudes": 0, "doublons": 0,
                 "degeneres": 0, "retournes": 0, "trous": None}
        for pr in _l(_l(doc, "meshes")[nodes[i]["mesh"]], "primitives"):
            if pr.get("mode", 4) != 4: raise ValueError(f"noeud {i} : primitive non TRIANGLES — hors périmètre")
            attrs = pr.get("attributes") or {}
            pos = _lire_accesseur(doc, binc, attrs["POSITION"])
            autres = [_lire_accesseur(doc, binc, attrs[k]) for k in sorted(attrs) if k != "POSITION"]
            idx = [t[0] for t in _lire_accesseur(doc, binc, pr["indices"])] if pr.get("indices") is not None else list(range(len(pos)))
            xs, ys, zs = [p[0] for p in pos], [p[1] for p in pos], [p[2] for p in pos]
            diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2) ** 0.5 or 1.0
            tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
            ferme_avant = ferme_avant and _ferme(pos, tris)
            if "souder" in actions:
                idx, n = souder(pos, autres, idx, _TOL_SOUDURE * diag); piece["soudes"] += n
                tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
            if "degeneres" in actions: tris, n = degeneres(pos, tris); piece["degeneres"] += n
            if "doublons" in actions: tris, n = doublons(pos, tris); piece["doublons"] += n
            if "normales" in actions: tris, n = normales(pos, tris); piece["retournes"] += n
            if "trous" in actions:
                ajout, rt = trous(pos, tris); tris += ajout
                piece["trous"] = rt if piece["trous"] is None else {k: (piece["trous"][k] + rt[k] if isinstance(rt[k], int) else piece["trous"][k] + rt[k]) for k in rt}
            ferme_apres = ferme_apres and _ferme(pos, tris)
            pr["indices"] = _ajouter_indices(doc, tampon, tris)
        rapport["pieces"].append(piece)
    if not cibles: raise ValueError("aucune pièce à réparer dans la scène active")
    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, m_node = _extraire_doc(doc, bytes(tampon), racines)
    for piece in rapport["pieces"]: piece["noeud_apres"] = m_node.get(piece["noeud_avant"])
    rapport.update({"ferme_avant": ferme_avant, "ferme_apres": ferme_apres})
    return ecrire_glb(out, neuf), rapport
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k reparer`
Expected : `4 passed`.

- [ ] **Step 4 : mesurer contre le budget**

Run : `python tests/mesure_etabli_outils.py reparer`
Expected : `tore : 100352 triangles` puis `reparer tore 100k : <N> s` avec N < 20 (ordre de grandeur attendu 6–12 s : cinq passes O(T) sur des dictionnaires de tuples) ; si N ≥ 20, retirer `souder` de la liste par défaut de l'UI (tâche 2) et le dire dans son infobulle. Consigner N dans la docstring du module (« mesuré le … »).

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_repair.py backend/tests/test_etabli_outils.py backend/tests/mesure_etabli_outils.py
git commit -m 'etabli : mesh_repair - souder, doublons, degeneres, normales, trous, budget mesure' -m 'Réparer en un clic côté serveur : cinq actions qui ne réécrivent que les indices, rapport par pièce, compaction par _extraire_doc ; mesh_edit reste la seule plume. Budget : 100 352 triangles en moins de 20 s (mesuré).' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 2 : P1 — la route et le bouton « Réparer en un clic », le détail dans la barre

**Files :** modifier `backend/app/api/routes.py` (après `etabli_couper`), `frontend/etabli/etabli.js` (`ORDRE_ECRITURE`, `ROUTES`, `LIBELLES_ATTENTE`, `rendreFiche`), `backend/tests/mutations_assise_couteau.py` (ancre 22), `backend/tests/test_etabli_canevas.py` (assertion sur `ORDRE_ECRITURE`) ; tests dans `test_etabli_outils.py` et `test_etabli_outils_page.py`.

- [ ] **Step 1 : test de route (rouge)**

```python
def _client():                      # recopié de test_etabli_socle.py (init_db puis TestClient)
    import asyncio as _a
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    _a.run(init_db()); return TestClient(app)

def _job(nom, data):
    from app.config import settings
    d = settings.outputs_path / "assets3d" / nom; d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data); return d

def test_la_route_reparer_maillage_ecrit_une_version_avec_son_rapport_et_refuse_les_corps_invalides():
    d = _job("job_rep", _cube_casse("trou")); c = _client()
    r = c.post("/api/etabli/reparer-maillage", json={"job": "job_rep", "version": 1})
    assert r.status_code == 200 and r.json()["version"] == 2 and (d / "model.v2.glb").is_file()
    src = r.json()["source"]
    assert src["operation"] == "reparer_maillage" and src["depuis"] == {"version": 1, "fichier": "model.glb"}
    assert src["ferme_apres"] is True and src["pieces"][0]["trous"]["bouches"] == 1
    assert c.post("/api/etabli/reparer-maillage", json={"job": "job_rep", "version": 1, "actions": ["lisser"]}).status_code == 400
    assert c.post("/api/etabli/reparer-maillage", json={"job": "job_rep", "version": "1"}).status_code == 400
    assert c.post("/api/etabli/reparer-maillage", json={"job": "..", "version": 1}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k route_reparer_maillage` → Expected : `1 failed` (404 : la route n'existe pas).

- [ ] **Step 2 : la route**

```python
@router.post("/etabli/reparer-maillage")
async def etabli_reparer_maillage(body: dict):
    """Réparer en un clic : `actions` ⊆ mesh_repair.ACTIONS (toutes par défaut),
    `noeuds` facultatif (toutes les pièces sinon). Le rapport devient le
    `source` de la fiche — le panneau lit ce qui a été fait, pièce par pièce."""
    from app.services import mesh_repair
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"), "réparation du maillage")
    actions = body.get("actions", list(mesh_repair.ACTIONS))
    if not isinstance(actions, list) or not actions or any(a not in mesh_repair.ACTIONS for a in actions):
        raise HTTPException(400, f"réparation : actions attendues parmi {', '.join(mesh_repair.ACTIONS)}")
    noeuds = body.get("noeuds")
    if noeuds is not None and (not isinstance(noeuds, list) or any(not _etabli_entier(n) or n < 0 for n in noeuds)):
        raise HTTPException(400, "réparation : `noeuds` doit être une liste d'index de nœud")
    try:
        sortie, rapport = mesh_repair.reparer(data, noeuds, actions)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "reparer_maillage", {"depuis": depuis, **rapport})
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k route_reparer_maillage` → Expected : `1 passed`.

- [ ] **Step 3 : la page — hors file, comme le couteau, et le détail dans la barre**

Dans `etabli.js` : la constante d'ordre devient, UNE fois pour tout le plan (les opérations qui RENUMÉROTENT écrivent seules, derrière le refus « file non vide » de `ecrireSeule`) :

```js
const ORDRE_ECRITURE = ["transformer", "assise", "reparer", "extraire", "couper",
                        "reparer_maillage", "creuser", "percer", "decimer",
                        "connecteur", "booleen", "orienter"];
/* Ce qui RENUMÉROTE écrit SEUL : la file doit être vide, la ligne y entre pour la
   durée de sa propre écriture, comme confirmerCoupe(). Rend le bilan d'ecrireVersion. */
async function ecrireSeule(operation, charge, source) {
  if (!S.a) { direRefus("aucun modèle chargé"); return null; }
  if (_ecritEnCours) { direRefus("une écriture est en cours — attends la fin de la série"); return null; }
  if (S.enAttente.length) {
    direRefus(`${S.enAttente.length} modification(s) en attente — écris-les d'abord : « ${LIBELLE_OP[operation]} » renumérote les nœuds et ne se met pas en file derrière elles`);
    return null;
  }
  noterAttente(operation, charge, source);
  const bilan = await ecrireVersion();
  if (!bilan || !bilan.ecrites.includes(operation)) {
    const i = S.enAttente.findIndex((t) => t.operation === operation);
    if (i >= 0) S.enAttente.splice(i, 1);
    rendreAttente();
    return null;
  }
  return bilan;
}
const LIBELLE_OP = { reparer_maillage: "réparer le maillage", creuser: "creuser", percer: "percer",
                     decimer: "décimer", connecteur: "connecteur", booleen: "booléen",
                     orienter: "orienter" };
```

`ROUTES` gagne `reparer_maillage: "/api/etabli/reparer-maillage"` ; `LIBELLES_ATTENTE` gagne `reparer_maillage: (t) => \`réparer le maillage : ${t.charge.actions.join(", ")}\``. Dans `rendreFiche()`, après le bloc « Réparer l'assise » :

```js
    <div class="dt-label">Réparer le maillage</div>
    <div class="reparer-actions">${["souder", "doublons", "degeneres", "normales", "trous"].map((a) =>
      `<label><input type="checkbox" data-action="${a}" checked> ${LIBELLE_ACTION[a]}</label>`).join("")}</div>
    <button id="fReparerMaillage">Réparer en un clic</button>
    <p class="note">Écrit AUSSITÔT une version de plus (les nœuds sont renumérotés) ; le détail de
      ce qui a été fait s'affiche dans la barre du bas, et la version d'avant reste sur le disque.</p>
```

avec `const LIBELLE_ACTION = { souder: "sommets confondus", doublons: "faces dupliquées", degeneres: "triangles plats", normales: "normales unifiées", trous: "trous bouchés" };` et le branchement :

```js
  $("#fReparerMaillage").addEventListener("click", async () => {
    const actions = [...$("#panFiche").querySelectorAll("[data-action]:checked")].map((c) => c.dataset.action);
    if (!actions.length) { direRefus("cochez au moins une action de réparation"); return; }
    const bilan = await ecrireSeule("reparer_maillage", { actions });
    if (bilan) direBilanReparation(bilan.derniere);
  });
```

```js
function direBilanReparation(fiche) {
  const src = fiche && fiche.source; if (!src) return;
  const p = (src.pieces || []).reduce((s, x) => ({
    soudes: s.soudes + x.soudes, doublons: s.doublons + x.doublons, degeneres: s.degeneres + x.degeneres,
    retournes: s.retournes + x.retournes, bouches: s.bouches + ((x.trous && x.trous.bouches) || 0),
    non: s.non + ((x.trous && x.trous.non_bouches) || 0) }), { soudes: 0, doublons: 0, degeneres: 0, retournes: 0, bouches: 0, non: 0 });
  direAvis(`réparé (version ${fiche.version}) : ${p.soudes} soudé(s), ${p.doublons} doublon(s), ${p.degeneres} plat(s), `
    + `${p.retournes} retourné(s), ${p.bouches} trou(s) bouché(s)${p.non ? `, ${p.non} NON bouché(s) (détail dans la fiche)` : ""}`
    + ` — ${src.ferme_apres ? "fermé" : "encore ouvert"}`);
}
```

- [ ] **Step 4 : miroir de page (rouge puis vert), et les deux textes qui citent l'ancienne ligne**

Dans `test_etabli_outils_page.py` (en-tête, `_lire`, `_code`, `_node`, `_fonction_etabli`, `_constantes_etabli` recopiés de `test_etabli_canevas.py`) :

```python
def test_reparer_en_un_clic_ecrit_SEUL_et_dit_le_detail():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'reparer_maillage: "/api/etabli/reparer-maillage"' in js
    assert '"reparer_maillage", "creuser", "percer", "decimer",' in js
    assert '"connecteur", "booleen", "orienter"]' in js
    seule = _fonction_etabli("ecrireSeule")
    assert seule.index("S.enAttente.length") < seule.index("noterAttente(operation") < seule.index("await ecrireVersion()")
    fiche = _fonction_etabli("rendreFiche")
    for a in ("souder", "doublons", "degeneres", "normales", "trous"):
        assert f'data-action="{a}"' in js and a in fiche
    assert 'ecrireSeule("reparer_maillage", { actions })' in code
    assert "direBilanReparation(bilan.derniere)" in code and "NON bouché" in _fonction_etabli("direBilanReparation")
```

Puis : dans `backend/tests/mutations_assise_couteau.py`, la mutation 22 remplace ses deux chaînes par la ligne neuve (les douze opérations) et sa variante inversée (`"assise", "transformer", …`) ; dans `test_etabli_canevas.py`, l'assertion de `test_l_extraction_est_ecrite_en_DERNIER_car_elle_renumerote` qui cite `const ORDRE_ECRITURE = [` est alignée sur la ligne neuve (grep `ORDRE_ECRITURE = \[` pour la trouver — une seule).

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k un_clic` → `1 passed` ; `python -m pytest tests/test_etabli_canevas.py -q -k "DERNIER or MET_EN_ATTENTE or AU_SOL"` → tous verts ; `python tests/mutations_assise_couteau.py 22` → `[22] ROUGE`.

- [ ] **Step 5 : commit**

```bash
git add backend/app/api/routes.py frontend/etabli/etabli.js frontend/etabli/etabli.css backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py backend/tests/mutations_assise_couteau.py backend/tests/test_etabli_canevas.py
git commit -m 'etabli : reparer en un clic - route, bouton, detail dans la barre, ecriture seule' -m 'La route juge actions et nœuds ; la page écrit hors file par ecrireSeule (ce qui renumérote n écrit jamais derrière une file) ; le compte rendu par pièce se lit dans la barre et reste dans la fiche.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 3 : P2 — `print_profiles` : Centauri Carbon 2 intégrée, import OrcaSlicer/ElegooSlicer en lecture seule

**Files :** créer `backend/app/services/print_profiles.py` ; tests dans `test_etabli_outils.py`.

- [ ] **Step 1 : mesurer les chemins réels (déjà fait le 03/09 ; à REFAIRE sur la machine d'exécution)**

Run (PowerShell) :
```powershell
Get-ChildItem "$env:APPDATA\OrcaSlicer\system" -Recurse -Filter *.json | Where-Object { $_.FullName -match '\\machine\\' } | Select-Object -First 5 FullName
Get-ChildItem "$env:APPDATA\OrcaSlicer\user" -Recurse -Filter *.json | Select-Object FullName
Test-Path "$env:APPDATA\ElegooSlicer"
```
Expected (03/09) : `…\system\Elegoo\machine\ECC2\Elegoo Centauri Carbon 2 0.4 nozzle.json` parmi les cinq ; aucun JSON sous `user` ; `False` pour ElegooSlicer. Ces trois faits sont ce que le module doit tolérer : un profil hérite, l'utilisateur n'a rien, un slicer peut manquer.

- [ ] **Step 2 : tests (rouge) sur un faux `%APPDATA%` fabriqué au format MESURÉ**

```python
def _faux_orca(tmp):
    """La forme RÉELLE relevée le 03/09 : machine_model, preset instancié qui hérite, preset 0.2 sans printable_area."""
    m = tmp / "OrcaSlicer" / "system" / "Elegoo" / "machine" / "ECC2"; m.mkdir(parents=True)
    (m / "Elegoo Centauri Carbon 2.json").write_text(json.dumps({"type": "machine_model", "name": "Elegoo Centauri Carbon 2"}), "utf-8")
    (m / "Elegoo Centauri Carbon 2 0.4 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Elegoo Centauri Carbon 2 0.4 nozzle", "instantiation": "true",
        "printable_area": ["0x0", "256x0", "256x256", "0x256"], "printable_height": "256",
        "bed_exclude_area": ["246x0", "256x0", "256x20", "246x20"], "inherits": "fdm_elegoo_3dp_001_common"}), "utf-8")
    (m / "Elegoo Centauri Carbon 2 0.2 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Elegoo Centauri Carbon 2 0.2 nozzle", "instantiation": "true",
        "inherits": "Elegoo Centauri Carbon 2 0.4 nozzle", "nozzle_diameter": ["0.2"]}), "utf-8")
    u = tmp / "OrcaSlicer" / "user" / "default" / "machine"; u.mkdir(parents=True)
    (u / "Ma CC2 modifiee.json").write_text(json.dumps({"type": "machine", "name": "Ma CC2 modifiee",
        "inherits": "Elegoo Centauri Carbon 2 0.4 nozzle", "printable_height": "250"}), "utf-8")
    (tmp / "OrcaSlicer" / "OrcaSlicer.conf").write_text('{\n"presets": {"machine": "Elegoo Centauri Carbon 2 0.4 nozzle"}\n}\nMD5 checksum 338F06710BD1E8116D5507BA509F20E1\n', "utf-8")
    return tmp

def test_les_profils_orca_sont_LUS_avec_leur_heritage_et_jamais_ecrits(tmp_path):
    from app.services import print_profiles as PP
    racine = _faux_orca(tmp_path)
    avant = sorted((p.name, p.stat().st_mtime_ns) for p in racine.rglob("*"))
    profils = PP.importer(racine / "OrcaSlicer", "orcaslicer")
    par = {p["nom"]: p for p in profils}
    assert par["Elegoo Centauri Carbon 2 0.2 nozzle"]["plateau_mm"] == [256.0, 256.0]      # hérité du 0.4
    assert par["Elegoo Centauri Carbon 2 0.2 nozzle"]["exclusions_mm"] == [[246.0, 0.0, 256.0, 20.0]]
    assert par["Ma CC2 modifiee"]["hauteur_mm"] == 250.0 and par["Ma CC2 modifiee"]["origine"] == "orcaslicer"
    assert "Elegoo Centauri Carbon 2" not in par                                           # un machine_model n'est pas un preset
    assert PP.profil_actif_du_slicer(racine / "OrcaSlicer") == "Elegoo Centauri Carbon 2 0.4 nozzle"   # la ligne MD5 n'empêche pas de lire
    assert sorted((p.name, p.stat().st_mtime_ns) for p in racine.rglob("*")) == avant      # LECTURE SEULE

def test_le_profil_integre_est_la_centauri_carbon_2_et_le_choix_persiste(tmp_path, monkeypatch):
    from app.config import settings
    from app.services import print_profiles as PP
    monkeypatch.setattr(PP, "_dossiers_slicers", lambda: [])
    assert PP.lister()["profils"][0]["nom"] == "Elegoo Centauri Carbon 2"
    assert PP.profil_courant()["plateau_mm"] == [256.0, 256.0] and PP.profil_courant()["hauteur_mm"] == 256.0
    PP.choisir("integre:elegoo-centauri-carbon-2", {"nom": "Ma résine", "plateau_mm": [143.0, 89.6], "hauteur_mm": 175.0, "exclusions_mm": []})
    assert PP.lister()["actif"] == "manuel:ma-resine" and PP.profil_courant()["plateau_mm"] == [143.0, 89.6]
    with pytest.raises(ValueError, match="inconnu"):
        PP.choisir("orca:nexiste-pas")
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k profil` → `2 failed` (`ModuleNotFoundError`).

- [ ] **Step 3 : le module**

```python
# -*- coding: utf-8 -*-
"""Profils d'imprimante — la Centauri Carbon 2 intégrée, ceux d'OrcaSlicer /
ElegooSlicer IMPORTÉS EN LECTURE SEULE, ceux de l'utilisateur à la main.
Format relevé le 03/09/2026 dans %APPDATA%\OrcaSlicer (voir le plan) :
`printable_area` = quatre "XxY" en mm, `printable_height`, `bed_exclude_area`,
`inherits` (à résoudre : le preset 0.2 ne porte pas de plateau). Le seul fichier
ÉCRIT est le nôtre, profils.json sous assets/print3d."""
from __future__ import annotations
import json, os
from pathlib import Path

INTEGRES = [{"id": "integre:elegoo-centauri-carbon-2", "nom": "Elegoo Centauri Carbon 2", "origine": "integre",
             "plateau_mm": [256.0, 256.0], "hauteur_mm": 256.0, "exclusions_mm": [[246.0, 0.0, 256.0, 20.0]]}]
_SLICERS = (("OrcaSlicer", "orcaslicer"), ("ElegooSlicer", "elegooslicer"))   # ElegooSlicer : candidat NON mesuré (absent ici)

def _dossiers_slicers():
    base = Path(os.environ.get("APPDATA", ""))
    return [(base / nom, tag) for nom, tag in _SLICERS if (base / nom).is_dir()]

def _aire(chaines):
    pts = []
    for c in chaines or []:
        x, y = str(c).lower().split("x"); pts.append((float(x), float(y)))
    return pts

def _lire(p: Path) -> dict:
    d = json.loads(p.read_text("utf-8"))
    return d if isinstance(d, dict) else {}

def _resoudre(d: dict, par_nom: dict, cle: str, profondeur=0):
    if cle in d: return d[cle]
    parent = par_nom.get(str(d.get("inherits") or ""))
    return None if parent is None or profondeur > 8 else _resoudre(parent, par_nom, cle, profondeur + 1)

def importer(racine: Path, origine: str) -> list[dict]:
    fichiers = [p for sous in ("system", "user") for p in (racine / sous).rglob("*.json")
                if p.parent.name == "machine" or p.parent.parent.name == "machine"]
    docs = {}
    for p in fichiers:
        try: d = _lire(p)
        except (ValueError, OSError): continue
        if d.get("type") == "machine" and d.get("name"): docs[str(d["name"])] = (d, p)
    par_nom = {n: d for n, (d, _) in docs.items()}
    out = []
    for nom, (d, p) in sorted(docs.items()):
        aire = _aire(_resoudre(d, par_nom, "printable_area"))
        if len(aire) < 3: continue                     # un preset commun sans plateau n'est pas une imprimante
        xs, ys = [q[0] for q in aire], [q[1] for q in aire]
        excl = _aire(_resoudre(d, par_nom, "bed_exclude_area") or [])
        h = _resoudre(d, par_nom, "printable_height")
        out.append({"id": f"{origine[:5]}:{nom}", "nom": nom, "origine": origine, "fichier": str(p),
                    "plateau_mm": [max(xs) - min(xs), max(ys) - min(ys)],
                    "hauteur_mm": float(h) if h not in (None, "") else None,
                    "exclusions_mm": [[min(q[0] for q in excl), min(q[1] for q in excl), max(q[0] for q in excl), max(q[1] for q in excl)]] if len(excl) >= 3 else []})
    return out

def profil_actif_du_slicer(racine: Path) -> str | None:
    """Le preset machine sélectionné dans le slicer. Le .conf porte une ligne
    `MD5 checksum …` APRÈS le JSON (mesuré) : on lit jusqu'à la dernière accolade."""
    for nom in ("OrcaSlicer.conf", "ElegooSlicer.conf"):
        p = racine / nom
        if p.is_file():
            txt = p.read_text("utf-8", errors="replace")
            try: return (json.loads(txt[:txt.rindex("}") + 1]).get("presets") or {}).get("machine")
            except ValueError: return None
    return None

def _fichier():
    from app.config import settings
    return settings.outputs_path.parent / "print3d" / "profils.json"

def _etat() -> dict:
    p = _fichier()
    if p.is_file():
        try: return json.loads(p.read_text("utf-8"))
        except ValueError: pass
    return {"actif": INTEGRES[0]["id"], "manuels": []}

def lister() -> dict:
    etat = _etat()
    profils = list(INTEGRES) + [{**m, "origine": "manuel"} for m in etat["manuels"]]
    for dossier, tag in _dossiers_slicers(): profils += importer(dossier, tag)
    return {"profils": profils, "actif": etat["actif"],
            "actif_slicer": next((profil_actif_du_slicer(d) for d, _ in _dossiers_slicers()), None)}

def profil_courant() -> dict:
    l = lister()
    return next((p for p in l["profils"] if p["id"] == l["actif"]), INTEGRES[0])

def _slug(nom): return "".join(c if c.isalnum() else "-" for c in nom.lower()).strip("-")[:40]

def choisir(pid: str, manuel: dict | None = None) -> dict:
    etat = _etat()
    if manuel:
        pl = [float(v) for v in manuel.get("plateau_mm") or []]
        if len(pl) != 2 or min(pl) <= 0: raise ValueError("plateau_mm attend deux nombres > 0")
        m = {"id": f"manuel:{_slug(str(manuel.get('nom') or 'imprimante'))}", "nom": str(manuel.get("nom") or "imprimante"),
             "plateau_mm": pl, "hauteur_mm": float(manuel.get("hauteur_mm") or 0) or None,
             "exclusions_mm": [[float(v) for v in e] for e in (manuel.get("exclusions_mm") or []) if len(e) == 4]}
        etat["manuels"] = [x for x in etat["manuels"] if x["id"] != m["id"]] + [m]; pid = m["id"]
    ids = {p["id"] for p in INTEGRES} | {m["id"] for m in etat["manuels"]} | {p["id"] for d, t in _dossiers_slicers() for p in importer(d, t)}
    if pid not in ids: raise ValueError(f"profil inconnu : {pid}")
    etat["actif"] = pid
    p = _fichier(); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=1), "utf-8"); tmp.replace(p)
    return etat
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k profil` → `2 passed`.

- [ ] **Step 4 : commit** — `git commit -m 'print3d : profils d imprimante - Centauri Carbon 2 integree, import OrcaSlicer en lecture seule' -m 'Format relevé sur la machine (printable_area, bed_exclude_area, inherits résolu, .conf avec sa ligne MD5). Le seul fichier écrit est profils.json.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'`

### Task 4 : P2 — la garde de `print3d` devient une propriété du profil ; routes ; contour du plateau dans l'Établi

**Files :** modifier `backend/app/services/print3d.py` (`creer_export`), `backend/app/api/routes.py` (`print3d_from_assets3d`, routes `/print3d/profils`), `frontend/lib3d/viewer.js` (`dessinerContourPlateau`), `frontend/etabli/etabli.js` (`rendreRepere`, `lireRepere`, `graduerPlateau`) ; tests.

- [ ] **Step 1 : tests (rouge)**

```python
def test_la_garde_du_plateau_est_celle_du_PROFIL_et_le_message_ne_change_pas_par_defaut(tmp_path):
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_cube())
    grand = P3.creer_export(tmp_path, "g", tris, 300.0)
    assert "dépasse le plateau de la Centauri Carbon 2 (256 mm)" in grand["avertissement"]
    petit = P3.creer_export(tmp_path, "p", tris, 300.0, profil={"nom": "Ma résine", "plateau_mm": [143.0, 89.6], "hauteur_mm": 175.0})
    assert "Ma résine (143 mm)" in petit["avertissement"]
    assert P3.creer_export(tmp_path, "ok", tris, 140.0, profil={"nom": "Ma résine", "plateau_mm": [143.0, 89.6], "hauteur_mm": 175.0}).get("avertissement") is None
    meta = json.loads((tmp_path / petit["dossier"] / "impression.json").read_text("utf-8"))
    assert meta["profil"] == "Ma résine"

def test_les_routes_profils_listent_choisissent_et_l_impression_prend_le_profil_actif(monkeypatch):
    from app.services import print_profiles as PP
    monkeypatch.setattr(PP, "_dossiers_slicers", lambda: [])
    c = _client(); _job("job_prof", _cube())
    assert c.get("/api/print3d/profils").json()["actif"] == "integre:elegoo-centauri-carbon-2"
    r = c.post("/api/print3d/profils/actif", json={"manuel": {"nom": "Mini", "plateau_mm": [100, 100], "hauteur_mm": 100}})
    assert r.status_code == 200 and r.json()["actif"] == "manuel:mini"
    e = c.post("/api/print3d/from-assets3d/job_prof", json={"cible_mm": 120}).json()
    assert "Mini (100 mm)" in e["avertissement"]
    assert c.post("/api/print3d/profils/actif", json={"id": "orca:rien"}).status_code == 400
```

- [ ] **Step 2 : `print3d.creer_export(..., profil=None)`**

Dans `creer_export`, remplacer le bloc de garde par :

```python
    nom_profil = (profil or {}).get("nom") or "la Centauri Carbon 2"
    plateau = float(max((profil or {}).get("plateau_mm") or [256.0]))
    hauteur = (profil or {}).get("hauteur_mm")
    (lx, ly, lz) = [b[1] - b[0] for b in bb]
    avertissement = None
    if max(lx, ly) > plateau + 1e-6:
        avertissement = (f"{max(lx, ly):.0f} mm dépasse le plateau de {nom_profil} ({plateau:.0f} mm) "
                         "— le slicer devra couper ou réduire")
    elif hauteur and lz > float(hauteur) + 1e-6:
        avertissement = f"{lz:.0f} mm dépasse la hauteur de {nom_profil} ({float(hauteur):.0f} mm)"
```
et ajouter `"profil": nom_profil` dans `meta`. Signature : `def creer_export(base, nom, tris, cible_mm=None, source="", etancheite="inconnue", profil=None)`.

- [ ] **Step 3 : les routes** (après `print3d_open`)

```python
@router.get("/print3d/profils")
async def print3d_profils():
    from app.services import print_profiles as PP
    return await asyncio.to_thread(PP.lister)          # parcourt %APPDATA% : E/S synchrone

@router.post("/print3d/profils/actif")
async def print3d_profil_actif(body: dict):
    from app.services import print_profiles as PP
    try:
        etat = await asyncio.to_thread(PP.choisir, str(body.get("id") or ""), body.get("manuel"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "actif": etat["actif"]}
```
et dans `print3d_from_assets3d`, l'appel devient `P3.creer_export, _print3d_base(), nom, tris, cible, f"assets3d:{Path(job).name}", "inconnue", PP.profil_courant()` (avec `from app.services import print_profiles as PP` en tête de la route). Même passage dans `print3d_from_stl`.

Run : `python -m pytest tests/test_etabli_outils.py -q -k "profil or plateau"` → `4 passed` ; `python -m pytest tests/test_print3d.py -q` → vert (le message par défaut est inchangé).

- [ ] **Step 4 : le contour du plateau réel sur la plaque (viewer.js dessine, la page fournit les cotes)**

Dans `viewer.js`, à côté de `dessinerRegles` :

```js
/* Le CONTOUR d'un plateau réel, posé au coin d'origine des règles, en UNITÉS DU
   MODÈLE — c'est la page qui convertit les millimètres du profil (elle seule
   sait s'il existe une taille cible). `null` efface. `zones` : rectangles
   [u0, v0, u1, v1] exclus (la zone de purge de la Centauri Carbon 2). */
const _contours = new WeakMap();
export function dessinerContourPlateau(api, plateau, cotes) {
  const ancien = _contours.get(api);
  if (ancien) { api.scene.remove(ancien); ancien.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); }); _contours.delete(api); }
  if (!plateau || !cotes || !(cotes.l > 0) || !(cotes.p > 0)) return null;
  const g = plateau, groupe = new THREE.Group(); groupe.name = "plaque-contour";
  const pt = (du, dv) => { const p = new THREE.Vector3(); p[g.u] = g.coin[g.u] + g.sens.u * du; p[g.v] = g.coin[g.v] + g.sens.v * dv; p[g.axe] = g.niveau; return p; };
  const rect = (u0, v0, u1, v1, couleur) => groupe.add(new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints([pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)]),
    new THREE.LineBasicMaterial({ color: couleur })));
  for (let k = 0; k < (cotes.plateaux || 1); k++) rect(k * cotes.l * 1.25, 0, k * cotes.l * 1.25 + cotes.l, cotes.p, 0x62b56a);
  for (const z of cotes.zones || []) rect(z[0], z[1], z[2], z[3], 0xd2544e);
  api.scene.add(groupe); _contours.set(api, groupe);
  return { plateaux: cotes.plateaux || 1, zones: (cotes.zones || []).length };
}
```

Dans `etabli.js` : `const PROFIL = { liste: [], actif: null };` (déclaré après `REP`), chargé à l'import par `jget("/api/print3d/profils")` ; `rendreRepere()` ajoute `<label>imprimante <select id="rProfil"></select></label>` rempli par `rendreProfils()` (option par profil, `change` → `jpost("/api/print3d/profils/actif", { id })`) ; `graduerPlateau()` ajoute, après `dessinerRegles` :

```js
  const p = PROFIL.actif;
  dessinerContourPlateau(S.vueA, PLQ.active ? plateauDe(S.vueA) : null,
    p && enMillimetres() ? { l: p.plateau_mm[0] / REP.echelle, p: p.plateau_mm[1] / REP.echelle, plateaux: PLQ.plateaux || 1,
      zones: (p.exclusions_mm || []).map((z) => z.map((v) => v / REP.echelle)) } : null);
```
(`REP.echelle` = millimètres par unité, donc `mm / echelle` = unités ; `PLQ.plateaux` naît à `1` dans la déclaration de `PLQ` et sera écrit par la tâche 5.) Miroir dans `test_etabli_outils_page.py` : `dessinerContourPlateau` exportée par `viewer.js`, importée par la page, appelée UNIQUEMENT sous `enMillimetres()` (aucun millimètre inventé), et `"256"` absent de `plaque.js` et de `viewer.js` (`_code`).

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k contour` → `1 passed`.

- [ ] **Step 5 : commit** — `git commit -m 'print3d : la garde du plateau vient du profil actif ; contour du plateau reel sur la plaque' -m 'Routes /print3d/profils ; creer_export(profil=) ; viewer.js dessine le contour et la zone exclue en unités du modèle, la page convertit les millimètres du profil sous une taille cible seulement.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'`

### Task 5 : P3 — `nesting` : ranger pour de vrai (rotation, espacement, plusieurs plateaux)

**Files :** créer `backend/app/services/nesting.py` ; modifier `backend/tests/mesure_etabli_outils.py`, `backend/app/api/routes.py`, `frontend/etabli/etabli.js`, `frontend/etabli/index.html` ; tests dans `test_etabli_outils.py` et `test_etabli_outils_page.py`.

- [ ] **Step 1 : la mesure d'abord, et le budget qu'elle fixe**

Ajouter au `if/elif` de `backend/tests/mesure_etabli_outils.py` :

```python
    elif quoi == "nesting":
        import random
        from app.services import nesting
        random.seed(7)
        for n in (12, 120, 500):
            pieces = [{"cle": i, "l": random.uniform(5, 60), "p": random.uniform(5, 60)}
                      for i in range(n)]
            r = chrono(f"ranger {n} pieces",
                       lambda: nesting.ranger(pieces, (256.0, 256.0), 2.0))
            print(f"   -> {len(r['plateaux'])} plateau(x), taux "
                  f"{['%.2f' % t for t in r['taux']]}, {len(r['debordent'])} debordent")
```

Run : `python tests/mesure_etabli_outils.py nesting` (depuis `backend/`)
Expected : `ModuleNotFoundError: No module named 'app.services.nesting'`. **Budget fixé ici, avant d'écrire : 500 empreintes rangées en moins de 1 s** — le squelette est en O(n × segments × 2 orientations) et `segments ≤ n + 1`. Au-delà de `MAX_PIECES`, la route refuse plutôt que de faire attendre.

- [ ] **Step 2 : les tests (rouge)**

Dans `backend/tests/test_etabli_outils.py` :

```python
def test_le_nesting_range_sans_chevauchement_et_TOURNE_quand_cela_fait_gagner():
    """MESURÉ le 03/09 : 96x40 et 40x96 sur un plateau de 100x100, marge 2. À
    plat, la seconde demande 98 de large ET 42+98 = 140 de profondeur : elle ne
    rentre pas. Tournée, elle demande 98 x 42 et se pose à v = 42. Sans
    rotation, la même paire prend DEUX plateaux."""
    from app.services import nesting
    pieces = [{"cle": "A", "l": 96.0, "p": 40.0}, {"cle": "B", "l": 40.0, "p": 96.0}]
    r = nesting.ranger(pieces, (100.0, 100.0), 2.0)
    assert len(r["plateaux"]) == 1 and not r["debordent"]
    poses = {q["cle"]: q for q in r["plateaux"][0]}
    assert poses["A"] == {"cle": "A", "u": 0.0, "v": 0.0, "rot": 0, "l": 96.0, "p": 40.0}
    assert poses["B"] == {"cle": "B", "u": 0.0, "v": 42.0, "rot": 90, "l": 40.0, "p": 96.0}
    assert r["taux"] == [0.768]                       # (96x40 + 40x96) / 100x100
    boites = []
    for q in r["plateaux"][0]:
        l, prof = (q["p"], q["l"]) if q["rot"] == 90 else (q["l"], q["p"])
        assert q["u"] + l <= 100.0 + 1e-9 and q["v"] + prof <= 100.0 + 1e-9
        boites.append((q["u"], q["v"], q["u"] + l, q["v"] + prof))
    a, b = boites
    assert (a[3] <= b[1] + 1e-9 or b[3] <= a[1] + 1e-9
            or a[2] <= b[0] + 1e-9 or b[2] <= a[0] + 1e-9)
    # la marge est bien ENTRE les pièces : 42 − 40 = 2
    assert abs(poses["B"]["v"] - poses["A"]["p"] - 2.0) < 1e-9
    assert len(nesting.ranger(pieces, (100.0, 100.0), 2.0,
                              rotation=False)["plateaux"]) == 2

def test_le_nesting_dit_ce_qui_ne_rentre_sur_AUCUN_plateau_au_lieu_de_le_poser_dehors():
    from app.services import nesting
    r = nesting.ranger([{"cle": "trop", "l": 300.0, "p": 10.0},
                        {"cle": "ok", "l": 10.0, "p": 10.0}], (256.0, 256.0), 2.0)
    assert r["debordent"] == ["trop"]
    assert [p["cle"] for p in r["plateaux"][0]] == ["ok"]
    assert 0.0 < r["taux"][0] < 1.0

def test_le_nesting_refuse_les_entrees_qui_ne_sont_pas_des_cotes():
    import pytest as _p
    from app.services import nesting
    for mauvais in ([], [{"cle": 1, "l": 0.0, "p": 5.0}], [{"cle": 1, "l": 5.0}]):
        with _p.raises(ValueError):
            nesting.ranger(mauvais, (100.0, 100.0), 2.0)
    with _p.raises(ValueError):
        nesting.ranger([{"cle": 1, "l": 5.0, "p": 5.0}], (0.0, 100.0), 2.0)
    with _p.raises(ValueError, match="budget"):
        nesting.ranger([{"cle": i, "l": 1.0, "p": 1.0} for i in range(1001)],
                       (100.0, 100.0), 2.0)

def test_la_route_ranger_calcule_sans_rien_ecrire_et_juge_son_corps():
    c = _client()
    r = c.post("/api/etabli/ranger", json={"pieces": [{"cle": 0, "l": 60, "p": 10},
                                                      {"cle": 1, "l": 60, "p": 10}],
                                           "plateau": [100, 100], "marge": 2})
    d = r.json()
    assert r.status_code == 200 and len(d["plateaux"]) == 1 and len(d["plateaux"][0]) == 2
    assert c.post("/api/etabli/ranger",
                  json={"pieces": [], "plateau": [100, 100]}).status_code == 400
    assert c.post("/api/etabli/ranger",
                  json={"pieces": [{"cle": 0, "l": 1, "p": 1}],
                        "plateau": [100]}).status_code == 400
    assert c.post("/api/etabli/ranger",
                  json={"pieces": [{"cle": 0, "l": 1, "p": 1}],
                        "plateau": [100, 100], "marge": -1}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "nesting or ranger"`
Expected : `4 failed` — `ModuleNotFoundError` pour trois, 404 pour la route.

- [ ] **Step 3 : le module — squelette (skyline) bas-gauche, deux orientations, plateaux en cascade**

```python
# -*- coding: utf-8 -*-
"""Ranger des empreintes sur un ou plusieurs plateaux — stdlib pure.

CE N'EST PAS `plaque.rangerEnEtageres`, ET C'EST LE POINT. Les étagères du
navigateur étalent pour VOIR : elles ne connaissent aucun plateau, ne tournent
rien et ne débordent nulle part. Ici on range pour IMPRIMER — un plateau borné
(la cote du profil actif), un espacement en millimètres, la rotation à plat
quand elle fait gagner, et le débordement sur un second plateau plutôt qu'un
chevauchement silencieux.

L'ALGORITHME : squelette (« skyline ») bas-gauche. Le plateau est décrit par une
suite de segments (x, largeur, hauteur) initialement plats ; chaque pièce est
essayée à l'abscisse de chaque segment, dans ses deux orientations, et l'on
retient la pose dont le SOMMET est le plus bas (puis la plus à gauche). C'est
l'heuristique de bacs à deux dimensions la mieux appariée à des pièces
rectangulaires de tailles voisines, et elle est linéaire en segments — donc
mesurable et bornée, ce qu'un MaxRects n'est pas en Python pur (il garde une
liste de rectangles libres qui enfle en O(n²)).

L'ESPACEMENT EST PORTÉ PAR LA PIÈCE, pas par le plateau : chaque empreinte est
gonflée de `marge` à droite et en haut, et le plateau de `marge` lui aussi. Une
pièce collée au bord garde ainsi sa marge vis-à-vis de ses voisines sans la
perdre contre la paroi — un jeu au bord n'est pas un jeu entre pièces.
"""
from __future__ import annotations

MAX_PIECES = 1000          # borne du budget mesuré (500 en moins de 1 s)
MAX_PLATEAUX = 8


def _cotes(p) -> tuple[float, float]:
    try:
        l, prof = float(p["l"]), float(p["p"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("chaque pièce attend `cle`, `l` et `p` (deux nombres > 0)")
    if not (l > 0) or not (prof > 0):
        raise ValueError(f"pièce {p.get('cle')!r} : l et p doivent être finis et > 0")
    return l, prof


def _poser(skyline, largeur, profondeur, l, p):
    """La meilleure pose de (l, p) sur ce squelette, ou None. Rend (x, y)."""
    meilleur = None
    for i, (x, _w, _h) in enumerate(skyline):
        if x + l > largeur + 1e-9:
            continue
        reste, y, j = l, 0.0, i
        while reste > 1e-9 and j < len(skyline):
            y = max(y, skyline[j][2])
            reste -= skyline[j][1]
            j += 1
        if reste > 1e-9 or y + p > profondeur + 1e-9:
            continue          # l'empreinte dépasse le dernier segment, ou le fond
        if meilleur is None or (y, x) < (meilleur[1], meilleur[0]):
            meilleur = (x, y)
    return meilleur


def _fusionner(skyline, x, l, sommet):
    """Écrase l'intervalle [x, x+l] à la hauteur `sommet`, puis recolle les
    segments de même hauteur — sans quoi le squelette enflerait sans fin et le
    budget de temps mesuré serait faux dès la centième pièce."""
    neuf = []
    for (sx, sw, sh) in skyline:
        if sx + sw <= x + 1e-9 or sx >= x + l - 1e-9:
            neuf.append((sx, sw, sh))
            continue
        if sx < x - 1e-9:
            neuf.append((sx, x - sx, sh))
        if sx + sw > x + l + 1e-9:
            neuf.append((x + l, sx + sw - (x + l), sh))
    neuf.append((x, l, sommet))
    neuf.sort(key=lambda s: s[0])
    colle = []
    for s in neuf:
        if colle and abs(colle[-1][2] - s[2]) < 1e-12 \
                and abs(colle[-1][0] + colle[-1][1] - s[0]) < 1e-9:
            colle[-1] = (colle[-1][0], colle[-1][1] + s[1], s[2])
        else:
            colle.append(s)
    return colle


def ranger(pieces, plateau, marge=2.0, rotation=True, plateaux_max=MAX_PLATEAUX):
    """Range `pieces` — [{cle, l, p}] — sur des plateaux de `plateau` = (L, P).

    Rend {plateaux: [[{cle, u, v, rot, l, p}]], debordent: [cle], taux: [f],
    marge}. `u`/`v` sont le COIN de l'empreinte dans les axes du plateau — la
    forme que `plaque.poserCoin` consomme —, `rot` vaut 0 ou 90 degrés, `l`/`p`
    sont les cotes NON tournées. Toutes les longueurs sont dans l'unité de
    `plateau` : des millimètres, en pratique."""
    if not isinstance(pieces, list) or not pieces:
        raise ValueError("aucune pièce à ranger")
    if len(pieces) > MAX_PIECES:
        raise ValueError(f"{len(pieces)} pièces — au-delà de {MAX_PIECES} le "
                         "rangement dépasse son budget de temps mesuré ; "
                         "range par lots")
    try:
        pl_l, pl_p = float(plateau[0]), float(plateau[1])
    except (IndexError, KeyError, TypeError, ValueError):
        raise ValueError("plateau attend deux nombres > 0 (largeur, profondeur)")
    if not (pl_l > 0) or not (pl_p > 0):
        raise ValueError("plateau attend deux nombres > 0 (largeur, profondeur)")
    m = float(marge)
    if not (m >= 0):
        raise ValueError("marge attend un nombre ≥ 0")
    cotes = [(p["cle"], *_cotes(p)) for p in pieces]
    # la plus grande dimension d'abord : c'est ce qui fait tenir un squelette
    ordre = sorted(cotes, key=lambda c: (-max(c[1], c[2]), -c[1] * c[2]))

    plateaux: list[list[dict]] = []
    squelettes: list[list[tuple]] = []
    debordent: list = []
    for cle, l, p in ordre:
        gl, gp = l + m, p + m       # gonflée : l'espacement voyage avec la pièce
        essais = ((0, gl, gp),) + (((90, gp, gl),) if rotation else ())
        pose, k = None, 0
        while pose is None and k <= len(plateaux):
            if k == len(plateaux):
                # INUTILE D'OUVRIR UN PLATEAU DE PLUS quand le dernier est déjà
                # vide : ce qui ne tient pas sur un plateau nu ne tiendra sur
                # aucun autre. Sans ce garde, une pièce plus grande que la
                # machine ouvrait les huit plateaux à elle seule.
                if len(plateaux) >= plateaux_max or (plateaux and not plateaux[-1]):
                    break
                plateaux.append([])
                squelettes.append([(0.0, pl_l + m, 0.0)])
            for rot, a, b in essais:
                trouve = _poser(squelettes[k], pl_l + m, pl_p + m, a, b)
                if trouve and (pose is None or trouve[1] < pose[1]):
                    pose = (trouve[0], trouve[1], rot, a, b, k)
            k += 1
        if pose is None:
            debordent.append(cle)
            continue
        x, y, rot, a, b, k = pose
        squelettes[k] = _fusionner(squelettes[k], x, a, y + b)
        plateaux[k].append({"cle": cle, "u": x, "v": y, "rot": rot, "l": l, "p": p})
    while plateaux and not plateaux[-1]:
        plateaux.pop()
    aire = pl_l * pl_p
    taux = [round(sum(q["l"] * q["p"] for q in pk) / aire, 4) for pk in plateaux]
    return {"plateaux": plateaux, "debordent": debordent, "taux": taux, "marge": m}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k nesting` → `3 passed`
Run : `python tests/mesure_etabli_outils.py nesting`
Expected (MESURÉ le 03/09 sur cette machine, algorithme identique exécuté à part) :
`ranger 12 pieces : 0.00 s` → 1 plateau, taux 0,13 ; `ranger 120 pieces : 0.01 s` → 3 plateaux (0,79 / 0,81 / 0,31) ; `ranger 500 pieces : 0.04 s` → 8 plateaux à ~0,80 d'occupation et **179 débordent** — huit plateaux de 256 mm ne portent pas 500 pièces de 5 à 60 mm, et le rangement le DIT au lieu de les empiler. **Le budget est tenu à deux ordres de grandeur près** (0,04 s contre 1 s) ; noter le chiffre du jour dans le message de commit.

- [ ] **Step 4 : la route — un calcul, aucune écriture**

Dans `routes.py`, après `etabli_couper` :

```python
@router.post("/etabli/ranger")
async def etabli_ranger(body: dict):
    """Range des empreintes sur des plateaux. AUCUNE ÉCRITURE : la page applique
    le résultat sur la plaque et l'enregistre par le plan de plaque déjà en
    place (`POST /etabli/plaque`). Un rangement est un point de vue sur le
    modèle, pas une correction — il n'a donc pas de version, exactement comme
    l'étalement de la plaque."""
    from app.services import nesting
    pieces = body.get("pieces")
    if not isinstance(pieces, list) or not pieces:
        raise HTTPException(400, "rangement : `pieces` doit être une liste non "
                                 "vide de {cle, l, p}")
    plateau = body.get("plateau")
    if not isinstance(plateau, list) or len(plateau) != 2 \
            or not all(_etabli_nombre(v) and v > 0 for v in plateau):
        raise HTTPException(400, "rangement : `plateau` attend deux nombres > 0")
    marge = body.get("marge", 2.0)
    if not _etabli_nombre(marge) or marge < 0:
        raise HTTPException(400, "rangement : `marge` attend un nombre ≥ 0")
    try:
        return await asyncio.to_thread(
            nesting.ranger, pieces, (float(plateau[0]), float(plateau[1])),
            float(marge), body.get("rotation", True) is not False)
    except ValueError as e:
        raise HTTPException(400, str(e))
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k route_ranger` → `1 passed`.

- [ ] **Step 5 : la page — le bouton, les millimètres exigés, les plateaux en cascade**

Dans `frontend/etabli/index.html`, dans `#vueOutils`, après `#btnCouteau` (l'invariant du banc est AUTO-PORTANT : il compare le nombre de `<button>` de la barre à celui des porteurs de `outil-btn` — le neuf porte donc la classe) :

```html
          <button class="outil-btn" id="btnArranger"></button>
```

Dans `etabli.js` : `PLQ` gagne `plateaux: 1` dans sa déclaration (la tâche 4 le lit déjà) ; près de `PAS_ROTATION`, `const MARGE_PLATEAU_MM = 2;` — *deux millimètres entre pièces, l'espacement que les slicers proposent par défaut ; il voyage avec la pièce (voir `nesting`), jamais avec le plateau* ; `majOutils()` écrit le libellé du bouton (`Ranger sur le plateau`, `title` : « range les pièces sur le plateau du profil actif — rotation, espacement, second plateau si besoin ») ; et :

```js
/* AUTO-ARRANGE. « ranger » est déjà pris par plaque.js, où il veut dire
   « remettre le modèle assemblé » : ici c'est ARRANGER, et le nom le dit —
   deux verbes voisins pour deux gestes opposés se confondraient au premier
   coup d'œil.
   REFUSE HORS MILLIMÈTRES, et ce n'est pas une pudeur : un plateau est une
   cote physique ; ranger des unités glTF sur 256 mm inventerait l'échelle que
   enMillimetres() est le seul site autorisé à poser. */
async function arrangerPlaque() {
  if (!PLQ.active) { direRefus("bascule d'abord sur la plaque"); return; }
  if (!enMillimetres() || !PROFIL.actif) {
    direRefus("pose une taille cible en millimètres et choisis une imprimante — "
      + "un plateau est une cote physique, pas une unité glTF");
    return;
  }
  const empreintes = PLQ.pieces
    .filter((p) => !PLQ.masquees.has(p.cle))
    .map((p) => ({ cle: p.cle, e: empreinteDe(S.vueA, p.cle) }))
    .filter((x) => x.e);
  if (!empreintes.length) { direRefus("aucune pièce visible à ranger"); return; }
  let d;
  try {
    d = await jpost("/api/etabli/ranger", {
      pieces: empreintes.map((x) => ({ cle: x.cle,
        l: x.e.l * REP.echelle, p: x.e.p * REP.echelle })),
      plateau: PROFIL.actif.plateau_mm,
      marge: MARGE_PLATEAU_MM, rotation: true });
  } catch (e) { direRefus(e.message); return; }
  const g = plateauDe(S.vueA);
  if (!g) { direRefus("plateau introuvable"); return; }
  PLQ.plateaux = Math.max(1, d.plateaux.length);
  /* Le second plateau est posé à côté du premier, au MÊME pas que le contour
     que viewer.js dessine (tâche 4, `k * cotes.l * 1.25`) : deux écritures du
     même écart se contrediraient à la première retouche, celle-ci s'y aligne. */
  const largeurPlateau = PROFIL.actif.plateau_mm[0] / REP.echelle;
  d.plateaux.forEach((poses, k) => {
    for (const q of poses) {
      poserAngle(S.vueA, q.cle, q.rot);
      poserCoin(S.vueA, q.cle,
                g.coin[g.u] + k * largeurPlateau * 1.25 + q.u / REP.echelle,
                g.coin[g.v] + q.v / REP.echelle);
      marquerPiece(S.vueA, q.cle);
    }
  });
  graduerPlateau();
  rendreRotation();
  noterPlan();
  direAvis(`rangé : ${d.plateaux.length} plateau(x), occupation `
    + `${d.taux.map((t) => `${Math.round(t * 100)} %`).join(" · ")}`
    + (d.debordent.length
      ? ` — ${d.debordent.length} pièce(s) plus grandes que le plateau, laissées où elles sont`
      : ""));
}
$("#btnArranger").addEventListener("click", arrangerPlaque);
```

- [ ] **Step 6 : le miroir de page**

```python
def test_arranger_exige_les_millimetres_et_pose_les_plateaux_en_cascade():
    js = _lire("etabli/etabli.js")
    assert '<button class="outil-btn" id="btnArranger">' in _lire("etabli/index.html")
    f = _fonction_etabli("arrangerPlaque")
    assert f.index("enMillimetres()") < f.index('jpost("/api/etabli/ranger"')
    assert "PROFIL.actif.plateau_mm" in f and "REP.echelle" in f
    assert "poserAngle(S.vueA, q.cle, q.rot)" in f and "poserCoin(" in f
    # le MÊME écart entre plateaux que le contour dessiné par viewer.js
    assert f.count("* 1.25") == 1 and "* 1.25" in _code("lib3d/viewer.js")
    assert "PLQ.plateaux = Math.max(1, d.plateaux.length)" in f
    assert "noterPlan();" in f
    assert "const MARGE_PLATEAU_MM = 2;" in js
    # aucun millimètre inventé dans le corps : la cote vient du profil
    corps = _code("etabli/etabli.js").split("function arrangerPlaque", 1)[1] \
        .split("\n}\n", 1)[0]
    assert "256" not in corps
    assert "plateaux: 1" in js.split("const PLQ = {", 1)[1].split("};", 1)[0]
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k arranger` → `1 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k outils_vivent` → `1 passed` (l'invariant auto-portant des `outil-btn` tient).

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/nesting.py backend/app/api/routes.py backend/tests/mesure_etabli_outils.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js frontend/etabli/index.html
git commit -m 'etabli : auto-arrange vrai - squelette bas-gauche, rotation a plat, plateaux en cascade' -m 'nesting.ranger est stdlib pur et borné (500 empreintes sous le budget mesuré, chiffre au banc de mesure) ; la marge voyage avec la pièce, jamais avec le plateau ; le bouton refuse hors millimètres — un plateau est une cote physique — et dit le taux d occupation et ce qui déborde.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 6 : P4 — `hollow.creuser` : une paroi en millimètres, et la limite du procédé, comptée

**Files :** créer `backend/app/services/hollow.py` ; modifier `backend/tests/mesure_etabli_outils.py`, `backend/app/api/routes.py`, `frontend/etabli/etabli.js` ; tests dans les deux bancs neufs.

- [ ] **Step 1 : la mesure d'abord**

Ajouter au `if/elif` de `mesure_etabli_outils.py` :

```python
    elif quoi == "creuser":
        from app.services import hollow
        chrono("creuser tore 100k paroi 0,05",
               lambda: hollow.creuser(data, None, 0.05))
        if REEL.is_file():
            chrono("creuser reel 144k paroi 0,001",
                   lambda: hollow.creuser(REEL.read_bytes(), None, 0.001))
```

Run : `python tests/mesure_etabli_outils.py creuser`
Expected : `ModuleNotFoundError: No module named 'app.services.hollow'`. **Budget fixé ici, avant d'écrire : 100 352 triangles creusés (200 704 en sortie) en moins de 20 s** — trois passes linéaires sur des tuples Python (normales par aire, comptage des effondrements, dichotomie de douze pas). Au-delà de `MAX_TRIS`, la route refuse et propose la décimation (tâche 7) d'abord, du même mot que `mesh_report.MAX_TRIS_TOPOLOGIE`.

Si le temps mesuré dépasse 20 s : ne PAS élargir le budget. Réduire `_PAS_DICHOTOMIE` à 6 (la dichotomie est le seul terme multiplicatif ; six pas donnent déjà la paroi à 1,6 % près) et re-mesurer avant de continuer.

- [ ] **Step 2 : les tests (rouge)**

Dans `backend/tests/test_etabli_outils.py` :

```python
def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)

def test_creuser_double_la_peau_garde_le_dehors_et_soustrait_le_dedans():
    from app.services import hollow, print3d
    sortie, r = hollow.creuser(_cube(), None, 0.25)       # le cube du dépôt : arête 2
    tris = print3d.lire_glb_triangles(sortie)
    assert len(tris) == 24                                # 12 dehors + 12 dedans retournés
    # volume signé de la coque : 2³ − 1,5³ (la peau intérieure retourne son signe)
    assert abs(_volume(tris) - (8.0 - 1.5 ** 3)) < 1e-6
    p = r["pieces"][0]
    assert p["paroi"] == 0.25 and p["effondres"] == 0
    assert p["triangles_avant"] == 12 and p["triangles_apres"] == 24
    b = print3d.bbox(tris)
    assert abs((b[0][1] - b[0][0]) - 2.0) < 1e-9          # la peau extérieure n'a pas bougé
    assert r["avertissement"] is None

def test_creuser_COMPTE_les_triangles_effondres_et_nomme_la_paroi_qui_tient():
    from app.services import hollow
    _sortie, r = hollow.creuser(_cube(), None, 1.5)       # plus que la demi-arête
    p = r["pieces"][0]
    assert p["effondres"] > 0
    assert 0.0 < p["paroi_max"] < 1.5
    assert "effondr" in r["avertissement"] and "paroi" in r["avertissement"]

def test_creuser_refuse_ce_qu_il_ne_sait_pas_lire_et_les_parois_absurdes():
    import pytest as _p
    from app.services import hollow, mesh_edit
    for paroi in (0.0, -1.0, "2"):
        with _p.raises(ValueError, match="paroi"):
            hollow.creuser(_cube(), None, paroi)
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with _p.raises(ValueError, match="draco"):
        hollow.creuser(mesh_edit.ecrire_glb(doc, binc), None, 0.1)
    with _p.raises(ValueError, match="aucune pièce"):
        hollow.creuser(_cube(), [999], 0.1)

def test_la_route_creuser_convertit_les_millimetres_et_ecrit_une_version():
    d = _job("job_creux", _cube()); c = _client()
    r = c.post("/api/etabli/creuser", json={"job": "job_creux", "version": 1,
                                            "paroi_mm": 2.0, "echelle": 8.0})
    assert r.status_code == 200 and (d / "model.v2.glb").is_file()
    src = r.json()["source"]
    assert src["operation"] == "creuser" and src["paroi_mm"] == 2.0 and src["echelle"] == 8.0
    assert src["depuis"] == {"version": 1, "fichier": "model.glb"}
    assert abs(src["pieces"][0]["paroi"] - 0.25) < 1e-12   # 2 mm ÷ 8 mm par unité
    for corps in ({"paroi_mm": 2.0, "echelle": 0}, {"paroi_mm": 0, "echelle": 8},
                  {"paroi_mm": 2.0}, {"paroi_mm": 2.0, "echelle": 8, "noeuds": ["a"]}):
        assert c.post("/api/etabli/creuser",
                      json={"job": "job_creux", "version": 1, **corps}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k creuser` → `4 failed`.

- [ ] **Step 3 : le module**

```python
# -*- coding: utf-8 -*-
"""Creuser : doubler la peau vers l'intérieur, et DIRE où la paroi ne tient pas.

CE QUE C'EST, EXACTEMENT : une coque par décalage des sommets le long de leur
normale moyennée par aire, la peau intérieure retournée. C'est le procédé que
tous les préparateurs appellent « shell », et il a une limite CONNUE : dans un
creux plus serré que la paroi, la peau intérieure se retourne sur elle-même et
le solide s'auto-intersecte. On ne la cache pas — on COMPTE les triangles dont
la normale s'inverse sous le décalage (`effondres`), on cherche par dichotomie
la paroi la plus épaisse qui n'en produit aucun (`paroi_max`), et le compte
rendu le dit. Un creusage muet qui rend un solide faux est ce que ce module
refuse d'être.

CE QUE CE N'EST PAS : un décalage exact. Celui-là demande un champ de distance
signée, donc une grille de voxels, donc numpy — ABSENT du Python embarqué
(mesuré le 27/08, rappelé dans print3d.py). La tâche 18 mesure cette famille-là
pour les booléens ; ici on assume le procédé simple et on publie sa limite.

`mesh_edit` RESTE LA SEULE PLUME : ce module compose un document et un tampon,
il n'écrit aucun fichier.
"""
from __future__ import annotations

import math

from app.services.mesh_cut import (_ajouter_flottants, _ajouter_indices,
                                   _lire_accesseur)
from app.services.mesh_edit import _extraire_doc, _l, ecrire_glb, lire_glb

MAX_TRIS = 200_000          # borne du budget mesuré (100 352 sous 20 s)
_PAS_DICHOTOMIE = 12


def refus_compression(doc: dict, quoi: str) -> None:
    """Le refus commun aux outils qui LISENT des triangles. Écrit ici et importé
    par les modules suivants (perçage, tranches, booléens, orientation) : cinq
    copies de la même phrase divergeraient à la première retouche."""
    for ext in (doc.get("extensionsRequired") or []):
        bas = ext.lower()
        if "draco" in bas or "meshopt" in bas:
            raise ValueError(
                f"GLB compressé ({ext}) — {quoi} lit des triangles et ne sait "
                "pas les décompresser. Pars du model.glb non compressé.")


def _normale(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])


def normales_sommets(pos, tris):
    """Normales moyennées par AIRE — le produit vectoriel non normalisé la porte
    déjà. Une moyenne de normales UNITAIRES ferait pivoter la peau vers les
    facettes fines, qui sont nombreuses là où la géométrie est fine : le
    creusage y mangerait justement la matière qu'il faut préserver."""
    acc = [[0.0, 0.0, 0.0] for _ in pos]
    for (i, j, k) in tris:
        n = _normale(pos[i], pos[j], pos[k])
        for s in (i, j, k):
            acc[s][0] += n[0]; acc[s][1] += n[1]; acc[s][2] += n[2]
    out = []
    for n in acc:
        d = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        out.append((0.0, 0.0, 0.0) if d < 1e-20
                   else (n[0] / d, n[1] / d, n[2] / d))
    return out


def _effondres(pos, nrm, tris, paroi):
    """Combien de triangles retournent leur normale sous ce décalage."""
    n = 0
    for (i, j, k) in tris:
        av = _normale(pos[i], pos[j], pos[k])
        d = [tuple(pos[s][c] - nrm[s][c] * paroi for c in range(3)) for s in (i, j, k)]
        ap = _normale(*d)
        if av[0] * ap[0] + av[1] * ap[1] + av[2] * ap[2] <= 0.0:
            n += 1
    return n


def creuser(data: bytes, noeuds, paroi):
    """Rend (GLB, rapport). `paroi` est en UNITÉS DU MODÈLE ; la route la déduit
    des millimètres et de l'échelle, qu'elle seule connaît."""
    if not isinstance(paroi, (int, float)) or isinstance(paroi, bool) \
            or paroi != paroi or paroi <= 0:
        raise ValueError("paroi : un nombre fini > 0 est attendu "
                         "(en unités du modèle)")
    paroi = float(paroi)
    doc, binc = lire_glb(data)
    refus_compression(doc, "le creusage")
    nodes = _l(doc, "nodes")
    cible = None if noeuds is None else set(int(n) for n in noeuds)
    vises = [i for i in range(len(nodes))
             if (cible is None or i in cible) and "mesh" in nodes[i]]
    if not vises:
        raise ValueError("aucune pièce à creuser dans la sélection")

    tampon = bytearray(binc)
    pieces, total = [], 0
    for i in vises:
        mesh = _l(doc, "meshes")[nodes[i]["mesh"]]
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4 or "POSITION" not in (prim.get("attributes") or {}):
                continue
            pos = [tuple(v) for v in
                   _lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
            idx = ([t[0] for t in _lire_accesseur(doc, binc, prim["indices"])]
                   if "indices" in prim else list(range(len(pos))))
            tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
            total += len(tris)
            if total > MAX_TRIS:
                raise ValueError(
                    f"plus de {MAX_TRIS} triangles — le creusage dépasse son "
                    "budget de temps mesuré. Décime d'abord (bouton "
                    "« Décimer »), puis creuse.")
            nrm = normales_sommets(pos, tris)
            eff = _effondres(pos, nrm, tris, paroi)
            bas, haut = 0.0, paroi
            for _ in range(_PAS_DICHOTOMIE):
                mid = (bas + haut) / 2
                if _effondres(pos, nrm, tris, mid):
                    haut = mid
                else:
                    bas = mid
            n0 = len(pos)
            dedans = [tuple(pos[s][c] - nrm[s][c] * paroi for c in range(3))
                      for s in range(n0)]
            tous = list(pos) + dedans
            plat = [c for p in tous for c in p]
            mini = [min(p[c] for p in tous) for c in range(3)]
            maxi = [max(p[c] for p in tous) for c in range(3)]
            # LES AUTRES ATTRIBUTS TOMBENT, et c'est dit : une peau intérieure
            # n'a ni les UV ni les tangentes de l'extérieure, et les recopier
            # telles quelles produirait une texture retournée. Le creusage sert
            # l'impression, où seule la géométrie compte. `material` reste
            # attaché : seul le tableau d'attributs est refait.
            prim["attributes"] = {"POSITION": _ajouter_flottants(
                doc, tampon, plat, 3, mini, maxi)}
            prim["indices"] = _ajouter_indices(
                doc, tampon,
                tris + [(b + n0, a + n0, c + n0) for (a, b, c) in tris])
            pieces.append({"noeud": i,
                           "nom": nodes[i].get("name") or f"nœud {i}",
                           "triangles_avant": len(tris),
                           "triangles_apres": 2 * len(tris),
                           "paroi": paroi, "effondres": eff,
                           "paroi_max": round(bas, 9)})
    if not pieces:
        raise ValueError("aucune pièce à creuser dans la sélection")
    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, _ = _extraire_doc(doc, bytes(tampon), list(range(len(nodes))))
    total_eff = sum(p["effondres"] for p in pieces)
    rapport = {
        "paroi": paroi, "pieces": pieces,
        "avertissement": (
            None if not total_eff else
            f"{total_eff} triangle(s) effondrés : la paroi de {paroi:g} est plus "
            "épaisse que le creux le plus serré, le solide s'auto-intersecte. "
            f"Paroi qui tient : {min(p['paroi_max'] for p in pieces):g} unité(s) "
            "du modèle."),
    }
    return ecrire_glb(out, neuf), rapport
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k creuser` → `3 passed, 1 failed` (la route manque)
Run : `python tests/mesure_etabli_outils.py creuser` → deux lignes chronométrées ; **noter les deux temps dans le message de commit**.

- [ ] **Step 4 : la route — c'est ELLE qui connaît les millimètres**

```python
@router.post("/etabli/creuser")
async def etabli_creuser(body: dict):
    """Creuse : `paroi_mm` (> 0) et `echelle` (millimètres par unité du modèle,
    > 0), `noeuds` facultatif. LES MILLIMÈTRES N'ENTRENT PAS DANS LE SERVICE :
    un GLB n'en porte aucun (voir `viewer.echelleMm`), et c'est la page — seule
    à porter la taille cible — qui fournit le facteur. La fiche garde les deux
    nombres, pour qu'une version se relise sans deviner."""
    from app.services import hollow
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "creusage")
    paroi_mm, echelle = body.get("paroi_mm"), body.get("echelle")
    if not _etabli_nombre(paroi_mm) or paroi_mm <= 0:
        raise HTTPException(400, "creusage : `paroi_mm` attend un nombre > 0")
    if not _etabli_nombre(echelle) or echelle <= 0:
        raise HTTPException(400, "creusage : `echelle` (mm par unité du modèle) "
                                 "attend un nombre > 0 — pose une taille cible")
    noeuds = body.get("noeuds")
    if noeuds is not None and (not isinstance(noeuds, list)
                               or any(not _etabli_entier(n) or n < 0 for n in noeuds)):
        raise HTTPException(400, "creusage : `noeuds` doit être une liste "
                                 "d'index de nœud")
    try:
        sortie, rapport = await asyncio.to_thread(
            hollow.creuser, data, noeuds, float(paroi_mm) / float(echelle))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "creuser",
                          {"depuis": depuis, "paroi_mm": float(paroi_mm),
                           "echelle": float(echelle), **rapport})
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k creuser` → `4 passed`.

- [ ] **Step 5 : la page — dans le panneau Fiche, sous la réparation**

`ROUTES` gagne `creuser: "/api/etabli/creuser"`. Dans `rendreFiche()`, après le bloc « Réparer le maillage » :

```js
    <div class="dt-label">Creuser</div>
    <label>paroi <input id="fParoi" type="number" step="0.1" min="0.1" value="2"> mm</label>
    <button id="fCreuser">Creuser</button>
    <p class="note">Double la peau vers l'intérieur. Exige une taille cible — une
      paroi est une cote physique. Ce que la paroi ne peut pas tenir est COMPTÉ
      et dit ; le compte rendu propose alors l'épaisseur qui tient.</p>
```

et le branchement, à la suite de celui de « Réparer en un clic » :

```js
  $("#fCreuser").addEventListener("click", async () => {
    if (!enMillimetres()) {
      direRefus("pose une taille cible : une paroi de 2 mm n'a de sens qu'avec une échelle");
      return;
    }
    const paroi = Number($("#fParoi").value);
    if (!(paroi > 0)) { direRefus("paroi : un nombre de millimètres > 0"); return; }
    const bilan = await ecrireSeule("creuser",
      { paroi_mm: paroi, echelle: REP.echelle, noeuds: noeudsRetenus().noeuds });
    if (!bilan) return;
    const src = bilan.derniere.source;
    direAvis(`creusé (version ${bilan.derniere.version}) : paroi ${paroi} mm sur `
      + `${src.pieces.length} pièce(s)`
      + (src.avertissement ? ` — ${src.avertissement}` : ""));
  });
```

`LIBELLES_ATTENTE` gagne `creuser: (t) => \`creuser : paroi ${t.charge.paroi_mm} mm\``.

- [ ] **Step 6 : le miroir**

```python
def test_creuser_exige_les_millimetres_et_repete_l_avertissement_du_serveur():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'creuser: "/api/etabli/creuser"' in js
    fiche = _fonction_etabli("rendreFiche")
    assert 'id="fParoi"' in fiche and 'id="fCreuser"' in fiche
    bloc = code.split('$("#fCreuser").addEventListener', 1)[1].split("  });", 1)[0]
    assert bloc.index("enMillimetres()") < bloc.index('ecrireSeule("creuser"')
    assert "echelle: REP.echelle" in bloc and "src.avertissement" in bloc
    assert "creuser" in _table_js("etabli/etabli.js", "LIBELLES_ATTENTE")
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k creuser` → `1 passed`.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/hollow.py backend/app/api/routes.py backend/tests/mesure_etabli_outils.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js
git commit -m 'etabli : creuser - coque par decalage des sommets, et la limite du procede est comptee et dite' -m 'Le service ne connaît que des unités du modèle ; la route convertit les millimètres par l échelle que la page seule porte. Les triangles effondrés sont comptés et la paroi qui tient est cherchée par dichotomie, plutôt que de rendre un solide auto-intersecté en silence. Temps mesurés au banc de mesure, reportés ici.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 7 : P4 — percer (drainage) et décimer depuis l'Établi

**Files :** modifier `backend/app/services/hollow.py` (`percer`), `backend/app/services/mesh_optimize.py` (`decimer_version`), `backend/app/api/routes.py`, `frontend/etabli/etabli.js` ; tests dans les deux bancs neufs.

- [ ] **Step 1 : les tests de `percer` (rouge)**

```python
def _cube_creux():
    from app.services import hollow
    return hollow.creuser(_cube(), None, 0.25)[0]

def test_percer_ouvre_le_creux_et_recoud_les_deux_peaux():
    from app.services import hollow, mesh_report, print3d
    import pathlib, tempfile
    creux = _cube_creux()
    sortie, r = hollow.percer(creux, None, [0.0, -1.0, 0.0], [0.0, -1.0, 0.0], 0.4)
    p = r["pieces"][0]
    assert p["retires"] > 0 and p["boucles"] == 2 and p["tube"] > 0
    # le trou débouche : le solide reste FERMÉ (la paroi du tube recoud tout)
    d = pathlib.Path(tempfile.mkdtemp()); (d / "m.glb").write_bytes(sortie)
    assert mesh_report.geometry(d / "m.glb")["topologie"]["ferme"] is True
    assert len(print3d.lire_glb_triangles(sortie)) > 0

def test_percer_refuse_en_le_disant_quand_le_rayon_ne_prend_aucun_triangle():
    import pytest as _p
    from app.services import hollow
    with _p.raises(ValueError, match="aucun triangle"):
        hollow.percer(_cube_creux(), None, [0.0, -1.0, 0.0], [0.0, -1.0, 0.0], 1e-4)
    with _p.raises(ValueError, match="rayon"):
        hollow.percer(_cube_creux(), None, [0.0, -1.0, 0.0], [0.0, -1.0, 0.0], 0.0)
    with _p.raises(ValueError, match="direction"):
        hollow.percer(_cube_creux(), None, [0.0, -1.0, 0.0], [0.0, 0.0, 0.0], 0.4)
    # un solide PLEIN n'a qu'une peau : le perçage le dit au lieu de coudre à vide
    with _p.raises(ValueError, match="deux peaux"):
        hollow.percer(_cube(), None, [0.0, -1.0, 0.0], [0.0, -1.0, 0.0], 0.4)

def test_la_route_percer_ecrit_une_version_et_juge_son_corps():
    d = _job("job_perce", _cube_creux()); c = _client()
    r = c.post("/api/etabli/percer", json={"job": "job_perce", "version": 1,
                                           "point": [0, -1, 0], "normale": [0, -1, 0],
                                           "rayon_mm": 3.2, "echelle": 8.0})
    assert r.status_code == 200 and (d / "model.v2.glb").is_file()
    src = r.json()["source"]
    assert src["operation"] == "percer" and src["rayon_mm"] == 3.2
    for corps in ({"point": [0, -1, 0], "normale": [0, 0, 0], "rayon_mm": 3.2, "echelle": 8},
                  {"point": [0, -1, 0], "normale": [0, -1, 0], "rayon_mm": 0, "echelle": 8},
                  {"point": "x", "normale": [0, -1, 0], "rayon_mm": 3.2, "echelle": 8}):
        assert c.post("/api/etabli/percer",
                      json={"job": "job_perce", "version": 1, **corps}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k percer` → `3 failed`.

- [ ] **Step 2 : `hollow.percer` — retirer un disque sur chaque peau, coudre un tube entre les deux bords**

À la suite de `creuser`, dans `hollow.py` :

```python
def _base_orthonormee(n):
    """Deux vecteurs unitaires orthogonaux à `n` — pour mesurer un angle autour
    de l'axe. `mesh_cut._base_du_plan` fait déjà ce calcul ; on l'importerait
    si le couteau n'était pas destiné à devenir un consommateur de CE
    module-ci. Écrit ici, six lignes, sans dépendance croisée."""
    a = (0.0, 0.0, 1.0) if abs(n[0]) > 0.9 else (1.0, 0.0, 0.0)
    u = (n[1] * a[2] - n[2] * a[1], n[2] * a[0] - n[0] * a[2],
         n[0] * a[1] - n[1] * a[0])
    lu = math.sqrt(sum(c * c for c in u)) or 1.0
    u = tuple(c / lu for c in u)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2],
         n[0] * u[1] - n[1] * u[0])
    return u, v


def _bords_ouverts(tris):
    """Les arêtes DIRIGÉES sans jumelle, chaînées en boucles. Même mécanique
    que `mesh_repair.trous` — et pour la même raison : un trou se referme par
    ses bords, jamais par une devinette sur la forme."""
    sortie, entrantes = {}, set()
    for (i, j, k) in tris:
        for (a, b) in ((i, j), (j, k), (k, i)):
            entrantes.add((a, b))
    ouverts = [(a, b) for (a, b) in entrantes if (b, a) not in entrantes]
    suivant = {}
    for (a, b) in ouverts:
        suivant.setdefault(a, []).append(b)
    boucles, vus = [], set()
    for (a0, _b0) in ouverts:
        if a0 in vus:
            continue
        boucle, s = [], a0
        while s in suivant and suivant[s] and s not in vus:
            vus.add(s); boucle.append(s); s = suivant[s].pop()
        if len(boucle) >= 3:
            boucles.append(boucle)
    return boucles


def percer(data: bytes, noeuds, point, normale, rayon):
    """Perce un trou de drainage CYLINDRIQUE à travers les deux peaux d'une
    pièce creusée, et recoud le tube entre elles.

    LE PROCÉDÉ, ET SES REFUS. On retire de chaque peau les triangles dont les
    TROIS sommets sont à moins de `rayon` de l'axe ; les deux bords ouverts qui
    apparaissent sont chaînés en boucles ; les boucles sont appariées par ANGLE
    autour de l'axe et cousues deux à deux. Exactement DEUX boucles sont
    attendues (l'extérieure et l'intérieure) : zéro dit que le rayon est plus
    petit qu'un triangle, une seule dit que la pièce n'est pas creuse, plus de
    deux que l'axe rase un relief. Chacun de ces trois cas SE DIT — un tube
    cousu à l'aveugle rendrait un solide faux, imprimé.

    `rayon` est en unités du modèle ; la route convertit les millimètres.
    """
    if not isinstance(rayon, (int, float)) or isinstance(rayon, bool) \
            or rayon != rayon or rayon <= 0:
        raise ValueError("rayon : un nombre fini > 0 est attendu")
    n = tuple(float(c) for c in normale)
    ln = math.sqrt(sum(c * c for c in n))
    if ln < 1e-12:
        raise ValueError("direction : la normale de perçage ne peut pas être nulle")
    n = tuple(c / ln for c in n)
    o = tuple(float(c) for c in point)
    u, v = _base_orthonormee(n)
    rayon = float(rayon)

    doc, binc = lire_glb(data)
    refus_compression(doc, "le perçage")
    nodes = _l(doc, "nodes")
    cible = None if noeuds is None else set(int(x) for x in noeuds)
    vises = [i for i in range(len(nodes))
             if (cible is None or i in cible) and "mesh" in nodes[i]]
    if not vises:
        raise ValueError("aucune pièce à percer dans la sélection")

    tampon, pieces = bytearray(binc), []
    for i in vises:
        mesh = _l(doc, "meshes")[nodes[i]["mesh"]]
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4 or "POSITION" not in (prim.get("attributes") or {}):
                continue
            pos = [tuple(p) for p in
                   _lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
            idx = ([t[0] for t in _lire_accesseur(doc, binc, prim["indices"])]
                   if "indices" in prim else list(range(len(pos))))
            tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]

            def radial(s):
                d = (pos[s][0] - o[0], pos[s][1] - o[1], pos[s][2] - o[2])
                du = d[0] * u[0] + d[1] * u[1] + d[2] * u[2]
                dv = d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
                return math.hypot(du, dv), math.atan2(dv, du)

            dedans = {s for s in range(len(pos)) if radial(s)[0] <= rayon}
            gardes = [t for t in tris if not all(s in dedans for s in t)]
            retires = len(tris) - len(gardes)
            if not retires:
                raise ValueError(
                    "aucun triangle sous le foret — le rayon est plus petit "
                    "qu'une facette. Augmente le rayon, ou décime moins.")
            boucles = _bords_ouverts(gardes)
            if len(boucles) != 2:
                raise ValueError(
                    f"{len(boucles)} bord(s) ouvert(s) après le foret, deux "
                    "peaux sont attendues (l'extérieure et l'intérieure). "
                    "Creuse d'abord, et vise une zone plane.")
            a, b = boucles
            # appariement par ANGLE autour de l'axe : deux boucles concentriques
            # n'ont ni le même nombre de sommets ni le même point de départ
            a = sorted(a, key=lambda s: radial(s)[1])
            b = sorted(b, key=lambda s: radial(s)[1])
            tube = []
            na, nb = len(a), len(b)
            for k in range(max(na, nb)):
                a0, a1 = a[k % na], a[(k + 1) % na]
                b0, b1 = b[k % nb], b[(k + 1) % nb]
                tube.append((a0, b0, a1))
                tube.append((a1, b0, b1))
            prim["indices"] = _ajouter_indices(doc, tampon, gardes + tube)
            pieces.append({"noeud": i,
                           "nom": nodes[i].get("name") or f"nœud {i}",
                           "retires": retires, "boucles": len(boucles),
                           "tube": len(tube), "rayon": rayon})
    if not pieces:
        raise ValueError("aucune pièce à percer dans la sélection")
    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, _ = _extraire_doc(doc, bytes(tampon), list(range(len(nodes))))
    return ecrire_glb(out, neuf), {
        "point": list(o), "normale": list(n), "rayon": rayon,
        "repere": "monde", "pieces": pieces}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k percer` → `2 passed, 1 failed` (la route manque).

- [ ] **Step 3 : `mesh_optimize.decimer_version` — gltfpack décime, `mesh_edit` écrit**

Dans `mesh_optimize.py`, à la suite d'`optimize_glb` :

```python
def decimer_version(job: str, version: int, target_tris=None,
                    preset: str | None = None) -> tuple[bytes, dict]:
    """Décime `model.v<version>.glb` et rend (octets, info) — SANS écrire dans
    le job.

    POURQUOI PAS `optimize_glb` : celle-là écrit `model.opt.glb`, un fichier À
    PART que `mesh_sources` marque `version: null` et que l'Établi refuse de
    charger (voir `ecrireVersion`). Une décimation demandée depuis l'Établi
    doit entrer dans la LIGNÉE : elle devient une version de plus, écrite par
    `mesh_edit.ecrire_version` comme toutes les autres. gltfpack reste l'outil
    qui décime — la doctrine dit que `mesh_edit` est la seule plume DU JOB,
    pas qu'aucun binaire tiers ne produit d'octets ; ici les octets passent par
    un dossier temporaire et rentrent par la porte commune.
    """
    import tempfile

    d = settings.outputs_path / "assets3d" / Path(job).name
    nom = "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"
    src = d / nom
    if not src.is_file():
        raise FileNotFoundError(f"{Path(job).name}/{nom} introuvable")
    exe = _gltfpack()
    target, preset = resolve_target(target_tris, preset)
    before = glb_stats(src)
    ratio = max(0.001, min(1.0, target / max(1, before["tris"])))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "decime.glb"

        def run(extra):
            r = subprocess.run(
                [exe, "-i", str(src), "-o", str(out),
                 "-si", f"{ratio:.6f}", "-noq"] + extra,
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0 or not out.is_file():
                raise RuntimeError(
                    f"gltfpack a échoué ({r.returncode}): "
                    f"{(r.stderr or r.stdout or '').strip()[:300]}")

        run([])
        after = glb_stats(out)
        aggressive = False
        if ratio < 1.0 and after["tris"] > target * 1.15:
            run(["-sa"])
            after = glb_stats(out)
            aggressive = True
        octets = out.read_bytes()
    return octets, {"before": before, "after": after, "target_tris": target,
                    "preset": preset, "ratio": round(ratio, 6),
                    "aggressive": aggressive,
                    "reduction_pct": round(
                        100.0 * (1 - after["tris"] / max(1, before["tris"])), 1)}
```

Test (dans `test_etabli_outils.py`) :

```python
def test_decimer_une_version_rend_des_octets_et_ne_touche_pas_au_job(monkeypatch, tmp_path):
    import shutil
    from app.services import mesh_optimize as MO
    if not shutil.which("gltfpack") and not pathlib.Path(
            os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\gltfpack.exe")).is_file():
        pytest.skip("gltfpack absent : la décimation ne peut pas être MESURÉE ici")
    from tests.test_mesh_optimize import build_torus_glb
    d = _job("job_dec", b"")
    build_torus_glb(d / "model.glb", 60, 60)
    octets, info = MO.decimer_version("job_dec", 1, target_tris=1000)
    assert octets[:4] == b"glTF" and info["after"]["tris"] < info["before"]["tris"]
    assert not (d / "model.opt.glb").exists()      # AUCUN fichier à part
    assert not (d / "optimize.json").exists()

def test_la_route_decimer_juge_son_corps_avant_de_lancer_gltfpack():
    _job("job_dec_rt", _cube()); c = _client()
    # preset inconnu : le refus vient de resolve_target, traduit en 400
    assert c.post("/api/etabli/decimer", json={"job": "job_dec_rt", "version": 1,
                                               "preset": "inconnu"}).status_code == 400
    # version non entière : refusée par la porte commune, AVANT tout disque
    assert c.post("/api/etabli/decimer", json={"job": "job_dec_rt",
                                               "version": "1"}).status_code == 400
    # nom de job dégénéré : la garde de chemin, comme les cinq autres routes
    assert c.post("/api/etabli/decimer", json={"job": "..",
                                               "version": 1}).status_code == 400
```

- [ ] **Step 4 : les deux routes**

```python
@router.post("/etabli/percer")
async def etabli_percer(body: dict):
    """Perce un trou de drainage : `point` et `normale` (monde), `rayon_mm` et
    `echelle`. Le point vient du clic sur la pièce (`selection.designerAuClic`
    rend déjà `touche.point` et `touche.normale`) ; c'est le même chemin que
    « poser sur une face »."""
    from app.services import hollow
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "perçage")
    point = _etabli_vecteur(body.get("point"), "perçage : point")
    normale = _etabli_vecteur(body.get("normale"), "perçage : normale",
                              direction=True)
    rayon_mm, echelle = body.get("rayon_mm"), body.get("echelle")
    if not _etabli_nombre(rayon_mm) or rayon_mm <= 0:
        raise HTTPException(400, "perçage : `rayon_mm` attend un nombre > 0")
    if not _etabli_nombre(echelle) or echelle <= 0:
        raise HTTPException(400, "perçage : `echelle` attend un nombre > 0")
    noeuds = body.get("noeuds")
    if noeuds is not None and (not isinstance(noeuds, list)
                               or any(not _etabli_entier(n) or n < 0 for n in noeuds)):
        raise HTTPException(400, "perçage : `noeuds` doit être une liste d'index")
    try:
        sortie, rapport = await asyncio.to_thread(
            hollow.percer, data, noeuds, point, normale,
            float(rayon_mm) / float(echelle))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "percer",
                          {"depuis": depuis, "rayon_mm": float(rayon_mm),
                           "echelle": float(echelle), **rapport})


@router.post("/etabli/decimer")
async def etabli_decimer(body: dict):
    """Décime une version et écrit la suivante — la décimation entre dans la
    LIGNÉE au lieu de vivre à part dans `model.opt.glb` (voir
    `mesh_optimize.decimer_version`)."""
    from app.services import mesh_optimize
    job, _data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                           "décimation")
    preset, cible = body.get("preset"), body.get("target_tris")
    try:
        octets, info = await asyncio.to_thread(
            mesh_optimize.decimer_version, job, int(body["version"]), cible, preset)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return _etabli_ecrire(job, octets, "decimer", {"depuis": depuis, **info})
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "percer or decimer"` → `5 passed` (un `skipped` si gltfpack manque).

- [ ] **Step 5 : la page — un mode de geste pour le foret, un bouton pour la décimation**

`ROUTES` gagne `percer: "/api/etabli/percer"` et `decimer: "/api/etabli/decimer"` ; `LIBELLES_ATTENTE` gagne
`percer: (t) => \`percer : ⌀ ${2 * t.charge.rayon_mm} mm\`` et `decimer: (t) => \`décimer vers ${t.charge.preset || t.charge.target_tris} triangles\``.

`MODES_GESTE` gagne `"foret"` (déclaré en tête, avec les quatre autres). Dans `armerGeste`, le mode sortant `"foret"` n'a rien à ranger (aucun objet posé dans la scène) ; dans le branchement de `designerAuClic` (là où `"assise"` est traité), avant la branche `assise` :

```js
    if (GESTE.mode === "foret") { percerAuClic(obj, touche); return; }
```

et :

```js
/* LE FORET. Un clic sur la peau extérieure, et Python perce le long de la
   normale de la face touchée — la MÊME normale monde que « poser sur une
   face » (matrice normale, jamais le quaternion : 24,2° d'écart mesuré sous
   échelle non uniforme). La normale de la face pointe DEHORS ; le foret
   s'enfonce donc dans son opposé, ce que la route reçoit tel quel. */
async function percerAuClic(objet, touche) {
  armerGeste("selection");
  if (!enMillimetres()) {
    direRefus("pose une taille cible : un trou de drainage se donne en millimètres");
    return;
  }
  const rayon = Number($("#fRayon").value);
  if (!(rayon > 0)) { direRefus("rayon : un nombre de millimètres > 0"); return; }
  const n = touche.normale, p = touche.point;
  const bilan = await ecrireSeule("percer", {
    point: [p.x, p.y, p.z], normale: [-n.x, -n.y, -n.z],
    rayon_mm: rayon, echelle: REP.echelle,
    noeuds: objet && objet.userData && objet.userData.indexGltf !== undefined
      ? [objet.userData.indexGltf] : undefined });
  if (!bilan) return;
  const q = bilan.derniere.source.pieces[0];
  direAvis(`percé (version ${bilan.derniere.version}) : ⌀ ${2 * rayon} mm, `
    + `${q.retires} triangle(s) retirés, tube de ${q.tube} triangle(s)`);
}
```

Dans `rendreFiche()`, sous le bloc « Creuser » :

```js
    <label>trou de drainage ⌀ <input id="fRayon" type="number" step="0.5" min="0.5" value="4"> mm</label>
    <button id="fForet">Percer (clic sur la pièce)</button>
    <div class="dt-label">Décimer</div>
    <label>cible <select id="fDecPreset">
      <option value="ultra">ultra — 100 000 triangles</option>
      <option value="high">élevé — 50 000</option>
      <option value="game">jeu — 10 000</option>
      <option value="detailed">détaillé — 5 000</option></select></label>
    <button id="fDecimer">Décimer</button>
    <p class="note">La décimation écrit une VERSION de plus — elle entre dans la
      lignée, au lieu du fichier « décimé » à part que l'Établi ne sait pas
      charger. Décime avant de creuser un maillage très lourd.</p>
```

avec, en branchements :

```js
  $("#fForet").addEventListener("click", () => {
    armerGeste(GESTE.mode === "foret" ? "selection" : "foret");
    majOutils();
    direAvis(GESTE.mode === "foret"
      ? "clique la face à percer — le foret suit sa normale"
      : "foret rangé");
  });
  $("#fDecimer").addEventListener("click", async () => {
    const preset = $("#fDecPreset").value;
    const bilan = await ecrireSeule("decimer", { preset });
    if (!bilan) return;
    const src = bilan.derniere.source;
    direAvis(`décimé (version ${bilan.derniere.version}) : `
      + `${src.before.tris} → ${src.after.tris} triangles `
      + `(−${src.reduction_pct} %)${src.aggressive ? ", passe agressive" : ""}`);
  });
```

Le `<select>` `#fDecPreset` n'invente aucun chiffre : ses trois valeurs sont les clés de `mesh_optimize.PRESETS`, et le banc l'épingle.

- [ ] **Step 6 : les miroirs**

```python
def test_le_foret_est_un_mode_de_geste_et_la_decimation_ecrit_une_version():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'const MODES_GESTE = ["selection", "glisser", "assise", "couteau", "foret"];' in js
    assert 'percer: "/api/etabli/percer"' in js and 'decimer: "/api/etabli/decimer"' in js
    f = _fonction_etabli("percerAuClic")
    assert 'armerGeste("selection")' in f and f.index("armerGeste") < f.index("ecrireSeule")
    assert "normale: [-n.x, -n.y, -n.z]" in f       # le foret s'enfonce, la face sort
    assert "echelle: REP.echelle" in f and f.index("enMillimetres()") < f.index("ecrireSeule")
    assert 'if (GESTE.mode === "foret") { percerAuClic(obj, touche); return; }' in code
    fiche = _fonction_etabli("rendreFiche")
    assert 'id="fRayon"' in fiche and 'id="fDecPreset"' in fiche and 'id="fDecimer"' in fiche
    for cle in ("percer", "decimer"):
        assert cle in _table_js("etabli/etabli.js", "LIBELLES_ATTENTE")

def test_chaque_option_de_decimation_est_une_CLE_du_service_et_dit_son_vrai_compte():
    """Le `<select>` ne recopie pas des chiffres : chaque `value` doit exister
    dans `mesh_optimize.PRESETS`, et le libellé doit porter le compte que le
    service applique VRAIMENT. Un preset renommé côté service rougirait ici au
    lieu d'envoyer une valeur que la route refuse en 400."""
    import re as _re
    from app.services import mesh_optimize
    fiche = _fonction_etabli("rendreFiche")
    bloc = fiche.split('id="fDecPreset"', 1)[1].split("</select>", 1)[0]
    options = _re.findall(r'<option value="([a-z]+)">([^<]+)</option>', bloc)
    assert len(options) == 4
    for cle, libelle in options:
        assert cle in mesh_optimize.PRESETS, cle
        chiffres = int(_re.sub(r"[^0-9]", "", libelle))
        assert chiffres == mesh_optimize.PRESETS[cle], (cle, chiffres)
```

Puis, dans `test_etabli_canevas.py`, l'assertion de `test_UN_SEUL_proprietaire_du_pointeur` qui cite `const MODES_GESTE = [` est alignée sur la ligne à cinq modes (grep `MODES_GESTE = \[` — une seule occurrence dans le banc, une seule dans la source).

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "foret or presets"` → `2 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k UN_SEUL_proprietaire` → `1 passed`.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/hollow.py backend/app/services/mesh_optimize.py backend/app/api/routes.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py backend/tests/test_etabli_canevas.py frontend/etabli/etabli.js
git commit -m 'etabli : percer le drainage et decimer dans la lignee' -m 'Le foret retire un disque sur chaque peau et coud le tube entre les deux bords appariés par angle ; zéro, une ou plus de deux boucles se DISENT au lieu de coudre à l aveugle. La décimation passe par gltfpack dans un dossier temporaire et rentre par mesh_edit.ecrire_version : une version de plus, pas un fichier à part que l Établi refuse de charger.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 8 : P5 — Measure : deux points, deux faces, dans le repère de T3

**Files :** créer `frontend/lib3d/mesure.js` ; modifier `frontend/etabli/etabli.js`, `frontend/etabli/index.html`, `frontend/etabli/etabli.css`, `backend/tests/test_etabli_canevas.py` (assertion `MODES_GESTE`) ; tests dans `test_etabli_outils_page.py`.

- [ ] **Step 1 : les tests EXÉCUTÉS dans node (rouge)**

Les deux règles sont PURES : elles s'exécutent, elles ne se relisent pas.

```python
def test_la_mesure_rend_une_distance_et_un_angle_de_faces_EXECUTES():
    src = _fonction_mesure("distance") + _fonction_mesure("angleDeFaces") + """
const d = distance({x:0,y:0,z:0},{x:3,y:4,z:0});
const plat = angleDeFaces({x:0,y:1,z:0},{x:0,y:1,z:0});
const droit = angleDeFaces({x:0,y:1,z:0},{x:1,y:0,z:0});
const rentrant = angleDeFaces({x:0,y:1,z:0},{x:0,y:-1,z:0});
const nul = angleDeFaces({x:0,y:0,z:0},{x:0,y:1,z:0});
console.log(JSON.stringify({d, plat, droit, rentrant, nul}));
"""
    r = json.loads(_node(src))
    assert r["d"] == 5
    assert r["plat"] == 180 and r["droit"] == 90 and r["rentrant"] == 0
    assert r["nul"] is None          # une normale nulle n'a pas d'angle

def test_la_mesure_projette_sur_les_axes_du_repere_EXECUTEE():
    src = _fonction_mesure("composantes") + """
console.log(JSON.stringify(composantes({x:1,y:2,z:3},{x:4,y:6,z:3})));
"""
    r = json.loads(_node(src))
    assert r == {"dx": 3, "dy": 4, "dz": 0, "norme": 5}
```

avec, dans le banc, l'extracteur jumeau des autres :

```python
def _fonction_mesure(nom: str) -> str:
    """Une fonction ENTIÈRE de lib3d/mesure.js, prête pour node — même patron
    que `_fonction_plaque` et `_fonction_viewer` du banc du canevas : extraite
    de la VRAIE source, jamais recopiée."""
    js = _lire("lib3d/mesure.js")
    m = re.search(r"^export function " + nom + r"\(", js, re.M)
    assert m, f"fonction {nom} introuvable dans mesure.js"
    j = js.index("\n}\n", m.start())
    return js[m.start():j + 2].replace("export function", "function", 1) + "\n"
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k mesure` → `2 failed` (`mesure.js` n'existe pas).

- [ ] **Step 2 : `frontend/lib3d/mesure.js` — trois règles pures, aucune dépendance à three.js**

```js
/* La MESURE — trois règles pures, dans lib3d/ parce qu'elles sont générales
   (spec §12 : ce qui est général va dans lib3d/, ce qui est propre à l'Établi
   reste dans etabli/). Aucune ne connaît three.js : elles prennent des
   {x, y, z} et rendent des nombres, ce qui les rend EXÉCUTABLES au banc dans
   node — la leçon de la plaque, où deux erreurs de suite sont passées parce
   qu'un miroir de texte lit une ligne mais ne voit pas une carte tomber. */

/* La distance entre deux points, dans l'unité du modèle. La page la convertit
   en millimètres par fmtMesure(), seul site qui sache s'il y a une échelle. */
export function distance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
}

/* Les composantes du segment sur les axes du repère, et sa norme. Ce que
   demande un préparateur : « combien en x, combien en z », pas seulement une
   diagonale. */
export function composantes(a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
  return { dx, dy, dz, norme: Math.hypot(dx, dy, dz) };
}

/* L'ANGLE ENTRE DEUX FACES, EN DEGRÉS — et c'est l'angle DIÈDRE de la matière,
   pas l'angle entre les normales. Deux faces coplanaires font 180° (une plaque
   plate), deux faces perpendiculaires 90°, deux faces qui se font face 0°
   (une arête rentrante infiniment fine). L'angle entre les NORMALES rendrait
   0° pour la plaque plate — le complément exact, et la moitié des gens le
   lisent à l'envers. On rend celui que l'on trace sur un plan.
   Une normale nulle n'a pas d'angle : `null`, jamais NaN — la page sait
   afficher « — », elle ne sait pas afficher NaN sans mentir. */
export function angleDeFaces(n1, n2) {
  const l1 = Math.hypot(n1.x, n1.y, n1.z), l2 = Math.hypot(n2.x, n2.y, n2.z);
  if (!(l1 > 0) || !(l2 > 0)) return null;
  const c = (n1.x * n2.x + n1.y * n2.y + n1.z * n2.z) / (l1 * l2);
  const borne = Math.max(-1, Math.min(1, c));
  return Math.round((180 - (Math.acos(borne) * 180) / Math.PI) * 1e6) / 1e6;
}
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k mesure` → `2 passed`.

- [ ] **Step 3 : le mode « mesure » dans la page**

`MODES_GESTE` devient `["selection", "glisser", "assise", "couteau", "foret", "mesure"]`. Dans `etabli.js`, à côté de `COUTEAU` :

```js
/* L'état de la MESURE — à côté de COUTEAU, et pour la même raison qu'à côté de
   S : c'est un état de geste, pas un état du modèle. `points` porte au plus
   deux touches ({point, normale, nom}) ; la troisième REMPLACE la série, plutôt
   que de faire deviner laquelle des trois compte. */
const MESURE = { points: [] };

function mesurerAuClic(objet, touche) {
  if (MESURE.points.length >= 2) MESURE.points.length = 0;
  MESURE.points.push({ p: touche.point.clone(), n: touche.normale.clone(),
                       nom: (objet && objet.name) || "sans nom" });
  marquerAuRepere(S.vueA, MESURE.points.map((m) => m.p));
  rendreMesure();
}

/* La lecture vit dans le rail du repère, SOUS la lecture x/y/z : c'est la même
   règle qui la gradue, et deux zones de cotes à deux endroits de l'écran se
   contrediraient à la première conversion. */
function rendreMesure() {
  const box = $("#repereMesure");
  if (!box) return;
  if (MESURE.points.length < 2) {
    box.textContent = MESURE.points.length
      ? "mesure : clique un second point"
      : "";
    return;
  }
  const [a, b] = MESURE.points;
  const c = composantes(a.p, b.p);
  const ang = angleDeFaces(a.n, b.n);
  box.innerHTML = `<b>mesure</b> ${esc(a.nom)} → ${esc(b.nom)}<br>
    d = ${fmtMesure(c.norme)} ${uniteCourante()}
    (x ${fmtMesure(c.dx)} · y ${fmtMesure(c.dy)} · z ${fmtMesure(c.dz)})<br>
    angle des faces : ${ang === null ? "—" : `${ang.toFixed(1)}°`}`;
}
```

Dans le branchement de `designerAuClic`, avant la branche `assise` :

```js
    if (GESTE.mode === "mesure") { mesurerAuClic(obj, touche); return; }
```

Dans `armerGeste`, quand le mode SORTANT est `"mesure"` : `MESURE.points.length = 0; marquerAuRepere(S.vueA, []); rendreMesure();` — le rangement du mode sortant, exactement comme `rangerCouteau()`.

Dans `index.html`, un bouton de plus dans `#vueOutils` (l'invariant auto-portant tient) :

```html
          <button class="outil-btn" id="btnMesure"></button>
```

`majOutils()` écrit son libellé (`Mesurer` / `Mesurer ✓` quand le mode est armé, `title` : « deux clics : distance, composantes x/y/z et angle des deux faces ») et le branchement bascule `armerGeste("mesure")`. `lireRepere()` appelle `rendreMesure()` en queue — la conversion en millimètres change quand la cible change, et la mesure affichée doit suivre. Dans `rendreRepere()`, le bloc statique gagne `<div class="repere-mesure" id="repereMesure"></div>` après `#repereLecture`, et `etabli.css` lui donne la même famille que `.repere-lecture` (`font-size: 11px; color: var(--dt-soft); margin-top: 6px;`).

Les imports de tête d'`etabli.js` gagnent `import { angleDeFaces, composantes } from "../lib3d/mesure.js";` — `distance` n'est PAS importée : `composantes` rend déjà la norme, et importer les deux ferait deux sources pour un même nombre.

- [ ] **Step 4 : le miroir de la page**

```python
def test_la_mesure_vit_dans_le_rail_du_repere_et_se_range_avec_son_mode():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert ('const MODES_GESTE = ["selection", "glisser", "assise", "couteau", '
            '"foret", "mesure"];') in js
    assert 'import { angleDeFaces, composantes } from "../lib3d/mesure.js";' in js
    assert "distance" not in js.split('from "../lib3d/mesure.js"', 1)[0].rsplit("import", 1)[1]
    assert 'if (GESTE.mode === "mesure") { mesurerAuClic(obj, touche); return; }' in code
    arme = _fonction_etabli("armerGeste")
    assert "MESURE.points.length = 0" in arme          # le mode sortant range
    assert 'id="repereMesure"' in _fonction_etabli("rendreRepere")
    assert "rendreMesure()" in _fonction_etabli("lireRepere")
    r = _fonction_etabli("rendreMesure")
    assert "fmtMesure(" in r and "uniteCourante()" in r and "esc(" in r
    assert "mm" not in _code("etabli/etabli.js").split("function rendreMesure", 1)[1].split("\n}\n", 1)[0]
    assert '<button class="outil-btn" id="btnMesure">' in _lire("etabli/index.html")
    assert ".repere-mesure" in _lire("etabli/etabli.css")
```

Puis, dans `test_etabli_canevas.py`, l'assertion sur la ligne littérale `const MODES_GESTE = [` est alignée sur les six modes (une seule occurrence, celle de la tâche 7 vient d'y passer).

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k mesure` → `3 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k "UN_SEUL_proprietaire or outils_vivent"` → verts.

- [ ] **Step 5 : commit**

```bash
git add frontend/lib3d/mesure.js frontend/etabli/etabli.js frontend/etabli/index.html frontend/etabli/etabli.css backend/tests/test_etabli_outils_page.py backend/tests/test_etabli_canevas.py
git commit -m 'etabli : Measure - distance, composantes et angle diedre des deux faces' -m 'Trois règles pures dans lib3d/mesure.js, EXÉCUTÉES au banc dans node ; l angle rendu est celui de la matière (180 degrés pour deux faces coplanaires), pas celui des normales, que la moitié des gens lit à l envers. La lecture vit dans le rail du repère, sous la lecture x/y/z, et passe par fmtMesure : aucun millimètre n est inventé.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 9 : P6 / T5 — extraire ensemble, ou une par une (un fichier par élément)

**Files :** modifier `backend/app/api/routes.py` (`etabli_extraire`), `frontend/etabli/etabli.js` (`separerSelection`, `LIBELLES_ATTENTE`, `ecrireVersion`), `frontend/etabli/etabli.css` ; tests dans les deux bancs neufs.

- [ ] **Step 1 : le test de route (rouge)**

```python
def test_extraire_une_par_une_ecrit_UN_FICHIER_PAR_ELEMENT_toutes_nees_du_MEME_parent():
    from app.services import mesh_edit
    d = _job("job_sep", _cube_et_sol()); c = _client()      # deux nœuds
    r = c.post("/api/etabli/extraire", json={"job": "job_sep", "version": 1,
                                             "noeuds": [0, 1], "separement": True})
    assert r.status_code == 200
    corps = r.json()
    assert [v["version"] for v in corps["versions"]] == [2, 3]
    assert corps["version"] == 3                              # la fiche rendue est la DERNIÈRE
    assert (d / "model.v2.glb").is_file() and (d / "model.v3.glb").is_file()
    for v, noeud in ((2, 0), (3, 1)):
        src = json.loads((d / "report.json").read_text("utf-8"))
        fiche = next(e for e in src["entries"] if e["file"] == f"model.v{v}.glb")["source"]
        # TOUTES nées du MÊME parent : des SŒURS, pas une chaîne
        assert fiche["depuis"] == {"version": 1, "fichier": "model.glb"}
        assert fiche["element"] == {"noeud": noeud, "rang": v - 2, "sur": 2}
        assert fiche["noeuds"] == [noeud]
    # chaque fichier ne contient QUE son élément
    doc2, _ = mesh_edit.lire_glb((d / "model.v2.glb").read_bytes())
    doc3, _ = mesh_edit.lire_glb((d / "model.v3.glb").read_bytes())
    assert len(doc2["nodes"]) == 1 and len(doc3["nodes"]) == 1

def test_extraire_ensemble_reste_ce_qu_elle_etait_et_separement_juge_son_corps():
    d = _job("job_sep2", _cube_et_sol()); c = _client()
    r = c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1,
                                             "noeuds": [0, 1]})
    assert r.status_code == 200 and r.json()["version"] == 2 and "versions" not in r.json()
    assert (d / "model.v2.glb").is_file() and not (d / "model.v3.glb").exists()
    assert c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1,
                                                "noeuds": [], "separement": True}
                  ).status_code == 400
    assert c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1,
                                                "noeuds": [0], "separement": "oui"}
                  ).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "une_par_une or ensemble_reste"` → `2 failed`.

- [ ] **Step 2 : la route**

`etabli_extraire` devient :

```python
@router.post("/etabli/extraire")
async def etabli_extraire(body: dict):
    """Extrait la sélection. `separement: true` écrit UNE VERSION PAR ÉLÉMENT
    au lieu d'un seul fichier qui les contient tous.

    LES N VERSIONS SONT DES SŒURS, PAS UNE CHAÎNE : chacune part des MÊMES
    octets — ceux de `version` — et sa fiche porte le même `depuis`. Chaîner
    les extractions l'une sur l'autre serait faux deux fois : la deuxième
    partirait d'un fichier qui ne contient plus que le premier élément, et
    `extraire` renumérote (voir `_carte`), si bien que les index d'après le
    premier tour ne désigneraient plus rien de ce que l'utilisateur a coché.
    La fiche RENDUE est la dernière — c'est elle que `ecrireVersion` chaîne,
    et c'est la version que la page ouvrira."""
    from app.services import mesh_edit
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "extraction")
    noeuds = body.get("noeuds")
    separement = body.get("separement", False)
    if not isinstance(separement, bool):
        raise HTTPException(400, "extraction : `separement` attend un booléen")
    if not separement:
        try:
            sortie = mesh_edit.extraire(data, noeuds or [])
        except ValueError as e:
            raise HTTPException(400, str(e))
        return _etabli_ecrire(job, sortie, "extraire",
                              {"depuis": depuis, "noeuds": list(noeuds or [])})
    if not isinstance(noeuds, list) or not noeuds:
        raise HTTPException(400, "extraction élément par élément : `noeuds` doit "
                                 "être une liste non vide d'index de nœud")
    fiches = []
    for rang, n in enumerate(noeuds):
        try:
            sortie = mesh_edit.extraire(data, [n])
        except ValueError as e:
            raise HTTPException(400, f"élément {n} : {e}")
        fiches.append(_etabli_ecrire(
            job, sortie, "extraire",
            {"depuis": depuis, "noeuds": [n],
             "element": {"noeud": n, "rang": rang, "sur": len(noeuds)}}))
    return {**fiches[-1], "versions": fiches}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "une_par_une or ensemble_reste"` → `2 passed`
Run : `python -m pytest tests/test_etabli_socle.py -q -k extra` → vert (la forme d'avant est intacte).

- [ ] **Step 3 : la page — la charge d'`extraire` devient un objet**

Dans `etabli.js` :

```js
/* Séparer : la sélection courante part comme nouvelle version. LA CHARGE EST
   UN OBJET depuis T5 : « ensemble » et « une par une » sont deux gestes que
   l'utilisateur choisit AVANT d'écrire, et une liste nue n'avait nulle part où
   porter ce choix. `LIBELLES_ATTENTE` et `ecrireVersion` lisent tous deux
   `charge.noeuds` — les trois sites changent ensemble. */
function separerSelection() {
  const { noeuds: idx, source } = noeudsRetenus();
  if (!idx.length) {
    direRefus("aucun nœud glTF dans la sélection — un matériau, ou une "
      + "primitive de maillage, n'a pas d'index à envoyer");
    return;
  }
  const separement = !!($("#pSeparement") && $("#pSeparement").checked);
  noterAttente("extraire", { noeuds: idx, separement }, source);
  direGeometrie();
}
```

`LIBELLES_ATTENTE.extraire` devient :

```js
  extraire: (t) => `${t.charge.noeuds.length} nœud(s) à séparer`
    + (t.charge.separement ? " — un fichier par élément" : ""),
```

et, dans `ecrireVersion`, la composition du corps :

```js
        const corps = t.operation === "transformer"
          ? { ...base, transforms: t.charge }
          : t.operation === "extraire"
            ? { ...base, noeuds: t.charge.noeuds, separement: t.charge.separement }
            : { ...base, ...t.charge };
```

Dans le panneau Parties, à côté de `#btnSeparer` (le balisage est écrit par `rendreParties()`) :

```js
      <label class="sep-mode" title="une version par élément, toutes nées de la version courante">
        <input type="checkbox" id="pSeparement"> une par une</label>
```

et `etabli.css` gagne `.sep-mode { font-size: 11px; color: var(--dt-soft); margin-left: 8px; }`.

- [ ] **Step 4 : les miroirs, et les deux assertions du banc d'avant**

Dans `test_etabli_outils_page.py` :

```python
def test_separer_porte_le_choix_une_par_une_et_les_TROIS_sites_lisent_la_meme_charge():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    sep = _fonction_etabli("separerSelection")
    assert 'noterAttente("extraire", { noeuds: idx, separement }, source)' in sep
    assert '$("#pSeparement")' in sep
    table = _table_js("etabli/etabli.js", "LIBELLES_ATTENTE")
    assert "t.charge.noeuds.length" in table and "t.charge.separement" in table
    assert ("noeuds: t.charge.noeuds, separement: t.charge.separement") in code
    # la charge n'est plus une liste NULLE PART : `t.charge.length` a disparu
    assert "t.charge.length" not in code
    assert 'id="pSeparement"' in _fonction_etabli("rendreParties")
    assert ".sep-mode" in _lire("etabli/etabli.css")
```

Puis, dans `test_etabli_canevas.py`, deux assertions à aligner (`grep -n 'extraire' backend/tests/test_etabli_canevas.py` les nomme) : celle qui cite `noterAttente("extraire", idx, source)` et celle qui compose le corps d'`extraire` dans le harnais node de `ecrireVersion` — les deux reçoivent la forme objet.

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k une_par_une` → `1 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k "extraire or DERNIER"` → verts.

- [ ] **Step 5 : commit**

```bash
git add backend/app/api/routes.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py backend/tests/test_etabli_canevas.py frontend/etabli/etabli.js frontend/etabli/etabli.css
git commit -m 'etabli : T5 - extraire ensemble ou une par une, un fichier par element' -m 'Les N versions sont des SŒURS nées des mêmes octets : chaîner les extractions serait faux deux fois, la seconde partirait d un fichier réduit et extraire renumérote. La charge de la file devient un objet, et les trois sites qui la lisent changent ensemble.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 10 : P6 / T6 — la Bibliothèque hiérarchique : la lignée côté route, le repli côté bundle

**Files :** modifier `backend/app/api/routes.py` (`_etabli_entree`, `_etabli_du_job`, `_etabli_productions`) ; créer `scripts/patch_bundle_lignee.py` ; tests dans `test_etabli_outils.py` et `test_etabli_outils_page.py`. **C'est le SEUL patch de bundle du plan.**

- [ ] **Step 1 : le test de route (rouge)**

```python
def test_les_productions_portent_leur_lignee_et_sortent_MERE_PUIS_FILLES():
    from app.services import mesh_edit
    d = _job("job_lign", _cube_et_sol())
    from app.services import mesh_report
    mesh_report.write_report("job_lign", "model.glb", version=1,
                             extra={"outil": "etabli", "operation": "adoption"})
    mesh_edit.ecrire_version("job_lign", _cube(), operation="reparer",
                             detail={"depuis": {"version": 1, "fichier": "model.glb"}})
    mesh_edit.ecrire_version("job_lign", _cube(), operation="couper",
                             detail={"depuis": {"version": 2, "fichier": "model.v2.glb"}})
    mesh_edit.ecrire_version("job_lign", _cube(), operation="extraire",
                             detail={"depuis": {"version": 1, "fichier": "model.glb"},
                                     "element": {"noeud": 0, "rang": 0, "sur": 2}})
    items = _client().get("/api/etabli/productions").json()["items"]
    lign = [z for z in items if z["job"] == "job_lign"]
    assert [z["version"] for z in lign] == [1, 2, 3, 4]        # mère d'abord, jamais l'ordre du temps
    assert [z["profondeur"] for z in lign] == [0, 1, 2, 1]
    assert [z["depuis_version"] for z in lign] == [None, 1, 2, 1]
    assert lign[0]["mere"] == 1 and lign[3]["mere"] == 1
    assert lign[3]["element"] == {"noeud": 0, "rang": 0, "sur": 2}

def test_une_lignee_cassee_ne_fait_pas_boucler_l_affichage():
    """`depuis` vient d'un report.json ouvert aux mains de l'utilisateur : deux
    versions qui se désignent l'une l'autre feraient tourner la remontée sans
    fin. La profondeur est BORNÉE par le nombre de versions du job."""
    from app.services import mesh_edit
    _job("job_boucle", _cube())
    from app.services import mesh_report
    mesh_report.write_report("job_boucle", "model.glb", version=1,
                             extra={"outil": "etabli", "operation": "adoption",
                                    "depuis": {"version": 2, "fichier": "model.v2.glb"}})
    mesh_edit.ecrire_version("job_boucle", _cube(), operation="reparer",
                             detail={"depuis": {"version": 1, "fichier": "model.glb"}})
    items = _client().get("/api/etabli/productions").json()["items"]
    b = [z for z in items if z["job"] == "job_boucle"]
    assert len(b) == 2 and all(isinstance(z["profondeur"], int) for z in b)
    assert max(z["profondeur"] for z in b) <= 2
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "lignee or boucle"` → `2 failed` (`KeyError: 'profondeur'`).

- [ ] **Step 2 : la lignée dans la route**

Dans `_etabli_entree`, trois champs de plus (juste après `"origine"`), et la signature prend la lignée :

```python
def _etabli_entree(ligne: dict, etape: dict, operation: str, d: Path,
                   lignee: dict | None = None) -> dict:
```

puis, dans le dictionnaire rendu :

```python
        "depuis_version": (lignee or {}).get("depuis"),
        "profondeur": (lignee or {}).get("profondeur", 0),
        "mere": (lignee or {}).get("mere", etape["version"]),
        "element": (lignee or {}).get("element"),
```

Dans `_etabli_du_job`, avant la boucle qui compose les entrées, une passe qui LIT `depuis` :

```python
    # LA LIGNÉE. `src["depuis"]` est écrit par toutes les routes d'écriture
    # depuis le lot B ; il donne le PARENT de chaque version. On en déduit une
    # profondeur (pour le repli de l'onglet) et une mère (la racine de la
    # branche). LA REMONTÉE EST BORNÉE par le nombre de versions : `depuis`
    # vient d'un report.json que la doctrine décrit comme ouvert aux mains de
    # l'utilisateur, et deux versions qui se désignent l'une l'autre feraient
    # tourner la boucle sans fin — un écran qui gèle plutôt qu'une ligne fausse.
    parent: dict[int, int | None] = {}
    for etape in ligne["etapes"]:
        v = etape["version"]
        if v is None:
            continue
        src = (fiches.get(etape["file"]) or {}).get("source")
        dep = (src or {}).get("depuis") if isinstance(src, dict) else None
        pv = dep.get("version") if isinstance(dep, dict) else None
        parent[v] = pv if isinstance(pv, int) and pv != v else None

    def _lignee(v: int) -> dict:
        profondeur, mere, garde = 0, v, len(parent) + 1
        while parent.get(mere) is not None and profondeur < garde:
            mere = parent[mere]
            profondeur += 1
        return {"depuis": parent.get(v), "profondeur": profondeur, "mere": mere}
```

et l'appel devient :

```python
        out.append(_etabli_entree(
            ligne, etape, str(src.get("operation") or "?"), d,
            {**_lignee(v), "element": src.get("element")}))
```

Enfin, `_etabli_productions` trie AUTREMENT — et c'est le cœur de T6 :

```python
    # T6 : LE TRI DEVIENT HIÉRARCHIQUE. Avant, les productions sortaient par
    # date décroissante, toutes versions mêlées : la v4 d'un job voisinait la
    # v1 d'un autre, et la lignée était invisible. Ici les jobs restent classés
    # par leur production la PLUS RÉCENTE (ce que la personne cherche est son
    # dernier dossier), mais À L'INTÉRIEUR d'un job l'ordre est celui de la
    # LIGNÉE : la mère, puis ses filles par numéro croissant. L'onglet n'a plus
    # qu'à décaler selon `profondeur`.
    par_job: dict[str, list[dict]] = {}
    for e in out:
        par_job.setdefault(e["job"], []).append(e)
    jobs = sorted(par_job, key=lambda j: max(
        (e["created_at"] or "") for e in par_job[j]), reverse=True)
    ordonne: list[dict] = []
    for j in jobs:
        ordonne.extend(sorted(par_job[j], key=lambda e: (e["mere"], e["version"])))
    return ordonne
```

(La ligne `out.sort(...)` précédente disparaît ; son commentaire sur l'ordre lexical des ISO reste utile et migre au-dessus de `jobs = sorted(...)`.)

Run : `python -m pytest tests/test_etabli_outils.py -q -k "lignee or boucle"` → `2 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k productions` → vert (la forme des entrées n'a fait que s'enrichir).

- [ ] **Step 3 : le patcher de bundle — tag NEUF `lignee`, EN QUEUE**

`scripts/patch_bundle_lignee.py` (patron mot pour mot de `patch_bundle_etabli.py` : `deltas`, `check_spec_parity`, `guard_downstream`, `ensure_tail_order`, `apply`, `read_src`, `eol_stats`, `resolve_root`, `main` — recopiés tels quels ; seules les constantes ci-dessous changent) :

```python
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "lignee"
MARKER = "__dzLignee"
MARKER_ATTENDU = 2      # la definition + l'appel

STABLE_PROBES = [
    ("etabli", "__dzEtabli", 2),
    ("etabli-onglet", "Établi", 2),
    ("libprov", "__dzSrcChips", 2),
    ("libsend", "__dzSendTo", 2),
    ("rangee-onglets", "Object.keys(vo)", 1),
]

POST_COUNTS = [
    ("__dzLignee", 2),
    ("Établi", 2),          # AUCUN litteral ajoute : le compte d'etabli tient
    ("__dzEtabli", 2),
    ("q=__dzLignee(Lfs(", 1),
    ("Object.keys(vo)", 1),
]

SPEC_CHAR_DELTA = 458
SPEC_BYTE_DELTA = 460

# ── L1 : la seule greffe de code, un replieur de liste ───────────────────────
# IL NE NOMME PAS L'ONGLET, et c'est la decision : ecrire "Etabli" ici
# ajouterait un troisieme exemplaire du litteral et casserait le POST_COUNT de
# patch_bundle_etabli.py, qui en attend DEUX. Le replieur reconnait donc sa
# liste a ce qu'elle PORTE : `profondeur`, un champ que seule la route
# /api/etabli/productions ecrit. Toute autre categorie ressort inchangee.
HELPER = (
    "function __dzLignee(L){try{"
    "if(!L||!L.length)return L;"
    "for(var i=0;i<L.length;i++)if(!L[i]||typeof L[i].profondeur!==\"number\")return L;"
    "var g={},o=[];"
    "L.forEach(function(z){var j=String(z.job||\"\");"
    "if(!g[j]){g[j]=[];o.push(j)}g[j].push(z)});"
    "var r=[];o.forEach(function(j){g[j].forEach(function(z){"
    "var p=z.profondeur>3?3:z.profondeur;"
    "r.push(p?Object.assign({},z,{name:new Array(p+1).join(\"↳ \")"
    "+String(z.name||\"\")}):z)})});"
    "return r}catch(e){return L}}"
)

_L1 = "function __dzEtabli(cb){"
_L2 = "q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]))"

PATCHES = [
    ("L1-replieur", _L1, HELPER + _L1),
    ("L2-branchement", _L2, "q=__dzLignee(" + _L2 + ")"),
]
```

**Le repli est un DÉCALAGE DU NOM, pas une carte neuve** : la carte de l'onglet 3D existe déjà (c'est tout l'argument de `patch_bundle_etabli.py`), et lui ajouter une colonne d'arborescence demanderait du balisage, de la CSS et un composant. Un `↳` par génération, borné à trois, dit la même chose pour deux greffes — et la ROUTE, elle, porte la lignée complète pour qui voudra la dessiner un jour.

- [ ] **Step 4 : appliquer et vérifier**

Run : `python scripts/patch_bundle_lignee.py --deltas`
Expected : `[lignee] delta +458 car / +460 o`
Run : `python scripts/patch_bundle_lignee.py --check`
Expected : `[lignee] applicable sur …index-BEOJX8L5.js`, `2 ancres OK, marqueur absent, 5 sondes aux comptes`, `CRLF=… LF-isole=0 CR-isole=0`
Run : `python scripts/patch_bundle_lignee.py`
Expected : `backup -> index-BEOJX8L5.js.bak_lignee`, `OK - bundle patche`, `taille : 1395299 -> 1395759 o (+460)`
Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp_check.mjs && node --check /tmp_check.mjs && rm /tmp_check.mjs` (depuis la racine ; sous PowerShell : `Copy-Item frontend\dist\assets\index-BEOJX8L5.js $env:TEMP\c.mjs; node --check $env:TEMP\c.mjs; Remove-Item $env:TEMP\c.mjs`)
Expected : aucune sortie (le fichier est du JS valide)
Run : `python scripts/repatch_all.py --list`
Expected : la chaîne se termine par `lignee OK (bak …)` — le maillon neuf est bien EN QUEUE.

- [ ] **Step 5 : le miroir du patcher et du bundle**

```python
def test_le_patcher_lignee_est_en_queue_de_chaine_et_n_ajoute_aucun_Etabli():
    src = (RACINE / "scripts" / "patch_bundle_lignee.py").read_text("utf-8")
    assert 'TAG = "lignee"' in src and 'MARKER = "__dzLignee"' in src
    assert "guard_downstream" in src and "ensure_tail_order" in src
    assert 'SPEC_CHAR_DELTA = 458' in src and 'SPEC_BYTE_DELTA = 460' in src
    # le litteral de l'onglet ne bouge pas : c'est l'invariant qui garde
    # patch_bundle_etabli.py rejouable
    assert '("\\u00c9tabli", 2)' in src
    assert "Établi" not in src.split("HELPER = (", 1)[1].split(")\n", 1)[0]

def test_le_bundle_deploye_porte_le_replieur_et_le_branche_une_fois():
    b = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(
        "utf-8", newline="")
    assert b.count("__dzLignee") == 2
    assert b.count("q=__dzLignee(Lfs(") == 1
    assert b.count("Établi") == 2 and b.count("__dzEtabli") == 2
    assert b.count("Object.keys(vo)") == 1

def test_le_replieur_regroupe_par_job_et_laisse_les_autres_categories_INTACTES():
    """EXÉCUTÉ dans node, sur le texte du BUNDLE — pas sur une recopie."""
    b = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(
        "utf-8", newline="")
    i = b.index("function __dzLignee(L){")
    src = b[i:b.index("function __dzEtabli(cb){")] + """
const etabli = [
  {job:"a", version:3, profondeur:2, name:"a v3"},
  {job:"b", version:1, profondeur:0, name:"b v1"},
  {job:"a", version:1, profondeur:0, name:"a v1"},
];
const images = [{name:"img.png"}, {name:"autre.png"}];
console.log(JSON.stringify({
  etabli: __dzLignee(etabli).map((z) => z.name),
  images: __dzLignee(images).map((z) => z.name),
  vide: __dzLignee([]).length,
}));
"""
    r = json.loads(_node(src))
    # MESURÉ dans node le 03/09 : les deux entrées du job « a » se suivent (le
    # replieur REGROUPE), l'ordre interne est celui que la route a posé, et une
    # profondeur de 2 met deux chevrons devant le nom.
    assert r["etabli"] == ["↳ ↳ a v3", "a v1", "b v1"]
    assert r["images"] == ["img.png", "autre.png"]      # aucune profondeur : INTACT
    assert r["vide"] == 0
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "lignee or replieur or bundle_deploye"` → `3 passed`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/api/routes.py scripts/patch_bundle_lignee.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py
git commit -m 'etabli : T6 - la lignee dans la route, le repli dans l onglet Bibliotheque' -m 'La route classe les jobs par leur production la plus récente et, DANS un job, par la lignée (mère puis filles) ; profondeur, mère et depuis_version sont portés par chaque entrée, la remontée est bornée par le nombre de versions parce que report.json est ouvert aux mains de l utilisateur. Le patcher lignee est le seul patch de bundle du plan : deux greffes, aucun littéral Établi ajouté, en queue de chaîne, rejouable par repatch_all --from lignee.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 11 : P6 — la lecture chiffrée de la pièce que l'on glisse

**Files :** modifier `frontend/etabli/etabli.js` (`lirePieceCourante`, `glisserSurPlaque`, `toucheClavierPlaque`, `pieceCourante`, `rendreParties`, `lireRepere`), `frontend/etabli/etabli.css` ; tests dans `test_etabli_outils_page.py`.

- [ ] **Step 1 : le test EXÉCUTÉ (rouge)**

La règle qui compose la ligne est pure ; seul l'écrit dans le DOM ne l'est pas. On sépare donc les deux, et c'est ce qui rend la mesure possible.

```python
def test_la_lecture_du_glisser_est_relative_au_COIN_du_plateau_EXECUTEE():
    """La cote qu'un préparateur lit sur un plateau part du COIN du plateau, pas
    de l'origine du monde : c'est le zéro des règles (voir geometriePlateau).
    Une lecture en coordonnées monde afficherait −31,50 pour une pièce posée au
    bord, et le plan de plaque, lui, est écrit en monde — deux nombres pour un
    seul geste."""
    src = (_constantes_etabli("LIGNES_REPERE") + """
      const REP = { echelle: 10, cibleMm: 100, pas: null };
      const uniteCourante = () => "mm";
      const fmtMesure = (v) => (v * REP.echelle).toFixed(2);
      const PLQ = { courante: 7, pieces: [{ cle: 7, nom: "cadre" }] };
      const S = { vueA: {} };
      const plateauDe = () => ({ u: "x", v: "z", axe: "y", coin: { x: -5, z: -5 } });
      const empreinteDe = () => ({ u: -3, v: -1, l: 2, p: 4 });
      const rotationDe = () => 90;
      const box = { textContent: "" };
      const $ = () => box;
    """ + _fonction_etabli("nomDePiece") + _fonction_etabli("lirePieceCourante") + """
      lirePieceCourante();
      console.log(JSON.stringify({ txt: box.textContent }));
    """)
    r = json.loads(_node(src))
    # coin relatif : (−3 − (−5)) = 2 u → 20,00 mm ; (−1 − (−5)) = 4 u → 40,00 mm
    assert "cadre" in r["txt"] and "20.00 ; 40.00" in r["txt"]
    assert "20.00 × 40.00 mm" in r["txt"] and "90°" in r["txt"]

def test_la_lecture_du_glisser_ne_redessine_PAS_le_rail_a_chaque_image():
    """Le prix est mesuré et il est dans le fichier : lireRepere() coûte
    2,057 ms à douze sélections HORS navigateur — 12 % d'une trame à 60 Hz — et
    le navigateur y ajoute une analyse de balisage. Un `pointermove` ne peut
    donc pas l'appeler ; il écrit un textContent sur UNE pièce."""
    f = _fonction_etabli("lirePieceCourante")
    assert "textContent" in f and "innerHTML" not in f
    assert "lireRepere" not in f and "rendreParties" not in f
    glisse = _fonction_etabli("glisserSurPlaque")
    assert "lirePieceCourante()" in glisse and "lireRepere()" not in glisse
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k glisser` → `2 failed`.

- [ ] **Step 2 : les deux fonctions**

Dans `etabli.js`, à côté de `rendreRotation()` :

```js
/* Le NOM d'une pièce de la plaque. `PLQ.pieces` porte {cle, nom, couleur,
   uuid} : le nom vient d'`etaler()`, jamais du graphe three.js — sur la plaque
   la pièce vit dans un berceau, et remonter au maillage donnerait le nom du
   maillage, pas celui de la pièce. */
function nomDePiece(cle) {
  const p = PLQ.pieces.find((x) => x.cle === cle);
  return (p && p.nom) || `pièce ${cle}`;
}

/* LA LECTURE CHIFFRÉE DE LA PIÈCE COURANTE — la dette nommée du lot B (« la
   lecture chiffrée de la pièce que l'on glisse n'a pas été demandée deux
   fois »). Elle l'est maintenant.

   RELATIVE AU COIN DU PLATEAU, et c'est la décision : le zéro des règles est
   ce coin (geometriePlateau), et c'est là que le préparateur lit ses cotes. Le
   plan de plaque, lui, reste écrit en coordonnées MONDE — deux repères, un
   seul écrit sur le disque, et le commentaire du plan le dit déjà.

   BORNÉE À UNE PIÈCE, et c'est le prix qui l'exige : `lireRepere()` coûte
   2,057 ms à douze sélections hors navigateur (12 % d'une trame à 60 Hz), et
   un glissement l'appellerait à chaque `pointermove`. Ici : un textContent,
   aucune analyse de balisage, aucune remise en page du rail. */
function lirePieceCourante() {
  const box = $("#plaqueLecture");
  if (!box) return;
  const cle = PLQ.courante;
  const g = cle === null ? null : plateauDe(S.vueA);
  const emp = g ? empreinteDe(S.vueA, cle) : null;
  if (!emp) { box.textContent = ""; return; }
  const u = emp.u - g.coin[g.u];
  const v = emp.v - g.coin[g.v];
  box.textContent = `${nomDePiece(cle)} · coin ${fmtMesure(u)} ; ${fmtMesure(v)}`
    + ` · ${fmtMesure(emp.l)} × ${fmtMesure(emp.p)} ${uniteCourante()}`
    + ` · ${Number(rotationDe(S.vueA, cle) || 0).toFixed(0)}°`;
}
```

Les cinq sites d'appel :
1. `glisserSurPlaque`, dans `pointermove`, juste après `rendreRotation();` ;
2. `toucheClavierPlaque`, après `marquerPiece(S.vueA, PLQ.courante);` ;
3. `pieceCourante(cle)`, en queue (le clic change de pièce) ;
4. `graduerPlateau()`, en queue (l'entrée et la sortie de la plaque) ;
5. `lireRepere()`, en queue — poser une taille cible change l'UNITÉ, et une lecture qui resterait en unités glTF sous un rail en millimètres serait fausse à l'écran.

Le bloc d'accueil est écrit par `rendreParties()`, dans `.plaque-tete`, après le compte de pièces :

```js
    <div class="plaque-lecture" id="plaqueLecture"></div>
```

et `etabli.css` gagne :

```css
.plaque-lecture { font-size: 11px; color: var(--dt-soft); margin: 4px 0 6px;
                  font-variant-numeric: tabular-nums; min-height: 13px; }
```

`min-height` n'est pas décoratif : la ligne naît vide et se remplit au premier clic ; sans hauteur réservée, la liste des pièces sauterait d'un cran sous le pointeur au moment même où l'on vise une rangée. `tabular-nums` fige la largeur des chiffres — sans quoi la cote danse pendant le glissement.

- [ ] **Step 3 : vert**

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k glisser` → `2 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k "plaque or Parties"` → verts.

- [ ] **Step 4 : commit**

```bash
git add frontend/etabli/etabli.js frontend/etabli/etabli.css backend/tests/test_etabli_outils_page.py
git commit -m 'etabli : la lecture chiffree de la piece que l on glisse' -m 'Coin, cotes et angle relus dans le repère du PLATEAU — le zéro des règles —, pas en coordonnées monde comme le plan de plaque. Bornée à une pièce et écrite en textContent : lireRepere coûte 2,057 ms à douze sélections, un pointermove ne peut pas le payer.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 12 : P6 — la dette des DEUX lecteurs d'accesseurs : un seul, qui APPLIQUE `sparse`

**Files :** modifier `backend/app/services/mesh_edit.py` (`lire_accesseur`, neuve), `mesh_cut.py`, `print3d.py`, `mesh_repair.py`, `hollow.py` ; tests dans `test_etabli_outils.py`.

> Dette nommée dans `2026-09-01-etabli-plaque-et-extraction.md` : « deux lecteurs d'accesseurs (`print3d` ignore `sparse` en silence, `mesh_cut` le refuse) à unifier dans le lot qui touchera `print3d` ». La tâche 4 a touché `print3d` ; le lot est celui-ci.

- [ ] **Step 1 : le test qui montre le mensonge (rouge)**

```python
def _cube_sparse() -> bytes:
    """Le cube du dépôt, dont UN sommet est déplacé par un accesseur `sparse`.

    glTF 2.0 §3.6.2.3 : `sparse` remplace `count` valeurs de l'accesseur de
    base, désignées par des index. Un lecteur qui l'ignore rend la géométrie
    d'AVANT la substitution — ici, une boîte de côté 2 au lieu de 4."""
    import struct as _s
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    acc = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    off_i = len(tampon); tampon += _s.pack("<H", 0)
    while len(tampon) % 4:
        tampon.append(0)
    off_v = len(tampon); tampon += _s.pack("<3f", -3.0, -3.0, -3.0)
    n = len(doc["bufferViews"])
    doc["bufferViews"] += [{"buffer": 0, "byteOffset": off_i, "byteLength": 2},
                           {"buffer": 0, "byteOffset": off_v, "byteLength": 12}]
    acc["sparse"] = {"count": 1,
                     "indices": {"bufferView": n, "byteOffset": 0, "componentType": 5123},
                     "values": {"bufferView": n + 1, "byteOffset": 0}}
    acc["min"] = [-3.0, -3.0, -3.0]
    doc["buffers"] = [{"byteLength": len(tampon)}]
    return mesh_edit.ecrire_glb(doc, bytes(tampon))

def test_UN_SEUL_lecteur_et_il_APPLIQUE_sparse_pour_les_deux_appelants():
    from app.services import mesh_cut, mesh_edit, print3d
    data = _cube_sparse()
    doc, binc = mesh_edit.lire_glb(data)
    i = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    pos = mesh_edit.lire_accesseur(doc, binc, i)
    assert pos[0] == (-3.0, -3.0, -3.0)              # la substitution est APPLIQUÉE
    assert sum(1 for p in pos if p == (-3.0, -3.0, -3.0)) == 1
    # les deux anciens lecteurs délèguent : même réponse, plus de refus, plus
    # de silence
    assert mesh_cut._lire_accesseur(doc, binc, i)[0] == (-3.0, -3.0, -3.0)
    assert print3d._accessor(doc, binc, i)[0] == (-3.0, -3.0, -3.0)
    b = print3d.bbox(print3d.lire_glb_triangles(data))
    assert abs(b[0][0] - (-3.0)) < 1e-6              # le lecteur de print3d aussi

def test_le_lecteur_unique_garde_les_PERIMETRES_de_chaque_appelant():
    """`print3d` ne sait écrire que float32 / u16 / u32 ; `mesh_cut` lit tous
    les composants de glTF. Unifier ne doit pas ÉLARGIR print3d en douce : le
    périmètre reste un argument de l'appelant, et le refus garde son mot."""
    import pytest as _p
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    i = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    doc["accessors"][i]["componentType"] = 5121      # u8 : hors périmètre print3d
    with _p.raises(ValueError, match="hors périmètre"):
        print3d._accessor(doc, binc, i)
    # le lecteur générique, lui, sait le lire
    assert len(mesh_edit.lire_accesseur(doc, binc, i)) > 0

def test_un_accesseur_sans_bufferView_part_de_ZERO_comme_le_dit_glTF():
    """glTF 2.0 : quand `bufferView` est absent, les valeurs de base sont
    NULLES et `sparse` les remplace. `mesh_cut` le refusait ; il ne le refuse
    plus, il l'applique."""
    from app.services import mesh_edit
    import struct as _s
    doc, binc = mesh_edit.lire_glb(_cube())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    oi = len(tampon); tampon += _s.pack("<H", 1)
    while len(tampon) % 4:
        tampon.append(0)
    ov = len(tampon); tampon += _s.pack("<3f", 7.0, 8.0, 9.0)
    n = len(doc["bufferViews"])
    doc["bufferViews"] += [{"buffer": 0, "byteOffset": oi, "byteLength": 2},
                           {"buffer": 0, "byteOffset": ov, "byteLength": 12}]
    doc["accessors"].append({"componentType": 5126, "type": "VEC3", "count": 3,
                             "sparse": {"count": 1,
                                        "indices": {"bufferView": n, "byteOffset": 0,
                                                    "componentType": 5123},
                                        "values": {"bufferView": n + 1, "byteOffset": 0}}})
    doc["buffers"] = [{"byteLength": len(tampon)}]
    vals = mesh_edit.lire_accesseur(doc, bytes(tampon), len(doc["accessors"]) - 1)
    assert vals == [(0.0, 0.0, 0.0), (7.0, 8.0, 9.0), (0.0, 0.0, 0.0)]
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "lecteur or sparse"` → `4 failed` (`AttributeError: module 'app.services.mesh_edit' has no attribute 'lire_accesseur'`, et les refus d'aujourd'hui).

- [ ] **Step 2 : le lecteur, dans `mesh_edit` — la maison du socle**

Dans `mesh_edit.py`, après `ecrire_glb` :

```python
_COMPOSANTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
               5125: ("I", 4), 5126: ("f", 4)}
_NB_COMPOSANTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                  "MAT2": 4, "MAT3": 9, "MAT4": 16}


def lire_accesseur(doc: dict, binc: bytes, i: int, *,
                   composants=None, quoi: str = "la lecture") -> list[tuple]:
    """UN SEUL LECTEUR D'ACCESSEUR pour tout le dépôt, et il APPLIQUE `sparse`.

    Il y en avait DEUX, et ils se contredisaient : `print3d._accessor` ignorait
    `sparse` EN SILENCE — il rendait donc la géométrie d'avant la substitution,
    un STL faux et imprimé sans que rien ne grince — tandis que
    `mesh_cut._lire_accesseur` le REFUSAIT. Un même fichier passait chez l'un
    et rebondissait chez l'autre. Ici il est lu comme glTF 2.0 le décrit
    (§3.6.2.3) : des valeurs de base (nulles quand `bufferView` est absent),
    puis `count` substitutions désignées par des index.

    `composants` GARDE LE PÉRIMÈTRE DE L'APPELANT : `print3d` n'écrit que
    float32 / u16 / u32 et doit continuer de refuser le reste avec son propre
    mot ; le couteau lit tout. Unifier le code ne veut pas dire élargir les
    promesses.
    """
    a = _l(doc, "accessors")[i]
    ty = a["type"]
    ct = a["componentType"]
    permis = _COMPOSANTS if composants is None else {
        c: _COMPOSANTS[c] for c in composants}
    if ct not in permis or ty not in _NB_COMPOSANTS:
        raise ValueError(f"accesseur {i} : composant {ct} / type {ty} hors "
                         f"périmètre de {quoi}")
    fmt, taille = _COMPOSANTS[ct]
    n = _NB_COMPOSANTS[ty]
    count = int(a["count"])
    serre = taille * n

    def _vue(bv_index: int, octets_offset: int, combien: int, f: str, pas: int):
        bv = _l(doc, "bufferViews")[bv_index]
        if "uri" in _l(doc, "buffers")[bv.get("buffer", 0)]:
            raise ValueError("buffer externe (uri) — nos GLB sont "
                             "monolithiques, hors périmètre")
        base = bv.get("byteOffset", 0) + octets_offset
        return [struct.unpack_from(f, binc, base + k * pas)
                for k in range(combien)]

    if a.get("bufferView") is None:
        # glTF : sans bufferView, les valeurs de base sont NULLES
        out = [tuple([0] * n) for _ in range(count)]
    else:
        bv = _l(doc, "bufferViews")[a["bufferView"]]
        pas = bv.get("byteStride") or serre
        out = _vue(a["bufferView"], a.get("byteOffset", 0), count,
                   "<" + fmt * n, pas)

    sp = a.get("sparse")
    if sp:
        nb = int(sp["count"])
        ic = sp["indices"]["componentType"]
        if ic not in _COMPOSANTS:
            raise ValueError(f"accesseur {i} : composant d'index sparse {ic} "
                             "hors périmètre")
        ifmt, itaille = _COMPOSANTS[ic]
        idx = _vue(sp["indices"]["bufferView"],
                   sp["indices"].get("byteOffset", 0), nb, "<" + ifmt, itaille)
        vals = _vue(sp["values"]["bufferView"],
                    sp["values"].get("byteOffset", 0), nb, "<" + fmt * n, serre)
        for (k,), v in zip(idx, vals):
            if 0 <= k < count:
                out[k] = v
    return out
```

(`import struct` est déjà en tête de `mesh_edit.py` ; le vérifier d'un `grep -n '^import struct' backend/app/services/mesh_edit.py` — attendu : une ligne.)

- [ ] **Step 3 : les deux anciens lecteurs DÉLÈGUENT**

Dans `mesh_cut.py`, `_lire_accesseur` devient trois lignes, et les deux tables `_COMPOSANTS` / `_NB_COMPOSANTS` du module disparaissent (elles vivent maintenant dans `mesh_edit`) :

```python
def _lire_accesseur(doc: dict, binc: bytes, i: int) -> list[tuple]:
    """Le lecteur du socle, sans restriction de composant — le couteau lit tout
    ce que glTF sait écrire. `sparse` n'est plus refusé : il est APPLIQUÉ (voir
    `mesh_edit.lire_accesseur`)."""
    from app.services.mesh_edit import lire_accesseur
    return lire_accesseur(doc, binc, i, quoi="le couteau")
```

Dans `print3d.py` :

```python
def _accessor(doc, binc, i):
    """Le lecteur du socle, BORNÉ au périmètre que print3d sait écrire :
    float32, u16, u32. `sparse` était ignoré en silence ici — un STL faux,
    imprimé — et il est désormais appliqué."""
    from app.services.mesh_edit import lire_accesseur
    return lire_accesseur(doc, binc, i, composants=tuple(_FMT),
                          quoi="l'export d'impression")
```

`_TAILLE_COMPOSANT` et `_NB_COMPOSANTS` de `print3d.py` ne servent plus qu'ici : les supprimer, `_FMT` reste (il nomme le périmètre et sert aussi à l'écriture).

Dans `mesh_repair.py` et `hollow.py`, l'import `from app.services.mesh_cut import (…, _lire_accesseur, …)` devient `from app.services.mesh_edit import lire_accesseur` et les appels perdent leur tiret bas — un module de service n'importe pas un nom privé d'un autre quand le socle en offre un public.

Run : `python -m pytest tests/test_etabli_outils.py -q -k "lecteur or sparse"` → `4 passed`
Run : `python -m pytest tests/test_etabli_socle.py -q` → vert
Run : `python -m pytest tests/test_print3d.py -q` → vert
Run : `python -m pytest tests/test_mesh_report.py -q` → vert

- [ ] **Step 4 : et la dette est CLOSE, par un banc qui interdit la rechute**

```python
def test_il_n_y_a_plus_qu_UN_lecteur_d_accesseur_dans_le_depot():
    """La dette se referme par une assertion, pas par une intention : deux
    `struct.unpack_from` sur un `bufferView` dans deux modules, et le silence
    revient au premier fichier `sparse`."""
    import pathlib
    services = pathlib.Path(__file__).resolve().parent.parent / "app" / "services"
    porteurs = [p.name for p in services.glob("*.py")
                if "byteStride" in p.read_text("utf-8")]
    assert porteurs == ["mesh_edit.py"], porteurs
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k UN_lecteur` → `1 passed`.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/app/services/mesh_cut.py backend/app/services/print3d.py backend/app/services/mesh_repair.py backend/app/services/hollow.py backend/tests/test_etabli_outils.py
git commit -m 'socle : un seul lecteur d accesseur, et il applique sparse' -m 'Dette nommée du lot B refermée. print3d ignorait sparse EN SILENCE — un STL faux, imprimé — et mesh_cut le refusait : le même fichier passait chez l un et rebondissait chez l autre. Le lecteur unique vit dans mesh_edit, applique la substitution comme glTF la décrit, et garde le périmètre de composants de chaque appelant. Un banc interdit la rechute : un seul module du dépôt lit un byteStride.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 13 : P6 — la contradiction assise / recentrer, DITE et refusée

**Files :** modifier `frontend/etabli/etabli.js` (`contradictionDeLaFile`, `rendreAttente`, `ecrireVersion`), `frontend/etabli/etabli.css` ; tests dans `test_etabli_outils_page.py`.

> Dette nommée du lot B : « `assise` + `reparer (recentrer)` dans la même file se contredisent par définition, la barre ne le dit pas ».

- [ ] **Step 1 : le test EXÉCUTÉ (rouge)**

```python
def test_assise_et_recentrer_dans_la_MEME_file_sont_refuses_en_le_disant():
    src = (_constantes_etabli("ORDRE_ECRITURE") + """
      const S = { enAttente: [] };
    """ + _fonction_etabli("contradictionDeLaFile") + """
      const cas = [];
      const poser = (l) => { S.enAttente = l; return contradictionDeLaFile(); };
      cas.push(poser([{ operation: "assise", charge: {} }]));
      cas.push(poser([{ operation: "reparer", charge: { recentrer: false } }]));
      cas.push(poser([{ operation: "assise", charge: {} },
                      { operation: "reparer", charge: { recentrer: false } }]));
      cas.push(poser([{ operation: "assise", charge: {} },
                      { operation: "reparer", charge: { recentrer: true } }]));
      console.log(JSON.stringify(cas));
    """)
    r = json.loads(_node(src))
    assert r[0] is None and r[1] is None and r[2] is None
    assert isinstance(r[3], str)
    assert "recentr" in r[3] and "face" in r[3]

def test_la_barre_dit_la_contradiction_et_le_bouton_d_ecriture_se_grise():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    barre = _fonction_etabli("rendreAttente")
    assert "contradictionDeLaFile()" in barre
    assert 'class="attente-refus"' in barre
    # le bouton est grisé par la MÊME expression que le verrou d'écriture
    assert "_ecritEnCours || contra" in barre
    ecrit = _fonction_etabli_async("ecrireVersion")
    assert ecrit.index("contradictionDeLaFile()") < ecrit.index("_ecritEnCours = true")
    assert ".attente-refus" in _lire("etabli/etabli.css")
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "contradiction or assise_et_recentrer"` → `2 failed`.

- [ ] **Step 2 : la règle, la barre, le refus**

Dans `etabli.js`, juste après `fileOrdonnee()` :

```js
/* LA CONTRADICTION NOMMÉE (dette du lot B). « Poser sur une face » tourne le
   modèle et le met AU CONTACT du sol ; « réparer l'assise » avec « recentrer
   sur l'origine » ramène le centre de la boîte englobante sur (0, 0, 0) — donc
   soulève ou enfonce exactement ce que l'assise vient de poser. Et
   ORDRE_ECRITURE écrit `assise` AVANT `reparer` : le recentrage gagne
   TOUJOURS, silencieusement, et l'utilisateur voit une version qui flotte
   sans savoir laquelle des deux cases l'a produite.
   PURE, et rendue plutôt qu'affichée : c'est ce qui la rend exécutable au banc
   dans node — la leçon de la plaque. */
function contradictionDeLaFile() {
  const a = S.enAttente.some((t) => t.operation === "assise");
  const r = S.enAttente.some((t) => t.operation === "reparer"
    && t.charge && t.charge.recentrer);
  if (!a || !r) return null;
  return "« posé sur une face » et « recentrer sur l'origine » se contredisent :"
    + " le recentrage est écrit APRÈS l'assise (voir l'ordre d'écriture) et la"
    + " défait. Décoche « recentrer », ou annule l'assise.";
}
```

Dans `rendreAttente()`, DEUX lignes de plus avant l'affectation d'`innerHTML`, juste après celle qui compose `doute` :

```js
  /* La contradiction se dit à la MÊME place que le doute d'index — la barre
     est le seul endroit du dépôt où l'on refuse (voir direRefus). Le `<span>`
     naît VIDE et son texte est posé plus bas en textContent : la règle du
     fichier veut que tout texte qui ne compose pas de balisage y aille, et
     elle tiendra le jour où cette phrase citera un nom de fichier. */
  const contra = contradictionDeLaFile();
  const refus = contra ? `<span class="attente-refus"></span>` : "";
```

le gabarit de la barre gagne `${refus}` juste après `${doute}`, et l'attribut du bouton d'écriture devient — l'attribut du bouton `#btnAnnuler`, lui, NE CHANGE PAS : annuler une file contradictoire est exactement ce qu'il faut pouvoir faire :

```js
    <button id="btnEcrire"${_ecritEnCours || contra ? " disabled" : ""}>écrire la version</button>
```

Enfin, juste après l'affectation d'`innerHTML` et AVANT les deux `addEventListener` :

```js
  if (contra) $("#barreAttente .attente-refus").textContent = contra;
```

Dans `ecrireVersion()`, en toute première ligne du corps, AVANT le verrou :

```js
  const contra = contradictionDeLaFile();
  if (contra) { direRefus(contra); return null; }
```

`etabli.css` gagne `.attente-refus { color: var(--dt-erreur); margin-left: 8px; }` — la même variable que `.erreur` de la barre, jamais une seconde couleur rouge.

- [ ] **Step 3 : vert, et la campagne d'avant**

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "contradiction or assise_et_recentrer"` → `2 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k "MET_EN_ATTENTE or AU_SOL"` → verts
Run : `python tests/mutations_assise_couteau.py 22 36` → `[22] ROUGE`, `[36] ROUGE`.

- [ ] **Step 4 : commit**

```bash
git add frontend/etabli/etabli.js frontend/etabli/etabli.css backend/tests/test_etabli_outils_page.py
git commit -m 'etabli : la contradiction assise / recentrer est dite et refusee' -m 'Dette nommée du lot B refermée. Le recentrage est écrit APRÈS l assise et la défait : la barre le dit, le bouton d écriture se grise, et ecrireVersion refuse avant même de prendre son verrou. La règle est PURE et exécutée au banc dans node.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

Rien ici ne se lance tant que le lot 1 n'est pas vert : le guide (D1) DÉCRIT les
outils du lot 1, l'aperçu de tranchage (D2) suppose l'orientation et le
rangement, les connecteurs (D3) prolongent le couteau, les booléens (D4)
commencent par une mesure qui peut les faire refuser, et l'auto-orient (D5)
s'applique par le mécanisme d'assise.

### Task 14 : D1 — le chapitre 21 du guide, FR et EN : démarrer, le lexique, les ressources

**Files :** modifier `docs/guide/fr.html`, `docs/guide/en.html`, `docs/guide/Deepotus-Guide-FR.pdf`, `docs/guide/Deepotus-Guide-EN.pdf` ; tests dans `test_etabli_outils_page.py`.

> Demandé MOT POUR MOT en R10f, réponse 1 : « un guide style tutoriel débutant
> pour accompagner l'utilisateur dans ses premières manipulations et
> préparations avant l'export vers le slicer. lexique explicatif avec des
> ressources liées aux meilleures pratiques enregistrées sur le net par type
> d'impressions, de machines, de slicer, et de filament, bref un vrai petit
> guide FR-EN pour démarrer ».

- [ ] **Step 1 : le banc du guide, d'abord (rouge)**

```python
GUIDE = RACINE / "docs" / "guide"

def test_le_chapitre_21_existe_dans_les_DEUX_langues_avec_son_entree_de_sommaire():
    for nom, titre in (("fr.html", "Préparer avant le slicer"),
                       ("en.html", "Prepare before slicing")):
        h = (GUIDE / nom).read_text("utf-8")
        assert '<h2 id="c21">' in h and titre in h
        assert '<a href="#c21">' in h
        # le chapitre 21 vient APRÈS le 20 dans le corps ET dans le sommaire
        assert h.index('<a href="#c20"') < h.index('<a href="#c21"')
        assert h.index('<h2 id="c20"') < h.index('<h2 id="c21"')

def test_le_lexique_a_ses_DIX_HUIT_termes_ancres_dans_les_deux_langues():
    termes = ["assise", "surplomb", "support", "brim", "raft", "jupe",
              "remplissage", "couture", "retraction", "couche", "perimetre",
              "pont", "warping", "etancheite", "manifold", "decimation",
              "creusage", "drainage"]
    for nom in ("fr.html", "en.html"):
        h = (GUIDE / nom).read_text("utf-8")
        for t in termes:
            assert f'id="lex-{t}"' in h, (nom, t)
        assert h.count('id="lex-') == 18

def test_chaque_ressource_du_guide_est_DATEE_et_pointe_un_domaine_verifie():
    import re as _re
    domaines = {"help.prusa3d.com", "github.com", "www.simplify3d.com",
                "wiki.elegoo.com"}
    for nom in ("fr.html", "en.html"):
        h = (GUIDE / nom).read_text("utf-8")
        bloc = h.split('<h2 id="c21"', 1)[1]
        liens = _re.findall(r'<a href="(https?://[^"]+)"[^>]*>', bloc)
        assert len(liens) >= 12, (nom, len(liens))
        for u in liens:
            assert u.split("/")[2] in domaines, u
        # une date de vérification par ligne de ressource, au format 03/09/2026
        rows = _re.findall(r"<tr>.*?</tr>", bloc, _re.S)
        avec_lien = [r for r in rows if "<a href=\"http" in r]
        for r in avec_lien:
            assert "03/09/2026" in r, r[:120]

def test_les_PDF_sont_plus_recents_que_leur_source_HTML():
    """Le PDF est REGÉNÉRÉ, pas oublié : c'est lui que l'utilisateur imprime."""
    for html, pdf in (("fr.html", "Deepotus-Guide-FR.pdf"),
                      ("en.html", "Deepotus-Guide-EN.pdf")):
        assert (GUIDE / pdf).stat().st_mtime >= (GUIDE / html).stat().st_mtime
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "chapitre_21 or lexique or ressource or PDF"` → `4 failed`.

- [ ] **Step 2 : l'entrée de sommaire, dans les deux fichiers**

Dans `docs/guide/fr.html`, la dernière ligne du `.toc` devient :

```html
  <a href="#c20">20 · Imprimer ses créations — impression 3D</a><br>
  <a href="#c21">21 · Préparer avant le slicer — démarrer, lexique, ressources</a>
```

Dans `docs/guide/en.html`, à la même place :

```html
  <a href="#c20">20 · Print your creations — 3D printing</a><br>
  <a href="#c21">21 · Prepare before slicing — start here, glossary, resources</a>
```

- [ ] **Step 3 : le chapitre FR, entre le chapitre 20 et le `.footer`**

```html
<h2 id="c21"><span class="num">21</span>Préparer avant le slicer — démarrer, lexique, ressources <span class="new">nouveau</span></h2>
<p>Le chapitre 20 vous a montré comment <em>sortir</em> un fichier. Celui-ci vous montre quoi faire <em>avant</em>. L'écran <strong>Établi</strong> (Game Assets · 3D → un modèle → <em>Ouvrir dans l'Établi</em>) est l'atelier où l'on répare, oriente, range, creuse et mesure une pièce, pour que le slicer n'ait plus qu'à trancher. Rien de ce qui suit n'est irréversible : <strong>chaque geste écrit une VERSION de plus</strong>, et toutes restent sur le disque.</p>

<div class="step"><span class="n">1</span><div><strong>Posez une taille cible.</strong> Rail de droite, champ <em>taille cible</em> : tapez la plus grande dimension voulue, en millimètres (80 pour une figurine, 250 pour un plateau). Un fichier 3D ne porte aucune unité — tant que ce champ est vide, l'Établi affiche des « unités glTF » et refuse tout ce qui demande une cote physique (creuser, ranger, percer). C'est voulu : mieux vaut un refus qu'un millimètre inventé.</div></div>
<div class="step"><span class="n">2</span><div><strong>Choisissez l'imprimante.</strong> Toujours dans le rail, le menu <em>imprimante</em> : la <strong>Elegoo Centauri Carbon 2</strong> est là d'origine (plateau 256 × 256 × 256 mm, zone de purge exclue). Si OrcaSlicer ou ElegooSlicer est installé, ses profils apparaissent aussi — lus, jamais modifiés. Le contour vert dessiné sur la plaque EST le plateau de la machine choisie ; le rectangle rouge est la zone où l'on ne pose rien.</div></div>
<div class="step"><span class="n">3</span><div><strong>Réparez en un clic.</strong> Onglet <em>Fiche</em> → <em>Réparer en un clic</em>. Cinq passes : sommets confondus soudés, faces dupliquées retirées, triangles plats retirés, normales remises dans le même sens, trous bouchés. Le détail s'affiche en bas — « 12 soudés, 1 trou bouché, fermé ». Ce qu'il n'a pas su boucher est dit aussi : un maillage ouvert s'imprime mal, mieux vaut le savoir ici que devant la machine.</div></div>
<div class="step"><span class="n">4</span><div><strong>Posez la pièce à plat.</strong> Bouton <em>Poser sur une face</em>, puis cliquez la face qui doit toucher le plateau. C'est le geste qui décide de tout le reste : une pièce bien posée n'a presque pas besoin de supports. Si vous hésitez, <em>Orienter automatiquement</em> propose trois poses classées et vous dit pourquoi — surface de contact, surplombs, complexité du contour. <strong>Regardez toujours la proposition</strong> : aucun calcul ne connaît la face que vous voulez voir belle.</div></div>
<div class="step"><span class="n">5</span><div><strong>Regardez les surplombs.</strong> Bouton <em>Surplombs</em> : les faces trop penchées se peignent en orange. Au-delà d'environ 45° depuis l'horizontale, une couche n'a plus grand-chose sous elle et le slicer devra poser un support. Tournez la pièce jusqu'à ce que l'orange recule — c'est plus rapide, plus propre, et cela économise du filament.</div></div>
<div class="step"><span class="n">6</span><div><strong>Creusez, si la pièce est massive.</strong> Onglet <em>Fiche</em> → <em>Creuser</em>, paroi de 2 mm pour commencer. Une figurine pleine coûte des heures et du filament pour rien. Ajoutez ensuite un <strong>trou de drainage</strong> (⌀ 4 mm) en cliquant une face cachée : sans lui, le creux emprisonne de l'air (et, en résine, du liquide).</div></div>
<div class="step"><span class="n">7</span><div><strong>Rangez sur le plateau.</strong> Bouton <em>Sur la plaque</em> pour séparer les pièces, puis <em>Ranger sur le plateau</em> : elles se posent dans le plateau réel, tournées si cela fait gagner de la place, avec 2 mm entre elles. Ce qui ne rentre pas passe sur un second plateau, et ce qui est plus grand que la machine est dit. Vous pouvez toujours déplacer une pièce à la souris (les flèches la poussent d'un cran de règle).</div></div>
<div class="step"><span class="n">8</span><div><strong>Mesurez, puis exportez.</strong> <em>Mesurer</em> → deux clics donnent une distance, ses composantes x/y/z et l'angle des deux faces. Enfin, le bouton <strong>→ Impression 3D</strong> écrit le STL et le 3MF (chapitre 20), et « Ouvrir dans le slicer » vous y emmène.</div></div>

<div class="tip"><strong>L'ordre qui marche</strong> : réparer → orienter → creuser → percer → ranger → exporter. Réparer en dernier ne sert à rien (les autres gestes partent d'une géométrie déjà saine) ; ranger avant d'orienter fait tout recommencer.</div>

<h3>Lexique</h3>
<p>Les mots que le slicer va vous dire, expliqués une fois.</p>
<table>
<tr><th>Terme</th><th>Ce que c'est</th></tr>
<tr><td id="lex-assise"><strong>Assise</strong></td><td>La face qui touche le plateau. Large et plate, l'impression tient ; étroite, elle se décolle.</td></tr>
<tr><td id="lex-surplomb"><strong>Surplomb</strong></td><td>Une paroi trop penchée pour tenir sur la couche d'en dessous. Prusa donne <strong>45 à 60°</strong> comme limite propre sans support.</td></tr>
<tr><td id="lex-support"><strong>Support</strong></td><td>Une structure jetable qui soutient les surplombs. Trois styles courants : <em>Grid</em> (grille), <em>Snug</em> (au plus près), <em>Organic</em> (arborescent).</td></tr>
<tr><td id="lex-brim"><strong>Brim</strong></td><td>Une collerette d'une couche autour de la pièce, pour l'empêcher de décoller aux coins.</td></tr>
<tr><td id="lex-raft"><strong>Raft</strong></td><td>Un radeau imprimé SOUS la pièce entière. Plus sûr qu'un brim, plus coûteux, et il laisse une face rugueuse.</td></tr>
<tr><td id="lex-jupe"><strong>Jupe (skirt)</strong></td><td>Un contour tracé à côté de la pièce, sans la toucher, pour amorcer le flux avant de commencer.</td></tr>
<tr><td id="lex-remplissage"><strong>Remplissage (infill)</strong></td><td>Le motif de l'intérieur. <em>Gyroid</em> et <em>Cubic</em> sont isotropes ; <em>Lightning</em> ne remplit que sous les toits. 15 % suffisent le plus souvent.</td></tr>
<tr><td id="lex-couture"><strong>Couture (seam)</strong></td><td>Chaque tour de paroi commence et finit quelque part : cela laisse une ligne verticale visible. Le slicer la cache (<em>Aligned</em>, <em>Rear</em>) ou la disperse (<em>Random</em>).</td></tr>
<tr><td id="lex-retraction"><strong>Rétraction</strong></td><td>Le filament est tiré en arrière pendant les déplacements, pour éviter les fils (<em>stringing</em>).</td></tr>
<tr><td id="lex-couche"><strong>Couche (layer)</strong></td><td>Une tranche horizontale. 0,2 mm est le compromis courant ; 0,12 mm pour du détail, 0,28 mm pour de la vitesse.</td></tr>
<tr><td id="lex-perimetre"><strong>Périmètre (wall)</strong></td><td>Le nombre de tours de paroi. Deux périmètres à 0,45 mm font une paroi de 0,9 mm : c'est le minimum à viser lors de la modélisation.</td></tr>
<tr><td id="lex-pont"><strong>Pont (bridging)</strong></td><td>Imprimer une couche au-dessus du vide, entre deux appuis. Ça marche jusqu'à quelques centimètres, avec un bon refroidissement.</td></tr>
<tr><td id="lex-warping"><strong>Warping</strong></td><td>Les coins qui se soulèvent en refroidissant. Remèdes : plateau propre, brim, enceinte fermée. Fréquent en ABS/ASA, rare en PLA.</td></tr>
<tr><td id="lex-etancheite"><strong>Étanchéité</strong></td><td>Un solide est étanche quand sa surface est fermée, sans trou ni bord libre. C'est ce que la fiche de l'Établi appelle « fermé ».</td></tr>
<tr><td id="lex-manifold"><strong>Manifold</strong></td><td>Chaque arête appartient à exactement deux faces. Un maillage non-manifold peut être fermé et rester impossible à trancher proprement.</td></tr>
<tr><td id="lex-decimation"><strong>Décimation</strong></td><td>Réduire le nombre de triangles. Un maillage de 500 000 triangles ne s'imprime pas mieux qu'un de 100 000, mais il ralentit tout.</td></tr>
<tr><td id="lex-creusage"><strong>Creusage (hollowing)</strong></td><td>Remplacer l'intérieur plein par une coque d'épaisseur donnée. 2 mm est un bon point de départ en FDM.</td></tr>
<tr><td id="lex-drainage"><strong>Drainage</strong></td><td>Le ou les trous qui laissent sortir l'air (en FDM) ou la résine non polymérisée (en SLA) d'une pièce creusée.</td></tr>
</table>

<h3>Où apprendre la suite</h3>
<p>Chaque lien ci-dessous a été ouvert et vérifié le 03/09/2026. Ils sont classés par ce qu'ils vous apprennent.</p>
<table>
<tr><th>Sujet</th><th>Ressource</th><th>Vérifié</th></tr>
<tr><td>Supports et surplombs</td><td><a href="https://help.prusa3d.com/article/support-material_1698">Prusa — Support material</a></td><td>03/09/2026</td></tr>
<tr><td>Modéliser pour l'impression</td><td><a href="https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135">Prusa — Modeling with 3D printing in mind</a></td><td>03/09/2026</td></tr>
<tr><td>Ponts</td><td><a href="https://help.prusa3d.com/article/poor-bridging_1802">Prusa — Poor bridging</a></td><td>03/09/2026</td></tr>
<tr><td>Couches et périmètres</td><td><a href="https://help.prusa3d.com/article/layers-and-perimeters_1748">Prusa — Layers and perimeters</a></td><td>03/09/2026</td></tr>
<tr><td>Remplissage</td><td><a href="https://help.prusa3d.com/article/infill-patterns_177130">Prusa — Infill patterns</a></td><td>03/09/2026</td></tr>
<tr><td>Couture</td><td><a href="https://help.prusa3d.com/article/seam-position_151069">Prusa — Seam position</a></td><td>03/09/2026</td></tr>
<tr><td>Jupe et brim</td><td><a href="https://help.prusa3d.com/article/skirt-and-brim_133969">Prusa — Skirt and brim</a></td><td>03/09/2026</td></tr>
<tr><td>Décollement (warping)</td><td><a href="https://help.prusa3d.com/article/warping_2011">Prusa — Warping</a></td><td>03/09/2026</td></tr>
<tr><td>Filament PLA</td><td><a href="https://help.prusa3d.com/article/pla_2062">Prusa — PLA</a> (buse 215 °C première couche puis 210 °C, plateau 60 °C)</td><td>03/09/2026</td></tr>
<tr><td>Filament PETG</td><td><a href="https://help.prusa3d.com/article/petg_2059">Prusa — PETG</a> (buse 230–240 °C, plateau 85–90 °C)</td><td>03/09/2026</td></tr>
<tr><td>Choisir un filament</td><td><a href="https://help.prusa3d.com/materials">Prusa — Material guide</a> (PLA, PETG, ASA/ABS, PC, PA, Flex, composites)</td><td>03/09/2026</td></tr>
<tr><td>Défauts d'impression</td><td><a href="https://www.simplify3d.com/resources/print-quality-troubleshooting/">Simplify3D — Print Quality Troubleshooting</a> (26 symptômes illustrés)</td><td>03/09/2026</td></tr>
<tr><td>Slicer — préparer</td><td><a href="https://github.com/SoftFever/OrcaSlicer/wiki/prepare_object_manipulation">OrcaSlicer — Object manipulation</a></td><td>03/09/2026</td></tr>
<tr><td>Slicer — orienter</td><td><a href="https://github.com/SoftFever/OrcaSlicer/wiki/prepare_auto_orient">OrcaSlicer — Auto orientation</a> (« may not always find the best orientation »)</td><td>03/09/2026</td></tr>
<tr><td>Slicer — calibrer</td><td><a href="https://github.com/SoftFever/OrcaSlicer/wiki/Home">OrcaSlicer — Wiki (Calibrations)</a></td><td>03/09/2026</td></tr>
<tr><td>Machine</td><td><a href="https://wiki.elegoo.com/centauri-carbon-2-combo">Elegoo — Centauri Carbon 2</a></td><td>03/09/2026</td></tr>
</table>

<div class="warn">Ces liens sont ceux d'éditeurs de slicers et de fabricants : ils décrivent LEUR machine et LEUR logiciel. Les réglages chiffrés (températures, vitesses) valent pour le matériel qu'ils citent ; sur une autre machine, ce sont des points de départ, pas des vérités. Deux références souvent conseillées ailleurs sont <strong>en fin de vie</strong> et ne figurent donc pas ici : Microsoft 3D Builder (déprécié en juillet 2024) et Autodesk Meshmixer (plus développé depuis 2017).</div>
```

- [ ] **Step 4 : le chapitre EN, à la même place dans `en.html`**

Traduction fidèle, MÊME structure, MÊMES ancres `id="lex-…"` (les identifiants ne se traduisent pas : ce sont les cibles de l'aide contextuelle de la tâche 15, qui n'a qu'un jeu de clés) et MÊME table de ressources.

```html
<h2 id="c21"><span class="num">21</span>Prepare before slicing — start here, glossary, resources <span class="new">new</span></h2>
<p>Chapter 20 showed you how to get a file <em>out</em>. This one shows what to do <em>before</em>. The <strong>Workbench</strong> screen (Game Assets · 3D → a model → <em>Open in Workbench</em>) is the workshop where you repair, orient, arrange, hollow and measure a part, so the slicer only has to slice. Nothing below is irreversible: <strong>every gesture writes one more VERSION</strong>, and all of them stay on disk.</p>

<div class="step"><span class="n">1</span><div><strong>Set a target size.</strong> Right rail, <em>target size</em> field: type the largest wanted dimension, in millimeters (80 for a figurine, 250 for a board). A 3D file carries no unit — while this field is empty the Workbench shows "glTF units" and refuses everything that needs a physical dimension (hollowing, arranging, drilling). That is deliberate: a refusal beats an invented millimeter.</div></div>
<div class="step"><span class="n">2</span><div><strong>Pick the printer.</strong> Same rail, <em>printer</em> menu: the <strong>Elegoo Centauri Carbon 2</strong> is built in (256 × 256 × 256 mm bed, purge area excluded). If OrcaSlicer or ElegooSlicer is installed, its profiles show up too — read, never modified. The green outline drawn on the plate IS the chosen machine's bed; the red rectangle is the area where nothing may sit.</div></div>
<div class="step"><span class="n">3</span><div><strong>Repair in one click.</strong> <em>Sheet</em> tab → <em>Repair in one click</em>. Five passes: coincident vertices welded, duplicate faces dropped, flat triangles dropped, normals unified, holes capped. The detail appears at the bottom — "12 welded, 1 hole capped, closed". What it could not cap is said too: an open mesh prints badly, better to know here than at the machine.</div></div>
<div class="step"><span class="n">4</span><div><strong>Lay the part flat.</strong> <em>Lay on face</em>, then click the face that must touch the bed. This one gesture decides everything else: a well-placed part barely needs supports. If unsure, <em>Auto-orient</em> proposes three ranked poses and says why — contact area, overhangs, contour complexity. <strong>Always review the proposal</strong>: no computation knows which face you want to look good.</div></div>
<div class="step"><span class="n">5</span><div><strong>Look at the overhangs.</strong> <em>Overhangs</em> button: faces that lean too far turn orange. Past roughly 45° from horizontal, a layer has little underneath it and the slicer will add support. Turn the part until the orange recedes — it is faster, cleaner and saves filament.</div></div>
<div class="step"><span class="n">6</span><div><strong>Hollow it, if the part is solid.</strong> <em>Sheet</em> tab → <em>Hollow</em>, 2 mm wall to begin with. A solid figurine costs hours and filament for nothing. Then add a <strong>drain hole</strong> (⌀ 4 mm) by clicking a hidden face: without it the cavity traps air (and, in resin, liquid).</div></div>
<div class="step"><span class="n">7</span><div><strong>Arrange on the bed.</strong> <em>On the plate</em> to separate the pieces, then <em>Arrange on the bed</em>: they land inside the real bed, rotated when that saves room, 2 mm apart. What does not fit moves to a second plate, and what is larger than the machine is reported. You can still drag any piece (arrow keys nudge it by one ruler step).</div></div>
<div class="step"><span class="n">8</span><div><strong>Measure, then export.</strong> <em>Measure</em> → two clicks give a distance, its x/y/z components and the angle between the two faces. Finally, <strong>→ 3D printing</strong> writes the STL and the 3MF (chapter 20), and "Open in slicer" takes you there.</div></div>

<div class="tip"><strong>The order that works</strong>: repair → orient → hollow → drill → arrange → export. Repairing last is pointless (the other gestures start from already-sound geometry); arranging before orienting makes you redo it all.</div>
```

suivi du même `<h3>Glossary</h3>` (mêmes 18 `id="lex-…"`, définitions traduites), du même `<h3>Where to learn more</h3>` (table de ressources IDENTIQUE — mêmes URL, mêmes dates) et du même `.warn` traduit.

- [ ] **Step 5 : régénérer les deux PDF (Edge sans interface)**

Run (PowerShell, depuis la racine du dépôt ; le chemin d'Edge est celui MESURÉ sur cette machine le 03/09 — la version 64 bits sous `C:\Program Files\` n'existe pas ici) :

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$g = (Resolve-Path .\docs\guide).Path
& $edge --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="$g\Deepotus-Guide-FR.pdf" "file:///$($g -replace '\\','/')/fr.html"
& $edge --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="$g\Deepotus-Guide-EN.pdf" "file:///$($g -replace '\\','/')/en.html"
Get-ChildItem $g\*.pdf | Select-Object Name, Length, LastWriteTime
```

Expected : deux fichiers réécrits, `LastWriteTime` de l'instant, taille du même ordre qu'avant (8,3 Mo — les captures dominent le poids ; le chapitre 21 est textuel, comme le 20 et le 17).

- [ ] **Step 6 : vert, et le guide servi par l'application**

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "chapitre_21 or lexique or ressource or PDF"` → `4 passed`

Le guide est monté par `app.main` (`app.mount("/guide", …)`) : aucune route à écrire, `/guide/fr.html#c21` marche dès le fichier écrit.

- [ ] **Step 7 : commit**

```bash
git add docs/guide/fr.html docs/guide/en.html docs/guide/Deepotus-Guide-FR.pdf docs/guide/Deepotus-Guide-EN.pdf backend/tests/test_etabli_outils_page.py
git commit -m 'guide : chapitre 21 FR/EN - preparer avant le slicer, lexique de 18 termes, 16 ressources datees' -m 'Demandé mot pour mot au balayage : un guide de démarrage FR-EN, un lexique, et des ressources par type d impression, de machine, de slicer et de filament. Chaque lien a été OUVERT et vérifié le 03/09/2026 et porte sa date dans la table ; les deux références de réparation en un clic les plus citées ailleurs (3D Builder, Meshmixer) sont dites en fin de vie plutôt que recommandées. PDF régénérés par Edge sans interface.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 15 : D1 — l'aide contextuelle dans `/etabli`, alignée sur le guide par un banc

**Files :** créer `frontend/etabli/aide.js` ; modifier `frontend/etabli/etabli.js`, `frontend/etabli/index.html`, `frontend/etabli/etabli.css` ; tests dans `test_etabli_outils_page.py`.

- [ ] **Step 1 : les tests (rouge)**

```python
def test_l_aide_de_l_etabli_ne_definit_QUE_des_termes_qui_existent_dans_LE_GUIDE():
    """DEUX NIVEAUX, UNE SEULE VÉRITÉ. L'écran donne une phrase, le guide donne
    le chapitre ; un terme défini à l'écran et absent du guide enverrait sur une
    ancre morte, et un lexique qui diverge du guide est pire que pas de lexique."""
    import re as _re
    aide = _lire("etabli/aide.js")
    cles = _re.findall(r'^\s{2}([a-z]+): \{', aide, _re.M)
    assert len(cles) == 18
    for lang in ("fr.html", "en.html"):
        h = (RACINE / "docs" / "guide" / lang).read_text("utf-8")
        for c in cles:
            assert f'id="lex-{c}"' in h, (lang, c)

def test_l_aide_pointe_le_guide_dans_la_langue_de_la_page_et_par_ancre():
    aide, js = _lire("etabli/aide.js"), _lire("etabli/etabli.js")
    assert 'document.documentElement.lang' in aide
    assert '"/guide/fr.html#lex-"' in aide.replace(" ", "") or '/guide/fr.html#lex-' in aide
    assert "/guide/en.html#lex-" in aide
    assert 'import { LEXIQUE, ouvrirAide } from "./aide.js";' in js
    assert '<button class="head-btn" id="btnAide">' in _lire("etabli/index.html")
    # le compte de head-btn du banc d'avant devient QUATRE, et l'invariant
    # auto-portant (autant de <button> que de porteurs de la classe) tient
    html = _lire("etabli/index.html")
    entete = html.split("<header", 1)[1].split("</header>", 1)[0]
    assert entete.count("<button") == entete.count('class="head-btn"') == 4
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k aide` → `2 failed`.

- [ ] **Step 2 : `frontend/etabli/aide.js`**

```js
/* L'AIDE CONTEXTUELLE DE L'ÉTABLI — dix-huit mots, une phrase chacun, et le
   chemin vers le chapitre du guide qui les développe.

   POURQUOI DEUX NIVEAUX PLUTÔT QUE DEUX COPIES : le guide (chapitre 21) porte
   les définitions longues, les chiffres et les liens vérifiés ; l'écran porte
   la phrase qu'on lit sans quitter son geste. Les CLÉS sont les mêmes des deux
   côtés (`lex-<clé>` est l'ancre du guide), et un banc refuse un terme d'ici
   qui n'existerait pas là-bas : deux lexiques qui divergent valent moins que
   pas de lexique du tout.

   PAS DE TRADUCTION ICI : l'écran de l'Établi est en français, comme tout le
   reste de l'application ; seul le LIEN change de langue, d'après le `lang` du
   document — c'est le guide, lui, qui existe en deux langues. */
export const LEXIQUE = {
  assise: { titre: "Assise", texte: "La face qui touche le plateau. Large et plate, l'impression tient ; étroite, elle se décolle." },
  surplomb: { titre: "Surplomb", texte: "Une paroi trop penchée pour tenir sur la couche d'en dessous. Au-delà de 45 à 60° depuis l'horizontale, il faut un support." },
  support: { titre: "Support", texte: "Structure jetable qui soutient les surplombs. Le slicer la génère ; l'Établi ne fait que réduire le besoin." },
  brim: { titre: "Brim", texte: "Collerette d'une couche autour de la pièce, contre le décollement des coins." },
  raft: { titre: "Raft", texte: "Radeau imprimé sous toute la pièce. Plus sûr qu'un brim, plus coûteux, face rugueuse." },
  jupe: { titre: "Jupe (skirt)", texte: "Contour tracé à côté de la pièce pour amorcer le flux avant de commencer." },
  remplissage: { titre: "Remplissage", texte: "Motif de l'intérieur. 15 % suffisent le plus souvent ; gyroïde et cubique sont isotropes." },
  couture: { titre: "Couture", texte: "Ligne verticale laissée par le début et la fin de chaque tour de paroi. Le slicer la cache ou la disperse." },
  retraction: { titre: "Rétraction", texte: "Le filament est tiré en arrière pendant les déplacements, contre les fils." },
  couche: { titre: "Couche", texte: "Tranche horizontale. 0,2 mm est le compromis courant ; 0,12 mm pour du détail." },
  perimetre: { titre: "Périmètre", texte: "Nombre de tours de paroi. Deux à 0,45 mm font 0,9 mm : le minimum à viser en modélisant." },
  pont: { titre: "Pont", texte: "Couche imprimée au-dessus du vide entre deux appuis. Quelques centimètres, avec un bon refroidissement." },
  warping: { titre: "Warping", texte: "Coins qui se soulèvent en refroidissant. Plateau propre, brim, enceinte fermée." },
  etancheite: { titre: "Étanchéité", texte: "Surface fermée, sans trou ni bord libre. C'est le « fermé » de la fiche de maillage." },
  manifold: { titre: "Manifold", texte: "Chaque arête appartient à exactement deux faces. Un maillage peut être fermé ET non-manifold." },
  decimation: { titre: "Décimation", texte: "Réduire le nombre de triangles. 500 000 ne s'impriment pas mieux que 100 000, mais ralentissent tout." },
  creusage: { titre: "Creusage", texte: "Remplacer l'intérieur plein par une coque. 2 mm est un bon point de départ en FDM." },
  drainage: { titre: "Drainage", texte: "Le trou qui laisse sortir l'air d'une pièce creusée — et la résine, en SLA." },
};

/* Le chapitre du guide, dans la langue du document. `lang` est posé une seule
   fois, sur <html>, et l'Établi le porte à « fr » ; une page servie un jour en
   anglais suivrait sans qu'on touche ici. */
export function lienGuide(cle) {
  const en = String(document.documentElement.lang || "fr").startsWith("en");
  const page = en ? "/guide/en.html" : "/guide/fr.html";
  return cle ? `${page}#lex-${cle}` : `${page}#c21`;
}

/* Le panneau. Il n'invente aucun balisage de plus que ce que la feuille de
   l'Établi habille déjà : un titre, une liste de définitions, un lien. */
export function ouvrirAide(hote) {
  const lignes = Object.entries(LEXIQUE).map(([cle, d]) =>
    `<div class="aide-mot"><b>${d.titre}</b> — ${d.texte}
     <a href="${lienGuide(cle)}" target="_blank" rel="noopener">guide</a></div>`).join("");
  hote.innerHTML = `<div class="dt-label">Aide — préparer avant le slicer</div>
    <ol class="aide-pas">
      <li>Pose une taille cible (rail de droite) : sans elle, aucun millimètre.</li>
      <li>Choisis l'imprimante : le contour vert est son plateau.</li>
      <li>Répare en un clic (onglet Fiche), lis le détail dans la barre.</li>
      <li>Pose sur une face, ou laisse « Orienter » proposer — et REGARDE la proposition.</li>
      <li>Regarde les surplombs, tourne jusqu'à ce que l'orange recule.</li>
      <li>Creuse (2 mm), puis perce un trou de drainage sur une face cachée.</li>
      <li>Range sur le plateau.</li>
      <li>Mesure, puis « → Impression 3D ».</li>
    </ol>
    <div class="aide-lex">${lignes}</div>
    <a class="aide-tout" href="${lienGuide(null)}" target="_blank" rel="noopener">
      Le chapitre complet du guide, avec les ressources vérifiées →</a>`;
  hote.classList.remove("hidden");
}
```

- [ ] **Step 3 : le branchement dans la page**

`index.html` : un quatrième bouton d'en-tête, à gauche de « Sur la plaque » (il porte `head-btn` comme ses trois voisins — c'est la classe, jamais l'`id`, qui les rend identiques) :

```html
        <button class="head-btn" id="btnAide" title="Le pas à pas et le lexique, sans quitter l'écran">Aide</button>
```

et un panneau d'accueil, après `#repere` :

```html
    <div class="aide hidden" id="panAide"></div>
```

`etabli.js` : `import { LEXIQUE, ouvrirAide } from "./aide.js";` en tête, et :

```js
$("#btnAide").addEventListener("click", () => {
  const p = $("#panAide");
  if (!p.classList.contains("hidden")) { p.classList.add("hidden"); return; }
  ouvrirAide(p);
});
```

`etabli.css` gagne `.aide`, `.aide-pas`, `.aide-mot`, `.aide-tout` — mêmes tailles et mêmes variables que `.repere-note` et `.plaque-liste`, aucune couleur neuve.

- [ ] **Step 4 : vert, et l'invariant d'en-tête**

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k aide` → `2 passed`

Puis, dans `test_etabli_canevas.py`, l'assertion `html.count('class="head-btn"') == 3` (deux sites : le banc de l'en-tête et celui des outils) devient `== 4`. L'invariant auto-portant — `entete.count("<button") == entete.count('class="head-btn"')` — n'a pas à bouger : c'est tout son intérêt.

Run : `python -m pytest tests/test_etabli_canevas.py -q -k "entete or vue_a or outils_vivent"` → verts.

- [ ] **Step 5 : commit**

```bash
git add frontend/etabli/aide.js frontend/etabli/etabli.js frontend/etabli/index.html frontend/etabli/etabli.css backend/tests/test_etabli_outils_page.py backend/tests/test_etabli_canevas.py
git commit -m 'etabli : aide contextuelle - le pas a pas et les 18 mots, alignes sur le guide par un banc' -m 'Deux niveaux, une seule vérité : l écran donne la phrase, le guide donne le chapitre, et les clés sont les mêmes des deux côtés. Un banc refuse un terme de l écran qui n aurait pas son ancre lex- dans les DEUX langues du guide — un lexique qui diverge vaut moins que pas de lexique.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 16 : D2 — l'aperçu de tranchage INDICATIF : les surplombs peints, les couches tracées

**Files :** créer `frontend/lib3d/surplomb.js`, `backend/app/services/mesh_slice.py` ; modifier `frontend/lib3d/viewer.js` (`dessinerTranches`), `frontend/etabli/etabli.js`, `frontend/etabli/index.html`, `backend/app/api/routes.py`, `backend/tests/mesure_etabli_outils.py` ; tests dans les deux bancs neufs.

> **INDICATIF, et le mot est dans le titre.** Aucun G-code, aucune extrusion, aucun support : E1 l'a écarté (« métier du slicer »). Ce que cet aperçu montre, c'est ce qu'on ne peut PAS voir sur un modèle assemblé — quelles faces vont pendre dans le vide, et à quoi ressemble la section à une hauteur donnée. Le **pas 5 du chapitre 21** (écrit en tâche 14) décrit exactement ce geste.

- [ ] **Step 1 : la règle du surplomb, EXÉCUTÉE (rouge)**

Dans `test_etabli_outils_page.py` :

```python
def _fonction_surplomb(nom: str) -> str:
    js = _lire("lib3d/surplomb.js")
    m = re.search(r"^export function " + nom + r"\(", js, re.M)
    assert m, f"fonction {nom} introuvable dans surplomb.js"
    return js[m.start():js.index("\n}\n", m.start()) + 2].replace(
        "export function", "function", 1) + "\n"

def test_la_pente_du_surplomb_suit_la_convention_des_slicers_EXECUTEE():
    """Convention de Prusa, vérifiée le 03/09 : « The Overhang threshold value
    represents the most horizontal slope (measured from the horizontal plane)
    that you can print without support material (90=vertical) ». Donc 90° = mur
    vertical (rien à faire), 0° = plafond plat (le pire). Une face qui regarde
    vers le HAUT n'est jamais un surplomb, quelle que soit sa pente."""
    src = _fonction_surplomb("penteDepuisHorizontale") + _fonction_surplomb("estSurplomb") + """
const H = { x: 0, y: 1, z: 0 };
const bas = { x: 0, y: -1, z: 0 };      // plafond plat : pente 0
const mur = { x: 1, y: 0, z: 0 };       // mur vertical : pente 90
const biais = { x: 0.7071067811865476, y: -0.7071067811865475, z: 0 };
const haut = { x: 0, y: 1, z: 0 };      // regarde le ciel : jamais un surplomb
console.log(JSON.stringify({
  p_bas: penteDepuisHorizontale(bas, H),
  p_mur: penteDepuisHorizontale(mur, H),
  p_biais: penteDepuisHorizontale(biais, H),
  p_haut: penteDepuisHorizontale(haut, H),
  s_bas: estSurplomb(bas, H, 45), s_mur: estSurplomb(mur, H, 45),
  s_biais45: estSurplomb(biais, H, 45), s_biais50: estSurplomb(biais, H, 50),
  s_haut: estSurplomb(haut, H, 45),
  s_nul: estSurplomb({ x: 0, y: 0, z: 0 }, H, 45),
}));
"""
    r = json.loads(_node(src))
    assert r["p_bas"] == 0 and r["p_mur"] == 90
    assert abs(r["p_biais"] - 45) < 1e-6
    assert r["p_haut"] is None                    # une face vers le ciel n'a pas de pente
    assert r["s_bas"] is True and r["s_mur"] is False
    assert r["s_biais45"] is False                # 45 n'est pas SOUS le seuil 45
    assert r["s_biais50"] is True
    assert r["s_haut"] is False and r["s_nul"] is False
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k surplomb` → `1 failed` (`surplomb.js` n'existe pas).

- [ ] **Step 2 : `frontend/lib3d/surplomb.js`**

```js
/* LES SURPLOMBS — deux règles pures et un calque, dans lib3d/ parce que la
   question « cette face pend-elle dans le vide ? » n'a rien de propre à
   l'Établi (spec §12).

   LA CONVENTION EST CELLE DES SLICERS, et elle se lit à l'envers de l'intuition
   la première fois : la pente est mesurée DEPUIS L'HORIZONTALE, si bien que 90°
   est un mur vertical (qui s'imprime tout seul) et 0° un plafond plat (le pire
   cas). C'est le mot exact de la base de connaissance Prusa, vérifiée le
   03/09/2026. Un seuil de 45° veut donc dire : « peins ce qui est SOUS 45° ». */

/* La pente d'une face, en degrés depuis l'horizontale — ou `null` quand la
   face ne regarde pas vers le bas (une face tournée vers le ciel n'a jamais
   besoin de support) ou que la normale est nulle. */
export function penteDepuisHorizontale(n, haut) {
  const ln = Math.hypot(n.x, n.y, n.z), lh = Math.hypot(haut.x, haut.y, haut.z);
  if (!(ln > 0) || !(lh > 0)) return null;
  const d = -(n.x * haut.x + n.y * haut.y + n.z * haut.z) / (ln * lh);
  if (!(d > 0)) return null;                        // vers le haut, ou tangente
  const borne = Math.min(1, d);
  return Math.round((Math.acos(borne) * 180) / Math.PI * 1e6) / 1e6;
}

/* SOUS le seuil, strictement : à 45° pile, la face tient — c'est la borne que
   les slicers appellent « imprimable sans support ». */
export function estSurplomb(n, haut, seuilDeg) {
  const p = penteDepuisHorizontale(n, haut);
  return p !== null && p < seuilDeg;
}

/* Le CALQUE : un maillage translucide posé sur les seuls triangles en
   surplomb, dans le monde. Même mécanique que l'aperçu du couteau (des objets
   ajoutés à la scène, retirés au rangement) — jamais une couleur écrite dans
   le matériau de l'utilisateur, qui est PARTAGÉ entre pièces (la leçon des
   teintes de la plaque : la dernière parcourue gagne, et la couleur fuit). */
const _calques = new WeakMap();
export function peindreSurplombs(api, seuilDeg, haut) {
  const ancien = _calques.get(api);
  if (ancien) {
    api.scene.remove(ancien);
    ancien.traverse((o) => { if (o.geometry) o.geometry.dispose();
                             if (o.material) o.material.dispose(); });
    _calques.delete(api);
  }
  if (!(seuilDeg > 0) || !api || !api.racine) return null;
  api.racine.updateMatrixWorld(true);
  const points = [];
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const u = new THREE.Vector3(), v = new THREE.Vector3(), n = new THREE.Vector3();
  let vus = 0;
  api.racine.traverse((o) => {
    if (!o.isMesh || !o.geometry || !o.visible) return;
    const g = o.geometry, pos = g.attributes && g.attributes.position;
    if (!pos) return;
    const idx = g.index;
    const nb = idx ? idx.count : pos.count;
    for (let k = 0; k + 2 < nb; k += 3) {
      const i0 = idx ? idx.getX(k) : k;
      const i1 = idx ? idx.getX(k + 1) : k + 1;
      const i2 = idx ? idx.getX(k + 2) : k + 2;
      a.fromBufferAttribute(pos, i0).applyMatrix4(o.matrixWorld);
      b.fromBufferAttribute(pos, i1).applyMatrix4(o.matrixWorld);
      c.fromBufferAttribute(pos, i2).applyMatrix4(o.matrixWorld);
      u.subVectors(b, a); v.subVectors(c, a); n.crossVectors(u, v);
      vus++;
      if (!estSurplomb(n, haut, seuilDeg)) continue;
      points.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    }
  });
  if (!points.length) return { triangles: 0, vus };
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  const calque = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
    color: 0xe08a2e, transparent: true, opacity: 0.75, side: THREE.DoubleSide,
    depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  calque.name = "surplombs";
  api.scene.add(calque);
  _calques.set(api, calque);
  return { triangles: points.length / 9, vus };
}
```

`surplomb.js` importe `THREE` comme les autres modules de `lib3d/` (`import * as THREE from "three";` en tête — la carte d'import de `index.html` le résout).

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k surplomb` → `1 passed`.

- [ ] **Step 3 : le bouton dans la page**

`index.html`, dans `#vueOutils` :

```html
          <button class="outil-btn" id="btnSurplombs"></button>
```

`etabli.js` : `import { peindreSurplombs } from "../lib3d/surplomb.js";`, `const SEUIL_SURPLOMB = 45;` près de `SEUIL` — *45° depuis l'horizontale, la borne que la base de connaissance Prusa donne comme « imprimable sans support » (vérifiée le 03/09/2026) ; les modèles patients descendent à 55°, on ne prétend pas choisir à leur place* — et :

```js
/* L'AXE HAUT DE L'IMPRESSION, et il n'est pas toujours +Y. Sur la plaque, c'est
   l'axe d'empilement que plaque.js a choisi et qui porte le plateau ; hors
   plaque, glTF pose +Y vers le ciel et l'export STL fait de même. Deviner
   autrement peindrait tout un modèle en orange sur un simple changement de vue. */
function axeHautImpression() {
  const g = PLQ.active ? plateauDe(S.vueA) : null;
  if (!g) return { x: 0, y: 1, z: 0 };
  return { x: g.axe === "x" ? 1 : 0, y: g.axe === "y" ? 1 : 0,
           z: g.axe === "z" ? 1 : 0 };
}

function basculerSurplombs() {
  SURPLOMB.actif = !SURPLOMB.actif;
  const r = peindreSurplombs(S.vueA, SURPLOMB.actif ? SEUIL_SURPLOMB : 0,
                             axeHautImpression());
  majOutils();
  if (!SURPLOMB.actif) { direAvis("surplombs éteints"); return; }
  if (!r) { direRefus("aucun modèle à l'écran"); return; }
  direAvis(`${r.triangles} triangle(s) sous ${SEUIL_SURPLOMB}° sur ${r.vus} — `
    + (r.triangles
      ? "tourne la pièce jusqu'à ce que l'orange recule, ou laisse le slicer poser des supports"
      : "rien à supporter dans cette pose"));
}
$("#btnSurplombs").addEventListener("click", basculerSurplombs);
```

avec `const SURPLOMB = { actif: false };` déclaré à côté de `MESURE` (règle du fichier : tout état se déclare en tête). `majOutils()` écrit le libellé (`Surplombs` / `Surplombs ✓`). Le calque est REPEINT en queue de `graduerPlateau()` quand `SURPLOMB.actif` (entrer sur la plaque change l'axe haut), et ÉTEINT par `ouvrirPrincipale()` (un modèle neuf, un calque périmé).

- [ ] **Step 4 : le miroir du bouton**

```python
def test_les_surplombs_suivent_l_axe_de_la_plaque_et_s_eteignent_au_chargement():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'import { peindreSurplombs } from "../lib3d/surplomb.js";' in js
    assert "const SEUIL_SURPLOMB = 45;" in js
    assert "const SURPLOMB = { actif: false };" in js
    axe = _fonction_etabli("axeHautImpression")
    assert "plateauDe(S.vueA)" in axe and "g.axe ===" in axe
    b = _fonction_etabli("basculerSurplombs")
    assert "axeHautImpression()" in b and "SEUIL_SURPLOMB" in b
    assert "peindreSurplombs" in _fonction_etabli("graduerPlateau")
    assert "peindreSurplombs" in _fonction_etabli("ouvrirPrincipale")
    assert '<button class="outil-btn" id="btnSurplombs">' in _lire("etabli/index.html")
    # le calque ne touche AUCUN matériau du modèle (leçon des teintes partagées)
    s = _code("lib3d/surplomb.js")
    assert ".material.color" not in s and "o.material =" not in s
```

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "surplomb"` → `2 passed`.

- [ ] **Step 5 : la mesure des tranches, puis leurs tests (rouge)**

Ajouter à `mesure_etabli_outils.py` :

```python
    elif quoi == "tranches":
        from app.services import mesh_slice
        r = chrono("trancher tore 100k en 20 couches",
                   lambda: mesh_slice.trancher(data, None, "y", nombre=20))
        print(f"   -> {sum(len(c['segments']) for c in r['couches'])} segments, "
              f"perimetre max {max(c['perimetre'] for c in r['couches']):.3f}")
        if REEL.is_file():
            chrono("trancher reel 144k en 20 couches",
                   lambda: mesh_slice.trancher(REEL.read_bytes(), None, "y", nombre=20))
```

Puis, dans `test_etabli_outils.py` :

```python
def test_trancher_un_cube_donne_des_sections_carrees_et_un_perimetre_juste():
    from app.services import mesh_slice
    r = mesh_slice.trancher(_cube(), None, "y", nombre=4)
    assert len(r["couches"]) == 4
    assert r["axe"] == "y" and abs(r["hauteur"] - 2.0) < 1e-9
    for c in r["couches"]:
        # le cube du dépôt a une arête de 2 : chaque section est un carré 2x2
        assert abs(c["perimetre"] - 8.0) < 1e-6, c
        assert len(c["segments"]) >= 4
        for (a, b) in c["segments"]:
            assert abs(a[1] - c["z"]) < 1e-9 and abs(b[1] - c["z"]) < 1e-9
    # les couches montent, et aucune ne touche les faces extrêmes
    zs = [c["z"] for c in r["couches"]]
    assert zs == sorted(zs) and min(zs) > -1.0 and max(zs) < 1.0

def test_trancher_refuse_ce_qu_il_ne_sait_pas_lire_et_borne_son_travail():
    import pytest as _p
    from app.services import mesh_edit, mesh_slice
    with _p.raises(ValueError, match="axe"):
        mesh_slice.trancher(_cube(), None, "w", nombre=4)
    for n in (0, -3, 501):
        with _p.raises(ValueError, match="couches"):
            mesh_slice.trancher(_cube(), None, "y", nombre=n)
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with _p.raises(ValueError, match="draco"):
        mesh_slice.trancher(mesh_edit.ecrire_glb(doc, binc), None, "y", nombre=4)

def test_la_route_tranches_ne_touche_pas_au_disque_et_juge_son_corps():
    d = _job("job_tr", _cube()); c = _client()
    r = c.post("/api/etabli/tranches", json={"job": "job_tr", "version": 1,
                                             "axe": "y", "nombre": 6})
    assert r.status_code == 200 and len(r.json()["couches"]) == 6
    assert not (d / "model.v2.glb").exists()          # AUCUNE version écrite
    for corps in ({"axe": "w", "nombre": 6}, {"axe": "y", "nombre": 0},
                  {"axe": "y", "nombre": 5000}):
        assert c.post("/api/etabli/tranches",
                      json={"job": "job_tr", "version": 1, **corps}).status_code == 400
```

Run : `python tests/mesure_etabli_outils.py tranches` → `ModuleNotFoundError`. **Budget fixé ici : 100 352 triangles tranchés en 20 couches en moins de 10 s**, grâce au rangement des triangles par intervalle de couches (chaque triangle n'est testé que contre les plans qu'il traverse VRAIMENT). Sans ce rangement, 20 × 100 352 tests seraient à la fois inutiles et hors budget.
Run : `python -m pytest tests/test_etabli_outils.py -q -k "trancher or tranches"` → `3 failed`.

- [ ] **Step 6 : `backend/app/services/mesh_slice.py`**

```python
# -*- coding: utf-8 -*-
"""Aperçu de tranchage INDICATIF : la section du modèle à N hauteurs.

CE QUE C'EST : l'intersection du maillage avec des plans horizontaux, rendue en
SEGMENTS bruts. Pas de chaînage en contours, pas d'orientation, pas de
remplissage, pas de G-code — E1 l'a écarté et c'est le métier du slicer. Ce que
cela donne à voir, un modèle assemblé ne le montre pas : la forme réelle d'une
section, et sa longueur (le périmètre à parcourir à cette hauteur).

DES SEGMENTS ET NON DES CONTOURS, délibérément : chaîner demanderait de décider
ce qu'on fait d'une arête non-manifold ou d'un trou — exactement les défauts que
la réparation (tâche 1) sert à trouver. Un aperçu qui refuserait de s'afficher
sur un maillage abîmé serait muet au moment où l'on en a le plus besoin. Le
viewer dessine des `LineSegments`, qui n'ont besoin d'aucun ordre.

LE RANGEMENT PAR INTERVALLE EST CE QUI TIENT LE BUDGET : chaque triangle sait
entre quelles couches il vit (de son z minimum à son z maximum) et n'est testé
que contre celles-là. Sans lui, 20 couches coûteraient 20 balayages complets.
"""
from __future__ import annotations

from app.services.hollow import refus_compression
from app.services.mesh_cut import _lire_accesseur
from app.services.mesh_edit import (_l, _mat_locale, _mat_mul,
                                    _monde_des_ancetres, lire_glb)

AXES = {"x": 0, "y": 1, "z": 2}
MAX_COUCHES = 500


def _monde(doc: dict, i: int) -> list:
    """La matrice monde d'un nœud. AUCUN calcul de chaîne neuf : `mesh_edit`
    porte déjà `_monde_des_ancetres` (avec sa garde contre un `children`
    cyclique), et sa docstring demande explicitement UN SITE pour ce calcul —
    quatre boucles l'avaient écrit à la main avant elle."""
    return _mat_mul(_monde_des_ancetres(doc, i),
                    _mat_locale(_l(doc, "nodes")[i]))


def _appliquer(m, p):
    """Un point par une matrice 4x4 en colonnes. `mesh_edit._appliquer3` ne
    sait tourner qu'une 3x3 (l'assise de Rodrigues) : ce n'est pas la même
    opération, et l'emprunter perdrait la translation."""
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


def trancher(data: bytes, noeuds, axe: str = "y", nombre: int = 20):
    """Rend {axe, hauteur, pas, couches: [{z, segments, perimetre}]}.

    Les couches sont posées au MILIEU de chaque tranche (`z0 + (k + 0,5)·pas`),
    jamais sur les faces extrêmes : un plan exactement confondu avec la face du
    dessous rendrait une section dégénérée, et c'est le même piège que le
    couteau a déjà payé (`_EPS_PLAN`, face confondue)."""
    if axe not in AXES:
        raise ValueError(f"axe « {axe} » — x, y ou z sont attendus")
    if not isinstance(nombre, int) or isinstance(nombre, bool) \
            or not (1 <= nombre <= MAX_COUCHES):
        raise ValueError(f"couches : un entier entre 1 et {MAX_COUCHES}")
    a = AXES[axe]
    doc, binc = lire_glb(data)
    refus_compression(doc, "l'aperçu de tranchage")
    nodes = _l(doc, "nodes")
    cible = None if noeuds is None else set(int(n) for n in noeuds)

    tris = []
    for i in range(len(nodes)):
        if "mesh" not in nodes[i] or (cible is not None and i not in cible):
            continue
        m = _monde(doc, i)
        for prim in _l(doc, "meshes")[nodes[i]["mesh"]].get("primitives", []):
            if prim.get("mode", 4) != 4 or "POSITION" not in (prim.get("attributes") or {}):
                continue
            pos = [_appliquer(m, p) for p in
                   _lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
            idx = ([t[0] for t in _lire_accesseur(doc, binc, prim["indices"])]
                   if "indices" in prim else list(range(len(pos))))
            for k in range(0, len(idx) - 2, 3):
                tris.append((pos[idx[k]], pos[idx[k + 1]], pos[idx[k + 2]]))
    if not tris:
        raise ValueError("aucun triangle à trancher dans la sélection")

    zmin = min(min(t[0][a], t[1][a], t[2][a]) for t in tris)
    zmax = max(max(t[0][a], t[1][a], t[2][a]) for t in tris)
    hauteur = zmax - zmin
    if hauteur <= 0:
        raise ValueError("le modèle est plat sur cet axe — rien à trancher")
    pas = hauteur / nombre
    plans = [zmin + (k + 0.5) * pas for k in range(nombre)]

    # LE RANGEMENT : chaque triangle dans les seules couches qu'il traverse
    seaux: list[list] = [[] for _ in range(nombre)]
    for t in tris:
        lo = min(t[0][a], t[1][a], t[2][a])
        hi = max(t[0][a], t[1][a], t[2][a])
        k0 = max(0, int((lo - zmin) / pas - 0.5))
        k1 = min(nombre - 1, int((hi - zmin) / pas + 0.5))
        for k in range(k0, k1 + 1):
            if lo <= plans[k] <= hi:
                seaux[k].append(t)

    couches = []
    for k, z in enumerate(plans):
        segments, perimetre = [], 0.0
        for t in seaux[k]:
            pts = []
            for e in range(3):
                p, q = t[e], t[(e + 1) % 3]
                dp, dq = p[a] - z, q[a] - z
                if (dp > 0) == (dq > 0) or dp == dq:
                    continue
                f = dp / (dp - dq)
                pts.append(tuple(round(p[c] + (q[c] - p[c]) * f, 6)
                                 for c in range(3)))
            if len(pts) == 2:
                segments.append([list(pts[0]), list(pts[1])])
                perimetre += sum((pts[0][c] - pts[1][c]) ** 2
                                 for c in range(3)) ** 0.5
        couches.append({"z": round(z, 6), "segments": segments,
                        "perimetre": round(perimetre, 6)})
    return {"axe": axe, "hauteur": round(hauteur, 6), "pas": round(pas, 6),
            "z_min": round(zmin, 6), "couches": couches}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k trancher` → `2 passed`
Run : `python tests/mesure_etabli_outils.py tranches` → deux lignes chronométrées ; **noter les deux temps dans le message de commit**.

- [ ] **Step 7 : la route et le tracé**

```python
@router.post("/etabli/tranches")
async def etabli_tranches(body: dict):
    """L'aperçu de tranchage. AUCUNE ÉCRITURE : c'est un regard, pas une
    correction — même doctrine que `/etabli/ranger`."""
    from app.services import mesh_slice
    _job, data, _depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                            "aperçu de tranchage")
    nombre = body.get("nombre", 20)
    if not _etabli_entier(nombre):
        raise HTTPException(400, "tranches : `nombre` attend un entier")
    noeuds = body.get("noeuds")
    if noeuds is not None and (not isinstance(noeuds, list)
                               or any(not _etabli_entier(n) or n < 0 for n in noeuds)):
        raise HTTPException(400, "tranches : `noeuds` doit être une liste d'index")
    try:
        return await asyncio.to_thread(
            mesh_slice.trancher, data, noeuds, str(body.get("axe", "y")), int(nombre))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

Dans `viewer.js`, à côté de `dessinerContourPlateau` :

```js
/* Les SECTIONS, en segments — `null` efface. Le module ne chaîne rien et ne
   colore rien par couche : une couche est une couleur, toutes les couches sont
   la même, et c'est l'empilement qui informe. */
const _tranches = new WeakMap();
export function dessinerTranches(api, couches) {
  const ancien = _tranches.get(api);
  if (ancien) {
    api.scene.remove(ancien);
    ancien.geometry.dispose(); ancien.material.dispose();
    _tranches.delete(api);
  }
  if (!couches || !couches.length) return null;
  const pts = [];
  for (const c of couches) for (const [a, b] of c.segments) pts.push(...a, ...b);
  if (!pts.length) return { segments: 0 };
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  const l = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    color: 0x4d7fd0, transparent: true, opacity: 0.9, depthTest: false }));
  l.name = "tranches";
  api.scene.add(l);
  _tranches.set(api, l);
  return { segments: pts.length / 6 };
}
```

Dans `etabli.js`, un bouton `#btnTranches` (`outil-btn`), `const NB_TRANCHES = 20;` et :

```js
async function basculerTranches() {
  if (TRANCHES.actives) {
    TRANCHES.actives = false;
    dessinerTranches(S.vueA, null); majOutils(); direAvis("aperçu de tranchage éteint");
    return;
  }
  if (!S.a || !S.a.job || !S.a.version) { direRefus("aucune version chargée"); return; }
  const g = PLQ.active ? plateauDe(S.vueA) : null;
  let d;
  try {
    d = await jpost("/api/etabli/tranches", { job: S.a.job, version: S.a.version,
      axe: g ? g.axe : "y", nombre: NB_TRANCHES });
  } catch (e) { direRefus(e.message); return; }
  TRANCHES.actives = true;
  const r = dessinerTranches(S.vueA, d.couches);
  majOutils();
  const plus = d.couches.reduce((m, c) => (c.perimetre > m.perimetre ? c : m), d.couches[0]);
  direAvis(`${NB_TRANCHES} couches indicatives, ${r ? r.segments : 0} segments — `
    + `la plus longue est à ${fmtMesure(plus.z - d.z_min)} ${uniteCourante()} du bas `
    + `(${fmtMesure(plus.perimetre)} de contour). Aperçu seulement : le slicer tranche pour de vrai.`);
}
```

avec `const TRANCHES = { actives: false };` déclaré à côté de `SURPLOMB`, l'extinction dans `ouvrirPrincipale()`, et `ROUTES` inchangée (aucune écriture : l'appel est direct, comme `/etabli/ranger`).

- [ ] **Step 8 : les miroirs, puis vert**

```python
def test_l_apercu_de_tranchage_ne_promet_QUE_l_indicatif_et_n_ecrit_rien():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'import { dessinerContourPlateau, dessinerTranches' in js or \
           "dessinerTranches" in js.split('from "../lib3d/viewer.js"', 1)[0]
    assert "const TRANCHES = { actives: false };" in js
    f = _fonction_etabli("basculerTranches")
    assert '"/api/etabli/tranches"' in f and "ecrireSeule" not in f
    assert "Aperçu seulement" in f and "le slicer tranche pour de vrai" in f
    assert "fmtMesure(" in f and "uniteCourante()" in f
    assert "dessinerTranches" in _fonction_etabli("ouvrirPrincipale")
    assert '<button class="outil-btn" id="btnTranches">' in _lire("etabli/index.html")
    # aucune des deux routes de REGARD n'entre dans la table des écritures
    assert "tranches" not in _table_js("etabli/etabli.js", "ROUTES")
    assert "ranger" not in _table_js("etabli/etabli.js", "ROUTES")
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "trancher or tranches"` → `3 passed`
Run : `python -m pytest tests/test_etabli_outils_page.py -q -k "surplomb or tranchage"` → `3 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k outils_vivent` → `1 passed`

- [ ] **Step 9 : commit**

```bash
git add frontend/lib3d/surplomb.js frontend/lib3d/viewer.js backend/app/services/mesh_slice.py backend/app/api/routes.py backend/tests/mesure_etabli_outils.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js frontend/etabli/index.html
git commit -m 'etabli : apercu de tranchage indicatif - surplombs peints, sections tracees' -m 'La pente suit la convention des slicers, vérifiée chez Prusa le 03/09 : 90 degrés est un mur, 0 un plafond, et le seuil de 45 se lit SOUS. Le calque n écrit dans aucun matériau du modèle (les matériaux sont partagés, la couleur fuirait). Les sections sont des segments bruts, pas des contours : chaîner demanderait de décider ce qu on fait d un maillage abîmé, au moment même où l on en a le plus besoin. Ni l un ni l autre n écrit sur le disque.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 17 : D3 — les connecteurs du couteau : téton, cheville, queue d'aronde

**Files :** créer `backend/app/services/mesh_connect.py` ; modifier `backend/app/api/routes.py`, `frontend/etabli/etabli.js`, `frontend/etabli/index.html` ; tests dans les deux bancs neufs.

> Inventaire relevé le 02/09 dans `2026-09-01-etabli-plaque-et-extraction.md`, Task 4 (OrcaSlicer, *Cut tool*) : dovetail, dowel, plug, snap. On en livre **trois** — téton (plug), cheville (dowel), queue d'aronde (dovetail) — et le quatrième (snap, un clip élastique) est écarté en une ligne dans « Écarté » : un clip demande une matière qui plie, donc une épaisseur et un matériau, donc une promesse que la géométrie seule ne tient pas.

- [ ] **Step 1 : le connecteur est POSÉ APRÈS la coupe, et c'est la décision**

Le couteau (`mesh_cut.couper`) est déjà long (903 lignes) et son capuchon a coûté quatre cas de refus nommés. Y greffer une géométrie ajoutée rouvrirait la triangulation par oreilles, qui vient tout juste d'être close.

À la place : une opération de plus, sur la version que le couteau vient d'écrire. Elle voit les deux moitiés comme deux nœuds, et fait sur chacune ce qu'un module éprouvé sait déjà faire — **poser un tube et un disque** (le foret de la tâche 7 les pose déjà pour le drainage). Le plan de coupe est relu dans la fiche (`source.plan`), donc l'utilisateur ne le ressaisit pas.

- [ ] **Step 2 : les tests (rouge)**

Dans `test_etabli_outils.py` :

```python
def _cube_coupe():
    """Le cube du dépôt, tranché en deux par le plan y = 0 : deux nœuds."""
    from app.services import mesh_cut
    sortie, rapport = mesh_cut.couper(_cube(), [0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], "deux")
    return sortie, rapport

def test_la_section_d_un_connecteur_a_la_forme_de_son_TYPE():
    from app.services import mesh_connect as MC
    rond = MC.section("teton", 1.0, 24)
    assert len(rond) == 24
    assert all(abs((x * x + y * y) ** 0.5 - 1.0) < 1e-9 for (x, y) in rond)
    aronde = MC.section("aronde", 1.0, 24)
    assert len(aronde) == 4                      # un trapèze, pas un cercle
    # la queue d'aronde est PLUS LARGE au fond qu'à l'entrée : c'est ce qui la
    # retient, et c'est mesurable
    largeur = lambda v: max(x for (x, y) in aronde if abs(y - v) < 1e-9) * 2
    assert largeur(max(y for (_x, y) in aronde)) > largeur(min(y for (_x, y) in aronde))
    import pytest as _p
    with _p.raises(ValueError, match="type"):
        MC.section("vis", 1.0, 24)

def test_poser_un_teton_ajoute_de_la_matiere_a_A_et_en_retire_a_B():
    from app.services import mesh_connect as MC, print3d
    coupe, _r = _cube_coupe()
    avant = len(print3d.lire_glb_triangles(coupe))
    sortie, rap = MC.poser(coupe, [0, 1], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                           "teton", rayon=0.3, hauteur=0.4, jeu=0.05)
    assert len(print3d.lire_glb_triangles(sortie)) > avant
    assert [p["role"] for p in rap["pieces"]] == ["male", "femelle"]
    assert rap["pieces"][0]["ajoutes"] > 0 and rap["pieces"][1]["retires"] > 0
    assert rap["jeu"] == 0.05 and rap["type"] == "teton"
    # le trou de la femelle est PLUS LARGE que le téton, du jeu exactement
    assert abs(rap["pieces"][1]["rayon"] - (0.3 + 0.05)) < 1e-12

def test_poser_refuse_ce_qui_n_a_pas_de_sens_en_le_disant():
    import pytest as _p
    from app.services import mesh_connect as MC
    coupe, _r = _cube_coupe()
    with _p.raises(ValueError, match="deux nœuds"):
        MC.poser(coupe, [0], [0, 0, 0], [0, 1, 0], "teton", 0.3, 0.4, 0.05)
    with _p.raises(ValueError, match="rayon"):
        MC.poser(coupe, [0, 1], [0, 0, 0], [0, 1, 0], "teton", 0.0, 0.4, 0.05)
    with _p.raises(ValueError, match="hauteur"):
        MC.poser(coupe, [0, 1], [0, 0, 0], [0, 1, 0], "teton", 0.3, 0.0, 0.05)
    with _p.raises(ValueError, match="direction"):
        MC.poser(coupe, [0, 1], [0, 0, 0], [0, 0, 0], "teton", 0.3, 0.4, 0.05)

def test_la_route_connecteur_relit_le_plan_de_la_fiche_et_ecrit_une_version():
    from app.services import mesh_edit
    coupe, rapport = _cube_coupe()
    d = _job("job_conn", _cube())
    mesh_edit.ecrire_version("job_conn", coupe, operation="couper",
                             detail={"depuis": {"version": 1, "fichier": "model.glb"},
                                     **rapport})
    c = _client()
    r = c.post("/api/etabli/connecteur",
               json={"job": "job_conn", "version": 2, "noeuds": [0, 1],
                     "type": "teton", "rayon_mm": 3.0, "hauteur_mm": 4.0,
                     "jeu_mm": 0.2, "echelle": 10.0})
    assert r.status_code == 200 and (d / "model.v3.glb").is_file()
    src = r.json()["source"]
    assert src["operation"] == "connecteur" and src["type"] == "teton"
    # le plan vient de la FICHE de la version coupée, pas du corps de la requête
    assert src["plan"]["normale"] == [0.0, 1.0, 0.0]
    assert src["depuis"] == {"version": 2, "fichier": "model.v2.glb"}
    for corps in ({"noeuds": [0], "type": "teton"}, {"noeuds": [0, 1], "type": "vis"},
                  {"noeuds": [0, 1], "type": "teton", "rayon_mm": 0}):
        assert c.post("/api/etabli/connecteur",
                      json={"job": "job_conn", "version": 2, "hauteur_mm": 4.0,
                            "jeu_mm": 0.2, "echelle": 10.0,
                            **{"rayon_mm": 3.0, **corps}}).status_code == 400
    # une version SANS plan de coupe dans sa fiche : refus nommé, pas un 500
    assert c.post("/api/etabli/connecteur",
                  json={"job": "job_conn", "version": 1, "noeuds": [0, 1],
                        "type": "teton", "rayon_mm": 3.0, "hauteur_mm": 4.0,
                        "jeu_mm": 0.2, "echelle": 10.0}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "connecteur or teton or section_d_un"` → `5 failed`.

- [ ] **Step 3 : `backend/app/services/mesh_connect.py`**

```python
# -*- coding: utf-8 -*-
"""Les connecteurs du couteau : téton, cheville, queue d'aronde.

POSÉS APRÈS LA COUPE, sur les deux moitiés que le couteau vient d'écrire. Le
couteau fait déjà quatre refus nommés autour de son capuchon ; y greffer une
géométrie ajoutée rouvrirait la triangulation par oreilles qui vient d'être
close. Ici on ne fait que deux choses, et un module éprouvé les fait déjà : un
TUBE fermé posé sur la moitié mâle, un TROU BORGNE creusé dans la femelle
(le foret du drainage, tâche 7, pose exactement ces primitives).

UNE SEULE SECTION POUR TROIS TYPES : téton et cheville sont des polygones
réguliers (24 côtés) ; la queue d'aronde est un TRAPÈZE, plus large
au FOND qu'à l'entrée — c'est cette différence, et elle seule, qui la retient.
Le reste du code est identique, et c'est ce qui rend les trois testables du même
geste.

LE JEU EST PORTÉ PAR LA FEMELLE, jamais par le mâle : deux pièces imprimées à
la même cote ne rentrent pas l'une dans l'autre. La base de connaissance Prusa
donne 0,3 mm de jeu entre pièces mobiles (vérifiée le 03/09/2026) ; l'UI
propose 0,2 pour un ajustement serré, et la valeur reste dans la fiche.
"""
from __future__ import annotations

import math

from app.services.hollow import refus_compression
from app.services.mesh_cut import (_ajouter_flottants, _ajouter_indices,
                                   _lire_accesseur)
from app.services.mesh_edit import _extraire_doc, _l, ecrire_glb, lire_glb

TYPES = ("teton", "cheville", "aronde")
COTES = 24


def section(type_: str, rayon: float, cotes: int = COTES):
    """La section du connecteur dans le plan de coupe, en (u, v) unitaires
    multipliés par `rayon`. Rend une liste de points dans le SENS DIRECT."""
    if type_ not in TYPES:
        raise ValueError(f"type de connecteur « {type_} » — "
                         f"{', '.join(TYPES)} sont attendus")
    if type_ == "aronde":
        # Un TRAPÈZE : étroit à l'entrée (v = −1), large au fond (v = +1).
        # C'est cette contre-dépouille, et elle seule, qui retient les deux
        # moitiés l'une dans l'autre — un rond ne retient rien en rotation.
        return [(rayon * x, rayon * y) for (x, y) in
                ((-0.55, -1.0), (0.55, -1.0), (1.0, 1.0), (-1.0, 1.0))]
    return [(rayon * math.cos(2 * math.pi * k / cotes),
             rayon * math.sin(2 * math.pi * k / cotes)) for k in range(cotes)]


def _base(n):
    """Deux vecteurs unitaires orthogonaux à `n`."""
    a = (0.0, 0.0, 1.0) if abs(n[0]) > 0.9 else (1.0, 0.0, 0.0)
    u = (n[1] * a[2] - n[2] * a[1], n[2] * a[0] - n[0] * a[2],
         n[0] * a[1] - n[1] * a[0])
    lu = math.sqrt(sum(c * c for c in u)) or 1.0
    u = tuple(c / lu for c in u)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2],
         n[0] * u[1] - n[1] * u[0])
    return u, v


def _prisme(poly, o, u, v, n, hauteur, vers_le_haut: bool):
    """Le TUBE fermé engendré par `poly` entre le plan et `hauteur`.

    Rend (positions, triangles). `vers_le_haut` dit de quel côté la matière est
    ajoutée ; l'enroulement suit, pour que les normales sortent du solide —
    sans quoi le maillage serait fermé ET retourné, ce que `mesh_repair`
    saurait réparer mais que personne n'aurait à réparer."""
    h = hauteur if vers_le_haut else -hauteur
    pts, tris = [], []
    m = len(poly)
    for (a, b) in poly:
        base = tuple(o[c] + a * u[c] + b * v[c] for c in range(3))
        pts.append(base)
    for (a, b) in poly:
        pts.append(tuple(o[c] + a * u[c] + b * v[c] + h * n[c] for c in range(3)))
    for k in range(m):
        k2 = (k + 1) % m
        if vers_le_haut:
            tris += [(k, k2, m + k), (k2, m + k2, m + k)]
        else:
            tris += [(k, m + k, k2), (k2, m + k, m + k2)]
    # le couvercle, en éventail depuis le premier point du sommet
    for k in range(1, m - 1):
        tris.append((m, m + k, m + k + 1) if vers_le_haut else (m, m + k + 1, m + k))
    return pts, tris


def poser(data: bytes, noeuds, point, normale, type_: str,
          rayon: float, hauteur: float, jeu: float):
    """Pose un connecteur entre DEUX nœuds. Le premier reçoit le mâle (côté
    vers lequel pointe la normale — le côté « a » du couteau), le second la
    femelle. Rend (GLB, rapport)."""
    if type_ not in TYPES:
        raise ValueError(f"type de connecteur « {type_} » — "
                         f"{', '.join(TYPES)} sont attendus")
    if not isinstance(noeuds, (list, tuple)) or len(noeuds) != 2:
        raise ValueError("un connecteur relie exactement deux nœuds — "
                         "les deux moitiés que le couteau a produites")
    for nom, val in (("rayon", rayon), ("hauteur", hauteur)):
        if not isinstance(val, (int, float)) or isinstance(val, bool) \
                or val != val or val <= 0:
            raise ValueError(f"{nom} : un nombre fini > 0 est attendu")
    if not isinstance(jeu, (int, float)) or jeu != jeu or jeu < 0:
        raise ValueError("jeu : un nombre ≥ 0 est attendu")
    n = tuple(float(c) for c in normale)
    ln = math.sqrt(sum(c * c for c in n))
    if ln < 1e-12:
        raise ValueError("direction : la normale du plan ne peut pas être nulle")
    n = tuple(c / ln for c in n)
    o = tuple(float(c) for c in point)
    u, v = _base(n)

    doc, binc = lire_glb(data)
    refus_compression(doc, "la pose d'un connecteur")
    nodes = _l(doc, "nodes")
    for i in noeuds:
        if not (0 <= int(i) < len(nodes)) or "mesh" not in nodes[int(i)]:
            raise ValueError(f"nœud {i} : aucun maillage à connecter")
    tampon, pieces = bytearray(binc), []

    for rang, i in enumerate((int(noeuds[0]), int(noeuds[1]))):
        male = rang == 0
        r = float(rayon) if male else float(rayon) + float(jeu)
        h = float(hauteur) if male else float(hauteur) + float(jeu)
        poly = section(type_, r)
        # le mâle POUSSE dans le sens de la normale ; la femelle CREUSE dans le
        # sens opposé — les deux prismes se font face, jeu compris
        pts, tris = _prisme(poly, o, u, v, n, h, vers_le_haut=male)
        mesh = _l(doc, "meshes")[nodes[i]["mesh"]]
        prim = next(p for p in mesh["primitives"]
                    if p.get("mode", 4) == 4 and "POSITION" in (p.get("attributes") or {}))
        pos = [tuple(p) for p in
               _lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
        idx = ([t[0] for t in _lire_accesseur(doc, binc, prim["indices"])]
               if "indices" in prim else list(range(len(pos))))
        anciens = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]

        retires = 0
        if not male:
            # la femelle RETIRE d'abord les facettes du capuchon qui sont sous
            # la section : sans quoi le prisme creusé resterait bouché par le
            # couvercle plat que le couteau vient de poser
            def dedans(s):
                d = (pos[s][0] - o[0], pos[s][1] - o[1], pos[s][2] - o[2])
                du = sum(d[c] * u[c] for c in range(3))
                dv = sum(d[c] * v[c] for c in range(3))
                return math.hypot(du, dv) <= r
            gardes = [t for t in anciens if not all(dedans(s) for s in t)]
            retires = len(anciens) - len(gardes)
            if not retires:
                raise ValueError(
                    "aucune facette du capuchon sous le connecteur — le rayon "
                    "est plus petit qu'une facette de la section. Augmente le "
                    "rayon.")
            anciens = gardes

        n0 = len(pos)
        tous = list(pos) + pts
        plat = [c for p in tous for c in p]
        mini = [min(p[c] for p in tous) for c in range(3)]
        maxi = [max(p[c] for p in tous) for c in range(3)]
        prim["attributes"] = {"POSITION": _ajouter_flottants(
            doc, tampon, plat, 3, mini, maxi)}
        prim["indices"] = _ajouter_indices(
            doc, tampon, anciens + [(a + n0, b + n0, c + n0) for (a, b, c) in tris])
        pieces.append({"noeud": i, "role": "male" if male else "femelle",
                       "nom": nodes[i].get("name") or f"nœud {i}",
                       "rayon": r, "hauteur": h,
                       "ajoutes": len(tris), "retires": retires})

    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, _ = _extraire_doc(doc, bytes(tampon), list(range(len(nodes))))
    return ecrire_glb(out, neuf), {
        "type": type_, "rayon": float(rayon), "hauteur": float(hauteur),
        "jeu": float(jeu), "plan": {"point": list(o), "normale": list(n),
                                    "repere": "monde"},
        "pieces": pieces}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "teton or section_d_un or poser_refuse"` → `3 passed`.

- [ ] **Step 4 : la route — le plan vient de la FICHE, pas du corps**

```python
@router.post("/etabli/connecteur")
async def etabli_connecteur(body: dict):
    """Pose un connecteur entre les deux moitiés d'une coupe.

    LE PLAN N'EST PAS DANS LE CORPS, ET C'EST LE POINT : il est lu dans la
    fiche de la version visée (`source.plan`, écrite par `/etabli/couper`).
    Le redemander à la page inviterait un plan LÉGÈREMENT différent de celui
    qui a coupé — un connecteur posé de travers, sans que rien ne grince."""
    from app.services import mesh_connect, mesh_report
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "connecteur")
    v = int(body["version"])
    nom = "model.glb" if v <= 1 else f"model.v{v}.glb"
    fiches = {str(f.get("file")): f
              for f in (mesh_report.read_registry(job).get("entries") or [])
              if isinstance(f, dict)}
    src = (fiches.get(nom) or {}).get("source") or {}
    plan = src.get("plan") if isinstance(src, dict) else None
    if not isinstance(plan, dict) or "point" not in plan or "normale" not in plan:
        raise HTTPException(400, f"connecteur : la version {v} n'est pas née "
                                 "d'une coupe (aucun plan dans sa fiche) — pose "
                                 "un connecteur sur la version que le couteau "
                                 "vient d'écrire")
    noeuds = body.get("noeuds")
    if not isinstance(noeuds, list) or len(noeuds) != 2 \
            or any(not _etabli_entier(x) or x < 0 for x in noeuds):
        raise HTTPException(400, "connecteur : `noeuds` attend exactement deux "
                                 "index de nœud (les deux moitiés)")
    echelle = body.get("echelle")
    if not _etabli_nombre(echelle) or echelle <= 0:
        raise HTTPException(400, "connecteur : `echelle` attend un nombre > 0")
    mm = {}
    for cle, defaut in (("rayon_mm", None), ("hauteur_mm", None), ("jeu_mm", 0.2)):
        val = body.get(cle, defaut)
        if not _etabli_nombre(val) or val < 0 or (val == 0 and cle != "jeu_mm"):
            raise HTTPException(400, f"connecteur : `{cle}` attend un nombre "
                                     f"{'≥ 0' if cle == 'jeu_mm' else '> 0'}")
        mm[cle] = float(val)
    try:
        sortie, rapport = await asyncio.to_thread(
            mesh_connect.poser, data, noeuds, plan["point"], plan["normale"],
            str(body.get("type", "teton")),
            mm["rayon_mm"] / float(echelle), mm["hauteur_mm"] / float(echelle),
            mm["jeu_mm"] / float(echelle))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "connecteur",
                          {"depuis": depuis, "echelle": float(echelle), **mm,
                           **rapport})
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k route_connecteur` → `1 passed`.

- [ ] **Step 5 : la page — dans la barre du couteau, APRÈS la coupe**

`ROUTES` gagne `connecteur: "/api/etabli/connecteur"` ; `LIBELLES_ATTENTE` gagne
`connecteur: (t) => \`connecteur ${t.charge.type} ⌀ ${2 * t.charge.rayon_mm} mm\``.

Dans `index.html`, à la suite de `#btnCouper` dans `#couteauBarre` :

```html
            <select class="outil-sel" id="couteauConnecteur"
                    title="posé APRÈS la coupe, sur la version que le couteau vient d'écrire">
              <option value="">sans connecteur</option>
              <option value="teton">téton</option>
              <option value="cheville">cheville</option>
              <option value="aronde">queue d'aronde</option>
            </select>
```

Dans `etabli.js`, `COUTEAU` gagne `connecteur: ""` dans sa déclaration, le `change` du `<select>` l'écrit, et `confirmerCoupe()` — après le bilan de la coupe — enchaîne :

```js
  /* LE CONNECTEUR VIENT APRÈS, sur la version que la coupe vient d'écrire, et
     il lit SON plan dans la fiche : la page n'a rien à renvoyer. Deux versions
     donc, pas une — et c'est juste : couper et connecter sont deux gestes, et
     la lignée doit pouvoir revenir entre les deux. */
  if (COUTEAU.connecteur && bilan && bilan.derniere) {
    if (!enMillimetres()) {
      direRefus("connecteur ignoré : pose une taille cible — un téton se donne en millimètres");
      return;
    }
    const pieces = (bilan.derniere.source.pieces || []);
    const cotes = pieces[0] && pieces[0].cotes;
    if (!cotes || !cotes.a || !cotes.b) {
      direRefus("connecteur ignoré : la coupe n'a pas produit deux moitiés");
      return;
    }
    const b2 = await ecrireSeule("connecteur", {
      noeuds: [cotes.a.noeud_apres, cotes.b.noeud_apres],
      type: COUTEAU.connecteur, rayon_mm: RAYON_CONNECTEUR_MM,
      hauteur_mm: HAUTEUR_CONNECTEUR_MM, jeu_mm: JEU_CONNECTEUR_MM,
      echelle: REP.echelle });
    if (b2) {
      direAvis(`connecteur ${COUTEAU.connecteur} posé (version ${b2.derniere.version}) — `
        + `mâle sur « ${b2.derniere.source.pieces[0].nom} », femelle sur `
        + `« ${b2.derniere.source.pieces[1].nom} », jeu ${JEU_CONNECTEUR_MM} mm`);
    }
  }
```

avec, près de `PAS_ROTATION` :

```js
/* Les cotes du connecteur, en millimètres. Elles ne sont pas réglables à
   l'écran, et c'est délibéré : trois champs de plus dans la barre du couteau
   pour trois nombres que personne ne sait choisir au premier essai. Le JEU est
   le seul qui compte vraiment, et 0,2 mm est un ajustement serré — la base de
   connaissance Prusa donne 0,3 mm pour des pièces MOBILES (vérifiée le
   03/09/2026), ce qui n'est pas le cas d'un assemblage collé. */
const RAYON_CONNECTEUR_MM = 3;
const HAUTEUR_CONNECTEUR_MM = 4;
const JEU_CONNECTEUR_MM = 0.2;
```

- [ ] **Step 6 : le miroir**

```python
def test_le_connecteur_vient_APRES_la_coupe_et_lit_les_noeuds_de_la_fiche():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'connecteur: "/api/etabli/connecteur"' in js
    assert "const JEU_CONNECTEUR_MM = 0.2;" in js
    assert 'connecteur: ""' in js.split("const COUTEAU = {", 1)[1].split("};", 1)[0]
    conf = _fonction_etabli_async("confirmerCoupe")
    assert conf.index('ecrireSeule("couper"') < conf.index('ecrireSeule("connecteur"') \
        if 'ecrireSeule("couper"' in conf else 'ecrireSeule("connecteur"' in conf
    assert "cotes.a.noeud_apres" in conf and "cotes.b.noeud_apres" in conf
    assert "enMillimetres()" in conf
    # aucun point ni normale renvoyés : le plan vient de la fiche
    bloc = conf.split('ecrireSeule("connecteur"', 1)[1].split("});", 1)[0]
    assert "point" not in bloc and "normale" not in bloc
    assert 'id="couteauConnecteur"' in _lire("etabli/index.html")
    for t in ("teton", "cheville", "aronde"):
        assert f'value="{t}"' in _lire("etabli/index.html")
```

*(Le banc importe `_fonction_etabli_async`, recopié de `test_etabli_canevas.py` avec les autres aides.)*

Run : `python -m pytest tests/test_etabli_outils_page.py -q -k connecteur` → `1 passed`
Run : `python -m pytest tests/test_etabli_canevas.py -q -k "REFUSE_sans_piece or outils_vivent"` → verts.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/mesh_connect.py backend/app/api/routes.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js frontend/etabli/index.html
git commit -m 'etabli : connecteurs du couteau - teton, cheville, queue d aronde' -m 'Posés APRÈS la coupe, sur la version que le couteau vient d écrire, et le plan est relu dans SA fiche : le redemander à la page inviterait un plan légèrement différent, donc un connecteur de travers. Une seule section pour trois types — le trapèze de l aronde est plus large au fond, et c est cela seul qui retient. Le jeu est porté par la femelle, jamais par le mâle.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 18 : D4 — les booléens : d'abord le CHOIX D'ALGORITHME, mesuré, et sans promesse

**Files :** modifier `backend/tests/mesure_etabli_outils.py` ; créer `backend/app/services/mesh_boolean.py` ; modifier `backend/app/api/routes.py`, `frontend/etabli/etabli.js`, `frontend/etabli/index.html` ; tests dans les deux bancs neufs.

> **AUCUNE PROMESSE N'EST FAITE ICI.** R10f D4 dit « algorithme à choisir et mesurer ; le plan dira son coût en temps sur des maillages de 50 000 triangles ». Cette tâche commence donc par une MESURE dont le résultat peut refuser le reste. Si le budget tombe, l'étape 3 le dit et l'opération se livre bornée — pas élargie.

- [ ] **Step 1 : la table des candidats, et ce que chacun coûterait**

| Candidat | Ce qu'il faut écrire | Coût mémoire | Coût temps attendu (2 × 50 000 tris) | Ce qui le disqualifie ou non |
|---|---|---|---|---|
| **BSP** (arbre de partition binaire, façon `csg.js`) | construction récursive d'un arbre par plan de triangle, découpe des polygones à l'insertion, inversion, union des arbres | l'arbre porte O(n log n) à O(n²) polygones sur des maillages non convexes | l'arbre se construit en O(n log n) triangles mais chaque insertion DÉCOUPE : la littérature et l'usage donnent un facteur 3 à 10 sur le nombre de polygones. En Python pur, ~10⁶ opérations de plan par côté | robuste et bien connu, mais son explosion de polygones n'est pas bornée : un maillage organique de 50 000 triangles peut en produire plusieurs centaines de milliers, et le temps devient imprévisible. **Sa borne n'est pas mesurable à l'avance**, ce qui est disqualifiant pour une route qui doit dire son budget. |
| **Découpe par plan itérée** (le couteau, en boucle sur les triangles de B) | réutilise `mesh_cut._decouper_primitive` (déjà écrit, déjà éprouvé, déjà muté 45 fois) + une classification dedans/dehors | O(n) par passe | 50 000 passes de découpe sur 50 000 triangles = O(n²) — **hors budget de plusieurs ordres de grandeur**, même avec une grille | l'idée est séduisante parce que le code existe ; le compte la tue. Écartée par le calcul, pas par le goût. |
| **Voxels** (grille d'occupation, opération booléenne sur les cellules, puis marching cubes) | rastérisation des deux maillages, ET/OU/moins par cellule, extraction de surface | 128³ = 2 097 152 cellules ; en Python, un `bytearray` de 2 Mio tient, une liste de booléens non | rastériser 50 000 triangles dans 128³ est linéaire en triangles × cellules touchées ; marching cubes est linéaire en cellules | **borné par construction** : le coût ne dépend PAS de la complexité de l'intersection, seulement de la résolution choisie. En revanche il ARRONDIT — une face plane devient un escalier de la taille d'une cellule, et il faut le dire. |
| **Classification par parité + découpe locale** (le retenu, sous réserve de mesure) | grille de hachage des triangles de B ; pour chaque triangle de A, ne le découper que par les plans des triangles de B dont la boîte le recoupe ; classer chaque morceau par lancer de rayon (parité des traversées) | O(n) + O(paires proches) | linéaire hors zone de contact ; quadratique SEULEMENT dans la zone d'intersection | **exact** (aucun arrondi), et son coût suit la TAILLE DE L'INTERSECTION, pas celle des modèles. C'est ce que la mesure de l'étape 2 doit confirmer ou infirmer. |

- [ ] **Step 2 : la mesure qui tranche**

Ajouter à `mesure_etabli_outils.py` :

```python
    elif quoi == "booleen":
        import struct as _s
        from app.services import gltf_builder, mesh_boolean, print3d
        # deux tores de 50 176 triangles chacun, décalés pour s'intersecter sur
        # environ un quart de leur volume — la géométrie la plus dure de la
        # famille (courbure partout, aucune face plane à faire tomber)
        from test_mesh_optimize import build_torus_glb
        a = pathlib.Path(_tmp, "a.glb"); build_torus_glb(a, 158, 158)
        b = pathlib.Path(_tmp, "b.glb"); build_torus_glb(b, 158, 158, R=2.0, r=0.7)
        ta = print3d.lire_glb_triangles(a.read_bytes())
        tb = [tuple(tuple(c + (1.4 if i == 0 else 0.0) for i, c in enumerate(p))
                    for p in t) for t in tb_src] if False else \
             [tuple(tuple(p[i] + (1.4 if i == 0 else 0.0) for i in range(3))
                    for p in t) for t in print3d.lire_glb_triangles(b.read_bytes())]
        print(f"A : {len(ta)} tris, B : {len(tb)} tris")
        for op in ("union", "difference", "intersection"):
            chrono(f"{op} 50k x 50k", lambda o=op: mesh_boolean.operer(ta, tb, o))
```

Run : `python tests/mesure_etabli_outils.py booleen`
Expected : `ModuleNotFoundError: No module named 'app.services.mesh_boolean'`.

**LE BUDGET, ET LA RÈGLE DE DÉCISION, fixés ici avant d'écrire une ligne d'algorithme :**

- si `difference 50k x 50k` tient **sous 60 s** → l'opération se livre avec `MAX_TRIS = 50_000` par opérande et le message de refus au-delà ;
- si elle tient sous 300 s mais pas sous 60 → l'opération se livre avec `MAX_TRIS = 20_000`, et la mesure à 20 000 est refaite et notée ;
- si elle dépasse 300 s à 20 000 triangles → **la tâche s'arrête là**. On commite la mesure et le tableau de l'étape 1 dans le plan, on écrit la ligne dans « Écarté » (« D4 mesuré le JJ/MM, hors budget en Python pur, à reprendre le jour où une roue native est embarquée »), et on ne livre AUCUN bouton. Un booléen qui tourne trois minutes derrière un bouton est un bouton qui ment.

- [ ] **Step 3 : les tests (rouge), écrits AVANT de savoir si le budget passe**

```python
def _cube_tris(cx=0.0, cote=2.0):
    """Un cube en triangles, sans passer par un GLB : les booléens travaillent
    sur des TRIANGLES MONDE, pas sur un document."""
    h = cote / 2
    s = [(cx - h, -h, -h), (cx + h, -h, -h), (cx + h, h, -h), (cx - h, h, -h),
         (cx - h, -h, h), (cx + h, -h, h), (cx + h, h, h), (cx - h, h, h)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [(s[a], s[b], s[c]) for (a, b, c) in f]

def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)

def test_les_trois_booleens_donnent_le_VOLUME_attendu_sur_deux_cubes():
    """Deux cubes d'arête 2, décalés de 1 sur x : l'intersection est une boîte
    1x2x2 (volume 4), l'union 12, la différence 4. Le volume signé est le seul
    juge qui ne se laisse pas tromper par un triangle en trop."""
    from app.services import mesh_boolean as MB
    a, b = _cube_tris(0.0), _cube_tris(1.0)
    assert abs(_volume(MB.operer(a, b, "intersection")) - 4.0) < 1e-6
    assert abs(_volume(MB.operer(a, b, "union")) - 12.0) < 1e-6
    assert abs(_volume(MB.operer(a, b, "difference")) - 4.0) < 1e-6
    # la différence n'est PAS commutative, et le banc le prouve
    assert abs(_volume(MB.operer(b, a, "difference")) - 4.0) < 1e-6
    assert MB.operer(a, b, "difference") != MB.operer(b, a, "difference")

def test_deux_solides_disjoints_ne_font_pas_semblant():
    from app.services import mesh_boolean as MB
    a, b = _cube_tris(0.0), _cube_tris(10.0)
    assert abs(_volume(MB.operer(a, b, "union")) - 16.0) < 1e-6
    assert MB.operer(a, b, "intersection") == []
    assert abs(_volume(MB.operer(a, b, "difference")) - 8.0) < 1e-6

def test_le_booleen_refuse_au_dela_de_son_budget_MESURE_et_le_dit():
    import pytest as _p
    from app.services import mesh_boolean as MB
    gros = _cube_tris() * (MB.MAX_TRIS // 12 + 2)
    with _p.raises(ValueError, match="budget"):
        MB.operer(gros, _cube_tris(1.0), "union")
    with _p.raises(ValueError, match="operation"):
        MB.operer(_cube_tris(), _cube_tris(1.0), "xor")

def test_la_route_booleen_ecrit_une_version_et_juge_son_corps():
    d = _job("job_bool", _cube_et_sol()); c = _client()
    r = c.post("/api/etabli/booleen", json={"job": "job_bool", "version": 1,
                                            "a": [0], "b": [1], "operation": "union"})
    assert r.status_code == 200 and (d / "model.v2.glb").is_file()
    src = r.json()["source"]
    assert src["operation"] == "booleen" and src["booleen"] == "union"
    assert src["triangles_a"] > 0 and src["triangles_b"] > 0 and src["triangles"] > 0
    for corps in ({"a": [0], "b": [0], "operation": "union"},
                  {"a": [], "b": [1], "operation": "union"},
                  {"a": [0], "b": [1], "operation": "xor"}):
        assert c.post("/api/etabli/booleen",
                      json={"job": "job_bool", "version": 1, **corps}).status_code == 400
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "booleen or disjoints"` → `4 failed`.

- [ ] **Step 4 : `backend/app/services/mesh_boolean.py` — classification par parité, découpe locale**

```python
# -*- coding: utf-8 -*-
"""Union, différence, intersection sur des triangles MONDE — stdlib pure.

L'ALGORITHME RETENU, et le tableau des candidats écartés vit dans le plan
(tâche 18, étape 1) : découpe LOCALE puis classification par PARITÉ.

  1. les triangles de B sont rangés dans une grille de hachage à la maille de
     leur taille moyenne ;
  2. chaque triangle de A n'est découpé QUE par les plans des triangles de B
     dont la boîte recoupe la sienne — hors de la zone de contact, un triangle
     n'est jamais touché, et c'est là que le coût reste linéaire ;
  3. chaque morceau est classé dedans/dehors de l'autre solide par LANCER DE
     RAYON : on compte les traversées d'un rayon partant du barycentre. Impair
     = dedans. Le rayon est tiré dans une direction pseudo-aléatoire fixe (le
     même à chaque appel : un résultat qui change d'une exécution à l'autre est
     pire qu'un résultat faux) ;
  4. l'opération choisit quels morceaux garder, et de quel côté ils regardent.

CE QU'IL NE FAIT PAS, ET C'EST DIT : il ne recoud pas les sommets en T le long
de la couture (les morceaux se touchent bord à bord sans partager d'index).
Le maillage est donc étanche GÉOMÉTRIQUEMENT mais non-manifold au sens des
index — exactement ce que `mesh_report` sait mesurer et `mesh_repair.souder`
sait refermer. La route le dit dans son compte rendu, et l'UI propose la
réparation en un clic derrière.

LE BUDGET EST UNE CONSTANTE, PAS UNE ESPÉRANCE : `MAX_TRIS` vient de la mesure
de l'étape 2 du plan, sur deux tores. Au-delà, on refuse en nommant le chiffre.
"""
from __future__ import annotations

import math

OPERATIONS = ("union", "difference", "intersection")
MAX_TRIS = 50_000          # ← le chiffre RETENU par la mesure de l'étape 2
_EPS = 1e-9
# direction de lancer fixe, choisie non alignée sur les axes pour ne pas
# raser les faces d'une boîte : un rayon parallèle à une face compte mal
_RAYON = (0.5773502691896258, 0.5773502691896257, 0.5773502691896256)


def _boite(t):
    return (min(p[0] for p in t), min(p[1] for p in t), min(p[2] for p in t),
            max(p[0] for p in t), max(p[1] for p in t), max(p[2] for p in t))


def _normale(t):
    a, b, c = t
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])


def _traverse(o, d, t):
    """Möller–Trumbore : le rayon (o, d) coupe-t-il le triangle t devant lui ?"""
    a, b, c = t
    e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    h = (d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2],
         d[0] * e2[1] - d[1] * e2[0])
    det = sum(e1[i] * h[i] for i in range(3))
    if abs(det) < _EPS:
        return False
    inv = 1.0 / det
    s = (o[0] - a[0], o[1] - a[1], o[2] - a[2])
    u = inv * sum(s[i] * h[i] for i in range(3))
    if u < 0.0 or u > 1.0:
        return False
    q = (s[1] * e1[2] - s[2] * e1[1], s[2] * e1[0] - s[0] * e1[2],
         s[0] * e1[1] - s[1] * e1[0])
    v = inv * sum(d[i] * q[i] for i in range(3))
    if v < 0.0 or u + v > 1.0:
        return False
    return inv * sum(e2[i] * q[i] for i in range(3)) > _EPS


def _dedans(p, autres) -> bool:
    """Parité des traversées depuis `p` dans la direction fixe."""
    return sum(1 for t in autres if _traverse(p, _RAYON, t)) % 2 == 1


def _couper_par_plan(t, point, n):
    """Le triangle `t` coupé par le plan (point, n) : rend la liste des
    morceaux, orientation préservée. Zéro découpe quand il ne traverse pas."""
    d = [sum((p[i] - point[i]) * n[i] for i in range(3)) for p in t]
    if all(x >= -_EPS for x in d) or all(x <= _EPS for x in d):
        return [t]
    out, m = [], []
    for k in range(3):
        a, b = t[k], t[(k + 1) % 3]
        da, db = d[k], d[(k + 1) % 3]
        m.append((a, da))
        if (da > _EPS) != (db > _EPS) and abs(da - db) > _EPS:
            f = da / (da - db)
            m.append((tuple(a[i] + (b[i] - a[i]) * f for i in range(3)), 0.0))
    for cote in (1, -1):
        poly = [p for (p, x) in m if x * cote > -_EPS]
        for k in range(1, len(poly) - 1):
            tri = (poly[0], poly[k], poly[k + 1])
            if abs(sum(c * c for c in _normale(tri))) > _EPS:
                out.append(tri)
    return out or [t]


def _grille(tris):
    """Grille de hachage à la maille de la diagonale moyenne des boîtes."""
    if not tris:
        return {}, 1.0
    boites = [_boite(t) for t in tris]
    maille = max(1e-6, sum(
        max(b[3] - b[0], b[4] - b[1], b[5] - b[2]) for b in boites) / len(boites))
    g: dict = {}
    for t, b in zip(tris, boites):
        for i in range(int(math.floor(b[0] / maille)), int(math.floor(b[3] / maille)) + 1):
            for j in range(int(math.floor(b[1] / maille)), int(math.floor(b[4] / maille)) + 1):
                for k in range(int(math.floor(b[2] / maille)), int(math.floor(b[5] / maille)) + 1):
                    g.setdefault((i, j, k), []).append(t)
    return g, maille


def _voisins(g, maille, t):
    b, vus = _boite(t), []
    ids = set()
    for i in range(int(math.floor(b[0] / maille)), int(math.floor(b[3] / maille)) + 1):
        for j in range(int(math.floor(b[1] / maille)), int(math.floor(b[4] / maille)) + 1):
            for k in range(int(math.floor(b[2] / maille)), int(math.floor(b[5] / maille)) + 1):
                for u in g.get((i, j, k), ()):
                    if id(u) not in ids:
                        ids.add(id(u)); vus.append(u)
    return vus


def _decouper_contre(tris, autres):
    g, maille = _grille(autres)
    out = []
    for t in tris:
        morceaux = [t]
        for u in _voisins(g, maille, t):
            n = _normale(u)
            if abs(sum(c * c for c in n)) < _EPS:
                continue
            suivant = []
            for m in morceaux:
                suivant.extend(_couper_par_plan(m, u[0], n))
            morceaux = suivant
            if len(morceaux) > 64:      # garde-fou : un triangle qui explose
                break                    # n'ajoute plus de précision utile
        out.extend(morceaux)
    return out


def _retourner(t):
    return (t[0], t[2], t[1])


def operer(a, b, operation: str):
    """`a` et `b` sont des listes de triangles ((x,y,z)×3) en coordonnées
    MONDE ; rend la liste de triangles du résultat."""
    if operation not in OPERATIONS:
        raise ValueError(f"operation « {operation} » — "
                         f"{', '.join(OPERATIONS)} sont attendues")
    if len(a) > MAX_TRIS or len(b) > MAX_TRIS:
        raise ValueError(
            f"{max(len(a), len(b))} triangles — le budget mesuré du booléen est "
            f"de {MAX_TRIS} triangles par opérande. Décime d'abord "
            "(bouton « Décimer »), puis recommence.")
    ca = _decouper_contre(a, b)
    cb = _decouper_contre(b, a)
    bary = lambda t: tuple(sum(p[i] for p in t) / 3.0 for i in range(3))
    a_dedans_b = [t for t in ca if _dedans(bary(t), b)]
    a_dehors_b = [t for t in ca if t not in a_dedans_b]
    b_dedans_a = [t for t in cb if _dedans(bary(t), a)]
    b_dehors_a = [t for t in cb if t not in b_dedans_a]
    if operation == "union":
        return a_dehors_b + b_dehors_a
    if operation == "intersection":
        return a_dedans_b + b_dedans_a
    # différence A − B : la peau de A hors de B, plus la peau de B dans A,
    # RETOURNÉE (elle devient la paroi du creux)
    return a_dehors_b + [_retourner(t) for t in b_dedans_a]
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "booleen or disjoints"` → `3 passed, 1 failed` (la route manque)
Run : `python tests/mesure_etabli_outils.py booleen` → **noter les trois temps dans le message de commit, et appliquer la règle de décision de l'étape 2**.

- [ ] **Step 5 : la route et le bouton**

```python
@router.post("/etabli/booleen")
async def etabli_booleen(body: dict):
    """Union / différence / intersection entre deux groupes de nœuds de la MÊME
    version. Le résultat remplace les deux groupes par un nœud unique.

    LE COMPTE RENDU DIT LA COUTURE : le résultat est étanche géométriquement
    mais ses morceaux ne partagent pas leurs sommets (voir `mesh_boolean`).
    L'UI propose « Réparer en un clic » derrière — c'est `souder` qui referme."""
    from app.services import mesh_boolean, print3d
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "booléen")
    a, b = body.get("a"), body.get("b")
    for nom, v in (("a", a), ("b", b)):
        if not isinstance(v, list) or not v \
                or any(not _etabli_entier(x) or x < 0 for x in v):
            raise HTTPException(400, f"booléen : `{nom}` attend une liste non "
                                     "vide d'index de nœud")
    if set(a) & set(b):
        raise HTTPException(400, "booléen : un même nœud ne peut pas être des "
                                 "deux côtés de l'opération")
    op = str(body.get("operation", "union"))
    if op not in mesh_boolean.OPERATIONS:
        raise HTTPException(400, f"booléen : operation « {op} » — "
                                 f"{', '.join(mesh_boolean.OPERATIONS)}")
    try:
        ta = await asyncio.to_thread(print3d.lire_glb_triangles, data, a)
        tb = await asyncio.to_thread(print3d.lire_glb_triangles, data, b)
        tris = await asyncio.to_thread(mesh_boolean.operer, ta, tb, op)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not tris:
        raise HTTPException(400, f"booléen : « {op} » ne laisse aucune matière "
                                 "— les deux pièces ne se touchent peut-être pas")
    sortie = await asyncio.to_thread(print3d.glb_de_triangles, tris, "booleen")
    return _etabli_ecrire(job, sortie, "booleen",
                          {"depuis": depuis, "booleen": op, "a": list(a),
                           "b": list(b), "triangles_a": len(ta),
                           "triangles_b": len(tb), "triangles": len(tris),
                           "couture": "sommets non soudés — passe « Réparer en "
                                      "un clic » pour refermer les index"})
```

Deux ajouts à `print3d.py`, tous deux nommés dans les tests ci-dessus :
`lire_glb_triangles(data, noeuds=None)` gagne un filtre facultatif sur les index de nœud (`if noeuds is not None and i not in set(noeuds): return` dans `_noeud`) ; et `glb_de_triangles(tris, nom)` compose un GLB minimal à partir de triangles monde — le chemin inverse de `lire_glb_triangles`, écrit avec `mesh_edit.ecrire_glb` comme partout ailleurs.

Dans `etabli.js` : `ROUTES` gagne `booleen: "/api/etabli/booleen"` ; `LIBELLES_ATTENTE` gagne `booleen: (t) => \`${t.charge.operation} de ${t.charge.a.length} et ${t.charge.b.length} pièce(s)\`` ; le panneau Parties gagne, sous `#btnSeparer` :

```js
      <div class="bool-barre">
        <select id="pBoolOp">
          <option value="union">union</option>
          <option value="difference">différence (A − B)</option>
          <option value="intersection">intersection</option>
        </select>
        <button id="btnBoolA">A = sélection</button>
        <button id="btnBoolB">B = sélection</button>
        <button id="btnBooleen">Appliquer</button>
        <span class="bool-etat" id="boolEtat"></span>
      </div>
```

avec `const BOOL = { a: [], b: [] };` déclaré à côté de `MESURE`, les deux boutons qui y rangent `noeudsRetenus().noeuds`, `#boolEtat` qui dit « A : 2 · B : 1 », et :

```js
  $("#btnBooleen").addEventListener("click", async () => {
    if (!BOOL.a.length || !BOOL.b.length) {
      direRefus("choisis A puis B : un booléen a deux opérandes"); return;
    }
    const bilan = await ecrireSeule("booleen",
      { a: BOOL.a, b: BOOL.b, operation: $("#pBoolOp").value });
    if (!bilan) return;
    BOOL.a = []; BOOL.b = []; rendreParties();
    const src = bilan.derniere.source;
    direAvis(`${src.booleen} écrite (version ${bilan.derniere.version}) : `
      + `${src.triangles_a} + ${src.triangles_b} → ${src.triangles} triangles — `
      + `${src.couture}`);
  });
```

- [ ] **Step 6 : les miroirs, puis vert**

```python
def test_le_booleen_a_DEUX_operandes_nommes_et_dit_sa_couture():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'booleen: "/api/etabli/booleen"' in js
    assert "const BOOL = { a: [], b: [] };" in js
    p = _fonction_etabli("rendreParties")
    assert 'id="pBoolOp"' in p and 'id="btnBoolA"' in p and 'id="btnBoolB"' in p
    for o in ("union", "difference", "intersection"):
        assert f'value="{o}"' in p
    bloc = code.split('$("#btnBooleen").addEventListener', 1)[1].split("  });", 1)[0]
    assert "BOOL.a.length" in bloc and "BOOL.b.length" in bloc
    assert "src.couture" in bloc          # la limite est RÉPÉTÉE à l'écran
    assert "booleen" in _table_js("etabli/etabli.js", "LIBELLES_ATTENTE")

def test_les_operations_du_select_sont_celles_du_service():
    from app.services import mesh_boolean
    p = _fonction_etabli("rendreParties")
    for o in mesh_boolean.OPERATIONS:
        assert f'value="{o}"' in p, o
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "booleen or disjoints"` → `4 passed`
Run : `python -m pytest tests/test_etabli_outils_page.py -q -k booleen` → `2 passed`
Run : `python -m pytest tests/test_print3d.py -q` → vert (le filtre `noeuds` est facultatif)

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/mesh_boolean.py backend/app/services/print3d.py backend/app/api/routes.py backend/tests/mesure_etabli_outils.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js
git commit -m 'etabli : booleens - classification par parite et decoupe locale, budget mesure' -m 'Quatre candidats comparés dans le plan avant d écrire (BSP, découpe par plan itérée, voxels, parité) ; les trois premiers écartés par le calcul, pas par le goût. Le retenu est EXACT et son coût suit la taille de l intersection, pas celle des modèles. Temps mesurés sur deux tores de 50 176 triangles, reportés ici, et MAX_TRIS en vient. La couture non soudée est dite dans la fiche ET répétée à l écran : c est réparable en un clic, ce n est pas un secret.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 19 : D5 — auto-orient : trois poses proposées, classées, et l'utilisateur tranche

**Files :** créer `backend/app/services/orient.py` ; modifier `backend/app/api/routes.py`, `frontend/etabli/etabli.js`, `frontend/etabli/index.html`, `backend/tests/mesure_etabli_outils.py` ; tests dans les deux bancs neufs.

> Référence vérifiée le 03/09/2026 (OrcaSlicer wiki, *prepare_auto_orient*) : « analyzes the mesh geometry to extract face normals and areas », quatre critères — *overhang area, bottom contact, support interface, contour complexity* —, « selects the orientation with the lowest unprintability score », et l'avertissement, mot pour mot : « **Auto Orientation may not always find the best orientation for complex models. Always review the suggested orientation.** » Le nôtre PROPOSE et n'applique rien tout seul ; le **pas 4 du chapitre 21** (écrit en tâche 14) répète l'avertissement en français.

- [ ] **Step 1 : la mesure d'abord**

```python
    elif quoi == "orienter":
        from app.services import orient
        r = chrono("orienter tore 100k", lambda: orient.candidats(data, None))
        print(f"   -> {len(r['candidats'])} poses, meilleure "
              f"{r['candidats'][0]['score']:.4f}")
        if REEL.is_file():
            chrono("orienter reel 144k", lambda: orient.candidats(REEL.read_bytes(), None))
```

Run : `python tests/mesure_etabli_outils.py orienter`
Expected : `ModuleNotFoundError`. **Budget fixé ici : 100 352 triangles évalués contre au plus 64 poses en moins de 30 s.** Le coût est `poses × triangles` de produits scalaires ; les poses viennent d'un regroupement des normales par direction quantifiée, donc leur nombre est BORNÉ (`MAX_POSES`) quelle que soit la finesse du maillage — c'est ce qui rend le budget prévisible.

- [ ] **Step 2 : les tests (rouge)**

```python
def test_orienter_un_cube_propose_ses_faces_et_les_classe():
    from app.services import orient
    r = orient.candidats(_cube(), None)
    assert 1 <= len(r["candidats"]) <= orient.MAX_POSES
    c0 = r["candidats"][0]
    assert set(c0) == {"bas", "contact", "surplomb", "contour", "score", "rotation"}
    # un cube pose sur une face : contact maximal, aucun surplomb
    assert abs(c0["surplomb"]) < 1e-9
    assert abs(abs(c0["bas"][0]) + abs(c0["bas"][1]) + abs(c0["bas"][2]) - 1.0) < 1e-6
    # les scores sont CROISSANTS : le meilleur est le premier, et c'est dit
    scores = [c["score"] for c in r["candidats"]]
    assert scores == sorted(scores)
    assert r["seuil_surplomb"] == 45.0

def test_orienter_prefere_la_face_LARGE_sur_une_dalle():
    """Une dalle 4 x 4 x 0,5 : posée à plat, elle a 16 d'appui ; sur la tranche,
    2. Le score doit préférer la première — c'est le sens du critère
    « bottom contact » du wiki OrcaSlicer, vérifié le 03/09."""
    from app.services import orient
    r = orient.candidats(_dalle(), None)
    meilleur = r["candidats"][0]
    assert meilleur["contact"] > 10.0
    assert abs(meilleur["bas"][1]) > 0.9        # la dalle repose sur ±Y

def test_orienter_refuse_ce_qu_il_ne_sait_pas_lire():
    import pytest as _p
    from app.services import mesh_edit, orient
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with _p.raises(ValueError, match="draco"):
        orient.candidats(mesh_edit.ecrire_glb(doc, binc), None)
    with _p.raises(ValueError, match="aucun triangle"):
        orient.candidats(_cube(), [999])

def test_la_route_orienter_PROPOSE_sans_ecrire_et_repete_l_avertissement():
    d = _job("job_or", _cube()); c = _client()
    r = c.get("/api/etabli/orienter?job=job_or&version=1")
    assert r.status_code == 200
    corps = r.json()
    assert len(corps["candidats"]) >= 1 and "avertissement" in corps
    assert "pas toujours" in corps["avertissement"]
    assert not (d / "model.v2.glb").exists()     # AUCUNE écriture : c'est une proposition
    assert c.get("/api/etabli/orienter?job=..&version=1").status_code == 400
```

avec, dans le banc, une dalle fabriquée par `gltf_builder` :

```python
def _dalle() -> bytes:
    """Une dalle 4 x 4 x 0,5 — le cube du dépôt mis à l'échelle par la seule
    plume autorisée, `mesh_edit.transformer`."""
    from app.services import mesh_edit
    return mesh_edit.transformer(_cube(), {"0": {"scale": [2.0, 0.25, 2.0]}})
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "orienter or dalle"` → `4 failed`.

- [ ] **Step 3 : `backend/app/services/orient.py`**

```python
# -*- coding: utf-8 -*-
"""Auto-orient : PROPOSER des poses, classées, et laisser l'utilisateur trancher.

CE MODULE N'ÉCRIT RIEN, et ce n'est pas une timidité. Le wiki d'OrcaSlicer,
vérifié le 03/09/2026, l'écrit lui-même de son propre outil : « Auto Orientation
may not always find the best orientation for complex models. Always review the
suggested orientation. » Aucun score ne sait quelle face l'utilisateur veut voir
belle. On rend donc TROIS poses avec leurs chiffres, et c'est le bouton « poser
sur une face » — déjà là, déjà éprouvé (`mesh_edit.assise`) — qui applique celle
qu'il choisit.

LES CANDIDATS SONT LES NORMALES DU MODÈLE, quantifiées. Une face pose sur le
plateau : les directions qui valent la peine d'être essayées sont donc les
normales des faces, regroupées par direction arrondie et pondérées par leur
aire. Leur nombre est BORNÉ (`MAX_POSES`), ce qui rend le budget prévisible
quelle que soit la finesse du maillage.

LES QUATRE CRITÈRES sont ceux que le wiki nomme, avec des poids qui sont ÉCRITS
ici et non cachés dans une formule : aire en surplomb (le pire), surface
d'appui (le meilleur), périmètre de l'appui (une base longue et fine décolle),
hauteur (une pièce haute vibre). Le score se lit, se discute, et chaque terme
part dans le compte rendu.
"""
from __future__ import annotations

import math

from app.services.hollow import refus_compression
from app.services.mesh_cut import _lire_accesseur
from app.services.mesh_edit import _l, _mat_locale, _mat_mul, _monde_des_ancetres, lire_glb

MAX_POSES = 64
MAX_TRIS = 400_000
SEUIL_SURPLOMB = 45.0        # degrés depuis l'horizontale (convention Prusa)
QUANTUM = 12                 # pas de quantification des directions, en degrés
# LES POIDS, ÉCRITS : ils se lisent et se discutent, ils ne se devinent pas.
POIDS = {"surplomb": 1.0, "contact": -0.6, "contour": 0.15, "hauteur": 0.05}


def _normale(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])


def _appliquer(m, p):
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


def _triangles(data: bytes, noeuds):
    doc, binc = lire_glb(data)
    refus_compression(doc, "l'orientation automatique")
    nodes = _l(doc, "nodes")
    cible = None if noeuds is None else set(int(n) for n in noeuds)
    tris = []
    for i in range(len(nodes)):
        if "mesh" not in nodes[i] or (cible is not None and i not in cible):
            continue
        m = _mat_mul(_monde_des_ancetres(doc, i), _mat_locale(nodes[i]))
        for prim in _l(doc, "meshes")[nodes[i]["mesh"]].get("primitives", []):
            if prim.get("mode", 4) != 4 or "POSITION" not in (prim.get("attributes") or {}):
                continue
            pos = [_appliquer(m, p) for p in
                   _lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
            idx = ([t[0] for t in _lire_accesseur(doc, binc, prim["indices"])]
                   if "indices" in prim else list(range(len(pos))))
            for k in range(0, len(idx) - 2, 3):
                tris.append((pos[idx[k]], pos[idx[k + 1]], pos[idx[k + 2]]))
                if len(tris) > MAX_TRIS:
                    raise ValueError(
                        f"plus de {MAX_TRIS} triangles — l'orientation "
                        "automatique dépasse son budget mesuré. Décime d'abord.")
    if not tris:
        raise ValueError("aucun triangle à orienter dans la sélection")
    return tris


def _poses(tris):
    """Les directions candidates : les normales, quantifiées et pondérées par
    l'aire. Rend au plus MAX_POSES directions unitaires, les plus « portantes »
    d'abord, plus les six axes (une pièce sans grande face plane doit quand
    même avoir des poses à comparer)."""
    seaux: dict = {}
    for t in tris:
        n = _normale(*t)
        d = math.sqrt(sum(c * c for c in n))
        if d < 1e-20:
            continue
        u = tuple(c / d for c in n)
        cle = tuple(round(math.degrees(math.acos(max(-1.0, min(1.0, c)))) / QUANTUM)
                    for c in u)
        s = seaux.setdefault(cle, [0.0, [0.0, 0.0, 0.0]])
        s[0] += d / 2.0
        for c in range(3):
            s[1][c] += u[c] * d / 2.0
    ordre = sorted(seaux.values(), key=lambda s: -s[0])
    poses = []
    for _aire, v in ordre[:MAX_POSES - 6]:
        d = math.sqrt(sum(c * c for c in v))
        if d > 1e-12:
            poses.append(tuple(c / d for c in v))
    for ax in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        if all(sum(p[i] * ax[i] for i in range(3)) < 0.999 for p in poses):
            poses.append(tuple(float(c) for c in ax))
    return poses[:MAX_POSES]


def _noter(tris, bas):
    """Les quatre chiffres d'une pose, `bas` étant la direction qui regarde le
    plateau (donc l'opposé de l'axe haut)."""
    cos_seuil = math.cos(math.radians(90.0 - SEUIL_SURPLOMB))
    surplomb = contact = 0.0
    zmin = min(sum(p[i] * bas[i] for i in range(3)) for t in tris for p in t)
    zmax = max(sum(p[i] * bas[i] for i in range(3)) for t in tris for p in t)
    for t in tris:
        n = _normale(*t)
        d = math.sqrt(sum(c * c for c in n))
        if d < 1e-20:
            continue
        aire = d / 2.0
        cosn = sum(n[i] * bas[i] for i in range(3)) / d
        if cosn <= 0:
            continue                       # la face regarde le ciel
        hauteur = min(sum(p[i] * bas[i] for i in range(3)) for p in t) - zmin
        if cosn > 0.999 and hauteur < 1e-6 * max(1.0, zmax - zmin):
            contact += aire                # à plat SUR le plateau
        elif cosn > cos_seuil:
            surplomb += aire               # penché au-delà du seuil, en l'air
    return surplomb, contact, zmax - zmin


def candidats(data: bytes, noeuds, garder: int = 3):
    """Rend {seuil_surplomb, candidats: [{bas, contact, surplomb, contour,
    score, rotation}]}, les meilleurs d'abord. `rotation` est la NORMALE à
    envoyer à `POST /etabli/assise` — donc l'opposé de `bas`."""
    tris = _triangles(data, noeuds)
    total = sum(math.sqrt(sum(c * c for c in _normale(*t))) / 2.0 for t in tris) or 1.0
    out = []
    for bas in _poses(tris):
        surplomb, contact, hauteur = _noter(tris, bas)
        contour = math.sqrt(max(0.0, contact))      # une base longue et fine
        score = (POIDS["surplomb"] * surplomb / total
                 + POIDS["contact"] * contact / total
                 + POIDS["contour"] * (contour / max(1e-9, math.sqrt(total)))
                 + POIDS["hauteur"] * hauteur / max(1e-9, math.sqrt(total)))
        out.append({"bas": [round(c, 6) for c in bas],
                    "contact": round(contact, 6),
                    "surplomb": round(surplomb, 6),
                    "contour": round(contour, 6),
                    "score": round(score, 6),
                    "rotation": [round(-c, 6) for c in bas]})
    out.sort(key=lambda c: c["score"])
    return {"seuil_surplomb": SEUIL_SURPLOMB, "poids": dict(POIDS),
            "candidats": out[:max(1, int(garder))]}
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "orienter or dalle"` → `3 passed, 1 failed`
Run : `python tests/mesure_etabli_outils.py orienter` → **noter les deux temps dans le message de commit**.

- [ ] **Step 4 : la route — un GET, parce que rien n'est écrit**

```python
@router.get("/etabli/orienter")
async def etabli_orienter(job: str, version: int = 1):
    """PROPOSE trois poses classées. AUCUNE ÉCRITURE — c'est un avis, et le
    wiki d'OrcaSlicer dit du sien : « may not always find the best orientation
    … Always review ». La pose choisie s'applique par `POST /etabli/assise`,
    qui existe depuis le lot B."""
    from app.services import orient
    _j, data, _d = _etabli_glb_cible(job, version, "orientation")
    try:
        r = await asyncio.to_thread(orient.candidats, data, None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {**r, "avertissement":
            "Une orientation calculée ne trouve pas toujours la meilleure pose : "
            "regarde la proposition avant de l'appliquer — aucun score ne sait "
            "quelle face tu veux voir belle."}
```

`_etabli_glb_cible` juge déjà `job` (garde de chemin) et `version` ; le 400 du nom dégénéré vient de là.

- [ ] **Step 5 : la page — trois propositions, et c'est l'assise qui applique**

`index.html`, dans `#vueOutils` :

```html
          <button class="outil-btn" id="btnOrienter"></button>
```

`etabli.js` :

```js
/* AUTO-ORIENT : on PROPOSE, l'assise applique. Le bouton n'écrit jamais de
   version — c'est `ecrireSeule("assise", …)`, déjà éprouvé depuis le lot B,
   qui le fait quand l'utilisateur a choisi. Trois propositions et pas une :
   une seule aurait l'air d'une réponse. */
async function proposerOrientation() {
  if (!S.a || !S.a.job || !S.a.version) { direRefus("aucune version chargée"); return; }
  let d;
  try {
    d = await jget(`/api/etabli/orienter?job=${encodeURIComponent(S.a.job)}`
      + `&version=${S.a.version}`);
  } catch (e) { direRefus(e.message); return; }
  const box = $("#panFiche");
  const lignes = d.candidats.map((c, k) => `
    <button class="orient-choix" data-orient="${k}">
      pose ${k + 1} — appui ${fmtMesure(c.contact)}, surplomb ${fmtMesure(c.surplomb)}
      <small>score ${c.score}</small></button>`).join("");
  const zone = document.createElement("div");
  zone.className = "orient";
  zone.innerHTML = `<div class="dt-label">Orientations proposées</div>${lignes}
    <p class="note"></p>`;
  zone.querySelector(".note").textContent = d.avertissement;
  const vieux = box.querySelector(".orient");
  if (vieux) vieux.remove();
  box.appendChild(zone);
  zone.querySelectorAll("[data-orient]").forEach((b) => {
    b.addEventListener("click", async () => {
      const c = d.candidats[Number(b.dataset.orient)];
      const bilan = await ecrireSeule("assise", { normale: c.rotation, point: null });
      if (bilan) {
        direAvis(`posé sur la pose ${Number(b.dataset.orient) + 1} `
          + `(version ${bilan.derniere.version}) — appui ${fmtMesure(c.contact)}, `
          + `surplomb ${fmtMesure(c.surplomb)} ${uniteCourante()}²`);
      }
    });
  });
  direAvis(`${d.candidats.length} pose(s) proposée(s) — seuil de surplomb `
    + `${d.seuil_surplomb}°. ${d.avertissement}`);
}
$("#btnOrienter").addEventListener("click", proposerOrientation);
```

`etabli.css` gagne `.orient-choix` (même famille que les autres boutons du panneau) et `.orient .note` (même famille que `.repere-note`).

- [ ] **Step 6 : les miroirs**

```python
def test_l_auto_orient_PROPOSE_et_c_est_l_assise_qui_ecrit():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    f = _fonction_etabli_async("proposerOrientation")
    assert '"/api/etabli/orienter?job="' in f.replace("`", '"') or "/api/etabli/orienter?job=" in f
    assert 'ecrireSeule("assise"' in f          # l'assise applique, rien d'autre
    assert 'ecrireSeule("orienter"' not in f
    assert "c.rotation" in f                    # la normale rendue, telle quelle
    # l'avertissement du wiki est REPETÉ, en textContent (il vient du serveur)
    assert 'zone.querySelector(".note").textContent = d.avertissement' in f
    assert "d.avertissement" in f and f.count("d.avertissement") >= 2
    assert '<button class="outil-btn" id="btnOrienter">' in _lire("etabli/index.html")
    assert "orienter" not in _table_js("etabli/etabli.js", "ROUTES")   # aucune écriture
```

Run : `python -m pytest tests/test_etabli_outils.py -q -k "orienter or dalle"` → `4 passed`
Run : `python -m pytest tests/test_etabli_outils_page.py -q -k orient` → `1 passed`

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/orient.py backend/app/api/routes.py backend/tests/mesure_etabli_outils.py backend/tests/test_etabli_outils.py backend/tests/test_etabli_outils_page.py frontend/etabli/etabli.js frontend/etabli/index.html frontend/etabli/etabli.css
git commit -m 'etabli : auto-orient - trois poses proposees, classees, et l utilisateur tranche' -m 'Les quatre critères sont ceux que le wiki OrcaSlicer nomme (vérifié le 03/09), et les poids sont ÉCRITS dans le module plutôt que cachés dans une formule. Le module n écrit RIEN : la route est un GET, et c est POST /etabli/assise — éprouvé depuis le lot B — qui applique la pose choisie. L avertissement du wiki (une orientation calculée ne trouve pas toujours la meilleure pose) est repris en français, à l écran et dans le guide.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

- **E1 — Mini-slicer complet, peinture de supports, hauteurs de couche variables.** Réponse 1 de R10f : la frontière est « préparation + aperçu de tranchage indicatif ». Générer du G-code, c'est reprendre le métier d'un logiciel que l'utilisateur a déjà installé et qui connaît sa machine mieux que nous ; la tâche 16 s'arrête à des sections tracées, sans extrusion ni support, et le dit dans son propre titre.
- **E2 — Envoi réseau à l'imprimante et suivi d'impression.** Réponse 6 : « l'association de fichier suffit ». Mesuré en R10f le 03/09 : ElegooSlicer sait lancer une impression en LAN (IP + code d'accès), OrcaSlicer n'envoie que le fichier ; refaire ce chemin demanderait de parler le protocole d'une machine, pour remplacer un double-clic qui marche.
- **E3 — Le connecteur « snap » (clip élastique) du couteau.** Les trois autres formes d'OrcaSlicer sont livrées en tâche 17 ; celle-ci demande une matière qui plie, donc une épaisseur, un matériau et une force — une promesse mécanique que la géométrie seule ne tient pas, et qu'aucun chiffre de ce plan ne saurait vérifier au banc.

---

## Campagne de mutations

### Task 20 : `backend/tests/mutations_etabli_outils.py` — toute assertion neuve se prouve par mutation

**Files :** créer `backend/tests/mutations_etabli_outils.py`.

> Piège hérité, `2026-09-01-etabli-plaque-et-extraction.md` : « Huit bancs de ce chantier étaient satisfaits par leur **propre prose** : toute assertion nouvelle se prouve par **mutation**. » Et la leçon du lot B : « compter les assertions, pas les noms — un patch a supprimé un test entier, rattrapé par la campagne. » Cette tâche est la dernière du plan et elle n'est pas décorative : **une mutation VERTE est une assertion qui manque**, et elle se corrige avant de clore.

- [ ] **Step 1 : le fichier, patron des deux campagnes du dépôt**

`backend/tests/mutations_etabli_outils.py`. Les fonctions `rouges()` et `main()` sont recopiées **mot pour mot** de `mutations_assise_couteau.py` (même verdict à trois états, même remise à l'octet près assertée sur le sha256, même `ERREUR(collecte)` sur le code de sortie et sur une ligne `ERROR`). Seuls l'en-tête et la table `M` sont neufs :

```python
"""Banc de mutations des outils de l'Établi — plan 2026-09-03.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_etabli_outils.py           # toutes
    python tests/mutations_etabli_outils.py 3 17      # celles-là

Même modèle que mutations_plaque_slicer.py (lot A) et mutations_assise_couteau.py
(lot B), avec la colonne du BANC visé : la géométrie et les routes vivent dans
test_etabli_outils.py, la page et le guide dans test_etabli_outils_page.py, et
les deux ne se lancent jamais dans le même processus (run-tests.ps1 dit
pourquoi : chaque banc fige `app.config` avec son propre environnement).

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion
sur le sha256, journalisée), donc il ne se lance pas pendant qu'un autre banc
lit ces fichiers. Chaque mutation nomme les tests qu'elle doit faire rougir ;
une « VERTE » est une assertion qui manque, un « ERREUR(collecte) » un banc qui
n'a pas tourné.

Chaque mutation : (fichier, ancien, nouveau, banc, tests attendus rouges).
`ancien` peut être une LISTE de (ancien, nouveau) appliqués dans l'ordre.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
OUTILS = "tests/test_etabli_outils.py"
PAGE = "tests/test_etabli_outils_page.py"
MR = "backend/app/services/mesh_repair.py"
PP = "backend/app/services/print_profiles.py"
NE = "backend/app/services/nesting.py"
HO = "backend/app/services/hollow.py"
MS = "backend/app/services/mesh_slice.py"
MK = "backend/app/services/mesh_connect.py"
MB = "backend/app/services/mesh_boolean.py"
OR = "backend/app/services/orient.py"
ME = "backend/app/services/mesh_edit.py"
P3 = "backend/app/services/print3d.py"
RT = "backend/app/api/routes.py"
JS = "frontend/etabli/etabli.js"
SU = "frontend/lib3d/surplomb.js"
MZ = "frontend/lib3d/mesure.js"
AI = "frontend/etabli/aide.js"
FR = "docs/guide/fr.html"
```

- [ ] **Step 2 : la table `M` — quarante-deux mutations, une par assertion qui compte**

```python
M = [
    # ── P1 réparer (tâches 1-2) ─────────────────────────────────────────────
    # 0. la soudure ignore les attributs : une couture UV devient un doublon
    (MR, "        k = (tuple(round(c / tol) for c in p),) + tuple(a[i] for a in attrs)",
     "        k = (tuple(round(c / tol) for c in p),)",
     OUTILS, ["SANS_casser_les_coutures_UV"]),
    # 1. les normales ne sont plus remises d'aplomb par le VOLUME signé
    (MR, "        if _volume([tuple(pos[i] for i in tris[n]) for n in comp]) < 0:",
     "        if False:", OUTILS, ["par_le_volume"]),
    # 2. le capuchon prend +Newell : il regarde DEDANS, le volume tombe
    (MR, "            nw[0] -= (p[1] - q[1]) * (p[2] + q[2])",
     "            nw[0] += (p[1] - q[1]) * (p[2] + q[2])",
     OUTILS, ["bouche_un_trou"]),
    # 3. une chaîne ouverte est bouchée quand même, au lieu d'être dite
    (MR, '            r["non_bouches"] += 1; r["raisons"].append(f"chaîne ouverte de {len(boucle)} bord(s)"); continue',
     "            pass", OUTILS, ["bouche_un_trou"]),
    # 4. la route accepte une action inconnue
    (RT, "or any(a not in mesh_repair.ACTIONS for a in actions)", "or False",
     OUTILS, ["route_reparer_maillage"]),
    # 5. « réparer en un clic » repasse par la file au lieu d'écrire seul
    (JS, '    const bilan = await ecrireSeule("reparer_maillage", { actions });',
     '    const bilan = await noterAttente("reparer_maillage", { actions });',
     PAGE, ["un_clic"]),

    # ── P2 profils (tâches 3-4) ─────────────────────────────────────────────
    # 6. l'héritage des profils Orca n'est plus résolu : le 0.2 perd sa cote
    (PP, "    return _resoudre(d, par_nom, cle)", "    return d.get(cle)",
     OUTILS, ["heritage"]),
    # 7. un profil importé devient MODIFIABLE : le dossier du slicer s'écrit
    (PP, "def importer(", "def importer_ecrit(", OUTILS, ["jamais_ecrits"]),
    # 8. la garde du plateau redevient une constante
    (P3, '    plateau = float(max((profil or {}).get("plateau_mm") or [256.0]))',
     "    plateau = 256.0", OUTILS, ["garde_du_plateau", "routes_profils"]),
    # 9. le contour du plateau se dessine SANS millimètres
    (JS, "    p && enMillimetres() ? {", "    p ? {", PAGE, ["contour"]),

    # ── P3 nesting (tâche 5) ────────────────────────────────────────────────
    # 10. la rotation n'est plus essayée
    (NE, "        essais = ((0, gl, gp),) + (((90, gp, gl),) if rotation else ())",
     "        essais = ((0, gl, gp),)", OUTILS, ["TOURNE_quand_cela_fait_gagner"]),
    # 11. la marge cesse de voyager avec la pièce : les pièces se touchent
    (NE, "        gl, gp = l + m, p + m", "        gl, gp = l, p",
     OUTILS, ["TOURNE_quand_cela_fait_gagner"]),
    # 12. le squelette n'est plus recollé : il enfle et la pose se dégrade
    (NE, "    colle = []", "    return neuf\n    colle = []",
     OUTILS, ["TOURNE_quand_cela_fait_gagner", "ne_rentre_sur_AUCUN"]),
    # 13. ce qui déborde est posé quand même
    (NE, "            debordent.append(cle)\n            continue",
     "            plateaux[0].append({\"cle\": cle, \"u\": 0.0, \"v\": 0.0,\n"
     "                                \"rot\": 0, \"l\": l, \"p\": p})\n            continue",
     OUTILS, ["ne_rentre_sur_AUCUN"]),
    # 14. « ranger » n'exige plus les millimètres
    (JS, "  if (!enMillimetres() || !PROFIL.actif) {", "  if (false) {",
     PAGE, ["arranger"]),

    # ── P4 creuser / percer / décimer (tâches 6-7) ──────────────────────────
    # 15. la peau intérieure n'est pas retournée : volume nul, solide faux
    (HO, "                tris + [(b + n0, a + n0, c + n0) for (a, b, c) in tris])",
     "                tris + [(a + n0, b + n0, c + n0) for (a, b, c) in tris])",
     OUTILS, ["double_la_peau"]),
    # 16. les normales de sommet sont moyennées SANS l'aire
    (HO, "        n = _normale(pos[i], pos[j], pos[k])",
     "        n = _normale(pos[i], pos[j], pos[k])\n"
     "        _d = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0\n"
     "        n = (n[0] / _d, n[1] / _d, n[2] / _d)",
     OUTILS, ["double_la_peau"]),
    # 17. les triangles effondrés ne sont plus comptés
    (HO, "            eff = _effondres(pos, nrm, tris, paroi)", "            eff = 0",
     OUTILS, ["COMPTE_les_triangles_effondres"]),
    # 18. le foret ne vérifie plus qu'il a DEUX peaux
    (HO, "            if len(boucles) != 2:", "            if False:",
     OUTILS, ["percer_refuse"]),
    # 19. le tube du foret n'apparie plus par angle : il coud n'importe comment
    (HO, "            a = sorted(a, key=lambda s: radial(s)[1])",
     "            a = list(a)", OUTILS, ["percer_ouvre_le_creux"]),
    # 20. la décimation réécrit model.opt.glb au lieu d'une version
    (RT, '    return _etabli_ecrire(job, octets, "decimer", {"depuis": depuis, **info})',
     '    return {"version": 1, "source": info}',
     OUTILS, ["route_decimer"]),

    # ── P5 Measure (tâche 8) ────────────────────────────────────────────────
    # 21. l'angle rendu est celui des NORMALES, pas celui de la matière
    (MZ, "  return Math.round((180 - (Math.acos(borne) * 180) / Math.PI) * 1e6) / 1e6;",
     "  return Math.round(((Math.acos(borne) * 180) / Math.PI) * 1e6) / 1e6;",
     PAGE, ["angle_de_faces"]),
    # 22. le mode sortant ne range plus la mesure
    (JS, "  MESURE.points.length = 0;", "", PAGE, ["la_mesure_vit_dans_le_rail"]),

    # ── P6 T5, T6, glisser, dettes (tâches 9-13) ────────────────────────────
    # 23. « une par une » CHAÎNE les extractions au lieu de partir du parent
    (RT, "            sortie = mesh_edit.extraire(data, [n])",
     "            sortie = mesh_edit.extraire(sortie if fiches else data, [n])",
     OUTILS, ["une_par_une"]),
    # 24. la lignée n'est plus bornée : deux versions qui se désignent bouclent
    (RT, "        profondeur, mere, garde = 0, v, len(parent) + 1\n"
         "        while parent.get(mere) is not None and profondeur < garde:",
     "        profondeur, mere, garde = 0, v, len(parent) + 1\n"
         "        while parent.get(mere) is not None:",
     OUTILS, ["lignee_cassee"]),
    # 25. le tri redevient chronologique : la lignée disparaît
    (RT, "        ordonne.extend(sorted(par_job[j], key=lambda e: (e[\"mere\"], e[\"version\"])))",
     "        ordonne.extend(par_job[j])",
     OUTILS, ["MERE_PUIS_FILLES"]),
    # 26. la lecture du glisser part de l'origine du MONDE, pas du coin
    (JS, "  const u = emp.u - g.coin[g.u];\n  const v = emp.v - g.coin[g.v];",
     "  const u = emp.u;\n  const v = emp.v;",
     PAGE, ["COIN_du_plateau"]),
    # 27. la lecture du glisser refait le rail à chaque image
    (JS, "  box.textContent = `${nomDePiece(cle)} · coin",
     "  lireRepere();\n  box.textContent = `${nomDePiece(cle)} · coin",
     PAGE, ["ne_redessine_PAS_le_rail"]),
    # 28. `sparse` redevient ignoré en silence, comme avant la dette
    (ME, "    sp = a.get(\"sparse\")", "    sp = None",
     OUTILS, ["APPLIQUE_sparse"]),
    # 29. print3d perd son périmètre : il lit des composants qu'il ne sait pas écrire
    (P3, "    return lire_accesseur(doc, binc, i, composants=tuple(_FMT),",
     "    return lire_accesseur(doc, binc, i, composants=None,",
     OUTILS, ["PERIMETRES"]),
    # 30. la contradiction assise/recentrer n'est plus vue
    (JS, '  const r = S.enAttente.some((t) => t.operation === "reparer"\n'
         "    && t.charge && t.charge.recentrer);",
     '  const r = false;',
     PAGE, ["assise_et_recentrer", "la_barre_dit_la_contradiction"]),

    # ── D1 guide et aide (tâches 14-15) ─────────────────────────────────────
    # 31. un terme du lexique perd son ancre dans le guide français
    (FR, 'id="lex-drainage"', 'id="lex-drainages"',
     PAGE, ["lexique", "l_aide_de_l_etabli"]),
    # 32. une ressource du guide perd sa date de vérification
    (FR, "<td>Prusa — Warping</a></td><td>03/09/2026</td>",
     "<td>Prusa — Warping</a></td><td>—</td>",
     PAGE, ["ressource"]),

    # ── D2 surplombs (tâche 16) ─────────────────────────────────────────────
    # 33. le surplomb est jugé À l'inverse : les murs sont peints, les plafonds non
    (SU, "  return p !== null && p < seuilDeg;", "  return p !== null && p > seuilDeg;",
     PAGE, ["pente_du_surplomb"]),
    # 34. une face qui regarde le ciel devient un surplomb
    (SU, "  if (!(d > 0)) return null;                        // vers le haut, ou tangente",
     "  if (false) return null;",
     PAGE, ["pente_du_surplomb"]),

    # ── D4 booléens, D5 orientation (tâches 18-19) ──────────────────────────
    # 35. la différence ne retourne plus la peau de B : le creux est plein
    (MB, "    return a_dehors_b + [_retourner(t) for t in b_dedans_a]",
     "    return a_dehors_b + b_dedans_a",
     OUTILS, ["VOLUME_attendu"]),
    # 36. le budget du booléen n'est plus gardé
    (MB, "    if len(a) > MAX_TRIS or len(b) > MAX_TRIS:", "    if False:",
     OUTILS, ["refuse_au_dela_de_son_budget"]),
    # 37. l'orientation n'est plus triée : la « meilleure » est la première venue
    (OR, '    out.sort(key=lambda c: c["score"])', "    pass",
     OUTILS, ["propose_ses_faces"]),
    # 38. l'auto-orient ÉCRIT au lieu de proposer
    (JS, '      const bilan = await ecrireSeule("assise", { normale: c.rotation, point: null });',
     '      const bilan = await ecrireSeule("orienter", { normale: c.rotation });',
     PAGE, ["PROPOSE_et_c_est_l_assise"]),

    # ── D2 tranches, D3 connecteur, D1 aide ─────────────────────────────────
    # 39. la section ne teste plus le CHANGEMENT DE SIGNE : trois points par
    #     triangle, aucun segment, périmètre nul
    (MS, "                if (dp > 0) == (dq > 0) or dp == dq:
                    continue",
     "                if False:
                    continue",
     OUTILS, ["sections_carrees"]),
    # 40. le jeu part du côté du MÂLE : les deux pièces ne rentrent plus
    (MK, "        r = float(rayon) if male else float(rayon) + float(jeu)",
     "        r = float(rayon) + float(jeu) if male else float(rayon)",
     OUTILS, ["teton_ajoute_de_la_matiere"]),
    # 41. un terme de l'aide n'a plus son jumeau dans le guide
    (AI, "  drainage: {", "  drainages: {", PAGE, ["l_aide_de_l_etabli"]),
]
```

- [ ] **Step 3 : lancer la campagne, et corriger ce qui sort VERT**

Run : `python tests/mutations_etabli_outils.py` (depuis `backend/`, quelques minutes — chaque mutation relance un banc filtré)
Expected : quarante-deux lignes `ROUGE`, et la ligne JSON de bilan en queue.

Ce qui peut sortir autrement, et quoi en faire :

- **`VERTE`** — l'assertion manque. Écrire l'assertion qui manque dans le banc nommé par la colonne, la faire rougir sous la mutation, puis la faire verdir sans. **Ne jamais retirer la mutation pour faire taire la ligne.**
- **`ROUGE(autres)`** — la mutation casse d'autres tests que les attendus : soit l'ancre est trop large, soit le test attendu est mal nommé. Corriger la colonne, pas le code.
- **`ERREUR(collecte)`** — le banc n'a pas tourné (import cassé par la mutation). Choisir une ancre qui laisse le module importable.

Run (contrôle de remise) : `git status --porcelain backend/ frontend/ docs/`
Expected : **aucune ligne**. La campagne remet chaque fichier à l'octet près et l'assère sur son sha256 ; une sortie non vide veut dire qu'elle a été interrompue, et il faut restaurer avant toute autre chose.

- [ ] **Step 4 : les deux campagnes d'avant tournent encore**

Les tâches 2, 7, 8, 9 et 13 ont touché des lignes que les campagnes précédentes citent (`ORDRE_ECRITURE`, `MODES_GESTE`, la charge d'`extraire`).

Run : `python tests/mutations_assise_couteau.py`
Expected : 45 lignes `ROUGE` — en particulier `[22]`, `[16]`, `[17]`, `[18]`, `[19]`, `[20]`, `[21]`, dont les ancres ont été mises à jour par les tâches 2, 7 et 8.
Run : `python tests/mutations_plaque_slicer.py`
Expected : 77 lignes `ROUGE`.

- [ ] **Step 5 : la suite complète, une dernière fois**

Run : `.\scripts\run-tests.ps1`
Expected : tous les bancs verts, `test_etabli_outils.py` et `test_etabli_outils_page.py` compris (chacun dans son propre processus).

- [ ] **Step 6 : commit**

```bash
git add backend/tests/mutations_etabli_outils.py
git commit -m 'bancs : campagne de mutations des outils de l Etabli - 42 mutations, toutes rouges' -m 'Troisième campagne du dépôt, patron des deux précédentes : chaque mutation nomme le banc visé et les tests qu elle doit faire rougir, les sources sont remises à l octet près (sha256 asserté), et une VERTE est une assertion qui manque — jamais une mutation à retirer. Elle couvre les cinq bacs de parité, les cinq du différenciant et les deux dettes.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Relecture du plan (faite le 03/09/2026)

**Couverture des bacs de R10f, un par un.** P1 → tâches 1–2 · P2 → 3–4 · P3 → 5 · P4 → 6–7 · P5 → 8 · P6 → 9 (T5), 10 (T6), 11 (lecture du glisser), 12 (dette des deux lecteurs), 13 (dette assise/recentrer) · D1 → 14–15 · D2 → 16 · D3 → 17 · D4 → 18 · D5 → 19 · E1, E2 et E3 → section « Écarté » · campagne → 20. Aucun bac sans tâche.

**Cohérence des noms, vérifiée en relisant les tâches à l'envers.** `ORDRE_ECRITURE` porte les douze opérations dès la tâche 2 et ne rebouge plus (`decimer` y est, tâche 7). `ecrireSeule(operation, charge, source)` rend un bilan `{ecrites, derniere, echec}` et c'est cette forme que lisent les tâches 2, 6, 7, 9, 17, 18 et 19. `MODES_GESTE` passe à cinq en tâche 7 (`foret`) puis à six en tâche 8 (`mesure`), et l'assertion littérale de `test_etabli_canevas.py` est mise à jour aux DEUX endroits. `refus_compression` naît dans `hollow.py` (tâche 6) et est importée par `mesh_slice`, `mesh_connect` et `orient`. `mesh_edit.lire_accesseur` naît en tâche 12 ; les modules écrits avant (tâches 1, 6, 7) importent `mesh_cut._lire_accesseur` et la tâche 12 les migre nommément. Les cotes en millimètres n'entrent JAMAIS dans un service : la route convertit (`creuser`, `percer`, `connecteur`), ou la page refuse (`arranger`).

**Deux routes de REGARD, qui n'écrivent rien** — `/etabli/ranger`, `/etabli/tranches`, plus le `GET /etabli/orienter` — et elles sont hors de `ROUTES` côté page, ce qu'un banc épingle. **Six routes d'ÉCRITURE neuves** — `reparer-maillage`, `creuser`, `percer`, `decimer`, `connecteur`, `booleen` — qui passent toutes par `_etabli_glb_cible` puis `_etabli_ecrire`, comme les cinq d'avant.
