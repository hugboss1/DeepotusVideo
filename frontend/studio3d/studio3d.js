/* 3D Studio (v2.1) — écran 1 du design « DeepOtus Studio » (bloc is3d).
   Vanilla JS, même gabarit standalone que /spritelab. Le graphe ne pilote
   rien : il REND l'état émis par MeshyPipeline (frontend/meshy/meshy.client.js,
   client de référence de la spec INTEGRATION-MESHY.md). La clé Meshy reste
   côté serveur — le client parle au proxy /api/meshy/*. Le coût estimé est
   affiché AVANT chaque lancement (rail gauche + modale de confirmation). */
"use strict";
import { MeshyClient, MeshyPipeline, estimatePipeline }
  from "/meshy/meshy.client.js";

const $ = (s) => document.querySelector(s);

/* ── couleurs d'état (rampe sémantique — jamais la rampe catégorielle) ───── */
const STC = {
  PENDING: "var(--ink-soft)", IN_PROGRESS: "var(--accent)",
  SUCCEEDED: "var(--green)", FAILED: "var(--red)",
  CANCELED: "var(--red)", SKIPPED: "var(--ink-muted)",
};
/* durées observées en prod (s) — sert uniquement à l'ETA affichée. */
const REAL_S = { source: 0, preview: 118, texture: 96, remesh: 22, rig: 34, animate: 17, export: 9 };

/* ── géométrie du graphe : positions EXACTES de la maquette (892 × 354) ────
   740 × 354 à l'origine ; le nœud 07 (760 → 892) a repoussé le bord droit.
   Les trois largeurs vont ENSEMBLE : ces coordonnées, la viewBox de
   index.html et les deux `width` de studio3d.css (.graph et .graph svg).
   En désaccorder une suffit à décrocher les huit câbles d'origine. */
const NODES = [
  { id: "prompt", phase: "source", x: 0, y: 28, w: 132, h: 120, kind: "--c-text",
    kicker: "00 · prompt", ports: [[128, 56]] },
  { id: "ref", phase: "source", x: 0, y: 204, w: 132, h: 120, kind: "--c-image",
    kicker: "00 · réf.", ports: [[128, 56]] },
  { id: "preview", phase: "preview", x: 152, y: 80, w: 132, h: 196, kind: "--c-3d",
    kicker: "01 · maillage", mesh: true, ports: [[-4, 94], [128, 94]] },
  { id: "texture", phase: "texture", x: 304, y: 190, w: 132, h: 138, kind: "--c-image",
    kicker: "02 · texture", ports: [[-4, 65], [62, -4]] },
  { id: "remesh", phase: "remesh", x: 304, y: 24, w: 132, h: 138, kind: "--c-3d",
    kicker: "03 · topologie", ports: [[62, 134], [128, 65]] },
  { id: "rig", phase: "rig", x: 456, y: 24, w: 132, h: 138, kind: "--c-av",
    kicker: "04 · squelette", ports: [[-4, 65], [62, 134], [128, 65]] },
  { id: "animate", phase: "animate", x: 456, y: 190, w: 132, h: 138, kind: "--c-av",
    kicker: "05 · animation", ports: [[62, -4], [128, 65]] },
  /* le port [128, 78] est le DÉPART de k9 : chaque câble du graphe naît d'un
     centre de pastille (7 px), et 608 + 128 + 3,5 = 739,5 ≈ 740, à mi-hauteur
     94 + 78 + 3,5 = 175,5 ≈ 176. Sans lui, k9 partirait d'un bord nu. */
  { id: "export", phase: "export", x: 608, y: 94, w: 132, h: 164, kind: "--c-video",
    kicker: "06 · export", chips: true, ports: [[-4, 78], [128, 78]] },
  /* 07 · l'Établi — une PORTE, pas une phase. `door` le dit à buildGraph() et
     à paint() : aucun pipeline n'émettra jamais « etabli », donc ce nœud n'a
     ni barre, ni état, ni crédits, et son clic OUVRE au lieu d'éditer. */
  { id: "etabli", phase: "etabli", x: 760, y: 94, w: 132, h: 164, kind: "--c-3d",
    kicker: "07 · établi", door: true, ports: [[-4, 78]] },
];
/* câbles : mêmes attributs d que la maquette — géométrie ET data appariées. */
const CABLES = [
  { id: "k1", d: "M132,88 C142,88 142,178 152,178", phase: "preview", kind: "--c-3d" },
  { id: "k2", d: "M132,264 C142,264 142,178 152,178", phase: "preview", kind: "--c-3d" },
  { id: "k3", d: "M284,178 C294,178 294,259 304,259", phase: "texture", kind: "--c-image" },
  { id: "k4", d: "M370,190 C370,180 370,172 370,162", phase: "remesh", kind: "--c-3d" },
  { id: "k5", d: "M436,93 C443,93 449,93 456,93", phase: "rig", kind: "--c-av" },
  { id: "k6", d: "M522,162 C522,172 522,180 522,190", phase: "animate", kind: "--c-av" },
  { id: "k7", d: "M588,259 C598,259 598,176 608,176", phase: "export", kind: "--c-video" },
  { id: "k8", d: "M588,93 C598,93 598,176 608,176", phase: "export", kind: "--c-video" },
  /* 740 = bord droit d'export, 760 = port du 07, tous deux à mi-hauteur (176).
     `door` : ce câble ne transporte rien, il ne s'anime donc jamais. */
  { id: "k9", d: "M740,176 C750,176 750,176 760,176", phase: "etabli", kind: "--c-3d", door: true },
];
const ENGINES3D = [
  { id: "meshy", name: "Meshy", meta: "meshy-6/7 · api" },
  { id: "tripo", name: "tripo", meta: "glb fbx obj" },
  { id: "rodin", name: "rodin", meta: "glb fbx obj" },
  { id: "hunyuan", name: "hunyuan", meta: "glb obj" },
  { id: "trellis", name: "trellis", meta: "glb" },
  { id: "triposr", name: "triposr", meta: "glb" },
];
const CHIP_COLOR = { glb: "--c-3d", fbx: "--c-3d", obj: "--c-3d", usdz: "--c-av", stl: "--c-image", "3mf": "--c-image" };
const EP_LABEL = {
  source: "library · prompt",
  preview: "/v2/text-to-3d · preview", "preview:image": "/v1/image-to-3d",
  texture: "/v2/text-to-3d · refine", remesh: "/v1/remesh", rig: "/v1/rigging",
  animate: "/v1/animations", export: "/v1/convert",
  /* la porte n'appelle aucune API — entrée non lue (epOf ne sert que les
     phases), elle garde la carte totale. */
  etabli: "local · inspection",
};
const KIND_EP = {   /* journal persistant : kind backend → endpoint court */
  "text-to-3d:preview": "/v2/text-to-3d · preview",
  "text-to-3d:refine": "/v2/text-to-3d · refine",
  "image-to-3d": "/v1/image-to-3d", "multi-image-to-3d": "/v1/multi-image-to-3d",
  remesh: "/v1/remesh", rigging: "/v1/rigging", animations: "/v1/animations",
  convert: "/v1/convert", retexture: "/v1/retexture",
};

