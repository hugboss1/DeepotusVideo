# Cardforge Phase 2b — mesh3d payant (7 moteurs), matières, iridescence, fusion GLB : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le graphe P9 monte en gamme : nœuds `mesh3d` payants (5 moteurs fal + **meshy-6 /
meshy-7 via l'API Meshy DIRECTE**, clé de l'utilisateur, prix/crédits affichés AVANT),
nœuds `material` (matières Material Forge + finitions holographiques iridescence/
anisotropy/clearcoat), nœud `transform`, et la FUSION des GLB externes dans l'artefact —
plus les 6 points du « Legs à la 2b » du plan 2a.

**Architecture:** Les moteurs fal passent par les coutures de `asset3d_service`
(_upload/_run_engine, patchées en tests) ; les moteurs Meshy passent par
`meshy_service` (proxy/tarifs/mock DÉJÀ livrés par le 3D Studio v2.1) enrichi de deux
helpers serveur mock-aware — les tests du flux Meshy roulent sur `MESHY_MOCK=1`, ZÉRO
crédit dépensé. Chaque job `mesh3d` écrit dans `forge3d/nodes/{nid}/` (job.json = état
durable, registre en mémoire = détection de redémarrage), et son `closed` est mesuré
UNE fois à l'import puis caché (legs 1-2). Le writer de scène gagne les maps de matière
(basecolor = LA COUCHE, la matière fournit normal/roughness/metallic/ao/emissive —
spec §5.2), les recettes §6.2bis-c (extensions dans `extensionsUsed` UNIQUEMENT), le
TRS par élément (legs 3), et un assembleur de GLB externes par réindexation pure-Python
(spec §5.4). Avant tout ça : la découpe `forge3d_scene.py` (legs 6), parce que le
fichier va grossir de ~1000 lignes.

**Tech Stack:** P9 existant (mod-forge3d.js / forge3d.py / test_cards_forge3d.py),
PIL pur, struct/json stdlib, `asset3d_service` (fal), `meshy_service` (API Meshy
directe + mock), `material_store`/`pbr_service` (maps), `pricing.py`, model-viewer
vendored 3.3.3 (iridescence/anisotropy vérifiés sur les octets du bundle).

**Dépendances :** phase 2a livrée (949f47d) — graphe gratuit, `write_scene_glb`,
`build3d`, manifeste post-compléments `layers_c{NN}_{side}.json`.

