# Game Assets 3D — les moteurs image → 3D : rig, LOD, textures, conversion, vues, bible, banc, matière, GPU local, photos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer les deux bacs de R10e — parité (P1–P5) puis différenciant (D1–D5) — sur le flux fal `assets3d`, sans toucher au pipeline Meshy du 3D Studio, en mesurant chaque perte, chaque coût et chaque capacité **avant** de la promettre.

**Architecture :** tout ce qui écrit un fichier vit dans `backend/app/services/` (stdlib + Pillow, jamais numpy), un module par métier (`asset3d_rig`, `mesh_lod`, `mesh_textures`, `mesh_convert`, `asset3d_views`, `asset3d_banc`, `local3d_service`, plus `mesh_edit.habiller`) ; les routes de `routes.py` orchestrent et journalisent (`JobRecord`, `provider="asset3d"`) ; l'interface va dans les pages **autonomes** (`/studio3d` gagne un panneau « Atelier fal », `/etabli` un sélecteur de matière) et **un seul** patch de bundle (`asset3dlod`) pour l'écran « 3D » du hub. Chaque module a son banc-miroir `backend/tests/test_<x>.py` qui relit les GLB, JSON et archives écrits — jamais le code.

**Tech Stack :** FastAPI, httpx, Pillow 12.3 (mesuré : Python embarqué 3.13.15, `numpy False`, `torch False`), gltfpack 1.2 embarqué (`%LOCALAPPDATA%\DeepotusVideoGen\bin\gltfpack.exe`), fal_client (Tripo/Hunyuan/Trellis/Rodin/TripoSR/Seedream), proxy Meshy existant (`meshy_service.create_task`/`get_task`/`_fetch_url`, mock `MESHY_MOCK=1`), `<model-viewer>` vendu dans `frontend/dist/assets/model-viewer.min.js`.

---

## Périmètre

**Bacs de R10e, exactement** (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`, § R10e) :

| Lot | Tâche | Bac | Ce qu'elle livre |
|---|---|---|---|
| 1 | T1 | socle | tarifs des nouvelles opérations, mock Meshy rigging fidèle aux docs, `tiny_rigged_glb`, helper de job en fond |
| 1 | T2 | **P1** | rig + animations Meshy sur un job fal : remesh automatique > 300 000 faces, GLB animé rapatrié, lu, exporté |
| 1 | T3 | **P2** | LOD en chaîne gltfpack (3 niveaux), perte mesurée (IoU 3 vues + écart de normales), budget par usage, archive nommée par moteur |
| 1 | T4 | **P3** | textures d'un modèle exportées aux conventions `naming_catalog` (R10c), résolution choisie, cartes manquantes dérivées en PIL |
| 1 | T5 | **P4** | conversion locale GLB → OBJ+MTL / STL / 3MF, OBJ/STL → GLB ; FBX/USDZ/BLEND par Meshy `convert` (1 cr) — l'écriture FBX libre est **écartée et dite** |
| 1 | T6 | **P5** | les 4 vues générées, montrées, rejouables une à une, détourables, **avant** de payer le moteur |
| 2 | T7 | **D1** | vues depuis la planche de la bible (panneaux persistés, ou découpe de la planche par gouttières) → job de vues P5 → modèle rattaché à l'entité |
| 2 | T8 | **D2** | banc de référence par sujet type (personnage, objet, véhicule) sur chaque moteur, `banc.json`, cité par `/assets3d/engines` |
| 2 | T9 | **D3** | matière du Forge posée sur un modèle, par partie (nœud), depuis l'Établi — refus parlant sans UV |
| 2 | T10 | **D4** | service GPU local optionnel (Hunyuan3D 2.1, patron Voicebox) : mesure de la carte d'abord, table de décision, moteur `hunyuan-local` gratuit, repli fal |
| 2 | T11 | **D5** | photos réelles (1–4, depuis le téléphone ou un fichier) → détourage → job de vues P5 |
| — | T12 | — | campagne de mutations `backend/tests/mutations_moteurs3d.py` |

**E exclus** : E1 (génération locale sans service) — le Python embarqué n'a ni numpy ni torch (mesuré) ; E2 (API Tripo directe) — fal suffit ; voir « Écarté ».

**Ce que le terrain dit — mesuré le 03/09/2026**

| Fait | Conséquence |
|---|---|
| `gltfpack 1.2 -h` : entrées `.obj/.gltf/.glb`, sorties `.gltf/.glb` **seulement** ; options utiles `-si R`, `-sa`, `-se E`, `-slb`, `-kn`, `-km`, `-noq`, `-tl N`, `-r rapport.json` | P4 : aucun FBX/USDZ local par gltfpack ; P2 : la chaîne LOD et le rapport JSON sont gratuits |
| `nvidia-smi` : `NVIDIA GeForce RTX 2080 Ti, 11264 MiB, 616.56` ; `Win32_VideoController.AdapterRAM = 4293918720` (uint32 : **plafonne à 4 Gio**) | D4 : lire nvidia-smi d'abord, Win32 en repli avec l'avertissement du plafond ; la carte est **Turing**, 11 Gio |
| Python embarqué 3.13.15, PIL 12.3.0, httpx 0.28.1, `numpy False`, `torch False` | tout service GPU est un processus à part (Python 3.10 + PyTorch, README Hunyuan) |
| `asset3d_service.generate_asset3d` fait upload → vues Seedream → moteur → téléchargements en **une seule** passe ; `_upload`, `_seedream_edit`, `_run_engine`, `_download` sont les coutures monkeypatchées des bancs | P5 découpe la passe en deux sans changer les coutures |
| `meshy_service.MeshyMock.get` rend pour `rigging` `result.rigged_model_url` — la doc relue dit `rigged_character_glb_url` + `basic_animations` | T1 aligne le mock sur la doc en gardant la clé historique |
| `test_meshy_service.py:469` épingle `set(ENGINES)` à six moteurs, « à dessein » | T10 passe par là pour ajouter `hunyuan-local` |
| chaîne des patchs du bundle (`repatch_all.py --list`) : `dzrailmotion → version → dznodecat → seedance25` | le patch `asset3dlod` (T3+T4) se pose en **queue**, un seul `.bak_asset3dlod` |
| la planche personnage (`board_service.compose_character_board`) est composée par code : colonnes `front, left, right, back`, gouttières 28 px de fond `(242,239,233)`, visages 300 px, corps 560 px ; les fichiers des panneaux **ne sont pas persistés** sur l'entité (`prompt_recipe.panels` = prompt+seed+model) | D1 : persister `file` dans la recette pour les prochaines planches, et découper les anciennes par détection de gouttières |
| `sprite_service._rembg_api` (fal `imageutils/rembg`, 0,003 $) et `asset3d_qc.masque_reference` (fond estimé sur les quatre coins, gratuit) existent | P5/D5 : détourage local gratuit d'abord, fal en option |
| le hub envoie `{multiview:!0,views:4,textures:!0,tpose:!1,formats:["glb"]}` à `POST /api/assets/3d` (mesuré dans le bundle) | P5 ne touche pas ce chemin : le contrôle des vues vit dans `/studio3d` |

**Règles du dépôt qui s'appliquent ici**
- `python` = le runtime embarqué (`$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`) ; les bancs se lancent **un processus par fichier** depuis `backend/` : `python tests/test_<x>.py`. Jamais `pytest tests`.
- Les bancs forcent `sys.stdout.reconfigure(encoding="utf-8")` et isolent `DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER` (patron `test_meshy_service.py:19-31`).
- Chaque appel Meshy nouveau **commence par relire sa page docs.meshy.ai** (WebFetch exact, date figée dans le docstring), puis fige les paramètres dans le module.
- Commits : sujet SANS accents, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, guillemets simples dans `-m`.
- Jamais d'écrasement : toute écriture de maillage est une **version** (`model.v{n}.glb` via `asset3d_service.next_version` + `mesh_report.write_report`).

---

## Coût de patch

| Tâche | Surface | Coût |
|---|---|---|
| T1 socle | backend (`pricing.py`, `meshy_service.py`, `routes.py`), bancs | 0 patch |
| T2 P1 rig | backend + `/studio3d` (autonome, `frontend/studio3d/fal.js` nouveau, 1 `<section>` dans `index.html`) | 0 patch |
| T3 P2 LOD | backend + **1 patch bundle** `scripts/patch_bundle_asset3dlod.py` (zone « LOD · Textures » sous `DzOptimize` dans la carte 3D du hub) | 1 patch, en queue de chaîne |
| T4 P3 textures | backend ; l'UI est **dans le même patch** que T3 (un bouton « ↓ Textures ▾ ») | 0 patch de plus |
| T5 P4 conversion | backend + `/studio3d` (panneau « Job courant » de `fal.js`) | 0 patch |
| T6 P5 vues | backend + `/studio3d` (panneau « Vues d'abord » de `fal.js`) | 0 patch |
| T7 D1 bible | backend (route `model3d` + `board_service`) ; le bouton « depuis la planche » est un `from_board:true` que Chapitres enverra plus tard — pas de patch ici | 0 patch |
| T8 D2 banc | backend + script + tableau dans `/studio3d` | 0 patch |
| T9 D3 matière | backend (`mesh_edit`) + `/etabli` (autonome) | 0 patch |
| T10 D4 GPU | backend + un repli parlant dans `/studio3d` ; le service lui-même est **hors dépôt** | 0 patch |
| T11 D5 photos | backend + `/studio3d` (`<input type=file multiple>`) | 0 patch |
| T12 mutations | `backend/tests/mutations_moteurs3d.py` | 0 patch |

Le patch `asset3dlod` se rejoue par `python scripts/repatch_all.py --from asset3dlod` ; la vérification est l'**inventaire des fonctions** (README « Patching the compiled UI »), pas l'œil.

---

## Références vérifiées

Seules les références de R10e (03/09/2026) et celles **relues aujourd'hui** servent d'argument. Tout le reste est « de mémoire » et se mesure au banc.

| Source | Relue le | Ce qu'elle dit (verbatim ou chiffres) | Sert à |
|---|---|---|---|
| docs.meshy.ai/en/api/rigging | 03/09/2026 (WebFetch) | `POST /openapi/v1/rigging` ; `input_task_id` **ou** `model_url` (« .glb format only », « character's face must point toward the +Z axis ») ; `height_meters` défaut 1.7 ; `texture_image_url` (.png) ; « models with more than **300,000 faces** are not supported » ; humanoïdes texturés seulement ; réponse `rigged_character_glb_url`, `rigged_character_fbx_url`, `basic_animations.walking_glb_url`, `.running_glb_url`, `_fbx_url`, `_armature_glb_url` ; **5 crédits** | T1, T2 |
| docs.meshy.ai/en/api/animation | 03/09/2026 | `POST /openapi/v1/animations` ; `rig_task_id` ; `action_id` (entier) **ou** `motion_task_id` ; `post_process.operation_type` ∈ `change_fps`, `fbx2usdz`, `extract_armature`, `fps` ∈ 24/25/30/60 ; réponse `animation_glb_url`, `animation_fbx_url` ; **3 crédits** ; bibliothèque : `0 Idle`, `1 Walking_Woman`, `4 Attack`, `8 Dead`, `11 Idle_02` (docs.meshy.ai/en/api/animation-library) | T2 |
| docs.meshy.ai/en/api/remesh | 03/09/2026 | `POST /openapi/v1/remesh` ; `model_url` (URL publique ou data URI) ; `target_formats` ∈ glb fbx obj usdz blend stl 3mf ; `topology` quad/triangle ; `target_polycount` défaut 30 000, « 100 to 300,000 » | T2 (remesh avant rig) |
| docs.meshy.ai/en/api/convert | 03/09/2026 | `POST /openapi/v1/convert` ; `model_url` (.glb .gltf .obj .fbx .stl) ; `target_formats` idem ; **1 crédit par tâche** (pas par format) | T5 |
| github.com/Tencent-Hunyuan/Hunyuan3D-2.1 (README, `api_server.py`, `api_models.py`) | 03/09/2026 | « 10 GB VRAM » forme, « 21GB » texture, « 29GB » les deux ; Python 3.10, PyTorch 2.5.1+cu124 ; `api_server.py` : `POST /generate` (FileResponse GLB), `POST /send`, `GET /status/{uid}`, `GET /health`, hôte `0.0.0.0`, **port 8081**, `--low_vram_mode` ; `GenerationRequest` : `image` (str base64), `remove_background=True`, `texture=False`, `seed=1234`, `octree_resolution=256`, `num_inference_steps=5`, `guidance_scale=5.0`, `num_chunks=8000`, `face_count=40000`. **Le README ne nomme aucune génération de GPU** — le « RTX 30+ » de R10e n'y est pas ; le seuil mesurable est la VRAM | T10 |
| docs.unity3d.com/Manual/lod-group-configure.html | 03/09/2026 | « Add the suffix `_LODX` to the name of each mesh … `ExampleMeshName_LOD0` » ; le guide exporte en **.fbx** ; « Unity automatically creates a LOD Group component » ; 8 niveaux max | T3 (nommage) |
| docs.godotengine.org … node_type_customization | 03/09/2026 | suffixes `-col`, `-convcol`, `-rigid`, `-noimp`, `-loop`… ; **aucun suffixe LOD** documenté | T3 : Godot reçoit des noms lisibles, rien de promis |
| Tripo (developers.tripo3d.ai, R10e) | 03/09/2026 | rig Tripo = API directe, clé séparée | E2 écarté |
| `<model-viewer>` : attributs `autoplay`, `animation-name` | **de mémoire** | — | T2 : vérifié à l'écran au step 8, jamais au banc |
| FBX ASCII lu par Unity/Unreal, refusé par Blender | **de mémoire** | — | T5 : raison de l'écart, pas un argument de livraison |

---

## Lot 1 — parité

### Task 1 : le socle — tarifs, mock Meshy fidèle, helper de job

**Files:**
- Modify: `backend/app/services/pricing.py:68-72` (DEFAULTS), `:305-334` (kind `asset3d`, nouveaux kinds)
- Modify: `backend/app/services/meshy_service.py:195-240` (`tiny_rigged_glb`, `mock_file_bytes`), `:340-344` (résultat rigging du mock)
- Modify: `backend/app/api/routes.py` (helper `_lancer_job_asset3d`, juste avant `@router.post("/assets/3d")` ligne 352)
- Modify: `backend/tests/test_meshy_service.py:275` (le rig du mock porte les clés documentées)
- Test: `backend/tests/test_moteurs3d_socle.py`

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""Socle des moteurs 3D (plan 2026-09-03) : tarifs des nouvelles opérations,
mock Meshy rigging aligné sur docs.meshy.ai (relu le 03/09/2026), GLB riggé
minimal relu par mesh_edit.rig_inventory. Run : python tests/test_moteurs3d_socle.py
"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["MESHY_MOCK"] = "1"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_le_devis_du_rig_dit_remesh_et_animations():
    from app.services.pricing import estimate
    r = estimate({"kind": "asset3d_rig"})
    assert r["credits"] == {"meshy": 5.0}, r
    r2 = estimate({"kind": "asset3d_rig", "remesh_requis": True, "actions": [0, 4]})
    assert r2["credits"] == {"meshy": 16.0}, r2          # 5 + 5 + 2 × 3
    labels = [l["label"] for l in r2["breakdown"]]
    assert any("300" in l for l in labels), labels        # le remesh DIT pourquoi


def test_les_operations_locales_coutent_zero_et_le_disent():
    from app.services.pricing import estimate
    for kind in ("asset3d_lod", "asset3d_textures", "asset3d_local"):
        r = estimate({"kind": kind})
        assert r["total_usd"] == 0.0 and r["breakdown"][0]["provider"] == "local", kind
    assert estimate({"kind": "asset3d_convert", "via": "local"})["total_usd"] == 0.0
    assert estimate({"kind": "asset3d_convert", "via": "meshy"})["credits"] == {"meshy": 1.0}
    v = estimate({"kind": "asset3d_views", "views": 4})
    assert abs(v["total_usd"] - 0.12) < 1e-9, v
    v2 = estimate({"kind": "asset3d_views", "views": 2, "rembg": 2})
    assert abs(v2["total_usd"] - (0.06 + 0.006)) < 1e-9, v2


def test_le_mock_rigging_porte_les_cles_documentees():
    from app.services import meshy_service as MS
    MS._mock = None
    from app.config import settings
    settings.MESHY_MOCK, settings.MESHY_MOCK_SPEED = True, 0.001
    mk = MS.get_mock()
    code, d = mk.create("openapi/v1/rigging", {"model_url": "http://x/m.glb", "height_meters": 1.7})
    assert code == 202
    import time; time.sleep(0.05)
    code, t = mk.get(d["result"])
    res = t["result"]
    assert res["rigged_character_glb_url"].endswith("rig.glb")
    assert res["rigged_model_url"]                          # clé historique conservée
    assert set(res["basic_animations"]) >= {"walking_glb_url", "running_glb_url"}


def test_le_glb_rigge_du_mock_a_un_squelette_et_un_clip():
    from app.services import meshy_service as MS, mesh_edit, print3d
    data = MS.tiny_rigged_glb()
    inv = mesh_edit.rig_inventory(data)
    assert inv["a_squelette"] and inv["nb_os"] == 1 and len(inv["clips"]) == 1, inv
    assert len(print3d.lire_glb_triangles(data)) == 1
    octets, media = MS.mock_file_bytes("anim_walking.glb")
    assert octets[:4] == b"glTF" and media == "model/gltf-binary"
    assert mesh_edit.rig_inventory(octets)["a_squelette"]


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001 — on VEUT le nom du rouge
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (moteurs3d_socle)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer, constater le rouge**

```
cd backend ; python tests/test_moteurs3d_socle.py
```
Attendu : `✗ test_le_devis_du_rig_dit_remesh_et_animations — AssertionError`, `✗ test_le_glb_rigge_du_mock… — AttributeError: module … has no attribute 'tiny_rigged_glb'`, fin `ROUGE — 4 tests, 4 rouge(s)`.

- [ ] **Step 3 : les tarifs**

Dans `pricing.py`, `DEFAULTS` gagne après `"rembg_api_usd"` :

```python
    "seedream_edit_usd": 0.03,        # fal.ai bytedance/seedream/v4/edit, par vue (spec §7)
```

et `estimate()` remplace la ligne `lines.append(_line("fal", "Multi-view edits", v, "img", v * 0.03))` par `v * p.get("seedream_edit_usd", DEFAULTS["seedream_edit_usd"])`, puis gagne, après le bloc `asset3d_texture` :

```python
    elif kind == "asset3d_rig":
        # Rig Meshy d'un job fal (R10e P1). docs.meshy.ai/en/api/rigging relue
        # le 03/09/2026 : 5 cr ; > 300 000 faces → remesh d'abord (5 cr) ;
        # chaque action de la bibliothèque : 3 cr. Les animations de marche et
        # de course sont INCLUSES dans le rig (basic_animations).
        from app.services import meshy_service as _MS
        usd_cr = float(p.get("meshy_credit_usd", DEFAULTS["meshy_credit_usd"]))
        if op.get("remesh_requis"):
            cr = _MS.CREDITS_FLAT["remesh"]
            lines.append(_line("meshy", "Remesh (> 300 000 faces, exigé par le rig)",
                               cr, "credits", cr * usd_cr))
        cr = _MS.CREDITS_FLAT["rigging"]
        lines.append(_line("meshy", "Auto-rig humanoïde (marche + course incluses)",
                           cr, "credits", cr * usd_cr))
        n = len(op.get("actions") or [])
        if n:
            cr = n * _MS.CREDITS_FLAT["animations"]
            lines.append(_line("meshy", f"Animations x{n}", cr, "credits", cr * usd_cr))
    elif kind == "asset3d_views":
        v = int(op.get("views", 4))
        lines.append(_line("fal", "Vues quasi-orthographiques (Seedream)", v, "img",
                           v * p.get("seedream_edit_usd", DEFAULTS["seedream_edit_usd"])))
        n = int(op.get("rembg", 0) or 0)
        if n:
            lines.append(_line("fal", f"Détourage fal x{n}", n, "img",
                               n * p.get("rembg_api_usd", DEFAULTS["rembg_api_usd"])))
    elif kind == "asset3d_convert":
        if str(op.get("via") or "local") == "meshy":
            from app.services import meshy_service as _MS
            cr = _MS.CREDITS_FLAT["convert"]
            lines.append(_line("meshy", "Conversion Meshy (fbx/usdz/blend)", cr, "credits",
                               cr * float(p.get("meshy_credit_usd", DEFAULTS["meshy_credit_usd"]))))
        else:
            lines.append(_line("local", "Conversion locale (obj/stl/3mf)", 1, "fichier", 0.0))
    elif kind in ("asset3d_lod", "asset3d_textures", "asset3d_local"):
        libelle = {"asset3d_lod": "Chaîne LOD (gltfpack)",
                   "asset3d_textures": "Export textures (PIL)",
                   "asset3d_local": "Hunyuan3D local (GPU)"}[kind]
        lines.append(_line("local", libelle, 1, "op", 0.0))
```

- [ ] **Step 4 : le mock rigging et le GLB riggé minimal**

Dans `meshy_service.py`, après `tiny_png()` :

```python
def tiny_rigged_glb() -> bytes:
    """GLB v2 minimal RIGGÉ : un triangle, un os, un skin, un clip de deux
    clés. C'est ce que le simulateur sert pour rig.glb et anim_*.glb, et ce
    que `mesh_edit.rig_inventory` doit relire avec a_squelette=True."""
    pos = struct.pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.5, 1.0, 0.0)
    joints = struct.pack("<12H", *([0, 0, 0, 0] * 3))
    weights = struct.pack("<12f", *([1.0, 0.0, 0.0, 0.0] * 3))
    ibm = struct.pack("<16f", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    times = struct.pack("<2f", 0.0, 1.0)
    quats = struct.pack("<8f", 0, 0, 0, 1, 0, 0.7071068, 0, 0.7071068)
    parts, views, off = [], [], 0
    for blob in (pos, joints, weights, ibm, times, quats):
        pad = b"\x00" * (-len(blob) % 4)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(blob)})
        parts.append(blob + pad); off += len(blob) + len(pad)
    binc = b"".join(parts)
    gltf = {
        "asset": {"version": "2.0", "generator": "deepotus-meshy-mock-rig"},
        "scene": 0, "scenes": [{"nodes": [0, 1]}],
        "nodes": [{"mesh": 0, "skin": 0, "name": "corps"},
                  {"name": "os_racine", "rotation": [0, 0, 0, 1]}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "JOINTS_0": 1,
                                                    "WEIGHTS_0": 2}}]}],
        "skins": [{"joints": [1], "inverseBindMatrices": 3, "skeleton": 1}],
        "animations": [{"name": "walking", "samplers": [
            {"input": 4, "output": 5, "interpolation": "LINEAR"}],
            "channels": [{"sampler": 0, "target": {"node": 1, "path": "rotation"}}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
             "min": [0, 0, 0], "max": [1, 1, 0]},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "VEC4"},
            {"bufferView": 2, "componentType": 5126, "count": 3, "type": "VEC4"},
            {"bufferView": 3, "componentType": 5126, "count": 1, "type": "MAT4"},
            {"bufferView": 4, "componentType": 5126, "count": 2, "type": "SCALAR",
             "min": [0.0], "max": [1.0]},
            {"bufferView": 5, "componentType": 5126, "count": 2, "type": "VEC4"}],
        "bufferViews": views, "buffers": [{"byteLength": len(binc)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binc)
    return (struct.pack("<III", 0x46546C67, 2, total)
            + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binc), 0x004E4942) + binc)
```

`mock_file_bytes` : avant `if ext == "glb":`, ajouter

```python
    if ext == "glb" and (fname.startswith("rig") or fname.startswith("anim_")):
        return tiny_rigged_glb(), "model/gltf-binary"
```

`MeshyMock.get`, le bloc `if t["kind"] == "rigging":` devient :

```python
            if t["kind"] == "rigging":
                # docs.meshy.ai/en/api/rigging relue le 03/09/2026 ; la clé
                # historique du mock reste pour meshy.client.js (out.rigged)
                out["result"] = {
                    "rigged_model_url": f"{pre}rig.glb",
                    "rigged_character_glb_url": f"{pre}rig.glb",
                    "rigged_character_fbx_url": f"{pre}rig.fbx",
                    "basic_animations": {
                        f"{n}_{k}_url": f"{pre}anim_{n}.{k.split('_')[-1]}"
                        for n in ("walking", "running")
                        for k in ("glb", "fbx", "armature_glb")}}
```

Dans `test_meshy_service.py:275`, remplacer `assert rig["consumed_credits"] == 5 and rig["result"]["rigged_model_url"]` par `assert rig["consumed_credits"] == 5 and rig["result"]["rigged_character_glb_url"]`.

- [ ] **Step 5 : le helper de job en fond, dans `routes.py`**

Juste avant `@router.post("/assets/3d")` :

```python
async def _lancer_job_asset3d(background_tasks, *, job: str, titre: str,
                              etape: str, travail, cost_meta) -> dict:
    """Le patron des cinq routes qui lancent une opération PAYANTE sur un job
    3D : un JobRecord provider="asset3d" (image_filename=asset3d_<job>), un
    verrou 409 contre deux clics, `travail(on_step)` en fond, `cost_meta(r)`
    dans la ligne à la fin. Rend {job_id, status:"queued"} — POLLER
    GET /api/jobs/{job_id}."""
    from datetime import datetime as _dtu
    import json as _json
    from app.services.storage import JobRecord as _JR, async_session_factory as _sf
    async with _sf() as s:
        res = await s.execute(_select(_JR).where(
            _JR.provider == "asset3d",
            _JR.image_filename == f"asset3d_{Path(job).name}",
            _JR.status.notin_(["done", "failed"])))
        if res.scalars().first() is not None:
            raise HTTPException(409, "Une opération est déjà en cours sur ce "
                                     "maillage — attends la fin (file des rendus).")
    job_id = str(uuid4())
    async with _sf() as s:
        s.add(_JR(id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=5,
                  title=titre, image_filename=f"asset3d_{Path(job).name}",
                  provider="asset3d", current_step=etape))
        await s.commit()

    async def on_step(label, pct):
        async with _sf() as s2:
            jr2 = await s2.get(_JR, job_id)
            if jr2 is not None:
                jr2.current_step, jr2.progress = label, int(pct)
                await s2.commit()

    async def _run():
        try:
            r = await travail(on_step)
            async with _sf() as s:
                jr = await s.get(_JR, job_id)
                if jr is not None:
                    jr.status, jr.progress = JobStatus.DONE.value, 100
                    jr.current_step, jr.completed_at = "Complete", _dtu.utcnow()
                    if r.get("file"):
                        jr.final_video_path = str(
                            settings.outputs_path / "assets3d" / Path(job).name / r["file"])
                    jr.cost_meta = _json.dumps(cost_meta(r), ensure_ascii=False)
                    await s.commit()
        except Exception as e:
            logger.exception(f"asset3d {etape} {job_id} failed: {e}")
            async with _sf() as s:
                jr = await s.get(_JR, job_id)
                if jr is not None:
                    jr.status, jr.error, jr.current_step = JobStatus.FAILED.value, str(e), "Failed"
                    await s.commit()

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued", "source_job": Path(job).name}
```

- [ ] **Step 6 : relancer**

```
python tests/test_moteurs3d_socle.py ; python tests/test_meshy_service.py ; python tests/test_asset3d_service.py
```
Attendu : `OK — 4 tests, 0 rouge(s) (moteurs3d_socle)` ; `OK — … assertions groupées vertes (meshy_service)` ; les 13 tests d'`asset3d_service` verts (`test_pricing_asset3d` inchangé : 3 × 0,03 $ = même total).

- [ ] **Step 7 : commit**

```
git add backend/app/services/pricing.py backend/app/services/meshy_service.py backend/app/api/routes.py backend/tests/test_moteurs3d_socle.py backend/tests/test_meshy_service.py
git commit -m 'moteurs 3d : socle - tarifs rig/vues/conversion, mock rigging fidele aux docs, helper de job' -m 'Tarifs des cinq opérations nouvelles (rig 5 cr + remesh conditionnel + 3 cr/action, vues à seedream_edit_usd, conversion Meshy 1 cr, locales à 0 $ dites). Le simulateur Meshy rend les clés documentées du rigging (rigged_character_glb_url, basic_animations) et sert un GLB riggé minimal relu par rig_inventory. Un seul patron de job en fond pour les routes payantes.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Task 2 : P1 — rig et animations Meshy reliés au flux fal

**Files:**
- Create: `backend/app/services/asset3d_rig.py`
- Modify: `backend/app/api/routes.py` (4 routes, déclarées AVANT `get_asset3d_file` ligne 1197)
- Create: `frontend/studio3d/fal.js` ; Modify: `frontend/studio3d/index.html` (une `<section>` dans `.rail-left`), `frontend/studio3d/studio3d.js:947` (le bouton `engineGoto` ouvre le panneau au lieu de renvoyer au hub)
- Test: `backend/tests/test_asset3d_rig.py`

- [ ] **Step 1 : relire la doc et figer les paramètres**

WebFetch `https://docs.meshy.ai/en/api/rigging` et `https://docs.meshy.ai/en/api/animation` (prompt : « quote field names, limits, credits »). Comparer au tableau « Références vérifiées » ; si un champ diffère, corriger la constante correspondante de `asset3d_rig.py` ET la ligne du tableau, avec la date.

- [ ] **Step 2 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""P1 — rig Meshy d'un job fal. Le banc ne sort jamais : upload fal stubbé,
Meshy en MESHY_MOCK, GLB fabriqués par gltf_builder, relus par
mesh_edit.rig_inventory. Run : python tests/test_asset3d_rig.py"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["MESHY_MOCK"] = "1"; os.environ["MESHY_MOCK_SPEED"] = "0.005"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3, gltf_builder, mesh_edit, mesh_report  # noqa: E402
from app.services import asset3d_rig as RIG                      # noqa: E402

UPLOADS = []


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name); return f"https://fal.test/{pathlib.Path(p).name}"


A3._upload = _faux_upload


def _png() -> bytes:
    import io
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (4, 4), (200, 90, 40)).save(b, "PNG"); return b.getvalue()


def _job(nom: str, texture: bool = True) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    maps = {"basecolor": _png()} if texture else {}
    (d / "model.glb").write_bytes(gltf_builder.build_glb(maps, None, "cube", nom))
    A3.write_manifest(d, {"engine": "tripo-h3.1", "stage": "final", "version": 1,
                          "texture_mode": "meshy:2k" if texture else "no", "shots": []})
    mesh_report.write_report(nom, "model.glb", version=1, avec_silhouettes=False)
    A3.approve(nom, True)
    return d


def test_le_devis_lit_les_faces_et_dit_si_le_remesh_est_requis():
    _job("rig_devis")
    d = RIG.devis("rig_devis", actions=[0])
    assert d["tris"] == 12 and d["remesh_requis"] is False and d["credits"] == {"meshy": 8.0}, d
    RIG.RIG_MAX_FACES = 10                        # un cube de 12 faces dépasse
    try:
        assert RIG.devis("rig_devis")["remesh_requis"] is True
    finally:
        RIG.RIG_MAX_FACES = 300_000


def test_un_maillage_nu_est_refuse_avant_toute_depense():
    _job("rig_nu", texture=False); UPLOADS.clear()
    try:
        asyncio.run(RIG.rigger_asset3d("rig_nu")); raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "texture" in str(e).lower(), e
    assert UPLOADS == [], "rien ne doit partir chez fal avant la porte"


def test_le_rig_ecrit_une_version_squelettee_et_ses_animations():
    d = _job("rig_ok"); UPLOADS.clear()
    r = asyncio.run(RIG.rigger_asset3d("rig_ok", height_m=1.8, actions=[0]))
    assert r["version"] == 2 and r["file"] == "model.v2.glb", r
    assert mesh_edit.rig_inventory((d / "model.v2.glb").read_bytes())["a_squelette"]
    anims = RIG.animations_du_job("rig_ok")
    noms = {a["nom"] for a in anims}
    assert noms == {"walking", "running", "action_0"}, noms
    for a in anims:
        assert (d / a["file"]).is_file() and mesh_edit.rig_inventory((d / a["file"]).read_bytes())["clips"]
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["rig"]["height_m"] == 1.8 and man["rig"]["remesh_task"] is None
    reg = mesh_report.read_registry("rig_ok")
    assert reg["current"] == "model.v2.glb" and reg["entries"][-1]["source"]["operation"] == "rig"
    assert UPLOADS == ["model.glb"], UPLOADS       # le GLB courant, une fois


def test_au_dela_de_300000_faces_le_remesh_precede_le_rig():
    d = _job("rig_gros"); RIG.RIG_MAX_FACES = 10
    try:
        r = asyncio.run(RIG.rigger_asset3d("rig_gros"))
    finally:
        RIG.RIG_MAX_FACES = 300_000
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["rig"]["remesh_task"] and man["rig"]["remesh_task"] != man["rig"]["meshy_task"]
    assert r["remesh"] is True


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_rig)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 3 : lancer** — `python tests/test_asset3d_rig.py` → `ModuleNotFoundError: No module named 'app.services.asset3d_rig'`.

- [ ] **Step 4 : le service**

