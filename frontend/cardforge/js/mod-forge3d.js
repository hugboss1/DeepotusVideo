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

   Phase 2b — LES CHAINES ET L'ARGENT. Un rang devient une CHAINE
   couche -> traitement -> [matiere] -> [placement] -> assemblage, et le
   traitement peut desormais etre un MOTEUR 3D payant (mesh3d). D'ou trois
   engagements que cet ecran tient AVANT toute depense :
     · LE PRIX EST DIT AVANT. Moteurs, tarifs, credits, surcout ultra, bornes
       et matieres viennent TOUS de GET /info — aucune grille recopiee ici
       (le bloc miroir NODE_KINDS reste la seule table partagee). Le pied de
       page somme ce que « Lancer » coutera, nœud par nœud, et il compte
       comme PAYANT tout nœud dont il ne connait pas le prix.
     · LA PANNE EST DITE, PAS AVALEE. Cle Meshy absente (has_meshy), boutique
       de matieres ou grille de prix en panne (degraded / materials_degraded),
       refus HTTP du lancement (400/409/503/413) : le message part TEL QUEL a
       l'ecran, jamais un select vide muet ni un bouton qui echoue en silence.
     · L'ETAT VIENT DU JOB, PAS DE L'INTENTION. La chip d'un nœud est peinte
       depuis job.json (POST mesh3d/<nid> puis poll GET), et le `run_id` —
       opaque mais COMPARABLE — est confronte d'un poll a l'autre : s'il
       change, un AUTRE onglet a relance ce nœud, et on le DIT.
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
    { kind: "mesh3d", params: ["engine", "texture_prompt", "ultra"] },
    { kind: "material", params: ["mat", "tile_mm", "finish", "aniso"] },
    { kind: "transform", params: ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"] },
    { kind: "assemble", params: [] },
    { kind: "artifact", params: ["name"] },
  ];
  /* ═══ CF-FORGE3D-NODES-END ═══ */

  /* LES TRAITEMENTS — miroir de `_PROC_KINDS` (forge3d.py:907) : ce qui peut
     s'intercaler entre une couche et l'assemblage, et donc ce qui merite un
     rang. La 2a l'ecrivait deja en dur dans `graphRows` (plane|relief) ; la 2b
     y ajoute le moteur. Ce n'est PAS une grille de prix ni un roster de
     moteurs (ceux-la viennent de /info) : c'est le vocabulaire du graphe. */
  const PROC_KINDS = ["plane", "relief", "mesh3d"];
  const PROC_LABELS = { plane: "plan", relief: "relief", mesh3d: "mesh 3D (moteur)" };
  /* borne ANTI-GEL de la descente de chaine — miroir de `_CHAIN_MAX` */
  const CHAIN_MAX = 4;
  /* le pas de tuilage que `clean_graph` posera si le noeud matiere n'en porte
     pas (forge3d.py:404). /info sert les BORNES (material_limits.tile_mm), pas
     ce defaut — d'ou cette copie, nommee, plutot qu'un champ vide qui ferait
     croire que rien ne sera construit. */
  const TILE_DEFAUT = 63;
  const POLL_MS = 1200;         /* periode du poll d'un job (plan 2b) */

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
  let LAST_MANIFEST = null;     /* le manifeste RECTO de la carte courante —
                                    reçu d'un POST layers de cette session, OU
                                    relu du disque au boot (refreshManifest,
                                    I2) ; seed du graphe, bouton seed/re-seed
                                    n'existe que s'il est posé */
  let MANIFEST_CARD = null;     /* l'étiquette de carte (c01, c02…) POUR
                                    LAQUELLE `LAST_MANIFEST` a été chargé —
                                    legs 5 : c'est elle qu'on confronte à la
                                    carte courante à chaque peinture */
  let ARTIFACT = null;          /* le dernier bordereau de build3d */
  let PREVIEW_URL = null;       /* objectURL du GLB monté dans model-viewer —
                                    révoquée avant d'en poser une nouvelle */
  const HIST = [];              /* pile d'annulation des éditions du graphe —
                                    patron mod-gltf.js:HIST, 40 entrées max */
  /* ── L'ÉTAT DES JOBS mesh3d, par nœud — LU, jamais inventé ──────────────
     JOBS[nid] : le DERNIER job.json reçu (objet), ou `null` quand le backend
     a répondu 404 (« jamais lancé » — une réponse, pas une panne). La clé
     ABSENTE veut dire « pas encore sondé » : c'est ce qui déclenche le
     sondage d'une seule requête au premier rendu (un GET, gratuit).
     POLLS[nid] : la GÉNÉRATION du poll en cours (pas un booléen) — un poll
     par nœud, et un tic rassis ne retire que SA PROPRE entrée, jamais celle
     de son successeur (même doctrine que `_MESH3D_RUNNING.get(cle) is moi`
     côté serveur).
     SEEN[nid]  : l'instant du dernier état LU — c'est lui qui autorise une
     re-sonde d'un job terminal (sans quoi « relancé ailleurs » ne pourrait
     jamais se déclencher : une fois le poll arrêté, plus personne ne
     regarde).
     RUNS[nid]  : vrai dès qu'un poll a vu le `run_id` CHANGER — un autre
     onglet a relancé ce nœud, et l'écran le dit au lieu d'un flip muet.
     ERRS[nid]  : le refus HTTP LITTÉRAL du dernier lancement/poll (la
     famille nommée 400/409/503/413), effacé au premier succès. */
  const JOBS = {};
  const POLLS = {};
  const SEEN = {};
  const RUNS = {};
  const ERRS = {};
  const REPROBE_MS = 30000;     /* au-delà, l'état terminal d'un nœud est
                                    RELU une fois par peinture — c'est ce qui
                                    laisse voir la relance d'un autre onglet */
  let GEN = 1;                  /* génération : un poll d'un deck (ou d'une
                                    carte) précédent se tait au lieu d'écrire
                                    dans l'écran du suivant. Commence à 1 :
                                    zéro serait un jeton FAUX dans POLLS. */

  /* OUBLIER LES JOBS — appelé quand ce qu'ils décrivent n'est plus à l'écran
     (changement de deck, changement de carte). `GEN` d'abord : les tics déjà
     en vol se taisent, et les nouvelles sondes repartent sous un jeton neuf
     que ces tics-là ne peuvent plus retirer. */
  function oublieLesJobs() {
    GEN += 1;
    [JOBS, POLLS, SEEN, RUNS, ERRS].forEach((reg) => {
      Object.keys(reg).forEach((k) => { delete reg[k]; });
    });
  }

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
      + '<p class="hint">Un traitement par couche livrée : plan texturé (gratuit), '
      + 'relief extrudé (gratuit, solide fermé imprimable) ou moteur 3D (payant, '
      + 'prix annoncé avant). Chaque rang porte sa chaîne — matière et placement. '
      + 'Chaque champ édité patche aussitôt le graphe — annulable.</p>'
      + '<div id="cf-forge3d-graph"></div>'
      + '<p class="hint" id="cf-forge3d-cost"></p>'
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
    /* ASSURANCE : un changement de deck recharge la page aujourd'hui (donc
       ce module repart de zéro par construction) — mais si ça change un
       jour, un undo ou un seed cross-deck serait un bug sérieux. mod-frame
       et mod-texture s'abonnent déjà à cet événement pour la même raison. */
    CF.on("core:deck", () => {
      HIST.length = 0;
      LAST_MANIFEST = null;
      MANIFEST_CARD = null;
      ARTIFACT = null;
      /* M1 — un chargement de manifeste en vol appartient au deck PRÉCÉDENT :
         on coupe le verrou, sinon le deck suivant se croit « déjà en train de
         charger » et n'en redemande jamais. Le chargement rassis, lui, jette
         son propre résultat (il compare sa génération). */
      refreshManifest.busy = null;
      /* les jobs sont DECK-LOCAUX (nodes/<nid>/job.json sous le deck) : ceux
         du deck précédent ne disent plus rien de celui-ci. */
      oublieLesJobs();
      if (PREVIEW_URL) { URL.revokeObjectURL(PREVIEW_URL); PREVIEW_URL = null; }
    });
    /* LEGS 5, CÔTÉ POUSSÉE — sans cet abonnement la fraîcheur du manifeste
       n'était qu'un contrôle TIRÉ depuis `paintGraph`, que rien ne déclenchait :
       le rail (#prevBtn/#nextBtn) change `CUR` puis appelle `invalidate("core")`,
       qui redessine l'aperçu et émet `core:render {i}` — JAMAIS `core:deck`, le
       seul évènement auquel P9 s'abonnait. Résultat : changer de carte l'onglet
       Forge 3D ouvert ne rafraîchissait rien.
       `core:render` est L'ÉVÈNEMENT ÉTABLI pour ça (core.js:715 le dit :
       « quatre modules y accrochent leur péremption » — mod-gltf:checkStale,
       mod-type, mod-print, mod-data) ; P9 y devient le cinquième. Il est aussi
       le bon pour NOUS : un rendu PARTIEL (l'export par couches de ce module)
       ne l'émet volontairement pas, donc exporter ne déclenche pas N+1 fausses
       alertes de changement de carte.
       Le handler est GRATUIT quand rien ne bouge : `cardChanged` compare les
       étiquettes d'abord et rend `null` sans rien toucher. */
    CF.on("core:render", () => { cardChanged(); });
    refreshInfo();
    refreshManifest();
    paintUndo();
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
        /* seed du graphe par défaut (Task 5) : le RECTO fait foi, jamais le
           dernier reçu — le backend défaut side="front", l'écran affiche
           recto par défaut, et l'aperçu figé devient l'image ERC-721
           (l'identité d'une carte est sa face).

           C1 — L'APPARIEMENT SE POSE ICI AUSSI, sans quoi le legs 5 rentre
           par la porte de l'export : poser `LAST_MANIFEST` seul laissait
           `MANIFEST_CARD` sur l'ancienne carte (ou `null`), et un changement
           de carte PENDANT l'export figeait une paire fausse que le
           comparateur de `cardChanged` valide pour toujours — `seedDefault`
           semait alors depuis les couches d'une autre carte. C'est `carte`,
           l'index figé en tête de fonction, qui étiquette (pas le rail, qui
           a pu bouger). */
        if (face === "front") {
          LAST_MANIFEST = rep.layers;
          MANIFEST_CARD = cardLabel(carte);
        }
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

  /* I2 — LE MANIFESTE SE CHARGE AU BOOT : `LAST_MANIFEST` ne vivait qu'en
     mémoire de module, donc un F5 après un export réel faisait mentir le
     hint « exportez les couches d'abord » et effaçait le bouton de re-seed
     alors que les couches, elles, sont bel et bien sur le disque. On relit
     le manifeste RECTO de la carte courante (le même fichier que
     `post_layers` écrit, `layers_c{NN}_front.json`) — 404 = jamais exporté
     pour cette carte, toléré EN SILENCE (ce n'est pas une panne, le hint
     le dit déjà). `M.api.blob` rend un Blob de provenance connue ; on le
     relit en texte puis en JSON (pas de route JSON dédiée à ce fichier). */
  /* L'ÉTIQUETTE D'UNE CARTE — une seule règle de formatage pour tout le
     module (`c01`, `c02`… : celle de `post_layers`, qui nomme
     `layers_c{NN}_front.json`). L'index est un PARAMÈTRE : `exportLayers` a
     déjà figé le sien en tête de fonction et doit étiqueter CE numéro-là, pas
     celui que le rail affiche au moment où l'appariement se pose. */
  function cardLabel(carte) {
    const i = (carte == null) ? (CF.current ? CF.current() : 0) : carte;
    return "c" + String(i + 1).padStart(2, "0");
  }

  /* un seul chargement à la fois, et `busy` porte LA PROMESSE en cours (pas
     un booléen) : `wire()` en lance un ET peint dans la foulée, et cette
     peinture appelle `cardChanged()` — sans ce verrou, le boot partait en
     DOUBLE requête. Rendre la promesse permet en plus à un appelant qui va
     CONSOMMER le manifeste (le seed) d'attendre le chargement au lieu de lire
     l'ancien. */
  function refreshManifest() {
    if (!refreshManifest.busy) refreshManifest.busy = chargeManifeste();
    return refreshManifest.busy;
  }

  async function chargeManifeste() {
    const label = cardLabel();
    const gen = GEN;
    let recu = null;
    try {
      const blob = await M.api.blob("GET", "file/layers_" + label + "_front.json");
      recu = JSON.parse(await blob.text());
    } catch (e) {
      recu = null;
    }
    /* M1 — CE CHARGEMENT PEUT ÊTRE RASSIS : un changement de deck pendant la
       requête a incrémenté `GEN`. Écrire son résultat poserait un manifeste —
       et surtout un APPARIEMENT — appartenant à ce qui n'est plus à l'écran.
       Il se jette, il ne se peint pas ; et il ne TOUCHE PAS au verrou, que le
       handler `core:deck` a déjà libéré (le nuller ici tuerait celui du
       chargement suivant, déjà parti). Le chemin `cardChanged`, lui, ne peut
       pas rassir : il incrémente `GEN` AVANT de lancer sa requête. */
    if (gen !== GEN) return;
    LAST_MANIFEST = recu;
    /* l'étiquette est posée MÊME en échec : un 404 est une réponse (« jamais
       exporté pour cette carte »), pas une raison de re-demander en boucle
       à chaque peinture. */
    MANIFEST_CARD = label;
    refreshManifest.busy = null;
    paintGraph();
  }

  /* LEGS 5 — LE MANIFESTE SUIT LA CARTE, pas seulement le boot. `LAST_MANIFEST`
     ne se chargeait qu'à l'initialisation du panneau : changer de carte au rail
     laissait donc l'écran proposer (ou refuser) un graphe par défaut d'après
     les couches d'une AUTRE carte.

     LE COMPARATEUR EST LE GARDE, et il est le PREMIER geste : tant que
     l'étiquette de la carte courante est celle du manifeste chargé, cette
     fonction ne touche à RIEN — ni réseau, ni DOM, ni focus (le piège
     syncInputs/renderPanel de mod-face : un abonné qui repeint à chaque tic de
     rendu volerait le curseur de l'utilisateur des dizaines de fois par
     minute). Elle rend la promesse du rechargement quand il a lieu (ou celle
     du rechargement DÉJÀ en vol), `null` quand il n'y a rien à faire — c'est
     ce qui permet au seed de l'ATTENDRE. */
  function cardChanged() {
    if (refreshManifest.busy) return refreshManifest.busy;
    if (cardLabel() === MANIFEST_CARD) return null;
    /* I2 — UN JOB EST LIÉ À SA CARTE. Le GLB d'un nœud a été fabriqué depuis
       LA couche d'une carte précise (le job le dit lui-même : `source.file`).
       Garder les chips en changeant de carte afficherait « servi · 30 cr » sur
       un nœud qui, pour LA carte affichée, n'a rien servi du tout — et le pied
       de coût compterait ce nœud comme déjà payé. Le chip d'une autre carte
       serait un mensonge : on oublie, et on re-sonde. */
    oublieLesJobs();
    return refreshManifest();
  }

  /* LE MODÈLE D'UN RANG — la CHAÎNE d'un traitement, résolue exactement comme
     le backend la résoudra : `_resolve_graph_elements` pour la source (la
     PREMIÈRE arête layer -> traitement gagne) et `_chaine_aval` pour l'aval
     (`material` puis `transform`, 0 ou 1 de chacun, dans n'importe quel ordre,
     première arête gagnante là aussi). Les maillons surnuméraires restent dans
     le graphe — le backend les avoue au bordereau via `ignored` après
     construction ; l'écran ne les cache pas, il ne leur donne simplement pas
     de rang. Rendre `{layer, proc, mat, trs}` : c'est la seule forme que
     l'affichage ET l'édition manipulent. */
  function rowModel(graph, procId) {
    const byId = {};
    (graph.nodes || []).forEach((n) => { byId[n.id] = n; });
    const proc = byId[procId];
    if (!proc || PROC_KINDS.indexOf(proc.kind) < 0) return null;
    const edges = graph.edges || [];
    let layer = null;
    for (let i = 0; i < edges.length && !layer; i++) {
      const f = byId[edges[i].from];
      if (edges[i].to === procId && f && f.kind === "layer") layer = f;
    }
    let mat = null, trs = null, cur = procId;
    for (let k = 0; k < CHAIN_MAX; k++) {
      let nxt = null;
      for (let i = 0; i < edges.length && !nxt; i++) {
        const t = (edges[i].from === cur) ? byId[edges[i].to] : null;
        if (t && (t.kind === "material" || t.kind === "transform")) nxt = t;
      }
      if (!nxt) break;
      /* deux matières (ou deux transforms) sur une même chaîne : on s'arrête,
         comme le backend — la seconde ne peut pas gagner sans que la première
         mente. */
      if (nxt.kind === "material") { if (mat) break; mat = nxt; } else { if (trs) break; trs = nxt; }
      cur = nxt.id;
    }
    return { layer: layer, proc: proc, mat: mat, trs: trs };
  }

  /* les rangs, DANS L'ORDRE DES NŒUDS du graphe — le même ordre que celui où
     le backend listera les éléments du bordereau. Un traitement sans aucune
     couche source n'a pas de rang (le backend l'avoue en `ignored`). */
  function graphRows(graph) {
    const rows = [];
    (graph.nodes || []).forEach((n) => {
      if (PROC_KINDS.indexOf(n.kind) < 0) return;
      const r = rowModel(graph, n.id);
      if (r && r.layer) rows.push(r);
    });
    return rows;
  }

  /* ── LES PRIX : SERVIS PAR /info, JAMAIS RECOPIÉS ───────────────────────
     `engineOf` cherche un moteur dans la table servie ; `engineFor` résout
     CELUI d'un nœud comme le fera `clean_graph` (le sien s'il est connu,
     sinon le défaut du contrat). Un seul résolveur pour l'affichage, le prix
     et le lancement — sinon l'écran annonce un prix et le backend en facture
     un autre. */
  function mesh3dInfo() { return (INFO && INFO.mesh3d) || null; }

  function engineOf(id) {
    const m = mesh3dInfo();
    const tab = (m && m.engines) || [];
    return tab.filter((e) => e && e.id === id)[0] || null;
  }

  function engineFor(proc) {
    const m = mesh3dInfo();
    const tab = (m && m.engines) || [];
    if (!tab.length) return null;
    return engineOf(proc && proc.engine) || engineOf(m.default_engine) || tab[0];
  }

  function defaultEngine() {
    const m = mesh3dInfo();
    return (m && m.default_engine) || "";
  }

  /* le surcoût ultra vient du contrat (`ultra_extra_credits`), jamais d'un id
     de moteur écrit ici : la grille partagée de meshy_service en est la seule
     vérité, et elle ne l'accorde qu'aux moteurs qui le proposent. */
  function ultraCredits(eng) {
    return (eng && Number(eng.ultra_extra_credits)) || 0;
  }

  function engPrice(eng, ultra) {
    if (!eng) return null;
    if (eng.provider !== "meshy") return { usd: Number(eng.price_usd) || 0, credits: 0 };
    const base = Number(eng.credits) || 0;
    const cr = base + (ultra ? ultraCredits(eng) : 0);
    /* le taux crédit -> $ n'est pas une constante d'ici : il se DÉDUIT du
       couple servi (`price_usd` vaut exactement `credits x taux`, cf.
       forge3d.py:_engine_table). Zéro crédit annoncé = zéro équivalent. */
    const taux = base > 0 ? (Number(eng.price_usd) || 0) / base : 0;
    return { usd: Math.round(cr * taux * 10000) / 10000, credits: cr };
  }

  function usdTxt(v) {
    return (Number(v) || 0).toFixed(2).replace(".", ",") + " $";
  }

  /* le prix d'UN nœud, dans les mots de son fournisseur */
  function priceTxt(eng, ultra) {
    const p = engPrice(eng, ultra);
    if (!p) return "prix inconnu";
    return (eng.provider === "meshy")
      ? (p.credits + " cr (~" + usdTxt(p.usd) + ")")
      : usdTxt(p.usd);
  }

  /* un champ numérique borné PAR /info — jamais des bornes écrites ici */
  function numHtml(label, field, value, bornes, step, unite, off) {
    /* les bornes viennent de /info : ABSENTES, on n'en invente pas (un
       min=0/max=0 de repli verrouillerait le champ en prétendant que c'est
       la règle du domaine). */
    const b = (bornes && bornes.length === 2
      && isFinite(bornes[0]) && isFinite(bornes[1])) ? bornes : null;
    return '<label class="cf-forge3d-num">' + esc(label)
      + '<input type="number" data-field="' + esc(field) + '" value="'
      + esc(value != null ? value : "") + '"'
      + (b ? ' min="' + Number(b[0]) + '" max="' + Number(b[1]) + '"' : "")
      + ' step="' + esc(step) + '"' + (off ? " disabled" : "")
      + '>' + (unite ? "<i>" + esc(unite) + "</i>" : "") + '</label>';
  }

  function rowHtml(r, lim) {
    const proc = r.proc, layer = r.layer;
    const isRelief = proc.kind === "relief";
    const isMesh = proc.kind === "mesh3d";
    const pd = (lim && lim.plane_depth_mm) || [0, 0];
    const rdMax = lim ? lim.relief_depth_mm_max : 0;
    const rb = (lim && lim.relief_base_mm) || [0, 0];
    const rg = (lim && lim.relief_grid) || [0, 0];
    const depthMin = isRelief ? 0 : pd[0];
    const depthMax = isRelief ? rdMax : pd[1];
    /* un moteur ne s'extrude pas : sa géométrie vient du GLB livré, pas d'une
       profondeur d'ici — les champs du relief n'ont donc rien à dire sur ce
       rang (ils restent sur le nœud, `clean_graph` ne garde que ceux du kind
       retenu : revenir en arrière ne perd rien). */
    const geoHtml = isMesh ? ""
      : (numHtml("profondeur", "depth_mm", proc.depth_mm, [depthMin, depthMax],
                 "0.05", "mm")
        + (isRelief
          ? (numHtml("base", "base_mm", proc.base_mm, rb, "0.05", "mm")
            + numHtml("grille", "grid", proc.grid, rg, "1", ""))
          : ""));
    return '<div class="cf-forge3d-row" data-proc="' + esc(proc.id) + '">'
      + '<div class="cf-forge3d-line">'
      + '<span class="mono cf-forge3d-role">' + esc(layer.role || "composite") + '</span>'
      + '<select class="cf-forge3d-kind" data-field="kind">'
      + PROC_KINDS.map((k) => '<option value="' + esc(k) + '"'
        + (proc.kind === k ? " selected" : "") + '>' + esc(PROC_LABELS[k])
        + '</option>').join("")
      + '</select>'
      + geoHtml
      + '<select class="cf-forge3d-side" data-field="side">'
      + '<option value="front"' + (layer.side === "back" ? "" : " selected") + '>recto</option>'
      + '<option value="back"' + (layer.side === "back" ? " selected" : "") + '>verso</option>'
      + '</select>'
      + '</div>'
      + (isMesh ? mesh3dHtml(proc) : "")
      + matHtml(r, isMesh)
      + trsHtml(r)
      + '</div>';
  }

  /* ── LE BLOC MOTEUR — la SEULE dépense de cet écran ─────────────────────
     Tout y vient de `INFO.mesh3d` : le roster, les libellés, les prix, le
     surcoût ultra, la longueur du prompt, la présence de la clé. Rien n'y est
     écrit en dur. Et quand la table est VIDE, on affiche la panne TELLE
     QUELLE — jamais un <select> vide muet, qui se relit « aucun moteur
     n'existe » alors qu'il veut dire « la grille de prix est tombée ». */
  function mesh3dHtml(proc) {
    const m = mesh3dInfo();
    const engines = (m && m.engines) || [];
    if (!engines.length) {
      /* M2 — LA ZONE D'ÉTAT SURVIT À LA PANNE. La table des moteurs est
         tombée, mais un job PAYÉ, lui, ne disparaît pas avec elle : faire
         s'évaporer sa chip effacerait la seule trace à l'écran de ce qui a été
         dépensé. `runHtml` sait déjà se désactiver sans moteur — il rend un
         bouton mort et l'état lu du disque. */
      return '<div class="cf-forge3d-blk cf-forge3d-mesh"><p class="hint">'
        + '<b>moteurs 3D indisponibles</b> — ' + esc((m && m.degraded)
          || "le contrat /info n'a pas été chargé (backend injoignable ?)")
        + '</p><span class="cf-forge3d-run" data-nid="' + esc(proc.id) + '">'
        + runHtml(proc) + '</span></div>';
    }
    const eng = engineFor(proc);
    const cle = !m.has_meshy;
    const opts = engines.map((e) => '<option value="' + esc(e.id) + '"'
      + (e.id === eng.id ? " selected" : "") + '>' + esc(e.label) + " · "
      + esc(priceTxt(e, false))
      + esc(e.provider === "meshy" && cle ? " — clé requise (Réglages)" : "")
      + '</option>').join("");
    const ultraCr = ultraCredits(eng);
    const promptMax = Number((m && m.prompt_max) || 0);
    return '<div class="cf-forge3d-blk cf-forge3d-mesh">'
      + '<label class="cf-forge3d-sel">moteur<select data-field="engine">'
      + opts + '</select></label>'
      + '<span class="cf-forge3d-price mono">' + esc(priceTxt(eng, proc.ultra))
      + '</span>'
      + (ultraCr > 0
        ? ('<label class="cf-forge3d-chk"><input type="checkbox" data-field="ultra"'
          + (proc.ultra ? " checked" : "") + '> ultra <i>+' + Number(ultraCr)
          + ' cr</i></label>')
        : "")
      + '<label class="cf-forge3d-txt">texture<input type="text" '
      + 'data-field="texture_prompt"'
      + (promptMax > 0 ? ' maxlength="' + promptMax + '"' : "")
      + ' value="' + esc(proc.texture_prompt || "") + '" '
      + 'placeholder="ce que le moteur doit peindre"></label>'
      + '<span class="cf-forge3d-run" data-nid="' + esc(proc.id) + '">'
      + runHtml(proc) + '</span>'
      + (m.meshy_mock
        ? '<p class="hint">simulateur Meshy local actif — aucun crédit réel '
          + 'n\'est débité.</p>'
        : "")
      + '</div>';
  }

  /* le bouton et la chip d'un nœud, peints DEPUIS le job (jamais l'intention
     envoyée). `runHtml` est le seul endroit qui décide de désactiver Lancer :
     un job en cours (le backend refuserait en 409) et une clé Meshy absente
     (il refuserait en 503) — l'écran le DIT avant de faire perdre un aller-
     retour à l'utilisateur. */
  function runHtml(proc) {
    const m = mesh3dInfo();
    const eng = engineFor(proc);
    const meshy = !!(eng && eng.provider === "meshy");
    const sansCle = meshy && !(m && m.has_meshy);
    const connu = Object.prototype.hasOwnProperty.call(JOBS, proc.id);
    const job = connu ? JOBS[proc.id] : undefined;
    const court = !!(job && (job.status === "queued" || job.status === "running"));
    return '<button class="btn primary sm" type="button" data-act="launch" '
      + 'data-nid="' + esc(proc.id) + '"'
      + ((court || sansCle || !eng) ? " disabled" : "") + '>'
      + (job ? "relancer" : "lancer") + '</button>'
      + (sansCle
        ? '<span class="cf-forge3d-chip echec">clé Meshy absente — Réglages</span>'
        : "")
      + chipHtml(proc.id, job);
  }

  /* I2 — CE QU'UN JOB A SERVI, dit par le job lui-même. `source` porte la
     couche ET le fichier de carte depuis lesquels ce GLB a été fabriqué : une
     chip muette là-dessus laisse croire qu'un « servi » vaut pour la carte
     affichée, alors qu'un GLB est lié à SA carte (le backend refuse d'ailleurs
     la fusion quand les deux ne coïncident plus). */
  function sourceTxt(job) {
    const s = (job && job.source) || null;
    if (!s) return "";
    return (s.role || "composite") + " · "
      + ((s.side === "back") ? "verso" : "recto")
      + (s.file ? " · " + s.file : "");
  }

  function chipHtml(nid, job) {
    const src = sourceTxt(job);
    const dit = src ? (' title="servi depuis ' + esc(src) + '"') : "";
    let html = "";
    if (RUNS[nid]) {
      html += '<span class="cf-forge3d-chip ailleurs">relancé ailleurs — un '
        + 'autre onglet a repris ce nœud</span>';
    }
    if (ERRS[nid]) {
      /* le refus du backend TEL QUEL : la famille nommée 400 (nœud/couche/clé
         fal), 409 (job déjà en cours, couches absentes), 503 (clé Meshy),
         413 (couche trop lourde). Le paraphraser le diluerait. */
      return html + '<span class="cf-forge3d-chip echec">' + esc(ERRS[nid])
        + '</span>';
    }
    if (job === undefined) return html;              /* pas encore sondé */
    if (job === null) {
      return html + '<span class="cf-forge3d-chip">jamais lancé</span>';
    }
    /* la provenance suit TOUTES les chips d'un job : ce qu'il a servi, ce
       qu'il sert, ce sur quoi il a échoué — jamais un état muet sur SA
       couche. Le texte court reste lisible, le fichier complet est en
       infobulle. */
    const quoi = src
      ? ('<i class="cf-forge3d-src"> · ' + esc((job.source.role || "composite")
        + " " + ((job.source.side === "back") ? "verso" : "recto")) + '</i>')
      : "";
    /* ÉCHAPPER À LA FRONTIÈRE, UNE FOIS. `step`, `error` et `closed_note` sont
       les SEULES valeurs de cette fonction écrites par le backend (tout le
       reste est un littéral d'ici ou passe par Number()). On les convertit en
       texte SÛR dès leur lecture, et plus bas on ne manipule que du sûr : un
       `esc()` par champ, à un endroit, plutôt qu'un `esc()` à retrouver dans
       chaque branche — c'est aussi ce qui rend la garantie vérifiable d'un
       coup d'œil (et épinglable par un test de source). */
    const pas = esc(job.step || "");
    const echec = esc(job.error || "sans motif rendu par le backend");
    const note = esc(job.closed_note || "");
    const st = job.status;
    if (st === "queued") {
      return html + '<span class="cf-forge3d-chip file"' + dit + '>en file'
        + quoi + '</span>';
    }
    if (st === "running") {
      return html + '<span class="cf-forge3d-chip cours"' + dit + '>en cours '
        + Number(job.progress || 0) + ' %' + (pas ? " · " + pas : "")
        + quoi + '</span>';
    }
    if (st === "served") {
      const cr = (job.consumed_credits != null)
        ? " · " + Number(job.consumed_credits) + " cr" : "";
      return html + '<span class="cf-forge3d-chip servi"' + dit + '>servi'
        + cr + quoi + '</span>'
        + (note ? '<span class="cf-forge3d-chip note">' + note + '</span>' : "");
    }
    if (st === "failed") {
      return html + '<span class="cf-forge3d-chip echec"' + dit + '>échec : '
        + echec + quoi + '</span>';
    }
    return html + '<span class="cf-forge3d-chip"' + dit + '>' + esc(st)
      + quoi + '</span>';
  }

  /* ── MATIÈRE ET FINITION — bornes et roster servis par /info ────────────
     Même règle que `clean_graph` : une matière sans matière NI finition n'est
     rien. `tuile` et `anisotropie` ne deviennent donc éditables qu'une fois
     l'une des deux posée — sans quoi le nœud naîtrait vide, serait jeté, et
     la case cochée mentirait sur un graphe qui ne la porte pas. */
  function finishLabel(f) {
    /* la seule finition qui ne soit pas holographique est l'absence de
       finition — le libellé se DÉRIVE de la liste servie, il ne la recopie
       pas (une recette de plus côté serveur s'affichera toute seule). */
    return (f === "aucune") ? "aucune" : (f + " holographique");
  }

  function matHtml(r, isMesh) {
    const mats = (INFO && INFO.materials) || [];
    const lim = (INFO && INFO.material_limits) || null;
    const panne = INFO ? INFO.materials_degraded : null;
    const mat = r.mat;
    const finitions = (lim && lim.finishes) || [];
    const pose = !!mat;
    const matSel = mats.length
      ? ('<label class="cf-forge3d-sel">matière<select data-field="mat">'
        + '<option value=""' + (mat && mat.mat ? "" : " selected") + '>aucune</option>'
        + mats.map((x) => '<option value="' + esc(x.id) + '"'
          + (mat && mat.mat === x.id ? " selected" : "") + '>' + esc(x.name)
          + '</option>').join("")
        + '</select></label>')
      /* jamais un select vide muet : la panne (ou la boutique vide) est dite */
      : ('<span class="hint"><b>aucune matière</b> — ' + esc(panne
        || (INFO ? "la boutique de matières est vide (aucune matière installée)."
                 : "contrat /info non chargé.")) + '</span>');
    const finSel = finitions.length
      ? ('<label class="cf-forge3d-sel">finition<select data-field="finish">'
        + finitions.map((f) => '<option value="' + esc(f) + '"'
          + (((mat && mat.finish) || "aucune") === f ? " selected" : "") + '>'
          + esc(finishLabel(f)) + '</option>').join("")
        + '</select></label>')
      : '<span class="hint">finitions inconnues (contrat /info non chargé).</span>';
    return '<details class="cf-forge3d-blk"><summary>matière'
      + (mat ? ' <b class="cf-forge3d-on">·</b>' : "") + '</summary>'
      + '<div class="cf-forge3d-line">' + matSel + finSel
      + numHtml("tuile", "tile_mm",
                (mat && mat.tile_mm != null) ? mat.tile_mm : TILE_DEFAUT,
                lim && lim.tile_mm, "1", "mm", !pose)
      + '<label class="cf-forge3d-chk"><input type="checkbox" data-field="aniso"'
      + (mat && mat.aniso ? " checked" : "") + (pose ? "" : " disabled")
      + '> anisotropie</label></div>'
      + '<p class="hint">matière sur plan/relief seulement — un GLB moteur '
      + 'garde la sienne.' + (isMesh && mat
        ? ' Ce rang est un moteur : la matière chaînée sera avouée comme '
          + 'ignorée au bordereau.' : "")
      + (pose ? "" : ' Tuile et anisotropie s\'activent dès qu\'une matière ou '
        + 'une finition est posée.') + '</p>'
      + '</details>';
  }

  /* LE z EFFECTIF D'UN ÉLÉMENT SANS NŒUD `transform` — c'est-à-dire ce que le
     writer posera de toute façon : pour un PLAN, sa profondeur d'empilement
     (`_node_trs` traduit `z_mm` en translation) ; pour un relief ou un GLB de
     moteur, zéro. UNE seule règle, lue par le SEMIS du nœud (`editTrs`) ET par
     son AFFICHAGE (`trsHtml`) : les laisser diverger, c'est exactement la faute
     que cette fonction existe pour tuer. */
  function zEmpilement(proc) {
    const d = Number(proc && proc.depth_mm);
    return (proc && proc.kind === "plane" && isFinite(d)) ? d : 0;
  }

  function trsHtml(r) {
    const lim = (INFO && INFO.transform_limits) || null;
    const t = r.trs;
    if (!lim) {
      return '<details class="cf-forge3d-blk"><summary>placement</summary>'
        + '<p class="hint">bornes inconnues (contrat /info non chargé).</p>'
        + '</details>';
    }
    /* M1 — CE QUI SERA CONSTRUIT, JAMAIS UN CHAMP VIDE. Même sans nœud
       `transform`, le writer POSE un placement : identité en x/y/rotation,
       échelle 1, et en z l'empilement du traitement. Un champ blanc se relit
       « rien de défini » là où quelque chose l'est très précisément — et c'est
       ce z-là qu'un semis à zéro écrasait. Les défauts que /info ne sert pas
       sont ceux de `clean_graph` (forge3d.py:410-414). */
    const d = t || { x_mm: 0, y_mm: 0, z_mm: zEmpilement(r.proc),
                     rot_deg: 0, scale: 1 };
    return '<details class="cf-forge3d-blk"><summary>placement'
      + (t ? ' <b class="cf-forge3d-on">·</b>' : "") + '</summary>'
      + '<div class="cf-forge3d-line">'
      + numHtml("x", "x_mm", d.x_mm, lim.xy_mm, "0.5", "mm")
      + numHtml("y", "y_mm", d.y_mm, lim.xy_mm, "0.5", "mm")
      + numHtml("z", "z_mm", d.z_mm, lim.z_mm, "0.1", "mm")
      + numHtml("rotation", "rot_deg", d.rot_deg, lim.rot_deg, "1", "°")
      + numHtml("échelle", "scale", d.scale, lim.scale, "0.05", "")
      + '</div>'
      + '<p class="hint">un placement absent laisse l\'élément là où son '
      + 'traitement le pose — les valeurs ci-dessus sont celles qui seront '
      + 'construites.</p>'
      + '</details>';
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
    /* legs 5, second filet : l'abonnement `core:render` de `wire()` est ce qui
       DÉCLENCHE la fraîcheur ; ce contrôle-ci rattrape les peintures qui
       n'ont pas de rendu de carte derrière elles (arrivée sur l'onglet,
       réponse tardive de /info). Il est gratuit quand rien n'a bougé. */
    cardChanged();
    const graph = get("graph");
    if (!graph) {
      host.innerHTML = LAST_MANIFEST
        ? ('<p class="hint">Aucun graphe construit pour le moment.</p>'
          + seedButtonHtml("cf-forge3d-graph-seed", "construire le graphe par défaut"))
        : '<p class="hint">Exportez les couches d\'abord (section ci-dessus) '
          + 'pour proposer un graphe par défaut.</p>';
      paintCost();
      return;
    }
    const rows = graphRows(graph);
    const lim = (INFO && INFO.graph_limits) || null;
    const body = rows.length
      ? rows.map((r) => rowHtml(r, lim)).join("")
      : '<p class="hint">Graphe sans traitement — aucune couche reliée à un '
        + 'plan, un relief ou un moteur.</p>';
    /* le re-seed reste OFFERT même une fois le graphe construit : abîmer son
       graphe n'est plus une impasse — et comme il passe par setGraph, il
       reste lui-même annulable. */
    const reseed = LAST_MANIFEST
      ? seedButtonHtml("cf-forge3d-reseed", "reconstruire le graphe par défaut")
      : "";
    /* M5 — LE PLAFOND D'ÉLÉMENTS EST DIT, PAS DÉCOUVERT AU REFUS. `build3d`
       rend un 400 nommé au-delà de `max_elements` ; ce chiffre est SERVI par
       /info (jamais recopié ici), et l'écran le rappelle dès que le graphe
       courant le dépasse — sinon l'utilisateur monte un graphe entier avant
       d'apprendre qu'il ne se construira pas. */
    const maxEl = Number(lim && lim.max_elements) || 0;
    const trop = (maxEl > 0 && rows.length > maxEl)
      ? ('<p class="hint cf-forge3d-trop"><b>' + rows.length + ' éléments</b> — '
        + 'le maximum construisible est ' + maxEl
        + ' : retire des rangs, la construction refuserait.</p>')
      : "";
    host.innerHTML = body + trop + reseed;
    /* l'état des nœuds moteur vient du DISQUE, pas de la mémoire de l'onglet :
       un nœud jamais sondé l'est UNE fois (un GET, gratuit), sans quoi un job
       servi d'une session précédente resterait invisible et serait recompté
       comme payant par le pied de coût. */
    rows.forEach((r) => {
      if (r.proc.kind === "mesh3d") pollMesh3d(r.proc.id, true);
    });
    paintCost();
  }

  /* ── LE PIED DE COÛT — CE QUE « LANCER » COÛTERA, AVANT ────────────────
     Somme des nœuds moteur NON SERVIS (un job déjà livré est payé : le
     relancer coûterait, mais tant qu'on ne le relance pas il ne doit pas
     gonfler le devis). fal en $, Meshy en crédits + équivalent $ déduit du
     contrat. Un nœud dont le prix est INCONNU (table des moteurs tombée) est
     compté comme payant et NOMMÉ — dire « 100 % gratuit » là serait le seul
     mensonge que ce pied de page puisse commettre. */
  function sacoche() { return { usdFal: 0, credits: 0, usdMeshy: 0, inconnus: 0, n: 0 }; }

  function montantTxt(s, appendice) {
    const bouts = [];
    if (s.usdFal > 0) bouts.push(usdTxt(s.usdFal));
    if (s.credits > 0) bouts.push(s.credits + " cr Meshy (~" + usdTxt(s.usdMeshy) + ")");
    if (s.inconnus > 0) {
      /* N7 — LA MÊME LACUNE, DEUX POSITIONS GRAMMATICALES. En tête on ÉNUMÈRE
         (« Coût à lancer : 0,30 $ + 2 nœud(s) au prix inconnu ») ; en appendice
         on complète un verbe (« relancer coûterait … »), où cette énumération
         ne se dit pas. Un aveu qu'on ne peut pas lire n'avoue rien. */
      bouts.push(appendice
        ? ("un montant inconnu pour " + s.inconnus + " nœud(s) (table des "
          + "moteurs indisponible)")
        : (s.inconnus + " nœud(s) au prix inconnu (table des moteurs "
          + "indisponible)"));
    }
    return bouts.join(" + ");
  }

  function costLine() {
    const graph = get("graph");
    if (!graph) return null;   /* pas de graphe, pas de devis à annoncer */
    const alancer = sacoche(), servis = sacoche();
    graphRows(graph).forEach((r) => {
      if (r.proc.kind !== "mesh3d") return;
      const job = Object.prototype.hasOwnProperty.call(JOBS, r.proc.id)
        ? JOBS[r.proc.id] : undefined;
      const s = (job && job.status === "served") ? servis : alancer;
      s.n += 1;
      const eng = engineFor(r.proc);
      const p = engPrice(eng, r.proc.ultra);
      if (!p) { s.inconnus += 1; return; }
      if (eng.provider === "meshy") { s.credits += p.credits; s.usdMeshy += p.usd; } else s.usdFal += p.usd;
    });
    const tete = montantTxt(alancer, false);
    const differe = montantTxt(servis, true);   /* complète « coûterait … » */
    /* I4 — LE COÛT DIFFÉRÉ SE DIT AUSSI. Un nœud déjà servi ne gonfle pas le
       devis (il est payé), mais son bouton « relancer » est là, actif, et
       recliquer dessus REDÉPENSE. Taire ce chiffre laissait un écran affirmer
       « 100 % gratuit » à côté d'un bouton payant : le seul mensonge que ce
       pied de page puisse commettre. */
    if (tete) {
      return { txt: "Coût à lancer : " + tete + (differe
        ? (" · " + servis.n + " nœud(s) déjà servi(s) — relancer coûterait "
          + differe) : ""), payant: true };
    }
    if (differe) {
      return { txt: "Graphe construit — relancer " + servis.n + " nœud(s) "
        + "moteur coûterait " + differe + ".", payant: true };
    }
    return { txt: "Graphe 100 % gratuit.", payant: false };
  }

  function paintCost() {
    const el = $("#cf-forge3d-cost");
    if (!el) return;
    const c = costLine();
    el.textContent = c ? c.txt : "";
    /* M4 — l'ambre est le rôle « ce que l'action va COÛTER » (cardforge.css :
       un rôle par emploi de l'accent) : un graphe gratuit n'y a pas droit. */
    el.classList.toggle("cf-forge3d-payant", !!(c && c.payant));
  }

  /* le rang d'un nœud dans le DOM, retrouvé par comparaison d'attribut et non
     par sélecteur construit : un id de nœud est une donnée, jamais un
     fragment de sélecteur (un point y suffirait à tout casser). */
  function findByAttr(cls, attr, val) {
    const host = $("#cf-forge3d-graph");
    if (!host) return null;
    const tab = Array.prototype.slice.call(host.querySelectorAll(cls));
    for (let i = 0; i < tab.length; i++) {
      if (tab[i].getAttribute(attr) === val) return tab[i];
    }
    return null;
  }

  /* REPEINDRE UN SEUL RANG (et rien d'autre) : le moteur et l'ultra changent
     ce que le rang AFFICHE au-delà de la valeur saisie (prix, case ultra,
     bouton). Repeindre la liste entière y référerait les tiroirs ouverts des
     AUTRES rangs et volerait le focus — le piège syncInputs/renderPanel de
     mod-face. On préserve donc les deux choses que le DOM porte et que le
     graphe ne dit pas : les blocs dépliés et l'élément focalisé. */
  function paintRow(procId, focusField) {
    const graph = get("graph");
    const old = findByAttr(".cf-forge3d-row", "data-proc", procId);
    const r = graph ? rowModel(graph, procId) : null;
    if (!old || !r || !r.layer || !old.parentNode) { paintGraph(); return; }
    const ouverts = Array.prototype.slice.call(old.querySelectorAll("details"))
      .map((d) => !!d.open);
    const tmp = document.createElement("div");
    tmp.innerHTML = rowHtml(r, (INFO && INFO.graph_limits) || null);
    const neuf = tmp.firstChild;
    old.parentNode.replaceChild(neuf, old);
    Array.prototype.slice.call(neuf.querySelectorAll("details"))
      .forEach((d, i) => { if (ouverts[i]) d.open = true; });
    if (focusField) {
      const f = neuf.querySelector('[data-field="' + focusField + '"]');
      if (f && f.focus) f.focus();
    }
    paintCost();
  }

  /* la zone bouton+chip d'un nœud moteur, repeinte SEULE par le poll : c'est
     ce qui permet à un job de couler pendant que l'utilisateur écrit dans le
     champ texture du même rang sans jamais perdre son curseur. */
  function paintChip(nid) {
    const zone = findByAttr(".cf-forge3d-run", "data-nid", nid);
    if (!zone) return;
    const graph = get("graph");
    const proc = graph ? (graph.nodes || []).filter((n) => n.id === nid)[0] : null;
    if (!proc) return;
    zone.innerHTML = runHtml(proc);
  }

  function onGraphClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    const act = b.getAttribute("data-act");
    if (act === "seed-default") {
      e.preventDefault();
      seedDefault();
    } else if (act === "launch") {
      e.preventDefault();
      launchMesh3d(b.getAttribute("data-nid"));
    }
  }

  /* LE SEED CONSOMME LE MANIFESTE : il doit donc ATTENDRE la vérification de
     fraîcheur avant de le lire, pas seulement se fier au dernier repaint. Sans
     cette attente, la séquence « je change de carte, je clique aussitôt sur
     construire le graphe par défaut » sème depuis les couches de la carte
     PRÉCÉDENTE — exactement le défaut que le legs 5 existe pour tuer, et que
     l'abonnement à `core:render` seul ne couvre pas (le clic peut arriver
     avant que le rechargement déclenché ne soit revenu).
     La boucle est BORNÉE et son cas d'usage est précis : si un chargement pour
     l'ANCIENNE carte était déjà en vol, `cardChanged` rend cette promesse-là —
     l'attendre ne suffit pas, il faut un second tour pour la carte courante. */
  async function seedDefault() {
    for (let k = 0; k < 3 && cardLabel() !== MANIFEST_CARD; k++) await cardChanged();
    if (cardLabel() !== MANIFEST_CARD) {
      M.toast("manifeste de cette carte non chargé — réessayez", true);
      return;
    }
    if (!LAST_MANIFEST) {
      /* la carte courante n'a pas de couches livrées : le bouton lui-même
         n'aurait pas dû être là — on repeint pour dire la vérité. */
      M.toast("aucune couche exportée pour cette carte", true);
      paintGraph();
      return;
    }
    setGraph(defaultGraph(LAST_MANIFEST), "graphe par défaut");
    paintGraph();     /* structurel : la liste entière change de forme */
  }

  function onGraphChange(e) {
    const row = e.target.closest ? e.target.closest(".cf-forge3d-row") : null;
    if (!row) return;
    const field = e.target.getAttribute("data-field");
    if (!field) return;
    const val = (e.target.type === "checkbox") ? e.target.checked : e.target.value;
    editGraph(row.getAttribute("data-proc"), field, val);
  }

  /* ÉCRITURE + PILE D'ANNULATION (patron mod-gltf.js:set/undo, paintUndo
     ~ligne 1623) : chaque édition du graphe — champ par champ, ou un
     re-seed entier — pousse l'ANCIEN graphe sur `HIST` avant de patcher,
     jamais après : c'est cette valeur-là que `undoGraph` restaure.
     `setGraph` NE REPEINT JAMAIS la liste par elle-même (patron exact de
     mod-gltf.js:set — c'est TOUJOURS l'appelant qui décide) : c'est ce
     découplage qui rend le correctif I1 possible juste en dessous. */
  function setGraph(next, label) {
    HIST.push({ before: get("graph"), label: label || "graphe" });
    if (HIST.length > 40) HIST.shift();
    M.patch({ graph: next });
    paintUndo();
  }

  /* le bouton reflète la pile (patron mod-gltf.js:paintUndo) : désactivé si
     rien à annuler, sinon étiqueté par le label de la PROCHAINE annulation. */
  function paintUndo() {
    const b = $("#cf-forge3d-undo");
    if (!b) return;
    b.disabled = !HIST.length;
    b.textContent = HIST.length ? "↶ annuler " + HIST[HIST.length - 1].label : "↶ annuler";
  }

  function undoGraph() {
    const h = HIST.pop();
    if (!h) { M.toast("rien à annuler"); return; }
    M.patch({ graph: h.before });
    paintUndo();
    paintGraph();
    M.toast("annulé : " + h.label);
  }

  const MAT_FIELDS = ["mat", "finish", "tile_mm", "aniso"];
  const TRS_FIELDS = ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"];
  /* les champs qui changent l'AFFICHAGE du rang au-delà de leur propre valeur */
  const STRUCT_FIELDS = ["engine", "ultra", "mat", "finish"];

  /* clone + modifie + setGraph : `graph` est deep-freeze par le CORE dès
     qu'il est posé (schema simple, fusion superficielle) — une mutation en
     place lèverait TypeError en mode strict.

     I1 — NE PLUS TUER LE FOCUS : c'est le piège syncInputs/renderPanel de
     mod-face — un repaint de la LISTE à chaque édition détruit et recrée
     l'input focalisé, donc chaque pas de spinner (depth_mm/base_mm/grid) ou
     chaque changement de <select> (side) perd le focus et le curseur de
     saisie. Le DOM porte déjà la valeur commise par le navigateur : seul
     `kind` change la STRUCTURE du rang (base/grille apparaissent ou
     disparaissent) et exige donc, lui seul, un repaint. La 2b ajoute deux
     champs qui changent ce que le rang AFFICHE sans changer sa valeur
     (moteur, ultra : prix, case ultra, bouton) et deux qui font naître ou
     mourir un maillon (matière, finition) : ceux-là repeignent LE RANG SEUL,
     focus restauré, tiroirs conservés. */
  function editGraph(procId, field, rawValue) {
    const graph = get("graph");
    if (!graph || !procId) return;
    const next = JSON.parse(JSON.stringify(graph));
    const proc = next.nodes.filter((n) => n.id === procId)[0];
    if (!proc) return;
    /* M1b — la NAISSANCE d'un maillon est STRUCTURELLE même quand le champ
       édité, lui, ne l'est pas : le tiroir gagne sa puce, tuile/anisotropie
       s'activent, et le z semé par `editTrs` doit se voir TOUT DE SUITE (sans
       quoi l'écran afficherait 0 pendant que le graphe porte l'empilement). */
    let naissance = false;
    if (field === "kind") {
      proc.kind = (PROC_KINDS.indexOf(rawValue) >= 0) ? rawValue : "plane";
      /* les paramètres des autres traitements RESTENT sur le nœud (patron 2a :
         `clean_graph` ne garde que ceux du kind retenu, revenir en arrière ne
         perd rien). Le moteur, lui, doit exister dès le premier rendu du bloc,
         et il vient de /info — jamais d'une constante d'ici. */
      if (proc.kind === "mesh3d" && !proc.engine) proc.engine = defaultEngine();
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
    } else if (field === "engine") {
      proc.engine = String(rawValue || "");
      /* MÊME conservatisme que `clean_graph` sur l'axe qui coûte : l'ultra ne
         se reconduit jamais tout seul vers un moteur qui ne le propose pas —
         l'utilisateur n'a pas consenti à un surcoût qu'il n'a pas nommé. */
      if (ultraCredits(engineOf(proc.engine)) <= 0) delete proc.ultra;
    } else if (field === "ultra") {
      proc.ultra = !!rawValue;
    } else if (field === "texture_prompt") {
      const max = Number((mesh3dInfo() && mesh3dInfo().prompt_max) || 0);
      const t = String(rawValue == null ? "" : rawValue);
      proc.texture_prompt = max > 0 ? t.slice(0, max) : t;
    } else if (MAT_FIELDS.indexOf(field) >= 0) {
      naissance = editMat(next, procId, field, rawValue);
    } else if (TRS_FIELDS.indexOf(field) >= 0) {
      naissance = editTrs(next, procId, field, rawValue);
    }
    setGraph(next, field);
    if (field === "kind") paintGraph();
    else if (naissance || STRUCT_FIELDS.indexOf(field) >= 0) paintRow(procId, field);
    else paintCost();
  }

  /* ── LA CHAÎNE D'UN RANG, RECONSTRUITE ─────────────────────────────────
     On ne touche QU'À l'aval : les arêtes ENTRANTES du traitement (les
     sources, y compris une source surnuméraire que le backend avoue) ne nous
     appartiennent pas. L'ordre canonique est celui du contrat serveur :
     traitement -> [matière] -> [placement] -> assemblage.
     `morts` porte les maillons que l'édition vient de RETIRER : leurs arêtes
     doivent tomber avec eux, sinon le graphe local garde des arêtes pendantes
     vers un nœud absent — `clean_graph` les jetterait côté serveur, mais
     l'écran, lui, montrerait une chaîne qui n'existe plus.

     M6 — LES MAILLONS SURNUMÉRAIRES PARTENT AVEC LA RÉÉCRITURE. L'API brute
     autorise deux matières en éventail sur un même traitement ; le backend
     retient la première et AVOUE la seconde dans `ignored`. Mais dès que
     l'utilisateur édite ce rang, son geste EST l'intention : garder un
     deuxième maillon que la chaîne réécrite n'emprunte plus laisserait dans
     le graphe un nœud que `build3d` dénoncerait à chaque construction, sans
     que l'écran ne l'ait jamais montré. On le retire — le rang affiché et le
     graphe disent alors la même chose. */
  function rewireRow(g, procId, matId, trsId, morts) {
    const garde = {};
    if (matId) garde[matId] = 1;
    if (trsId) garde[trsId] = 1;
    /* LES SURNUMÉRAIRES QUITTENT LE GRAPHE — eux seuls. `morts`, lui, ne
       purge que des ARÊTES : son nœud a déjà été retiré par l'appelant, et
       il porte aussi l'id d'un maillon qui vient de NAÎTRE (le retirer ici
       effacerait la matière que l'utilisateur vient de poser). */
    const surnum = maillonsAval(g, procId).filter((id) => !garde[id]);
    if (surnum.length) {
      const off = {};
      surnum.forEach((id) => { off[id] = 1; });
      g.nodes = (g.nodes || []).filter((n) => !off[n.id]);
    }
    const purge = {};
    (morts || []).forEach((id) => { if (id) purge[id] = 1; });
    surnum.forEach((id) => { purge[id] = 1; });
    if (matId) purge[matId] = 1;
    if (trsId) purge[trsId] = 1;
    g.edges = (g.edges || []).filter((e) => !(
      e.from === procId || purge[e.from] || purge[e.to]));
    const asm = (g.nodes || []).filter((n) => n.kind === "assemble")[0];
    const suite = [procId];
    if (matId) suite.push(matId);
    if (trsId) suite.push(trsId);
    if (asm) suite.push(asm.id);
    for (let i = 0; i + 1 < suite.length; i++) {
      g.edges.push({ from: suite[i], to: suite[i + 1] });
    }
  }

  /* TOUS les maillons (matière/placement) atteignables en aval d'un
     traitement — pas seulement ceux que la chaîne retient. C'est ce qui
     permet à `rewireRow` de distinguer le maillon GARDÉ des surnuméraires.
     Balayage en largeur, borné par `CHAIN_MAX` comme la descente du backend.
     N5, LIMITE AVOUÉE : un graphe CHARGÉ À LA MAIN (l'API brute est ouverte,
     cet écran ne produit jamais cette topologie) peut partager un maillon
     entre deux rangées — le retrait suit alors l'intention de LA rangée
     éditée, et `clean_graph` comme le bordereau `ignored` avouent le reste. */
  function maillonsAval(g, procId) {
    const byId = {};
    (g.nodes || []).forEach((n) => { byId[n.id] = n; });
    const vus = {};
    let front = [procId];
    for (let k = 0; k < CHAIN_MAX && front.length; k++) {
      const suiv = [];
      (g.edges || []).forEach((e) => {
        if (front.indexOf(e.from) < 0) return;
        const t = byId[e.to];
        if (!t || (t.kind !== "material" && t.kind !== "transform")) return;
        if (vus[t.id]) return;
        vus[t.id] = 1;
        suiv.push(t.id);
      });
      front = suiv;
    }
    return Object.keys(vus);
  }

  /* un id LIBRE au charset du backend (`clean_graph` désinfecte sur
     [A-Za-z0-9._-] et tronque à 24) : le fabriquer déjà conforme évite qu'un
     nettoyage serveur ne renomme un nœud dont nos arêtes parlent encore. */
  function freeId(nodes, base) {
    const pris = {};
    (nodes || []).forEach((n) => { pris[n.id] = 1; });
    const racine = String(base).replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 20) || "n";
    if (!pris[racine]) return racine;
    for (let k = 2; k < 500; k++) {
      if (!pris[racine + k]) return racine + k;
    }
    /* M5 — inatteignable, et pour la bonne raison : ce ne sont pas les
       ÉLÉMENTS (`graph_limits.max_elements`, le plafond métier appliqué APRÈS
       résolution par build3d) qui bornent ce compteur, mais les NŒUDS, que
       `clean_graph` tronque à `_GRAPH_ITER_MAX` (200). 500 candidats ne
       peuvent donc pas être tous pris. */
    return racine + "999";
  }

  function editMat(g, procId, field, rawValue) {
    const r = rowModel(g, procId);
    if (!r) return false;
    let mat = r.mat;
    const neuf = !mat;
    if (neuf) {
      mat = { id: freeId(g.nodes, procId + "m"), kind: "material" };
      g.nodes.push(mat);
    }
    if (field === "mat") mat.mat = String(rawValue || "") || null;
    else if (field === "finish") mat.finish = String(rawValue || "aucune");
    else if (field === "aniso") mat.aniso = !!rawValue;
    else if (field === "tile_mm") {
      const v = Number(rawValue);
      if (isFinite(v)) mat.tile_mm = v; else delete mat.tile_mm;
    }
    /* MÊME règle que `clean_graph` : une matière sans matière NI finition
       n'est rien. On retire le maillon plutôt que de laisser dans le graphe un
       nœud que le serveur jetterait en silence — l'écran montrerait alors une
       chaîne que la construction ne suivrait pas. */
    const vide = !mat.mat && (!mat.finish || mat.finish === "aucune");
    if (vide) g.nodes = g.nodes.filter((n) => n.id !== mat.id);
    rewireRow(g, procId, vide ? null : mat.id, r.trs ? r.trs.id : null,
              [mat.id]);
    /* la NAISSANCE (comme la mort) d'un maillon change ce que le rang montre :
       la puce du tiroir, l'activation de tuile/anisotropie. */
    return neuf || vide;
  }

  function editTrs(g, procId, field, rawValue) {
    const r = rowModel(g, procId);
    if (!r) return false;
    let trs = r.trs;
    const neuf = !trs;
    if (neuf) {
      /* I1 — L'ÉLÉMENT NEUTRE D'UN PLAN PORTE SON z D'EMPILEMENT. Côté writer,
         `translate` REMPLACE le `z_mm` de l'élément (`_node_trs`) : il ne s'y
         ajoute pas. Semer un z à zéro n'était donc pas « neutre » du tout — ça
         APLATISSAIT le plan sur la couche du dessous (le cadre du graphe par
         défaut vit à 1,05 mm), et il suffisait d'ouvrir le tiroir Placement
         pour pousser x de 2 mm afin de perdre la parallaxe et gagner du
         z-fighting : le GLB et le STL d'accord entre eux, et tous deux en
         désaccord avec ce que l'utilisateur voyait une frappe plus tôt.
         `zEmpilement` est la MÊME règle que celle qu'affiche `trsHtml`. */
      trs = { id: freeId(g.nodes, procId + "t"), kind: "transform",
              x_mm: 0, y_mm: 0, z_mm: zEmpilement(r.proc), rot_deg: 0, scale: 1 };
      g.nodes.push(trs);
    }
    const v = Number(rawValue);
    if (isFinite(v)) trs[field] = v;
    rewireRow(g, procId, r.mat ? r.mat.id : null, trs.id);
    return neuf;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES JOBS mesh3d — LA SEULE DÉPENSE DE CET ÉCRAN
     Lancer POSTe le graphe COURANT (le backend le renettoie et n'en retient
     que le nœud visé) ; l'état, lui, ne vient jamais de ce qu'on a envoyé :
     il est POLLÉ sur `GET mesh3d/<nid>` jusqu'au terminal.
     ═══════════════════════════════════════════════════════════════════════ */
  async function launchMesh3d(nid) {
    const graph = get("graph");
    if (!nid || !graph) return;
    if (POLLS[nid]) {
      /* un clic pendant la lecture d'un état (ou pendant un job vivant) ne
         disparaît pas en silence : le backend refuserait en 409, l'écran le
         dit d'abord. */
      M.toast("état de ce nœud en cours de lecture — réessayez");
      return;
    }
    const zone = findByAttr(".cf-forge3d-run", "data-nid", nid);
    const btn = zone ? zone.querySelector("[data-act='launch']") : null;
    if (btn) btn.disabled = true;
    ERRS[nid] = null;
    RUNS[nid] = false;
    /* N1 — LA GARDE DE GÉNÉRATION SUR LE CHEMIN QUI DÉPENSE. C'est le seul
       endroit de l'écran qui engage de l'argent, et il traverse un await : si
       la carte (ou le deck) change pendant le POST, écrire le job au retour
       poserait l'état d'un job de la carte 1 dans l'écran de la carte 2 — la
       chip mentirait sur ce qui a été servi, et le pied de coût SOUS-ESTIMERAIT
       (un nœud compté « servi » alors qu'il ne l'est pas pour cette carte-ci).
       Le job, lui, existe bel et bien côté serveur : il n'est pas perdu, il
       sera relu par la sonde quand on reviendra sur SA carte. */
    const gen = GEN;
    try {
      const carte = (CF.current ? CF.current() : 0);
      const rep = await M.api.post("mesh3d/" + encodeURIComponent(nid),
                                   { graph: graph, card: carte });
      if (gen !== GEN) return;   /* cette carte n'est plus à l'écran */
      /* on ne peint QUE ce que le backend a rendu : pas de job, pas de chip
         inventée — le poll qui suit dira l'état depuis le disque. */
      JOBS[nid] = (rep && rep.job) || null;
      SEEN[nid] = Date.now();
      paintChip(nid);
      paintCost();
      pollMesh3d(nid);
    } catch (e) {
      if (gen !== GEN) return;
      ERRS[nid] = String(e && e.message || e);
      paintChip(nid);
      M.toast(ERRS[nid], true);
    }
  }

  /* M7 — LES DEUX 404 NE DISENT PAS LA MÊME CHOSE, et `M.api.get` les
     confond : le CORE lève `ApiMissing` sur le statut AVANT même de lire le
     corps, donc « aucun job sur ce noeud » (jamais lancé — une RÉPONSE) et
     « Deck introuvable » / route absente (une PANNE) arrivent avec le même
     message générique. On passe donc par `M.api.raw`, qui rend la réponse
     telle quelle, et c'est le `detail` du backend qui tranche. */
  async function fetchJob(nid) {
    const r = await M.api.raw("GET", "mesh3d/" + encodeURIComponent(nid));
    /* N2 — ET LA GARDE QUE LE CORE AVAIT, REPRISE : en sortant de `M.api.get`
       on a perdu son contrôle de type de contenu (core.js:1161). Sans lui, un
       backend absent derrière un attrape-tout SPA rend 200 + du HTML, `json()`
       échoue, `d` vaut null, et `r.ok` déclare le nœud « jamais lancé » — une
       réponse fausse et CONFIANTE, exactement ce que la distinction des deux
       404 existait pour empêcher. Un 200 qui n'est pas du JSON est une route
       absente, pas un job absent. */
    const ct = (r.headers.get("content-type") || "").toLowerCase();
    if (r.ok && ct.indexOf("json") < 0) {
      return { erreur: "route absente sur ce backend (reponse non JSON)" };
    }
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (r.ok) return { job: d || null };
    const detail = (d && (d.detail || d.error)) || (r.status + " " + r.statusText);
    if (r.status === 404 && /aucun job/i.test(String(detail))) return { job: null };
    return { erreur: String(detail) };
  }

  /* I3b — FAUT-IL RE-SONDER CE NŒUD ? Jamais vu : oui. Job vivant : non, une
     boucle le suit déjà. Job TERMINAL : oui, mais au plus une fois par
     `REPROBE_MS` — sans cela, l'état gelait au dernier poll et « relancé
     ailleurs » ne pouvait plus jamais se déclencher, alors que c'est
     précisément après la fin d'un job qu'un autre onglet le relance. */
  function aResonder(nid) {
    if (!Object.prototype.hasOwnProperty.call(JOBS, nid)) {
      /* N4 — MÊME CADENCE POUR L'ÉCHEC. Une sonde qui a échoué (transport
         coupé, route absente) ne laisse PAS de clé dans `JOBS` : sans cette
         limite, chaque peinture relançait aussitôt une requête vouée au même
         échec. `SEEN` est posé par toutes les issues du poll, y compris
         celle-là : c'est lui qui espace les reprises. */
      return !SEEN[nid] || (Date.now() - SEEN[nid]) > REPROBE_MS;
    }
    const job = JOBS[nid];
    if (job && (job.status === "queued" || job.status === "running")) return false;
    return (Date.now() - (SEEN[nid] || 0)) > REPROBE_MS;
  }

  /* UN poll par nœud (registre `POLLS`) : recliquer Lancer pendant qu'un job
     court ne peut pas empiler deux boucles. `immediat` sert au SONDAGE — une
     seule requête, qui se prolonge en boucle uniquement si le job trouvé est
     encore vivant. Le registre porte la GÉNÉRATION, pas `true` : un tic
     rassis ne retire que sa propre entrée, jamais celle de son successeur. */
  function pollMesh3d(nid, immediat) {
    if (!nid || POLLS[nid]) return;
    if (immediat && !aResonder(nid)) return;
    const gen = GEN;
    POLLS[nid] = gen;
    const relache = () => { if (POLLS[nid] === gen) delete POLLS[nid]; };
    const tick = async () => {
      if (gen !== GEN) { relache(); return; }
      let rep = null;
      try {
        rep = await fetchJob(nid);
      } catch (e) {                    /* panne de transport, pas une réponse */
        rep = { erreur: String(e && e.message || e) };
      }
      if (gen !== GEN) { relache(); return; }
      SEEN[nid] = Date.now();
      if (rep.erreur) {
        relache();
        ERRS[nid] = rep.erreur;
        paintChip(nid);
        paintCost();
        return;
      }
      const job = rep.job;
      const avant = JOBS[nid];
      /* `run_id` est OPAQUE (jamais inventé ni renvoyé par l'écran) mais
         COMPARABLE : s'il a changé entre deux lectures, ce n'est pas notre job
         qui progresse — un AUTRE onglet a relancé ce nœud. On le DIT plutôt
         que de laisser l'état basculer en silence. */
      if (avant && avant.run_id && job && job.run_id && avant.run_id !== job.run_id) {
        RUNS[nid] = true;
      }
      JOBS[nid] = job;
      ERRS[nid] = null;
      paintChip(nid);
      paintCost();
      if (!job || job.status === "served" || job.status === "failed") {
        relache();
        return;
      }
      setTimeout(tick, POLL_MS);
    };
    if (immediat) tick(); else setTimeout(tick, POLL_MS);
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
    /* N1 (même forme, enjeu moindre) : le bordereau d'une construction décrit
       LA carte pour laquelle elle a tourné — le peindre dans l'écran d'une
       autre attribuerait ses fichiers et son aperçu à la mauvaise. */
    const gen = GEN;
    try {
      const carte = (CF.current ? CF.current() : 0);
      const rep = await M.api.post("build3d", { graph: graph, card: carte });
      if (gen !== GEN) return;
      ARTIFACT = rep.artifact;
      paintArtifact(ARTIFACT);
      if (status) status.textContent = ARTIFACT.elements + " élément(s) — "
        + weight(ARTIFACT.glb.bytes) + " · " + ARTIFACT.ms.total + " ms.";
      await mountPreview(ARTIFACT.glb.name);
    } catch (e) {
      if (status) status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
      /* I3a — LE BACKEND VIENT DE CONTREDIRE NOS CHIPS. La plupart des refus
         de `build3d` parlent d'un nœud moteur (n'a pas servi, GLB disparu,
         servi pour une AUTRE couche, trop lourd) : notre état en cache est
         donc périmé, et le garder afficherait « servi » sur le nœud même que
         le serveur vient de refuser. On oublie l'état des nœuds moteur du
         graphe — bornés par le graphe lui-même — et la peinture qui suit les
         re-sonde depuis le disque. */
      graphRows(graph).forEach((r) => {
        if (r.proc.kind !== "mesh3d") return;
        delete JOBS[r.proc.id];
        delete SEEN[r.proc.id];
      });
      paintGraph();
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
    /* 2b — CE QUI A ÉTÉ ASSEMBLÉ, ÉLÉMENT PAR ÉLÉMENT : `elements` reste le
       NOMBRE (la phrase de la 2a le concatène) et le détail vit dans
       `elements_detail`. Le moteur et les crédits RÉELLEMENT consommés y sont
       ceux du job.json de chaque nœud — la comptabilité du fournisseur, pas
       le devis annoncé avant. */
    const detail = (art.elements_detail && art.elements_detail.length)
      ? ('<p class="hint">éléments assemblés :</p>'
        + '<ul class="cf-forge3d-elems">'
        + art.elements_detail.map((d) => '<li class="mono">' + esc(d.name)
          + " · " + esc(d.kind) + " · " + esc(d.node)
          + (d.engine ? " · " + esc(d.engine) : "")
          + (d.credits != null ? " · " + Number(d.credits) + " cr" : "")
          + "</li>").join("")
        + "</ul>")
      : "";
    const ignoredHtml = (art.ignored && art.ignored.length)
      ? ('<p class="hint"><b>éléments ignorés</b> — avoués, jamais tus :</p>'
        + '<ul class="cf-forge3d-ignored">'
        + art.ignored.map((i) => "<li class=\"mono\">" + esc(i.node) + " · "
          + esc(i.why) + "</li>").join("")
        + "</ul>")
      : "";
    slip.innerHTML = rows + stlHtml + previewHtml + detail + ignoredHtml;
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
