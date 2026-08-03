// scheduler.jsx — Post scheduler wired to /api/schedule (v1.9).
// Data model: posts carry a real `runAt` Date (local). The visible week is
// weekStart + 7 days; posts outside it simply don't render in week view.
// Status vocabulary (consistent everywhere):
//   draft -> muted   scheduled -> cyan   ready -> amber (needs action)
//   posted -> green  failed -> red
import React, { useState as useStateSch, useMemo as useMemoSch, useEffect as useEffectSch, useRef as useRefSch } from 'react';
import { Icon, Button, IconButton, Input, Badge, Toggle, InspectorSection, Field, Select, Thumb } from './atoms.jsx';
import { api, postFromRow, useHealth, urlParam } from './api.js';

/* Channel metadata */
const CHANNELS = {
  x:         { id: 'x',         label: 'X',          icon: 'channelX',         color: '#e6f1ff', bg: '#0f1c30', limit: 280 },
  telegram:  { id: 'telegram',  label: 'Telegram',   icon: 'channelTelegram',  color: '#29b6f6', bg: '#0e2335', limit: 4096 },
  youtube:   { id: 'youtube',   label: 'YouTube',    icon: 'channelYoutube',   color: '#ef4444', bg: '#2a0d0d', limit: 5000 },
  instagram: { id: 'instagram', label: 'Instagram',  icon: 'channelInstagram', color: '#c084fc', bg: '#241333', limit: 2200 },
};
const CHANNEL_LIST = Object.values(CHANNELS);

/* Quick emojis for captions (Telegram / X / etc.). */
const CAPTION_EMOJIS = ['❤️', '🔥', '🚀', '😍', '🎉', '👍', '💯'];

/* Telegram Premium pack — branded one-tap tags per content vertical. Inserts
   "emoji + label" into the caption so each post is instantly tagged. */
const TELEGRAM_PREMIUM_PACK = [
  { e: '🐙', label: 'Deepotus Protocol', icon: '/pack/deepotus-protocol.png' },
  { e: '🌊', label: 'Rippled Signal',    icon: '/pack/rippled-signal.png' },
  { e: '👁️', label: 'Prophet' },
  { e: '📖', label: 'Chapter Drop' },
  { e: '🎴', label: 'Board Game' },
  { e: '🎲', label: 'D&D' },
  { e: '📱', label: 'Mobile Devlog' },
  { e: '🪙', label: '$DEEP' },
  { e: '🧬', label: 'Gencoin' },
  { e: '🎬', label: 'Video Engine' },
];

/* Pack chip glyph: custom icon image when present (falls back to the unicode
   emoji if the asset is missing). */
function PackIcon({ icon, emoji, size = 16 }) {
  const [err, setErr] = useStateSch(false);
  if (icon && !err) {
    return <img src={icon} alt="" width={size} height={size} onError={() => setErr(true)}
      style={{ objectFit: 'contain', borderRadius: 4, display: 'block' }} />;
  }
  return <span style={{ fontSize: 13 }}>{emoji}</span>;
}

const STATUS_COLOR = {
  posted:    'var(--green)',
  failed:    'var(--red)',
  ready:     'var(--amber)',
  scheduled: 'var(--cyan)',
  draft:     'var(--ink-muted)',
};
function statusColor(s) { return STATUS_COLOR[s] || 'var(--ink-muted)'; }

/* ---- date helpers (all local time) ---- */
function mondayOf(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return x;
}
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function dayLabel(weekStart, i) {
  const d = addDays(weekStart, i);
  return { day: d.getDate(), short: ['MON','TUE','WED','THU','FRI','SAT','SUN'][i], month: d.toLocaleString('en', { month: 'short' }), date: d };
}
function fmtRange(weekStart) {
  const end = addDays(weekStart, 6);
  const m1 = weekStart.toLocaleString('en', { month: 'short' });
  const m2 = end.toLocaleString('en', { month: 'short' });
  return m1 === m2
    ? `${m1} ${weekStart.getDate()} to ${end.getDate()}, ${end.getFullYear()}`
    : `${m1} ${weekStart.getDate()} to ${m2} ${end.getDate()}, ${end.getFullYear()}`;
}
function setTimeOn(date, hhmm) {
  const [hh, mm] = (hhmm || '12:00').split(':');
  const x = new Date(date);
  x.setHours(Number(hh) || 12, Number(mm) || 0, 0, 0);
  return x;
}

