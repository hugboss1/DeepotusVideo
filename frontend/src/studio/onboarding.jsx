// onboarding.jsx — Splash (rotating red logo) + Onboarding flow (ESM port)
import React, { useState as useStateOb, useEffect as useEffectOb, useRef as useRefOb } from 'react';
import { Icon, Button, Input, Badge, Logo, Panel } from './atoms.jsx';
import { PersonaCreatorModal, PersonaSelector } from './persona.jsx';
import { useHealth, useBranding, api as _bapi } from './api.js';

/* ────────────────────── Splash ──────────────────────
 * 4 phases sur ~8s :
 *  0  mount instantané (logo zoom 0.4)
 *  1  apparition wordmark + caustiques en mouvement (≈800ms)
 *  2  immersion : zoom-in continu (1.0 → 1.32), caustiques actives, load bar
 *  3  fade-out
 */
function Splash({ onDone }) {
  const b = useBranding();
  const [phase, setPhase] = useStateOb(0);
  useEffectOb(() => {
    const t1 = setTimeout(() => setPhase(1),   30);
    const t2 = setTimeout(() => setPhase(2),   800);
    const t3 = setTimeout(() => setPhase(3),  7400);
    const t4 = setTimeout(() => onDone?.(),   7950);
    return () => [t1,t2,t3,t4].forEach(clearTimeout);
  }, []);

  // Logo scale: phase0 = 0.4 (small, fade in), phase1 = 0.95 (drop),
  // phase2 = 1.32 (continuous immersive zoom-in held until fade).
  const scale = phase === 0 ? 0.4 : phase === 1 ? 0.95 : 1.32;

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 24,
      background: 'radial-gradient(circle at 50% 40%, #1a0606 0%, #02060d 70%)',
      opacity: phase >= 3 ? 0 : 1,
      transition: 'opacity 520ms var(--ease)',
      pointerEvents: phase >= 3 ? 'none' : 'auto',
      overflow: 'hidden',
    }}>
      {/* Underwater caustics — animated SVG filter (light diffraction through water) */}
      <Caustics />
      {/* Drifting plankton particles */}
      <SplashParticles />
      {/* Vignette + sunbeams from above */}
      <Sunbeams />

      {/* Logo — continuous immersive zoom on phase 2 */}
      <div style={{
        width: 168, height: 168, position: 'relative',
        transform: `scale(${scale})`,
        opacity: phase === 0 ? 0 : 1,
        transition: phase === 2
          ? 'transform 6600ms cubic-bezier(.32,.0,.28,1), opacity 500ms var(--ease)'
          : 'transform 800ms cubic-bezier(.22,1,.36,1), opacity 500ms var(--ease)',
        filter: 'drop-shadow(0 12px 32px #ef444466)',
      }}>
        {/* Rotating outer rings */}
        <svg width="168" height="168" viewBox="0 0 168 168" style={{ position: 'absolute', inset: 0, animation: 'splash-spin 8s linear infinite' }}>
          <circle cx="84" cy="84" r="78" fill="none" stroke="#ef4444" strokeWidth="0.7" strokeDasharray="2 6" opacity="0.55" />
          <circle cx="84" cy="84" r="70" fill="none" stroke="#ef4444" strokeWidth="0.5" strokeDasharray="1 12" opacity="0.45" />
        </svg>
        <svg width="168" height="168" viewBox="0 0 168 168" style={{ position: 'absolute', inset: 0, animation: 'splash-spin-rev 12s linear infinite' }}>
          <circle cx="84" cy="84" r="82" fill="none" stroke="#00e5ff" strokeWidth="0.5" strokeDasharray="0.5 18" opacity="0.5" />
        </svg>

        {/* Logo image */}
        <div style={{
          position: 'absolute', inset: 18,
          borderRadius: '50%',
          boxShadow: '0 0 70px #ef4444aa, 0 0 140px #ef444466, inset 0 0 22px #ef444333',
          animation: 'splash-rotate 6s ease-in-out infinite, splash-pulse 2.2s ease-in-out infinite',
        }}>
          <img src={_bapi.brandLogoUrl()} width={132} height={132} alt={b.app_name}
            style={{ width: '100%', height: '100%', objectFit: 'contain', borderRadius: '50%',
              filter: 'drop-shadow(0 0 14px var(--brand, #ef4444))' }} />
        </div>
      </div>

      {/* Wordmark */}
      <div style={{
        textAlign: 'center',
        opacity: phase >= 1 ? 1 : 0,
        transform: phase >= 1 ? 'translateY(0)' : 'translateY(10px)',
        transition: 'opacity 700ms var(--ease) 250ms, transform 800ms var(--ease) 250ms',
      }}>
        <div className="display" style={{ fontSize: 32, letterSpacing: '0.14em', fontWeight: 700, color: '#e6f1ff', textShadow: '0 0 24px var(--brand-soft, #ef444466)' }}>{b.app_name}</div>
        <div style={{ fontSize: 11, letterSpacing: '0.4em', color: '#6b7a92', marginTop: 6 }}>{b.app_sub} · v1.14.0</div>
        <div style={{ marginTop: 22, fontSize: 12, color: 'var(--brand, #ef4444)', fontStyle: 'italic', letterSpacing: 0.04 }}>{b.tagline_1} {b.tagline_2}</div>
      </div>

      {/* Bottom load bar */}
      <div style={{ position: 'absolute', bottom: 36, left: '50%', transform: 'translateX(-50%)', width: 240 }}>
        <div style={{ height: 2, background: '#1a2740', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: phase >= 2 ? '100%' : phase === 1 ? '32%' : '8%',
            background: 'linear-gradient(90deg, #ef4444, #00e5ff)',
            transition: 'width 6500ms var(--ease)',
            boxShadow: '0 0 12px #ef444466',
          }} />
        </div>
        <div style={{ marginTop: 8, fontSize: 9.5, letterSpacing: '0.18em', color: '#6b7a92', textAlign: 'center', fontFamily: 'JetBrains Mono' }}>
          {phase === 0 ? 'BOOTING THE DEEP…' :
           phase === 1 ? 'CALIBRATING TENTACLES…' :
           phase === 2 ? 'DESCENDING…' : 'READY'}
        </div>
      </div>

      <style>{`
        @keyframes splash-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes splash-spin-rev { from { transform: rotate(360deg); } to { transform: rotate(0deg); } }
        @keyframes splash-rotate { 0%,100% { transform: rotate(-6deg); } 50% { transform: rotate(6deg); } }
        @keyframes splash-pulse { 0%,100% { filter: brightness(1); } 50% { filter: brightness(1.18); } }
      `}</style>
    </div>
  );
}

