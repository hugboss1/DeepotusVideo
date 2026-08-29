# L'Établi P4+P5 — le rig regardé, et la pièce emmenée dans un moteur

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** rendre le squelette visible et jugeable avant qu'on paie une
animation — os, hiérarchie, poids d'influence, pose d'essai, lecture des clips
— puis livrer la pièce dans Blender, Godot, Unreal ou Unity.

**Architecture :** le rig est **entièrement au navigateur** (three.js décode
déjà tout ce qu'il faut), et **rien n'y est écrit** : c'est un instrument de
lecture. L'export, lui, est écrit par Python et réutilise `mesh_edit.reparer`
pour les surcharges d'axe et d'échelle — aucune arithmétique de matrice n'est
réécrite.

**Tech Stack :** three.js (`SkeletonHelper`, `AnimationMixer`, skinning GPU),
Python stdlib, `fs_guard` pour la sonde d'écriture, pytest.

---

## Prérequis

**P1 et P2+P3 livrés.** Ce plan remplit les deux panneaux laissés en coquille
(« arrive en P4 », « arrive en P5 ») et consomme `mesh_edit.rig_inventory`,
`mesh_edit.reparer` et `mesh_edit.ecrire_version`.

Spec : `docs/superpowers/specs/2026-08-29-etabli-inspecteur-3d-design.md` §7 et §8.

## Structure de fichiers

| Fichier | Responsabilité |
|---|---|
| **Créer** `frontend/lib3d/rig.js` | squelette, arbre, heatmap des poids, pose d'essai, lecture des clips |
| **Créer** `backend/app/services/mesh_export.py` | cibles moteur, fiche d'import, ouverture d'application, dépôt projet |
| **Modifier** `frontend/etabli/etabli.js` | les panneaux Rig et Export |
| **Modifier** `backend/app/api/routes.py` | `/etabli/export`, `/etabli/ouvrir`, `/etabli/deposer` |
| **Créer** `backend/tests/test_etabli_rig_export.py` | le banc de P4+P5 |

---

# Partie P4 — le rig

## Task 1 : le squelette et sa hiérarchie

**Files:**
- Create: `frontend/lib3d/rig.js`
- Test: `backend/tests/test_etabli_rig_export.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_etabli_rig_export.py` :

```python
"""L'Établi P4+P5 — rig regardé, piece exportee
(plan 2026-08-29-etabli-p4-p5-rig-export).

Bancs miroirs pour le frontend, bancs reels pour l'export. Aucun lancement
d'application : le hook _lancer est monkeypatche (patron _lancer_startfile
de print3d).

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_rig_export.py
"""
import json
import os
import pathlib
import struct
import sys
import tempfile
import zlib

import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _lire(rel: str) -> str:
    return (FRONT / rel).read_text(encoding="utf-8")


def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _job(nom: str) -> pathlib.Path:
    from app.config import settings
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    return d


# ── A. le squelette ──────────────────────────────────────────────────────────

def test_le_module_rig_dessine_le_squelette():
    js = _lire("lib3d/rig.js")
    assert "SkeletonHelper" in js


def test_le_module_rig_n_ecrit_rien():
    """P4 est un instrument de LECTURE : la creation d'animation et la
    peinture des poids sont en phases ulterieures (U1, U2)."""
    js = _lire("lib3d/rig.js")
    assert "fetch" not in js
    assert "/api/etabli/extraire" not in js


def test_l_arbre_des_os_vient_de_l_inventaire_serveur():
    """rig_inventory permet de dire 'aucun squelette' sans telecharger 200 Mo."""
    js = _lire("etabli/etabli.js")
    assert "/api/etabli/rig" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : `FileNotFoundError` sur `lib3d/rig.js`.

- [ ] **Step 3 : implémenter**

Créer `frontend/lib3d/rig.js` :

```js
/* Le rig, REGARDÉ. Ce module ne parle à aucune route et n'écrit rien : il
   montre le squelette, les poids et la déformation pour qu'on juge un rig
   AVANT de payer les animations qui l'utilisent.

   Créer des clips (U1) et repeindre les poids (U2) sont des phases
   ultérieures documentées — ne rien en anticiper ici. */
"use strict";
import * as THREE from "three";

export function poserSquelette(api) {
  retirerSquelette(api);
  const peaux = [];
  api.racine.traverse((o) => { if (o.isSkinnedMesh) peaux.push(o); });
  if (!peaux.length) return { aSquelette: false, os: [] };

  const aides = [];
  for (const p of peaux) {
    const aide = new THREE.SkeletonHelper(p.skeleton.bones[0] || p);
    aide.material.depthTest = false;       /* les os se voient À TRAVERS la peau */
    aide.material.transparent = true;
    aide.renderOrder = 999;
    api.scene.add(aide);
    aides.push(aide);
  }
  api._aidesRig = aides;
  const os = peaux[0].skeleton.bones.map((b, i) => ({
    i, nom: b.name || `os_${i}`, uuid: b.uuid,
    parent: b.parent && b.parent.isBone ? b.parent.name : null,
  }));
  return { aSquelette: true, os, peaux };
}

export function retirerSquelette(api) {
  for (const a of api._aidesRig || []) { api.scene.remove(a); a.dispose?.(); }
  api._aidesRig = [];
}

/* Surligne une chaîne d'os : l'os choisi et toute sa descendance. */
export function surlignerChaine(api, nomOs) {
  for (const aide of api._aidesRig || []) {
    aide.material.color.set(nomOs ? 0x3a4048 : 0xffffff);
  }
  let cible = null;
  api.racine.traverse((o) => { if (o.isBone && o.name === nomOs) cible = o; });
  if (!cible) return [];
  const chaine = [];
  cible.traverse((b) => { if (b.isBone) chaine.push(b.name); });
  return chaine;
}
```

- [ ] **Step 4 : brancher le panneau Rig**

> **Contrat de `rig_inventory` à respecter si tu bâtis un arbre depuis `inv.os`
> plutôt que depuis les os three.js :** `os` ne contient que les JOINTS, donc un
> `os[].parent` peut désigner un nœud **absent** de la liste — cas courant des
> exports Blender et Mixamo, où la racine d'armature porte le déplacement global
> sans être elle-même un os. Traiter un `parent` introuvable comme une racine ;
> ne jamais supposer qu'il se résout dans `os`.

Ajouter à `frontend/etabli/etabli.js` :

```js
/* Import complet dès maintenant : les tâches 2 et 3 câblent la heatmap, la
   pose et les clips dans ce même fichier, et une ligne d'import oubliée
   échouerait à l'exécution sans qu'aucun banc miroir ne le voie. */
import {
  poserSquelette, retirerSquelette, surlignerChaine,
  peindrePoids, retirerPoids,
  memoriserRepos, remettreRepos, tournerOs, lecteurClips,
} from "/lib3d/rig.js";

async function rendreRig() {
  const box = $("#panRig");
  /* L'inventaire serveur répond AVANT le chargement : il permet d'annoncer
     l'absence de squelette sans télécharger le maillage. */
  let inv = { a_squelette: false, os: [], clips: [] };
  if (S.a && S.a.job) {
    try {
      inv = await jget(`/api/etabli/rig?job=${encodeURIComponent(S.a.job)}`
        + `&version=${S.a.version || 1}`);
    } catch { /* une source Meshy n'a pas de fiche job */ }
  }
  const vu = poserSquelette(S.vueA);
  if (!vu.aSquelette && !inv.a_squelette) {
    box.innerHTML = '<div class="vide">ce maillage n\'a pas de squelette — '
      + 'la tâche <b>04 · rig</b> du 3D Studio en pose un</div>';
    return;
  }
  box.innerHTML = `
    <div class="dt-label">${vu.os.length} os</div>
    <div class="os-arbre">${vu.os.map((o) =>
      `<button class="os" data-os="${o.nom}">${o.parent ? "· " : ""}${o.nom}</button>`
    ).join("")}</div>
    <div class="dt-label spaced">Poids d'influence</div>
    <label><input type="checkbox" id="rigHeat"> colorer l'os choisi</label>
    <div class="dt-label spaced">Pose d'essai</div>
    <div class="pose-aide">glisser un os le fait tourner — rien n'est écrit</div>
    <button id="rigRepos">remettre la pose de repos</button>
    <div class="dt-label spaced">Clips</div>
    <div class="clips" id="rigClips"></div>`;
  box.querySelectorAll(".os").forEach((b) =>
    b.addEventListener("click", () => {
      surlignerChaine(S.vueA, b.dataset.os);
      SEL.osCourant = b.dataset.os;
      if ($("#rigHeat").checked) peindrePoids(S.vueA, b.dataset.os);
    }));
}
```

et appeler `rendreRig()` depuis l'écouteur `etabli:charge`.

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 3 tests PASS.

- [ ] **Step 6 : commit**

```bash
git add frontend/lib3d/rig.js frontend/etabli/etabli.js backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : le squelette dessine a travers la peau, avec son arbre d os' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 2 : la heatmap des poids

**Files:**
- Modify: `frontend/lib3d/rig.js`
- Test: `backend/tests/test_etabli_rig_export.py`

C'est l'instrument qui révèle un rig raté : un bras qui tire l'oreille se voit
ici, et sur aucune vignette.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_rig_export.py` :

```python
# ── B. poids d'influence ─────────────────────────────────────────────────────

def test_la_heatmap_lit_les_attributs_de_skinning():
    js = _lire("lib3d/rig.js")
    assert "skinIndex" in js
    assert "skinWeight" in js


def test_la_heatmap_travaille_sur_un_materiau_CLONE():
    """Peindre sur le materiau d'origine abimerait le modele affiche, et la
    couleur survivrait au changement d'etape."""
    js = _lire("lib3d/rig.js")
    assert "clone" in js
    assert "vertexColors" in js


def test_la_heatmap_se_retire():
    js = _lire("lib3d/rig.js")
    assert "retirerPoids" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : les trois nouveaux tests échouent.

- [ ] **Step 3 : implémenter**

Ajouter à `frontend/lib3d/rig.js` :

```js
/* Poids d'influence en couleurs de sommets : bleu = 0, rouge = 1.
   `GLTFLoader` a déjà décodé JOINTS_0 et WEIGHTS_0 — y compris sur un GLB
   Draco, puisque le décodeur est branché. Rien ne remonte au serveur. */
export function peindrePoids(api, nomOs) {
  api.racine.traverse((o) => {
    if (!o.isSkinnedMesh) return;
    const idxOs = o.skeleton.bones.findIndex((b) => b.name === nomOs);
    if (idxOs < 0) return;
    const g = o.geometry;
    const si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
    if (!si || !sw) return;

    const n = si.count;
    const cols = new Float32Array(n * 3);
    for (let v = 0; v < n; v++) {
      let p = 0;
      for (let k = 0; k < 4; k++) {
        if (si.getComponent(v, k) === idxOs) p += sw.getComponent(v, k);
      }
      p = Math.min(Math.max(p, 0), 1);
      cols[v * 3] = p;                    /* rouge  : influence forte      */
      cols[v * 3 + 1] = 0.15;
      cols[v * 3 + 2] = 1 - p;            /* bleu   : influence nulle      */
    }
    g.setAttribute("color", new THREE.BufferAttribute(cols, 3));

    /* Un matériau CLONÉ : peindre sur l'original abîmerait le modèle affiché
       et la couleur survivrait au changement d'étape. */
    if (!o.userData.matOrigine) o.userData.matOrigine = o.material;
    const m = (Array.isArray(o.material) ? o.material[0] : o.material).clone();
    m.vertexColors = true;
    m.map = null;
    m.needsUpdate = true;
    o.material = m;
  });
}

export function retirerPoids(api) {
  api.racine.traverse((o) => {
    if (!o.isSkinnedMesh || !o.userData.matOrigine) return;
    o.material.dispose?.();
    o.material = o.userData.matOrigine;
    o.userData.matOrigine = null;
    o.geometry.deleteAttribute("color");
  });
}
```

Câbler la case `#rigHeat` dans `etabli.js` :

```js
$("#rigHeat").addEventListener("change", (e) => {
  if (e.target.checked && SEL.osCourant) peindrePoids(S.vueA, SEL.osCourant);
  else retirerPoids(S.vueA);
});
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 6 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add frontend/lib3d/rig.js frontend/etabli/etabli.js backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : heatmap des poids d influence sur materiau clone' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 3 : la pose d'essai et la lecture des clips

**Files:**
- Modify: `frontend/lib3d/rig.js`
- Test: `backend/tests/test_etabli_rig_export.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_rig_export.py` :

```python
# ── C. pose et clips ─────────────────────────────────────────────────────────

def test_la_pose_de_repos_est_memorisee_avant_toute_rotation():
    """Sans memoriser le repos, 'annuler' est impossible et l'utilisateur a
    abime son affichage sans recours."""
    js = _lire("lib3d/rig.js")
    assert "poseRepos" in js
    assert "remettreRepos" in js


def test_les_clips_se_lisent_avec_timeline_et_vitesse():
    js = _lire("lib3d/rig.js")
    assert "AnimationMixer" in js
    assert "timeScale" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : les deux nouveaux tests échouent.

- [ ] **Step 3 : implémenter**

Ajouter à `frontend/lib3d/rig.js` :

```js
/* Pose d'essai. Le skinning GPU fait le reste : tourner un os déforme la peau
   immédiatement. RIEN n'est écrit — c'est une répétition, pas une animation
   (créer des clips est la phase ultérieure U1). */
export function memoriserRepos(api) {
  const repos = new Map();
  api.racine.traverse((o) => {
    if (o.isBone) repos.set(o.uuid, o.quaternion.clone());
  });
  api._poseRepos = repos;
  return repos.size;
}

export function remettreRepos(api) {
  for (const [uuid, q] of api._poseRepos || []) {
    api.racine.traverse((o) => { if (o.uuid === uuid) o.quaternion.copy(q); });
  }
}

export function tournerOs(api, nomOs, euler) {
  if (!api._poseRepos) memoriserRepos(api);
  api.racine.traverse((o) => {
    if (o.isBone && o.name === nomOs) {
      o.rotation.set(euler.x || 0, euler.y || 0, euler.z || 0);
    }
  });
}

/* Lecture des clips livrés par Meshy : juger l'animation payée au lieu de la
   deviner. */
export function lecteurClips(api) {
  const clips = (api.gltf && api.gltf.animations) || [];
  if (!clips.length) return { clips: [], jouer: () => {}, arreter: () => {} };
  const mixer = new THREE.AnimationMixer(api.racine);
  const horloge = new THREE.Clock();
  let action = null;
  (function boucle() {
    requestAnimationFrame(boucle);
    mixer.update(horloge.getDelta());
  })();
  return {
    clips: clips.map((c, i) => ({ i, nom: c.name || `clip_${i}`,
                                  duree: Number(c.duration.toFixed(2)) })),
    jouer(i, vitesse = 1) {
      if (action) action.stop();
      action = mixer.clipAction(clips[i]);
      mixer.timeScale = vitesse;
      action.reset().play();
    },
    arreter() { if (action) action.stop(); },
    allerA(t) { mixer.setTime(t); },
  };
}
```

Câbler dans `etabli.js`, à la fin de `rendreRig()` :

```js
memoriserRepos(S.vueA);
$("#rigRepos").addEventListener("click", () => remettreRepos(S.vueA));
const lect = lecteurClips(S.vueA);
$("#rigClips").innerHTML = lect.clips.length
  ? lect.clips.map((c) =>
      `<button class="clip" data-i="${c.i}">${c.nom}<span>${c.duree} s</span></button>`
    ).join("") + '<label>vitesse <input id="rigVit" type="range" min="0.1" '
    + 'max="2" step="0.1" value="1"></label>'
  : '<div class="vide">aucun clip — la tâche <b>05 · animation</b> en produit</div>';
$("#rigClips").querySelectorAll(".clip").forEach((b) =>
  b.addEventListener("click", () =>
    lect.jouer(Number(b.dataset.i), Number($("#rigVit")?.value || 1))));
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 8 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add frontend/lib3d/rig.js frontend/etabli/etabli.js backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : pose d essai avec retour au repos, et lecture des clips livres' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

# Partie P5 — l'export

## Task 4 : les cibles moteur et la fiche d'import

**Files:**
- Create: `backend/app/services/mesh_export.py`
- Test: `backend/tests/test_etabli_rig_export.py`

**Le défaut est le glTF standard pour les quatre cibles.** Les importeurs de
Blender et d'Unreal convertissent l'axe eux-mêmes ; pré-cuire la conversion
produirait un modèle tourné deux fois. Ce que l'export apporte est le bon
format, une échelle déclarée, la fiche qui dit ce que le moteur fera, et le
chemin de dépôt.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_rig_export.py` :

```python
# ── D. cibles moteur ─────────────────────────────────────────────────────────

def test_les_quatre_cibles_sont_declarees():
    from app.services import mesh_export
    assert set(mesh_export.CIBLES) == {"blender", "godot", "unreal", "unity"}


def test_le_defaut_est_le_gltf_standard_partout():
    """Blender et Unreal convertissent EUX-MEMES : pre-cuire l'axe tournerait
    le modele deux fois."""
    from app.services import mesh_export
    for nom, c in mesh_export.CIBLES.items():
        assert c["format"] == "glb", nom
        assert c["axe_haut"] == "Y", nom
        assert c["echelle"] == 1.0, nom


def test_unity_annonce_son_greffon():
    from app.services import mesh_export
    assert "glTFast" in mesh_export.CIBLES["unity"]["note"]


def test_exporter_ecrit_le_fichier_et_sa_fiche():
    from app.services import mesh_export
    d = _job("job_exp")
    r = mesh_export.exporter("job_exp", 1, "godot")
    sortie = pathlib.Path(r["chemin"])
    assert sortie.is_file()
    assert sortie.suffix == ".glb"
    fiche = sortie.parent / "import.md"
    assert fiche.is_file()
    assert "Godot" in fiche.read_text(encoding="utf-8")
    assert (d / "model.glb").is_file()          # la source est intacte


def test_une_surcharge_d_axe_passe_par_mesh_edit_reparer():
    """Pas de seconde arithmetique de matrice dans le depot."""
    from app.services import mesh_export, print3d
    _job("job_axe")
    r = mesh_export.exporter("job_axe", 1, "unreal", axe_haut="Z", echelle=100.0)
    tris = print3d.lire_glb_triangles(pathlib.Path(r["chemin"]).read_bytes())
    (x0, x1), _, _ = print3d.bbox(tris)
    assert abs(x1 - 100.0) < 1e-3        # le cube unite fait 100 en centimetres


def test_le_fbx_n_est_propose_que_s_il_existe_deja():
    """Le depot ne sait pas ECRIRE de FBX : format ferme Autodesk."""
    from app.services import mesh_export
    d = _job("job_fbx")
    assert mesh_export.fbx_disponible("job_fbx") is False
    (d / "model.fbx").write_bytes(b"faux fbx du banc")
    assert mesh_export.fbx_disponible("job_fbx") is True


def test_exporter_refuse_une_cible_inconnue():
    from app.services import mesh_export
    _job("job_ko")
    with pytest.raises(ValueError, match="cible inconnue"):
        mesh_export.exporter("job_ko", 1, "cryengine")
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : `ModuleNotFoundError: No module named 'app.services.mesh_export'`.

- [ ] **Step 3 : implémenter**

Créer `backend/app/services/mesh_export.py` :

```python
# -*- coding: utf-8 -*-
"""Emmener la pièce dans un moteur.

Ce ne sont pas des cibles réseau : ce sont des formats et des conventions
d'import. Le défaut est le **glTF standard** pour les quatre — Blender et
Unreal convertissent l'axe eux-mêmes, et pré-cuire la conversion produirait un
modèle tourné deux fois. Ce que ce module apporte est le bon format, une
échelle déclarée, la fiche qui dit ce que le moteur fera, et le chemin.

Le FBX n'est jamais ÉCRIT ici : format fermé d'Autodesk, hors de portée de la
stdlib. Il n'est proposé que là où un fournisseur l'a déjà livré.
"""
from __future__ import annotations

from pathlib import Path

CIBLES: dict[str, dict] = {
    "blender": {
        "nom": "Blender 4", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Import natif (File > Import > glTF 2.0). L'option « +Y up » "
                "est active par défaut et convertit vers le Z-up de Blender — "
                "le fichier est donc livré en glTF standard, sans rotation "
                "pré-cuite.",
    },
    "godot": {
        "nom": "Godot 4", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Godot est Y-up comme glTF : rien à convertir. Déposer le "
                "fichier dans le dossier du projet (res://) suffit, "
                "l'import est automatique.",
    },
    "unreal": {
        "nom": "Unreal Engine 5", "format": "glb", "axe_haut": "Y",
        "echelle": 1.0,
        "note": "Interchange importe glTF nativement et fait lui-même la "
                "conversion vers Z-up et l'échelle centimètre. Déposer dans "
                "Content/. Ne PAS pré-cuire l'axe : ce serait une double "
                "rotation.",
    },
    "unity": {
        "nom": "Unity 6", "format": "glb", "axe_haut": "Y", "echelle": 1.0,
        "note": "Unity n'importe pas glTF sans greffon. Installer glTFast "
                "(gratuit, standard, via Package Manager) puis déposer le "
                "fichier dans Assets/. Sans greffon, seul un FBX entre — et "
                "il n'existe que si le fournisseur en a livré un.",
    },
}


def dossier_exports(job: str) -> Path:
    from app.services import mesh_report
    d = mesh_report.job_dir(job) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fbx_disponible(job: str) -> bool:
    """Un FBX n'existe que si Meshy, Tripo ou Rodin en a livré un."""
    from app.services import mesh_report
    return (mesh_report.job_dir(job) / "model.fbx").is_file()


def _source(job: str, version: int) -> bytes:
    from app.services import mesh_report
    nom = "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"
    p = mesh_report.job_dir(job) / nom
    if not p.is_file():
        raise FileNotFoundError(f"{job}/{nom} introuvable")
    return p.read_bytes()


def _fiche(cible: str, fichier: str, axe: str, echelle: float) -> str:
    c = CIBLES[cible]
    surcharge = ""
    if axe != c["axe_haut"] or float(echelle) != float(c["echelle"]):
        surcharge = (f"\n> **Surcharge explicite appliquée** : axe haut {axe}, "
                     f"échelle ×{echelle}. Le défaut de cette cible est "
                     f"{c['axe_haut']}-up à l'échelle 1. Vérifie que ton "
                     f"importeur ne refait pas la conversion.\n")
    return (f"# Importer dans {c['nom']}\n\n"
            f"**Fichier :** `{fichier}`  \n"
            f"**Format :** {c['format']}  \n"
            f"**Axe haut écrit :** {axe}  \n"
            f"**Échelle :** ×{echelle} (1 unité = 1 mètre)\n\n"
            f"{c['note']}\n{surcharge}")


def exporter(job: str, version: int, cible: str, *,
             axe_haut: str | None = None,
             echelle: float | None = None) -> dict:
    """Écrit la pièce prête pour un moteur, et sa fiche d'import.

    Les surcharges d'axe et d'échelle passent par `mesh_edit.reparer` : aucune
    seconde arithmétique de matrice n'existe dans le dépôt.
    """
    from app.services import mesh_edit

    job = Path(job).name
    if cible not in CIBLES:
        raise ValueError(f"cible inconnue : {cible} "
                         f"(attendu {', '.join(sorted(CIBLES))})")
    c = CIBLES[cible]
    axe = (axe_haut or c["axe_haut"]).upper()
    ech = float(c["echelle"] if echelle is None else echelle)

    data = _source(job, version)
    if axe != "Y" or ech != 1.0:
        data = mesh_edit.reparer(data, axe_haut=axe, echelle=ech)

    d = dossier_exports(job)
    nom = f"{job}_v{int(version)}_{cible}.{c['format']}"
    (d / nom).write_bytes(data)
    (d / "import.md").write_text(_fiche(cible, nom, axe, ech), encoding="utf-8")
    return {
        "cible": cible, "chemin": str(d / nom), "fichier": nom,
        "bytes": len(data), "axe_haut": axe, "echelle": ech,
        "fiche": str(d / "import.md"),
        "url": f"/api/assets/3d/{job}/export/{nom}",
        "fbx_disponible": fbx_disponible(job),
    }
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 15 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_export.py backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : quatre cibles moteur en glTF standard, fiche d import, FBX seulement s il existe' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 5 : ouvrir l'application, déposer dans le projet

**Files:**
- Modify: `backend/app/services/mesh_export.py`
- Test: `backend/tests/test_etabli_rig_export.py`

Deux gestes de nature différente, et le plan ne fait pas semblant du
contraire : « ouvrir » est réel pour Blender, alors qu'Unity, Unreal et Godot
importent **par dossier**. Le dépôt est par ailleurs **la seule écriture hors
de `outputs/`** de tout le chantier, donc la seule qui a besoin d'une sonde.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_rig_export.py` :

```python
# ── E. ouvrir et deposer ─────────────────────────────────────────────────────

def test_blender_est_lance_avec_un_import_reel(monkeypatch):
    """Pour Blender, 'ouvrir' veut vraiment dire ouvrir : --python-expr
    importe le glTF au lancement."""
    from app.services import mesh_export
    _job("job_open")
    r = mesh_export.exporter("job_open", 1, "blender")
    vus = {}
    monkeypatch.setattr(mesh_export, "_lancer",
                        lambda argv: vus.setdefault("argv", argv))
    monkeypatch.setenv("BLENDER_PATH", "C:/faux/blender.exe")
    mesh_export.ouvrir("blender", r["chemin"])
    assert vus["argv"][0] == "C:/faux/blender.exe"
    assert any("import_scene.gltf" in str(a) for a in vus["argv"])


def test_les_trois_autres_moteurs_ouvrent_le_PROJET(monkeypatch):
    """Ouvrir une app sur un fichier n'existe pas pour Unity, Unreal et
    Godot : le bouton dit ce qu'il fait."""
    from app.services import mesh_export
    assert mesh_export.geste_ouvrir("blender") == "fichier"
    for c in ("unity", "unreal", "godot"):
        assert mesh_export.geste_ouvrir(c) == "projet"


def test_ouvrir_sans_chemin_configure_refuse_parlant(monkeypatch):
    from app.services import mesh_export
    monkeypatch.delenv("BLENDER_PATH", raising=False)
    with pytest.raises(RuntimeError, match="BLENDER_PATH"):
        mesh_export.ouvrir("blender", "x.glb")


def test_deposer_sonde_la_visibilite_avant_de_declarer_le_succes(monkeypatch):
    """L'incident MSIX : une ecriture peut sembler reussir en partant dans un
    overlay invisible. Un depot qui ne se voit pas est un depot rate."""
    from app.services import mesh_export
    _job("job_dep")
    r = mesh_export.exporter("job_dep", 1, "unity")
    cible = pathlib.Path(_tmp) / "projet_unity" / "Assets"
    cible.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("UNITY_PROJECT_DIR", str(cible))
    monkeypatch.setattr(mesh_export, "_sonder", lambda d: False)
    with pytest.raises(RuntimeError, match="invisible"):
        mesh_export.deposer("unity", r["chemin"])
    monkeypatch.setattr(mesh_export, "_sonder", lambda d: True)
    out = mesh_export.deposer("unity", r["chemin"])
    assert pathlib.Path(out["chemin"]).is_file()


def test_deposer_refuse_un_dossier_non_configure(monkeypatch):
    from app.services import mesh_export
    monkeypatch.delenv("GODOT_PROJECT_DIR", raising=False)
    with pytest.raises(RuntimeError, match="GODOT_PROJECT_DIR"):
        mesh_export.deposer("godot", "x.glb")
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : `AttributeError` sur `ouvrir`, `geste_ouvrir`, `deposer`.

- [ ] **Step 3 : implémenter**

Ajouter à `backend/app/services/mesh_export.py` :

```python
import shutil

# Les chemins vivent dans l'environnement, comme SLICER_PATH de print3d — pas
# dans Settings : c'est le patron déjà éprouvé du dépôt pour un exécutable
# local que tout le monde n'a pas.
EXE_ENV = {"blender": "BLENDER_PATH", "unity": "UNITY_PATH",
           "unreal": "UNREAL_PATH", "godot": "GODOT_PATH"}
PROJET_ENV = {"blender": "BLENDER_PROJECT_DIR", "unity": "UNITY_PROJECT_DIR",
              "unreal": "UNREAL_PROJECT_DIR", "godot": "GODOT_PROJECT_DIR"}


def geste_ouvrir(cible: str) -> str:
    """Ce que « ouvrir » veut dire pour cette cible, et rien de plus.

    Blender ouvre vraiment un FICHIER. Unity, Unreal et Godot importent par
    dossier : leur bouton s'appelle « ouvrir le projet », parce que c'est ce
    qu'il fait.
    """
    return "fichier" if cible == "blender" else "projet"


def _lancer(argv: list) -> None:      # pragma: no cover — monkeypatché au banc
    import subprocess
    subprocess.Popen([str(a) for a in argv])


def ouvrir(cible: str, chemin: str) -> dict:
    import os
    if cible not in CIBLES:
        raise ValueError(f"cible inconnue : {cible}")
    cle = EXE_ENV[cible]
    exe = os.environ.get(cle, "").strip()
    if not exe:
        raise RuntimeError(
            f"{cle} n'est pas renseigné — pose le chemin de l'exécutable "
            f"dans le .env pour ouvrir {CIBLES[cible]['nom']} d'ici.")
    if cible == "blender":
        # --python-expr : Blender importe le glTF au lancement. C'est ce qui
        # fait que « ouvrir » n'est pas un mensonge pour cette cible.
        expr = ("import bpy; bpy.ops.import_scene.gltf(filepath=r'%s')"
                % str(chemin))
        _lancer([exe, "--python-expr", expr])
        return {"geste": "fichier", "exe": exe}
    dossier = os.environ.get(PROJET_ENV[cible], "").strip()
    _lancer([exe, dossier] if dossier else [exe])
    return {"geste": "projet", "exe": exe, "projet": dossier or None}


def _sonder(dossier) -> bool:         # pragma: no cover — monkeypatché au banc
    from app.services import fs_guard
    return fs_guard.probe_write_visibility(Path(dossier))


def deposer(cible: str, chemin: str) -> dict:
    """Copie l'export dans le dossier de projet du moteur.

    SEULE écriture hors de `outputs/` du chantier, donc la seule qui a besoin
    d'une sonde. L'incident MSIX de juin-juillet 2026 a montré qu'une écriture
    peut sembler réussir tout en partant dans un overlay invisible : déposer
    un asset dans un projet Unity est exactement ce cas-là.
    """
    import os
    if cible not in CIBLES:
        raise ValueError(f"cible inconnue : {cible}")
    cle = PROJET_ENV[cible]
    dossier = os.environ.get(cle, "").strip()
    if not dossier:
        raise RuntimeError(
            f"{cle} n'est pas renseigné — indique le dossier du projet "
            f"{CIBLES[cible]['nom']} (aucune valeur par défaut : ce dépôt "
            f"n'écrit pas hors de ses sorties sans qu'on le lui demande).")
    d = Path(dossier)
    if not d.is_dir():
        raise RuntimeError(f"{cle} pointe vers un dossier inexistant : {d}")
    if not _sonder(d):
        raise RuntimeError(
            f"écriture invisible dans {d} — le processus est virtualisé "
            f"(MSIX) et le fichier n'apparaîtrait pas pour le moteur. "
            f"Relance l'application hors du conteneur.")
    src = Path(chemin)
    dest = d / src.name
    shutil.copy2(src, dest)
    fiche = src.parent / "import.md"
    if fiche.is_file():
        shutil.copy2(fiche, d / "import.md")
    return {"chemin": str(dest), "dossier": str(d), "visible": True}
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 20 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/mesh_export.py backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : ouvrir Blender sur le fichier, ouvrir le projet ailleurs, deposer sous sonde' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 6 : les routes et le panneau Export

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `frontend/etabli/etabli.js`
- Test: `backend/tests/test_etabli_rig_export.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_rig_export.py` :

```python
# ── F. routes et panneau ─────────────────────────────────────────────────────

def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_la_route_export_ecrit_et_rend_le_chemin():
    _job("job_route_exp")
    r = _client().post("/api/etabli/export",
                       json={"job": "job_route_exp", "version": 1,
                             "cible": "blender"})
    assert r.status_code == 200
    assert pathlib.Path(r.json()["chemin"]).is_file()


def test_la_route_export_refuse_une_cible_inconnue():
    _job("job_route_ko")
    r = _client().post("/api/etabli/export",
                       json={"job": "job_route_ko", "version": 1,
                             "cible": "cryengine"})
    assert r.status_code == 400


def test_la_route_cibles_annonce_les_gestes():
    r = _client().get("/api/etabli/cibles")
    assert r.status_code == 200
    c = r.json()["cibles"]
    assert c["blender"]["geste_ouvrir"] == "fichier"
    assert c["godot"]["geste_ouvrir"] == "projet"


def test_le_panneau_export_montre_les_quatre_cibles():
    js = _lire("etabli/etabli.js")
    for c in ("blender", "godot", "unreal", "unity"):
        assert c in js
    assert "/api/etabli/export" in js


def test_le_panneau_dit_la_verite_sur_le_fbx():
    js = _lire("etabli/etabli.js")
    assert "fbx" in js.lower()
    assert "crédit" in js or "credit" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 404 sur les routes, marqueurs absents du panneau.

- [ ] **Step 3 : ajouter les routes**

Ajouter à `backend/app/api/routes.py`, à la suite des routes `/etabli/*` de P1 :

```python
@router.get("/etabli/cibles")
async def etabli_cibles():
    """Les cibles moteur, avec le GESTE que chacune supporte vraiment."""
    from app.services import mesh_export
    return {"cibles": {k: {**v, "geste_ouvrir": mesh_export.geste_ouvrir(k)}
                       for k, v in mesh_export.CIBLES.items()}}


@router.post("/etabli/export")
async def etabli_export(body: dict):
    from app.services import mesh_export
    try:
        return mesh_export.exporter(
            str(body.get("job") or ""), int(body.get("version") or 1),
            str(body.get("cible") or ""),
            axe_haut=body.get("axe_haut"), echelle=body.get("echelle"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/etabli/ouvrir")
async def etabli_ouvrir(body: dict):
    from app.services import mesh_export
    try:
        return mesh_export.ouvrir(str(body.get("cible") or ""),
                                  str(body.get("chemin") or ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))


@router.post("/etabli/deposer")
async def etabli_deposer(body: dict):
    from app.services import mesh_export
    try:
        return mesh_export.deposer(str(body.get("cible") or ""),
                                   str(body.get("chemin") or ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        # dossier absent, non configuré, ou ÉCRITURE INVISIBLE : le message
        # dit lequel des trois
        raise HTTPException(409, str(e))


@router.get("/assets/3d/{job}/export/{fname}")
async def assets3d_export_file(job: str, fname: str):
    from app.services import mesh_export
    p = mesh_export.dossier_exports(Path(job).name) / Path(fname).name
    if not p.is_file():
        raise HTTPException(404, "export introuvable")
    return FileResponse(str(p))
```

- [ ] **Step 4 : brancher le panneau Export**

Ajouter à `frontend/etabli/etabli.js` :

```js
async function rendreExport() {
  const { cibles } = await jget("/api/etabli/cibles");
  const dernier = {};
  $("#panExport").innerHTML = Object.entries(cibles).map(([id, c]) => `
    <section class="cible" data-cible="${id}">
      <div class="cible-tete"><b>${c.nom}</b><span>${c.format}</span></div>
      <p class="cible-note">${c.note}</p>
      <div class="cible-actions">
        <button data-a="preparer">Préparer</button>
        <button data-a="ouvrir">${c.geste_ouvrir === "fichier"
          ? "Ouvrir l'application" : "Ouvrir le projet"}</button>
        <button data-a="deposer">Déposer dans le projet</button>
        <button data-a="url">Copier l'URL</button>
      </div>
      <div class="cible-etat"></div>
    </section>`).join("")
    + `<p class="note">Le <b>FBX</b> n'est jamais écrit ici : format fermé
       d'Autodesk. Il n'apparaît que si un fournisseur en a livré un avec le
       job, ou via une conversion Meshy à <b>1 crédit</b>, qui passe par la
       porte de coût habituelle.</p>`;

  $("#panExport").querySelectorAll(".cible").forEach((sec) => {
    const id = sec.dataset.cible, etat = sec.querySelector(".cible-etat");
    sec.querySelectorAll("[data-a]").forEach((b) =>
      b.addEventListener("click", async () => {
        try {
          if (b.dataset.a === "preparer") {
            dernier[id] = await jpost("/api/etabli/export",
              { job: S.a.job, version: S.a.version || 1, cible: id });
            etat.textContent = `écrit : ${dernier[id].fichier}`;
            return;
          }
          if (!dernier[id]) { etat.textContent = "prépare d'abord le fichier"; return; }
          if (b.dataset.a === "url") {
            await navigator.clipboard.writeText(
              location.origin + dernier[id].url);
            etat.textContent = "URL copiée";
            return;
          }
          const r = await jpost(`/api/etabli/${b.dataset.a}`,
            { cible: id, chemin: dernier[id].chemin });
          etat.textContent = b.dataset.a === "deposer"
            ? `déposé et vérifié : ${r.chemin}` : `lancé (${r.geste})`;
        } catch (e) {
          etat.textContent = String(e.message || e);
        }
      }));
  });
}
```

et l'appeler depuis l'écouteur `etabli:charge`.

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_rig_export.py
```

Attendu : 25 tests PASS.

- [ ] **Step 6 : lancer la suite complète**

```bash
.\scripts\run-tests.ps1
```

Attendu : tout au vert.

- [ ] **Step 7 : commit**

```bash
git add backend/app/api/routes.py frontend/etabli/etabli.js backend/tests/test_etabli_rig_export.py
git commit -m 'etabli : routes export, ouvrir et deposer, panneau des quatre cibles' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Vérification à l'écran (utilisateur)

**Ne pas lancer le backend depuis l'agent.** Préparer, puis demander la
relance et vérifier sur `/etabli/` :

1. charger une étape **rig** d'une tâche Meshy : les os apparaissent à travers
   la peau, et l'arbre les liste ;
2. cocher « colorer l'os choisi » : le maillage passe en bleu-rouge autour de
   l'os sélectionné ;
3. tourner un os déforme la peau, et « remettre la pose de repos » l'annule ;
4. un clip d'animation se joue, la vitesse répond ;
5. « Préparer » pour Godot écrit un `.glb` et un `import.md` lisible ;
6. « Déposer » sans `GODOT_PROJECT_DIR` refuse **en nommant la variable**.

## Ce que P4+P5 laisse aux phases ultérieures

Rien de ce qui suit ne doit apparaître dans ce plan — chacun a son analyse
dans `2026-08-29-etabli-phases-ulterieures.md` :

**U1** création de clips · **U2** peinture des poids · **U3** sculpture et
retopologie (verdict : router vers Blender, ne pas construire) · **U4**
matériaux et UV · **U5** convergence du Plateau.