/* ── état ─────────────────────────────────────────────────────────────────── */
const S = {
  cfg: {
    name: "prophet_octopus",
    source: "text",
    prompt: "prophète pieuvre, armure de corail, pose héroïque, style créature marine cinématographique",
    imageUrl: null, imageName: null,
    aiModel: "meshy-6", modelType: "standard",
    textureResolution: "4k", withTexture: true, enablePbr: true, texturePrompt: "",
    withRemesh: true, topology: "quad", targetPolycount: 30000, poseMode: "a-pose",
    withRig: true, heightMeters: 1.75,
    animationActions: [
      { actionId: 41, name: "idle_breathe" },
      { actionId: 92, name: "walk_cycle" },
      { actionId: 118, name: "attack_slam" },
    ],
    exportFormats: ["glb", "fbx", "usdz", "obj", "stl"], fps: 24,
  },
  engine: "meshy",
  status: { enabled: false, mock: false, configured: false, host: "api.meshy.ai" },
  falOk: false,
  balance: null,
  persisted: [],
  pipeline: null, run: null,
  playing: true, pinned: null,
  libImages: null, pickedImage: null,
};

/* ── la configuration survit à l'aller-retour vers l'Établi ─────────────────
   Depuis que le nœud 07 NAVIGUE au lieu d'ouvrir un onglet (voir
   ouvrirEtabli), revenir ici recharge la page : `S.cfg` repartait aux valeurs
   d'usine à chaque aller-retour — le prompt tapé, le nom de l'asset, l'image
   choisie dans la Library, le modèle, le polycount, les animations, les
   formats d'export. C'est le geste NORMAL, pas l'exception ; la perte serait
   donc routinière, et c'est cette navigation qui l'a introduite. Elle se
   RÉPARE ici, elle ne se documente pas.

   `sessionStorage` et non `localStorage` : la portée est l'ONGLET. Elle
   couvre exactement un aller-retour et n'impose rien à une session future —
   la même portée que celle retenue par
   docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md
   (« En session uniquement »). Cette spec-là, implémentée par
   scripts/patch_bundle_keepstate.py, garde l'état des écrans REACT DU BUNDLE
   dans des variables de module (`__dzKeep`) : cela survit au démontage d'un
   composant, pas à une navigation de page — les variables de module meurent
   avec le document. /studio3d est une page autonome, servie hors du bundle :
   son cas demande un autre outil, pas une réimplémentation du sien. Les deux
   objections que cette spec oppose au disque tombent d'ailleurs ici : `S.cfg`
   est du JSON pur (le clone ci-dessous le prouve, et lèverait sinon), et rien
   n'est restauré d'une session morte puisque l'onglet emporte la clé.

   ON NE PERSISTE QUE `S.cfg`. Pas `S.run`, pas `S.pipeline`, pas `persisted`
   ni `balance` : ce sont des états VIVANTS. Ressusciter une série d'une
   session morte afficherait une progression qui ne progresse plus et des
   crédits qui ne se consomment plus — un mensonge d'interface, et le pire de
   tous puisqu'il porte sur ce qui coûte. Le boot les redemande au serveur
   (loadStatus, loadHealth, loadBalance, loadTasks), sa seule source de
   vérité. */
const CLE_CFG = "dz.studio3d.cfg";

/* Le DÉFAUT, cloné avant toute réhydratation. Clone PROFOND (et non
   `{ ...S.cfg }`) parce que `animationActions` est un tableau d'objets : une
   copie de surface partagerait la référence, et le premier geste de l'éditeur
   souillerait le défaut, qui doit rester le repli. Par JSON plutôt que par
   structuredClone : c'est le même aller-retour que la persistance, si bien
   que le jour où l'on glisserait dans `S.cfg` quelque chose de non
   sérialisable, la page lèverait ICI, au chargement, au lieu de perdre le
   champ en silence à la navigation. */
const CFG_DEFAUT = JSON.parse(JSON.stringify(S.cfg));

function memoriserCfg() {
  /* try/catch, et non un test de disponibilité : en navigation privée, sur
     quota plein ou stockage bloqué, `sessionStorage` LÈVE — son simple accès
     lève même dans certains contextes. Perdre la mémoire de la config est un
     désagrément ; empêcher le clic sur 07 d'aboutir serait un bogue. On
     avale, et on part quand même. */
  try {
    sessionStorage.setItem(CLE_CFG, JSON.stringify(S.cfg));
  } catch { /* pas de mémoire de session — la config repartira au défaut */ }
}

function rehydraterCfg() {
  let lu = null;
  try {
    lu = JSON.parse(sessionStorage.getItem(CLE_CFG) || "null");
  } catch { return; }          /* absent, illisible : on garde le défaut */
  if (!lu || typeof lu !== "object" || Array.isArray(lu)) return;
  /* FUSION sur le défaut, clé par clé, et non un remplacement en bloc : un
     champ AJOUTÉ plus tard au défaut doit survivre à un vieux JSON qui ne le
     connaît pas — sinon `S.cfg.nouveauChamp` devient undefined et tout ce qui
     le lit casse —, et une clé d'un vieux JSON que le défaut ne connaît plus
     ne doit pas ressusciter. Le défaut fait donc la LISTE des clés ; le
     stockage ne fait que fournir des valeurs. */
  for (const cle of Object.keys(CFG_DEFAUT)) {
    if (lu[cle] === undefined) continue;
    /* Le seul contrôle de FORME, et il est volontairement étroit : tableau
       contre tableau. `animationActions` et `exportFormats` sont parcourus
       sans détour (`.map`, `.join`, `.includes`) par estimate() et par
       paramsOf(), appelés dès le premier render() — une chaîne à leur place
       et la page ne peint plus du tout. Les autres champs ne risquent qu'une
       coercition inoffensive, et un `typeof` général serait FAUX : `imageUrl`
       vaut `null` par défaut et une URL est une chaîne, si bien qu'un contrôle
       de type rejetterait la valeur même qu'on cherche à retrouver. */
    if (Array.isArray(lu[cle]) !== Array.isArray(CFG_DEFAUT[cle])) continue;
    S.cfg[cle] = lu[cle];
  }
}

/* estimation : des actions sans rig ne partent jamais (le pipeline les
   saute) — l'estimé ne doit pas les compter non plus. */
const effCfg = () => ({ ...S.cfg, animationActions: S.cfg.withRig ? S.cfg.animationActions : [] });
const estimate = () => estimatePipeline(effCfg());
const fmtCr = (n) => `${Number(n).toLocaleString("fr-FR")} cr`;
const shortId = (id) => !id ? "—" : (String(id).length <= 14 ? String(id) : `${String(id).slice(0, 8)}…${String(id).slice(-4)}`);
const hhmm = (ts) => { const d = new Date(ts); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };

