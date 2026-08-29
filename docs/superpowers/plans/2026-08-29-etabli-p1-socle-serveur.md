# L'Établi P1 — socle serveur : chirurgie GLB et chronologie des étapes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer, sans une ligne d'interface, le module qui opère sur les GLB
(extraire une partie, transformer un nœud, réparer l'assise, inventorier un
squelette) et le service qui fond les trois registres 3D du dépôt en une seule
chronologie.

**Architecture :** deux services stdlib purs — `mesh_edit.py` (chirurgie de
document glTF) et `mesh_sources.py` (agrégation de registres) — plus les routes
de lecture et d'écriture. Le navigateur n'écrit jamais un GLB : ces fonctions
sont les seules plumes du chantier. Chaque écriture passe par
`asset3d_service.next_version()` et `mesh_report.write_report()`, donc rien
n'est jamais écrasé.

**Tech Stack :** Python stdlib (`json`, `struct`), FastAPI, pytest. Lecteurs
existants réutilisés : `print3d.lire_glb_triangles`, `print3d.bbox`,
`mesh_report`, `gltf_builder.build_glb` (fabrique les GLB des bancs).

---

## Plan 1 sur 3

| Plan | Contenu | Livre à lui seul |
|---|---|---|
| **P1 — celui-ci** | `mesh_edit`, `mesh_sources`, `rig_inventory`, routes | des routes utilisables et testées, sans UI |
| P2+P3 | canevas three.js, chronologie, comparaison A/B, Parties | `2026-08-29-etabli-p2-p3-canevas-parties.md` |
| P4+P5 | Rig affiché, export par moteur | `2026-08-29-etabli-p4-p5-rig-export.md` |

Spec de référence : `docs/superpowers/specs/2026-08-29-etabli-inspecteur-3d-design.md`.
Les cinq capacités écartées sont analysées dans
`docs/superpowers/specs/2026-08-29-etabli-phases-ulterieures.md` — **ne pas les
implémenter ici**.

## Note de fiabilité — le code de ce plan a été exercé

L'algorithme d'extraction, la matrice de réparation et l'invariance du tampon
binaire ont été **exécutés contre les lecteurs réels du dépôt** au moment de
l'écriture du plan. Les valeurs attendues affichées dans les étapes ne sont pas
des estimations :

```
DEPART : 2 noeuds, 14 triangles, 4360 octets
EXTRAIT noeud 0 (cube) : noeuds=1 meshes=1 materials=1 images=0
                         accessors=5 views=5 bin=1224
                         triangles = 12 | bbox = ((-1,1), (-1,1), (-1,1))
EXTRAIT noeud 1 (stage): triangles = 2 | images = 1
transformer : bin identique = True | bbox = ((-1,1), (2,4), (-1,1))
echelle x2  : ((-2,2), (-2,2), (-2,2))
axe Z       : ((-1,1), (-1,1), (2,4))
recentre    : ((-1,1), (-1,1), (-1,1))
```

Un écart à ces nombres est un vrai échec, pas un seuil à ajuster.

## Structure de fichiers

| Fichier | Responsabilité |
|---|---|
| **Créer** `backend/app/services/mesh_edit.py` | lecture/écriture GLB, `extraire`, `transformer`, `reparer`, `rig_inventory`, `ecrire_version` |
| **Créer** `backend/app/services/mesh_sources.py` | fond `MeshyTaskRecord`, les registres `report.json` et `model.opt.glb` en une chronologie |
| **Créer** `backend/tests/test_etabli_socle.py` | le banc de tout P1 |
| **Modifier** `backend/app/api/routes.py` | les six routes `/api/etabli/*` de lecture et d'écriture, plus `adopter` |

`mesh_edit` ne dépend d'aucun réglage (`settings`) : c'est de la manipulation
d'octets pure, et c'est ce qui la rend testable sans environnement. `print3d` et
`gltf_builder` ont la même propriété — vérifié : ils s'importent sans
`pydantic_settings`.

---

## Task 1 : lire et réécrire un GLB sans le déformer

**Files:**
- Create: `backend/app/services/mesh_edit.py`
- Create: `backend/tests/test_etabli_socle.py`

Pourquoi un lecteur de plus : `mesh_report._gltf_json` ne rend que le JSON,
`print3d._chunks` sert son propre décodeur de triangles. La chirurgie a besoin
des **deux moitiés** — document et tampon — et de savoir les recoller.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_etabli_socle.py` :

```python
"""L'Établi P1 — chirurgie GLB et chronologie des étapes
(plan 2026-08-29-etabli-p1-socle-serveur).

Le banc ne SORT jamais : les GLB sont fabriqués par gltf_builder et relus par
print3d, les deux lecteurs déjà éprouvés du dépôt.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_socle.py
"""
import json
import os
import pathlib
import struct
import sys
import tempfile
import zlib

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _png1x1() -> bytes:
    """PNG RGBA 1x1 valide — déclenche le quad de sol de gltf_builder, donc
    un GLB à DEUX nœuds, deux matériaux et une texture."""
    def ch(tag: bytes, d: bytes) -> bytes:
        c = tag + d
        return (struct.pack(">I", len(d)) + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
            + ch(b"IEND", b""))


def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _cube_et_sol() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc",
                                  stage_png=_png1x1())


# ── A. lecture / écriture ────────────────────────────────────────────────────

def test_aller_retour_glb_ne_deforme_rien():
    from app.services import mesh_edit
    data = _cube()
    doc, binc = mesh_edit.lire_glb(data)
    refait = mesh_edit.ecrire_glb(doc, binc)
    doc2, bin2 = mesh_edit.lire_glb(refait)
    assert doc == doc2
    assert binc == bin2


def test_le_glb_reecrit_se_relit_par_print3d():
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    tris = print3d.lire_glb_triangles(mesh_edit.ecrire_glb(doc, binc))
    assert len(tris) == 12
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_un_fichier_qui_n_est_pas_un_glb_est_refuse_parlant():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="magic GLB"):
        mesh_edit.lire_glb(b"ceci n'est pas un GLB")


def test_des_octets_parasites_apres_la_fin_declaree_sont_ignores():
    """Le conteneur GLB déclare sa longueur à l'octet 8, et cette longueur
    FAIT AUTORITÉ — `print3d._chunks` la respecte déjà.

    Sans cette borne, des octets traînant après la fin (téléchargement
    rejoué, artefact d'un générateur tiers) seraient lus comme des chunks.
    Ici la queue imite un chunk BIN vide : sans borne, le tampon déjà lu
    serait écrasé EN SILENCE, sans la moindre exception."""
    from app.services import mesh_edit
    data = _cube()
    doc, binc = mesh_edit.lire_glb(data)
    assert binc, "le cube doit avoir un tampon binaire"
    parasite = data + struct.pack("<I", 0) + b"BIN\x00"
    doc2, bin2 = mesh_edit.lire_glb(parasite)
    assert doc2 == doc
    assert bin2 == binc          # et surtout : PAS écrasé par le bruit
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.mesh_edit'` sur
les quatre tests.

- [ ] **Step 3 : écrire le module minimal**

Créer `backend/app/services/mesh_edit.py` :

