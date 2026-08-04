import { useMemo, useState } from "react";
import { Stage, Layer, Rect } from "react-konva";
import { RegionPalette } from "./RegionPalette.jsx";
import { RegionNode } from "./RegionNode.jsx";
import { PropertiesPanel } from "./PropertiesPanel.jsx";
import { SlotInputsPanel } from "./SlotInputsPanel.jsx";
import { TimelineEditor } from "./TimelineEditor.jsx";
import { TemplateList } from "./TemplateList.jsx";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";
import { usePersistedState } from "../lib/usePersistedState.js";

const MAX_W = 380;
const MAX_H = 620;

function emptyTemplate() {
  return {
    id: "",
    name: "Untitled template",
    description: "",
    version: 1,
    canvas: {
      width: 1080,
      height: 1920,
      background_color: "#02060d",
      fps: 30,
      duration_s: 8,
    },
    regions: [],
    transitions: [],
    audio: {
      master_track: "mix",
      background_music: null,
      ducking_db: -18,
      fade_in_s: 0.3,
      fade_out_s: 0.6,
      loudness_target_lufs: -14,
    },
    metadata: {
      tags: [],
      target_platforms: ["instagram_reels", "youtube_shorts"],
    },
  };
}

function uid(type) {
  return `r_${type}_${Math.random().toString(36).slice(2, 8)}`;
}