```python
# -*- coding: utf-8 -*-
"""Rig et animations Meshy pour un job `assets3d` (fal) — R10e P1.

docs.meshy.ai/en/api/rigging et /api/animation relues le 03/09/2026 :
  - POST openapi/v1/rigging : `model_url` (.glb, face vers +Z) OU `input_task_id`,
    `height_meters` (défaut 1.7) ; humanoïdes TEXTURÉS seulement ; au-delà de
    300 000 faces : remesh d'abord (POST openapi/v1/remesh, 100–300 000 polys) ;
    réponse result.rigged_character_glb_url + result.basic_animations.{walking,
    running}_glb_url ; 5 crédits.
  - POST openapi/v1/animations : `rig_task_id`, `action_id` (entier de la
    bibliothèque) ; réponse result.animation_glb_url ; 3 crédits l'action.
Le proxy allowliste déjà ces trois chemins (meshy_service.ALLOWED_BASES) — ce
module RELIE le flux fal à ce qui était déjà atteignable.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.services import asset3d_service as A3
from app.services import meshy_service as MS

logger = logging.getLogger(__name__)

RIG_BASE = "openapi/v1/rigging"
ANIM_BASE = "openapi/v1/animations"
REMESH_BASE = "openapi/v1/remesh"
RIG_MAX_FACES = 300_000              # docs.meshy.ai/en/api/rigging, 03/09/2026
RIG_REMESH_POLYCOUNT = 100_000       # sous la limite, topologie triangle
ANIMS_DE_BASE = ("walking", "running")
ACTIONS = {0: "Idle", 1: "Walking_Woman", 4: "Attack", 8: "Dead", 11: "Idle_02"}


def _urls_du_rig(task: dict) -> dict:
    """{'rig', 'rig_fbx', 'walking', 'running'} → URL, depuis la forme
    documentée (result.*). La clé historique du mock reste acceptée."""
    res = task.get("result") if isinstance(task.get("result"), dict) else task
    out = {}
    glb = res.get("rigged_character_glb_url") or res.get("rigged_model_url")
    if glb:
        out["rig"] = glb
    if res.get("rigged_character_fbx_url"):
        out["rig_fbx"] = res["rigged_character_fbx_url"]
    for nom in ANIMS_DE_BASE:
        u = (res.get("basic_animations") or {}).get(f"{nom}_glb_url")
        if u:
            out[nom] = u
    return out


def devis(job: str, actions=()) -> dict:
    """Ce que le rig coûtera, AVANT : les faces sont LUES sur le GLB courant."""
    from app.services import mesh_optimize, pricing
    d = A3._job_dir(job)
    nom = A3._glb_courant(job)
    st = mesh_optimize.glb_stats(d / nom)
    remesh = st["tris"] > RIG_MAX_FACES
    est = pricing.estimate({"kind": "asset3d_rig", "remesh_requis": remesh,
                            "actions": list(actions or [])})
    return {"fichier": nom, "tris": st["tris"], "remesh_requis": remesh, **est}


def _texturee(glb: Path) -> bool:
    from app.services import mesh_report
    return int((mesh_report.gltf_inventory(glb) or {}).get("textures") or 0) > 0


async def rigger_asset3d(job: str, *, height_m: float = 1.7, actions=(),
                         on_step=None) -> dict:
    """Rig Meshy du GLB courant → model.v{n}.glb (squelette) + anim_*.v{n}.glb.
    Refuse AVANT toute dépense : géométrie non approuvée, maillage sans texture
    (Meshy le refuse — autant le dire ici, gratuitement)."""
    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    d = A3._job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    man = A3.read_manifest(job)
    if not A3.approval(job).get("approved"):
        raise PermissionError("Géométrie non approuvée : valide le volume avant de payer un rig.")
    src = d / A3._glb_courant(job)
    if not _texturee(src):
        raise ValueError("Meshy ne rigge que des maillages TEXTURÉS (docs 03/09/2026) : "
                         "texture-le d'abord (POST …/texturer), puis reviens.")
    from app.services import mesh_optimize
    tris = mesh_optimize.glb_stats(src)["tris"]
    h = float(height_m) if float(height_m) > 0 else 1.7

    await _step("Envoi du maillage", 15)
    model_url = await A3._upload(src)

    remesh_id = None
    if tris > RIG_MAX_FACES:
        await _step(f"Remesh Meshy ({tris} faces > {RIG_MAX_FACES})", 25)
        remesh_id = await MS.create_task(REMESH_BASE, {
            "model_url": model_url, "topology": "triangle",
            "target_polycount": RIG_REMESH_POLYCOUNT, "target_formats": ["glb"]})
        await MS.record_created(remesh_id, REMESH_BASE, {"target_polycount": RIG_REMESH_POLYCOUNT})
        t = await A3._attendre_meshy(REMESH_BASE, remesh_id, on_step, depart=25, fin=45)
        await MS.record_state(t, REMESH_BASE)
        payload = {"input_task_id": remesh_id, "height_meters": h}
    else:
        payload = {"model_url": model_url, "height_meters": h}

    await _step("Meshy rigging", 50)
    tid = await MS.create_task(RIG_BASE, payload)
    await MS.record_created(tid, RIG_BASE, payload)
    task = await A3._attendre_meshy(RIG_BASE, tid, on_step, depart=50, fin=80)
    await MS.record_state(task, RIG_BASE)
    urls = _urls_du_rig(task)
    if "rig" not in urls:
        raise RuntimeError(f"meshy: la tâche {tid} n'a rendu aucun GLB riggé "
                           f"(clés : {sorted(urls) or 'aucune'})")

    # ── crédits CONSOMMÉS : le squelette entre dans le registre tout de suite
    v = A3.next_version(job)
    dest = d / f"model.v{v}.glb"
    dest.write_bytes(await MS._fetch_url(urls["rig"]))
    anims: dict[str, str] = {}
    for nom in ANIMS_DE_BASE:
        if nom in urls:
            f = d / f"anim_{nom}.v{v}.glb"
            f.write_bytes(await MS._fetch_url(urls[nom]))
            anims[nom] = f.name
    for i, aid in enumerate(actions or []):
        await _step(f"Animation {i + 1}/{len(actions)}", 82 + 10 * (i + 1) // max(1, len(actions)))
        a_payload = {"rig_task_id": tid, "action_id": int(aid)}
        atid = await MS.create_task(ANIM_BASE, a_payload)
        await MS.record_created(atid, ANIM_BASE, a_payload)
        at = await A3._attendre_meshy(ANIM_BASE, atid, None)
        await MS.record_state(at, ANIM_BASE)
        res = at.get("result") or {}
        if res.get("animation_glb_url"):
            f = d / f"anim_action_{int(aid)}.v{v}.glb"
            f.write_bytes(await MS._fetch_url(res["animation_glb_url"]))
            anims[f"action_{int(aid)}"] = f.name

    A3.write_manifest(d, {**man, "version": v, "file": dest.name,
                          "rig": {"meshy_task": tid, "remesh_task": remesh_id,
                                  "height_m": h, "animations": anims,
                                  "rig_fbx_url": urls.get("rig_fbx")}})
    from app.services import mesh_report
    await asyncio.to_thread(mesh_report.write_report, job, dest.name, version=v,
                            extra={"outil": "meshy", "operation": "rig",
                                   "meshy_task": tid, "remesh_task": remesh_id,
                                   "animations": sorted(anims)})
    await _step("Complete", 100)
    return {"version": v, "file": dest.name, "meshy_task": tid,
            "remesh": remesh_id is not None, "animations": anims,
            "url": f"/api/assets/3d/{job}/version/{v}"}


def animations_du_job(job: str) -> list[dict]:
    """Les clips rapatriés qui existent VRAIMENT sur le disque."""
    d = A3._job_dir(job)
    try:
        rig = A3.read_manifest(job).get("rig") or {}
    except FileNotFoundError:
        return []
    return [{"nom": nom, "file": f, "url": f"/api/assets/3d/{job}/animation/{nom}"}
            for nom, f in sorted((rig.get("animations") or {}).items())
            if (d / str(f)).is_file()]
```

- [ ] **Step 5 : les routes** (avant `get_asset3d_file`)

```python
def _asset3d_approuve(job: str) -> bool:
    from app.services.asset3d_service import approval
    return bool(approval(job).get("approved"))


@router.get("/assets/3d/{job}/rig/devis")
async def asset3d_rig_devis(job: str, actions: str = ""):
    from app.services import asset3d_rig as RIG
    acts = [int(a) for a in actions.split(",") if a.strip().isdigit()]
    try:
        return RIG.devis(job, acts)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/assets/3d/{job}/rig")
async def asset3d_rig(job: str, background_tasks: BackgroundTasks, body: dict = None):
    """Body: {height_m?: 1.7, actions?: [0, 4]}. Refus AVANT le job : clé,
    approbation, texture. Rend un job_id à poller."""
    from app.services import asset3d_rig as RIG, meshy_service as MS
    from app.services.asset3d_service import _job_dir as _jd, _glb_courant as _gc
    body = body or {}
    if not MS.mock_enabled() and not settings.MESHY_API_KEY.strip():
        raise HTTPException(400, "MESHY_API_KEY absente — Réglages.")
    try:
        d = RIG.devis(job, body.get("actions") or [])
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    if not _asset3d_approuve(job):
        raise HTTPException(409, "Géométrie non approuvée : POST …/approve d'abord.")
    if not RIG._texturee(_jd(job) / _gc(job)):
        raise HTTPException(400, "Maillage sans texture : Meshy refuse le rig — "
                                 "texture-le d'abord (POST …/texturer).")
    h = float(body.get("height_m") or 1.7)
    acts = [int(a) for a in (body.get("actions") or [])]
    lancement = await _lancer_job_asset3d(
        background_tasks, job=job, titre=f"3D · rig Meshy ({d['credits']['meshy']:.0f} cr)",
        etape="Rig Meshy",
        travail=lambda on_step: RIG.rigger_asset3d(job, height_m=h, actions=acts, on_step=on_step),
        cost_meta=lambda r: {"job": Path(job).name, "rig": True, "version": r["version"],
                             "meshy_task": r["meshy_task"], "animations": r["animations"]})
    return {**lancement, "devis": d}


@router.get("/assets/3d/{job}/animations")
async def asset3d_animations(job: str):
    from app.services import asset3d_rig as RIG
    return {"animations": RIG.animations_du_job(job)}


@router.get("/assets/3d/{job}/animation/{nom}")
async def asset3d_animation(job: str, nom: str):
    from app.services import asset3d_rig as RIG
    for a in RIG.animations_du_job(job):
        if a["nom"] == Path(nom).name:
            p = settings.outputs_path / "assets3d" / Path(job).name / a["file"]
            return FileResponse(p, media_type="model/gltf-binary", filename=a["file"])
    raise HTTPException(404, "animation inconnue pour ce job")
```

- [ ] **Step 6 : relancer** — `python tests/test_asset3d_rig.py` → `OK — 4 tests, 0 rouge(s) (asset3d_rig)`.

- [ ] **Step 7 : le panneau « Atelier fal » de /studio3d**

`frontend/studio3d/index.html`, dans `<aside class="rail-left">`, après la section « Transport » :

```html
    <section id="falPanel" class="hidden">
      <div class="dt-label">Atelier fal · job courant</div>
      <select id="falJob" title="Jobs Game Assets 3D (fal) et adoptions"></select>
      <div class="engine-note" id="falJobNote">—</div>
      <div class="fld-row">
        <label class="fld"><span>taille (m)</span><input type="number" id="rigH" value="1.7" step="0.05" min="0.3"></label>
        <label class="fld"><span>actions</span><input type="text" id="rigActions" placeholder="0,4" title="ids de la bibliothèque Meshy : 0 Idle · 1 Walking_Woman · 4 Attack · 8 Dead · 11 Idle_02"></label>
      </div>
      <button id="btnRig" class="btn-run">Rig Meshy · —</button>
      <select id="animPick" class="hidden"></select>
    </section>
```

`frontend/studio3d/fal.js` (module autonome, importé par `studio3d.js`) :

```js
/* Atelier fal du 3D Studio — P1 rig, P4 conversion, P5 vues, D2 banc, D5 photos.
   Aucun état partagé avec le graphe Meshy : ce module parle aux routes
   /api/assets/3d/* et montre le résultat dans le même <model-viewer>. */
"use strict";
const $ = (s) => document.querySelector(s);
export const jget = async (p) => { const r = await fetch(p); if (!r.ok) throw new Error(`${p} → ${r.status}`); return r.json(); };
export const jpost = async (p, b) => { const r = await fetch(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `${p} → ${r.status}`); return j; };
export const F = { jobs: [], job: null, poll: null };

export async function chargerJobs() {
  const s = await jget("/api/etabli/sources");
  F.jobs = (s.jobs || []).filter((j) => j.etapes && j.etapes.length);
  const sel = $("#falJob");
  sel.innerHTML = F.jobs.map((j) => `<option value="${j.id}">${j.nom} · ${j.moteur || "?"} · v${j.etapes[j.etapes.length - 1].version || "?"}</option>`).join("");
  F.job = F.jobs[0] ? F.jobs[0].id : null;
  await rafraichirDevis();
}

export async function rafraichirDevis() {
  if (!F.job) { $("#btnRig").textContent = "Rig Meshy · aucun job"; return; }
  try {
    const d = await jget(`/api/assets/3d/${F.job}/rig/devis?actions=${encodeURIComponent($("#rigActions").value)}`);
    $("#falJobNote").textContent = `${d.fichier} · ${d.tris.toLocaleString("fr-FR")} tris${d.remesh_requis ? " · remesh requis (> 300 000)" : ""}`;
    $("#btnRig").textContent = `Rig Meshy · ${d.credits.meshy} cr`;
  } catch (e) { $("#falJobNote").textContent = String(e.message || e); }
}

export function suivre(jobId, onDone) {
  clearInterval(F.poll);
  F.poll = setInterval(async () => {
    const j = await jget(`/api/jobs/${jobId}`).catch(() => null);
    if (!j) return;
    $("#mEta").textContent = `${j.current_step || ""} ${j.progress || 0}%`;
    if (j.status === "done" || j.status === "failed") { clearInterval(F.poll); onDone(j); }
  }, 2500);
}

export function montrerGlb(url, animation) {
  const box = $("#previewBox"); $("#previewPh").classList.add("hidden");
  let mv = box.querySelector("model-viewer");
  if (!mv) { mv = document.createElement("model-viewer"); mv.setAttribute("camera-controls", ""); mv.setAttribute("interaction-prompt", "none"); box.insertBefore(mv, box.firstChild); }
  mv.setAttribute("src", url);
  if (animation) { mv.setAttribute("autoplay", ""); mv.setAttribute("animation-name", animation); } else { mv.removeAttribute("autoplay"); }
}

export async function lancerRig() {
  const actions = $("#rigActions").value.split(",").map((s) => s.trim()).filter(Boolean).map(Number);
  const r = await jpost(`/api/assets/3d/${F.job}/rig`, { height_m: Number($("#rigH").value) || 1.7, actions });
  suivre(r.job_id, async (j) => {
    if (j.status !== "done") { alert(`Rig échoué : ${j.error || "?"}`); return; }
    const a = await jget(`/api/assets/3d/${F.job}/animations`);
    const pick = $("#animPick"); pick.classList.toggle("hidden", !a.animations.length);
    pick.innerHTML = a.animations.map((x) => `<option value="${x.url}">${x.nom}</option>`).join("");
    pick.onchange = () => montrerGlb(pick.value, "walking");
    if (a.animations[0]) montrerGlb(a.animations[0].url, "walking");
  });
}

export function brancher() {
  $("#btnRig").addEventListener("click", () => lancerRig().catch((e) => alert(e.message)));
  $("#falJob").addEventListener("change", (ev) => { F.job = ev.target.value; rafraichirDevis(); });
  $("#rigActions").addEventListener("change", rafraichirDevis);
}
```

`studio3d.js` : en tête `import * as FAL from "./fal.js";` ; ligne 947 remplacer `$("#engineGoto").addEventListener("click", () => gotoSubtab("3d"));` par `$("#engineGoto").addEventListener("click", () => { $("#falPanel").classList.remove("hidden"); FAL.chargerJobs().catch((e) => toast(e.message)); }); FAL.brancher();` et changer le libellé du bouton dans `index.html` en `→ Atelier fal (vues, rig, conversion)`.

- [ ] **Step 8 : vérification à l'écran (utilisateur)** — `MESHY_MOCK=1`, ouvrir `/studio3d`, choisir un moteur fal, « Atelier fal », un job texturé, « Rig Meshy · 5 cr » → à la fin, le `<model-viewer>` joue `walking` (attribut `autoplay` : **c'est ici qu'on mesure** que la version vendue de model-viewer l'honore ; sinon le noter dans « Incertitudes » et retomber sur `mv.play()` via `availableAnimations`).

- [ ] **Step 9 : commit**

```
git add backend/app/services/asset3d_rig.py backend/app/api/routes.py backend/tests/test_asset3d_rig.py frontend/studio3d/fal.js frontend/studio3d/index.html frontend/studio3d/studio3d.js
git commit -m 'moteurs 3d : P1 - rig et animations Meshy relies au flux fal, GLB anime rapatrie et lu' -m 'docs.meshy.ai relues le 03/09/2026 : remesh automatique au-delà de 300 000 faces, refus gratuit d un maillage nu, marche et course incluses, actions de la bibliothèque à 3 cr. Version squelettée dans le registre, clips à côté, panneau Atelier fal dans /studio3d.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 3 : P2 — LOD en chaîne, perte mesurée, budget par usage

**Files:**
- Create: `backend/app/services/mesh_lod.py`
- Modify: `backend/app/api/routes.py` (4 routes, déclarées AVANT `@router.get("/assets/3d/{job}/{fmt}")` — ce catch-all à un segment avalerait sinon `/lod`)
- Create: `scripts/patch_bundle_asset3dlod.py`
- Test: `backend/tests/test_mesh_lod.py`

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""P2 — chaîne de LOD, perte mesurée, budget par usage. Le banc relit les GLB
ÉCRITS (compteurs, noms de mesh), les PNG de silhouette écrits et lod.json ;
gltfpack est le vrai binaire embarqué. Run : python tests/test_mesh_lod.py"""
import io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                             # noqa: E402
from app.config import settings                                   # noqa: E402
from app.services import gltf_builder, mesh_edit, mesh_lod, mesh_optimize  # noqa: E402


def _job(nom: str, forme: str = "sphere") -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, forme, nom))
    return d


def test_les_budgets_par_usage_sont_decroissants_et_motives():
    b = {x["id"]: x for x in mesh_lod.budgets()}
    assert set(b) == {"mobile", "pc", "impression"}, sorted(b)
    for x in b.values():
        assert x["label"] and x["pourquoi"], x
        n = x["niveaux"]
        assert n == sorted(n, reverse=True) and len(set(n)) == len(n), x


def test_un_budget_plus_lourd_que_la_source_est_refuse_en_le_disant():
    _job("lod_refus")
    try:
        mesh_lod.chaine("lod_refus", niveaux=[10_000_000])
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "n'allègerait rien" in str(e), e
    try:
        mesh_lod.chaine("lod_refus", niveaux=[2000, 3000])
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "DÉCROÎTRE" in str(e), e


def test_la_chaine_ecrit_quatre_glb_nommes_pour_unity():
    d = _job("lod_ok")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    info = mesh_lod.chaine("lod_ok", niveaux=[src // 2, src // 6, src // 20])
    assert [n["niveau"] for n in info["niveaux"]] == [0, 1, 2, 3], info
    precedent = None
    for n in info["niveaux"]:
        p = d / "lod" / n["file"]
        assert p.is_file(), n
        lus = mesh_optimize.glb_stats(p)                 # on RELIT le fichier
        assert lus["tris"] == n["tris"], (n, lus)
        if precedent is not None:
            assert lus["tris"] < precedent, (n, precedent)
        precedent = lus["tris"]
        doc, _ = mesh_edit.lire_glb(p.read_bytes())
        noms = [m.get("name") or "" for m in doc["meshes"]]
        assert noms and all(x.endswith(f"_LOD{n['niveau']}") for x in noms), (n, noms)
        noeuds = [q.get("name") or "" for q in doc["nodes"] if "mesh" in q]
        assert noeuds and all(x.endswith(f"_LOD{n['niveau']}") for x in noeuds), (n, noeuds)


def test_la_perte_est_mesuree_contre_le_LOD0_et_croit_avec_la_decimation():
    d = _job("lod_perte")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    info = mesh_lod.chaine("lod_perte", niveaux=[src // 2, src // 20])
    n0, n1, n2 = info["niveaux"]
    assert n0["perte"]["iou_min"] == 1.0 and n0["perte"]["ecart_normales"] == 0.0
    for n in (n1, n2):
        assert n["perte"]["mesure"] is True, n
        assert set(n["perte"]["iou"]) == {"face", "profil", "dessus"}, n
        assert 0.0 < n["perte"]["iou_min"] <= 1.0, n
        assert 0.0 <= n["perte"]["ecart_normales"] <= 1.0, n
        for vue in ("face", "profil", "dessus"):
            assert (d / "lod" / f"sil_lod{n['niveau']}"
                    / f"silhouette_{vue}.png").is_file(), n
    assert n2["perte"]["ecart_normales"] > n1["perte"]["ecart_normales"], (n1, n2)
    assert n2["perte"]["iou_min"] <= n1["perte"]["iou_min"] + 1e-9, (n1, n2)
    # la silhouette SEULE ne suffit pas : c'est pourquoi l'écart de normales existe
    assert n1["perte"]["iou_min"] > 0.9 and n1["perte"]["ecart_normales"] > 0.0, n1
    relu = json.loads((d / "lod" / "lod.json").read_text("utf-8"))
    assert relu == info, "lod.json doit être exactement ce qui est rendu"


def test_une_chaine_neuve_efface_les_niveaux_de_la_precedente():
    d = _job("lod_rejeu")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    mesh_lod.chaine("lod_rejeu", niveaux=[src // 2, src // 6, src // 20])
    assert (d / "lod" / "lod3.glb").is_file()
    mesh_lod.chaine("lod_rejeu", niveaux=[src // 3])
    assert not (d / "lod" / "lod3.glb").exists(), "LOD3 orphelin de la chaîne d'avant"
    assert (d / "model.glb").is_file(), "la source n'est JAMAIS touchée"


def test_l_archive_porte_les_glb_le_json_et_le_lisezmoi():
    d = _job("lod_zip")
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    mesh_lod.chaine("lod_zip", niveaux=[src // 2, src // 8])
    nom, octets = mesh_lod.archive("lod_zip")
    assert nom == "lod_zip_LOD.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert noms == ["LISEZMOI.txt", "lod.json", "lod0.glb", "lod1.glb",
                        "lod2.glb"], noms
        txt = z.read("LISEZMOI.txt").decode("utf-8")
        assert "_LOD" in txt and "Godot" in txt and "IoU" in txt, txt[:400]
        assert mesh_edit.lire_glb(z.read("lod1.glb"))[0]["meshes"], "GLB illisible"


def test_la_signature_de_normales_distingue_un_cube_d_une_sphere():
    from app.services import print3d
    cube = print3d.lire_glb_triangles(gltf_builder.build_glb({}, None, "cube", "c"))
    sph = print3d.lire_glb_triangles(gltf_builder.build_glb({}, None, "sphere", "s"))
    sc, ss = mesh_lod.signature_normales(cube), mesh_lod.signature_normales(sph)
    assert abs(sum(sc) - 1.0) < 1e-3 and abs(sum(ss) - 1.0) < 1e-3
    assert mesh_lod.ecart_normales(sc, sc) == 0.0
    assert mesh_lod.ecart_normales(sc, ss) > 0.4, mesh_lod.ecart_normales(sc, ss)


def test_les_routes_lod_sont_declarees_avant_le_catch_all():
    """Le catch-all `/assets/3d/{job}/{fmt}` avalerait `/lod` : FastAPI sert la
    PREMIÈRE route déclarée qui apparie. On lit l'ordre réel du routeur."""
    from app.api.routes import router
    chemins = [r.path for r in router.routes if hasattr(r, "path")]
    fmt = chemins.index("/assets/3d/{job}/{fmt}")
    for p in ("/assets/3d/{job}/lod", "/assets/3d/{job}/lod/{niveau}",
              "/assets/3d/{job}/lod-zip"):
        assert p in chemins, p
        assert chemins.index(p) < fmt, f"{p} déclarée APRÈS le catch-all"


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_lod)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer, constater le rouge**

```
python tests/test_mesh_lod.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.mesh_lod'` (l'import de tête casse avant les tests — c'est le rouge voulu).

- [ ] **Step 3 : le service**

Créer `backend/app/services/mesh_lod.py` :

```python
# -*- coding: utf-8 -*-
"""LOD en chaîne, perte mesurée, budget par usage — R10e P2.

Trois choses que `mesh_optimize` ne fait pas :
  1. une CHAÎNE (LOD0 = la source, puis LOD1, LOD2…) écrite ensemble, nommée
     pour le moteur et livrée en une archive ;
  2. la PERTE, mesurée par niveau : IoU des trois silhouettes contre le LOD0
     (le rasteriseur de `mesh_report`) ET écart de la signature de normales —
     parce qu'une bosse aplatie garde sa silhouette et perd ses normales ;
  3. un BUDGET par usage, proposé et motivé, jamais imposé.

Tout est local et gratuit. `gltfpack 1.2 -h` mesuré le 03/09/2026 : entrées
.obj/.gltf/.glb, sorties .gltf/.glb, `-si R`, `-sa`, `-se E`, `-slb`, `-kn`,
`-km`, `-noq`, `-r fichier`. Pas de numpy : la signature de normales est un
histogramme sphérique en Python pur, borné par MAX_TRIS_SIGNATURE.

Le dossier `lod/` est DÉRIVÉ (recalculable depuis la source), pas une version
au sens de la doctrine §2.1 : une chaîne neuve le remplace en entier, sans
quoi un LOD3 de la chaîne précédente survivrait à côté d'un LOD1 de la
nouvelle. Le maillage source, lui, n'est jamais touché.
"""
from __future__ import annotations

import io
import json
import math
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Budgets par usage. Les nombres sont des CHOIX de départ, pas des mesures :
# ils sont éditables par `niveaux`, et le banc de référence (D2, Task 8) les
# corrigera avec des chiffres du terrain. Ce qui est mesuré ici, c'est la
# PERTE qu'ils coûtent — affichée à côté de chacun.
BUDGETS = {
    "mobile": {
        "label": "Mobile / WebGL",
        "niveaux": [10_000, 4_000, 1_500],
        "pourquoi": "Un personnage de premier plan sur téléphone tient sous "
                    "10 000 triangles ; les deux niveaux suivants servent aux "
                    "silhouettes de fond.",
    },
    "pc": {
        "label": "PC / console",
        "niveaux": [60_000, 20_000, 6_000],
        "pourquoi": "Le LOD0 garde le détail du gros plan ; LOD1 tient la "
                    "distance moyenne, LOD2 le décor lointain.",
    },
    "impression": {
        "label": "Impression 3D",
        "niveaux": [200_000],
        "pourquoi": "L'impression ne fait PAS de LOD : un seul palier, assez "
                    "haut pour que la buse ne voie pas les facettes, assez bas "
                    "pour que le slicer ne rame pas.",
    },
}
MAX_NIVEAUX = 8            # docs.unity3d.com : 8 LOD au plus dans un LOD Group
MAX_TRIS_SIGNATURE = 400_000
SIG_BINS = 8
SIL_PX = 256               # 3 vues x N niveaux : 65 536 px par IoU, tenable
_VUES = ("face", "profil", "dessus")


def budgets() -> list[dict]:
    """Les budgets, pour l'UI et pour la route."""
    return [{"id": k, **v} for k, v in BUDGETS.items()]


def _job_dir(job):
    from app.services import mesh_report
    return mesh_report.job_dir(job)


# ── nommage moteur ───────────────────────────────────────────────────────────

def _renommer(data: bytes, n: int) -> bytes:
    """Suffixe `_LOD{n}` sur chaque mesh ET sur les nœuds qui en portent un.

    docs.unity3d.com/Manual/lod-group-configure.html, relue le 03/09/2026 :
    « Add the suffix _LODX to the name of each mesh … ExampleMeshName_LOD0 » —
    le guide exporte en .fbx, donc en GLB l'import Unity ne fabrique pas
    forcément le LOD Group tout seul. Ce qu'on promet est le NOM, pas le
    composant. Godot (docs.godotengine.org, node_type_customization, relue le
    03/09/2026 : `-col`, `-convcol`, `-rigid`, `-noimp`, `-loop`…) ne
    documente AUCUN suffixe LOD : il reçoit des noms lisibles, rien de plus.
    Le LISEZMOI de l'archive le dit aux deux.
    """
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(data)
    suffixe = f"_LOD{int(n)}"
    for i, m in enumerate(doc.get("meshes") or []):
        m["name"] = (m.get("name") or f"mesh_{i}").split("_LOD")[0] + suffixe
    for i, nd in enumerate(doc.get("nodes") or []):
        if "mesh" in nd:
            nd["name"] = (nd.get("name") or f"node_{i}").split("_LOD")[0] + suffixe
    return mesh_edit.ecrire_glb(doc, binc)


# ── la perte : silhouettes + normales ────────────────────────────────────────

def signature_normales(tris, bins: int = SIG_BINS) -> list[float]:
    """Histogramme des normales de face PONDÉRÉ PAR L'AIRE, en (cos θ, φ).

    Rendu normalisé (somme = 1), donc comparable entre deux maillages de
    comptes très différents : c'est une fraction d'aire par direction. Les
    triangles d'aire nulle n'ont pas de normale et sont ignorés — les compter
    fabriquerait une direction arbitraire (même leçon que le `continue` des
    dégénérés dans `mesh_report.geometry`).
    """
    largeur = 2 * int(bins)
    h = [0.0] * (int(bins) * largeur)
    total = 0.0
    for t in tris:
        ux, uy, uz = (t[1][0] - t[0][0], t[1][1] - t[0][1], t[1][2] - t[0][2])
        vx, vy, vz = (t[2][0] - t[0][0], t[2][1] - t[0][1], t[2][2] - t[0][2])
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        norme = math.sqrt(nx * nx + ny * ny + nz * nz)
        if norme <= 1e-12:
            continue
        aire = norme * 0.5
        i = min(int(bins) - 1, int((nz / norme + 1.0) * 0.5 * int(bins)))
        phi = math.atan2(ny, nx)
        j = min(largeur - 1, int((phi + math.pi) / (2 * math.pi) * largeur))
        h[i * largeur + j] += aire
        total += aire
    if total <= 0:
        raise ValueError("maillage sans aire : signature de normales impossible")
    return [round(v / total, 6) for v in h]


def ecart_normales(a, b) -> float:
    """Distance en variation totale entre deux signatures : 0 = identiques,
    1 = disjointes. C'est la FRACTION D'AIRE qui a changé de direction — un
    nombre lisible, pas un score arbitraire."""
    if len(a) != len(b):
        raise ValueError("signatures de tailles différentes")
    return round(0.5 * sum(abs(x - y) for x, y in zip(a, b)), 4)


def _mesurer_perte(dossier: Path, niveau: int, fichier: str,
                   ref_sig=None) -> dict:
    """Silhouettes du niveau + IoU contre le LOD0 + écart de normales.

    Dégrade proprement : un GLB compressé ou trop lourd rend `mesure: False`
    avec la raison, jamais une exception qui ferait tomber une chaîne déjà
    payée en temps de calcul.
    """
    from PIL import Image
    from app.services import asset3d_qc, mesh_report, print3d
    p = dossier / fichier
    try:
        tris = print3d.lire_glb_triangles(p.read_bytes())
    except Exception as e:                       # compressé, buffer externe…
        return {"mesure": False, "raison": str(e)}
    if not tris:
        return {"mesure": False, "raison": "maillage vide"}
    if len(tris) > MAX_TRIS_SIGNATURE:
        return {"mesure": False,
                "raison": f"{len(tris)} triangles > {MAX_TRIS_SIGNATURE}"}
    mesh_report.silhouettes(p, dossier / f"sil_lod{niveau}", px=SIL_PX)
    sig = signature_normales(tris)
    if niveau == 0:
        return {"mesure": True, "signature": sig,
                "iou": {v: 1.0 for v in _VUES}, "iou_min": 1.0,
                "ecart_normales": 0.0}
    ref_dir = dossier / "sil_lod0"
    if ref_sig is None or not ref_dir.is_dir():
        return {"mesure": False,
                "raison": "le LOD0 n'a pas pu être mesuré : rien à comparer"}
    ious = {}
    for vue in _VUES:
        a = Image.open(ref_dir / f"silhouette_{vue}.png").convert("L")
        b = Image.open(dossier / f"sil_lod{niveau}"
                       / f"silhouette_{vue}.png").convert("L")
        ious[vue] = round(asset3d_qc.iou(a, b), 4)
    return {"mesure": True, "signature": sig, "iou": ious,
            "iou_min": min(ious.values()),
            "ecart_normales": ecart_normales(ref_sig, sig)}


# ── la chaîne ────────────────────────────────────────────────────────────────

def _normaliser_niveaux(tris_source: int, usage: str, niveaux=None) -> list[int]:
    from app.services import mesh_optimize
    if niveaux is None:
        if usage not in BUDGETS:
            raise ValueError(
                f"usage inconnu: {usage!r} (attendu: {', '.join(BUDGETS)})")
        niveaux = list(BUDGETS[usage]["niveaux"])
    else:
        try:
            niveaux = [int(v) for v in niveaux]
        except (TypeError, ValueError):
            raise ValueError(f"niveaux invalides: {niveaux!r} — des entiers")
    if not niveaux:
        raise ValueError("il faut au moins un niveau sous le LOD0")
    if len(niveaux) > MAX_NIVEAUX - 1:
        raise ValueError(f"{len(niveaux) + 1} niveaux — Unity en accepte "
                         f"{MAX_NIVEAUX} au plus (LOD Group)")
    out: list[int] = []
    for v in niveaux:
        v = max(mesh_optimize.TARGET_MIN, min(mesh_optimize.TARGET_MAX, v))
        if out and v >= out[-1]:
            raise ValueError("les niveaux doivent DÉCROÎTRE strictement — "
                             f"{v} arrive après {out[-1]}")
        out.append(v)
    if out[0] >= tris_source:
        raise ValueError(
            f"le premier niveau vise {out[0]} triangles pour une source de "
            f"{tris_source} : la chaîne n'allègerait rien. Choisis un budget "
            "plus bas, ou un autre usage.")
    return out


def chaine(job, *, usage: str = "pc", niveaux=None,
           source: str = "model.glb") -> dict:
    """Écrit `lod/lod0.glb … lodN.glb` + `lod/lod.json`. Synchrone (gltfpack) —
    la route l'exécute dans un thread, comme `/optimize`."""
    from app.services import mesh_optimize
    d = _job_dir(job)
    src = d / Path(str(source)).name
    if not src.is_file():
        raise FileNotFoundError(
            f"{Path(str(source)).name} introuvable pour ce job")
    exe = mesh_optimize._gltfpack()
    base = mesh_optimize.glb_stats(src)
    cibles = _normaliser_niveaux(base["tris"], usage, niveaux)

    dossier = d / "lod"
    if dossier.is_dir():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)

    (dossier / "lod0.glb").write_bytes(_renommer(src.read_bytes(), 0))
    niveaux_out = [{"niveau": 0, "file": "lod0.glb", "cible": None,
                    "aggressive": False,
                    **mesh_optimize.glb_stats(dossier / "lod0.glb")}]

    for i, cible in enumerate(cibles, 1):
        out = dossier / f"lod{i}.glb"
        rapport = dossier / f"lod{i}.rapport.json"
        ratio = max(0.001, min(1.0, cible / max(1, base["tris"])))

        def run(extra, _out=out, _rapport=rapport, _ratio=ratio, _i=i):
            r = subprocess.run(
                [exe, "-i", str(src), "-o", str(_out), "-si", f"{_ratio:.6f}",
                 "-noq", "-kn", "-km", "-r", str(_rapport)] + extra,
                capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not _out.is_file():
                raise RuntimeError(
                    f"gltfpack a échoué au LOD{_i} ({r.returncode}) : "
                    f"{(r.stderr or r.stdout or '').strip()[:300]}")

        run([])
        agressif = False
        if mesh_optimize.glb_stats(out)["tris"] > cible * 1.15:
            run(["-sa"])                  # même seuil de rattrapage qu'optimize
            agressif = True
        out.write_bytes(_renommer(out.read_bytes(), i))
        st = {"niveau": i, "file": out.name, "cible": cible,
              "aggressive": agressif, **mesh_optimize.glb_stats(out)}
        try:
            st["gltfpack"] = json.loads(rapport.read_text(encoding="utf-8"))
        except Exception as e:            # rapport absent ou illisible : le dire
            st["gltfpack"] = {"erreur": str(e)}
        niveaux_out.append(st)

    p0 = _mesurer_perte(dossier, 0, "lod0.glb")
    ref_sig = p0.get("signature")
    niveaux_out[0]["perte"] = {k: v for k, v in p0.items() if k != "signature"}
    for st in niveaux_out[1:]:
        p = _mesurer_perte(dossier, st["niveau"], st["file"], ref_sig)
        st["perte"] = {k: v for k, v in p.items() if k != "signature"}

    info = {
        "job": Path(str(job)).name, "source": src.name, "usage": usage,
        "niveaux": niveaux_out,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (dossier / "lod.json").write_text(
        json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    return info


def lire(job) -> dict:
    p = _job_dir(job) / "lod" / "lod.json"
    if not p.is_file():
        raise FileNotFoundError("aucune chaîne de LOD pour ce job")
    return json.loads(p.read_text(encoding="utf-8"))


def _lisezmoi(info: dict) -> str:
    L = [f"Chaîne de LOD — job {info['job']} (source {info['source']}, "
         f"usage {info['usage']}, {info['created_at']})",
         "",
         "Niveau  fichier      triangles     cible   IoU min   écart normales"]
    for n in info["niveaux"]:
        pe = n.get("perte") or {}
        iou = pe.get("iou_min")
        ec = pe.get("ecart_normales")
        cible = str(n["cible"]) if n["cible"] is not None else "—"
        s_iou = f"{iou:.4f}" if iou is not None else "non mesuré"
        s_ec = f"{ec:.4f}" if ec is not None else "non mesuré"
        L.append(f"LOD{n['niveau']}    {n['file']:<12} {n['tris']:>9}  "
                 f"{cible:>8}  {s_iou:>9}   {s_ec}")
    L += [
        "",
        f"IoU : intersection sur union des silhouettes face/profil/dessus "
        f"({SIL_PX} px) contre le LOD0. 1,0 = silhouette identique.",
        "Écart de normales : fraction de l'aire qui a changé de direction "
        "(0 = aucune, 1 = tout). Une bosse aplatie garde sa silhouette et "
        "déplace ses normales : c'est ce que ce nombre voit.",
        "",
        "Unity — docs.unity3d.com/Manual/lod-group-configure.html, relue le "
        "03/09/2026 : le suffixe _LODX sur le nom de chaque mesh est la "
        "convention. Le guide exporte en .fbx ; en GLB, l'import ne crée pas "
        "forcément le LOD Group tout seul — ajoute-le sur le parent et glisse "
        "les niveaux dedans.",
        "Godot — docs.godotengine.org (node_type_customization), relue le "
        "03/09/2026 : les suffixes documentés sont -col, -convcol, -rigid, "
        "-noimp, -loop… AUCUN suffixe LOD. Les noms _LODX ne déclenchent donc "
        "rien : importe les niveaux comme des scènes séparées.",
        "Unreal — importe chaque GLB puis assigne les LOD dans le Static Mesh "
        "Editor. Cette ligne-ci n'est PAS vérifiée dans la documentation : ne "
        "t'appuie pas dessus comme sur les deux précédentes.",
    ]
    return "\n".join(L) + "\n"


def archive(job) -> tuple[str, bytes]:
    """Le ZIP livré : les GLB de la chaîne, lod.json, et le LISEZMOI qui dit ce
    que chaque moteur fait — ou ne fait pas — du suffixe."""
    d = _job_dir(job)
    info = lire(job)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for st in info["niveaux"]:
            z.write(d / "lod" / st["file"], st["file"])
        z.writestr("lod.json", json.dumps(info, indent=1, ensure_ascii=False))
        z.writestr("LISEZMOI.txt", _lisezmoi(info))
    return f"{Path(str(job)).name}_LOD.zip", buf.getvalue()
```