**Références obligatoires :** le préambule du plan phase 1
(`2026-08-19-cardforge-phase1-couches.md` : harnais un-processus-par-fichier, EOL/UTF-8
sans BOM (vérifier les octets après CHAQUE édition de .js/.mjs), déploiement
`cf_deploy.ps1`, interdits) + la « NOTE de revue » de sa Task 4 (to_thread, bornes,
jamais-500 mesuré) pour TOUTE nouvelle route. Branche : celle du chantier courant
(`git status` d'abord ; les phases 1/2a ont poussé sur `claude/audit-cleanup-2026-08`).

**Règle d'argent (transversale) :** aucun test, aucune vérification navigateur ne
dépense un centime ni un crédit. fal = coutures monkeypatchées ; Meshy = `MESHY_MOCK=1`.
Un tir réel meshy-7 sur les crédits de l'utilisateur = proposition en fin de chantier,
jamais un fait accompli.

---

## Structure de fichiers

| Fichier | Sort | Responsabilité |
|---|---|---|
| `backend/app/services/cards/forge3d_scene.py` | **Créé** (Task 1) | TOUTE la géométrie/écriture pure (zéro FastAPI) : quad/relief, mesures, writer glTF, STL deux-passes, tuilage de maps, finitions holo, lecture/fusion de GLB |
| `backend/app/services/cards/forge3d.py` | Modifié | routes + vocabulaire + validation + jobs mesh3d (réexporte la géométrie pour compat tests) |
| `backend/app/services/meshy_service.py` | Modifié (Task 2) | grille meshy-7/ultra + helpers serveur `create_task`/`get_task` mock-aware |
| `frontend/meshy/meshy.client.js` | Modifié (Task 2) | miroir de la grille (CREDITS) + `ultra` |
| `backend/tests/test_meshy_service.py` | Modifié (Task 2) | asserts meshy-7/ultra + helpers |
| `frontend/studio3d/studio3d.js` | Modifié (Task 2) | option `meshy-7` du 3D Studio (gamme Assets) |
| `backend/app/services/pricing.py` | Modifié (Task 3) | `meshy_credit_usd` (directionnel, éditable) |
| `frontend/cardforge/js/mod-forge3d.js` | Modifié (Tasks 3, 7) | miroir NODE_KINDS 2b + rangées chaînées + Lancer/polling + coût AVANT + legs 5 |
| `frontend/cardforge/css/mod-forge3d.css` | Modifié (Task 7) | blocs mesh3d/matière/transform, chips d'état, pied de coût |
| `backend/tests/test_cards_forge3d.py` | Modifié (toutes) | la preuve de tout ce qui précède |
| `scripts/qa/lint_cardforge.py` | Modifié SI besoin (Task 1) | autorisation NOMMÉE de `forge3d_scene.py` dans le module forge3d |

Stockage : `outputs/decks/{did}/forge3d/nodes/{nid}/` = `job.json`, `upload_src.png`,
`model.glb`, `preview.png`, `textures/…` (legs 2). Les nœuds gratuits restent à plat.

---

### Task 1: La découpe `forge3d_scene.py` + le writer STL deux-passes (legs 6)

> **LIVRÉE (91e7ddd + correctifs de revue b559512) — amendements actés en revue,
> qui prévalent sur les extraits ci-dessous :** (1) le test s'appelle
> `test_la_geometrie_vit_dans_forge3d_scene_et_le_stl_garde_son_contrat_d_octets`
> et porte EN PLUS un bloc « contrat d'octets de la facette » (en-tête sans
> horodatage, sommets dans l'ordre, z_mm appliqué, normale unitaire — mutants
> winding/z_mm/normales/timestamp TUÉS, mesuré) ; (2) l'en-tête STL réel est
> `f"{name} - millimetres - {total} triangles"` (le code existant avait raison,
> comme prévu) ; (3) le lint scanne AUSSI le sidecar : `EXTRA_PY = {"forge3d":
> ["forge3d_scene.py"]}` + `check_r8(..., require_router=False)` pour lui (R8
> complet sauf l'exigence d'un routeur propre, absent par conception) ; (4) le
> module porte un avertissement : le test de pureté scanne TOUT le source, le
> nom du framework HTTP ne doit apparaître nulle part, même en prose ; deux-passes
> mesuré 267→57 Mo de pic sur 575k triangles (propriété d'implémentation, pas
> d'assert). Étapes cochées ci-dessous.

**Files:**
- Create: `backend/app/services/cards/forge3d_scene.py`
- Modify: `backend/app/services/cards/forge3d.py`
- Modify: `scripts/qa/lint_cardforge.py` (SEULEMENT si le lint refuse le nouveau fichier)
- Test: `backend/tests/test_cards_forge3d.py`

La couture est celle tracée par la revue finale de la 2a : le bloc géométrie pure —
`quad_mesh`, `relief_mesh`, `mesh_measures`, `write_scene_glb`, `_write_stl_binary` —
part TEL QUEL dans `forge3d_scene.py` (imports `math/json/struct/io` qu'il faut, AUCUN
import FastAPI/routeur). `forge3d.py` les RÉEXPORTE (`from .forge3d_scene import
quad_mesh, relief_mesh, mesh_measures, write_scene_glb, _write_stl_binary`) : les tests
et les routes ne changent pas d'orthographe. Les CONSTANTES (bornes, blocs miroir)
restent dans `forge3d.py` — elles appartiennent au contrat de l'API.

- [x] **Step 1 : test en RED (contrat d'octets + réexport)**

```python
def test_la_geometrie_vit_dans_forge3d_scene_et_le_stl_garde_son_contrat_d_octets():
    """Legs 6 : la couture intra-pièce. Le module scène n'importe pas FastAPI ;
    forge3d réexporte (compat) ; le writer STL garde son CONTRAT D'OCTETS —
    structure, normale unitaire, ordre des sommets, z_mm appliqué, en-tête
    sans horodatage — pas seulement sa taille (mutants tués en revue)."""
    # stratégie deux-passes mesurée en revue : pic 267 Mo → 57 Mo sur 575k
    # triangles — propriété d'implémentation, pas d'assert ici (un budget
    # mémoire flakerait).
    import importlib
    from app.services.cards import forge3d as F9
    scene = importlib.import_module("app.services.cards.forge3d_scene")
    src = (ROOT / "backend" / "app" / "services" / "cards" /
           "forge3d_scene.py").read_text(encoding="utf-8")
    assert "fastapi" not in src.lower() and "APIRouter" not in src
    for nom in ("quad_mesh", "relief_mesh", "mesh_measures",
                "write_scene_glb", "_write_stl_binary"):
        assert getattr(F9, nom) is getattr(scene, nom), nom

    m = scene.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0, 0.3, 8)
    m["closed"] = True
    stl = scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": 0.0}], "x")
    n = struct.unpack("<I", stl[80:84])[0]
    assert n == len(m["indices"]) // 3
    assert len(stl) == 84 + 50 * n
    # déterminisme : deux appels, mêmes octets
    assert stl == scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": 0.0}], "x")

    # Le CONTRAT d'octets de la facette, pas seulement sa taille : normale
    # UNITAIRE, sommets dans l'ORDRE du triangle, z_mm APPLIQUÉ (le format STL
    # n'a pas de nœud pour le porter) et en-tête SANS horodatage. Sans ça, une
    # réécriture du writer passe la suite en inversant le winding, en perdant
    # l'empilement ou en datant le fichier (mutants mesurés en revue).
    assert stl[:80].rstrip(b"\x00") == f"x - millimetres - {n} triangles".encode()
    dz = 4.25
    stl_z = scene._write_stl_binary([{"name": "a", "mesh": m, "z_mm": dz}], "x")
    f0 = struct.unpack_from("<12fH", stl_z, 84)
    pos, idx = m["positions"], m["indices"]
    for s, iv in enumerate((idx[0] * 3, idx[1] * 3, idx[2] * 3)):
        for k in range(3):
            attendu = pos[iv + k] + (dz if k == 2 else 0.0)
            assert f0[3 + s * 3 + k] == pytest.approx(attendu, abs=1e-4), (s, k)
    assert sum(v * v for v in f0[:3]) == pytest.approx(1.0, abs=1e-5)
    assert f0[12] == 0
```

Run : `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d` — FAIL (module absent).

- [x] **Step 2 : créer `forge3d_scene.py`**

Déplacement TEXTUEL des cinq fonctions (aucune réécriture au passage, à UNE exception :
le corps de `_write_stl_binary`). En-tête du fichier :

```python
"""P9 Forge 3D — géométrie et écriture de scène, PURES (zéro FastAPI).

Couture intra-pièce actée par la revue finale de la 2a (legs 6) : forge3d.py
garde le contrat HTTP (routes, bornes, blocs miroir) et RÉEXPORTE ces noms —
les tests et l'API ne changent pas. Règle 8 inchangée : aucune importation
d'une autre pièce du lab.
"""
```

Le writer STL réécrit en DEUX PASSES (même sortie au bit près, sans matérialiser des
tuples ; garder l'en-tête 80 octets SANS nom d'outil et l'unité mm tels quels) :

```python
def _write_stl_binary(elements: list, name: str) -> bytes:
    """STL binaire, DEUX PASSES : compter d'abord, packer ensuite, droit dans
    le buffer de sortie — l'ancienne version recopiait toute la géométrie en
    tuples (~160 Mo d'intermédiaires par relief au grid max, mesuré en 2a).
    En mm ; en-tête 80 octets sans nom d'outil (règle P8)."""
    total = sum(len(el["mesh"]["indices"]) // 3 for el in elements)
    out = bytearray(84 + 50 * total)
    entete = f"card3d {name}".encode("ascii", "replace")[:80]
    out[0:len(entete)] = entete
    struct.pack_into("<I", out, 80, total)
    off = 84
    for el in elements:
        pos, idx = el["mesh"]["positions"], el["mesh"]["indices"]
        dz = float(el.get("z_mm") or 0.0)
        for t in range(0, len(idx), 3):
            a, b, c = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
            ax, ay, az = pos[a], pos[a + 1], pos[a + 2] + dz
            bx, by, bz = pos[b], pos[b + 1], pos[b + 2] + dz
            cx, cy, cz = pos[c], pos[c + 1], pos[c + 2] + dz
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            struct.pack_into("<12fH", out, off,
                             nx / ln, ny / ln, nz / ln,
                             ax, ay, az, bx, by, bz, cx, cy, cz, 0)
            off += 50
    return bytes(out)
```

**ATTENTION à l'équivalence** : relire le corps ACTUEL de `_write_stl_binary` dans
forge3d.py avant de le remplacer — si l'actuel applique déjà `z_mm` ou un autre détail
(ordre des éléments, en-tête exact), le reproduire à l'identique ; seule la
STRATÉGIE MÉMOIRE change. En cas d'écart constaté avec ce squelette, l'actuel a raison.

- [x] **Step 3 : `forge3d.py` importe/réexporte, suite verte**

En tête de forge3d.py, à la place des définitions déplacées :
```python
from .forge3d_scene import (quad_mesh, relief_mesh, mesh_measures,
                            write_scene_glb, _write_stl_binary)
```
Run : run-tests -Filter cards_forge3d → **TOUTE la suite 2a reste verte** (c'est le
vrai verrou de la découpe) + le nouveau test PASS.

- [x] **Step 4 : lint**

`python scripts\qa\lint_cardforge.py --module forge3d` → 0 violation attendu. SI le
lint signale `forge3d_scene.py` (fichier py inattendu / règle routeur), l'autoriser
EXPLICITEMENT (liste de fichiers du module forge3d, commentaire « couture legs 6,
revue 2a ») — modification nommée, jamais un contournement silencieux.

- [x] **Step 5 : Commit**

```bash
git add backend/app/services/cards/forge3d_scene.py backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py scripts/qa/lint_cardforge.py
git commit -m "refactor(cardforge): decoupe forge3d_scene (geometrie pure) + writer STL deux-passes - legs 6 de la 2a"
```

---

### Task 2: La grille Meshy 6/7 des DEUX côtés du miroir + helpers serveur (gamme Assets)

> **LIVRÉE (f84fa0a + correctifs de revue 572a1e8/e9f4a78/7ba3449) — amendements
> actés en revue, qui prévalent sur les extraits ci-dessous :** (1) la restauration
> de fin de bloc test est `settings.MESHY_MOCK = True` (PAS False — le main() du
> fichier suppose le mock actif) + `MESHY_MOCK_SPEED = 0.02` restauré ; boucle de
> poll BORNÉE (500 itérations) via asyncio.run (l'API get_event_loop est dépréciée
> sur le runtime 3.13) ; (2) le miroir CREDITS est CONFRONTÉ PAR VALEURS via node
> (96 combinaisons, 0 divergence ; repli substring honnête si node absent) — le
> substring seul ne confrontait rien ; (3) les helpers tiennent le contrat
> `meshy:` sur TOUTE panne (httpx.HTTPError enveloppé, `_meshy_detail` message→
> error→HTTP code+corps tronqué, garde clé absente nommée) et get_task porte
> allowlist + validation d'id AVANT le dispatch mock ; (4) `ultra` est câblé de
> bout en bout sur les TROIS méthodes client (textTo3dPreview, imageTo3d,
> multiImageTo3d → ultra_mode) ET les deux branches de MeshyPipeline.start —
> partout où le devis compte l'ultra, la requête l'envoie. Étapes cochées.

**Files:**
- Modify: `backend/app/services/meshy_service.py`
- Modify: `frontend/meshy/meshy.client.js`
- Modify: `frontend/studio3d/studio3d.js`
- Test: `backend/tests/test_meshy_service.py`

Grille OFFICIELLE (docs.meshy.ai/en/api/pricing, relevée le 20/08/2026) : image-to-3d
**meshy-6 ET meshy-7 = 20 cr sans texture · 30 cr texturé 2k/4k · 35 cr en 8k** ;
**ultra (meshy-7 et `latest` SEULEMENT, car `latest` EST meshy-7 depuis le
10/08/2026) = +5 cr** ; text-to-3d preview meshy-7 = 20 (+5 ultra) ; meshy-5 reste
5/15. `ai_model` accepté par l'API : meshy-5/meshy-6/meshy-7/latest (vérifié sur
docs.meshy.ai/en/api/image-to-3d).

- [x] **Step 1 : asserts en RED dans test_meshy_service.py** (fichier script : ajouter
sous les asserts de grille existants, style du fichier)

```python
assert MS.credits_image_to_3d("meshy-7", "standard", True, "2k") == 30
assert MS.credits_image_to_3d("meshy-7", "standard", True, "8k") == 35
assert MS.credits_image_to_3d("meshy-7", "standard", False) == 20
assert MS.credits_image_to_3d("meshy-7", "standard", True, "2k", ultra=True) == 35
assert MS.credits_image_to_3d("meshy-7", "standard", True, "8k", ultra=True) == 40
assert MS.credits_image_to_3d("meshy-6", "standard", True, "2k", ultra=True) == 30  # ultra ignoré hors v7/latest
assert MS.credits_image_to_3d("latest", "standard", True, "2k", ultra=True) == 35
assert MS.credits_text_to_3d_preview("meshy-7") == 20
assert MS.credits_text_to_3d_preview("meshy-7", ultra=True) == 25
ok("meshy-7 : grille HD (20/30/35) + ultra +5 (v7/latest seulement)")

# le miroir JS porte les mêmes valeurs (bloc CREDITS)
_js = (Path(__file__).resolve().parents[1].parent / "frontend" / "meshy"
       / "meshy.client.js").read_text(encoding="utf-8")
_bloc = _js.split("export const CREDITS")[1].split("};")[0]
assert "meshy-7" in _bloc and "ultra" in _bloc
ok("miroir CREDITS de meshy.client.js : meshy-7 + ultra présents")

# helpers serveur mock-aware (P9 s'en sert ; ici on prouve le contrat)
import asyncio as _aio
settings.MESHY_MOCK = True
settings.MESHY_MOCK_SPEED = 0.01
MS._mock = None                      # repartir d'un simulateur neuf, vitesse test
_tid = _aio.get_event_loop().run_until_complete(
    MS.create_task("openapi/v1/image-to-3d",
                   {"image_url": "data:image/png;base64,AAAA",
                    "ai_model": "meshy-7", "should_texture": True,
                    "ultra_mode": True}))
assert _tid.startswith("mock-")
while True:
    _t = _aio.get_event_loop().run_until_complete(
        MS.get_task("openapi/v1/image-to-3d", _tid))
    if _t["status"] in MS.TERMINAL:
        break
assert _t["status"] == "SUCCEEDED" and _t["consumed_credits"] == 35
assert _t["model_urls"]["glb"].startswith(MS.MOCK_FILE_PREFIX)
ok("create_task/get_task serveur : mock-aware, crédits ultra comptés")
settings.MESHY_MOCK = False
MS._mock = None
```

(Adapter le chemin `_js` au calcul de racine DÉJÀ utilisé en tête de ce fichier de
test s'il en a un ; sinon garder celui-ci. Si le fichier utilise déjà une boucle
asyncio/un helper `run`, s'y conformer.)

Run : `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter meshy` — FAIL attendu (signatures sans `ultra`, helpers absents).

- [x] **Step 2 : meshy_service.py — la grille**

```python
def _is_hd_model(ai_model: str, model_type: str) -> bool:
    # meshy-7 rejoint la grille HD le 10/08/2026 ; `latest` EST meshy-7.
    return ai_model in ("meshy-6", "meshy-7", "latest") or model_type == "lowpoly"


def _ultra_extra(ai_model: str, ultra: bool) -> int:
    """docs.meshy.ai/en/api/pricing : Ultra n'existe QUE sur meshy-7/latest — +5 cr."""
    return 5 if ultra and ai_model in ("meshy-7", "latest") else 0


def credits_text_to_3d_preview(ai_model: str = "meshy-6",
                               model_type: str = "standard",
                               ultra: bool = False) -> int:
    return (20 if _is_hd_model(ai_model, model_type) else 5) \
        + _ultra_extra(ai_model, ultra)


def credits_image_to_3d(ai_model: str = "meshy-6", model_type: str = "standard",
                        should_texture: bool = True,
                        texture_resolution: str = "2k",
                        ultra: bool = False) -> int:
    smart = model_type == "smart-topology"
    if not should_texture:
        base = 5 if smart else (20 if _is_hd_model(ai_model, model_type) else 5)
    elif texture_resolution == "8k":
        base = 20 if smart else 35
    else:
        base = 15 if smart else (30 if _is_hd_model(ai_model, model_type) else 15)
    return base + _ultra_extra(ai_model, ultra)
```

`estimate_pipeline` : lire `ultra = bool(_cfg(cfg, "ultra", "ultra", False))` et le
passer à `credits_text_to_3d_preview(ai_model, model_type, ultra)` et à
`credits_image_to_3d(ai_model, model_type, with_texture, res, ultra)`.
`MeshyMock._credits` : passer `payload.get("ultra_mode")` en `ultra=` aux deux mêmes
appels (le simulateur facture comme la vraie API).

- [x] **Step 3 : meshy_service.py — les helpers serveur**

Sous `proxy_request` (même section « proxy vers l'API réelle ») :

```python
async def create_task(base: str, payload: dict) -> str:
    """Crée une tâche Meshy CÔTÉ SERVEUR (P9 Forge 3D) — mock-aware, même
    surface allowlistée que le proxy. Retourne l'id ; RuntimeError au message
    LITTÉRAL préfixé `meshy:` sinon (doctrine erreurs du lab)."""
    if base not in ALLOWED_BASES:
        raise RuntimeError(f"meshy: chemin non autorisé {base!r}")
    if mock_enabled():
        code, res = get_mock().create(base, payload)
    else:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as c:
            r = await c.post(f"{MESHY_API}/{base}", headers=_headers(), json=payload)
            code = r.status_code
            try:
                res = r.json()
            except ValueError:
                res = {"message": r.text[:400]}
    if code not in (200, 202) or not isinstance(res, dict) or not res.get("result"):
        raise RuntimeError(f"meshy: {res.get('message') if isinstance(res, dict) else res}")
    return str(res["result"])


async def get_task(base: str, task_id: str) -> dict:
    """État d'une tâche Meshy côté serveur — mock-aware. RuntimeError littérale
    sur code HTTP hors 200 (la tâche de fond de P9 la journalise telle quelle)."""
    if mock_enabled():
        code, res = get_mock().get(task_id)
    else:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as c:
            r = await c.get(f"{MESHY_API}/{base}/{task_id}", headers=_headers())
            code = r.status_code
            try:
                res = r.json()
            except ValueError:
                res = {"message": r.text[:400]}
    if code != 200 or not isinstance(res, dict):
        raise RuntimeError(f"meshy: {res.get('message') if isinstance(res, dict) else res}")
    return res
```

- [x] **Step 4 : meshy.client.js — le miroir**

Dans le bloc `export const CREDITS` (mêmes valeurs, mêmes conditions ; le test de
Step 1 vérifie la présence, la discipline du port exact vérifie les chiffres) :

```js
export const CREDITS = {
  _hd: (m, t) => m === "meshy-6" || m === "meshy-7" || m === "latest" || t === "lowpoly",
  _ultra: (m, u) => (u && (m === "meshy-7" || m === "latest") ? 5 : 0),
  textTo3dPreview: ({ aiModel = "meshy-6", modelType = "standard", ultra = false } = {}) =>
    (CREDITS._hd(aiModel, modelType) ? 20 : 5) + CREDITS._ultra(aiModel, ultra),
  ...
  imageTo3d: ({ aiModel = "meshy-6", modelType = "standard", shouldTexture = true, textureResolution = "2k", ultra = false } = {}) => {
    const smart = modelType === "smart-topology";
    const base = !shouldTexture ? (smart ? 5 : (CREDITS._hd(aiModel, modelType) ? 20 : 5))
      : textureResolution === "8k" ? (smart ? 20 : 35)
      : (smart ? 15 : (CREDITS._hd(aiModel, modelType) ? 30 : 15));
    return base + CREDITS._ultra(aiModel, ultra);
  },
  ...
```
(Adapter les `...` aux entrées existantes du bloc sans les toucher ; `estimatePipeline`
lit `ultra` de la config et le passe aux deux fonctions ; la méthode `imageTo3d` du
client API ajoute `ultra_mode` au corps quand il est vrai — suivre le style de
construction de corps déjà dans le fichier.)

- [x] **Step 5 : studio3d.js — l'option meshy-7 (cohérence gamme Assets)**

Trois retouches, style du fichier :
- ligne du catalogue (~53) : `meta: "meshy-6 · api"` → `meta: "meshy-6/7 · api"` ;
- le `<select id="f-model">` (~588) gagne `meshy-7` EN TÊTE :
  `<option${c.aiModel === "meshy-7" ? " selected" : ""}>meshy-7</option>` (défaut du
  Studio INCHANGÉ : meshy-6) ;
- la note (~593) : préfixer par « meshy-7 : 30 cr texturé (grille meshy-6), alignement
  image→3D supérieur, ultra +5 cr (exposé dans la Forge 3D des cartes). ».

- [x] **Step 6 : GREEN + commit**

Run : run-tests -Filter meshy → PASS (toutes les sections du fichier script).
```bash
git add backend/app/services/meshy_service.py frontend/meshy/meshy.client.js frontend/studio3d/studio3d.js backend/tests/test_meshy_service.py
git commit -m "feat(assets): grille Meshy 7 + ultra des deux cotes du miroir, helpers serveur mock-aware, option studio3d"
```

---

### Task 3: Le vocabulaire 2b (miroir), `clean_graph`, `pricing`, `/info`

> **LIVRÉE (edf355a + correctifs de revue) — amendements actés en revue, qui
> PRÉVALENT sur les extraits ci-dessous :** (1) `clean_graph`/mesh3d : un moteur
> INCONNU est réparé vers `MESH3D_DEFAULT_ENGINE`, mais **`ultra` ne survit
> JAMAIS à cette réparation** (`connu and engine == "meshy-7"`) — conservateur
> sur l'axe qui coûte de l'argent, l'utilisateur n'a pas consenti à l'ultra d'un
> moteur qu'il n'a pas nommé ; (2) les arêtes sont filtrées contre les nœuds
> SURVIVANTS (`vivants`), plus d'arêtes pendantes quand un nœud est jeté (le
> chemin 2a layer en profite aussi) ; (3) `/info` fait son IO en
> `asyncio.to_thread` (584 ms de blocage mesurés à 200 matières sinon) et NE
> FAIT JAMAIS 500 : `_engine_table`/matières dégradent en `[]` + champ
> `degraded` au message littéral ; (4) `_engine_table` tire l'ultra de
> `MS._ultra_extra` (grille partagée, jamais recopiée) et les littéraux du prix
> deviennent `MESH3D_TEXTURE_RES = "2k"` / `MESH3D_SHOULD_TEXTURE = True`,
> constantes PARTAGÉES avec le payload du job de la Task 4 (une seule vérité) ;
> (5) tests épinglés : has_meshy/has_fal par égalité, default_engine, une
> matière réelle listée, les 4 bornes en littéral, verrou de roster
> `MESH3D_ENGINES(fal) ⊆ asset3d_service.ENGINES`.

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Modify: `frontend/cardforge/js/mod-forge3d.js` (bloc miroir seul ici)
- Modify: `backend/app/services/pricing.py`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : tests en RED**

```python
def test_le_vocabulaire_2b_est_identique_des_deux_cotes():
    """Le miroir CF-FORGE3D-NODES s'étend : mesh3d, material, transform."""
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-NODES-BEGIN")[1].split("CF-FORGE3D-NODES-END")[0]
    js_rows = re.findall(r'\{ kind: "([a-z0-9]+)", params: \[([^\]]*)\] \}', bloc)
    js_table = [{"kind": k, "params": [p.strip().strip('"') for p in ps.split(",") if p.strip()]}
                for k, ps in js_rows]
    assert js_table == F9.NODE_KINDS, (js_table, F9.NODE_KINDS)
    assert [r["kind"] for r in F9.NODE_KINDS] == [
        "layer", "plane", "relief", "mesh3d", "material", "transform",
        "assemble", "artifact"]


def test_clean_graph_borne_les_nouveaux_noeuds():
    from app.services.cards import forge3d as F9
    g = {"nodes": [
        {"id": "s", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m", "kind": "mesh3d", "engine": "meshy-7",
         "texture_prompt": "  or ancien, gravure  ", "ultra": 1},
        {"id": "m2", "kind": "mesh3d", "engine": "warp-drive", "ultra": True},
        {"id": "mat", "kind": "material", "mat": "zzz-pas-un-mid",
         "finish": "argent", "aniso": "oui", "tile_mm": 9999},
        {"id": "tr", "kind": "transform", "x_mm": -500, "rot_deg": 720,
         "scale": 99, "z_mm": "abc"},
        {"id": "a", "kind": "assemble"}], "edges": []}
    out = F9.clean_graph(g)
    n = {x["id"]: x for x in out["nodes"]}
    assert n["m"]["engine"] == "meshy-7" and n["m"]["ultra"] is True
    assert n["m"]["texture_prompt"] == "or ancien, gravure"
    # moteur inconnu -> défaut meshy-7 ; ultra HORS meshy-7 -> False
    assert n["m2"]["engine"] == "meshy-7"
    assert F9.clean_graph({"nodes": [{"id": "x", "kind": "mesh3d",
        "engine": "tripo", "ultra": True}], "edges": []})["nodes"][0]["ultra"] is False
    # matière : mid invalide -> None, mais la FINITION la garde en vie
    assert n["mat"]["mat"] is None and n["mat"]["finish"] == "argent"
    assert n["mat"]["aniso"] is True
    assert n["mat"]["tile_mm"] == F9.MATERIAL_TILE_MM[1]
    # matière sans matière NI finition -> jetée
    vide = F9.clean_graph({"nodes": [{"kind": "material", "mat": "!!",
                                      "finish": "aucune"}], "edges": []})
    assert vide["nodes"] == []
    # transform : bornes
    assert n["tr"]["x_mm"] == F9.TRANSFORM_XY_MM[0]
    assert n["tr"]["rot_deg"] == F9.TRANSFORM_ROT_DEG[1]
    assert n["tr"]["scale"] == F9.TRANSFORM_SCALE[1]
    assert n["tr"]["z_mm"] == 0.0


def test_info_publie_moteurs_prix_matieres_et_bornes():
    """7 moteurs, prix fal en $ depuis pricing, crédits Meshy depuis la grille
    partagée (+ conversion $ directionnelle meshy_credit_usd), matières de la
    boutique, bornes matière/transform — l'écran ne recopie RIEN."""
    from app.services import pricing, meshy_service as MS
    did = _deck("Info 2b")
    info = _api("GET", f"/api/cards/{did}/forge3d/info").json()
    eng = {e["id"]: e for e in info["mesh3d"]["engines"]}
    assert list(eng) == ["tripo", "hunyuan", "trellis", "rodin", "triposr",
                         "meshy-6", "meshy-7"]
    p = pricing.load()
    attendu = pricing.estimate({"kind": "asset3d", "engine": "tripo"}, p)["total_usd"]
    assert eng["tripo"]["provider"] == "fal" and eng["tripo"]["price_usd"] == attendu
    assert eng["meshy-7"]["provider"] == "meshy"
    assert eng["meshy-7"]["credits"] == MS.credits_image_to_3d("meshy-7", "standard", True, "2k") == 30
    assert eng["meshy-7"]["ultra_extra_credits"] == 5
    assert eng["meshy-6"]["ultra_extra_credits"] == 0
    assert eng["meshy-7"]["price_usd"] == round(30 * float(p["meshy_credit_usd"]), 4)
    assert isinstance(info["mesh3d"]["has_meshy"], bool)
    assert isinstance(info["mesh3d"]["has_fal"], bool)
    assert isinstance(info["materials"], list)     # [] accepté : boutique vide
    assert info["material_limits"]["finishes"] == ["aucune", "argent", "dorure"]
    assert info["transform_limits"]["scale"] == [0.1, 4.0]
```

Run : run-tests -Filter cards_forge3d → FAIL.

- [ ] **Step 2 : pricing.py**

Dans `DEFAULTS`, sous `rembg_api_usd` :
```python
    "meshy_credit_usd": 0.02,         # valeur $ directionnelle d'un crédit Meshy
                                      # (~plan Pro 1000 cr/mois) ; éditable comme
                                      # le reste — Meshy facture en crédits, la
                                      # vérité comptable est consumed_credits
```

- [ ] **Step 3 : forge3d.py — vocabulaire + bornes + clean_graph**

Bloc miroir (les DEUX côtés, mêmes rangs, commentaires par genre comme l'existant) :
```python
NODE_KINDS = [
    {"kind": "layer", "params": ["role", "side"]},
    {"kind": "plane", "params": ["depth_mm"]},
    {"kind": "relief", "params": ["depth_mm", "base_mm", "grid"]},
    {"kind": "mesh3d", "params": ["engine", "texture_prompt", "ultra"]},
    {"kind": "material", "params": ["mat", "tile_mm", "finish", "aniso"]},
    {"kind": "transform", "params": ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"]},
    {"kind": "assemble", "params": []},
    {"kind": "artifact", "params": ["name"]},
]
```
(Miroir JS identique entre `CF-FORGE3D-NODES-BEGIN/END` de mod-forge3d.js — vérifier
les octets du .js après édition, piège Windows connu.)

Bornes et tables (sous les bornes 2a ; `MESH3D_ENGINES` N'EST PAS un bloc miroir —
il est SERVI par /info, l'écran ne le recopie jamais) :
```python
# ── mesh3d (2b) : les 7 moteurs — 5 fal (asset3d_service) + Meshy direct ────
MESH3D_ENGINES = [
    {"id": "tripo",   "provider": "fal",   "label": "Tripo v2.5"},
    {"id": "hunyuan", "provider": "fal",   "label": "Hunyuan3D v2"},
    {"id": "trellis", "provider": "fal",   "label": "TRELLIS"},
    {"id": "rodin",   "provider": "fal",   "label": "Rodin"},
    {"id": "triposr", "provider": "fal",   "label": "TripoSR"},
    {"id": "meshy-6", "provider": "meshy", "label": "Meshy 6"},
    {"id": "meshy-7", "provider": "meshy", "label": "Meshy 7"},
]
MESH3D_DEFAULT_ENGINE = "meshy-7"     # la demande d'origine : « pour les textures »
MESH3D_PROMPT_MAX = 600
MESH3D_UPLOAD_PX = 2048               # côté long envoyé aux moteurs — un moteur
                                      # texture en 2k, le 300 DPI n'y gagne rien
MESH3D_POLL_S = 4.0                   # période de poll Meshy (0.05 en mock)
MESH3D_TIMEOUT_S = 1800.0             # 30 min — après quoi le job échoue NOMMÉ
MESH3D_CLOSED_TRI_MAX = 1_500_000     # au-delà : closed=None (« non mesuré »),
                                      # le gate STL refuse MOTIVÉ (borne mémoire)
MAX_EXT_GLB_BYTES = 64 * 1024 * 1024  # même chiffre que MAX_LAYER_BYTES

MATERIAL_TILE_MM = (10.0, 200.0)
MATERIAL_FINISHES = ("aucune", "argent", "dorure")
TRANSFORM_XY_MM = (-100.0, 100.0)
TRANSFORM_Z_MM = (0.0, 10.0)
TRANSFORM_ROT_DEG = (-180.0, 180.0)
TRANSFORM_SCALE = (0.1, 4.0)
```

Branches de `clean_graph` (dans la boucle existante, style des branches 2a) :
```python
        elif n["kind"] == "mesh3d":
            eng = str(n.get("engine") or "")
            node["engine"] = eng if eng in {e["id"] for e in MESH3D_ENGINES} \
                else MESH3D_DEFAULT_ENGINE
            node["texture_prompt"] = str(n.get("texture_prompt") or "").strip()[:MESH3D_PROMPT_MAX]
            node["ultra"] = bool(n.get("ultra")) and node["engine"] == "meshy-7"
        elif n["kind"] == "material":
            from app.services import material_store as MSTORE
            mid = str(n.get("mat") or "")
            node["mat"] = mid if MSTORE.is_valid_mid(mid) else None
            node["tile_mm"] = _num(n.get("tile_mm"), 63.0, *MATERIAL_TILE_MM)
            node["finish"] = n.get("finish") if n.get("finish") in MATERIAL_FINISHES else "aucune"
            node["aniso"] = bool(n.get("aniso"))
            if node["mat"] is None and node["finish"] == "aucune":
                continue          # une matière sans matière ni finition n'est rien
        elif n["kind"] == "transform":
            node["x_mm"] = _num(n.get("x_mm"), 0.0, *TRANSFORM_XY_MM)
            node["y_mm"] = _num(n.get("y_mm"), 0.0, *TRANSFORM_XY_MM)
            node["z_mm"] = _num(n.get("z_mm"), 0.0, *TRANSFORM_Z_MM)
            node["rot_deg"] = _num(n.get("rot_deg"), 0.0, *TRANSFORM_ROT_DEG)
            node["scale"] = _num(n.get("scale"), 1.0, *TRANSFORM_SCALE)
```
(`import material_store` en tête de fichier plutôt qu'en ligne si le style du fichier
le permet — service partagé, spec §3.5.)

- [ ] **Step 4 : `/info` enrichi**

```python
def _engine_table() -> list[dict]:
    """Prix AVANT, jamais recopiés : fal en $ (pricing.estimate), Meshy en
    crédits (grille partagée meshy_service) + conversion $ directionnelle."""
    from app.services import pricing
    from app.services import meshy_service as MS
    p = pricing.load()
    rows = []
    for e in MESH3D_ENGINES:
        row = dict(e)
        if e["provider"] == "fal":
            row["price_usd"] = pricing.estimate(
                {"kind": "asset3d", "engine": e["id"]}, p)["total_usd"]
        else:
            cr = MS.credits_image_to_3d(e["id"], "standard", True, "2k")
            row["credits"] = cr
            row["ultra_extra_credits"] = 5 if e["id"] == "meshy-7" else 0
            row["price_usd"] = round(cr * float(p.get("meshy_credit_usd", 0.02)), 4)
        rows.append(row)
    return rows
```
La réponse de `get_info` gagne :
```python
            "mesh3d": {
                "engines": _engine_table(),
                "default_engine": MESH3D_DEFAULT_ENGINE,
                "has_fal": bool(settings.FAL_KEY),
                "has_meshy": settings.has_meshy or bool(settings.MESHY_MOCK),
                "meshy_mock": bool(settings.MESHY_MOCK),
                "prompt_max": MESH3D_PROMPT_MAX,
            },
            "materials": [{"id": m["id"], "name": m["name"]}
                          for m in material_store.list_materials()],
            "material_limits": {"tile_mm": list(MATERIAL_TILE_MM),
                                "finishes": list(MATERIAL_FINISHES)},
            "transform_limits": {"xy_mm": list(TRANSFORM_XY_MM),
                                 "z_mm": list(TRANSFORM_Z_MM),
                                 "rot_deg": list(TRANSFORM_ROT_DEG),
                                 "scale": list(TRANSFORM_SCALE)},
```
(`settings` est déjà importé ou s'importe de `app.config` selon l'existant du fichier ;
`list_materials()` ne lève pas sur boutique vide — elle rend `[]`.)

- [ ] **Step 5 : mettre à jour le test de parité 2a**

Le test existant `test_le_vocabulaire_du_graphe_est_identique_des_deux_cotes` affirme
l'ordre 2a (`["layer", "plane", "relief", "assemble", "artifact"]`) : le NOUVEAU test
le remplace — supprimer l'ancien assert d'ordre (garder le reste du test s'il vérifie
autre chose, sinon retirer l'ancien test au profit du nouveau, une seule source).

- [ ] **Step 6 : GREEN + commit**

Run : run-tests -Filter cards_forge3d → PASS ; lint --module forge3d → 0.
```bash
git add backend/app/services/cards/forge3d.py frontend/cardforge/js/mod-forge3d.js backend/app/services/pricing.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): vocabulaire 2b (mesh3d/material/transform) en miroir, clean_graph borne, /info sert moteurs+prix+matieres"
```

---

### Task 4: Le job `mesh3d` — routes, runner fal, runner Meshy, `closed` mesuré UNE fois

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Modify: `backend/app/services/cards/forge3d_scene.py` (extraction GLB→mesh)
- Test: `backend/tests/test_cards_forge3d.py`

Modèle : job de fond par nœud (patron `/assets/3d` : pré-enregistrer, travailler en
tâche de fond, poller), MAIS l'état durable est `nodes/{nid}/job.json` (deck-local,
legs 2) — pas un JobRecord global. Un registre mémoire `{(did, nid): task}` détecte
les jobs orphelins après redémarrage. Relancer un nœud RÉINITIALISE son dossier
(l'aperçu périmé ne survit pas — legs 4 appliqué aux nœuds).

- [ ] **Step 1 : tests en RED**

```python
def _graphe_mesh3d(engine="meshy-7", ultra=False):
    return {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": engine,
         "texture_prompt": "pierre gravée", "ultra": ultra},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}


def _exporter_couches(did):
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "card": "0", "paper": "#ffffff",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text


def _attendre_job(did, nid, timeout=30.0):
    import time as _t
    fin = _t.monotonic() + timeout
    while _t.monotonic() < fin:
        r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/{nid}")
        if r.status_code == 200 and r.json().get("status") in ("served", "failed"):
            return r.json()
        _t.sleep(0.05)
    raise AssertionError("job mesh3d jamais terminal")


def test_le_job_meshy_traverse_le_mock_et_mesure_closed_une_fois():
    """Flux Meshy COMPLET sur le simulateur (zéro crédit) : création, poll,
    rapatriement des binaires DANS le nœud, crédits consommés (ultra compté),
    closed mesuré à l'import et caché — le triangle du mock est OUVERT."""
    from app.config import settings as cfg
    from app.services import meshy_service as MS
    cfg.MESHY_MOCK = True
    cfg.MESHY_MOCK_SPEED = 0.01
    MS._mock = None
    try:
        did = _deck("Job meshy")
        _exporter_couches(did)
        g = _graphe_mesh3d("meshy-7", ultra=True)
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        lance = r.json()
        assert lance["job"]["status"] in ("queued", "running")
        assert lance["job"]["price"] == {"credits": 35, "usd": round(35 * 0.02, 4)}
        job = _attendre_job(did, "m1")
        assert job["status"] == "served", job
        assert job["engine"] == "meshy-7" and job["consumed_credits"] == 35
        assert job["closed"] is False            # le tiny_glb du mock est un triangle
        ndir = Path(_api("GET", f"/api/cards/{did}/forge3d/info").headers.get("x-noop", ".")) # (voir note)
        base = OUTPUTS / "decks" / did / "forge3d" / "nodes" / "m1"
        assert (base / "model.glb").is_file()
        assert (base / "preview.png").is_file()
        assert (base / "job.json").is_file()
        # relancer = dossier réinitialisé (aperçu périmé jamais servi — legs 4)
        r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r2.status_code == 200
        _attendre_job(did, "m1")
    finally:
        cfg.MESHY_MOCK = False
        MS._mock = None


def test_le_job_fal_passe_par_les_coutures_et_le_glb_ferme_est_su():
    """Moteur fal monkeypatché de bout en bout : upload -> run -> download.
    Le « GLB téléchargé » est un relief FERMÉ écrit par notre writer ->
    closed True mesuré une fois, prix $ = pricing."""
    from app.services import asset3d_service as A3D
    from app.services import pricing
    from app.services.cards import forge3d_scene as SC
    from PIL import Image
    relief = SC.relief_mesh(Image.new("L", (16, 16), 255), 63.0, 88.0, 1.0, 0.3, 8)
    relief["closed"] = True
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(png, "PNG")
    glb_connu = SC.write_scene_glb(
        [{"name": "x", "mesh": relief, "png": png.getvalue(), "alpha": False,
          "z_mm": 0.0}], name="x", extras={"unit": "metre"})

    async def faux_upload(path):
        assert Path(path).is_file()
        return "https://fal.test/src.png"

    async def faux_run(engine, args):
        assert engine == "tripo" and args["image_url"] == "https://fal.test/src.png"
        return {"mesh_url": "https://fal.test/model.glb",
                "format_urls": {}, "texture_urls": [],
                "preview_url": None}

    def faux_download(url, dest, timeout=120):
        dest.write_bytes(glb_connu)
        return True

    vrai = (A3D._upload, A3D._run_engine, A3D._download)
    A3D._upload, A3D._run_engine, A3D._download = faux_upload, faux_run, faux_download
    try:
        did = _deck("Job fal")
        _exporter_couches(did)
        g = _graphe_mesh3d("tripo")
        r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                 json={"graph": g, "card": 0})
        assert r.status_code == 200, r.text
        attendu = pricing.estimate({"kind": "asset3d", "engine": "tripo"})["total_usd"]
        assert r.json()["job"]["price"] == {"usd": attendu}
        job = _attendre_job(did, "m1")
        assert job["status"] == "served" and job["closed"] is True
    finally:
        A3D._upload, A3D._run_engine, A3D._download = vrai


def test_les_refus_du_job_mesh3d_sont_nommes():
    from app.config import settings as cfg
    did = _deck("Refus mesh3d")
    g = _graphe_mesh3d("meshy-7")
    # sans couches livrées -> 409 motivé
    r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1", json={"graph": g, "card": 0})
    assert r.status_code == 409 and "couches" in r.json()["detail"]
    _exporter_couches(did)
    # nid absent du graphe -> 400 nommé
    r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/zzz", json={"graph": g, "card": 0})
    assert r2.status_code == 400
    # moteur meshy sans clé ni mock -> 503 qui dit QUOI configurer
    avant = (cfg.MESHY_API_KEY, cfg.MESHY_MOCK)
    cfg.MESHY_API_KEY, cfg.MESHY_MOCK = "", False
    try:
        r3 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r3.status_code == 503 and "MESHY_API_KEY" in r3.json()["detail"]
    finally:
        cfg.MESHY_API_KEY, cfg.MESHY_MOCK = avant
    # jamais lancé -> GET 404
    r4 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r4.status_code == 404


def test_un_job_running_orphelin_apres_redemarrage_est_avoue():
    """job.json dit `running` mais le registre mémoire ne le connaît pas
    (procès redémarré) : le GET le bascule en failed « interrompu »."""
    did = _deck("Orphelin")
    base = OUTPUTS / "decks" / did / "forge3d" / "nodes" / "m1"
    base.mkdir(parents=True, exist_ok=True)
    (base / "job.json").write_text(json.dumps(
        {"schema": "card-3d/mesh3d-job@1", "node": "m1", "engine": "meshy-7",
         "status": "running", "progress": 50}), encoding="utf-8")
    r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "interrompu" in r.json()["error"]
```

NOTE au rédacteur des tests : `OUTPUTS` = la racine outputs des tests (le fichier de
test a déjà sa manière d'atteindre `outputs/decks/{did}` pour relire les fichiers —
réutiliser EXACTEMENT le même mécanisme que les tests 2a de `build3d`, et supprimer la
ligne factice `ndir…x-noop` ci-dessus qui n'existe que pour rappeler cette adaptation).
Le test 409-concurrent n'est PAS écrit : le mock à vitesse 0.01 finit trop vite pour
le fenêtrer de façon fiable — la garde est couverte par relecture de code en revue.

Run : run-tests -Filter cards_forge3d → FAIL (routes absentes).

- [ ] **Step 2 : `forge3d_scene.py` — lire un GLB en mesh**

```python
def read_glb(data: bytes) -> tuple[dict, bytes]:
    """Document JSON + chunk BIN d'un GLB. ValueError NOMMÉE sinon (la route
    la transforme en refus motivé, jamais un 500)."""
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("pas un GLB (magie glTF absente)")
    doc_len = struct.unpack("<I", data[12:16])[0]
    if 20 + doc_len > len(data):
        raise ValueError("GLB tronqué (chunk JSON)")
    doc = json.loads(data[20:20 + doc_len].decode("utf-8").rstrip("\x00 "))
    off = 20 + doc_len
    binv = b""
    if off + 8 <= len(data):
        blen = struct.unpack("<I", data[off:off + 4])[0]
        binv = data[off + 8:off + 8 + blen]
    return doc, binv


def _accessor_floats(doc: dict, binv: bytes, idx: int) -> list[float]:
    acc = doc["accessors"][idx]
    bv = doc["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
    return list(struct.unpack_from("<" + "f" * (acc["count"] * n), binv, off))


def _accessor_indices(doc: dict, binv: bytes, idx: int) -> list[int]:
    acc = doc["accessors"][idx]
    bv = doc["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    fmt = {5121: "B", 5123: "H", 5125: "I"}[acc["componentType"]]
    return list(struct.unpack_from("<" + fmt * acc["count"], binv, off))


def glb_scene_mesh(data: bytes) -> dict:
    """Concatène POSITION+indices de TOUTES les primitives triangles d'un GLB
    en un mesh {positions, indices} pour mesh_measures/STL. Les transforms de
    nœuds INTERNES sont ignorés (les GLB des moteurs sont un maillage centré —
    limitation documentée, le bordereau relit les octets de toute façon).
    ValueError nommée si une primitive n'est pas indexée."""
    doc, binv = read_glb(data)
    positions, indices = [], []
    for mesh in doc.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            if prim.get("mode", 4) != 4:
                continue                      # seuls les TRIANGLES comptent
            if "indices" not in prim or "POSITION" not in prim.get("attributes", {}):
                raise ValueError("primitive sans indices/POSITION")
            base = len(positions) // 3
            positions += _accessor_floats(doc, binv, prim["attributes"]["POSITION"])
            indices += [base + i for i in _accessor_indices(doc, binv, prim["indices"])]
    if not indices:
        raise ValueError("aucune primitive triangle dans le GLB")
    return {"positions": positions, "indices": indices}
```

- [ ] **Step 3 : forge3d.py — les routes et les runners**

Registre + utilitaires (module-level) :
```python
_MESH3D_RUNNING: dict[tuple, "asyncio.Task"] = {}
_NID_RE = re.compile(r"^[A-Za-z0-9._-]{1,24}$")


def _node_dir(did: str, nid: str, create: bool = False) -> Path: ...
def _job_write(did: str, nid: str, job: dict) -> None:
    """Écriture ATOMIQUE (tmp + os.replace) — un poll ne lit jamais un JSON à moitié."""
def _job_read(did: str, nid: str) -> dict | None: ...
```

`POST /mesh3d/{nid}` — points imposés (corps sur les patrons du fichier, NOTE de
revue phase 1 applicable) :
- gardes deck 400/404 (patron get_info) ; `nid` au `_NID_RE` sinon 400 ;
  `clean_graph(body["graph"])` puis le nœud `nid` doit exister, kind `mesh3d`,
  sinon **400 nommé** (« nœud mesh3d {nid} absent du graphe ») ;
- source : l'edge `layer→nid` (from d'un nœud layer vers nid) ; la couche
  `_layer_filename(...)` doit exister sur disque, sinon **409 « exporte les couches
  d'abord »** (formulation 2a) ;
- clés : moteur fal sans `settings.FAL_KEY` → **400** « FAL_KEY not configured. Add it
  in Settings. » (formulation de routes.py) ; moteur meshy sans `settings.has_meshy`
  ni `MESHY_MOCK` → **503** au MESSAGE EXACT du proxy (« MESHY_API_KEY not
  configured — add it in Settings (or set MESHY_MOCK=1 for the local simulator) ») ;
- concurrence : `(did, nid)` déjà dans `_MESH3D_RUNNING` avec un task non-done →
  **409** « un job court déjà sur ce nœud » ;
- prix AVANT, écrit dans le job : fal → `{"usd": pricing.estimate({"kind": "asset3d",
  "engine": eng})["total_usd"]}` ; meshy → `cr = credits_image_to_3d(eng, "standard",
  True, "2k", ultra=node["ultra"])` puis `{"credits": cr, "usd": round(cr *
  meshy_credit_usd, 4)}` ;
- RESET du dossier nœud (`shutil.rmtree` + recreate — legs 4 : rien de périmé ne
  survit à une relance), puis `job.json` `queued` : `{"schema":
  "card-3d/mesh3d-job@1", "node", "engine", "status": "queued", "progress": 0,
  "step": "En file", "error": None, "price", "source": {"role", "side", "file",
  "sha256"}, "closed": None, "started": iso, "files": {}}` ;
- lancer via `background_tasks.add_task(_run_mesh3d, did, nid, node, source)` et
  ENREGISTRER le task réel depuis le runner (asyncio.current_task) dans
  `_MESH3D_RUNNING` ; retour `{"job": job}` (le job queued).

`_run_mesh3d(did, nid, node, source)` (async, TOUT le travail image en to_thread) :
1. downscale : ouvrir la couche (bytes du disque), `thumbnail((MESH3D_UPLOAD_PX,) * 2,
   LANCZOS)` en conservant l'alpha, écrire `upload_src.png` ; step « Préparation », 10 ;
2. **fal** : `url = await A3D._upload(chemin)` ; `args = A3D.build_engine_args(engine,
   [url], {"format": "glb", "textures": True})` ; step « Moteur {engine} », 40 ;
   `res = await A3D._run_engine(engine, args)` ; `mesh_url` absent → RuntimeError
   littérale (patron asset3d « aucun mesh dans la réponse fal ») ; download
   `model.glb` (+ `preview.png` si preview_url) via `asyncio.to_thread(A3D._download,…)` ;
3. **meshy** : payload `{"image_url": "data:image/png;base64," + b64, "ai_model":
   engine, "should_texture": True, "enable_pbr": True, "texture_resolution": "2k",
   "topology": "triangle", "target_polycount": 30000}` + `texture_prompt` si non vide
   + `ultra_mode: True` si `node["ultra"]` ; `tid = await MS.create_task(
   "openapi/v1/image-to-3d", payload)` ; boucle : `await MS.get_task(...)` toutes les
   `0.05 if MS.mock_enabled() else MESH3D_POLL_S` s, MAJ `progress`/`step` dans
   job.json, budget `MESH3D_TIMEOUT_S` sinon RuntimeError « meshy: délai dépassé
   (30 min) » ; `FAILED/CANCELED` → RuntimeError « meshy: {task_error.message
   littéral} » ; `SUCCEEDED` → télécharger `model_urls["glb"]` via `MS._fetch_url`
   (mock-aware) → `model.glb`, `thumbnail_url` → `preview.png`, chaque entrée de
   `texture_urls[i]` (dict kind→url) → `textures/{i}_{kind}.png` ; noter
   `consumed_credits` ;
4. `closed` UNE FOIS (legs 1) : `m = glb_scene_mesh(model.glb bytes)` ;
   si `len(m["indices"])//3 > MESH3D_CLOSED_TRI_MAX` → `closed = None` (+ note
   « fermeture non mesurée : maillage trop lourd ») sinon
   `closed = mesh_measures(m)["closed"]` — en to_thread ;
5. job final `served` : `progress: 100`, `finished`, `files` {glb, preview?,
   textures: […]}, `closed`, `consumed_credits?` ; sur exception : `failed` +
   `error` LITTÉRALE (str(e)) — préfixée fournisseur par construction (« fal.ai: … »
   vient de _run_engine, « meshy: … » des helpers) ; `finally` : retirer du registre.

`GET /mesh3d/{nid}` :
- gardes deck/nid ; `_job_read` → 404 « aucun job sur ce nœud » si absent ;
- si `status == "running"` ou `"queued"` MAIS `(did, nid)` absent du registre (ou
  task done) → réécrire `failed` avec `error` = « interrompu par un redémarrage du
  backend — relancer le nœud » et servir ça (l'aveu honnête, jamais un `running`
  fantôme) ;
- sinon servir le job.json tel quel.

- [ ] **Step 4 : GREEN + commit**

Run : run-tests -Filter cards_forge3d → PASS (les jobs mock tournent en ~1 s).
```bash
git add backend/app/services/cards/forge3d.py backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): job mesh3d par noeud - 5 moteurs fal + meshy-6/7 directs (mock teste), closed mesure une fois, prix avant"
```

---

### Task 5: Matières, transform et finitions holographiques dans le writer

**Files:**
- Modify: `backend/app/services/cards/forge3d_scene.py`
- Test: `backend/tests/test_cards_forge3d.py`

Sémantique (spec §5.2) : **baseColor = LA COUCHE**, la matière fournit
normal / metallicRoughness / ao / emissive. Les maps sont TUILÉES en PIL au pas
`tile_mm` sur une toile au ratio carte (déterministe, samplers CLAMP conservés —
aucun KHR_texture_transform à porter). Finitions §6.2bis-c : recettes argent/dorure,
`KHR_materials_iridescence` + `KHR_materials_clearcoat` (+ `KHR_materials_anisotropy`
si demandé, avec l'attribut TANGENT), le tout dans **`extensionsUsed` UNIQUEMENT**.

- [ ] **Step 1 : tests en RED**

```python
def test_la_matiere_habille_l_element_et_les_maps_sont_cuites():
    """normal/MR/ao câblées ; le pack MR suit la convention glTF (G=rugosité,
    B=métal — doctrine pbr_service) ; relu dans les OCTETS du GLB."""
    from PIL import Image
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (200, 30, 30, 255)).save(png, "PNG")
    maps = {
        "normal": Image.new("RGB", (16, 16), (128, 128, 255)),
        "roughness": Image.new("L", (16, 16), 64),
        "metallic": Image.new("L", (16, 16), 255),
        "ao": Image.new("L", (16, 16), 200),
    }
    el = {"name": "cadre", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": True, "z_mm": 0.0,
          "mat_maps": SC.material_pngs(maps)}
    glb = SC.write_scene_glb([el], name="x", extras={"unit": "metre"})
    doc, binv = _read_glb(glb)
    m = doc["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in pbr and "normalTexture" in m
    assert "occlusionTexture" in m
    # quand une map MR existe, les FACTEURS repassent à 1.0 (les niveaux sont
    # dans la map — convention pbr_service)
    assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0
    # relire le PNG MR du buffer : G=64 (rugosité), B=255 (métal)
    img_idx = doc["textures"][pbr["metallicRoughnessTexture"]["index"]]["source"]
    bv = doc["bufferViews"][doc["images"][img_idx]["bufferView"]]
    mr_png = binv[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
    px = Image.open(io.BytesIO(mr_png)).convert("RGB").getpixel((4, 4))
    assert px[1] == 64 and px[2] == 255
    # et le sampler reste CLAMP (le tuilage est CUIT, pas répété)
    for s in doc["samplers"]:
        assert s["wrapS"] == 33071 and s["wrapT"] == 33071


def test_tile_maps_tuile_au_pas_physique_et_reste_deterministe(tmp_path):
    """Une matière de la boutique, tuilée à tile_mm sur le ratio carte :
    même graine -> mêmes octets ; le motif se répète au pas attendu."""
    from PIL import Image
    from app.services import material_store as MSTORE
    from app.services.cards import forge3d_scene as SC
    mat = MSTORE.create_material(name="essai-2b")
    tuile = Image.new("RGB", (64, 64), (10, 10, 10))
    tuile.paste(Image.new("RGB", (8, 8), (250, 250, 250)), (0, 0))
    MSTORE.save_maps(mat["id"], {"basecolor": tuile,
                                 "roughness": Image.new("L", (64, 64), 100)})
    a = SC.tile_maps(mat["id"], ("roughness",), tile_mm=31.5,
                     w_mm=63.0, h_mm=88.0, out_px=256)
    b = SC.tile_maps(mat["id"], ("roughness",), tile_mm=31.5,
                     w_mm=63.0, h_mm=88.0, out_px=256)
    assert list(a["roughness"].tobytes()) == list(b["roughness"].tobytes())
    # 63 mm / 31.5 mm = 2 tuiles sur la largeur : les pixels (x) et (x + w/2)
    # portent la même valeur
    im = a["roughness"]
    w, h = im.size
    assert im.getpixel((3, 3)) == im.getpixel((3 + w // 2, 3))


def test_les_finitions_holo_suivent_la_recette_et_restent_optionnelles():
    """§6.2bis-c : extensions dans extensionsUsed UNIQUEMENT, facteurs exacts,
    épaisseur en secteurs radiaux relue dans le canal G, TANGENT présent quand
    l'anisotropie est demandée, clearcoat posé. Déterminisme prouvé."""
    from PIL import Image
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (220, 220, 220, 255)).save(png, "PNG")
    f1 = SC.holo_finish("argent", aniso=True, out_px=256)
    f2 = SC.holo_finish("argent", aniso=True, out_px=256)
    assert f1["iridescence"]["png"] == f2["iridescence"]["png"]   # même octets
    el = {"name": "sceau", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": False, "z_mm": 0.0, "finish": f1}
    glb = SC.write_scene_glb([el], name="x", extras={"unit": "metre"})
    doc, binv = _read_glb(glb)
    assert "extensionsRequired" not in doc
    assert set(doc["extensionsUsed"]) == {"KHR_materials_iridescence",
                                          "KHR_materials_clearcoat",
                                          "KHR_materials_anisotropy"}
    m = doc["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert pbr["baseColorFactor"] == [0.95, 0.95, 0.97, 1.0]
    assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 0.12
    iri = m["extensions"]["KHR_materials_iridescence"]
    assert iri["iridescenceFactor"] == 1.0 and iri["iridescenceIor"] == 1.8
    assert iri["iridescenceThicknessMinimum"] == 200.0
    assert iri["iridescenceThicknessMaximum"] == 900.0
    cc = m["extensions"]["KHR_materials_clearcoat"]
    assert cc["clearcoatFactor"] == 1.0 and cc["clearcoatRoughnessFactor"] == 0.06
    ani = m["extensions"]["KHR_materials_anisotropy"]
    assert ani["anisotropyStrength"] == 0.85 and "anisotropyTexture" in ani
    # TANGENT écrit (VEC4, un par sommet)
    prim = doc["meshes"][0]["primitives"][0]
    assert "TANGENT" in prim["attributes"]
    acc = doc["accessors"][prim["attributes"]["TANGENT"]]
    assert acc["type"] == "VEC4" and acc["count"] == 4
    # l'épaisseur varie AUTOUR du centre : 4 angles -> >= 3 valeurs G distinctes
    img_idx = doc["textures"][iri["iridescenceThicknessTexture"]["index"]]["source"]
    bv = doc["bufferViews"][doc["images"][img_idx]["bufferView"]]
    tex = Image.open(io.BytesIO(binv[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]))
    cx = cy = tex.size[0] // 2
    r = tex.size[0] // 3
    gs = {tex.getpixel((cx + r, cy))[1], tex.getpixel((cx - r, cy))[1],
          tex.getpixel((cx, cy + r))[1], tex.getpixel((cx + int(r * 0.7), cy + int(r * 0.7)))[1]}
    assert len(gs) >= 3, gs
    # la dorure a SA recette
    fd = SC.holo_finish("dorure", aniso=False, out_px=128)
    assert fd["pbr"]["baseColorFactor"] == [1.0, 0.84, 0.55, 1.0]
    assert fd["iridescence"]["ior"] == 1.6
    assert fd["iridescence"]["thickness"] == [200.0, 600.0]
    assert fd.get("anisotropy") is None
    # SANS finition ni matière : AUCUNE extension n'apparaît (dégradation
    # propre : un GLB 2a reste un GLB 2a)
    el2 = {"name": "nu", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
           "alpha": True, "z_mm": 0.0}
    doc2, _ = _read_glb(SC.write_scene_glb([el2], name="x", extras={}))
    assert "extensionsUsed" not in doc2 and "extensions" not in doc2["materials"][0]


def test_le_transform_porte_le_trs_du_noeud():
    from app.services.cards import forge3d_scene as SC
    from PIL import Image
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(png, "PNG")
    el = {"name": "e", "mesh": SC.quad_mesh(63.0, 88.0), "png": png.getvalue(),
          "alpha": True, "z_mm": 0.0,
          "trs": {"translate": [5.0, -3.0, 2.0], "rotate_deg": 90.0, "scale": 2.0}}
    doc, _ = _read_glb(SC.write_scene_glb([el], name="x", extras={}))
    node = doc["nodes"][0]
    assert node["translation"] == [5.0, -3.0, 2.0]
    assert node["scale"] == [2.0, 2.0, 2.0]
    q = node["rotation"]                      # quaternion z pour 90°
    assert abs(q[2] - 0.7071067811865476) < 1e-12 and abs(q[3] - 0.7071067811865476) < 1e-12
    assert q[0] == 0.0 and q[1] == 0.0
```

Run : FAIL (material_pngs/tile_maps/holo_finish absents, writer ignore les clés).

- [ ] **Step 2 : implémentation dans forge3d_scene.py**

```python
def material_pngs(maps: dict) -> dict:
    """PIL -> PNG octets prêts pour le writer : `normal` (RGB), `mr` (pack
    glTF : G=rugosité, B=métal — conventions pbr_service), `ao` (L->RGB),
    `emissive` (RGB). N'émet que ce qui existe."""
    from PIL import Image
    out = {}

    def _png(im):
        b = io.BytesIO()
        im.save(b, "PNG")
        return b.getvalue()

    if maps.get("normal") is not None:
        out["normal"] = _png(maps["normal"].convert("RGB"))
    rough, metal = maps.get("roughness"), maps.get("metallic")
    if rough is not None or metal is not None:
        ref = rough if rough is not None else metal
        size = ref.size
        g = (rough.convert("L") if rough is not None
             else Image.new("L", size, 255)).resize(size)
        b = (metal.convert("L") if metal is not None
             else Image.new("L", size, 0)).resize(size)
        out["mr"] = _png(Image.merge("RGB", (Image.new("L", size, 255), g, b)))
    if maps.get("ao") is not None:
        out["ao"] = _png(maps["ao"].convert("L").convert("RGB"))
    if maps.get("emissive") is not None:
        out["emissive"] = _png(maps["emissive"].convert("RGB"))
    return out


def tile_maps(mid: str, kinds: tuple, tile_mm: float, w_mm: float, h_mm: float,
              out_px: int = 1024) -> dict:
    """Les maps d'une matière de la boutique, TUILÉES au pas physique tile_mm
    sur une toile au ratio de la carte — wrap-paste PIL déterministe. Niveaux
    de la matière CUITS (bake_levels) : la carte montre ce que Material Forge
    montre. Le tuilage est cuit -> le sampler du GLB reste CLAMP."""
    from app.services import material_store as MSTORE
    mat = MSTORE.read_material(mid)
    if mat is None:
        raise ValueError(f"matière introuvable : {mid}")
    maps = MSTORE.load_maps(mid, kinds=list(set(kinds) | {"basecolor"}))
    maps = MSTORE.bake_levels(maps, mat.get("props"))
    W = out_px if w_mm >= h_mm else max(8, int(round(out_px * w_mm / h_mm)))
    H = out_px if h_mm > w_mm else max(8, int(round(out_px * h_mm / w_mm)))
    tpx = max(4, int(round(W * tile_mm / w_mm)))
    out = {}
    for kind in kinds:
        src = maps.get(kind)
        if src is None:
            continue
        tuile = src.resize((tpx, tpx))
        toile = src.__class__.new(src.mode, (W, H)) if False else None  # (voir note)
        from PIL import Image as _I
        toile = _I.new(src.mode, (W, H))
        for y in range(0, H, tpx):
            for x in range(0, W, tpx):
                toile.paste(tuile, (x, y))
        out[kind] = toile
    return out
```
(Nettoyer la ligne factice `toile = src.__class__...` au profit du `_I.new` — elle ne
sert qu'à rappeler que `Image` s'importe en tête de fonction ou de module selon le
style du fichier.)

```python
_HOLO_RECIPES = {
    # §6.2bis-c — chiffres de la spec, relus par le test au bit près.
    "argent": {"base": [0.95, 0.95, 0.97, 1.0], "rough": 0.12, "ior": 1.8,
               "thickness": [200.0, 900.0]},
    "dorure": {"base": [1.0, 0.84, 0.55, 1.0], "rough": 0.12, "ior": 1.6,
               "thickness": [200.0, 600.0]},
}
_HOLO_SECTORS = 48       # secteurs radiaux : mip-stable, zéro moiré (§6.2bis-c)


def holo_finish(kind: str, aniso: bool, out_px: int = 1024) -> dict:
    """La finition holographique PRÊTE pour le writer : facteurs PBR de la
    recette + iridescence (épaisseur en secteurs radiaux, canal G linéaire)
    + clearcoat (le vernis laminé) + anisotropie optionnelle (direction
    TANGENTE au périmètre encodée RG). PUR calcul : mêmes octets à chaque
    appel — l'aperçu et le fichier livré sont le même monde."""
    from PIL import Image
    r = _HOLO_RECIPES[kind]
    cx = cy = out_px / 2.0
    tex = Image.new("RGB", (out_px, out_px))
    px = tex.load()
    for y in range(out_px):
        for x in range(out_px):
            ang = math.atan2(y - cy, x - cx)
            sect = int(((ang + math.pi) / (2 * math.pi)) * _HOLO_SECTORS) % _HOLO_SECTORS
            g = int(round(255 * ((sect % 8) / 7.0)))     # 8 paliers cycliques
            px[x, y] = (0, g, 0)
    b = io.BytesIO()
    tex.save(b, "PNG")
    out = {"pbr": {"baseColorFactor": r["base"], "metallicFactor": 1.0,
                   "roughnessFactor": r["rough"]},
           "iridescence": {"factor": 1.0, "ior": r["ior"],
                           "thickness": r["thickness"], "png": b.getvalue()},
           "clearcoat": {"factor": 1.0, "rough": 0.06},
           "anisotropy": None}
    if aniso:
        atex = Image.new("RGB", (out_px, out_px))
        apx = atex.load()
        for y in range(out_px):
            for x in range(out_px):
                ang = math.atan2(y - cy, x - cx) + math.pi / 2.0   # tangente
                apx[x, y] = (int(round((math.cos(ang) * 0.5 + 0.5) * 255)),
                             int(round((math.sin(ang) * 0.5 + 0.5) * 255)), 0)
        ab = io.BytesIO()
        atex.save(ab, "PNG")
        out["anisotropy"] = {"strength": 0.85, "png": ab.getvalue()}
    return out
```
NOTE perf : la double boucle 1024² en Python pur ≈ 1 M d'itérations ×2 — acceptable
pour UNE génération par build, mais si la mesure locale dépasse ~2 s, vectoriser via
`Image.frombytes` sur un `bytes` construit par lignes (rester stdlib+PIL, même octets).

**Amendements de `write_scene_glb`** (le writer reste écrit-juste-du-premier-coup) :
- `el.get("trs")` → le nœud d'élément porte `translation` (trs.translate, à défaut
  l'ancien z_mm en translation z — compat 2a intacte), `rotation` (quaternion
  `[0, 0, sin(rad/2), cos(rad/2)]` si `rotate_deg`), `scale` (`[s, s, s]` si ≠ 1) ;
- `el.get("mat_maps")` → images/textures supplémentaires (même sampler CLAMP unique) ;
  matériau : `normalTexture`, `metallicRoughnessTexture` (et ALORS metallicFactor =
  roughnessFactor = 1.0), `occlusionTexture`, `emissiveTexture` +
  `emissiveFactor [1,1,1]` — chaque map seulement si présente ;
- `el.get("finish")` → facteurs PBR de la recette (écrasent les défauts), extensions
  sur le matériau : `KHR_materials_iridescence` {iridescenceFactor, iridescenceIor,
  iridescenceThicknessMinimum/Maximum, iridescenceThicknessTexture},
  `KHR_materials_clearcoat` {clearcoatFactor, clearcoatRoughnessFactor},
  `KHR_materials_anisotropy` {anisotropyStrength, anisotropyTexture} si aniso — et
  l'attribut `TANGENT` (VEC4, `[1, 0, 0, 1] * nverts`, accessor float exact) ajouté à
  la primitive de CET élément ;
- collecte doc-level : `extensionsUsed` = union triée des extensions posées — ABSENT
  si vide ; `extensionsRequired` n'est JAMAIS écrit par nous ;
- alpha : un élément avec `finish` reste au mode de son `alpha` (les plans du sceau
  seront opaques par leurs nœuds — pas de règle cachée ici).

- [ ] **Step 3 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): matieres tuilees (pack MR glTF), finitions holo iridescence/clearcoat/anisotropy extensionsUsed-only, TRS par element"
```

---

### Task 6: `build3d` chaîné — fusion des GLB externes, STL mixte, metadata moteurs

**Files:**
- Modify: `backend/app/services/cards/forge3d_scene.py` (fusion)
- Modify: `backend/app/services/cards/forge3d.py` (résolution de chaînes + route)
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : tests en RED**

```python
def _job_servi(did, nid, glb: bytes, closed, engine="meshy-7", credits=None):
    """Pose un nœud mesh3d SERVI sur disque (comme l'aurait fait Task 4)."""
    base = OUTPUTS / "decks" / did / "forge3d" / "nodes" / nid
    (base / "textures").mkdir(parents=True, exist_ok=True)
    (base / "model.glb").write_bytes(glb)
    job = {"schema": "card-3d/mesh3d-job@1", "node": nid, "engine": engine,
           "status": "served", "progress": 100, "error": None,
           "closed": closed, "files": {"glb": "model.glb"}}
    if credits is not None:
        job["consumed_credits"] = credits
    (base / "job.json").write_text(json.dumps(job), encoding="utf-8")


def test_l_assemblage_fusionne_le_glb_externe_a_sa_place_de_couche():
    """Chaîne layer->mesh3d->transform->assemble : l'élément externe est
    réindexé sous un parent au TRS calculé (ajusté à la BOÎTE MM de sa couche,
    centré, à z du transform), l'identité du doc externe est jetée, les
    accesseurs restent exacts, le STL mixte sort quand tout est fermé."""
    from PIL import Image
    from app.services.cards import forge3d_scene as SC
    did = _deck("Fusion")
    _exporter_couches(did)
    # l'« externe » : un relief FERMÉ écrit par notre writer (bornes exactes
    # garanties), taille connue 63x88 -> le fit se calcule de tête
    relief = SC.relief_mesh(Image.new("L", (8, 8), 255), 63.0, 88.0, 1.0, 0.3, 4)
    relief["closed"] = True
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    ext = SC.write_scene_glb([{"name": "brut", "mesh": relief,
                               "png": png.getvalue(), "alpha": False,
                               "z_mm": 0.0}], name="brut", extras={})
    _job_servi(did, "m1", ext, closed=True, engine="meshy-7", credits=30)

    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": "meshy-7", "texture_prompt": "", "ultra": False},
        {"id": "tr", "kind": "transform", "x_mm": 0, "y_mm": 0, "z_mm": 2.0,
         "rot_deg": 0, "scale": 1.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "fusion3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "tr"},
                  {"from": "tr", "to": "asm"}, {"from": "s2", "to": "t2"},
                  {"from": "t2", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d", json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, binv = _read_glb(glb)
    plat = json.dumps(doc)
    for mot in ("generator", "copyright", "author", "producer"):
        assert f'"{mot}"' not in plat, mot
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    assert "illustration" in noms and "cadre" in noms
    parent_ext = doc["nodes"][racine["children"][noms.index("illustration")]]
    # le fit : la couche illustration des couches synthétiques couvre une boîte
    # mesurée au manifeste ; l'externe (63x88) y est mis à l'échelle et posé à
    # z=2.0 — on relit le manifeste pour calculer l'attendu EXACT
    man = json.loads(_api("GET", f"/api/cards/{did}/forge3d/file/layers_c00_front.json").content)
    boite = next(l for l in man["layers"] if l["role"] == "illustration")["box_mm"]
    bw = boite[2] - boite[0]; bh = boite[3] - boite[1]
    s = min(bw / 63.0, bh / 88.0)
    assert abs(parent_ext["scale"][0] - s) < 1e-9
    assert abs(parent_ext["translation"][2] - 2.0) < 1e-9
    # bornes des accesseurs du doc fusionné : toujours EXACTES (re-mesure)
    import struct as _s
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126 or "min" not in acc:
            continue
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
        lo = [float("inf")] * n; hi = [float("-inf")] * n
        for e2 in range(acc["count"]):
            vals = _s.unpack_from("<" + "f" * n, binv, off + e2 * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c]); hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi
    # metadata : les moteurs utilisés, mesurés
    meta = json.loads(_api("GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["engines"] == "local+meshy-7"
    assert types["elements_3d"] == 2
    # STL : les DEUX éléments sont fermés -> écrit, longueur exacte
    assert b["stl"]["written"] is True
    stl = _api("GET", f"/api/cards/{did}/forge3d/file/{b['stl']['name']}").content
    assert len(stl) == 84 + 50 * struct.unpack("<I", stl[80:84])[0]


def test_un_noeud_mesh3d_sans_glb_servi_refuse_l_assemblage():
    did = _deck("Trou")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d", json={"graph": g, "card": 0})
    assert r.status_code == 409
    assert "m1" in r.json()["detail"] and "servi" in r.json()["detail"]


def test_le_stl_mixte_refuse_un_externe_ouvert_ou_non_mesure():
    from app.services.cards import forge3d_scene as SC
    from PIL import Image
    did = _deck("Ouvert")
    _exporter_couches(did)
    png = io.BytesIO(); Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    q = SC.quad_mesh(63.0, 88.0); q["closed"] = False
    ext = SC.write_scene_glb([{"name": "plan", "mesh": q, "png": png.getvalue(),
                               "alpha": True, "z_mm": 0.0}], name="p", extras={})
    _job_servi(did, "m1", ext, closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d", json={"graph": g, "card": 0})
    b = r.json()["artifact"]
    assert b["stl"]["written"] is False and "ferm" in b["stl"]["why"]
    # closed=None (non mesuré) refuse aussi, motif différent
    _job_servi(did, "m1", ext, closed=None)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d", json={"graph": g, "card": 0})
    assert r2.json()["artifact"]["stl"]["written"] is False
    assert "mesur" in r2.json()["artifact"]["stl"]["why"]


def test_le_rebuild_efface_l_apercu_perime():
    """Legs 4 : rebâtir `carte3d` supprime carte3d_preview.png — le metadata
    ne montre plus jamais l'ancien GLB."""
    did = _deck("Perime")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    fdir = OUTPUTS / "decks" / did / "forge3d"
    (fdir / "carte3d_preview.png").write_bytes(_png(Image.new("RGBA", (4, 4))))
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    assert not (fdir / "carte3d_preview.png").exists()


def test_le_glb_externe_a_images_uri_est_refuse_motive():
    did = _deck("Uri")
    _exporter_couches(did)
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
           "accessors": [
               {"componentType": 5126, "count": 3, "type": "VEC3",
                "bufferView": 0, "min": [0, 0, 0], "max": [1, 1, 0]},
               {"componentType": 5125, "count": 3, "type": "SCALAR", "bufferView": 1}],
           "images": [{"uri": "https://ailleurs.example/tex.png"}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                           {"buffer": 0, "byteOffset": 36, "byteLength": 12}],
           "buffers": [{"byteLength": 48}]}
    binv = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0.5, 1, 0) + struct.pack("<3I", 0, 1, 2)
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    glb = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binv))
           + struct.pack("<II", len(js), 0x4E4F534A) + js
           + struct.pack("<II", len(binv), 0x004E4942) + binv)
    _job_servi(did, "m1", glb, closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d", json={"graph": g, "card": 0})
    assert r.status_code == 409 and "uri" in r.json()["detail"].lower()
```

(Réutiliser le helper `_job_servi` et `_exporter_couches` définis plus haut ; `Image`
et `io` sont déjà importés dans le fichier de test. Le nom du manifeste
`layers_c00_front.json` : reprendre la convention EXACTE des tests 2a du fichier —
si l'existant nomme `layers_c{NN}_{side}.json` avec un autre gabarit pour card 0,
suivre l'existant.)

Run : FAIL.

- [ ] **Step 2 : la fusion dans forge3d_scene.py**

`write_scene_glb` gagne un paramètre `externals: list | None = None`, traité APRÈS les
éléments locaux, chaque entrée `{"name", "glb": bytes, "fit": {"scale": s,
"translate": [x, y, z], "rotate_deg": r}}` :

```python
def _merge_external(doc, buf, views, accessors, images, textures, materials,
                    meshes, nodes, ext: dict) -> list:
    """Réindexation complète d'UN GLB externe dans le document en cours.
    - bufferViews recopiées dans LE buffer (offsets décalés, pad4 respecté) ;
    - images par bufferView OBLIGATOIRES (une image `uri` -> ValueError nommée :
      rien ne se télécharge à l'assemblage) ;
    - samplers du doc externe PRÉSERVÉS (leurs textures tuilent parfois en
      REPEAT — c'est LEUR matériau ; notre CLAMP ne vaut que pour NOS couches) ;
    - matériaux/textures/meshes décalés ; hiérarchie de nœuds interne gardée,
      re-basée sous UN parent {name, TRS du fit} retourné à l'appelant ;
    - animations/skins JETÉS (retournés dans `ignored`) ;
    - asset/generator/copyright du doc externe JETÉS (scrub_identity) ;
    - extensionsUsed ∪ ; leurs extensionsRequired CONSERVÉES telles quelles
      (honnêteté : le doc fusionné les exige vraiment) — les NÔTRES n'y entrent
      jamais."""
```
Points d'implémentation imposés :
- offsets : `pad4()` avant chaque vue recopiée (réutiliser le helper existant du
  writer) ; `byteOffset += base` où base = offset de recopie de la vue (recopier VUE
  PAR VUE, pas le buffer entier : les paddings d'origine ne sont pas les nôtres) ;
- décalages d'indices : construire `dv` (map vue), `da` (accessors), `di` (images),
  `dt` (textures), `dm` (matériaux), `dh` (meshes), `dn` (nodes) puis réécrire les
  références dans les copies (`prim["attributes"]`, `prim["indices"]`,
  `prim["material"]`, `textures[i]["source"]`, `normalTexture.index`, etc. — balayer
  les dicts de matériau récursivement pour toute clé `index`) ;
- sampler : si le doc externe n'a PAS de samplers mais des textures, pointer son
  entrée vers un sampler par défaut AJOUTÉ (wrap par défaut glTF = REPEAT : créer
  `{}` vide — jamais recycler notre CLAMP) ;
- le parent : quaternion z depuis `rotate_deg` (même formule que Task 5), `scale`
  uniforme, `translation` ; ses `children` = les racines des scènes du doc externe
  (toutes les scènes, à défaut tous les nœuds orphelins) ;
- retour : liste `ignored` (["animations x2", "skins x1"] si jetés).

`fit` calculé côté forge3d.py (PAS dans la scène — c'est une décision de placement) :
```python
def _fit_external(glb: bytes, box_mm: list, z_mm: float, trs: dict | None) -> dict:
    """Échelle uniforme pour tenir dans la boîte mm de SA couche (max-fit,
    proportions gardées), centré sur la boîte, posé à z. Le transform utilisateur
    COMPOSE : scale multiplie, rotation s'ajoute, translation s'ajoute."""
    m = glb_scene_mesh(glb)
    xs = m["positions"][0::3]; ys = m["positions"][1::3]; zs = m["positions"][2::3]
    mw, mh = (max(xs) - min(xs)) or 1.0, (max(ys) - min(ys)) or 1.0
    bw, bh = box_mm[2] - box_mm[0], box_mm[3] - box_mm[1]
    s = min(bw / mw, bh / mh)
    t = trs or {}
    s *= float(t.get("scale") or 1.0)
    cx = (box_mm[0] + box_mm[2]) / 2.0 - s * (min(xs) + max(xs)) / 2.0
    cy = (box_mm[1] + box_mm[3]) / 2.0 - s * (min(ys) + max(ys)) / 2.0
    cz = float(z_mm) - s * min(zs)
    return {"scale": s,
            "translate": [cx + float(t.get("x_mm") or 0.0),
                          cy + float(t.get("y_mm") or 0.0),
                          cz + float(t.get("z_mm") or 0.0)],
            "rotate_deg": float(t.get("rot_deg") or 0.0)}
```
(ATTENTION : si le transform est la SEULE source de z, ne pas le compter deux fois —
la règle : `z_mm` passé à `_fit_external` = 0.0 et TOUT le z vient de `t["z_mm"]`.
Le test l'épingle : translation z == 2.0 exactement.)

- [ ] **Step 3 : forge3d.py — résolution de chaînes + route**

`_resolve_graph_elements` v2 (garder la signature de sortie `(elements, ignored)` en
l'étendant) :
- adjacence `from→[to]` et inverse ; pour chaque nœud de TRAITEMENT (plane/relief/
  mesh3d) : sa source = l'unique `layer` amont (comme en 2a) ; sa CHAÎNE aval = suivre
  les edges à travers `material` puis `transform` (0 ou 1 de chaque, dans n'importe
  quel ordre — s'arrêter à `assemble`) ;
- `plane`/`relief` : élément local comme en 2a + si `material` dans la chaîne :
  `mat_maps` = `material_pngs(tile_maps(mat, ("normal", "roughness", "metallic",
  "ao", "emissive"), tile_mm, w_mm, h_mm))` quand `mat` est posé (matière introuvable
  sur disque → l'élément passe SANS maps et la paire entre dans `ignored` avec motif) ;
  si `finish != "aucune"` : `finish = holo_finish(finish, aniso)` ; si `transform` :
  `trs` sur l'élément (translate/rotate/scale — le z_mm 2a devient
  `translate[2]` s'il n'y a pas de transform, sinon le transform gagne) ;
- `mesh3d` : lire `nodes/{nid}/job.json` — absent ou `status != "served"` → **409**
  « le nœud {nid} n'a pas servi son GLB — lance-le d'abord » ; lire `model.glb`
  (borne `MAX_EXT_GLB_BYTES` sinon 400 nommé) ; boîte mm de SA couche depuis le
  manifeste du disque (coverage 0 ou boîte absente → toute la carte) ; construire
  l'entrée externe `{"name": role, "glb", "fit": _fit_external(...), "engine",
  "closed": job["closed"]}` ; un `material` chaîné sur un mesh3d → `ignored`
  (« matière ignorée : le GLB moteur porte déjà ses matériaux ») ;
- toute `ValueError` de la fusion/lecture GLB (uri, tronqué…) → **409** au message
  littéral.

Route `build3d` :
- appel `write_scene_glb(elements_locaux, name, extras, externals=externes)` ;
- **aperçu périmé (legs 4)** : avant d'écrire `{name}.glb`, `unlink` de
  `{name}_preview.png` s'il existe (le bordereau garde `preview: {expected, written:
  false}` — mécanique 2a inchangée) ;
- STL : tous les éléments doivent être fermés — locaux par le drapeau constructeur
  (2a), externes par `job["closed"] is True` ; `False` → refus « …pas un solide
  fermé… » ; `None` → refus « fermeture non mesurée (maillage trop lourd) » ; sinon
  STL = locaux (writer deux-passes) + externes (`glb_scene_mesh` + application
  scale/rotation/translation du fit AVANT packing — étendre `_write_stl_binary` d'un
  paramètre `externals` qui transforme sommet par sommet, streaming, deux passes) ;
- metadata : `engines` = `"+".join(sorted({"local"} | {moteurs des externes}))` quand
  il y a au moins un élément local, sinon juste les moteurs triés ; `elements_3d` =
  total ; le bordereau liste par élément `{name, kind: "local"|"externe", engine?,
  credits?}` + `ignored` ;
- plafond `MAX_GRAPH_ELEMENTS` inchangé (locaux + externes confondus).

- [ ] **Step 4 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): fusion des GLB externes dans l artefact - fit a la boite de couche, STL mixte gate par closed cache, metadata moteurs"
```

---

### Task 7: L'écran 2b — chaînes de nœuds, prix AVANT, Lancer/poll, legs 5

**Files:**
- Modify: `frontend/cardforge/js/mod-forge3d.js`
- Modify: `frontend/cardforge/css/mod-forge3d.css`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : test de source en RED**

```python
def test_l_ecran_2b_affiche_les_prix_avant_et_les_etats_de_job():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # le sélecteur de traitement offre mesh3d, les moteurs viennent de /info
    # (jamais une liste recopiée), le prix est affiché sur le nœud ET sommé
    assert "mesh3d" in rendu
    assert 'INFO.mesh3d' in rendu and "engines" in rendu
    assert 'id="cf-forge3d-cost"' in rendu
    # Lancer -> POST mesh3d/{nid}, puis poll GET jusqu'au terminal
    corps = rendu.split("async function launchMesh3d(")[1].split("\n  }")[0]
    assert 'M.api.post("mesh3d/"' in corps
    assert "pollMesh3d" in rendu
    # crédit/clé : l'écran DIT quand la clé manque (has_meshy) et n'invente rien
    assert "has_meshy" in rendu
    # texture_prompt et ultra existent (meshy), bornés par prompt_max de /info
    assert "texture_prompt" in rendu and "ultra" in rendu and "prompt_max" in rendu
    # matière + finition + aniso + tile, transform x/y/z/rot/scale : édités par
    # M.patch via le graphe (annulable), bornes lues de /info
    for champ in ("material_limits", "transform_limits", "finish", "aniso",
                  "tile_mm", "rot_deg"):
        assert champ in rendu, champ
    # legs 5 : le manifeste est rechargé quand la CARTE change, pas au boot seul
    assert "LAST_MANIFEST" in rendu and "cardChanged" in rendu
    # l'échec d'un job est montré LITTÉRAL (error du job.json)
    assert "job.error" in rendu or 'job["error"]' in rendu
```

Run : FAIL.

- [ ] **Step 2 : implémentation (suit les patrons DU fichier — paintGraph/rowHtml/
editGraph/M.patch/M.api, exigences fixées par le test et par ce qui suit)**

1. **Modèle de rangées chaînées** : `rowModel(graph)` → pour chaque paire 2a
   {layer, traitement} : suivre la chaîne aval (`material`, `transform`) et rendre
   UNE rangée `{layer, proc, mat?, trs?}`. Toute édition passe par `setGraph`
   (reconstruction nodes+edges de la rangée, M.patch, HIST inchangé). Le sélecteur de
   traitement gagne `mesh 3D` ; en le choisissant, la rangée gagne le BLOC mesh3d :
   - `<select>` moteur peuplé de `INFO.mesh3d.engines` — libellé
     `label · 0,30 $` (fal) ou `label · 30 cr (~0,60 $)` (meshy) ; défaut
     `INFO.mesh3d.default_engine` ; si `!INFO.mesh3d.has_meshy`, les moteurs meshy
     sont suffixés « — clé requise (Réglages) » et le bouton Lancer est désactivé
     pour eux (le backend redirait 503 : l'écran le DIT avant) ;
   - champ `texture_prompt` (maxlength = `INFO.mesh3d.prompt_max`), case `ultra`
     visible SEULEMENT quand moteur = meshy-7 (elle ajoute
     `ultra_extra_credits` au prix affiché) ;
   - bouton **Lancer/Relancer** → `launchMesh3d(nid)` ; chip d'état peinte depuis le
     job : `en file / en cours N % / servi · N cr / échec : {error littéral}` ;
2. **`launchMesh3d(nid)`** : `M.api.post("mesh3d/" + encodeURIComponent(nid),
   {graph: get("graph"), card: CF.current()})` puis `pollMesh3d(nid)` —
   `setTimeout` 1200 ms, re-GET, repeint la chip, s'arrête au terminal ; un poll par
   nid (registre local, relance idempotente) ; toute erreur HTTP → chip échec avec le
   `detail` du backend TEL QUEL ;
3. **Pied de coût** `#cf-forge3d-cost` : somme des nœuds mesh3d NON servis
   (fal en $, meshy en crédits + équivalent $), recalculée à chaque paint —
   « Coût à lancer : 0,30 $ + 35 cr Meshy (~0,70 $) » ; zéro nœud payant →
   « Graphe 100 % gratuit » ;
4. **Blocs matière/transform** de la rangée : selects/inputs bornés par
   `INFO.material_limits`/`INFO.transform_limits`, matières de `INFO.materials`
   (option « aucune » + nom), finitions (`aucune/argent/dorure` : libellés « argent
   holographique »/« dorure holographique »), case `aniso`, champ `tile_mm` ; un mot
   d'aide : « matière sur plan/relief seulement — un GLB moteur garde la sienne » ;
5. **Legs 5** : suivre la carte courante — mémoriser `LAST_MANIFEST.card` et, dans le
   chemin de peinture appelé à chaque rendu (là où `CF.current()` est disponible,
   même endroit que le seed 2a), si l'étiquette de carte a changé →
   `cardChanged()` qui re-fetch le manifeste (même mécanique que `refreshManifest`)
   puis repeint ; AUCUN nouveau listener global (le piège syncInputs/renderPanel de
   mod-face reste la référence : préserver le focus) ;
6. **Bordereau build3d** : les éléments listés avec leur moteur et crédits consommés
   (`b.elements`), la liste `ignored` affichée telle quelle ;
7. CSS : chips d'état (file/cours/servi/échec), blocs repliés des rangées, pied de
   coût — tout scopé `.cf-forge3d`, styles sobres existants.

- [ ] **Step 3 : GREEN + vérifications + commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
python scripts\qa\lint_cardforge.py --module forge3d
node frontend\cardforge\qa\test_core_contract.mjs --contract
```
(Vérifier les OCTETS du .js après édition — piège Windows NUL/CRLF connu du chantier.)
```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): ecran 2b - rangees chainees, moteurs et prix servis par /info, lancer/poll des jobs, cout avant, manifeste par carte"
```

---

### Task 7bis: Fluidité des manipulations à la souris (spec §9.6 — toutes les surfaces de drag du lab)

**Files:**
- Modify: `frontend/cardforge/js/mod-frame.js` (fenêtre du cadre — la plainte d'origine)
- Modify: `frontend/cardforge/js/mod-face.js`, `mod-type.js`, `mod-texture.js`,
  `mod-print.js`, `mod-solid.js` (mêmes gestes, même remède)
- Modify: `frontend/cardforge/css/*.css` correspondants (curseurs, `touch-action`)
- Modify: `scripts/qa/lint_cardforge.py` (règle « octets sains »)
- Test: `backend/tests/test_cards_forge3d.py` N'EST PAS le bon fichier — les tests de
  source des pièces vivent dans les tests de CHAQUE pièce ; ajouter les asserts de
  source au fichier de test de la pièce modifiée quand il a déjà une section « source »
  (sinon le lint porte la vérification)

Contexte mesuré (ne pas re-diagnostiquer) : `core.js` coalesce DÉJÀ l'aperçu au rAF
(`invalidate`, core.js:889-897). Le problème est en AMONT : les `pointermove` des
pièces font un `M.patch` PAR ÉVÉNEMENT (mod-frame.js:2446-2463 par exemple) — clone
`sanitize`, `markDirty`, `emitCore("core:doc")` diffusé aux ~10 modules, `scheduleSave`
— jusqu'à ~1000 fois/s sur une souris à haut taux de scrutation. Le rectangle traîne
derrière le curseur : la « latence » et l'« imprécision » perçues sont le même défaut.

- [ ] **Step 1 : le patron rAF, appliqué à mod-frame.js d'abord**

Dans `wireMap` (mod-frame.js:2430-2489), remplacer le `M.patch` direct du
`pointermove` par le patron coalescé :

```js
    let drag = null, pendingWin = null, rafId = 0;
    const flushWin = () => {
      rafId = 0;
      if (!pendingWin) return;
      const n = pendingWin; pendingWin = null;
      M.patch({ window: n });          /* <= 1 patch par frame (spec 9.6-1) */
    };
    /* ... dans pointermove, a la place de M.patch({window:n}) : */
      pendingWin = n;
      if (!rafId) rafId = (typeof requestAnimationFrame === "function"
        ? requestAnimationFrame(flushWin) : setTimeout(flushWin, 16));
      drawMapWith(n);                  /* feedback LOCAL immediat (9.6-2) */
```
et au `pointerup`/`pointercancel` (`end`) : annuler le rAF en attente puis appliquer
l'état FINAL exact (`if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
if (pendingWin) { M.patch({ window: pendingWin }); pendingWin = null; }`) AVANT le
push HIST existant. `drawMapWith(n)` = le `drawMap` actuel paramétré par la fenêtre en
cours de geste (le dessin de la mini-carte lit aujourd'hui l'état du doc ; lui passer
la fenêtre candidate évite d'attendre le patch). Poignée : zone de saisie 8→12 px
(les DEUX tests `< 8` de pointerdown), curseurs contextuels (`cv.style.cursor` =
`nwse-resize` sur la poignée au survol, `move` dans la fenêtre, `crosshair` sinon)
et `touch-action: none` sur le canvas de la mini-carte (CSS de la pièce).

- [ ] **Step 2 : le même patron sur les cinq autres surfaces**

Lire chaque handler AVANT de le modifier (les modes de geste diffèrent), appliquer le
MÊME remède : état de geste local + un patch par frame + patch final exact au relâché +
`touch-action: none` + poignées/zones ≥ 12 px là où il y a des poignées. Surfaces :
mod-face.js:3769-3790 (pose), mod-type.js:4022-4126 (overlay de slots — le futur cœur
de l'édition directe §6.1), mod-texture.js:1509-1520, mod-print.js:1462-1481,
mod-solid.js:557-570. AUCUN changement de sémantique : mêmes bornes, mêmes arrondis,
même HIST une-fois-par-geste. Si une surface fait DÉJÀ moins d'un patch par frame
(certaines ne patchent qu'au relâché), la laisser telle quelle et le noter au rapport.

- [ ] **Step 3 : l'octet NUL échappé + la règle lint « octets sains »**

mod-frame.js contient UN octet NUL brut (offset ~180802, dans
`s.indexOf("<NUL>")` d'un parseur binaire — légal en JS mais il fait passer le fichier
pour du binaire aux outils, grep s'arrête dessus). Le remplacer par la séquence
ÉCHAPPÉE `"\x00"` (4 caractères). Puis, dans lint_cardforge.py, nouvelle règle nommée
R13 « octets sains » : pour chaque fichier js/css/py/mjs du lab, lire les OCTETS et
signaler tout `\x00` brut et tout `\r` (CRLF) — violation, pas avertissement.
Vérifier : `python scripts\qa\lint_cardforge.py` complet → 0 violation (mod-frame
corrigé, aucun autre fichier atteint).

- [ ] **Step 4 : vérification navigateur RÉELLE**

Via cf_deploy puis dans l'app : faire glisser la fenêtre du cadre avec des mouvements
RAPIDES — le rectangle suit le curseur sans traîner ; la poignée s'attrape sans viser
au pixel ; l'annulation reste UNE entrée par geste ; répéter sur un slot P3 (overlay) et
la pose P1. Rapporter ce qui est vu (avant/après si possible).

- [ ] **Step 5 : GREEN + commit**

Les tests de source des pièces concernées (s'il en existe qui épinglent les handlers
modifiés) restent verts ; lint complet vert ; `node frontend\cardforge\qa\test_core_contract.mjs
--contract` inchangé.
```bash
git add frontend/cardforge/js frontend/cardforge/css scripts/qa/lint_cardforge.py
git commit -m "perf(cardforge): un patch par frame pendant les gestes souris, poignees 12px, touch-action none, NUL echappe + lint octets sains - spec 9.6"
```

---

### Task 8: Intégration finale 2b

- [ ] Suite complète : `run-tests.ps1 -Filter cards` → tout vert ; `-Filter meshy` → vert.
- [ ] `lint_cardforge.py` complet → 0 violation ; `--geom` et `--contract` → tenus.
- [ ] `cf_deploy.ps1` : déployer, puis `-Check` → 0 écart. Redémarrer le backend
      installé (piège du processus orphelin sur :8765 — le tuer d'abord, sinon les
      réglages/routes restent d'hier).
- [ ] **Vérification navigateur RÉELLE, zéro dépense** : poser `MESHY_MOCK=1` dans le
      `.env` des données de l'app (le noter), redémarrer le backend, puis dans le lab :
      exporter les couches d'un deck réel → passer l'illustration en « mesh 3D »
      moteur meshy-7 + ultra → le nœud affiche « 35 cr (~0,70 $) » et le pied de
      graphe la somme AVANT → Lancer → chip en cours → servi → Construire → l'aperçu
      model-viewer montre l'élément externe fusionné À SA PLACE + le relief du cadre →
      le STL est REFUSÉ MOTIVÉ (le triangle du mock est ouvert — c'est la preuve du
      gate) → bordereau : moteurs `local+meshy-7`, crédits consommés 35 → une rangée
      matière (une matière de la boutique + finition « argent holographique ») →
      re-Construire → aperçu : reflets iridescents visibles en tournant la carte
      (rapporter CE QUI EST VU, deux angles differents = teintes différentes) →
      retirer `MESHY_MOCK` du .env, re-redémarrer. Rapporter chaque étape. Dans la
      même session navigateur : re-vérifier la FLUIDITÉ (Task 7bis) sur la fenêtre du
      cadre et un slot P3 à mouvements rapides.
- [ ] Mémoire du chantier : mettre à jour `cardforge-universel.md` (2b livrée, restes
      éventuels), et le plan (cases cochées, amendements à la source si des fautes de
      plan ont été trouvées en route).
- [ ] Commit de clôture éventuel + PUSH de la branche du chantier.
- [ ] Dire à l'utilisateur : la clé Meshy se colle dans Réglages (champ existant du
      3D Studio, `MESHY_API_KEY`) ; proposer — SANS le faire — un premier tir réel
      meshy-7 (30-35 cr) sur une carte de son choix.

---

## Auto-revue du plan

- **Périmètre 2b couvert** : mesh3d 7 moteurs + jobs + prix avant (§5.2/§5.3, Tasks
  3-4) ; moteurs meshy-6/7 via l'API directe et la grille officielle v7/ultra des
  deux côtés du miroir + option studio3d (amendement spec du 20/08, Task 2) ; matières
  Material Forge sur plane/relief avec pack MR conforme (§5.2, Tasks 5-6) ;
  iridescence/anisotropy/clearcoat extensionsUsed-only, recettes §6.2bis-c au chiffre
  près, épaisseur radiale relue dans le canal G (Task 5) ; fusion des GLB externes par
  réindexation + fit à la boîte de couche + STL mixte + metadata moteurs (§5.4/§5.5,
  Task 6) ; 3MF tranché « refus motivé permanent » (spec amendée — aucun code : le
  refus 2a existe déjà). **Legs 6 points** : (1) closed mesuré une fois et caché
  (Task 4) ; (2) nodes/{nid} (Task 4) ; (3) transform apporte le z/offset (Tasks 5-6) ;
  (4) aperçu périmé supprimé au rebuild + dossier nœud réinitialisé à la relance
  (Tasks 4/6) ; (5) LAST_MANIFEST au changement de carte (Task 7) ; (6) découpe
  forge3d_scene + STL deux-passes (Task 1).
- **Placeholders** : les corps de routes/UI non recopiés ici s'appuient sur des
  patrons DÉJÀ dans les mêmes fichiers (get_info/post_layers/build3d,
  paintGraph/rowHtml/grabZip) avec les exigences fixées par les tests fournis — même
  convention que le plan 2a. Deux lignes factices de tests sont explicitement
  signalées à adapter/retirer (`x-noop`, `src.__class__`).
- **Cohérence de types** : `holo_finish` → `{pbr, iridescence{factor, ior, thickness,
  png}, clearcoat, anisotropy?}` consommé par `write_scene_glb(el["finish"])` et
  vérifié par le test au même schéma ; `material_pngs` → clés `normal/mr/ao/emissive`
  = celles que le writer câble ; `_fit_external` → `{scale, translate, rotate_deg}` =
  l'entrée `externals[].fit` ; `job.json` schéma `card-3d/mesh3d-job@1` partagé entre
  Tasks 4, 6 et 7 (mêmes champs, mêmes états `queued/running/served/failed`).
- **Argent** : aucun test ni étape de vérification ne dépense — fal monkeypatché,
  Meshy sur mock, tir réel = proposition finale opt-in.
- **Risques nommés** : perf de la double boucle holo 1024² (note de vectorisation à
  iso-octets) ; équivalence du STL deux-passes (l'actuel fait foi en cas d'écart) ;
  lint face au nouveau fichier (autorisation nommée prévue) ; formats de manifeste
  (les tests reprennent la convention 2a du fichier de test).
