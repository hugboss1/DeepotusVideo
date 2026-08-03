// shell.jsx — App shell: Sidebar + Topbar + JobDock + view routing (ESM port)
import React, { useState as useStateSh, useEffect as useEffectSh } from 'react';
import { createPortal } from 'react-dom';
import { Icon, Button, IconButton, Badge, Logo, Progress, Thumb } from './atoms.jsx';
import { Studio } from './studio.jsx';
import { QuickScreen, NewsScreen, TemplatesScreen, LibraryScreen, SettingsScreen } from './screens.jsx';
import { SchedulerScreen } from './scheduler.jsx';
import { Splash, Onboarding } from './onboarding.jsx';
import { PERSONA_PRESETS } from './persona.jsx';
import { api, fmtDur, fmtAgo, useHealth, postFromRow, useBranding } from './api.js';

const NAV_SECTIONS = [
  { id: 'quick',     label: 'Quick',     icon: 'zap',      desc: '1-shot generators' },
  { id: 'studio',    label: 'Studio',    icon: 'flow',     desc: 'Node editor', new: true },
  { id: 'scheduler', label: 'Scheduler', icon: 'calendar', desc: 'Plan & auto-post', new: true },
  { id: 'templates', label: 'Templates', icon: 'grid',     desc: 'Spatial layouts' },
  { id: 'news',      label: 'News',      icon: 'rss',      desc: 'RSS → reel' },
  { id: 'library',   label: 'Library',   icon: 'folder',   desc: 'Assets & renders' },
  { id: 'settings',  label: 'Settings',  icon: 'cog',      desc: 'Keys, paths, persona' },
];

const SAMPLE_JOBS = [
  { id: 'job_2k1f4a', title: 'oracle_solana_pump',   provider: 'News reel · 9:16', progress: 64, etaS: 38, kind: 'render', status: 'running' },
  { id: 'job_2k1f4b', title: 'avatar_inktober_drop', provider: 'HeyGen · 9:16',    progress: 22, etaS: 110, kind: 'avatar', status: 'running' },
  { id: 'job_2k1f4c', title: 'seed_glitch_throne_v4', provider: 'Seedance · 9:16', progress: 100, etaS: 0,   kind: 'render', status: 'succeeded', dur: '00:10' },
  { id: 'job_2k1ea1', title: 'reel_jupiter_routing',  provider: 'Composition · 9:16', progress: 100, etaS: 0, kind: 'render', status: 'succeeded', dur: '00:23' },
  { id: 'job_2k1e9a', title: 'voice_test_prophet',    provider: 'ElevenLabs',        progress: 100, etaS: 0, kind: 'audio', status: 'failed', error: '401 unauthorized' },
];