```python
# -*- coding: utf-8 -*-
"""Chirurgie de document glTF — la SEULE plume à GLB du chantier Établi.

Règle de l'option C (spec 2026-08-29-etabli-inspecteur-3d-design §2.1) : le
navigateur voit et manipule, Python écrit. Aucun GLB n'est jamais produit par
le client, de sorte que tout artefact reste versionné, fiché par mesh_report,
et vérifiable par le harnais.

Deux propriétés porteront la sûreté du module, et les bancs des tâches 3 et 5
de ce plan les épingleront (elles n'existent pas encore à la tâche 1) :

* `extraire` est une RECOPIE D'OCTETS, jamais un décodage de géométrie — les
  bufferViews retenus sont copiés tels quels. L'extraction fonctionne donc sur
  un GLB Draco ou meshopt, là où `print3d.lire_glb_triangles` refuse.
* `transformer` ne touche QUE le document JSON — le tampon binaire ressort
  identique octet pour octet, ce qui rend l'opération sûre sur 200 Mo.

Module sans `settings` : de la manipulation d'octets pure, testable sans
environnement.
"""
from __future__ import annotations

import json
import struct

_MAGIC = b"glTF"
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942


def lire_glb(data: bytes) -> tuple[dict, bytes]:
    """Les DEUX moitiés d'un GLB v2 : le document et son tampon.

    `mesh_report._gltf_json` ne rend que le JSON et `print3d` sert son propre
    décodeur ; la chirurgie a besoin des deux et de savoir les recoller.
    """
    if len(data) < 12 or data[:4] != _MAGIC:
        raise ValueError("magic GLB absent — ce fichier n'est pas un .glb")
    version, longueur = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ValueError(f"GLB v{version} non géré (v2 attendu)")
    doc: dict | None = None
    binc = b""
    off = 12
    # Borner par la longueur DÉCLARÉE dans l'en-tête, comme le fait déjà
    # `print3d._chunks`. Sans cette borne, des octets parasites après la fin
    # du conteneur (téléchargement rejoué, artefact d'un générateur tiers)
    # seraient lus comme des chunks : si les quatre suivants ressemblent à
    # `BIN\0`, le tampon déjà lu serait écrasé EN SILENCE. Un GLB de 200 Mo
    # venu de Meshy ou Tripo mérite mieux qu'une corruption muette.
    while off + 8 <= min(longueur, len(data)):
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        bloc = data[off:off + clen]
        if ctype == _CHUNK_JSON:
            doc = json.loads(bloc.decode("utf-8"))
        elif ctype == _CHUNK_BIN:
            binc = bloc
        off += clen + (-clen % 4)
    if doc is None:
        raise ValueError("chunk JSON introuvable")
    return doc, binc


def ecrire_glb(doc: dict, binc: bytes) -> bytes:
    """Recolle un document et son tampon. Les deux chunks sont alignés sur 4
    octets — le JSON par des espaces, le binaire par des zéros, comme l'exige
    la spec glTF 2.0."""
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    bn = bytes(binc) + b"\x00" * (-len(binc) % 4)
    total = 12 + 8 + len(js) + ((8 + len(bn)) if bn else 0)
    out = struct.pack("<4sII", _MAGIC, 2, total)
    out += struct.pack("<II", len(js), _CHUNK_JSON) + js
    if bn:
        out += struct.pack("<II", len(bn), _CHUNK_BIN) + bn
    return out


def _l(doc: dict, cle: str) -> list:
    """Un tableau glTF absent et un tableau vide se traitent pareil."""
    return doc.get(cle) or []
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 4 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : mesh_edit lit et reecrit un GLB sans le deformer' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 2 : inventorier un squelette

**Files:**
- Modify: `backend/app/services/mesh_edit.py`
- Test: `backend/tests/test_etabli_socle.py`

Le panneau Rig de P4 doit pouvoir dire « ce maillage n'a pas de squelette »
**avant** de télécharger 200 Mo. La fonction ne lit que le chunk JSON.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── B. inventaire de squelette ───────────────────────────────────────────────

def test_un_maillage_sans_squelette_le_dit():
    from app.services import mesh_edit
    inv = mesh_edit.rig_inventory(_cube())
    assert inv["a_squelette"] is False
    assert inv["os"] == []
    assert inv["clips"] == []


def test_l_inventaire_lit_les_os_et_leur_hierarchie():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    base = len(doc["nodes"])
    doc["nodes"].append({"name": "hanche", "children": [base + 1]})
    doc["nodes"].append({"name": "colonne"})
    doc["skins"] = [{"name": "armature", "joints": [base, base + 1],
                     "skeleton": base}]
    doc["nodes"][0]["skin"] = 0
    doc["animations"] = [{"name": "idle", "channels": [], "samplers": []}]
    inv = mesh_edit.rig_inventory(mesh_edit.ecrire_glb(doc, binc))
    assert inv["a_squelette"] is True
    assert inv["nb_os"] == 2
    assert [o["nom"] for o in inv["os"]] == ["hanche", "colonne"]
    assert inv["os"][0]["enfants"] == [base + 1]
    assert inv["os"][1]["parent"] == base
    assert inv["clips"] == [{"nom": "idle", "canaux": 0}]
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `AttributeError: module 'app.services.mesh_edit' has no attribute 'rig_inventory'`.

- [ ] **Step 3 : implémenter**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
def rig_inventory(data: bytes) -> dict:
    """Os, hiérarchie, skins et clips — chunk JSON seulement.

    Instantané même sur un GLB de 200 Mo, et c'est le but : le panneau Rig doit
    pouvoir annoncer l'absence de squelette sans rien télécharger.

    CONTRAT À LIRE AVANT DE BÂTIR UN ARBRE DESSUS : `os` ne contient que les
    JOINTS. Un `os[].parent` peut donc désigner un nœud absent de la liste —
    c'est le cas courant des exports Blender ou Mixamo, où la racine
    d'armature (`skins[].skeleton`) porte le déplacement global sans être
    elle-même un os. Un consommateur doit traiter un `parent` introuvable
    comme une racine, jamais supposer qu'il se résout dans `os`.
    """
    doc, _ = lire_glb(data)
    nodes = _l(doc, "nodes")
    skins = _l(doc, "skins")

    parent: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent[c] = i

    joints: list[int] = []
    for s in skins:
        for j in _l(s, "joints"):
            if j not in joints:
                joints.append(j)

    os_: list[dict] = []
    for j in joints:
        n = nodes[j] if 0 <= j < len(nodes) else {}
        os_.append({
            "index": j,
            "nom": n.get("name") or f"os_{j}",
            "parent": parent.get(j),
            "enfants": [c for c in _l(n, "children") if c in joints],
        })

    clips = [{"nom": a.get("name") or f"clip_{i}",
              "canaux": len(_l(a, "channels"))}
             for i, a in enumerate(_l(doc, "animations"))]

    return {
        "a_squelette": bool(skins),
        "nb_os": len(joints),
        "os": os_,
        "skins": [{"nom": s.get("name") or f"skin_{i}",
                   "nb_joints": len(_l(s, "joints")),
                   "racine": s.get("skeleton")}
                  for i, s in enumerate(skins)],
        "clips": clips,
    }
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 6 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : rig_inventory lit os, hierarchie et clips sans toucher au binaire' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 3 : transformer un nœud sans toucher au tampon

**Files:**
- Modify: `backend/app/services/mesh_edit.py`
- Test: `backend/tests/test_etabli_socle.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── C. transformer : JSON seulement ──────────────────────────────────────────

def test_transformer_laisse_le_tampon_binaire_identique():
    """LA propriété qui rend l'opération sûre sur un fichier de 200 Mo."""
    from app.services import mesh_edit
    base = _cube()
    bouge = mesh_edit.transformer(base, {"0": {"translation": [0.0, 3.0, 0.0]}})
    _, bin_avant = mesh_edit.lire_glb(base)
    _, bin_apres = mesh_edit.lire_glb(bouge)
    assert bin_avant == bin_apres


