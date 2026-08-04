// prompts.jsx — Prompt templates + Prompt Generator modal (ESM port)
import React, { useState as useStatePr, useEffect as useEffectPr, useMemo as useMemoPr } from 'react';
import { Icon, Button, IconButton, Badge } from './atoms.jsx';

/* ────────────────────── Templates ────────────────────── */
const PROMPT_TEMPLATES = [
  // Cinematic
  { id: 'deep-throne',   cat: 'cinematic', title: 'Deep throne',           emoji: '🐙', short: 'Slow push toward a luminous throne',
    body: 'A deep-sea throne lit by bioluminescent currents, slow cinematic push-in, indigo and cyan, particles drifting, anamorphic lens flares, 35mm grain, atmospheric haze.' },
  { id: 'oracle-eye',    cat: 'cinematic', title: 'Oracle eye',            emoji: '👁', short: 'Macro of a glowing oracle eye',
    body: 'Extreme macro of an oracle eye, iris like a galaxy, reflections of red neon glyphs, slow zoom-out revealing tentacles, anamorphic, shallow depth of field, soft underwater volumetrics.' },
  { id: 'abyss-descent', cat: 'cinematic', title: 'Abyss descent',         emoji: '🌊', short: 'Vertical fall into deep blue',
    body: 'Vertical descent into a midnight-blue abyss, godrays piercing from above, scale plankton drifting, slow handheld with subtle camera shake, mood: solemn, prophetic.' },

  // Deep-sea / brand
  { id: 'shoal-ascend',  cat: 'deep-sea',  title: 'Shoal ascends',         emoji: '🐟', short: 'Hundreds of tentacles swirling up',
    body: 'A shoal of tiny red-glow octopi spiraling upward through dark water, like sparks rising, lo-fi cinematic, crimson highlights against deep teal, slow-motion.' },
  { id: 'tentacle-coin', cat: 'deep-sea',  title: 'Tentacle coin',         emoji: '🪙', short: 'Tentacle wraps a glowing coin',
    body: 'A bioluminescent red tentacle slowly wraps around a glowing Solana-style coin, droplets of light, dark watery background, hyper-detailed, macro lens, cinematic.' },
  { id: 'submarine-port',cat: 'deep-sea',  title: 'Porthole watch',        emoji: '🛸', short: 'Looking out a submarine porthole',
    body: 'POV through a brass submarine porthole into deep cyan water, a single red octopus eye drifting closer, slow push-in, condensation on the glass, dramatic, lonely.' },

  // Noir / glitch
  { id: 'red-noir',      cat: 'noir',      title: 'Red noir prophecy',     emoji: '🔴', short: 'Hard red shadows, smoke',
    body: 'Noir-lit scene of an oracle silhouette in a smoky room, single hard red light source, deep shadows, rain on windows, slow dolly, 35mm, high contrast monochrome with red accent.' },
  { id: 'glitch-throne', cat: 'glitch',    title: 'Glitch throne',         emoji: '⚡', short: 'Datamoshed bioluminescent throne',
    body: 'Datamoshed bioluminescent throne, red and cyan chromatic aberration, scan-lines, brief frame stutters, glitch art aesthetic, otherworldly, 12fps stutter inside 24fps footage.' },
  { id: 'flicker-eye',   cat: 'glitch',    title: 'Flicker eye',           emoji: '👁', short: 'Eye flickers between worlds',
    body: 'A close-up eye flickering between two realities — abyss and city — with VHS noise, CRT scanlines, color bleed between red and cyan, slow blink at midpoint.' },

  // Dream / abstract
  { id: 'liquid-time',   cat: 'dream',     title: 'Liquid time',           emoji: '⏳', short: 'Hourglass under water',
    body: 'Slow-motion hourglass underwater, the sand replaced by tiny glowing octopi, suspended in indigo, cathedral light, dreamlike, surrealist composition, painterly.' },
  { id: 'echo-shoal',    cat: 'dream',     title: 'Echo shoal',            emoji: '🪞', short: 'Mirror corridor of shoals',
    body: 'A corridor of mirrors reflecting an infinite shoal of red octopi, refracted light, dreamlike, infinite recursion, soft focus edges, ambient mist.' },

  // Documentary
  { id: 'chart-deep',    cat: 'documentary', title: 'Chart of the deep',   emoji: '📈', short: 'Holographic candle chart',
    body: 'Holographic candle chart floating in dark water, candles cast in red and green light, slow camera orbit, particles drifting through the chart, documentary tone.' },
  { id: 'oracle-desk',   cat: 'documentary', title: 'Oracle\u2019s desk',  emoji: '📜', short: 'Lit desk with scrolls and a tentacle',
    body: 'Top-down view of a wooden desk in candlelight, parchment with red glyphs, a tentacle reaching from off-frame to a coin, slow dolly-in, intimate, documentary feel.' },

  // Punchy / social
  { id: 'red-flash',     cat: 'social',    title: 'Red flash drop',        emoji: '⚡', short: '1s flash → logo lock-up',
    body: 'Hard red flash to black, then the Deepotus mark fades in at center, single sonar ping, sub-second, punchy social opener.' },
  { id: 'tickerwall',    cat: 'social',    title: 'Tickerwall',            emoji: '📰', short: 'Stack of scrolling red headlines',
    body: 'Stack of red horizontal news ticker lines scrolling at different speeds, dark navy background, brand mark floats top-right, 30fps, ultra-readable.' },
];

