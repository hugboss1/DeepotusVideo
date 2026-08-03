// atoms.jsx — Deepotus Studio atomic components (ESM port)
import React, { useState, useRef, useEffect, useLayoutEffect, useMemo, useCallback, createContext, useContext } from 'react';

/* ───────────────── Icon ───────────────── */
// All inline SVG; size by font-size. Stroke-based for crispness.
const ICONS = {
  octopus: <g fill="currentColor"><path d="M12 2.4c-3.6 0-6.4 2.7-6.4 6.4 0 1.4.4 2.3.4 3 0 .4-.2.7-.6 1L4 14c-.9.5-1.4 1.3-1.4 2.2 0 1.2.9 2 2 2 .8 0 1.4-.4 1.7-1l.5-1.2c.2-.4.6-.6 1-.4.4.2.5.6.4 1l-.5 1.3c-.4 1-.1 2 .8 2.5.9.5 2 .2 2.5-.8l.4-1c.2-.4.6-.5 1-.4.4.2.6.6.4 1l-.4.9c-.4 1-.1 2 .8 2.5.9.5 2 .2 2.5-.8l.5-1c.2-.4.6-.5 1-.4.4.2.5.6.3 1l-.4.8c-.5 1-.1 2.1.8 2.5.9.5 2 .1 2.5-.8.3-.7.4-1.3.4-2 0-.9-.4-1.7-1.3-2.2l-1.4-.7c-.4-.2-.6-.6-.6-1 0-.6.4-1.6.4-3 0-3.7-2.8-6.4-6.4-6.4z"/><circle cx="9.8" cy="8.6" r=".9" fill="#02060d"/><circle cx="14.2" cy="8.6" r=".9" fill="#02060d"/></g>,
  play:    <path fill="currentColor" d="M6 4l14 8-14 8V4z"/>,
  preview: <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M4 12a8 8 0 1 0 16 0 8 8 0 0 0-16 0zm0 0h16"/>,
  download:<path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 4v12m0 0l-4-4m4 4l4-4M4 18v2h16v-2"/>,
  upload:  <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 20V8m0 0l-4 4m4-4l4 4M4 4v2h16V4"/>,
  search:  <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm5-2l5 5"/>,
  plus:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 5v14M5 12h14"/>,
  minus:   <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M5 12h14"/>,
  close:   <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M6 6l12 12M18 6L6 18"/>,
  more:    <g fill="currentColor"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></g>,
  edit:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M3 21v-4l12-12 4 4-12 12H3zm12-16l4 4"/>,
  trash:   <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>,
  copy:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M8 8h11v13H8V8zM5 5h11v3M5 5v13h3"/>,
  rename:  <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M14 4v16M10 4v16M6 8h2M6 16h2M16 8h2M16 16h2"/>,
  bolt:    <path fill="currentColor" d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>,
  film:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M4 4h16v16H4V4zm0 4h16M4 12h16M4 16h16M8 4v16M16 4v16"/>,
  mic:     <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zm-7 9a7 7 0 0 0 14 0M12 19v3"/>,
  layers:  <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 3l9 5-9 5-9-5 9-5zm-9 9l9 5 9-5M3 17l9 5 9-5"/>,
  rss:     <g fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M5 5a14 14 0 0 1 14 14M5 11a8 8 0 0 1 8 8"/><circle cx="5.5" cy="18.5" r="1.5" fill="currentColor" stroke="none"/></g>,
  folder:  <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z"/>,
  cog:     <g fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M22 12h-3M5 12H2M19.07 4.93l-2.12 2.12M7.05 16.95l-2.12 2.12M19.07 19.07l-2.12-2.12M7.05 7.05L4.93 4.93"/></g>,
  zap:     <path fill="currentColor" d="M11 2v8H6l7 12v-8h5L11 2z"/>,
  image:   <g fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M3 17l5-5 4 4 3-3 6 6"/></g>,
  sparkle: <path fill="currentColor" d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6L12 2zM19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14z"/>,
  signal:  <g fill="currentColor"><rect x="4" y="14" width="3" height="6" rx="1"/><rect x="10" y="9" width="3" height="11" rx="1"/><rect x="16" y="4" width="3" height="16" rx="1"/></g>,
  caret:   <path fill="currentColor" d="M7 10l5 5 5-5H7z"/>,
  caretR:  <path fill="currentColor" d="M10 7l5 5-5 5V7z"/>,
  check:   <path stroke="currentColor" strokeWidth="2" fill="none" d="M5 13l4 4 10-10"/>,
  flow:    <g fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8 7l8 0M7 8l4 8M17 8l-4 8"/></g>,
  wave:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M2 12c2 0 2-6 4-6s2 12 4 12 2-12 4-12 2 12 4 12 2-6 4-6"/>,
  link:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11.5 7M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7L12.5 17"/>,
  warn:    <g fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 3L2 21h20L12 3z"/><path d="M12 10v5M12 18v.5" strokeLinecap="round"/></g>,
  grid:    <g fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></g>,
  calendar:<g fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></g>,
  clock:   <g fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></g>,
  send:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>,
  book:    <path stroke="currentColor" strokeWidth="1.6" fill="none" d="M12 6c-2-1.5-4.5-2-8-2v14c3.5 0 6 .5 8 2 2-1.5 4.5-2 8-2V4c-3.5 0-6 .5-8 2zm0 0v14"/>,
  channelX:        <path fill="currentColor" d="M17.5 3h3.2l-7 8 8.2 10h-6.4l-5-6.5-5.8 6.5H1.5l7.5-8.6L1 3h6.6l4.5 6 5.4-6zm-1.1 16h1.8L7.7 5H5.8l10.6 14z"/>,
  channelTelegram: <path fill="currentColor" d="M22 3L2.5 10.7c-1 .4-1 1.5 0 1.9l4.8 1.7 1.9 5.7c.3.8 1.1 1 1.7.3l2.8-2.5 4.9 3.5c.9.7 1.7.3 1.9-.8L22.7 4.4c.3-1.2-.6-1.9-1.7-1.4zM9.7 14.6l9.3-7.4c.2-.2.5.1.3.3l-7.4 7.6-.3 4.1-1.9-4.6z"/>,
  channelYoutube:  <g fill="currentColor"><path d="M22 7.5c-.2-1.6-.9-2.6-2.5-2.8-2.8-.4-7.5-.4-7.5-.4s-4.7 0-7.5.4C2.9 4.9 2.2 5.9 2 7.5 1.7 9.5 1.7 12 1.7 12s0 2.5.3 4.5c.2 1.6.9 2.6 2.5 2.8 2.8.4 7.5.4 7.5.4s4.7 0 7.5-.4c1.6-.2 2.3-1.2 2.5-2.8.3-2 .3-4.5.3-4.5s0-2.5-.3-4.5z"/><path fill="#02060d" d="M10 15.5l5-3.5-5-3.5v7z"/></g>,
  channelInstagram:<g fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></g>,
};