def test_transformer_deplace_vraiment_le_maillage():
    from app.services import mesh_edit, print3d
    bouge = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    assert print3d.bbox(print3d.lire_glb_triangles(bouge)) == (
        (-1.0, 1.0), (2.0, 4.0), (-1.0, 1.0))


def test_transformer_refuse_un_noeud_hors_document():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="hors du document"):
        mesh_edit.transformer(_cube(), {"99": {"translation": [0.0, 0.0, 0.0]}})


def test_transformer_refuse_un_vecteur_de_mauvaise_taille():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="attend 3 valeurs"):
        mesh_edit.transformer(_cube(), {"0": {"translation": [1.0, 2.0]}})


def test_transformer_refuse_un_quaternion_non_norme():
    """glTF exige un quaternion UNITAIRE. Le refuser plutôt que le normaliser
    en douce : normaliser masquerait le bug amont qui l'a produit."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="quaternion normé"):
        mesh_edit.transformer(_cube(), {"0": {"rotation": [0.0, 0.0, 0.0, 2.0]}})


def test_transformer_refuse_une_entree_qui_n_est_pas_un_dictionnaire():
    """Sans ce garde, une liste lève AttributeError — que la route de la
    tâche 8 ne rattrape pas, et qui sortirait donc en 500 au lieu d'un 400."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="dictionnaire"):
        mesh_edit.transformer(_cube(), [{"0": {}}])
    with pytest.raises(ValueError, match="non numérique"):
        mesh_edit.transformer(_cube(), {"abc": {"translation": [0.0, 0.0, 0.0]}})


def test_transformer_exerce_aussi_rotation_et_echelle():
    """Les chemins `rotation` et `scale` de `_TAILLES` ne sont exercés par
    aucun autre banc. TRS glTF = T · R · S : le cube unité mis à l'échelle 2,
    tourné d'un quart de tour autour de X, puis décalé de +3 en Y."""
    from app.services import mesh_edit, print3d
    q = [(2 ** 0.5) / 2, 0.0, 0.0, (2 ** 0.5) / 2]      # 90° autour de X
    sortie = mesh_edit.transformer(_cube(), {"0": {
        "translation": [0.0, 3.0, 0.0], "rotation": q, "scale": [2.0, 2.0, 2.0]}})
    doc, _ = mesh_edit.lire_glb(sortie)
    assert doc["nodes"][0]["scale"] == [2.0, 2.0, 2.0]
    bb = print3d.bbox(print3d.lire_glb_triangles(sortie))
    attendu = ((-2.0, 2.0), (1.0, 5.0), (-2.0, 2.0))
    for (lo, hi), (alo, ahi) in zip(bb, attendu):
        assert abs(lo - alo) < 1e-6 and abs(hi - ahi) < 1e-6


def test_transformer_retire_une_matrice_preexistante():
    """glTF interdit de porter `matrix` ET un TRS : la docstring en fait une
    garantie, ce banc l'épingle."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["nodes"][0]["matrix"] = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                                 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    avec = mesh_edit.ecrire_glb(doc, binc)
    sortie, _ = mesh_edit.lire_glb(
        mesh_edit.transformer(avec, {"0": {"translation": [0.0, 1.0, 0.0]}}))
    assert "matrix" not in sortie["nodes"][0]
    assert sortie["nodes"][0]["translation"] == [0.0, 1.0, 0.0]
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `AttributeError: ... has no attribute 'transformer'`.

- [ ] **Step 3 : implémenter**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
_TAILLES = {"translation": 3, "rotation": 4, "scale": 3}
_TOLERANCE_QUATERNION = 1e-3


def transformer(data: bytes, transforms: dict) -> bytes:
    """Position / rotation / échelle de nœuds nommés.

    N'écrit QUE le document : le tampon binaire ressort identique octet pour
    octet, et le banc l'épingle. `matrix` est retiré du nœud touché — glTF
    interdit de porter à la fois une matrice et un TRS.

    Trois refus explicites plutôt que des corrections silencieuses, parce que
    cette fonction sera exposée par une route HTTP (tâche 8) qui ne traduit
    en 400 que les `ValueError` : entrée non-dictionnaire, clé de nœud non
    numérique, quaternion non normalisé. Normaliser un quaternion en douce
    masquerait un bug amont ; le refuser le montre.

    `scale` négatif ou nul passe DÉLIBÉRÉMENT : une échelle négative par axe
    est un TRS glTF valide (effet miroir). `reparer` refuse au contraire une
    échelle globale ≤ 0. Les deux fonctions n'ont pas la même politique, et
    c'est voulu — ne pas « harmoniser » sans y repenser.
    """
    if transforms is None:
        transforms = {}
    if not isinstance(transforms, dict):
        raise ValueError(
            "transforms attend un dictionnaire noeud -> TRS, reçu "
            f"{type(transforms).__name__}")
    doc, binc = lire_glb(data)
    nodes = _l(doc, "nodes")
    for cle, trs in transforms.items():
        try:
            i = int(cle)
        except (TypeError, ValueError):
            raise ValueError(f"clé de noeud non numérique : {cle!r}") from None
        if not (0 <= i < len(nodes)):
            raise ValueError(f"noeud {i} hors du document ({len(nodes)} noeuds)")
        n = nodes[i]
        n.pop("matrix", None)
        for champ, taille in _TAILLES.items():
            if champ not in trs:
                continue
            v = [float(x) for x in trs[champ]]
            if len(v) != taille:
                raise ValueError(f"{champ} attend {taille} valeurs, reçu {len(v)}")
            if champ == "rotation":
                # glTF exige un quaternion UNITAIRE. Non normalisé, il déforme
                # chez les lecteurs stricts et pas chez les autres : un bug qui
                # ne se voit qu'à l'export, donc à attraper à l'écriture.
                norme = sum(x * x for x in v) ** 0.5
                if abs(norme - 1.0) > _TOLERANCE_QUATERNION:
                    raise ValueError(
                        "rotation attend un quaternion normé [x,y,z,w] ; "
                        f"norme reçue {norme:.4f}")
            n[champ] = v
    return ecrire_glb(doc, binc)
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 14 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : transformer un noeud sans toucher au tampon binaire' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 4 : réparer l'assise — axe haut, échelle, recentrage

**Files:**
- Modify: `backend/app/services/mesh_edit.py`
- Test: `backend/tests/test_etabli_socle.py`

Un nœud racine neuf porte la correction. Le recentrage est la **seule** des
trois opérations qui a besoin de la géométrie, donc la seule qui refuse sur un
fichier compressé — et elle doit le dire au lieu d'échouer en bloc.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── D. réparer : assise globale ──────────────────────────────────────────────

def test_reparer_met_a_l_echelle():
    from app.services import mesh_edit, print3d
    gros = mesh_edit.reparer(_cube(), echelle=2.0)
    assert print3d.bbox(print3d.lire_glb_triangles(gros)) == (
        (-2.0, 2.0), (-2.0, 2.0), (-2.0, 2.0))


def test_reparer_bascule_en_z_up():
    """Un decalage de +3 en Y doit se retrouver en +3 en Z."""
    from app.services import mesh_edit, print3d
    haut = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    zup = mesh_edit.reparer(haut, axe_haut="Z")
    assert print3d.bbox(print3d.lire_glb_triangles(zup)) == (
        (-1.0, 1.0), (-1.0, 1.0), (2.0, 4.0))


def test_reparer_recentre_sur_l_origine():
    from app.services import mesh_edit, print3d
    haut = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    centre = mesh_edit.reparer(haut, recentrer=True)
    assert print3d.bbox(print3d.lire_glb_triangles(centre)) == (
        (-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_reparer_refuse_un_axe_inconnu():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="axe haut inconnu"):
        mesh_edit.reparer(_cube(), axe_haut="Q")


def test_reparer_refuse_une_echelle_nulle_ou_negative():
    """Politique DIFFÉRENTE de `transformer`, et c'est voulu : une échelle
    globale ≤ 0 n'a pas de sens pour une assise, alors qu'un `scale` négatif
    par axe est un miroir glTF parfaitement valide."""
    from app.services import mesh_edit
    for mauvaise in (0.0, -1.0):
        with pytest.raises(ValueError, match="strictement positive"):
            mesh_edit.reparer(_cube(), echelle=mauvaise)


def _cube_compresse() -> bytes:
    """Un cube qui se DÉCLARE draco. `print3d` refuse sur la déclaration
    `extensionsRequired`, pas sur le décodage : c'est donc une simulation
    honnête du contrat, sans embarquer un encodeur Draco au banc."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    return mesh_edit.ecrire_glb(doc, binc)