- [ ] **Step 4 : les routes**

Dans `routes.py`, **avant** `@router.get("/assets/3d/{job}/{fmt}")` :

```python
@router.get("/assets/3d/{job}/lod")
async def get_asset3d_lod(job: str):
    """La chaîne écrite, plus les budgets proposés. 200 avec `chaine: null`
    tant qu'aucune chaîne n'existe — l'UI a besoin des budgets AVANT de
    pouvoir en lancer une."""
    from app.services import mesh_lod
    try:
        info = mesh_lod.lire(job)
    except FileNotFoundError:
        info = None
    return {"chaine": info, "budgets": mesh_lod.budgets()}


@router.post("/assets/3d/{job}/lod")
async def post_asset3d_lod(job: str, body: dict = None):
    """Construit la chaîne. Local et gratuit (gltfpack), mais long : exécuté
    dans un thread, comme POST /optimize."""
    from app.services import mesh_lod
    body = body or {}
    niveaux = body.get("niveaux")
    if niveaux is not None and not isinstance(niveaux, list):
        raise HTTPException(400, "niveaux doit être une liste d'entiers.")
    try:
        return await asyncio.to_thread(
            mesh_lod.chaine, job, usage=str(body.get("usage") or "pc"),
            niveaux=niveaux, source=str(body.get("source") or "model.glb"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/assets/3d/{job}/lod/{niveau}")
async def get_asset3d_lod_file(job: str, niveau: int):
    p = (settings.outputs_path / "assets3d" / Path(job).name / "lod"
         / f"lod{int(niveau)}.glb")
    if not p.is_file():
        raise HTTPException(404, f"LOD{int(niveau)} absent — lance la chaîne.")
    return FileResponse(p, media_type="model/gltf-binary", filename=p.name)


@router.get("/assets/3d/{job}/lod-zip")
async def get_asset3d_lod_zip(job: str):
    """L'archive de la chaîne. Le segment est `lod-zip` et non `lod.zip` : un
    point y est légal mais brouille la lecture du catch-all `{fmt}` juste en
    dessous, qui sert `model.<fmt>`."""
    from app.services import mesh_lod
    try:
        nom, octets = await asyncio.to_thread(mesh_lod.archive, job)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return Response(content=octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})
```

- [ ] **Step 5 : relancer**

```
python tests/test_mesh_lod.py
```
Attendu : `OK — 8 tests, 0 rouge(s) (mesh_lod)`.

- [ ] **Step 6 : le patch de bundle (zone « LOD · Textures » sous DzOptimize)**

Créer `scripts/patch_bundle_asset3dlod.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_asset3dlod.py
"""Assert-guarded patcher : zone « LOD · Textures » dans la carte 3D du hub.

BASELINE : bundle POST-patch seedance25 (queue de chaîne au 03/09/2026 —
`python scripts/repatch_all.py --list` : dzrailmotion, version, dznodecat,
seedance25). Backup dédié : .js.bak_asset3dlod.

Ajoute DzLod, greffé juste après la ligne de boutons de DzOptimize (ancre
unique, mesurée) : select d'usage rempli par GET /api/assets/3d/{sh}/lod,
bouton « LOD » (POST), une ligne par niveau avec triangles, IoU min et écart
de normales, et « Archive LOD » vers /lod-zip. Le bouton Textures (P3,
Task 4) rejoindra la MÊME zone et le MÊME script.

Re-jouable : si le .bak existe il est restauré avant application, donc ce
script se relance après une modification sans empiler les patchs.

Run : python scripts/patch_bundle_asset3dlod.py
      python scripts/patch_bundle_asset3dlod.py --check
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "asset3dlod"
MARQUEURS = (("DzLod", 2),)      # definition + greffe ; Task 4 ajoute DzTex


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{TAG} doit rester le DERNIER maillon ; sinon "
                f"python scripts/repatch_all.py --from {TAG}.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    autres = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not autres:
        return False
    top = max(autres)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


BTN = ('style:{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",'
       'background:"var(--surface-2)",border:"1px solid var(--stroke)",'
       'color:"var(--ink)"}')
LIEN = ('style:{fontSize:11,padding:"4px 8px",borderRadius:6,'
        'textDecoration:"none",background:"var(--surface-2)",'
        'border:"1px solid var(--stroke)",color:"var(--cyan)"}')

ANCRE_DEF = 'function DzOptFmt(n){'
ANCRE_ZONE = 'children:cmp?"▣ Simple":"⇆ Comparer"},"cp"):null]},"row"),'

DZ_LOD = (
    'function DzLodNum(v){return v==null?"—":Number(v).toFixed(3)}'
    'function DzLod({sh}){'
    'var DS=x.useState(null),d0=DS[0],setD0=DS[1],'
    'BS=x.useState(!1),busy=BS[0],setBusy=BS[1],'
    'US=x.useState("pc"),us=US[0],setUs=US[1],'
    'ES=x.useState(""),err=ES[0],setErr=ES[1];'
    'x.useEffect(function(){var on=!0;'
    'fetch("/api/assets/3d/"+sh+"/lod")'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(j){on&&j&&setD0(j)}).catch(function(){});'
    'return function(){on=!1}},[sh]);'
    'function run(){if(busy)return;setBusy(!0);setErr("");'
    'fetch("/api/assets/3d/"+sh+"/lod",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({usage:us})})'
    '.then(function(r2){return r2.json().then(function(j){return{ok:r2.ok,j:j}})'
    '.catch(function(){return{ok:r2.ok,j:{}}})})'
    '.then(function(z){setBusy(!1);'
    'if(!z.ok){setErr(String((z.j&&z.j.detail)||"echec LOD"));return}'
    'setD0(function(o){return Object.assign({},o||{},{chaine:z.j})})})'
    '.catch(function(e2){setBusy(!1);setErr(String(e2&&e2.message||e2))})}'
    'var bud=(d0&&d0.budgets)||[],ch=d0&&d0.chaine;'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",'
    'gap:4,marginTop:4},children:['
    'r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center",'
    'flexWrap:"wrap"},children:['
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)"},'
    'children:"LOD"},"lb"),'
    'r.jsx("select",{value:us,onChange:function(ev){setUs(ev.target.value)},'
    + BTN + ',children:bud.map(function(b){return r.jsx("option",'
    '{value:b.id,children:b.label},b.id)})},"sel"),'
    'r.jsx("button",{onClick:run,disabled:busy,' + BTN + ','
    'children:busy?"Chaine…":"⛰ LOD"},"go"),'
    'ch?r.jsx("a",{href:"/api/assets/3d/"+sh+"/lod-zip",download:!0,'
    + LIEN + ',children:"↓ Archive LOD"},"dl"):null]},"row"),'
    'err?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},'
    'children:err},"er"):null,'
    'ch?r.jsx("div",{style:{fontSize:10,fontFamily:"var(--f-mono)",'
    'color:"var(--ink-strong)"},children:ch.niveaux.map(function(n){'
    'var p=n.perte||{};return r.jsxs("div",{children:["LOD",String(n.niveau),'
    '" · ",DzOptFmt(n.tris)," tris · IoU ",DzLodNum(p.iou_min),'
    '" · Δn ",DzLodNum(p.ecart_normales)]},"n"+n.niveau)})},'
    '"st"):null]},"lod")}')

GREFFE = 'r.jsx(DzLod,{sh:sh},"lod"+sh),'


def main():
    args = sys.argv[1:]
    check = "--check" in args
    root = pathlib.Path(".").resolve()
    if not (root / REL_BUNDLE).is_file():
        root = pathlib.Path(__file__).resolve().parent.parent
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        for marq, _want in MARQUEURS:
            if s.count(marq):
                raise SystemExit(
                    f"[{TAG}] marqueur {marq} deja present x{s.count(marq)} "
                    f"dans {src.name} — double application refusee.")
        for tag, a in (("D1-def", ANCRE_DEF), ("D2-zone", ANCRE_ZONE)):
            n = s.count(a)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
        crlf, lf, cr = eol_stats(src.read_bytes())
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] 2 ancres OK, marqueurs absents")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr}")
        return

    if not bak.exists():
        if MARQUEURS[0][0] in read_src(bundle):
            raise SystemExit(f"[{TAG}] marqueur present sans {bak.name} : "
                             "etat ambigu, abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    s = read_src(bundle)
    s = apply(s, ANCRE_DEF, DZ_LOD + ANCRE_DEF, "D1-def")
    s = apply(s, ANCRE_ZONE, ANCRE_ZONE + GREFFE, "D2-zone")
    for marq, want in MARQUEURS:
        n = s.count(marq)
        if n != want:
            raise SystemExit(f"[{TAG}] {marq} x{n} (want {want}). Aborting.")
    bundle.write_text(s, encoding="utf-8", newline="")
    print(f"OK — {TAG} applique. Taille :", bundle.stat().st_size)


if __name__ == "__main__":
    main()
```

Lancer, dans cet ordre :

```
python scripts/patch_bundle_asset3dlod.py --check
python scripts/patch_bundle_asset3dlod.py
python scripts/repatch_all.py --list
```

Attendu : `[asset3dlod] applicable sur …` + `2 ancres OK, marqueurs absents` ; puis `backup -> index-BEOJX8L5.js.bak_asset3dlod` et `OK — asset3dlod applique.` ; enfin la chaîne se termine par une ligne `asset3dlod       OK  (bak …)`.

- [ ] **Step 7 : l'inventaire des fonctions, pas l'œil**

```
python -c "import pathlib,re,sys; sys.stdout.reconfigure(encoding='utf-8'); s=pathlib.Path('frontend/dist/assets/index-BEOJX8L5.js').read_text('utf-8'); f=re.findall(r'function ([A-Za-z_$][\w$]*)\(', s); d=sorted(x for x in set(f) if x.startswith('Dz')); print(len(f), len(set(f))); print(d)"
```
Attendu : la liste `Dz*` contient **`DzLod` ET `DzLodNum` ET `DzOptimize` ET `DzOptFmt`** — c'est la preuve que la greffe a AJOUTÉ sans remplacer. Noter le premier nombre (fonctions totales) : après le patch de la Task 4 il devra augmenter d'exactement 1 de plus.

- [ ] **Step 8 : commit**

```
git add backend/app/services/mesh_lod.py backend/app/api/routes.py backend/tests/test_mesh_lod.py scripts/patch_bundle_asset3dlod.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'moteurs 3d : P2 - chaine de LOD, perte mesuree par niveau, budget par usage' -m 'Les niveaux gltfpack sont écrits ensemble sous lod/, nommés _LODX (docs Unity relues le 03/09/2026 ; Godot ne documente aucun suffixe LOD et le LISEZMOI le dit). La perte est double : IoU des trois silhouettes contre le LOD0, et écart de la signature de normales — une bosse aplatie garde sa silhouette et perd ses normales. Budgets mobile, PC et impression proposés, jamais imposés. Zone LOD dans la carte 3D du hub, un patch en queue de chaîne.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 4 : P3 — export PBR aux conventions moteur

**Files:**
- Create: `backend/app/services/mesh_textures.py`
- Modify: `backend/app/services/material_store.py` (une façade publique `png_bytes`, plus `__all__` ligne 46)
- Modify: `backend/app/api/routes.py` (2 routes, avant le catch-all `{fmt}`)
- Modify: `scripts/patch_bundle_asset3dlod.py` (un composant de plus dans la MÊME zone)
- Test: `backend/tests/test_mesh_textures.py`

- [ ] **Step 1 : trouver le nom réel du convertisseur PNG du Forge**

```
python -c "import re,pathlib,sys; sys.stdout.reconfigure(encoding='utf-8'); s=pathlib.Path('backend/app/services/material_store.py').read_text('utf-8'); print([m for m in re.findall(r'^def (\w+)\(([^)]*)', s, re.M) if 'kind' in m[1] and 'bits' in m[1]])"
```
Attendu : une seule paire `(nom, 'img, kind, bits…')`. C'est la fonction privée qui fait `_as_mode` + `_png16` (bloc « export », vers la ligne 1195). Noter son nom exact — il est appelé `_MAP_PNG` ci-dessous.

- [ ] **Step 2 : la façade publique**

À la fin de `backend/app/services/material_store.py` :

```python
def png_bytes(img, kind: str, bits: int = 8) -> bytes:
    """Les octets PNG d'une map, dans le mode que son genre exige (L, RGB,
    RGBA, 16 bits pour height et normal). Façade PUBLIQUE du convertisseur
    d'export : `mesh_textures` (P3) livre les textures d'un maillage avec
    exactement les mêmes octets que l'archive d'une matière — deux chemins,
    un seul encodeur."""
    return _MAP_PNG(img, kind, bits)
```
(remplacer `_MAP_PNG` par le nom relevé au Step 1), et ajouter `"png_bytes",` à `__all__` (ligne 46, à côté de `"clean_naming", "naming_catalog", "engine_slot"`).

- [ ] **Step 3 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""P3 — textures d'un modèle exportées aux conventions moteur (R10c). Le banc
relit l'ARCHIVE écrite : noms de fichiers, tailles en pixels, modes, bordereau.
Run : python tests/test_mesh_textures.py"""
import io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import gltf_builder, material_store, mesh_textures  # noqa: E402


def _png(couleur, taille=64) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (taille, taille), couleur).save(b, "PNG")
    return b.getvalue()


def _job(nom: str, maps: dict) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(
        gltf_builder.build_glb(maps, None, "cube", "peau"))
    return d


def test_l_inventaire_dit_quels_canaux_le_glb_porte_vraiment():
    _job("tex_inv", {"basecolor": _png((180, 90, 40)),
                     "normal": _png((128, 128, 255))})
    inv = mesh_textures.inventaire("tex_inv")
    assert inv["materiaux"], inv
    m = inv["materiaux"][0]
    assert set(m["canaux"]) >= {"basecolor", "normal"}, m
    assert m["canaux"]["basecolor"]["px"] == [64, 64], m
    assert m["canaux"]["basecolor"]["bytes"] > 0, m
    assert "orm" in inv["manquants"] and "emissive" in inv["manquants"], inv
    assert "basecolor" not in inv["manquants"], inv


def test_un_glb_sans_texture_est_refuse_avant_l_archive():
    _job("tex_nu", {})
    try:
        mesh_textures.exporter("tex_nu")
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "aucune texture" in str(e).lower(), e


def test_l_archive_unity_urp_porte_les_noms_et_le_maskmap():
    _job("tex_urp", {"basecolor": _png((180, 90, 40)),
                     "normal": _png((128, 128, 255))})
    nom, octets = mesh_textures.exporter("tex_urp", naming="unity_urp",
                                         resolution=128)
    assert nom == "tex_urp_unity_urp.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert "peau/peau_BaseMap.png" in noms, noms
        assert "peau/peau_Normal.png" in noms, noms
        assert "peau/peau_MetallicOcclusion.png" in noms, noms
        assert "BORDEREAU.txt" in noms and "textures.json" in noms, noms
        im = Image.open(io.BytesIO(z.read("peau/peau_BaseMap.png")))
        assert im.size == (128, 128), im.size
        mm = Image.open(io.BytesIO(z.read("peau/peau_MetallicOcclusion.png")))
        assert mm.mode == "RGBA", mm.mode
        bord = z.read("BORDEREAU.txt").decode("utf-8")
        assert "Metallic Map ET Occlusion Map" in bord, bord[:400]
        meta = json.loads(z.read("textures.json").decode("utf-8"))
        assert meta["naming"] == "unity_urp" and meta["resolution"] == 128


def test_les_noms_suivent_la_convention_demandee():
    _job("tex_conv", {"basecolor": _png((10, 200, 90))})
    attendus = {
        "standard": "peau/peau_basecolor.png",
        "unreal": "peau/T_peau_BC.png",
        "godot": "peau/peau_albedo.png",
        "unity_hdrp": "peau/peau_BaseMap.png",
    }
    for naming, f in attendus.items():
        _, octets = mesh_textures.exporter("tex_conv", naming=naming,
                                           resolution=64)
        with zipfile.ZipFile(io.BytesIO(octets)) as z:
            assert f in z.namelist(), (naming, sorted(z.namelist()))


def test_la_convention_inconnue_retombe_sur_standard_comme_le_forge():
    _job("tex_alias", {"basecolor": _png((10, 200, 90))})
    nom, octets = mesh_textures.exporter("tex_alias", naming="n_importe_quoi",
                                         resolution=64)
    assert nom == "tex_alias.zip", nom          # standard : pas de suffixe
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        assert "peau/peau_basecolor.png" in z.namelist(), sorted(z.namelist())
    assert material_store.clean_naming("n_importe_quoi") == "standard"


def test_la_cuisson_locale_fabrique_ce_qui_manque_et_le_dit():
    _job("tex_cuit", {"basecolor": _png((120, 120, 120))})
    _, sans = mesh_textures.exporter("tex_cuit", naming="unreal",
                                     resolution=64, cuire=False)
    _, avec = mesh_textures.exporter("tex_cuit", naming="unreal",
                                     resolution=64, cuire=True)
    with zipfile.ZipFile(io.BytesIO(sans)) as z:
        assert "peau/T_peau_ORM.png" not in z.namelist(), sorted(z.namelist())
        assert json.loads(z.read("textures.json"))["materiaux"][0]["cuits"] == []
    with zipfile.ZipFile(io.BytesIO(avec)) as z:
        assert "peau/T_peau_ORM.png" in z.namelist(), sorted(z.namelist())
        orm = Image.open(io.BytesIO(z.read("peau/T_peau_ORM.png")))
        assert orm.mode == "RGB" and orm.size == (64, 64), (orm.mode, orm.size)
        meta = json.loads(z.read("textures.json").decode("utf-8"))
        assert "orm" in meta["materiaux"][0]["cuits"], meta["materiaux"][0]
        bord = z.read("BORDEREAU.txt").decode("utf-8")
        assert "carte de MOTIF" in bord or "cartes de\nMOTIF" in bord, bord[-600:]


def test_les_routes_textures_sont_avant_le_catch_all():
    from app.api.routes import router
    chemins = [r.path for r in router.routes if hasattr(r, "path")]
    assert (chemins.index("/assets/3d/{job}/textures")
            < chemins.index("/assets/3d/{job}/{fmt}"))


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_textures)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 4 : lancer** — `python tests/test_mesh_textures.py` → `ModuleNotFoundError: No module named 'app.services.mesh_textures'`.

- [ ] **Step 5 : le service**

Créer `backend/app/services/mesh_textures.py` :

```python
# -*- coding: utf-8 -*-
"""Textures d'un maillage exportées aux conventions moteur — R10e P3.

La moitié du travail existe déjà et n'est PAS réécrite : `material_store`
porte les cinq conventions (standard, unity_urp, unity_hdrp, unreal, godot),
la MaskMap Unity, l'emplacement de destination de chaque fichier et sa note
vérifiée (R10c) ; `pbr_service` dérive les cartes manquantes en PIL pur.
Ce module fait le CHAÎNON qui manquait : sortir les images d'un GLB, les
ranger par matériau, les renommer, les redimensionner, cuire ce qui manque,
écrire l'archive et son bordereau.

Deux limites dites franchement :
  - un GLB compressé (KHR_draco_mesh_compression, EXT_meshopt_compression) ou
    à buffer externe lève un refus parlant : les octets d'image n'y sont pas ;
  - la cuisson locale part de la BASECOLOR, pas de la géométrie. Une AO cuite
    ainsi est une carte de MOTIF (cavités de la texture), pas une carte
    d'OBJET (cavités du maillage). C'est écrit dans le bordereau, à côté du
    fichier — pas caché derrière un nom qui promet autre chose.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# canal glTF -> genre de carte du Forge (material_store.MAP_KINDS)
_CANAL_PAR_CLE = {
    "baseColorTexture": "basecolor",
    "metallicRoughnessTexture": "orm",   # glTF : G=rugosité, B=métal (R=AO)
    "normalTexture": "normal",
    "occlusionTexture": "ao",
    "emissiveTexture": "emissive",
}
# ce qu'on sait cuire depuis la basecolor quand le moteur ne l'a pas livré
CUISSON = ("ao", "roughness", "metallic", "orm", "height")
# les genres qu'on regarde pour dire « il manque quoi »
SUIVIS = ("basecolor", "normal", "orm", "ao", "emissive")
RESOLUTIONS = (512, 1024, 2048, 4096)


def _job_dir(job):
    from app.services import mesh_report
    return mesh_report.job_dir(job)


def _glb_cible(job, version=None) -> Path:
    d = _job_dir(job)
    v = int(version or 1)
    p = d / ("model.glb" if v <= 1 else f"model.v{v}.glb")
    if not p.is_file():
        raise FileNotFoundError(f"{p.name} introuvable pour ce job")
    return p


def _images_du_doc(doc: dict, binc: bytes) -> list[bytes | None]:
    """Les octets de chaque `images[i]`. None quand l'image est externe (uri) :
    elle n'est pas dans le fichier, et on ne va pas la chercher sur le réseau
    depuis un service qui promet d'être local."""
    vues = doc.get("bufferViews") or []
    out: list[bytes | None] = []
    for img in doc.get("images") or []:
        bv = img.get("bufferView")
        if not isinstance(bv, int) or not (0 <= bv < len(vues)):
            out.append(None)
            continue
        v = vues[bv]
        off = int(v.get("byteOffset") or 0)
        out.append(binc[off:off + int(v.get("byteLength") or 0)])
    return out


def _source_de_texture(doc: dict, ref) -> int | None:
    """Index d'image derrière une référence de texture d'un matériau."""
    if not isinstance(ref, dict):
        return None
    i = ref.get("index")
    tex = doc.get("textures") or []
    if not isinstance(i, int) or not (0 <= i < len(tex)):
        return None
    s = tex[i].get("source")
    return s if isinstance(s, int) else None


def _lire(job, version):
    from app.services import mesh_edit
    p = _glb_cible(job, version)
    doc, binc = mesh_edit.lire_glb(p.read_bytes())
    for ext in doc.get("extensionsRequired") or []:
        raise ValueError(
            f"{p.name} exige l'extension {ext} : les images ne sont pas "
            "lisibles telles quelles. Passe par une version non compressée — "
            "l'Établi en écrit une à chaque opération.")
    return p, doc, binc


def inventaire(job, *, version=None) -> dict:
    """Ce que le maillage porte VRAIMENT : par matériau, quel canal est câblé
    sur quelle image, sa taille en pixels et en octets — et ce qui manque."""
    from PIL import Image
    from app.services.material_store import MAP_KINDS
    p, doc, binc = _lire(job, version)
    octets = _images_du_doc(doc, binc)

    materiaux = []
    presents: set[str] = set()
    for i, mat in enumerate(doc.get("materials") or []):
        pbr = mat.get("pbrMetallicRoughness") or {}
        refs = {"baseColorTexture": pbr.get("baseColorTexture"),
                "metallicRoughnessTexture": pbr.get("metallicRoughnessTexture"),
                "normalTexture": mat.get("normalTexture"),
                "occlusionTexture": mat.get("occlusionTexture"),
                "emissiveTexture": mat.get("emissiveTexture")}
        canaux = {}
        for cle, ref in refs.items():
            src = _source_de_texture(doc, ref)
            if src is None or src >= len(octets) or octets[src] is None:
                continue
            genre = _CANAL_PAR_CLE[cle]
            data = octets[src]
            try:
                im = Image.open(io.BytesIO(data))
                canaux[genre] = {"image": src, "bytes": len(data),
                                 "px": [im.width, im.height]}
                presents.add(genre)
            except Exception as e:               # image illisible : le dire
                canaux[genre] = {"image": src, "bytes": len(data),
                                 "px": None, "erreur": str(e)}
        materiaux.append({"index": i,
                          "nom": mat.get("name") or f"materiau_{i}",
                          "canaux": canaux})
    from app.services.material_store import naming_catalog
    return {
        "job": Path(str(job)).name, "file": p.name,
        "materiaux": materiaux,
        "manquants": sorted(set(SUIVIS) - presents),
        "resolutions": list(RESOLUTIONS),
        "conventions": [c["id"] for c in naming_catalog()],
        "map_kinds": list(MAP_KINDS),
    }


def exporter(job, *, naming: str = "standard", resolution: int = 2048,
             version=None, cuire: bool = True) -> tuple[str, bytes]:
    """L'archive : un dossier par matériau, des noms à la convention, la
    résolution demandée, la MaskMap pour Unity, et un bordereau qui dit où
    chaque fichier VA dans le moteur visé."""
    from PIL import Image
    from app.services import material_store as MS
    from app.services import pbr_service
    p, doc, binc = _lire(job, version)
    octets = _images_du_doc(doc, binc)
    naming = MS.clean_naming(naming)
    res = MS.clean_res(resolution)
    inv = inventaire(job, version=version)
    if not any(m["canaux"] for m in inv["materiaux"]):
        raise ValueError(
            f"{p.name} ne porte aucune texture : rien à exporter. Texture-le "
            "d'abord (retexture Meshy), ou habille-le d'une matière du Forge.")

    voulus = MS.default_export_maps(naming)
    buf = io.BytesIO()
    meta_mats = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for m in inv["materiaux"]:
            if not m["canaux"]:
                continue
            dossier = MS.slug(m["nom"], fallback=f"materiau_{m['index']}")
            maps: dict[str, Image.Image] = {}
            for genre, info in m["canaux"].items():
                data = octets[info["image"]]
                if data is None or info.get("px") is None:
                    continue
                im = Image.open(io.BytesIO(data))
                im.load()
                maps[genre] = im
            cuits: list[str] = []
            if cuire and "basecolor" in maps:
                besoin = [k for k in CUISSON
                          if k in set(voulus) | {"orm"} and k not in maps]
                if besoin:
                    for k, img in pbr_service.derive_maps(
                            maps["basecolor"].convert("RGB"), None,
                            want=besoin).items():
                        maps[k] = img
                        cuits.append(k)
            maps = pbr_service.resize_maps(maps, res)
            if naming in MS.UNITY_NAMINGS:
                mm = MS.build_maskmap(maps)
                if mm is not None:
                    maps[MS.MASKMAP] = mm
            noms = MS.naming_map(naming, dossier)
            livres = []
            for genre in list(voulus) + [MS.MASKMAP]:
                if genre not in maps or genre not in noms:
                    continue
                z.writestr(f"{dossier}/{noms[genre]}",
                           MS.png_bytes(maps[genre], genre, 8))
                livres.append({"kind": genre, "file": noms[genre],
                               "slot": MS.engine_slot(genre, naming),
                               "role": MS.map_role(genre, naming)})
            meta_mats.append({"nom": m["nom"], "dossier": dossier,
                              "cuits": sorted(cuits), "fichiers": livres})
        meta = {
            "job": inv["job"], "file": inv["file"], "naming": naming,
            "label": MS.NAMING_LABELS.get(naming, naming),
            "resolution": res, "cuisson": bool(cuire),
            "materiaux": meta_mats,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        z.writestr("textures.json", json.dumps(meta, indent=1, ensure_ascii=False))
        z.writestr("BORDEREAU.txt", _bordereau(meta))
    return (MS.export_filename({"name": Path(str(job)).name}, "zip", naming),
            buf.getvalue())


def _bordereau(meta: dict) -> str:
    from app.services.material_store import NAMING_NOTES
    L = [f"Textures du maillage — job {meta['job']} ({meta['file']})",
         f"Convention : {meta['label']} · résolution {meta['resolution']} px "
         f"· {meta['created_at']}",
         "", NAMING_NOTES.get(meta["naming"], ""), ""]
    for m in meta["materiaux"]:
        L.append(f"[{m['nom']}] -> {m['dossier']}/")
        for f in m["fichiers"]:
            L.append(f"  {f['file']:<32} {f['slot']}")
            if f["role"]:
                L.append(f"  {'':<32} ({f['role']})")
        if m["cuits"]:
            L.append(f"  CUITES LOCALEMENT : {', '.join(m['cuits'])}. Dérivées "
                     "de la basecolor en PIL : ce sont des cartes de MOTIF "
                     "(cavités de la texture), pas des cartes d'OBJET "
                     "(cavités de la géométrie). Utile, mais ce n'est pas un "
                     "bake de maillage.")
        L.append("")
    return "\n".join(L) + "\n"
```

- [ ] **Step 6 : les routes** (avant le catch-all `{fmt}`)

```python
@router.get("/assets/3d/{job}/textures")
async def get_asset3d_textures(job: str, version: int = None):
    """Ce que le maillage porte en textures, et ce qui manque — avant de
    choisir une convention et une résolution."""
    from app.services import mesh_textures
    try:
        return await asyncio.to_thread(mesh_textures.inventaire, job,
                                       version=version)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/assets/3d/{job}/textures")
async def post_asset3d_textures(job: str, body: dict = None):
    """L'archive PBR aux conventions moteur. Locale, gratuite, synchrone."""
    from app.services import mesh_textures
    body = body or {}
    try:
        nom, octets = await asyncio.to_thread(
            mesh_textures.exporter, job,
            naming=str(body.get("naming") or "standard"),
            resolution=int(body.get("resolution") or 2048),
            version=body.get("version"),
            cuire=bool(body.get("cuire", True)))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    return Response(content=octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})
