import { useEffect, useMemo, useRef, useState } from "react";
import { Stage, Layer, Rect, Text, Line, Group } from "react-konva";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";
import { usePersistedState } from "../lib/usePersistedState.js";

// Simple Remotion-style timeline for sequential/montage templates:
// one video track (reorder by drag, resize length, transitions, cut) +
// one optional audio track + format + duration-vs-avatar gauge.

const FORMATS = [
  ["9:16", 1080, 1920],
  ["1:1", 1080, 1080],
  ["16:9", 1920, 1080],
  ["4:5", 1080, 1350],
];
const TRANSITIONS = [
  ["crossfade", "Crossfade"],
  ["cut", "Cut"],
  ["fadeblack", "Fade black"],
  ["glitch", "Glitch"],
  ["slide", "Slide"],
  ["flash", "Flash"],
];
const STAGE_W = 760;
const RULER_H = 22;
const VID_Y = 30;
const VID_H = 72;
const AUD_Y = 122;
const AUD_H = 44;
const STAGE_H = 184;
const KIND_FILL = {
  seedance: "rgba(0,229,255,0.20)",
  existing: "rgba(168,85,247,0.20)",
  upload: "rgba(251,191,36,0.18)",
  empty: "rgba(148,163,184,0.10)",
};

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {children}
    </label>
  );
}

function uid() {
  return Math.random().toString(36).slice(2, 8);
}