def test_reparer_refuse_des_parametres_de_mauvais_type():
    """Ces deux paramètres viendront d'un corps JSON (tâche 8), et la route ne
    traduit en 400 que les `ValueError`. Sans gardes, `axe_haut=123` lève
    AttributeError et `echelle=[1.0]` TypeError — deux 500."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="axe_haut attend une chaîne"):
        mesh_edit.reparer(_cube(), axe_haut=123)
    with pytest.raises(ValueError, match="echelle attend un nombre"):
        mesh_edit.reparer(_cube(), echelle=[1.0])
    # `bool` est un `int` : sans garde, True passerait pour une échelle de 1
    with pytest.raises(ValueError, match="echelle attend un nombre"):
        mesh_edit.reparer(_cube(), echelle=True)


def test_reparer_refuse_une_scene_active_hors_du_document():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["scene"] = 5
    with pytest.raises(ValueError, match="scène active 5 hors du document"):
        mesh_edit.reparer(mesh_edit.ecrire_glb(doc, binc))


def test_sur_un_glb_compresse_la_degradation_est_partielle_et_explicite():
    """LE principe du dépôt : axe et échelle passent, seul le recentrage
    refuse — et il dit pourquoi. Jamais un échec global quand une partie du
    travail est faisable."""
    from app.services import mesh_edit, print3d
    comp = _cube_compresse()
    with pytest.raises(ValueError, match="draco"):
        print3d.lire_glb_triangles(comp)
    # axe + échelle : aucune géométrie n'est lue, donc ça passe
    sortie, _ = mesh_edit.lire_glb(
        mesh_edit.reparer(comp, axe_haut="Z", echelle=2.0))
    assert sortie["nodes"][-1]["name"] == "etabli_correction"
    assert sortie["extensionsRequired"] == ["KHR_draco_mesh_compression"]
    # le recentrage, lui, a besoin des triangles : il refuse, en le disant
    with pytest.raises(ValueError, match="draco"):
        mesh_edit.reparer(comp, recentrer=True)
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `AttributeError: ... has no attribute 'reparer'`.

- [ ] **Step 3 : implémenter**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
# Y-up est la convention glTF ; Z-up est celle de Blender et d'Unreal.
# La rotation envoie +Y sur +Z : (x, y, z) -> (x, -z, y).
_ROT = {
    "Y": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "Z": ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
}


def _matrice(rot, s: float, t) -> list[float]:
    """Matrice glTF COLONNE-majeure pour p' = R · (s · p) + t.

    Se tromper d'ordre ici donne un modèle couché, et le banc de bascule Z-up
    est là pour l'attraper.
    """
    m = [[rot[r][c] * s for c in range(3)] for r in range(3)]
    return [m[0][0], m[1][0], m[2][0], 0.0,
            m[0][1], m[1][1], m[2][1], 0.0,
            m[0][2], m[1][2], m[2][2], 0.0,
            float(t[0]), float(t[1]), float(t[2]), 1.0]


def reparer(data: bytes, *, axe_haut: str | None = None,
            echelle: float | None = None, recentrer: bool = False) -> bytes:
    """Assise globale : axe haut, échelle, recentrage sur l'origine.

    La correction est portée par un nœud racine NEUF qui adopte les racines de
    la scène — on ne réécrit jamais les transformations existantes, de sorte
    qu'une réparation reste lisible et annulable dans le document.

    `recentrer` est la seule option qui a besoin de la géométrie : elle passe
    par `print3d.lire_glb_triangles`, qui refuse un GLB compressé avec un
    message explicite. Les deux autres options n'ont pas cette limite.

    Seule la scène active (`doc["scene"]`) est corrigée : un GLB multi-scènes
    garderait les autres intactes. C'est la convention de tout le module —
    `print3d.lire_glb_triangles` et `rig_inventory` font de même — et les
    maillages livrés par Meshy, Tripo ou Rodin sont mono-scène en pratique.

    Deux réparations successives EMPILENT deux nœuds `etabli_correction`
    imbriqués : c'est voulu, chaque correction restant ainsi annulable. Mais
    cela veut dire qu'on ne cherche jamais « le » nœud de correction par son
    nom — il peut y en avoir plusieurs.
    """
    from app.services import print3d

    # Types validés AVANT toute lecture : ces deux paramètres viendront d'un
    # corps JSON (tâche 8), et la route ne traduit en 400 que les ValueError.
    # Sans ces gardes, `axe_haut=123` lève AttributeError et `echelle=[1.0]`
    # lève TypeError — deux 500 au lieu de deux refus parlants.
    if axe_haut is not None and not isinstance(axe_haut, str):
        raise ValueError("axe_haut attend une chaîne (Y ou Z), reçu "
                         f"{type(axe_haut).__name__}")
    if echelle is not None and (isinstance(echelle, bool)
                                or not isinstance(echelle, (int, float))):
        # `bool` est un `int` en Python : sans ce garde, `echelle=True`
        # deviendrait silencieusement une échelle de 1.
        raise ValueError("echelle attend un nombre, reçu "
                         f"{type(echelle).__name__}")

    doc, binc = lire_glb(data)
    axe = (axe_haut or "Y").upper()
    if axe not in _ROT:
        raise ValueError(f"axe haut inconnu : {axe} (attendu Y ou Z)")
    rot = _ROT[axe]
    s = 1.0 if echelle is None else float(echelle)
    if s <= 0:
        raise ValueError("echelle doit être strictement positive")

    t = [0.0, 0.0, 0.0]
    if recentrer:
        tris = print3d.lire_glb_triangles(data)
        (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
        c = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
        t = [-sum(rot[r][k] * s * c[k] for k in range(3)) for r in range(3)]

    scenes = doc.get("scenes") or [{"nodes": []}]
    isc = int(doc.get("scene", 0))
    if not (0 <= isc < len(scenes)):
        raise ValueError(f"scène active {isc} hors du document "
                         f"({len(scenes)} scènes)")
    racines = list(scenes[isc].get("nodes") or [])
    doc.setdefault("nodes", []).append({
        "name": "etabli_correction",
        "children": racines,
        "matrix": _matrice(rot, s, t),
    })
    scenes[isc]["nodes"] = [len(doc["nodes"]) - 1]
    doc["scenes"] = scenes
    return ecrire_glb(doc, binc)
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 22 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : reparer axe haut, echelle et recentrage par un noeud racine' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 5 : extraire une partie — la recopie d'octets

**Files:**
- Modify: `backend/app/services/mesh_edit.py`
- Test: `backend/tests/test_etabli_socle.py`

La pièce centrale du design. Le sous-arbre retenu garde ses bufferViews
**copiés tels quels** ; tout le reste est élagué et les index sont remappés.

> ### ⚠ Décision de conception issue de la revue de la tâche 4
>
> La revue a repéré un piège que cette tâche doit traiter, et qui n'était pas
> dans la première rédaction du plan.
>
> Après un `reparer`, la scène a une racine synthétique `etabli_correction`
> qui porte la matrice de correction, et les anciennes racines sont devenues
> ses enfants. Si `extraire` sélectionne un nœud **sous** cette racine et
> recopie sa seule transformation locale, la pièce extraite **perd en silence
> la correction d'axe et d'échelle** : un modèle redressé puis découpé
> ressortirait couché.
>
> **Tranche retenue : `extraire` compose les matrices des ANCÊTRES hors
> sélection dans chaque racine extraite.** La pièce sort donc là où
> l'utilisateur la voyait — ce qui est le sens même de « séparer une partie
> de ce modèle ». L'inverse (garder l'espace local) serait défendable pour un
> outil de rigging, pas pour un outil qui sépare ce qu'on regarde.
>
> **Un banc doit l'épingler** : `reparer(axe_haut="Z")` puis `extraire` d'un
> sous-nœud, et vérifier que la bbox extraite est bien celle du monde
> redressé, pas celle d'avant correction. Les valeurs attendues seront
> **mesurées** avant d'être écrites, comme le reste de ce plan.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── E. extraire : la somme des parties fait le tout ──────────────────────────

def test_le_depart_porte_bien_deux_parties():
    from app.services import print3d
    assert len(print3d.lire_glb_triangles(_cube_et_sol())) == 14


def test_extraire_le_cube_garde_ses_douze_triangles():
    from app.services import mesh_edit, print3d
    cube = mesh_edit.extraire(_cube_et_sol(), [0])
    tris = print3d.lire_glb_triangles(cube)
    assert len(tris) == 12
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_extraire_elague_les_dependances_de_l_autre_partie():
    """Le cube ne doit PAS trainer la texture du sol : c'est tout l'interet
    d'extraire plutot que de masquer."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(mesh_edit.extraire(_cube_et_sol(), [0]))
    assert len(doc["nodes"]) == 1
    assert len(doc["meshes"]) == 1
    assert len(doc.get("materials", [])) == 1
    assert len(doc.get("images", [])) == 0
    assert len(doc["accessors"]) == 5
    assert len(doc["bufferViews"]) == 5
    assert len(binc) == 1224


