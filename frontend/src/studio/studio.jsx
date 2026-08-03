// studio.jsx — The Node Studio (ESM port)
import React, { useState as useStateS, useRef as useRefS, useEffect as useEffectS, useMemo as useMemoS, useCallback as useCallbackS } from 'react';
import { Icon, Button, IconButton, Input, Badge, Toggle, Slider, InspectorSection, Field, Select, Progress } from './atoms.jsx';
import { NODE_TYPES, PALETTE_GROUPS, CAT, PORT, NODE_W, nodeHeight, portAnchor, NodeCard } from './nodes.jsx';
import { api, urlParam } from './api.js';

/* ───────────── Graph compiler: graph → real backend job ─────────────
 * Traces back from the Render node and maps the generator chain to an
 * existing backend endpoint. Supported shapes (the 4 starters):
 *   Image → Seedance → Render                         → /api/generate
 *   Text  → HeyGen   → Render                         → /api/generate/heygen
 *   [Image→Seedance]×N → Concatenate → Render         → sequential template
 *   …→ SpatialCompose → Render (news reel)            → clear message (use News tab)
 * Returns { ok, summary, run } or { ok:false, error }. run() is async and
 * returns the postJson result (with job_id). */
function _src(graph, nodeId, portId) {
  const e = graph.edges.find(e => e.to === nodeId && e.toPort === portId);
  return e ? (graph.nodes.find(n => n.id === e.from) || null) : null;
}
function _fmtDims(fmt) {
  if (fmt === '1:1') return [1080, 1080];
  if (fmt === '16:9') return [1920, 1080];
  if (fmt === '4:5') return [1080, 1350];
  return [1080, 1920];
}
function compileGraph(graph) {
  const render = graph.nodes.find(n => n.type === 'Render');
  if (!render) return { ok: false, error: 'Add a Render node — it is the graph output.' };
  const fmt = render.props?.format || '9:16';
  const title = render.props?.name || 'studio render';
  const seedances = graph.nodes.filter(n => n.type === 'Seedance');
  const heygen = graph.nodes.find(n => n.type === 'HeyGenAvatar');
  const concat = graph.nodes.find(n => n.type === 'Concatenate');
  const spatial = graph.nodes.find(n => n.type === 'SpatialCompose');
  const ugc = graph.nodes.find(n => n.type === 'Upload' && n.props?.jobId);

  // UGC composition: a user-uploaded clip composited with a generated Seedance
  // animation. The UGC slot's real (ffprobe) length drives the MASTER duration
  // via the layout renderer's `audio.master_track`, so the animation is
  // calibrated to the human clip. UGC alone → normalize/re-encode to format.
  if (ugc) {
    const [w, h] = _fmtDims(fmt);
    const ugcMaster = ugc.props?.master !== false;
    const ugcDur = Number(ugc.props?.durationS) || 8;
    const slotValues = { ugc: { source_kind: 'job', job_id: ugc.props.jobId } };
    const regions = [];
    const sd = seedances[0];
    if (sd) {
      const img = _src(graph, sd.id, 'image');
      if (!img || img.type !== 'Image' || !img.props?.filename)
        return { ok: false, error: 'Connect an Image node to the Seedance node (the animation half of the composition).' };
      const txt = _src(graph, sd.id, 'prompt');
      slotValues.anim = { source_kind: 'seedance', seedance: {
        image_filename: img.props.filename,
        custom_prompt: (txt?.props?.value) || 'cinematic motion, deep-sea bioluminescence',
        duration_s: Number(sd.props?.durationS) || 10,
        extend_mode: sd.props?.extendMode || 'loop', voiceover_enabled: false } };
      regions.push({ id: 'r_anim', type: 'video_slot', x: 0, y: 0, width: w, height: Math.round(h / 2),
        z_index: 0, slot_name: 'anim', slot_label: 'Animation (top)', fit: 'cover', audio_volume: 0.0 });
      regions.push({ id: 'r_ugc', type: 'video_slot', x: 0, y: Math.round(h / 2), width: w, height: Math.round(h / 2),
        z_index: 0, slot_name: 'ugc', slot_label: 'Your video (bottom)', fit: 'cover', audio_volume: 1.0,
        length_mode: 'source', tail_pad_s: 0.3 });
    } else {
      regions.push({ id: 'r_ugc', type: 'video_slot', x: 0, y: 0, width: w, height: h,
        z_index: 0, slot_name: 'ugc', slot_label: 'Your video', fit: 'cover', audio_volume: 1.0,
        length_mode: 'source', tail_pad_s: 0.3 });
    }
    const template = { id: 'tpl_studio_ugc', name: 'Studio UGC composition', version: 1,
      canvas: { width: w, height: h, fps: 30, background_color: '#02060d', duration_s: Math.max(2, Math.round(ugcDur)) },
      regions,
      audio: ugcMaster
        ? { master_track: 'from_slot:ugc', tail_pad_s: 0.3, loudness_target_lufs: -14 }
        : { loudness_target_lufs: -14 } };
    return { ok: true,
      summary: sd ? `UGC + animation · master ${ugcMaster ? ugcDur + 's' : 'canvas'}` : `UGC clip · ${ugcDur}s`,
      run: () => api.renderLayoutTemplate('tpl_studio_ugc', slotValues, null, template, title) };
  }

  // News reel / spatial compose: mixes News + Avatar generators — not a
  // one-shot compile. Point the user to the dedicated path.
  if (spatial) {
    return { ok: false, error: 'News-reel graphs mix News + Avatar. Build them from the News tab (Build script → Build illustration → compose), then schedule the render.' };
  }

  // Concatenate montage (timeline starter)
  if (concat) {
    const acts = [];
    for (const port of ['a', 'b', 'c', 'd', 'e', 'f']) {
      const sd = _src(graph, concat.id, port);
      if (sd && sd.type === 'Seedance') acts.push(sd);
    }
    if (acts.length < 2) return { ok: false, error: 'Concatenate needs at least 2 Seedance clips connected.' };
    const [w, h] = _fmtDims(fmt);
    const slotValues = {};
    const regions = acts.map((sd, i) => {
      const img = _src(graph, sd.id, 'image');
      if (!img || img.type !== 'Image' || !img.props?.filename) throw new Error(`Seedance #${i + 1} needs an Image node connected.`);
      const txt = _src(graph, sd.id, 'prompt');
      const slot = 'clip' + i;
      const len = Number(sd.props?.durationS) || 5;
      slotValues[slot] = { source_kind: 'seedance', seedance: {
        image_filename: img.props.filename,
        custom_prompt: (txt?.props?.value) || 'cinematic motion, deep-sea bioluminescence',
        duration_s: len, extend_mode: sd.props?.extendMode || 'loop', voiceover_enabled: false } };
      return { id: 'r' + i, type: 'video_slot', act: i, x: 0, y: 0, width: w, height: h,
        slot_name: slot, length_s: len, length_mode: 'fixed',
        transition: i ? { type: concat.props?.transition || 'crossfade', duration_s: Number(concat.props?.durationS) || 0.4 } : { type: 'cut' } };
    });
    const template = { id: 'tpl_studio_montage', name: 'Studio montage', render_mode: 'sequential',
      canvas: { width: w, height: h, fps: 30, background_color: '#02060d' }, regions };
    return { ok: true, summary: `Montage · ${acts.length} clips`,
      run: () => api.renderLayoutTemplate('tpl_studio_montage', slotValues, null, template, title) };
  }

  // Single Seedance
  if (seedances.length && !heygen) {
    const sd = seedances[0];
    const img = _src(graph, sd.id, 'image');
    if (!img || img.type !== 'Image' || !img.props?.filename) return { ok: false, error: 'Connect an Image node to the Seedance node.' };
    const txt = _src(graph, sd.id, 'prompt');
    return { ok: true, summary: `Seedance · ${img.props.filename}`,
      run: () => api.postJson('/generate', {
        image_filename: img.props.filename,
        custom_prompt: (txt?.props?.value) || 'cinematic push-in, deep-sea bioluminescence',
        style: sd.props?.style || 'cinematic',
        duration_s: Number(sd.props?.durationS) || 10,
        aspect_ratio: fmt, seed: Number(sd.props?.seed) || undefined,
        voiceover_enabled: false }) };
  }

  // HeyGen avatar
  if (heygen && !seedances.length) {
    const txt = _src(graph, heygen.id, 'script');
    const script = (txt?.props?.value) || 'From the deep, the prophecy ascends.';
    return { ok: true, summary: 'HeyGen avatar',
      run: async () => {
        const [a, v] = await Promise.all([api.listHeygenAvatars(), api.listHeygenVoices()]);
        const avatar = (a?.avatars || [])[0];
        const voice = (v?.voices || [])[0];
        if (!avatar || !voice) return { ok: false, error: 'HeyGen avatars/voices unavailable (check key / network in Settings).' };
        return api.postJson('/generate/heygen', {
          avatar_id: avatar.avatar_id, voice_id: voice.voice_id,
          script: script.slice(0, 4900), avatar_type: avatar.avatar_type || 'avatar',
          aspect_ratio: fmt, speed: 1.0 }); } };
  }

  return { ok: false, error: 'Cannot compile this graph. Supported: Image→Seedance→Render, Text→HeyGen→Render, or [Image→Seedance]×N→Concatenate→Render.' };
}