/* ────────────────────── Sidebar ────────────────────── */
function Sidebar({ view, setView, collapsed, setCollapsed }) {
  const brand = useBranding();
  return (
    <aside style={{
      width: collapsed ? 64 : 232,
      background: 'var(--bg-panel)',
      borderRight: '1px solid var(--stroke)',
      display: 'flex', flexDirection: 'column',
      transition: 'width var(--dur-3) var(--ease)',
      minHeight: 0,
    }}>
      <div style={{
        height: 56, padding: collapsed ? '0 12px' : '0 14px',
        display: 'flex', alignItems: 'center', justifyContent: collapsed ? 'center' : 'space-between',
        borderBottom: '1px solid var(--stroke)',
      }}>
        <Logo compact={collapsed} size={18} />
        {!collapsed && <IconButton name="caret" iconSize={11} onClick={() => setCollapsed(true)} title="Collapse" />}
      </div>

      <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV_SECTIONS.map(s => {
          const active = view === s.id;
          return (
            <button key={s.id} onClick={() => setView(s.id)} title={collapsed ? s.label : ''} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: collapsed ? '10px' : '8px 10px',
              background: active ? 'linear-gradient(90deg, var(--cyan-soft) 0%, transparent 100%)' : 'transparent',
              border: 0, borderLeft: `2px solid ${active ? 'var(--cyan)' : 'transparent'}`,
              color: active ? 'var(--ink-strong)' : 'var(--ink)',
              borderRadius: 0, cursor: 'pointer', textAlign: 'left',
              transition: 'all var(--dur-1) var(--ease)',
              justifyContent: collapsed ? 'center' : 'flex-start',
            }}
            onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--bg-panel-2)'; }}
            onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
            >
              <Icon name={s.icon} size={16} style={{ color: active ? 'var(--cyan)' : 'var(--ink-soft)', flexShrink: 0 }} />
              {!collapsed && (
                <>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: active ? 600 : 500 }}>{s.label}</div>
                    <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{s.desc}</div>
                  </div>
                  {s.new && <Badge tone="violet">new</Badge>}
                </>
              )}
            </button>
          );
        })}
      </nav>

      {!collapsed && (
        <div style={{ padding: '0 14px 14px' }}>
          <div style={{ padding: 12, background: 'var(--bg-panel-2)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Icon name="octopus" size={14} style={{ color: 'var(--cyan)' }} />
              <span style={{ fontSize: 11.5, color: 'var(--ink-strong)' }}>{brand.tagline_1}</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)', fontStyle: 'italic' }}>{brand.tagline_2}</div>
            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-muted)' }}>v1.14.0</span>
              <Badge tone="green" dot>local</Badge>
            </div>
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="book" size={11} style={{ color: 'var(--ink-soft)' }} />
              <span style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>Guide</span>
              <span style={{ flex: 1 }} />
              {[['fr', 'FR'], ['en', 'EN']].map(([lang, label]) => (
                <a key={lang} href={`/guide/${lang}.html`} target="_blank" rel="noreferrer" style={{
                  fontSize: 10, fontFamily: 'var(--f-mono)', fontWeight: 600,
                  color: 'var(--cyan)', textDecoration: 'none',
                  padding: '2px 7px', borderRadius: 4,
                  border: '1px solid var(--stroke)', background: 'var(--bg-base)',
                }}>{label}</a>
              ))}
            </div>
          </div>
        </div>
      )}

      {collapsed && (
        <button onClick={() => setCollapsed(false)} style={{
          height: 36, margin: 8, background: 'transparent', border: 0, color: 'var(--ink-soft)', cursor: 'pointer',
          borderRadius: 'var(--r-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} title="Expand">
          <Icon name="caretR" size={14} />
        </button>
      )}
    </aside>
  );
}

/* ────────────────────── Topbar ────────────────────── */
function Topbar({ view, setCommandOpen, variant, onShowOnboarding, setView }) {
  const sec = NAV_SECTIONS.find(s => s.id === view);
  const h = useHealth();
  function tone(b) { return b ? 'green' : 'red'; }
  function dotTitle(label, set, hint) {
    return set ? `${label} configured` : `${label} missing — ${hint}`;
  }
  return (
    <header style={{
      height: 56, padding: '0 18px',
      borderBottom: '1px solid var(--stroke)',
      background: 'linear-gradient(180deg, var(--bg-panel) 0%, var(--bg-panel)dd 100%)',
      display: 'flex', alignItems: 'center', gap: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Icon name={sec.icon} size={18} style={{ color: 'var(--cyan)' }} />
        <span className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>{sec.label}</span>
        <span style={{ fontSize: 11.5, color: 'var(--ink-soft)' }}>· {sec.desc}</span>
      </div>

      <div style={{ flex: 1 }} />

      <button onClick={() => setCommandOpen(true)} style={{
        height: 32, padding: '0 10px',
        background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)',
        display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--ink-soft)',
        fontSize: 12, cursor: 'pointer', minWidth: 240,
      }}>
        <Icon name="search" size={13} />
        <span style={{ flex: 1, textAlign: 'left' }}>Quick command…</span>
        <kbd style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-muted)', background: 'var(--bg-panel-2)', padding: '1px 5px', borderRadius: 3, border: '1px solid var(--stroke)' }}>⌘K</kbd>
      </button>

      <div style={{ display: 'flex', gap: 6, cursor: 'pointer' }} title="Click to open Settings → API keys"
        onClick={() => setView && setView('settings')}>
        <Badge tone={h ? tone(h.fal_configured) : 'amber'} dot title={dotTitle('FAL_KEY', h?.fal_configured, 'add it in backend/.env then restart')}>fal</Badge>
        <Badge tone={!h ? 'amber' : !h.heygen_enabled ? 'red' : h.heygen_reachable === false ? 'amber' : 'green'} dot
          title={!h?.heygen_enabled ? dotTitle('HEYGEN_API_KEY', false, 'add it in backend/.env then restart')
                 : h.heygen_reachable === false ? `HeyGen key set but API unreachable — ${h.heygen_message || 'network/SSL issue'}`
                 : 'HeyGen reachable'}>heygen</Badge>
        <Badge tone={h ? tone(h.voiceover_enabled) : 'amber'} dot title={dotTitle('ELEVENLABS_API_KEY', h?.voiceover_enabled, 'add it in backend/.env then restart')}>voice</Badge>
        <Badge tone={h?.ok ? 'green' : 'red'} dot title={h?.ok ? `Backend v${h.version}` : 'Backend unreachable'}>{h?.ok ? `v${h.version}` : 'down'}</Badge>
      </div>
      <IconButton name="octopus" title="Replay onboarding" onClick={onShowOnboarding} />
    </header>
  );
}

