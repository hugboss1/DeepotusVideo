// persona.jsx — Persona creator wizard + selector + library (ESM port)
import React, { useState as useStatePer, useEffect as useEffectPer, useMemo as useMemoPer } from 'react';
import { Icon, Button, IconButton, Input, Badge, Field, Select, Slider, Panel } from './atoms.jsx';

/* ────────────────────── Built-in personas ────────────────────── */
const PERSONA_PRESETS = [
  {
    id: 'deepotus',
    name: 'Deepotus',
    handle: '@deepotus_official',
    avatar: 'octopus',
    role: 'The brand voice of $DEEPOTUS — half oracle, half community shitposter.',
    voiceMode: 'prophet',
    tone: ['slow','prophetic','wry','low-volume','confident'],
    formality: 35, // 0 = shitposter, 100 = formal
    emojiPolicy: 'sparse',  // never | sparse | liberal
    catchphrase: 'From the deep, for the deep.',
    preferred: ['shoal','tentacle','descent','ink','depths','current'],
    banned:    ['gm','to the moon','wagmi','degen','financial advice'],
    languages: ['EN'],
    builtIn: true,
    active: true,
  },
  {
    id: 'oracle',
    name: 'The Oracle',
    handle: '@deepotus_oracle',
    avatar: 'sparkle',
    role: 'High-prophet voice for News reels — slow, dramatic, restrained.',
    voiceMode: 'oracle',
    tone: ['oracular','slow','restrained','dramatic'],
    formality: 70, emojiPolicy: 'never',
    catchphrase: 'The current will tell.',
    preferred: ['behold','depths','tide','prophecy','sign'],
    banned:    ['gm','wagmi','lol','fr fr','no cap'],
    languages: ['EN'],
    builtIn: true,
    active: false,
  },
  {
    id: 'seer',
    name: 'The Seer',
    handle: '@deepotus_seer',
    avatar: 'zap',
    role: 'Intense, urgent — for charts and breaking news.',
    voiceMode: 'seer',
    tone: ['urgent','terse','clipped','intense'],
    formality: 50, emojiPolicy: 'never',
    catchphrase: 'Watch the depths.',
    preferred: ['signal','flicker','spike','listen','now'],
    banned:    ['lol','soon™','probably nothing'],
    languages: ['EN'],
    builtIn: true,
    active: false,
  },
];

const VOICE_MODES = [
  { id: 'prophet', label: 'Prophet',  desc: 'Deep · slow · solemn' },
  { id: 'oracle',  label: 'Oracle',   desc: 'Smooth · steady · poetic' },
  { id: 'seer',    label: 'Seer',     desc: 'Urgent · terse · intense' },
  { id: 'custom',  label: 'Custom',   desc: 'Define a new voice' },
];

/* Persona → JSON shape matching backend/persona/deepotus.json. */
function personaToJson(p) {
  return {
    id: p.id, name: p.name, handle: p.handle, role: p.role,
    voice: {
      mode: p.voiceMode,
      tone: p.tone,
      formality: p.formality,
      emoji_policy: p.emojiPolicy,
      catchphrase: p.catchphrase,
    },
    vocabulary: {
      preferred: p.preferred,
      banned: p.banned,
    },
    languages: p.languages,
    created_at: p.createdAt || new Date().toISOString(),
    schema_version: 1,
  };
}

