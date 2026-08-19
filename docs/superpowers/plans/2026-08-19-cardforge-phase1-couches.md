# Cardforge Phase 1 — Export par couches : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exporter chaque carte en couches PNG alpha nommées par rôle (recto et verso) + un composite, avec PREUVE D'EMPILEMENT stricte, dans un ZIP au manifeste chiffré — la pièce P9 « Forge 3D » naît avec cette capacité.

**Architecture:** Le moteur de rendu du CORE gagne deux options internes (`only_z`, `paper:false`) et une API `CF.layers` qui rend chaque groupe de painters isolément, vérifie couche par couche que l'isolée empile (pixel strict), et bascule sinon en « empreinte » (delta de cumulatifs — reproduction exacte par construction : la pièce Matières pose `multiply/overlay/screen`, mesuré dans mod-texture.js:835-857, l'empilement naïf ne PEUT PAS reproduire). Le navigateur téléverse couches + composite + preuve ; `forge3d.py` contre-vérifie en PIL, estampille, zippe avec manifeste `card-3d/layers-manifest@1`.

**Tech Stack:** lab Cardforge (JS source direct + FastAPI), PIL pur, patrons existants : multipart de `print.py:post_sheet`, manifeste/ZIP de `gltf.py`, parité JS↔py de `type.py`.

