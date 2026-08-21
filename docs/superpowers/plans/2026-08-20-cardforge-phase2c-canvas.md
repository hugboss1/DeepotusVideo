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

- [x] **Step 1 : tests en RED**

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

- [x] **Step 2 : implémentation**

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
  `nodes/{nid}/model.glb`. **AMENDÉ EN REVUE (la parenthèse d'origine « borne
  déjà gardée par le job » était FAUSSE — l'asymétrie I4 de la 2b laisse un
  job fal servi dépasser 64 Mo)** : borne PROPRE `MAX_APERCU_GLB_BYTES`
  (32 Mio — ce qu'un clic envoie dans model-viewer, pas la borne de fusion),
  mesurée sans lire le contenu, refus 409 nommé pointant vers le nœud
  artefact ; en-dessous, `FileResponse` (jamais read_bytes en RAM) ;
- autres kinds → 400 nommé (« nœud non prévisualisable : {kind} ») ;
- AUCUNE écriture disque (réponse éphémère).

`GET /material-thumb/{mid}` : `material_store.is_valid_mid` sinon 400 ;
chemin de vignette via material_store (lire comment `write_thumb` nomme le
fichier) ; absent → 404 nommé ; `FileResponse` image. Jamais-500.

- [x] **Step 3 : GREEN + lint + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): node-preview borne (le vrai 3D d un element) + material-thumb par provenance"
```

---

### Task 2: Le canvas — surface pan/zoom, nœuds positionnés, arêtes SVG, layout sans undo

> **CLOSE (b6c3fc5 + 521d5bd + d41b528, re-revue OK).** Amendements actés : le
> drag ne peut plus raser le layout (DRAG nul aux trois vidages — dont une
> route trouvée par l'implémenteur), filtre pointerId sur move/up, arêtes
> INCIDENTES seules par frame, **flush au relâché** (décision : un patch par
> frame cascadait invalidate→drawPreview, un re-rendu complet de la carte pour
> un geste qui ne change pas un pixel), épingle 2a AMENDÉE À LA SOURCE
> (paintVue — la lettre du pin forçait la duplication qu'il existait pour
> empêcher), et la régression du durcissement M7 fermée : `__proto__` jamais
> patché (la reconstruction `{}` du CORE reparentait l'objet puis jetait à
> chaque doc() — onglet brické ; reproduit en node avant correction, épinglé
> par regex). Restes à T7 (navigateur) : ressenti pan/zoom/drag, plancher de
> zoom, cadrage recentrer.

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py.

- [x] **Step 1 : test de source en RED**

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

- [x] **Step 2 : implémentation** (patrons du fichier ; lire d'abord
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

- [x] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): canvas nodal - surface pan/zoom, noeuds depuis layout sans undo, aretes svg, bascule liste conservee"
```

---

### Task 3: Les corps de nœuds — menus embarqués + vignettes réactives

> **CLOSE (ff0d434 + a072e74, re-revue APPROUVÉE).** Réutilisation prouvée à
> l'octet (vue liste inchangée), zéro duplication épinglée par comptage des
> data-field, paintNode chirurgical, vignettes déterministes par genre, chips
> indépendantes de l'hôte, cache d'images RETAILLÉ (154×) et invalidé
> honnêtement (flush par face + re-sonde 30 s des matières y compris les 404
> mémorisés — le no-store du backend est un ordre), side repeint l'en-tête,
> saisie tapée dessinée sous le curseur (SAISIE synchrone), thème observé.
> Trou preview.png ACCORDÉ à la T5 (route node-file à liste blanche). 17/17
> mutants + ancre-contrôle survivante. **Suivis pliés en tête de T4** : époque
> d'images (IMGS_EPOQUE) contre le chargeur en vol qui réécrit des octets
> pré-export ; commentaire M11 ramené au vrai (le voisin n'était PAS
> atteignable — la valeur du changement est la doctrine, pas un bug corrigé) ;
> 3 asserts de site d'appel (oublieLesImages dans exportLayers,
> reSondeLesMatieres dans paintCanvas, retaille dans chargeImage) ; le
> commentaire M8 dit « n'importe quelle écriture », pas « un patch de
> layout ».

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py.

> **LIVRÉ (ff0d434).** 85 tests (84 + 1), lint 0, `--geom` 4/4,
> `node --check` OK. Amendements actés, tous à la SOURCE :
> · le pas de semis FIXE de la T2 (RANG_DY = 120) devenait un CHEVAUCHEMENT
>   dès que les corps portaient vignette + menus — il devient contenu-dépendant
>   (`RANG_H` par kind, généreux : sous-estimer chevauche, surestimer ne coûte
>   que du blanc), et « recentrer » MESURE désormais la vraie boîte
>   (`hauteurNoeud`) au lieu de croire la table ;
> · `matHtml`/`trsHtml` gagnent `hote: "row"|"node"` — l'emballage seul change
>   (tiroir dans la liste, champs nus dans le nœud), les champs sont les mêmes
>   octets ; `procSelHtml`/`geoHtml`/`sideSelHtml` extraits de `rowHtml` ;
> · la délégation passe de `.cf-forge3d-row` à `[data-proc]` : un corps de
>   nœud matière/placement y met l'id de SON traitement, donc `editMat`/
>   `editTrs` marchent depuis le canvas sans une ligne de plus ;
> · `paintChip` repeint AUSSI la vignette (elle porte le même état lu du job)
>   et `repeintChaine` suit la chaîne (changer la FACE d'une couche change la
>   PNG que son traitement ET son placement dessinent) ;
> · repeint des vignettes COALESCÉ au rAF (sept images reviennent dans la même
>   poignée de frames — un balayage complet par arrivée croissait avec le
>   graphe, la faute déjà corrigée sur `majAretes`).
> **MANQUE REMONTÉ AU CONTRÔLEUR (Task 5)** : le `preview.png` d'un job meshy
> vit sous `nodes/{nid}/` et AUCUNE route ne le sert — `GET /file/{name}`
> valide sur `^[A-Za-z0-9._-]{1,90}$`, séparateur interdit. La branche « à
> défaut » du plan s'applique (pictogramme moteur + état lu) ; ouvrir une
> route en douce depuis l'écran aurait été décider seul d'une surface d'API.
> Restes à T7 (navigateur) : la justesse des hauteurs de `RANG_H` à l'œil, le
> cadrage d'un graphe à six couches (~1,5 k px de colonne, plancher de zoom),
> la lisibilité des menus à 200 px de large.