/* ────────────────────── Job Dock ────────────────────── */
function JobDock({ expanded, setExpanded, variant }) {
  const [liveJobs, setLiveJobs] = useStateSh([]);
  const [confirmDel, setConfirmDel] = useStateSh(null); // job id pending confirmation
  const [preview, setPreview] = useStateSh(null); // { id, title } of job being previewed
  const refresh = React.useCallback(async () => {
    const arr = await api.listJobs(40);
    setLiveJobs(Array.isArray(arr) ? arr : []);
  }, []);
  useEffectSh(() => {
    let alive = true;
    async function tick() { if (alive) await refresh(); }
    tick();
    const t = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(t); };
  }, [refresh]);

  async function doDelete(id) {
    await api.deleteJob(id);
    setConfirmDel(null);
    refresh();
  }
  async function doRename(id, title) {
    // Persist the new render name. The backend job.title drives both the dock
    // and the Library (which reads /api/jobs titles), so this reflects there
    // automatically on the next poll.
    await api.renameJob(id, title);
    refresh();
  }
  function doCopy(j) {
    // Copy the video URL when the render is done (useful for sharing /
    // pasting elsewhere) else the job_id (useful for re-queue debugging).
    const text = j.status === 'succeeded' && j.id
      ? `${window.location.origin}/api/jobs/${j.id}/video`
      : (j.id || '');
    try { navigator.clipboard.writeText(text); } catch {}
  }

  // Normalise backend jobs to the JobCard shape, fall back to samples if
  // the queue is empty (so the UI still shows something on first run).
  const norm = liveJobs.map(j => ({
    id: j.job_id,
    title: j.title || j.image_filename || j.job_id || 'job',
    provider: (j.provider || '').replace(/^./, c => c.toUpperCase()) + (j.aspect_ratio ? ` · ${j.aspect_ratio}` : ''),
    progress: j.progress || 0,
    etaS: j.status === 'done' || j.status === 'failed' ? 0 : Math.max(0, Math.round((100 - (j.progress || 0)) * 0.6)),
    kind: j.provider === 'heygen' ? 'avatar' : j.audio_path ? 'audio' : 'render',
    status: j.status === 'done' ? 'succeeded' : j.status === 'failed' ? 'failed' : 'running',
    dur: j.duration_s ? fmtDur(j.duration_s) : '',
    error: j.error,
  }));
  const jobs = norm.length > 0 ? norm : SAMPLE_JOBS;
  const running = jobs.filter(j => j.status === 'running');
  const done = jobs.filter(j => j.status !== 'running');
  return (
    <div style={{
      height: expanded ? 280 : 64,
      background: 'var(--bg-panel)',
      borderTop: '1px solid var(--stroke-strong)',
      boxShadow: '0 -8px 24px #0006',
      display: 'flex', flexDirection: 'column',
      transition: 'height var(--dur-3) var(--ease)',
      minHeight: 0,
    }}>
      <div style={{ height: 36, padding: '0 14px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: expanded ? '1px solid var(--stroke)' : 0 }}>
        <Icon name="signal" size={14} style={{ color: 'var(--cyan)' }} />
        <span className="upper">Job dock</span>
        <Badge tone="cyan" dot>{running.length} running</Badge>
        <Badge>{done.length} recent</Badge>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: 'var(--ink-soft)' }}>
          ETA <span className="mono strong">~01:48</span> · cost <span className="mono strong" style={{ color: 'var(--amber)' }}>$0.42</span>
        </span>
        <IconButton name={expanded ? 'caret' : 'caretR'} iconSize={11} onClick={() => setExpanded(!expanded)} title={expanded ? 'Collapse' : 'Expand'} />
      </div>

      {/* Collapsed strip: 3 inline cards */}
      {!expanded ? (
        <div style={{ flex: 1, padding: '0 14px', display: 'flex', alignItems: 'center', gap: 10, overflowX: 'auto' }}>
          {[...running, ...done].slice(0, 3).map(j => <JobCardCompact key={j.id} job={j} onPreview={() => setPreview({ id: j.id, title: j.title })} onCopy={() => doCopy(j)} onDelete={() => setConfirmDel(j.id)} onRename={(t) => doRename(j.id, t)} />)}
        </div>
      ) : (
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '8px 14px' }}>
          <div className="upper" style={{ padding: '4px 0' }}>Running</div>
          {running.map(j => <JobCardWide key={j.id} job={j} onPreview={() => setPreview({ id: j.id, title: j.title })} onCopy={() => doCopy(j)} onDelete={() => setConfirmDel(j.id)} onRename={(t) => doRename(j.id, t)} confirmDel={confirmDel === j.id} onConfirm={() => doDelete(j.id)} onCancelDel={() => setConfirmDel(null)} />)}
          <div className="upper" style={{ padding: '12px 0 4px' }}>Recent</div>
          {done.map(j => <JobCardWide key={j.id} job={j} onPreview={() => setPreview({ id: j.id, title: j.title })} onCopy={() => doCopy(j)} onDelete={() => setConfirmDel(j.id)} onRename={(t) => doRename(j.id, t)} confirmDel={confirmDel === j.id} onConfirm={() => doDelete(j.id)} onCancelDel={() => setConfirmDel(null)} />)}
        </div>
      )}

      {preview && createPortal((
        <div onClick={() => setPreview(null)} style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'var(--bg-overlay)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
            borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 80px var(--cyan-soft)',
            padding: 16, display: 'flex', flexDirection: 'column', gap: 12, maxWidth: '90%', maxHeight: '92%',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Icon name="film" size={15} style={{ color: 'var(--cyan)' }} />
              <span style={{ fontSize: 12.5, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)' }}>{preview.title}</span>
              <div style={{ flex: 1 }} />
              <a href={api.jobVideoUrl(preview.id)} download style={{ textDecoration: 'none' }}><Button variant="outline" size="sm" icon="download">Download</Button></a>
              <IconButton name="close" onClick={() => setPreview(null)} />
            </div>
            <video src={api.jobVideoUrl(preview.id)} controls autoPlay
              onError={(e) => {
                const wrap = e.currentTarget.parentElement;
                e.currentTarget.style.display = 'none';
                if (wrap && !wrap.querySelector('[data-missing]')) {
                  const d = document.createElement('div');
                  d.setAttribute('data-missing', '1');
                  d.style.cssText = 'padding:40px;text-align:center;color:var(--ink-soft);font-size:12.5px;min-width:320px';
                  d.textContent = 'Video file not found on disk (the render may have been deleted). The job record still exists in the queue.';
                  wrap.appendChild(d);
                }
              }}
              style={{ maxWidth: '70vw', maxHeight: '74vh', borderRadius: 'var(--r)', background: '#000' }} />
          </div>
        </div>
      ), document.body)}
    </div>
  );
}

