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
# -*- coding: utf-8 -*-
# NB (revue) : le test de pureté scanne TOUT ce fichier, commentaires compris
# — le nom du framework HTTP du projet ne doit apparaître nulle part ici,
# même en prose (voir test_cards_forge3d.py, l'assertion sur ce mot en
# minuscules : un rappel de SON nom ici la ferait échouer).
"""P9 Forge 3D — géométrie et écriture de scène, PURES (zéro dépendance HTTP).

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
    """STL binaire local, en millimètres, DEUX PASSES : compter d'abord le
    total de triangles (pour dimensionner le buffer de sortie UNE fois), puis
    packer chaque facette directement dedans — l'ancienne version
    matérialisait toute la géométrie en tuples Python avant d'écrire (~160 Mo
    d'intermédiaires par relief au grid max, mesuré en 2a). Même sortie, au
    bit près (couture legs 6, revue finale 2a). `z_mm` de chaque élément
    (l'écart de pile porté par SON nœud, comme dans le GLB) est appliqué aux
    positions puisque le format STL n'a pas de nœud pour le porter.

    `elements` est parcouru DEUX FOIS (le comptage, puis l'emballage) : une
    LISTE (ou toute séquence re-parcourable), jamais un générateur à usage
    unique — la seconde passe le trouverait épuisé et écrirait un buffer de
    la bonne taille mais rempli de zéros après le premier élément."""
    total = sum(len(el["mesh"]["indices"]) // 3 for el in elements)
    out = bytearray(84 + 50 * total)
    # [:80] n'est pas cosmétique : le compte de triangles est empaqueté à
    # l'offset FIXE 80 juste en dessous (struct.pack_into("<I", out, 80, ...))
    # -- une entête qui déborderait au-delà de 80 octets décalerait ce champ
    # (et toute la suite du buffer), le corrompant silencieusement.
    entete = f"{name} - millimetres - {total} triangles".encode(
        "ascii", "ignore")[:80]
    out[0:len(entete)] = entete
    struct.pack_into("<I", out, 80, total)
    off = 84
    for el in elements:
        pos, idx = el["mesh"]["positions"], el["mesh"]["indices"]
        z = float(el.get("z_mm") or 0.0)
        for t in range(0, len(idx) - 2, 3):
            a, b, c = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
            ax, ay, az = pos[a], pos[a + 1], pos[a + 2] + z
            bx, by, bz = pos[b], pos[b + 1], pos[b + 2] + z
            cx, cy, cz = pos[c], pos[c + 1], pos[c + 2] + z
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
print("— meshy-7 + ultra —")
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

# le miroir JS porte les mêmes valeurs — confronté PAR VALEUR via node, pas
# par simple présence de sous-chaîne (le docstring du module promet mieux).
_js_path = (pathlib.Path(__file__).resolve().parent.parent.parent
           / "frontend" / "meshy" / "meshy.client.js")
if shutil.which("node") is None:
    _js = _js_path.read_text(encoding="utf-8")
    _bloc = _js.split("export const CREDITS")[1].split("};")[0]
    assert "meshy-7" in _bloc and "ultra" in _bloc
    ok("miroir JS non confronté : node absent (substring seulement)")
else:
    _js_url = "file:///" + str(_js_path.resolve()).replace("\\", "/")
    _node_script = f"""
const M = await import(new URL({_json.dumps(_js_url)}));
const models = ["meshy-5", "meshy-6", "meshy-7", "latest"];
const modelTypes = ["standard", "lowpoly", "smart-topology"];
const out = [];
for (const aiModel of models)
  for (const modelType of modelTypes)
    for (const shouldTexture of [true, false])
      for (const textureResolution of ["2k", "8k"])
        for (const ultra of [true, false]) {{
          out.push({{
            aiModel, modelType, shouldTexture, textureResolution, ultra,
            img: M.CREDITS.imageTo3d({{ aiModel, modelType, shouldTexture, textureResolution, ultra }}),
            prev: M.CREDITS.textTo3dPreview({{ aiModel, modelType, ultra }})
          }});
        }}
console.log(JSON.stringify(out));
"""
    _r = subprocess.run(["node", "--input-type=module"], input=_node_script,
                        capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert _r.returncode == 0, _r.stderr
    _combos = _json.loads(_r.stdout)
    _bad = [c for c in _combos if
           MS.credits_image_to_3d(c["aiModel"], c["modelType"], c["shouldTexture"],
                                  c["textureResolution"], ultra=c["ultra"]) != c["img"]
           or MS.credits_text_to_3d_preview(c["aiModel"], c["modelType"],
                                            ultra=c["ultra"]) != c["prev"]]
    assert not _bad, _bad[:5]
    ok(f"miroir CREDITS confronté par node : {len(_combos)} combinaisons, 0 divergence")

# helpers serveur mock-aware (P9 s'en servira ; ici on prouve le contrat)
settings.MESHY_MOCK = True
settings.MESHY_MOCK_SPEED = 0.01
MS._mock = None                      # repartir d'un simulateur neuf, vitesse test


async def _create_and_wait_ultra():
    tid = await MS.create_task("openapi/v1/image-to-3d", {
        "image_url": "data:image/png;base64,AAAA", "ai_model": "meshy-7",
        "should_texture": True, "ultra_mode": True})
    assert tid.startswith("mock-")
    for _ in range(500):
        t = await MS.get_task("openapi/v1/image-to-3d", tid)
        if t["status"] in MS.TERMINAL:
            return t
        await asyncio.sleep(0.02)
    else:
        raise AssertionError("tâche mock jamais terminale")


_final_task = asyncio.run(_create_and_wait_ultra())
assert _final_task["status"] == "SUCCEEDED" and _final_task["consumed_credits"] == 35
assert _final_task["model_urls"]["glb"].startswith(MS.MOCK_FILE_PREFIX)
ok("create_task/get_task serveur : mock-aware, crédits ultra comptés")
settings.MESHY_MOCK = True    # restaure : main() plus bas suppose le mock actif
settings.MESHY_MOCK_SPEED = 0.02   # restaure : valeur d'origine (env, ligne ~24)
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
        if not settings.MESHY_API_KEY.strip():
            raise RuntimeError("meshy: MESHY_API_KEY absente — Réglages")
        try:
            async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as c:
                r = await c.post(f"{MESHY_API}/{base}", headers=_headers(), json=payload)
            code = r.status_code
            try:
                res = r.json()
            except ValueError:
                res = {"message": r.text[:400]}
        except httpx.HTTPError as e:
            raise RuntimeError(f"meshy: {type(e).__name__}: {e}") from e
    if code not in (200, 202) or not isinstance(res, dict) or not res.get("result"):
        raise RuntimeError(f"meshy: {_meshy_detail(code, res)}")
    return str(res["result"])


async def get_task(base: str, task_id: str) -> dict:
    """État d'une tâche Meshy côté serveur — mock-aware. RuntimeError littérale
    sur code HTTP hors 200 (la tâche de fond de P9 la journalise telle quelle)."""
    if base not in ALLOWED_BASES:
        raise RuntimeError(f"meshy: chemin non autorisé {base!r}")
    if not _TASK_ID_RE.match(str(task_id)):
        raise RuntimeError(f"meshy: identifiant de tâche invalide {task_id!r}")
    if mock_enabled():
        code, res = get_mock().get(task_id)
    else:
        if not settings.MESHY_API_KEY.strip():
            raise RuntimeError("meshy: MESHY_API_KEY absente — Réglages")
        try:
            async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as c:
                r = await c.get(f"{MESHY_API}/{base}/{task_id}", headers=_headers())
            code = r.status_code
            try:
                res = r.json()
            except ValueError:
                res = {"message": r.text[:400]}
        except httpx.HTTPError as e:
            raise RuntimeError(f"meshy: {type(e).__name__}: {e}") from e
    if code != 200 or not isinstance(res, dict):
        raise RuntimeError(f"meshy: {_meshy_detail(code, res)}")
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
> `MESH3D_ENGINES(fal) ⊆ asset3d_service.ENGINES`. **Résidus de re-revue REPRIS
> EN TÊTE DE TASK 4** : (a) l'assert d'isolation de la panne de prix doit
> prouver l'isolation avec une matière témoin PRÉSENTE (pas une boutique vide) ;
> (b) une panne de la boutique matières est SIGNALÉE (`materials_degraded` au
> message littéral), pas avalée ; (c) has_meshy piloté par les DEUX états
> (monkeypatch MESHY_MOCK False→True, assert False puis True), pas un miroir de
> l'expression. **Report à la Task 7** : l'écran doit avoir une branche pour
> `engines: []` + `degraded` renseigné (message affiché tel quel, pas un select
> vide muet). **Legs Task 4 pour l'écran** : le 413 (couche trop lourde) rejoint
> la famille des refus nommés (400/409/503/413 affichés tels quels) ; `run_id`
> du job est opaque mais COMPARABLE entre deux polls — s'il change, un autre
> onglet a relancé le nœud (le dire, plutôt qu'un flip silencieux d'état) ;
> `record_state` déclenche le rapatriement meshy3d (stockage DOUBLE voulu :
> filet de sécurité, le dossier nœud est rasé à chaque relance — rétention à
> arbitrer plus tard, hors 2b).

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Modify: `frontend/cardforge/js/mod-forge3d.js` (bloc miroir seul ici)
- Modify: `backend/app/services/pricing.py`
- Test: `backend/tests/test_cards_forge3d.py`

- [x] **Step 1 : tests en RED**

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
    # moteur inconnu -> défaut meshy-7 ; ET l'ultra ne survit pas à la
    # réparation (amendement contrôleur) : un drapeau PAYANT ne peut pas
    # naître du repli sur le défaut, l'utilisateur n'a pas nommé ce moteur.
    assert n["m2"]["engine"] == "meshy-7"
    assert n["m2"]["ultra"] is False
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


def test_info_publie_moteurs_prix_matieres_et_bornes(monkeypatch):
    """7 moteurs, prix fal en $ depuis pricing, crédits Meshy depuis la grille
    partagée (+ conversion $ directionnelle meshy_credit_usd), matières de la
    boutique, bornes matière/transform — l'écran ne recopie RIEN."""
    from app.config import settings
    from app.services import pricing, meshy_service as MS, material_store
    from app.services import asset3d_service as A3D
    from app.services.cards import forge3d as F9
    did = _deck("Info 2b")
    mat = material_store.create_material(name="essai-info")
    try:
        info = _api("GET", f"/api/cards/{did}/forge3d/info").json()
        eng = {e["id"]: e for e in info["mesh3d"]["engines"]}
        assert list(eng) == ["tripo", "hunyuan", "trellis", "rodin", "triposr",
                             "meshy-6", "meshy-7"]
        # roster lock (M4) : les moteurs fal du miroir 2b sont un
        # SOUS-ENSEMBLE du registre asset3d_service — jamais un moteur que
        # le job (Task 4) ne saurait pas router.
        assert {e["id"] for e in F9.MESH3D_ENGINES if e["provider"] == "fal"} \
            <= set(A3D.ENGINES)
        p = pricing.load()
        attendu = pricing.estimate({"kind": "asset3d", "engine": "tripo"}, p)["total_usd"]
        assert eng["tripo"]["provider"] == "fal" and eng["tripo"]["price_usd"] == attendu
        assert eng["meshy-7"]["provider"] == "meshy"
        assert eng["meshy-7"]["credits"] == MS.credits_image_to_3d("meshy-7", "standard", True, "2k") == 30
        assert eng["meshy-7"]["ultra_extra_credits"] == 5
        assert eng["meshy-6"]["ultra_extra_credits"] == 0
        assert eng["meshy-7"]["price_usd"] == round(30 * float(p["meshy_credit_usd"]), 4)
        assert info["mesh3d"]["default_engine"] == "meshy-7"
        assert info["mesh3d"]["degraded"] is None
        assert info["materials_degraded"] is None
        # has_meshy / has_fal : CONDUITS par leurs deux états (résidu de
        # re-revue Task 3). L'ancien miroir `== (settings.has_meshy or
        # bool(settings.MESHY_MOCK))` recopiait l'expression de
        # l'implémentation : VACUEUX dès que les deux côtés valaient False —
        # un `has_meshy: False` en dur l'aurait passé. Ici on force chaque
        # état et on lit le contrat, jamais la formule.
        monkeypatch.setattr(settings, "MESHY_API_KEY", "")
        monkeypatch.setattr(settings, "MESHY_MOCK", False)
        i0 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i0["has_meshy"] is False and i0["meshy_mock"] is False
        monkeypatch.setattr(settings, "MESHY_MOCK", True)     # simulateur seul
        i1 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i1["has_meshy"] is True and i1["meshy_mock"] is True
        monkeypatch.setattr(settings, "MESHY_MOCK", False)
        monkeypatch.setattr(settings, "MESHY_API_KEY", "cle-de-test")  # clé seule
        i2 = _api("GET", f"/api/cards/{did}/forge3d/info").json()["mesh3d"]
        assert i2["has_meshy"] is True and i2["meshy_mock"] is False
        monkeypatch.setattr(settings, "FAL_KEY", "")
        assert _api("GET", f"/api/cards/{did}/forge3d/info"
                    ).json()["mesh3d"]["has_fal"] is False
        monkeypatch.setattr(settings, "FAL_KEY", "cle-de-test")
        assert _api("GET", f"/api/cards/{did}/forge3d/info"
                    ).json()["mesh3d"]["has_fal"] is True
        monkeypatch.undo()      # les réglages redeviennent ceux du runtime
        # la boutique n'est plus vide (M3) : la matière créée voyage telle
        # quelle, et CHAQUE entrée n'expose que id/name — jamais les maps.
        assert isinstance(info["materials"], list)
        assert all(set(m.keys()) == {"id", "name"} for m in info["materials"])
        assert {"id": mat["id"], "name": "essai-info"} in info["materials"]
        # bornes matière/transform, épinglées littéralement (M6)
        assert info["material_limits"]["tile_mm"] == [10.0, 200.0]
        assert info["material_limits"]["finishes"] == ["aucune", "argent", "dorure"]
        assert info["transform_limits"]["xy_mm"] == [-100.0, 100.0]
        assert info["transform_limits"]["z_mm"] == [0.0, 10.0]
        assert info["transform_limits"]["rot_deg"] == [-180.0, 180.0]
        assert info["transform_limits"]["scale"] == [0.1, 4.0]
    finally:
        material_store.delete_material(mat["id"])
```

Run : run-tests -Filter cards_forge3d → FAIL.

- [x] **Step 2 : pricing.py**

Dans `DEFAULTS`, sous `rembg_api_usd` :
```python
    "meshy_credit_usd": 0.02,         # valeur $ directionnelle d'un crédit Meshy
                                      # (~plan Pro 1000 cr/mois) ; éditable comme
                                      # le reste — Meshy facture en crédits, la
                                      # vérité comptable est consumed_credits
```

- [x] **Step 3 : forge3d.py — vocabulaire + bornes + clean_graph**

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
# littéraux PARTAGÉS entre le prix de /info (_engine_table) et le payload du
# job (Task 4) — une seule vérité, jamais recopiés d'un côté à l'autre.
MESH3D_TEXTURE_RES = "2k"
MESH3D_SHOULD_TEXTURE = True
MESH3D_UPLOAD_PX = 2048               # côté long envoyé aux moteurs — un moteur
                                      # texture en 2k, le 300 DPI n'y gagne rien
MESH3D_POLL_S = 4.0                   # période de poll Meshy (0.05 en mock)
MESH3D_TIMEOUT_S = 1800.0             # 30 min — après quoi le job échoue NOMMÉ
MESH3D_CLOSED_TRI_MAX = 1_500_000     # au-delà : closed=None (« non mesuré »),
                                      # le gate STL refuse MOTIVÉ (borne mémoire)
MAX_EXT_GLB_BYTES = 64 * 1024 * 1024  # même chiffre que MAX_LAYER_BYTES

MATERIAL_TILE_MM = (10.0, 200.0)
# UNE seule vérité pour les finitions : les recettes vivent dans le module
# scène, l'écran en reçoit la liste par /info. « aucune » est le seul mot que
# ce fichier ajoute (l'absence de finition n'est pas une recette).
MATERIAL_FINISHES = ("aucune",) + HOLO_KINDS
TRANSFORM_XY_MM = (-100.0, 100.0)
TRANSFORM_Z_MM = (0.0, 10.0)
TRANSFORM_ROT_DEG = (-180.0, 180.0)
TRANSFORM_SCALE = (0.1, 4.0)
```

Branches de `clean_graph` (dans la boucle existante, style des branches 2a) :
```python
        elif n["kind"] == "mesh3d":
            eng = str(n.get("engine") or "")
            connu = eng in {e["id"] for e in MESH3D_ENGINES}
            node["engine"] = eng if connu else MESH3D_DEFAULT_ENGINE
            node["texture_prompt"] = str(n.get("texture_prompt") or "").strip()[:MESH3D_PROMPT_MAX]
            # amendement du contrôleur (plan 2b) : un moteur inconnu est
            # réparé vers le défaut, mais un drapeau PAYANT ne survit jamais
            # à une réparation — l'utilisateur n'a pas consenti à l'ultra
            # d'un moteur qu'il n'a pas nommé.
            # M8 : UNE SEULE SOURCE D'ÉLIGIBILITÉ À L'ULTRA — la grille
            # partagée de `meshy_service`, celle-là même qui FACTURE le
            # surcoût et que `/info` publie en `ultra_extra_credits`. L'ancien
            # `== "meshy-7"` recopiait ici une règle de tarification : le jour
            # où un moteur de plus le propose, le devis l'annoncerait et le
            # nettoyage l'effacerait, chacun sûr d'avoir raison.
            node["ultra"] = (bool(n.get("ultra")) and connu
                             and MS._ultra_extra(node["engine"], True) > 0)
        elif n["kind"] == "material":
            mid = str(n.get("mat") or "")
            node["mat"] = mid if material_store.is_valid_mid(mid) else None
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

- [x] **Step 4 : `/info` enrichi**

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
            cr = MS.credits_image_to_3d(e["id"], "standard", MESH3D_SHOULD_TEXTURE,
                                        MESH3D_TEXTURE_RES)
            row["credits"] = cr
            # M1 (revue) : la grille PARTAGÉE est la seule source du surcoût
            # ultra — jamais recopiée en dur ici (la docstring promet « jamais
            # recopiés », l'ancien `5 if ... else 0` la trahissait).
            row["ultra_extra_credits"] = MS._ultra_extra(e["id"], True)
            row["price_usd"] = round(cr * float(p.get("meshy_credit_usd", 0.02)), 4)
        rows.append(row)
    return rows
```
La réponse de `get_info` gagne :
```python
            "mesh3d": {
                "engines": engines,
                "default_engine": MESH3D_DEFAULT_ENGINE,
                "has_fal": bool(settings.FAL_KEY),
                "has_meshy": settings.has_meshy or bool(settings.MESHY_MOCK),
                "meshy_mock": bool(settings.MESHY_MOCK),
                "prompt_max": MESH3D_PROMPT_MAX,
                "degraded": mesh3d_degraded,
            },
            "materials": [{"id": m["id"], "name": m["name"]}
                          for m in materials_raw],
            "materials_degraded": materials_degraded,
            "material_limits": {"tile_mm": list(MATERIAL_TILE_MM),
                                "finishes": list(MATERIAL_FINISHES)},
            "transform_limits": {"xy_mm": list(TRANSFORM_XY_MM),
                                 "z_mm": list(TRANSFORM_Z_MM),
                                 "rot_deg": list(TRANSFORM_ROT_DEG),
                                 "scale": list(TRANSFORM_SCALE)}}
```
(`settings` est déjà importé ou s'importe de `app.config` selon l'existant du fichier ;
`list_materials()` ne lève pas sur boutique vide — elle rend `[]`.)

- [x] **Step 5 : mettre à jour le test de parité 2a**

Le test existant `test_le_vocabulaire_du_graphe_est_identique_des_deux_cotes` affirme
l'ordre 2a (`["layer", "plane", "relief", "assemble", "artifact"]`) : le NOUVEAU test
le remplace — supprimer l'ancien assert d'ordre (garder le reste du test s'il vérifie
autre chose, sinon retirer l'ancien test au profit du nouveau, une seule source).

- [x] **Step 6 : GREEN + commit**

Run : run-tests -Filter cards_forge3d → PASS ; lint --module forge3d → 0.
```bash
git add backend/app/services/cards/forge3d.py frontend/cardforge/js/mod-forge3d.js backend/app/services/pricing.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): vocabulaire 2b (mesh3d/material/transform) en miroir, clean_graph borne, /info sert moteurs+prix+matieres"
```

---

### Task 4: Le job `mesh3d` — routes, runner fal, runner Meshy, `closed` mesuré UNE fois

> **LIVRÉE (a5578da) — amendements actés, qui PRÉVALENT sur les extraits
> ci-dessous. FAUTE DU PLAN corrigée par l'implémenteur :** le `_NID_RE` du plan
> (`^[A-Za-z0-9._-]{1,24}$`) **acceptait `..`** — et `clean_graph` normalise les
> ids vers ce même charset, donc un nœud nommé `..` survivait au nettoyage ;
> `_node_dir(did, "..")` remontait sur `forge3d/` et la réinitialisation
> (`shutil.rmtree`) aurait DÉTRUIT tous les exports du deck en un POST. Régle
> livrée : `^(?!\.+$)[A-Za-z0-9._-]{1,24}$` + DOUBLE garde de confinement dans
> `_node_dir` (doctrine `deck_dir` du contrat) — les deux prouvés par mutation.
> **Autres amendements :** (1) `BackgroundTasks` retenu (sondé empiriquement :
> `asyncio.create_task` meurt avec la boucle du client de test) ; le task ne
> démarrant qu'APRÈS l'envoi de la réponse, la route pose un MARQUEUR de
> lancement dans le registre (expiration `MESH3D_LAUNCH_GRACE_S`) que le runner
> remplace — sinon un poll rapide déclarait l'orphelin à tort ; (2)
> `glb_scene_mesh` accepte les primitives NON indexées (dessin légal glTF 2.0 —
> le tiny_glb du mock en est ; les assertions du plan étaient insatisfiables
> sinon) en synthétisant `range(count)` ; (3) `glb_triangle_estimate` décide la
> borne `MESH3D_CLOSED_TRI_MAX` sur les MÉTADONNÉES d'accesseurs AVANT toute
> allocation ; (4) un GLB imparsable/trop lourd DÉGRADE (`closed: None` +
> `closed_note`, job `served`) au lieu d'échouer — le binaire est payé ; (5) le
> 409 de concurrence EST testé (neutraliser le runner tient la fenêtre ouverte) ;
> (6) GET rend le job à plat, POST rend `{"job": …}` (asymétrie des tests du
> plan, documentée). **Revue qualité (2e passe) :** le dessin du marqueur de
> grâce portait DEUX modes de défaillance, pas un — le faux-orphelin (couvert)
> ET le DOUBLE LANCEMENT PAYANT : garde 409 non atomique (4 points de
> suspension entre test et pose du marqueur) + un runner rassis (envoi de
> réponse retardé au-delà de la grâce) qui écrase le job.json d'une relance.
> Correctifs actés : pose du marqueur ATOMIQUE (zéro await) avec déroulage sur
> refus, clôture par `run_id` (le runner se tait s'il a été remplacé), pop du
> registre conditionnel à sa propre tâche ; + retries bornés du poll d'un job
> PAYÉ (`MESH3D_POLL_RETRIES`), journalisation `record_created/record_state`
> de la tâche Meshy (récupération via le 3D Studio), `mesh_url` fal persistée
> avant download, bornes de taille TESTÉES par rétrécissement de constante.
> Étapes cochées.

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Modify: `backend/app/services/cards/forge3d_scene.py` (extraction GLB→mesh)
- Test: `backend/tests/test_cards_forge3d.py`

Modèle : job de fond par nœud (patron `/assets/3d` : pré-enregistrer, travailler en
tâche de fond, poller), MAIS l'état durable est `nodes/{nid}/job.json` (deck-local,
legs 2) — pas un JobRecord global. Un registre mémoire `{(did, nid): task}` détecte
les jobs orphelins après redémarrage. Relancer un nœud RÉINITIALISE son dossier
(l'aperçu périmé ne survit pas — legs 4 appliqué aux nœuds).

- [x] **Step 1 : tests en RED**

```python
def _graphe_mesh3d(engine="meshy-7", ultra=False):
    return {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": engine,
         "texture_prompt": "pierre gravee", "ultra": ultra},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}


def _exporter_couches(did):
    """Les couches de la phase 1, MÊME forme d'envoi que les tests voisins."""
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
    from app.services import meshy_service as MS, pricing
    from app.services.storage import init_db
    # le journal partagé (I2) vit en base : les tests n'exécutent pas le
    # `lifespan` de l'application, donc les tables n'existent pas encore ici.
    asyncio.run(init_db())
    avant = (cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED)
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
        # le prix est ANNONCÉ avant, depuis la grille partagée et pricing.json
        # (jamais un littéral recopié) : 30 cr + 5 d'ultra sur meshy-7.
        cr = MS.credits_image_to_3d("meshy-7", "standard", True, "2k", ultra=True)
        assert cr == 35
        usd = round(cr * float(pricing.load()["meshy_credit_usd"]), 4)
        assert lance["job"]["price"] == {"credits": cr, "usd": usd}
        # la provenance voyage avec le job : LA couche source, son empreinte
        assert lance["job"]["source"]["file"] == "illustration_c01_front.png"

        job = _attendre_job(did, "m1")
        assert job["status"] == "served", job
        assert job["engine"] == "meshy-7" and job["consumed_credits"] == 35
        assert job["closed"] is False            # le tiny_glb du mock est un triangle
        base = _dossier_noeud(did, "m1")
        assert (base / "model.glb").is_file()
        assert (base / "preview.png").is_file()
        assert (base / "job.json").is_file()
        # les octets rapatriés sont bien ceux du simulateur, pas un fichier vide
        assert (base / "model.glb").read_bytes() == MS.tiny_glb()
        assert job["files"]["glb"] == "model.glb"
        assert job["files"]["textures"] == ["textures/0_base_color.png"]
        assert (base / "textures" / "0_base_color.png").is_file()
        assert job["task_id"], job          # l'id du fournisseur est tracé
        # l'empreinte annoncée est celle de la couche RÉELLEMENT lue — et la
        # vignette RÉELLEMENT envoyée a la sienne (M1 : deux questions
        # distinctes, « de quelle couche » et « qu'a vu le moteur »).
        from app.services.cards.contract import deck_dir
        src = deck_dir(did) / "forge3d" / "illustration_c01_front.png"
        assert job["source"]["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
        assert job["source"]["bytes"] == src.stat().st_size
        envoi = (base / "upload_src.png").read_bytes()
        assert job["source"]["upload_sha256"] == hashlib.sha256(envoi).hexdigest()
        assert job["source"]["upload_bytes"] == len(envoi)

        # I2 : la tâche PAYÉE est entrée au journal PARTAGÉ — sans quoi
        # `repatriate` refuse son id et `expiring_soon` ne prévient personne
        # avant que les URL Meshy n'expirent.
        rows = {r["id"]: r for r in asyncio.run(MS.list_tasks())}
        assert job["task_id"] in rows, sorted(rows)
        # la CRÉATION (seule à écrire le payload) et l'ÉTAT TERMINAL (seul à
        # écrire les crédits débités) sont journalisés tous les deux — l'un
        # sans l'autre laisserait le journal muet sur la moitié de l'histoire.
        assert rows[job["task_id"]]["payload"]["ai_model"] == "meshy-7"
        assert rows[job["task_id"]]["payload"]["ultra_mode"] is True
        assert rows[job["task_id"]]["status"] == "SUCCEEDED"
        assert rows[job["task_id"]]["consumed_credits"] == 35

        # relancer = dossier RÉINITIALISÉ (legs 4) : un vestige de la passe
        # précédente ne doit pas survivre au nouveau job.
        (base / "vestige.txt").write_text("passe precedente", encoding="utf-8")
        r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r2.status_code == 200, r2.text
        job2 = _attendre_job(did, "m1")
        assert job2["status"] == "served", job2
        assert not (base / "vestige.txt").exists(), "le dossier n'a pas ete reinitialise"
        # ...et la relance a bien une IDENTITÉ neuve (clôture C2)
        assert job2["run_id"] and job2["run_id"] != job["run_id"]
    finally:
        cfg.MESHY_MOCK, cfg.MESHY_MOCK_SPEED = avant
        MS._mock = None


def test_le_job_fal_passe_par_les_coutures_et_le_glb_ferme_est_su():
    """Moteur fal monkeypatché de bout en bout : upload -> run -> download.
    Le « GLB téléchargé » est un relief FERMÉ écrit par notre writer ->
    closed True mesuré une fois, prix $ = pricing."""
    from pathlib import Path
    from app.services import asset3d_service as A3D
    from app.services import pricing
    glb_connu = _glb_ferme()

    async def faux_upload(path):
        assert Path(path).is_file()
        return "https://fal.test/src.png"

    async def faux_run(engine, args):
        assert engine == "tripo" and args["image_url"] == "https://fal.test/src.png"
        return {"mesh_url": "https://fal.test/model.glb",
                "format_urls": {}, "texture_urls": [], "preview_url": None}

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
        # le GLB livré est EXACTEMENT celui que la couture a téléchargé
        assert (_dossier_noeud(did, "m1") / "model.glb").read_bytes() == glb_connu
        # I3 : l'URL de l'artefact PAYÉ est PERSISTÉE, pas jetée après usage —
        # c'est le seul lien vers ce qu'on vient d'acheter si le disque casse.
        assert job["mesh_url"] == "https://fal.test/model.glb", job
        disque = json.loads(
            (_dossier_noeud(did, "m1") / "job.json").read_text(encoding="utf-8"))
        assert disque["mesh_url"] == "https://fal.test/model.glb"
    finally:
        A3D._upload, A3D._run_engine, A3D._download = vrai


def test_les_refus_du_job_mesh3d_sont_nommes(monkeypatch):
    """Chaque refus a SON motif : couches absentes (409), nœud hors graphe
    (400), couche trop lourde (413), clé de moteur manquante (503), job
    inexistant (404)."""
    from app.config import settings as cfg
    from app.services.cards import forge3d as F9
    did = _deck("Refus mesh3d")
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1", json={"graph": g, "card": 0})
    assert r.status_code == 409 and "couches" in r.json()["detail"]
    _exporter_couches(did)
    r2 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/zzz", json={"graph": g, "card": 0})
    assert r2.status_code == 400
    # M1 : la borne de POIDS de la couche source est vérifiée sur un `stat`,
    # AVANT tout travail — la constante de production (64 Mo) n'est pas
    # testable à taille réelle, on l'abaisse (idiome du fichier).
    monkeypatch.setattr(F9, "MAX_LAYER_BYTES", 10)
    rl = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
              json={"graph": g, "card": 0})
    assert rl.status_code == 413, rl.text
    assert "trop lourde" in rl.json()["detail"]
    monkeypatch.undo()
    avant = (cfg.MESHY_API_KEY, cfg.MESHY_MOCK)
    cfg.MESHY_API_KEY, cfg.MESHY_MOCK = "", False
    try:
        r3 = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/m1",
                  json={"graph": g, "card": 0})
        assert r3.status_code == 503 and "MESHY_API_KEY" in r3.json()["detail"]
    finally:
        cfg.MESHY_API_KEY, cfg.MESHY_MOCK = avant
    r4 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r4.status_code == 404
    # aucun refus n'a laissé de dossier derrière lui
    assert not _dossier_noeud(did, "m1").exists()

    # TRAVERSÉE (constatée en auto-revue) : un nid qui n'est QUE des points
    # n'est pas un NOM de dossier, c'est un SAUT — `nodes/..` désigne
    # `forge3d/`, que la réinitialisation du nœud efface au rmtree. Un seul
    # lancement sur un nœud nommé `..` détruisait toutes les couches du deck.
    from app.services.cards.contract import deck_dir
    for mechant in ("..", ".", "...", "a" * 25):
        assert not F9._NID_RE.match(mechant), mechant
    # le CONFINEMENT, par-dessus le motif (doctrine deck_dir : ceinture et
    # bretelles) : les deux noms qui sont vraiment des sauts de chemin.
    for saut in ("..", "."):
        with pytest.raises(Exception):
            F9._node_dir(did, saut, create=True)
    for mechant in ("..", ".", "...", "a" * 25):
        g2 = json.loads(json.dumps(g))
        g2["nodes"][1]["id"] = mechant
        g2["edges"] = [{"from": "s1", "to": mechant}]
        chemin = mechant.replace(".", "%2e")
        rr = _api("POST", f"/api/cards/{did}/forge3d/mesh3d/{chemin}",
                  json={"graph": g2, "card": 0})
        assert rr.status_code in (400, 404), (mechant, rr.status_code, rr.text)
    # ...et les couches exportées du deck sont TOUJOURS là
    assert (deck_dir(did) / "forge3d" / "illustration_c01_front.png").is_file()


def test_un_job_running_orphelin_apres_redemarrage_est_avoue(monkeypatch):
    """Le registre mémoire ne survit pas au processus : un `running` sur
    disque sans tâche vivante est un ORPHELIN — avoué, jamais laissé tourner
    en rond dans l'écran."""
    import time as _t
    from app.services.cards import forge3d as F9
    did = _deck("Orphelin")
    base = _dossier_noeud(did, "m1")
    base.mkdir(parents=True, exist_ok=True)
    (base / "job.json").write_text(json.dumps(
        {"schema": "card-3d/mesh3d-job@1", "node": "m1", "engine": "tripo",
         "run_id": "d" * 32, "status": "running", "progress": 50}),
        encoding="utf-8")

    # L'AUTRE moitié du garde-fou, celle qui ne doit PAS se déclencher : tant
    # que le marqueur de lancement est frais (la tâche de fond n'a pas encore
    # démarré — le serveur ne la lance qu'après l'envoi de la réponse), le job
    # est VIVANT et le poll doit le voir « running », pas « failed ».
    F9._MESH3D_RUNNING[(did, "m1")] = _t.monotonic()
    try:
        r0 = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
        assert r0.status_code == 200 and r0.json()["status"] == "running", r0.text
        # ...et ce marqueur PÉRIME : sans péremption, un lancement dont la
        # tâche n'est jamais partie bloquerait le nœud jusqu'au redémarrage.
        F9._MESH3D_RUNNING[(did, "m1")] = _t.monotonic() - F9.MESH3D_LAUNCH_GRACE_S - 1
        assert F9._mesh3d_vivant(did, "m1") is False
    finally:
        F9._MESH3D_RUNNING.pop((did, "m1"), None)

    r = _api("GET", f"/api/cards/{did}/forge3d/mesh3d/m1")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "interrompu" in r.json()["error"]
    # le motif dit CE QU'ON A CONSTATÉ (aucune tâche vivante), pas une cause
    # devinée : un redémarrage n'est qu'UNE des façons de perdre la tâche.
    assert r.json()["error"] == ("interrompu (aucune tache vivante) - "
                                 "relancer le noeud")
    # l'aveu est PERSISTÉ, pas seulement servi : un second appel le relit tel
    # quel (sinon l'écran verrait « running » à chaque rechargement).
    disque = json.loads((base / "job.json").read_text(encoding="utf-8"))
    assert disque["status"] == "failed" and "interrompu" in disque["error"]

    # ...et il est DÉFINITIF : le run_id est invalidé, donc un runner en retard
    # (envoi de réponse resté coincé au-delà de la péremption du marqueur) qui
    # démarrerait enfin ne peut PLUS contredire ce que l'écran vient de
    # montrer — sa clôture échoue et il abandonne SANS DÉPENSER.
    assert r.json()["run_id"] is None
    assert disque["run_id"] is None
    from app.services import asset3d_service as A3D

    async def jamais(*a, **k):
        raise AssertionError("un runner en retard ne doit RIEN depenser")

    monkeypatch.setattr(A3D, "_upload", jamais)
    monkeypatch.setattr(A3D, "_run_engine", jamais)
    fige = (base / "job.json").read_bytes()
    asyncio.run(F9._run_mesh3d(
        did, "m1", {"id": "m1", "kind": "mesh3d", "engine": "tripo",
                    "texture_prompt": "", "ultra": False}, "fal",
        {"role": "illustration", "side": "front",
         "file": "illustration_c01_front.png", "sha256": None}, "d" * 32))
    assert (base / "job.json").read_bytes() == fige, "l'aveu a ete contredit"
```

NOTE au rédacteur des tests : `OUTPUTS` = la racine outputs des tests (le fichier de
test a déjà sa manière d'atteindre `outputs/decks/{did}` pour relire les fichiers —
réutiliser EXACTEMENT le même mécanisme que les tests 2a de `build3d` ; la ligne
factice `ndir…x-noop` du plan d'origine est retirée de l'extrait, comme du test livré).
Le test 409-concurrent n'est PAS écrit : le mock à vitesse 0.01 finit trop vite pour
le fenêtrer de façon fiable — la garde est couverte par relecture de code en revue.

Run : run-tests -Filter cards_forge3d → FAIL (routes absentes).

- [x] **Step 2 : `forge3d_scene.py` — lire un GLB en mesh**

```python
def read_glb(data: bytes) -> tuple[dict, bytes]:
    """Document JSON + chunk BIN d'un GLB. ValueError NOMMÉE sinon (la route
    la transforme en refus motivé, jamais un 500).

    Le chunk BIN est FACULTATIF (un GLB peut n'avoir que du JSON) : absent,
    on rend b"" plutôt que de lever — c'est `glb_scene_mesh` qui décidera si
    l'absence de géométrie est une faute, avec SON message."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("pas un GLB (octets attendus)")
    data = bytes(data)
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("pas un GLB (magie glTF absente)")
    doc_len = struct.unpack("<I", data[12:16])[0]
    if 20 + doc_len > len(data):
        raise ValueError("GLB tronqué (chunk JSON)")
    try:
        doc = json.loads(data[20:20 + doc_len].decode("utf-8").rstrip("\x00 "))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"GLB au document JSON illisible ({e})") from e
    if not isinstance(doc, dict):
        raise ValueError("GLB au document JSON qui n'est pas un objet")
    off = 20 + doc_len
    binv = b""
    if off + 8 <= len(data):
        blen = struct.unpack("<I", data[off:off + 4])[0]
        binv = data[off + 8:off + 8 + blen]
    return doc, binv


def _accessor_floats(doc: dict, binv: bytes, idx: int) -> list[float]:
    acc, off = _accessor_view(doc, idx)
    # LE COUPLAGE, RENDU EXPLICITE (résidu de la re-revue Task 6) : ce lecteur
    # ne décode QUE du float32 (5126). Un accesseur quantifié
    # (KHR_mesh_quantization : 5120/5121/5122/5123) relu ici en flottants
    # rendrait des positions ABSURDES sans lever — un GLB parfaitement valide
    # qui mesure et imprime la mauvaise chose. C'est LA raison pour laquelle
    # `_EXIG_CONNUES` n'accueille pas cette extension : la garde et l'allowlist
    # disent maintenant la même chose, chacune à son étage.
    ct = acc.get("componentType") if isinstance(acc, dict) else None
    if ct != 5126:
        raise ValueError(f"accesseur {idx!r} non float32 (componentType "
                         f"{ct!r}) — quantization non fusionnable")
    try:
        n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
        return list(struct.unpack_from("<" + "f" * (int(acc["count"]) * n),
                                       binv, off))
    except (KeyError, TypeError, ValueError, struct.error) as e:
        raise ValueError(f"accesseur flottant {idx!r} illisible ({e})") from e


def _accessor_indices(doc: dict, binv: bytes, idx: int) -> list[int]:
    acc, off = _accessor_view(doc, idx)
    try:
        fmt = {5121: "B", 5123: "H", 5125: "I"}[acc["componentType"]]
        return list(struct.unpack_from("<" + fmt * int(acc["count"]), binv, off))
    except (KeyError, TypeError, ValueError, struct.error) as e:
        raise ValueError(f"accesseur d'indices {idx!r} illisible ({e})") from e


def glb_scene_mesh(data: bytes, world: bool = False) -> dict:
    """Concatène POSITION+indices des primitives triangles d'un GLB en un mesh
    {positions, indices} pour `mesh_measures`/STL. ValueError nommée si rien
    n'est mesurable.

    `world=False` (défaut, contrat de la tâche 4) : TOUTES les primitives du
    document, positions BRUTES, transforms de nœuds IGNORÉS. C'est ce qu'il
    faut pour une mesure de TOPOLOGIE — `closed` ne dépend d'aucun transform,
    et un mesh que rien n'instancie compte quand même comme géométrie livrée.

    `world=True` (tâche 6) : la scène TELLE QU'ELLE SERA VUE — descente du
    graphe de nœuds, matrices COMPOSÉES, positions dans le repère de la scène.
    C'est ce qu'il faut pour PLACER (fit) et pour IMPRIMER (STL), les deux
    devant montrer la même chose que le GLB. Repli automatique sur le
    balayage brut si AUCUN nœud n'instancie de mesh (le GLB du simulateur
    Meshy, entre autres) : une géométrie orpheline vaut mieux que rien.

    Une primitive SANS `indices` n'est PAS une faute : glTF 2.0 la définit
    comme un tirage NON INDEXÉ, ses sommets se suivant dans l'ordre. Le GLB du
    simulateur Meshy est exactement cela (un triangle nu) — la refuser ferait
    échouer une mesure parfaitement calculable."""
    doc, binv = read_glb(data)
    couples: list = []
    if world:
        meshes = doc.get("meshes")
        meshes = meshes if isinstance(meshes, list) else []
        for mi, monde in _meshes_du_monde(doc):
            if 0 <= mi < len(meshes):
                couples.extend((prim, monde) for prim in _mesh_prims(meshes[mi]))
    if not couples:
        couples = [(prim, None) for prim in _triangle_prims(doc)]
    positions: list[float] = []
    indices: list[int] = []
    for prim, monde in couples:
        attrs = prim.get("attributes")
        if not isinstance(attrs, dict) or "POSITION" not in attrs:
            raise ValueError("primitive triangle sans POSITION")
        base = len(positions) // 3
        pts = _accessor_floats(doc, binv, attrs["POSITION"])
        positions += pts if monde is None else _applique_mat4(pts, monde)
        if prim.get("indices") is None:
            indices += list(range(base, base + len(pts) // 3))
        else:
            indices += [base + i
                        for i in _accessor_indices(doc, binv, prim["indices"])]
    if not indices:
        raise ValueError("aucune primitive triangle dans le GLB")
    # dernier garde-fou AVANT que `mesh_measures` n'indexe : un indice hors
    # bornes (GLB de moteur malformé) y lèverait un IndexError nu — donc un
    # 500 chez l'appelant, exactement ce que ce module s'interdit.
    if (max(indices) + 1) * 3 > len(positions):
        raise ValueError("GLB aux indices hors bornes (maillage incohérent)")
    return {"positions": positions, "indices": indices}
```

- [x] **Step 3 : forge3d.py — les routes et les runners**

Registre + utilitaires (module-level) :
```python
_MESH3D_RUNNING: dict[tuple, "asyncio.Task"] = {}
_NID_RE = re.compile(r"^(?!\.+$)[A-Za-z0-9._-]{1,24}$")


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

- [x] **Step 4 : GREEN + commit**

Run : run-tests -Filter cards_forge3d → PASS (les jobs mock tournent en ~1 s).
```bash
git add backend/app/services/cards/forge3d.py backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): job mesh3d par noeud - 5 moteurs fal + meshy-6/7 directs (mock teste), closed mesure une fois, prix avant"
```

---

### Task 5: Matières, transform et finitions holographiques dans le writer

> **LIVRÉE (eb8fd47) — amendements actés, qui PRÉVALENT sur les extraits
> ci-dessous. FAUTE DU PLAN corrigée :** la texture d'anisotropie du plan
> mettait **B = 0** — or `KHR_materials_anisotropy` MULTIPLIE
> `anisotropyStrength` par le canal BLEU de la texture : à B=0 l'effet est
> invisiblement mort. Livré : **B = 255** (force pleine, modulée par le
> facteur 0.85). **Autres amendements :** (1) `tile_maps` vit dans
> `forge3d.py`, PAS dans le module scène — il dépend de `material_store`, la
> pureté du module scène (prouvée par test) prime sur le placement littéral ;
> `material_pngs`/`holo_finish`/`HOLO_KINDS` sont réexportés par forge3d.py ;
> (2) textures holo VECTORISÉES (bytearray par lignes + frombytes, octets
> IDENTIQUES prouvés : 4,49 s → ~1,1 s au 1024²) ; `out_px` borné 8..4096 ;
> `holo_finish` lève une ValueError nommée sur kind inconnu ; `tile_maps`
> refuse les dimensions non positives (jamais un ZeroDivisionError nu) ;
> (3) sortie 2a inchangée PROUVÉE à l'octet (module parallèle chargé depuis
> HEAD) ; TANGENT VEC4 aux bornes exactes. **2e passe de revue — DEUX FAUTES
> DU PLAN de plus, corrigées :** (a) le plan prescrivait `TANGENT w=+1` — or
> ces maillages ont les UV à V INVERSÉ : la règle glTF (et gltf_builder.py:485
> du dépôt lui-même) donne **w = −1** ; à +1 le champ anisotrope devenait
> RADIAL sur les diagonales (nœud papillon au lieu du brossé circulaire) et le
> vert des normal maps s'inversait ; (b) la sémantique finition×matière :
> glTF MULTIPLIE facteurs × textures — décision actée : **la finition SAUTE la
> map MR** de la matière (une feuille holo remplace la micro-surface mais
> laisse parler le relief/normal et l'occlusion). Aussi actés : lru_cache sur
> les deux PNG holo (octets immuables), dédup des textures par appel, cap
> out_px 2048 partout, resample explicites, `MATERIAL_FINISHES` dérivé de
> `HOLO_KINDS`, drapeau `uv_axis_aligned` sur quad/relief + ValueError nommée
> si anisotropie sur maillage sans le drapeau (garde pour la fusion Task 6),
> assert de pas de tuilage REFAIT en dimensions divisibles (l'ancien comparait
> des texels non correspondants). Étapes cochées. **RE-REVUE APPROUVÉE (8f62d31)** — résidus repliés en
> tête de Task 6 : borne du tpx dérivé (127 Mo d'intermédiaire possible depuis
> des entrées légales — même classe que la faute corrigée), commentaire du test
> de perpendicularité à rectifier (les DEUX asserts sont complémentaires, pas
> redondants — ne jamais supprimer le tw==-1), saut de MR conditionné à une
> recette PRÉSENTE (pas à la simple vérité du dict), et DÉCISION À CONSIGNER :
> le writer P9 n'émet TANGENT que sous anisotropie (une normal map seule laisse
> le client dériver — divergence assumée avec la doctrine gltf_builder, à
> justifier en commentaire).

**Files:**
- Modify: `backend/app/services/cards/forge3d_scene.py`
- Test: `backend/tests/test_cards_forge3d.py`

Sémantique (spec §5.2) : **baseColor = LA COUCHE**, la matière fournit
normal / metallicRoughness / ao / emissive. Les maps sont TUILÉES en PIL au pas
`tile_mm` sur une toile au ratio carte (déterministe, samplers CLAMP conservés —
aucun KHR_texture_transform à porter). Finitions §6.2bis-c : recettes argent/dorure,
`KHR_materials_iridescence` + `KHR_materials_clearcoat` (+ `KHR_materials_anisotropy`
si demandé, avec l'attribut TANGENT), le tout dans **`extensionsUsed` UNIQUEMENT**.

- [x] **Step 1 : tests en RED**

```python
def test_la_matiere_habille_l_element_et_les_maps_sont_cuites():
    """normal/MR/ao câblées ; le pack MR suit la convention glTF (G=rugosité,
    B=métal — doctrine pbr_service) ; relu dans les OCTETS du GLB."""
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

    # UNE FINITION SAUTE LE PACK MR (décision de revue Task 5). glTF MULTIPLIE
    # facteur x texture : garder les deux donnerait rugosité = 0,12 x G/255 —
    # une dorure posée sur une matière mate virerait au miroir noir, l'inverse
    # de ce que les deux réglages disent séparément. Sémantique : la feuille
    # holo REMPLACE la micro-surface, le RELIEF et l'OCCLUSION parlent encore.
    el2 = dict(el, name="sceau",
               finish=SC.holo_finish("dorure", aniso=False, out_px=64))
    doc2, _ = _read_glb(SC.write_scene_glb([el2], name="x", extras={}))
    m2 = doc2["materials"][0]
    pbr2 = m2["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" not in pbr2          # sauté, pas empilé
    assert pbr2["roughnessFactor"] == 0.12 and pbr2["metallicFactor"] == 1.0
    assert pbr2["baseColorFactor"] == [1.0, 0.84, 0.55, 1.0]
    assert "normalTexture" in m2 and "occlusionTexture" in m2   # relief + AO
    # la map MR n'est même plus EMBARQUÉE : rien ne la référencerait
    assert not any(im["name"].endswith("-mr") for im in doc2["images"])


def test_tile_maps_tuile_au_pas_physique_et_reste_deterministe(monkeypatch):
    """Une matière de la boutique, tuilée à tile_mm sur le ratio carte :
    mêmes octets à chaque appel ; le motif se répète au pas attendu.
    (tile_maps vit dans forge3d.py — décision de pureté du module scène.)

    COTES À DIVISION EXACTE (correctif de revue Task 5) : 64x128 mm, pas de
    32 mm, 256 px -> toile 128x256, tuile de 64 px. La première version
    comparait x et x + W//2 sur 183 px de large pour une tuile de 92 — DEUX
    TEXELS QUI NE SE CORRESPONDENT PAS, d'un texel près ; l'assertion ne
    tenait que parce que la map demandée (`roughness`) était UNIFORME. Ici on
    compare des TUILES ENTIÈRES, sur la map qui porte vraiment un motif."""
    from app.services import material_store as MSTORE
    from app.services.cards import forge3d as F9
    mat = MSTORE.create_material(name="essai-2b")
    try:
        tuile = Image.new("RGB", (64, 64), (10, 10, 10))
        tuile.paste(Image.new("RGB", (8, 8), (250, 250, 250)), (0, 0))
        MSTORE.save_maps(mat["id"], {"basecolor": tuile,
                                     "roughness": Image.new("L", (64, 64), 100)})
        a = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=32.0,
                         w_mm=64.0, h_mm=128.0, out_px=256)
        b = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=32.0,
                         w_mm=64.0, h_mm=128.0, out_px=256)
        assert a["basecolor"].tobytes() == b["basecolor"].tobytes()
        im = a["basecolor"]
        assert im.size == (128, 256)          # ratio carte, division exacte
        # 64 mm / 32 mm = 2 tuiles de 64 px : les tuiles voisines sont
        # identiques OCTET POUR OCTET, à l'horizontale comme à la verticale.
        coin = im.crop((0, 0, 64, 64)).tobytes()
        assert im.crop((64, 0, 128, 64)).tobytes() == coin
        assert im.crop((0, 64, 64, 128)).tobytes() == coin
        # ...et le motif est bien LÀ : sans ça les égalités ci-dessus seraient
        # vraies d'une toile unie (le piège exact de la version précédente).
        assert im.getpixel((2, 2))[0] > im.getpixel((40, 40))[0] + 100
        import pytest as _pt
        # matière introuvable -> ValueError nommée
        with _pt.raises(ValueError):
            F9.tile_maps("mat_inexistant00", ("basecolor",), 63.0, 63.0, 88.0)
        # cote nulle, négative, ou PAS NUMÉRIQUE : refus NOMMÉ — jamais un
        # ZeroDivisionError ni un TypeError nus (ce serait un 500).
        for cotes in ((0.0, 63.0, 88.0), (31.5, -1.0, 88.0),
                      (31.5, 63.0, 0.0), ("31,5", 63.0, 88.0)):
            with _pt.raises(ValueError):
                F9.tile_maps(mat["id"], ("basecolor",), *cotes)
        # out_px borné au MÊME plafond que les finitions (bornes symétriques)
        gros = F9.tile_maps(mat["id"], ("basecolor",), 32.0, 64.0, 64.0,
                            out_px=99999)["basecolor"]
        assert gros.size == (F9.HOLO_PX[1], F9.HOLO_PX[1]) == (2048, 2048)
        # LA BORNE DE L'ALLOCATION DÉRIVÉE (résidu de re-revue Task 5) : à
        # tile_mm=200 sur une carte mini de 31,75 mm, `W x tile_mm / w_mm`
        # visait 12 900 px de côté — une tuile de ~500 Mo en RGB, depuis des
        # entrées PARFAITEMENT LÉGALES (les deux sont dans les bornes
        # publiées). Le pixel rendu, lui, ne change pas d'un poil : une tuile
        # plus grande que la toile est collée UNE fois puis rognée. La seule
        # trace observable est donc la taille DEMANDÉE au rééchantillonnage —
        # espionnée ici, faute de quoi la borne ne serait qu'un commentaire.
        demandes = []
        vrai_resize = Image.Image.resize

        def resize_espion(self, size, *a, **kw):
            demandes.append(tuple(size))
            return vrai_resize(self, size, *a, **kw)

        monkeypatch.setattr(Image.Image, "resize", resize_espion)
        petit = F9.tile_maps(mat["id"], ("basecolor",), tile_mm=200.0,
                             w_mm=31.75, h_mm=44.45, out_px=256)["basecolor"]
        monkeypatch.undo()
        assert petit.size == (183, 256)      # ratio de la carte mini
        assert demandes, "aucun reechantillonnage observe"
        assert max(max(s) for s in demandes) <= max(petit.size), demandes
    finally:
        MSTORE.delete_material(mat["id"])


def test_les_finitions_holo_suivent_la_recette_et_restent_optionnelles():
    """§6.2bis-c : extensions dans extensionsUsed UNIQUEMENT, facteurs exacts,
    épaisseur en secteurs radiaux relue dans le canal G, TANGENT présent quand
    l'anisotropie est demandée, clearcoat posé. Déterminisme prouvé."""
    from app.services.cards import forge3d_scene as SC
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (220, 220, 220, 255)).save(png, "PNG")
    f1 = SC.holo_finish("argent", aniso=True, out_px=256)
    f2 = SC.holo_finish("argent", aniso=True, out_px=256)
    assert f1["iridescence"]["png"] == f2["iridescence"]["png"]   # mêmes octets
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
    # LE SIGNE DE w : -1, PAS +1 — relu dans les OCTETS, pas déduit du code.
    # Nos UV sont inversées en v (`quad_mesh`), donc dP/dv = -y quand
    # cross(N, T) = cross(+z, +x) = +y : la règle glTF (w = signe de
    # dot(cross(N,T), B)) donne -1, ce que `gltf_builder.py:485` calcule déjà
    # pour les maillages du dépôt. Avec +1 le champ anisotrope devient RADIAL
    # sur les diagonales et le vert d'une normal map s'inverse.
    bvt = doc["bufferViews"][acc["bufferView"]]
    offt = bvt.get("byteOffset", 0) + acc.get("byteOffset", 0)
    for k in range(acc["count"]):
        tx, ty, tz, tw = struct.unpack_from("<4f", binv, offt + k * 16)
        assert (tx, ty, tz) == (1.0, 0.0, 0.0), (k, tx, ty, tz)
        assert tw == -1.0, (k, tw)
    assert acc["min"][3] == -1.0 and acc["max"][3] == -1.0
    # l'épaisseur varie AUTOUR du centre : 4 angles -> >= 3 valeurs G distinctes
    img_idx = doc["textures"][iri["iridescenceThicknessTexture"]["index"]]["source"]
    bv = doc["bufferViews"][doc["images"][img_idx]["bufferView"]]
    tex = Image.open(io.BytesIO(binv[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]))
    cx = cy = tex.size[0] // 2
    r = tex.size[0] // 3
    gs = {tex.getpixel((cx + r, cy))[1], tex.getpixel((cx - r, cy))[1],
          tex.getpixel((cx, cy + r))[1], tex.getpixel((cx + int(r * 0.7), cy + int(r * 0.7)))[1]}
    assert len(gs) >= 3, gs
    # LE PEIGNE EST TANGENT AU PÉRIMÈTRE, pas radial : le produit scalaire
    # (R-127,5 ; G-127,5).(dx ; dy) est nul aux arrondis près (borne exacte :
    # 0,5 par canal). Un champ RADIAL — une texture d'anisotropie qui porterait
    # la DIRECTION du rayon au lieu de sa perpendiculaire — y donnerait
    # ~127,5 x r, deux ordres de grandeur plus haut.
    #
    # RECTIFICATIF (re-revue Task 5) : cet assert et le `tw == -1` ci-dessus
    # sont COMPLÉMENTAIRES, pas redondants — ne jamais supprimer le second en
    # le croyant couvert par celui-ci. Ils mesurent deux objets différents :
    # `tw` épingle la MAIN du repère tangent (l'attribut du maillage), celui-ci
    # épingle le CHAMP dans l'espace des pixels (les octets de la texture). Une
    # tangente de mauvaise main laisse cette texture PARFAITEMENT
    # perpendiculaire — elle ne la touche pas — et ne se voit que sur `tw` ;
    # inversement une texture radiale passerait le `tw`. Il faut les deux.
    i_ani = doc["textures"][ani["anisotropyTexture"]["index"]]["source"]
    bva = doc["bufferViews"][doc["images"][i_ani]["bufferView"]]
    tex_a = Image.open(io.BytesIO(
        binv[bva["byteOffset"]:bva["byteOffset"] + bva["byteLength"]]))
    ca = tex_a.size[0] // 2
    for dx, dy in ((60, 0), (0, 60), (42, 42), (-42, 42), (-55, -20),
                   (30, -70), (-70, 30)):
        rr, gg, bb = tex_a.getpixel((ca + dx, ca + dy))[:3]
        scal = (rr - 127.5) * dx + (gg - 127.5) * dy
        assert abs(scal) <= 0.5 * (abs(dx) + abs(dy)) + 1.0, (dx, dy, scal)
        # et le canal B reste à 255 : l'extension MULTIPLIE la force par lui,
        # à 0 la finition serait invisible partout (amendement Task 5).
        assert bb == 255, (dx, dy, bb)
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
    # LES DEUX GARDES, PROUVÉES et pas seulement écrites (revue Task 5) : une
    # finition inconnue est REFUSÉE (la remplacer en douce par l'argent
    # livrerait une carte fausse sans que personne le sache), et out_px est
    # ramené au plafond §6.2bis au lieu de cuire 4096² pour rien.
    with pytest.raises(ValueError):
        SC.holo_finish("cuivre", aniso=False, out_px=128)
    borne = SC.holo_finish("argent", aniso=False, out_px=99999)
    assert Image.open(io.BytesIO(borne["iridescence"]["png"])).size == \
        (SC.HOLO_PX[1], SC.HOLO_PX[1]) == (2048, 2048)
    assert Image.open(io.BytesIO(
        SC.holo_finish("argent", aniso=False, out_px=1)["iridescence"]["png"]
    )).size == (SC.HOLO_PX[0], SC.HOLO_PX[0])


def test_le_transform_porte_le_trs_du_noeud():
    from app.services.cards import forge3d_scene as SC
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

- [x] **Step 2 : implémentation (forge3d_scene.py ; `tile_maps` vit dans forge3d.py — revue)**

```python
def material_pngs(maps: dict) -> dict:
    """Les maps d'une matière, CUITES en PNG pour le writer.

    Sortie : `{"normal", "mr", "ao", "emissive"}` en octets PNG — SEULEMENT
    ce qui existe en entrée (une matière sans normale ne fabrique pas une
    normale plate pour faire nombre). Le pack `mr` suit la convention glTF,
    celle que le lab Matières applique déjà à son ORM (R=AO, G=Roughness,
    B=Metallic) : ici R est neutre (255), G porte la rugosité, B la
    métallicité. L'occlusion voyage à part parce que le writer la câble sur
    SON entrée dédiée (`occlusionTexture`), pas dans le pack.

    Rugosité ou métallicité SEULE : le canal manquant prend le neutre du
    MOTEUR — rugosité 255 (entièrement mate) et métallicité 0 (diélectrique).
    Un zéro par défaut dans les deux cas rendrait un MIROIR PARFAIT à qui ne
    fournit qu'une rugosité.

    Les niveaux sont DANS les octets : c'est le writer qui remet
    metallicFactor/roughnessFactor à 1.0 (doctrine `RENDER_NOTE` du lab
    Matières — appliquer le curseur EN PLUS le compterait deux fois)."""
    # PIL importé LOCALEMENT : ce module ne dépend de PIL que là où il
    # FABRIQUE une image ; la géométrie, elle, en reçoit et n'a rien à
    # importer (patron déjà en place dans `relief_mesh`).
    from PIL import Image
    out: dict = {}
    nrm = maps.get("normal")
    if nrm is not None:
        out["normal"] = _png_bytes(nrm.convert("RGB"))
    ao = maps.get("ao")
    if ao is not None:
        out["ao"] = _png_bytes(ao.convert("L").convert("RGB"))
    emi = maps.get("emissive")
    if emi is not None:
        out["emissive"] = _png_bytes(emi.convert("RGB"))
    rough, metal = maps.get("roughness"), maps.get("metallic")
    if rough is not None or metal is not None:
        # taille de RÉFÉRENCE : la PLUS GRANDE des deux, pas la première venue.
        # Un pack RGB exige trois canaux de même dimension (`Image.merge`
        # lèverait sinon) ; aligner sur la plus petite JETTERAIT le détail de
        # l'autre, définitivement, pour n'avoir rien gagné.
        cotes = [im.size for im in (rough, metal) if im is not None]
        taille = max(cotes, key=lambda s: s[0] * s[1])
        g = (rough.convert("L") if rough is not None
             else Image.new("L", taille, 255))
        b = (metal.convert("L") if metal is not None
             else Image.new("L", taille, 0))
        # filtre de rééchantillonnage EXPLICITE (convention de
        # `material_store.resize_maps` : LANCZOS pour les maps de couleur,
        # BICUBIC pour les maps de données). Le défaut de PIL a déjà changé
        # d'une version à l'autre — le laisser implicite ferait dépendre nos
        # octets de la version de Pillow installée, et le déterminisme est
        # une PROMESSE ici, pas un effet de bord.
        if g.size != taille:
            g = g.resize(taille, Image.BICUBIC)
        if b.size != taille:
            b = b.resize(taille, Image.BICUBIC)
        out["mr"] = _png_bytes(
            Image.merge("RGB", (Image.new("L", taille, 255), g, b)))
    return out


def tile_maps(mid, kinds, tile_mm, w_mm, h_mm, out_px=1024):
    """Les maps d'une matière de la boutique, TUILÉES au pas physique
    `tile_mm` sur une toile au ratio de la carte — collage par pavage PIL,
    donc DÉTERMINISTE (aucun aléa, aucun bruit : deux appels rendent les mêmes
    octets). Les niveaux de la matière sont CUITS (`bake_levels`), comme sur
    tous les chemins de sortie du lab Matières : l'écran et le moteur
    reçoivent le même pixel.

    LE TUILAGE EST CUIT DANS LES PIXELS, et c'est le point : le sampler du GLB
    peut rester CLAMP_TO_EDGE partout (invariant de `write_scene_glb` depuis
    la 2a) au lieu de basculer en REPEAT pour ces textures-là — un REPEAT sur
    une carte dont les UV débordent d'un cheveu répéterait le bord, pas le
    motif.

    `mid` introuvable -> ValueError NOMMÉE (l'appelant en fait un refus motivé,
    jamais un 500 — doctrine 2.5). Idem pour une cote nulle, négative ou pas
    numérique du tout : les cotes passent d'abord par `_num` (qui ne lève
    JAMAIS — une chaîne y devient 0.0), et c'est la garde de positivité qui
    refuse, NOMMÉMENT. Sans ce passage, `"31,5"` sortait en TypeError nu sur
    la comparaison, et les trois divisions plus bas en ZeroDivisionError :
    deux 500 sur une simple donnée d'entrée.

    `out_px` est borné à `SC.HOLO_PX` (8..2048) — LE MÊME plafond que les
    finitions, exprès : les deux textures habillent la même carte, un plafond
    dissymétrique n'aurait aucun sens (bornes symétriques, revue Task 5)."""
    from app.services import material_store as MSTORE
    tile_mm = _num(tile_mm, 0.0, -1e6, 1e6)
    w_mm = _num(w_mm, 0.0, -1e6, 1e6)
    h_mm = _num(h_mm, 0.0, -1e6, 1e6)
    if tile_mm <= 0 or w_mm <= 0 or h_mm <= 0:
        raise ValueError(f"cotes de tuilage invalides : tile={tile_mm} "
                         f"w={w_mm} h={h_mm} (toutes strictement positives)")
    out_px = int(_num(out_px, 1024.0, *HOLO_PX))
    mat = MSTORE.read_material(mid)
    if mat is None:
        raise ValueError(f"matière introuvable : {mid}")
    maps = MSTORE.load_maps(mid, kinds=list(set(kinds) | {"basecolor"}))
    maps = MSTORE.bake_levels(maps, mat.get("props"))
    # la toile prend le RATIO de la carte : `out_px` est le GRAND côté, l'autre
    # s'en déduit — une toile carrée étirerait le motif d'un tiers sur une
    # carte 63x88.
    W = out_px if w_mm >= h_mm else max(8, int(round(out_px * w_mm / h_mm)))
    H = out_px if h_mm > w_mm else max(8, int(round(out_px * h_mm / w_mm)))
    # BORNE L'ALLOCATION DÉRIVÉE (résidu de re-revue Task 5) : mêmes entrées
    # légales, jamais 127 Mo d'intermédiaire — même classe que la faute des
    # bornes d'entrée. `tile_mm` va jusqu'à 200 mm et `w_mm` peut valoir
    # 31,75 mm (mini US) : `W * tile_mm / w_mm` atteignait 12 900 px pour une
    # toile de 2048, soit une tuile de 500 Mo en RGB. Une tuile PLUS GRANDE
    # que la toile est de toute façon collée une fois puis rognée — la borner
    # au grand côté de la toile ne change RIEN au pixel rendu.
    tpx = max(4, min(max(W, H), int(round(W * tile_mm / w_mm))))
    out = {}
    from PIL import Image as _I
    for kind in kinds:
        src = maps.get(kind)
        if src is None:
            continue
        # `resize` NU, et pas `material_store.resize_maps` : celui-ci passe par
        # `clean_preview_res`, qui SNAPPERAIT `tpx` sur la liste blanche des
        # tailles servies (128/256/...) et détruirait le pas physique — la
        # raison d'être de cette fonction. Coût connu : une normale
        # rééchantillonnée n'est plus exactement unitaire (`resize_maps`, lui,
        # renormalise) ; l'écart est sous le bruit d'un octet à ces tailles.
        #
        # Filtre EXPLICITE, convention de `material_store.resize_maps:1033` :
        # LANCZOS pour les maps de couleur, BICUBIC pour les maps de données.
        # Le défaut de PIL a déjà changé d'une version à l'autre — l'implicite
        # ferait dépendre nos octets de la version de Pillow installée, et le
        # déterminisme est une PROMESSE ici.
        filtre = (_I.LANCZOS if kind in ("basecolor", "emissive")
                  else _I.BICUBIC)
        tuile = src.resize((tpx, tpx), filtre)
        toile = _I.new(src.mode, (W, H))
        for y in range(0, H, tpx):
            for x in range(0, W, tpx):
                toile.paste(tuile, (x, y))
        out[kind] = toile
    return out
```

```python
# §6.2bis-c — les DEUX recettes de finition, chiffres de la spec, relus au bit
# près par le test.
_HOLO_RECIPES = {
    "argent": {"base": [0.95, 0.95, 0.97, 1.0], "rough": 0.12, "ior": 1.8,
               "thickness": [200.0, 900.0]},
    "dorure": {"base": [1.0, 0.84, 0.55, 1.0], "rough": 0.12, "ior": 1.6,
               "thickness": [200.0, 600.0]},
}
_HOLO_SECTORS = 48   # secteurs radiaux : mip-stables, zéro moiré (§6.2bis-c)
_HOLO_CYCLE = 8          # niveaux d'épaisseur, un cycle complet tous les 8
_HOLO_ANISO_STRENGTH = 0.85
_HOLO_CLEARCOAT_ROUGH = 0.06
# §6.2bis : les finitions se cuisent entre 1024 et 2048. Le plafond est ICI,
# et le MÊME que celui de `tile_maps` (bornes symétriques, revue Task 5) :
# 4096² coûtait ~17 s et ~200 Mo pour un gain invisible sur une carte de
# 63 mm — un chiffre venu d'un graphe ne doit pas pouvoir l'atteindre.
HOLO_PX = (8, 2048)

# La liste blanche PUBLIÉE : l'appelant borne son entrée avec elle au lieu de
# recopier deux noms qui dériveront (même patron que les blocs miroir).
HOLO_KINDS = tuple(_HOLO_RECIPES)


def holo_finish(kind: str, aniso: bool, out_px: int = 1024) -> dict:
    """UNE finition holographique de la spec (§6.2bis-c), prête pour le
    writer : facteurs PBR, bloc iridescence (+ sa texture d'épaisseur),
    clearcoat, et l'anisotropie SEULEMENT si on la demande.

    `kind` hors `HOLO_KINDS` lève une ValueError NOMMÉE : une finition
    inconnue silencieusement remplacée par l'argent livrerait une carte FAUSSE
    sans que personne ne le sache. C'est à l'appelant de borner son entrée
    AVANT (doctrine 2.5) — `HOLO_KINDS` lui donne la liste sans la recopier.

    `out_px` est borné à `HOLO_PX` (8..2048, §6.2bis) : la texture est
    fabriquée pixel par pixel en Python ; un chiffre non borné venu d'un
    graphe serait une bombe mémoire."""
    r = _HOLO_RECIPES.get(str(kind))
    if r is None:
        raise ValueError(f"finition holographique inconnue : {kind!r} "
                         f"(connues : {', '.join(HOLO_KINDS)})")
    px = max(HOLO_PX[0], min(HOLO_PX[1], int(_f(out_px, 1024.0))))
    return {
        "pbr": {"baseColorFactor": list(r["base"]),
                "metallicFactor": 1.0, "roughnessFactor": r["rough"]},
        "iridescence": {"factor": 1.0, "ior": r["ior"],
                        "thickness": list(r["thickness"]),
                        "png": _holo_thickness_png(px)},
        "clearcoat": {"factor": 1.0, "rough": _HOLO_CLEARCOAT_ROUGH},
        "anisotropy": ({"strength": _HOLO_ANISO_STRENGTH,
                        "png": _holo_aniso_png(px)} if aniso else None),
    }
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

- [x] **Step 3 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): matieres tuilees (pack MR glTF), finitions holo iridescence/clearcoat/anisotropy extensionsUsed-only, TRS par element"
```

---

### Task 6: `build3d` chaîné — fusion des GLB externes, STL mixte, metadata moteurs

> **LEGS DE LA TASK 4 (revue du 20/08) — OBLIGATOIRE ici :** depuis l'asymétrie
> I4, un job fal `served` n'implique PLUS « utilisable » : un GLB au-delà de
> `MAX_EXT_GLB_BYTES` arrive `served` avec `closed: None` + `closed_note` et
> `source/bytes` au job. La FUSION doit donc GATER sur `job["bytes"]` (refus
> 400 nommé au-delà de la borne — sans OUVRIR le fichier) et traiter
> `closed is None` comme non-imprimable (refus STL motivé par la note), en
> plus du `closed is False` déjà prévu. Le schéma job : `run_id` est OPAQUE
> (jamais inventé/envoyé par l'écran) et `source.sha256` est null tant que
> `queued`.
>
> **LIVRÉE (11b25a9) — écarts plan-vs-réalité corrigés, qui PRÉVALENT :**
> (1) le manifeste dit **`bbox_mm`** (pas box_mm), fichier `layers_c01_front`
> (carte 0 → c01) ; surtout, `bbox_mm` est en espace **TOILE** (fond perdu
> inclus, y vers le BAS) alors que les maillages vivent en espace **COUPE**
> (y vers le haut) — `_layer_box_mm` convertit, sans quoi chaque maillage
> moteur atterrissait décalé du fond perdu et en MIROIR vertical ; (2) le fit
> du plan mesurait les positions BRUTES — l'étalon du plan lui-même (écrit par
> notre writer, racine ×0.001) était 1000× trop petit : `glb_scene_mesh`
> gagne `world=True` (descente du graphe de scène, matrices composées, garde
> de profondeur + visités, repli plat) et le fit devient AGNOSTIQUE AUX UNITÉS
> (le défaut `world=False` garde la mesure `closed` de la Task 4 inchangée à
> l'octet) ; (3) gate de taille sur `max(job["bytes"], stat)` (métadonnée,
> jamais un open — prouvé sur GLB corrompu : 400 au-dessus, 409 en-dessous) ;
> (4) `out_ignored` non cassant sur le writer, entrées par INDEX (deux
> couches homonymes recto/verso ne collisionnent pas) ; (5) STL refusé →
> l'ancien `{art}.stl` est DÉLIÉ (même argument legs 4 que l'aperçu) ; la
> description du metadata cesse de dire « construite localement » quand un
> moteur a contribué ; `elements` reste un INT (l'écran 2a le concatène),
> le détail par élément vit dans `elements_detail`. **CLOSE (11b25a9 +
> correctifs 9d95155, re-revue APPROUVÉE)** : le STL honore le trs local
> (même monde que le GLB, bbox recalculée de zéro en re-revue), allowlist
> `_EXIG_CONNUES` des extensions exigées fusionnables (le refus nommé tombe
> exactement sur la couture meshopt — les deux branches justes), éventail de
> frères avoué, profondeur de scène nommée, variants réindexés + déclarations
> doc-niveau avouées, canvas_mm/bleed_mm du manifeste, 73/73, 23+2 mutants
> tués. Reste d'une ligne replié en tête de Task 7 : garde componentType
> float32 dans `_accessor_floats` (le couplage allowlist↔lecteur devient
> explicite). Étapes cochées.

**Files:**
- Modify: `backend/app/services/cards/forge3d_scene.py` (fusion)
- Modify: `backend/app/services/cards/forge3d.py` (résolution de chaînes + route)
- Test: `backend/tests/test_cards_forge3d.py`

- [x] **Step 1 : tests en RED**

```python
def _job_servi(did, nid, glb: bytes, closed, engine="meshy-7", credits=None,
               note=None, octets=None, source=None):
    """Pose un nœud mesh3d SERVI sur disque, avec la forme EXACTE de job.json
    qu'écrit `_run_mesh3d` (Task 4) — `bytes` compris : c'est LUI que le gate
    de taille de la fusion relit, sans ouvrir le fichier. `octets` permet de
    mentir sur cette taille (le gate doit croire le job, pas le disque)."""
    base = _dossier_noeud(did, nid)
    (base / "textures").mkdir(parents=True, exist_ok=True)
    (base / "model.glb").write_bytes(glb)
    job = {"schema": "card-3d/mesh3d-job@1", "node": nid, "engine": engine,
           "provider": "meshy" if str(engine).startswith("meshy") else "fal",
           "run_id": "essai-" + nid, "status": "served", "progress": 100,
           "step": "Livré", "error": None, "closed": closed,
           "closed_note": note, "triangles": 0,
           "bytes": len(glb) if octets is None else int(octets),
           "files": {"glb": "model.glb"}}
    if credits is not None:
        job["consumed_credits"] = credits
    if source is not None:
        # `source` dit de QUELLE couche ce GLB est né (la route l'écrit au
        # lancement) — le laisser absent garde le comportement historique des
        # tests qui ne s'y intéressent pas.
        job["source"] = source
    (base / "job.json").write_text(json.dumps(job, ensure_ascii=False),
                                   encoding="utf-8")
    return job


def test_l_assemblage_fusionne_le_glb_externe_a_sa_place_de_couche():
    """Chaîne layer->mesh3d->transform->assemble : l'élément externe est
    réindexé sous un parent au TRS calculé (ajusté à la BOÎTE MM de sa couche,
    centré, à z du transform), l'identité du doc externe est jetée, les
    accesseurs restent exacts, le STL mixte sort quand tout est fermé."""
    did = _deck("Fusion")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_externe_63x88(), closed=True, engine="meshy-7",
               credits=30)

    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "illustration", "side": "front"},
        {"id": "m1", "kind": "mesh3d", "engine": "meshy-7",
         "texture_prompt": "", "ultra": False},
        {"id": "tr", "kind": "transform", "x_mm": 0, "y_mm": 0, "z_mm": 2.0,
         "rot_deg": 0, "scale": 1.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "fusion3d"}],
        "edges": [{"from": "s1", "to": "m1"}, {"from": "m1", "to": "tr"},
                  {"from": "tr", "to": "asm"}, {"from": "s2", "to": "t2"},
                  {"from": "t2", "to": "asm"}, {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, binv = _read_glb(glb)
    # l'identité du document externe est JETÉE : le nôtre n'en émet aucune, le
    # sien n'en apporte pas.
    plat = json.dumps(doc)
    for mot in ("generator", "copyright", "author", "producer"):
        assert f'"{mot}"' not in plat, mot
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    # DEUX enfants de racine, et deux SEULEMENT : les nœuds INTERNES du GLB
    # externe restent sous SON parent — les hisser au rang de racine ferait
    # exploser la carte en pièces détachées, chacune à l'origine.
    assert sorted(noms) == ["cadre", "illustration"], noms
    parent_ext = doc["nodes"][racine["children"][noms.index("illustration")]]
    assert [doc["nodes"][k]["name"] for k in parent_ext["children"]] == ["brut"]
    # LE FIT, RECALCULÉ DEPUIS LE MANIFESTE : la boîte de la couche
    # illustration est mesurée à l'export (champ `bbox_mm`, repère TOILE —
    # origine au coin de toile, y vers le BAS, fond perdu compris) ; l'externe
    # (63x88) y est mis à l'échelle, centré, et posé à z du transform.
    man = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/layers_c01_front.json").content)
    boite = next(l for l in man["layers"]
                 if l["role"] == "illustration")["bbox_mm"]
    bw = boite[2] - boite[0]
    bh = boite[3] - boite[1]
    # NOTE D'ÉCHELLE, et ce n'est PAS un détail : ce faux-moteur est écrit par
    # NOTRE writer, dont la racine porte le mm->m (0,001). Sa scène mesure donc
    # 0,063 x 0,088, pas 63 x 88 — et c'est la taille RENDUE que le fit doit
    # mesurer. Un fit calculé sur les positions BRUTES rendrait ici une pièce
    # mille fois trop petite dans un GLB structurellement irréprochable.
    mw, mh = 63.0 * 0.001, 88.0 * 0.001
    s = min(bw / mw, bh / mh)
    assert abs(parent_ext["scale"][0] - s) < 1e-9
    assert parent_ext["scale"] == [parent_ext["scale"][0]] * 3   # UNIFORME
    # TOUT le z vient du transform (le fit ne le compte pas deux fois) : la
    # base de l'externe est à z=0, donc translation z == 2.0 EXACTEMENT.
    assert abs(parent_ext["translation"][2] - 2.0) < 1e-9
    # ...et le centrage est celui de la boîte RAMENÉE au repère COUPE du
    # maillage (origine coin de coupe, y vers le HAUT) : sans ce changement de
    # repère, l'élément serait décalé du fond perdu sur les deux axes.
    saignee = man["bleed_mm"]
    cx = (boite[0] + boite[2]) / 2.0 - saignee - s * mw / 2.0
    cy = (man["canvas_mm"][1] - (boite[1] + boite[3]) / 2.0) - saignee - s * mh / 2.0
    assert abs(parent_ext["translation"][0] - cx) < 1e-6
    assert abs(parent_ext["translation"][1] - cy) < 1e-6
    # BORNES DES ACCESSEURS DU DOC FUSIONNÉ : toujours EXACTES (re-mesurées
    # ici, pas relues du document) — la recopie vue par vue décale les
    # offsets, elle ne doit toucher NI les octets NI les bornes.
    vus = 0
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126 or "min" not in acc:
            continue
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "VEC4": 4, "SCALAR": 1}[acc["type"]]
        lo = [float("inf")] * n
        hi = [float("-inf")] * n
        for e2 in range(acc["count"]):
            vals = struct.unpack_from("<" + "f" * n, binv, off + e2 * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c])
                hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi, acc
        vus += 1
    assert vus >= 6, vus            # 3 par élément au minimum, deux éléments
    # RÉINDEXATION PROUVÉE : le matériau du maillage externe vise SON image
    # (celle embarquée avec lui), pas celle du voisin local — un indice oublié
    # au décalage donnerait un GLB parfaitement valide montrant la mauvaise
    # texture, ce qu'aucun contrôle de structure ne verrait.
    # (le faux-moteur est un GLB de NOTRE writer : sous son parent de fusion
    # vient SA racine mm->m, et sous elle seulement le nœud porteur du mesh —
    # la hiérarchie interne est GARDÉE telle quelle, pas aplatie)
    n_brut = doc["nodes"][doc["nodes"][parent_ext["children"][0]]["children"][0]]
    prim = doc["meshes"][n_brut["mesh"]]["primitives"][0]
    tex_ext = doc["materials"][prim["material"]]["pbrMetallicRoughness"][
        "baseColorTexture"]["index"]
    assert doc["images"][doc["textures"][tex_ext]["source"]]["name"] == "brut"
    # ...et son SAMPLER est le SIEN, ajouté, jamais notre CLAMP recyclé
    tex_loc = doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    assert doc["textures"][tex_loc]["sampler"] == 0
    assert doc["textures"][tex_ext]["sampler"] != 0
    assert len(doc["samplers"]) >= 2
    # metadata : les moteurs RÉELLEMENT utilisés, mesurés
    meta = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["engines"] == "local+meshy-7"
    assert types["elements_3d"] == 2
    # le bordereau dit QUI est local et QUI vient d'un moteur, et ce qu'il a coûté
    detail = {e["name"]: e for e in b["elements_detail"]}
    assert detail["cadre"]["kind"] == "local"
    assert detail["illustration"]["kind"] == "externe"
    assert detail["illustration"]["engine"] == "meshy-7"
    assert detail["illustration"]["credits"] == 30
    assert b["elements"] == 2
    # STL : les DEUX éléments sont fermés -> écrit, longueur exacte
    assert b["stl"]["written"] is True, b["stl"]
    stl = _api("GET", f"/api/cards/{did}/forge3d/file/{b['stl']['name']}").content
    n_tri = struct.unpack("<I", stl[80:84])[0]
    assert len(stl) == 84 + 50 * n_tri
    # LE MAILLAGE EXTERNE EST DANS LE STL, ET À SA PLACE. Le compte : celui
    # des deux éléments réunis — mesuré en rebâtissant le MÊME graphe amputé
    # de sa chaîne moteur (aucun chiffre recopié à la main).
    from app.services.cards import forge3d_scene as SC
    ext_tris = len(SC.glb_scene_mesh(_glb_externe_63x88())["indices"]) // 3
    g_local = {"nodes": [n for n in g["nodes"] if n["id"] not in ("s1", "m1", "tr")],
               "edges": [e for e in g["edges"]
                         if e["from"] not in ("s1", "m1", "tr")]}
    g_local["nodes"] = [dict(n, name="fusion3d_local") if n["kind"] == "artifact"
                        else n for n in g_local["nodes"]]
    r_l = _api("POST", f"/api/cards/{did}/forge3d/build3d",
               json={"graph": g_local, "card": 0})
    assert r_l.status_code == 200, r_l.text
    stl_l = _api("GET", "/api/cards/" + did + "/forge3d/file/"
                 + r_l.json()["artifact"]["stl"]["name"]).content
    assert n_tri == struct.unpack("<I", stl_l[80:84])[0] + ext_tris
    # ...et à SA place : l'externe est posé à z=2.0 + son épaisseur mise à
    # l'échelle, bien au-dessus du relief local (qui plafonne à 1,3 mm).
    zmax = max(max(struct.unpack_from("<f", stl, k + 20)[0],
                   struct.unpack_from("<f", stl, k + 32)[0],
                   struct.unpack_from("<f", stl, k + 44)[0])
               for k in range(84, 84 + 50 * n_tri, 50))
    assert abs(zmax - (2.0 + s * 1.3 * 0.001)) < 1e-3, zmax
    # ── LE MANIFESTE FAIT FOI pour le changement de repère (M6) : la toile et
    # le fond perdu viennent de LUI, pas d'une re-dérivation depuis la
    # géométrie courante. Preuve : on rallonge la toile DÉCLARÉE de 10 mm et
    # le placement suit, exactement de 10 mm en y (une re-dérivation ne
    # bougerait pas d'un cheveu).
    p_man = _dossier_forge3d(did) / "layers_c01_front.json"
    doctore = json.loads(p_man.read_text(encoding="utf-8"))
    doctore["canvas_mm"] = [doctore["canvas_mm"][0],
                            doctore["canvas_mm"][1] + 10.0]
    p_man.write_text(json.dumps(doctore), encoding="utf-8")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 200, r2.text
    doc2, _ = _read_glb(_api(
        "GET", "/api/cards/" + did + "/forge3d/file/"
        + r2.json()["artifact"]["glb"]["name"]).content)
    rac2 = doc2["nodes"][doc2["scenes"][0]["nodes"][0]]
    noms2 = [doc2["nodes"][k]["name"] for k in rac2["children"]]
    p2 = doc2["nodes"][rac2["children"][noms2.index("illustration")]]
    assert abs(p2["translation"][1] - (cy + 10.0)) < 1e-6
    assert abs(p2["translation"][0] - cx) < 1e-6      # x : inchangé


def test_un_noeud_mesh3d_sans_glb_servi_refuse_l_assemblage():
    did = _deck("Trou")
    _exporter_couches(did)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 409, r.text
    assert "m1" in r.json()["detail"] and "servi" in r.json()["detail"]


def test_le_stl_mixte_refuse_un_externe_ouvert_ou_non_mesure():
    """Le gate STL relit le `closed` CACHÉ au job (jamais une re-mesure) :
    `False` refuse pour non-fermeture, `None` refuse pour non-MESURE, avec la
    note du job — deux motifs distincts, jamais le même message recyclé."""
    from app.services.cards import forge3d_scene as SC
    did = _deck("Ouvert")
    _exporter_couches(did)
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    q = SC.quad_mesh(63.0, 88.0)
    ext = SC.write_scene_glb([{"name": "plan", "mesh": q,
                               "png": png.getvalue(), "alpha": True,
                               "z_mm": 0.0}], name="p", extras={})
    _job_servi(did, "m1", ext, closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    b = r.json()["artifact"]
    assert b["stl"]["written"] is False and "ferm" in b["stl"]["why"]
    assert "m1" in b["stl"]["why"] or "illustration" in b["stl"]["why"]
    # un graphe SANS aucun élément local : les moteurs seuls font le metadata
    meta = json.loads(_api(
        "GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["engines"] == "meshy-7" and types["elements_3d"] == 1
    # closed=None (non mesuré) refuse aussi, motif DIFFÉRENT — et la note du
    # job voyage jusqu'au bordereau (le « pourquoi » du pourquoi).
    _job_servi(did, "m1", ext, closed=None,
               note="fermeture non mesurée : maillage trop lourd (2 triangles)")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": g, "card": 0})
    assert r2.status_code == 200, r2.text
    pourquoi = r2.json()["artifact"]["stl"]
    assert pourquoi["written"] is False
    assert "mesur" in pourquoi["why"] and "trop lourd" in pourquoi["why"]
    assert pourquoi["why"] != b["stl"]["why"]


def test_le_rebuild_efface_l_apercu_perime():
    """Legs 4 : rebâtir `carte3d` supprime carte3d_preview.png — le metadata
    ne montre plus jamais l'aperçu d'un GLB qui n'existe plus."""
    did = _deck("Perime")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "carte3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    assert _api("POST", f"/api/cards/{did}/forge3d/build3d",
                json={"graph": g, "card": 0}).status_code == 200
    fdir = _dossier_forge3d(did)
    (fdir / "carte3d_preview.png").write_bytes(_png(Image.new("RGBA", (4, 4))))
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 200, r.text
    assert not (fdir / "carte3d_preview.png").exists()
    # le bordereau reste HONNÊTE : l'aperçu est attendu, pas écrit
    assert r.json()["artifact"]["preview"] == {
        "expected": "carte3d_preview.png", "written": False}


def test_le_glb_externe_a_images_uri_est_refuse_motive():
    """Rien ne se télécharge à l'assemblage : un GLB dont les images vivent
    au bout d'une URL est REFUSÉ NOMMÉMENT, pas silencieusement dépouillé de
    ses textures."""
    did = _deck("Uri")
    _exporter_couches(did)
    _job_servi(did, "m1", _glb_bricole(
        images=[{"uri": "https://ailleurs.example/tex.png"}]), closed=False)
    g = _graphe_mesh3d("meshy-7")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": g, "card": 0})
    assert r.status_code == 409, r.text
    assert "uri" in r.json()["detail"].lower()
```

(Réutiliser le helper `_job_servi` et `_exporter_couches` définis plus haut ; `Image`
et `io` sont déjà importés dans le fichier de test. Le nom du manifeste
`layers_c00_front.json` : reprendre la convention EXACTE des tests 2a du fichier —
si l'existant nomme `layers_c{NN}_{side}.json` avec un autre gabarit pour card 0,
suivre l'existant.)

Run : FAIL.

- [x] **Step 2 : la fusion dans forge3d_scene.py**

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
def _fit_external(monde: dict, box_mm: list, trs: dict | None) -> dict:
    """LE PLACEMENT d'un GLB de moteur : échelle UNIFORME pour tenir dans la
    boîte mm de SA couche (max-fit, proportions gardées), centré sur cette
    boîte, posé à z. Le transform de l'utilisateur COMPOSE : son échelle
    MULTIPLIE, sa rotation et sa translation S'AJOUTENT.

    `trs` est le NŒUD `transform` DU GRAPHE (x_mm/y_mm/z_mm/rot_deg/scale),
    pas le dict TRS du writer (`_trs_dict`) : un externe n'a pas de nœud à
    lui dans lequel poser un transform séparé — le fit et le transform de
    l'utilisateur se composent en UN SEUL TRS, celui du parent de fusion.

    POLITIQUE, pas mécanique — d'où sa place ICI et non dans le module scène
    (même partage des rôles que `tile_maps`) : la scène sait POSER un TRS,
    elle n'a pas à décider LEQUEL.

    TOUT le z vient du transform, et il n'y a PAS de paramètre `z_mm` : le
    plan en prévoyait un, que sa propre règle épinglait à 0.0 (« ne pas le
    compter deux fois »). Un paramètre qui doit TOUJOURS valoir zéro n'est pas
    un paramètre, c'est un piège — le premier appelant qui y passe autre chose
    double le décalage sans qu'aucun test ne s'en aperçoive. La base du
    maillage est POSÉE SUR le plan z du transform (`z - s x min(z)`), jamais
    enfoncée dedans.

    Une cote nulle (maillage parfaitement plat sur un axe) vaut 1.0 plutôt
    qu'un refus : un décalque est un maillage légitime, et le rapport
    d'échelle d'un axe sans épaisseur n'a simplement pas de sens — c'est
    l'AUTRE axe qui décide alors, ce que le `min` fait déjà.

    `monde` est le maillage DÉJÀ MESURÉ dans le repère de la scène
    (`glb_scene_mesh(..., world=True)`), pas les octets du GLB : c'est la
    taille RENDUE qui doit tenir dans la boîte. Un exportateur qui pose une
    conversion d'axes ou une échelle d'unité sur son nœud racine — le nôtre le
    fait, avec son mm->m — rendrait un fit calculé sur du brut faux de
    plusieurs ordres de grandeur, et la pièce invisible dans l'artefact sans
    qu'aucune structure ne soit fautive. Recevoir le maillage plutôt que les
    octets évite AUSSI de le dépaqueter deux fois : l'appelant le garde pour
    le STL (voir `_element_externe`), et cette fonction redevient de la
    politique PURE — aucune lecture de GLB ici."""
    pos = monde["positions"]
    xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    mw = (x1 - x0) or 1.0
    mh = (y1 - y0) or 1.0
    bw = (box_mm[2] - box_mm[0]) or 1.0
    bh = (box_mm[3] - box_mm[1]) or 1.0
    t = trs if isinstance(trs, dict) else {}
    s = min(bw / mw, bh / mh) * _num(t.get("scale"), 1.0, *TRANSFORM_SCALE)
    cx = (box_mm[0] + box_mm[2]) / 2.0 - s * (x0 + x1) / 2.0
    cy = (box_mm[1] + box_mm[3]) / 2.0 - s * (y0 + y1) / 2.0
    cz = -s * min(zs)
    return {"scale": s,
            "translate": [cx + _num(t.get("x_mm"), 0.0, *TRANSFORM_XY_MM),
                          cy + _num(t.get("y_mm"), 0.0, *TRANSFORM_XY_MM),
                          cz + _num(t.get("z_mm"), 0.0, *TRANSFORM_Z_MM)],
            "rotate_deg": _num(t.get("rot_deg"), 0.0, *TRANSFORM_ROT_DEG)}
```
(ATTENTION : si le transform est la SEULE source de z, ne pas le compter deux fois —
la règle : `z_mm` passé à `_fit_external` = 0.0 et TOUT le z vient de `t["z_mm"]`.
Le test l'épingle : translation z == 2.0 exactement.)

- [x] **Step 3 : forge3d.py — résolution de chaînes + route**

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

- [x] **Step 4 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/app/services/cards/forge3d_scene.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): fusion des GLB externes dans l artefact - fit a la boite de couche, STL mixte gate par closed cache, metadata moteurs"
```

---

### Task 7: L'écran 2b — chaînes de nœuds, prix AVANT, Lancer/poll, legs 5

> **CLOSE (9414eb4 + 6d321cf + b315ec3 + bdec22f) — amendements actés, qui
> PRÉVALENT sur les extraits ci-dessous :** (1) le point 5 disait « AUCUN
> nouveau listener global » — FAUX à l'usage : rien ne poussait la fraîcheur
> au changement de carte ; l'écran s'abonne à `core:render` (le patron des 4
> pièces sœurs, seul événement qui porte l'index, et le rendu PARTIEL de
> l'export ne l'émet pas — pas d'auto-alerte), garde = comparaison d'étiquette,
> gratuite quand rien n'a bougé ; le seed ATTEND la vérification avant de
> consommer le manifeste ; (2) l'INVARIANT D'APPARIEMENT
> `LAST_MANIFEST`↔`MANIFEST_CARD` est épinglé SYMÉTRIQUEMENT par test de
> source (l'export l'avait cassé par sa porte) ; (3) GARDES DE GÉNÉRATION sur
> TOUS les chemins asynchrones qui écrivent l'état (charge du manifeste,
> Lancer — le seul chemin qui dépense —, build3d, polls à jeton de
> génération) : un changement de carte à mi-vol ne ment jamais ; les
> registres de jobs sont vidés au changement de carte (un job est lié à SA
> carte) et le backend REFUSE (409 aux deux noms) un GLB servi pour une autre
> couche ; (4) la sonde re-sonde (30 s par nœud terminal, purge sur échec de
> build) — « relancé ailleurs » est atteignable ; (5) le pied de coût dit
> AUSSI le coût différé (« déjà servi — relancer coûterait ») ; jamais
> « 100 % gratuit » sous un bouton payant actif ; (6) la case ultra est
> pilotée par `ultra_extra_credits > 0` (contrat), PAS par l'id du moteur ;
> l'éligibilité ultra de `clean_graph` dérive de `MS._ultra_extra` (une seule
> source) ; (7) nouvelle règle lint **R14 « échappement »** (interpolation en
> valeur d'attribut, masqueur JS maison, 0 faux positif sur les 9 modules,
> morsure prouvée par mutation dans 2 modules) + épingles de source pour la
> position TEXTE (esc aux frontières de chipHtml) et le terminal du poll
> (l'opérateur, pas les mots) ; résidu avoué : ~30 interpolations numériques
> en position texte dans mod-gltf (nombres servis par le backend, sans risque
> aujourd'hui) ; (8) fetchJob garde le content-type (une route absente est
> DITE, jamais « jamais lancé ») — le sniff du détail 404 est un couplage au
> message, à durcir par un champ `code` (consigné pour plus tard) ; (9)
> Step 3 : `--geom` exécuté, `--contract` reporté à la Task 8 (backend
> requis). 77 tests, lint complet 0, mutants esc/poll/appariement/C1/I2 tous
> tués. Étapes cochées.

**Files:**
- Modify: `frontend/cardforge/js/mod-forge3d.js`
- Modify: `frontend/cardforge/css/mod-forge3d.css`
- Test: `backend/tests/test_cards_forge3d.py`

- [x] **Step 1 : test de source en RED**

```python
def test_l_ecran_2b_affiche_les_prix_avant_et_les_etats_de_job():
    """Test de SOURCE (Task 7) : l'écran 2b ne peut pas exister sans ces
    engagements — le prix AVANT (servi par /info, jamais recopié), le
    lancement et le poll d'un job payant, la clé manquante DITE avant le 503
    du backend, les chaînes matière/transform bornées par /info, le manifeste
    qui suit LA CARTE (legs 5), l'échec montré LITTÉRAL, une dégradation
    affichée telle quelle plutôt qu'un select vide muet, et le `run_id`
    comparé entre deux polls (une relance d'un autre onglet est DITE)."""
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
    # ... et ce rechargement est POUSSÉ, pas seulement tiré : le rail émet
    # `core:render` (jamais `core:deck`), l'évènement auquel mod-gltf/type/
    # print/data accrochent déjà leur péremption de carte. Sans cet abonnement
    # le contrôle de fraîcheur n'était appelé que depuis paintGraph, que rien
    # ne déclenchait quand l'utilisateur changeait de carte.
    assert 'CF.on("core:render"' in rendu
    handler = rendu.split('CF.on("core:render"')[1][:160]
    assert "cardChanged" in handler, handler
    # le seed CONSOMME le manifeste : il attend la vérification de fraîcheur
    # AVANT de le lire, sinon « construire le graphe par défaut » juste après
    # un changement de carte sème depuis les couches de la carte PRÉCÉDENTE.
    seed = rendu.split("async function seedDefault(")[1].split("\n  }")[0]
    assert "cardChanged" in seed and "defaultGraph(" in seed, seed
    assert seed.index("cardChanged") < seed.index("defaultGraph("), seed

    # L'INVARIANT D'APPARIEMENT, ÉPINGLÉ SUR LA SOURCE ENTIÈRE (et pas sur les
    # seuls chemins auxquels on a pensé) : `LAST_MANIFEST` et `MANIFEST_CARD`
    # forment une PAIRE — le manifeste et la carte POUR LAQUELLE il vaut. Poser
    # l'un sans l'autre fige un appariement faux que le comparateur de
    # `cardChanged` valide ensuite pour toujours ; c'est exactement ce qui est
    # arrivé au chemin de l'export (il posait `LAST_MANIFEST = rep.layers` seul,
    # à 123 lignes du plus proche `MANIFEST_CARD =`). Toute écriture de l'un
    # doit donc voisiner une écriture de l'autre. Mesuré : le plus grand écart
    # LÉGITIME est de 7 lignes.
    src_lignes = src.splitlines()
    pose_man = [i for i, l in enumerate(src_lignes)
                if re.search(r"LAST_MANIFEST\s*=[^=]", l)]
    pose_carte = [i for i, l in enumerate(src_lignes)
                  if re.search(r"MANIFEST_CARD\s*=[^=]", l)]
    assert pose_man and pose_carte
    # SYMETRIQUE (N6) : la paire se casse aussi bien en posant l'etiquette
    # seule (l'ecran se croit a jour sur un manifeste qui ne l'est pas) qu'en
    # posant le manifeste seul. Les deux sens sont donc verifies.
    for gauche, droite, quoi in ((pose_man, pose_carte, "LAST_MANIFEST"),
                                 (pose_carte, pose_man, "MANIFEST_CARD")):
        autre = "MANIFEST_CARD" if quoi == "LAST_MANIFEST" else "LAST_MANIFEST"
        for i in gauche:
            ecart = min(abs(i - j) for j in droite)
            assert ecart <= 10, (
                f"ligne {i + 1} pose {quoi} sans poser {autre} a cote (plus "
                f"proche : {ecart} lignes) — l'appariement manifeste/carte se "
                f"casse la : {src_lignes[i].strip()}")

    # le poll s'arrête aux DEUX états terminaux du contrat — et la DISJONCTION
    # est le fond de l'affaire : avec un « et » à la place du « ou », aucun job
    # ne satisfait plus la condition et la boucle tourne pour toujours, à un
    # GET toutes les 1,2 s, sans qu'aucun état affiché ne bouge. Épingler les
    # deux mots ne suffisait donc pas : on épingle l'opérateur.
    poll = rendu.split("function pollMesh3d(")[1].split("\n  }")[0]
    assert '"served"' in poll and '"failed"' in poll, poll
    assert re.search(r'status\s*===\s*"served"\s*\|\|', poll), poll

    # I1 — LA COUTURE writer<->ecran. Cote writer, `translate` REMPLACE le
    # `z_mm` de l'element (_node_trs) : il ne s'y AJOUTE pas. Semer un nœud
    # placement a z=0 sur un PLAN n'est donc pas « neutre » — ca l'aplatit sur
    # la couche du dessous (le cadre du graphe par defaut vit a 1,05 mm), et il
    # suffit d'ouvrir le tiroir Placement et de pousser x pour perdre la
    # parallaxe. Le neutre d'un plan, c'est SON z d'empilement.
    trs_corps = rendu.split("function editTrs(")[1].split("\n  }")[0]
    assert re.search(r"z_mm:\s*zEmpilement\(", trs_corps), trs_corps
    assert not re.search(r"z_mm:\s*0\b", trs_corps), trs_corps
    # ... et cette regle est CELLE que l'ecran affiche : une seule fonction,
    # lue par le semis ET par le rendu, sinon les deux derivent.
    zemp = rendu.split("function zEmpilement(")[1].split("\n  }")[0]
    assert "depth_mm" in zemp and '"plane"' in zemp, zemp
    assert "zEmpilement(" in rendu.split("function trsHtml(")[1].split("\n  }")[0]

    # LES CHAINES ECRITES PAR LE BACKEND (error, step, closed_note) sont
    # rendues ECHAPPEES : ce sont les seules valeurs de chipHtml qui ne
    # viennent ni d'un Number() ni d'un litteral d'ici, et un `<` dans un
    # message d'erreur de moteur casse la mise en page — au mieux.
    chip = rendu.split("function chipHtml(")[1].split("\n  }")[0]
    for champ in ("job.error", "job.step", "job.closed_note"):
        assert champ in chip, f"{champ} a disparu de chipHtml — pin obsolete"
        for m in re.finditer(re.escape(champ), chip):
            avant = chip[:m.start()]
            assert re.search(r"esc\(\s*(?:[\w.]+\s*\|\|\s*)?$", avant), (
                f"{champ} interpole sans esc() dans chipHtml : "
                f"...{chip[max(0, m.start() - 60):m.end() + 20]}")
    # l'échec d'un job est montré LITTÉRAL (error du job.json)
    assert "job.error" in rendu or 'job["error"]' in rendu
    # les legs d'affichage : degraded affiché tel quel, jamais un select vide muet
    assert "degraded" in rendu
    # run_id comparé entre deux polls (une relance d'un autre onglet est DITE)
    assert "run_id" in rendu
```

Run : FAIL.

- [x] **Step 2 : implémentation (suit les patrons DU fichier — paintGraph/rowHtml/
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

- [x] **Step 3 : GREEN + vérifications + commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
python scripts\qa\lint_cardforge.py --module forge3d
node frontend\cardforge\qa\test_core_contract.mjs --contract
```
(Vérifier les OCTETS du .js après édition — piège Windows NUL/CRLF connu du chantier.)
```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): ecran 2b - rangees chainees, moteurs et prix servis par /info, lancer/poll des jobs, cout avant, degraded et run_id dits"
```

---

### Task 7bis: Fluidité des manipulations à la souris (spec §9.6 — toutes les surfaces de drag du lab)

> **CLOSE (26f838f + ff285ea + acf6029) — re-revue APPROUVÉE.** Livré au-delà
> du plan : bug préexistant de position finale perdue (overlay P3) corrigé ;
> undo du scrub P6 rétabli (couplage corner_link généralisé par patchKeysOf) ;
> R13 en sémantique INDEX, 50 fichiers couverts, 60x plus vite ; isPrimary aux
> pointerdown (anti-coincement) ; before0 du slider remis à zéro par geste.
> **Résidus NOMMÉS de la revue du 20/08 :** (1) molette de zoom P1
> (mod-face.js:3843) : coalescence d'abord DIFFÉRÉE (geste INCRÉMENTAL, risque
> nommé sur l'invariant point-sous-curseur), ROUVERTE et CLOSE le 20/08 même —
> les molettes haute résolution et les flings de trackpad livrent bien
> plusieurs événements par frame. Livrée avec l'accumulateur local annoncé :
> `wheelPending` est l'état courant tant que la frame n'a pas écrit le doc et
> sert de base au cran suivant (composition identique cran par cran à la
> version séquentielle — x/y relus déjà arrondis au centième, scale non
> arrondi) ; groupage wheelArmed/420 ms CONSERVÉ, sa clôture pousse l'état
> FINAL exact AVANT de désarmer (l'équivalent du pointerup) ; épinglé par
> test_la_molette_p1_coalesce_son_zoom_a_la_frame ; vérification navigateur
> FAITE le 20/08 sur instance isolée du dépôt (:8799, DEEPOTUS_DATA_DIR
> scratch — l'app :8765 de l'utilisateur jamais touchée), mesures au vrai
> labo sur la carte seed : 6 crans dans un même tick → 0 patch synchrone,
> 1 seul core:doc, échelle finale = e^0.96 exacte au bit (les 6 crans
> composent — le risque « base périmée » est mort) ; 30 crans étalés sur
> 6 frames → 6 core:doc (30 avant le fix) ; centre du zoom résolu depuis
> deux curseurs distincts stable à < 0,8 px (point-sous-curseur tenu,
> fenêtre publiée par le cadre) ; un seul Ctrl+Z restaure l'état
> d'avant-rafale à l'identité et la rafale rejouée est déterministe ;
> clamp SCALE_MAX atteint proprement au fling ; touch-action calculé du
> slider P6 = "none".
> (2) le slider `.cf-solid-rg`, lui, EST coalescé (correctifs de revue) — même
> rangée, même clé, même coût que le champ voisin ; il porte désormais aussi
> son `touch-action: none` (spec 9.6-3, parité avec le scrub voisin — épinglé
> par test_le_slider_p6_est_une_surface_de_drag_declaree). (3) `--contract` et
> la vérification navigateur interactive restent dus à la Task 8 (backend
> :8765 éteint pendant la tâche — skip honnête, constaté par deux réviseurs).

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

- [x] **Step 1 : le patron rAF, appliqué à mod-frame.js d'abord**

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

- [x] **Step 2 : le même patron sur les cinq autres surfaces**

Lire chaque handler AVANT de le modifier (les modes de geste diffèrent), appliquer le
MÊME remède : état de geste local + un patch par frame + patch final exact au relâché +
`touch-action: none` + poignées/zones ≥ 12 px là où il y a des poignées. Surfaces :
mod-face.js:3769-3790 (pose), mod-type.js:4022-4126 (overlay de slots — le futur cœur
de l'édition directe §6.1), mod-texture.js:1509-1520, mod-print.js:1462-1481,
mod-solid.js:557-570. AUCUN changement de sémantique : mêmes bornes, mêmes arrondis,
même HIST une-fois-par-geste. Si une surface fait DÉJÀ moins d'un patch par frame
(certaines ne patchent qu'au relâché), la laisser telle quelle et le noter au rapport.

- [x] **Step 3 : l'octet NUL échappé + la règle lint « octets sains »**

mod-frame.js contient UN octet NUL brut (offset ~180802, dans
`s.indexOf("<NUL>")` d'un parseur binaire — légal en JS mais il fait passer le fichier
pour du binaire aux outils, grep s'arrête dessus). Le remplacer par la séquence
ÉCHAPPÉE `"\x00"` (4 caractères). Puis, dans lint_cardforge.py, nouvelle règle nommée
R13 « octets sains » : pour chaque fichier js/css/py/mjs du lab, lire les OCTETS et
signaler tout `\x00` brut et tout `\r` (CRLF) — violation, pas avertissement.
Vérifier : `python scripts\qa\lint_cardforge.py` complet → 0 violation (mod-frame
corrigé, aucun autre fichier atteint).

- [x] **Step 4 : vérification navigateur RÉELLE**

Via cf_deploy puis dans l'app : faire glisser la fenêtre du cadre avec des mouvements
RAPIDES — le rectangle suit le curseur sans traîner ; la poignée s'attrape sans viser
au pixel ; l'annulation reste UNE entrée par geste ; répéter sur un slot P3 (overlay) et
la pose P1. Rapporter ce qui est vu (avant/après si possible).

- [x] **Step 5 : GREEN + commit**

Les tests de source des pièces concernées (s'il en existe qui épinglent les handlers
modifiés) restent verts ; lint complet vert ; `node frontend\cardforge\qa\test_core_contract.mjs
--contract` inchangé.
```bash
git add frontend/cardforge/js frontend/cardforge/css scripts/qa/lint_cardforge.py
git commit -m "perf(cardforge): un patch par frame pendant les gestes souris, poignees 12px, touch-action none, NUL echappe + lint octets sains - spec 9.6"
```

---

### Task 8: Intégration finale 2b

> **FAITE (DONE_WITH_CONCERNS) — et la vérification navigateur a PAYÉ : deux
> vrais bugs de course Windows trouvés EN VIVANT, corrigés (f635d73, 3f0dbf3),
> prouvés sous 250 GET concurrents.** `os.replace` du job.json contre un
> `open()` concurrent : côté LECTEUR (PermissionError → _job_read rendait None
> → un job PAYÉ en cours se lisait « jamais lancé », le polling s'arrêtait à
> jamais et le pied de coût recomptait 35 crédits déjà consommés) ; côté
> ÉCRIVAIN (WinError 5 sur os.replace → l'exception marquait le job payé
> FAILED — **le poll tuait le job**). Remède : 3 essais bornés à 20 ms des
> deux côtés + test de régression bidirectionnel (mutation-vérifié ×2).
> Le TestClient sérialisé ne pouvait PAS voir ces courses — leçon : la vérif
> navigateur réelle est un instrument de mesure, pas une formalité.
> Portails : 10/10 fichiers cards (534 s), meshy vert, lint 9/9 0 violation,
> --geom 4/4, --contract TENU (backend vivant), cf_deploy -Check 0 écart
> (le script gère lui-même le piège du snapshot : lock + kill :8765 +
> relance + health), MESHY_MOCK posé/restauré à l'octet près, ZÉRO dépense
> réelle, 45 commits poussés (0 ahead). Parcours navigateur : manifests
> recto/verso 0 px d'écart, 7 moteurs aux prix de /info, 35 cr affichés
> AVANT, job mock servi ~9 s, bordereau engines local+meshy-7 aux crédits
> RÉELS, STL refusé au motif littéral nommant le nœud, extensions
> iridescence/clearcoat/aniso relues dans les octets du GLB fusionné, fit à
> sa place de couche (T=[11.9, 36.9, 0], échelle 39.97).
> **RESTE À VÉRIFIER À LA MAIN (l'outillage capture/pointeur du navigateur
> est mort en cours de session)** : le CHATOIEMENT visuel des franges en
> tournant le viewer (les octets sont justes, l'œil n'a pas tranché) ; le
> bloc FLUIDITÉ 7bis au pointeur réel (drags rapides, poignées 12 px, un
> undo par geste, scrub P6, molette P1) ; la capture d'aperçu (« figer ») ;
> les cas à deux onglets (« relancé ailleurs », route absente) ; les
> branches degraded/clé-requise hors mock. Résidu de test assumé sur le
> deck réel deck_e273a971 (graphe + job mock t2 + carte3d/solide3d.glb —
> gratuit, reproductible, non destructif).

- [x] Suite complète : `run-tests.ps1 -Filter cards` → tout vert ; `-Filter meshy` → vert.
- [x] `lint_cardforge.py` complet → 0 violation ; `--geom` et `--contract` → tenus.
- [x] `cf_deploy.ps1` : déployer, puis `-Check` → 0 écart. Redémarrer le backend
      installé (piège du processus orphelin sur :8765 — le tuer d'abord, sinon les
      réglages/routes restent d'hier).
- [x] **Vérification navigateur RÉELLE, zéro dépense** : poser `MESHY_MOCK=1` dans le
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
- [x] Mémoire du chantier : mettre à jour `cardforge-universel.md` (2b livrée, restes
      éventuels), et le plan (cases cochées, amendements à la source si des fautes de
      plan ont été trouvées en route).
- [x] Commit de clôture éventuel + PUSH de la branche du chantier.
- [x] Dire à l'utilisateur : la clé Meshy se colle dans Réglages (champ existant du
      3D Studio, `MESHY_API_KEY`) ; proposer — SANS le faire — un premier tir réel
      meshy-7 (30-35 cr) sur une carte de son choix.

---

## REVUE FINALE DE COUTURE (clôture de phase, 20/08 soir)

La leçon 2a re-confirmée : la revue d'ensemble a attrapé UN défaut de couture
invisible aux revues par tâche — **le placement « neutre » d'un plan écrasait
son z d'empilement** (editTrs semait z_mm: 0 ; _node_trs REMPLACE z_mm par
translate ; le graphe par défaut porte depth_mm jusqu'à 1,75 mm → un seul champ
édité aplatissait la parallaxe, GLB et STL d'accord entre eux et faux tous les
deux). Corrigé par la règle PARTAGÉE `zEmpilement(proc)` lue par le semis ET
l'affichage (la divergence des deux ÉTAIT le bug), épinglée par source + 14
assertions de harnais + mutant tué des deux côtés (25da56c, poussé). Aussi :
défauts servis rendus (jamais un champ vide qui ment), naissance d'un maillon
= repaint structurel, et le lint REFUSE les drapeaux inconnus (« un outil de
contrôle qui répond conforme à une question qu'il n'a pas comprise fabrique
de la preuve » — le réviseur de couture s'y était fait prendre lui-même).
Toutes les autres coutures marchées et déclarées PROPRES avec preuves :
contrats job.json producteur→consommateurs, chemin de l'argent bout en bout
(35 cr sans divergence à aucun saut), stabilité aller-retour du modèle de
graphe, writer (une seule transformation par chemin), composition R13/R14/
EXTRA_PY, l'accumulateur de molette 93987ab (session-puce) validé a
posteriori, résidu de test hors code. **Bilan final : 78 tests forge3d,
lint 9/9 0 violation, ~50 commits, phase 2b PRÊTE** (restes manuels de la
Task 8 : chatoiement visuel, bloc fluidité au pointeur réel, capture
d'aperçu, cas deux-onglets).

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