```

- [ ] **Step 7 : relancer, et vérifier la non-régression du Forge**

```
python tests/test_mesh_textures.py
python tests/test_material_truth.py
python -m pytest tests/test_materials_api.py -q --no-header -p no:warnings
```
Attendu : `OK — 7 tests, 0 rouge(s) (mesh_textures)` ; les deux bancs du Forge verts (le second reste au format pytest — c'est un banc HÉRITÉ qu'on ne convertit pas ici).

- [ ] **Step 8 : le bouton, dans le MÊME patch**

Dans `scripts/patch_bundle_asset3dlod.py` :

1. `MARQUEURS = (("DzLod", 2), ("DzTex", 2))` ;
2. ajouter la constante, après `DZ_LOD` :

```python
DZ_TEX = (
    'function DzTex({sh}){'
    'var IS=x.useState(null),inv=IS[0],setInv=IS[1],'
    'NS=x.useState("standard"),nm=NS[0],setNm=NS[1],'
    'RS=x.useState(2048),rs=RS[0],setRs=RS[1];'
    'x.useEffect(function(){var on=!0;'
    'fetch("/api/assets/3d/"+sh+"/textures")'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(j){on&&j&&setInv(j)}).catch(function(){});'
    'return function(){on=!1}},[sh]);'
    'function dl(){fetch("/api/assets/3d/"+sh+"/textures",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({naming:nm,resolution:rs})})'
    '.then(function(r2){return r2.ok?r2.blob():null}).then(function(b){'
    'if(!b)return;var u=URL.createObjectURL(b),a=document.createElement("a");'
    'a.href=u;a.download=sh+"_"+nm+".zip";a.click();'
    'setTimeout(function(){URL.revokeObjectURL(u)},4e3)}).catch(function(){})}'
    'if(!inv)return null;'
    'return r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center",'
    'flexWrap:"wrap",marginTop:4},children:['
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)"},'
    'children:"Textures"},"lb"),'
    'r.jsx("select",{value:nm,onChange:function(e2){setNm(e2.target.value)},'
    + BTN + ',children:inv.conventions.map(function(c){'
    'return r.jsx("option",{value:c,children:c},c)})},"cv"),'
    'r.jsx("select",{value:String(rs),'
    'onChange:function(e2){setRs(Number(e2.target.value))},'
    + BTN + ',children:inv.resolutions.map(function(v){'
    'return r.jsx("option",{value:String(v),children:String(v)+" px"},'
    'String(v))})},"rs"),'
    'r.jsx("button",{onClick:dl,' + BTN + ',children:"↓ Textures"},"go"),'
    'inv.manquants.length?r.jsx("span",{style:{fontSize:10,'
    'color:"var(--ink-soft)"},children:"cuites : "+inv.manquants.join(", ")},'
    '"mq"):null]},"tex")}')
```
3. `GREFFE = 'r.jsx(DzLod,{sh:sh},"lod"+sh),r.jsx(DzTex,{sh:sh},"tex"+sh),'` ;
4. la greffe `D1-def` devient `apply(s, ANCRE_DEF, DZ_LOD + DZ_TEX + ANCRE_DEF, "D1-def")` ;
5. dans `--check`, la boucle sur `MARQUEURS` teste déjà les deux marqueurs.

Rejouer :
```
python scripts/patch_bundle_asset3dlod.py
python scripts/repatch_all.py --list
```
Attendu : `restore <- index-BEOJX8L5.js.bak_asset3dlod` puis `OK — asset3dlod applique.` — le `restore` PROUVE que le script est re-jouable et n'empile pas les greffes. L'inventaire du Step 7 de la Task 3, rejoué, doit rendre exactement **un** nom `Dz*` de plus (`DzTex`).

- [ ] **Step 9 : commit**

```
git add backend/app/services/mesh_textures.py backend/app/services/material_store.py backend/app/api/routes.py backend/tests/test_mesh_textures.py scripts/patch_bundle_asset3dlod.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'moteurs 3d : P3 - textures du maillage exportees aux conventions moteur' -m 'Les images du GLB sortent par matériau, renommées selon naming_catalog (standard, Unity URP et HDRP, Unreal, Godot — R10c), à la résolution choisie, avec la MaskMap Unity et le bordereau qui dit où chaque fichier va. Ce qui manque est cuit en PIL depuis la basecolor, et le bordereau dit que c est une carte de MOTIF, pas une carte d OBJET. Un GLB compressé ou nu refuse en le disant. Un seul encodeur PNG pour le Forge et pour les maillages.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 5 : P4 — conversion locale de formats

**Ce qui n'est PAS livré ici, et pourquoi.** `gltfpack 1.2 -h`, mesuré le 03/09/2026 sur le binaire embarqué (`%LOCALAPPDATA%\DeepotusVideoGen\bin\gltfpack.exe`), déclare : *entrées* `.obj/.gltf/.glb`, *sorties* `.gltf/.glb`. **Aucun FBX, aucun USDZ, aucun BLEND en local.** Le format FBX est propriétaire ; l'écriture libre en est partielle : un FBX **ASCII 7.x** écrit à la main est lu par Unity et Unreal, et **refusé par Blender** (de mémoire, non vérifié — donc pas un argument de livraison). Écrire un FBX à moitié valable serait pire que ne pas l'écrire : il faudrait le maintenir, et l'utilisateur découvrirait le trou à l'import. FBX, USDZ et BLEND passent donc par **Meshy convert — 1 crédit par tâche, pas par format** (docs.meshy.ai/en/api/convert relue le 03/09/2026), déjà proxifié et déjà allowlisté. Le devis de la route le dit avant le clic.

**Files:**
- Create: `backend/app/services/mesh_convert.py`
- Modify: `backend/app/api/routes.py` (2 routes, avant le catch-all `{fmt}`)
- Modify: `frontend/studio3d/fal.js` (bloc « Conversion » du panneau Atelier fal)
- Test: `backend/tests/test_mesh_convert.py`

- [ ] **Step 1 : relire la doc Meshy et figer**

WebFetch `https://docs.meshy.ai/en/api/convert` (prompt : « quote the request fields, the accepted input formats, the target_formats enum and the credit cost »). Comparer à la ligne « docs.meshy.ai/en/api/convert » du tableau « Références vérifiées ». Si un champ diffère, corriger la constante de `mesh_convert.py` **et** la ligne du tableau, avec la date du jour.

- [ ] **Step 2 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""P4 — conversion locale de formats. Le banc relit les fichiers ÉCRITS : OBJ
reparsé (compteurs v/vt/vn/f, usemtl), MTL, STL relu par print3d, 3MF ouvert
comme un zip, GLB relu. Meshy en MESHY_MOCK, upload fal stubbé.
Run : python tests/test_mesh_convert.py"""
import asyncio, io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["MESHY_MOCK"] = "1"; os.environ["MESHY_MOCK_SPEED"] = "0.005"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import gltf_builder, mesh_convert, print3d     # noqa: E402


async def _faux_upload(p):
    return f"https://fal.test/{pathlib.Path(p).name}"


A3._upload = _faux_upload


def _png(couleur=(200, 90, 40), taille=32) -> bytes:
    b = io.BytesIO(); Image.new("RGB", (taille, taille), couleur).save(b, "PNG")
    return b.getvalue()


def _job(nom: str, texture: bool = True) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    maps = {"basecolor": _png()} if texture else {}
    (d / "model.glb").write_bytes(gltf_builder.build_glb(maps, None, "cube", "peau"))
    return d


def test_les_capacites_disent_ce_qui_est_local_et_ce_qui_coute():
    c = mesh_convert.capacites()
    assert set(c["local_export"]) == {"obj", "stl", "3mf", "gltf"}, c
    assert set(c["local_import"]) == {"obj", "stl", "glb", "gltf"}, c
    assert set(c["meshy"]) == {"fbx", "usdz", "blend"}, c
    assert c["credits_meshy"] == 1, c
    assert "FBX" in c["pourquoi_pas_local"] and "Blender" in c["pourquoi_pas_local"]


def test_l_obj_sort_avec_son_mtl_ses_uv_et_sa_texture():
    _job("cv_obj")
    nom, octets = mesh_convert.exporter("cv_obj", "obj")
    assert nom == "cv_obj_obj.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert "cv_obj.obj" in noms and "cv_obj.mtl" in noms, noms
        assert any(n.endswith(".png") for n in noms), noms
        obj = z.read("cv_obj.obj").decode("utf-8")
        assert obj.startswith("# Deepotus"), obj[:80]
        assert "mtllib cv_obj.mtl" in obj, obj[:300]
        assert obj.count("\nusemtl ") == 1, obj
        v = sum(1 for l in obj.splitlines() if l.startswith("v "))
        vt = sum(1 for l in obj.splitlines() if l.startswith("vt "))
        vn = sum(1 for l in obj.splitlines() if l.startswith("vn "))
        f = sum(1 for l in obj.splitlines() if l.startswith("f "))
        assert v == 24 and vt == 24 and vn == 24 and f == 12, (v, vt, vn, f)
        assert all(len(l.split()) == 4 for l in obj.splitlines() if l.startswith("f "))
        mtl = z.read("cv_obj.mtl").decode("utf-8")
        assert "newmtl peau" in mtl and "map_Kd " in mtl, mtl


def test_le_stl_et_le_3mf_passent_par_print3d_et_se_relisent():
    _job("cv_stl", texture=False)
    _, stl = mesh_convert.exporter("cv_stl", "stl")
    tris = print3d.lire_stl(stl)
    assert len(tris) == 12, len(tris)
    _, mf3 = mesh_convert.exporter("cv_stl", "3mf")
    with zipfile.ZipFile(io.BytesIO(mf3)) as z:
        assert "3D/3dmodel.model" in z.namelist(), sorted(z.namelist())
    _, stl_mm = mesh_convert.exporter("cv_stl", "stl", cible_mm=100.0)
    bb = print3d.bbox(print3d.lire_stl(stl_mm))
    assert abs(max(b[1] - b[0] for b in bb) - 100.0) < 1e-3, bb


def test_le_gltf_separe_sort_avec_son_bin():
    _job("cv_gltf")
    nom, octets = mesh_convert.exporter("cv_gltf", "gltf")
    assert nom == "cv_gltf_gltf.zip", nom
    with zipfile.ZipFile(io.BytesIO(octets)) as z:
        noms = sorted(z.namelist())
        assert any(n.endswith(".gltf") for n in noms), noms
        # gltfpack peut écrire le tampon À CÔTÉ (.bin) ou l'embarquer en
        # data: URI selon la version : on relit le .gltf et l'on accepte les
        # DEUX vérités plutôt que d'épingler celle qu'on croit connaître.
        doc = json.loads(z.read([n for n in noms if n.endswith(".gltf")][0]))
        uri = str(((doc.get("buffers") or [{}])[0]).get("uri") or "")
        assert any(n.endswith(".bin") for n in noms) or uri.startswith("data:"), \
            (noms, uri[:40])


def test_un_format_inconnu_ou_proprietaire_refuse_en_disant_la_voie():
    _job("cv_ref")
    for fmt in ("fbx", "usdz", "blend"):
        try:
            mesh_convert.exporter("cv_ref", fmt)
            raise AssertionError(f"{fmt} aurait dû refuser")
        except ValueError as e:
            assert "Meshy" in str(e) and "1 crédit" in str(e), (fmt, e)
    try:
        mesh_convert.exporter("cv_ref", "dae")
        raise AssertionError("dae aurait dû refuser")
    except ValueError as e:
        assert "dae" in str(e), e


def test_l_import_stl_et_obj_redevient_un_glb_relisible():
    d = _job("cv_in", texture=False)
    stl = print3d.ecrire_stl(print3d.lire_glb_triangles((d / "model.glb").read_bytes()))
    glb = mesh_convert.importer(stl, "objet.stl")
    assert print3d.lire_glb_triangles(glb) and len(print3d.lire_glb_triangles(glb)) == 12
    _, zobj = mesh_convert.exporter("cv_in", "obj")
    with zipfile.ZipFile(io.BytesIO(zobj)) as z:
        obj = z.read("cv_in.obj")
    glb2 = mesh_convert.importer(obj, "objet.obj")
    assert len(print3d.lire_glb_triangles(glb2)) == 12, "OBJ -> GLB par gltfpack"
    try:
        mesh_convert.importer(b"xx", "objet.fbx")
        raise AssertionError("fbx aurait dû refuser")
    except ValueError as e:
        assert "fbx" in str(e).lower(), e


def test_la_conversion_meshy_devis_puis_tache_et_rapatriement():
    d = _job("cv_meshy")
    devis = mesh_convert.devis_meshy(["fbx", "usdz"])
    assert devis["credits"] == 1 and devis["lines"][0]["credits"] == 1, devis
    r = asyncio.run(mesh_convert.convertir_par_meshy("cv_meshy", ["fbx", "usdz"]))
    assert r["task_id"] and r["credits"] == 1, r
    for f in r["files"]:
        assert (d / "convert" / f).is_file(), (f, r)
    assert sorted(r["files"]) == ["model.fbx", "model.usdz"], r["files"]


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_convert)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 3 : lancer** — `python tests/test_mesh_convert.py` → `ModuleNotFoundError: No module named 'app.services.mesh_convert'`.

- [ ] **Step 4 : le service**

Créer `backend/app/services/mesh_convert.py` :

```python
# -*- coding: utf-8 -*-
"""Conversion de formats — R10e P4.

CE QUI EST LOCAL ET GRATUIT (mesuré le 03/09/2026) :
  export  GLB -> OBJ+MTL(+PNG), STL, 3MF, glTF séparé (.gltf + .bin)
  import  OBJ, STL, glTF, GLB -> GLB
Les briques existent déjà : `print3d` lit un GLB en triangles monde et écrit
STL et 3MF aux millimètres ; `gltfpack 1.2` (embarqué) accepte .obj/.gltf/.glb
en entrée et écrit .gltf/.glb ; `mesh_textures` sort les images.

CE QUI NE L'EST PAS, ET POURQUOI : `gltfpack -h` ne sort NI fbx, NI usdz, NI
blend. Le FBX est un format propriétaire ; l'écriture libre en est partielle
(un FBX ASCII 7.x est lu par Unity et Unreal, refusé par Blender — de
mémoire, non vérifié). On ne l'écrit donc pas : ces trois formats passent par
**Meshy convert**, 1 crédit par TÂCHE (pas par format), docs.meshy.ai/en/api/
convert relue le 03/09/2026. Le devis le dit avant le clic.

Aucune conversion n'écrase le maillage : les sorties vivent dans
`outputs/assets3d/<job>/convert/`, à côté, et le GLB source ne bouge pas.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

LOCAL_EXPORT = ("obj", "stl", "3mf", "gltf")
LOCAL_IMPORT = ("obj", "stl", "glb", "gltf")
MESHY_EXPORT = ("fbx", "usdz", "blend")
POURQUOI_PAS_LOCAL = (
    "gltfpack 1.2 (embarqué) n'écrit que .gltf et .glb — mesuré le "
    "03/09/2026. Le FBX est propriétaire et son écriture libre est partielle "
    "(un FBX ASCII est lu par Unity et Unreal, refusé par Blender) ; USDZ et "
    "BLEND n'ont pas d'écriture stdlib raisonnable. Ces trois-là passent par "
    "Meshy convert, 1 crédit par tâche."
)


def capacites() -> dict:
    from app.services import meshy_service as MS
    return {
        "local_export": list(LOCAL_EXPORT),
        "local_import": list(LOCAL_IMPORT),
        "meshy": list(MESHY_EXPORT),
        "credits_meshy": MS.CREDITS_FLAT["convert"],
        "pourquoi_pas_local": POURQUOI_PAS_LOCAL,
    }


def _job_dir(job):
    from app.services import mesh_report
    return mesh_report.job_dir(job)


def _glb_cible(job, version=None) -> Path:
    d = _job_dir(job)
    v = int(version or 1)
    p = d / ("model.glb" if v <= 1 else f"model.v{v}.glb")
    if not p.is_file():
        raise FileNotFoundError(f"{p.name} introuvable pour ce job")
    return p


# ── GLB -> OBJ + MTL ─────────────────────────────────────────────────────────

def _primitives(doc: dict, binc: bytes):
    """(nom du matériau, positions monde, normales monde, uv, indices) par
    primitive TRIANGLES de la scène.

    Réutilise les lecteurs de `print3d` (accesseurs et matrices de nœuds)
    plutôt que d'en écrire un troisième : ce sont eux qui portent déjà les
    refus parlants sur GLB compressé ou à buffer externe.
    """
    from app.services.print3d import (_accessor, _appliquer, _IDENTITE,
                                      _mat_locale, _mat_mul)
    mats = doc.get("materials") or []
    out = []

    def _mesh(im, monde):
        for prim in doc["meshes"][im].get("primitives", []):
            if prim.get("mode", 4) != 4:
                raise ValueError("primitives TRIANGLES seulement "
                                 f"(mode {prim.get('mode')}) — hors périmètre")
            att = prim.get("attributes") or {}
            pos = [_appliquer(monde, p) for p in _accessor(doc, binc, att["POSITION"])]
            nrm = ([_appliquer(monde, p) for p in _accessor(doc, binc, att["NORMAL"])]
                   if "NORMAL" in att else [])
            uv = (_accessor(doc, binc, att["TEXCOORD_0"])
                  if "TEXCOORD_0" in att else [])
            if "indices" in prim:
                idx = [v[0] for v in _accessor(doc, binc, prim["indices"])]
            else:
                idx = list(range(len(pos)))
            mi = prim.get("material")
            nom = (mats[mi].get("name") if isinstance(mi, int) and mi < len(mats)
                   else None) or "materiau"
            out.append((nom, pos, nrm, uv, idx))

    def _noeud(i, parent):
        node = doc["nodes"][i]
        monde = _mat_mul(parent, _mat_locale(node))
        if "mesh" in node:
            _mesh(node["mesh"], monde)
        for enfant in node.get("children", []):
            _noeud(enfant, monde)

    scenes = doc.get("scenes") or []
    for i in (scenes[doc.get("scene", 0)].get("nodes", []) if scenes else []):
        _noeud(i, _IDENTITE)
    return out


def _obj_et_mtl(doc, binc, base: str, textures: dict) -> tuple[str, str]:
    """Le .obj et le .mtl, en texte. Les indices OBJ sont GLOBAUX et
    commencent à 1 ; le v de glTF est compté du HAUT et celui d'OBJ du BAS,
    d'où le `1 - v` (sans lui, toutes les textures sortent retournées)."""
    from app.services.material_store import slug
    L = [f"# Deepotus — {base}.obj (converti depuis GLB, coordonnées monde)",
         f"mtllib {base}.mtl"]
    M = []
    vus = set()
    offset = 1
    for nom, pos, nrm, uv, idx in _primitives(doc, binc):
        for p in pos:
            L.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
        for t in uv:
            L.append(f"vt {t[0]:.6f} {1.0 - t[1]:.6f}")
        for n in nrm:
            L.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
        s = slug(nom, fallback="materiau")
        L.append(f"usemtl {s}")
        if s not in vus:
            vus.add(s)
            M.append(f"newmtl {s}")
            M.append("Kd 1.000 1.000 1.000")
            M.append("d 1.0")
            M.append("illum 2")
            if textures.get(nom):
                M.append(f"map_Kd {textures[nom]}")
            M.append("")
        for k in range(0, len(idx) - 2, 3):
            coins = []
            for j in (idx[k], idx[k + 1], idx[k + 2]):
                a = offset + j
                coins.append(f"{a}/{a if uv else ''}/{a if nrm else ''}"
                             .rstrip("/") if (uv or nrm) else str(a))
            L.append("f " + " ".join(coins))
        offset += len(pos)
    return "\n".join(L) + "\n", "\n".join(M) + "\n"


def exporter(job, fmt: str, *, version=None, cible_mm: float = None,
             nom: str = None) -> tuple[str, bytes]:
    """Un format local. Rend (nom de fichier, octets). `obj` et `gltf` sont
    des ZIP (plusieurs fichiers) ; `stl` et `3mf` sont le fichier nu."""
    import subprocess
    import tempfile
    from app.services import mesh_edit, mesh_optimize, mesh_textures, print3d
    fmt = str(fmt or "").lower().lstrip(".")
    base = nom or Path(str(job)).name
    if fmt in MESHY_EXPORT:
        raise ValueError(
            f"{fmt} n'est pas écrit localement : {POURQUOI_PAS_LOCAL} "
            f"Passe par la conversion Meshy — 1 crédit pour la tâche entière.")
    if fmt not in LOCAL_EXPORT:
        raise ValueError(f"format {fmt} inconnu — local : "
                         f"{', '.join(LOCAL_EXPORT)} ; par Meshy : "
                         f"{', '.join(MESHY_EXPORT)}")
    src = _glb_cible(job, version)

    if fmt in ("stl", "3mf"):
        tris = print3d.mettre_a_l_echelle(
            print3d.lire_glb_triangles(src.read_bytes()), cible_mm)
        octets = (print3d.ecrire_stl(tris) if fmt == "stl"
                  else print3d.ecrire_3mf(tris, nom=base))
        return f"{base}.{fmt}", octets

    if fmt == "gltf":
        exe = mesh_optimize._gltfpack()
        with tempfile.TemporaryDirectory() as td:
            sortie = Path(td) / f"{base}.gltf"
            r = subprocess.run([exe, "-i", str(src), "-o", str(sortie), "-noq",
                                "-kn", "-km"],
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not sortie.is_file():
                raise RuntimeError(
                    f"gltfpack a échoué ({r.returncode}) : "
                    f"{(r.stderr or r.stdout or '').strip()[:300]}")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for p in sorted(Path(td).iterdir()):
                    z.write(p, p.name)
            return f"{base}_gltf.zip", buf.getvalue()

    # obj : géométrie écrite ici, textures par mesh_textures (un seul encodeur)
    doc, binc = mesh_edit.lire_glb(src.read_bytes())
    buf = io.BytesIO()
    textures: dict[str, str] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        try:
            _, arch = mesh_textures.exporter(job, naming="standard",
                                             resolution=2048, version=version)
        except ValueError:
            arch = None                    # maillage nu : OBJ sans map_Kd
        if arch is not None:
            from app.services.material_store import slug as _slug
            inv = mesh_textures.inventaire(job, version=version)
            # l'archive range chaque matériau sous le dossier `slug(nom)` :
            # cette table lui rend son NOM, et le nom est ce que `usemtl`
            # écrit dans l'OBJ
            par_dossier = {_slug(m["nom"], fallback=f"materiau_{m['index']}"):
                           m["nom"] for m in inv["materiaux"]}
            with zipfile.ZipFile(io.BytesIO(arch)) as za:
                for n in za.namelist():
                    if not n.lower().endswith(".png"):
                        continue
                    plat = n.replace("/", "_")
                    z.writestr(plat, za.read(n))
                    mnom = par_dossier.get(n.split("/")[0])
                    if mnom and "basecolor" in n.lower() and mnom not in textures:
                        textures[mnom] = plat
        obj, mtl = _obj_et_mtl(doc, binc, base, textures)
        z.writestr(f"{base}.obj", obj)
        z.writestr(f"{base}.mtl", mtl)
    return f"{base}_obj.zip", buf.getvalue()


# ── import : OBJ / STL / glTF -> GLB ─────────────────────────────────────────

def tris_vers_glb(tris, nom: str = "objet") -> bytes:
    """GLB v2 minimal depuis des triangles (positions seules, sans indices).
    C'est la sortie honnête d'un STL : un STL n'a ni UV, ni matériau, ni
    sommets partagés — inventer les trois serait mentir."""
    import json
    import struct
    plats = [c for t in tris for s in t for c in s]
    binc = struct.pack(f"<{len(plats)}f", *plats)
    binc += b"\x00" * (-len(binc) % 4)
    xs = plats[0::3] or [0.0]
    ys = plats[1::3] or [0.0]
    zs = plats[2::3] or [0.0]
    gltf = {
        "asset": {"version": "2.0", "generator": "deepotus-mesh-convert"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": str(nom)}],
        "meshes": [{"name": str(nom),
                    "primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"bufferView": 0, "componentType": 5126,
                       "count": len(tris) * 3, "type": "VEC3",
                       "min": [min(xs), min(ys), min(zs)],
                       "max": [max(xs), max(ys), max(zs)]}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0,
                         "byteLength": len(plats) * 4}],
        "buffers": [{"byteLength": len(binc)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binc)
    return (struct.pack("<III", 0x46546C67, 2, total)
            + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binc), 0x004E4942) + binc)


def importer(data: bytes, nom_fichier: str) -> bytes:
    """Un fichier venu du dehors -> octets GLB. Refus parlant sur tout ce que
    ni print3d ni gltfpack ne savent lire."""
    import subprocess
    import tempfile
    from app.services import mesh_optimize, print3d
    ext = Path(str(nom_fichier)).suffix.lower().lstrip(".")
    if ext == "glb":
        return bytes(data)
    if ext == "stl":
        return tris_vers_glb(print3d.lire_stl(bytes(data)),
                             Path(str(nom_fichier)).stem)
    if ext in ("obj", "gltf"):
        exe = mesh_optimize._gltfpack()
        with tempfile.TemporaryDirectory() as td:
            entree = Path(td) / f"entree.{ext}"
            entree.write_bytes(bytes(data))
            sortie = Path(td) / "sortie.glb"
            r = subprocess.run([exe, "-i", str(entree), "-o", str(sortie),
                                "-noq", "-kn", "-km"],
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not sortie.is_file():
                raise ValueError(
                    f"gltfpack n'a pas pu lire ce {ext} ({r.returncode}) : "
                    f"{(r.stderr or r.stdout or '').strip()[:300]}")
            return sortie.read_bytes()
    raise ValueError(
        f"import {ext or '(sans extension)'} impossible en local — "
        f"formats lus : {', '.join(LOCAL_IMPORT)}. {POURQUOI_PAS_LOCAL}")


# ── FBX / USDZ / BLEND : Meshy convert ───────────────────────────────────────

def devis_meshy(formats) -> dict:
    """1 crédit par TÂCHE, quel que soit le nombre de formats
    (docs.meshy.ai/en/api/convert, relue le 03/09/2026)."""
    from app.services import meshy_service as MS
    voulus = sorted({str(f).lower().lstrip(".") for f in (formats or [])})
    inconnus = [f for f in voulus if f not in MESHY_EXPORT]
    if not voulus:
        raise ValueError("aucun format demandé")
    if inconnus:
        raise ValueError(f"la conversion Meshy sert {', '.join(MESHY_EXPORT)} — "
                         f"{', '.join(inconnus)} sont locaux ou inconnus")
    cr = MS.CREDITS_FLAT["convert"]
    return {"formats": voulus, "credits": cr,
            "lines": [{"id": "convert",
                       "label": "Conversion Meshy " + ", ".join(voulus),
                       "credits": cr}]}


async def convertir_par_meshy(job, formats, *, version=None,
                              on_step=None) -> dict:
    """Envoie le GLB courant à `openapi/v1/convert` et rapatrie les binaires
    sous `convert/`. L'URL du modèle vient du même upload fal que le rig
    (Task 2) : Meshy exige une URL publique ou un data URI, et le proxy ne
    sert pas de fichiers."""
    from app.services import asset3d_service as A3
    from app.services import meshy_service as MS
    devis = devis_meshy(formats)
    src = _glb_cible(job, version)

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    await _step("Envoi du maillage", 15)
    url = await A3._upload(src)
    await _step("Conversion Meshy", 35)
    tid = await MS.create_task("openapi/v1/convert",
                               {"model_url": url,
                                "target_formats": devis["formats"]})
    tache = await A3._attendre_meshy("openapi/v1/convert", tid, on_step,
                                     depart=40, fin=85)
    res = tache.get("result") or {}
    d = _job_dir(job) / "convert"
    d.mkdir(parents=True, exist_ok=True)
    ecrits = []
    for f in devis["formats"]:
        u = res.get(f"model_url_{f}") or res.get(f) or (
            (res.get("model_urls") or {}).get(f))
        if not u:
            continue
        (d / f"model.{f}").write_bytes(await MS._fetch_url(u))
        ecrits.append(f"model.{f}")
    await _step("Complete", 100)
    return {"task_id": tid, "credits": tache.get("consumed_credits")
            or devis["credits"], "files": sorted(ecrits),
            "manquants": [f for f in devis["formats"]
                          if f"model.{f}" not in ecrits]}
```

**Note d'intégration** : `A3._attendre_meshy(base, tid, on_step, depart=…, fin=…)` existe déjà (`asset3d_service.py:792`) mais sa signature actuelle est à relire ; si elle ne prend pas `depart`/`fin`, appeler `A3._attendre_meshy("openapi/v1/convert", tid, on_step)` et laisser la progression au helper. Vérifier d'abord :
```
python -c "import inspect,sys; sys.path.insert(0,'backend'); from app.services import asset3d_service as A; print(inspect.signature(A._attendre_meshy))"
```
Attendu : la signature exacte ; adapter l'appel, **pas** le helper.

- [ ] **Step 5 : relancer** — `python tests/test_mesh_convert.py` → `OK — 7 tests, 0 rouge(s) (mesh_convert)`.

- [ ] **Step 6 : les routes** (avant le catch-all `{fmt}`)

```python
@router.get("/assets/3d/{job}/convert")
async def get_asset3d_convert(job: str):
    """Ce qui est convertible localement, ce qui passe par Meshy, et pourquoi."""
    from app.services import mesh_convert
    return mesh_convert.capacites()


@router.post("/assets/3d/{job}/convert")
async def post_asset3d_convert(job: str, body: dict = None,
                               background_tasks: BackgroundTasks = None):
    """Un format local -> le fichier tout de suite ; fbx/usdz/blend -> une
    tâche Meshy en fond (PAYANTE : un job de la file, comme le rig)."""
    from app.services import mesh_convert
    body = body or {}
    fmt = str(body.get("format") or "").lower().lstrip(".")
    if fmt in mesh_convert.MESHY_EXPORT or body.get("formats"):
        formats = body.get("formats") or [fmt]
        try:
            devis = mesh_convert.devis_meshy(formats)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return await _lancer_job_asset3d(
            background_tasks, job=job,
            titre=f"Conversion {', '.join(devis['formats'])} · {Path(job).name}",
            etape="Conversion Meshy",
            travail=lambda on_step: mesh_convert.convertir_par_meshy(
                job, devis["formats"], version=body.get("version"),
                on_step=on_step),
            cost_meta=lambda r: {"kind": "asset3d_convert", "via": "meshy",
                                 "formats": devis["formats"],
                                 "credits": r.get("credits")})
    try:
        nom, octets = await asyncio.to_thread(
            mesh_convert.exporter, job, fmt, version=body.get("version"),
            cible_mm=body.get("cible_mm"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    media = ("application/zip" if nom.endswith(".zip")
             else "model/3mf" if nom.endswith(".3mf") else "model/stl")
    return Response(content=octets, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})
```

- [ ] **Step 7 : le bloc « Conversion » dans /studio3d**

Dans `frontend/studio3d/fal.js`, à la suite du panneau « Job courant » posé par la Task 2 :

```js
/* Conversion — ce qui est local sort tout de suite, ce qui coûte le dit
   avant. Le serveur est la seule source de la liste : coder « fbx » en dur
   ici, c'est promettre un format le jour où gltfpack change. */
export async function brancherConversion(job) {
  const zone = document.querySelector("#falConvert");
  const caps = await (await fetch(`/api/assets/3d/${job}/convert`)).json();
  const opt = (f, suffixe) => `<option value="${f}">${f}${suffixe}</option>`;
  zone.innerHTML = `
    <label class="fld"><span>Format</span>
      <select id="cvFmt">
        ${caps.local_export.map((f) => opt(f, " · local, gratuit")).join("")}
        ${caps.meshy.map((f) => opt(f, ` · Meshy, ${caps.credits_meshy} cr`)).join("")}
      </select>
    </label>
    <label class="fld"><span>Taille (mm, STL/3MF)</span>
      <input id="cvMm" type="number" min="1" step="1" placeholder="tel quel"></label>
    <button id="cvGo">Convertir</button>
    <div class="cv-note">${caps.pourquoi_pas_local}</div>`;
  document.querySelector("#cvGo").addEventListener("click", async () => {
    const fmt = document.querySelector("#cvFmt").value;
    const mm = Number(document.querySelector("#cvMm").value) || null;
    const r = await fetch(`/api/assets/3d/${job}/convert`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: fmt, cible_mm: mm }),
    });
    if (!r.ok) { toast((await r.json().catch(() => ({}))).detail || "échec"); return; }
    if (caps.meshy.includes(fmt)) {
      const j = await r.json();
      toast(`Conversion lancée (job ${j.job_id.slice(0, 8)}) — suis la file.`);
      return;
    }
    const b = await r.blob();
    const u = URL.createObjectURL(b), a = document.createElement("a");
    a.href = u; a.download = `${job}.${fmt === "obj" || fmt === "gltf" ? "zip" : fmt}`;
    a.click(); setTimeout(() => URL.revokeObjectURL(u), 4000);
  });
}
```

`index.html` : dans la `<section>` « Atelier fal » posée par la Task 2, ajouter `<div id="falConvert"></div>` sous le panneau « Job courant ». `fal.js` appelle `brancherConversion(job)` quand un job est sélectionné.

- [ ] **Step 8 : vérification à l'écran (utilisateur)** — ouvrir `/studio3d`, « Atelier fal », choisir un job terminé, format **obj** → le ZIP tombe et s'ouvre dans Blender (import Wavefront) avec sa texture ; format **stl** + 100 mm → le fichier s'ouvre dans le slicer à la bonne taille ; format **fbx** → un job apparaît dans la file avec « 1 cr ».

- [ ] **Step 9 : commit**

```
git add backend/app/services/mesh_convert.py backend/app/api/routes.py backend/tests/test_mesh_convert.py frontend/studio3d/fal.js frontend/studio3d/index.html
git commit -m 'moteurs 3d : P4 - conversion locale obj stl 3mf gltf, fbx usdz blend par Meshy' -m 'gltfpack 1.2 mesuré le 03/09/2026 : entrées obj/gltf/glb, sorties gltf/glb — donc aucun FBX local. L écriture FBX libre est partielle (ASCII lu par Unity et Unreal, refusé par Blender) : on ne l écrit pas, on passe par Meshy convert à 1 crédit par tâche, et la route le dit avant le clic. En local : OBJ avec MTL, UV retournés du bon côté et texture, STL et 3MF aux millimètres par print3d, glTF séparé par gltfpack ; import OBJ, STL, glTF vers GLB.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 6 : P5 — contrôle des vues avant tir