def test_extraire_le_sol_garde_SA_texture():
    from app.services import mesh_edit, print3d
    sol = mesh_edit.extraire(_cube_et_sol(), [1])
    doc, _ = mesh_edit.lire_glb(sol)
    assert len(print3d.lire_glb_triangles(sol)) == 2
    assert len(doc["images"]) == 1
    assert len(doc["materials"]) == 1


def test_extraire_emporte_les_enfants_du_noeud():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    doc["nodes"][0]["children"] = [1]
    doc["scenes"][0]["nodes"] = [0]
    tout = mesh_edit.ecrire_glb(doc, binc)
    sortie, _ = mesh_edit.lire_glb(mesh_edit.extraire(tout, [0]))
    assert len(sortie["nodes"]) == 2


def test_extraire_refuse_une_selection_vide():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="aucun noeud retenu"):
        mesh_edit.extraire(_cube_et_sol(), [])
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `AttributeError: ... has no attribute 'extraire'`.

- [ ] **Step 3 : implémenter la collecte des dépendances**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
def _dependances(doc: dict, garder: set[int]) -> dict:
    """Tout ce qu'un ensemble de nœuds retenus tire derrière lui.

    L'ordre compte : nœuds -> meshes/skins -> accesseurs et matériaux ->
    textures -> images -> bufferViews. Un maillon oublié produit un GLB qui
    référence un index disparu, et le lecteur le dit brutalement.
    """
    nodes = _l(doc, "nodes")
    meshes = {nodes[i]["mesh"] for i in garder
              if nodes[i].get("mesh") is not None}
    skins = {nodes[i]["skin"] for i in garder
             if nodes[i].get("skin") is not None}
    # un skin dont TOUS les joints ne sont pas retenus est lâché : le garder
    # produirait une peau qui vise des os absents
    skins = {s for s in skins
             if all(j in garder for j in _l(_l(doc, "skins")[s], "joints"))}

    acc: set[int] = set()
    mats: set[int] = set()
    for mi in meshes:
        for p in _l(_l(doc, "meshes")[mi], "primitives"):
            acc.update((p.get("attributes") or {}).values())
            if p.get("indices") is not None:
                acc.add(p["indices"])
            for cible in _l(p, "targets"):
                acc.update(cible.values())
            if p.get("material") is not None:
                mats.add(p["material"])
    for si in skins:
        ibm = _l(doc, "skins")[si].get("inverseBindMatrices")
        if ibm is not None:
            acc.add(ibm)

    texs: set[int] = set()

    def _tex(x) -> None:
        if isinstance(x, dict) and x.get("index") is not None:
            texs.add(x["index"])

    for mi in mats:
        m = _l(doc, "materials")[mi]
        pbr = m.get("pbrMetallicRoughness") or {}
        _tex(pbr.get("baseColorTexture"))
        _tex(pbr.get("metallicRoughnessTexture"))
        _tex(m.get("normalTexture"))
        _tex(m.get("occlusionTexture"))
        _tex(m.get("emissiveTexture"))

    imgs: set[int] = set()
    smps: set[int] = set()
    for ti in texs:
        t = _l(doc, "textures")[ti]
        if t.get("source") is not None:
            imgs.add(t["source"])
        if t.get("sampler") is not None:
            smps.add(t["sampler"])

    bvs: set[int] = set()
    for ai in acc:
        a = _l(doc, "accessors")[ai]
        if a.get("bufferView") is not None:
            bvs.add(a["bufferView"])
        sparse = a.get("sparse") or {}
        for part in ("indices", "values"):
            vue = (sparse.get(part) or {}).get("bufferView")
            if vue is not None:
                bvs.add(vue)
    for ii in imgs:
        vue = _l(doc, "images")[ii].get("bufferView")
        if vue is not None:
            bvs.add(vue)
    # compression : la vue Draco est RECOPIÉE sans être décodée — c'est ce qui
    # fait marcher l'extraction là où le lecteur de triangles refuse
    for mi in meshes:
        for p in _l(_l(doc, "meshes")[mi], "primitives"):
            draco = (p.get("extensions") or {}).get(
                "KHR_draco_mesh_compression") or {}
            if draco.get("bufferView") is not None:
                bvs.add(draco["bufferView"])

    return {"meshes": meshes, "skins": skins, "accessors": acc,
            "materials": mats, "textures": texs, "images": imgs,
            "samplers": smps, "bufferViews": bvs}
