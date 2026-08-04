// screens.jsx — Quick, News, Templates, Library, Settings (ESM port)
import React, { useState as useStateScr, useRef, useEffect } from 'react';
import { Icon, Button, IconButton, Input, Badge, Toggle, Slider, Panel, InspectorSection, Field, Select, Thumb } from './atoms.jsx';
import { PromptGeneratorModal, PromptTemplateGallery } from './prompts.jsx';
import { PersonaCreatorModal, PersonaSelector } from './persona.jsx';
import { api, fmtDur, fmtAgo, fmtSize, useHealth, refreshHealth, useBranding, refreshBranding, applyBrandColors, urlParam } from './api.js';

/* ────────────────────── Sample data ────────────────────── */
const SAMPLE_NEWS = [
  { id: 'n1', title: 'Solana memecoin volume +38% in 24h, retail piles in', source: 'cryptoslate.com', age: '34m', tags: ['solana','memecoin'], essence: 'The shoal awakens. Liquidity returns to the depths.' },
  { id: 'n2', title: '$DEEPOTUS holders cross 12,000 — second wave of inkings', source: 'birdeye.so', age: '1h', tags: ['$deepotus','community'], essence: 'Twelve thousand strong. The tentacle widens.' },
  { id: 'n3', title: 'Jupiter routes deeper liquidity into long-tail SPL tokens', source: 'jup.ag/blog', age: '3h', tags: ['solana','dex'], essence: 'Jupiter charts a deeper current.' },
  { id: 'n4', title: 'Pyth oracle launches sub-200ms feeds for shitcoin perps', source: 'pyth.network', age: '5h', tags: ['oracle','solana'], essence: 'The oracle blinks faster than the market.' },
  { id: 'n5', title: 'Helius adds 8-hop WebSocket fanout, latency falls 42%', source: 'helius.xyz', age: '8h', tags: ['infra'], essence: 'The currents quicken.' },
  { id: 'n6', title: 'BONK & WIF lose ground as fresh memes capture rotation', source: 'coingecko.com', age: '9h', tags: ['memecoin'], essence: 'Old gods sleep. New tentacles uncoil.' },
];

const SAMPLE_TEMPLATES = [
  { id: 'tpl_news_reel',    name: 'News reel + avatar',   tags: ['news','9:16'], builtIn: true },
  { id: 'tpl_split_lower',  name: 'Split lower-third',    tags: ['news','9:16'], builtIn: true },
  { id: 'tpl_avatar_pip',   name: 'Avatar PIP corner',    tags: ['avatar','9:16'], builtIn: true },
  { id: 'tpl_full_avatar',  name: 'Full avatar + ticker', tags: ['avatar','9:16'], builtIn: true },
  { id: 'tpl_grid_3',       name: 'Triptych grid',        tags: ['custom','1:1'], builtIn: false },
  { id: 'tpl_oracle_lab',   name: 'Oracle Lab (custom)',  tags: ['custom','9:16'], builtIn: false },
];

const SAMPLE_LIBRARY = {
  Images: [
    { name: 'octopus_throne_01.png',     kind: 'image', size: '2.4 MB', date: 'May 18' },
    { name: 'abyss_shoal_v2.png',         kind: 'image', size: '1.8 MB', date: 'May 17' },
    { name: 'oracle_eye_drift.png',       kind: 'image', size: '2.1 MB', date: 'May 16' },
    { name: 'tentacle_lo-fi_keyart.png',  kind: 'image', size: '3.0 MB', date: 'May 15' },
    { name: 'deep_pump_chart_glow.png',   kind: 'image', size: '0.9 MB', date: 'May 15' },
    { name: 'submarine_porthole.png',     kind: 'image', size: '1.4 MB', date: 'May 14' },
  ],
  Renders: [
    { name: 'tweet_2026-05-19_oracle.mp4', kind: 'render', size: '14.2 MB', date: '6m ago', dur: '00:18', provider: 'Composition' },
    { name: 'reel_solana_pump_v3.mp4',     kind: 'render', size: '22.1 MB', date: '1h ago', dur: '00:23', provider: 'News reel' },
    { name: 'avatar_inktober_drop.mp4',    kind: 'render', size: '9.4 MB',  date: '3h ago', dur: '00:11', provider: 'HeyGen' },
    { name: 'seed_glitch_throne.mp4',      kind: 'render', size: '6.8 MB',  date: '5h ago', dur: '00:10', provider: 'Seedance' },
  ],
  Audio: [
    { name: 'deep_ambient_lo_fi.wav',  kind: 'audio', size: '8.1 MB',  date: 'May 12', dur: '02:14' },
    { name: 'voiceover_oracle_03.wav', kind: 'audio', size: '1.4 MB',  date: 'May 11', dur: '00:17' },
    { name: 'sonar_ping_loop.wav',     kind: 'audio', size: '0.6 MB',  date: 'May 10', dur: '00:04' },
  ],
  Captions: [
    { name: 'oracle_solana_pump.srt', kind: 'text', size: '1.1 KB',  date: 'today', dur: '32 lines' },
    { name: 'tentacle_drop_dialog.srt', kind: 'text', size: '0.9 KB', date: 'May 18', dur: '21 lines' },
  ],
};