/* Animated underwater caustics — SVG turbulence + displacement gives the
   classic shimmering light pattern you see on a pool floor / shallow seabed. */
function Caustics() {
  return (
    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', mixBlendMode: 'screen', opacity: 0.55 }}>
      <defs>
        <filter id="caustics-filter" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves="2" seed="7">
            <animate attributeName="baseFrequency" dur="14s" values="0.012 0.018;0.018 0.012;0.012 0.018" repeatCount="indefinite" />
          </feTurbulence>
          <feColorMatrix type="matrix" values="
            0 0 0 0 1
            0 0 0 0 0.95
            0 0 0 0 0.78
            0 0 0 1.8 -0.6" />
          <feGaussianBlur stdDeviation="1.4" />
          <feComposite in2="SourceGraphic" operator="in" />
        </filter>
        <radialGradient id="caustics-mask" cx="50%" cy="30%" r="80%">
          <stop offset="0%"  stopColor="#fff" stopOpacity="0.9" />
          <stop offset="60%" stopColor="#fff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#caustics-mask)" filter="url(#caustics-filter)" />
    </svg>
  );
}

/* Sunbeams piercing from above — three soft diagonal gradients that drift. */
function Sunbeams() {
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden', mixBlendMode: 'screen' }}>
      {[0,1,2].map(i => (
        <div key={i} style={{
          position: 'absolute', top: '-20%',
          left: `${20 + i * 28}%`,
          width: 120, height: '140%',
          background: 'linear-gradient(180deg, #ffd28a44 0%, #ffd28a11 35%, transparent 70%)',
          transform: `rotate(${-8 + i * 4}deg) translateX(-50%)`,
          filter: 'blur(14px)',
          animation: `sunbeam-drift ${9 + i * 2}s ease-in-out infinite`,
          animationDelay: `${-i * 1.4}s`,
          opacity: 0.55,
        }} />
      ))}
      <style>{`
        @keyframes sunbeam-drift {
          0%,100% { transform: rotate(-8deg) translateX(-30%); opacity: 0.35; }
          50%     { transform: rotate(-2deg) translateX(-10%); opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}

function SplashParticles() {
  // 14 small drifting dots
  const parts = Array.from({ length: 14 }).map((_, i) => ({
    id: i, x: (i * 73 % 100), y: ((i * 41 + 13) % 100),
    s: 1 + (i % 3) * 0.6,
    dur: 6 + (i % 5) * 2,
    delay: -(i * 0.7),
  }));
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {parts.map(p => (
        <div key={p.id} style={{
          position: 'absolute', left: p.x + '%', top: p.y + '%',
          width: p.s, height: p.s, borderRadius: 999,
          background: '#ef4444', boxShadow: '0 0 6px #ef4444',
          animation: `splash-drift ${p.dur}s ease-in-out infinite`,
          animationDelay: p.delay + 's',
          opacity: 0.5,
        }} />
      ))}
      <style>{`
        @keyframes splash-drift {
          0%,100% { transform: translate(0,0); opacity: 0.3; }
          50% { transform: translate(20px, -30px); opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}

/* ────────────────────── Onboarding ────────────────────── */
function Onboarding({ onDone, onSkip, personas = [], activePersonaId, setActivePersonaId, savePersona }) {
  const STEPS = [
    { id: 'welcome',   title: 'Welcome to the deep' },
    { id: 'persona',   title: 'Pick a persona' },
    { id: 'providers', title: 'Generation providers' },
    { id: 'channels',  title: 'Where you post' },
    { id: 'ready',     title: 'You\u2019re ready' },
  ];
  const [i, setI] = useStateOb(0);
  const [personaModal, setPersonaModal] = useStateOb(null);
  const step = STEPS[i];
  const last = i === STEPS.length - 1;

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 900,
      background: 'radial-gradient(circle at 30% 20%, #1a06064d 0%, transparent 60%), radial-gradient(circle at 70% 80%, #001a2466 0%, transparent 60%), #02060df2',
      backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24,
    }}>
      <div style={{
        width: 640, maxWidth: '100%', maxHeight: '94%',
        background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
        borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 80px #ef444422',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* Header: stepper */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 14 }}>
          <img src={_bapi.brandLogoUrl()} width={28} height={28} alt="" style={{ borderRadius: '50%', filter: 'drop-shadow(0 0 6px var(--brand-soft, #ef444488))' }} />
          <div style={{ flex: 1 }}>
            <div className="upper" style={{ color: 'var(--brand)' }}>Setup · {i + 1} / {STEPS.length}</div>
            <div className="display" style={{ fontSize: 14, color: 'var(--ink-strong)' }}>{step.title}</div>
          </div>
          <button onClick={onSkip} style={{ background: 'transparent', border: 0, color: 'var(--ink-soft)', cursor: 'pointer', fontSize: 11.5 }}>Skip for now</button>
        </div>

        {/* Stepper bar */}
        <div style={{ display: 'flex', gap: 3, padding: '0 18px 14px', borderBottom: '1px solid var(--stroke)' }}>
          {STEPS.map((s, idx) => (
            <div key={s.id} style={{
              flex: 1, height: 3, borderRadius: 999,
              background: idx <= i ? 'linear-gradient(90deg, var(--brand), var(--cyan))' : 'var(--stroke)',
              transition: 'background var(--dur-2) var(--ease)',
            }} />
          ))}
        </div>

        {/* Body */}
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '20px 22px' }}>
          {step.id === 'welcome'   && <WelcomeStep />}
          {step.id === 'persona'   && <PersonaStep personas={personas} activeId={activePersonaId} setActive={setActivePersonaId} onNew={() => setPersonaModal('new')} onEdit={p => setPersonaModal(p)} />}
          {step.id === 'providers' && <ProvidersStep />}
          {step.id === 'channels'  && <ChannelsStep />}
          {step.id === 'ready'     && <ReadyStep personas={personas} activeId={activePersonaId} />}
        </div>

        {/* Footer */}
        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <button disabled={i === 0} onClick={() => setI(i - 1)} style={{
            background: 'transparent', border: 0, color: i === 0 ? 'var(--ink-muted)' : 'var(--ink)',
            fontSize: 12, cursor: i === 0 ? 'default' : 'pointer', padding: '6px 10px',
          }}>← Back</button>
          <div style={{ fontSize: 11, color: 'var(--ink-muted)', flex: 1, textAlign: 'center' }}>
            You can adjust everything later in <span style={{ color: 'var(--ink-strong)' }}>Settings</span>.
          </div>
          {last
            ? <Button variant="primary" size="md" icon="zap" glow onClick={onDone}>Enter the studio</Button>
            : <Button variant="primary" size="md" iconRight="caretR" glow onClick={() => setI(i + 1)}>Continue</Button>
          }
        </div>
      </div>

      <PersonaCreatorModal
        open={!!personaModal}
        initial={personaModal === 'new' ? null : personaModal}
        onClose={() => setPersonaModal(null)}
        onSave={p => { savePersona?.(p); setPersonaModal(null); }}
      />
    </div>
  );
}

