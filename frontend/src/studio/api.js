// api.js — thin fetch helpers for the Reef shell. All calls hit the real
// backend on the same origin (FastAPI serves /api/* and Vite dev-proxies).
// Failures are non-fatal: every helper returns a safe default so the UI
// still renders.

const BASE = '/api';

async function _get(path, fallback) {
  try {
    const r = await fetch(BASE + path);
    if (!r.ok) return fallback;
    return await r.json();
  } catch {
    return fallback;
  }
}

export const api = {
  health: () => _get('/health', null),

  // Images stored under assets/images/. Each: { filename, size, modified, url }.
  listImages: () => _get('/images', { images: [] }),
  imageUrl: (filename) => `${BASE}/images/${encodeURIComponent(filename)}`,

  // Jobs: { job_id, status, progress, title, provider, final_video_path,
  //         current_step, duration_s, created_at, ... }
  listJobs: (limit = 50) => _get(`/jobs?limit=${limit}`, []),
  getJob: (id) => _get(`/jobs/${id}`, null),
  jobVideoUrl: (id) => `${BASE}/jobs/${id}/video`,
  renameJob: async (id, title) => {
    try {
      const r = await fetch(`${BASE}/jobs/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title || null }),
      });
      return r.ok ? await r.json() : null;
    } catch { return null; }
  },
  deleteJob: async (id) => {
    try {
      const r = await fetch(`${BASE}/jobs/${id}`, { method: 'DELETE' });
      return r.ok;
    } catch { return false; }
  },
  // Upload a user video (UGC). Registers it as a finished render and returns
  // { ok, job_id, filename, duration_s }. Its duration can drive the master
  // duration of a Studio composition.
  uploadVideo: async (file) => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${BASE}/videos/upload`, { method: 'POST', body: fd });
      return r.ok ? await r.json() : { ok: false, error: `HTTP ${r.status}` };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },

  // Editable caption pack (Telegram Premium tags). { pack:[{id,emoji,label,icon}], is_default }.
  getCaptionPack: () => _get('/caption-pack', null),
  saveCaptionPack: async (pack) => {
    try {
      const r = await fetch(`${BASE}/caption-pack`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pack }) });
      return r.ok ? await r.json() : { ok: false, error: `HTTP ${r.status}` };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },
  resetCaptionPack: async () => {
    try {
      const r = await fetch(`${BASE}/caption-pack`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reset: true }) });
      return r.ok ? await r.json() : { ok: false };
    } catch { return { ok: false }; }
  },
  uploadPackIcon: async (slot, file) => {
    try {
      const fd = new FormData(); fd.append('file', file);
      const r = await fetch(`${BASE}/caption-pack/icon/${encodeURIComponent(slot)}`, { method: 'POST', body: fd });
      return r.ok ? await r.json() : { ok: false, error: `HTTP ${r.status}` };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },

  // Layout templates (the spatial / sequential templates, e.g. tpl_news_reel).
  listLayoutTemplates: () => _get('/layout-templates', []),
  // Render a layout template (saved id, or an inline `template` override for
  // unsaved/Studio-built layouts). slotValues maps slot_name -> {source_kind,…}.
  // Returns { job_id } (render runs in the background — poll /jobs).
  renderLayoutTemplate: async (templateId, slotValues, voiceMode, template, title) => {
    try {
      const r = await fetch(`${BASE}/layout-templates/${encodeURIComponent(templateId)}/render`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          slot_values: slotValues || {},
          voice_mode: voiceMode || null,
          template: template || null,
          title: title || null,
        }),
      });
      return r.ok ? await r.json() : { ok: false, error: `HTTP ${r.status}: ${(await r.text()).slice(0, 160)}` };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },

  // Seedance prompt templates (legacy /api/templates).
  listSeedanceTemplates: () => _get('/templates', []),

  // News.
  listNewsItems: () => _get('/news/items', { items: [] }),

  // v1.9 — Scheduler + marketing plan + image generation.
  listSchedule: () => _get('/schedule', []),
  createScheduledPost: (body) => api.postJson('/schedule', body),
  updateScheduledPost: async (id, patch) => {
    try {
      const r = await fetch(`${BASE}/schedule/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      return r.ok ? await r.json() : null;
    } catch { return null; }
  },
  deleteScheduledPost: async (id) => {
    try {
      const r = await fetch(`${BASE}/schedule/${id}`, { method: 'DELETE' });
      return r.ok;
    } catch { return false; }
  },
  fireScheduledPost: (id) => api.postJson(`/schedule/${id}/fire`, {}),
  marketingPlan: (body) => api.postJson('/marketing/plan', body),
  // v1.10 — import an existing strategy doc (.md/.txt/.docx/.pdf).
  importPlan: async (file, { days = 30, channels = ['x'], language = 'EN' } = {}) => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const qs = new URLSearchParams({
        days: String(days), channels: channels.join(','), language,
      });
      const r = await fetch(`${BASE}/marketing/plan/import?${qs}`, {
        method: 'POST', body: fd,
      });
      if (!r.ok) return { ok: false, error: await r.text() };
      return { ok: true, ...(await r.json()) };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },
  materializePlan: (posts, startDate, mode = 'assisted') =>
    api.postJson('/marketing/plan/materialize', {
      posts, start_date: startDate, mode,
      tz_offset_minutes: new Date().getTimezoneOffset(),
    }),
  testChannel: (channel) => api.postJson('/channels/test', { channel }),
  generateImage: (prompt, n = 1, size = 'portrait_16_9') =>
    api.postJson('/images/generate', { prompt, n, size }),
  importImageUrl: (url) => api.postJson('/images/import-url', { url }),

  // v1.11 — white-label branding.
  getBranding: () => _get('/branding', null),
  setBranding: (fields) => api.postJson('/branding', fields),
  resetBranding: () => api.postJson('/branding', { reset: true }),
  brandLogoUrl: (bust) => `${BASE}/branding/logo${bust ? `?t=${bust}` : ''}`,
  uploadBrandLogo: async (file) => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${BASE}/branding/logo`, { method: 'POST', body: fd });
      if (!r.ok) return { ok: false, error: await r.text() };
      return { ok: true, ...(await r.json()) };
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },

  // Settings / .env editor (local single-user; allowlist enforced server-side).
  listKeys: () => _get('/settings/keys', { keys: [], env_path: '' }),
  setKeys: async (entries) => {
    try {
      const r = await fetch(BASE + '/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries }),
      });
      if (!r.ok) return { ok: false, error: await r.text() };
      return await r.json();
    } catch (e) { return { ok: false, error: String(e?.message || e) }; }
  },

  // HeyGen.
  heygenHealth: () => _get('/heygen/health', { configured: false, reachable: false }),
  listHeygenAvatars: () => _get('/heygen/avatars', { avatars: [], talking_photos: [] }),
  listHeygenVoices: () => _get('/heygen/voices', { voices: [] }),
  createPhotoAvatar: async (file, name = 'Custom deepotus avatar') => {
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('avatar_name', name);
      const r = await fetch(BASE + '/heygen/photo-avatar/create', { method: 'POST', body: fd });
      if (!r.ok) return { ok: false, error: await r.text() };
      const j = await r.json();
      return { ok: true, ...j };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  },

  // POST helpers (return parsed JSON or { error }).
  postJson: async (path, body) => {
    try {
      const r = await fetch(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) return { ok: false, status: r.status, error: await r.text() };
      const j = await r.json().catch(() => ({}));
      return { ok: true, ...j };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  },
};