/* ────────────────────── Quick ────────────────────── */
function QuickScreen({ variant, activePersona }) {
  const h = useHealth();
  const [mode, setMode] = useStateScr(() => {
    const m = urlParam('mode');
    return ['seedance', 'heygen', 'comp'].includes(m) ? m : 'seedance';
  });
  const [prompt, setPrompt] = useStateScr('A deep-sea throne lit by bioluminescent currents, slow cinematic push-in, indigo and cyan, particles drifting.');
  const [generatorOpen, setGeneratorOpen] = useStateScr(false);
  const [images, setImages] = useStateScr([]);
  const [seedTemplates, setSeedTemplates] = useStateScr([]);
  const [startImage, setStartImage] = useStateScr('');
  const [endImage, setEndImage] = useStateScr('');
  const [style, setStyle] = useStateScr('cinematic');
  const [duration, setDuration] = useStateScr(10);
  const [aspect, setAspect] = useStateScr('9:16');
  const [seed, setSeed] = useStateScr(String(Math.floor(Math.random() * 10000)));
  const [generating, setGenerating] = useStateScr(false);
  const [pickedTpl, setPickedTpl] = useStateScr('');

  // Style mapping: backend StylePreset only accepts ugc_raw|cinematic|hybrid.
  // The richer "vibe" picker injects keywords into the prompt and resolves
  // to one of those 3 presets so the API call doesn't 422.
  const VIBES = [
    { id: 'cinematic',   preset: 'cinematic', tags: '' },
    { id: 'ugc_raw',     preset: 'ugc_raw',   tags: 'shot on phone, handheld, available light, slight motion blur' },
    { id: 'hybrid',      preset: 'hybrid',    tags: '' },
    { id: 'documentary', preset: 'cinematic', tags: 'documentary realism, observational, natural light, candid framing' },
    { id: 'glitch',      preset: 'hybrid',    tags: 'glitch aesthetic, datamosh, RGB shift, scanlines, VHS chroma noise' },
    { id: 'dream',       preset: 'cinematic', tags: 'dreamlike haze, soft focus, drifting motion, pastel bloom' },
    { id: 'deep-sea',    preset: 'cinematic', tags: 'deep-sea bioluminescence, indigo and cyan tones, particulate currents, slow push-in' },
    { id: 'noir',        preset: 'cinematic', tags: 'chiaroscuro noir, deep shadows, single key light, neon rim, smoke' },
  ];
  const [vibe, setVibe] = useStateScr('cinematic');
  function resolveStyle() {
    const v = VIBES.find(x => x.id === vibe) || VIBES[0];
    return { preset: v.preset, tags: v.tags };
  }

  // HeyGen-specific state.
  const [avatars, setAvatars] = useStateScr([]);     // {avatar_id, name, avatar_type}
  const [voices, setVoices] = useStateScr([]);       // {voice_id, name, language}
  const [avatarId, setAvatarId] = useStateScr('');
  const [voiceId, setVoiceId] = useStateScr('');
  const [script, setScript] = useStateScr('From the deep, the prophet speaks. The shoal awakens.');
  const [avatarQuery, setAvatarQuery] = useStateScr('');
  const [photoUploading, setPhotoUploading] = useStateScr(false);
  const [photoMsg, setPhotoMsg] = useStateScr('');
  const photoRef = React.useRef(null);

  // Composition extras.
  const [compLayout, setCompLayout] = useStateScr('sequential');

  // Last submit result (job id / error).
  const [lastResult, setLastResult] = useStateScr(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.listImages(), api.listSeedanceTemplates()]).then(([imgRes, tpls]) => {
      if (!alive) return;
      const imgs = (imgRes?.images || []).map(im => im.filename);
      setImages(imgs);
      if (!startImage && imgs.length) setStartImage(imgs[0]);
      setSeedTemplates(Array.isArray(tpls) ? tpls : []);
    });
    return () => { alive = false; };
  }, []);

  // Load HeyGen avatars + voices lazily when the user switches to heygen/comp.
  useEffect(() => {
    if (mode === 'seedance') return;
    if (!h?.heygen_enabled) return;
    let alive = true;
    Promise.all([api.listHeygenAvatars(), api.listHeygenVoices()]).then(([a, v]) => {
      if (!alive) return;
      const list = [
        ...((a?.avatars || []).map(x => ({ ...x, _kind: 'avatar' }))),
        ...((a?.talking_photos || []).map(x => ({
          avatar_id: x.talking_photo_id || x.id, name: x.talking_photo_name || x.name || x.id,
          avatar_type: 'talking_photo', _kind: 'talking_photo',
        }))),
      ];
      setAvatars(list);
      if (!avatarId && list.length) setAvatarId(list[0].avatar_id);
      const vs = v?.voices || [];
      setVoices(vs);
      if (!voiceId && vs.length) setVoiceId(vs[0].voice_id);
    });
    return () => { alive = false; };
  }, [mode, h?.heygen_enabled]);

  async function uploadPhotoAvatar(file) {
    if (!file) return;
    setPhotoUploading(true);
    setPhotoMsg('Uploading + training (5-30s)…');
    const r = await api.createPhotoAvatar(file, file.name.replace(/\.[^.]+$/, ''));
    setPhotoUploading(false);
    if (r.ok) {
      setPhotoMsg('Avatar created ✓');
      // Refresh avatars list and select the new one.
      const a = await api.listHeygenAvatars();
      const list = [
        ...((a?.avatars || []).map(x => ({ ...x, _kind: 'avatar' }))),
        ...((a?.talking_photos || []).map(x => ({
          avatar_id: x.talking_photo_id || x.id, name: x.talking_photo_name || x.name || x.id,
          avatar_type: 'talking_photo', _kind: 'talking_photo',
        }))),
      ];
      setAvatars(list);
      if (r.photo_avatar_id) setAvatarId(r.photo_avatar_id);
      setTimeout(() => setPhotoMsg(''), 4000);
    } else {
      setPhotoMsg('Failed: ' + (r.error || 'unknown'));
    }
  }

  async function doGenerate() {
    if (generating) return;
    setGenerating(true);
    setLastResult(null);
    try {
      if (mode === 'seedance') {
        if (!startImage) { setLastResult({ error: 'Pick a start image first.' }); return; }
        const { preset, tags } = resolveStyle();
        const fullPrompt = tags ? `${prompt} ${tags}`.trim() : prompt;
        const body = {
          image_filename: startImage,
          image_filename_end: endImage || null,
          custom_prompt: fullPrompt,
          style: preset, duration_s: duration, aspect_ratio: aspect,
          seed: Number(seed) || undefined,
          voiceover_enabled: false,
          template_id: pickedTpl || null,
        };
        const r = await api.postJson('/generate', body);
        setLastResult(r.ok ? { jobId: r.job_id, msg: 'Seedance queued.' } : { error: r.error });
      } else if (mode === 'heygen') {
        if (!avatarId || !voiceId) { setLastResult({ error: 'Pick avatar + voice.' }); return; }
        if (!script.trim()) { setLastResult({ error: 'Empty script.' }); return; }
        const av = avatars.find(a => a.avatar_id === avatarId);
        const r = await api.postJson('/generate/heygen', {
          avatar_id: avatarId,
          voice_id: voiceId,
          script: script.trim(),
          avatar_type: av?.avatar_type || 'avatar',
          aspect_ratio: aspect,
          speed: 1.0,
        });
        setLastResult(r.ok ? { msg: 'HeyGen queued.' } : { error: r.error });
      } else if (mode === 'comp') {
        if (!startImage) { setLastResult({ error: 'Pick a Seedance start image.' }); return; }
        if (!avatarId || !voiceId) { setLastResult({ error: 'Pick avatar + voice.' }); return; }
        if (!script.trim()) { setLastResult({ error: 'Empty HeyGen script.' }); return; }
        const av = avatars.find(a => a.avatar_id === avatarId);
        const { preset, tags } = resolveStyle();
        const fullPrompt = tags ? `${prompt} ${tags}`.trim() : prompt;
        const r = await api.postJson('/generate/composition', {
          seedance: {
            image_filename: startImage,
            custom_prompt: fullPrompt,
            style: preset, duration_s: duration, aspect_ratio: aspect,
            seed: Number(seed) || undefined,
            voiceover_enabled: false,
            template_id: pickedTpl || null,
            prompt_source: pickedTpl ? 'template' : 'free',
          },
          heygen: {
            avatar_id: avatarId, voice_id: voiceId, script: script.trim(),
            avatar_type: av?.avatar_type || 'avatar',
            aspect_ratio: aspect, speed: 1.0,
          },
          layout: compLayout,
          audio_source: 'heygen',
          transition_duration_s: 0.5,
        });
        setLastResult(r.ok ? { msg: 'Composition queued.' } : { error: r.error });
      }
    } finally {
      setGenerating(false);
    }
  }

  const heygenDisabled = !h?.heygen_enabled;
  const falDisabled = !h?.fal_configured;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', height: '100%', minHeight: 0 }}>
      {/* Left source/params panel */}
      <div style={{ background: 'var(--bg-panel)', borderRight: '1px solid var(--stroke)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
          <div className="display" style={{ fontSize: 17, color: 'var(--ink-strong)' }}>Quick</div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-soft)' }}>One form, one result. For solo posts.</div>
          <div style={{ display: 'flex', gap: 4, marginTop: 12, padding: 3, background: 'var(--bg-base)', borderRadius: 'var(--r-sm)', border: '1px solid var(--stroke)' }}>
            {[['seedance','Seedance','sparkle', falDisabled],['heygen','HeyGen','mic', heygenDisabled],['comp','Composition','layers', falDisabled || heygenDisabled]].map(([k,l,ic, disabled]) => (
              <button key={k} onClick={() => setMode(k)} disabled={disabled}
                title={disabled ? `${l} disabled — required API key missing in backend/.env` : ''} style={{
                flex: 1, height: 28, padding: '0 8px',
                background: mode === k ? 'var(--bg-panel-2)' : 'transparent',
                border: mode === k ? '1px solid var(--stroke-strong)' : '1px solid transparent',
                color: disabled ? 'var(--ink-muted)' : mode === k ? 'var(--ink-strong)' : 'var(--ink-soft)',
                borderRadius: 'var(--r-sm)', cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 11.5, fontWeight: 500,
                opacity: disabled ? 0.55 : 1,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}>
                <Icon name={ic} size={12} />{l}
              </button>
            ))}
          </div>
          {(mode === 'heygen' || mode === 'comp') && heygenDisabled && (
            <div style={{ marginTop: 8, padding: 8, background: 'var(--red-soft)', border: '1px solid var(--red)', borderRadius: 'var(--r-sm)', fontSize: 11, color: 'var(--ink)' }}>
              <strong style={{ color: 'var(--red)' }}>HEYGEN_API_KEY not set.</strong> Add it to <span className="mono">backend/.env</span> and restart the backend.
            </div>
          )}
          {(mode === 'heygen' || mode === 'comp') && !heygenDisabled && h?.heygen_reachable === false && (
            <div style={{ marginTop: 8, padding: 8, background: 'var(--amber-soft)', border: '1px solid var(--amber)', borderRadius: 'var(--r-sm)', fontSize: 11, color: 'var(--ink)' }}>
              <strong style={{ color: 'var(--amber)' }}>HeyGen API unreachable.</strong> Key is loaded but the backend can't reach <span className="mono">app.heygen.com</span>. Probably an SSL cert / proxy / antivirus issue. Avatars + voices won't load. <span style={{ color: 'var(--ink-soft)' }}>{h?.heygen_message?.slice(0, 80)}</span>
            </div>
          )}
          {activePersona && (
            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', background: 'var(--bg-panel-2)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)' }}>
              <Icon name={activePersona.avatar || 'octopus'} size={12} style={{ color: 'var(--brand)' }} />
              <span style={{ fontSize: 11, color: 'var(--ink-soft)' }}>persona</span>
              <span style={{ fontSize: 11.5, color: 'var(--ink-strong)', fontWeight: 500 }}>{activePersona.name}</span>
              <span style={{ flex: 1 }} />
              <span className="mono" style={{ fontSize: 10, color: 'var(--ink-muted)' }}>{activePersona.voiceMode}</span>
            </div>
          )}
        </div>

        <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
          {mode !== 'heygen' && (
            <InspectorSection label="Source (Seedance)">
              <Field label="Start image">
                {images.length > 0 ? (
                  <Select value={startImage} options={images.map(f => ({ value: f, label: f }))} onChange={setStartImage} />
                ) : (
                  <DropZone label="upload images in Library" kind="image" />
                )}
              </Field>
              <Field label="End image (optional)">
                {images.length > 0 ? (
                  <Select value={endImage} options={[{ value: '', label: '— none —' }, ...images.map(f => ({ value: f, label: f }))]} onChange={setEndImage} />
                ) : (
                  <DropZone label="drop or pick" kind="image" />
                )}
              </Field>
            </InspectorSection>
          )}

          {(mode === 'heygen' || mode === 'comp') && !heygenDisabled && (
            <InspectorSection label={`Avatar (${avatars.length})`} right={
              <Button variant="ghost" size="sm" icon="upload" onClick={() => photoRef.current?.click()}>
                {photoUploading ? 'Uploading…' : 'Upload photo'}
              </Button>
            }>
              <input ref={photoRef} type="file" accept="image/png,image/jpeg,image/webp" style={{ display: 'none' }}
                onChange={e => { uploadPhotoAvatar(e.target.files?.[0]); e.target.value = ''; }} />
              <Field label="Search avatars">
                <Input icon="search" value={avatarQuery} onChange={setAvatarQuery} placeholder={`Search ${avatars.length} avatars…`} />
              </Field>
              <Field label="Avatar">
                <Select value={avatarId}
                  options={(avatars.filter(a => {
                    const q = avatarQuery.trim().toLowerCase();
                    if (!q) return true;
                    return `${a.name || ''} ${a.avatar_id || ''} ${a.avatar_type || ''}`.toLowerCase().includes(q);
                  }).slice(0, 200)).map(a => ({
                    value: a.avatar_id,
                    label: `${a._kind === 'talking_photo' ? '📷 ' : ''}${a.name || a.avatar_id} ${a.gender ? `· ${a.gender}` : ''}`,
                  }))}
                  onChange={setAvatarId} />
              </Field>
              <Field label="Voice">
                <Select value={voiceId}
                  options={voices.slice(0, 200).map(v => ({
                    value: v.voice_id,
                    label: `${v.name || v.voice_id} ${v.language ? `· ${v.language}` : ''}`,
                  }))}
                  onChange={setVoiceId} />
              </Field>
              {photoMsg && (
                <div style={{ marginTop: 6, fontSize: 11, color: photoMsg.startsWith('Failed') ? 'var(--red)' : 'var(--green)' }}>{photoMsg}</div>
              )}
            </InspectorSection>
          )}

          {(mode === 'heygen' || mode === 'comp') && (
            <InspectorSection label={`Script (${script.length}/4900 chars)`}>
              <textarea value={script} onChange={e => setScript(e.target.value.slice(0, 4900))} rows={5} style={{
                width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)',
                borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical',
              }} />
            </InspectorSection>
          )}

          {mode === 'comp' && (
            <InspectorSection label="Composition layout">
              <Field><Select value={compLayout} options={[
                { value: 'sequential',   label: 'Sequential (Seedance → HeyGen)' },
                { value: 'split_vstack', label: 'Split vertical (avatar bottom)' },
                { value: 'split_hstack', label: 'Split horizontal' },
              ]} onChange={setCompLayout} /></Field>
            </InspectorSection>
          )}

          <InspectorSection label="Parameters">
            <Field label="Vibe (style + keywords appended to the prompt)">
              <Select value={vibe} options={VIBES.map(v => ({
                value: v.id,
                label: `${v.id}${v.preset !== v.id ? ` · preset:${v.preset}` : ''}${v.tags ? ' · +tags' : ''}`,
              }))} onChange={setVibe} />
            </Field>
            <Field><Slider label="Duration" value={duration} min={5} max={60} step={5} unit="s" onChange={setDuration} /></Field>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Field label="Aspect"><Select value={aspect} options={['9:16','1:1','16:9','4:5']} onChange={setAspect} /></Field>
              <Field label="Seed"><Input mono value={seed} onChange={setSeed} /></Field>
            </div>
            <Field><Toggle checked={false} label="Voice (HeyGen comp)" onChange={()=>{}} /></Field>
          </InspectorSection>

          {seedTemplates.length > 0 && (
            <InspectorSection label={`Seedance templates (${seedTemplates.length})`}>
              <Select value={pickedTpl}
                options={[{ value: '', label: '— none —' }, ...seedTemplates.map(t => ({ value: t.id, label: t.name || t.id }))]}
                onChange={(v) => {
                  setPickedTpl(v);
                  const t = seedTemplates.find(x => x.id === v);
                  if (t && t.prompt) setPrompt(t.prompt);
                }} />
            </InspectorSection>
          )}

          <InspectorSection label="Prompt templates" right={<Button variant="ghost" size="sm" icon="sparkle" onClick={() => setGeneratorOpen(true)}>Generate</Button>}>
            <PromptTemplateGallery onPick={t => setPrompt(t.body)} />
          </InspectorSection>

          <InspectorSection label="Prompt">
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={6} style={{
              width: '100%', padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)',
              borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, resize: 'vertical',
            }} />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6 }}>
              <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-muted)' }}>{prompt.length} ch · ~{prompt.split(' ').filter(Boolean).length} words</span>
              <Button variant="link" size="sm" icon="sparkle" onClick={() => setGeneratorOpen(true)}>Open prompt generator</Button>
            </div>
          </InspectorSection>
        </div>

        <div style={{ padding: 14, borderTop: '1px solid var(--stroke)', background: 'var(--bg-panel-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, fontSize: 11.5 }}>
            <span className="soft">Est. cost</span>
            <span className="mono" style={{ color: 'var(--amber)' }}>$0.18 · ~30s</span>
          </div>
          <Button variant="primary" size="lg" icon={generating ? 'sparkle' : 'play'} glow style={{ width: '100%' }}
            onClick={doGenerate} disabled={generating || (mode === 'seedance' && !startImage) || (mode !== 'seedance' && heygenDisabled)}>
            {generating ? 'Queueing…' : `Generate ${mode === 'comp' ? 'composition' : mode}`}
          </Button>
          {lastResult && (
            <div style={{ marginTop: 8, padding: 8, borderRadius: 'var(--r-sm)',
              background: lastResult.error ? 'var(--red-soft)' : 'var(--green-soft)',
              border: `1px solid ${lastResult.error ? 'var(--red)' : 'var(--green)'}`,
              fontSize: 11, color: 'var(--ink)' }}>
              {lastResult.error
                ? <><strong style={{ color: 'var(--red)' }}>Failed:</strong> {lastResult.error.slice(0, 200)}</>
                : <><strong style={{ color: 'var(--green)' }}>Queued.</strong> {lastResult.msg || ''} {lastResult.jobId && <span className="mono"> · {String(lastResult.jobId).slice(0, 10)}</span>} Watch the Job Dock below.</>}
            </div>
          )}
        </div>
      </div>

      {/* Right: live preview — aspect follows the selected ratio */}
      {(() => {
        // Map "9:16" → { ratio, w, h, maxH for sizing }
        const ratios = {
          '9:16': { css: '9 / 16', w: 1080, h: 1920 },
          '1:1':  { css: '1 / 1',  w: 1080, h: 1080 },
          '16:9': { css: '16 / 9', w: 1920, h: 1080 },
          '4:5':  { css: '4 / 5',  w: 1080, h: 1350 },
        };
        const ar = ratios[aspect] || ratios['9:16'];
        const isLandscape = ar.w > ar.h;
        // Frame size: portrait/square → height-bound, landscape → width-bound.
        const frameStyle = isLandscape
          ? { width: 420, aspectRatio: ar.css }
          : { height: 460, aspectRatio: ar.css };
        return (
      <div style={{ position: 'relative', background: 'var(--bg-base)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: variant === 'reef'
            ? 'radial-gradient(circle at 30% 40%, #053040 0%, transparent 60%), radial-gradient(circle at 70% 70%, #2a0d3e 0%, transparent 60%)'
            : 'radial-gradient(circle at center, #08182955 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{
          ...frameStyle,
          background: 'linear-gradient(160deg, #053040 0%, #02060d 80%)',
          border: '1px solid var(--stroke-strong)',
          borderRadius: 'var(--r-lg)',
          position: 'relative', overflow: 'hidden',
          boxShadow: '0 24px 80px #000a, 0 0 60px var(--cyan-soft)',
          transition: 'width 320ms var(--ease), height 320ms var(--ease)',
        }}>
          <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg, transparent 0 10px, #00e5ff10 10px 11px)' }} />
          <div style={{ position: 'absolute', top: 12, left: 12, right: 12, display: 'flex', justifyContent: 'space-between' }}>
            <Badge tone="cyan" dot>{aspect} · preview</Badge>
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-soft)' }}>{ar.w} × {ar.h}</span>
          </div>
          {startImage ? (
            <img src={api.imageUrl(startImage)} alt={startImage}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8 }}>
              <Icon name="image" size={42} style={{ color: 'var(--amber)', filter: 'drop-shadow(0 0 12px var(--amber-soft))' }} />
              <span style={{ fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--ink-soft)' }}>upload an image in Library</span>
            </div>
          )}
          <div style={{ position: 'absolute', bottom: 14, left: 14, right: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, background: '#02060daa', padding: '4px 8px', borderRadius: 4 }}>
            <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--cyan)' }}>seed:{seed}</span>
            <span style={{ fontFamily: 'var(--f-mono)', color: 'var(--ink-soft)' }}>{vibe} · {duration}s</span>
          </div>
        </div>
        <div style={{ position: 'absolute', bottom: 24, left: 24, right: 24, display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: 'var(--ink-soft)' }}>
          <Icon name="warn" size={13} style={{ color: 'var(--amber)' }} />
          You're about to call <span className="mono strong">fal.ai</span> · expect 30–45s · this will queue in the Job Dock.
        </div>
      </div>
        );
      })()}

      <PromptGeneratorModal open={generatorOpen} onClose={() => setGeneratorOpen(false)} onUse={p => setPrompt(p)} initial={prompt} />
    </div>
  );
}

