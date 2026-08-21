# Cardforge Phase 1 — Export par couches : plan d'implémentation

> **Extraits resynchronisés a posteriori (audit de couture du 2026-08-21)** :
> les extraits python ci-dessous sont alignés sur le code livré à la clôture
> de la phase 1 (commit 3c3a96d) ; les évolutions ultérieures (2a, 2b) vivent
> dans leurs propres plans. En cas d'écart résiduel, le code livré fait foi.

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
    # /info est scopée au deck comme toute route du domaine (règle §2.5) :
    # un id syntaxiquement invalide lève 400, un id valide mais absent 404.
    assert _api("GET", "/api/cards/nimportequoi/forge3d/info").status_code == 400
    assert _api("GET", "/api/cards/deck_00000000/forge3d/info").status_code == 404
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
    """Ce que l'écran doit savoir sans rien recalculer."""
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
    """Bloc miroir JS <-> py : une table recopiée qui dérive est un mensonge."""
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
    # I1 : la normalisation doit garder [] tel quel : [] = aucun painter,
    # null = tous — un .length ici casserait le cumulatif C0
    assert "Array.isArray(o.only_z) ? o.only_z : null" in corps, \
        "la normalisation doit garder [] tel quel : [] = aucun painter, null = tous — un .length ici casserait le cumulatif C0"
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
    # C1 : identite de carte — par defaut card="0", donc c01
    assert b["card"] == {"index": 0, "label": "c01"}
    # C2 : la base papier REELLEMENT peinte par le moteur voyage dans le
    # manifeste (defaut du formulaire : blanc, PAPER de core.js)
    assert b["paper"] == "#ffffff"
    # contre-preuve backend : empilement PIL == composite, ecart mesure nul
    assert b["proof"]["backend"]["diff_px"] == 0
    assert b["proof"]["client"]["stack_ok"] is True
    # la couche vide est LIVREE et mesuree, pas devinee
    voile = [l for l in b["layers"] if l["role"] == "voile-matiere"][0]
    assert voile["coverage_pct"] == 0.0 and voile["bbox_px"] is None
    assert voile["bbox_mm"] is None    # boite vide : None des deux cotes

    # reliquat de revue phase 1 : le manifeste porte le format du deck et la
    # densite pHYs REELLEMENT ecrite (memes octets que ceux relus plus bas),
    # et chaque couche non vide porte sa boite convertie en mm a cote de sa
    # boite en pixels — deck par defaut : poker_eu, 300 DPI.
    assert b["format"] == "poker_eu"
    assert b["phys_ppm"] == 11811
    cadre = [l for l in b["layers"] if l["role"] == "cadre"][0]
    assert cadre["bbox_px"] is not None and cadre["bbox_mm"] is not None
    # bbox_mm = bbox_px * dimensions physiques TOTALES / canvas_px — poker_eu
    # a 300 DPI : canvas = 815 x 1110 px pour 69 x 94 mm (trim + fond perdu
    # des deux cotes), donc c'est bien la trame w x h qui divise, pas trim_mm
    # seul (qui sous-evaluerait toute couche qui deborde dans le fond perdu).
    bx = cadre["bbox_px"]
    attendu_mm = [round(bx[0] * 69.0 / 815, 2), round(bx[1] * 94.0 / 1110, 2),
                 round(bx[2] * 69.0 / 815, 2), round(bx[3] * 94.0 / 1110, 2)]
    assert cadre["bbox_mm"] == attendu_mm

    # le ZIP existe, ses entrees portent les 7 PNG + manifeste, les SHA collent
    rz = _api("GET", f"/api/cards/{did}/forge3d/file/{b['zip']['name']}")
    assert rz.status_code == 200
    # patron P8 : Content-Disposition + Cache-Control sur le livrable
    assert rz.headers.get("content-disposition", "").startswith("attachment")
    assert rz.headers.get("cache-control") == "no-store"
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    noms = sorted(z.namelist())
    assert "layers.json" in noms and "composite_c01_front.png" in noms
    man = json.loads(z.read("layers.json").decode("utf-8"))
    for l in man["layers"]:
        h = hashlib.sha256(z.read(l["file"])).hexdigest()
        assert h == l["sha256"], l["file"]
    # chaque PNG livre porte son pHYs, et la VALEUR relue dans les octets
    # est celle de P1 - pas seulement sa presence (patron P1/P8, la deck
    # par defaut est a 300 DPI). Parite : copie locale == 11811 == pHYs reel.
    from app.services.cards import forge3d as F9
    assert F9._dpi_to_ppm(300) == 11811
    px = z.read("illustration_c01_front.png")
    i = px.find(b"pHYs")
    assert i >= 0, "pHYs absent"
    ppm_x, ppm_y, unite = struct.unpack(">IIB", px[i + 4:i + 13])
    assert (ppm_x, ppm_y, unite) == (F9._dpi_to_ppm(300), F9._dpi_to_ppm(300), 1) \
        == (11811, 11811, 1)


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
    """Insère sRGB + gAMA + cHRM puis pHYs après l'IHDR — ordre P1 (IHDR ·
    sRGB · gAMA · cHRM · pHYs, `face.py:png_finalize`) : même espace de
    couleur et même densité que l'écran, relus dans les octets par les
    tests. Un PNG déjà estampillé (n'importe lequel des 4 chunks) est
    réécrit, jamais doublé.

    La boucle est BORNÉE et s'arrête à IEND : un PNG à queue parasite (des
    octets après IEND — navigateurs et outils en écrivent bel et bien) passe
    le décodage PIL sans broncher, mais faisait planter `struct.unpack` sur
    un fragment de moins de 4 octets — 500 non attrapé, reproduit en revue."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu")
    ihdr_end = 8 + 8 + struct.unpack(">I", png[8:12])[0] + 4
    out, off = [png[:ihdr_end]], ihdr_end
    out.extend(_srgb_chunks())
    out.append(_phys_chunk(int(round(ppm[0])), int(round(ppm[1]))))
    while off + 8 <= len(png):
        ln = struct.unpack(">I", png[off:off + 4])[0]
        typ = png[off + 4:off + 8]
        end = off + 8 + ln + 4
        if end > len(png):
            break
        if typ not in _PREPRESS_TYPES:
            out.append(png[off:end])
        off = end
        if typ == b"IEND":
            break
    return b"".join(out)


@router.post("/layers")
async def post_layers(did: str,
                      layers: list[UploadFile] = File(...),
                      composite: UploadFile = File(...),
                      side: str = Form("front"),
                      card: str = Form("0"),
                      paper: str = Form("#ffffff"),
                      modes: str = Form("{}"),
                      client_proof: str = Form("{}")):
    """N couches PNG alpha + composite -> contre-preuve PIL, estampille,
    ZIP + manifeste. Le navigateur a DÉJÀ prouvé l'empilement chez lui
    (même moteur, pixel strict) ; ici on ré-empile en second avis et on
    écrit LES DEUX mesures dans le manifeste.

    `card` (C1) : l'index de la carte courante, tel que l'écran l'a rendu
    (même valeur que le temps de preuve). Sans lui, les sorties ne portaient
    que deck+side : exporter la carte B écrasait les fichiers de la carte A.
    Les noms de sortie et le manifeste portent désormais `c{idx+1:02d}`.

    `paper` (C2) : la base RÉELLEMENT peinte par le moteur (`PAPER` de
    core.js, jamais une constante recopiée ailleurs). La contre-preuve
    empilait sur transparent ; le ZIP seul ne reproduisait alors pas le
    composite dès que le papier de la pièce Matières passe à « none ».

    `await up.read()` reste async (c'est de l'E/S) ; tout le reste — décodage,
    empilement, mesures, estampilles, zip, écritures — est du calcul pur et
    tourne dans `work()`, déporté par `asyncio.to_thread` (patron des sœurs :
    gltf.py:post_build, gltf.py:post_atlas, print.py:post_card). Mesuré :
    l'inline gelait la boucle d'évènements de 0,45 s (poker 300 DPI) à plus
    de 2,6 s (tarot 600 DPI)."""
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
    # C1 : l'identite de la CARTE dans toute la chaine — sans elle, exporter
    # la carte B ecrase les fichiers de la carte A (sorties nommees par
    # deck+side seulement, avant ce correctif).
    idx = _card_idx(card)
    card_label = f"c{idx + 1:02d}"
    # C2 : la base papier — validee AVANT le calcul, jamais recalculee dans
    # `work()` a partir d'une valeur non sure.
    paper_hex = _paper_hex(paper)

    # ── bornes AVANT décodage : compte, puis rôle — aucune des deux ne lit
    #    un octet du corps du fichier ─────────────────────────────────────
    if len(layers) > MAX_LAYER_FILES:
        raise HTTPException(
            400, f"trop de couches ({len(layers)}, maximum {MAX_LAYER_FILES})")
    valid_roles = {r["role"] for r in LAYER_ROLES}
    noms: list[str] = []
    seen: set[str] = set()
    for up in layers:
        nom = (up.filename or "").rsplit(".", 1)[0]
        if nom not in valid_roles:
            raise HTTPException(400, f"{nom!r} : rôle de couche inconnu")
        if nom in seen:
            raise HTTPException(400, f"{nom!r} : couche envoyée deux fois")
        seen.add(nom)
        noms.append(nom)

    # ── modes / preuve client : JSON valide mais pas un objet -> réparé,
    #    jamais 500 (spec 2.5) ; le mode est validé contre le vocabulaire
    #    fermé du CORE ────────────────────────────────────────────────────
    try:
        modes_d = json.loads(modes or "{}")
    except ValueError:
        modes_d = {}
    if not isinstance(modes_d, dict):
        modes_d = {}
    for role, mode in modes_d.items():
        if str(mode) not in LAYER_MODES:
            raise HTTPException(
                400, f"mode inconnu pour {role!r} : {mode!r} "
                     f"(attendu {sorted(LAYER_MODES)})")
    try:
        proof_c = json.loads(client_proof or "{}")
    except ValueError:
        proof_c = {}
    if not isinstance(proof_c, dict):
        proof_c = {}

    # ── lecture des octets (E/S -> reste async), bornée AVANT tout décodage
    raw_par_role: dict[str, bytes] = {}
    for up, nom in zip(layers, noms):
        raw = await up.read()
        if len(raw) > MAX_LAYER_BYTES:
            raise HTTPException(
                413, f"{nom} : fichier trop lourd ({len(raw)} o, "
                     f"maximum {MAX_LAYER_BYTES} o)")
        raw_par_role[nom] = raw
    raw_comp = await composite.read()
    if len(raw_comp) > MAX_LAYER_BYTES:
        raise HTTPException(
            413, f"composite : fichier trop lourd ({len(raw_comp)} o, "
                 f"maximum {MAX_LAYER_BYTES} o)")

    def work() -> dict:
        from PIL import Image, ImageChops

        def _ouvre(raw: bytes, nom: str):
            """Un corps mal formé fait 400, JAMAIS 500 (spec 2.5). `format`
            est lu AVANT `convert()` : la conversion RGBA renvoie une image
            neuve dont `.format` vaut None — le vérifier après serait un
            contrôle qui ne contrôle rien."""
            try:
                im = Image.open(io.BytesIO(raw))
                im.load()
            except Exception as e:
                raise HTTPException(400, f"{nom} : PNG illisible ({e})")
            fmt = (im.format or "").upper()
            if fmt != "PNG":
                raise HTTPException(
                    400, f"{nom} : PNG attendu, {fmt or 'format inconnu'} reçu")
            return im.convert("RGBA")

        images: dict[str, "Image.Image"] = {}
        for nom, raw in raw_par_role.items():
            im = _ouvre(raw, nom)
            if im.size != (w, h):
                raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
            images[nom] = im
        comp = _ouvre(raw_comp, "composite")
        if comp.size != (w, h):
            raise HTTPException(409, f"composite : trame {comp.size} != {(w, h)}")

        ordre = [r["role"] for r in LAYER_ROLES if r["role"] in images]
        if not ordre:
            raise HTTPException(409, "aucune couche reconnue")

        # ── contre-preuve : empilement PIL, ecart MESURE au composite ──────
        # C2 : la base est le PAPIER reellement peint par le moteur (validee
        # en amont dans `paper_hex`), pas transparent — le composite REEL
        # (cote navigateur) est peint sur ce meme papier avant les couches ;
        # empiler sur transparent divergeait en masse des que la couche
        # fond-matiere ne couvre plus tout le canevas (papier « none »).
        pile = Image.new("RGBA", (w, h), _paper_rgba(paper_hex))
        for nom in ordre:
            pile = Image.alpha_composite(pile, images[nom])
        diff = ImageChops.difference(pile, comp)
        # getdata() est déprécié (retrait Pillow 14) — équivalence mesurée
        # (scratchpad/bench_forge3d.py) : fast-path getbbox() si aucun écart,
        # sinon histogramme du canal fusionné (0 == pixels IDENTIQUES sur les
        # 4 bandes, donc w*h - ce compte = pixels qui diffèrent).
        if diff.getbbox() is None:
            diff_px = 0
        else:
            fusion = reduce(ImageChops.lighter, diff.split())
            diff_px = w * h - fusion.histogram()[0]

        ppm = float(_dpi_to_ppm(g.dpi))
        phys_ppm = int(round(ppm))    # la valeur EXACTE que `_phys_chunk`
                                       # écrit dans les octets (même arrondi)
        # dimensions physiques TOTALES de la trame (w, h) == canvas_px, donc
        # trim + fond perdu des DEUX côtés — pas trim_mm seul, qui ne couvre
        # que la carte coupée et sous-évaluerait bbox_mm sur toute couche qui
        # déborde dans le fond perdu.
        size_mm_totale = (g.trim_mm[0] + 2.0 * g.bleed_mm,
                          g.trim_mm[1] + 2.0 * g.bleed_mm)
        zip_entries: dict[str, bytes] = {}
        rows = []
        for nom in ordre:
            data = _stamp_phys(raw_par_role[nom], (ppm, ppm))
            fn = f"{nom}_{card_label}_{face}.png"
            zip_entries[fn] = data
            alpha = images[nom].getchannel("A")
            bbox = alpha.getbbox()
            # coverage : w*h - (pixels d'alpha nul), même mesure histogramme
            cover = ((w * h - alpha.histogram()[0]) / float(w * h) * 100.0)
            meta = next(r for r in LAYER_ROLES if r["role"] == nom)
            # bbox_mm : la MEME boîte, convertie par les dimensions physiques
            # (bbox_px * size_mm_totale / canvas_px) — None si bbox_px l'est,
            # jamais une conversion inventée sur une couche vide.
            bbox_mm = None if bbox is None else [
                round(bbox[0] * size_mm_totale[0] / w, 2),
                round(bbox[1] * size_mm_totale[1] / h, 2),
                round(bbox[2] * size_mm_totale[0] / w, 2),
                round(bbox[3] * size_mm_totale[1] / h, 2),
            ]
            rows.append({
                "role": nom, "z": meta["z"], "module": meta["module"],
                "file": fn,
                "mode": str(modes_d.get(nom, "isolee")),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "bbox_px": list(bbox) if bbox else None,
                "bbox_mm": bbox_mm,
                "coverage_pct": round(cover, 2),
            })
        comp_fn = f"composite_{card_label}_{face}.png"
        comp_data = _stamp_phys(raw_comp, (ppm, ppm))
        zip_entries[comp_fn] = comp_data

        manifest = {
            "schema": MANIFEST_SCHEMA,
            "deck": {"id": did, "name": doc.get("name")},
            "card": {"index": idx, "label": card_label},
            "side": face,
            "format": g.fmt,
            "paper": paper_hex,
            "canvas_px": [w, h],
            "size_mm": [g.trim_mm[0], g.trim_mm[1]],
            "bleed_mm": g.bleed_mm,
            "phys_ppm": phys_ppm,
            "layers": rows,
            "composite": {"file": comp_fn,
                          "sha256": hashlib.sha256(comp_data).hexdigest(),
                          "bytes": len(comp_data)},
            "proof": {
                "client": {"stack_ok": bool(proof_c.get("stack_ok")),
                           "diff_px": int(_num(proof_c.get("diff_px"), 0,
                                               0, w * h)),
                           "note": "empilement navigateur, meme moteur, strict"},
                "backend": {"diff_px": int(diff_px),
                            "note": "re-empilement PIL alpha-over, second avis"},
            },
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # ── ZIP : octets EN MÉMOIRE, jamais de relecture disque ────────────
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            for fn, data in zip_entries.items():
                z.writestr(fn, data)
            z.writestr("layers.json", json.dumps(manifest, ensure_ascii=False,
                                                 indent=2))
        zname = f"couches_{card_label}_{face}.zip"
        zip_bytes = zbuf.getvalue()
        manifest["zip"] = {"name": zname, "bytes": len(zip_bytes)}

        out = _out_dir(did, create=True)
        for fn, data in zip_entries.items():
            (out / fn).write_bytes(data)
        (out / zname).write_bytes(zip_bytes)
        (out / f"layers_{card_label}_{face}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return manifest

    try:
        manifest = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except ModuleNotFoundError as e:           # pragma: no cover - env casse
        raise HTTPException(503, f"Module requis absent : {e}")
    except Exception as e:
        logger.exception("cards/forge3d: export de couches impossible")
        raise HTTPException(500, f"Export de couches impossible : {e}")
    return {"layers": manifest}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit (patron P8)."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    import re as _re
    if not _re.match(r"^[A-Za-z0-9._-]{1,90}$", name or ""):
        raise HTTPException(400, "Nom invalide")
    p = _out_dir(did) / name
    if not p.is_file():
        raise HTTPException(404, "Fichier inconnu")
    kind = "application/zip" if name.endswith(".zip") else \
        "image/png" if name.endswith(".png") else "application/json"
    return Response(p.read_bytes(), media_type=kind, headers={
        "Content-Disposition": f'attachment; filename="{p.name}"',
        "Cache-Control": "no-store"})
```
NOTE d'implémentation : vérifier sur place la signature exacte de `geom_of` et les
champs de `CardGeom` (`canvas_px`, `trim_mm`, `bleed_mm`) dans
`backend/app/services/cards/contract.py` — si `bleed_mm` porte un autre nom, la
densité `ppm` s'aligne sur le calcul de `face.py:stamp_png` (le recopier).

NOTE de revue (obligatoire, apprise sur la première implémentation) :
1. **Travail lourd HORS event loop** — patron des sœurs : `await up.read()` en
   async, puis TOUT le reste (décodage, empilement, mesures, estampilles, zip,
   écritures) dans un `def work():` passé à `asyncio.to_thread`, avec
   `except HTTPException: raise` (P7 `print.py:3668+`, P8 `gltf.py:3961+`).
   Mesuré : l'inline gèle le backend 0,45 s (poker 300) à 2,6 s+ (tarot 600).
2. **Bornes AVANT décodage** : constante locale 64 Mo par fichier (précédent
   `gltf.py:MAX_ATLAS_BYTES`, copie règle 8) → 413 ; plafond de compte
   (12 fichiers) → 400 ; rôle inconnu ou en double → 400 (le seul producteur
   légitime est core.js, un autre nom est un bug à révéler).
3. **Jamais 500, chemins mesurés** : `modes`/`client_proof` normalisés après
   parse (`isinstance(dict)` sinon `{}` ; `diff_px` par garde numérique) ;
   `modes` validé contre le vocabulaire fermé {isolee, empreinte} (400 sinon) ;
   `_stamp_phys` borné (`while off + 8 <= len(png)`, arrêt à IEND — un PNG à
   queue parasite passe PIL puis plantait struct) ; `_ouvre` exige
   `im.format == "PNG"` (400 nommé — un JPEG ne doit pas traverser la
   contre-preuve) ; `GET /file` garde `is_valid_did`/`read_deck` comme /info.
4. **Mesures idiomatiques** : `diff.getbbox() is None` en fast-path puis
   `reduce(ImageChops.lighter, diff.split()).histogram()[0]` ; coverage par
   `w*h - alpha.histogram()[0]` — exact, ~10× plus rapide, et `getdata()` est
   déprécié (retrait Pillow 14). Le ZIP écrit les octets EN MÉMOIRE
   (`z.writestr(r["file"], data)`), jamais une relecture disque.
5. `GET /file` : `Content-Disposition` + `Cache-Control` comme P8.

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
    # l'identite de carte et la base papier partent bel et bien avec chaque
    # envoi — des defauts backend (card="0", paper="#ffffff") rendraient
    # leur suppression invisible aux tests d'integration (200 quand meme) :
    # ce test cible litteralement l'appel, pas seulement son effet observe.
    assert 'fd.append("card"' in corps
    assert 'fd.append("paper"' in corps
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