// React hook that returns the /api/health payload. SHARED singleton poll:
// every useHealth() consumer subscribes to ONE 15s poller instead of each
// running its own. This matters because the HeyGen sub-probe can hang
// 15-25s on flaky networks — N independent pollers (Topbar, Scheduler,
// Inspector, modals…) would pile up dozens of slow requests. One poll, one
// heygen probe, an in-flight guard so a slow probe never stacks.
import { useEffect as _useEffect, useState as _useState } from 'react';

let _healthState = null;
const _healthSubs = new Set();
let _healthTimer = null;
let _healthInFlight = false;

async function _pollHealth() {
  if (_healthInFlight) return;
  _healthInFlight = true;
  try {
    const j = await api.health();
    let merged = j;
    if (j?.heygen_enabled) {
      const hg = await api.heygenHealth().catch(() => null);
      merged = { ...j, heygen_reachable: !!hg?.reachable, heygen_message: hg?.message || '' };
    }
    _healthState = merged;
    _healthSubs.forEach(fn => { try { fn(merged); } catch {} });
  } finally {
    _healthInFlight = false;
  }
}

export function useHealth() {
  const [h, setH] = _useState(_healthState);
  _useEffect(() => {
    _healthSubs.add(setH);
    if (_healthState) setH(_healthState);
    if (!_healthTimer) {
      _pollHealth();
      _healthTimer = setInterval(_pollHealth, 15000);
    }
    function onRefresh() { _pollHealth(); }
    window.addEventListener('deepotus:health-refresh', onRefresh);
    return () => {
      _healthSubs.delete(setH);
      window.removeEventListener('deepotus:health-refresh', onRefresh);
      if (_healthSubs.size === 0 && _healthTimer) { clearInterval(_healthTimer); _healthTimer = null; }
    };
  }, []);
  return h;
}