/* DropZone */
function DropZone({ label, kind = 'image', filled }) {
  return (
    <div style={{
      height: 90, padding: 10,
      background: filled ? 'var(--bg-base)' : 'transparent',
      border: `1px dashed ${filled ? 'var(--amber)' : 'var(--stroke-strong)'}`,
      borderRadius: 'var(--r-sm)',
      display: 'flex', alignItems: 'center', gap: 10,
      transition: 'all var(--dur-1) var(--ease)',
      cursor: 'pointer',
    }}>
      {filled
        ? <Thumb kind={kind} size={68} />
        : <div style={{
            width: 68, height: 68, borderRadius: 'var(--r-sm)',
            background: 'var(--bg-panel)', border: '1px solid var(--stroke)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Icon name="upload" size={20} style={{ color: 'var(--ink-muted)' }} /></div>
      }
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)' }}>{label}</div>
        <div style={{ fontSize: 10.5, color: 'var(--ink-soft)', marginTop: 2 }}>{filled ? '1080 × 1920 · 2.4 MB' : 'PNG, JPG, WEBP up to 16MB'}</div>
      </div>
    </div>
  );
}

/* ────────────────────── News ────────────────────── */
function NewsScreen({ variant }) {
  const [picked, setPicked] = useStateScr(new Set(['n1','n2']));
  function toggle(id) {
    const s = new Set(picked);
    s.has(id) ? s.delete(id) : s.add(id);
    setPicked(s);
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr 320px', height: '100%', minHeight: 0 }}>
      {/* Sources */}
      <div style={{ background: 'var(--bg-panel)', borderRight: '1px solid var(--stroke)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Sources</div>
            <Button variant="ghost" size="sm" icon="plus">Add</Button>
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-soft)', marginTop: 2 }}>RSS feeds · 6 active</div>
        </div>
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          {[
            ['cryptoslate.com', true,  '34m'],
            ['birdeye.so',      true,  '1h'],
            ['jup.ag/blog',     true,  '3h'],
            ['pyth.network',    true,  '5h'],
            ['helius.xyz',      true,  '8h'],
            ['coingecko.com',   true,  '9h'],
            ['theblock.co',     false, '—'],
          ].map(([host, on, age]) => (
            <div key={host} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px', borderLeft: on ? '2px solid var(--cyan)' : '2px solid transparent' }}>
              <Icon name="rss" size={13} style={{ color: on ? 'var(--cyan)' : 'var(--ink-muted)' }} />
              <span style={{ flex: 1, fontSize: 12, color: on ? 'var(--ink-strong)' : 'var(--ink-muted)' }}>{host}</span>
              <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-soft)' }}>{age}</span>
              <Toggle checked={on} onChange={()=>{}} />
            </div>
          ))}
        </div>
        <div style={{ padding: 12, borderTop: '1px solid var(--stroke)', display: 'flex', gap: 8 }}>
          <Button variant="outline" size="sm" icon="bolt" style={{ flex: 1 }}>Refresh all</Button>
        </div>
      </div>

      {/* Items */}
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, background: 'var(--bg-base)' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10, background: 'var(--bg-panel)' }}>
          <span className="display" style={{ fontSize: 14, color: 'var(--ink-strong)' }}>{SAMPLE_NEWS.length} fresh items</span>
          <Badge tone="cyan">{picked.size} selected</Badge>
          <div style={{ flex: 1 }} />
          <Input icon="search" placeholder="Filter items…" style={{ width: 200 }} value="" onChange={()=>{}} />
          <Select value="recent" options={[{value:'recent',label:'Most recent'},{value:'relevance',label:'By relevance'}]} onChange={()=>{}} style={{ width: 140 }} />
        </div>
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {SAMPLE_NEWS.map(item => {
            const sel = picked.has(item.id);
            return (
              <div key={item.id} onClick={() => toggle(item.id)} style={{
                display: 'grid', gridTemplateColumns: 'auto 88px 1fr auto', gap: 14, padding: 12,
                background: sel ? 'var(--cyan-soft)' : 'var(--bg-panel)',
                border: `1px solid ${sel ? 'var(--cyan)' : 'var(--stroke)'}`,
                borderRadius: 'var(--r)',
                cursor: 'pointer',
                transition: 'all var(--dur-1) var(--ease)',
              }}>
                <div style={{
                  width: 18, height: 18, borderRadius: 4,
                  background: sel ? 'var(--cyan)' : 'transparent',
                  border: `1.5px solid ${sel ? 'var(--cyan)' : 'var(--ink-muted)'}`,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginTop: 2,
                }}>
                  {sel && <Icon name="check" size={12} style={{ color: '#02060d' }} />}
                </div>
                <Thumb kind="image" size={70} ratio={9/16 * 1.6} style={{ width: 88, height: 88 }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'var(--ink-strong)', fontWeight: 500, marginBottom: 4 }}>{item.title}</div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', fontSize: 11, color: 'var(--ink-soft)', marginBottom: 6 }}>
                    <span className="mono">{item.source}</span><span>·</span><span>{item.age} ago</span>
                    {item.tags.map(t => <Badge key={t}>{t}</Badge>)}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--violet)', fontStyle: 'italic' }}>
                    <Icon name="sparkle" size={11} /> {item.essence}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  <IconButton name="link" />
                  <IconButton name="more" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Compose pane */}
      <div style={{ background: 'var(--bg-panel)', borderLeft: '1px solid var(--stroke)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
          <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Compose</div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-soft)' }}>{picked.size} item{picked.size === 1 ? '' : 's'} selected</div>
        </div>
        <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
          <InspectorSection label="Script">
            <Field label="Voice"><Select value="prophet" options={[{value:'prophet',label:'Prophet (deep, slow)'},{value:'oracle',label:'Oracle (smooth)'},{value:'seer',label:'Seer (intense)'}]} onChange={()=>{}} /></Field>
            <Field label="Length"><Slider value={80} min={40} max={140} step={10} unit=" words" onChange={()=>{}} /></Field>
            <Field><Toggle checked label="Use Anthropic summarizer" onChange={()=>{}} /></Field>
          </InspectorSection>
          <InspectorSection label="Illustration">
            <Field label="Style"><Select value="deep-sea" options={['deep-sea','cinematic','glitch','documentary']} onChange={()=>{}} /></Field>
            <Field><Slider label="Duration" value={15} min={5} max={30} step={5} unit="s" onChange={()=>{}} /></Field>
          </InspectorSection>
          <InspectorSection label="Advanced" defaultOpen={false}>
            <Field><Slider label="Tail pad" value={0.4} min={0} max={2} step={0.1} unit="s" onChange={()=>{}} /></Field>
            <Field><Toggle checked label="Reader fallback (scrape on miss)" onChange={()=>{}} /></Field>
          </InspectorSection>
        </div>
        <div style={{ padding: 14, borderTop: '1px solid var(--stroke)', display: 'grid', gap: 8 }}>
          <Button variant="violet" size="md" icon="flow">Send to Studio</Button>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <Button variant="outline" size="sm" icon="mic">Script</Button>
            <Button variant="outline" size="sm" icon="film">Illustration</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────── Templates ────────────────────── */
function TemplatesScreen({ variant }) {
  const [picked, setPicked] = useStateScr('tpl_news_reel');
  const [liveTpls, setLiveTpls] = useStateScr([]);
  const [refreshTick, setRefreshTick] = useStateScr(0);
  useEffect(() => {
    let alive = true;
    api.listLayoutTemplates().then(res => {
      if (!alive) return;
      // Backend returns { templates: [...] }; tolerate a bare array too.
      const arr = Array.isArray(res) ? res : (res?.templates || []);
      const list = arr.map(t => ({
        id: t.id,
        name: t.name || t.id,
        tags: [
          ...(t.metadata?.tags || []),
          t.canvas ? `${t.canvas.width}×${t.canvas.height}` : (t.metadata?.format || ''),
        ].filter(Boolean),
        builtIn: !!t.builtIn || (t.id || '').startsWith('tpl_'),
        // Keep the real layout so thumbnails reflect each template's regions.
        regions: t.regions || [],
        canvas: t.canvas || null,
      }));
      setLiveTpls(list);
    });
    return () => { alive = false; };
  }, [refreshTick]);

  async function newTemplate() {
    // Build a minimal valid layout-template: 1080×1920 canvas with two
    // editable regions (a primary video slot + a brand strip footer).
    const id = 'tpl_custom_' + Math.random().toString(36).slice(2, 8);
    const draft = {
      id,
      name: 'Untitled layout',
      description: 'Custom layout — edit regions in the visual editor on the right.',
      version: 1,
      canvas: { width: 1080, height: 1920, background_color: '#02060d', fps: 30, duration_s: 8 },
      regions: [
        {
          id: 'r_main', type: 'video_slot',
          x: 0, y: 0, width: 1080, height: 1700,
          z_index: 0,
          slot_name: 'main', slot_label: 'Main clip',
          default_provider: 'seedance', fit: 'cover', audio_volume: 1.0,
        },
        {
          id: 'r_brand', type: 'brand_strip',
          x: 0, y: 1760, width: 1080, height: 160,
          z_index: 1, background_color: '#02060d',
          items: [
            { type: 'text', text: '$DEEPOTUS', x: 40, y: 60, font: 'JetBrains Mono', size: 36, color: '#ef4444', weight: 700 },
          ],
        },
      ],
      audio: { master_track: 'from_slot:main', tail_pad_s: 0.4, fade_in_s: 0.2, fade_out_s: 0.4 },
      metadata: { tags: ['custom'], target_platforms: ['x','instagram_reels'] },
    };
    try {
      const r = await fetch('/api/layout-templates', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: draft }),
      });
      if (!r.ok) {
        alert('Create failed: ' + await r.text());
        return;
      }
      // Refresh the list and select the new template.
      setRefreshTick(t => t + 1);
      setTimeout(() => setPicked(id), 200);
    } catch (e) {
      alert('Create failed: ' + e);
    }
  }
  const templates = liveTpls.length > 0 ? liveTpls : SAMPLE_TEMPLATES;
  const pickedT = templates.find(t => t.id === picked) || templates[0];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', height: '100%', minHeight: 0 }}>
      <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', gap: 10, background: 'var(--bg-panel)' }}>
          <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Templates</div>
          <Badge>{templates.length}</Badge>
          <div style={{ flex: 1 }} />
          <Input icon="search" placeholder="Search…" style={{ width: 220 }} value="" onChange={()=>{}} />
          <Button variant="primary" size="sm" icon="plus" glow onClick={newTemplate}>New template</Button>
        </div>
        <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
            {templates.map(t => {
              const sel = picked === t.id;
              return (
                <div key={t.id} onClick={() => setPicked(t.id)} style={{
                  background: 'var(--bg-panel)',
                  border: `1px solid ${sel ? 'var(--cyan)' : 'var(--stroke)'}`,
                  borderRadius: 'var(--r-lg)', overflow: 'hidden', cursor: 'pointer',
                  boxShadow: sel ? '0 0 24px var(--cyan-soft)' : 'var(--shadow-1)',
                  transition: 'all var(--dur-2) var(--ease)',
                }}>
                  <TemplateThumb id={t.id} regions={t.regions} canvas={t.canvas} />
                  <div style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: 'var(--ink-strong)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {t.builtIn && <span title="Built-in" style={{ color: 'var(--ink-soft)' }}>🔒</span>}
                        {t.name}
                      </div>
                      <div style={{ fontSize: 10.5, color: 'var(--ink-soft)', display: 'flex', gap: 4 }}>
                        {t.tags.map(x => <span key={x}>· {x}</span>)}
                      </div>
                    </div>
                    <IconButton name="more" size={24} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Right: spatial editor preview — fully interactive */}
      <TemplateRegionEditor pickedT={pickedT} onSaved={() => setRefreshTick(t => t + 1)} />
    </div>
  );
}

/* Interactive template editor — drag region body to move, drag corner/edge
   handles to resize. Hydrates from /api/layout-templates/{id} and shows
   the real regions (reel/avatar/brand/separator etc.) over a 9:16 canvas. */
function TemplateRegionEditor({ pickedT, onSaved }) {
  const CANVAS_W = 1080;
  const PREVIEW_W = 240;
  const scale = PREVIEW_W / CANVAS_W;
  const stageRef = React.useRef(null);

  const [tpl, setTpl] = useStateScr(null);
  const [regions, setRegions] = useStateScr([]);
  const [selId, setSelId] = useStateScr(null);
  const [saveMsg, setSaveMsg] = useStateScr('');

  useEffect(() => {
    if (!pickedT?.id) return;
    let alive = true;
    fetch(`/api/layout-templates/${pickedT.id}`)
      .then(r => r.ok ? r.json() : null)
      .then(j => {
        if (!alive || !j) return;
        setTpl(j);
        const rs = (j.regions || []).map(r => ({
          id: r.id,
          type: r.type,
          slot_name: r.slot_name || r.id,
          x: r.x || 0, y: r.y || 0,
          width: r.width || 200, height: r.height || 200,
          color: r.type === 'video_slot' && r.slot_name === 'avatar' ? 'var(--violet)'
               : r.type === 'video_slot' ? 'var(--cyan)'
               : r.type === 'brand_strip' ? 'var(--amber)'
               : r.type === 'separator'   ? 'var(--green)'
               : r.type === 'image_slot'  ? 'var(--amber)'
               : 'var(--ink-soft)',
        }));
        setRegions(rs);
        if (rs.length) setSelId(rs[0].id);
      });
    return () => { alive = false; };
  }, [pickedT?.id]);

  const ch = tpl?.canvas?.height || 1920;
  const cw = tpl?.canvas?.width || 1080;
  const previewH = PREVIEW_W * ch / cw;
  const sel = regions.find(r => r.id === selId);

  function patch(id, p) { setRegions(rs => rs.map(r => r.id === id ? { ...r, ...p } : r)); }

  // mouse-driven drag (move + 8 resize handles). Returns mousemove handler
  // that updates the region in real-time, clamping to canvas bounds.
  function startDrag(e, id, mode) {
    e.stopPropagation();
    e.preventDefault();
    const reg = regions.find(r => r.id === id);
    if (!reg) return;
    const stage = stageRef.current.getBoundingClientRect();
    const start = { x0: reg.x, y0: reg.y, w0: reg.width, h0: reg.height,
                    mx: e.clientX, my: e.clientY };
    function onMove(ev) {
      const dxPx = ev.clientX - start.mx;
      const dyPx = ev.clientY - start.my;
      const dx = dxPx / scale;
      const dy = dyPx / scale;
      let { x0, y0, w0, h0 } = start;
      let nx = x0, ny = y0, nw = w0, nh = h0;
      if (mode === 'move') { nx = x0 + dx; ny = y0 + dy; }
      if (mode.includes('e')) nw = Math.max(20, w0 + dx);
      if (mode.includes('s')) nh = Math.max(20, h0 + dy);
      if (mode.includes('w')) { nw = Math.max(20, w0 - dx); nx = x0 + (w0 - nw); }
      if (mode.includes('n')) { nh = Math.max(20, h0 - dy); ny = y0 + (h0 - nh); }
      // Clamp to canvas.
      nx = Math.max(0, Math.min(cw - nw, nx));
      ny = Math.max(0, Math.min(ch - nh, ny));
      nw = Math.max(20, Math.min(cw - nx, nw));
      nh = Math.max(20, Math.min(ch - ny, nh));
      patch(id, { x: Math.round(nx), y: Math.round(ny), width: Math.round(nw), height: Math.round(nh) });
    }
    function onUp() {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  async function save() {
    if (!tpl) return;
    const merged = { ...tpl, regions: tpl.regions.map(r => {
      const ed = regions.find(x => x.id === r.id);
      return ed ? { ...r, x: ed.x, y: ed.y, width: ed.width, height: ed.height } : r;
    }) };
    try {
      const r = await fetch('/api/layout-templates', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: merged }),
      });
      if (r.ok) {
        setSaveMsg('Saved ✓');
        onSaved?.();                       // refresh the gallery list immediately
        setTimeout(() => setSaveMsg(''), 3000);
      } else {
        setSaveMsg('Save failed: ' + (await r.text()).slice(0, 120));
      }
    } catch (e) { setSaveMsg('Save failed: ' + String(e).slice(0, 120)); }
  }

  function openInStudio() {
    // Hand off to the node editor (Studio view). The studio builds renders
    // from a node graph; we navigate there with the template id as context.
    window.dispatchEvent(new CustomEvent('deepotus:navigate', { detail: { view: 'studio', templateId: pickedT?.id } }));
  }

  return (
    <div style={{ background: 'var(--bg-panel)', borderLeft: '1px solid var(--stroke)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--stroke)' }}>
        <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>{pickedT?.name || '—'}</div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-soft)' }}>Spatial editor · {cw} × {ch} · drag regions or their handles</div>
      </div>
      <div style={{ padding: 18, display: 'flex', justifyContent: 'center' }}>
        <div ref={stageRef} onMouseDown={() => setSelId(null)} style={{
          width: PREVIEW_W, height: previewH,
          background: tpl?.canvas?.background_color || '#02060d',
          border: '1px solid var(--stroke-strong)', borderRadius: 8,
          position: 'relative', overflow: 'hidden', userSelect: 'none',
        }}>
          {/* Grid overlay */}
          <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(0deg, transparent 0 19px, var(--stroke) 19px 20px), repeating-linear-gradient(90deg, transparent 0 19px, var(--stroke) 19px 20px)', opacity: 0.4, pointerEvents: 'none' }} />
          {regions.map(r => {
            const selected = r.id === selId;
            const sx = r.x * scale, sy = r.y * scale, sw = r.width * scale, sh = r.height * scale;
            return (
              <div key={r.id}
                onMouseDown={(e) => { setSelId(r.id); startDrag(e, r.id, 'move'); }}
                style={{
                  position: 'absolute', left: sx, top: sy, width: sw, height: sh,
                  background: selected ? `${r.color}33` : `${r.color}22`,
                  border: `${selected ? 2 : 1}px solid ${r.color}`,
                  borderRadius: 3, boxSizing: 'border-box', cursor: 'move',
                  boxShadow: selected ? `0 0 16px ${r.color}66` : 'none',
                }}>
                <div style={{ padding: '2px 4px', fontSize: 9, fontFamily: 'var(--f-mono)', color: r.color, pointerEvents: 'none' }}>{r.slot_name || r.type}</div>
                {selected && ['nw','n','ne','w','e','sw','s','se'].map(dir => {
                  const styles = {
                    nw: { top: -4, left: -4, cursor: 'nwse-resize' },
                    n:  { top: -4, left: '50%', marginLeft: -4, cursor: 'ns-resize' },
                    ne: { top: -4, right: -4, cursor: 'nesw-resize' },
                    w:  { top: '50%', left: -4, marginTop: -4, cursor: 'ew-resize' },
                    e:  { top: '50%', right: -4, marginTop: -4, cursor: 'ew-resize' },
                    sw: { bottom: -4, left: -4, cursor: 'nesw-resize' },
                    s:  { bottom: -4, left: '50%', marginLeft: -4, cursor: 'ns-resize' },
                    se: { bottom: -4, right: -4, cursor: 'nwse-resize' },
                  }[dir];
                  return (
                    <div key={dir}
                      onMouseDown={(e) => startDrag(e, r.id, dir)}
                      style={{
                        position: 'absolute', width: 8, height: 8,
                        background: r.color, border: '1px solid #02060d', borderRadius: 1, ...styles,
                      }} />
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
      <div className="scroll" style={{ flex: 1, overflowY: 'auto' }}>
        <InspectorSection label={sel ? `Region · ${sel.slot_name || sel.type}` : 'No region selected'}>
          {sel ? (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <Field label="x"><Input mono value={String(sel.x)} onChange={(v) => patch(sel.id, { x: Math.max(0, Math.min(cw - sel.width, Number(v) || 0)) })} /></Field>
                <Field label="y"><Input mono value={String(sel.y)} onChange={(v) => patch(sel.id, { y: Math.max(0, Math.min(ch - sel.height, Number(v) || 0)) })} /></Field>
                <Field label="w"><Input mono value={String(sel.width)}  onChange={(v) => patch(sel.id, { width:  Math.max(20, Math.min(cw - sel.x, Number(v) || 20)) })} /></Field>
                <Field label="h"><Input mono value={String(sel.height)} onChange={(v) => patch(sel.id, { height: Math.max(20, Math.min(ch - sel.y, Number(v) || 20)) })} /></Field>
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-soft)', marginTop: 6 }}>
                Type: <span className="mono">{sel.type}</span>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 11.5, color: 'var(--ink-soft)' }}>Click a region in the preview to edit. Drag the body to move, the dots to resize.</div>
          )}
        </InspectorSection>
      </div>
      <div style={{ padding: 12, borderTop: '1px solid var(--stroke)', display: 'grid', gap: 8 }}>
        {saveMsg && <div style={{ fontSize: 10.5, color: saveMsg.startsWith('Save failed') ? 'var(--red)' : 'var(--green)' }}>{saveMsg}</div>}
        <Button variant="primary" size="md" icon="check" glow onClick={save} disabled={!tpl}>Save layout</Button>
        <Button variant="outline" size="sm" icon="flow" onClick={openInStudio} disabled={!pickedT}>Open in Studio</Button>
      </div>
    </div>
  );
}

function Region({ x, y, w, h, color, label }) {
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width: w, height: h,
      background: color + '12', border: `1px solid ${color}`, borderRadius: 4,
    }}>
      <div style={{ position: 'absolute', top: -3, left: -3, width: 6, height: 6, background: color, borderRadius: 1 }} />
      <div style={{ position: 'absolute', top: -3, right: -3, width: 6, height: 6, background: color, borderRadius: 1 }} />
      <div style={{ position: 'absolute', bottom: -3, left: -3, width: 6, height: 6, background: color, borderRadius: 1 }} />
      <div style={{ position: 'absolute', bottom: -3, right: -3, width: 6, height: 6, background: color, borderRadius: 1 }} />
      <div style={{ padding: '2px 4px', fontSize: 9, fontFamily: 'var(--f-mono)', color }}>{label}</div>
    </div>
  );
}

// Color a region by its kind (matches the spatial editor palette).
function _regionColor(r) {
  if (r.type === 'video_slot') return (r.slot_name === 'avatar' || /avatar|heygen/i.test(r.slot_label || r.slot_name || '')) ? 'var(--violet)' : 'var(--cyan)';
  if (r.type === 'brand_strip') return 'var(--amber)';
  if (r.type === 'separator')   return 'var(--green)';
  if (r.type === 'image_slot')  return 'var(--amber)';
  return 'var(--ink-soft)';
}

function TemplateThumb({ id, regions, canvas }) {
  // Preferred: render the template's REAL regions so every card is distinct.
  if (regions && regions.length && canvas) {
    const cw = canvas.width || 1080, ch = canvas.height || 1920;
    return (
      <div style={{ aspectRatio: `${cw} / ${ch}`, background: canvas.background_color || '#02060d', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg, transparent 0 8px, #00e5ff08 8px 9px)' }} />
        {regions.map((r, i) => {
          const c = _regionColor(r);
          return (
            <div key={r.id || i} style={{
              position: 'absolute',
              left: `${(r.x / cw) * 100}%`, top: `${(r.y / ch) * 100}%`,
              width: `${(r.width / cw) * 100}%`, height: `${(r.height / ch) * 100}%`,
              background: `${c}22`, border: `1px solid ${c}`, borderRadius: 3, boxSizing: 'border-box',
            }}>
              <div style={{ fontFamily: 'var(--f-mono)', fontSize: 8, padding: '1px 3px', color: c, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.slot_name || r.type}</div>
            </div>
          );
        })}
      </div>
    );
  }
  // Fallback (only when the backend list is empty → SAMPLE_TEMPLATES).
  const layouts = {
    tpl_news_reel: { reel: [4,4,72,52], avatar: [44,58,32,30], brand: [4,90,46,7] },
    tpl_split_lower: { reel: [4,4,72,60], avatar: [4,68,72,28] },
    tpl_avatar_pip:  { reel: [4,4,72,92], avatar: [52,72,22,22] },
    tpl_full_avatar: { avatar: [4,4,72,82], brand: [4,90,72,7] },
    tpl_grid_3:      { a: [4,4,34,46], b: [42,4,34,46], c: [22,54,34,42] },
    tpl_oracle_lab:  { reel: [4,4,72,46], avatar: [4,54,34,42], brand: [42,54,34,42] },
  };
  const layout = layouts[id] || layouts.tpl_news_reel;
  return (
    <div style={{ aspectRatio: '9 / 16', background: '#02060d', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(45deg, transparent 0 8px, #00e5ff08 8px 9px)' }} />
      {Object.entries(layout).map(([k, [x, y, w, h]]) => (
        <div key={k} style={{
          position: 'absolute', left: x + '%', top: y + '%', width: w + '%', height: h + '%',
          background: k === 'avatar' ? '#2a0d3e' : k === 'brand' ? 'var(--amber-soft)' : '#053040',
          border: `1px solid ${k === 'avatar' ? 'var(--violet)' : k === 'brand' ? 'var(--amber)' : 'var(--cyan)'}`,
          borderRadius: 3,
        }}>
          <div style={{ fontFamily: 'var(--f-mono)', fontSize: 8, padding: '1px 3px', color: k === 'avatar' ? 'var(--violet)' : k === 'brand' ? 'var(--amber)' : 'var(--cyan)' }}>{k}</div>
        </div>
      ))}
    </div>
  );
}

/* ────────────────────── Library ────────────────────── */
function LibraryScreen({ variant, uploads = [], setUploads = () => {} }) {
  const [tab, setTab] = useStateScr('Images');
  const [drag, setDrag] = useStateScr(false);
  const [liveImages, setLiveImages] = useStateScr([]);
  const [liveJobs, setLiveJobs] = useStateScr([]);
  const [preview, setPreview] = useStateScr(null); // { url, name, kind, jobId }
  const [genPrompt, setGenPrompt] = useStateScr('');
  const [genBusy, setGenBusy] = useStateScr(false);
  const [genMsg, setGenMsg] = useStateScr('');
  const [genGenOpen, setGenGenOpen] = useStateScr(false); // prompt manager modal
  const fileRef = React.useRef(null);
  const vidRef = React.useRef(null);
  const [vidBusy, setVidBusy] = useStateScr(false);

  // Upload a user video (UGC). It registers as a finished render → shows in the
  // Renders tab, attachable to posts, and usable as a Studio "UGC video" / its
  // duration as a composition master.
  async function uploadVideoFile(f) {
    if (!f) return;
    setVidBusy(true);
    const r = await api.uploadVideo(f);
    setVidBusy(false);
    if (r?.ok) { setTab('Renders'); }
    else alert('Video upload failed: ' + String(r?.error || 'unknown'));
  }

  async function generateImages() {
    const p = genPrompt.trim();
    if (!p || genBusy) return;
    setGenBusy(true); setGenMsg('');
    const r = await api.generateImage(p, 1, 'portrait_16_9');
    setGenBusy(false);
    if (r?.images?.length) {
      setGenMsg(`${r.images.length} image saved to Library.`);
      setGenPrompt('');
      // Surface immediately without waiting for the 8s poll.
      setUploads(u => [
        ...r.images.map(f => ({
          name: f, kind: 'image', size: '', date: 'just now',
          url: api.imageUrl(f), uploaded: true,
        })), ...u,
      ]);
      setTimeout(() => setGenMsg(''), 4000);
    } else {
      setGenMsg('Failed: ' + String(r?.error || 'generation error').slice(0, 140));
    }
  }

  // Hydrate from backend: assets/images and the job queue (renders + audio).
  useEffect(() => {
    let alive = true;
    async function refresh() {
      const [imgRes, jobs] = await Promise.all([api.listImages(), api.listJobs(80)]);
      if (!alive) return;
      const imgs = (imgRes?.images || []).map(im => ({
        name: im.filename,
        kind: 'image',
        size: fmtSize(im.size),
        date: fmtAgo(im.modified) || 'on disk',
        url: api.imageUrl(im.filename),
      }));
      setLiveImages(imgs);
      setLiveJobs(jobs || []);
    }
    refresh();
    const t = setInterval(refresh, 8000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // Real renders from /api/jobs (done + has final video).
  const realRenders = liveJobs
    .filter(j => j.status === 'done' && j.final_video_path)
    .map(j => ({
      name: j.title || `${j.provider || 'render'}_${(j.job_id || '').slice(0, 6)}.mp4`,
      kind: 'render',
      size: '',
      date: fmtAgo(j.created_at),
      dur: j.duration_s ? fmtDur(j.duration_s) : '',
      provider: (j.provider || '').replace(/^./, c => c.toUpperCase()),
      url: api.jobVideoUrl(j.job_id),
      jobId: j.job_id,
    }));
  // Audio jobs (HeyGen / ElevenLabs voiceover) if they ship audio_path.
  const realAudio = liveJobs
    .filter(j => j.audio_path)
    .map(j => ({
      name: (j.title || 'voice') + '.wav',
      kind: 'audio',
      size: '',
      date: fmtAgo(j.created_at),
      dur: j.duration_s ? fmtDur(j.duration_s) : '',
      jobId: j.job_id,
    }));
  // Captions from done jobs.
  const realCaptions = liveJobs
    .filter(j => j.caption_text)
    .map(j => ({
      name: (j.title || 'caption_' + (j.job_id || '').slice(0,6)) + '.srt',
      kind: 'text',
      size: '',
      date: fmtAgo(j.created_at),
      dur: (j.caption_text || '').split('\n').length + ' lines',
      jobId: j.job_id,
    }));

  function handleFiles(fileList) {
    const arr = Array.from(fileList || []);
    const imgs = arr.filter(f => f.type.startsWith('image/'));
    if (!imgs.length) return;
    // Upload to backend so the image becomes available in Studio/Quick.
    imgs.forEach(async (f) => {
      const fd = new FormData();
      fd.append('file', f);
      try {
        const r = await fetch('/api/images/upload', { method: 'POST', body: fd });
        if (r.ok) {
          const j = await r.json();
          setUploads(u => [{
            name: j.filename || f.name,
            kind: 'image',
            size: fmtSize(f.size),
            date: 'just now',
            url: api.imageUrl(j.filename || f.name),
            uploaded: true,
          }, ...u]);
        } else {
          // Backend rejected: keep the local preview so the user sees something.
          setUploads(u => [{
            name: f.name, kind: 'image', size: fmtSize(f.size),
            date: 'just now (local)', url: URL.createObjectURL(f), uploaded: true,
          }, ...u]);
        }
      } catch {
        setUploads(u => [{
          name: f.name, kind: 'image', size: fmtSize(f.size),
          date: 'just now (local)', url: URL.createObjectURL(f), uploaded: true,
        }, ...u]);
      }
    });
    setTab('Images');
  }

  function onDrop(e) {
    e.preventDefault(); e.stopPropagation();
    setDrag(false);
    if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
  }
  function onDragOver(e) { e.preventDefault(); e.stopPropagation(); setDrag(true); }
  function onDragLeave(e) { e.preventDefault(); e.stopPropagation(); if (e.target === e.currentTarget) setDrag(false); }

  // Compose item list per tab: live backend data + uploads. Fall back to
  // SAMPLE_LIBRARY for tabs the backend doesn't surface (e.g. Audio/Captions
  // before any job produces them).
  const liveByTab = {
    Images:   [...uploads, ...liveImages],
    Renders:  realRenders,
    Audio:    realAudio,
    Captions: realCaptions,
  };
  const live = liveByTab[tab] || [];
  const items = live.length > 0 ? live : SAMPLE_LIBRARY[tab];
  const totalCount = (liveByTab[tab] || []).length || SAMPLE_LIBRARY[tab].length;

  return (
    <div onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
      style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, background: 'var(--bg-base)', position: 'relative' }}
    >
      <input ref={fileRef} type="file" accept="image/*" multiple style={{ display: 'none' }}
        onChange={e => { handleFiles(e.target.files); e.target.value = ''; }} />
      <input ref={vidRef} type="file" accept="video/*" style={{ display: 'none' }}
        onChange={e => { uploadVideoFile(e.target.files?.[0]); e.target.value = ''; }} />

      <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--stroke)', background: 'var(--bg-panel)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)' }}>Library</div>
          <div style={{ display: 'flex', gap: 2, padding: 3, background: 'var(--bg-base)', borderRadius: 'var(--r-sm)', border: '1px solid var(--stroke)' }}>
            {Object.keys(SAMPLE_LIBRARY).map(t => {
              const liveCount = (liveByTab[t] || []).length;
              const count = liveCount > 0 ? liveCount : SAMPLE_LIBRARY[t].length;
              return (
                <button key={t} onClick={() => setTab(t)} style={{
                  height: 26, padding: '0 10px',
                  background: tab === t ? 'var(--bg-panel-2)' : 'transparent',
                  border: 0, borderRadius: 4, cursor: 'pointer',
                  color: tab === t ? 'var(--ink-strong)' : 'var(--ink-soft)',
                  fontSize: 11.5, fontWeight: 500,
                }}>{t} <span style={{ color: 'var(--ink-muted)', fontSize: 10 }}>{count}</span></button>
              );
            })}
          </div>
          <div style={{ flex: 1 }} />
          <Input icon="search" placeholder="Search assets…" value="" onChange={()=>{}} style={{ width: 240 }} />
          <Select value="recent" options={[{value:'recent',label:'Most recent'},{value:'name',label:'Name'},{value:'size',label:'Size'}]} onChange={()=>{}} style={{ width: 130 }} />
          <Button variant="outline" size="sm" icon="film" onClick={() => vidRef.current?.click()} disabled={vidBusy} title="Upload your own video (UGC) — appears in Renders, usable in Studio as a duration master">
            {vidBusy ? 'Uploading…' : 'Upload video'}
          </Button>
          <Button variant="primary" size="sm" icon="upload" glow onClick={() => fileRef.current?.click()}>Upload image</Button>
        </div>
      </div>

      <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
        {/* Always-visible upload chip when on Images */}
        {tab === 'Images' && (
          <div onClick={() => fileRef.current?.click()} style={{
            display: 'flex', alignItems: 'center', gap: 12, padding: 14, marginBottom: 14,
            background: drag ? 'var(--brand-soft)' : 'var(--bg-panel)',
            border: `1px dashed ${drag ? 'var(--brand)' : 'var(--stroke-strong)'}`,
            borderRadius: 'var(--r)', cursor: 'pointer',
            transition: 'all var(--dur-1) var(--ease)',
            boxShadow: drag ? '0 0 18px var(--brand-soft)' : 'none',
          }}>
            <Icon name="upload" size={20} style={{ color: drag ? 'var(--brand)' : 'var(--ink-soft)' }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: 'var(--ink-strong)' }}>{drag ? 'Drop to upload' : 'Drag images here or click to browse'}</div>
              <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>PNG · JPG · WEBP up to 16 MB. Stored locally; available immediately in Studio.</div>
            </div>
            {uploads.length > 0 && <Badge tone="green" dot>{uploads.length} uploaded this session</Badge>}
          </div>
        )}

        {/* Create an image with FLUX (same FAL key as Seedance) */}
        {tab === 'Images' && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: 12, marginBottom: 14,
            background: 'var(--bg-panel)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)',
          }}>
            <Icon name="sparkle" size={18} style={{ color: 'var(--cyan)' }} />
            <input
              value={genPrompt}
              onChange={e => setGenPrompt(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && generateImages()}
              placeholder="Describe an image to create (FLUX, ~3s, uses your fal.ai key)…"
              style={{
                flex: 1, height: 32, padding: '0 10px',
                background: 'var(--bg-base)', border: '1px solid var(--stroke)',
                borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)',
                fontFamily: 'var(--f-ui)', fontSize: 12.5,
              }} />
            <Button variant="outline" size="sm" icon="zap" onClick={() => setGenGenOpen(true)} title="Build a prompt with the prompt manager (overwrites the field)">
              Prompt manager
            </Button>
            <Button variant="primary" size="sm" icon="sparkle" glow onClick={generateImages} disabled={genBusy || !genPrompt.trim()}>
              {genBusy ? 'Creating…' : 'Create image'}
            </Button>
            {genMsg && (
              <span style={{ fontSize: 11, color: genMsg.startsWith('Failed') ? 'var(--red)' : 'var(--green)' }}>{genMsg}</span>
            )}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }}>
          {items.map((it, i) => (
            <div key={i} onClick={() => it.url && setPreview(it)} style={{
              background: 'var(--bg-panel)', border: `1px solid ${it.uploaded ? 'var(--brand)' : 'var(--stroke)'}`,
              borderRadius: 'var(--r)', overflow: 'hidden',
              transition: 'all var(--dur-1) var(--ease)', cursor: it.url ? 'pointer' : 'default',
              boxShadow: it.uploaded ? '0 0 18px var(--brand-soft)' : 'none',
            }}
            onMouseEnter={e => { if (!it.uploaded) { e.currentTarget.style.borderColor = 'var(--cyan)'; e.currentTarget.style.boxShadow = '0 0 18px var(--cyan-soft)'; } }}
            onMouseLeave={e => { if (!it.uploaded) { e.currentTarget.style.borderColor = 'var(--stroke)'; e.currentTarget.style.boxShadow = 'none'; } }}
            >
              {it.url && it.kind === 'render' ? (
                <div style={{ width: '100%', height: 120, background: '#02060d', position: 'relative', overflow: 'hidden' }}>
                  <video src={it.url} muted preload="metadata" playsInline
                    onMouseEnter={e => e.currentTarget.play().catch(() => {})}
                    onMouseLeave={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                  <div style={{ position: 'absolute', bottom: 4, right: 4, padding: '2px 5px', fontSize: 9, fontWeight: 600, fontFamily: 'var(--f-mono)', color: 'var(--cyan)', background: '#02060daa', borderRadius: 3 }}>▶ hover</div>
                </div>
              ) : it.url && it.kind === 'image' ? (
                <div style={{ width: '100%', height: 120, background: '#02060d', position: 'relative', overflow: 'hidden' }}>
                  <img src={it.url} alt={it.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                  {it.uploaded && <div style={{ position: 'absolute', top: 4, left: 4, padding: '2px 5px', fontSize: 9, fontWeight: 600, fontFamily: 'var(--f-mono)', color: 'var(--brand)', background: '#02060daa', borderRadius: 3, letterSpacing: 0.5 }}>NEW</div>}
                </div>
              ) : (
                <Thumb kind={it.kind} size={1} style={{ width: '100%', height: 120, borderRadius: 0, border: 0 }} />
              )}
              <div style={{ padding: '8px 10px' }}>
                <div style={{ fontSize: 11.5, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.name}</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4, fontSize: 10, color: 'var(--ink-soft)' }}>
                  <span>{it.date}</span>
                  <span className="mono">{it.dur || it.size}</span>
                </div>
                {it.provider && <div style={{ fontSize: 10, color: 'var(--violet)', marginTop: 2 }}>{it.provider}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Preview modal — clicked render plays at full size, clicked image shows full-res */}
      {preview && (
        <div onClick={() => setPreview(null)} style={{
          position: 'absolute', inset: 0, zIndex: 60,
          background: 'var(--bg-overlay)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            maxWidth: '90%', maxHeight: '92%',
            background: 'var(--bg-panel-2)', border: '1px solid var(--stroke-strong)',
            borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-2), 0 0 80px var(--cyan-soft)',
            padding: 18, display: 'flex', flexDirection: 'column', gap: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Icon name={preview.kind === 'render' ? 'film' : 'image'} size={16} style={{ color: 'var(--cyan)' }} />
              <span style={{ fontSize: 13, color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)' }}>{preview.name}</span>
              {preview.provider && <Badge tone="violet">{preview.provider}</Badge>}
              <div style={{ flex: 1 }} />
              <a href={preview.url} download={preview.name} style={{ textDecoration: 'none' }}><Button variant="outline" size="sm" icon="download">Download</Button></a>
              {preview.jobId && (
                <Button variant="ghost" size="sm" icon="trash" onClick={async () => {
                  if (!confirm('Delete this render and its files?')) return;
                  await api.deleteJob(preview.jobId);
                  setPreview(null);
                }}>Delete</Button>
              )}
              <IconButton name="close" onClick={() => setPreview(null)} />
            </div>
            {preview.kind === 'render' ? (
              <video src={preview.url} controls autoPlay style={{ maxWidth: '70vw', maxHeight: '70vh', borderRadius: 'var(--r)', background: '#000' }} />
            ) : (
              <img src={preview.url} alt={preview.name} style={{ maxWidth: '70vw', maxHeight: '70vh', borderRadius: 'var(--r)' }} />
            )}
          </div>
        </div>
      )}

      {/* Drop scrim while dragging anywhere on the screen */}
      {drag && (
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          background: 'var(--brand-soft)',
          border: '2px dashed var(--brand)',
          borderRadius: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 10,
        }}>
          <div style={{ padding: '14px 22px', background: 'var(--bg-panel-2)', border: '1px solid var(--brand)', borderRadius: 'var(--r-lg)', boxShadow: '0 0 32px var(--brand-soft)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Icon name="upload" size={22} style={{ color: 'var(--brand)' }} />
            <div>
              <div style={{ fontSize: 14, color: 'var(--ink-strong)' }}>Drop to add to Library</div>
              <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>Images will appear immediately.</div>
            </div>
          </div>
        </div>
      )}

      {/* Prompt manager for image generation — its output OVERWRITES the field. */}
      <PromptGeneratorModal open={genGenOpen} onClose={() => setGenGenOpen(false)} onUse={p => setGenPrompt(p)} initial={genPrompt} />
    </div>
  );
}

/* ────────────────────── Settings ────────────────────── */
const SETTINGS_SECTIONS = ['keys', 'accounts', 'personas', 'branding', 'pack', 'defaults', 'paths', 'news', 'appearance'];
function SettingsScreen({ variant, personas = [], activePersonaId, setActivePersonaId, savePersona }) {
  const [section, setSection] = useStateScr(() => {
    const s = urlParam('section');
    return SETTINGS_SECTIONS.includes(s) ? s : 'accounts';
  });
  const [personaModal, setPersonaModal] = useStateScr(null);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', height: '100%', minHeight: 0, background: 'var(--bg-base)' }}>
      <div style={{ background: 'var(--bg-panel)', borderRight: '1px solid var(--stroke)', padding: '14px 8px' }}>
        <div className="upper" style={{ padding: '0 10px 10px' }}>Settings</div>
        {[
          { k: 'keys',      l: 'API keys' },
          { k: 'accounts',  l: 'Connected accounts' },
          { k: 'personas',  l: 'Personas' },
          { k: 'branding',  l: 'Branding' },
          { k: 'pack',      l: 'Caption pack' },
          { k: 'defaults',  l: 'Provider defaults' },
          { k: 'paths',     l: 'Paths' },
          { k: 'news',      l: 'News' },
          { k: 'appearance',l: 'Appearance' },
        ].map(s => (
          <div key={s.k} onClick={() => setSection(s.k)} style={{
            padding: '8px 12px', borderRadius: 'var(--r-sm)', fontSize: 12.5,
            color: section === s.k ? 'var(--brand)' : 'var(--ink)',
            background: section === s.k ? 'var(--brand-soft)' : 'transparent',
            display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
            marginBottom: 2,
          }}>
            {s.l}
          </div>
        ))}
      </div>
      <div className="scroll" style={{ overflowY: 'auto', padding: 24, maxWidth: 880 }}>
        {section === 'accounts' && <ConnectedAccountsSection />}
        {section === 'personas' && (
          <PersonasSection personas={personas} activePersonaId={activePersonaId} setActivePersonaId={setActivePersonaId}
            onNew={() => setPersonaModal('new')}
            onEdit={(p) => setPersonaModal(p)}
          />
        )}
        {section === 'keys'       && <ApiKeysSection />}
        {section === 'branding'   && <BrandingSection />}
        {section === 'pack'       && <CaptionPackSection />}
        {section === 'defaults'   && <ProviderDefaultsSection />}
        {section === 'paths'      && <PathsSection />}
        {section === 'news'       && <NewsSettingsSection />}
        {section === 'appearance' && <AppearanceSection />}
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

// Editable Telegram Premium / caption pack — branded one-tap tags (emoji +
// label + optional custom icon) shown under the Scheduler caption editor.
function CaptionPackSection() {
  const [pack, setPack] = useStateScr(null);
  const [busy, setBusy] = useStateScr(false);
  const [msg, setMsg] = useStateScr('');
  const iconRefs = useRef({});
  useEffect(() => { api.getCaptionPack().then(r => setPack(r?.pack || [])); }, []);
  const inputStyle = { height: 30, padding: '0 8px', background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', color: 'var(--ink-strong)', fontFamily: 'var(--f-ui)', fontSize: 12.5, width: '100%' };
  function up(i, patch) { setPack(p => p.map((e, j) => j === i ? { ...e, ...patch } : e)); }
  function addRow() { setPack(p => [...(p || []), { id: 'tag-' + Math.random().toString(36).slice(2, 6), emoji: '🔥', label: 'New tag', icon: '' }]); }
  function removeRow(i) { setPack(p => p.filter((_, j) => j !== i)); }
  async function save() {
    setBusy(true); setMsg('');
    const clean = (pack || []).filter(e => (e.label || '').trim()).map(e => ({ ...e, icon: (e.icon || '').split('?')[0] }));
    const r = await api.saveCaptionPack(clean);
    setBusy(false);
    if (r?.pack) { setPack(r.pack); setMsg('Saved ✓ — open the Scheduler to use it.'); setTimeout(() => setMsg(''), 4000); }
    else setMsg('Save failed: ' + String(r?.error || ''));
  }
  async function reset() {
    if (!confirm('Reset the caption pack to the deepotus defaults? Custom icons are removed.')) return;
    const r = await api.resetCaptionPack();
    if (r?.pack) setPack(r.pack);
  }
  async function onIcon(i, file) {
    if (!file) return;
    const slot = pack[i].id || ('tag-' + i);
    setMsg('Uploading icon…');
    const r = await api.uploadPackIcon(slot, file);
    if (r?.ok && r.icon) { up(i, { id: slot, icon: r.icon + '?t=' + Date.now() }); setMsg('Icon set — click Save pack to keep it.'); }
    else setMsg('Icon upload failed: ' + String(r?.error || ''));
  }
  if (!pack) return <div style={{ color: 'var(--ink-soft)', fontSize: 12 }}>Loading…</div>;
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 4 }}>
        <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)' }}>Caption pack</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="ghost" size="sm" onClick={reset}>Reset</Button>
          <Button variant="primary" size="sm" icon="check" glow onClick={save} disabled={busy}>{busy ? 'Saving…' : 'Save pack'}</Button>
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 16, maxWidth: 640 }}>
        One-tap branded tags shown under the caption editor in the Scheduler (great for Telegram / X). Edit the emoji and label, upload a custom icon per tag, add or remove rows. {msg && <strong style={{ color: msg.includes('failed') ? 'var(--red)' : 'var(--green)' }}> · {msg}</strong>}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 640 }}>
        {pack.map((e, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '36px 56px 1fr auto auto', gap: 10, alignItems: 'center', padding: '8px 10px', background: 'var(--bg-panel)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)' }}>
            <div style={{ width: 32, height: 32, borderRadius: 6, background: 'var(--bg-base)', border: '1px solid var(--stroke)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
              {e.icon ? <img src={e.icon} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} onError={ev => { ev.currentTarget.style.display = 'none'; }} /> : <span style={{ fontSize: 16 }}>{e.emoji}</span>}
            </div>
            <input value={e.emoji} onChange={ev => up(i, { emoji: ev.target.value })} title="Fallback emoji" style={{ ...inputStyle, textAlign: 'center', fontSize: 15 }} />
            <input value={e.label} onChange={ev => up(i, { label: ev.target.value })} placeholder="Tag label" style={inputStyle} />
            <input ref={el => (iconRefs.current[i] = el)} type="file" accept="image/*" style={{ display: 'none' }} onChange={ev => { onIcon(i, ev.target.files?.[0]); ev.target.value = ''; }} />
            <Button variant="outline" size="sm" icon="upload" onClick={() => iconRefs.current[i]?.click()}>{e.icon ? 'Replace' : 'Icon'}</Button>
            <IconButton name="trash" title="Remove tag" onClick={() => removeRow(i)} />
          </div>
        ))}
      </div>
      <Button variant="outline" size="sm" icon="plus" onClick={addRow} style={{ marginTop: 10 }}>Add tag</Button>
    </>
  );
}

function PersonasSection({ personas, activePersonaId, setActivePersonaId, onNew, onEdit }) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 4 }}>
        <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)' }}>Personas</div>
        <Button variant="primary" size="sm" icon="plus" glow onClick={onNew}>New persona</Button>
      </div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20, maxWidth: 620 }}>
        Each persona is a JSON file at <span className="mono">backend/persona/&lt;id&gt;.json</span>. The active one drives the News scripter, the prompt generator's tone, and the default Voiceover.
        Built-in personas are read-only; duplicate any of them to edit.
      </div>
      <PersonaSelector
        personas={personas}
        activeId={activePersonaId}
        onSelect={setActivePersonaId}
        onNew={onNew}
        onEdit={onEdit}
      />
    </>
  );
}