const PROMPT_CATS = [
  { id: 'cinematic',   label: 'Cinematic' },
  { id: 'deep-sea',    label: 'Deep-sea' },
  { id: 'noir',        label: 'Noir' },
  { id: 'glitch',      label: 'Glitch' },
  { id: 'dream',       label: 'Dream' },
  { id: 'documentary', label: 'Documentary' },
  { id: 'social',      label: 'Social' },
];

// (PROMPT_TEMPLATES / PROMPT_CATS are exported below)

/* ────────────────────── Generator ingredients ────────────────────── */
const ING = {
  subject:  ['throne','oracle eye','tentacle','submarine','abyss','shoal','glowing coin','candle chart','ink cloud'],
  mood:     ['prophetic','glitchy','dreamy','tense','triumphant','meditative','noir','playful'],
  light:    ['bioluminescent','neon red','godrays','sodium-yellow','single hard light','soft volumetric','candlelight'],
  motion:   ['slow push-in','slow orbit','locked-off','handheld micro-shake','vertical descent','vertical rise','dolly-out'],
  palette:  ['indigo+cyan','red+black','amber+navy','monochrome+red accent','muted teal','lo-fi VHS'],
  lens:     ['anamorphic','35mm','50mm','wide 24mm','macro','fisheye'],
  fx:       ['particles drifting','volumetric haze','rain on glass','chromatic aberration','grain','lens flares','scanlines','condensation'],
};

const ING_LABEL = {
  subject: 'Subject', mood: 'Mood', light: 'Lighting',
  motion: 'Motion', palette: 'Palette', lens: 'Lens', fx: 'Effects',
};

function composePrompt(picks, freeNotes) {
  const parts = [];
  if (picks.subject?.length)  parts.push(picks.subject.join(' and a '));
  if (picks.motion?.length)   parts.push(picks.motion[0]);
  if (picks.light?.length)    parts.push(picks.light.join(' + ') + ' lighting');
  if (picks.palette?.length)  parts.push('palette: ' + picks.palette.join(' / '));
  if (picks.lens?.length)     parts.push(picks.lens[0] + ' lens');
  if (picks.fx?.length)       parts.push(picks.fx.join(', '));
  if (picks.mood?.length)     parts.push('mood: ' + picks.mood.join(', '));
  if (freeNotes && freeNotes.trim()) parts.push(freeNotes.trim());
  return parts
    .filter(Boolean)
    .map((p, i) => (i === 0 ? cap(p) : p))
    .join(', ') + '.';
}
function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

