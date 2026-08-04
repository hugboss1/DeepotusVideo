// nodes.jsx — Node catalog + node card rendering for the Studio (ESM port)
import React, { useState as useStateN, useRef as useRefN, useEffect as useEffectN } from 'react';
import { Icon, Badge, Thumb } from './atoms.jsx';
import { api } from './api.js';

/* Port types and their colors. */
const PORT = {
  image: { color: 'var(--node-image)', label: 'image' },
  video: { color: 'var(--node-video)', label: 'video' },
  audio: { color: 'var(--node-audio)', label: 'audio' },
  av:    { color: 'var(--node-av)',    label: 'av'    },
  text:  { color: 'var(--node-text)',  label: 'text'  },
  data:  { color: 'var(--node-data)',  label: 'data'  },
};

const CAT = {
  source:  { color: 'var(--amber)',  label: 'Source',      icon: 'image' },
  gen:     { color: 'var(--cyan)',   label: 'Generator',   icon: 'sparkle' },
  audio:   { color: 'var(--green)',  label: 'Audio',       icon: 'wave' },
  edit:    { color: 'var(--violet)', label: 'Edit',        icon: 'film' },
  compose: { color: '#06b6d4',       label: 'Composition', icon: 'layers' },
  master:  { color: 'var(--red)',    label: 'Master',      icon: 'warn' },
  output:  { color: '#ffffff',       label: 'Output',      icon: 'download' },
};