const PROVIDER_KEYS = [
  { k: 'FAL_KEY',           label: 'fal.ai (Seedance)',   why: 'image → cinematic clip',          health: 'fal_configured' },
  { k: 'HEYGEN_API_KEY',    label: 'HeyGen avatars',      why: 'talking avatars',                  health: 'heygen_enabled' },
  { k: 'ELEVENLABS_API_KEY',label: 'ElevenLabs voice',    why: 'voiceover',                        health: 'voiceover_enabled' },
  { k: 'ANTHROPIC_API_KEY', label: 'Anthropic (summary)', why: 'news summarizer',                  health: 'has_summarizer' },
];

function ApiKeysSection() {
  const h = useHealth();
  const [serverKeys, setServerKeys] = useStateScr([]);   // {key,set,preview}
  const [envPath, setEnvPath] = useStateScr('');
  const [draft, setDraft] = useStateScr({});             // { KEY: 'new value' }
  const [saving, setSaving] = useStateScr(false);
  const [saveMsg, setSaveMsg] = useStateScr('');

  function refresh() {
    api.listKeys().then(r => {
      setServerKeys(r?.keys || []);
      setEnvPath(r?.env_path || '');
    });
  }
  useEffect(() => { refresh(); }, []);

  function setVal(k, v) { setDraft(d => ({ ...d, [k]: v })); }

  async function saveOne(k) {
    const v = (draft[k] || '').trim();
    if (!v) return;
    setSaving(true);
    const r = await api.setKeys([{ name: k, value: v }]);
    setSaving(false);
    if (r.ok) {
      setDraft(d => { const n = { ...d }; delete n[k]; return n; });
      setSaveMsg(`${k} saved — restart the backend to apply.`);
      refresh(); refreshHealth();
      setTimeout(() => setSaveMsg(''), 4500);
    } else {
      setSaveMsg(`Failed: ${String(r.error || '').slice(0, 120)}`);
    }
  }

  async function saveAll() {
    const entries = Object.entries(draft)
      .map(([k, v]) => ({ name: k, value: (v || '').trim() }))
      .filter(e => e.value);
    if (!entries.length) return;
    setSaving(true);
    const r = await api.setKeys(entries);
    setSaving(false);
    if (r.ok) {
      setDraft({});
      setSaveMsg(`${r.written?.length || entries.length} key(s) saved — restart the backend to apply.`);
      refresh(); refreshHealth();
      setTimeout(() => setSaveMsg(''), 5500);
    } else {
      setSaveMsg(`Failed: ${String(r.error || '').slice(0, 120)}`);
    }
  }

  const serverByKey = Object.fromEntries(serverKeys.map(k => [k.key, k]));

  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>API keys</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20 }}>
        Stored in <span className="mono">{envPath || 'backend/.env'}</span>. Paste a value and click <strong>Save</strong> — the backend writes it to .env (allowlisted keys only, never returned in clear). <strong>Restart the backend</strong> after saving so pydantic-settings re-reads the file.
      </div>

      <Panel style={{ padding: 0 }}>
        {PROVIDER_KEYS.map((row, i) => {
          const set = !!h?.[row.health];
          const sk = serverByKey[row.k];
          return (
            <div key={row.k} style={{
              display: 'grid', gridTemplateColumns: '220px 1fr auto auto', gap: 14, alignItems: 'center',
              padding: '14px 18px',
              borderTop: i ? '1px solid var(--stroke)' : 'none',
            }}>
              <div>
                <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>{row.label}</div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink-muted)' }}>{row.k} · {row.why}</div>
                {sk?.preview && <div className="mono" style={{ fontSize: 10, color: 'var(--ink-soft)', marginTop: 2 }}>current: {sk.preview}</div>}
              </div>
              <input
                type="password"
                value={draft[row.k] || ''}
                onChange={(e) => setVal(row.k, e.target.value)}
                placeholder={sk?.set ? 'paste a new value to rotate (leave empty to keep)' : 'paste key here…'}
                style={{ background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', padding: '6px 10px', color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', fontSize: 12 }}
              />
              <Badge tone={set ? 'green' : 'red'} dot>{set ? 'set' : 'missing'}</Badge>
              <Button variant="primary" size="sm" icon="check"
                onClick={() => saveOne(row.k)}
                disabled={saving || !(draft[row.k] || '').trim()}>
                {saving ? '…' : 'Save'}
              </Button>
            </div>
          );
        })}
      </Panel>

      <div style={{ marginTop: 14, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button variant="primary" size="md" icon="check" glow
          onClick={saveAll}
          disabled={saving || !Object.values(draft).some(v => (v || '').trim())}>
          Save all changes
        </Button>
        <span style={{ fontSize: 11, color: 'var(--ink-soft)' }}>
          Then in a PowerShell window: <span className="mono">Get-Process python | Stop-Process -Force; .\\scripts\\launch.ps1</span>
        </span>
        {saveMsg && (
          <div style={{
            padding: '6px 10px', borderRadius: 'var(--r-sm)', fontSize: 11.5,
            background: saveMsg.startsWith('Failed') ? 'var(--red-soft)' : 'var(--green-soft)',
            border: `1px solid ${saveMsg.startsWith('Failed') ? 'var(--red)' : 'var(--green)'}`,
            color: 'var(--ink-strong)',
          }}>{saveMsg}</div>
        )}
      </div>

      <OllamaCard serverKeys={serverByKey} onSaved={() => { refresh(); refreshHealth(); }} />

      <div style={{ marginTop: 24, padding: 12, background: 'var(--bg-panel-2)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', fontSize: 11, color: 'var(--ink-soft)' }}>
        Tip: see <span className="mono">Settings → Provider defaults</span> to pick which credential each role uses, and <span className="mono">Settings → Appearance</span> for motion preferences.
      </div>
    </>
  );
}