function Icon({ name, size = 16, style }) {
  const path = ICONS[name];
  if (!path) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}>{path}</svg>
  );
}

/* ───────────────── Button ───────────────── */
function Button({ variant = 'ghost', size = 'md', icon, iconRight, glow, children, style, ...rest }) {
  const H = { sm: 26, md: 32, lg: 38 }[size];
  const padX = { sm: 9, md: 12, lg: 16 }[size];
  const fontSize = { sm: 11.5, md: 12.5, lg: 13.5 }[size];
  const base = {
    height: H, padding: `0 ${padX}px`,
    display: 'inline-flex', alignItems: 'center', gap: 7,
    fontSize, fontWeight: 500, fontFamily: 'var(--f-ui)',
    borderRadius: 'var(--r-sm)',
    border: '1px solid transparent',
    cursor: 'pointer',
    transition: `background var(--dur-1) var(--ease), border-color var(--dur-1) var(--ease), color var(--dur-1) var(--ease), box-shadow var(--dur-2) var(--ease), transform var(--dur-1) var(--ease)`,
    userSelect: 'none', whiteSpace: 'nowrap',
  };
  const variants = {
    primary: {
      background: 'linear-gradient(180deg, #00e5ff 0%, #00b8cc 100%)',
      color: '#02060d', borderColor: '#00e5ff',
      boxShadow: glow ? '0 0 24px var(--cyan-glow), inset 0 1px 0 #ffffff66' : 'inset 0 1px 0 #ffffff66',
      fontWeight: 600,
    },
    violet: {
      background: 'linear-gradient(180deg, #c084fc 0%, #9333ea 100%)',
      color: '#02060d', borderColor: '#a855f7', fontWeight: 600,
      boxShadow: glow ? '0 0 24px var(--violet-soft), inset 0 1px 0 #ffffff44' : 'inset 0 1px 0 #ffffff44',
    },
    ghost: {
      background: 'transparent', color: 'var(--ink)', borderColor: 'transparent',
    },
    outline: {
      background: 'var(--bg-panel)', color: 'var(--ink-strong)', borderColor: 'var(--stroke-strong)',
    },
    soft: {
      background: 'var(--bg-panel-2)', color: 'var(--ink-strong)', borderColor: 'var(--stroke)',
    },
    danger: {
      background: 'transparent', color: 'var(--red)', borderColor: 'transparent',
    },
    link: {
      background: 'transparent', color: 'var(--cyan)', borderColor: 'transparent', padding: 0, height: 'auto',
    },
  };
  const [hover, setHover] = useState(false);
  const hovers = {
    primary: { transform: 'translateY(-1px)', boxShadow: '0 0 32px var(--cyan-glow), inset 0 1px 0 #ffffff66' },
    violet:  { transform: 'translateY(-1px)', boxShadow: '0 0 32px var(--violet-soft), inset 0 1px 0 #ffffff44' },
    ghost:   { background: 'var(--bg-panel-2)', color: 'var(--ink-strong)' },
    outline: { borderColor: 'var(--cyan)', color: 'var(--ink-strong)' },
    soft:    { borderColor: 'var(--stroke-strong)' },
    danger:  { background: 'var(--red-soft)', borderColor: 'var(--red)' },
    link:    { color: 'var(--ink-strong)' },
  };
  return (
    <button
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ ...base, ...variants[variant], ...(hover ? hovers[variant] : {}), ...style }}
      {...rest}
    >
      {icon && <Icon name={icon} size={size === 'sm' ? 13 : 15} />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === 'sm' ? 13 : 15} />}
    </button>
  );
}

