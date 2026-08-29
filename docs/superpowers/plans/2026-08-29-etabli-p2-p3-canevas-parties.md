# L'Établi P2+P3 — le grand canevas, la chronologie des étapes et les Parties

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer la page `/etabli` — un canevas three.js plein écran où l'on
charge le modèle à n'importe laquelle de ses étapes, où l'on compare deux
étapes côte à côte sur des chiffres, et où l'on isole, sépare et transforme des
parties du maillage.

**Architecture :** three.js vendorisé localement dans `frontend/dist/assets/three/`,
un module partagé `frontend/lib3d/viewer.js` (canevas, chargement, cadrage) et
une page vanilla `frontend/etabli/` hors du bundle minifié. **Le navigateur
n'écrit jamais un GLB** : il appelle les routes `/api/etabli/*` livrées par P1,
qui sont les seules plumes.

**Tech Stack :** three.js (module ES, servi localement), JavaScript vanilla,
FastAPI pour les montages statiques, pytest pour les bancs miroirs.

---

## Prérequis

**P1 doit être livré** (`2026-08-29-etabli-p1-socle-serveur.md`) : ce plan
consomme `/api/etabli/sources`, `/extraire`, `/transformer` et `/reparer`.

Spec de référence : `docs/superpowers/specs/2026-08-29-etabli-inspecteur-3d-design.md`,
sections 3, 4, 5 et 6. Les cinq capacités écartées sont dans
`2026-08-29-etabli-phases-ulterieures.md` — **ne rien en anticiper ici**.

## Structure de fichiers

| Fichier | Responsabilité |
|---|---|
| **Créer** `frontend/dist/assets/three/` | three.js et ses addons, vendorisés et épinglés |
| **Créer** `frontend/lib3d/viewer.js` | canevas partagé : renderer, scène, caméra, contrôles, chargement, cadrage |
| **Créer** `frontend/lib3d/selection.js` | parcours du graphe glTF, sélection par nœud / maillage / matériau, isolation |
| **Créer** `frontend/etabli/index.html` | la coque : canevas au centre, chronologie à gauche, onglets à droite |
| **Créer** `frontend/etabli/etabli.css` | mise en page et jetons visuels |
| **Créer** `frontend/etabli/etabli.js` | l'état de la page et le câblage aux routes |
| **Modifier** `backend/app/main.py` | montages `/etabli` et `/lib3d` |
| **Modifier** `frontend/studio3d/studio3d.js` | le nœud `07 · établi` et l'élargissement de la `viewBox` |
| **Créer** `backend/tests/test_etabli_canevas.py` | bancs miroirs (patron `test_library_picker.py`) |

`viewer.js` et `selection.js` vivent dans `lib3d/` **et non dans la page** :
c'est la précondition écrite d'avance de la convergence du Plateau (spec §12).

---

## Task 1 : vendoriser three.js et l'épingler

**Files:**
- Create: `frontend/dist/assets/three/` (fichiers téléchargés)
- Create: `frontend/dist/assets/three/VERSION.txt`
- Create: `backend/tests/test_etabli_canevas.py`

Aucun CDN : l'application doit fonctionner sans réseau, exactement comme
`model-viewer.min.js` (956 Ko) qui vit déjà là.

- [ ] **Step 1 : télécharger et poser les fichiers**

Récupérer depuis la distribution officielle npm du paquet `three` (par exemple
via `npm pack three` puis extraction, ou depuis unpkg) **une seule version**, et
poser exactement ces fichiers :

```
frontend/dist/assets/three/three.module.min.js
frontend/dist/assets/three/addons/loaders/GLTFLoader.js
frontend/dist/assets/three/addons/controls/OrbitControls.js
frontend/dist/assets/three/addons/controls/TransformControls.js
frontend/dist/assets/three/addons/libs/meshopt_decoder.module.js
frontend/dist/assets/three/addons/loaders/DRACOLoader.js
frontend/dist/assets/three/addons/libs/draco/          (dossier des décodeurs)
```

Les décodeurs ne sont pas un confort : sans eux un GLB compressé s'affiche noir
au lieu de s'afficher.

Les addons importent `three` par un specifier nu. Créer donc
`frontend/dist/assets/three/importmap.json` avec le contenu exact :

```json
{
  "imports": {
    "three": "/assets/three/three.module.min.js",
    "three/addons/": "/assets/three/addons/"
  }
}
```

- [ ] **Step 2 : enregistrer la version et les poids MESURÉS**

La spec annonce « environ 800 Ko, à mesurer » : c'est ici qu'on mesure.

```bash
find frontend/dist/assets/three -type f -name '*.js' -exec ls -l {} \; | awk '{s+=$5} END {print s" octets"}'
```

Écrire `frontend/dist/assets/three/VERSION.txt` avec la version exacte du
paquet, la date, le total mesuré en octets, et la ligne de comparaison
`model-viewer.min.js = 956649 octets`.

- [ ] **Step 3 : écrire le banc qui épingle la vendorisation**

Créer `backend/tests/test_etabli_canevas.py` :

```python
"""L'Établi P2+P3 — canevas, chronologie et Parties
(plan 2026-08-29-etabli-p2-p3-canevas-parties).

Bancs MIROIRS : ils lisent les fichiers frontend comme du texte et y épinglent
des marqueurs. Patron de test_library_picker.py — c'est ainsi que le dépôt
garde un frontend vanilla sans navigateur au banc.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_canevas.py
"""
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"


def _lire(rel: str) -> str:
    return (FRONT / rel).read_text(encoding="utf-8")


# ── A. three.js vendorisé ────────────────────────────────────────────────────

def test_three_est_vendorise_et_non_pointe_vers_un_cdn():
    trois = FRONT / "dist" / "assets" / "three"
    assert (trois / "three.module.min.js").is_file()
    assert (trois / "addons" / "loaders" / "GLTFLoader.js").is_file()
    assert (trois / "addons" / "controls" / "OrbitControls.js").is_file()
    assert (trois / "addons" / "controls" / "TransformControls.js").is_file()
    # un moteur de rendu tronqué serait pire qu'absent
    assert (trois / "three.module.min.js").stat().st_size > 100_000


def test_les_decodeurs_de_compression_sont_la():
    """Sans eux, un GLB Draco ou meshopt s'affiche NOIR au lieu de s'afficher."""
    addons = FRONT / "dist" / "assets" / "three" / "addons"
    assert (addons / "libs" / "meshopt_decoder.module.js").is_file()
    assert (addons / "loaders" / "DRACOLoader.js").is_file()
    assert (addons / "libs" / "draco").is_dir()


def test_l_importmap_resout_les_specifiers_nus():
    trois = FRONT / "dist" / "assets" / "three"
    carte = json.loads((trois / "importmap.json").read_text("utf-8"))
    assert carte["imports"]["three"] == "/assets/three/three.module.min.js"
    assert carte["imports"]["three/addons/"] == "/assets/three/addons/"


def test_la_version_et_le_poids_sont_consignes():
    """La spec promettait de MESURER le poids plutot que de l'estimer."""
    txt = (FRONT / "dist" / "assets" / "three" / "VERSION.txt").read_text("utf-8")
    assert "octets" in txt
    assert "model-viewer" in txt
```