- [x] **Step 1 : test de source en RED**

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

- [x] **Step 2 : implémentation**

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

- [x] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): corps de noeuds - menus reutilises tels quels, vignettes canvas 2d reactives, chips partagees"
```

---

### Task 4: Les connexions à la souris + le kind `export` (miroir)

> **CLOSE (9418a50 + cec5042, re-revue APPROUVÉE).** La GRAMMAIRE est UNE table
> à trois lecteurs (validation, ports DÉRIVÉS, texte du toast) et l'acyclicité
> est PROUVÉE par sa structure de rangs. Correctifs de revue : **un maillon
> n'appartient qu'à une chaîne** (cible déjà prise = refus AVANT écriture —
> le partage acceptait exactement le lien qui faisait qu'une rangée jamais
> touchée cessait d'être construite en silence ; le mutant retournait un
> graphe, la preuve accept-puis-avoue) ; le contrôle ne s'aveugle plus sur une
> chaîne sans couche (marche amont vers le proc + rowModel) ; « couper puis
> rebrancher » vérifié fonctionnel (aucun geste légitime coûté) ;
> export_formats épinglé ; commentaires ramenés au vrai (le `in` de tuple ne
> hache pas). 35 cas de banc, 10/10 mutants + contrôle survivant, ports au
> pixel (calc − bord). **Reports T5** : l'éventail résiduel t1→m9 (accepté,
> honnête à l'écran « matière hors chaîne » — la palette le rendra trivial,
> décider refus-ou-état) ; la sélection d'arête vs SEL (asymétrie à trancher
> avec l'inspecteur) ; une phrase au commentaire CHAIN_MAX (garde d'API brute
> seulement). **Reports T7** : empilement des zones de saisie aux convergences,
> port 14 px sous z≈0,86, ressenti du fil, bouton sur arête courte.

**Files:** mod-forge3d.js, mod-forge3d.css, forge3d.py, test_cards_forge3d.py.
(La feuille s'ajoute à la liste du plan : la Task 4 est ce qui PAIE la dette
CSS nommée en Task 2 — zone de saisie des arêtes et pastilles de ports.)

> **LIVRÉ.** 88 tests (85 + 3), lint 0 violation, `--geom` 4/4, `node --check`
> OK ; 10 mutants tués + ancre-contrôle survivante. Décisions et amendements,
> tous à la SOURCE :
> · **une table, trois lecteurs** : `GRAMMAIRE` sert la validation
>   (`lienValide`), les PORTS (`aEntree`/`aSortie` s'en DÉDUISENT — pas de
>   seconde liste « qui a quel port » à tenir d'accord) et le TEXTE du refus
>   (`chaineAttendue` marche la table et rend « couche → plan | relief |
>   mesh 3D → matière | placement | assemblage → artefact → export ») ;
> · **moitié pure / moitié qui écrit** : `grapheAvecLien`/`grapheSansLien`
>   rendent un graphe ou un motif et ne touchent à rien — c'est ce qui les
>   rend JUGEABLES. Le harnais de chaînes (nouveau, dans le test : extraction
>   des VRAIES fonctions du fichier livré + node) mesure l'aller-retour
>   canvas → `rowModel`/`graphRows` → `rewireRow`, dont l'idempotence de
>   l'écrivain de la vue liste sur un graphe câblé à la souris. Le test
>   n'épingle qu'un PLANCHER de cas (un banc amputé passerait sinon en vert
>   sans rien mesurer) : geler le compte exact condamnerait chaque cas
>   ajouté à toucher deux endroits — et la première rédaction de cette note
>   s'était déjà trompée de deux ;
> · **le refus précède l'écriture** (jamais créer-puis-avouer) : grammaire,
>   puis SURNOMBRE avec les mots du bordereau (source surnuméraire, seconde
>   matière, second placement) ; un DOUBLON n'est ni refus ni écriture (rien
>   à annuler, rien à dire) ;
> · **trois défauts trouvés en auto-revue et corrigés** : (1) les ports
>   posés à `left: 0`/`top: PORT_Y` tombaient à UN PIXEL de l'ancre — le
>   repère d'un enfant absolu est la boîte de PADDING de son ancêtre, pas sa
>   boîte de bordure (`- var(--cf-bord)`, épinglé au chiffre des deux
>   fichiers) ; (2) le bouton « supprimer » vit DANS le monde, donc le
>   glisser du fond le retirait au `pointerdown` avant que son propre clic
>   n'arrive ; (3) `paintNode` réécrit l'intérieur d'un nœud — sans
>   `portsHtml` là aussi, les poignées disparaissaient au premier caractère
>   tapé ;
> · **français accordé** : le libellé du plan (« un {from} ne se branche pas
>   sur un {to} ») donne « un couche » une fois sur deux et aurait exigé une
>   table de GENRES à tenir d'accord avec `KIND_LABELS` — les kinds sont donc
>   CITÉS entre guillemets, et les phrases de surnombre s'accordent en bloc.
> **REVUE DE QUALITÉ (2e passe) — 7 points, tous appliqués** : **C1** un
> maillon n'appartient qu'à UNE chaîne — le contrôle de surnombre demandait
> « MA chaîne en a-t-elle déjà un ? » et jamais « cette cible est-elle déjà
> prise ? » : tirer sur un maillon qui sert une AUTRE chaîne passait, et le
> dégât arrivait plus tard et ailleurs (`rewireRow` réécrit la rangée éditée
> en premier et purge l'arête de l'autre — la seconde chaîne cesse d'être
> construite en silence tout en s'affichant encore). Une arête entrante par
> maillon, refusée AVANT l'écriture ; les deux commentaires « cet écran ne
> produit jamais cette topologie » (`rowDuNoeud`, `maillonsAval`) redeviennent
> VRAIS et pointent désormais la garde qui les tient. **I2** le contrôle
> s'aveuglait sans couche : `chaineDe` remontait par `rowDuNoeud`→`graphRows`,
> qui n'a de rang qu'AVEC une couche — or couper `layer→traitement` est un
> geste de première classe depuis cette tâche, et le surnombre acceptait
> alors tout (créer-puis-avouer). La remontée se fait maintenant à la main
> jusqu'au traitement de tête (`rowModel` répond sans couche). **I3**
> `export_formats` épinglé au contrat `/info`. **M4** le commentaire du
> nettoyage disait « le `in` hache » d'un TUPLE (faux : balayage linéaire de
> `==`) et citait `finish` comme même patron alors qu'il n'a pas de garde
> justement parce que c'est un tuple — la fiction aurait appris au lecteur
> suivant à retirer une garde dont un `set` a besoin. **M5** compte de banc
> retiré de la prose (plancher dans le test). **M6** le fantôme lit
> `camPending || CAM` : zoomer en plein glisser le faisait retarder d'une
> frame. **M7** ci-dessous. Les deux défauts de comportement (C1, I2) sont
> tués PAR LE BANC — mesuré : les pins de source y survivent, le nom d'une
> fonction ne dit pas ce qu'elle refuse.
> **Restes à T7 (navigateur)** : le ressenti du fil au pointeur réel, la
> pastille de 14 px au zoom arrière (assumé : sous z≈0,86 elle passe sous la
> barre des 12 px — le plancher de zoom protège la poignée de DÉPLACEMENT,
> pas celle de connexion ; remède nommé dans la feuille si la passe dit le
> contraire), la lisibilité du bouton de coupe sur une arête courte, et
> (M7) les arêtes CONVERGENTES : là où six chaînes se rejoignent sur
> l'assemblage, leurs zones de saisie de 14 px se chevauchent et c'est le
> dernier chemin du DOM qui prend le clic. Ce n'est pas une perte de contrôle
> — le geste est en DEUX temps, le clic ne fait que DÉSIGNER et `.sel` montre
> laquelle avant que « supprimer » n'existe, et le bouton reste cliquable
> au-dessus des nœuds (z-index 3) ; ce qui reste à juger à l'œil, c'est la
> lisibilité de ce surlignage au zoom arrière.
> **Dépendance T5** : aucun nœud `export` ne peut NAÎTRE avant la palette —
> le vocabulaire, les ports, la grammaire et le nettoyage l'attendent, mais
> l'écran ne montre encore que son motif (`KIND_HINTS.export`) ; son corps
> (choix du format, téléchargement) est bien la Task 5. `/info` publie
> désormais `graph_limits.export_formats` pour qu'elle ne le recopie pas.

- [x] **Step 1 : tests en RED**

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

- [x] **Step 2 : implémentation**

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

- [x] **Step 3 : GREEN + harnais + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): connexions port-a-port validees a l arete (grammaire nommee), kind export en miroir - le bordereau reste entier"
```

