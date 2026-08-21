# Cardforge Phase 2c — Le canvas nodal : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le « full redesign » demandé : les couches exportées deviennent des NŒUDS
sur un canvas pan/zoom, chaque nœud porte ses menus d'options ET une vignette qui
réagit immédiatement, les connexions se font à la souris (grammaire validée à
l'arête), un nœud artefact terminal montre le résultat dans son viewer, des nœuds
d'export s'y branchent au choix, et « Publier dans la Bibliothèque » fait entrer
l'artefact dans la Bibliothèque de l'app (onglet 3D, viewer/téléchargement/favoris/
Optimiser existants).

**Architecture:** spec §5.6 (lue et actée) — DOM+SVG vanilla, le graphe
`doc.forge3d.graph` reste LA vérité (vue liste conservée en bascule), positions
dans `doc.forge3d.layout` (présentation, patchée SANS undo), vignettes canvas 2D
déterministes par nœud + UN inspecteur model-viewer partagé (limite WebGL),
`POST /node-preview` borné pour le vrai 3D d'un seul élément, nœuds d'export =
vrais nœuds du graphe (kind `export`, ils n'éteignent rien — le bordereau reste
entier), Bibliothèque via JobRecord `provider="card3d"` + copie dans
`outputs/assets3d/{short}/` + patch bundle MINIMAL (2 filtres élargis) sur la
chaîne officielle.

**Tech Stack:** P9 existant (mod-forge3d.js 1705 l., forge3d.py 2168 l.,
forge3d_scene.py 1433 l., test_cards_forge3d.py 78 tests), model-viewer vendored,
chaîne de patchs bundle (scripts/reapply_inblock_patches.py, pièges connus).

**Références obligatoires :** préambule du plan phase 1 (harnais un-processus-par-
fichier, EOL/UTF-8 sans BOM, cf_deploy, interdits) + NOTE de revue Task 4 phase 1
(to_thread, bornes, jamais-500) + **règle d'argent 2b** : aucun test ni vérif ne
dépense (fal monkeypatché, Meshy sur MESHY_MOCK) + barre de fluidité §9.6 pour
TOUTE surface de drag du canvas. Bloc miroir NODE_KINDS : toute extension passe
par les DEUX côtés + test de parité. Gardes de génération (2b Task 7) : tout
chemin async qui écrit l'état de l'écran vérifie GEN après ses await.

---

## Structure de fichiers

| Fichier | Sort | Responsabilité |
|---|---|---|
| `frontend/cardforge/js/mod-forge3d.js` | Modifié (Tasks 2-5) | canvas, nœuds, arêtes, vignettes, inspecteur, exports, publier |
| `frontend/cardforge/css/mod-forge3d.css` | Modifié (Tasks 2-5) | surface, nœuds, ports, arêtes, inspecteur — scopé `.cf-forge3d` |
| `backend/app/services/cards/forge3d.py` | Modifié (Tasks 1, 4, 6) | node-preview, material-thumb, kind `export`, publier-bibliothèque |
| `backend/tests/test_cards_forge3d.py` | Modifié (toutes) | la preuve |
| `scripts/patch_bundle_card3d_library.py` | **Créé** (Task 6) | élargir les 2 filtres provider de la Bibliothèque |
| la chaîne de patchs (reapply) | Modifié (Task 6) | enregistrer le patch dans l'ordre officiel |

---

### Task 1: Backend — `node-preview` (le vrai 3D d'UN élément) + `material-thumb`

**Files:** forge3d.py, test_cards_forge3d.py.

- [ ] **Step 1 : tests en RED**

```python
def test_node_preview_construit_le_glb_du_seul_element():
    """POST /forge3d/node-preview {graph, card, nid} -> le GLB d'UN élément,
    grille de relief BORNÉE (aperçu rapide), réponse éphémère, jamais-500."""
    did = _deck("Preview noeud")
    _exporter_couches(did)
    g = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t1", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3,
         "grid": 256},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "x"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
             json={"graph": g, "card": 0, "nid": "t1"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("model/gltf-binary")
    doc, binv = _read_glb(r.content)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert [doc["nodes"][k]["name"] for k in racine["children"]] == ["cadre"]
    # la grille demandée (256) est PLAFONNÉE pour l'aperçu : le compte de
    # triangles est celui de RELIEF_GRID_PREVIEW, pas du grid max
    from app.services.cards import forge3d as F9
    from app.services.cards import forge3d_scene as SC
    m = SC.glb_scene_mesh(r.content)
    gy = max(2, round(F9.RELIEF_GRID_PREVIEW * (88.0 / 63.0)))
    attendu = 4 * F9.RELIEF_GRID_PREVIEW * gy + 4 * F9.RELIEF_GRID_PREVIEW + 4 * gy
    assert len(m["indices"]) // 3 == attendu
    # un nœud mesh3d SERVI -> les octets du GLB du job, tels quels
    relief = SC.relief_mesh(__import__("PIL.Image", fromlist=["Image"])
                            .new("L", (8, 8), 255), 63.0, 88.0, 1.0, 0.3, 4)
    relief["closed"] = True
    png = io.BytesIO()
    Image.new("RGBA", (4, 4), (9, 9, 9, 255)).save(png, "PNG")
    glb_job = SC.write_scene_glb([{"name": "brut", "mesh": relief,
                                   "png": png.getvalue(), "alpha": False,
                                   "z_mm": 0.0}], name="b", extras={})
    _job_servi(did, "m1", glb_job, closed=True)
    g2 = _graphe_mesh3d("meshy-7")
    r2 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r2.status_code == 200 and r2.content == glb_job
    # refus nommés : mesh3d non servi -> 409 « servi » ; nid inconnu -> 400 ;
    # kind non prévisualisable (layer/assemble) -> 400 nommé
    _reset_node(did, "m1")          # helper : rmtree du dossier nœud
    r3 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g2, "card": 0, "nid": "m1"})
    assert r3.status_code == 409 and "servi" in r3.json()["detail"]
    r4 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g, "card": 0, "nid": "zzz"})
    assert r4.status_code == 400
    r5 = _api("POST", f"/api/cards/{did}/forge3d/node-preview",
              json={"graph": g, "card": 0, "nid": "asm"})
    assert r5.status_code == 400 and "prévisualisable" in r5.json()["detail"] \
        or r5.status_code == 400


def test_material_thumb_est_servi_par_provenance():
    from app.services import material_store as MSTORE
    mat = MSTORE.create_material(name="vignette-2c")
    try:
        MSTORE.write_thumb(mat["id"], _png(Image.new("RGBA", (64, 64),
                                                     (10, 200, 10, 255))))
        did = _deck("Thumb")
        r = _api("GET", f"/api/cards/{did}/forge3d/material-thumb/{mat['id']}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")
        # mid invalide -> 400 ; matière sans vignette -> 404 nommé
        r2 = _api("GET", f"/api/cards/{did}/forge3d/material-thumb/..%2Fx")
        assert r2.status_code in (400, 404)
        m2 = MSTORE.create_material(name="sans-vignette")
        try:
            r3 = _api("GET",
                      f"/api/cards/{did}/forge3d/material-thumb/{m2['id']}")
            assert r3.status_code == 404
        finally:
            MSTORE.delete_material(m2["id"])
    finally:
        MSTORE.delete_material(mat["id"])
```
(Adapter les helpers aux conventions réelles du fichier — `_job_servi`,
`_exporter_couches`, `_graphe_mesh3d`, `_png`, `_read_glb` existent ; `_reset_node`
est à écrire (3 lignes, rmtree du dossier nœud). VÉRIFIER la signature réelle de
`write_thumb` avant d'écrire le test — le code réel fait foi.)

Run : run-tests -Filter cards_forge3d → FAIL (routes absentes).

- [ ] **Step 2 : implémentation**

`forge3d.py` :
```python
RELIEF_GRID_PREVIEW = 96      # l'aperçu d'UN nœud privilégie la vitesse : le
                              # vrai grid ne joue qu'au build (2a : 256 max)
```
`POST /node-preview` — points imposés (patrons du fichier, NOTE de revue) :
- gardes deck 400/404, `clean_graph`, `nid` présent sinon 400 nommé ;
- kind du nœud : `plane`/`relief` → sous-graphe {sa couche source, lui, un
  assemble+artifact synthétiques} passé à `_resolve_graph_elements` (réutiliser
  `_chaine_aval` pour embarquer matière/placement de SA chaîne — l'aperçu montre
  l'option choisie) ; `grid` plafonné à `RELIEF_GRID_PREVIEW` AVANT résolution ;
  `write_scene_glb` sur CE seul élément ; `Response(content=glb,
  media_type="model/gltf-binary")` ; tout le travail en `asyncio.to_thread` ;
- `mesh3d` → job servi exigé (409 « le nœud {nid} n'a pas servi son GLB — 
  lance-le d'abord », même formulation que build3d) ; streamer les octets de
  `nodes/{nid}/model.glb` (borne `MAX_EXT_GLB_BYTES` déjà gardée par le job) ;
- autres kinds → 400 nommé (« nœud non prévisualisable : {kind} ») ;
- AUCUNE écriture disque (réponse éphémère).

`GET /material-thumb/{mid}` : `material_store.is_valid_mid` sinon 400 ;
chemin de vignette via material_store (lire comment `write_thumb` nomme le
fichier) ; absent → 404 nommé ; `FileResponse` image. Jamais-500.

- [ ] **Step 3 : GREEN + lint + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): node-preview borne (le vrai 3D d un element) + material-thumb par provenance"
```

---

### Task 2: Le canvas — surface pan/zoom, nœuds positionnés, arêtes SVG, layout sans undo

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py.

- [ ] **Step 1 : test de source en RED**

```python
def test_le_canvas_est_la_projection_du_meme_graphe():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # la surface, la bascule liste/canvas, le layout dans le doc
    assert 'id="cf-forge3d-canvas"' in rendu
    assert "layout" in rendu and 'get("layout"' in rendu
    # les positions sont de la PRÉSENTATION : patchées SANS entrée d'annulation
    corps = rendu.split("function flushLayout(")[1].split("\n  }")[0]
    assert "M.patch" in corps and "HIST" not in corps
    # drag de nœud coalescé au rAF (spec 9.6) + geste exact au relâché
    assert "scheduleFrame" in rendu and "cancelFrame" in rendu
    # l'auto-arrangement est DÉTERMINISTE (colonnes par kind, pas de hasard)
    assert "function seedLayout(" in rendu and "Math.random" not in rendu
    # les arêtes sont UNE couche SVG sous les nœuds
    assert "cf-forge3d-edges" in rendu and "path" in rendu
    # la vue liste SURVIT (bascule) — les pins 2a/2b restent valables
    assert "graphRows(graph)" in rendu
    assert "cf-forge3d-vue" in rendu
```

- [ ] **Step 2 : implémentation** (patrons du fichier ; lire d'abord
`shell()/wire()/paintGraph()` et le schéma `CF.register` du module)

1. **Schéma** : la déclaration `CF.register` du module gagne la clé `layout`
   (dict `{nid: [x, y]}`, nombres bornés 0..20000 au flush). `get("layout")`.
2. **Bascule** `#cf-forge3d-vue` (canvas | liste), persistée en
   `localStorage("dz_cf_forge3d_vue")` — présentation, pas doc. La vue liste =
   l'existant, INTOUCHÉE.
3. **Surface** `#cf-forge3d-canvas` : conteneur `position:relative` clippé,
   monde interne translaté/zoomé (`transform: translate(px,py) scale(z)` sur un
   enfant `.cf-forge3d-monde`) ; pan = drag du fond (rAF-coalescé, état local,
   pas de doc) ; zoom = molette AVEC accumulateur local (le patron 93987ab de
   mod-face : base capturée au début de rafale, point-sous-curseur préservé,
   flush au rAF) ; `touch-action: none` sur la surface.
4. **Nœuds** : divs `.cf-forge3d-noeud[data-nid]` absolument positionnées depuis
   `layout` ; `seedLayout(graph)` place les manquants en COLONNES par kind
   (layer x=40, traitement x=280, matière/placement x=520, assemble x=760,
   artifact x=1000, export x=1240 ; y = 40 + 190·rang dans sa colonne) —
   déterministe, zéro aléa.
5. **Drag de nœud** : pointerdown sur l'en-tête du nœud (pas ses champs) →
   `isPrimary` gate, position locale par événement (feedback immédiat via
   style.left/top), `flushLayout()` au rAF = UN `M.patch({layout})` par frame,
   flush EXACT au pointerup — **sans entrée HIST** (commentaire : « la position
   est de la présentation — l'annulation appartient au CONTENU du graphe »).
6. **Arêtes** : un `<svg class="cf-forge3d-edges">` sous les nœuds, un `<path>`
   bézier par arête du graphe (sortie droite du nœud from → entrée gauche du
   nœud to), repeint sur layout/graph. `esc()` partout où un id entre dans le
   DOM (R14 garde les attributs).
7. CSS : surface (fond quadrillé discret aux jetons du thème), nœud (carte
   sombre, en-tête par kind, ombre à la sélection), ports, arêtes
   (`stroke: var(--stroke)`, hover accent) — tout scopé `.cf-forge3d`.

- [ ] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): canvas nodal - surface pan/zoom, noeuds depuis layout sans undo, aretes svg, bascule liste conservee"
```

---

### Task 3: Les corps de nœuds — menus embarqués + vignettes réactives

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py.

- [ ] **Step 1 : test de source en RED**

```python
def test_chaque_noeud_porte_ses_menus_et_sa_vignette_reactive():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # les MÊMES bâtisseurs de champs servent la liste ET le canvas (zéro
    # duplication de balisage) : le corps du nœud appelle les blocs existants
    corps = rendu.split("function nodeBodyHtml(")[1].split("\n  }")[0]
    for bloc in ("mesh3dHtml", "matHtml", "trsHtml"):
        assert bloc in corps, bloc
    # la vignette est un canvas 2D DÉTERMINISTE repeint au changement d'option
    assert "function paintNodeThumb(" in rendu
    assert "cf-forge3d-thumb" in rendu and "Math.random" not in rendu
    # mesh3d : le preview.png du job quand servi, la chip d'état sinon
    assert "preview" in rendu and "chipHtml" in rendu
    # matière : la vignette de la boutique par la route de provenance
    assert "material-thumb/" in rendu
```

- [ ] **Step 2 : implémentation**

1. **Réutilisation stricte** : `nodeBodyHtml(nid)` compose les bâtisseurs
   EXISTANTS (`mesh3dHtml`/`matHtml`/`trsHtml`/le sélecteur de traitement/les
   champs profondeur) — si un bâtisseur suppose la rangée, le paramétrer par
   hôte (`hote: "row"|"node"`), JAMAIS dupliquer le balisage des champs. Les
   handlers d'édition existants (`editGraph`/`editMat`/`editTrs`) marchent par
   `data-*` — vérifier qu'ils remontent depuis le canvas aussi (délégation au
   conteneur commun).
2. **Vignette** `paintNodeThumb(nid)` — canvas 2D 120×168 (ratio carte),
   DÉTERMINISTE, locale :
   - `layer` : la PNG de couche (blob par provenance `M.api.blob("GET",
     "file/…")`, cache par (rôle, côté, carte)) ;
   - `plane` : la couche + légère perspective CSS (classe) ;
   - `relief` : la couche + ombrage d'emboss proportionnel à `depth_mm`
     (double drawImage décalé teinté — pur canvas 2D) ;
   - `material` : la vignette boutique (`material-thumb/{mid}`) en fond +
     bandeau finition (dégradé holo CSS pour argent/dorure, badge « aniso ») ;
   - `mesh3d` : `nodes/{nid}` servi → le preview.png du job (des jobs meshy) ou
     à défaut un pictogramme moteur + la chip d'état (réutiliser `chipHtml`) ;
   - `transform` : la couche avec le décalage x/y/rotation esquissé (trait) ;
   - `artifact`/`export` : pictogrammes fixes + états (Task 5).
   Repeinte par les hooks d'édition existants (là où `paintRow` est déclenché,
   déclencher aussi la vignette du nid touché). AUCUN aléa, AUCUN réseau autre
   que les blobs de provenance déjà en cache.
3. Les polls (`pollMesh3d`) repeignent la chip dans LES DEUX vues (le sélecteur
   de zone chip devient indépendant de l'hôte).

- [ ] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): corps de noeuds - menus reutilises tels quels, vignettes canvas 2d reactives, chips partagees"
```

---

### Task 4: Les connexions à la souris + le kind `export` (miroir)

**Files:** mod-forge3d.js, forge3d.py, test_cards_forge3d.py.

- [ ] **Step 1 : tests en RED**

```python
def test_le_vocabulaire_gagne_export_des_deux_cotes():
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-NODES-BEGIN")[1].split("CF-FORGE3D-NODES-END")[0]
    js_rows = re.findall(r'\{ kind: "([a-z0-9]+)", params: \[([^\]]*)\] \}', bloc)
    js_table = [{"kind": k, "params": [p.strip().strip('"') for p in ps.split(",") if p.strip()]}
                for k, ps in js_rows]
    assert js_table == F9.NODE_KINDS
    assert [r["kind"] for r in F9.NODE_KINDS] == [
        "layer", "plane", "relief", "mesh3d", "material", "transform",
        "assemble", "artifact", "export"]


def test_clean_graph_borne_le_noeud_export():
    from app.services.cards import forge3d as F9
    g = {"nodes": [{"id": "e1", "kind": "export", "format": "stl"},
                   {"id": "e2", "kind": "export", "format": "warp"}],
         "edges": []}
    out = F9.clean_graph(g)
    n = {x["id"]: x for x in out["nodes"]}
    assert n["e1"]["format"] == "stl"
    assert n["e2"]["format"] == "glb"      # défaut sur format inconnu
    # le résolveur les IGNORE sans les avouer en erreur (ce sont des points de
    # téléchargement, pas des éléments) — build3d inchangé
```

Et le test de source (grammaire des connexions) :
```python
def test_les_connexions_valident_la_grammaire_a_l_arete():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # la table de grammaire est UNIQUE et nommée ; un refus est un toast NOMMÉ
    assert "GRAMMAIRE" in rendu and "function lienValide(" in rendu
    corps = rendu.split("function lienValide(")[1].split("\n  }")[0]
    for regle in ("layer", "assemble", "artifact", "export"):
        assert regle in corps or regle in rendu
    # créer/supprimer une arête passe par setGraph (annulable, HIST)
    assert "function creeLien(" in rendu and "setGraph" in rendu
    assert "function suppLien(" in rendu
    # le drag de port est gardé isPrimary et coalescé
    assert "cf-forge3d-port" in rendu
```

- [ ] **Step 2 : implémentation**

Backend (forge3d.py) : miroir `NODE_KINDS` += `{"kind": "export", "params":
["format"]}` (les DEUX côtés) ; `EXPORT_FORMATS = ("glb", "stl", "metadata",
"preview")` ; branche `clean_graph` (format validé sinon "glb") ;
`_resolve_graph_elements` : les nœuds `export` (et leurs arêtes depuis
`artifact`) sont IGNORÉS sans entrée `ignored` (commentaire : « points de
téléchargement — ils n'éteignent rien, le bordereau reste entier ») ; parité
mise à jour (l'assert d'ordre 2b est REMPLACÉ par le nouveau — une seule
source).

Écran :
1. **Ports** : sortie (droite) et entrée (gauche) par nœud selon son kind ;
   `pointerdown` sur un port (isPrimary) → arête fantôme suivie au rAF ;
   relâché sur un port d'entrée → `lienValide(fromKind, toKind)` d'après la
   table `GRAMMAIRE` unique : layer→(plane|relief|mesh3d) ;
   (plane|relief|mesh3d)→(material|transform|assemble) ;
   material→(transform|assemble) ; transform→(assemble) ;
   assemble→(artifact) ; artifact→(export). Valide → `creeLien` (setGraph,
   HIST une entrée) ; invalide → toast NOMMÉ (« un {from} ne se branche pas
   sur un {to} — chaîne attendue : … ») et rien n'est écrit.
2. **Suppression** : clic sur une arête → surlignage + bouton « supprimer »
   flottant → `suppLien` (setGraph). Échap annule.
3. La palette (Task 5) fournit les nœuds à connecter ; `rewireRow` (vue liste)
   et `creeLien`/`suppLien` (canvas) écrivent le MÊME graphe — le harnais de
   chaînes est ÉTENDU : créer un lien au canvas puis lire `rowModel` rend la
   même chaîne (aller-retour stable).

- [ ] **Step 3 : GREEN + harnais + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): connexions port-a-port validees a l arete (grammaire nommee), kind export en miroir - le bordereau reste entier"
```

---

### Task 5: L'inspecteur partagé, le nœud artefact, les nœuds d'export, la palette

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py.

- [ ] **Step 1 : test de source en RED**

```python
def test_l_inspecteur_est_unique_et_l_artefact_rend_dans_son_noeud():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # UN seul inspecteur model-viewer (limite WebGL) : sélection -> node-preview
    assert 'id="cf-forge3d-inspecteur"' in rendu
    corps = rendu.split("async function inspecte(")[1].split("\n  }")[0]
    assert 'node-preview' in corps and "gen" in corps      # garde de génération
    # le nœud artefact : Construire + le viewer du RÉSULTAT + figer l'aperçu
    assert "function artifactNodeHtml(" in rendu
    assert "build3d(" in rendu and "freezePreview" in rendu
    # les nœuds d'export : écrit/refusé au motif LITTÉRAL + téléchargement
    # par provenance — jamais un nœud muet
    assert "function exportNodeHtml(" in rendu
    assert "grabZip(" in rendu or "M.api.blob" in rendu
    # la palette nomme ce qui peut naître (couches restantes, traitements,
    # matière, placement, exports) et respecte max_elements
    assert 'id="cf-forge3d-palette"' in rendu and "max_elements" in rendu
```

- [ ] **Step 2 : implémentation**

1. **Inspecteur** `#cf-forge3d-inspecteur` (panneau latéral du canvas) : UN
   model-viewer ; sélection d'un nœud (clic en-tête) → `inspecte(nid)` : garde
   de génération, POST `node-preview` par `M.api.raw`, blob → objectURL
   (révoquer l'ancienne — patron mountPreview), états busy/erreur LITTÉRALE ;
   les kinds non prévisualisables affichent le motif du backend tel quel.
2. **Nœud artefact** : `artifactNodeHtml` — nom éditable (champ existant),
   bouton Construire (le `build3d()` existant, garde GEN), le viewer du
   résultat MONTÉ DANS le nœud (retarget de `mountPreview` vers l'hôte nœud —
   c'est le 2e et DERNIER contexte WebGL), « figer l'aperçu » conservé,
   résumé du bordereau (poids, moteurs, crédits consommés) + `ignored`.
3. **Nœuds d'export** : `exportNodeHtml(format)` — état depuis le DERNIER
   bordereau (`ARTIFACT`) : `glb` poids + bouton (grabZip), `stl` écrit/refusé
   au MOTIF littéral, `metadata` poids + bouton, `preview` attendu/écrit.
   Un export sans build encore : « construis d'abord » (état, pas une erreur).
4. **Palette** `#cf-forge3d-palette` : boutons « + couche » (celles du manifeste
   pas encore sources), « + traitement », « + matière », « + placement »,
   « + export (format) » — chaque naissance = `setGraph` (HIST) + seedLayout
   pour SA position ; plafond `graph_limits.max_elements` nommé (message
   existant de la 2b).
5. Les gardes 2b restent : prix AVANT au pied (le canvas l'affiche aussi),
   `has_meshy`/degraded, polls, run_id.

- [ ] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): inspecteur 3d unique, noeud artefact avec son viewer, noeuds d export au motif litteral, palette bornee"
```

---

### Task 6: La Bibliothèque — publier l'artefact + le patch bundle minimal

**Files:** forge3d.py, test_cards_forge3d.py, scripts/patch_bundle_card3d_library.py (créé), la chaîne de patchs, mod-forge3d.js (le bouton).

- [ ] **Step 1 : tests en RED (backend)**

```python
def test_publier_dans_la_bibliotheque_est_idempotent():
    """POST /forge3d/library/{art} : JobRecord provider=card3d + copie dans
    outputs/assets3d/{short}/ pour que les routes EXISTANTES servent ;
    re-publier MET À JOUR, ne duplique pas."""
    did = _deck("Bibliotheque")
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
    r = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d")
    assert r.status_code == 200
    pub = r.json()
    assert pub["provider"] == "card3d" and pub["short"]
    # le GLB est servi par la route EXISTANTE de la Bibliothèque 3D
    r2 = _api("GET", f"/api/assets/3d/{pub['short']}/glb")
    assert r2.status_code == 200 and r2.content[:4] == b"glTF"
    # idempotent : même artefact -> même id, pas de doublon
    r3 = _api("POST", f"/api/cards/{did}/forge3d/library/carte3d")
    assert r3.json()["job_id"] == pub["job_id"]
    # le JobRecord existe, provider card3d, status done
    # (lecture par la route /api/jobs — patron des tests app existants)
    jobs = _api("GET", "/api/jobs").json()
    moi = [j for j in jobs if j.get("job_id") == pub["job_id"]
           or j.get("id") == pub["job_id"]]
    assert moi and moi[0]["provider"] == "card3d"
    # sans build -> 409 nommé
    r4 = _api("POST", f"/api/cards/{did}/forge3d/library/jamais-construit")
    assert r4.status_code == 409
```
(Adapter la lecture de /api/jobs à la forme réelle de sa réponse — la lire
d'abord. Si `_api` ne couvre que les routes deck-scopées, vérifier comment les
tests existants atteignent les routes app — le TestClient de l'app couvre tout.)

- [ ] **Step 2 : la route**

`POST /forge3d/library/{art}` — points imposés :
- gardes deck ; `{art}.glb` doit exister sous `forge3d/` sinon 409
  (« construis l'artefact d'abord ») ;
- `job_id = uuid5(NAMESPACE_CARD3D, f"{did}/{art}")` (déterministe = idempotence
  par construction ; `NAMESPACE_CARD3D = uuid.UUID("...")` constante nommée) ;
  `short = job_id.hex[:8]` ;
- copie `{art}.glb` → `outputs/assets3d/{short}/model.glb`,
  `{art}_preview.png` → `preview.png` si présent (sinon pas de fichier — la
  vignette de la Bibliothèque tolère l'absence) ; `metadata` copié aussi
  (`{art}.metadata.json` → `metadata.json`, bonus honnête) ;
- upsert `JobRecord(id, provider="card3d", status done, title=f"Carte 3D · "
  f"{nom_deck} · {art}", final_video_path=chemin glb copié, image_filename=
  "preview.png" si copiée, cost_meta json {deck: did, art, engines, files})` —
  upsert = get puis update, sinon insert (l'idempotence du test) ;
- réponse `{job_id, short, provider}` ; to_thread pour les copies ; jamais-500.

Écran : bouton « Publier dans la Bibliothèque » sur le nœud artefact (et le
bordereau liste), garde GEN, toast succès avec le titre publié, état
« publié » persistant dans le bordereau affiché.

- [ ] **Step 3 : le patch bundle (chaîne officielle)**

`scripts/patch_bundle_card3d_library.py`, style des patchers existants (en LIRE
un d'abord + relire la mémoire des pièges : source en LF, ancres exactes,
inventaire de fonctions après) :
- ancre 1 : `return z.provider==="asset3d"});setJobs(L)` →
  `return z.provider==="asset3d"||z.provider==="card3d"});setJobs(L)` ;
- ancre 2 : `T3=u.filter(C=>C.provider==="asset3d"&&C.status==="done")` →
  `T3=u.filter(C=>(C.provider==="asset3d"||C.provider==="card3d")&&C.status==="done")` ;
- chaque ancre UNIQUE dans le bundle (le vérifier AVANT d'écrire), échec du
  patch = message nommé, jamais un bundle à moitié patché ;
- enregistrer dans la chaîne de ré-application (lire
  `scripts/reapply_inblock_patches.py` et suivre SON registre) ;
- test du patcher : sur une COPIE du bundle, exécuter, asserter 2 remplacements
  et l'idempotence (re-exécuter → 0 changement, pas de double-patch).
- Appliquer au bundle du DÉPÔT (frontend/dist) + commit. Le déploiement vers
  l'app = Task 7.

- [ ] **Step 4 : GREEN + lint + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py scripts/patch_bundle_card3d_library.py scripts/reapply_inblock_patches.py frontend/dist frontend/cardforge/js/mod-forge3d.js
git commit -m "feat(cardforge): publier dans la bibliotheque - JobRecord card3d idempotent servi par les routes 3d existantes + patch bundle des 2 filtres"
```

---

### Task 7: Intégration finale 2c

- [ ] Suite complète `-Filter cards` → 10/10 ; `-Filter meshy` → vert ; lint
      intégral → 0 (R4 sur le nouveau CSS, R13, R14) ; `--geom` 4/4.
- [ ] `cf_deploy.ps1 -Backend` + `-Check` → 0 écart ; déployer AUSSI le bundle
      patché vers l'app (suivre le flux app-tree : copier `frontend/dist` —
      lire comment les déploiements bundle précédents l'ont fait) ; redémarrer.
- [ ] `MESHY_MOCK=1` posé (retiré à la fin, à l'octet près — patron 2b Task 8).
- [ ] **Vérification navigateur RÉELLE, zéro dépense** : export → BASCULE
      CANVAS → les couches sont là en nœuds ; glisser un nœud (fluide, pas
      d'undo pollué) ; pan/zoom ; connecter layer→relief à la souris ;
      connexion invalide → toast nommé ; changer profondeur → la vignette
      réagit ; matière + finition → vignette teintée + badge ; sélection →
      l'inspecteur montre le VRAI 3D du nœud ; mesh3d meshy-7 : prix sur le
      nœud, Lancer (mock), chip → servi, vignette = preview du job ;
      Construire au nœud artefact → viewer du résultat DANS le nœud ; nœuds
      d'export : GLB télécharge, STL affiche le refus motivé (mock ouvert) ;
      « figer l'aperçu » ; « Publier dans la Bibliothèque » → aller dans la
      BIBLIOTHÈQUE de l'app : l'artefact est dans l'onglet 3D, viewer tourne,
      téléchargement OK ; re-publier → pas de doublon. AUSSI (restes 2b) :
      tourner le viewer pour le CHATOIEMENT holo (dire ce qui est VU), sentir
      la fluidité des cadres au pointeur réel. Captures d'écran aux moments
      clés. Rapporter TOUT ce qui est vu, y compris ce qui déçoit.
- [ ] Mémoire + plan (cases, notes) + push.

---

## Auto-revue du plan

- **Exigences utilisateur couvertes** : couches en nœuds (T2-T3), menus complets
  par nœud (T3, réutilisation stricte), visualisation immédiate par nœud (T3
  vignettes + T5 inspecteur vrai-3D), connexions à la souris (T4), nœud artefact
  avec le résultat (T5), nœuds d'export au choix (T4 kind + T5 UI), Bibliothèque
  (T6 + patch). Spec §5.6 = la source ; toute divergence découverte s'amende À LA
  SOURCE (leçon ×5 de la 2b).
- **Placeholders** : les corps de routes/UI renvoient aux patrons NOMMÉS du
  fichier avec exigences fixées par les tests fournis (convention 2a/2b) ; les
  deux ancres bundle sont citées TEXTUELLEMENT depuis le bundle lu le 20/08.
- **Types** : `layout {nid: [x,y]}` (T2) lu par seedLayout/flushLayout/arêtes ;
  `EXPORT_FORMATS` (T4) consommé par exportNodeHtml (T5) ; `node-preview`
  (T1) consommé par inspecte (T5) ; publier (T6) rend `{job_id, short,
  provider}` consommé par le toast.
- **Risques nommés** : contextes WebGL (2 max par construction) ; le patch
  bundle (ancres uniques vérifiées avant, idempotence testée, chaîne
  officielle) ; la délégation d'événements des menus embarqués (T3 vérifie que
  les handlers remontent) ; forge3d.py ~2168 l. + ~300 → surveiller le seuil
  ~2400 (la couture routes est identifiée si besoin : bloc bibliothèque).
- **Argent** : rien ne dépense — mock partout, fal jamais lancé.