/* ──────────── Local LLM (Ollama) — plain-text fields, not secrets ──────────── */
function OllamaCard({ serverKeys, onSaved }) {
  const h = useHealth();
  const [url, setUrl] = useStateScr(null);
  const [model, setModel] = useStateScr(null);
  const [saving, setSaving] = useStateScr(false);
  const [msg, setMsg] = useStateScr('');
  const liveUrl = serverKeys?.OLLAMA_URL?.preview ? '' : '';
  const urlVal = url ?? '';
  const modelVal = model ?? '';
  const on = !!h?.ollama_enabled;

  async function save() {
    setSaving(true); setMsg('');
    const entries = [];
    if (url !== null) entries.push({ name: 'OLLAMA_URL', value: url.trim() });
    if (model !== null) entries.push({ name: 'OLLAMA_MODEL', value: model.trim() });
    if (!entries.length) { setSaving(false); return; }
    const r = await api.setKeys(entries);
    setSaving(false);
    if (r.ok) { setUrl(null); setModel(null); setMsg('Saved — restart the backend to use the local model.'); onSaved?.(); setTimeout(() => setMsg(''), 4000); }
    else setMsg('Failed: ' + String(r.error || '').slice(0, 120));
  }

  return (
    <div style={{ marginTop: 22 }}>
      <div className="display" style={{ fontSize: 15, color: 'var(--ink-strong)', marginBottom: 4 }}>Local LLM (Ollama)</div>
      <div style={{ fontSize: 11.5, color: 'var(--ink-soft)', marginBottom: 12, maxWidth: 640 }}>
        Run marketing plans on a <strong>local model</strong> — free, and nothing leaves your machine. Install <span className="mono">ollama.com</span>, then <span className="mono">ollama pull qwen2.5:14b-instruct</span>. Set the model below. Priority: Anthropic &gt; Ollama &gt; built-in planner.
      </div>
      <Panel style={{ padding: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, alignItems: 'end' }}>
          <Field label="Server URL">
            <Input mono value={urlVal} placeholder={serverKeys?.OLLAMA_URL?.preview || 'http://127.0.0.1:11434'} onChange={setUrl} />
          </Field>
          <Field label="Model name">
            <Input mono value={modelVal} placeholder={serverKeys?.OLLAMA_MODEL?.set ? serverKeys.OLLAMA_MODEL.preview : 'qwen2.5:14b-instruct'} onChange={setModel} />
          </Field>
          <Button variant="primary" size="md" icon="check" onClick={save} disabled={saving || (url === null && model === null)}>
            {saving ? '…' : 'Save'}
          </Button>
        </div>
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Badge tone={on ? 'green' : 'neutral'} dot>{on ? 'local model active' : 'not configured (cloud/built-in used)'}</Badge>
          {msg && <span style={{ fontSize: 11, color: msg.startsWith('Failed') ? 'var(--red)' : 'var(--green)' }}>{msg}</span>}
        </div>
      </Panel>
    </div>
  );
}