- [ ] **Step 4 : lancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 4 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add frontend/dist/assets/three backend/tests/test_etabli_canevas.py
git commit -m 'etabli : three.js vendorise localement, decodeurs compris, poids mesure' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 2 : monter `/etabli` et `/lib3d`

**Files:**
- Modify: `backend/app/main.py` (après le bloc `/studio3d`, ligne ~444)
- Create: `frontend/etabli/index.html`
- Create: `frontend/lib3d/viewer.js` (coquille)
- Test: `backend/tests/test_etabli_canevas.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── B. montages ──────────────────────────────────────────────────────────────

def _client():
    import os
    import sys
    import tempfile
    _tmp = tempfile.mkdtemp()
    os.environ.setdefault("FAL_KEY", "test-key")
    os.environ["DATABASE_URL"] = \
        f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
    os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
    os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
    os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
    pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
    sys.path.insert(0, str(RACINE / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_la_page_etabli_est_servie():
    r = _client().get("/etabli/")
    assert r.status_code == 200
    assert "etabli.js" in r.text


def test_lib3d_est_servi_et_partageable():
    """viewer.js vit hors de la page : c'est la precondition ecrite d'avance
    de la convergence du Plateau (spec §12)."""
    r = _client().get("/lib3d/viewer.js")
    assert r.status_code == 200
    assert "creerCanevas" in r.text
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : les deux nouveaux tests en 404.

- [ ] **Step 3 : monter les deux dossiers**

Ajouter à `backend/app/main.py`, juste après le bloc `/studio3d` (qui se termine
par `logger.info(f"Serving studio3d from {_studio3d}")`) :

```python
# ── /etabli : l'inspecteur 3D en bout de chaîne du 3D Studio ─────────────────
# Même patron standalone que /studio3d — HORS du bundle minifié. La page pilote
# three.js (servi depuis /assets/three) ; l'écriture des GLB reste au serveur.
_etabli = Path(__file__).resolve().parent.parent.parent / "frontend" / "etabli"
if _etabli.is_dir():
    from fastapi.staticfiles import StaticFiles as _SFEt

    class _EtabliStatic(_SFEt):
        """no-cache comme /studio3d : etabli.js garde un nom stable, donc le
        navigateur doit revalider au lieu de servir une version périmée."""
        async def get_response(self, path, scope):
            resp = await super().get_response(path, scope)
            try:
                resp.headers["Cache-Control"] = "no-cache, must-revalidate"
            except Exception:
                pass
            return resp

    app.mount("/etabli", _EtabliStatic(directory=str(_etabli), html=True),
              name="etabli")

    @app.get("/etabli", include_in_schema=False)
    async def _etabli_no_slash():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/etabli/", status_code=307)

    logger.info(f"Serving etabli from {_etabli}")

# ── /lib3d : le canevas 3D PARTAGÉ (Établi aujourd'hui, Plateau le jour où) ──
_lib3d = Path(__file__).resolve().parent.parent.parent / "frontend" / "lib3d"
if _lib3d.is_dir():
    from fastapi.staticfiles import StaticFiles as _SFL3
    app.mount("/lib3d", _SFL3(directory=str(_lib3d)), name="lib3d")
    logger.info(f"Serving lib3d from {_lib3d}")
```

- [ ] **Step 4 : créer la coque de page**

Créer `frontend/etabli/index.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Établi — Deepotus Video Gen</title>
<link rel="stylesheet" href="etabli.css">
<script type="importmap" src="/assets/three/importmap.json"></script>
</head>
<body>
<div class="etabli" id="etabli">

  <!-- ══════════ gauche : la vie du modèle ══════════ -->
  <aside class="rail-left">
    <div class="dt-label">La vie du modèle</div>
    <div class="chrono" id="chrono">
      <div class="chrono-vide">chargement…</div>
    </div>
    <div class="chrono-aide">
      clic : charger · <b>alt-clic</b> : comparer
    </div>
  </aside>

  <!-- ══════════ centre : le grand canevas ══════════ -->
  <main class="centre">
    <header class="head">
      <span class="head-title">Établi</span>
      <span class="head-chip" id="chipSource">—</span>
      <div class="head-right">
        <button id="btnCompare" title="Fermer la comparaison">A/B ✕</button>
      </div>
    </header>

    <div class="vues" id="vues">
      <div class="vue" id="vueA"><canvas></canvas><span class="vue-tag">A</span></div>
      <div class="vue hidden" id="vueB"><canvas></canvas><span class="vue-tag">B</span></div>
    </div>

    <div class="ecart hidden" id="ecart"></div>

    <footer class="barre" id="barre">
      <span id="barreFichier">aucun modèle chargé</span>
      <span id="barreGeo">—</span>
      <span class="barre-attente" id="barreAttente"></span>
    </footer>
  </main>

  <!-- ══════════ droite : les onglets ══════════ -->
  <aside class="rail-right">
    <div class="onglets">
      <button class="on actif" data-onglet="parties">Parties</button>
      <button class="on" data-onglet="rig">Rig</button>
      <button class="on" data-onglet="fiche">Fiche</button>
      <button class="on" data-onglet="export">Export</button>
    </div>
    <div class="panneau" id="panParties"></div>
    <div class="panneau hidden" id="panRig">
      <div class="vide">le panneau Rig arrive en P4</div>
    </div>
    <div class="panneau hidden" id="panFiche"></div>
    <div class="panneau hidden" id="panExport">
      <div class="vide">l'export par moteur arrive en P5</div>
    </div>
  </aside>
</div>
<script type="module" src="etabli.js"></script>
</body>
</html>
```

- [ ] **Step 5 : créer la coquille de `viewer.js`**

Créer `frontend/lib3d/viewer.js` :

```js
/* Canevas 3D PARTAGÉ du dépôt.
   Il vit ici, et non dans /etabli, parce que la spec §12 écrit d'avance la
   condition de convergence : le jour où le Plateau réclame des gizmos, il
   migre vers CE canevas plutôt que d'en faire naître un second. */