/* Node catalog: each entry defines title, category, ports, default props.  */
const NODE_TYPES = {
  /* Sources */
  Image:          { cat: 'source', title: 'Image',          desc: 'Pick a still image',          inPorts: [], outPorts: [{ id: 'out', type: 'image' }],         props: { filename: 'octopus_throne.png' } },
  Text:           { cat: 'source', title: 'Text',           desc: 'Plain text input',            inPorts: [], outPorts: [{ id: 'out', type: 'text'  }],         props: { value: 'From the deep, the prophecy ascends.' } },
  ExistingRender: { cat: 'source', title: 'Existing render',desc: 'Reuse a previous render',     inPorts: [], outPorts: [{ id: 'out', type: 'av'    }],         props: { jobId: 'job_2k1f4a', durationS: 18.4 } },
  Upload:         { cat: 'source', title: 'UGC video',      desc: 'Upload your own clip',        inPorts: [], outPorts: [{ id: 'out', type: 'av'    }],         props: { jobId: '', filename: '', durationS: 0, master: true } },
  NewsItem:       { cat: 'source', title: 'News item',      desc: 'Pick from RSS feed',          inPorts: [], outPorts: [{ id: 'out', type: 'data'  }],         props: { title: 'Solana memecoin volume +38% in 24h', source: 'cryptoslate.com' } },

  /* Generators */
  Seedance:       { cat: 'gen',    title: 'Seedance',       desc: 'image → cinematic clip',      inPorts: [{ id: 'image', type: 'image' }, { id: 'end', type: 'image' }, { id: 'prompt', type: 'text' }], outPorts: [{ id: 'out', type: 'video' }], props: { style: 'cinematic', durationS: 10, aspect: '9:16', seed: 4421, extendMode: 'loop' } },
  HeyGenAvatar:   { cat: 'gen',    title: 'HeyGen avatar',  desc: 'script → talking avatar',     inPorts: [{ id: 'script', type: 'text' }], outPorts: [{ id: 'out', type: 'av' }], props: { avatar: 'Asha · prophetess', voice: 'Asha · EN', speedX: 1.0 } },
  NewsScript:     { cat: 'gen',    title: 'News script',    desc: 'news → prophet voice',        inPorts: [{ id: 'news', type: 'data' }], outPorts: [{ id: 'script', type: 'text' }, { id: 'essences', type: 'data' }], props: { useAnthropic: true, words: 80 } },
  NewsIllustration:{cat: 'gen',    title: 'News illust.',   desc: 'news → reel B-roll',          inPorts: [{ id: 'news', type: 'data' }], outPorts: [{ id: 'out', type: 'video' }], props: { style: 'cinematic-deep', durationS: 15 } },

  /* Audio */
  Voiceover:      { cat: 'audio',  title: 'Voiceover',      desc: 'ElevenLabs TTS',              inPorts: [{ id: 'text', type: 'text' }], outPorts: [{ id: 'out', type: 'audio' }], props: { voice: 'Adam · oracular', stability: 0.6 } },
  MusicTrack:     { cat: 'audio',  title: 'Music track',    desc: 'Looped BGM',                  inPorts: [{ id: 'src', type: 'audio' }], outPorts: [{ id: 'out', type: 'audio' }], props: { volumeDb: -14, loop: true } },
  AudioMix:       { cat: 'audio',  title: 'Audio mix',      desc: 'Mix N tracks',                inPorts: [{ id: 'a', type: 'audio' }, { id: 'b', type: 'audio' }], outPorts: [{ id: 'out', type: 'audio' }], props: { duckDb: -8, fadeInS: 0.4, fadeOutS: 0.6 } },
  Loudness:       { cat: 'audio',  title: 'Loudness norm.', desc: 'LUFS target',                 inPorts: [{ id: 'in', type: 'audio' }], outPorts: [{ id: 'out', type: 'audio' }], props: { lufs: -14 } },

  /* Edit */
  Trim:           { cat: 'edit',   title: 'Trim',           desc: 'cut start/end',               inPorts: [{ id: 'in', type: 'av' }], outPorts: [{ id: 'out', type: 'av' }], props: { startS: 0, endS: 6, lengthMode: 'source' } },
  Extend:         { cat: 'edit',   title: 'Extend',         desc: 'loop or hold tail',           inPorts: [{ id: 'in', type: 'video' }], outPorts: [{ id: 'out', type: 'video' }], props: { targetS: 18, mode: 'loop' } },
  Concatenate:    { cat: 'edit',   title: 'Concatenate',    desc: 'xfade · cut · glitch',        inPorts: [{ id: 'a', type: 'av' }, { id: 'b', type: 'av' }, { id: 'c', type: 'av' }], outPorts: [{ id: 'out', type: 'av' }], props: { transition: 'crossfade', durationS: 0.4 } },
  Split:          { cat: 'edit',   title: 'Split',          desc: 'cut at point',                inPorts: [{ id: 'in', type: 'av' }], outPorts: [{ id: 'a', type: 'av' }, { id: 'b', type: 'av' }], props: { atS: 5.0 } },
  Speed:          { cat: 'edit',   title: 'Speed',          desc: 'time-stretch',                inPorts: [{ id: 'in', type: 'video' }], outPorts: [{ id: 'out', type: 'video' }], props: { factor: 1.0 } },

  /* Composition */
  SpatialCompose: { cat: 'compose',title: 'Spatial compose',desc: 'layout 9:16 regions',         inPorts: [{ id: 'reel', type: 'av' }, { id: 'avatar', type: 'av' }, { id: 'brand', type: 'image' }, { id: 'bg', type: 'image' }], outPorts: [{ id: 'out', type: 'av' }], props: { templateId: 'tpl_news_reel', useAsMaster: false, tailPadS: 0.4 } },
  BrandStrip:     { cat: 'compose',title: 'Brand strip',    desc: 'mark + text → image',         inPorts: [{ id: 'data', type: 'data' }], outPorts: [{ id: 'out', type: 'image' }], props: { mark: '🐙', text: 'DEEPOTUS' } },
  TextOverlay:    { cat: 'compose',title: 'Text overlay',   desc: 'caption on video',            inPorts: [{ id: 'in', type: 'video' }], outPorts: [{ id: 'out', type: 'video' }], props: { text: 'oracle says: send.', font: 'Space Grotesk', size: 64, pulse: true, startS: 0, endS: 4 } },
  Ticker:         { cat: 'compose',title: 'Ticker',         desc: 'scrolling text',              inPorts: [{ id: 'in', type: 'video' }, { id: 'text', type: 'text' }], outPorts: [{ id: 'out', type: 'video' }], props: { speed: 60, direction: 'left' } },
  Separator:      { cat: 'compose',title: 'Separator',      desc: 'thin divider image',          inPorts: [], outPorts: [{ id: 'out', type: 'image' }], props: { color: '#00e5ff', thickness: 2 } },

  /* Master */
  AvatarMaster:   { cat: 'master', title: 'Avatar master',  desc: 'duration master',             inPorts: [{ id: 'in', type: 'av' }], outPorts: [{ id: 'out', type: 'av' }], props: { tailPadS: 0.4, fadeOutS: 0.3 } },

  /* Output */
  Render:         { cat: 'output', title: 'Render',         desc: 'final encode',                inPorts: [{ id: 'in', type: 'av' }], outPorts: [], props: { format: '9:16', fps: 30, crf: 20, name: 'tweet_2026-05-20', voiceMode: 'passthrough' } },
};