function StepHero({ icon, kicker, title, lead }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div className="upper" style={{ color: 'var(--brand)', marginBottom: 4 }}>{kicker}</div>
      <div className="display" style={{ fontSize: 24, color: 'var(--ink-strong)', display: 'flex', alignItems: 'center', gap: 12, letterSpacing: '-0.01em' }}>
        {icon && <Icon name={icon} size={22} style={{ color: 'var(--brand)' }} />}
        {title}
      </div>
      <div style={{ fontSize: 13, color: 'var(--ink-soft)', marginTop: 6, lineHeight: 1.55, maxWidth: 540 }}>{lead}</div>
    </div>
  );
}

function WelcomeStep() {
  return (
    <>
      <StepHero kicker="Welcome" title="You are about to pilot a studio." lead="Deepotus turns a single image (or a news item, or a sentence) into a finished 9:16 video and ships it to every channel where the shoal lives. We just need a few credentials and a handle." />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 6 }}>
        {[
          { i: 'sparkle', t: 'Studio', d: 'Compose graphs.' },
          { i: 'calendar', t: 'Scheduler', d: 'Queue posts per day.' },
          { i: 'send', t: 'Auto-post', d: 'X · TG · YT · IG.' },
        ].map(c => (
          <div key={c.t} style={{ padding: 14, background: 'var(--bg-panel)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)' }}>
            <Icon name={c.i} size={18} style={{ color: 'var(--brand)' }} />
            <div style={{ fontSize: 13, color: 'var(--ink-strong)', marginTop: 6 }}>{c.t}</div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{c.d}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 18, padding: 12, background: 'var(--bg-panel)', borderLeft: '2px solid var(--brand)', borderRadius: 4 }}>
        <div style={{ fontSize: 11.5, color: 'var(--ink)', lineHeight: 1.5 }}>
          Everything runs locally. API keys go in <span className="mono">backend/.env</span>. Your renders never leave your machine until a Scheduler post fires.
        </div>
      </div>
    </>
  );
}

