/* ════════════════════════════════════════════════════════════════════════════
   meshy.client.js — client Meshy officiel + orchestrateur de pipeline
   DeepOtus Video · v1.0 · aucune dépendance, ES module, navigateur ou Node 18+

   Couvre la surface documentée sur docs.meshy.ai :
     v2 text-to-3d (preview → refine)  ·  v1 image-to-3d  ·  v1 multi-image-to-3d
     remesh · convert · resize · uv-unwrap · rigging · animations · retexture
     text-to-image · image-to-image · balance
   Chaque tâche est asynchrone : POST → id, puis GET /:id ou SSE /:id/stream.
   Statuts : PENDING · IN_PROGRESS · SUCCEEDED · FAILED · CANCELED.

   ⚠ La clé API ne doit JAMAIS être exposée au navigateur. En production,
   `baseUrl` pointe sur le proxy backend DeepOtus (voir INTEGRATION-MESHY.md),
   qui injecte l'en-tête Authorization côté serveur.
   ════════════════════════════════════════════════════════════════════════════ */

export const MESHY_API = "https://api.meshy.ai";

/* ── Tarifs officiels, en crédits Meshy (docs.meshy.ai/en/api/pricing) ──────── */
export const CREDITS = {
  _hd: (m, t) => m === "meshy-6" || m === "meshy-7" || m === "latest" || t === "lowpoly",
  _ultra: (m, u) => (u && (m === "meshy-7" || m === "latest") ? 5 : 0),
  textTo3dPreview: ({ aiModel = "meshy-6", modelType = "standard", ultra = false } = {}) =>
    (CREDITS._hd(aiModel, modelType) ? 20 : 5) + CREDITS._ultra(aiModel, ultra),
  textTo3dRefine: ({ textureResolution = "2k" } = {}) => (textureResolution === "8k" ? 15 : 10),
  imageTo3d: ({ aiModel = "meshy-6", modelType = "standard", shouldTexture = true, textureResolution = "2k", ultra = false } = {}) => {
    const smart = modelType === "smart-topology";
    const base = !shouldTexture ? (smart ? 5 : (CREDITS._hd(aiModel, modelType) ? 20 : 5))
      : textureResolution === "8k" ? (smart ? 20 : 35)
      : (smart ? 15 : (CREDITS._hd(aiModel, modelType) ? 30 : 15));
    return base + CREDITS._ultra(aiModel, ultra);
  },
  multiImageTo3d: (o = {}) => CREDITS.imageTo3d(o),
  retexture: ({ textureResolution = "2k" } = {}) => (textureResolution === "8k" ? 15 : 10),
  remesh: () => 5,
  convert: () => 1,
  resize: () => 1,
  uvUnwrap: () => 1,
  rigging: () => 5,
  animation: () => 3,
  textToImage: ({ model = "nano-banana" } = {}) =>
    ({ "nano-banana": 3, "nano-banana-2": 6, "nano-banana-pro": 9, "gpt-image-2": 9 })[model] ?? 3,
  imageToImage: ({ model = "nano-banana" } = {}) =>
    ({ "nano-banana": 3, "nano-banana-2": 6, "nano-banana-pro": 9, "gpt-image-2": 12 })[model] ?? 3,
  printMultiColor: () => 10,
  printAnalyze: () => 0,
  printRepair: () => 10
};

export const TERMINAL = ["SUCCEEDED", "FAILED", "CANCELED"];
export const EXPORT_FORMATS = ["glb", "fbx", "obj", "stl", "usdz", "3mf"];

export class MeshyError extends Error {
  constructor(message, { status, body, taskId } = {}) {
    super(message);
    this.name = "MeshyError";
    this.status = status; this.body = body; this.taskId = taskId;
    /* 402 = crédits insuffisants, 429 = quota atteint : à remonter en UI */
    this.insufficientCredits = status === 402;
    this.rateLimited = status === 429;
  }
}