/* Starter pre-wired graphs. */
const STARTER_GRAPHS = {
  newsReel: {
    name: 'oracle_solana_pump.graph',
    nodes: [
      { id: 'n1', type: 'NewsItem',         x: 40,  y: 60  },
      { id: 'n2', type: 'NewsScript',       x: 280, y: 60  },
      { id: 'n3', type: 'HeyGenAvatar',     x: 540, y: 60  },
      { id: 'n4', type: 'NewsIllustration', x: 280, y: 320 },
      { id: 'n5', type: 'BrandStrip',       x: 540, y: 320 },
      { id: 'n6', type: 'SpatialCompose',   x: 820, y: 180 },
      { id: 'n7', type: 'AvatarMaster',     x: 1100,y: 180 },
      { id: 'n8', type: 'Render',           x: 1340,y: 180 },
    ],
    edges: [
      { id:'e1', from:'n1', fromPort:'out',    to:'n2', toPort:'news' },
      { id:'e2', from:'n2', fromPort:'script', to:'n3', toPort:'script' },
      { id:'e3', from:'n1', fromPort:'out',    to:'n4', toPort:'news' },
      { id:'e4', from:'n2', fromPort:'essences', to:'n5', toPort:'data' },
      { id:'e5', from:'n4', fromPort:'out',    to:'n6', toPort:'reel' },
      { id:'e6', from:'n3', fromPort:'out',    to:'n6', toPort:'avatar' },
      { id:'e7', from:'n5', fromPort:'out',    to:'n6', toPort:'brand' },
      { id:'e8', from:'n6', fromPort:'out',    to:'n7', toPort:'in' },
      { id:'e9', from:'n7', fromPort:'out',    to:'n8', toPort:'in' },
    ],
  },
  seedanceSolo: {
    name: 'solo_clip.graph',
    nodes: [
      { id: 'n1', type: 'Image',    x: 80,  y: 200 },
      { id: 'n2', type: 'Seedance', x: 380, y: 200 },
      { id: 'n3', type: 'Render',   x: 680, y: 200 },
    ],
    edges: [
      { id:'e1', from:'n1', fromPort:'out', to:'n2', toPort:'image' },
      { id:'e2', from:'n2', fromPort:'out', to:'n3', toPort:'in' },
    ],
  },
  timeline: {
    name: 'four_clip_montage.graph',
    nodes: [
      { id: 'i1', type: 'Image',    x: 30,  y: 30  },
      { id: 'i2', type: 'Image',    x: 30,  y: 220 },
      { id: 'i3', type: 'Image',    x: 30,  y: 410 },
      { id: 'i4', type: 'Image',    x: 30,  y: 600 },
      { id: 's1', type: 'Seedance', x: 300, y: 30  },
      { id: 's2', type: 'Seedance', x: 300, y: 220 },
      { id: 's3', type: 'Seedance', x: 300, y: 410 },
      { id: 's4', type: 'Seedance', x: 300, y: 600 },
      { id: 'm1', type: 'MusicTrack',x:570, y: 600 },
      { id: 'c1', type: 'Concatenate',x: 620, y: 220 },
      { id: 'r1', type: 'Render',   x: 920, y: 320 },
    ],
    edges: [
      { id:'a', from:'i1', fromPort:'out', to:'s1', toPort:'image' },
      { id:'b', from:'i2', fromPort:'out', to:'s2', toPort:'image' },
      { id:'c', from:'i3', fromPort:'out', to:'s3', toPort:'image' },
      { id:'d', from:'i4', fromPort:'out', to:'s4', toPort:'image' },
      { id:'e', from:'s1', fromPort:'out', to:'c1', toPort:'a' },
      { id:'f', from:'s2', fromPort:'out', to:'c1', toPort:'b' },
      { id:'g', from:'s3', fromPort:'out', to:'c1', toPort:'c' },
      { id:'h', from:'c1', fromPort:'out', to:'r1', toPort:'in' },
    ],
  },
  ugcComposition: {
    name: 'ugc_composition.graph',
    nodes: [
      { id: 'i1', type: 'Image',          x: 30,  y: 60  },
      { id: 's1', type: 'Seedance',       x: 300, y: 60  },
      { id: 'u1', type: 'Upload',         x: 300, y: 360 },
      { id: 'c1', type: 'SpatialCompose', x: 600, y: 190 },
      { id: 'r1', type: 'Render',         x: 880, y: 190 },
    ],
    edges: [
      { id: 'a', from: 'i1', fromPort: 'out', to: 's1', toPort: 'image' },
      { id: 'b', from: 's1', fromPort: 'out', to: 'c1', toPort: 'reel' },
      { id: 'c', from: 'u1', fromPort: 'out', to: 'c1', toPort: 'avatar' },
      { id: 'd', from: 'c1', fromPort: 'out', to: 'r1', toPort: 'in' },
    ],
  },
  avatarPost: {
    name: 'avatar_post.graph',
    nodes: [
      { id: 'n1', type: 'Text',         x: 40, y: 200 },
      { id: 'n2', type: 'HeyGenAvatar', x: 320, y: 200 },
      { id: 'n3', type: 'AvatarMaster', x: 600, y: 200 },
      { id: 'n4', type: 'Render',       x: 860, y: 200 },
    ],
    edges: [
      { id:'a', from:'n1', fromPort:'out', to:'n2', toPort:'script' },
      { id:'b', from:'n2', fromPort:'out', to:'n3', toPort:'in' },
      { id:'c', from:'n3', fromPort:'out', to:'n4', toPort:'in' },
    ],
  },
};