// Inline-editable render name: click the pencil to rename in place. Commit on
// Enter/blur, cancel on Escape. Stops propagation so editing never triggers the
// card's preview click. The new title persists via onRename (→ api.renameJob),
// which also drives the Library name.
function EditableName({ value, onRename, size = 12.5, show = true }) {
  const [editing, setEditing] = useStateSh(false);
  const [val, setVal] = useStateSh(value);
  useEffectSh(() => { setVal(value); }, [value]);
  function commit() {
    setEditing(false);
    const v = (val || '').trim();
    if (v && v !== value) onRename?.(v); else setVal(value);
  }
  if (editing) {
    return (
      <input autoFocus value={val}
        onClick={e => e.stopPropagation()}
        onChange={e => setVal(e.target.value)}
        onBlur={commit}
        onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') commit(); if (e.key === 'Escape') { setEditing(false); setVal(value); } }}
        style={{ flex: 1, minWidth: 0, fontSize: size, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)',
          background: 'var(--bg-panel-2)', border: '1px solid var(--cyan)', borderRadius: 4, padding: '1px 5px' }} />
    );
  }
  return (
    <>
      <span style={{ fontSize: size, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1, minWidth: 0 }}>{value}</span>
      {show && onRename && <IconButton name="rename" size={20} iconSize={11} title="Rename render" onClick={(e) => { e?.stopPropagation?.(); setEditing(true); }} />}
    </>
  );
}