/* The palette grouping. */
const PALETTE_GROUPS = [
  { cat: 'source',  types: ['Image','Text','ExistingRender','Upload','NewsItem'] },
  { cat: 'gen',     types: ['Seedance','HeyGenAvatar','NewsScript','NewsIllustration'] },
  { cat: 'audio',   types: ['Voiceover','MusicTrack','AudioMix','Loudness'] },
  { cat: 'edit',    types: ['Trim','Extend','Concatenate','Split','Speed'] },
  { cat: 'compose', types: ['SpatialCompose','BrandStrip','TextOverlay','Ticker','Separator'] },
  { cat: 'master',  types: ['AvatarMaster'] },
  { cat: 'output',  types: ['Render'] },
];

/* Node dimensions (used by editor for layout/edge anchoring). */
const NODE_W = 220;
const NODE_HEADER_H = 36;
const NODE_PORT_ROW = 22;
const NODE_THUMB_H = 92;
const NODE_FOOT_H = 30;

function nodeHeight(type, variant) {
  const spec = NODE_TYPES[type];
  const portRows = Math.max(spec.inPorts.length, spec.outPorts.length);
  const portsH = Math.max(portRows, 1) * NODE_PORT_ROW + 8;
  const thumbH = variant === 'reef' ? NODE_THUMB_H : 0;
  const footH = variant === 'reef' ? NODE_FOOT_H : 14;
  return NODE_HEADER_H + portsH + thumbH + footH;
}

/* Anchor positions (relative to node top-left) for a given port. */
function portAnchor(type, side, portId, variant) {
  const spec = NODE_TYPES[type];
  const list = side === 'in' ? spec.inPorts : spec.outPorts;
  const idx = list.findIndex(p => p.id === portId);
  if (idx < 0) return { x: 0, y: 0 };
  const x = side === 'in' ? 0 : NODE_W;
  const y = NODE_HEADER_H + 12 + idx * NODE_PORT_ROW;
  return { x, y };
}