```

- [ ] **Step 4 : implémenter l'extraction et le remappage**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
def _carte(ref: set[int]) -> tuple[dict[int, int], list[int]]:
    ordre = sorted(ref)
    return {v: i for i, v in enumerate(ordre)}, ordre


def extraire(data: bytes, noeuds) -> bytes:
    """Un GLB qui ne contient QUE le sous-arbre demandé et ses dépendances.

    RECOPIE D'OCTETS : les bufferViews retenus sont copiés tels quels, sans
    décodage. L'opération survit donc à Draco et meshopt, contrairement à tout
    ce qui lit des triangles.
    """
    doc, binc = lire_glb(data)
    nodes = _l(doc, "nodes")

    garder: set[int] = set()
    pile = [int(n) for n in (noeuds or [])]
    while pile:
        i = pile.pop()
        if i in garder or not (0 <= i < len(nodes)):
            continue
        garder.add(i)
        pile.extend(_l(nodes[i], "children"))
    if not garder:
        raise ValueError("aucun noeud retenu — la selection est vide")

    dep = _dependances(doc, garder)
    m_node, o_node = _carte(garder)
    m_mesh, o_mesh = _carte(dep["meshes"])
    m_mat, o_mat = _carte(dep["materials"])
    m_tex, o_tex = _carte(dep["textures"])
    m_img, o_img = _carte(dep["images"])
    m_smp, o_smp = _carte(dep["samplers"])
    m_acc, o_acc = _carte(dep["accessors"])
    m_bv, o_bv = _carte(dep["bufferViews"])
    m_skin, o_skin = _carte(dep["skins"])

    neuf = bytearray()
    vues: list[dict] = []
    for bi in o_bv:
        v = dict(_l(doc, "bufferViews")[bi])
        off, ln = v.get("byteOffset", 0), v["byteLength"]
        while len(neuf) % 4:
            neuf.append(0)
        v["byteOffset"] = len(neuf)
        v["buffer"] = 0
        neuf += binc[off:off + ln]
        vues.append(v)

    out: dict = {"asset": doc.get("asset") or {"version": "2.0"}}
    out["bufferViews"] = vues
    out["buffers"] = [{"byteLength": len(neuf)}]

    out["accessors"] = []
    for ai in o_acc:
        a = dict(_l(doc, "accessors")[ai])
        if a.get("bufferView") is not None:
            a["bufferView"] = m_bv[a["bufferView"]]
        out["accessors"].append(a)

    if o_smp:
        out["samplers"] = [dict(_l(doc, "samplers")[i]) for i in o_smp]
    if o_img:
        out["images"] = []
        for ii in o_img:
            im = dict(_l(doc, "images")[ii])
            if im.get("bufferView") is not None:
                im["bufferView"] = m_bv[im["bufferView"]]
            out["images"].append(im)
    if o_tex:
        out["textures"] = []
        for ti in o_tex:
            t = dict(_l(doc, "textures")[ti])
            if t.get("source") is not None:
                t["source"] = m_img[t["source"]]
            if t.get("sampler") is not None:
                t["sampler"] = m_smp[t["sampler"]]
            out["textures"].append(t)
    if o_mat:
        out["materials"] = []
        for mi in o_mat:
            m = json.loads(json.dumps(_l(doc, "materials")[mi]))
            pbr = m.get("pbrMetallicRoughness") or {}
            for hote, cle in ((pbr, "baseColorTexture"),
                              (pbr, "metallicRoughnessTexture"),
                              (m, "normalTexture"), (m, "occlusionTexture"),
                              (m, "emissiveTexture")):
                cible = hote.get(cle)
                if isinstance(cible, dict) and cible.get("index") is not None:
                    cible["index"] = m_tex[cible["index"]]
            out["materials"].append(m)

    out["meshes"] = []
    for mi in o_mesh:
        me = json.loads(json.dumps(_l(doc, "meshes")[mi]))
        for p in me.get("primitives") or []:
            p["attributes"] = {k: m_acc[v]
                               for k, v in (p.get("attributes") or {}).items()}
            if p.get("indices") is not None:
                p["indices"] = m_acc[p["indices"]]
            if p.get("material") is not None:
                p["material"] = m_mat[p["material"]]
            for cible in p.get("targets") or []:
                for k in list(cible):
                    cible[k] = m_acc[cible[k]]
            draco = (p.get("extensions") or {}).get(
                "KHR_draco_mesh_compression")
            if draco and draco.get("bufferView") is not None:
                draco["bufferView"] = m_bv[draco["bufferView"]]
        out["meshes"].append(me)

    if o_skin:
        out["skins"] = []
        for si in o_skin:
            s = json.loads(json.dumps(_l(doc, "skins")[si]))
            if s.get("inverseBindMatrices") is not None:
                s["inverseBindMatrices"] = m_acc[s["inverseBindMatrices"]]
            s["joints"] = [m_node[j] for j in _l(s, "joints")]
            if s.get("skeleton") in m_node:
                s["skeleton"] = m_node[s["skeleton"]]
            else:
                s.pop("skeleton", None)
            out["skins"].append(s)

    out["nodes"] = []
    for ni in o_node:
        n = json.loads(json.dumps(nodes[ni]))
        enfants = [m_node[c] for c in _l(n, "children") if c in m_node]
        if enfants:
            n["children"] = enfants
        else:
            n.pop("children", None)
        if n.get("mesh") is not None:
            n["mesh"] = m_mesh[n["mesh"]]
        if n.get("skin") is not None:
            if n["skin"] in m_skin:
                n["skin"] = m_skin[n["skin"]]
            else:
                n.pop("skin")
        n.pop("camera", None)
        out["nodes"].append(n)

    racines = [m_node[i] for i in sorted({int(x) for x in noeuds})
               if i in m_node]
    out["scenes"] = [{"nodes": racines}]
    out["scene"] = 0
    for cle in ("extensionsUsed", "extensionsRequired"):
        if doc.get(cle):
            out[cle] = doc[cle]
    return ecrire_glb(out, bytes(neuf))
```

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 28 tests PASS.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : extraire une partie par recopie d octets, dependances elaguees' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 6 : écrire une version, jamais écraser

**Files:**
- Modify: `backend/app/services/mesh_edit.py`
- Test: `backend/tests/test_etabli_socle.py`

Le pont entre la chirurgie et la doctrine d'artefacts : toute sortie devient
`model.v{n}.glb` avec sa fiche.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── F. écriture versionnée ───────────────────────────────────────────────────

def test_ecrire_version_ajoute_sans_ecraser():
    from app.config import settings
    from app.services import mesh_edit
    d = settings.outputs_path / "assets3d" / "job_banc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube_et_sol())

    fiche = mesh_edit.ecrire_version(
        "job_banc", mesh_edit.extraire(_cube_et_sol(), [0]),
        operation="extraire", detail={"noeuds": [0]})

    assert fiche["version"] == 2
    assert fiche["file"] == "model.v2.glb"
    assert (d / "model.glb").is_file()          # le brouillon survit
    assert (d / "model.v2.glb").is_file()
    registre = json.loads((d / "report.json").read_text("utf-8"))
    assert registre["current"] == "model.v2.glb"
    assert fiche["source"]["operation"] == "extraire"
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `AttributeError: ... has no attribute 'ecrire_version'`.