---

### Task 5: L'inspecteur partagé, le nœud artefact, les nœuds d'export, la palette

**Files:** mod-forge3d.js, mod-forge3d.css, test_cards_forge3d.py **+ forge3d.py**
(la route `node-file` ACCORDÉE par le contrôleur — voir la note de livraison).

> **LIVRÉ (f2abf55).** 91 tests (88 + 3), lint 0 violation, `--geom` 4/4,
> `node --check` OK ; **23 mutants tués, ancre-contrôle survivante**. Décisions
> et amendements, tous à la SOURCE :
> · **DEUX contextes WebGL, PAS TROIS**, et c'est une contrainte tenue par
>   RÉFÉRENCE, pas par `querySelector` : `paintCanvas` reconstruit le monde en
>   un `innerHTML`, ce qui DÉTACHE le viewer monté dans le nœud artefact — un
>   `$("#cf-forge3d-mv")` ne l'aurait plus trouvé et en aurait fait naître un
>   second à chaque repeinture. `MV`/`INSP_MV` gardent l'élément, `poseViewer`
>   le DÉMÉNAGE (canvas → nœud artefact, liste → section « Aperçu »), et la
>   section qu'il quitte DIT où il est parti au lieu de rester un cadre vide.
> · **le débounce vit dans le DÉCLENCHEUR, pas dans la requête** (note de
>   concurrence T1) : `majInspecteur` porte la CLÉ de sujet (idempotence) et la
>   minuterie (250 ms) ; `inspecte` porte le jeton (`INSP_JETON`) et la garde
>   de génération. Les deux ne couvrent pas la même chose — le jeton avance
>   quand le SUJET change, `GEN` quand la CARTE change — d'où un défaut trouvé
>   en revue par mutation et corrigé à la source : **un changement de carte
>   lâche l'aperçu** (`cardChanged` → `videInspecteur`), exactement comme il
>   lâche les jobs ; un GLB d'aperçu est construit depuis LES COUCHES d'une
>   carte précise.
> · **la palette naît DU VIVANT** : une matière sans matière ni finition est
>   JETÉE par `clean_graph`, donc un maillon né vide serait un nœud que le
>   serveur efface — elle naît avec la première matière servie (patron du
>   moteur par défaut d'un mesh3d), et la boutique vide se DIT. Le câblage
>   passe par `editMat`/`editTrs` → `rewireRow` : zéro seconde recette
>   d'arêtes, et le placement tombe au BOUT de la chaîne (jamais l'éventail
>   `t1→r2` que le report T4 nommait).
> · **un seul sujet à la fois, sans dépendance d'ORDRE** : `selectionne` lâche
>   l'arête et `selectionneArete` lâche le nœud — le faire dans les fonctions
>   plutôt qu'aux sites d'appel enlève le piège du « qui appelle qui en
>   second » (mutant M21). Cliquer le FOND, lui, garde l'arête : on se déplace
>   sans perdre ce qu'on visait.
> · **ÉCART ASSUMÉ au point imposé de la route accordée** : `node-file` LIT ses
>   octets au lieu de `FileResponse`. La raison est écrite deux fonctions plus
>   haut (`get_material_thumb`, M3) : `FileResponse` re-`stat` le fichier à
>   l'ENVOI, donc APRÈS le contrôle — et ici la fenêtre n'est pas théorique, le
>   dossier d'un nœud est `rmtree` INTÉGRALEMENT à chaque relance. C'eût été un
>   500 sur la doctrine « jamais-500 ». Le motif de `node-preview` (qui, lui,
>   GARDE `FileResponse`) ne s'applique pas : là il s'agit d'un GLB de 32 Mio
>   qu'on refuse de charger en RAM, ici d'une vignette.
> · **un banc de palette** (le pendant du banc de chaînes T4) : les VRAIES
>   fonctions extraites du fichier livré tournent dans node et mesurent ce
>   qu'elles REFUSENT — 43 cas, dont les aveux d'un VRAI GLB d'aperçu
>   (octets construits par le backend dans le test, relus côté client par
>   `glbExtras`). Un pin de source dit qu'une fonction est appelée ; il ne dit
>   pas ce qu'elle refuse (la leçon T4, re-confirmée : 4 mutants ont survécu à
>   la première passe).
> **Restes à T7 (navigateur)** : la lisibilité du panneau à 232 px et le
> repli sous 720 px, le ressenti du débounce à 250 ms sur un balayage réel, un
> `model-viewer` de 200 px dans un nœud (est-ce assez pour juger un modèle ?),
> la caméra du viewer après un DÉMÉNAGEMENT (re-`connectedCallback` : on
> attend qu'elle survive, ce n'est pas mesuré), et les hauteurs `RANG_H`
> d'`artifact` (420) et `export` (320) à l'œil.