export class MeshyClient {
  /**
   * @param {object} opts
   * @param {string} [opts.baseUrl]  proxy backend en prod, MESHY_API en direct
   * @param {string} [opts.apiKey]   uniquement côté serveur
   * @param {function} [opts.fetch]
   */
  constructor({ baseUrl = MESHY_API, apiKey = null, fetch: f = globalThis.fetch } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this._fetch = f.bind(globalThis);
  }

  get headers() {
    const h = { "Content-Type": "application/json" };
    if (this.apiKey) h.Authorization = `Bearer ${this.apiKey}`;
    return h;
  }

  async request(method, path, body) {
    const res = await this._fetch(this.baseUrl + path, {
      method, headers: this.headers, body: body ? JSON.stringify(body) : undefined
    });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!res.ok) {
      throw new MeshyError(data?.message || `Meshy ${method} ${path} → ${res.status}`, { status: res.status, body: data });
    }
    return data;
  }

  /* ── Génération ─────────────────────────────────────────────────────────── */

  /** Text to 3D, étape 1 : maillage sans texture. 20 cr (meshy-6). */
  textTo3dPreview({ prompt, aiModel = "meshy-6", modelType = "standard", topology, targetPolycount,
                    decimationMode, shouldRemesh, poseMode = "", targetFormats, autoSize, originAt,
                    alphaThumbnail, moderation = true }) {
    return this.request("POST", "/openapi/v2/text-to-3d", clean({
      mode: "preview", prompt, ai_model: aiModel, model_type: modelType, topology,
      target_polycount: targetPolycount, decimation_mode: decimationMode, should_remesh: shouldRemesh,
      pose_mode: poseMode, target_formats: targetFormats, auto_size: autoSize, origin_at: originAt,
      alpha_thumbnail: alphaThumbnail, moderation
    })).then(r => r.result);
  }

  /** Text to 3D, étape 2 : texture sur un preview SUCCEEDED. 10 cr (2k/4k), 15 cr (8k). */
  textTo3dRefine({ previewTaskId, enablePbr = true, textureResolution = "2k", texturePrompt,
                   textureImageUrl, aiModel = "meshy-6", removeLighting, targetFormats,
                   autoSize, originAt, moderation = true }) {
    return this.request("POST", "/openapi/v2/text-to-3d", clean({
      mode: "refine", preview_task_id: previewTaskId, enable_pbr: enablePbr,
      texture_resolution: textureResolution, texture_prompt: texturePrompt,
      texture_image_url: textureImageUrl, ai_model: aiModel, remove_lighting: removeLighting,
      target_formats: targetFormats, auto_size: autoSize, origin_at: originAt, moderation
    })).then(r => r.result);
  }

  /** Image to 3D — une seule passe (pas de preview/refine). 30 cr texturé (meshy-6/7) ; +5 cr en ultra (meshy-7/latest). */
  imageTo3d({ imageUrl, inputTaskId, modelType = "standard", aiModel = "meshy-6", shouldTexture = true,
              enablePbr = true, textureResolution = "2k", texturePrompt, textureImageUrl,
              shouldRemesh, topology, targetPolycount, decimationMode, savePreRemeshedModel,
              poseMode = "", imageEnhancement, removeLighting, targetFormats, autoSize, originAt,
              alphaThumbnail, multiViewThumbnails, ultra = false, moderation = true }) {
    return this.request("POST", "/openapi/v1/image-to-3d", clean({
      image_url: imageUrl, input_task_id: inputTaskId, model_type: modelType, ai_model: aiModel,
      should_texture: shouldTexture, enable_pbr: enablePbr, texture_resolution: textureResolution,
      texture_prompt: texturePrompt, texture_image_url: textureImageUrl, should_remesh: shouldRemesh,
      topology, target_polycount: targetPolycount, decimation_mode: decimationMode,
      save_pre_remeshed_model: savePreRemeshedModel, pose_mode: poseMode,
      image_enhancement: imageEnhancement, remove_lighting: removeLighting,
      target_formats: targetFormats, auto_size: autoSize, origin_at: originAt,
      alpha_thumbnail: alphaThumbnail, multi_view_thumbnails: multiViewThumbnails,
      ultra_mode: ultra ? true : undefined, moderation
    })).then(r => r.result);
  }

  /** Multi Image to 3D — jusqu'à 4 vues cardinales du même sujet. */
  multiImageTo3d({ imageUrls, ...rest }) {
    return this.request("POST", "/openapi/v1/multi-image-to-3d", clean({
      image_urls: imageUrls, ...snakeRest(rest)
    })).then(r => r.result);
  }

  /* ── Post-traitement ────────────────────────────────────────────────────── */

  /** Remesh : topologie + décimation. 5 cr. Obligatoire au-delà de 300 000 faces avant rig. */
  remesh({ inputTaskId, modelUrl, targetFormats = ["glb", "fbx"], topology = "quad",
           targetPolycount = 30000, decimationMode, resizeHeight, originAt, convertFormatOnly }) {
    return this.request("POST", "/openapi/v1/remesh", clean({
      input_task_id: inputTaskId, model_url: modelUrl, target_formats: targetFormats,
      topology, target_polycount: targetPolycount, decimation_mode: decimationMode,
      resize_height: resizeHeight, origin_at: originAt, convert_format_only: convertFormatOnly
    })).then(r => r.result);
  }

  /** Retexture : nouvelle passe de texture sur un modèle existant. 10 / 15 cr. */
  retexture({ inputTaskId, modelUrl, textPrompt, imageUrl, enablePbr = true,
              textureResolution = "2k", aiModel = "meshy-6", targetFormats, moderation = true }) {
    return this.request("POST", "/openapi/v1/retexture", clean({
      input_task_id: inputTaskId, model_url: modelUrl, text_style_prompt: textPrompt,
      image_style_url: imageUrl, enable_pbr: enablePbr, texture_resolution: textureResolution,
      ai_model: aiModel, target_formats: targetFormats, moderation
    })).then(r => r.result);
  }

  /** Conversion de format seule. 1 cr. */
  convert({ inputTaskId, modelUrl, targetFormats }) {
    return this.request("POST", "/openapi/v1/convert", clean({
      input_task_id: inputTaskId, model_url: modelUrl, target_formats: targetFormats
    })).then(r => r.result);
  }

  /** Auto-rig humanoïde. 5 cr. Modèle texturé, ≤ 300 000 faces, face vers +Z. */
  rig({ inputTaskId, modelUrl, heightMeters = 1.7, textureImageUrl }) {
    return this.request("POST", "/openapi/v1/rigging", clean({
      input_task_id: inputTaskId, model_url: modelUrl,
      height_meters: heightMeters, texture_image_url: textureImageUrl
    })).then(r => r.result);
  }

  /** Applique une action de la bibliothèque d'animations à un rig. 3 cr par action. */
  animate({ rigTaskId, actionId, postProcess }) {
    return this.request("POST", "/openapi/v1/animations", clean({
      rig_task_id: rigTaskId, action_id: actionId, post_process: postProcess
    })).then(r => r.result);
  }

  /* ── Images 2D (utile pour fabriquer la référence en amont du 3D) ───────── */
  textToImage(p) { return this.request("POST", "/openapi/v1/text-to-image", clean(snakeRest(p))).then(r => r.result); }
  imageToImage(p) { return this.request("POST", "/openapi/v1/image-to-image", clean(snakeRest(p))).then(r => r.result); }

  /* ── Lecture ────────────────────────────────────────────────────────────── */
  get(kind, id) { return this.request("GET", `${endpointOf(kind)}/${id}`); }
  list(kind, { pageNum = 1, pageSize = 20, sortBy = "-created_at" } = {}) {
    return this.request("GET", `${endpointOf(kind)}?page_num=${pageNum}&page_size=${pageSize}&sort_by=${encodeURIComponent(sortBy)}`);
  }
  remove(kind, id) { return this.request("DELETE", `${endpointOf(kind)}/${id}`); }
  /** Solde du portefeuille API — à afficher dans la barre supérieure. */
  balance() { return this.request("GET", "/openapi/v1/balance"); }

  /**
   * Suit une tâche jusqu'à un statut terminal.
   * Utilise le flux SSE `/:id/stream` quand EventSource est disponible et que la
   * clé transite par le proxy ; retombe sinon sur un polling adaptatif.
   * @param {(task:object)=>void} onProgress
   */
  async wait(kind, id, { onProgress, intervalMs = 2500, timeoutMs = 15 * 60_000, signal } = {}) {
    const started = Date.now();
    for (;;) {
      if (signal?.aborted) throw new MeshyError("Suivi annulé", { taskId: id });
      const task = await this.get(kind, id);
      onProgress?.(task);
      if (TERMINAL.includes(task.status)) {
        if (task.status !== "SUCCEEDED") {
          throw new MeshyError(task.task_error?.message || `Tâche ${task.status}`, { taskId: id, body: task });
        }
        return task;
      }
      if (Date.now() - started > timeoutMs) throw new MeshyError("Délai de suivi dépassé", { taskId: id });
      /* file d'attente longue → on espace les appels pour ménager le quota */
      const wait = task.status === "PENDING" && task.preceding_tasks > 2 ? intervalMs * 2 : intervalMs;
      await sleep(wait);
    }
  }

  /** Flux SSE natif — progression à la seconde, sans polling. */
  stream(kind, id, { onMessage, onError } = {}) {
    const url = `${this.baseUrl}${endpointOf(kind)}/${id}/stream`;
    const es = new EventSource(url, { withCredentials: true });
    es.addEventListener("message", e => {
      const task = JSON.parse(e.data);
      onMessage?.(task);
      if (TERMINAL.includes(task.status)) es.close();
    });
    es.addEventListener("error", e => { onError?.(e); es.close(); });
    return () => es.close();
  }
}

