# Cardforge Phase 2a — Graphe gratuit + assembleur + artefact : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Du manifeste de couches (phase 1) à un artefact 3D téléchargeable — graphe de
nœuds par élément, traitements 100 % GRATUITS (plan texturé, relief extrudé), assemblage
en UN GLB propre, metadata.json compatible ERC-721, aperçu model-viewer — sans un appel
payant. (Les moteurs image→3D, les matières Material Forge et l'iridescence sont la
phase 2b.)

**Architecture:** Le graphe vit dans `doc.forge3d.graph` (undo/autosave gratuits), un
nœud par couche du manifeste + un nœud d'assemblage. Le backend N'ASSEMBLE PAS des GLB
externes en 2a : il ÉCRIT un document glTF multi-nœuds d'un seul tenant (`scene_writer`
local à P9) — bornes d'accesseurs EXACTES calculées à l'écriture, AUCUN champ d'identité
jamais inséré, samplers CLAMP dès la création : pas de rustine post-hoc façon
`finalize_glb`. L'« extrusion » gratuite v1 est une DALLE EN RELIEF : grille déplacée
par l'alpha de la couche — solide fermé PAR CONSTRUCTION (prouvé par les mesures
locales arêtes/volume), donc imprimable. L'UI 2a est une LISTE structurée de nœuds
(un rang par couche : traitement + profondeur), pas un canvas nodal — le modèle de
données EST le graphe ; la vue canvas viendra plus tard si besoin.

**Tech Stack:** P9 existant (mod-forge3d.js / forge3d.py / test_cards_forge3d.py),
PIL pur, struct/json stdlib pour le glTF, model-viewer vendored (aperçu + capture).

**Dépendances :** les compléments de revue de la phase 1 (identité de carte `c{NN}`,
`paper` et `card` au manifeste, chunks sRGB) — le graphe consomme le manifeste
POST-compléments (`layers_c{NN}_{side}.json`).

**Références obligatoires :** le préambule du plan phase 1
(`2026-08-19-cardforge-phase1-couches.md` : harnais, EOL, déploiement, interdits) reste
entièrement applicable, PLUS la « NOTE de revue » de sa Task 4 (to_thread, bornes,
jamais-500 mesuré, mesures idiomatiques) qui s'applique à TOUTE nouvelle route.

---

### Task 1: Le vocabulaire du graphe (bloc miroir) + l'état + le graphe par défaut

**Files:**
- Modify: `frontend/cardforge/js/mod-forge3d.js` (state + bloc miroir + seed)
- Modify: `backend/app/services/cards/forge3d.py` (bloc miroir + validation de graphe)
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : tests en RED**

```python
def test_le_vocabulaire_du_graphe_est_identique_des_deux_cotes():
    """Bloc miroir CF-FORGE3D-NODES : les genres de nœuds et leurs paramètres
    bornés, champ à champ et dans l'ordre — comme la table des couches."""
    from app.services.cards import forge3d as F9
    src = JS.read_text(encoding="utf-8")
    bloc = src.split("CF-FORGE3D-NODES-BEGIN")[1].split("CF-FORGE3D-NODES-END")[0]
    js_rows = re.findall(r'\{ kind: "([a-z0-9]+)", params: \[([^\]]*)\] \}', bloc)
    js_table = [{"kind": k, "params": [p.strip().strip('"') for p in ps.split(",") if p.strip()]}
                for k, ps in js_rows]
    assert js_table == F9.NODE_KINDS, (js_table, F9.NODE_KINDS)
    assert [r["kind"] for r in F9.NODE_KINDS] == ["layer", "plane", "relief",
                                                  "assemble", "artifact"]


def test_clean_graph_repare_et_ne_leve_jamais():
    """Un graphe mal formé ne fait jamais 500 : nettoyeur clé par clé, patron
    clean_options de P8. Les bornes sont celles du bloc miroir."""
    from app.services.cards import forge3d as F9
    # graphe sain : conservé tel quel (aux arrondis près)
    g = {"nodes": [
        {"id": "n1", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "n2", "kind": "relief", "depth_mm": 1.2, "base_mm": 0.3},
        {"id": "n3", "kind": "assemble"}],
        "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]}
    out = F9.clean_graph(g)
    assert [n["kind"] for n in out["nodes"]] == ["layer", "relief", "assemble"]
    assert out["nodes"][1]["depth_mm"] == 1.2
    # poubelle : kinds inconnus jetés, bornes appliquées, ids resynthétisés,
    # edges orphelines jetées, JAMAIS d'exception
    sale = {"nodes": [{"kind": "teleport"}, {"kind": "relief", "depth_mm": 99},
                      {"id": "x", "kind": "layer", "role": "inexistant"}],
            "edges": [{"from": "fantome", "to": "x"}], "extra": object}
    out2 = F9.clean_graph(sale)   # ne lève pas
    kinds = [n["kind"] for n in out2["nodes"]]
    assert "teleport" not in kinds
    relief = [n for n in out2["nodes"] if n["kind"] == "relief"][0]
    assert relief["depth_mm"] <= F9.RELIEF_DEPTH_MM_MAX
    assert out2["edges"] == []
    assert F9.clean_graph(None) == {"nodes": [], "edges": []}
    assert F9.clean_graph("n'importe quoi") == {"nodes": [], "edges": []}
```

Run : `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d` — FAIL attendu (NODE_KINDS absent).

- [ ] **Step 2 : le bloc miroir, des deux côtés**