/* ──────────── Branding (white-label, v1.11) ──────────── */
function BrandingSection() {
  const live = useBranding();
  const [draft, setDraft] = useStateScr(null);   // editable copy
  const [saving, setSaving] = useStateScr(false);
  const [msg, setMsg] = useStateScr('');
  const [logoBust, setLogoBust] = useStateScr(0);
  const logoRef = React.useRef(null);
  const b = draft || live;

  function field(k, v) { setDraft(d => ({ ...(d || live), [k]: v })); }

  async function save() {
    if (!draft) return;
    setSaving(true); setMsg('');
    const r = await api.setBranding({
      app_name: draft.app_name, app_sub: draft.app_sub,
      tagline_1: draft.tagline_1, tagline_2: draft.tagline_2,
      brand_color: draft.brand_color, accent_color: draft.accent_color,
    });
    setSaving(false);
    if (r?.app_name) {
      setDraft(null); refreshBranding(); applyBrandColors(r);
      setMsg('Brand saved — applied everywhere.');
      setTimeout(() => setMsg(''), 3500);
    } else {
      setMsg('Failed: ' + String(r?.error || '').slice(0, 140));
    }
  }

  async function uploadLogo(file) {
    if (!file) return;
    setSaving(true); setMsg('');
    const r = await api.uploadBrandLogo(file);
    setSaving(false);
    if (r?.ok) { setLogoBust(Date.now()); refreshBranding(); setMsg('Logo updated.'); setTimeout(() => setMsg(''), 3000); }
    else setMsg('Failed: ' + String(r?.error || '').slice(0, 140));
  }

  async function resetAll() {
    if (!confirm('Reset name, taglines, colors and logo to the deepotus defaults?')) return;
    setSaving(true);
    const r = await api.resetBranding();
    setSaving(false);
    setDraft(null); setLogoBust(Date.now());
    if (r?.app_name) { refreshBranding(); applyBrandColors(r); setMsg('Reset to deepotus.'); setTimeout(() => setMsg(''), 3000); }
  }

  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>Branding</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20, maxWidth: 620 }}>
        Make this studio yours: name, taglines, colors and logo apply to the splash screen, the sidebar and every accent in the app. Stored in <span className="mono">assets/branding/</span> — survives upgrades. The product ships as <strong>deepotus</strong>; reset any time.
      </div>

      <Panel style={{ padding: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 18, alignItems: 'start' }}>
          {/* Logo */}
          <div style={{ textAlign: 'center' }}>
            <img src={api.brandLogoUrl(logoBust)} alt="logo" width={96} height={96}
              style={{ width: 96, height: 96, objectFit: 'contain', borderRadius: '50%', border: '1px solid var(--stroke)', background: 'var(--bg-base)', boxShadow: '0 0 24px var(--brand-soft)' }} />
            <input ref={logoRef} type="file" accept="image/png,image/jpeg,image/webp" style={{ display: 'none' }}
              onChange={e => { uploadLogo(e.target.files?.[0]); e.target.value = ''; }} />
            <Button variant="outline" size="sm" icon="upload" style={{ marginTop: 8, width: '100%' }}
              onClick={() => logoRef.current?.click()} disabled={saving}>Logo…</Button>
          </div>
          {/* Fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="App name"><Input value={b.app_name} onChange={v => field('app_name', v.toUpperCase().slice(0, 18))} /></Field>
            <Field label="Sub-label"><Input value={b.app_sub} onChange={v => field('app_sub', v.toUpperCase().slice(0, 12))} /></Field>
            <Field label="Tagline line 1"><Input value={b.tagline_1} onChange={v => field('tagline_1', v.slice(0, 40))} /></Field>
            <Field label="Tagline line 2"><Input value={b.tagline_2} onChange={v => field('tagline_2', v.slice(0, 40))} /></Field>
            <Field label="Brand color (primary)">
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input type="color" value={b.brand_color} onChange={e => field('brand_color', e.target.value)}
                  style={{ width: 44, height: 30, padding: 2, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }} />
                <Input mono value={b.brand_color} onChange={v => field('brand_color', v)} style={{ flex: 1 }} />
              </div>
            </Field>
            <Field label="Accent color (cyan)">
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input type="color" value={b.accent_color} onChange={e => field('accent_color', e.target.value)}
                  style={{ width: 44, height: 30, padding: 2, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', cursor: 'pointer' }} />
                <Input mono value={b.accent_color} onChange={v => field('accent_color', v)} style={{ flex: 1 }} />
              </div>
            </Field>
          </div>
        </div>

        {/* Live wordmark preview */}
        <div style={{ marginTop: 16, padding: 14, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r)', display: 'flex', alignItems: 'center', gap: 14 }}>
          <img src={api.brandLogoUrl(logoBust)} alt="" width={34} height={34} style={{ borderRadius: '50%' }} />
          <div style={{ lineHeight: 1.1 }}>
            <div className="display" style={{ fontSize: 15, fontWeight: 700, letterSpacing: '0.04em', color: b.brand_color }}>{b.app_name || 'APP NAME'}</div>
            <div style={{ fontSize: 9, color: 'var(--ink-soft)', letterSpacing: '0.18em' }}>{b.app_sub} · v1.14.0</div>
          </div>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, fontStyle: 'italic', color: 'var(--ink-soft)' }}>{b.tagline_1} {b.tagline_2}</span>
          <span style={{ width: 16, height: 16, borderRadius: 4, background: b.accent_color, border: '1px solid var(--stroke)' }} title="accent" />
        </div>

        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Button variant="primary" size="md" icon="check" glow onClick={save} disabled={saving || !draft}>
            {saving ? 'Saving…' : 'Save brand'}
          </Button>
          <Button variant="ghost" size="sm" onClick={resetAll} disabled={saving}>Reset to deepotus</Button>
          {msg && <span style={{ fontSize: 11.5, color: msg.startsWith('Failed') ? 'var(--red)' : 'var(--green)' }}>{msg}</span>}
        </div>
      </Panel>
    </>
  );
}

