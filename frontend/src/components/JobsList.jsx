import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

const STATUS_COLORS = {
  queued: "text-slate-400",
  prompt_building: "text-bio-cyan",
  uploading_image: "text-bio-cyan",
  generating_video: "text-bio-cyan",
  downloading_video: "text-bio-cyan",
  generating_voiceover: "text-bio-cyan",
  merging: "text-bio-cyan",
  done: "text-green-400",
  failed: "text-red-400",
};

export function JobsList({ onClone }) {
  const [jobs, setJobs] = useState([]);
  const [expanded, setExpanded] = useState(null);          // job_id or batch_id
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [compareMode, setCompareMode] = useState(null);    // batch_id when comparing
  const toast = useToast();

  async function refresh() {
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch (e) {
      console.error(e);
    }
  }

  useEffect(() => {
    refresh();
    const i = setInterval(refresh, 2000);
    return () => clearInterval(i);
  }, []);

  // Group jobs: those with batch_id are clustered, others are singletons.
  // Each "group" is { type: 'single'|'batch', key, jobs[], headline_job }
  const groups = useMemo(() => {
    const byBatch = new Map();
    const singles = [];
    for (const j of jobs) {
      if (j.batch_id) {
        if (!byBatch.has(j.batch_id)) byBatch.set(j.batch_id, []);
        byBatch.get(j.batch_id).push(j);
      } else {
        singles.push({ type: "single", key: j.job_id, jobs: [j], headline: j });
      }
    }
    const batches = [];
    for (const [bid, bjobs] of byBatch.entries()) {
      // Sort by batch_index ascending
      bjobs.sort((a, b) => (a.batch_index ?? 0) - (b.batch_index ?? 0));
      batches.push({
        type: "batch",
        key: bid,
        jobs: bjobs,
        headline: bjobs[0],
      });
    }
    // Merge & sort by most recent created_at within group
    const all = [...singles, ...batches];
    all.sort((a, b) => {
      const ta = Math.max(...a.jobs.map((j) => new Date(j.created_at).getTime()));
      const tb = Math.max(...b.jobs.map((j) => new Date(j.created_at).getTime()));
      return tb - ta;
    });
    return all;
  }, [jobs]);

  async function copyText(text, label = "Copied") {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(label);
    } catch (e) {
      toast.error(`Copy failed: ${e.message}`);
    }
  }

  async function handleDelete(jobId) {
    try {
      await api.deleteJob(jobId);
      toast.success("Job deleted");
      setConfirmDelete(null);
      setExpanded(null);
      refresh();
    } catch (e) {
      toast.error(`Delete failed: ${e.message}`);
    }
  }

  async function handleDeleteBatch(batchId) {
    try {
      const res = await api.deleteBatch(batchId);
      toast.success(`Batch deleted (${res.jobs_deleted} jobs)`);
      setConfirmDelete(null);
      setExpanded(null);
      refresh();
    } catch (e) {
      toast.error(`Batch delete failed: ${e.message}`);
    }
  }

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-3">
        <div className="panel-title mb-0">Job Queue</div>
        <span className="text-xs text-slate-500">
          {jobs.length} jobs · {groups.length} {groups.length === 1 ? "group" : "groups"}
        </span>
      </div>

      {jobs.length === 0 && (
        <div className="text-sm text-slate-500 text-center py-6">
          Aucun job pour l'instant.
        </div>
      )}

      <div className="space-y-2 max-h-[680px] overflow-y-auto pr-1">
        {groups.map((g) => {
          if (g.type === "single") {
            return (
              <SingleJobRow
                key={g.key}
                job={g.headline}
                expanded={expanded === g.key}
                onToggle={() => setExpanded(expanded === g.key ? null : g.key)}
                onCopyText={copyText}
                onClone={onClone}
                onConfirmDelete={() => setConfirmDelete({ type: "job", id: g.key })}
                isConfirmingDelete={confirmDelete?.type === "job" && confirmDelete?.id === g.key}
                onCancelDelete={() => setConfirmDelete(null)}
                onDelete={() => handleDelete(g.key)}
                onRefresh={refresh}
              />
            );
          }
          return (
            <BatchGroupRow
              key={g.key}
              batch={g}
              expanded={expanded === g.key}
              onToggle={() => setExpanded(expanded === g.key ? null : g.key)}
              compareMode={compareMode === g.key}
              onToggleCompare={() => setCompareMode(compareMode === g.key ? null : g.key)}
              onCopyText={copyText}
              onClone={onClone}
              onConfirmDelete={() => setConfirmDelete({ type: "batch", id: g.key })}
              isConfirmingDelete={confirmDelete?.type === "batch" && confirmDelete?.id === g.key}
              onCancelDelete={() => setConfirmDelete(null)}
              onDelete={() => handleDeleteBatch(g.key)}
            />
          );
        })}
      </div>
    </div>
  );
}