/* ────────────────────── PromptGeneratorModal ────────────────────── */
function PromptGeneratorModal({ open, onClose, onUse, initial }) {
  const [picks, setPicks] = useStatePr({});
  const [notes, setNotes] = useStatePr('');
  const [refined, setRefined] = useStatePr('');
  const [refining, setRefining] = useStatePr(false);
  const [refineErr, setRefineErr] = useStatePr(null);
  const composed = useMemoPr(() => composePrompt(picks, notes), [picks, notes]);
  const final = refined || composed;

  useEffectPr(() => {
    if (open) {
      setPicks({});
      // Start with a CLEAN slate — never seed the notes with the current /
      // default prompt. The generator's output must OVERWRITE the default,
      // not append to it, so the result reflects only the user's own choices.
      setNotes('');
      setRefined(''); setRefineErr(null);
    }
  }, [open]);

  function toggle(group, value) {
    setRefined('');
    setPicks(p => {
      const cur = p[group] || [];
      const next = cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value];
      return { ...p, [group]: next };
    });
  }
  function rollDice() {
    setRefined('');
    const next = {};
    Object.entries(ING).forEach(([k, opts]) => {
      const n = (k === 'subject' || k === 'mood' || k === 'motion' || k === 'lens' || k === 'palette') ? 1 : 1 + Math.floor(Math.random() * 2);
      const picked = [];
      const pool = [...opts];
      for (let i = 0; i < n && pool.length; i++) {
        picked.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
      }
      next[k] = picked;
    });
    setPicks(next);
  }
  async function refineWithAI() {
    setRefining(true); setRefineErr(null);
    try {
      // Local refinement: hit the backend's prompt builder if available;
      // otherwise apply a small deterministic polish so the UI still works.
      let txt = final;
      try {
        const r = await fetch('/api/prompt/build', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intent: final, style: 'cinematic' }),
        });
        if (r.ok) {
          const j = await r.json();
          txt = j.final_prompt || j.prompt || final;
        }
      } catch { /* fall through to deterministic polish */ }
      if (txt === final) {
        txt = final.replace(/\s+/g, ' ').trim();
        if (!/\.$/.test(txt)) txt += '.';
      }
      setRefined((txt || '').trim().replace(/^["']|["']$/g, ''));
    } catch (e) {
      setRefineErr(String(e?.message || e));
    } finally {
      setRefining(false);
    }
  }

  if (!open) return null;
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, zIndex: 80,
      background: 'var(--bg-overlay)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 800, maxWidth: '100%', maxHeight: '94%',
        background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
        borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 80px var(--cyan-soft)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--brand-soft)', color: 'var(--brand)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="sparkle" size={16} />
          </span>
          <div style={{ flex: 1 }}>
            <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Prompt generator</div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>Pick ingredients · roll the dice · refine with AI</div>
          </div>
          <Button variant="ghost" size="sm" icon="zap" onClick={rollDice}>Random</Button>
          <IconButton name="close" onClick={onClose} />
        </div>

        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
          {Object.entries(ING).map(([k, opts]) => (
            <div key={k} style={{ marginBottom: 12 }}>
              <div className="upper" style={{ marginBottom: 6 }}>{ING_LABEL[k]}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {opts.map(o => {
                  const on = (picks[k] || []).includes(o);
                  return (
                    <button key={o} onClick={() => toggle(k, o)} style={{
                      padding: '5px 10px', fontSize: 11.5, borderRadius: 999,
                      background: on ? 'var(--brand-soft)' : 'var(--bg-base)',
                      color: on ? 'var(--brand)' : 'var(--ink)',
                      border: `1px solid ${on ? 'var(--brand)' : 'var(--stroke)'}`,
                      cursor: 'pointer',
                      transition: 'all var(--dur-1) var(--ease)',
                      boxShadow: on ? '0 0 12px var(--brand-soft)' : 'none',
                    }}>{o}</button>
                  );
                })}
              </div>
            </div>
          ))}

          <div style={{ marginTop: 14 }}>
            <div className="upper" style={{ marginBottom: 6 }}>Extra notes (optional)</div>
            <textarea value={notes} onChange={e => { setNotes(e.target.value); setRefined(''); }} rows={2} placeholder="e.g. fits the $DEEPOTUS Pyth-feed announcement"
              style={{ width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical' }} />
          </div>

          <div style={{
            marginTop: 14, padding: 14,
            background: 'var(--bg-base)', border: '1px solid var(--stroke)',
            borderRadius: 'var(--r)', position: 'relative',
          }}>
            <div className="upper" style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>Composed prompt</span>
              {refined && <Badge tone="violet" dot>AI-refined</Badge>}
              <span style={{ flex: 1 }} />
              <span className="mono" style={{ fontSize: 10, color: 'var(--ink-muted)' }}>{final.length} ch · ~{Math.round(final.split(' ').length)} words</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-strong)', lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
              {final || <span style={{ color: 'var(--ink-muted)' }}>Pick a few ingredients above, or hit Random.</span>}
            </div>
            {refineErr && <div style={{ marginTop: 8, color: 'var(--red)', fontSize: 11 }}>Refine failed: {refineErr}</div>}
          </div>
        </div>

        <div style={{ padding: 14, borderTop: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Button variant="outline" size="sm" icon="copy" onClick={() => navigator.clipboard?.writeText(final)}>Copy</Button>
          <Button variant="ghost" size="sm" icon="sparkle" onClick={refineWithAI} disabled={refining || !final}>
            {refining ? 'Refining…' : 'Refine with AI'}
          </Button>
          <span style={{ flex: 1 }} />
          <Button variant="primary" size="md" icon="zap" glow onClick={() => { onUse?.(final); onClose(); }} disabled={!final || final.trim() === '.'}>Use this prompt</Button>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── PromptTemplateGallery (used in Quick) ────────────────────── */
function PromptTemplateGallery({ onPick }) {
  const [cat, setCat] = useStatePr('all');
  const list = useMemoPr(() =>
    cat === 'all' ? PROMPT_TEMPLATES : PROMPT_TEMPLATES.filter(t => t.cat === cat),
  [cat]);

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
        <CatChip on={cat==='all'} onClick={() => setCat('all')}>All</CatChip>
        {PROMPT_CATS.map(c => (
          <CatChip key={c.id} on={cat===c.id} onClick={() => setCat(c.id)}>{c.label}</CatChip>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, maxHeight: 240, overflowY: 'auto' }} className="scroll">
        {list.map(t => (
          <button key={t.id} onClick={() => onPick(t)} style={{
            display: 'flex', gap: 8, padding: '8px 9px', textAlign: 'left',
            background: 'var(--bg-base)', border: '1px solid var(--stroke)',
            borderRadius: 'var(--r-sm)', cursor: 'pointer',
            color: 'var(--ink)', transition: 'all var(--dur-1) var(--ease)',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.background = 'var(--brand-soft)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--stroke)'; e.currentTarget.style.background = 'var(--bg-base)'; }}
          >
            <span style={{ fontSize: 16 }}>{t.emoji}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, color: 'var(--ink-strong)', fontWeight: 500 }}>{t.title}</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-soft)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.short}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function CatChip({ on, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '3px 9px', fontSize: 10.5, borderRadius: 999,
      background: on ? 'var(--brand-soft)' : 'transparent',
      color: on ? 'var(--brand)' : 'var(--ink-soft)',
      border: `1px solid ${on ? 'var(--brand)' : 'var(--stroke)'}`,
      cursor: 'pointer', fontWeight: 500,
      transition: 'all var(--dur-1) var(--ease)',
    }}>{children}</button>
  );
}

export { PromptGeneratorModal, PromptTemplateGallery, PROMPT_TEMPLATES, composePrompt };