function JobCardCompact({ job, onPreview, onCopy, onDelete, onRename }) {
  const isRun = job.status === 'running';
  const isOk = job.status === 'succeeded';
  const isErr = job.status === 'failed';
  const accent = isRun ? 'var(--cyan)' : isErr ? 'var(--red)' : 'var(--green)';
  const canPreview = isOk && !String(job.id || '').startsWith('p_'); // skip sample jobs
  // Rename real backend jobs only (not the seeded sample rows).
  const canRename = !String(job.id || '').startsWith('p_') && !String(job.id || '').startsWith('job_2k');
  return (
    <div onClick={() => canPreview && onPreview?.()} style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 10px 6px 6px',
      background: 'var(--bg-base)', border: `1px solid ${isRun ? 'var(--cyan)' : isErr ? 'var(--red)' : 'var(--stroke)'}`,
      borderRadius: 'var(--r)',
      minWidth: 320,
      cursor: canPreview ? 'pointer' : 'default',
      boxShadow: isRun ? '0 0 18px var(--cyan-soft)' : 'none',
    }}>
      <Thumb kind={job.kind === 'avatar' ? 'avatar' : 'render'} size={40} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
          <EditableName value={job.title} onRename={onRename} size={11.5} show={canRename} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'var(--ink-soft)' }}>
          <span>{job.provider}</span>
          {isRun && <><span>·</span><span className="mono" style={{ color: 'var(--cyan)' }}>{fmtS(job.etaS)}</span></>}
          {isErr && <span style={{ color: 'var(--red)' }}>· {job.error}</span>}
        </div>
        {isRun && <div style={{ marginTop: 4 }}><Progress value={job.progress} /></div>}
      </div>
      <div style={{ display: 'flex', gap: 2 }}>
        {canPreview && <IconButton name="play" size={24} iconSize={11} title="Preview" onClick={(e) => { e?.stopPropagation?.(); onPreview?.(); }} />}
        <IconButton name="copy" size={24} iconSize={11} title="Copy link / id" onClick={(e) => { e?.stopPropagation?.(); onCopy?.(); }} />
        <IconButton name="trash" size={24} iconSize={11} title="Delete" onClick={(e) => { e?.stopPropagation?.(); if (confirm('Delete this job and its files?')) onDelete?.(); }} />
      </div>
    </div>
  );
}