/* ================== SINGLE JOB ROW ================== */

function SingleJobRow({ job: j, expanded, onToggle, onCopyText, onClone,
                        onConfirmDelete, isConfirmingDelete, onCancelDelete, onDelete,
                        onRefresh }) {
  return (
    <div className="border border-deep-700/50 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-3 hover:bg-deep-800/40 transition-colors"
      >
        <JobRowHeader job={j} />
      </button>
      {expanded && (
        <JobDetailBody
          job={j}
          onCopyText={onCopyText}
          onClone={onClone}
          onConfirmDelete={onConfirmDelete}
          isConfirmingDelete={isConfirmingDelete}
          onCancelDelete={onCancelDelete}
          onDelete={onDelete}
          onRefresh={onRefresh}
        />
      )}
    </div>
  );
}

/* ================== BATCH GROUP ROW ================== */

function BatchGroupRow({ batch, expanded, onToggle, compareMode, onToggleCompare,
                         onCopyText, onClone, onConfirmDelete, isConfirmingDelete,
                         onCancelDelete, onDelete }) {
  const jobs = batch.jobs;
  const headline = batch.headline;
  const total = jobs.length;
  const done = jobs.filter((j) => j.status === "done").length;
  const failed = jobs.filter((j) => j.status === "failed").length;
  const inFlight = total - done - failed;
  const seeds = jobs.map((j) => j.seed).filter((s) => s != null);
  const seedRange = seeds.length > 0 ? `${Math.min(...seeds)}–${Math.max(...seeds)}` : "—";

  const overallProgress = Math.round(
    jobs.reduce((acc, j) => acc + (j.progress || 0), 0) / total
  );

  return (
    <div className="border border-bio-violet/40 rounded-lg overflow-hidden bg-bio-violet/5">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-3 hover:bg-bio-violet/10 transition-colors text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="badge bg-bio-violet/20 border-bio-violet/40 text-bio-violet">
              ⚡ BATCH · {total}
            </span>
            <span className="text-xs text-slate-400 truncate">
              {headline.image_filename}
              {headline.image_filename_end && (
                <span className="text-bio-violet"> → end</span>
              )}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            seeds {seedRange} · {done}/{total} done
            {failed > 0 && <span className="text-red-400"> · {failed} failed</span>}
            {inFlight > 0 && <span className="text-bio-cyan"> · {inFlight} in flight</span>}
          </div>
          <div className="mt-1.5 h-1 bg-deep-800 rounded-full overflow-hidden">
            <div
              className="h-full transition-all duration-500 bg-gradient-to-r from-bio-cyan to-bio-violet"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>
        <span className="text-xs font-mono text-slate-500">{overallProgress}%</span>
      </button>

      {expanded && (
        <div className="border-t border-bio-violet/30 p-3 space-y-3 bg-deep-950/40">
          {/* Compare toggle and batch actions */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onToggleCompare}
              disabled={done < 2}
              className={`btn-ghost !text-xs ${compareMode ? "!bg-bio-violet/30 !border-bio-violet" : ""} disabled:opacity-40`}
              title={done < 2 ? "Need at least 2 done jobs to compare" : ""}
            >
              {compareMode ? "▣ Hide comparison" : `▦ Compare (${done} done)`}
            </button>
            <button
              onClick={onConfirmDelete}
              className="btn-ghost !text-xs hover:!border-red-500/40 hover:!text-red-300"
              title="Delete entire batch (all variations)"
            >
              🗑 Delete batch
            </button>
            <span className="text-[10px] text-slate-500 font-mono ml-auto">
              {batch.key.slice(0, 8)}…
            </span>
          </div>

          {/* Confirm batch delete */}
          {isConfirmingDelete && (
            <div className="p-2 rounded border border-red-500/40 bg-red-500/10 text-xs space-y-2">
              <div className="text-red-200">
                Delete this entire batch ({total} jobs and their files)? This cannot be undone.
              </div>
              <div className="flex gap-2">
                <button
                  onClick={onDelete}
                  className="btn-ghost flex-1 !bg-red-500/30 !border-red-500/60 !text-red-100"
                >
                  Yes, delete all {total}
                </button>
                <button onClick={onCancelDelete} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Compare grid (videos side-by-side) */}
          {compareMode && (
            <div className={`grid gap-2 ${total >= 4 ? "grid-cols-2" : "grid-cols-1"}`}>
              {jobs.filter(j => j.status === "done" && j.final_video_path).map((j) => (
                <CompareCell key={j.job_id} job={j} onCopyText={onCopyText} onClone={onClone} />
              ))}
            </div>
          )}

          {/* List view of all variations */}
          {!compareMode && (
            <div className="space-y-1.5">
              {jobs.map((j) => (
                <VariationRow key={j.job_id} job={j} onClone={onClone} onCopyText={onCopyText} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ================== Variation row inside expanded batch ================== */

function VariationRow({ job: j, onClone, onCopyText }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-deep-700/40 rounded-md overflow-hidden bg-deep-900/60">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 p-2 hover:bg-deep-800/60 text-left"
      >
        <span className="text-[10px] font-mono text-bio-violet w-6">
          #{(j.batch_index ?? 0) + 1}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-mono uppercase ${STATUS_COLORS[j.status] || "text-slate-400"}`}>
              {j.status}
            </span>
            {j.seed != null && (
              <span className="text-[10px] font-mono text-slate-500">
                seed {j.seed}
              </span>
            )}
          </div>
          {j.current_step && j.status !== "done" && j.status !== "failed" && (
            <div className="text-[9px] text-slate-500 truncate mt-0.5">{j.current_step}</div>
          )}
          <div className="mt-1 h-0.5 bg-deep-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                j.status === "failed" ? "bg-red-500" :
                j.status === "done" ? "bg-green-500" :
                "bg-bio-cyan"
              }`}
              style={{ width: `${j.progress || 0}%` }}
            />
          </div>
        </div>
        <span className="text-[10px] font-mono text-slate-600">{j.progress || 0}%</span>
      </button>

      {open && (
        <div className="px-2 pb-2 pt-1 space-y-2">
          {j.status === "done" && j.final_video_path && (
            <video
              src={api.jobVideoUrl(j.job_id)}
              controls
              className="w-full rounded bg-black"
            />
          )}
          {j.error && (
            <div className="text-[10px] text-red-400 bg-red-500/10 border border-red-500/30 rounded p-1.5 font-mono">
              {j.error}
            </div>
          )}
          <div className="flex gap-1.5">
            {j.status === "done" && (
              <a href={api.jobVideoUrl(j.job_id)} download className="btn-ghost flex-1 text-center !text-[10px]">
                ⬇ MP4
              </a>
            )}
            {(j.status === "done" || j.status === "failed") && (
              <button onClick={() => onClone?.(j)} className="btn-ghost flex-1 !text-[10px]">
                🔁 Clone
              </button>
            )}
            {j.seed != null && (
              <button onClick={() => onCopyText(String(j.seed), `Seed ${j.seed} copied`)} className="btn-ghost flex-1 !text-[10px]">
                📋 Seed
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ================== Compare cell (one video in compare grid) ================== */

function CompareCell({ job: j, onCopyText, onClone }) {
  return (
    <div className="border border-deep-700/40 rounded-md overflow-hidden bg-deep-950/60 p-2">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono text-bio-violet">
          #{(j.batch_index ?? 0) + 1} · seed {j.seed}
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => onClone?.(j)}
            className="text-[10px] text-slate-400 hover:text-bio-cyan"
            title="Clone this variation"
          >
            🔁
          </button>
          <a
            href={api.jobVideoUrl(j.job_id)}
            download
            className="text-[10px] text-slate-400 hover:text-bio-cyan"
            title="Download MP4"
          >
            ⬇
          </a>
        </div>
      </div>
      <video
        src={api.jobVideoUrl(j.job_id)}
        controls
        className="w-full rounded bg-black"
      />
    </div>
  );
}

/* ================== Reusable header for single jobs ================== */

function JobRowHeader({ job: j }) {
  return (
    <>
      <div className="flex-1 min-w-0 text-left">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-mono uppercase ${STATUS_COLORS[j.status] || "text-slate-400"}`}>
            {j.status}
          </span>
          {j.provider && j.provider !== "seedance" && (
            <span className={`badge text-[9px] ${
              j.provider === "heygen" ? "bg-bio-violet/20 border-bio-violet/40 text-bio-violet" :
              j.provider === "composition" ? "bg-glow-amber/20 border-glow-amber/40 text-glow-amber" :
              ""
            }`}>
              {j.provider === "heygen" ? "🎤 HG" : "⚡ COMP"}
            </span>
          )}
          <span className="text-xs text-slate-500 truncate">
            {j.title || j.image_filename}
          </span>
          {j.image_filename_end && <span className="text-[10px] text-bio-violet">→ end</span>}
        </div>
        {j.current_step && j.status !== "done" && j.status !== "failed" && (
          <div className="text-[10px] text-slate-500 mt-0.5 truncate">{j.current_step}</div>
        )}
        <div className="mt-1.5 h-1 bg-deep-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              j.status === "failed" ? "bg-red-500" :
              j.status === "done" ? "bg-green-500" :
              "bg-gradient-to-r from-bio-cyan to-bio-violet"
            }`}
            style={{ width: `${j.progress || 0}%` }}
          />
        </div>
      </div>
      <span className="text-xs font-mono text-slate-500">{j.progress || 0}%</span>
    </>
  );
}

/* ================== Reusable detail body for single jobs ================== */

function RenameField({ job: j, onRefresh }) {
  const [val, setVal] = useState(j.title || "");
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  async function save() {
    setSaving(true);
    try {
      await api.renameJob(j.job_id, val);
      toast.success("Render renamed");
      onRefresh && onRefresh();
    } catch (e) {
      toast.error(`Rename failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-bio-cyan/60 mb-1">
        Render name
      </div>
      <div className="flex gap-1.5">
        <input
          className="input flex-1 !py-1 !text-xs"
          placeholder="name this render…"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
        />
        <button
          onClick={save}
          disabled={saving || val === (j.title || "")}
          className="btn-ghost !text-[10px] disabled:opacity-40"
        >
          {saving ? "…" : "Save"}
        </button>
      </div>
    </div>
  );
}

function JobDetailBody({ job: j, onCopyText, onClone,
                         onConfirmDelete, isConfirmingDelete, onCancelDelete, onDelete,
                         onRefresh }) {
  return (
    <div className="border-t border-deep-700/50 p-3 space-y-3 bg-deep-950/40">
      <RenameField job={j} onRefresh={onRefresh} />

      {j.error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded p-2 font-mono whitespace-pre-wrap">
          {j.error}
        </div>
      )}

      {j.status === "done" && j.final_video_path && (
        <video src={api.jobVideoUrl(j.job_id)} controls className="w-full rounded-lg bg-black" />
      )}

      {j.caption_text && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="text-[10px] uppercase tracking-wider text-bio-cyan/60">
              X Caption (ready to paste)
            </div>
            <button
              onClick={() => onCopyText(j.caption_text, "Caption copied")}
              className="btn-ghost !py-0.5 !px-2 !text-[10px]"
            >
              📋 Copy
            </button>
          </div>
          <div className="text-xs whitespace-pre-wrap p-2 rounded bg-deep-950/60 border border-deep-700/40">
            {j.caption_text}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-[11px]">
        {j.seed != null && (
          <Meta label="Seed">
            <button
              onClick={() => onCopyText(String(j.seed), "Seed copied")}
              className="font-mono text-bio-cyan hover:underline"
            >
              {j.seed}
            </button>
          </Meta>
        )}
        {j.template_id && <Meta label="Template" value={j.template_id} />}
        {j.style && <Meta label="Style" value={j.style} />}
        {j.duration_s && <Meta label="Duration" value={`${j.duration_s}s`} />}
        {j.aspect_ratio && <Meta label="Aspect" value={j.aspect_ratio} />}
        {j.voiceover_language && <Meta label="VO" value={j.voiceover_language} />}
        {j.voice_mode && <Meta label="Voice mode" value={j.voice_mode} />}
        {j.provider && <Meta label="Provider" value={j.provider} />}
        {j.composition_layout && <Meta label="Composition" value={j.composition_layout} />}
      </div>

      {j.final_prompt && (
        <details className="text-[11px]">
          <summary className="text-slate-400 cursor-pointer hover:text-bio-cyan">
            ▸ Show full prompt
          </summary>
          <div className="mt-2 p-2 rounded bg-deep-950/60 border border-deep-700/40 font-mono whitespace-pre-wrap text-slate-300">
            {j.final_prompt}
          </div>
        </details>
      )}

      <div className="flex flex-wrap gap-2 pt-2 border-t border-deep-700/40">
        {j.status === "done" && j.final_video_path && (
          <a href={api.jobVideoUrl(j.job_id)} download className="btn-ghost flex-1 text-center !text-xs">
            ⬇ Download MP4
          </a>
        )}
        {(j.status === "done" || j.status === "failed") && (
          <button onClick={() => onClone?.(j)} className="btn-ghost flex-1 !text-xs">
            🔁 Clone
          </button>
        )}
        <button
          onClick={onConfirmDelete}
          className="btn-ghost !text-xs hover:!border-red-500/40 hover:!text-red-300"
        >
          🗑
        </button>
      </div>

      {isConfirmingDelete && (
        <div className="p-2 rounded border border-red-500/40 bg-red-500/10 text-xs space-y-2">
          <div className="text-red-200">Delete this job and its files? This cannot be undone.</div>
          <div className="flex gap-2">
            <button
              onClick={onDelete}
              className="btn-ghost flex-1 !bg-red-500/30 !border-red-500/60 !text-red-100"
            >
              Yes, delete
            </button>
            <button onClick={onCancelDelete} className="btn-ghost flex-1">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="text-[10px] text-slate-600 font-mono">
        {j.job_id} · {j.created_at}
      </div>
    </div>
  );
}

function Meta({ label, value, children }) {
  return (
    <div className="p-1.5 rounded bg-deep-950/60 border border-deep-700/40">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-slate-300 truncate">{children || value}</div>
    </div>
  );
}