- [ ] **Step 3 : implémenter**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
def ecrire_version(job: str, data: bytes, *, operation: str,
                   detail: dict | None = None) -> dict:
    """Dépose un GLB corrigé comme NOUVELLE version d'un job, avec sa fiche.

    Jamais d'écrasement (doctrine §2.1) : le numéro vient de
    `asset3d_service.next_version`, et `mesh_report.write_report` ajoute la
    fiche au registre en gardant toutes les précédentes.
    """
    from app.services import asset3d_service, mesh_report

    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)
    v = asset3d_service.next_version(job)
    nom = f"model.v{v}.glb"
    (d / nom).write_bytes(data)
    return mesh_report.write_report(
        job, nom, version=v,
        extra={"outil": "etabli", "operation": operation,
               **(detail or {})})
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 29 tests PASS.

- [ ] **Step 5 : écrire le banc de l'adoption (spec §6.2)**

Une tâche Meshy vit dans `outputs/meshy3d/<id>/`, qui n'a **pas** de registre.
Corriger un maillage venu de là doit donc créer un job `assets3d` pour
l'accueillir — une seule provenance, pas deux modèles concurrents.

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
def test_une_tache_meshy_est_adoptee_par_un_job():
    from app.config import settings
    from app.services import mesh_edit
    src = settings.outputs_path / "meshy3d" / "tache_abc"
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_cube_et_sol())

    job = mesh_edit.adopter_meshy("tache_abc", "model.glb")

    assert job == "meshy_tache_abc"
    d = settings.outputs_path / "assets3d" / job
    assert (d / "model.glb").is_file()
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["adopte_de"] == "meshy3d/tache_abc"
    # adopter deux fois ne duplique pas
    assert mesh_edit.adopter_meshy("tache_abc", "model.glb") == job


def test_l_adoption_refuse_une_tache_sans_glb():
    from app.services import mesh_edit
    with pytest.raises(FileNotFoundError):
        mesh_edit.adopter_meshy("tache_absente", "model.glb")