function JobCardWide({ job, onPreview, onCopy, onDelete, onRename, confirmDel, onConfirm, onCancelDel }) {
  const isRun = job.status === 'running';
  const isErr = job.status === 'failed';
  const canPreview = job.status === 'succeeded' && !String(job.id || '').startsWith('p_');
  const canRename = !String(job.id || '').startsWith('p_') && !String(job.id || '').startsWith('job_2k');
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '52px 1fr 200px auto', gap: 14, alignItems: 'center',
      padding: '10px 12px', marginBottom: 6,
      background: isRun ? 'var(--cyan-soft)' : 'var(--bg-base)',
      border: `1px solid ${isRun ? 'var(--cyan)' : isErr ? 'var(--red)' : 'var(--stroke)'}`,
      borderRadius: 'var(--r)',
    }}>
      <Thumb kind={job.kind === 'avatar' ? 'avatar' : job.kind === 'audio' ? 'audio' : 'render'} size={52} />
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EditableName value={job.title} onRename={onRename} size={12.5} show={canRename} />
        </div>
        <div style={{ fontSize: 11, color: 'var(--ink-soft)', display: 'flex', gap: 8, marginTop: 2 }}>
          <span>{job.provider}</span>·
          <span className="mono">{job.id}</span>
          {job.dur && <><span>·</span><span className="mono">{job.dur}</span></>}
          {isErr && <span style={{ color: 'var(--red)' }}>· {job.error}</span>}
        </div>
      </div>
      <div style={{ minWidth: 0 }}>
        {isRun && (<>
          <Progress value={job.progress} />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10.5, color: 'var(--ink-soft)' }}>
            <span className="mono">{job.progress}%</span>
            <span className="mono" style={{ color: 'var(--cyan)' }}>ETA {fmtS(job.etaS)}</span>
          </div>
        </>)}
        {!isRun && !isErr && <Badge tone="green" dot>done</Badge>}
        {isErr && <Badge tone="red" dot>failed</Badge>}
      </div>
      <div style={{ display: 'flex', gap: 4, position: 'relative' }}>
        {canPreview && <IconButton name="play" title="Preview" onClick={onPreview} />}
        {isErr && <Button variant="outline" size="sm" icon="bolt">Retry</Button>}
        <IconButton name="copy" title={job.status === 'succeeded' ? 'Copy video URL' : 'Copy job id'} onClick={onCopy} />
        <IconButton name="trash" title="Delete" onClick={onDelete} />
        {confirmDel && (
          <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 4, zIndex: 5,
            padding: 10, background: 'var(--bg-panel-2)', border: '1px solid var(--red)', borderRadius: 'var(--r)',
            boxShadow: 'var(--shadow-2)', minWidth: 220 }}>
            <div style={{ fontSize: 11.5, color: 'var(--ink-strong)', marginBottom: 6 }}>Delete this job + files?</div>
            <div style={{ display: 'flex', gap: 6 }}>
              <Button variant="danger" size="sm" icon="trash" onClick={onConfirm}>Delete</Button>
              <Button variant="ghost" size="sm" onClick={onCancelDel}>Cancel</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function fmtS(s) {
  if (!s) return '0s';
  const m = Math.floor(s / 60), r = s % 60;
  return m ? `${m}m ${r}s` : `${r}s`;
}

