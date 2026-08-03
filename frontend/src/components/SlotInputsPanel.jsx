import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";
import { usePersistedState } from "../lib/usePersistedState.js";

const SLOT_TYPES = ["video_slot", "image_slot", "text_slot"];
const VOICE_MODES = ["", "oracle", "alpha", "zen", "memer"];

function slotsOf(template) {
  return (template.regions || [])
    .filter((r) => SLOT_TYPES.includes(r.type))
    .map((r) => ({
      slot_name: r.slot_name,
      slot_label: r.slot_label || r.slot_name,
      type: r.type,
      default_provider: r.default_provider,
      default_text: r.default_text || "",
      max_chars: r.max_chars,
    }));
}

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

const AV_LIMIT = 200;

function VideoSlotRow({ slot, value, onChange, images, avatars, voices, jobs }) {
  const kind = value.source_kind || slot.default_provider || "upload";
  const [avq, setAvq] = useState("");
  function set(patch) {
    onChange({ ...value, ...patch });
  }
  const q = avq.trim().toLowerCase();
  const avMatches = q
    ? avatars.filter((a) =>
        (`${a.name || ""} ${a.avatar_name || ""} ${a.avatar_id || ""}`)
          .toLowerCase()
          .includes(q)
      )
    : avatars;
  const avShown = avMatches.slice(0, AV_LIMIT);
  return (
    <div className="space-y-2">
      <div className="flex gap-1">
        {[
          ["seedance", "seedance"],
          ["heygen", "heygen"],
          ["upload", "upload"],
          ["existing", "job"],
        ].map(([label, k]) => (
          <button
            key={k}
            onClick={() => set({ source_kind: k })}
            className={`flex-1 text-xs px-2 py-1 rounded-md border transition-all ${
              kind === k
                ? "bg-bio-cyan/20 text-bio-cyan border-bio-cyan/40"
                : "border-deep-700/50 text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {kind === "job" && (
        <Field label="Pick an already-rendered video">
          <select
            className="input w-full"
            value={value.job_id || ""}
            onChange={(e) => set({ job_id: e.target.value })}
          >
            <option value="">— pick a rendered clip —</option>
            {jobs.map((j) => (
              <option key={j.job_id} value={j.job_id}>
                {`${j.title || j.provider || "?"} · ${(j.job_id || "").slice(0, 8)} · ${
                  j.created_at ? j.created_at.slice(0, 16).replace("T", " ") : ""
                }`}
              </option>
            ))}
          </select>
          {value.job_id && (
            <video
              key={value.job_id}
              className="w-full rounded-md mt-2 bg-black max-h-48"
              src={api.jobVideoUrl(value.job_id)}
              controls
            />
          )}
        </Field>
      )}

      {kind === "seedance" && (
        <div className="space-y-2">
          <Field label="Start image">
            <select
              className="input w-full"
              value={value.seedance?.image_filename || ""}
              onChange={(e) =>
                set({
                  seedance: {
                    ...(value.seedance || {}),
                    image_filename: e.target.value,
                  },
                })
              }
            >
              <option value="">— pick image —</option>
              {images.map((im) => (
                <option key={im.filename} value={im.filename}>
                  {im.filename}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Prompt">
            <textarea
              className="input w-full h-16"
              value={value.seedance?.custom_prompt || ""}
              onChange={(e) =>
                set({
                  seedance: {
                    ...(value.seedance || {}),
                    custom_prompt: e.target.value,
                  },
                })
              }
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Duration (fit avatar)">
              <select
                className="input w-full"
                value={value.seedance?.duration_s || 5}
                onChange={(e) =>
                  set({
                    seedance: {
                      ...(value.seedance || {}),
                      duration_s: Number(e.target.value),
                    },
                  })
                }
              >
                {[5, 10, 15, 20, 25, 30, 40, 50, 60].map((d) => (
                  <option key={d} value={d}>
                    {d}s
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Extend mode">
              <select
                className="input w-full"
                value={value.seedance?.extend_mode || "loop"}
                onChange={(e) =>
                  set({
                    seedance: {
                      ...(value.seedance || {}),
                      extend_mode: e.target.value,
                    },
                  })
                }
              >
                <option value="loop">loop</option>
                <option value="hold">hold last frame</option>
              </select>
            </Field>
          </div>
          <div className="text-[10px] text-slate-500">
            Seedance generates ≤10s; longer is extended (loop/hold) to fit
            the HeyGen avatar length.
          </div>
        </div>
      )}

      {kind === "heygen" && (
        <div className="space-y-2">
          <Field label="Avatar">
            <input
              className="input w-full mb-1"
              placeholder={`Search ${avatars.length} avatars…`}
              value={avq}
              onChange={(e) => setAvq(e.target.value)}
            />
            <select
              className="input w-full"
              value={value.heygen?.avatar_id || ""}
              onChange={(e) => {
                const a = avatars.find((x) => x.avatar_id === e.target.value);
                set({
                  heygen: {
                    ...(value.heygen || {}),
                    avatar_id: e.target.value,
                    avatar_type: a?.avatar_type || "avatar",
                  },
                });
              }}
            >
              <option value="">— pick avatar —</option>
              {avShown.map((a) => (
                <option key={a.avatar_id} value={a.avatar_id}>
                  {(a.name || a.avatar_name || a.avatar_id) +
                    (a.avatar_type === "talking_photo" ? " (photo)" : "")}
                </option>
              ))}
            </select>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {avMatches.length > AV_LIMIT
                ? `${avMatches.length} matches — showing first ${AV_LIMIT}, refine search`
                : `${avMatches.length} match${avMatches.length === 1 ? "" : "es"}`}
            </div>
          </Field>
          <Field label="Voice">
            <select
              className="input w-full"
              value={value.heygen?.voice_id || ""}
              onChange={(e) =>
                set({
                  heygen: { ...(value.heygen || {}), voice_id: e.target.value },
                })
              }
            >
              <option value="">— pick voice —</option>
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name || v.voice_id}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Script">
            <textarea
              className="input w-full h-16"
              value={value.heygen?.script || ""}
              onChange={(e) =>
                set({
                  heygen: { ...(value.heygen || {}), script: e.target.value },
                })
              }
            />
          </Field>
        </div>
      )}

      {kind === "upload" && (
        <Field label="Filename (in assets/images or assets/outputs)">
          <input
            className="input w-full"
            placeholder="my_clip.mp4"
            value={value.upload_filename || ""}
            onChange={(e) => set({ upload_filename: e.target.value })}
          />
        </Field>
      )}
    </div>
  );
}

const TRANSITIONS = [
  ["crossfade", "Crossfade (fondu enchaîné)"],
  ["cut", "Cut (franc)"],
  ["fadeblack", "Fade to black"],
  ["glitch", "Glitch"],
  ["slide", "Slide"],
  ["flash", "Flash"],
];

export function SlotInputsPanel({ template, onJob, onRegionPatch }) {
  const toast = useToast();
  const slots = slotsOf(template);
  const isSeq = template.render_mode === "sequential";
  // Montage acts in order (the chained clips).
  const acts = (template.regions || [])
    .filter((r) => r.type === "video_slot" || r.type === "image_slot")
    .slice()
    .sort(
      (a, b) =>
        (a.act ?? 0) - (b.act ?? 0) ||
        (a.z_index ?? 0) - (b.z_index ?? 0)
    );
  // Persisted: filled slot inputs + voice mode survive edit<->render,
  // tab switches and reloads (the work you don't want to redo for a post).
  const [values, setValues] = usePersistedState("deepotus.slots.draft", {});
  const [voiceMode, setVoiceMode] = usePersistedState(
    "deepotus.slots.voiceMode", "");
  const [images, setImages] = useState([]);
  const [avatars, setAvatars] = useState([]);
  const [voices, setVoices] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [job, setJob] = useState(null);
  const [rendering, setRendering] = useState(false);
  const pollRef = useRef(null);

  // Mirror job state up so the center pane can show the result big.
  function pushJob(j) {
    setJob(j);
    onJob && onJob(j);
  }

  useEffect(() => {
    api.listImages().then((r) => setImages(r.images || [])).catch(() => {});
    api
      .listHeygenAvatars()
      .then((r) => setAvatars(r.avatars || []))
      .catch(() => {});
    api
      .listHeygenVoices()
      .then((r) => setVoices(r.voices || []))
      .catch(() => {});
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
  }, []);

  useEffect(() => () => clearInterval(pollRef.current), []);

  function setSlot(name, v) {
    setValues((s) => ({ ...s, [name]: v }));
  }

  function slotFilled(s) {
    const v = values[s.slot_name] || {};
    if (s.type === "text_slot")
      return String(v.text ?? s.default_text ?? "").trim().length > 0;
    const kind = v.source_kind || s.default_provider || "upload";
    if (kind === "seedance")
      return !!(v.seedance?.image_filename && v.seedance?.custom_prompt);
    if (kind === "heygen")
      return !!(v.heygen?.avatar_id && v.heygen?.voice_id && v.heygen?.script);
    if (kind === "job") return !!v.job_id;
    return !!v.upload_filename;
  }

  function buildPayload() {
    const out = {};
    for (const s of slots) {
      // Montage: only send the clips actually filled (empties are skipped).
      if (isSeq && !slotFilled(s)) continue;
      const v = values[s.slot_name] || {};
      if (s.type === "text_slot") {
        out[s.slot_name] = {
          source_kind: "text",
          text: v.text ?? s.default_text ?? "",
        };
        continue;
      }
      const kind = v.source_kind || s.default_provider || "upload";
      if (kind === "seedance") {
        out[s.slot_name] = {
          source_kind: "seedance",
          seedance: {
            image_filename: v.seedance?.image_filename || "",
            custom_prompt: v.seedance?.custom_prompt || "",
            duration_s: Number(v.seedance?.duration_s) || 5,
            extend_mode: v.seedance?.extend_mode || "loop",
            voiceover_enabled: false,
          },
        };
      } else if (kind === "heygen") {
        out[s.slot_name] = {
          source_kind: "heygen",
          heygen: {
            avatar_id: v.heygen?.avatar_id || "",
            avatar_type: v.heygen?.avatar_type || "avatar",
            voice_id: v.heygen?.voice_id || "",
            script: v.heygen?.script || "",
          },
        };
      } else if (kind === "job") {
        out[s.slot_name] = {
          source_kind: "job",
          job_id: v.job_id || "",
        };
      } else {
        out[s.slot_name] = {
          source_kind: "upload",
          upload_filename: v.upload_filename || "",
        };
      }
    }
    return out;
  }

  function validate(payload) {
    if (isSeq) {
      const filled = slots.filter(
        (s) => s.type !== "text_slot" && slotFilled(s)
      );
      if (filled.length < 2)
        return "Montage: fill at least 2 clips.";
    }
    for (const s of slots) {
      const p = payload[s.slot_name];
      if (!p) continue; // skipped (empty montage act)
      if (s.type === "text_slot") continue;
      if (p.source_kind === "seedance" && !p.seedance.image_filename)
        return `Slot "${s.slot_label}": pick a start image.`;
      if (p.source_kind === "seedance" && !p.seedance.custom_prompt)
        return `Slot "${s.slot_label}": enter a prompt.`;
      if (p.source_kind === "heygen" && (!p.heygen.avatar_id || !p.heygen.voice_id))
        return `Slot "${s.slot_label}": pick avatar + voice.`;
      if (p.source_kind === "heygen" && !p.heygen.script)
        return `Slot "${s.slot_label}": enter a script.`;
      if (p.source_kind === "upload" && !p.upload_filename)
        return `Slot "${s.slot_label}": enter a filename.`;
      if (p.source_kind === "job" && !p.job_id)
        return `Slot "${s.slot_label}": pick a rendered clip.`;
    }
    return null;
  }

  function poll(jobId) {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getJob(jobId);
        pushJob(j);
        if (j.status === "done" || j.status === "failed") {
          clearInterval(pollRef.current);
          setRendering(false);
          if (j.status === "done") toast.success("Render complete.");
          else toast.error(`Render failed: ${j.error || "unknown"}`);
        }
      } catch {
        /* keep polling */
      }
    }, 2000);
  }

  async function render() {
    if (!template.regions || template.regions.length === 0) {
      toast.error("Add at least one region first.");
      return;
    }
    const payload = buildPayload();
    const err = validate(payload);
    if (err) {
      toast.error(err);
      return;
    }
    setRendering(true);
    pushJob(null);
    try {
      // Send the LIVE edited template inline so unsaved edits (ticker
      // color/text, etc.) render exactly as seen — no save required.
      const { _builtin, ...inlineTpl } = template;
      const r = await api.renderLayoutTemplate(
        template.id || "inline",
        payload,
        voiceMode || null,
        inlineTpl
      );
      toast.success("Render queued.");
      poll(r.job_id);
      pushJob({ job_id: r.job_id, status: "queued", progress: 0 });
    } catch (e) {
      setRendering(false);
      toast.error(`Render failed: ${e.message}`);
    }
  }

  return (
    <div className="panel space-y-4">
      <div className="panel-title">Render · {template.name}</div>
      {isSeq && (
        <div className="text-[11px] text-slate-500">
          Montage: fill 2 to {acts.length} clips (empty ones are skipped),
          pick transitions below, then render — no save required.
        </div>
      )}
      {slots.length === 0 && (
        <div className="text-sm text-slate-500 italic">
          This template has no fillable slots.
        </div>
      )}

      {slots.map((s) => (
        <div
          key={s.slot_name}
          className="border-t border-deep-700/50 pt-3 space-y-2"
        >
          <div className="text-sm font-medium">
            {s.slot_label}{" "}
            <span className="text-[10px] font-mono text-slate-500">
              {s.slot_name} · {s.type}
            </span>
          </div>
          {s.type === "text_slot" ? (
            <Field label={`Text${s.max_chars ? ` (max ${s.max_chars})` : ""}`}>
              <input
                className="input w-full"
                maxLength={s.max_chars || undefined}
                value={values[s.slot_name]?.text ?? s.default_text}
                onChange={(e) =>
                  setSlot(s.slot_name, { text: e.target.value })
                }
              />
            </Field>
          ) : (
            <VideoSlotRow
              slot={s}
              value={values[s.slot_name] || {}}
              onChange={(v) => setSlot(s.slot_name, v)}
              images={images}
              avatars={avatars}
              voices={voices}
              jobs={jobs}
            />
          )}
        </div>
      ))}

      {isSeq && acts.length >= 2 && (
        <div className="border-t border-deep-700/50 pt-3 space-y-2">
          <div className="panel-title">Transitions</div>
          <div className="text-[10px] text-slate-500">
            Between each filled clip. Saved with the template (persists
            across tabs / reloads) and rendered as-is.
          </div>
          {acts.slice(1).map((a) => {
            const tr = a.transition || {};
            return (
              <div key={a.id} className="flex items-center gap-2">
                <div className="text-[11px] text-slate-400 w-20 shrink-0 truncate">
                  → {a.slot_label || a.slot_name}
                </div>
                <select
                  className="input flex-1"
                  value={tr.type || "crossfade"}
                  onChange={(e) =>
                    onRegionPatch &&
                    onRegionPatch(a.id, {
                      transition: {
                        type: e.target.value,
                        duration_s: Number(tr.duration_s) || 0.5,
                      },
                    })
                  }
                >
                  {TRANSITIONS.map(([v, label]) => (
                    <option key={v} value={v}>
                      {label}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  className="input w-16"
                  min={0.1}
                  max={2}
                  step={0.1}
                  value={tr.duration_s ?? 0.5}
                  title="Transition seconds"
                  onChange={(e) =>
                    onRegionPatch &&
                    onRegionPatch(a.id, {
                      transition: {
                        type: tr.type || "crossfade",
                        duration_s: Number(e.target.value) || 0.5,
                      },
                    })
                  }
                />
              </div>
            );
          })}
        </div>
      )}

      <div className="border-t border-deep-700/50 pt-3 space-y-3">
        <Field label="Voice mode (applies to all generated clips)">
          <select
            className="input w-full"
            value={voiceMode}
            onChange={(e) => setVoiceMode(e.target.value)}
          >
            {VOICE_MODES.map((m) => (
              <option key={m} value={m}>
                {m || "(none)"}
              </option>
            ))}
          </select>
        </Field>
        <button
          className="btn-primary w-full"
          onClick={render}
          disabled={rendering || slots.length === 0}
        >
          {rendering ? "Rendering…" : "🎨 Render template"}
        </button>

        {job && (
          <div className="text-xs font-mono text-slate-400">
            job {job.job_id?.slice(0, 12)} · {job.status} ·{" "}
            {job.progress ?? 0}%
            {job.status === "done" && (
              <span className="text-green-300"> · see preview ←</span>
            )}
            {job.status === "failed" && (
              <span className="text-red-300"> · failed</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