function phaseView(id) {
  if (S.run) {
    const p = S.run.phases.find(x => x.id === id);
    if (p) return p;
  }
  const off = (id === "texture" && !S.cfg.withTexture)
    || (id === "remesh" && !S.cfg.withRemesh)
    || (id === "rig" && !S.cfg.withRig)
    || (id === "animate" && (!S.cfg.withRig || !S.cfg.animationActions.length));
  return { id, status: off ? "SKIPPED" : "PENDING", progress: 0, taskId: null, startedAt: 0, queued: 0 };
}
function phaseCredits(id) {
  /* finishedAt requis : avant la fin d'une phase, `credits` porte le défaut
     statique de PHASES (3 cr animate, 1 cr export…) — pas la réalité de la
     config. La vérité comptable n'arrive qu'avec consumed_credits. */
  const p = S.run && S.run.phases.find(x => x.id === id);
  if (p && p.finishedAt && p.credits != null && p.status !== "FAILED") {
    if (id === "animate") {
      const n = (S.run.outputs.animations || []).length;
      return { cr: n * 3, real: true };   // une tâche = 3 cr, cumul des actions
    }
    return { cr: p.credits, real: true };
  }
  const lines = estimate().lines.filter(l => l.id === id);
  return { cr: lines.reduce((s, l) => s + l.credits, 0), real: false };
}

/* ── API ──────────────────────────────────────────────────────────────────── */
async function jget(p) { const r = await fetch(p); if (!r.ok) throw new Error(`${p} → ${r.status}`); return r.json(); }
async function loadStatus() { try { S.status = await jget("/api/meshy3d/status"); } catch { /* backend absent */ } }
async function loadHealth() { try { S.falOk = !!(await jget("/api/health")).fal_configured; } catch { S.falOk = false; } }
async function loadBalance() {
  if (!S.status.enabled) { S.balance = null; return; }
  try { S.balance = (await jget("/api/meshy/openapi/v1/balance")).balance; } catch { S.balance = null; }
}
async function loadTasks() { try { S.persisted = (await jget("/api/meshy3d/tasks")).tasks || []; } catch { S.persisted = []; } }

/* ── construction du graphe (une fois) ───────────────────────────────────── */
function buildGraph() {
  const g = $("#graph");
  const svg = $("#cables");
  for (const c of CABLES) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", c.d); p.id = `cable-${c.id}`;
    svg.appendChild(p);
    /* rien ne circule vers une porte : pas de paquet, donc pas d'élément
       animé qui resterait invisible pour toujours dans le SVG. */
    if (c.door) continue;
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("r", "3.2"); dot.id = `packet-${c.id}`; dot.style.opacity = "0";
    const mo = document.createElementNS("http://www.w3.org/2000/svg", "animateMotion");
    mo.setAttribute("dur", "0.9s"); mo.setAttribute("repeatCount", "indefinite");
    mo.setAttribute("path", c.d.replace(/^M/, "M").replace(/,/g, " ").replace(/C/g, " C "));
    dot.appendChild(mo);
    svg.appendChild(dot);
  }
  for (const n of NODES) {
    const el = document.createElement("div");
    el.className = "node"; el.id = `node-${n.id}`;
    el.style.cssText = `left:${n.x}px; top:${n.y}px; width:${n.w}px; height:${n.h}px;`;
    el.innerHTML = `
      <div class="node-kicker"><span class="kdot" style="background:var(${n.kind})"></span><span>${n.kicker}</span></div>
      <div class="node-title" id="nt-${n.id}">${n.door ? "L'Établi" : ""}</div>
      <div class="node-sub" id="ns-${n.id}">${n.door ? "parties · rig · versions" : ""}</div>
      ${n.mesh ? `<div class="node-mesh" id="nm-${n.id}">en attente</div>` : ""}
      ${n.chips ? `<div class="node-chips" id="nc-${n.id}"></div>` : ""}
      ${n.door
        ? `<div class="node-bottom"><span class="node-door">ouvrir →</span></div>`
        : `<div class="node-bottom">
            <div class="node-bar"><div id="nb-${n.id}" style="width:0%"></div></div>
            <div class="node-state">
              <span class="node-st" id="nst-${n.id}">PENDING</span>
              <span class="node-cr" id="ncr-${n.id}">—</span>
            </div>
          </div>`}
      ${n.ports.map(([px, py]) => `<span class="port" style="left:${px}px; top:${py}px; border-color:var(${n.kind})"></span>`).join("")}`;
    /* SOIT les gestionnaires génériques, SOIT la porte — jamais les deux.
       openEditor("etabli") ouvrirait un éditeur de tâche Meshy pour un nœud
       qui n'est pas une tâche, et S.pinned = "etabli" épinglerait au panneau
       droit une phase dont aucun pipeline n'émettra jamais l'état. */
    if (n.door) brancherEtabli(el);
    else {
      el.addEventListener("click", () => { S.pinned = n.id; render(); });
      el.addEventListener("dblclick", () => openEditor(n.id));
    }
    g.appendChild(el);
  }
}

/* ── rendu ────────────────────────────────────────────────────────────────── */
/* setTimeout et non requestAnimationFrame : rAF ne tire pas quand la page ne
   composite pas (onglet caché, iframe d'un onglet en arrière-plan) — l'état
   doit continuer à se peindre pendant une série même hors écran. */
let _pending = false;
function render() {
  if (_pending) return;
  _pending = true;
  setTimeout(() => { _pending = false; paint(); }, 16);
}

function nodeTitle(id) {
  const c = S.cfg;
  switch (id) {
    case "prompt": return "Prompt de scène";
    case "ref": return "Image de départ";
    case "preview": return "Maillage brut";
    case "texture": return `Texture PBR ${c.textureResolution}`;
    case "remesh": return `Remesh ${c.topology} ${Math.round(c.targetPolycount / 1000)} k`;
    case "rig": return `Auto-rig ${String(c.heightMeters).replace(".", ",")} m`;
    case "animate": return `${c.animationActions.length} action${c.animationActions.length > 1 ? "s" : ""} Meshy`;
    case "export": return "Livrables";
  }
}
function nodeSub(id) {
  const c = S.cfg;
  switch (id) {
    case "prompt": return `texte · ${c.prompt.length} car.`;
    case "ref": return c.imageName || "aucune · optionnel";
    case "preview": return c.source === "image" ? "v1 · image-to-3d" : "v2 · preview";
    case "texture": return "v2 · refine";
    case "remesh": return "/v1/remesh";
    case "rig": return "/v1/rigging";
    case "animate": return "/v1/animations";
    case "export": return "/v1/convert";
  }
}
function epOf(id) {
  if (id === "preview" && S.cfg.source === "image") return EP_LABEL["preview:image"];
  return EP_LABEL[id];
}

function activeNodeId() {
  if (S.pinned) return S.pinned;
  if (S.run) {
    const inp = S.run.phases.find(p => p.status === "IN_PROGRESS");
    if (inp) return NODES.find(n => n.phase === inp.id)?.id || "prompt";
    const started = S.run.phases.filter(p => p.startedAt).slice(-1)[0];
    if (started) return NODES.find(n => n.phase === started.id)?.id || "prompt";
  }
  return "prompt";
}