**Références obligatoires avant de commencer :**
- Spec : `docs/superpowers/specs/2026-08-19-cardforge-universel-design.md` §3, §4.
- Contrat du lab : `docs/superpowers/specs/2026-08-11-cardforge-design.md` (règles 1-16).
- Le backend :8765 sert l'APP INSTALLÉE, pas le dépôt : après toute modif backend,
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qa\cf_deploy.ps1 -Backend`.
- Tests : `powershell -File scripts\run-tests.ps1 -Filter cards_forge3d` (UN processus par
  fichier — jamais `pytest tests` global).
- Encodage : UTF-8 sans BOM ; `mod-frame.js` est en LF, tout le reste en CRLF — conserver
  l'EOL du fichier touché.
- Interdits : `Math.random()` dans un painter/rendu (PRNG seedé), z nouveaux (table
  gelée), écriture hors de son sous-arbre, `alert(`.

---

### Task 1: Squelette de la pièce P9 « forge3d » (fichiers, coquille, lint, routeur)

**Files:**
- Modify: `scripts/qa/lint_cardforge.py:69` (liste MODULES) et `:59-68` (table z)
- Modify: `frontend/cardforge/index.html` (css, panneau 09, script)
- Modify: `backend/app/services/cards/__init__.py:38-58` (branchement routeur)
- Create: `frontend/cardforge/js/mod-forge3d.js`
- Create: `frontend/cardforge/css/mod-forge3d.css`
- Create: `backend/app/services/cards/forge3d.py`
- Create: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : test qui échoue — la pièce n'existe pas**

Créer `backend/tests/test_cards_forge3d.py` avec l'en-tête d'environnement STANDARD du
domaine (copier les lignes 29-58 de `backend/tests/test_cards_gltf.py` : tempdir,
DATABASE_URL, FAL_KEY, IMAGES/OUTPUTS_FOLDER, sys.path, helper `_api`) puis :

```python
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = ROOT / "frontend" / "cardforge" / "js" / "mod-forge3d.js"


def test_la_piece_est_complete_et_passe_le_lint():
    """Règle 1 : 1 JS + 1 CSS + 1 py + 1 test. Le lint est le juge, pas nous."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "qa" / "lint_cardforge.py"),
         "--module", "forge3d"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_info_publie_les_roles_de_couches():
    did = _deck("Forge")
    info = _api("GET", f"/api/cards/{did}/forge3d/info").json()
    assert info["schema"] == "card-3d/layers-manifest@1"
    roles = [r["role"] for r in info["layer_roles"]]
    assert roles == ["fond-matiere", "illustration", "voile-matiere",
                     "cadre", "typographie", "ornements"]
    # les z de chaque rôle sont ceux de la table gelée du CORE
    par_role = {r["role"]: r["z"] for r in info["layer_roles"]}
    assert par_role["fond-matiere"] == [10] and par_role["illustration"] == [20]
    assert par_role["voile-matiere"] == [30] and par_role["cadre"] == [40]
    assert par_role["typographie"] == [60] and par_role["ornements"] == [70]
```

(le helper `_deck` : copier `_deck` de `test_cards_gltf.py:125-128`. Terminer le
fichier par le bloc des sœurs — sans lui, une exécution directe « passe » sans
lancer un seul test :
```python
if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```
)

- [ ] **Step 2 : vérifier l'échec**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
```
Attendu : FAIL (lint rc=2 « module inconnu », route 404).

- [ ] **Step 3 : lint — déclarer le module**

`scripts/qa/lint_cardforge.py` ligne 69 :
```python
MODULES = ["face", "frame", "type", "data", "solid", "texture", "print",
           "gltf", "forge3d"]
```
Dans la table z (lignes 59-68), ajouter `forge3d` à la famille « aucun painter » — même
traitement que `data/solid/print/gltf` (repérer la structure exacte sur place ; si la
table est un dict `{module: {z autorisés}}`, l'entrée est `"forge3d": set()`).

- [ ] **Step 4 : coquille index.html (changement CORE assumé)**

Trois insertions dans `frontend/cardforge/index.html` :
après la ligne 20 (`css/mod-gltf.css`) :
```html
<link rel="stylesheet" href="css/mod-forge3d.css">
```
après la section `cf-panel-gltf` (ligne 125) :
```html
    <section class="cf-panel" id="cf-panel-forge3d" data-mod="forge3d">
      <div class="panel-head"><b class="ph-n">09</b><h2>Forge 3D</h2><p class="hint">Couches PNG alpha par élément, preuve d'empilement, manifeste — l'entrée du graphe 3D.</p></div>
      <div class="cf-host cf-forge3d" data-host="forge3d"></div>
    </section>
```
après la ligne 146 (`mod-gltf.js`) :
```html
<script src="js/mod-forge3d.js"></script>
```

- [ ] **Step 5 : mod-forge3d.js minimal**

Créer `frontend/cardforge/js/mod-forge3d.js` (CRLF) :
```js
"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   CARD FORGE — P9 « Forge 3D ». Export par couches (phase 1).
   Proprietaire exclusif de : doc.forge3d · AUCUN z (ce module ne peint pas) ·
   /api/cards/<did>/forge3d/* · prefixe DOM cf-forge3d-.
   ═══════════════════════════════════════════════════════════════════════════ */
const CF = (typeof window !== "undefined") ? window.CF : null;
if (!CF) throw new Error("mod-forge3d: js/core.js doit etre charge avant ce fichier");
(() => {
  /* ── LA TABLE DES COUCHES — BLOC MIROIR ─────────────────────────────────
     ═══ CF-FORGE3D-LAYERS-BEGIN ═══
     Le miroir Python est dans backend/app/services/cards/forge3d.py, entre
     les mêmes marqueurs ; test_cards_forge3d compare les deux MOT POUR MOT.
     Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82). */
  const LAYER_ROLES = [
    { role: "fond-matiere", z: [10], module: "texture" },
    { role: "illustration", z: [20], module: "face" },
    { role: "voile-matiere", z: [30], module: "texture" },
    { role: "cadre", z: [40], module: "frame" },
    { role: "typographie", z: [60], module: "type" },
    { role: "ornements", z: [70], module: "frame" },
  ];
  /* ═══ CF-FORGE3D-LAYERS-END ═══ */

  const M = CF.register({
    id: "forge3d",
    title: "Forge 3D",
    icon: "⬢",
    order: 9,
    state: {
      last_export: null,        /* bordereau du dernier export de couches */
    },
    init(host) {
      host.innerHTML = shell();
      wire(host);
    },
  });

  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);

  function shell() {
    return '<div class="cf-forge3d-wrap">'
      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Couches de la carte</b></header>'
      + '<p class="hint">Une PNG alpha par élément (fond, illustration, voile, cadre, '
      + 'typo, ornements), recto et verso, plus le composite. Chaque couche est '
      + 'PROUVÉE : l\'empilement doit reproduire la carte au pixel près.</p>'
      + '<button class="btn strong" id="cf-forge3d-export" type="button">'
      + 'Exporter les couches</button>'
      + '<p class="hint" id="cf-forge3d-status"></p>'
      + '<div id="cf-forge3d-slip"></div>'
      + '</section>'
      + '</div>';
  }

  function wire(host) {
    $("#cf-forge3d-export").addEventListener("click", () => exportLayers());
  }

  async function exportLayers() { /* Task 6 remplit ce corps */ }
})();
```

- [ ] **Step 6 : mod-forge3d.css minimal**

Créer `frontend/cardforge/css/mod-forge3d.css` (chaque sélecteur porte `.cf-forge3d`,
règle 4) :
```css
/* P9 Forge 3D — règle 4 : tout sélecteur contient .cf-forge3d */
.cf-forge3d .cf-forge3d-card { border: 1px solid var(--stroke); border-radius: 10px; padding: 12px; }
.cf-forge3d .cf-forge3d-h { margin-bottom: 8px; }
.cf-forge3d .cf-forge3d-lay { display: flex; gap: 8px; align-items: center; padding: 4px 0; border-bottom: 1px dashed var(--stroke); }
.cf-forge3d .cf-forge3d-lay img { width: 44px; height: 62px; object-fit: contain; background: repeating-conic-gradient(rgba(128,128,128,0.18) 0% 25%, transparent 0% 50%) 0 0 / 10px 10px; }
```

- [ ] **Step 7 : forge3d.py minimal**

Créer `backend/app/services/cards/forge3d.py` (CRLF) :
```python
# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Backend, phase 1 : export par couches.

Monté par `cards/__init__.py` sous `/api/cards/{did}/forge3d`. Chemins RELATIFS.
CE FICHIER APPARTIENT À P9 (règle 8) : aucun autre module ne l'importe, il
n'importe le routeur d'aucun autre.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()

MANIFEST_SCHEMA = "card-3d/layers-manifest@1"

# ── LA TABLE DES COUCHES — BLOC MIROIR ──────────────────────────────────────
# ═══ CF-FORGE3D-LAYERS-BEGIN ═══
# Le miroir JS est dans frontend/cardforge/js/mod-forge3d.js, entre les mêmes
# marqueurs ; test_cards_forge3d compare les deux MOT POUR MOT.
# Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82).
LAYER_ROLES = [
    {"role": "fond-matiere", "z": [10], "module": "texture"},
    {"role": "illustration", "z": [20], "module": "face"},
    {"role": "voile-matiere", "z": [30], "module": "texture"},
    {"role": "cadre", "z": [40], "module": "frame"},
    {"role": "typographie", "z": [60], "module": "type"},
    {"role": "ornements", "z": [70], "module": "frame"},
]
# ═══ CF-FORGE3D-LAYERS-END ═══


@router.get("/info")
async def get_info(did: str):
    """Ce que l'écran doit savoir sans rien recalculer. Scopé au deck comme
    toute route du domaine : un id invalide fait 400, un deck absent 404."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    return {"schema": MANIFEST_SCHEMA, "layer_roles": LAYER_ROLES}
```

- [ ] **Step 8 : brancher le routeur**

`backend/app/services/cards/__init__.py` — ligne 38 devient :
```python
from . import face, frame, data, solid, texture, gltf, forge3d
```
et après la ligne 58 (`gltf.router`) :
```python
router.include_router(forge3d.router, prefix="/{did}/forge3d",
                      tags=["cards:forge3d"])
```
(TOUJOURS avant le filet `cards_not_found` — Starlette apparie dans l'ordre.)

- [ ] **Step 9 : test de parité du bloc miroir**

Ajouter à `test_cards_forge3d.py` (patron de `test_cards_type.py`) :
```python
def test_la_table_des_couches_est_identique_des_deux_cotes():
    """Bloc miroir JS <-> py, comparé champ à champ ET dans l'ordre : une
    table recopiée qui dérive est un mensonge."""
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-LAYERS-BEGIN")[1].split("CF-FORGE3D-LAYERS-END")[0]
    js_rows = re.findall(
        r'\{ role: "([a-z-]+)", z: \[([0-9, ]+)\], module: "([a-z]+)" \}', bloc)
    js_table = [{"role": r, "z": [int(x) for x in z.split(",")], "module": m}
                for r, z, m in js_rows]
    assert js_table == F9.LAYER_ROLES, (js_table, F9.LAYER_ROLES)
    # ...et les z sont un sous-ensemble EXACT de la table gelée du CORE
    core = (ROOT / "frontend" / "cardforge" / "js" / "core.js").read_text(encoding="utf-8")
    assert "Z_TABLE" in core
    tous = sorted(z for row in F9.LAYER_ROLES for z in row["z"])
    assert tous == [10, 20, 30, 40, 60, 70], tous
```

- [ ] **Step 10 : vérifier que tout passe, committer**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
```
Attendu : PASS. Puis :
```bash
git add scripts/qa/lint_cardforge.py frontend/cardforge/index.html frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/app/services/cards/__init__.py backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): piece P9 Forge 3D - squelette, table des couches miroir, lint"
```

---

### Task 2: CORE — `renderRaw` apprend `only_z` et `paper:false`

**Files:**
- Modify: `frontend/cardforge/js/core.js:646-707` (renderRaw)
- Test: `backend/tests/test_cards_forge3d.py` (assertions de source, patron maison)

- [ ] **Step 1 : test de source qui échoue**

Ajouter à `test_cards_forge3d.py` :
```python
CORE = ROOT / "frontend" / "cardforge" / "js" / "core.js"


def test_le_moteur_sait_rendre_un_sous_ensemble_sur_toile_nue():
    """`renderRaw({only_z, paper:false})` : le rendu par couches est un filtre
    du MOTEUR UNIQUE, pas un second moteur qui divergerait (règle WYSIWYG)."""
    src = CORE.read_text(encoding="utf-8")
    corps = src.split("async function renderRaw(")[1].split("\n  }")[0]
    assert "only_z" in corps, "le filtre de painters manque"
    assert "o.paper" in corps, "l'option de support papier manque"
    # le filtre s'applique DANS la boucle des painters, apres le garde z=90
    boucle = corps.split("for (let k = 0; k < PAINTERS.length; k++) {")[1]
    assert "only" in boucle.split("ctx.save()")[0]
    # le papier reste le defaut : paper !== false
    assert 'o.paper !== false' in corps
```

- [ ] **Step 2 : vérifier l'échec**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
```
Attendu : FAIL sur « le filtre de painters manque ».

- [ ] **Step 3 : implémenter dans core.js**

Dans `renderRaw` (core.js:646), après `const side = ...` (ligne 650) :
```js
    const only = Array.isArray(o.only_z) ? o.only_z : null;
    const paper = o.paper !== false;
```
Remplacer les lignes 661-666 (support + emptyPlate) par :
```js
    /* le support : plein cadre, fond perdu compris (la decoupe vient apres).
       `paper:false` (rendu par couches, P9) : toile TRANSPARENTE — la couche
       ne porte que ses propres pixels. */
    if (paper) {
      ctx.fillStyle = PAPER;
      ctx.fillRect(0, 0, w, h);
    }
    let draws = false;
    for (let k = 0; k < PAINTERS.length; k++) if (PAINTERS[k].z !== Z_GUIDES) { draws = true; break; }
    if (!draws && paper && !only) emptyPlate(ctx, g);
```
Dans la boucle des painters, après `if (p.z === Z_GUIDES) continue;` (ligne 678) :
```js
      if (only && only.indexOf(p.z) < 0) continue;   /* filtre P9, couche par couche */
```

- [ ] **Step 4 : tests + contrat géométrique**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
node frontend\cardforge\qa\test_core_contract.mjs --geom
```
Attendu : PASS des deux (le volet --geom prouve zéro régression du contrat).

- [ ] **Step 5 : commit**

```bash
git add frontend/cardforge/js/core.js backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): renderRaw only_z + paper:false - le moteur unique filtre, il ne se duplique pas"
```

---

### Task 3: CORE — `CF.layers` : cumulatifs, isolée-ou-empreinte, preuve

**Files:**
- Modify: `frontend/cardforge/js/core.js` (après cardBlob, ~ligne 740)
- Test: `backend/tests/test_cards_forge3d.py` (source) + `frontend/cardforge/qa/contract.html` + `frontend/cardforge/qa/test_core_contract.mjs` (preuve en vrai navigateur)

**Le contrat de `CF.layers(i, {face, groups})`** — `groups` = la table de P9
(`[{role, z:[...]}]`). Retour :
`{face, w, h, stack_ok, layers: [{role, z, mode: "isolee"|"empreinte", canvas}], composite, errors}`.
NOTE (revue tâche 2) : un rendu partiel n'émet plus `core:render` et n'écrase plus
`LAST_ERRORS` — ses erreurs voyagent sur la toile (`cv.cfErrors`). `CF.layers` DOIT
les collecter (union des `cfErrors` de tous ses rendus) et les rendre dans `errors` ;
une couche rendue avec erreur de painter n'est pas une couche de confiance.
Algorithme : C0 = papier seul ; pour chaque groupe k, C_k = cumulatif(z ≤ groupe k,
papier) ; solo_k = groupe k seul sur toile nue ; si `C_(k-1) + solo_k == C_k` au pixel
STRICT → mode « isolee » (la couche est un vrai isolat) ; sinon mode « empreinte » =
pixels de C_k qui diffèrent de C_(k-1) (alpha plein) — reproduction exacte PAR
CONSTRUCTION même sous `multiply/overlay/screen` (mod-texture.js:835-857). L'empilement
final DOIT reproduire le rendu d'un trait (`stack_ok`).

- [ ] **Step 1 : test de source qui échoue**

Ajouter à `test_cards_forge3d.py` :
```python
def test_cf_layers_verifie_couche_par_couche_et_avoue_le_mode():
    """Chaque couche est prouvée : isolée si elle EMPILE (pixel strict), sinon
    empreinte (delta de cumulatifs, exact par construction). Le mode est un
    constat mesuré, jamais une intention."""
    src = CORE.read_text(encoding="utf-8")
    assert "function layers(" in src or "async function layers(" in src
    corps = src.split("function layers(")[1].split("\n  }")[0]
    for attendu in ("only_z", '"isolee"', '"empreinte"', "stack_ok",
                    "getImageData"):
        assert attendu in corps, f"il manque {attendu}"
    # la comparaison est STRICTE : aucun seuil, aucune tolerance
    assert "tolerance" not in corps and "seuil" not in corps
    # les rendus passent par la MEME file serialisee que tout le monde
    assert "RENDER_CHAIN" in corps
    # l'API est publique et les blobs de couche sont mintes (provenance)
    assert re.search(r"layers:\s*layers", src), "CF.layers non exposee"
```

- [ ] **Step 2 : vérifier l'échec** — même commande, FAIL attendu sur `function layers(`.

- [ ] **Step 3 : implémenter dans core.js**

Après `cardBlob` (ligne ~740), ajouter :
```js
  /* ── P9 : LE RENDU PAR COUCHES, PROUVÉ COUCHE PAR COUCHE ────────────────
     Une couche n'est digne de confiance que si l'empilement REPRODUIT la
     carte. Or la piece Matieres pose multiply/overlay/screen (mesure) : une
     couche isolee n'empile pas toujours. Chaque groupe est donc VERIFIE au
     pixel strict : below + solo == cumulatif ? -> "isolee" ; sinon
     -> "empreinte" (les pixels que le groupe a CHANGES, alpha plein), exacte
     par construction. Aucun seuil : la difference est stricte, comme la
     passe temoin de la mesure de masquage de P1. */
  function samePixels(a, b) {
    const w = a.width, h = a.height;
    if (b.width !== w || b.height !== h) return false;
    const da = a.getContext("2d").getImageData(0, 0, w, h).data;
    const db = b.getContext("2d").getImageData(0, 0, w, h).data;
    for (let i = 0; i < da.length; i++) if (da[i] !== db[i]) return false;
    return true;
  }

  function deltaCanvas(below, cum) {
    const w = cum.width, h = cum.height;
    const out = document.createElement("canvas");
    out.width = w; out.height = h;
    const dB = below.getContext("2d").getImageData(0, 0, w, h).data;
    const img = cum.getContext("2d").getImageData(0, 0, w, h);
    const dC = img.data;
    for (let i = 0; i < dC.length; i += 4) {
      if (dC[i] === dB[i] && dC[i + 1] === dB[i + 1]
        && dC[i + 2] === dB[i + 2] && dC[i + 3] === dB[i + 3]) {
        dC[i] = 0; dC[i + 1] = 0; dC[i + 2] = 0; dC[i + 3] = 0;
      } else {
        dC[i + 3] = 255;   /* l'empreinte porte le pixel FINAL, opaque */
      }
    }
    out.getContext("2d").putImageData(img, 0, 0);
    return out;
  }

  function stackOnto(base, layer) {
    const out = document.createElement("canvas");
    out.width = base.width; out.height = base.height;
    const c = out.getContext("2d");
    c.drawImage(base, 0, 0);
    c.drawImage(layer, 0, 0);          /* source-over, seul mode autorise */
    return out;
  }

  async function layers(i, opt) {
    if (!hasDOM) throw new Error("cardforge: CF.layers exige un DOM (canvas)");
    const o = opt || {};
    const groups = Array.isArray(o.groups) ? o.groups : [];
    const face = o.face === "back" ? "back" : "front";
    const run = async () => {
      let below = await renderRaw(i, { face: face, only_z: [], paper: true });
      const out = { face: face, w: below.width, h: below.height,
                    layers: [], composite: null, stack_ok: false, errors: [] };
      const takeErrors = (cv) => {
        if (cv && cv.cfErrors && cv.cfErrors.length) {
          out.errors.push.apply(out.errors, cv.cfErrors);
        }
      };
      takeErrors(below);
      let stack = below;
      const zSoFar = [];
      for (let k = 0; k < groups.length; k++) {
        const grp = groups[k];
        for (let j = 0; j < grp.z.length; j++) zSoFar.push(grp.z[j]);
        const cum = await renderRaw(i, { face: face, only_z: zSoFar.slice(), paper: true });
        const solo = await renderRaw(i, { face: face, only_z: grp.z.slice(), paper: false });
        takeErrors(cum); takeErrors(solo);
        const isolee = samePixels(stackOnto(below, solo), cum);
        const cv = isolee ? solo : deltaCanvas(below, cum);
        out.layers.push({ role: String(grp.role || ("z" + grp.z.join("-"))),
                          z: grp.z.slice(), mode: isolee ? "isolee" : "empreinte",
                          canvas: cv });
        stack = stackOnto(stack, cv);
        below = cum;
      }
      /* le composite passe par le rendu PUBLIC (plein, evenement compris) :
         c'est le meme appel que le fichier livre. */
      out.composite = await renderRaw(i, { face: face, paper: true });
      out.stack_ok = samePixels(stack, out.composite);
      return out;
    };
    const p = RENDER_CHAIN.then(run, run);
    RENDER_CHAIN = p.then(() => { }, () => { });
    return p;
  }

  /* blob d'une toile de couche, MINTE : CF.download/M.api.blob l'acceptent. */
  async function layerBlob(cv) {
    const b = await new Promise((res, rej) => {
      cv.toBlob((x) => x ? res(x) : rej(new Error("cardforge: encodage impossible")), "image/png");
    });
    return mint(b);
  }
```
Puis exposer sur l'API publique : repérer l'objet public (celui qui porte
`renderCard: renderCard, cardBlob: cardBlob`, plus bas dans le fichier) et y ajouter :
```js
    layers: layers,
    layerBlob: layerBlob,
```

- [ ] **Step 4 : preuve EN VRAI NAVIGATEUR (harnais QA)**

Dans `frontend/cardforge/qa/contract.html`, section des checks `__CFQA` (après les
checks de rendu existants), ajouter :
```js
      /* ── P9 : couches prouvees sur les painters du banc ── */
      try {
        const L = await CF.layers(0, { face: "front", groups: [
          { role: "illustration", z: [20] }, { role: "cadre", z: [40] }] });
        ok("layers : empilement reproduit le rendu", L.stack_ok === true
          ? "stack_ok" : "ECHEC stack_ok=false");
        ok("layers : modes avoues", L.layers.map(l => l.role + "=" + l.mode).join(" "));
      } catch (e) { bad("layers", e); }
```
(`ok`/`bad` : réutiliser les helpers du fichier — repérer leur nom exact en tête de
`contract.html` ; les faux modules du banc peignent en source-over, `stack_ok` doit
être vrai et les modes « isolee ».)

- [ ] **Step 5 : tout vérifier**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
node frontend\cardforge\qa\test_core_contract.mjs --geom
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qa\cf_deploy.ps1
node frontend\cardforge\qa\test_core_contract.mjs --contract
```
Attendu : PASS partout (le --contract exige le lab déployé : `cf_deploy.ps1` sans
`-Backend` suffit pour du JS pur).

- [ ] **Step 6 : commit**

```bash
git add frontend/cardforge/js/core.js frontend/cardforge/qa/contract.html backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): CF.layers - isolee ou empreinte, prouve couche par couche au pixel strict"
```

---

### Task 4: Backend — `POST /layers` : contre-preuve, estampille, ZIP + manifeste

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : test qui échoue — l'aller-retour complet sur couches SYNTHÉTIQUES**

Le test fabrique en PIL des couches qui empilent EXACTEMENT (il est son propre
navigateur) et vérifie le manifeste sur les octets :
```python
def _couches_synthetiques(w=815, h=1110):
    """6 couches + composite qui empilent exactement, en PIL pur."""
    from PIL import Image, ImageDraw
    fond = Image.new("RGBA", (w, h), (250, 246, 238, 255))
    couches = {"fond-matiere": fond}
    for nom, boite, teinte in (
            ("illustration", (80, 120, w - 80, 620), (196, 148, 74, 255)),
            ("voile-matiere", (0, 0, w, h), (0, 0, 0, 0)),        # couche VIDE
            ("cadre", (30, 30, w - 30, h - 30), (60, 80, 140, 255)),
            ("typographie", (120, 700, w - 120, 780), (240, 236, 228, 255)),
            ("ornements", (40, 40, 140, 140), (220, 190, 90, 255))):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if teinte[3]:
            ImageDraw.Draw(im).rectangle(boite, fill=teinte)
        couches[nom] = im
    composite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for nom in ("fond-matiere", "illustration", "voile-matiere", "cadre",
                "typographie", "ornements"):
        composite = Image.alpha_composite(composite, couches[nom])
    return couches, composite