function endpointOf(kind) {
  const map = {
    "text-to-3d": "/openapi/v2/text-to-3d",
    "image-to-3d": "/openapi/v1/image-to-3d",
    "multi-image-to-3d": "/openapi/v1/multi-image-to-3d",
    remesh: "/openapi/v1/remesh",
    convert: "/openapi/v1/convert",
    resize: "/openapi/v1/resize",
    "uv-unwrap": "/openapi/v1/uv-unwrap",
    retexture: "/openapi/v1/retexture",
    rig: "/openapi/v1/rigging",
    animate: "/openapi/v1/animations",
    "text-to-image": "/openapi/v1/text-to-image",
    "image-to-image": "/openapi/v1/image-to-image"
  };
  const e = map[kind];
  if (!e) throw new MeshyError(`Type de tâche inconnu : ${kind}`);
  return e;
}

const clean = o => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== ""));
const snakeRest = o => Object.fromEntries(Object.entries(o).map(([k, v]) => [k.replace(/[A-Z]/g, c => "_" + c.toLowerCase()), v]));
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* ════════════════════════════════════════════════════════════════════════════
   Orchestrateur de pipeline — c'est lui que le graphe de nœuds affiche.
   Émet un événement à chaque transition ; l'UI ne fait que rendre l'état.
   ════════════════════════════════════════════════════════════════════════════ */