"use strict";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export function creerCanevas(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14161a);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);
  camera.position.set(2.5, 1.8, 3.2);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(3, 5, 2);
  scene.add(key);

  const api = { renderer, scene, camera, controls, racine: null };

  function redimensionner() {
    const w = canvas.clientWidth || 1, h = canvas.clientHeight || 1;
    if (canvas.width !== w || canvas.height !== h) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }
  (function boucle() {
    requestAnimationFrame(boucle);
    redimensionner();
    controls.update();
    renderer.render(scene, camera);
  })();
  return api;
}
```

- [ ] **Step 6 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 6 tests PASS.

- [ ] **Step 7 : commit**

```bash
git add backend/app/main.py frontend/etabli/index.html frontend/lib3d/viewer.js backend/tests/test_etabli_canevas.py
git commit -m 'etabli : montages /etabli et /lib3d, coque de page et canevas partage' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 3 : charger un GLB et le cadrer

**Files:**
- Modify: `frontend/lib3d/viewer.js`
- Test: `backend/tests/test_etabli_canevas.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── C. chargement et cadrage ─────────────────────────────────────────────────

def test_le_viewer_branche_les_deux_decodeurs():
    js = _lire("lib3d/viewer.js")
    assert "meshopt_decoder" in js
    assert "DRACOLoader" in js
    assert "setDRACOLoader" in js


def test_le_viewer_cadre_sur_la_boite_englobante():
    """Sans cadrage, un modele en metres et un modele en centimetres donnent
    l'un un point, l'autre un mur : le cadrage est ce qui rend les etapes
    comparables."""
    js = _lire("lib3d/viewer.js")
    assert "cadrer" in js
    assert "Box3" in js


def test_le_viewer_libere_la_memoire_entre_deux_chargements():
    """Charger dix etapes de 200 Mo sans disposer sature le GPU."""
    js = _lire("lib3d/viewer.js")
    assert "dispose" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : les trois nouveaux tests échouent (marqueurs absents).

- [ ] **Step 3 : implémenter chargement, cadrage et libération**

Ajouter à `frontend/lib3d/viewer.js` :

```js
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

let _loader = null;
function loader() {
  if (_loader) return _loader;
  _loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath("/assets/three/addons/libs/draco/");
  _loader.setDRACOLoader(draco);
  _loader.setMeshoptDecoder(MeshoptDecoder);
  return _loader;
}

/* Libère la mémoire GPU. Charger dix étapes d'un maillage texturé sans
   disposer sature la carte en quelques minutes. */
export function vider(api) {
  if (!api.racine) return;
  api.racine.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const mats = Array.isArray(o.material) ? o.material : (o.material ? [o.material] : []);
    for (const m of mats) {
      for (const k of Object.keys(m)) {
        const v = m[k];
        if (v && v.isTexture) v.dispose();
      }
      m.dispose();
    }
  });
  api.scene.remove(api.racine);
  api.racine = null;
}

/* Cadre la caméra sur la boîte englobante. Indispensable : un modèle en
   mètres et un modèle en centimètres donneraient l'un un point, l'autre un
   mur — et deux étapes ne seraient pas comparables à l'œil. */
export function cadrer(api, marge = 1.35) {
  if (!api.racine) return null;
  const boite = new THREE.Box3().setFromObject(api.racine);
  const taille = boite.getSize(new THREE.Vector3());
  const centre = boite.getCenter(new THREE.Vector3());
  const rayon = Math.max(taille.x, taille.y, taille.z) * 0.5 || 1;
  const d = (rayon * marge) / Math.tan((api.camera.fov * Math.PI) / 360);
  api.camera.position.set(centre.x + d * 0.6, centre.y + d * 0.45, centre.z + d);
  api.camera.near = Math.max(d / 1000, 0.001);
  api.camera.far = d * 100;
  api.camera.updateProjectionMatrix();
  api.controls.target.copy(centre);
  api.controls.update();
  return { taille, centre, rayon };
}

export async function charger(api, url) {
  vider(api);
  const gltf = await loader().loadAsync(url);
  api.racine = gltf.scene;
  api.gltf = gltf;
  api.scene.add(api.racine);
  const cadre = cadrer(api);
  let tris = 0, maillages = 0;
  api.racine.traverse((o) => {
    if (!o.isMesh || !o.geometry) return;
    maillages++;
    const g = o.geometry;
    tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
  });
  return { tris: Math.round(tris), maillages, ...cadre };
}
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 9 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add frontend/lib3d/viewer.js backend/tests/test_etabli_canevas.py
git commit -m 'etabli : chargement GLB avec decodeurs, cadrage et liberation memoire' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 4 : la chronologie des étapes

**Files:**
- Create: `frontend/etabli/etabli.js`
- Create: `frontend/etabli/etabli.css`
- Test: `backend/tests/test_etabli_canevas.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── D. la chronologie ────────────────────────────────────────────────────────

def test_la_page_lit_la_chronologie_unifiee():
    js = _lire("etabli/etabli.js")
    assert "/api/etabli/sources" in js


def test_le_seuil_de_charge_est_affiche_et_configurable():
    """La spec §4.1 : 300 000 triangles ou 80 Mo, montre, jamais cache."""
    js = _lire("etabli/etabli.js")
    assert "300000" in js.replace("_", "").replace(" ", "")
    assert "80" in js
    assert "SEUIL" in js


def test_alt_clic_ouvre_la_comparaison():
    js = _lire("etabli/etabli.js")
    assert "altKey" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : `FileNotFoundError` sur `etabli/etabli.js`.

- [ ] **Step 3 : écrire l'état et la chronologie**

Créer `frontend/etabli/etabli.js` :

```js
/* L'Établi — inspecteur 3D en bout de chaîne du 3D Studio.
   Vanilla, HORS du bundle minifié (même patron que /studio3d).

   RÈGLE STRUCTURANTE (spec §2.1) : cette page ne fabrique JAMAIS un GLB. Elle
   envoie des paramètres — une liste de nœuds, une matrice — aux routes
   /api/etabli/*, et c'est Python qui écrit, versionne et fiche. */
"use strict";
import { creerCanevas, charger, cadrer, vider } from "/lib3d/viewer.js";

const $ = (s) => document.querySelector(s);