> **RONDE DE CORRECTION (revue adverse de f2abf55 + 50326f1 → FIX-FIRST).**
> 91 tests (le compte de fonctions ne bouge pas : la mesure neuve entre dans
> le banc et les pins EXISTANTS — le banc de palette passe de **43 à 83 cas**),
> lint 0, `--geom` 4/4, `node --check` OK ; **24 mutants tués, ancre-contrôle
> survivante** (doubler `_NODE_FILE_MAX` reste vert : le test lit la constante
> au lieu de recopier 4 Mio).
> *Corrigé* — **S1** : `majInspecteur` LÂCHE le nœud désigné quand il a quitté
> le graphe (annulation, maillon vidé par `editMat`) ; sans ça la clé de sujet
> le faisait sortir par le haut et le panneau gardait le nom et le 3D d'un
> mort. `majSelArete` le faisait déjà pour l'arête : c'était l'asymétrie.
> **S2** : la molette AU-DESSUS du viewer embarqué ne zoome plus la scène (le
> `model-viewer` `preventDefault` sans `stopPropagation`) — et le garde tombe
> AVANT `preventDefault`, sinon le défilement serait confisqué pour rien.
> **S3** : les TROIS sorties d'échec de `inspecte` (transport, refus nommé,
> corps vide) passent par `echecInsp` — elles VIDENT (le modèle d'avant ne
> reste plus sous le NOM du nouveau nœud) et RENDENT `INSP_SUJET`, sans quoi
> l'échec était collant (aucune peinture ne re-tentait). Le succès, lui, garde
> sa clé — c'est l'ancre de mutation du banc.
> **S3 (résidu, tranché dans la même ronde)** : rendre la clé ne suffisait pas
> au geste le plus évident. `selectionne` sort PAR LE HAUT sur un nœud déjà
> désigné — c'est le garde qui empêche un balayage de mettre N constructions
> en file — donc RE-CLIQUER le nœud qui vient d'échouer ne repartait pas, et
> la seule sortie de secours était d'aller en désigner un autre pour revenir.
> Une fissure ÉTROITE y est ouverte : `const reprise = !!SEL && !INSP_SUJET;`.
> Les deux moitiés comptent. `!INSP_SUJET` ne décrit que l'après-échec —
> `majInspecteur` pose la clé de façon SYNCHRONE, 250 ms avant même d'appeler
> `inspecte`, donc pendant l'attente comme pendant la requête elle est POSÉE
> et un double-clic rapide ne peut pas mettre deux constructions en vol.
> `!!SEL` ferme le FOND : `onCanvasDown` appelle `selectionne(null)` à CHAQUE
> pointerdown du fond, c'est-à-dire au début de chaque déplacement de vue, et
> au repos la clé y est vide elle aussi — une clause qui n'aurait regardé que
> la clé (la forme d'abord proposée) aurait repeint la palette entière à
> chaque début de pan, soit exactement le gaspillage que ce garde existe pour
> empêcher. Le banc mesure les DEUX moitiés, et il les mesure en journalisant
> les sélecteurs demandés : sans DOM, « il n'a rien fait » ne se voit pas
> autrement (un `marqueSel` + `paintPalette` inutiles ne laissent aucune
> trace). Et le passage ouvert ne coûte RIEN de payant : `selectionne` ne fait
> que `marqueSel` + `paintPalette` + `majInspecteur`, et la seule requête au
> bout est `node-preview`, gratuite et éphémère — `build3d`, `launchMesh3d` et
> les polls vivent tous derrière un `data-act`, jamais derrière une sélection.
> **M1** : le repli ≤720 px était MORT (la forme courte `flex: 0 0 232px`,
> écrite plus bas, remet la longhand `flex-basis: 100%`) — la requête de média
> DESCEND sous la règle de base, et le pin mesure désormais l'ORDRE, pas la
> présence. **M2** : `node-file` plafonne sa lecture (`_NODE_FILE_MAX` 4 Mio,
> sentinelle nommée → 413 littéral) — le chemin qui ÉCRIT ce PNG ne le borne
> pas. **M3** : `text-overflow: ellipsis` était inerte sans `white-space:
> nowrap`. **M4** : « + matière » / « + placement » REFUSENT un traitement
> sans couche source — le maillon serait né câblé mais son corps aurait
> accusé le mauvais coupable (« matière hors chaîne — aucun traitement ne la
> porte » : faux, c'est la couche qui manque). **M5** : `FIGE_PRET` — « figer »
> suit la SCÈNE (l'évènement `load`), plus la seule présence de `PREVIEW_URL` ;
> chaque repeinture de nœud le ré-armait dans la fenêtre où une capture aurait
> rendu un cadre VIDE, et ce cadre devient l'image de la carte. **M6** : un
> changement de carte lâche AUSSI `ARTIFACT` (+ `videApercu`, la porte
> complète) — les nœuds d'export ne lisent rien d'autre, ils affichaient donc
> les poids, les crédits et les boutons de la carte d'avant ; la promesse de
> `refreshManifest` est prise AVANT la repeinture (une peinture rappelle
> `cardChanged`, le verrou doit être posé).
> *Tidy* — **N1** (`no-store` sur les refus de `node-file` et
> `material-thumb` : un 404 en cache laisse le pictogramme par défaut sur un
> nœud qui a déjà sa vignette), **N3** (un format refusé ne pousse plus
> d'entrée d'annulation pour un graphe inchangé), **N5** (le garde `|| []` à
> l'écriture — pris AUSSI dans `naitProc`, même défaut, même famille : le
> laisser eût été la copie que le grep rate), **N8** (deux exports du même
> format sont refusés, nommés).
> *Décliné* — **N6** : la piste proposée (comparer l'id de nœud du parent
> capturé AVANT le détachement) demande de restructurer `paintNode`, ce que la
> revue autorisait à reporter. Fait à la place, sans restructuration :
> `majSectionApercu` n'ÉCRIT que si le texte change — le churn (une réécriture
> identique par champ commis) disparaît, et l'échec de l'égalité au pire
> réécrit comme avant. Le reste (un vrai « même-nœud ») reste **pour T7**.
> *Hors périmètre, toujours ouverts* : N2 (éviction d'`IMGS`), N4 (registres
> `{}` nus des fonctions T4), N7 (dimensionnement du pool de threads).
> *Amendé à la source* : un cas du banc T5 désignait « t2 », un nœud ABSENT
> du graphe de test — S1 le refuse désormais, à raison. Le cas mesure
> maintenant la même propriété sur un nœud RÉEL, et un cas de plus dit que
> désigner un nœud absent ne pose aucun sujet.

> **CLOSE (ronde 350a416→633439d, re-revue : RONDE VALIDÉE).** Les quinze
> correctifs vérifiés SÉMANTIQUEMENT, pas au grep — les deux affirmations
> d'ordre retracées par le réviseur lui-même (la clé de sujet posée AVANT la
> minuterie ; le verrou `.busy` de `refreshManifest` armé avant la repeinture
> qui peut rappeler `cardChanged`). Zéro régression sur les 18 hunks JS,
> hors-périmètre intouché (grep du diff complet), plan 914/914 CRLF après
> l'incident sed. Deux assertions manquantes consignées → **reprises T6** :
> `cache-control` jamais asserté sur les refus de `material-thumb` (le code
> l'envoie, le test ne le lit que côté `node-file`) ; aucun pin d'ORDRE sur
> `refreshManifest`-avant-`repeintLeBordereau` dans `cardChanged` (un
> réordonnancement accidentel raviverait la récursion sans qu'un test rougisse).

- [x] **Step 1 : test de source en RED**

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

- [x] **Step 2 : implémentation**

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

- [x] **Step 3 : GREEN + lint + commit**

```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): inspecteur 3d unique, noeud artefact avec son viewer, noeuds d export au motif litteral, palette bornee"
```

---

### Task 6: La Bibliothèque — publier l'artefact + le patch bundle minimal

> **LIVRÉ (838d7e1 → 8eb0605, 6 commits LOCAUX, rien de poussé).** 95 tests
> (91 + 4), suite `-Filter cards` **10/10**, `-Filter meshy` vert, lint
> INTÉGRAL 0 violation (9/9 modules), `--geom` 4/4, `node --check` OK, index
> git en `lf` partout, zéro BOM, zéro octet NUL. **19 mutants tués, ancre de
> contrôle survivante** (changer la valeur de `NAMESPACE_CARD3D` ne fait
> rougir personne : aucune propriété mesurée ne dépend du littéral).
>
> · **LA COUTURE, D'ABORD ET SEULE** (838d7e1) : forge3d.py 2879 → 2637
> lignes, forge3d_apercu.py 415. La suite 91 a servi de verrou — coupée
> d'abord, lancée verte SANS qu'un test bouge, tests touchés APRÈS.
> **La règle qui a décidé de la découpe : le sidecar n'importe RIEN de
> forge3d.py.** Une couture qui importe son parent n'en est pas une, c'est la
> même pièce en deux fichiers. Ça a coûté deux injections NOMMÉES
> (`element_local(…, ouvre_png=, habille=)` — `_open_png` sert aussi trois
> routes de forge3d.py, et `_habille` a besoin de `tile_maps`, qui a besoin de
> `_num` : trois fondations qui ne pouvaient pas déménager sous un nom
> « apercu ») et le passage du job/dossier par l'appelant
> (`glb_servi_path(job, node_dir, nid)`) : **le magasin ici, les règles
> là-bas**. Paramètres NOMMÉS et non positionnels — deux callables
> interchangeables au même rang, c'est le swap silencieux que N2 existe pour
> rendre impossible.
> · **ÉCART ASSUMÉ au patron `forge3d_scene`** : le sidecar N'EST PAS pur au
> sens du module scène (il importe `HTTPException`). Le rendre pur aurait
> demandé de traduire les refus en `ValueError` + codes, c'est-à-dire de
> RÉÉCRIRE les chemins d'échec pendant une découpe dont tout l'intérêt est de
> ne rien changer — et surtout de SÉPARER la phrase de son code, l'exact
> inverse de N1. La pureté de forge3d_scene tient à ce qu'il est (de la
> géométrie) ; ce fichier-ci est fait de refus nommés.
> · **N1 mesuré, pas promis** : les deux phrases d'aveu vivent dans
> `_source_gagnante` / `_chaine_aval(…, ignores)`. La revue par mutation a
> trouvé que la phrase « source surnumeraire » n'était **pinnée nulle part**
> (celle du maillon l'était) — d'où un test neuf qui compare les DEUX
> producteurs (bordereau de build3d vs extras du GLB de node-preview) **octet
> pour octet** sur la même topologie. Deux mutants le tuent.
> · **N2** : `_element_local(…, g, ignores)` — 13 paramètres → 9, et la
> dérivation UV/fond-perdu, qui existait en DOUBLE (build3d et node-preview),
> vit désormais dans `_geom_element` seule. Échanger `bleed_px` et
> `canvas_px` dedans est tué par le test de fenêtre UV.
> · **N3** : la fenêtre TOCTOU du `FileResponse` de node-preview est écrite
> LÀ OÙ ELLE VIT, avec le prix accepté et la raison pour laquelle les deux
> autres routes servant des octets ont tranché l'INVERSE (des vignettes, pas
> des GLB de 32 Mio).
> · **La route** (daa98e2) : `POST /library/{art}`, id `uuid5(deck/art)` —
> l'idempotence est une propriété de CONSTRUCTION, pas une vérification.
> `short = job_id[:8]`, le MÊME calcul que l'écran (`job_id.slice(0,8)`) et
> que `_delete_provider_output_dir` (`job.id[:8]`) : une seule règle, pas
> trois. **Publier n'est pas fabriquer** : sans `{art}.glb`, 409 nommé, jamais
> un build implicite. La disposition écrite est celle que les routes
> EXISTANTES lisent — vérifié dans routes.py : `/{fmt}` sert `model.{fmt}`,
> `/preview` sert `preview.png`, `/manifest` liste `model.*` — donc le plan
> avait raison sur la disposition, et le test le prouve en passant par les
> vraies routes plutôt qu'en regardant le disque.
> · **Le patch** (e4d75d3) : 2 ancres, uniques, vérifiées avant ; bundle du
> dépôt 1367240 → 1367288 o (+48), CRLF 11884 inchangé, **inventaire de
> fonctions IDENTIQUE** (1395 déclarations, 1228 noms, même sha1 — le piège de
> la mémoire, mesuré). Écriture par fichier temporaire + `os.replace` :
> jamais un bundle à moitié patché sur disque. 5 sondes de stabilité, dont les
> TROIS filtres de rendus vidéo qui doivent rester intacts.
> · **Le bouton** (e30d712) : dans les DEUX vues par la MÊME fonction d'état ;
> garde de génération à la zone exacte (entre le retour réseau et l'écriture
> de « publié ») ; verrou `.busy` en PREMIER geste ; aucun `setGraph`/`M.patch`
> — publier n'est pas une édition, « ↶ annuler » n'a rien à avaler. L'état
> « publié » meurt avec `ARTIFACT` : au changement de carte (M6) **et** à la
> reconstruction — la copie qui dort dans la Bibliothèque porte alors les
> octets d'AVANT. Banc de palette 83 → 89 cas.
>
> **Restes / concerns pour T7** :
> 1. ~~Dossier orphelin à la suppression~~ — **PRIS dans la ronde** (M9a) :
>    `pipeline._delete_provider_output_dir` connaît `card3d`, avec son test.
> 2. ~~`image_filename` = `"preview.png"`~~ — **PRIS dans la ronde** (M6) :
>    toujours `f"card3d_{short}"`, sans extension, donc impossible à prendre
>    pour un fichier de la bibliothèque d'images.
> 3. ~~`short` = 32 bits, collision possible~~ — **PRIS dans la ronde** (M8) :
>    l'exposition demeure (c'est la disposition d'`asset3d`), mais elle ne
>    peut plus DÉTRUIRE : un dossier déjà occupé fait un 409 nommé avant la
>    première écriture. Reste vrai que deux objets ne peuvent pas coexister
>    sous le même `short` — le refus dit de renommer l'artefact.
> 4. Le déploiement du bundle vers l'app **n'est pas fait** (Task 7), et le
>    `--check` du patcher sur la racine de l'APP refusera à raison : on ne
>    patche pas l'app, on y COPIE le bundle du dépôt.
> 5. **`reapply_inblock_patches.py` n'a aujourd'hui aucun emploi sûr**
>    (mesuré en ronde, M9b) : les deux égalités de mtime rendent tout rejeu
>    depuis `sonvfx` indécidable. Ce n'est pas un reste de la 2c — c'est une
>    dette de la chaîne, désormais ÉCRITE dans les deux fichiers. La
>    désamorcer demanderait de re-dater les `.bak` ex aequo dans le vrai
>    ordre, ce qu'aucune mesure ne permet de reconstituer aujourd'hui.
>
> **RONDE DE CORRECTION T6 (revue adverse → FIX-FIRST, 3689060 → a071a57).**
> 97 tests (95 + 2), banc de palette 89 → 91 cas, lint intégral 0, `--geom` 4/4,
> `node --check` OK, index `lf` partout, bundle INTOUCHÉ par la ronde
> (1367288 o). **13 mutants tués, ancre-contrôle survivante** (changer les
> MOTS du 409 de collision ne fait rougir personne : le refus est la
> propriété, pas sa prose) — plus 1 mutant reconnu ÉQUIVALENT et consigné.
>
> *Corrigé* — **S1** : le test du patcheur lisait `.bak_card3d_library`, que
> `.gitignore:58` exclut : il était donc le seul rouge de la suite sur TOUT
> clone frais. L'état pré-patch se DÉRIVE désormais du bundle livré en
> inversant les deux paires — **vérifié octet-identique au `.bak`** (1 349 689
> caractères), et re-vérifié en cachant le `.bak` pour simuler le clone.
> **S2** : re-publier n'ÉCRASAIT que ce qui existe — la vignette de la
> publication précédente restait servie sous le même `short` après une
> reconstruction sans re-figer (le rebuild efface pourtant le PNG du deck), et
> un `model.opt.glb` d'« Optimiser » aurait servi le maillage optimisé de
> l'ANCIEN modèle. Le dossier est l'IMAGE de l'artefact, pas un dépôt qui
> s'accumule. **M3** : `copyfile` tronque puis réécrit EN PLACE → GLB ÉPISSÉ
> pour un `FileResponse` en cours ; copie vers un temporaire (à point de tête,
> pour que `manifest` ne le déclare pas comme un format) puis `os.replace`,
> dans la MÊME boucle de reprise que `_job_write`. **M4** : « Publier » était
> cliquable pendant une construction — donc publiait les octets du build
> précédent ; verrou sur le bouton ET dans la fonction (un bouton désactivé
> n'arrête ni le clavier ni un double-clic). **M5** : un metadata de la
> mauvaise FORME faisait un 500 sur un fichier qu'on ne fait que recopier.
> **M6** : `image_filename` ne vaut plus « preview.png » — ce nom passe le
> contrôle d'extension du tiroir de file d'attente et se résoudrait en
> `/api/images/preview.png`. **M7** : le patcheur écrivait son `.bak` AVANT de
> valider ses ancres — backup posé puis abandon, et la relance d'après
> DÉTRUIT la réparation manuelle. **M8** : `short` fait 32 bits et `asset3d`
> coupe un uuid4 au même endroit — publier aurait écrasé un maillage PAYÉ,
> **de façon reproductible** (notre id est déterministe) ; garde nommée par
> préfixe de clé primaire, avant le premier octet. **M9a** (transverse,
> chirurgical) : `_delete_provider_output_dir` apprend `card3d` — `job.id[:8]`
> EST déjà notre `short`. **M9b** : les deux fichiers de chaîne se
> contredisaient ; mesuré que **DEUX** couples de `.bak` sont ex aequo
> (`keepstate`/`sfxstudio` ET `subs`/`vfxrack`, mtime + sha1), donc rejouer
> depuis un point ≤ `subs`/`vfxrack` est indécidable — ce qui inclut
> `--from sonvfx`, donc `reapply_inblock_patches.py`, qui n'a **aujourd'hui
> aucun emploi sûr**. Une doctrine, dans le patcheur ; l'autre fichier y
> renvoie.
> *Élagué* — les SIX réexports morts (`_PROC_KINDS`, `_CHAIN_MAX`,
> `_source_gagnante`, `_chaine_aval`, `_trs_dict`, `_geom_element`) :
> recensement sur tout le backend + les tests, ils n'apparaissaient plus que
> dans de la prose. Les deux EXERCÉS (`_resolve_graph_elements`,
> `_PREVIEW_ASM_ID`) sont désormais ÉPINGLÉS comme réexports, avec un pin de
> PURETÉ DE COUTURE (le sidecar n'importe rien de forge3d.py) — la propriété
> qui a décidé de la découpe devient mesurée au lieu d'être promise.
> *Trouvé par la mutation elle-même* — deux pins étaient décoratifs : celui
> de M3 acceptait « au moins un temporaire » (donc restait vert si SEUL le
> `model.glb` de 32 Mio retombait sur un `copyfile`), et celui de M6 vivait
> AVANT que l'aperçu existe, là où les deux écritures rendent le même nom.
> Corrigés, puis re-tués.
> *Consigné, non corrigé* — le `isinstance` de M5 seul est un mutant
> ÉQUIVALENT (le filet élargi rattrape l'AttributeError ; il reste parce
> qu'un chemin nominal ne doit pas passer par une exception pour décider
> d'une forme — écrit sur place). Et les trois points laissés en l'état par
> le contrôleur : `finally` sans garde GEN dans `publishLibrary` (bénin,
> mesuré), `datetime.utcnow` (question maison, endémique — SQLAlchemy l'émet
> aussi), chemin absolu dans le message de 500 (convention existante ×5 dans
> le fichier).
>
> **Défaut trouvé APRÈS coup, en vérifiant la chaîne plutôt qu'en la
> supposant** : `repatch_all.py --list` sortait `card3dlibrary SANS SCRIPT`.
> Le tag était `card3dlibrary` et le fichier `patch_bundle_card3d_library.py`
> (le nom imposé par le plan) — or la chaîne DÉDUIT le script du tag du
> backup. Chaîne non rejouable, et un abandon net le jour où quelqu'un rejoue
> depuis un maillon amont. Tag aligné sur le nom (`card3d_library`), `.bak`
> renommé, et **deux pins de plus** : le nom du patcher, et le nom du `.bak`
> qu'il POSE. Un patcher correct qui n'est pas dans la chaîne n'est pas une
> livraison.

> **COUTURE DE DÉLESTAGE (ajoutée après T1)** : forge3d.py a franchi le seuil
> des ~2400 lignes (2708 après les correctifs T1). AVANT d'ajouter le bloc
> bibliothèque, extraire dans un sidecar intra-pièce `forge3d_apercu.py`
> (EXTRA_PY += ; règle R8 sans routeur propre, patron forge3d_scene) le bloc
> APERÇU pur : `_apercu_mesh3d`, `_glb_servi_path`, `_element_local`, la
> logique de sous-graphe de node-preview (la ROUTE reste dans forge3d.py et
> appelle le sidecar) — réexports pour la compat des tests. La suite verte 91
> (~~83~~, corrigé à la source : la ronde T5 l'a portée à 91) est le verrou de
> la découpe (patron Task 1 de la 2b). **La même passe prend
> (re-revue T1)** : N1 — extraire `_source_gagnante` + `_chaine_aval(…,
> ignores)` pour que LES phrases d'avoeu vivent à côté des règles qui les
> produisent (le grep a déjà raté une copie au découpage de littéral près) ;
> N2 — `_element_local(…, g, ignores)` dérive bleed/canvas/uv_window EN
> INTERNE (13 paramètres positionnels → 9, le swap silencieux de tuples
> devient impossible) ; N3 — une ligne d'honnêteté sur la fenêtre TOCTOU
> assumée du stream FileResponse mesh3d (un relaunch concurrent peut 500 —
> prix accepté du streaming, le dire).

**Files:** forge3d.py, test_cards_forge3d.py, scripts/patch_bundle_card3d_library.py (créé), la chaîne de patchs, mod-forge3d.js (le bouton).

> **Reprises de la ronde T5 (re-revue)** : ajouter l'assertion `cache-control:
> no-store` aux chemins de refus du test de `material-thumb` (r2/r3/r4), et un
> pin d'ORDRE dans le test de `cardChanged` (`refreshManifest(` apparaît AVANT
> `repeintLeBordereau(` dans le corps — comparaison d'indices, patron du pin M1
> CSS). Les deux tombent naturellement ici : la découpe `forge3d_apercu.py`
> déplace ces routes et leurs tests de toute façon.
>
> **AMENDÉ À LA SOURCE (T6, mesure RED)** : ~~r2~~ n'est PAS un refus de cette
> route. `material-thumb/..%2Fx` porte un séparateur : AUCUNE route ne matche,
> c'est le 404 du ROUTEUR qui répond, sans un seul de nos en-têtes. La reprise
> porte donc sur r3/r4 **plus un cas neuf** — un `mid` hors motif qui ATTEINT
> la route (400 nommé + `no-store`), c'est-à-dire le refus que r2 croyait
> viser ; et r2 est désormais pinné pour ce qu'il est (aucun en-tête à nous).

- [x] **Step 1 : tests en RED (backend)**

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

- [x] **Step 2 : la route**

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
  f"{nom_deck} · {art}", ~~final_video_path=chemin glb copié~~, image_filename=
  "preview.png" si copiée, cost_meta json {deck: did, art, engines, files})` —
  upsert = get puis update, sinon insert (l'idempotence du test) ;
  **AMENDÉ À LA SOURCE (T6)** : `final_video_path` reste VIDE. Trois écrans
  listent les rendus par `status==="done" && final_video_path &&
  provider!=="asset3d" && provider!=="sprite2d"` (onglet « rendus » de la
  Bibliothèque, sélecteur « Existing render » du Studio, Scheduler) : y poser
  le chemin du GLB aurait fait apparaître la carte comme une VIDÉO dans les
  trois, avec un lecteur incapable de l'ouvrir. Un GLB n'est pas un rendu
  vidéo — la colonne vide les exclut par construction, sans un filtre de plus
  à patcher. Mesuré dans le test.
- réponse `{job_id, short, provider}` ; to_thread pour les copies ; jamais-500.

Écran : bouton « Publier dans la Bibliothèque » sur le nœud artefact (et le
bordereau liste), garde GEN, toast succès avec le titre publié, état
« publié » persistant dans le bordereau affiché.

- [x] **Step 3 : le patch bundle (chaîne officielle)**

`scripts/patch_bundle_card3d_library.py`, style des patchers existants (en LIRE
un d'abord + relire la mémoire des pièges : source en LF, ancres exactes,
inventaire de fonctions après) :
- ancre 1 : `return z.provider==="asset3d"});setJobs(L)` →
  `return z.provider==="asset3d"||z.provider==="card3d"});setJobs(L)` ;
- ancre 2 : `T3=u.filter(C=>C.provider==="asset3d"&&C.status==="done")` →
  `T3=u.filter(C=>(C.provider==="asset3d"||C.provider==="card3d")&&C.status==="done")` ;
- chaque ancre UNIQUE dans le bundle (le vérifier AVANT d'écrire), échec du
  patch = message nommé, jamais un bundle à moitié patché ;
- ~~enregistrer dans la chaîne de ré-application (lire
  `scripts/reapply_inblock_patches.py` et suivre SON registre)~~ — **AMENDÉ À
  LA SOURCE (T6)** : `MODULES` de ce script ne vaut QUE pour les couples situés
  DANS le bloc sonvfx (c'est ce qu'un rafraîchissement du bloc efface). Les
  deux ancres d'ici sont dans le bundle NATIF : la boucle les compterait à 0 et
  les classerait « hors bloc, intacts » — un no-op qui ferait CROIRE que ce
  script les protège. La chaîne réelle est `repatch_all.py`, qui la déduit des
  `.bak_<tag>` par mtime : y être inscrit, c'est avoir un `.bak_<tag>` (fait,
  en queue) et un `patch_bundle_<tag>.py` (fait). Le CRITÈRE d'entrée dans
  `MODULES` est désormais écrit dans le fichier, avec l'avertissement mesuré :
  lancer `reapply_inblock_patches.py` aujourd'hui restaure un `.bak_sonvfx` de
  730 Ko (état du 6 août) et efface TOUS les maillons posés depuis ;
- test du patcher : sur une COPIE du bundle, exécuter, asserter 2 remplacements
  et l'idempotence (re-exécuter → 0 changement, pas de double-patch).
- Appliquer au bundle du DÉPÔT (frontend/dist) + commit. Le déploiement vers
  l'app = Task 7.

- [x] **Step 4 : GREEN + lint + commit**

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
- [ ] **Report N6 (ronde de correction T5)** : `poseViewer` appelle
      `majSectionApercu` à CHAQUE ré-accrochage, parce qu'un `paintNode`
      détache le viewer avant de le remettre — le « déménagement » n'est donc
      jamais distinguable d'un retour au même hôte. Le churn est déjà éteint
      (la section n'écrit que si son texte change) ; ce qui reste est le vrai
      test de même-nœud, qui demande à `paintNode` de dire s'il détache le
      viewer. À trancher ici, avec le pointeur : le voir, puis décider si ça
      vaut la restructuration.
- [ ] **Dettes consignées (ronde T5, hors périmètre — trancher en clôture :
      corriger ici ou reporter NOMMÉMENT en phase 3)** : N2 — éviction
      d'`IMGS` (chaque relance d'un job ajoute ~322 Kio de canvas jusqu'au
      changement de deck) ; N4 — registres `{}` nus dans `freeId`/`rewireRow`/
      `maillonsAval`/`rowModel` (fonctions T4) alors que `couchesRestantes`
      suit la doctrine `sansProto()` et que `_NID_RE` admet `constructor` ;
      N7 — pool de threads par défaut partagé entre les lectures courtes
      (vignettes, polls) et les téléchargements bloquants 120 s de
      `A3D._download` (hérité 2b, structurel).
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