/** Description canonique des phases. `kind` pilote la couleur catégorielle UI. */
export const PHASES = [
  { id: "source",  kind: "text",  label: "Source",       endpoint: "—",                     credits: 0 },
  { id: "preview", kind: "3d",    label: "Maillage",     endpoint: "POST /v2/text-to-3d",   credits: 20 },
  { id: "texture", kind: "image", label: "Texture PBR",  endpoint: "POST /v2/text-to-3d",   credits: 10 },
  { id: "remesh",  kind: "3d",    label: "Remesh",       endpoint: "POST /v1/remesh",       credits: 5 },
  { id: "rig",     kind: "av",    label: "Auto-rig",     endpoint: "POST /v1/rigging",      credits: 5 },
  { id: "animate", kind: "av",    label: "Animation",    endpoint: "POST /v1/animations",   credits: 3 },
  { id: "export",  kind: "video", label: "Export",       endpoint: "POST /v1/convert",      credits: 1 }
];

/**
 * Calcule le coût total AVANT lancement — exigence produit : coût toujours visible.
 * @returns {{total:number, lines:Array<{id:string,label:string,credits:number}>}}
 */
export function estimatePipeline(cfg = {}) {
  const {
    source = "text", aiModel = "meshy-6", modelType = "standard",
    textureResolution = "2k", withTexture = true, withRemesh = true,
    withRig = true, animationActions = [], exportFormats = ["glb", "fbx"],
    ultra = false
  } = cfg;
  const lines = [];
  if (source === "text") {
    lines.push({ id: "preview", label: "Maillage · text-to-3d preview", credits: CREDITS.textTo3dPreview({ aiModel, modelType, ultra }) });
    if (withTexture) lines.push({ id: "texture", label: `Texture PBR ${textureResolution} · refine`, credits: CREDITS.textTo3dRefine({ textureResolution }) });
  } else {
    lines.push({ id: "preview", label: `Maillage + texture · image-to-3d`, credits: CREDITS.imageTo3d({ aiModel, modelType, shouldTexture: withTexture, textureResolution, ultra }) });
  }
  if (withRemesh) lines.push({ id: "remesh", label: "Remesh · topologie", credits: CREDITS.remesh() });
  if (withRig) lines.push({ id: "rig", label: "Auto-rig humanoïde", credits: CREDITS.rigging() });
  for (const a of animationActions) lines.push({ id: "animate", label: `Animation · ${a.name ?? a.actionId ?? a}`, credits: CREDITS.animation() });
  const extra = exportFormats.filter(f => !["glb", "fbx", "obj", "usdz", "stl"].includes(f));
  if (extra.length) lines.push({ id: "export", label: `Conversion ${extra.join(", ")}`, credits: extra.length * CREDITS.convert() });
  return { total: lines.reduce((s, l) => s + l.credits, 0), lines };
}