/* ────────────────────── PersonaCreatorModal ────────────────────── */
function PersonaCreatorModal({ open, onClose, onSave, initial }) {
  const [step, setStep] = useStatePer(0);
  const [p, setP] = useStatePer(emptyPersona());

  useEffectPer(() => {
    if (open) {
      setStep(0);
      setP(initial ? { ...emptyPersona(), ...initial } : emptyPersona());
    }
  }, [open]);

  function setField(k, v) { setP(prev => ({ ...prev, [k]: v })); }
  function toggleList(k, val) {
    setP(prev => {
      const list = prev[k] || [];
      return { ...prev, [k]: list.includes(val) ? list.filter(x => x !== val) : [...list, val] };
    });
  }

  if (!open) return null;
  const STEPS = ['Identity','Voice','Vocabulary','Preview'];

  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, zIndex: 80,
      background: 'var(--bg-overlay)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 760, maxWidth: '100%', maxHeight: '94%',
        background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
        borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 80px var(--brand-soft)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ width: 32, height: 32, borderRadius: '50%', overflow: 'hidden', flexShrink: 0, boxShadow: '0 0 12px var(--brand-soft)' }}>
            <img src="/api/branding/logo" width="32" height="32" alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </span>
          <div style={{ flex: 1 }}>
            <div className="upper" style={{ color: 'var(--brand)' }}>Persona · {step + 1} / {STEPS.length}</div>
            <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>{STEPS[step]}</div>
          </div>
          <Badge tone="violet">{p.voiceMode}</Badge>
          <IconButton name="close" onClick={onClose} />
        </div>

        <div style={{ display: 'flex', gap: 3, padding: '0 18px 14px', borderBottom: '1px solid var(--stroke)' }}>
          {STEPS.map((s, i) => (
            <div key={s} style={{ flex: 1, height: 3, borderRadius: 999, background: i <= step ? 'linear-gradient(90deg, var(--brand), var(--violet))' : 'var(--stroke)' }} />
          ))}
        </div>

        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '18px 22px' }}>
          {step === 0 && <IdentityStep p={p} setField={setField} />}
          {step === 1 && <VoiceStep    p={p} setField={setField} />}
          {step === 2 && <VocabStep    p={p} setField={setField} toggleList={toggleList} />}
          {step === 3 && <PreviewStep  p={p} />}
        </div>

        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <button disabled={step === 0} onClick={() => setStep(step - 1)} style={{
            background: 'transparent', border: 0, color: step === 0 ? 'var(--ink-muted)' : 'var(--ink)',
            fontSize: 12, cursor: step === 0 ? 'default' : 'pointer', padding: '6px 10px',
          }}>← Back</button>
          <div style={{ fontSize: 11, color: 'var(--ink-muted)' }}>
            Will save to <span className="mono strong">backend/persona/{(p.id || 'new').replace(/[^a-z0-9_-]/gi,'')}.json</span>
          </div>
          {step < STEPS.length - 1
            ? <Button variant="primary" size="md" iconRight="caretR" glow onClick={() => setStep(step + 1)}>Continue</Button>
            : <Button variant="primary" size="md" icon="check" glow onClick={() => { onSave?.({ ...p, id: p.id || slugify(p.name), createdAt: new Date().toISOString() }); onClose(); }}>Save persona</Button>
          }
        </div>
      </div>
    </div>
  );
}

function emptyPersona() {
  return {
    id: '', name: '', handle: '@', role: '', voiceMode: 'prophet',
    tone: ['slow','prophetic'], formality: 50, emojiPolicy: 'sparse',
    catchphrase: '', preferred: [], banned: [], languages: ['EN'],
  };
}
function slugify(s) { return (s || 'persona').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'persona'; }

function IdentityStep({ p, setField }) {
  return (
    <>
      <div className="display" style={{ fontSize: 20, color: 'var(--ink-strong)', marginBottom: 6 }}>Who is this persona?</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 18 }}>The Scheduler signs posts with this identity; the News scripter borrows its voice.</div>
      <div style={{ display: 'grid', gap: 12 }}>
        <Field label="Display name (e.g. Deepotus · Oracle · The Seer)">
          <Input value={p.name} onChange={v => setField('name', v)} placeholder="The Oracle" />
        </Field>
        <Field label="Handle on X">
          <Input mono value={p.handle} onChange={v => setField('handle', v)} placeholder="@deepotus_oracle" />
        </Field>
        <Field label="What does this persona do?" hint="One sentence. Used as a system-prompt seed for the script generator.">
          <textarea value={p.role} onChange={e => setField('role', e.target.value)} rows={3} placeholder="High-prophet voice for News reels — slow, dramatic, restrained."
            style={{ width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical' }} />
        </Field>
      </div>
    </>
  );
}