Dans `forge3d.py` (sous LAYER_ROLES) :
```python
# ── LE VOCABULAIRE DU GRAPHE — BLOC MIROIR ──────────────────────────────────
# ═══ CF-FORGE3D-NODES-BEGIN ═══
# Miroir JS dans mod-forge3d.js ; test de parité champ à champ.
# `layer`    : source — une couche du manifeste (role + side).
# `plane`    : plan texturé, GRATUIT (quad aux dimensions de la carte).
# `relief`   : dalle en relief, GRATUITE — grille déplacée par l'alpha,
#              solide FERMÉ par construction (imprimable).
# `assemble` : fusionne les amonts en une scène.
# `artifact` : sorties (GLB + metadata + aperçu + STL si fermé).
NODE_KINDS = [
    {"kind": "layer", "params": ["role", "side"]},
    {"kind": "plane", "params": ["depth_mm"]},
    {"kind": "relief", "params": ["depth_mm", "base_mm", "grid"]},
    {"kind": "assemble", "params": []},
    {"kind": "artifact", "params": ["name"]},
]
# ═══ CF-FORGE3D-NODES-END ═══

# Bornes des paramètres (publiées par /info, jamais recopiées à l'écran).
PLANE_DEPTH_MM = (0.0, 5.0)          # écart z entre plans empilés
RELIEF_DEPTH_MM_MAX = 3.0            # relief au-dessus de la base
RELIEF_BASE_MM = (0.1, 2.0)          # épaisseur de la dalle
RELIEF_GRID = (48, 256)              # subdivisions — borne sur l'axe X seul :
                                     # gy suit le rapport h/w (tarot portrait à
                                     # 256 -> gy=439, ~452k triangles, mesuré)
RELIEF_GRID_DEFAULT = 160
```

Dans `mod-forge3d.js` (sous LAYER_ROLES, même contenu en syntaxe JS entre
`CF-FORGE3D-NODES-BEGIN/END`) :
```js
  /* ═══ CF-FORGE3D-NODES-BEGIN ═══
     Miroir Python dans forge3d.py ; parité testée champ à champ. */
  const NODE_KINDS = [
    { kind: "layer", params: ["role", "side"] },
    { kind: "plane", params: ["depth_mm"] },
    { kind: "relief", params: ["depth_mm", "base_mm", "grid"] },
    { kind: "assemble", params: [] },
    { kind: "artifact", params: ["name"] },
  ];
  /* ═══ CF-FORGE3D-NODES-END ═══ */
```

- [ ] **Step 3 : `clean_graph` dans forge3d.py**

```python
def _num_or(raw, default: float, lo: float, hi: float) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(lo if v < lo else hi if v > hi else v)


def clean_graph(raw) -> dict:
    """Le graphe, réparé clé par clé — patron `clean_options` de P8. Un nœud
    inconnu est jeté, un paramètre hors bornes est ramené, une arête orpheline
    tombe. Ne lève JAMAIS (doctrine 2.5)."""
    g = raw if isinstance(raw, dict) else {}
    kinds = {k["kind"] for k in NODE_KINDS}
    roles = {r["role"] for r in LAYER_ROLES}
    nodes, ids = [], set()
    for i, n in enumerate(g.get("nodes") or [] if isinstance(g.get("nodes"), list) else []):
        if not isinstance(n, dict) or n.get("kind") not in kinds:
            continue
        brut = re.sub(r"[^A-Za-z0-9._-]", "_", str(n.get("id") or f"n{i + 1}"))[:24]
        node = {"id": brut or f"n{i + 1}", "kind": n["kind"]}
        # resynthese SANS collision possible : "n2x" + "n2x" donnait "n2x" deux
        # fois (mesure en revue) — on suffixe jusqu'a unicite, borne par la
        # longueur d'entree deja tronquee.
        while node["id"] in ids:
            node["id"] += "x"
        ids.add(node["id"])
        if n["kind"] == "layer":
            node["role"] = n.get("role") if n.get("role") in roles else None
            node["side"] = "back" if n.get("side") == "back" else "front"
            node["composite"] = bool(n.get("composite"))
            if node["role"] is None and not node["composite"]:
                continue                      # une source sans source n'est rien
        elif n["kind"] == "plane":
            node["depth_mm"] = _num_or(n.get("depth_mm"), 0.0, *PLANE_DEPTH_MM)
        elif n["kind"] == "relief":
            node["depth_mm"] = _num_or(n.get("depth_mm"), 0.6, 0.05, RELIEF_DEPTH_MM_MAX)
            node["base_mm"] = _num_or(n.get("base_mm"), 0.3, *RELIEF_BASE_MM)
            node["grid"] = int(_num_or(n.get("grid"), RELIEF_GRID_DEFAULT, *RELIEF_GRID))
        elif n["kind"] == "artifact":
            nom = str(n.get("name") or "artefact")
            node["name"] = re.sub(r"[^A-Za-z0-9._-]", "_", nom)[:60] or "artefact"
        nodes.append(node)
    edges = []
    for e in (g.get("edges") or [] if isinstance(g.get("edges"), list) else []):
        if isinstance(e, dict) and e.get("from") in ids and e.get("to") in ids:
            edges.append({"from": e["from"], "to": e["to"]})
    return {"nodes": nodes, "edges": edges}
```
(imports à compléter en tête : `math` si absent.)

- [ ] **Step 4 : l'état écran + le graphe par défaut**