/* ──────────── Appearance (Reduced motion + halo) ──────────── */
function AppearanceSection() {
  // Persist + apply via CSS classes on <html>.
  const [reduced, setReduced] = useStateScr(() => localStorage.getItem('deepotus.motion.reduced') === '1');
  const [halo, setHalo]       = useStateScr(() => localStorage.getItem('deepotus.motion.halo') !== '0');
  useEffect(() => {
    const html = document.documentElement;
    if (reduced) html.classList.add('no-motion'); else html.classList.remove('no-motion');
    localStorage.setItem('deepotus.motion.reduced', reduced ? '1' : '0');
  }, [reduced]);
  useEffect(() => {
    const html = document.documentElement;
    if (halo) html.classList.remove('no-halo'); else html.classList.add('no-halo');
    localStorage.setItem('deepotus.motion.halo', halo ? '1' : '0');
  }, [halo]);
  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>Appearance</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20 }}>Motion + flair toggles. Saved in your browser; apply across all screens immediately.</div>
      <Panel style={{ padding: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>Reduced motion</div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>Disable halo pulse, edge cascade, splash zoom, caustics. Honors <span className="mono">prefers-reduced-motion</span> automatically.</div>
          </div>
          <Toggle checked={reduced} onChange={setReduced} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>Tentacle halo on active node</div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>🐙 The deep flair on the running Studio node.</div>
          </div>
          <Toggle checked={halo} onChange={setHalo} />
        </div>
      </Panel>
    </>
  );
}

/* ──────────── Paths (read-only system folders + open buttons) ──────────── */
function PathsSection() {
  const h = useHealth();
  const rows = [
    { k: 'images_folder',  label: 'Images folder',  desc: 'Where uploaded source images are stored. Library reads from here.' },
    { k: 'outputs_folder', label: 'Outputs folder', desc: 'Final renders, audio, captions are written here per job.' },
  ];
  function copy(p) { try { navigator.clipboard.writeText(p); } catch {} }
  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>Paths</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20 }}>Resolved from <span className="mono">/api/health</span>. Auto-configured by <span className="mono">scripts/setup-paths.ps1</span>. To change them, edit <span className="mono">backend/.env</span> with <span className="mono">PYTHON_EXE_PATH</span> / <span className="mono">FFMPEG_BIN_PATH</span>.</div>
      <Panel style={{ padding: 0 }}>
        {rows.map((r, i) => (
          <div key={r.k} style={{
            display: 'grid', gridTemplateColumns: '200px 1fr auto', gap: 16, alignItems: 'center',
            padding: '14px 18px', borderTop: i ? '1px solid var(--stroke)' : 'none',
          }}>
            <div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>{r.label}</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{r.desc}</div>
            </div>
            <div className="mono" style={{ fontSize: 11, color: 'var(--ink)', wordBreak: 'break-all' }}>{h?.[r.k] || '—'}</div>
            <Button variant="ghost" size="sm" icon="copy" onClick={() => copy(h?.[r.k])} disabled={!h?.[r.k]}>Copy</Button>
          </div>
        ))}
      </Panel>
      <div className="display" style={{ fontSize: 16, color: 'var(--ink-strong)', margin: '28px 0 8px' }}>Backend version</div>
      <Panel style={{ padding: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>API version</div>
            <div style={{ fontSize: 11, color: 'var(--ink-soft)' }}>From <span className="mono">/api/health</span></div>
          </div>
          <Badge tone={h?.ok ? 'green' : 'red'} dot>{h?.version ? `v${h.version}` : 'unreachable'}</Badge>
        </div>
      </Panel>
    </>
  );
}