function VoiceStep({ p, setField }) {
  const allTones = ['slow','prophetic','wry','solemn','urgent','clipped','intense','playful','poetic','low-volume','restrained','dramatic','warm','cold'];
  return (
    <>
      <div className="display" style={{ fontSize: 20, color: 'var(--ink-strong)', marginBottom: 6 }}>How does it sound?</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 18 }}>Voice mode picks the spoken-voice default; tones, formality and emoji policy steer the written one.</div>

      <div className="upper" style={{ marginBottom: 6 }}>Voice mode</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 18 }}>
        {VOICE_MODES.map(v => {
          const on = p.voiceMode === v.id;
          return (
            <button key={v.id} onClick={() => setField('voiceMode', v.id)} style={{
              padding: 10, textAlign: 'left',
              background: on ? 'var(--brand-soft)' : 'var(--bg-base)',
              color: on ? 'var(--brand)' : 'var(--ink)',
              border: `1px solid ${on ? 'var(--brand)' : 'var(--stroke)'}`,
              borderRadius: 'var(--r-sm)', cursor: 'pointer',
              boxShadow: on ? '0 0 14px var(--brand-soft)' : 'none',
            }}>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>{v.label}</div>
              <div style={{ fontSize: 10.5, color: on ? 'var(--brand)' : 'var(--ink-soft)' }}>{v.desc}</div>
            </button>
          );
        })}
      </div>

      <div className="upper" style={{ marginBottom: 6 }}>Tone keywords</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 16 }}>
        {allTones.map(t => {
          const on = (p.tone || []).includes(t);
          return (
            <button key={t} onClick={() => {
              const list = p.tone || [];
              setField('tone', list.includes(t) ? list.filter(x => x !== t) : [...list, t]);
            }} style={{
              padding: '4px 9px', fontSize: 11, borderRadius: 999,
              background: on ? 'var(--cyan-soft)' : 'var(--bg-base)',
              color: on ? 'var(--cyan)' : 'var(--ink)',
              border: `1px solid ${on ? 'var(--cyan)' : 'var(--stroke)'}`,
              cursor: 'pointer',
            }}>{t}</button>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Field>
          <Slider label="Formality (shitpost ⇆ liturgy)" value={p.formality} min={0} max={100} step={5} onChange={v => setField('formality', v)} unit="%" />
        </Field>
        <Field label="Emoji policy">
          <Select value={p.emojiPolicy} onChange={v => setField('emojiPolicy', v)} options={[
            { value: 'never',   label: 'Never' },
            { value: 'sparse',  label: 'Sparse · 1 max' },
            { value: 'liberal', label: 'Liberal' },
          ]} />
        </Field>
      </div>
      <Field label="Catchphrase (optional)" hint="Appears as a signature line in long-form posts.">
        <Input value={p.catchphrase} onChange={v => setField('catchphrase', v)} placeholder="From the deep, for the deep." />
      </Field>
    </>
  );
}

function VocabStep({ p, setField, toggleList }) {
  return (
    <>
      <div className="display" style={{ fontSize: 20, color: 'var(--ink-strong)', marginBottom: 6 }}>Vocabulary</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 18 }}>Preferred phrases are weighted upward by the script model; banned phrases are filtered post-generation. Comma-separated.</div>
      <Field label="Preferred phrases" hint="e.g. shoal, tentacle, descent, ink, depths, current">
        <Input value={(p.preferred || []).join(', ')} onChange={v => setField('preferred', v.split(',').map(s => s.trim()).filter(Boolean))} placeholder="shoal, tentacle, descent" />
      </Field>
      <Field label="Banned phrases" hint="e.g. gm, wagmi, to the moon, financial advice">
        <Input value={(p.banned || []).join(', ')} onChange={v => setField('banned', v.split(',').map(s => s.trim()).filter(Boolean))} placeholder="gm, wagmi" />
      </Field>
      <Field label="Languages">
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {['EN','FR','DE','ES','PT','IT','JA'].map(l => {
            const on = (p.languages || []).includes(l);
            return (
              <button key={l} onClick={() => toggleList('languages', l)} style={{
                padding: '4px 10px', fontSize: 11, borderRadius: 999,
                background: on ? 'var(--violet-soft)' : 'var(--bg-base)',
                color: on ? 'var(--violet)' : 'var(--ink)',
                border: `1px solid ${on ? 'var(--violet)' : 'var(--stroke)'}`,
                cursor: 'pointer', fontFamily: 'var(--f-mono)',
              }}>{l}</button>
            );
          })}
        </div>
      </Field>
    </>
  );
}

function PreviewStep({ p }) {
  const json = personaToJson({ ...p, id: p.id || slugify(p.name) });
  const text = JSON.stringify(json, null, 2);
  function download() {
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${json.id || 'persona'}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <div className="display" style={{ fontSize: 20, color: 'var(--ink-strong)', marginBottom: 6 }}>Preview & save</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 18 }}>
        This JSON gets written to <span className="mono">backend/persona/{json.id}.json</span> and added to your persona library. You can pick it as the active persona anywhere a script is generated.
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <Panel style={{ padding: 14 }}>
          <div className="upper" style={{ marginBottom: 8 }}>Identity</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 10px', fontSize: 12 }}>
            <span className="soft">Name</span><span className="strong">{p.name || '—'}</span>
            <span className="soft">Handle</span><span className="mono strong">{p.handle || '—'}</span>
            <span className="soft">Voice</span><span className="strong">{p.voiceMode}</span>
            <span className="soft">Tones</span><span className="strong">{(p.tone||[]).join(', ') || '—'}</span>
            <span className="soft">Formality</span><span className="mono strong">{p.formality}%</span>
            <span className="soft">Emoji</span><span className="strong">{p.emojiPolicy}</span>
            <span className="soft">Langs</span><span className="mono strong">{(p.languages||[]).join(' · ')}</span>
          </div>
          <div className="upper" style={{ marginTop: 12, marginBottom: 6 }}>Sample post</div>
          <div style={{ fontSize: 12, color: 'var(--ink-strong)', fontStyle: 'italic', lineHeight: 1.5, padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)' }}>
            {samplePostFor(p)}
          </div>
        </Panel>
        <div style={{ position: 'relative' }}>
          <pre className="scroll mono" style={{
            margin: 0, padding: 14, fontSize: 10.5, lineHeight: 1.5,
            background: '#02060d', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)',
            color: 'var(--ink)', maxHeight: 320, overflow: 'auto',
          }}>{text}</pre>
          <div style={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 6 }}>
            <IconButton name="copy" onClick={() => navigator.clipboard?.writeText(text)} title="Copy JSON" />
            <IconButton name="download" onClick={download} title="Download .json" />
          </div>
        </div>
      </div>
    </>
  );
}