/* ───────────────── IconButton ───────────────── */
function IconButton({ name, size = 28, iconSize, title, active, children, style, ...rest }) {
  const [h, setH] = useState(false);
  return (
    <button
      title={title}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        width: size, height: size, borderRadius: 'var(--r-sm)',
        background: active ? 'var(--cyan-soft)' : (h ? 'var(--bg-panel-2)' : 'transparent'),
        color: active ? 'var(--cyan)' : (h ? 'var(--ink-strong)' : 'var(--ink-soft)'),
        border: active ? '1px solid var(--cyan)' : '1px solid transparent',
        cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all var(--dur-1) var(--ease)',
        ...style,
      }}
      {...rest}
    >
      {children || <Icon name={name} size={iconSize || Math.floor(size * 0.55)} />}
    </button>
  );
}

/* ───────────────── Input ───────────────── */
function Input({ icon, placeholder, value, onChange, mono, style, ...rest }) {
  const [focus, setFocus] = useState(false);
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      height: 30, padding: '0 10px',
      background: 'var(--bg-base)',
      border: `1px solid ${focus ? 'var(--cyan)' : 'var(--stroke)'}`,
      borderRadius: 'var(--r-sm)',
      transition: 'border-color var(--dur-1) var(--ease), box-shadow var(--dur-1) var(--ease)',
      boxShadow: focus ? '0 0 0 3px var(--cyan-soft)' : 'none',
      ...style,
    }}>
      {icon && <Icon name={icon} size={13} style={{ color: 'var(--ink-soft)' }} />}
      <input
        placeholder={placeholder}
        value={value ?? ''}
        onChange={e => onChange?.(e.target.value)}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{ flex: 1, fontFamily: mono ? 'var(--f-mono)' : 'var(--f-ui)', fontSize: 12.5, minWidth: 0 }}
        {...rest}
      />
    </div>
  );
}