`mod-forge3d.js` : le `state` gagne `graph: null` (commentaire : « le graphe
{nodes, edges} — null = jamais construit ; le graphe PAR DÉFAUT est proposé dès
qu'un export de couches existe »). Fonction de seed (côté écran, à partir du
DERNIER manifeste reçu — donc après un export, ou depuis `GET /files` en Task 3) :

```js
  /* le graphe par defaut : chaque couche -> un plan texture empile (parallaxe),
     100 % gratuit, apercu immediat — on monte en gamme nœud par nœud. */
  function defaultGraph(man) {
    const nodes = [], edges = [];
    let k = 0;
    (man.layers || []).forEach((l, i) => {
      const src = "s" + (++k), tr = "t" + k;
      nodes.push({ id: src, kind: "layer", role: l.role, side: man.side });
      nodes.push({ id: tr, kind: "plane", depth_mm: Math.round(i * 0.35 * 100) / 100 });
      edges.push({ from: src, to: tr });
      edges.push({ from: tr, to: "asm" });
    });
    nodes.push({ id: "asm", kind: "assemble" });
    nodes.push({ id: "art", kind: "artifact", name: "carte3d" });
    edges.push({ from: "asm", to: "art" });
    return { nodes: nodes, edges: edges };
  }
```

- [ ] **Step 5 : GREEN + commit**

Run : run-tests -Filter cards_forge3d → PASS ; lint --module forge3d → 0 violation.
```bash
git add frontend/cardforge/js/mod-forge3d.js backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): vocabulaire du graphe P9 en bloc miroir, clean_graph jamais-500, graphe par defaut"
```

---

### Task 2: La dalle en relief (maillage fermé prouvé) et le quad — géométrie locale

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : tests en RED**

```python
def test_le_relief_est_un_solide_ferme_et_le_quad_un_plan_exact():
    """La dalle en relief est FERMÉE PAR CONSTRUCTION — on le PROUVE sur les
    arêtes (chacune partagée par exactement 2 triangles) et sur le volume
    signé positif, les mesures du domaine (doctrine P8), en copie locale."""
    from PIL import Image, ImageDraw
    from app.services.cards import forge3d as F9
    # une silhouette réaliste : un anneau (trou au centre)
    im = Image.new("L", (64, 64), 0)
    d = ImageDraw.Draw(im)
    d.ellipse([4, 4, 60, 60], fill=255)
    d.ellipse([20, 20, 44, 44], fill=0)
    m = F9.relief_mesh(im, w_mm=63.0, h_mm=88.0, depth_mm=1.0, base_mm=0.3,
                       grid=48)
    rep = F9.mesh_measures(m)
    assert rep["closed"] is True, rep
    assert rep["volume_mm3"] > 0.0
    # le relief est borné : base <= z <= base+depth, xy dans la carte
    xs = m["positions"][0::3]; ys = m["positions"][1::3]; zs = m["positions"][2::3]
    assert min(zs) == 0.0 and max(zs) <= 0.3 + 1.0 + 1e-6
    assert max(xs) <= 63.0 + 1e-6 and max(ys) <= 88.0 + 1e-6
    # UV : couvertes 0..1 pour plaquer la texture de couche
    assert 0.0 <= min(m["uvs"]) and max(m["uvs"]) <= 1.0

    q = F9.quad_mesh(w_mm=63.0, h_mm=88.0)
    assert len(q["positions"]) == 4 * 3 and len(q["indices"]) == 6
    assert F9.mesh_measures(q)["closed"] is False     # un plan n'est pas un solide
```

- [ ] **Step 2 : implémentation**

