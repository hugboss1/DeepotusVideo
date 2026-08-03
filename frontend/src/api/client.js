// Backend API client — v1.2
const BASE = "/api";

async function http(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch {}
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export const api = {
  health: () => http("/health"),
  listImages: () => http("/images"),
  uploadImage: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/images/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  imageUrl: (filename) => `${BASE}/images/${encodeURIComponent(filename)}`,
  listTemplates: () => http("/templates"),
  previewPrompt: (request) =>
    http("/prompt/preview", { method: "POST", body: JSON.stringify(request) }),
  buildPromptFromIntent: (request) =>
    http("/prompt/build", { method: "POST", body: JSON.stringify(request) }),
  generate: (request) =>
    http("/generate", { method: "POST", body: JSON.stringify(request) }),
  generateBatch: (request) =>
    http("/generate/batch", { method: "POST", body: JSON.stringify(request) }),
  // HeyGen (v1.4)
  heygenHealth: () => http("/heygen/health"),
  listHeygenAvatars: () => http("/heygen/avatars"),
  listHeygenVoices: () => http("/heygen/voices"),
  generateHeygen: (request) =>
    http("/generate/heygen", { method: "POST", body: JSON.stringify(request) }),
  generateComposition: (request) =>
    http("/generate/composition", { method: "POST", body: JSON.stringify(request) }),

  // v1.5: photo avatar upload + universal builder
  createPhotoAvatar: (formData) =>
    fetch("/api/heygen/photo-avatar/create", { method: "POST", body: formData })
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail || "Photo avatar creation failed");
        return r.json();
      }),
  buildScript: (request) =>
    http("/prompt/build-script", { method: "POST", body: JSON.stringify(request) }),
  buildComposition: (request) =>
    http("/prompt/build-composition", { method: "POST", body: JSON.stringify(request) }),
  listJobs: () => http("/jobs"),
  getJob: (id) => http(`/jobs/${id}`),
  renameJob: (id, title) =>
    http(`/jobs/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title: title || null }),
    }),
  deleteJob: (id) => http(`/jobs/${id}`, { method: "DELETE" }),
  deleteBatch: (id) => http(`/batches/${id}`, { method: "DELETE" }),
  jobVideoUrl: (id) => `${BASE}/jobs/${id}/video`,

  // v1.6: layout templates (node system) -- namespaced to avoid the
  // existing /templates endpoint (Seedance prompt templates).
  listLayoutTemplates: () => http("/layout-templates"),
  getLayoutTemplate: (id) => http(`/layout-templates/${id}`),
  getLayoutTemplateSlots: (id) => http(`/layout-templates/${id}/slots`),
  saveLayoutTemplate: (tpl) =>
    http("/layout-templates", {
      method: "POST",
      body: JSON.stringify({ template: tpl }),
    }),
  deleteLayoutTemplate: (id) =>
    http(`/layout-templates/${id}`, { method: "DELETE" }),
  renderLayoutTemplate: (id, slotValues, voice_mode, template, title) =>
    http(`/layout-templates/${id}/render`, {
      method: "POST",
      body: JSON.stringify({
        template_id: id,
        slot_values: slotValues,
        voice_mode: voice_mode || null,
        template: template || null,
        title: title || null,
      }),
    }),

  // v1.7: news / RSS pipeline
  listNewsSources: () => http("/news/sources"),
  addNewsSource: (url, name, type = "rss") =>
    http("/news/sources", {
      method: "POST",
      body: JSON.stringify({ url, name: name || null, type }),
    }),
  deleteNewsSource: (id) =>
    http(`/news/sources/${id}`, { method: "DELETE" }),
  toggleNewsSource: (id, enabled) =>
    http(`/news/sources/${id}/toggle`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  seedDefaultNewsSources: () =>
    http("/news/sources/defaults", { method: "POST" }),
  refreshNews: () => http("/news/refresh", { method: "POST" }),
  listNewsItems: () => http("/news/items"),
  newsScript: (req) =>
    http("/news/script", { method: "POST", body: JSON.stringify(req) }),
  newsIllustration: (req) =>
    http("/news/illustration", {
      method: "POST",
      body: JSON.stringify(req),
    }),
};