**Files:**
- Modify: `backend/app/services/asset3d_service.py` (extraire `tirer_moteur` de `generate_asset3d`)
- Create: `backend/app/services/asset3d_views.py`
- Modify: `backend/app/api/routes.py` (5 routes, avant le catch-all `{fmt}`)
- Modify: `frontend/studio3d/fal.js`, `frontend/studio3d/index.html`
- Test: `backend/tests/test_asset3d_views.py`

- [ ] **Step 1 : l'extraction, d'abord — sous la garde du banc existant**

Dans `asset3d_service.py`, couper `generate_asset3d` en deux **sans rien changer d'autre**. Remplacer tout ce qui suit `await _step(f"Running {engine}", 60)` (jusqu'au `return` inclus) par un appel, et déclarer juste avant `generate_asset3d` :

```python
async def tirer_moteur(job_id: str, image_urls: list, payload: dict,
                       shots: list, on_step=None) -> dict:
    """Le moteur, les téléchargements, le manifeste et la fiche — la MOITIÉ
    AVAL de `generate_asset3d`, extraite telle quelle.

    Pourquoi l'extraction : P5 (contrôle des vues avant tir) doit pouvoir
    lancer CETTE moitié seule, une fois que l'utilisateur a regardé, rejoué
    et détouré ses vues. Les coutures monkeypatchées des bancs (`_upload`,
    `_seedream_edit`, `_run_engine`, `_download`) ne bougent pas : c'est la
    condition pour que les treize tests d'`test_asset3d_service` restent
    verts sans être touchés.
    """
    import asyncio
    from pathlib import Path
    from app.config import settings

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    formats = [f.lower() for f in (payload.get("formats") or ["glb"])]
    if "glb" not in formats:
        formats = ["glb"] + formats
    out_dir = settings.outputs_path / "assets3d" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    fn = Path(str(payload.get("image_filename") or "")).name

    await _step(f"Running {engine}", 60)
    # ... TOUT le corps historique, de `base_opts = {...}` jusqu'au `return`,
    # copié SANS modification.
```

et, dans `generate_asset3d`, la dernière ligne devient :

```python
    return await tirer_moteur(job_id, image_urls, payload, shots, on_step)
```

- [ ] **Step 2 : prouver que l'extraction n'a rien cassé**

```
python tests/test_asset3d_service.py
python tests/test_asset3d_phase_d.py
```
Attendu : les deux bancs verts, **sans une seule ligne modifiée dans les tests**. Si l'un rougit, l'extraction a changé un comportement — revenir dessus, pas sur le test.

- [ ] **Step 3 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""P5 — les vues avant le tir. Le banc relit les PNG écrits (shot_i.png), le
views.json, et vérifie qu'AUCUN appel moteur n'est parti tant que l'on n'a pas
tiré. fal stubbé, aucun réseau. Run : python tests/test_asset3d_views.py"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import asset3d_views as V, gltf_builder        # noqa: E402

EDITS, MOTEURS, TELECHARGES = [], [], []


async def _faux_upload(p):
    return f"https://fal.test/{pathlib.Path(p).name}"


async def _faux_seedream(url, prompt):
    EDITS.append(prompt)
    return f"https://fal.test/vue{len(EDITS)}.png"


async def _faux_moteur(engine, args, endpoint=None):
    MOTEURS.append((engine, sorted(args)))
    return {"mesh_url": "https://fal.test/m.glb", "format_urls": {},
            "texture_urls": {}, "preview_url": None}


def _faux_download(url, dest, timeout=120):
    TELECHARGES.append(dest.name)
    if str(dest).endswith(".glb"):
        dest.write_bytes(gltf_builder.build_glb({}, None, "cube", "m"))
    else:
        b = io.BytesIO(); Image.new("RGB", (32, 32), (30, 160, 90)).save(b, "PNG")
        dest.write_bytes(b.getvalue())
    return True


A3._upload = _faux_upload
A3._seedream_edit = _faux_seedream
A3._run_engine = _faux_moteur
A3._download = _faux_download


def _source(nom="src.png"):
    b = io.BytesIO(); Image.new("RGB", (64, 64), (200, 90, 40)).save(b, "PNG")
    (settings.images_path / nom).write_bytes(b.getvalue())
    return nom


def _vider():
    EDITS.clear(); MOTEURS.clear(); TELECHARGES.clear()


def test_preparer_genere_les_vues_et_ne_tire_PAS():
    _vider()
    p = {"image_filename": _source(), "engine": "tripo", "views": 4,
         "subject": "un poulpe prophète"}
    r = asyncio.run(V.preparer(p, "vu_prep"))
    d = settings.outputs_path / "assets3d" / "vu_prep"
    assert r["vues"] == 5 and len(EDITS) == 4, (r, EDITS)
    assert MOTEURS == [], "AUCUN moteur ne doit tourner avant le tir"
    for i in range(5):
        assert (d / f"shot_{i}.png").is_file(), i
    vj = json.loads((d / "views.json").read_text("utf-8"))
    assert vj["etat"] == "en_attente" and len(vj["vues"]) == 5, vj
    assert vj["vues"][0]["role"] == "source" and vj["vues"][0]["prompt"] is None
    assert vj["vues"][1]["prompt"] and "poulpe" in vj["vues"][1]["prompt"]
    assert all(v["url"] for v in vj["vues"]), vj


def test_rejouer_une_vue_ne_touche_que_celle_la():
    _vider()
    asyncio.run(V.preparer({"image_filename": _source(), "engine": "tripo",
                            "views": 3}, "vu_rej"))
    d = settings.outputs_path / "assets3d" / "vu_rej"
    avant = (d / "shot_1.png").read_bytes()
    autre = (d / "shot_2.png").read_bytes()
    _vider()
    r = asyncio.run(V.rejouer("vu_rej", 2, prompt="left side view, exact profile"))
    assert len(EDITS) == 1 and EDITS[0].endswith("exact profile"), EDITS
    assert (d / "shot_2.png").read_bytes() != autre, "la vue 2 devait changer"
    assert (d / "shot_1.png").read_bytes() == avant, "la vue 1 ne devait PAS bouger"
    vj = json.loads((d / "views.json").read_text("utf-8"))
    assert vj["vues"][2]["rejeux"] == 1 and vj["vues"][1]["rejeux"] == 0, vj
    assert r["index"] == 2


def test_la_source_ne_se_rejoue_pas():
    asyncio.run(V.preparer({"image_filename": _source(), "engine": "tripo",
                            "views": 1}, "vu_src"))
    try:
        asyncio.run(V.rejouer("vu_src", 0))
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "source" in str(e).lower(), e


def test_le_detourage_local_est_gratuit_et_ecrit_un_alpha():
    _vider()
    asyncio.run(V.preparer({"image_filename": _source(), "engine": "tripo",
                            "views": 2}, "vu_det"))
    d = settings.outputs_path / "assets3d" / "vu_det"
    r = asyncio.run(V.detourer("vu_det", 1, via="local"))
    assert r["via"] == "local" and r["usd"] == 0.0, r
    im = Image.open(d / "shot_1.png")
    assert im.mode == "RGBA", im.mode
    assert im.getchannel("A").getextrema()[0] == 0, "aucun pixel transparent"
    vj = json.loads((d / "views.json").read_text("utf-8"))
    assert vj["vues"][1]["detoure"] == "local", vj


def test_tirer_envoie_les_vues_validees_et_ecrit_le_maillage():
    _vider()
    asyncio.run(V.preparer({"image_filename": _source(), "engine": "tripo",
                            "views": 4}, "vu_tir"))
    d = settings.outputs_path / "assets3d" / "vu_tir"
    r = asyncio.run(V.tirer("vu_tir"))
    assert len(MOTEURS) == 1 and MOTEURS[0][0] == "tripo", MOTEURS
    assert (d / "model.glb").is_file() and r["glb"], r
    assert (d / "asset.json").is_file() and (d / "report.json").is_file()
    vj = json.loads((d / "views.json").read_text("utf-8"))
    assert vj["etat"] == "tire", vj
    assert len(EDITS) == 0, "tirer ne regénère AUCUNE vue"


def test_on_ne_tire_pas_deux_fois_le_meme_jeu_de_vues():
    asyncio.run(V.preparer({"image_filename": _source(), "engine": "tripo",
                            "views": 1}, "vu_2x"))
    asyncio.run(V.tirer("vu_2x"))
    try:
        asyncio.run(V.tirer("vu_2x"))
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "déjà" in str(e), e


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_views)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 4 : lancer** — `python tests/test_asset3d_views.py` → `ModuleNotFoundError: No module named 'app.services.asset3d_views'`.

- [ ] **Step 5 : le service**

Créer `backend/app/services/asset3d_views.py` :

```python
# -*- coding: utf-8 -*-
"""Les vues AVANT le tir — R10e P5.

Aujourd'hui `generate_asset3d` fait tout d'une traite : upload, quatre vues
Seedream, moteur, téléchargements. Une vue ratée (bras coupé, fond sale,
profil de trois quarts) est donc payée DEUX fois — la vue, puis le maillage
qu'elle abîme. Ici la passe est coupée en deux :

    preparer()  upload + vues -> shot_i.png + views.json (état « en_attente »)
    rejouer()   UNE vue seulement, avec un prompt corrigé
    detourer()  fond retiré : local et gratuit d'abord, fal en option
    tirer()     asset3d_service.tirer_moteur() sur les vues validées

Aucune couture nouvelle : `preparer` et `rejouer` appellent les mêmes
`asset3d_service._upload` / `_seedream_edit` / `_download` que le chemin
historique, et `tirer` appelle `tirer_moteur`, la moitié aval extraite.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ETATS = ("en_attente", "tire")
MAX_VUES = 4                 # le quatuor orthographique d'asset3d_service


def _dir(job) -> Path:
    from app.config import settings
    return settings.outputs_path / "assets3d" / Path(str(job)).name


def _chemin(job) -> Path:
    return _dir(job) / "views.json"


def lire(job) -> dict:
    p = _chemin(job)
    if not p.is_file():
        raise FileNotFoundError("aucun jeu de vues pour ce job")
    return json.loads(p.read_text(encoding="utf-8"))


def _ecrire(job, data: dict) -> dict:
    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    _chemin(job).write_text(json.dumps(data, indent=1, ensure_ascii=False),
                            encoding="utf-8")
    return data


async def preparer(payload: dict, job: str, on_step=None) -> dict:
    """Upload + vues, et RIEN d'autre. Le moteur n'est pas appelé : c'est
    tout l'intérêt."""
    import asyncio
    import shutil
    from app.config import settings
    from app.services import asset3d_service as A3

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in A3.ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    fn = Path(str(payload.get("image_filename") or "")).name
    src = settings.images_path / fn
    if not fn or not src.is_file() or not str(src.resolve()).startswith(
            str(settings.images_path.resolve())):
        raise ValueError(
            f"Image not found in Library: {payload.get('image_filename')!r}")
    try:
        n = max(1, min(MAX_VUES, int(payload.get("views", 4))))
    except (TypeError, ValueError):
        n = 4

    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    await _step("Uploading", 10)
    url = await A3._upload(src)
    shutil.copy2(src, d / "shot_0.png")
    vues = [{"index": 0, "role": "source", "file": "shot_0.png", "url": url,
             "prompt": None, "rejeux": 0, "detoure": None}]

    prompts = A3.view_prompts(n, payload.get("subject", ""))
    for i, pr in enumerate(prompts, 1):
        await _step(f"View {i}/{n}", 10 + int(60 * i / max(1, n)))
        try:
            u = await A3._seedream_edit(url, pr)
        except Exception as e:                  # une vue ratée n'annule rien
            vues.append({"index": i, "role": "vue", "file": None, "url": None,
                         "prompt": pr, "rejeux": 0, "detoure": None,
                         "erreur": str(e)})
            continue
        if not u:
            vues.append({"index": i, "role": "vue", "file": None, "url": None,
                         "prompt": pr, "rejeux": 0, "detoure": None,
                         "erreur": "aucune image rendue"})
            continue
        await asyncio.to_thread(A3._download, u, d / f"shot_{i}.png")
        vues.append({"index": i, "role": "vue", "file": f"shot_{i}.png",
                     "url": u, "prompt": pr, "rejeux": 0, "detoure": None})

    await _step("Vues prêtes — à toi de juger", 100)
    info = _ecrire(job, {
        "job": Path(str(job)).name, "etat": "en_attente",
        "payload": {k: v for k, v in payload.items() if k != "image_filename"},
        "image_filename": fn, "engine": engine, "vues": vues,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return {"vues": len(vues), "etat": info["etat"], "job": info["job"],
            "file": None}


async def rejouer(job, index: int, *, prompt: str = None, on_step=None) -> dict:
    """UNE vue régénérée, avec le prompt corrigé si on en donne un. La vue 0
    est la source de l'utilisateur : elle ne se rejoue pas."""
    import asyncio
    from app.services import asset3d_service as A3
    info = lire(job)
    i = int(index)
    vues = info["vues"]
    if not (0 <= i < len(vues)):
        raise ValueError(f"vue {i} inconnue (0..{len(vues) - 1})")
    if vues[i]["role"] == "source":
        raise ValueError("la vue 0 est ta source : elle ne se régénère pas — "
                         "change d'image dans la Bibliothèque.")
    if on_step:
        await on_step(f"Vue {i}", 30)
    pr = str(prompt or vues[i]["prompt"] or "").strip()
    if not pr:
        raise ValueError("cette vue n'a pas de prompt : donnes-en un")
    u = await A3._seedream_edit(vues[0]["url"], pr)
    if not u:
        raise RuntimeError("aucune image rendue")
    await asyncio.to_thread(A3._download, u, _dir(job) / f"shot_{i}.png")
    vues[i].update({"file": f"shot_{i}.png", "url": u, "prompt": pr,
                    "rejeux": int(vues[i].get("rejeux") or 0) + 1,
                    "detoure": None})
    vues[i].pop("erreur", None)
    _ecrire(job, info)
    if on_step:
        await on_step("Complete", 100)
    return {"index": i, "file": f"shot_{i}.png", "rejeux": vues[i]["rejeux"]}


async def detourer(job, index: int, *, via: str = "local",
                   on_step=None) -> dict:
    """Fond retiré. `local` : masque des quatre coins d'`asset3d_qc`, gratuit
    et hors ligne. `fal` : imageutils/rembg, tarif `rembg_api_usd`."""
    import asyncio
    from PIL import Image
    from app.services import asset3d_qc, pricing
    from app.services import asset3d_service as A3
    info = lire(job)
    i = int(index)
    vues = info["vues"]
    if not (0 <= i < len(vues)) or not vues[i].get("file"):
        raise ValueError(f"vue {i} absente : rien à détourer")
    p = _dir(job) / vues[i]["file"]
    if on_step:
        await on_step(f"Détourage vue {i}", 40)

    if via == "fal":
        from app.services import sprite_service
        u = await sprite_service._rembg_api(vues[i]["url"])
        await asyncio.to_thread(A3._download, u, p)
        usd = float(pricing.DEFAULTS["rembg_api_usd"])
        vues[i]["url"] = u
    else:
        def _local():
            masque, methode = asset3d_qc.masque_reference(p)
            im = Image.open(p).convert("RGB")
            masque = masque.resize(im.size, Image.NEAREST)
            rgba = im.convert("RGBA")
            rgba.putalpha(masque)
            rgba.save(p, "PNG")
            return methode
        methode = await asyncio.to_thread(_local)
        usd = 0.0
        vues[i]["methode"] = methode
    vues[i]["detoure"] = via
    _ecrire(job, info)
    if on_step:
        await on_step("Complete", 100)
    return {"index": i, "via": via, "usd": usd, "file": vues[i]["file"]}


async def tirer(job, on_step=None) -> dict:
    """Le moteur, sur les vues telles qu'elles sont MAINTENANT."""
    from app.services import asset3d_service as A3
    info = lire(job)
    if info["etat"] == "tire":
        raise ValueError("ce jeu de vues a déjà été tiré : le maillage existe. "
                         "Prépare un nouveau job pour retirer.")
    urls = [v["url"] for v in info["vues"] if v.get("url")]
    if not urls:
        raise ValueError("aucune vue exploitable : régénère-en au moins une")
    shots = [v["file"] for v in info["vues"] if v.get("file")]
    payload = dict(info.get("payload") or {})
    payload["image_filename"] = info["image_filename"]
    payload["engine"] = info["engine"]
    r = await A3.tirer_moteur(Path(str(job)).name, urls, payload, shots, on_step)
    info["etat"] = "tire"
    info["tire_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire(job, info)
    r["file"] = "model.glb"
    return r
```

- [ ] **Step 6 : relancer** — `python tests/test_asset3d_views.py` → `OK — 6 tests, 0 rouge(s) (asset3d_views)`. Puis `python tests/test_asset3d_service.py` : toujours vert.

- [ ] **Step 7 : les routes** (avant le catch-all `{fmt}`)

```python
@router.post("/assets/3d/views")
async def post_asset3d_views(background_tasks: BackgroundTasks,
                             body: dict = None):
    """Prépare un jeu de vues SANS lancer de moteur. Payant (Seedream) —
    donc un job de la file, comme le rig."""
    from uuid import uuid4 as _u
    from app.services import asset3d_views
    body = body or {}
    job = str(body.get("job") or _u().hex[:12])
    return await _lancer_job_asset3d(
        background_tasks, job=job,
        titre=f"Vues · {body.get('subject') or job}", etape="Vues",
        travail=lambda on_step: asset3d_views.preparer(body, job, on_step),
        cost_meta=lambda r: {"kind": "asset3d_views",
                             "views": int(body.get("views", 4))})


@router.get("/assets/3d/{job}/views")
async def get_asset3d_views(job: str):
    from app.services import asset3d_views
    try:
        return asset3d_views.lire(job)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/assets/3d/{job}/views/{index}/rejouer")
async def post_asset3d_view_rejouer(job: str, index: int,
                                    background_tasks: BackgroundTasks,
                                    body: dict = None):
    from app.services import asset3d_views
    body = body or {}
    return await _lancer_job_asset3d(
        background_tasks, job=job, titre=f"Vue {index} · {Path(job).name}",
        etape=f"Vue {index}",
        travail=lambda on_step: asset3d_views.rejouer(
            job, index, prompt=body.get("prompt"), on_step=on_step),
        cost_meta=lambda r: {"kind": "asset3d_views", "views": 1})


@router.post("/assets/3d/{job}/views/{index}/detourer")
async def post_asset3d_view_detourer(job: str, index: int, body: dict = None):
    """Le détourage local est gratuit et rapide : réponse directe, pas de job."""
    from app.services import asset3d_views
    body = body or {}
    via = "fal" if str(body.get("via") or "local") == "fal" else "local"
    try:
        return await asset3d_views.detourer(job, index, via=via)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/assets/3d/{job}/tirer")
async def post_asset3d_tirer(job: str, background_tasks: BackgroundTasks):
    """Le moteur, enfin — sur des vues regardées."""
    from app.services import asset3d_views
    try:
        info = asset3d_views.lire(job)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    if info["etat"] == "tire":
        raise HTTPException(409, "ce jeu de vues a déjà été tiré.")
    return await _lancer_job_asset3d(
        background_tasks, job=job,
        titre=f"Maillage · {info['engine']} · {Path(job).name}",
        etape=f"Running {info['engine']}",
        travail=lambda on_step: asset3d_views.tirer(job, on_step),
        cost_meta=lambda r: {"kind": "asset3d", "engine": info["engine"],
                             "textures": bool((info.get("payload") or {})
                                              .get("textures", True)),
                             "multiview": True,
                             "views": len(info["vues"]) - 1})
```

- [ ] **Step 8 : le panneau « Vues d'abord » de /studio3d**

Dans `frontend/studio3d/fal.js` :

```js
/* Vues d'abord — la règle du panneau : le bouton « Tirer » reste GRIS tant
   que les vues n'ont pas été regardées au moins une fois. C'est la seule
   chose que P5 ajoute par rapport au flux d'un clic : un temps d'arrêt. */
export async function brancherVues(job) {
  const zone = document.querySelector("#falViews");
  const v = await (await fetch(`/api/assets/3d/${job}/views`)).json();
  const tire = v.etat === "tire";
  zone.innerHTML = `
    <div class="vues-grille">${v.vues.map((x) => `
      <figure class="vue ${x.file ? "" : "vide"}" data-i="${x.index}">
        <img src="/api/assets/3d/${job}/shot/${x.index}?t=${Date.now()}" alt="">
        <figcaption>
          ${x.role === "source" ? "source" : `vue ${x.index}`}
          ${x.rejeux ? ` · ${x.rejeux} rejeu(x)` : ""}
          ${x.detoure ? ` · détourée (${x.detoure})` : ""}
          ${x.erreur ? ` · <b class="rouge">${x.erreur}</b>` : ""}
        </figcaption>
        ${x.role === "source" ? "" : `
          <div class="vue-actions">
            <button class="v-rej" data-i="${x.index}">↻ Rejouer</button>
            <button class="v-det" data-i="${x.index}">✂ Détourer</button>
          </div>`}
      </figure>`).join("")}</div>
    <button id="vTirer" ${tire ? "disabled" : ""}>
      ${tire ? "Déjà tiré" : `Tirer · ${v.engine}`}</button>`;
  zone.querySelectorAll(".v-rej").forEach((b) => b.addEventListener("click", async () => {
    const i = b.dataset.i;
    const prompt = window.prompt("Prompt de cette vue :",
      v.vues[i].prompt || "");
    if (prompt === null) return;
    const r = await fetch(`/api/assets/3d/${job}/views/${i}/rejouer`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }) });
    toast(r.ok ? "Vue relancée — suis la file." : "échec");
  }));
  zone.querySelectorAll(".v-det").forEach((b) => b.addEventListener("click", async () => {
    const r = await fetch(`/api/assets/3d/${job}/views/${b.dataset.i}/detourer`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ via: "local" }) });
    if (r.ok) { toast("Détourée (local, gratuit)"); brancherVues(job); }
    else toast((await r.json().catch(() => ({}))).detail || "échec");
  }));
  const bt = document.querySelector("#vTirer");
  if (bt && !tire) bt.addEventListener("click", async () => {
    const r = await fetch(`/api/assets/3d/${job}/tirer`, { method: "POST" });
    toast(r.ok ? "Moteur lancé — suis la file."
               : (await r.json().catch(() => ({}))).detail || "échec");
  });
}
```

`index.html` : ajouter `<div id="falViews"></div>` en tête de la `<section>` « Atelier fal ».

- [ ] **Step 9 : vérification à l'écran (utilisateur)** — dans `/studio3d`, « Atelier fal », lancer un jeu de vues sur une image de la Bibliothèque : les 5 vignettes apparaissent, **aucun coût de moteur n'a été engagé** (la file n'affiche qu'une ligne « Vues »), rejouer la vue 3 avec un prompt corrigé, la détourer, puis « Tirer ». Le maillage arrive avec les vues validées.

- [ ] **Step 10 : commit**

```
git add backend/app/services/asset3d_service.py backend/app/services/asset3d_views.py backend/app/api/routes.py backend/tests/test_asset3d_views.py frontend/studio3d/fal.js frontend/studio3d/index.html
git commit -m 'moteurs 3d : P5 - les vues se regardent, se rejouent et se detourent avant le tir' -m 'La passe unique de generate_asset3d est coupée en deux : la moitié aval devient tirer_moteur (les treize tests d asset3d_service restent verts sans être touchés), et asset3d_views porte préparer, rejouer une vue seule, détourer (masque des quatre coins, gratuit et hors ligne ; fal en option), puis tirer. Une vue ratée ne coûte plus deux fois : la vue, puis le maillage qu elle abîme.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

> Le lot 1 met l'application à la hauteur de ce que les concurrents font déjà. Le lot 2 fait ce qu'ils ne font pas : les vues viennent de la **bible** au lieu d'un prompt neuf (D1), la matrice besoin → moteur cite des **chiffres mesurés chez nous** au lieu de fiches produit (D2), les matières du **Forge** habillent le maillage (D3), un **service GPU local** optionnel rend le brouillon gratuit et hors ligne (D4), et les vues peuvent venir de **photos réelles** (D5). Chacune s'appuie sur une brique du lot 1 : D1, D5 sur P5 ; D3 sur P3 ; D4 sur le registre des moteurs ; D2 sur P2 et sur la fiche de maillage.

### Task 7 : D1 — les vues viennent de la planche de la bible

**Files:**
- Modify: `backend/app/services/board_service.py` (`decouper_planche`, `panneaux_de_la_recette`)
- Modify: `backend/app/services/asset3d_views.py` (`preparer_depuis_images`)
- Modify: `backend/app/api/routes.py:5561` (la recette persiste le **fichier** de chaque panneau), route `POST /bible/entities/{entity_id}/model3d` (branche `from_board`), route `POST /assets/3d/{job}/tirer` (rattachement à l'entité)
- Test: `backend/tests/test_asset3d_bible_vues.py`

**Le fait qui commande cette tâche** (mesuré le 03/09/2026) : la planche personnage est composée **par code** (`board_service.compose_character_board`) — colonnes `front, left, right, back`, gouttières de `_GUTTER = 28` px, fond `_BG = (242, 239, 233)`, visages 300 px, corps 560 px. Mais `prompt_recipe.panels` ne garde que `{key, prompt, seed, model}` : **le nom de fichier de chaque panneau n'est pas persisté**. Deux chemins, donc, et les deux sont livrés : persister `file` pour les planches à venir, et **découper** la planche par détection de gouttières pour celles qui existent déjà.

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""D1 — les quatre vues viennent de la planche de la bible. Le banc COMPOSE
une vraie planche avec board_service, la relit, la découpe, et vérifie que les
morceaux sont les panneaux d'origine. Aucun réseau : Seedream n'est jamais
appelé — c'est le point. Run : python tests/test_asset3d_bible_vues.py"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import asset3d_views as V, board_service as BS  # noqa: E402

UPLOADS, EDITS = [], []


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).name}"


async def _faux_seedream(url, prompt):
    EDITS.append(prompt)
    return "https://fal.test/jamais.png"


def _faux_download(url, dest, timeout=120):
    b = io.BytesIO(); Image.new("RGB", (8, 8), (0, 0, 0)).save(b, "PNG")
    dest.write_bytes(b.getvalue()); return True


A3._upload = _faux_upload
A3._seedream_edit = _faux_seedream
A3._download = _faux_download


def _panneau(nom, couleur, w, h):
    b = settings.images_path / nom
    Image.new("RGB", (w, h), couleur).save(b, "PNG")
    return nom


def _planche() -> str:
    panels = {
        "front": _panneau("p_front.png", (220, 40, 40), 300, 700),
        "left": _panneau("p_left.png", (40, 220, 40), 300, 700),
        "right": _panneau("p_right.png", (40, 40, 220), 300, 700),
        "back": _panneau("p_back.png", (220, 220, 40), 300, 700),
        "face_front": _panneau("f_front.png", (200, 60, 60), 300, 300),
        "face_left": _panneau("f_left.png", (60, 200, 60), 300, 300),
        "face_right": _panneau("f_right.png", (60, 60, 200), 300, 300),
    }
    return BS.compose_character_board(settings.images_path, panels)


def test_la_planche_se_decoupe_en_quatre_colonnes_par_les_gouttieres():
    board = _planche()
    cols = BS.decouper_planche(settings.images_path, board)
    assert list(cols) == ["front", "left", "right", "back"], list(cols)
    couleurs = {}
    for k, f in cols.items():
        p = settings.images_path / f
        assert p.is_file(), (k, f)
        im = Image.open(p).convert("RGB")
        # le CORPS domine la colonne (560 px contre 300) : le pixel du bas la nomme
        couleurs[k] = im.getpixel((im.width // 2, int(im.height * 0.85)))
    assert couleurs["front"][0] > 150 and couleurs["front"][1] < 100, couleurs
    assert couleurs["left"][1] > 150 and couleurs["left"][0] < 100, couleurs
    assert couleurs["right"][2] > 150 and couleurs["right"][0] < 100, couleurs
    assert couleurs["back"][0] > 150 and couleurs["back"][2] < 100, couleurs
    assert len(set(couleurs.values())) == 4, couleurs


def test_une_image_qui_n_est_pas_une_planche_refuse_en_le_disant():
    _panneau("solo.png", (10, 10, 10), 512, 512)
    try:
        BS.decouper_planche(settings.images_path, "solo.png")
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "gouttière" in str(e) or "colonne" in str(e), e


def test_la_recette_rend_les_fichiers_quand_elle_les_a_persistes():
    recette = {"v": 2, "kind": "character", "panels": [
        {"key": "front", "file": "p_front.png"},
        {"key": "left", "file": "p_left.png"},
        {"key": "right", "file": "p_right.png"},
        {"key": "back", "file": "p_back.png"},
        {"key": "face_front", "file": "f_front.png"}]}
    assert BS.panneaux_de_la_recette(recette) == {
        "front": "p_front.png", "left": "p_left.png",
        "right": "p_right.png", "back": "p_back.png"}
    assert BS.panneaux_de_la_recette({"v": 2, "panels": [
        {"key": "front", "prompt": "x", "seed": 1}]}) is None
    assert BS.panneaux_de_la_recette(None) is None


def test_les_vues_venues_de_la_planche_ne_coutent_aucune_generation():
    board = _planche()
    cols = BS.decouper_planche(settings.images_path, board)
    UPLOADS.clear(); EDITS.clear()
    r = asyncio.run(V.preparer_depuis_images(
        "bib_vues", [cols[k] for k in ("front", "left", "right", "back")],
        {"engine": "tripo-h3.1", "subject": "le prophète",
         "entity_id": "ent-42"}))
    assert EDITS == [], "AUCUN appel Seedream : les vues existent déjà"
    assert r["vues"] == 4 and len(UPLOADS) == 4, (r, UPLOADS)
    d = settings.outputs_path / "assets3d" / "bib_vues"
    for i in range(4):
        assert (d / f"shot_{i}.png").is_file(), i
    vj = json.loads((d / "views.json").read_text("utf-8"))
    assert vj["etat"] == "en_attente" and vj["entity_id"] == "ent-42", vj
    assert vj["source"] == "planche", vj
    assert [v["role"] for v in vj["vues"]] == ["source", "vue", "vue", "vue"]
    assert all(v["prompt"] is None for v in vj["vues"]), vj


def test_une_liste_vide_ou_trop_longue_est_refusee():
    for mauvais in ([], ["a.png"] * 5):
        try:
            asyncio.run(V.preparer_depuis_images("bib_ko", mauvais, {}))
            raise AssertionError(f"aurait dû refuser {len(mauvais)}")
        except ValueError as e:
            assert "1 à 4" in str(e), e


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (bible_vues)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer** — `python tests/test_asset3d_bible_vues.py` → cinq `✗` avec `AttributeError: module 'app.services.board_service' has no attribute 'decouper_planche'` (et l'équivalent pour `preparer_depuis_images`).

- [ ] **Step 3 : la découpe de planche**

À la fin de `backend/app/services/board_service.py` :

```python
def panneaux_de_la_recette(recette) -> dict | None:
    """Les fichiers des quatre panneaux de corps d'une recette de planche, ou
    None si la recette ne les porte pas.

    `prompt_recipe.panels` n'a persisté que {key, prompt, seed, model} jusqu'au
    03/09/2026 : les planches d'AVANT n'ont pas de `file`, et pour celles-là
    c'est `decouper_planche` qui fait le travail. Rendre None au lieu d'un
    dictionnaire à trous est ce qui permet à l'appelant de choisir la voie."""
    if not isinstance(recette, dict):
        return None
    voulus = ("front", "left", "right", "back")
    par_cle = {p.get("key"): p.get("file")
               for p in (recette.get("panels") or []) if isinstance(p, dict)}
    if not all(par_cle.get(k) for k in voulus):
        return None
    return {k: par_cle[k] for k in voulus}