```

- [ ] **Step 6 : implémenter l'adoption**

Ajouter à `backend/app/services/mesh_edit.py` :

```python
def adopter_meshy(task_id: str, fichier: str = "model.glb") -> str:
    """Fait entrer un maillage Meshy dans le monde des jobs `assets3d`.

    Les binaires rapatriés vivent dans `outputs/meshy3d/<id>/`, qui n'a pas de
    registre : sans adoption, une correction n'aurait nulle part où être
    versionnée. Idempotent — adopter deux fois rend le même job.
    """
    import json as _json
    from pathlib import Path as _Path

    from app.config import settings
    from app.services import mesh_report

    tid = _Path(str(task_id)).name
    src = settings.outputs_path / "meshy3d" / tid / _Path(str(fichier)).name
    if not src.is_file():
        raise FileNotFoundError(f"meshy3d/{tid}/{_Path(fichier).name} introuvable")

    job = f"meshy_{tid}"
    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)
    cible = d / "model.glb"
    if not cible.is_file():
        cible.write_bytes(src.read_bytes())
        (d / "asset.json").write_text(_json.dumps({
            "name": job, "engine": "meshy", "stage": "adopte",
            "version": 1, "adopte_de": f"meshy3d/{tid}",
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        mesh_report.write_report(job, "model.glb", version=1,
                                 extra={"outil": "etabli",
                                        "operation": "adoption",
                                        "meshy_task": tid})
    return job
```

- [ ] **Step 7 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 31 tests PASS.

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/mesh_edit.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : ecrire_version sans ecrasement, et adoption d une tache Meshy par un job' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 7 : la chronologie unifiée des étapes

**Files:**
- Create: `backend/app/services/mesh_sources.py`
- Test: `backend/tests/test_etabli_socle.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── G. chronologie des étapes ────────────────────────────────────────────────

def test_la_chronologie_fond_les_versions_d_un_job():
    from app.config import settings
    from app.services import mesh_edit, mesh_sources
    d = settings.outputs_path / "assets3d" / "job_chrono"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    mesh_edit.ecrire_version("job_chrono", _cube_et_sol(),
                             operation="banc", detail={})

    lignes = [x for x in mesh_sources.lister() if x["id"] == "job_chrono"]
    assert len(lignes) == 1
    versions = lignes[0]["etapes"]
    assert [e["version"] for e in versions] == [1, 2]
    assert versions[0]["url"].endswith("/version/1")
    assert versions[1]["triangles"] == 14
    assert versions[0]["sha256"] != versions[1]["sha256"]


def test_la_chronologie_survit_a_un_job_sans_registre():
    from app.config import settings
    from app.services import mesh_sources
    d = settings.outputs_path / "assets3d" / "job_nu"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    lignes = [x for x in mesh_sources.lister() if x["id"] == "job_nu"]
    assert len(lignes) == 1
    assert lignes[0]["etapes"][0]["version"] == 1
    assert lignes[0]["etapes"][0]["triangles"] is None
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.mesh_sources'`.

- [ ] **Step 3 : implémenter**

Créer `backend/app/services/mesh_sources.py` :

```python
# -*- coding: utf-8 -*-
"""La vie d'un modèle, en une seule liste.

Trois registres racontent aujourd'hui la même histoire sans se parler : les
tâches Meshy (`MeshyTaskRecord`, binaires rapatriés), les versions d'un job
`assets3d` (`report.json`), et la version décimée (`model.opt.glb`). Ce module
les fond — il LIT ce qui existe, sans table ni migration.
"""
from __future__ import annotations

import json

from app.config import settings


def _jobs_dir():
    return settings.outputs_path / "assets3d"


def _versions_du_job(job: str) -> list[dict]:
    """Les versions d'un job, enrichies par sa fiche quand elle existe."""
    from app.services import mesh_report

    d = _jobs_dir() / job
    fiches: dict[str, dict] = {}
    try:
        registre = mesh_report.read_registry(job)
        for e in registre.get("entries") or []:
            fiches[str(e.get("file"))] = e
    except (FileNotFoundError, ValueError):
        pass                      # un job sans registre reste listable

    etapes: list[dict] = []
    for glb in sorted(d.glob("model*.glb")):
        if glb.name == "model.opt.glb":
            continue
        v = 1 if glb.name == "model.glb" else int(
            glb.name.split(".v")[1].split(".")[0])
        f = fiches.get(glb.name) or {}
        geo = f.get("geometry") or {}
        etapes.append({
            "version": v,
            "file": glb.name,
            "libelle": "brouillon" if v == 1 else f"version {v}",
            "url": f"/api/assets/3d/{job}/version/{v}",
            "bytes": glb.stat().st_size,
            "sha256": f.get("sha256"),
            # ATTENTION : la fiche nomme ce compte `tris_lus`, pas `triangles`.
            # `mesh_sources` normalise le nom pour toute l'interface.
            "triangles": geo.get("tris_lus"),
            "created_at": f.get("created_at"),
        })
    etapes.sort(key=lambda e: e["version"])
    if (d / "model.opt.glb").is_file():
        etapes.append({
            "version": None, "file": "model.opt.glb", "libelle": "décimée",
            "url": f"/api/assets/3d/{job}/opt-glb",
            "bytes": (d / "model.opt.glb").stat().st_size,
            "sha256": None, "triangles": None, "created_at": None,
        })
    return etapes


async def lister_meshy(limit: int = 60) -> list[dict]:
    """Les tâches Meshy rapatriées, une ligne par tâche."""
    from app.services import meshy_service

    out: list[dict] = []
    for t in await meshy_service.list_tasks(limit=limit):
        glbs = {k: u for k, u in (t.get("local_files") or {}).items()
                if str(u).endswith(".glb")}
        if not glbs:
            continue
        out.append({
            "source": "meshy", "id": t["id"], "nom": t["id"][:12],
            "phase": t.get("phase"), "kind": t.get("kind"),
            "created_at": t.get("created_at"),
            "etapes": [{
                "version": None, "file": cle, "libelle": cle,
                "url": url, "bytes": None, "sha256": None,
                "triangles": None, "created_at": t.get("created_at"),
            } for cle, url in sorted(glbs.items())],
        })
    return out


def lister() -> list[dict]:
    """Les jobs `assets3d` et leurs versions. Synchrone : lecture de disque."""
    racine = _jobs_dir()
    if not racine.is_dir():
        return []
    out: list[dict] = []
    for d in sorted(racine.iterdir()):
        if not d.is_dir():
            continue
        etapes = _versions_du_job(d.name)
        if not etapes:
            continue
        manifeste = {}
        p = d / "asset.json"
        if p.is_file():
            try:
                manifeste = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                manifeste = {}
        out.append({
            "source": "assets3d", "id": d.name,
            "nom": manifeste.get("name") or d.name,
            "moteur": manifeste.get("engine"),
            "phase": manifeste.get("stage"),
            "created_at": manifeste.get("created_at"),
            "etapes": etapes,
        })
    return out
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 33 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_sources.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : mesh_sources fond les registres 3D en une chronologie' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 8 : les routes `/api/etabli/*`

**Files:**
- Modify: `backend/app/api/routes.py` (ajouter à la fin, après les routes `meshy3d`)
- Test: `backend/tests/test_etabli_socle.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_socle.py` :

```python
# ── H. routes ────────────────────────────────────────────────────────────────

def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_la_route_sources_rend_la_chronologie():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_route"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    r = _client().get("/api/etabli/sources")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["jobs"]]
    assert "job_route" in ids


def test_la_route_rig_dit_l_absence_de_squelette():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_rig"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    r = _client().get("/api/etabli/rig", params={"job": "job_rig", "version": 1})
    assert r.status_code == 200
    assert r.json()["a_squelette"] is False


def test_la_route_extraire_ecrit_une_version_de_plus():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_extr"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube_et_sol())
    r = _client().post("/api/etabli/extraire",
                       json={"job": "job_extr", "version": 1, "noeuds": [0]})
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert (d / "model.v2.glb").is_file()
    assert (d / "model.glb").is_file()          # jamais d'ecrasement


def test_la_route_extraire_refuse_un_job_inconnu():
    r = _client().post("/api/etabli/extraire",
                       json={"job": "nexiste_pas", "version": 1, "noeuds": [0]})
    assert r.status_code == 404
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : les quatre tests échouent en 404 (routes absentes).

- [ ] **Step 3 : implémenter**

Ajouter à la fin de `backend/app/api/routes.py` :

```python
# ── l'Établi : inspection et chirurgie de maillage ───────────────────────────
# Spec docs/superpowers/specs/2026-08-29-etabli-inspecteur-3d-design.md.
# Le navigateur envoie des PARAMÈTRES ; l'écriture du GLB vit ici.

def _etabli_glb(job: str, version: int | None) -> bytes:
    """Les octets d'une version d'un job, ou un 404 parlant."""
    from app.services import mesh_report
    d = mesh_report.job_dir(Path(job).name)
    nom = "model.glb" if not version or int(version) == 1 \
        else f"model.v{int(version)}.glb"
    p = d / nom
    if not p.is_file():
        raise HTTPException(404, f"{Path(job).name}/{nom} introuvable")
    return p.read_bytes()


@router.get("/etabli/sources")
async def etabli_sources(limit: int = 60):
    """La chronologie unifiée : jobs assets3d et tâches Meshy rapatriées."""
    from app.services import mesh_sources
    return {"jobs": mesh_sources.lister(),
            "meshy": await mesh_sources.lister_meshy(limit)}


@router.get("/etabli/rig")
async def etabli_rig(job: str, version: int = 1):
    from app.services import mesh_edit
    return mesh_edit.rig_inventory(_etabli_glb(job, version))


@router.post("/etabli/adopter")
async def etabli_adopter(body: dict):
    """Fait entrer une tâche Meshy dans le monde des jobs (spec §6.2), pour
    qu'une correction ait où être versionnée."""
    from app.services import mesh_edit
    try:
        job = mesh_edit.adopter_meshy(str(body.get("task_id") or ""),
                                      str(body.get("fichier") or "model.glb"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return {"job": job, "version": 1,
            "url": f"/api/assets/3d/{job}/version/1"}


@router.post("/etabli/extraire")
async def etabli_extraire(body: dict):
    from app.services import mesh_edit
    job = Path(str(body.get("job") or "")).name
    noeuds = body.get("noeuds") or []
    if not noeuds:
        raise HTTPException(400, "aucun noeud selectionne")
    data = _etabli_glb(job, body.get("version"))
    try:
        sortie = mesh_edit.extraire(data, noeuds)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return mesh_edit.ecrire_version(job, sortie, operation="extraire",
                                    detail={"noeuds": list(noeuds)})


@router.post("/etabli/transformer")
async def etabli_transformer(body: dict):
    from app.services import mesh_edit
    job = Path(str(body.get("job") or "")).name
    data = _etabli_glb(job, body.get("version"))
    try:
        sortie = mesh_edit.transformer(data, body.get("transforms") or {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return mesh_edit.ecrire_version(
        job, sortie, operation="transformer",
        detail={"transforms": body.get("transforms") or {}})


@router.post("/etabli/reparer")
async def etabli_reparer(body: dict):
    from app.services import mesh_edit
    job = Path(str(body.get("job") or "")).name
    data = _etabli_glb(job, body.get("version"))
    try:
        sortie = mesh_edit.reparer(
            data, axe_haut=body.get("axe_haut"),
            echelle=body.get("echelle"),
            recentrer=bool(body.get("recentrer")))
    except ValueError as e:
        # un GLB compresse refuse le RECENTRAGE seul : le message le dit
        raise HTTPException(400, str(e))
    return mesh_edit.ecrire_version(
        job, sortie, operation="reparer",
        detail={"axe_haut": body.get("axe_haut"),
                "echelle": body.get("echelle"),
                "recentrer": bool(body.get("recentrer"))})
```

- [ ] **Step 4 : relancer le banc complet**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_socle.py
```

Attendu : 37 tests PASS.

- [ ] **Step 5 : vérifier qu'on n'a rien cassé ailleurs**

```bash
.\scripts\run-tests.ps1
```

Attendu : toute la suite au vert. `routes.py` a été modifié — les bancs
`test_asset3d_phase_d.py`, `test_meshy_service.py` et `test_print3d.py` sont
les plus proches et doivent rester verts.

- [ ] **Step 6 : commit**

```bash
git add backend/app/api/routes.py backend/tests/test_etabli_socle.py
git commit -m 'etabli : routes sources, rig, extraire, transformer et reparer' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Ce que P1 laisse volontairement de côté

- **Aucune interface** — c'est P2.
- **Aucun export moteur** — c'est P5. Ne pas ajouter de route `/etabli/export`
  ici : elle a besoin des conventions d'axe et d'échelle par cible, qui sont
  décrites dans le plan P4+P5.
- **Aucune écriture hors de `outputs/`** — le dépôt dans un dossier de projet
  est en P5, avec sa sonde `fs_guard`.
- **Les cinq capacités écartées** (animation, poids, sculpture, UV,
  convergence Plateau) — elles ont leur propre document, et P1 ne doit rien en
  anticiper.