function paramsOf(nodeId, ph) {
  const c = S.cfg, run = S.run;
  const tid = (phase) => shortId(run?.phases.find(p => p.id === phase)?.taskId);
  switch (nodeId) {
    case "prompt": case "ref":
      return [["source", c.source === "image" ? "image + texte" : "texte"],
              ["prompt", `${c.prompt.length} car.`],
              ["image_url", c.imageName || "absente"],
              ["moderation", "true"]];
    case "preview":
      return c.source === "image"
        ? [["image_url", c.imageName || "—"], ["ai_model", c.aiModel],
           ["should_texture", String(c.withTexture)], ["texture_resolution", c.textureResolution],
           ["pose_mode", c.poseMode || "—"], ["target_formats", c.exportFormats.join(", ")]]
        : [["mode", "preview"], ["ai_model", c.aiModel], ["model_type", c.modelType],
           ["topology", c.topology], ["target_polycount", c.targetPolycount.toLocaleString("fr-FR")],
           ["pose_mode", c.poseMode || "—"], ["should_remesh", "false"]];
    case "texture":
      return [["mode", "refine"], ["preview_task_id", tid("preview")],
              ["texture_resolution", c.textureResolution], ["enable_pbr", String(c.enablePbr)],
              ["ai_model", c.aiModel]];
    case "remesh":
      return [["input_task_id", tid("texture") !== "—" ? tid("texture") : tid("preview")],
              ["topology", c.topology], ["target_polycount", c.targetPolycount.toLocaleString("fr-FR")],
              ["target_formats", c.exportFormats.join(", ")]];
    case "rig":
      return [["input_task_id", tid("remesh") !== "—" ? tid("remesh") : tid("texture")],
              ["height_meters", String(c.heightMeters)],
              ["faces", `≤ 300 000 (remesh ${c.withRemesh ? "on" : "off"})`]];
    case "animate":
      return [["rig_task_id", tid("rig")],
              ["action_id", c.animationActions.map(a => a.actionId).join(", ") || "—"],
              ["operation_type", "change_fps"], ["fps", String(c.fps)]];
    case "export":
      return [["input_task_id", tid("remesh") !== "—" ? tid("remesh") : tid("preview")],
              ["target_formats", c.exportFormats.join(", ")],
              ["3mf", c.exportFormats.includes("3mf") ? "1 cr · demandé" : "1 cr · opt-in"]];
  }
  return [];
}

/* L'Établi s'ouvre DANS LA FENÊTRE COURANTE — donc DANS l'iframe du hub quand
   cette page y est embarquée, et dans l'onglet quand /studio3d est ouvert en
   direct. UNE seule instruction pour les deux cas : `location.href` désigne la
   fenêtre qui exécute ce script, pas la fenêtre du dessus. Pas de
   `window.top`, qui casserait l'ouverture en direct ; pas de repli
   `window.open`, qui rouvrirait par la bande l'onglet qu'on retire ici.

   CE CHOIX RETOURNE CELUI DE LA TÂCHE 6, qui ouvrait un nouvel onglet. Motif :
   demande explicite de l'utilisateur — « je veux conserver l'atelier dans une
   vue iframe pour éviter toute confusion, et rajoute du coup un bouton pour
   revenir au graph ». /studio3d est réellement iframé (patch_bundle_studio3d.py
   greffe un sous-onglet « 🐙 3D Studio » = `iframe src="/studio3d/"` dans le
   hub Game Assets) ; l'Établi y prend maintenant la place du graphe, et son
   en-tête porte un bouton « ← 3D Studio » qui ramène ici.

   PARTIR COÛTE DEUX CHOSES, et elles ne se traitent pas pareil.

   1. LA CONFIGURATION — réparée, pas seulement dite. `S.cfg` ne vivait qu'en
      mémoire ; chaque aller-retour la remettait aux valeurs d'usine. C'est le
      geste NORMAL, donc la perte la plus fréquente des deux. memoriserCfg()
      l'écrit en session juste avant de partir, rehydraterCfg() la relit au
      boot (voir le bloc de persistance en tête de fichier).

   2. LA SÉRIE MESHY EN VOL — IRRÉDUCTIBLE. Elle vit DANS CETTE PAGE
      (runPipeline / MeshyPipeline) : partir la tue, crédits déjà consommés
      compris, et Meshy ne rembourse que les tâches ÉCHOUÉES, pas celles qu'on
      abandonne. Aucun stockage ne rattrape cela — un pipeline est une suite
      d'appels en cours, pas un état. Rien à sauver, donc rien à proposer.

   D'OÙ L'ASYMÉTRIE AVEC L'ÉTABLI, et la règle qui la porte : ON DEMANDE QUAND
   LE COÛT EST INÉVITABLE, ON REFUSE QUAND LE REMÈDE EST À UN CLIC. Ici, aucun
   geste ne sauve la série : informer et laisser choisir est tout ce qu'on peut
   faire, et refuser sec enfermerait l'utilisateur hors de l'Établi pour toute
   la durée d'une série — qui se compte en minutes. Là-bas, « écrire la
   version » et « annuler » sont deux boutons de la barre où le refus s'écrit :
   proposer « pars et perds tout » y serait offrir strictement pire.

   confirm() plutôt que toast() : un toast annonce, il ne retient pas une
   navigation. Le geste existe dans le dépôt — mesuré : 16 appels dans 7
   fichiers de source écrits à la main (atelier.js ×9, cardforge ×3,
   vectorlab ×4), le plus proche étant le retour ⌂ de vectorlab, qui confirme
   lui aussi avant de quitter un document modifié. Le modal #confirm de cette
   page n'est pas réutilisable : il est câblé une fois pour toutes sur
   runPipeline().

   Et le confirm ARRIVE bien dans l'iframe : patch_bundle_studio3d.py la greffe
   MÊME ORIGINE et SANS `sandbox` — vérifié ligne par ligne. Un navigateur qui
   l'étoufferait quand même rendrait `false`, donc `return` : la série survit,
   et l'échec penche du bon côté. */
function ouvrirEtabli() {
  const q = S.cfg.name ? `?job=${encodeURIComponent(S.cfg.name)}` : "";
  const url = `/etabli/${q}`;
  if (S.run && S.run.status === "running"
      && !confirm("Une série Meshy tourne dans cette page : aller à l'Établi "
                  + "l'interrompt, et les crédits déjà consommés ne reviennent "
                  + "pas. Ta configuration, elle, sera retrouvée au retour. "
                  + "Quitter quand même ?")) return;
  /* APRÈS le confirm : mémoriser une config qu'on ne quitte finalement pas
     serait inoffensif, mais l'ordre dit ce qu'on veut dire — on n'écrit qu'au
     moment où l'on part pour de bon. Et AVANT la navigation, évidemment : le
     `pagehide` de l'init est un filet pour les départs qui ne passent pas par
     ici (rechargement, fermeture), pas le chemin nominal. */
  memoriserCfg();
  location.href = url;
}

/* Le nœud 07 n'est pas une tâche Meshy : il ouvre l'Établi sur le job courant.
   Simple clic (et non double), parce qu'il ne s'édite pas. */
function brancherEtabli(el) {
  el.addEventListener("click", ouvrirEtabli);
  el.title = "Ouvrir l'Établi : parties, rig, versions, export moteurs";
}