def _png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_l_export_de_couches_zippe_manifeste_et_contre_preuve():
    did = _deck("Couches")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    data = {"side": "front",
            "modes": json.dumps({n: "isolee" for n in couches}),
            "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})}
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files, data=data)
    assert r.status_code == 200, r.text
    b = r.json()["layers"]

    # le manifeste : schema, roles ordonnes, SHA-256 et boites RECALCULES ici
    assert b["schema"] == "card-3d/layers-manifest@1"
    assert [l["role"] for l in b["layers"]] == [
        "fond-matiere", "illustration", "voile-matiere", "cadre",
        "typographie", "ornements"]
    # contre-preuve backend : empilement PIL == composite, ecart mesure nul
    assert b["proof"]["backend"]["diff_px"] == 0
    assert b["proof"]["client"]["stack_ok"] is True
    # la couche vide est LIVREE et mesuree, pas devinee
    voile = [l for l in b["layers"] if l["role"] == "voile-matiere"][0]
    assert voile["coverage_pct"] == 0.0 and voile["bbox_px"] is None

    # le ZIP existe, ses entrees portent les 7 PNG + manifeste, les SHA collent
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    noms = sorted(z.namelist())
    assert "layers.json" in noms and "composite_front.png" in noms
    man = json.loads(z.read("layers.json").decode("utf-8"))
    for l in man["layers"]:
        h = hashlib.sha256(z.read(l["file"])).hexdigest()
        assert h == l["sha256"], l["file"]
    # chaque PNG livre porte son pHYs (300 DPI reels, patron P1/P8)
    px = z.read("illustration_front.png")
    assert b"pHYs" in px