function PersonaStep({ personas, activeId, setActive, onNew, onEdit }) {
  return (
    <>
      <StepHero kicker="Persona" title="Pick or create a voice." lead="Each persona is a JSON file with tone, vocabulary and a voice mode. The active one shapes the News scripter, the prompt generator and the default voiceover. You can swap any time from Settings." icon="octopus" />
      <PersonaSelector
        personas={personas}
        activeId={activeId}
        onSelect={setActive}
        onNew={onNew}
        onEdit={onEdit}
        compact
      />
    </>
  );
}

function ReadyStep({ personas, activeId }) {
  const active = personas?.find(p => p.id === activeId);
  return (
    <>
      <StepHero kicker="Ready" title="The deep is calibrated." lead="Open Studio to compose your first graph, or go straight to Scheduler to plan the week. You can revisit this checklist from the command palette (⌘K → 'Replay onboarding')." icon="zap" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 6 }}>
        {[
          ['Active persona', active ? `${active.name} · ${active.handle}` : '—'],
          ['Providers ready', 'fal.ai · HeyGen · ElevenLabs · Anthropic'],
          ['Channels connected', 'X · Telegram · YouTube'],
          ['Channels pending', 'Instagram'],
        ].map(([k, v]) => (
          <div key={k} style={{ display: 'flex', gap: 12, padding: '8px 10px', background: 'var(--bg-panel)', borderRadius: 'var(--r-sm)' }}>
            <Icon name="check" size={14} style={{ color: 'var(--green)' }} />
            <span style={{ fontSize: 12, color: 'var(--ink)', flex: 1 }}>{k}</span>
            <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink-strong)' }}>{v}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function ProvidersStep() {
  const h = useHealth();
  const rows = [
    { k: 'FAL_KEY',         label: 'fal.ai',     why: 'Seedance + image generation', required: true,  set: !!h?.fal_configured },
    { k: 'HEYGEN_API_KEY',  label: 'HeyGen',     why: 'Talking avatars',                    required: false, set: !!h?.heygen_enabled },
    { k: 'ELEVENLABS_API_KEY', label: 'ElevenLabs', why: 'Voiceover',                       required: false, set: !!h?.voiceover_enabled },
    { k: 'ANTHROPIC_API_KEY',  label: 'Anthropic',  why: 'News summary + marketing plans (cloud)', required: false, set: !!h?.has_summarizer },
    { k: 'OLLAMA_MODEL',    label: 'Ollama (local LLM)', why: 'Marketing plans on your own machine — free, private', required: false, set: !!h?.ollama_enabled },
  ];
  const missing = rows.filter(r => !r.set && r.required);
  return (
    <>
      <StepHero kicker="Generators" title="Plug in your generation providers." lead="The badges reflect what's in backend/.env. Only fal.ai is required. For marketing plans you can use Anthropic (cloud) OR a local Ollama model — nothing leaves your machine with Ollama. Edit backend/.env and restart to apply." icon="sparkle" />
      <Panel style={{ padding: 0 }}>
        {rows.map((r, i) => (
          <div key={r.k} style={{
            display: 'grid', gridTemplateColumns: '32px 1fr 1fr auto', gap: 12, alignItems: 'center',
            padding: '12px 14px', borderTop: i ? '1px solid var(--stroke)' : 'none',
          }}>
            <div style={{ width: 26, height: 26, borderRadius: 6, background: 'var(--bg-panel-2)', border: '1px solid var(--stroke)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: r.set ? 'var(--green)' : 'var(--red)' }}>
              <Icon name={r.set ? 'check' : 'warn'} size={12} />
            </div>
            <div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>{r.label} {r.required && <span style={{ color: 'var(--brand)', fontSize: 10 }}>· required</span>}</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{r.why} · <span className="mono">{r.k}</span></div>
            </div>
            <div style={{ fontSize: 11, color: r.set ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--f-mono)' }}>
              {r.set ? '••••••••••••' : '(not set in backend/.env)'}
            </div>
            <Badge tone={r.set ? 'green' : 'red'} dot>{r.set ? 'set' : 'empty'}</Badge>
          </div>
        ))}
      </Panel>
      {missing.length > 0 && (
        <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-panel)', borderLeft: '2px solid var(--amber)', borderRadius: 4 }}>
          <div style={{ fontSize: 12, color: 'var(--ink)' }}>
            <strong style={{ color: 'var(--amber)' }}>{missing.length} key{missing.length === 1 ? '' : 's'} missing.</strong> Open <span className="mono">backend/.env</span>, paste the value(s) for <span className="mono">{missing.map(r => r.k).join(', ')}</span> and restart the backend. The status updates here automatically (polled every 10s).
          </div>
        </div>
      )}
    </>
  );
}

function ChannelsStep() {
  return (
    <>
      <StepHero kicker="Distribution" title="Connect your channels." lead="The Scheduler ships finished renders to whatever is connected here. You can skip any and connect later from Settings → Connected accounts." icon="send" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[
          { id: 'x', label: 'X (Twitter)', icon: 'channelX', color: '#e6f1ff', desc: 'Posts threads and replies via API v2.', status: 'connected' },
          { id: 'telegram', label: 'Telegram', icon: 'channelTelegram', color: '#29b6f6', desc: 'Bot token + channel chat ID via @BotFather.', status: 'connected' },
          { id: 'youtube', label: 'YouTube', icon: 'channelYoutube', color: '#ef4444', desc: 'OAuth — uploads Shorts to your channel.', status: 'connected' },
          { id: 'instagram', label: 'Instagram', icon: 'channelInstagram', color: '#c084fc', desc: 'Requires Business account on a Facebook Page.', status: 'missing' },
        ].map(c => {
          const ok = c.status === 'connected';
          return (
            <div key={c.id} style={{
              padding: 14, borderRadius: 'var(--r)',
              background: ok ? 'var(--bg-panel)' : 'var(--bg-panel)',
              border: `1px solid ${ok ? c.color + '55' : 'var(--stroke)'}`,
              boxShadow: ok ? `0 0 16px ${c.color}22` : 'none',
              display: 'flex', flexDirection: 'column', gap: 8,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 30, height: 30, borderRadius: 7, background: ok ? c.color + '22' : 'var(--bg-panel-2)', color: ok ? c.color : 'var(--ink-muted)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon name={c.icon} size={15} />
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: 'var(--ink-strong)' }}>{c.label}</div>
                  <Badge tone={ok ? 'green' : 'red'} dot>{ok ? 'connected' : 'not yet'}</Badge>
                </div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>{c.desc}</div>
              <Button variant={ok ? 'outline' : 'primary'} size="sm" icon={ok ? 'edit' : 'link'} glow={!ok}>{ok ? 'Manage' : 'Connect'}</Button>
            </div>
          );
        })}
      </div>
    </>
  );
}

export { Splash, Onboarding };