/* Seuil de confort machine — MONTRÉ, jamais caché (doctrine des seuils du QC).
   Le franchir n'interdit rien : cela propose la version allégée. */
const SEUIL = { triangles: 300000, octets: 80 * 1024 * 1024 };

const S = {
  sources: { jobs: [], meshy: [] },
  a: null, b: null,          // { job, version, url, libelle, fiche }
  vueA: null, vueB: null,    // canevas
  enAttente: [],             // corrections non écrites
};

async function jget(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json();
}

async function jpost(p, corps) {
  const r = await fetch(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  const t = await r.text();
  if (!r.ok) throw new Error(t || `${p} → ${r.status}`);
  return t ? JSON.parse(t) : {};
}

const fmtOctets = (n) => !n ? "—"
  : n > 1048576 ? `${(n / 1048576).toFixed(1)} Mo` : `${Math.round(n / 1024)} Ko`;

/* ── la chronologie : une ligne par job, une puce par étape ────────────────── */
function rendreChrono() {
  const box = $("#chrono");
  const blocs = [];
  for (const j of S.sources.jobs) {
    const etapes = j.etapes.map((e) => {
      const lourd = (e.triangles && e.triangles > SEUIL.triangles)
        || (e.bytes && e.bytes > SEUIL.octets);
      return `<button class="etape${lourd ? " lourde" : ""}"
        data-job="${j.id}" data-version="${e.version || ""}"
        data-url="${e.url}" data-libelle="${e.libelle}"
        title="${e.triangles ? e.triangles + " triangles · " : ""}${fmtOctets(e.bytes)}">
        <b>${e.libelle}</b>
        <span>${e.triangles ? e.triangles.toLocaleString("fr-FR") + " tri" : fmtOctets(e.bytes)}</span>
      </button>`;
    }).join("");
    blocs.push(`<section class="job">
      <div class="job-tete">${j.nom}<span>${j.moteur || j.source}</span></div>
      <div class="job-etapes">${etapes}</div></section>`);
  }
  for (const t of S.sources.meshy) {
    const etapes = t.etapes.map((e) => `<button class="etape"
      data-meshy="${t.id}" data-url="${e.url}" data-libelle="${e.libelle}">
      <b>${e.libelle}</b><span>${t.phase || t.kind || "meshy"}</span></button>`).join("");
    blocs.push(`<section class="job">
      <div class="job-tete">${t.nom}<span>meshy · ${t.phase || ""}</span></div>
      <div class="job-etapes">${etapes}</div></section>`);
  }
  box.innerHTML = blocs.join("") || '<div class="chrono-vide">aucun maillage</div>';

  box.querySelectorAll(".etape").forEach((b) => {
    b.addEventListener("click", (ev) => {
      const cible = {
        job: b.dataset.job || null,
        /* une étape Meshy n'a pas de job : on garde l'id de la tâche pour
           pouvoir la faire adopter au moment d'écrire (spec §6.2) */
        meshy: b.dataset.meshy || null,
        version: b.dataset.version ? Number(b.dataset.version) : null,
        url: b.dataset.url,
        libelle: b.dataset.libelle,
      };
      /* alt-clic : la seconde vue, pour comparer deux étapes (spec §5.1) */
      if (ev.altKey) ouvrirComparaison(cible);
      else ouvrirPrincipale(cible);
    });
  });
}

async function ouvrirPrincipale(cible) {
  if (!S.vueA) S.vueA = creerCanevas($("#vueA canvas"));
  S.a = cible;
  const geo = await charger(S.vueA, cible.url);
  $("#chipSource").textContent = `${cible.job || "meshy"} · ${cible.libelle}`;
  $("#barreFichier").textContent = cible.url.split("/").pop();
  $("#barreGeo").textContent =
    `${geo.tris.toLocaleString("fr-FR")} triangles · ${geo.maillages} maillages`;
  if (geo.tris > SEUIL.triangles) {
    $("#barreGeo").textContent +=
      ` · au-delà du seuil de ${SEUIL.triangles.toLocaleString("fr-FR")}, une version décimée existe peut-être`;
  }
  document.dispatchEvent(new CustomEvent("etabli:charge", { detail: { geo } }));
}

async function amorcer() {
  S.sources = await jget("/api/etabli/sources");
  rendreChrono();
}
amorcer();

export { S, SEUIL, jget, jpost, ouvrirPrincipale };
```

- [ ] **Step 4 : écrire la feuille de style**

Créer `frontend/etabli/etabli.css`. Reprendre les jetons de
`frontend/studio3d/studio3d.css` (mêmes variables `--ink-*`, `--accent`,
`--green`, `--red`) pour que les deux pages du 3D Studio se ressemblent, et
poser la grille :

```css
/* L'Établi — même famille visuelle que /studio3d. */
.etabli {
  display: grid;
  grid-template-columns: 260px 1fr 320px;
  height: 100vh;
  overflow: hidden;
}
.centre { display: flex; flex-direction: column; min-width: 0; }
.vues { flex: 1; display: flex; gap: 2px; min-height: 0; }
.vue { position: relative; flex: 1; min-width: 0; }
.vue canvas { width: 100%; height: 100%; display: block; }
.vue-tag {
  position: absolute; top: 8px; left: 10px;
  font: 600 11px/1 ui-monospace, monospace; opacity: .6;
}
.hidden { display: none !important; }
.etape.lourde b::after { content: " ⚠"; }
.barre {
  display: flex; gap: 16px; align-items: center;
  padding: 6px 12px; font: 11px/1.4 ui-monospace, monospace;
}
.rail-left, .rail-right { overflow-y: auto; padding: 12px; }
.job-etapes { display: flex; flex-wrap: wrap; gap: 4px; }
.etape { display: flex; flex-direction: column; align-items: flex-start; }
```

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 12 tests PASS.

- [ ] **Step 6 : commit**

```bash
git add frontend/etabli backend/tests/test_etabli_canevas.py
git commit -m 'etabli : la chronologie des etapes, avec seuil de charge affiche' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 5 : la comparaison A/B et la ligne d'écart

**Files:**
- Modify: `frontend/etabli/etabli.js`
- Test: `backend/tests/test_etabli_canevas.py`

C'est la fonction qui répond à « m'assurer que tout est bien cohérent » : deux
vues, caméras synchronisées, et des chiffres sous elles.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── E. comparaison A/B ───────────────────────────────────────────────────────

def test_les_cameras_des_deux_vues_sont_synchronisees():
    """Comparer deux etapes sous deux angles differents ne compare rien."""
    js = _lire("etabli/etabli.js")
    assert "synchroniser" in js


def test_la_ligne_d_ecart_chiffre_la_comparaison():
    js = _lire("etabli/etabli.js")
    for mot in ("triangles", "sha256", "dimensions"):
        assert mot in js
    assert "/report" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : les deux nouveaux tests échouent.

- [ ] **Step 3 : implémenter**

Ajouter à `frontend/etabli/etabli.js` :

```js
/* Deux vues, une seule caméra logique. Comparer deux étapes sous deux angles
   différents ne compare rien : la synchronisation n'est pas un confort. */
function synchroniser(src, dst) {
  let enCours = false;
  src.controls.addEventListener("change", () => {
    if (enCours) return;
    enCours = true;
    dst.camera.position.copy(src.camera.position);
    dst.camera.quaternion.copy(src.camera.quaternion);
    dst.camera.fov = src.camera.fov;
    dst.camera.near = src.camera.near;
    dst.camera.far = src.camera.far;
    dst.camera.updateProjectionMatrix();
    dst.controls.target.copy(src.controls.target);
    dst.controls.update();
    enCours = false;
  });
}

async function ficheDe(cible) {
  if (!cible.job) return null;
  try {
    const reg = await jget(`/api/assets/3d/${cible.job}/report`);
    const v = cible.version || 1;
    return (reg.entries || []).find((e) => Number(e.version) === Number(v)) || null;
  } catch { return null; }
}

function ligneEcart(fa, fb, geoA, geoB) {
  const ga = (fa && fa.geometry) || {}, gb = (fb && fb.geometry) || {};
  /* La fiche nomme le compte `tris_lus` et les cotes `dims` (un OBJET
     largeur/hauteur/profondeur, pas un tableau) — vérifié dans
     mesh_report.geometry. Se tromper de clé afficherait « — » partout sans
     rien casser, ce qui est le pire des échecs : silencieux. */
  const ta = ga.tris_lus ?? geoA.tris, tb = gb.tris_lus ?? geoB.tris;
  const delta = (tb - ta);
  const pct = ta ? ` (${delta >= 0 ? "+" : ""}${((delta / ta) * 100).toFixed(1)} %)` : "";
  const dim = (g) => g.dims
    ? [g.dims.largeur, g.dims.hauteur, g.dims.profondeur]
        .map((x) => Number(x).toFixed(3)).join(" × ") : "—";
  const sha = (f) => f && f.sha256 ? f.sha256.slice(0, 10) + "…" : "—";
  return `
    <div><b>triangles</b> ${ta ?? "—"} → ${tb ?? "—"}
      <i>${delta >= 0 ? "+" : ""}${delta}${pct}</i></div>
    <div><b>dimensions</b> ${dim(ga)} → ${dim(gb)}</div>
    <div><b>textures</b> ${(fa?.gltf?.textures) ?? "—"} → ${(fb?.gltf?.textures) ?? "—"}</div>
    <div><b>sha256</b> ${sha(fa)} → ${sha(fb)}</div>`;
}

async function ouvrirComparaison(cible) {
  if (!S.a) { await ouvrirPrincipale(cible); return; }
  $("#vueB").classList.remove("hidden");
  if (!S.vueB) {
    S.vueB = creerCanevas($("#vueB canvas"));
    synchroniser(S.vueA, S.vueB);
    synchroniser(S.vueB, S.vueA);
  }
  S.b = cible;
  const geoB = await charger(S.vueB, cible.url);
  const geoA = { tris: null };
  const [fa, fb] = await Promise.all([ficheDe(S.a), ficheDe(S.b)]);
  const box = $("#ecart");
  box.classList.remove("hidden");
  box.innerHTML = `<div class="ecart-tete">A ${S.a.libelle} → B ${cible.libelle}</div>`
    + ligneEcart(fa, fb, geoA, geoB);
}

$("#btnCompare").addEventListener("click", () => {
  $("#vueB").classList.add("hidden");
  $("#ecart").classList.add("hidden");
  if (S.vueB) vider(S.vueB);
  S.b = null;
});
```

- [ ] **Step 4 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 14 tests PASS.

- [ ] **Step 5 : commit**

```bash
git add frontend/etabli/etabli.js backend/tests/test_etabli_canevas.py
git commit -m 'etabli : comparaison A/B a cameras synchronisees et ligne d ecart chiffree' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 6 : le nœud `07 · établi` dans le 3D Studio

**Files:**
- Modify: `frontend/studio3d/studio3d.js` (constantes `NODES` ligne ~24, `CABLES` ligne ~42)
- Modify: `frontend/studio3d/index.html` (la `viewBox` du `<svg id="cables">`, ligne ~66)
- Test: `backend/tests/test_etabli_canevas.py`

Le graphe a des coordonnées au pixel près et le nœud `export` (x 608, largeur
132) occupe déjà le bord droit de la `viewBox 0 0 740 330`. Le changement est
**confiné à trois constantes** ; aucune autre géométrie ne bouge.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── F. le bout de chaine dans /studio3d ──────────────────────────────────────

def test_le_graphe_porte_le_noeud_07_etabli():
    js = _lire("studio3d/studio3d.js")
    assert '"etabli"' in js
    assert "07 · établi" in js


def test_la_viewbox_a_ete_elargie_pour_le_noeud_07():
    """Le noeud export tenait deja le bord droit : sans elargissement, le 07
    serait hors cadre."""
    html = _lire("studio3d/index.html")
    assert "0 0 892 330" in html


def test_le_noeud_07_ouvre_la_page_etabli():
    js = _lire("studio3d/studio3d.js")
    assert "/etabli" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : les trois nouveaux tests échouent.

- [ ] **Step 3 : élargir la viewBox**

Dans `frontend/studio3d/index.html`, remplacer :

```html
          <svg viewBox="0 0 740 330" id="cables"></svg>
```

par :

```html
          <!-- 892 (et non 740) : le nœud 07 · établi tient le nouveau bord
               droit. Élargissement confiné — NODES, CABLES et cette viewBox. -->
          <svg viewBox="0 0 892 330" id="cables"></svg>
```

- [ ] **Step 4 : ajouter le nœud et son câble**

Dans `frontend/studio3d/studio3d.js`, ajouter à la fin du tableau `NODES`
(après l'entrée `export`) :

```js
  { id: "etabli", phase: "etabli", x: 760, y: 94, w: 132, h: 164, kind: "--c-3d",
    kicker: "07 · établi", ports: [[-4, 78]] },
```

et à la fin du tableau `CABLES` :

```js
  { id: "k9", d: "M740,176 C750,176 750,176 760,176", phase: "etabli", kind: "--c-3d" },
```

Ajouter enfin, dans la même section que les autres libellés d'endpoint
(`EP_LABEL`) :

```js
  etabli: "local · inspection",
```

- [ ] **Step 5 : rendre le nœud cliquable**

Dans `frontend/studio3d/studio3d.js`, à l'endroit où les nœuds reçoivent leur
gestionnaire de double-clic, ajouter le cas particulier de l'Établi — il n'a
rien à éditer, il s'ouvre :

```js
/* Le nœud 07 n'est pas une tâche Meshy : il ouvre l'Établi sur le job courant.
   Simple clic (et non double), parce qu'il ne s'édite pas. */
function brancherEtabli(el) {
  el.addEventListener("click", () => {
    const q = S.cfg.name ? `?job=${encodeURIComponent(S.cfg.name)}` : "";
    window.location.href = `/etabli/${q}`;
  });
  el.title = "Ouvrir l'Établi : parties, rig, versions, export moteurs";
}
```

et l'appeler depuis la boucle de construction des nœuds quand
`node.id === "etabli"`.

- [ ] **Step 6 : ajouter aussi l'entrée du rail gauche**

Dans `frontend/studio3d/index.html`, section « Étape suivante », après le
bouton `goSprite` :

```html
      <button class="next-step" id="goEtabli">07 · Établi 3D →</button>
```

et le câbler dans `studio3d.js` à côté de `goSprite` :

```js
$("#goEtabli").addEventListener("click", () => {
  const q = S.cfg.name ? `?job=${encodeURIComponent(S.cfg.name)}` : "";
  window.location.href = `/etabli/${q}`;
});
```

- [ ] **Step 7 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 17 tests PASS.

- [ ] **Step 8 : commit**

```bash
git add frontend/studio3d backend/tests/test_etabli_canevas.py
git commit -m 'studio3d : le noeud 07 etabli en bout de graphe, viewBox elargie a 892' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 7 : les Parties — sélectionner et isoler

**Files:**
- Create: `frontend/lib3d/selection.js`
- Modify: `frontend/etabli/etabli.js`
- Test: `backend/tests/test_etabli_canevas.py`

Trois granularités, parce que les moteurs ne découpent pas pareil : un modèle
Meshy est souvent un nœud unique à plusieurs matériaux, un Tripo plusieurs
nœuds. **L'isolation est un affichage — elle n'écrit rien.**

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── G. Parties : selection et isolation ──────────────────────────────────────

def test_les_trois_granularites_de_selection_existent():
    js = _lire("lib3d/selection.js")
    for mot in ("noeud", "maillage", "materiau"):
        assert mot in js


def test_la_selection_se_fait_aussi_au_clic_dans_le_canevas():
    js = _lire("lib3d/selection.js")
    assert "Raycaster" in js


def test_l_isolation_est_un_affichage_et_n_ecrit_rien():
    """Isoler ne doit toucher AUCUNE route d'ecriture."""
    js = _lire("lib3d/selection.js")
    assert "isoler" in js
    assert "/api/etabli/extraire" not in js
    assert "fetch" not in js


def test_l_index_de_noeud_gltf_est_conserve_pour_le_serveur():
    """Le serveur raisonne en index de noeud glTF ; three.js en objets. Sans
    ce pont, l'extraction viserait le mauvais noeud."""
    js = _lire("lib3d/selection.js")
    assert "userData" in js
    assert "indexGltf" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : `FileNotFoundError` sur `lib3d/selection.js`.

- [ ] **Step 3 : implémenter**

Créer `frontend/lib3d/selection.js` :

```js
/* Sélection et isolation dans le canevas partagé.
   Ce module NE PARLE À AUCUNE ROUTE : isoler est un affichage. C'est
   l'Établi qui, sur un clic explicite, envoie les index au serveur. */
"use strict";
import * as THREE from "three";

/* Le serveur raisonne en INDEX DE NŒUD glTF, three.js en objets. GLTFLoader
   pose l'index d'origine dans `userData` sous une clé non documentée selon
   les versions ; on le rétablit ici une fois pour toutes, à partir du
   document parsé, et tout le reste s'appuie sur `userData.indexGltf`. */
export function indexerNoeuds(api) {
  const doc = api.gltf && api.gltf.parser && api.gltf.parser.json;
  if (!doc || !doc.nodes) return;
  const parNom = new Map();
  doc.nodes.forEach((n, i) => {
    if (n.name) {
      if (!parNom.has(n.name)) parNom.set(n.name, []);
      parNom.get(n.name).push(i);
    }
  });
  api.racine.traverse((o) => {
    if (o.userData && o.userData.indexGltf !== undefined) return;
    const cands = parNom.get(o.name);
    if (cands && cands.length) {
      o.userData = o.userData || {};
      o.userData.indexGltf = cands.shift();
    }
  });
}

/* L'inventaire que le panneau Parties affiche. */
export function inventaire(api) {
  const noeuds = [], maillages = [], materiaux = new Map();
  api.racine.traverse((o) => {
    if (o.userData && o.userData.indexGltf !== undefined) {
      noeuds.push({ nom: o.name || `noeud_${o.userData.indexGltf}`,
                    indexGltf: o.userData.indexGltf, uuid: o.uuid });
    }
    if (!o.isMesh) return;
    const g = o.geometry;
    maillages.push({
      nom: o.name || "maillage", uuid: o.uuid,
      tris: Math.round((g.index ? g.index.count : g.attributes.position.count) / 3),
      indexGltf: o.userData ? o.userData.indexGltf : undefined,
    });
    for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
      if (!m) continue;
      if (!materiaux.has(m.uuid)) {
        materiaux.set(m.uuid, { nom: m.name || "matériau", uuid: m.uuid, objets: [] });
      }
      materiaux.get(m.uuid).objets.push(o.uuid);
    }
  });
  return { noeuds, maillages, materiaux: [...materiaux.values()] };
}

const _teinte = new THREE.Color(0x4da3ff);

/* Isole : ce qui est retenu reste plein, le reste passe en fantôme.
   Masquer complètement ferait perdre le contexte ; un fantôme le garde. */
export function isoler(api, gardes, { fantome = 0.08 } = {}) {
  const retenu = new Set(gardes || []);
  api.racine.traverse((o) => {
    if (!o.isMesh) return;
    const dedans = retenu.size === 0 || retenu.has(o.uuid)
      || (o.userData && retenu.has(o.userData.indexGltf));
    for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
      if (!m) continue;
      if (m.userData.opaciteOrigine === undefined) {
        m.userData.opaciteOrigine = m.opacity;
        m.userData.transparentOrigine = m.transparent;
      }
      m.transparent = dedans ? m.userData.transparentOrigine : true;
      m.opacity = dedans ? m.userData.opaciteOrigine : fantome;
      m.depthWrite = dedans;
      m.needsUpdate = true;
    }
  });
}

export function surligner(api, uuid) {
  api.racine.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
      if (!m || !m.emissive) continue;
      if (m.userData.emissiveOrigine === undefined) {
        m.userData.emissiveOrigine = m.emissive.getHex();
      }
      m.emissive.setHex(o.uuid === uuid ? _teinte.getHex()
                                        : m.userData.emissiveOrigine);
      m.needsUpdate = true;
    }
  });
}

/* Clic dans le canevas -> le maillage sous le curseur. */
export function designerAuClic(api, canvas, quand) {
  const ray = new THREE.Raycaster();
  const p = new THREE.Vector2();
  canvas.addEventListener("pointerdown", (ev) => {
    const r = canvas.getBoundingClientRect();
    p.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    p.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(p, api.camera);
    const touche = ray.intersectObject(api.racine, true)
      .find((h) => h.object && h.object.isMesh);
    quand(touche ? touche.object : null);
  });
}
```

- [ ] **Step 4 : brancher le panneau Parties**

Ajouter à `frontend/etabli/etabli.js` :

```js
import { indexerNoeuds, inventaire, isoler, surligner, designerAuClic }
  from "/lib3d/selection.js";

const SEL = { granularite: "maillage", retenus: new Set() };

function rendreParties() {
  const inv = inventaire(S.vueA);
  const liste = SEL.granularite === "noeud" ? inv.noeuds
    : SEL.granularite === "materiau" ? inv.materiaux : inv.maillages;
  $("#panParties").innerHTML = `
    <div class="granularite">
      ${["noeud", "maillage", "materiau"].map((g) =>
        `<button data-g="${g}" class="${g === SEL.granularite ? "actif" : ""}">${g}</button>`
      ).join("")}
    </div>
    <div class="parties">${liste.map((x) => `
      <label class="partie">
        <input type="checkbox" data-uuid="${x.uuid}"
               data-index="${x.indexGltf ?? ""}"
               ${SEL.retenus.has(x.uuid) ? "checked" : ""}>
        <b>${x.nom}</b>${x.tris ? `<span>${x.tris} tri</span>` : ""}
      </label>`).join("")}</div>
    <div class="parties-actions">
      <button id="btnIsoler">Isoler la sélection</button>
      <button id="btnToutVoir">Tout revoir</button>
    </div>`;

  $("#panParties").querySelectorAll("[data-g]").forEach((b) =>
    b.addEventListener("click", () => {
      SEL.granularite = b.dataset.g; SEL.retenus.clear(); rendreParties();
    }));
  $("#panParties").querySelectorAll("input[type=checkbox]").forEach((c) =>
    c.addEventListener("change", () => {
      if (c.checked) SEL.retenus.add(c.dataset.uuid);
      else SEL.retenus.delete(c.dataset.uuid);
    }));
  $("#btnIsoler").addEventListener("click", () => isoler(S.vueA, [...SEL.retenus]));
  $("#btnToutVoir").addEventListener("click", () => isoler(S.vueA, []));
}

document.addEventListener("etabli:charge", () => {
  indexerNoeuds(S.vueA);
  rendreParties();
  designerAuClic(S.vueA, $("#vueA canvas"), (obj) => {
    if (!obj) return;
    surligner(S.vueA, obj.uuid);
    SEL.retenus.add(obj.uuid);
    rendreParties();
  });
});
```

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 21 tests PASS.

- [ ] **Step 6 : commit**

```bash
git add frontend/lib3d/selection.js frontend/etabli/etabli.js backend/tests/test_etabli_canevas.py
git commit -m 'etabli : Parties par noeud, maillage ou materiau, isolation non destructive' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Task 8 : séparer, transformer, écrire — la porte

**Files:**
- Modify: `frontend/etabli/etabli.js`
- Test: `backend/tests/test_etabli_canevas.py`

**Tant que « écrire la version » n'a pas été cliqué, rien n'a bougé sur le
disque.** La barre du bas énumère les modifications en attente.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_etabli_canevas.py` :

```python
# ── H. la porte d'ecriture ───────────────────────────────────────────────────

def test_la_page_appelle_les_routes_d_ecriture_de_p1():
    js = _lire("etabli/etabli.js")
    for route in ("/api/etabli/extraire", "/api/etabli/transformer",
                  "/api/etabli/reparer"):
        assert route in js


def test_rien_n_est_ecrit_sans_le_bouton():
    js = _lire("etabli/etabli.js")
    assert "enAttente" in js
    assert "btnEcrire" in js


def test_la_page_ne_fabrique_jamais_un_glb():
    """Regle de l'option C : pas de GLTFExporter, pas de Blob GLB cote client.
    Son absence du bundle rend la regle impossible a enfreindre par megarde."""
    js = _lire("etabli/etabli.js")
    assert "GLTFExporter" not in js
    viewer = _lire("lib3d/viewer.js")
    assert "GLTFExporter" not in viewer


def test_les_gizmos_sont_branches():
    js = _lire("etabli/etabli.js")
    assert "TransformControls" in js
```

- [ ] **Step 2 : lancer le banc et vérifier qu'il échoue**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : les quatre nouveaux tests échouent, sauf
`test_la_page_ne_fabrique_jamais_un_glb` qui passe déjà — et **doit continuer à
passer** : c'est un test de non-régression, pas une étape à franchir.

- [ ] **Step 3 : implémenter la file d'attente et les gizmos**

Ajouter à `frontend/etabli/etabli.js` :

```js
import { TransformControls } from "three/addons/controls/TransformControls.js";

let GIZMO = null;

function poserGizmo(objet) {
  if (!GIZMO) {
    GIZMO = new TransformControls(S.vueA.camera, S.vueA.renderer.domElement);
    /* le gizmo et l'orbite se disputent la souris : l'un désarme l'autre */
    GIZMO.addEventListener("dragging-changed", (e) => {
      S.vueA.controls.enabled = !e.value;
    });
    GIZMO.addEventListener("objectChange", () => {
      const o = GIZMO.object;
      if (!o || !o.userData || o.userData.indexGltf === undefined) return;
      noterAttente("transformer", {
        [o.userData.indexGltf]: {
          translation: [o.position.x, o.position.y, o.position.z],
          rotation: [o.quaternion.x, o.quaternion.y, o.quaternion.z, o.quaternion.w],
          scale: [o.scale.x, o.scale.y, o.scale.z],
        },
      });
    });
    S.vueA.scene.add(GIZMO);
  }
  GIZMO.attach(objet);
}

/* Rien n'est écrit tant que le bouton n'est pas cliqué : la file est la
   mémoire de ce qui attend, et la barre du bas la montre. */
function noterAttente(operation, charge) {
  const i = S.enAttente.findIndex((x) => x.operation === operation);
  if (i >= 0) S.enAttente[i] = { operation, charge };
  else S.enAttente.push({ operation, charge });
  rendreAttente();
}

function rendreAttente() {
  const box = $("#barreAttente");
  if (!S.enAttente.length) { box.innerHTML = ""; return; }
  box.innerHTML = `<b>${S.enAttente.length} modification(s) en attente</b>
    <button id="btnEcrire">écrire la version</button>
    <button id="btnAnnuler">annuler</button>`;
  $("#btnEcrire").addEventListener("click", ecrireVersion);
  $("#btnAnnuler").addEventListener("click", () => {
    S.enAttente.length = 0; rendreAttente(); ouvrirPrincipale(S.a);
  });
}

async function ecrireVersion() {
  /* Une étape venue d'une tâche Meshy n'a pas de job où se versionner : on la
     fait adopter d'abord (spec §6.2). Une seule provenance, pas deux. */
  if (S.a && !S.a.job && S.a.meshy) {
    const ad = await jpost("/api/etabli/adopter", { task_id: S.a.meshy });
    S.a = { ...S.a, job: ad.job, version: ad.version, url: ad.url };
  }
  const base = { job: S.a.job, version: S.a.version };
  let derniere = null;
  for (const t of S.enAttente) {
    const corps = t.operation === "transformer"
      ? { ...base, transforms: t.charge }
      : t.operation === "extraire"
        ? { ...base, noeuds: t.charge }
        : { ...base, ...t.charge };
    derniere = await jpost(`/api/etabli/${t.operation}`, corps);
    base.version = derniere.version;      /* enchaîner sur la version écrite */
  }
  S.enAttente.length = 0;
  rendreAttente();
  S.sources = await jget("/api/etabli/sources");
  rendreChrono();
  if (derniere) {
    await ouvrirPrincipale({ ...S.a, version: derniere.version,
      url: `/api/assets/3d/${S.a.job}/version/${derniere.version}`,
      libelle: `version ${derniere.version}` });
  }
}

/* Séparer : la sélection courante part comme nouvelle version. */
function brancherSeparer() {
  const b = document.createElement("button");
  b.textContent = "Séparer la sélection en une version";
  b.addEventListener("click", () => {
    const idx = [...SEL.retenus]
      .map((u) => {
        let trouve;
        S.vueA.racine.traverse((o) => { if (o.uuid === u) trouve = o; });
        return trouve && trouve.userData ? trouve.userData.indexGltf : undefined;
      })
      .filter((x) => x !== undefined);
    if (!idx.length) { alert("Aucun nœud glTF dans la sélection."); return; }
    noterAttente("extraire", idx);
  });
  $("#panParties").querySelector(".parties-actions").appendChild(b);
}
```

Appeler `brancherSeparer()` à la fin de `rendreParties()`, et `poserGizmo(obj)`
depuis le gestionnaire de `designerAuClic`.

- [ ] **Step 4 : ajouter le bloc Réparer au panneau Fiche**

Ajouter à `frontend/etabli/etabli.js` :

```js
function rendreFiche() {
  $("#panFiche").innerHTML = `
    <div class="dt-label">Réparer l'assise</div>
    <label>axe haut
      <select id="fAxe"><option value="Y">Y (glTF, Unity, Godot)</option>
      <option value="Z">Z (Blender, Unreal)</option></select></label>
    <label>échelle <input id="fEchelle" type="number" step="0.01" value="1"></label>
    <label><input id="fRecentrer" type="checkbox"> recentrer sur l'origine</label>
    <button id="fAppliquer">Mettre en attente</button>
    <p class="note">Le recentrage a besoin de la géométrie : sur un GLB
      compressé il refuse, en le disant. L'axe et l'échelle passent quand
      même.</p>`;
  $("#fAppliquer").addEventListener("click", () => {
    noterAttente("reparer", {
      axe_haut: $("#fAxe").value,
      echelle: Number($("#fEchelle").value) || 1,
      recentrer: $("#fRecentrer").checked,
    });
  });
}
```

et l'appeler depuis l'écouteur `etabli:charge`.

- [ ] **Step 5 : relancer le banc**

```bash
.\scripts\run-tests.ps1 -Filter test_etabli_canevas.py
```

Attendu : 25 tests PASS.

- [ ] **Step 6 : lancer la suite complète**

```bash
.\scripts\run-tests.ps1
```

Attendu : tout au vert. `main.py` et `studio3d.js` ont été modifiés — les bancs
qui les épinglent doivent rester verts.

- [ ] **Step 7 : commit**

```bash
git add frontend/etabli/etabli.js backend/tests/test_etabli_canevas.py
git commit -m 'etabli : gizmos, separation et reparation derriere la porte d ecriture' -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>'
```

---

## Vérification à l'écran (utilisateur)

Les bancs miroirs prouvent la structure, pas le rendu. **Ne pas lancer le
backend depuis l'agent** : le préparer, puis demander à l'utilisateur de
relancer et de vérifier, sur `/etabli/` :

1. la chronologie liste les jobs et leurs versions ;
2. cliquer une étape l'affiche, cadrée ;
3. alt-cliquer une seconde ouvre la vue B, **les deux caméras bougent
   ensemble**, et la ligne d'écart affiche des chiffres ;
4. cocher deux maillages puis « Isoler » laisse le reste en fantôme ;
5. « Séparer » puis « écrire la version » fait apparaître une version de plus
   dans la chronologie, **sans faire disparaître la précédente** ;
6. dans `/studio3d`, le nœud `07 · établi` est visible en bout de graphe et
   n'a pas décalé les six autres.

## Ce que P2+P3 laisse de côté

- **Le panneau Rig** est une coquille (« arrive en P4 »).
- **Le panneau Export** est une coquille (« arrive en P5 »).
- **Aucune écriture hors de `outputs/`.**
- **Les cinq capacités écartées** ont leur document ; ne rien en anticiper.