def test_une_trame_fausse_fait_409_jamais_500():
    did = _deck("Trame fausse")
    im = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    files = [("layers", ("fond-matiere.png", _png(im), "image/png")),
             ("composite", ("composite.png", _png(im), "image/png"))]
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "modes": "{}", "client_proof": "{}"})
    assert r.status_code == 409, r.text
```
(imports en tête de fichier : `io, json, zipfile, hashlib`, `from PIL import Image,
ImageDraw`.)

- [ ] **Step 2 : vérifier l'échec** — FAIL attendu (404 sur /layers).

- [ ] **Step 3 : implémenter la route**

Dans `forge3d.py` (multipart : patron `print.py:post_sheet` ; ZIP+manifeste : patron
`gltf.py:build_zip` ; pHYs : écrire un helper local minimal) :
```python
import hashlib
import io
import json
import struct
import time
import zipfile
import zlib
from pathlib import Path

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .contract import deck_dir


def _out_dir(did: str, create: bool = False) -> Path:
    d = deck_dir(did) / "forge3d"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _phys_chunk(ppm_x: int, ppm_y: int) -> bytes:
    data = struct.pack(">IIB", ppm_x, ppm_y, 1)
    return (struct.pack(">I", len(data)) + b"pHYs" + data
            + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xFFFFFFFF))