export function TemplateEditor() {
  const toast = useToast();
  // Persisted so a template being built for a post survives edit<->render
  // toggles, provider-tab switches and full reloads.
  const [template, setTemplate] = usePersistedState(
    "deepotus.tpl.draft", emptyTemplate);
  const [mode, setMode] = usePersistedState("deepotus.tpl.mode", "edit");
  const [selectedId, setSelectedId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [saving, setSaving] = useState(false);
  const [renderJob, setRenderJob] = useState(null);

  const c = template.canvas;
  const scale = useMemo(
    () => Math.min(MAX_W / c.width, MAX_H / c.height),
    [c.width, c.height]
  );

  const ordered = useMemo(
    () =>
      [...template.regions].sort(
        (a, b) => (a.z_index ?? 0) - (b.z_index ?? 0)
      ),
    [template.regions]
  );
  const selected = template.regions.find((r) => r.id === selectedId) || null;

  function patchTemplate(patch) {
    setTemplate((t) => ({ ...t, ...patch }));
  }

  function uniqueSlot(name, exceptId) {
    const used = new Set(
      template.regions
        .filter((r) => r.id !== exceptId && r.slot_name)
        .map((r) => r.slot_name)
    );
    if (!name) return name;
    let n = name;
    let i = 2;
    while (used.has(n)) n = `${name}_${i++}`;
    return n;
  }

  function addRegion(region) {
    const id = uid(region.type);
    const r = { ...region, id };
    r.width = Math.min(r.width, c.width);
    r.height = Math.min(r.height, c.height);
    r.x = Math.max(0, Math.min(r.x, c.width - r.width));
    r.y = Math.max(0, Math.min(r.y, c.height - r.height));
    if (r.slot_name) r.slot_name = uniqueSlot(r.slot_name, id);
    setTemplate((t) => ({ ...t, regions: [...t.regions, r] }));
    setSelectedId(id);
  }

  function updateRegion(id, patch) {
    setTemplate((t) => ({
      ...t,
      regions: t.regions.map((r) =>
        r.id === id ? { ...r, ...patch } : r
      ),
    }));
  }

  function deleteRegion(id) {
    setTemplate((t) => ({
      ...t,
      regions: t.regions.filter((r) => r.id !== id),
    }));
    setSelectedId(null);
  }

  function loadTemplate(t) {
    const { _builtin, ...clean } = t;
    setTemplate(structuredClone(clean));
    setSelectedId(null);
    setRenderJob(null);
  }

  async function loadMontage() {
    try {
      const t = await api.getLayoutTemplate("tpl_timeline");
      loadTemplate(t);
      setMode("render");
      toast.success("Timeline loaded — order clips, set lengths + transitions.");
    } catch (e) {
      toast.error(`Timeline load failed: ${e.message}`);
    }
  }

  async function save() {
    if (!template.name?.trim()) {
      toast.error("Template needs a name.");
      return;
    }
    if (template.regions.length === 0) {
      toast.error("Add at least one region first.");
      return;
    }
    setSaving(true);
    try {
      const r = await api.saveLayoutTemplate(template);
      setTemplate((t) => ({ ...t, id: r.template_id }));
      setRefreshKey((k) => k + 1);
      toast.success(`Saved as ${r.template_id}`);
    } catch (e) {
      toast.error(`Save failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="col-span-12 grid grid-cols-12 gap-4">
      {/* Left: palette + saved templates */}
      <div className="col-span-12 lg:col-span-3 space-y-4">
        {mode === "edit" && <RegionPalette onAdd={addRegion} />}
        <TemplateList
          refreshKey={refreshKey}
          currentId={template.id}
          onPick={loadTemplate}
        />
      </div>

      {/* Center: canvas */}
      <div className="col-span-12 lg:col-span-6">
        <div className="panel space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-1">
              {["edit", "render"].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`text-xs px-3 py-1 rounded-md border transition-all ${
                    mode === m
                      ? "bg-bio-cyan/20 text-bio-cyan border-bio-cyan/40"
                      : "border-deep-700/50 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                className="btn-ghost text-xs px-3 py-1"
                onClick={() => {
                  setTemplate(emptyTemplate());
                  setSelectedId(null);
                  setRenderJob(null);
                }}
              >
                New
              </button>
              <button
                className="btn-ghost text-xs px-3 py-1"
                onClick={loadMontage}
                title="Timeline: order clips, set lengths, transitions, format, audio"
              >
                🎬 Timeline
              </button>
              <button
                className="btn-primary text-xs px-3 py-1"
                onClick={save}
                disabled={saving}
              >
                {saving ? "Saving…" : "Save template"}
              </button>
            </div>
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            {c.width}×{c.height} · {Math.round(scale * 100)}% preview ·{" "}
            {template.regions.length} regions · snap 60px
          </div>
          {mode === "render" && renderJob ? (
            <div className="bg-deep-900/40 rounded-lg p-4 space-y-3">
              <div className="text-xs font-mono text-slate-400">
                render {renderJob.job_id?.slice(0, 12)} · {renderJob.status} ·{" "}
                {renderJob.progress ?? 0}%
              </div>
              {renderJob.current_step && (
                <div className="text-[11px] text-slate-500">
                  {renderJob.current_step}
                </div>
              )}
              {renderJob.status !== "done" &&
                renderJob.status !== "failed" && (
                  <div className="h-1.5 bg-deep-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-bio-cyan transition-all"
                      style={{ width: `${renderJob.progress ?? 0}%` }}
                    />
                  </div>
                )}
              {renderJob.status === "done" && (
                <div className="space-y-3">
                  <video
                    key={renderJob.job_id}
                    className="w-full rounded-lg max-h-[620px] mx-auto bg-black"
                    src={api.jobVideoUrl(renderJob.job_id)}
                    controls
                    autoPlay
                  />
                  <a
                    className="btn-primary block text-center"
                    href={api.jobVideoUrl(renderJob.job_id)}
                    download
                  >
                    Download MP4
                  </a>
                </div>
              )}
              {renderJob.status === "failed" && (
                <div className="text-sm text-red-300">
                  {renderJob.error || "Render failed."}
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex justify-center bg-deep-900/40 rounded-lg p-3">
                <Stage
                  width={c.width * scale}
                  height={c.height * scale}
                  onMouseDown={(e) => {
                    if (e.target === e.target.getStage()) setSelectedId(null);
                  }}
                >
                  <Layer scaleX={scale} scaleY={scale}>
                    <Rect
                      x={0}
                      y={0}
                      width={c.width}
                      height={c.height}
                      fill={c.background_color || "#02060d"}
                      listening={false}
                    />
                    {ordered.map((r) => (
                      <RegionNode
                        key={r.id}
                        region={r}
                        canvas={c}
                        selected={selectedId === r.id}
                        onSelect={() => setSelectedId(r.id)}
                        onChange={(patch) => updateRegion(r.id, patch)}
                      />
                    ))}
                  </Layer>
                </Stage>
              </div>
              <div className="text-[10px] text-slate-500">
                {mode === "render"
                  ? "Fill the slots on the right, then Render — the result appears here."
                  : "Drag to move (snaps to grid). Select a region then resize via handles or the properties panel. Higher z-index draws on top."}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Right: properties (edit) AND slot inputs (render) stay mounted —
          only visibility toggles, so switching edit<->render never wipes
          the slot inputs / generated script you already filled in. */}
      <div className="col-span-12 lg:col-span-3">
        <div className={mode === "edit" ? "" : "hidden"}>
          <PropertiesPanel
            template={template}
            region={selected}
            onTemplateChange={patchTemplate}
            onRegionChange={(patch) => {
              if (patch.slot_name)
                patch.slot_name = uniqueSlot(patch.slot_name, selectedId);
              updateRegion(selectedId, patch);
            }}
            onDeleteRegion={() => deleteRegion(selectedId)}
          />
        </div>
        <div className={mode === "render" ? "" : "hidden"}>
          {template.render_mode === "sequential" ? (
            <TimelineEditor
              template={template}
              onTemplateChange={(t) => setTemplate(t)}
              onJob={setRenderJob}
            />
          ) : (
            <SlotInputsPanel
              template={template}
              onJob={setRenderJob}
              onRegionPatch={updateRegion}
            />
          )}
        </div>
      </div>
    </div>
  );
}