/* ────────────────────── NodeCard ────────────────────── */
function NodeCard({ node, variant, selected, status, onMouseDown, onPortPress, onPortRelease, onClick, onDelete }) {
  const spec = NODE_TYPES[node.type];
  const cat = CAT[spec.cat];
  const isReef = variant === 'reef';

  const borderColor = selected
    ? 'var(--cyan)'
    : status === 'failed' ? 'var(--red)'
    : status === 'succeeded' ? 'var(--green)'
    : cat.color;
  const cardBg = isReef
    ? `linear-gradient(180deg, var(--bg-panel-2) 0%, var(--bg-panel) 100%)`
    : 'var(--bg-panel)';

  const halo = status === 'running'
    ? { '--node-color': cat.color + '66', boxShadow: `0 0 0 1px ${cat.color}, 0 0 40px ${cat.color}55` }
    : selected
    ? { boxShadow: '0 0 0 1px var(--cyan), 0 0 32px var(--cyan-soft)' }
    : { boxShadow: 'var(--shadow-1)' };

  return (
    <div
      data-node-id={node.id}
      onMouseDown={onMouseDown}
      onClick={onClick}
      className={status === 'running' ? 'pulse' : ''}
      style={{
        position: 'absolute',
        left: node.x, top: node.y,
        width: NODE_W,
        background: cardBg,
        borderRadius: isReef ? 14 : 10,
        border: `1px solid ${borderColor}`,
        color: 'var(--ink)',
        userSelect: 'none', cursor: 'grab',
        ...halo,
        transition: 'box-shadow 200ms var(--ease), border-color 200ms var(--ease)',
      }}
    >
      {/* Header */}
      <div style={{
        height: NODE_HEADER_H, padding: '0 10px',
        display: 'flex', alignItems: 'center', gap: 8,
        borderBottom: `1px solid var(--stroke)`,
        background: `linear-gradient(180deg, ${cat.color}1a 0%, transparent 100%)`,
        borderTopLeftRadius: isReef ? 13 : 9,
        borderTopRightRadius: isReef ? 13 : 9,
      }}>
        <span style={{
          width: 18, height: 18, borderRadius: 5,
          background: cat.color + '22', color: cat.color,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name={cat.icon} size={11} />
        </span>
        <span style={{ flex: 1, fontSize: 12.5, fontWeight: 600, color: 'var(--ink-strong)' }}>
          {spec.title}
        </span>
        {status === 'running' && <Badge tone="cyan" dot>run</Badge>}
        {status === 'succeeded' && <Badge tone="green" dot>ok</Badge>}
        {status === 'failed' && <Badge tone="red" dot>err</Badge>}
        {status === 'queued' && <Badge tone="neutral">queued</Badge>}
        {onDelete && (
          <button
            onMouseDown={e => { e.stopPropagation(); }}
            onClick={e => { e.stopPropagation(); onDelete(); }}
            title="Delete node"
            style={{
              width: 18, height: 18, borderRadius: 5, border: 0, cursor: 'pointer',
              background: 'transparent', color: 'var(--ink-muted)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              transition: 'background var(--dur-1) var(--ease), color var(--dur-1) var(--ease)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--red-soft)'; e.currentTarget.style.color = 'var(--red)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--ink-muted)'; }}
          >
            <Icon name="close" size={12} />
          </button>
        )}
      </div>

      {/* Ports */}
      <div style={{ position: 'relative', minHeight: 16, padding: '8px 0' }}>
        {spec.inPorts.map((p, i) => (
          <PortRow key={p.id} side="in" port={p} index={i}
            onPress={(e) => onPortPress(node.id, 'in', p, e)}
            onRelease={(e) => onPortRelease(node.id, 'in', p, e)} />
        ))}
        {spec.outPorts.map((p, i) => (
          <PortRow key={p.id} side="out" port={p} index={i}
            onPress={(e) => onPortPress(node.id, 'out', p, e)}
            onRelease={(e) => onPortRelease(node.id, 'out', p, e)} />
        ))}
      </div>

      {/* Reef variant: media preview slab */}
      {isReef && (
        <div style={{
          height: NODE_THUMB_H, margin: '4px 10px 0',
          borderRadius: 8, overflow: 'hidden',
          border: '1px solid var(--stroke)',
          position: 'relative',
        }}>
          <NodePreview node={node} status={status} />
        </div>
      )}

      {/* Foot meta line */}
      <div style={{
        height: isReef ? NODE_FOOT_H : 14,
        padding: isReef ? '0 12px' : '0 10px 6px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10.5, color: 'var(--ink-muted)', fontFamily: 'var(--f-mono)',
      }}>
        <span>{nodeMetaLeft(node)}</span>
        <span>{nodeMetaRight(node)}</span>
      </div>
    </div>
  );
}

function PortRow({ side, port, index, onPress, onRelease }) {
  const c = PORT[port.type].color;
  return (
    <div style={{
      position: 'absolute',
      top: 8 + index * NODE_PORT_ROW + 2,
      left: side === 'in' ? -8 : 'auto',
      right: side === 'out' ? -8 : 'auto',
      display: 'flex', alignItems: 'center', gap: 6,
      flexDirection: side === 'in' ? 'row' : 'row-reverse',
      width: 130,
    }}>
      <span
        data-port-side={side}
        data-port-id={port.id}
        onMouseDown={(e) => { e.stopPropagation(); onPress(e); }}
        onMouseUp={(e) => { e.stopPropagation(); onRelease(e); }}
        style={{
          width: 16, height: 16, borderRadius: 999,
          background: c, border: '2px solid var(--bg-panel)',
          boxShadow: `0 0 8px ${c}88`,
          cursor: 'crosshair', flexShrink: 0,
        }}
      />
      <span style={{
        fontSize: 10.5, color: 'var(--ink-soft)',
        textAlign: side === 'in' ? 'left' : 'right',
        padding: side === 'in' ? '0 0 0 4px' : '0 4px 0 0',
      }}>
        {port.id}<span style={{ color: c, opacity: 0.6 }}> · {port.type}</span>
      </span>
    </div>
  );
}

/* Preview content baked into reef-variant nodes (visual flavor). */
function NodePreview({ node, status }) {
  const type = node?.type;
  const p = { ...(NODE_TYPES[type]?.props || {}), ...(node?.props || {}) };
  const spec = NODE_TYPES[type];
  const cat = CAT[spec.cat];
  // Real chosen-asset thumbnails: when an Image node has a filename picked from
  // the Library, populate the node body with the actual image so you can see at
  // a glance what the chain will produce. Same for an ExistingRender (its clip).
  if (type === 'Image' && p.filename)
    return (
      <img src={api.imageUrl(p.filename)} alt={p.filename}
        onError={e => { e.currentTarget.style.display = 'none'; }}
        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', background: '#02060d' }} />
    );
  if ((type === 'ExistingRender' || type === 'Upload') && p.jobId)
    return (
      <video src={api.jobVideoUrl(p.jobId)} muted preload="metadata" playsInline
        onMouseEnter={e => e.currentTarget.play().catch(() => {})}
        onMouseLeave={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
        onError={e => { e.currentTarget.style.display = 'none'; }}
        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', background: '#000' }} />
    );
  if (['Image'].includes(type))
    return <Thumb kind="image" size={1} style={{ width: '100%', height: '100%', borderRadius: 0, border: 0 }} />;
  if (['Seedance','NewsIllustration','Trim','Extend','Speed','TextOverlay','Ticker','SpatialCompose','ExistingRender','Upload'].includes(type))
    return (
      <div style={{ width: '100%', height: '100%', position: 'relative', background: 'linear-gradient(135deg, #053040 0%, #02060d 100%)' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg, transparent 0 6px, #00e5ff10 6px 7px)' }} />
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#00e5ff', opacity: 0.5 }}>
          <Icon name="film" size={28} />
        </div>
        <div style={{ position: 'absolute', bottom: 4, left: 6, fontFamily: 'var(--f-mono)', fontSize: 9, color: 'var(--ink-strong)' }}>
          {status === 'running' ? '00:08 / 00:15' : 'av · 9:16'}
        </div>
      </div>
    );
  if (['HeyGenAvatar'].includes(type))
    return (
      <div style={{ width: '100%', height: '100%', background: 'radial-gradient(circle at 50% 40%, #a855f744 0%, #02060d 70%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(160deg, #a855f7, #5b21b6)', boxShadow: '0 0 24px var(--violet-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 22, fontWeight: 700 }}>A</div>
      </div>
    );
  if (['Voiceover','MusicTrack','AudioMix','Loudness'].includes(type))
    return (
      <svg viewBox="0 0 200 90" style={{ width: '100%', height: '100%', background: 'linear-gradient(135deg, #063020 0%, #02060d 100%)' }}>
        <path stroke="var(--green)" strokeWidth="1.5" fill="none" d={waveformPath()} />
      </svg>
    );
  if (['Concatenate'].includes(type))
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 3, padding: 4, height: '100%' }}>
        {[0,1,2].map(i => (
          <div key={i} style={{ background: 'linear-gradient(135deg, #053040, #02060d)', borderRadius: 4, position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg, transparent 0 4px, #00e5ff12 4px 5px)', borderRadius: 4 }} />
          </div>
        ))}
      </div>
    );
  if (['NewsItem','NewsScript','BrandStrip'].includes(type))
    return (
      <div style={{ width: '100%', height: '100%', padding: 8, background: 'linear-gradient(135deg, #1a0f00 0%, #02060d 100%)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 10, color: 'var(--amber)', fontFamily: 'var(--f-mono)' }}>{type === 'NewsItem' ? 'cryptoslate.com' : 'prophet voice'}</div>
        <div style={{ fontSize: 11, color: 'var(--ink-strong)', lineHeight: 1.25 }}>
          {type === 'NewsItem' ? 'Solana memecoin volume +38% in 24h, retail piles in.' :
           type === 'NewsScript' ? '"Behold the depths. The shoal awakens..."' :
           '🐙 DEEPOTUS · from the deep'}
        </div>
      </div>
    );
  if (['Render'].includes(type))
    return (
      <div style={{ width: '100%', height: '100%', background: '#02060d', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 36, height: 64, border: '2px solid var(--ink)', borderRadius: 4, position: 'relative' }}>
          <Icon name="play" size={18} style={{ position: 'absolute', top: 22, left: 9, color: 'var(--ink-strong)' }} />
        </div>
      </div>
    );
  return (
    <div style={{ width: '100%', height: '100%', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: cat.color, opacity: 0.5 }}>
      <Icon name={cat.icon} size={28} />
    </div>
  );
}

function waveformPath() {
  const pts = [];
  for (let x = 0; x <= 200; x += 4) {
    const a = (Math.sin(x * 0.15) + Math.sin(x * 0.07 + 1.2) * 0.6 + (Math.random() - 0.5) * 0.4) * 22 + 45;
    pts.push(`${x === 0 ? 'M' : 'L'}${x} ${a.toFixed(1)}`);
  }
  return pts.join(' ');
}

function nodeMetaLeft(node) {
  const p = { ...(NODE_TYPES[node.type]?.props || {}), ...(node.props || {}) };
  if (node.type === 'Image' || node.type === 'BrandStrip') return p.filename || p.mark;
  if (node.type === 'Seedance') return `${p.style} · ${p.durationS}s`;
  if (node.type === 'HeyGenAvatar') return p.avatar?.split('·')[0]?.trim();
  if (node.type === 'NewsScript') return `${p.words}w`;
  if (node.type === 'Voiceover') return p.voice?.split('·')[0]?.trim();
  if (node.type === 'Trim') return `${p.startS}s → ${p.endS}s`;
  if (node.type === 'Extend') return `→ ${p.targetS}s · ${p.mode}`;
  if (node.type === 'Concatenate') return `xfade ${p.durationS}s`;
  if (node.type === 'Render') return p.format;
  if (node.type === 'SpatialCompose') return p.templateId;
  if (node.type === 'AvatarMaster') return `tail ${p.tailPadS}s`;
  if (node.type === 'ExistingRender') return p.jobId;
  if (node.type === 'Upload') return p.filename || 'upload a clip';
  if (node.type === 'NewsItem') return p.source;
  if (node.type === 'Text') return `${(p.value||'').length} ch`;
  return '';
}
function nodeMetaRight(node) {
  const p = { ...(NODE_TYPES[node.type]?.props || {}), ...(node.props || {}) };
  if (node.type === 'Seedance') return `seed:${p.seed}`;
  if (node.type === 'Upload') return p.durationS ? `${p.durationS}s${p.master ? ' ⏱master' : ''}` : '';
  if (node.type === 'Render') return `${p.fps}fps`;
  if (node.type === 'AudioMix') return `${p.duckDb}dB`;
  return '';
}

export { NODE_TYPES, PALETTE_GROUPS, CAT, PORT, NODE_W, nodeHeight, portAnchor, NodeCard };