function paint() {
  const est = estimate();
  const used = S.run ? S.run.consumedCredits : 0;
  const meshyOn = S.engine === "meshy";
  const running = S.run && S.run.status === "running";

  /* rail gauche */
  const engEl = $("#engines");
  engEl.innerHTML = "";
  for (const e of ENGINES3D) {
    const up = e.id === "meshy" ? S.status.enabled : S.falOk;
    const b = document.createElement("button");
    b.className = "engine" + (S.engine === e.id ? " on" : "");
    b.innerHTML = `<span class="dot ${up ? "up" : "down"}"></span>
      <span class="name">${e.name}</span><span class="meta">${e.meta}</span>`;
    b.title = e.id === "meshy"
      ? "Pipeline complet Meshy : maillage, texture, remesh, rig, animations"
      : "Moteur fal une passe (image → mesh) — vit dans Game Assets 3D";
    b.addEventListener("click", () => { S.engine = e.id; render(); });
    engEl.appendChild(b);
  }
  $("#engineNote").textContent = meshyOn
    ? (S.status.mock ? "simulateur local actif (MESHY_MOCK) · pipeline complet sans crédits"
      : S.status.configured ? "abonnement actif · text→3D, image→3D, remesh, rig, animation, retexture"
        : "clé absente — Réglages → « Meshy 6 (3D) », ou MESHY_MOCK=1 pour la démo")
    : "moteur fal · une passe image → mesh, pas de rig ni d'animation, export limité";
  $("#engineGoto").classList.toggle("hidden", meshyOn);

  $("#mEstimate").textContent = fmtCr(est.total);
  $("#mUsed").textContent = fmtCr(used);
  $("#mUsed2").textContent = fmtCr(used);
  $("#mBalance").textContent = S.balance == null ? "—" : fmtCr(S.balance);
  $("#mUsedBar").style.width = est.total ? `${Math.min(100, Math.round(used / est.total * 100))}%` : "0%";

  $("#btnPlay").textContent = S.playing ? "❙❙ Pause" : "▶ Lecture";
  const runBtn = $("#btnRun");
  runBtn.textContent = `${S.run ? "Relancer" : "Lancer"} · ${fmtCr(est.total)}`;
  runBtn.disabled = !meshyOn || !S.status.enabled || !!running;
  runBtn.title = !meshyOn ? "Sélectionne Meshy — les moteurs fal vivent dans Game Assets 3D"
    : !S.status.enabled ? "Configure MESHY_API_KEY dans Réglages (ou MESHY_MOCK=1)"
      : running ? "Série en cours…" : "Le coût estimé est détaillé avant tout lancement";

  /* header */
  $("#mModelChip").textContent = `meshy · ${S.cfg.aiModel}`;
  const prev = phaseView("preview");
  $("#mAssetMeta").textContent = `${S.cfg.name} · ${prev.status === "SUCCEEDED" ? "maillage prêt" : running ? "maillage en cours" : `${Math.round(S.cfg.targetPolycount / 1000)} k cible`}`;
  let eta = "prêt";
  if (S.run) {
    if (S.run.status === "done") eta = "série terminée";
    else if (S.run.status === "failed") eta = "échec — voir journal";
    else {
      const rem = S.run.phases.reduce((s, p) => {
        if (["SUCCEEDED", "SKIPPED"].includes(p.status)) return s;
        const w = p.id === "animate" ? REAL_S.animate * (S.cfg.animationActions.length || 1) : (REAL_S[p.id] || 0);
        return s + w * (1 - (p.progress || 0) / 100);
      }, 0);
      eta = rem < 1 ? "série terminée" : `reste ${Math.floor(rem / 60)} m ${String(Math.round(rem % 60)).padStart(2, "0")} s`;
    }
  }
  $("#mEta").textContent = eta;
  $("#hostDot").className = "dt-dot " + (S.status.enabled ? (running ? "run" : "ok") : "off");
  $("#hostLabel").textContent = S.status.host || "api.meshy.ai";

  /* nœuds */
  for (const n of NODES) {
    /* Une PORTE n'est pas une phase. phaseView("etabli") ne lève pas — elle
       rend un objet par défaut — mais ce qu'elle rend est un PENDING ÉTERNEL,
       barre à 0 % et « 0 cr » sur un nœud qui n'est pas une tâche : un état
       inventé, donc un mensonge d'interface. Son texte, lui, ne change jamais
       et se pose une fois pour toutes dans buildGraph() ; il n'y a donc rien à
       peindre ici, et `#nb-etabli` rendrait `null` si l'on essayait. */
    if (n.door) continue;
    const p = phaseView(n.phase);
    const col = STC[p.status] || STC.PENDING;
    const el = $(`#node-${n.id}`);
    el.style.borderColor = ["PENDING", "SKIPPED"].includes(p.status) ? "var(--stroke)" : col;
    el.classList.toggle("active", activeNodeId() === n.id);
    $(`#nt-${n.id}`).textContent = nodeTitle(n.id);
    $(`#ns-${n.id}`).textContent = nodeSub(n.id);
    const bar = $(`#nb-${n.id}`);
    bar.style.width = `${p.status === "SUCCEEDED" ? 100 : p.progress || 0}%`;
    bar.style.background = col;
    const st = $(`#nst-${n.id}`);
    st.textContent = p.status + (p.status === "IN_PROGRESS" ? ` ${p.progress || 0} %` : "") + (p.note ? ` · ${p.note}` : "");
    st.style.color = col;
    const { cr, real } = phaseCredits(n.phase);
    const crEl = $(`#ncr-${n.id}`);
    crEl.textContent = n.phase === "source" ? "0 cr" : fmtCr(cr);
    crEl.style.color = real || p.status === "IN_PROGRESS" ? "var(--accent)" : "var(--ink-soft)";
    if (n.mesh) {
      const m = $(`#nm-${n.id}`);
      m.textContent = p.status === "PENDING" ? "en attente"
        : p.status === "IN_PROGRESS" ? `génération ${p.progress || 0} %` : "maillage prêt";
      m.classList.toggle("working", p.status === "IN_PROGRESS" && S.playing);
    }
    if (n.chips) {
      $(`#nc-${n.id}`).innerHTML = S.cfg.exportFormats
        .map(f => `<span style="color:var(${CHIP_COLOR[f] || "--c-3d"})">${f.toUpperCase()}</span>`).join("");
    }
  }

  /* câbles : PENDING pointillé neutre · actif pointillé animé + paquet ·
     terminé trait plein atténué (codes visuels de la spec §4). */
  for (const c of CABLES) {
    const path = $(`#cable-${c.id}`);
    if (c.door) {
      /* le câble d'une porte ne transporte rien et n'attend rien : trait plein
         atténué, une fois pour toutes — et surtout jamais le pointillé « en
         attente » d'une phase qui ne démarrera pas. */
      path.style.stroke = `var(${c.kind})`;
      path.style.opacity = "0.5";
      path.style.strokeDasharray = "0";
      continue;
    }
    const p = phaseView(c.phase);
    const packet = $(`#packet-${c.id}`);
    if (p.status === "IN_PROGRESS") {
      path.style.stroke = `var(${c.kind})`;
      path.style.opacity = "1";
      path.style.strokeDasharray = "7 7";
      path.classList.add("flow");
      packet.style.opacity = "1";
      packet.style.fill = `var(${c.kind})`;
    } else if (p.status === "SUCCEEDED") {
      path.style.stroke = `var(${c.kind})`;
      path.style.opacity = "0.7";
      path.style.strokeDasharray = "0";
      path.classList.remove("flow");
      packet.style.opacity = "0";
    } else {
      path.style.stroke = "var(--stroke)";
      path.style.opacity = "0.4";
      path.style.strokeDasharray = "3 5";
      path.classList.remove("flow");
      packet.style.opacity = "0";
    }
  }

  /* journal */
  const jr = $("#journal");
  let rows = [];
  if (S.run) {
    rows = S.run.phases.filter(p => p.startedAt && p.id !== "source")
      .sort((a, b) => a.startedAt - b.startedAt).slice(-4)
      .map(p => ({
        time: hhmm(p.startedAt), ep: epOf(p.id), task: shortId(p.taskId),
        st: p.status, col: STC[p.status], pct: `${p.status === "SUCCEEDED" ? 100 : p.progress || 0} %`,
        cr: fmtCr(phaseCredits(p.id).cr),
        crCol: p.status === "SUCCEEDED" ? "var(--accent)" : "var(--ink-soft)",
        live: p.status === "IN_PROGRESS",
      }));
  } else {
    rows = S.persisted.slice(0, 4).reverse().map(t => ({
      time: t.created_at ? hhmm(t.created_at) : "—", ep: KIND_EP[t.kind] || t.kind || "—",
      task: shortId(t.id), st: t.status, col: STC[t.status] || STC.PENDING,
      pct: `${t.progress} %`, cr: fmtCr(t.consumed_credits),
      crCol: t.status === "SUCCEEDED" ? "var(--accent)" : "var(--ink-soft)", live: false,
    }));
  }
  jr.innerHTML = rows.length ? rows.map(r => `
    <div class="jrow${r.live ? " live" : ""}">
      <span class="j-time">${r.time}</span><span class="j-ep">${r.ep}</span>
      <span class="j-task">${r.task}</span>
      <span class="j-st" style="color:${r.col}">${r.st}</span>
      <span class="j-pct">${r.pct}</span>
      <span class="j-cr" style="color:${r.crCol}">${r.cr}</span>
    </div>`).join("")
    : `<div class="journal-empty">aucune tâche Meshy — lance une série pour peupler le journal</div>`;
  const act = S.run && S.run.phases.find(p => p.status === "IN_PROGRESS");
  $("#mQueue").textContent = act && act.queued ? `${act.queued} tâches` : "0 tâche";

  /* panneau droit */
  const aid = activeNodeId();
  const an = NODES.find(n => n.id === aid);
  const ap = phaseView(an.phase);
  $("#mActName").textContent = nodeTitle(aid);
  $("#mActStatus").textContent = `${ap.status}${ap.status === "IN_PROGRESS" ? ` ${ap.progress || 0} %` : ""}`;
  $("#mActStatus").style.color = STC[ap.status];
  $("#activeNode").style.borderColor = ["PENDING", "SKIPPED"].includes(ap.status) ? "var(--stroke)" : STC[ap.status];
  $("#mActEp").textContent = an.phase === "source" ? EP_LABEL.source : epOf(an.phase);
  $("#params").innerHTML = paramsOf(aid, ap)
    .map(([k, v]) => `<div class="prow"><span>${k}</span><span>${v}</span></div>`).join("");
  $("#mActCost").textContent = `${an.phase === "source" ? 0 : phaseCredits(an.phase).cr} crédits`;

  /* actions animation */
  const acts = S.cfg.animationActions;
  const doneN = S.run ? (S.run.outputs.animations || []).length : 0;
  const animPh = phaseView("animate");
  $("#actions").innerHTML = acts.length ? acts.map((a, i) => {
    const dot = i < doneN ? "var(--green)"
      : (animPh.status === "IN_PROGRESS" && i === doneN) ? "var(--accent)" : "var(--ink-muted)";
    return `<div class="action-row"><span class="dot" style="background:${dot}"></span>
      <span class="name">${a.name || `action ${a.actionId}`}</span>
      <span class="meta">action ${a.actionId} · 3 cr</span></div>`;
  }).join("") : `<div class="actions-empty">aucune action — double-clic sur 05 · animation</div>`;

  renderPreview();
}