def _colonnes_par_gouttieres(im, fond=_BG, tol: int = 12,
                             mini_gouttiere: int = None) -> list[tuple[int, int]]:
    """Les intervalles [x0, x1) des colonnes, séparés par des bandes VERTICALES
    entièrement au fond. La planche est composée par code : les gouttières font
    exactement `_GUTTER` px et le fond est exactement `_BG` — on cherche donc
    une bande pleine, pas une heuristique de contenu."""
    mini = int(mini_gouttiere or max(4, _GUTTER // 2))
    w, h = im.size
    px = im.convert("RGB").load()
    # une colonne de pixels est « vide » si TOUS ses pixels sont au fond ;
    # on n'échantillonne que 1 ligne sur 8 — la planche est plate, et 8x moins
    # de lectures suffisent à distinguer une gouttière d'un panneau
    vide = []
    for x in range(w):
        v = True
        for y in range(0, h, 8):
            p = px[x, y]
            if (abs(p[0] - fond[0]) + abs(p[1] - fond[1])
                    + abs(p[2] - fond[2])) > tol * 3:
                v = False
                break
        vide.append(v)
    cols, debut = [], None
    for x in range(w):
        if not vide[x] and debut is None:
            debut = x
        elif vide[x] and debut is not None:
            # ne coupe que si la bande vide est assez large pour être une gouttière
            fin_vide = x
            while fin_vide < w and vide[fin_vide]:
                fin_vide += 1
            if fin_vide - x >= mini or fin_vide >= w:
                cols.append((debut, x))
                debut = None
    if debut is not None:
        cols.append((debut, w))
    return cols


def decouper_planche(images_path: Path, board_file: str,
                     cles=("front", "left", "right", "back")) -> dict[str, str]:
    """Redécoupe une planche personnage en ses colonnes, écrites dans la
    Bibliothèque. Rend {clé: filename}.

    C'est le chemin de RATTRAPAGE pour les planches composées avant que la
    recette ne persiste ses panneaux. Il refuse plutôt que de deviner : une
    image qui ne donne pas exactement autant de colonnes que de clés n'est pas
    une planche personnage, et un maillage bâti sur une découpe fausse coûte
    une génération payée pour rien.
    """
    im = _load(images_path, board_file)
    cols = _colonnes_par_gouttieres(im)
    if len(cols) != len(cles):
        raise ValueError(
            f"« {board_file} » donne {len(cols)} colonne(s) séparées par des "
            f"gouttières, il en faut {len(cles)} ({', '.join(cles)}). Ce n'est "
            "pas une planche personnage composée par l'application — choisis "
            "les vues une à une dans la Bibliothèque.")
    out = {}
    for k, (x0, x1) in zip(cles, cols):
        crop = im.crop((x0, 0, x1, im.height))
        # on ôte les bandes de fond en HAUT et en BAS de la colonne : la
        # colonne « back » n'a pas de visage, sa moitié haute est vide, et
        # une vue à moitié vide envoyée au moteur donne un objet minuscule
        # perdu dans un cadre. On échantillonne 1 colonne de pixels sur 4 :
        # assez pour trouver la première ligne pleine, 4x moins de lectures.
        rgb = crop.convert("RGB")
        px = rgb.load()
        pleines = []
        for y in range(crop.height):
            for x in range(0, crop.width, 4):
                c = px[x, y]
                if (abs(c[0] - _BG[0]) + abs(c[1] - _BG[1])
                        + abs(c[2] - _BG[2])) > 36:
                    pleines.append(y)
                    break
        if pleines:
            crop = crop.crop((0, pleines[0], crop.width, pleines[-1] + 1))
        nom = f"vue_{k}_{uuid4().hex[:8]}.png"
        crop.save(images_path / nom)
        out[k] = nom
    logger.info(f"planche {board_file} découpée en {len(out)} vues : "
                f"{', '.join(out.values())}")
    return out
```

- [ ] **Step 4 : les vues sans génération**

À la fin de `backend/app/services/asset3d_views.py` :

```python
async def preparer_depuis_images(job: str, fichiers, payload: dict,
                                 on_step=None) -> dict:
    """Un jeu de vues bâti sur des images qui EXISTENT DÉJÀ dans la
    Bibliothèque — panneaux d'une planche de bible (D1) ou photos importées
    (D5). Aucun appel Seedream : c'est tout l'intérêt, et le banc le vérifie
    en comptant les appels, pas en lisant le code.

    La première image devient `shot_0` (la « source » au sens du moteur) ;
    les autres suivent dans l'ordre donné. L'ordre imposé par H3.1
    (`[front, left, back, right]`) est appliqué plus tard par
    `asset3d_service.ordonner_vues`, comme pour tout autre chemin.
    """
    import asyncio
    import shutil
    from app.config import settings
    from app.services import asset3d_service as A3

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    noms = [Path(str(f)).name for f in (fichiers or [])]
    if not (1 <= len(noms) <= MAX_VUES):
        raise ValueError(f"il faut de 1 à 4 images ; {len(noms)} donnée(s)")
    racine = settings.images_path.resolve()
    chemins = []
    for n in noms:
        p = settings.images_path / n
        if not p.is_file() or not str(p.resolve()).startswith(str(racine)):
            raise ValueError(f"Image not found in Library: {n!r}")
        chemins.append(p)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in A3.ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    vues = []
    for i, p in enumerate(chemins):
        await _step(f"Vue {i + 1}/{len(chemins)}",
                    10 + int(80 * (i + 1) / len(chemins)))
        shutil.copy2(p, d / f"shot_{i}.png")
        url = await A3._upload(p)
        vues.append({"index": i, "role": "source" if i == 0 else "vue",
                     "file": f"shot_{i}.png", "url": url, "prompt": None,
                     "rejeux": 0, "detoure": None, "origine": p.name})

    await _step("Vues prêtes — à toi de juger", 100)
    info = _ecrire(job, {
        "job": Path(str(job)).name, "etat": "en_attente",
        "source": str(payload.get("source") or "planche"),
        "entity_id": payload.get("entity_id"),
        "payload": {k: v for k, v in payload.items()
                    if k not in ("image_filename", "entity_id", "source")},
        "image_filename": noms[0], "engine": engine, "vues": vues,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return {"vues": len(vues), "etat": info["etat"], "job": info["job"],
            "file": None}
```

Note : `rejouer()` refuse déjà une vue sans prompt (« cette vue n'a pas de prompt : donnes-en un ») — c'est exactement le bon comportement ici, une vue venue d'une planche n'a pas de prompt à rejouer.

- [ ] **Step 5 : relancer** — `python tests/test_asset3d_bible_vues.py` → `OK — 5 tests, 0 rouge(s) (bible_vues)`. Puis `python tests/test_asset3d_views.py` : toujours vert.

- [ ] **Step 6 : persister le fichier des panneaux, pour les planches à venir**

Dans `routes.py`, ligne 5561, la recette :

```python
            recipe_panels.append({"key": key, "prompt": prompt,
                                  "seed": out.get("seed"), "model": model,
                                  # persisté depuis le 03/09/2026 : sans lui,
                                  # « vues depuis la planche » (R10e D1) doit
                                  # redécouper l'image au lieu de reprendre
                                  # les panneaux d'origine
                                  "file": out["images"][0]})
```

et, juste après la boucle des miroirs (`panels[tgt] = BS.mirror_panel(...)`), enregistrer aussi les miroirs :

```python
        for tgt, src in (plan.get("mirrors") or {}).items():
            panels[tgt] = BS.mirror_panel(settings.images_path, panels[src])
            recipe_panels.append({"key": tgt, "prompt": None, "seed": None,
                                  "model": "miroir", "file": panels[tgt]})
```

- [ ] **Step 7 : la branche `from_board` de la route de la bible**

Dans `POST /bible/entities/{entity_id}/model3d`, juste après la lecture de l'entité (`nom, kind, ref = e.name, e.kind, e.ref_image`), ajouter — **avant** le refus « c'est une PLANCHE composite », qui garde tout son sens pour les autres appels :

```python
    # R10e D1 — les quatre vues viennent de la planche, pas d'un prompt neuf.
    # L'identité tenue par la bible (R3) est CE qu'on ne veut pas régénérer.
    if body.get("from_board"):
        from app.services import board_service as BS
        from app.services import asset3d_views
        async with async_session_factory() as session:
            ent = await session.get(BibleEntity, entity_id)
            recette = getattr(ent, "prompt_recipe", None)
        try:
            recette = _json.loads(recette) if recette else None
        except Exception:
            recette = None
        vues = BS.panneaux_de_la_recette(recette)
        if vues is None:
            if not (ref or "").startswith("board_"):
                raise HTTPException(
                    400, f"« {nom} » n'a pas de planche composite : génère-la "
                         "d'abord (Planche), ou choisis une vue seule.")
            try:
                vues = await asyncio.to_thread(
                    BS.decouper_planche, settings.images_path, ref)
            except (ValueError, FileNotFoundError) as e:
                raise HTTPException(400, str(e))
        job = uuid4().hex[:12]
        return await _lancer_job_asset3d(
            background_tasks, job=job, titre=f"Vues de la planche · {nom}",
            etape="Vues", travail=lambda on_step: asset3d_views.preparer_depuis_images(
                job, [vues[k] for k in ("front", "left", "right", "back")],
                {"engine": str(body.get("engine") or "tripo-h3.1"),
                 "subject": nom, "entity_id": entity_id, "source": "planche",
                 "textures": body.get("textures", True),
                 "quality": body.get("quality"),
                 "formats": body.get("formats") or ["glb"]},
                on_step),
            cost_meta=lambda r: {"kind": "asset3d_views", "views": 0,
                                 "note": "vues reprises de la planche — "
                                         "aucune génération d'image"})
```

- [ ] **Step 8 : le rattachement à l'entité, au tir**

Dans `routes.py`, juste avant `@router.post("/assets/3d/{job}/tirer")` :

```python
async def _tirer_et_rattacher(job: str, info: dict, on_step):
    """Le tir, puis — s'il vient d'une entité de la bible — le maillage rejoint
    sa fiche. Le service `asset3d_views` reste sans base de données : c'est la
    route qui connaît la bible, comme partout ailleurs dans ce fichier."""
    from app.services import asset3d_views
    from app.services.storage import BibleEntity, async_session_factory
    r = await asset3d_views.tirer(job, on_step)
    eid = info.get("entity_id")
    if eid:
        async with async_session_factory() as session:
            ent = await session.get(BibleEntity, eid)
            if ent is not None:
                ent.model3d_job = Path(str(job)).name
                ent.model3d_file = "model.glb"
                ent.updated_at = datetime.utcnow()
                await session.commit()
    return r
```
et, dans la route, `travail=lambda on_step: _tirer_et_rattacher(job, info, on_step)`.

- [ ] **Step 9 : vérification à l'écran (utilisateur)** — dans la bible, sur une entité personnage qui a déjà sa planche : « Verrouiller en 3D » avec `from_board` → la file affiche « Vues de la planche · <nom> » **sans coût d'image**, `/studio3d` → Atelier fal montre les quatre colonnes de la planche comme vues, « Tirer » → le maillage apparaît **et** la fiche de l'entité porte son `model3d_job`.

- [ ] **Step 10 : commit**

```
git add backend/app/services/board_service.py backend/app/services/asset3d_views.py backend/app/api/routes.py backend/tests/test_asset3d_bible_vues.py
git commit -m 'moteurs 3d : D1 - les quatre vues viennent de la planche de la bible' -m 'Deux chemins, les deux livrés : la recette persiste désormais le fichier de chaque panneau (miroirs compris), et les planches déjà composées se redécoupent par détection des gouttières de 28 px sur le fond exact de compose_character_board. preparer_depuis_images n appelle AUCUN modèle d image — le banc le vérifie en comptant les appels. Au tir, le maillage rejoint la fiche de l entité.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 8 : D2 — banc de référence par sujet type

**Files:**
- Create: `backend/app/services/asset3d_banc.py`
- Create: `scripts/banc_moteurs3d.py`
- Modify: `backend/app/api/routes.py` (`GET /assets3d/engines` cite les chiffres du banc)
- Modify: `frontend/studio3d/fal.js` (le tableau)
- Test: `backend/tests/test_asset3d_banc.py`

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""D2 — banc de référence par sujet type. Le banc du banc : il RELIT le
banc.json écrit, et vérifie que les chiffres viennent des fiches de maillage,
pas d'une saisie. Aucun réseau. Run : python tests/test_asset3d_banc.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                                  # noqa: E402
from app.services import asset3d_banc as B                       # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import gltf_builder, mesh_report               # noqa: E402


def _job(nom: str, moteur: str, forme: str = "sphere") -> str:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, forme, nom))
    A3.write_manifest(d, {"engine": moteur, "stage": "final", "version": 1,
                          "texture_mode": "standard", "shots": [],
                          "quality": "medium"})
    mesh_report.write_report(nom, "model.glb", version=1, avec_silhouettes=True)
    return nom


def test_les_sujets_types_sont_trois_et_portent_leur_consigne():
    s = {x["id"]: x for x in B.sujets()}
    assert set(s) == {"personnage", "objet", "vehicule"}, sorted(s)
    for x in s.values():
        assert x["label"] and x["prompt"] and x["besoin"], x


def test_mesurer_lit_la_fiche_du_maillage_et_pas_une_saisie():
    _job("bc_a", "tripo")
    L = B.mesurer("bc_a", "personnage", "tripo")
    assert L["sujet"] == "personnage" and L["moteur"] == "tripo", L
    assert L["tris"] > 0 and L["bytes"] > 0 and L["sha256"], L
    assert L["usd_estime"] > 0, L
    assert set(L["couverture"]) == {"face", "profil", "dessus"}, L
    assert L["ferme"] in (True, False), L
    relu = json.loads((settings.outputs_path / "assets3d" / "_banc"
                       / "banc.json").read_text("utf-8"))
    # les lignes sont TRIÉES par (moteur, sujet) : la dernière écrite n'est pas
    # la dernière du fichier — on cherche la ligne, on ne suppose pas sa place
    assert L in relu["lignes"], relu


def test_remesurer_le_meme_couple_remplace_la_ligne_sans_effacer_les_autres():
    _job("bc_b", "trellis", "cube")
    B.mesurer("bc_b", "objet", "trellis")
    n1 = len(B.lire()["lignes"])
    B.mesurer("bc_b", "objet", "trellis")
    assert len(B.lire()["lignes"]) == n1, "un couple sujet+moteur = UNE ligne"
    B.mesurer("bc_b", "vehicule", "trellis")
    assert len(B.lire()["lignes"]) == n1 + 1


def test_le_resume_par_moteur_donne_ce_que_la_matrice_cite():
    # ce banc lance ses tests dans l'ordre ALPHABÉTIQUE : chacun pose donc ses
    # propres points, sinon celui-ci lirait un banc encore vide
    _job("bc_c", "triposr", "cube")
    B.mesurer("bc_c", "objet", "triposr")
    _job("bc_c2", "trellis")
    B.mesurer("bc_c2", "personnage", "trellis")
    _job("bc_c3", "tripo", "cube")
    B.mesurer("bc_c3", "vehicule", "tripo")
    r = B.resume_par_moteur()
    assert "triposr" in r, sorted(r)
    x = r["triposr"]
    assert x["sujets"] >= 1 and x["tris_median"] > 0 and x["usd_median"] > 0, x
    assert "trellis" in r and "tripo" in r, sorted(r)
    assert "rodin" not in r, "un moteur jamais mesuré n'invente pas de chiffres"


def test_un_job_sans_fiche_refuse_au_lieu_de_deviner():
    d = settings.outputs_path / "assets3d" / "bc_vide"
    d.mkdir(parents=True, exist_ok=True)
    try:
        B.mesurer("bc_vide", "objet", "tripo")
        raise AssertionError("aurait dû refuser")
    except FileNotFoundError as e:
        assert "fiche" in str(e).lower() or "report" in str(e).lower(), e
    try:
        B.mesurer("bc_c", "poisson", "tripo")
        raise AssertionError("sujet inconnu")
    except ValueError as e:
        assert "poisson" in str(e), e


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_banc)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer** — `python tests/test_asset3d_banc.py` → `ModuleNotFoundError: No module named 'app.services.asset3d_banc'`.

- [ ] **Step 3 : le service**

Créer `backend/app/services/asset3d_banc.py` :

```python
# -*- coding: utf-8 -*-
"""Banc de référence par sujet type — R10e D2.

Le registre des moteurs (`asset3d_service.ENGINES`) porte des drapeaux et des
notes ; la matrice `BESOINS_3D` recommande. Aucun des deux ne dit ce que CE
moteur produit CHEZ NOUS : combien de triangles, quel poids, quelle silhouette,
pour combien. Ce module range ces chiffres — un par (sujet type, moteur) — et
les rend à `/assets3d/engines`, qui cesse alors de citer des fiches produit.

Il ne GÉNÈRE rien : générer coûte de l'argent, et l'argent se dépense sur un
geste de l'utilisateur. `scripts/banc_moteurs3d.py` propose le plan de tir et
`mesurer()` enregistre ce qui a été produit. Tout ce qu'il lit vient de la
fiche de maillage (`report.json`) et du manifeste (`asset.json`) — écrits par
le flux normal, jamais saisis à la main.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

SUJETS = {
    "personnage": {
        "label": "Personnage",
        "besoin": "hero",
        "prompt": "full body character, T-pose, stylized, plain flat neutral "
                  "background, even diffuse lighting, no cast shadow",
    },
    "objet": {
        "label": "Objet / accessoire",
        "besoin": "prop",
        "prompt": "a single hand prop object, centered, plain flat neutral "
                  "background, even diffuse lighting, no cast shadow",
    },
    "vehicule": {
        "label": "Véhicule",
        "besoin": "decor",
        "prompt": "a small vehicle, three quarter view, centered, plain flat "
                  "neutral background, even diffuse lighting, no cast shadow",
    },
}


def sujets() -> list[dict]:
    return [{"id": k, **v} for k, v in SUJETS.items()]


def _dossier():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "_banc"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lire() -> dict:
    p = _dossier() / "banc.json"
    if not p.is_file():
        return {"lignes": [], "created_at": None}
    try:
        charge = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"lignes": [], "created_at": None}
    if not isinstance(charge, dict) or not isinstance(charge.get("lignes"), list):
        return {"lignes": [], "created_at": None}
    return charge


def mesurer(job, sujet: str, moteur: str, *, version: int = None) -> dict:
    """Range un job déjà produit comme point de référence.

    Le couple (sujet, moteur) est la CLÉ : remesurer remplace la ligne, comme
    `mesh_report.write_report` remplace une fiche de même version. Sans cela,
    trois essais du même moteur pèseraient trois fois dans la médiane.
    """
    from app.services import asset3d_service, mesh_report, pricing
    sujet = str(sujet)
    if sujet not in SUJETS:
        raise ValueError(f"sujet type inconnu : {sujet!r} "
                         f"(attendu : {', '.join(SUJETS)})")
    reg = mesh_report.read_registry(Path(str(job)).name)   # FileNotFoundError si absente
    entrees = reg.get("entries") or []
    if not entrees:
        raise FileNotFoundError(f"la fiche de {job} est vide : rien à mesurer")
    v = int(version) if version else int(reg.get("current_version") or
                                         entrees[-1].get("version") or 1)
    fiche = next((e for e in entrees if int(e.get("version") or 0) == v),
                 entrees[-1])
    try:
        man = asset3d_service.read_manifest(Path(str(job)).name)
    except Exception:
        man = {}
    geo = fiche.get("geometry") or {}
    topo = geo.get("topologie") or {}
    sil = fiche.get("silhouettes") or {}
    devis = pricing.estimate({
        "kind": "asset3d", "engine": moteur,
        "textures": (man.get("texture_mode") or "standard") != "no",
        "quality": man.get("quality"),
        "multiview": bool(man.get("multiview")),
        "views": int(man.get("views") or 0)})

    ligne = {
        "sujet": sujet, "moteur": str(moteur), "job": Path(str(job)).name,
        "version": v,
        "tris": int(geo.get("tris") or 0),
        "verts": int(geo.get("verts") or 0),
        "materials": int(geo.get("materials") or 0),
        "bytes": int(fiche.get("bytes") or 0),
        "texture_bytes": int((fiche.get("gltf") or {}).get("texture_bytes") or 0),
        "sha256": fiche.get("sha256"),
        "ferme": topo.get("ferme"),
        "bord_pct": topo.get("bord_pct"),
        "couverture": {k: (sil.get(k) or {}).get("couverture")
                       for k in ("face", "profil", "dessus")},
        "texture_mode": man.get("texture_mode"),
        "usd_estime": float(devis["total_usd"]),
        "mesure_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    banc = lire()
    banc["lignes"] = [l for l in banc["lignes"]
                      if not (l.get("sujet") == sujet
                              and l.get("moteur") == str(moteur))]
    banc["lignes"].append(ligne)
    banc["lignes"].sort(key=lambda l: (l.get("moteur") or "",
                                       l.get("sujet") or ""))
    banc.setdefault("created_at",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))
    banc["updated_at"] = ligne["mesure_le"]
    (_dossier() / "banc.json").write_text(
        json.dumps(banc, indent=1, ensure_ascii=False), encoding="utf-8")
    return ligne


def resume_par_moteur() -> dict:
    """{moteur: {sujets, tris_median, bytes_median, usd_median, ferme_sur}} —
    ce que la matrice besoin → moteur peut CITER. Un moteur jamais mesuré est
    absent : mieux vaut un trou visible qu'un chiffre inventé."""
    out: dict[str, dict] = {}
    par_moteur: dict[str, list] = {}
    for l in lire()["lignes"]:
        par_moteur.setdefault(l.get("moteur") or "?", []).append(l)
    for m, lignes in par_moteur.items():
        tris = [int(l.get("tris") or 0) for l in lignes if l.get("tris")]
        octs = [int(l.get("bytes") or 0) for l in lignes if l.get("bytes")]
        usd = [float(l.get("usd_estime") or 0) for l in lignes]
        out[m] = {
            "sujets": len({l.get("sujet") for l in lignes}),
            "tris_median": int(statistics.median(tris)) if tris else 0,
            "bytes_median": int(statistics.median(octs)) if octs else 0,
            "usd_median": round(statistics.median(usd), 4) if usd else 0.0,
            "ferme_sur": sum(1 for l in lignes if l.get("ferme")),
            "mesures": len(lignes),
            "dernier": max((l.get("mesure_le") or "") for l in lignes),
        }
    return out
```

- [ ] **Step 4 : relancer** — `python tests/test_asset3d_banc.py` → `OK — 5 tests, 0 rouge(s) (asset3d_banc)`.

- [ ] **Step 5 : la matrice cite ses chiffres**

Dans `routes.py`, `GET /assets3d/engines`, après la boucle `for eid, e in ENGINES.items():` :

```python
    from app.services import asset3d_banc
    banc = asset3d_banc.resume_par_moteur()
    for m in out:
        m["banc"] = banc.get(m["id"])       # None = jamais mesuré, dit tel quel
```
et le `return` gagne `"sujets_banc": asset3d_banc.sujets(),`.

- [ ] **Step 6 : le script de campagne**

Créer `scripts/banc_moteurs3d.py` :

```python
# -*- coding: utf-8 -*-
# scripts/banc_moteurs3d.py
"""Campagne du banc de référence 3D — R10e D2.

Ce script NE DÉPENSE RIEN tout seul. Sans argument il imprime le plan de tir
(sujet x moteur, coût estimé, ce qui est déjà mesuré) ; avec `--enregistrer
<job> <sujet> <moteur>` il range un job déjà produit.

  python scripts/banc_moteurs3d.py
  python scripts/banc_moteurs3d.py --enregistrer 7f3a1b2c personnage tripo

Le tir lui-même se fait par l'interface (/studio3d, Atelier fal), en connaissant
le coût : c'est la même règle que partout, l'argent se dépense sur un geste.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services import asset3d_banc as B          # noqa: E402
from app.services import asset3d_service as A3      # noqa: E402
from app.services import pricing                    # noqa: E402


def plan():
    fait = {(l["sujet"], l["moteur"]) for l in B.lire()["lignes"]}
    total = 0.0
    print(f"{'sujet':<12} {'moteur':<12} {'coût estimé':>12}  état")
    for s in B.SUJETS:
        for m in sorted(A3.ENGINES):
            usd = pricing.estimate({"kind": "asset3d", "engine": m,
                                    "textures": True, "multiview": True,
                                    "views": 4})["total_usd"]
            etat = "mesuré" if (s, m) in fait else "à tirer"
            if etat == "à tirer":
                total += usd
            print(f"{s:<12} {m:<12} {usd:>11.4f} $  {etat}")
    print(f"\nReste à dépenser pour compléter le banc : {total:.2f} $ "
          f"({len(B.SUJETS) * len(A3.ENGINES) - len(fait)} tirs).")
    r = B.resume_par_moteur()
    if r:
        print("\nCe que le banc dit déjà :")
        for m, x in sorted(r.items()):
            print(f"  {m:<12} {x['sujets']} sujet(s) · "
                  f"{x['tris_median']} tris médians · "
                  f"{x['usd_median']:.4f} $ médians · "
                  f"étanche sur {x['ferme_sur']}/{x['mesures']}")


def main():
    a = sys.argv[1:]
    if a and a[0] == "--enregistrer":
        if len(a) != 4:
            raise SystemExit("Usage: --enregistrer <job> <sujet> <moteur>")
        ligne = B.mesurer(a[1], a[2], a[3])
        print(f"OK — {ligne['sujet']} / {ligne['moteur']} : "
              f"{ligne['tris']} tris, {ligne['bytes']} o, "
              f"{ligne['usd_estime']:.4f} $ estimés, "
              f"étanche={ligne['ferme']}")
        return
    plan()


if __name__ == "__main__":
    main()
```

Lancer : `python scripts/banc_moteurs3d.py`
Attendu : un tableau de 18 lignes (3 sujets × 6 moteurs), toutes « à tirer » au premier passage, et un total en dollars.

- [ ] **Step 7 : le tableau dans /studio3d**

Dans `frontend/studio3d/fal.js` :

```js
/* Le banc — la matrice cesse de citer des fiches produit. Un moteur sans
   ligne affiche « jamais mesuré », et c'est une information : ne pas
   remplir la case par la note du fournisseur. */
export async function brancherBanc() {
  const zone = document.querySelector("#falBanc");
  const d = await (await fetch("/api/assets3d/engines")).json();
  zone.innerHTML = `<table class="banc"><thead><tr>
      <th>moteur</th><th>sujets</th><th>tris médians</th>
      <th>poids médian</th><th>$ médians</th><th>étanche</th></tr></thead>
    <tbody>${d.engines.map((e) => {
      const b = e.banc;
      return `<tr><td>${e.label}</td>${b
        ? `<td>${b.sujets}</td><td>${b.tris_median.toLocaleString("fr")}</td>
           <td>${(b.bytes_median / 1048576).toFixed(1)} Mo</td>
           <td>${b.usd_median.toFixed(3)}</td>
           <td>${b.ferme_sur}/${b.mesures}</td>`
        : `<td colspan="5" class="jamais">jamais mesuré chez nous</td>`}</tr>`;
    }).join("")}</tbody></table>`;
}
```
`index.html` : `<div id="falBanc"></div>` sous le panneau « Job courant ».

- [ ] **Step 8 : commit**

```
git add backend/app/services/asset3d_banc.py backend/app/api/routes.py backend/tests/test_asset3d_banc.py scripts/banc_moteurs3d.py frontend/studio3d/fal.js frontend/studio3d/index.html
git commit -m 'moteurs 3d : D2 - banc de reference par sujet type, la matrice cite ses chiffres' -m 'Un point par couple (sujet type, moteur) : triangles, sommets, poids, poids de texture, étanchéité, couverture des trois silhouettes, coût estimé. Tout vient de la fiche de maillage et du manifeste écrits par le flux normal — rien n est saisi. Le service ne génère RIEN : le script imprime le plan de tir et son coût, le tir se fait par l interface. Un moteur jamais mesuré affiche jamais mesuré, au lieu de recopier la note du fournisseur.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 9 : D3 — une matière du Forge sur le modèle, par partie

**Files:**
- Modify: `backend/app/services/mesh_edit.py` (`habiller`)
- Modify: `backend/app/api/routes.py` (`POST /etabli/habiller`, la sixième route d'écriture de l'Établi)
- Modify: `frontend/etabli/etabli.js`, `frontend/etabli/index.html` (un sélecteur de matière dans le panneau « parties »)
- Test: `backend/tests/test_mesh_habiller.py`

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""D3 — habiller un maillage d'une matière du Forge, par partie. Le banc relit
le GLB ÉCRIT : matériaux, textures, bufferViews, et l'octet des images.
Run : python tests/test_mesh_habiller.py"""
import io, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.services import gltf_builder, mesh_edit                 # noqa: E402
from app.services import mesh_convert, print3d                   # noqa: E402


def _png(couleur, taille=16) -> bytes:
    b = io.BytesIO(); Image.new("RGB", (taille, taille), couleur).save(b, "PNG")
    return b.getvalue()


def _cube_uv() -> bytes:
    """Un cube de gltf_builder : il porte TEXCOORD_0 (c'est un aperçu de
    matière), donc il est habillable."""
    return gltf_builder.build_glb({}, None, "cube", "nu")


def _noeud_mesh(data: bytes) -> int:
    """L'index du premier nœud qui porte de la géométrie. Épingler 0 marcherait
    aujourd'hui et casserait le jour où gltf_builder ajouterait un nœud de
    scène devant — on le CHERCHE."""
    doc, _ = mesh_edit.lire_glb(data)
    return next(i for i, nd in enumerate(doc["nodes"]) if "mesh" in nd)


def _sans_uv() -> bytes:
    """Un maillage sans UV : la sortie STL d'un cube, réimportée. Un STL n'a
    ni UV ni matériau — c'est le cas de refus, et il est réel."""
    tris = print3d.lire_glb_triangles(_cube_uv())
    return mesh_convert.tris_vers_glb(tris, "brut")


def test_habiller_pose_une_matiere_et_le_glb_se_relit():
    maps = {"basecolor": _png((200, 40, 40)), "normal": _png((128, 128, 255)),
            "orm": _png((255, 128, 0))}
    depart = _cube_uv()
    n0 = _noeud_mesh(depart)
    sortie = mesh_edit.habiller(depart, noeuds=[n0], maps=maps,
                                nom="cuir_rouge")
    doc, binc = mesh_edit.lire_glb(sortie)
    mats = [m for m in doc["materials"] if m.get("name") == "cuir_rouge"]
    assert len(mats) == 1, [m.get("name") for m in doc["materials"]]
    m = mats[0]
    pbr = m["pbrMetallicRoughness"]
    assert pbr["baseColorTexture"]["index"] is not None, m
    assert pbr["metallicRoughnessTexture"]["index"] == m["occlusionTexture"]["index"]
    assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0, pbr
    assert m["normalTexture"]["index"] is not None, m
    # la primitive du nœud visé pointe bien la NOUVELLE matière
    im = doc["nodes"][n0]["mesh"]
    cible = doc["materials"].index(m)
    assert all(p.get("material") == cible
               for p in doc["meshes"][im]["primitives"]), doc["meshes"][im]
    # et les octets sont VRAIMENT dans le tampon
    vues = doc["bufferViews"]
    for img in doc["images"]:
        v = vues[img["bufferView"]]
        oct_ = binc[v["byteOffset"]:v["byteOffset"] + v["byteLength"]]
        assert Image.open(io.BytesIO(oct_)).size == (16, 16), img
    assert doc["buffers"][0]["byteLength"] == len(binc), "byteLength désaccordé"


def test_un_maillage_sans_uv_refuse_avant_d_ecrire_quoi_que_ce_soit():
    try:
        brut = _sans_uv()
        mesh_edit.habiller(brut, noeuds=[_noeud_mesh(brut)],
                           maps={"basecolor": _png((0, 0, 0))}, nom="x")
        raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "TEXCOORD_0" in str(e) and "UV" in str(e), e


def test_habiller_ne_touche_pas_les_noeuds_non_vises():
    """Deux nœuds : seul le premier est habillé, le second garde sa matière."""
    origine = gltf_builder.build_glb(
        {"basecolor": _png((10, 10, 10))}, None, "cube", "origine")
    n0 = _noeud_mesh(origine)
    doc, binc = mesh_edit.lire_glb(origine)
    doc["nodes"].append({"mesh": doc["nodes"][n0]["mesh"], "name": "jumeau"})
    doc["scenes"][0]["nodes"] = [n0, len(doc["nodes"]) - 1]
    # le jumeau a SA propre primitive, sinon les deux nœuds partagent le mesh
    mv = doc["nodes"][n0]["mesh"]
    doc["meshes"].append({"name": "jumeau",
                          "primitives": [dict(doc["meshes"][mv]["primitives"][0])]})
    mj = len(doc["meshes"]) - 1
    doc["nodes"][-1]["mesh"] = mj
    depart = mesh_edit.ecrire_glb(doc, binc)
    avant = mesh_edit.lire_glb(depart)[0]["meshes"][mj]["primitives"][0].get("material")

    sortie = mesh_edit.habiller(depart, noeuds=[n0],
                                maps={"basecolor": _png((250, 250, 0))},
                                nom="or")
    d2, _ = mesh_edit.lire_glb(sortie)
    cible = [i for i, m in enumerate(d2["materials"]) if m.get("name") == "or"][0]
    assert d2["meshes"][mv]["primitives"][0]["material"] == cible
    assert d2["meshes"][mj]["primitives"][0].get("material") == avant, \
        "le jumeau ne devait pas changer de matière"


def test_les_noeuds_enfants_suivent_leur_parent():
    cube = _cube_uv()
    n0 = _noeud_mesh(cube)
    doc, binc = mesh_edit.lire_glb(cube)
    doc["nodes"].append({"mesh": doc["nodes"][n0]["mesh"], "name": "enfant"})
    doc["nodes"][n0]["children"] = [len(doc["nodes"]) - 1]
    depart = mesh_edit.ecrire_glb(doc, binc)
    sortie = mesh_edit.habiller(depart, noeuds=[n0],
                                maps={"basecolor": _png((0, 200, 200))},
                                nom="turquoise")
    d2, _ = mesh_edit.lire_glb(sortie)
    cible = [i for i, m in enumerate(d2["materials"])
             if m.get("name") == "turquoise"][0]
    im = d2["nodes"][-1]["mesh"]
    assert all(p.get("material") == cible for p in d2["meshes"][im]["primitives"])


def test_une_liste_de_noeuds_vide_ou_hors_bornes_refuse():
    for mauvais in ([], [9999], ["a"]):
        try:
            mesh_edit.habiller(_cube_uv(), noeuds=mauvais,
                               maps={"basecolor": _png((1, 1, 1))}, nom="x")
            raise AssertionError(f"aurait dû refuser {mauvais!r}")
        except ValueError:
            pass
    try:
        mesh_edit.habiller(_cube_uv(), noeuds=[_noeud_mesh(_cube_uv())],
                           maps={}, nom="x")
        raise AssertionError("aurait dû refuser des maps vides")
    except ValueError as e:
        assert "aucune carte" in str(e).lower(), e


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mesh_habiller)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer** — `python tests/test_mesh_habiller.py` → cinq `✗` avec `AttributeError: module 'app.services.mesh_edit' has no attribute 'habiller'`.

- [ ] **Step 3 : la chirurgie**

Dans `backend/app/services/mesh_edit.py`, après `assise` (ligne 845 et suivantes) et avant `ecrire_version` :

```python
# ── habiller : une matière du Forge sur des parties du maillage (R10e D3) ────
#
# Le Forge produit huit cartes seamless en PIL, avec leurs conventions et leur
# note de rendu ; l'Établi connaît les parties d'un maillage. Ce qui manquait
# était le geste qui joint les deux. Il est ici, et il ne fabrique AUCUNE
# image : il pose des octets déjà écrits.
#
# LES NIVEAUX SONT CUITS DANS LES CARTES (material_store.RENDER_NOTE) : les
# facteurs glTF restent donc à 1.0. Poser en plus la valeur du curseur
# reviendrait à la compter deux fois — rugosité = roughnessFactor x texture.G.

_MIMES = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"))
CARTES_HABILLAGE = ("basecolor", "normal", "orm", "emissive")


def _mime_image(octets: bytes) -> str:
    for magie, mime in _MIMES:
        if octets.startswith(magie):
            return mime
    raise ValueError("carte illisible : ni PNG ni JPEG")


def _meshes_des_noeuds(doc: dict, noeuds) -> set[int]:
    """Les meshes visés : ceux des nœuds donnés ET de leurs descendants.

    Le choix des descendants n'est pas gratuit : dans l'Établi, une « partie »
    est souvent un nœud de groupe dont les enfants portent la géométrie
    (exports Blender, Meshy). Ne prendre que le nœud nommé habillerait le vide
    en silence et l'utilisateur croirait à un bug de la matière.
    """
    nodes = _l(doc, "nodes")
    if not isinstance(noeuds, (list, tuple)) or not noeuds:
        raise ValueError("habiller : `noeuds` doit être une liste non vide "
                         "d'index de nœud glTF")
    vus: set[int] = set()
    meshes: set[int] = set()
    pile = []
    for n in noeuds:
        if not isinstance(n, int) or isinstance(n, bool) or not (0 <= n < len(nodes)):
            raise ValueError(f"habiller : nœud « {n} » hors bornes "
                             f"(0..{len(nodes) - 1})")
        pile.append(n)
    while pile:
        i = pile.pop()
        if i in vus:
            continue
        vus.add(i)
        nd = nodes[i]
        if isinstance(nd.get("mesh"), int):
            meshes.add(nd["mesh"])
        pile.extend(c for c in _l(nd, "children") if isinstance(c, int))
    if not meshes:
        raise ValueError("habiller : aucun de ces nœuds ne porte de géométrie")
    return meshes


def habiller(data: bytes, *, noeuds, maps: dict, nom: str = "matiere") -> bytes:
    """Pose une matière (octets PNG ou JPEG) sur les parties désignées.

    `maps` : {"basecolor": octets, "normal": …, "orm": …, "emissive": …} —
    au moins une. L'ORM sert à la fois de metallicRoughnessTexture et
    d'occlusionTexture, comme la spec glTF le prévoit et comme le Forge
    l'écrit déjà.

    REFUS PARLANT SANS UV : une primitive sans TEXCOORD_0 n'a nulle part où
    poser une texture. glTF la rendrait avec l'UV (0,0) partout — un aplat de
    la couleur du coin haut gauche, qui a tout l'air d'un bug. On refuse et
    l'on dit quoi faire (déplier les UV : Meshy uv-unwrap, 1 crédit).
    """
    cartes = {k: v for k, v in (maps or {}).items()
              if k in CARTES_HABILLAGE and v}
    if not cartes:
        raise ValueError("habiller : aucune carte fournie — il en faut au "
                         f"moins une parmi {', '.join(CARTES_HABILLAGE)}")
    doc, binc = lire_glb(data)
    meshes = _meshes_des_noeuds(doc, noeuds)

    sans_uv = []
    for im in sorted(meshes):
        for k, prim in enumerate(_l(doc["meshes"][im], "primitives")):
            if "TEXCOORD_0" not in (prim.get("attributes") or {}):
                sans_uv.append(f"{doc['meshes'][im].get('name') or im}[{k}]")
    if sans_uv:
        raise ValueError(
            "habiller : ces parties n'ont pas d'UV (attribut TEXCOORD_0) — "
            f"{', '.join(sans_uv[:6])}"
            + (" …" if len(sans_uv) > 6 else "")
            + ". Une texture n'a nulle part où se poser : déplie les UV "
              "d'abord (Meshy uv-unwrap, 1 crédit), ou pose une couleur "
              "unie plutôt qu'une matière.")

    tampon = bytearray(binc)
    doc.setdefault("bufferViews", [])
    doc.setdefault("images", [])
    doc.setdefault("samplers", [])
    doc.setdefault("textures", [])
    doc.setdefault("materials", [])

    def _texture(octets: bytes, etiquette: str) -> int:
        mime = _mime_image(bytes(octets))
        while len(tampon) % 4:
            tampon.append(0)
        off = len(tampon)
        tampon.extend(bytes(octets))
        doc["bufferViews"].append({"buffer": 0, "byteOffset": off,
                                   "byteLength": len(octets)})
        doc["images"].append({"bufferView": len(doc["bufferViews"]) - 1,
                              "mimeType": mime,
                              "name": f"{nom}_{etiquette}"})
        doc["samplers"].append({"magFilter": 9729, "minFilter": 9987,
                                "wrapS": 10497, "wrapT": 10497})
        doc["textures"].append({"sampler": len(doc["samplers"]) - 1,
                                "source": len(doc["images"]) - 1})
        return len(doc["textures"]) - 1

    pbr = {"baseColorFactor": [1.0, 1.0, 1.0, 1.0],
           "metallicFactor": 1.0, "roughnessFactor": 1.0}
    materiau = {"name": str(nom), "pbrMetallicRoughness": pbr}
    if "basecolor" in cartes:
        pbr["baseColorTexture"] = {"index": _texture(cartes["basecolor"], "basecolor")}
    if "orm" in cartes:
        t = _texture(cartes["orm"], "orm")
        pbr["metallicRoughnessTexture"] = {"index": t}
        materiau["occlusionTexture"] = {"index": t}
    if "normal" in cartes:
        materiau["normalTexture"] = {"index": _texture(cartes["normal"], "normal")}
    if "emissive" in cartes:
        materiau["emissiveTexture"] = {"index": _texture(cartes["emissive"],
                                                          "emissive")}
        materiau["emissiveFactor"] = [1.0, 1.0, 1.0]
    doc["materials"].append(materiau)
    cible = len(doc["materials"]) - 1

    for im in sorted(meshes):
        for prim in _l(doc["meshes"][im], "primitives"):
            prim["material"] = cible

    if not doc.get("buffers"):
        doc["buffers"] = [{"byteLength": len(tampon)}]
    else:
        doc["buffers"][0]["byteLength"] = len(tampon)
    return ecrire_glb(doc, bytes(tampon))
```

- [ ] **Step 4 : relancer** — `python tests/test_mesh_habiller.py` → `OK — 5 tests, 0 rouge(s) (mesh_habiller)`. Puis `python tests/test_etabli_socle.py` et `python tests/test_etabli_canevas.py` (ou `-m pytest` pour celui-ci, qui est hérité) : verts — `mesh_edit` n'a rien perdu.

- [ ] **Step 5 : la route** (la SIXIÈME route d'écriture de l'Établi — même porte)

Dans `routes.py`, après `@router.post("/etabli/couper")` :

```python
@router.post("/etabli/habiller")
async def etabli_habiller(body: dict):
    """Pose une matière du Forge sur des parties du maillage et écrit une
    version de plus. Body : `job`, `version`, `noeuds` (index de nœud glTF),
    `mid` (identifiant de matière), `resolution` (px, défaut 1024).

    La résolution est redescendue ICI et pas dans le Forge : une matière 4K
    posée sur trois parties ferait un GLB de 100 Mo que le viewport n'ouvre
    plus. 1024 est le défaut ; l'appelant peut demander plus.
    """
    from PIL import Image
    from app.services import material_store as MS
    from app.services import mesh_edit, pbr_service
    job, data, depuis = _etabli_glb_cible(body.get("job"), body.get("version"),
                                          "habillage")
    mid = str(body.get("mid") or "")
    if not MS.is_valid_mid(mid):
        raise HTTPException(400, "habiller : `mid` doit être l'identifiant "
                                 "d'une matière du Forge.")
    mat = MS.read_material(mid)
    if mat is None:
        raise HTTPException(404, f"matière {mid} introuvable.")
    res = MS.clean_res(body.get("resolution") or 1024)
    noeuds = body.get("noeuds")
    if not isinstance(noeuds, list) or not noeuds:
        raise HTTPException(400, "habiller : `noeuds` doit être une liste non "
                                 "vide d'index de nœud — on n'habille jamais "
                                 "tout le modèle par défaut.")

    def _cartes():
        ouvertes = {}
        for kind in mesh_edit.CARTES_HABILLAGE:
            p = MS.map_path(mid, kind)
            if p.is_file():
                im = Image.open(p)
                im.load()
                ouvertes[kind] = im
        if not ouvertes:
            return {}
        ouvertes = pbr_service.resize_maps(ouvertes, res)
        return {k: MS.png_bytes(v, k, 8) for k, v in ouvertes.items()}

    cartes = await asyncio.to_thread(_cartes)
    if not cartes:
        raise HTTPException(400, f"« {mat.get('name')} » n'a aucune des cartes "
                                 f"posables ({', '.join(mesh_edit.CARTES_HABILLAGE)}) : "
                                 "dérive-la d'abord dans le Material Forge.")
    try:
        sortie = await asyncio.to_thread(
            mesh_edit.habiller, data, noeuds=noeuds, maps=cartes,
            nom=MS.slug(mat.get("name"), fallback=mid))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _etabli_ecrire(job, sortie, "habiller",
                          {"depuis": depuis, "noeuds": list(noeuds),
                           "mid": mid, "matiere": mat.get("name"),
                           "resolution": res,
                           "note_rendu": MS.RENDER_NOTE})
```

- [ ] **Step 6 : le sélecteur de matière dans l'Établi**

`frontend/etabli/index.html`, dans `.parties-actions` (le bloc du panneau « parties », vers la ligne 2172 de `etabli.js` qui le rend) : ajouter un `<select id="matiereSel">` et un bouton `<button id="matiereGo">Habiller</button>`.

`frontend/etabli/etabli.js` — à côté des autres opérations (`ROUTES`, ligne 183) :

```js
ROUTES.habiller = "/api/etabli/habiller";

/* Habiller — la matière vient du Forge, la sélection vient du panneau parties.
   Le bouton reste GRIS tant qu'aucune partie n'est cochée : « habiller tout »
   par défaut est exactement le geste qu'on ne veut pas rendre facile. */
async function chargerMatieres() {
  const sel = document.querySelector("#matiereSel");
  if (!sel) return;
  const d = await jget("/api/materials");
  const liste = d.materials || d.items || [];
  sel.innerHTML = liste.length
    ? liste.map((m) => `<option value="${m.id}">${esc(m.name)}</option>`).join("")
    : `<option value="">aucune matière — passe par le Material Forge</option>`;
}

function brancherHabiller() {
  const bouton = document.querySelector("#matiereGo");
  if (!bouton) return;
  bouton.addEventListener("click", async () => {
    const { noeuds, source } = noeudsRetenus();
    if (!noeuds.length) {
      toast("Coche au moins une partie : on n'habille jamais tout par défaut.");
      return;
    }
    const mid = document.querySelector("#matiereSel").value;
    if (!mid) { toast("Aucune matière disponible."); return; }
    noterAttente("habiller", { noeuds, mid, source });
    const r = await jpost(ROUTES.habiller, {
      job: S.a.job, version: S.a.version, noeuds, mid, resolution: 1024,
    });
    toast(`Habillé — version ${r.version}`);
    await rechargerVersion(r);
  });
}
```
et appeler `chargerMatieres(); brancherHabiller();` là où les autres branchements se font (à côté de `brancherEtabli`). `noterAttente` et `rechargerVersion` sont les mécanismes existants des cinq autres opérations — aucun nouveau.

- [ ] **Step 7 : vérification à l'écran (utilisateur)** — ouvrir `/etabli`, charger un maillage texturé, cocher une partie dans le panneau « parties », choisir une matière, « Habiller » → la partie change de matière dans le viewport, une version de plus apparaît dans la chronologie, et la fiche porte `mid`, `matiere` et la note de rendu. Sur un maillage sans UV (import STL), le refus s'affiche avec « déplie les UV d'abord ».

- [ ] **Step 8 : commit**

```
git add backend/app/services/mesh_edit.py backend/app/api/routes.py backend/tests/test_mesh_habiller.py frontend/etabli/etabli.js frontend/etabli/index.html
git commit -m 'moteurs 3d : D3 - une matiere du Forge posee sur des parties du maillage' -m 'habiller() embarque les cartes (basecolor, normal, ORM, emissive) dans le tampon du GLB, crée UNE matière et la pointe depuis les primitives des nœuds visés et de leurs descendants — un nœud de groupe habillait le vide sans cela. Les facteurs restent à 1.0 : les niveaux sont cuits dans les cartes (RENDER_NOTE). Sans TEXCOORD_0, refus parlant qui dit quoi faire, avant toute écriture. Sixième route d écriture de l Établi, même porte que les cinq autres.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 10 : D4 — service GPU local optionnel, partagé

**La carte graphique est INCONNUE tant qu'on ne l'a pas lue.** R10e écrit « RTX 30 ou plus récent » ; le README de Hunyuan3D-2.1, relu le 03/09/2026, **ne nomme aucune génération de carte** — il donne des VRAM (10 Go forme, 21 Go texture, 29 Go les deux). Le seuil mesurable est donc la **VRAM**, pas le millésime. La première étape de cette tâche est une **mesure**.

- [ ] **Step 1 : mesurer la carte de CETTE machine (PowerShell)**

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-List
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

Relevé du 03/09/2026 sur la machine de l'utilisateur, à confirmer par l'implémenteur :

| Source | Sortie |
|---|---|
| `nvidia-smi` | `NVIDIA GeForce RTX 2080 Ti, 11264 MiB, 616.56` |
| `Win32_VideoController` | `Name = NVIDIA GeForce RTX 2080 Ti` · `AdapterRAM = 4293918720` · `DriverVersion = 32.0.16.1656` |

**Le piège, mesuré** : `AdapterRAM` est un `uint32` — il **plafonne à 4 294 967 295 octets (4 Gio)**. Lu seul, il ferait croire à une carte de 4 Go et refuserait Hunyuan3D **à tort** sur une carte de 11 Go. `nvidia-smi` d'abord ; `Win32` en repli, avec l'avertissement écrit dans la réponse.

**Table de décision** (VRAM mesurée → ce qu'on propose) :

| VRAM | Décision | Pourquoi |
|---|---|---|
| ≥ 29 Go | `hunyuan-2.1` forme **et** texture | README : « 29GB » pour les deux |
| ≥ 21 Go | `hunyuan-2.1` forme, texture possible | README : « 21GB » texture |
| ≥ 10 Go | **`hunyuan-2.1` forme seule**, texture par fal ou Meshy | README : « 10 GB VRAM » forme. **C'est le cas de cette machine (11 Go).** |
| ≥ 6 Go | `hunyuan-optimise` — variantes communautaires 3–6 Go, `--low_vram_mode` | R10e ; **non vérifié**, à mesurer au premier essai |
| < 6 Go ou inconnue | `fal` seul | Le service local ne servirait à rien |

- [ ] **Step 2 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""D4 — service GPU local optionnel (patron Voicebox). Rien ne sort : la
détection, la lecture de carte et l'appel HTTP sont stubbés. Le banc vérifie
la TABLE de décision et le repli, pas la présence d'un serveur.
Run : python tests/test_local3d_service.py"""
import asyncio, base64, io, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import asset3d_service as A3                   # noqa: E402
from app.services import gltf_builder, local3d_service as L      # noqa: E402


def test_la_table_de_decision_suit_la_vram_pas_le_millesime():
    assert L.decision(30000)["moteur"] == "hunyuan-2.1"
    assert L.decision(30000)["texture"] is True
    assert L.decision(22000)["texture"] is True
    d = L.decision(11264)                       # la carte mesurée le 03/09/2026
    assert d["moteur"] == "hunyuan-2.1" and d["texture"] is False, d
    assert "10" in d["pourquoi"], d
    assert L.decision(8000)["moteur"] == "hunyuan-optimise"
    assert L.decision(8000)["verifie"] is False, "les variantes 3-6 Go ne sont pas vérifiées"
    assert L.decision(2000)["moteur"] == "fal"
    assert L.decision(None)["moteur"] == "fal"


def test_la_carte_prefere_nvidia_smi_et_avertit_sur_le_plafond_win32():
    L._carte_cache["t"] = 0.0
    L._lire_nvidia_smi = lambda timeout=4.0: ("NVIDIA GeForce RTX 2080 Ti", 11264)
    c = L.carte()
    assert c["vram_mo"] == 11264 and c["source"] == "nvidia-smi", c
    assert c["avertissement"] is None, c
    L._carte_cache["t"] = 0.0
    L._lire_nvidia_smi = lambda timeout=4.0: None
    L._lire_win32 = lambda timeout=6.0: ("NVIDIA GeForce RTX 2080 Ti", 4293918720 // (1 << 20))
    c = L.carte()
    assert c["source"] == "win32", c
    assert "uint32" in c["avertissement"] and "4 Gio" in c["avertissement"], c
    L._carte_cache["t"] = 0.0
    L._lire_win32 = lambda timeout=6.0: None
    c = L.carte()
    assert c["vram_mo"] is None and c["source"] is None, c


def test_le_moteur_local_est_au_registre_et_gratuit():
    from app.services.pricing import estimate
    assert "hunyuan-local" in A3.ENGINES, sorted(A3.ENGINES)
    e = A3.ENGINES["hunyuan-local"]
    assert e["local"] is True and e["formats"] == ["glb"], e
    assert e["multiview"] is False and e["max_images"] == 1, e
    d = estimate({"kind": "asset3d", "engine": "hunyuan-local", "textures": True})
    assert d["total_usd"] == 0.0, d


def test_sans_serveur_le_moteur_local_refuse_en_disant_quoi_faire():
    L._reach_cache["t"] = 0.0
    L.joignable = lambda timeout=2.0, ttl=5.0: False
    try:
        asyncio.run(L.run_engine("hunyuan-local", {"image_url": "https://x/y.png"}))
        raise AssertionError("aurait dû refuser")
    except RuntimeError as e:
        assert "8081" in str(e) and "Hunyuan" in str(e), e


def test_avec_serveur_le_glb_revient_et_se_relit():
    envois = []

    async def _faux_post(url, charge, timeout):
        envois.append((url, sorted(charge)))
        return gltf_builder.build_glb({}, None, "cube", "local")

    async def _faux_image(url):
        return b"\x89PNG\r\n\x1a\n" + b"0" * 8

    import time as _t
    L.joignable = lambda timeout=2.0, ttl=5.0: True
    # la carte de la machine qui lance le banc ne doit RIEN décider ici : on
    # remplit le cache plutôt que de remplacer carte(), que le test suivant lit
    L._carte_cache.update(t=_t.monotonic(),
                          v={"nom": "banc", "vram_mo": 11264,
                             "source": "banc", "avertissement": None})
    L._poster_generate = _faux_post
    L._octets_de_l_image = _faux_image
    r = asyncio.run(L.run_engine("hunyuan-local",
                                 {"image_url": "https://x/y.png",
                                  "texture": False, "face_limit": 20000,
                                  "seed": 7}))
    assert r["mesh_url"].startswith("data:model/gltf-binary;base64,"), r["mesh_url"][:60]
    brut = base64.b64decode(r["mesh_url"].split(",", 1)[1])
    from app.services import print3d
    assert len(print3d.lire_glb_triangles(brut)) == 12
    assert envois and envois[0][0].endswith("/generate"), envois
    assert "image" in envois[0][1] and "face_count" in envois[0][1], envois


def test_les_disponibilites_disent_toujours_l_etat_des_deux_voies():
    L.joignable = lambda timeout=2.0, ttl=5.0: False
    d = L.disponible()
    assert {x["id"] for x in d} == {"fal", "local3d"}, d
    assert [x for x in d if x["id"] == "local3d"][0]["ready"] is False, d


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (local3d)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 3 : lancer** — `python tests/test_local3d_service.py` → `ModuleNotFoundError: No module named 'app.services.local3d_service'`.

- [ ] **Step 4 : le service**

Créer `backend/app/services/local3d_service.py` :

```python
# -*- coding: utf-8 -*-
"""Service GPU local optionnel — R10e D4, patron `voice_providers` (Voicebox).

Le Python EMBARQUÉ de l'application n'a ni numpy ni torch, et n'en aura pas :
Hunyuan3D 2.1 demande Python 3.10 et PyTorch 2.5.1+cu124 (README relu le
03/09/2026). Le service vit donc À CÔTÉ, comme Voicebox : un processus séparé
que l'utilisateur lance ou non, détecté par un `GET /health`, avec repli fal
silencieux quand il n'est pas là. Aucune dépendance nouvelle ici : httpx est
déjà au bagage.

Ce que le README de Hunyuan3D-2.1 dit, relu le 03/09/2026 :
  - VRAM : « 10 GB » pour la forme, « 21GB » pour la texture, « 29GB » pour
    les deux ; `--low_vram_mode` existe. **Aucune génération de carte n'y est
    nommée** — le « RTX 30+ » de R10e n'en vient pas. Le seuil mesurable est
    la VRAM, et c'est celui qu'on applique.
  - `api_server.py` : `POST /generate` (rend le GLB en FileResponse),
    `POST /send` + `GET /status/{uid}` (asynchrone), `GET /health`, hôte
    `0.0.0.0`, **port 8081**.
  - `GenerationRequest` : `image` (base64), `remove_background=True`,
    `texture=False`, `seed=1234`, `octree_resolution=256`,
    `num_inference_steps=5`, `guidance_scale=5.0`, `num_chunks=8000`,
    `face_count=40000`.

Ce même serveur est le futur hôte de CLAP (R4 D3) et de CLIP (R9 D1) : c'est
pourquoi il s'appelle « service GPU local » et non « service Hunyuan ».
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import time

DEFAULT_LOCAL3D_URL = "http://127.0.0.1:8081"

# README Hunyuan3D-2.1, relu le 03/09/2026 — en Mo, comme nvidia-smi
VRAM_FORME = 10 * 1024
VRAM_TEXTURE = 21 * 1024
VRAM_LES_DEUX = 29 * 1024
VRAM_OPTIMISE = 6 * 1024


def url() -> str:
    from app.config import settings
    return (getattr(settings, "LOCAL3D_URL", "") or "").strip().rstrip("/") \
        or DEFAULT_LOCAL3D_URL


_reach_cache = {"t": 0.0, "ok": False}


def joignable(timeout: float = 2.0, ttl: float = 5.0) -> bool:
    """« Le service tourne » (GET /health). Mise en cache `ttl` secondes :
    `/assets3d/engines` est appelé à chaque ouverture d'écran — pas un ping
    par moteur listé."""
    import httpx
    now = time.monotonic()
    if ttl > 0 and now - _reach_cache["t"] < ttl:
        return _reach_cache["ok"]
    try:
        r = httpx.get(url() + "/health", timeout=timeout)
        ok = r.status_code == 200
    except Exception:
        ok = False
    _reach_cache.update(t=now, ok=ok)
    return ok


# ── la carte, MESURÉE ────────────────────────────────────────────────────────

def _lire_nvidia_smi(timeout: float = 4.0):
    """(nom, VRAM en Mo) ou None. La source la plus juste sur une carte
    NVIDIA : `memory.total` est en MiB et ne plafonne pas."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    ligne = (r.stdout or "").strip().splitlines()
    if not ligne:
        return None
    parts = [p.strip() for p in ligne[0].split(",")]
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return parts[0], int(parts[1])


def _lire_win32(timeout: float = 6.0):
    """(nom, VRAM en Mo) ou None, par WMI. ATTENTION : `AdapterRAM` est un
    uint32 — il plafonne à 4 Gio. Mesuré le 03/09/2026 : 4 293 918 720 pour
    une carte de 11 264 Mio. C'est un repli, pas une source."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object -First 1 Name,AdapterRAM | ConvertTo-Json"],
            capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    if r.returncode != 0 or not (r.stdout or "").strip():
        return None
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None
    if isinstance(d, list):
        d = d[0] if d else {}
    ram = d.get("AdapterRAM")
    if not isinstance(ram, int):
        return None
    return str(d.get("Name") or "?"), int(ram) // (1 << 20)


_carte_cache = {"t": 0.0, "v": None}


def carte(ttl: float = 60.0) -> dict:
    """{nom, vram_mo, source, avertissement}. nvidia-smi d'abord, WMI ensuite,
    rien du tout en dernier — et le dire vaut mieux que deviner."""
    now = time.monotonic()
    if ttl > 0 and _carte_cache["v"] is not None \
            and now - _carte_cache["t"] < ttl:
        return _carte_cache["v"]
    lu = _lire_nvidia_smi()
    if lu:
        out = {"nom": lu[0], "vram_mo": lu[1], "source": "nvidia-smi",
               "avertissement": None}
    else:
        lu = _lire_win32()
        if lu:
            out = {"nom": lu[0], "vram_mo": lu[1], "source": "win32",
                   "avertissement":
                       "Win32_VideoController.AdapterRAM est un uint32 : il "
                       "plafonne à 4 Gio. Une carte plus grosse sera "
                       "sous-évaluée ici — installe les outils NVIDIA "
                       "(nvidia-smi) pour une mesure juste."}
        else:
            out = {"nom": None, "vram_mo": None, "source": None,
                   "avertissement":
                       "Ni nvidia-smi ni WMI n'ont répondu : la carte est "
                       "inconnue, le service local n'est pas proposé."}
    _carte_cache.update(t=now, v=out)
    return out


def decision(vram_mo) -> dict:
    """Ce qu'on PROPOSE pour cette VRAM. Aucune génération de carte n'entre
    dans ce calcul : le README de Hunyuan3D ne parle qu'en gigaoctets."""
    v = int(vram_mo) if isinstance(vram_mo, (int, float)) and vram_mo else 0
    if v >= VRAM_LES_DEUX:
        return {"moteur": "hunyuan-2.1", "texture": True, "low_vram": False,
                "verifie": True,
                "pourquoi": f"{v} Mo ≥ 29 Go : forme ET texture tiennent "
                            "(README Hunyuan3D-2.1, 03/09/2026)."}
    if v >= VRAM_TEXTURE:
        return {"moteur": "hunyuan-2.1", "texture": True, "low_vram": False,
                "verifie": True,
                "pourquoi": f"{v} Mo ≥ 21 Go : la texture tient, les deux "
                            "passes ensemble non."}
    if v >= VRAM_FORME:
        return {"moteur": "hunyuan-2.1", "texture": False, "low_vram": False,
                "verifie": True,
                "pourquoi": f"{v} Mo ≥ 10 Go : la FORME tient. La texture "
                            "demande 21 Go — texture par fal ou Meshy."}
    if v >= VRAM_OPTIMISE:
        return {"moteur": "hunyuan-optimise", "texture": False,
                "low_vram": True, "verifie": False,
                "pourquoi": f"{v} Mo : sous les 10 Go du README. Les variantes "
                            "communautaires annoncent 3–6 Go avec "
                            "--low_vram_mode — NON VÉRIFIÉ : mesure au "
                            "premier essai avant d'y compter."}
    return {"moteur": "fal", "texture": True, "low_vram": False,
            "verifie": True,
            "pourquoi": (f"{v} Mo" if v else "carte inconnue")
                        + " : trop peu pour Hunyuan3D. fal reste la voie."}


def disponible() -> list[dict]:
    """Pour l'UI : les deux voies et leur état, toujours les deux."""
    from app.config import settings
    c = carte()
    d = decision(c["vram_mo"])
    return [
        {"id": "fal", "label": "fal.ai (cloud, clé API)",
         "ready": bool(settings.FAL_KEY)},
        {"id": "local3d", "label": "Service GPU local (Hunyuan3D 2.1)",
         "ready": joignable(), "url": url(), "carte": c, "decision": d},
    ]


# ── l'appel ──────────────────────────────────────────────────────────────────

async def _octets_de_l_image(image_url: str) -> bytes:
    """Les octets de l'image d'entrée. DETTE ASSUMÉE : quand le flux vient de
    `tirer_moteur`, l'image a déjà été téléversée chez fal et l'on va la
    RECHERCHER là-bas — un aller-retour réseau pour un moteur qui se dit
    local. Un `data:` URI est accepté sans réseau, ce que fera un appelant
    direct ; brancher le chemin local du job demanderait de faire descendre le
    job jusqu'ici, et ce n'est pas de cette tâche."""
    import httpx
    if image_url.startswith("data:"):
        return base64.b64decode(image_url.split(",", 1)[1])
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.get(image_url)
        r.raise_for_status()
        return r.content


async def _poster_generate(cible: str, charge: dict, timeout: float) -> bytes:
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(cible, json=charge)
        r.raise_for_status()
        return r.content


async def run_engine(engine: str, args: dict) -> dict:
    """La couture appelée par `asset3d_service._run_engine` quand le moteur est
    marqué `local`. Rend la MÊME forme que `parse_engine_result` — le reste du
    flux (téléchargement, manifeste, fiche) ne sait pas d'où vient le GLB."""
    if not joignable():
        raise RuntimeError(
            "Le service GPU local ne répond pas sur " + url() + " (Hunyuan3D "
            "2.1, port 8081 par défaut). Lance-le à côté de l'application, ou "
            "choisis un moteur fal. Réglage : LOCAL3D_URL.")
    c = carte()
    d = decision(c["vram_mo"])
    if d["moteur"] == "fal":
        raise RuntimeError(
            "Le service répond, mais cette carte ne suffit pas : "
            + d["pourquoi"])
    image = await _octets_de_l_image(str(args.get("image_url") or ""))
    charge = {
        "image": base64.b64encode(image).decode("ascii"),
        "remove_background": True,
        "texture": bool(args.get("texture")) and d["texture"],
        "seed": int(args.get("seed") or 1234),
        "octree_resolution": 256,
        "num_inference_steps": 5,
        "guidance_scale": 5.0,
        "num_chunks": 8000,
        "face_count": int(args.get("face_limit") or 40000),
    }
    glb = await _poster_generate(url() + "/generate", charge, timeout=900.0)
    if not glb.startswith(b"glTF"):
        raise RuntimeError("le service local n'a pas rendu un GLB "
                           f"({len(glb)} octets, entête {glb[:8]!r})")
    return {"mesh_url": "data:model/gltf-binary;base64,"
                        + base64.b64encode(glb).decode("ascii"),
            "format_urls": {}, "texture_urls": {}, "preview_url": None}
```

- [ ] **Step 5 : le moteur au registre, et la couture**

1. Dans `asset3d_service.py`, `ENGINES` gagne, après `"triposr"` :

```python
    # R10e D4 — moteur LOCAL. `endpoint` porte le préfixe « local: » : ce
    # n'est pas une URL fal, et le filtre de /assets3d/engines (qui coupe
    # toute clé commençant par « endpoint ») l'écarte déjà de la réponse.
    "hunyuan-local": {
        "endpoint": "local:hunyuan3d-2.1",
        "formats": ["glb"],
        "label": "Hunyuan3D 2.1 (local)",
        "multiview": False, "max_images": 1,
        "texture_modes": ["no"],
        "draft": True, "detailed": False, "pbr": False, "tpose": False,
        "quality_passthrough": False,
        "face_limit": True, "quad": False, "seed": True,
        "local": True,
        "note": "gratuit et hors ligne, si le service GPU tourne à côté. "
                "Forme seulement au-dessus de 10 Go de VRAM ; la texture "
                "demande 21 Go (README Hunyuan3D-2.1, 03/09/2026).",
    },
```

2. `build_engine_args` gagne une branche, avant le `else` final :

```python
    if engine == "hunyuan-local":
        # le service local ne lit qu'UNE image, et ne connaît ni palier de
        # texture ni quad : ce que l'adaptateur n'envoie pas, le drapeau le dit
        return {"image_url": primary, "texture": tex_on,
                "face_limit": opts.get("face_limit"), "seed": opts.get("seed")}
```

3. `_run_engine` gagne trois lignes en tête (la couture reste monkeypatchable — les bancs la remplacent en entier) :

```python
async def _run_engine(engine, args, endpoint=None):
    # R10e D4 — un moteur marqué `local` ne passe pas par fal. Le test est
    # AVANT `import fal_client` : sans clé fal, le moteur local doit marcher.
    if ENGINES.get(engine, {}).get("local"):
        from app.services import local3d_service
        return await local3d_service.run_engine(engine, args)
    import fal_client
```
puis le corps historique de la fonction (`n = max(...)`, `ep = endpoint or resolve_endpoint(...)`, le `try/except` autour de `subscribe_async`, le `return parse_engine_result(...)`) reste **inchangé, à la ligne près** : les trois lignes ci-dessus se posent au-dessus, rien d'autre ne bouge.

4. Dans `pricing.py`, kind `asset3d`, le dictionnaire `rates` gagne :

```python
                 # R10e D4 : le service GPU local est gratuit — c'est
                 # l'argument, et un tarif > 0 le ferait mentir
                 "hunyuan-local": 0.0,
```

5. Dans `test_meshy_service.py:469`, le pin EXACT — c'est lui qui force à passer par ici :

```python
    assert set(ENGINES) == {"tripo", "tripo-h3.1", "hunyuan", "trellis",
                            "rodin", "triposr", "hunyuan-local"}
```
et le libellé du `ok(...)` juste après devient `"ENGINES fal — 6 moteurs + 1 local, meshy ne s'y invite pas"`.

- [ ] **Step 6 : la route d'état et le repli parlant**

Dans `routes.py`, à côté de `GET /assets3d/engines` :

```python
@router.get("/assets3d/local")
async def get_asset3d_local():
    """L'état du service GPU local : joignable ou non, la carte MESURÉE, et
    ce que sa VRAM permet. Miroir de ce que fait Voicebox pour les voix."""
    from app.services import local3d_service
    return {"providers": await asyncio.to_thread(local3d_service.disponible),
            "url": local3d_service.url()}
```
et, dans `GET /assets3d/engines`, la ligne `"available": dispo` devient :

```python
        dispo_moteur = (local3d_service.joignable() if e.get("local") else dispo)
        out.append({**{k: v for k, v in e.items()
                       if not k.startswith("endpoint")},
                    "id": eid, "available": dispo_moteur,
                    "usd_texture": devis["total_usd"],
                    "usd_brouillon": brouillon["total_usd"]})
```
avec `from app.services import local3d_service` en tête de la fonction. Un moteur local sans service reste **listé et grisé**, comme un moteur fal sans clé : c'est la règle de l'écran, pas une exception.

Dans `frontend/studio3d/fal.js`, le repli :

```js
/* Le service local n'est pas une promesse : s'il ne tourne pas, on le dit
   avec l'adresse et la mesure de la carte, au lieu de griser sans raison. */
export async function noterServiceLocal() {
  const d = await (await fetch("/api/assets3d/local")).json();
  const l = d.providers.find((p) => p.id === "local3d");
  const el = document.querySelector("#falLocal");
  if (!l.ready) {
    el.innerHTML = `<b>Service GPU local absent</b> (${d.url}).
      Carte détectée : ${l.carte.nom || "inconnue"}
      ${l.carte.vram_mo ? `· ${l.carte.vram_mo} Mo (${l.carte.source})` : ""}.
      ${l.decision.pourquoi}
      ${l.carte.avertissement ? `<i>${l.carte.avertissement}</i>` : ""}`;
    return;
  }
  el.innerHTML = `<b>Service GPU local prêt</b> — ${l.decision.moteur},
    texture ${l.decision.texture ? "oui" : "non"}. ${l.decision.pourquoi}`;
}
```
`index.html` : `<div id="falLocal"></div>` en pied de la section « Atelier fal ».

- [ ] **Step 7 : relancer**

```
python tests/test_local3d_service.py
python tests/test_meshy_service.py
python tests/test_asset3d_service.py
```
Attendu : `OK — 6 tests, 0 rouge(s) (local3d)` ; le banc Meshy vert avec son pin à sept moteurs ; `asset3d_service` vert (le nouveau moteur n'est appelé par aucun test existant).

- [ ] **Step 8 : commit**

```
git add backend/app/services/local3d_service.py backend/app/services/asset3d_service.py backend/app/services/pricing.py backend/app/api/routes.py backend/tests/test_local3d_service.py backend/tests/test_meshy_service.py frontend/studio3d/fal.js frontend/studio3d/index.html
git commit -m 'moteurs 3d : D4 - service GPU local optionnel, decide par la VRAM mesuree' -m 'Patron Voicebox : un processus à côté, détecté par GET /health sur 8081, repli fal silencieux. Le README de Hunyuan3D-2.1 ne nomme AUCUNE génération de carte — le seuil est la VRAM (10 Go forme, 21 Go texture, 29 Go les deux), et la table de décision le suit. La carte est lue par nvidia-smi d abord : Win32_VideoController.AdapterRAM est un uint32 qui plafonne à 4 Gio et sous-évaluerait une 11 Go, mesuré le 03/09/2026. Le moteur hunyuan-local est au registre, gratuit, grisé quand le service dort.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 11 : D5 — photos réelles, depuis le téléphone ou un fichier

**Files:**
- Modify: `backend/app/services/asset3d_views.py` (`enregistrer_photos`, `detourer_toutes`)
- Modify: `backend/app/api/routes.py` (`POST /assets/3d/views/photos`)
- Modify: `frontend/studio3d/fal.js`, `frontend/studio3d/index.html`
- Test: `backend/tests/test_asset3d_photos.py`

**Où s'arrête cette tâche.** R12 (application compagnon) a répondu **B — le téléphone travaille seul**, et l'appairage par QR + jeton n'existe pas encore. D5 livre donc **le côté application** : une route qui accepte 1 à 4 photos, les range dans la Bibliothèque, les détoure et en fait un jeu de vues P5. Le compagnon s'y branchera par la même route quand il existera — la garde CSRF laisse passer une requête sans `Origin` (mesuré, R12), donc une application native y arrivera sans changement ici.

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""D5 — photos réelles vers un jeu de vues. Le banc relit les fichiers rangés
dans la Bibliothèque et les shots écrits ; le détourage est le local (gratuit).
Run : python tests/test_asset3d_photos.py"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import asset3d_views as V                      # noqa: E402


async def _faux_upload(p):
    return f"https://fal.test/{pathlib.Path(p).name}"


A3._upload = _faux_upload


def _photo(couleur=(180, 60, 30), taille=(1200, 900)) -> bytes:
    im = Image.new("RGB", taille, (245, 245, 244))       # fond clair d'atelier
    im.paste(Image.new("RGB", (400, 500), couleur), (400, 200))
    b = io.BytesIO(); im.save(b, "JPEG", quality=88)
    return b.getvalue()


def test_les_photos_entrent_dans_la_bibliotheque_avec_un_nom_sur():
    noms = V.enregistrer_photos([("IMG_0042.JPEG", _photo()),
                                 ("../../evasion.png", _photo((20, 200, 60)))])
    assert len(noms) == 2, noms
    for n in noms:
        p = settings.images_path / n
        assert p.is_file() and n.startswith("photo_") and n.endswith(".png"), n
        assert ".." not in n and "/" not in n and "\\" not in n, n
        assert Image.open(p).format == "PNG", n


def test_une_photo_trop_grande_est_ramenee_a_la_borne():
    noms = V.enregistrer_photos([("grande.jpg", _photo(taille=(6000, 4000)))])
    im = Image.open(settings.images_path / noms[0])
    assert max(im.size) == V.PHOTO_MAX_PX, im.size
    assert im.size[0] > im.size[1], "le rapport doit être gardé"


def test_zero_ou_cinq_photos_refusent():
    for n in (0, 5):
        try:
            V.enregistrer_photos([("a.jpg", _photo())] * n)
            raise AssertionError(f"aurait dû refuser {n}")
        except ValueError as e:
            assert "1 à 4" in str(e), e


def test_les_photos_deviennent_un_jeu_de_vues_detourees_sans_generation():
    noms = V.enregistrer_photos([("a.jpg", _photo()),
                                 ("b.jpg", _photo((30, 60, 180))),
                                 ("c.jpg", _photo((30, 180, 60)))])
    r = asyncio.run(V.preparer_depuis_images(
        "ph_job", noms, {"engine": "tripo", "source": "photos",
                         "subject": "une théière"}))
    assert r["vues"] == 3, r
    d = asyncio.run(V.detourer_toutes("ph_job", via="local"))
    assert d["detourees"] == 3 and d["usd"] == 0.0, d
    dossier = settings.outputs_path / "assets3d" / "ph_job"
    for i in range(3):
        im = Image.open(dossier / f"shot_{i}.png")
        assert im.mode == "RGBA", (i, im.mode)
        assert im.getchannel("A").getextrema()[0] == 0, i
    vj = json.loads((dossier / "views.json").read_text("utf-8"))
    assert vj["source"] == "photos" and vj["etat"] == "en_attente", vj
    assert all(v["detoure"] == "local" for v in vj["vues"]), vj


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_photos)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
```

- [ ] **Step 2 : lancer** — `python tests/test_asset3d_photos.py` → quatre `✗` avec `AttributeError: module 'app.services.asset3d_views' has no attribute 'enregistrer_photos'`.

- [ ] **Step 3 : le service**

À la fin de `backend/app/services/asset3d_views.py` :

```python
PHOTO_MAX_PX = 2048          # au-delà, la vue coûte du temps d'upload pour rien
PHOTO_MAX = 4                # le quatuor du moteur multi-vues


def enregistrer_photos(fichiers) -> list[str]:
    """Range 1 à 4 photos dans la Bibliothèque et rend leurs noms.

    Le nom d'origine n'est JAMAIS repris : une photo vient d'un téléphone ou
    d'un partage, et son nom est une entrée non maîtrisée (`../../…`, un
    accent, un nom déjà pris). On génère `photo_<hex>.png` et l'on réencode en
    PNG — ce qui, au passage, jette les données EXIF (position GPS comprise).
    """
    import io
    from uuid import uuid4
    from PIL import Image, ImageOps
    from app.config import settings
    entrees = list(fichiers or [])
    if not (1 <= len(entrees) <= PHOTO_MAX):
        raise ValueError(f"il faut de 1 à 4 photos ; {len(entrees)} donnée(s)")
    settings.images_path.mkdir(parents=True, exist_ok=True)
    noms = []
    for _nom_origine, octets in entrees:
        im = Image.open(io.BytesIO(bytes(octets)))
        im = ImageOps.exif_transpose(im)          # le téléphone tourne, pas nous
        im = im.convert("RGB")
        if max(im.size) > PHOTO_MAX_PX:
            im.thumbnail((PHOTO_MAX_PX, PHOTO_MAX_PX), Image.LANCZOS)
        nom = f"photo_{uuid4().hex[:10]}.png"
        im.save(settings.images_path / nom, "PNG")
        noms.append(nom)
    return noms


async def detourer_toutes(job, *, via: str = "local", on_step=None) -> dict:
    """Détoure toutes les vues d'un jeu. Le local est gratuit et hors ligne :
    c'est le défaut, et sur une photo au fond propre il suffit."""
    info = lire(job)
    total = 0.0
    faites = 0
    for v in list(info["vues"]):
        if not v.get("file"):
            continue
        r = await detourer(job, v["index"], via=via, on_step=on_step)
        total += float(r["usd"])
        faites += 1
    return {"detourees": faites, "via": via, "usd": round(total, 4)}
```

- [ ] **Step 4 : relancer** — `python tests/test_asset3d_photos.py` → `OK — 4 tests, 0 rouge(s) (asset3d_photos)`.

- [ ] **Step 5 : la route**

Dans `routes.py`, à côté de `POST /assets/3d/views` :

```python
@router.post("/assets/3d/views/photos")
async def post_asset3d_views_photos(background_tasks: BackgroundTasks,
                                    fichiers: list[UploadFile] = File(...),
                                    engine: str = Form("tripo"),
                                    subject: str = Form(""),
                                    detourer: bool = Form(True)):
    """1 à 4 photos réelles -> Bibliothèque -> détourage -> jeu de vues P5.

    Aucune génération d'image : les vues SONT les photos. C'est le point de
    R10e D5, et c'est aussi ce qui rend cette route utilisable depuis une
    application native — la garde CSRF laisse passer une requête sans
    `Origin` (mesuré, R12), donc le compagnon s'y branchera sans changement.
    """
    from uuid import uuid4 as _u
    from app.services import asset3d_views
    from app.services import library_index as LI
    lus = [(f.filename or "photo", await f.read()) for f in fichiers]
    try:
        noms = await asyncio.to_thread(asset3d_views.enregistrer_photos, lus)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"photo illisible : {e}")
    await LI.noter(noms, "assets3d")
    job = _u().hex[:12]

    async def _travail(on_step):
        r = await asset3d_views.preparer_depuis_images(
            job, noms, {"engine": engine, "subject": subject,
                        "source": "photos"}, on_step)
        if detourer:
            await asset3d_views.detourer_toutes(job, via="local",
                                                on_step=on_step)
        return r

    return await _lancer_job_asset3d(
        background_tasks, job=job, titre=f"Photos · {subject or job}",
        etape="Photos", travail=_travail,
        cost_meta=lambda r: {"kind": "asset3d_views", "views": 0,
                             "note": f"{len(noms)} photo(s) réelle(s) — "
                                     "aucune génération d'image"})