def _stamp_phys(png: bytes, ppm: tuple[float, float]) -> bytes:
    """Insère un pHYs après l'IHDR — même densité que l'écran (patron P1/P8),
    relue dans les octets par les tests. Un PNG déjà estampillé est réécrit."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu")
    ihdr_end = 8 + 8 + struct.unpack(">I", png[8:12])[0] + 4
    out, off = [png[:ihdr_end]], ihdr_end
    out.append(_phys_chunk(int(round(ppm[0])), int(round(ppm[1]))))
    while off < len(png):
        ln = struct.unpack(">I", png[off:off + 4])[0]
        typ = png[off + 4:off + 8]
        if typ != b"pHYs":
            out.append(png[off:off + 8 + ln + 4])
        off += 8 + ln + 4
    return b"".join(out)


@router.post("/layers")
async def post_layers(did: str,
                      layers: list[UploadFile] = File(...),
                      composite: UploadFile = File(...),
                      side: str = Form("front"),
                      modes: str = Form("{}"),
                      client_proof: str = Form("{}")):
    """N couches PNG alpha + composite -> contre-preuve PIL, estampille,
    ZIP + manifeste. Le navigateur a DÉJÀ prouvé l'empilement chez lui
    (même moteur, pixel strict) ; ici on ré-empile en second avis et on
    écrit LES DEUX mesures dans le manifeste."""
    try:
        from PIL import Image
    except Exception as e:                     # pragma: no cover - env casse
        raise HTTPException(503, f"PIL indisponible : {e}")
    from .core import read_deck, geom_of
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    g = geom_of(doc)
    w, h = g.canvas_px
    face = "back" if str(side).strip().lower() == "back" else "front"
    try:
        modes_d = json.loads(modes or "{}")
        proof_c = json.loads(client_proof or "{}")
    except ValueError:
        modes_d, proof_c = {}, {}

    def _ouvre(raw: bytes, nom: str) -> "Image.Image":
        """Des octets illisibles font 400, jamais 500 (doctrine du domaine,
        spec 2.5) — PIL lève UnidentifiedImageError sur un corps corrompu."""
        try:
            return Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            raise HTTPException(400, f"{nom} : PNG illisible")

    par_role: dict[str, bytes] = {}
    images: dict[str, "Image.Image"] = {}
    for up in layers:
        nom = (up.filename or "").rsplit(".", 1)[0]
        raw = await up.read()
        im = _ouvre(raw, nom)
        if im.size != (w, h):
            raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
        par_role[nom], images[nom] = raw, im
    raw_comp = await composite.read()
    comp = _ouvre(raw_comp, "composite")
    if comp.size != (w, h):
        raise HTTPException(409, f"composite : trame {comp.size} != {(w, h)}")

    ordre = [r["role"] for r in LAYER_ROLES if r["role"] in par_role]
    if not ordre:
        raise HTTPException(409, "aucune couche reconnue")

    # ── contre-preuve : empilement PIL, ecart MESURE au composite ───────────
    pile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for nom in ordre:
        pile = Image.alpha_composite(pile, images[nom])
    from PIL import ImageChops
    diff = ImageChops.difference(pile, comp)
    diff_px = sum(1 for p in diff.getdata() if p != (0, 0, 0, 0))

    # LA DENSITÉ EST CELLE DE P1, PAS UNE RE-DÉRIVATION. La formule
    # « canvas_px / mm » réinjecte le bruit d'arrondi entier de canvas_px
    # (mesuré : poker_eu 300 DPI -> (11812, 11809) au lieu de 11811, 5 formats
    # sur 12 divergent). Copie LOCALE de la formule de P1 (précédents :
    # frame.py, print.py — zéro import pièce->pièce dans le domaine), avec
    # assertion de parité 300 -> 11811 dans le test.
    ppm_v = round(float(g.dpi) / 25.4 * 1000.0)   # px/m, valeur nominale isotrope
    ppm = (float(ppm_v), float(ppm_v))
    out = _out_dir(did, create=True)
    rows = []
    for nom in ordre:
        data = _stamp_phys(par_role[nom], ppm)
        fn = f"{nom}_{face}.png"
        (out / fn).write_bytes(data)
        alpha = images[nom].getchannel("A")
        bbox = alpha.getbbox()
        cover = (sum(1 for a in alpha.getdata() if a) / float(w * h) * 100.0)
        meta = next(r for r in LAYER_ROLES if r["role"] == nom)
        rows.append({
            "role": nom, "z": meta["z"], "module": meta["module"], "file": fn,
            "mode": str(modes_d.get(nom, "isolee")),
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "bbox_px": list(bbox) if bbox else None,
            "coverage_pct": round(cover, 2),
        })
    comp_fn = f"composite_{face}.png"
    comp_data = _stamp_phys(raw_comp, ppm)
    (out / comp_fn).write_bytes(comp_data)

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "deck": {"id": did, "name": doc.get("name")},
        "side": face,
        "canvas_px": [w, h],
        "size_mm": [g.trim_mm[0], g.trim_mm[1]],
        "bleed_mm": g.bleed_mm,
        "layers": rows,
        "composite": {"file": comp_fn,
                      "sha256": hashlib.sha256(comp_data).hexdigest(),
                      "bytes": len(comp_data)},
        "proof": {
            "client": {"stack_ok": bool(proof_c.get("stack_ok")),
                       "diff_px": int(proof_c.get("diff_px") or 0),
                       "note": "empilement navigateur, meme moteur, strict"},
            "backend": {"diff_px": int(diff_px),
                        "note": "re-empilement PIL alpha-over, second avis"},
        },
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            z.writestr(r["file"], (out / r["file"]).read_bytes())
        z.writestr(comp_fn, comp_data)
        z.writestr("layers.json", json.dumps(manifest, ensure_ascii=False,
                                             indent=2))
    zname = f"couches_{face}.zip"
    (out / zname).write_bytes(zbuf.getvalue())
    manifest["zip"] = {"name": zname, "bytes": len(zbuf.getvalue())}
    (out / f"layers_{face}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"layers": manifest}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit (patron P8)."""
    import re as _re
    if not _re.match(r"^[A-Za-z0-9._-]{1,90}$", name or ""):
        raise HTTPException(400, "Nom invalide")
    p = _out_dir(did) / name
    if not p.is_file():
        raise HTTPException(404, "Fichier inconnu")
    kind = "application/zip" if name.endswith(".zip") else \
        "image/png" if name.endswith(".png") else "application/json"
    return Response(p.read_bytes(), media_type=kind)