function renderPreview() {
  const box = $("#previewBox"), ph = $("#previewPh");
  const texDone = phaseView("texture").status === "SUCCEEDED";
  const prevDone = phaseView("preview").status === "SUCCEEDED";
  const rigDone = phaseView("rig").status === "SUCCEEDED";
  let glb = S.run?.outputs?.modelUrls?.glb;
  if (!glb) {
    const t = S.persisted.find(x => x.local_files && x.local_files.glb);
    if (t) glb = t.local_files.glb;
  }
  if (glb && customElements.get("model-viewer")) {
    if (box.dataset.src !== glb) {
      box.dataset.src = glb;
      ph.classList.add("hidden");
      let mv = box.querySelector("model-viewer");
      if (!mv) {
        mv = document.createElement("model-viewer");
        mv.setAttribute("camera-controls", "");
        mv.setAttribute("auto-rotate", "");
        mv.setAttribute("interaction-prompt", "none");
        box.insertBefore(mv, box.firstChild);
      }
      mv.setAttribute("src", glb);
    }
  } else {
    ph.classList.remove("hidden");
    ph.textContent = rigDone ? "riggé + animé" : texDone ? "modèle texturé"
      : prevDone ? "maillage nu" : (S.run && S.run.status === "running") ? "en génération" : "en attente";
    ph.style.borderColor = rigDone ? "var(--c-av)" : texDone ? "var(--c-3d)" : "var(--stroke-strong)";
  }
}

/* ── transport ────────────────────────────────────────────────────────────── */
function setPlaying(on) {
  S.playing = on;
  const svg = $("#cables");
  try { on ? svg.unpauseAnimations() : svg.pauseAnimations(); } catch { /* vieux moteurs */ }
  $("#graph").classList.toggle("paused", !on);
  render();
}

/* ── lancement du pipeline (coût confirmé AVANT) ─────────────────────────── */
function openConfirm() {
  const est = estimate();
  $("#confirmLines").innerHTML = est.lines
    .map(l => `<div class="prow"><span>${l.label}</span><span>${fmtCr(l.credits)}</span></div>`).join("");
  $("#confirmTotal").textContent = fmtCr(est.total);
  $("#confirmHost").textContent = S.status.host;
  $("#confirmGo").textContent = `Lancer · ${fmtCr(est.total)}`;
  $("#confirmNote").textContent = S.status.mock
    ? "Simulateur local : aucune tâche réelle, aucun crédit consommé."
    : "Le coût réel comptabilisé est le consumed_credits de chaque tâche (une tâche échouée est remboursée).";
  $("#confirm").classList.remove("hidden");
}

async function runPipeline() {
  const client = new MeshyClient({ baseUrl: "/api/meshy" });
  const cfg = effCfg();
  if (cfg.source !== "image") delete cfg.imageUrl;
  const run = new MeshyPipeline(client, cfg);
  S.pipeline = run;
  S.run = run.state;
  S.pinned = null;
  run.on(() => render());
  try {
    await run.start();
    toast(`Série terminée — ${fmtCr(run.state.consumedCredits)} consommés`);
  } catch (e) {
    toast(e.insufficientCredits ? "Crédits Meshy insuffisants (402) — série bloquée"
      : e.rateLimited ? "Quota Meshy atteint (429) — réessaie plus tard" : `Échec : ${e.message}`);
  }
  await Promise.all([loadBalance(), loadTasks()]);
  render();
}