/* ───────────────── Badge / Tag / Chip ───────────────── */
function Badge({ tone = 'neutral', dot, children, style }) {
  const tones = {
    neutral: { color: 'var(--ink-soft)', bg: 'var(--bg-panel-2)', bd: 'var(--stroke)' },
    cyan:    { color: 'var(--cyan)', bg: 'var(--cyan-soft)', bd: '#00e5ff44' },
    violet:  { color: 'var(--violet)', bg: 'var(--violet-soft)', bd: '#a855f744' },
    amber:   { color: 'var(--amber)', bg: 'var(--amber-soft)', bd: '#fbbf2444' },
    green:   { color: 'var(--green)', bg: 'var(--green-soft)', bd: '#22c55e44' },
    red:     { color: 'var(--red)', bg: 'var(--red-soft)', bd: '#ef444444' },
  };
  const t = tones[tone];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      height: 22, padding: '0 8px',
      fontSize: 11, fontWeight: 500,
      color: t.color, background: t.bg, border: `1px solid ${t.bd}`,
      borderRadius: 'var(--r-pill)', letterSpacing: 0,
      ...style,
    }}>
      {dot && <span style={{ width: 6, height: 6, borderRadius: 999, background: t.color, boxShadow: `0 0 6px ${t.color}` }} />}
      {children}
    </span>
  );
}

/* ───────────────── Toggle ───────────────── */
function Toggle({ checked, onChange, label }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
      <span onClick={() => onChange?.(!checked)} style={{
        width: 30, height: 18, borderRadius: 999,
        background: checked ? 'var(--cyan)' : 'var(--stroke-strong)',
        position: 'relative', transition: 'background var(--dur-2) var(--ease)',
        boxShadow: checked ? '0 0 12px var(--cyan-glow)' : 'none',
      }}>
        <span style={{
          position: 'absolute', top: 2, left: checked ? 14 : 2,
          width: 14, height: 14, borderRadius: 999,
          background: checked ? '#02060d' : 'var(--ink)',
          transition: 'left var(--dur-2) var(--ease)',
        }} />
      </span>
      {label && <span style={{ fontSize: 12, color: 'var(--ink)' }}>{label}</span>}
    </label>
  );
}

/* ───────────────── Slider ───────────────── */
function Slider({ value, min = 0, max = 100, step = 1, onChange, unit = '', label }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
          <span style={{ color: 'var(--ink-soft)' }}>{label}</span>
          <span style={{ color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)' }}>{value}{unit}</span>
        </div>
      )}
      <div style={{ position: 'relative', height: 18, display: 'flex', alignItems: 'center' }}>
        <div style={{ position: 'absolute', inset: '7px 0', borderRadius: 999, background: 'var(--bg-base)', border: '1px solid var(--stroke)' }} />
        <div style={{ position: 'absolute', left: 0, top: 7, bottom: 7, width: `${pct}%`, background: 'linear-gradient(90deg, var(--cyan), var(--violet))', borderRadius: 999 }} />
        <input type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange?.(Number(e.target.value))}
          style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', cursor: 'pointer' }} />
        <div style={{
          position: 'absolute', left: `calc(${pct}% - 7px)`, width: 14, height: 14, borderRadius: 999,
          background: 'var(--ink-strong)', boxShadow: '0 0 0 3px var(--bg-base), 0 0 12px var(--cyan-glow)',
          pointerEvents: 'none',
        }} />
      </div>
    </div>
  );
}