```
NOTE d'implémentation : vérifier sur place la signature exacte de `geom_of` et les
champs de `CardGeom` (`canvas_px`, `trim_mm`, `bleed_mm`) dans
`backend/app/services/cards/contract.py` — si `bleed_mm` porte un autre nom, la
densité `ppm` s'aligne sur le calcul de `face.py:stamp_png` (le recopier).

- [ ] **Step 4 : tests verts**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
```
Attendu : PASS (les 2 nouveaux tests + les anciens).

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): POST forge3d/layers - contre-preuve PIL, pHYs, ZIP + manifeste card-3d/layers-manifest@1"
```

---

### Task 5: Écran P9 — exporter, prouver, téléverser, bordereau

**Files:**
- Modify: `frontend/cardforge/js/mod-forge3d.js` (le corps d'`exportLayers`)
- Test: `backend/tests/test_cards_forge3d.py` (assertions de source)

- [ ] **Step 1 : test de source qui échoue**

```python
def test_l_ecran_prouve_avant_de_televerser_et_montre_le_bordereau():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    corps = rendu.split("async function exportLayers(")[1].split("\n  }")[0]
    # les DEUX faces partent, avec la preuve client par face
    assert 'CF.layers' in corps and '"front"' in corps and '"back"' in corps
    assert "stack_ok" in corps
    # l'echec de preuve NOMME la couche et n'envoie RIEN
    assert "return" in corps.split("stack_ok")[1].split("FormData")[0]
    # provenance : les blobs passent par CF.layerBlob (mintes)
    assert "CF.layerBlob" in corps
    # le bordereau est peint depuis la REPONSE (mesure), pas depuis l'intention
    assert "cf-forge3d-slip" in rendu
    assert "weight" in rendu or "Kio" in rendu