```

Vérifier que `UploadFile`, `File` et `Form` sont importés en tête de `routes.py` (ils le sont pour les imports d'images ; sinon les ajouter à l'import `fastapi`) :
```
python -c "import re,pathlib,sys; sys.stdout.reconfigure(encoding='utf-8'); s=pathlib.Path('backend/app/api/routes.py').read_text('utf-8'); print([l for l in s.splitlines()[:60] if 'fastapi' in l])"
```

- [ ] **Step 6 : le bouton dans /studio3d**

Dans `frontend/studio3d/fal.js` :

```js
/* Photos — 1 à 4 clichés d'un objet tourné. `capture="environment"` fait
   ouvrir l'appareil arrière quand la page est vue depuis un téléphone du
   réseau ; sur PC c'est un sélecteur de fichiers ordinaire. */
export function brancherPhotos() {
  const zone = document.querySelector("#falPhotos");
  zone.innerHTML = `
    <input id="phFiles" type="file" accept="image/*" multiple capture="environment">
    <label class="fld"><span>Sujet</span><input id="phSujet" type="text"></label>
    <label class="fld"><span>Moteur</span><select id="phMoteur"></select></label>
    <button id="phGo">Vues depuis les photos</button>`;
  fetch("/api/assets3d/engines").then((r) => r.json()).then((d) => {
    document.querySelector("#phMoteur").innerHTML = d.engines
      .filter((e) => e.multiview)
      .map((e) => `<option value="${e.id}">${e.label}</option>`).join("");
  });
  document.querySelector("#phGo").addEventListener("click", async () => {
    const f = document.querySelector("#phFiles").files;
    if (!f.length || f.length > 4) { toast("De 1 à 4 photos."); return; }
    const fd = new FormData();
    for (const x of f) fd.append("fichiers", x);
    fd.append("engine", document.querySelector("#phMoteur").value);
    fd.append("subject", document.querySelector("#phSujet").value);
    fd.append("detourer", "true");
    const r = await fetch("/api/assets/3d/views/photos", { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    toast(r.ok ? `Vues en préparation (job ${String(j.source_job).slice(0, 8)})`
               : j.detail || "échec");
  });
}
```
`index.html` : `<div id="falPhotos"></div>` sous `#falViews`.

- [ ] **Step 7 : vérification à l'écran (utilisateur)** — dans `/studio3d`, « Atelier fal », choisir 4 photos d'un objet tourné à 90° prises sur fond clair uni → la file affiche « Photos · … » **sans coût d'image**, les quatre vues apparaissent détourées dans le panneau « Vues d'abord », « Tirer » produit le maillage.

- [ ] **Step 8 : commit**

```
git add backend/app/services/asset3d_views.py backend/app/api/routes.py backend/tests/test_asset3d_photos.py frontend/studio3d/fal.js frontend/studio3d/index.html
git commit -m 'moteurs 3d : D5 - des photos reelles deviennent les quatre vues' -m 'De 1 à 4 clichés entrent dans la Bibliothèque sous un nom généré (le nom d origine d une photo est une entrée non maîtrisée) et réencodés en PNG, ce qui jette l EXIF et sa position GPS ; l orientation du téléphone est redressée. Détourage local gratuit, puis jeu de vues P5 : aucune génération d image. La garde CSRF laissant passer une requête sans Origin, le compagnon de R12 se branchera sur cette route sans changement.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

- **E1 — Génération locale sans service optionnel.** Mesuré le 03/09/2026 : le Python embarqué est en 3.13.15 avec `numpy False` et `torch False`, et Hunyuan3D 2.1 exige Python 3.10 + PyTorch 2.5.1+cu124 (README relu le 03/09/2026). Un moteur 3D dans le processus de l'application n'est pas une question de volonté : c'est impossible sans changer de runtime. La D4 livre la seule forme tenable — un processus à côté, détecté, avec repli.
- **E2 — API Tripo directe.** fal sert déjà Tripo v2.5 et H3.1 ; le rig Tripo (auto-rig + `rig-check` + 100 mouvements) demanderait une clé Tripo séparée, un second compte à facturer et un second client à maintenir, pour un service que Meshy rend déjà par le proxy en place (P1). À rouvrir seulement si le rig Meshy se révèle insuffisant sur un sujet réel — pas avant.

---

## Campagne de mutations

### Task 12 : `backend/tests/mutations_moteurs3d.py`

**Files:**
- Create: `backend/tests/mutations_moteurs3d.py`

**Ce que la campagne prouve.** Un banc vert ne prouve pas qu'il MESURE quelque chose. La campagne casse une ligne à la fois dans les sources livrées, relance le banc visé, et exige qu'il rougisse. Une mutation « VERTE » est une assertion qui manque — c'est ainsi qu'on a trouvé, sur la plaque du slicer, la ligne morte du pivot et le mutant faible du libellé. Ce n'est **pas un test** : `pytest` ne le collecte pas (son nom ne commence pas par `test_`), `run-tests.ps1` ne le liste pas, il se lance à la main.

- [ ] **Step 1 : écrire le fichier**

```python
# -*- coding: utf-8 -*-
"""Banc de mutations des moteurs image -> 3D (plan 2026-09-03) : casser ->
rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas, run-tests.ps1 ne le liste pas. À la
main, depuis backend/ :

    python tests/mutations_moteurs3d.py            # toutes
    python tests/mutations_moteurs3d.py 3 17       # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion),
donc il ne se lance pas pendant qu'un autre banc lit ces fichiers.

DIFFÉRENCE AVEC mutations_plaque_slicer.py : les bancs de ce plan sont des
SCRIPTS AUTONOMES (`python tests/test_x.py`), pas des fichiers pytest. On lit
donc les lignes `✗ <nom>` de leur sortie, et l'on refuse de conclure quand
NI « OK — » NI « ROUGE — » n'apparaît : sans cette garde, un import cassé par
la mutation passerait pour « aucun rouge », donc pour une mutation VERTE, et
l'on croirait avoir trouvé un trou d'assertion là où rien n'a tourné.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

# (fichier, ancien, nouveau, banc, tests attendus rouges)
M = [
    # ── mesh_lod.py ──────────────────────────────────────────────────────────
    ("backend/app/services/mesh_lod.py",
     '    for i, nd in enumerate(doc.get("nodes") or []):\n'
     '        if "mesh" in nd:\n'
     '            nd["name"] = (nd.get("name") or f"node_{i}").split("_LOD")[0] + suffixe\n',
     "",
     "test_mesh_lod.py", ["la_chaine_ecrit_quatre_glb_nommes_pour_unity"]),
    ("backend/app/services/mesh_lod.py",
     '        m["name"] = (m.get("name") or f"mesh_{i}").split("_LOD")[0] + suffixe',
     '        m["name"] = (m.get("name") or f"mesh_{i}").split("_LOD")[0]',
     "test_mesh_lod.py", ["la_chaine_ecrit_quatre_glb_nommes_pour_unity"]),
    ("backend/app/services/mesh_lod.py",
     "        if out and v >= out[-1]:",
     "        if False:",
     "test_mesh_lod.py", ["un_budget_plus_lourd_que_la_source_est_refuse"]),
    ("backend/app/services/mesh_lod.py",
     "    if out[0] >= tris_source:",
     "    if False:",
     "test_mesh_lod.py", ["un_budget_plus_lourd_que_la_source_est_refuse"]),
    ("backend/app/services/mesh_lod.py",
     "        i = min(int(bins) - 1, int((nz / norme + 1.0) * 0.5 * int(bins)))",
     "        i = 0",
     "test_mesh_lod.py", ["la_signature_de_normales_distingue_un_cube_d_une_sphere"]),
    ("backend/app/services/mesh_lod.py",
     "    return round(0.5 * sum(abs(x - y) for x, y in zip(a, b)), 4)",
     "    return round(sum(abs(x - y) for x, y in zip(a, b)), 4)",
     "test_mesh_lod.py", ["la_perte_est_mesuree_contre_le_LOD0"]),
    ("backend/app/services/mesh_lod.py",
     "    if dossier.is_dir():\n        shutil.rmtree(dossier)\n    dossier.mkdir(parents=True)",
     "    dossier.mkdir(parents=True, exist_ok=True)",
     "test_mesh_lod.py", ["une_chaine_neuve_efface_les_niveaux_de_la_precedente"]),
    ("backend/app/services/mesh_lod.py",
     '    mesh_report.silhouettes(p, dossier / f"sil_lod{niveau}", px=SIL_PX)\n',
     "",
     "test_mesh_lod.py", ["la_perte_est_mesuree_contre_le_LOD0"]),
    ("backend/app/services/mesh_lod.py",
     '        z.writestr("LISEZMOI.txt", _lisezmoi(info))\n',
     "",
     "test_mesh_lod.py", ["l_archive_porte_les_glb_le_json_et_le_lisezmoi"]),
    # ── mesh_textures.py ─────────────────────────────────────────────────────
    ("backend/app/services/mesh_textures.py",
     '    if not any(m["canaux"] for m in inv["materiaux"]):',
     "    if False:",
     "test_mesh_textures.py", ["un_glb_sans_texture_est_refuse_avant_l_archive"]),
    ("backend/app/services/mesh_textures.py",
     "    naming = MS.clean_naming(naming)\n    res = MS.clean_res(resolution)",
     "    res = MS.clean_res(resolution)",
     "test_mesh_textures.py", ["la_convention_inconnue_retombe_sur_standard"]),
    ("backend/app/services/mesh_textures.py",
     "            if naming in MS.UNITY_NAMINGS:",
     "            if False:",
     "test_mesh_textures.py", ["l_archive_unity_urp_porte_les_noms_et_le_maskmap"]),
    ("backend/app/services/mesh_textures.py",
     "            maps = pbr_service.resize_maps(maps, res)\n",
     "",
     "test_mesh_textures.py", ["l_archive_unity_urp_porte_les_noms_et_le_maskmap",
                               "la_cuisson_locale_fabrique_ce_qui_manque_et_le_dit"]),
    ("backend/app/services/mesh_textures.py",
     '            L.append(f"  CUITES LOCALEMENT : {\', \'.join(m[\'cuits\'])}. Dérivées "',
     '            L.append(f"  cartes ajoutees : {\', \'.join(m[\'cuits\'])}. "',
     "test_mesh_textures.py", ["la_cuisson_locale_fabrique_ce_qui_manque_et_le_dit"]),
    # ── mesh_convert.py ──────────────────────────────────────────────────────
    ("backend/app/services/mesh_convert.py",
     "    if fmt in MESHY_EXPORT:",
     "    if False:",
     "test_mesh_convert.py", ["un_format_inconnu_ou_proprietaire_refuse"]),
    ("backend/app/services/mesh_convert.py",
     'LOCAL_EXPORT = ("obj", "stl", "3mf", "gltf")',
     'LOCAL_EXPORT = ("obj", "stl", "gltf")',
     "test_mesh_convert.py", ["les_capacites_disent_ce_qui_est_local"]),
    ("backend/app/services/mesh_convert.py",
     '                       "count": len(tris) * 3, "type": "VEC3",',
     '                       "count": len(tris), "type": "VEC3",',
     "test_mesh_convert.py", ["l_import_stl_et_obj_redevient_un_glb_relisible"]),
    # Celle-ci est ATTENDUE VERTE au premier passage : aucune assertion ne
    # regarde le sens du v. Quand elle sort VERTE, c'est une assertion qui
    # manque — l'ajouter au banc (voir « Ce qui reste incertain »), pas
    # supprimer la mutation.
    ("backend/app/services/mesh_convert.py",
     '            L.append(f"vt {t[0]:.6f} {1.0 - t[1]:.6f}")',
     '            L.append(f"vt {t[0]:.6f} {t[1]:.6f}")',
     "test_mesh_convert.py", ["l_obj_sort_avec_son_mtl_ses_uv_et_sa_texture"]),
    # ── asset3d_views.py ─────────────────────────────────────────────────────
    ("backend/app/services/asset3d_views.py",
     '    vues = [{"index": 0, "role": "source", "file": "shot_0.png", "url": url,',
     '    vues = [{"index": 0, "role": "vue", "file": "shot_0.png", "url": url,',
     "test_asset3d_views.py", ["preparer_genere_les_vues_et_ne_tire_PAS",
                               "la_source_ne_se_rejoue_pas"]),
    ("backend/app/services/asset3d_views.py",
     '    if vues[i]["role"] == "source":',
     "    if False:",
     "test_asset3d_views.py", ["la_source_ne_se_rejoue_pas"]),
    ("backend/app/services/asset3d_views.py",
     '    if info["etat"] == "tire":\n        raise ValueError("ce jeu de vues a déjà été tiré',
     '    if False:\n        raise ValueError("ce jeu de vues a déjà été tiré',
     "test_asset3d_views.py", ["on_ne_tire_pas_deux_fois_le_meme_jeu_de_vues"]),
    ("backend/app/services/asset3d_views.py",
     "            rgba.putalpha(masque)\n",
     "",
     "test_asset3d_views.py", ["le_detourage_local_est_gratuit_et_ecrit_un_alpha"]),
    ("backend/app/services/asset3d_views.py",
     "    if not (1 <= len(noms) <= MAX_VUES):",
     "    if False:",
     "test_asset3d_bible_vues.py", ["une_liste_vide_ou_trop_longue_est_refusee"]),
    ("backend/app/services/asset3d_views.py",
     "    if not (1 <= len(entrees) <= PHOTO_MAX):",
     "    if False:",
     "test_asset3d_photos.py", ["zero_ou_cinq_photos_refusent"]),
    ("backend/app/services/asset3d_views.py",
     "        if max(im.size) > PHOTO_MAX_PX:\n"
     "            im.thumbnail((PHOTO_MAX_PX, PHOTO_MAX_PX), Image.LANCZOS)\n",
     "",
     "test_asset3d_photos.py", ["une_photo_trop_grande_est_ramenee_a_la_borne"]),
    ("backend/app/services/asset3d_views.py",
     '        nom = f"photo_{uuid4().hex[:10]}.png"',
     "        nom = Path(str(_nom_origine)).name",
     "test_asset3d_photos.py", ["les_photos_entrent_dans_la_bibliotheque_avec_un_nom_sur"]),
    # ── board_service.py ─────────────────────────────────────────────────────
    ("backend/app/services/board_service.py",
     "    if len(cols) != len(cles):",
     "    if False:",
     "test_asset3d_bible_vues.py", ["une_image_qui_n_est_pas_une_planche_refuse"]),
    ("backend/app/services/board_service.py",
     "            if fin_vide - x >= mini or fin_vide >= w:",
     "            if True:",
     "test_asset3d_bible_vues.py", ["la_planche_se_decoupe_en_quatre_colonnes"]),
    ("backend/app/services/board_service.py",
     "    if not all(par_cle.get(k) for k in voulus):\n        return None\n",
     "",
     "test_asset3d_bible_vues.py", ["la_recette_rend_les_fichiers_quand_elle_les_a_persistes"]),
    # ── mesh_edit.py (habiller) ──────────────────────────────────────────────
    ("backend/app/services/mesh_edit.py",
     "    if sans_uv:\n        raise ValueError(",
     "    if False:\n        raise ValueError(",
     "test_mesh_habiller.py", ["un_maillage_sans_uv_refuse"]),
    ("backend/app/services/mesh_edit.py",
     '        pile.extend(c for c in _l(nd, "children") if isinstance(c, int))\n',
     "",
     "test_mesh_habiller.py", ["les_noeuds_enfants_suivent_leur_parent"]),
    ("backend/app/services/mesh_edit.py",
     '        doc["buffers"][0]["byteLength"] = len(tampon)',
     "        pass",
     "test_mesh_habiller.py", ["habiller_pose_une_matiere_et_le_glb_se_relit"]),
    ("backend/app/services/mesh_edit.py",
     '            prim["material"] = cible',
     "            pass",
     "test_mesh_habiller.py", ["habiller_pose_une_matiere_et_le_glb_se_relit",
                               "habiller_ne_touche_pas_les_noeuds_non_vises"]),
    # ── local3d_service.py ───────────────────────────────────────────────────
    ("backend/app/services/local3d_service.py",
     "    if v >= VRAM_TEXTURE:",
     "    if v >= VRAM_FORME:",
     "test_local3d_service.py", ["la_table_de_decision_suit_la_vram"]),
    ("backend/app/services/local3d_service.py",
     "    lu = _lire_nvidia_smi()\n    if lu:",
     "    lu = _lire_win32()\n    if lu:",
     "test_local3d_service.py", ["la_carte_prefere_nvidia_smi"]),
    ("backend/app/services/local3d_service.py",
     "    if not joignable():",
     "    if False:",
     "test_local3d_service.py", ["sans_serveur_le_moteur_local_refuse"]),
    # ── asset3d_banc.py ──────────────────────────────────────────────────────
    ("backend/app/services/asset3d_banc.py",
     '    banc["lignes"] = [l for l in banc["lignes"]\n'
     '                      if not (l.get("sujet") == sujet\n'
     '                              and l.get("moteur") == str(moteur))]\n',
     "",
     "test_asset3d_banc.py", ["remesurer_le_meme_couple_remplace_la_ligne"]),
    ("backend/app/services/asset3d_banc.py",
     "    if sujet not in SUJETS:",
     "    if False:",
     "test_asset3d_banc.py", ["un_job_sans_fiche_refuse_au_lieu_de_deviner"]),
]


def rouges(banc: str):
    """Les tests rouges d'un banc AUTONOME — et si rien n'a tourné, on le dit.

    Les bancs de ce plan impriment `  ✓ nom` / `  ✗ nom — Type: message` puis
    une ligne de bilan `OK — n tests, 0 rouge(s) (x)` ou `ROUGE — …`. L'absence
    de cette ligne signifie que le module n'a même pas pu s'importer : c'est un
    troisième état, ni vert ni rouge.
    """
    r = subprocess.run([PY, f"tests/{banc}"], capture_output=True,
                       cwd=R / "backend", timeout=1800)
    txt = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    bilan = re.search(r"^(OK|ROUGE) — \d+ tests", txt, re.M)
    erreur = bilan is None or r.returncode not in (0, 1)
    return set(re.findall(r"✗ (\w+)", txt)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF et
        # l'on réécrit avec la fin de ligne du fichier ; la remise se fait à
        # l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:70])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(import)"
            print(sortie[-1200:], file=sys.stderr)
        elif attendus:
            verdict = ("ROUGE" if not manquants
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        else:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        bilan.append((i, rel.rsplit("/", 1)[-1], verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip().splitlines()[0][:52]
        print(f"[{i:2d}] {verdict:15s} {banc:28s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne entière**

```
python tests/mutations_moteurs3d.py
```

Attendu : une ligne par mutation (38 au total, index 0 à 37). **Chaque ligne doit dire `ROUGE`**, sauf la mutation 17 (`vt` sans retournement), attendue `VERTE` au premier passage — c'est une assertion qui manque, pas une mutation à supprimer. Aucune ligne ne doit dire `ERREUR(import)` : ce verdict signale que la mutation a cassé la syntaxe ou un import, donc que rien n'a été mesuré. La dernière ligne est un JSON récapitulatif.

Durée : les bancs LOD et textures appellent le vrai gltfpack et rastérisent des silhouettes — compter 15 à 30 minutes pour les 38 mutations. Pour itérer, viser des index : `python tests/mutations_moteurs3d.py 17 18 19`.

- [ ] **Step 3 : fermer la VERTE**

La mutation 17 remplace `vt {u} {1 - v}` par `vt {u} {v}`. Aucune assertion du banc ne regarde le sens du `v`, donc l'OBJ sortirait avec ses textures retournées verticalement sans que rien ne rougisse. Ajouter à `backend/tests/test_mesh_convert.py`, dans `test_l_obj_sort_avec_son_mtl_ses_uv_et_sa_texture`, juste après le compte des `vt` :

```python
        # le v d'OBJ est compté du BAS, celui de glTF du HAUT : la conversion
        # doit retourner. Le cube de gltf_builder a des UV dans [0,1] avec au
        # moins un v strictement au-dessus de 0,5 ET un strictement en dessous ;
        # on compare donc à la lecture directe du GLB, pas à une constante.
        from app.services import mesh_edit
        from app.services.print3d import _accessor
        doc, binc = mesh_edit.lire_glb(
            (settings.outputs_path / "assets3d" / "cv_obj" / "model.glb").read_bytes())
        prim = doc["meshes"][0]["primitives"][0]
        v_gltf = [t[1] for t in _accessor(doc, binc, prim["attributes"]["TEXCOORD_0"])]
        v_obj = [float(l.split()[2]) for l in obj.splitlines() if l.startswith("vt ")]
        assert len(v_obj) == len(v_gltf), (len(v_obj), len(v_gltf))
        for a, b in zip(v_obj, v_gltf):
            assert abs(a - (1.0 - b)) < 1e-5, (a, b)
```
(et `from app.config import settings` en tête du banc s'il n'y est pas déjà).

Rejouer la mutation seule :
```
python tests/mutations_moteurs3d.py 17
python tests/test_mesh_convert.py
```
Attendu : `[17] ROUGE …` puis `OK — 7 tests, 0 rouge(s) (mesh_convert)`.

- [ ] **Step 4 : la passe complète des bancs, un processus par fichier**

```
python tests/test_moteurs3d_socle.py
python tests/test_asset3d_rig.py
python tests/test_mesh_lod.py
python tests/test_mesh_textures.py
python tests/test_mesh_convert.py
python tests/test_asset3d_views.py
python tests/test_asset3d_bible_vues.py
python tests/test_asset3d_banc.py
python tests/test_mesh_habiller.py
python tests/test_local3d_service.py
python tests/test_asset3d_photos.py
python tests/test_asset3d_service.py
python tests/test_meshy_service.py
python tests/test_mesh_optimize.py
python tests/test_hygiene_imports.py
```
Attendu : onze lignes `OK — n tests, 0 rouge(s) (…)` pour les bancs de ce plan, et les quatre bancs hérités verts. `test_hygiene_imports.py` est le garde-fou des imports de module (leçon seedance du 28/08) : il doit passer sur les sept modules neufs (`asset3d_rig`, `mesh_lod`, `mesh_textures`, `mesh_convert`, `asset3d_views`, `asset3d_banc`, `local3d_service`).

- [ ] **Step 5 : commit**

```
git add backend/tests/mutations_moteurs3d.py backend/tests/test_mesh_convert.py
git commit -m 'moteurs 3d : campagne de mutations, et la verte qu elle a trouvee' -m 'Trente-huit mutations sur les huit modules livrés, chacune nommant le banc et les tests qu elle doit faire rougir. Le lanceur lit les lignes des bancs AUTONOMES et refuse de conclure quand ni OK ni ROUGE n apparaît : sans cette garde, un import cassé par la mutation passerait pour une assertion manquante. La mutation du sens de v en OBJ est sortie VERTE : le banc de conversion gagne l assertion qui manquait, comparée à la lecture directe du GLB.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Ce qui reste incertain

Ces points ne sont pas des trous du plan : ce sont les endroits où le plan **dit ne pas savoir**, avec l'étape qui tranchera.

| Point | Ce qu'on ne sait pas | Où ça se tranche |
|---|---|---|
| `<model-viewer>` et `autoplay` | La version vendue dans `frontend/dist/assets/model-viewer.min.js` honore-t-elle `autoplay` et `animation-name` ? De mémoire, non vérifié. | Task 2, Step 8 — à l'écran. Repli déjà écrit : `mv.play()` sur `availableAnimations`. |
| Nom réel de l'encodeur PNG du Forge | `material_store` a une fonction privée `(img, kind, bits)` ; son nom exact n'est pas relevé dans ce plan. | Task 4, Step 1 — une commande qui l'imprime. |
| Signature de `_attendre_meshy` | `asset3d_service._attendre_meshy` existe (ligne 792) ; prend-elle `depart`/`fin` ? | Task 5, note d'intégration — `inspect.signature`, puis adapter l'APPEL, pas le helper. |
| Sortie de `gltfpack -o .gltf` | Combien de fichiers écrit-il vraiment (`.gltf` + `.bin` + images séparées ?) selon le contenu. | Task 5, Step 2 — le banc zippe tout le dossier et assère la présence du `.bin`. |
| Variantes Hunyuan3D « 3–6 Go » | R10e les annonce ; le README officiel ne les documente pas. `decision()` les rend avec `verifie: False`. | Task 10 — au premier essai réel sur une carte de cette classe. |
| Le sens du `v` en OBJ | Aucune assertion ne le gardait ; la mutation 17 le prouve. | Task 12, Step 3 — l'assertion est écrite, il reste à la poser. |
| Image d'entrée du moteur local | Elle transite par fal même pour `hunyuan-local` (dette assumée, écrite dans `_octets_de_l_image`). | Hors de ce plan : demanderait de faire descendre le job jusqu'à la couture `_run_engine`. |
| Étanchéité des budgets LOD | `BUDGETS` porte des choix de départ, pas des mesures. | Task 8 — le banc de référence les corrigera avec des chiffres du terrain. |