/* ───────────────── Panel ───────────────── */
function Panel({ elevated, children, style, ...rest }) {
  return (
    <div style={{
      background: elevated ? 'var(--bg-panel-2)' : 'var(--bg-panel)',
      border: '1px solid var(--stroke)',
      borderRadius: 'var(--r-lg)',
      boxShadow: 'var(--shadow-1)',
      ...style,
    }} {...rest}>{children}</div>
  );
}

/* ───────────────── InspectorSection ───────────────── */
function InspectorSection({ label, defaultOpen = true, right, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderBottom: '1px solid var(--stroke)' }}>
      <button onClick={() => setOpen(!open)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px', background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--ink-soft)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="caretR" size={12} style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform var(--dur-1) var(--ease)' }} />
          <span className="upper">{label}</span>
        </span>
        {right}
      </button>
      {open && <div style={{ padding: '4px 14px 12px' }}>{children}</div>}
    </div>
  );
}

/* ───────────────── Field (label + control) ───────────────── */
function Field({ label, hint, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
      {label && <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{label}</div>}
      {children}
      {hint && <div style={{ fontSize: 10.5, color: 'var(--ink-muted)' }}>{hint}</div>}
    </div>
  );
}

/* ───────────────── Select ───────────────── */
function Select({ value, options, onChange, style }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();
  useEffect(() => {
    function h(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  const cur = options.find(o => (o.value ?? o) === value);
  return (
    <div ref={ref} style={{ position: 'relative', ...style }}>
      <button onClick={() => setOpen(!open)} style={{
        width: '100%', height: 30, padding: '0 10px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--bg-base)', border: `1px solid ${open ? 'var(--cyan)' : 'var(--stroke)'}`,
        borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', cursor: 'pointer',
        fontSize: 12.5,
      }}>
        <span>{cur?.label ?? cur ?? '—'}</span>
        <Icon name="caret" size={12} style={{ color: 'var(--ink-soft)' }} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 100,
          background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
          borderRadius: 'var(--r-sm)', boxShadow: 'var(--shadow-2)', overflow: 'hidden',
          maxHeight: 240, overflowY: 'auto',
        }} className="scroll">
          {options.map((o, i) => {
            const v = o.value ?? o, l = o.label ?? o;
            return (
              <button key={i} onClick={() => { onChange?.(v); setOpen(false); }} style={{
                width: '100%', padding: '8px 10px', textAlign: 'left',
                background: v === value ? 'var(--cyan-soft)' : 'transparent',
                color: v === value ? 'var(--cyan)' : 'var(--ink)',
                border: 0, cursor: 'pointer', fontSize: 12.5,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}
              onMouseEnter={e => { if (v !== value) e.currentTarget.style.background = 'var(--bg-panel-3)'; }}
              onMouseLeave={e => { if (v !== value) e.currentTarget.style.background = 'transparent'; }}
              >
                <span>{l}</span>
                {v === value && <Icon name="check" size={12} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ───────────────── Progress ───────────────── */
function Progress({ value, indeterminate, tone = 'cyan' }) {
  return (
    <div style={{
      width: '100%', height: 4, borderRadius: 999, overflow: 'hidden',
      background: 'var(--bg-base)', border: '1px solid var(--stroke)',
    }}>
      <div className={indeterminate ? 'shimmer' : ''} style={{
        height: '100%',
        width: indeterminate ? '100%' : `${value}%`,
        background: indeterminate ? undefined : `linear-gradient(90deg, var(--cyan), var(--violet))`,
        transition: 'width 300ms var(--ease)',
        boxShadow: '0 0 12px var(--cyan-glow)',
      }} />
    </div>
  );
}

/* ───────────────── Thumb (placeholder media) ───────────────── */
function Thumb({ kind = 'image', label, size = 56, ratio, style }) {
  // kind: image | video | avatar | audio | render
  const accents = { image: 'var(--amber)', video: 'var(--cyan)', avatar: 'var(--violet)', audio: 'var(--green)', render: 'var(--ink)' };
  const tints   = { image: '#3a2a05', video: '#053040', avatar: '#2a0d3e', audio: '#063020', render: '#1a253a' };
  const labels  = { image: 'IMG', video: 'CLIP', avatar: 'AVT', audio: 'WAV', render: 'OUT' };
  const w = ratio ? size : size;
  const h = ratio ? Math.round(size * ratio) : size;
  return (
    <div style={{
      width: w, height: h, borderRadius: 'var(--r-sm)',
      background: `linear-gradient(135deg, ${tints[kind]} 0%, #02060d 100%)`,
      border: `1px solid var(--stroke)`,
      position: 'relative', overflow: 'hidden', flexShrink: 0,
      ...style,
    }}>
      {/* diagonal stripes placeholder */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `repeating-linear-gradient(45deg, transparent 0 6px, ${accents[kind]}10 6px 7px)`,
      }} />
      {kind === 'audio' && (
        <svg viewBox="0 0 60 30" style={{ position: 'absolute', inset: '20% 10%', color: accents.audio }}>
          <path stroke="currentColor" strokeWidth="1.5" fill="none" d="M0 15 Q5 5 10 15 T20 15 T30 15 T40 15 T50 15 T60 15" />
        </svg>
      )}
      <div style={{
        position: 'absolute', top: 4, left: 4,
        padding: '2px 5px', fontSize: 9, fontWeight: 600, fontFamily: 'var(--f-mono)',
        color: accents[kind], background: '#02060daa', borderRadius: 3, letterSpacing: 0.5,
      }}>{labels[kind]}</div>
      {label && (
        <div style={{
          position: 'absolute', bottom: 4, left: 4, right: 4,
          fontSize: 9, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{label}</div>
      )}
    </div>
  );
}

/* ───────────────── Logo / Wordmark (white-label aware) ───────────────── */
import { useBranding as _useBranding, api as _brandApi } from './api.js';

function Logo({ compact, size = 16 }) {
  const b = _useBranding();
  const dim = size + 14;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-strong)' }}>
      <span style={{
        width: dim, height: dim, borderRadius: '50%',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        background: 'radial-gradient(circle at 30% 25%, color-mix(in srgb, var(--brand) 20%, transparent) 0%, transparent 60%), radial-gradient(circle at 75% 80%, color-mix(in srgb, var(--cyan) 13%, transparent) 0%, transparent 55%)',
        boxShadow: '0 0 18px var(--brand-soft)',
        flexShrink: 0,
      }}>
        <img src={_brandApi.brandLogoUrl()} alt={b.app_name} width={dim} height={dim}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
          style={{ width: '100%', height: '100%', objectFit: 'contain', borderRadius: '50%', filter: 'drop-shadow(0 0 6px var(--brand-soft))' }} />
      </span>
      {!compact && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
          <span className="display" style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.04em', color: 'var(--brand)' }}>{b.app_name}</span>
          <span style={{ fontSize: 9, color: 'var(--ink-soft)', letterSpacing: '0.18em', fontWeight: 500, marginTop: 2 }}>{b.app_sub} · v1.14.0</span>
        </div>
      )}
    </div>
  );
}

/* ───────────────── Expose ───────────────── */
export {
  Icon, Button, IconButton, Input, Badge, Toggle, Slider,
  Panel, InspectorSection, Field, Select, Progress, Thumb, Logo,
};