```

- [ ] **Step 2 : vérifier l'échec** — FAIL sur `CF.layers`.

- [ ] **Step 3 : implémenter `exportLayers` dans mod-forge3d.js**

```js
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1048576) return (v / 1024).toFixed(1) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  async function exportLayers() {
    const status = $("#cf-forge3d-status");
    const btn = $("#cf-forge3d-export");
    btn.disabled = true;
    try {
      const sides = ["front", "back"];
      const results = [];
      for (let s = 0; s < sides.length; s++) {
        const face = sides[s];
        status.textContent = "rendu des couches (" + (face === "front" ? "recto" : "verso") + ")…";
        const L = await CF.layers(CF.current ? CF.current() : 0,
          { face: face, groups: LAYER_ROLES });
        if (L.errors && L.errors.length) {
          /* une couche rendue avec une erreur de painter n'est pas une couche
             de confiance : on nomme et on n'envoie rien. */
          status.textContent = "erreur de painter pendant le rendu des couches ("
            + L.errors.map(e => e.id + " z=" + e.z).join(", ") + ") — rien n'a été envoyé.";
          M.toast("rendu des couches en erreur : export refusé", true);
          return;
        }
        if (!L.stack_ok) {
          /* la preuve a echoue : on NOMME et on n'envoie RIEN — un ZIP faux
             est pire qu'un echec dit. */
          const fautive = L.layers.filter(l => l.mode === "empreinte")
            .map(l => l.role).join(", ") || "inconnue";
          status.textContent = "preuve d'empilement ÉCHOUÉE (" + face
            + ") — couches en cause : " + fautive + ". Rien n'a été envoyé.";
          M.toast("empilement non reproduit : export refusé", true);
          return;
        }
        const fd = new FormData();
        for (let k = 0; k < L.layers.length; k++) {
          const lay = L.layers[k];
          fd.append("layers", await CF.layerBlob(lay.canvas), lay.role + ".png");
        }
        fd.append("composite", await CF.layerBlob(L.composite), "composite.png");
        fd.append("side", face);
        const modes = {};
        L.layers.forEach(l => { modes[l.role] = l.mode; });
        fd.append("modes", JSON.stringify(modes));
        fd.append("client_proof", JSON.stringify({ stack_ok: true, diff_px: 0 }));
        status.textContent = "téléversement (" + face + ")…";
        const rep = await M.api.post("layers", fd);
        results.push(rep.layers);
      }
      M.patch({ last_export: { at: Date.now ? new Date().toISOString() : "", sides: results.length } });
      paintSlip(results);
      status.textContent = "couches livrées, preuve tenue des deux côtés.";
    } catch (e) {
      status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      btn.disabled = false;
    }
  }

  function paintSlip(results) {
    const slip = $("#cf-forge3d-slip");
    if (!slip) return;
    slip.innerHTML = results.map(man => {
      const rows = man.layers.map(l =>
        '<div class="cf-forge3d-lay"><img src="' + M.api.url("file/" + l.file)
        + '" alt=""><span class="mono">' + l.role + " · " + l.mode + " · "
        + l.coverage_pct + " % · " + weight(l.bytes) + "</span></div>").join("");
      return '<h4>' + (man.side === "front" ? "Recto" : "Verso") + '</h4>' + rows
        + '<p class="mono">empilement : navigateur strict OK · second avis PIL '
        + man.proof.backend.diff_px + ' px d\'écart · '
        + '<a href="' + M.api.url("file/" + man.zip.name) + '">'
        + man.zip.name + " (" + weight(man.zip.bytes) + ")</a></p>";
    }).join("");
  }