export function refreshHealth() {
  try { window.dispatchEvent(new Event('deepotus:health-refresh')); } catch {}
}

// ── White-label branding (v1.11). Defaults = deepotus; the buyer rebrands
// from Settings → Branding. Colors are applied as CSS-var overrides on
// <body> (wins over the .deepotus scope in tokens.css).
const BRAND_FALLBACK = {
  app_name: 'DEEPOTUS', app_sub: 'VIDEO',
  tagline_1: 'From the deep,', tagline_2: 'for the deep.',
  brand_color: '#ef4444', accent_color: '#00e5ff',
  has_custom_logo: false, is_default: true,
};

export function applyBrandColors(b) {
  try {
    const s = document.body.style;
    s.setProperty('--brand', b.brand_color);
    s.setProperty('--brand-soft', b.brand_color + '22');
    s.setProperty('--cyan', b.accent_color);
    s.setProperty('--cyan-soft', b.accent_color + '22');
    document.title = `${b.app_name} Video Gen`;
  } catch {}
}

let _brandCache = null;
export function useBranding() {
  const [b, setB] = _useState(_brandCache || BRAND_FALLBACK);
  _useEffect(() => {
    let alive = true;
    async function load() {
      const j = await api.getBranding();
      if (!j) return;
      _brandCache = { ...BRAND_FALLBACK, ...j };
      if (alive) setB(_brandCache);
      applyBrandColors(_brandCache);
    }
    if (!_brandCache) load();
    function onRefresh() { _brandCache = null; load(); }
    window.addEventListener('deepotus:brand-refresh', onRefresh);
    return () => { alive = false; window.removeEventListener('deepotus:brand-refresh', onRefresh); };
  }, []);
  return b;
}

export function refreshBranding() {
  try { window.dispatchEvent(new Event('deepotus:brand-refresh')); } catch {}
}

// Read a URL query param (used by the guide's screenshot pipeline + handy
// for bookmarks): ?view=settings&section=branding, ?view=quick&mode=heygen,
// ?view=scheduler&plan=import.
export function urlParam(name) {
  try { return new URLSearchParams(window.location.search).get(name); } catch { return null; }
}

// Map a /api/schedule row to the Scheduler UI shape. runAt is a local Date;
// time is derived for display. Keep both in sync when patching.
export function postFromRow(r) {
  const runAt = r.run_at ? new Date(r.run_at) : new Date();
  const hh = String(runAt.getHours()).padStart(2, '0');
  const mm = String(runAt.getMinutes()).padStart(2, '0');
  return {
    id: r.id,
    title: r.title || '',
    caption: r.caption || '',
    channels: r.channels || [],
    runAt,
    time: `${hh}:${mm}`,
    status: r.status || 'draft',
    mode: r.mode || 'assisted',
    jobId: r.job_id || null,
    format: r.format || null,
    hook: r.hook || null,
    script_idea: r.script_idea || null,
    image_idea: r.image_idea || null,
    sourceImage: r.source_image || null,
    x_post_id: r.x_post_id || null,
    metrics: r.metrics || null,
    error: r.error || null,
  };
}

// Pretty-print duration in seconds → "00:14" or "01:32".
export function fmtDur(s) {
  if (!s && s !== 0) return '';
  const n = Math.max(0, Math.round(Number(s) || 0));
  const m = Math.floor(n / 60), r = n % 60;
  return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
}

// Pretty-print a created_at ISO string → "6m ago" / "today" / "May 16".
export function fmtAgo(iso) {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (!t) return '';
  const dt = (Date.now() - t) / 1000;
  if (dt < 60) return `${Math.round(dt)}s ago`;
  if (dt < 3600) return `${Math.round(dt/60)}m ago`;
  if (dt < 86400) return `${Math.round(dt/3600)}h ago`;
  if (dt < 86400 * 7) return `${Math.round(dt/86400)}d ago`;
  return new Date(iso).toLocaleString('en', { month: 'short', day: 'numeric' });
}

// Pretty-print bytes → "2.4 MB".
export function fmtSize(b) {
  if (!b && b !== 0) return '';
  const n = Number(b) || 0;
  if (n < 1024) return n + ' B';
  if (n < 1024*1024) return (n/1024).toFixed(1) + ' KB';
  return (n/(1024*1024)).toFixed(1) + ' MB';
}
