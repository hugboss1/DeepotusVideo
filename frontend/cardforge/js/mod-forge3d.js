"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 09 · Forge 3D   [P9]
   Proprietaire exclusif de : doc.forge3d · AUCUN z (ce module ne peint pas) ·
   /api/cards/<did>/forge3d/* · prefixe DOM cf-forge3d-
   feuille : css/mod-forge3d.css (tout selecteur y contient .cf-forge3d)

   Export par couches (phase 1) + l'ecran du graphe (phase 2a) : liste de
   noeuds de traitement (un rang par couche livree), construction du graphe
   100 % GRATUIT (POST build3d), apercu REEL dans <model-viewer> (le fichier
   livre, jamais un rendu invente), capture d'apercu figee cote client (POST
   preview/<art>), bordereau qui peint UNIQUEMENT la reponse mesuree — jamais
   l'intention envoyee. Ce module n'a AUCUN painter : il lit le rendu, il n'y
   dessine jamais.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-forge3d: js/core.js doit etre charge avant ce fichier");

  /* ── LA TABLE DES COUCHES — BLOC MIROIR ─────────────────────────────────
     ═══ CF-FORGE3D-LAYERS-BEGIN ═══
     Le miroir Python est dans backend/app/services/cards/forge3d.py, entre
     les mêmes marqueurs ; test_cards_forge3d compare les deux champ à champ
     et dans l'ordre.
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

  const M = CF.register({
    id: "forge3d",
    title: "Forge 3D",
    icon: "⬢",
    order: 9,
    state: {
      last_export: null,        /* horodatage et compte de faces du dernier
                                    export ; le bordereau n'est pas persisté */
      graph: null,               /* le graphe {nodes, edges} — null = jamais
                                    construit ; le graphe PAR DÉFAUT est
                                    proposé dès qu'un export de couches existe */
    },
    init(host) {
      host.innerHTML = shell();
      wire(host);
    },
  });

  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);

  /* état éphémère du panneau — AUCUN n'est persisté (patron mod-gltf.js :
     INFO/BUILD/ATLAS/BUSY sont eux aussi hors de `state`). */
  let INFO = null;              /* dernière réponse de GET info (graph_limits) */
  let LAST_MANIFEST = null;     /* le manifeste du DERNIER export reçu (POST
                                    layers) — seed du graphe ; le bouton seed
                                    n'existe que s'il est posé */
  let ARTIFACT = null;          /* le dernier bordereau de build3d */
  let PREVIEW_URL = null;       /* objectURL du GLB monté dans model-viewer —
                                    révoquée avant d'en poser une nouvelle */
  const HIST = [];              /* pile d'annulation des éditions du graphe —
                                    patron mod-gltf.js:HIST, 40 entrées max */

  function get(k) { return CF.get("forge3d." + k, null); }

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

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Graphe 3D</b>'
      + '<button class="lnk" id="cf-forge3d-undo" type="button" '
      + 'title="annule la dernière édition du graphe">↶ annuler</button>'
      + '</header>'
      + '<p class="hint">Un traitement par couche livrée : plan texturé (gratuit) '
      + 'ou relief extrudé (gratuit, solide fermé imprimable). Chaque champ édité '
      + 'patche aussitôt le graphe — annulable.</p>'
      + '<div id="cf-forge3d-graph"></div>'
      + '</section>'

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Construire</b></header>'
      + '<button class="btn strong" id="cf-forge3d-build" type="button">'
      + 'Construire l\'artefact 3D</button>'
      + '<p class="hint" id="cf-forge3d-build-status"></p>'
      + '<div id="cf-forge3d-build-slip"></div>'
      + '</section>'

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Aperçu</b>'
      + '<button class="btn sm" id="cf-forge3d-freeze" type="button" disabled>'
      + 'figer l\'aperçu</button>'
      + '</header>'
      + '<div class="cf-forge3d-view" id="cf-forge3d-view"></div>'
      + '<p class="hint" id="cf-forge3d-freeze-status"></p>'
      + '</section>'
      + '</div>';
  }

  function wire(host) {
    $("#cf-forge3d-export").addEventListener("click", () => exportLayers());
    const slip = $("#cf-forge3d-slip");
    if (slip) slip.addEventListener("click", onSlipClick);
    const graphHost = $("#cf-forge3d-graph");
    if (graphHost) {
      graphHost.addEventListener("change", onGraphChange);
      graphHost.addEventListener("click", onGraphClick);
    }
    const undoBtn = $("#cf-forge3d-undo");
    if (undoBtn) undoBtn.addEventListener("click", () => undoGraph());
    $("#cf-forge3d-build").addEventListener("click", () => build3d());
    const buildSlip = $("#cf-forge3d-build-slip");
    if (buildSlip) buildSlip.addEventListener("click", onSlipClick);
    $("#cf-forge3d-freeze").addEventListener("click", () => freezePreview());
    refreshInfo();
    paintGraph();
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* Le meme poids binaire (CEI 80000-13) que le reste du lab (mod-gltf.js,
     mod-print.js) : « Mo » decimal ne se retrouve jamais sur le disque. */
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1048576) return (v / 1024).toFixed(1) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     EXPORT — DEUX TEMPS, pour que « rien n'a été envoyé » soit vrai PAR
     CONSTRUCTION et non par discipline de lecture du code.
     Temps 1 (preuve) : les DEUX faces sont rendues et prouvées (CF.layers) ;
     la moindre erreur de painter ou le moindre echec d'empilement NOMME la
     face fautive et REND (aucun FormData, aucun fetch n'existe encore a cet
     instant du code — pas seulement « avant d'etre appele »). Temps 2
     (envoi) : uniquement atteint si les deux faces ont passe le temps 1 —
     chaque face part alors avec SA preuve mesuree.
     Note memoire : les toiles des deux faces (12 couches + 2 composites, au
     lieu de 6+1) restent retenues entre les deux temps — un geste ponctuel
     sur clic, pas une boucle : acceptable. */
  async function exportLayers() {
    /* la carte courante, lue UNE SEULE FOIS en tete de fonction : un
       changement de carte au rail pendant l'export (temps 1 -> temps 2) ne
       peut plus desynchroniser la preuve (CF.layers) de l'etiquette envoyee
       (fd.append("card", ...)) — les deux lisaient CF.current() separement. */
    const carte = (CF.current ? CF.current() : 0);
    const status = $("#cf-forge3d-status");
    const btn = $("#cf-forge3d-export");
    btn.disabled = true;
    try {
      const sides = ["front", "back"];

      /* ── TEMPS 1 : PREUVE DES DEUX FACES, AUCUN RESEAU ────────────────── */
      const preuves = [];
      for (let s = 0; s < sides.length; s++) {
        const face = sides[s];
        status.textContent = "rendu des couches ("
          + (face === "front" ? "recto" : "verso") + ")…";
        const L = await CF.layers(carte, { face: face, groups: LAYER_ROLES });
        if (L.errors && L.errors.length) {
          /* une couche rendue avec une erreur de painter n'est pas une couche
             de confiance : on nomme (face + painters) et on n'envoie rien. */
          status.textContent = "erreur de painter pendant le rendu des couches ("
            + face + " : " + L.errors.map((e) => e.id + " z=" + e.z).join(", ")
            + ") — rien n'a été envoyé.";
          M.toast("rendu des couches en erreur : export refusé", true);
          return;
        }
        if (!L.stack_ok) {
          /* la preuve a echoue : on NOMME et on n'envoie RIEN — un ZIP faux
             est pire qu'un echec dit. */
          const fautive = L.layers.filter((l) => l.mode === "empreinte")
            .map((l) => l.role).join(", ") || "inconnue";
          status.textContent = "preuve d'empilement ÉCHOUÉE (" + face
            + ") — couches en cause : " + fautive + ". Rien n'a été envoyé.";
          M.toast("empilement non reproduit : export refusé", true);
          return;
        }
        preuves.push({ face: face, L: L });
      }

      /* ── TEMPS 2 : LES DEUX FACES SONT PROUVEES — ON ENVOIE ───────────── */
      const results = [];
      for (let p = 0; p < preuves.length; p++) {
        const face = preuves[p].face, L = preuves[p].L;
        const fd = new FormData();
        for (let k = 0; k < L.layers.length; k++) {
          const lay = L.layers[k];
          fd.append("layers", await CF.layerBlob(lay.canvas), lay.role + ".png");
        }
        fd.append("composite", await CF.layerBlob(L.composite), "composite.png");
        fd.append("side", face);
        fd.append("card", String(carte));
        fd.append("paper", L.paper || "#ffffff");
        const modes = {};
        L.layers.forEach((l) => { modes[l.role] = l.mode; });
        fd.append("modes", JSON.stringify(modes));
        fd.append("client_proof", JSON.stringify({ stack_ok: L.stack_ok, diff_px: 0 }));
        status.textContent = "téléversement (" + face + ")…";
        const rep = await M.api.post("layers", fd);
        results.push(rep.layers);
        /* seed du graphe par défaut (Task 5) : le RECTO fait foi (le backend
           défaut side="front", l'écran affiche recto par défaut, et l'aperçu
           figé devient l'image ERC-721 — l'identité d'une carte est sa
           face) ; on ne retombe sur le verso que si le recto, pour une
           raison quelconque, n'a jamais été reçu. */
        if (face === "front" || !LAST_MANIFEST) LAST_MANIFEST = rep.layers;
      }
      M.patch({ last_export: { at: new Date().toISOString(), sides: results.length } });
      paintSlip(results);
      paintGraph();
      status.textContent = "couches livrées, preuve tenue des deux côtés.";
    } catch (e) {
      status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      btn.disabled = false;
    }
  }

  /* ── LE BORDEREAU — peint depuis la REPONSE mesuree, jamais depuis
     l'intention envoyee : role/mode/couverture/poids viennent des lignes du
     manifeste, l'ecart d'empilement vient de proof.backend.diff_px (second
     avis PIL, cote serveur). Les vignettes chargent le PNG livre par
     GET file/<nom> (patron mod-gltf.js:loadProof/mountViewer — un <img src>
     n'est pas un telechargement, juste une lecture d'apercu). */
  function paintSlip(results) {
    const slip = $("#cf-forge3d-slip");
    if (!slip) return;
    slip.innerHTML = results.map((man) => {
      const rows = man.layers.map((l) =>
        '<div class="cf-forge3d-lay"><img src="'
        + esc(M.api.url("file/" + encodeURIComponent(l.file)))
        + '" alt="" loading="lazy" decoding="async">'
        + '<span class="mono">' + esc(l.role) + " · " + esc(l.mode) + " · "
        + Number(l.coverage_pct) + " % · " + weight(l.bytes) + "</span></div>").join("");
      return '<h4>' + (man.side === "front" ? "Recto" : "Verso") + '</h4>' + rows
        + '<p class="mono">empilement : navigateur strict OK · second avis PIL '
        + Number(man.proof.backend.diff_px) + ' px d\'écart · '
        + '<button class="btn sm" type="button" data-act="grab-zip" data-name="'
        + esc(man.zip.name) + '">' + esc(man.zip.name) + " ("
        + weight(man.zip.bytes) + ')</button></p>';
    }).join("");
  }

  /* ── TELECHARGEMENT — meme provenance que le reste du lab : un fichier
     livre n'est jamais un <a href> direct (patron mod-gltf.js:grab). Le blob
     vient de M.api.blob (mint), donc M.download (alias de CF.download)
     l'accepte — un lien nu servirait un blob de provenance inconnue.
     GENERIQUE (revue) : sert aussi bien le ZIP des couches que le GLB, le
     metadata.json ou le STL du bordereau de build3d — un nom livre est un
     nom livre, peu importe la section qui l'affiche. */
  async function grabZip(name) {
    if (!name) return;
    try {
      const b = await M.api.blob("GET", "file/" + encodeURIComponent(name));
      M.download(b, name);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    }
  }

  function onSlipClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    const act = b.getAttribute("data-act");
    if (act === "grab-zip" || act === "grab-file") {
      e.preventDefault();
      grabZip(b.getAttribute("data-name"));
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE GRAPHE — liste structurée de nœuds (pas un canvas nodal, Task 5 du
     plan) : un rang par nœud de TRAITEMENT (plane/relief), lu depuis l'edge
     layer -> traitement qui le sourcE. Chaque édition clone le graphe (state
     immuable : le patch précédent l'a deep-frozen), modifie le clone, puis
     M.patch — jamais une mutation en place.
     ═══════════════════════════════════════════════════════════════════════ */
  async function refreshInfo() {
    try {
      INFO = await M.api.get("info");
    } catch (e) {
      INFO = null;
    }
    paintGraph();
  }

  /* {layer, proc} pour chaque edge layer -> (plane|relief) : c'est la MEME
     regle de resolution que le backend (_resolve_graph_elements) — la
     premiere arete entrante d'un traitement en dicte la source affichee ;
     les sources surnumeraires restent dans le graphe (le backend les avoue
     au bordereau via `ignored` apres construction), l'ecran ne les cache
     pas, il ne leur donne simplement pas de second rang. */
  function graphRows(graph) {
    const byId = {};
    graph.nodes.forEach((n) => { byId[n.id] = n; });
    const rows = [];
    graph.edges.forEach((e) => {
      const from = byId[e.from], to = byId[e.to];
      if (from && to && from.kind === "layer"
        && (to.kind === "plane" || to.kind === "relief")
        && !rows.some((r) => r.proc.id === to.id)) {
        rows.push({ layer: from, proc: to });
      }
    });
    return rows;
  }

  function rowHtml(r, lim) {
    const proc = r.proc, layer = r.layer;
    const isRelief = proc.kind === "relief";
    const pd = (lim && lim.plane_depth_mm) || [0, 0];
    const rdMax = lim ? lim.relief_depth_mm_max : 0;
    const rb = (lim && lim.relief_base_mm) || [0, 0];
    const rg = (lim && lim.relief_grid) || [0, 0];
    const depthMin = isRelief ? 0 : pd[0];
    const depthMax = isRelief ? rdMax : pd[1];
    return '<div class="cf-forge3d-row" data-proc="' + esc(proc.id) + '">'
      + '<span class="mono cf-forge3d-role">' + esc(layer.role || "composite") + '</span>'
      + '<select class="cf-forge3d-kind" data-field="kind">'
      + '<option value="plane"' + (isRelief ? "" : " selected") + '>plan</option>'
      + '<option value="relief"' + (isRelief ? " selected" : "") + '>relief</option>'
      + '</select>'
      + '<label class="cf-forge3d-num">profondeur<input type="number" data-field="depth_mm" '
      + 'value="' + (proc.depth_mm != null ? proc.depth_mm : "") + '" '
      + 'min="' + depthMin + '" max="' + depthMax + '" step="0.05"><i>mm</i></label>'
      + (isRelief
        ? ('<label class="cf-forge3d-num">base<input type="number" data-field="base_mm" '
          + 'value="' + (proc.base_mm != null ? proc.base_mm : "") + '" '
          + 'min="' + rb[0] + '" max="' + rb[1] + '" step="0.05"><i>mm</i></label>'
          + '<label class="cf-forge3d-num">grille<input type="number" data-field="grid" '
          + 'value="' + (proc.grid != null ? proc.grid : "") + '" '
          + 'min="' + rg[0] + '" max="' + rg[1] + '" step="1"></label>')
        : "")
      + '<select class="cf-forge3d-side" data-field="side">'
      + '<option value="front"' + (layer.side === "back" ? "" : " selected") + '>recto</option>'
      + '<option value="back"' + (layer.side === "back" ? " selected" : "") + '>verso</option>'
      + '</select>'
      + '</div>';
  }

  /* le bouton seed : identique dans les deux branches (graphe absent ou déjà
     posé), seul l'id et le libellé changent — le re-seed d'un graphe déjà
     construit passe par la MÊME pile d'annulation que toute autre édition
     (patron « re-seed = juste une édition de plus »). */
  function seedButtonHtml(id, label) {
    return '<button class="btn sm" id="' + id + '" type="button" '
      + 'data-act="seed-default">' + esc(label) + '</button>';
  }

  function paintGraph() {
    const host = $("#cf-forge3d-graph");
    if (!host) return;
    const graph = get("graph");
    if (!graph) {
      host.innerHTML = LAST_MANIFEST
        ? ('<p class="hint">Aucun graphe construit pour le moment.</p>'
          + seedButtonHtml("cf-forge3d-graph-seed", "construire le graphe par défaut"))
        : '<p class="hint">Exportez les couches d\'abord (section ci-dessus) '
          + 'pour proposer un graphe par défaut.</p>';
      return;
    }
    const rows = graphRows(graph);
    const lim = (INFO && INFO.graph_limits) || null;
    const body = rows.length
      ? rows.map((r) => rowHtml(r, lim)).join("")
      : '<p class="hint">Graphe sans traitement — aucune couche reliée à un '
        + 'plan ou un relief.</p>';
    /* le re-seed reste OFFERT même une fois le graphe construit : abîmer son
       graphe n'est plus une impasse — et comme il passe par setGraph, il
       reste lui-même annulable. */
    const reseed = LAST_MANIFEST
      ? seedButtonHtml("cf-forge3d-reseed", "reconstruire le graphe par défaut")
      : "";
    host.innerHTML = body + reseed;
  }

  function onGraphClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    if (b.getAttribute("data-act") === "seed-default") {
      e.preventDefault();
      if (LAST_MANIFEST) setGraph(defaultGraph(LAST_MANIFEST), "graphe par défaut");
    }
  }

  function onGraphChange(e) {
    const row = e.target.closest ? e.target.closest(".cf-forge3d-row") : null;
    if (!row) return;
    const field = e.target.getAttribute("data-field");
    if (!field) return;
    editGraph(row.getAttribute("data-proc"), field, e.target.value);
  }

  /* ÉCRITURE + PILE D'ANNULATION (patron mod-gltf.js:set/undo) : chaque
     édition du graphe — champ par champ, ou un re-seed entier — pousse
     l'ANCIEN graphe sur `HIST` avant de patcher, jamais après : c'est cette
     valeur-là que `undoGraph` restaure. */
  function setGraph(next, label) {
    HIST.push({ before: get("graph"), label: label || "graphe" });
    if (HIST.length > 40) HIST.shift();
    M.patch({ graph: next });
    paintGraph();
  }

  function undoGraph() {
    const h = HIST.pop();
    if (!h) { M.toast("rien à annuler"); return; }
    M.patch({ graph: h.before });
    paintGraph();
    M.toast("annulé : " + h.label);
  }

  /* clone + modifie + setGraph : `graph` est deep-freeze par le CORE dès
     qu'il est posé (schema simple, fusion superficielle) — une mutation en
     place lèverait TypeError en mode strict. */
  function editGraph(procId, field, rawValue) {
    const graph = get("graph");
    if (!graph || !procId) return;
    const next = JSON.parse(JSON.stringify(graph));
    const proc = next.nodes.filter((n) => n.id === procId)[0];
    if (!proc) return;
    if (field === "kind") {
      proc.kind = (rawValue === "relief") ? "relief" : "plane";
    } else if (field === "side") {
      const edge = next.edges.filter((e) => e.to === procId)[0];
      const layer = edge ? next.nodes.filter((n) => n.id === edge.from)[0] : null;
      if (layer) layer.side = (rawValue === "back") ? "back" : "front";
    } else if (field === "grid") {
      const v = Math.round(Number(rawValue));
      if (isFinite(v)) proc.grid = v; else delete proc.grid;
    } else if (field === "depth_mm" || field === "base_mm") {
      const v = Number(rawValue);
      if (isFinite(v)) proc[field] = v; else delete proc[field];
    }
    setGraph(next, field);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     CONSTRUIRE — POST build3d {graph, card}, le bordereau peint UNIQUEMENT
     la réponse mesurée (jamais l'intention envoyée : `graph_used` est le
     graphe NETTOYÉ par le backend, pas celui qu'on vient de poster).
     ═══════════════════════════════════════════════════════════════════════ */
  async function build3d() {
    if (build3d.busy) return;
    const graph = get("graph");
    const btn = $("#cf-forge3d-build");
    const status = $("#cf-forge3d-build-status");
    if (!graph) {
      if (status) status.textContent = "construisez d'abord le graphe (par "
        + "défaut ou personnalisé), ci-dessus.";
      return;
    }
    build3d.busy = true;
    if (btn) btn.disabled = true;
    if (status) status.textContent = "construction…";
    try {
      const carte = (CF.current ? CF.current() : 0);
      const rep = await M.api.post("build3d", { graph: graph, card: carte });
      ARTIFACT = rep.artifact;
      paintArtifact(ARTIFACT);
      status.textContent = ARTIFACT.elements + " élément(s) — "
        + weight(ARTIFACT.glb.bytes) + " · " + ARTIFACT.ms.total + " ms.";
      await mountPreview(ARTIFACT.glb.name);
    } catch (e) {
      if (status) status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      build3d.busy = false;
      if (btn) btn.disabled = false;
    }
  }

  /* le nom de l'artefact : lu dans `graph_used` (ce que le backend a
     RÉELLEMENT construit), jamais dans le graphe posté — un nœud artifact
     jeté par clean_graph retomberait sur "artefact" cote serveur, jamais
     recopie en dur ici. */
  function artifactName(art) {
    const nodes = (art && art.graph_used && art.graph_used.nodes) || [];
    const n = nodes.filter((x) => x.kind === "artifact")[0];
    return (n && n.name) || "artefact";
  }

  /* ── LE BORDEREAU DE BUILD3D — peint depuis la REPONSE, jamais l'intention.
     GLB + metadata.json (+ STL si écrit) : même patron de téléchargement que
     paintSlip (provenance M.api.blob). Le motif STL refusé est affiché TEL
     QUEL (art.stl.why) — jamais réécrit par l'écran. `ignored` (le contrat
     d'honnêteté du backend) est rendu ligne par ligne s'il n'est pas vide. */
  function paintArtifact(art) {
    const slip = $("#cf-forge3d-build-slip");
    if (!slip || !art) return;
    const files = [
      { label: "GLB", name: art.glb.name, bytes: art.glb.bytes },
      { label: "metadata.json", name: art.metadata.name, bytes: art.metadata.bytes },
    ];
    let stlHtml;
    if (art.stl && art.stl.written) {
      files.push({ label: "STL", name: art.stl.name, bytes: art.stl.bytes });
      stlHtml = '<p class="mono">STL : imprimable, solide fermé prouvé.</p>';
    } else {
      stlHtml = '<p class="hint"><b>STL non fourni</b> : '
        + esc(art.stl.why) + '</p>';
    }
    const rows = files.map((f) =>
      '<div class="cf-forge3d-file"><span class="mono">' + esc(f.label) + " · "
      + esc(f.name) + " · " + weight(f.bytes) + '</span>'
      + '<button class="btn sm" type="button" data-act="grab-file" data-name="'
      + esc(f.name) + '">télécharger</button></div>').join("");
    const previewHtml = '<p class="hint">aperçu : ' + (art.preview.written
      ? "figé — " + esc(art.preview.expected)
      : "en attente (" + esc(art.preview.expected) + ")") + '</p>';
    const ignoredHtml = (art.ignored && art.ignored.length)
      ? ('<p class="hint"><b>éléments ignorés</b> — avoués, jamais tus :</p>'
        + '<ul class="cf-forge3d-ignored">'
        + art.ignored.map((i) => "<li class=\"mono\">" + esc(i.node) + " · "
          + esc(i.why) + "</li>").join("")
        + "</ul>")
      : "";
    slip.innerHTML = rows + stlHtml + previewHtml + ignoredHtml;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     APERÇU — <model-viewer> sur le VRAI fichier livré : la provenance
     d'abord (M.api.blob, pas une URL directe), objectURL révoquée avant
     d'en poser une nouvelle (patron mod-gltf.js:ATLAS/compose). Le script
     est déjà chargé par la coquille (index.html:23).
     ═══════════════════════════════════════════════════════════════════════ */
  async function mountPreview(name) {
    const host = $("#cf-forge3d-view");
    if (!host) return;
    if (typeof customElements === "undefined" || !customElements.get("model-viewer")) {
      host.innerHTML = '<p class="empty-note sm">La visionneuse 3D '
        + '(/assets/model-viewer.min.js) n\'est pas chargée. Le fichier, lui, '
        + 'est construit et téléchargeable.</p>';
      return;
    }
    try {
      const blob = await M.api.blob("GET", "file/" + encodeURIComponent(name));
      if (PREVIEW_URL) URL.revokeObjectURL(PREVIEW_URL);
      PREVIEW_URL = URL.createObjectURL(blob);
      const freeze = $("#cf-forge3d-freeze");
      let mv = $("#cf-forge3d-mv");
      if (!mv) {
        mv = document.createElement("model-viewer");
        mv.id = "cf-forge3d-mv";
        mv.setAttribute("camera-controls", "");
        mv.setAttribute("auto-rotate", "");
        mv.addEventListener("load", () => {
          const f = $("#cf-forge3d-freeze");
          if (f) f.disabled = false;
        });
        mv.addEventListener("error", () => {
          M.toast("la visionneuse n'a pas pu ouvrir le GLB", true);
        });
        host.innerHTML = "";
        host.appendChild(mv);
      }
      if (freeze) freeze.disabled = true;   /* re-verrouillé jusqu'au prochain load */
      mv.setAttribute("src", PREVIEW_URL);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    }
  }

  /* « figer l'aperçu » : modelViewer.toBlob() (API officielle 3.3.3) capture
     le rendu affiché, POST preview/<art> l'écrit tel quel côté serveur —
     RIEN de la carte n'est rendu au serveur (patron du domaine). Si toBlob()
     échoue (WebGL absent), toast honnête, pas de crash. */
  async function freezePreview() {
    const mv = $("#cf-forge3d-mv");
    const status = $("#cf-forge3d-freeze-status");
    if (!mv || !ARTIFACT) {
      M.toast("construisez et affichez l'aperçu d'abord", true);
      return;
    }
    const btn = $("#cf-forge3d-freeze");
    if (btn) btn.disabled = true;
    try {
      const blob = await mv.toBlob();
      const name = artifactName(ARTIFACT);
      const r = await M.api.raw("POST", "preview/" + encodeURIComponent(name), blob);
      if (!r.ok) {
        let d = null;
        try { d = await r.json(); } catch (err) { d = null; }
        throw new Error((d && d.detail) || ("aperçu refusé (" + r.status + ")"));
      }
      const d = await r.json();
      ARTIFACT = Object.assign({}, ARTIFACT, {
        preview: { expected: ARTIFACT.preview.expected, written: true },
      });
      paintArtifact(ARTIFACT);
      if (status) status.textContent = "aperçu figé — " + weight(d.preview.bytes) + ".";
      M.toast("aperçu figé");
    } catch (e) {
      if (status) status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }
})();