/* ── éditeurs de nœuds (double-clic — « double-clic pour éditer ») ───────── */
function fld(label, inner) { return `<label class="fld"><span>${label}</span>${inner}</label>`; }
function esc(s) { return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

async function openEditor(id) {
  const c = S.cfg, body = $("#modalBody");
  const cost = (phid) => fmtCr(phaseCredits(phid).cr);
  let html = "", apply = null;
  if (id === "prompt") {
    $("#modalTitle").textContent = "00 · prompt — source de la série";
    $("#modalCost").textContent = "0 cr";
    html = fld("Nom de l'asset", `<input type="text" id="f-name" value="${esc(c.name)}">`)
      + fld("Prompt de scène", `<textarea id="f-prompt">${esc(c.prompt)}</textarea>`)
      + fld("Source du maillage", `<select id="f-source">
          <option value="text"${c.source === "text" ? " selected" : ""}>texte → /v2/text-to-3d (preview + refine)</option>
          <option value="image"${c.source === "image" ? " selected" : ""}>image → /v1/image-to-3d (passe unique)</option>
        </select>`)
      + `<div class="fld-note">La source image exige une image de départ (nœud 00 · réf.).</div>`;
    apply = () => {
      c.name = $("#f-name").value.trim() || "asset_3d";
      c.prompt = $("#f-prompt").value;
      c.source = $("#f-source").value;
      if (c.source === "image" && !c.imageUrl) { c.source = "text"; toast("Pas d'image de départ — source texte conservée"); }
    };
  } else if (id === "ref") {
    $("#modalTitle").textContent = "00 · réf. — image de départ (Library)";
    $("#modalCost").textContent = "0 cr";
    if (!S.libImages) {
      try { S.libImages = (await jget("/api/images")).images || []; } catch { S.libImages = []; }
    }
    S.pickedImage = c.imageName;
    html = (S.libImages.length
      ? `<div class="img-pick" id="f-pick">${S.libImages.slice(0, 24).map(im =>
        `<button data-f="${esc(im.filename)}" class="${im.filename === c.imageName ? "sel" : ""}" title="${esc(im.filename)}">
           <img src="/api/images/${encodeURIComponent(im.filename)}" alt="" loading="lazy"></button>`).join("")}</div>`
      : `<div class="fld-note">Library vide — génère ou importe une image d'abord.</div>`)
      + `<div class="fld-note">L'image est transmise à Meshy en data URI via le proxy — elle ne quitte pas la machine autrement. <b>Vider :</b> re-sélectionner l'image active.</div>`;
    apply = async () => {
      if (!S.pickedImage) return;
      if (S.pickedImage === c.imageName) { c.imageUrl = null; c.imageName = null; if (c.source === "image") c.source = "text"; return; }
      const blob = await (await fetch(`/api/images/${encodeURIComponent(S.pickedImage)}`)).blob();
      c.imageUrl = await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(blob); });
      c.imageName = S.pickedImage;
    };
  } else if (id === "preview") {
    $("#modalTitle").textContent = "01 · maillage — text/image-to-3d";
    $("#modalCost").textContent = cost("preview");
    html = `<div class="fld-row">`
      + fld("ai_model", `<select id="f-model"><option${c.aiModel === "meshy-7" ? " selected" : ""}>meshy-7</option><option${c.aiModel === "meshy-6" ? " selected" : ""}>meshy-6</option><option${c.aiModel === "meshy-5" ? " selected" : ""}>meshy-5</option></select>`)
      + fld("pose_mode", `<select id="f-pose"><option value="a-pose"${c.poseMode === "a-pose" ? " selected" : ""}>a-pose (meilleur rig)</option><option value="t-pose"${c.poseMode === "t-pose" ? " selected" : ""}>t-pose</option><option value=""${!c.poseMode ? " selected" : ""}>libre</option></select>`)
      + `</div><div class="fld-row">`
      + fld("topology", `<select id="f-topo"><option${c.topology === "quad" ? " selected" : ""}>quad</option><option${c.topology === "triangle" ? " selected" : ""}>triangle</option></select>`)
      + fld("target_polycount", `<input type="number" id="f-poly" value="${c.targetPolycount}" min="1000" step="1000">`)
      + `</div><div class="fld-note">meshy-7 : même grille que meshy-6 (20 cr le preview, 30 cr texturé), alignement image→3D supérieur ; ultra +5 cr (Forge 3D des cartes). meshy-6 : sortie haute précision souvent &gt; 300 000 faces → remesh obligatoire avant le rig. meshy-5 : 5 cr.</div>`;
    apply = () => {
      c.aiModel = $("#f-model").value; c.poseMode = $("#f-pose").value;
      c.topology = $("#f-topo").value;
      c.targetPolycount = Math.max(1000, parseInt($("#f-poly").value, 10) || 30000);
    };
  } else if (id === "texture") {
    $("#modalTitle").textContent = "02 · texture — refine PBR";
    $("#modalCost").textContent = cost("texture");
    html = `<label class="fld-check"><input type="checkbox" id="f-wtex"${c.withTexture ? " checked" : ""}> Texturer (refine — 10 cr en 2k/4k, 15 cr en 8k)</label>`
      + `<div class="fld-row">`
      + fld("texture_resolution", `<select id="f-res">${["2k", "4k", "8k"].map(r => `<option${c.textureResolution === r ? " selected" : ""}>${r}</option>`).join("")}</select>`)
      + fld("enable_pbr", `<select id="f-pbr"><option value="true"${c.enablePbr ? " selected" : ""}>true</option><option value="false"${!c.enablePbr ? " selected" : ""}>false</option></select>`)
      + `</div>`
      + fld("texture_prompt (optionnel)", `<input type="text" id="f-texp" value="${esc(c.texturePrompt)}">`)
      + `<div class="fld-note fld-warn">8k : interdit la topologie quad et supprime la carte d'émission.</div>`;
    apply = () => {
      c.withTexture = $("#f-wtex").checked;
      c.textureResolution = $("#f-res").value;
      c.enablePbr = $("#f-pbr").value === "true";
      c.texturePrompt = $("#f-texp").value;
      if (c.textureResolution === "8k" && c.topology === "quad") { c.topology = "triangle"; toast("8k : topologie repassée en triangle (contrainte Meshy)"); }
    };
  } else if (id === "remesh") {
    $("#modalTitle").textContent = "03 · topologie — remesh";
    $("#modalCost").textContent = cost("remesh");
    html = `<label class="fld-check"><input type="checkbox" id="f-wrem"${c.withRemesh ? " checked" : ""}> Remesh (5 cr) — obligatoire au-delà de 300 000 faces avant le rig</label>`
      + `<div class="fld-row">`
      + fld("topology", `<select id="f-topo2"><option${c.topology === "quad" ? " selected" : ""}>quad</option><option${c.topology === "triangle" ? " selected" : ""}>triangle</option></select>`)
      + fld("target_polycount", `<input type="number" id="f-poly2" value="${c.targetPolycount}" min="1000" step="1000">`)
      + `</div>`;
    apply = () => {
      c.withRemesh = $("#f-wrem").checked;
      c.topology = $("#f-topo2").value;
      c.targetPolycount = Math.max(1000, parseInt($("#f-poly2").value, 10) || 30000);
    };
  } else if (id === "rig") {
    $("#modalTitle").textContent = "04 · squelette — auto-rig";
    $("#modalCost").textContent = cost("rig");
    html = `<label class="fld-check"><input type="checkbox" id="f-wrig"${c.withRig ? " checked" : ""}> Auto-rig humanoïde (5 cr) — modèle texturé, face vers +Z</label>`
      + fld("height_meters", `<input type="number" id="f-h" value="${c.heightMeters}" min="0.1" max="5" step="0.05">`)
      + `<div class="fld-note">Sans rig, les actions d'animation sont sautées (et retirées de l'estimé).</div>`;
    apply = () => {
      c.withRig = $("#f-wrig").checked;
      c.heightMeters = Math.min(5, Math.max(0.1, parseFloat($("#f-h").value) || 1.75));
    };
  } else if (id === "animate") {
    $("#modalTitle").textContent = "05 · animation — actions de la bibliothèque Meshy";
    $("#modalCost").textContent = cost("animate");
    html = c.animationActions.map((a, i) => `<div class="fld-row" data-act="${i}">`
      + fld("action_id", `<input type="number" class="f-aid" value="${a.actionId}">`)
      + fld("nom", `<input type="text" class="f-aname" value="${esc(a.name)}">`)
      + fld("retirer", `<select class="f-adel"><option value="">garder</option><option value="1">retirer</option></select>`)
      + `</div>`).join("")
      + `<div class="fld-row">`
      + fld("nouvelle action_id", `<input type="number" id="f-newid" placeholder="ex. 7">`)
      + fld("nom", `<input type="text" id="f-newname" placeholder="run_cycle">`)
      + `</div>`
      + fld("fps (post_process change_fps)", `<input type="number" id="f-fps" value="${c.fps}" min="1" max="60">`)
      + `<div class="fld-note">3 cr par action. Une tâche /v1/animations par action, enchaînées sur le rig.</div>`;
    apply = () => {
      const rows = [...$("#modalBody").querySelectorAll("[data-act]")];
      c.animationActions = rows
        .filter(r => !r.querySelector(".f-adel").value)
        .map(r => ({ actionId: parseInt(r.querySelector(".f-aid").value, 10) || 0,
                     name: r.querySelector(".f-aname").value.trim() }))
        .filter(a => a.actionId > 0);
      const nid = parseInt($("#f-newid").value, 10);
      if (nid > 0) c.animationActions.push({ actionId: nid, name: $("#f-newname").value.trim() || `action_${nid}` });
      c.fps = Math.min(60, Math.max(1, parseInt($("#f-fps").value, 10) || 24));
    };
  } else if (id === "export") {
    $("#modalTitle").textContent = "06 · export — livrables";
    $("#modalCost").textContent = cost("export");
    const all = ["glb", "fbx", "obj", "usdz", "stl", "3mf"];
    html = all.map(f => `<label class="fld-check"><input type="checkbox" class="f-fmt" value="${f}"${c.exportFormats.includes(f) ? " checked" : ""}> ${f.toUpperCase()}${f === "3mf" ? " — conversion 1 cr (opt-in)" : " — natif, gratuit"}</label>`).join("")
      + `<div class="fld-note">target_formats réduit le temps de tâche : ne demander que ce qu'on exporte.</div>`;
    apply = () => {
      const sel = [...$("#modalBody").querySelectorAll(".f-fmt:checked")].map(x => x.value);
      c.exportFormats = sel.length ? sel : ["glb"];
    };
  }
  body.innerHTML = html;
  if (id === "ref") {
    body.querySelectorAll("#f-pick button").forEach(b => b.addEventListener("click", () => {
      body.querySelectorAll("#f-pick button").forEach(x => x.classList.remove("sel"));
      b.classList.add("sel");
      S.pickedImage = b.dataset.f;
    }));
  }
  $("#modal").classList.remove("hidden");
  $("#modalApply").onclick = async () => {
    if (apply) await apply();
    $("#modal").classList.add("hidden");
    render();
  };
}