function SchedulerScreen({ variant, posts: postsProp, setPosts: setPostsProp, reloadPosts }) {
  const [localPosts, setLocalPosts] = useStateSch([]);
  const posts = postsProp ?? localPosts;
  const setPosts = setPostsProp ?? setLocalPosts;
  const [selectedId, setSelectedId] = useStateSch(null);
  const [view, setView] = useStateSch('week');
  const [weekOffset, setWeekOffset] = useStateSch(0);
  const [monthOffset, setMonthOffset] = useStateSch(0);
  // ?plan=generate|import opens the modal straight away (guide screenshots + bookmarks).
  const _planParam = urlParam('plan');
  const [planOpen, setPlanOpen] = useStateSch(_planParam === 'generate' || _planParam === 'import');
  const [jobs, setJobs] = useStateSch([]);
  const [captionPack, setCaptionPack] = useStateSch(null);
  const h = useHealth();

  // Load the (editable) caption pack once; normalize to the {e,label,icon}
  // shape the inspector renders. Falls back to the built-in defaults.
  useEffectSch(() => {
    api.getCaptionPack().then(r => {
      if (r?.pack?.length) setCaptionPack(r.pack.map(x => ({ id: x.id, e: x.emoji, label: x.label, icon: x.icon || undefined })));
    });
  }, []);

  const weekStart = useMemoSch(() => addDays(mondayOf(new Date()), weekOffset * 7), [weekOffset]);

  // Done renders for the "attach a render" picker. Poll so a render produced
  // from the inspector (Produce) surfaces here within a few seconds and can be
  // previewed before the post is sent / automated (human-in-the-loop).
  useEffectSch(() => {
    let alive = true;
    const pull = () => api.listJobs(60).then(arr => {
      if (!alive) return;
      setJobs((Array.isArray(arr) ? arr : []).filter(j => j.status === 'done' && j.final_video_path));
    });
    pull();
    const t = setInterval(pull, 8000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // Listen for "select this freshly-created post" event from Studio.
  useEffectSch(() => {
    function hh(e) { const id = e?.detail?.id; if (id) setSelectedId(id); }
    window.addEventListener('deepotus:select-post', hh);
    return () => window.removeEventListener('deepotus:select-post', hh);
  }, []);

  // Deep-link ?post=<id|first> auto-selects a post (guide screenshots + bookmarks).
  useEffectSch(() => {
    const want = urlParam('post');
    if (!want || selectedId || !posts.length) return;
    const target = (want === 'first' || want === '1') ? posts[0] : posts.find(p => p.id === want);
    if (target) setSelectedId(target.id);
  }, [posts.length]);

  const selected = posts.find(p => p.id === selectedId);

  // Optimistic local update + debounced PATCH per post.
  const patchTimers = useRefSch({});
  function persistPatch(id, uiPatch) {
    const body = {};
    if ('title' in uiPatch) body.title = uiPatch.title;
    if ('caption' in uiPatch) body.caption = uiPatch.caption;
    if ('channels' in uiPatch) body.channels = uiPatch.channels;
    if ('status' in uiPatch) body.status = uiPatch.status;
    if ('mode' in uiPatch) body.mode = uiPatch.mode;
    if ('jobId' in uiPatch) body.job_id = uiPatch.jobId;
    if ('sourceImage' in uiPatch) body.source_image = uiPatch.sourceImage;
    if ('runAt' in uiPatch) body.run_at = uiPatch.runAt.toISOString();
    clearTimeout(patchTimers.current[id]);
    patchTimers.current[id] = setTimeout(() => { api.updateScheduledPost(id, body); }, 500);
  }
  function updateSelected(patch) {
    if (!selectedId) return;
    setPosts(ps => ps.map(p => p.id === selectedId ? { ...p, ...patch } : p));
    persistPatch(selectedId, patch);
  }
  function toggleChannel(ch) {
    if (!selected) return;
    const has = selected.channels.includes(ch);
    const channels = has ? selected.channels.filter(c => c !== ch) : [...selected.channels, ch];
    updateSelected({ channels });
  }
  async function createPost(dayIdx) {
    const runAt = setTimeOn(addDays(weekStart, dayIdx ?? 0), '12:00');
    const r = await api.createScheduledPost({
      title: 'Untitled post', caption: '', channels: ['x'],
      run_at: runAt.toISOString(), status: 'draft', mode: 'assisted',
    });
    if (r?.id) {
      await (reloadPosts?.() ?? Promise.resolve());
      setSelectedId(r.id);
    }
  }
  async function deleteSelected() {
    if (!selected) return;
    await api.deleteScheduledPost(selected.id);
    setSelectedId(null);
    reloadPosts?.();
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', height: '100%', minHeight: 0, background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <SchedulerHeader
          view={view} setView={setView} count={posts.length}
          range={view === 'month'
            ? new Date(new Date().getFullYear(), new Date().getMonth() + monthOffset, 1).toLocaleString('en', { month: 'long', year: 'numeric' })
            : fmtRange(weekStart)}
          onPrev={() => view === 'month' ? setMonthOffset(o => o - 1) : setWeekOffset(o => o - 1)}
          onNext={() => view === 'month' ? setMonthOffset(o => o + 1) : setWeekOffset(o => o + 1)}
          onToday={() => { setWeekOffset(0); setMonthOffset(0); }}
          onNew={() => createPost(0)}
          onPlan={() => setPlanOpen(true)}
        />
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 18 }} className="scroll">
          {view === 'month'
            ? <MonthGrid posts={posts} selectedId={selectedId} onSelect={setSelectedId} monthOffset={monthOffset} />
            : <WeekGrid posts={posts} selectedId={selectedId} onSelect={setSelectedId} weekStart={weekStart} onAdd={createPost} />
          }
          <DayNodeGraph post={selected} weekStart={weekStart} reloadPosts={reloadPosts} />
        </div>
      </div>
      <InspectorPanel
        post={selected} weekStart={weekStart} jobs={jobs}
        telegramOn={!!h?.telegram_enabled} xOn={!!h?.x_enabled}
        onChange={updateSelected} onToggleChannel={toggleChannel} onDelete={deleteSelected}
        reloadPosts={reloadPosts} captionPack={captionPack}
      />
      {planOpen && (
        <PlanModal
          initialTab={_planParam === 'import' ? 'import' : 'generate'}
          onClose={() => setPlanOpen(false)}
          onMaterialized={(startDate) => {
            setPlanOpen(false);
            // Jump the calendar to the plan's first week.
            const target = mondayOf(new Date(startDate));
            const cur = mondayOf(new Date());
            setWeekOffset(Math.round((target - cur) / (7 * 86400000)));
            setView('week');
            reloadPosts?.();
          }}
        />
      )}
    </div>
  );
}

function SchedulerHeader({ view, setView, count, range, onPrev, onNext, onToday, onNew, onPlan }) {
  return (
    <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--stroke)', background: 'var(--bg-panel)', display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Scheduler</div>
        <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{count} post{count === 1 ? '' : 's'} planned</div>
      </div>
      <div style={{ display: 'flex', gap: 2, padding: 3, background: 'var(--bg-base)', borderRadius: 'var(--r-sm)', border: '1px solid var(--stroke)', marginLeft: 16 }}>
        {['week','month'].map(v => (
          <button key={v} onClick={() => setView(v)} style={{
            height: 26, padding: '0 12px', background: view === v ? 'var(--bg-panel-2)' : 'transparent',
            border: 0, borderRadius: 4, cursor: 'pointer',
            color: view === v ? 'var(--ink-strong)' : 'var(--ink-soft)', fontSize: 11.5, fontWeight: 500,
          }}>{v[0].toUpperCase()+v.slice(1)}</button>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
        <IconButton name="caret" iconSize={12} style={{ transform: 'rotate(90deg)' }} title="Previous" onClick={onPrev} />
        <button onClick={onToday} title="Back to today" style={{ background: 'transparent', border: 0, cursor: 'pointer', padding: 0 }}>
          <span className="display" style={{ fontSize: 13, color: 'var(--ink-strong)' }}>{range}</span>
        </button>
        <IconButton name="caret" iconSize={12} style={{ transform: 'rotate(-90deg)' }} title="Next" onClick={onNext} />
      </div>
      <div style={{ flex: 1 }} />
      <Button variant="outline" size="sm" icon="sparkle" onClick={onPlan}>Generate plan</Button>
      <Button variant="primary" size="sm" icon="plus" glow onClick={onNew}>New post</Button>
    </div>
  );
}

/* ──────────── Week grid (7 cols, real dates) ──────────── */
function WeekGrid({ posts, selectedId, onSelect, weekStart, onAdd }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 10, marginBottom: 22 }}>
      {Array.from({ length: 7 }).map((_, i) => {
        const lbl = dayLabel(weekStart, i);
        const dayPosts = posts
          .filter(p => sameDay(p.runAt, lbl.date))
          .sort((a, b) => a.runAt - b.runAt);
        const isToday = sameDay(new Date(), lbl.date);
        return (
          <div key={i} style={{
            background: 'var(--bg-panel)', border: `1px solid ${isToday ? 'var(--brand)' : 'var(--stroke)'}`,
            borderRadius: 'var(--r)', overflow: 'hidden',
            boxShadow: isToday ? '0 0 16px var(--brand-soft)' : 'none',
            minHeight: 220,
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="upper" style={{ color: isToday ? 'var(--brand)' : 'var(--ink-soft)' }}>{lbl.short}</div>
                <div className="display" style={{ fontSize: 17, color: 'var(--ink-strong)' }}>{lbl.day}</div>
              </div>
              {dayPosts.length > 0 && (
                <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-soft)', background: 'var(--bg-base)', padding: '2px 5px', borderRadius: 3, border: '1px solid var(--stroke)' }}>
                  {dayPosts.length}
                </div>
              )}
            </div>
            <div style={{ padding: 6, display: 'flex', flexDirection: 'column', gap: 5, flex: 1 }}>
              {dayPosts.map(p => <DayPostCard key={p.id} post={p} selected={selectedId === p.id} onClick={() => onSelect(p.id)} />)}
              <button onClick={() => onAdd(i)} style={{
                marginTop: 'auto', padding: '5px 6px',
                background: 'transparent', border: '1px dashed var(--stroke-strong)', borderRadius: 'var(--r-sm)',
                color: 'var(--ink-muted)', fontSize: 10.5, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.color = 'var(--brand)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--stroke-strong)'; e.currentTarget.style.color = 'var(--ink-muted)'; }}
              >
                <Icon name="plus" size={11} /> add post
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ──────────── Month grid — real calendar dates ──────────── */
function MonthGrid({ posts, selectedId, onSelect, monthOffset = 0 }) {
  const now = new Date();
  const ref = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  const year = ref.getFullYear(), month = ref.getMonth();
  const firstWd = (ref.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const totalCells = Math.ceil((firstWd + daysInMonth) / 7) * 7;
  const monthName = ref.toLocaleString('en', { month: 'long' });

  function postsForDom(dom) {
    if (!dom) return [];
    const d = new Date(year, month, dom);
    return posts.filter(p => sameDay(p.runAt, d)).sort((a, b) => a.runAt - b.runAt);
  }

  return (
    <div style={{ marginBottom: 22 }}>
      <div className="upper" style={{ marginBottom: 8, color: 'var(--ink-soft)' }}>{monthName} {year}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 1, background: 'var(--stroke)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)', overflow: 'hidden' }}>
        {['MON','TUE','WED','THU','FRI','SAT','SUN'].map(d => (
          <div key={d} style={{ padding: '6px 8px', background: 'var(--bg-panel)', textAlign: 'left' }} className="upper">{d}</div>
        ))}
        {Array.from({ length: totalCells }).map((_, idx) => {
          const dom = idx >= firstWd && idx < firstWd + daysInMonth ? idx - firstWd + 1 : null;
          const isToday = dom != null && sameDay(new Date(year, month, dom), now);
          const dayPosts = postsForDom(dom);
          return (
            <div key={idx} style={{
              minHeight: 92, padding: 6,
              background: dom ? (isToday ? 'var(--brand-soft)' : 'var(--bg-panel)') : 'var(--bg-base)',
              opacity: dom ? 1 : 0.4,
              display: 'flex', flexDirection: 'column', gap: 3,
            }}>
              {dom && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="display" style={{ fontSize: 13, color: isToday ? 'var(--brand)' : 'var(--ink-strong)' }}>{dom}</span>
                    {dayPosts.length > 0 && <span className="mono" style={{ fontSize: 9, color: 'var(--ink-soft)' }}>{dayPosts.length}</span>}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
                    {dayPosts.slice(0, 3).map(p => {
                      const sel = p.id === selectedId;
                      return (
                        <div key={p.id} onClick={() => onSelect(p.id)} title={`${p.time} · ${p.title}`} style={{
                          padding: '2px 4px', borderRadius: 3, cursor: 'pointer',
                          background: sel ? 'var(--brand-soft)' : 'var(--bg-base)',
                          border: `1px solid ${sel ? 'var(--brand)' : 'var(--stroke)'}`,
                          fontSize: 9.5, color: 'var(--ink)',
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                          display: 'flex', alignItems: 'center', gap: 4,
                        }}>
                          <span style={{ width: 4, height: 4, borderRadius: '50%', background: statusColor(p.status), flexShrink: 0 }} />
                          <span className="mono" style={{ fontSize: 8.5, color: 'var(--ink-soft)' }}>{p.time}</span>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.title}</span>
                        </div>
                      );
                    })}
                    {dayPosts.length > 3 && (
                      <div style={{ fontSize: 9, color: 'var(--ink-soft)', padding: '0 4px' }}>+{dayPosts.length - 3} more</div>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DayPostCard({ post, selected, onClick }) {
  const col = statusColor(post.status);
  return (
    <div onClick={onClick} style={{
      padding: '6px 8px', borderRadius: 6,
      background: selected ? 'var(--brand-soft)' : 'var(--bg-base)',
      border: `1px solid ${selected ? 'var(--brand)' : 'var(--stroke)'}`,
      cursor: 'pointer',
      transition: 'all var(--dur-1) var(--ease)',
      boxShadow: selected ? '0 0 14px var(--brand-soft)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3 }}>
        <span style={{ width: 5, height: 5, borderRadius: 999, background: col }} />
        <span style={{ fontFamily: 'var(--f-mono)', fontSize: 9.5, color: col, fontWeight: 600 }}>{post.time}</span>
        {post.status === 'ready' && <span style={{ fontSize: 8.5, color: 'var(--amber)', fontWeight: 600 }}>READY</span>}
        {post.status === 'failed' && <span style={{ fontSize: 8.5, color: 'var(--red)', fontWeight: 600 }}>FAILED</span>}
      </div>
      <div style={{ fontSize: 10.5, color: 'var(--ink-strong)', lineHeight: 1.25, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {post.title}
      </div>
      <div style={{ display: 'flex', gap: 2, marginTop: 4 }}>
        {post.channels.map(c => CHANNELS[c] && (
          <span key={c} style={{
            width: 14, height: 14, borderRadius: 4,
            background: CHANNELS[c].bg, color: CHANNELS[c].color,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            border: `1px solid ${CHANNELS[c].color}33`,
          }}><Icon name={CHANNELS[c].icon} size={9} /></span>
        ))}
      </div>
    </div>
  );
}

/* ──────────── Per-post node graph (draggable nodes + bezier edges) ──────────── */
const NODE_DIMS = {
  render:  { w: 230, h: 168 },
  caption: { w: 220, h: 180 },
  channel: { w: 300, h: 70 },
};
function defaultLayout(p) {
  const out = { render: { x: 30, y: 130 }, caption: { x: 320, y: 90 } };
  (p?.channels || []).forEach((c, i) => { out[`ch:${c}`] = { x: 720, y: 30 + i * 88 }; });
  return out;
}

function DayNodeGraph({ post, weekStart, reloadPosts }) {
  // All hooks run unconditionally (post may be null) — the empty state
  // renders after, so the hook count never changes between renders.
  const h = useHealth();
  const [layout, setLayout] = useStateSch(() => defaultLayout(post));
  const [firing, setFiring] = useStateSch(false);
  const [fireMsg, setFireMsg] = useStateSch('');
  const lastPostId = useRefSch(post?.id);
  useEffectSch(() => {
    if (!post) return;
    setLayout(prev => {
      if (lastPostId.current !== post.id) {
        lastPostId.current = post.id;
        return defaultLayout(post);
      }
      const next = { render: prev.render || { x: 30, y: 130 }, caption: prev.caption || { x: 320, y: 90 } };
      post.channels.forEach((c, i) => {
        const k = `ch:${c}`;
        next[k] = prev[k] || { x: 720, y: 30 + i * 88 };
      });
      return next;
    });
  }, [post?.id, (post?.channels || []).join('|')]);

  const dragRef = useRefSch(null);
  const canvasRef = useRefSch(null);
  const panning = useRefSch(null);
  const [zoom, setZoom] = useStateSch(1);
  const [pan, setPan] = useStateSch({ x: 0, y: 0 });
  function onDragStart(e, key) {
    e.preventDefault(); e.stopPropagation();
    const pos = layout[key];
    if (!pos) return;
    dragRef.current = { key, startX: e.clientX, startY: e.clientY, posX: pos.x, posY: pos.y, zoom };
  }
  // Node drag (delta divided by zoom) + canvas pan, on one global listener pair.
  useEffectSch(() => {
    function m(e) {
      if (dragRef.current) {
        const d = dragRef.current;
        setLayout(L => ({ ...L, [d.key]: { x: d.posX + (e.clientX - d.startX) / d.zoom, y: d.posY + (e.clientY - d.startY) / d.zoom } }));
      } else if (panning.current) {
        const p = panning.current;
        setPan({ x: p.panX + (e.clientX - p.x), y: p.panY + (e.clientY - p.y) });
      }
    }
    function u() { dragRef.current = null; panning.current = null; }
    window.addEventListener('mousemove', m);
    window.addEventListener('mouseup', u);
    return () => { window.removeEventListener('mousemove', m); window.removeEventListener('mouseup', u); };
  }, []);

  if (!post) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: 'var(--ink-muted)', fontSize: 12 }}>
        Select a post on the calendar above to see its routing graph,
        or press <span className="mono" style={{ color: 'var(--ink-soft)' }}>Generate plan</span> to fill the week.
      </div>
    );
  }
  const RH = Math.max(360, 80 + post.channels.length * 78);

  function center(key, kind) {
    const pos = layout[key];
    if (!pos) return { x: 0, y: 0 };
    const d = NODE_DIMS[kind] || NODE_DIMS.channel;
    return { x: pos.x + d.w / 2, y: pos.y + d.h / 2 };
  }
  function rightEdge(key, kind) { const c = center(key, kind); const d = NODE_DIMS[kind] || NODE_DIMS.channel; return { x: c.x + d.w / 2, y: c.y }; }
  function leftEdge(key, kind) { const c = center(key, kind); const d = NODE_DIMS[kind] || NODE_DIMS.channel; return { x: c.x - d.w / 2, y: c.y }; }
  function bezier(a, b) {
    const dx = Math.max(40, Math.abs(b.x - a.x) * 0.5);
    return `M ${a.x} ${a.y} C ${a.x + dx} ${a.y}, ${b.x - dx} ${b.y}, ${b.x} ${b.y}`;
  }
  // Mouse-wheel zoom anchored on the cursor; left-drag on empty canvas pans.
  function onWheel(e) {
    e.preventDefault();
    const r = canvasRef.current?.getBoundingClientRect();
    if (!r) return;
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const nz = Math.max(0.4, Math.min(2, zoom - e.deltaY * 0.0015));
    if (nz === zoom) return;
    setPan({ x: mx - (mx - pan.x) * (nz / zoom), y: my - (my - pan.y) * (nz / zoom) });
    setZoom(nz);
  }
  function onCanvasDown(e) {
    if (e.button !== 0 || e.target.closest('[data-pnode]')) return; // ignore node clicks
    panning.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }
  function resetView() { setZoom(1); setPan({ x: 0, y: 0 }); setLayout(defaultLayout(post)); }

  async function fireNow() {
    setFiring(true); setFireMsg('');
    const r = await api.fireScheduledPost(post.id);
    setFiring(false);
    if (r?.ok) setFireMsg(`Sent: ${(r.sent || []).join(' · ')}`);
    else setFireMsg(`Marked ready. ${(r?.pending || []).join(' · ')}`);
    reloadPosts?.();
  }

  const when = post.runAt.toLocaleString('en', { weekday: 'short', day: 'numeric', month: 'short' });
  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Icon name="flow" size={14} style={{ color: 'var(--brand)' }} />
        <span className="display" style={{ fontSize: 14, color: 'var(--ink-strong)' }}>{post.title}</span>
        <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--ink-soft)' }}>{when} · {post.time}</span>
        <Badge>{post.mode === 'auto' ? 'auto-publish' : 'assisted'}</Badge>
        <span style={{ flex: 1 }} />
        {fireMsg && <span style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{fireMsg}</span>}
        <Badge tone={post.status === 'posted' ? 'green' : post.status === 'failed' ? 'red' : post.status === 'ready' ? 'amber' : post.status === 'draft' ? 'neutral' : 'cyan'} dot>{post.status}</Badge>
        <Button variant="ghost" size="sm" icon="bolt" onClick={resetView} title="Reset layout, zoom & pan">Reset</Button>
        <Button variant="primary" size="sm" icon="send" glow onClick={fireNow} disabled={firing}>
          {firing ? 'Sending…' : `Send now`}
        </Button>
      </div>
      <div ref={canvasRef} onWheel={onWheel} onMouseDown={onCanvasDown} style={{
        position: 'relative', height: RH, overflow: 'hidden',
        background: `radial-gradient(circle at center, var(--stroke) 1px, transparent 1.5px)`,
        backgroundSize: `${24 * zoom}px ${24 * zoom}px`, backgroundPosition: `${pan.x}px ${pan.y}px`,
        cursor: panning.current ? 'grabbing' : 'default',
      }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: '0 0' }}>
        <svg style={{ position: 'absolute', top: 0, left: 0, width: 2200, height: 1500, pointerEvents: 'none', overflow: 'visible' }}>
          {(() => {
            const a = rightEdge('render','render');
            const b = leftEdge('caption','caption');
            return <path d={bezier(a,b)} stroke="var(--brand)" strokeWidth={2} fill="none" opacity={0.85} style={{ filter: 'drop-shadow(0 0 6px var(--brand-soft))' }} />;
          })()}
          {post.channels.map(c => CHANNELS[c] && (
            <path key={c} d={bezier(rightEdge('caption','caption'), leftEdge(`ch:${c}`,'channel'))}
              stroke={CHANNELS[c].color} strokeWidth={1.8} fill="none" opacity={0.85}
              style={{ filter: `drop-shadow(0 0 4px ${CHANNELS[c].color}66)` }} />
          ))}
        </svg>

        <DragNode pos={layout.render} dims={NODE_DIMS.render} color="var(--brand)" icon="film" title="Render" onDragStart={e => onDragStart(e,'render')}>
          {/* Thumbnail: the produced render (jobId), else the chosen source
              image (image/news/composition source) — see at a glance what this
              chain will produce. */}
          {(post.jobId || post.sourceImage) && (
            <div style={{ height: 70, marginBottom: 5, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--stroke)', background: '#000' }}>
              {post.jobId ? (
                <video src={api.jobVideoUrl(post.jobId)} muted preload="metadata" playsInline
                  onMouseEnter={e => e.currentTarget.play().catch(() => {})}
                  onMouseLeave={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                  onError={e => { e.currentTarget.style.display = 'none'; }}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              ) : (
                <img src={api.imageUrl(post.sourceImage)} alt=""
                  onError={e => { e.currentTarget.style.display = 'none'; }}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              )}
            </div>
          )}
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 10.5, color: 'var(--ink-strong)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {post.jobId ? post.jobId.slice(0, 18) : post.sourceImage ? 'source ready' : 'no render attached'}
          </div>
          <div style={{ fontSize: 10, color: post.jobId ? 'var(--ink-soft)' : post.sourceImage ? 'var(--cyan)' : 'var(--amber)', marginTop: 3 }}>
            {post.jobId ? (post.format || 'render from Library') : post.sourceImage ? 'source preview · Produce to render' : 'attach one in the inspector'}
          </div>
        </DragNode>

        <DragNode pos={layout.caption} dims={NODE_DIMS.caption} color="var(--violet)" icon="rename" title="Caption" onDragStart={e => onDragStart(e,'caption')}>
          <div style={{ fontSize: 10.5, color: 'var(--ink-strong)', whiteSpace: 'pre-wrap', lineHeight: 1.35, maxHeight: 110, overflow: 'hidden' }}>
            {post.caption || <span style={{ color: 'var(--ink-muted)' }}>empty caption</span>}
          </div>
          <div style={{ position: 'absolute', bottom: 6, left: 10, right: 10, display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--ink-soft)', fontFamily: 'var(--f-mono)' }}>
            <span>{(post.caption || '').length} ch</span>
            <span>{post.hook ? 'from plan' : ''}</span>
          </div>
        </DragNode>

        {post.channels.map(c => {
          const ch = CHANNELS[c];
          if (!ch) return null;
          const auto = (c === 'telegram' && !!h?.telegram_enabled)
                    || (c === 'x' && !!h?.x_enabled);
          return (
            <DragNode key={c} pos={layout[`ch:${c}`]} dims={NODE_DIMS.channel} color={ch.color} icon={ch.icon} title={ch.label} onDragStart={e => onDragStart(e,`ch:${c}`)}>
              <div style={{ fontSize: 10.5, color: 'var(--ink-strong)' }}>{auto ? 'bot publish' : 'manual publish'}</div>
              <div style={{ fontSize: 10, color: 'var(--ink-soft)', marginTop: 2, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: 999, background: auto ? 'var(--green)' : 'var(--amber)' }} />
                  {auto ? 'auto-capable' : 'assisted only'}
                </span>
                <span className="mono">{(post.caption || '').length}/{ch.limit}</span>
              </div>
            </DragNode>
          );
        })}
        </div>
        {/* Zoom HUD (wheel zooms anywhere; drag empty canvas to pan). */}
        <div style={{ position: 'absolute', left: 10, bottom: 10, zIndex: 4, display: 'flex', gap: 2, background: 'var(--bg-panel)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', padding: 2 }}>
          <IconButton name="minus" size={24} iconSize={11} onClick={() => setZoom(z => Math.max(0.4, +(z - 0.1).toFixed(2)))} />
          <div style={{ minWidth: 42, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--f-mono)', fontSize: 10.5, color: 'var(--ink-soft)' }}>{Math.round(zoom * 100)}%</div>
          <IconButton name="plus" size={24} iconSize={11} onClick={() => setZoom(z => Math.min(2, +(z + 0.1).toFixed(2)))} />
        </div>
      </div>
    </div>
  );
}

function DragNode({ pos, dims, color, icon, title, children, onDragStart }) {
  if (!pos) return null;
  return (
    <div data-pnode style={{
      position: 'absolute', left: pos.x, top: pos.y, width: dims.w, height: dims.h,
      background: 'var(--bg-panel-2)',
      border: `1px solid ${color}`,
      borderRadius: 14,
      boxShadow: `0 0 0 1px ${color}33, 0 0 24px ${color}22`,
      overflow: 'hidden', userSelect: 'none',
    }}>
      <div onMouseDown={onDragStart} style={{
        height: 26, padding: '0 10px',
        display: 'flex', alignItems: 'center', gap: 8,
        background: `linear-gradient(180deg, ${color}22 0%, transparent 100%)`,
        borderBottom: '1px solid var(--stroke)',
        cursor: 'grab',
      }}>
        <span style={{ width: 16, height: 16, borderRadius: 4, background: `${color}22`, color, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={icon} size={10} />
        </span>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-strong)' }}>{title}</span>
        <span style={{ flex: 1 }} />
        <Icon name="more" size={11} style={{ color: 'var(--ink-muted)' }} />
      </div>
      <div style={{ padding: 8, position: 'relative', height: dims.h - 26 }}>{children}</div>
    </div>
  );
}

/* ──────────── Right inspector ──────────── */
function InspectorPanel({ post, weekStart, jobs, telegramOn, xOn, onChange, onToggleChannel, onDelete, reloadPosts, captionPack }) {
  const PACK = (captionPack && captionPack.length) ? captionPack : TELEGRAM_PREMIUM_PACK;
  const [firing, setFiring] = useStateSch(false);
  const [fireMsg, setFireMsg] = useStateSch('');
  const [producing, setProducing] = useStateSch(false);
  const [produceMsg, setProduceMsg] = useStateSch('');
  const captionRef = useRefSch(null);

  // Insert an emoji into the caption at the cursor (or append), then restore focus.
  function insertEmoji(em) {
    const ta = captionRef.current;
    const cur = post?.caption || '';
    if (ta && typeof ta.selectionStart === 'number') {
      const s = ta.selectionStart, e = ta.selectionEnd;
      onChange({ caption: cur.slice(0, s) + em + cur.slice(e) });
      requestAnimationFrame(() => {
        try { ta.focus(); const pos = s + em.length; ta.setSelectionRange(pos, pos); } catch {}
      });
    } else {
      onChange({ caption: cur + em });
    }
  }

  // C — Produce the render for this post from its plan seeds.
  // image: FLUX still → Library. seedance: FLUX start frame → Seedance clip,
  // job auto-attached. heygen/composition: queued via their pipelines (job id
  // is assigned async by the backend → attach from the Render picker when done).
  async function produce() {
    if (!post || producing) return;
    setProducing(true); setProduceMsg('');
    const fmt = post.format || 'seedance';
    const idea = post.image_idea || post.hook || post.title;
    const script = post.script_idea || post.caption || post.title;
    try {
      if (fmt === 'image') {
        if (post.sourceImage) {
          setProduceMsg(`Source image ready: ${post.sourceImage} (in Library).`);
        } else {
          setProduceMsg('Creating image (FLUX)…');
          const r = await api.generateImage(idea, 1, 'portrait_16_9');
          setProduceMsg(r?.images?.length
            ? `Image saved to Library: ${r.images[0]}`
            : `Failed: ${String(r?.error || '').slice(0, 120)}`);
        }
      } else if (fmt === 'seedance' || fmt === 'composition' || fmt === 'news') {
        // Reuse the source picked in the plan's Sources step; only generate
        // a start frame when none was chosen.
        let startImage = post.sourceImage;
        if (!startImage) {
          setProduceMsg('Start frame (FLUX, ~3s)…');
          const img = await api.generateImage(idea, 1, 'portrait_16_9');
          if (!img?.images?.length) {
            setProduceMsg(`Image step failed: ${String(img?.error || '').slice(0, 120)}`);
            return;
          }
          startImage = img.images[0];
        } else {
          setProduceMsg('Using your chosen source image…');
        }
        setProduceMsg('Cinematic clip (Seedance, ~40s)… watch the Job Dock.');
        const r = await api.postJson('/generate', {
          image_filename: startImage,
          custom_prompt: script,
          style: 'cinematic', duration_s: 10, aspect_ratio: '9:16',
          voiceover_enabled: false,
        });
        if (r?.job_id && r.job_id !== 'pending') {
          onChange({ jobId: r.job_id });
          setProduceMsg('Clip queued + attached to this post. It renders in the background.');
        } else {
          setProduceMsg('Clip queued — attach it from the Render picker when it finishes.');
        }
      } else if (fmt === 'heygen') {
        setProduceMsg('Loading avatar + voice…');
        const [a, v] = await Promise.all([api.listHeygenAvatars(), api.listHeygenVoices()]);
        const avatar = (a?.avatars || [])[0];
        const voice = (v?.voices || [])[0];
        if (!avatar || !voice) {
          setProduceMsg('HeyGen avatars/voices unavailable (check the key / network).');
          return;
        }
        setProduceMsg('Avatar video queued (HeyGen, 1-3 min)…');
        const r = await api.postJson('/generate/heygen', {
          avatar_id: avatar.avatar_id, voice_id: voice.voice_id,
          script: script.slice(0, 4900),
          avatar_type: avatar.avatar_type || 'avatar',
          aspect_ratio: '9:16', speed: 1.0,
        });
        setProduceMsg(r?.ok === false
          ? `Failed: ${String(r?.error || '').slice(0, 120)}`
          : 'Avatar render queued — attach it from the Render picker when done.');
      } else {
        setProduceMsg(`No auto-production for format "${fmt}".`);
      }
    } finally {
      setProducing(false);
    }
  }
  if (!post) {
    return (
      <div style={{ background: 'var(--bg-panel)', borderLeft: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, color: 'var(--ink-muted)', textAlign: 'center', fontSize: 12 }}>
        Select a post to edit caption, render, channels and timing.
      </div>
    );
  }
  const when = post.runAt.toLocaleString('en', { weekday: 'short', day: 'numeric', month: 'short' });

  async function fireNow() {
    setFiring(true); setFireMsg('');
    const r = await api.fireScheduledPost(post.id);
    setFiring(false);
    if (r?.ok) setFireMsg(`Sent on: ${(r.sent || []).join(' · ')}`);
    else setFireMsg(`Not auto-sent. ${(r?.pending || []).join(' · ')}`);
    reloadPosts?.();
  }
  async function duplicateTomorrow() {
    const runAt = new Date(post.runAt); runAt.setDate(runAt.getDate() + 1);
    const r = await api.createScheduledPost({
      title: post.title + ' (copy)', caption: post.caption, channels: post.channels,
      run_at: runAt.toISOString(), status: 'draft', mode: post.mode, job_id: post.jobId,
    });
    if (r?.id) reloadPosts?.();
  }

  return (
    <div style={{ background: 'var(--bg-panel)', borderLeft: '1px solid var(--stroke)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 28, height: 28, borderRadius: 7, background: 'var(--brand-soft)', color: 'var(--brand)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="send" size={14} />
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <input value={post.title} onChange={e => onChange({ title: e.target.value })} style={{ width: '100%', fontFamily: 'var(--f-display)', fontSize: 16, color: 'var(--ink-strong)', background: 'transparent', border: 0, padding: 0 }} />
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{when} · {post.time}</div>
          </div>
          <IconButton name="trash" onClick={onDelete} title="Delete" />
        </div>
        {post.error && (
          <div style={{ marginTop: 8, padding: 8, background: 'var(--red-soft)', border: '1px solid var(--red)', borderRadius: 'var(--r-sm)', fontSize: 10.5, color: 'var(--ink)' }}>
            {post.error}
          </div>
        )}
      </div>
      <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
        <InspectorSection label="Schedule">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Field label="Day">
              <Select
                value={String(Math.max(0, Math.min(6, Math.round((new Date(post.runAt.getFullYear(), post.runAt.getMonth(), post.runAt.getDate()) - weekStart) / 86400000))))}
                onChange={v => {
                  const lbl = dayLabel(weekStart, Number(v));
                  onChange({ runAt: setTimeOn(lbl.date, post.time), time: post.time });
                }}
                options={[0,1,2,3,4,5,6].map(d => {
                  const l = dayLabel(weekStart, d);
                  return { value: String(d), label: `${l.short} ${l.day}` };
                })} />
            </Field>
            <Field label="Time">
              <Input mono value={post.time} onChange={v => {
                onChange({ time: v, runAt: setTimeOn(post.runAt, v) });
              }} placeholder="HH:MM" />
            </Field>
          </div>
          <Field>
            <Toggle checked={post.status === 'scheduled'} label="Scheduled (uncheck = draft)" onChange={v => onChange({ status: v ? 'scheduled' : 'draft' })} />
          </Field>
          <Field hint={post.mode === 'auto'
            ? ((telegramOn || xOn)
              ? `Auto: fires alone at the set time (${[telegramOn && 'Telegram', xOn && 'X'].filter(Boolean).join(' + ')}).`
              : 'Auto needs Telegram or X keys (Settings → Connected accounts). Without them it flips to ready.')
            : 'Assisted: flips to READY at the set time; you press Send.'}>
            <Toggle checked={post.mode === 'auto'} label="Auto-publish at time" onChange={v => onChange({ mode: v ? 'auto' : 'assisted' })} />
          </Field>
        </InspectorSection>

        <InspectorSection label="Render">
          <Field hint={post.jobId ? '' : 'Optional. Without a render, the post is caption-only (or attach later).'}>
            <Select
              value={post.jobId || ''}
              onChange={v => onChange({ jobId: v || null })}
              options={[{ value: '', label: 'no render (caption only)' },
                ...jobs.map(j => ({ value: j.job_id, label: `${j.title || j.provider || 'render'} · ${(j.job_id || '').slice(0, 6)}` }))]} />
          </Field>
          {post.sourceImage && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 6, background: 'var(--bg-base)', border: '1px solid var(--amber)', borderRadius: 'var(--r-sm)' }}>
              <img src={api.imageUrl(post.sourceImage)} alt="" onError={e => { e.currentTarget.style.opacity = 0.2; }}
                style={{ width: 26, height: 34, objectFit: 'cover', borderRadius: 4 }} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 600 }}>SOURCE IMAGE</div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--ink-soft)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{post.sourceImage}</div>
              </div>
              <IconButton name="close" size={20} iconSize={10} title="Clear source" onClick={() => onChange({ sourceImage: null })} />
            </div>
          )}
          <Button variant="outline" size="sm" icon="sparkle" onClick={produce} disabled={producing} style={{ width: '100%' }}>
            {producing ? 'Producing…' : post.sourceImage ? `Produce with chosen source` : `Produce ${post.format || 'seedance'} render from plan`}
          </Button>
          {produceMsg && (
            <div style={{ marginTop: 6, fontSize: 10.5, color: produceMsg.startsWith('Failed') || produceMsg.includes('failed') || produceMsg.includes('unavailable') ? 'var(--red)' : 'var(--ink-soft)' }}>
              {produceMsg}
            </div>
          )}

          {/* Review the produced render right here, before Send / Auto. */}
          {post.jobId && (() => {
            const ready = jobs.some(j => j.job_id === post.jobId);
            return (
              <div style={{ marginTop: 10 }}>
                <div className="upper" style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>Render preview</span>
                  {ready ? <Badge tone="green" dot>ready</Badge> : <Badge tone="amber" dot>rendering…</Badge>}
                </div>
                {ready ? (
                  <video src={api.jobVideoUrl(post.jobId)} controls preload="metadata"
                    onError={e => { e.currentTarget.style.display = 'none'; }}
                    style={{ width: '100%', maxHeight: 320, borderRadius: 'var(--r-sm)', background: '#000', display: 'block' }} />
                ) : (
                  <div style={{ padding: 10, background: 'var(--bg-base)', border: '1px solid var(--amber)', borderRadius: 'var(--r-sm)', fontSize: 10.5, color: 'var(--ink-soft)', lineHeight: 1.45 }}>
                    Rendering in the background — watch the Job Dock. The clip plays here once it finishes.
                  </div>
                )}
                <div style={{ marginTop: 5, fontSize: 10, color: 'var(--ink-soft)' }}>
                  Review the render before you <strong style={{ color: 'var(--ink)' }}>Send</strong> or turn on <strong style={{ color: 'var(--ink)' }}>Auto-publish</strong>.
                </div>
              </div>
            );
          })()}
          {(post.image_idea || post.script_idea) && (
            <div style={{ marginTop: 6, padding: 8, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', fontSize: 10.5, color: 'var(--ink-soft)', lineHeight: 1.45 }}>
              {post.image_idea && <div><span style={{ color: 'var(--amber)', fontWeight: 600 }}>visual · </span>{post.image_idea}</div>}
              {post.script_idea && <div style={{ marginTop: post.image_idea ? 4 : 0 }}><span style={{ color: 'var(--cyan)', fontWeight: 600 }}>script · </span>{post.script_idea}</div>}
            </div>
          )}
        </InspectorSection>

        <InspectorSection label="Channels">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {CHANNEL_LIST.map(ch => {
              const on = post.channels.includes(ch.id);
              return (
                <button key={ch.id} onClick={() => onToggleChannel(ch.id)} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '9px 10px',
                  background: on ? ch.bg : 'var(--bg-base)',
                  border: `1px solid ${on ? ch.color + '88' : 'var(--stroke)'}`,
                  borderRadius: 'var(--r-sm)', cursor: 'pointer',
                  color: on ? ch.color : 'var(--ink-muted)',
                  boxShadow: on ? `0 0 12px ${ch.color}33` : 'none',
                  transition: 'all var(--dur-1) var(--ease)',
                }}>
                  <Icon name={ch.icon} size={14} />
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{ch.label}</span>
                  {ch.id === 'telegram' && <span style={{ marginLeft: 'auto', fontSize: 8.5, color: telegramOn ? 'var(--green)' : 'var(--ink-muted)' }}>{telegramOn ? 'auto' : 'no key'}</span>}
                  {ch.id === 'x' && <span style={{ marginLeft: 'auto', fontSize: 8.5, color: xOn ? 'var(--green)' : 'var(--ink-muted)' }}>{xOn ? 'auto' : 'assisted'}</span>}
                </button>
              );
            })}
          </div>
        </InspectorSection>

        <InspectorSection label="Caption">
          <Field hint={`${(post.caption || '').length} characters · same on all channels`}>
            <textarea ref={captionRef} value={post.caption} onChange={e => onChange({ caption: e.target.value })} rows={5} style={{
              width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)',
              borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical',
            }} />
          </Field>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: -4 }}>
            {CAPTION_EMOJIS.map(em => (
              <button key={em} type="button" onClick={() => insertEmoji(em)} title={`Insert ${em}`} style={{
                width: 30, height: 28, fontSize: 15, lineHeight: 1,
                background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)',
                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all var(--dur-1) var(--ease)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.background = 'var(--brand-soft)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--stroke)'; e.currentTarget.style.background = 'var(--bg-base)'; }}
              >{em}</button>
            ))}
          </div>
          <div className="upper" style={{ marginTop: 10, marginBottom: 5, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="sparkle" size={11} style={{ color: 'var(--brand)' }} />
            <span>Telegram Premium pack</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {PACK.map(t => (
              <button key={t.label} type="button" onClick={() => insertEmoji(`${t.e} ${t.label}`)} title={`Insert "${t.e} ${t.label}"`} style={{
                display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 9px', fontSize: 11,
                background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 999,
                color: 'var(--ink)', cursor: 'pointer', transition: 'all var(--dur-1) var(--ease)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.background = 'var(--brand-soft)'; e.currentTarget.style.color = 'var(--ink-strong)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--stroke)'; e.currentTarget.style.background = 'var(--bg-base)'; e.currentTarget.style.color = 'var(--ink)'; }}
              >
                <PackIcon icon={t.icon} emoji={t.e} size={16} />{t.label}
              </button>
            ))}
          </div>
          {post.hook && (
            <div style={{ padding: 8, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', fontSize: 10.5, color: 'var(--ink-soft)' }}>
              <span style={{ color: 'var(--violet)', fontWeight: 600 }}>Plan hook · </span>{post.hook}
            </div>
          )}
        </InspectorSection>
      </div>
      <div style={{ padding: 12, borderTop: '1px solid var(--stroke)', display: 'grid', gap: 8 }}>
        {fireMsg && <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{fireMsg}</div>}
        <Button variant="primary" size="md" icon="send" glow onClick={fireNow} disabled={firing}>
          {firing ? 'Sending…' : `Send to ${post.channels.length} channel${post.channels.length === 1 ? '' : 's'} now`}
        </Button>
        <Button variant="outline" size="sm" icon="copy" onClick={duplicateTomorrow}>Duplicate to next day</Button>
      </div>
    </div>
  );
}

/* ──────────── Per-post source picker (plan Sources step) ──────────── */
function PostSourceCell({ post, idx, images, newsItems, source, setSource }) {
  const [busy, setBusy] = useStateSch(false);
  const [msg, setMsg] = useStateSch('');
  const needsImage = ['seedance', 'composition', 'image', 'news'].includes(post.format);
  if (!needsImage) {
    return <span style={{ fontSize: 9.5, color: 'var(--ink-muted)', textAlign: 'right' }}>
      {post.format === 'heygen' ? 'avatar @ produce' : ''}
    </span>;
  }
  const newsWithImg = (post.format === 'news') ? newsItems.filter(n => n.image) : [];
  const opts = [
    { value: '', label: 'auto @ produce' },
    { value: '__gen__', label: '✨ generate image' },
    ...(newsWithImg.length ? newsWithImg.slice(0, 20).map((n, k) => ({ value: 'news:' + k, label: '📰 ' + (n.title || 'news').slice(0, 28) })) : []),
    ...images.slice(0, 60).map(f => ({ value: 'lib:' + f, label: f })),
  ];
  async function onPick(v) {
    setMsg('');
    if (v === '__gen__') {
      setBusy(true);
      const r = await api.generateImage(post.image_idea || post.title || 'deep-sea key visual, 9:16', 1, 'portrait_16_9');
      setBusy(false);
      if (r?.images?.length) setSource(idx, r.images[0]);
      else setMsg('gen failed');
      return;
    }
    if (v.startsWith('lib:')) { setSource(idx, v.slice(4)); return; }
    if (v.startsWith('news:')) {
      const n = newsWithImg[Number(v.slice(5))];
      if (n?.image) {
        setBusy(true);
        const r = await api.importImageUrl(n.image);
        setBusy(false);
        if (r?.filename) setSource(idx, r.filename);
        else { setMsg('news image failed — generating…'); onPick('__gen__'); }
      } else { onPick('__gen__'); } // news without image → generate
      return;
    }
    setSource(idx, null);
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
      {source ? (
        <img src={api.imageUrl(source)} alt="" onError={e => { e.currentTarget.style.opacity = 0.2; }}
          style={{ width: 24, height: 32, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--amber)', flexShrink: 0 }} />
      ) : (
        <span style={{ width: 24, height: 32, borderRadius: 4, border: '1px dashed var(--stroke-strong)', flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-muted)', fontSize: 9 }}>?</span>
      )}
      <Select value={source && images.includes(source) ? 'lib:' + source : ''} options={opts} onChange={onPick} style={{ flex: 1, minWidth: 0 }} />
      {busy && <span style={{ fontSize: 9.5, color: 'var(--cyan)' }}>…</span>}
      {msg && <span style={{ fontSize: 9, color: 'var(--red)' }}>{msg}</span>}
    </div>
  );
}

/* ──────────── Generate / Import plan modal ──────────── */
function PlanModal({ onClose, onMaterialized, initialTab = 'generate' }) {
  const h = useHealth();
  const [tab, setTab] = useStateSch(initialTab); // generate | import
  const [prompt, setPrompt] = useStateSch('');
  const [days, setDays] = useStateSch(7);
  const [perDay, setPerDay] = useStateSch(1);
  const [channels, setChannels] = useStateSch(['x', 'telegram']);
  const [language, setLanguage] = useStateSch('EN');
  const [mode, setMode] = useStateSch('assisted');
  const [startDate, setStartDate] = useStateSch(() => {
    const d = new Date(); return d.toISOString().slice(0, 10);
  });
  const [generating, setGenerating] = useStateSch(false);
  const [plan, setPlan] = useStateSch(null);     // {posts, engine, filename?}
  const [adding, setAdding] = useStateSch(false);
  const [err, setErr] = useStateSch('');
  const [importDays, setImportDays] = useStateSch(30);
  const fileRef = useRefSch(null);
  // v1.12 — Sources step: per-post resolved start image (filename).
  const [images, setImages] = useStateSch([]);     // library filenames
  const [newsItems, setNewsItems] = useStateSch([]); // {title, image, link}
  const [sources, setSources] = useStateSch({});   // postIndex -> filename

  // Load library images + news items so the Sources step can offer them.
  useEffectSch(() => {
    let alive = true;
    api.listImages().then(r => { if (alive) setImages((r?.images || []).map(im => im.filename)); });
    api.listNewsItems().then(r => { if (alive) setNewsItems((r?.items || r || []).filter(n => n && n.title)); });
    return () => { alive = false; };
  }, []);

  function setSource(idx, filename) {
    setSources(s => ({ ...s, [idx]: filename || undefined }));
    if (filename) setImages(im => im.includes(filename) ? im : [filename, ...im]);
  }

  function toggleCh(id) {
    setChannels(cs => cs.includes(id) ? cs.filter(c => c !== id) : [...cs, id]);
  }

  async function generate() {
    if (!prompt.trim() || generating) return;
    setGenerating(true); setErr(''); setPlan(null);
    const r = await api.marketingPlan({
      prompt: prompt.trim(), days, posts_per_day: perDay,
      channels, language, auto_materialize: false,
    });
    setGenerating(false);
    if (r?.posts) setPlan(r);
    else setErr(String(r?.error || 'Plan generation failed').slice(0, 160));
  }

  async function importDoc(file) {
    if (!file || generating) return;
    setGenerating(true); setErr(''); setPlan(null);
    const r = await api.importPlan(file, { days: importDays, channels, language });
    setGenerating(false);
    if (r?.posts) setPlan({ posts: r.posts, engine: r.engine, filename: r.filename });
    else setErr(String(r?.error || 'Import failed').slice(0, 200));
  }

  async function addToCalendar() {
    if (!plan || adding) return;
    setAdding(true); setErr('');
    // Human-in-the-loop: materialize EXACTLY the previewed posts, carrying the
    // source image chosen in the Sources step so Produce reuses it.
    const posts = plan.posts.map((p, i) => ({ ...p, source_image: sources[i] || null }));
    const r = await api.materializePlan(posts, startDate, mode);
    setAdding(false);
    if (r?.materialized_ids?.length) onMaterialized(startDate);
    else setErr(String(r?.error || 'Could not add posts').slice(0, 160));
  }

  const fmtColor = { image: 'var(--amber)', seedance: 'var(--cyan)', heygen: 'var(--violet)', composition: 'var(--brand)', news: 'var(--green)' };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 80,
      background: 'var(--bg-overlay)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 28,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 900, maxWidth: '96%', maxHeight: '92%',
        background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
        borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 70px var(--cyan-soft)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name="sparkle" size={16} style={{ color: 'var(--cyan)' }} />
          <div style={{ flex: 1 }}>
            <div className="display" style={{ fontSize: 15, color: 'var(--ink-strong)' }}>
              {tab === 'import' ? 'Import a strategy document' : 'Generate a marketing plan'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>
              {tab === 'import'
                ? 'Upload your existing plan (.md, .docx, .pdf) — it becomes calendar posts after your review.'
                : (h?.has_summarizer || h?.summarizer_enabled
                  ? 'Claude builds the plan from your brief and the persona voice.'
                  : h?.ollama_enabled
                    ? 'Local LLM (Ollama) builds the plan — nothing leaves your machine.'
                    : 'Built-in planner active. Add ANTHROPIC_API_KEY or a local Ollama model in Settings for smarter plans.')}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 2, padding: 3, background: 'var(--bg-base)', borderRadius: 'var(--r-sm)', border: '1px solid var(--stroke)' }}>
            {[['generate','Generate'],['import','Import doc']].map(([k, l]) => (
              <button key={k} onClick={() => { setTab(k); setPlan(null); setErr(''); }} style={{
                height: 26, padding: '0 12px', background: tab === k ? 'var(--bg-panel)' : 'transparent',
                border: 0, borderRadius: 4, cursor: 'pointer',
                color: tab === k ? 'var(--ink-strong)' : 'var(--ink-soft)', fontSize: 11.5, fontWeight: 500,
              }}>{l}</button>
            ))}
          </div>
          <IconButton name="close" onClick={onClose} />
        </div>

        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {tab === 'generate' && (
            <Field label="Brief (what should this week say?)">
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3}
                placeholder="e.g. Week around the $DEEPOTUS staking launch. Tease Monday, reveal Wednesday 18:00, recap Sunday. Tone: prophetic, playful."
                style={{
                  width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)',
                  borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical',
                }} />
            </Field>
          )}

          {tab === 'import' && (
            <div
              onClick={() => fileRef.current?.click()}
              onDragOver={e => { e.preventDefault(); }}
              onDrop={e => { e.preventDefault(); importDoc(e.dataTransfer?.files?.[0]); }}
              style={{
                padding: 22, textAlign: 'center', cursor: 'pointer',
                background: 'var(--bg-base)', border: '1px dashed var(--stroke-strong)',
                borderRadius: 'var(--r)', color: 'var(--ink-soft)',
              }}>
              <input ref={fileRef} type="file" accept=".md,.markdown,.txt,.docx,.pdf" style={{ display: 'none' }}
                onChange={e => { importDoc(e.target.files?.[0]); e.target.value = ''; }} />
              <Icon name="upload" size={22} style={{ color: 'var(--cyan)' }} />
              <div style={{ fontSize: 13, color: 'var(--ink-strong)', marginTop: 8 }}>
                {plan?.filename ? plan.filename : 'Drop your strategy document here, or click to browse'}
              </div>
              <div style={{ fontSize: 11, marginTop: 4 }}>
                .md · .txt · .docx · .pdf — dates, weeks and themes in the document are preserved.
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 }}>
            {tab === 'generate' ? (
              <>
                <Field label="Days"><Select value={String(days)} onChange={v => setDays(Number(v))} options={['3','5','7','14'].map(d => ({ value: d, label: `${d} days` }))} /></Field>
                <Field label="Posts / day"><Select value={String(perDay)} onChange={v => setPerDay(Number(v))} options={['1','2','3'].map(d => ({ value: d, label: d }))} /></Field>
              </>
            ) : (
              <>
                <Field label="Horizon"><Select value={String(importDays)} onChange={v => setImportDays(Number(v))} options={['7','14','30','60'].map(d => ({ value: d, label: `${d} days` }))} /></Field>
                <Field label=" "><div style={{ fontSize: 10.5, color: 'var(--ink-muted)', paddingTop: 8 }}>day 1 = start date</div></Field>
              </>
            )}
            <Field label="Language"><Select value={language} onChange={setLanguage} options={[{ value: 'EN', label: 'English' }, { value: 'FR', label: 'Français' }]} /></Field>
            <Field label="Start date">
              <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{
                width: '100%', height: 30, padding: '0 8px', background: 'var(--bg-base)',
                border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)',
                color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', fontSize: 11.5,
                colorScheme: 'dark',
              }} />
            </Field>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="upper" style={{ color: 'var(--ink-soft)' }}>Channels</span>
            {CHANNEL_LIST.map(c => (
              <button key={c.id} onClick={() => toggleCh(c.id)} style={{
                height: 26, padding: '0 10px', display: 'inline-flex', alignItems: 'center', gap: 5,
                background: channels.includes(c.id) ? c.bg : 'transparent',
                border: `1px solid ${channels.includes(c.id) ? c.color + '66' : 'var(--stroke)'}`,
                borderRadius: 999, color: channels.includes(c.id) ? c.color : 'var(--ink-muted)',
                cursor: 'pointer', fontSize: 11, fontWeight: 500,
              }}>
                <Icon name={c.icon} size={11} />{c.label}
              </button>
            ))}
            <span style={{ flex: 1 }} />
            <Toggle checked={mode === 'auto'} label="Auto-publish (Telegram)" onChange={v => setMode(v ? 'auto' : 'assisted')} />
          </div>

          {err && (
            <div style={{ padding: 10, background: 'var(--red-soft)', border: '1px solid var(--red)', borderRadius: 'var(--r-sm)', fontSize: 11.5, color: 'var(--ink)' }}>
              {err}
            </div>
          )}

          {generating && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[0,1,2].map(i => (
                <div key={i} className="shimmer" style={{
                  height: 52, borderRadius: 'var(--r-sm)',
                  background: 'linear-gradient(90deg, var(--bg-panel) 25%, var(--bg-panel-2) 50%, var(--bg-panel) 75%)',
                  backgroundSize: '400% 100%',
                  animation: 'plan-shimmer 1.4s ease-in-out infinite',
                  animationDelay: `${i * 0.15}s`,
                  border: '1px solid var(--stroke)',
                }} />
              ))}
              <style>{`@keyframes plan-shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }`}</style>
            </div>
          )}

          {plan && !generating && (
            <div style={{ border: '1px solid var(--stroke)', borderRadius: 'var(--r)', overflow: 'hidden' }}>
              <div style={{ padding: '8px 12px', background: 'var(--bg-panel)', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11.5, color: 'var(--ink-strong)', fontWeight: 600 }}>{plan.posts.length} posts</span>
                <Badge tone={plan.engine === 'anthropic' ? 'violet' : plan.engine === 'ollama' ? 'cyan' : 'neutral'}>
                  {plan.engine === 'anthropic' ? 'Claude plan' : plan.engine === 'ollama' ? 'local LLM plan' : 'built-in plan'}
                </Badge>
              </div>
              <div style={{ padding: '6px 12px', background: 'var(--bg-base)', borderBottom: '1px solid var(--stroke)', fontSize: 10, color: 'var(--ink-soft)' }}>
                <Icon name="image" size={11} style={{ color: 'var(--amber)', marginRight: 5, verticalAlign: 'middle' }} />
                Pick a start image for each Seedance / image / news post — from your library, generate one from the plan's idea, or reuse a news picture. Leave on <span className="mono">auto</span> to decide later at Produce.
              </div>
              <div style={{ maxHeight: 300, overflowY: 'auto' }} className="scroll">
                {plan.posts.map((p, i) => (
                  <div key={i} style={{
                    display: 'grid', gridTemplateColumns: '58px 70px 1fr 188px', gap: 10,
                    padding: '9px 12px', borderTop: i ? '1px solid var(--stroke)' : 'none',
                    alignItems: 'center',
                  }}>
                    <span className="mono" style={{ fontSize: 10, color: 'var(--ink-soft)' }}>D{(p.day_offset ?? 0) + 1}·{p.time}</span>
                    <span style={{
                      fontSize: 9.5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5,
                      color: fmtColor[p.format] || 'var(--ink-soft)',
                    }}>{p.format}</span>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 12, color: 'var(--ink-strong)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.title}</div>
                      <div style={{ fontSize: 10.5, color: 'var(--ink-soft)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.caption}</div>
                    </div>
                    <PostSourceCell post={p} idx={i} images={images} newsItems={newsItems} source={sources[i]} setSource={setSource} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 10.5, color: 'var(--ink-muted)', flex: 1 }}>
            Plans land as {mode === 'auto' ? 'auto-publish' : 'assisted'} posts. Sources you pick are reused by the inspector's Produce button.
          </span>
          {tab === 'generate' && (
            <Button variant="outline" size="md" icon="sparkle" onClick={generate} disabled={generating || !prompt.trim()}>
              {generating ? 'Consulting the deep…' : plan ? 'Regenerate' : 'Generate'}
            </Button>
          )}
          {tab === 'import' && plan && (
            <Button variant="outline" size="md" icon="upload" onClick={() => fileRef.current?.click()} disabled={generating}>
              Re-import
            </Button>
          )}
          <Button variant="primary" size="md" icon="calendar" glow onClick={addToCalendar} disabled={!plan || adding}>
            {adding ? 'Adding…' : plan ? `Add ${plan.posts.length} posts to calendar` : 'Add to calendar'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export { SchedulerScreen, CHANNELS, CHANNEL_LIST };