/**
 * Exécute le pipeline complet. Chaque phase émet start / progress / done / error.
 * L'orchestrateur n'affiche rien : il produit un état que le graphe consomme.
 *
 *   const run = new MeshyPipeline(client, cfg);
 *   run.on(state => setGraphState(state));
 *   await run.start();
 */
export class MeshyPipeline {
  constructor(client, config = {}) {
    this.client = client;
    this.config = config;
    this.listeners = new Set();
    this.abort = new AbortController();
    this.state = {
      status: "idle",
      consumedCredits: 0,
      estimate: estimatePipeline(config).total,
      phases: PHASES.map(p => ({ ...p, status: "PENDING", progress: 0, taskId: null, startedAt: 0, finishedAt: 0, error: null })),
      outputs: {}
    };
  }

  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  emit() { for (const fn of this.listeners) fn(this.state); }

  _phase(id) { return this.state.phases.find(p => p.id === id); }
  _set(id, patch) { Object.assign(this._phase(id), patch); this.emit(); }

  /** Enchaîne une tâche Meshy et tient la phase à jour (statut, %, crédits réels). */
  async _run(id, kind, create) {
    const phase = this._phase(id);
    this._set(id, { status: "IN_PROGRESS", startedAt: Date.now(), progress: 0 });
    try {
      const taskId = await create();
      this._set(id, { taskId });
      const task = await this.client.wait(kind, taskId, {
        signal: this.abort.signal,
        onProgress: t => this._set(id, {
          progress: t.progress ?? 0,
          status: t.status,
          queued: t.status === "PENDING" ? t.preceding_tasks : 0
        })
      });
      /* consumed_credits est la vérité comptable : 0 si la tâche a échoué (remboursée) */
      this.state.consumedCredits += task.consumed_credits ?? 0;
      this._set(id, { status: "SUCCEEDED", progress: 100, finishedAt: Date.now(), credits: task.consumed_credits ?? phase.credits });
      return task;
    } catch (err) {
      this._set(id, { status: "FAILED", error: err.message, finishedAt: Date.now() });
      this.state.status = "failed";
      this.emit();
      throw err;
    }
  }

  cancel() { this.abort.abort(); this.state.status = "canceled"; this.emit(); }