```python
def quad_mesh(w_mm: float, h_mm: float) -> dict:
    """Un quad aux dimensions de la carte, UV pleines, normale +z."""
    return {
        "positions": [0.0, 0.0, 0.0, w_mm, 0.0, 0.0, w_mm, h_mm, 0.0,
                      0.0, h_mm, 0.0],
        "normals": [0.0, 0.0, 1.0] * 4,
        "uvs": [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],   # v inversé (image)
        "indices": [0, 1, 2, 0, 2, 3],
    }


def relief_mesh(alpha_img, w_mm: float, h_mm: float, depth_mm: float,
                base_mm: float, grid: int) -> dict:
    """LA DALLE EN RELIEF : une grille (grid x grid') dont la face du dessus
    est déplacée par l'alpha de la couche (0 -> base, 255 -> base+depth), face
    du dessous plate à z=0, murs périphériques — un solide FERMÉ PAR
    CONSTRUCTION : chaque arête appartient à exactement deux triangles parce
    que dessus, dessous et murs partagent leurs anneaux de bord. C'est
    l'« extrusion » gratuite v1 : un vrai suivi de contour (marching squares +
    triangulation à trous) viendra si le besoin le prouve."""
    gx = max(2, int(grid))
    gy = max(2, int(round(grid * (h_mm / w_mm))))
    a = alpha_img.convert("L").resize((gx + 1, gy + 1))
    px = list(a.getdata())          # (gx+1)*(gy+1) échantillons

    def z_at(i, j):
        return base_mm + (px[j * (gx + 1) + i] / 255.0) * depth_mm

    pos, uv = [], []
    # dessus : (gx+1)*(gy+1) sommets déplacés
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, z_at(i, j)]
            uv += [i / gx, j / gy]
    top = lambda i, j: j * (gx + 1) + i                      # noqa: E731
    n_top = (gx + 1) * (gy + 1)
    # dessous : mêmes (x, y), z=0 (UV répliquées, sans importance au dos)
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, 0.0]
            uv += [i / gx, j / gy]
    bot = lambda i, j: n_top + j * (gx + 1) + i              # noqa: E731

    idx = []
    # WINDING CORRIGÉ EN REVUE (tâche 2) : la première version de ce plan
    # sortait un maillage à l'ENVERS (normales vers l'intérieur, volume signé
    # NÉGATIF — mesuré : -4557,89 mm³ sur l'anneau de test). Avec
    # `y = (1 - j/gy) * h_mm`, j=0 est le HAUT de carte : l'ordre ci-dessous
    # est celui qui donne aire signée positive vue de +z. Prouvé par le test
    # (closed ET volume > 0 sur silhouette à trou).
    for j in range(gy):
        for i in range(gx):
            aa, bb = top(i, j), top(i + 1, j)
            cc, dd = top(i + 1, j + 1), top(i, j + 1)
            idx += [aa, cc, bb, aa, dd, cc]                  # dessus, +z
            a2, b2 = bot(i, j), bot(i + 1, j)
            c2, d2 = bot(i + 1, j + 1), bot(i, j + 1)
            idx += [a2, b2, c2, a2, c2, d2]                  # dessous, -z
    # murs : les 4 bords, quads entre anneau du dessus et anneau du dessous
    def wall(t1, t2, b1, b2):
        idx.extend([t1, b2, b1, t1, t2, b2])
    for i in range(gx):                                       # j=0 et j=gy
        wall(top(i, 0), top(i + 1, 0), bot(i, 0), bot(i + 1, 0))
        wall(top(i + 1, gy), top(i, gy), bot(i + 1, gy), bot(i, gy))
    for j in range(gy):                                       # i=0 et i=gx
        wall(top(0, j + 1), top(0, j), bot(0, j + 1), bot(0, j))
        wall(top(gx, j), top(gx, j + 1), bot(gx, j), bot(gx, j + 1))

    # normales : accumulation de normales de faces ponderees par l'aire sur les
    # sommets partages ; l'anneau de bord melange mur et face (arete du pourtour
    # adoucie a l'ombrage — geometrie exacte, STL non affecte).
    nrm = [0.0] * len(pos)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
        ux, uy, uz = (pos[i1] - pos[i0], pos[i1 + 1] - pos[i0 + 1], pos[i1 + 2] - pos[i0 + 2])
        vx, vy, vz = (pos[i2] - pos[i0], pos[i2 + 1] - pos[i0 + 1], pos[i2 + 2] - pos[i0 + 2])
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for k in (i0, i1, i2):
            nrm[k] += cx; nrm[k + 1] += cy; nrm[k + 2] += cz
    for k in range(0, len(nrm), 3):
        ln = math.sqrt(nrm[k] ** 2 + nrm[k + 1] ** 2 + nrm[k + 2] ** 2) or 1.0
        nrm[k] /= ln; nrm[k + 1] /= ln; nrm[k + 2] /= ln
    return {"positions": pos, "normals": nrm, "uvs": uv, "indices": idx}


def mesh_measures(mesh: dict) -> dict:
    """Fermeture et volume signé, MESURES locales — copie du principe de
    `mesh_report` de P8 (règle 8 : pas d'import pièce->pièce), réduite aux
    deux chiffres dont l'artefact a besoin (closed, volume)."""
    pos, idx = mesh["positions"], mesh["indices"]
    edges: dict = {}
    vol = 0.0
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            ka = (round(pos[a * 3], 6), round(pos[a * 3 + 1], 6), round(pos[a * 3 + 2], 6))
            kb = (round(pos[b * 3], 6), round(pos[b * 3 + 1], 6), round(pos[b * 3 + 2], 6))
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
        a3, b3, c3 = tri[0] * 3, tri[1] * 3, tri[2] * 3
        vol += (pos[a3] * (pos[b3 + 1] * pos[c3 + 2] - pos[b3 + 2] * pos[c3 + 1])
                - pos[a3 + 1] * (pos[b3] * pos[c3 + 2] - pos[b3 + 2] * pos[c3])
                + pos[a3 + 2] * (pos[b3] * pos[c3 + 1] - pos[b3 + 1] * pos[c3])) / 6.0
    closed = bool(edges) and all(n == 2 for n in edges.values())
    return {"closed": closed, "volume_mm3": vol,
            "triangles": len(idx) // 3, "vertices": len(pos) // 3}
```

- [ ] **Step 3 : GREEN + commit**

run-tests -Filter cards_forge3d → PASS.
```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): relief ferme par construction et quad - geometrie locale prouvee de P9"
```

---

### Task 3: `scene_writer` — UN document glTF propre, écrit juste du premier coup

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Test: `backend/tests/test_cards_forge3d.py`

Écrire, PAS rafistoler : le writer produit directement des bornes d'accesseurs exactes
(calculées sur les octets qu'il vient d'empaqueter), aucun champ generator/copyright,
samplers CLAMP_TO_EDGE, un nœud racine « carte3d » à l'ÉCHELLE PHYSIQUE (mm → m,
scale 0.001) portant un enfant par élément nommé par son rôle. Textures PNG embarquées
dans le buffer (les octets ESTAMPILLÉS de la phase 1, tels quels — mêmes SHA que le
manifeste). Matériau par élément : baseColorTexture = la couche, alphaMode BLEND pour
les plans, OPAQUE pour les reliefs, doubleSided pour les plans (une feuille se voit des
deux côtés), false pour les reliefs (solides fermés — doctrine P8).