/* ── divers ───────────────────────────────────────────────────────────────── */
let _toastT = 0;
function toast(msg) {
  let t = $("#toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.style.cssText = "position:fixed; left:50%; bottom:26px; transform:translateX(-50%);"
      + "background:var(--bg-panel-2); border:1px solid var(--stroke-strong); color:var(--ink-strong);"
      + "padding:9px 14px; border-radius:9px; font-size:12.5px; z-index:99; max-width:80vw;";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.display = "block";
  clearTimeout(_toastT);
  _toastT = setTimeout(() => { t.style.display = "none"; }, 4200);
}

function gotoSubtab(tab) {
  try {
    if (window.parent && window.parent !== window) {
      window.parent.dispatchEvent(new CustomEvent("deepotus:assets-subtab", { detail: { subtab: tab } }));
      return;
    }
  } catch { /* iframe cross-origin improbable (même origine) */ }
  location.href = tab === "sprites" ? "/spritelab/" : "/";
}

/* ── init ─────────────────────────────────────────────────────────────────── */
(function init() {
  /* EN PREMIER, avant buildGraph() et avant le premier render() : les deux
     peignent `S.cfg`, et une réhydratation d'après coup ferait clignoter la
     page du défaut vers la config retrouvée. */
  rehydraterCfg();
  buildGraph();
  const style = document.createElement("style");
  style.textContent = `
    .graph svg path.flow { animation: dz-dash .38s linear infinite; }
    .graph.paused svg path.flow, .graph.paused .node-mesh.working { animation-play-state: paused; }
    @keyframes dz-dash { to { stroke-dashoffset: -14; } }
    .node-mesh.working { animation: dz-shim 1.2s linear infinite; }
    @keyframes dz-shim { to { background-position: 44px 0; } }
    @media (prefers-reduced-motion: reduce) { .graph svg path.flow, .node-mesh.working { animation: none; } }`;
  document.head.appendChild(style);

  $("#btnPlay").addEventListener("click", () => setPlaying(!S.playing));
  $("#btnReplay").addEventListener("click", () => {
    if (S.run && S.run.status === "running") { toast("Série en cours — ↺ disponible à la fin"); return; }
    S.run = null; S.pipeline = null; S.pinned = null;
    render();
  });
  $("#btnRun").addEventListener("click", openConfirm);
  $("#confirmCancel").addEventListener("click", () => $("#confirm").classList.add("hidden"));
  $("#confirmGo").addEventListener("click", () => { $("#confirm").classList.add("hidden"); runPipeline(); });
  $("#modalCancel").addEventListener("click", () => $("#modal").classList.add("hidden"));
  $("#goSprite").addEventListener("click", () => gotoSubtab("sprites"));
  $("#goEtabli").addEventListener("click", ouvrirEtabli);
  $("#engineGoto").addEventListener("click", () => gotoSubtab("3d"));

  /* Le filet des départs qui ne passent pas par ouvrirEtabli() : rechargement,
     fermeture de l'onglet, retour arrière, gotoSubtab. `pagehide` et non
     `beforeunload` : ce dernier ne sert vraiment qu'à POSER UNE QUESTION, il
     évince la page du cache de retour arrière et les navigateurs l'ignorent
     de plus en plus dans une iframe — or on ne demande rien ici, on écrit. */
  window.addEventListener("pagehide", memoriserCfg);

  render();
  Promise.all([loadStatus(), loadHealth()]).then(async () => {
    await Promise.all([loadBalance(), loadTasks()]);
    render();
  });
})();