/* ──────────── News settings (real sources + toggles) ──────────── */
function NewsSettingsSection() {
  const [sources, setSources] = useStateScr([]);
  const [adding, setAdding] = useStateScr('');
  const [busy, setBusy] = useStateScr(false);
  const [msg, setMsg] = useStateScr('');
  async function refresh() {
    try {
      const r = await fetch('/api/news/sources');
      if (r.ok) {
        const j = await r.json();
        setSources(j?.sources || []);
      }
    } catch {}
  }
  useEffect(() => { refresh(); }, []);
  async function toggle(id, enabled) {
    setBusy(true);
    try {
      await fetch(`/api/news/sources/${id}/toggle`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      refresh();
    } finally { setBusy(false); }
  }
  async function remove(id) {
    if (!confirm('Remove this feed?')) return;
    setBusy(true);
    try {
      await fetch(`/api/news/sources/${id}`, { method: 'DELETE' });
      refresh();
    } finally { setBusy(false); }
  }
  async function add() {
    const url = adding.trim();
    if (!url) return;
    setBusy(true); setMsg('');
    try {
      const r = await fetch('/api/news/sources', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, name: null, type: 'rss' }),
      });
      if (r.ok) { setAdding(''); setMsg('Added.'); refresh(); }
      else { setMsg('Failed: ' + (await r.text()).slice(0, 120)); }
    } catch (e) { setMsg('Failed: ' + e); }
    finally { setBusy(false); setTimeout(() => setMsg(''), 3500); }
  }
  async function seedDefaults() {
    setBusy(true);
    try {
      const r = await fetch('/api/news/sources/defaults', { method: 'POST' });
      if (r.ok) refresh();
    } finally { setBusy(false); }
  }
  async function refreshAll() {
    setBusy(true); setMsg('Refreshing all feeds…');
    try {
      const r = await fetch('/api/news/refresh', { method: 'POST' });
      if (r.ok) {
        const j = await r.json();
        setMsg(`Pulled ${j?.fetched || '?'} items.`);
      } else setMsg('Refresh failed.');
    } finally { setBusy(false); setTimeout(() => setMsg(''), 3500); }
  }
  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>News</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20 }}>RSS / Atom feed pack used by the News pipeline. Defaults cover crypto, geopolitics, economy. Toggle individual feeds; add custom URLs.</div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center', flexWrap: 'wrap' }}>
        <input value={adding} onChange={e => setAdding(e.target.value)} placeholder="https://… (RSS feed URL)"
          style={{ flex: 1, minWidth: 280, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', padding: '8px 10px', color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', fontSize: 12 }} />
        <Button variant="primary" size="sm" icon="plus" onClick={add} disabled={busy || !adding.trim()}>Add feed</Button>
        <Button variant="outline" size="sm" icon="bolt" onClick={refreshAll} disabled={busy}>Refresh all</Button>
        <Button variant="ghost" size="sm" onClick={seedDefaults} disabled={busy}>Restore defaults</Button>
      </div>
      {msg && <div style={{ marginBottom: 10, fontSize: 11.5, color: msg.startsWith('Failed') ? 'var(--red)' : 'var(--green)' }}>{msg}</div>}
      <Panel style={{ padding: 0, maxHeight: 480, overflow: 'auto' }}>
        {sources.length === 0 && <div style={{ padding: 20, fontSize: 12, color: 'var(--ink-soft)' }}>No sources. Click "Restore defaults" to seed the curated feed pack.</div>}
        {sources.map((s, i) => (
          <div key={s.id || i} style={{
            display: 'grid', gridTemplateColumns: '20px 1fr auto auto auto', gap: 12, alignItems: 'center',
            padding: '10px 14px', borderTop: i ? '1px solid var(--stroke)' : 'none',
          }}>
            <Icon name="rss" size={13} style={{ color: s.enabled ? 'var(--cyan)' : 'var(--ink-muted)' }} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12, color: s.enabled ? 'var(--ink-strong)' : 'var(--ink-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name || s.url}</div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--ink-soft)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.url}</div>
            </div>
            <Badge tone={s.enabled ? 'green' : 'red'} dot>{s.enabled ? 'on' : 'off'}</Badge>
            <Toggle checked={s.enabled} onChange={(v) => toggle(s.id, v)} />
            <IconButton name="trash" iconSize={11} title="Remove" onClick={() => remove(s.id)} />
          </div>
        ))}
      </Panel>
      <div style={{ marginTop: 12, fontSize: 11, color: 'var(--ink-soft)' }}>
        {sources.length} source{sources.length === 1 ? '' : 's'} ·
        {' '}{sources.filter(s => s.enabled).length} active
      </div>
    </>
  );
}

function ProviderDefaultsSection() {
  const h = useHealth();
  const available = PROVIDER_KEYS.filter(p => !!h?.[p.health]).map(p => p.k);

  // Persisted defaults: which keys to use by default per role.
  const [defaults, setDefaults] = useStateScr(() => {
    try { return JSON.parse(localStorage.getItem('deepotus.provider_defaults') || '{}'); } catch { return {}; }
  });
  function setDef(role, key) {
    const next = { ...defaults, [role]: key };
    setDefaults(next);
    localStorage.setItem('deepotus.provider_defaults', JSON.stringify(next));
  }

  const roles = [
    { id: 'video',       label: 'Image → video',       hint: 'Seedance / fal.ai for cinematic clips',       options: ['FAL_KEY'] },
    { id: 'avatar',      label: 'Talking avatar',       hint: 'HeyGen for the speaking head',                 options: ['HEYGEN_API_KEY'] },
    { id: 'voice',       label: 'Voiceover (non-avatar)', hint: 'ElevenLabs for narration on Seedance clips', options: ['ELEVENLABS_API_KEY'] },
    { id: 'summarizer',  label: 'News summarizer',      hint: 'Anthropic Claude for neutral 2-3 sentence article summaries', options: ['ANTHROPIC_API_KEY'] },
  ];

  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>Provider defaults</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20 }}>
        Pick which credential each role uses by default. Only keys actually set in <span className="mono">backend/.env</span> appear here. Saved locally.
      </div>
      <Panel style={{ padding: 0 }}>
        {roles.map((role, i) => {
          const usable = role.options.filter(k => available.includes(k));
          const cur = defaults[role.id] || usable[0] || '';
          return (
            <div key={role.id} style={{
              display: 'grid', gridTemplateColumns: '260px 1fr auto', gap: 14, alignItems: 'center',
              padding: '14px 18px', borderTop: i ? '1px solid var(--stroke)' : 'none',
            }}>
              <div>
                <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>{role.label}</div>
                <div style={{ fontSize: 10.5, color: 'var(--ink-soft)' }}>{role.hint}</div>
              </div>
              {usable.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--red)' }}>No key set for this role. Add one in API keys.</div>
              ) : (
                <Select value={cur} options={usable.map(k => ({ value: k, label: k }))} onChange={(v) => setDef(role.id, v)} />
              )}
              <Badge tone={usable.length ? 'green' : 'red'} dot>{usable.length ? 'ready' : 'missing'}</Badge>
            </div>
          );
        })}
      </Panel>
    </>
  );
}

function ConnectedAccountsSection() {
  const [open, setOpen] = useStateScr(new Set(['x']));
  const [serverKeys, setServerKeys] = useStateScr({});   // {KEY: {set, preview}}
  const [draft, setDraft] = useStateScr({});             // {KEY: 'new value'}
  const [busyKey, setBusyKey] = useStateScr('');
  const [testMsg, setTestMsg] = useStateScr({});         // {channel: msg}
  const h = useHealth();

  function refreshKeys() {
    api.listKeys().then(r => {
      const map = {};
      (r?.keys || []).forEach(k => { map[k.key] = k; });
      setServerKeys(map);
    });
  }
  useEffect(() => { refreshKeys(); }, []);

  async function saveField(keyName) {
    const v = (draft[keyName] || '').trim();
    if (!v) return;
    setBusyKey(keyName);
    const r = await api.setKeys([{ name: keyName, value: v }]);
    setBusyKey('');
    if (r.ok) {
      setDraft(d => { const n = { ...d }; delete n[keyName]; return n; });
      refreshKeys(); refreshHealth();
    }
  }

  async function testChannel(ch) {
    setTestMsg(m => ({ ...m, [ch]: 'Testing…' }));
    const r = await api.testChannel(ch);
    setTestMsg(m => ({ ...m, [ch]: r?.ok ? `OK — ${r.detail}` : `Failed — ${String(r?.detail || r?.error || '').slice(0, 120)}` }));
  }

  // Channel definitions driven by which .env keys exist server-side.
  // "connected" = all required keys set AND (for adapters) backend confirms.
  const ACCOUNTS = [
    {
      k: 'x', label: 'X (Twitter)', icon: 'channelX', color: '#e6f1ff',
      auto: true, testable: true,
      connected: !!h?.x_enabled,
      note: 'Auto-publish via API v2. Get the 4 keys at developer.x.com (free tier allows posting). Restart the backend after saving.',
      fields: [
        { k: 'X_API_KEY',       label: 'API key' },
        { k: 'X_API_SECRET',    label: 'API secret' },
        { k: 'X_ACCESS_TOKEN',  label: 'Access token' },
        { k: 'X_ACCESS_SECRET', label: 'Access secret' },
      ],
    },
    {
      k: 'telegram', label: 'Telegram', icon: 'channelTelegram', color: '#29b6f6',
      auto: true, testable: true,
      connected: !!h?.telegram_enabled,
      note: 'Auto-publish via bot. Create a bot with @BotFather, add it as channel ADMIN, paste token + chat id. Restart the backend after saving.',
      fields: [
        { k: 'TELEGRAM_BOT_TOKEN', label: 'Bot token' },
        { k: 'TELEGRAM_CHAT_ID',   label: 'Channel chat ID' },
      ],
    },
    {
      k: 'youtube', label: 'YouTube', icon: 'channelYoutube', color: '#ef4444',
      auto: false, testable: false,
      connected: ['YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN'].every(k => serverKeys[k]?.set),
      note: 'Assisted publishing for now (the Scheduler flips posts to READY and you upload manually). Auto-upload is on the roadmap; keys can be stored already.',
      fields: [
        { k: 'YOUTUBE_CLIENT_ID',     label: 'OAuth client ID' },
        { k: 'YOUTUBE_CLIENT_SECRET', label: 'OAuth client secret' },
        { k: 'YOUTUBE_REFRESH_TOKEN', label: 'Refresh token' },
        { k: 'YOUTUBE_CHANNEL_ID',    label: 'Channel ID' },
      ],
    },
    {
      k: 'instagram', label: 'Instagram', icon: 'channelInstagram', color: '#c084fc',
      auto: false, testable: false,
      connected: ['IG_ACCESS_TOKEN','IG_BUSINESS_ID'].every(k => serverKeys[k]?.set),
      note: 'Assisted publishing. True auto-post requires a Business/Creator account + Meta app review — out of scope for most setups.',
      fields: [
        { k: 'IG_ACCESS_TOKEN', label: 'Graph API token' },
        { k: 'IG_BUSINESS_ID',  label: 'Business account ID' },
      ],
    },
  ];

  function toggle(k) { const s = new Set(open); s.has(k) ? s.delete(k) : s.add(k); setOpen(s); }
  return (
    <>
      <div className="display" style={{ fontSize: 22, color: 'var(--ink-strong)', marginBottom: 4 }}>Connected accounts</div>
      <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 20, maxWidth: 620 }}>
        Live status from <span className="mono">backend/.env</span> + <span className="mono">/api/health</span>. Paste a value and Save — then restart the backend to activate the adapter. <span style={{ color: 'var(--green)' }}>auto</span> = the Scheduler can publish alone; <span style={{ color: 'var(--amber)' }}>assisted</span> = it preps the post and you click Send.
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {ACCOUNTS.map(acc => {
          const isOpen = open.has(acc.k);
          const connected = acc.connected;
          const keysSet = acc.fields.filter(f => serverKeys[f.k]?.set).length;
          return (
            <Panel key={acc.k} style={{ overflow: 'hidden' }}>
              <button onClick={() => toggle(acc.k)} style={{
                width: '100%', padding: '14px 16px',
                display: 'flex', alignItems: 'center', gap: 14,
                background: 'transparent', border: 0, cursor: 'pointer', textAlign: 'left',
              }}>
                <span style={{
                  width: 36, height: 36, borderRadius: 8,
                  background: connected ? acc.color + '22' : 'var(--bg-panel-2)',
                  border: `1px solid ${connected ? acc.color + '66' : 'var(--stroke)'}`,
                  color: connected ? acc.color : 'var(--ink-muted)',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <Icon name={acc.icon} size={18} />
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, color: 'var(--ink-strong)', fontWeight: 600 }}>{acc.label}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ink-soft)', fontFamily: 'var(--f-mono)' }}>
                    {keysSet}/{acc.fields.length} keys set
                  </div>
                </div>
                <Badge tone={acc.auto ? (connected ? 'green' : 'red') : (connected ? 'amber' : 'neutral')} dot>
                  {acc.auto
                    ? (connected ? 'auto' : 'not connected')
                    : (connected ? 'assisted (keys stored)' : 'assisted')}
                </Badge>
                <Icon name="caretR" size={12} style={{ color: 'var(--ink-soft)', transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform var(--dur-1) var(--ease)' }} />
              </button>
              {isOpen && (
                <div style={{ borderTop: '1px solid var(--stroke)', padding: '12px 16px 16px', background: 'var(--bg-panel-2)' }}>
                  <div style={{ marginBottom: 12, padding: 10, background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', fontSize: 11.5, color: 'var(--ink)', lineHeight: 1.5 }}>
                    {acc.note}
                  </div>
                  {acc.fields.map((f, i) => {
                    const sk = serverKeys[f.k];
                    return (
                      <div key={f.k} style={{
                        display: 'grid', gridTemplateColumns: '180px 1fr auto auto', gap: 12, alignItems: 'center',
                        padding: '10px 0', borderTop: i ? '1px solid var(--stroke)' : 'none',
                      }}>
                        <div>
                          <div style={{ fontSize: 12.5, color: 'var(--ink-strong)' }}>{f.label}</div>
                          <div className="mono" style={{ fontSize: 10, color: 'var(--ink-muted)' }}>{f.k}</div>
                          {sk?.preview && <div className="mono" style={{ fontSize: 10, color: 'var(--ink-soft)' }}>{sk.preview}</div>}
                        </div>
                        <input
                          type="password"
                          value={draft[f.k] || ''}
                          onChange={e => setDraft(d => ({ ...d, [f.k]: e.target.value }))}
                          placeholder={sk?.set ? 'paste a new value to rotate' : 'paste value…'}
                          style={{ background: 'var(--bg-base)', border: '1px solid var(--stroke)', borderRadius: 'var(--r-sm)', padding: '6px 10px', color: 'var(--ink-strong)', fontFamily: 'var(--f-mono)', fontSize: 11.5 }}
                        />
                        <Badge tone={sk?.set ? 'green' : 'red'} dot>{sk?.set ? 'set' : 'empty'}</Badge>
                        <Button variant="primary" size="sm"
                          onClick={() => saveField(f.k)}
                          disabled={busyKey === f.k || !(draft[f.k] || '').trim()}>
                          {busyKey === f.k ? '…' : 'Save'}
                        </Button>
                      </div>
                    );
                  })}
                  {acc.testable && (
                    <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Button variant="outline" size="sm" icon="bolt"
                        onClick={() => testChannel(acc.k)} disabled={!connected}>
                        {acc.k === 'telegram' ? 'Send test message' : 'Verify credentials'}
                      </Button>
                      {!connected && <span style={{ fontSize: 10.5, color: 'var(--ink-muted)' }}>save keys + restart the backend first</span>}
                      {testMsg[acc.k] && (
                        <span style={{ fontSize: 11, color: testMsg[acc.k].startsWith('OK') ? 'var(--green)' : testMsg[acc.k] === 'Testing…' ? 'var(--ink-soft)' : 'var(--red)' }}>
                          {testMsg[acc.k]}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </>
  );
}

export { QuickScreen, NewsScreen, TemplatesScreen, LibraryScreen, SettingsScreen };