- [ ] **Step 1 : tests en RED**

```python
def _read_glb(data: bytes):
    import struct as _s
    assert data[:4] == b"glTF"
    doc_len = _s.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + doc_len].decode("utf-8").rstrip("\x00 "))
    off = 20 + doc_len
    binv = b""
    if off < len(data):
        blen = _s.unpack("<I", data[off:off + 4])[0]
        binv = data[off + 8:off + 8 + blen]
    return doc, binv


def test_le_glb_assemble_est_propre_des_l_ecriture():
    """Bornes EXACTES, zéro identité, CLAMP, échelle physique — pas une
    rustine post-hoc : le writer écrit juste du premier coup, et ce test
    relit les octets pour le prouver (doctrine P8, re-mesurée ici)."""
    from PIL import Image
    from app.services.cards import forge3d as F9
    png = io.BytesIO(); Image.new("RGBA", (8, 8), (200, 30, 30, 255)).save(png, "PNG")
    elements = [
        {"name": "cadre", "mesh": F9.quad_mesh(63.0, 88.0), "png": png.getvalue(),
         "alpha": True, "z_mm": 0.0},
        {"name": "relief", "mesh": F9.relief_mesh(Image.new("L", (16, 16), 255),
                                                  63.0, 88.0, 1.0, 0.3, 8),
         "png": png.getvalue(), "alpha": False, "z_mm": 0.4},
    ]
    glb = F9.write_scene_glb(elements, name="carte3d",
                             extras={"deck": "test", "unit": "metre"})
    doc, binv = _read_glb(glb)
    # 1. identité : AUCUN champ interdit, nulle part
    plat = json.dumps(doc)
    for mot in ("generator", "copyright", "author", "producer"):
        assert f'"{mot}"' not in plat, mot
    # 2. bornes exactes : re-mesure des float32 du buffer, écart zéro exigé
    import struct as _s
    for acc in doc["accessors"]:
        if acc.get("componentType") != 5126 or "min" not in acc:
            continue
        bv = doc["bufferViews"][acc["bufferView"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        n = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[acc["type"]]
        lo = [float("inf")] * n; hi = [float("-inf")] * n
        for e in range(acc["count"]):
            vals = _s.unpack_from("<" + "f" * n, binv, off + e * n * 4)
            for c in range(n):
                lo[c] = min(lo[c], vals[c]); hi[c] = max(hi[c], vals[c])
        assert acc["min"] == lo and acc["max"] == hi, "bornes inexactes"
    # 3. CLAMP partout, échelle physique sur la racine, enfants nommés
    for s in doc.get("samplers", []):
        assert s["wrapS"] == 33071 and s["wrapT"] == 33071
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert racine["scale"] == [0.001, 0.001, 0.001]
    noms = [doc["nodes"][k]["name"] for k in racine["children"]]
    assert noms == ["cadre", "relief"]
    # 4. l'écart z du second élément est porté par SON nœud (translation mm)
    assert doc["nodes"][racine["children"][1]]["translation"][2] == 0.4
    # 5. matériaux : BLEND pour le plan, OPAQUE non double face pour le relief
    m_plan = doc["materials"][doc["meshes"][0]["primitives"][0]["material"]]
    m_rel = doc["materials"][doc["meshes"][1]["primitives"][0]["material"]]
    assert m_plan["alphaMode"] == "BLEND" and m_plan["doubleSided"] is True
    assert m_rel.get("alphaMode", "OPAQUE") == "OPAQUE" and not m_rel.get("doubleSided")
```

- [ ] **Step 2 : implémentation de `write_scene_glb`**