export function TimelineEditor({ template, onTemplateChange, onJob }) {
  const toast = useToast();

  const acts = useMemo(
    () =>
      (template.regions || [])
        .filter((r) => r.type === "video_slot" || r.type === "image_slot")
        .slice()
        .sort((a, b) => (a.act ?? 0) - (b.act ?? 0)),
    [template.regions]
  );
  const audioReg = (template.regions || []).find(
    (r) => r.type === "audio_slot"
  );
  const canvas = template.canvas || { width: 1080, height: 1920 };

  const [values, setValues] = usePersistedState("deepotus.tl.values", {});
  const [selId, setSelId] = useState(acts[0]?.id || null);
  const [targetS, setTargetS] = usePersistedState("deepotus.tl.target", 20);
  const [renderTitle, setRenderTitle] = usePersistedState(
    "deepotus.tl.title", ""
  );
  const [fitting, setFitting] = useState(false);
  const [images, setImages] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [job, setJob] = useState(null);
  const [rendering, setRendering] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    api.listImages().then((r) => setImages(r.images || [])).catch(() => {});
    api
      .listJobs()
      .then((r) =>
        setJobs(
          (Array.isArray(r) ? r : []).filter(
            (j) => j.status === "done" && j.final_video_path
          )
        )
      )
      .catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  // ---- template structure mutations (persisted via onTemplateChange) ----
  function setRegions(regions) {
    onTemplateChange({ ...template, regions });
  }
  function patchRegion(id, patch) {
    setRegions(
      (template.regions || []).map((r) =>
        r.id === id ? { ...r, ...patch } : r
      )
    );
  }
  function setFormat(w, h) {
    onTemplateChange({
      ...template,
      canvas: { ...canvas, width: w, height: h },
    });
  }
  function reorder(orderedIds) {
    const byId = Object.fromEntries(
      (template.regions || []).map((r) => [r.id, r])
    );
    let act = 0;
    const next = orderedIds.map((id) => ({ ...byId[id], act: act++ }));
    const others = (template.regions || []).filter(
      (r) => !orderedIds.includes(r.id)
    );
    setRegions([...next, ...others]);
  }
  function addClip() {
    const n = acts.length + 1;
    const id = `r_tl_${uid()}`;
    const reg = {
      id,
      type: "video_slot",
      x: 0,
      y: 0,
      width: canvas.width,
      height: canvas.height,
      z_index: 0,
      act: acts.length,
      slot_name: `clip_${uid()}`,
      slot_label: `Clip ${n}`,
      default_provider: "seedance",
      fit: "cover",
      audio_volume: 0.0,
      length_s: 5,
      transition: { type: "crossfade", duration_s: 0.5 },
    };
    setRegions([...(template.regions || []), reg]);
    setSelId(id);
  }
  function removeClip(id) {
    const remaining = acts.filter((a) => a.id !== id).map((a) => a.id);
    reorder(remaining);
    if (selId === id) setSelId(remaining[0] || null);
  }
  function move(id, dir) {
    const ids = acts.map((a) => a.id);
    const i = ids.indexOf(id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    reorder(ids);
  }
  function splitClip(id) {
    const a = acts.find((x) => x.id === id);
    if (!a) return;
    const ids = acts.map((x) => x.id);
    const pos = ids.indexOf(id);
    const v = values[a.slot_name] || {};
    const kind = v.source_kind || a.default_provider || "seedance";
    const L = Number(a.length_s) || 5;
    let h1, h2;
    if (kind === "seedance") {
      h1 = Math.max(5, Math.round(L / 2 / 5) * 5);
      h2 = Math.max(5, L - h1);
    } else {
      h1 = Math.max(2, Math.floor(L / 2));
      h2 = Math.max(2, L - h1);
    }
    const nid = `r_tl_${uid()}`;
    const nslot = `clip_${uid()}`;
    const newReg = {
      ...structuredClone(a),
      id: nid,
      slot_name: nslot,
      slot_label: `${a.slot_label || a.slot_name} (b)`,
      length_s: h2,
      transition: {
        type: a.transition?.type || "crossfade",
        duration_s: a.transition?.duration_s || 0.5,
      },
    };
    const regions = (template.regions || []).map((r) =>
      r.id === id ? { ...r, length_s: h1 } : r
    );
    regions.push(newReg);
    const order = [...ids];
    order.splice(pos + 1, 0, nid);
    const byId = Object.fromEntries(regions.map((r) => [r.id, r]));
    let act = 0;
    const reordered = order.map((x) => ({ ...byId[x], act: act++ }));
    const others = regions.filter(
      (r) => r.type !== "video_slot" && r.type !== "image_slot"
    );
    onTemplateChange({ ...template, regions: [...reordered, ...others] });
    setValues((s) => ({
      ...s,
      [nslot]: structuredClone(s[a.slot_name] || {}),
    }));
    setSelId(nid);
  }

  function addAudio() {
    if (audioReg) return;
    setRegions([
      ...(template.regions || []),
      {
        id: `r_aud_${uid()}`,
        type: "audio_slot",
        slot_name: "music",
        slot_label: "Audio track",
        volume: 0.8,
      },
    ]);
  }
  function removeAudio() {
    if (!audioReg) return;
    setRegions(
      (template.regions || []).filter((r) => r.type !== "audio_slot")
    );
  }

  // ---- timeline geometry ----
  const lens = acts.map((a) => Number(a.length_s) || 5);
  const totalLen = lens.reduce((s, v) => s + v, 0);
  const span = Math.max(totalLen, targetS, 10);
  const pps = (STAGE_W - 8) / span; // px per second

  const blocks = [];
  let acc = 0;
  acts.forEach((a, i) => {
    const x = 4 + acc * pps;
    const w = Math.max(18, lens[i] * pps);
    blocks.push({ a, i, x, w });
    acc += lens[i];
  });

  function setSlot(name, v) {
    setValues((s) => ({ ...s, [name]: v }));
  }
  const sel = acts.find((a) => a.id === selId) || null;
  const selVal = sel ? values[sel.slot_name] || {} : {};

  // ---- render ----
  function filled(a) {
    const v = values[a.slot_name] || {};
    const k = v.source_kind || a.default_provider || "seedance";
    if (k === "seedance")
      return !!(v.seedance?.image_filename && v.seedance?.custom_prompt);
    if (k === "existing") return !!v.job_id;
    return !!v.upload_filename;
  }
  function buildSlotValues() {
    const out = {};
    for (const a of acts) {
      if (!filled(a)) continue;
      const v = values[a.slot_name] || {};
      const k = v.source_kind || a.default_provider || "seedance";
      if (k === "seedance")
        out[a.slot_name] = {
          source_kind: "seedance",
          seedance: {
            image_filename: v.seedance.image_filename,
            custom_prompt: v.seedance.custom_prompt,
            duration_s: Number(a.length_s) || 5,
            extend_mode: v.seedance?.extend_mode || "loop",
            voiceover_enabled: false,
          },
        };
      else if (k === "existing")
        out[a.slot_name] = { source_kind: "job", job_id: v.job_id };
      else
        out[a.slot_name] = {
          source_kind: "upload",
          upload_filename: v.upload_filename,
        };
    }
    if (audioReg) {
      const av = values[audioReg.slot_name] || {};
      if (av.job_id)
        out[audioReg.slot_name] = { source_kind: "job", job_id: av.job_id };
      else if (av.upload_filename)
        out[audioReg.slot_name] = {
          source_kind: "upload",
          upload_filename: av.upload_filename,
        };
    }
    return out;
  }

  // Pull a clip's real media duration (existing render) so animation
  // clips can be matched to it and a talking avatar is never trimmed.
  async function fitToSource(a) {
    const v = values[a.slot_name] || {};
    const k = v.source_kind || a.default_provider || "seedance";
    if (k !== "existing" || !v.job_id) {
      toast.error(
        "Fit to source needs an 'existing' clip (e.g. the avatar render)."
      );
      return;
    }
    setFitting(true);
    try {
      const j = await api.getJob(v.job_id);
      const d = Number(j.duration_real_s);
      if (!d || d <= 0) {
        toast.error("Could not read that clip's duration.");
        return;
      }
      const secs = Math.max(1, Math.ceil(d));
      patchRegion(a.id, {
        length_mode: "source",
        length_s: secs,
        tail_pad_s: a.tail_pad_s ?? 0.3,
      });
      setTargetS(secs);
      toast.success(
        `Locked to source: ${d.toFixed(1)}s (+${(a.tail_pad_s ?? 0.3)}s pad). ` +
          `Size the other clips to the gauge.`
      );
    } catch (e) {
      toast.error(`Fit failed: ${e.message}`);
    } finally {
      setFitting(false);
    }
  }

  function poll(id) {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getJob(id);
        setJob(j);
        onJob && onJob(j);
        if (j.status === "done" || j.status === "failed") {
          clearInterval(pollRef.current);
          setRendering(false);
          toast[j.status === "done" ? "success" : "error"](
            j.status === "done" ? "Timeline rendered." : `Failed: ${j.error}`
          );
        }
      } catch {
        /* keep polling */
      }
    }, 2000);
  }

  async function render() {
    const nFilled = acts.filter(filled).length;
    if (nFilled < 2) {
      toast.error("Fill at least 2 clips.");
      return;
    }
    setRendering(true);
    setJob(null);
    onJob && onJob(null);
    try {
      const { _builtin, ...inlineTpl } = template;
      const r = await api.renderLayoutTemplate(
        template.id || "timeline",
        buildSlotValues(),
        null,
        inlineTpl,
        renderTitle
      );
      toast.success("Timeline render queued.");
      setJob({ job_id: r.job_id, status: "queued", progress: 0 });
      poll(r.job_id);
    } catch (e) {
      setRendering(false);
      toast.error(`Render failed: ${e.message}`);
    }
  }

  const gaugePct = Math.min(100, (totalLen / Math.max(targetS, 1)) * 100);
  const close = Math.abs(totalLen - targetS) <= 1;

  return (
    <div className="panel space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="panel-title">Timeline</div>
        <div className="flex gap-1">
          {FORMATS.map(([lbl, w, h]) => (
            <button
              key={lbl}
              onClick={() => setFormat(w, h)}
              className={`text-[10px] px-2 py-1 rounded border transition-all ${
                canvas.width === w && canvas.height === h
                  ? "bg-bio-cyan/20 text-bio-cyan border-bio-cyan/40"
                  : "border-deep-700/50 text-slate-400 hover:text-slate-200"
              }`}
            >
              {lbl}
            </button>
          ))}
        </div>
      </div>

      {/* duration gauge vs avatar target */}
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-slate-400">Total {totalLen.toFixed(1)}s</span>
        <div className="flex-1 h-2 bg-deep-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${close ? "bg-green-400" : "bg-bio-cyan"}`}
            style={{ width: `${gaugePct}%` }}
          />
        </div>
        <label className="text-slate-500">avatar</label>
        <input
          type="number"
          className="input w-16 !py-1 text-xs"
          min={5}
          step={5}
          value={targetS}
          onChange={(e) => setTargetS(Number(e.target.value) || 5)}
        />
        <span className="text-slate-500">s</span>
      </div>

      {/* the timeline canvas */}
      <div className="bg-deep-900/40 rounded-lg p-2 overflow-x-auto">
        <Stage width={STAGE_W} height={STAGE_H}>
          <Layer>
            {/* ruler */}
            <Rect x={0} y={0} width={STAGE_W} height={RULER_H}
              fill="#050a17" />
            {Array.from({ length: Math.ceil(span / 5) + 1 }).map((_, k) => {
              const x = 4 + k * 5 * pps;
              return (
                <Group key={k}>
                  <Line points={[x, 0, x, STAGE_H]}
                    stroke="#1f2d4a" strokeWidth={1} />
                  <Text x={x + 3} y={5} text={`${k * 5}s`}
                    fontSize={10} fill="#64748b" />
                </Group>
              );
            })}
            {/* target marker */}
            <Line
              points={[4 + targetS * pps, 0, 4 + targetS * pps, STAGE_H]}
              stroke="#22c55e" strokeWidth={2} dash={[4, 4]}
            />
            {/* video track */}
            <Text x={4} y={VID_Y - 12} text="VIDEO" fontSize={9}
              fill="#64748b" />
            {blocks.map(({ a, i, x, w }) => {
              const v = values[a.slot_name] || {};
              const k = v.source_kind || a.default_provider || "seedance";
              const fill = filled(a)
                ? KIND_FILL[k] || KIND_FILL.empty
                : KIND_FILL.empty;
              return (
                <Group
                  key={a.id}
                  x={x}
                  y={VID_Y}
                  draggable
                  dragBoundFunc={(pos) => ({ x: pos.x, y: VID_Y })}
                  onClick={() => setSelId(a.id)}
                  onTap={() => setSelId(a.id)}
                  onDragEnd={(e) => {
                    const cx = e.target.x() + w / 2;
                    // order by each block's center after the drag
                    const centers = blocks.map((b) =>
                      b.a.id === a.id ? cx : b.x + b.w / 2
                    );
                    const order = blocks
                      .map((b, idx) => ({ id: b.a.id, c: centers[idx] }))
                      .sort((p, q) => p.c - q.c)
                      .map((p) => p.id);
                    reorder(order);
                    setSelId(a.id);
                  }}
                >
                  <Rect
                    width={w}
                    height={VID_H}
                    fill={fill}
                    stroke={selId === a.id ? "#ffffff" : "#1f2d4a"}
                    strokeWidth={selId === a.id ? 3 : 1}
                    cornerRadius={4}
                  />
                  <Text x={6} y={6} width={w - 12}
                    text={`${i + 1}. ${a.slot_label || a.slot_name}`}
                    fontSize={11} fill="#e2e8f0" ellipsis wrap="none" />
                  <Text x={6} y={26} text={`${lens[i]}s · ${k}`}
                    fontSize={10} fill="#94a3b8" />
                  <Text x={6} y={44}
                    text={i === 0 ? "" : `⤳ ${(a.transition?.type || "crossfade")}`}
                    fontSize={9} fill="#00e5ff" />
                  {/* right-edge length handle */}
                  <Rect
                    x={w - 7}
                    y={0}
                    width={7}
                    height={VID_H}
                    fill="#00e5ff"
                    opacity={0.5}
                    draggable
                    dragBoundFunc={(pos) => ({
                      x: Math.max(x + 18, pos.x),
                      y: VID_Y,
                    })}
                    onDragEnd={(e) => {
                      const newW = e.target.x() - x + 7;
                      let secs = Math.round(newW / pps);
                      const isSeed = k === "seedance";
                      secs = isSeed
                        ? Math.max(5, Math.round(secs / 5) * 5)
                        : Math.max(2, secs);
                      secs = Math.min(secs, 60);
                      patchRegion(a.id, { length_s: secs });
                      e.target.position({ x: w - 7, y: 0 });
                    }}
                  />
                </Group>
              );
            })}
            {/* audio track */}
            <Text x={4} y={AUD_Y - 12} text="AUDIO" fontSize={9}
              fill="#64748b" />
            <Rect
              x={4}
              y={AUD_Y}
              width={STAGE_W - 8}
              height={AUD_H}
              fill={
                audioReg && (values[audioReg.slot_name] || {}).job_id
                  ? "rgba(34,197,94,0.18)"
                  : audioReg &&
                    (values[audioReg.slot_name] || {}).upload_filename
                  ? "rgba(34,197,94,0.18)"
                  : "rgba(148,163,184,0.08)"
              }
              stroke="#1f2d4a"
              cornerRadius={4}
            />
            <Text x={10} y={AUD_Y + 14}
              text={
                audioReg
                  ? (values[audioReg.slot_name] || {}).upload_filename ||
                    ((values[audioReg.slot_name] || {}).job_id
                      ? "existing audio"
                      : "no audio (silent)")
                  : "no audio track"
              }
              fontSize={11} fill="#94a3b8" />
          </Layer>
        </Stage>
      </div>

      {/* clip controls */}
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost text-xs px-2 py-1" onClick={addClip}>
          + Clip
        </button>
        {sel && (
          <>
            <button className="btn-ghost text-xs px-2 py-1"
              onClick={() => move(sel.id, -1)}>◀ Move</button>
            <button className="btn-ghost text-xs px-2 py-1"
              onClick={() => move(sel.id, 1)}>Move ▶</button>
            <button className="btn-ghost text-xs px-2 py-1"
              onClick={() => splitClip(sel.id)}
              title="Split this clip into two">✂ Split</button>
            <button
              className="btn-ghost text-xs px-2 py-1 text-red-300"
              onClick={() => removeClip(sel.id)}
            >
              ✕ Remove
            </button>
          </>
        )}
        {audioReg ? (
          <button className="btn-ghost text-xs px-2 py-1 text-red-300"
            onClick={removeAudio}>✕ Audio</button>
        ) : (
          <button className="btn-ghost text-xs px-2 py-1"
            onClick={addAudio}>+ Audio track</button>
        )}
      </div>

      {/* selected clip editor */}
      {sel && (
        <div className="border-t border-deep-700/50 pt-3 space-y-2">
          <div className="text-sm font-medium">
            Clip {acts.indexOf(sel) + 1} — {sel.slot_label || sel.slot_name}
          </div>
          <div className="flex gap-1">
            {["seedance", "existing", "upload"].map((k) => {
              const cur =
                selVal.source_kind || sel.default_provider || "seedance";
              return (
                <button
                  key={k}
                  onClick={() =>
                    setSlot(sel.slot_name, { ...selVal, source_kind: k })
                  }
                  className={`flex-1 text-xs px-2 py-1 rounded border ${
                    cur === k
                      ? "bg-bio-cyan/20 text-bio-cyan border-bio-cyan/40"
                      : "border-deep-700/50 text-slate-400"
                  }`}
                >
                  {k}
                </button>
              );
            })}
          </div>
          {(selVal.source_kind || sel.default_provider || "seedance") ===
            "seedance" && (
            <>
              <Field label="Start image">
                <select
                  className="input w-full"
                  value={selVal.seedance?.image_filename || ""}
                  onChange={(e) =>
                    setSlot(sel.slot_name, {
                      ...selVal,
                      seedance: {
                        ...(selVal.seedance || {}),
                        image_filename: e.target.value,
                      },
                    })
                  }
                >
                  <option value="">— image —</option>
                  {images.map((im) => (
                    <option key={im.filename} value={im.filename}>
                      {im.filename}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Prompt">
                <textarea
                  className="input w-full h-14"
                  value={selVal.seedance?.custom_prompt || ""}
                  onChange={(e) =>
                    setSlot(sel.slot_name, {
                      ...selVal,
                      seedance: {
                        ...(selVal.seedance || {}),
                        custom_prompt: e.target.value,
                      },
                    })
                  }
                />
              </Field>
            </>
          )}
          {(selVal.source_kind || sel.default_provider) === "existing" && (
            <Field label="Existing rendered clip">
              <select
                className="input w-full"
                value={selVal.job_id || ""}
                onChange={(e) =>
                  setSlot(sel.slot_name, {
                    ...selVal,
                    job_id: e.target.value,
                  })
                }
              >
                <option value="">— pick clip —</option>
                {jobs.map((j) => (
                  <option key={j.job_id} value={j.job_id}>
                    {j.title
                      ? `${j.title} · ${(j.job_id || "").slice(0, 6)}`
                      : `${j.provider || "?"} · ${(j.job_id || "").slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </Field>
          )}
          {(selVal.source_kind || sel.default_provider) === "upload" && (
            <Field label="Filename (assets/images or assets/outputs)">
              <input
                className="input w-full"
                placeholder="clip.mp4"
                value={selVal.upload_filename || ""}
                onChange={(e) =>
                  setSlot(sel.slot_name, {
                    ...selVal,
                    upload_filename: e.target.value,
                  })
                }
              />
            </Field>
          )}
          <div className="grid grid-cols-2 gap-2">
            <Field label="Length mode">
              <select
                className="input w-full"
                value={sel.length_mode || "fixed"}
                onChange={(e) =>
                  patchRegion(sel.id, { length_mode: e.target.value })
                }
              >
                <option value="fixed">Fixed (trim/pad)</option>
                <option value="source">Source (full clip)</option>
              </select>
            </Field>
            <Field
              label={
                (sel.length_mode || "fixed") === "source"
                  ? "Length (auto)"
                  : "Length (s)"
              }
            >
              <input
                type="number"
                className="input w-full"
                min={2}
                max={60}
                step={5}
                disabled={(sel.length_mode || "fixed") === "source"}
                value={sel.length_s ?? 5}
                onChange={(e) =>
                  patchRegion(sel.id, {
                    length_s: Number(e.target.value) || 5,
                  })
                }
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label={`Tail pad (${sel.tail_pad_s ?? 0}s)`}>
              <input
                type="range"
                className="w-full"
                min={0}
                max={2}
                step={0.1}
                value={sel.tail_pad_s ?? 0}
                onChange={(e) =>
                  patchRegion(sel.id, {
                    tail_pad_s: Number(e.target.value),
                  })
                }
              />
            </Field>
            <label className="flex items-end gap-2 pb-1 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={Number(sel.audio_volume || 0) > 0}
                onChange={(e) =>
                  patchRegion(sel.id, {
                    audio_volume: e.target.checked ? 1.0 : 0.0,
                  })
                }
              />
              Keep this clip's audio (avatar voice)
            </label>
          </div>
          <button
            className="btn-ghost text-xs px-2 py-1 w-full"
            disabled={fitting}
            onClick={() => fitToSource(sel)}
            title="Read the real duration of the picked existing clip and lock this clip to it"
          >
            {fitting ? "Reading…" : "🎯 Fit to source (avatar length)"}
          </button>
          <div className="grid grid-cols-2 gap-2">
            {acts.indexOf(sel) > 0 && (
              <Field label="Transition in">
                <select
                  className="input w-full"
                  value={sel.transition?.type || "crossfade"}
                  onChange={(e) =>
                    patchRegion(sel.id, {
                      transition: {
                        type: e.target.value,
                        duration_s: sel.transition?.duration_s || 0.5,
                      },
                    })
                  }
                >
                  {TRANSITIONS.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </Field>
            )}
          </div>
        </div>
      )}

      {/* audio editor */}
      {audioReg && (
        <div className="border-t border-deep-700/50 pt-3 space-y-2">
          <div className="text-sm font-medium">Audio track</div>
          <Field label="Existing audio (rendered job)">
            <select
              className="input w-full"
              value={(values[audioReg.slot_name] || {}).job_id || ""}
              onChange={(e) =>
                setSlot(audioReg.slot_name, {
                  job_id: e.target.value,
                  upload_filename: "",
                })
              }
            >
              <option value="">— none —</option>
              {jobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {`${j.provider || "?"} · ${(j.job_id || "").slice(0, 8)}`}
                </option>
              ))}
            </select>
          </Field>
          <Field label="…or upload filename (assets/images|outputs)">
            <input
              className="input w-full"
              placeholder="music.mp3"
              value={(values[audioReg.slot_name] || {}).upload_filename || ""}
              onChange={(e) =>
                setSlot(audioReg.slot_name, {
                  upload_filename: e.target.value,
                  job_id: "",
                })
              }
            />
          </Field>
          <Field label={`Volume (${audioReg.volume ?? 0.8})`}>
            <input
              type="range"
              className="w-full"
              min={0}
              max={1}
              step={0.05}
              value={audioReg.volume ?? 0.8}
              onChange={(e) =>
                patchRegion(audioReg.id, {
                  volume: Number(e.target.value),
                })
              }
            />
          </Field>
        </div>
      )}

      <Field label="Render name (optional — shows in queue & pickers)">
        <input
          className="input w-full"
          placeholder="e.g. deepotus daily — ep. 12"
          value={renderTitle}
          onChange={(e) => setRenderTitle(e.target.value)}
        />
      </Field>
      <button
        className="btn-primary w-full"
        onClick={render}
        disabled={rendering}
      >
        {rendering ? "Rendering…" : "🎬 Render timeline"}
      </button>
      {job && (
        <div className="text-xs font-mono text-slate-400">
          {job.job_id?.slice(0, 12)} · {job.status} · {job.progress ?? 0}%
          {job.status === "done" && (
            <span className="text-green-300"> · preview ←</span>
          )}
        </div>
      )}
      <div className="text-[10px] text-slate-500">
        Fill 2+ clips, set lengths to match the avatar (gauge), pick
        transitions, render. The result lands in the queue — reuse it via
        “existing” in your post template. Everything here persists across
        tabs / reloads.
      </div>
    </div>
  );
}