  async start() {
    const c = this.config;
    this.state.status = "running"; this.emit();
    const out = this.state.outputs;

    this._set("source", { status: "SUCCEEDED", progress: 100 });

    /* 1-2 · maillage puis texture (text) ou passe unique (image) */
    if (c.source === "image") {
      const t = await this._run("preview", "image-to-3d", () => this.client.imageTo3d({
        imageUrl: c.imageUrl, aiModel: c.aiModel, modelType: c.modelType,
        shouldTexture: c.withTexture !== false, enablePbr: c.enablePbr !== false,
        textureResolution: c.textureResolution, poseMode: c.poseMode, targetFormats: c.exportFormats
      }));
      out.modelUrls = t.model_urls; out.textures = t.texture_urls; out.thumbnail = t.thumbnail_url;
      this._set("texture", { status: "SUCCEEDED", progress: 100, credits: 0, note: "inclus dans image-to-3d" });
    } else {
      const prev = await this._run("preview", "text-to-3d", () => this.client.textTo3dPreview({
        prompt: c.prompt, aiModel: c.aiModel, modelType: c.modelType, topology: c.topology,
        targetPolycount: c.targetPolycount, poseMode: c.poseMode, targetFormats: c.exportFormats
      }));
      out.previewTaskId = prev.id; out.thumbnail = prev.thumbnail_url;
      if (c.withTexture !== false) {
        const ref = await this._run("texture", "text-to-3d", () => this.client.textTo3dRefine({
          previewTaskId: prev.id, enablePbr: c.enablePbr !== false,
          textureResolution: c.textureResolution, texturePrompt: c.texturePrompt,
          aiModel: c.aiModel, targetFormats: c.exportFormats
        }));
        out.modelUrls = ref.model_urls; out.textures = ref.texture_urls; out.thumbnail = ref.thumbnail_url;
      } else {
        out.modelUrls = prev.model_urls;
      }
    }

    /* 3 · remesh — indispensable si > 300 000 faces avant le rig */
    let modelTaskId = this._phase("texture").taskId || this._phase("preview").taskId;
    if (c.withRemesh) {
      const t = await this._run("remesh", "remesh", () => this.client.remesh({
        inputTaskId: modelTaskId, topology: c.topology ?? "quad",
        targetPolycount: c.targetPolycount ?? 30000, targetFormats: c.exportFormats
      }));
      modelTaskId = t.id; out.modelUrls = t.model_urls ?? out.modelUrls;
    } else {
      this._set("remesh", { status: "SKIPPED", credits: 0 });
    }

    /* 4 · auto-rig — humanoïde uniquement */
    let rigTaskId = null;
    if (c.withRig) {
      const t = await this._run("rig", "rig", () => this.client.rig({
        inputTaskId: modelTaskId, heightMeters: c.heightMeters ?? 1.7
      }));
      rigTaskId = t.id;
      out.rigged = t.result;
    } else {
      this._set("rig", { status: "SKIPPED", credits: 0 });
    }

    /* 5 · animations — une tâche par action, 3 cr pièce */
    const actions = c.animationActions ?? [];
    if (rigTaskId && actions.length) {
      out.animations = [];
      for (let i = 0; i < actions.length; i++) {
        const a = actions[i];
        this._set("animate", { progress: Math.round((i / actions.length) * 100), note: `${i + 1}/${actions.length}` });
        const t = await this._run("animate", "animate", () => this.client.animate({
          rigTaskId, actionId: a.actionId ?? a, postProcess: c.fps ? { operation_type: "change_fps", fps: c.fps } : undefined
        }));
        out.animations.push({ name: a.name ?? `action ${a.actionId ?? a}`, ...t.result });
      }
    } else {
      this._set("animate", { status: "SKIPPED", credits: 0 });
    }

    /* 6 · export — formats natifs gratuits, conversions supplémentaires à 1 cr */
    const extra = (c.exportFormats ?? []).filter(f => f === "3mf");
    if (extra.length) {
      const t = await this._run("export", "convert", () => this.client.convert({
        inputTaskId: modelTaskId, targetFormats: extra
      }));
      out.modelUrls = { ...out.modelUrls, ...t.model_urls };
    } else {
      this._set("export", { status: "SUCCEEDED", progress: 100, credits: 0, note: "formats natifs" });
    }

    this.state.status = "done";
    this.emit();
    return this.state;
  }
}

export default MeshyClient;