Structure (le code complet suit ce squelette, ~150 lignes — l'engineer écrit chaque
partie en s'appuyant sur le test ci-dessus qui fixe TOUTES les exigences) :

```python
def write_scene_glb(elements: list, name: str, extras: dict) -> bytes:
    """UN document glTF multi-éléments, écrit JUSTE du premier coup :
    bornes exactes (calculées ici même sur les floats empaquetés), aucun champ
    d'identité (ce writer n'en émet simplement jamais), samplers CLAMP, racine
    à l'échelle physique mm->m, un enfant nommé par élément, translation z en
    mm portée par le nœud de l'élément. Textures : les PNG estampillés de la
    phase 1, embarqués tels quels (mêmes octets, mêmes SHA que le manifeste)."""
    import struct
    buf = bytearray()
    views, accessors, images, textures, materials, meshes, nodes = [], [], [], [], [], [], []

    def pad4():
        while len(buf) % 4:
            buf.append(0)

    def add_view(data: bytes, target=None) -> int:
        pad4()
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data),
                      **({"target": target} if target else {})})
        buf.extend(data)
        return len(views) - 1

    def add_accessor(vals, n, ctype, atype, target) -> int:
        data = struct.pack("<" + "f" * len(vals), *vals) if ctype == 5126 \
            else struct.pack("<" + "I" * len(vals), *vals)
        v = add_view(data, target)
        acc = {"bufferView": v, "componentType": ctype,
               "count": len(vals) // n, "type": atype}
        if ctype == 5126:
            acc["min"] = [min(vals[i::n]) for i in range(n)]
            acc["max"] = [max(vals[i::n]) for i in range(n)]
            # les bornes sont posées sur les float32 EXACTS : repasser par
            # struct garantit la valeur que le lecteur relira
            packed = struct.unpack("<" + "f" * len(vals), data)
            acc["min"] = [min(packed[i::n]) for i in range(n)]
            acc["max"] = [max(packed[i::n]) for i in range(n)]
        accessors.append(acc)
        return len(accessors) - 1

    sampler = 0   # un seul sampler CLAMP
    for k, el in enumerate(elements):
        m = el["mesh"]
        ip = add_accessor(m["positions"], 3, 5126, "VEC3", 34962)
        inm = add_accessor(m["normals"], 3, 5126, "VEC3", 34962)
        iuv = add_accessor(m["uvs"], 2, 5126, "VEC2", 34962)
        iix = add_accessor(m["indices"], 1, 5125, "SCALAR", 34963)
        img = add_view(el["png"])
        images.append({"bufferView": img, "mimeType": "image/png",
                       "name": el["name"]})
        textures.append({"sampler": sampler, "source": len(images) - 1})
        materials.append({
            "name": el["name"],
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": len(textures) - 1},
                "metallicFactor": 0.0, "roughnessFactor": 0.9},
            **({"alphaMode": "BLEND", "doubleSided": True} if el.get("alpha")
               else {})})
        meshes.append({"name": el["name"], "primitives": [{
            "attributes": {"POSITION": ip, "NORMAL": inm, "TEXCOORD_0": iuv},
            "indices": iix, "material": len(materials) - 1}]})
        nodes.append({"name": el["name"], "mesh": len(meshes) - 1,
                      **({"translation": [0.0, 0.0, float(el.get("z_mm") or 0.0)]}
                         if el.get("z_mm") else {})})
    # PAD FINAL AVANT de figer buffers[0].byteLength : l'ordre inverse declare
    # un byteLength plus court que le chunk BIN reellement ecrit (mesure en
    # tache 3 : 12359 declare vs 12360 ecrit, PNG de 79 octets non aligne).
    pad4()
    racine = {"name": str(name)[:60], "scale": [0.001, 0.001, 0.001],
              "children": list(range(len(nodes))), "extras": extras}
    nodes.append(racine)
    doc = {"asset": {"version": "2.0", "extras": extras},
           "scene": 0, "scenes": [{"name": str(name)[:60], "nodes": [len(nodes) - 1]}],
           "nodes": nodes, "meshes": meshes, "materials": materials,
           "textures": textures, "images": images,
           "samplers": [{"wrapS": 33071, "wrapT": 33071}],
           "accessors": accessors, "bufferViews": views,
           "buffers": [{"byteLength": len(buf)}]}
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(buf)
    out = struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
    return out
```

- [ ] **Step 3 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): scene_writer glTF - bornes exactes, zero identite, CLAMP, echelle physique, ecrit juste du premier coup"
```

---

### Task 4: `POST /build3d` — exécuter le graphe gratuit, livrer l'artefact

**Files:**
- Modify: `backend/app/services/cards/forge3d.py`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : tests en RED**

```python
def test_le_graphe_gratuit_produit_un_glb_et_son_metadata():
    """Bout en bout backend : couches livrées (réutilise l'export de la
    phase 1) -> graphe par défaut -> GLB assemblé + metadata.json ERC-721 +
    bordereau ; STL refusé avec MOTIF (des plans ne sont pas un solide)."""
    did = _deck("Graphe gratuit")
    couches, composite = _couches_synthetiques()
    files = [("layers", (f"{nom}.png", _png(im), "image/png"))
             for nom, im in couches.items()]
    files.append(("composite", ("composite.png", _png(composite), "image/png")))
    r = _api("POST", f"/api/cards/{did}/forge3d/layers", files=files,
             data={"side": "front", "card": "0", "paper": "#ffffff",
                   "modes": json.dumps({n: "isolee" for n in couches}),
                   "client_proof": json.dumps({"stack_ok": True, "diff_px": 0})})
    assert r.status_code == 200, r.text

    graphe = {"nodes": [
        {"id": "s1", "kind": "layer", "role": "fond-matiere", "side": "front"},
        {"id": "t1", "kind": "plane", "depth_mm": 0.0},
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "essai3d"}],
        "edges": [{"from": "s1", "to": "t1"}, {"from": "t1", "to": "asm"},
                  {"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r2 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe, "card": 0})
    assert r2.status_code == 200, r2.text
    b = r2.json()["artifact"]

    # le GLB : relu, 2 éléments nommés par leurs rôles, échelle physique
    glb = _api("GET", f"/api/cards/{did}/forge3d/file/{b['glb']['name']}").content
    doc, _ = _read_glb(glb)
    racine = doc["nodes"][doc["scenes"][0]["nodes"][0]]
    assert [doc["nodes"][k]["name"] for k in racine["children"]] == \
        ["fond-matiere", "cadre"]
    # metadata.json : ERC-721 compatible, attributs mesurés
    meta = json.loads(_api("GET", f"/api/cards/{did}/forge3d/file/{b['metadata']['name']}").content)
    assert meta["name"] and meta["image"] and meta["animation_url"]
    types = {a["trait_type"]: a["value"] for a in meta["attributes"]}
    assert types["deck"] and types["elements_3d"] == 2 and types["engines"] == "local"
    # STL : REFUSÉ avec motif (le plan n'est pas fermé) — jamais un fichier faux
    assert b["stl"]["written"] is False
    assert "ferme" in b["stl"]["why"] or "fermé" in b["stl"]["why"]

    # le graphe 100 % relief, lui, obtient son STL
    graphe2 = {"nodes": [
        {"id": "s2", "kind": "layer", "role": "cadre", "side": "front"},
        {"id": "t2", "kind": "relief", "depth_mm": 1.0, "base_mm": 0.3, "grid": 48},
        {"id": "asm", "kind": "assemble"},
        {"id": "art", "kind": "artifact", "name": "relief3d"}],
        "edges": [{"from": "s2", "to": "t2"}, {"from": "t2", "to": "asm"},
                  {"from": "asm", "to": "art"}]}
    r3 = _api("POST", f"/api/cards/{did}/forge3d/build3d",
              json={"graph": graphe2, "card": 0})
    b3 = r3.json()["artifact"]
    assert b3["stl"]["written"] is True
    stl = _api("GET", f"/api/cards/{did}/forge3d/file/{b3['stl']['name']}").content
    assert len(stl) == 84 + 50 * struct.unpack("<I", stl[80:84])[0]


def test_un_graphe_sans_couches_livrees_fait_409_motive():
    did = _deck("Sans couches")
    r = _api("POST", f"/api/cards/{did}/forge3d/build3d",
             json={"graph": {"nodes": [], "edges": []}, "card": 0})
    assert r.status_code == 409
    assert "couches" in r.json()["detail"]
```

- [ ] **Step 2 : implémentation de la route**

Points imposés (le corps suit les patrons déjà en place dans ce fichier) :
- gardes deck (400/404) puis `clean_graph(body.get("graph"))` ; `card` par garde
  numérique ; TOUT le travail dans `def work():` → `asyncio.to_thread` (NOTE de revue
  du plan phase 1, obligatoire) ;
- résolution des chaînes `layer→(plane|relief)→assemble` : pour chaque traitement,
  retrouver sa source par les edges ; la couche est lue dans
  `outputs/decks/{did}/forge3d/{role}_c{NN}_{side}.png` (les octets ESTAMPILLÉS) ; si
  absente → 409 motivé (« exporte les couches d'abord ») ;
- `plane` → `quad_mesh` + z du nœud ; `relief` → `relief_mesh` sur le canal alpha de
  la couche + z ; l'ORDRE des éléments = l'ordre des nœuds du graphe ;
- `write_scene_glb(elements, name, extras)` avec extras {deck, card, format,
  size_mm, unit: "metre", schema: "card-3d/artifact@1"} ;
- **metadata.json ERC-721** :
```python
    meta = {
        "name": f"{doc_name} — carte {card_label}",
        "description": "Carte 3D par éléments séparés, construite localement.",
        "image": f"{art_name}_preview.png",
        "animation_url": f"{art_name}.glb",
        "attributes": [
            {"trait_type": "deck", "value": doc_name},
            {"trait_type": "carte", "value": card_label},
            {"trait_type": "elements_3d", "value": len(elements)},
            {"trait_type": "engines", "value": "local"},
            {"trait_type": "schema", "value": "card-3d/artifact@1"},
        ],
    }
```
  (l'aperçu est déclaré par NOM ; il n'existe qu'après la capture client de la
  Task 5 — le bordereau dit `preview: {expected: name, written: false}` tant qu'il
  n'est pas téléversé : une déclaration honnête, pas un mensonge) ;
- **STL** : gate sur le drapeau `closed` DÉCLARÉ PAR LES CONSTRUCTEURS de maillage
  (`relief_mesh` pose `"closed": True` dans son dict — fermeture topologique prouvée
  une fois pour toutes par son test unitaire, indépendante du contenu alpha ;
  `quad_mesh` pose `False`). JAMAIS de re-mesure par requête : `mesh_measures` à
  grid max coûte 7 s + ~340 Mo de pic PAR ÉLÉMENT (mesuré en revue) pour re-prouver
  un théorème structurel — il reste l'instrument des TESTS. La route ne fait
  jamais elle-même une affirmation de fermeture sur un maillage qu'elle n'a pas
  construit. Si un élément n'est pas fermé : `{"written": False, "why": "…pas un
  solide ferme…"}` — writer binaire local (~20 lignes, en mm, en-tête 80 octets
  SANS nom d'outil) ;
- bordereau : fichiers écrits `{name}.glb`, `{name}.metadata.json`, `{name}.stl?`
  sous `outputs/decks/{did}/forge3d/`, pesés ; `graph_used` = le graphe NETTOYÉ
  (celui qui a réellement tourné) ;
- `POST /preview/{art}` (petite route sœur) : reçoit le PNG de capture model-viewer
  (corps brut, borne 8 Mo, PNG vérifié) et l'écrit `{art}_preview.png` — le patron
  « rien de la carte n'est rendu au serveur ».

- [ ] **Step 3 : GREEN + commit**

```bash
git add backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): POST build3d - graphe gratuit execute, GLB assemble, metadata ERC-721, STL prouve ou refuse motive"
```

---

### Task 5: L'écran du graphe — liste de nœuds, aperçu, artefact

**Files:**
- Modify: `frontend/cardforge/js/mod-forge3d.js`
- Modify: `frontend/cardforge/css/mod-forge3d.css`
- Test: `backend/tests/test_cards_forge3d.py`

- [ ] **Step 1 : test de source en RED**

```python
def test_l_ecran_du_graphe_est_une_liste_honnete_et_un_apercu_reel():
    src = JS.read_text(encoding="utf-8")
    rendu = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    # un rang par couche : traitement + profondeur, bornés par /info (jamais
    # de bornes recopiées en dur dans le HTML)
    assert 'id="cf-forge3d-graph"' in rendu
    assert "defaultGraph(" in rendu
    # le POST part avec le graphe de l'état, la réponse peint le bordereau
    corps = rendu.split("async function build3d(")[1].split("\n  }")[0]
    assert 'M.api.post("build3d"' in corps
    assert "artifact" in corps
    # l'aperçu est le VRAI fichier livré, chargé dans model-viewer par blob
    assert "model-viewer" in rendu
    # la capture d'aperçu part au serveur (rien n'est rendu côté serveur)
    assert "toBlob" in rendu and "preview/" in rendu
    # STL refusé : le motif du backend est AFFICHÉ, jamais réécrit
    assert "stl.why" in rendu or 'stl["why"]' in rendu or "stl && !" in rendu
```

- [ ] **Step 2 : implémentation**

Sections du panneau (sous l'export de couches existant) :
1. **« Graphe 3D »** (`#cf-forge3d-graph`) : peint depuis `doc.forge3d.graph` (ou
   propose « construire le graphe par défaut » si null et qu'un manifeste existe —
   bouton qui fait `M.patch({graph: defaultGraph(dernierManifeste)})`). Un rang par
   nœud de traitement : rôle source · sélecteur plan/relief · champs profondeur
   (bornes lues de `GET /info` — les publier dans /info : `graph_limits` avec
   PLANE_DEPTH_MM, RELIEF_*) · côté. Chaque édition = `M.patch` (annulable).
2. **« Construire »** (`#cf-forge3d-build`) : POST build3d {graph, card:
   CF.current()}, busy pendant le travail, puis bordereau : GLB (poids, bouton
   téléchargement par provenance — MÊME patron grabZip), metadata.json, STL écrit
   ou refus avec le MOTIF du backend affiché tel quel.
3. **Aperçu** : `<model-viewer>` (le script est déjà chargé par la coquille) —
   src = blob URL du GLB téléchargé par `M.api.blob` (pas d'URL directe : la
   provenance d'abord), camera-controls, auto-rotate. Après chargement, bouton
   « figer l'aperçu » → `modelViewer.toBlob()` → POST `preview/{art}` → le
   metadata.json cesse d'être en attente d'image.
4. CSS : rangées du graphe, viewer 300px — tout scopé `.cf-forge3d`.

- [ ] **Step 3 : GREEN + vérifications complètes + commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-tests.ps1 -Filter cards_forge3d
python scripts\qa\lint_cardforge.py --module forge3d
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qa\cf_deploy.ps1 -Backend
node frontend\cardforge\qa\test_core_contract.mjs --contract
```
Vérification navigateur RÉELLE : exporter les couches d'un deck réel → graphe par
défaut → Construire → aperçu tourne dans model-viewer → figer l'aperçu → télécharger
GLB + metadata. Rapporter ce qui a été vu.
```bash
git add frontend/cardforge/js/mod-forge3d.js frontend/cardforge/css/mod-forge3d.css backend/app/services/cards/forge3d.py backend/tests/test_cards_forge3d.py
git commit -m "feat(cardforge): ecran du graphe P9 - liste de noeuds, build3d, apercu model-viewer, capture, bordereau"
```

---

### Task 6: Intégration finale 2a

- [ ] Suite complète : `run-tests.ps1 -Filter cards` → 10/10.
- [ ] `lint_cardforge.py` complet → 0 violation ; `--geom` et `--contract` → tenus.
- [ ] `cf_deploy.ps1 -Check` → 0 écart.
- [ ] Commit de clôture éventuel + PUSH `claude/audit-cleanup-2026-08`.

---

## Auto-revue du plan

- **Spec §5 couverte pour la part 2a** : graphe dans doc.forge3d (§5.1), nœuds
  layer/plane(=plan)/relief(=extrusion locale v1)/assemble/artifact (§5.2 — mesh3d et
  material sont 2b), graphe par défaut parallaxe (§5.2), assembleur (§5.4 : ici un
  WRITER propre — la fusion de GLB EXTERNES arrive en 2b avec mesh3d, c'est là qu'elle
  devient nécessaire), artefact GLB + metadata ERC-721 + aperçu client + STL prouvé ou
  refusé motivé (§5.5). Écart de spec assumé et motivé : « STL/3MF via builders P8 » du
  §5.5 violerait la règle zéro-import-pièce→pièce constatée en phase 1 — STL en writer
  local minimal, 3MF DIFFÉRÉ (l'échantillonnage couleur de build_3mf est trop gros pour
  une copie ; à trancher en 2b : montée de build_3mf dans un service partagé).
- **Placeholders** : aucun TBD ; les deux blocs « suit les patrons du fichier »
  (Task 4 route, Task 5 UI) s'appuient sur des patrons DÉJÀ dans les mêmes fichiers
  (post_layers, exportLayers/paintSlip/grabZip) avec les exigences fixées par les
  tests fournis.
- **Cohérence de types** : `relief_mesh`/`quad_mesh` → `{positions, normals, uvs,
  indices}` consommé par `write_scene_glb` et `mesh_measures` ; `clean_graph` est la
  SEULE porte d'entrée du graphe côté backend ; les noms de fichiers consomment le
  nommage post-compléments `_c{NN}_{side}`.
- **Périmètre** : mesh3d/matières/iridescence/anisotropy/KHR = phase 2b ; canvas nodal
  visuel = plus tard ; deck-scope 3D = plus tard.