/* ────────────────────── Bezier path helper ────────────────────── */
function edgePath(x1, y1, x2, y2) {
  const dx = Math.max(40, Math.abs(x2 - x1) * 0.5);
  return `M${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

/* ────────────────────── Studio ────────────────────── */
function hydrateGraph(g) {
  return {
    ...g,
    nodes: g.nodes.map(n => ({
      ...n,
      props: { ...(NODE_TYPES[n.type]?.props || {}), ...(n.props || {}) },
    })),
  };
}

function Studio({ variant, onScheduleRender }) {
  // Use a deep copy so multiple Studio instances don't share state.
  // Deep-link ?graph=<starter key> opens that starter (guide screenshots).
  const _g0 = STARTER_GRAPHS[urlParam('graph')] ? urlParam('graph') : 'newsReel';
  const [graph, setGraph] = useStateS(() => hydrateGraph(structuredClone(STARTER_GRAPHS[_g0])));
  const [selected, setSelected] = useStateS(urlParam('node') || 'n6'); // ?node=<id> selects on load
  const [statuses, setStatuses] = useStateS({}); // nodeId -> 'idle'|'queued'|'running'|'succeeded'|'failed'
  const [edgeStatus, setEdgeStatus] = useStateS({}); // edgeId -> 'flowing'|'done'
  const [running, setRunning] = useStateS(false);
  const [previewOpen, setPreviewOpen] = useStateS(false);
  const [lastJob, setLastJob] = useStateS(null); // { id, title } of the produced render
  const [runMsg, setRunMsg] = useStateS('');      // compile errors / run status
  const [zoom, setZoom] = useStateS(0.75);
  const [pan, setPan] = useStateS({ x: 0, y: 0 });
  const canvasRef = useRefS(null);

  // Edge in progress while user drags from a port
  const [pendingEdge, setPendingEdge] = useStateS(null); // {fromNodeId, fromPort, side:'out'|'in', x, y}

  /* ── Node dragging ── */
  const draggingNode = useRefS(null);
  function onNodeMouseDown(e, nodeId) {
    if (e.button !== 0) return;
    e.stopPropagation();
    setSelected(nodeId);
    const n = graph.nodes.find(n => n.id === nodeId);
    draggingNode.current = { id: nodeId, startX: e.clientX, startY: e.clientY, nodeX: n.x, nodeY: n.y };
  }

  /* ── Mouse move (both node drag & pending edge tracking) ── */
  useEffectS(() => {
    function onMove(e) {
      if (draggingNode.current) {
        const d = draggingNode.current;
        const dx = (e.clientX - d.startX) / zoom;
        const dy = (e.clientY - d.startY) / zoom;
        setGraph(g => ({
          ...g,
          nodes: g.nodes.map(n => n.id === d.id ? { ...n, x: d.nodeX + dx, y: d.nodeY + dy } : n),
        }));
      }
      if (pendingEdge && canvasRef.current) {
        const r = canvasRef.current.getBoundingClientRect();
        const x = (e.clientX - r.left - pan.x) / zoom;
        const y = (e.clientY - r.top - pan.y) / zoom;
        setPendingEdge(pe => pe ? { ...pe, x, y } : pe);
      }
    }
    function onUp() {
      draggingNode.current = null;
      setPendingEdge(null);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [zoom, pan, pendingEdge]);

  /* ── Port interactions ── */
  function onPortPress(nodeId, side, port, e) {
    if (!canvasRef.current) return;
    const r = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - r.left - pan.x) / zoom;
    const y = (e.clientY - r.top - pan.y) / zoom;
    setPendingEdge({ fromNodeId: nodeId, fromPort: port, side, x, y });
  }
  function onPortRelease(nodeId, side, port) {
    if (!pendingEdge) return;
    if (pendingEdge.fromNodeId === nodeId) return;
    if (pendingEdge.side === side) return; // must connect in→out or out→in
    // normalize so source is 'out' and target is 'in'
    let from, fromP, to, toP;
    if (pendingEdge.side === 'out') {
      from = pendingEdge.fromNodeId; fromP = pendingEdge.fromPort;
      to = nodeId; toP = port;
    } else {
      from = nodeId; fromP = port;
      to = pendingEdge.fromNodeId; toP = pendingEdge.fromPort;
    }
    // Type compatibility: allow av→video, av→audio
    const t1 = fromP.type, t2 = toP.type;
    const ok = (t1 === t2) || (t1 === 'av' && (t2 === 'video' || t2 === 'audio'));
    if (!ok) {
      setPendingEdge(null);
      return;
    }
    setGraph(g => ({
      ...g,
      edges: [...g.edges.filter(e => !(e.to === to && e.toPort === toP.id)), {
        id: 'e' + Math.random().toString(36).slice(2, 6),
        from, fromPort: fromP.id, to, toPort: toP.id,
      }],
    }));
    setPendingEdge(null);
  }

  /* ── Canvas pan (middle/right click drag) and select clear ── */
  const panning = useRefS(null);
  function onCanvasMouseDown(e) {
    if (e.target.closest('[data-node-id]')) return;
    if (e.button === 0) { setSelected(null); return; }
    panning.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }
  useEffectS(() => {
    function m(e) {
      if (!panning.current) return;
      setPan({ x: panning.current.panX + e.clientX - panning.current.x, y: panning.current.panY + e.clientY - panning.current.y });
    }
    function u() { panning.current = null; }
    window.addEventListener('mousemove', m);
    window.addEventListener('mouseup', u);
    return () => { window.removeEventListener('mousemove', m); window.removeEventListener('mouseup', u); };
  }, []);

  // Plain mouse wheel zooms, anchored on the cursor (pan adjusts so the graph
  // point under the pointer stays put). Pan (middle/right-drag) is unchanged.
  function onWheel(e) {
    e.preventDefault();
    const r = canvasRef.current?.getBoundingClientRect();
    if (!r) return;
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const nz = Math.max(0.3, Math.min(1.5, zoom - e.deltaY * 0.0015));
    if (nz === zoom) return;
    setPan(p => ({ x: mx - (mx - p.x) * (nz / zoom), y: my - (my - p.y) * (nz / zoom) }));
    setZoom(nz);
  }

  /* ── New graph + add node by drag-and-drop from the palette ── */
  const idSeq = useRefS(0);
  function newGraph() {
    idSeq.current += 1;
    // Start from a clean canvas with just the Render output anchor; the user
    // drags generator nodes in from the palette and wires them up.
    setGraph(hydrateGraph({
      name: 'untitled.graph',
      nodes: [{ id: 'render' + idSeq.current, type: 'Render', x: 640, y: 240 }],
      edges: [],
    }));
    setStatuses({}); setEdgeStatus({}); setSelected(null);
    setLastJob(null); setRunMsg(''); setPan({ x: 0, y: 0 }); setZoom(0.75);
  }
  function addNode(type, x, y) {
    const spec = NODE_TYPES[type];
    if (!spec) return;
    const id = 'n' + (++idSeq.current) + Math.random().toString(36).slice(2, 5);
    setGraph(g => ({ ...g, nodes: [...g.nodes, { id, type, x, y, props: { ...(spec.props || {}) } }] }));
    setSelected(id);
  }
  function deleteNode(id) {
    setGraph(g => ({
      ...g,
      nodes: g.nodes.filter(n => n.id !== id),
      edges: g.edges.filter(e => e.from !== id && e.to !== id),
    }));
    setSelected(s => (s === id ? null : s));
    setStatuses(s => { const { [id]: _drop, ...rest } = s; return rest; });
  }
  function onCanvasDragOver(e) {
    if ([...e.dataTransfer.types].includes('application/node-type')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    }
  }
  function onCanvasDrop(e) {
    const type = e.dataTransfer.getData('application/node-type');
    if (!type || !canvasRef.current) return;
    e.preventDefault();
    const r = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - r.left - pan.x) / zoom;
    const y = (e.clientY - r.top - pan.y) / zoom;
    addNode(type, x - NODE_W / 2, y - 20);
  }

  /* ── Run: compile the graph → real backend job, track it, store result ── */
  async function runGraph() {
    if (running) return;
    setRunMsg('');
    let compiled;
    try { compiled = compileGraph(graph); }
    catch (e) { setRunMsg(String(e.message || e)); return; }
    if (!compiled.ok) { setRunMsg(compiled.error); return; }

    const renderNode = graph.nodes.find(n => n.type === 'Render');
    setRunning(true);
    setLastJob(null);
    // Upstream nodes are "compiled" → succeeded; the Render node tracks the
    // real backend job until it finishes.
    const order = topoSort(graph);
    setStatuses(Object.fromEntries(order.map(id => [id, id === renderNode?.id ? 'running' : 'succeeded'])));
    setEdgeStatus(Object.fromEntries(graph.edges.map(e => [e.id, 'done'])));
    setRunMsg(`Queued: ${compiled.summary}. Generating…`);

    try {
      const before = new Set(((await api.listJobs(20)) || []).map(j => j.job_id));
      const res = await compiled.run();
      if (res && res.ok === false) throw new Error(res.error || 'generation failed');

      // Poll for the freshly-created job and follow it to completion.
      let jobId = (res && res.job_id && res.job_id !== 'pending') ? res.job_id : null;
      let tries = 0, finalJob = null;
      while (tries++ < 140) {
        await new Promise(r => setTimeout(r, 2500));
        const list = (await api.listJobs(20)) || [];
        if (!jobId) {
          const fresh = list.find(j => !before.has(j.job_id));
          if (fresh) jobId = fresh.job_id;
        }
        const j = jobId ? list.find(x => x.job_id === jobId) : null;
        if (j) {
          setStatuses(s => ({ ...s, [renderNode.id]: j.status === 'done' ? 'succeeded' : j.status === 'failed' ? 'failed' : 'running' }));
          if (j.status === 'done' && j.final_video_path) { finalJob = j; break; }
          if (j.status === 'failed') { setRunMsg('Render failed: ' + String(j.error || '').slice(0, 140)); break; }
        }
      }
      if (finalJob) {
        setLastJob({ id: finalJob.job_id, title: finalJob.title || compiled.summary });
        setRunMsg('Done. Open Preview to watch it, or schedule it from the Render node.');
        setPreviewOpen(true);
      } else if (!runMsg.startsWith('Render failed')) {
        setRunMsg('Still rendering in the background — check the Job Dock.');
      }
    } catch (e) {
      setStatuses(s => ({ ...s, [renderNode.id]: 'failed' }));
      setRunMsg('Run failed: ' + String(e.message || e).slice(0, 160));
    } finally {
      setRunning(false);
    }
  }

  const selectedNode = graph.nodes.find(n => n.id === selected);

  /* ── Inspector content (graph or node) ── */

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '260px 1fr 340px',
      height: '100%', minHeight: 0,
      background: 'var(--bg-base)',
    }}>
      <NodePalette variant={variant} onPickStarter={(key) => {
        setGraph(hydrateGraph(structuredClone(STARTER_GRAPHS[key])));
        setStatuses({}); setEdgeStatus({}); setSelected(null);
      }} />

      <div style={{ position: 'relative', overflow: 'hidden', borderLeft: '1px solid var(--stroke)', borderRight: '1px solid var(--stroke)' }}>
        {/* Topbar */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, zIndex: 5,
          height: 48, padding: '0 16px',
          background: 'linear-gradient(180deg, #0a1422ee 0%, #0a142299 100%)',
          backdropFilter: 'blur(8px)',
          borderBottom: '1px solid var(--stroke)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <Icon name="flow" size={16} style={{ color: 'var(--violet)' }} />
          <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--ink-strong)', fontSize: 12.5 }}>{graph.name}</span>
          <Badge tone="amber">unsaved</Badge>
          <div style={{ flex: 1 }} />
          <Button variant="outline" size="sm" icon="plus" onClick={newGraph} title="Start a new node graph">New</Button>
          <Select value="9:16" onChange={() => {}} options={['9:16','1:1','16:9','4:5']} style={{ width: 90 }} />
          <Button variant="outline" size="sm" icon="preview" onClick={() => setPreviewOpen(true)}>Preview</Button>
          <Button variant="primary" size="sm" icon="play" glow onClick={runGraph} disabled={running}>
            {running ? 'Running…' : 'Run'}
          </Button>
          <Button variant="ghost" size="sm" icon="download">Export</Button>
        </div>

        {/* Run status banner */}
        {runMsg && (
          <div style={{
            position: 'absolute', top: 56, left: 16, right: 16, zIndex: 5,
            padding: '8px 12px', borderRadius: 'var(--r-sm)',
            background: runMsg.startsWith('Run failed') || runMsg.startsWith('Render failed') || runMsg.includes('Cannot') || runMsg.includes('needs') || runMsg.includes('Connect') || runMsg.includes('mix News')
              ? 'var(--red-soft)' : runMsg.startsWith('Done') ? 'var(--green-soft)' : 'var(--bg-panel-2)',
            border: `1px solid ${runMsg.startsWith('Run failed') || runMsg.startsWith('Render failed') || runMsg.includes('Cannot') || runMsg.includes('needs') || runMsg.includes('Connect') || runMsg.includes('mix News') ? 'var(--red)' : runMsg.startsWith('Done') ? 'var(--green)' : 'var(--stroke-strong)'}`,
            fontSize: 11.5, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 8,
            boxShadow: 'var(--shadow-1)',
          }}>
            <Icon name={running ? 'sparkle' : runMsg.startsWith('Done') ? 'check' : 'warn'} size={13}
              style={{ color: running ? 'var(--cyan)' : runMsg.startsWith('Done') ? 'var(--green)' : 'var(--amber)' }} />
            <span style={{ flex: 1 }}>{runMsg}</span>
            <IconButton name="close" size={20} iconSize={10} onClick={() => setRunMsg('')} />
          </div>
        )}

        {/* Canvas viewport */}
        <div
          ref={canvasRef}
          onMouseDown={onCanvasMouseDown}
          onWheel={onWheel}
          onDragOver={onCanvasDragOver}
          onDrop={onCanvasDrop}
          style={{
            position: 'absolute', inset: 0, top: 48,
            backgroundColor: '#02060d',
            backgroundImage: variant === 'reef'
              ? `radial-gradient(circle at 20% 20%, #0d2a4044 0%, transparent 60%), radial-gradient(circle at 80% 80%, #2a0d4044 0%, transparent 55%), radial-gradient(circle at center, var(--stroke) 1px, transparent 1.5px)`
              : `radial-gradient(circle at center, var(--stroke) 1px, transparent 1.5px)`,
            backgroundSize: variant === 'reef' ? '100% 100%, 100% 100%, 28px 28px' : '24px 24px',
            cursor: panning.current ? 'grabbing' : 'default',
            overflow: 'hidden',
          }}
        >
          {/* Inner pan/zoom layer */}
          <div style={{
            position: 'absolute', inset: 0,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}>
            {/* Edges SVG */}
            <svg style={{ position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none', width: '4000px', height: '3000px' }}>
              <defs>
                <marker id={`arr-${variant}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-soft)" />
                </marker>
              </defs>
              {graph.edges.map(e => {
                const a = graph.nodes.find(n => n.id === e.from);
                const b = graph.nodes.find(n => n.id === e.to);
                if (!a || !b) return null;
                const A = portAnchor(a.type, 'out', e.fromPort, variant);
                const B = portAnchor(b.type, 'in', e.toPort, variant);
                const x1 = a.x + A.x, y1 = a.y + A.y;
                const x2 = b.x + B.x, y2 = b.y + B.y;
                const fromSpec = NODE_TYPES[a.type].outPorts.find(p => p.id === e.fromPort);
                const portColor = fromSpec ? PORT[fromSpec.type].color : 'var(--ink-soft)';
                const st = edgeStatus[e.id];
                const dim = !st && running;
                return (
                  <g key={e.id}>
                    <path d={edgePath(x1, y1, x2, y2)} stroke={portColor} strokeWidth={2}
                      fill="none" opacity={dim ? 0.18 : (st === 'done' ? 0.55 : 0.85)}
                      strokeDasharray={st === 'flowing' ? '6 4' : 'none'}
                      className={st === 'flowing' ? 'edge-running' : ''}
                      style={{ filter: st === 'flowing' ? `drop-shadow(0 0 6px ${portColor})` : 'none', transition: 'opacity 200ms' }}
                    />
                  </g>
                );
              })}
              {/* Pending edge */}
              {pendingEdge && (() => {
                const node = graph.nodes.find(n => n.id === pendingEdge.fromNodeId);
                if (!node) return null;
                const a = portAnchor(node.type, pendingEdge.side, pendingEdge.fromPort.id, variant);
                const sx = node.x + a.x, sy = node.y + a.y;
                const color = PORT[pendingEdge.fromPort.type].color;
                const d = pendingEdge.side === 'out'
                  ? edgePath(sx, sy, pendingEdge.x, pendingEdge.y)
                  : edgePath(pendingEdge.x, pendingEdge.y, sx, sy);
                return <path d={d} stroke={color} strokeWidth={2} fill="none" strokeDasharray="4 4" opacity={0.9} style={{ filter: `drop-shadow(0 0 8px ${color})` }} />;
              })()}
            </svg>

            {/* Nodes */}
            {graph.nodes.map(n => (
              <NodeCard
                key={n.id}
                node={n}
                variant={variant}
                selected={selected === n.id}
                status={statuses[n.id]}
                onMouseDown={(e) => onNodeMouseDown(e, n.id)}
                onClick={() => setSelected(n.id)}
                onPortPress={onPortPress}
                onPortRelease={onPortRelease}
                onDelete={() => deleteNode(n.id)}
              />
            ))}
          </div>

          {/* Minimap */}
          <Minimap graph={graph} statuses={statuses} variant={variant} />

          {/* Zoom HUD */}
          <div style={{
            position: 'absolute', left: 12, bottom: 12, zIndex: 4,
            display: 'flex', gap: 4, background: 'var(--bg-panel)', border: '1px solid var(--stroke)',
            borderRadius: 'var(--r-sm)', padding: 2,
          }}>
            <IconButton name="minus" size={26} onClick={() => setZoom(z => Math.max(0.3, z - 0.1))} />
            <div style={{ minWidth: 50, padding: '0 6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--ink-soft)' }}>{Math.round(zoom * 100)}%</div>
            <IconButton name="plus" size={26} onClick={() => setZoom(z => Math.min(1.5, z + 0.1))} />
          </div>

          {/* Hint */}
          <div style={{
            position: 'absolute', right: 12, top: 60, zIndex: 4,
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 10px', background: 'var(--bg-panel)', border: '1px solid var(--stroke)',
            borderRadius: 'var(--r-sm)', fontSize: 11, color: 'var(--ink-soft)',
          }}>
            <kbd style={kbdStyle}>/</kbd> nodes
            <kbd style={kbdStyle}>⌘K</kbd> palette
            <kbd style={kbdStyle}>⌘⏎</kbd> run
          </div>

          {/* Preview drawer */}
          {previewOpen && <PreviewDrawer onClose={() => setPreviewOpen(false)} graph={graph} lastJob={lastJob} />}
        </div>
      </div>

      <Inspector node={selectedNode} graph={graph} lastJob={lastJob} onUpdate={(props) => {
        setGraph(g => ({ ...g, nodes: g.nodes.map(n => n.id === selected ? { ...n, props: { ...n.props, ...props } } : n) }));
      }} onRenameGraph={(name) => setGraph(g => ({ ...g, name }))} variant={variant} onScheduleRender={onScheduleRender} />
    </div>
  );
}

const kbdStyle = {
  display: 'inline-block', padding: '1px 5px', borderRadius: 4,
  background: 'var(--bg-base)', border: '1px solid var(--stroke)',
  fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-strong)',
};

/* Topo sort (simple). */
function topoSort(graph) {
  const incoming = Object.fromEntries(graph.nodes.map(n => [n.id, 0]));
  graph.edges.forEach(e => { incoming[e.to] = (incoming[e.to] || 0) + 1; });
  const queue = graph.nodes.filter(n => !incoming[n.id]).map(n => n.id);
  const order = [];
  while (queue.length) {
    const id = queue.shift(); order.push(id);
    graph.edges.filter(e => e.from === id).forEach(e => {
      incoming[e.to]--;
      if (incoming[e.to] === 0) queue.push(e.to);
    });
  }
  // include anything left (cycles), shouldn't happen here
  graph.nodes.forEach(n => { if (!order.includes(n.id)) order.push(n.id); });
  return order;
}

/* ────────────────────── NodePalette ────────────────────── */
function NodePalette({ variant, onPickStarter }) {
  const [q, setQ] = useStateS('');
  return (
    <div style={{ background: 'var(--bg-panel)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: '12px 14px 8px', borderBottom: '1px solid var(--stroke)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <span className="upper">Nodes</span>
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-muted)' }}>press /</span>
        </div>
        <Input icon="search" placeholder="Search…" value={q} onChange={setQ} />
      </div>

      <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '8px 0 24px' }}>
        {/* Starters */}
        <div style={{ padding: '0 14px 12px' }}>
          <div className="upper" style={{ marginBottom: 6 }}>Starter graphs</div>
          {[
            { k: 'seedanceSolo', l: 'Seedance solo',   d: 'image → clip → render' },
            { k: 'avatarPost',   l: 'Avatar post',     d: 'text → HeyGen → render' },
            { k: 'ugcComposition', l: 'UGC + animation', d: 'your clip drives the master duration' },
            { k: 'newsReel',     l: 'News reel post',  d: 'RSS → script → reel + brand' },
            { k: 'timeline',     l: 'Timeline montage', d: '4 clips → xfade → render' },
          ].map(s => (
            <button key={s.k} onClick={() => onPickStarter(s.k)} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              width: '100%', padding: '8px 8px', textAlign: 'left',
              background: 'transparent', border: 0, cursor: 'pointer',
              borderRadius: 'var(--r-sm)', color: 'var(--ink)',
              transition: 'background var(--dur-1) var(--ease)',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-panel-2)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <span style={{
                width: 26, height: 26, borderRadius: 6,
                background: 'var(--cyan-soft)', color: 'var(--cyan)',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              }}><Icon name="flow" size={13} /></span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: 'var(--ink-strong)' }}>{s.l}</div>
                <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{s.d}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Categories */}
        {PALETTE_GROUPS.map(g => {
          const types = g.types.filter(t => !q || t.toLowerCase().includes(q.toLowerCase()) || NODE_TYPES[t].title.toLowerCase().includes(q.toLowerCase()));
          if (!types.length) return null;
          const cat = CAT[g.cat];
          return (
            <div key={g.cat} style={{ padding: '6px 14px 10px' }}>
              <div className="upper" style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, color: cat.color }}>
                <Icon name={cat.icon} size={11} /> {cat.label}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {types.map(t => {
                  const spec = NODE_TYPES[t];
                  return (
                    <div key={t}
                      draggable
                      onDragStart={e => {
                        e.dataTransfer.setData('application/node-type', t);
                        e.dataTransfer.effectAllowed = 'copy';
                      }}
                      title={`Drag onto the canvas to add a ${spec.title} node`}
                      style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '5px 8px', borderRadius: 'var(--r-sm)',
                      cursor: 'grab', color: 'var(--ink)',
                      transition: 'background var(--dur-1) var(--ease)',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-panel-2)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: 2, background: cat.color, boxShadow: `0 0 6px ${cat.color}` }} />
                      <span style={{ flex: 1, fontSize: 12 }}>{spec.title}</span>
                      <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9.5, color: 'var(--ink-muted)' }}>
                        {spec.inPorts.length}→{spec.outPorts.length}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ────────────────────── Inspector ────────────────────── */
function Inspector({ node, graph, lastJob, onUpdate, onRenameGraph, variant, onScheduleRender }) {
  return (
    <div style={{ background: 'var(--bg-panel)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {node ? (
        <>
          <InspectorHeader node={node} />
          <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
            <NodeInspector node={node} onUpdate={onUpdate} />
            {node.type === 'Render' && onScheduleRender && (
              <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--stroke)', background: 'linear-gradient(180deg, var(--brand-soft) 0%, transparent 100%)' }}>
                <div style={{ fontSize: 11, color: 'var(--ink-soft)', marginBottom: 8 }}>
                  {lastJob
                    ? 'The produced render will be attached to a scheduled post (tomorrow 09:00 by default; edit before sending).'
                    : 'Run the graph first to produce the render, then schedule it. You can also schedule now as a caption-only post and attach the render later.'}
                </div>
                <Button variant="primary" size="md" icon="send" glow style={{ width: '100%' }}
                  onClick={() => onScheduleRender({
                    jobId: lastJob?.id || null,
                    filename: (node.props?.name || 'tweet') + '.mp4',
                    title: lastJob?.title || node.props?.name || 'New post',
                    caption: 'Drop from the deep. 🐙' })}
                >
                  {lastJob ? 'Schedule this render' : 'Schedule (no render yet)'}
                </Button>
              </div>
            )}
            <InspectorSection label="Connections">
              <Connections node={node} graph={graph} />
            </InspectorSection>
            <InspectorSection label="Runtime" defaultOpen={false}>
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 11.5 }}>
                <span className="soft">node id</span><span className="mono strong">{node.id}</span>
                <span className="soft">type</span><span className="mono strong">{node.type}</span>
                <span className="soft">duration est.</span><span className="mono strong">{estDuration(node)}</span>
                <span className="soft">cost est.</span><span className="mono strong" style={{ color: 'var(--amber)' }}>{estCost(node)}</span>
              </div>
            </InspectorSection>
          </div>
        </>
      ) : (
        <GraphInspector graph={graph} onRename={onRenameGraph} />
      )}
    </div>
  );
}

function InspectorHeader({ node }) {
  const spec = NODE_TYPES[node.type];
  const cat = CAT[spec.cat];
  return (
    <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 28, height: 28, borderRadius: 7, background: cat.color + '22', color: cat.color, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={cat.icon} size={14} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>{spec.title}</div>
          <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{spec.desc}</div>
        </div>
        <IconButton name="more" />
      </div>
    </div>
  );
}

function GraphInspector({ graph, onRename }) {
  return (
    <>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
        <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Graph</div>
        <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{graph.nodes.length} nodes · {graph.edges.length} edges</div>
      </div>
      <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
        <InspectorSection label="Graph name">
          <Field hint="Drag nodes from the left palette onto the canvas, then wire them up.">
            <Input mono value={graph.name || ''} onChange={v => onRename?.(v)} placeholder="untitled.graph" />
          </Field>
        </InspectorSection>
        <InspectorSection label="Output">
          <Field label="Format"><Select value="9:16" onChange={()=>{}} options={['9:16','1:1','16:9','4:5']} /></Field>
          <Field label="FPS"><Select value={30} onChange={()=>{}} options={[24,30,48,60]} /></Field>
          <Field label="Render name"><Input mono value="tweet_2026-05-20_oracle" onChange={()=>{}} /></Field>
        </InspectorSection>
        <InspectorSection label="Audio master">
          <Field><Toggle checked onChange={()=>{}} label="Avatar node is duration master" /></Field>
          <Field><Slider label="Tail pad" value={0.4} min={0} max={2} step={0.1} unit="s" onChange={()=>{}} /></Field>
          <Field><Slider label="Loudness target" value={-14} min={-23} max={-9} step={0.5} unit=" LUFS" onChange={()=>{}} /></Field>
        </InspectorSection>
        <InspectorSection label="Estimated">
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 12px', fontSize: 12 }}>
            <span className="soft">Duration</span><span className="mono strong">00:17.6</span>
            <span className="soft">Cost</span><span className="mono strong" style={{ color: 'var(--amber)' }}>$0.43</span>
            <span className="soft">Providers</span><span className="mono strong">fal.ai · HeyGen · ElevenLabs</span>
          </div>
        </InspectorSection>
      </div>
    </>
  );
}

function ImageNodeInspector({ p, set }) {
  const [images, setImages] = useStateS([]);
  useEffectS(() => {
    let alive = true;
    api.listImages().then(r => { if (alive) setImages((r?.images || []).map(im => im.filename)); });
    return () => { alive = false; };
  }, []);
  const known = images.includes(p.filename);
  return (
    <InspectorSection label="Image">
      <Field label="From library">
        {images.length > 0 ? (
          <Select value={known ? p.filename : ''} onChange={v => v && set('filename', v)}
            options={[{ value: '', label: known ? p.filename : '— pick an image —' }, ...images.map(f => ({ value: f, label: f }))]} />
        ) : (
          <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>No images yet — create or upload one in the Library tab.</div>
        )}
      </Field>
      <Field label="Filename"><Input mono value={p.filename} onChange={v => set('filename', v)} /></Field>
      <div style={{ marginTop: 4, aspectRatio: '9 / 16', background: '#02060d', border: `1px solid ${known ? 'var(--amber)' : 'var(--stroke)'}`, borderRadius: 8, position: 'relative', overflow: 'hidden' }}>
        <img src={api.imageUrl(p.filename || '')} alt={p.filename}
          onError={e => { e.currentTarget.style.opacity = 0; }}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        {!known && <div style={{ position: 'absolute', top: 6, left: 8, fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--amber)' }}>not in library</div>}
      </div>
    </InspectorSection>
  );
}

// SpatialCompose: pick a REAL layout template and preview its actual regions.
// The dropdown is populated from /api/layout-templates and the preview redraws
// from the chosen template's regions, so the layout changes with the choice.
function _spatialRegionColor(r) {
  if (r.type === 'video_slot') return (r.slot_name === 'avatar' || /avatar|heygen/i.test(r.slot_label || r.slot_name || '')) ? 'var(--violet)' : 'var(--cyan)';
  if (r.type === 'brand_strip') return 'var(--amber)';
  if (r.type === 'separator')   return 'var(--green)';
  if (r.type === 'image_slot')  return 'var(--amber)';
  return 'var(--ink-soft)';
}
function SpatialComposeInspector({ p, set }) {
  const [tpls, setTpls] = useStateS([]);
  useEffectS(() => {
    let alive = true;
    api.listLayoutTemplates().then(res => {
      if (!alive) return;
      setTpls(Array.isArray(res) ? res : (res?.templates || []));
    });
    return () => { alive = false; };
  }, []);
  const selected = tpls.find(t => t.id === p.templateId);
  const cw = selected?.canvas?.width || 1080;
  const ch = selected?.canvas?.height || 1920;
  const regions = selected?.regions || [];
  return (
    <InspectorSection label="Layout">
      <Field label="Template">
        <Select value={p.templateId} onChange={v => set('templateId', v)}
          options={tpls.length
            ? tpls.map(t => ({ value: t.id, label: t.name || t.id }))
            : [{ value: p.templateId, label: p.templateId || '— loading… —' }]} />
      </Field>
      <div style={{ margin: '6px 0 8px', background: selected?.canvas?.background_color || '#02060d',
        border: '1px solid var(--stroke)', borderRadius: 8, aspectRatio: `${cw} / ${ch}`, position: 'relative', overflow: 'hidden' }}>
        {regions.length ? regions.map((r, i) => {
          const c = _spatialRegionColor(r);
          return (
            <div key={r.id || i} style={{ position: 'absolute',
              left: `${(r.x / cw) * 100}%`, top: `${(r.y / ch) * 100}%`,
              width: `${(r.width / cw) * 100}%`, height: `${(r.height / ch) * 100}%`,
              background: `${c}22`, border: `1px solid ${c}`, borderRadius: 4, boxSizing: 'border-box' }}>
              <div style={{ position: 'absolute', top: 3, left: 5, fontFamily: 'var(--f-mono)', fontSize: 9, color: c, whiteSpace: 'nowrap', overflow: 'hidden' }}>{r.slot_name || r.type}</div>
            </div>
          );
        }) : (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: 'var(--ink-muted)' }}>
            {tpls.length ? 'pick a template above' : 'loading templates…'}
          </div>
        )}
      </div>
      {selected?.description && (
        <div style={{ fontSize: 10.5, color: 'var(--ink-soft)', marginBottom: 8, lineHeight: 1.4 }}>{selected.description}</div>
      )}
      <Field><Toggle checked={p.useAsMaster} onChange={v => set('useAsMaster', v)} label="Avatar slot is duration master" /></Field>
      <Field><Slider label="Tail pad" value={p.tailPadS} min={0} max={2} step={0.1} unit="s" onChange={v => set('tailPadS', v)} /></Field>
    </InspectorSection>
  );
}

// ExistingRender: pick a finished render from the Library; the node then shows
// its clip thumbnail.
function ExistingRenderInspector({ p, set }) {
  const [jobs, setJobs] = useStateS([]);
  useEffectS(() => {
    let alive = true;
    api.listJobs(60).then(arr => { if (alive) setJobs((Array.isArray(arr) ? arr : []).filter(j => j.status === 'done' && j.final_video_path)); });
    return () => { alive = false; };
  }, []);
  const known = jobs.some(j => j.job_id === p.jobId);
  return (
    <InspectorSection label="Existing render">
      <Field label="From library">
        {jobs.length ? (
          <Select value={known ? p.jobId : ''} onChange={v => v && set('jobId', v)}
            options={[{ value: '', label: known ? p.jobId : '— pick a render —' },
              ...jobs.map(j => ({ value: j.job_id, label: `${j.title || j.provider || 'render'} · ${(j.job_id || '').slice(0, 6)}` }))]} />
        ) : (
          <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>No finished renders yet — produce one first.</div>
        )}
      </Field>
      {p.jobId && (
        <div style={{ marginTop: 4, maxHeight: 280, background: '#000', border: '1px solid var(--stroke)', borderRadius: 8, overflow: 'hidden' }}>
          <video src={api.jobVideoUrl(p.jobId)} controls preload="metadata"
            onError={e => { e.currentTarget.style.opacity = 0.2; }}
            style={{ width: '100%', maxHeight: 280, display: 'block' }} />
        </div>
      )}
    </InspectorSection>
  );
}

// UGC video upload node: upload your own clip; it becomes a reusable render
// and (when "Duration master" is on) drives the composition's final length.
function UploadInspector({ p, set }) {
  const fileRef = useRefS(null);
  const [busy, setBusy] = useStateS(false);
  const [msg, setMsg] = useStateS('');
  async function onFile(f) {
    if (!f) return;
    setBusy(true); setMsg('Uploading + reading duration…');
    const r = await api.uploadVideo(f);
    setBusy(false);
    if (r?.ok) {
      set('jobId', r.job_id);
      set('filename', r.filename);
      set('durationS', Math.round((r.duration_s || 0) * 10) / 10);
      setMsg(`Uploaded · ${r.duration_s}s`);
      setTimeout(() => setMsg(''), 4000);
    } else {
      setMsg('Upload failed: ' + String(r?.error || '').slice(0, 120));
    }
  }
  return (
    <InspectorSection label="UGC video">
      <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }}
        onChange={e => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      <Field hint="Your own clip — a phone selfie, a screen-grab, anything. It becomes a reusable render in your Library.">
        <Button variant={p.jobId ? 'outline' : 'primary'} size="sm" icon="upload" glow={!p.jobId}
          onClick={() => fileRef.current?.click()} disabled={busy} style={{ width: '100%' }}>
          {busy ? 'Uploading…' : p.jobId ? 'Replace clip' : 'Upload your video'}
        </Button>
      </Field>
      {msg && <div style={{ fontSize: 10.5, color: msg.startsWith('Upload failed') ? 'var(--red)' : 'var(--green)', marginTop: -2, marginBottom: 6 }}>{msg}</div>}
      {p.jobId && (
        <>
          <div style={{ aspectRatio: '9 / 16', maxHeight: 240, background: '#000', border: '1px solid var(--stroke)', borderRadius: 8, overflow: 'hidden', marginBottom: 8 }}>
            <video src={api.jobVideoUrl(p.jobId)} controls preload="metadata"
              onError={e => { e.currentTarget.style.opacity = 0.2; }}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 10px', fontSize: 11.5, marginBottom: 8 }}>
            <span className="soft">clip</span><span className="mono strong" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.filename}</span>
            <span className="soft">duration</span><span className="mono strong">{p.durationS}s</span>
          </div>
        </>
      )}
      <Field hint={p.master
        ? 'ON: this clip sets the MASTER duration — the final composition matches its real length, and generated animations are calibrated around it.'
        : 'OFF: the composition uses the canvas/own duration instead.'}>
        <Toggle checked={!!p.master} onChange={v => set('master', v)} label="⏱ Duration master" />
      </Field>
    </InspectorSection>
  );
}

function NodeInspector({ node, onUpdate }) {
  const p = node.props || {};
  const set = (k, v) => onUpdate({ [k]: v });

  if (node.type === 'Seedance') return (
    <InspectorSection label="Generator">
      <Field label="Style"><Select value={p.style} onChange={v=>set('style',v)} options={['cinematic','documentary','glitch','dream','noir','deep-sea']} /></Field>
      <Field label="Duration"><Slider value={p.durationS} min={5} max={30} step={5} unit="s" onChange={v=>set('durationS',v)} /></Field>
      <Field label="Aspect"><Select value={p.aspect} onChange={v=>set('aspect',v)} options={['9:16','1:1','16:9','4:5']} /></Field>
      <Field label="Seed"><Input mono value={p.seed} onChange={v=>set('seed',Number(v)||0)} /></Field>
      <Field label="Extend mode"><Select value={p.extendMode} onChange={v=>set('extendMode',v)} options={['loop','hold','crossfade']} /></Field>
    </InspectorSection>
  );

  if (node.type === 'HeyGenAvatar') return (
    <InspectorSection label="Avatar">
      <Field label="Avatar"><Select value={p.avatar} onChange={v=>set('avatar',v)} options={['Asha · prophetess','Mara · oracle','Kai · seer','Yuna · whisper']} /></Field>
      <Field label="Voice"><Select value={p.voice} onChange={v=>set('voice',v)} options={['Asha · EN','Mara · EN-low','Kai · FR','Yuna · EN-soft']} /></Field>
      <Field label="Speed"><Slider value={p.speedX*100|0} min={70} max={140} step={5} unit="%" onChange={v=>set('speedX',v/100)} /></Field>
    </InspectorSection>
  );

  if (node.type === 'SpatialCompose') return <SpatialComposeInspector p={p} set={set} />;

  if (node.type === 'Trim') return (
    <InspectorSection label="Trim">
      <Field><Slider label="Start" value={p.startS} min={0} max={30} step={0.1} unit="s" onChange={v=>set('startS',v)} /></Field>
      <Field><Slider label="End"   value={p.endS}   min={0} max={30} step={0.1} unit="s" onChange={v=>set('endS',v)} /></Field>
      <Field label="Length mode"><Select value={p.lengthMode} onChange={v=>set('lengthMode',v)} options={['source','fixed']} /></Field>
    </InspectorSection>
  );

  if (node.type === 'Concatenate') return (
    <InspectorSection label="Concatenate">
      <Field label="Transition"><Select value={p.transition} onChange={v=>set('transition',v)} options={['crossfade','cut','fadeblack','glitch','slide','flash']} /></Field>
      <Field><Slider label="Transition duration" value={p.durationS} min={0} max={2} step={0.05} unit="s" onChange={v=>set('durationS',v)} /></Field>
    </InspectorSection>
  );

  if (node.type === 'AvatarMaster') return (
    <InspectorSection label="Master">
      <Field hint="Final render duration ≥ this clip's real duration + tail pad."><Slider label="Tail pad" value={p.tailPadS} min={0} max={2} step={0.1} unit="s" onChange={v=>set('tailPadS',v)} /></Field>
      <Field><Slider label="Fade out" value={p.fadeOutS} min={0} max={2} step={0.1} unit="s" onChange={v=>set('fadeOutS',v)} /></Field>
    </InspectorSection>
  );

  if (node.type === 'Render') return (
    <InspectorSection label="Render">
      <Field label="Format"><Select value={p.format} onChange={v=>set('format',v)} options={['9:16','1:1','16:9','4:5']} /></Field>
      <Field label="FPS"><Select value={p.fps} onChange={v=>set('fps',v)} options={[24,30,48,60]} /></Field>
      <Field><Slider label="CRF" value={p.crf} min={14} max={28} step={1} onChange={v=>set('crf',v)} /></Field>
      <Field label="Render name"><Input mono value={p.name} onChange={v=>set('name',v)} /></Field>
      <Field label="Voice mode"><Select value={p.voiceMode} onChange={v=>set('voiceMode',v)} options={['passthrough','duck-bgm','mute']} /></Field>
    </InspectorSection>
  );

  if (node.type === 'Image') return <ImageNodeInspector p={p} set={set} />;

  if (node.type === 'ExistingRender') return <ExistingRenderInspector p={p} set={set} />;

  if (node.type === 'Upload') return <UploadInspector p={p} set={set} />;

  if (node.type === 'Text') return (
    <InspectorSection label="Text">
      <Field>
        <textarea value={p.value} onChange={e => set('value', e.target.value)} rows={5} style={{
          width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)',
          borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5,
          resize: 'vertical',
        }} />
      </Field>
      <Field hint="Used by HeyGen / Voiceover / Ticker."><div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{(p.value||'').length} characters · ~{Math.round((p.value||'').split(' ').length / 2.5)}s spoken</div></Field>
    </InspectorSection>
  );

  if (node.type === 'NewsItem') return (
    <InspectorSection label="News item">
      <Field label="Title"><Input value={p.title} onChange={v=>set('title',v)} /></Field>
      <Field label="Source"><Input mono value={p.source} onChange={v=>set('source',v)} /></Field>
    </InspectorSection>
  );

  // Default: render every prop as a generic input
  return (
    <InspectorSection label="Properties">
      {Object.entries(p).map(([k,v]) => (
        <Field key={k} label={k}>
          {typeof v === 'boolean'
            ? <Toggle checked={v} onChange={nv=>set(k,nv)} />
            : <Input mono={typeof v === 'number'} value={String(v)} onChange={nv => set(k, typeof v === 'number' ? Number(nv) : nv)} />}
        </Field>
      ))}
    </InspectorSection>
  );
}

function Connections({ node, graph }) {
  const spec = NODE_TYPES[node.type];
  const ins = spec.inPorts.map(p => {
    const e = graph.edges.find(e => e.to === node.id && e.toPort === p.id);
    const from = e && graph.nodes.find(n => n.id === e.from);
    return { p, from };
  });
  const outs = spec.outPorts.map(p => {
    const es = graph.edges.filter(e => e.from === node.id && e.fromPort === p.id);
    const tos = es.map(e => graph.nodes.find(n => n.id === e.to));
    return { p, tos };
  });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {ins.map(({p, from}) => (
        <div key={'i'+p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5 }}>
          <span style={{ width: 9, height: 9, borderRadius: 999, background: PORT[p.type].color }} />
          <span className="soft">in · {p.id}</span>
          <span style={{ flex: 1 }} />
          <span className="mono" style={{ color: from ? 'var(--ink-strong)' : 'var(--ink-muted)' }}>{from ? NODE_TYPES[from.type].title : '—'}</span>
        </div>
      ))}
      {outs.map(({p, tos}) => (
        <div key={'o'+p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5 }}>
          <span style={{ width: 9, height: 9, borderRadius: 999, background: PORT[p.type].color }} />
          <span className="soft">out · {p.id}</span>
          <span style={{ flex: 1 }} />
          <span className="mono" style={{ color: tos.length ? 'var(--ink-strong)' : 'var(--ink-muted)' }}>
            {tos.length ? tos.map(t => NODE_TYPES[t.type].title).join(', ') : '—'}
          </span>
        </div>
      ))}
    </div>
  );
}

function estDuration(node) {
  if (node.type === 'Seedance') return node.props.durationS + 's';
  if (node.type === 'HeyGenAvatar') return '~9s';
  if (node.type === 'Concatenate') return 'sum + xfades';
  if (node.type === 'Render') return '00:17.6';
  return '—';
}
function estCost(node) {
  if (node.type === 'Seedance') return '$0.18';
  if (node.type === 'HeyGenAvatar') return '$0.21';
  if (node.type === 'Voiceover') return '$0.04';
  if (node.type === 'NewsScript') return '$0.01';
  return '—';
}

/* ────────────────────── Minimap ────────────────────── */
function Minimap({ graph, statuses, variant }) {
  const SCALE = 0.05;
  const W = 200, H = 130;
  const xs = graph.nodes.map(n => n.x);
  const ys = graph.nodes.map(n => n.y);
  const minX = Math.min(...xs, 0), minY = Math.min(...ys, 0);
  return (
    <div style={{
      position: 'absolute', right: 12, bottom: 12, zIndex: 4,
      width: W, height: H, padding: 6,
      background: 'var(--bg-panel)cc', backdropFilter: 'blur(4px)',
      border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)',
    }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%' }}>
        {graph.edges.map(e => {
          const a = graph.nodes.find(n => n.id === e.from);
          const b = graph.nodes.find(n => n.id === e.to);
          if (!a || !b) return null;
          return <line key={e.id} x1={(a.x - minX) * SCALE + 4} y1={(a.y - minY) * SCALE + 4} x2={(b.x - minX) * SCALE + 4} y2={(b.y - minY) * SCALE + 4} stroke="var(--stroke-strong)" strokeWidth="1" />;
        })}
        {graph.nodes.map(n => {
          const cat = CAT[NODE_TYPES[n.type].cat];
          const st = statuses[n.id];
          return <rect key={n.id} x={(n.x - minX) * SCALE + 4} y={(n.y - minY) * SCALE + 4} width={NODE_W * SCALE} height={6} fill={cat.color} opacity={st === 'running' ? 1 : 0.7} />;
        })}
      </svg>
    </div>
  );
}

/* ────────────────────── Preview Drawer ──────────────────────
 * After a Run: plays the produced render. Before a Run: shows the graph's
 * source inputs (images, text, existing renders) — what the generation
 * will be built from. */
function PreviewDrawer({ onClose, graph, lastJob }) {
  const sources = (graph?.nodes || []).filter(n => ['Image', 'Text', 'ExistingRender', 'Upload', 'NewsItem'].includes(n.type));
  return (
    <div style={{
      position: 'absolute', right: 0, top: 48, bottom: 0,
      width: 340, zIndex: 6,
      background: 'var(--bg-panel-2)', borderLeft: '1px solid var(--stroke-strong)',
      boxShadow: '-12px 0 32px #0008',
      display: 'flex', flexDirection: 'column',
      animation: 'slidein 320ms var(--ease)',
    }}>
      <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon name="preview" size={16} style={{ color: 'var(--cyan)' }} />
        <span className="display" style={{ fontSize: 14, color: 'var(--ink-strong)' }}>{lastJob ? 'Result' : 'Inputs'}</span>
        {lastJob ? <Badge tone="green" dot>rendered</Badge> : <Badge tone="cyan" dot>{sources.length} sources</Badge>}
        <span style={{ flex: 1 }} />
        <IconButton name="close" onClick={onClose} />
      </div>

      <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 14 }}>
        {lastJob ? (
          <>
            <video src={api.jobVideoUrl(lastJob.id)} controls autoPlay
              style={{ width: '100%', borderRadius: 8, background: '#000', border: '1px solid var(--stroke-strong)' }} />
            <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
              <a href={api.jobVideoUrl(lastJob.id)} download style={{ flex: 1, textDecoration: 'none' }}>
                <Button variant="outline" size="sm" icon="download" style={{ width: '100%' }}>Download</Button>
              </a>
            </div>
            <div style={{ marginTop: 10, fontSize: 11, color: 'var(--ink-soft)' }}>
              The produced render. Schedule it from the <b style={{ color: 'var(--ink-strong)' }}>Render</b> node, or find it in the Job Dock and Library.
            </div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 11.5, color: 'var(--ink-soft)', marginBottom: 12 }}>
              These are the graph's inputs. Press <b style={{ color: 'var(--ink-strong)' }}>Run</b> to generate the final video, then this panel shows the result.
            </div>
            {sources.length === 0 && (
              <div style={{ fontSize: 11.5, color: 'var(--ink-muted)' }}>No source nodes yet. Add an Image, Text or Existing-render node.</div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {sources.map(n => (
                <div key={n.id} style={{ background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)', overflow: 'hidden' }}>
                  <div style={{ padding: '6px 10px', borderBottom: '1px solid var(--stroke)', fontSize: 10.5, color: 'var(--ink-soft)', display: 'flex', gap: 6 }}>
                    <span style={{ color: 'var(--ink-strong)' }}>{NODE_TYPES[n.type]?.title || n.type}</span>
                    <span className="mono">{n.id}</span>
                  </div>
                  {n.type === 'Image' && (
                    <img src={api.imageUrl(n.props?.filename || '')} alt={n.props?.filename}
                      onError={e => { e.currentTarget.style.display = 'none'; }}
                      style={{ width: '100%', maxHeight: 220, objectFit: 'cover', display: 'block' }} />
                  )}
                  {n.type === 'ExistingRender' && n.props?.jobId && (
                    <video src={api.jobVideoUrl(n.props.jobId)} controls muted
                      onError={e => { e.currentTarget.style.display = 'none'; }}
                      style={{ width: '100%', background: '#000', display: 'block' }} />
                  )}
                  {(n.type === 'Text' || n.type === 'NewsItem') && (
                    <div style={{ padding: 10, fontSize: 11.5, color: 'var(--ink)', whiteSpace: 'pre-wrap' }}>
                      {n.props?.value || n.props?.title || '—'}
                    </div>
                  )}
                  {n.type === 'Upload' && (
                    <div style={{ padding: 10, fontSize: 11, color: 'var(--ink-soft)', fontFamily: 'var(--f-mono)' }}>{n.props?.path || '—'}</div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export { Studio, STARTER_GRAPHS };