```
NOTE : vérifier la signature exacte de `M.api.post` et `M.api.url` pour un FormData —
le précédent est dans `mod-print.js` (rechercher `FormData` ; si l'api du jeton passe
par `api("POST", path, body)`, adapter l'appel à l'identique).

- [ ] **Step 4 : tests + lint + déploiement lab + vérification navigateur**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
python scripts\qa\lint_cardforge.py --module forge3d
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qa\cf_deploy.ps1 -Backend
```
Puis dans le navigateur (`http://127.0.0.1:8765/cardforge/`) : onglet 09 → « Exporter
les couches » sur un deck réel (avec cadre + typo actifs) ; attendre le bordereau ;
télécharger le ZIP ; VÉRIFIER : 7 PNG + layers.json, la couche voile en mode
« empreinte » si un voile Matières est actif, `proof.backend.diff_px` à 0 ou avoué.

- [ ] **Step 5 : commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): ecran P9 - export des couches deux faces, preuve avant envoi, bordereau mesure"
```

---

### Task 6: Intégration finale de la phase

**Files:** aucun nouveau — vérifications et livraison.

- [ ] **Step 1 : suite complète du domaine cartes**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards
```
Attendu : 10 fichiers sur 10 PASS (les 9 existants + `test_cards_forge3d.py`).

- [ ] **Step 2 : contrats et lint complets**

```powershell
python scripts\qa\lint_cardforge.py
node frontend\cardforge\qa\test_core_contract.mjs
```
Attendu : lint 0 violation (9 modules complets) ; contrat géométrie + cloisonnement OK.

- [ ] **Step 3 : zéro écart dépôt/app**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qa\cf_deploy.ps1 -Check
```
Attendu : « 0 ecart ».

- [ ] **Step 4 : commit de clôture + push**

```bash
git add -A
git commit -m "feat(cardforge): phase 1 couches - suite verte, lab deploye, preuve d'empilement tenue" --allow-empty
git push origin claude/audit-cleanup-2026-08
```
(le `--allow-empty` ne sert que si les steps précédents ont tout commité ; sinon le
commit porte les restes.)

---

## Auto-revue du plan (faite à l'écriture)

- **Couverture spec §4** : couches et rôles (§4.1 → Tasks 1/3), preuve stricte client +
  second avis (§4.2 → Tasks 3/4/5), route/stockage/manifeste (§4.3 → Task 4), bordereau
  écran (§4.3 → Task 5). Le mode « empreinte » couvre la réalité mesurée des blend
  modes de Matières (mod-texture.js:835-857) — la spec disait « échec nommé » ; le plan
  fait mieux : reproduction exacte quand même, ET le mode avoué dans le manifeste.
- **Hors périmètre de cette phase** : rien du graphe (phase 2), rien de l'import.
- **Cohérence de types** : `LAYER_ROLES` (JS et py) portent les mêmes clés
  `role/z/module` ; `CF.layers` retourne `layers[].mode` que `modes` (Form) transporte
  et que le manifeste réécrit ; `layerBlob` est le seul chemin de blob (provenance).
- **Deux notes de vérification sur place** (signature `M.api.post` FormData, champs de
  `CardGeom`) : bornées, avec le fichier de référence exact à consulter.