function samplePostFor(p) {
  const mode = p.voiceMode;
  const cp = p.catchphrase ? `\n\n${p.catchphrase}` : '';
  if (mode === 'prophet') return `The shoal turns. ${(p.preferred?.[0]||'depths')} ripple — a sign for those who listen.${cp}`;
  if (mode === 'oracle')  return `Behold the chart. The ${(p.preferred?.[0]||'tide')} returns to its bed, slowly.${cp}`;
  if (mode === 'seer')    return `Signal · ${(p.preferred?.[0]||'spike')}. Watch the depths. Now.${cp}`;
  return `${p.name || 'New persona'} speaks: ${(p.preferred?.[0]||'something')} stirs.${cp}`;
}

/* ────────────────────── PersonaSelector ────────────────────── */
function PersonaSelector({ personas, activeId, onSelect, onNew, onEdit, compact }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {personas.map(p => {
        const active = p.id === activeId;
        return (
          <div key={p.id} onClick={() => onSelect?.(p.id)} style={{
            display: 'grid', gridTemplateColumns: '32px 1fr auto auto', gap: 12, alignItems: 'center',
            padding: '10px 12px',
            background: active ? 'var(--brand-soft)' : 'var(--bg-panel)',
            border: `1px solid ${active ? 'var(--brand)' : 'var(--stroke)'}`,
            borderRadius: 'var(--r)', cursor: 'pointer',
            transition: 'all var(--dur-1) var(--ease)',
            boxShadow: active ? '0 0 18px var(--brand-soft)' : 'none',
          }}>
            <span style={{
              width: 30, height: 30, borderRadius: '50%', overflow: 'hidden',
              background: active ? 'radial-gradient(circle at 35% 30%, #ef444466, #02060d)' : 'var(--bg-panel-2)',
              border: `1px solid ${active ? 'var(--brand)' : 'var(--stroke)'}`,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              color: active ? 'var(--brand)' : 'var(--ink-soft)',
            }}>
              <Icon name={p.avatar || 'octopus'} size={14} />
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, color: 'var(--ink-strong)', fontWeight: 600 }}>{p.name}</span>
                {p.builtIn && <Badge tone="neutral">built-in</Badge>}
              </div>
              {!compact && <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{p.role}</div>}
              <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center', fontSize: 10, color: 'var(--ink-muted)', fontFamily: 'var(--f-mono)' }}>
                <span>{p.handle}</span><span>·</span>
                <span>{p.voiceMode}</span><span>·</span>
                <span>{p.formality}% formal</span>
              </div>
            </div>
            <Badge tone={active ? 'green' : 'neutral'} dot={active}>{active ? 'active' : 'idle'}</Badge>
            <div style={{ display: 'flex', gap: 4 }}>
              {!p.builtIn && onEdit && <IconButton name="edit" size={26} iconSize={12} onClick={(e) => { e.stopPropagation(); onEdit(p); }} />}
              <IconButton name="download" size={26} iconSize={12} title="Export JSON" onClick={(e) => {
                e.stopPropagation();
                const blob = new Blob([JSON.stringify(personaToJson(p), null, 2)], { type: 'application/json' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob); a.download = (p.id || 'persona') + '.json';
                document.body.appendChild(a); a.click(); a.remove();
              }} />
            </div>
          </div>
        );
      })}
      {onNew && (
        <button onClick={onNew} style={{
          padding: '12px', background: 'transparent', border: '1px dashed var(--stroke-strong)',
          borderRadius: 'var(--r)', cursor: 'pointer', color: 'var(--ink-soft)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          fontSize: 12.5,
          transition: 'all var(--dur-1) var(--ease)',
        }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.color = 'var(--brand)'; e.currentTarget.style.background = 'var(--brand-soft)'; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--stroke-strong)'; e.currentTarget.style.color = 'var(--ink-soft)'; e.currentTarget.style.background = 'transparent'; }}
        >
          <Icon name="plus" size={14} /> Create new persona
        </button>
      )}
    </div>
  );
}

export { PERSONA_PRESETS, PersonaCreatorModal, PersonaSelector, personaToJson };