/* ────────────────────── Command palette ────────────────────── */
function CommandPalette({ open, onClose, setView, onShowOnboarding }) {
  const [q, setQ] = useStateSh('');
  useEffectSh(() => {
    if (!open) return;
    function h(e) { if (e.key === 'Escape') onClose(); }
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [open, onClose]);
  if (!open) return null;
  const items = [
    { l: 'Go to Studio',        icon: 'flow', go: () => { setView('studio'); onClose(); } },
    { l: 'Go to Scheduler',     icon: 'calendar', go: () => { setView('scheduler'); onClose(); } },
    { l: 'Go to Quick',         icon: 'zap',  go: () => { setView('quick'); onClose(); } },
    { l: 'Go to News',          icon: 'rss',  go: () => { setView('news'); onClose(); } },
    { l: 'Replay onboarding',   icon: 'octopus', go: () => { onShowOnboarding(); onClose(); } },
    { l: 'New News reel graph', icon: 'sparkle', go: () => { setView('studio'); onClose(); } },
    { l: 'New Avatar post graph', icon: 'mic', go: () => { setView('studio'); onClose(); } },
    { l: 'Schedule a post for tomorrow', icon: 'send', go: () => { setView('scheduler'); onClose(); } },
    { l: 'Open last render',    icon: 'film', go: () => { setView('library'); onClose(); } },
    { l: 'Settings · Connected accounts', icon: 'link',  go: () => { setView('settings'); onClose(); } },
    { l: 'Settings · API keys', icon: 'cog',  go: () => { setView('settings'); onClose(); } },
  ].filter(i => !q || i.l.toLowerCase().includes(q.toLowerCase()));
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, background: 'var(--bg-overlay)',
      backdropFilter: 'blur(6px)', zIndex: 50,
      display: 'flex', justifyContent: 'center', paddingTop: 100,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 520, maxHeight: 480,
        background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
        borderRadius: 'var(--r-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-2)',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name="search" size={16} style={{ color: 'var(--ink-soft)' }} />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Type a command, node, or graph…" style={{ flex: 1, fontSize: 14, color: 'var(--ink-strong)' }} />
          <kbd style={{ fontSize: 10, fontFamily: 'var(--f-mono)', color: 'var(--ink-muted)', background: 'var(--bg-base)', padding: '2px 5px', borderRadius: 3, border: '1px solid var(--stroke)' }}>esc</kbd>
        </div>
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 6 }}>
          {items.map((it, i) => (
            <button key={i} onClick={it.go} style={{
              width: '100%', padding: '9px 12px', display: 'flex', alignItems: 'center', gap: 12,
              background: i === 0 ? 'var(--cyan-soft)' : 'transparent',
              color: i === 0 ? 'var(--ink-strong)' : 'var(--ink)',
              border: 0, borderRadius: 'var(--r-sm)', cursor: 'pointer', fontSize: 13, textAlign: 'left',
            }}>
              <Icon name={it.icon} size={14} style={{ color: i === 0 ? 'var(--cyan)' : 'var(--ink-soft)' }} />
              {it.l}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── App (full shell) ────────────────────── */
// URL deep-links: ?view=quick|studio|scheduler|templates|news|library|settings
// jumps straight to a screen; ?nosplash=1 skips splash + onboarding. Used by
// the guide's screenshot pipeline and handy for bookmarks.
const _urlParams = (() => {
  try { return new URLSearchParams(window.location.search); } catch { return new URLSearchParams(); }
})();
const _VIEWS = ['quick','studio','scheduler','templates','news','library','settings'];
const _urlView = _VIEWS.includes(_urlParams.get('view')) ? _urlParams.get('view') : null;
const _noSplash = _urlParams.get('nosplash') === '1';

function DeepotusApp({ variant = 'abyssal', initialView = 'studio', initialSidebar = false, initialDock = false, motionOn = true }) {
  const [view, setView] = useStateSh(_urlView || initialView);
  const [sidebarCollapsed, setSidebarCollapsed] = useStateSh(initialSidebar);
  const [dockExpanded, setDockExpanded] = useStateSh(initialDock);
  const [cmdOpen, setCmdOpen] = useStateSh(false);

  // Boot flow: splash → onboarding (only once per app instance per variant).
  const [booting, setBooting] = useStateSh(!_noSplash);
  const [showOnboarding, setShowOnboarding] = useStateSh(false);

  // Shared state across Studio / Scheduler / Library. Posts live in the
  // backend (scheduled_posts table); we hydrate here and re-poll every 60s
  // so the schedule loop's status flips (scheduled -> ready/posted) show up.
  const [posts, setPosts] = useStateSh([]);
  const [uploads, setUploads] = useStateSh([]); // user-uploaded library images

  async function reloadPosts() {
    const rows = await api.listSchedule();
    setPosts((Array.isArray(rows) ? rows : []).map(postFromRow));
  }
  useEffectSh(() => {
    reloadPosts();
    const t = setInterval(reloadPosts, 60000);
    return () => clearInterval(t);
  }, []);

  // Persona library (Onboarding / Settings / Scheduler / News all read it).
  const [personas, setPersonas] = useStateSh(() => (PERSONA_PRESETS || []).slice());
  const [activePersonaId, setActivePersonaId] = useStateSh('deepotus');
  function savePersona(p) {
    setPersonas(list => {
      const exists = list.some(x => x.id === p.id);
      const next = exists ? list.map(x => x.id === p.id ? { ...x, ...p } : x) : [...list, p];
      return next;
    });
    setActivePersonaId(p.id);
  }

  async function scheduleFromRender(opts) {
    // Tomorrow 09:00 local, persisted in the backend.
    const runAt = new Date();
    runAt.setDate(runAt.getDate() + 1);
    runAt.setHours(9, 0, 0, 0);
    const r = await api.createScheduledPost({
      title: opts.title || 'New post from Studio',
      caption: opts.caption || 'New drop from the deep. 🐙',
      channels: ['x', 'telegram'],
      run_at: runAt.toISOString(),
      status: 'draft',
      mode: 'assisted',
      job_id: opts.jobId || null,
    });
    await reloadPosts();
    setView('scheduler');
    // Defer so SchedulerScreen mounts before it tries to select.
    if (r?.id) {
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('deepotus:select-post', { detail: { id: r.id } }));
      }, 50);
    }
  }

  useEffectSh(() => {
    function h(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(o => !o); }
    }
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  // Cross-screen navigation (e.g. Templates → "Open in Studio").
  useEffectSh(() => {
    function nav(e) {
      const v = e?.detail?.view;
      if (v && _VIEWS.includes(v)) setView(v);
    }
    window.addEventListener('deepotus:navigate', nav);
    return () => window.removeEventListener('deepotus:navigate', nav);
  }, []);

  return (
    <div className="deepotus" data-variant={variant} style={{
      width: '100%', height: '100%',
      display: 'grid', gridTemplateColumns: 'auto 1fr', gridTemplateRows: '1fr auto',
      background: 'var(--bg-base)',
      overflow: 'hidden', position: 'relative',
    }}>
      <div style={{ gridRow: '1 / 3' }}>
        <Sidebar view={view} setView={setView} collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
      </div>

      <main style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <Topbar view={view} setView={setView} setCommandOpen={setCmdOpen} variant={variant} onShowOnboarding={() => setShowOnboarding(true)} />
        <div style={{ flex: 1, minHeight: 0, position: 'relative' }} className={motionOn ? '' : 'no-motion'}>
          {view === 'studio'    && <Studio variant={variant} onScheduleRender={scheduleFromRender} />}
          {view === 'quick'     && <QuickScreen variant={variant} activePersona={personas.find(p => p.id === activePersonaId)} />}
          {view === 'scheduler' && <SchedulerScreen variant={variant} posts={posts} setPosts={setPosts} reloadPosts={reloadPosts} />}
          {view === 'news'      && <NewsScreen variant={variant} />}
          {view === 'templates' && <TemplatesScreen variant={variant} />}
          {view === 'library'   && <LibraryScreen variant={variant} uploads={uploads} setUploads={setUploads} />}
          {view === 'settings'  && <SettingsScreen variant={variant} personas={personas} activePersonaId={activePersonaId} setActivePersonaId={setActivePersonaId} savePersona={savePersona} />}
        </div>
      </main>

      <div style={{ gridColumn: '2 / 3' }}>
        <JobDock expanded={dockExpanded} setExpanded={setDockExpanded} variant={variant} />
      </div>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} setView={setView} onShowOnboarding={() => setShowOnboarding(true)} />

      {booting && <Splash onDone={() => { setBooting(false); setShowOnboarding(true); }} />}
      {!booting && showOnboarding && <Onboarding onDone={() => setShowOnboarding(false)} onSkip={() => setShowOnboarding(false)} personas={personas} activePersonaId={activePersonaId} setActivePersonaId={setActivePersonaId} savePersona={savePersona} />}
    </div>
  );
}

export { DeepotusApp, NAV_SECTIONS, SAMPLE_JOBS };
